# IndicPDF — Multimedia Tools Addition
**Date:** 2026-06-07  
**Phase:** 1 of 3 (Multimedia tools + UI placeholders)

---

## Overview

Add browser-side image, video, and audio conversion to IndicPDF using FFmpeg.wasm. Conversions run entirely in the user's browser — zero server load. Two minor backend header changes required for FFmpeg.wasm compatibility.

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

## What This Does NOT Change

- Existing Indic PDF pipeline (DOCX↔PDF, TXT→PDF, Analyser, Font Converter)
- Backend job queue, Redis, RQ worker
- Existing UI design/theme (redesign is Phase 2)
- Routing structure for existing pages
