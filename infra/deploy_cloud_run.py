#!/usr/bin/env python3
"""
Auteur — Cloud Run deploy via Cloud Build (no gcloud needed).

Pipeline:
  1. Create Artifact Registry repo 'auteur' (done).
  2. Tarball the backend/ source + upload to a GCS bucket.
  3. Submit a Cloud Build job that:
     - builds the Docker image (backend/Dockerfile)
     - pushes it to us-central1-docker.pkg.dev/auteur-506523/auteur/auteur-dev:latest
  4. Poll the Cloud Build op until the image is pushed.
  5. Create the Cloud Run service (auteur-dev) pointing at the image.
  6. Poll the Cloud Run op until the service is ready.
  7. curl the deployed /api/health URL — must return 200 (blueprint DoD P830).

Usage:
  source .env
  python3 infra/deploy_cloud_run.py --service auteur-dev --region us-central1
"""
from __future__ import annotations

import argparse
import io
import os
import sys
import tarfile
import time
from pathlib import Path

import requests

SA_KEY = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "auteur-506523")
REGION = os.environ.get("GCP_LOCATION", "us-central1")


def _creds():
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    if not SA_KEY or not Path(SA_KEY).exists():
        raise RuntimeError(f"GOOGLE_APPLICATION_CREDENTIALS not set or missing: {SA_KEY}")
    creds = service_account.Credentials.from_service_account_file(
        SA_KEY, scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(Request())
    return creds


def _H() -> dict:
    return {"Authorization": f"Bearer {_creds().token}", "Content-Type": "application/json"}


# --------------------------------------------------------------------------- #
# Step 1 — ensure AR repo (idempotent)
# --------------------------------------------------------------------------- #

def ensure_ar_repo(repo: str, region: str) -> None:
    H = _H()
    url = f"https://artifactregistry.googleapis.com/v1/projects/{PROJECT_ID}/locations/{region}/repositories/{repo}"
    r = requests.get(url, headers=H, timeout=20)
    if r.status_code == 200:
        print(f"  AR repo {repo}: exists")
        return
    if r.status_code != 404:
        raise RuntimeError(f"AR repo check failed: {r.status_code} {r.text[:200]}")
    print(f"  creating AR repo {repo}...")
    parent = f"projects/{PROJECT_ID}/locations/{region}"
    body = {"format": "DOCKER", "description": "Auteur backend images"}
    r = requests.post(f"https://artifactregistry.googleapis.com/v1/{parent}/repositories?repositoryId={repo}",
                      headers=H, json=body, timeout=30)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"AR create failed: {r.status_code} {r.text[:300]}")
    op = r.json().get("name", "")
    for _ in range(12):
        time.sleep(5)
        rp = requests.get(f"https://artifactregistry.googleapis.com/v1/{op}", headers=H, timeout=20)
        dp = rp.json() if rp.status_code == 200 else {}
        if dp.get("done"):
            break
    print(f"  AR repo {repo}: created")


# --------------------------------------------------------------------------- #
# Step 2 — create GCS bucket + upload source tarball
# --------------------------------------------------------------------------- #

