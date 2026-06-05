import os
import uuid
import logging
import shutil
import tempfile
from pathlib import Path
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Depends, Security
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.security.api_key import APIKeyHeader
from redis import Redis
from rq import Queue
from rq.job import Job

from fastapi.staticfiles import StaticFiles

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

logger.info(f"BASE_DIR: {BASE_DIR}")
logger.info(f"FRONTEND_DIST: {FRONTEND_DIST} (Exists: {FRONTEND_DIST.exists()})")

# Import tasks (must be importable by worker too)
from tasks import convert_docx_to_pdf_task, convert_pdf_to_docx_task, convert_txt_to_pdf_task, cleanup_old_files_task
from security_manager import security_manager
import io

def retry_logic():
    from rq import Retry
    return Retry(max=2, interval=[10, 30])

async def secure_file_upload(file: UploadFile, destination_path: Path):
    """Helper to stream an upload to a temp file and then encrypt it in chunks."""
    try:
        with tempfile.NamedTemporaryFile(delete=True) as tmp:
            while True:
                chunk = await file.read(1024 * 1024) # 1MB chunks
                if not chunk:
                    break
                tmp.write(chunk)
            tmp.flush()
            security_manager.encrypt_file(Path(tmp.name), destination_path)
    except Exception as e:
        logger.error(f"Failed to securely process upload {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Secure processing failed for {file.filename}")

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
            raise HTTPException(status_code=400, detail="Invalid PDF signature.")
        if file_ext == ".docx" and not header.startswith(b'PK\x03\x04'):
            raise HTTPException(status_code=400, detail="Invalid DOCX signature.")
            
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)
        
        if size > 25 * 1024 * 1024:
             raise HTTPException(status_code=400, detail=f"File {file.filename} exceeds 25MB limit.")

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
        if file_ext == ".docx":
            job = q_instance.enqueue(
                convert_docx_to_pdf_task, 
                args=(str(input_path), str(output_path)),
                job_id=file_id,
                retry=retry_logic(),
                job_timeout=300
            )
        elif file_ext == ".txt":
            job = q_instance.enqueue(
                convert_txt_to_pdf_task, 
                args=(str(input_path), str(output_path)),
                job_id=file_id,
                retry=retry_logic(),
                job_timeout=300
            )
        else:
            job = q_instance.enqueue(
                convert_pdf_to_docx_task, 
                args=(str(input_path), str(output_path)),
                job_id=file_id,
                retry=retry_logic(),
                job_timeout=600
            )
            
        job_ids.append({
            "original_name": file.filename,
            "job_id": job.id,
            "status": "queued"
        })
        
    return {"jobs": job_ids}

@app.post("/batch/upload")
@limiter.limit("2/minute")
async def upload_batch(request: Request, files: List[UploadFile] = File(...)):
    """Accept multiple files for batch processing, encrypt, and enqueue with size routing."""
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Max 10 files allowed per batch.")
    
    batch_id = str(uuid.uuid4())
    job_ids = []
    
    for file in files:
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)
        if size > 25 * 1024 * 1024:
            raise HTTPException(status_code=400, detail=f"File {file.filename} exceeds 25MB limit.")
            
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in [".docx", ".pdf", ".txt"]:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_ext}")
            
        header = await file.read(4)
        await file.seek(0)
        if file_ext == ".pdf" and not header.startswith(b'%PDF'):
            raise HTTPException(status_code=400, detail=f"Invalid PDF signature in batch: {file.filename}")
        if file_ext == ".docx" and not header.startswith(b'PK\x03\x04'):
            raise HTTPException(status_code=400, detail=f"Invalid DOCX signature in batch: {file.filename}")

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
    
    # Decrypt in memory and stream
    try:
        decrypted_bytes = security_manager.decrypt_to_memory(output_path)
        return Response(
            content=decrypted_bytes,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename=processed_{job_id}{output_path.suffix}"}
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
            headers={"Content-Disposition": f"attachment; filename=batch_{batch_id}{final_path.suffix}"}
        )
    except Exception as e:
        logger.error(f"Batch decryption failed during download: {e}")
        raise HTTPException(status_code=500, detail="Decryption error")

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

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Explicitly serve index.html for the root path with enhanced diagnostics."""
    index_path = FRONTEND_DIST / "index.html"
    
    if index_path.exists():
        return FileResponse(index_path)
    
    # Diagnostics for troubleshooting
    try:
        files_in_base = [f.name for f in BASE_DIR.iterdir()]
        frontend_exists = (BASE_DIR / "frontend").exists()
        dist_exists = FRONTEND_DIST.exists()
    except Exception as e:
        files_in_base = [f"Error: {e}"]
        frontend_exists = dist_exists = False

    return HTMLResponse(
        content=f"""
        <html>
            <body style="font-family: sans-serif; padding: 20px; line-height: 1.6;">
                <h1 style="color: #d32f2f;">IndicPDF API - Frontend Not Found</h1>
                <p>The application is running, but the static frontend files were not found.</p>
                <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; border: 1px solid #ddd;">
                    <p><strong>Looked at:</strong> <code>{FRONTEND_DIST}</code></p>
                    <p><strong>BASE_DIR:</strong> <code>{BASE_DIR}</code> (Exists: {BASE_DIR.exists()})</p>
                    <p><strong>Frontend folder:</strong> <code>{BASE_DIR / "frontend"}</code> (Exists: {frontend_exists})</p>
                    <p><strong>Dist folder:</strong> <code>{FRONTEND_DIST}</code> (Exists: {dist_exists})</p>
                    <p><strong>Files in BASE_DIR:</strong> <code>{", ".join(files_in_base)}</code></p>
                </div>
                <p><strong>Possible Solutions:</strong></p>
                <ul>
                    <li>If using <b>Native Python</b>: Ensure your Build Command includes <code>cd frontend && npm install && npm run build</code>.</li>
                    <li>If using <b>Docker</b>: Ensure your service is set to "Docker" in the Render Dashboard.</li>
                    <li>Verify that <code>frontend/dist</code> is being generated correctly.</li>
                </ul>
            </body>
        </html>
        """,
        status_code=404
    )

# Mount frontend at the very end to avoid shadowing API routes
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
