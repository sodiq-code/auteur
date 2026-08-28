#!/usr/bin/env python3
"""
Auteur — Day 1 consistency-check re-run (newer Pro vision model).

Re-runs ONLY the Gemini-Vision consistency check on the existing character
reference + 4 shot frames, using the upgraded vision model
(gemini-3.1-pro-preview, global region). Does NOT regenerate any Veo clips
— the shots are already validated; only the scoring model changes.

Then updates the manifest + report with the new model + scores.
"""
from __future__ import annotations
import json, os, sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from day1_validate_consistency import (
    OUTPUT_DIR, DOCS_DIR, VISION_MODEL, IMAGE_LOCATION,
    get_vision_client, consistency_check, write_manifest_and_report, log,
)


def main() -> int:
    os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS",
                          "/home/z/my-project/auteur-sa-key.json")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    char_ref = OUTPUT_DIR / "character_reference.png"
    if not char_ref.exists():
        log("FATAL", f"character_reference.png not found at {char_ref}")
        return 2

    # Load existing manifest (keeps shot generation history intact)
    manifest_path = OUTPUT_DIR / "day1-manifest.json"
    manifest: dict[str, Any] = json.loads(manifest_path.read_text())
    log("MAIN", f"Re-running consistency check with {VISION_MODEL} (region={IMAGE_LOCATION})")
    log("MAIN", "(shots unchanged — only the scoring model is upgraded)")

    # Collect existing frame paths from the manifest
    frames = []
    for r in manifest.get("shots", []):
        fp = r.get("frame_path")
        frames.append(Path(fp) if fp else OUTPUT_DIR / "missing.png")

    vision_client = get_vision_client()
    vision = consistency_check(vision_client, char_ref, frames)
    manifest["consistency_check"] = vision
    manifest["vision_model"] = VISION_MODEL
    manifest["vision_model_note"] = (
        "Blueprint specifies Gemini 2.5 Pro (Table 31) for the Consistency Check "
        "Agent + Director Agent. gemini-2.5-pro works but is the older generation. "
        "gemini-3-pro-preview 404s on this project; gemini-3.1-pro-preview is the "
        "newest accessible Pro model (text + vision), available only in the `global` "
        "region. Used here for the consistency check; will also be the Director "
        "Agent's reasoning model (Day 6+)."
    )
    verdict = vision.get("verdict", "UNKNOWN") if isinstance(vision, dict) else "UNKNOWN"
    manifest["verdict"] = verdict

    side_by_side = Path(manifest.get("side_by_side", str(DOCS_DIR / "validation-day-1.png")))
    write_manifest_and_report(manifest, side_by_side, vision)
    log("MAIN", f"VERDICT ({VISION_MODEL}): {verdict}")
    log("MAIN", f"mean_overall: {vision.get('mean_overall') if isinstance(vision,dict) else '?'}")
    return 0 if verdict in ("GO", "PARTIAL") else 1


if __name__ == "__main__":
    sys.exit(main())
