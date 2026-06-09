"""Builds the deterministic base cycle plan from athlete baseline + goals.

This is the structural backbone (the role ``build_cycle1.py`` played for the
hand-made artifact). The agent chooses goals, priorities, and the template; this
module assembles a coach-quality skeleton with every number sourced from
``obelisk_api.tools.deterministic``. The agent then explains, cites, and adapts it.
"""

from __future__ import annotations

from obelisk_api.domain.models import (
    Athlete,
    CyclePlan,
    DayType,
    NutritionProfile,
    TableRow,
    TemplateName,
    TrainingBlock,
    TrainingDay,
    TrainingMaxRow,
    Wave,
    WeekScheme,
    WorkSet,
)
from obelisk_api.tools.deterministic import (
    compute_macros,
    compute_maf,
    compute_training_max,
    get_periodization_template,
)

DISPLAY_NAMES: dict[str, str] = {
    "back_squat": "Back Squat",
    "deadlift": "Deadlift",
    "bench_press": "Bench Press",
    "strict_press": "Strict Press",
    "front_squat": "Front Squat",
    "power_clean": "Power Clean",
    "trap_bar_deadlift": "Trap Bar Deadlift",
}

# Lower-body / posterior lifts grow faster than pressing lifts.
TM_INCREMENT: dict[str, int] = {
    "back_squat": 10,
    "front_squat": 10,
    "deadlift": 10,
    "trap_bar_deadlift": 10,
    "bench_press": 5,
    "strict_press": 5,
    "power_clean": 5,
}

TM_NOTES: dict[str, str] = {
    "back_squat": "High-bar full depth (matches tested style)",
    "bench_press": "Paused, some arch — priority lift this cycle",
    "deadlift": "Conventional, 1 work set only — high stress",
    "strict_press": "Standing, no leg drive",
    "front_squat": "Used as squat #2 light/technique day",
    "power_clean": "Used 1x/wk as speed work (not main lift)",
}

# Order of lifts in the Overview training-max table.
_TM_ORDER: list[str] = [
    "back_squat",
    "bench_press",
    "deadlift",
    "strict_press",
    "front_squat",
    "power_clean",
]

_ACCESSORY_PRESS = [WorkSet(pct=0.60, reps=8), WorkSet(pct=0.70, reps=8), WorkSet(pct=0.70, reps=8)]
_LIGHT_TECHNIQUE = [WorkSet(pct=0.60, reps=5), WorkSet(pct=0.60, reps=5), WorkSet(pct=0.60, reps=5)]
_POWER_SPEED = [WorkSet(pct=0.65, reps=3) for _ in range(5)]


def _est_1rm(athlete: Athlete) -> dict[str, int]:
    """Extract the six barbell 1RMs the hybrid model needs. Raises if any are
    missing — the hybrid_531 model must not be used without tested 1RMs."""
    rm = athlete.estimated_1rm
    if rm is None:
        raise ValueError(
            "hybrid_531 requires tested barbell 1RMs, but this athlete has none. "
            "Use program_model='linear_novice' (or 'marathon_block') instead."
        )
    values = {
        "back_squat": rm.back_squat,
        "bench_press": rm.bench_press,
        "deadlift": rm.deadlift,
        "strict_press": rm.strict_press,
        "front_squat": rm.front_squat,
        "power_clean": rm.power_clean,
    }
    missing = [k for k, v in values.items() if v is None]
    if missing:
        raise ValueError(f"hybrid_531 requires 1RMs for all lifts; missing: {', '.join(missing)}")
    return {k: int(v) for k, v in values.items() if v is not None}


def _training_max_rows(athlete: Athlete) -> list[TrainingMaxRow]:
    est = _est_1rm(athlete)
    rows: list[TrainingMaxRow] = []
    for key in _TM_ORDER:
        tm1 = compute_training_max(est[key])
        inc = TM_INCREMENT[key]
        rows.append(
            TrainingMaxRow(
                lift_key=key,
                display_name=DISPLAY_NAMES[key],
                est_1rm=est[key],
                tm_wave1=tm1,
                tm_wave2=tm1 + inc,
                tm_wave3=tm1 + 2 * inc,
                increment=inc,
                notes=TM_NOTES[key],
            )
        )
    return rows


