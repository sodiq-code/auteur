#!/usr/bin/env bash
# Auteur — Cloud Run deploy (one-command path with gcloud).
#
# This is the recommended deploy path if you have gcloud installed locally.
# The Python fallback (deploy_cloud_run.py) is for environments without gcloud.
#
# Pre-reqs:
#   1. gcloud auth login
#   2. gcloud config set project auteur-506523
#   3. gcloud auth application-default login   # for the SA
#
# Usage:
#   bash infra/deploy.sh auteur-dev us-central1
set -euo pipefail

SERVICE="${1:-auteur-dev}"
REGION="${2:-us-central1}"
PROJECT="auteur-506523"

echo "Deploying $SERVICE to Cloud Run ($REGION) on project $PROJECT..."
echo ""

# Deploy from source (Cloud Build compiles backend/Dockerfile in the cloud)
gcloud run deploy "$SERVICE" \
    --source . \
    --region "$REGION" \
    --project "$PROJECT" \
    --allow-unauthenticated \
    --min-instances 1 \
    --max-instances 10 \
    --concurrency 80 \
    --memory 1Gi \
    --cpu 1 \
    --timeout 300 \
    --service-account "auteur@${PROJECT}.iam.gserviceaccount.com" \
    --set-env-vars "GCP_PROJECT_ID=${PROJECT},GCP_LOCATION=${REGION},GCP_IMAGE_LOCATION=global,PORT=8000"

echo ""
echo "Deployed. Health check:"
SERVICE_URL=$(gcloud run services describe "$SERVICE" --region "$REGION" --format 'value(status.url)')
echo "  $SERVICE_URL/api/health"
echo ""
echo "Smoke test:"
curl -fsS "$SERVICE_URL/api/health" | jq .
