#!/usr/bin/env python3
"""
Auteur — minimal FastAPI scaffold (blueprint Section 32.2 Day 2: "Initialize
the Next.js + FastAPI scaffold").

This is the seed for the full backend skeleton that comes in the next task
(Section 32.2: backend/ main.py + agents/ + bible/schema.py + api/). For now
it exposes a single /api/health endpoint that the next task will expand into
the full API surface (blueprint Table 38).

Run:
  pip install -r backend/requirements.txt
  uvicorn backend.main:app --reload --port 8000

Health check:
  curl http://localhost:8000/api/health
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Auteur — The Film Bible Agent",
    description=(
        "Agentic AI film studio that maintains a persistent, research-grounded "
        "Film Bible and enforces cross-shot consistency across every Veo 3.1, "
        "Chirp 3, Lyria 2, and Imagen 3 generation call. (Agentic Cinema "
        "Hackathon — Parallel Partner Track)"
    ),
    version="0.1.0",
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


@app.get("/api/health")
def health() -> dict[str, Any]:
    """Blueprint Table 38 row 14: /api/health returns {status, partner_status, model_status}."""
    return {
        "status": "ok",
        "service": "auteur-backend",
        "version": "0.1.0",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "partner_status": {
            "parallel_search": _check_env("PARALLEL_API_KEY"),
            "endpoint": "https://api.parallel.ai/v1/search",
            "auth": "x-api-key",
        },
        "model_status": {
            # Regions documented in docs/validation-day-1-report.md
            "veo": {"model": "veo-3.1-fast-generate-001", "region": "us-central1", "configured": _check_env("GCP_PROJECT_ID")},
            "image": {"model": "gemini-3-pro-image", "region": "global", "configured": _check_env("GCP_PROJECT_ID")},
            "bible": {"model": "gemini-3.1-pro-preview", "region": "global", "configured": _check_env("GCP_PROJECT_ID")},
            "tts": {"model": "gemini-2.5-flash-tts", "region": "us-central1", "configured": _check_env("GCP_PROJECT_ID")},
            "lyria": {"model": "lyria-002", "region": "us-central1", "configured": _check_env("GCP_PROJECT_ID")},
        },
        "definition_of_done": "next task: expand to full API surface (blueprint Table 38)",
    }


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "auteur", "docs": "/docs", "health": "/api/health"}


def _check_env(name: str) -> bool:
    return bool(os.environ.get(name))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
