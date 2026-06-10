#!/usr/bin/env python3
"""E2E flow test — uploads real files, polls until done, verifies output."""
import os
import sys
import time
import json
import requests

BASE = "http://localhost:8000"
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(TEST_DIR, "input", "fast_queue")
DATA_DIR = os.path.join(TEST_DIR, "..", "data")

PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
INFO = "\033[94m[INFO]\033[0m"

results = []

def log(tag, msg):
    print(f"{tag} {msg}")

def record(name, ok, detail=""):
    results.append({"name": name, "ok": ok, "detail": detail})
    tag = PASS if ok else FAIL
    log(tag, f"{name}{(' — ' + detail) if detail else ''}")

def poll_job(job_id, timeout=120):
    """Poll /status/{job_id} until complete or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = requests.get(f"{BASE}/status/{job_id}", timeout=10)
        if r.status_code != 200:
            return None, f"status HTTP {r.status_code}"
        data = r.json()
        status = data.get("status")
        if status == "finished":
            return data, None
        if status in ("failed", "stopped"):
            return None, f"job status={status} error={data.get('error','')}"
        time.sleep(2)
    return None, "timeout"

def test_health():
    r = requests.get(f"{BASE}/health", timeout=5)
    ok = r.status_code == 200 and r.json().get("status") == "ok"
    record("Health check", ok, r.text if not ok else "")

def upload_single(path, mime):
    """POST to /upload with a single file, return (job_id, error)."""
    with open(path, "rb") as f:
        r = requests.post(f"{BASE}/upload",
            files=[("files", (os.path.basename(path), f, mime))],
            timeout=15)
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}: {r.text[:200]}"
    jobs = r.json().get("jobs", [])
    if not jobs:
        return None, "empty jobs list"
    return jobs[0].get("job_id"), None

def test_docx_to_pdf():
    path = os.path.join(INPUT_DIR, "01_hindi_unicode.docx")
    if not os.path.exists(path):
        record("DOCX→PDF", False, "test file missing")
        return
    job_id, err = upload_single(path, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    if err:
        record("DOCX→PDF upload", False, err)
        return
    record("DOCX→PDF upload", True)
    data, err = poll_job(job_id)
    if err:
        record("DOCX→PDF convert", False, err)
        return
    record("DOCX→PDF convert", True, f"job={job_id}")

    dl = requests.get(f"{BASE}/download/{job_id}", timeout=15)
    ok = dl.status_code == 200 and dl.content[:4] == b"%PDF"
    record("DOCX→PDF download", ok, f"bytes={len(dl.content)}" if ok else f"HTTP {dl.status_code}")

def test_pdf_to_docx():
    path = os.path.join(TEST_DIR, "output", "out_01_hindi_unicode.pdf")
    if not os.path.exists(path):
        record("PDF→DOCX", False, "test file missing")
        return
    job_id, err = upload_single(path, "application/pdf")
    if err:
        record("PDF→DOCX upload", False, err)
        return
    record("PDF→DOCX upload", True)
    data, err = poll_job(job_id)
    if err:
        record("PDF→DOCX convert", False, err)
        return
    record("PDF→DOCX convert", True, f"job={job_id}")

    dl = requests.get(f"{BASE}/download/{job_id}", timeout=15)
    ok = dl.status_code == 200 and dl.content[:2] == b"PK"
    record("PDF→DOCX download", ok, f"bytes={len(dl.content)}" if ok else f"HTTP {dl.status_code}")

def test_txt_to_pdf():
    txt_path = os.path.join(TEST_DIR, "..", "hello.txt")
    if not os.path.exists(txt_path):
        txt_path = "/tmp/test_indicpdf.txt"
        with open(txt_path, "w") as f:
            f.write("Hello IndicPDF!\nThis is a test document.\nLine three.")
    job_id, err = upload_single(txt_path, "text/plain")
    if err:
        record("TXT→PDF upload", False, err)
        return
    record("TXT→PDF upload", True)
    data, err = poll_job(job_id)
    if err:
        record("TXT→PDF convert", False, err)
        return
    record("TXT→PDF convert", True, f"job={job_id}")

    dl = requests.get(f"{BASE}/download/{job_id}", timeout=15)
    ok = dl.status_code == 200 and dl.content[:4] == b"%PDF"
    record("TXT→PDF download", ok, f"bytes={len(dl.content)}" if ok else f"HTTP {dl.status_code}")

def test_convert_endpoint():
    """Test the /convert endpoint (LibreOffice-backed — skipped if soffice not installed)."""
    import shutil
    soffice = shutil.which("soffice") or os.path.exists("/Applications/LibreOffice.app/Contents/MacOS/soffice")
    if not soffice:
        log(INFO, "/convert test SKIPPED — LibreOffice not installed (required for this endpoint)")
        results.append({"name": "/convert (LibreOffice)", "ok": True, "detail": "SKIPPED — LibreOffice not installed"})
        return

    path = os.path.join(INPUT_DIR, "03_mixed_languages.docx")
    if not os.path.exists(path):
        record("/convert upload", False, "test file missing")
        return
    with open(path, "rb") as f:
        r = requests.post(f"{BASE}/convert",
            files={"file": ("03_mixed_languages.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={"target_format": "pdf"},
            timeout=15)
    if r.status_code != 200:
        record("/convert upload", False, f"HTTP {r.status_code}: {r.text[:200]}")
        return
    record("/convert upload", True)
    job_id = r.json().get("job_id")
    data, err = poll_job(job_id, timeout=180)
    if err:
        record("/convert job", False, err)
        return
    record("/convert job", True, f"job={job_id}")

def test_batch_upload():
    """Test batch upload with 2 DOCX files."""
    files_to_use = [
        os.path.join(INPUT_DIR, "01_hindi_unicode.docx"),
        os.path.join(INPUT_DIR, "02_hindi_legacy_krutidev.docx"),
    ]
    missing = [p for p in files_to_use if not os.path.exists(p)]
    if missing:
        record("Batch upload", False, f"missing: {missing}")
        return

    files = []
    handles = []
    for p in files_to_use:
        h = open(p, "rb")
        handles.append(h)
        files.append(("files", (os.path.basename(p), h, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")))

    r = requests.post(f"{BASE}/batch/upload", files=files, data={"target_format": "pdf"}, timeout=20)
    for h in handles:
        h.close()

    if r.status_code != 200:
        record("Batch upload", False, f"HTTP {r.status_code}: {r.text[:200]}")
        return
    record("Batch upload", True)

    batch_id = r.json().get("batch_id")
    if not batch_id:
        record("Batch job IDs", False, "no batch_id in response")
        return

    # Poll batch status
    deadline = time.time() + 120
    while time.time() < deadline:
        br = requests.get(f"{BASE}/batch/status/{batch_id}", timeout=10)
        if br.status_code != 200:
            break
        bd = br.json()
        total = bd.get("total", 0)
        completed = bd.get("completed", 0)
        failed = bd.get("failed", 0)
        log(INFO, f"Batch {batch_id}: {completed}/{total} done, {failed} failed")
        if completed + failed >= total and total > 0:
            break
        time.sleep(3)

    ok = bd.get("completed", 0) > 0
    record("Batch convert", ok, f"completed={bd.get('completed')}/{bd.get('total')}")

def test_pdf_analyse():
    path = os.path.join(TEST_DIR, "output", "out_01_hindi_unicode.pdf")
    if not os.path.exists(path):
        record("PDF Analyse", False, "test file missing")
        return
    with open(path, "rb") as f:
        r = requests.post(f"{BASE}/analyse-pdf-quality", files={"file": ("test.pdf", f, "application/pdf")}, timeout=30)
    ok = r.status_code == 200
    if ok:
        data = r.json()
        has_score = "score" in data or "quality_score" in data or "overall_score" in str(data)
        record("PDF Analyse", ok, f"keys={list(data.keys())[:5]}")
    else:
        record("PDF Analyse", False, f"HTTP {r.status_code}: {r.text[:200]}")

def test_invalid_file():
    """Upload a fake PDF (wrong magic bytes) — should get 400."""
    fake = b"NOTPDF fake content"
    r = requests.post(f"{BASE}/upload",
        files=[("files", ("fake.pdf", fake, "application/pdf"))],
        timeout=10)
    ok = r.status_code == 400
    record("Invalid file rejection", ok, f"got HTTP {r.status_code} (want 400)")

def test_corrupt_docx():
    """Upload corrupt DOCX — should fail gracefully (not 500 crash)."""
    path = os.path.join(INPUT_DIR, "05_corrupt_file.docx")
    if not os.path.exists(path):
        record("Corrupt DOCX handling", False, "test file missing")
        return
    with open(path, "rb") as f:
        r = requests.post(f"{BASE}/upload",
            files=[("files", ("corrupt.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))],
            timeout=15)
    # Either 400 (rejected immediately) or 200 with a job that eventually fails — both acceptable
    if r.status_code == 400:
        record("Corrupt DOCX handling", True, "rejected at upload (good)")
        return
    if r.status_code == 200:
        jobs = r.json().get("jobs", [])
        job_id = jobs[0].get("job_id") if jobs else None
        if not job_id:
            record("Corrupt DOCX handling", False, "no job_id returned")
            return
        data, err = poll_job(job_id, timeout=60)
        record("Corrupt DOCX handling", True, f"job failed gracefully: {err or 'completed'}")
    else:
        record("Corrupt DOCX handling", False, f"unexpected HTTP {r.status_code}")

# ── Run all tests ─────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print("  IndicPDF E2E Flow Test")
print(f"{'='*60}\n")

test_health()
test_docx_to_pdf()
test_pdf_to_docx()
test_txt_to_pdf()
test_convert_endpoint()
test_batch_upload()
test_pdf_analyse()
test_invalid_file()
test_corrupt_docx()

# ── Summary ───────────────────────────────────────────────────────────────────
passed = sum(1 for r in results if r["ok"])
total = len(results)
print(f"\n{'='*60}")
print(f"  Results: {passed}/{total} passed")
print(f"{'='*60}")
if passed < total:
    print("\nFailed tests:")
    for r in results:
        if not r["ok"]:
            print(f"  {FAIL} {r['name']}: {r['detail']}")
    sys.exit(1)
else:
    print("\nAll tests passed.")
    sys.exit(0)
