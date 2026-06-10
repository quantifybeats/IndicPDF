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
    monkeypatch.setattr(re_mod, "_pdf_to_images", lambda path: [object()])

    result = engine.process_path(tmp_path / "scan.pdf", original_filename="scan.pdf")
    assert not result.success
    assert "ocr_dependency_missing" in result.detected_issues
    assert "pdf_ocr_returned_no_text" not in result.detected_issues
