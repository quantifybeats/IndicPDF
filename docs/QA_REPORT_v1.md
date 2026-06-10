# IndicPDF — QA & Reliability Audit Report

- **Report version:** v1.0
- **Date:** 2026-06-10
- **Author role:** Senior QA Engineer + Systems Reliability Auditor
- **Build under test:** `backend/main.py`, `backend/hybrid_engine.py`, `frontend/src/App.tsx` (v2 scaffold per `docs/system.md`)
- **Method:** Static code audit + live testing against the real, code-enforced limits. Backend run under uvicorn and FastAPI `TestClient` in a Linux sandbox (Python 3.10). OCR stack (`paddleocr`) intentionally absent to exercise the dependency-failure path the same way the shipped venv would.
- **Prior reports:** none found in `/docs` (only `system.md`). No regression baseline existed, so findings are also diffed against the `system.md` spec.

---

## 1. Discovered system limits (treated as hard boundaries)

| Limit | Enforced value | Source | Notes |
|---|---|---|---|
| Max file size | **25 MB** (`26214400` bytes) | `main.py:19` `MAX_FILE_SIZE_BYTES` | Rejected only when `size > limit`; exactly 25 MB is **accepted**. |
| Max files per upload | **1** | `main.py:209`, `App.tsx:92,231` | Single `UploadFile`; UI reads `files[0]`, no `multiple`. |
| Request payload limit (`/api/export/pdf`) | **none** | `main.py:217` | Unbounded JSON body. |
| Timeout thresholds | **none** | — | No request/processing timeouts anywhere. |
| Queue / concurrency limits | **none** | `main.py:208` | One shared engine; CPU work runs inside `async def`. |
| Allowed extensions | `.pdf .png .jpg .jpeg .docx` | `main.py:18` | Case-insensitive. |

> **Scope note:** the brief lists *multi-file / batch upload* as a core feature. It does **not exist** in this codebase (see F6). Multi-file flow, per-file status, failure isolation, and batch progress could not be tested because they are unimplemented; this is itself reported as a high-impact gap.

---

## 2. Findings (highest priority first)

### F1 — Indic-language filename crashes PDF export (HTTP 500) — **HIGH**
*Category: boundary / i18n / unhandled exception. This is the product's primary use case.*

`/api/export/pdf` builds a `Content-Disposition` header from the user filename. `safe_pdf_filename()` keeps any character where `c.isalnum()` is true — and **Telugu/Hindi characters return `True`** — so Indic characters survive into the header. Starlette then encodes headers as **latin-1**, which cannot represent Telugu/Devanagari, raising `UnicodeEncodeError` → unhandled **500**.

- **Repro:** `POST /api/export/pdf` with `{"clean_text":"తెలుగు","filename":"తెలుగు-పత్రం.docx"}`.
- **Observed:** `UnicodeEncodeError: 'latin-1' codec can't encode character 'త'` → 500.
- **Verified root cause:** `'త'.isalnum() == True`; `safe_pdf_filename('తెలుగు-పత్రం.docx') -> 'త-ల-గ--పత-ర-.pdf'` (non-latin-1).
- **Real-world trigger:** the UI sends `result.language_metadata.input_filename` as `filename` (`App.tsx:152`). Any user who uploads `నివేదిక.docx` / `పత్రం.docx` and clicks **Download PDF** hits a 500. Both Telugu and Hindi reproduce.
- **Fix direction:** transliterate/strip to ASCII for the `filename=` token and use RFC 5987 `filename*=UTF-8''…` for the Unicode name; or restrict the sanitizer to `[A-Za-z0-9._-]` instead of `isalnum()`.

### F2 — `/api/export/pdf` has no payload limit and renders synchronously (DoS) — **HIGH**
*Category: performance / resource exhaustion / event-loop blocking.*

The export body is unbounded and WeasyPrint rendering runs inline on the event loop.

- **Repro / measured scaling** (`clean_text` length → response):
  - 28,000 chars → 200, **0.24 s**
  - 280,000 chars → 200, **4.19 s**
  - 840,000 chars → 200, **28.23 s**
  - ~2,000,000 chars → did **not** complete within 40 s (request hangs).
