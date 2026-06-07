# IndicPDF — Session Handoff Report
**Date:** 2026-06-07  
**Project root:** `/Users/jay/IndicPdf-Main`

---

## 1. What IndicPDF Is

A production-grade document conversion web app specializing in **bidirectional DOCX ↔ PDF for Indic scripts** (Telugu, Devanagari, Tamil). Built with:

| Layer | Stack |
|---|---|
| Frontend | React 19 + Vite + Tailwind CSS |
| Backend | FastAPI + Uvicorn |
| Job Queue | RQ (Redis Queue) + Redis |
| PDF Rendering | fpdf2 + uharfbuzz (HarfBuzz shaping) |
| PDF Extraction | pdfminer.six |
| Fonts | Deterministic local TTF/OTF registry in `fonts/system/` |
| Deployment | Render.com (Web + Worker + Redis), Docker |

**Existing tools (already working):**
- DOCX → PDF (Indic script support)
- PDF → DOCX
- TXT → PDF
- PDF Analyser
- English Font Converter

---

## 2. What Was Decided This Session

### UI Direction (Phase 2 — deferred, do LAST)
- Layout: **Grid launcher + inline expand** (click a tool card → workspace expands below, no page redirect)
- Theme: **Light mode**, warm off-white background (`#FAF9F6`), terracotta accent (`#C2410C`)
- Typography: **Plus Jakarta Sans** from Google Fonts
- Bigger dropzone
- Mobile-responsive hamburger menu
- Per-file status badges (queued → processing → done ✓)

### Phase 1 Scope (implement NOW — 3 tracks)

**Track B — Indic Font Expansion** *(do first, backend only)*  
**Track C — OCR** *(do second, backend + frontend)*  
**Track A — Multimedia Tools** *(do third, frontend only)*

### ECC Plugin
The `ecc@ecc` plugin is installed. Use these skills throughout implementation:
- `ecc:python-review` — after every Python file change
- `ecc:fastapi-review` — after backend/main.py changes
- `ecc:react-review` — after every React component change
- `ecc:security-scan` — before each deploy
- `ecc:docker-patterns` — after Dockerfile changes
- `ecc:pr` — at end of each track

### ECC MCP Servers (now available)
- **GitHub MCP** — create PRs, push files, manage branches
- **Context7 MCP** — live docs for any library
- **Memory MCP** — persist decisions across sessions
- **Playwright MCP** — browser-based UI testing

---

## 3. Files Created This Session

| File | What it is |
|---|---|
| `docs/superpowers/specs/2026-06-07-multimedia-tools-design.md` | Full design spec (all 3 tracks + ECC + OCR) |
| `docs/superpowers/plans/2026-06-07-track-b-indic-fonts.md` | Implementation plan: font download script |
| `docs/superpowers/plans/2026-06-07-track-c-ocr.md` | Implementation plan: OCR backend + frontend |
| `docs/superpowers/plans/2026-06-07-track-a-multimedia.md` | Implementation plan: FFmpeg.wasm multimedia |

Font folders created (empty, with `.gitkeep`):
- `fonts/system/Bengali/`
- `fonts/system/Tamil/`
- `fonts/system/Marathi/`
- `fonts/system/Gujarati/`
- `fonts/system/Kannada/`
- `fonts/system/Malayalam/`
- `fonts/system/Odia/`
- `fonts/system/Urdu/`

---

## 4. Remaining Execution — Full Plan

### ▶ TRACK B: Indic Font Expansion
**Plan:** `docs/superpowers/plans/2026-06-07-track-b-indic-fonts.md`

**What it does:** Downloads all OFL-licensed Google Fonts + Lohit fonts for 8 new Indian language scripts. Zero backend code changes — FontRegistry already auto-scans new folders.

**Key tasks:**
1. Write + run `tests/test_font_downloader.py`
2. Implement `scripts/download_indic_fonts.py`
3. Run the script → fonts download into language folders
4. Commit downloaded fonts
5. Run `ecc:python-review`

**Font tiers:**
- **Auto-downloaded (OFL):** Noto Sans/Serif for all scripts, Lohit series, plus language-specific Google Fonts
- **Manual drop-in (proprietary):** Kruti Dev, Nirmala UI, Latha, Gautami, Tunga, Vrinda, Bamini, TSCII, Nudi, Baraha — drop into `fonts/system/LANGUAGE/` if you have a license

---

