import os
import sys
from pathlib import Path
from redis import Redis
from rq import Worker, Queue
from ocr_processor import run_ocr

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
    """OCR job function. Writes plaintext output; /download serves it directly (no encryption)."""
    output_dir = BASE_DIR / "data" / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    job_id = ocr_job_id or Path(file_path).stem.split("_")[0]
    output_path = output_dir / f"{job_id}_ocr.txt"
    try:
        text = run_ocr(file_path, lang)
        output_path.write_text(text, encoding="utf-8")
        Path(file_path).unlink(missing_ok=True)
        return {"output_path": str(output_path), "char_count": len(text), "lang": lang, "ocr": True}
    except Exception as exc:
        Path(file_path).unlink(missing_ok=True)
        raise RuntimeError(f"OCR failed: {exc}") from exc

if __name__ == "__main__":
    print(f"Starting RQ worker connecting to {REDIS_URL}")
    run_worker()
