"""Typed data model for athletes, cycle plans, and plan diffs.

The plan is stored at the *template* level, not fully expanded per set: a wave
carries its training maxes, the loading scheme carries the per-week percentages,
and the renderer (``obelisk_api.services.render``) expands them deterministically into prescribed
weights. This keeps the agent's emitted JSON compact and makes conversational
adaptation a matter of editing a small, well-typed structure.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# Canonical lift keys used across tools, plan, and renderer.
LiftKey = Literal[
    "back_squat",
    "deadlift",
    "bench_press",
    "strict_press",
    "front_squat",
    "power_clean",
    "trap_bar_deadlift",
]

DayType = Literal["rest", "light", "moderate", "hard"]
TemplateName = Literal["531_bbb", "rat6", "juggernaut", "tactical_barbell_operator"]
# The macrocycle program model the agent selects for an athlete.
ProgramModel = Literal["hybrid_531", "linear_novice", "marathon_block"]
BlockKind = Literal["main", "accessory", "note"]


class EstimatedOneRepMax(BaseModel):
    """Estimated 1RMs per lift, in pounds. All optional — not every athlete has
    tested every lift (a marathoner may skip front squat / power clean; a novice
    has none at all)."""

    back_squat: int | None = None
    deadlift: int | None = None
    bench_press: int | None = None
    strict_press: int | None = None
    front_squat: int | None = None
    power_clean: int | None = None


class Athlete(BaseModel):
    """Athlete baseline, parsed from the structured baseline JSON.

    Only identity + a couple of vitals are required. Everything modality-specific
    is optional so out-of-distribution athletes (novice with no 1RMs, a pure
    runner) parse cleanly. Unknown extra keys are preserved via ``extra='allow'``
    so the agent can see them in the profile.
    """

    model_config = {"extra": "allow"}

    name: str
    age: int
    bodyweight_lb: float
    height_in: float | None = None
    resting_hr_bpm: int | None = None
    sex: str | None = None
    training_age_months: int | None = None
    estimated_1rm: EstimatedOneRepMax | None = None
    rep_max_known: dict[str, float] | None = None
    max_strict_pullups: int | None = None
    weighted_pullup_3rm_total_lb: float | None = None
    lattice_20mm_load_pct_bw: float | None = None
    max_bw_hang_sec: int | None = None
    maf_test_distance_mi: float | None = None
    maf_pace_min_per_mi: str | None = None
    row_2k_time: str | None = None
    ruck_60min_distance_mi_at_35lb: float | None = None
    current_weekly_mileage: float | None = None
    marathon_pr: str | None = None
    named_objective: str | None = None
    objective_date_weeks_out: int | None = None
    mobility_screen_all_pass: bool | None = None
    primary_goals: list[str] = Field(default_factory=list)
    equipment: str | None = None
    days_per_week: int = 3
    injuries: list[str] = Field(default_factory=list)


class WorkSet(BaseModel):
    """A single prescribed set as a percentage of the lift's training max."""

    pct: float = Field(ge=0.0, le=1.5, description="Fraction of training max (0-1.5).")
    reps: int = Field(ge=1, le=30)
    amrap: bool = Field(default=False, description="Top set is AMRAP (leave 1-2 RIR).")


class WeekScheme(BaseModel):
    """One week of a 4-week wave: a label plus the main-lift set percentages."""

    label: str
    is_deload: bool = False
    main_sets: list[WorkSet]


class TrainingBlock(BaseModel):
    """One exercise block within a training day.

    - ``main``: barbell main lift; sets come from the wave's weekly scheme.
    - ``accessory``: uses ``lift_key`` + its own fixed ``accessory_sets`` (% of TM).
    - ``note``: free-text prescription (pull-ups, carries, conditioning, etc.).
    """

    label: str
    kind: BlockKind
    lift_key: LiftKey | None = None
    accessory_sets: list[WorkSet] | None = None
    note: str | None = None


class TrainingDay(BaseModel):
    """A single day in the weekly template."""

    day: str
    session: str
    blocks: list[TrainingBlock]


class TrainingMaxRow(BaseModel):
    """A row of the Overview training-max table."""

    lift_key: LiftKey
    display_name: str
    est_1rm: int
    tm_wave1: int
    tm_wave2: int
    tm_wave3: int
    increment: int
    notes: str


class Wave(BaseModel):
    """A 4-week mesocycle. For strength plans ``training_maxes`` maps lift_key ->
    TM; for endurance/novice plans it is empty and ``phase`` / ``week_labels``
    carry the structure (Base / Build / Peak / Taper, etc.)."""

    wave_num: int
    week_range: str
    training_maxes: dict[str, int] = Field(default_factory=dict)
    phase: str | None = None
    week_labels: list[str] | None = Field(
        default=None,
        description="Optional per-week header labels (4 entries) for this wave; "
        "falls back to the shared loading_scheme labels when absent.",
    )
    days_override: list[TrainingDay] | None = Field(
        default=None,
        description="If set, replaces the shared day_template for this whole wave.",
    )


class TableRow(BaseModel):
    """Generic labelled row for the aerobic-build and loading-scheme tables."""

    cells: list[str]


class NutritionProfile(BaseModel):
    """Computed nutrition targets plus narrative guidance lines."""

    calories_low: int
    calories_high: int
    protein_g: int
    carbs_by_day: dict[str, int]
    fat_floor_g: int
    notes: list[str]


class CyclePlan(BaseModel):
    """The full cycle plan. This is the durable artifact inside a Block."""

    title: str
    subtitle: str
    goals: list[str]
    program_model: ProgramModel = "hybrid_531"
    template_name: TemplateName = "531_bbb"
    maf_cap_bpm: int
    # Strength-specific sections — empty for endurance/novice plans, which carry
    # their prescriptions as note blocks in the day template instead.
    training_maxes: list[TrainingMaxRow] = Field(default_factory=list)
    weekly_schedule: list[TableRow] = Field(default_factory=list)
    loading_scheme: list[WeekScheme] = Field(default_factory=list)
    aerobic_build: list[TableRow] = Field(default_factory=list)
    aerobic_headers: list[str] = Field(
        default_factory=lambda: ["Weeks", "Tue (MAF)", "Thu", "Sat (Long)", "Notes"]
    )
    hangboard_notes: list[str] = Field(default_factory=list)
    nutrition: NutritionProfile
    day_template: list[TrainingDay]
    waves: list[Wave]
    week_overrides: dict[str, list[TrainingDay]] = Field(
        default_factory=dict,
        description="Global-week-number (as str) -> day list, for one-off weeks "
        "(e.g. travel weeks). Overrides both day_template and wave days_override.",
    )

    def days_for_week(self, global_week: int) -> list[TrainingDay]:
        """Resolve the effective day list for a global week number (1-based)."""
        override = self.week_overrides.get(str(global_week))
        if override is not None:
            return override
        wave_index = (global_week - 1) // 4
        if 0 <= wave_index < len(self.waves):
            wave = self.waves[wave_index]
            if wave.days_override is not None:
                return wave.days_override
        return self.day_template


class FieldChange(BaseModel):
    """A single what-was / what-will-be change for the approval diff."""

    path: str
    before: str
    after: str


class PlanDiff(BaseModel):
    """Structured diff between two plans, shown to the athlete before commit."""

    summary: str
    changes: list[FieldChange]

    def is_empty(self) -> bool:
        return len(self.changes) == 0
