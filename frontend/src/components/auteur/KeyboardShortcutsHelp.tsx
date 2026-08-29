/**
 * KeyboardShortcutsHelp — a command-palette-style dialog.
 *
 * Two tabs:
 *   - "Actions": a fuzzy-searchable, keyboard-navigable list of runnable
 *     commands (navigate to a view, load the demo, toggle the health panel,
 *     reset the project, etc.). Arrow keys move the selection, Enter runs it.
 *   - "Shortcuts": the reference list of all keyboard shortcuts with kbd chips.
 *
 * Opens with ⌘K / Ctrl+K. Closes on Esc (capture-phase, stops propagation so
 * the global "back to home" doesn't fire) or click-outside.
 *
 * The palette is context-aware: navigation actions are disabled (greyed out)
 * when the destination isn't reachable yet (e.g. can't go to "Bible" before a
 * project exists). Action commands that need a project show the project id.
 */
"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  Command, Navigation, Zap, X, Search, CornerDownLeft, Home, Edit3,
  Search as SearchIcon, BookOpen, ListOrdered, Loader2, Grid3x3, Gauge,
  Clapperboard, Share2, Server, Sparkles, RotateCcw, ArrowUp, ArrowDown,
} from "lucide-react";
import { useStudio, type StudioView } from "@/lib/store";

// --------------------------------------------------------------------------- //
// Types
// --------------------------------------------------------------------------- //

interface Shortcut {
  keys: string[];
  label: string;
  hint?: string;
}

interface Action {
  id: string;
  label: string;
  hint?: string;
  icon: typeof Home;
  group: "Navigate" | "Action";
  run: () => void;
  disabled?: boolean;
  disabledReason?: string;
  keywords?: string;
}

// --------------------------------------------------------------------------- //
// Shortcut reference data (the "Shortcuts" tab)
// --------------------------------------------------------------------------- //

const NAV_SHORTCUTS: Shortcut[] = [
  { keys: ["1"], label: "Home", hint: "landing" },
  { keys: ["2"], label: "Logline", hint: "step 1" },
  { keys: ["3"], label: "Research", hint: "step 2" },
  { keys: ["4"], label: "Bible", hint: "step 3" },
  { keys: ["5"], label: "Shots", hint: "step 4" },
  { keys: ["6"], label: "Render", hint: "step 5" },
  { keys: ["7"], label: "Grid", hint: "step 6" },
  { keys: ["8"], label: "Drift", hint: "step 7" },
  { keys: ["9"], label: "Assembly", hint: "step 8" },
  { keys: ["0"], label: "Share", hint: "step 9" },
];

const ACTION_SHORTCUTS: Shortcut[] = [
  { keys: ["⌘", "K"], label: "Open this palette", hint: "command palette" },
  { keys: ["?"], label: "Toggle backend status", hint: "health panel" },
  { keys: ["D"], label: "Load the sample production", hint: "lighthouse keeper" },
  { keys: ["Esc"], label: "Back to home", hint: "or close a dialog" },
];

const SUBMIT_SHORTCUTS: Shortcut[] = [
  { keys: ["⌘", "↵"], label: "Submit logline", hint: "on the logline view" },
];

// --------------------------------------------------------------------------- //
// Fuzzy match — simple substring match across label + hint + keywords,
// case-insensitive, with a small bonus for prefix matches.
// --------------------------------------------------------------------------- //

function fuzzyScore(query: string, haystack: string): number {
  if (!query) return 1;
  const q = query.toLowerCase().trim();
  const h = haystack.toLowerCase();
  if (!q) return 1;
  if (h.includes(q)) {
    // prefix match scores higher
    const idx = h.indexOf(q);
    return idx === 0 ? 100 : 50 - idx;
  }
  // word-boundary partial: each query token must appear in the haystack
  const tokens = q.split(/\s+/).filter(Boolean);
  if (tokens.every((t) => h.includes(t))) return 20;
  return -1;
}

// --------------------------------------------------------------------------- //
// Component
// --------------------------------------------------------------------------- //

interface Props {
  open: boolean;
  onClose: () => void;
  onToggleHealth: () => void;
  onLoadDemo: () => void;
}

export function KeyboardShortcutsHelp({ open, onClose, onToggleHealth, onLoadDemo }: Props) {
  // Esc closes the palette (capture-phase so the global "back to home" doesn't fire).
  // The inner PaletteContent is only mounted when open, so its useState initializers
  // give fresh state each time the palette opens (no reset effect needed).
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        e.stopPropagation();
        onClose();
      }
    }
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <PaletteContent
      onClose={onClose}
      onToggleHealth={onToggleHealth}
      onLoadDemo={onLoadDemo}
    />
  );
}

