# IndicPDF v2 Engine Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Merge the IndicPDF v2 scaffold (`/Users/jay/IndicPDF` — hybrid OCR engine with confidence scoring, rich `ProcessResult` contract, reconstruction UI) into the production app at `/Users/jay/IndicPdf-Main`, fixing QA report findings F1–F8 (`/Users/jay/IndicPDF/docs/QA_REPORT_v1.md`) during the port.

**Architecture:** IndicPdf-Main is the host — it keeps its RQ job queue, encryption (`security_manager`), rate limiting, batch infra, font registry, and Tesseract Docker stack. From the v2 scaffold we port: (1) the extraction engine as a new `backend/reconstruction_engine.py`, rewritten Tesseract-first (PaddleOCR dropped — paddlepaddle won't fit Render's 512 MB; `pytesseract.image_to_data` gives *real* per-word confidences, which closes the spec gap "word confidences are placeholders"); (2) a queued reconstruction pipeline (`/api/process` → RQ job → JSON result), which structurally fixes F2/F8 (no CPU work on the event loop, job timeouts) and F6 (multi-file with per-file jobs); (3) PDF export reusing the existing `convert_txt_to_pdf_task` (fpdf2 + HarfBuzz — better Indic shaping than WeasyPrint, zero new deps); (4) a `ReconstructionTool` frontend page following Main's existing JSX/axios/polling conventions. Cross-cutting fixes: F1 (Content-Disposition latin-1 crash — **also live in Main's `/download` today**), F3 (explicit `success` flag + UI failure state), F4 (streamed upload size cap), F5 (DOCX decompression bomb cap), F7 (dependency-error propagation through the PDF path).

**Tech Stack:** FastAPI, RQ/Redis, pytesseract (`image_to_data`), pdf2image/Pillow, fpdf2+uharfbuzz (existing), React 19 + Vite + axios, pytest, Vitest.

**Source repos:**
- Host (all changes land here): `/Users/jay/IndicPdf-Main`
- Donor (read-only reference): `/Users/jay/IndicPDF` — `backend/hybrid_engine.py`, `backend/main.py`, `frontend/src/App.tsx`, `docs/QA_REPORT_v1.md`

**QA findings → task map:**

| Finding | Fixed in |
|---|---|
| F1 filename header 500 | Task 1 (helper), Task 2 (apply to existing endpoints) |
| F2 unbounded export / sync render | Task 6 (queued export, 1 MB text cap, job timeout) |
| F3 200-on-failure / false success UX | Task 4 (`success` flag), Task 5 (HTTP contract), Task 7 (UI failure state) |
| F4 buffer-before-validate | Task 3 (streamed cap in `secure_file_upload`) |
| F5 docx zip bomb | Task 4 (decompression caps in engine) |
| F6 no multi-file | Task 5 (multi-file `/api/process`, per-file jobs) |
| F7 PDF masks dependency error | Task 4 (engine propagates dependency issues from page results) |
| F8 CPU on event loop | Task 5/6 (everything heavy runs in RQ worker) |

---

### Task 1: Content-Disposition helper (F1)

A single helper producing an RFC 6266/5987-compliant header: ASCII-only `filename=` fallback plus `filename*=UTF-8''…` carrying the real Unicode name. Restrict fallback to `[A-Za-z0-9._-]` — never `str.isalnum()` (Telugu/Devanagari pass `isalnum()` and then crash Starlette's latin-1 header encoding).

**Files:**
- Create: `backend/http_utils.py`
- Test: `tests/test_http_utils.py`

- [x] **Step 1: Write the failing tests**

```python
# tests/test_http_utils.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from http_utils import content_disposition


def test_ascii_filename_passes_through():
    header = content_disposition("report.pdf")
    assert header == "attachment; filename=\"report.pdf\"; filename*=UTF-8''report.pdf"


def test_telugu_filename_is_latin1_safe():
    header = content_disposition("తెలుగు-పత్రం.pdf")
    # Starlette encodes headers as latin-1; this must not raise
    header.encode("latin-1")
    assert 'filename="' in header
    assert "filename*=UTF-8''" in header
    # percent-encoded UTF-8 carries the real name
    assert "%E0%B0%A4" in header  # 'త'


def test_devanagari_filename_fallback_is_ascii_only():
    header = content_disposition("नमस्ते दुनिया.pdf")
    fallback = header.split('filename="')[1].split('"')[0]
    assert all(c.isascii() for c in fallback)
    assert fallback.endswith(".pdf")


def test_empty_and_hostile_names_get_default():
    for name in ("", "தமிழ்", "../../etc/passwd"):
        header = content_disposition(name)
        header.encode("latin-1")
        fallback = header.split('filename="')[1].split('"')[0]
        assert fallback  # never empty
        assert "/" not in fallback and "\\" not in fallback
```

- [x] **Step 2: Run tests to verify they fail**

Run: `cd /Users/jay/IndicPdf-Main && python -m pytest tests/test_http_utils.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'http_utils'`

- [x] **Step 3: Implement `backend/http_utils.py`**

```python
# backend/http_utils.py
"""HTTP header helpers shared by download/export endpoints."""
import re
import unicodedata
from pathlib import PurePosixPath, PureWindowsPath
from urllib.parse import quote

_SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def content_disposition(filename: str, default: str = "download") -> str:
    """Build an attachment Content-Disposition header that survives latin-1
    header encoding (RFC 6266 / RFC 5987).

    - `filename=` gets an ASCII-only fallback (transliterated where possible,
      otherwise stripped). Never uses str.isalnum(): Indic characters pass
      isalnum() but cannot be encoded as latin-1 and crash Starlette.
    - `filename*=UTF-8''...` carries the percent-encoded original name for
      modern clients.
    """
    # Strip any path components (defence in depth alongside existing checks)
    name = PureWindowsPath(PurePosixPath(filename or "").name).name

    ascii_name = (
        unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    )
    ascii_name = _SAFE_CHARS.sub("-", ascii_name).strip("-.")
    if not ascii_name or ascii_name in {".", ".."}:
        suffix = PurePosixPath(name).suffix
        ascii_suffix = "".join(c for c in suffix if c.isascii() and c.isprintable())
        ascii_name = f"{default}{ascii_suffix or ''}"

    utf8_name = quote(name or ascii_name, safe="")
    return f"attachment; filename=\"{ascii_name[:120]}\"; filename*=UTF-8''{utf8_name}"
```

- [x] **Step 4: Run tests to verify they pass**

Run: `cd /Users/jay/IndicPdf-Main && python -m pytest tests/test_http_utils.py -v`
Expected: 4 PASSED

- [x] **Step 5: Commit**

```bash
cd /Users/jay/IndicPdf-Main
git add backend/http_utils.py tests/test_http_utils.py
git commit -m "feat: add latin-1-safe Content-Disposition helper (QA F1)"
```

---

### Task 2: Apply the helper to existing download endpoints (F1 in Main)

Main's `/download/{job_id}` and `/batch/download/{batch_id}` interpolate `original_stem` (the user's upload name) straight into `Content-Disposition` — an Indic upload name 500s today, same bug as QA F1. Replace both.

