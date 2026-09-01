/**
 * LandingView row 1 + Day 11 (canonical demo) + Day 12 (UX polish).
 *
 * Loads the pre-rendered canonical demo by default (the safety net — visitors
 * see the demo instantly). The SideBySide component is the signature moment.
 * The "Make your first film" CTA triggers the real pipeline.
 */
"use client";

import { useEffect, useState } from "react";
import { Film, Play, Sparkles, ArrowRight, Zap, Check, Loader2, Edit3, Search, BookOpen, Clapperboard } from "lucide-react";
import { useStudio } from "@/lib/store";
import { getDemo, type DemoData } from "@/lib/api";
import { SideBySide } from "@/components/auteur/SideBySide";
import { LoadingSkeleton } from "@/components/auteur/StateComponents";

export function LandingView() {
  const setView = useStudio((s) => s.setView);
  const [demo, setDemo] = useState<DemoData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDemo()
      .then(setDemo)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const demoShots = demo?.shots?.map((s) => ({
    id: s.order,
    label: s.label,
    scene: s.scene,
    frame: s.frame,
    score: s.score,
  })) || [];

  return (
    <div className="relative flex min-h-[calc(100vh-3.5rem)] flex-col items-center justify-center overflow-hidden px-4 py-12">
      {/* ambient glow */}
      <div className="pointer-events-none absolute -top-32 left-1/2 h-96 w-96 -translate-x-1/2 rounded-full bg-teal-500/15 blur-3xl auteur-hero-blob" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-72 w-72 rounded-full bg-amber-500/10 blur-3xl" />

      <div className="relative z-10 mx-auto max-w-4xl text-center">
        <div className="auteur-rise mb-6 inline-flex items-center gap-2 rounded-full border border-zinc-700 bg-zinc-900/60 px-3 py-1 text-xs text-zinc-400 backdrop-blur">
          <Sparkles className="h-3.5 w-3.5 text-amber-400" />
          The Film Bible Agent · Cross-shot consistency for generative cinema
        </div>

        <h1 className="auteur-rise text-4xl font-bold leading-tight tracking-tight text-zinc-100 sm:text-6xl" style={{ animationDelay: "0.1s" }}>
          AI cinema&apos;s memory.
          <br />
          <span className="auteur-shimmer bg-gradient-to-r from-teal-400 via-emerald-300 to-amber-300 bg-clip-text text-transparent">
            Consistent across every shot.
          </span>
        </h1>

        <p className="auteur-rise mx-auto mt-6 max-w-xl text-sm leading-relaxed text-zinc-400 sm:text-base" style={{ animationDelay: "0.2s" }}>
          An agentic AI film studio that maintains a persistent, research-grounded
          Film Bible and enforces cross-shot consistency across every Veo 3.1,
          Chirp 3, Lyria 2, and Imagen 3 generation call.
        </p>

        {/* SideBySide signature moment */}
        <div className="auteur-rise mt-10" style={{ animationDelay: "0.3s" }}>
          {loading ? (
            <LoadingSkeleton rows={1} className="mx-auto max-w-2xl" />
          ) : (
            <SideBySide
              shots={demoShots}
              meanOverall={demo?.consistency?.mean_overall}
              verdict={demo?.consistency?.verdict}
            />
          )}
        </div>

        {/* demo stats */}
        {demo && (
          <div className="auteur-rise mt-6 flex items-center justify-center gap-6 text-xs" style={{ animationDelay: "0.4s" }}>
            <div className="flex items-center gap-1.5 text-emerald-400">
              <Check className="h-3.5 w-3.5" />
              <span className="font-mono">{demo.consistency.mean_overall}</span>
              <span className="text-zinc-500">consistency</span>
            </div>
            <div className="flex items-center gap-1.5 text-zinc-400">
              <Film className="h-3.5 w-3.5 text-teal-400" />
              <span className="font-mono">{demo.shots.length}</span>
              <span className="text-zinc-500">shots</span>
            </div>
            <div className="flex items-center gap-1.5 text-amber-400">
              <Zap className="h-3.5 w-3.5" />
              <span className="text-zinc-500">sample production</span>
            </div>
          </div>
        )}

        <button
          onClick={() => setView("logline")}
          className="auteur-rise group mt-8 inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-teal-500 to-emerald-500 px-6 py-3 text-sm font-semibold text-zinc-950 shadow-lg shadow-teal-500/25 transition hover:shadow-teal-500/40 hover:brightness-110"
          style={{ animationDelay: "0.5s" }}
        >
          <Film className="h-4 w-4" />
          Start a new production
          <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
        </button>

        <div className="auteur-rise mt-8 flex items-center justify-center gap-6 text-[11px] text-zinc-600" style={{ animationDelay: "0.6s" }}>
          <span className="flex items-center gap-1.5">
            <Play className="h-3 w-3" /> 4-shot short film
          </span>
          <span>~5 min end-to-end</span>
          <span>Google Cloud native</span>
        </div>

        {/* how it works — 4 steps */}
        <div className="auteur-rise mt-14 grid grid-cols-2 gap-3 sm:grid-cols-4" style={{ animationDelay: "0.7s" }}>
          {[
            { n: "01", t: "Logline", d: "One sentence", icon: Edit3 },
            { n: "02", t: "Research", d: "Parallel Search", icon: Search },
            { n: "03", t: "Bible", d: "Gemini 3.1 Pro", icon: BookOpen },
            { n: "04", t: "Render", d: "Veo, Chirp, Lyria", icon: Clapperboard },
          ].map((s) => (
            <div
              key={s.n}
              className="group rounded-lg border border-zinc-800/80 bg-zinc-900/30 p-3 text-left transition hover:border-teal-500/30 hover:bg-zinc-900/60"
            >
              <div className="mb-2 flex items-center justify-between">
                <s.icon className="h-4 w-4 text-teal-400" />
                <span className="font-mono text-[10px] text-zinc-600">{s.n}</span>
              </div>
              <div className="text-xs font-semibold text-zinc-200">{s.t}</div>
              <div className="mt-0.5 text-[10px] text-zinc-500">{s.d}</div>
            </div>
          ))}
        </div>

        {/* partners ribbon */}
        <div className="auteur-rise mt-10" style={{ animationDelay: "0.8s" }}>
          <div className="auteur-ribbon-divider mb-4" />
          <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-[11px] text-zinc-600">
            <span className="font-medium uppercase tracking-wide text-zinc-500">Powered by</span>
            <span className="font-mono text-zinc-400">Veo 3.1</span>
            <span className="text-zinc-800">·</span>
            <span className="font-mono text-zinc-400">Chirp 3</span>
            <span className="text-zinc-800">·</span>
            <span className="font-mono text-zinc-400">Lyria 2</span>
            <span className="text-zinc-800">·</span>
            <span className="font-mono text-zinc-400">Imagen 3</span>
            <span className="text-zinc-800">·</span>
            <span className="font-mono text-zinc-400">Gemini 3.1 Pro</span>
            <span className="text-zinc-800">·</span>
            <span className="font-mono text-amber-400/80">Parallel Search</span>
          </div>
        </div>
      </div>
    </div>
  );
}
