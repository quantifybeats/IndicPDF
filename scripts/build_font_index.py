"""
build_font_index.py — Three-in-one font maintenance tool:
  1. Rename hash-named font files to human-readable names (PostScriptName.ttf)
  2. Scan each language folder and download missing Google Fonts families
  3. Write fonts/fonts_index.json — pre-extracted metadata for O(1) startup

Usage:
    python scripts/build_font_index.py            # full run
    python scripts/build_font_index.py --no-download  # skip network calls
    python scripts/build_font_index.py --index-only   # only rebuild index
"""
import json
import re
import sys
import argparse
from pathlib import Path

try:
    from fontTools.ttLib import TTFont, TTCollection
except ImportError:
    sys.exit("Install fontTools: pip install fonttools")

try:
    import requests
except ImportError:
    requests = None

FONTS_BASE = Path(__file__).parent.parent / "fonts" / "system"
INDEX_PATH = Path(__file__).parent.parent / "fonts" / "fonts_index.json"

FONTS_CSS_HEADERS = {"User-Agent": "Mozilla/4.0 (compatible)"}
DOWNLOAD_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Expected Google Fonts families per language folder.
# Running the script will download any that are not yet present.
EXPECTED_FONTS = {
    "Bengali":  ["Noto Sans Bengali", "Noto Serif Bengali", "Hind Siliguri", "Baloo Da 2", "Tiro Bangla", "Mukta Mahee"],
    "Tamil":    ["Noto Sans Tamil", "Noto Serif Tamil", "Hind Madurai", "Baloo Thambi 2", "Tiro Tamil"],
    "Marathi":  ["Noto Sans Devanagari", "Noto Serif Devanagari", "Tiro Devanagari Marathi", "Baloo 2"],
    "Gujarati": ["Noto Sans Gujarati", "Noto Serif Gujarati", "Hind Vadodara", "Rasa", "Baloo Bhai 2"],
    "Kannada":  ["Noto Sans Kannada", "Noto Serif Kannada", "Hind Mysuru", "Baloo Tamma 2", "Tiro Kannada"],
    "Malayalam":["Noto Sans Malayalam", "Noto Serif Malayalam", "Baloo Chettan 2", "Chilanka", "Gayathri", "Manjari"],
    "Odia":     ["Noto Sans Oriya", "Noto Serif Oriya", "Baloo Bhaina 2"],
    "Urdu":     ["Noto Nastaliq Urdu", "Noto Sans Arabic"],
    "Sanskrit": ["Sanskrit2003", "Tiro Devanagari Sanskrit", "Shobhika", "Noto Sans Devanagari", "Noto Serif Devanagari"],
}

SCRIPT_RANGES = {
    "devanagari": range(0x0900, 0x0980),
    "telugu": range(0x0C00, 0x0C80),
    "tamil": range(0x0B80, 0x0C00),
}

# Regex that matches typical Google Fonts hash filenames (no human-readable stem)
_HASH_RE = re.compile(r'^[A-Za-z0-9_\-]{25,}$')


def _is_hash_name(stem: str) -> bool:
    return bool(_HASH_RE.match(stem)) and not any(c.islower() and c.isalpha() and stem[stem.index(c)-1:stem.index(c)] == '-' for c in stem[1:])


def _read_ps_name(path: Path) -> str | None:
    """Return PostScript name from a TTF/OTF file, or None on failure."""
    try:
        font = TTFont(path, lazy=True)
        for rec in font['name'].names:
            if rec.nameID == 6:
                try:
                    return rec.toUnicode().strip()
                except Exception:
                    pass
    except Exception:
        pass
    return None


def rename_hash_files(lang_dir: Path) -> int:
    """Rename hash-named .ttf/.otf files to their PostScript name. Returns count renamed."""
    renamed = 0
    for f in lang_dir.glob("*.ttf"):
        if _is_hash_name(f.stem):
            ps = _read_ps_name(f)
            if ps and ps != f.stem:
                target = f.with_name(ps + f.suffix)
                if not target.exists():
                    f.rename(target)
                    print(f"  renamed: {f.name} → {target.name}")
                    renamed += 1
                else:
                    # Duplicate — remove the hash file, keep the named one
                    f.unlink()
                    print(f"  removed duplicate: {f.name}")
    return renamed


