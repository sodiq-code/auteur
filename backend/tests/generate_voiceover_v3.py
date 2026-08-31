#!/usr/bin/env python3
"""
Generate perfectly-synced narration: each video segment gets its own TTS
segment calibrated to fill that segment's exact duration. No long silences,
no narration talking about the Bible while the landing page is showing.
"""
import os, sys, time, wave, io, subprocess, json
from google import genai
from google.genai import types

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/home/z/my-project/auteur-sa-key.json'
client = genai.Client(vertexai=True, project='auteur-506523', location='us-central1')

OUTDIR = "/home/z/my-project/demo-voiceover-v3"
os.makedirs(OUTDIR, exist_ok=True)

# Each segment: start time, duration, narration text
# The text is calibrated to naturally fill the duration at Charon's pace (~130 wpm)
SEGMENTS = [
    # 1. Intro card (0-5s) — SILENCE
    {"start": 0, "dur": 5, "text": None, "name": "01_intro"},

    # 2. Landing (5-23s, 18s) — hook + problem
    {"start": 5, "dur": 18, "text": "AI cinema's biggest unsolved problem is not video quality. It is consistency. Veo 3.1 produces gorgeous individual clips, but every shot is an isolated lottery. Characters drift. Wardrobes mutate. The result looks like four different films stitched together, not one film.", "name": "02_landing"},

    # 3. Research (23-38s, 15s) — Parallel Search visible
    {"start": 23, "dur": 15, "text": "The filmmaker writes one logline. The Director Agent researches it via Parallel Search at runtime, grounding every creative decision in real-world references. Era, location, fashion, music, lighting. Every search result is shown with its source URL.", "name": "03_research"},

    # 4. Bible view (38-53s, 15s) — tabs visible
    {"start": 38, "dur": 15, "text": "Then Gemini 3.1 Pro synthesizes a typed, versioned Film Bible. Characters, locations, wardrobes, voice profiles, score motifs, style anchors, and story beats. Every claim traces to a real URL.", "name": "04_bible"},

    # 5. Shots (53-63s, 10s) — shot list
    {"start": 53, "dur": 10, "text": "The Bible generates a shot list. Four shots, each citing the Bible version that produced it.", "name": "05_shots"},

    # 6. Render (63-78s, 15s) — Veo/Chirp/Lyria
    {"start": 63, "dur": 15, "text": "The Film Bible is injected as structured context into every generation call. Veo 3.1 for video. Chirp 3 for voiceover. Lyria 2 for score. The same character, the same wardrobe, the same world, across every shot.", "name": "06_render"},

    # 7. Drift + regeneration (78-103s, 25s) — the agentic loop
    {"start": 78, "dur": 25, "text": "The Consistency Check Agent scores every shot against the character reference. Face, age, beard, wardrobe. When drift exceeds the threshold, the system regenerates with the drift report injected as corrective context. Prior score: zero point eight five. After regeneration: zero point nine zero. The loop is closed.", "name": "07_drift"},

    # 8. Assembly (103-108s, 5s) — brief transition
    {"start": 103, "dur": 5, "text": "The shots are assembled into a final film.", "name": "08_assembly"},

    # 9. Final film (108-145s, 37s) — the film plays
    {"start": 108, "dur": 37, "text": "Same character. Same world. Same voice. Same score. Same style. Across every shot. This is the project that made an AI film look like the same film, because one agent remembered all of it.", "name": "09_film"},

    # 10. Share (145-175s, 30s) — closing narration
    {"start": 145, "dur": 30, "text": "Three agents on Google Agent Development Kit. Director orchestrates. Research grounds via Parallel Search. Consistency Check scores drift with Gemini Vision. The Film Bible is typed, versioned, citable. Every generation cites its Bible version. All on Google Cloud. Auteur. AI cinema's memory. Grounded in reality. Consistent across every shot. Try it live.", "name": "10_share"},

    # 11. Outro card (175-180s, 5s) — SILENCE
    {"start": 175, "dur": 5, "text": None, "name": "11_outro"},
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
    """Fit a TTS segment to exactly target_dur: atempo if needed, then pad with silence."""
    natural = get_dur(wav_path)
    if natural == 0:
        return 0.0

    # If natural is within 1.05x of target, use atempo (max 1.05x as requested)
    ratio = natural / target_dur
    if 0.95 <= ratio <= 1.05:
        # Close enough — just pad/trim
        pass
    elif ratio > 1.05:
        # Too long — speed up (max 1.05x)
        atempo = min(ratio, 1.05)
        subprocess.run(["ffmpeg","-y","-loglevel","error","-i",wav_path,
            "-af",f"atempo={atempo:.4f}","-c:a","pcm_s16le","-f","wav",out_path],
            check=True, timeout=30)
    elif ratio < 0.95:
        # Too short — slow down slightly (min 0.95x to stay natural)
        atempo = max(ratio, 0.95)
        subprocess.run(["ffmpeg","-y","-loglevel","error","-i",wav_path,
            "-af",f"atempo={atempo:.4f}","-c:a","pcm_s16le","-f","wav",out_path],
            check=True, timeout=30)
    else:
        # Copy as-is
        subprocess.run(["ffmpeg","-y","-loglevel","error","-i",wav_path,
            "-c:a","pcm_s16le","-f","wav",out_path], check=True, timeout=30)

    # Now pad with silence to exactly target
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
print("PERFECTLY-SYNCED NARRATION (per-segment TTS)")
print("=" * 60)

# Generate each segment
for seg in SEGMENTS:
    out_path = os.path.join(OUTDIR, f"{seg['name']}.wav")

    if seg["text"] is None:
        # Silence segment
        subprocess.run(["ffmpeg","-y","-loglevel","error",
            "-f","lavfi","-i",f"anullsrc=r=24000:cl=mono",
            "-t",str(seg["dur"]),"-c:a","pcm_s16le","-f","wav",out_path],
            check=True, timeout=10)
        print(f"  {seg['name']}: {seg['dur']}s SILENCE")
    else:
        # Generate TTS
        pcm = generate_tts(seg["text"])
        wav = pcm_to_wav(pcm)
        raw_path = out_path + ".raw.wav"
        with open(raw_path, "wb") as f:
            f.write(wav)
        natural = get_dur(raw_path)

        # Fit to exact duration
        final = fit_segment(raw_path, seg["dur"], out_path)
        os.unlink(raw_path)
        print(f"  {seg['name']}: {seg['dur']}s target, {natural:.1f}s natural -> {final:.1f}s final")

# Concatenate all segments in order
print("\n[concat] Building full audio track...")
concat_list = os.path.join(OUTDIR, "concat.txt")
with open(concat_list, "w") as f:
    for seg in SEGMENTS:
        f.write(f"file '{OUTDIR}/{seg['name']}.wav'\n")

full_path = os.path.join(OUTDIR, "full_narration_v3.wav")
subprocess.run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0",
    "-i",concat_list,"-c","copy",full_path], check=True, timeout=30)
total = get_dur(full_path)
print(f"  total: {total:.3f}s (target 180.000s)")

# Convert to stereo 48k
stereo_path = os.path.join(OUTDIR, "full_narration_v3_stereo.wav")
subprocess.run(["ffmpeg","-y","-loglevel","error","-i",full_path,
    "-ar","48000","-ac","2","-c:a","pcm_s16le",stereo_path], check=True, timeout=30)
print(f"  stereo 48k: {get_dur(stereo_path):.3f}s")

# Save timing
timing = [{"name": s["name"], "start": s["start"], "dur": s["dur"], "text": s["text"][:60] if s["text"] else "SILENCE"} for s in SEGMENTS]
with open(os.path.join(OUTDIR, "timing.json"), "w") as f:
    json.dump(timing, f, indent=2)
print("\nTiming:")
for t in timing:
    print(f"  {t['start']:3d}s-{t['start']+t['dur']:3d}s ({t['dur']:2d}s) {t['name']}: {t['text']}")
