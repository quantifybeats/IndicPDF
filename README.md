# IndicPDF Engine

## A. System Overview

IndicPDF is a production-grade document conversion pipeline specializing in bidirectional (DOCX ↔ PDF) processing of complex Indic scripts (Telugu, Devanagari, Tamil).

```text
[ DOCX Upload ] --> [ Normalization & CID Cleaning ] --> [ Font Resolution ] --> [ HarfBuzz Shaping via fpdf2 ] --> [ PDF Output ]
[ PDF Upload ]  --> [ Line-Level Extraction ]        --> [ CID Stripping ]   --> [ Font Mapping ]                 --> [ DOCX Output ]
```

The system relies on a **deterministic font asset layer** rather than OS-level dependencies, allowing precise control over rendering fidelity.

## B. Core Engine Design

1.  **Rendering Engine (DOCX → PDF)**: Built on `fpdf2`. Crucially, it relies on `fpdf2`'s native integration with `uharfbuzz` for text shaping.
2.  **Extraction Engine (PDF → DOCX)**: Built on `pdfminer.six`. It utilizes `LAParams` for line-level semantic grouping to reconstruct paragraphs without micro-fragmentation.
3.  **Encoding & Normalization**: All incoming text is forced into Unicode Normalization Form C (NFC). An aggressive filter (`EncodingManager.strip_all_junk`) eliminates extraction artifacts like `(cid:N)`.

## C. Key Design Decisions

*   **`pdf.write()` Only**: Manual layout engines (measuring clusters and managing cursors) were abandoned. `fpdf2` maintains deep state regarding cursor position and cluster widths. Intercepting this with manual `pdf.text()` calls causes severe spacing anomalies (horizontal expansion).
*   **Cluster-Level Rendering Abandoned**: Attempting to pre-wrap text by analyzing HarfBuzz grapheme clusters caused interference with `fpdf2`'s internal word-wrapping algorithm. The engine now trusts `fpdf2` + HarfBuzz to handle line breaks natively, provided the shaping script tags are set correctly.
*   **Aggressive Junk Stripping**: Older PDF generators embed subsetted fonts without complete `ToUnicode` tables. This causes `pdfminer.six` to extract raw CIDs (e.g., `(cid:46)`). These are usually invisible formatting or control glyphs. A "scorched earth" regex filter is applied universally to prevent these from polluting the DOCX output or breaking shaping sequences.
*   **Point (pt) Units**: The `IndicPDF` wrapper explicitly initializes `fpdf2` with `unit="pt"`. This prevents floating-point conversion errors between HarfBuzz (which operates in points) and `fpdf2` (which defaults to millimeters).

## D. Module Breakdown

*   **`frontend/`**: The modern React + Vite + Tailwind CSS frontend. Replaced the monolithic static HTML with a component-based architecture for better performance and UX.
*   **`backend/processor.py`**: The DOCX → PDF pipeline.
*   **`backend/pdf_processor.py`**: The PDF → DOCX pipeline.
*   **`backend/encoding_manager.py`**: Handles text sanitization.
*   **`backend/font_manager.py`**: Manages the deterministic font asset layer.
*   **`scripts/download_indic_fonts.py`**: One-time CLI script to download OFL-licensed Google Fonts + Lohit fonts for 8 new Indic language scripts into `fonts/system/`. Re-runnable — skips already-present files. Run with `python3 scripts/download_indic_fonts.py` or `--lang Bengali` for a single language.

<!-- AUTO-GENERATED: font-registry -->
## G. Font Registry (Track B)

`fonts/system/` contains TTF/OTF fonts organized by script folder. FontRegistry auto-scans all subfolders on startup — dropping a font file in is sufficient.

| Folder | Script | Bundled Fonts |
|--------|--------|--------------|
| `Hindi/` | Devanagari | Noto Sans/Serif Devanagari |
| `telugu/` | Telugu | Noto Sans/Serif Telugu |
| `devanagari/` | Devanagari | (legacy alias) |
| `latin/` | Latin | Inter, Roboto |
| `Bengali/` | Bengali | Noto Sans/Serif Bengali, Hind Siliguri, Baloo Da 2, Tiro Bangla, Kalam, Mukta Mahee, Lohit-Bengali |
| `Tamil/` | Tamil | Noto Sans/Serif Tamil, Hind Madurai, Baloo Thambi 2, Tiro Tamil, Arima, Lohit-Tamil |
| `Marathi/` | Devanagari | Noto Sans/Serif Devanagari, Tiro Devanagari Marathi, Baloo 2, Lohit-Devanagari |
| `Gujarati/` | Gujarati | Noto Sans/Serif Gujarati, Hind Vadodara, Rasa, Baloo Bhai 2, Lohit-Gujarati |
| `Kannada/` | Kannada | Noto Sans/Serif Kannada, Hind Mysuru, Baloo Tamma 2, Tiro Kannada, Lohit-Kannada |
| `Malayalam/` | Malayalam | Noto Sans/Serif Malayalam, Baloo Chettan 2, Chilanka, Gayathri, Manjari, Lohit-Malayalam |
| `Odia/` | Odia | Noto Sans/Serif Oriya, Baloo Bhaina 2, Lohit-Odia |
| `Urdu/` | Arabic/Nastaliq | Noto Nastaliq Urdu, Noto Sans Arabic |

