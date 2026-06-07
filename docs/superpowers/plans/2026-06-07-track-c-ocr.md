# Track C — OCR Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `/ocr` tool that lets users upload scanned PDFs or images and download extracted text, with Tesseract OCR supporting 9 Indic language packs.

**Architecture:** Server-side OCR via `pytesseract` + `pdf2image`. Scanned PDFs are converted to images page-by-page, then Tesseract extracts text with the user-selected language pack. The job runs in the existing RQ worker queue. A new React page (`/ocr`) reuses existing Dropzone, ProcessingSteps, and SuccessView components.

**Tech Stack:** pytesseract, pdf2image, Pillow, Tesseract OCR (apt), FastAPI, RQ, React 19, Vite

---

## File Map

| Action | Path |
|---|---|
| Modify | `Dockerfile` |
| Modify | `requirements.txt` |
| Create | `backend/ocr_processor.py` |
| Modify | `backend/main.py` |
| Modify | `backend/worker.py` |
| Create | `tests/test_ocr_processor.py` |
| Create | `frontend/src/pages/OcrTool.jsx` |
| Modify | `frontend/src/App.jsx` |
| Modify | `frontend/src/components/Navbar.jsx` |

---

### Task 1: Update Dockerfile with Tesseract

**Files:**
- Modify: `Dockerfile`

- [ ] **Step 1: Read the current Dockerfile**

```bash
cat Dockerfile
```

- [ ] **Step 2: Add Tesseract and Poppler apt packages**

Find the `apt-get install` line (or add one) and add:
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-hin \
    tesseract-ocr-tel \
    tesseract-ocr-tam \
    tesseract-ocr-ben \
    tesseract-ocr-guj \
    tesseract-ocr-kan \
    tesseract-ocr-mal \
    tesseract-ocr-ori \
    tesseract-ocr-pan \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*
```

- [ ] **Step 3: Verify Dockerfile builds locally (optional but recommended)**

```bash
docker build -t indicpdf-test . 2>&1 | tail -5
```

Expected: `Successfully built <id>`

- [ ] **Step 4: Commit**

```bash
git add Dockerfile
git commit -m "feat: add Tesseract OCR + Poppler to Dockerfile (Track C)"
```

---

### Task 2: Add Python dependencies

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add new deps**

Add these three lines to `requirements.txt`:
```
pytesseract
pdf2image
Pillow
```

- [ ] **Step 2: Install locally for development**

```bash
pip install pytesseract pdf2image Pillow
```

- [ ] **Step 3: Verify Tesseract is accessible**

```bash
tesseract --version
python -c "import pytesseract; print(pytesseract.get_tesseract_version())"
```

Expected: Tesseract version printed (e.g. `5.3.x`)

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "feat: add pytesseract, pdf2image, Pillow to requirements (Track C)"
```

---

### Task 3: Write failing tests for ocr_processor

**Files:**
- Create: `tests/test_ocr_processor.py`

- [ ] **Step 1: Write the tests**

