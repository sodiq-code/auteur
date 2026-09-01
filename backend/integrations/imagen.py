"""
Auteur — image generation client.

Model: gemini-3-pro-image (Imagen 3 deprecated on the project; gemini-3-pro-image
is the newest accessible Google Cloud image model — Pro tier, 3.x generation).
ONLY accessible in the `global` region (404s in us-central1).

Used for:
  - character reference images (the ASSET reference for Veo cross-shot consistency)
  - storyboard previews (Day 7+)
"""
from __future__ import annotations

import os
from typing import Optional

from google import genai
from google.genai import types

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "auteur-506523")
IMAGE_REGION = "global"
IMAGE_MODEL = "gemini-3-pro-image"

_CLIENT = None


def _client():
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = genai.Client(vertexai=True, project=PROJECT_ID, location=IMAGE_REGION)
    return _CLIENT


async def generate_image(prompt: str) -> bytes:
    """Generate a single image and return the PNG bytes."""
    resp = await _client().aio.models.generate_content(
        model=IMAGE_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
    )
    for cand in resp.candidates or []:
        for part in (cand.content.parts if cand.content else []):
            inline = getattr(part, "inline_data", None)
            if inline and inline.data:
                return inline.data
    raise RuntimeError("image model returned no image")
