#!/bin/bash
set -e

echo "Starting IndicPDF Monolith..."

# Use absolute paths or ensure working directory is correct
export PYTHONPATH=$PYTHONPATH:$(pwd)/backend

# Start Redis (queue broker for RQ). Loopback only; persistence disabled —
# the job queue is ephemeral and conversion artifacts live on disk.
echo "Launching Redis..."
redis-server --daemonize yes --bind 127.0.0.1 --port 6379 --save "" --appendonly no

# Wait until Redis answers PING (max ~10s) so worker/API never race it
for i in $(seq 1 50); do
    if redis-cli -h 127.0.0.1 -p 6379 ping > /dev/null 2>&1; then
        break
    fi
    sleep 0.2
done
if ! redis-cli -h 127.0.0.1 -p 6379 ping > /dev/null 2>&1; then
    echo "FATAL: Redis did not become ready" >&2
    exit 1
fi
echo "Redis is ready."

# Start the RQ worker in the background
echo "Launching RQ Worker..."
python3 backend/worker.py &

# Start the FastAPI application
echo "Launching FastAPI API..."
python3 backend/main.py
