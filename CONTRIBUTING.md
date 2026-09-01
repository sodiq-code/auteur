# Contributing to Auteur

Auteur is a hackathon build of an agentic film studio. We keep the
contribution path lightweight so changes can land quickly without
sacrificing the invariants that make the system work.

## The four invariants

These must hold for any contribution to merge:

1. **The Film Bible is the source of truth.** No generation call may
   be made without the relevant Bible section (character / wardrobe /
   location / score motif) injected as structured context.
2. **The loop is closed.** Every `POST /generate` is followed by a
   Consistency Check. Drift above threshold feeds back into
   `POST /regenerate` as corrective context. If you add a generation
   path, you add its check path.
3. **Google-native only.** Veo, Chirp, Lyria, Gemini, Imagen. No
   OpenAI / Anthropic / LangChain. Parallel Search is the only
   sanctioned external partner.
4. **The demo must never go dark.** The pre-rendered canonical demo
   at `GET /api/demo` is the safety net for demo day. Don't remove it,
   don't make it depend on a live API call.

## Workflow

1. Branch off `main`: `git checkout -b feat/your-thing`.
2. Make the change. Keep commits descriptive — see `git log` for tone.
3. Verify locally:
   - Backend: `cd backend && python -c "from main import app"`
   - Frontend: `cd frontend && bun install && bun run lint`
   - Live smoke: `curl https://auteur-app-jbkbgthudq-uc.a.run.app/api/health`
4. Push + open a PR. Use the PR template — fill the "Evidence" section,
   it is not optional.
5. Squash-merge on approval.

## What not to commit

- `.env`, `*-sa-key.json`, service-account credentials of any kind.
- Generated MP4s / PNGs / WAVs from a real run (those go in Cloud Storage,
  not the repo). The only committed media are the canonical demo assets
  under `frontend/public/demo/` and `backend/character_reference.png`,
  which exist as fallback evidence.
- `node_modules/`, `.next/`, `__pycache__/`, `.venv/`.
- Draft docs or planning notes. The repo is the public face of the
  project to hackathon judges.

## Repo layout

```
backend/      FastAPI app (agents, integrations, pipelines, storage)
frontend/     Next.js 16 studio UI (the only user-visible route is /)
docs/         Architecture, API contract, validation report, demo script
infra/        Cloud Build + Cloud Run deploy scripts
```

## Deploy

`main` is deployed via `infra/deploy-unified.py` (Cloud Build → Artifact
Registry → Cloud Run, unified service on port 3000 + FastAPI on 8000).

## License

By contributing you agree your contributions are licensed MIT, same as
the rest of the project.