- **Impact:** one large export pins a CPU and, because it runs in `async def` with no `run_in_threadpool`, blocks the entire server (all other requests + `/api/health` stall) for the full render. No timeout aborts it.
- **Fix direction:** cap `clean_text`/`layout_structure` size, offload `write_pdf()` to a thread/process pool, add a render timeout.

### F3 — Processing failures return HTTP 200 → silent failure / misleading "success" UX — **HIGH**
*Category: UX / contract. Directly violates `system.md` ("Flag or reject inputs below minimum thresholds", "Avoid silent corrections", surface failures).*

Every failure mode returns **200 OK** with `status:"processing_incomplete"`, empty `clean_text`, and `0.0` confidences:

| Input | HTTP | status / issues |
|---|---|---|
| Corrupt docx (not a zip) | 200 | `docx_extraction_failed` |
| docx with no text | 200 | `docx_contains_no_extractable_text` |
| Garbage `.pdf` bytes | 200 | `pdf_processing_failed` |
| Real PDF, OCR engine missing | 200 | `pdf_ocr_returned_no_text` |
| Valid PNG, OCR engine missing | 200 | `ocr_dependency_missing` |

The frontend only shows its red error card when `!response.ok` (`App.tsx:116`). Since these are 200, it instead renders the full **"Processing Result"** panel: 0.0% everywhere, blank "Reconstructed Text", and a green/normal layout that reads as success. There is no dead-state spinner, but there is a **false-success state**, which is worse for trust.

- **Fix direction:** return 4xx/422 for unusable inputs (or a top-level `success:false`), and have the UI render a distinct failure state for `processing_incomplete`.

### F4 — Upload fully buffered into memory *before* size validation — **MEDIUM-HIGH**
*Category: memory mismanagement / boundary.*

```py
payload = await file.read()        # entire body in RAM first
validate_upload(file, len(payload)) # 413 only checked afterward
```

There is no global request-body cap, so a 2 GB POST to `/api/process` is read fully into memory before the 25 MB check rejects it. The limit is reactive, not protective.
- **Verified:** size boundary behaves correctly at the value level — `25 MB−1` and `25 MB` accepted, `25 MB+1 B` and `25 MB+1 KB` → **413** with a clear message — but only *after* the whole payload is in memory.
- **Fix direction:** enforce a max body size at the ASGI/server layer (e.g. reject by `Content-Length` / stream-and-abort) before reading.

### F5 — 25 MB limit guards compressed bytes only; docx decompression bomb bypasses it — **MEDIUM-HIGH**
*Category: resource amplification / memory.*

The size check is on the uploaded (compressed) bytes. DOCX is a zip.
- **Repro:** an **81 KB** `.docx` whose `word/document.xml` decompresses to ~20 MB → **200**, processed in 0.84 s, producing **40,000 layout segments**, a ~**20 MB** `clean_text`, and a per-word `word_confidence` list — all held in memory and serialized into the JSON response. A handful of concurrent such uploads exhausts memory while each stays "within" the 25 MB upload limit.
- **Fix direction:** cap decompressed size / paragraph count during `_extract_docx_text`; bound segment counts.

### F6 — Multi-file / batch upload is unimplemented (core-feature gap) — **MEDIUM**
*Category: missing functionality. The brief's priority area.*

`/api/process` accepts a single `UploadFile`. Sending two parts in the `file` field returns **200 and silently processes only the last file**, discarding the first (no error, no per-file status). The UI `<input>` lacks `multiple` and reads only `e.target.files[0]`. Consequently none of the requested batch behaviors exist: per-file status tracking, failure isolation, batch progress indicators. Any "multi-file" testing is blocked until this is built.

### F7 — PDF path masks the OCR dependency failure (inconsistent diagnostics) — **MEDIUM**
*Category: error-reporting consistency.*

With the OCR engine missing, the **image** path correctly reports `ocr_dependency_missing` + `processing_incomplete`, but the **PDF** path (which renders pages to images internally) swallows the per-page dependency result and reports the misleading `pdf_ocr_returned_no_text` / `no_text_extracted`. Operators cannot distinguish "server misconfigured" from "blank scan." (`hybrid_engine.py:262-287` discards `image_result` dependency signals.)

