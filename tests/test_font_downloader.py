# tests/test_font_downloader.py
import pytest
from unittest.mock import patch, MagicMock, call
from pathlib import Path
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))


def test_get_font_urls_extracts_ttf_links():
    css = """
    @font-face {
      font-family: 'Noto Sans Bengali';
      src: url(https://fonts.gstatic.com/s/notosansbengali/v1/Cn-sJsCFTjPRb8Cq1GfDRgMZoGNMk.ttf) format('truetype');
    }
    @font-face {
      font-family: 'Noto Sans Bengali';
      src: url(https://fonts.gstatic.com/s/notosansbengali/v1/Cn-sJsCFTjPRb8Cq1GfDRgMZoGNMk-Bold.ttf) format('truetype');
    }
    """
    mock_resp = MagicMock()
    mock_resp.text = css
    mock_resp.raise_for_status = lambda: None

    with patch('requests.get', return_value=mock_resp):
        from download_indic_fonts import get_font_urls
        urls = get_font_urls("Noto Sans Bengali")

    assert len(urls) == 2
    assert all("fonts.gstatic.com" in u for u in urls)
    assert all(u.endswith(".ttf") for u in urls)


def test_download_font_skips_existing_file(tmp_path):
    dest = tmp_path / "existing.ttf"
    dest.write_bytes(b"already here")

    with patch('requests.get') as mock_get:
        from download_indic_fonts import download_font
        download_font("https://fonts.gstatic.com/s/test.ttf", dest)

    mock_get.assert_not_called()
    assert dest.read_bytes() == b"already here"


def test_download_font_saves_new_file(tmp_path):
    dest = tmp_path / "new_font.ttf"
    mock_resp = MagicMock()
    mock_resp.content = b"font binary data"
    mock_resp.raise_for_status = lambda: None

    with patch('requests.get', return_value=mock_resp):
        from download_indic_fonts import download_font
        download_font("https://fonts.gstatic.com/s/new.ttf", dest)

    assert dest.exists()
    assert dest.read_bytes() == b"font binary data"


def test_get_font_urls_handles_http_error():
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = Exception("404 Not Found")

    with patch('requests.get', return_value=mock_resp):
        from download_indic_fonts import get_font_urls
        with pytest.raises(Exception, match="404"):
            get_font_urls("Nonexistent Font Family")


def test_download_language_fonts_creates_folder_and_downloads(tmp_path):
    css = "src: url(https://fonts.gstatic.com/s/test/v1/TestFont.ttf) format('truetype');"
    css_resp = MagicMock()
    css_resp.text = css
    css_resp.raise_for_status = lambda: None

    font_resp = MagicMock()
    font_resp.content = b"ttf data"
    font_resp.raise_for_status = lambda: None

    with patch('requests.get', side_effect=[css_resp, font_resp]):
        import download_indic_fonts as m
        original_base = m.FONTS_BASE
        m.FONTS_BASE = tmp_path
        m.download_language_fonts("Bengali", {"families": ["Noto Sans Bengali"]})
        m.FONTS_BASE = original_base

    assert (tmp_path / "Bengali").is_dir()
    assert (tmp_path / "Bengali" / "TestFont.ttf").exists()
