/**
 * ShotDetailDialog row 8.
 * Click a shot in the grid to see full detail: video frame, bible refs,
 * consistency report, re-generate button.
 */
"use client";

import Image from "next/image";
import { Film, Mic, Music, X, RotateCcw, Check, ExternalLink, BookOpen } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

interface ShotDetail {
  id: number;
  label: string;
  scene: string;
  frame: string;
  scores: { face: number; age: number; beard: number; wardrobe: number; overall: number };
  notes: string;
}

export function ShotDetailDialog({
  shot,
  open,
  onOpenChange,
}: {
  shot: ShotDetail | null;
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  if (!shot) return null;
  const drift = 1 - shot.scores.overall;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl border-zinc-800 bg-zinc-950 p-0">
        <DialogHeader className="border-b border-zinc-800 p-4">
          <DialogTitle className="flex items-center gap-2 text-base font-semibold text-zinc-100">
            <span className="grid h-7 w-7 place-items-center rounded bg-teal-500/15 font-mono text-xs font-bold text-teal-300">
              {shot.id}
            </span>
            {shot.label}
            <Badge className="ml-auto border-0 bg-emerald-500/15 text-emerald-300">
              <Check className="mr-1 h-3 w-3" />consistent
            </Badge>
          </DialogTitle>
        </DialogHeader>

        <div className="max-h-[70vh] overflow-y-auto p-4 auteur-scroll">
          {/* frame — use <video> if the frame is a video URL, otherwise <Image> */}
          <div className="relative mb-4 aspect-video overflow-hidden rounded-lg border border-zinc-800">
            {shot.frame.startsWith("http") || shot.frame.startsWith("/api/") ? (
              <video
                src={shot.frame}
                className="h-full w-full object-cover"
                controls
                autoPlay
                loop
              />
            ) : (
              <Image src={shot.frame} alt={shot.label} fill className="object-cover" sizes="640px" />
            )}
            <div className="absolute bottom-2 left-2 rounded bg-zinc-950/80 px-2 py-0.5 font-mono text-[10px] text-teal-300 backdrop-blur">
              Veo 3.1 · 8s · 1280×720
            </div>
          </div>

          {/* scene */}
          <div className="mb-4 rounded-lg border border-zinc-800 bg-zinc-900/40 p-3">
            <div className="text-[10px] uppercase tracking-wide text-zinc-500">Scene</div>
            <p className="mt-1 text-sm text-zinc-200">{shot.scene}</p>
          </div>

          {/* consistency */}
          <div className="mb-4">
            <div className="mb-2 flex items-center gap-2 text-[10px] font-medium uppercase tracking-wide text-zinc-500">
              <Film className="h-3 w-3" /> Consistency check
            </div>
            <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-3">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-xs text-zinc-400">overall</span>
                <span className={`font-mono text-sm font-bold ${shot.scores.overall >= 0.9 ? "text-emerald-400" : "text-amber-400"}`}>
                  {shot.scores.overall.toFixed(2)}
                </span>
              </div>
              <Progress value={shot.scores.overall * 100} className="mb-3 h-2 bg-zinc-800 [&>div]:bg-gradient-to-r [&>div]:from-teal-500 [&>div]:to-emerald-400" />
              <div className="grid grid-cols-4 gap-2">
                {([
                  ["face", shot.scores.face],
                  ["age", shot.scores.age],
                  ["beard", shot.scores.beard],
                  ["wardrobe", shot.scores.wardrobe],
                ] as const).map(([k, v]) => (
                  <div key={k} className="rounded bg-zinc-950/50 px-2 py-1.5 text-center">
                    <div className="text-[9px] uppercase text-zinc-500">{k}</div>
                    <div className={`font-mono text-xs font-bold ${v >= 0.9 ? "text-emerald-400" : v >= 0.75 ? "text-amber-400" : "text-rose-400"}`}>
                      {v.toFixed(2)}
                    </div>
                  </div>
                ))}
              </div>
              <p className="mt-2 text-[11px] text-zinc-500">{shot.notes}</p>
              <p className="mt-1 text-[10px] text-zinc-600">drift: {drift.toFixed(3)} · threshold 0.25 · {drift <= 0.25 ? "PASS" : "REVIEW"}</p>
            </div>
          </div>

          {/* bible refs */}
          <div className="mb-4">
            <div className="mb-2 flex items-center gap-2 text-[10px] font-medium uppercase tracking-wide text-zinc-500">
              <BookOpen className="h-3 w-3" /> Bible references
            </div>
            <div className="space-y-1.5">
              <div className="flex items-center gap-2 rounded-lg border border-zinc-800 bg-zinc-900/40 px-3 py-2 text-xs">
                <span className="text-zinc-500">Character:</span>
                <span className="text-zinc-200">Ewan MacAskill</span>
                <Badge variant="outline" className="ml-auto border-zinc-700 text-[9px] text-zinc-500">v1</Badge>
              </div>
              <div className="flex items-center gap-2 rounded-lg border border-zinc-800 bg-zinc-900/40 px-3 py-2 text-xs">
                <span className="text-zinc-500">Location:</span>
                <span className="text-zinc-200">Skerryvore Lighthouse</span>
                <Badge variant="outline" className="ml-auto border-zinc-700 text-[9px] text-zinc-500">v1</Badge>
              </div>
              <div className="flex items-center gap-2 rounded-lg border border-zinc-800 bg-zinc-900/40 px-3 py-2 text-xs">
                <span className="text-zinc-500">Wardrobe:</span>
                <span className="text-zinc-200">Oilskin storm coat</span>
              </div>
            </div>
          </div>

          {/* modality calls */}
          <div className="mb-4">
            <div className="mb-2 flex items-center gap-2 text-[10px] font-medium uppercase tracking-wide text-zinc-500">
              Generation calls
            </div>
            <div className="grid grid-cols-3 gap-2">
              {[
                { m: "veo", label: "Veo 3.1", icon: Film, color: "text-teal-400" },
                { m: "chirp", label: "Chirp 3", icon: Mic, color: "text-amber-400" },
                { m: "lyria", label: "Lyria 2", icon: Music, color: "text-purple-400" },
              ].map(({ m, label, icon: Icon, color }) => (
                <div key={m} className="flex flex-col items-center gap-1 rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-2.5">
                  <Icon className={`h-4 w-4 ${color}`} />
                  <span className="text-[10px] font-mono text-zinc-400">{label}</span>
                  <Check className="h-3 w-3 text-emerald-400" />
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* footer */}
        <div className="flex items-center justify-between border-t border-zinc-800 p-3">
          <a href="https://en.wikipedia.org/wiki/Fresnel_lens" target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-[11px] text-teal-400/70 transition hover:text-teal-300">
            <ExternalLink className="h-3 w-3" /> view citation
          </a>
          <button className="inline-flex items-center gap-1.5 rounded-md border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-xs font-medium text-zinc-300 transition hover:border-zinc-600 hover:text-zinc-100">
            <RotateCcw className="h-3.5 w-3.5" /> Re-generate
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
