"""
Auteur — generation pipeline (blueprint Section 32.2 Day 7).

Orchestrates Veo 3.1 (video) + Chirp 3 (voice) + Lyria 2 (music) per shot,
with the Film Bible injected as context. Each modality call is independent
and runs concurrently; results are collected + logged.

The pipeline is called by POST /api/projects/{id}/shots/{shotId}/generate.

Definition of done (blueprint P854): shot list → 4 shots generate end-to-end
in UI. For a single shot: Veo + Chirp + Lyria all complete within ~90s.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

from ..bible import store
from ..bible.schema import FilmBible, ShotSpec
from ..integrations import veo, chirp, lyria, imagen
from ..storage import cloud_storage


async def generate_shot(
    project_id: str,
    shot: ShotSpec,
    bible: FilmBible,
) -> dict[str, Any]:
    """Generate all modalities for one shot (blueprint Day 7 DoD).

    Runs Veo (video) + Chirp (voice) + Lyria (music) concurrently.
    Each modality is independent — if one fails, the others still complete
    (blueprint Table 40 per-API failure handling).

    Returns a dict with per-modality status + output URIs + total elapsed.
    """
    t0 = time.time()
    await store.log_event(project_id, "generation_started", {
        "shotId": shot.id, "order": shot.order,
        "bible_version": shot.bible_version,
        "modalities": shot.modality_calls,
    })

    # Build the prompts from the Bible + shot description
    char_ref_png = None
    if bible.characters:
        # Use the first character's reference image if available
        # (in production, this would be a Cloud Storage URI; for now
        # the Day-1 validation images serve as the canonical reference)
        pass  # Veo will use text-to-video if no char ref (Day 11 wires the real ASSET ref)

    veo_prompt = _build_veo_prompt(shot, bible)
    tts_line = _build_tts_line(shot, bible)
    lyria_prompt = _build_lyria_prompt(bible)

    # Run all modalities concurrently (blueprint Table 36 — they're independent)
    tasks = {}
    if "veo" in shot.modality_calls:
        tasks["veo"] = asyncio.create_task(
            _run_veo(project_id, shot, veo_prompt, char_ref_png),
        )
    if "chirp" in shot.modality_calls:
        tasks["chirp"] = asyncio.create_task(
            _run_chirp(project_id, shot, tts_line),
        )
    if "lyria" in shot.modality_calls:
        tasks["lyria"] = asyncio.create_task(
            _run_lyria(project_id, shot, lyria_prompt),
        )

    # Wait for all to complete (each handles its own errors internally)
    results = {}
    for name, task in tasks.items():
        try:
            results[name] = await task
        except Exception as e:
            results[name] = {"status": "failed", "error": str(e)[:200]}

    elapsed = round(time.time() - t0, 2)

    # Update shot status
    all_ok = all(r.get("status") == "ok" for r in results.values()) if results else False
    new_status = "generated" if all_ok else "generating"
    await _update_shot_status(project_id, shot.id, new_status)

    await store.log_event(project_id, "generation_completed", {
        "shotId": shot.id,
        "modalities": {k: v.get("status") for k, v in results.items()},
        "elapsed_sec": elapsed,
        "all_ok": all_ok,
    })

    return {
        "shot_id": shot.id,
        "order": shot.order,
        "status": new_status,
        "modalities": results,
        "elapsed_sec": elapsed,
    }


# --------------------------------------------------------------------------- #
# Per-modality runners (each catches its own errors — blueprint Table 40)
# --------------------------------------------------------------------------- #

async def _run_veo(project_id: str, shot: ShotSpec, prompt: str, char_ref: bytes | None) -> dict:
    """Veo 3.1 video generation (blueprint Table 40 row 2-3)."""
    t0 = time.time()
    try:
        mp4 = await veo.generate_video(
            prompt=prompt,
            character_ref_png=char_ref,
            duration_seconds=8,
            resolution="720p",
            generate_audio=False,
        )
        elapsed = round(time.time() - t0, 2)
        # Upload to Cloud Storage
        blob_name = f"{project_id}/{shot.id}_veo.mp4"
        try:
            uri = cloud_storage.upload_bytes(blob_name, mp4, content_type="video/mp4")
        except Exception:
            uri = None  # storage optional for dev
        await store.log_event(project_id, "generation_completed", {
            "shotId": shot.id, "modality": "veo", "elapsed_sec": elapsed,
            "size_bytes": len(mp4), "uri": uri,
        })
        return {
            "status": "ok", "modality": "veo",
            "model": veo.VEO_MODEL_FAST,
            "size_bytes": len(mp4),
            "uri": uri,
            "elapsed_sec": elapsed,
        }
    except Exception as e:
        await store.log_event(project_id, "generation_failed", {
            "shotId": shot.id, "modality": "veo", "error": str(e)[:200],
        })
        return {"status": "failed", "modality": "veo", "error": str(e)[:200]}


async def _run_chirp(project_id: str, shot: ShotSpec, line: str) -> dict:
    """Chirp 3 / Gemini TTS voiceover (blueprint Table 40 row 4)."""
    t0 = time.time()
    try:
        pcm = await chirp.generate_voiceover(line, voice_name="Charon")
        elapsed = round(time.time() - t0, 2)
        # Wrap PCM as WAV
        import wave, io
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000)
            w.writeframes(pcm)
        wav = buf.getvalue()
        blob_name = f"{project_id}/{shot.id}_chirp.wav"
        try:
            uri = cloud_storage.upload_bytes(blob_name, wav, content_type="audio/wav")
        except Exception:
            uri = None
        await store.log_event(project_id, "generation_completed", {
            "shotId": shot.id, "modality": "chirp", "elapsed_sec": elapsed,
            "size_bytes": len(wav), "uri": uri,
        })
        return {
            "status": "ok", "modality": "chirp",
            "model": chirp.TTS_MODEL,
            "size_bytes": len(wav),
            "uri": uri,
            "elapsed_sec": elapsed,
        }
    except Exception as e:
        await store.log_event(project_id, "generation_failed", {
            "shotId": shot.id, "modality": "chirp", "error": str(e)[:200],
        })
        return {"status": "failed", "modality": "chirp", "error": str(e)[:200]}


async def _run_lyria(project_id: str, shot: ShotSpec, prompt: str) -> dict:
    """Lyria 2 score (blueprint Table 40 row 5)."""
    t0 = time.time()
    try:
        wav = await lyria.generate_score(prompt)
        elapsed = round(time.time() - t0, 2)
        blob_name = f"{project_id}/{shot.id}_lyria.wav"
        try:
            uri = cloud_storage.upload_bytes(blob_name, wav, content_type="audio/wav")
        except Exception:
            uri = None
        await store.log_event(project_id, "generation_completed", {
            "shotId": shot.id, "modality": "lyria", "elapsed_sec": elapsed,
            "size_bytes": len(wav), "uri": uri,
        })
        return {
            "status": "ok", "modality": "lyria",
            "model": lyria.LYRIA_MODEL,
            "size_bytes": len(wav),
            "uri": uri,
            "elapsed_sec": elapsed,
        }
    except Exception as e:
        await store.log_event(project_id, "generation_failed", {
            "shotId": shot.id, "modality": "lyria", "error": str(e)[:200],
        })
        return {"status": "failed", "modality": "lyria", "error": str(e)[:200]}


# --------------------------------------------------------------------------- #
# Prompt builders — inject the Bible as context (the core innovation)
# --------------------------------------------------------------------------- #

def _build_veo_prompt(shot: ShotSpec, bible: FilmBible) -> str:
    """Build the Veo prompt with Bible context injected (blueprint Section 17)."""
    parts = [shot.description]
    if bible.characters:
        c = bible.characters[0]
        parts.append(f"Featuring {c.name}")
        if c.wardrobe:
            parts.append(f"wearing {c.wardrobe}")
        if c.description:
            parts.append(c.description)
    if bible.locations:
        loc = bible.locations[0]
        parts.append(f"at {loc.name}")
        if loc.description:
            parts.append(loc.description)
    if bible.style_anchors:
        s = bible.style_anchors[0]
        if s.color_grade:
            parts.append(f"color grade: {s.color_grade}")
        if s.photographic_aesthetic:
            parts.append(s.photographic_aesthetic)
    return ". ".join(parts) + ". Cinematic, photorealistic, 24fps."


def _build_tts_line(shot: ShotSpec, bible: FilmBible) -> str:
    """Build a voiceover line for the shot (from the story beat)."""
    beat = next((b for b in bible.story_beats if b.order == shot.order), None)
    if beat:
        return f"Shot {shot.order}. {beat.description}"
    return shot.description


def _build_lyria_prompt(bible: FilmBible) -> str:
    """Build the Lyria score prompt from the Bible's score motifs + mood."""
    if bible.score_motifs:
        m = bible.score_motifs[0]
        return m.prompt
    mood = bible.style_anchors[0].mood if bible.style_anchors else "melancholic"
    return f"a slow {mood} instrumental score, cinematic, sparse"


async def _update_shot_status(project_id: str, shot_id: str, status: str) -> None:
    """Update a shot's status in the store."""
    # The store doesn't have a direct update_shot_status; we use save_shot with
    # the existing shot + new status. For now, log it (full shot update in Day 8).
    await store.log_event(project_id, "shot_status_changed", {
        "shotId": shot_id, "new_status": status,
    })
