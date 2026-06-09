# ADR-002: POC → backend migration strategy

**Status:** Accepted · **Date:** 2026-06-09

## Context

The validated POC (`src/`, 81 tests, ~92% coverage, 100% on tools) is the
load-bearing asset. The mission's hard stop condition: *if migration breaks any of
the 80 tests, stop.* We must move it into `apps/api/src/obelisk_api/` without
changing validated behavior — especially the calorie-floor rail and the under-18 gate.

## Decision

**Mechanical, byte-faithful migration via a one-shot script**, not hand-rewriting:

1. Copy each POC module into a subpackage that matches the mission's layout, renaming
   only where the layout requires it:
   | POC module | New module |
   |-----------|-----------|
   | `models.py` | `obelisk_api/domain/models.py` |
   | `tools.py` | `obelisk_api/tools/deterministic.py` |
   | `coach_tools.py` | `obelisk_api/tools/registry.py` |
   | `planbuilder.py`, `render.py`, `diff.py`, `brief.py` | `obelisk_api/services/*` |
   | `agent.py` | `obelisk_api/agent/loop.py` |
   | `system_prompt.py`, `cost_tracker.py`, `persistence.py` | `obelisk_api/agent/*` |
   | `cli.py` | `obelisk_api/cli.py` |
2. Rewrite **only import lines** via a deterministic remap (`from src.X` → new path),
   plus the `from src import tools` → `from obelisk_api.tools import deterministic as tools`
   aliasing special cases. No logic edits.
3. Port the 4 test files identically, updating imports **and** the monkeypatch string
   targets (`src.persistence.RUNS_DIR` → `obelisk_api.agent.block.RUNS_DIR`, etc.).

The only module rewritten (not copied) is `brief.py` — see [ADR-003](ADR-003-advisor-brief-markdown.md).

## Consequences

- The validated numeric logic is preserved exactly; the 81 tests are the proof.
- A future reader sees a clean subpackage layout, not a flat dump.
- `persistence.Block` (JSON-file state) survives as the agent's in-memory working
  set; the DB layer ([ADR-005](ADR-005-plan-persistence.md)) wraps it rather than
  replacing the agent loop. Documented honestly in `docs/poc_handoff.md`.
