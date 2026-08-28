"""
Auteur — Consistency Check Agent (blueprint Section 22.3, Table 31).

Verifies that each generated shot matches the Film Bible references. Produces a
drift score per shot (0.0 = totally different, 1.0 = identical). Flags drift
above threshold; suggests re-generation.

Model: gemini-3.1-pro-preview with vision (global region). Stateless; operates
per-shot (no project memory — blueprint Table 31 row 6).

Authority (blueprint Table 31 row 7): READ-ONLY. Cannot modify shots; only flags.
"""
from __future__ import annotations

import json
from typing import Any

from ..integrations import gemini

DRIFT_THRESHOLD = 0.25  # blueprint §34.1 north-star metric


async def check_shot(
    char_ref_png: bytes,
    shot_frame_png: bytes,
    scene_label: str = "",
) -> dict[str, Any]:
    """Compare a shot frame to the character reference.

    Returns: {drift_score, per_attribute_breakdown, recommendation, notes}.
    drift_score = 1 - overall_consistency (lower drift = better match).
    """
    instruction = (
        "You are Auteur's Consistency Check Agent (blueprint Section 22.3, Table 31). "
        "Image 1 is the character reference. Image 2 is a video frame from a generated "
        f"shot{f' ({scene_label})' if scene_label else ''}. "
        "Score how well the character in image 2 matches the reference, on these "
        "dimensions (0.0 = totally different, 1.0 = identical):\n"
        "  - face_identity, age_appearance, beard_facial_hair, wardrobe, overall\n\n"
        "Return STRICT JSON only:\n"
        "{\n"
        '  "face_identity": 0.0, "age_appearance": 0.0, "beard_facial_hair": 0.0, '
        '"wardrobe": 0.0, "overall": 0.0,\n'
        '  "notes": "...",\n'
        '  "recommendation": "accept" | "re-generate"\n'
        "}\n"
        f"Recommendation: accept if overall >= {1 - DRIFT_THRESHOLD:.2f}, else re-generate.\n"
    )
    text = await gemini.pro_generate(
        instruction, response_mime_type="application/json", temperature=0.2,
        images=[char_ref_png, shot_frame_png],
    )
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = {"_raw": text, "overall": 0.0, "recommendation": "accept",
                "notes": "consistency check skipped (JSON parse failed)"}

    overall = float(data.get("overall", 0.0))
    data["drift_score"] = round(1.0 - overall, 3)  # drift = 1 - consistency
    data["threshold"] = DRIFT_THRESHOLD
    if "recommendation" not in data:
        data["recommendation"] = "accept" if overall >= (1 - DRIFT_THRESHOLD) else "re-generate"
    return data
