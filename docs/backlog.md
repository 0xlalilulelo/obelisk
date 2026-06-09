# Backlog — tracked follow-ups

Known limitations and deferred work, captured so they aren't lost. Each item notes
the root cause and what "done" looks like. Promote to an issue/PR when picked up.

---

## BL-001 — Plan duration is template-intrinsic, not a requested parameter

**Severity:** Medium · **Surfaced:** 2026-06-09 (Phase 1 testing) · **Status:** Open

**Symptom.** An athlete asked for a *"12-week strength + aerobic base"* block and got a
**16-week** plan. The free-text "12-week" in the goal was not honored as a constraint.

**Root cause.** In the migrated POC planner, each program builder has a **hard-coded
length**, and the agent picks a *model*, not a duration:

| `program_model` | Builder | Length |
|---|---|---|
| `hybrid_531` | `build_default_plan` | 12 wk (3 waves) |
| `linear_novice` | `build_linear_novice_plan` | 16 wk (4 waves) |
| `marathon_block` | `build_endurance_block_plan` | 16 wk (4 waves) |

`draft_cycle_plan` has no `weeks`/`duration` argument, and the builders
(`apps/api/src/obelisk_api/services/planbuilder.py`) don't accept one. So a requested
duration only "works" when it happens to match the chosen template's fixed length.

> Note: the *immediate* report was compounded by onboarding not collecting 1RMs (fixed
> 2026-06-09 — the New-Block wizard now has an optional "Tested lifts" step, so a
> strength athlete with 1RMs routes to the 12-week `hybrid_531`). This BL item is the
> *remaining* structural limitation: arbitrary durations still aren't supported.

**Done looks like.**
- `draft_cycle_plan` accepts an optional `target_weeks` (validated range, e.g. 8–20).
- Each builder parameterizes wave count / phase lengths from `target_weeks` instead of a
  constant, preserving the validated loading schemes (deload cadence, taper, etc.).
- The agent honors an explicit duration in the athlete's request, or explains why it
  can't (e.g. "a marathon base needs ≥16 wk").
- Tests: a parametrized planbuilder test asserting wave/week counts for a few durations,
  per program model. Update `docs/poc_handoff.md` if validated numbers shift.

**Why deferred.** Touches the validated numeric core (the 271/276 byte-identical
reproduction); wants careful, separately-tested work rather than a Phase-1 bolt-on.
