/**
 * KeyboardShortcutsHelp — a command-palette-style dialog showing all keyboard
 * shortcuts. Opens with ⌘K / Ctrl+K (and the "?" key still opens the health
 * panel).
 *
 * Lists navigation, action, and submit shortcuts grouped by category, each
 * with styled <kbd> chips so the user can see exactly what to press.
 */
"use client";

import { useEffect } from "react";
import { Command, Navigation, Zap, X } from "lucide-react";

interface Shortcut {
  keys: string[];
  label: string;
  hint?: string;
}

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
  { keys: ["⌘", "K"], label: "Open this help", hint: "command palette" },
  { keys: ["?"], label: "Toggle backend status", hint: "health panel" },
  { keys: ["D"], label: "Load canonical demo", hint: "lighthouse keeper" },
  { keys: ["Esc"], label: "Back to home", hint: "or close a dialog" },
];

const SUBMIT_SHORTCUTS: Shortcut[] = [
  { keys: ["⌘", "↵"], label: "Submit logline", hint: "on the logline view" },
];

interface Props {
  open: boolean;
  onClose: () => void;
}

export function KeyboardShortcutsHelp({ open, onClose }: Props) {
  // close on Escape (but don't trigger the global "back to home" — stopPropagation)
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        e.stopPropagation();
        onClose();
      }
    }
    // capture phase so we run before the global handler
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-zinc-950/70 px-4 pt-[10vh] backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="auteur-cmd-in w-full max-w-lg overflow-hidden rounded-xl border border-zinc-700 bg-zinc-950 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* header */}
        <div className="flex items-center justify-between border-b border-zinc-800 bg-zinc-900/60 px-4 py-3">
          <div className="flex items-center gap-2">
            <Command className="h-4 w-4 text-teal-400" />
            <span className="text-sm font-semibold text-zinc-100">Keyboard shortcuts</span>
          </div>
          <button
            onClick={onClose}
            className="grid h-7 w-7 place-items-center rounded-md text-zinc-500 transition hover:bg-zinc-800 hover:text-zinc-200"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* body */}
        <div className="max-h-[60vh] overflow-y-auto auteur-scroll p-4">
          {/* navigation */}
          <Section
            icon={<Navigation className="h-3.5 w-3.5 text-teal-400" />}
            title="Navigation"
            shortcuts={NAV_SHORTCUTS}
          />

          {/* actions */}
          <Section
            icon={<Zap className="h-3.5 w-3.5 text-amber-400" />}
            title="Actions"
            shortcuts={ACTION_SHORTCUTS}
            className="mt-6"
          />

          {/* submit */}
          <Section
            icon={<Command className="h-3.5 w-3.5 text-emerald-400" />}
            title="Submit"
            shortcuts={SUBMIT_SHORTCUTS}
            className="mt-6"
          />
        </div>

        {/* footer */}
        <div className="border-t border-zinc-800 bg-zinc-900/40 px-4 py-2.5">
          <p className="text-center text-[10px] text-zinc-600">
            Press <span className="auteur-kbd inline-flex">Esc</span> or click outside to close
          </p>
        </div>
      </div>
    </div>
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
