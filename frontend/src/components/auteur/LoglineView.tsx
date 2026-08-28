/**
 * LoglineView — blueprint Section 30.2 row 2.
 * One input field; example loglines; "Build my film" button.
 */
"use client";

import { useState } from "react";
import { ArrowRight, Clapperboard, Loader2, Lightbulb } from "lucide-react";
import { useStudio } from "@/lib/store";
import { createProject } from "@/lib/api";

const EXAMPLE_LOGLINES = [
  "An 1892 Scottish lighthouse keeper discovers a message in a bottle that changes his life.",
  "A noir detective in 1920s Shanghai hunts a ghost from his past.",
  "A young astronaut alone on a dying Mars colony sends one final transmission home.",
  "Two rival chefs compete in a remote village cooking contest that becomes a matter of honor.",
];

export function LoglineView() {
  const setView = useStudio((s) => s.setView);
  const setProject = useStudio((s) => s.setProject);
  const setResearchProgress = useStudio((s) => s.setResearchProgress);
  const setError = useStudio((s) => s.setError);

  const [logline, setLogline] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit() {
    if (logline.trim().length < 8) return;
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

  return (
    <div className="mx-auto flex min-h-[calc(100vh-3.5rem)] max-w-2xl flex-col justify-center px-4 py-12">
      <div className="mb-8">
        <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-zinc-700 bg-zinc-900/60 px-3 py-1 text-xs text-zinc-400">
          <Clapperboard className="h-3.5 w-3.5 text-teal-400" />
          Step 1 — Logline
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-zinc-100 sm:text-3xl">
          What&apos;s your film about?
        </h2>
        <p className="mt-2 text-sm text-zinc-400">
          One sentence. The Director Agent will research it, build a Film Bible,
          and generate a 4-shot short film.
        </p>
      </div>

      <textarea
        value={logline}
        onChange={(e) => setLogline(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleSubmit();
        }}
        rows={3}
        placeholder="An 1892 Scottish lighthouse keeper discovers a message in a bottle..."
        className="w-full resize-none rounded-xl border border-zinc-700 bg-zinc-900/60 px-4 py-3 text-sm text-zinc-100 placeholder-zinc-600 outline-none transition focus:border-teal-500/60 focus:ring-2 focus:ring-teal-500/20"
        autoFocus
      />

      <div className="mt-3 flex items-center justify-between text-xs text-zinc-500">
        <span>{logline.length} chars · ⌘+Enter to submit</span>
        <button
          onClick={handleSubmit}
          disabled={logline.trim().length < 8 || loading}
          className="inline-flex items-center gap-1.5 rounded-lg bg-teal-500 px-4 py-2 text-xs font-semibold text-zinc-950 transition hover:bg-teal-400 disabled:cursor-not-allowed disabled:bg-zinc-800 disabled:text-zinc-600"
        >
          {loading ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <ArrowRight className="h-3.5 w-3.5" />
          )}
          Build my film
        </button>
      </div>

      <div className="mt-10">
        <div className="mb-3 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-zinc-500">
          <Lightbulb className="h-3.5 w-3.5 text-amber-400" />
          Example loglines
        </div>
        <div className="space-y-2">
          {EXAMPLE_LOGLINES.map((ex, i) => (
            <button
              key={i}
              onClick={() => setLogline(ex)}
              className="block w-full rounded-lg border border-zinc-800 bg-zinc-900/40 px-3 py-2.5 text-left text-xs text-zinc-400 transition hover:border-zinc-700 hover:bg-zinc-900 hover:text-zinc-200"
            >
              {ex}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
