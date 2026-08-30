#!/usr/bin/env python3
"""
Generate the 3-minute demo voiceover as a SINGLE continuous narration
(not 11 separate segments). The narration flows naturally — no abrupt cuts,
no atempo speedup. Generated in 2 chunks (TTS output limit), concatenated
with a natural crossfade.

Then the video timeline is built to MATCH the narration's natural timing.
"""
import os, sys, time, wave, io, subprocess, json
from google import genai
from google.genai import types

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/home/z/my-project/auteur-sa-key.json'
client = genai.Client(vertexai=True, project='auteur-506523', location='us-central1')

OUTDIR = "/home/z/my-project/demo-voiceover-v2"
os.makedirs(OUTDIR, exist_ok=True)

# The full narration script — ONE continuous piece, split into 2 chunks for TTS
# Chunk 1: Hook + Problem + Solution + Bible + Research + Render (~90s)
# Chunk 2: Drift + Regeneration + Technical + Closing (~80s)

CHUNK_1 = """AI cinema's biggest unsolved problem is not video quality. It is consistency. Veo 3.1 produces gorgeous individual clips, but every shot is an isolated lottery. Characters drift. Wardrobes mutate. Voices lose continuity. The result looks like four different films stitched together, not one film.

Meet Auteur — AI cinema's memory. Grounded in reality. Consistent across every shot.

The filmmaker writes one logline. The Director Agent researches it via Parallel Search at runtime, grounding every creative decision in real-world references — era, location, fashion, music, lighting. Then Gemini 3.1 Pro synthesizes a typed, versioned Film Bible: characters, locations, wardrobes, voice profiles, score motifs, style anchors, and story beats. Every claim traces to a real URL.

The Film Bible is then injected as structured context into every generation call. Veo 3.1 for video. Chirp 3 for voiceover. Lyria 2 for score. The same character reference, the same wardrobe, the same voice profile, the same score motif — across every shot. Consistency is enforced by the architecture, not requested by the prompt.
"""

CHUNK_2 = """The Consistency Check Agent scores every shot against the character reference. Face identity, age appearance, beard, wardrobe — each dimension scored zero to one. When drift exceeds the threshold, the system regenerates with the drift report injected as corrective context. The prior generation scored zero point eight five on face identity. The regeneration received the drift diagnosis. The new score: zero point nine zero. The loop is closed.

Three agents on Google Agent Development Kit. Director orchestrates. Research grounds via Parallel Search. Consistency Check scores drift with Gemini Vision. The Film Bible is typed, versioned, citable. Every generation cites its Bible version. Drift is attributable. All on Google Cloud — Gemini, Veo, Chirp, Lyria, Firestore, Cloud Run.

Same character. Same world. Same voice. Same score. Same style. Across every shot. This is the project that made an AI film look like the same film. Auteur — AI cinema's memory. Grounded in reality. Consistent across every shot. Try it live.
"""

def generate_tts(text: str, voice: str = "Charon") -> bytes:
    """Generate TTS, return raw PCM (24kHz mono 16-bit)."""
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

def get_duration(path: str) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, timeout=10,
    )
    return float(r.stdout.strip()) if r.returncode == 0 else 0.0

def to_stereo_48k(wav_path: str, out_path: str) -> float:
    """Convert to stereo 48kHz WAV (for final mux with video)."""
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", wav_path,
        "-ar", "48000", "-ac", "2",
        "-c:a", "pcm_s16le",
        out_path,
    ], check=True, timeout=30)
    return get_duration(out_path)

print("=" * 60)
print("GENERATING CONTINUOUS NARRATION (Charon voice, natural pace)")
print("=" * 60)

# Generate chunk 1
print("\n[1/2] Generating chunk 1 (Hook + Problem + Solution + Bible + Research + Render)...")
pcm1 = generate_tts(CHUNK_1)
wav1 = pcm_to_wav(pcm1)
chunk1_path = os.path.join(OUTDIR, "chunk1.wav")
with open(chunk1_path, "wb") as f:
    f.write(wav1)
dur1 = get_duration(chunk1_path)
print(f"  chunk 1: {dur1:.1f}s ({len(pcm1)} bytes PCM)")

# Generate chunk 2
print("\n[2/2] Generating chunk 2 (Drift + Regeneration + Technical + Closing)...")
pcm2 = generate_tts(CHUNK_2)
wav2 = pcm_to_wav(pcm2)
chunk2_path = os.path.join(OUTDIR, "chunk2.wav")
with open(chunk2_path, "wb") as f:
    f.write(wav2)
dur2 = get_duration(chunk2_path)
print(f"  chunk 2: {dur2:.1f}s ({len(pcm2)} bytes PCM)")

# Concatenate naturally (no atempo, no padding — just natural flow)
print("\n[concat] Concatenating chunks naturally...")
concat_list = os.path.join(OUTDIR, "concat_list.txt")
with open(concat_list, "w") as f:
    f.write(f"file '{chunk1_path}'\n")
    f.write(f"file '{chunk2_path}'\n")

full_path = os.path.join(OUTDIR, "full_narration_raw.wav")
subprocess.run([
    "ffmpeg", "-y", "-loglevel", "error",
    "-f", "concat", "-safe", "0",
    "-i", concat_list,
    "-c", "copy",
    full_path,
], check=True, timeout=30)
total_dur = get_duration(full_path)
print(f"  total narration: {total_dur:.1f}s")

