"""
Auteur — Firestore CRUD for projects + bibles (blueprint Section 24 / Table 33).

Collections:
  projects/{projectId}                         — project state
  bibles/{projectId}_{version}                  — immutable Bible snapshots (append-only)
  shots/{auto-id}                               — shot list (projectId, order, status)
  search_cache/{projectId}_{queryHash}          — Parallel Search results (24h TTL)

This module wraps the Firestore async client. In dev (no GCP creds / emulator)
it falls back to an in-memory store so the API surface is testable end-to-end
without provisioning Firestore.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from .schema import FilmBible, Project, ShotSpec

# --------------------------------------------------------------------------- #
# Region selection — Firestore is multi-region native mode for this project
# --------------------------------------------------------------------------- #

FIRESTORE_PROJECT = os.environ.get("GCP_PROJECT_ID", "auteur-506523")
FIRESTORE_DATABASE = os.environ.get("FIRESTORE_DATABASE", "auteur")  # created on the project


# --------------------------------------------------------------------------- #
# In-memory fallback (dev / tests / Cloud Run cold path before Firestore warm)
# --------------------------------------------------------------------------- #

class _MemoryStore:
    """Dict-backed store mirroring the Firestore collection layout."""

    def __init__(self) -> None:
        self.projects: dict[str, dict[str, Any]] = {}
        self.bibles: dict[str, dict[str, Any]] = {}  # key = projectId_version
        self.shots: dict[str, dict[str, Any]] = {}   # key = shotId
        self.search_cache: dict[str, dict[str, Any]] = {}
        self.events: dict[str, list[dict[str, Any]]] = {}  # projectId -> events


_MEMORY = _MemoryStore()
_FIRESTORE_CLIENT = None
_USE_MEMORY = True  # flipped to False once Firestore client initializes

# Initialize Firestore on module load (don't wait for the first store call)
try:
    from google.cloud import firestore as firestore_sync
    _FIRESTORE_CLIENT = firestore_sync.Client(project=FIRESTORE_PROJECT, database=FIRESTORE_DATABASE)
    _USE_MEMORY = False
    print(f"[STORE] Firestore initialized at module load (db={FIRESTORE_DATABASE})", flush=True)
except Exception as e:
    _FIRESTORE_CLIENT = None
    _USE_MEMORY = True
    print(f"[STORE] Firestore init FAILED at module load, using in-memory: {str(e)[:200]}", flush=True)


def _get_firestore():
    """Lazily init the Firestore async client; fall back to memory on failure."""
    global _FIRESTORE_CLIENT, _USE_MEMORY
    if not _USE_MEMORY and _FIRESTORE_CLIENT is not None:
        return _FIRESTORE_CLIENT
    try:
        from google.cloud import firestore_async
        _FIRESTORE_CLIENT = firestore_async.Client(project=FIRESTORE_PROJECT, database=FIRESTORE_DATABASE)
        _USE_MEMORY = False
        print(f"[STORE] Firestore initialized (db={FIRESTORE_DATABASE})", flush=True)
        return _FIRESTORE_CLIENT
    except Exception as e:
        print(f"[STORE] Firestore init FAILED, using in-memory: {str(e)[:200]}", flush=True)
        _USE_MEMORY = True
        return None


# --------------------------------------------------------------------------- #
# Projects
# --------------------------------------------------------------------------- #

async def create_project(project: Project) -> Project:
    db = _get_firestore()
    data = project.model_dump(mode="json")
    if _USE_MEMORY or db is None:
        _MEMORY.projects[project.id] = data
        _MEMORY.events[project.id] = []
    else:
        db.collection("projects").document(project.id).set(data)
    await log_event(project.id, "project_created", {"logline": project.logline})
    return project


async def get_project(project_id: str) -> Optional[Project]:
    db = _get_firestore()
    if _USE_MEMORY or db is None:
        data = _MEMORY.projects.get(project_id)
    else:
        doc = db.collection("projects").document(project_id).get()
        data = doc.to_dict() if doc.exists else None
    return Project(**data) if data else None


async def update_project_status(project_id: str, status: str, bible_version: Optional[int] = None) -> None:
    db = _get_firestore()
    if _USE_MEMORY or db is None:
        if project_id in _MEMORY.projects:
            _MEMORY.projects[project_id]["status"] = status
            if bible_version is not None:
                _MEMORY.projects[project_id]["current_bible_version"] = bible_version
    else:
        update: dict[str, Any] = {"status": status}
        if bible_version is not None:
            update["current_bible_version"] = bible_version
        db.collection("projects").document(project_id).update(update)
    await log_event(project_id, "project_status_changed", {"status": status, "bible_version": bible_version})


# --------------------------------------------------------------------------- #
# Bibles (append-only versioned)
# --------------------------------------------------------------------------- #

async def save_bible(project_id: str, bible: FilmBible) -> FilmBible:
    """Persist a Bible as an immutable versioned snapshot (blueprint 23.3)."""
    key = f"{project_id}_{bible.version}"
    # Also store project_id + version as top-level fields for simple queries
    db = _get_firestore()
    data = bible.model_dump(mode="json")
    data["project_id"] = project_id
    data["version_num"] = bible.version
    if _USE_MEMORY or db is None:
        _MEMORY.bibles[key] = data
    else:
        db.collection("bibles").document(key).set(data)
    await log_event(project_id, "bible_built" if bible.version == 1 else "bible_edited",
                    {"version": bible.version})
    return bible


async def get_bible(project_id: str, version: Optional[int] = None) -> Optional[FilmBible]:
    db = _get_firestore()
    if version is not None:
        key = f"{project_id}_{version}"
        if _USE_MEMORY or db is None:
            data = _MEMORY.bibles.get(key)
        else:
            doc = db.collection("bibles").document(key).get()
            data = doc.to_dict() if doc.exists else None
        if data:
            data.pop("project_id", None)
            data.pop("version_num", None)
        return FilmBible(**data) if data else None
    # no version — get the latest by trying version 1, 2, 3... (avoids composite index)
    if _USE_MEMORY or db is None:
        candidates = [k for k in _MEMORY.bibles if k.startswith(f"{project_id}_")]
        if not candidates:
            return None
        latest_key = max(candidates, key=lambda k: int(k.rsplit("_", 1)[1]))
        data = _MEMORY.bibles[latest_key]
        data.pop("project_id", None)
        data.pop("version_num", None)
        return FilmBible(**data)
    else:
        # Try version 1 first, then 2, 3 (avoids needing a composite index)
        for v in [1, 2, 3, 4, 5]:
            key = f"{project_id}_{v}"
            doc = db.collection("bibles").document(key).get()
            if doc.exists:
                data = doc.to_dict()
                data.pop("project_id", None)
                data.pop("version_num", None)
                return FilmBible(**data)
            # If v=1 doesn't exist, no bible yet
            if v == 1 and not doc.exists:
                return None
        return None


# --------------------------------------------------------------------------- #
# Shots
# --------------------------------------------------------------------------- #

async def save_shot(shot: ShotSpec, project_id: str) -> ShotSpec:
    db = _get_firestore()
    data = {**shot.model_dump(mode="json"), "projectId": project_id}
    if _USE_MEMORY or db is None:
        _MEMORY.shots[shot.id] = data
    else:
        db.collection("shots").document(shot.id).set(data)
    return shot


async def get_shots(project_id: str) -> list[ShotSpec]:
    db = _get_firestore()
    if _USE_MEMORY or db is None:
        rows = [s for s in _MEMORY.shots.values() if s.get("projectId") == project_id]
    else:
        docs = db.collection("shots").where("projectId", "==", project_id).stream()
        rows = [doc.to_dict() for doc in docs]
    rows.sort(key=lambda r: r.get("order", 0))
    return [ShotSpec(**{k: v for k, v in r.items() if k != "projectId"}) for r in rows]


# --------------------------------------------------------------------------- #
# Generations (the MP4/WAV bytes from Veo/Chirp/Lyria — for assembly)
# --------------------------------------------------------------------------- #

_GENERATIONS: dict[str, dict[str, Any]] = {}  # key = {projectId}_{shotId}_{modality}
_SHARE_LINKS: dict[str, str] = {}  # slug -> project_id


def _gen_key(project_id: str, shot_id: str, modality: str) -> str:
    return f"{project_id}_{shot_id}_{modality}"


async def save_generation(project_id: str, shot_id: str, modality: str, data: dict[str, Any]) -> None:
    """Persist a generation result (incl. MP4/WAV bytes) for later assembly.

    NOTE: for the hackathon, large binary blobs (MP4/WAV) are stored in-memory
    (per Cloud Run instance) rather than Firestore (which has a 1MB doc limit).
    Cloud Storage is the production path; the in-memory store is sufficient for
    the demo flow within a single instance (min-instances=1).
    """
    key = _gen_key(project_id, shot_id, modality)
    _GENERATIONS[key] = data
    # Only log to Firestore if project_id is valid (not empty)
    if project_id:
        await log_event(project_id, "generation_saved", {
            "shotId": shot_id, "modality": modality,
            "size_bytes": data.get("size_bytes", 0),
        })


async def get_generation(project_id: str, shot_id: str, modality: str) -> dict[str, Any] | None:
    """Retrieve a generation result by project + shot + modality."""
    return _GENERATIONS.get(_gen_key(project_id, shot_id, modality))


async def get_all_generations(project_id: str) -> list[dict[str, Any]]:
    """Get all generation results for a project (for the render queue + assembly)."""
    return [
        {**v, "shot_id": k.split("_")[1], "modality": k.split("_")[2]}
        for k, v in _GENERATIONS.items()
        if k.startswith(f"{project_id}_")
    ]


# --------------------------------------------------------------------------- #
# Share links (slug → project_id, blueprint Table 33 + Table 39 row 7)
# --------------------------------------------------------------------------- #

async def create_share_link(project_id: str) -> str:
    """Create a public share slug for a project. Returns the slug."""
    import secrets
    slug = secrets.token_urlsafe(6)  # 8-char random slug (~2^48 entropy, blueprint Table 39 row 7)
    _SHARE_LINKS[slug] = project_id
    await log_event(project_id, "share_link_created", {"slug": slug})
    return slug


async def get_project_by_slug(slug: str) -> str | None:
    """Look up a project_id by its share slug (for the public share view)."""
    return _SHARE_LINKS.get(slug)


# --------------------------------------------------------------------------- #
# Search cache (24h TTL — blueprint Table 28 row 2 / 24.4)
# --------------------------------------------------------------------------- #

CACHE_TTL = timedelta(hours=24)


def _query_hash(query: str) -> str:
    return hashlib.sha256(query.encode()).hexdigest()[:16]


async def cache_get_search(project_id: str, query: str) -> Optional[list[dict]]:
    key = f"{project_id}_{_query_hash(query)}"
    db = _get_firestore()
    if _USE_MEMORY or db is None:
        row = _MEMORY.search_cache.get(key)
    else:
        doc = db.collection("search_cache").document(key).get()
        row = doc.to_dict() if doc.exists else None
    if not row:
        return None
    if datetime.now(timezone.utc) > row["expires_at"]:
        return None  # expired
    return row.get("results")


async def cache_set_search(project_id: str, query: str, results: list[dict]) -> None:
    key = f"{project_id}_{_query_hash(query)}"
    row = {
        "projectId": project_id,
        "query": query,
        "results": results,
        "retrieved_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + CACHE_TTL,
    }
    db = _get_firestore()
    if _USE_MEMORY or db is None:
        _MEMORY.search_cache[key] = row
    else:
        db.collection("search_cache").document(key).set(row)


# --------------------------------------------------------------------------- #
# Event log (audit + demo narrative — blueprint Table 33 / 24.3)
# --------------------------------------------------------------------------- #

async def log_event(project_id: str, event_type: str, payload: Optional[dict] = None) -> None:
    evt = {
        "type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload or {},
    }
    db = _get_firestore()
    if _USE_MEMORY or db is None or not project_id:
        _MEMORY.events.setdefault(project_id, []).append(evt)
    else:
        # Sync Firestore client — call directly (no await)
        db.collection("projects").document(project_id).collection("events").add(evt)


async def get_events(project_id: str) -> list[dict]:
    db = _get_firestore()
    if _USE_MEMORY or db is None:
        return _MEMORY.events.get(project_id, [])
    else:
        docs = db.collection("projects").document(project_id).collection("events").stream()
        return [doc.to_dict() for doc in docs]