def _loading_scheme(template_name: TemplateName) -> list[WeekScheme]:
    template = get_periodization_template(template_name)
    schemes: list[WeekScheme] = []
    for week in template["weeks"]:
        schemes.append(
            WeekScheme(
                label=week["label"],
                is_deload=week["is_deload"],
                main_sets=[
                    WorkSet(pct=s["pct"], reps=s["reps"], amrap=s["amrap"])
                    for s in week["main_sets"]
                ],
            )
        )
    return schemes


def _weekly_schedule() -> list[TableRow]:
    rows = [
        ("Mon", "Strength A — Squat main + Press accessory + pulling"),
        ("Tue", "MAF aerobic — build 30 → 60 min over the cycle"),
        ("Wed", "Strength B — Bench main + Squat light + rows"),
        ("Thu", "MAF aerobic (Wk 1-6) → 30/30 intervals (Wk 7-12) + Hangboard #1"),
        ("Fri", "Strength C — Deadlift main + Bench light + Power Clean speed"),
        ("Sat", "Long pack hike (60 → 120 min @ 25-35#) + Hangboard #2"),
        ("Sun", "Rest"),
    ]
    return [TableRow(cells=[day, desc]) for day, desc in rows]


def _aerobic_build(maf_cap: int) -> list[TableRow]:
    rows = [
        ("Wk 1-2", "30-40 min", "60 min", "60 min", "MAF Tue+Thu, Sat long"),
        ("Wk 3-4", "40-50 min", "75 min", "75 min", "Build slowly"),
        ("Wk 5-6", "50 min", "90 min", "90 min", "Re-test MAF end of Wk 6"),
        ("Wk 7-8", "50 min", "Intervals: 30/30 × 2×10", "100 min", "Intro 30/30 — after RHR drops"),
        ("Wk 9-10", "60 min", "30/30 × 2×15", "110 min", ""),
        ("Wk 11", "60 min", "30/30 × 1×20", "120 min", ""),
        ("Wk 12 (deload)", "30 min", "30 min", "60 min", "Final week — easy only"),
    ]
    return [TableRow(cells=list(r)) for r in rows]


def _hangboard_notes() -> list[str]:
    return [
        "Protocol: 20mm edge, half-crimp, 7s hang / 53s rest, 6 hangs per set, 3 sets per session.",
        "Start load: BW + 5 lb (~50% of max 7s load). Add 5 lb total whenever last set is clean.",
        "Target by Wk 12: BW + 40-50 lb (~125-130% BW load). Re-test in Wk 13.",
        "ALWAYS warm up fingers fully (10-15 min) before loaded hangs.",
        "If pain or sharpness in fingers/forearms: STOP. 7-14 days of antagonist work only.",
    ]


def _nutrition(athlete: Athlete) -> NutritionProfile:
    bw = athlete.bodyweight_lb
    carbs_by_day = {
        day: compute_macros(bw, day)["carbs_g"]  # type: ignore[arg-type]
        for day in ("rest", "light", "moderate", "hard")
    }
    cal_low = round(18 * bw)
    cal_high = round(20 * bw)
    protein_g = compute_macros(bw, "moderate")["protein_g"]
    fat_floor = round(0.4 * bw)
    notes = [
        f"Calories: BW × 18-20 = {cal_low:,}-{cal_high:,} cal/day (maintenance, slight surplus on hard days).",
        f"Protein: 1.0 g/lb = {protein_g} g/day, split across 5-6 meals (~30-35 g/meal).",
        "Carbs (Renaissance scheme): Rest {r} • Light {l} • Moderate {m} • Hard {h} g/day.".format(
            r=carbs_by_day["rest"],
            l=carbs_by_day["light"],
            m=carbs_by_day["moderate"],
            h=carbs_by_day["hard"],
        ),
        f"Fat: fills remaining calories. Minimum 0.4 g/lb ({fat_floor} g).",
        "Peri-workout: 15% pre / 40% during-and-post / 35% post-post / 10% rest. Near-zero fat around training.",
        "Saturday long-pack overlay: electrolytes hourly, omega-3 3-6 g/day, sodium phosphate 1 g/3-4 hr if >2 hr.",
        "Track BW twice/wk (Mon + Thu fasted). Target stable ±2 lb; aerobic goal supersedes mass gain.",
    ]
    return NutritionProfile(
        calories_low=cal_low,
        calories_high=cal_high,
        protein_g=protein_g,
        carbs_by_day=carbs_by_day,
        fat_floor_g=fat_floor,
        notes=notes,
    )


