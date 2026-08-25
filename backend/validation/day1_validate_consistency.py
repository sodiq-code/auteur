#!/usr/bin/env python3
"""
Auteur — Day 1 Validation (most important day)
================================================
Blueprint Section 32.2 / 50.2.

Objective: validate that Veo 3.1 can produce visibly consistent characters
across 4 shots in 4 scenes, given a character reference image.

Pipeline:
  1. Generate a character reference image.
     (Blueprint specifies Imagen 3. On project auteur-506523, Imagen 3 is
      deprecated AND the 3.x Gemini image models are only accessible in the
      `global` region (they 404 in us-central1). gemini-3-pro-image (Pro tier,
      3.x generation) is the newest accessible Google Cloud image model —
      used here via generate_content(response_modalities=["IMAGE"]).)
  2. Generate 4 Veo 3.1 Fast clips using the SAME character reference image
     (passed as an ASSET reference) + 4 different scene prompts:
       - Scene 1: lamp room (interior, dusk)
       - Scene 2: rocks (coastal, dawn)
       - Scene 3: interior (candlelight, reading)
       - Scene 4: exterior (balcony, stormy sea, dusk)
  3. Download the 4 MP4s.
  4. Extract a representative frame from each clip (ffmpeg @ 50% duration).
  5. Build a side-by-side composite image: character reference + 4 frames.
  6. Run a Gemini-Vision consistency check (drift score per shot + overall verdict).
  7. Emit a JSON manifest + a markdown report with the GO / PARTIAL / NO verdict.

Definition of done (blueprint P815): side-by-side comparison screenshot saved to
docs/validation-day-1.png.

Run:
    GOOGLE_APPLICATION_CREDENTIALS=/path/to/auteur-sa-key.json \
    GCP_PROJECT_ID=auteur-506523 \
    python3 day1_validate_consistency.py
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "auteur-506523")
LOCATION = os.environ.get("GCP_LOCATION", "us-central1")          # Veo + Gemini Pro (vision)
IMAGE_LOCATION = os.environ.get("GCP_IMAGE_LOCATION", "global")  # gemini-3-pro-image only in `global`
SA_KEY = os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS",
    "/home/z/my-project/auteur-sa-key.json",
)

# Blueprint model mapping (see worklog + docs/validation-day-1-report.md):
#   blueprint "Imagen 3"        -> gemini-3-pro-image  (Imagen 3 deprecated on project;
#                                  gemini-3-pro-image is the newest ACCESSIBLE Google
#                                  image model — Pro tier, 3.x generation. NOTE: the
#                                  3.x image models are ONLY accessible in the `global`
#                                  region; in us-central1 they 404. gemini-2.5-flash-image
#                                  was the first working model on Day 1 but is older;
#                                  upgraded to gemini-3-pro-image for higher quality.)
#                                  Iteration tier (storyboards, Day 7+): gemini-3.1-flash-image.
#   blueprint "Veo 3.1 Light"  -> NOT USABLE: veo-3.1-lite-generate-001 rejects
#                                  reference_images with FAILED_PRECONDITION
#                                  ("The request is not supported by this model").
#                                  Lite supports only plain text-to-video + I2V.
#                                  Cross-shot character consistency REQUIRES the
#                                  ASSET reference image feature, so we use:
#   blueprint "Veo 3.1" (Fast)  -> veo-3.1-fast-generate-001  (supports ASSET ref)
#   blueprint "Veo 3.1 Standard" -> veo-3.1-generate-001      (supports ASSET ref)
#   For Day 1 validation we use the FAST tier (cheaper than Standard, still supports
#   the ASSET character reference). Standard is reserved for final demo renders.
#   blueprint "Gemini 2.5 Pro"  -> gemini-3.1-pro-preview
#                                  (gemini-2.5-pro works but is older; gemini-3-pro-preview
#                                   404s on this project; gemini-3.1-pro-preview is the
#                                   newest accessible Pro model — text + vision both work
#                                   in the `global` region. Used for Director Agent
#                                   orchestration (Day 6+) + Consistency Check vision.)
IMAGE_MODEL = "gemini-3-pro-image"         # blueprint "Imagen 3" -> newest accessible (global region)
VEO_MODEL = "veo-3.1-fast-generate-001"    # blueprint "Veo 3.1" w/ ASSET ref (Lite lacks it)
VISION_MODEL = "gemini-3.1-pro-preview"    # blueprint "Gemini 2.5 Pro" -> newest accessible Pro (global)

# The canonical character: Ewan, the 1892 lighthouse keeper (blueprint Table 25).
CHARACTER_NAME = "Ewan"
CHARACTER_PROMPT = (
    "Cinematic portrait photograph of Ewan, a 52-year-old Scottish lighthouse "
    "keeper from 1892. Weathered, deeply lined face with a salt-and-pepper "
    "beard, tired but kind eyes. Wearing a heavy dark oilskin storm coat over "
    "a wool sweater. Dramatic single-source lamplight from the side, moody "
    "atmosphere, photorealistic, shallow depth of field, 50mm lens, "
    "muted teal-and-amber color grade. Looking just off camera."
)

# 4 scenes — each places the SAME character in a different environment.
# (blueprint Table 25 shot list, condensed to prompts.)
SCENES = [
    {
        "id": "shot_1_lamp_room",
        "scene_label": "Lamp Room (interior, dusk)",
        "prompt": (
            "Ewan, the 52-year-old lighthouse keeper with a salt-and-pepper "
            "beard and dark oilskin coat, walks slowly through the lamp room "
            "of a 1892 lighthouse at dusk. He polishes the great brass Fresnel "
            "lens. Warm golden lamplight, glass and brass reflections, dust "
            "motes in the air. Cinematic, slow tracking shot, muted teal-and-"
            "amber color grade, photorealistic, 24fps."
        ),
    },
    {
        "id": "shot_2_rocks",
        "scene_label": "Rocks (coastal, dawn)",
        "prompt": (
            "Ewan, the 52-year-old lighthouse keeper with a salt-and-pepper "
            "beard and dark oilskin coat, descends carefully over wet black "
            "rocks below the lighthouse at dawn. He discovers a glass bottle "
            "washed ashore and kneels to pick it up. Crashing waves, sea "
            "spray, overcast grey sky, North Sea coast. Cinematic wide shot, "
            "muted teal-and-amber color grade, photorealistic, 24fps."
        ),
    },
    {
        "id": "shot_3_interior",
        "scene_label": "Interior (candlelight, reading)",
        "prompt": (
            "Ewan, the 52-year-old lighthouse keeper with a salt-and-pepper "
            "beard, now wearing a thick knitted wool sweater, sits at a wooden "
            "table in his quarters reading a message by candlelight. Flickering "
            "amber light on his face, old maps and a lantern on the table, "
            "1892 interior. Close-up, shallow depth of field, muted teal-and-"
            "amber color grade, photorealistic, 24fps."
        ),
    },
    {
        "id": "shot_4_exterior",
        "scene_label": "Exterior (balcony, stormy sea, dusk)",
        "prompt": (
            "Ewan, the 52-year-old lighthouse keeper with a salt-and-pepper "
            "beard and dark oilskin coat, stands on the lighthouse balcony "
            "looking out over a stormy dark sea at dusk. His coat flaps in the "
            "wind, his expression is transformed and resolute. Lighthouse beam "
            "sweeping, dramatic sky. Cinematic medium shot, muted teal-and-"
            "amber color grade, photorealistic, 24fps."
        ),
    },
]

VEO_DURATION_SECONDS = 8          # Veo 3.1 Lite supports 6-8s clips
VEO_ASPECT_RATIO = "16:9"
VEO_RESOLUTION = "720p"          # Lite tier cap; keeps cost low
VEO_GENERATE_AUDIO = False       # focus on visual consistency for Day 1
VEO_POLL_INTERVAL_SEC = 12
VEO_MAX_WAIT_SEC = 600           # 10 min per clip cap

OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
DOCS_DIR = Path(__file__).resolve().parents[2] / "docs"  # auteur/docs


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def log(stage: str, msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] {stage} :: {msg}", flush=True)


def ensure_dirs() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)


def get_client(region: str | None = None):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = SA_KEY
    from google import genai  # imported lazily so --help works offline
    return genai.Client(vertexai=True, project=PROJECT_ID, location=region or LOCATION)


def get_image_client():
    """Image model (gemini-3-pro-image) is only accessible in the `global` region."""
    return get_client(region=IMAGE_LOCATION)


def get_vision_client():
    """Vision/Pro model (gemini-3.1-pro-preview) is only accessible in the `global` region."""
    return get_client(region=IMAGE_LOCATION)  # same `global` region as the image model


# --------------------------------------------------------------------------- #
# Step 1 — Character reference image (Imagen 3 -> gemini-3-pro-image)
# --------------------------------------------------------------------------- #

def generate_character_reference(image_client) -> Path:
    from google.genai import types

    out_path = OUTPUT_DIR / "character_reference.png"
    log("IMAGE", f"Generating character reference: {CHARACTER_NAME}")
    log("IMAGE", f"  prompt: {CHARACTER_PROMPT[:90]}...")
    log("IMAGE", f"  model : {IMAGE_MODEL} (region={IMAGE_LOCATION}; newest accessible Google image model)")

    t0 = time.time()
    resp = image_client.models.generate_content(
        model=IMAGE_MODEL,
        contents=CHARACTER_PROMPT,
        config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
    )
    elapsed = time.time() - t0

    image_bytes: bytes | None = None
    for cand in resp.candidates or []:
        for part in (cand.content.parts if cand.content else []):
            inline = getattr(part, "inline_data", None)
            if inline and inline.data:
                image_bytes = inline.data
                break
        if image_bytes:
            break

    if not image_bytes:
        raise RuntimeError("No image returned from image model")

    out_path.write_bytes(image_bytes)
    log("IMAGE", f"  -> saved {out_path.name} ({len(image_bytes):,} bytes, {elapsed:.1f}s)")
    return out_path


# --------------------------------------------------------------------------- #
# Step 2 — 4 Veo 3.1 Lite clips with the character as an ASSET reference
# --------------------------------------------------------------------------- #

def generate_veo_clip(client, scene: dict, char_ref_path: Path, idx: int) -> dict:
    from google.genai import types

    shot_id = scene["id"]
    out_path = OUTPUT_DIR / f"{shot_id}.mp4"
    log("VEO", f"[{idx}/4] {shot_id} — {scene['scene_label']}")
    log("VEO", f"  model : {VEO_MODEL} (blueprint 'Veo 3.1 Light')")
    log("VEO", f"  prompt: {scene['prompt'][:90]}...")

    # Load the character reference image as an ASSET reference.
    # ASSET = persistent subject reference; Veo 3.1 keeps the subject
    # consistent across different scene prompts (the cross-shot primitive).
    # NOTE: mime_type is REQUIRED — without it Veo rejects with
    # "image mime type is empty" (400 INVALID_ARGUMENT).
    ref_image = types.Image(
        image_bytes=char_ref_path.read_bytes(),
        mime_type="image/png",
    )
    reference_images = [
        types.VideoGenerationReferenceImage(
            image=ref_image,
            reference_type=types.VideoGenerationReferenceType.ASSET,
        )
    ]

    config = types.GenerateVideosConfig(
        number_of_videos=1,
        duration_seconds=VEO_DURATION_SECONDS,
        aspect_ratio=VEO_ASPECT_RATIO,
        resolution=VEO_RESOLUTION,
        generate_audio=VEO_GENERATE_AUDIO,
        reference_images=reference_images,
        person_generation="allow_adult",
        enhance_prompt=True,
    )

    t0 = time.time()
    try:
        # Use `source` (the non-deprecated path) per the SDK deprecation notice:
        #   "Please use the source argument instead of prompt/image/video."
        source = types.GenerateVideosSource(prompt=scene["prompt"])
        op = client.models.generate_videos(
            model=VEO_MODEL,
            source=source,
            config=config,
        )
    except Exception as e:
        log("VEO", f"  SUBMIT ERROR: {type(e).__name__}: {str(e)[:200]}")
        return {
            "shot_id": shot_id,
            "status": "submit_failed",
            "error": str(e)[:500],
            "elapsed_sec": round(time.time() - t0, 1),
        }

    log("VEO", f"  submitted. operation name: {op.name}")
    log("VEO", f"  polling (up to {VEO_MAX_WAIT_SEC}s, every {VEO_POLL_INTERVAL_SEC}s)...")

    # Poll the long-running operation
    wait_start = time.time()
    done_resp = op
    while True:
        elapsed_wait = time.time() - wait_start
        if elapsed_wait > VEO_MAX_WAIT_SEC:
            log("VEO", f"  TIMEOUT after {elapsed_wait:.0f}s")
            return {
                "shot_id": shot_id,
                "status": "timeout",
                "error": f"no completion in {VEO_MAX_WAIT_SEC}s",
                "operation_name": op.name,
                "elapsed_sec": round(time.time() - t0, 1),
            }
        # check the operation
        try:
            current = client.operations.get(operation=op)
        except Exception:
            current = op
        done = getattr(current, "done", False)
        err = getattr(current, "error", None)
        if err:
            log("VEO", f"  OPERATION ERROR: {err}")
            return {
                "shot_id": shot_id,
                "status": "operation_failed",
                "error": str(err)[:500],
                "operation_name": op.name,
                "elapsed_sec": round(time.time() - t0, 1),
            }
        if done:
            done_resp = current
            break
        time.sleep(VEO_POLL_INTERVAL_SEC)

    elapsed = time.time() - t0
    log("VEO", f"  done in {elapsed:.1f}s. Collecting result...")

    # Collect the generated video
    result = getattr(done_resp, "result", None) or getattr(done_resp, "response", None)
    videos = []
    if result is not None:
        generated = getattr(result, "generated_videos", None) or []
        for gv in generated:
            vid = getattr(gv, "video", None)
            if vid is not None:
                videos.append(vid)

    if not videos:
        # maybe result has generated_videos differently
        return {
            "shot_id": shot_id,
            "status": "no_video_returned",
            "operation_name": op.name,
            "elapsed_sec": round(elapsed, 1),
        }

    vid = videos[0]
    # Video may be inline or a GCS URI
    video_bytes: bytes | None = None
    gcs_uri: str | None = None
    inline_b = getattr(vid, "video_bytes", None)
    if inline_b:
        video_bytes = inline_b
    else:
        # try the underlying part
        gcs_uri = getattr(vid, "uri", None) or getattr(vid, "gcs_uri", None)

    if video_bytes:
        out_path.write_bytes(video_bytes)
        log("VEO", f"  -> saved {out_path.name} inline ({len(video_bytes):,} bytes)")
    elif gcs_uri:
        log("VEO", f"  -> video at GCS: {gcs_uri}; downloading...")
        video_bytes = download_gcs_object(gcs_uri)
        if video_bytes:
            out_path.write_bytes(video_bytes)
            log("VEO", f"  -> downloaded {out_path.name} ({len(video_bytes):,} bytes)")
        else:
            return {
                "shot_id": shot_id,
                "status": "gcs_download_failed",
                "gcs_uri": gcs_uri,
                "operation_name": op.name,
                "elapsed_sec": round(elapsed, 1),
            }
    else:
        return {
            "shot_id": shot_id,
            "status": "empty_video_payload",
            "operation_name": op.name,
            "elapsed_sec": round(elapsed, 1),
        }

    return {
        "shot_id": shot_id,
        "scene_label": scene["scene_label"],
        "status": "ok",
        "output_path": str(out_path),
        "duration_seconds": VEO_DURATION_SECONDS,
        "resolution": VEO_RESOLUTION,
        "aspect_ratio": VEO_ASPECT_RATIO,
        "model": VEO_MODEL,
        "operation_name": op.name,
        "elapsed_sec": round(elapsed, 1),
        "file_size_bytes": out_path.stat().st_size,
    }


def download_gcs_object(gcs_uri: str) -> bytes | None:
    """Download a gs://bucket/object via the storage REST API using SA token."""
    if not gcs_uri.startswith("gs://"):
        return None
    path = gcs_uri[len("gs://"):]
    bucket, _, obj = path.partition("/")
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request

    creds = service_account.Credentials.from_service_account_file(
        SA_KEY, scopes=["https://www.googleapis.com/auth/devstorage.read_only"]
    )
    creds.refresh(Request())
    url = f"https://storage.googleapis.com/storage/v1/b/{bucket}/o/{obj}?alt=media"
    import requests
    r = requests.get(url, headers={"Authorization": f"Bearer {creds.token}"}, timeout=120)
    if r.status_code == 200:
        return r.content
    log("GCS", f"  download failed {r.status_code}: {r.text[:200]}")
    return None