**Files:**
- Modify: `backend/main.py:428` and `backend/main.py:435,444,469` (the three `Content-Disposition` header dicts)

- [x] **Step 1: Import the helper in `backend/main.py`**

Below the existing `from security_manager import security_manager` line (main.py:81), add:

```python
from http_utils import content_disposition
```

- [x] **Step 2: Replace the three header constructions**

In `download_result` (main.py:428-445), replace:

```python
    download_name = f"IndicPDF_{original_stem}{output_path.suffix}"
```
…and both header dicts `{"Content-Disposition": f'attachment; filename="{download_name}"'}` so the function reads:

```python
    download_name = f"IndicPDF_{original_stem}{output_path.suffix}"
    disposition = content_disposition(download_name)

    # OCR jobs write plaintext directly — skip decryption
    if job.result.get("ocr"):
        return Response(
            content=output_path.read_bytes(),
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": disposition}
        )

    # Decrypt in memory and stream
    try:
        decrypted_bytes = security_manager.decrypt_to_memory(output_path)
        return Response(
            content=decrypted_bytes,
            media_type="application/octet-stream",
            headers={"Content-Disposition": disposition}
        )
```

In `download_batch_result` (main.py:469), replace:

```python
            headers={"Content-Disposition": f'attachment; filename="IndicPDF_batch{final_path.suffix}"'}
```
with:

```python
            headers={"Content-Disposition": content_disposition(f"IndicPDF_batch{final_path.suffix}")}
```

- [x] **Step 3: Write a regression test**

```python
# tests/test_download_headers.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from http_utils import content_disposition


def test_indic_original_stem_does_not_crash_header_encoding():
    # The exact pattern /download builds: "IndicPDF_" + user stem + suffix
    for stem in ("నివేదిక", "पत्रं", "தமிழ்-ஆவணம்"):
        header = content_disposition(f"IndicPDF_{stem}.pdf")
        header.encode("latin-1")  # would raise UnicodeEncodeError pre-fix
```

- [x] **Step 4: Run tests**

Run: `cd /Users/jay/IndicPdf-Main && python -m pytest tests/test_download_headers.py tests/test_http_utils.py -v`
Expected: ALL PASSED

- [x] **Step 5: Commit**

```bash
cd /Users/jay/IndicPdf-Main
git add backend/main.py tests/test_download_headers.py
git commit -m "fix: latin-1-safe download filenames for Indic upload names (QA F1)"
```

---

### Task 3: Streamed upload size cap (F4)

`secure_file_upload` streams in 1 MB chunks but never counts bytes; the seek/tell size checks in the routes run only after FastAPI has spooled the whole body. Enforce the 25 MB cap *during* the stream and abort with 413.

**Files:**
- Modify: `backend/main.py:91-104` (`secure_file_upload`)
- Test: `tests/test_upload_cap.py`

- [x] **Step 1: Write the failing test**

```python
# tests/test_upload_cap.py
import io
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))


class FakeUpload:
    """Minimal async stand-in for fastapi.UploadFile."""

    def __init__(self, data: bytes):
        self._buf = io.BytesIO(data)
        self.filename = "big.docx"

    async def read(self, n: int = -1) -> bytes:
        return self._buf.read(n)


@pytest.mark.asyncio
async def test_oversized_stream_aborts_with_413(tmp_path, monkeypatch):
    from fastapi import HTTPException
    import main as backend_main

    # avoid touching the real encryptor
    monkeypatch.setattr(
        backend_main.security_manager, "encrypt_file", lambda src, dst: None
    )

    oversized = FakeUpload(b"x" * (backend_main.MAX_UPLOAD_BYTES + 1))
    with pytest.raises(HTTPException) as exc_info:
        await backend_main.secure_file_upload(oversized, tmp_path / "out.bin")
    assert exc_info.value.status_code == 413


@pytest.mark.asyncio
async def test_at_limit_stream_is_accepted(tmp_path, monkeypatch):
    import main as backend_main

    called = {}
    monkeypatch.setattr(
        backend_main.security_manager,
        "encrypt_file",
        lambda src, dst: called.setdefault("ok", True),
    )

    exact = FakeUpload(b"x" * backend_main.MAX_UPLOAD_BYTES)
    await backend_main.secure_file_upload(exact, tmp_path / "out.bin")
    assert called.get("ok")  # F9: exactly-at-limit stays accepted
```

Note: needs `pytest-asyncio`. If absent: `pip install pytest-asyncio` and add to `requirements.txt` dev section.

- [x] **Step 2: Run test to verify it fails**

Run: `cd /Users/jay/IndicPdf-Main && python -m pytest tests/test_upload_cap.py -v`
Expected: FAIL — `AttributeError: module 'main' has no attribute 'MAX_UPLOAD_BYTES'`

- [x] **Step 3: Implement the cap**

In `backend/main.py`, add a constant near the other config (below `OUTPUT_DIR`, ~line 70):

```python
MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # single shared limit; checked during streaming
```

Replace `secure_file_upload` (main.py:91-104) with:

```python
async def secure_file_upload(file: UploadFile, destination_path: Path):
    """Stream an upload to a temp file with a hard size cap, then encrypt it.

    The cap is enforced per-chunk so an oversized body is aborted after at
    most 25 MB + 1 chunk, instead of being buffered fully before validation.
    """
    total = 0
    try:
        with tempfile.NamedTemporaryFile(delete=True) as tmp:
            while True:
                chunk = await file.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File {file.filename} exceeds 25 MB limit.",
                    )
                tmp.write(chunk)
            tmp.flush()
            security_manager.encrypt_file(Path(tmp.name), destination_path)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to securely process upload {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Secure processing failed for {file.filename}")
```

Also replace the four existing literal checks `if size > 25 * 1024 * 1024:` (main.py:134, 227, 503 and the seek/tell in `/batch/upload/unified`) with `if size > MAX_UPLOAD_BYTES:` — keep them as cheap early rejections; the streaming cap is the backstop.

- [x] **Step 4: Run tests**

Run: `cd /Users/jay/IndicPdf-Main && python -m pytest tests/test_upload_cap.py -v`
Expected: 2 PASSED

- [x] **Step 5: Commit**

```bash
cd /Users/jay/IndicPdf-Main
git add backend/main.py tests/test_upload_cap.py requirements.txt
git commit -m "fix: enforce 25 MB cap while streaming uploads (QA F4)"
```

---

### Task 4: Port the engine as `backend/reconstruction_engine.py` (F5, F7, real word confidences)

