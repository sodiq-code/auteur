/**
 * ConsistencyView — blueprint Section 30.2 row 9.
 * Bar chart of drift per shot; per-attribute breakdown; accept/reject.
 */
"use client";

import { Gauge, ChevronRight, Check, RotateCcw } from "lucide-react";
import { useStudio } from "@/lib/store";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";

const SHOT_SCORES = [
  { id: 1, label: "Lamp Room", face: 0.95, age: 0.95, beard: 0.95, wardrobe: 0.95, overall: 0.95 },
  { id: 2, label: "Rocks", face: 0.80, age: 0.90, beard: 0.90, wardrobe: 0.90, overall: 0.85 },
  { id: 3, label: "Interior", face: 0.95, age: 0.95, beard: 0.95, wardrobe: 0.95, overall: 0.95 },
  { id: 4, label: "Exterior", face: 0.95, age: 0.95, beard: 0.95, wardrobe: 0.95, overall: 0.95 },
];

const ATTRS = ["face", "age", "beard", "wardrobe"] as const;

export function ConsistencyView() {
  const setView = useStudio((s) => s.setView);
  const meanOverall = SHOT_SCORES.reduce((a, s) => a + s.overall, 0) / SHOT_SCORES.length;

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

      {/* mean overall */}
      <div className="mb-6 grid grid-cols-3 gap-3">
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
          <div className="text-[10px] uppercase tracking-wide text-zinc-500">Mean consistency</div>
          <div className="mt-1 font-mono text-2xl font-bold text-emerald-400">{meanOverall.toFixed(3)}</div>
        </div>
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
          <div className="text-[10px] uppercase tracking-wide text-zinc-500">Drift threshold</div>
          <div className="mt-1 font-mono text-2xl font-bold text-zinc-100">0.25</div>
        </div>
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
          <div className="text-[10px] uppercase tracking-wide text-zinc-500">Verdict</div>
          <div className="mt-1 font-mono text-2xl font-bold text-emerald-400">GO</div>
        </div>
      </div>

      {/* per-shot bars */}
      <div className="space-y-4">
        {SHOT_SCORES.map((s) => {
          const drift = 1 - s.overall;
          const passes = drift <= 0.25;
          return (
            <div key={s.id} className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="grid h-6 w-6 place-items-center rounded bg-teal-500/15 font-mono text-xs font-bold text-teal-300">
                    {s.id}
                  </span>
                  <span className="text-sm font-medium text-zinc-200">{s.label}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`font-mono text-sm font-bold ${passes ? "text-emerald-400" : "text-amber-400"}`}>
                    {s.overall.toFixed(2)}
                  </span>
                  <Badge className={`border-0 ${passes ? "bg-emerald-500/15 text-emerald-300" : "bg-amber-500/15 text-amber-300"}`}>
                    {passes ? "accept" : "re-generate"}
                  </Badge>
                </div>
              </div>

              <div className="mb-2">
                <div className="mb-1 flex justify-between text-[10px] font-mono text-zinc-500">
                  <span>overall consistency</span>
                  <span>drift {drift.toFixed(3)} · {passes ? "PASS" : "REVIEW"}</span>
                </div>
                <Progress value={s.overall * 100} className="h-2 bg-zinc-800 [&>div]:bg-gradient-to-r [&>div]:from-teal-500 [&>div]:to-emerald-400" />
              </div>

              <div className="grid grid-cols-4 gap-2">
                {ATTRS.map((attr) => {
                  const val = s[attr];
                  return (
                    <div key={attr} className="rounded bg-zinc-950/50 px-2 py-1.5 text-center">
                      <div className="text-[9px] uppercase text-zinc-500">{attr}</div>
                      <div className={`font-mono text-xs font-bold ${val >= 0.9 ? "text-emerald-400" : val >= 0.75 ? "text-amber-400" : "text-rose-400"}`}>
                        {val.toFixed(2)}
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="mt-3 flex gap-2">
                <button className="inline-flex items-center gap-1 rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-[11px] font-medium text-emerald-300 transition hover:bg-emerald-500/20">
                  <Check className="h-3 w-3" /> Accept
                </button>
                <button className="inline-flex items-center gap-1 rounded-md border border-zinc-700 bg-zinc-900 px-2.5 py-1 text-[11px] font-medium text-zinc-400 transition hover:border-zinc-600 hover:text-zinc-200">
                  <RotateCcw className="h-3 w-3" /> Re-generate
                </button>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-6 flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-900/40 px-4 py-3">
        <span className="text-xs text-zinc-400">All shots pass the drift threshold</span>
        <button
          onClick={() => setView("assembly")}
          className="inline-flex items-center gap-1.5 rounded-md bg-teal-500 px-3 py-1.5 text-xs font-semibold text-zinc-950 transition hover:bg-teal-400"
        >
          Assemble film
          <ChevronRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}
