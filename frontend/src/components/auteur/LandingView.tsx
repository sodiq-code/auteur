/**
 * LandingView — blueprint Section 30.2 row 1 + Day 11 (canonical demo).
 *
 * Loads the pre-rendered canonical demo by default (the safety net — visitors
 * see the demo instantly). The "Make your first film" CTA triggers the real
 * logline → research → bible pipeline.
 */
"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { Film, Play, Sparkles, ArrowRight, Zap, Check, Loader2 } from "lucide-react";
import { useStudio } from "@/lib/store";
import { getDemo, type DemoData } from "@/lib/api";

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

  return (
    <div className="relative flex min-h-[calc(100vh-3.5rem)] flex-col items-center justify-center overflow-hidden px-4 py-12">
      {/* ambient glow */}
      <div className="pointer-events-none absolute -top-32 left-1/2 h-96 w-96 -translate-x-1/2 rounded-full bg-teal-500/15 blur-3xl auteur-hero-blob" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-72 w-72 rounded-full bg-amber-500/10 blur-3xl" />

      <div className="relative z-10 mx-auto max-w-3xl text-center">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-zinc-700 bg-zinc-900/60 px-3 py-1 text-xs text-zinc-400 backdrop-blur">
          <Sparkles className="h-3.5 w-3.5 text-amber-400" />
          The Film Bible Agent · Agentic Cinema Hackathon
        </div>

        <h1 className="text-4xl font-bold leading-tight tracking-tight text-zinc-100 sm:text-6xl">
          AI cinema&apos;s memory.
          <br />
          <span className="bg-gradient-to-r from-teal-400 via-emerald-300 to-amber-300 bg-clip-text text-transparent">
            Consistent across every shot.
          </span>
        </h1>

        <p className="mx-auto mt-6 max-w-xl text-sm leading-relaxed text-zinc-400 sm:text-base">
          An agentic AI film studio that maintains a persistent, research-grounded
          Film Bible and enforces cross-shot consistency across every Veo 3.1,
          Chirp 3, Lyria 2, and Imagen 3 generation call.
        </p>

        {/* side-by-side signature moment (from the pre-rendered demo) */}
        <div className="mx-auto mt-10 max-w-2xl overflow-hidden rounded-xl border border-zinc-800 bg-zinc-900/40 shadow-2xl shadow-teal-500/5">
          {loading ? (
            <div className="flex aspect-[1920/440] items-center justify-center bg-zinc-950">
              <Loader2 className="h-6 w-6 animate-spin text-teal-400" />
            </div>
          ) : (
            <Image
              src="/auteur/day1/side-by-side.png"
              alt="Side-by-side: one character held consistent across four scenes"
              width={1920}
              height={440}
              className="h-auto w-full"
              priority
            />
          )}
        </div>
        <p className="mt-2 text-[11px] text-zinc-500">
          One character reference · four scenes · Veo 3.1 ASSET consistency
        </p>

        {/* demo stats (from the pre-rendered canonical demo) */}
        {demo && (
          <div className="mt-6 flex items-center justify-center gap-6 text-xs">
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
              <span className="text-zinc-500">pre-rendered demo</span>
            </div>
          </div>
        )}

        <button
          onClick={() => setView("logline")}
          className="group mt-8 inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-teal-500 to-emerald-500 px-6 py-3 text-sm font-semibold text-zinc-950 shadow-lg shadow-teal-500/25 transition hover:shadow-teal-500/40 hover:brightness-110"
        >
          <Film className="h-4 w-4" />
          Make your first film
          <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
        </button>

        <div className="mt-8 flex items-center justify-center gap-6 text-[11px] text-zinc-600">
          <span className="flex items-center gap-1.5">
            <Play className="h-3 w-3" /> 4-shot short film
          </span>
          <span>~5 min end-to-end</span>
          <span>Google Cloud native</span>
        </div>
      </div>
    </div>
  );
}
