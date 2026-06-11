#!/usr/bin/env bash
# Local full-stack launcher for the preview harness: starts the RQ worker and
# the FastAPI app (which also serves the built SPA) on $PORT. Both processes
# share INDICPDF_MASTER_KEY so the worker can decrypt the API's uploads.
set -euo pipefail
cd "$(dirname "$0")/.."

PORT="${PORT:-8000}"
export PATH="/Applications/LibreOffice.app/Contents/MacOS:$PATH"

# Shared master key: reuse the one from this QA session, else generate one.
KEY_FILE="/tmp/qa/master.key"
if [ -f "$KEY_FILE" ]; then
  export INDICPDF_MASTER_KEY="$(cat "$KEY_FILE")"
else
  export INDICPDF_MASTER_KEY="$(python3 -c 'import base64,os;print(base64.b64encode(os.urandom(32)).decode())')"
fi

# Worker (fast/slow/default) in the background; killed when this script exits.
OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES \
  rq worker fast slow default --url "${REDIS_URL:-redis://localhost:6379}" \
  --path "$(pwd)/backend" &
WORKER_PID=$!
trap 'kill "$WORKER_PID" 2>/dev/null || true' EXIT

cd backend
exec python3 -m uvicorn main:app --host 127.0.0.1 --port "$PORT" --log-level info
