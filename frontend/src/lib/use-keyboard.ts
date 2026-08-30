/**
 * Auteur — keyboard shortcuts hook.
 * 1-9: jump to views (1=landing, 2=logline, ... 9=share)
 * Esc: go back to landing (or close any open modal)
 * ?: open the health panel
 * d: load the canonical demo (lighthouse keeper)
 * ⌘K / Ctrl+K: open the keyboard shortcuts help (command palette)
 */
"use client";

import { useEffect } from "react";
import { useStudio, type StudioView } from "@/lib/store";

const VIEW_KEYS: Record<string, StudioView> = {
  "1": "landing",
  "2": "logline",
  "3": "research",
  "4": "bible",
  "5": "shots",
  "6": "render",
  "7": "grid",
  "8": "consistency",
  "9": "assembly",
  "0": "share",
};

export function useKeyboardShortcuts(opts: {
  onToggleHealth: () => void;
  onLoadDemo: () => void;
  onToggleShortcutsHelp?: () => void;
}) {
  const { view, setView, project, reset } = useStudio();

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      // ⌘K / Ctrl+K — open the shortcuts help (command palette)
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        opts.onToggleShortcutsHelp?.();
        return;
      }

      // don't intercept if typing in an input/textarea
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || (e.target as HTMLElement)?.isContentEditable) return;

      if (e.key === "Escape") {
        if (view !== "landing") setView("landing");
        return;
      }
      if (e.key === "?" || (e.key === "/" && e.shiftKey)) {
        e.preventDefault();
        opts.onToggleHealth();
        return;
      }
      if (e.key === "d" || e.key === "D") {
        e.preventDefault();
        opts.onLoadDemo();
        return;
      }
      const target = VIEW_KEYS[e.key];
      if (target) {
        // only allow navigation to views that are reachable
        if (target === "landing" || target === "logline" || project) {
          setView(target);
        }
      }
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [view, setView, project, reset, opts]);
}
