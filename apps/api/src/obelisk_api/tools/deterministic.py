"""Deterministic tools exposed to the Block Coach via Anthropic function calling.

Every numeric prescription in the system originates here, never from LLM
free-generation. Functions are pure and side-effect free (except the renderer,
which writes a file), which makes them straightforward to unit test.
"""

from __future__ import annotations

import math
from typing import TypedDict

from obelisk_api.domain.models import DayType, TemplateName

# ----------------------------------------------------------------------------
# Rounding helpers
# ----------------------------------------------------------------------------


def round_half_up(value: float) -> int:
    """Round to the nearest integer, halves going up (gym-plate convention)."""
    return math.floor(value + 0.5)


def round_to_5(value: float) -> int:
    """Round to the nearest 5 lb."""
    return round_half_up(value / 5.0) * 5


# ----------------------------------------------------------------------------
# 1. Estimated 1RM (Epley)
# ----------------------------------------------------------------------------


def compute_1rm(weight_lb: float, reps: int) -> int:
    """Epley estimated one-rep max, rounded to the nearest 5 lb.

    1RM = weight * (1 + reps / 30). Most accurate in the 3-10 rep range.
    """
    if weight_lb <= 0:
        raise ValueError("weight_lb must be positive")
    if reps < 1:
        raise ValueError("reps must be >= 1")
    est = weight_lb * (1.0 + reps / 30.0)
    return round_to_5(est)


# ----------------------------------------------------------------------------
# 2. Training max
# ----------------------------------------------------------------------------


def compute_training_max(est_1rm: int, conservatism: float = 0.85) -> int:
    """Training max = conservatism * estimated 1RM, rounded to the nearest 5 lb.

    Default 0.85 reflects the Advisor Brief's '<=85% of 1RM most weeks' rule for
    concurrent (hybrid) athletes.
    """
    if est_1rm <= 0:
        raise ValueError("est_1rm must be positive")
    if not 0.5 <= conservatism <= 1.0:
        raise ValueError("conservatism must be between 0.5 and 1.0")
    return round_to_5(est_1rm * conservatism)


# ----------------------------------------------------------------------------
# 3. Macros (Renaissance scheme)
# ----------------------------------------------------------------------------

_CARB_FACTOR: dict[str, float] = {"rest": 0.5, "light": 1.0, "moderate": 1.5, "hard": 2.0}
# Calorie multiplier (cal/lb) by training day, centered on the Brief's BW x 18-20
# maintenance band with a surplus on hard days.
_CAL_MULTIPLIER: dict[str, float] = {"rest": 16.0, "light": 18.0, "moderate": 20.0, "hard": 22.0}
_PROTEIN_PER_LB = 1.0
_FAT_FLOOR_PER_LB = 0.4
# Hard calorie safety floor (see compute_macros): max(BW x 10, 1200) cal/day.
_CAL_FLOOR_PER_LB = 10.0
_CAL_FLOOR_ABSOLUTE = 1200


class MacroResult(TypedDict):
    day_type: str
    calories: int
    protein_g: int
    carbs_g: int
    fat_g: int


def compute_macros(
    bw_lb: float,
    day_type: DayType,
    protein_g_per_lb: float | None = None,
    carb_g_per_lb: float | None = None,
    cal_per_lb: float | None = None,
) -> MacroResult:
    """Renaissance-style macros for a given bodyweight and training-day type.

    Defaults: protein 1.0 g/lb; carbs scaled by day type (0.5/1.0/1.5/2.0 g/lb);
    fat fills the day's calorie target, never below the 0.4 g/lb floor. Calories
    are recomputed from the final macros so the numbers are internally consistent.

    The optional overrides let the coach calibrate for athletes outside the
    hybrid default: a marathoner needs far higher carbs (``carb_g_per_lb=4.0`` on
    long-run days) and lower protein (``protein_g_per_lb=0.75``); a novice on a cut
    needs a deficit (``cal_per_lb`` below the day-type default).
    """
    if bw_lb <= 0:
        raise ValueError("bw_lb must be positive")
    if day_type not in _CARB_FACTOR:
        raise ValueError(f"day_type must be one of {sorted(_CARB_FACTOR)}")
    if protein_g_per_lb is not None and not 0.3 <= protein_g_per_lb <= 1.5:
        raise ValueError("protein_g_per_lb must be between 0.3 and 1.5")
    if carb_g_per_lb is not None and not 0.0 <= carb_g_per_lb <= 7.0:
        raise ValueError("carb_g_per_lb must be between 0.0 and 7.0")
    if cal_per_lb is not None and not 8.0 <= cal_per_lb <= 35.0:
        raise ValueError("cal_per_lb must be between 8.0 and 35.0")

    protein_factor = protein_g_per_lb if protein_g_per_lb is not None else _PROTEIN_PER_LB
    carb_factor = carb_g_per_lb if carb_g_per_lb is not None else _CARB_FACTOR[day_type]
    cal_mult = cal_per_lb if cal_per_lb is not None else _CAL_MULTIPLIER[day_type]

    protein_g = round_half_up(protein_factor * bw_lb)
    carbs_g = round_half_up(carb_factor * bw_lb)
    fat_floor_g = round_half_up(_FAT_FLOOR_PER_LB * bw_lb)

    cal_target = cal_mult * bw_lb
    remaining_cal = cal_target - (4 * protein_g) - (4 * carbs_g)
    fat_g = max(fat_floor_g, round_half_up(remaining_cal / 9.0))

    calories = (4 * protein_g) + (4 * carbs_g) + (9 * fat_g)
    # Hard safety floor: never return a calorie target below bodyweight x 10, and
    # never below 1200 for any adult. If a caller (or the agent) requests a deeper
    # cut, the result is clamped UP to the floor — the tool refuses to produce a
    # sub-floor prescription. Extra calories go to fat to keep protein/carbs intact.
    cal_floor = max(_CAL_FLOOR_ABSOLUTE, round_half_up(_CAL_FLOOR_PER_LB * bw_lb))
    if calories < cal_floor:
        fat_g = round_half_up((cal_floor - (4 * protein_g) - (4 * carbs_g)) / 9.0)
        calories = (4 * protein_g) + (4 * carbs_g) + (9 * fat_g)
    return MacroResult(
        day_type=day_type,
        calories=calories,
        protein_g=protein_g,
        carbs_g=carbs_g,
        fat_g=fat_g,
    )


