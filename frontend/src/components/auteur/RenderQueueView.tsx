/**
 * RenderQueueView — blueprint Section 30.2 row 6.
 * Live status of Veo/Chirp/Lyria/Imagen calls; thumbnails as they complete; drift scores.
 *
 * Calls POST /api/projects/{id}/shots/{shotId}/generate for each shot, running
 * the real generation pipeline on the deployed backend.
 */
"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, Check, Film, Mic, Music, ChevronRight, AlertCircle } from "lucide-react";
import { useStudio } from "@/lib/store";
import { generateShot } from "@/lib/api";
import Image from "next/image";
import { Badge } from "@/components/ui/badge";

const MODALITY_META = {
  veo: { label: "Veo 3.1", icon: Film, color: "text-teal-400" },
  chirp: { label: "Chirp 3", icon: Mic, color: "text-amber-400" },
  lyria: { label: "Lyria 2", icon: Music, color: "text-purple-400" },
} as const;

interface ShotGenState {
  shotId: string;
  order: number;
  description: string;
  modalities: Record<string, { status: string; size_bytes?: number; elapsed_sec?: number; error?: string }>;
  totalElapsed?: number;
  done: boolean;
}

export function RenderQueueView() {
  const { shots, bible, project, setView } = useStudio();
  const [genStates, setGenStates] = useState<Record<string, ShotGenState>>({});
  const [generating, setGenerating] = useState(false);
  const startedRef = useRef(false);

  // If no shots, build them from the bible
  const effectiveShots = shots.length > 0 ? shots : (bible ? bible.story_beats.slice(0, 4).map((beat, i) => ({
    id: `shot-${i + 1}`,
    order: beat.order,
    description: beat.description,
    bible_version: bible.version,
    character_ids: [],
    location_id: null,
    modality_calls: ["veo", "chirp", "lyria"] as const,
    status: "pending" as const,
  })) : []);

  useEffect(() => {
    if (startedRef.current || effectiveShots.length === 0 || !project) return;
    startedRef.current = true;
    setGenerating(true);

    // Generate each shot sequentially (concurrent Veo calls would hit quota)
    (async () => {
      for (const shot of effectiveShots) {
        setGenStates((prev) => ({
          ...prev,
          [shot.id]: {
            shotId: shot.id,
            order: shot.order,
            description: shot.description,
            modalities: {},
            done: false,
          },
        }));
        try {
          const result = await generateShot(project.id, shot.id, shot.bible_version || bible?.version || 1);
          setGenStates((prev) => ({
            ...prev,
            [shot.id]: {
              shotId: shot.id,
              order: shot.order,
              description: shot.description,
              modalities: result.modalities || {},
              totalElapsed: result.elapsed_sec,
              done: true,
            },
          }));
        } catch (e) {
          setGenStates((prev) => ({
            ...prev,
            [shot.id]: {
              ...prev[shot.id],
              modalities: { error: { status: "failed", error: e instanceof Error ? e.message : "generation failed" } },
              done: true,
            },
          }));
        }
      }
      setGenerating(false);
    })();
  }, [effectiveShots, project, bible]);

  const totalDone = Object.values(genStates).filter((s) => s.done).length;
  const allDone = totalDone === effectiveShots.length && totalDone > 0;

  if (effectiveShots.length === 0) {
    return <div className="p-8 text-sm text-zinc-500">Build a Bible first.</div>;
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="mb-6">
        <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-zinc-700 bg-zinc-900/60 px-3 py-1 text-xs text-zinc-400">
          {generating ? <Loader2 className="h-3.5 w-3.5 animate-spin text-teal-400" /> : <Check className="h-3.5 w-3.5 text-emerald-400" />}
          Step 5 — Render Queue
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-zinc-100">Rendering your film</h2>
        <p className="mt-1.5 text-sm text-zinc-400">
          The Director Agent calls Veo 3.1, Chirp 3, and Lyria 2 per shot, with the
          Film Bible injected as context. Each modality runs concurrently.
        </p>
      </div>

      <div className="space-y-4">
        {effectiveShots.map((shot) => {
          const gs = genStates[shot.id];
          const shotDone = gs?.done;
          const shotMods = gs?.modalities || {};
          const shotOk = shotDone && Object.values(shotMods).every((m) => m.status === "ok");
          const shotFailed = shotDone && !shotOk;
          return (
            <div
              key={shot.id}
              className={`rounded-lg border bg-zinc-900/40 p-4 transition ${
                shotOk ? "border-emerald-500/30" : shotFailed ? "border-amber-500/30" : "border-zinc-800"
              }`}
            >
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="grid h-6 w-6 place-items-center rounded bg-teal-500/15 font-mono text-xs font-bold text-teal-300">
                    {shot.order}
                  </span>
                  <span className="text-xs text-zinc-200">{shot.description}</span>
                </div>
                {shotOk ? (
                  <Badge className="border-0 bg-emerald-500/15 text-emerald-300">done</Badge>
                ) : shotFailed ? (
                  <Badge className="border-0 bg-amber-500/15 text-amber-300">partial</Badge>
                ) : (
                  <Loader2 className="h-4 w-4 animate-spin text-teal-400" />
                )}
              </div>

              <div className="grid grid-cols-3 gap-2">
                {(shot.modality_calls as string[]).map((m) => {
                  const modState = shotMods[m];
                  const isOk = modState?.status === "ok";
                  const isFailed = modState?.status === "failed";
                  const isActive = !shotDone;
                  const meta = MODALITY_META[m as keyof typeof MODALITY_META] || { label: m, icon: AlertCircle, color: "text-zinc-400" };
                  const Icon = meta.icon;
                  return (
                    <div
                      key={m}
                      className={`flex flex-col items-center gap-1.5 rounded-md border p-2.5 transition ${
                        isOk
                          ? "border-emerald-500/30 bg-emerald-500/5"
                          : isFailed
                            ? "border-rose-500/30 bg-rose-500/5"
                            : "border-zinc-800 bg-zinc-950/40"
                      }`}
                    >
                      <Icon className={`h-4 w-4 ${isOk ? "text-emerald-400" : isFailed ? "text-rose-400" : meta.color}`} />
                      <span className="text-[10px] font-mono text-zinc-400">{meta.label}</span>
                      {isOk ? (
                        <Check className="h-3 w-3 text-emerald-400" />
                      ) : isFailed ? (
                        <AlertCircle className="h-3 w-3 text-rose-400" />
                      ) : isActive ? (
                        <Loader2 className="h-3 w-3 animate-spin text-zinc-600" />
                      ) : (
                        <div className="h-3 w-3" />
                      )}
                      {isOk && modState?.size_bytes ? (
                        <span className="text-[9px] text-zinc-500">{(modState.size_bytes / 1024 / 1024).toFixed(1)}MB</span>
                      ) : isFailed ? (
                        <span className="text-[9px] text-rose-400/70">failed</span>
                      ) : null}
                    </div>
                  );
                })}
              </div>

              {shotDone && gs?.totalElapsed && (
                <div className="mt-2 text-[10px] text-zinc-600">
                  completed in {gs.totalElapsed}s
                  {shotFailed && " · some modalities failed (check logs)"}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="mt-6 flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-900/40 px-4 py-3">
        <span className="text-xs text-zinc-400">
          {generating ? `generating... ${totalDone}/${effectiveShots.length} shots done` : `${totalDone}/${effectiveShots.length} shots complete`}
        </span>
        <button
          onClick={() => setView("grid")}
          disabled={generating}
          className="inline-flex items-center gap-1.5 rounded-md bg-teal-500 px-3 py-1.5 text-xs font-semibold text-zinc-950 transition hover:bg-teal-400 disabled:opacity-50"
        >
          View shot grid
          <ChevronRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}
