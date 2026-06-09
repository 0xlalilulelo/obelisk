# ADR-004: Authentication via Clerk

**Status:** Accepted · **Date:** 2026-06-09 · Locked by PRD §15.1

## Context

Phase 1 needs Apple ID + Google + email-magic-link sign-in across desktop and iOS
without spending the security budget to build auth. The stack locks Clerk.

## Decision

- **Clerk is the identity source of truth.** Backend never stores passwords.
- **Backend** validates the Clerk-issued JWT on every `/v1/*` request except
  `/v1/healthz`. It fetches Clerk's JWKS (cached) keyed off `CLERK_ISSUER`, verifies
  signature/exp/iss, extracts `sub` as `clerk_user_id`, and **upserts a `User` row on
  first sight** (the local mirror in the schema). A FastAPI dependency
  (`require_user`) yields the `User` and 401s on any failure.
- **Desktop** uses `@clerk/clerk-react`; **iOS** uses the official Clerk iOS SDK. Both
  send the session JWT as `Authorization: Bearer <jwt>`.
- Publishable key ships to clients via `VITE_CLERK_PUBLISHABLE_KEY`; the secret key
  stays server-side.

## Consequences

- No custom auth surface to secure or test in Phase 1.
- Local dev and CI cannot complete a real interactive sign-in without Clerk keys;
  backend tests therefore inject a fake verifier and assert the dependency contract,
  not a live token exchange.
- Migrating off Clerk later means re-homing the `users` table and swapping the verifier
  dependency — the rest of the app depends only on the local `User`, not on Clerk types.
