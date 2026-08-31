# Auteur — Architecture

> Component justification, data flow, and design decisions.
> canonical component-justification reference; per Phase 15, every
> component below answers: *what user value or competitive advantage does this
> create?* Do not add components that do not answer this question.

## Product Thesis (Section 21, Table 21)

Auteur is **AI cinema's memory**. Individual Veo 3.1, Chirp 3, Lyria 2, and
Imagen 3 generations are already beautiful — the unsolved problem is that every
shot is an isolated lottery: characters drift, wardrobes mutate, voices lose
continuity, and the resulting "short film" looks like four different films
stitched together. Auteur closes that gap with a single architectural primitive:
a **typed, versioned, citable Film Bible** that a Director Agent maintains and
**injects into every generation call**. The result is a 30-second short film
that looks like one film, not four — the side-by-side drift-vs-consistency
comparison is the project's entire pitch .

## High-Level Data Flow

```
User (browser, Cloud Run)
   │  HTTPS (REST + SSE)
   ▼
Next.js 16 Studio UI ─────────────────────┐
   │  Logline · Research · Bible · Shots · Render · Grid · Drift · Assembly · Share
   ▼
Cloud Run: auteur-dev (FastAPI + Google ADK)
 ┌──────────────────────────────────────────────────────────┐
 │  Director Agent ──▶ Research Agent (Parallel Search)     │
 │        │                     │                            │
 │        │                     ▼                            │
 │        │              Gemini 3.1 Pro synthesis            │
 │        ▼                                                  │
 │  Consistency Check Agent (Gemini 3.1 Pro Vision)          │
 │        │                                                  │
 │        ▼                                                  │
 │  Film Bible (Pydantic, versioned, citable)                │
 └───┬──────────┬───────────┬──────────────┬─────────────────┘
     │          │           │              │
     ▼          ▼           ▼              ▼
 Firestore  Parallel    Vertex AI     Cloud Storage
 (bible,    Search API  (Veo 3.1,      (rendered MP4s,
  shots,    (x-api-key)  Chirp 3,       voice WAVs,
  events)                Lyria 2,       score WAVs,
                         Imagen,        char-ref PNGs)
                         Gemini)
```

End-to-end: **Logline → Research Agent (Parallel Search) → Director Agent →
Film Bible v{n} (Firestore) → Shot List → Generation Pipeline (Veo / Chirp /
Lyria / Imagen) → Consistency Check → Assembly (ffmpeg: concat + audio mux) →
Export / Share.** Each generation cites the Bible version it used; each drift
report cites the generation it scored; the assembled film's audio track is the
mixed voiceover (Chirp) + score (Lyria) trimmed and padded to each shot's
exact Veo duration.

## Component Justification 

