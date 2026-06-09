"""Expand a stored :class:`CyclePlan` into a single day's *prescribed* session.

The plan is stored at the template level (waves carry training maxes, the loading
scheme carries per-week percentages). To drive the iOS In-Session screen we need
the concrete sets for one calendar date: weight = round_to_5(training_max × pct),
the same deterministic math the xlsx renderer uses. This module is the pure,
openpyxl-free version of that expansion so the `/v1/blocks/{id}/sessions/{date}`
endpoint can reuse it without dragging in the workbook builder.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from obelisk_api.domain.models import CyclePlan, TrainingDay
from obelisk_api.tools.deterministic import round_to_5

# Plans label days with the 3-letter English abbreviation (see planbuilder).
_WEEKDAY_ABBR = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Default rest between sets (PRD §2.1): compounds get a full 3 min, accessories 90s.
REST_DEFAULT_COMPOUND_SEC = 180
REST_DEFAULT_ACCESSORY_SEC = 90


@dataclass
class PrescribedSet:
    set_index: int
    pct: float
    reps: int
    amrap: bool
    weight_lb: int | None  # None for note blocks / bodyweight work


@dataclass
class PrescribedExercise:
    label: str
    kind: str  # "main" | "accessory" | "note"
    lift_key: str | None
    note: str | None
    rest_default_sec: int
    sets: list[PrescribedSet] = field(default_factory=list)

    @property
    def match_key(self) -> str:
        """Stable identity used to line up this exercise with prior actuals and to
        tag logged sets. Prefer the canonical lift key; fall back to the label."""
        return self.lift_key or self.label


@dataclass
class PrescribedSession:
    block_id: str
    date: date
    global_week: int
    week_in_wave: int
    wave_num: int
    day: str
    session_title: str
    is_rest_day: bool
    exercises: list[PrescribedExercise] = field(default_factory=list)


def resolve_global_week(start_date: date, target: date) -> int:
    """1-based cycle week that ``target`` falls in, given the block's start date.

    Day-aligned to the start date: the start day and the next six days are week 1.
    Dates before the start resolve to week 1 (the plan hasn't begun); the caller
    decides whether that's a rest/empty day.
    """
    delta_days = (target - start_date).days
    if delta_days < 0:
        return 1
    return delta_days // 7 + 1


def _day_for_date(plan: CyclePlan, global_week: int, target: date) -> TrainingDay | None:
    abbr = _WEEKDAY_ABBR[target.weekday()]
    for day in plan.days_for_week(global_week):
        if day.day == abbr:
            return day
    return None


def expand_session(
    plan: CyclePlan, block_id: str, start_date: date, target: date
) -> PrescribedSession:
    """Concrete prescribed session for ``target``. An off day (no matching template
    day, or a day with no work) comes back with ``is_rest_day=True`` and no
    exercises."""
    global_week = resolve_global_week(start_date, target)
    wave_index = (global_week - 1) // 4
    week_in_wave = (global_week - 1) % 4 + 1
    wave = plan.waves[wave_index] if 0 <= wave_index < len(plan.waves) else None
    scheme = (
        plan.loading_scheme[week_in_wave - 1]
        if 0 <= week_in_wave - 1 < len(plan.loading_scheme)
        else None
    )

    day = _day_for_date(plan, global_week, target)
    session = PrescribedSession(
        block_id=block_id,
        date=target,
        global_week=global_week,
        week_in_wave=week_in_wave,
        wave_num=wave.wave_num if wave else 0,
        day=_WEEKDAY_ABBR[target.weekday()],
        session_title=day.session if day else "Rest",
        is_rest_day=day is None,
    )
    if day is None:
        return session

    training_maxes = wave.training_maxes if wave else {}
    for block in day.blocks:
        if block.kind == "main" and block.lift_key and scheme and scheme.main_sets:
            tm = training_maxes.get(block.lift_key, 0)
            ex = PrescribedExercise(
                label=block.label,
                kind="main",
                lift_key=block.lift_key,
                note=None,
                rest_default_sec=REST_DEFAULT_COMPOUND_SEC,
                sets=[
                    PrescribedSet(
                        set_index=i,
                        pct=s.pct,
                        reps=s.reps,
                        amrap=s.amrap,
                        weight_lb=round_to_5(tm * s.pct) if tm else None,
                    )
                    for i, s in enumerate(scheme.main_sets, start=1)
                ],
            )
        elif block.kind == "accessory" and block.lift_key and block.accessory_sets:
            tm = training_maxes.get(block.lift_key, 0)
            ex = PrescribedExercise(
                label=block.label,
                kind="accessory",
                lift_key=block.lift_key,
                note=None,
                rest_default_sec=REST_DEFAULT_ACCESSORY_SEC,
                sets=[
                    PrescribedSet(
                        set_index=i,
                        pct=s.pct,
                        reps=s.reps,
                        amrap=s.amrap,
                        weight_lb=round_to_5(tm * s.pct) if tm else None,
                    )
                    for i, s in enumerate(block.accessory_sets, start=1)
                ],
            )
        else:
            # Note block: free-text prescription (carries, conditioning, pull-ups).
            ex = PrescribedExercise(
                label=block.label,
                kind="note",
                lift_key=block.lift_key,
                note=block.note,
                rest_default_sec=REST_DEFAULT_ACCESSORY_SEC,
                sets=[],
            )
        session.exercises.append(ex)

    # A template day that expanded to nothing loggable is effectively a rest day.
    session.is_rest_day = not any(ex.sets for ex in session.exercises) and all(
        ex.kind == "note" and not ex.note for ex in session.exercises
    )
    return session
