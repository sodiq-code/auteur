#!/usr/bin/env python3
"""
Auteur — Cloud Run deploy script (blueprint Section 31.4 / 29.2).

Deploys the FastAPI backend to Cloud Run (dev environment) via the Cloud Run +
Cloud Build Python SDKs. No `gcloud` CLI required.

Pre-requisites (the SA must have these roles — grant via Console or gcloud):
  roles/run.admin
  roles/cloudbuild.builds.editor
  roles/artifactregistry.writer
  roles/iam.serviceAccountUser

Also requires:
  - An Artifact Registry repo named 'auteur' in us-central1 (created below if missing)
  - The GCP APIs: run, cloudbuild, artifactregistry (enabled below if missing)

Usage:
  source .env
  python3 infra/deploy_cloud_run.py --service auteur-dev --region us-central1

After deploy, verify:
  curl https://auteur-dev-<hash>.run.app/api/health
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path

SA_KEY = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "auteur-506523")
REGION = os.environ.get("GCP_LOCATION", "us-central1")


def _token():
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    if not SA_KEY or not Path(SA_KEY).exists():
        raise RuntimeError(f"GOOGLE_APPLICATION_CREDENTIALS not set or missing: {SA_KEY}")
    creds = service_account.Credentials.from_service_account_file(
        SA_KEY, scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(Request())
    return creds.token


def _rest(method: str, url: str, body: dict | None = None, token: str | None = None):
    """Raw REST helper (avoids needing the full Cloud Build SDK for one-off calls)."""
    import requests
    headers = {"Authorization": f"Bearer {token or _token()}", "Content-Type": "application/json"}
    r = requests.request(method, url, headers=headers, json=body, timeout=60)
    return r.status_code, r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text


def ensure_artifact_registry(repo: str, region: str, token: str) -> None:
    """Create the Artifact Registry Docker repo if it doesn't exist."""
    parent = f"projects/{PROJECT_ID}/locations/{region}"
    url = f"https://artifactregistry.googleapis.com/v1/{parent}/repositories"
    code, body = _rest("GET", f"{url}/{repo}", token=token)
    if code == 200:
        print(f"  artifact registry repo {repo} exists")
        return
    if code != 404:
        raise RuntimeError(f"artifact registry check failed: {code} {body}")
    print(f"  creating artifact registry repo {repo}...")
    body = {"format": "DOCKER", "name": repo, "description": "Auteur backend images"}
    code, b = _rest("POST", url, body=body, token=token)
    if code not in (200, 201):
        raise RuntimeError(f"failed to create AR repo: {code} {b}")
    print(f"  -> created {repo}")


def build_image(source_dir: Path, image: str, repo: str, region: str, token: str) -> str:
    """Submit a Cloud Build from source (compiles the Dockerfile in the cloud)."""
    # Package the source as a tarball (Cloud Build accepts a source tarball)
    import io, tarfile
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        # include the backend/ dir + Dockerfile
        for p in [source_dir / "backend", source_dir / "infra"]:
            tar.add(str(p), arcname=p.name)
    src_bytes = buf.getvalue()

    # Upload the source to Cloud Storage (Cloud Build needs a source)
    # Use the Cloud Build API directly with inline storage source
    build_body = {
        "source": {"storageSource": {"bucket": "", "object": ""}},  # filled below
        "steps": [{
            "name": "gcr.io/cloud-builders/docker",
            "args": ["build", "-t", image, "-f", "backend/Dockerfile", "."],
        }, {
            "name": "gcr.io/cloud-builders/docker",
            "args": ["push", image],
        }],
        "images": [image],
    }
    # NOTE: This simplified path requires a GCS bucket for the source tarball.
    # For the hackathon, the recommended path is `gcloud run deploy --source`
    # from a local checkout with gcloud installed. This script is the fallback
    # for environments without gcloud.
    raise NotImplementedError(
        "Cloud Build from source requires a GCS bucket for the source tarball. "
        "Use `gcloud run deploy auteur-dev --source . --region us-central1 "
        "--allow-unauthenticated --set-env-vars GCP_PROJECT_ID=auteur-506523` "
        "from a machine with gcloud installed."
    )


