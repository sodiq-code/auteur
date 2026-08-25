/**
 * Auteur — global app state (Zustand).
 *
 * Manages the current view, the active project, and the staged Film Bible
 * (for the demo flow when the backend's full generation pipeline isn't yet
 * wired end-to-end).
 */
import { create } from "zustand";
import type { FilmBible, Project, ShotSpec, Reference } from "./types";

export type StudioView =
  | "landing"
  | "logline"
  | "research"
  | "bible"
  | "shots"
  | "render"
  | "grid"
  | "consistency"
  | "assembly"
  | "share";

interface StudioState {
  view: StudioView;
  project: Project | null;
  bible: FilmBible | null;
  shots: ShotSpec[];
  research: Reference[];
  researchProgress: "idle" | "searching" | "synthesizing" | "done" | "error";
  shareSlug: string | null;
  error: string | null;

  setView: (v: StudioView) => void;
  setProject: (p: Project | null) => void;
  setBible: (b: FilmBible | null) => void;
  setShots: (s: ShotSpec[]) => void;
  setResearch: (r: Reference[]) => void;
  setResearchProgress: (p: StudioState["researchProgress"]) => void;
  setShareSlug: (s: string | null) => void;
  setError: (e: string | null) => void;
  reset: () => void;
}

export const useStudio = create<StudioState>((set) => ({
  view: "landing",
  project: null,
  bible: null,
  shots: [],
  research: [],
  researchProgress: "idle",
  shareSlug: null,
  error: null,

  setView: (view) => set({ view }),
  setProject: (project) => set({ project }),
  setBible: (bible) => set({ bible }),
  setShots: (shots) => set({ shots }),
  setResearch: (research) => set({ research }),
  setResearchProgress: (researchProgress) => set({ researchProgress }),
  setShareSlug: (shareSlug) => set({ shareSlug }),
  setError: (error) => set({ error }),
  reset: () =>
    set({
      view: "landing",
      project: null,
      bible: null,
      shots: [],
      research: [],
      researchProgress: "idle",
      shareSlug: null,
      error: null,
    }),
}));