def _day_template(priority_lifts: list[str]) -> list[TrainingDay]:
    bench_priority = "bench_press" in priority_lifts

    mon_blocks: list[TrainingBlock] = [
        TrainingBlock(label="Back Squat — main", kind="main", lift_key="back_squat"),
        TrainingBlock(
            label="Strict Press — accessory",
            kind="accessory",
            lift_key="strict_press",
            accessory_sets=_ACCESSORY_PRESS,
        ),
        TrainingBlock(
            label="Pull-ups",
            kind="note",
            note="Strict pull-ups, 4 sets x 5 reps with 5-lb belt (or BW if 5 lb impossible).",
        ),
    ]
    if bench_priority:
        mon_blocks.append(
            TrainingBlock(
                label="DB bench press — accessory (bench priority)",
                kind="note",
                note="4 sets x 8-10 reps, controlled tempo. Extra pressing volume for the priority lift.",
            )
        )
    mon_blocks.append(
        TrainingBlock(
            label="Optional finisher",
            kind="note",
            note="3 rounds: 10 KB swings 53# + 10 push-ups, no rest. 5 min.",
        )
    )

    return [
        TrainingDay(day="Mon", session="Strength A", blocks=mon_blocks),
        TrainingDay(
            day="Tue",
            session="MAF Aerobic",
            blocks=[
                TrainingBlock(
                    label="MAF run/bike/ruck",
                    kind="note",
                    note="See Overview aerobic-build table for duration. Cap at MAF HR.",
                )
            ],
        ),
        TrainingDay(
            day="Wed",
            session="Strength B",
            blocks=[
                TrainingBlock(label="Bench Press — main", kind="main", lift_key="bench_press"),
                TrainingBlock(
                    label="Back Squat — light technique",
                    kind="accessory",
                    lift_key="back_squat",
                    accessory_sets=_LIGHT_TECHNIQUE,
                ),
                TrainingBlock(
                    label="DB row", kind="note", note="4 sets x 10 each side, heavy. 60s rest."
                ),
                TrainingBlock(
                    label="Face pulls + band pull-aparts",
                    kind="note",
                    note="3 sets x 15 each, supersetted.",
                ),
            ],
        ),
        TrainingDay(
            day="Thu",
            session="Aerobic + Hangboard",
            blocks=[
                TrainingBlock(
                    label="MAF or 30/30 (see Overview)",
                    kind="note",
                    note="Per aerobic-build table.",
                ),
                TrainingBlock(
                    label="Hangboard — Hörst 7-53",
                    kind="note",
                    note="3 sets x 6 hangs. 7s on / 53s off. Add weight when last set is clean.",
                ),
                TrainingBlock(
                    label="Antagonist work",
                    kind="note",
                    note="Band ext rot 3x12 + scap pull-ups 3x10 + narrow push-ups 3x12 + wrist ext 3x15.",
                ),
            ],
        ),
        TrainingDay(
            day="Fri",
            session="Strength C",
            blocks=[
                TrainingBlock(label="Deadlift — main", kind="main", lift_key="deadlift"),
                TrainingBlock(
                    label="Bench Press — light",
                    kind="accessory",
                    lift_key="bench_press",
                    accessory_sets=_LIGHT_TECHNIQUE,
                ),
                TrainingBlock(
                    label="Power Clean — speed",
                    kind="accessory",
                    lift_key="power_clean",
                    accessory_sets=_POWER_SPEED,
                ),
                TrainingBlock(
                    label="Loaded carry",
                    kind="note",
                    note="3 sets x 50m farmer carry @ 2×70# DB, fast walk.",
                ),
            ],
        ),
        TrainingDay(
            day="Sat",
            session="Long Pack + Hangboard",
            blocks=[
                TrainingBlock(
                    label="Long pack hike",
                    kind="note",
                    note="See aerobic-build table. 25-35# pack. Cap at MAF HR.",
                ),
                TrainingBlock(
                    label="Hangboard — Hörst 7-53",
                    kind="note",
                    note="3 sets x 6 hangs. Same load as Thu (or +5 lb if Thu went clean).",
                ),
            ],
        ),
        TrainingDay(
            day="Sun",
            session="Rest",
            blocks=[
                TrainingBlock(
                    label="Active recovery optional",
                    kind="note",
                    note="20 min walk + 15 min mobility on any tight spots.",
                )
            ],
        ),
    ]


