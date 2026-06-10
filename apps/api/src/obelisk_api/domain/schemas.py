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


# --- Set logging (In-Session) ----------------------------------------------
class SetLogIn(BaseModel):
    """One logged set. ``client_id`` is generated on-device and used as the row's
    primary key so retries (gym basement → reconnect) are idempotent (PRD §2.1)."""

    client_id: uuid.UUID
    block_id: uuid.UUID | None = None
    session_date: date
    exercise: str = Field(min_length=1)
    lift_key: str | None = None
    set_index: int = Field(ge=1, le=50)
    weight_lb: float = Field(ge=0, le=2000)
    reps: int = Field(ge=0, le=100)
    rpe: float | None = Field(default=None, ge=0, le=10)
    completed: bool = True
    occurred_at: datetime | None = None


class LogBatchIn(BaseModel):
    """Batch of set logs flushed from the on-device queue."""

    sets: list[SetLogIn] = Field(min_length=1, max_length=200)


class LogBatchResult(BaseModel):
    received: int
    inserted: int
    duplicates: int


class LogEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    occurred_at: datetime
    data: Any
    source: str
    created_at: datetime


class LogPage(BaseModel):
    entries: list[LogEntryOut]
    total: int
    limit: int
    offset: int


# --- Session prescription (pre-fill) ---------------------------------------
class LoggedSetOut(BaseModel):
    set_index: int
    weight_lb: float
    reps: int
    rpe: float | None = None
    occurred_at: datetime | None = None


class PrescribedSetOut(BaseModel):
    set_index: int
    pct: float
    reps: int
    amrap: bool
    weight_lb: int | None = None


class PrescribedExerciseOut(BaseModel):
    label: str
    kind: str
    lift_key: str | None = None
    note: str | None = None
    rest_default_sec: int
    sets: list[PrescribedSetOut]
    prior_sets: list[LoggedSetOut] = Field(default_factory=list)


class SessionOut(BaseModel):
    block_id: uuid.UUID
    date: date
    global_week: int
    week_in_wave: int
    wave_num: int
    day: str
    session_title: str
    is_rest_day: bool
    exercises: list[PrescribedExerciseOut]


# --- Wearable ingest (HealthKit) -------------------------------------------
class WearableSampleIn(BaseModel):
    """One sample from HealthKit. ``sample_uuid`` is the HKObject UUID; the backend
    dedups on (athlete, source, sample_uuid) so a re-synced window is idempotent."""

    sample_uuid: str = Field(min_length=1)
    source: str = "healthkit"
    sample_type: str  # bodyweight|sleep|hr|rhr|hrv|workout
    occurred_at: datetime
    duration_sec: int | None = None
    value: float | None = None
    unit: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class WearableBatchIn(BaseModel):
    samples: list[WearableSampleIn] = Field(min_length=1, max_length=1000)


class WearableBatchResult(BaseModel):
    received: int
    inserted: int
    duplicates: int


# --- Readiness composite ---------------------------------------------------
class ReadinessFactorOut(BaseModel):
    key: str
    label: str
    value: str
    score: int
    weight: float


class ReadinessOut(BaseModel):
    date: date
    score: int | None
    band: str
    guidance: str
    factors: list[ReadinessFactorOut]


# --- Analytics -------------------------------------------------------------
class LiftPointOut(BaseModel):
    date: date
    e1rm: int


class AnalyticsLiftsOut(BaseModel):
    """Per-lift e1RM time series keyed by lift_key (PRD §2.7 Analytics charts)."""

    series: dict[str, list[LiftPointOut]]


# --- Subscriptions ---------------------------------------------------------
class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tier: str
    status: str
    source: str
    period_end: datetime | None = None
    canceled_at: datetime | None = None


class AppleVerifyIn(BaseModel):
    signed_transaction: str = Field(min_length=1)


class StripeCheckoutIn(BaseModel):
    plan: str = Field(default="monthly", pattern="^(monthly|annual)$")


class CheckoutOut(BaseModel):
    url: str


# --- PR / e1RM -------------------------------------------------------------
class PROut(BaseModel):
    lift: str
    e1rm: int | None
    source: str  # "logged" | "profile" | "none"
    weight_lb: float | None = None
    reps: int | None = None
    occurred_at: datetime | None = None