function PaletteContent({ onClose, onToggleHealth, onLoadDemo }: Omit<Props, "open">) {
  const { setView, project, reset } = useStudio();
  const [tab, setTab] = useState<"actions" | "shortcuts">("actions");
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Build the action list (context-aware: disable unreachable destinations)
  const actions = useMemo<Action[]>(() => {
    const navItems: { view: StudioView; label: string; icon: typeof Home; hint: string }[] = [
      { view: "landing", label: "Go to Home", icon: Home, hint: "the landing page" },
      { view: "logline", label: "Go to Logline", icon: Edit3, hint: "step 1 — enter the logline" },
      { view: "research", label: "Go to Research", icon: SearchIcon, hint: "step 2 — Parallel Search refs" },
      { view: "bible", label: "Go to Bible", icon: BookOpen, hint: "step 3 — the Film Bible" },
      { view: "shots", label: "Go to Shots", icon: ListOrdered, hint: "step 4 — the shot list" },
      { view: "render", label: "Go to Render Queue", icon: Loader2, hint: "step 5 — Veo + Chirp + Lyria" },
      { view: "grid", label: "Go to Shot Grid", icon: Grid3x3, hint: "step 6 — the shot grid" },
      { view: "consistency", label: "Go to Drift Report", icon: Gauge, hint: "step 7 — consistency check" },
      { view: "assembly", label: "Go to Assembly", icon: Clapperboard, hint: "step 8 — final film" },
      { view: "share", label: "Go to Share", icon: Share2, hint: "step 9 — public share link" },
    ];
    const reached = (v: StudioView) => v === "landing" || v === "logline" || project !== null;
    const navActions: Action[] = navItems.map((n) => ({
      id: `nav-${n.view}`,
      label: n.label,
      hint: n.hint,
      icon: n.icon,
      group: "Navigate",
      keywords: `${n.view} ${n.label} ${n.hint}`,
      run: () => {
        if (reached(n.view)) {
          setView(n.view);
          onClose();
        }
      },
      disabled: !reached(n.view),
      disabledReason: "create a project first",
    }));
    const actionItems: Action[] = [
      {
        id: "act-health",
        label: "Toggle backend status",
        hint: "open the health panel",
        icon: Server,
        group: "Action",
        keywords: "health backend status models api",
        run: () => {
          onToggleHealth();
          onClose();
        },
      },
      {
        id: "act-demo",
        label: "Load the sample production",
        hint: "the lighthouse-keeper 4-shot demo",
        icon: Sparkles,
        group: "Action",
        keywords: "demo sample canonical lighthouse ewan example",
        run: () => {
          onLoadDemo();
          onClose();
        },
      },
      {
        id: "act-reset",
        label: "Reset project",
        hint: "clear the current project and start over",
        icon: RotateCcw,
        group: "Action",
        keywords: "reset clear new restart start over",
        run: () => {
          reset();
          onClose();
        },
        disabled: !project,
        disabledReason: "no active project",
      },
    ];
    return [...navActions, ...actionItems];
  }, [project, setView, onToggleHealth, onLoadDemo, reset, onClose]);

  // Filter actions by the fuzzy query
  const filtered = useMemo(() => {
    if (!query.trim()) return actions;
    return actions
      .map((a) => {
        const hay = `${a.label} ${a.hint || ""} ${a.keywords || ""} ${a.group}`;
        return { a, score: fuzzyScore(query, hay) };
      })
      .filter((x) => x.score >= 0)
      .sort((x, y) => y.score - x.score)
      .map((x) => x.a);
  }, [actions, query]);

  // Clamp activeIndex when the filtered list shrinks (computed inline, no effect)
  const maxIndex = Math.max(0, filtered.length - 1);
  if (activeIndex > maxIndex) {
    setActiveIndex(maxIndex);
  }

  // Auto-focus the search input on mount (the component is freshly mounted each open).
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Scroll the active item into view
  useEffect(() => {
    const el = listRef.current?.querySelector(`[data-idx="${activeIndex}"]`);
    el?.scrollIntoView({ block: "nearest" });
  }, [activeIndex]);

  // Keyboard nav (capture phase so we beat the global Esc handler in the wrapper)
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") return; // handled by the wrapper
      if (tab !== "actions") return;
      if (e.key === "ArrowDown") {
        e.preventDefault();
        e.stopPropagation();
        setActiveIndex((i) => Math.min(i + 1, filtered.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        e.stopPropagation();
        setActiveIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === "Enter") {
        e.preventDefault();
        e.stopPropagation();
        const a = filtered[activeIndex];
        if (a && !a.disabled) a.run();
      } else if (e.key === "Tab") {
        e.preventDefault();
        e.stopPropagation();
        setTab((t) => (t === "actions" ? "shortcuts" : "actions"));
      }
    }
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [tab, filtered, activeIndex]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-zinc-950/70 px-4 pt-[8vh] backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="auteur-cmd-in w-full max-w-xl overflow-hidden rounded-xl border border-zinc-700 bg-zinc-950 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* header with tabs */}
        <div className="border-b border-zinc-800 bg-zinc-900/60">
          <div className="flex items-center justify-between px-4 pt-3">
            <div className="flex items-center gap-2">
              <Command className="h-4 w-4 text-teal-400" />
              <span className="text-sm font-semibold text-zinc-100">Command palette</span>
            </div>
            <button
              onClick={onClose}
              className="grid h-7 w-7 place-items-center rounded-md text-zinc-500 transition hover:bg-zinc-800 hover:text-zinc-200"
              aria-label="Close"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          {/* tab switcher */}
          <div className="flex gap-1 px-4 pt-2.5">
            <TabButton active={tab === "actions"} onClick={() => setTab("actions")}>
              <Zap className="h-3 w-3" /> Actions
            </TabButton>
            <TabButton active={tab === "shortcuts"} onClick={() => setTab("shortcuts")}>
              <Command className="h-3 w-3" /> Shortcuts
            </TabButton>
          </div>
        </div>

        {/* body */}
        {tab === "actions" ? (
          <>
            {/* search input */}
            <div className="flex items-center gap-2 border-b border-zinc-800 px-4 py-2.5">
              <Search className="h-4 w-4 text-zinc-500" />
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search actions (e.g. bible, sample, reset, share)"
                className="flex-1 bg-transparent text-sm text-zinc-100 placeholder-zinc-600 outline-none"
              />
              <span className="text-[10px] text-zinc-600">
                {filtered.length} result{filtered.length === 1 ? "" : "s"}
              </span>
            </div>

            {/* action list */}
            <div ref={listRef} className="max-h-[52vh] overflow-y-auto auteur-scroll p-2">
              {filtered.length === 0 ? (
                <div className="px-3 py-8 text-center">
                  <Search className="mx-auto mb-2 h-6 w-6 text-zinc-700" />
                  <p className="text-sm text-zinc-500">No actions match &ldquo;{query}&rdquo;</p>
                  <p className="mt-1 text-[11px] text-zinc-600">Try a different search term</p>
                </div>
              ) : (
                <>
                  {/* group: Navigate */}
                  {filtered.some((a) => a.group === "Navigate") && (
                    <GroupLabel icon={<Navigation className="h-3 w-3 text-teal-400" />}>
                      Navigate
                    </GroupLabel>
                  )}
                  {filtered.filter((a) => a.group === "Navigate").map((a) => (
                    <ActionRow
                      key={a.id}
                      action={a}
                      active={filtered[activeIndex]?.id === a.id}
                      onClick={() => !a.disabled && a.run()}
                      onMouseEnter={() => {
                        const idx = filtered.findIndex((x) => x.id === a.id);
                        if (idx >= 0) setActiveIndex(idx);
                      }}
                    />
                  ))}
                  {/* group: Action */}
                  {filtered.some((a) => a.group === "Action") && (
                    <GroupLabel icon={<Zap className="h-3 w-3 text-amber-400" />} className="mt-3">
                      Actions
                    </GroupLabel>
                  )}
                  {filtered.filter((a) => a.group === "Action").map((a) => (
                    <ActionRow
                      key={a.id}
                      action={a}
                      active={filtered[activeIndex]?.id === a.id}
                      onClick={() => !a.disabled && a.run()}
                      onMouseEnter={() => {
                        const idx = filtered.findIndex((x) => x.id === a.id);
                        if (idx >= 0) setActiveIndex(idx);
                      }}
                    />
                  ))}
                </>
              )}
            </div>

            {/* footer with nav hints */}
            <div className="flex items-center justify-between border-t border-zinc-800 bg-zinc-900/40 px-4 py-2">
              <div className="flex items-center gap-3 text-[10px] text-zinc-600">
                <span className="flex items-center gap-1">
                  <span className="auteur-kbd"><ArrowUp className="h-2.5 w-2.5" /></span>
                  <span className="auteur-kbd"><ArrowDown className="h-2.5 w-2.5" /></span>
                  navigate
                </span>
                <span className="flex items-center gap-1">
                  <span className="auteur-kbd"><CornerDownLeft className="h-2.5 w-2.5" /></span>
                  run
                </span>
                <span className="flex items-center gap-1">
                  <span className="auteur-kbd">Tab</span>
                  switch tab
                </span>
              </div>
              <span className="text-[10px] text-zinc-600">
                <span className="auteur-kbd">Esc</span> close
              </span>
            </div>
          </>
        ) : (
          /* shortcuts tab */
          <div className="max-h-[60vh] overflow-y-auto auteur-scroll p-4">
            <Section
              icon={<Navigation className="h-3.5 w-3.5 text-teal-400" />}
              title="Navigation"
              shortcuts={NAV_SHORTCUTS}
            />
            <Section
              icon={<Zap className="h-3.5 w-3.5 text-amber-400" />}
              title="Actions"
              shortcuts={ACTION_SHORTCUTS}
              className="mt-6"
            />
            <Section
              icon={<Command className="h-3.5 w-3.5 text-emerald-400" />}
              title="Submit"
              shortcuts={SUBMIT_SHORTCUTS}
              className="mt-6"
            />
          </div>
        )}
      </div>
    </div>
  );
}

