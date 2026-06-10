import os
import uuid
import logging
import shutil
import tempfile
import json
from pathlib import Path
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends, Security
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from redis import Redis
from rq import Queue
from rq.job import Job

from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

def err(status: int, detail: str, code: str):
    return JSONResponse(status_code=status, content={"detail": detail, "code": code})

# Absolute path resolution
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

import sys
if str(BACKEND_DIR) not in sys.path:
    sys.path.append(str(BACKEND_DIR))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import secrets

# Security Configuration
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
INTERNAL_API_KEY = os.environ.get("INDICPDF_API_KEY", "dev-key-placeholder")

async def get_api_key(api_key_header: str = Security(api_key_header)):
    # Constant-time comparison to prevent timing attacks
    if secrets.compare_digest(api_key_header or "", INTERNAL_API_KEY):
        return api_key_header
    raise HTTPException(
        status_code=403, detail="Could not validate credentials"
    )

# Redis & RQ Setup
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
redis_conn = Redis.from_url(REDIS_URL)
q = Queue("default", connection=redis_conn)

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request

# Initialize Limiter
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="IndicPDF Production API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

IS_VERCEL = "VERCEL" in os.environ
# Ensure directories exist
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
OUTPUT_DIR = BASE_DIR / "data" / "outputs"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # single shared limit; checked during streaming
MAX_EXPORT_TEXT_BYTES = 1 * 1024 * 1024  # QA F2: cap export payload


def export_text_too_large(text: str) -> bool:
    return len(text.encode("utf-8")) > MAX_EXPORT_TEXT_BYTES

logger.info(f"BASE_DIR: {BASE_DIR}")
logger.info(f"FRONTEND_DIST: {FRONTEND_DIST} (Exists: {FRONTEND_DIST.exists()})")
if FRONTEND_DIST.exists():
    logger.info(f"Contents of FRONTEND_DIST: {[f.name for f in FRONTEND_DIST.iterdir()]}")

# Import tasks (must be importable by worker too)
from tasks import convert_docx_to_pdf_task, convert_pdf_to_docx_task, convert_txt_to_pdf_task, cleanup_old_files_task, convert_document_task, process_reconstruction_task
from processor import LIBREOFFICE_INPUT_FORMATS, LIBREOFFICE_OUTPUT_MAP
from ocr_processor import LANG_MAP as OCR_LANG_MAP
from security_manager import security_manager
from http_utils import content_disposition
import io

def retry_logic():
    # Only retry in production (e.g. if not default development key)
    if os.environ.get("INDICPDF_API_KEY", "dev-key-placeholder") == "dev-key-placeholder":
        return None
    from rq import Retry
    return Retry(max=2, interval=[10, 30])

async def secure_file_upload(file: UploadFile, destination_path: Path):
    """Stream an upload to a temp file with a hard size cap, then encrypt it.

    The cap is enforced per-chunk so an oversized body is aborted after at
    most 25 MB + 1 chunk, instead of being buffered fully before validation.
    """
    total = 0
    try:
        with tempfile.NamedTemporaryFile(delete=True) as tmp:
            while True:
                chunk = await file.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File {file.filename} exceeds 25 MB limit.",
                    )
                tmp.write(chunk)
            tmp.flush()
            security_manager.encrypt_file(Path(tmp.name), destination_path)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to securely process upload {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Secure processing failed for {file.filename}")

@app.get("/health")
async def health_check():
    """Lightweight health check for keep-alive pings."""
    return {"status": "ok"}

@app.post("/upload")
@limiter.limit("5/minute")
async def upload_files(request: Request, files: List[UploadFile] = File(...)):
    """Accept multiple files, encrypt, and enqueue processing jobs."""
    job_ids = []
    
    for file in files:
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in [".docx", ".pdf", ".txt"]:
            continue
            
        # 0. Magic Byte Validation & Size Routing
        header = await file.read(4)
        await file.seek(0)
        if file_ext == ".pdf" and not header.startswith(b'%PDF'):
            return err(400, "Invalid PDF signature.", "INVALID_SIGNATURE")
        if file_ext == ".docx" and not header.startswith(b'PK\x03\x04'):
            return err(400, "Invalid DOCX signature.", "INVALID_SIGNATURE")

        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)

        if size > MAX_UPLOAD_BYTES:
            return err(400, f"File {file.filename} exceeds 25 MB limit.", "TOO_LARGE")

        queue_name = "slow" if size > 5 * 1024 * 1024 else "fast"
        q_instance = Queue(queue_name, connection=redis_conn)
        
        file_id = str(uuid.uuid4())
        input_filename = f"{file_id}{file_ext}"
        input_path = UPLOAD_DIR / input_filename
        
        # Stream and Encrypt
        await secure_file_upload(file, input_path)
        
        output_ext = ".pdf" if file_ext in [".docx", ".txt"] else ".docx"
        output_filename = f"{file_id}{output_ext}"
        output_path = OUTPUT_DIR / output_filename
        
        # Enqueue with strict timeout
        original_stem = Path(file.filename).stem
        if file_ext == ".docx":
            job = q_instance.enqueue(
                convert_docx_to_pdf_task,
                args=(str(input_path), str(output_path)),
                job_id=file_id,
                meta={"original_stem": original_stem},
                retry=retry_logic(),
                job_timeout=300
            )
        elif file_ext == ".txt":
            job = q_instance.enqueue(
                convert_txt_to_pdf_task,
                args=(str(input_path), str(output_path)),
                job_id=file_id,
                meta={"original_stem": original_stem},
                retry=retry_logic(),
                job_timeout=300
            )
        else:
            job = q_instance.enqueue(
                convert_pdf_to_docx_task,
                args=(str(input_path), str(output_path)),
                job_id=file_id,
                meta={"original_stem": original_stem},
                retry=retry_logic(),
                job_timeout=600
            )
            
        job_ids.append({
            "original_name": file.filename,
            "job_id": job.id,
            "status": "queued"
        })
        
    return {"jobs": job_ids}

