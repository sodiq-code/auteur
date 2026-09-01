"""
Auteur — Film Bible Pydantic schemas.

The Film Bible is the typed, versioned, citable memory schema that is injected
as structured context into every Veo / Chirp / Lyria / image generation call.
This module defines every model the Director Agent builds and every model the
generation pipeline reads.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl


# --------------------------------------------------------------------------- #
# Reference (the grounding unit — one Parallel Search result)
# --------------------------------------------------------------------------- #

Modality = Literal["text", "image", "video", "audio"]


class Reference(BaseModel):
    """One grounded reference, sourced from Parallel Search."""
    id: str = Field(default_factory=lambda: uuid4().hex)
    url: str
    title: str
    snippet: str = ""
    image_url: Optional[str] = None
    modality: Modality = "text"
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# --------------------------------------------------------------------------- #
# Bible entry types (one per dimension of the film)
# --------------------------------------------------------------------------- #

class CharacterSpec(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str
    age: Optional[int] = None
    description: str
    voice_profile: str = ""
    wardrobe: str = ""
    reference_image_url: Optional[str] = None  # character ASSET reference for Veo
    references: list[Reference] = Field(default_factory=list)


class LocationSpec(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str
    description: str
    era: str = ""
    references: list[Reference] = Field(default_factory=list)


class WardrobeSpec(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    character_id: str
    garment: str
    fabric: str = ""
    color: str = ""
    references: list[Reference] = Field(default_factory=list)


class VoiceProfileSpec(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    character_id: str
    voice_model: str = "gemini-3.1-flash-tts-preview"  #
    voice_name: str = "Charon"
    description: str = ""


class ScoreMotifSpec(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str
    prompt: str  # the Lyria prompt for this motif
    instrument: str = ""
    mood: str = ""


class StyleAnchorSpec(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    color_grade: str
    aspect_ratio: str = "16:9"
    photographic_aesthetic: str = ""
    mood: str = ""


class StoryBeat(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    order: int
    description: str
    character_ids: list[str] = Field(default_factory=list)
    location_id: Optional[str] = None


# --------------------------------------------------------------------------- #
# Film Bible (top-level, versioned)
# --------------------------------------------------------------------------- #

class FilmBible(BaseModel):
    """The top-level Film Bible.

    Versioned: every user edit creates a new immutable version.
    Every generation cites which Bible version it used, so drift is attributable.
    """
    version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    logline: str
    characters: list[CharacterSpec] = Field(default_factory=list)
    locations: list[LocationSpec] = Field(default_factory=list)
    wardrobes: list[WardrobeSpec] = Field(default_factory=list)
    voice_profiles: list[VoiceProfileSpec] = Field(default_factory=list)
    score_motifs: list[ScoreMotifSpec] = Field(default_factory=list)
    style_anchors: list[StyleAnchorSpec] = Field(default_factory=list)
    story_beats: list[StoryBeat] = Field(default_factory=list)
    research_references: list[Reference] = Field(default_factory=list)

    def bump_version(self) -> "FilmBible":
        """Return a new immutable copy with version+1."""
        return self.model_copy(update={"version": self.version + 1})


# --------------------------------------------------------------------------- #
# Shot list (what gets generated)
# --------------------------------------------------------------------------- #

ModalityCall = Literal["veo", "chirp", "lyria", "imagen"]
ShotStatus = Literal["pending", "generating", "generated", "approved", "rejected"]


class ShotSpec(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    order: int
    description: str
    bible_version: int  # cites which Bible version produced this shot
    character_ids: list[str] = Field(default_factory=list)
    location_id: Optional[str] = None
    modality_calls: list[ModalityCall] = Field(default_factory=lambda: ["veo", "chirp", "lyria"])
    status: ShotStatus = "pending"


# --------------------------------------------------------------------------- #
# Project (top-level entity)
# --------------------------------------------------------------------------- #

ProjectStatus = Literal["created", "researching", "bible_v1", "generating", "assembled", "shared"]


class Project(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)  # 128-bit UUIDv4
    logline: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    current_bible_version: int = 0  # 0 = no bible yet
    status: ProjectStatus = "created"