# ----------------------------------------------------------------------------
# 4. MAF heart-rate cap
# ----------------------------------------------------------------------------


def compute_maf(age: int) -> int:
    """Maffetone aerobic HR cap = 180 - age."""
    if not 0 < age < 120:
        raise ValueError("age must be between 1 and 119")
    return 180 - age


# ----------------------------------------------------------------------------
# 5. Periodization templates
# ----------------------------------------------------------------------------


class SetSpec(TypedDict):
    pct: float
    reps: int
    amrap: bool


class TemplateWeek(TypedDict):
    label: str
    is_deload: bool
    main_sets: list[SetSpec]


class TemplateResult(TypedDict):
    name: str
    description: str
    days_per_week: int
    weekly_split: list[str]
    weeks: list[TemplateWeek]
    notes: list[str]


def _set(pct: float, reps: int, amrap: bool = False) -> SetSpec:
    return SetSpec(pct=pct, reps=reps, amrap=amrap)


# The 5/3/1 + Boring-But-Big wave used by Cycle 1. Percentages are of training max.
_FIVE_THREE_ONE_BBB: list[TemplateWeek] = [
    TemplateWeek(
        label="5s",
        is_deload=False,
        main_sets=[_set(0.65, 5), _set(0.75, 5), _set(0.85, 5, amrap=True)],
    ),
    TemplateWeek(
        label="3s",
        is_deload=False,
        main_sets=[_set(0.70, 3), _set(0.80, 3), _set(0.90, 3, amrap=True)],
    ),
    TemplateWeek(
        label="5/3/1",
        is_deload=False,
        main_sets=[_set(0.75, 5), _set(0.85, 3), _set(0.95, 1, amrap=True)],
    ),
    TemplateWeek(
        label="Deload",
        is_deload=True,
        main_sets=[_set(0.40, 5), _set(0.50, 5), _set(0.60, 5)],
    ),
]

_RAT6: list[TemplateWeek] = [
    TemplateWeek(
        label="Wk1", is_deload=False, main_sets=[_set(0.70, 5), _set(0.75, 5), _set(0.80, 5)]
    ),
    TemplateWeek(
        label="Wk2", is_deload=False, main_sets=[_set(0.72, 5), _set(0.78, 3), _set(0.83, 3)]
    ),
    TemplateWeek(
        label="Wk3",
        is_deload=False,
        main_sets=[_set(0.75, 5), _set(0.80, 3), _set(0.85, 1, amrap=True)],
    ),
    TemplateWeek(
        label="Deload", is_deload=True, main_sets=[_set(0.50, 5), _set(0.55, 5), _set(0.60, 5)]
    ),
]

_JUGGERNAUT: list[TemplateWeek] = [
    TemplateWeek(
        label="10s",
        is_deload=False,
        main_sets=[_set(0.60, 10), _set(0.60, 10), _set(0.60, 10, amrap=True)],
    ),
    TemplateWeek(
        label="8s",
        is_deload=False,
        main_sets=[_set(0.65, 8), _set(0.65, 8), _set(0.65, 8, amrap=True)],
    ),
    TemplateWeek(
        label="5s",
        is_deload=False,
        main_sets=[_set(0.70, 5), _set(0.70, 5), _set(0.70, 5, amrap=True)],
    ),
    TemplateWeek(
        label="3s",
        is_deload=False,
        main_sets=[_set(0.75, 3), _set(0.75, 3), _set(0.75, 3, amrap=True)],
    ),
]

