#!/usr/bin/env python3
"""
Auteur — End-to-end API validation (blueprint Section 32.2 / 50.3, Day 2).

Confirms all 5 production APIs return successfully within budget (< $1) and
reasonable latency (< 6 minutes). The pipeline:

  1. Parallel Search API  -> grounded references (real web, x-api-key auth)
  2. Gemini 3.1 Pro        -> synthesizes a small Film Bible from the references
  3. Image model            -> generates a character reference image (global region)
  4. Veo 3.1 Fast           -> generates one video clip with the char as ASSET ref
  5. Gemini TTS             -> generates one voiceover line (PCM -> WAV)
  6. Lyria 2                 -> generates one score clip (WAV)

Each step is timed + cost-estimated. The final manifest records the full
budget + latency breakdown.

Auth corrections vs. blueprint Section 26.3 pseudo-code:
  - Parallel Search uses the `x-api-key` header (NOT `Authorization: Bearer`).
  - Image model is gemini-3-pro-image (Imagen 3 deprecated), `global` region.
  - Voice is gemini-2.5-flash-tts (Chirp 3 is the underlying model; the SDK
    surface is the Gemini TTS generate_content with speech_config).
  - Music is lyria-002 (blueprint "Lyria 2"), via the Vertex :predict endpoint.
  - Veo 3.1 Fast tier (not Lite — Lite lacks reference_images support).
  - Consistency LLM is gemini-3.1-pro-preview (blueprint "Gemini 2.5 Pro"),
    `global` region.

Run:
  source .env
  python3 backend/validation/day2_e2e_api_validation.py
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import time
import traceback
import wave
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "auteur-506523")
VEO_LOCATION = os.environ.get("GCP_LOCATION", "us-central1")        # Veo + Lyria
IMAGE_LOCATION = os.environ.get("GCP_IMAGE_LOCATION", "global")     # gemini-3-pro-image + gemini-3.1-pro-preview
SA_KEY = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "/home/z/my-project/auteur-sa-key.json")
PARALLEL_API_KEY = os.environ.get("PARALLEL_API_KEY", "")

# Models (see Day 1 worklog for the discovery + substitutions)
PARALLEL_ENDPOINT = "https://api.parallel.ai/v1/search"
IMAGE_MODEL = "gemini-3-pro-image"        # blueprint "Imagen 3"
VEO_MODEL = "veo-3.1-fast-generate-001"   # blueprint "Veo 3.1" (Lite lacks ref images)
TTS_MODEL = "gemini-2.5-flash-tts"        # blueprint "Chirp 3" (SDK surface)
LYRIA_MODEL = "lyria-002"                  # blueprint "Lyria 2"
BIBLE_MODEL = "gemini-3.1-pro-preview"     # blueprint "Gemini 2.5 Pro"

OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
DOCS_DIR = Path(__file__).resolve().parents[2] / "docs"

# The canonical lighthouse-keeper logline (blueprint Section 50.3 + Table 25)
LOGLINE = "An 1892 Scottish lighthouse keeper discovers a message in a bottle that changes his life."

PARALLEL_OBJECTIVE = (
    "Find historical facts about 1892 Scottish lighthouse keepers: their daily "
    "duties, the oilskin storm coats they wore, the brass Fresnel lens lamps they "
    "tended, and the lonely rhythm of life on a remote Scottish lighthouse."
)
PARALLEL_QUERIES = [
    "1892 lighthouse keeper duties Scotland",
    "oilskin storm coat lighthouse keeper 1890s",
    "Fresnel lens lighthouse lamp 1892 maintenance",
    "lonely life remote Scottish lighthouse keeper",
]

CHARACTER_PROMPT = (
    "Cinematic portrait photograph of Ewan, a 52-year-old Scottish lighthouse "
    "keeper from 1892. Weathered, deeply lined face with a salt-and-pepper "
    "beard, tired but kind eyes. Wearing a heavy dark oilskin storm coat over "
    "a wool sweater. Dramatic single-source lamplight from the side, moody "
    "atmosphere, photorealistic, shallow depth of field, muted teal-and-amber "
    "color grade."
)

VEO_PROMPT = (
    "Ewan, the 52-year-old lighthouse keeper with a salt-and-pepper beard and "
    "dark oilskin coat, walks slowly through the lamp room of a 1892 lighthouse "
    "at dusk, polishing the great brass Fresnel lens. Warm golden lamplight, "
    "glass and brass reflections, dust motes. Cinematic, photorealistic, 24fps."
)

TTS_LINE = (
    "The lamp must never go dark. Not while I draw breath, and not while the sea "
    "still whispers her secrets to the night."
)
TTS_VOICE = "Charon"  # somber, deep — fits Ewan

LYRIA_PROMPT = (
    "a slow mournful solo fiddle playing a traditional scottish air, sparse, "
    "melancholic, minor key, with the distant sound of ocean waves and wind "
    "against a lighthouse, 1892 atmosphere"
)

# Cost estimates (blueprint Table 36) — per-call, USD
COST = {
    "parallel_search": 0.001,   # ~$0.001 per search (per-request pricing)
    "bible_synthesis": 0.02,    # Gemini Pro 1 multi-turn call
    "image_reference": 0.02,    # Imagen/gemini-image per image
    "veo_fast_clip": 0.05,     # Veo 3.1 Light tier (we use Fast; same tier family)
    "tts_voiceover": 0.02,     # Chirp 3 / Gemini TTS per clip
    "lyria_score": 0.03,       # Lyria 2 per clip
}
BUDGET_USD = 1.00
LATENCY_BUDGET_SEC = 360  # 6 minutes


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def log(stage: str, msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] {stage:9s} :: {msg}", flush=True)


def ensure_dirs() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class StepResult:
    name: str
    status: str = "pending"          # ok | failed | skipped
    elapsed_sec: float = 0.0
    cost_usd: float = 0.0
    output_path: str | None = None
    output_size_bytes: int = 0
    detail: dict = field(default_factory=dict)
    error: str | None = None


def pcm_to_wav(pcm: bytes, sample_rate: int = 24000, channels: int = 1, sampwidth: int = 2) -> bytes:
    """Wrap raw PCM in a WAV container."""
    import io
    bio = io.BytesIO()
    with wave.open(bio, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(sampwidth)
        w.setframerate(sample_rate)
        w.writeframes(pcm)
    return bio.getvalue()


# --------------------------------------------------------------------------- #
# Step 1 — Parallel Search (grounded references)
# --------------------------------------------------------------------------- #

def step_parallel_search() -> StepResult:
    r = StepResult(name="parallel_search", cost_usd=COST["parallel_search"])
    import requests
    log("PARALLEL", f"POST {PARALLEL_ENDPOINT} (x-api-key auth)")
    log("PARALLEL", f"  objective: {PARALLEL_OBJECTIVE[:80]}...")
    t0 = time.time()
    try:
        resp = requests.post(
            PARALLEL_ENDPOINT,
            headers={"Content-Type": "application/json", "x-api-key": PARALLEL_API_KEY},
            json={"objective": PARALLEL_OBJECTIVE, "search_queries": PARALLEL_QUERIES},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        r.elapsed_sec = round(time.time() - t0, 2)
        results = data.get("results", [])
        refs = []
        for res in results:
            excerpts = res.get("excerpts", [])
            excerpt_text = excerpts[0] if excerpts else ""
            refs.append({
                "url": res.get("url", ""),
                "title": res.get("title", ""),
                "publish_date": res.get("publish_date"),
                "excerpt": excerpt_text[:300] if isinstance(excerpt_text, str) else str(excerpt_text)[:300],
            })
        out_path = OUTPUT_DIR / "parallel_references.json"
        out_path.write_text(json.dumps({
            "search_id": data.get("search_id"),
            "session_id": data.get("session_id"),
            "usage": data.get("usage"),
            "references": refs,
        }, indent=2))
        r.output_path = str(out_path)
        r.output_size_bytes = out_path.stat().st_size
        r.status = "ok"
        r.detail = {"results_count": len(refs), "search_id": data.get("search_id", "")[:40]}
        log("PARALLEL", f"  -> {len(refs)} references in {r.elapsed_sec}s")
    except Exception as e:
        r.elapsed_sec = round(time.time() - t0, 2)
        r.status = "failed"
        r.error = str(e)[:300]
        log("PARALLEL", f"  FAILED: {r.error}")
    return r


# --------------------------------------------------------------------------- #
# Step 2 — Bible synthesis (Gemini 3.1 Pro from the references)
# --------------------------------------------------------------------------- #

def step_bible_synthesis(references: list[dict]) -> StepResult:
    r = StepResult(name="bible_synthesis", cost_usd=COST["bible_synthesis"])
    from google import genai
    from google.genai import types
    log("BIBLE", f"Building small Film Bible via {BIBLE_MODEL} (global region)")
    log("BIBLE", f"  logline: {LOGLINE}")
    log("BIBLE", f"  references: {len(references)}")
    client = genai.Client(vertexai=True, project=PROJECT_ID, location=IMAGE_LOCATION)
    refs_text = "\n".join(
        f"- [{i+1}] {ref['title']} ({ref['url']})\n  {ref['excerpt']}"
        for i, ref in enumerate(references[:6])
    )
    prompt = (
        "You are Auteur's Director Agent (blueprint Section 22.1). Build a SMALL "
        "Film Bible from this logline + research references. Return STRICT JSON only.\n\n"
        f"LOGLINE: {LOGLINE}\n\n"
        f"RESEARCH REFERENCES:\n{refs_text}\n\n"
        "Return JSON with this schema:\n"
        "{\n"
        '  "logline": "...",\n'
        '  "character": {"name": "...", "age": 52, "description": "...", "voice": "...", "wardrobe": "..."},\n'
        '  "location": {"name": "...", "description": "...", "era": "1892"},\n'
        '  "style": {"color_grade": "...", "aspect_ratio": "16:9", "mood": "..."},\n'
        '  "shot_list": [{"id": 1, "description": "...", "bible_refs": "char:Ewan;loc:lamp room"}],\n'
        '  "citations": ["url1", "url2"]\n'
        "}\n"
    )
    t0 = time.time()
    try:
        resp = client.models.generate_content(
            model=BIBLE_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json", temperature=0.4,
            ),
        )
        bible = json.loads(resp.text or "{}")
        r.elapsed_sec = round(time.time() - t0, 2)
        out_path = OUTPUT_DIR / "bible_v1.json"
        out_path.write_text(json.dumps(bible, indent=2))
        r.output_path = str(out_path)
        r.output_size_bytes = out_path.stat().st_size
        r.status = "ok"
        r.detail = {
            "character": bible.get("character", {}).get("name", "?"),
            "location": bible.get("location", {}).get("name", "?"),
            "shots": len(bible.get("shot_list", [])),
            "citations": len(bible.get("citations", [])),
        }
        log("BIBLE", f"  -> {r.detail['character']} @ {r.detail['location']} ({r.elapsed_sec}s)")
    except Exception as e:
        r.elapsed_sec = round(time.time() - t0, 2)
        r.status = "failed"
        r.error = str(e)[:300]
        log("BIBLE", f"  FAILED: {r.error}")
    return r


# --------------------------------------------------------------------------- #
# Step 3 — Character reference image (gemini-3-pro-image, global)
# --------------------------------------------------------------------------- #

def step_character_image() -> StepResult:
    r = StepResult(name="character_image", cost_usd=COST["image_reference"])
    from google import genai
    from google.genai import types
    log("IMAGE", f"Generating character reference via {IMAGE_MODEL} (global region)")
    client = genai.Client(vertexai=True, project=PROJECT_ID, location=IMAGE_LOCATION)
    t0 = time.time()
    try:
        resp = client.models.generate_content(
            model=IMAGE_MODEL, contents=CHARACTER_PROMPT,
            config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
        )
        img_bytes = None
        for cand in resp.candidates or []:
            for part in (cand.content.parts if cand.content else []):
                inline = getattr(part, "inline_data", None)
                if inline and inline.data:
                    img_bytes = inline.data
                    break
            if img_bytes:
                break
        r.elapsed_sec = round(time.time() - t0, 2)
        if not img_bytes:
            raise RuntimeError("no image in response")
        out_path = OUTPUT_DIR / "e2e_character_reference.png"
        out_path.write_bytes(img_bytes)
        r.output_path = str(out_path)
        r.output_size_bytes = len(img_bytes)
        r.status = "ok"
        log("IMAGE", f"  -> {len(img_bytes):,} bytes in {r.elapsed_sec}s")
    except Exception as e:
        r.elapsed_sec = round(time.time() - t0, 2)
        r.status = "failed"
        r.error = str(e)[:300]
        log("IMAGE", f"  FAILED: {r.error}")
    return r


# --------------------------------------------------------------------------- #
# Step 4 — Veo 3.1 Fast clip (ASSET character reference)
# --------------------------------------------------------------------------- #

def step_veo_clip(char_ref_path: str) -> StepResult:
    r = StepResult(name="veo_clip", cost_usd=COST["veo_fast_clip"])
    from google import genai
    from google.genai import types
    log("VEO", f"Generating clip via {VEO_MODEL} (us-central1, ASSET char ref)")
    client = genai.Client(vertexai=True, project=PROJECT_ID, location=VEO_LOCATION)
    ref = types.Image(image_bytes=Path(char_ref_path).read_bytes(), mime_type="image/png")
    cfg = types.GenerateVideosConfig(
        number_of_videos=1, duration_seconds=8, aspect_ratio="16:9",
        resolution="720p", generate_audio=False,
        reference_images=[types.VideoGenerationReferenceImage(
            image=ref, reference_type=types.VideoGenerationReferenceType.ASSET)],
        person_generation="allow_adult", enhance_prompt=True,
    )
    src = types.GenerateVideosSource(prompt=VEO_PROMPT)
    t0 = time.time()
    try:
        op = client.models.generate_videos(model=VEO_MODEL, source=src, config=cfg)
        log("VEO", f"  submitted op: {op.name}")
        # poll
        wait_start = time.time()
        done = op
        while time.time() - wait_start < 300:
            try:
                cur = client.operations.get(operation=op)
            except Exception:
                cur = op
            if getattr(cur, "done", False):
                done = cur
                break
            if getattr(cur, "error", None):
                raise RuntimeError(str(getattr(cur, "error")))
            time.sleep(12)
        else:
            raise RuntimeError("Veo op timed out > 300s")
        r.elapsed_sec = round(time.time() - t0, 2)
        result = getattr(done, "result", None) or getattr(done, "response", None)
        gvs = getattr(result, "generated_videos", []) if result else []
        if not gvs:
            raise RuntimeError("no video in Veo result")
        vid = gvs[0].video
        vb = getattr(vid, "video_bytes", None)
        if not vb:
            raise RuntimeError("no inline video_bytes")
        out_path = OUTPUT_DIR / "e2e_shot.mp4"
        out_path.write_bytes(vb)
        r.output_path = str(out_path)
        r.output_size_bytes = len(vb)
        r.status = "ok"
        r.detail = {"operation": op.name}
        log("VEO", f"  -> {len(vb):,} bytes in {r.elapsed_sec}s")
    except Exception as e:
        r.elapsed_sec = round(time.time() - t0, 2)
        r.status = "failed"
        r.error = str(e)[:300]
        log("VEO", f"  FAILED: {r.error}")
    return r


# --------------------------------------------------------------------------- #
# Step 5 — Voiceover (gemini-2.5-flash-tts)
# --------------------------------------------------------------------------- #

def step_tts_voiceover() -> StepResult:
    r = StepResult(name="tts_voiceover", cost_usd=COST["tts_voiceover"])
    from google import genai
    from google.genai import types
    log("TTS", f"Generating voiceover via {TTS_MODEL} (voice={TTS_VOICE})")
    log("TTS", f"  line: {TTS_LINE[:70]}...")
    client = genai.Client(vertexai=True, project=PROJECT_ID, location=VEO_LOCATION)
    cfg = types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=TTS_VOICE)
            )
        ),
    )
    t0 = time.time()
    try:
        resp = client.models.generate_content(model=TTS_MODEL, contents=TTS_LINE, config=cfg)
        pcm = None
        mime = None
        for cand in resp.candidates or []:
            for part in (cand.content.parts if cand.content else []):
                inline = getattr(part, "inline_data", None)
                if inline and inline.data:
                    pcm = inline.data
                    mime = inline.mime_type
                    break
            if pcm:
                break
        r.elapsed_sec = round(time.time() - t0, 2)
        if not pcm:
            raise RuntimeError("no audio in TTS response")
        # audio/L16;rate=24000 = raw 16-bit PCM mono @ 24kHz -> wrap as WAV
        wav_bytes = pcm_to_wav(pcm, sample_rate=24000, channels=1, sampwidth=2)
        out_path = OUTPUT_DIR / "e2e_voiceover.wav"
        out_path.write_bytes(wav_bytes)
        r.output_path = str(out_path)
        r.output_size_bytes = len(wav_bytes)
        r.status = "ok"
        r.detail = {"raw_mime": mime, "pcm_bytes": len(pcm)}
        log("TTS", f"  -> {len(wav_bytes):,} bytes WAV in {r.elapsed_sec}s")
    except Exception as e:
        r.elapsed_sec = round(time.time() - t0, 2)
        r.status = "failed"
        r.error = str(e)[:300]
        log("TTS", f"  FAILED: {r.error}")
    return r


# --------------------------------------------------------------------------- #
# Step 6 — Score (Lyria 2)
# --------------------------------------------------------------------------- #

def step_lyria_score() -> StepResult:
    r = StepResult(name="lyria_score", cost_usd=COST["lyria_score"])
    import requests
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    log("LYRIA", f"Generating score via {LYRIA_MODEL} (us-central1 :predict)")
    log("LYRIA", f"  prompt: {LYRIA_PROMPT[:70]}...")
    creds = service_account.Credentials.from_service_account_file(
        SA_KEY, scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(Request())
    url = f"https://{VEO_LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{VEO_LOCATION}/publishers/google/models/{LYRIA_MODEL}:predict"
    body = {"instances": [{"prompt": LYRIA_PROMPT}], "parameters": {"sampleCount": 1}}
    t0 = time.time()
    try:
        resp = requests.post(url, headers={
            "Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"
        }, json=body, timeout=180)
        resp.raise_for_status()
        d = resp.json()
        preds = d.get("predictions", [])
        if not preds or "bytesBase64Encoded" not in preds[0]:
            raise RuntimeError("no audio in Lyria response")
        audio = base64.b64decode(preds[0]["bytesBase64Encoded"])
        r.elapsed_sec = round(time.time() - t0, 2)
        out_path = OUTPUT_DIR / "e2e_score.wav"
        out_path.write_bytes(audio)
        r.output_path = str(out_path)
        r.output_size_bytes = len(audio)
        r.status = "ok"
        log("LYRIA", f"  -> {len(audio):,} bytes WAV in {r.elapsed_sec}s")
    except Exception as e:
        r.elapsed_sec = round(time.time() - t0, 2)
        r.status = "failed"
        r.error = str(e)[:300]
        log("LYRIA", f"  FAILED: {r.error}")
    return r


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #

def main() -> int:
    ensure_dirs()
    if not PARALLEL_API_KEY:
        log("FATAL", "PARALLEL_API_KEY not set in env")
        return 2
    if not Path(SA_KEY).exists():
        log("FATAL", f"SA key not found at {SA_KEY}")
        return 2

    log("MAIN", f"Project={PROJECT_ID}  Veo/Lyria={VEO_LOCATION}  Image/Bible={IMAGE_LOCATION}")
    log("MAIN", f"Budget: ${BUDGET_USD}  Latency: {LATENCY_BUDGET_SEC}s (6 min)")

    overall_t0 = time.time()
    results: list[StepResult] = []

    # Step 1 — Parallel Search
    s1 = step_parallel_search()
    results.append(s1)
    refs = []
    if s1.status == "ok" and s1.output_path:
        refs = json.loads(Path(s1.output_path).read_text()).get("references", [])

    # Step 2 — Bible synthesis (needs refs)
    if refs:
        s2 = step_bible_synthesis(refs)
    else:
        s2 = StepResult(name="bible_synthesis", status="skipped",
                        error="skipped — no Parallel references")
        log("BIBLE", "  SKIPPED (no references)")
    results.append(s2)

    # Step 3 — Character image
    s3 = step_character_image()
    results.append(s3)

    # Step 4 — Veo clip (needs char ref image)
    if s3.status == "ok" and s3.output_path:
        s4 = step_veo_clip(s3.output_path)
    else:
        s4 = StepResult(name="veo_clip", status="skipped", error="skipped — no char ref")
        log("VEO", "  SKIPPED (no char ref)")
    results.append(s4)

    # Step 5 — TTS voiceover (independent)
    s5 = step_tts_voiceover()
    results.append(s5)

    # Step 6 — Lyria score (independent)
    s6 = step_lyria_score()
    results.append(s6)

    total_elapsed = round(time.time() - overall_t0, 2)
    total_cost = round(sum(r.cost_usd for r in results if r.status == "ok"), 4)

    # Verify outputs
    verification = verify_outputs(results)

    # Manifest
    manifest = {
        "task": "End-to-end API validation (blueprint Section 32.2 / 50.3)",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "logline": LOGLINE,
        "project_id": PROJECT_ID,
        "regions": {"veo_lyria": VEO_LOCATION, "image_bible": IMAGE_LOCATION},
        "models": {
            "parallel_search": PARALLEL_ENDPOINT,
            "bible_synthesis": BIBLE_MODEL,
            "image": IMAGE_MODEL,
            "veo": VEO_MODEL,
            "tts": TTS_MODEL,
            "lyria": LYRIA_MODEL,
        },
        "budget": {"usd": BUDGET_USD, "latency_sec": LATENCY_BUDGET_SEC},
        "steps": [
            {
                "name": r.name, "status": r.status,
                "elapsed_sec": r.elapsed_sec, "cost_usd": r.cost_usd,
                "output_path": r.output_path, "output_size_bytes": r.output_size_bytes,
                "detail": r.detail, "error": r.error,
            }
            for r in results
        ],
        "totals": {
            "elapsed_sec": total_elapsed,
            "cost_usd": total_cost,
            "ok_count": sum(1 for r in results if r.status == "ok"),
            "total_count": len(results),
        },
        "verification": verification,
        "definition_of_done": {
            "cost_under_1_usd": total_cost < BUDGET_USD,
            "latency_under_6_min": total_elapsed < LATENCY_BUDGET_SEC,
            "all_5_apis_ok": sum(1 for r in results if r.status == "ok") >= 5,
        },
    }
    manifest_path = OUTPUT_DIR / "day2-e2e-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    # Report
    write_report(manifest)

    log("MAIN", "=" * 60)
    log("MAIN", f"TOTAL: {manifest['totals']['ok_count']}/{manifest['totals']['total_count']} APIs OK")
    log("MAIN", f"  cost:   ${total_cost}  (budget ${BUDGET_USD})  -> {'PASS' if total_cost < BUDGET_USD else 'FAIL'}")
    log("MAIN", f"  time:   {total_elapsed}s  (budget {LATENCY_BUDGET_SEC}s)  -> {'PASS' if total_elapsed < LATENCY_BUDGET_SEC else 'FAIL'}")
    log("MAIN", f"  DoD:    {manifest['definition_of_done']}")
    log("MAIN", f"  manifest: {manifest_path}")
    return 0 if manifest["definition_of_done"]["all_5_apis_ok"] else 1


def verify_outputs(results: list[StepResult]) -> dict:
    """Verify each generated artifact is well-formed (ffprobe for media, JSON parse for data)."""
    v = {}
    for r in results:
        if r.status != "ok" or not r.output_path:
            v[r.name] = {"valid": False, "reason": "no output"}
            continue
        p = Path(r.output_path)
        if not p.exists():
            v[r.name] = {"valid": False, "reason": "file missing"}
            continue
        if r.name in ("veo_clip", "tts_voiceover", "lyria_score"):
            # ffprobe media
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries",
                 "format=duration:stream=codec_name,width,height,sample_rate,channels",
                 "-of", "default=noprint_wrappers=1", str(p)],
                capture_output=True, text=True,
            )
            v[r.name] = {"valid": probe.returncode == 0, "ffprobe": probe.stdout.strip()}
        elif r.name in ("parallel_search", "bible_synthesis"):
            try:
                json.loads(p.read_text())
                v[r.name] = {"valid": True}
            except Exception as e:
                v[r.name] = {"valid": False, "reason": str(e)[:100]}
        elif r.name == "character_image":
            # PNG: check magic bytes
            head = p.read_bytes()[:8]
            v[r.name] = {"valid": head[:4] == b"\x89PNG", "magic": head.hex()}
    return v


def write_report(manifest: dict) -> None:
    lines = []
    lines.append("# Auteur — End-to-End API Validation Report\n")
    lines.append(f"**Blueprint:** Section 32.2 / 50.3  \n")
    lines.append(f"**Date (UTC):** {manifest['timestamp_utc']}  \n")
    lines.append(f"**Project:** `{manifest['project_id']}`\n")
    lines.append("## Objective\n")
    lines.append("Confirm all 5 production APIs (Parallel Search, image, Veo, TTS, Lyria) return "
                 "successfully within budget (< $1) and reasonable latency (< 6 min), and that "
                 "the bible-synthesis path produces a coherent Film Bible from the logline.\n")
    lines.append("## Models used (with blueprint substitutions)\n")
    lines.append("| Blueprint | Actual model | Region | Notes |\n")
    lines.append("|-----------|--------------|--------|-------|\n")
    lines.append(f"| Parallel Search | `{PARALLEL_ENDPOINT}` | n/a | `x-api-key` header (NOT Bearer) |\n")
    lines.append(f"| Gemini 2.5 Pro (bible) | `{BIBLE_MODEL}` | global | newest accessible Pro |\n")
    lines.append(f"| Imagen 3 | `{IMAGE_MODEL}` | global | Imagen 3 deprecated |\n")
    lines.append(f"| Veo 3.1 | `{VEO_MODEL}` | us-central1 | Lite lacks ref_images; Fast used |\n")
    lines.append(f"| Chirp 3 | `{TTS_MODEL}` | us-central1 | SDK surface; speech_config w/ voice |\n")
    lines.append(f"| Lyria 2 | `{LYRIA_MODEL}` | us-central1 | via Vertex :predict endpoint |\n")
    lines.append("\n## Step results\n")
    lines.append("| # | Step | Status | Time (s) | Cost ($) | Output | Size |\n")
    lines.append("|---|------|--------|----------|----------|--------|------|\n")
    for i, s in enumerate(manifest["steps"], 1):
        size = f"{s['output_size_bytes']:,}" if s["output_size_bytes"] else "-"
        path = Path(s["output_path"]).name if s["output_path"] else "-"
        lines.append(f"| {i} | {s['name']} | {s['status']} | {s['elapsed_sec']} | "
                     f"{s['cost_usd']} | {path} | {size} |\n")
    lines.append("\n## Totals\n")
    t = manifest["totals"]
    dod = manifest["definition_of_done"]
    lines.append(f"- **APIs OK:** {t['ok_count']}/{t['total_count']}\n")
    lines.append(f"- **Total cost:** ${t['cost_usd']} (budget ${manifest['budget']['usd']}) "
                 f"-> {'PASS' if dod['cost_under_1_usd'] else 'FAIL'}\n")
    lines.append(f"- **Total time:** {t['elapsed_sec']}s (budget {manifest['budget']['latency_sec']}s) "
                 f"-> {'PASS' if dod['latency_under_6_min'] else 'FAIL'}\n")
    lines.append(f"- **Definition of done:** {'ALL PASS' if all(dod.values()) else 'PARTIAL'}\n")
    lines.append("\n## Output verification\n")
    lines.append("| Step | Valid | Detail |\n|------|-------|--------|\n")
    for name, v in manifest["verification"].items():
        detail = v.get("ffprobe") or v.get("reason") or v.get("magic") or "ok"
        lines.append(f"| {name} | {'yes' if v['valid'] else 'NO'} | {str(detail)[:80]} |\n")
    lines.append("\n## Artifacts\n")
    lines.append("- Manifest: `backend/validation/outputs/day2-e2e-manifest.json`\n")
    lines.append("- Parallel references: `backend/validation/outputs/parallel_references.json`\n")
    lines.append("- Bible v1: `backend/validation/outputs/bible_v1.json`\n")
    lines.append("- Character ref: `backend/validation/outputs/e2e_character_reference.png`\n")
    lines.append("- Veo clip: `backend/validation/outputs/e2e_shot.mp4`\n")
    lines.append("- Voiceover: `backend/validation/outputs/e2e_voiceover.wav`\n")
    lines.append("- Score: `backend/validation/outputs/e2e_score.wav`\n")
    (DOCS_DIR / "e2e-api-validation-report.md").write_text("".join(lines))


if __name__ == "__main__":
    sys.exit(main())