def ensure_bucket(bucket: str) -> None:
    H = _H()
    url = f"https://storage.googleapis.com/storage/v1/b/{bucket}"
    r = requests.get(url, headers=H, timeout=20)
    if r.status_code == 200:
        print(f"  GCS bucket {bucket}: exists")
    else:
        print(f"  creating GCS bucket {bucket} (US multi-region)...")
        r = requests.post(f"https://storage.googleapis.com/storage/v1/b?project={PROJECT_ID}",
                          headers=H, json={"name": bucket, "location": "US"}, timeout=30)
        if r.status_code not in (200, 201):
            raise RuntimeError(f"bucket create failed: {r.status_code} {r.text[:300]}")
        print(f"  GCS bucket {bucket}: created")

    # Grant the Cloud Build default SA (Compute Engine default SA) read access
    # to this bucket via IAM binding. Cloud Build fetches source as this SA.
    # The Compute default SA email uses the project NUMBER, not the project ID.
    # We look it up via the Cloud Resource Manager projects API.
    print(f"  granting Cloud Build SA read access to bucket {bucket}...")
    # 1. get the project number
    pr = requests.get(f"https://cloudresourcemanager.googleapis.com/v1/projects/{PROJECT_ID}",
                      headers=H, timeout=20)
    if pr.status_code != 200:
        print(f"  WARNING: couldn't look up project number ({pr.status_code}): {pr.text[:200]}")
        return
    project_number = pr.json().get("projectNumber")
    if not project_number:
        print(f"  WARNING: no projectNumber in response")
        return
    compute_sa = f"{project_number}-compute@developer.gserviceaccount.com"
    print(f"  Compute default SA: {compute_sa}")
    iam_url = f"https://storage.googleapis.com/storage/v1/b/{bucket}/iam"
    rp = requests.get(iam_url + "?options=requestedPolicyVersion=3", headers=H, timeout=20)
    if rp.status_code == 200:
        policy = rp.json()
        policy.setdefault("bindings", [])
        member = f"serviceAccount:{compute_sa}"
        existing = next((b for b in policy["bindings"] if b["role"] == "roles/storage.objectViewer"), None)
        if existing is None:
            policy["bindings"].append({"role": "roles/storage.objectViewer", "members": [member]})
        elif member not in existing["members"]:
            existing["members"].append(member)
        else:
            print(f"  already granted")
            return
        r2 = requests.put(iam_url, headers=H, json=policy, timeout=20)
        if r2.status_code in (200, 201):
            print(f"  granted roles/storage.objectViewer to {compute_sa}")
        else:
            print(f"  WARNING: IAM grant failed ({r2.status_code}): {r2.text[:200]}")
    else:
        print(f"  WARNING: getIAMPolicy failed ({rp.status_code}): {rp.text[:200]}")


def upload_source_tarball(bucket: str, object_name: str, source_dir: Path) -> str:
    """Tarball backend/ + Dockerfile + requirements + upload to GCS.

    Makes the object public-read so Cloud Build's default Compute SA can fetch it
    (the bucket is a build-source bucket, contents are just app code — no secrets).
    """
    H = _H()
    print(f"  tarring source from {source_dir}...")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        # backend/ dir (the app)
        tar.add(str(source_dir / "backend"), arcname="backend")
        # backend/Dockerfile is inside backend/, already included
    src_bytes = buf.getvalue()
    print(f"  tarball: {len(src_bytes):,} bytes")

    # upload via the GCS resumable / simple upload
    url = (f"https://storage.googleapis.com/upload/storage/v1/b/{bucket}/o?"
           f"uploadType=media&name={object_name}")
    headers = {"Authorization": H["Authorization"], "Content-Type": "application/gzip"}
    r = requests.post(url, headers=headers, data=src_bytes, timeout=120)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"upload failed: {r.status_code} {r.text[:300]}")
    gcs_uri = f"gs://{bucket}/{object_name}"
    print(f"  uploaded -> {gcs_uri}")

    # make the object public-read so Cloud Build can fetch it
    acl_url = f"https://storage.googleapis.com/storage/v1/b/{bucket}/o/{object_name}/acl"
    r = requests.post(acl_url, headers=H, json={"entity": "allUsers", "role": "READER"}, timeout=20)
    if r.status_code in (200, 201):
        print(f"  made object public-read (Cloud Build fetch access)")
    else:
        print(f"  WARNING: ACL grant failed ({r.status_code}); Cloud Build may not fetch: {r.text[:150]}")
    return gcs_uri


# --------------------------------------------------------------------------- #
# Step 3 — submit Cloud Build
# --------------------------------------------------------------------------- #

def submit_build(source_gcs: str, image: str, bucket: str, region: str) -> str:
    H = _H()
    print(f"  submitting Cloud Build -> {image}")
    build_body = {
        "source": {"storageSource": {
            "bucket": bucket,
            "object": source_gcs.split(f"{bucket}/")[1],
        }},
        "steps": [
            {
                "name": "gcr.io/cloud-builders/docker",
                "args": ["build", "-t", image, "-f", "backend/Dockerfile", "."],
            },
            {
                "name": "gcr.io/cloud-builders/docker",
                "args": ["push", image],
            },
        ],
        "images": [image],
        "options": {"logging": "CLOUD_LOGGING_ONLY"},
    }
    parent = f"projects/{PROJECT_ID}/locations/{region}"
    url = f"https://cloudbuild.googleapis.com/v1/{parent}/builds"
    r = requests.post(url, headers=H, json=build_body, timeout=60)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"build submit failed: {r.status_code} {r.text[:400]}")
    build = r.json()
    build_id = build.get("metadata", {}).get("build", {}).get("id") or build.get("name", "")
    print(f"  build submitted: {build_id}")
    return build.get("name", build_id)  # full operation name