def get_font_urls(family: str) -> list[str]:
    url = f"https://fonts.googleapis.com/css?family={family.replace(' ', '+')}"
    resp = requests.get(url, headers=FONTS_CSS_HEADERS, timeout=15)
    resp.raise_for_status()
    return re.findall(r'url\((https://fonts\.gstatic\.com/[^)]+\.ttf)\)', resp.text)


def download_family(family: str, lang_dir: Path) -> int:
    """Download all TTF variants for a Google Fonts family. Returns count downloaded."""
    if requests is None:
        print(f"  [skip] requests not installed")
        return 0
    try:
        urls = get_font_urls(family)
    except Exception as e:
        print(f"  [warn] {family}: {e}")
        return 0
    if not urls:
        print(f"  [warn] no TTF URLs for: {family}")
        return 0
    downloaded = 0
    for url in urls:
        filename = url.split("/")[-1].split("?")[0]
        # Use a placeholder name — rename step will fix it later
        dest = lang_dir / filename
        if dest.exists():
            continue
        try:
            resp = requests.get(url, headers=DOWNLOAD_HEADERS, timeout=30)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
            downloaded += 1
        except Exception as e:
            print(f"    [error] {filename}: {e}")
    return downloaded


def _extract_metadata(path: Path) -> dict | None:
    """Extract font metadata dict from a .ttf/.otf file."""
    try:
        font = TTFont(path, lazy=True)
        ps_name = full_name = family_name = ""
        for rec in font['name'].names:
            try:
                val = rec.toUnicode().strip()
            except Exception:
                continue
            if rec.nameID == 1 and not family_name:
                family_name = val
            elif rec.nameID == 4 and not full_name:
                full_name = val
            elif rec.nameID == 6 and not ps_name:
                ps_name = val
        if not ps_name:
            ps_name = path.stem
        weight = "regular"
        style = "normal"
        if 'OS/2' in font:
            sel = font['OS/2'].fsSelection
            if sel & 0x20:
                weight = "bold"
            if sel & 0x01:
                style = "italic"
            wc = font['OS/2'].usWeightClass
            if wc >= 700:
                weight = "bold"
            elif wc <= 300:
                weight = "light"
        codepoints = set()
        if "cmap" in font:
            for table in font["cmap"].tables:
                try:
                    codepoints.update(table.cmap.keys())
                except Exception:
                    pass
        scripts = [name for name, r in SCRIPT_RANGES.items()
                   if any(cp in codepoints for cp in r)]
        return {
            "postscript_name": ps_name,
            "full_name": full_name or ps_name,
            "family_name": family_name or ps_name,
            "weight": weight,
            "style": style,
            "scripts": scripts,
        }
    except Exception as e:
        print(f"  [warn] metadata failed for {path.name}: {e}")
        return None


def _extract_ttc(path: Path) -> list[dict]:
    """Extract metadata from all faces in a .ttc collection."""
    results = []
    try:
        col = TTCollection(path)
        extract_dir = path.parent / f"_{path.stem}_extracted"
        extract_dir.mkdir(exist_ok=True)
        for i, font in enumerate(col.fonts):
            ps_name = full_name = family_name = ""
            for rec in font['name'].names:
                try:
                    val = rec.toUnicode().strip()
                except Exception:
                    continue
                if rec.nameID == 1 and not family_name:
                    family_name = val
                elif rec.nameID == 4 and not full_name:
                    full_name = val
                elif rec.nameID == 6 and not ps_name:
                    ps_name = val
            if not ps_name:
                ps_name = f"{path.stem}_face{i}"
            face_path = extract_dir / f"{ps_name}.ttf"
            if not face_path.exists():
                font.save(face_path)
            weight = "regular"
            style = "normal"
            if 'OS/2' in font:
                sel = font['OS/2'].fsSelection
                if sel & 0x20:
                    weight = "bold"
                if sel & 0x01:
                    style = "italic"
                wc = font['OS/2'].usWeightClass
                if wc >= 700:
                    weight = "bold"
                elif wc <= 300:
                    weight = "light"
            codepoints = set()
            if "cmap" in font:
                for table in font["cmap"].tables:
                    try:
                        codepoints.update(table.cmap.keys())
                    except Exception:
                        pass
            scripts = [name for name, r in SCRIPT_RANGES.items()
                       if any(cp in codepoints for cp in r)]
            results.append({
                "rel_path": str(face_path.relative_to(FONTS_BASE.parent)),
                "postscript_name": ps_name,
                "full_name": full_name or ps_name,
                "family_name": family_name or ps_name,
                "weight": weight,
                "style": style,
                "scripts": scripts,
            })
    except Exception as e:
        print(f"  [warn] TTC extraction failed for {path.name}: {e}")
    return results


