#!/bin/bash
# Start the RQ worker in the background
python backend/worker.py &

# Start the FastAPI application
python backend/main.py