# Now we need the narration to fit within the 180s video timeline.
# The intro card is 5s (silence), then narration starts, then outro card is 5s (silence at end).
# So narration needs to fit in 170s.
# If natural narration is longer, apply a GENTLE atempo (max 1.05x — the user's requested pace).
# If shorter, pad with silence at the end (before the outro card).

INTRO_DUR = 5.0  # seconds of intro card (silence)
OUTRO_DUR = 5.0  # seconds of outro card (silence)
TARGET_NARRATION = 180.0 - INTRO_DUR - OUTRO_DUR  # 170s

print(f"\n[adjust] Target narration duration: {TARGET_NARRATION:.1f}s (within {INTRO_DUR}s intro + {OUTRO_DUR}s outro)")

if total_dur > TARGET_NARRATION + 2:
    # Need to speed up slightly (max 1.05x as requested)
    ratio = total_dur / TARGET_NARRATION
    atempo = min(ratio, 1.05)  # cap at 1.05x as the user requested
    print(f"  natural duration {total_dur:.1f}s > target {TARGET_NARRATION:.1f}s")
    print(f"  applying atempo={atempo:.4f} (capped at 1.05x)")
    adjusted_path = os.path.join(OUTDIR, "narration_adjusted.wav")
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", full_path,
        "-af", f"atempo={atempo:.4f}",
        "-c:a", "pcm_s16le",
        adjusted_path,
    ], check=True, timeout=30)
    narr_dur = get_duration(adjusted_path)
    print(f"  adjusted duration: {narr_dur:.1f}s")
elif total_dur < TARGET_NARRATION - 2:
    # Narration is shorter — pad with silence at the end
    pad = TARGET_NARRATION - total_dur
    print(f"  natural duration {total_dur:.1f}s < target {TARGET_NARRATION:.1f}s")
    print(f"  padding with {pad:.1f}s of silence at end")
    adjusted_path = os.path.join(OUTDIR, "narration_adjusted.wav")
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", full_path,
        "-af", f"apad=pad_dur={pad:.3f}",
        "-c:a", "pcm_s16le",
        adjusted_path,
    ], check=True, timeout=30)
    narr_dur = get_duration(adjusted_path)
    print(f"  padded duration: {narr_dur:.1f}s")
else:
    # Natural duration is close enough — use as-is
    print(f"  natural duration {total_dur:.1f}s is close to target {TARGET_NARRATION:.1f}s — using as-is")
    adjusted_path = full_path
    narr_dur = total_dur

# Now build the full audio track: 5s silence (intro) + narration + 5s silence (outro)
print(f"\n[build] Building full audio track: {INTRO_DUR}s silence + {narr_dur:.1f}s narration + {OUTRO_DUR}s silence")

# Create 5s of silence
silence_path = os.path.join(OUTDIR, "silence_5s.wav")
subprocess.run([
    "ffmpeg", "-y", "-loglevel", "error",
    "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
    "-t", str(INTRO_DUR),
    "-c:a", "pcm_s16le",
    silence_path,
], check=True, timeout=10)

silence_outro = os.path.join(OUTDIR, "silence_outro.wav")
outro_silence_dur = 180.0 - INTRO_DUR - narr_dur
print(f"  outro silence: {outro_silence_dur:.1f}s")
subprocess.run([
    "ffmpeg", "-y", "-loglevel", "error",
    "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
    "-t", f"{outro_silence_dur:.3f}",
    "-c:a", "pcm_s16le",
    silence_outro,
], check=True, timeout=10)

# Concatenate: silence_intro + narration + silence_outro
full_audio_list = os.path.join(OUTDIR, "full_audio_list.txt")
with open(full_audio_list, "w") as f:
    f.write(f"file '{silence_path}'\n")
    f.write(f"file '{adjusted_path}'\n")
    f.write(f"file '{silence_outro}'\n")

full_audio_path = os.path.join(OUTDIR, "full_narration_v2.wav")
subprocess.run([
    "ffmpeg", "-y", "-loglevel", "error",
    "-f", "concat", "-safe", "0",
    "-i", full_audio_list,
    "-c", "copy",
    full_audio_path,
], check=True, timeout=30)

final_audio_dur = get_duration(full_audio_path)
print(f"\n  FULL AUDIO: {final_audio_dur:.3f}s (target 180.000s)")

# Convert to stereo 48k for final mux
stereo_path = os.path.join(OUTDIR, "full_narration_stereo.wav")
to_stereo_48k(full_audio_path, stereo_path)
print(f"  STEREO 48k: {get_duration(stereo_path):.3f}s")

# Save the timing info for the video assembly
timing = {
    "intro_duration": INTRO_DUR,
    "narration_start": INTRO_DUR,
    "narration_duration": narr_dur,
    "narration_end": INTRO_DUR + narr_dur,
    "outro_start": INTRO_DUR + narr_dur,
    "outro_duration": outro_silence_dur,
    "total": final_audio_dur,
}
timing_path = os.path.join(OUTDIR, "timing.json")
with open(timing_path, "w") as f:
    json.dump(timing, f, indent=2)
print(f"\n  timing saved to {timing_path}")
print(json.dumps(timing, indent=2))