Port of donor `hybrid_engine.py` with four deliberate changes:
1. **Tesseract-first** via `pytesseract.image_to_data` (real per-word confidences; PaddleOCR dropped — RAM budget).
2. **File-path API** (`process_path`) — Main's worker hands decrypted temp paths, not bytes.
3. **F5:** DOCX decompression caps (`getinfo().file_size` checked *before* read; paragraph cap).
4. **F7:** PDF path propagates per-page dependency issues instead of reporting `pdf_ocr_returned_no_text`.
5. **F3 groundwork:** `EngineResult.success` property.

**Files:**
- Create: `backend/reconstruction_engine.py`
- Test: `tests/test_reconstruction_engine.py`
- Reference (do not modify): `/Users/jay/IndicPDF/backend/hybrid_engine.py`

- [x] **Step 1: Write the failing tests**

```python
# tests/test_reconstruction_engine.py
import io
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from reconstruction_engine import (
    MAX_DOCX_XML_BYTES,
    IndicReconstructionEngine,
)


def make_docx(tmp_path: Path, body_xml: str, name: str = "doc.docx") -> Path:
    """Build a minimal docx (zip with word/document.xml)."""
    path = tmp_path / name
    document = (
        '<?xml version="1.0"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body_xml}</w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("word/document.xml", document)
    return path


def test_docx_extraction_with_telugu(tmp_path):
    doc = make_docx(tmp_path, "<w:p><w:r><w:t>తెలుగు పరీక్ష</w:t></w:r></w:p>")
    result = IndicReconstructionEngine().process_path(doc, original_filename="తెలుగు.docx")
    assert result.success
    assert result.text == "తెలుగు పరీక్ష"
    assert result.detected_language == "telugu"
    assert result.segments[0].confidence == 0.99


def test_docx_zip_bomb_is_rejected_before_decompression(tmp_path):
    # 60 MB of repeated XML compresses to well under 1 MB
    bomb_paragraph = "<w:p><w:r><w:t>" + ("అ" * 100) + "</w:t></w:r></w:p>"
    repeats = (MAX_DOCX_XML_BYTES // len(bomb_paragraph.encode())) + 100
    doc = make_docx(tmp_path, bomb_paragraph * repeats, name="bomb.docx")
    result = IndicReconstructionEngine().process_path(doc, original_filename="bomb.docx")
    assert not result.success
    assert "docx_decompressed_size_exceeds_limit" in result.detected_issues


def test_corrupt_docx_reports_failure_not_success(tmp_path):
    bad = tmp_path / "corrupt.docx"
    bad.write_bytes(b"this is not a zip file")
    result = IndicReconstructionEngine().process_path(bad, original_filename="corrupt.docx")
    assert not result.success
    assert "docx_extraction_failed" in result.detected_issues


def test_unsupported_extension(tmp_path):
    weird = tmp_path / "file.xyz"
    weird.write_bytes(b"data")
    result = IndicReconstructionEngine().process_path(weird, original_filename="file.xyz")
    assert not result.success
    assert "unsupported_file_type" in result.detected_issues


def test_pdf_dependency_failure_is_propagated(tmp_path, monkeypatch):
    """F7: when OCR deps are missing, the PDF path must say so —
    not report 'no text extracted'."""
    import reconstruction_engine as re_mod

    engine = IndicReconstructionEngine()
    monkeypatch.setattr(
        engine,
        "_ocr_image",
        lambda *a, **k: (_ for _ in ()).throw(
            re_mod.OcrDependencyError("pytesseract is not installed")
        ),
    )
    # also force the pdf→image step to "succeed" with one fake page
    monkeypatch.setattr(
        re_mod, "_pdf_to_images", lambda path: [object()], raising=False
    )

    result = engine.process_path(tmp_path / "scan.pdf", original_filename="scan.pdf")
    assert not result.success
    assert "ocr_dependency_missing" in result.detected_issues
    assert "pdf_ocr_returned_no_text" not in result.detected_issues
```

- [x] **Step 2: Run tests to verify they fail**

Run: `cd /Users/jay/IndicPdf-Main && python -m pytest tests/test_reconstruction_engine.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'reconstruction_engine'`

- [x] **Step 3: Implement `backend/reconstruction_engine.py`**

```python
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


def _pdf_to_images(path: Path):
    """Render PDF pages to PIL images. Separate function so tests can stub it."""
    from pdf2image import convert_from_path

    return convert_from_path(str(path), dpi=300)


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
            conf = float(data["conf"][i])
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
        try:
            images = _pdf_to_images(path)
        except OcrDependencyError as exc:
            return self._dependency_failure(name, "pdf", stages, str(exc))
        except Exception as exc:
            return self._failure(name, "pdf", stages, issue="pdf_processing_failed",
                                 recommendation=f"PDF processing failed: {exc}")
        if not images:
            return self._failure(name, "pdf", stages, issue="pdf_contains_no_pages",
                                 recommendation="The PDF has no renderable pages.")

        segments: List[OCRSegment] = []
        warnings: List[str] = []
        for page_index, image in enumerate(images):
            try:
                page_segments, page_warnings = self._ocr_image(image)
            except OcrDependencyError as exc:
                # QA F7: surface the real cause, never "no text extracted"
                return self._dependency_failure(name, "pdf", stages, str(exc))
            warnings.extend(page_warnings)
            for segment in page_segments:
                segment.line_number = len(segments) + 1
                segments.append(segment)

        if not segments:
            return self._failure(name, "pdf", stages, issue="pdf_ocr_returned_no_text",
                                 recommendation="Upload a clearer scan, or the PDF may be blank.")
        result = self._result_from_segments(name, "pdf", segments, sorted(set(warnings)), stages)
        result.metadata["page_count"] = str(len(images))
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
```

- [x] **Step 4: Run tests**

Run: `cd /Users/jay/IndicPdf-Main && python -m pytest tests/test_reconstruction_engine.py -v`
Expected: 5 PASSED

- [x] **Step 5: Commit**

```bash
cd /Users/jay/IndicPdf-Main
git add backend/reconstruction_engine.py tests/test_reconstruction_engine.py
git commit -m "feat: port v2 reconstruction engine with real word confidences (QA F5, F7)"
```

---

### Task 5: Queued reconstruction pipeline — task + endpoints (F2, F3, F6, F8)

`POST /api/process` accepts **multiple** files (per-file jobs, max 10 — F6), validates magic bytes + size, streams encrypted to disk, and enqueues `process_reconstruction_task` with a 300 s timeout (F2/F8). The task decrypts, runs the engine, and stores the rich result JSON. `GET /api/process/result/{job_id}` returns it with a top-level `success` boolean (F3). Failure results are stored, not thrown — the client gets a complete diagnostic payload, while `success: false` makes the failure unambiguous.

**Files:**
- Modify: `backend/tasks.py` (append task)
- Modify: `backend/main.py` (two new endpoints; extend imports)
- Test: `tests/test_reconstruction_task.py`