def poll_build(op_name: str, region: str, max_wait: int = 600) -> bool:
    H = _H()
    print(f"  polling build (max {max_wait}s)...")
    t0 = time.time()
    while time.time() - t0 < max_wait:
        url = f"https://cloudbuild.googleapis.com/v1/{op_name}"
        r = requests.get(url, headers=H, timeout=20)
        if r.status_code != 200:
            time.sleep(10)
            continue
        d = r.json()
        status = d.get("status", "?")
        done = d.get("finishTime") is not None
        elapsed = int(time.time() - t0)
        if done:
            if status == "SUCCESS":
                print(f"  build SUCCESS ({elapsed}s)")
                return True
            else:
                # fetch logs
                logs_url = f"https://console.cloud.google.com/cloud-build/builds/{op_name.split('/')[-1]}?project={PROJECT_ID}"
                raise RuntimeError(f"build {status} after {elapsed}s. Logs: {logs_url}")
        print(f"  poll {elapsed}s: status={status}")
        time.sleep(15)
    raise TimeoutError(f"build not done in {max_wait}s")


# --------------------------------------------------------------------------- #
# Step 4 — create/update Cloud Run service
# --------------------------------------------------------------------------- #

def deploy_service(service: str, image: str, region: str) -> str:
    H = _H()
    parent = f"projects/{PROJECT_ID}/locations/{region}"
    svc_url = f"https://run.googleapis.com/v2/{parent}/services/{service}"
    r = requests.get(svc_url, headers=H, timeout=20)
    exists = r.status_code == 200

    # Cloud Run v2 service body (NOTE: field names differ from v1)
    # - timeoutSeconds -> timeout (string like "300s")
    # - containerConcurrency -> at template level
    # - PORT env is auto-set by Cloud Run (reserved name)
    service_body = {
        "template": {
            "containers": [{
                "image": image,
                "ports": [{"containerPort": 8000}],
                "resources": {"limits": {"memory": "1Gi", "cpu": "1"}},
                "env": [
                    {"name": "GCP_PROJECT_ID", "value": PROJECT_ID},
                    {"name": "GCP_LOCATION", "value": region},
                    {"name": "GCP_IMAGE_LOCATION", "value": "global"},
                    {"name": "AUTEUR_CORS_ORIGINS", "value": "*"},
                    # PORT is auto-set by Cloud Run (reserved env name)
                ],
            }],
            "timeout": "300s",
            "serviceAccount": f"auteur@{PROJECT_ID}.iam.gserviceaccount.com",
            "scaling": {"minInstanceCount": 1, "maxInstanceCount": 10},
        },
        "ingress": "INGRESS_TRAFFIC_ALL",
    }
    if exists:
        # PATCH needs the etag + name
        existing = r.json()
        service_body["name"] = existing.get("name", f"{parent}/services/{service}")
        etag = existing.get("etag", "")
        print(f"  updating service {service} (etag {etag[:8]})...")
        url = f"https://run.googleapis.com/v2/{parent}/services/{service}"
        r2 = requests.patch(url, headers={**H, "If-Match": etag} if etag else H,
                            json=service_body, timeout=60)
    else:
        print(f"  creating service {service}...")
        # MUST pass serviceId query param or Cloud Run auto-generates a name
        url = f"https://run.googleapis.com/v2/{parent}/services?serviceId={service}"
        r2 = requests.post(url, headers=H, json=service_body, timeout=60)
    if r2.status_code not in (200, 201):
        raise RuntimeError(f"service deploy failed: {r2.status_code} {r2.text[:400]}")
    op = r2.json().get("name", "")
    print(f"  operation: {op}")
    return op


def poll_service_op(op: str, max_wait: int = 300) -> str:
    H = _H()
    print(f"  polling service deploy (max {max_wait}s)...")
    t0 = time.time()
    while time.time() - t0 < max_wait:
        r = requests.get(f"https://run.googleapis.com/v2/{op}", headers=H, timeout=20)
        if r.status_code != 200:
            time.sleep(10)
            continue
        d = r.json()
        if d.get("done"):
            if d.get("error"):
                raise RuntimeError(f"service deploy failed: {d['error']}")
            # get the response which has the service URI
            resp = d.get("response", {})
            uri = resp.get("uri", "")
            if uri:
                print(f"  service ready ({int(time.time()-t0)}s): {uri}")
                return uri
            break
        print(f"  poll {int(time.time()-t0)}s: pending")
        time.sleep(10)
    raise TimeoutError(f"service not ready in {max_wait}s")


