# Obelisk API

FastAPI backend wrapping the validated **Block Coach** agent (migrated from the POC —
see [`docs/poc_handoff.md`](../../docs/poc_handoff.md)). Python 3.11+, managed by `uv`.

## Layout

```
src/obelisk_api/
├── domain/      # Pydantic domain models (Athlete, CyclePlan, PlanDiff)
├── tools/       # deterministic.py (numerics) + registry.py (agent tool specs + dispatch)
├── services/    # planbuilder, render, diff, brief (Advisor Brief loader)
├── agent/       # loop.py (tool-use loop), system_prompt, cost_tracker, block (in-memory state)
├── db/          # SQLAlchemy models + session
├── auth/        # Clerk JWT verification
├── routes/      # /v1 endpoints
└── main.py      # FastAPI app
alembic/         # migrations
tests/           # ported POC suite (81 tests) + API tests
```

## Develop

```bash
uv sync --extra dev                 # create .venv, install deps + project
uv run pytest --cov=obelisk_api     # the migrated POC suite must stay green
uv run ruff check . && uv run black --check . && uv run mypy src
uv run uvicorn obelisk_api.main:app --reload   # http://localhost:8000  (/docs for OpenAPI)
```

The agent needs `ANTHROPIC_API_KEY`; the API needs `DATABASE_URL` and `CLERK_*`
(see the repo-root `.env.example`). Deterministic tests run without any keys.

## Offline demo (no API key)

```bash
uv run obelisk demo-offline --athlete data/sample_athlete.json
```
