# ADR-006: Chat streaming over SSE

**Status:** Accepted · **Date:** 2026-06-09

## Context

`POST /v1/blocks/{id}/chat` runs the agent's tool loop, which can take seconds and
several tool round-trips. The POC's "What surprised me" notes flagged latency tracking
output length and recommended streaming. Both desktop and iOS must consume the stream.

## Decision

- Stream responses via **Server-Sent Events** (`text/event-stream`), not WebSockets —
  the channel is one-directional (server → client) per turn, and SSE is trivial to
  consume from both `EventSource`-style clients and a Swift `URLSession.bytes` reader.
- Event protocol (named events, JSON data):
  - `token` — incremental assistant text deltas.
  - `tool_use` — a tool was invoked (name only; for the "thinking" UI).
  - `plan_edit` — a staged edit was produced; carries `edit_id` + the diff, so the
    desktop right-pane can swap to the Diff viewer.
  - `done` — final turn metadata: `message_id`, `cost_usd`, `tokens_in/out`, `latency_ms`.
  - `error` — terminal error with a user-safe message.
- The endpoint persists the user message, runs the loop, emits events as blocks arrive,
  and writes the assistant `Message` row (with cost) before `done`.

## Consequences

- Clients render tokens as they arrive; the largest call no longer blocks the UI.
- No background job system needed — the request is held open for the turn (locked
  decision: chat is synchronous request/response, no Celery/SQS in MVP).
- Reconnect/resume is out of scope for Phase 1; a dropped stream re-fetches via
  `GET /v1/blocks/{id}/messages`.
