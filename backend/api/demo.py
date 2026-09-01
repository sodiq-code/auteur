"""
Auteur — canonical demo endpoint (blueprint Section 32.2 Day 11, P872-P878).

GET /api/demo — returns the pre-rendered canonical 4-shot demo (the safety net
for demo day). The demo is the Day-1 validation: the lighthouse-keeper film
with 4 Veo 3.1 clips held consistent via the ASSET character reference.

This is the DEFAULT landing experience: visitors see the demo instantly without
needing to generate anything. The "Watch it live" CTA triggers a fresh Veo
generation to prove the loop is real (blueprint Section 28.1 demo-safe path).

DoD (blueprint P878): deployed URL loads canonical demo in under 5 seconds.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import FileResponse

from ..bible.schema import FilmBible

router = APIRouter(prefix="/demo", tags=["demo"])

# The canonical demo data (the Day-1 validation — lighthouse keeper Ewan)
CANONICAL_LOGLINE = "An 1892 Scottish lighthouse keeper discovers a message in a bottle that changes his life."

CANONICAL_BIBLE: dict[str, Any] = {
    "version": 1,
    "logline": CANONICAL_LOGLINE,
    "characters": [{
        "id": "char-ewan",
        "name": "Ewan MacAskill",
        "age": 52,
        "description": "A weathered, solitary Scottish lighthouse keeper whose life is dictated by the clockwork precision of the light.",
        "voice_profile": "Gruff, sparse, with a thick Scottish brogue.",
        "wardrobe": "Hand-waxed oilskin storm coat over a heavy-knit wool sweater.",
        "reference_image_url": "/auteur/demo/character-reference.png",
    }],
    "locations": [{
        "id": "loc-skerryvore",
        "name": "Skerryvore Lighthouse",
        "description": "A remote stone lighthouse battered by the North Sea, featuring a gleaming hyper-radial Fresnel lens.",
        "era": "1892",
    }],
    "style_anchors": [{
        "id": "s1",
        "color_grade": "Desaturated cold blues + warm amber lamp glow",
        "aspect_ratio": "16:9",
        "mood": "Atmospheric, isolating, hauntingly beautiful",
    }],
    "story_beats": [
        {"id": "b1", "order": 1, "description": "Ewan walks the lamp room at dusk, polishing the lens."},
        {"id": "b2", "order": 2, "description": "He discovers a bottle on the rocks below at dawn."},
        {"id": "b3", "order": 3, "description": "He reads the message by candlelight."},
        {"id": "b4", "order": 4, "description": "He looks out to sea, transformed."},
    ],
    "shots": [
        {"id": "shot-1", "order": 1, "label": "Lamp Room", "scene": "Interior, dusk · polishing the lens", "frame": "/auteur/demo/shot-1.png", "score": 0.95},
        {"id": "shot-2", "order": 2, "label": "Rocks", "scene": "Coastal, dawn · the bottle", "frame": "/auteur/demo/shot-2.png", "score": 0.85},
        {"id": "shot-3", "order": 3, "label": "Interior", "scene": "Candlelight · reading the message", "frame": "/auteur/demo/shot-3.png", "score": 0.95},
        {"id": "shot-4", "order": 4, "label": "Exterior", "scene": "Balcony · stormy sea, dusk", "frame": "/auteur/demo/shot-4.png", "score": 0.95},
    ],
    "consistency": {
        "mean_overall": 0.925,
        "threshold": 0.25,
        "verdict": "GO",
        "model": "gemini-3.1-pro-preview",
        "independent_vlm": 0.90,
    },
    "side_by_side": "/auteur/demo/side-by-side.png",
    "character_reference": "/auteur/demo/character-reference.png",
}


@router.get("")
async def get_demo() -> dict[str, Any]:
    """Return the canonical pre-rendered demo (blueprint Day 11, P873-P876).

    This is the DEFAULT landing experience — visitors see the demo instantly.
    The demo is pre-rendered (not generated on-demand) so it loads in < 1s.
    """
    return {
        "status": "ok",
        "logline": CANONICAL_LOGLINE,
        "bible": CANONICAL_BIBLE,
        "shots": CANONICAL_BIBLE["shots"],
        "consistency": CANONICAL_BIBLE["consistency"],
        "side_by_side": CANONICAL_BIBLE["side_by_side"],
        "character_reference": CANONICAL_BIBLE["character_reference"],
        "note": "Pre-rendered canonical demo — the Day-1 validation (lighthouse keeper Ewan). "
                "The 'Watch it live' CTA triggers a fresh Veo generation to prove the loop is real.",
    }
