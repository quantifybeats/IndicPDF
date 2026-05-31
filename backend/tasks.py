import os
import logging
import unicodedata
import shutil
from pathlib import Path
from redis import Redis
from rq import get_current_job, Queue

# Adjusting paths to import from the existing engine
import sys
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR / "backend"))

try:
    from processor import process_docx_to_pdf_final
    from pdf_processor import process_pdf_to_docx
    from font_manager import initialize_font_registry
    from merger import merge_pdfs, merge_docx, create_zip_archive
except ImportError:
    from .processor import process_docx_to_pdf_final
    from .pdf_processor import process_pdf_to_docx
    from .font_manager import initialize_font_registry
    from .merger import merge_pdfs, merge_docx, create_zip_archive

logger = logging.getLogger(__name__)

# Redis Setup for tracking
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
redis_conn = Redis.from_url(REDIS_URL)

# Ensure directories exist
IS_VERCEL = "VERCEL" in os.environ
UPLOAD_DIR = Path("/tmp/uploads") if IS_VERCEL else BASE_DIR / "data" / "uploads"
OUTPUT_DIR = Path("/tmp/outputs") if IS_VERCEL else BASE_DIR / "data" / "outputs"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Initialize fonts once per worker process
initialize_font_registry()

import time

def cleanup_old_files_task(max_age_hours: int = 24):
    """Remove files from uploads and outputs older than max_age_hours."""
    logger.info(f"Starting cleanup of files older than {max_age_hours} hours")
    now = time.time()
    cutoff = now - (max_age_hours * 3600)
    
    count = 0
    for folder in [UPLOAD_DIR, OUTPUT_DIR]:
        for file_path in folder.glob("*"):
            if file_path.is_file():
                if file_path.stat().st_mtime < cutoff:
                    try:
                        file_path.unlink()
                        count += 1
                    except Exception as e:
                        logger.error(f"Failed to delete {file_path}: {e}")
    
    logger.info(f"Cleanup finished. Removed {count} files.")
    return {"status": "success", "removed_count": count}

def update_batch_progress(batch_id: str, success: bool):
    """Update batch progress in Redis and trigger merge if finished."""
    if not batch_id:
        return

    batch_key = f"batch:{batch_id}"
    if success:
        redis_conn.hincrby(batch_key, "completed", 1)
    else:
        redis_conn.hincrby(batch_key, "failed", 1)

    completed = int(redis_conn.hget(batch_key, "completed") or 0)
    failed = int(redis_conn.hget(batch_key, "failed") or 0)
    total = int(redis_conn.hget(batch_key, "total") or 0)

    if completed + failed == total:
        logger.info(f"Batch {batch_id} finished. Triggering merge task.")
        q = Queue("default", connection=redis_conn)
        q.enqueue(merge_batch_task, args=(batch_id,))

def convert_docx_to_pdf_task(input_path: str, output_path: str, batch_id: str = None):
    """RQ Task for DOCX to PDF conversion."""
    job = get_current_job()
    logger.info(f"Starting job {job.id}: DOCX -> PDF (Batch: {batch_id})")
    
    try:
        report = process_docx_to_pdf_final(Path(input_path), Path(output_path))
        logger.info(f"Job {job.id} completed successfully.")
        
        # Cleanup input file after success
        if os.path.exists(input_path):
            os.remove(input_path)
            
        update_batch_progress(batch_id, True)
        return {"status": "success", "report": report, "output_path": str(output_path), "batch_id": batch_id}
    except Exception as e:
        logger.error(f"Job {job.id} failed: {str(e)}")
        update_batch_progress(batch_id, False)
        raise e

def convert_pdf_to_docx_task(input_path: str, output_path: str, batch_id: str = None):
    """RQ Task for PDF to DOCX conversion."""
    job = get_current_job()
    logger.info(f"Starting job {job.id}: PDF -> DOCX (Batch: {batch_id})")
    
    try:
        report = process_pdf_to_docx(Path(input_path), Path(output_path))
        logger.info(f"Job {job.id} completed successfully.")
        
        # Cleanup input file after success
        if os.path.exists(input_path):
            os.remove(input_path)
            
        update_batch_progress(batch_id, True)
        return {"status": "success", "report": report, "output_path": str(output_path), "batch_id": batch_id}
    except Exception as e:
        logger.error(f"Job {job.id} failed: {str(e)}")
        update_batch_progress(batch_id, False)
        raise e

def merge_batch_task(batch_id: str):
    """Task to merge successful outputs based on type (PDF->DOCX or DOCX->PDF)."""
    logger.info(f"Starting batch merge for {batch_id}")
    batch_key = f"batch:{batch_id}"
    
    job_ids_str = redis_conn.hget(batch_key, "job_ids")
    if not job_ids_str:
        logger.error(f"No job IDs found for batch {batch_id}")
        return
    
    job_ids = job_ids_str.decode().split(",")
    successful_paths = []
    
    from rq.job import Job
    for jid in job_ids:
        try:
            job = Job.fetch(jid, connection=redis_conn)
            if job.is_finished and job.result and job.result.get("status") == "success":
                path_str = job.result.get("output_path")
                if path_str and os.path.exists(path_str):
                    successful_paths.append(Path(path_str))
        except Exception as e:
            logger.warning(f"Could not fetch job {jid} for batch merge: {e}")

    if not successful_paths:
        logger.error(f"No successful output files for batch {batch_id}")
        redis_conn.hset(batch_key, "status", "failed_no_files")
        return

    # Determine format based on first successful file
    first_ext = successful_paths[0].suffix.lower()
    final_output_path = OUTPUT_DIR / f"merged_{batch_id}{first_ext}"
    
    try:
        if first_ext == ".pdf":
            # DOCX uploads produced PDFs
            merge_pdfs(successful_paths, final_output_path)
        elif first_ext == ".docx":
            # PDF uploads produced DOCXs
            merge_docx(successful_paths, final_output_path)
        else:
            # Fallback for unknown
            final_output_path = OUTPUT_DIR / f"batch_{batch_id}.zip"
            create_zip_archive(successful_paths, final_output_path)
            
        redis_conn.hset(batch_key, mapping={
            "status": "finished",
            "final_output_path": str(final_output_path)
        })
        logger.info(f"Batch {batch_id} merged into {final_output_path}")
        
    except Exception as e:
        logger.error(f"Batch merge failed for {batch_id}: {e}")
        try:
            final_output_path = OUTPUT_DIR / f"batch_{batch_id}.zip"
            create_zip_archive(successful_paths, final_output_path)
            redis_conn.hset(batch_key, mapping={
                "status": "finished", # We treat ZIP fallback as finished success
                "final_output_path": str(final_output_path)
            })
        except Exception as ze:
            logger.error(f"ZIP fallback also failed for {batch_id}: {ze}")
            redis_conn.hset(batch_key, "status", "failed_merge")
