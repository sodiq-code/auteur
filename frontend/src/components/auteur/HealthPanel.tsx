/**
 * HealthPanel — a slide-over panel showing the live backend model status.
 * Pings GET /api/health on the deployed Cloud Run backend and shows every
 * model's status (veo, image, bible, tts, lyria) + the partner integration.
 */
"use client";

import { useEffect, useState } from "react";
import { X, Server, Cpu, Mic, Music, Film, Image as ImageIcon, Search, Check, AlertCircle } from "lucide-react";
import { getHealth, type HealthStatus } from "@/lib/api";

const MODEL_META = {
  veo: { label: "Veo 3.1", icon: Film, color: "text-teal-400" },
  image: { label: "Image", icon: ImageIcon, color: "text-rose-400" },
  bible: { label: "Bible LLM", icon: Cpu, color: "text-amber-400" },
  tts: { label: "Voice", icon: Mic, color: "text-emerald-400" },
  lyria: { label: "Music", icon: Music, color: "text-purple-400" },
} as const;

export function HealthPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    // Fetch-on-open pattern: setState in effect is the standard way to load data
    // when a panel opens. The cascading-render concern doesn't apply here (loading
    // state is only read by this component).
    /* eslint-disable react-hooks/set-state-in-effect */
    setLoading(true);
    setError(null);
    getHealth()
      .then((h) => { if (!cancelled) setHealth(h); })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : "backend unreachable"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    /* eslint-enable react-hooks/set-state-in-effect */
    return () => { cancelled = true; };
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true">
      <div className="absolute inset-0 bg-zinc-950/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative z-10 h-full w-full max-w-md overflow-y-auto border-l border-zinc-800 bg-zinc-950 p-5 shadow-2xl auteur-scroll">
        <div className="mb-5 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Server className="h-4 w-4 text-teal-400" />
            <h2 className="text-sm font-semibold text-zinc-100">Backend status</h2>
          </div>
          <button onClick={onClose} className="grid h-7 w-7 place-items-center rounded-md text-zinc-500 transition hover:bg-zinc-900 hover:text-zinc-200">
            <X className="h-4 w-4" />
          </button>
        </div>

        {loading && (
          <div className="space-y-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-12 animate-pulse rounded-lg bg-zinc-900" />
            ))}
          </div>
        )}

        {error && (
          <div className="flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-xs text-amber-200">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <div className="font-medium">Backend unreachable</div>
              <div className="mt-0.5 text-amber-200/70">{error}</div>
            </div>
          </div>
        )}

        {health && (
          <div className="space-y-4">
            {/* service status */}
            <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-3">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-emerald-400 auteur-pulse" />
                <span className="text-xs font-medium text-emerald-300">
                  {health.status.toUpperCase()} · v{health.version}
                </span>
              </div>
              <div className="mt-1 font-mono text-[10px] text-zinc-500">
                {new Date(health.timestamp_utc).toLocaleString()}
              </div>
            </div>

            {/* partner integration */}
            <div>
              <div className="mb-2 flex items-center gap-2 text-[10px] font-medium uppercase tracking-wide text-zinc-500">
                <Search className="h-3 w-3" />
                Partner integration
              </div>
              <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-zinc-200">Parallel Search</span>
                  <span className={`flex items-center gap-1 text-[10px] ${health.partner_status.parallel_search.configured ? "text-emerald-400" : "text-amber-400"}`}>
                    {health.partner_status.parallel_search.configured ? <Check className="h-3 w-3" /> : <AlertCircle className="h-3 w-3" />}
                    {health.partner_status.parallel_search.configured ? "configured" : "not set"}
                  </span>
                </div>
                <div className="mt-1.5 space-y-0.5 text-[10px] text-zinc-500">
                  <div>endpoint: <code className="font-mono text-teal-400/70">{health.partner_status.parallel_search.endpoint}</code></div>
                  <div>auth: <code className="font-mono text-teal-400/70">{health.partner_status.parallel_search.auth}</code></div>
                  <div>track: <span className="text-zinc-400">{health.partner_status.parallel_search.track}</span></div>
                </div>
              </div>
            </div>

            {/* model status */}
            <div>
              <div className="mb-2 flex items-center gap-2 text-[10px] font-medium uppercase tracking-wide text-zinc-500">
                <Cpu className="h-3 w-3" />
                Model status ({Object.keys(health.model_status).length} models)
              </div>
              <div className="space-y-1.5">
                {Object.entries(health.model_status).map(([key, m]) => {
                  const meta = MODEL_META[key as keyof typeof MODEL_META] || { label: key, icon: Cpu, color: "text-zinc-400" };
                  const Icon = meta.icon;
                  return (
                    <div key={key} className="flex items-center gap-3 rounded-lg border border-zinc-800 bg-zinc-900/40 px-3 py-2">
                      <Icon className={`h-4 w-4 ${meta.color}`} />
                      <div className="min-w-0 flex-1">
                        <div className="text-xs font-medium text-zinc-200">{meta.label}</div>
                        <div className="truncate font-mono text-[10px] text-teal-400/70">{m.model}</div>
                      </div>
                      <div className="text-right">
                        <div className="flex items-center gap-1 text-[10px] text-zinc-500">
                          {m.configured ? <Check className="h-3 w-3 text-emerald-400" /> : <AlertCircle className="h-3 w-3 text-amber-400" />}
                          {m.region}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-3 text-[10px] text-zinc-500">
              <div className="font-mono text-teal-400/70">https://auteur-dev-jbkbgthudq-uc.a.run.app</div>
              <div className="mt-1">Cloud Run · us-central1 · 14 endpoints live</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
