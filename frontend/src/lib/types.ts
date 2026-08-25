/**
 * Auteur — TypeScript types mirroring the backend Pydantic schema
 * (backend/bible/schema.py). Keep in sync.
 */

export type Modality = "text" | "image" | "video" | "audio";

export interface Reference {
  id: string;
  url: string;
  title: string;
  snippet: string;
  image_url?: string | null;
  modality: Modality;
  retrieved_at?: string;
}

export interface CharacterSpec {
  id: string;
  name: string;
  age?: number | null;
  description: string;
  voice_profile?: string;
  wardrobe?: string;
  reference_image_url?: string | null;
  references?: Reference[];
}

export interface LocationSpec {
  id: string;
  name: string;
  description: string;
  era?: string;
  references?: Reference[];
}

export interface WardrobeSpec {
  id: string;
  character_id: string;
  garment: string;
  fabric?: string;
  color?: string;
}

export interface VoiceProfileSpec {
  id: string;
  character_id: string;
  voice_model: string;
  voice_name: string;
  description?: string;
}

export interface ScoreMotifSpec {
  id: string;
  name: string;
  prompt: string;
  instrument?: string;
  mood?: string;
}

export interface StyleAnchorSpec {
  id: string;
  color_grade: string;
  aspect_ratio: string;
  photographic_aesthetic?: string;
  mood?: string;
}

export interface StoryBeat {
  id: string;
  order: number;
  description: string;
  character_ids?: string[];
  location_id?: string | null;
}

export interface FilmBible {
  version: number;
  created_at: string;
  logline: string;
  characters: CharacterSpec[];
  locations: LocationSpec[];
  wardrobes: WardrobeSpec[];
  voice_profiles: VoiceProfileSpec[];
  score_motifs: ScoreMotifSpec[];
  style_anchors: StyleAnchorSpec[];
  story_beats: StoryBeat[];
  research_references: Reference[];
}

export type ShotStatus = "pending" | "generating" | "generated" | "approved" | "rejected";
export type ModalityCall = "veo" | "chirp" | "lyria" | "imagen";

export interface ShotSpec {
  id: string;
  order: number;
  description: string;
  bible_version: number;
  character_ids: string[];
  location_id?: string | null;
  modality_calls: ModalityCall[];
  status: ShotStatus;
}

export type ProjectStatus =
  | "created"
  | "researching"
  | "bible_v1"
  | "generating"
  | "assembled"
  | "shared";

export interface Project {
  id: string;
  logline: string;
  created_at: string;
  current_bible_version: number;
  status: ProjectStatus;
}

export interface ProjectEvent {
  type: string;
  timestamp: string;
  payload?: Record<string, unknown>;
}

export interface ProjectState {
  project: Project;
  bible: FilmBible | null;
  shots: ShotSpec[];
  events: ProjectEvent[];
}

export interface HealthStatus {
  status: string;
  service: string;
  version: string;
  timestamp_utc: string;
  partner_status: {
    parallel_search: {
      configured: boolean;
      endpoint: string;
      auth: string;
      track: string;
    };
  };
  model_status: Record<
    string,
    { model: string; region: string; configured: boolean }
  >;
}
