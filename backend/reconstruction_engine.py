# backend/reconstruction_engine.py
"""Confidence-scored document reconstruction engine.

Port of the IndicPDF v2 scaffold's hybrid_engine, adapted for IndicPdf-Main:
Tesseract-first (real per-word confidences via image_to_data), file-path API
for the RQ worker, DOCX decompression caps (QA F5), and dependency-error
propagation through the PDF path (QA F7).
"""
import re
import unicodedata
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
from xml.etree import ElementTree

try:
    from .encoding_manager import encoding_manager
except (ImportError, ValueError):
    from encoding_manager import encoding_manager

# QA F5: caps applied before/while decompressing DOCX content
MAX_DOCX_XML_BYTES = 20 * 1024 * 1024   # decompressed word/document.xml
MAX_PARAGRAPHS = 5000
CONFIDENCE_THRESHOLD = 0.85


class OcrDependencyError(RuntimeError):
    """OCR runtime dependency missing or unusable (server misconfiguration)."""


@dataclass
class OCRSegment:
    text: str
    confidence: float
    engine: str
    line_number: int
    status: str = "accepted"
    word_confidences: List[float] = field(default_factory=list)


@dataclass
class EngineResult:
    filename: str
    source_type: str
    text: str
    original_text: str
    segments: List[OCRSegment]
    aggregate_confidence: float
    detected_language: str
    script: str
    quality_score: float
    detected_issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)
    processing_stages: List[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        # QA F3: a result with no usable text is a failure, full stop.
        return bool(self.text.strip())


MAX_PDF_PAGES = 50
_PDF_RENDER_CHUNK = 5


def _pdf_to_images(path: Path):
    """Yield PDF pages as PIL images in small chunks to bound memory.

    Renders _PDF_RENDER_CHUNK pages per pdf2image call instead of the whole
    document at once (a 300 DPI page is ~25 MB uncompressed; the host has
    512 MB). Stops at MAX_PDF_PAGES.
    """
    from pdf2image import convert_from_path
    from pdf2image.exceptions import PDFPageCountError

    first = 1
    while first <= MAX_PDF_PAGES:
        try:
            batch = convert_from_path(
                str(path), dpi=300,
                first_page=first, last_page=first + _PDF_RENDER_CHUNK - 1,
            )
        except PDFPageCountError:
            break
        if not batch:
            break
        yield from batch
        if len(batch) < _PDF_RENDER_CHUNK:
            break
        first += _PDF_RENDER_CHUNK


class IndicReconstructionEngine:
    def __init__(self, lang: str = "auto", confidence_threshold: float = CONFIDENCE_THRESHOLD):
        self.lang = lang
        self.confidence_threshold = confidence_threshold

    # ------------------------------------------------------------------ API

    def process_path(self, path: Path, original_filename: Optional[str] = None) -> EngineResult:
        path = Path(path)
        name = original_filename or path.name
        extension = Path(name).suffix.lower() or path.suffix.lower()

        if extension == ".docx":
            return self._process_docx(path, name)
        if extension in {".png", ".jpg", ".jpeg", ".tiff", ".tif"}:
            return self._process_image(path, name)
        if extension == ".pdf":
            return self._process_pdf(path, name)

        return self._failure(
            name, "unknown", ["input_validation"],
            issue="unsupported_file_type",
            recommendation="Upload PDF, DOCX, PNG, JPG, JPEG, or TIFF.",
        )

    # ----------------------------------------------------------------- DOCX

    def _process_docx(self, path: Path, name: str) -> EngineResult:
        stages = ["input_validation", "docx_xml_extraction", "unicode_normalization", "confidence_scoring"]
        try:
            text = self._extract_docx_text(path)
        except zipfile.BadZipFile:
            return self._failure(name, "docx", stages, issue="docx_extraction_failed",
                                 recommendation="The file is not a valid DOCX (zip) archive.")
        except _DocxTooLarge as exc:
            return self._failure(name, "docx", stages, issue=str(exc),
                                 recommendation="The document expands beyond supported limits. Split it and retry.")
        except Exception as exc:
            return self._failure(name, "docx", stages, issue="docx_extraction_failed",
                                 recommendation=f"DOCX extraction failed: {exc}")

        # Strip PDF text-extraction artifacts (cid markers, U+FFFD) that ride
        # along when the DOCX was itself produced from a PDF.
        text = encoding_manager.strip_all_junk(text)
        normalized = unicodedata.normalize("NFC", text).strip()
        if not normalized:
            return self._failure(name, "docx", stages, issue="docx_contains_no_extractable_text",
                                 recommendation="The document contains no readable text.")

        lines = [line.strip() for line in normalized.splitlines() if line.strip()]
        segments = [
            OCRSegment(text=line, confidence=0.99, engine="docx_xml", line_number=i + 1)
            for i, line in enumerate(lines)
        ]
        language, script = self._detect_language_and_script(normalized)
        return EngineResult(
            filename=name, source_type="docx", text=normalized, original_text=normalized,
            segments=segments, aggregate_confidence=0.99,
            detected_language=language, script=script, quality_score=0.98,
            metadata={"input_filename": name, "extraction_mode": "docx_xml",
                      "unicode_normalization": "NFC"},
            processing_stages=stages,
        )

    def _extract_docx_text(self, path: Path) -> str:
        with zipfile.ZipFile(path) as archive:
            info = archive.getinfo("word/document.xml")
            # QA F5: reject by declared decompressed size BEFORE reading
            if info.file_size > MAX_DOCX_XML_BYTES:
                raise _DocxTooLarge("docx_decompressed_size_exceeds_limit")
            xml = archive.read("word/document.xml")
        if len(xml) > MAX_DOCX_XML_BYTES:  # belt-and-braces vs lying headers
            raise _DocxTooLarge("docx_decompressed_size_exceeds_limit")

        root = ElementTree.fromstring(xml)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs: List[str] = []
        for paragraph in root.findall(".//w:p", ns):
            if len(paragraphs) >= MAX_PARAGRAPHS:
                raise _DocxTooLarge("docx_paragraph_count_exceeds_limit")
            chunks: List[str] = []
            for node in paragraph.iter():
                if node.tag == f"{{{ns['w']}}}t" and node.text:
                    chunks.append(node.text)
                elif node.tag == f"{{{ns['w']}}}tab":
                    chunks.append("\t")
            text = "".join(chunks).strip()
            if text:
                paragraphs.append(text)
        return "\n".join(paragraphs)

    # ---------------------------------------------------------------- Image

    def _process_image(self, path: Path, name: str) -> EngineResult:
        stages = ["input_validation", "image_decode", "tesseract_ocr",
                  "unicode_normalization", "confidence_scoring"]
        try:
            segments, warnings = self._ocr_image(path)
        except OcrDependencyError as exc:
            return self._dependency_failure(name, "image", stages, str(exc))
        except Exception as exc:
            return self._failure(name, "image", stages, issue="image_decode_failed",
                                 recommendation=f"Could not read the image: {exc}")

        if not segments:
            return self._failure(name, "image", stages, issue="ocr_returned_no_text",
                                 recommendation="Upload a sharper 300 DPI scan with minimal skew.")
        return self._result_from_segments(name, "image", segments, warnings, stages)

    def _ocr_image(self, image_or_path) -> tuple:
        """OCR one image (PIL image or path). Returns (segments, warnings).
        Raises OcrDependencyError when the OCR runtime is missing."""
        try:
            import pytesseract
            from PIL import Image
        except Exception as exc:  # pragma: no cover - environment specific
            raise OcrDependencyError(
                f"OCR dependencies are not installed: {exc}. "
                "Install pytesseract/Pillow and the tesseract-ocr system package."
            ) from exc

        from ocr_processor import _resolve_lang  # reuse Track C language mapping
        tess_lang = _resolve_lang(self.lang)

        image = image_or_path
        if isinstance(image_or_path, (str, Path)):
            image = Image.open(image_or_path)

        try:
            data = pytesseract.image_to_data(
                image, lang=tess_lang, output_type=pytesseract.Output.DICT
            )
        except pytesseract.TesseractNotFoundError as exc:
            raise OcrDependencyError(
                "tesseract binary not found on the server. Install tesseract-ocr."
            ) from exc

        # Group words into lines by (block, paragraph, line) keys
        lines: Dict[tuple, dict] = {}
        for i in range(len(data["text"])):
            word = (data["text"][i] or "").strip()
            try:
                conf = float(data["conf"][i])
            except (TypeError, ValueError):
                continue
            if not word or conf < 0:
                continue
            key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
            entry = lines.setdefault(key, {"words": [], "confs": []})
            entry["words"].append(word)
            entry["confs"].append(conf / 100.0)

        segments: List[OCRSegment] = []
        warnings: List[str] = []
        for line_no, key in enumerate(sorted(lines), start=1):
            entry = lines[key]
            text = unicodedata.normalize("NFC", " ".join(entry["words"])).strip()
            if not text:
                continue
            confidence = sum(entry["confs"]) / len(entry["confs"])
            status = "accepted"
            if confidence < self.confidence_threshold:
                status = "requires_review"
                warnings.append("low_confidence_region_requires_review")
            segments.append(OCRSegment(
                text=text, confidence=confidence, engine="tesseract",
                line_number=line_no, status=status,
                word_confidences=entry["confs"],
            ))
        return segments, sorted(set(warnings))

    # ------------------------------------------------------------------ PDF

    def _process_pdf(self, path: Path, name: str) -> EngineResult:
        stages = ["input_validation", "pdf_page_render", "tesseract_ocr", "confidence_scoring"]
        segments: List[OCRSegment] = []
        warnings: List[str] = []
        page_count = 0
        try:
            for image in _pdf_to_images(path):
                page_count += 1
                try:
                    page_segments, page_warnings = self._ocr_image(image)
                except OcrDependencyError as exc:
                    # QA F7: surface the real cause, never "no text extracted"
                    return self._dependency_failure(name, "pdf", stages, str(exc))
                finally:
                    # release page bitmap before rendering the next chunk
                    getattr(image, "close", lambda: None)()
                warnings.extend(page_warnings)
                for segment in page_segments:
                    segment.line_number = len(segments) + 1
                    segments.append(segment)
        except OcrDependencyError as exc:
            return self._dependency_failure(name, "pdf", stages, str(exc))
        except Exception as exc:
            return self._failure(name, "pdf", stages, issue="pdf_processing_failed",
                                 recommendation=f"PDF processing failed: {exc}")

        if page_count == 0:
            return self._failure(name, "pdf", stages, issue="pdf_contains_no_pages",
                                 recommendation="The PDF has no renderable pages.")
        if not segments:
            return self._failure(name, "pdf", stages, issue="pdf_ocr_returned_no_text",
                                 recommendation="Upload a clearer scan, or the PDF may be blank.")
        result = self._result_from_segments(name, "pdf", segments, sorted(set(warnings)), stages)
        result.metadata["page_count"] = str(page_count)
        return result

    # -------------------------------------------------------------- Helpers

    def _result_from_segments(self, name: str, source_type: str,
                              segments: List[OCRSegment], warnings: List[str],
                              stages: List[str]) -> EngineResult:
        text = "\n".join(s.text for s in segments)
        language, script = self._detect_language_and_script(text)
        aggregate = sum(s.confidence for s in segments) / len(segments)
        issues = []
        if any(s.confidence < self.confidence_threshold for s in segments):
            issues.append("low_confidence_regions")
        recommendations = []
        if aggregate < 0.9:
            recommendations = [
                "Review low-confidence lines before archival or legal use.",
                "Use a sharper 300 DPI scan with minimal skew and consistent lighting.",
            ]
        return EngineResult(
            filename=name, source_type=source_type, text=text, original_text=text,
            segments=segments, aggregate_confidence=aggregate,
            detected_language=language, script=script,
            quality_score=min(0.99, aggregate),
            detected_issues=issues, recommendations=recommendations, warnings=warnings,
            metadata={"input_filename": name, "ocr_language": self.lang,
                      "unicode_normalization": "NFC"},
            processing_stages=stages,
        )

    def _detect_language_and_script(self, text: str) -> tuple:
        if re.search(r"[ఀ-౿]", text):
            return "telugu", "telugu"
        if re.search(r"[ऀ-ॿ]", text):
            return "hindi_or_devanagari", "devanagari"
        if re.search(r"[஀-௿]", text):
            return "tamil", "tamil"
        if re.search(r"[ঀ-৿]", text):
            return "bengali_or_assamese", "bengali"
        return "unknown", "unknown"

    def _failure(self, name: str, source_type: str, stages: List[str],
                 issue: str, recommendation: str) -> EngineResult:
        return EngineResult(
            filename=name, source_type=source_type, text="", original_text="",
            segments=[], aggregate_confidence=0.0,
            detected_language="unknown", script="unknown", quality_score=0.0,
            detected_issues=[issue], recommendations=[recommendation],
            warnings=["processing_incomplete"],
            metadata={"input_filename": name},
            processing_stages=stages,
        )

    def _dependency_failure(self, name: str, source_type: str,
                            stages: List[str], message: str) -> EngineResult:
        result = self._failure(
            name, source_type, stages,
            issue="ocr_dependency_missing",
            recommendation=f"OCR engine failure: {message}",
        )
        result.metadata["error"] = "dependency_failure"
        return result


class _DocxTooLarge(Exception):
    """str(exc) is the machine-readable issue code."""
