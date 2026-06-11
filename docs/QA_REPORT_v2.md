# IndicPDF — QA & Reliability Audit Report

- **Report version:** v2.0
- **Date:** 2026-06-11
- **Author role:** Senior QA Engineer + Systems Tester (document pipelines / conversion engines)
- **Build under test:** branch `feat/v2-engine-integration` @ `a88a2e8`. Integrated codebase: `backend/main.py` (FastAPI), `backend/tasks.py` (RQ worker), `backend/reconstruction_engine.py` (v2 engine), `backend/processor.py` (DOCX/TXT→PDF), `backend/security_manager.py`, `backend/font_manager.py`, `frontend/src/**`.
- **Method:** Empirical destructive testing — engine internals called directly, full HTTP layer via FastAPI `TestClient`, a **real two-process end-to-end** (separate `rq worker` subprocess), and a **live uvicorn** server for traversal. Environment: macOS, Python 3.14, Redis up, Tesseract 163 langs present, **LibreOffice absent** (so the FPDF fallback is the active DOCX→PDF engine — representative of any slim container).
- **Relationship to v1:** v1 (`QA_REPORT_v1.md`) audited the donor v2 scaffold; F1–F8 were fixed during integration and **re-verified as PASS here** (see §4). This report is a fresh destructive pass on the integrated product and finds **new, higher-severity defects**.

---

## 1. Discovered system limits (code-enforced, verified)

| Limit | Value | Where | Verified |
|---|---|---|---|
| Max upload size | 25 MB (`>` strict; 25 MB exact accepted) | `main.py:91` | ✅ streamed cap aborts at 25 MB +1 chunk |
| Max files / batch | 10 (`/api/process`, `/batch/upload`, `/batch/upload/unified`) | — | ✅ 11 → 400 `BATCH_LIMIT` |
| Allowed upload ext | `.docx .pdf .txt` (upload), wider sets for `/ocr`, `/api/process`, `/convert` | — | ✅ |
| Magic-byte check | DOCX `PK\x03\x04`, PDF `%PDF` | — | ✅ spoofs → 400 `INVALID_SIGNATURE` |
| Export text cap | 1 MB (`/api/export/pdf`) | `main.py:93` | ✅ >1 MB → 413 |
| DOCX decompressed cap | 20 MB xml / 5000 paragraphs | `reconstruction_engine.py:18` | ✅ zip-bomb + 6000-para → rejected |
| PDF OCR page cap | 50 pages, 5-page render chunks | `reconstruction_engine.py:60` | code-verified |
| Rate limits | `/upload` `/convert` `/api/process` `/api/export` 5/min; `/batch/*` 2/min | — | ✅ 6th `/upload` → 429 |
| Job timeouts | 300 s (docx/txt/recon), 600 s (pdf→docx) | — | code-verified |
| Auth | **none enforced** (see F5) | — | ✅ all endpoints open |

---

## 2. Findings (highest severity first)

### F1 — Unauthenticated path traversal / arbitrary file read (LFI) — **CRITICAL**
*Category: security / OWASP A01. Newly introduced by the SPA catch-all route.*

The catch-all `@app.get("/{full_path:path}")` joins user input straight onto the dist dir and serves whatever exists:
```py
file_path = FRONTEND_DIST / full_path        # main.py:740
if file_path.exists() and file_path.is_file():
    return FileResponse(file_path)
```
`full_path` is never normalized or confined to `FRONTEND_DIST`. URL-encoded `..` survives client/proxy normalization and escapes the web root.

- **Repro (live uvicorn, verified):**
  - `GET /%2e%2e/%2e%2e/backend/security_manager.py` → **200**, returns full source.
  - `GET /..%2f..%2fbackend%2fmain.py` → **200**, leaks `main.py` incl. `INDICPDF_API_KEY` / `INDICPDF_MASTER_KEY` references.
  - `GET /%2e%2e/%2e%2e/%2e%2e/%2e%2e/%2e%2e/etc/passwd` → **200**, returns the host's `/etc/passwd` (`## User Database`).
