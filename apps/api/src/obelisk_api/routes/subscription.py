"""Subscription routes (PRD §2.6, ADR-012). Stripe/Apple calls are gated by config
so the suite stays green without live billing credentials; absence of keys yields a
clear 503 rather than trusting the client."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from obelisk_api.auth.clerk import require_user
from obelisk_api.config import get_settings
from obelisk_api.db.base import get_db
from obelisk_api.db.models import User
from obelisk_api.domain.schemas import (
    AppleVerifyIn,
    CheckoutOut,
    StripeCheckoutIn,
    SubscriptionOut,
)
from obelisk_api.ratelimit import limiter
from obelisk_api.services import analytics, apple, subscription

router = APIRouter(tags=["subscription"])


@router.get("/subscription", response_model=SubscriptionOut)
@limiter.limit("60/minute")
def get_subscription(
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> SubscriptionOut:
    sub = subscription.get_or_create(db, user.id)
    return SubscriptionOut.model_validate(sub)


@router.post("/subscription/apple/verify", response_model=SubscriptionOut)
@limiter.limit("30/minute")
def verify_apple(
    request: Request,
    payload: AppleVerifyIn,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> SubscriptionOut:
    """Verify a StoreKit 2 transaction server-side and update the subscription."""
    try:
        tx = apple.decode_transaction(payload.signed_transaction)
    except apple.AppleVerificationUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed transaction"
        ) from exc
    sub = subscription.apply_apple_transaction(db, user.id, tx)
    if sub.tier == "plus" and sub.status == "active":
        analytics.capture(str(user.id), "subscription_purchased", {"source": "apple"})
    return SubscriptionOut.model_validate(sub)


@router.post("/subscription/stripe/checkout", response_model=CheckoutOut)
@limiter.limit("30/minute")
def stripe_checkout(
    request: Request,
    payload: StripeCheckoutIn,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> CheckoutOut:
    """Create a Stripe Checkout session for Plus and return its URL."""
    settings = get_settings()
    price = (
        settings.stripe_price_annual if payload.plan == "annual" else settings.stripe_price_monthly
    )
    if not settings.stripe_secret_key or not price:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not configured.",
        )
    import stripe

    stripe.api_key = settings.stripe_secret_key
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price, "quantity": 1}],
        client_reference_id=str(user.id),
        success_url=settings.stripe_success_url,
        cancel_url=settings.stripe_cancel_url,
        customer_email=user.email or None,  # type: ignore[arg-type]
    )
    return CheckoutOut(url=session.url or "")


# Webhook lives under /v1/webhooks/stripe (no auth — verified by signature).
webhook_router = APIRouter(tags=["subscription"])


@webhook_router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)) -> dict[str, bool]:
    settings = get_settings()
    if not settings.stripe_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe webhooks are not configured.",
        )
    import stripe

    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(  # type: ignore[no-untyped-call]
            payload, sig, settings.stripe_webhook_secret
        )
    except Exception as exc:  # signature mismatch / malformed
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook signature"
        ) from exc
    subscription.apply_stripe_event(db, dict(event))
    return {"received": True}
