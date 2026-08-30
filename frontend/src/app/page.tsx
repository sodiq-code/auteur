"use client";

import { useEffect, useState } from "react";
import {
  Film, Home, Edit3, Search, BookOpen, ListOrdered,
  Loader2, Grid3x3, Gauge, Clapperboard, Share2,
  Github, ExternalLink, AlertCircle, Server, Zap,
} from "lucide-react";
import Link from "next/link";
import { useStudio, type StudioView } from "@/lib/store";
import { getHealth, type HealthStatus } from "@/lib/api";
import { useKeyboardShortcuts } from "@/lib/use-keyboard";
import type { Reference } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { LandingView } from "@/components/auteur/LandingView";
import { LoglineView } from "@/components/auteur/LoglineView";
import { ResearchView } from "@/components/auteur/ResearchView";
import { BibleView } from "@/components/auteur/BibleView";
import { ShotListView } from "@/components/auteur/ShotListView";
import { RenderQueueView } from "@/components/auteur/RenderQueueView";
import { ShotGridView } from "@/components/auteur/ShotGridView";
import { ConsistencyView } from "@/components/auteur/ConsistencyView";
import { AssemblyView } from "@/components/auteur/AssemblyView";
import { ShareView } from "@/components/auteur/ShareView";
import { HealthPanel } from "@/components/auteur/HealthPanel";
import { ShotDetailDialog } from "@/components/auteur/ShotDetailDialog";
import { KeyboardShortcutsHelp } from "@/components/auteur/KeyboardShortcutsHelp";

const NAV_ITEMS: { view: StudioView; label: string; icon: typeof Film; step?: number }[] = [
  { view: "landing", label: "Home", icon: Home },
  { view: "logline", label: "Logline", icon: Edit3, step: 1 },
  { view: "research", label: "Research", icon: Search, step: 2 },
  { view: "bible", label: "Bible", icon: BookOpen, step: 3 },
  { view: "shots", label: "Shots", icon: ListOrdered, step: 4 },
  { view: "render", label: "Render", icon: Loader2, step: 5 },
  { view: "grid", label: "Grid", icon: Grid3x3, step: 6 },
  { view: "consistency", label: "Drift", icon: Gauge, step: 7 },
  { view: "assembly", label: "Assembly", icon: Clapperboard, step: 8 },
  { view: "share", label: "Share", icon: Share2, step: 9 },
];

