#!/usr/bin/env python3
"""
E2E verification on the deployed backend: create project → build bible →
generate one shot (Veo + Chirp + Lyria) → assemble → verify the final film
has a real audio track (voiceover + score).

This proves the audio fix works end-to-end on Cloud Run (not just locally).
"""
import requests, time, sys, subprocess, tempfile, json
from pathlib import Path

BASE = "https://auteur-dev-jbkbgthudq-uc.a.run.app"
LOGLINE = "A detective investigates a disappearance at a remote coastal lighthouse."

def step(n, msg):
    print(f"\n[{n}] {msg}")

# 1. Health check
step(1, "health check")
r = requests.get(f"{BASE}/api/health", timeout=30)
assert r.status_code == 200, f"health failed: {r.status_code}"
print(f"  ✓ backend healthy ({len(r.json()['endpoints'])} endpoints)")

# 2. Create project
step(2, "create project")
r = requests.post(f"{BASE}/api/projects", json={"logline": LOGLINE}, timeout=30)
assert r.status_code == 200, f"create project failed: {r.status_code} {r.text[:200]}"
project = r.json()
project_id = project["project_id"]
print(f"  ✓ project created: {project_id}")

# 3. Build bible (takes ~30s — Parallel Search + Gemini Pro)
step(3, "build bible (Parallel Search + Gemini + char ref image) — ~30s")
t0 = time.time()
r = requests.post(f"{BASE}/api/projects/{project_id}/build-bible", timeout=120)
elapsed = round(time.time() - t0, 1)
assert r.status_code == 200, f"build-bible failed ({r.status_code}): {r.text[:300]}"
bible_resp = r.json()
print(f"  ✓ bible built in {elapsed}s (v{bible_resp['version']}, {bible_resp['references_count']} refs, {len(bible_resp['bible']['characters'])} char)")

# 4. Get shots
step(4, "get shots")
r = requests.get(f"{BASE}/api/projects/{project_id}/shots", timeout=30)
assert r.status_code == 200, f"get shots failed: {r.status_code}"
shots = r.json()["shots"]
print(f"  ✓ {len(shots)} shots")
assert len(shots) >= 1, "no shots returned"
shot = shots[0]
shot_id = shot["id"]
print(f"  shot 1: {shot_id} (order={shot['order']})")

# 5. Generate shot (Veo + Chirp + Lyria) — takes ~60-90s
step(5, "generate shot 1 (Veo + Chirp + Lyria) — ~60-90s")
t0 = time.time()
r = requests.post(f"{BASE}/api/projects/{project_id}/shots/{shot_id}/generate",
                   json={"bible_version": 1}, timeout=300)
elapsed = round(time.time() - t0, 1)
assert r.status_code == 200, f"generate failed ({r.status_code}): {r.text[:300]}"
gen = r.json()
print(f"  ✓ generation complete in {elapsed}s")
print(f"  modalities: {[(k, v.get('status'), v.get('size_bytes',0)) for k,v in gen.get('modalities',{}).items()]}")
modalities = gen.get("modalities", {})
veo_ok = modalities.get("veo", {}).get("status") == "ok"
chirp_ok = modalities.get("chirp", {}).get("status") == "ok"
lyria_ok = modalities.get("lyria", {}).get("status") == "ok"
print(f"  veo={'✓' if veo_ok else '✗'} chirp={'✓' if chirp_ok else '✗'} lyria={'✓' if lyria_ok else '✗'}")

if not veo_ok:
    print("  ⚠ Veo failed — cannot test assembly audio. Aborting.")
    sys.exit(1)

