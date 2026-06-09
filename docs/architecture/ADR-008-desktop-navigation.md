# ADR-008: Desktop navigation — Zustand shell now, TanStack Router later

**Status:** Accepted · **Date:** 2026-06-09

## Context

The locked component architecture (PRD-derived) names TanStack Router (file-based)
for the desktop app. In practice the Phase 1 desktop is a **single Tauri window** with
a persistent three-pane shell; no acceptance criterion needs URL routing, deep links,
or multiple pages. The Stitch mocks are one app surface with switchable center tabs.

## Decision

Phase 1 drives in-shell navigation (active Block, center tab, modal/palette open,
pending diff) with a small **Zustand** store — the locked choice for client state.
**TanStack Router is deferred** until there's a real routing need (multi-window,
deep links to a Block/day, shareable URLs), at which point block selection moves from
Zustand state to route params. The dependency is removed now rather than shipped unused.

This follows the project's stated default for unresolved details: pick the simplest,
most reversible option and document it.

## Consequences

- Less moving machinery in Phase 1; the shell renders reliably with no route codegen.
- Reversible: `activeBlockId`/`activeTab` are already isolated in the store, so swapping
  to route-param-driven navigation is a contained change.
- No browser back/forward or URL deep-linking until Phase 2 (acceptable for a desktop
  shell).
