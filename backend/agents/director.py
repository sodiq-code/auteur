"""
Auteur — Director Agent (blueprint Section 22.1, Table 29).

Top-level orchestrator. Receives a logline, coordinates the Research Agent to
ground creative decisions, builds a typed Film Bible, generates a shot list
with explicit bible references per shot.

Model: gemini-3.1-pro-preview (global region) — blueprint "Gemini 2.5 Pro",
upgraded to the newest accessible Pro model.

Authority (blueprint Table 29 row 7): can call all tools; cannot delete user
data; cannot call Parallel Search directly (delegates to Research Agent).
"""
from __future__ import annotations

import json
from typing import Any

from . import research as research_agent
from ..integrations import gemini
from ..bible import store, versioning
from ..bible.schema import FilmBible, Project, ShotSpec


async def build_bible(project: Project) -> FilmBible:
    """Logline -> Bible v1 in Firestore (blueprint Day 6 definition of done).

    1. Run Research Agent (Parallel Search) to ground the bible in real references.
    2. Call Gemini 3.1 Pro to synthesize the bible from logline + references.
    3. Persist the bible as an immutable versioned snapshot.
    """
    await store.update_project_status(project.id, status="researching")
    await store.log_event(project.id, "logline_submitted", {"logline": project.logline})

    # 1. Research
    objective = (
        f"Find historical references for a film with this logline: {project.logline}. "
        "Cover: era, setting, fashion/wardrobe, technology, music, mood."
    )
    queries = [
        project.logline,
        f"historical context: {project.logline}",
        "wardrobe + setting for the era",
    ]
    refs = await research_agent.research(project.id, objective, queries)

    # 2. Synthesize the bible via Gemini 3.1 Pro
    bible = await _synthesize_bible(project.logline, refs)
    bible.research_references = refs

    # 3. Persist (append-only versioned)
    await versioning.commit_bible_version(project.id, bible)

    # 4. Generate the shot list from the story beats (blueprint Day 7 prerequisite)
    shots = await generate_shot_list(project, bible)

    return bible


async def generate_shot_list(project: Project, bible: FilmBible) -> list[ShotSpec]:
    """Generate a shot list (max 4) with explicit bible references per shot.

    Called automatically after the bible is built, so the generation pipeline
    (Day 7) has shots to generate.
    """
    # Build shots from story beats (max 4 — hackathon scope)
    shots = []
    for i, beat in enumerate(bible.story_beats[:4]):
        shot = ShotSpec(
            order=beat.order,
            description=beat.description,
            bible_version=bible.version,
            character_ids=[c.id for c in bible.characters],
            location_id=bible.locations[0].id if bible.locations else None,
            modality_calls=["veo", "chirp", "lyria"],
        )
        await store.save_shot(shot, project.id)
        shots.append(shot)
    await store.log_event(project.id, "shot_list_generated", {"count": len(shots)})
    return shots


async def _synthesize_bible(logline: str, refs: list) -> FilmBible:
    """Call Gemini 3.1 Pro to build the typed Film Bible from logline + references."""
    refs_text = "\n".join(
        f"- [{i+1}] {r.title} ({r.url})\n  {r.snippet}"
        for i, r in enumerate(refs[:6])
    ) or "(no research references available — use creative inference, clearly labeled)"

    prompt = (
        "You are Auteur's Director Agent (blueprint Section 22.1). Build a typed "
        "Film Bible from this logline + research references. Return STRICT JSON only.\n\n"
        f"LOGLINE: {logline}\n\n"
        f"RESEARCH REFERENCES:\n{refs_text}\n\n"
        "Return JSON with this exact schema:\n"
        "{\n"
        '  "logline": "...",\n'
        '  "characters": [{"name": "...", "age": 52, "description": "...", '
        '"voice_profile": "...", "wardrobe": "..."}],\n'
        '  "locations": [{"name": "...", "description": "...", "era": "1892"}],\n'
        '  "style_anchors": [{"color_grade": "...", "aspect_ratio": "16:9", '
        '"photographic_aesthetic": "...", "mood": "..."}],\n'
        '  "story_beats": [{"order": 1, "description": "..."}],\n'
        '  "citations": ["url1", "url2"]\n'
        "}\n"
        "Constraints:\n"
        "- Cite the research references wherever possible.\n"
        "- If you have no research reference for a fact, omit it (do NOT invent facts).\n"
        "- Maximum 4 shots worth of story beats (hackathon scope).\n"
    )
    data = await gemini.pro_generate_json(prompt, temperature=0.4)

    # Map to the typed schema
    from ..bible.schema import (
        CharacterSpec, LocationSpec, StyleAnchorSpec, StoryBeat, Reference,
    )
    characters = [CharacterSpec(
        name=c.get("name", "?"),
        age=c.get("age"),
        description=c.get("description", ""),
        voice_profile=c.get("voice_profile", ""),
        wardrobe=c.get("wardrobe", ""),
    ) for c in data.get("characters", [])]
    locations = [LocationSpec(
        name=l.get("name", "?"),
        description=l.get("description", ""),
        era=l.get("era", ""),
    ) for l in data.get("locations", [])]
    style_anchors = [StyleAnchorSpec(
        color_grade=s.get("color_grade", ""),
        aspect_ratio=s.get("aspect_ratio", "16:9"),
        photographic_aesthetic=s.get("photographic_aesthetic", ""),
        mood=s.get("mood", ""),
    ) for s in data.get("style_anchors", [])]
    story_beats = [StoryBeat(
        order=b.get("order", i+1),
        description=b.get("description", ""),
    ) for i, b in enumerate(data.get("story_beats", []))]

    return FilmBible(
        version=1,
        logline=data.get("logline", logline),
        characters=characters,
        locations=locations,
        style_anchors=style_anchors,
        story_beats=story_beats,
    )


async def generate_shot_list(project: Project, bible: FilmBible) -> list[ShotSpec]:
    """Generate a shot list (max 4) with explicit bible references per shot."""
    prompt = (
        "You are Auteur's Director Agent. Generate a shot list for this Film Bible. "
        f"Return STRICT JSON. Maximum 4 shots (hackathon scope).\n\n"
        f"BIBLE: {bible.model_dump_json(indent=2)}\n\n"
        "Return JSON: {\"shots\": [{\"order\": 1, \"description\": \"...\", "
        "\"character_names\": [\"...\"], \"location_name\": \"...\", "
        "\"modality_calls\": [\"veo\", \"chirp\", \"lyria\"]}]}\n"
    )
    data = await gemini.pro_generate_json(prompt, temperature=0.3)
    shots = []
    char_by_name = {c.name: c for c in bible.characters}
    loc_by_name = {l.name: l for l in bible.locations}
    for s in data.get("shots", [])[:4]:
        char_ids = [char_by_name[n].id for n in s.get("character_names", []) if n in char_by_name]
        loc = loc_by_name.get(s.get("location_name", ""))
        shots.append(ShotSpec(
            order=s.get("order", len(shots) + 1),
            description=s.get("description", ""),
            bible_version=bible.version,
            character_ids=char_ids,
            location_id=loc.id if loc else None,
            modality_calls=s.get("modality_calls", ["veo", "chirp", "lyria"]),
        ))
        await store.save_shot(shots[-1], project.id)
    await store.log_event(project.id, "shot_list_generated", {"count": len(shots)})
    return shots
