import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from http_utils import content_disposition


def test_indic_original_stem_does_not_crash_header_encoding():
    # The exact pattern /download builds: "IndicPDF_" + user stem + suffix
    for stem in ("నివేదిక", "पत्रं", "தமிழ்-ஆவணம்"):
        header = content_disposition(f"IndicPDF_{stem}.pdf")
        header.encode("latin-1")  # would raise UnicodeEncodeError pre-fix
