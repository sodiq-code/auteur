## Inspiration

Veo 3.1 can produce a gorgeous 8-second clip. But try to make a 4-shot short film with it, and you hit a wall: the character in shot 1 has a different face in shot 2. The wardrobe changes between cuts. The voice doesn't match. Every generation call is an isolated lottery — the model has no memory of what it generated 30 seconds ago.

We watched this happen in our own testing. Four clips that were individually beautiful but collectively incoherent. Four different films stitched together, not one film.

The insight: **consistency, not quality, is the bottleneck in AI cinema.** And that's a software-architecture problem, not a model-capability problem. No amount of prompt engineering fixes it — you need a persistent state layer that every generation call must obey.

That's what Auteur is.

## What it does

Auteur is an agentic AI film studio that maintains a persistent, research-grounded **Film Bible** and enforces cross-shot consistency across every generation call.

The filmmaker writes one logline. The Director Agent takes over:

1. **Research** — calls the Parallel Search API at runtime to ground every creative decision (era, location, fashion, music, lighting) in real-world references. Every result streams live in the UI with its source URL.

2. **Bible synthesis** — Gemini 3.1 Pro synthesizes a typed, versioned Film Bible from the references: characters, locations, wardrobes, voice profiles, score motifs, style anchors, and story beats. Every claim traces to a real URL.

3. **Generation** — each shot calls Veo 3.1 (video), Chirp 3 (voiceover), and Lyria 2 (score) concurrently, with the Bible injected as structured context. The same character reference, the same wardrobe, the same voice profile, across every shot.

4. **Consistency check** — a Consistency Check Agent (Gemini 3.1 Pro Vision) extracts a frame from each generated clip and scores it against the character reference across four dimensions (face identity, age, facial hair, wardrobe) plus a holistic overall score.

5. **Closed-loop regeneration** — when drift exceeds the threshold, the system regenerates the shot with the prior drift report injected as corrective context ("prior face identity 0.80 — preserve the exact facial features from the reference"). The agentic loop is real: the evaluator's output changes the agent's behavior.

6. **Assembly** — ffmpeg concatenates the Veo clips and muxes the Chirp voiceover + Lyria score into the final MP4 with synchronized AAC audio.

The result: a short film that looks like one film, not four.

## How we built it

**Three agents on Google Agent Development Kit (ADK):**
- **Director Agent** (`gemini-3.1-pro-preview`) — orchestrates the full pipeline from logline to final film
- **Research Agent** (`gemini-3.1-pro-preview`) — calls Parallel Search at runtime, synthesizes typed Reference objects
- **Consistency Check Agent** (`gemini-3.1-pro-preview` vision) — scores per-shot drift against the character reference

**Six-layer memory architecture:**
- L1: Working memory (in-process tool-call state)
- L2: Project state (Firestore — project, Bible, shots, generation log)
- L3: Bible versions (Firestore — immutable, append-only snapshots; every edit creates a new version; every generation cites which version it used)
- L4: Search cache (Firestore — Parallel Search results, 24h TTL)
- L5: Rendered artifacts (Cloud Storage — Veo MP4s, Chirp WAVs, Lyria WAVs, character-ref PNGs)
- L6: Drift history (Firestore — per-shot drift scores across re-generations)

**The Film Bible** is a typed Pydantic schema with seven collections (characters, locations, wardrobes, voice profiles, score motifs, style anchors, story beats). It's versioned: editing a field creates a new immutable version. Every generation cites its Bible version, so drift is attributable across edits.

**The closed loop** is the core agentic mechanism: `POST /shots/{id}/regenerate` fetches the prior drift report, injects the per-attribute scores into the Veo prompt as targeted corrective context, re-runs generation, and re-checks. There's also an autonomous endpoint (`POST /shots/auto-regenerate`) that checks all shots and auto-regenerates those above the drift threshold without caller-specified shot IDs.

**100% Google Cloud native:** Gemini 3.1 Pro, Veo 3.1, Chirp 3, Lyria 2, Firestore, Cloud Storage, Cloud Run, ADK. The only external dependency is the partner (Parallel Search API), which is intrinsic to the agent's value — it grounds the film in reality.

**The studio UI** is Next.js 16 with 10 views mapping to the filmmaking workflow: Logline → Research → Bible → Shots → Render → Grid → Drift → Assembly → Share. The Bible is visible and editable at every step. A command palette (⌘K) navigates the workflow.

