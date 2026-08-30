"""
Auteur — Research Agent (blueprint Section 22.2, Table 30).

Grounds creative decisions in real-world references via the Parallel Search API
(the partner integration, called at runtime).

Role: takes a logline + a research objective, calls Parallel Search, caches the
results (24h TTL), synthesizes them into typed References via Gemini, returns
them to the Director Agent.

The UI Research panel streams every Parallel Search query + result in real time.
"""
from __future__ import annotations

import json
from typing import Any

from .adk_registry import research_agent  # ADK integration point
from ..integrations import parallel_search
from ..bible import store
from ..bible.schema import Reference


async def research(
    project_id: str,
    objective: str,
    queries: list[str],
) -> list[Reference]:
    """Run Parallel Search for the objective, return typed References.

    Caches per-project per-query (24h TTL — blueprint Table 28 row 2). If the
    cache has results, Parallel is not re-called. If Parallel is unavailable,
    returns an empty list (the Director falls back to creative inference).
    """
    # 1. Cache check (per query)
    cached = await store.cache_get_search(project_id, objective)
    if cached:
        return [Reference(**r) for r in cached]

    # 2. Call Parallel Search at runtime (REQUIRED by rules §7B)
    try:
        raw = await parallel_search.search(objective, queries, project_id=project_id)
    except Exception as e:
        # Fallback (blueprint Table 40 row 1): empty list; Director uses creative inference
        await store.log_event(project_id, "research_failed", {"error": str(e)[:200]})
        return []

    # 3. Parse the raw Parallel response into flat reference dicts
    refs = parallel_search.parse_references(raw)

    # 4. Cache (24h TTL)
    await store.cache_set_search(project_id, objective, refs)

    await store.log_event(project_id, "research_completed", {
        "objective": objective[:100],
        "results_count": len(refs),
        "search_id": raw.get("search_id", ""),
        "usage": raw.get("usage"),
    })

    return [Reference(**r) for r in refs]
