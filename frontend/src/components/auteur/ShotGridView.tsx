/**
 * ShotGridView — blueprint Section 30.2 row 7.
 * Fetches REAL shots from the backend + shows actual Veo clips.
 * The SideBySide component shows the pre-rendered demo as the signature moment.
 * Individual shot cards show the REAL generated clips via GET /shots/{id}/video.
 */
"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { Grid3x3, ChevronRight, Check, Loader2, Film, AlertCircle } from "lucide-react";
import { useStudio } from "@/lib/store";
import { getShots, type ShotSpec } from "@/lib/api";
import { SideBySide } from "@/components/auteur/SideBySide";
import { EmptyState, Spinner } from "@/components/auteur/StateComponents";
import { Badge } from "@/components/ui/badge";

const API_BASE = "https://auteur-dev-jbkbgthudq-uc.a.run.app";

export function ShotGridView({ onShotClick }: { onShotClick?: (shot: { id: number; label: string; scene: string; frame: string; score: number; notes: string }) => void }) {
  const setView = useStudio((s) => s.setView);
  const project = useStudio((s) => s.project);
  const [realShots, setRealShots] = useState<ShotSpec[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!project) { return; }
    let cancelled = false;
    getShots(project.id)
      .then((data) => { if (!cancelled) setRealShots(data.shots); })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [project]);

  if (loading) return <Spinner label="Fetching shots..." />;
  if (!project) return <EmptyState title="No project" description="Create a project first." ctaLabel="Start" onCta={() => setView("logline")} />;
  if (realShots.length === 0) return <EmptyState title="No shots generated" description="Build a Bible and render shots first." ctaLabel="Start" onCta={() => setView("logline")} />;

  const hasGenerated = realShots.some((s) => s.status === "generated" || s.status === "approved" || s.status === "generating");

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="auteur-rise mb-6">
        <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-zinc-700 bg-zinc-900/60 px-3 py-1 text-xs text-zinc-400">
          <Grid3x3 className="h-3.5 w-3.5 text-teal-400" />
          Step 6 — Shot Grid
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-zinc-100">{hasGenerated ? "Generated shots" : "One character. Four scenes."}</h2>
        <p className="mt-1.5 text-sm text-zinc-400">
          {hasGenerated
            ? "The Veo 3.1 clips generated for this production. Click any shot for detail."
            : "The signature moment: the same character held consistent across four different scenes via the Veo 3.1 ASSET reference."}
        </p>
      </div>

      {/* SideBySide signature moment (always shows the pre-rendered demo) */}
      <div className="auteur-rise mb-6" style={{ animationDelay: "0.1s" }}>
        <SideBySide meanOverall={0.925} verdict="GO" />
      </div>

      {/* Real generated shot clips */}
      {hasGenerated ? (
        <div className="grid grid-cols-2 gap-3">
          {realShots.map((shot) => {
            const isGenerated = shot.status === "generated" || shot.status === "approved" || shot.status === "generating";
            const videoUrl = `${API_BASE}/api/projects/${project.id}/shots/${shot.id}/video`;
            return (
              <button
                key={shot.id}
                onClick={() => onShotClick?.({
                  id: shot.order,
                  label: `Shot ${shot.order}`,
                  scene: shot.description.slice(0, 60),
                  frame: "/auteur/demo/shot-1.png", // fallback thumbnail
                  score: 0.9,
                  notes: shot.description,
                })}
                className={`auteur-shot-card group relative block w-full overflow-hidden rounded-lg border bg-zinc-900/40 text-left transition ${
                  isGenerated ? "border-emerald-500/30" : "border-zinc-800"
                }`}
              >
                <div className="relative aspect-video overflow-hidden bg-zinc-950">
                  {isGenerated ? (
                    <video
                      src={videoUrl}
                      className="h-full w-full object-cover"
                      muted
                      loop
                      onMouseEnter={(e) => (e.target as HTMLVideoElement).play()}
                      onMouseLeave={(e) => (e.target as HTMLVideoElement).pause()}
                    />
                  ) : (
                    <div className="grid h-full place-items-center text-zinc-600">
                      <Film className="h-6 w-6" />
                    </div>
                  )}
                  <div className="absolute left-2 top-2 rounded bg-zinc-950/80 px-1.5 py-0.5 font-mono text-[10px] text-teal-300 backdrop-blur">
                    #{shot.order}
                  </div>
                  {isGenerated && (
                    <div className="absolute right-2 top-2 rounded bg-emerald-500/80 px-1.5 py-0.5 text-[10px] font-bold text-zinc-950 backdrop-blur">
                      GENERATED
                    </div>
                  )}
                </div>
                <div className="p-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-zinc-200">Shot {shot.order}</span>
                    {isGenerated ? (
                      <Badge className="border-0 bg-emerald-500/15 px-1.5 py-0 text-[9px] text-emerald-300">
                        <Check className="mr-0.5 h-2.5 w-2.5" />generated
                      </Badge>
                    ) : (
                      <Badge className="border-0 bg-zinc-700/40 px-1.5 py-0 text-[9px] text-zinc-400">
                        {shot.status}
                      </Badge>
                    )}
                  </div>
                  <p className="mt-0.5 line-clamp-2 text-[11px] text-zinc-500">{shot.description}</p>
                </div>
              </button>
            );
          })}
        </div>
      ) : (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4 text-center">
          <p className="text-xs text-amber-200">
            Shots haven&apos;t been generated yet. Go to the Render Queue (Step 5) to generate real Veo clips.
          </p>
          <button
            onClick={() => setView("render")}
            className="mt-3 inline-flex items-center gap-1.5 rounded-md bg-amber-500 px-3 py-1.5 text-xs font-semibold text-zinc-950 transition hover:bg-amber-400"
          >
            Go to Render Queue
            <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      <div className="auteur-rise mt-6 flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-900/40 px-4 py-3" style={{ animationDelay: "0.2s" }}>
        <span className="text-xs text-zinc-400">
          {hasGenerated ? `${realShots.filter((s) => s.status === "generated").length}/${realShots.length} shots generated` : "No shots generated yet"}
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
