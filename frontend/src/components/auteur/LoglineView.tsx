/**
 * LoglineView — blueprint Section 30.2 row 2.
 * One input field; example loglines; "Build my film" button.
 *
 * Polish:
 *  - Stronger heading with a gradient accent on the key word
 *  - Char-limit progress bar with color feedback (green → amber → red)
 *  - Hover affordances on example cards (lift + arrow icon)
 *  - Keyboard shortcut chip (⌘+Enter) styled as a <kbd> element
 *  - Focus glow on the textarea
 *  - Better vertical rhythm / breathing room
 */
"use client";

import { useState } from "react";
import { ArrowRight, Clapperboard, Loader2, Lightbulb, ChevronRight, Sparkles } from "lucide-react";
import { useStudio } from "@/lib/store";
import { createProject } from "@/lib/api";

const EXAMPLE_LOGLINES = [
  {
    text: "An 1892 Scottish lighthouse keeper discovers a message in a bottle that changes his life.",
    tag: "Period drama",
  },
  {
    text: "A noir detective in 1920s Shanghai hunts a ghost from his past.",
    tag: "Noir mystery",
  },
  {
    text: "A young astronaut alone on a dying Mars colony sends one final transmission home.",
    tag: "Sci-fi",
  },
  {
    text: "Two rival chefs compete in a remote village cooking contest that becomes a matter of honor.",
    tag: "Drama",
  },
];

const MIN_CHARS = 20;
const SOFT_LIMIT = 200;
const HARD_LIMIT = 280;

function getCharState(len: number): { pct: number; color: string; label: string } {
  if (len === 0) return { pct: 0, color: "rgb(63 63 70)", label: "empty" };
  if (len < MIN_CHARS) return { pct: (len / HARD_LIMIT) * 100, color: "rgb(82 82 91)", label: "keep going" };
  if (len <= SOFT_LIMIT) return { pct: (len / HARD_LIMIT) * 100, color: "rgb(16 185 129)", label: "good" };
  if (len <= HARD_LIMIT) return { pct: (len / HARD_LIMIT) * 100, color: "rgb(245 158 11)", label: "getting long" };
  return { pct: 100, color: "rgb(239 68 68)", label: "too long" };
}