def _waves(tm_rows: list[TrainingMaxRow]) -> list[Wave]:
    waves: list[Wave] = []
    for w in range(1, 4):
        tms = {row.lift_key: (row.tm_wave1, row.tm_wave2, row.tm_wave3)[w - 1] for row in tm_rows}
        waves.append(
            Wave(wave_num=w, week_range=f"Wk {(w - 1) * 4 + 1}-{w * 4}", training_maxes=tms)
        )
    return waves


def build_default_plan(
    athlete: Athlete,
    title: str,
    goals: list[str],
    priority_lifts: list[str] | None = None,
    template_name: TemplateName = "531_bbb",
) -> CyclePlan:
    """Assemble the deterministic base cycle plan.

    ``goals`` are priority-ordered Overview goal lines (the agent writes these).
    ``priority_lifts`` (lift_keys) bias accessory volume — e.g. ``bench_press``
    adds a pressing-volume accessory.
    """
    priorities = priority_lifts or []
    tm_rows = _training_max_rows(athlete)
    maf_cap = compute_maf(athlete.age)
    return CyclePlan(
        title=title,
        subtitle=(
            f"12 weeks  •  3 waves × 4 weeks  •  Built from baseline "
            f"(BW {athlete.bodyweight_lb:g}, age {athlete.age}, RHR {athlete.resting_hr_bpm})"
        ),
        goals=goals,
        program_model="hybrid_531",
        template_name=template_name,
        maf_cap_bpm=maf_cap,
        training_maxes=tm_rows,
        weekly_schedule=_weekly_schedule(),
        loading_scheme=_loading_scheme(template_name),
        aerobic_build=_aerobic_build(maf_cap),
        hangboard_notes=_hangboard_notes(),
        nutrition=_nutrition(athlete),
        day_template=_day_template(priorities),
        waves=_waves(tm_rows),
    )


# ---------------------------------------------------------------------------
# Shared helpers for the non-hybrid program models
# ---------------------------------------------------------------------------


def _note(label: str, text: str) -> TrainingBlock:
    return TrainingBlock(label=label, kind="note", note=text)


def _phase_waves(phases: list[tuple[str, list[str]]]) -> list[Wave]:
    """Build 4 mesocycle waves from (phase_name, [4 week labels]) tuples."""
    waves: list[Wave] = []
    for i, (phase, labels) in enumerate(phases, start=1):
        waves.append(
            Wave(
                wave_num=i,
                week_range=f"Wk {(i - 1) * 4 + 1}-{i * 4}",
                phase=phase,
                week_labels=labels,
            )
        )
    return waves


# ---------------------------------------------------------------------------
# Linear-novice program (Practical Programming novice tier)
# ---------------------------------------------------------------------------