- [x] **Step 1: Write the failing test for the task's serialization**

```python
# tests/test_reconstruction_task.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from reconstruction_engine import EngineResult, OCRSegment
from tasks import engine_result_to_payload


def test_payload_has_v2_contract_fields_and_success_flag():
    result = EngineResult(
        filename="తెలుగు.docx", source_type="docx",
        text="తెలుగు పరీక్ష", original_text="తెలుగు పరీక్ష",
        segments=[OCRSegment(text="తెలుగు పరీక్ష", confidence=0.99,
                             engine="docx_xml", line_number=1)],
        aggregate_confidence=0.99, detected_language="telugu",
        script="telugu", quality_score=0.98,
    )
    payload = engine_result_to_payload(result)
    assert payload["success"] is True
    assert payload["clean_text"] == "తెలుగు పరీక్ష"
    assert payload["confidence_scores"]["document"] == 0.99
    assert payload["layout_structure"][0]["type"] == "paragraph"
    assert payload["language_metadata"]["detected_language"] == "telugu"
    assert payload["quality_assessment"]["status"] == "usable"


def test_failure_payload_is_marked_unsuccessful():
    result = EngineResult(
        filename="bad.docx", source_type="docx", text="", original_text="",
        segments=[], aggregate_confidence=0.0, detected_language="unknown",
        script="unknown", quality_score=0.0,
        detected_issues=["docx_extraction_failed"],
        warnings=["processing_incomplete"],
    )
    payload = engine_result_to_payload(result)
    assert payload["success"] is False
    assert payload["quality_assessment"]["status"] == "processing_incomplete"
    assert "docx_extraction_failed" in payload["quality_assessment"]["detected_issues"]
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd /Users/jay/IndicPdf-Main && python -m pytest tests/test_reconstruction_task.py -v`
Expected: FAIL — `ImportError: cannot import name 'engine_result_to_payload' from 'tasks'`

- [x] **Step 3: Append the task + serializer to `backend/tasks.py`**

Add to the imports block (inside both branches of the existing try/except import at tasks.py:17-28):

```python
    from reconstruction_engine import IndicReconstructionEngine, EngineResult
```
(and `from .reconstruction_engine import ...` in the except branch)

Append at the end of `backend/tasks.py`:

```python
import json


def engine_result_to_payload(result: "EngineResult") -> dict:
    """Serialize an EngineResult into the v2 ProcessResult contract,
    plus a top-level success flag (QA F3)."""
    return {
        "success": result.success,
        "clean_text": result.text,
        "original_ocr_text": result.original_text,
        "layout_structure": [
            {
                "type": "paragraph",
                "content": segment.text,
                "confidence": segment.confidence,
                "reading_order": index + 1,
            }
            for index, segment in enumerate(result.segments)
        ],
        "confidence_scores": {
            "document": result.aggregate_confidence,
            "word_avg": (
                sum(c for s in result.segments for c in (s.word_confidences or [s.confidence]))
                / max(1, sum(len(s.word_confidences or [s.confidence]) for s in result.segments))
            ),
            "line_avg": (
                sum(s.confidence for s in result.segments) / max(1, len(result.segments))
            ),
            "layout": result.aggregate_confidence if result.segments else 0.0,
            "quality": result.quality_score,
        },
        "word_confidence": [
            {"text": token, "confidence": conf, "status": segment.status}
            for segment in result.segments
            for token, conf in zip(
                segment.text.split(),
                segment.word_confidences or [segment.confidence] * len(segment.text.split()),
            )
        ],
        "line_confidence": [
            {
                "line_number": segment.line_number,
                "text": segment.text,
                "confidence": segment.confidence,
                "low_confidence_tokens": segment.text.split() if segment.confidence < 0.85 else [],
            }
            for segment in result.segments
        ],
        "language_metadata": {
            "detected_language": result.detected_language,
            "script": result.script,
            "source_type": result.source_type,
            **result.metadata,
        },
        "quality_assessment": {
            "status": "usable" if result.success else "processing_incomplete",
            "readability_score": result.quality_score,
            "detected_issues": result.detected_issues,
            "recommendations": result.recommendations,
        },
        "warning_flags": result.warnings,
        "processing_stages": result.processing_stages,
    }


def process_reconstruction_task(input_path: str, original_filename: str, lang: str = "auto"):
    """RQ Task: confidence-scored document reconstruction (v2 engine).

    Runs entirely in the worker (QA F2/F8). A processing failure is a
    *successful job* with success:false in the payload — the API and UI
    use that flag (QA F3). Only infrastructure errors raise.
    """
    job = get_current_job()
    logger.info(f"Starting job {job.id}: reconstruction ({original_filename})")

    suffix = Path(original_filename).suffix.lower() or Path(input_path).suffix
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_input = Path(temp_dir) / f"input{suffix}"
        security_manager.decrypt_to_file(Path(input_path), temp_input)

        engine = IndicReconstructionEngine(lang=lang)
        result = engine.process_path(temp_input, original_filename=original_filename)

    payload = engine_result_to_payload(result)

    # Persist payload encrypted, same lifecycle as other outputs (2h cleanup)
    output_path = OUTPUT_DIR / f"{job.id}.recon.json"
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tmp:
        json.dump(payload, tmp, ensure_ascii=False)
        tmp_path = Path(tmp.name)
    try:
        security_manager.encrypt_file(tmp_path, output_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    Path(input_path).unlink(missing_ok=True)
    return {
        "status": "success",
        "reconstruction": True,
        "success": payload["success"],
        "output_path": str(output_path),
    }
```

- [x] **Step 4: Run the serializer tests**

Run: `cd /Users/jay/IndicPdf-Main && python -m pytest tests/test_reconstruction_task.py -v`
Expected: 2 PASSED

- [x] **Step 5: Add the endpoints to `backend/main.py`**

Extend the task import line (main.py:78) to include the new task:

```python
from tasks import convert_docx_to_pdf_task, convert_pdf_to_docx_task, convert_txt_to_pdf_task, cleanup_old_files_task, convert_document_task, process_reconstruction_task
```

Add `import json` next to the other stdlib imports (main.py:1-6).

Insert after the `/ocr` endpoint (after main.py:211):

