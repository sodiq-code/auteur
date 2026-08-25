# Auteur — Architecture

> Source: blueprint Sections 21, 22, 23, 25, 27, 29, 31. This document is the
> canonical component-justification reference; per blueprint Phase 15, every
> component below answers: *what user value or competitive advantage does this
> create?* Do not add components that do not answer this question.

## Product Thesis (blueprint Section 21, Table 21)

Auteur is **AI cinema's memory**. Individual Veo 3.1, Chirp 3, Lyria 2, and
Imagen 3 generations are already beautiful — the unsolved problem is that every
shot is an isolated lottery: characters drift, wardrobes mutate, voices lose
continuity, and the resulting "short film" looks like four different films
stitched together. Auteur closes that gap with a single architectural primitive:
a **typed, versioned, citable Film Bible** that a Director Agent maintains and
**injects into every generation call**. The result is a 30-second short film
that looks like one film, not four — the side-by-side drift-vs-consistency
comparison is the project's entire pitch (blueprint Section 30.5).

## High-Level Data Flow

```
User (browser, Cloud Run)
   │  HTTPS (REST + SSE)
   ▼
Next.js 15 SPA ─────────────────────┐
   │  Script Pane | Bible Pane | Shot Grid | Render Queue | Research Panel
   ▼
Cloud Run: auteur-api (FastAPI + Google ADK)
 ┌──────────────────────────────────────────────────────────┐
 │  Director Agent ──▶ Research Agent (Parallel Search)     │
 │        │                     │                            │
 │        │                     ▼                            │
 │        │              Gemini 2.5 Flash synthesis          │
 │        ▼                                                  │
 │  Consistency Check Agent (Gemini 2.5 Pro Vision)          │
 │        │                                                  │
 │        ▼                                                  │
 │  Film Bible (Pydantic, versioned, citable)                │
 └───┬──────────┬───────────┬──────────────┬─────────────────┘
     │          │           │              │
     ▼          ▼           ▼              ▼
 Firestore  Parallel    Vertex AI     Cloud Storage
 (bible,    Search API  (Veo 3.1,      (rendered MP4s,
  shots,                 Chirp 3,       storyboards,
  events)                Lyria 2,       voice WAVs)
                         Imagen,        [see model note]
                         Gemini)
```

End-to-end (blueprint Section 21.3): **Logline → Research Agent (Parallel
Search) → Director Agent → Film Bible v{n} (Firestore) → Shot List → Generation
Pipeline (Veo / Chirp / Lyria / Imagen) → Consistency Check → Assembly
(ffmpeg) → Export / Share.** Each generation cites the Bible version it used;
each drift report cites the generation it scored.

## Component Justification (blueprint Section 21.2)

| Component | What it does | Why it exists | What it does NOT do |
|---|---|---|---|
| Director Agent | Top-level orchestrator (Gemini 2.5 Pro). Receives logline, plans the pipeline, calls Research/Bible/Shot-list/Generation/Consistency/Assembly tools. | Orchestration logic is distinct from specialist logic; keeps each agent's prompt focused (blueprint Table 29, "Why separate"). | Cannot delete user data; cannot call Parallel Search directly (delegates to Research); cannot bypass user approval on bible edits. |
| Research Agent | Specialist (Gemini 2.5 Flash). Grounds creative decisions in real-world references via the Parallel Search API; synthesizes structured `Reference` objects. | Search-grounding is a distinct capability; isolating it lets us swap partners or add caching without touching the Director (blueprint Table 30). | Read-only — cannot write to the Bible; returns results to the Director, who writes. |
| Consistency Check Agent | Specialist (Gemini 2.5 Pro Vision). Compares each generated shot against the Bible references (character image, location image, wardrobe spec); produces a drift score and recommendation. | Consistency-checking is a distinct capability; isolating it lets us tune thresholds independently (blueprint Table 31). | Cannot modify shots; only flags. Stateless — operates per-shot with no memory of prior runs. |
| Film Bible | Typed, versioned, citable Pydantic schema stored in Firestore. Characters, Locations, Wardrobes, Voices, Score motifs, Style anchors, Story beats, References. | This is the project's core primitive — the persistent, structured memory that every generation cites (blueprint Section 23). | Does not generate content itself; it is data, not an agent. Schema is defined in `bible/schema.py`. |
| Generation Pipeline | Orchestrates Veo/Chirp/Lyria/Imagen calls per shot, with bible-version citation, prompt construction, and render-queue streaming. | Wraps the multimodal model calls so the Director can treat them as one "generate shot" tool. | Does not decide *which* shot to generate or *when* to re-generate — that is the Director's job. |
| Assembly | ffmpeg concatenation of 4 shots + voice + score → a single MP4. | A deterministic operation that does not need an LLM (blueprint Table 35, Row 14). | No edit decisions, no color match, no localization — those are post-hackathon roadmap (blueprint Section 36.9). |
| Export / Share | JSON bible export, CSV shot list export, public share link with 8-char random slug. | Hackathon compliance: judges must be able to inspect the bible and view the film without an account (blueprint Table 44). | No accounts, no auth — anonymous projects only (blueprint Table 27, Row 14). |

## Memory Layers L1–L6 (blueprint Section 23.1, Table 32)

Auteur's memory is layered to keep ephemeral, persistent, versioned, and
historical data in the right store. Per blueprint Section 22.5, this layered
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
(blueprint Section 23.3): "Shot 3 was generated with Bible v2; user changed
beard color at v3; re-generation pending." Every generation cites its Bible
version; every drift report cites its generation ID.

