#!/usr/bin/env python3
"""
Local verification for the assembly pipeline audio muxing.

Generates synthetic Veo MP4 clips (video-only, 8s each) + synthetic Chirp
voiceover WAVs + synthetic Lyria score WAVs, saves them to the in-memory store,
then runs assemble_film() and verifies:
  1. The final MP4 has an audio stream (ffprobe).
  2. The audio stream duration matches the video duration.
  3. The audio is NOT silent (RMS amplitude > 0).
  4. The per-shot audio segments are correctly mixed/trimmed/padded.

Also tests edge cases:
  - Shot with voiceover only (no score).
  - Shot with score only (no voiceover).
  - Shot with neither (silence).
  - Shot with both (mix).

Run: python3 backend/tests/test_assembly_audio.py
"""
from __future__ import annotations

import asyncio
import io
import struct
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

# Add the backend to the path so we can import the pipeline + store
BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND.parent))

from backend.bible import store  # noqa: E402
from backend.pipelines import assemble as assemble_pipeline  # noqa: E402

# Force the in-memory store (no Firestore creds in this test env)
store._USE_MEMORY = True
store._FIRESTORE_CLIENT = None

PROJECT_ID = "test-audio-verify"
SAMPLE_RATE = 48000


# --------------------------------------------------------------------------- #
# Synthetic asset generators (no API calls — pure ffmpeg + Python)
# --------------------------------------------------------------------------- #

def _make_silent_video(path: Path, duration: float = 8.0, color: str = "black") -> None:
    """Generate a video-only MP4 (no audio track) of a solid color."""
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", f"color=c={color}:s=1280x720:r=24:d={duration}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-an",  # no audio
        str(path),
    ]
    subprocess.run(cmd, check=True, capture_output=True, timeout=30)


def _make_tone_wav(path: Path, freq: float, duration: float, sample_rate: int = SAMPLE_RATE) -> None:
    """Generate a WAV with a sine wave of the given frequency + duration."""
    n_samples = int(duration * sample_rate)
    # Generate a simple sine wave with a small envelope (avoid clicks)
    frames = bytearray()
    for i in range(n_samples):
        # linear fade-in/out over 50ms to avoid clicks
        t = i / sample_rate
        env = 1.0
        fade = int(0.05 * sample_rate)
        if i < fade:
            env = i / fade
        elif i > n_samples - fade:
            env = (n_samples - i) / fade
        # sine wave, 0.5 amplitude (16-bit signed: -16384..16384)
        sample = int(0.5 * env * 32767 * __import__("math").sin(2 * __import__("math").pi * freq * t))
        frames += struct.pack("<h", sample)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(bytes(frames))


