/**
 * ShotGridView — blueprint Section 30.2 row 7 + Day 12 (UX polish).
 * 2x2 grid of 4 shots + the SideBySide signature moment; click any for detail.
 */
"use client";

import Image from "next/image";
import { Grid3x3, ChevronRight, Check } from "lucide-react";
import { useStudio } from "@/lib/store";
import { Badge } from "@/components/ui/badge";
import { SideBySide } from "@/components/auteur/SideBySide";
import { EmptyState } from "@/components/auteur/StateComponents";

const SHOT_DATA = [
  { id: 1, label: "Lamp Room", scene: "Interior, dusk · polishing the lens", score: 0.95, frame: "/auteur/day1/shot-1.png", notes: "Re-framed to three-quarter profile after stricter model flagged obscured face." },
  { id: 2, label: "Rocks", scene: "Coastal, dawn · the bottle", score: 0.85, frame: "/auteur/day1/shot-2.png", notes: "Re-framed to medium shot after wide-shot drift; face in profile + shadow." },
  { id: 3, label: "Interior", scene: "Candlelight · reading the message", score: 0.95, frame: "/auteur/day1/shot-3.png", notes: "Near-perfect match across all dimensions." },
  { id: 4, label: "Exterior", scene: "Balcony · stormy sea, dusk", score: 0.95, frame: "/auteur/day1/shot-4.png", notes: "Excellent match. Coat, sweater, beard all consistent." },
];

interface ShotGridProps {
  onShotClick?: (shot: typeof SHOT_DATA[number]) => void;
}

export function ShotGridView({ onShotClick }: ShotGridProps = {}) {
  const setView = useStudio((s) => s.setView);
  const bible = useStudio((s) => s.bible);

  if (!bible && !SHOT_DATA.length) {
    return <EmptyState title="No shots generated yet" description="Build a Bible first, then generate shots." ctaLabel="Start" onCta={() => setView("logline")} />;
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="auteur-rise mb-6">
        <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-zinc-700 bg-zinc-900/60 px-3 py-1 text-xs text-zinc-400">
          <Grid3x3 className="h-3.5 w-3.5 text-teal-400" />
          Step 6 — Shot Grid
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-zinc-100">One character. Four scenes.</h2>
        <p className="mt-1.5 text-sm text-zinc-400">
          The signature moment: the same character held consistent across four
          different scenes via the Veo 3.1 ASSET reference.
        </p>
      </div>

      {/* SideBySide signature moment */}
      <div className="auteur-rise mb-6" style={{ animationDelay: "0.1s" }}>
        <SideBySide
          shots={SHOT_DATA.map((s) => ({ id: s.id, label: s.label, scene: s.scene.split(" · ")[0], frame: s.frame, score: s.score }))}
          meanOverall={0.925}
          verdict="GO"
        />
      </div>

      {/* individual shot cards */}
      <div className="grid grid-cols-2 gap-3">
        {SHOT_DATA.map((s) => (
          <button
            key={s.id}
            onClick={() => onShotClick?.(s)}
            className="auteur-shot-card group relative block w-full overflow-hidden rounded-lg border border-zinc-800 bg-zinc-900/40 text-left"
          >
            <div className="relative aspect-video overflow-hidden">
              <Image
                src={s.frame}
                alt={`Shot ${s.id} — ${s.label}`}
                fill
                className="object-cover transition group-hover:scale-105"
                sizes="(max-width: 640px) 50vw, 400px"
              />
              <div className="absolute left-2 top-2 rounded bg-zinc-950/80 px-1.5 py-0.5 font-mono text-[10px] text-teal-300 backdrop-blur">
                #{s.id}
              </div>
              <div className="absolute right-2 top-2 rounded bg-zinc-950/80 px-1.5 py-0.5 font-mono text-[10px] text-emerald-300 backdrop-blur">
                {s.score.toFixed(2)}
              </div>
            </div>
            <div className="p-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-zinc-200">{s.label}</span>
                <Badge className="border-0 bg-emerald-500/15 px-1.5 py-0 text-[9px] text-emerald-300">
                  <Check className="mr-0.5 h-2.5 w-2.5" />consistent
                </Badge>
              </div>
              <p className="mt-0.5 text-[11px] text-zinc-500">{s.scene}</p>
            </div>
          </button>
        ))}
      </div>

      <div className="auteur-rise mt-6 flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-900/40 px-4 py-3" style={{ animationDelay: "0.2s" }}>
        <span className="text-xs text-zinc-400">
          Mean consistency: <span className="font-mono text-emerald-400">0.925</span> · drift threshold 0.25
        </span>
        <button
          onClick={() => setView("consistency")}
          className="inline-flex items-center gap-1.5 rounded-md bg-teal-500 px-3 py-1.5 text-xs font-semibold text-zinc-950 transition hover:bg-teal-400"
        >
          Consistency dashboard
          <ChevronRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}
