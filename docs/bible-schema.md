# Auteur — Film Bible Schema Reference

> Film Bible schema reference.
> citation), 23.4 (learning loop). The schema is implemented in
> `backend/bible/schema.py`. This document is the canonical field reference
> for the typed, versioned, citable Film Bible.

## Why the Bible is typed 

The Film Bible is the project's core primitive. It is the persistent,
structured memory that the Director Agent maintains and that every
generation call cites. Three properties make it work:

1. **Typed** — every entry is a Pydantic model with explicit fields; the
   Director cannot write free-form YAML that breaks downstream prompt
   construction.
2. **Versioned** — every edit creates a new immutable snapshot; users can
   roll back to any version at any time.
3. **Citable** — every generation cites which Bible version it used, so
   drift is attributable ("Shot 3 used Bible v2; beard color changed at
   v3; re-generation pending").

## Schema 

The Python source below is from. The
TypeScript mirror lives in `frontend/src/lib/types.ts`.

### `Reference`

A single Parallel Search result, attached to any bible entry that needs
grounding. Each `Reference` is what makes a Bible entry *citable* — it
traces the entry back to a real URL.

| Field | Type | Notes |
|---|---|---|
| `url` | `str` | Source URL (Parallel Search result). |
| `title` | `str` | Page or result title. |
| `snippet` | `str` | Short excerpt returned by Parallel. |
| `image_url` | `Optional[str]` | Image URL if the search returned one (for visual / location modalities). |
| `modality` | `str` | One of `"visual"`, `"factual"`, `"audio"`, `"location"`. Drives which bible entry type it attaches to. |
| `retrieved_at` | `datetime` | When Parallel Search returned this result (used for cache TTL on L4). |

### `CharacterSpec`

A character in the film. The character's `reference_image_url` is what the
Veo 3.1 generation pipeline passes as `reference_type=ASSET` — the
cross-shot consistency primitive (see `ARCHITECTURE.md` model note).

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | Stable ID within the project (e.g., `"ewan"`). |
| `name` | `str` | Display name (e.g., `"Ewan MacLeod"`). |
| `age` | `int` | Used in Veo prompt construction. |
| `appearance` | `str` | Free-text description; injected into the Veo prompt. |
| `reference_image_url` | `Optional[str]` | Imagen 3-generated or user-uploaded. **Note:** on `auteur-506523` Imagen 3 is deprecated; the character reference is generated with `gemini-3-pro-image`. See `ARCHITECTURE.md`. |
| `voice_profile` | `VoiceProfileSpec` | Link to a voice entry (each character has exactly one voice). |
| `wardrobe_ids` | `List[str]` | Links to `WardrobeSpec` entries (a character can have multiple wardrobe options, e.g., interior vs. exterior). |

### `VoiceProfileSpec`

A voice profile. Each character has exactly one. The `chirp_voice_id` is the
Chirp 3 voice clone ID for cross-shot voice consistency.

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | Stable ID (e.g., `"ewan-voice"`). |
| `name` | `str` | Display name (e.g., `"Ewan's voice"`). |
| `gender` | `str` | Used by Chirp 3 voice selection. |
| `age_range` | `str` | E.g., `"50-60"`. |
| `accent` | `str` | E.g., `"Scottish, Hebridean"`. |
| `register` | `str` | One of `"low"`, `"medium"`, `"high"`. |
| `cadence` | `str` | One of `"slow"`, `"medium"`, `"fast"`. |
| `chirp_voice_id` | `Optional[str]` | Chirp 3 voice clone ID. Set when the voice has been cloned; `None` during initial bible build. |

### `WardrobeSpec`

A wardrobe element (coat, hat, etc.) that can be attached to one or more
characters. Always carries a `references` list from Parallel Search.

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | Stable ID (e.g., `"oilskin-coat"`). |
| `name` | `str` | Display name (e.g., `"Ewan's oilskin coat"`). |
| `description` | `str` | Free-text description injected into the Veo prompt. |
| `reference_image_url` | `Optional[str]` | Imagen-generated reference, if any. |
| `references` | `List[Reference]` | Parallel Search results used to ground the wardrobe choice (e.g., "1892 oilskin coat" search). |

### `LocationSpec`

A location. Same shape as `WardrobeSpec` — a description + image + grounded
references.

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | Stable ID (e.g., `"skerryvore"`). |
| `name` | `str` | Display name (e.g., `"Skerryvore Lighthouse, 1892"`). |
| `description` | `str` | Free-text. |
| `reference_image_url` | `Optional[str]` | Imagen-generated location plate. |
| `references` | `List[Reference]` | Parallel Search results for the location (architecture, period, geography). |

### `ScoreMotifSpec`

A musical motif. Each shot's Lyria 2 call uses the `lyria_prompt` field,
which the Director constructs from the motif's key, BPM, and instruments.

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | Stable ID (e.g., `"sea-shanty-d-minor"`). |
| `name` | `str` | Display name (e.g., `"Ewan's theme"`). |
| `key` | `str` | Musical key, e.g., `"D minor"`. |
| `bpm` | `int` | Tempo. |
| `instruments` | `List[str]` | E.g., `["accordion", "fiddle"]`. |
| `lyria_prompt` | `str` | The actual prompt string passed to Lyria 2. |

### `StyleAnchorSpec`

A visual style anchor — color palette, lighting, photographic aesthetic.
Injected into every Veo prompt to enforce a consistent look across shots.

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | Stable ID. |
| `name` | `str` | Display name. |
| `color_palette` | `List[str]` | Hex colors, e.g., `["#0B1F3A", "#E89B3C"]`. |
| `lighting` | `str` | E.g., `"soft fog"`, `"candlelight"`. |
| `photographic_aesthetic` | `str` | E.g., `"19th-century daguerreotype, deep shadows"`. |

### `StoryBeat`

A single story beat. The shot list is generated by decomposing the logline
into ordered beats, each bound to characters and a location.

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | Stable ID. |
| `order` | `int` | 1-based ordering. |
| `description` | `str` | What happens in this beat. |
| `character_ids` | `List[str]` | Characters present in this beat. |
| `location_id` | `str` | The location for this beat. |

### `FilmBible` (top-level)

The top-level container persisted to Firestore `bibles/{projectId}/{version}`
(layer L3 — versioned persistent).

| Field | Type | Notes |
|---|---|---|
| `version` | `int` | Monotonically increasing. v1 is built on `POST /api/projects`. |
| `created_at` | `datetime` | When this version was written. |
| `logline` | `str` | The user's original logline (immutable across versions unless the user re-submits). |
| `characters` | `List[CharacterSpec]` | |
| `locations` | `List[LocationSpec]` | |
| `wardrobes` | `List[WardrobeSpec]` | |
| `voice_profiles` | `List[VoiceProfileSpec]` | |
| `score_motifs` | `List[ScoreMotifSpec]` | |
| `style_anchors` | `List[StyleAnchorSpec]>` | |
| `story_beats` | `List[StoryBeat]` | Ordered by `order`. |
| `research_references` | `List[Reference]` | All Parallel Search results, flattened. The union of every `references` list on every entry. |

## Versioning & Citation 

1. **Every user edit creates a new Bible version** (immutable snapshot). v1
   is never modified; v2, v3, ... are appended. The Firestore path is
   `bibles/{projectId}/{version}` .
2. **Every generation cites which Bible version it used.** The
   `generations` collection stores a `bible_version` field per generation
   . This is the row-level citation.
3. **Drift is therefore attributable.** A drift report cites its
   generation ID, which cites its Bible version, which cites its
   references. Full provenance chain: search result → bible entry →
   generation → drift report .
4. **The user can roll back to any Bible version at any time.** Because
   versions are append-only, rollback is just pointing
   `projects.current_bible_version` at an older integer.

## Provenance chain 

```
Parallel Search result (url, retrieved_at)
        │
        ▼
Bible entry references[]   (Bible v{n}, immutable)
        │
        ▼
Generation (bible_version = n, output_url)
        │
        ▼
Drift report (generation_id, drift_score, breakdown)
```

Every link is queryable. A judge (or user) can ask "why does Shot 3's
character look like this?" and trace it back to the exact Bible version,
and from there to the exact Parallel Search result that grounded the
character's appearance.

## Learning Loop 

Within a single project, the agent "learns" in three senses. (Note:
Auteur does NOT learn across projects for the hackathon — no cross-project
RAG. This is a deliberate scope cut per Section 20; cross-project learning
is a post-hackathon roadmap item.)

1. **Threshold tuning.** Drift thresholds tune per project. If a user keeps
   accepting drift > 0.3, the threshold relaxes. If they keep re-generating
   at drift 0.15, the threshold tightens. Stored on the project, not the
   bible.
2. **Query refinement.** Search queries refine. If the user edits a
   wardrobe description ("oilskin coat" → "weathered yellow oilskin"), future
   Parallel Search queries use the edited terms, producing better-grounded
   references on the next Research Agent call.
3. **Context injection.** Re-generation prompts tighten. Each
   re-generation includes the previous drift breakdown as additional
   context, so Veo 3.1 receives more specific guidance on the second pass.
   This is what produces the measurable drift improvement across
   re-generations within a project (Section 22.5 — "Measurable
   improvement").

## Validation

All inputs are validated with Pydantic schemas (fail-fast — 
Section 24.5). The Pydantic models above are the single source of truth;
the TypeScript types in `frontend/src/lib/types.ts` mirror them, and the
OpenAPI schema generated by FastAPI at `/openapi.json` is the wire
contract.

## Cross-references

- Where the Bible is used: generation pipeline
  (`backend/pipelines/generate.py`), consistency check
  (`backend/agents/consistency.py`), REST API (`docs/api-contract.md`).
- Where the Bible is grounded: Parallel Search integration
  (`docs/partner-integration.md`).
- Architecture overview: [`ARCHITECTURE.md`](../ARCHITECTURE.md).
