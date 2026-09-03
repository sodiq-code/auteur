# Auteur — Partner Integration (Parallel Search API)

> Parallel Search integration notes. Parallel Search is the
> grounding layer of the Research Agent — every character, location,
> wardrobe, voice, score motif, and style anchor in the Film Bible traces
> back to a real URL it returned. Per the partner-track rules, the call
> site must be visible in the deployed UI at runtime.

## Why this integration exists

The Research Agent grounds creative decisions in real-world references via
the Parallel Search API. Every character, location, wardrobe, voice, score
motif, and style anchor in the Film Bible carries a `references[]` list of
`Reference` objects — each with a `url`, `title`, `snippet`, and `modality`
returned by Parallel. This is what makes the Bible *citable*: every
creative decision traces back to a real URL, not a hallucination.

Without this integration, Auteur would be a fluent liar — generating
plausible-sounding but ungrounded period details. Parallel is the
ground-truth layer.

## The integration

Implemented in two files:

- `backend/agents/research.py` — the agentic loop. The Research Agent
  uses **Google ADK function calling**: Gemini is given a
  `parallel_search` tool declaration, decides what to search for, calls
  the tool, evaluates the results, and decides whether more searches are
  needed. This is a genuine agentic tool-use loop, not a deterministic
  Python pipeline.
- `backend/integrations/parallel_search.py` — the HTTP client. One
  function, `search()`, calls the real Parallel Search API and returns
  the raw response. `parse_references()` maps the Parallel response onto
  the `Reference` schema.

### The agentic loop

```python
# backend/agents/research.py (simplified for clarity)

_SEARCH_FUNCTION_DECLARATION = types.FunctionDeclaration(
    name="parallel_search",
    description="Search the web for real-world references using the Parallel Search API.",
    parameters=types.Schema(
        type="OBJECT",
        properties={"query": types.Schema(type="STRING")},
        required=["query"],
    ),
)

async def research_with_tools(project_id: str, logline: str) -> list[Reference]:
    """The agent decides what to search for via function calling."""
    for round_num in range(5):  # max 5 rounds of searching
        resp = await gemini.pro_client().aio.models.generate_content(
            model="gemini-3.1-pro-preview",
            contents=contents,
            config=types.GenerateContentConfig(tools=[_SEARCH_TOOL]),
        )
        # Gemini may return MULTIPLE function calls in one response
        for part in resp.candidates[0].content.parts:
            fc = getattr(part, "function_call", None)
            if fc and fc.name == "parallel_search":
                query = fc.args.get("query", "")
                # Execute the real Parallel Search API call
                raw = await parallel_search.search(
                    f"Research for film: {logline}", [query], project_id=project_id,
                )
                refs = parallel_search.parse_references(raw)
                # Feed the results back to Gemini so it can decide what to search next
                ...
        if not has_function_call:
            break  # agent is done researching
```

The LLM controls the research trajectory: it decides what to search, how
many times to search, and when it has gathered enough references. Python
just executes the tool calls and feeds results back.

### Auth

- **API key** in the `x-api-key` header (not `Authorization: Bearer`).
  Set as `PARALLEL_API_KEY` in the Cloud Run service environment.
- Server-side only. No client-side secrets — the frontend talks only to
  our FastAPI service.

### Request shape

```http
POST https://api.parallel.ai/v1/search
x-api-key: <PARALLEL_API_KEY>
Content-Type: application/json

{
  "objective": "Research for film: <logline>",
  "search_queries": [
    "1892 Scottish lighthouse keeper oilskin coat",
    "Skerryvore Lighthouse architecture",
    "Victorian sea shanties"
  ]
}
```

The `objective` is the high-level research goal; `search_queries` is the
list of specific queries the LLM generated. Both are sent in a single
request — Parallel runs the queries and returns the combined result set.

### Response shape

```json
{
  "search_id": "...",
  "results": [
    {
      "url": "https://en.wikipedia.org/wiki/Skerryvore",
      "title": "Skerryvore - Wikipedia",
      "publish_date": "2024-01-15",
      "excerpts": ["Skerryvore is a remote..."]
    }
  ],
  "usage": { "total_queries": 3 }
}
```

