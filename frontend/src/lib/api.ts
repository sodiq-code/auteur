/**
 * Auteur — API client.
 *
 * Wired to the deployed Cloud Run backend. All 14 endpoints.
 * Uses the XTransformPort gateway pattern for local dev (not needed in prod
 * since the backend is on its own Cloud Run URL).
 */

import type {
  FilmBible,
  HealthStatus,
  Project,
  ProjectState,
  ShotSpec,
} from "./types";

// The frontend calls the dedicated backend service directly (NOT through the Next.js proxy)
// This avoids the proxy timeout issue on long-running calls like build-bible (~30s)
// Hardcoded — no env var dependency
const API_BASE = "https://auteur-dev-jbkbgthudq-uc.a.run.app";

async function apiFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const resp = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
  });
  if (!resp.ok) {
    const body = await resp.text();
    let detail = body;
    try {
      detail = JSON.parse(body).detail || body;
    } catch {
      /* keep raw text */
    }
    throw new AuteurApiError(resp.status, detail, path);
  }
  return resp.json();
}

export class AuteurApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
    public path: string,
  ) {
    super(`[${status}] ${path}: ${detail}`);
    this.name = "AuteurApiError";
  }
}

// --------------------------------------------------------------------------- //
// Health
// --------------------------------------------------------------------------- //

export async function getHealth(): Promise<HealthStatus> {
  return apiFetch<HealthStatus>("/api/health");
}

// --------------------------------------------------------------------------- //
// Canonical demo (pre-rendered safety net)
// --------------------------------------------------------------------------- //

export interface DemoData {
  status: string;
  logline: string;
  bible: Record<string, unknown>;
  shots: Array<{ id: string; order: number; label: string; scene: string; frame: string; score: number }>;
  consistency: {
    mean_overall: number;
    threshold: number;
    verdict: string;
    model: string;
    independent_vlm: number;
  };
  side_by_side: string;
  character_reference: string;
  note: string;
}

export async function getDemo(): Promise<DemoData> {
  return apiFetch<DemoData>("/api/demo");
}

// --------------------------------------------------------------------------- //
// Director Agent
// --------------------------------------------------------------------------- //

export interface BuildBibleResponse {
  bible: FilmBible;
  version: number;
  references: Reference[];
  references_count: number;
  project_status: string;
}

export async function buildBible(projectId: string): Promise<BuildBibleResponse> {
  return apiFetch<BuildBibleResponse>(`/api/projects/${projectId}/build-bible`, {
    method: "POST",
  });
}

export async function getResearch(projectId: string): Promise<{
  references: Reference[];
  references_count: number;
  bible_version?: number;
}> {
  return apiFetch(`/api/projects/${projectId}/research`);
}

// --------------------------------------------------------------------------- //
// Projects
// --------------------------------------------------------------------------- //

export async function createProject(logline: string): Promise<Project> {
  const data = await apiFetch<{ project_id: string; logline: string; status: string; created_at: string }>(
    "/api/projects",
    { method: "POST", body: JSON.stringify({ logline }) },
  );
  return {
    id: data.project_id,
    logline: data.logline,
    created_at: data.created_at,
    current_bible_version: 0,
    status: data.status as Project["status"],
  };
}

export async function getProject(projectId: string): Promise<ProjectState> {
  return apiFetch<ProjectState>(`/api/projects/${projectId}`);
}

// --------------------------------------------------------------------------- //
// Bible
// --------------------------------------------------------------------------- //

export async function getBible(projectId: string): Promise<{ bible: FilmBible; version: number }> {
  return apiFetch(`/api/projects/${projectId}/bible`);
}

export async function editBibleEntry(
  projectId: string,
  entryId: string,
  field: string,
  value: string,
): Promise<{ bible: FilmBible; version: number }> {
  return apiFetch(`/api/projects/${projectId}/bible/entries/${entryId}`, {
    method: "PATCH",
    body: JSON.stringify({ field, value }),
  });
}

// --------------------------------------------------------------------------- //
// Shots
// --------------------------------------------------------------------------- //

export async function getShots(projectId: string): Promise<{ shots: ShotSpec[] }> {
  return apiFetch(`/api/projects/${projectId}/shots`);
}

export async function generateShot(
  projectId: string,
  shotId: string,
  bibleVersion: number,
): Promise<{ generation_id: string; status: string }> {
  return apiFetch(`/api/projects/${projectId}/shots/${shotId}/generate`, {
    method: "POST",
    body: JSON.stringify({ bible_version: bibleVersion }),
  });
}

// --------------------------------------------------------------------------- //
// Regeneration (the closed loop)
// --------------------------------------------------------------------------- //

