# Auteur — REST API Contract

> REST API contract. All endpoints are versioned under
> for the FastAPI service `auteur-api` deployed on Cloud Run. All endpoints
> are versioned under `/api` and require no authentication ,
> anonymous projects).

## Conventions

- **Base URL:** `https://auteur-cinema-xxxx.run.app/api` (prod). Dev:
  `https://auteur-dev-xxxx.run.app/api`.
- **Content type:** `application/json` for request/response bodies, except
  the two export endpoints (CSV / JSON download).
- **Errors:** standard HTTP status codes. `4xx` for user error, `5xx` for
  server error with a JSON body `{ "error": "...", "detail": "..." }`.
- **Streaming:** the `generate` endpoint streams progress over
  **Server-Sent Events (SSE)** rather than returning a single JSON body
  .
- **Project IDs:** 128-bit UUIDv4 . There is no
  project-listing endpoint — IDs are unguessable.

## Endpoints 

| # | Endpoint | Method | Purpose | Request | Response |
|---|---|---|---|---|---|
| 1 | `/api/projects` | POST | Create new project | `{ "logline": "..." }` | `{ "projectId": "...", "bible": <Bible v1> }` |
| 2 | `/api/projects/{id}` | GET | Get project state | — | `{ "project": {...}, "bible": <Bible v{n}>, "shots": [...], "generations": [...] }` |
| 3 | `/api/projects/{id}/bible` | GET | Get current bible | — | `{ "bible": <Bible v{n}> }` |
| 4 | `/api/projects/{id}/bible/entries/{entryId}` | PATCH | Edit bible entry | `{ "field": "...", "value": "..." }` | `{ "bible": <Bible v{n+1}> }` |
| 5 | `/api/projects/{id}/shots` | GET | Get shot list | — | `{ "shots": [...] }` |
| 6 | `/api/projects/{id}/shots/{shotId}/generate` | POST | Trigger generation (SSE stream) | `{ "bibleVersion": n }` | `text/event-stream` — `{ "generationId": "..." }` plus progress events |
| 7 | `/api/projects/{id}/shots/{shotId}/regenerate` | POST | Re-generate | `{ "reason": "drift 0.34" }` | `{ "generationId": "..." }` |
| 8 | `/api/projects/{id}/shots/{shotId}/consistency` | GET | Get drift report | — | `{ "drift_score": 0.12, "breakdown": { "character": ..., "location": ..., "wardrobe": ..., "style": ... }, "recommendation": "accept" }` |
| 9 | `/api/projects/{id}/assemble` | POST | Assemble final film | — | `{ "outputUrl": "gs://auteur-renders/.../final.mp4" }` |
| 10 | `/api/projects/{id}/share` | POST | Create share link | — | `{ "publicSlug": "ab12cd34" }` |
| 11 | `/api/projects/{id}/export/bible` | GET | Export bible JSON | — | `application/json` (file download) |
| 12 | `/api/projects/{id}/export/shots` | GET | Export shot list CSV | — | `text/csv` (file download) |
| 13 | `/api/projects/{id}/events` | GET | Get event log | — | `{ "events": [...] }` |
| 14 | `/api/health` | GET | Health check | — | `{ "status": "ok", "partner_status": "ok", "model_status": "ok" }` |

## Detailed contracts

### 1. `POST /api/projects` — create new project

Creates a new anonymous project and triggers the Director Agent to build
Bible v1 (Research Agent runs, Director builds the typed Bible, persists
`bibles/{projectId}/1` in Firestore, returns the typed object). This is the
main entry point — a single logline in, a typed Film Bible out.

- **Request body:** `{ "logline": string }` (max 280 chars).
  Input sanitization rejects prompt-injection patterns.
- **Response 201:** `{ "projectId": string (UUIDv4), "bible": <Bible v1> }`
  (see `docs/bible-schema.md` for the `FilmBible` shape).
- **Side effects:** writes `projects/{id}`, `bibles/{projectId}/1`,
  `events` subcollection (`project_created`, `logline_submitted`,
  `research_started`, `research_completed`, `bible_built (version: 1)`).

### 2. `GET /api/projects/{id}` — get project state

Returns the full project state used by the Next.js workspace UI: project
metadata, current Bible, shots, and the most recent generation per shot.

### 3. `GET /api/projects/{id}/bible` — get current bible

Returns the current Bible version (highest integer in the append-only
`bibles/{projectId}/{version}` collection). The UI's Bible Pane binds to
this response .

### 4. `PATCH /api/projects/{id}/bible/entries/{entryId}` — edit bible entry

Edits a single field on a character / location / wardrobe / voice / score /
style / story-beat entry. Each PATCH creates a new immutable Bible version
(`v{n+1}`) — never mutates `v{n}` in place . The
Director propagates the edit to affected shots (their `bible_version` field
becomes stale, prompting re-generation).

### 5. `GET /api/projects/{id}/shots` — get shot list

Returns the ordered shot list with `bible_version` per shot, generation IDs,
status (`pending | generating | ready | drift | accepted`), and drift
scores.

