"""
Auteur — Veo 3.1 video generation client.

Model: veo-3.1-fast-generate-001 — the Lite tier does NOT
support reference_images, so the Fast tier is used for iteration; Standard for
final renders). us-central1 region.

The ASSET reference image is the cross-shot consistency primitive: the same
character reference image passed to multiple scene prompts keeps the subject
consistent (validated Day 1, verdict GO 0.925).
"""
from __future__ import annotations

import asyncio
import os
import time
from typing import Optional

from google import genai
from google.genai import types

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "auteur-506523")
VEO_REGION = "us-central1"
VEO_MODEL_FAST = "veo-3.1-fast-generate-001"     # iteration
VEO_MODEL_STANDARD = "veo-3.1-generate-001"       # final demo renders

_CLIENT = None


def _client():
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = genai.Client(vertexai=True, project=PROJECT_ID, location=VEO_REGION)
    return _CLIENT


async def generate_video(
    prompt: str,
    character_ref_png: Optional[bytes] = None,
    duration_seconds: int = 8,
    resolution: str = "720p",
    aspect_ratio: str = "16:9",
    generate_audio: bool = False,
    model: str = VEO_MODEL_FAST,
    poll_interval_sec: float = 12.0,
    max_wait_sec: float = 300.0,
) -> bytes:
    """Generate a Veo 3.1 clip. If character_ref_png is provided, it's passed as
    an ASSET reference (persistent subject across scenes — the cross-shot primitive).
    Returns the MP4 bytes.
    """
    cfg_kwargs: dict = {
        "number_of_videos": 1,
        "duration_seconds": duration_seconds,
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
        "generate_audio": generate_audio,
        "person_generation": "allow_adult",
        "enhance_prompt": True,
    }
    if character_ref_png:
        ref = types.Image(image_bytes=character_ref_png, mime_type="image/png")
        cfg_kwargs["reference_images"] = [
            types.VideoGenerationReferenceImage(
                image=ref,
                reference_type=types.VideoGenerationReferenceType.ASSET,
            )
        ]
    cfg = types.GenerateVideosConfig(**cfg_kwargs)
    source = types.GenerateVideosSource(prompt=prompt)

    op = await _client().aio.models.generate_videos(model=model, source=source, config=cfg)

    # poll the long-running operation
    t0 = time.time()
    while time.time() - t0 < max_wait_sec:
        cur = await _client().aio.operations.get(operation=op)
        if getattr(cur, "done", False):
            result = getattr(cur, "result", None) or getattr(cur, "response", None)
            gvs = getattr(result, "generated_videos", []) if result else []
            if not gvs:
                raise RuntimeError("Veo completed but no video returned")
            vid = gvs[0].video
            vb = getattr(vid, "video_bytes", None)
            if not vb:
                raise RuntimeError("Veo returned empty video payload")
            return vb
        if getattr(cur, "error", None):
            raise RuntimeError(f"Veo operation error: {cur.error}")
        await asyncio.sleep(poll_interval_sec)
    raise TimeoutError(f"Veo operation did not complete within {max_wait_sec}s")