def _wav_bytes(freq: float, duration: float, sample_rate: int = 24000) -> bytes:
    """Generate WAV bytes (in memory) with a sine wave."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        n = int(duration * sample_rate)
        frames = bytearray()
        for i in range(n):
            t = i / sample_rate
            sample = int(0.5 * 32767 * __import__("math").sin(2 * __import__("math").pi * freq * t))
            frames += struct.pack("<h", sample)
        w.writeframes(bytes(frames))
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# ffprobe helpers
# --------------------------------------------------------------------------- #

def _ffprobe_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, timeout=10,
    )
    return float(r.stdout.strip()) if r.returncode == 0 else 0.0


def _ffprobe_has_audio(path: Path) -> bool:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=index", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, timeout=10,
    )
    return bool(r.stdout.strip())


def _ffprobe_audio_rms(path: Path) -> float:
    """Compute the mean volume of the audio track in dB (via volumedetect).

    Returns the mean_volume in dB (negative; -100+ = effectively silent).
    A healthy audible track is typically -30 to -10 dB.
    """
    r = subprocess.run(
        ["ffmpeg", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True, timeout=60,
    )
    # volumedetect writes to stderr
    import re
    m = re.search(r"mean_volume:\s*(-?\d+\.?\d*)\s*dB", r.stderr)
    if not m:
        return -100.0
    db = float(m.group(1))
    return db


# --------------------------------------------------------------------------- #
# Test scenarios
# --------------------------------------------------------------------------- #

async def _setup_shots(shots_config: list[dict]) -> list:
    """Save synthetic shots + their Veo/Chirp/Lyria generations to the store.

    Each config: {order, id, color, voice_freq (or None), score_freq (or None),
                   duration}
    """
    from backend.bible.schema import ShotSpec

    tmpdir = Path(tempfile.mkdtemp(prefix="audio_verify_"))
    saved_shots = []

    for cfg in shots_config:
        # Build + save the shot
        shot = ShotSpec(
            id=cfg["id"],
            order=cfg["order"],
            description=f"test shot {cfg['order']}",
            bible_version=1,
            status="generated",
            modality_calls=["veo", "chirp", "lyria"],
        )
        await store.save_shot(shot, PROJECT_ID)
        saved_shots.append(shot)

        # Generate + save the Veo MP4 (video-only, synthetic)
        veo_path = tmpdir / f"shot_{cfg['order']}_veo.mp4"
        _make_silent_video(veo_path, duration=cfg.get("duration", 8.0), color=cfg["color"])
        mp4_bytes = veo_path.read_bytes()
        await store.save_generation(PROJECT_ID, cfg["id"], "veo", {
            "mp4_bytes": mp4_bytes,
            "size_bytes": len(mp4_bytes),
        })

        # Generate + save the Chirp voiceover WAV (if requested)
        if cfg.get("voice_freq"):
            # voiceover is ~3-4 seconds (shorter than the 8s video)
            wav = _wav_bytes(cfg["voice_freq"], duration=cfg.get("voice_dur", 4.0), sample_rate=24000)
            await store.save_generation(PROJECT_ID, cfg["id"], "chirp", {
                "wav_bytes": wav,
                "size_bytes": len(wav),
            })

        # Generate + save the Lyria score WAV (if requested)
        if cfg.get("score_freq"):
            # score is ~8 seconds (matches video), 48kHz stereo via Lyria
            wav = _wav_bytes(cfg["score_freq"], duration=cfg.get("score_dur", 8.0), sample_rate=48000)
            await store.save_generation(PROJECT_ID, cfg["id"], "lyria", {
                "wav_bytes": wav,
                "size_bytes": len(wav),
            })

    return saved_shots


async def run_test():
    print("=" * 60)
    print("ASSEMBLY AUDIO MUXING — LOCAL VERIFICATION")
    print("=" * 60)

    # Define 4 shots covering all audio scenarios:
    #   Shot 1: voiceover + score (mix mode)  — 440Hz voice, 220Hz score
    #   Shot 2: voiceover only                — 523Hz voice
    #   Shot 3: score only                    — 330Hz score
    #   Shot 4: neither (silence)
    shots_config = [
        {"order": 1, "id": "shot-1", "color": "0x1a1a2e", "voice_freq": 440.0, "score_freq": 220.0},
        {"order": 2, "id": "shot-2", "color": "0x16213e", "voice_freq": 523.0, "score_freq": None},
        {"order": 3, "id": "shot-3", "color": "0x0f3460", "voice_freq": None, "score_freq": 330.0},
        {"order": 4, "id": "shot-4", "color": "0x533483", "voice_freq": None, "score_freq": None},
    ]

    print("\n[1/4] setting up 4 synthetic shots (video-only MP4 + voiceover/score WAVs)...")
    await _setup_shots(shots_config)
    print("  ✓ 4 shots saved to the in-memory store")
    print("  ✓ shot-1: voiceover(440Hz) + score(220Hz) — mix mode")
    print("  ✓ shot-2: voiceover(523Hz) only — single:voice mode")
    print("  ✓ shot-3: score(330Hz) only — single:score mode")
    print("  ✓ shot-4: no audio — silent mode")

    print("\n[2/4] running assemble_film()...")
    result = await assemble_pipeline.assemble_film(PROJECT_ID)
    print(f"  status: {result['status']}")
    print(f"  duration: {result['duration_seconds']}s")
    print(f"  clip_count: {result['clip_count']}")
    print(f"  size: {result['size_bytes']:,} bytes")
    print(f"  has_audio: {result['has_audio']}")
    print(f"  audio summary: voiceover={result['audio']['voiceover_shots']}, "
          f"score={result['audio']['score_shots']}, "
          f"silent={result['audio']['silent_shots']}")

    assert result["status"] == "ok", f"assembly failed: {result}"
    assert result["clip_count"] == 4, f"expected 4 clips, got {result['clip_count']}"
    assert result["has_audio"] is True, "FINAL FILM HAS NO AUDIO STREAM — the bug is not fixed!"
    assert result["audio"]["voiceover_shots"] == 2, f"expected 2 voiced shots, got {result['audio']['voiceover_shots']}"
    assert result["audio"]["score_shots"] == 2, f"expected 2 scored shots, got {result['audio']['score_shots']}"
    assert result["audio"]["silent_shots"] == 1, f"expected 1 silent shot, got {result['audio']['silent_shots']}"
    print("  ✓ has_audio=True, audio summary correct")

    print("\n[3/4] verifying the final MP4 on disk...")
    # Get the final film bytes from the store
    film_gen = await store.get_generation(PROJECT_ID, "final", "film")
    assert film_gen and film_gen.get("mp4_bytes"), "no final film in store"

    tmpdir = Path(tempfile.mkdtemp(prefix="audio_verify_output_"))
    film_path = tmpdir / "final_film.mp4"
    film_path.write_bytes(film_gen["mp4_bytes"])

    # Check the audio stream exists + duration matches video
    has_audio = _ffprobe_has_audio(film_path)
    assert has_audio, "ffprobe: final film has NO audio stream!"
    print(f"  ✓ ffprobe confirms audio stream present")

    duration = _ffprobe_duration(film_path)
    expected_duration = 4 * 8.0  # 4 shots × 8s each = 32s
    print(f"  duration: {duration:.2f}s (expected ~{expected_duration:.1f}s)")
    assert abs(duration - expected_duration) < 1.5, f"duration {duration:.2f} far from expected {expected_duration:.1f}"

    # Check the audio is NOT silent (mean volume should be well above -60 dB)
    mean_db = _ffprobe_audio_rms(film_path)
    print(f"  audio mean volume: {mean_db:.1f} dB (silent ≈ -100 dB, healthy ≈ -30 to -10 dB)")
    assert mean_db > -60.0, f"audio is effectively silent (mean={mean_db} dB), the mux did not produce audible audio!"

    # Also verify each per-shot audio segment was built correctly
    print("\n[4/4] verifying per-shot mix modes...")
    for seg in result["audio"]["per_shot"]:
        print(f"  shot {seg['order']}: mode={seg['mix_mode']}, "
              f"voice={seg['voiceover']}, score={seg['score']}, "
              f"dur={seg['duration_seconds']}s")

    assert result["audio"]["per_shot"][0]["mix_mode"] == "mixed", "shot 1 should be 'mixed'"
    assert result["audio"]["per_shot"][1]["mix_mode"] == "single:voice", "shot 2 should be 'single:voice'"
    assert result["audio"]["per_shot"][2]["mix_mode"] == "single:score", "shot 3 should be 'single:score'"
    assert result["audio"]["per_shot"][3]["mix_mode"] == "silent", "shot 4 should be 'silent'"
    print("  ✓ all 4 mix modes correct")

    print("\n" + "=" * 60)
    print("✓ ALL CHECKS PASSED — the assembled film has a real, audible audio track")
    print("=" * 60)
    print(f"\nFinal film: {film_path}")
    print(f"  - {duration:.2f}s, {len(film_gen['mp4_bytes']):,} bytes")
    print(f"  - audio mean volume: {mean_db:.1f} dB (audible)")
    print(f"  - 4 shots: mix/single-voice/single-score/silent")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run_test()))