export interface RegenerationResponse {
  shot_id: string;
  status: string;
  bible_version: number;
  drift_correction_applied: boolean;
  prior_drift: { overall: number | null; drift_score: number | null } | null;
  generation: {
    shot_id: string;
    order: number;
    status: string;
    modalities: Record<string, { status: string; [k: string]: unknown }>;
    elapsed_sec: number;
  };
  consistency: {
    shot_id: string;
    status: string;
    overall?: number | null;
    drift_score?: number | null;
    face_identity?: number | null;
    age_appearance?: number | null;
    beard_facial_hair?: number | null;
    wardrobe?: number | null;
    recommendation?: string | null;
    notes?: string;
  };
}

export async function regenerateShot(
  projectId: string,
  shotId: string,
  reason: string = "",
  bibleVersion: number = 1,
  useDriftCorrection: boolean = true,
): Promise<RegenerationResponse> {
  return apiFetch<RegenerationResponse>(
    `/api/projects/${projectId}/shots/${shotId}/regenerate`,
    {
      method: "POST",
      body: JSON.stringify({
        reason,
        bible_version: bibleVersion,
        use_drift_correction: useDriftCorrection,
      }),
    },
  );
}

export interface AutoRegenerateResponse {
  project_id: string;
  status: string;
  threshold: number;
  shots_checked: number;
  shots_regenerated: number;
  regenerations: Array<{
    shot_id: string;
    order: number;
    before: { overall: number | null; drift_score: number | null; recommendation: string | null };
    after: { overall: number | null; drift_score: number | null; recommendation: string | null };
    drift_correction_applied: boolean;
  }>;
}

export async function autoRegenerate(projectId: string): Promise<AutoRegenerateResponse> {
  return apiFetch<AutoRegenerateResponse>(
    `/api/projects/${projectId}/shots/auto-regenerate`,
    { method: "POST" },
  );
}

export async function getConsistency(
  projectId: string,
  shotId: string,
): Promise<{ drift_score: number | null; breakdown: unknown; recommendation: string | null; status?: string }> {
  return apiFetch(`/api/projects/${projectId}/shots/${shotId}/consistency`);
}

export async function runConsistency(
  projectId: string,
  shotId: string,
): Promise<Record<string, unknown>> {
  return apiFetch(`/api/projects/${projectId}/shots/${shotId}/consistency`, { method: "POST" });
}

export interface ConsistencyShotReport {
  shot_id: string;
  order: number;
  description?: string;
  status: string;
  drift_score?: number | null;
  overall?: number | null;
  face_identity?: number | null;
  age_appearance?: number | null;
  beard_facial_hair?: number | null;
  wardrobe?: number | null;
  recommendation?: string | null;
  notes?: string;
  error?: string;
}

export interface ConsistencyAllResponse {
  project_id: string;
  status: string;
  shots: ConsistencyShotReport[];
  mean_overall: number;
  threshold: number;
  verdict: string;
  elapsed_sec: number;
}

export async function checkAllShots(projectId: string): Promise<ConsistencyAllResponse> {
  return apiFetch<ConsistencyAllResponse>(`/api/projects/${projectId}/shots/check-all`, {
    method: "POST",
  });
}

// --------------------------------------------------------------------------- //
// Assembly + Share + Export
// --------------------------------------------------------------------------- //

export interface AudioSummary {
  voiceover_shots: number;
  score_shots: number;
  silent_shots: number;
  per_shot: Array<{
    order: number;
    shot_id: string;
    duration_seconds: number;
    voiceover: boolean;
    score: boolean;
    mix_mode: string;
  }>;
}

export interface AssembleFilmResponse {
  status: string;
  output_url: string | null;
  duration_seconds: number;
  clip_count: number;
  size_bytes: number;
  has_audio: boolean;
  audio: AudioSummary;
  elapsed_sec: number;
}

export async function assembleFilm(projectId: string): Promise<AssembleFilmResponse> {
  return apiFetch<AssembleFilmResponse>(`/api/projects/${projectId}/assemble`, { method: "POST" });
}

export async function createShareLink(projectId: string): Promise<{ public_slug: string; share_url: string }> {
  return apiFetch(`/api/projects/${projectId}/share`, { method: "POST" });
}

export async function exportBible(projectId: string): Promise<FilmBible> {
  return apiFetch(`/api/projects/${projectId}/export/bible`);
}

export async function exportShotsCsv(projectId: string): Promise<string> {
  const resp = await fetch(`${API_BASE}/api/projects/${projectId}/export/shots`);
  return resp.text();
}

export async function getEvents(projectId: string): Promise<{ project_id: string; events: unknown[]; count: number }> {
  return apiFetch(`/api/projects/${projectId}/events`);
}

// --------------------------------------------------------------------------- //
// Public share view
// --------------------------------------------------------------------------- //

export interface SharedProject {
  project: Project;
  bible: FilmBible | null;
  shots: ShotSpec[];
  film_url: string | null;
  share_slug: string;
}

export async function getSharedProject(slug: string): Promise<SharedProject> {
  return apiFetch<SharedProject>(`/api/share/${slug}`);
}
