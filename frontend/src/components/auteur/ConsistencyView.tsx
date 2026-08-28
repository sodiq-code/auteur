/**
 * ConsistencyView — blueprint Section 30.2 row 9.
 * Bar chart of drift per shot; per-attribute breakdown; accept/reject.
 *
 * Calls POST /api/projects/{id}/shots/check-all to run the real Consistency
 * Check Agent (Gemini 3.1 Pro vision) on every shot, comparing each to the
 * character reference image.
 */
"use client";

import { useEffect, useState } from "react";
import { Gauge, ChevronRight, Check, RotateCcw, Loader2, AlertCircle, Play } from "lucide-react";
import { useStudio } from "@/lib/store";
import { checkAllShots, type ConsistencyAllResponse, type ConsistencyShotReport } from "@/lib/api";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";

export function ConsistencyView() {
  const { project, bible, setView } = useStudio();
  const [result, setResult] = useState<ConsistencyAllResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCheck() {
    if (!project) return;
    setLoading(true);
    setError(null);
    try {
      const r = await checkAllShots(project.id);
      setResult(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "consistency check failed");
    } finally {
      setLoading(false);
    }
  }

  // auto-run if we have shots (from the store)
  useEffect(() => {
    if (project && !result && !loading) {
      handleCheck();
    }
  }, [project]);

  const meanOverall = result?.mean_overall ?? 0;
  const threshold = result?.threshold ?? 0.25;
  const verdict = result?.verdict ?? "—";

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="mb-6">
        <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-zinc-700 bg-zinc-900/60 px-3 py-1 text-xs text-zinc-400">
          <Gauge className="h-3.5 w-3.5 text-teal-400" />
          Step 7 — Consistency Check
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-zinc-100">Drift dashboard</h2>
        <p className="mt-1.5 text-sm text-zinc-400">
          The Consistency Check Agent (Gemini 3.1 Pro vision) compares each shot
          to the character reference. Drift = 1 − consistency; threshold 0.25.
        </p>
      </div>

      {loading && (
        <div className="mb-6 flex items-center gap-2 rounded-lg border border-teal-500/30 bg-teal-500/5 px-4 py-3 text-xs text-teal-200">
          <Loader2 className="h-4 w-4 animate-spin" />
          Running Consistency Check Agent on {result?.shots.length || "all"} shots...
        </div>
      )}

      {error && (
        <div className="mb-6 flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-xs text-amber-200">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <div className="font-medium">Consistency check error</div>
            <div className="mt-0.5 text-amber-200/80">{error}</div>
          </div>
        </div>
      )}

      {/* mean overall + verdict */}
      {result && (
        <div className="mb-6 grid grid-cols-3 gap-3">
          <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
            <div className="text-[10px] uppercase tracking-wide text-zinc-500">Mean consistency</div>
            <div className={`mt-1 font-mono text-2xl font-bold ${meanOverall >= 0.75 ? "text-emerald-400" : "text-amber-400"}`}>
              {meanOverall.toFixed(3)}
            </div>
          </div>
          <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
            <div className="text-[10px] uppercase tracking-wide text-zinc-500">Drift threshold</div>
            <div className="mt-1 font-mono text-2xl font-bold text-zinc-100">{threshold}</div>
          </div>
          <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
            <div className="text-[10px] uppercase tracking-wide text-zinc-500">Verdict</div>
            <div className={`mt-1 font-mono text-2xl font-bold ${verdict === "GO" ? "text-emerald-400" : verdict === "PARTIAL" ? "text-amber-400" : "text-zinc-400"}`}>
              {verdict}
            </div>
          </div>
        </div>
      )}

      {/* per-shot results */}
      {result && (
        <div className="space-y-4">
          {result.shots.map((s) => (
            <ShotDriftCard key={s.shot_id} shot={s} />
          ))}
        </div>
      )}

      {/* run button */}
      <div className="mt-6 flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-900/40 px-4 py-3">
        <span className="text-xs text-zinc-400">
          {result ? `checked ${result.shots.length} shots in ${result.elapsed_sec}s` : "no checks run yet"}
        </span>
        <div className="flex gap-2">
          <button
            onClick={handleCheck}
            disabled={loading || !project}
            className="inline-flex items-center gap-1.5 rounded-md border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-xs font-medium text-zinc-300 transition hover:border-zinc-600 disabled:opacity-50"
          >
            {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RotateCcw className="h-3.5 w-3.5" />}
            Re-check all
          </button>
          <button
            onClick={() => setView("assembly")}
            disabled={!result}
            className="inline-flex items-center gap-1.5 rounded-md bg-teal-500 px-3 py-1.5 text-xs font-semibold text-zinc-950 transition hover:bg-teal-400 disabled:opacity-50"
          >
            Assemble film
            <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}