_TB_OPERATOR: list[TemplateWeek] = [
    TemplateWeek(
        label="Wk1", is_deload=False, main_sets=[_set(0.70, 5), _set(0.70, 5), _set(0.70, 5)]
    ),
    TemplateWeek(
        label="Wk2", is_deload=False, main_sets=[_set(0.80, 5), _set(0.80, 5), _set(0.80, 5)]
    ),
    TemplateWeek(
        label="Wk3", is_deload=False, main_sets=[_set(0.90, 3), _set(0.90, 3), _set(0.90, 3)]
    ),
    TemplateWeek(
        label="Deload", is_deload=True, main_sets=[_set(0.55, 5), _set(0.55, 5), _set(0.55, 5)]
    ),
]

_TEMPLATES: dict[str, TemplateResult] = {
    "531_bbb": TemplateResult(
        name="531_bbb",
        description="5/3/1 with submaximal top sets — the default hybrid wave. "
        "Three working sets ramping to an AMRAP top set, weekly undulation 5s/3s/5-3-1, "
        "then a deload. TMs at 85% of 1RM keep most work submaximal per the Brief.",
        days_per_week=3,
        weekly_split=[
            "Mon: Strength A (squat main + press accessory + pulling)",
            "Wed: Strength B (bench main + squat light + rows)",
            "Fri: Strength C (deadlift main + bench light + power clean speed)",
        ],
        weeks=_FIVE_THREE_ONE_BBB,
        notes=[
            "Top set is AMRAP on weeks 1-3 — leave 1-2 reps in reserve (Brief 3.3).",
            "Week 4 is a true deload — no AMRAP, full recovery.",
            "Bump TM +5 (upper) / +10 (lower) each wave.",
        ],
    ),
    "rat6": TemplateResult(
        name="rat6",
        description="MTI RAT 6-style weekly undulation for an intermediate pure-strength "
        "block. Simplified 3-week wave + deload.",
        days_per_week=3,
        weekly_split=["Mon: Lower", "Wed: Upper", "Fri: Full-body strength"],
        weeks=_RAT6,
        notes=["Best for a winter strength emphasis when conditioning volume is low."],
    ),
    "juggernaut": TemplateResult(
        name="juggernaut",
        description="Juggernaut 2.0 accumulation wave: 10s/8s/5s/3s rep brackets, "
        "submaximal, high-volume hypertrophy-to-strength.",
        days_per_week=4,
        weekly_split=["Squat day", "Bench day", "Deadlift day", "Press day"],
        weeks=_JUGGERNAUT,
        notes=["Use for a 16-week block toward a defined objective (Brief 5.3)."],
    ),
    "tactical_barbell_operator": TemplateResult(
        name="tactical_barbell_operator",
        description="Tactical Barbell Operator: 3x/week, same lifts each day, "
        "percentage-cycled across the wave. Pairs with heavy concurrent conditioning.",
        days_per_week=3,
        weekly_split=["Mon: SQ/BP/DL", "Wed: SQ/BP/DL", "Fri: SQ/BP/DL"],
        weeks=_TB_OPERATOR,
        notes=["Strength is the constant in operator phases; endurance bends (Brief 3.2)."],
    ),
}


def get_periodization_template(name: TemplateName) -> TemplateResult:
    """Return the weekly loading scheme (and recommended split) for a template."""
    if name not in _TEMPLATES:
        raise ValueError(f"name must be one of {sorted(_TEMPLATES)}")
    return _TEMPLATES[name]


# ----------------------------------------------------------------------------
# 6. Warm-up / working-set ramp
# ----------------------------------------------------------------------------


def compute_warmup_ramp(tm: int, week: int, set_num: int) -> int:
    """Prescribed working weight for a given week/set of a 5/3/1 wave.

    ``week`` is 1-4 within the wave; ``set_num`` is 1-3. Returns the load rounded
    to the nearest 5 lb. This is the same math the renderer uses to fill the
    Prescribed-lb column.
    """
    if not 1 <= week <= 4:
        raise ValueError("week must be 1-4 (within the wave)")
    if not 1 <= set_num <= 3:
        raise ValueError("set_num must be 1-3")
    if tm <= 0:
        raise ValueError("tm must be positive")
    pct = _FIVE_THREE_ONE_BBB[week - 1]["main_sets"][set_num - 1]["pct"]
    return round_to_5(tm * pct)


# ----------------------------------------------------------------------------
# 7. Render cycle plan to xlsx
# ----------------------------------------------------------------------------


def render_cycle_plan_xlsx(plan: dict[str, object], output_path: str) -> str:
    """Render a cycle-plan dict to an Excel workbook; returns the output path.

    Imported lazily so unit tests for the pure tools don't require openpyxl to be
    importable at module load. Validates the plan via the Pydantic model first.
    """
    from obelisk_api.domain.models import CyclePlan
    from obelisk_api.services.render import render_plan

    validated = CyclePlan.model_validate(plan)
    return render_plan(validated, output_path)


# ----------------------------------------------------------------------------
# 8. Advisor Brief lookup
# ----------------------------------------------------------------------------


def lookup_advisor_principle(topic: str) -> str:
    """Keyword search over the Advisor Brief; returns the best-matching section."""
    from obelisk_api.services.brief import search

    return search(topic)
