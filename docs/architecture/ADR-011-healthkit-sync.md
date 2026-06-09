# ADR-011: HealthKit sync architecture

**Status:** Accepted · **Date:** 2026-06-09

## Context

PRD §2.2 reads body weight, sleep, heart rate, resting HR, HRV, active energy, and
workouts from HealthKit (read-only in Phase 2). HealthKit is on-device only; the backend
never talks to Apple. We need a sync path that's robust to re-delivery and treats the
data as PHI-adjacent.

## Decision

- **Push model: device → backend.** The iOS app reads HealthKit and POSTs batches to
  `POST /v1/wearable/healthkit`. On app open, plus background delivery for the
  low-frequency types (body weight, sleep). Higher-frequency types sync on foreground.
- **Idempotent on the HKObject UUID.** Each sample carries its HealthKit `sample_uuid`;
  the backend stores `dedup_key = "{athlete}:{source}:{sample_uuid}"` with a unique index
  and skips anything already seen. Re-syncing HealthKit's rolling anchor window is a no-op.
- **`WearableSample` table** (source / sample_type / occurred_at / value / unit /
  duration_sec / raw JSONB) is the normalized store; readiness and the Today surfaces read
  from it. `source` is generic so Strava (Phase 3) lands in the same table.
- **PHI-adjacent handling:** values are never logged to stdout/Sentry; only counts.
- **Fallback (per the spec's stop-condition):** if background delivery proves materially
  harder than budgeted, foreground polling is the Phase 2 fallback and background delivery
  moves to Phase 3. The backend contract is identical either way.

## Consequences

- The server stays a pure sink; all Apple-entitlement complexity is client-side.
- Dedup is structural (unique index), so the client may over-send without harm — which is
  exactly what an anchored-query re-sync does.
- Trade-off: read-only means we can't write workouts *back* to Apple Health in Phase 2
  (deferred to Phase 3), accepted per the locked decision.
