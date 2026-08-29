# Auteur — unified app Dockerfile (pre-built Next.js + FastAPI on one Cloud Run service)
# The Next.js standalone build is pre-built locally and included in the tarball
# so Docker doesn't need to run npm install/build (avoids Cloud Build cache issues)

FROM python:3.12-slim

# System deps: Node.js + ffmpeg + curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ffmpeg ca-certificates gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the backend
COPY backend/ ./backend/

# Install Python deps
RUN pip install --no-cache-dir fastapi uvicorn[standard] pydantic httpx \
    google-genai google-cloud-aiplatform google-auth google-cloud-storage \
    google-cloud-firestore Pillow python-dotenv sse-starlette requests

# Copy the PRE-BUILT Next.js standalone output (built locally, not in Docker)
COPY .next/standalone ./next-standalone/
COPY .next/static ./next-standalone/.next/static/
COPY public ./next-standalone/public/

# Copy the startup script
COPY deploy-start.sh ./
RUN chmod +x deploy-start.sh

# Verify the URL is baked into the build
RUN grep -rq "auteur-dev-jbkbgthudq" /app/next-standalone/ && echo "✓ API_BASE URL verified in build" || echo "⚠ API_BASE URL not found"

# Cloud Run sets PORT env (used by Next.js); FastAPI runs on 8000 internally
ENV PORT=3000
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:3000/api/health || exit 1

# Start both Next.js + FastAPI via the startup script
CMD ["./deploy-start.sh"]
