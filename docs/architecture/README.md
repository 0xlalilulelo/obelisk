# Architecture Decision Records

Tiny, append-only records of decisions that shape Obelisk. One screen each:
**Context → Decision → Consequences.** Supersede rather than rewrite.

| ADR | Title | Status |
|-----|-------|--------|
| [001](ADR-001-monorepo-structure.md) | Monorepo structure & toolchain | Accepted |
| [002](ADR-002-poc-migration.md) | POC → backend migration strategy | Accepted |
| [003](ADR-003-advisor-brief-markdown.md) | Advisor Brief as a versioned Markdown source | Accepted |
| [004](ADR-004-auth-clerk.md) | Authentication via Clerk | Accepted |
| [005](ADR-005-plan-persistence.md) | Plan persistence & event-sourced edits | Accepted |
| [006](ADR-006-chat-streaming-sse.md) | Chat streaming over SSE | Accepted |
| [007](ADR-007-ios-scaffold-on-windows.md) | iOS scaffolded & CI-verified (no local Mac) | Accepted |
| [008](ADR-008-desktop-navigation.md) | Desktop navigation — Zustand shell, Router deferred | Accepted |

Locked stack decisions originate in PRD §10 + §15.1 and are not re-litigated here;
these ADRs record the *implementation* choices made while building Phase 1.
