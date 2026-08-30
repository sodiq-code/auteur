# Auteur — Operations Runbook

> Manual operations, deployment, debugging, and rollback procedures for the
> Auteur Film Bible Agent. Intended for the operator on call.

## Services

| Service | URL | Port | Purpose |
|---------|-----|------|---------|
| `auteur-app` | <https://auteur-app-jbkbgthudq-uc.a.run.app> | 3000 | Unified Studio UI (Next.js 16 standalone) |
| `auteur-dev` | <https://auteur-dev-jbkbgthudq-uc.a.run.app> | 8000 | Backend API (FastAPI) |
| Firestore | `auteur-506523` / database `auteur` | — | Project, Bible, shots, events persistence |
| Cloud Storage | `gs://auteur-renders`, `gs://auteur-demo` | — | Rendered MP4s, WAVs, PNGs |

The Studio UI calls the backend directly via `API_BASE` (hardcoded to
`auteur-dev`). The unified `auteur-app` serves the pre-built Next.js
standalone bundle and does not proxy `/api/*` — this avoids the Next.js
proxy timeout on long-running calls (build-bible takes ~30s).

---

## Health checks

### Backend
```bash
curl -s https://auteur-dev-jbkbgthudq-uc.a.run.app/api/health | jq .
```
Expected: `status: ok`, `endpoints` count matches (22), `parallel_search.configured: true`,
all 5 `model_status` entries `configured: true`.

### Frontend
```bash
curl -s -o /dev/null -w "%{http_code} %{{time_total}}s\n" https://auteur-app-jbkbgthudq-uc.a.run.app/
```
Expected: `200` in under 0.5s.

### Sample production (safety net)
```bash
curl -s https://auteur-dev-jbkbgthudq-uc.a.run.app/api/demo | jq '.status, .consistency.verdict, .consistency.mean_overall'
```
Expected: `ok`, `GO`, `0.925`. If this fails, the safety-net demo is broken and
the landing page will show a loading skeleton instead of the signature moment.

---

## Deployment

### Deploy the backend (`auteur-dev`)

```bash
cd auteur
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/auteur-sa-key.json
export GCP_PROJECT_ID=auteur-506523
export PARALLEL_API_KEY=...
python3 infra/deploy_cloud_run.py --service auteur-dev --region us-central1
```

This uploads the `backend/` source to Cloud Build, builds the Docker image
(`backend/Dockerfile`), pushes it to Artifact Registry, and updates the
Cloud Run service. The deploy script polls the build (up to 600s) and the
service update, then runs a health check.

If the build succeeds but the service update times out (the script's 600s
limit), update the service directly:

```bash
python3 -c "
from google.oauth2 import service_account
from google.auth.transport.requests import Request
import requests, time
c = service_account.Credentials.from_service_account_file(
    '$GOOGLE_APPLICATION_CREDENTIALS',
    scopes=['https://www.googleapis.com/auth/cloud-platform'])
c.refresh(Request())
H = {'Authorization': f'Bearer {c.token}', 'Content-Type': 'application/json'}
svc = 'https://run.googleapis.com/v2/projects/auteur-506523/locations/us-central1/services/auteur-dev'
r = requests.get(svc, headers=H, timeout=20)
existing = r.json()
body = {'template': {'containers': [{'image': 'us-central1-docker.pkg.dev/auteur-506523/auteur/auteur-dev:latest', 'ports': [{'containerPort': 8000}], 'resources': {'limits': {'memory': '1Gi', 'cpu': '1'}}, 'env': existing['template']['containers'][0]['env']}], 'timeout': '300s', 'serviceAccount': 'auteur@auteur-506523.iam.gserviceaccount.com', 'scaling': {'minInstanceCount': 1, 'maxInstanceCount': 10}}, 'ingress': 'INGRESS_TRAFFIC_ALL', 'name': existing['name']}
r2 = requests.patch(svc, headers={**H, 'If-Match': existing['etag']}, json=body, timeout=60)
print('patch:', r2.status_code, r2.json().get('name',''))
"
```

### Deploy the unified app (`auteur-app`)

```bash
# 1. Build the Next.js standalone bundle locally (frontend changes)
cd /home/z/my-project
bun run build

# 2. Deploy the unified image (frontend + backend bundled)
source auteur/.env
python3 deploy-unified.py
```

This builds a single Docker image containing the pre-built Next.js standalone
bundle + the FastAPI backend, deploys it to `auteur-app`, and grants public
access. The unified app runs Next.js on port 3000 and FastAPI on port 8000
internally (started by `deploy-start.sh`).

### Rollback

Cloud Run keeps the last several revisions. To roll back:

```bash
# List recent revisions
gcloud run revisions list --service auteur-dev --region us-central1 --limit 5

# Roll back to a previous revision
gcloud run services update auteur-dev \
  --region us-central1 \
  --no-traffic --tag=rollback \
  && gcloud run services update-traffic auteur-dev \
    --region us-central1 --to-tags=rollback=100
```

