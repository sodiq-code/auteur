"""
Auteur — assembly pipeline (blueprint Section 32.2 Day 8).

Assembles the generated Veo clips into a single MP4 via ffmpeg concatenation,
then muxes the per-shot Chirp voiceover + Lyria score as the audio track.

For each shot:
  1. Retrieve the Veo MP4 (video-only — generate_audio=False).
  2. Retrieve the Chirp voiceover WAV + Lyria score WAV from the store.
  3. Build a per-shot audio segment: mix voiceover (loud) + score (quiet),
     trimmed/padded to exactly the Veo clip duration.
Concatenate all video segments + all audio segments, then mux into the final MP4.

Definition of done (blueprint P859): shot grid shows 4 thumbnails; assembly
produces a single MP4 with synchronized audio (voiceover + score).
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

from ..bible import store
from ..storage import cloud_storage

# Audio mixing constants
VOICEOVER_VOLUME = 1.0      # voiceover at full volume (the narration)
SCORE_VOLUME = 0.25         # score at 25% volume (bed under the voiceover)
AUDIO_SAMPLE_RATE = 48000   # 48kHz (matches Lyria output; Chirp gets resampled)
AUDIO_CHANNELS = 2          # stereo
DEFAULT_SHOT_DURATION = 8.0 # Veo clips are 8s (duration_seconds=8 in generate.py)


async def assemble_film(project_id: str) -> dict[str, Any]:
    """Assemble all generated shots into a single MP4 with audio (blueprint Day 8 DoD).

    Pipeline:
      1. Retrieve the generated Veo clips (video) + Chirp voiceover + Lyria score
         from the in-memory generations store.
      2. For each shot, build a per-shot audio segment (voiceover + score mixed,
         trimmed/padded to the Veo clip duration).
      3. Concatenate the Veo clips into a single video stream.
      4. Concatenate the per-shot audio segments into a single audio track.
      5. Mux the video + audio into the final MP4 (AAC audio, H.264 video copy).
      6. Upload to Cloud Storage (optional).
      7. Return the output URL + duration + shot count + audio summary.
    """
    t0 = time.time()
    await store.log_event(project_id, "assembly_started", {})

    # 1. Get all shots for this project
    shots = await store.get_shots(project_id)
    if not shots:
        raise ValueError("no shots to assemble — generate shots first")

    tmpdir = Path(tempfile.mkdtemp(prefix=f"auteur_assemble_{project_id}_"))
    try:
        clip_paths: list[Path] = []
        audio_paths: list[Path] = []
        audio_summary: list[dict[str, Any]] = []

        for shot in sorted(shots, key=lambda s: s.order):
            veo_gen = await store.get_generation(project_id, shot.id, "veo")
            if not veo_gen or not veo_gen.get("mp4_bytes"):
                # Skip shots without a generated video
                continue

            # Write the Veo MP4 to disk
            clip_path = tmpdir / f"shot_{shot.order}_veo.mp4"
            clip_path.write_bytes(veo_gen["mp4_bytes"])
            clip_paths.append(clip_path)

            # Measure the actual Veo clip duration (ffprobe) — falls back to 8s
            shot_duration = _get_duration(clip_path) or DEFAULT_SHOT_DURATION

            # Retrieve the per-shot audio assets (now persisted by generate.py)
            chirp_gen = await store.get_generation(project_id, shot.id, "chirp")
            lyria_gen = await store.get_generation(project_id, shot.id, "lyria")
            voiceover_wav = chirp_gen.get("wav_bytes") if chirp_gen else None
            score_wav = lyria_gen.get("wav_bytes") if lyria_gen else None

            # Build the per-shot audio segment (mix voiceover + score, trim to duration)
            audio_path, seg_info = _build_shot_audio(
                shot.order, shot_duration, voiceover_wav, score_wav, tmpdir,
            )
            audio_paths.append(audio_path)
            audio_summary.append({
                "order": shot.order,
                "shot_id": shot.id,
                "duration_seconds": round(shot_duration, 2),
                "voiceover": bool(voiceover_wav),
                "score": bool(score_wav),
                "mix_mode": seg_info["mode"],
            })

        if not clip_paths:
            raise ValueError("no generated Veo clips found — generate shots first")

        # 2. Concatenate the Veo clips (video-only stream)
        video_concat_path = tmpdir / "video_concat.mp4"
        _concat_mp4(clip_paths, video_concat_path)

        # 3. Concatenate the per-shot audio segments
        audio_concat_path = tmpdir / "audio_concat.wav"
        _concat_wav(audio_paths, audio_concat_path)

        # 4. Mux video + audio into the final MP4
        output_path = tmpdir / "final_film.mp4"
        _mux_av(video_concat_path, audio_concat_path, output_path)

        film_bytes = output_path.read_bytes()
        elapsed = round(time.time() - t0, 2)
        duration = _get_duration(output_path)
        has_audio = _has_audio_stream(output_path)

        # Save the final film bytes in the generations store (for /film streaming)
        await store.save_generation(project_id, "final", "film", {
            "mp4_bytes": film_bytes,
            "size_bytes": len(film_bytes),
            "duration_seconds": duration,
            "clip_count": len(clip_paths),
            "has_audio": has_audio,
            "audio_summary": audio_summary,
            "elapsed_sec": elapsed,
        })

        # 5. Upload to Cloud Storage (optional)
        output_url = None
        try:
            output_url = cloud_storage.upload_bytes(
                f"{project_id}/final_film.mp4", film_bytes, content_type="video/mp4",
            )
        except Exception:
            pass

        await store.log_event(project_id, "assembly_completed", {
            "output_url": output_url,
            "duration_seconds": duration,
            "clip_count": len(clip_paths),
            "size_bytes": len(film_bytes),
            "has_audio": has_audio,
            "audio_summary": audio_summary,
            "elapsed_sec": elapsed,
        })

        return {
            "status": "ok",
            "output_url": output_url,
            "duration_seconds": duration,
            "clip_count": len(clip_paths),
            "size_bytes": len(film_bytes),
            "has_audio": has_audio,
            "audio": {
                "voiceover_shots": sum(1 for s in audio_summary if s["voiceover"]),
                "score_shots": sum(1 for s in audio_summary if s["score"]),
                "silent_shots": sum(1 for s in audio_summary if s["mix_mode"] == "silent"),
                "per_shot": audio_summary,
            },
            "elapsed_sec": elapsed,
        }
    finally:
        # cleanup temp files
        shutil.rmtree(tmpdir, ignore_errors=True)


# --------------------------------------------------------------------------- #
# Per-shot audio builder
# --------------------------------------------------------------------------- #

def _build_shot_audio(
    shot_order: int,
    duration: float,
    voiceover_wav: Optional[bytes],
    score_wav: Optional[bytes],
    tmpdir: Path,
) -> tuple[Path, dict[str, Any]]:
    """Build a per-shot audio segment: voiceover + score mixed, trimmed to duration.

    Returns (path_to_wav, info_dict). The output is always exactly `duration`
    seconds long, 48kHz stereo PCM s16le WAV. If neither voiceover nor score is
    available, generates silence.
    """
    dur = f"{max(duration, 0.1):.3f}"  # ffmpeg wants a positive number
    out_path = tmpdir / f"shot_{shot_order}_audio.wav"

    # Case 1: no audio assets — generate silence
    if not voiceover_wav and not score_wav:
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", f"anullsrc=r={AUDIO_SAMPLE_RATE}:cl=stereo",
            "-t", dur, "-c:a", "pcm_s16le", str(out_path),
        ]
        _run_ffmpeg(cmd, "silence generation")
        return out_path, {"mode": "silent"}

    # Write the audio assets to disk for ffmpeg input
    inputs: list[tuple[str, Path, float]] = []  # (label, path, volume)
    if voiceover_wav:
        p = tmpdir / f"shot_{shot_order}_voice.wav"
        p.write_bytes(voiceover_wav)
        inputs.append(("voice", p, VOICEOVER_VOLUME))
    if score_wav:
        p = tmpdir / f"shot_{shot_order}_score.wav"
        p.write_bytes(score_wav)
        inputs.append(("score", p, SCORE_VOLUME))

    # Case 2: single audio asset — trim/pad to duration, normalize format
    if len(inputs) == 1:
        label, in_path, vol = inputs[0]
        af = f"volume={vol},apad,atrim=0:{dur}"
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(in_path),
            "-af", af,
            "-t", dur,
            "-ar", str(AUDIO_SAMPLE_RATE), "-ac", str(AUDIO_CHANNELS),
            "-c:a", "pcm_s16le", str(out_path),
        ]
        _run_ffmpeg(cmd, f"single-audio ({label})")
        return out_path, {"mode": f"single:{label}"}

    # Case 3: mix voiceover + score
    # Build: [0]volume=v0,apad,atrim=0:dur[a0]; [1]volume=v1,apad,atrim=0:dur[a1];
    #        [a0][a1]amix=inputs=2:duration=first:normalize=0,atrim=0:dur[aout]
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for _, in_path, _ in inputs:
        cmd += ["-i", str(in_path)]
    chain_parts = []
    for i, (_, _, vol) in enumerate(inputs):
        chain_parts.append(
            f"[{i}]volume={vol},apad,atrim=0:{dur}[a{i}]"
        )
    mix_inputs = "".join(f"[a{i}]" for i in range(len(inputs)))
    chain_parts.append(
        f"{mix_inputs}amix=inputs={len(inputs)}:duration=first:normalize=0,atrim=0:{dur}[aout]"
    )
    filter_complex = ";".join(chain_parts)
    cmd += [
        "-filter_complex", filter_complex,
        "-map", "[aout]",
        "-t", dur,
        "-ar", str(AUDIO_SAMPLE_RATE), "-ac", str(AUDIO_CHANNELS),
        "-c:a", "pcm_s16le", str(out_path),
    ]
    _run_ffmpeg(cmd, "mix voiceover+score")
    return out_path, {"mode": "mixed"}


# --------------------------------------------------------------------------- #
# Concat + mux helpers
# --------------------------------------------------------------------------- #

def _concat_mp4(clip_paths: list[Path], output_path: Path) -> None:
    """Concatenate MP4 clips via the concat demuxer (copy codec if possible)."""
    list_file = output_path.parent / "video_concat_list.txt"
    list_file.write_text("\n".join(
        f"file '{p.absolute()}'" for p in clip_paths
    ))
    # Try stream copy first (fast — works when all clips share codec/timestamps)
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy", str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        # Fallback: re-encode (handles codec/timestamp mismatches)
        cmd_reencode = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-c:v", "libx264", "-c:a", "aac",
            "-movflags", "+faststart",
            str(output_path),
        ]
        result2 = subprocess.run(cmd_reencode, capture_output=True, text=True, timeout=180)
        if result2.returncode != 0:
            raise RuntimeError(
                f"ffmpeg concat failed (copy: {result.stderr[:200]} | re-encode: {result2.stderr[:200]})"
            )


def _concat_wav(wav_paths: list[Path], output_path: Path) -> None:
    """Concatenate WAV files via the concat demuxer (copy codec)."""
    list_file = output_path.parent / "audio_concat_list.txt"
    list_file.write_text("\n".join(
        f"file '{p.absolute()}'" for p in wav_paths
    ))
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy", str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        # Fallback: re-encode (in case WAV headers differ)
        cmd_reencode = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-ar", str(AUDIO_SAMPLE_RATE), "-ac", str(AUDIO_CHANNELS),
            "-c:a", "pcm_s16le", str(output_path),
        ]
        result2 = subprocess.run(cmd_reencode, capture_output=True, text=True, timeout=120)
        if result2.returncode != 0:
            raise RuntimeError(
                f"ffmpeg audio concat failed (copy: {result.stderr[:200]} | re-encode: {result2.stderr[:200]})"
            )


def _mux_av(video_path: Path, audio_path: Path, output_path: Path) -> None:
    """Mux a video-only MP4 + a WAV into the final MP4 (AAC audio, copy video)."""
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-map", "0:v:0", "-map", "1:a:0",
        "-shortest",
        "-movflags", "+faststart",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        # Fallback: re-encode the video too (handles edge cases where copy fails)
        cmd_reencode = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
            "-map", "0:v:0", "-map", "1:a:0",
            "-shortest",
            "-movflags", "+faststart",
            str(output_path),
        ]
        result2 = subprocess.run(cmd_reencode, capture_output=True, text=True, timeout=240)
        if result2.returncode != 0:
            raise RuntimeError(
                f"ffmpeg mux failed (copy: {result.stderr[:200]} | re-encode: {result2.stderr[:200]})"
            )


# --------------------------------------------------------------------------- #
# ffprobe helpers
# --------------------------------------------------------------------------- #

def _get_duration(path: Path) -> float:
    """Get MP4/WAV duration in seconds via ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=10,
        )
        return float(result.stdout.strip()) if result.returncode == 0 else 0.0
    except Exception:
        return 0.0


def _has_audio_stream(path: Path) -> bool:
    """Return True if the media file has at least one audio stream."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a",
             "-show_entries", "stream=index", "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=10,
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


def _run_ffmpeg(cmd: list[str], context: str) -> None:
    """Run an ffmpeg command, raising RuntimeError with context on failure."""
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg {context} failed: {result.stderr[:300]}"
        )