```python
# tests/test_ocr_processor.py
import pytest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))


def test_lang_map_contains_all_indic_languages():
    from ocr_processor import LANG_MAP
    required = ["hindi", "telugu", "tamil", "bengali", "gujarati",
                "kannada", "malayalam", "odia", "punjabi", "english", "auto"]
    for lang in required:
        assert lang in LANG_MAP, f"Missing language: {lang}"


def test_lang_map_auto_returns_none():
    from ocr_processor import LANG_MAP
    assert LANG_MAP["auto"] is None


def test_ocr_image_to_text_calls_tesseract(tmp_path):
    img_path = tmp_path / "sample.png"
    img_path.write_bytes(b"fake png data")

    with patch("ocr_processor.Image") as mock_image, \
         patch("ocr_processor.pytesseract") as mock_tess:
        mock_img = MagicMock()
        mock_image.open.return_value = mock_img
        mock_tess.image_to_string.return_value = "extracted text"

        from ocr_processor import ocr_image_to_text
        result = ocr_image_to_text(str(img_path), lang="hindi")

    mock_image.open.assert_called_once_with(str(img_path))
    mock_tess.image_to_string.assert_called_once_with(mock_img, lang="hin")
    assert result == "extracted text"


def test_ocr_image_to_text_auto_uses_multi_lang(tmp_path):
    img_path = tmp_path / "sample.png"
    img_path.write_bytes(b"fake png data")

    with patch("ocr_processor.Image") as mock_image, \
         patch("ocr_processor.pytesseract") as mock_tess:
        mock_image.open.return_value = MagicMock()
        mock_tess.image_to_string.return_value = "text"

        from ocr_processor import ocr_image_to_text
        ocr_image_to_text(str(img_path), lang="auto")

    call_lang = mock_tess.image_to_string.call_args[1]["lang"]
    assert "hin" in call_lang
    assert "eng" in call_lang


def test_ocr_pdf_to_text_processes_each_page(tmp_path):
    pdf_path = tmp_path / "scan.pdf"
    pdf_path.write_bytes(b"fake pdf")

    mock_images = [MagicMock(), MagicMock()]

    with patch("ocr_processor.convert_from_path", return_value=mock_images) as mock_convert, \
         patch("ocr_processor.pytesseract") as mock_tess:
        mock_tess.image_to_string.side_effect = ["page 1 text", "page 2 text"]

        from ocr_processor import ocr_pdf_to_text
        result = ocr_pdf_to_text(str(pdf_path), lang="telugu")

    mock_convert.assert_called_once_with(str(pdf_path), dpi=300)
    assert mock_tess.image_to_string.call_count == 2
    assert "page 1 text" in result
    assert "page 2 text" in result
    assert "Page Break" in result


def test_unsupported_lang_falls_back_to_english():
    with patch("ocr_processor.Image") as mock_image, \
         patch("ocr_processor.pytesseract") as mock_tess:
        mock_image.open.return_value = MagicMock()
        mock_tess.image_to_string.return_value = "text"

        from ocr_processor import ocr_image_to_text
        ocr_image_to_text("/fake/path.png", lang="klingon")

    call_lang = mock_tess.image_to_string.call_args[1]["lang"]
    assert call_lang == "eng"
```

- [ ] **Step 2: Run tests — expect ImportError**

```bash
python -m pytest tests/test_ocr_processor.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'ocr_processor'`

---

### Task 4: Implement ocr_processor.py

**Files:**
- Create: `backend/ocr_processor.py`

- [ ] **Step 1: Write the module**

```python
# backend/ocr_processor.py
"""
OCR processing module using Tesseract for Indic script support.
Supports scanned PDFs and images. Runs server-side via RQ worker.
"""
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
from pathlib import Path

# Maps user-facing language names to Tesseract language codes
LANG_MAP = {
    "hindi":     "hin",
    "telugu":    "tel",
    "tamil":     "tam",
    "bengali":   "ben",
    "gujarati":  "guj",
    "kannada":   "kan",
    "malayalam": "mal",
    "odia":      "ori",
    "punjabi":   "pan",
    "english":   "eng",
    "auto":      None,   # None triggers multi-language fallback
}

# Multi-language string used when lang=auto
AUTO_LANG = "hin+tel+tam+ben+guj+kan+mal+ori+eng"


def _resolve_lang(lang: str) -> str:
    """Convert user-facing language name to Tesseract lang string."""
    tess_code = LANG_MAP.get(lang.lower())
    if tess_code is None and lang.lower() != "auto":
        # Unknown language — fall back to English
        return "eng"
    return tess_code or AUTO_LANG


def ocr_image_to_text(file_path: str, lang: str = "auto") -> str:
    """
    Extract text from an image file using Tesseract OCR.

    Args:
        file_path: Absolute path to JPG/PNG/TIFF image.
        lang: Language name (e.g. 'hindi', 'telugu', 'auto').

    Returns:
        Extracted text string.
    """
    tess_lang = _resolve_lang(lang)
    img = Image.open(file_path)
    return pytesseract.image_to_string(img, lang=tess_lang)


def ocr_pdf_to_text(file_path: str, lang: str = "auto") -> str:
    """
    Extract text from all pages of a scanned PDF.

    Args:
        file_path: Absolute path to scanned PDF.
        lang: Language name (e.g. 'hindi', 'telugu', 'auto').

    Returns:
        Full extracted text, with page breaks between pages.
    """
    tess_lang = _resolve_lang(lang)
    images = convert_from_path(file_path, dpi=300)
    page_texts = [
        pytesseract.image_to_string(img, lang=tess_lang)
        for img in images
    ]
    return "\n\n--- Page Break ---\n\n".join(page_texts)


def run_ocr(file_path: str, lang: str = "auto") -> str:
    """
    Auto-detect file type and run appropriate OCR pipeline.

    Args:
        file_path: Path to PDF or image file.
        lang: Language name.

    Returns:
        Extracted text string.
    """
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return ocr_pdf_to_text(file_path, lang)
    elif ext in {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp"}:
        return ocr_image_to_text(file_path, lang)
    else:
        raise ValueError(f"Unsupported file type for OCR: {ext}")
```

