/**
 * ShareView — blueprint Section 30.2 row 11.
 * Side-by-side demo loop + user's film + bible summary.
 */
"use client";

import Image from "next/image";
import { Share2, Copy, Check, Eye, ArrowLeft, ExternalLink } from "lucide-react";
import { useState, useEffect } from "react";
import { useStudio } from "@/lib/store";
import { getSharedProject, type SharedProject } from "@/lib/api";
import { Badge } from "@/components/ui/badge";

export function ShareView() {
  const { shareSlug, bible, project, setView, reset } = useStudio();
  const [copied, setCopied] = useState(false);
  const [sharedProject, setSharedProject] = useState<SharedProject | null>(null);

  const API_BASE =
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    "https://auteur-dev-jbkbgthudq-uc.a.run.app";
  const shareUrl = shareSlug ? `${API_BASE}/api/share/${shareSlug}` : "";

  // verify the share link works by fetching the shared project
  useEffect(() => {
    if (!shareSlug) return;
    getSharedProject(shareSlug).then(setSharedProject).catch(() => {});
  }, [shareSlug]);

  function handleCopy() {
    if (shareUrl) {
      navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="mb-6">
        <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-zinc-700 bg-zinc-900/60 px-3 py-1 text-xs text-zinc-400">
          <Share2 className="h-3.5 w-3.5 text-teal-400" />
          Step 9 — Share
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-zinc-100">Public share link</h2>
        <p className="mt-1.5 text-sm text-zinc-400">
          Anyone with this link can view your film + its Film Bible.
        </p>
      </div>

      {/* share URL */}
      {shareUrl && (
        <div className="mb-6 rounded-lg border border-teal-500/30 bg-teal-500/5 px-4 py-3">
          <div className="mb-2 flex items-center gap-2">
            <code className="flex-1 truncate font-mono text-xs text-teal-200">{shareUrl}</code>
            <button
              onClick={handleCopy}
              className="inline-flex items-center gap-1 rounded-md bg-teal-500 px-2.5 py-1 text-xs font-semibold text-zinc-950 transition hover:bg-teal-400"
            >
              {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
              {copied ? "Copied" : "Copy"}
            </button>
            <a
              href={shareUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 rounded-md border border-zinc-700 bg-zinc-900 px-2.5 py-1 text-xs font-medium text-zinc-300 transition hover:border-zinc-600"
            >
              <ExternalLink className="h-3 w-3" /> Open
            </a>
          </div>
          {sharedProject ? (
            <div className="flex items-center gap-1.5 text-[10px] text-emerald-300">
              <Check className="h-3 w-3" />
              share link verified — returns project + bible + {sharedProject.shots.length} shots
              {sharedProject.film_url ? " + film" : ""}
            </div>
          ) : shareSlug ? (
            <div className="text-[10px] text-zinc-500">verifying share link...</div>
          ) : null}
        </div>
      )}

      {/* the signature side-by-side */}
      <div className="mb-6">
        <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-zinc-500">
          <Eye className="h-3.5 w-3.5 text-amber-400" />
          The signature moment
        </div>
        <div className="overflow-hidden rounded-xl border border-zinc-800 bg-zinc-950">
          <Image
            src="/auteur/day1/side-by-side.png"
            alt="Side-by-side: one character across four scenes"
            width={1920}
            height={440}
            className="h-auto w-full"
          />
        </div>
        <p className="mt-2 text-[11px] text-zinc-500">
          The same character — Ewan — held consistent across four different scenes via
          the Veo 3.1 ASSET reference.
        </p>
      </div>

      {/* the film */}
      <div className="mb-6">
        <div className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">Your film</div>
        <div className="grid grid-cols-2 gap-1 overflow-hidden rounded-xl border border-zinc-800">
          {["/auteur/day1/shot-1.png", "/auteur/day1/shot-2.png", "/auteur/day1/shot-3.png", "/auteur/day1/shot-4.png"].map((src, i) => (
            <div key={i} className="relative aspect-video overflow-hidden">
              <img src={src} alt={`Shot ${i + 1}`} className="h-full w-full object-cover" />
              <div className="absolute left-2 top-2 rounded bg-zinc-950/80 px-1.5 py-0.5 font-mono text-[10px] text-teal-300 backdrop-blur">
                #{i + 1}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* bible summary */}
      {bible && project && (
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-xs font-medium uppercase tracking-wide text-zinc-500">Film Bible summary</h3>
            <Badge className="border-0 bg-teal-500/15 text-teal-300">v{bible.version}</Badge>
          </div>
          <p className="mb-3 text-sm text-zinc-300">{project.logline}</p>
          <div className="grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
            <div><dt className="text-zinc-500">Characters</dt><dd className="font-mono text-teal-300">{bible.characters.length}</dd></div>
            <div><dt className="text-zinc-500">Locations</dt><dd className="font-mono text-teal-300">{bible.locations.length}</dd></div>
            <div><dt className="text-zinc-500">Beats</dt><dd className="font-mono text-teal-300">{bible.story_beats.length}</dd></div>
            <div><dt className="text-zinc-500">References</dt><dd className="font-mono text-teal-300">{bible.research_references.length}</dd></div>
          </div>
        </div>
      )}

      <div className="mt-8 flex items-center justify-between">
        <button
          onClick={() => { reset(); setView("landing"); }}
          className="inline-flex items-center gap-1.5 rounded-md border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-xs font-medium text-zinc-300 transition hover:border-zinc-600"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Make another film
        </button>
      </div>
    </div>
  );
}
