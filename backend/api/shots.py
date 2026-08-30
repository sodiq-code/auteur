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
    bible_version: int = 1


@router.post("/{shot_id}/regenerate")
async def regenerate_shot(project_id: str, shot_id: str, req: RegenerateRequest) -> dict[str, Any]:
    """Re-generate a shot (blueprint Table 38 row 7).

    Re-runs the generation pipeline (Veo + Chirp + Lyria) for the shot with the
    Bible injected as context, then re-runs the Consistency Check Agent so the
    caller can compare the before/after drift scores. This closes the agentic
    loop: drift > threshold -> regenerate -> re-check.
    """
    from ..pipelines import generate as generate_pipeline, check as check_pipeline

    project = await store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    shots = await store.get_shots(project_id)
    shot = next((s for s in shots if s.id == shot_id), None)
    if not shot:
        raise HTTPException(status_code=404, detail="shot not found")

    bible = await store.get_bible(project_id, version=req.bible_version) or await store.get_bible(project_id)
    if not bible:
        raise HTTPException(status_code=404, detail="no bible found — call POST /build-bible first")

    await store.log_event(project_id, "regeneration_started", {
        "shotId": shot_id, "reason": req.reason, "bible_version": bible.version,
    })

    # Re-run the generation pipeline (overwrites the previous generation in the store)
    gen_result = await generate_pipeline.generate_shot(project_id, shot, bible)

    # Re-run the consistency check so the caller can compare before/after
    check_result = await check_pipeline.check_shot(project_id, shot_id)

    return {
        "shot_id": shot_id,
        "status": "regenerated",
        "bible_version": bible.version,
        "generation": gen_result,
        "consistency": check_result,
    }


@router.get("/{shot_id}/consistency")
async def get_consistency(project_id: str, shot_id: str) -> dict[str, Any]:
    """Get the drift report for a shot (blueprint Table 38 row 8).

    If the consistency check hasn't been run yet, runs it now.
    Returns the drift score + per-attribute breakdown + recommendation.
    """
    # check if we already have a cached consistency report
    existing = await store.get_generation(project_id, shot_id, "consistency")
    if existing:
        return {"shot_id": shot_id, "status": "cached", **existing}

    # run the check
    from ..pipelines import check as check_pipeline
    result = await check_pipeline.check_shot(project_id, shot_id)
    return result


@router.post("/{shot_id}/consistency")
async def run_consistency(project_id: str, shot_id: str) -> dict[str, Any]:
    """Run the Consistency Check Agent on a shot (blueprint Day 9).

    Extracts a frame from the generated Veo clip, compares it to the character
    reference via Gemini 3.1 Pro vision, returns the drift score + breakdown.
    """
    from ..pipelines import check as check_pipeline
    project = await store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    shots = await store.get_shots(project_id)
    if not any(s.id == shot_id for s in shots):
        raise HTTPException(status_code=404, detail="shot not found")
    result = await check_pipeline.check_shot(project_id, shot_id)
    return result


@router.post("/check-all")
async def check_all_shots(project_id: str) -> dict[str, Any]:
    """Run the Consistency Check Agent on ALL shots (blueprint Day 9 DoD).

    Returns a summary with per-shot drift scores + the mean overall + the verdict.
    """
    from ..pipelines import check as check_pipeline
    project = await store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    result = await check_pipeline.check_all_shots(project_id)
    return result
