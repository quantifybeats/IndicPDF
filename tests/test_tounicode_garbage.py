"""Regression: PDF->DOCX must not silently emit broken-ToUnicode garbage.

Some source PDFs ship a corrupt ToUnicode CMap where every glyph maps to the
same (or a tiny set of) wrong code point — extraction yields 'సససససస',
'తెతెతెతె', 'नननन'. These are valid Indic code points, so they survive NFC and
junk-stripping and get written to the DOCX as a wall of one repeated character.
Text extraction cannot recover them (only OCR or fixing the source can), so the
converter must DETECT this signature and fail loudly with an actionable message
instead of producing a confidently-wrong file.
"""
import sys
from pathlib import Path

import pytest
from docx import Document
from fpdf import FPDF
from fpdf.enums import XPos, YPos

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from font_manager import font_registry, initialize_font_registry  # noqa: E402
import pdf_processor as pp  # noqa: E402

initialize_font_registry()

# A real Telugu paragraph: many distinct aksharas, no single char dominates.
REAL_TELUGU = ("సత్యాన్వేషణ మరియు ఆత్మవిచారణ దైనందిన జీవితంలో ఎలా "
               "చేరుకోవాలి అనేది ముఖ్యమైన ప్రశ్న అని పెద్దలు చెబుతారు")


class TestGarbageDetector:
    def test_single_char_repeat_is_garbage(self):
        # every glyph -> 'స'
        assert pp._is_tounicode_garbage("స" * 60) is True

    def test_bigram_repeat_is_garbage(self):
        # every glyph -> 'తె' (base + vowel sign): distinct chars {త, ె}
        assert pp._is_tounicode_garbage("తె" * 40) is True

    def test_devanagari_single_char_repeat_is_garbage(self):
        assert pp._is_tounicode_garbage("न" * 60) is True

    def test_mixed_latin_and_garbage_indic_is_garbage(self):
        # Real-world case (IndicPDF_test_devanagari.pdf): broken Hindi 'नननन'
        # diluted by English. The Indic portion is still unrecoverable, so a
        # whole-document character count must not let the Latin hide it.
        text = ("The quick brown fox jumps over the lazy dog in this test "
                "document sample " + "न" * 27)
        assert pp._is_tounicode_garbage(text) is True

    def test_real_telugu_is_not_garbage(self):
        assert pp._is_tounicode_garbage(REAL_TELUGU) is False

    def test_long_real_telugu_is_not_garbage(self):
        # Guard against the "long real document drives distinct-ratio low" trap:
        # a big real document still has many distinct aksharas and no dominant char.
        assert pp._is_tounicode_garbage(REAL_TELUGU * 50) is False

    def test_latin_repeat_is_not_flagged(self):
        # Latin is not affected by this bug and must keep the fast path untouched.
        assert pp._is_tounicode_garbage("a" * 100) is False

    def test_short_indic_text_is_not_garbage(self):
        # Too short to judge — a legitimately repetitive short string must pass.
        assert pp._is_tounicode_garbage("తెలుగు") is False

    def test_empty_is_not_garbage(self):
        assert pp._is_tounicode_garbage("") is False
        assert pp._is_tounicode_garbage("   \n  ") is False


def _telugu_font_path():
    return str(font_registry.get_font_metadata("Noto Sans Telugu").path)


def _build_garbage_pdf(path: Path):
    """A PDF whose visible text layer is one Telugu char repeated per line —
    the broken-ToUnicode signature."""
    pdf = FPDF()
    pdf.add_font("nt", "", _telugu_font_path())
    pdf.set_font("nt", size=16)
    pdf.add_page()
    for _ in range(20):
        pdf.cell(0, 10, "స" * 30, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.output(str(path))


def _build_real_pdf(path: Path):
    pdf = FPDF()
    pdf.add_font("nt", "", _telugu_font_path())
    pdf.set_font("nt", size=16)
    pdf.add_page()
    for line in REAL_TELUGU.split("మరియు"):
        pdf.cell(0, 10, line.strip(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.output(str(path))


class TestProcessPdfRaisesOnGarbage:
    def test_garbage_pdf_raises(self, tmp_path):
        src = tmp_path / "garbage.pdf"
        out = tmp_path / "out.docx"
        _build_garbage_pdf(src)
        with pytest.raises(pp.ToUnicodeGarbageError):
            pp.process_pdf_to_docx(src, out)

    def test_real_pdf_does_not_raise(self, tmp_path):
        src = tmp_path / "real.pdf"
        out = tmp_path / "out.docx"
        _build_real_pdf(src)
        report = pp.process_pdf_to_docx(src, out)
        assert report["status"] == "success"
        assert out.exists()
