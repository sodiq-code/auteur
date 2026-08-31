"""
Auteur — ADK agent registry.

Instantiates the three agents as Google Agent Development Kit (ADK) Agent
objects with their models, instructions, and tool bindings.
"""
from __future__ import annotations

from google.adk import Agent
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

RESEARCH_INSTRUCTION = (
    "You are Auteur's Research Agent. You take a research objective + queries, "
    "call the Parallel Search API at runtime (x-api-key auth), cache the results "
    "(24h TTL), and synthesize typed Reference objects. You are read-only — you "
    "return references to the Director, who writes them into the Bible."
)

research_agent = Agent(
    name="research",
    description="Grounds creative decisions in real-world references via the Parallel Search API.",
    model="gemini-3.1-pro-preview",
    instruction=RESEARCH_INSTRUCTION,
    generate_content_config=_REASONING_CONFIG,
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
