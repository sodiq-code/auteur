#!/usr/bin/env python3
"""
Auteur — unified app deploy (Next.js + FastAPI on one Cloud Run service).

Builds the Dockerfile (which bundles both the Next.js standalone build + the
FastAPI backend) via Cloud Build, pushes to Artifact Registry, deploys to
Cloud Run as a single service.

Usage:
  source auteur/.env
  python3 deploy-unified.py --service auteur-app --region us-central1
"""
from __future__ import annotations

import os, sys, time, io, tarfile, json, requests
from pathlib import Path

SA_KEY = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "/home/z/my-project/auteur-sa-key.json")
PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "auteur-506523")
REGION = "us-central1"
REPO = "auteur"
BUCKET = "auteur-build-source"

def _creds():
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    c = service_account.Credentials.from_service_account_file(SA_KEY, scopes=["https://www.googleapis.com/auth/cloud-platform"])
    c.refresh(Request())
    return c

def _H():
    c = _creds()
    return {"Authorization": f"Bearer {c.token}", "Content-Type": "application/json"}

def main():
    SERVICE = "auteur-app"
    IMAGE = f"{REGION}-docker.pkg.dev/{PROJECT_ID}/{REPO}/auteur-app:v{int(time.time())}"

    print(f"Deploying {SERVICE} to Cloud Run ({REGION})...")
    H = _H()

    # 1. Upload source (the full project: Next.js + backend + Dockerfile)
    source_dir = Path("/home/z/my-project")
    print("[1/3] uploading source...")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        # include the PRE-BUILT Next.js standalone + static + public + backend + Dockerfile
        for item in [".next/standalone", ".next/static", "public", "package.json",
                          "Dockerfile", "deploy-start.sh"]:
            p = source_dir / item
            if p.exists():
                tar.add(str(p), arcname=item)
        # add the backend from auteur/backend/ as backend/
        backend_dir = source_dir / "auteur" / "backend"
        if backend_dir.exists():
            tar.add(str(backend_dir), arcname="backend")
    src_bytes = buf.getvalue()
    print(f"  tarball: {len(src_bytes):,} bytes")

    obj_name = f"unified-source-{int(time.time())}.tar.gz"
    url = f"https://storage.googleapis.com/upload/storage/v1/b/{BUCKET}/o?uploadType=media&name={obj_name}"
    r = requests.post(url, headers={"Authorization": H["Authorization"], "Content-Type": "application/gzip"},
                      data=src_bytes, timeout=300)
    if r.status_code not in (200, 201):
        print(f"  upload FAILED: {r.status_code} {r.text[:200]}")
        return 1
    gcs_uri = f"gs://{BUCKET}/{obj_name}"
    print(f"  uploaded -> {gcs_uri}")

    # 2. Submit Cloud Build
    print("[2/3] building + pushing image...")
    build_body = {
        "source": {"storageSource": {"bucket": BUCKET, "object": obj_name}},
        "steps": [
            {"name": "gcr.io/cloud-builders/docker", "args": ["build", "--no-cache", "--build-arg", f"CACHEBUST={int(time.time())}", "-t", IMAGE, "-f", "Dockerfile", "."]},
            {"name": "gcr.io/cloud-builders/docker", "args": ["push", IMAGE]},
        ],
        "images": [IMAGE],
        "options": {"logging": "CLOUD_LOGGING_ONLY"},
    }
    parent = f"projects/{PROJECT_ID}/locations/{REGION}"
    r = requests.post(f"https://cloudbuild.googleapis.com/v1/{parent}/builds", headers=H, json=build_body, timeout=60)
    if r.status_code not in (200, 201):
        print(f"  build submit FAILED: {r.status_code} {r.text[:300]}")
        return 1
    build_name = r.json().get("name", r.json().get("metadata", {}).get("build", {}).get("id", ""))
    print(f"  build: {build_name}")

    # poll build
    for i in range(40):
        time.sleep(15)
        bid = r.json().get("metadata", {}).get("build", {}).get("id", "")
        if not bid:
            # try to get it from the build name
            bid = build_name.split("/")[-1] if build_name else ""
        rp = requests.get(f"https://cloudbuild.googleapis.com/v1/projects/{PROJECT_ID}/locations/{REGION}/builds/{bid}", headers=H, timeout=15)
        d = rp.json()
        status = d.get("status", "?")
        if status in ("SUCCESS", "FAILURE", "FAILED"):
            print(f"  build {status}")
            if status != "SUCCESS":
                return 1
            break
        print(f"  poll {i+1}: {status}")

    # 3. Deploy Cloud Run service
    print("[3/3] deploying Cloud Run service...")
    svc_url = f"https://run.googleapis.com/v2/projects/{PROJECT_ID}/locations/{REGION}/services/{SERVICE}"
    r = requests.get(svc_url, headers=H, timeout=15)
    exists = r.status_code == 200

    service_body = {
        "template": {
            "containers": [{
                "image": IMAGE,
                "ports": [{"containerPort": 3000}],
                "resources": {"limits": {"memory": "2Gi", "cpu": "2"}},
                "env": [
                    {"name": "GCP_PROJECT_ID", "value": PROJECT_ID},
                    {"name": "GCP_LOCATION", "value": REGION},
                    {"name": "GCP_IMAGE_LOCATION", "value": "global"},
                    {"name": "AUTEUR_CORS_ORIGINS", "value": "*"},
                    {"name": "PARALLEL_API_KEY", "value": os.environ.get("PARALLEL_API_KEY", "")},
                    {"name": "FIRESTORE_DATABASE", "value": "auteur"},
                    {"name": "NODE_ENV", "value": "production"},
                ],
            }],
            "timeout": "300s",
            "serviceAccount": f"auteur@{PROJECT_ID}.iam.gserviceaccount.com",
            "scaling": {"minInstanceCount": 1, "maxInstanceCount": 10},
        },
        "ingress": "INGRESS_TRAFFIC_ALL",
    }

    if exists:
        existing = r.json()
        etag = existing.get("etag", "")
        service_body["name"] = existing.get("name", f"projects/{PROJECT_ID}/locations/{REGION}/services/{SERVICE}")
        r2 = requests.patch(f"https://run.googleapis.com/v2/projects/{PROJECT_ID}/locations/{REGION}/services/{SERVICE}",
            headers={**H, "If-Match": etag}, json=service_body, timeout=60)
    else:
        r2 = requests.post(f"https://run.googleapis.com/v2/projects/{PROJECT_ID}/locations/{REGION}/services?serviceId={SERVICE}",
            headers=H, json=service_body, timeout=60)

    if r2.status_code not in (200, 201):
        print(f"  deploy FAILED: {r2.status_code} {r2.text[:400]}")
        return 1

    op = r2.json().get("name", "")
    print(f"  operation: {op}")
    for i in range(20):
        time.sleep(8)
        rp = requests.get(f"https://run.googleapis.com/v2/{op}", headers=H, timeout=15)
        dp = rp.json() if rp.status_code == 200 else {}
        if dp.get("done"):
            if dp.get("error"):
                print(f"  FAILED: {dp['error']}")
                return 1
            break

    # Get the service URL
    r = requests.get(f"https://run.googleapis.com/v2/projects/{PROJECT_ID}/locations/{REGION}/services/{SERVICE}", headers=H, timeout=15)
    uri = r.json().get("uri", "")
    print(f"\n{'='*60}")
    print(f"DEPLOYED: {uri}")
    print(f"{'='*60}")

    # Grant public access
    iam_url = f"https://run.googleapis.com/v1/projects/{PROJECT_ID}/locations/{REGION}/services/{SERVICE}:getIamPolicy"
    r = requests.get(iam_url, headers=H, timeout=15)
    policy = r.json() if r.status_code == 200 else {"bindings": []}
    policy.setdefault("bindings", [])
    existing = next((b for b in policy["bindings"] if b["role"] == "roles/run.invoker"), None)
    if existing is None:
        policy["bindings"].append({"role": "roles/run.invoker", "members": ["allUsers"]})
    elif "allUsers" not in existing["members"]:
        existing["members"].append("allUsers")
    requests.post(f"https://run.googleapis.com/v1/projects/{PROJECT_ID}/locations/{REGION}/services/{SERVICE}:setIamPolicy",
        headers=H, json={"policy": policy}, timeout=20)
    print("Granted public access (allUsers -> roles/run.invoker)")

    # Health check
    time.sleep(8)
    print(f"\n=== health check ===")
    for i in range(8):
        time.sleep(5)
        try:
            rh = requests.get(f"{uri}/api/health", timeout=20)
            print(f"  attempt {i+1}: {rh.status_code}")
            if rh.status_code == 200:
                d = rh.json()
                print(f"  status={d.get('status')} service={d.get('service')}")
                print(f"  models: {list(d.get('model_status',{}).keys())}")
                print(f"  parallel: {d.get('partner_status',{}).get('parallel_search',{}).get('configured')}")
                break
        except Exception as e:
            print(f"  attempt {i+1}: {e}")

    # Check the frontend
    print(f"\n=== frontend check ===")
    for i in range(5):
        time.sleep(3)
        try:
            rf = requests.get(uri, timeout=20)
            print(f"  GET /: {rf.status_code}")
            if rf.status_code == 200 and "Auteur" in rf.text:
                print(f"  ✓ Frontend loads — 'Auteur' found in HTML")
                break
        except Exception as e:
            print(f"  attempt {i+1}: {e}")

    print(f"\n{'='*60}")
    print(f"APP URL:  {uri}")
    print(f"API:       {uri}/api/health")
    print(f"Docs:      {uri}/api/docs")
    print(f"{'='*60}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
