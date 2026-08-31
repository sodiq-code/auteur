# Auteur backend — FastAPI Docker image (blueprint Section 31.4)
# Deployed to Cloud Run. Min instances=1 (always warm), max=10 (cost cap).

FROM python:3.12-slim

# System deps for ffmpeg (assembly) + curl (health check)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps (cached layer)
# Cache bust — changes every build to invalidate the COPY layer
ARG CACHEBUST=1
RUN echo "Build cache bust: $CACHEBUST"
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend source
COPY backend/ ./backend/

# Cloud Run sets PORT env; default 8000 for local
ENV PORT=8000
EXPOSE 8000

# Health check (blueprint §31.4 smoke test)
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:${PORT}/api/health || exit 1

# Run with uvicorn (1 worker for hackathon scale; Cloud Run handles concurrency)
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT} --workers 1"]