```python
RECON_EXTENSIONS = {".pdf", ".docx", ".png", ".jpg", ".jpeg", ".tiff", ".tif"}


@app.post("/api/process")
@limiter.limit("5/minute")
async def process_documents(
    request: Request,
    files: List[UploadFile] = File(...),
    lang: str = Form(default="auto"),
):
    """Confidence-scored reconstruction. Multi-file: one job per file (QA F6)."""
    if len(files) > 10:
        return err(400, "Max 10 files allowed per request.", "BATCH_LIMIT")

    jobs = []
    for file in files:
        ext = Path(file.filename or "").suffix.lower()
        if ext not in RECON_EXTENSIONS:
            jobs.append({"original_name": file.filename, "job_id": None,
                         "status": "rejected",
                         "detail": f"Unsupported file type: {ext or 'none'}"})
            continue

        header = await file.read(4)
        await file.seek(0)
        if ext == ".pdf" and not header.startswith(b"%PDF"):
            jobs.append({"original_name": file.filename, "job_id": None,
                         "status": "rejected", "detail": "Invalid PDF signature."})
            continue
        if ext == ".docx" and not header.startswith(b"PK\x03\x04"):
            jobs.append({"original_name": file.filename, "job_id": None,
                         "status": "rejected", "detail": "Invalid DOCX signature."})
            continue

        file_id = str(uuid.uuid4())
        input_path = UPLOAD_DIR / f"{file_id}{ext}"
        await secure_file_upload(file, input_path)  # streams + caps (QA F4)

        q_instance = Queue("slow", connection=redis_conn)  # OCR is CPU-heavy
        job = q_instance.enqueue(
            process_reconstruction_task,
            args=(str(input_path), file.filename, lang),
            job_id=file_id,
            meta={"original_stem": Path(file.filename).stem},
            retry=retry_logic(),
            job_timeout=300,  # QA F2/F8: hard processing timeout
        )
        jobs.append({"original_name": file.filename, "job_id": job.id, "status": "queued"})

    if not any(j["job_id"] for j in jobs):
        return err(400, "No processable files in request.", "NO_VALID_FILES")
    return {"jobs": jobs}


@app.get("/api/process/result/{job_id}")
async def get_process_result(job_id: str):
    """Fetch the rich reconstruction payload for a finished job."""
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.is_finished:
        raise HTTPException(status_code=409, detail=f"Job is in state: {job.get_status()}")

    output_path_str = (job.result or {}).get("output_path")
    if not output_path_str or not Path(output_path_str).exists():
        raise HTTPException(status_code=404, detail="Result expired or missing")

    decrypted = security_manager.decrypt_to_memory(Path(output_path_str))
    payload = json.loads(decrypted)
    # QA F3: unusable input → explicit 422 with full diagnostics in the body
    status_code = 200 if payload.get("success") else 422
    return JSONResponse(status_code=status_code, content=payload)
```

- [x] **Step 6: Verify the app imports cleanly**

Run: `cd /Users/jay/IndicPdf-Main/backend && python -c "import main" && cd .. && python -m pytest tests/test_reconstruction_task.py tests/test_reconstruction_engine.py -v`
Expected: import succeeds (Redis connection is lazy), all tests PASS

- [x] **Step 7: Commit**

```bash
cd /Users/jay/IndicPdf-Main
git add backend/tasks.py backend/main.py tests/test_reconstruction_task.py
git commit -m "feat: queued multi-file reconstruction pipeline (QA F2, F3, F6, F8)"
```

---

### Task 6: PDF export of reconstructed text (F1, F2)

`POST /api/export/pdf` takes `{clean_text, filename}` with a **1 MB text cap** (F2), writes the text encrypted to UPLOAD_DIR, and reuses the existing `convert_txt_to_pdf_task` (fpdf2 + HarfBuzz Indic shaping, queued with timeout — no WeasyPrint, no event-loop rendering). Download flows through the existing `/download/{job_id}` which now uses `content_disposition` (F1 fixed in Task 2).

**Files:**
- Modify: `backend/main.py` (one new endpoint, after `get_process_result`)
- Test: `tests/test_export_endpoint.py`

- [x] **Step 1: Write the failing test for the cap logic**

```python
# tests/test_export_endpoint.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import main as backend_main


def test_export_text_cap_constant():
    assert backend_main.MAX_EXPORT_TEXT_BYTES == 1 * 1024 * 1024


def test_export_request_model_rejects_oversized_text():
    text = "అ" * (backend_main.MAX_EXPORT_TEXT_BYTES + 1)  # bytes > chars for Telugu
    assert len(text.encode("utf-8")) > backend_main.MAX_EXPORT_TEXT_BYTES
    assert backend_main.export_text_too_large(text) is True
    assert backend_main.export_text_too_large("చిన్న పాఠ్యం") is False
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd /Users/jay/IndicPdf-Main && python -m pytest tests/test_export_endpoint.py -v`
Expected: FAIL — `AttributeError: module 'main' has no attribute 'MAX_EXPORT_TEXT_BYTES'`

- [x] **Step 3: Implement the endpoint**

In `backend/main.py`, add near `MAX_UPLOAD_BYTES`:

```python
MAX_EXPORT_TEXT_BYTES = 1 * 1024 * 1024  # QA F2: cap export payload


def export_text_too_large(text: str) -> bool:
    return len(text.encode("utf-8")) > MAX_EXPORT_TEXT_BYTES
```

Add `from pydantic import BaseModel` to the imports, then after `get_process_result`:

```python
class PdfExportRequest(BaseModel):
    clean_text: str
    filename: str = "indicpdf-reconstruction"


@app.post("/api/export/pdf")
@limiter.limit("5/minute")
async def export_pdf(request: Request, payload: PdfExportRequest):
    """Render reconstructed text to PDF via the existing Indic-aware
    txt→pdf worker task (queued, font-registry shaping, 300s timeout)."""
    if not payload.clean_text.strip():
        return err(400, "No reconstructed text is available for PDF export.", "EMPTY_TEXT")
    if export_text_too_large(payload.clean_text):
        return err(413, "Export text exceeds the 1 MB limit.", "TOO_LARGE")

    file_id = str(uuid.uuid4())
    input_path = UPLOAD_DIR / f"{file_id}.txt"
    output_path = OUTPUT_DIR / f"{file_id}.pdf"

    # Write plaintext to a temp file, encrypt at rest like every other upload
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as tmp:
        tmp.write(payload.clean_text)
        tmp_path = Path(tmp.name)
    try:
        security_manager.encrypt_file(tmp_path, input_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    q_instance = Queue("fast", connection=redis_conn)
    job = q_instance.enqueue(
        convert_txt_to_pdf_task,
        args=(str(input_path), str(output_path)),
        job_id=file_id,
        meta={"original_stem": Path(payload.filename).stem or "indicpdf-reconstruction"},
        retry=retry_logic(),
        job_timeout=300,
    )
    return {"job_id": job.id, "status": "queued"}
```

- [x] **Step 4: Run tests**

Run: `cd /Users/jay/IndicPdf-Main && python -m pytest tests/test_export_endpoint.py -v && cd backend && python -c "import main"`
Expected: 2 PASSED, clean import

- [x] **Step 5: Commit**

```bash
cd /Users/jay/IndicPdf-Main
git add backend/main.py tests/test_export_endpoint.py
git commit -m "feat: queued, size-capped PDF export of reconstructed text (QA F1, F2)"
```

