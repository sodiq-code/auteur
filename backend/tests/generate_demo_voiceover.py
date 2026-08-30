#!/usr/bin/env python3
"""
Generate the 3-minute demo video voiceover using Chirp 3 (gemini-3.1-flash-tts-preview)
with the Charon voice (deep, steady). Each segment is generated separately so the
timing matches the video clips exactly.

The narration is paced for 1.05x steady delivery — each segment's text is calibrated
to fill its exact time slot.
"""
import os, sys, time, wave, io, subprocess
from google import genai
from google.genai import types

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/home/z/my-project/auteur-sa-key.json'
client = genai.Client(vertexai=True, project='auteur-506523', location='us-central1')

# The narration script — each segment maps to a video clip + time slot
# The text is calibrated to fill the exact duration at a steady 1.05x pace
SEGMENTS = [
    {
        "id": "01_hook",
        "duration": 10,  # seconds
        "text": "AI cinema's biggest unsolved problem is not video quality. It is consistency.",
    },
    {
        "id": "02_problem",
        "duration": 10,
        "text": "Veo 3.1 produces gorgeous individual clips. But every shot is an isolated lottery. Characters drift. Wardrobes mutate. The result looks like four different films stitched together.",
    },
    {
        "id": "03_logline",
        "duration": 15,
        "text": "Meet Auteur. AI cinema's memory. Grounded in reality. Consistent across every shot. The filmmaker writes one logline. The Director Agent does the rest.",
    },
    {
        "id": "04_bible",
        "duration": 15,
        "text": "The Research Agent calls Parallel Search at runtime to ground every creative decision in real-world references. Then Gemini 3.1 Pro synthesizes a typed, versioned Film Bible. Characters, locations, wardrobes, voices, score motifs, style anchors, story beats. Every claim traces to a real URL.",
    },
    {
        "id": "05_research",
        "duration": 15,
        "text": "The Film Bible is injected as structured context into every generation call. Veo 3.1 for video. Chirp 3 for voiceover. Lyria 2 for score. The same character, the same wardrobe, the same world, across every shot.",
    },
    {
        "id": "06_render",
        "duration": 15,
        "text": "Each shot generates with the Bible injected as context. Four shots, four scenes, one coherent character.",
    },
    {
        "id": "07_drift_regen",
        "duration": 25,
        "text": "The Consistency Check Agent scores every shot. Face, age, beard, wardrobe. When drift exceeds the threshold, the system regenerates with the drift report injected as corrective context. Prior face identity zero point seven zero. Regeneration. New face identity zero point eight zero. The loop is closed.",
    },
    {
        "id": "08_assembly",
        "duration": 10,
        "text": "ffmpeg concatenates the clips and muxes the voiceover and score into the final film. With synchronized audio.",
    },
    {
        "id": "09_technical",
        "duration": 35,
        "text": "Three agents on Google Agent Development Kit. Director orchestrates. Research grounds via Parallel Search. Consistency Check scores drift with Gemini Vision. The Film Bible is typed, versioned, citable. Every generation cites its Bible version. Drift is attributable. All on Google Cloud. Gemini, Veo, Chirp, Lyria, Firestore, Cloud Run.",
    },
    {
        "id": "10_final_film",
        "duration": 20,
        "text": "Same character. Same world. Same voice. Same score. Same style. Across every shot. This is the project that made an AI film look like the same film.",
    },
    {
        "id": "11_closing",
        "duration": 10,
        "text": "Auteur. AI cinema's memory. Grounded in reality. Consistent across every shot. Try it live.",
    },
]

OUTDIR = "/home/z/my-project/demo-voiceover"
os.makedirs(OUTDIR, exist_ok=True)

def generate_segment(text: str, voice: str = "Charon") -> bytes:
    """Generate a TTS segment, return raw PCM (24kHz mono 16-bit)."""
    cfg = types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            language_code="en-US",
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
            ),
        ),
    )
    resp = client.models.generate_content(
        model="gemini-3.1-flash-tts-preview", contents=text, config=cfg,
    )
    for cand in resp.candidates or []:
        for part in (cand.content.parts if cand.content else []):
            inline = getattr(part, "inline_data", None)
            if inline and inline.data:
                return inline.data
    raise RuntimeError("no audio returned")