def _novice_nutrition(athlete: Athlete, deficit: bool) -> NutritionProfile:
    bw = athlete.bodyweight_lb
    # Novice on a modest cut: protein 0.8 g/lb, ~250 cal/day deficit.
    cal_lb = 16.0 if deficit else 18.0
    novice_days: list[tuple[DayType, float]] = [
        ("rest", 0.0),
        ("light", 1.5),
        ("moderate", 3.0),
        ("hard", 3.0),
    ]
    carbs = {
        day: compute_macros(bw, day, protein_g_per_lb=0.8, cal_per_lb=cal_lb + bump)["carbs_g"]
        for day, bump in novice_days
    }
    protein_g = compute_macros(bw, "moderate", protein_g_per_lb=0.8)["protein_g"]
    cal_low = round((cal_lb - 0.5) * bw)
    cal_high = round((cal_lb + 2.5) * bw)
    notes = [
        f"Calories: ~{cal_low:,}-{cal_high:,}/day — a modest deficit (~250 cal) for the ~10 lb "
        "loss goal. Don't crash-diet while learning to train; small deficit only.",
        f"Protein: 0.8 g/lb = {protein_g} g/day. High for a novice but it protects muscle in a "
        "deficit and aids recovery between sessions.",
        "Carbs: most around your 3 lifting days and the Saturday long effort; lower on rest days.",
        "Fat fills the rest; keep it ≥0.4 g/lb. Don't fear it on rest days.",
        "Weigh weekly, same day/time. Aim for ~0.5-0.75 lb/week down — slow loss keeps strength.",
    ]
    return NutritionProfile(
        calories_low=cal_low,
        calories_high=cal_high,
        protein_g=protein_g,
        carbs_by_day=carbs,
        fat_floor_g=round(0.4 * bw),
        notes=notes,
    )


def _novice_days(phase_idx: int) -> list[TrainingDay]:
    """Weekly template for a novice; aerobic + ruck scale by phase (0-3)."""
    runwalk = [
        "Run 1 min / walk 2 min × 8 (24 min). Easy — you can talk the whole time.",
        "Run 2 min / walk 1 min × 8 (24 min). Stay conversational; MAF cap applies.",
        "Run 5 min / walk 1 min × 5 (30 min). Build continuous time on feet.",
        "Continuous easy run 30-40 min at MAF cap. This is race-simulation pace.",
    ][phase_idx]
    longday = [
        "Walk/jog 30-40 min on varied terrain. Habit + base.",
        "Continuous jog 2-3 mi, easy. Walk the hills if needed.",
        "Run 3-4 mi easy + 20 min ruck @ 10-15 lb afterward.",
        "Run 5-6 mi (event distance build) OR 60 min ruck @ 20 lb. Taper this in wk16.",
    ][phase_idx]
    squat_load = [
        "Start: empty bar 45 lb (or 35 lb goblet). +5 lb every session you hit all reps.",
        "Keep adding 5 lb/session while reps stay clean; if you miss, repeat the weight.",
        "Progress continues; if a lift stalls twice, drop 10% and rebuild (first deload).",
        "Hold loads steady into the event; this is a peak/taper block, not a PR block.",
    ][phase_idx]
    return [
        TrainingDay(
            day="Mon",
            session="Full Body A (linear)",
            blocks=[
                _note(
                    "Back Squat (or goblet) — 3×5", f"This IS the progression, not %s. {squat_load}"
                ),
                _note(
                    "DB bench / push-up progression — 3×8", "Add reps then load. Push-ups count."
                ),
                _note("1-arm DB row — 3×10/side", "Build the pull for obstacles."),
                _note(
                    "Plank 3× max hold + dead hang 3× max", "Grip + trunk for monkey bars/hangs."
                ),
            ],
        ),
        TrainingDay(
            day="Tue",
            session="Run/Walk intervals",
            blocks=[_note("Run/walk", runwalk)],
        ),
        TrainingDay(
            day="Wed",
            session="Full Body B (linear)",
            blocks=[
                _note(
                    "Deadlift / KB hinge — 1×5 work set", "Light, perfect form. +5-10 lb/session."
                ),
                _note("Overhead press — 3×5", "Empty bar to start; +2.5-5 lb/session."),
                _note(
                    "Lat pulldown → pull-up progression — 4×6",
                    "You have 5 strict pull-ups: do 3×3 weighted-negative + banded reps toward 10+.",
                ),
                _note(
                    "Farmer carry 3×40 m + towel dead hang 3×20s", "Grip is a Tough Mudder limiter."
                ),
            ],
        ),
        TrainingDay(
            day="Thu",
            session="Rest / mobility",
            blocks=[_note("Easy", "20 min walk + mobility on tight spots.")],
        ),
        TrainingDay(
            day="Fri",
            session="Full Body C (linear)",
            blocks=[
                _note("Front squat or split squat — 3×5", "Add load slowly; quality reps."),
                _note("Incline DB press — 3×8 + band pull-aparts 3×15", "Push/pull balance."),
                _note(
                    "Obstacle skills — 15 min",
                    "Wall climb-overs, bear crawl, monkey-bar swings or hangs, rope-pull rows.",
                ),
                _note("Sled/prowler push or hill walk 3×", "Low-skill conditioning."),
            ],
        ),
        TrainingDay(day="Sat", session="Long aerobic / ruck", blocks=[_note("Long day", longday)]),
        TrainingDay(
            day="Sun",
            session="Rest",
            blocks=[_note("Recovery", "Full rest or gentle walk + stretch.")],
        ),
    ]