- **Expected:** path-escaping requests → 404 and never serve files outside `FRONTEND_DIST`.
- **Actual:** arbitrary file read of anything the server process can read — `.env`, the AES master key, SSH keys, source, system files. No auth required.
- **Impact:** total confidentiality breach; reading the master key also defeats the at-rest encryption (F2).
- **Fix:** resolve and confine — `full = (FRONTEND_DIST / full_path).resolve(); if not full.is_relative_to(FRONTEND_DIST.resolve()): 404`. Prefer Starlette `StaticFiles` (which blocks traversal) for assets and serve `index.html` only for known SPA routes.

### F2 — No master key → every conversion fails; encryption silently self-destructs — **CRITICAL (default config)**
*Category: data integrity / deploy correctness. End-to-end verified.*

`SecurityManager` falls back to a **random per-process** AES-GCM key when `INDICPDF_MASTER_KEY` is unset (`security_manager.py:26-32`). The web (uvicorn) and the RQ worker are **separate processes**, so each encrypts/decrypts with a different key.

- **Repro (real two-process e2e, verified):** web process encrypts an uploaded `hindi.docx` → enqueue → a separate `rq worker` process runs `convert_docx_to_pdf_task` → `decrypt_to_file` raises `cryptography.exceptions.InvalidTag` → **job FAILED, no output**. Reproduced for every queued job in the run.
- **Expected:** documented dev setup (no `.env` exists in repo) should work, or refuse to start.
- **Actual:** with no key set, the entire upload→convert→download pipeline is 100% broken; the failure is a generic `InvalidTag` deep in the worker, not a clear "key not configured" message. Even with a single process, a restart makes all previously-encrypted in-flight files permanently unreadable; multi-replica/multi-worker prod is broken even without restart.
- **Fix:** fail fast at startup if `INDICPDF_MASTER_KEY` is missing/invalid (raise, don't `os.urandom`). Document key generation. Optionally derive worker/web from the same env at import and assert equality.

### F3 — FPDF fallback crashes on **all Indic DOCX** (flagship use case) — **HIGH**
*Category: conversion engine / i18n. Direct-call verified.*

When LibreOffice is absent, `process_docx_to_pdf_final` routes to `process_docx_to_pdf_fpdf_fallback`. For a run whose font name is `None`/"Normal" (the common case), it resolves the font by character only:
```py
resolved_path = font_registry.resolve_font(requested_font, ord(processed_text[0]))   # no script arg
```
But the prebuilt `fonts/fonts_index.json` stores **`unicode_ranges` for 0 of 286 fonts**, so `resolve_font`'s char-based last-resort branch (`char_code in font.unicode_ranges`) can never match. With no script passed, it returns `None` → code falls to `pdf.set_font("helvetica")` → `pdf.write()` of Devanagari →

- **Repro (verified):** `process_docx_to_pdf_final(hindi.docx)` → `FPDFUnicodeEncodingException: Character "न" … outside the range of characters supported by the font used: "helvetica"`. Same for Telugu, mixed. Latin-only DOCX succeeds.
- **Verified root cause:** `resolve_font('Normal', 0x0928)` → `None`; `resolve_font('Normal', 0x0928, script='devanagari')` → a path. The fallback never passes `script`, and the index has no `unicode_ranges`, so the char path is dead.
- **Expected:** Indic DOCX renders (or a clean, reported failure).
- **Actual:** on any LibreOffice-less host, every Indic DOCX→PDF job throws and fails. (In the default no-key config this is masked because F2 fails first — but it is the next failure the moment F2 is fixed without LibreOffice present.)
- **Fix:** in the fallback, detect script from the text and pass `script=` to `resolve_font` (the txt→pdf path already does this); and/or store `unicode_ranges` in the index so the char fallback works.

### F4 — Wrong-script font substitution (Devanagari rendered with a Bengali font) — **HIGH**
*Category: font integrity (the core requirement) / silent corruption.*

`fonts_index.json` mis-tags script coverage: **212 of 286** fonts are tagged `devanagari`, and e.g. `system/Bengali/Lohit-Bengali.ttf` carries `scripts: ["devanagari"]`.

- **Repro (verified):** `font_registry.resolve_font('Normal', 0x0928, script='devanagari')` → `Lohit-Bengali.ttf`. A Bengali font has no Devanagari glyphs → the output renders tofu / missing glyphs.
- **Expected:** Devanagari text resolves to a Devanagari-capable font.
- **Actual:** the script-fallback bucket is polluted; even when fallback fires correctly it can pick a wrong-script face, producing silently garbled PDFs while the report claims success. Directly violates "Font preservation (critical)."
- **Fix:** correct the index builder's script detection (gate on actual codepoint coverage in the cmap, not a loose heuristic); validate that a resolved fallback actually covers the target codepoint before use.

### F5 — API-key auth is defined but enforced on zero routes — **MEDIUM**
*Category: security posture / dead code.*

`get_api_key` (`main.py:45`) with `secrets.compare_digest` is written but never attached as a `Depends`/`Security` on any endpoint (verified by grep + TestClient: all endpoints respond without `X-API-Key`). The auth scaffolding reads as protection that does not exist. Combined with F1 this is material. **Fix:** either wire the dependency onto state-changing routes or remove it so the security model isn't misrepresented.

### F6 — Legacy Indic encodings (Kruti Dev / APS / Anu / Shusha) are empty-stub maps → silent garble — **MEDIUM**
*Category: feature completeness / silent corruption.*

`EncodingManager.legacy_maps` are placeholders (Kruti Dev/Shusha empty; APS/Anu map a single codepoint). `detect_legacy_encoding("Kruti Dev 010")` correctly returns `"KRUTI DEV"`, but `convert_to_unicode("vk", "KRUTI DEV")` returns `"vk"` unchanged.

- **Actual:** a DOCX authored in a legacy 8-bit Indic font is "detected" and logged as a legacy conversion, then passed through **unconverted** — the PDF shows Latin gibberish, and the report lists a `legacy_conversions` entry implying success. **Fix:** ship real mapping tables or explicitly flag legacy-encoded input as unsupported instead of pretending to convert it.

### F7 — Rendered PDF text layer is not reliably extractable (searchability / round-trip) — **MEDIUM**
*Category: output quality / accessibility.*

The FPDF/HarfBuzz path writes shaped glyphs without a usable `ToUnicode` map. Extracting text from the produced TXT→PDF yields broken output, e.g. source `నమస్కారం` → extracted `నమస్కా\x04 \x05రం\x07` (control chars, reordered matras).

- **Impact:** generated PDFs are not searchable/copyable and fail accessibility; `/analyse-pdf-quality` would score them "Not Searchable"; any PDF→DOCX round-trip degrades. (Visual rendering may still look correct — this is the text layer, not necessarily the glyphs.) **Fix:** embed a `ToUnicode` CMap, or note the limitation in the product contract.

### F8 — `/upload` silently drops unsupported files (no error, false 200) — **MEDIUM-LOW**
*Category: UX contract / silent failure.*

`/upload` `continue`s past any non-`.docx/.pdf/.txt` file and returns `200 {"jobs": []}` with no rejection notice.

- **Repro (verified):** `POST /upload` with `evil.exe` → `200`, `jobs: []`. **Inconsistent** with `/api/process`, which returns per-file `{"status":"rejected","detail":…}`. **Fix:** return per-file rejection records (mirror `/api/process`) or a 400 when nothing is processable.

### F9 — `OcrTool.jsx` polling has no timeout and leaks intervals — **LOW**
*Category: UX / front-end resource.*

`OcrTool` (`frontend/src/components/OcrTool.jsx:68`) polls `/status` every 2 s with **no max-attempt cap** and **no unmount cleanup**. If the worker is down (e.g. F2), the job stays `queued` forever → infinite spinner; navigating away leaks the interval. `ReconstructionTool.jsx` already does this correctly (`MAX_POLLS=150`, `useEffect` cleanup) — `OcrTool` should match.

### F10 — Only deva/telu/tamil have a script-fallback bucket — **LOW**
*Category: i18n coverage.* The UI offers Hindi, Telugu, Tamil, Bengali, Gujarati, Kannada, Malayalam, Odia, Punjabi, Sanskrit. But `script_fallback` only has `devanagari/telugu/tamil` keys, and `_detect_language_and_script`/the render paths only branch on those three Unicode blocks. Bengali/Gujarati/Kannada/Malayalam/Odia/Gurmukhi DOCX/TXT rendering has no script-aware fallback (works only on exact font-name match). OCR for them works (Tesseract data present).

### F11 — Indic OCR accuracy is low; correctly surfaced — **INFO (limitation, not a bug)**
Live OCR of rendered `नमस्ते दुनिया` returned `नमसू्‌ते दुनयिा` at **0.40** confidence (matra reordering). The engine correctly flags `requires_review` / `low_confidence_regions` and recommends a sharper scan — the confidence system behaves as designed. Worth setting user expectations: Indic OCR output needs human review.

---

## 3. Security test matrix

| Vector | Result |
|---|---|
| Path traversal (encoded `..`) | ❌ **VULNERABLE (F1)** — reads `/etc/passwd`, source, keys |
| Magic-byte spoof (`%PDF` in `.docx`, `PK` in `.pdf`) | ✅ rejected 400 |
| Extension spoof (`.exe`) | ✅ rejected (but silently on `/upload`, F8) |
| Oversized upload (>25 MB) | ✅ streamed cap, 413 |
| Zip-bomb DOCX (≈25 MB decompressed from 60 KB) | ✅ rejected pre-read |
| Paragraph flood (6000) | ✅ rejected |
| Indic filename header injection | ✅ RFC 6266 `content_disposition`, latin-1 safe |
| Export DoS (huge text) | ✅ 1 MB cap + queued worker render |
| Authentication | ❌ none enforced (F5) |
| At-rest encryption | ⚠️ AES-GCM, but key mgmt broken by default (F2) |

---

## 4. v1 regression re-verification (all PASS)

F1 (Indic filename 500) → fixed via `content_disposition`. F2/F4/F5 (export DoS, pre-validation buffering, zip-bomb) → fixed: queued render, streamed size cap, decompression caps. F3 (silent 200 on failure) → fixed: reconstruction returns `success:false` → `/api/process/result` returns **422**, UI renders a distinct failure card. F6 (no multi-file) → fixed: real multi-file intake with per-file `rejected` status and failure isolation (verified: mixed valid/invalid batch returns per-file records). F7 (PDF masks OCR dep error) → fixed: `_dependency_failure` propagated. F8 (event-loop blocking) → fixed: CPU work moved to RQ workers.

---

## 5. Performance summary

| Operation | Measurement |
|---|---|
| DOCX reconstruction (XML extract) | ~8,600 docs/s in-proc (text-only, no render) |
| Image OCR (1 line, Hindi) | ~0.28 s/image |
| Encrypt+decrypt roundtrip (same key) | correct; chunked 64 KB, low memory |
| `/upload` rate limit | trips at 6th call/min (5/min) |
| DOCX→PDF (FPDF fallback) | Latin OK ~1 KB PDF; **Indic throws (F3)** |

No request/queue timeouts missing now (job_timeout set on all enqueues). No event-loop blocking observed (all heavy work is queued).

---

## 6. Priority recommendations

1. **F1** — confine the SPA catch-all to `FRONTEND_DIST` (or use `StaticFiles`). Ship today; it's an unauthenticated full-filesystem read.
2. **F2** — refuse to start without a valid `INDICPDF_MASTER_KEY`; never fall back to a random per-process key.
3. **F3 / F4** — pass `script=` into the FPDF-fallback font resolution, store `unicode_ranges` in the index, and fix the index builder's script tagging + validate glyph coverage before substituting.
4. **F5 / F6 / F8** — wire or remove the API-key dependency; ship real legacy maps or reject legacy input; return per-file rejections from `/upload`.
5. **F7 / F9 / F10** — embed `ToUnicode` for searchable output; align `OcrTool` polling with `ReconstructionTool`; extend script fallback beyond deva/telu/tamil.

---

## 7. Reproduction assets
Harnesses (re-runnable): `/tmp/qa/harness1.py` (fixtures, security, reconstruction caps), `/tmp/qa/harness2.py` (font integrity, helpers, HTTP layer, traversal, rate limit), `/tmp/qa/e2e.py` (two-process encrypt→worker). Structured results in `/tmp/qa/out/*.json`.

## 8. Fixes applied this session (verified)

| ID | Fix | Verification |
|---|---|---|
| **F1** | `serve_frontend` resolves and confines paths to `FRONTEND_DIST` via `is_relative_to`. | Live uvicorn: encoded-`..` requests for `backend/*.py` and `/etc/passwd` leak **0** bytes; normal SPA + `/health` still 200. New test `tests/test_path_traversal.py`. |
| **F2** | `SecurityManager` raises on missing/invalid `INDICPDF_MASTER_KEY` (no silent random fallback, no silent pad/truncate). Opt-in `INDICPDF_ALLOW_EPHEMERAL_KEY=1` for single-process dev/test. Added `tests/conftest.py`, `.env.example`. | No key → `RuntimeError`; 5-byte key → `RuntimeError`; two-process e2e with a shared key now **decrypts successfully**. |
| **F3** | FPDF fallback now detects script and passes `script=` to `resolve_font`; helvetica branch wrapped so an unrenderable run is skipped (recorded in `unrendered_runs`) instead of aborting the document. | `process_docx_to_pdf_final` on Hindi/Telugu/mixed DOCX produces PDFs (4–13 KB), no `FPDFUnicodeEncodingException`. Full e2e: `status: finished, output_produced: true`. |
| **F4** | `scripts/build_font_index.py` tags a script only when the font covers ≥70% of that script's **core letters** (was: any single codepoint → Bengali fonts mis-tagged via the shared danda). Rebuilt `fonts/fonts_index.json`. | Devanagari-tagged fonts 212→132 (the ones that truly cover it); Lohit-Bengali no longer devanagari. Resolution now returns covering fonts (Hindi→Aparajita, Telugu→Akshar, Tamil→Lohit-Tamil); **0** non-covering fonts in any bucket. New test `tests/test_font_resolution.py`. |
| **F8** | `/upload` emits a per-file `{"status":"rejected","detail":…}` record instead of silently dropping unsupported files. | `.exe` upload → `200` with a rejection record. |
| **F9** | `OcrTool.jsx` polling now has `MAX_POLLS` (≈5 min) cap and a `useEffect` unmount cleanup (parity with `ReconstructionTool`). | Code review; no infinite spinner / interval leak. |

| F5 | Removed the dead `APIKeyHeader`/`get_api_key` scaffolding (wired to zero routes) and documented that the public same-origin API is intentionally unauthenticated, bounded by per-IP rate limits. `INDICPDF_API_KEY` is still read by `retry_logic`. | Behavior-preserving (API was already open); `main.py` imports + 19 routes intact. |
| F6 | `EncodingManager.legacy_supported()` gates on real map coverage (≥32 entries). The FPDF fallback no longer records a fake `legacy_conversions` success for stub encodings — it emits `legacy_unsupported` + a `warnings` entry. | Kruti Dev DOCX → `legacy_unsupported:[…]` + "may be garbled" warning, empty `legacy_conversions`. |
| F7 | **Resolved for Devanagari & Tamil as a side effect of F4** — with a glyph-covering font, fpdf2 emits a correct `/ToUnicode` and `नमस्ते`/`வணக்கம் உலகம்` now extract cleanly. **Telugu remains an upstream fpdf2 2.8.7 + HarfBuzz limitation** (matra-reorder shaping corrupts the text layer for all 96 Telugu fonts; visual rendering is correct). | pypdf/pdfminer extract Deva+Tamil cleanly; Telugu text layer still shows control chars. |

**Still open (documented):** F7-Telugu (fpdf2 shaping limitation in the LibreOffice-less fallback / txt→pdf path — install LibreOffice for fully searchable Telugu output, which the strict path already expects), F10 (only deva/telu/tamil have script-fallback buckets; other Indic scripts now degrade gracefully via the F3 guard rather than crashing), F11 (Indic OCR accuracy — inherent). Regression suite: **43 backend + 16 frontend pass**.

## 9. Change log
- **v2.0 (2026-06-11):** Fresh destructive audit of the integrated build. 11 findings (2 CRITICAL, 2 HIGH, 4 MEDIUM, 2 LOW, 1 INFO). v1 F1–F8 re-verified fixed.
- **v2.1 (2026-06-11):** Fixed F1, F2, F3, F4, F8, F9 with regression tests; rebuilt font index. 43 tests pass.
- **v2.2 (2026-06-11):** Removed dead auth scaffolding (F5); honest legacy-encoding flagging (F6); F7 resolved for Devanagari/Tamil via the F4 font-index fix, Telugu documented as an fpdf2 shaping limitation. 8 of 11 findings now fixed or substantially mitigated.
