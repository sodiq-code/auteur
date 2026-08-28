#!/bin/bash
# deploy-start.sh — starts both FastAPI (port 8000) + Next.js (port 3000)
# Next.js rewrites /api/* to the FastAPI backend on port 8000.

set -e

# Start FastAPI backend on port 8000
cd /app
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1 &
BACKEND_PID=$!

# Wait for backend to be ready
for i in $(seq 1 10); do
    if curl -fsS http://localhost:8000/api/health > /dev/null 2>&1; then
        echo "Backend ready on :8000"
        break
    fi
    sleep 1
done

# Start Next.js standalone server on port 3000 (PORT env from Cloud Run)
cd /app/next-standalone
export NODE_ENV=production
node server.js &
FRONTEND_PID=$!

# Wait for either process to exit
wait -n $BACKEND_PID $FRONTEND_PID