def build_linear_novice_plan(
    athlete: Athlete,
    title: str,
    goals: list[str],
    weeks: int = 16,
    deficit: bool = True,
) -> CyclePlan:
    """A Practical-Programming novice-tier plan: linear strength (no %s/TMs),
    couch-to-5K-style run/walk build, ruck progression, grip/pull emphasis for an
    obstacle race. No barbell 1RMs are fabricated — progression is per-session."""
    maf_cap = compute_maf(athlete.age)
    phases = [
        ("Foundation — movement + base", ["wk1 learn", "wk2", "wk3", "wk4 first deload"]),
        ("Build — linear add + run/walk", ["wk5", "wk6", "wk7", "wk8 deload"]),
        ("Specific — continuous runs + ruck", ["wk9", "wk10", "wk11", "wk12 deload"]),
        (
            "Peak / taper — obstacle prep + event",
            ["wk13", "wk14 peak", "wk15 sharpen", "wk16 EVENT"],
        ),
    ]
    waves = _phase_waves(phases)
    for i, wave in enumerate(waves):
        wave.days_override = _novice_days(i)

    aerobic_headers = ["Phase", "Tue intervals", "Sat long / ruck", "Strength", "Notes"]
    aerobic = [
        TableRow(
            cells=[
                "Wk 1-4",
                "Run 1'/walk 2'×8",
                "30-40 min walk/jog",
                "Learn lifts, 3×5 linear",
                "Build the habit",
            ]
        ),
        TableRow(
            cells=[
                "Wk 5-8",
                "Run 2'/walk 1'×8",
                "Jog 2-3 mi + ruck 20' @ 0-10 lb",
                "+5 lb/session",
                "Ruck intro",
            ]
        ),
        TableRow(
            cells=[
                "Wk 9-12",
                "Run 5'/walk 1'×5",
                "Run 3-4 mi + ruck 40' @ 10-15 lb",
                "Linear continues",
                "Add pack load",
            ]
        ),
        TableRow(
            cells=[
                "Wk 13-16",
                "Continuous 30-40 min",
                "Run 5-6 mi / ruck 60' @ 20 lb",
                "Hold loads",
                "Taper wk16 → event",
            ]
        ),
    ]
    return CyclePlan(
        title=title,
        subtitle=(
            f"{weeks} weeks  •  4 phases × 4 weeks  •  Novice linear progression  •  "
            f"Built from baseline (BW {athlete.bodyweight_lb:g}, age {athlete.age}, "
            f"{athlete.training_age_months or 0} mo training age)"
        ),
        goals=goals,
        program_model="linear_novice",
        maf_cap_bpm=maf_cap,
        aerobic_build=aerobic,
        aerobic_headers=aerobic_headers,
        nutrition=_novice_nutrition(athlete, deficit),
        day_template=_novice_days(0),
        waves=waves,
    )


# ---------------------------------------------------------------------------
# Marathon-block program (Pfitzinger-style base/build/peak/taper)
# ---------------------------------------------------------------------------


