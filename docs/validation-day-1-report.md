# Auteur — Day 1 Validation Report
**Blueprint:** Section 32.2 / 50.2  **Date (UTC):** 2026-08-25T01:05:14.537176+00:00  **Project:** `auteur-506523` / `us-central1`
## Objective
Validate that Veo 3.1 can produce visibly consistent characters across 4 shots in 4 scenes, given a character reference image.
## Models
- **Character reference image:** `gemini-3-pro-image` (blueprint specifies Imagen 3; on this project Imagen 3 is deprecated and the 3.x Gemini image models are only accessible in the `global` region — `gemini-3-pro-image` is the newest accessible, Pro-tier, used here in region `global`).
- **Video generation:** `veo-3.1-fast-generate-001` (blueprint 'Veo 3.1 Light' tier).
- **Reference mechanism:** `reference_images` with `reference_type=ASSET` — the Veo 3.1 persistent subject reference.
- **Consistency check:** `gemini-2.5-pro` (vision).
## Shots
| # | Scene | Status | Elapsed (s) | Size (bytes) |
|---|-------|--------|-------------|--------------|
| 1 | Lamp Room (interior, dusk) | ok | 31.6 | 3625956 |
| 2 | Rocks (coastal, dawn) — medium shot | ok | 44.9 | 3747553 |
| 3 | Interior (candlelight, reading) | ok | 43.8 | 3538234 |
| 4 | Exterior (balcony, stormy sea, dusk) | ok | 44.7 | 3834565 |

## Verdict
**GO**
- Mean overall consistency: **0.815**
- Drift threshold: 0.25
- Rationale: Character identity is held with near-perfect fidelity in Shots 3 and 4. While Shots 1 and 2 have obscured views that prevent full facial confirmation, they maintain strong consistency in wardrobe, context, and visible partial features, and introduce no contradictory information. The overall result is a successful and consistent character portrayal.

### Per-shot drift
| Shot | Scene | face | age | beard | wardrobe | overall |
|------|-------|------|-----|-------|----------|---------|
| 1 | Man polishing the lens of a lighthouse lamp. | 0.6 | 0.7 | 0.5 | 1.0 | 0.7 |
| 2 | Man crouching on wet rocks, placing a green bottle in a tide pool. | 0.0 | 0.7 | 0.8 | 1.0 | 0.6 |
| 3 | Man sitting at a wooden table, looking down at a map with a lantern. | 0.95 | 1.0 | 1.0 | 1.0 | 0.98 |
| 4 | Man standing on top of a lighthouse, holding a lantern up against a stormy sky. | 0.95 | 1.0 | 1.0 | 1.0 | 0.98 |

## Artifacts
- Side-by-side: `docs/validation-day-1.png`
- Manifest: `backend/validation/outputs/day1-manifest.json`
- Character reference: `backend/validation/outputs/character_reference.png`
- Clips: `backend/validation/outputs/shot_*.mp4`

## Decision (per blueprint P812-P814)
- Project is **GO**. Proceed to Day 2.