def pcm_to_wav(pcm: bytes, sample_rate: int = 24000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm)
    return buf.getvalue()

def get_duration(wav_path: str) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", wav_path],
        capture_output=True, text=True, timeout=10,
    )
    return float(r.stdout.strip()) if r.returncode == 0 else 0.0

def adjust_to_target(wav_path: str, target_duration: float, out_path: str) -> float:
    """Adjust the WAV to exactly target_duration using atempo (1.05x max deviation).
    If the natural duration is within 1.05x of target, use atempo to match exactly.
    Otherwise, pad with silence or trim."""
    natural = get_duration(wav_path)
    if natural == 0:
        return 0.0

    # Calculate the tempo adjustment needed
    ratio = natural / target_duration
    if ratio > 1.5 or ratio < 0.5:
        # Too far off — just pad/trim
        if natural < target_duration:
            # Pad with silence
            pad_dur = target_duration - natural
            subprocess.run([
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", wav_path,
                "-af", f"apad=pad_dur={pad_dur}",
                "-acodec", "pcm_s16le",
                out_path,
            ], check=True, timeout=30)
        else:
            # Trim
            subprocess.run([
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", wav_path, "-t", str(target_duration),
                "-acodec", "pcm_s16le", out_path,
            ], check=True, timeout=30)
    else:
        # Use atempo to match exactly (within the 0.5-2.0 range)
        atempo = 1.0 / ratio  # if natural > target, speed up (atempo > 1); if natural < target, slow down (atempo < 1)
        # Clamp to reasonable bounds
        atempo = max(0.75, min(1.35, atempo))
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", wav_path,
            "-af", f"atempo={atempo:.4f}",
            "-acodec", "pcm_s16le",
            out_path,
        ], check=True, timeout=30)

    result_dur = get_duration(out_path)
    # If still not exact, pad/trim
    if abs(result_dur - target_duration) > 0.3:
        if result_dur < target_duration:
            pad = target_duration - result_dur
            subprocess.run([
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", out_path,
                "-af", f"apad=pad_dur={pad}",
                "-acodec", "pcm_s16le",
                "-f", "wav",
                out_path + ".tmp.wav",
            ], check=True, timeout=30)
            os.replace(out_path + ".tmp.wav", out_path)
        else:
            subprocess.run([
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", out_path, "-t", str(target_duration),
                "-acodec", "pcm_s16le",
                "-f", "wav",
                out_path + ".tmp.wav",
            ], check=True, timeout=30)
            os.replace(out_path + ".tmp.wav", out_path)

    return get_duration(out_path)

print("=" * 60)
print("GENERATING DEMO VOICEOVER (Charon voice, steady pace)")
print("=" * 60)

total = 0
for seg in SEGMENTS:
    out_path = os.path.join(OUTDIR, f"{seg['id']}.wav")
    print(f"\n[{seg['id']}] target={seg['duration']}s")
    print(f"  text: {seg['text'][:80]}...")

    # Generate
    pcm = generate_segment(seg["text"])
    wav = pcm_to_wav(pcm)
    raw_path = out_path + ".raw.wav"
    with open(raw_path, "wb") as f:
        f.write(wav)
    natural = get_duration(raw_path)
    print(f"  natural duration: {natural:.1f}s")

    # Adjust to exact target
    final = adjust_to_target(raw_path, seg["duration"], out_path)
    print(f"  adjusted duration: {final:.1f}s (target {seg['duration']}s)")

    # Cleanup raw
    os.unlink(raw_path)
    total += final

print(f"\n{'=' * 60}")
print(f"TOTAL VOICEOVER DURATION: {total:.1f}s ({total/60:.1f}min)")
print(f"Target: 180s (3:00)")
print(f"{'=' * 60}")
