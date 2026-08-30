/**
 * ConsistencyView — blueprint Section 30.2 row 9.
 * Drift dashboard with per-shot breakdown + working Accept/Re-generate.
 *
 * The Accept button marks a shot as approved (moves to assembly-ready).
 * The Re-generate button calls POST /shots/{id}/regenerate with drift
 * correction — the prior drift report is injected as corrective context
 * into the Veo prompt, then the shot is re-checked. The before/after
 * scores are shown inline.
 */
"use client";

import { useEffect, useState, useCallback } from "react";
import { Gauge, ChevronRight, Check, RotateCcw, Loader2, AlertCircle, Film, Zap } from "lucide-react";
import { useStudio } from "@/lib/store";
import {
  checkAllShots,
  getShots,
  regenerateShot,
  autoRegenerate,
  type ConsistencyAllResponse,
  type ConsistencyShotReport,
  type RegenerationResponse,
} from "@/lib/api";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { EmptyState, Spinner } from "@/components/auteur/StateComponents";

export function ConsistencyView() {
  const { project, bible, setView } = useStudio();
  const [result, setResult] = useState<ConsistencyAllResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [shotsReady, setShotsReady] = useState(false);
  const [checkingShots, setCheckingShots] = useState(true);
  const [autoRegenLoading, setAutoRegenLoading] = useState(false);
  const [autoRegenResult, setAutoRegenResult] = useState<string | null>(null);
  // Track per-shot regeneration state + results
  const [regenerating, setRegenerating] = useState<Record<string, boolean>>({});
  const [regenResults, setRegenResults] = useState<Record<string, RegenerationResponse>>({});
  // Track accepted shots
  const [accepted, setAccepted] = useState<Record<string, boolean>>({});

  // 1. First check if shots have been generated (status != "pending")
  useEffect(() => {
    if (!project) {
      setCheckingShots(false);
      return;
    }
    getShots(project.id)
      .then((data) => {
        const generated = data.shots.some((s) => s.status === "generated" || s.status === "approved" || s.status === "generating");
        setShotsReady(generated);
        setCheckingShots(false);
      })
      .catch(() => setCheckingShots(false));
  }, [project]);

  const handleCheck = useCallback(async () => {
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
  }, [project]);

  // Re-generate a single shot (the closed loop with drift correction)
  const handleRegenerate = useCallback(async (shotId: string, reason: string) => {
    if (!project || !bible) return;
    setRegenerating((prev) => ({ ...prev, [shotId]: true }));
    setError(null);
    try {
      const r = await regenerateShot(
        project.id,
        shotId,
        reason,
        bible.version,
        true, // use_drift_correction
      );
      setRegenResults((prev) => ({ ...prev, [shotId]: r }));
      // Re-run check-all to refresh the dashboard with the new scores
      await handleCheck();
    } catch (e) {
      setError(e instanceof Error ? e.message : "regeneration failed");
    } finally {
      setRegenerating((prev) => ({ ...prev, [shotId]: false }));
    }
  }, [project, bible, handleCheck]);

  // Accept a shot (marks it as accepted in the local state)
  const handleAccept = useCallback((shotId: string) => {
    setAccepted((prev) => ({ ...prev, [shotId]: true }));
  }, []);

  // Auto-regenerate all drifted shots (the autonomous loop)
  const handleAutoRegenerate = useCallback(async () => {
    if (!project) return;
    setAutoRegenLoading(true);
    setError(null);
    setAutoRegenResult(null);
    try {
      const r = await autoRegenerate(project.id);
      const n = r.shots_regenerated;
      setAutoRegenResult(
        n === 0
          ? `All ${r.shots_checked} shots passed the drift threshold (≤ ${r.threshold}). No regeneration needed.`
          : `Auto-regenerated ${n} of ${r.shots_checked} shots (those above the ${r.threshold} drift threshold).`,
      );
      // Refresh the dashboard
      await handleCheck();
    } catch (e) {
      setError(e instanceof Error ? e.message : "auto-regeneration failed");
    } finally {
      setAutoRegenLoading(false);
    }
  }, [project, handleCheck]);

  const meanOverall = result?.mean_overall ?? 0;
  const threshold = result?.threshold ?? 0.25;
  const verdict = result?.verdict ?? "—";

  // Show empty state if shots haven't been generated yet
  if (!checkingShots && !shotsReady) {
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
        <EmptyState
          icon={Film}
          title="No generated shots to check"
          description="Generate your shots first (Step 5 — Render Queue). The Consistency Check Agent needs Veo clips to compare against the character reference."
          ctaLabel="Go to Render Queue"
          onCta={() => setView("render")}
        />
      </div>
    );
  }

  if (checkingShots) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8">
        <Spinner label="Checking shot status..." />
      </div>
    );
  }

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
            <div className="font-medium">Error</div>
            <div className="mt-0.5 text-amber-200/80">{error}</div>
          </div>
        </div>
      )}

      {autoRegenResult && (
        <div className="mb-6 flex items-start gap-2 rounded-lg border border-teal-500/30 bg-teal-500/5 p-3 text-xs text-teal-200">
          <Zap className="mt-0.5 h-4 w-4 shrink-0 text-teal-400" />
          <div>
            <div className="font-medium">Autonomous loop</div>
            <div className="mt-0.5 text-teal-200/80">{autoRegenResult}</div>
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
            <ShotDriftCard
              key={s.shot_id}
              shot={s}
              projectId={project?.id}
              bibleVersion={bible?.version}
              onRegenerate={handleRegenerate}
              onAccept={handleAccept}
              isRegenerating={!!regenerating[s.shot_id]}
              regenResult={regenResults[s.shot_id]}
              isAccepted={!!accepted[s.shot_id]}
            />
          ))}
        </div>
      )}

      {/* action buttons */}
      <div className="mt-6 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-zinc-800 bg-zinc-900/40 px-4 py-3">
        <span className="text-xs text-zinc-400">
          {result ? `checked ${result.shots.length} shots in ${result.elapsed_sec}s` : "no checks run yet"}
        </span>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={handleCheck}
            disabled={loading || !project}
            className="inline-flex items-center gap-1.5 rounded-md border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-xs font-medium text-zinc-300 transition hover:border-zinc-600 disabled:opacity-50"
          >
            {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RotateCcw className="h-3.5 w-3.5" />}
            Re-check all
          </button>
          <button
            onClick={handleAutoRegenerate}
            disabled={autoRegenLoading || !project || !result}
            className="inline-flex items-center gap-1.5 rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-1.5 text-xs font-medium text-amber-300 transition hover:bg-amber-500/20 disabled:opacity-50"
            title="The autonomous loop: check all shots, auto-regenerate those above the drift threshold"
          >
            {autoRegenLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Zap className="h-3.5 w-3.5" />}
            Auto-regenerate drifted
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

