"""initial schema (PRD §5, ADR-005)

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-09
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# JSONB on Postgres, JSON elsewhere (SQLite). Mirrors db/models.JSONType.
JSONType = JSONB().with_variant(sa.JSON(), "sqlite")
UUID = sa.Uuid(as_uuid=True)
TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # For V1 RAG (Phase 2); harmless now. pgvector image ships the extension.
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("clerk_user_id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", TS, nullable=True),
    )
    op.create_index("ix_users_clerk_user_id", "users", ["clerk_user_id"], unique=True)

    op.create_table(
        "athlete_profiles",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("sex", sa.String(), nullable=True),
        sa.Column("bodyweight_lb", sa.Float(), nullable=True),
        sa.Column("height_in", sa.Float(), nullable=True),
        sa.Column("resting_hr_bpm", sa.Integer(), nullable=True),
        sa.Column("estimated_1rm", JSONType, nullable=False),
        sa.Column("rep_max_known", JSONType, nullable=True),
        sa.Column("maf_data", JSONType, nullable=True),
        sa.Column("primary_goals", JSONType, nullable=False),
        sa.Column("equipment", sa.String(), nullable=False),
        sa.Column("days_per_week", sa.Integer(), nullable=False),
        sa.Column("injuries", JSONType, nullable=False),
        sa.Column("primary_modality", sa.String(), nullable=False),
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_athlete_profiles_user_id", "athlete_profiles", ["user_id"], unique=True)

    op.create_table(
        "blocks",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("athlete_id", UUID, sa.ForeignKey("athlete_profiles.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("goal", sa.String(), nullable=False),
        sa.Column("program_model", sa.String(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("phase", sa.String(), nullable=False),
        sa.Column("plan_json", JSONType, nullable=True),
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_blocks_athlete_id", "blocks", ["athlete_id"])

    op.create_table(
        "conversations",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("block_id", UUID, sa.ForeignKey("blocks.id"), nullable=False),
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_conversations_block_id", "conversations", ["block_id"])

    op.create_table(
        "messages",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("conversation_id", UUID, sa.ForeignKey("conversations.id"), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", JSONType, nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=True),
        sa.Column("tokens_out", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index(
        "ix_messages_conversation_created", "messages", ["conversation_id", "created_at"]
    )

    op.create_table(
        "log_entries",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("athlete_id", UUID, sa.ForeignKey("athlete_profiles.id"), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("occurred_at", TS, nullable=False),
        sa.Column("data", JSONType, nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_log_entries_athlete_id", "log_entries", ["athlete_id"])
    op.create_index("ix_log_entries_occurred_at", "log_entries", ["occurred_at"])
    op.create_index(
        "ix_log_entries_athlete_type_occurred",
        "log_entries",
        ["athlete_id", "type", "occurred_at"],
    )

    op.create_table(
        "artifacts",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("block_id", UUID, sa.ForeignKey("blocks.id"), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("s3_key", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_artifacts_block_id", "artifacts", ["block_id"])

    op.create_table(
        "plan_edits",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("block_id", UUID, sa.ForeignKey("blocks.id"), nullable=False),
        sa.Column("edit_type", sa.String(), nullable=False),
        sa.Column("payload", JSONType, nullable=False),
        sa.Column("staged", sa.Boolean(), nullable=False),
        sa.Column("committed_at", TS, nullable=True),
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_plan_edits_block_id", "plan_edits", ["block_id"])
    op.create_index("ix_plan_edits_block_created", "plan_edits", ["block_id", "created_at"])


def downgrade() -> None:
    op.drop_table("plan_edits")
    op.drop_table("artifacts")
    op.drop_table("log_entries")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("blocks")
    op.drop_table("athlete_profiles")
    op.drop_table("users")
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP EXTENSION IF EXISTS vector")
