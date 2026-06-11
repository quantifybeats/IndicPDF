import logging
import os
import sys
import tempfile
from pathlib import Path
from redis import Redis
from rq import Worker, Queue
from ocr_processor import run_ocr
from security_manager import security_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Absolute path resolution
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
sys.path.append(str(BACKEND_DIR))

# Redis URL from environment
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")

def run_worker():
    redis_conn = Redis.from_url(REDIS_URL)
    # Define the queues in priority order
    listen = ['fast', 'slow', 'default']
    
    try:
        from tasks import handle_job_failure
        handlers = [handle_job_failure]
    except ImportError:
        handlers = None
        
    # Start the worker with memory safeguards via exception handling
    worker = Worker(listen, connection=redis_conn, exception_handlers=handlers)
    worker.work(with_scheduler=True)

def process_ocr(file_path: str, lang: str = "auto", ocr_job_id: str = None) -> dict:
    """OCR job function. Input is encrypted; decrypts before OCR, encrypts output at rest."""
    output_dir = BASE_DIR / "data" / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    job_id = ocr_job_id or Path(file_path).stem.split("_")[0]
    output_path = output_dir / f"{job_id}_ocr.txt"
    ext = Path(file_path).suffix
    logger.info(f"OCR job {job_id}: starting (lang={lang}, ext={ext})")
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_input = Path(tmp_dir) / f"input{ext}"
            tmp_output = Path(tmp_dir) / "output.txt"
            security_manager.decrypt_to_file(Path(file_path), tmp_input)
            text = run_ocr(str(tmp_input), lang)
            tmp_output.write_text(text, encoding="utf-8")
            security_manager.encrypt_file(tmp_output, output_path)
        Path(file_path).unlink(missing_ok=True)
        logger.info(f"OCR job {job_id}: completed ({len(text)} chars)")
        return {"output_path": str(output_path), "char_count": len(text), "lang": lang, "ocr": True}
    except Exception as exc:
        Path(file_path).unlink(missing_ok=True)
        logger.error(f"OCR job {job_id}: failed — {exc}")
        raise RuntimeError(f"OCR failed: {exc}") from exc

if __name__ == "__main__":
    print(f"Starting RQ worker connecting to {REDIS_URL}")
    run_worker()
