/**
 * AssemblyView — blueprint Section 30.2 row 10.
 * Final film preview + export buttons (MP4, Bible JSON, Shot CSV); share link.
 *
 * Calls POST /api/projects/{id}/assemble to run ffmpeg concatenation on the
 * backend, then streams the assembled MP4 via GET /api/projects/{id}/film.
 */
"use client";

import { useState } from "react";
import { Clapperboard, Download, Share2, Play, FileJson, FileText, Film, Check, Loader2 } from "lucide-react";
import { useStudio } from "@/lib/store";
import { Badge } from "@/components/ui/badge";
import { assembleFilm, createShareLink, exportBible } from "@/lib/api";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "";

export function AssemblyView() {
  const { project, bible, setView, setShareSlug } = useStudio();
  const [assembling, setAssembling] = useState(false);
  const [filmUrl, setFilmUrl] = useState<string | null>(null);
  const [filmInfo, setFilmInfo] = useState<{ duration?: number; size?: number; clips?: number } | null>(null);
  const [exporting, setExporting] = useState(false);
  const [sharing, setSharing] = useState(false);

  async function handleAssemble() {
    if (!project) return;
    setAssembling(true);
    try {
      const result = await assembleFilm(project.id);
      if (result.status === "ok") {
        setFilmUrl(`${API_BASE}/api/projects/${project.id}/film`);
        setFilmInfo({
          duration: result.duration_seconds,
          size: result.size_bytes,
          clips: result.clip_count,
        });
      }
    } catch (e) {
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

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="mb-6">
        <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-zinc-700 bg-zinc-900/60 px-3 py-1 text-xs text-zinc-400">
          <Clapperboard className="h-3.5 w-3.5 text-teal-400" />
          Step 8 — Assembly
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-zinc-100">
          {filmUrl ? "Your film is ready" : "Assemble your film"}
        </h2>
        <p className="mt-1.5 text-sm text-zinc-400">
          {filmUrl
            ? "ffmpeg concatenated the generated Veo clips into a single MP4."
            : "Concatenate the generated Veo clips into a single short film via ffmpeg."}
        </p>
      </div>

      {/* film preview */}
      <div className="relative overflow-hidden rounded-xl border border-zinc-800 bg-zinc-950">
        <div className="relative aspect-video">
          {filmUrl ? (
            <video
              src={filmUrl}
              controls
              className="h-full w-full"
              autoPlay
              loop
              muted
            />
          ) : (
            <div className="grid h-full grid-cols-2 gap-0.5">
              {["/auteur/day1/shot-1.png", "/auteur/day1/shot-2.png", "/auteur/day1/shot-3.png", "/auteur/day1/shot-4.png"].map((src, i) => (
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
                  {assembling ? "Assembling..." : "Assemble film"}
                </button>
              </div>
            </div>
          )}
          {filmUrl && (
            <div className="absolute bottom-3 left-3 flex items-center gap-2">
              <Badge className="border-0 bg-emerald-500/15 text-emerald-300">
                <Check className="mr-1 h-3 w-3" /> assembled
              </Badge>
              {filmInfo?.duration && (
                <span className="rounded bg-zinc-950/80 px-2 py-0.5 font-mono text-[10px] text-zinc-300 backdrop-blur">
                  {filmInfo.duration}s · {filmInfo.clips} clips
                </span>
              )}
            </div>
          )}
        </div>
      </div>

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
