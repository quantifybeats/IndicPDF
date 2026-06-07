import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

def test_lang_map_contains_all_indic_languages():
    from ocr_processor import LANG_MAP
    required = ["hindi","telugu","tamil","bengali","gujarati","kannada","malayalam","odia","punjabi","english","auto"]
    for lang in required:
        assert lang in LANG_MAP, f"Missing language: {lang}"

def test_lang_map_auto_returns_none():
    from ocr_processor import LANG_MAP
    assert LANG_MAP["auto"] is None

def test_ocr_image_to_text_calls_tesseract(tmp_path):
    img_path = tmp_path / "sample.png"
    img_path.write_bytes(b"fake png data")
    with patch("ocr_processor.Image") as mock_image, patch("ocr_processor.pytesseract") as mock_tess:
        mock_img = MagicMock()
        mock_image.open.return_value = mock_img
        mock_tess.image_to_string.return_value = "extracted text"
        from ocr_processor import ocr_image_to_text
        result = ocr_image_to_text(str(img_path), lang="hindi")
    mock_image.open.assert_called_once_with(str(img_path))
    mock_tess.image_to_string.assert_called_once_with(mock_img, lang="hin")
    assert result == "extracted text"

def test_ocr_image_to_text_auto_uses_multi_lang(tmp_path):
    img_path = tmp_path / "sample.png"
    img_path.write_bytes(b"fake png data")
    with patch("ocr_processor.Image") as mock_image, patch("ocr_processor.pytesseract") as mock_tess:
        mock_image.open.return_value = MagicMock()
        mock_tess.image_to_string.return_value = "text"
        from ocr_processor import ocr_image_to_text
        ocr_image_to_text(str(img_path), lang="auto")
    call_lang = mock_tess.image_to_string.call_args[1]["lang"]
    assert "hin" in call_lang
    assert "eng" in call_lang

def test_ocr_pdf_to_text_processes_each_page(tmp_path):
    pdf_path = tmp_path / "scan.pdf"
    pdf_path.write_bytes(b"fake pdf")
    mock_images = [MagicMock(), MagicMock()]
    with patch("ocr_processor.convert_from_path", return_value=mock_images) as mock_convert, \
         patch("ocr_processor.pytesseract") as mock_tess:
        mock_tess.image_to_string.side_effect = ["page 1 text", "page 2 text"]
        from ocr_processor import ocr_pdf_to_text
        result = ocr_pdf_to_text(str(pdf_path), lang="telugu")
    mock_convert.assert_called_once_with(str(pdf_path), dpi=300)
    assert mock_tess.image_to_string.call_count == 2
    assert "page 1 text" in result
    assert "page 2 text" in result
    assert "Page Break" in result

def test_unsupported_lang_falls_back_to_english():
    with patch("ocr_processor.Image") as mock_image, patch("ocr_processor.pytesseract") as mock_tess:
        mock_image.open.return_value = MagicMock()
        mock_tess.image_to_string.return_value = "text"
        from ocr_processor import ocr_image_to_text
        ocr_image_to_text("/fake/path.png", lang="klingon")
    call_lang = mock_tess.image_to_string.call_args[1]["lang"]
    assert call_lang == "eng"
