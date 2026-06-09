"""SQLAlchemy ORM models — the Phase 1 schema (PRD §5, ADR-005).

Cross-dialect types: JSONB on Postgres (falls back to JSON on SQLite so unit tests
run without a database); UUID primary keys; timezone-aware timestamps.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from obelisk_api.db.base import Base

# JSONB on Postgres, JSON elsewhere (SQLite in unit tests).
JSONType = JSONB().with_variant(JSON(), "sqlite")


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)


class User(Base):
    """Auth identity. Clerk is the source of truth; we mirror a row per user."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _uuid_pk()
    clerk_user_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    email: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    profile: Mapped[AthleteProfile | None] = relationship(back_populates="user", uselist=False)


class AthleteProfile(Base):
    """The persistent athlete identity (PRD §5)."""

    __tablename__ = "athlete_profiles"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), unique=True
    )
    name: Mapped[str] = mapped_column(String)
    age: Mapped[int] = mapped_column(Integer)
    sex: Mapped[str | None] = mapped_column(String, nullable=True)
    bodyweight_lb: Mapped[float | None] = mapped_column(Float, nullable=True)
    height_in: Mapped[float | None] = mapped_column(Float, nullable=True)
    resting_hr_bpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_1rm: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    rep_max_known: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    maf_data: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    primary_goals: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    equipment: Mapped[str] = mapped_column(String, default="full_gym")
    days_per_week: Mapped[int] = mapped_column(Integer, default=3)
    injuries: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    primary_modality: Mapped[str] = mapped_column(String, default="hybrid")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="profile")
    blocks: Mapped[list[Block]] = relationship(back_populates="athlete")


class Block(Base):
    """The training-cycle workspace (PRD §5)."""

    __tablename__ = "blocks"

    id: Mapped[uuid.UUID] = _uuid_pk()
    athlete_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("athlete_profiles.id"), index=True
    )
    name: Mapped[str] = mapped_column(String)
    goal: Mapped[str] = mapped_column(String, default="")
    program_model: Mapped[str] = mapped_column(String, default="hybrid_531")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    phase: Mapped[str] = mapped_column(String, default="active")
    plan_json: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    athlete: Mapped[AthleteProfile] = relationship(back_populates="blocks")
    conversation: Mapped[Conversation | None] = relationship(
        back_populates="block", uselist=False, cascade="all, delete-orphan"
    )
    plan_edits: Mapped[list[PlanEdit]] = relationship(
        back_populates="block", cascade="all, delete-orphan"
    )
    artifacts: Mapped[list[Artifact]] = relationship(
        back_populates="block", cascade="all, delete-orphan"
    )


class Conversation(Base):
    """Per-block chat thread."""

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = _uuid_pk()
    block_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("blocks.id"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    block: Mapped[Block] = relationship(back_populates="conversation")
    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class Message(Base):
    """One chat message; stores raw Anthropic content + per-call cost telemetry."""

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = _uuid_pk()
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("conversations.id"), index=True
    )
    role: Mapped[str] = mapped_column(String)
    content: Mapped[Any] = mapped_column(JSONType)
    tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped[Conversation] = relationship(back_populates="messages")

    __table_args__ = (Index("ix_messages_conversation_created", "conversation_id", "created_at"),)


class LogEntry(Base):
    """Append-only history (sets, meals, mobility, body, sleep, hrv)."""

    __tablename__ = "log_entries"

    id: Mapped[uuid.UUID] = _uuid_pk()
    athlete_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("athlete_profiles.id"), index=True
    )
    type: Mapped[str] = mapped_column(String)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    data: Mapped[Any] = mapped_column(JSONType)
    source: Mapped[str] = mapped_column(String, default="user_input")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_log_entries_athlete_type_occurred", "athlete_id", "type", "occurred_at"),
    )


class Artifact(Base):
    """Generated outputs (cycle plan xlsx, meal/mobility plans, reports)."""

    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = _uuid_pk()
    block_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("blocks.id"), index=True
    )
    kind: Mapped[str] = mapped_column(String)
    s3_key: Mapped[str] = mapped_column(String)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    block: Mapped[Block] = relationship(back_populates="artifacts")


class PlanEdit(Base):
    """Event-sourced edit log — the lesson from OOD bugs 4 & 5 (ADR-005)."""

    __tablename__ = "plan_edits"

    id: Mapped[uuid.UUID] = _uuid_pk()
    block_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("blocks.id"), index=True
    )
    edit_type: Mapped[str] = mapped_column(String)
    payload: Mapped[Any] = mapped_column(JSONType)
    staged: Mapped[bool] = mapped_column(Boolean, default=True)
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    block: Mapped[Block] = relationship(back_populates="plan_edits")

    __table_args__ = (Index("ix_plan_edits_block_created", "block_id", "created_at"),)
