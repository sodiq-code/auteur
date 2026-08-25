# Auteur — Day 1 Validation Report
**Blueprint:** Section 32.2 / 50.2  **Date (UTC):** 2026-08-25T00:34:23.481628+00:00  **Project:** `auteur-506523` / `us-central1`
## Objective
Validate that Veo 3.1 can produce visibly consistent characters across 4 shots in 4 scenes, given a character reference image.
## Models
- **Character reference image:** `gemini-2.5-flash-image` (blueprint specifies Imagen 3; on this project Imagen 3 is deprecated and `gemini-2.5-flash-image` is the supported successor).
- **Video generation:** `veo-3.1-fast-generate-001` (blueprint 'Veo 3.1 Light' tier).
- **Reference mechanism:** `reference_images` with `reference_type=ASSET` — the Veo 3.1 persistent subject reference.
- **Consistency check:** `gemini-2.5-pro` (vision).
## Shots
| # | Scene | Status | Elapsed (s) | Size (bytes) |
|---|-------|--------|-------------|--------------|
| 1 | Lamp Room (interior, dusk) | ok | 44.7 | 3458786 |
| 2 | Rocks (coastal, dawn) | ok | 44.1 | 4151015 |
| 3 | Interior (candlelight, reading) | ok | 30.1 | 2705307 |
| 4 | Exterior (balcony, stormy sea, dusk) | ok | 30.3 | 3089220 |

## Verdict
**GO**
- Mean overall consistency: **0.94**
- Drift threshold: 0.25
- Rationale: Character consistency is exceptionally high across all four shots. Facial identity, age, beard, and wardrobe are maintained with remarkable fidelity to the reference image and across different scenes, lighting conditions, and camera angles. The character 'Ewan' is successfully realized as a persistent asset.

### Per-shot drift
| Shot | Scene | face | age | beard | wardrobe | overall |
|------|-------|------|-----|-------|----------|---------|
| 1 | Character tending to the lighthouse lamp. | 0.95 | 1.0 | 1.0 | 0.9 | 0.95 |
| 2 | Character walking on a rocky shore near the sea. | 0.75 | 1.0 | 0.9 | 1.0 | 0.85 |
| 3 | Character reading a letter by candlelight. | 1.0 | 1.0 | 1.0 | 0.9 | 0.95 |
| 4 | Character looking towards the camera on a balcony overlooking the sea. | 0.95 | 1.0 | 1.0 | 1.0 | 1.0 |

## Artifacts
- Side-by-side: `docs/validation-day-1.png`
- Manifest: `backend/validation/outputs/day1-manifest.json`
- Character reference: `backend/validation/outputs/character_reference.png`
- Clips: `backend/validation/outputs/shot_*.mp4`

## Decision (per blueprint P812-P814)
- Project is **GO**. Proceed to Day 2.
