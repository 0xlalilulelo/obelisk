"""Agent-facing tool registry: Anthropic function-calling specs + dispatch.

Two groups of tools:

* **Deterministic** (``obelisk_api.tools.deterministic``): the pure numeric/lookup functions. Every
  number the coach uses comes from one of these.
* **Plan lifecycle** (stateful, bound to a :class:`~obelisk_api.agent.block.Block`):
  draft the cycle, read it, propose an update (returns a diff), commit after
  approval. These enforce the diff-before-commit gate.
"""

from __future__ import annotations

import json
from typing import cast

from obelisk_api.agent.block import Block
from obelisk_api.domain.models import CyclePlan, DayType, TemplateName, TrainingBlock, TrainingDay
from obelisk_api.services.diff import compute_plan_diff, format_diff
from obelisk_api.services.planbuilder import (
    build_default_plan,
    build_endurance_block_plan,
    build_linear_novice_plan,
)
from obelisk_api.services.render import render_plan
from obelisk_api.tools import deterministic as tools

ToolSpec = dict[str, object]

_TEMPLATE_NAMES = ["531_bbb", "rat6", "juggernaut", "tactical_barbell_operator"]
_DAY_TYPES = ["rest", "light", "moderate", "hard"]


def tool_specs() -> list[ToolSpec]:
    """Return all tool definitions in Anthropic function-calling format."""
    return [
        {
            "name": "compute_1rm",
            "description": "Epley estimated 1RM from a rep test, rounded to 5 lb.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "weight_lb": {"type": "number"},
                    "reps": {"type": "integer", "minimum": 1},
                },
                "required": ["weight_lb", "reps"],
            },
        },
        {
            "name": "compute_training_max",
            "description": "Training max = conservatism × est 1RM, rounded to 5 lb. "
            "Default conservatism 0.85 (Brief: ≤85% of 1RM most weeks).",
            "input_schema": {
                "type": "object",
                "properties": {
                    "est_1rm": {"type": "integer"},
                    "conservatism": {"type": "number", "default": 0.85},
                },
                "required": ["est_1rm"],
            },
        },
        {
            "name": "compute_macros",
            "description": "Renaissance-scheme macros for a bodyweight and training-day type.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "bw_lb": {"type": "number"},
                    "day_type": {"type": "string", "enum": _DAY_TYPES},
                },
                "required": ["bw_lb", "day_type"],
            },
        },
        {
            "name": "compute_maf",
            "description": "Maffetone aerobic HR cap = 180 − age.",
            "input_schema": {
                "type": "object",
                "properties": {"age": {"type": "integer"}},
                "required": ["age"],
            },
        },
        {
            "name": "get_periodization_template",
            "description": "Weekly loading scheme + recommended split for a named template.",
            "input_schema": {
                "type": "object",
                "properties": {"name": {"type": "string", "enum": _TEMPLATE_NAMES}},
                "required": ["name"],
            },
        },
        {
            "name": "compute_warmup_ramp",
            "description": "Prescribed working weight for a week (1-4) and set (1-3) of a "
            "5/3/1 wave, given the training max.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "tm": {"type": "integer"},
                    "week": {"type": "integer", "minimum": 1, "maximum": 4},
                    "set_num": {"type": "integer", "minimum": 1, "maximum": 3},
                },
                "required": ["tm", "week", "set_num"],
            },
        },
        {
            "name": "lookup_advisor_principle",
            "description": "Keyword search over the Advisor Brief; returns the best-matching "
            "section. Use to ground and cite recommendations.",
            "input_schema": {
                "type": "object",
                "properties": {"topic": {"type": "string"}},
                "required": ["topic"],
            },
        },
        {
            "name": "draft_cycle_plan",
            "description": (
                "Build and render the initial cycle from the athlete baseline, then explain it. "
                "FIRST choose the right program_model for THIS athlete — do not default:\n"
                "• 'hybrid_531' — concurrent strength + conditioning, 5/3/1 BBB, 12 wk. For "
                "athletes with KNOWN barbell 1RMs pursuing strength alongside endurance/climbing.\n"
                "• 'linear_novice' — Practical-Programming novice tier: linear per-session strength "
                "(no TMs/%s), couch-to-5K run/walk build, ruck progression, 16 wk. For beginners "
                "with NO tested 1RMs. Never fabricate 1RMs for these athletes.\n"
                "• 'marathon_block' — Pfitzinger-style base/build/peak/taper, polarized 80/20, "
                "strength demoted to Easy Strength maintenance, 16 wk. For endurance-priority "
                "runners. Pass current_weekly_mileage-derived peak_mileage + long_run_peak_mi.\n"
                "priority_lifts (hybrid only) emphasizes a lift (e.g. ['bench_press'])."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "program_model": {
                        "type": "string",
                        "enum": ["hybrid_531", "linear_novice", "marathon_block"],
                    },
                    "title": {"type": "string"},
                    "goals": {"type": "array", "items": {"type": "string"}},
                    "priority_lifts": {"type": "array", "items": {"type": "string"}},
                    "peak_mileage": {"type": "integer", "description": "marathon_block peak mpw"},
                    "long_run_peak_mi": {
                        "type": "integer",
                        "description": "marathon_block long-run peak",
                    },
                    "deficit": {
                        "type": "boolean",
                        "description": "linear_novice: modest cut for fat loss",
                    },
                },
                "required": ["program_model", "title", "goals"],
            },
        },
        {
            "name": "get_plan_json",
            "description": "Return a compact summary of the current plan (read-only): program "
            "model, phases, per-week day→session map, training-max + nutrition headlines. Use it "
            "to answer questions or decide an edit; the targeted edit tools don't need the full "
            "block-level detail.",
            "input_schema": {"type": "object", "properties": {}},
        },
        {
            "name": "swap_lift",
            "description": "Stage a swap of the main lift on a given day (e.g. deadlift → trap "
            "bar deadlift). Returns a what-was/what-will-be diff; does NOT commit. ``scope`` is "
            "'whole_cycle' or 'wave_1'/'wave_2'/'wave_3' (use wave_1 for 'the first 4 weeks'). "
            "If the new lift's est 1RM differs, pass new_est_1rm; otherwise the existing training "
            "max carries over. Show the diff and get approval before commit.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "scope": {
                        "type": "string",
                        "enum": ["whole_cycle", "wave_1", "wave_2", "wave_3"],
                    },
                    "day": {"type": "string", "description": "Mon/Tue/Wed/Thu/Fri/Sat/Sun"},
                    "new_lift_key": {"type": "string"},
                    "new_display_name": {"type": "string"},
                    "new_est_1rm": {"type": "integer"},
                },
                "required": ["scope", "day", "new_lift_key", "new_display_name"],
            },
        },
        {
            "name": "override_week",
            "description": "Stage a one-off replacement of a whole week (e.g. a travel week with "
            "only a kettlebell). Returns a diff; does NOT commit. ``global_week`` is 1-12. Each "
            "day is {day, session, items:[str]} — free-text prescriptions (no barbell numbers "
            "needed). Show the diff and get approval before commit.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "global_week": {"type": "integer", "minimum": 1, "maximum": 12},
                    "days": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "day": {"type": "string"},
                                "session": {"type": "string"},
                                "items": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["day", "session", "items"],
                        },
                    },
                },
                "required": ["global_week", "days"],
            },
        },
        {
            "name": "set_day_across_weeks",
            "description": (
                "Replace ONE day's session across multiple weeks in a single atomic, staged "
                "change (returns a diff; does NOT commit). Use this for multi-week or cycle-wide "
                "edits in note-based plans where swap_lift doesn't apply — e.g. 'Tuesday = MP "
                "progression run for weeks 5-8', or 'goblet squat instead of back squat every "
                "Monday all 16 weeks'. ``weeks`` is the list of global week numbers to change; "
                "the named day is replaced with the given session + free-text items, all other "
                "days untouched. Do NOT claim a multi-week change is done unless you used THIS "
                "tool (or override_week) and commit_plan_update returned success."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "day": {"type": "string", "description": "Mon/Tue/.../Sun"},
                    "weeks": {
                        "type": "array",
                        "items": {"type": "integer", "minimum": 1, "maximum": 16},
                    },
                    "session": {"type": "string"},
                    "items": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["day", "weeks", "session", "items"],
            },
        },
        {
            "name": "commit_plan_update",
            "description": "Apply the pending staged change after the athlete approves; re-renders "
            "the xlsx. Only call this once the athlete has explicitly approved the diff.",
            "input_schema": {"type": "object", "properties": {}},
        },
        {
            "name": "show_plan_diff",
            "description": "Show the most recent staged/committed plan diff.",
            "input_schema": {"type": "object", "properties": {}},
        },
    ]


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