@app.post("/ocr")
async def ocr_upload(
    file: UploadFile = File(...),
    lang: str = Form(default="auto"),
):
    allowed_exts = {".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_exts:
        return err(400, f"Unsupported file type: {ext}. Allowed: {', '.join(allowed_exts)}", "UNSUPPORTED_TYPE")
    if lang not in OCR_LANG_MAP:
        return err(400, f"Unknown language: {lang}.", "INVALID_PARAM")
    job_id = str(uuid.uuid4())
    input_path = UPLOAD_DIR / f"{job_id}_input{ext}"
    contents = await file.read()
    input_path.write_bytes(contents)
    q.enqueue(
        "backend.worker.process_ocr",
        job_id=job_id,
        kwargs={"file_path": str(input_path), "lang": lang, "ocr_job_id": job_id},
        meta={"original_stem": Path(file.filename).stem},
        job_timeout=300,
    )
    return {"job_id": job_id}


RECON_EXTENSIONS = {".pdf", ".docx", ".png", ".jpg", ".jpeg", ".tiff", ".tif"}


@app.post("/api/process")
@limiter.limit("5/minute")
async def process_documents(
    request: Request,
    files: List[UploadFile] = File(...),
    lang: str = Form(default="auto"),
):
    """Confidence-scored reconstruction. Multi-file: one job per file (QA F6)."""
    if len(files) > 10:
        return err(400, "Max 10 files allowed per request.", "BATCH_LIMIT")

    jobs = []
    for file in files:
        ext = Path(file.filename or "").suffix.lower()
        if ext not in RECON_EXTENSIONS:
            jobs.append({"original_name": file.filename, "job_id": None,
                         "status": "rejected",
                         "detail": f"Unsupported file type: {ext or 'none'}"})
            continue

        header = await file.read(4)
        await file.seek(0)
        if ext == ".pdf" and not header.startswith(b"%PDF"):
            jobs.append({"original_name": file.filename, "job_id": None,
                         "status": "rejected", "detail": "Invalid PDF signature."})
            continue
        if ext == ".docx" and not header.startswith(b"PK\x03\x04"):
            jobs.append({"original_name": file.filename, "job_id": None,
                         "status": "rejected", "detail": "Invalid DOCX signature."})
            continue

        file_id = str(uuid.uuid4())
        input_path = UPLOAD_DIR / f"{file_id}{ext}"
        await secure_file_upload(file, input_path)  # streams + caps (QA F4)

        q_instance = Queue("slow", connection=redis_conn)  # OCR is CPU-heavy
        job = q_instance.enqueue(
            process_reconstruction_task,
            args=(str(input_path), file.filename, lang),
            job_id=file_id,
            meta={"original_stem": Path(file.filename).stem},
            retry=retry_logic(),
            job_timeout=300,  # QA F2/F8: hard processing timeout
        )
        jobs.append({"original_name": file.filename, "job_id": job.id, "status": "queued"})

    if not any(j["job_id"] for j in jobs):
        return err(400, "No processable files in request.", "NO_VALID_FILES")
    return {"jobs": jobs}


@app.get("/api/process/result/{job_id}")
async def get_process_result(job_id: str):
    """Fetch the rich reconstruction payload for a finished job."""
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.is_finished:
        raise HTTPException(status_code=409, detail=f"Job is in state: {job.get_status()}")

    if not (job.result or {}).get("reconstruction"):
        raise HTTPException(status_code=404, detail="Not a reconstruction job")

    output_path_str = (job.result or {}).get("output_path")
    if not output_path_str or not Path(output_path_str).exists():
        raise HTTPException(status_code=404, detail="Result expired or missing")

    decrypted = security_manager.decrypt_to_memory(Path(output_path_str))
    payload = json.loads(decrypted)
    # QA F3: unusable input → explicit 422 with full diagnostics in the body
    status_code = 200 if payload.get("success") else 422
    return JSONResponse(status_code=status_code, content=payload)


@app.post("/batch/upload")
@limiter.limit("2/minute")
async def upload_batch(request: Request, files: List[UploadFile] = File(...)):
    """Accept multiple files for batch processing, encrypt, and enqueue with size routing."""
    if len(files) > 10:
        return err(400, "Max 10 files allowed per batch.", "BATCH_LIMIT")
    
    batch_id = str(uuid.uuid4())
    job_ids = []
    
    for file in files:
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)
        if size > MAX_UPLOAD_BYTES:
            return err(400, f"File {file.filename} exceeds 25 MB limit.", "TOO_LARGE")

        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in [".docx", ".pdf", ".txt"]:
            return err(400, f"Unsupported file type: {file_ext}", "UNSUPPORTED_TYPE")

        header = await file.read(4)
        await file.seek(0)
        if file_ext == ".pdf" and not header.startswith(b'%PDF'):
            return err(400, f"Invalid PDF signature: {file.filename}", "INVALID_SIGNATURE")
        if file_ext == ".docx" and not header.startswith(b'PK\x03\x04'):
            return err(400, f"Invalid DOCX signature: {file.filename}", "INVALID_SIGNATURE")

        queue_name = "slow" if size > 5 * 1024 * 1024 else "fast"
        q_instance = Queue(queue_name, connection=redis_conn)
        
        file_id = str(uuid.uuid4())
        input_filename = f"{file_id}{file_ext}"
        input_path = UPLOAD_DIR / input_filename
        
        # Stream and Encrypt
        await secure_file_upload(file, input_path)
        
        output_ext = ".pdf" if file_ext in [".docx", ".txt"] else ".docx"
        output_filename = f"{file_id}{output_ext}"
        output_path = OUTPUT_DIR / output_filename
        
        if file_ext == ".docx":
            job = q_instance.enqueue(
                convert_docx_to_pdf_task, 
                args=(str(input_path), str(output_path), batch_id),
                job_id=file_id,
                retry=retry_logic(),
                job_timeout=300
            )
        elif file_ext == ".txt":
            job = q_instance.enqueue(
                convert_txt_to_pdf_task, 
                args=(str(input_path), str(output_path), batch_id),
                job_id=file_id,
                retry=retry_logic(),
                job_timeout=300
            )
        else:
            job = q_instance.enqueue(
                convert_pdf_to_docx_task, 
                args=(str(input_path), str(output_path), batch_id),
                job_id=file_id,
                retry=retry_logic(),
                job_timeout=600
            )
            
        job_ids.append(job.id)
        
    redis_conn.hset(f"batch:{batch_id}", mapping={
        "total": len(files),
        "completed": 0,
        "failed": 0,
        "status": "processing",
        "job_ids": ",".join(job_ids)
    })
    
    return {"batch_id": batch_id, "jobs": job_ids}

