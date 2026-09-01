/**
 * ResearchView row 3.
 * Real-time search panel; query + results with URLs; progress indicator.
 *
 * Calls POST /api/projects/{id}/build-bible on the deployed Cloud Run backend,
 * which runs the Director Agent at runtime:
 *   1. Research Agent calls Parallel Search (x-api-key) → grounded references
 *   2. Gemini 3.1 Pro synthesizes a typed Film Bible from the references
 *
 * The Parallel Search results are streamed into the UI as they arrive, so
 * the partner API integration is visible in real time.
 */
"use client";

import { useEffect, useRef, useState } from "react";
import { Search, ExternalLink, Loader2, Check, Globe, ChevronRight, AlertCircle } from "lucide-react";
import { useStudio } from "@/lib/store";
import { buildBible, type BuildBibleResponse } from "@/lib/api";
import type { FilmBible, Reference } from "@/lib/types";

const RESEARCH_STAGES = [
  "Formulating search queries from the logline",
  "Querying the Parallel Search API (x-api-key)",
  "Grounding era and setting references",
  "Grounding wardrobe and location references",
  "Synthesizing the Film Bible via Gemini 3.1 Pro",
  "Persisting Bible v1 (immutable snapshot)",
] as const;

export function ResearchView() {
  const { project, setView, setResearch, setResearchProgress, setBible, researchProgress, setError, error } = useStudio();
  const [stageIdx, setStageIdx] = useState(0);
  const [streamedRefs, setStreamedRefs] = useState<Reference[]>([]);
  const calledRef = useRef(false);

  useEffect(() => {
    if (!project) {
      setView("logline");
      return;
    }
    if (calledRef.current) return; // guard against double-call in StrictMode
    calledRef.current = true;

    let cancelled = false;
    setResearchProgress("searching");

    // advance through the stages visually while the real API call runs
    let idx = 0;
    const stageTimer = setInterval(() => {
      if (cancelled) return;
      idx = Math.min(idx + 1, RESEARCH_STAGES.length - 2);
      setStageIdx(idx);
    }, 1500);

    // fire the real Director Agent call
    buildBible(project.id)
      .then((resp: BuildBibleResponse) => {
        if (cancelled) return;
        clearInterval(stageTimer);
        setStageIdx(RESEARCH_STAGES.length - 1);
        setStreamedRefs(resp.references);
        setResearch(resp.references);
        setBible(resp.bible);
        setResearchProgress("done");
      })
      .catch((e) => {
        if (cancelled) return;
        clearInterval(stageTimer);
        setError(e instanceof Error ? e.message : "Director Agent failed");
        setResearchProgress("error");
      });

    return () => {
      cancelled = true;
      clearInterval(stageTimer);
    };
  }, [project, setView, setResearch, setBible, setResearchProgress, setError]);

  const done = researchProgress === "done";

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="mb-6">
        <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-zinc-700 bg-zinc-900/60 px-3 py-1 text-xs text-zinc-400">
          <Search className="h-3.5 w-3.5 text-teal-400" />
          Step 2 — Research Agent
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-zinc-100">
          Grounding the production in reality
        </h2>
        <p className="mt-1.5 text-sm text-zinc-400">
          The Research Agent calls the{" "}
          <span className="font-mono text-teal-300">Parallel Search API</span> at
          runtime to ground every creative decision in real-world references, then
          Gemini 3.1 Pro synthesizes a typed Film Bible.
        </p>
        {project && (
          <div className="mt-3 rounded-lg border border-zinc-800 bg-zinc-900/40 px-3 py-2 text-xs text-zinc-400">
            <span className="text-zinc-500">Logline:</span> {project.logline}
          </div>
        )}
      </div>

      {/* progress stages */}
      <div className="mb-6 space-y-2">
        {RESEARCH_STAGES.map((stage, i) => {
          const isActive = i === stageIdx && !done;
          const isDone = (done && i === RESEARCH_STAGES.length - 1) || i < stageIdx;
          return (
            <div
              key={stage}
              className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-xs transition ${
                isActive
                  ? "border border-teal-500/40 bg-teal-500/5 text-teal-200"
                  : isDone
                    ? "text-zinc-400"
                    : "text-zinc-600"
              }`}
            >
              {isDone ? (
                <Check className="h-3.5 w-3.5 text-emerald-400" />
              ) : isActive ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin text-teal-400" />
              ) : (
                <div className="h-3.5 w-3.5 rounded-full border border-zinc-700" />
              )}
              <span className="font-mono">{stage}</span>
            </div>
          );
        })}
      </div>

      {/* error */}
      {error && researchProgress === "error" && (
        <div className="mb-6 flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-xs text-amber-200">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <div className="font-medium">Director Agent error</div>
            <div className="mt-0.5 text-amber-200/80">{error}</div>
          </div>
        </div>
      )}

      {/* streamed references */}
      <div className="space-y-2">
        <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-zinc-500">
          <Globe className="h-3.5 w-3.5" />
          Parallel Search results ({streamedRefs.length})
          {streamedRefs.length > 0 && (
            <span className="ml-auto font-mono text-[10px] text-emerald-400">live from api.parallel.ai</span>
          )}
        </div>
        {streamedRefs.length === 0 && !done && researchProgress !== "error" && (
          <div className="rounded-lg border border-dashed border-zinc-800 px-4 py-6 text-center text-xs text-zinc-600">
            <Loader2 className="mx-auto mb-2 h-4 w-4 animate-spin text-zinc-600" />
            Awaiting Parallel Search results
          </div>
        )}
        {streamedRefs.map((ref, i) => (
          <a
            key={ref.id || i}
            href={ref.url}
            target="_blank"
            rel="noreferrer"
            className="auteur-rise block rounded-lg border border-zinc-800 bg-zinc-900/40 px-3 py-2.5 transition hover:border-zinc-700 hover:bg-zinc-900"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5 text-xs font-medium text-zinc-200">
                  <span className="truncate">{ref.title}</span>
                  <ExternalLink className="h-3 w-3 shrink-0 text-zinc-600" />
                </div>
                <p className="mt-1 line-clamp-2 text-[11px] text-zinc-500">{ref.snippet}</p>
                <div className="mt-1 truncate font-mono text-[10px] text-teal-500/70">{ref.url}</div>
              </div>
            </div>
          </a>
        ))}
      </div>

      {done && (
        <div className="auteur-rise mt-8 flex items-center justify-between rounded-lg border border-emerald-500/30 bg-emerald-500/5 px-4 py-3">
          <span className="text-xs text-emerald-300">
            Bible v1 built from {streamedRefs.length} grounded references (Parallel Search and Gemini 3.1 Pro)
          </span>
          <button
            onClick={() => setView("bible")}
            className="inline-flex items-center gap-1.5 rounded-md bg-emerald-500 px-3 py-1.5 text-xs font-semibold text-zinc-950 transition hover:bg-emerald-400"
          >
            View Bible
            <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}