### F8 — No concurrency limit; CPU-bound work on the event loop — **MEDIUM**
*Category: concurrency / throughput.*

`process_document` / `export_pdf` are `async def` but call synchronous, CPU-heavy work (PyMuPDF render, OCR, WeasyPrint) with no `run_in_threadpool` and no concurrency cap or timeout. Light DOCX requests are fine (10 serial = 0.02 s), but a single heavy PDF or large export (F2) head-of-line-blocks every other request, including `/api/health`. Under real load near capacity this manifests as latency cliffs rather than graceful queueing.

### F9 — Exactly-at-limit acceptance (expected behavior, documented) — **LOW**
25 MB exact is accepted because the guard is strict `>`. This is consistent with the "Maximum supported size is 25 MB" message. No change required; recorded so it isn't re-flagged as off-by-one.

### F10 — No client-side size/type pre-check — **LOW**
*Category: UX.* The UI performs no size check before upload, so a user can select a multi-GB file and wait through a full transfer only to receive a 413. Minor: the `accept` attribute omits a literal `.jpg` (relies on `image/jpeg`).

### F11 — Empty filename yields a developer-facing 422 — **LOW**
`POST /api/process` with an empty filename returns a pydantic 422 (`Expected UploadFile, received str`) instead of the clean 400 used for other invalid inputs.

### F12 — Security checks that PASSED (positive findings) — **INFO**
- **Path traversal:** `filename:"../../etc/passwd"` → safely reduced to `passwd.pdf`.
- **Template injection / XSS in PDF:** Jinja `autoescape` is on; `<script>…</script>` and `{{7*7}}` in `clean_text` are escaped, not executed — no SSTI/stored-XSS in the generated PDF.
- **Extension spoofing:** `x.pdf.exe`, trailing-space `x.pdf `, and extension-less files are correctly rejected (400); uppercase `.PDF` correctly accepted.

---

## 3. Spec-vs-implementation gaps (`system.md`)

| Spec promise | Status |
|---|---|
| "Flag or reject inputs below minimum thresholds" | **Not met** — failures return 200 (F3). |
| Multi-format input incl. batch handling | Single-file only (F6). |
| Confidence scoring at word/line/document/layout | Present, but word/line confidences are duplicated from the document aggregate (`main.py:128-129`), not independently computed — they are placeholders, not real per-token scores. |
| "Automatic deletion within 2 hours" / ephemeral | Asserted in the response contract only; nothing in code persists or schedules deletion (no storage exists), so the claim is currently cosmetic metadata. |
| End-to-end encryption / password-protected access | Not implemented in this scaffold (expected for v2). |

---

## 4. Priority recommendations

1. **F1** — fix the export filename sanitizer + header encoding (ships a 500 on the product's flagship language). 
2. **F3** — stop returning 200 for unusable inputs; give the UI a real failure state.
3. **F2 / F4 / F5** — add body-size caps (upload *and* export), decompression bounds, and move blocking work off the event loop with timeouts.
4. **F6** — implement true multi-file intake with per-file status and failure isolation, or remove "batch" from the product description until built.
5. **F7** — propagate the real dependency error through the PDF path.

---

## 5. Reproduction assets
Test scripts used for this report (re-runnable against a local backend):
- `outputs/qa/test_boundaries.py` — size/extension/empty/format boundary matrix.
- `outputs/qa/test_inproc.py` — export endpoint, payload scaling, zip-bomb, dependency-masking (FastAPI `TestClient`).

## 6. Change log
- **v1.0 (2026-06-10):** Initial audit. 12 findings (3 HIGH, 4 MED, 2 LOW, 3 INFO/positive). No prior report to regress against.
- **v1.1 (2026-06-10):** v2 scaffold merged into IndicPdf-Main
  (`docs/superpowers/plans/2026-06-10-v2-engine-integration.md`).
  F1–F8 addressed in the integrated codebase; donor repo retired.