def _as_str(result: object) -> str:
    if isinstance(result, str):
        return result
    return json.dumps(result, ensure_ascii=False)


def _to_float(value: object) -> float:
    if isinstance(value, bool):
        raise TypeError("expected a number, got bool")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return float(value)
    raise TypeError(f"expected a number, got {type(value).__name__}")


def _to_int(value: object) -> int:
    return int(_to_float(value))


def _to_str_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def _dispatch_deterministic(name: str, args: dict[str, object]) -> str | None:
    """Handle the pure tools; return None if ``name`` is not one of them."""
    if name == "compute_1rm":
        return _as_str(tools.compute_1rm(_to_float(args["weight_lb"]), _to_int(args["reps"])))
    if name == "compute_training_max":
        cons = _to_float(args.get("conservatism", 0.85))
        return _as_str(tools.compute_training_max(_to_int(args["est_1rm"]), cons))
    if name == "compute_macros":
        day_type = cast(DayType, str(args["day_type"]))
        return _as_str(tools.compute_macros(_to_float(args["bw_lb"]), day_type))
    if name == "compute_maf":
        return _as_str(tools.compute_maf(_to_int(args["age"])))
    if name == "get_periodization_template":
        return _as_str(tools.get_periodization_template(cast(TemplateName, str(args["name"]))))
    if name == "compute_warmup_ramp":
        return _as_str(
            tools.compute_warmup_ramp(
                _to_int(args["tm"]), _to_int(args["week"]), _to_int(args["set_num"])
            )
        )
    if name == "lookup_advisor_principle":
        return _as_str(tools.lookup_advisor_principle(str(args["topic"])))
    return None


