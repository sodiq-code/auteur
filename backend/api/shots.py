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
    use_drift_correction: bool = True


@router.post("/{shot_id}/regenerate")
async def regenerate_shot(project_id: str, shot_id: str, req: RegenerateRequest) -> dict[str, Any]:
    """Re-generate a shot, consuming the prior drift report as corrective context.

    This closes the agentic loop with causality: the regenerate path fetches
    the previous Consistency Check result, injects the per-attribute drift
    scores into the Veo prompt as targeted corrective context (e.g. "prior
    face identity 0.70 — preserve the exact facial features from the
    reference"), re-runs generation, and re-runs the check so the caller
    can compare before/after.

    If `use_drift_correction` is false, regenerates without the corrective
    context (a fresh stochastic sample for comparison).
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

    # Fetch the PRIOR drift report to inject as corrective context
    prior_drift = None
    if req.use_drift_correction:
        prior = await store.get_generation(project_id, shot_id, "consistency")
        if prior and prior.get("overall") is not None:
            prior_drift = prior

    await store.log_event(project_id, "regeneration_started", {
        "shotId": shot_id, "reason": req.reason, "bible_version": bible.version,
        "drift_correction": req.use_drift_correction,
        "prior_drift_score": prior_drift.get("drift_score") if prior_drift else None,
        "prior_overall": prior_drift.get("overall") if prior_drift else None,
    })

    # Re-run generation with the drift report injected as corrective context
    gen_result = await generate_pipeline.generate_shot(
        project_id, shot, bible, drift_report=prior_drift,
    )

    # Re-run the consistency check so the caller can compare before/after
    check_result = await check_pipeline.check_shot(project_id, shot_id)

    return {
        "shot_id": shot_id,
        "status": "regenerated",
        "bible_version": bible.version,
        "drift_correction_applied": req.use_drift_correction and prior_drift is not None,
        "prior_drift": {
            "overall": prior_drift.get("overall") if prior_drift else None,
            "drift_score": prior_drift.get("drift_score") if prior_drift else None,
        } if prior_drift else None,
        "generation": gen_result,
        "consistency": check_result,
    }


@router.post("/auto-regenerate")
async def auto_regenerate_drifted_shots(project_id: str) -> dict[str, Any]:
    """The autonomous closed loop.

    Runs the consistency check on every shot, then for every shot whose drift
    exceeds the threshold (0.25), automatically triggers regeneration with the
    drift report injected as corrective context, and re-checks. Returns the
    before/after for every shot that was regenerated.

    This is the endpoint that makes the "automatic regeneration" claim
    literally true: the system itself decides which shots to regenerate
    based on the drift threshold, without the caller specifying shot IDs.
    """
    from ..pipelines import generate as generate_pipeline, check as check_pipeline

    project = await store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    shots = await store.get_shots(project_id)
    if not shots:
        raise HTTPException(status_code=404, detail="no shots to check")

    bible = await store.get_bible(project_id)
    if not bible:
        raise HTTPException(status_code=404, detail="no bible found")

    # 1. Check all shots
    check_all = await check_pipeline.check_all_shots(project_id)

    # 2. For each shot above the drift threshold, auto-regenerate
    threshold = check_all.get("threshold", 0.25)
    regenerated = []
    for shot_report in check_all.get("shots", []):
        drift = shot_report.get("drift_score")
        if drift is not None and drift > threshold:
            shot = next((s for s in shots if s.id == shot_report["shot_id"]), None)
            if not shot:
                continue
            # Fetch the full drift report (with per-attribute scores) for correction
            prior = await store.get_generation(project_id, shot.id, "consistency")
            await store.log_event(project_id, "auto_regeneration_triggered", {
                "shotId": shot.id, "drift_score": drift, "threshold": threshold,
            })
            regen = await generate_pipeline.generate_shot(
                project_id, shot, bible, drift_report=prior,
            )
            recheck = await check_pipeline.check_shot(project_id, shot.id)
            regenerated.append({
                "shot_id": shot.id,
                "order": shot.order,
                "before": {
                    "overall": shot_report.get("overall"),
                    "drift_score": drift,
                    "recommendation": shot_report.get("recommendation"),
                },
                "after": {
                    "overall": recheck.get("overall"),
                    "drift_score": recheck.get("drift_score"),
                    "recommendation": recheck.get("recommendation"),
                },
                "drift_correction_applied": prior is not None,
            })

    return {
        "project_id": project_id,
        "status": "ok",
        "threshold": threshold,
        "shots_checked": len(shots),
        "shots_regenerated": len(regenerated),
        "regenerations": regenerated,
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
