"""
Auteur — music / score client.

Model: lyria-002 (via the Vertex :predict REST endpoint, us-central1).
Needs SPECIFIC prompts — vague prompts return 500 "Could not generate audio"
(content filter). Returns a WAV (48kHz stereo, 16-bit PCM).
"""
from __future__ import annotations

import base64
import os
from typing import Any

from google.oauth2 import service_account
from google.auth.transport.requests import Request
import httpx

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "auteur-506523")
LYRIA_REGION = "us-central1"
LYRIA_MODEL = "lyria-002"

_CREDS = None


def _token() -> str:
    global _CREDENTIALS
    sa_key = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
    if sa_key and os.path.exists(sa_key):
        global _CREDS
        if _CREDS is None:
            _CREDS = service_account.Credentials.from_service_account_file(sa_key, scopes=scopes)
        if not _CREDS.valid:
            _CREDS.refresh(Request())
        return _CREDS.token
    # fallback: Application Default Credentials
    import google.auth
    creds, _ = google.auth.default(scopes=scopes)
    if not creds.valid:
        creds.refresh(Request())
    return creds.token


async def generate_score(prompt: str, timeout: float = 180.0) -> bytes:
    """Generate a score clip via Lyria 2. Returns WAV bytes (48kHz stereo).

    The prompt should be specific (instruments, mood, tempo) — vague prompts
    are rejected by the content filter with a 500.
    """
    token = _token()
    url = (f"https://{LYRIA_REGION}-aiplatform.googleapis.com/v1/projects/"
           f"{PROJECT_ID}/locations/{LYRIA_REGION}/publishers/google/models/"
           f"{LYRIA_MODEL}:predict")
    body: dict[str, Any] = {
        "instances": [{"prompt": prompt}],
        "parameters": {"sampleCount": 1},
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }, json=body)
        resp.raise_for_status()
        data = resp.json()
    preds = data.get("predictions", [])
    if not preds or "bytesBase64Encoded" not in preds[0]:
        raise RuntimeError("Lyria returned no audio")
    return base64.b64decode(preds[0]["bytesBase64Encoded"])