- [ ] **Step 2: Run the tests**

```bash
python -m pytest tests/test_ocr_processor.py -v
```

Expected: All 6 tests PASS

- [ ] **Step 3: Commit**

```bash
git add backend/ocr_processor.py tests/test_ocr_processor.py
git commit -m "feat: implement OCR processor with Indic language support (Track C)"
```

---

### Task 5: Add /ocr API endpoint

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Read the existing upload endpoint for reference**

```bash
grep -n "upload\|job_id\|enqueue" backend/main.py | head -20
```

- [ ] **Step 2: Add the OCR endpoint**

Add after the existing `/upload` endpoint in `backend/main.py`:

```python
# backend/main.py — add this import at the top with other imports
from backend.ocr_processor import LANG_MAP  # for validation

# Add this endpoint after the existing /upload route
@app.post("/ocr")
async def ocr_upload(
    file: UploadFile = File(...),
    lang: str = Form(default="auto"),
):
    """
    Accept a scanned PDF or image, enqueue OCR job, return job_id.
    """
    allowed_exts = {".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {', '.join(allowed_exts)}"
        )
    if lang not in LANG_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown language: {lang}. Valid: {', '.join(LANG_MAP.keys())}"
        )

    job_id = str(uuid.uuid4())
    input_path = UPLOAD_DIR / f"{job_id}_input{ext}"

    contents = await file.read()
    input_path.write_bytes(contents)

    queue.enqueue(
        "backend.worker.process_ocr",
        job_id=job_id,
        file_path=str(input_path),
        lang=lang,
        job_timeout=300,
    )

    return {"job_id": job_id}
```

- [ ] **Step 3: Verify the server starts without errors**

```bash
cd /Users/jay/IndicPdf-Main
uvicorn backend.main:app --reload --port 8001 &
sleep 3
curl -s http://localhost:8001/health
kill %1
```

Expected: `{"status":"ok"}` or similar health response

- [ ] **Step 4: Commit**

```bash
git add backend/main.py
git commit -m "feat: add /ocr endpoint to FastAPI (Track C)"
```

---

### Task 6: Add OCR job to RQ worker

**Files:**
- Modify: `backend/worker.py`

- [ ] **Step 1: Read the existing worker job handler for reference**

```bash
grep -n "def process\|job_id\|output" backend/worker.py | head -20
```

- [ ] **Step 2: Add process_ocr function**

Add to `backend/worker.py`:

```python
# backend/worker.py — add this import at top
from backend.ocr_processor import run_ocr

# Add this function alongside existing process_* functions
def process_ocr(job_id: str, file_path: str, lang: str = "auto") -> dict:
    """
    RQ worker job: run OCR on uploaded file, save result as .txt.

    Args:
        job_id: Unique job identifier.
        file_path: Absolute path to the uploaded file.
        lang: Language code (e.g. 'hindi', 'auto').

    Returns:
        dict with output_path and char_count.
    """
    try:
        text = run_ocr(file_path, lang)

        output_path = Path(file_path).parent / f"{job_id}_output.txt"
        output_path.write_text(text, encoding="utf-8")

        # Clean up input file
        Path(file_path).unlink(missing_ok=True)

        return {
            "output_path": str(output_path),
            "char_count": len(text),
            "lang": lang,
        }
    except Exception as exc:
        Path(file_path).unlink(missing_ok=True)
        raise RuntimeError(f"OCR failed: {exc}") from exc
```