### 6. `POST /api/projects/{id}/shots/{shotId}/generate` — trigger generation (SSE

The most complex endpoint. Triggers the generation pipeline for one shot:
Imagen storyboard → Veo 3.1 video → Chirp 3 voice → Lyria 2 score →
Consistency Check. The Director cites the Bible version passed in the request
body.

- **Request body:** `{ "bibleVersion": int }`
- **Response:** `text/event-stream` (SSE). The first event returns
  `{ "generationId": "..." }` so the client can correlate subsequent events
  (see Event Types below).
- **SSE event types** :
  ```
  event: generation_started
  data: {"shotId": "...", "modality": "imagen"}

  event: progress
  data: {"shotId": "...", "modality": "veo", "phase": "queued"}

  event: generation_completed
  data: {"shotId": "...", "modality": "veo", "output_url": "gs://..."}

  event: consistency_check_completed
  data: {"shotId": "...", "drift_score": 0.12, "recommendation": "accept"}

  event: generation_failed
  data: {"shotId": "...", "modality": "veo", "error": "..."}
  ```
- **Why SSE:** simple, HTTP-native, works with Cloud Run, no WebSocket
  complexity.
- **Failure handling** : on Veo 5xx / quota 429,
  retry once with Veo Light; if still failing, stream a `generation_failed`
  event and fall back to the sample shot from the demo.

### 7. `POST /api/projects/{id}/shots/{shotId}/regenerate` — re-generate

Re-runs generation with drift report as corrective context: the previous drift
breakdown is appended to the Veo prompt so the model receives more specific
guidance . Request body carries
a `reason` (e.g., `"drift 0.34"` or a user note) which is logged in the
event trail for auditability.

### 8. `GET /api/projects/{id}/shots/{shotId}/consistency` — drift report

Returns the most recent drift report for the shot: the aggregate
`drift_score` (0.0 = identical, 1.0 = totally drifted), the per-attribute
breakdown (character / location / wardrobe / style), and the
recommendation (`accept` or `re-generate`). The threshold defaults to 0.25 (an engineering operating threshold, not a statistically validated perceptual-quality boundary)
and tunes per project .

### 9. `POST /api/projects/{id}/assemble` — assemble final film

Triggers ffmpeg concatenation of the 4 accepted shots + voice + score into a
single MP4, written to Cloud Storage (`gs://auteur-renders/{projectId}/
final.mp4`). Returns the public URL of the assembled film.

### 10. `POST /api/projects/{id}/share` — create share link

Generates an 8-char random slug (2^48 entropy) and returns it. The slug is
used by the public share view at `/share/{slug}`. The share page renders the
assembled film, the Film Bible, and the side-by-side signature moment.

### 11. `GET /api/projects/{id}/export/bible` — export bible JSON

Downloads the current Bible as a standalone JSON file. This is the
open-source escape hatch: a user's curated Bible is portable structured
data they own .

### 12. `GET /api/projects/{id}/export/shots` — export shot list CSV

Downloads the shot list as CSV (columns: order, description, bible_version,
status, drift_score, generation_url). Useful for editors who want to work
with the shot list outside Auteur.

### 13. `GET /api/projects/{id}/events` — get event log

Returns the project's full event trail :
`project_created`, `logline_submitted`, `research_started`,
`research_completed`, `bible_built (version: n)`, `bible_edited (field,
old, new) → bible_version: n+1`, `shot_list_generated`,
`generation_started (shotId, modality)`, `generation_completed (shotId,
modality, output_url)`, `generation_failed (shotId, modality, error)`,
`consistency_check_completed (shotId, drift_score, recommendation)`,
`regeneration_prompted (shotId, reason)`, `assembly_started`,
`assembly_completed (output_url)`, `share_link_created`. Used for the demo
narrative and for audit.

### 14. `GET /api/health` — health check

Returns the integration health used by the Cloud Run smoke test and the
operations runbook .

```json
{
  "status": "ok",
  "partner_status": "ok",
  "model_status": "ok"
}
```

- `status`: aggregate ("ok" if Firestore + Cloud Storage reachable).
- `partner_status`: probes the Parallel Search API with a test query
  . `"ok"` if the Bearer token is valid
  and the API responds within 10s; `"degraded"` if returning cached results
  or unreachable.
- `model_status`: probes Vertex AI quota by listing the Veo publisher model
  . `"ok"` if Veo / Chirp / Lyria /
  Gemini / Imagen successor are all reachable.

## Rate limits and abuse prevention 

- Per-IP rate limit: max 2 projects / hour (Row 3).
- Per-project shot cap: 4 shots ).
- Anonymous generations use the Veo iteration tier only; the Standard tier
  is reserved for the final demo render.

## Cross-references

- Bible shape: [`docs/bible-schema.md`](bible-schema.md
- Parallel Search integration (underlying `partner_status` probe):
  [`docs/partner-integration.md`](partner-integration.md
- Per-API failure handling: see `docs/architecture.md`
  and `docs/partner-integration.md`.
- Demo script that drives the UI through these endpoints:
  [`docs/demo-script.md`](demo-script.md
