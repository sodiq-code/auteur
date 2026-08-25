"""
Auteur — /api/projects/{id}/shots (blueprint Table 38 rows 5-8).

GET  /api/projects/{id}/shots                          — get shot list
POST /api/projects/{id}/shots/{shotId}/generate        — trigger generation (SSE)
POST /api/projects/{id}/shots/{shotId}/regenerate      — re-generate
GET  /api/projects/{id}/shots/{shotId}/consistency     — get drift report

The generate endpoint streams progress via SSE (blueprint Table 38 row 6). For
the skeleton, generation returns a 202 (accepted) + generationId — the full SSE
pipeline comes in the generation-pipeline task.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..bible import store

router = APIRouter(prefix="/projects/{project_id}/shots", tags=["shots"])


@router.get("")
async def get_shots(project_id: str) -> dict[str, Any]:
    """Get the shot list (blueprint Table 38 row 5)."""
    project = await store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    shots = await store.get_shots(project_id)
    return {"shots": [s.model_dump(mode="json") for s in shots]}


class GenerateRequest(BaseModel):
    bible_version: int


@router.post("/{shot_id}/generate")
async def generate_shot(project_id: str, shot_id: str, req: GenerateRequest) -> dict[str, Any]:
    """Trigger generation for a shot (blueprint Table 38 row 6).

    Runs the real generation pipeline: Veo 3.1 (video) + Chirp 3 (voice) +
    Lyria 2 (music) concurrently, with the Film Bible injected as context.
    Returns the per-modality results + output URIs.
    """
    from ..pipelines import generate as generate_pipeline

    project = await store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    shots = await store.get_shots(project_id)
    shot = next((s for s in shots if s.id == shot_id), None)
    if not shot:
        raise HTTPException(status_code=404, detail="shot not found")

    # Get the bible at the requested version (or latest)
    bible = await store.get_bible(project_id, version=req.bible_version) or await store.get_bible(project_id)
    if not bible:
        raise HTTPException(status_code=404, detail="no bible found — call POST /build-bible first")

    # Run the generation pipeline (this takes ~60-90s for Veo)
    result = await generate_pipeline.generate_shot(project_id, shot, bible)
    return result


class RegenerateRequest(BaseModel):
    reason: str = ""


@router.post("/{shot_id}/regenerate")
async def regenerate_shot(project_id: str, shot_id: str, req: RegenerateRequest) -> dict[str, Any]:
    """Re-generate a shot (blueprint Table 38 row 7)."""
    generation_id = uuid.uuid4().hex
    await store.log_event(project_id, "regeneration_prompted", {
        "shotId": shot_id, "generationId": generation_id, "reason": req.reason,
    })
    return {"generation_id": generation_id, "shot_id": shot_id, "status": "accepted"}


@router.get("/{shot_id}/consistency")
async def get_consistency(project_id: str, shot_id: str) -> dict[str, Any]:
    """Get the drift report for a shot (blueprint Table 38 row 8).

    Returns a stub for now; the Consistency Check Agent (Day 9) will populate
    the per-attribute breakdown + recommendation.
    """
    return {
        "shot_id": shot_id,
        "drift_score": None,
        "breakdown": None,
        "recommendation": None,
        "note": "consistency check agent runs in the consistency-pipeline task",
    }