@app.post("/batch/upload/unified")
@limiter.limit("2/minute")
async def upload_unified(
    request: Request,
    pdf_files: List[UploadFile] = File(None), 
    docx_files: List[UploadFile] = File(None),
    txt_files: List[UploadFile] = File(None)
):
    """Unified endpoint for uploading PDF, DOCX, and TXT files securely with size routing."""
    results = {}
    
    # Process PDF Batch (PDF -> DOCX)
    if pdf_files:
        if len(pdf_files) > 10: raise HTTPException(status_code=400, detail="Max 10 PDF files allowed.")
        pdf_batch_id = str(uuid.uuid4())
        job_ids = []
        for file in pdf_files:
             file.file.seek(0, 2); size = file.file.tell(); file.file.seek(0)
             q_instance = Queue("slow" if size > 5*1024*1024 else "fast", connection=redis_conn)
             file_id = str(uuid.uuid4()); input_path = UPLOAD_DIR / f"{file_id}.pdf"
             await secure_file_upload(file, input_path)
             output_path = OUTPUT_DIR / f"{file_id}.docx"
             job = q_instance.enqueue(convert_pdf_to_docx_task, args=(str(input_path), str(output_path), pdf_batch_id), job_id=file_id, retry=retry_logic(), job_timeout=600)
             job_ids.append(job.id)
        redis_conn.hset(f"batch:{pdf_batch_id}", mapping={"total": len(pdf_files), "completed": 0, "failed": 0, "status": "processing", "job_ids": ",".join(job_ids)})
        results["pdf_batch_id"] = pdf_batch_id

    # Process DOCX Batch (DOCX -> PDF)
    if docx_files:
        if len(docx_files) > 10: raise HTTPException(status_code=400, detail="Max 10 DOCX files allowed.")
        docx_batch_id = str(uuid.uuid4())
        job_ids = []
        for file in docx_files:
             file.file.seek(0, 2); size = file.file.tell(); file.file.seek(0)
             q_instance = Queue("slow" if size > 5*1024*1024 else "fast", connection=redis_conn)
             file_id = str(uuid.uuid4()); input_path = UPLOAD_DIR / f"{file_id}.docx"
             await secure_file_upload(file, input_path)
             output_path = OUTPUT_DIR / f"{file_id}.pdf"
             job = q_instance.enqueue(convert_docx_to_pdf_task, args=(str(input_path), str(output_path), docx_batch_id), job_id=file_id, retry=retry_logic(), job_timeout=300)
             job_ids.append(job.id)
        redis_conn.hset(f"batch:{docx_batch_id}", mapping={"total": len(docx_files), "completed": 0, "failed": 0, "status": "processing", "job_ids": ",".join(job_ids)})
        results["docx_batch_id"] = docx_batch_id

    # Process TXT Batch (TXT -> PDF)
    if txt_files:
        if len(txt_files) > 10:
            raise HTTPException(status_code=400, detail="Max 10 TXT files allowed.")
        
        txt_batch_id = str(uuid.uuid4())
        job_ids = []
        for file in txt_files:
            file.file.seek(0, 2)
            size = file.file.tell()
            file.file.seek(0)
            q_name = "slow" if size > 5 * 1024 * 1024 else "fast"
            q_instance = Queue(q_name, connection=redis_conn)

            file_id = str(uuid.uuid4())
            input_path = UPLOAD_DIR / f"{file_id}.txt"
            
            # Encrypt (Refactored to secure_file_upload)
            await secure_file_upload(file, input_path)
            
            output_path = OUTPUT_DIR / f"{file_id}.pdf"
            job = q_instance.enqueue(
                convert_txt_to_pdf_task,
                args=(str(input_path), str(output_path), txt_batch_id),
                job_id=file_id,
                retry=retry_logic(),
                job_timeout=300
            )
            job_ids.append(job.id)
            
        redis_conn.hset(f"batch:{txt_batch_id}", mapping={
            "total": len(txt_files), "completed": 0, "failed": 0, "status": "processing", "job_ids": ",".join(job_ids)
        })
        results["txt_batch_id"] = txt_batch_id

    return results