# --------------------------------------------------------------------------- #
# Step 3 — Extract a representative frame from each clip (ffmpeg @ 50%)
# --------------------------------------------------------------------------- #

def extract_representative_frame(mp4_path: Path, out_png: Path) -> bool:
    # probe duration
    probe = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(mp4_path),
        ],
        capture_output=True, text=True,
    )
    duration = float(probe.stdout.strip() or "0") if probe.returncode == 0 else 0.0
    ts = max(0.1, duration / 2.0) if duration > 0 else 2.0
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-ss", f"{ts:.2f}", "-i", str(mp4_path),
        "-frames:v", "1", "-q:v", "2", str(out_png),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0


# --------------------------------------------------------------------------- #
# Step 4 — Build side-by-side composite (char ref + 4 frames)
# --------------------------------------------------------------------------- #

def build_side_by_side(char_ref: Path, frames: list[Path], out_png: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    log("COMPOSITE", f"Building side-by-side -> {out_png}")
    images = [("CHARACTER REFERENCE\n(Ewan)", char_ref)]
    for i, f in enumerate(frames, 1):
        label = f"SHOT {i}\n{SCENES[i-1]['scene_label']}"
        images.append((label, f if f.exists() else None))

    # Uniform cell size
    CELL_W, CELL_H = 640, 380
    LABEL_H = 44
    GAP = 16
    cols = len(images)  # 5 across (char ref + 4 shots)
    pad = 28
    title_h = 64
    canvas_w = pad * 2 + cols * CELL_W + (cols - 1) * GAP
    canvas_h = pad * 2 + title_h + CELL_H + LABEL_H + 30

    canvas = Image.new("RGB", (canvas_w, canvas_h), (10, 12, 18))
    draw = ImageDraw.Draw(canvas)

    def font(sz, bold=False):
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        for p in candidates:
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, sz)
                except Exception:
                    pass
        return ImageFont.load_default()

    title_font = font(30, bold=True)
    label_font = font(15, bold=True)
    sub_font = font(12)

    draw.text(
        (pad, pad),
        "AUTEUR  ·  Day 1 Validation  ·  Cross-shot character consistency (Veo 3.1)",
        fill=(235, 238, 245), font=title_font,
    )
    draw.text(
        (pad, pad + 38),
        f"Character: Ewan (52, salt-and-pepper beard, oilskin coat)  ·  "
        f"Model: {VEO_MODEL}  ·  Reference type: ASSET  ·  "
        f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        fill=(150, 160, 180), font=sub_font,
    )

    x = pad
    y = pad + title_h
    for label, path in images:
        # cell background
        draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=(20, 24, 34))
        if path and path.exists():
            try:
                img = Image.open(path).convert("RGB")
                img.thumbnail((CELL_W, CELL_H))
                # center
                ox = x + (CELL_W - img.width) // 2
                oy = y + (CELL_H - img.height) // 2
                canvas.paste(img, (ox, oy))
            except Exception as e:
                draw.text((x + 10, y + 10), f"frame err: {e}", fill=(200, 120, 120), font=sub_font)
        else:
            draw.text((x + 10, y + CELL_H // 2), "frame unavailable", fill=(140, 140, 150), font=sub_font)
        # label
        ly = y + CELL_H + 6
        for j, line in enumerate(label.split("\n")):
            draw.text((x + 4, ly + j * 17), line, fill=(210, 215, 230), font=label_font)
        x += CELL_W + GAP

    # footer
    fy = y + CELL_H + LABEL_H + 12
    draw.text((pad, fy), "Verdict determined by Gemini 2.5 Pro vision consistency check (see validation-day-1-report.md)",
              fill=(130, 140, 160), font=sub_font)

    canvas.save(out_png, optimize=True)
    log("COMPOSITE", f"  -> saved {out_png} ({out_png.stat().st_size:,} bytes)")


# --------------------------------------------------------------------------- #
# Step 5 — Gemini-Vision consistency check (drift score per shot + verdict)
# --------------------------------------------------------------------------- #

def consistency_check(vision_client, char_ref_path: Path, frame_paths: list[Path]) -> dict:
    from google.genai import types
    log("VISION", f"Running consistency check via {VISION_MODEL} (region={IMAGE_LOCATION})...")

    # Build multimodal content: char ref + 4 frames, with a structured prompt
    parts = [
        types.Part.from_bytes(
            data=char_ref_path.read_bytes(), mime_type="image/png"
        ),
    ]
    for f in frame_paths:
        if f.exists():
            parts.append(types.Part.from_bytes(data=f.read_bytes(), mime_type="image/png"))

    instruction = (
        "You are Auteur's Consistency Check Agent (blueprint Section 22.3, Table 31). "
        "You are given ONE character reference image (Ewan, a 52-year-old lighthouse "
        "keeper with a salt-and-pepper beard and oilskin coat), followed by FOUR video "
        "frames. Each frame is a different scene generated by Veo 3.1 using the "
        "character reference as a persistent ASSET.\n\n"
        "For EACH of the 4 shots, score how well the character in that shot matches the "
        "reference, on these dimensions (0.0 = totally different, 1.0 = identical):\n"
        "  - face_identity (does it look like the same person?)\n"
        "  - age_appearance (is the apparent age consistent, ~52?)\n"
        "  - beard_facial_hair (salt-and-pepper beard present and consistent?)\n"
        "  - wardrobe (oilskin coat / wool sweater consistent?)\n"
        "  - overall (holistic character match)\n\n"
        "Then produce an overall verdict: GO (all 4 shots clearly the same character), "
        "PARTIAL (some shots consistent, some not), or NO (character does not hold "
        "across shots).\n\n"
        "Return STRICT JSON only, no prose, with this exact schema:\n"
        "{\n"
        '  "shots": [\n'
        '    {"shot": 1, "scene": "...", "face_identity": 0.0, "age_appearance": 0.0, '
        '"beard_facial_hair": 0.0, "wardrobe": 0.0, "overall": 0.0, "notes": "..."},\n'
        '    {"shot": 2, ...}, {"shot": 3, ...}, {"shot": 4, ...}\n'
        '  ],\n'
        '  "mean_overall": 0.0,\n'
        '  "verdict": "GO|PARTIAL|NO",\n'
        '  "verdict_rationale": "...",\n'
        '  "drift_threshold": 0.25\n'
        "}\n"
    )

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.2,
    )
    try:
        resp = vision_client.models.generate_content(
            model=VISION_MODEL,
            contents=[instruction] + parts,
            config=config,
        )
        text = resp.text or ""
        data = json.loads(text)
        log("VISION", f"  verdict={data.get('verdict')}  mean_overall={data.get('mean_overall')}")
        return data
    except Exception as e:
        log("VISION", f"  ERROR: {type(e).__name__}: {str(e)[:300]}")
        return {"error": str(e)[:500], "verdict": "UNKNOWN"}


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #

def main() -> int:
    ensure_dirs()
    if not Path(SA_KEY).exists():
        log("FATAL", f"SA key not found at {SA_KEY}")
        return 2
    log("MAIN", f"Project={PROJECT_ID}  Location={LOCATION}  Image location={IMAGE_LOCATION}")
    log("MAIN", f"Image model={IMAGE_MODEL}  Veo model={VEO_MODEL}  Vision model={VISION_MODEL}")

    client = get_client()                 # Veo — us-central1
    image_client = get_image_client()      # gemini-3-pro-image — global region
    vision_client = get_vision_client()    # gemini-3.1-pro-preview — global region

    manifest: dict[str, Any] = {
        "task": "Day 1 — Veo 3.1 cross-shot character consistency validation",
        "blueprint_ref": "Section 32.2 / 50.2",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "project_id": PROJECT_ID,
        "location": LOCATION,
        "image_location": IMAGE_LOCATION,
        "character": {
            "name": CHARACTER_NAME,
            "prompt": CHARACTER_PROMPT,
        },
        "image_model": IMAGE_MODEL,
        "image_model_note": (
            "Blueprint specifies Imagen 3 (Table 34). On project auteur-506523 "
            "Imagen 3 is deprecated. The 3.x Gemini image models are listed but "
            "ONLY accessible in the `global` region (they 404 in us-central1). "
            f"{IMAGE_MODEL} (Pro tier, 3.x generation) is the newest accessible "
            "Google Cloud image model — used here for the character reference. "
            "Iteration tier for storyboards (Day 7+): gemini-3.1-flash-image."
        ),
        "veo_model": VEO_MODEL,
        "veo_model_note": (
            "Blueprint 'Veo 3.1 Light' tier (veo-3.1-lite-generate-001) does NOT "
            "support reference_images (FAILED_PRECONDITION). The ASSET character "
            "reference requires the Fast or Standard tier; Fast used here, "
            "Standard reserved for final demo renders (Day 11)."
        ),
        "reference_type": "ASSET (persistent subject reference across scenes)",
        "scenes": SCENES,
        "veo_config": {
            "duration_seconds": VEO_DURATION_SECONDS,
            "aspect_ratio": VEO_ASPECT_RATIO,
            "resolution": VEO_RESOLUTION,
            "generate_audio": VEO_GENERATE_AUDIO,
        },
    }

    # Step 1 — character reference image
    try:
        char_ref_path = generate_character_reference(image_client)
        manifest["character_reference"] = {
            "path": str(char_ref_path),
            "status": "ok",
        }
    except Exception as e:
        log("MAIN", f"character reference FAILED: {e}")
        traceback.print_exc()
        manifest["character_reference"] = {"status": "failed", "error": str(e)[:500]}
        write_manifest_and_report(manifest, None, None)
        return 3

    # Step 2 — 4 Veo clips
    shot_results = []
    for i, scene in enumerate(SCENES, 1):
        res = generate_veo_clip(client, scene, char_ref_path, i)
        shot_results.append(res)
        manifest.setdefault("shots", []).append(res)

    # Step 3 — extract a representative frame from each successful clip
    frames = []
    for r in shot_results:
        if r.get("status") == "ok":
            mp4 = Path(r["output_path"])
            png = OUTPUT_DIR / (mp4.stem + "_frame.png")
            ok = extract_representative_frame(mp4, png)
            r["frame_path"] = str(png) if ok else None
            frames.append(png if ok else png)
        else:
            frames.append(OUTPUT_DIR / "missing.png")
    manifest["frames"] = [str(f) for f in frames]

    # Step 4 — side-by-side composite
    side_by_side = DOCS_DIR / "validation-day-1.png"
    try:
        build_side_by_side(char_ref_path, frames, side_by_side)
        manifest["side_by_side"] = str(side_by_side)
    except Exception as e:
        log("MAIN", f"side-by-side FAILED: {e}")
        manifest["side_by_side_error"] = str(e)[:300]

    # Step 5 — vision consistency check
    vision = consistency_check(vision_client, char_ref_path, frames)
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

    # verdict
    verdict = vision.get("verdict", "UNKNOWN") if isinstance(vision, dict) else "UNKNOWN"
    manifest["verdict"] = verdict
    manifest["definition_of_done"] = {
        "docs_validation_day_1_png": str(side_by_side),
        "present": side_by_side.exists(),
    }

    write_manifest_and_report(manifest, side_by_side, vision)

    log("MAIN", f"VERDICT: {verdict}")
    log("MAIN", f"Side-by-side: {side_by_side}")
    log("MAIN", f"Manifest:     {OUTPUT_DIR / 'day1-manifest.json'}")
    log("MAIN", f"Report:       {DOCS_DIR / 'validation-day-1-report.md'}")
    return 0 if verdict in ("GO", "PARTIAL") else 1


def write_manifest_and_report(manifest: dict, side_by_side, vision) -> None:
    (OUTPUT_DIR / "day1-manifest.json").write_text(json.dumps(manifest, indent=2))
    # markdown report
    verdict = manifest.get("verdict", "UNKNOWN")
    shots = manifest.get("shots", [])
    lines = []
    lines.append("# Auteur — Day 1 Validation Report\n")
    lines.append(f"**Blueprint:** Section 32.2 / 50.2  ")
    lines.append(f"**Date (UTC):** {manifest.get('timestamp_utc','')}  ")
    lines.append(f"**Project:** `{manifest.get('project_id')}` / `{manifest.get('location')}`\n")
    lines.append("## Objective\n")
    lines.append("Validate that Veo 3.1 can produce visibly consistent characters across "
                 "4 shots in 4 scenes, given a character reference image.\n")
    lines.append("## Models\n")
    lines.append(f"- **Character reference image:** `{manifest.get('image_model')}` "
                 f"(blueprint specifies Imagen 3; on this project Imagen 3 is deprecated "
                 f"and the 3.x Gemini image models are only accessible in the `global` "
                 f"region — `gemini-3-pro-image` is the newest accessible, Pro-tier, "
                 f"used here in region `{manifest.get('image_location','global')}`).\n")
    lines.append(f"- **Video generation:** `{manifest.get('veo_model')}` "
                 "(blueprint 'Veo 3.1 Light' tier).\n")
    lines.append(f"- **Reference mechanism:** `reference_images` with "
                 f"`reference_type=ASSET` — the Veo 3.1 persistent subject reference.\n")
    lines.append(f"- **Consistency check:** `{manifest.get('vision_model','gemini-3.1-pro-preview')}` "
                 f"(vision; blueprint Table 31 specifies Gemini 2.5 Pro — upgraded to the newest "
                 f"accessible Pro model, in region `{manifest.get('image_location','global')}`).\n")
    lines.append("## Shots\n")
    lines.append("| # | Scene | Status | Elapsed (s) | Size (bytes) |\n")
    lines.append("|---|-------|--------|-------------|--------------|\n")
    for i, r in enumerate(shots, 1):
        lines.append(f"| {i} | {r.get('scene_label','')} | {r.get('status')} | "
                     f"{r.get('elapsed_sec','-')} | {r.get('file_size_bytes','-')} |\n")
    lines.append("\n## Verdict\n")
    lines.append(f"**{verdict}**\n")
    if isinstance(vision, dict):
        lines.append(f"- Mean overall consistency: **{vision.get('mean_overall','-')}**\n")
        lines.append(f"- Drift threshold: {vision.get('drift_threshold',0.25)}\n")
        lines.append(f"- Rationale: {vision.get('verdict_rationale','')}\n")
        shts = vision.get("shots", [])
        if shts:
            lines.append("\n### Per-shot drift\n")
            lines.append("| Shot | Scene | face | age | beard | wardrobe | overall |\n")
            lines.append("|------|-------|------|-----|-------|----------|---------|\n")
            for s in shts:
                lines.append(f"| {s.get('shot')} | {s.get('scene','')} | "
                             f"{s.get('face_identity','-')} | {s.get('age_appearance','-')} | "
                             f"{s.get('beard_facial_hair','-')} | {s.get('wardrobe','-')} | "
                             f"{s.get('overall','-')} |\n")
    lines.append("\n## Artifacts\n")
    lines.append(f"- Side-by-side: `docs/validation-day-1.png`\n")
    lines.append(f"- Manifest: `backend/validation/outputs/day1-manifest.json`\n")
    lines.append(f"- Character reference: `backend/validation/outputs/character_reference.png`\n")
    lines.append(f"- Clips: `backend/validation/outputs/shot_*.mp4`\n")
    lines.append("\n## Decision (per blueprint P812-P814)\n")
    if verdict == "GO":
        lines.append("- Project is **GO**. Proceed to Day 2.\n")
    elif verdict == "PARTIAL":
        lines.append("- Project is **GO with caveat** — document which scenes work and "
                     "which don't; constrain demo to scenes that work.\n")
    else:
        lines.append("- Pivot required per Section 32.2 Day 1 fallback: scope to "
                     "within-single-scene consistency + voice/score consistency.\n")
    (DOCS_DIR / "validation-day-1-report.md").write_text("".join(lines))


if __name__ == "__main__":
    sys.exit(main())