---

### Task 7: Frontend — ReconstructionTool page (F3, F6, F10)

Port of donor `App.tsx` UI to Main's conventions (JSX, axios, `OcrTool`-style polling). Multi-file input (F6), client-side pre-checks for size/type before upload (F10), per-file status badges, confidence panel, **distinct red failure card when `success` is false or HTTP 422** (F3), and a "Download PDF" button driving `/api/export/pdf` → `/status` poll → `/download`.

**Files:**
- Create: `frontend/src/pages/ReconstructionTool.jsx`
- Test: `frontend/src/pages/__tests__/ReconstructionTool.test.jsx`
- Reference (do not modify): `/Users/jay/IndicPDF/frontend/src/App.tsx`

- [x] **Step 1: Write the failing tests**

```jsx
// frontend/src/pages/__tests__/ReconstructionTool.test.jsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ReconstructionTool, { validateFiles } from '../ReconstructionTool';

vi.mock('axios');

describe('validateFiles', () => {
  it('rejects oversized files client-side before upload', () => {
    const big = new File([''], 'big.pdf', { type: 'application/pdf' });
    Object.defineProperty(big, 'size', { value: 26 * 1024 * 1024 });
    const { accepted, rejected } = validateFiles([big]);
    expect(accepted).toHaveLength(0);
    expect(rejected[0].reason).toMatch(/25 MB/);
  });

  it('rejects unsupported extensions and accepts supported ones', () => {
    const exe = new File(['x'], 'tool.exe');
    const pdf = new File(['x'], 'శాసనం.pdf');
    const { accepted, rejected } = validateFiles([exe, pdf]);
    expect(accepted.map((f) => f.name)).toEqual(['శాసనం.pdf']);
    expect(rejected[0].file.name).toBe('tool.exe');
  });

  it('caps at 10 files', () => {
    const files = Array.from({ length: 12 }, (_, i) => new File(['x'], `f${i}.pdf`));
    const { accepted, rejected } = validateFiles(files);
    expect(accepted).toHaveLength(10);
    expect(rejected).toHaveLength(2);
  });
});

describe('ReconstructionTool', () => {
  it('renders dropzone and language selector', () => {
    render(
      <MemoryRouter>
        <ReconstructionTool />
      </MemoryRouter>
    );
    expect(screen.getByText(/Document Reconstruction/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/language/i)).toBeInTheDocument();
  });
});
```

- [x] **Step 2: Run tests to verify they fail**

Run: `cd /Users/jay/IndicPdf-Main/frontend && npx vitest run src/pages/__tests__/ReconstructionTool.test.jsx`
Expected: FAIL — cannot resolve `../ReconstructionTool`

- [x] **Step 3: Implement `frontend/src/pages/ReconstructionTool.jsx`**

```jsx
// frontend/src/pages/ReconstructionTool.jsx
import React, { useState, useCallback, useRef } from 'react';
import axios from 'axios';

const MAX_FILE_BYTES = 25 * 1024 * 1024;
const MAX_FILES = 10;
const SUPPORTED = ['.pdf', '.docx', '.png', '.jpg', '.jpeg', '.tiff', '.tif'];

const LANGUAGES = [
  { value: 'auto', label: 'Auto Detect' },
  { value: 'hindi', label: 'Hindi (Devanagari)' },
  { value: 'telugu', label: 'Telugu' },
  { value: 'tamil', label: 'Tamil' },
  { value: 'bengali', label: 'Bengali' },
  { value: 'gujarati', label: 'Gujarati' },
  { value: 'kannada', label: 'Kannada' },
  { value: 'malayalam', label: 'Malayalam' },
  { value: 'odia', label: 'Odia' },
  { value: 'punjabi', label: 'Punjabi' },
  { value: 'english', label: 'English' },
];

// Client-side pre-check (QA F10): reject before any bytes leave the browser.
export function validateFiles(fileList) {
  const accepted = [];
  const rejected = [];
  for (const file of fileList) {
    const ext = `.${file.name.split('.').pop().toLowerCase()}`;
    if (!SUPPORTED.includes(ext)) {
      rejected.push({ file, reason: `Unsupported type ${ext}` });
    } else if (file.size > MAX_FILE_BYTES) {
      rejected.push({ file, reason: 'Exceeds the 25 MB limit' });
    } else if (accepted.length >= MAX_FILES) {
      rejected.push({ file, reason: `Max ${MAX_FILES} files per batch` });
    } else {
      accepted.push(file);
    }
  }
  return { accepted, rejected };
}

const POLL_MS = 2000;

function ConfidenceBar({ value }) {
  const pct = Math.round((value || 0) * 100);
  const tone = pct >= 90 ? 'bg-green-500' : pct >= 70 ? 'bg-yellow-500' : 'bg-red-500';
  return (
    <div className="flex items-center gap-2">
      <div className="w-32 h-2 rounded bg-gray-200 overflow-hidden">
        <div className={`h-full ${tone}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-sm tabular-nums">{pct}%</span>
    </div>
  );
}

function ResultCard({ item, onExport }) {
  // QA F3: explicit failure state — never render a success-looking panel
  // for processing_incomplete results.
  if (item.status === 'failed') {
    return (
      <div className="border border-red-300 bg-red-50 rounded-lg p-4">
        <p className="font-semibold text-red-700">✗ {item.name} — processing failed</p>
        {item.payload?.quality_assessment?.detected_issues?.map((issue) => (
          <p key={issue} className="text-sm text-red-600 font-mono">{issue}</p>
        ))}
        {item.payload?.quality_assessment?.recommendations?.map((rec) => (
          <p key={rec} className="text-sm text-red-600">{rec}</p>
        ))}
        {!item.payload && <p className="text-sm text-red-600">{item.error}</p>}
      </div>
    );
  }
  if (item.status !== 'done') {
    return (
      <div className="border rounded-lg p-4 flex items-center justify-between">
        <span>{item.name}</span>
        <span className="text-sm text-gray-500 capitalize animate-pulse">{item.status}…</span>
      </div>
    );
  }
  const p = item.payload;
  return (
    <div className="border border-green-300 rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between">
        <p className="font-semibold text-green-700">✓ {item.name}</p>
        <button
          onClick={() => onExport(item)}
          className="px-3 py-1.5 rounded bg-orange-700 text-white text-sm hover:bg-orange-800"
        >
          {item.exporting ? 'Preparing PDF…' : 'Download PDF'}
        </button>
      </div>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <span>Document confidence</span>
        <ConfidenceBar value={p.confidence_scores?.document} />
        <span>Word average</span>
        <ConfidenceBar value={p.confidence_scores?.word_avg} />
        <span>Language</span>
        <span>{p.language_metadata?.detected_language} ({p.language_metadata?.script})</span>
      </div>
      {p.warning_flags?.length > 0 && (
        <p className="text-sm text-yellow-700">⚠ {p.warning_flags.join(', ')}</p>
      )}
      <details>
        <summary className="cursor-pointer text-sm text-gray-600">Reconstructed text</summary>
        <pre className="mt-2 p-3 bg-gray-50 rounded text-sm whitespace-pre-wrap max-h-64 overflow-auto">
          {p.clean_text}
        </pre>
      </details>
    </div>
  );
}

