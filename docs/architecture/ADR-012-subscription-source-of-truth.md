# ADR-012: Subscription state source-of-truth

**Status:** Accepted · **Date:** 2026-06-09

## Context

PRD §2.6: Plus is sold via Apple StoreKit 2 on iOS and Stripe on desktop, but a purchase
on either platform must unlock Plus everywhere. We need one authoritative tier the API can
read on every request, and receipts must be validated server-side, never trusted from the
client.

## Decision

- **One `Subscription` row per user is the single source of truth.** `tier` (`free`/`plus`)
  is read from this row on authenticated requests that gate features; platform billing is
  an *input* that updates it, not the truth itself.
- **Apple:** the app sends the verified StoreKit 2 transaction to
  `POST /v1/subscription/apple/verify`; the backend validates with the App Store Server API
  and upserts the row keyed by `apple_original_transaction_id`.
- **Stripe:** `POST /v1/subscription/stripe/checkout` returns a Checkout URL; the
  authoritative update arrives via the signature-verified `/v1/webhooks/stripe` handler,
  keyed by `stripe_customer_id` / `stripe_subscription_id`.
- **Cross-platform unlock** falls out for free: both paths write the same per-user row, so
  the tier is identical on iOS and desktop.
- **Cancellation** is one-tap with zero retention friction (PRD §15.3): iOS deep-links to
  Manage Subscriptions, desktop opens the Stripe Customer Portal; the row flips to
  `canceled` and downgrades at `period_end`.
- **Credential-gated, not stubbed-wrong.** Until Apple/Stripe keys are provisioned the
  verify/checkout/webhook handlers are present but guarded by config; absence of keys
  yields a clear 503, never a silent "trust the client."

## Consequences

- Feature gating is one indexed row read; no per-request call to Apple/Stripe.
- The webhook is the trusted channel for Stripe state; the Checkout redirect is not.
- Trade-off: a brief lag between an Apple/Stripe event and our row update is possible
  (webhook latency / app re-verify on launch); acceptable for a monthly subscription.
