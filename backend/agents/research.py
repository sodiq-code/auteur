"""
Auteur — Research Agent (Section 22.2, Table 30).

Grounds creative decisions in real-world references via the Parallel Search API
(the partner integration, called at runtime as an ADK function tool).

The Research Agent uses function calling: the LLM decides what to search for,
calls the parallel_search tool, evaluates the results, and decides whether
more searches are needed. This is a genuine agentic tool-use loop, not a
deterministic Python pipeline.

The UI Research panel streams every Parallel Search query + result in real time.
"""
from __future__ import annotations

import json
from typing import Any

from google.genai import types

from .adk_registry import research_agent
from ..integrations import parallel_search
from ..integrations import gemini
from ..bible import store
from ..bible.schema import Reference


# The function declaration for the parallel_search tool.
# This is what Gemini sees — it decides when to call it and what query to pass.
_SEARCH_FUNCTION_DECLARATION = types.FunctionDeclaration(
    name="parallel_search",
    description=(
        "Search the web for real-world references using the Parallel Search API. "
        "Use this to find historical, cultural, architectural, fashion, and musical "
        "references for the film. You can call this tool multiple times with "
        "different queries."
    ),
    parameters=types.Schema(
        type="OBJECT",
        properties={
            "query": types.Schema(
                type="STRING",
                description="The specific search query (e.g., '1920s Shanghai architecture')",
            ),
        },
        required=["query"],
    ),
)

_SEARCH_TOOL = types.Tool(function_declarations=[_SEARCH_FUNCTION_DECLARATION])


async def research_with_tools(project_id: str, logline: str) -> list[Reference]:
    """The Research Agent uses function calling to decide when/how to search.

    This is the genuine agentic loop:
    1. Gemini is given the parallel_search tool
    2. Gemini decides what to search for
    3. Python executes the search (calls the real Parallel API)
    4. Gemini evaluates the results
    5. Gemini decides if more searches are needed
    6. Repeat until Gemini is satisfied

    Every tool call is logged so the UI can display the agent's research
    trajectory.

    Falls back to the old `research()` function if function calling fails.
    """
    # Check cache first
    cached = await store.cache_get_search(project_id, logline)
    if cached:
        return [Reference(**r) for r in cached]

    # Build the initial prompt — tell Gemini it has a tool and what to research
    prompt = (
        f"{research_agent.instruction}\n\n"
        f"LOGLINE: {logline}\n\n"
        "Determine what factual information is needed to ground this film in reality. "
        "Use the parallel_search tool to search for references covering: the era/time "
        "period, the location/setting, the clothing/wardrobe of the era, the "
        "music/cultural context, and any specific historical or technical details "
        "mentioned in the logline.\n\n"
        "You may call parallel_search multiple times with different queries. "
        "After each search, evaluate whether the results are sufficient or if "
        "you need to search for additional information.\n\n"
        "When you have gathered enough references, stop calling the tool and "
        "respond with a brief summary of what you found."
    )

    # Build the conversation as Content objects
    contents = [
        types.Content(role="user", parts=[types.Part(text=prompt)])
    ]

    all_refs: list[dict] = []
    search_count = 0

    try:
        for round_num in range(5):  # max 5 rounds of searching
            # Call Gemini with the tool available
            cfg = types.GenerateContentConfig(
                temperature=research_agent.generate_content_config.temperature or 0.3,
                tools=[_SEARCH_TOOL],
            )
            resp = await gemini.pro_client().aio.models.generate_content(
                model="gemini-3.1-pro-preview",
                contents=contents,
                config=cfg,
            )

            # Add the model's response to the conversation
            if resp.candidates and resp.candidates[0].content:
                contents.append(resp.candidates[0].content)

            # Check for function calls
            has_function_call = False
            if resp.candidates and resp.candidates[0].content:
                for part in resp.candidates[0].content.parts:
                    fc = getattr(part, "function_call", None)
                    if fc and fc.name == "parallel_search":
                        has_function_call = True
                        search_count += 1
                        query = fc.args.get("query", "")

                        # Log the agent's tool call
                        await store.log_event(project_id, "agent_tool_call", {
                            "tool": "parallel_search",
                            "query": query,
                            "round": round_num + 1,
                            "source": "llm_function_call",
                        })

                        # Execute the real Parallel Search API call
                        try:
                            raw = await parallel_search.search(
                                f"Research for film: {logline}",
                                [query],
                                project_id=project_id,
                            )
                            refs = parallel_search.parse_references(raw)
                            all_refs.extend(refs)

                            result_str = json.dumps(refs[:5])  # limit to 5 per search

                            await store.log_event(project_id, "agent_tool_result", {
                                "tool": "parallel_search",
                                "query": query,
                                "results_count": len(refs),
                                "round": round_num + 1,
                            })
                        except Exception as e:
                            result_str = json.dumps({"error": str(e)[:200]})

                        # Feed the function response back to Gemini
                        func_response = types.Part(
                            function_response=types.FunctionResponse(
                                name="parallel_search",
                                response={"results": result_str},
                            )
                        )
                        contents.append(
                            types.Content(role="user", parts=[func_response])
                        )

            if not has_function_call:
                # No more tool calls — the agent is done researching
                break

    except Exception as e:
        # If function calling fails, fall back to the old research method
        await store.log_event(project_id, "research_tool_calling_failed", {
            "error": str(e)[:200],
        })
        return await research(
            project_id,
            f"Research for film: {logline}",
            [logline, f"historical context: {logline}"],
        )

    # Deduplicate refs by URL
    seen_urls = set()
    unique_refs = []
    for r in all_refs:
        url = r.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_refs.append(r)

    # Cache the results
    if unique_refs:
        await store.cache_set_search(project_id, logline, unique_refs)

    await store.log_event(project_id, "research_completed", {
        "method": "agent_tool_calling",
        "total_searches": search_count,
        "total_references": len(unique_refs),
    })

    return [Reference(**r) for r in unique_refs]


async def research(
    project_id: str,
    objective: str,
    queries: list[str],
) -> list[Reference]:
    """Fallback: run Parallel Search with provided queries (non-agentic).

    Used as a fallback if the function-calling loop fails.
    """
    cached = await store.cache_get_search(project_id, objective)
    if cached:
        return [Reference(**r) for r in cached]

    try:
        raw = await parallel_search.search(objective, queries, project_id=project_id)
    except Exception as e:
        await store.log_event(project_id, "research_failed", {"error": str(e)[:200]})
        return []

    refs = parallel_search.parse_references(raw)
    await store.cache_set_search(project_id, objective, refs)

    await store.log_event(project_id, "research_completed", {
        "method": "fallback_direct",
        "results_count": len(refs),
    })

    return [Reference(**r) for r in refs]
