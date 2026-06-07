"""
One-time script to download OFL-licensed Google Fonts + Lohit fonts
for the top 10 Indian language scripts.

Usage:
    python scripts/download_indic_fonts.py
    python scripts/download_indic_fonts.py --lang Bengali  # single language

Fonts are saved to fonts/system/LANGUAGE/. Existing files are skipped.
"""
import re
import sys
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

# Lohit fonts — GitHub release direct TTF URLs (OFL)
LOHIT_FONTS = {
    "Bengali":   "https://github.com/nicowillis/lohit-fonts/raw/main/lohit-bengali/Lohit-Bengali.ttf",
    "Tamil":     "https://github.com/nicowillis/lohit-fonts/raw/main/lohit-tamil/Lohit-Tamil.ttf",
    "Telugu":    "https://github.com/nicowillis/lohit-fonts/raw/main/lohit-telugu/Lohit-Telugu.ttf",
    "Gujarati":  "https://github.com/nicowillis/lohit-fonts/raw/main/lohit-gujarati/Lohit-Gujarati.ttf",
    "Kannada":   "https://github.com/nicowillis/lohit-fonts/raw/main/lohit-kannada/Lohit-Kannada.ttf",
    "Malayalam": "https://github.com/nicowillis/lohit-fonts/raw/main/lohit-malayalam/Lohit-Malayalam.ttf",
    "Odia":      "https://github.com/nicowillis/lohit-fonts/raw/main/lohit-odia/Lohit-Odia.ttf",
    "Marathi":   "https://github.com/nicowillis/lohit-fonts/raw/main/lohit-devanagari/Lohit-Devanagari.ttf",
}


def get_font_urls(family: str) -> list:
    """Fetch all TTF download URLs for a Google Fonts family via the CSS API."""
    url = f"https://fonts.googleapis.com/css2?family={family.replace(' ', '+')}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
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


def download_lohit_font(lang: str, url: str) -> None:
    """Download a single Lohit font file."""
    folder = FONTS_BASE / lang
    folder.mkdir(parents=True, exist_ok=True)
    filename = url.split("/")[-1]
    try:
        download_font(url, folder / filename)
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
            download_lohit_font(lang, LOHIT_FONTS[lang])

    print("\n✓ Done. Drop proprietary fonts (Kruti Dev, Nirmala UI etc.) manually.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download Indic fonts from Google Fonts + Lohit")
    parser.add_argument("--lang", nargs="*", help="Languages to download (default: all)")
    args = parser.parse_args()
    main(args.lang)