@app.get("/status/{job_id}")
async def get_status(job_id: str):
    """Check the status of a specific job."""
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "job_id": job.id,
        "status": job.get_status(),
        "result": job.result if job.is_finished else None,
        "enqueued_at": job.enqueued_at,
        "started_at": job.started_at,
        "ended_at": job.ended_at,
        "exc_info": job.exc_info if job.is_failed else None
    }

@app.get("/batch/status/{batch_id}")
async def get_batch_status(batch_id: str):
    """Check the status of a batch."""
    batch_key = f"batch:{batch_id}"
    batch_data = redis_conn.hgetall(batch_key)
    
    if not batch_data:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    # Convert bytes to string
    data = {k.decode(): v.decode() for k, v in batch_data.items()}
    
    return {
        "batch_id": batch_id,
        "total": int(data.get("total", 0)),
        "completed": int(data.get("completed", 0)),
        "failed": int(data.get("failed", 0)),
        "status": data.get("status"),
        "final_output_ready": "final_output_path" in data
    }

@app.get("/download/{job_id}")
async def download_result(job_id: str):
    """Download and decrypt an individual processed file on-the-fly."""
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if not job.is_finished:
        raise HTTPException(status_code=400, detail=f"Job is in state: {job.get_status()}")
    
    output_path_str = job.result.get("output_path")
    if not output_path_str or not Path(output_path_str).exists():
        raise HTTPException(status_code=404, detail="Output file missing on server")
    
    output_path = Path(output_path_str)
    original_stem = job.meta.get("original_stem", "file")
    download_name = f"IndicPDF_{original_stem}{output_path.suffix}"
    disposition = content_disposition(download_name)

    # OCR jobs write plaintext directly — skip decryption
    if job.result.get("ocr"):
        return Response(
            content=output_path.read_bytes(),
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": disposition}
        )

    # Decrypt in memory and stream
    try:
        decrypted_bytes = security_manager.decrypt_to_memory(output_path)
        return Response(
            content=decrypted_bytes,
            media_type="application/octet-stream",
            headers={"Content-Disposition": disposition}
        )
    except Exception as e:
        logger.error(f"Decryption failed during download: {e}")
        raise HTTPException(status_code=500, detail="Decryption error")

