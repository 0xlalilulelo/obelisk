# Obelisk API image. Build context = repo root (needs apps/api + docs/advisor_brief.md).
FROM python:3.11-slim AS base

# uv for fast, lockfile-disciplined installs.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app/apps/api

# Dependency layer (cached unless pyproject/lock change).
COPY apps/api/pyproject.toml apps/api/README.md ./
COPY apps/api/uv.lock* ./
RUN uv sync --no-dev --no-install-project

# App source + migrations + the grounding brief.
COPY apps/api/src ./src
COPY apps/api/alembic.ini ./
COPY apps/api/alembic ./alembic
COPY docs/advisor_brief.md /app/docs/advisor_brief.md
RUN uv sync --no-dev

ENV OBELISK_BRIEF_PATH=/app/docs/advisor_brief.md
EXPOSE 8000

# Bind the platform-provided $PORT when set (Railway healthchecks target it),
# falling back to 8000 for local/compose/CI. Shell form so ${PORT} expands.
CMD ["sh", "-c", "uv run uvicorn obelisk_api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
