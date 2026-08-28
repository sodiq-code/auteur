# Auteur — End-to-End API Validation Report
**Blueprint:** Section 32.2 / 50.3  
**Date (UTC):** 2026-08-25T01:52:55.781499+00:00  
**Project:** `auteur-506523`
## Objective
Confirm all 5 production APIs (Parallel Search, image, Veo, TTS, Lyria) return successfully within budget (< $1) and reasonable latency (< 6 min), and that the bible-synthesis path produces a coherent Film Bible from the logline.
## Models used (with blueprint substitutions)
| Blueprint | Actual model | Region | Notes |
|-----------|--------------|--------|-------|
| Parallel Search | `https://api.parallel.ai/v1/search` | n/a | `x-api-key` header (NOT Bearer) |
| Gemini 2.5 Pro (bible) | `gemini-3.1-pro-preview` | global | newest accessible Pro |
| Imagen 3 | `gemini-3-pro-image` | global | Imagen 3 deprecated |
| Veo 3.1 | `veo-3.1-fast-generate-001` | us-central1 | Lite lacks ref_images; Fast used |
| Chirp 3 | `gemini-2.5-flash-tts` | us-central1 | SDK surface; speech_config w/ voice |
| Lyria 2 | `lyria-002` | us-central1 | via Vertex :predict endpoint |

## Step results
| # | Step | Status | Time (s) | Cost ($) | Output | Size |
|---|------|--------|----------|----------|--------|------|
| 1 | parallel_search | ok | 2.04 | 0.001 | parallel_references.json | 5,064 |
| 2 | bible_synthesis | ok | 19.59 | 0.02 | bible_v1.json | 2,027 |
| 3 | character_image | ok | 54.33 | 0.02 | e2e_character_reference.png | 1,505,008 |
| 4 | veo_clip | ok | 31.74 | 0.05 | e2e_shot.mp4 | 3,865,783 |
| 5 | tts_voiceover | ok | 7.21 | 0.02 | e2e_voiceover.wav | 449,850 |
| 6 | lyria_score | ok | 30.35 | 0.03 | e2e_score.wav | 6,291,544 |

## Totals
- **APIs OK:** 6/6
- **Total cost:** $0.141 (budget $1.0) -> PASS
- **Total time:** 148.19s (budget 360s) -> PASS
- **Definition of done:** ALL PASS

## Output verification
| Step | Valid | Detail |
|------|-------|--------|
| parallel_search | yes | ok |
| bible_synthesis | yes | ok |
| character_image | yes | 89504e470d0a1a0a |
| veo_clip | yes | codec_name=h264
width=1280
height=720
duration=8.000000 |
| tts_voiceover | yes | codec_name=pcm_s16le
sample_rate=24000
channels=1
duration=9.370958 |
| lyria_score | yes | codec_name=pcm_s16le
sample_rate=48000
channels=2
duration=32.768229 |

## Artifacts
- Manifest: `backend/validation/outputs/day2-e2e-manifest.json`
- Parallel references: `backend/validation/outputs/parallel_references.json`
- Bible v1: `backend/validation/outputs/bible_v1.json`
- Character ref: `backend/validation/outputs/e2e_character_reference.png`
- Veo clip: `backend/validation/outputs/e2e_shot.mp4`
- Voiceover: `backend/validation/outputs/e2e_voiceover.wav`
- Score: `backend/validation/outputs/e2e_score.wav`