def _draft(block: Block, args: dict[str, object]) -> str:
    # Hard safety rail: Obelisk does not serve under-18 athletes in this MVP.
    if block.athlete.age < 18:
        return (
            "REFUSED: cannot build a plan — this athlete is under 18, and Obelisk does not serve "
            "under-18 athletes yet (no parental-consent path in this MVP). Do not program. Point "
            "them to a high-school S&C coach or age-appropriate resources, and offer to delete "
            "their data. Be respectful."
        )
    title = str(args["title"])
    goals = _to_str_list(args.get("goals", []))
    program_model = str(args.get("program_model", "hybrid_531"))

    if program_model == "linear_novice":
        deficit = bool(args.get("deficit", True))
        plan = build_linear_novice_plan(block.athlete, title, goals, deficit=deficit)
    elif program_model == "marathon_block":
        peak = _to_int(args["peak_mileage"]) if args.get("peak_mileage") is not None else 70
        long_peak = (
            _to_int(args["long_run_peak_mi"]) if args.get("long_run_peak_mi") is not None else 22
        )
        plan = build_endurance_block_plan(
            block.athlete, title, goals, peak_mileage=peak, long_run_peak_mi=long_peak
        )
    else:
        priorities = _to_str_list(args.get("priority_lifts", []))
        template = cast(TemplateName, str(args.get("template_name", "531_bbb")))
        plan = build_default_plan(block.athlete, title, goals, priorities, template)

    block.current_plan = plan
    block.name = title
    block.pending_plan = None
    render_plan(plan, str(block.xlsx_path))
    block.save()

    # Ground-truth structure so the coach describes / edits the real plan, not a
    # remembered one: phases, the day template, and any training maxes.
    phase_lines = [
        f"  Wave {w.wave_num} ({w.week_range}): {w.phase or 'strength wave'}" for w in plan.waves
    ]
    schedule_lines: list[str] = []
    for day in plan.day_template:
        mains = [b.label for b in day.blocks if b.kind == "main"]
        main_str = f" [main: {', '.join(mains)}]" if mains else ""
        schedule_lines.append(f"  {day.day}: {day.session}{main_str}")
    tm_summary = (
        ", ".join(
            f"{row.display_name} {row.tm_wave1}→{row.tm_wave3}" for row in plan.training_maxes
        )
        or "none (no barbell TMs for this program model)"
    )
    return (
        f"Drafted '{title}' as program_model='{program_model}', MAF cap {plan.maf_cap_bpm} bpm.\n"
        f"Phases:\n" + "\n".join(phase_lines) + "\n\n"
        f"Training maxes (wave1→wave3): {tm_summary}.\n\n"
        f"Weekly template (describe days/sessions from THIS, not memory):\n"
        + "\n".join(schedule_lines)
        + f"\n\nRendered workbook: {block.xlsx_path}"
    )