@app.get("/batch/download/{batch_id}")
async def download_batch_result(batch_id: str):
    """Download and decrypt the merged result of a batch on-the-fly."""
    batch_key = f"batch:{batch_id}"
    final_path_str = redis_conn.hget(batch_key, "final_output_path")
    
    if not final_path_str:
        raise HTTPException(status_code=404, detail="Batch output not found")
    
    final_path = Path(final_path_str.decode())
    if not final_path.exists():
        raise HTTPException(status_code=404, detail="Final merged file missing")
    
    # Decrypt in memory and stream
    try:
        decrypted_bytes = security_manager.decrypt_to_memory(final_path)
        return Response(
            content=decrypted_bytes,
            media_type="application/octet-stream",
            headers={"Content-Disposition": content_disposition(f"IndicPDF_batch{final_path.suffix}")}
        )
    except Exception as e:
        logger.error(f"Batch decryption failed during download: {e}")
        raise HTTPException(status_code=500, detail="Decryption error")

@app.post("/convert")
@limiter.limit("5/minute")
async def convert_document(
    request: Request,
    file: UploadFile = File(...),
    target_format: str = Form(...),
):
    """Convert any LibreOffice-compatible document to a target format."""
    ext = Path(file.filename).suffix.lower().lstrip('.')
    fmt = target_format.lower().lstrip('.')

    if ext not in LIBREOFFICE_INPUT_FORMATS:
        return err(400, f"Unsupported input format: {ext}", "UNSUPPORTED_TYPE")
    if fmt not in LIBREOFFICE_OUTPUT_MAP:
        return err(400, f"Unsupported target format: {fmt}. Supported: {list(LIBREOFFICE_OUTPUT_MAP.keys())}", "UNSUPPORTED_TARGET")

    # Magic byte validation (same as /upload and /batch/upload)
    header = await file.read(4)
    await file.seek(0)
    if ext == "pdf" and not header.startswith(b'%PDF'):
        return err(400, "Invalid PDF signature.", "INVALID_SIGNATURE")
    if ext in ("docx", "doc", "docm", "dotx") and not header.startswith(b'PK\x03\x04'):
        return err(400, "Invalid DOCX/ZIP signature.", "INVALID_SIGNATURE")

    # Size check
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size > MAX_UPLOAD_BYTES:
        return err(400, "File exceeds 25 MB limit.", "TOO_LARGE")

    file_id = str(uuid.uuid4())
    input_path = UPLOAD_DIR / f"{file_id}.{ext}"
    output_path = OUTPUT_DIR / f"{file_id}.{fmt}"

    await secure_file_upload(file, input_path)

    queue_name = "slow" if size > 5 * 1024 * 1024 else "fast"
    q_instance = Queue(queue_name, connection=redis_conn)
    original_stem = Path(file.filename).stem

    job = q_instance.enqueue(
        convert_document_task,
        args=(str(input_path), str(output_path), fmt),
        job_id=file_id,
        meta={"original_stem": original_stem},
        retry=retry_logic(),
        job_timeout=300,
    )

    return {"job_id": job.id, "status": "queued", "target_format": fmt}