function ShotDriftCard({ shot }: { shot: ConsistencyShotReport }) {
  const overall = shot.overall ?? 0;
  const drift = shot.drift_score ?? (1 - overall);
  const passes = drift <= 0.25;
  const hasData = shot.status === "checked" || shot.status === "cached";
  const hasError = shot.status === "failed" || shot.status === "no_video" || shot.status === "frame_extract_failed" || shot.status === "no_char_ref" || shot.status === "check_failed";

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="grid h-6 w-6 place-items-center rounded bg-teal-500/15 font-mono text-xs font-bold text-teal-300">
            {shot.order}
          </span>
          <span className="text-sm font-medium text-zinc-200">
            {shot.description ? shot.description.slice(0, 60) : `Shot ${shot.order}`}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {hasData ? (
            <>
              <span className={`font-mono text-sm font-bold ${overall >= 0.75 ? "text-emerald-400" : "text-amber-400"}`}>
                {overall.toFixed(2)}
              </span>
              <Badge className={`border-0 ${passes ? "bg-emerald-500/15 text-emerald-300" : "bg-amber-500/15 text-amber-300"}`}>
                {passes ? "accept" : "re-generate"}
              </Badge>
            </>
          ) : hasError ? (
            <Badge className="border-0 bg-rose-500/15 text-rose-300">{shot.status}</Badge>
          ) : (
            <Loader2 className="h-4 w-4 animate-spin text-zinc-600" />
          )}
        </div>
      </div>

      {hasData && (
        <>
          <div className="mb-2">
            <div className="mb-1 flex justify-between text-[10px] font-mono text-zinc-500">
              <span>overall consistency</span>
              <span>drift {drift.toFixed(3)} · {passes ? "PASS" : "REVIEW"}</span>
            </div>
            <Progress value={overall * 100} className="h-2 bg-zinc-800 [&>div]:bg-gradient-to-r [&>div]:from-teal-500 [&>div]:to-emerald-400" />
          </div>

          <div className="grid grid-cols-4 gap-2">
            {([
              ["face", shot.face_identity],
              ["age", shot.age_appearance],
              ["beard", shot.beard_facial_hair],
              ["wardrobe", shot.wardrobe],
            ] as const).map(([k, v]) => (
              <div key={k} className="rounded bg-zinc-950/50 px-2 py-1.5 text-center">
                <div className="text-[9px] uppercase text-zinc-500">{k}</div>
                <div className={`font-mono text-xs font-bold ${(v ?? 0) >= 0.9 ? "text-emerald-400" : (v ?? 0) >= 0.75 ? "text-amber-400" : "text-rose-400"}`}>
                  {(v ?? 0).toFixed(2)}
                </div>
              </div>
            ))}
          </div>

          {shot.notes && (
            <p className="mt-2 text-[11px] text-zinc-500">{shot.notes}</p>
          )}
        </>
      )}

      {hasError && (
        <p className="text-[11px] text-rose-400/70">
          {shot.error || shot.note || `Status: ${shot.status}`}
        </p>
      )}

      {hasData && (
        <div className="mt-3 flex gap-2">
          <button className="inline-flex items-center gap-1 rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-[11px] font-medium text-emerald-300 transition hover:bg-emerald-500/20">
            <Check className="h-3 w-3" /> Accept
          </button>
          <button className="inline-flex items-center gap-1 rounded-md border border-zinc-700 bg-zinc-900 px-2.5 py-1 text-[11px] font-medium text-zinc-400 transition hover:border-zinc-600 hover:text-zinc-200">
            <RotateCcw className="h-3 w-3" /> Re-generate
          </button>
        </div>
      )}
    </div>
  );
}
