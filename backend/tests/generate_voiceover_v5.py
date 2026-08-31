#!/usr/bin/env python3
"""
Generate perfectly-synced narration v5:
- Uses the CORRECT video clips (07-01-28 for Bible view with tabs)
- No long silence gaps (every segment's narration fills its duration)
- Video ends at 2:50 (170s)
"""
import os, sys, time, wave, io, subprocess, json
from google import genai
from google.genai import types

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/home/z/my-project/auteur-sa-key.json'
client = genai.Client(vertexai=True, project='auteur-506523', location='us-central1')

OUTDIR = "/home/z/my-project/demo-voiceover-v5"
os.makedirs(OUTDIR, exist_ok=True)

# VIDEO TIMELINE (170s = 2:50):
# Source clips:
#   A = 07-00-03 (landing + logline + research start, 27s total)
#   B = 07-01-28 (research results + Bible view with tabs + shot list, 45s total)
#   C = 07-13-00 (render queue with generated shots, 45s total)
#   D = 07-23-28 (drift dashboard + regeneration, 28s total)
#   E = 07-25-34 (assembly + final film, 36s total)
#   F = 03-51-28 (share view, 7s total)

SEGMENTS = [
    # 1. Intro card (0-5s) — SILENCE
    {"start": 0, "dur": 5, "text": None, "name": "01_intro"},

    # 2. Landing + logline (5-17s, 12s) — from video A (07-00-03, 0-12s)
    {"start": 5, "dur": 12, "text": (
        "AI cinema's biggest unsolved problem is not video quality. It is consistency. "
        "Veo 3.1 produces gorgeous clips, but characters drift. Wardrobes mutate. "
        "The filmmaker writes one logline."
    ), "name": "02_landing"},

    # 3. Research results (17-25s, 8s) — from video B (07-01-28, 0-8s)
    {"start": 17, "dur": 8, "text": (
        "The Director Agent researches it via Parallel Search at runtime, "
        "grounding every creative decision in real-world references."
    ), "name": "03_research"},

    # 4. Bible view with tabs (25-40s, 15s) — from video B (07-01-28, 8-23s)
    # This shows the Bible component with all tabs: Locations, Voice, Score, References
    {"start": 25, "dur": 15, "text": (
        "Then Gemini 3.1 Pro synthesizes a typed, versioned Film Bible. "
        "Characters, locations, wardrobes, voice profiles, score motifs, "
        "style anchors, and story beats. Every claim traces to a real URL."
    ), "name": "04_bible"},

    # 5. Shot list (40-48s, 8s) — from video B (07-01-28, 35-43s)
    {"start": 40, "dur": 8, "text": (
        "The Bible generates a shot list. Four shots, each citing the Bible version."
    ), "name": "05_shots"},

    # 6. Render queue (48-61s, 13s) — from video C (07-13-00, 0-13s)
    {"start": 48, "dur": 13, "text": (
        "The Film Bible is injected as structured context into every generation call. "
        "Veo 3.1 for video. Chirp 3 for voiceover. Lyria 2 for score."
    ), "name": "06_render"},

    # 7. Drift + regeneration (61-84s, 23s) — from video D (07-23-28, 0-23s)
    {"start": 61, "dur": 23, "text": (
        "The Consistency Check Agent scores every shot. Face, age, beard, wardrobe. "
        "When drift exceeds the threshold, the system regenerates with the drift report "
        "injected as corrective context. Prior score zero point eight five. "
        "After regeneration zero point nine zero. The loop is closed."
    ), "name": "07_drift"},

    # 8. Assembly (84-88s, 4s) — from video E (07-25-34, 0-4s)
    {"start": 84, "dur": 4, "text": (
        "The shots are assembled into a final film."
    ), "name": "08_assembly"},

    # 9. Final film plays (88-117s, 29s) — from video E (07-25-34, 4-33s)
    # Narration fills the whole 29s (no silence)
    {"start": 88, "dur": 29, "text": (
        "Same character. Same world. Same voice. Same score. Same style. "
        "Across every shot. This is the project that made an AI film look like "
        "the same film, because one agent remembered all of it. "
        "The character walks the lamp room. He discovers a bottle. "
        "He reads the message. He looks out to sea, transformed."
    ), "name": "09_film"},

    # 10. Share + closing narration (117-165s, 48s) — from video F (03-51-28, padded)
    # Narration fills the whole 48s (no silence)
    {"start": 117, "dur": 48, "text": (
        "Three agents on Google Agent Development Kit. "
        "Director orchestrates the pipeline. "
        "Research grounds creative decisions via Parallel Search. "
        "Consistency Check scores drift with Gemini Vision. "
        "The Film Bible is typed, versioned, citable. "
        "Every generation cites its Bible version. Drift is attributable. "
        "All on Google Cloud. Gemini, Veo, Chirp, Lyria, Firestore, Cloud Run. "
        "Auteur. AI cinema's memory. Grounded in reality. "
        "Consistent across every shot. Try it live."
    ), "name": "10_share"},

    # 11. Outro card (165-170s, 5s) — SILENCE
    {"start": 165, "dur": 5, "text": None, "name": "11_outro"},
]

