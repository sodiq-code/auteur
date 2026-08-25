"""
Auteur — Gemini LLM client (blueprint Section 25, the Director + Consistency agent).

Model selection (see docs/validation-day-1-report.md):
  - gemini-3.1-pro-preview (global region) — Director Agent reasoning + vision
  - gemini-2.5-flash (us-central1) — Research synthesis (faster, cheaper)

All 3.x Gemini models are only accessible in the `global` region on this project.
"""
from __future__ import annotations

import json
import os
from typing import Any

from google import genai
from google.genai import types

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "auteur-506523")
PRO_REGION = "global"        # gemini-3.1-pro-preview
FLASH_REGION = "us-central1"  # gemini-2.5-flash

_PRO_CLIENT = None
_FLASH_CLIENT = None


def _pro_client():
    global _PRO_CLIENT
    if _PRO_CLIENT is None:
        _PRO_CLIENT = genai.Client(vertexai=True, project=PROJECT_ID, location=PRO_REGION)
    return _PRO_CLIENT


def _flash_client():
    global _FLASH_CLIENT
    if _FLASH_CLIENT is None:
        _FLASH_CLIENT = genai.Client(vertexai=True, project=PROJECT_ID, location=FLASH_REGION)
    return _FLASH_CLIENT


async def pro_generate(
    prompt: str,
    response_mime_type: str | None = None,
    temperature: float = 0.4,
    images: list[bytes] | None = None,
) -> str:
    """Gemini 3.1 Pro (global) — Director Agent reasoning + vision (blueprint Table 31)."""
    cfg_kwargs: dict[str, Any] = {"temperature": temperature}
    if response_mime_type:
        cfg_kwargs["response_mime_type"] = response_mime_type
    cfg = types.GenerateContentConfig(**cfg_kwargs)

    if images:
        # multimodal vision call
        parts = [types.Part.from_bytes(data=b, mime_type="image/png") for b in images]
        contents = [prompt] + parts
    else:
        contents = prompt

    resp = await _pro_client().aio.models.generate_content(
        model="gemini-3.1-pro-preview", contents=contents, config=cfg,
    )
    return resp.text or ""


async def pro_generate_json(prompt: str, temperature: float = 0.4) -> dict[str, Any]:
    """Gemini 3.1 Pro with JSON output schema."""
    text = await pro_generate(prompt, response_mime_type="application/json", temperature=temperature)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"_raw": text}


async def flash_synthesize(prompt: str, temperature: float = 0.3) -> str:
    """Gemini 2.5 Flash (us-central1) — Research synthesis (blueprint Table 34 row 2)."""
    cfg = types.GenerateContentConfig(temperature=temperature)
    resp = await _flash_client().aio.models.generate_content(
        model="gemini-2.5-flash", contents=prompt, config=cfg,
    )
    return resp.text or ""
