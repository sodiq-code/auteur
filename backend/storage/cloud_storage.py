"""
Auteur — Cloud Storage wrapper for rendered artifacts (blueprint Table 28 row 3).

Renders (Veo MP4s, Chirp WAVs, Lyria WAVs, Imagen PNGs) are stored in Cloud
Storage, not Firestore (they're too large + binary). Public share links read
from this bucket.
"""
from __future__ import annotations

import os
from typing import Optional

RENDERS_BUCKET = os.environ.get("GCS_RENDERS_BUCKET", "gs://auteur-renders")
DEMO_BUCKET = os.environ.get("GCS_DEMO_BUCKET", "gs://auteur-demo")

_CLIENT = None


def _client():
    global _CLIENT
    if _CLIENT is None:
        from google.cloud import storage
        _CLIENT = storage.Client(project=os.environ.get("GCP_PROJECT_ID", "auteur-506523"))
    return _CLIENT


def _bucket_name(uri: str) -> str:
    return uri.replace("gs://", "").split("/", 1)[0]


def _object_name(uri: str) -> str:
    parts = uri.replace("gs://", "").split("/", 1)
    return parts[1] if len(parts) > 1 else ""


def upload_bytes(blob_name: str, data: bytes, bucket: Optional[str] = None,
                 content_type: str = "application/octet-stream") -> str:
    """Upload bytes to Cloud Storage, return the gs:// URI."""
    target = bucket or RENDERS_BUCKET
    client = _client()
    b = client.bucket(_bucket_name(target))
    blob = b.blob(f"{blob_name}")
    blob.upload_from_string(data, content_type=content_type)
    return f"gs://{_bucket_name(target)}/{blob_name}"


def make_public_url(gs_uri: str) -> str:
    """Convert a gs:// URI to its public-read URL (object must be public-read)."""
    name = _bucket_name(gs_uri)
    obj = _object_name(gs_uri)
    return f"https://storage.googleapis.com/{name}/{obj}"
