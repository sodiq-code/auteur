/**
 * SideBySide — blueprint Section 30.5, the signature moment.
 *
 * Shows one character reference + 4 generated shot frames side-by-side,
 * demonstrating that Veo 3.1 holds the character consistent across scenes.
 * This is the "impossible to forget" visual proof (blueprint Section 17).
 *
 * Used on: Landing (hero), Share (public showcase), Grid (detail).
 */
"use client";

import Image from "next/image";
import { Eye, Check, AlertCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface Shot {
  id: number;
  label: string;
  scene: string;
  frame: string;
  score: number;
}

interface SideBySideProps {
  characterRef?: string;
  shots?: Shot[];
  meanOverall?: number;
  verdict?: string;
  compact?: boolean;
}

const DEFAULT_SHOTS: Shot[] = [
  { id: 1, label: "Lamp Room", scene: "Interior, dusk", frame: "/auteur/demo/shot-1.png", score: 0.95 },
  { id: 2, label: "Rocks", scene: "Coastal, dawn", frame: "/auteur/demo/shot-2.png", score: 0.85 },
  { id: 3, label: "Interior", scene: "Candlelight", frame: "/auteur/demo/shot-3.png", score: 0.95 },
  { id: 4, label: "Exterior", scene: "Balcony, dusk", frame: "/auteur/demo/shot-4.png", score: 0.95 },
];

export function SideBySide({
  characterRef = "/auteur/demo/character-reference.png",
  shots = DEFAULT_SHOTS,
  meanOverall = 0.925,
  verdict = "GO",
  compact = false,
}: SideBySideProps) {
  const allShots = [characterRef, ...shots.map((s) => s.frame)];

  return (
    <div className="overflow-hidden rounded-xl border border-zinc-800 bg-zinc-950">
      {/* header bar */}
      <div className="flex items-center justify-between border-b border-zinc-800 bg-zinc-900/60 px-4 py-2.5">
        <div className="flex items-center gap-2">
          <Eye className="h-4 w-4 text-teal-400" />
          <span className="text-xs font-semibold text-zinc-200">Cross-shot character consistency</span>
        </div>
        <div className="flex items-center gap-2">
          <Badge className={`border-0 ${verdict === "GO" ? "bg-emerald-500/15 text-emerald-300" : "bg-amber-500/15 text-amber-300"}`}>
            <Check className="mr-1 h-3 w-3" />
            {verdict} · {meanOverall.toFixed(2)}
          </Badge>
        </div>
      </div>

      {/* the side-by-side grid: char ref + 4 shots */}
      <div className={`grid ${compact ? "grid-cols-5" : "grid-cols-2 sm:grid-cols-5"} gap-0.5`}>
        {/* character reference */}
        <div className="group relative overflow-hidden border-b border-zinc-800 sm:border-b-0">
          <div className="relative aspect-video">
            <Image
              src={characterRef}
              alt="Character reference"
              fill
              className="object-cover"
              sizes="200px"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-zinc-950/80 via-transparent to-transparent" />
            <div className="absolute bottom-2 left-2">
              <div className="rounded bg-teal-500/90 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide text-zinc-950 backdrop-blur">
                Reference
              </div>
              <div className="mt-0.5 text-[10px] text-zinc-300">Ewan, 52</div>
            </div>
          </div>
        </div>

        {/* 4 shot frames */}
        {shots.map((shot) => (
          <div key={shot.id} className="group relative overflow-hidden">
            <div className="relative aspect-video">
              <Image
                src={shot.frame}
                alt={`Shot ${shot.id} — ${shot.label}`}
                fill
                className="object-cover transition duration-500 group-hover:scale-105"
                sizes="200px"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-zinc-950/80 via-transparent to-transparent" />
              <div className="absolute left-2 top-2 rounded bg-zinc-950/80 px-1.5 py-0.5 font-mono text-[9px] text-teal-300 backdrop-blur">
                #{shot.id}
              </div>
              <div className="absolute right-2 top-2 rounded bg-zinc-950/80 px-1.5 py-0.5 font-mono text-[9px] text-emerald-300 backdrop-blur">
                {shot.score.toFixed(2)}
              </div>
              <div className="absolute bottom-2 left-2">
                <div className="text-[10px] font-medium text-zinc-200">{shot.label}</div>
                <div className="text-[9px] text-zinc-400">{shot.scene}</div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* footer */}
      <div className="border-t border-zinc-800 bg-zinc-900/40 px-4 py-2">
        <p className="text-[10px] text-zinc-500">
          Veo 3.1 ASSET reference · same character across 4 scenes · drift threshold 0.25
        </p>
      </div>
    </div>
  );
}