export default function ReconstructionTool() {
  const [items, setItems] = useState([]);
  const [rejectedLocal, setRejectedLocal] = useState([]);
  const [lang, setLang] = useState('auto');
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef();

  const updateItem = (jobId, patch) =>
    setItems((prev) => prev.map((it) => (it.jobId === jobId ? { ...it, ...patch } : it)));

  const pollJob = useCallback((jobId) => {
    const poll = setInterval(async () => {
      try {
        const { data: s } = await axios.get(`/status/${jobId}`);
        if (s.status === 'finished') {
          clearInterval(poll);
          try {
            const { data: payload } = await axios.get(`/api/process/result/${jobId}`);
            updateItem(jobId, { status: payload.success ? 'done' : 'failed', payload });
          } catch (e) {
            // 422 carries the diagnostic payload in the body (QA F3)
            if (e.response?.status === 422) {
              updateItem(jobId, { status: 'failed', payload: e.response.data });
            } else {
              updateItem(jobId, { status: 'failed', error: 'Could not fetch result.' });
            }
          }
        } else if (s.status === 'failed') {
          clearInterval(poll);
          updateItem(jobId, { status: 'failed', error: 'Processing job failed.' });
        }
      } catch {
        clearInterval(poll);
        updateItem(jobId, { status: 'failed', error: 'Lost contact with server.' });
      }
    }, POLL_MS);
  }, []);

  const handleFiles = async (fileList) => {
    const { accepted, rejected } = validateFiles(Array.from(fileList));
    setRejectedLocal(rejected);
    if (!accepted.length) return;

    const formData = new FormData();
    accepted.forEach((f) => formData.append('files', f));
    formData.append('lang', lang);
    try {
      const { data } = await axios.post('/api/process', formData);
      const next = data.jobs.map((j) => ({
        jobId: j.job_id,
        name: j.original_name,
        status: j.job_id ? 'processing' : 'failed',
        error: j.detail,
      }));
      setItems(next);
      next.filter((it) => it.jobId).forEach((it) => pollJob(it.jobId));
    } catch (e) {
      setRejectedLocal([
        { file: { name: 'upload' }, reason: e.response?.data?.detail || 'Upload failed.' },
      ]);
    }
  };

  const handleExport = async (item) => {
    updateItem(item.jobId, { exporting: true });
    try {
      const { data } = await axios.post('/api/export/pdf', {
        clean_text: item.payload.clean_text,
        filename: item.name,
      });
      const poll = setInterval(async () => {
        const { data: s } = await axios.get(`/status/${data.job_id}`);
        if (s.status === 'finished') {
          clearInterval(poll);
          updateItem(item.jobId, { exporting: false });
          window.location.href = `/download/${data.job_id}`;
        } else if (s.status === 'failed') {
          clearInterval(poll);
          updateItem(item.jobId, { exporting: false, error: 'PDF export failed.' });
        }
      }, POLL_MS);
    } catch (e) {
      updateItem(item.jobId, {
        exporting: false,
        error: e.response?.data?.detail || 'PDF export failed.',
      });
    }
  };

  return (
    <div className="max-w-3xl mx-auto px-4 py-10 space-y-6">
      <h1 className="text-3xl font-bold">Document Reconstruction</h1>
      <p className="text-gray-600">
        Confidence-scored text extraction for Indic-script PDFs, scans, and DOCX.
        Up to {MAX_FILES} files, 25 MB each.
      </p>

      <label className="block text-sm font-medium" htmlFor="recon-lang">Language</label>
      <select
        id="recon-lang"
        value={lang}
        onChange={(e) => setLang(e.target.value)}
        className="border rounded px-3 py-2"
      >
        {LANGUAGES.map((l) => (
          <option key={l.value} value={l.value}>{l.label}</option>
        ))}
      </select>

      <div
        onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files); }}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition
          ${dragOver ? 'border-orange-600 bg-orange-50' : 'border-gray-300'}`}
      >
        <p>Drop files here or click to browse</p>
        <p className="text-sm text-gray-500">{SUPPORTED.join(' ')}</p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.png,.jpg,.jpeg,.tiff,.tif"
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      {rejectedLocal.length > 0 && (
        <div className="border border-yellow-300 bg-yellow-50 rounded-lg p-3 text-sm">
          {rejectedLocal.map((r, i) => (
            <p key={i}>⚠ {r.file.name}: {r.reason}</p>
          ))}
        </div>
      )}

      <div className="space-y-3">
        {items.map((item) => (
          <ResultCard key={item.jobId || item.name} item={item} onExport={handleExport} />
        ))}
      </div>
    </div>
  );
}
```

- [x] **Step 4: Run tests**

Run: `cd /Users/jay/IndicPdf-Main/frontend && npx vitest run src/pages/__tests__/ReconstructionTool.test.jsx`
Expected: 4 PASSED

- [x] **Step 5: Commit**

```bash
cd /Users/jay/IndicPdf-Main
git add frontend/src/pages/ReconstructionTool.jsx frontend/src/pages/__tests__/ReconstructionTool.test.jsx
git commit -m "feat: ReconstructionTool page with multi-file upload and failure states (QA F3, F6, F10)"
```

---

### Task 8: Wire route + navigation

**Files:**
- Modify: `frontend/src/App.jsx` (import + route, follow the lazy-import pattern used by the other pages)
- Modify: `frontend/src/components/Navbar.jsx` (nav link next to the existing OCR link)

- [x] **Step 1: Add the route**

In `frontend/src/App.jsx`, add with the other page imports (match the existing import style — check whether pages there use `React.lazy`; mirror it):

```jsx
import ReconstructionTool from './pages/ReconstructionTool';
```

Add inside `<Routes>` after the `/ocr` route (App.jsx:72):

```jsx
              <Route path="/reconstruct" element={<ReconstructionTool />} />
```

- [x] **Step 2: Add the Navbar link**

In `frontend/src/components/Navbar.jsx`, locate the existing OCR link (grep for `"/ocr"`) and add beside it, matching the surrounding element's classes exactly:

```jsx
<Link to="/reconstruct" className={/* same classes as the OCR link */}>Reconstruct</Link>
```

(Replace the comment with the literal class string copied from the adjacent OCR link — this is a copy-the-sibling edit, both desktop and mobile menu sections if Navbar has both.)

- [x] **Step 3: Verify the build**

Run: `cd /Users/jay/IndicPdf-Main/frontend && npm run build`
Expected: build succeeds, no unresolved imports

