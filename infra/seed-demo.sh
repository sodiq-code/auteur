#!/usr/bin/env bash
# seed-demo.sh — pre-render the canonical 4-shot demo (blueprint Section 28.3 / Day 11).
# Runs the Day-1 validation pipeline with the canonical lighthouse-keeper logline
# and uploads the artifacts to the GCS demo bucket so the deployed app can load
# them by default (the demo-day safety net).
#
# Usage: GCS_DEMO_BUCKET=gs://auteur-demo bash infra/seed-demo.sh
set -euo pipefail

: "${GCP_PROJECT_ID:=auteur-506523}"
: "${GCP_LOCATION:=us-central1}"
: "${GCS_DEMO_BUCKET:?GCS_DEMO_BUCKET is required (e.g. gs://auteur-demo)}"

echo "==> Pre-rendering canonical 4-shot demo (Day 11 deliverable, invoked early as safety net)..."
python3 backend/validation/day1_validate_consistency.py

echo "==> Uploading demo artifacts to ${GCS_DEMO_BUCKET}/..."
gcloud storage cp backend/validation/outputs/character_reference.png "${GCS_DEMO_BUCKET}/character_reference.png"
gcloud storage cp backend/validation/outputs/shot_*.mp4 "${GCS_DEMO_BUCKET}/"
gcloud storage cp backend/validation/outputs/day1-manifest.json "${GCS_DEMO_BUCKET}/manifest.json"
gcloud storage cp docs/validation-day-1.png "${GCS_DEMO_BUCKET}/side-by-side.png"

echo "==> Demo seeded. Deployed app should load ${GCS_DEMO_BUCKET}/side-by-side.png by default."