def grant_public_access(service: str, region: str) -> None:
    """Grant allUsers roles/run.invoker so the service is public (unauthenticated)."""
    H = _H()
    print(f"  granting public access (allUsers -> roles/run.invoker)...")
    iam_url = f"https://run.googleapis.com/v1/projects/{PROJECT_ID}/locations/{region}/services/{service}:getIamPolicy"
    r = requests.get(iam_url, headers=H, timeout=15)
    policy = r.json() if r.status_code == 200 else {"bindings": []}
    policy.setdefault("bindings", [])
    existing = next((b for b in policy["bindings"] if b["role"] == "roles/run.invoker"), None)
    if existing is None:
        policy["bindings"].append({"role": "roles/run.invoker", "members": ["allUsers"]})
    elif "allUsers" not in existing["members"]:
        existing["members"].append("allUsers")
    else:
        print("    already public")
        return
    r2 = requests.post(f"https://run.googleapis.com/v1/projects/{PROJECT_ID}/locations/{region}/services/{service}:setIamPolicy",
                       headers=H, json={"policy": policy}, timeout=20)
    if r2.status_code == 200:
        print("    granted")
    else:
        print(f"    WARNING: setIamPolicy failed ({r2.status_code}): {r2.text[:200]}")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--service", default="auteur-dev")
    ap.add_argument("--region", default=REGION)
    ap.add_argument("--repo", default="auteur")
    ap.add_argument("--bucket", default="auteur-build-source")
    args = ap.parse_args()

    source_dir = Path(__file__).resolve().parents[1]
    image = f"{args.region}-docker.pkg.dev/{PROJECT_ID}/{args.repo}/{args.service}:latest"

    print(f"Deploying {args.service} to Cloud Run ({args.region}) on project {PROJECT_ID}")
    print(f"  image:    {image}")
    print(f"  source:   {source_dir}")

    # 1. AR repo
    print("\n[1/5] Artifact Registry repo")
    ensure_ar_repo(args.repo, args.region)

    # 2. GCS bucket + upload source
    print("\n[2/5] GCS source upload")
    ensure_bucket(args.bucket)
    object_name = f"source-{int(time.time())}.tar.gz"
    gcs_uri = upload_source_tarball(args.bucket, object_name, source_dir)

    # 3. Cloud Build
    print("\n[3/5] Cloud Build")
    op_name = submit_build(gcs_uri, image, args.bucket, args.region)
    poll_build(op_name, args.region, max_wait=600)

    # 4. Cloud Run service
    print("\n[4/5] Cloud Run service")
    svc_op = deploy_service(args.service, image, args.region)
    uri = poll_service_op(svc_op, max_wait=300)

    # 5. Health check (blueprint DoD P830)
    print("\n[5/5] Health check (blueprint DoD P830)")
    health_url = f"{uri}/api/health"
    print(f"  curl {health_url}")
    ok = False
    for i in range(6):
        time.sleep(5)
        try:
            r = requests.get(health_url, timeout=15)
            print(f"  attempt {i+1}: {r.status_code}")
            if r.status_code == 200:
                d = r.json()
                print(f"  status={d.get('status')}  service={d.get('service')}")
                print(f"  partner: {d.get('partner_status',{}).get('parallel_search',{})}")
                print(f"  models: {list(d.get('model_status',{}).keys())}")
                ok = True
                break
        except Exception as e:
            print(f"  attempt {i+1}: {e}")
    if not ok:
        raise RuntimeError(f"health check failed at {health_url}")

    print(f"\n{'='*60}")
    print(f"DEPLOYED: {uri}")
    print(f"  health:  {health_url}")
    print(f"  docs:    {uri}/docs")
    print(f"{'='*60}")

    # write the URL to a file for the page + worklog
    out = Path(__file__).resolve().parents[1] / "backend" / "validation" / "outputs" / "deployed-url.json"
    out.write_text(__import__("json").dumps({
        "service": args.service, "region": args.region,
        "url": uri, "health_url": health_url,
        "deployed_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }, indent=2))
    print(f"\nURL written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
