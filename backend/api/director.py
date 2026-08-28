"""
Auteur — /api/projects/{id}/build-bible + /api/projects/{id}/research
(blueprint Table 38 — the Director Agent runtime endpoints).

POST /api/projects/{id}/build-bible
    Runs the Director Agent at runtime:
      1. Research Agent calls Parallel Search (x-api-key) → grounded references
      2. Gemini 3.1 Pro synthesizes a typed Film Bible from the references
      3. Persists the Bible as an immutable versioned snapshot (Firestore)
    Returns the synthesized Bible v1 + the research references.

GET /api/projects/{id}/research
    Returns the cached research references for a project (24h TTL).

These are the runtime endpoints that make the partner API visible to judges
(blueprint Section 26.3 / P670 — the #1 anti-anti-pattern mitigation).
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from ..agents import director
from ..bible import store
from ..bible.schema import Reference

router = APIRouter(prefix="/projects/{project_id}", tags=["director-agent"])


@router.post("/build-bible")
async def build_bible(project_id: str) -> dict[str, Any]:
    """Run the Director Agent: Parallel Search → Gemini Pro → Bible v1 (runtime).

    This is the endpoint the frontend ResearchView calls when the user submits
    a logline. It returns the synthesized Bible + the grounded references.
    """
    project = await store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")

    try:
        bible = await director.build_bible(project)
    except Exception as e:
        await store.log_event(project_id, "bible_build_failed", {"error": str(e)[:300]})
        raise HTTPException(status_code=500, detail=f"bible build failed: {str(e)[:200]}") from e

    return {
        "bible": bible.model_dump(mode="json"),
        "version": bible.version,
        "references": [r.model_dump(mode="json") for r in bible.research_references],
        "references_count": len(bible.research_references),
        "project_status": "bible_v1",
    }


@router.get("/research")
async def get_research(project_id: str) -> dict[str, Any]:
    """Get the cached research references for a project (blueprint 24.4 — 24h TTL)."""
    project = await store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")

    # get the latest bible (which holds the research_references)
    bible = await store.get_bible(project_id)
    if not bible:
        return {"references": [], "references_count": 0, "note": "no bible yet — call POST /build-bible"}

    return {
        "references": [r.model_dump(mode="json") for r in bible.research_references],
        "references_count": len(bible.research_references),
        "bible_version": bible.version,
    }
