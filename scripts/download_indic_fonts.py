"""
One-time script to download OFL-licensed Google Fonts + Lohit fonts
for the top 10 Indian language scripts.

Usage:
    python scripts/download_indic_fonts.py
    python scripts/download_indic_fonts.py --lang Bengali  # single language

Fonts are saved to fonts/system/LANGUAGE/. Existing files are skipped.
"""
import io
import re
import sys
import tarfile
import argparse
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Install requests: pip install requests")

FONTS_BASE = Path(__file__).parent.parent / "fonts" / "system"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Legacy User-Agent to get TTF (not WOFF2) from Google Fonts CSS API
FONTS_CSS_HEADERS = {
    "User-Agent": "Mozilla/4.0 (compatible)"
}

# Google Fonts families per language (all OFL-licensed)
LANGUAGE_FONTS = {
    "Bengali": {
        "script": "bengali",
        "families": [
            "Noto Sans Bengali",
            "Noto Serif Bengali",
            "Hind Siliguri",
            "Baloo Da 2",
            "Tiro Bangla",
            "Kalam",
            "Mukta Mahee",
        ],
    },
    "Tamil": {
        "script": "tamil",
        "families": [
            "Noto Sans Tamil",
            "Noto Serif Tamil",
            "Hind Madurai",
            "Baloo Thambi 2",
            "Tiro Tamil",
            "Arima",
        ],
    },
    "Marathi": {
        "script": "devanagari",
        "families": [
            "Noto Sans Devanagari",
            "Noto Serif Devanagari",
            "Tiro Devanagari Marathi",
            "Baloo 2",
        ],
    },
    "Gujarati": {
        "script": "gujarati",
        "families": [
            "Noto Sans Gujarati",
            "Noto Serif Gujarati",
            "Hind Vadodara",
            "Rasa",
            "Baloo Bhai 2",
        ],
    },
    "Kannada": {
        "script": "kannada",
        "families": [
            "Noto Sans Kannada",
            "Noto Serif Kannada",
            "Hind Mysuru",
            "Baloo Tamma 2",
            "Tiro Kannada",
        ],
    },
    "Malayalam": {
        "script": "malayalam",
        "families": [
            "Noto Sans Malayalam",
            "Noto Serif Malayalam",
            "Baloo Chettan 2",
            "Chilanka",
            "Gayathri",
            "Manjari",
        ],
    },
    "Odia": {
        "script": "oriya",
        "families": [
            "Noto Sans Oriya",
            "Noto Serif Oriya",
            "Baloo Bhaina 2",
        ],
    },
    "Urdu": {
        "script": "arabic",
        "families": [
            "Noto Nastaliq Urdu",
            "Noto Sans Arabic",
        ],
    },
}

# Lohit fonts — official pagure.io tarball releases (OFL-licensed)
# Each value is (tarball_url, ttf_filename_inside_tarball)
LOHIT_FONTS = {
    "Bengali":   ("https://releases.pagure.org/lohit/lohit-bengali-ttf-2.91.5.tar.gz",   "Lohit-Bengali.ttf"),
    "Tamil":     ("https://releases.pagure.org/lohit/lohit-tamil-ttf-2.91.3.tar.gz",     "Lohit-Tamil.ttf"),
    "Marathi":   ("https://releases.pagure.org/lohit/lohit-devanagari-ttf-2.95.4.tar.gz","Lohit-Devanagari.ttf"),
    "Gujarati":  ("https://releases.pagure.org/lohit/lohit-gujarati-ttf-2.92.4.tar.gz",  "Lohit-Gujarati.ttf"),
    "Kannada":   ("https://releases.pagure.org/lohit/lohit-kannada-ttf-2.5.4.tar.gz",    "Lohit-Kannada.ttf"),
    "Malayalam": ("https://releases.pagure.org/lohit/lohit-malayalam-ttf-2.92.2.tar.gz", "Lohit-Malayalam.ttf"),
    "Odia":      ("https://releases.pagure.org/lohit/lohit-odia-ttf-2.91.2.tar.gz",      "Lohit-Odia.ttf"),
}


def get_font_urls(family: str) -> list:
    """Fetch all TTF download URLs for a Google Fonts family via the CSS API."""
    # Use css v1 API with legacy UA to get TTF (not WOFF2) URLs
    url = f"https://fonts.googleapis.com/css?family={family.replace(' ', '+')}"
    resp = requests.get(url, headers=FONTS_CSS_HEADERS, timeout=15)
    resp.raise_for_status()
    return re.findall(
        r'url\((https://fonts\.gstatic\.com/[^)]+\.ttf)\)', resp.text
    )


def download_font(url: str, dest: Path) -> bool:
    """Download a single font file. Returns True if downloaded, False if skipped."""
    if dest.exists():
        return False
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    print(f"    ✓ {dest.name}")
    return True


def download_language_fonts(lang: str, config: dict) -> None:
    """Download all Google Fonts families for one language."""
    folder = FONTS_BASE / lang
    folder.mkdir(parents=True, exist_ok=True)

    for family in config["families"]:
        try:
            urls = get_font_urls(family)
            if not urls:
                print(f"    ⚠ No TTF URLs found for: {family}")
                continue
            for url in urls:
                filename = url.split("/")[-1].split("?")[0]
                download_font(url, folder / filename)
        except requests.exceptions.RequestException as exc:
            print(f"    ✗ SKIP {family}: {exc}")


def download_lohit_font(lang: str, tarball_url: str, ttf_name: str) -> None:
    """Download a Lohit font tarball and extract the TTF file."""
    folder = FONTS_BASE / lang
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / ttf_name
    if dest.exists():
        return
    try:
        resp = requests.get(tarball_url, headers=HEADERS, timeout=60)
        resp.raise_for_status()
        with tarfile.open(fileobj=io.BytesIO(resp.content), mode="r:gz") as tar:
            for member in tar.getmembers():
                if member.name.endswith(ttf_name):
                    f = tar.extractfile(member)
                    if f:
                        dest.write_bytes(f.read())
                        print(f"    ✓ {ttf_name}")
                        return
        print(f"    ⚠ {ttf_name} not found in tarball")
    except requests.exceptions.RequestException as exc:
        print(f"    ✗ SKIP Lohit-{lang}: {exc}")


def main(langs: list[str] | None = None) -> None:
    target_langs = langs or list(LANGUAGE_FONTS.keys())

    print("\n=== Downloading Google Fonts ===")
    for lang in target_langs:
        if lang not in LANGUAGE_FONTS:
            print(f"Unknown language: {lang}. Valid: {list(LANGUAGE_FONTS.keys())}")
            continue
        print(f"\n[{lang}]")
        download_language_fonts(lang, LANGUAGE_FONTS[lang])

    print("\n=== Downloading Lohit Fonts ===")
    for lang in target_langs:
        if lang in LOHIT_FONTS:
            print(f"\n[{lang} — Lohit]")
            tarball_url, ttf_name = LOHIT_FONTS[lang]
            download_lohit_font(lang, tarball_url, ttf_name)

    print("\n✓ Done. Drop proprietary fonts (Kruti Dev, Nirmala UI etc.) manually.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download Indic fonts from Google Fonts + Lohit")
    parser.add_argument("--lang", nargs="*", help="Languages to download (default: all)")
    args = parser.parse_args()
    main(args.lang)