### ▶ TRACK C: OCR
**Plan:** `docs/superpowers/plans/2026-06-07-track-c-ocr.md`

**What it does:** Server-side OCR using Tesseract with 9 Indic language packs. Users upload scanned PDFs or images, get back extracted text (.txt). Queued via existing RQ worker.

**New dependencies to add:**
```
# requirements.txt
pytesseract
pdf2image
Pillow
```

**Dockerfile additions:**
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-hin tesseract-ocr-tel tesseract-ocr-tam \
    tesseract-ocr-ben tesseract-ocr-guj tesseract-ocr-kan tesseract-ocr-mal \
    tesseract-ocr-ori tesseract-ocr-pan poppler-utils \
    && rm -rf /var/lib/apt/lists/*
```

**New files:**
- `backend/ocr_processor.py` — `run_ocr()`, `ocr_pdf_to_text()`, `ocr_image_to_text()`
- `backend/main.py` — add `POST /ocr` endpoint
- `backend/worker.py` — add `process_ocr()` job
- `frontend/src/pages/OcrTool.jsx` — language selector + dropzone + polling
- `frontend/src/App.jsx` — add `/ocr` route
- `frontend/src/components/Navbar.jsx` — add OCR nav link

**Supported languages:**
`auto` (multi-lang), Hindi, Telugu, Tamil, Bengali, Gujarati, Kannada, Malayalam, Odia, Punjabi, English

---

### ▶ TRACK A: Multimedia Tools (FFmpeg.wasm)
**Plan:** `docs/superpowers/plans/2026-06-07-track-a-multimedia.md`

**What it does:** Browser-side image/video/audio conversion using FFmpeg.wasm v0.12. Zero server load — runs entirely in the user's browser via Web Worker.

**New npm packages:**
```bash
npm install @ffmpeg/ffmpeg@0.12.15 @ffmpeg/util@0.12.1
npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
```

**New files:**
- `frontend/src/hooks/useFFmpeg.js` — lazy-loads WASM, exposes `load()` + `convertFile()`
- `frontend/src/components/FormatSelector.jsx` — output format dropdown
- `frontend/src/components/FileActionRow.jsx` — per-file row with status badge + download
- `frontend/src/components/MediaDropzone.jsx` — drag-and-drop for media files
- `frontend/src/pages/ImageConverter.jsx` — `/image-converter`
- `frontend/src/pages/VideoConverter.jsx` — `/video-converter`
- `frontend/src/pages/AudioConverter.jsx` — `/audio-converter`

**Routes to add to App.jsx:**
```
/image-converter → ImageConverter (lazy)
/video-converter → VideoConverter (lazy)
/audio-converter → AudioConverter (lazy)
```

**Navbar:** Add a "Media ▾" dropdown with links to all three tools.

**Supported formats:**
| Tool | Input | Output |
|---|---|---|
| Image | JPG PNG GIF BMP WEBP ICO TIFF | JPG PNG GIF BMP WEBP ICO |
| Video | MP4 AVI MOV MKV WEBM FLV | MP4 WEBM AVI MOV GIF |
| Audio | MP3 WAV FLAC AAC OGG M4A | MP3 WAV FLAC AAC OGG |

---

### ▶ PHASE 2: UI Redesign (do LAST)
- Deferred — full UI redesign with warm light theme, grid launcher layout, Plus Jakarta Sans
- User has a specific UI/UX change in mind (not yet disclosed — ask them)

---

## 5. Key Constraints to Remember

- **Never use `pdf.text()` for Indic layout** — always `pdf.write()` (HarfBuzz metrics)
- **Always NFC-normalize** text before rendering
- **Urdu fonts downloaded but RTL pipeline not supported yet** — `pdf_processor.py` assumes LTR
- **Render Starter = 512MB RAM** — OCR jobs are ~80–120MB each, manageable
- **FFmpeg.wasm ~30MB** — lazy-loaded, cached by browser after first visit
- **FontRegistry auto-scans** `fonts/system/` — dropping a font file in is enough

---

## 6. How to Start the New Session

Tell the new chat:

> "I'm continuing work on IndicPDF at `/Users/jay/IndicPdf-Main`. Read `docs/superpowers/HANDOFF.md` for full context. Start with Track B (font download script) using the plan at `docs/superpowers/plans/2026-06-07-track-b-indic-fonts.md`. Use `superpowers:subagent-driven-development` to execute it."
