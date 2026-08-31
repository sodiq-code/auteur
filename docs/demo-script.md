# Auteur — Demo Script (3-minute, Submission Version)

> Demo script for the 3-minute submission video.
> (Demo Architecture) + Section 30.5 (Side-by-side signature moment) +
> Table 34 (Chirp 3 voiceover). The 5-beat structure follows the Oleksandr
> pattern : Problem → Solution → App demo → Technical
> implementation → Closing.

## Format 

- **Length:** 3 minutes (≤ 3:00 — hard requirement, 
  Section 33.2 Row P915).
- **Aspect / resolution:** 16:9, 1080p, MP4.
- **Voiceover:** Chirp 3-generated narration using the script below
  (Section 39.3, "Voiceover: Chirp 3-generated narration with the
  5-beat script").
- **Visuals:** B-roll of the actual deployed UI + text overlays for key
  claims . No stock footage.
- **Subtitles:** English, verified .
- **Default landing:** the deployed app loads the sample
  demo automatically; the video includes one live Veo Light generation
  triggered by the "Watch it live" button (Section 39.3, "Live
  CTA").

## 5-Beat structure 

| Beat | Time | Beat name | Goal |
|---|---|---|---|
| 1 | 0:00 – 0:20 | Problem | Make the pain instantly felt. |
| 2 | 0:20 – 0:50 | Solution | Introduce Auteur and the Film Bible primitive. |
| 3 | 0:50 – 1:50 | App demo | Logline → research → bible → shots → assembly, end-to-end. |
| 4 | 1:50 – 2:30 | Technical implementation | Three agents, ADK, partner integration, citation chain. |
| 5 | 2:30 – 3:00 | Closing | The final film + tagline + CTA. |

---

## Beat 1 — Problem (0:00 – 0:20)

**[0:00 – 0:05] HOOK.** Voiceover (Chirp 3, calm, low register):

> "AI cinema's problem is not video quality. It's
> consistency."

Visual: black frame; the word **CONSISTENCY** fades in amber (#E89B3C),
then dissolves.

**[0:05 – 0:20] PROBLEM.** Voiceover:

> "Veo 3.1 and Sora 2 produce gorgeous individual clips. But every shot is
> an isolated lottery. Characters drift. Wardrobes mutate. Voices lose
> continuity. The result is incoherent. Same prompt, same character, 4
> shots — look at the drift. This is why every AI short film looks like
> four different films."

Visual: **THE SIDE-BY-SIDE SIGNATURE MOMENT** .
Two columns. LEFT column (no Auteur): Shot 1 character A, Shot 2 character
B, Shot 3 character C, Shot 4 character D — visibly different faces.
Caption under the left column: `drift: chaotic · 4 different films`. RIGHT
column (with Auteur): Shot 1 Ewan, Shot 2 Ewan, Shot 3 Ewan, Shot 4 Ewan —
same beard, same coat, same face. Caption under the right column:
`drift: 0.10 · 1 film, 4 shots`. Footer line, centered: *"Same prompt. Same
character. 4 shots. 4 scenes. The only difference: Auteur remembers."*

---

## Beat 2 — Solution (0:20 – 0:50)

**[0:20 – 0:35] SOLUTION.** Voiceover:

> "Meet Auteur — AI cinema's memory. Grounded in reality. Consistent across
> every shot. Auteur is an agentic AI film studio that maintains a
> persistent, research-grounded Film Bible. It uses Parallel Search to
> ground creative decisions in real-world references. Then it injects the
> bible into every Veo 3.1, Chirp 3, Lyria 2, and Imagen 3 call."

Visual: full-screen UI of the Auteur workspace — Script Pane, Bible Pane,
Shot Grid, Render Queue, Research Panel . The Bible
Pane expands: Characters → Locations → Wardrobe → Voice → Score → Style →
Beats. Each tab flips open for one second.

**[0:35 – 0:50] THE PRIMITIVE.** Voiceover:

> "The result: a film that looks like one film, not four."

Visual: zoom into one Bible entry — `Ewan MacLeod (52, beard, oilskin coat,
Skerryvore Lighthouse, 1892)`. Reference image thumbnail. Three Parallel
Search URLs hover next to the entry: `↳ wikipedia.org/wiki/Skerryvore`,
`↳ historic-scotland.org/...`, `↳ archive.org/1892-lightkeeper`. Text
overlay: *"Every claim traces to a real URL."*

---

## Beat 3 — App demo (0:50 – 1:50)

The heart of the demo — 60 seconds of live pipeline, recorded from the
deployed app .

**[0:50 – 0:55] Logline input.** Voiceover:

> "Let me show you. Logline: 'A lonely lighthouse keeper discovers a
> message in a bottle from 1892.'"

Visual: Script Pane with the logline typed, "Build my film" button clicked.

**[0:55 – 1:05] Research Agent — visible Parallel Search.** Voiceover:

> "The Research Agent activates. It searches via Parallel: 1892 lighthouse
> architecture, Scottish lighthouse keeper clothing 1892, 1892 handwriting
> styles, Victorian sea shanties. Every search result is shown with its
> source URL. The agent is grounding the film in real history."

Visual: Research Panel . Each
query appears as it's sent. Results stream in with their URLs visible —
this is the **#1 anti-anti-pattern mitigation** (Section 26.3,
P670): a judge watching the video sees the partner API being called live.

**[1:05 – 1:15] Bible build.** Voiceover:

> "The Director Agent builds the Film Bible. Ewan MacLeod, 52, weathered,
> salt-and-pepper beard, oilskin coat, fisherman's cap. Skerryvore
> Lighthouse, 1892. Voice profile: aged Scottish male. Score motif:
> minor-key sea shanty in D minor. Style anchor: muted blues and grays,
> candlelight warmth."

Visual: Bible Pane populates entry by entry. Each new entry fades in.
Bible version badge at the top of the pane flips `v1`.

**[1:15 – 1:20] Shot list.** Voiceover:

> "Four shots: lamp room at dusk, bottle on the rocks, reading by
> candlelight, looking out to sea."

Visual: Shot List view — 4 rows, each with bible refs and a "Generate"
button.

**[1:20 – 1:45] Generation — visible render queue.** Voiceover:

> "Each shot generates in turn. Imagen storyboard. Veo 3.1 video. Chirp 3
> voice. Lyria 2 score. Consistency Check: drift 0.12. Accept. Shot 3
> drift 0.34. Re-generate. New drift 0.08. Accept."

Visual: Render Queue. Each shot lights up with the active modality
(`Veo 3.1 Light | Shot 3 regen | 45s elapsed | est. 30s left`). The
Consistency Dashboard populates per-shot drift scores. Shot 3 flashes
amber (`drift 0.34`), then the Re-generate button pulses, then a fresh
generation replaces it and the drift drops to `0.08`. This is the
**learning loop made visible** .

**[1:45 – 1:50] Assembly.** Voiceover:

> "The four shots, voice, and score are assembled into a 30-second short
> film. Watch."

Visual: ffmpeg progress bar; final assembled MP4 thumbnail; "Watch"
button.

---

## Beat 4 — Technical implementation (1:50 – 2:30)

**[1:50 – 2:10] Three agents on ADK.** Voiceover:

> "How does this work? Three agents on Google Agent Development Kit.
> Director Agent orchestrates the pipeline — chooses which tool to call
> next based on current state. Research Agent grounds creative decisions
> in real-world references via Parallel Search API. Every bible entry has
> a source URL. Every fact is verifiable. Consistency Check Agent uses
> Gemini 2.5 Pro Vision to compare each generated shot against the bible
> references. Produces a drift score. Flags drift above threshold.
> Suggests re-generation."

Visual: three-card layout — Director (orchestrator), Research (Parallel),
Consistency (Gemini Vision). Arrows show the agentic loop
(Observe → Remember → Reason → Plan → Act → Measure → Learn → Update).

**[2:10 – 2:30] The Bible is typed, versioned, citable.** Voiceover:

> "The Film Bible is a typed, versioned, citable schema in Firestore. Every
> generation cites which bible version it used. Drift is attributable. The
> user can roll back to any version. All on Google Cloud. Gemini 2.5 Pro.
> Veo 3.1. Chirp 3. Lyria 2. Imagen. ADK. Firestore. Cloud Run. Parallel
> Search. The partner integration is intrinsic — Parallel Search is the
> grounding layer. Every creative decision can be traced to a real search
> result."

Visual: Pydantic models slide past (Section 23.2 — `CharacterSpec`,
`LocationSpec`, `WardrobeSpec`, `VoiceProfileSpec`, `ScoreMotifSpec`,
`StyleAnchorSpec`, `StoryBeat`, `FilmBible`). Provenance chain diagram:
Parallel Search result → Bible v{n} → Generation → Drift report
.

> Day-1 validation note: specifies "Imagen 3"; on the live GCP
> project, Imagen 3 is deprecated and `gemini-3-pro-image` is the
> supported successor used to generate the persistent character reference
> image. See `docs/validation-report.md` (mean cross-shot
> consistency 0.94, verdict GO).

---

## Beat 5 — Closing (2:30 – 3:00)

**[2:30 – 2:50] The final film.** Voiceover (under the film audio):

> "Same character. Same world. Same voice. Same score. Same style. Across
> every shot. This is the project that made an AI film look like the same
> film."

Visual: the assembled 30-second short film plays in full, side-by-side
with the original 4-shot drift comparison so the contrast remains
visible.

**[2:50 – 3:00] Tagline + CTA.** Voiceover:

> "Auteur — AI cinema's memory. Grounded in reality. Consistent across
> every shot. Try it live at <URL>. Fork it on GitHub at <REPO>. Built
> for the Agentic Cinema hackathon. Built on Google Cloud. Built on
> Parallel Search. Built to make AI cinema coherent. Thank you."

Visual: Auteur logo (amber on navy #0B1F3A), URL + repo URL text overlays,
fade to black at 3:00.

---

## Production checklist 

- [ ] Record screen captures of the deployed app: canonical demo + one
  live Veo Light generation (the "Watch it live" CTA).
- [ ] Generate the Chirp 3 voiceover from this script (one paragraph at a
  time, concatenated).
- [ ] Edit in CapCut or iMovie; add text overlays for every key claim.
- [ ] Upload to YouTube as unlisted; verify English subtitles; verify
  ≤ 3:00; re-watch with audio muted  —
  every key claim must be visible as a text overlay.

## Companion versions 

For social and judge-attention use, produce shorter cuts from this script:
30-second (Twitter/X hook, Section 40.1), 60-second (LinkedIn / trailer,
Section 40.2), 90-second (judge first-impression, Section 40.3), 5-minute
(judge deep-dive, Section 40.5 — adds Schema deep-dive, a second logline
to prove generalization, the learning-loop discussion, the roadmap, and
the open-source strategy).

## Cross-references

- Architecture: [`ARCHITECTURE.md`](../ARCHITECTURE.md).
- REST API exercised in the demo: [`docs/api-contract.md`](api-contract.md).
- Bible schema shown in Beat 4: [`docs/bible-schema.md`](bible-schema.md).
- Parallel Search visibility in Beat 3: [`docs/partner-integration.md`](partner-integration.md).
- Day-1 validation evidence: [`docs/validation-report.md`](validation-report.md).