export default function Page() {
  const { view, setView, project, error, setError, setBible, setResearch, setResearchProgress } = useStudio();
  const [health, setHealthState] = useState<HealthStatus | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [healthPanelOpen, setHealthPanelOpen] = useState(false);
  const [shortcutsHelpOpen, setShortcutsHelpOpen] = useState(false);
  const [detailShot, setDetailShot] = useState<{ id: number; label: string; scene: string; frame: string; scores: { face: number; age: number; beard: number; wardrobe: number; overall: number }; notes: string } | null>(null);

  useEffect(() => {
    getHealth()
      .then(setHealthState)
      .catch((e) => setError(e instanceof Error ? e.message : "backend unreachable"));
  }, [setError]);

  // keyboard shortcuts
  useKeyboardShortcuts({
    onToggleHealth: () => setHealthPanelOpen((v) => !v),
    onToggleShortcutsHelp: () => setShortcutsHelpOpen((v) => !v),
    onLoadDemo: () => {
      // load the canonical lighthouse-keeper demo into the store
      const demoRefs: Reference[] = [
        { id: "r1", url: "https://en.wikipedia.org/wiki/Fresnel_lens", title: "Fresnel lens — Wikipedia", snippet: "The Fresnel lens used in lighthouses was invented by Augustin-Jean Fresnel.", modality: "text" },
        { id: "r2", url: "https://www.nps.gov/articles/fresnel-lens.htm", title: "Fresnel Lens — NPS", snippet: "Lighthouse keepers maintained the brass clockwork mechanism.", modality: "text" },
        { id: "r3", url: "https://en.wikipedia.org/wiki/Lighthouse_keeper", title: "Lighthouse keeper — Wikipedia", snippet: "Keepers wore heavy oilskin storm coats against the North Sea spray.", modality: "text" },
      ];
      setResearch(demoRefs);
      setResearchProgress("done");
      setBible({
        version: 1,
        created_at: new Date().toISOString(),
        logline: "An 1892 Scottish lighthouse keeper discovers a message in a bottle that changes his life.",
        characters: [{ id: "c1", name: "Ewan MacAskill", age: 52, description: "A weathered, solitary Scottish lighthouse keeper.", voice_profile: "Gruff, sparse, Scottish brogue.", wardrobe: "Hand-waxed oilskin storm coat over a heavy-knit wool sweater.", reference_image_url: "/auteur/day1/character-reference.png", references: [demoRefs[2]] }],
        locations: [{ id: "l1", name: "Skerryvore Lighthouse", description: "A remote stone lighthouse battered by the North Sea.", era: "1892", references: [demoRefs[0]] }],
        wardrobes: [{ id: "w1", character_id: "c1", garment: "Oilskin storm coat", fabric: "Waxed cotton", color: "Dark oil-black" }],
        voice_profiles: [{ id: "v1", character_id: "c1", voice_model: "gemini-3.1-flash-tts-preview", voice_name: "Charon", description: "Weary, deep, Scottish brogue" }],
        score_motifs: [{ id: "m1", name: "The Keeper's Vigil", prompt: "a slow mournful solo fiddle, scottish air, melancholic, distant waves", instrument: "Solo fiddle", mood: "Melancholic, isolated" }],
        style_anchors: [{ id: "s1", color_grade: "Desaturated cold blues + warm amber lamp glow", aspect_ratio: "16:9", photographic_aesthetic: "Shallow depth of field, 50mm", mood: "Atmospheric, isolating" }],
        story_beats: [
          { id: "b1", order: 1, description: "Ewan walks the lamp room at dusk, polishing the lens." },
          { id: "b2", order: 2, description: "He discovers a bottle on the rocks below at dawn." },
          { id: "b3", order: 3, description: "He reads the message by candlelight." },
          { id: "b4", order: 4, description: "He looks out to sea, transformed." },
        ],
        research_references: demoRefs,
      });
      setView("bible");
    },
  });

  return (
    <div className="auteur-grain flex min-h-screen flex-col bg-zinc-950 text-zinc-100">
      <header className="sticky top-0 z-40 border-b border-zinc-800/80 bg-zinc-950/85 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-2.5 sm:px-6">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="grid h-8 w-8 place-items-center rounded-md border border-zinc-700 bg-zinc-900 text-zinc-400 transition hover:text-zinc-200 sm:hidden"
              aria-label="Toggle nav"
            >
              <Film className="h-4 w-4" />
            </button>
            <button onClick={() => setView("landing")} className="flex items-center gap-2.5">
              <div className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-teal-500 to-amber-500 text-zinc-950 shadow-lg shadow-teal-500/20">
                <Film className="h-4 w-4" />
              </div>
              <div className="leading-tight">
                <div className="font-semibold tracking-tight">Auteur</div>
                <div className="text-[10px] text-zinc-500">The Film Bible Agent</div>
              </div>
            </button>
          </div>

          <div className="flex items-center gap-2">
            {health && (
              <button
                onClick={() => setHealthPanelOpen(true)}
                className="hidden items-center gap-1.5 rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-300 transition hover:bg-emerald-500/20 sm:flex"
                title="Backend status (press ?)"
              >
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 auteur-pulse" />
                backend live
              </button>
            )}
            <button
              onClick={() => setHealthPanelOpen(true)}
              className="grid h-8 w-8 place-items-center rounded-md border border-zinc-700 bg-zinc-900 text-zinc-400 transition hover:text-zinc-200 sm:hidden"
              aria-label="Backend status"
            >
              <Server className="h-4 w-4" />
            </button>
            <button
              onClick={() => {
                // trigger the demo load (same as pressing 'd')
                const e = new KeyboardEvent('keydown', { key: 'd' });
                window.dispatchEvent(e);
              }}
              className="hidden items-center gap-1.5 rounded-md border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-xs font-medium text-amber-300 transition hover:bg-amber-500/20 md:flex"
              title="Load the sample production (press d)"
            >
              <Zap className="h-3 w-3" /> sample
            </button>
            {project && (
              <Badge variant="outline" className="hidden border-zinc-700 text-zinc-400 md:inline-flex">
                <span className="max-w-[160px] truncate font-mono text-[10px]">{project.id}</span>
              </Badge>
            )}
            <Link
              href="https://github.com/sodiq-code/auteur"
              target="_blank"
              className="grid h-8 w-8 place-items-center rounded-md border border-zinc-700 bg-zinc-900 text-zinc-400 transition hover:text-zinc-200"
              aria-label="GitHub repo"
            >
              <Github className="h-4 w-4" />
            </Link>
            <button
              onClick={() => setShortcutsHelpOpen(true)}
              className="hidden h-8 items-center gap-1.5 rounded-md border border-zinc-700 bg-zinc-900 px-2.5 text-xs font-medium text-zinc-400 transition hover:text-zinc-200 sm:flex"
              title="Keyboard shortcuts (⌘K)"
            >
              <span className="auteur-kbd">⌘</span>
              <span className="auteur-kbd">K</span>
            </button>
            <Link
              href="https://auteur-dev-jbkbgthudq-uc.a.run.app/docs"
              target="_blank"
              className="hidden h-8 items-center gap-1.5 rounded-md border border-zinc-700 bg-zinc-900 px-2.5 text-xs font-medium text-zinc-400 transition hover:text-zinc-200 sm:flex"
            >
              <ExternalLink className="h-3 w-3" /> API
            </Link>
          </div>
        </div>
      </header>

      <div className="mx-auto flex w-full max-w-7xl flex-1">
        <nav
          className={`${
            sidebarOpen ? "block" : "hidden"
          } absolute z-30 mt-[49px] h-[calc(100vh-49px)] w-56 border-r border-zinc-800 bg-zinc-950/95 backdrop-blur sm:sticky sm:top-[49px] sm:mt-0 sm:block sm:h-[calc(100vh-49px)] sm:w-48`}
        >
          <div className="flex h-full flex-col gap-0.5 overflow-y-auto p-2 auteur-scroll">
            {NAV_ITEMS.map((item) => {
              const active = view === item.view;
              const reached = project !== null || item.view === "landing" || item.view === "logline";
              return (
                <button
                  key={item.view}
                  onClick={() => {
                    if (reached) {
                      setView(item.view);
                      setSidebarOpen(false);
                    }
                  }}
                  disabled={!reached}
                  className={`flex items-center gap-2.5 rounded-md px-2.5 py-2 text-xs font-medium transition ${
                    active
                      ? "bg-teal-500/15 text-teal-300"
                      : reached
                        ? "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200"
                        : "cursor-not-allowed text-zinc-700"
                  }`}
                >
                  <item.icon className={`h-3.5 w-3.5 ${active ? "" : reached ? "text-zinc-500" : "text-zinc-700"}`} />
                  <span className="flex-1 text-left">{item.label}</span>
                  {item.step && (
                    <span className={`font-mono text-[9px] ${active ? "text-teal-400" : "text-zinc-600"}`}>
                      {item.step}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </nav>

        {sidebarOpen && (
          <div
            className="fixed inset-0 z-20 bg-zinc-950/60 sm:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        <main className="min-w-0 flex-1">
          {error && (
            <div className="mx-auto max-w-4xl px-4 pt-4">
              <div className="flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-xs text-amber-200">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <div>
                  <div className="font-medium">Backend note</div>
                  <div className="mt-0.5 text-amber-200/80">{error}</div>
                </div>
              </div>
            </div>
          )}
          {view === "landing" && <LandingView />}
          {view === "logline" && <LoglineView />}
          {view === "research" && <ResearchView />}
          {view === "bible" && <BibleView />}
          {view === "shots" && <ShotListView />}
          {view === "render" && <RenderQueueView />}
          {view === "grid" && <ShotGridView onShotClick={(s) => setDetailShot({
            id: s.id,
            label: `Shot ${s.id} — ${s.label}`,
            scene: s.scene,
            frame: s.frame,
            scores: { face: s.score - 0.05, age: s.score, beard: s.score, wardrobe: s.score, overall: s.score },
            notes: s.notes,
          })} />}
          {view === "consistency" && <ConsistencyView />}
          {view === "assembly" && <AssemblyView />}
          {view === "share" && <ShareView />}
        </main>
      </div>

      <footer className="mt-auto border-t border-zinc-800 bg-zinc-950">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-2 px-4 py-3 text-[11px] text-zinc-600 sm:flex-row sm:px-6">
          <div className="flex items-center gap-2">
            <Film className="h-3 w-3 text-teal-400" />
            <span>Auteur · The Film Bible Agent</span>
          </div>
          <div className="flex items-center gap-3">
            {health && (
              <span className="font-mono text-zinc-700">
                {Object.keys(health.model_status).length} models · {health.endpoints?.length ?? 0} endpoints
              </span>
            )}
            <Link href="https://agentic-cinema.devpost.com/" target="_blank" className="transition hover:text-zinc-400">
              Agentic Cinema
            </Link>
          </div>
        </div>
      </footer>

      {/* Slide-over health panel (press ?) */}
      <HealthPanel open={healthPanelOpen} onClose={() => setHealthPanelOpen(false)} />

      {/* Keyboard shortcuts command palette (press ⌘K) */}
      <KeyboardShortcutsHelp
        open={shortcutsHelpOpen}
        onClose={() => setShortcutsHelpOpen(false)}
        onToggleHealth={() => setHealthPanelOpen((v) => !v)}
        onLoadDemo={() => {
          // trigger the demo load (same as pressing 'd')
          const e = new KeyboardEvent("keydown", { key: "d" });
          window.dispatchEvent(e);
        }}
      />

      {/* Shot detail dialog (click a shot in the grid) */}
      <ShotDetailDialog shot={detailShot} open={!!detailShot} onOpenChange={(v) => !v && setDetailShot(null)} />
    </div>
  );
}
