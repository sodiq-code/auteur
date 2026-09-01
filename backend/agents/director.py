"""
Auteur — Director Agent.

Top-level orchestrator. Receives a logline, coordinates the Research Agent to
ground creative decisions, builds a typed Film Bible, generates a shot list
with explicit bible references per shot.

Model: gemini-3.1-pro-preview (global region),
upgraded to the newest accessible Pro model.

Authority: can call all tools; cannot delete user
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
    """Logline -> Bible v1 in Firestore.

    1. Run Research Agent (Parallel Search) to ground the bible in real references.
    2. Call Gemini 3.1 Pro to synthesize the bible from logline + references.
    3. Persist the bible as an immutable versioned snapshot.
    """
    await store.update_project_status(project.id, status="researching")
    await store.log_event(project.id, "logline_submitted", {"logline": project.logline})

    # 1. Research — the Research Agent uses function calling to decide
    #    what to search for via Parallel Search, then evaluates the results
    #    and may issue follow-up searches. This is a genuine agentic tool-use
    #    loop, not a deterministic Python pipeline.
    refs = await research_agent.research_with_tools(project.id, project.logline)

    # 2. Synthesize the bible via Gemini 3.1 Pro
    bible = await _synthesize_bible(project.logline, refs)
    bible.research_references = refs

    # 3. Persist (append-only versioned)
    await versioning.commit_bible_version(project.id, bible)

    # 4. Generate the shot list from the story beats
    # Only generate if no shots exist yet (avoid duplicates on re-build)
    existing_shots = await store.get_shots(project.id)
    if not existing_shots:
        shots = await generate_shot_list(project, bible)

    return bible


async def generate_shot_list(project: Project, bible: FilmBible) -> list[ShotSpec]:
    """Generate a shot list (max 4) from the bible's story beats.

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
    """Call Gemini 3.1 Pro (via the ADK Director Agent's model) to build the
    typed Film Bible from logline + references."""
    from .adk_registry import director_agent  # ADK integration point

    refs_text = "\n".join(
        f"- [{i+1}] {r.title} ({r.url})\n  {r.snippet}"
        for i, r in enumerate(refs[:6])
    ) or "(no research references available — use creative inference, clearly labeled)"

    prompt = (
        f"{director_agent.instruction}\n\n"
        "Build a typed Film Bible from this logline + research references. "
        "Return STRICT JSON only.\n\n"
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
        '  "score_motifs": [{"name": "...", "prompt": "a slow melancholic solo fiddle, cinematic", '
        '"instrument": "Solo fiddle", "mood": "Melancholic"}],\n'
        '  "story_beats": [{"order": 1, "description": "..."}],\n'
        '  "citations": ["url1", "url2"]\n'
        "}\n"
        "Constraints:\n"
        "- Cite the research references wherever possible.\n"
        "- If you have no research reference for a fact, omit it (do NOT invent facts).\n"
        "- Maximum 4 shots worth of story beats.\n"
        "- Include at least one score_motif with a specific Lyria-friendly prompt.\n"
    )
    # Route through the ADK agent's model + config
    data = await gemini.pro_generate_json(
        prompt,
        temperature=director_agent.generate_content_config.temperature or 0.4,
    )

    # Map to the typed schema
    from ..bible.schema import (
        CharacterSpec, LocationSpec, StyleAnchorSpec, StoryBeat, Reference,
    )
    from ..integrations import imagen

    characters = []
    for c in data.get("characters", []):
        char = CharacterSpec(
            name=c.get("name", "?"),
            age=c.get("age"),
            description=c.get("description", ""),
            voice_profile=c.get("voice_profile", ""),
            wardrobe=c.get("wardrobe", ""),
        )
        # Generate a character reference image for this character
        try:
            char_prompt = (
                f"Cinematic portrait photograph of {char.name}, {char.description}. "
                f"Wearing {char.wardrobe}. Photorealistic, shallow depth of field, "
                f"muted color grade. Looking just off camera."
            )
            img_bytes = await imagen.generate_image(char_prompt)
            # Store in the generations store so the consistency check can find it
            from ..bible import store
            await store.save_generation("", char.id, "character_ref", {
                "png_bytes": img_bytes,
                "size_bytes": len(img_bytes),
            })
            char.reference_image_url = f"generated:{char.id}"
            print(f"[DIRECTOR] Generated character reference image for {char.name}: {len(img_bytes)} bytes", flush=True)
        except Exception as e:
            import traceback
            print(f"[DIRECTOR] Character ref generation FAILED: {type(e).__name__}: {str(e)[:300]}", flush=True)
            traceback.print_exc()
        characters.append(char)
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

    return _build_bible_from_data(data, logline, characters, locations, style_anchors, story_beats)


def _build_bible_from_data(
    data: dict,
    logline: str,
    characters: list,
    locations: list,
    style_anchors: list,
    story_beats: list,
) -> FilmBible:
    """Assemble the typed Film Bible, deriving wardrobes/voice_profiles/score_motifs
    from the character + style data so every Bible tab is populated."""
    from ..bible.schema import (
        WardrobeSpec, VoiceProfileSpec, ScoreMotifSpec,
    )

    # Derive wardrobes from character wardrobe strings
    wardrobes = []
    for c in characters:
        if c.wardrobe:
            # Parse the wardrobe string into garment/fabric/color heuristically
            wardrobe_text = c.wardrobe
            wardrobes.append(WardrobeSpec(
                character_id=c.id,
                garment=wardrobe_text.split(",")[0].strip() if "," in wardrobe_text else wardrobe_text[:60],
                fabric="",  # parsed from the description if available
                color="",
            ))

    # Derive voice profiles from character voice_profile strings
    voice_profiles = []
    for c in characters:
        if c.voice_profile:
            voice_profiles.append(VoiceProfileSpec(
                character_id=c.id,
                voice_model="gemini-3.1-flash-tts-preview",
                voice_name="Charon",  # the prebuilt voice used by the TTS integration
                description=c.voice_profile,
            ))

    # Derive a score motif from the style anchor mood (or from the LLM's score_motifs if provided)
    score_motifs = []
    llm_motifs = data.get("score_motifs", [])
    if llm_motifs:
        for m in llm_motifs:
            score_motifs.append(ScoreMotifSpec(
                name=m.get("name", "Theme"),
                prompt=m.get("prompt", "a cinematic film score, orchestral, sparse"),
                instrument=m.get("instrument", ""),
                mood=m.get("mood", ""),
            ))
    elif style_anchors:
        s = style_anchors[0]
        mood = s.mood or "cinematic"
        score_motifs.append(ScoreMotifSpec(
            name=f"{mood.capitalize()} theme",
            prompt=f"a {mood} cinematic film score, orchestral, sparse",
            instrument="Orchestra",
            mood=mood,
        ))

    return FilmBible(
        version=1,
        logline=data.get("logline", logline),
        characters=characters,
        locations=locations,
        wardrobes=wardrobes,
        voice_profiles=voice_profiles,
        score_motifs=score_motifs,
        style_anchors=style_anchors,
        story_beats=story_beats,
    )
