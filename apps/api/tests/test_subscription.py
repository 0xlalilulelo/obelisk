"""Subscription source-of-truth: Apple decode/apply, Stripe events, tier reverts."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from obelisk_api.db.models import User
from obelisk_api.services import subscription
from tests.conftest import JOSH_PROFILE

pytestmark = pytest.mark.integration

Client = tuple[TestClient, Callable[[str], None]]

FUTURE_MS = int((datetime.now(UTC) + timedelta(days=30)).timestamp() * 1000)
PAST_MS = int((datetime.now(UTC) - timedelta(days=1)).timestamp() * 1000)


def _storekit_jws(product: str, expires_ms: int) -> str:
    """A decode-only StoreKit-style JWS (signature ignored in dev)."""
    return jwt.encode(
        {
            "productId": product,
            "originalTransactionId": "1000000",
            "purchaseDate": FUTURE_MS - 31 * 24 * 3600 * 1000,
            "expiresDate": expires_ms,
        },
        "test-secret",
        algorithm="HS256",
    )


# --- Endpoint: default + Apple verify --------------------------------------
def test_subscription_defaults_to_free(client: Client) -> None:
    c, _ = client
    c.post("/v1/athlete/profile", json=JOSH_PROFILE)
    body = c.get("/v1/subscription").json()
    assert body["tier"] == "free"
    assert body["status"] == "active"


def test_apple_verify_grants_plus(client: Client) -> None:
    c, _ = client
    c.post("/v1/athlete/profile", json=JOSH_PROFILE)
    jws = _storekit_jws("obelisk.plus.monthly", FUTURE_MS)
    resp = c.post("/v1/subscription/apple/verify", json={"signed_transaction": jws})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["tier"] == "plus"
    assert body["status"] == "active"
    assert body["source"] == "apple"
    # And the tier sticks on the next read.
    assert c.get("/v1/subscription").json()["tier"] == "plus"


def test_apple_verify_expired_is_free(client: Client) -> None:
    c, _ = client
    c.post("/v1/athlete/profile", json=JOSH_PROFILE)
    jws = _storekit_jws("obelisk.plus.monthly", PAST_MS)
    body = c.post("/v1/subscription/apple/verify", json={"signed_transaction": jws}).json()
    assert body["tier"] == "free"
    assert body["status"] == "expired"


def test_apple_verify_rejects_garbage(client: Client) -> None:
    c, _ = client
    c.post("/v1/athlete/profile", json=JOSH_PROFILE)
    resp = c.post("/v1/subscription/apple/verify", json={"signed_transaction": "not-a-jws"})
    assert resp.status_code == 400


def test_stripe_checkout_503_without_config(client: Client) -> None:
    c, _ = client
    c.post("/v1/athlete/profile", json=JOSH_PROFILE)
    resp = c.post("/v1/subscription/stripe/checkout", json={"plan": "monthly"})
    assert resp.status_code == 503


def test_stripe_webhook_503_without_secret(client: Client) -> None:
    c, _ = client
    resp = c.post("/v1/webhooks/stripe", json={"type": "x"})
    assert resp.status_code == 503


# --- Service: Stripe events + tier reversion -------------------------------
def _make_user(session_factory: sessionmaker[Session]) -> tuple[Session, User]:
    db = session_factory()
    user = User(clerk_user_id="stripe_user", email="s@example.com")
    db.add(user)
    db.flush()
    return db, user


def test_stripe_checkout_completed_grants_plus(
    session_factory: sessionmaker[Session],
) -> None:
    db, user = _make_user(session_factory)
    subscription.apply_stripe_event(
        db,
        {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "client_reference_id": str(user.id),
                    "customer": "cus_1",
                    "subscription": "sub_1",
                }
            },
        },
    )
    assert subscription.current_tier(db, user) == "plus"


def test_subscription_deleted_reverts_after_period_end(
    session_factory: sessionmaker[Session],
) -> None:
    db, user = _make_user(session_factory)
    subscription.apply_stripe_event(
        db,
        {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "client_reference_id": str(user.id),
                    "customer": "cus_2",
                    "subscription": "sub_2",
                }
            },
        },
    )
    # Cancellation with a period end in the past → reverts to free now.
    subscription.apply_stripe_event(
        db,
        {
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "id": "sub_2",
                    "customer": "cus_2",
                    "status": "canceled",
                    "current_period_end": int((datetime.now(UTC) - timedelta(days=1)).timestamp()),
                }
            },
        },
    )
    assert subscription.current_tier(db, user) == "free"


def test_unknown_user_id_is_ignored(session_factory: sessionmaker[Session]) -> None:
    db = session_factory()
    # Should not raise even with an unrelated event.
    subscription.apply_stripe_event(
        db,
        {"type": "customer.subscription.updated", "data": {"object": {"id": str(uuid.uuid4())}}},
    )