- [x] **Step 4: Commit**

```bash
cd /Users/jay/IndicPdf-Main
git add frontend/src/App.jsx frontend/src/components/Navbar.jsx
git commit -m "feat: wire /reconstruct route and nav link"
```

---

### Task 9: Dependencies + Docker

The engine needs `pdf2image` (Python) and `poppler-utils` (system) for the PDF path. Tesseract + language packs are already in the Dockerfile (lines 27–37).

**Files:**
- Modify: `requirements.txt`
- Modify: `Dockerfile`

- [x] **Step 1: Check what's already present**

Run: `grep -E "pdf2image|Pillow|pytest-asyncio" /Users/jay/IndicPdf-Main/requirements.txt; grep "poppler" /Users/jay/IndicPdf-Main/Dockerfile`

- [x] **Step 2: Add anything missing**

To `requirements.txt` (only the lines the grep did not find):

```
pdf2image
Pillow
pytest-asyncio
```

To the Dockerfile apt-get block (after `tesseract-ocr-san \`, Dockerfile:37), if missing:

```dockerfile
    poppler-utils \
```

- [x] **Step 3: Verify install resolves**

Run: `cd /Users/jay/IndicPdf-Main && pip install -r requirements.txt --dry-run`
Expected: resolves without conflicts

- [x] **Step 4: Commit**

```bash
cd /Users/jay/IndicPdf-Main
git add requirements.txt Dockerfile
git commit -m "chore: add pdf2image/poppler deps for reconstruction engine"
```

---

### Task 10: End-to-end verification + donor repo retirement

- [x] **Step 1: Full backend test suite**

Run: `cd /Users/jay/IndicPdf-Main && python -m pytest tests/ -v --ignore=tests/stress_test.py --ignore=tests/memory_stress.py`
Expected: all green (pre-existing failures, if any, noted but not introduced by this work — compare against `git stash` baseline if unsure)

- [x] **Step 2: Frontend test suite + build**

Run: `cd /Users/jay/IndicPdf-Main/frontend && npx vitest run && npm run build`
Expected: all green, build succeeds

- [x] **Step 3: Live smoke test (needs Redis + worker running)**

```bash
cd /Users/jay/IndicPdf-Main
# terminal 1: redis-server
# terminal 2: python backend/worker.py
# terminal 3: uvicorn backend.main:app --port 8000
# then:
python - <<'EOF'
import io, time, zipfile, requests

# Build a Telugu docx in memory
buf = io.BytesIO()
doc = ('<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
       '<w:body><w:p><w:r><w:t>తెలుగు పరీక్ష పత్రం</w:t></w:r></w:p></w:body></w:document>')
with zipfile.ZipFile(buf, "w") as zf:
    zf.writestr("word/document.xml", doc)

# 1. multi-file process with an Indic filename (F1+F6 in one shot)
r = requests.post("http://localhost:8000/api/process",
                  files=[("files", ("తెలుగు-పత్రం.docx", buf.getvalue()))])
r.raise_for_status()
job_id = r.json()["jobs"][0]["job_id"]
for _ in range(30):
    if requests.get(f"http://localhost:8000/status/{job_id}").json()["status"] == "finished":
        break
    time.sleep(1)

# 2. result has success flag + real confidences (F3)
result = requests.get(f"http://localhost:8000/api/process/result/{job_id}")
assert result.status_code == 200, result.text
payload = result.json()
assert payload["success"] and "తెలుగు" in payload["clean_text"]

# 3. export with Indic filename must NOT 500 (F1)
r = requests.post("http://localhost:8000/api/export/pdf",
                  json={"clean_text": payload["clean_text"], "filename": "తెలుగు-పత్రం.docx"})
r.raise_for_status()
export_id = r.json()["job_id"]
for _ in range(30):
    if requests.get(f"http://localhost:8000/status/{export_id}").json()["status"] == "finished":
        break
    time.sleep(1)
dl = requests.get(f"http://localhost:8000/download/{export_id}")
assert dl.status_code == 200 and dl.content[:4] == b"%PDF", dl.status_code

# 4. corrupt docx → 422 with diagnostics, not false success (F3)
r = requests.post("http://localhost:8000/api/process",
                  files=[("files", ("bad.docx", b"PK\x03\x04 not really a zip"))])
bad_id = r.json()["jobs"][0]["job_id"]
for _ in range(30):
    if requests.get(f"http://localhost:8000/status/{bad_id}").json()["status"] == "finished":
        break
    time.sleep(1)
bad = requests.get(f"http://localhost:8000/api/process/result/{bad_id}")
assert bad.status_code == 422 and bad.json()["success"] is False

print("E2E SMOKE: ALL PASS")
EOF
```

Expected: `E2E SMOKE: ALL PASS`

- [x] **Step 4: Update QA report change log**

Append to `/Users/jay/IndicPDF/docs/QA_REPORT_v1.md` §6:

```markdown
- **v1.1 (2026-06-10):** v2 scaffold merged into IndicPdf-Main
  (`docs/superpowers/plans/2026-06-10-v2-engine-integration.md`).
  F1–F8 addressed in the integrated codebase; this repo is retired as a donor.
```

Also copy the report into the host repo: `cp /Users/jay/IndicPDF/docs/QA_REPORT_v1.md /Users/jay/IndicPdf-Main/docs/QA_REPORT_v1.md` and commit.

- [x] **Step 5: Mark the donor repo retired**

Create `/Users/jay/IndicPDF/RETIRED.md`:

```markdown
# Repository retired — 2026-06-10

This v2 scaffold was merged into `/Users/jay/IndicPdf-Main`
(engine → `backend/reconstruction_engine.py`, pipeline → `/api/process`,
export → `/api/export/pdf`, UI → `frontend/src/pages/ReconstructionTool.jsx`).
Do not develop here. See
`IndicPdf-Main/docs/superpowers/plans/2026-06-10-v2-engine-integration.md`.
```

- [x] **Step 6: Final commit**

```bash
cd /Users/jay/IndicPdf-Main
git add docs/QA_REPORT_v1.md
git commit -m "docs: import QA report and record v2 integration"
```

---

## Out of scope (explicitly deferred)

- **PaddleOCR hybrid pass** — dropped for RAM budget (Render Starter 512 MB). The engine's `engine` field on segments keeps the door open; re-add as an optional pass when infra allows.
- **WeasyPrint report-style export** (donor's `pdf_template.html` with correction-trace tables) — the fpdf2 path exports clean text only. Port the template later if report formatting is wanted.
- **Word/line confidence in DOCX path** — DOCX text is exact (0.99 fixed), per the donor's behavior.
- **Pre-existing Main issues not in the QA report** (e.g. `/ocr` endpoint buffers via `file.read()` instead of `secure_file_upload`; `process_ocr` worker output is unencrypted) — worth a follow-up, not blocking this integration.
