"""
Auteur — ADK agent registry.

Instantiates the three agents as Google Agent Development Kit (ADK) Agent
objects with their models, instructions, and tool bindings.

The Research Agent has the `parallel_search` function registered as an ADK
FunctionTool — the LLM decides when and how to call it, making this a
genuine agentic tool-use loop rather than a deterministic Python pipeline.
"""
from __future__ import annotations

from google.adk import Agent
from google.adk.tools import FunctionTool
from google.genai import types

_REASONING_CONFIG = types.GenerateContentConfig(temperature=0.2)

DIRECTOR_INSTRUCTION = (
    "You are Auteur's Director Agent. You receive a film logline and orchestrate "
    "the full pipeline: research the era/setting via the Research Agent, synthesize "
    "a typed Film Bible (characters, locations, wardrobes, voices, score motifs, "
    "style anchors, story beats), generate a 4-shot list, call Veo 3.1 + Chirp 3 + "
    "Lyria 2 per shot with the Bible injected as context, run the Consistency Check "
    "Agent on each output, and assemble the final film. You delegate to specialist "
    "agents; you do not call Parallel Search directly."
)

director_agent = Agent(
    name="director",
    description="Top-level orchestrator. Logline in, plans the pipeline, delegates to Research and Consistency.",
    model="gemini-3.1-pro-preview",
    instruction=DIRECTOR_INSTRUCTION,
    generate_content_config=_REASONING_CONFIG,
)

# The parallel_search function tool — registered on the Research Agent.
# The LLM decides what query to pass and when to call it.
# The actual execution is handled by the function-calling loop in research.py.
async def parallel_search(query: str) -> str:
    """Search the web for real-world references using the Parallel Search API.

    Use this tool to find historical, cultural, architectural, fashion, and
    musical references for the film. You can call this tool multiple times
    with different queries.

    Args:
        query: The specific search query (e.g., "1920s Shanghai architecture")
    """
    # This is a stub — the actual execution happens in research_with_tools()
    # which intercepts the function call and routes it to the real Parallel
    # Search API. The stub exists so ADK can generate the tool schema.
    return "[]"

parallel_search_tool = FunctionTool.from_function(parallel_search)

RESEARCH_INSTRUCTION = (
    "You are Auteur's Research Agent. Your job is to ground a film in real-world "
    "evidence by determining what factual information is needed and using the "
    "parallel_search tool to find it. "
    "\n\n"
    "Before producing references, determine what factual information is "
    "needed from the logline: historical era, location/setting, clothing/wardrobe, "
    "cultural context, slang, architecture, lighting, music, and period details. "
    "\n\n"
    "Use parallel_search whenever external grounding would improve the film's "
    "accuracy. You may issue multiple searches when the first result set is "
    "insufficient. Do not invent factual references when relevant external "
    "grounding is available. "
    "\n\n"
    "Return a brief summary of what you found after your searches are complete."
)

research_agent = Agent(
    name="research",
    description="Grounds creative decisions in real-world references via the Parallel Search API.",
    model="gemini-3.1-pro-preview",
    instruction=RESEARCH_INSTRUCTION,
    generate_content_config=_REASONING_CONFIG,
    tools=[parallel_search_tool],
)

CONSISTENCY_INSTRUCTION = (
    "You are Auteur's Consistency Check Agent. You receive a character reference "
    "image and a video frame from a generated shot. You score the match on five "
    "dimensions (face_identity, age_appearance, beard_facial_hair, wardrobe, "
    "overall) on a 0.0-1.0 scale via a fixed rubric, and recommend accept or "
    "re-generate (threshold: overall >= 0.75 to accept). You are stateless and "
    "read-only — you flag, you do not modify."
)

consistency_agent = Agent(
    name="consistency",
    description="Scores per-shot drift against the character reference via Gemini Vision.",
    model="gemini-3.1-pro-preview",
    instruction=CONSISTENCY_INSTRUCTION,
    generate_content_config=_REASONING_CONFIG,
)

AGENTS: dict[str, Agent] = {
    "director": director_agent,
    "research": research_agent,
    "consistency": consistency_agent,
}
