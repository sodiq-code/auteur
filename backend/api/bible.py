"""
Auteur — /api/projects/{id}/bible (blueprint Table 38 rows 3-4).

GET  /api/projects/{id}/bible                       — get current bible
PATCH /api/projects/{id}/bible/entries/{entryId}    — edit a bible entry (creates a new version)
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..bible import store, versioning

router = APIRouter(prefix="/projects/{project_id}/bible", tags=["bible"])


@router.get("")
async def get_bible(project_id: str) -> dict[str, Any]:
    """Get the current (latest) bible version (blueprint Table 38 row 3)."""
    project = await store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    bible = await versioning.get_latest_bible(project_id)
    if not bible:
        raise HTTPException(status_code=404, detail="no bible yet — call the Director Agent")
    return {
        "bible": bible.model_dump(mode="json"),
        "version": bible.version,
    }


class EditEntryRequest(BaseModel):
    field: str
    value: str
    entry_type: Optional[str] = None  # characters | locations | style_anchors | ...


@router.patch("/entries/{entry_id}")
async def edit_entry(project_id: str, entry_id: str, req: EditEntryRequest) -> dict[str, Any]:
    """Edit a bible entry — creates a new immutable version (blueprint Table 38 row 4, 23.3)."""
    bible = await versioning.get_latest_bible(project_id)
    if not bible:
        raise HTTPException(status_code=404, detail="no bible to edit")

    # Find + mutate the entry across the typed collections
    mutated = False
    collections = [
        ("characters", bible.characters),
        ("locations", bible.locations),
        ("wardrobes", bible.wardrobes),
        ("style_anchors", bible.style_anchors),
        ("score_motifs", bible.score_motifs),
        ("voice_profiles", bible.voice_profiles),
        ("story_beats", bible.story_beats),
    ]
    for coll_name, coll in collections:
        for entry in coll:
            if entry.id == entry_id:
                if hasattr(entry, req.field):
                    old_val = getattr(entry, req.field)
                    setattr(entry, req.field, req.value)
                    mutated = True
                    await store.log_event(project_id, "bible_edited", {
                        "entry_id": entry_id, "collection": coll_name,
                        "field": req.field, "old": str(old_val), "new": req.value,
                    })
                break
        if mutated:
            break

    if not mutated:
        raise HTTPException(status_code=404, detail=f"entry {entry_id} or field {req.field} not found")

    # Persist as a new version (blueprint 23.3 — append-only, immutable snapshots)
    new_bible = bible.bump_version()
    await versioning.commit_bible_version(project_id, new_bible)
    return {
        "bible": new_bible.model_dump(mode="json"),
        "version": new_bible.version,
        "edited_entry": entry_id,
        "edited_field": req.field,
    }