_SCOPE_TO_WAVES = {
    "whole_cycle": (1, 2, 3),
    "wave_1": (1,),
    "wave_2": (2,),
    "wave_3": (3,),
}


def _edit_base(block: Block) -> CyclePlan:
    """The plan a new edit builds on: the pending (uncommitted) plan if one is
    staged, else the committed current plan. This lets several edits in one turn
    accumulate into a single staged diff instead of clobbering each other."""
    base = block.pending_plan or block.current_plan
    assert base is not None
    return base.model_copy(deep=True)


def _stage(block: Block, updated: CyclePlan) -> str:
    """Diff a proposed plan against the committed plan, stage it, return the diff."""
    assert block.current_plan is not None
    diff = compute_plan_diff(block.current_plan, updated)
    if diff.is_empty():
        return "That change produces no difference from the current plan."
    block.pending_plan = updated
    block.last_diff = diff
    return format_diff(diff)


def _swap_lift(block: Block, args: dict[str, object]) -> str:
    if block.current_plan is None:
        return "No current plan. Call draft_cycle_plan first."
    scope = str(args.get("scope", "whole_cycle"))
    if scope not in _SCOPE_TO_WAVES:
        return f"scope must be one of {sorted(_SCOPE_TO_WAVES)}"
    day_name = str(args["day"]).strip()[:3].title()
    new_lift_key = str(args["new_lift_key"])
    new_label = str(args["new_display_name"])
    new_est_1rm = args.get("new_est_1rm")

    updated = _edit_base(block)
    target_waves = _SCOPE_TO_WAVES[scope]
    touched = False
    for wave in updated.waves:
        if wave.wave_num not in target_waves:
            continue
        days = [d.model_copy(deep=True) for d in updated.days_for_week((wave.wave_num - 1) * 4 + 1)]
        for day in days:
            if day.day != day_name:
                continue
            for block_item in day.blocks:
                if block_item.kind != "main":
                    continue
                old_key = block_item.lift_key
                label_suffix = (
                    block_item.label.split("—")[-1].strip() if "—" in block_item.label else "main"
                )
                block_item.label = f"{new_label} — {label_suffix}"
                block_item.lift_key = new_lift_key  # type: ignore[assignment]
                # Carry the TM over: explicit est 1RM if given, else the old lift's TM.
                if new_est_1rm is not None:
                    wave_tm = tools.compute_training_max(_to_int(new_est_1rm))
                    inc = {1: 0, 2: 1, 3: 2}[wave.wave_num]
                    wave.training_maxes[new_lift_key] = wave_tm + inc * 10
                elif old_key is not None and old_key in wave.training_maxes:
                    wave.training_maxes[new_lift_key] = wave.training_maxes[old_key]
                touched = True
        wave.days_override = days
    if not touched:
        return f"No main lift found on {day_name} in {scope}. Nothing staged."
    return _stage(block, updated)


def _override_week(block: Block, args: dict[str, object]) -> str:
    if block.current_plan is None:
        return "No current plan. Call draft_cycle_plan first."
    global_week = _to_int(args["global_week"])
    raw_days = args.get("days", [])
    if not isinstance(raw_days, list) or not raw_days:
        return "Provide at least one day in `days`."
    days: list[TrainingDay] = []
    for raw in raw_days:
        if not isinstance(raw, dict):
            continue
        items = raw.get("items", [])
        item_list = [str(x) for x in items] if isinstance(items, list) else [str(items)]
        blocks = [TrainingBlock(label=text, kind="note", note=text) for text in item_list]
        days.append(
            TrainingDay(
                day=str(raw.get("day", "?")), session=str(raw.get("session", "")), blocks=blocks
            )
        )
    updated = _edit_base(block)
    updated.week_overrides[str(global_week)] = days
    return _stage(block, updated)


