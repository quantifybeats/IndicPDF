import os
import logging
import unicodedata
import shutil
from pathlib import Path
from redis import Redis
from rq import get_current_job, Queue

import tempfile
from datetime import timedelta

# Adjusting paths to import from the existing engine
import sys
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR / "backend"))

try:
    from processor import process_docx_to_pdf_final, process_txt_to_pdf
    from pdf_processor import process_pdf_to_docx
    from font_manager import initialize_font_registry
    from merger import merge_pdfs, merge_docx, create_zip_archive
    from security_manager import security_manager
except ImportError:
    from .processor import process_docx_to_pdf_final
    from .pdf_processor import process_pdf_to_docx
    from .font_manager import initialize_font_registry
    from .merger import merge_pdfs, merge_docx, create_zip_archive
    from .security_manager import security_manager

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

def cleanup_old_files_task(max_age_hours: int = 2):
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
    
    # Self-scheduling: Enqueue next cleanup in 2 hours
    try:
        q = Queue("default", connection=redis_conn)
        # Note: enqueue_in requires rq-scheduler or rq >= 1.2
        q.enqueue_in(timedelta(hours=max_age_hours), cleanup_old_files_task, max_age_hours)
    except Exception as e:
        logger.warning(f"Failed to self-schedule next cleanup: {e}")

    return {"status": "success", "removed_count": count}

def handle_job_failure(job, connection, type, value, traceback):
    """RQ Custom Exception Handler to prevent ghost jobs and infinite polling."""
    batch_id = job.kwargs.get('batch_id') or (job.args[2] if len(job.args) > 2 else None)
    if batch_id:
        update_batch_progress(batch_id, False)

def update_batch_progress(batch_id: str, success: bool):
    """Update batch progress atomically and trigger merge exactly once."""
    if not batch_id:
        return

    batch_key = f"batch:{batch_id}"
    
    # Atomic increment to prevent read-modify-write race conditions
    if success:
        completed = redis_conn.hincrby(batch_key, "completed", 1)
        failed = int(redis_conn.hget(batch_key, "failed") or 0)
    else:
        failed = redis_conn.hincrby(batch_key, "failed", 1)
        completed = int(redis_conn.hget(batch_key, "completed") or 0)

    total = int(redis_conn.hget(batch_key, "total") or 0)

    if completed + failed == total:
        lock_key = f"merge_lock:{batch_id}"
        # Distributed lock prevents duplicate merge tasks on simultaneous job completions
        if redis_conn.setnx(lock_key, "1"):
            redis_conn.expire(lock_key, 300)
            logger.info(f"Batch {batch_id} finished. Triggering merge task.")
            q_instance = Queue("fast", connection=redis_conn)
            q_instance.enqueue(merge_batch_task, args=(batch_id,), job_timeout=600)

def convert_docx_to_pdf_task(input_path: str, output_path: str, batch_id: str = None):
    """RQ Task for DOCX to PDF conversion with encryption."""
    job = get_current_job()
    logger.info(f"Starting job {job.id}: DOCX -> PDF (Batch: {batch_id})")
    
    # Use temporary directory for plaintext processing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_input = Path(temp_dir) / "input.docx"
        temp_output = Path(temp_dir) / "output.pdf"
        
        try:
            # 1. Decrypt ciphertext to temporary plaintext file
            security_manager.decrypt_to_file(Path(input_path), temp_input)
            
            # 2. Process
            report = process_docx_to_pdf_final(temp_input, temp_output)
            
            # 3. Encrypt output
            security_manager.encrypt_file(temp_output, Path(output_path))
            
            logger.info(f"Job {job.id} completed successfully.")
            
            # Cleanup encrypted input after success
            if os.path.exists(input_path):
                os.remove(input_path)
                
            update_batch_progress(batch_id, True)
            return {"status": "success", "report": report, "output_path": str(output_path), "batch_id": batch_id}
        except Exception as e:
            logger.error(f"Job {job.id} failed: {str(e)}")
            update_batch_progress(batch_id, False)
            raise e

