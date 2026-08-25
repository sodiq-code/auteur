/**
 * Auteur — API client (blueprint Section 26.2, Table 38).
 *
 * Wired to the deployed Cloud Run backend. All 14 endpoints from Table 38.
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

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "https://auteur-dev-jbkbgthudq-uc.a.run.app";

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
// Director Agent (Table 38 — runtime endpoints)
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
// Projects (Table 38 rows 1-2)
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
// Bible (Table 38 rows 3-4)
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
// Shots (Table 38 rows 5-8)
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

export async function regenerateShot(
  projectId: string,
  shotId: string,
  reason: string,
): Promise<{ generation_id: string; status: string }> {
  return apiFetch(`/api/projects/${projectId}/shots/${shotId}/regenerate`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
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
// Assembly + Share + Export (Table 38 rows 9-13)
// --------------------------------------------------------------------------- //

export async function assembleFilm(projectId: string): Promise<{ output_url: string | null; status: string }> {
  return apiFetch(`/api/projects/${projectId}/assemble`, { method: "POST" });
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
