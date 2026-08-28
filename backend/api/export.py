"""Auteur — /api/projects/{id}/assemble + /share + /export + /events (Table 38 rows 9-13).

The assemble endpoint runs the real ffmpeg assembly pipeline (pipelines/assemble.py).
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from ..bible import store
from ..pipelines import assemble as assemble_pipeline

router = APIRouter(prefix="/projects/{project_id}", tags=["assembly-export"])


@router.post("/assemble")
async def assemble(project_id: str) -> dict[str, Any]:
    """Assemble the final film (blueprint Table 38 row 9).

    Runs the real ffmpeg assembly: concatenates all generated Veo clips into
    a single MP4. Returns the output URL + duration + clip count.
    """
    project = await store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    try:
        result = await assemble_pipeline.assemble_film(project_id)
        # update project status
        await store.update_project_status(project_id, status="assembled")
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        await store.log_event(project_id, "assembly_failed", {"error": str(e)[:300]})
        raise HTTPException(status_code=500, detail=f"assembly failed: {str(e)[:200]}") from e


@router.post("/share")
async def create_share_link(project_id: str) -> dict[str, Any]:
    """Create a public share link (blueprint Table 38 row 10).

    Generates an 8-char random slug (~2^48 entropy, blueprint Table 39 row 7),
    persists the slug → project_id mapping, returns the share URL.
    """
    project = await store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    slug = await store.create_share_link(project_id)
    await store.update_project_status(project_id, status="shared")
    return {"public_slug": slug, "share_url": f"/api/share/{slug}"}


@router.get("/export/bible")
async def export_bible(project_id: str) -> dict[str, Any]:
    """Export the bible as JSON (blueprint Table 38 row 11)."""
    bible = await store.get_bible(project_id)
    if not bible:
        raise HTTPException(status_code=404, detail="no bible to export")
    return bible.model_dump(mode="json")


@router.get("/export/shots", response_class=PlainTextResponse)
async def export_shots_csv(project_id: str) -> str:
    """Export the shot list as CSV (blueprint Table 38 row 12)."""
    shots = await store.get_shots(project_id)
    rows = ["order,id,status,bible_version,description"]
    for s in shots:
        desc = s.description.replace('"', '""')
        rows.append(f'{s.order},{s.id},{s.status},{s.bible_version},"{desc}"')
    return "\n".join(rows)


@router.get("/events")
async def get_events(project_id: str) -> dict[str, Any]:
    """Get the event log (blueprint Table 38 row 13)."""
    events = await store.get_events(project_id)
    return {"project_id": project_id, "events": events, "count": len(events)}


@router.get("/film")
async def get_film(project_id: str):
    """Stream the assembled final film MP4 (for the AssemblyView video player)."""
    from fastapi.responses import StreamingResponse
    import io
    # find the assembled film in the generations store
    gens = await store.get_all_generations(project_id)
    film_gen = next((g for g in gens if g.get("modality") == "film"), None)
    if not film_gen or not film_gen.get("mp4_bytes"):
        raise HTTPException(status_code=404, detail="no assembled film — call POST /assemble first")
    return StreamingResponse(
        io.BytesIO(film_gen["mp4_bytes"]),
        media_type="video/mp4",
        headers={"Content-Disposition": f"inline; filename=auteur_film.mp4"},
    )


@router.get("/shots/{shot_id}/video")
async def get_shot_video(project_id: str, shot_id: str):
    """Stream a single shot's Veo MP4 (for the ShotGrid video player)."""
    from fastapi.responses import StreamingResponse
    import io
    gen = await store.get_generation(project_id, shot_id, "veo")
    if not gen or not gen.get("mp4_bytes"):
        raise HTTPException(status_code=404, detail="no video for this shot — generate first")
    return StreamingResponse(
        io.BytesIO(gen["mp4_bytes"]),
        media_type="video/mp4",
        headers={"Content-Disposition": f"inline; filename=shot_{shot_id}.mp4"},
    )
