# Auteur prompts (blueprint Section 25.3)

All prompts are version-controlled in this directory. Each prompt has:
- System prompt (role + constraints)
- User prompt template (with typed inputs)
- Few-shot examples (where helpful)
- Output schema (Pydantic model)
- Eval cases (5-10 input/output pairs)

## Prompt inventory

| File | Agent | Purpose | Output schema |
|------|-------|---------|---------------|
| `director_system.md` | Director Agent | Top-level orchestration role + constraints | FilmBible (bible/schema.py) |
| `research_system.md` | Research Agent | Grounds creative decisions in Parallel Search results | List[Reference] |
| `consistency_system.md` | Consistency Check Agent | Verifies shot matches bible references | DriftReport |

The actual prompt templates live in the agent modules (`backend/agents/*.py`) as
inline strings (so they're co-located with the schema they produce). This
directory holds the human-readable system prompts + eval cases.
