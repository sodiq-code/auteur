# Auteur — The Film Bible Agent

> **AI cinema's memory. Grounded in reality. Consistent across every shot.**

Auteur is an agentic AI film studio that maintains a persistent, research-grounded
**Film Bible** (characters, locations, wardrobes, voices, score motifs, style anchors,
story beats) and enforces **cross-shot consistency** across every Veo 3.1, Chirp 3,
Lyria 2, and Imagen 3 generation call.

Built for the **Agentic Cinema Hackathon** (Google Cloud × Devpost · Parallel Partner
Track · submission deadline September 9, 2026).

---

## The insight

AI cinema's biggest unsolved problem is **not** video quality — Veo 3.1 and Sora 2
already produce gorgeous individual clips. The problem is **consistency**: characters
drift across shots, wardrobes mutate, voices lose continuity, color grades don't match.
No commercial product ships a persistent project-memory layer that every generation
call must obey. **Auteur is that layer.**

The bottleneck in AI cinema is memory, not generation. Every existing tool treats each
generation call as stateless. Auteur makes the agent stateful across the entire film.

## Core innovation — the Film Bible persistence-and-injection layer

A typed schema (Pydantic) stored in Firestore, **versioned**, **citable**, and injected
as structured context into every Veo 3.1 / Chirp 3 / Lyria 2 / Imagen 3 call. This
converts cross-shot consistency from a *model-capability* problem (which the models do
not solve) into a *software-architecture* problem (which Auteur solves).

The signature demo moment: a **side-by-side** of the same logline, the same character
reference, four shots across four scenes — once generated **without** the Film Bible
(chaotic drift), once generated **with** the Film Bible (visibly consistent). The visual
proof is immediate, undeniable, and impossible to forget.

## Stack (100% Google-native)

| Layer | Choice | Why |
|------|--------|-----|
| LLM (orchestration + vision) | gemini-3.1-pro-preview via Vertex AI (global region) | REQUIRED by rules; best frontier model |
| Agent framework | Google Agent Development Kit (ADK) | REQUIRED by rules (stack lock) |
| Video | Veo 3.1 (Light for iteration, Standard for final) | REQUIRED + best fit (character ref images) |
| Voice | Chirp 3 | REQUIRED + best fit |
| Music | Lyria 2 | REQUIRED |
| Image | Imagen 3 (see note below) | REQUIRED |
| Persistence | Firestore | Serverless, schema-flexible |
| Object storage | Cloud Storage | For rendered MP4s and storyboards |
| Deployment | Cloud Run | Serverless, autoscaling |
| Partner integration | **Parallel Search API** (called at runtime, visible in UI) | Grounded imagination |

> **Image-model note:** the blueprint specifies Imagen 3 for character reference / storyboard generation. On the project used for this submission (`auteur-506523`), Imagen 3 is deprecated AND the 3.x Gemini image models are listed but ONLY accessible in the `global` region (they 404 in `us-central1`). `gemini-3-pro-image` (Pro tier, 3.x generation) is the newest accessible Google Cloud image model — used here via `generate_content(response_modalities=["IMAGE"])` in the `global` region. The iteration tier for storyboards (Day 7+) is `gemini-3.1-flash-image`. See `docs/validation-day-1-report.md` for the full Day-1 model discovery.

> **LLM-model note:** the blueprint specifies Gemini 2.5 Pro (Table 31) for the Director Agent and the Consistency Check. `gemini-2.5-pro` works but is the older generation. `gemini-3-pro-preview` 404s on this project; `gemini-3.1-pro-preview` is the newest accessible Pro model (text + vision), available only in the `global` region. Used for the Consistency Check here; will be the Director Agent's reasoning model (Day 6+).

## Partner-track declaration

**Parallel Partner Track.** The Parallel Search API is called at runtime by Auteur's
Research Agent to ground every creative decision (era, location, fashion, slang, music,
lighting) in real-world references. The call site is visible to judges in the live
**Research panel** of the deployed UI — every query and result streams in real time.

## Repository structure

