# ADR-009: Set-log durability & idempotent sync

**Status:** Accepted · **Date:** 2026-06-09

## Context

The In-Session screen (PRD §2.1) is the trust-critical path: an athlete logs sets in a
gym basement with no signal. A dropped or duplicated set is unacceptable. We need an
optimistic local write that survives loss-of-signal and syncs without ever
double-counting on retry.

## Decision

- **On-device queue, server is the merge point.** The iOS client writes each set to
  local storage immediately (SwiftData — see the iOS layer) and enqueues it for sync.
  `POST /v1/log` accepts a *batch* of `LogEntry` rows of type `"set"`.
- **Idempotency = client-generated UUID as the row primary key.** Each set carries a
  device-minted `client_id` that becomes `log_entries.id`. Ingest pre-queries which ids
  already exist and inserts only the rest; a replayed batch (the reconnect case) returns
  `{inserted: 0, duplicates: N}` and mutates nothing. We never *update* an existing row,
  so a `client_id` that collides with another athlete's row is skipped, not overwritten.
- **Reuse `LogEntry`, no new table.** A set's `data` JSON carries
  `{block_id, session_date, exercise, lift_key, set_index, weight_lb, reps, rpe,
  completed}`. Pre-fill and e1RM read back from these rows.
- **Pre-fill** (`GET /v1/blocks/{id}/sessions/{date}`) attaches each exercise's most
  recent *prior* session actuals, matched on `lift_key` (else label).

## Consequences

- Replay-safety is structural (PK conflict), not a dedup heuristic — the gym-basement
  reconnect can re-send the whole queue freely.
- No schema migration for logging; `LogEntry` stays the single append-only history.
- Trade-off: prior-actuals and e1RM scan recent rows in Python (dialect-portable) rather
  than via JSONB path queries. Fine at beta volume; revisit with a generated column or a
  materialized `set_logs` view if scan cost shows up.