def _plan_summary(plan: CyclePlan) -> str:
    """A compact, token-cheap view of the plan for the coach to reason over.

    Returns phases, the effective per-week day→session map, training-max headline,
    and nutrition headline — NOT the full nested block notes. Cycle-wide edits can
    bloat the raw plan to tens of thousands of tokens; echoing that on every later
    turn is slow and expensive, and the targeted edit tools don't need it.
    """
    lines: list[str] = [
        f"title: {plan.title}",
        f"program_model: {plan.program_model}  •  MAF cap: {plan.maf_cap_bpm} bpm",
        "goals: " + " | ".join(plan.goals),
    ]
    if plan.training_maxes:
        lines.append(
            "training_maxes (wave1→3): "
            + ", ".join(
                f"{r.display_name} {r.tm_wave1}/{r.tm_wave2}/{r.tm_wave3}"
                for r in plan.training_maxes
            )
        )
    lines.append(
        "phases: " + "; ".join(f"W{w.wave_num} {w.phase or 'strength'}" for w in plan.waves)
    )
    n = plan.nutrition
    lines.append(
        f"nutrition: {n.calories_low:,}-{n.calories_high:,} cal, protein {n.protein_g} g, "
        f"carbs/day {n.carbs_by_day}"
    )
    lines.append("weeks (effective day→session):")
    total_weeks = len(plan.waves) * 4
    for wk in range(1, total_weeks + 1):
        flag = " [override]" if str(wk) in plan.week_overrides else ""
        days = "; ".join(f"{d.day}:{d.session}" for d in plan.days_for_week(wk))
        lines.append(f"  wk{wk}{flag}: {days}")
    return "\n".join(lines)


def _set_day_across_weeks(block: Block, args: dict[str, object]) -> str:
    if block.current_plan is None:
        return "No current plan. Call draft_cycle_plan first."
    day_name = str(args["day"]).strip()[:3].title()
    raw_weeks = args.get("weeks", [])
    weeks = (
        [int(w) for w in raw_weeks if isinstance(w, (int, float))]
        if isinstance(raw_weeks, list)
        else []
    )
    if not weeks:
        return "Provide at least one week number in `weeks`."
    session = str(args.get("session", ""))
    items = _to_str_list(args.get("items", []))
    if not items:
        return "Provide at least one prescription in `items`."
    blocks = [TrainingBlock(label=text, kind="note", note=text) for text in items]

    updated = _edit_base(block)
    touched: list[int] = []
    for w in weeks:
        base = [d.model_copy(deep=True) for d in updated.days_for_week(w)]
        replaced = False
        for idx, day in enumerate(base):
            if day.day == day_name:
                base[idx] = TrainingDay(day=day_name, session=session, blocks=blocks)
                replaced = True
        if not replaced:
            base.append(TrainingDay(day=day_name, session=session, blocks=blocks))
        updated.week_overrides[str(w)] = base
        touched.append(w)
    if not touched:
        return "No weeks matched. Nothing staged."
    return _stage(block, updated)


def _commit(block: Block) -> str:
    if block.pending_plan is None:
        return "No pending change to commit. Stage one with swap_lift or override_week first."
    block.current_plan = block.pending_plan
    block.pending_plan = None
    render_plan(block.current_plan, str(block.xlsx_path))
    block.save()
    return f"Committed. Re-rendered workbook: {block.xlsx_path}"


def dispatch(block: Block, name: str, tool_input: dict[str, object]) -> str:
    """Route a tool call to its handler; always returns a string result."""
    try:
        deterministic = _dispatch_deterministic(name, tool_input)
        if deterministic is not None:
            return deterministic
        if name == "draft_cycle_plan":
            return _draft(block, tool_input)
        if name == "get_plan_json":
            return _plan_summary(block.current_plan) if block.current_plan else "No plan yet."
        if name == "swap_lift":
            return _swap_lift(block, tool_input)
        if name == "override_week":
            return _override_week(block, tool_input)
        if name == "set_day_across_weeks":
            return _set_day_across_weeks(block, tool_input)
        if name == "commit_plan_update":
            return _commit(block)
        if name == "show_plan_diff":
            return format_diff(block.last_diff) if block.last_diff else "No diff available yet."
        return f"Unknown tool: {name}"
    except (ValueError, KeyError, TypeError) as exc:
        return f"Tool '{name}' error: {exc}"
