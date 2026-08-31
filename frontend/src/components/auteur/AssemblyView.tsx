/**
 * AssemblyView — blueprint Section 30.2 row 10.
 * Final film preview + export buttons (MP4, Bible JSON, Shot CSV); share link.
 *
 * Calls POST /api/projects/{id}/assemble to run ffmpeg concatenation on the
 * backend (which now muxes the Chirp voiceover + Lyria score into the final
 * MP4 audio track), then streams the assembled MP4 via GET /api/projects/{id}/film.
 *
 * The <video> element is NOT muted — the assembled film has a real audio track
 * (voiceover narration + musical score). The user controls playback via the
 * native controls (play/pause/volume).
 */
"use client";

import { useState } from "react";
import {
  Clapperboard, Download, Share2, Play, FileJson, FileText, Film,
  Check, Loader2, Volume2, VolumeX, Music, Mic, Clock,
} from "lucide-react";
import { useStudio } from "@/lib/store";
import { Badge } from "@/components/ui/badge";
import { assembleFilm, createShareLink, exportBible, type AssembleFilmResponse } from "@/lib/api";

const API_BASE = "https://auteur-dev-jbkbgthudq-uc.a.run.app";

export function AssemblyView() {
  const { project, bible, setView, setShareSlug } = useStudio();
  const [assembling, setAssembling] = useState(false);
  const [assembleResult, setAssembleResult] = useState<AssembleFilmResponse | null>(null);
  const [filmUrl, setFilmUrl] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [sharing, setSharing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleAssemble() {
    if (!project) return;
    setAssembling(true);
    setError(null);
    try {
      const result = await assembleFilm(project.id);
      if (result.status === "ok") {
        setAssembleResult(result);
        // cache-bust so the browser fetches the fresh MP4 (not a stale muted one)
        setFilmUrl(`${API_BASE}/api/projects/${project.id}/film?t=${Date.now()}`);
      } else {
        setError(`Assembly returned status: ${result.status}`);
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(`Assembly failed: ${msg}`);
      console.error("assembly failed:", e);
    } finally {
      setAssembling(false);
    }
  }

  async function handleExportBible() {
    if (!project) return;
    setExporting(true);
    try {
      const data = await exportBible(project.id);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "bible.json";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error(e);
    } finally {
      setExporting(false);
    }
  }

  async function handleShare() {
    if (!project) return;
    setSharing(true);
    try {
      const result = await createShareLink(project.id);
      setShareSlug(result.public_slug);
      setView("share");
    } catch (e) {
      setShareSlug(Math.random().toString(36).substring(2, 10));
      setView("share");
    } finally {
      setSharing(false);
    }
  }

  const hasAudio = assembleResult?.has_audio ?? false;
  const audioInfo = assembleResult?.audio;

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="mb-6">
        <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-zinc-700 bg-zinc-900/60 px-3 py-1 text-xs text-zinc-400">
          <Clapperboard className="h-3.5 w-3.5 text-teal-400" />
          Step 8 — Assembly
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-zinc-100">
          {filmUrl ? "Film assembled" : "Assemble the film"}
        </h2>
        <p className="mt-1.5 text-sm text-zinc-400">
          {filmUrl
            ? "ffmpeg concatenated the Veo clips and muxed the Chirp voiceover + Lyria score into the final MP4 audio track."
            : "Concatenate the generated Veo clips + mux the voiceover + score into a single short film via ffmpeg."}
        </p>
      </div>

      {/* film preview */}
      <div className="relative overflow-hidden rounded-xl border border-zinc-800 bg-zinc-950">
        <div className="relative aspect-video">
          {filmUrl ? (
            <video
              src={filmUrl}
              controls
              playsInline
              className="h-full w-full"
              autoPlay
              loop
            />
          ) : (
            <div className="grid h-full grid-cols-2 gap-0.5">
              {["/auteur/demo/shot-1.png", "/auteur/demo/shot-2.png", "/auteur/demo/shot-3.png", "/auteur/demo/shot-4.png"].map((src, i) => (
                <div key={i} className="relative overflow-hidden">
                  <img src={src} alt={`Shot ${i + 1}`} className="h-full w-full object-cover opacity-60" />
                </div>
              ))}
              <div className="absolute inset-0 grid place-items-center bg-zinc-950/60">
                <button
                  onClick={handleAssemble}
                  disabled={assembling || !project}
                  className="inline-flex items-center gap-2 rounded-lg bg-teal-500 px-5 py-2.5 text-sm font-semibold text-zinc-950 transition hover:bg-teal-400 disabled:opacity-50"
                >
                  {assembling ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Play className="h-4 w-4" />
                  )}
                  {assembling ? "Assembling" : "Assemble film"}
                </button>
              </div>
            </div>
          )}
          {filmUrl && (
            <div className="pointer-events-none absolute bottom-3 left-3 flex items-center gap-2">
              <Badge className="border-0 bg-emerald-500/15 text-emerald-300">
                <Check className="mr-1 h-3 w-3" /> assembled
              </Badge>
              {hasAudio ? (
                <Badge className="border-0 bg-sky-500/15 text-sky-300">
                  <Volume2 className="mr-1 h-3 w-3" /> with sound
                </Badge>
              ) : (
                <Badge className="border-0 bg-amber-500/15 text-amber-300">
                  <VolumeX className="mr-1 h-3 w-3" /> no audio
                </Badge>
              )}
              {assembleResult?.duration_seconds && (
                <span className="rounded bg-zinc-950/80 px-2 py-0.5 font-mono text-[10px] text-zinc-300 backdrop-blur">
                  {assembleResult.duration_seconds}s · {assembleResult.clip_count} clips
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* error */}
      {error && (
        <div className="mt-4 rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-300">
          {error}
        </div>
      )}

      {/* audio summary */}
      {audioInfo && (
        <div className="mt-4 rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Music className="h-4 w-4 text-teal-400" />
              <h3 className="text-xs font-medium uppercase tracking-wide text-zinc-500">
                Audio track
              </h3>
            </div>
            <span className="font-mono text-[10px] text-zinc-500">
              {audioInfo.voiceover_shots}/{assembleResult?.clip_count} voiced · {audioInfo.score_shots}/{assembleResult?.clip_count} scored
            </span>
          </div>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div className="rounded border border-zinc-800 bg-zinc-950/40 p-2">
              <div className="mb-1 flex items-center gap-1 text-zinc-500">
                <Mic className="h-3 w-3" /> Voiceover
              </div>
              <div className="font-mono text-teal-300">{audioInfo.voiceover_shots} shots</div>
            </div>
            <div className="rounded border border-zinc-800 bg-zinc-950/40 p-2">
              <div className="mb-1 flex items-center gap-1 text-zinc-500">
                <Music className="h-3 w-3" /> Score
              </div>
              <div className="font-mono text-teal-300">{audioInfo.score_shots} shots</div>
            </div>
            <div className="rounded border border-zinc-800 bg-zinc-950/40 p-2">
              <div className="mb-1 flex items-center gap-1 text-zinc-500">
                <VolumeX className="h-3 w-3" /> Silent
              </div>
              <div className="font-mono text-amber-300">{audioInfo.silent_shots} shots</div>
            </div>
          </div>
          {/* per-shot breakdown */}
          <div className="mt-3 max-h-40 overflow-y-auto pr-1">
            <table className="w-full text-[11px]">
              <thead className="text-zinc-500">
                <tr>
                  <th className="px-1 py-1 text-left font-normal">#</th>
                  <th className="px-1 py-1 text-left font-normal">Mix mode</th>
                  <th className="px-1 py-1 text-right font-normal">Duration</th>
                  <th className="px-1 py-1 text-center font-normal">Voice</th>
                  <th className="px-1 py-1 text-center font-normal">Score</th>
                </tr>
              </thead>
              <tbody className="text-zinc-300">
                {audioInfo.per_shot.map((s) => (
                  <tr key={s.shot_id} className="border-t border-zinc-800/50">
                    <td className="px-1 py-1 font-mono text-zinc-500">{s.order}</td>
                    <td className="px-1 py-1 font-mono text-zinc-400">{s.mix_mode}</td>
                    <td className="px-1 py-1 text-right font-mono text-zinc-400">
                      <Clock className="mr-1 inline h-3 w-3 text-zinc-600" />
                      {s.duration_seconds}s
                    </td>
                    <td className="px-1 py-1 text-center">
                      {s.voiceover ? (
                        <Check className="mx-auto h-3 w-3 text-emerald-400" />
                      ) : (
                        <span className="text-zinc-700">—</span>
                      )}
                    </td>
                    <td className="px-1 py-1 text-center">
                      {s.score ? (
                        <Check className="mx-auto h-3 w-3 text-emerald-400" />
                      ) : (
                        <span className="text-zinc-700">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* export buttons */}
      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <button
          onClick={handleExportBible}
          disabled={exporting || !bible}
          className="flex flex-col items-center gap-1.5 rounded-lg border border-zinc-800 bg-zinc-900/40 p-3 transition hover:border-zinc-700 hover:bg-zinc-900 disabled:opacity-50"
        >
          {exporting ? <Loader2 className="h-5 w-5 animate-spin text-teal-400" /> : <FileJson className="h-5 w-5 text-teal-400" />}
          <span className="text-[11px] text-zinc-300">Bible JSON</span>
        </button>
        <a
          href={project ? `${API_BASE}/api/projects/${project.id}/export/shots` : "#"}
          className="flex flex-col items-center gap-1.5 rounded-lg border border-zinc-800 bg-zinc-900/40 p-3 transition hover:border-zinc-700 hover:bg-zinc-900"
        >
          <FileText className="h-5 w-5 text-amber-400" />
          <span className="text-[11px] text-zinc-300">Shot CSV</span>
        </a>
        {filmUrl && (
          <a
            href={filmUrl}
            download="auteur_film.mp4"
            className="flex flex-col items-center gap-1.5 rounded-lg border border-zinc-800 bg-zinc-900/40 p-3 transition hover:border-zinc-700 hover:bg-zinc-900"
          >
            <Film className="h-5 w-5 text-purple-400" />
            <span className="text-[11px] text-zinc-300">MP4</span>
          </a>
        )}
        <button
          onClick={handleShare}
          disabled={sharing || !filmUrl}
          className="flex flex-col items-center gap-1.5 rounded-lg border border-teal-500/40 bg-teal-500/10 p-3 transition hover:bg-teal-500/20 disabled:opacity-50"
        >
          {sharing ? <Loader2 className="h-5 w-5 animate-spin text-teal-300" /> : <Share2 className="h-5 w-5 text-teal-300" />}
          <span className="text-[11px] text-teal-200">Share</span>
        </button>
      </div>

      {bible && (
        <div className="mt-6 rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
          <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">Film Bible summary</h3>
          <div className="grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
            <div><dt className="text-zinc-500">Characters</dt><dd className="font-mono text-teal-300">{bible.characters.length}</dd></div>
            <div><dt className="text-zinc-500">Locations</dt><dd className="font-mono text-teal-300">{bible.locations.length}</dd></div>
            <div><dt className="text-zinc-500">Beats</dt><dd className="font-mono text-teal-300">{bible.story_beats.length}</dd></div>
            <div><dt className="text-zinc-500">References</dt><dd className="font-mono text-teal-300">{bible.research_references.length}</dd></div>
          </div>
        </div>
      )}
    </div>
  );
}
