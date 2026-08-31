# Auteur — Validation Report

## Objective
Validate that Veo 3.1 can produce visibly consistent characters across 4 shots in 4 scenes, given a character reference image.
## Models
- **Character reference image:** `gemini-3-pro-image` .
- **Video generation:** `veo-3.1-fast-generate-001` .
- **Reference mechanism:** `reference_images` with `reference_type=ASSET` — the Veo 3.1 persistent subject reference.
- **Consistency check:** `gemini-3.1-pro-preview` (vision; Table 31 specifies Gemini 2.5 Pro — upgraded to the current Pro model, in region `global`).
## Shots
| # | Scene | Status | Elapsed (s) | Size (bytes) |
|---|-------|--------|-------------|--------------|
| 1 | Lamp Room (interior, dusk) — face-visible | ok | 44.8 | 3355766 |
| 2 | Rocks (coastal, dawn) — medium shot | ok | 44.9 | 3747553 |
| 3 | Interior (candlelight, reading) | ok | 43.8 | 3538234 |
| 4 | Exterior (balcony, stormy sea, dusk) | ok | 44.7 | 3834565 |

## Verdict
**GO**
- Mean overall consistency: **0.925**
- Drift threshold: 0.25
- Rationale: The character's facial features, age, distinctive salt-and-pepper beard, and specific wardrobe (oilskin coat and cable-knit sweater) remain highly consistent across all four shots, despite changes in lighting, angle, and pose.

### Per-shot drift
| Shot | Scene | face | age | beard | wardrobe | overall |
|------|-------|------|-----|-------|----------|---------|
| 1 | Cleaning the lighthouse lens | 0.95 | 0.95 | 0.95 | 0.95 | 0.95 |
| 2 | Crouching on rocks by the sea | 0.8 | 0.9 | 0.9 | 0.9 | 0.85 |
| 3 | Sitting at a table looking at a document | 0.95 | 0.95 | 0.95 | 0.95 | 0.95 |
| 4 | Standing outside by the sea holding a lantern | 0.95 | 0.95 | 0.95 | 0.95 | 0.95 |

## Artifacts
- Side-by-side: `docs/validation.png`
- Manifest: `backend/validation/outputs/day1-manifest.json`
- Character reference: `backend/validation/outputs/character_reference.png`
- Clips: `backend/validation/outputs/shot_*.mp4`

## Decision
- Project is **GO**. Proceed to Day 2.