- [ ] **Step 3: Commit**

```bash
git add backend/worker.py
git commit -m "feat: add process_ocr job to RQ worker (Track C)"
```

---

### Task 7: Create OcrTool frontend page

**Files:**
- Create: `frontend/src/pages/OcrTool.jsx`

- [ ] **Step 1: Write the page**

```jsx
// frontend/src/pages/OcrTool.jsx
import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import axios from 'axios';
import ToolLayout from '../components/ToolLayout';
import ProcessingSteps from '../components/ProcessingSteps';
import SuccessView from '../components/SuccessView';

const LANGUAGES = [
  { value: 'auto',      label: 'Auto Detect' },
  { value: 'hindi',     label: 'Hindi (Devanagari)' },
  { value: 'telugu',    label: 'Telugu' },
  { value: 'tamil',     label: 'Tamil' },
  { value: 'bengali',   label: 'Bengali' },
  { value: 'gujarati',  label: 'Gujarati' },
  { value: 'kannada',   label: 'Kannada' },
  { value: 'malayalam', label: 'Malayalam' },
  { value: 'odia',      label: 'Odia' },
  { value: 'punjabi',   label: 'Punjabi' },
  { value: 'english',   label: 'English' },
];

const ACCEPTED_TYPES = {
  'application/pdf': ['.pdf'],
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/png': ['.png'],
  'image/tiff': ['.tiff', '.tif'],
};

export default function OcrTool() {
  const [file, setFile]       = useState(null);
  const [lang, setLang]       = useState('auto');
  const [status, setStatus]   = useState('idle'); // idle | uploading | processing | done | error
  const [jobId, setJobId]     = useState(null);
  const [resultUrl, setResultUrl] = useState(null);
  const [errorMsg, setErrorMsg]   = useState('');
  const [steps, setSteps]         = useState([
    { label: 'Uploading file',    state: 'pending' },
    { label: 'Running OCR',       state: 'pending' },
    { label: 'Extracting text',   state: 'pending' },
  ]);

  const updateStep = (index, state) =>
    setSteps(prev => prev.map((s, i) => i === index ? { ...s, state } : s));

  const onDrop = useCallback((accepted) => {
    if (accepted.length > 0) setFile(accepted[0]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    multiple: false,
  });

  const handleConvert = async () => {
    if (!file) return;
    setStatus('uploading');
    updateStep(0, 'active');

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('lang', lang);

      const { data } = await axios.post('/ocr', formData);
      setJobId(data.job_id);
      updateStep(0, 'done');
      updateStep(1, 'active');
      setStatus('processing');

      // Poll for completion
      const poll = setInterval(async () => {
        try {
          const { data: status } = await axios.get(`/status/${data.job_id}`);
          if (status.status === 'finished') {
            clearInterval(poll);
            updateStep(1, 'done');
            updateStep(2, 'done');
            setResultUrl(`/download/${data.job_id}`);
            setStatus('done');
          } else if (status.status === 'failed') {
            clearInterval(poll);
            setStatus('error');
            setErrorMsg('OCR processing failed. Please try again.');
          }
        } catch {
          clearInterval(poll);
          setStatus('error');
          setErrorMsg('Connection error while checking status.');
        }
      }, 2000);
    } catch (err) {
      setStatus('error');
      setErrorMsg(err.response?.data?.detail || 'Upload failed.');
      updateStep(0, 'error');
    }
  };

  const handleReset = () => {
    setFile(null); setStatus('idle'); setJobId(null);
    setResultUrl(null); setErrorMsg('');
    setSteps(steps.map(s => ({ ...s, state: 'pending' })));
  };

  return (
    <ToolLayout
      title="OCR — Extract Text from Scanned Documents"
      description="Upload a scanned PDF or image. We'll extract the text using Tesseract with full Indic script support."
    >
      {status === 'idle' && (
        <div className="workspace-card p-8">
          {/* Language selector */}
          <div className="mb-6">
            <label className="block text-sm font-black uppercase tracking-widest text-text-muted mb-2">
              Document Language
            </label>
            <select
              value={lang}
              onChange={e => setLang(e.target.value)}
              className="w-full bg-surface border border-border rounded-xl p-3 text-text font-semibold focus:outline-none focus:border-primary"
            >
              {LANGUAGES.map(l => (
                <option key={l.value} value={l.value}>{l.label}</option>
              ))}
            </select>
          </div>

          {/* Dropzone */}
          <div
            {...getRootProps()}
            className={`drop-zone ${isDragActive ? 'dragover' : ''} ${file ? 'has-file' : ''}`}
          >
            <input {...getInputProps()} />
            {file ? (
              <div>
                <p className="text-2xl mb-2">📄</p>
                <p className="font-black text-text">{file.name}</p>
                <p className="text-text-muted text-sm mt-1">{(file.size / 1024).toFixed(1)} KB</p>
              </div>
            ) : (
              <div>
                <p className="text-4xl mb-4">🔍</p>
                <p className="font-black text-lg">Drop a scanned PDF or image here</p>
                <p className="text-text-muted text-sm mt-2">PDF, JPG, PNG, TIFF supported</p>
              </div>
            )}
          </div>

          <button
            className="action-btn"
            disabled={!file}
            onClick={handleConvert}
          >
            Extract Text
          </button>
        </div>
      )}

      {(status === 'uploading' || status === 'processing') && (
        <ProcessingSteps steps={steps} />
      )}

      {status === 'done' && (
        <SuccessView
          downloadUrl={resultUrl}
          fileName={`${file?.name?.replace(/\.[^.]+$/, '')}_ocr.txt`}
          onReset={handleReset}
          message="Text extracted successfully!"
        />
      )}

      {status === 'error' && (
        <div className="workspace-card p-8 text-center">
          <p className="text-red-500 font-black text-lg mb-4">⚠ {errorMsg}</p>
          <button className="action-btn" onClick={handleReset}>Try Again</button>
        </div>
      )}
    </ToolLayout>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/OcrTool.jsx
git commit -m "feat: add OcrTool React page (Track C)"
```

