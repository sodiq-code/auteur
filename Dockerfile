# Auteur — unified app Dockerfile (Next.js frontend + FastAPI backend on one Cloud Run service)
# Serves the full application: the studio UI at / + the API at /api/*

FROM node:20-slim AS frontend-builder

WORKDIR /app

# Set the correct API base URL for the production build (overrides any .env file)
ENV NEXT_PUBLIC_API_BASE_URL=https://auteur-dev-jbkbgthudq-uc.a.run.app

# Copy package files + install deps (use npm, not bun — more reliable in Cloud Build)
COPY package.json bun.lock ./
RUN npm install --legacy-peer-deps

# Copy the Next.js app source
COPY . .

# Remove .env so it doesn't override the Docker ENV (which has the correct API_BASE_URL)
RUN rm -f .env

# Debug: verify the source has the correct API_BASE
RUN grep "API_BASE" src/lib/api.ts || echo "API_BASE not found in api.ts"

# Build the production standalone bundle
RUN npm run build

# ------------------------------------------------------------------- #
# Final stage: Python + Node runtime
# ------------------------------------------------------------------- #
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

# Copy the Next.js standalone build from the builder stage
COPY --from=frontend-builder /app/.next/standalone ./next-standalone/
COPY --from=frontend-builder /app/.next/static ./next-standalone/.next/static/
COPY --from=frontend-builder /app/public ./next-standalone/public/

# Copy the startup script
COPY deploy-start.sh ./
RUN chmod +x deploy-start.sh

# Cloud Run sets PORT env (used by Next.js); FastAPI runs on 8000 internally
ENV PORT=3000
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:3000/api/health || exit 1

# Start both Next.js + FastAPI via the startup script
CMD ["./deploy-start.sh"]