---

## Seeding the sample production

The pre-rendered lighthouse-keeper 4-shot demo is the safety net. If it needs
re-seeding (e.g. after a Firestore wipe):

```bash
bash infra/seed-demo.sh
```

This uploads the 4 Veo clips, character reference, and side-by-side image to
`gs://auteur-demo` and writes the demo manifest to Firestore. The `GET /api/demo`
endpoint reads from this; if it returns 404 or a skeleton, re-seed.

---

## Fallback path (Parallel Search outage)

The Research Agent degrades gracefully if the Parallel Search API is
unavailable (key missing, rate-limited, or the endpoint is down):

1. `parallel_search.search()` raises (key missing → `RuntimeError`; HTTP error
   → `httpx.HTTPStatusError`).
2. `research_agent.research()` catches the exception, logs a `research_failed`
   event, and returns an empty reference list.
3. The Director Agent synthesizes the Bible from the logline alone via
   creative inference (Gemini 3.1 Pro).
4. The Research panel shows "Awaiting Parallel Search results" briefly, then
   the Bible is built with 0 references (the success banner reads
   "Bible v1 built from 0 grounded references").

**To verify the fallback:** run `python3 backend/tests/test_fallback_no_parallel_key.py`
(locally, with `PARALLEL_API_KEY` unset). It asserts the research function
returns `[]` and logs a `research_failed` event rather than crashing.

**To simulate a partner outage in production:** temporarily remove the
`PARALLEL_API_KEY` env var from the Cloud Run service, create a new project,
and call `POST /build-bible`. The Bible should still build (with 0 refs).
Restore the key after the test.

---

## Debugging

### Backend logs

```bash
gcloud logging tail \
  "resource.type=cloud_run_revision AND resource.labels.service_name=auteur-dev" \
  --format="value(timestamp, textPayload)" --limit 50
```

### Frontend won't load (blank page)
- Check `auteur-app` is receiving traffic: `curl -s -o /dev/null -w "%{http_code}" https://auteur-app-jbkbgthudq-uc.a.run.app/`
- Check the backend health (above) — the frontend's first call is `GET /api/health`; if it fails, the header shows a "backend note" amber banner.
- Check the browser console for CORS errors — `AUTEUR_CORS_ORIGINS=*` should be set on the backend.

### Build-bible 500s
- Usually a Vertex AI quota/rate-limit. Check the backend logs for `generation_failed` events.
- If the Parallel Search call is the culprit, the `research_failed` event will be in the events log: `GET /api/projects/{id}/events`.

### Assembled film has no audio
- The assembly pipeline muxes the Chirp voiceover + Lyria score into the final MP4. If `has_audio: false` in the assemble response, the per-shot audio assets weren't persisted.
- Check `GET /api/projects/{id}/shots/{shotId}/video` streams (Veo OK) and that the generate response showed `chirp: ok` and `lyria: ok`.
- Run `python3 backend/tests/test_assembly_audio.py` (synthetic inputs, no API calls) to confirm the mux logic is healthy.

### Firestore composite-index errors
- The store uses document key lookups (`projectId_version`) instead of `.where().order_by()` queries to avoid composite-index requirements. If a new query is added that needs a composite index, either create it in the Firestore console or restructure the query to use document keys.

---

## Smoke tests

Run these after every deploy:

```bash
# 1. Backend endpoint smoke test (start the backend first, then):
cd auteur
uvicorn backend.main:app --port 8000 &
python3 backend/tests/test_api_smoke.py

# 2. Audio-mux unit test (synthetic inputs, no API calls, no backend needed):
python3 backend/tests/test_assembly_audio.py

# 3. Graceful-degradation test (no PARALLEL_API_KEY needed):
python3 backend/tests/test_fallback_no_parallel_key.py

# 4. Deployed E2E test (runs against the live Cloud Run backend — takes ~4 min):
python3 backend/tests/e2e_deployed_audio.py
```

All four should exit 0. If any fails, do not mark the deploy as done.

---

## Environment variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `PARALLEL_API_KEY` | No | Parallel Search API key. If unset, the Research Agent degrades gracefully (empty refs). |
| `GOOGLE_APPLICATION_CREDENTIALS` | Yes | Path to the GCP service-account JSON key. |
| `GCP_PROJECT_ID` | Yes | The GCP project ID (default `auteur-506523`). |
| `GCP_LOCATION` | Yes | The region for Veo/Chirp/Lyria (default `us-central1`). |
| `FIRESTORE_DATABASE` | No | The Firestore database name (default `auteur`). |
| `GCS_RENDERS_BUCKET` | No | Cloud Storage bucket for rendered artifacts (default `gs://auteur-renders`). |
| `AUTEUR_CORS_ORIGINS` | No | CORS origins (default `*`). |