def _marathon_nutrition(athlete: Athlete) -> NutritionProfile:
    bw = athlete.bodyweight_lb
    # Endurance: protein 0.75 g/lb, carbs scale steeply with the day's run load,
    # calorie surplus on big days to fuel 60-70 mpw.
    day_carbs: dict[str, float] = {"rest": 2.0, "light": 3.0, "moderate": 4.0, "hard": 5.0}
    day_cal: dict[str, float] = {"rest": 16.0, "light": 19.0, "moderate": 22.0, "hard": 26.0}
    endurance_days: list[DayType] = ["rest", "light", "moderate", "hard"]
    carbs = {
        day: compute_macros(
            bw, day, protein_g_per_lb=0.75, carb_g_per_lb=day_carbs[day], cal_per_lb=day_cal[day]
        )["carbs_g"]
        for day in endurance_days
    }
    protein_g = compute_macros(bw, "moderate", protein_g_per_lb=0.75)["protein_g"]
    notes = [
        f"Carb-periodized for mileage. Long-run / quality days: ~5 g/lb = {carbs['hard']} g carbs. "
        f"Easy days: ~3 g/lb = {carbs['light']} g. Recovery/rest: ~2 g/lb = {carbs['rest']} g.",
        f"Protein: 0.75 g/lb = {protein_g} g/day — enough for a lean runner; more just displaces carbs.",
        f"Calories surplus on peak days (BW×26 ≈ {round(26 * bw):,}) to support 65-72 mpw; "
        "don't diet inside a marathon build.",
        "Carb-load the 2-3 days before the long run and race: push to 5-6 g/lb, lower fat/fiber.",
        "Practice race fueling on long runs: 30-60 g carb/hr (gels/drink). Train the gut.",
        "Daily fat ≥0.4 g/lb for hormones; keep it low immediately around runs.",
    ]
    return NutritionProfile(
        calories_low=round(16 * bw),
        calories_high=round(26 * bw),
        protein_g=protein_g,
        carbs_by_day=carbs,
        fat_floor_g=round(0.4 * bw),
        notes=notes,
    )


def _marathon_days(phase_idx: int, maf_cap: int) -> list[TrainingDay]:
    """Weekly template for a marathon block; volume/quality scale by phase (0-3)."""
    easy_mi = [7, 8, 8, 5][phase_idx]
    tue_quality = [
        "Tempo 4-5 mi @ LT (half-marathon effort, ~comfortably hard).",
        "Tempo 6-7 mi @ LT, or 2×3 mi @ LT with 3' jog.",
        "VO2: 5×1000 m @ 5K pace (~3:45/km) w/ 3' jog; or 6×800 m.",
        "Sharpening: 3-4 mi @ marathon pace + 4×100 m strides. Stay fresh.",
    ][phase_idx]
    thu_quality = [
        "Easy + 6×100 m strides after.",
        "Marathon-pace: 8-10 mi w/ 4-6 mi @ MP (sub-3 = ~6:50/mi).",
        "Threshold: 2×2 mi @ LT w/ 3' jog. Last hard week.",
        "Easy 4-5 mi + strides. Race is the hard effort.",
    ][phase_idx]
    long_run = [
        "Long run 16-18 mi easy (≤MAF). Time on feet.",
        "Long run 18-20 mi; final 4-6 mi @ MP from wk8.",
        "Long run 20→22 mi peak (wk11-12); 6-8 mi @ MP segment.",
        "Cutback: 16 → 12 → 8 → race. Keep legs sharp, not tired.",
    ][phase_idx]
    return [
        TrainingDay(
            day="Mon",
            session="Easy + strength #1",
            blocks=[
                _note(
                    f"Easy run {easy_mi} mi",
                    f"Z1-Z2, ≤{maf_cap} bpm. Truly easy — this is the 80%.",
                ),
                _note(
                    "Easy Strength — 2×5",
                    "Back squat + deadlift + press @ ~80%, never to failure. Pavel Easy Strength: "
                    "submaximal, frequent, leaves the legs fresh for running. (Brief §3.3)",
                ),
            ],
        ),
        TrainingDay(day="Tue", session="Quality #1", blocks=[_note("Workout", tue_quality)]),
        TrainingDay(
            day="Wed",
            session="Medium-long easy",
            blocks=[_note(f"Easy {easy_mi + 2} mi", f"Z2, ≤{maf_cap} bpm. Recover from Tuesday.")],
        ),
        TrainingDay(day="Thu", session="Quality #2", blocks=[_note("Workout", thu_quality)]),
        TrainingDay(
            day="Fri",
            session="Recovery + strength #2",
            blocks=[
                _note("Recovery run 4-5 mi", "Very easy or off. Legs should feel better after."),
                _note(
                    "Durability strength (light)",
                    "Single-leg RDL, step-ups, hip/glute + calf/Achilles eccentrics. Posterior-chain "
                    "insurance only — no max effort. Strength bends to maintenance here (Brief §3.2).",
                ),
            ],
        ),
        TrainingDay(day="Sat", session="Long run", blocks=[_note("Long run", long_run)]),
        TrainingDay(
            day="Sun",
            session="Recovery / rest",
            blocks=[_note("Recovery", "Easy 4-5 mi or full rest. Sleep + carbs.")],
        ),
    ]


