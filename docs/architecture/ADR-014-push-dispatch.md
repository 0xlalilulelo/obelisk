# ADR-014: Push notification dispatch strategy

**Status:** Accepted · **Date:** 2026-06-09

## Context

PRD §2.3 wants a daily morning ping, a Sunday recap, and event-triggered pushes,
with hard anti-spam rules (one/day, quiet hours 10pm–6am, defer-if-unopened) and a
content rule (§6.6: every notification ties to a number that changed). Apple's
native flow (APNs) is the locked transport. None of it can be exercised without
APNs credentials + a device.

## Decision

- **In-process APScheduler** (Phase 2), not an external worker: an hourly morning
  tick and a Sunday-evening recap tick, registered in `create_app` **only when
  `push_scheduler_enabled`**. Extraction to a worker is a Phase-3 option.
- **Policy and content are pure functions** (`services/push`): quiet-hours
  (midnight-wrapping), `should_send_morning` (one/day + defer-if-unopened), and the
  morning/recap content builders that take the changed number as an argument. These
  are unit-tested; the scheduler just wires them to the DB + transport.
- **APNs via aioapns, gated.** `send_push` is a no-op (returns False, never raises)
  unless the APNs key/team/topic are configured — so the app and tests run without
  credentials.
- **Device token + prefs** live on `AthleteProfile`; `POST /v1/notifications/register`
  stores the token (never echoed back — treated like a credential) and
  `GET/PATCH /v1/notifications/preferences` manage cadence + quiet hours.

## Consequences

- The trust-sensitive logic (when/what to send) is testable without APNs; the
  untestable part (the wire send) is a thin gated shim.
- **Before production enablement** (tracked in the scheduler docstring): durable
  per-athlete send-state columns (`last_morning_sent_at` / `last_opened_at`) so the
  one/day and defer-if-unopened rules survive process restarts, and timezone-correct
  local-time scheduling (the tick currently compares against UTC). Until then the
  flag stays off.
- Quiet hours + one/day cap + the §6.6 "tie to a number" rule are enforced in the
  content/policy layer, not left to the caller.
