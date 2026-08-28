"""
Auteur — Bible versioning (blueprint Section 23.3).

Every user edit creates a new immutable Bible version (append-only). Every
generation cites which Bible version it used, so drift is attributable:
"Shot 3 was generated with Bible v2; user changed beard color at v3;
re-generation pending."

This module provides the versioning helpers on top of the store.
"""
from __future__ import annotations

from typing import Optional

from .schema import FilmBible
from . import store


async def commit_bible_version(project_id: str, bible: FilmBible) -> FilmBible:
    """Persist a new immutable Bible version + bump the project's current version."""
    await store.save_bible(project_id, bible)
    await store.update_project_status(
        project_id, status="bible_v1" if bible.version == 1 else "bible_v1",
        bible_version=bible.version,
    )
    return bible


async def get_latest_bible(project_id: str) -> Optional[FilmBible]:
    return await store.get_bible(project_id)


async def get_bible_at_version(project_id: str, version: int) -> Optional[FilmBible]:
    """Citation lookup: which Bible version produced this shot? (blueprint 23.3)."""
    return await store.get_bible(project_id, version=version)