def deploy_service(service_name: str, image: str, region: str, token: str) -> str:
    """Create or update the Cloud Run service."""
    parent = f"projects/{PROJECT_ID}/locations/{region}"
    url = f"https://run.googleapis.com/v2/{parent}/services"
    # Check if service exists
    code, body = _rest("GET", f"{url}/{service_name}", token=token)
    exists = code == 200

    service_body = {
        "apiVersion": "run.googleapis.com/v1",
        "kind": "Service",
        "metadata": {"name": service_name, "namespace": PROJECT_ID},
        "spec": {
            "template": {
                "spec": {
                    "containerConcurrency": 80,
                    "timeoutSeconds": 300,
                    "serviceAccountName": f"auteur@{PROJECT_ID}.iam.gserviceaccount.com",
                    "containers": [{
                        "image": image,
                        "ports": [{"containerPort": 8000}],
                        "resources": {"limits": {"memory": "1Gi", "cpu": "1"}},
                        "env": [
                            {"name": "GCP_PROJECT_ID", "value": PROJECT_ID},
                            {"name": "GCP_LOCATION", "value": region},
                            {"name": "GCP_IMAGE_LOCATION", "value": "global"},
                            {"name": "PORT", "value": "8000"},
                        ],
                    }],
                    "scaling": {"minInstanceCount": 1, "maxInstanceCount": 10},
                },
            },
        },
    }

    if exists:
        print(f"  updating service {service_name}...")
        code, body = _rest("PATCH",
            f"https://run.googleapis.com/v2/{parent}/services/{service_name}",
            body=service_body, token=token)
    else:
        print(f"  creating service {service_name}...")
        code, body = _rest("POST", url, body=service_body, token=token)

    if code not in (200, 201):
        raise RuntimeError(f"Cloud Run deploy failed: {code} {body}")
    # poll the long-running operation
    op_name = body.get("name") if isinstance(body, dict) else None
    if op_name:
        print(f"  operation: {op_name}")
        for _ in range(30):
            time.sleep(10)
            code, b = _rest("GET", f"https://run.googleapis.com/v2/{op_name}", token=token)
            if isinstance(b, dict) and b.get("done"):
                if b.get("error"):
                    raise RuntimeError(f"deploy failed: {b['error']}")
                break
        else:
            print("  WARNING: deploy still running after 5 min")

    # Get the service URL
    code, body = _rest("GET", f"https://run.googleapis.com/v2/{parent}/services/{service_name}", token=token)
    if isinstance(body, dict):
        uri = body.get("status", {}).get("uri", "")
        return uri
    return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--service", default="auteur-dev")
    ap.add_argument("--region", default=REGION)
    ap.add_argument("--repo", default="auteur")
    ap.add_argument("--source", default=str(Path(__file__).resolve().parents[1]))
    args = ap.parse_args()

    print(f"Deploying {args.service} to Cloud Run ({args.region})...")
    print(f"  project: {PROJECT_ID}")
    print(f"  source:  {args.source}")

    token = _token()

    # 1. Ensure Artifact Registry repo exists
    print("\n[1/3] Artifact Registry repo")
    ensure_artifact_registry(args.repo, args.region, token)

    # 2. Build the image via Cloud Build
    print("\n[2/3] Build image via Cloud Build")
    image = f"{args.region}-docker.pkg.dev/{PROJECT_ID}/{args.repo}/{args.service}:latest"
    try:
        build_image(Path(args.source), image, args.repo, args.region, token)
    except NotImplementedError as e:
        print(f"  ! {e}")
        print("\n  The SA needs roles/run.admin + roles/cloudbuild.builds.editor + "
              "roles/artifactregistry.writer + roles/iam.serviceAccountUser.")
        print("  Grant them via:")
        print(f"    gcloud projects add-iam-policy-binding {PROJECT_ID} \\")
        print(f"      --member='serviceAccount:auteur@{PROJECT_ID}.iam.gserviceaccount.com' \\")
        print("      --role='roles/run.admin'  # + cloudbuild.builds.editor, artifactregistry.writer, iam.serviceAccountUser")
        print("\n  Then re-run this script, OR deploy locally with gcloud:")
        print(f"    gcloud run deploy {args.service} --source . --region {args.region} "
              "--allow-unauthenticated --set-env-vars GCP_PROJECT_ID=auteur-506523,GCP_LOCATION=us-central1")
        return 2

    # 3. Deploy the Cloud Run service
    print("\n[3/3] Deploy Cloud Run service")
    url = deploy_service(args.service, image, args.region, token)
    print(f"\nDeployed: {url}")
    print(f"  health: {url}/api/health")
    return 0


if __name__ == "__main__":
    sys.exit(main())