// --------------------------------------------------------------------------- //
// Sub-components
// --------------------------------------------------------------------------- //

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 rounded-t-md border-b-2 px-3 py-1.5 text-xs font-medium transition ${
        active
          ? "border-teal-400 text-teal-300"
          : "border-transparent text-zinc-500 hover:text-zinc-300"
      }`}
    >
      {children}
    </button>
  );
}

function GroupLabel({
  icon,
  children,
  className = "",
}: {
  icon: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`mb-1 flex items-center gap-1.5 px-2 pt-2 text-[10px] font-medium uppercase tracking-wide text-zinc-600 ${className}`}>
      {icon}
      {children}
    </div>
  );
}

function ActionRow({
  action,
  active,
  onClick,
  onMouseEnter,
}: {
  action: Action;
  active: boolean;
  onClick: () => void;
  onMouseEnter: () => void;
}) {
  return (
    <button
      data-idx={action.id}
      onClick={onClick}
      onMouseEnter={onMouseEnter}
      disabled={action.disabled}
      className={`flex w-full items-center gap-3 rounded-md px-2.5 py-2 text-left transition ${
        active && !action.disabled
          ? "bg-teal-500/15 ring-1 ring-teal-500/30"
          : action.disabled
            ? "cursor-not-allowed opacity-40"
            : "hover:bg-zinc-900/60"
      }`}
    >
      <action.icon className={`h-3.5 w-3.5 shrink-0 ${active ? "text-teal-300" : "text-zinc-500"}`} />
      <div className="flex-1 min-w-0">
        <div className="text-xs font-medium text-zinc-200">{action.label}</div>
        {action.hint && (
          <div className="truncate text-[10px] text-zinc-500">{action.hint}</div>
        )}
      </div>
      {action.disabled && action.disabledReason && (
        <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[9px] text-zinc-500">
          {action.disabledReason}
        </span>
      )}
      {active && !action.disabled && (
        <CornerDownLeft className="h-3 w-3 text-teal-400" />
      )}
    </button>
  );
}

function Section({
  icon,
  title,
  shortcuts,
  className = "",
}: {
  icon: React.ReactNode;
  title: string;
  shortcuts: Shortcut[];
  className?: string;
}) {
  return (
    <div className={className}>
      <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-zinc-500">
        {icon}
        {title}
      </div>
      <div className="grid gap-1">
        {shortcuts.map((s, i) => (
          <div
            key={i}
            className="flex items-center justify-between rounded-md px-2 py-1.5 transition hover:bg-zinc-900/60"
          >
            <div className="flex items-center gap-2">
              <span className="text-xs text-zinc-300">{s.label}</span>
              {s.hint && (
                <span className="text-[10px] text-zinc-600">· {s.hint}</span>
              )}
            </div>
            <div className="flex items-center gap-1">
              {s.keys.map((k, j) => (
                <span key={j} className="auteur-kbd">
                  {k}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