def generate_tts(text, voice="Charon"):
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
    raise RuntimeError("no audio")

def pcm_to_wav(pcm, sr=24000):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(pcm)
    return buf.getvalue()

def get_dur(path):
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
        "-of","default=noprint_wrappers=1:nokey=1",path], capture_output=True, text=True, timeout=10)
    return float(r.stdout.strip()) if r.returncode == 0 else 0.0

def fit_segment(wav_path, target_dur, out_path):
    """Fit TTS to exact target: atempo (max 1.05x), then pad with silence or trim."""
    natural = get_dur(wav_path)
    if natural == 0:
        return 0.0
    ratio = natural / target_dur
    if ratio > 1.05:
        atempo = min(ratio, 1.05)
        subprocess.run(["ffmpeg","-y","-loglevel","error","-i",wav_path,
            "-af",f"atempo={atempo:.4f}","-c:a","pcm_s16le","-f","wav",out_path],
            check=True, timeout=30)
    elif ratio < 0.95:
        atempo = max(ratio, 0.95)
        subprocess.run(["ffmpeg","-y","-loglevel","error","-i",wav_path,
            "-af",f"atempo={atempo:.4f}","-c:a","pcm_s16le","-f","wav",out_path],
            check=True, timeout=30)
    else:
        subprocess.run(["ffmpeg","-y","-loglevel","error","-i",wav_path,
            "-c:a","pcm_s16le","-f","wav",out_path], check=True, timeout=30)

    current = get_dur(out_path)
    if current < target_dur - 0.1:
        pad = target_dur - current
        subprocess.run(["ffmpeg","-y","-loglevel","error","-i",out_path,
            "-af",f"apad=pad_dur={pad:.3f}","-c:a","pcm_s16le","-f","wav",out_path+".tmp"],
            check=True, timeout=30)
        os.replace(out_path+".tmp", out_path)
    elif current > target_dur + 0.1:
        subprocess.run(["ffmpeg","-y","-loglevel","error","-i",out_path,
            "-t",str(target_dur),"-c:a","pcm_s16le","-f","wav",out_path+".tmp"],
            check=True, timeout=30)
        os.replace(out_path+".tmp", out_path)
    return get_dur(out_path)

print("=" * 60)
print("PERFECTLY-SYNCED NARRATION v5 (Bible tabs + no silence + 2:50)")
print("=" * 60)

for seg in SEGMENTS:
    out_path = os.path.join(OUTDIR, f"{seg['name']}.wav")
    if seg["text"] is None:
        subprocess.run(["ffmpeg","-y","-loglevel","error","-f","lavfi",
            "-i",f"anullsrc=r=24000:cl=mono","-t",str(seg['dur']),
            "-c:a","pcm_s16le","-f","wav",out_path], check=True, timeout=10)
        print(f"  {seg['name']}: {seg['dur']}s SILENCE")
    else:
        pcm = generate_tts(seg["text"])
        wav = pcm_to_wav(pcm)
        raw_path = out_path + ".raw.wav"
        with open(raw_path, "wb") as f:
            f.write(wav)
        natural = get_dur(raw_path)
        final = fit_segment(raw_path, seg["dur"], out_path)
        os.unlink(raw_path)
        print(f"  {seg['name']}: {seg['dur']}s target, {natural:.1f}s natural -> {final:.1f}s final")

# Concatenate
print("\n[concat] Building full audio track...")
concat_list = os.path.join(OUTDIR, "concat.txt")
with open(concat_list, "w") as f:
    for seg in SEGMENTS:
        f.write(f"file '{OUTDIR}/{seg['name']}.wav'\n")

full_path = os.path.join(OUTDIR, "full_narration_v5.wav")
subprocess.run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0",
    "-i",concat_list,"-c","copy",full_path], check=True, timeout=30)
total = get_dur(full_path)
print(f"  total: {total:.3f}s (target 170.000s)")

# Pad to exactly 170
if total < 170.0 - 0.01:
    pad = 170.0 - total
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i",full_path,
        "-af",f"apad=pad_dur={pad:.3f}","-c:a","pcm_s16le","-f","wav",full_path+".tmp"],
        check=True, timeout=30)
    os.replace(full_path+".tmp", full_path)
    print(f"  padded to: {get_dur(full_path):.3f}s")

# Stereo 48k
stereo_path = os.path.join(OUTDIR, "full_narration_v5_stereo.wav")
subprocess.run(["ffmpeg","-y","-loglevel","error","-i",full_path,
    "-ar","48000","-ac","2","-c:a","pcm_s16le",stereo_path], check=True, timeout=30)
print(f"  stereo: {get_dur(stereo_path):.3f}s")
