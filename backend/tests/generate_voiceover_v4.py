#!/usr/bin/env python3
"""
Generate perfectly-synced narration v4:
- 0-39s: ONE continuous narration piece (no cuts between landing/research/bible)
- Video ends at 2:50 (170s) with outro card moved forward
- Every second matches: narration talks about what's on screen
"""
import os, sys, time, wave, io, subprocess, json
from google import genai
from google.genai import types

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/home/z/my-project/auteur-sa-key.json'
client = genai.Client(vertexai=True, project='auteur-506523', location='us-central1')

OUTDIR = "/home/z/my-project/demo-voiceover-v4"
os.makedirs(OUTDIR, exist_ok=True)

# VIDEO TIMELINE (ends at 170s = 2:50):
# 0-5s:    Intro card (SILENCE)
# 5-17s:   Landing page scrolling (12s)
# 17-20s:  Logline input (3s)
# 20-28s:  Research results (8s)
# 28-41s:  Bible view with tabs (13s)
# 41-49s:  Shot list (8s)
# 49-62s:  Render queue (13s)
# 62-85s:  Drift + regeneration (23s)
# 85-89s:  Assembly (4s)
# 89-118s: Final film plays (29s)
# 118-165s: Share view + closing narration (47s)
# 165-170s: Outro card (5s, SILENCE)

SEGMENTS = [
    # 1. Intro (0-5s) — SILENCE
    {"start": 0, "dur": 5, "text": None, "name": "01_intro"},

    # 2. Landing + Logline + Research + Bible (5-41s, 36s) — ONE CONTINUOUS NARRATION
    # This flows: problem → solution → logline → research → bible — NO CUTS
    # 73 words ≈ 34s at Charon's natural pace (fits 36s)
    {"start": 5, "dur": 36, "text": (
        "AI cinema biggest unsolved problem is not video quality. It is consistency. "
        "Veo 3.1 produces gorgeous individual clips, but every shot is an isolated lottery. "
        "Characters drift. Wardrobes mutate. "
        "Meet Auteur, AI cinema memory. The filmmaker writes one logline. "
        "The Director Agent researches it via Parallel Search at runtime, "
        "grounding every creative decision in real-world references. "
        "Then Gemini 3.1 Pro synthesizes a typed, versioned Film Bible. "
        "Every claim traces to a real URL."
    ), "name": "02_flow"},

    # 3. Shots (41-49s, 8s)
    {"start": 41, "dur": 8, "text": (
        "The Bible generates a shot list. Four shots, each citing the Bible version."
    ), "name": "03_shots"},

    # 4. Render (49-62s, 13s)
    {"start": 49, "dur": 13, "text": (
        "The Film Bible is injected as structured context into every generation call. "
        "Veo 3.1 for video. Chirp 3 for voiceover. Lyria 2 for score. "
        "The same character, across every shot."
    ), "name": "04_render"},

    # 5. Drift + regeneration (62-85s, 23s)
    {"start": 62, "dur": 23, "text": (
        "The Consistency Check Agent scores every shot. Face, age, beard, wardrobe. "
        "When drift exceeds the threshold, the system regenerates with the drift report "
        "injected as corrective context. Prior score zero point eight five. "
        "After regeneration zero point nine zero. The loop is closed."
    ), "name": "05_drift"},

    # 6. Assembly (85-89s, 4s)
    {"start": 85, "dur": 4, "text": (
        "The shots are assembled into a final film."
    ), "name": "06_assembly"},

    # 7. Final film (89-118s, 29s)
    {"start": 89, "dur": 29, "text": (
        "Same character. Same world. Same voice. Same score. Same style. "
        "Across every shot. This is the project that made an AI film look like "
        "the same film, because one agent remembered all of it. "
        "The character walks the lamp room. He discovers a bottle. "
        "He reads the message. He looks out to sea, transformed."
    ), "name": "07_film"},

    # 8. Share + closing (118-165s, 47s)
    {"start": 118, "dur": 47, "text": (
        "Three agents on Google Agent Development Kit. Director orchestrates. "
        "Research grounds via Parallel Search. Consistency Check scores drift "
        "with Gemini Vision. The Film Bible is typed, versioned, citable. "
        "Every generation cites its Bible version. Drift is attributable. "
        "All on Google Cloud. "
        "Auteur. AI cinema's memory. Grounded in reality. "
        "Consistent across every shot. Try it live."
    ), "name": "08_share"},

    # 9. Outro card (165-170s, 5s) — SILENCE
    {"start": 165, "dur": 5, "text": None, "name": "09_outro"},
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
    natural = get_dur(wav_path)
    if natural == 0:
        return 0.0
    ratio = natural / target_dur
    if 0.95 <= ratio <= 1.05:
        subprocess.run(["ffmpeg","-y","-loglevel","error","-i",wav_path,
            "-c:a","pcm_s16le","-f","wav",out_path], check=True, timeout=30)
    elif ratio > 1.05:
        atempo = min(ratio, 1.05)
        subprocess.run(["ffmpeg","-y","-loglevel","error","-i",wav_path,
            "-af",f"atempo={atempo:.4f}","-c:a","pcm_s16le","-f","wav",out_path],
            check=True, timeout=30)
    else:
        atempo = max(ratio, 0.95)
        subprocess.run(["ffmpeg","-y","-loglevel","error","-i",wav_path,
            "-af",f"atempo={atempo:.4f}","-c:a","pcm_s16le","-f","wav",out_path],
            check=True, timeout=30)
    # Pad/trim to exact
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
print("PERFECTLY-SYNCED NARRATION v4 (ends at 2:50 / 170s)")
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

full_path = os.path.join(OUTDIR, "full_narration_v4.wav")
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
stereo_path = os.path.join(OUTDIR, "full_narration_v4_stereo.wav")
subprocess.run(["ffmpeg","-y","-loglevel","error","-i",full_path,
    "-ar","48000","-ac","2","-c:a","pcm_s16le",stereo_path], check=True, timeout=30)
print(f"  stereo: {get_dur(stereo_path):.3f}s")