def build_index() -> dict:
    """Walk all fonts in fonts/system/ and produce the index dict."""
    fonts = []
    seen_ps = set()

    for font_file in sorted(FONTS_BASE.rglob("*")):
        if font_file.suffix.lower() not in {".ttf", ".otf", ".ttc"}:
            continue
        rel = str(font_file.relative_to(FONTS_BASE.parent))

        if font_file.suffix.lower() == ".ttc":
            for entry in _extract_ttc(font_file):
                key = entry["postscript_name"]
                if key and key not in seen_ps:
                    seen_ps.add(key)
                    fonts.append(entry)
        else:
            meta = _extract_metadata(font_file)
            if meta:
                key = meta["postscript_name"]
                if key not in seen_ps:
                    seen_ps.add(key)
                    fonts.append({"rel_path": rel, **meta})

    return {"version": 2, "count": len(fonts), "fonts": fonts}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-download", action="store_true", help="Skip network downloads")
    parser.add_argument("--index-only", action="store_true", help="Only rebuild index, no rename/download")
    args = parser.parse_args()

    print(f"Font base: {FONTS_BASE}")

    # Step 1: Ensure Sanskrit folder exists
    (FONTS_BASE / "Sanskrit").mkdir(parents=True, exist_ok=True)

    if not args.index_only:
        # Step 2: Rename hash-named files in every language folder
        print("\n=== Renaming hash-named files ===")
        total_renamed = 0
        for lang_dir in sorted(FONTS_BASE.iterdir()):
            if lang_dir.is_dir():
                n = rename_hash_files(lang_dir)
                if n:
                    print(f"  {lang_dir.name}: {n} renamed")
                total_renamed += n
        print(f"Total renamed: {total_renamed}")

        # Step 3: Download missing fonts
        if not args.no_download:
            if requests is None:
                print("\n[skip downloads] requests not installed")
            else:
                print("\n=== Downloading missing fonts ===")
                for lang, families in EXPECTED_FONTS.items():
                    lang_dir = FONTS_BASE / lang
                    lang_dir.mkdir(exist_ok=True)
                    # Collect existing family names (from non-hash-named files)
                    existing_names = {
                        f.stem.lower().replace("-", "").replace("_", "")
                        for f in lang_dir.glob("*.ttf")
                    }
                    for family in families:
                        norm = family.lower().replace(" ", "").replace("-", "").replace("_", "")
                        # Skip if any file starts with this family stem
                        if any(ex.startswith(norm[:8]) for ex in existing_names):
                            continue
                        print(f"  [{lang}] downloading: {family}")
                        n = download_family(family, lang_dir)
                        if n:
                            print(f"    → {n} files")
                    # Rename newly downloaded hashes
                    rename_hash_files(lang_dir)

    # Step 4: Build and write index
    print("\n=== Building font index ===")
    index = build_index()
    INDEX_PATH.write_text(json.dumps(index, indent=2, ensure_ascii=False))
    print(f"Written: {INDEX_PATH}  ({index['count']} fonts)")


if __name__ == "__main__":
    main()
