# IndicPDF

IndicPDF is a production-grade DOCX to PDF conversion engine focused on high-fidelity, Unicode-compliant rendering for Indic languages (Telugu, Hindi, Tamil, etc.).

## Core Features
- **Deterministic Font Asset Layer:** Operates independently of the host OS fonts. Scans internal font metadata (PostScript names, Unicode ranges) to ensure the correct font is always used.
- **Legacy Encoding Support:** Detects legacy font encodings (like APS, Anu, etc.) and automatically converts text to standard Unicode (NFC normalized).
- **Professional Text Shaping:** Integrated with `uharfbuzz` (HarfBuzz) to handle complex Indic ligatures, matra reordering, and glyph positioning.
- **Reliable PDF Output:** Mandatory subsetting and embedding of fonts to ensure identical rendering across all devices and PDF readers.
- **Trust Reporting:** Provides a processing log explaining font substitutions and encoding fixes to the user.

## Project Structure
```text
/backend
├── main.py             # FastAPI entry point & API routes
├── processor.py        # Core document processing & PDF generation logic
├── font_manager.py     # Font Asset Layer & Metadata Registry
├── encoding_manager.py # Legacy-to-Unicode conversion tables
├── shaping_engine.py   # HarfBuzz (uharfbuzz) integration
└── static/             # Frontend web interface
/fonts
├── system/             # Verified system fonts (e.g., Noto Sans)
├── fallback/           # Script-aware fallbacks
└── uploads/            # Document-specific font uploads
/data
├── uploads/            # Temporary storage for uploaded DOCX
└── outputs/            # Generated PDF storage
```

## Getting Started

### 1. Prerequisites
- Python 3.8+
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```

### 2. Font Setup
Place your `.ttf` or `.otf` font files in the `fonts/system` or `fonts/fallback` directories. The system will automatically index them on startup.

### 3. Run the Server
```bash
python3 -m backend.main
```
Navigate to `http://localhost:8000` to access the web interface.

## Implementation Methodology
This project was built following a strict 6-path deterministic execution model:
1. **Core Processing (MVP):** End-to-end pipeline skeleton.
2. **Font Intelligence Layer:** Metadata-based font registry.
3. **Encoding Integrity Layer:** Normalization and legacy mapping.
4. **Rendering Accuracy Layer:** Precise glyph shaping via HarfBuzz.
5. **Output Reliability Layer:** Full font embedding.
6. **UX & Trust Layer:** Transparency logs and UI.
