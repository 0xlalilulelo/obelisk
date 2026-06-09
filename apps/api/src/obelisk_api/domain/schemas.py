"""Pydantic request/response schemas for the /v1 API surface.

Distinct from ``domain/models.py`` (the agent's CyclePlan/Athlete). These are the
HTTP contract; the OpenAPI spec generated from them feeds packages/api-client.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# --- Athlete profile -------------------------------------------------------
class AthleteProfileIn(BaseModel):
    """5-question onboarding output + the persistent profile fields (PRD §5)."""

    name: str
    age: int = Field(ge=1, le=119)
    sex: str | None = None
    bodyweight_lb: float | None = None
    height_in: float | None = None
    resting_hr_bpm: int | None = None
    estimated_1rm: dict[str, int] = Field(default_factory=dict)
    rep_max_known: dict[str, Any] | None = None
    maf_data: dict[str, Any] | None = None
    primary_goals: list[str] = Field(default_factory=list)
    equipment: str = "full_gym"
    days_per_week: int = Field(default=3, ge=1, le=7)
    injuries: list[dict[str, Any]] = Field(default_factory=list)
    primary_modality: str = "hybrid"


class AthleteProfileOut(AthleteProfileIn):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# --- Blocks ----------------------------------------------------------------
class BlockCreateIn(BaseModel):
    """New-Block modal payload. The planner picks the program model from the
    athlete profile unless one is forced here."""

    name: str
    goal: str
    program_model: str | None = None


class BlockOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    athlete_id: uuid.UUID
    name: str
    goal: str
    program_model: str
    phase: str
    start_date: date | None = None
    end_date: date | None = None
    plan_json: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class BlockSummaryOut(BaseModel):
    """List view — omits the heavy plan_json."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    goal: str
    program_model: str
    phase: str
    start_date: date | None = None
    end_date: date | None = None
    created_at: datetime


class PlanOut(BaseModel):
    """Canonical plan: the full CyclePlan dict plus a compact summary (get_plan_json)."""

    plan: dict[str, Any] | None
    summary: str


# --- Chat / messages -------------------------------------------------------
class ChatIn(BaseModel):
    message: str = Field(min_length=1)


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: Any
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost_usd: float | None = None
    latency_ms: int | None = None
    created_at: datetime


class MessagePage(BaseModel):
    messages: list[MessageOut]
    total: int
    limit: int
    offset: int


# --- Plan edits ------------------------------------------------------------
class PlanEditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    edit_type: str
    staged: bool
    committed_at: datetime | None = None
    created_at: datetime


class ArtifactUrlOut(BaseModel):
    kind: str
    url: str
    version: int