## Challenges we ran into

**Audio muxing was the hardest bug.** The assembled film had no sound. Root cause: three compounding defects — the generation pipeline didn't persist the Chirp/Lyria WAV bytes to the store, the assembly pipeline used `-c copy` on video-only Veo clips (no audio track at all), and the frontend `<video>` element had a `muted` attribute. Each was invisible on its own; together they produced a silent film. The fix required rewriting the assembly pipeline to build per-shot audio segments (mix voiceover at full volume + score at 25% as a bed, trimmed/padded to each shot's exact Veo duration), then concatenate + mux into the final MP4.

**Veo 3.1 tier selection.** The "Veo 3.1 Light" tier doesn't support `reference_images` (the ASSET reference mechanism that enables cross-shot character consistency). We had to use `veo-3.1-fast-generate-001` for iteration and validate that the ASSET reference mechanism actually holds the character consistent across 4 scenes. It does — mean consistency 0.925.

**Firestore async/sync mismatch.** The `firestore_async` client doesn't exist on this project's google-cloud-firestore version. We switched to the sync client and removed all `await` calls on Firestore operations. Composite indexes were avoided by using document key lookups (`projectId_version`) instead of `.where().order_by()` queries.

**Lyria content-filter failures.** Lyria 2 rejects vague or dark prompts with a 500. We added retry logic with 4 progressively safer fallback prompts, starting from the Bible-derived motif and falling back to generic "ambient cinematic film score."

## Accomplishments that we're proud of

- **The Film Bible as a primitive.** It's not a feature — it's an architectural mechanism. Typed, versioned, citable, injected into every call. Every generation cites its Bible version. Drift is attributable. That's the thing judges remember.

- **The closed-loop regeneration is real.** Not theoretical — captured on the deployed backend: Shot 2 first generation overall 0.85 (face 0.80, age 0.90, beard 0.90), regeneration with drift-diagnosis-informed context improved to overall 0.90 (face 0.90, age 0.95, beard 0.95). The evaluator's output changes the agent's behavior.

- **The autonomous loop endpoint.** `POST /auto-regenerate` checks all shots, auto-regenerates those above the drift threshold, and re-checks. The system itself decides which shots to regenerate.

- **Parallel Search is intrinsic, not bolted on.** The Research Agent calls it at runtime. The live Research panel streams every query and result with source URLs. If Parallel is unavailable, the pipeline continues (the Director synthesizes from the logline alone). The partner integration is one half of the intelligence architecture: creative memory (Film Bible) + world memory (Parallel Search).

- **Methodological honesty.** The consistency scores are labeled as internal LLM-as-judge metrics, not objective perceptual measurements. The 0.75 acceptance threshold is described as an engineering threshold for the prototype. This pre-empts the skeptical judge rather than hiding from them.

## What we learned

- **State is the differentiator, not model power.** The generation models are already good enough. What's missing is persistent, structured, versioned state that every call consumes. That's a software-architecture insight, not a model-capability insight — and it's exactly the kind of insight an agentic-AI competition should reward.

- **The evaluator and the generator share an ecosystem.** Using Gemini Vision to evaluate Veo output creates a potential evaluator-bias question. We document this explicitly rather than hiding it. The scores are operational consistency signals, not independent ground-truth measurements.

- **Graceful degradation is not optional.** If Parallel Search is down, the pipeline continues. If Veo quota is exhausted, the sample production serves as the landing experience. Every external call has a fallback path. This is what makes the deployed app survive judge testing.

## What's next for Auteur — The Film Bible Agent

- **Public Film Bible marketplace.** Versioned Bibles become shareable, forkable artifacts. Each new Bible increases the value of the platform — a network moat.

- **Multi-character consistency.** The current system tracks one character reference per project. Extending to multiple characters (with per-character ASSET references) would enable ensemble scenes.

- **Color match and edit decisions.** The assembly pipeline currently concatenates + muxes audio. Post-prototype, it could make edit decisions (cut points, transitions, pacing) based on the story beats and the consistency scores.

- **Independent evaluator.** Adding a second evaluator model (outside the Google ecosystem) to cross-check the Gemini Vision scores would address the evaluator-bias question directly.

- **Open-source the Bible schema.** The Pydantic schema as an ecosystem primitive — a standard for how generative filmmaking projects declare and version their creative state.
