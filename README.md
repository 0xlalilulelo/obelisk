# Obelisk

**AI-native performance coaching.** Obelisk pairs an athlete with a *Block Coach* —
a single Claude agent, grounded in a strength-and-conditioning advisor brief and
equipped with deterministic tools, that designs and conversationally refines a
periodized training cycle (a "Block"). Every prescribed number comes from a tool,
every recommendation cites its reasoning, and plan changes go through a
diff-then-commit approval gate. The agent is validated across three athlete types
and a 14-scenario safety battery (see [`docs/poc_handoff.md`](docs/poc_handoff.md)).

This repository is the Phase 1 foundation: a deployed backend, a desktop app, and
an iOS app, in clearly separated workspaces.

## Monorepo layout

```
apps/
  api/        Python · FastAPI · the Block Coach as a service (migrated from the POC)
  desktop/    Tauri 2 · React 18 · TypeScript · Vite — the three-pane "performance lab"
  ios/        Swift · SwiftUI (iOS 17+) — scaffolded; built in CI on macOS (ADR-007)
packages/
  types/          shared TS domain types (Athlete, Block, Session, …)
  design-tokens/  the Stitch palette/type scale (desktop + iOS-translated)
  api-client/     typed client generated from the backend OpenAPI spec
docs/
  architecture/   ADRs — every decision, one screen each
  advisor_brief.md  the canonical grounding source (read by the agent)
  poc_handoff.md    what migrated from the POC, what changed
  stitch/           design mocks (visual reference)
infra/          Dockerfile · docker-compose.dev.yml
```

Three toolchains coexist (ADR-001): **pnpm + Turborepo** for `apps/desktop` and
`packages/*`, **`uv`** for `apps/api`, **Xcode** for `apps/ios`.

## Get running in 10 minutes

Prerequisites: Node 20+ & pnpm, Python 3.11+ & [`uv`](https://docs.astral.sh/uv/),
Docker, and a Rust toolchain (for the Tauri desktop shell).

```bash
# 1. Clone + install JS deps
git clone <repo> && cd obelisk
pnpm install

# 2. Configure secrets
cp .env.example .env
#   Fill in ANTHROPIC_API_KEY and the CLERK_* keys (Clerk dashboard).

# 3. Database (Postgres 16 + pgvector) + migrations
docker compose -f infra/docker-compose.dev.yml up -d        # brings up db + runs Alembic
#   …or run migrations from the host:
cd apps/api && uv sync --extra dev && uv run alembic upgrade head

# 4. Backend → http://localhost:8000  (OpenAPI at /docs)
uv run uvicorn obelisk_api.main:app --reload

# 5. Desktop (new terminal) → opens the Tauri window at http://localhost:1420
cd apps/desktop && pnpm dev
```

The deterministic backend tests need **no** keys: `cd apps/api && uv run pytest`.

## Per-surface docs

- Backend: [`apps/api/README.md`](apps/api/README.md)
- Desktop: [`apps/desktop/README.md`](apps/desktop/README.md)
- iOS: [`apps/ios/README.md`](apps/ios/README.md)
- Architecture decisions: [`docs/architecture/`](docs/architecture/README.md)

## Status (Phase 1)

| Surface | State |
|---------|-------|
| Backend | ✅ POC migrated (97 tests green, ~93% cov), `/v1` API, Clerk auth, SSE chat, Alembic |
| Desktop | three-pane shell, Clerk sign-in, New-Block quiz, Plan tab, Coach (SSE), Diff viewer |
| iOS | scaffolded; CI-built (ADR-007) |
| CI | per-surface GitHub Actions; PRs gated |
