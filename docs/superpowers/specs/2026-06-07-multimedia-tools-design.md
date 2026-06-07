# IndicPDF — Phase 1: Multimedia Tools + Indic Font Expansion
**Date:** 2026-06-07  
**Phase:** 1 of 3

---

## Overview

Two parallel tracks in Phase 1:

**Track A — Multimedia Tools**: Add browser-side image, video, and audio conversion via FFmpeg.wasm. Zero server load.

**Track B — Indic Font Expansion**: Write a one-time download script that pulls all available Google Fonts (and Noto fonts from GitHub) for the top 10 most spoken Indian languages, supplementing existing bundled fonts.

Deferred to later phases:
- Full UI redesign (warm light theme, grid launcher layout)
- Specific UI/UX change (TBD)

---

## Architecture

```
User's Browser
├── Existing tools (DOCX↔PDF, TXT→PDF, Analyser, Fonts) → FastAPI backend
└── New multimedia tools (Image, Video, Audio) → FFmpeg.wasm (Web Worker, local)

FastAPI Backend (unchanged except 2 CORS headers)
```

**FFmpeg.wasm version:** `@ffmpeg/ffmpeg@0.12.x` — does NOT require SharedArrayBuffer, so no `COOP/COEP` headers needed. Works on Render Starter as-is.

---

## Backend Changes

None. FFmpeg.wasm v0.12 does not require `SharedArrayBuffer` and therefore does not need `COOP/COEP` headers. The existing FastAPI backend is untouched.

---

## New Frontend Pages

### 1. `/image-converter`
- Accepted input: JPG, PNG, GIF, BMP, WEBP, ICO, TIFF
- Output formats: JPG, PNG, GIF, BMP, WEBP, ICO
- Batch: yes (multiple files, each gets own format selector)

### 2. `/video-converter`
- Accepted input: MP4, AVI, MOV, MKV, WEBM, FLV
- Output formats: MP4, WEBM, AVI, MOV, GIF
- Batch: yes

### 3. `/audio-converter`
- Accepted input: MP3, WAV, FLAC, AAC, OGG, M4A
- Output formats: MP3, WAV, FLAC, AAC, OGG
- Batch: yes

---

## New Components

### `useFFmpeg.js` (hook)
- Lazy-loads FFmpeg.wasm only when a multimedia page is first opened
- Exposes: `{ loaded, load, convertFile }`
- Shows loading progress bar while WASM downloads (~30MB, first visit only)

### `MediaDropzone.jsx`
- Reuses existing `Dropzone.jsx` styles
- Accepts image/video/audio MIME types
- On drop: builds a `fileActions` list (file + status + outputFormat)

### `FileActionRow.jsx`
- One row per uploaded file: icon | filename | size | `FormatSelector` | status badge | download button
- Status badge states: `idle` → `converting` (spinner) → `done ✓` → `error ✗`

### `FormatSelector.jsx`
- Dropdown showing valid output formats for the file's input type
- Disabled while converting

---

## Conversion Flow

1. User drops files → `fileActions` array built, status = `idle`
2. User selects output format per file
3. "Convert All" clicked → iterates `fileActions`, calls `ffmpeg.exec()` per file
4. Status badge updates in real time
5. On success: download button appears with `URL.createObjectURL(blob)`
6. On error: red badge with short error message

---

## Routing & Navbar

Add three new routes to `App.jsx`:
```
/image-converter  → ImageConverter (lazy)
/video-converter  → VideoConverter (lazy)
/audio-converter  → AudioConverter (lazy)
```

Navbar gets a **"Media"** dropdown group alongside existing tool links. On mobile: added to the existing menu list.

---

## Supported Format Matrix

| Tool | Input formats | Output formats |
|---|---|---|
| Image | JPG PNG GIF BMP WEBP ICO TIFF | JPG PNG GIF BMP WEBP ICO |
| Video | MP4 AVI MOV MKV WEBM FLV | MP4 WEBM AVI MOV GIF |
| Audio | MP3 WAV FLAC AAC OGG M4A | MP3 WAV FLAC AAC OGG |

---

## Performance Notes

- FFmpeg.wasm is ~30MB, loaded once and cached by the browser
- Loaded lazily — only when user navigates to a media tool
- Runs in a Web Worker — does not block the UI thread
- Large video files (>500MB) may be slow on low-end devices; no hard limit enforced

---

---

## Track B — Indic Font Expansion

### Goal
Supplement existing bundled fonts with all available Google Fonts for the top 10 most spoken Indian languages. Keep existing fonts untouched; only add new ones.

### Font Folder Structure

