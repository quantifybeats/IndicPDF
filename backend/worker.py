import os
import sys
from pathlib import Path
from redis import Redis
from rq import Worker, Queue

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
    worker.work()

if __name__ == "__main__":
    print(f"Starting RQ worker connecting to {REDIS_URL}")
    run_worker()