---

### Task 8: Wire routing and navbar

**Files:**
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/components/Navbar.jsx`

- [ ] **Step 1: Add lazy import and route to App.jsx**

In `frontend/src/App.jsx`, add after the existing lazy imports:

```jsx
const OcrTool = React.lazy(() => import('./pages/OcrTool'));
```

Add inside `<Routes>`:

```jsx
<Route path="/ocr" element={<OcrTool />} />
```

- [ ] **Step 2: Add OCR link to Navbar.jsx**

In `frontend/src/components/Navbar.jsx`, add a nav link alongside the existing ones:

```jsx
<li>
  <Link to="/ocr" className="no-underline text-text-muted text-[0.8rem] font-black uppercase hover:text-primary transition-all tracking-widest">
    OCR
  </Link>
</li>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.jsx frontend/src/components/Navbar.jsx
git commit -m "feat: add /ocr route and navbar link (Track C)"
```

---

### Task 9: End-to-end test + ECC review

- [ ] **Step 1: Start the dev server**

```bash
cd /Users/jay/IndicPdf-Main/frontend && npm run dev &
cd /Users/jay/IndicPdf-Main && uvicorn backend.main:app --reload &
```

- [ ] **Step 2: Open the OCR page**

Navigate to `http://localhost:5173/ocr`. Verify:
- Language selector visible with all 10 options
- Dropzone accepts PDF, JPG, PNG
- After drop, filename shown
- "Extract Text" button enabled

- [ ] **Step 3: Run ecc:fastapi-review on main.py**

```
/fastapi-review backend/main.py
```

Fix any issues flagged.

- [ ] **Step 4: Run ecc:python-review on ocr_processor.py**

```
/python-review backend/ocr_processor.py
```

- [ ] **Step 5: Run ecc:react-review on OcrTool.jsx**

```
/react-review frontend/src/pages/OcrTool.jsx
```

- [ ] **Step 6: Run ecc:security-scan**

```
/security-scan
```

- [ ] **Step 7: Create PR**

```
/pr
```

- [ ] **Step 8: Final commit**

```bash
git add -A
git commit -m "feat: complete Track C — OCR with Indic language support"
```