| Component | What it does | Why it exists | What it does NOT do |
|---|---|---|---|
| Director Agent | Top-level orchestrator (`gemini-3.1-pro-preview`, global region). Receives logline, plans the pipeline, calls Research/Bible/Shot-list/Generation/Consistency/Assembly tools. | Orchestration logic is distinct from specialist logic; keeps each agent's prompt focused. | Cannot delete user data; cannot call Parallel Search directly (delegates to Research); cannot bypass user approval on bible edits. |
| Research Agent | Specialist (`gemini-3.1-pro-preview`). Uses function calling to decide what to search, calls the Parallel Search API as an ADK function tool, evaluates results, and may issue follow-up searches. Synthesizes structured `Reference` objects. | Search-grounding is a distinct capability; isolating it lets us swap partners or add caching without touching the Director. The LLM controls the research trajectory, not Python. | Read-only — cannot write to the Bible; returns results to the Director, who writes. |
| Consistency Check Agent | Specialist (`gemini-3.1-pro-preview`, vision). Compares each generated shot against the Bible references (character image, location image, wardrobe spec); produces a drift score and recommendation. | Consistency-checking is a distinct capability; isolating it lets us tune thresholds independently. | Cannot modify shots; only flags. Stateless — operates per-shot with no memory of prior runs. |
| Film Bible | Typed, versioned, citable Pydantic schema stored in Firestore. Characters, Locations, Wardrobes, Voices, Score motifs, Style anchors, Story beats, References. | This is the project's core primitive — the persistent, structured memory that every generation cites. | Does not generate content itself; it is data, not an agent. Schema is defined in the `bible/schema.py`. |
| Generation Pipeline | Orchestrates Veo/Chirp/Lyria/Imagen calls per shot, with bible-version citation, prompt construction, and per-shot character-ref ASSET injection. Each modality is independent — one failing does not block the others. | Wraps the multimodal model calls so the Director can treat them as one "generate shot" tool. The Chirp + Lyria WAV bytes are persisted to the in-memory generations store so the assembly pipeline can mux them into the final film's audio track. | Does not decide *which* shot to generate or *when* to re-generate — that is the Director's job. |
| Assembly | ffmpeg concatenation of the Veo clips + per-shot audio mux (Chirp voiceover at full volume + Lyria score at 25% as a bed, trimmed/padded to each shot's exact duration) → a single MP4 with AAC audio. | A deterministic operation that does not need an LLM. Handles three per-shot audio scenarios: mix (both assets), single (one asset), silent (neither — generates `anullsrc` silence). | No edit decisions, no color match, no localization — those are future roadmap. |
| Export / Share | JSON bible export, CSV shot list export, public share link with 8-char random slug. | Judges can inspect the bible and view the film without an account . | No accounts, no auth — anonymous projects only . |

## Memory Layers L1–L6 (Section 23.1, Table 32)

Auteur's memory is layered to keep ephemeral, persistent, versioned, and
historical data in the right store. Per Section 22.5, this layered
persistence is what makes the system *genuinely agentic* rather than
LLM-as-a-wrapper.

| Layer | Type | Storage | Content | Read | Write |
|---|---|---|---|---|---|
| L1 — Working memory | Ephemeral | In-process (Cloud Run instance) | Current tool call args + last 5 tool results | Per turn | Per turn (overwrite) |
| L2 — Project state | Persistent | Firestore `projects/{id}` | Film Bible (typed), shot list, generation log, consistency scores | Per tool call | Per user action + per generation |
| L3 — Bible versions | Versioned persistent | Firestore `bibles/{projectId}/{version}` | Immutable snapshots of the Bible at each version | Per generation (cite which version) | Append-only on each edit |
| L4 — Search cache | Ephemeral-persistent | Firestore `search_cache/{projectId}/{queryHash}` | Recent Parallel Search results | Per Research Agent call | On cache miss (24h TTL) |
| L5 — Rendered artifacts | Persistent | Cloud Storage `gs://auteur-renders/{projectId}` | Veo MP4s, Chirp WAVs, Lyria MP3s, Imagen PNGs | Per shot display | On each generation |
| L6 — Drift history | Persistent | Firestore `shots/{projectId}/{shotId}/drift_history` | Per-shot drift scores over re-generations | Per consistency check | Append-only |

The versioning discipline on L3 is what makes drift attributable
: "Shot 3 was generated with Bible v2; user changed
beard color at v3; re-generation pending." Every generation cites its Bible
version; every drift report cites its generation ID.

## Tech Stack (Section 25.1, Table 27)

| Component | Chosen approach | Why | Alternative rejected |
|---|---|---|---|
| Frontend | Next.js 16 (App Router) on Cloud Run | Fast SSR/SSG, TypeScript, mature, standalone output for small Docker images | Pure React CRA (deprecated) |
| Backend | FastAPI on Cloud Run | Async, type-safe, ADK-native, fast cold-start | Flask (not async; weaker for SSE) |
| Agent framework | Google ADK | Required agent framework | LangGraph, CrewAI |
| LLM | `gemini-3.1-pro-preview` via Vertex AI (global region) | Text + vision in one call | OpenAI / Anthropic |
| Video model | Veo 3.1 (`veo-3.1-fast-generate-001` for iteration, `veo-3.1-generate-001` for final) | Supports ASSET reference images for cross-shot character consistency | Runway / Pika / Sora |
| Voice model | Chirp 3 (`gemini-3.1-flash-tts-preview`) | Prebuilt voices; 24kHz PCM output | ElevenLabs |
| Music model | Lyria 2 (`lyria-002`) | Cinematic score generation | Suno / Udio |
| Image model | `gemini-3-pro-image` (global region) | Character reference generation (Imagen 3 is deprecated on this project) | Midjourney / DALL-E |
| Persistence | Firestore | Serverless, schema-flexible, autoscales | Cloud SQL (overkill) |
| Object storage | Cloud Storage | Required for rendered MP4s and storyboards | Local disk (lost on cold-start) |
| Deployment | Cloud Run | Serverless, autoscaling, generous free tier | GKE (over-engineering) |
| Partner integration | Parallel Search API | Intrinsic to agent value (grounded imagination) | Other partners |
| Streaming | Server-Sent Events (SSE) | Simple, HTTP-native, works with Cloud Run | WebSocket (more complex) |
| Auth | None (anonymous projects) | Anonymous projects | Firebase Auth (out of scope, Section 20) |

## Model Note — Day-1 Validation Findings

The specifies "Imagen 3" and "Veo 3.1 Light" in several places. On
the live GCP project `auteur-506523` (us-central1), Day-1 validation surfaced
two deviations that are now codified into the architecture:

1. **Imagen 3 is deprecated on `auteur-506523`.** Use `gemini-3-pro-image`
   for character reference images and storyboards. This is the supported
   successor on this project; it is the same modal family (Gemini image) and
   produces the persistent character asset the architecture depends on.

2. **Veo 3.1 Lite tier does NOT support `reference_images`.** The cross-shot
   consistency primitive (`GenerateVideosConfig.reference_images` with
   `reference_type=ASSET`) requires a tier that supports the ASSET reference
   mechanism. Therefore:
   - For iteration / development: use `veo-3.1-fast-generate-001` (supports
     ASSET reference images, fast enough for tight loops).
   - For final demo-quality renders: use `veo-3.1-generate-001` (Standard tier,
     4K, best quality — Table 34, Row 4).
   - `veo-3.1-lite-generate-001` (the literal "Veo 3.1 Light" tier) is
     reserved for cases where reference images are *not* required.

Day-1 validation (4 shots, 4 scenes, same character reference, mean consistency
score **0.94**) confirms the project is GO on these substitutions. Full
evidence: [`docs/validation-report.md`](docs/validation-report.md)
and the side-by-side image at
[`docs/validation.png`](docs/validation.png).

## Agentic Loop 

```
Observe    logline + (later) generation results + consistency reports
   ↓
Remember   Film Bible v{n} in Firestore (L2/L3) + in-session working memory (L1)
   ↓
Reason     Gemini 3.1 Pro: "what is the next step toward the user's goal?"
   ↓
Plan       choose next tool: parallel_search | build_bible | generate_shot_list
           | call_veo | call_chirp | call_lyria | call_imagen
           | run_consistency_check | assemble_film
   ↓
Act        call the chosen tool with structured args
   ↓
Measure    Consistency Check Agent scores the output (drift 0.0–1.0)
   ↓
Learn      if drift > threshold → re-generate with drift report as corrective context
           if user edits bible → propagate to affected shots (re-gen prompt)
   ↓
Update     Bible version increments; shot list updates; scores logged (L6)
```

The loop is what makes the system agentic rather than a wrapper
: persistent state across the entire film (not per
call), autonomous tool selection among 6 external + 3 internal tools, planning
the research → bible → shot-list → generate → check → assemble sequence,
feedback from the Consistency Check Agent into re-generation decisions, and
measurable drift improvement across re-generations within a project.

## Engineering Strategy 

Repository structure, branch strategy, and CI/CD are defined in the 
Engineering Strategy. Summary relevant to architecture:

- **Repo layout**: `backend/` (FastAPI + agents + bible + pipelines +
  integrations + storage + tests), `frontend/` (Next.js 16 App Router with
  LoglineView, ResearchView, BibleView, ShotListView, RenderQueueView,
  ShotGridView, ConsistencyView, AssemblyView, ShareView, SideBySide,
  KeyboardShortcutsHelp), `infra/` (cloudbuild.yaml, deploy_cloud_run.py,
  deploy-unified.py, seed-demo.sh), plus this file, RUNBOOK.md, and the
  `docs/*.md` references.
- **Branch strategy** : `main` (always deployable,
  protected, green CI), `feature/{name}` (short-lived, squash-merged),
  `main` (frozen after Sept 5).
- **CI/CD** : PR → lint (ruff, eslint, prettier),
  type-check (mypy, tsc), unit + integration tests, prompt eval; merge to main
  → build Docker, push to Artifact Registry, deploy to dev Cloud Run; manual
  prod deploy via release tag; smoke test hits `/api/health` after every
  deploy.
- **Cloud Run config** : min instances 1 (always warm —
  no cold-start demo risk), max 10 (cost cap), concurrency 80, 1 GiB / 1 CPU,
  region us-central1, timeout 300s.
- **Three execution paths** : live path (real-time
  generation, 5–8 min), fallback path (sample production served from
  Cloud Storage), sample production (pre-rendered demo + one live Veo Light
  generation triggered by a "Watch it live" button).
