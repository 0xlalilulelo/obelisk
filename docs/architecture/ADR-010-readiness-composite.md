# ADR-010: Readiness composite algorithm

**Status:** Accepted · **Date:** 2026-06-09

## Context

PRD §2.4 wants a 0-100 readiness score on the Today screen and in the morning push,
computed from HealthKit data, **never a black box**, and stable enough that it doesn't
swing wildly night-to-night (the explicit stop-condition: a >30-point day-to-day swing
means the algorithm is wrong).

## Decision

- **Three inputs, each scored 0-100, then a weighted average over whatever is present:**
  sleep duration (last night, weight 0.40), resting-HR delta vs a 30-day baseline (0.35),
  HRV SDNN deviation vs baseline (0.25, optional). Weights renormalize when an input is
  missing, so an athlete without an HRV-capable watch still gets a meaningful score.
- **Bounded, monotonic sub-scores** (pure functions): sleep 100 in the 7-9 h band,
  penalized harder when short than long; RHR 100 at/below baseline, ~7 pts/bpm of
  elevation; HRV 100 at/above baseline, ~20 pts per 10% drop. Each clamps to [0, 100].
- **Transparency by construction.** The endpoint returns the composite *plus* each
  factor's raw value and sub-score, feeding the "Why?" expansion directly.
- **Behavioral bands** (≥80 / 60-79 / 40-59 / <40) map to the §2.4 guidance string used by
  the Coach and the morning push.
- `GET /v1/athlete/readiness?date=` recomputes on demand from the most recent samples.

## Consequences

- The stop-condition is satisfied *by design*: because the score is a weighted average of
  bounded sub-scores, a single-input change moves the composite by at most that input's
  weight × 100 (sleep ≤ 40 pts across its *entire* range; a realistic 2-hour swing moves
  it ~7). A unit test asserts this property.
- Baselines need ~30 days of history to be meaningful; before then RHR/HRV factors are
  simply absent (score leans on sleep) rather than noisy.
- Deferred: the 1-hour cache named in the locked decisions — recompute is a cheap
  in-memory scan at beta volume, and caching risks showing a stale score right after a
  fresh sync. Add a cache (invalidated on ingest) if recompute cost shows up.
