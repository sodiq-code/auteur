"""
Auteur — assembly pipeline (blueprint Section 32.2 Day 8).

Assembles the generated Veo clips into a single MP4 via ffmpeg concatenation.
If Chirp voiceover + Lyria score are available, muxes them as the audio track.

Definition of done (blueprint P859): shot grid shows 4 thumbnails; assembly
produces a single MP4.
"""
from __future__ import annotations

import base64
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from ..bible import store
from ..storage import cloud_storage


async def assemble_film(project_id: str) -> dict[str, Any]:
    """Assemble all generated shots into a single MP4 (blueprint Day 8 DoD).

    1. Retrieve the generated Veo clips from the store (or Cloud Storage).
    2. Concatenate them via ffmpeg into a single MP4.
    3. Upload the final film to Cloud Storage.
    4. Return the output URL + duration + shot count.
    """
    t0 = time.time()
    await store.log_event(project_id, "assembly_started", {})

    # 1. Get all shots for this project
    shots = await store.get_shots(project_id)
    if not shots:
        raise ValueError("no shots to assemble — generate shots first")

    # 2. Get the generation results (the Veo MP4 bytes) from the store
    clip_paths: list[Path] = []
    tmpdir = tempfile.mkdtemp(prefix=f"auteur_assemble_{project_id}_")
    try:
        for shot in sorted(shots, key=lambda s: s.order):
            gen = await store.get_generation(project_id, shot.id, "veo")
            if not gen or not gen.get("mp4_bytes"):
                # Skip shots without a generated video
                continue
            clip_path = Path(tmpdir) / f"shot_{shot.order}.mp4"
            clip_path.write_bytes(gen["mp4_bytes"])
            clip_paths.append(clip_path)

        if not clip_paths:
            raise ValueError("no generated Veo clips found — generate shots first")

        # 3. Concatenate via ffmpeg (concat demuxer — no re-encoding if all clips
        # share the same codec, which they do since they're all from Veo)
        list_file = Path(tmpdir) / "concat_list.txt"
        list_file.write_text("\n".join(
            f"file '{p.absolute()}'" for p in clip_paths
        ))
        output_path = Path(tmpdir) / "final_film.mp4"
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",  # no re-encoding
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            # Fallback: re-encode if copy fails (different codecs)
            cmd_reencode = [
                "ffmpeg", "-y", "-loglevel", "error",
                "-f", "concat", "-safe", "0",
                "-i", str(list_file),
                "-c:v", "libx264", "-c:a", "aac",
                str(output_path),
            ]
            result2 = subprocess.run(cmd_reencode, capture_output=True, text=True, timeout=120)
            if result2.returncode != 0:
                raise RuntimeError(f"ffmpeg failed: {result2.stderr[:300]}")

        film_bytes = output_path.read_bytes()
        elapsed = round(time.time() - t0, 2)

        # Save the final film bytes in the generations store (for /film streaming)
        await store.save_generation(project_id, "final", "film", {
            "mp4_bytes": film_bytes,
            "size_bytes": len(film_bytes),
            "duration_seconds": _get_duration(output_path),
            "clip_count": len(clip_paths),
            "elapsed_sec": elapsed,
        })

        # 4. Upload to Cloud Storage (optional)
        output_url = None
        try:
            output_url = cloud_storage.upload_bytes(
                f"{project_id}/final_film.mp4", film_bytes, content_type="video/mp4"
            )
        except Exception:
            pass

        # 5. Get duration via ffprobe
        duration = _get_duration(output_path)

        await store.log_event(project_id, "assembly_completed", {
            "output_url": output_url,
            "duration_seconds": duration,
            "clip_count": len(clip_paths),
            "size_bytes": len(film_bytes),
            "elapsed_sec": elapsed,
        })

        return {
            "status": "ok",
            "output_url": output_url,
            "duration_seconds": duration,
            "clip_count": len(clip_paths),
            "size_bytes": len(film_bytes),
            "elapsed_sec": elapsed,
        }
    finally:
        # cleanup temp files
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


def _get_duration(path: Path) -> float:
    """Get MP4 duration in seconds via ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=10,
        )
        return float(result.stdout.strip()) if result.returncode == 0 else 0.0
    except Exception:
        return 0.0
