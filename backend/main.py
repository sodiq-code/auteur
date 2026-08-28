"""
Auteur — FastAPI application (blueprint Section 26.2, Table 38).

Mounts all API routers. The full API surface (14 endpoints per Table 38) is
scaffolded; the heavy implementations (generation pipeline, assembly,
consistency) come in their respective tasks.

Run locally:
  uvicorn backend.main:app --reload --port 8000

Run in Docker:
  docker build -f backend/Dockerfile -t auteur-backend .
  docker run -p 8000:8000 --env-file .env auteur-backend

Health check:
  curl http://localhost:8000/api/health
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import health as health_api
from .api import projects as projects_api
from .api import bible as bible_api
from .api import shots as shots_api
from .api import export as export_api
from .api import director as director_api
from .api import share as share_api
from .api import demo as demo_api

app = FastAPI(
    title="Auteur — The Film Bible Agent",
    description=(
        "Agentic AI film studio that maintains a persistent, research-grounded "
        "Film Bible and enforces cross-shot consistency across every Veo 3.1, "
        "Chirp 3, Lyria 2, and Imagen 3 generation call. (Agentic Cinema "
        "Hackathon — Parallel Partner Track)"
    ),
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow the Next.js frontend (dev: localhost:3000; prod: same Cloud Run origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("AUTEUR_CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routers under /api
api_prefix = "/api"
app.include_router(health_api.router, prefix=api_prefix)
app.include_router(projects_api.router, prefix=api_prefix)
app.include_router(bible_api.router, prefix=api_prefix)
app.include_router(shots_api.router, prefix=api_prefix)
app.include_router(export_api.router, prefix=api_prefix)
app.include_router(director_api.router, prefix=api_prefix)
app.include_router(share_api.router, prefix=api_prefix)
app.include_router(demo_api.router, prefix=api_prefix)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "auteur", "docs": "/docs", "health": "/api/health"}


@app.get("/api")
def api_root() -> dict[str, Any]:
    return {
        "service": "auteur-backend",
        "version": "0.2.0",
        "endpoints": [
            "POST /api/projects",
            "GET  /api/projects/{id}",
            "GET  /api/projects/{id}/bible",
            "PATCH /api/projects/{id}/bible/entries/{entryId}",
            "GET  /api/projects/{id}/shots",
            "POST /api/projects/{id}/shots/{shotId}/generate",
            "POST /api/projects/{id}/shots/{shotId}/regenerate",
            "GET  /api/projects/{id}/shots/{shotId}/consistency",
            "POST /api/projects/{id}/assemble",
            "POST /api/projects/{id}/share",
            "GET  /api/projects/{id}/export/bible",
            "GET  /api/projects/{id}/export/shots",
            "GET  /api/projects/{id}/events",
            "GET  /api/health",
        ],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=True)
