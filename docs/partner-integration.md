# Auteur — Partner Integration (Parallel Search API)

> Parallel Search integration notes.
> API), Table 37 (External API matrix), Table 40 Row 1 (failure handling),
> Section 5.3 (anti-anti-pattern mitigation). This is the most important
> external integration: per Rules §7B, Parallel Search **MUST** be called
> at runtime, and the call site **must be visible to judges testing the
> deployed URL**.

## Why this integration exists 

The Research Agent grounds creative decisions in real-world references via
the Parallel Search API. Every character, location, wardrobe, voice, score
motif, and style anchor in the Film Bible carries a `references[]` list of
`Reference` objects — each with a `url`, `title`, `snippet`, and `modality`
returned by Parallel. This is what makes the Bible *citable* (
Section 23.3): every creative decision traces back to a real URL, not a
hallucination.

Without this integration, Auteur would be a fluent liar — generating
plausible-sounding but ungrounded period details. Parallel is the
ground-truth layer.

## The integration 

Implemented in `backend/agents/research.py` (or `integrations/parallel_search.py`,
per Section 31.1). The class below is reproduced verbatim from
P668-P658.

```python
# agents/research_agent.py
from google.adk import Agent
from google.cloud import aiplatform
from typing import List
import os, httpx

class ResearchAgent(Agent):
    """Grounds creative decisions via Parallel Search API."""

    async def search(self, query: str, modality: str) -> List[Reference]:
        # 1. Check cache (Firestore L4)
        cached = await self._cache_get(query)
        if cached:
            return cached

        # 2. Call Parallel Search API at runtime (required at runtime)
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.parallel.ai/v1/search",
                headers={"x-api-key": os.environ["PARALLEL_API_KEY"]},
                json={"query": query, "num": 10, "modality": modality}
            )
            resp.raise_for_status()
            results = resp.json()["results"]

        # 3. Synthesize via Gemini 2.5 Flash
        synthesized = await self._gemini_synthesize(query, results)

        # 4. Cache (24h TTL)
        await self._cache_set(query, synthesized)

        return synthesized

    async def _gemini_synthesize(self, query: str, raw_results: list) -> List[Reference]:
        # Gemini 2.5 Flash call with structured output
        model = aiplatform.GenerativeModel("gemini-2.5-flash")
        prompt = f"""You are extracting structured references for a film research query.
Query: {query}
Raw search results: {raw_results}

Return JSON array of references, each with: url, title, snippet, image_url (if available), modality.
Only include results directly relevant to the query."""
        resp = await model.generate_content_async(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        return [Reference(**r) for r in resp.json()]
```

### Auth

- **API key** in the `x-api-key` header: `x-api-key: ${PARALLEL_API_KEY}`.
  (The Parallel Search API uses `x-api-key`, not `Authorization: Bearer`.)
- `PARALLEL_API_KEY` is provisioned in **Google Secret Manager** and
  injected into the Cloud Run service as an env var at deploy time
  .
- Server-side only. No client-side secrets — the frontend talks only to
  our FastAPI service .

### Request shape

```json
POST https://api.parallel.ai/v1/search
x-api-key: <PARALLEL_API_KEY>
Content-Type: application/json

{
  "query": "1892 Scottish lighthouse keeper oilskin coat",
  "num": 10,
  "modality": "visual"
}
```

`modality` is one of `"visual"`, `"factual"`, `"audio"`, `"location"` —
matching the `Reference.modality` enum in `docs/bible-schema.md`. The
Research Agent formulates both the query and the modality based on the
Director's request .

### Response shape

```json
{
  "results": [
    { "url": "...", "title": "...", "snippet": "...", "image_url": "..." },
    ...
  ]
}
```

Raw results are then passed through Gemini 2.5 Flash synthesis to produce
a clean `List[Reference]` (filtering out irrelevant hits, normalizing the
schema). The synthesized list is what gets cached and what gets attached
to a Bible entry's `references[]` field.

## Caching 

| Aspect | Value |
|---|---|
| Cache store | Firestore `search_cache/{projectId}/{queryHash}` (layer L4) |
| TTL | **24 hours**  |
| Read pattern | Per Research Agent call — `_cache_get(query)` before any network call |
| Write pattern | On cache miss — `_cache_set(query, synthesized)` after a successful Parallel response |
| Eviction | TTL refreshes on next query; entries are per-project, so a popular query is re-cached per project |

Caching serves two purposes:

1. **Cost.** Per-call Parallel pricing (TBD; estimated $1–5/month at hackathon
   scale, Table 42, Row 7). Caching avoids re-searching the same
   query when the Director loops back to the same modality.
