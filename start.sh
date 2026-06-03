#!/bin/bash
set -e

echo "Starting IndicPDF Monolith..."

# Use absolute paths or ensure working directory is correct
export PYTHONPATH=$PYTHONPATH:$(pwd)/backend

# Start the RQ worker in the background
echo "Launching RQ Worker..."
python3 backend/worker.py &

# Start the FastAPI application
echo "Launching FastAPI API..."
python3 backend/main.py
