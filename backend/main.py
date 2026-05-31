import os
import uuid
import logging
import shutil
from pathlib import Path
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse, Response
from redis import Redis
from rq import Queue
from rq.job import Job

# Absolute path resolution
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis & RQ Setup
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
redis_conn = Redis.from_url(REDIS_URL)
q = Queue("default", connection=redis_conn)

app = FastAPI(title="IndicPDF Production API")

IS_VERCEL = "VERCEL" in os.environ
UPLOAD_DIR = Path("/tmp/uploads") if IS_VERCEL else BASE_DIR / "data" / "uploads"
OUTPUT_DIR = Path("/tmp/outputs") if IS_VERCEL else BASE_DIR / "data" / "outputs"
STATIC_DIR = BACKEND_DIR / "static"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Import tasks (must be importable by worker too)
from tasks import convert_docx_to_pdf_task, convert_pdf_to_docx_task, cleanup_old_files_task

@app.get("/", response_class=HTMLResponse)
async def root():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return HTMLResponse(content="<h1>IndicPDF API is running</h1><p>Frontend assets missing.</p>")
    return FileResponse(index_file)

def retry_logic():
    from rq import Retry
    return Retry(max=2, interval=[10, 30])

@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """Accept multiple files and enqueue processing jobs (Individual tracking)."""
    job_ids = []
    
    for file in files:
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in [".docx", ".pdf"]:
            continue
        
        file_id = str(uuid.uuid4())
        input_filename = f"{file_id}{file_ext}"
        input_path = UPLOAD_DIR / input_filename
        
        with input_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        output_ext = ".pdf" if file_ext == ".docx" else ".docx"
        output_filename = f"{file_id}{output_ext}"
        output_path = OUTPUT_DIR / output_filename
        
        if file_ext == ".docx":
            job = q.enqueue(
                convert_docx_to_pdf_task, 
                args=(str(input_path), str(output_path)),
                job_id=file_id,
                retry=retry_logic()
            )
        else:
            job = q.enqueue(
                convert_pdf_to_docx_task, 
                args=(str(input_path), str(output_path)),
                job_id=file_id,
                retry=retry_logic()
            )
            
        job_ids.append({
            "original_name": file.filename,
            "job_id": job.id,
            "status": "queued"
        })
        
    return {"jobs": job_ids}

@app.post("/batch/upload")
async def upload_batch(files: List[UploadFile] = File(...)):
    """Accept multiple files for batch processing and eventual merging."""
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Max 10 files allowed per batch.")
    
    batch_id = str(uuid.uuid4())
    job_ids = []
    
    for file in files:
        # Validate file size (25MB limit)
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)
        if size > 25 * 1024 * 1024:
            raise HTTPException(status_code=400, detail=f"File {file.filename} exceeds 25MB limit.")
            
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in [".docx", ".pdf"]:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_ext}")
        
        file_id = str(uuid.uuid4())
        input_filename = f"{file_id}{file_ext}"
        input_path = UPLOAD_DIR / input_filename
        
        with input_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        output_ext = ".pdf" if file_ext == ".docx" else ".docx"
        output_filename = f"{file_id}{output_ext}"
        output_path = OUTPUT_DIR / output_filename
        
        if file_ext == ".docx":
            job = q.enqueue(
                convert_docx_to_pdf_task, 
                args=(str(input_path), str(output_path), batch_id),
                job_id=file_id,
                retry=retry_logic()
            )
        else:
            job = q.enqueue(
                convert_pdf_to_docx_task, 
                args=(str(input_path), str(output_path), batch_id),
                job_id=file_id,
                retry=retry_logic()
            )
            
        job_ids.append(job.id)
        
    # Initialize batch tracker in Redis
    redis_conn.hset(f"batch:{batch_id}", mapping={
        "total": len(files),
        "completed": 0,
        "failed": 0,
        "status": "processing",
        "job_ids": ",".join(job_ids)
    })
    
    return {"batch_id": batch_id, "jobs": job_ids}

