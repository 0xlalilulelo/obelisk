# POC → Backend Handoff

What moved from the validated POC (`/src`, `/tests`) into `apps/api/src/obelisk_api`,
what was rewritten, and what changed. Honest record per the mission's stop conditions.

**Bottom line:** all **81 POC tests pass** against the migrated code (92% coverage),
`mypy --strict` / `ruff` / `black` are clean, and **no validated behavior changed** —
including the two safety rails (calorie floor, under-18 gate), which are byte-identical.

## Verbatim (logic untouched; only import paths rewritten)

A deterministic script (`_migrate.py`, ADR-002) copied these and rewrote *only* import
lines via a dotted-path remap. No statement of logic was edited.

| POC module | New module | Notes |
|-----------|-----------|-------|
| `models.py` | `domain/models.py` | Pydantic domain models — verbatim |
| `tools.py` | `tools/deterministic.py` | The 8 deterministic tools. **`compute_macros` calorie floor `max(BW×10, 1200)` byte-identical.** 100% test coverage retained |
| `coach_tools.py` | `tools/registry.py` | Tool specs + dispatch + diff-then-commit. **`draft_cycle_plan` under-18 gate byte-identical** |
| `planbuilder.py` | `services/planbuilder.py` | `linear_novice`, `marathon_block`, `hybrid_531` builders — verbatim |
| `render.py` | `services/render.py` | xlsx renderer — verbatim |
| `diff.py` | `services/diff.py` | Structured plan diff — verbatim |
| `agent.py` | `agent/loop.py` | The bare tool-use loop — verbatim |
| `system_prompt.py` | `agent/system_prompt.py` | **Safety protocols (7 categories + NEDA/988 + persistence rule) preserved verbatim** in `_OPERATING_INSTRUCTIONS` |
| `cost_tracker.py` | `agent/cost_tracker.py` | Per-call USD/token accounting — verbatim (already had `claude-opus-4-8` pricing) |
| `persistence.py` | `agent/block.py` | In-memory `Block` working set — verbatim |
| `cli.py` | `cli.py` | Offline `demo-offline` harness — verbatim |

Tests (`test_tools`, `test_plan`, `test_agent_layer`, `test_cli`) were ported with the
same remap, plus updated `monkeypatch` string targets
(`src.persistence.RUNS_DIR` → `obelisk_api.agent.block.RUNS_DIR`, etc.).

## Rewritten (one module)

**`brief.py` → `services/brief.py`** (ADR-003). The POC read the `.docx` at runtime via
`python-docx`. The backend reads a versioned Markdown file `docs/advisor_brief.md`
(extracted once by `_extract.py`, preserving heading text so the `1. Role and Mandate` /
`4. Programming Decision Trees` section regexes still match). Everything below the
`load_blocks` parsing seam — `system_prompt_source`, `_chunks`, `search` — is unchanged.
`python-docx` is no longer a backend runtime dependency. Verified by
`test_system_prompt_includes_brief_and_athlete` (asserts `Role and Mandate` survives).

## Changed / deferred (and why)

- **`runs/` paths.** `Block.RUNS_DIR` now resolves relative to the package, not the repo
  root. Irrelevant to tests (they monkeypatch it) and to `demo-offline` (CWD-relative).
  Superseded by DB persistence (ADR-005); the JSON-file path remains only for the CLI.
- **No behavior, no numbers, no prompts changed.** The 5 known rounding tie-breaks vs.
  the reference workbook (documented in the POC README) are unchanged.

## Not yet wired (next steps in this phase)

- DB-backed persistence around the in-memory `Block` (`db/`, Alembic) — ADR-005.
- Clerk JWT auth dependency (`auth/`) — ADR-004.
- `/v1` routes + SSE chat (`routes/`, `main.py`) — ADR-006.
- Artifact upload to S3/R2 (Phase 1 stubs the pre-signed URL).

## Reproduce

```bash
cd apps/api && uv sync --extra dev
uv run pytest --cov=obelisk_api      # 81 passed, ~92%
uv run ruff check . && uv run black --check . && uv run mypy src
```
