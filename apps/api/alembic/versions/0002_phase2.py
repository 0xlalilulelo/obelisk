"""phase 2: wearable samples, subscriptions, notification prefs (PRD §2.2/2.3/2.6)

Revision ID: 0002_phase2
Revises: 0001_initial
Create Date: 2026-06-09
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0002_phase2"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONType = JSONB().with_variant(sa.JSON(), "sqlite")
UUID = sa.Uuid(as_uuid=True)
TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    # --- Notification preferences on the athlete profile (PRD §2.3) ---
    op.add_column("athlete_profiles", sa.Column("apns_device_token", sa.String(), nullable=True))
    op.add_column(
        "athlete_profiles",
        sa.Column("timezone", sa.String(), nullable=False, server_default="America/New_York"),
    )
    op.add_column(
        "athlete_profiles",
        sa.Column("morning_ping_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "athlete_profiles",
        sa.Column("morning_ping_time", sa.String(), nullable=False, server_default="07:00"),
    )
    op.add_column(
        "athlete_profiles",
        sa.Column("weekly_recap_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "athlete_profiles",
        sa.Column(
            "event_notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
    )
    op.add_column(
        "athlete_profiles",
        sa.Column("quiet_hours_start", sa.String(), nullable=False, server_default="22:00"),
    )
    op.add_column(
        "athlete_profiles",
        sa.Column("quiet_hours_end", sa.String(), nullable=False, server_default="06:00"),
    )

    # --- Wearable samples (PRD §2.2) ---
    op.create_table(
        "wearable_samples",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("athlete_id", UUID, sa.ForeignKey("athlete_profiles.id"), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("sample_type", sa.String(), nullable=False),
        sa.Column("occurred_at", TS, nullable=False),
        sa.Column("duration_sec", sa.Integer(), nullable=True),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(), nullable=True),
        sa.Column("raw", JSONType, nullable=False),
        sa.Column("dedup_key", sa.String(), nullable=False),
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_wearable_samples_athlete_id", "wearable_samples", ["athlete_id"])
    op.create_index("ix_wearable_samples_occurred_at", "wearable_samples", ["occurred_at"])
    op.create_index("ix_wearable_samples_dedup_key", "wearable_samples", ["dedup_key"], unique=True)
    op.create_index(
        "ix_wearable_athlete_type_occurred",
        "wearable_samples",
        ["athlete_id", "sample_type", "occurred_at"],
    )

    # --- Subscriptions (PRD §2.6) ---
    op.create_table(
        "subscriptions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("tier", sa.String(), nullable=False, server_default="free"),
        sa.Column("source", sa.String(), nullable=False, server_default="free"),
        sa.Column("apple_original_transaction_id", sa.String(), nullable=True),
        sa.Column("stripe_customer_id", sa.String(), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("period_start", TS, nullable=True),
        sa.Column("period_end", TS, nullable=True),
        sa.Column("canceled_at", TS, nullable=True),
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"], unique=True)
    op.create_index(
        "ix_subscriptions_apple_original_transaction_id",
        "subscriptions",
        ["apple_original_transaction_id"],
    )
    op.create_index(
        "ix_subscriptions_stripe_customer_id", "subscriptions", ["stripe_customer_id"]
    )
    op.create_index(
        "ix_subscriptions_stripe_subscription_id", "subscriptions", ["stripe_subscription_id"]
    )


def downgrade() -> None:
    op.drop_table("subscriptions")
    op.drop_table("wearable_samples")
    for col in (
        "quiet_hours_end",
        "quiet_hours_start",
        "event_notifications_enabled",
        "weekly_recap_enabled",
        "morning_ping_time",
        "morning_ping_enabled",
        "timezone",
        "apns_device_token",
    ):
        op.drop_column("athlete_profiles", col)