# 6. Assemble the film (the audio fix is here)
step(6, "assemble film (mux Veo + Chirp + Lyria into final MP4)")
t0 = time.time()
r = requests.post(f"{BASE}/api/projects/{project_id}/assemble", timeout=120)
elapsed = round(time.time() - t0, 1)
assert r.status_code == 200, f"assemble failed ({r.status_code}): {r.text[:300]}"
asm = r.json()
print(f"  ✓ assembly complete in {elapsed}s")
print(f"  status: {asm.get('status')}")
print(f"  duration: {asm.get('duration_seconds')}s")
print(f"  clip_count: {asm.get('clip_count')}")
print(f"  size: {asm.get('size_bytes',0):,} bytes")
print(f"  has_audio: {asm.get('has_audio')}")
audio = asm.get("audio", {})
print(f"  audio: voiceover={audio.get('voiceover_shots',0)}, score={audio.get('score_shots',0)}, silent={audio.get('silent_shots',0)}")
for seg in audio.get("per_shot", []):
    print(f"    shot {seg['order']}: mode={seg['mix_mode']}, voice={seg['voiceover']}, score={seg['score']}, dur={seg['duration_seconds']}s")

# 7. Verify has_audio is True
assert asm.get("has_audio") is True, "❌ FINAL FILM HAS NO AUDIO — the fix didn't work!"
print(f"\n  ✓ has_audio=True — the final film has an audio track!")

# 8. Download the film + verify with ffprobe
step(8, "download final film + verify with ffprobe")
r = requests.get(f"{BASE}/api/projects/{project_id}/film", timeout=60)
assert r.status_code == 200, f"get film failed: {r.status_code}"
film_bytes = r.content
film_path = Path(tempfile.mktemp(suffix=".mp4"))
film_path.write_bytes(film_bytes)
print(f"  ✓ downloaded film ({len(film_bytes):,} bytes)")

# ffprobe: check audio stream exists
result = subprocess.run(
    ["ffprobe", "-v", "error", "-select_streams", "a",
     "-show_entries", "stream=index,codec_name,channels,sample_rate,duration",
     "-of", "json", str(film_path)],
    capture_output=True, text=True, timeout=30,
)
streams = json.loads(result.stdout).get("streams", [])
print(f"  ffprobe audio streams: {len(streams)}")
if streams:
    s = streams[0]
    print(f"    codec={s.get('codec_name')}, channels={s.get('channels')}, rate={s.get('sample_rate')}, dur={s.get('duration')}s")
assert len(streams) >= 1, "❌ ffprobe: no audio stream in the final film!"
print(f"  ✓ audio stream confirmed by ffprobe")

# ffprobe: check duration
result = subprocess.run(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
     "-of", "default=noprint_wrappers=1:nokey=1", str(film_path)],
    capture_output=True, text=True, timeout=10,
)
duration = float(result.stdout.strip())
print(f"  duration: {duration:.2f}s")

# ffmpeg: volumedetect (is the audio actually audible, not silent?)
result = subprocess.run(
    ["ffmpeg", "-i", str(film_path), "-af", "volumedetect", "-f", "null", "-"],
    capture_output=True, text=True, timeout=60,
)
import re
m = re.search(r"mean_volume:\s*(-?\d+\.?\d*)\s*dB", result.stderr)
mean_db = float(m.group(1)) if m else -100.0
print(f"  mean volume: {mean_db:.1f} dB (silent ≈ -100, healthy ≈ -30 to -10)")
assert mean_db > -60.0, f"❌ audio is effectively silent (mean={mean_db} dB)!"

print(f"\n{'='*60}")
print(f"✓ E2E VERIFICATION PASSED — the deployed film has audible audio")
print(f"{'='*60}")
print(f"  project: {project_id}")
print(f"  film: {len(film_bytes):,} bytes, {duration:.2f}s")
print(f"  audio: mean {mean_db:.1f} dB (audible)")
print(f"  has_audio: True")
print(f"  modalities: veo={'✓' if veo_ok else '✗'} chirp={'✓' if chirp_ok else '✗'} lyria={'✓' if lyria_ok else '✗'}")
film_path.unlink()
sys.exit(0)