`parse_references()` extracts each result and maps it onto the
`Reference` schema: `excerpts[0]` becomes `snippet`, `modality` defaults
to `"text"`, `publish_date` is dropped (not in the schema). The cleaned
list is what gets cached and attached to Bible entries.

## Caching

| Aspect | Value |
|---|---|
| Cache store | Firestore `search_cache/{projectId}/{queryHash}` |
| TTL | **24 hours** |
| Read pattern | `store.cache_get_search(project_id, objective)` before any network call |
| Write pattern | `store.cache_set_search(project_id, objective, refs)` after a successful Parallel response |
| Eviction | TTL refreshes on next query; entries are per-project, so a popular query is re-cached per project |

Caching serves two purposes:

1. **Cost.** Per-call Parallel pricing (TBD; estimated $1–5/month at
   hackathon scale). Caching avoids re-searching the same query when
   the Director loops back to the same modality.
2. **Resilience.** If Parallel is down, the cached results are the
   first fallback (see Failure Handling below).

## Visibility — the transparency guarantee

> The UI has a Research panel that shows, in real time, every Parallel
> Search query and result. A visitor testing the deployed URL can see
> the partner API being called live — not a recorded video, not a
> stubbed response.

The Research Panel (`frontend/src/components/auteur/ResearchView.tsx`)
renders:

- Every query as it is sent (e.g., `▶ Searching: "1892 lighthouse keeper
  oilskin coat..."`).
- Each result with its source URL, clickable (e.g., `↳ wikipedia.org/...`,
  `↳ historic-scotland.org/...`).
- A progress indicator while the search is in flight.

Every tool call is also logged to the project's event trail via
`store.log_event(project_id, "agent_tool_call", {...})` — so the
agent's research trajectory is fully auditable after the fact.

## Failure handling

| Failure | Detection | Fallback | User-visible impact |
|---|---|---|---|
| Parallel Search API unavailable | `httpx` timeout / 5xx | Cached search results (if any) **or** an empty `references[]` list | Bible still builds; fewer references |
| Function-calling loop fails | Exception in `research_with_tools()` | Falls back to `research()` (direct call with LLM-generated queries) | Same results, less agentic |
| `PARALLEL_API_KEY` not set | `RuntimeError` from `search()` | Returns empty list, logs `research_failed` | Bible builds with `references: []` |

The Director's contract is: **Research returning zero results is not a
hard error.** It degrades gracefully — the Bible entry carries an empty
`references: []` field, and the UI shows a "no grounding found" badge on
that entry. The event log records the failure for audit.

Additional resilience layers:

- **Per-request timeout:** 30 seconds (`httpx.AsyncClient(timeout=30.0)`).
  Long enough for Parallel to run multiple queries; short enough that
  the live demo doesn't stall.
- **Health probe:** `/api/health` reports `partner_status.parallel_search.configured: true/false`
  based on whether the API key is set.

## Quotas and rate limits

- **Parallel Search API:** per-call pricing TBD; validate in first 48
  hours of integration. Cache (24h TTL) is the primary rate-limit
  mitigation.
- **Vertex AI (Gemini 3.1 Pro for the function-calling loop):** standard
  Vertex AI quota per project.

## Cost

- Per `logline → research complete`: ~5 Parallel queries × ~$0.001 each
  ≈ $0.01 + Gemini 3.1 Pro function-calling ≈ $0.02 total.
- Estimated monthly partner cost at normal usage: $1–5. Well within
  the $100 Google Cloud credit budget.

## Stress test

**Kill the Parallel API key; reload the app; verify graceful
degradation.** Expected: the Research Panel shows "Research unavailable"
notes on each query; the Bible still builds with empty `references[]`
on affected entries; the rest of the pipeline (Veo / Chirp / Lyria /
Imagen / Consistency) still works. This test is run before every
operations submission.

## Cross-references

- Architecture & model note: [`ARCHITECTURE.md`](../ARCHITECTURE.md).
- REST API surface (incl. `/api/health` `partner_status`):
  [`docs/api-contract.md`](api-contract.md).
- `Reference` Pydantic model used by the cache + parse step:
  [`docs/bible-schema.md`](bible-schema.md).
- Demo script showing the Research Panel in Beat 3:
  [`docs/demo-script.md`](demo-script.md).
