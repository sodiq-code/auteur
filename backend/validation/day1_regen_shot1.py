#!/usr/bin/env python3
"""
Auteur — Day 1 shot-1 re-generation (face-visible framing).

The upgraded consistency model (gemini-3.1-pro-preview) correctly flagged that
shot 1's original framing had the character's face obscured behind the brass
Fresnel lens he was polishing — the older gemini-2.5-pro was lenient (0.75),
the newer model honestly scored it 0.30 because it could not confirm the face.

Re-generates shot 1 only with a framing where Ewan's face is visible (polishing
the lens from the side, three-quarter profile), then re-runs the consistency
check with gemini-3.1-pro-preview. Same scene, same story, visible face.
"""
from __future__ import annotations
import json, os, sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from day1_validate_consistency import (
    OUTPUT_DIR, DOCS_DIR, VISION_MODEL, IMAGE_LOCATION,
    get_client, get_vision_client,
    generate_veo_clip, extract_representative_frame,
    build_side_by_side, consistency_check, write_manifest_and_report, log,
)

SHOT_1_VISIBLE = {
    "id": "shot_1_lamp_room",
    "scene_label": "Lamp Room (interior, dusk) — face-visible",
    "prompt": (
        "Three-quarter profile medium shot of Ewan, the 52-year-old lighthouse "
        "keeper with a salt-and-pepper beard and dark oilskin coat, standing "
        "beside the great brass Fresnel lens in the lamp room of a 1892 "
        "lighthouse at dusk. His face is clearly visible, illuminated by warm "
        "golden lamplight as he carefully polishes the lens with a cloth. "
        "Glass and brass reflections, dust motes in the air. Cinematic, "
        "shallow depth of field, muted teal-and-amber color grade, "
        "photorealistic, 24fps."
    ),
}


def main() -> int:
    os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS",
                          "/home/z/my-project/auteur-sa-key.json")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    char_ref = OUTPUT_DIR / "character_reference.png"
    if not char_ref.exists():
        log("FATAL", f"character_reference.png not found at {char_ref}")
        return 2

    client = get_client()
    vision_client = get_vision_client()

    manifest_path = OUTPUT_DIR / "day1-manifest.json"
    manifest: dict[str, Any] = json.loads(manifest_path.read_text())
    log("MAIN", f"Re-generating shot 1 with face-visible framing (gemini-3.1-pro-preview flagged the lens-obscured face)...")

    res = generate_veo_clip(client, SHOT_1_VISIBLE, char_ref, 1)
    log("MAIN", f"shot 1 re-gen status: {res.get('status')} elapsed={res.get('elapsed_sec','-')}s")

    if res.get("status") == "ok":
        mp4 = Path(res["output_path"])
        png = OUTPUT_DIR / (mp4.stem + "_frame.png")
        ok = extract_representative_frame(mp4, png)
        res["frame_path"] = str(png) if ok else None

    shots = manifest.get("shots", [])
    if len(shots) >= 1:
        shots[0] = res
    manifest["shots"] = shots
    manifest["shot_1_regen_note"] = (
        "Shot 1 originally framed the character behind the brass Fresnel lens "
        "he was polishing. The upgraded consistency model (gemini-3.1-pro-preview) "
        "correctly flagged the obscured face (0.30, vs the older gemini-2.5-pro's "
        "lenient 0.75). Re-generated with a three-quarter profile medium shot "
        "where Ewan stands beside the lens, face clearly visible. Same scene, "
        "same story (polishing the lens at dusk). This is the validation loop "
        "working as designed (blueprint P862-P865)."
    )

    frames = []
    for r in shots:
        fp = r.get("frame_path")
        frames.append(Path(fp) if fp else OUTPUT_DIR / "missing.png")
    manifest["frames"] = [str(f) for f in frames]

    side_by_side = DOCS_DIR / "validation-day-1.png"
    build_side_by_side(char_ref, frames, side_by_side)
    manifest["side_by_side"] = str(side_by_side)

    vision = consistency_check(vision_client, char_ref, frames)
    manifest["consistency_check"] = vision
    manifest["vision_model"] = VISION_MODEL
    manifest["vision_model_note"] = (
        "Blueprint specifies Gemini 2.5 Pro (Table 31). Upgraded to "
        "gemini-3.1-pro-preview (newest accessible Pro model, text + vision, "
        "`global` region). Stricter than 2.5-pro — catches face-obscuring "
        "framings the older model glossed over."
    )
    verdict = vision.get("verdict", "UNKNOWN") if isinstance(vision, dict) else "UNKNOWN"
    manifest["verdict"] = verdict
    manifest["definition_of_done"] = {
        "docs_validation_day_1_png": str(side_by_side),
        "present": side_by_side.exists(),
    }

    write_manifest_and_report(manifest, side_by_side, vision)
    log("MAIN", f"VERDICT after shot-1 re-gen: {verdict}")
    log("MAIN", f"mean_overall: {vision.get('mean_overall') if isinstance(vision,dict) else '?'}")
    return 0 if verdict in ("GO", "PARTIAL") else 1


if __name__ == "__main__":
    sys.exit(main())
