"""Regression: /analyse-pdf-quality must not report broken-ToUnicode PDFs as
healthy. A corrupt ToUnicode CMap gives the page a text layer made of one
repeated wrong akshara ('సససస'), so the old `has_text` check called it
"Searchable" / "Ready for publishing". The analyzer now runs the garbage
detector and flags the corrupt text layer with an OCR recommendation instead.
"""
import io
import sys
from pathlib import Path

import pytest
from fpdf import FPDF
from fpdf.enums import XPos, YPos

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from font_manager import font_registry, initialize_font_registry  # noqa: E402
import main as backend_main  # noqa: E402

initialize_font_registry()

REAL_TELUGU = ("సత్యాన్వేషణ మరియు ఆత్మవిచారణ దైనందిన జీవితంలో ఎలా "
               "చేరుకోవాలి అనేది ముఖ్యమైన ప్రశ్న అని పెద్దలు చెబుతారు")


class FakeUpload:
    """Minimal async stand-in for fastapi.UploadFile."""

    def __init__(self, data: bytes, filename: str):
        self._buf = io.BytesIO(data)
        self.filename = filename

    async def read(self, n: int = -1) -> bytes:
        return self._buf.read(n)


def _telugu_font_path():
    return str(font_registry.get_font_metadata("Noto Sans Telugu").path)


def _garbage_pdf_bytes() -> bytes:
    pdf = FPDF()
    pdf.add_font("nt", "", _telugu_font_path())
    pdf.set_font("nt", size=16)
    pdf.add_page()
    for _ in range(20):
        pdf.cell(0, 10, "స" * 30, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    return bytes(pdf.output())


def _real_pdf_bytes() -> bytes:
    pdf = FPDF()
    pdf.add_font("nt", "", _telugu_font_path())
    pdf.set_font("nt", size=16)
    pdf.add_page()
    for line in REAL_TELUGU.split("మరియు"):
        pdf.cell(0, 10, line.strip(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    return bytes(pdf.output())


async def test_garbage_pdf_flagged_as_corrupt():
    result = await backend_main.analyse_pdf_quality(
        FakeUpload(_garbage_pdf_bytes(), "garbage.pdf"))
    assert result["text"] == "Corrupt text layer (broken ToUnicode)"
    assert any("OCR" in w for w in result["warnings"]), result["warnings"]
    assert int(result["score"].split("/")[0]) < 100


async def test_real_pdf_reported_searchable():
    result = await backend_main.analyse_pdf_quality(
        FakeUpload(_real_pdf_bytes(), "real.pdf"))
    assert result["text"] == "Searchable"
    assert not any("OCR" in w for w in result["warnings"]), result["warnings"]