## Tech Stack (blueprint Section 25.1, Table 27)

| Component | Chosen approach | Why | Alternative rejected |
|---|---|---|---|
| Frontend | Next.js 15 SPA on Cloud Run | Fast SSR/SSG, TypeScript, mature | Pure React CRA (deprecated) |
| Backend | FastAPI on Cloud Run | Async, type-safe, ADK-native, fast cold-start | Flask (not async; weaker for SSE) |
| Agent framework | Google ADK | **Required by rules (stack lock)** | LangGraph, CrewAI (banned) |
| LLM | Gemini 2.5 Pro via Vertex AI | Required by rules | OpenAI / Anthropic (banned) |
| Video model | Veo 3.1 (Lite + Standard) | Required + best fit (character ref images) | Runway / Pika / Sora (banned) |
| Voice model | Chirp 3 | Required + best fit | ElevenLabs (banned) |
| Music model | Lyria 2 | Required | Suno / Udio (banned) |
| Image model | Imagen 3 *(see model note below)* | Required | Midjourney / DALL-E (banned) |
| Persistence | Firestore | Serverless, schema-flexible, autoscales | Cloud SQL (overkill) |
| Object storage | Cloud Storage | Required for rendered MP4s and storyboards | Local disk (lost on cold-start) |
| Deployment | Cloud Run | Serverless, autoscaling, generous free tier | GKE (over-engineering) |
| Partner integration | Parallel Search API | Intrinsic to agent value (grounded imagination) | Other partners |
| Streaming | Server-Sent Events (SSE) | Simple, HTTP-native, works with Cloud Run | WebSocket (more complex) |
| Auth | None (anonymous projects) | Hackathon scope | Firebase Auth (out of scope, Section 20) |

## Model Note — Day-1 Validation Findings

The blueprint specifies "Imagen 3" and "Veo 3.1 Light" in several places. On
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
     4K, best quality — blueprint Table 34, Row 4).
   - `veo-3.1-lite-generate-001` (the literal "Veo 3.1 Light" tier) is
     reserved for cases where reference images are *not* required.

Day-1 validation (4 shots, 4 scenes, same character reference, mean consistency
score **0.94**) confirms the project is GO on these substitutions. Full
evidence: [`docs/validation-day-1-report.md`](docs/validation-day-1-report.md)
and the side-by-side image at
[`docs/validation-day-1.png`](docs/validation-day-1.png).

## Agentic Loop (blueprint Section 22.4)

```
Observe    logline + (later) generation results + consistency reports
   ↓
Remember   Film Bible v{n} in Firestore (L2/L3) + in-session working memory (L1)
   ↓
Reason     Gemini 2.5 Pro: "what is the next step toward the user's goal?"
   ↓
Plan       choose next tool: parallel_search | build_bible | generate_shot_list
           | call_veo | call_chirp | call_lyria | call_imagen
           | run_consistency_check | assemble_film
   ↓
Act        call the chosen tool with structured args
   ↓
Measure    Consistency Check Agent scores the output (drift 0.0–1.0)
   ↓
Learn      if drift > threshold → re-generate with stricter bible injection
           if user edits bible → propagate to affected shots (re-gen prompt)
   ↓
Update     Bible version increments; shot list updates; scores logged (L6)
```

The loop is what makes the system agentic rather than a wrapper
(blueprint Section 22.5): persistent state across the entire film (not per
call), autonomous tool selection among 6 external + 3 internal tools, planning
the research → bible → shot-list → generate → check → assemble sequence,
feedback from the Consistency Check Agent into re-generation decisions, and
measurable drift improvement across re-generations within a project.

## Engineering Strategy (blueprint Section 31)

Repository structure, branch strategy, and CI/CD are defined in blueprint
Section 31. Summary relevant to architecture:

- **Repo layout** (blueprint Section 31.1): `backend/` (FastAPI + agents +
  bible + pipelines + integrations + storage + tests), `frontend/` (Next.js 15
  App Router with `ScriptPane`, `BiblePane`, `ShotGrid`, `RenderQueue`,
  `ResearchPanel`, `ConsistencyDashboard`, `SideBySide`), `infra/`
  (cloudbuild.yaml, terraform/, seed-demo.sh), `.github/workflows/` (ci.yml,
  deploy.yml), plus this file and the four `docs/*.md` references.
- **Branch strategy** (blueprint Section 31.2): `main` (always deployable,
  protected, green CI), `feature/{name}` (short-lived, squash-merged),
  `demo-day` (frozen after Sept 5).
- **CI/CD** (blueprint Section 31.4): PR → lint (ruff, eslint, prettier),
  type-check (mypy, tsc), unit + integration tests, prompt eval; merge to main
  → build Docker, push to Artifact Registry, deploy to dev Cloud Run; manual
  prod deploy via release tag; smoke test hits `/api/health` after every
  deploy.
- **Cloud Run config** (blueprint Section 29.5): min instances 1 (always warm —
  no cold-start demo risk), max 10 (cost cap), concurrency 80, 1 GiB / 1 CPU,
  region us-central1, timeout 300s.
- **Three execution paths** (blueprint Section 28.1): live path (real-time
  generation, 5–8 min), fallback path (pre-rendered canonical demo served from
  Cloud Storage), demo-safe hybrid (pre-rendered demo + one live Veo Light
  generation triggered by a "Watch it live" button).