All fonts are OFL-licensed. Proprietary fonts (Kruti Dev, Nirmala UI, Latha, Gautami, Tunga, Vrinda) can be dropped in manually if you hold a license.
<!-- END AUTO-GENERATED: font-registry -->

## E. Deployment (Render Native)

The system is fully containerized and ready for Render via `render.yaml`. It uses a multi-stage Docker build to build the frontend and bundle it with the FastAPI backend.

1.  **Web Service**: Runs both the FastAPI API and the RQ Worker (via `start.sh`).
2.  **Redis (Key Value)**: Required for the task queue.

**Environment Variables**:
*   `REDIS_URL`: Auto-wired from the Redis service.
*   `INDICPDF_API_KEY`: Auto-generated on first deploy.
*   `INDICPDF_MASTER_KEY`: Auto-generated master key for file encryption.

## F. Text Processing Pipeline (The "Golden Path")

1.  **Input**: Raw text from DOCX run or PDF line.
2.  **Sanitization**: `encoding_manager.strip_all_junk()` removes `(cid:N)` and `\x00-\x1F`.
3.  **Normalization**: `unicodedata.normalize('NFC', text)` ensures base characters and matras are properly combined.
4.  **Font Resolution**: `font_registry.resolve_font()` finds a local TTF/OTF that supports the script and matches the requested weight/style.
5.  **Shaping State**: `pdf.set_text_shaping(use_shaping_engine=True, script="telu")` configures HarfBuzz.
6.  **Rendering**: `pdf.write()` calculates advances and renders to PDF.

## F. Known Constraints

*   **fpdf2 Line Breaking**: While `fpdf2` supports HarfBuzz, its line-breaking algorithm is optimized for Latin spaces. Extremely long, unbroken Indic words may occasionally wrap awkwardly if no spaces are present.
*   **Font Dependency**: The system's fidelity is 100% dependent on the presence of valid `GSUB`/`GPOS` tables in the loaded TTF/OTF files. A font without these tables will render without conjuncts/matras, even if shaping is enabled.
*   **PDF Extraction Limits**: `pdfminer.six` cannot reconstruct reading order perfectly for complex, multi-column PDFs.

## G. Extension Points

*   **Adding Scripts**: Update the `script` detection logic in `processor.py` and the Unicode ranges in `font_manager.py` to support languages like Kannada (`knda`), Malayalam (`mlym`), or Bengali (`beng`).
*   **Legacy Encodings**: Expand the `legacy_maps` dictionary in `encoding_manager.py` to support automated conversion of non-Unicode text (e.g., Shreelipi).

## H. Debug Playbook

**Symptom**: Characters are spaced unnaturally far apart.
*   **Check**: Ensure `IndicPDF` is initialized with `unit="pt"`. Ensure no manual `pdf.set_x()` calls are overriding the cursor.

**Symptom**: Matras are detached or rendering as dotted circles.
*   **Check**: Verify `pdf.set_text_shaping` is being hit with the correct `script` tag (e.g., `telu`). Check the log to see if the chosen font actually supports the Unicode range.

**Symptom**: Output contains `(cid:9)` or similar markers.
*   **Check**: The `strip_all_junk` regex in `encoding_manager.py` needs updating to catch a new, malformed extraction pattern.

## I. AI-Readable Design Notes

*   `INV_01`: All strings MUST pass through NFC normalization before layout calculation.
*   `INV_02`: `pdf.write()` is the exclusive mutation method for PDF text layout.
*   `INV_03`: `shaping_engine=True` MUST be paired with a valid ISO 15924 script tag (`deva`, `telu`, etc.) for Indic text.
*   `ASSUMP_01`: Local font registry contains authoritative TTF/OTF assets. PDF font requests are best-effort matched against this registry.
*   `DEAD_CODE`: Manual HarfBuzz buffering (`uharfbuzz` direct usage) was removed in favor of `fpdf2` internal integration to maintain metric consistency. Do not reintroduce.