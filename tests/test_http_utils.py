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