2. **Resilience.** If Parallel is down, the cached results are the first
   fallback (see Failure Handling below).

## Synthesis via Gemini 2.5 Flash

The Director never reads raw Parallel results. The Research Agent
synthesizes them through `gemini-2.5-flash` with structured JSON output
(`response_mime_type: "application/json"`) into a list of `Reference`
objects that match the `bible/schema.py` Pydantic model. This is what
guarantees the Bible's `references[]` field is always well-typed.

Why Gemini Flash and not Pro? Table 30, Row 2: "Faster, cheaper,
sufficient for query formulation + result synthesis." Table 34,
Row 2: Flash is the right model for search-synthesis; Pro would be overkill.

## Visibility — the #1 anti-anti-pattern mitigation 

> "The UI has a 'Research' panel that shows, in real-time, every Parallel
> Search query and result. A judge testing the deployed URL can see the
> partner API being called live. This is the #1 anti-anti-pattern
> mitigation (Section 5.3)." — P670.

The Research Panel (`frontend/src/components/ResearchPanel.tsx`
Section 30.2) renders:

- Every query as it is sent (e.g., `▶ Searching: "1892 lighthouse keeper
  oilskin coat..."`).
- Each result with its source URL, clickable (e.g., `↳ wikipedia.org/...`,
  `↳ historic-scotland.org/...`).
- A progress indicator while the search is in flight.

This is non-negotiable for the partner track. A judge who opens the
deployed URL, types a logline, and watches the Research Panel populate
sees the partner API being called at runtime — not a recorded video, not
a stubbed response. The companion UI requirement is that **the live
generation endpoint streams a `research_started` / `research_completed`
SSE event** so the Research Panel updates without polling (see
`docs/api-contract.md` Row 6).

## Failure handling 

| Failure | Detection | Fallback | User-visible impact |
|---|---|---|---|
| Parallel Search API unavailable | `httpx` timeout / 5xx | Cached search results (if any) **or** a clearly-labeled "Research unavailable — using creative inference" note | Bible still builds; fewer references |

The Director's contract is: **Research returning zero results is not a
hard error.** It degrades gracefully:

1. If a cached result exists for the query, return it (with a `cached_at`
   timestamp shown in the UI).
2. If no cache exists, the Research Agent returns an empty list and the
   Director proceeds with **clearly-labeled "creative inference"** —
   never asserted as fact . The Bible entry
   carries a `references: []` field, and the UI shows a "no grounding
   found" badge on that entry.
3. The event log records `research_failed (query, error)` for audit.

Additional resilience layers:

- **Retry with exponential backoff:** max 5 retries on 429 / 5xx
  .
- **Per-query timeout:** 10 seconds (the `httpx.AsyncClient(timeout=10.0)`
  in the source above). Long enough for Parallel to respond; short enough
  that the live demo doesn't stall.
- **Health probe:** `/api/health` returns `partner_status: "ok"` if a test
  query completes within 10s; `"degraded"` if returning cached results
  (see `docs/api-contract.md` Row 14). The operations runbook checks this
  at 00:05 .

## Quotas and rate limits

- **Parallel Search API:** per-call pricing TBD; validate in first 48 hours
  of integration . Cache (24h TTL) is the
  primary rate-limit mitigation.
- **Vertex AI (for the Gemini Flash synthesis step):** standard Vertex AI
  quota per project; retries with backoff .

## Cost 

- Per `logline → research complete`: ~5 Parallel queries × ~$0.001 each =
  ~$0.01 + Gemini Flash synthesis ≈ $0.01 total .
- Estimated monthly partner cost at normal usage: $1–5 (
  Table 42, Row 7). Well within the $100 Google Cloud credit budget.

## Stress test 

Test 1 : **Kill the Parallel API key; reload the app;
verify graceful degradation.** Expected: the Research Panel shows
"Research unavailable — using creative inference" notes on each query;
the Bible still builds with empty `references[]` on affected entries; the
rest of the pipeline (Veo / Chirp / Lyria / Imagen / Consistency) still
works. This test is run before every operations submission.

## Cross-references

- Architecture & model note: [`ARCHITECTURE.md`](../ARCHITECTURE.md).
- REST API surface (incl. `/api/health` `partner_status`):
  [`docs/api-contract.md`](api-contract.md).
- `Reference` Pydantic model used by the cache + synthesis:
  [`docs/bible-schema.md`](bible-schema.md).
- Demo script showing the Research Panel in Beat 3:
  [`docs/demo-script.md`](demo-script.md).
