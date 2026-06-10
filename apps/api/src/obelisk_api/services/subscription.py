"""Subscription source-of-truth (ADR-012). One row per user; Apple and Stripe are
inputs that update it, and the athlete's tier is read from here."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from obelisk_api.db.models import Subscription, User


def _now() -> datetime:
    return datetime.now(UTC)


def _tier_for_product(product_id: str) -> str:
    return "plus" if "plus" in product_id.lower() else "free"


def _ms_to_dt(ms: Any) -> datetime | None:
    try:
        return datetime.fromtimestamp(float(ms) / 1000.0, UTC)
    except (TypeError, ValueError):
        return None


def get_or_create(db: Session, user_id: uuid.UUID) -> Subscription:
    sub = db.scalar(select(Subscription).where(Subscription.user_id == user_id))
    if sub is None:
        sub = Subscription(user_id=user_id, tier="free", source="free", status="active")
        db.add(sub)
        db.flush()
    return sub


def current_tier(db: Session, user: User) -> str:
    """The athlete's effective tier. A canceled/expired sub past its period end
    reverts to free."""
    sub = db.scalar(select(Subscription).where(Subscription.user_id == user.id))
    if sub is None:
        return "free"
    period_end = sub.period_end
    if period_end is not None and period_end.tzinfo is None:
        period_end = period_end.replace(tzinfo=UTC)  # SQLite drops tz
    if sub.status in ("canceled", "expired") and period_end and period_end < _now():
        return "free"
    return sub.tier


def apply_apple_transaction(db: Session, user_id: uuid.UUID, tx: dict[str, Any]) -> Subscription:
    """Update the user's subscription from a (decoded) StoreKit 2 transaction."""
    sub = get_or_create(db, user_id)
    sub.source = "apple"
    sub.apple_original_transaction_id = str(
        tx.get("originalTransactionId") or tx.get("transactionId") or ""
    )
    sub.period_start = _ms_to_dt(tx.get("purchaseDate") or tx.get("originalPurchaseDate"))
    expires = _ms_to_dt(tx.get("expiresDate"))
    sub.period_end = expires
    active = expires is None or expires > _now()
    sub.tier = _tier_for_product(str(tx.get("productId", ""))) if active else "free"
    sub.status = "active" if active else "expired"
    db.flush()
    return sub


def apply_stripe_event(db: Session, event: dict[str, Any]) -> None:
    """Reflect a verified Stripe webhook event into the Subscription row."""
    etype = event.get("type", "")
    obj = event.get("data", {}).get("object", {})

    if etype == "checkout.session.completed":
        user_id = obj.get("client_reference_id")
        if not user_id:
            return
        sub = get_or_create(db, uuid.UUID(str(user_id)))
        sub.source = "stripe"
        sub.tier = "plus"
        sub.status = "active"
        sub.stripe_customer_id = obj.get("customer")
        sub.stripe_subscription_id = obj.get("subscription")
        sub.canceled_at = None
        db.flush()
        return

    if etype in ("customer.subscription.updated", "customer.subscription.deleted"):
        target: Subscription | None = db.scalar(
            select(Subscription).where(Subscription.stripe_subscription_id == obj.get("id"))
        ) or db.scalar(
            select(Subscription).where(Subscription.stripe_customer_id == obj.get("customer"))
        )
        if target is None:
            return
        target.period_end = _ms_to_dt(_s_to_ms(obj.get("current_period_end")))
        if etype == "customer.subscription.deleted" or obj.get("status") in (
            "canceled",
            "unpaid",
            "incomplete_expired",
        ):
            target.status = "canceled"
            target.canceled_at = _now()
            # Plus persists until period end; current_tier handles the revert.
        else:
            target.status = "active"
            target.tier = "plus"
        db.flush()


def _s_to_ms(seconds: Any) -> Any:
    """Stripe sends epoch seconds; our _ms_to_dt expects ms."""
    try:
        return float(seconds) * 1000.0
    except (TypeError, ValueError):
        return None