def convert_pdf_to_docx_task(input_path: str, output_path: str, batch_id: str = None):
    """RQ Task for PDF to DOCX conversion with encryption."""
    job = get_current_job()
    logger.info(f"Starting job {job.id}: PDF -> DOCX (Batch: {batch_id})")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_input = Path(temp_dir) / "input.pdf"
        temp_output = Path(temp_dir) / "output.docx"
        
        try:
            # 1. Decrypt
            security_manager.decrypt_to_file(Path(input_path), temp_input)
            
            # 2. Process
            report = process_pdf_to_docx(temp_input, temp_output)
            
            # 3. Encrypt
            security_manager.encrypt_file(temp_output, Path(output_path))
            
            logger.info(f"Job {job.id} completed successfully.")
            
            # Cleanup encrypted input
            if os.path.exists(input_path):
                os.remove(input_path)
                
            update_batch_progress(batch_id, True)
            return {"status": "success", "report": report, "output_path": str(output_path), "batch_id": batch_id}
        except Exception as e:
            logger.error(f"Job {job.id} failed: {str(e)}")
            update_batch_progress(batch_id, False)
            raise e

def convert_txt_to_pdf_task(input_path: str, output_path: str, batch_id: str = None):
    """RQ Task for TXT to PDF conversion with encryption."""
    job = get_current_job()
    logger.info(f"Starting job {job.id}: TXT -> PDF (Batch: {batch_id})")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_input = Path(temp_dir) / "input.txt"
        temp_output = Path(temp_dir) / "output.pdf"
        
        try:
            # 1. Decrypt
            security_manager.decrypt_to_file(Path(input_path), temp_input)
            
            # 2. Process
            report = process_txt_to_pdf(temp_input, temp_output)
            
            # 3. Encrypt output
            security_manager.encrypt_file(temp_output, Path(output_path))
            
            logger.info(f"Job {job.id} completed successfully.")
            
            # Cleanup encrypted input
            if os.path.exists(input_path):
                os.remove(input_path)
                
            update_batch_progress(batch_id, True)
            return {"status": "success", "report": report, "output_path": str(output_path), "batch_id": batch_id}
        except Exception as e:
            logger.error(f"Job {job.id} failed: {str(e)}")
            update_batch_progress(batch_id, False)
            raise e

def merge_batch_task(batch_id: str):
    """Task to merge successful encrypted outputs."""
    logger.info(f"Starting batch merge for {batch_id}")
    batch_key = f"batch:{batch_id}"
    
    job_ids_str = redis_conn.hget(batch_key, "job_ids")
    if not job_ids_str:
        logger.error(f"No job IDs found for batch {batch_id}")
        return
    
    job_ids = job_ids_str.decode().split(",")
    encrypted_paths = []
    
    from rq.job import Job
    for jid in job_ids:
        try:
            job = Job.fetch(jid, connection=redis_conn)
            if job.is_finished and job.result and job.result.get("status") == "success":
                path_str = job.result.get("output_path")
                if path_str and os.path.exists(path_str):
                    encrypted_paths.append(Path(path_str))
        except Exception as e:
            logger.warning(f"Could not fetch job {jid} for batch merge: {e}")

    if not encrypted_paths:
        logger.error(f"No successful output files for batch {batch_id}")
        redis_conn.hset(batch_key, "status", "failed_no_files")
        return

    # Use temp directory for the merge process
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        plaintext_paths = []
        
        # 1. Decrypt all files into the temp directory
        for i, enc_path in enumerate(encrypted_paths):
            tmp_p = temp_dir_path / f"part_{i}{enc_path.suffix}"
            security_manager.decrypt_to_file(enc_path, tmp_p)
            plaintext_paths.append(tmp_p)

        # Determine format based on first file
        first_ext = encrypted_paths[0].suffix.lower()
        temp_merged = temp_dir_path / f"merged{first_ext}"
        final_output_path = OUTPUT_DIR / f"merged_{batch_id}{first_ext}"
        
        try:
            # 2. Perform merge in plaintext
            if first_ext == ".pdf":
                merge_pdfs(plaintext_paths, temp_merged)
            elif first_ext == ".docx":
                merge_docx(plaintext_paths, temp_merged)
            else:
                # Fallback to ZIP (encrypted files can stay encrypted in ZIP or we ZIP plaintext?)
                # For consistency, we'll ZIP the plaintext and encrypt the ZIP
                temp_merged = temp_dir_path / "batch.zip"
                create_zip_archive(plaintext_paths, temp_merged)
                final_output_path = OUTPUT_DIR / f"merged_{batch_id}.zip"
            
            # 3. Encrypt the final result
            security_manager.encrypt_file(temp_merged, final_output_path)
                
            redis_conn.hset(batch_key, mapping={
                "status": "finished",
                "final_output_path": str(final_output_path)
            })
            logger.info(f"Batch {batch_id} merged and encrypted into {final_output_path}")
            
        except Exception as e:
            logger.error(f"Batch merge failed for {batch_id}: {e}")
            redis_conn.hset(batch_key, "status", "failed_merge")
