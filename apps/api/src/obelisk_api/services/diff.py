"""Structured diff between two cycle plans for the approval gate.

Plan changes are never committed silently: the agent stages an updated plan,
this module produces a human-readable what-was / what-will-be diff, and the
athlete approves before the change is written.
"""

from __future__ import annotations

from obelisk_api.domain.models import CyclePlan, FieldChange, PlanDiff

# JSON-able value produced by Pydantic ``model_dump()`` (recursive alias).
JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]


def _fmt(value: JsonValue) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (int, float, str)):
        return str(value)
    if isinstance(value, list):
        return f"[{len(value)} item(s)]"
    return "{…}"


def _walk(before: JsonValue, after: JsonValue, path: str, out: list[FieldChange]) -> None:
    if isinstance(before, dict) and isinstance(after, dict):
        keys = list(dict.fromkeys([*before.keys(), *after.keys()]))
        for key in keys:
            child = f"{path}.{key}" if path else key
            _walk(before.get(key), after.get(key), child, out)
        return
    if isinstance(before, list) and isinstance(after, list):
        for i in range(max(len(before), len(after))):
            b = before[i] if i < len(before) else None
            a = after[i] if i < len(after) else None
            _walk(b, a, f"{path}[{i}]", out)
        return
    if before != after:
        out.append(FieldChange(path=path or "(root)", before=_fmt(before), after=_fmt(after)))


def compute_plan_diff(before: CyclePlan, after: CyclePlan) -> PlanDiff:
    """Compute a structured diff between two plans."""
    changes: list[FieldChange] = []
    _walk(before.model_dump(), after.model_dump(), "", changes)
    if not changes:
        summary = "No changes."
    else:
        top_level = sorted({c.path.split(".")[0].split("[")[0] for c in changes})
        summary = f"{len(changes)} change(s) across: {', '.join(top_level)}."
    return PlanDiff(summary=summary, changes=changes)


def format_diff(diff: PlanDiff) -> str:
    """Render a diff as a readable text block for the CLI / agent."""
    if diff.is_empty():
        return "No changes to apply."
    lines = [f"PROPOSED CHANGES — {diff.summary}", ""]
    for c in diff.changes:
        lines.append(f"  • {c.path}")
        lines.append(f"      was:  {c.before}")
        lines.append(f"      will: {c.after}")
    lines.append("")
    lines.append("Approve these changes? (the plan is NOT modified until you approve)")
    return "\n".join(lines)