// --------------------------------------------------------------------------- //
// Per-shot drift card with working Accept + Re-generate buttons
// --------------------------------------------------------------------------- //

interface ShotDriftCardProps {
  shot: ConsistencyShotReport;
  projectId?: string;
  bibleVersion?: number;
  onRegenerate: (shotId: string, reason: string) => void;
  onAccept: (shotId: string) => void;
  isRegenerating: boolean;
  regenResult?: RegenerationResponse;
  isAccepted: boolean;
}

function ShotDriftCard({
  shot,
  onRegenerate,
  onAccept,
  isRegenerating,
  regenResult,
  isAccepted,
}: ShotDriftCardProps) {
  const overall = shot.overall ?? 0;
  const drift = shot.drift_score ?? (1 - overall);
  const passes = drift <= 0.25;
  const hasData = shot.status === "checked" || shot.status === "cached";
  const hasError = shot.status === "failed" || shot.status === "no_video" || shot.status === "frame_extract_failed" || shot.status === "no_char_ref" || shot.status === "check_failed";

  // The regeneration result's consistency scores (the "after" state)
  const regenConsistency = regenResult?.consistency;
  const regenOverall = regenConsistency?.overall;
  const regenDrift = regenConsistency?.drift_score;
  const regenPasses = regenDrift !== null && regenDrift !== undefined ? regenDrift <= 0.25 : passes;

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

      {/* regeneration before/after evidence */}
      {regenResult && regenOverall !== null && regenOverall !== undefined && (
        <div className="mt-3 rounded-md border border-teal-500/30 bg-teal-500/5 p-2.5">
          <div className="mb-1.5 flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wide text-teal-300">
            <Zap className="h-3 w-3" />
            Regeneration result {regenResult.drift_correction_applied ? "· drift-diagnosis-informed" : "· fresh sample"}
          </div>
          <div className="flex items-center gap-3 text-[11px]">
            <span className="text-zinc-500">
              before: <span className="font-mono text-zinc-400">{overall.toFixed(2)}</span>
              <span className="text-zinc-600"> (drift {drift.toFixed(2)})</span>
            </span>
            <span className="text-zinc-600">→</span>
            <span className="text-zinc-300">
              after: <span className={`font-mono font-bold ${regenPasses ? "text-emerald-400" : "text-amber-400"}`}>{regenOverall.toFixed(2)}</span>
              <span className="text-zinc-500"> (drift {(regenDrift ?? 0).toFixed(2)})</span>
            </span>
          </div>
        </div>
      )}

      {/* Accept + Re-generate buttons — now fully functional */}
      {hasData && (
        <div className="mt-3 flex gap-2">
          <button
            onClick={() => onAccept(shot.shot_id)}
            disabled={isRegenerating || isAccepted}
            className={`inline-flex items-center gap-1 rounded-md border px-2.5 py-1 text-[11px] font-medium transition disabled:opacity-50 ${
              isAccepted
                ? "border-emerald-500/50 bg-emerald-500/20 text-emerald-300"
                : "border-emerald-500/30 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20"
            }`}
          >
            {isAccepted ? (
              <><Check className="h-3 w-3" /> Accepted</>
            ) : (
              <><Check className="h-3 w-3" /> Accept</>
            )}
          </button>
          <button
            onClick={() => onRegenerate(shot.shot_id, `drift ${drift.toFixed(2)} above threshold`)}
            disabled={isRegenerating}
            className="inline-flex items-center gap-1 rounded-md border border-zinc-700 bg-zinc-900 px-2.5 py-1 text-[11px] font-medium text-zinc-300 transition hover:border-teal-500/40 hover:bg-zinc-800 hover:text-teal-300 disabled:opacity-50"
          >
            {isRegenerating ? (
              <><Loader2 className="h-3 w-3 animate-spin" /> Regenerating...</>
            ) : (
              <><RotateCcw className="h-3 w-3" /> Re-generate</>
            )}
          </button>
        </div>
      )}
    </div>
  );
}
