"""
Auteur — public share view.

GET /api/share/{slug} — public endpoint that returns the project state + bible
+ film URL for anyone with the share slug. No auth required
row 6: 8-char random slug with ~2^48 entropy is the access control).
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from ..bible import store

router = APIRouter(prefix="/share", tags=["share"])


@router.get("/{slug}")
async def get_shared_project(slug: str) -> dict[str, Any]:
    """Get a project's public share view by its slug.

    Returns the project state + bible + film URL + shot list. Anyone with the
    slug can view it (no auth — the slug IS the access control
    39 row 6).
    """
    project_id = await store.get_project_by_slug(slug)
    if not project_id:
        raise HTTPException(status_code=404, detail="share link not found")

    project = await store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")

    bible = await store.get_bible(project_id)
    shots = await store.get_shots(project_id)

    # check if a film was assembled
    gens = await store.get_all_generations(project_id)
    film_gen = next((g for g in gens if g.get("modality") == "film"), None)
    film_url = f"/api/projects/{project_id}/film" if film_gen else None

    return {
        "project": project.model_dump(mode="json"),
        "bible": bible.model_dump(mode="json") if bible else None,
        "shots": [s.model_dump(mode="json") for s in shots],
        "film_url": film_url,
        "share_slug": slug,
    }
