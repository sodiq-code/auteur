"""
Auteur — /api/projects (blueprint Table 38 rows 1-2).

POST /api/projects        — create a new project (from a logline)
GET  /api/projects/{id}   — get project state (project + bible + shots + events)
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..bible import store
from ..bible.schema import Project

router = APIRouter(prefix="/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    logline: str = Field(..., min_length=8, max_length=500)


class CreateProjectResponse(BaseModel):
    project_id: str
    logline: str
    status: str
    created_at: str


@router.post("", response_model=CreateProjectResponse)
async def create_project(req: CreateProjectRequest) -> CreateProjectResponse:
    """Create a new project from a logline (blueprint Table 38 row 1).

    The bible + shots are generated on-demand via the Director Agent (Day 6+).
    This endpoint just registers the project.
    """
    project = Project(logline=req.logline)
    await store.create_project(project)
    return CreateProjectResponse(
        project_id=project.id,
        logline=project.logline,
        status=project.status,
        created_at=project.created_at.isoformat(),
    )


@router.get("/{project_id}")
async def get_project(project_id: str) -> dict[str, Any]:
    """Get project state (blueprint Table 38 row 2)."""
    project = await store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    bible = await store.get_bible(project_id)
    shots = await store.get_shots(project_id)
    events = await store.get_events(project_id)
    return {
        "project": project.model_dump(mode="json"),
        "bible": bible.model_dump(mode="json") if bible else None,
        "shots": [s.model_dump(mode="json") for s in shots],
        "events": events,
    }