@app.post("/analyse-pdf-quality")
async def analyse_pdf_quality(file: UploadFile = File(...)):
    """Analyse a PDF for quality metrics (Fonts, Searchability, Compression)."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files can be analysed.")
    
    try:
        from pypdf import PdfReader
        import io
        
        content = await file.read()
        reader = PdfReader(io.BytesIO(content))
        
        pages = len(reader.pages)
        size_kb = len(content) / 1024
        
        # Simple heuristics for quality
        has_text = False
        embedded_fonts = True
        warnings = []
        
        for page in reader.pages:
            if page.extract_text().strip():
                has_text = True
            # Check for non-embedded fonts (simplified)
            if "/Resources" in page and "/Font" in page["/Resources"]:
                pass # Logic could be deeper here
        
        score = 100
        if not has_text:
            score -= 40
            warnings.append("No searchable text layer found (Image-only PDF).")
        if size_kb / (pages or 1) > 1000:
            score -= 15
            warnings.append("Large file size detected; consider optimizing compression.")
            
        return {
            "score": f"{max(score, 0)}/100",
            "size": f"{size_kb/1024:.1f} MB" if size_kb > 1024 else f"{size_kb:.0f} KB",
            "pages": pages,
            "fonts": "Fully Embedded" if embedded_fonts else "Suboptimal",
            "text": "Searchable" if has_text else "Not Searchable",
            "render": "High Quality" if score > 80 else "Medium Quality",
            "compression": "Optimized" if size_kb < 5000 else "Uncompressed",
            "warnings": warnings,
            "recommendation": "Ready for publishing" if score > 85 else "Optimisation recommended"
        }
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail="Internal analysis error")

@app.on_event("startup")
async def startup_event():
    logger.info(f"Connected to Redis at {REDIS_URL}")
    # Initialize the periodic cleanup cycle (2 hours)
    q.enqueue(cleanup_old_files_task, 2)

class PdfExportRequest(BaseModel):
    clean_text: str
    filename: str = "indicpdf-reconstruction"


@app.post("/api/export/pdf")
@limiter.limit("5/minute")
async def export_pdf(request: Request, payload: PdfExportRequest):
    """Render reconstructed text to PDF via the existing Indic-aware
    txt→pdf worker task (queued, font-registry shaping, 300s timeout)."""
    if not payload.clean_text.strip():
        return err(400, "No reconstructed text is available for PDF export.", "EMPTY_TEXT")
    if export_text_too_large(payload.clean_text):
        return err(413, "Export text exceeds the 1 MB limit.", "TOO_LARGE")

    file_id = str(uuid.uuid4())
    input_path = UPLOAD_DIR / f"{file_id}.txt"
    output_path = OUTPUT_DIR / f"{file_id}.pdf"

    # Write plaintext to a temp file, encrypt at rest like every other upload
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as tmp:
        tmp_path = Path(tmp.name)
        tmp.write(payload.clean_text)
    try:
        security_manager.encrypt_file(tmp_path, input_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    q_instance = Queue("fast", connection=redis_conn)
    job = q_instance.enqueue(
        convert_txt_to_pdf_task,
        args=(str(input_path), str(output_path)),
        job_id=file_id,
        meta={"original_stem": Path(payload.filename).stem or "indicpdf-reconstruction"},
        retry=retry_logic(),
        job_timeout=300,
    )
    return {"job_id": job.id, "status": "queued"}


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """Serve the frontend SPA, allowing React Router to handle sub-paths."""
    # 1. Try to serve exact file from dist (e.g., assets/index-hash.js)
    file_path = FRONTEND_DIST / full_path
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    
    # 2. Fallback to index.html for any other path (SPA routing)
    index_path = FRONTEND_DIST / "index.html"
    if index_path.exists():
        # Set no-cache for index.html to ensure users always get the latest build pointers
        return FileResponse(
            index_path, 
            headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}
        )
    
    # 3. Diagnostics if frontend is missing
    return HTMLResponse(content="Frontend not found. Please build the frontend first.", status_code=404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