@app.post("/batch/upload/unified")
async def upload_unified(
    pdf_files: List[UploadFile] = File(None), 
    docx_files: List[UploadFile] = File(None)
):
    """Unified endpoint for uploading PDF and DOCX files for separate processing pipelines."""
    results = {}
    
    # Process PDF Batch (PDF -> DOCX)
    if pdf_files:
        if len(pdf_files) > 10:
            raise HTTPException(status_code=400, detail="Max 10 PDF files allowed.")
        
        pdf_batch_id = str(uuid.uuid4())
        job_ids = []
        for file in pdf_files:
            file_ext = Path(file.filename).suffix.lower()
            if file_ext != ".pdf":
                raise HTTPException(status_code=400, detail=f"Non-PDF file in PDF box: {file.filename}")
            
            # Size check (25MB)
            file.file.seek(0, 2)
            if file.file.tell() > 25 * 1024 * 1024:
                raise HTTPException(status_code=400, detail=f"File {file.filename} exceeds 25MB.")
            file.file.seek(0)

            file_id = str(uuid.uuid4())
            input_path = UPLOAD_DIR / f"{file_id}.pdf"
            with input_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            output_path = OUTPUT_DIR / f"{file_id}.docx"
            job = q.enqueue(
                convert_pdf_to_docx_task,
                args=(str(input_path), str(output_path), pdf_batch_id),
                job_id=file_id,
                retry=retry_logic()
            )
            job_ids.append(job.id)
            
        redis_conn.hset(f"batch:{pdf_batch_id}", mapping={
            "total": len(pdf_files), "completed": 0, "failed": 0, "status": "processing", "job_ids": ",".join(job_ids)
        })
        results["pdf_batch_id"] = pdf_batch_id

    # Process DOCX Batch (DOCX -> PDF)
    if docx_files:
        if len(docx_files) > 10:
            raise HTTPException(status_code=400, detail="Max 10 DOCX files allowed.")
        
        docx_batch_id = str(uuid.uuid4())
        job_ids = []
        for file in docx_files:
            file_ext = Path(file.filename).suffix.lower()
            if file_ext != ".docx":
                raise HTTPException(status_code=400, detail=f"Non-DOCX file in DOCX box: {file.filename}")
            
            # Size check
            file.file.seek(0, 2)
            if file.file.tell() > 25 * 1024 * 1024:
                raise HTTPException(status_code=400, detail=f"File {file.filename} exceeds 25MB.")
            file.file.seek(0)

            file_id = str(uuid.uuid4())
            input_path = UPLOAD_DIR / f"{file_id}.docx"
            with input_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            output_path = OUTPUT_DIR / f"{file_id}.pdf"
            job = q.enqueue(
                convert_docx_to_pdf_task,
                args=(str(input_path), str(output_path), docx_batch_id),
                job_id=file_id,
                retry=retry_logic()
            )
            job_ids.append(job.id)
            
        redis_conn.hset(f"batch:{docx_batch_id}", mapping={
            "total": len(docx_files), "completed": 0, "failed": 0, "status": "processing", "job_ids": ",".join(job_ids)
        })
        results["docx_batch_id"] = docx_batch_id

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
    """Download an individual processed file."""
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
    return FileResponse(
        path=output_path, 
        filename=f"processed_{job_id}{output_path.suffix}",
        media_type="application/octet-stream"
    )

@app.get("/batch/download/{batch_id}")
async def download_batch_result(batch_id: str):
    """Download the merged result of a batch."""
    batch_key = f"batch:{batch_id}"
    final_path_str = redis_conn.hget(batch_key, "final_output_path")
    
    if not final_path_str:
        status = redis_conn.hget(batch_key, "status")
        if status:
            status = status.decode()
            if status == "processing":
                raise HTTPException(status_code=400, detail="Batch is still processing")
            else:
                raise HTTPException(status_code=400, detail=f"Batch failed or merge incomplete: {status}")
        raise HTTPException(status_code=404, detail="Batch not found")
    
    final_path = Path(final_path_str.decode())
    if not final_path.exists():
        raise HTTPException(status_code=404, detail="Final merged file missing on server")
    
    return FileResponse(
        path=final_path,
        filename=f"batch_{batch_id}{final_path.suffix}",
        media_type="application/octet-stream"
    )

@app.on_event("startup")
async def startup_event():
    logger.info(f"Connected to Redis at {REDIS_URL}")
    q.enqueue(cleanup_old_files_task)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
