/**
 * ShotListView — blueprint Section 30.2 row 5.
 * Table of 4 shots with bible refs; "Generate" button per shot.
 *
 * Fetches real shots from GET /api/projects/{id}/shots (created by build-bible).
 */
"use client";

import { useEffect, useState } from "react";
import { ChevronRight, Film, Clapperboard, Loader2 } from "lucide-react";
import { useStudio } from "@/lib/store";
import { getShots, type ShotSpec } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { EmptyState, Spinner } from "@/components/auteur/StateComponents";
import type { FilmBible } from "@/lib/types";

export function ShotListView() {
  const { bible, project, setView, setShots } = useStudio();
  const [realShots, setRealShots] = useState<ShotSpec[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!project) {
      return;
    }
    let cancelled = false;
    getShots(project.id)
      .then((data) => {
        if (cancelled) return;
        setRealShots(data.shots);
        setShots(data.shots);
      })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [project, setShots]);

  if (!bible || !project) {
    return <EmptyState title="No Bible yet" description="Submit a logline and build a Bible first." ctaLabel="Start" onCta={() => setView("logline")} />;
  }

  if (loading) {
    return <Spinner label="Fetching shots from backend..." />;
  }

  const shots = realShots.length > 0 ? realShots : [];

  if (shots.length === 0) {
    return <EmptyState title="No shots" description="The Director Agent should have created shots. Try rebuilding the Bible." ctaLabel="Rebuild Bible" onCta={() => setView("research")} />;
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="auteur-rise mb-6">
        <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-zinc-700 bg-zinc-900/60 px-3 py-1 text-xs text-zinc-400">
          <Clapperboard className="h-3.5 w-3.5 text-teal-400" />
          Step 4 — Shot List
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-zinc-100">The shot list</h2>
        <p className="mt-1.5 text-sm text-zinc-400">
          {shots.length} shots, each citing the Bible version that produced it. Each shot calls
          Veo 3.1 (video), Chirp 3 (voice), and Lyria 2 (score).
        </p>
      </div>

      <div className="overflow-hidden rounded-lg border border-zinc-800">
        <table className="w-full text-sm">
          <thead className="bg-zinc-900/60 text-[10px] uppercase tracking-wide text-zinc-500">
            <tr>
              <th className="px-3 py-2 text-left">#</th>
              <th className="px-3 py-2 text-left">Description</th>
              <th className="hidden px-3 py-2 text-left sm:table-cell">Bible refs</th>
              <th className="px-3 py-2 text-left">Calls</th>
              <th className="px-3 py-2 text-right">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800">
            {shots.map((s) => (
              <ShotRow key={s.id} shot={s} bible={bible} />
            ))}
          </tbody>
        </table>
      </div>

      <div className="auteur-rise mt-6 flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-900/40 px-4 py-3" style={{ animationDelay: "0.1s" }}>
        <span className="text-xs text-zinc-400">
          {shots.length} shots · Bible v{bible.version} · max 4 (hackathon scope)
        </span>
        <button
          onClick={() => setView("render")}
          className="inline-flex items-center gap-1.5 rounded-md bg-teal-500 px-3 py-1.5 text-xs font-semibold text-zinc-950 transition hover:bg-teal-400"
        >
          Start rendering
          <ChevronRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}

function ShotRow({ shot, bible }: { shot: ShotSpec; bible: FilmBible }) {
  const chars = shot.character_ids
    .map((id) => bible.characters.find((c) => c.id === id)?.name)
    .filter(Boolean)
    .join(", ");
  const loc = bible.locations.find((l) => l.id === shot.location_id)?.name;

  return (
    <tr className="bg-zinc-900/20 transition hover:bg-zinc-900/40">
      <td className="px-3 py-3">
        <span className="grid h-6 w-6 place-items-center rounded bg-teal-500/15 font-mono text-xs font-bold text-teal-300">
          {shot.order}
        </span>
      </td>
      <td className="px-3 py-3 text-xs text-zinc-200">{shot.description}</td>
      <td className="hidden px-3 py-3 text-[11px] text-zinc-500 sm:table-cell">
        <div>Char: {chars || "—"}</div>
        <div>Loc: {loc || "—"}</div>
      </td>
      <td className="px-3 py-3">
        <div className="flex gap-1">
          {shot.modality_calls.map((m) => (
            <Badge key={m} variant="outline" className="border-zinc-700 px-1.5 py-0 text-[9px] font-mono text-zinc-400">
              {m}
            </Badge>
          ))}
        </div>
      </td>
      <td className="px-3 py-3 text-right">
        <Badge variant="outline" className={`border-zinc-700 text-[10px] ${shot.status === "generated" ? "text-emerald-400" : "text-zinc-500"}`}>
          {shot.status}
        </Badge>
      </td>
    </tr>
  );
}