export function LoglineView() {
  const setView = useStudio((s) => s.setView);
  const setProject = useStudio((s) => s.setProject);
  const setResearchProgress = useStudio((s) => s.setResearchProgress);
  const setError = useStudio((s) => s.setError);

  const [logline, setLogline] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit() {
    if (logline.trim().length < MIN_CHARS || logline.length > HARD_LIMIT) return;
    setLoading(true);
    setError(null);
    try {
      const project = await createProject(logline.trim());
      setProject(project);
      setResearchProgress("searching");
      setView("research");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create project");
    } finally {
      setLoading(false);
    }
  }

  const len = logline.length;
  const charState = getCharState(len);
  const canSubmit = len >= MIN_CHARS && len <= HARD_LIMIT && !loading;

  return (
    <div className="mx-auto flex min-h-[calc(100vh-3.5rem)] max-w-3xl flex-col justify-center px-4 py-12">
      <div className="mb-8">
        <div className="auteur-rise mb-3 inline-flex items-center gap-2 rounded-full border border-zinc-700 bg-zinc-900/60 px-3 py-1 text-xs text-zinc-400 backdrop-blur">
          <Clapperboard className="h-3.5 w-3.5 text-teal-400" />
          Step 1 — Logline
        </div>
        <h2 className="auteur-rise text-3xl font-bold tracking-tight text-zinc-100 sm:text-4xl" style={{ animationDelay: "0.05s" }}>
          What&apos;s your film{" "}
          <span className="bg-gradient-to-r from-teal-400 to-amber-300 bg-clip-text text-transparent">
            about?
          </span>
        </h2>
        <p className="auteur-rise mt-3 text-sm leading-relaxed text-zinc-400 sm:text-base" style={{ animationDelay: "0.1s" }}>
          One sentence. The Director Agent will research it, build a Film Bible,
          and generate a 4-shot short film with synchronized voiceover and score.
        </p>
      </div>

      <div className="auteur-rise" style={{ animationDelay: "0.15s" }}>
        <textarea
          value={logline}
          onChange={(e) => setLogline(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
              e.preventDefault();
              handleSubmit();
            }
          }}
          rows={4}
          placeholder="An 1892 Scottish lighthouse keeper discovers a message in a bottle..."
          className="auteur-textarea-glow w-full resize-none rounded-xl border border-zinc-700 bg-zinc-900/60 px-4 py-4 text-base text-zinc-100 placeholder-zinc-600 outline-none transition focus:border-teal-500/60 focus:ring-2 focus:ring-teal-500/20"
          autoFocus
          maxLength={HARD_LIMIT + 40}
        />

        {/* char-limit progress bar */}
        <div className="mt-3">
          <div className="h-1 w-full overflow-hidden rounded-full bg-zinc-800">
            <div
              className="auteur-char-bar h-full rounded-full"
              style={{ width: `${charState.pct}%`, backgroundColor: charState.color }}
            />
          </div>
          <div className="mt-2 flex items-center justify-between text-xs">
            <span className="flex items-center gap-2 text-zinc-500">
              <span className="font-mono text-zinc-400">{len}</span>
              <span>/</span>
              <span className="font-mono">{HARD_LIMIT}</span>
              <span className="text-zinc-700">·</span>
              <span
                className="font-medium"
                style={{ color: len === 0 ? "rgb(113 113 122)" : charState.color }}
              >
                {charState.label}
              </span>
            </span>
            <span className="flex items-center gap-1.5 text-zinc-600">
              <span className="auteur-kbd">⌘</span>
              <span className="auteur-kbd">↵</span>
              <span className="text-zinc-500">to submit</span>
            </span>
          </div>
        </div>

        {/* submit button */}
        <div className="mt-5 flex justify-end">
          <button
            onClick={handleSubmit}
            disabled={!canSubmit}
            className="group inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-teal-500 to-emerald-500 px-6 py-2.5 text-sm font-semibold text-zinc-950 shadow-lg shadow-teal-500/25 transition hover:shadow-teal-500/40 hover:brightness-110 disabled:cursor-not-allowed disabled:from-zinc-800 disabled:to-zinc-800 disabled:text-zinc-600 disabled:shadow-none"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            {loading ? "Building…" : "Build my film"}
            {!loading && (
              <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
            )}
          </button>
        </div>
      </div>

      {/* example loglines */}
      <div className="auteur-rise mt-12" style={{ animationDelay: "0.25s" }}>
        <div className="mb-3 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-zinc-500">
          <Lightbulb className="h-3.5 w-3.5 text-amber-400" />
          Example loglines
          <span className="text-zinc-700">— click to use</span>
        </div>
        <div className="space-y-2">
          {EXAMPLE_LOGLINES.map((ex, i) => (
            <button
              key={i}
              onClick={() => setLogline(ex.text)}
              className="auteur-example-card group flex w-full items-start gap-3 rounded-lg border border-zinc-800 bg-zinc-900/40 px-3 py-3 text-left"
            >
              <ChevronRight className="auteur-example-arrow mt-0.5 h-3.5 w-3.5 shrink-0 text-teal-400" />
              <div className="flex-1 min-w-0">
                <div className="text-xs text-zinc-300 leading-relaxed">{ex.text}</div>
                <div className="mt-1.5 inline-flex items-center rounded-full bg-zinc-800/80 px-2 py-0.5 text-[10px] font-medium text-zinc-500">
                  {ex.tag}
                </div>
              </div>
              <span className="font-mono text-[10px] text-zinc-700">{ex.text.length}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
