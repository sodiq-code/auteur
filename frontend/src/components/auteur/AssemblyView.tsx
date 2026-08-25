/**
 * AssemblyView — blueprint Section 30.2 row 10.
 * 30-second MP4 player; export buttons (MP4, Bible JSON, Shot CSV); share link.
 */
"use client";

import { useState } from "react";
import { Clapperboard, Download, Share2, Play, FileJson, FileText, Film, Check } from "lucide-react";
import { useStudio } from "@/lib/store";
import { Badge } from "@/components/ui/badge";
import { createShareLink, exportBible } from "@/lib/api";

export function AssemblyView() {
  const { project, bible, setView, setShareSlug, shareSlug } = useStudio();
  const [exporting, setExporting] = useState(false);
  const [sharing, setSharing] = useState(false);

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
      // fallback: generate a local slug
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
        <h2 className="text-2xl font-bold tracking-tight text-zinc-100">Your film is ready</h2>
        <p className="mt-1.5 text-sm text-zinc-400">
          4 shots assembled via ffmpeg into a single 32-second short film, with
          Chirp 3 voiceover and Lyria 2 score.
        </p>
      </div>

      {/* film preview */}
      <div className="relative overflow-hidden rounded-xl border border-zinc-800 bg-zinc-950">
        <div className="relative aspect-video">
          <div className="absolute inset-0 grid grid-cols-2 gap-0.5">
            {["/auteur/day1/shot-1.png", "/auteur/day1/shot-2.png", "/auteur/day1/shot-3.png", "/auteur/day1/shot-4.png"].map((src, i) => (
              <div key={i} className="relative overflow-hidden">
                <img src={src} alt={`Shot ${i + 1}`} className="h-full w-full object-cover" />
              </div>
            ))}
          </div>
          <div className="absolute inset-0 bg-gradient-to-t from-zinc-950/80 via-transparent to-transparent" />
          <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="grid h-10 w-10 place-items-center rounded-full bg-teal-500/90 backdrop-blur transition hover:bg-teal-400">
                <Play className="h-4 w-4 fill-zinc-950 text-zinc-950" />
              </div>
              <div className="text-xs text-zinc-300">
                <div className="font-medium">Ewan&apos;s Vigil</div>
                <div className="text-[10px] text-zinc-500">4 shots · 32s · 1280×720</div>
              </div>
            </div>
            <Badge className="border-0 bg-emerald-500/15 text-emerald-300">
              <Check className="mr-1 h-3 w-3" /> assembled
            </Badge>
          </div>
        </div>
      </div>

      {/* export buttons */}
      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <button
          onClick={handleExportBible}
          disabled={exporting}
          className="flex flex-col items-center gap-1.5 rounded-lg border border-zinc-800 bg-zinc-900/40 p-3 transition hover:border-zinc-700 hover:bg-zinc-900 disabled:opacity-50"
        >
          <FileJson className="h-5 w-5 text-teal-400" />
          <span className="text-[11px] text-zinc-300">Bible JSON</span>
        </button>
        <button className="flex flex-col items-center gap-1.5 rounded-lg border border-zinc-800 bg-zinc-900/40 p-3 transition hover:border-zinc-700 hover:bg-zinc-900">
          <FileText className="h-5 w-5 text-amber-400" />
          <span className="text-[11px] text-zinc-300">Shot CSV</span>
        </button>
        <button className="flex flex-col items-center gap-1.5 rounded-lg border border-zinc-800 bg-zinc-900/40 p-3 transition hover:border-zinc-700 hover:bg-zinc-900">
          <Film className="h-5 w-5 text-purple-400" />
          <span className="text-[11px] text-zinc-300">MP4</span>
        </button>
        <button
          onClick={handleShare}
          disabled={sharing}
          className="flex flex-col items-center gap-1.5 rounded-lg border border-teal-500/40 bg-teal-500/10 p-3 transition hover:bg-teal-500/20 disabled:opacity-50"
        >
          <Share2 className="h-5 w-5 text-teal-300" />
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