def build_endurance_block_plan(
    athlete: Athlete,
    title: str,
    goals: list[str],
    peak_mileage: int = 70,
    long_run_peak_mi: int = 22,
    weeks: int = 16,
) -> CyclePlan:
    """A Pfitzinger-style marathon block: base/build/peak/taper, polarized 80/20,
    long-run progression with marathon-pace work, strength demoted to Easy
    Strength maintenance. No hangboard, no concurrent strength block."""
    maf_cap = compute_maf(athlete.age)
    start_mpw = int(athlete.current_weekly_mileage or 50)
    phases = [
        (
            "Base — aerobic volume",
            [f"{start_mpw} mpw", f"{start_mpw + 4} mpw", f"{start_mpw + 6} mpw", "cutback"],
        ),
        ("Build — LT + marathon pace", ["+LT work", "MP segments", "build", "cutback"]),
        (
            "Peak — VO2 + 22mi long",
            ["VO2", f"{peak_mileage} mpw", f"{long_run_peak_mi}mi long", "cutback"],
        ),
        ("Taper — sharpen to race", ["taper -20%", "taper -40%", "race week", "RACE"]),
    ]
    waves = _phase_waves(phases)
    for i, wave in enumerate(waves):
        wave.days_override = _marathon_days(i, maf_cap)

    aerobic_headers = ["Phase", "Weekly mileage", "Quality (2/wk)", "Long run", "Notes"]
    aerobic = [
        TableRow(
            cells=[
                "Wk 1-4 Base",
                f"{start_mpw}-{start_mpw + 8}",
                "1× tempo @ LT",
                "16-18 mi easy",
                f"80% easy ≤{maf_cap} bpm",
            ]
        ),
        TableRow(
            cells=[
                "Wk 5-8 Build",
                f"{start_mpw + 8}-{peak_mileage - 6}",
                "tempo + MP segments",
                "18-20 mi, MP from wk8",
                "marathon-pace fitness",
            ]
        ),
        TableRow(
            cells=[
                "Wk 9-12 Peak",
                f"{peak_mileage - 4}-{peak_mileage}",
                "VO2 (1km/800m) + LT",
                f"20→{long_run_peak_mi} mi peak",
                "highest load wk11-12",
            ]
        ),
        TableRow(
            cells=[
                "Wk 13-16 Taper",
                "55→40→30→race",
                "short MP + strides",
                "16→12→8→26.2",
                "freshness > fitness",
            ]
        ),
    ]
    return CyclePlan(
        title=title,
        subtitle=(
            f"{weeks} weeks  •  Base/Build/Peak/Taper  •  Marathon block  •  "
            f"PR {athlete.marathon_pr or 'n/a'} → sub-3  •  "
            f"from {start_mpw} mpw (BW {athlete.bodyweight_lb:g}, age {athlete.age})"
        ),
        goals=goals,
        program_model="marathon_block",
        maf_cap_bpm=maf_cap,
        aerobic_build=aerobic,
        aerobic_headers=aerobic_headers,
        nutrition=_marathon_nutrition(athlete),
        day_template=_marathon_days(0, maf_cap),
        waves=waves,
    )
