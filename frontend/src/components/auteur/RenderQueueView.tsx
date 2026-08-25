/**
 * RenderQueueView — blueprint Section 30.2 row 6.
 * Live status of Veo/Chirp/Lyria/Imagen calls; thumbnails as they complete; drift scores.
 */
"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, Check, Film, Mic, Music, Image as ImageIcon, ChevronRight } from "lucide-react";
import { useStudio } from "@/lib/store";
import Image from "next/image";
import { Badge } from "@/components/ui/badge";

const MODALITY_META = {
  veo: { label: "Veo 3.1", icon: Film, color: "text-teal-400", duration: 45 },
  chirp: { label: "Chirp 3", icon: Mic, color: "text-amber-400", duration: 8 },
  lyria: { label: "Lyria 2", icon: Music, color: "text-purple-400", duration: 30 },
  imagen: { label: "Imagen", icon: ImageIcon, color: "text-rose-400", duration: 15 },
} as const;

export function RenderQueueView() {
  const { shots, setView } = useStudio();
  const [progress, setProgress] = useState<Record<string, number>>({});

  // simulate the render queue progress
  useEffect(() => {
    if (shots.length === 0) return;
    const total = shots.length * 3; // 3 modalities per shot
    let done = 0;
    const timer = setInterval(() => {
      done += 1;
      setProgress((prev) => ({ ...prev, [done]: true }));
      if (done >= total) {
        clearInterval(timer);
        setTimeout(() => setView("grid"), 800);
      }
    }, 1200);
    return () => clearInterval(timer);
  }, [shots, setView]);

  if (shots.length === 0) {
    return <div className="p-8 text-sm text-zinc-500">Generate a shot list first.</div>;
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="mb-6">
        <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-zinc-700 bg-zinc-900/60 px-3 py-1 text-xs text-zinc-400">
          <Loader2 className="h-3.5 w-3.5 animate-spin text-teal-400" />
          Step 5 — Render Queue
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-zinc-100">Rendering your film</h2>
        <p className="mt-1.5 text-sm text-zinc-400">
          The Director Agent calls Veo 3.1, Chirp 3, and Lyria 2 per shot, with the
          Film Bible injected as context. Watch each modality complete.
        </p>
      </div>

      <div className="space-y-4">
        {shots.map((shot, shotIdx) => {
          const shotDoneCount = Object.keys(progress).filter((k) => {
            const n = parseInt(k);
            return n > shotIdx * 3 && n <= (shotIdx + 1) * 3;
          }).length;
          const shotDone = shotDoneCount === 3;
          return (
            <div
              key={shot.id}
              className={`rounded-lg border bg-zinc-900/40 p-4 transition ${
                shotDone ? "border-emerald-500/30" : "border-zinc-800"
              }`}
            >
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="grid h-6 w-6 place-items-center rounded bg-teal-500/15 font-mono text-xs font-bold text-teal-300">
                    {shot.order}
                  </span>
                  <span className="text-sm text-zinc-200">{shot.description}</span>
                </div>
                {shotDone ? (
                  <Badge className="border-0 bg-emerald-500/15 text-emerald-300">done</Badge>
                ) : (
                  <Loader2 className="h-4 w-4 animate-spin text-teal-400" />
                )}
              </div>

              <div className="grid grid-cols-3 gap-2">
                {shot.modality_calls.map((m, mIdx) => {
                  const globalIdx = shotIdx * 3 + mIdx + 1;
                  const isDone = progress[globalIdx];
                  const meta = MODALITY_META[m];
                  const Icon = meta.icon;
                  return (
                    <div
                      key={m}
                      className={`flex flex-col items-center gap-1.5 rounded-md border p-2.5 transition ${
                        isDone
                          ? "border-emerald-500/30 bg-emerald-500/5"
                          : "border-zinc-800 bg-zinc-950/40"
                      }`}
                    >
                      <Icon className={`h-4 w-4 ${isDone ? "text-emerald-400" : meta.color}`} />
                      <span className="text-[10px] font-mono text-zinc-400">{meta.label}</span>
                      {isDone ? (
                        <Check className="h-3 w-3 text-emerald-400" />
                      ) : (
                        <Loader2 className="h-3 w-3 animate-spin text-zinc-600" />
                      )}
                    </div>
                  );
                })}
              </div>

              {shotDone && shot.order <= 4 && (
                <div className="mt-3 overflow-hidden rounded-md border border-zinc-800">
                  <Image
                    src={`/auteur/day1/shot-${shot.order}.png`}
                    alt={`Shot ${shot.order} frame`}
                    width={352}
                    height={198}
                    className="aspect-video w-full object-cover"
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="mt-6 flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-900/40 px-4 py-3">
        <span className="text-xs text-zinc-400">
          {Object.keys(progress).length}/{shots.length * 3} modalities complete
        </span>
        <button
          onClick={() => setView("grid")}
          className="inline-flex items-center gap-1.5 rounded-md bg-teal-500 px-3 py-1.5 text-xs font-semibold text-zinc-950 transition hover:bg-teal-400"
        >
          View shot grid
          <ChevronRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}
