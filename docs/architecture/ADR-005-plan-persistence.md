# ADR-005: Plan persistence & event-sourced edits

**Status:** Accepted · **Date:** 2026-06-09

## Context

The POC stored a Block as JSON files under `runs/<id>/` and kept the canonical plan
at the *template* level (`CyclePlan`). Two OOD bugs (4 & 5) came from edits clobbering
each other and from losing the staged-vs-committed distinction. Phase 1 moves to
Postgres while preserving the validated diff-then-commit flow.

## Decision

- **`blocks.plan_json` (JSONB)** holds the canonical `CyclePlan`, mutated only by tools.
- **`plan_edits`** is an append-only, event-sourced log: each targeted edit
  (`swap_lift` / `override_week` / `set_day_across_weeks`) is a row with `staged=true`
  and the *minimal* mutation payload. `commit` flips `staged=false`, stamps
  `committed_at`, and applies the mutation to `plan_json`. Rejection deletes/voids the
  staged row. This is the durable form of the POC's `pending_plan`.
- The agent loop still operates on an in-memory `Block` (`agent/block.py`); a repository
  hydrates it from Postgres before a turn and persists `plan_json` + new `plan_edits` +
  `messages` after. Staged edits accumulate from `pending_plan` first (the bug-4/5 fix),
  exactly as validated.
- `messages` rows record `tokens_in/out`, `cost_usd`, `latency_ms` per the cost tracker.

## Consequences

- The diff timeline is queryable (`plan_edits(block_id, created_at)`); "show me the last
  change" is a row read, not a re-diff.
- `plan_json` stays compact (template-level), keeping agent token cost low as validated.
- Trade-off: applying a committed edit mutates `plan_json` in place, so the edit log is
  the audit trail, not a full plan-version history. Full versioned snapshots deferred.
