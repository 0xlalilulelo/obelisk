# ADR-001: Monorepo structure & toolchain

**Status:** Accepted · **Date:** 2026-06-09

## Context

Phase 1 ships three surfaces (Python backend, Tauri desktop, SwiftUI iOS) plus
shared TypeScript packages. The locked stack (PRD §10) mandates pnpm workspaces +
Turborepo for TS and `uv` for Python. Swift/Xcode is its own world.

## Decision

A single repo with three coexisting build systems, each owning its subtree:

- **pnpm + Turborepo** own `apps/desktop` and `packages/*` (declared in
  `pnpm-workspace.yaml`). Root scripts (`pnpm dev/build/lint/test`) fan out via Turbo.
- **`uv`** owns `apps/api` as an isolated Python project (`apps/api/pyproject.toml`,
  its own lockfile). It is intentionally **not** a pnpm workspace member.
- **Xcode** owns `apps/ios`. Not wired into pnpm/uv; built by `xcodebuild` in CI.

`packages/`: `types` (shared domain TS types), `design-tokens` (the Stitch palette/
type scale, consumed by desktop and hand-translated for iOS), `api-client` (typed
client generated from the backend OpenAPI spec).

## Consequences

- Each surface builds, tests, and lints independently; CI has one workflow per surface.
- No single "install everything" command — root README documents `pnpm install` **and**
  `uv sync` as separate steps. Acceptable for a 3-runtime repo.
- Cross-surface type safety flows one direction: backend Pydantic → OpenAPI →
  `packages/api-client` / `packages/types` → desktop. iOS mirrors by hand (ADR pending).
