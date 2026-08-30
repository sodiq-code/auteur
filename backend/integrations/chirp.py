"""
Auteur — voice / TTS client (blueprint "Chirp 3").

Model: gemini-3.1-flash-tts-preview (the Gemini 3.1 TTS model via
generate_content with response_modalities=['AUDIO'] + speech_config with a
prebuilt voice_name). us-central1 region.

Returns raw PCM (audio/L16;rate=24000, mono, 16-bit) — wrapped to WAV by the caller.
"""
from __future__ import annotations

import os
from typing import Optional

from google import genai
from google.genai import types

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "auteur-506523")
TTS_REGION = "us-central1"
TTS_MODEL = "gemini-3.1-flash-tts-preview"

_CLIENT = None


def _client():
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = genai.Client(vertexai=True, project=PROJECT_ID, location=TTS_REGION)
    return _CLIENT


async def generate_voiceover(line: str, voice_name: str = "Charon") -> bytes:
    """Generate a voiceover clip. Returns raw PCM (24kHz mono 16-bit).

    Caller wraps the PCM in a WAV container (see pipelines/assemble.py).
    """
    cfg = types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
            )
        ),
    )
    resp = await _client().aio.models.generate_content(model=TTS_MODEL, contents=line, config=cfg)
    for cand in resp.candidates or []:
        for part in (cand.content.parts if cand.content else []):
            inline = getattr(part, "inline_data", None)
            if inline and inline.data:
                return inline.data
    raise RuntimeError("TTS model returned no audio")
