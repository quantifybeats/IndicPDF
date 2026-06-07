# Track B — Indic Font Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Write a one-time Python script that downloads all OFL-licensed Google Fonts and Lohit fonts for 8 new Indian language folders, supplementing existing bundled fonts.

**Architecture:** A standalone CLI script (`scripts/download_indic_fonts.py`) fetches TTF URLs from the Google Fonts CSS API (no API key needed) and Lohit GitHub releases, saves files into `fonts/system/LANGUAGE/`, and skips files that already exist. FontRegistry already scans these folders on startup — no backend code changes needed.

**Tech Stack:** Python 3, `requests`, Google Fonts CSS API, GitHub releases (Lohit)

---

## File Map

| Action | Path |
|---|---|
| Create | `scripts/download_indic_fonts.py` |
| Create | `tests/test_font_downloader.py` |
| Create dirs | `fonts/system/Bengali/`, `Tamil/`, `Marathi/`, `Gujarati/`, `Kannada/`, `Malayalam/`, `Odia/`, `Urdu/` |

---

### Task 1: Create language font folders

**Files:**
- Create dirs: `fonts/system/Bengali/`, `fonts/system/Tamil/`, `fonts/system/Marathi/`, `fonts/system/Gujarati/`, `fonts/system/Kannada/`, `fonts/system/Malayalam/`, `fonts/system/Odia/`, `fonts/system/Urdu/`

- [ ] **Step 1: Create the folders with placeholder .gitkeep files**

```bash
mkdir -p fonts/system/Bengali fonts/system/Tamil fonts/system/Marathi \
         fonts/system/Gujarati fonts/system/Kannada fonts/system/Malayalam \
         fonts/system/Odia fonts/system/Urdu
touch fonts/system/Bengali/.gitkeep fonts/system/Tamil/.gitkeep \
      fonts/system/Marathi/.gitkeep fonts/system/Gujarati/.gitkeep \
      fonts/system/Kannada/.gitkeep fonts/system/Malayalam/.gitkeep \
      fonts/system/Odia/.gitkeep fonts/system/Urdu/.gitkeep
```

- [ ] **Step 2: Commit**

```bash
git add fonts/system/
git commit -m "feat: add empty language font folders for 8 new Indic scripts"
```

---

### Task 2: Write failing tests for the download script

**Files:**
- Create: `tests/test_font_downloader.py`

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run tests — expect ImportError (module not yet created)**

```bash
cd /Users/jay/IndicPdf-Main
python -m pytest tests/test_font_downloader.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'download_indic_fonts'`

---

### Task 3: Implement the download script

**Files:**
- Create: `scripts/download_indic_fonts.py`

- [ ] **Step 1: Write the full script**

```python
# scripts/download_indic_fonts.py
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
import requests
from pathlib import Path

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
        except Exception as exc:
            print(f"    ✗ SKIP {family}: {exc}")


def download_lohit_font(lang: str, url: str) -> None:
    """Download a single Lohit font file."""
    folder = FONTS_BASE / lang
    folder.mkdir(parents=True, exist_ok=True)
    filename = url.split("/")[-1]
    try:
        download_font(url, folder / filename)
    except Exception as exc:
        print(f"    ✗ SKIP Lohit-{lang}: {exc}")


def main(langs: list = None) -> None:
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
```

- [ ] **Step 2: Run the tests**

```bash
cd /Users/jay/IndicPdf-Main
python -m pytest tests/test_font_downloader.py -v
```

Expected: All 5 tests PASS

- [ ] **Step 3: Commit the script**

```bash
git add scripts/download_indic_fonts.py tests/test_font_downloader.py
git commit -m "feat: add Indic font download script with tests (Track B)"
```

---

### Task 4: Run the download and commit fonts

- [ ] **Step 1: Install requests if not already present**

```bash
pip show requests || pip install requests
```

- [ ] **Step 2: Run the download script**

```bash
cd /Users/jay/IndicPdf-Main
python scripts/download_indic_fonts.py
```

Expected: Fonts downloaded into `fonts/system/Bengali/`, `fonts/system/Tamil/`, etc. Each file printed with ✓.

- [ ] **Step 3: Verify fonts were downloaded**

```bash
find fonts/system -name "*.ttf" | grep -v "Hindi\|telugu\|devanagari\|latin" | wc -l
```

Expected: 50+ new TTF files

- [ ] **Step 4: Commit downloaded fonts**

```bash
git add fonts/system/Bengali/ fonts/system/Tamil/ fonts/system/Marathi/ \
        fonts/system/Gujarati/ fonts/system/Kannada/ fonts/system/Malayalam/ \
        fonts/system/Odia/ fonts/system/Urdu/
git commit -m "feat: add Indic fonts for Bengali, Tamil, Marathi, Gujarati, Kannada, Malayalam, Odia, Urdu"
```

---

### Task 5: ECC review + update docs

- [ ] **Step 1: Run ecc:python-review on the download script**

```
/python-review scripts/download_indic_fonts.py
```

Fix any issues flagged before proceeding.

- [ ] **Step 2: Run ecc:update-docs**

```
/update-docs
```

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "docs: update codemaps after Track B font expansion"
```
