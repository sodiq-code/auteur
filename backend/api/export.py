"""Auteur — /api/projects/{id}/assemble + /share + /export + /events (Table 38 rows 9-13).

These are stubs for now — the full implementations come in the assembly/export/share task.
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from ..bible import store

router = APIRouter(prefix="/projects/{project_id}", tags=["assembly-export"])


@router.post("/assemble")
async def assemble(project_id: str) -> dict[str, Any]:
    """Assemble the final film (blueprint Table 38 row 9). Stub for now."""
    await store.log_event(project_id, "assembly_started", {})
    return {"status": "accepted", "output_url": None,
            "note": "ffmpeg assembly comes in the assembly task"}


@router.post("/share")
async def create_share_link(project_id: str) -> dict[str, Any]:
    """Create a public share link (blueprint Table 38 row 10)."""
    import secrets
    slug = secrets.token_urlsafe(6)  # 8-char random slug (blueprint Table 39 row 7)
    await store.log_event(project_id, "share_link_created", {"slug": slug})
    return {"public_slug": slug, "share_url": f"/share/{slug}"}


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
