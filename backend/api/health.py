"""
Auteur — /api/health (blueprint Table 38 row 14).

Returns {status, partner_status, model_status}. This is the Cloud Run health
endpoint — smoke-tested after every deploy (blueprint §31.4).
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "auteur-backend",
        "version": "0.2.0",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "partner_status": {
            "parallel_search": {
                "configured": bool(os.environ.get("PARALLEL_API_KEY")),
                "endpoint": "https://api.parallel.ai/v1/search",
                "auth": "x-api-key",  # NOT Bearer (blueprint pseudo-code was wrong)
                "track": "Parallel partner track",
            },
        },
        "model_status": {
            # Regions documented in docs/validation-day-1-report.md
            "veo": {"model": "veo-3.1-fast-generate-001", "region": "us-central1",
                    "configured": bool(os.environ.get("GCP_PROJECT_ID"))},
            "image": {"model": "gemini-3-pro-image", "region": "global",
                      "configured": bool(os.environ.get("GCP_PROJECT_ID"))},
            "bible": {"model": "gemini-3.1-pro-preview", "region": "global",
                      "configured": bool(os.environ.get("GCP_PROJECT_ID"))},
            "tts": {"model": "gemini-2.5-flash-tts", "region": "us-central1",
                    "configured": bool(os.environ.get("GCP_PROJECT_ID"))},
            "lyria": {"model": "lyria-002", "region": "us-central1",
                      "configured": bool(os.environ.get("GCP_PROJECT_ID"))},
        },
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