```
fonts/system/
├── Hindi/          ✅ existing (extensive)
├── Telugu/         ✅ existing (extensive)
├── devanagari/     ✅ existing (keep as-is)
├── latin/          ✅ existing
├── Tamil/          🆕 dedicated folder (currently scattered in devanagari/)
├── Bengali/        🆕
├── Marathi/        🆕 (Devanagari script — different font families from Hindi)
├── Gujarati/       🆕
├── Kannada/        🆕
├── Malayalam/      🆕
├── Odia/           🆕
└── Urdu/           🆕 (Nastaliq/Arabic script — RTL)
```

### Download Script: `scripts/download_indic_fonts.py`

A one-time Python script (not run at server startup). Run locally, commit the fonts.

**Approach:**
1. For each language, define a list of Google Font family names
2. Fetch `https://fonts.googleapis.com/css2?family=FAMILY&subset=SCRIPT` with a desktop User-Agent
3. Parse the CSS response to extract `.ttf` URLs from `fonts.gstatic.com`
4. Download and save to the correct `fonts/system/LANGUAGE/` folder
5. Skip files that already exist (idempotent)

**Font sources:**
- Primary: Google Fonts CSS API (no API key needed)
- Secondary: Noto fonts from `https://github.com/notofonts` releases (for scripts with limited Google Fonts coverage)

### Font Priority Tiers

**Tier 1 — Pan-India Core (auto-downloaded, OFL)**
| Font | Scripts | Source |
|---|---|---|
| Noto Sans Indic | All 10 scripts | Google Fonts / github.com/notofonts |
| Noto Serif Indic | All 10 scripts | Google Fonts / github.com/notofonts |
| Lohit Series | Devanagari, Tamil, Telugu, Bengali, Gujarati, Kannada, Odia, Malayalam | github.com/nicowillis/lohit-fonts |

**Tier 2 — Regional Priority (auto-downloaded, OFL)**
| Language | Script | HarfBuzz tag | Fonts |
|---|---|---|---|
| Hindi/Marathi | Devanagari | `deva` | Noto Sans/Serif Devanagari, Lohit Devanagari, Tiro Devanagari Hindi/Marathi, Baloo 2, Mukta |
| Tamil | Tamil | `taml` | Noto Sans/Serif Tamil, Lohit Tamil, Hind Madurai, Baloo Thambi 2, Tiro Tamil |
| Telugu | Telugu | `telu` | Noto Sans/Serif Telugu, Lohit Telugu, Mandali, Baloo Tammudu 2 |
| Bengali | Bengali | `beng` | Noto Sans/Serif Bengali, Lohit Bengali, SolaimanLipi, Hind Siliguri, Tiro Bangla |
| Kannada | Kannada | `knda` | Noto Sans/Serif Kannada, Lohit Kannada, Hind Mysuru, Baloo Tamma 2, Tiro Kannada |
| Gujarati | Gujarati | `gujr` | Noto Sans/Serif Gujarati, Lohit Gujarati, Hind Vadodara, Rasa |
| Malayalam | Malayalam | `mlym` | Noto Sans/Serif Malayalam, Lohit Malayalam, Chilanka, Gayathri, Manjari |
| Odia | Oriya | `orya` | Noto Sans/Serif Oriya, Lohit Odia, Baloo Bhaina 2 |
| Urdu | Arabic | `arab` | Noto Nastaliq Urdu, Noto Sans Arabic — **RTL flagged, see note** |

**Tier 3 — Proprietary / Manual Drop-in (NOT auto-downloaded)**

These require a license. Drop files manually into the correct `fonts/system/LANGUAGE/` folder — FontRegistry picks them up automatically.

| Font | Script | Why needed |
|---|---|---|
| Kruti Dev | Devanagari | ~75% North India DTP print legacy |
| Nirmala UI | Multi-script | Windows default UI font |
| Latha / Gautami / Tunga / Vrinda | Tamil/Telugu/Kannada/Bengali | Windows legacy system fonts |
| Bamini / TSCII | Tamil | Legacy print media |
| Nudi / Baraha | Kannada | Legacy DTP |

**Urdu/RTL note:** fpdf2+HarfBuzz supports RTL via `arab` tag, but the line reconstruction logic in `pdf_processor.py` assumes LTR. Urdu fonts are downloaded; full RTL pipeline is a future constraint.

### FontRegistry Update
`backend/font_manager.py` already recursively scans `fonts/system/`. No code change needed — new folders are picked up automatically on next server start.

---

## What This Does NOT Change

- Existing Indic PDF pipeline (DOCX↔PDF, TXT→PDF, Analyser, Font Converter)
- Backend job queue, Redis, RQ worker
- Existing UI design/theme (redesign is Phase 2)
- Routing structure for existing pages
- FontRegistry scan logic (already handles new folders automatically)