```
auteur/
├── README.md                  # this file
├── LICENSE                    # MIT
├── ARCHITECTURE.md            # component justification + data flow
├── .env.example               # all required env vars
├── docs/
│   ├── validation-day-1.png          # Day 1 cross-shot consistency evidence
│   ├── validation-day-1-report.md    # Day 1 GO/PARTIAL/NO verdict
│   ├── api-contract.md               # REST API reference (blueprint Table 38)
│   ├── bible-schema.md               # Film Bible schema reference (blueprint §23)
│   ├── demo-script.md                # 5-beat demo script (blueprint §40)
│   └── partner-integration.md        # Parallel Search integration notes (blueprint §26.3)
├── backend/
│   ├── requirements.txt
│   ├── validation/
│   │   ├── day1_validate_consistency.py   # Day 1 validation script
│   │   └── outputs/                        # generated artifacts (char ref, 4 clips, manifest)
│   ├── agents/                # Director / Research / Consistency (ADK)
│   ├── bible/                 # schema.py, store.py, versioning.py
│   ├── pipelines/             # generate.py, assemble.py, check.py
│   ├── integrations/          # parallel_search, veo, chirp, lyria, imagen, gemini
│   ├── api/                   # FastAPI routes
│   ├── prompts/               # version-controlled prompts + eval cases
│   └── storage/               # firestore, cloud_storage
├── frontend/                  # Next.js 15 (App Router) — studio UI
└── infra/
    ├── cloudbuild.yaml
    └── seed-demo.sh           # pre-render the canonical 4-shot demo
```

## Quickstart (local)

```bash
# 1. Clone
git clone https://github.com/sodiq-code/auteur.git
cd auteur

# 2. Backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt

# 3. Configure
cp .env.example .env
# edit .env: set PARALLEL_API_KEY, GOOGLE_APPLICATION_CREDENTIALS, GCP_PROJECT_ID

# 4. Run the Day 1 validation (proves Veo 3.1 cross-shot consistency)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/auteur-sa-key.json \
GCP_PROJECT_ID=auteur-506523 \
python3 backend/validation/day1_validate_consistency.py

# 5. Open the evidence
open docs/validation-day-1.png
cat docs/validation-day-1-report.md
```

## Day-by-day execution plan

This repo is built strictly following the blueprint's 15-day day-by-day plan
(blueprint Section 32). Each day's task is verified before the next begins.

| Day | Phase | Goal | Status |
|-----|-------|------|--------|
| 1 (Aug 25) | Validation | Veo 3.1 cross-shot consistency validated | ✅ this commit |
| 2 (Aug 26) | Validation + setup | Parallel + Veo + Chirp + Lyria + Imagen end-to-end script | ☐ |
| 3 (Aug 27) | Skeleton | FastAPI + Cloud Run, `/api/health` 200 | ☐ |
| 4 (Aug 28) | Skeleton | UI shell — all 12 screens routed | ☐ |
| 5 (Aug 29) | Bible + research | Parallel Search live in UI | ☐ |
| 6 (Aug 30) | Bible + research | Director Agent → Bible v1 in Firestore | ☐ |
| 7 (Aug 31) | Generation | Veo/Chirp/Lyria/Imagen pipeline + render queue | ☐ |
| 8 (Sep 1) | Generation | Shot grid + ffmpeg assembly | ☐ |
| 9 (Sep 2) | Consistency | Drift scores + re-generation flow | ☐ |
| 10 (Sep 3) | Export + share | Full user journey end-to-end | ☐ |
| 11 (Sep 4) | Safety net | Pre-rendered canonical 4-shot demo | ☐ |
| 12 (Sep 5) | UX polish | Side-by-side signature moment | ☐ |
| 13 (Sep 6) | Demo video | 3-min demo on YouTube | ☐ |
| 14 (Sep 7) | Hardening | README + ARCHITECTURE + smoke tests | ☐ |
| 15 (Sep 8-9) | Submit | Devpost submission | ☐ |

## License

MIT — see [`LICENSE`](./LICENSE).

## Links

- Hackathon: <https://agentic-cinema.devpost.com/>
- Repo: <https://github.com/sodiq-code/auteur>
- Blueprint: `Auteur_GrandPrize_Blueprint_2026-08-25.docx` (internal)
