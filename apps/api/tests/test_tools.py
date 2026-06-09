"""Unit tests for the deterministic tools.

Coverage target: >90% of ``src/tools.py``. Every tool is exercised for correct
output and for input-validation edge cases.
"""

from __future__ import annotations

import pytest

from obelisk_api.tools.deterministic import (
    compute_1rm,
    compute_macros,
    compute_maf,
    compute_training_max,
    compute_warmup_ramp,
    get_periodization_template,
    lookup_advisor_principle,
    round_half_up,
    round_to_5,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Rounding helpers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0.0, 0), (0.4, 0), (0.5, 1), (1.5, 2), (2.5, 3), (87.5, 88), (262.5, 263)],
)
def test_round_half_up(value: float, expected: int) -> None:
    assert round_half_up(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0, 0), (143, 145), (142, 140), (165, 165), (187, 185), (2.5, 5), (12.4, 10)],
)
def test_round_to_5(value: float, expected: int) -> None:
    assert round_to_5(value) == expected


# ---------------------------------------------------------------------------
# compute_1rm (Epley)
# ---------------------------------------------------------------------------


def test_compute_1rm_known_values() -> None:
    # Epley: 235 * (1 + 3/30) = 258.5 -> nearest 5 = 260
    assert compute_1rm(235, 3) == 260
    # 315 * (1 + 2/30) = 336.0 -> 335
    assert compute_1rm(315, 2) == 335


def test_compute_1rm_single_rep_is_weight_rounded() -> None:
    # 1 rep: 1RM = weight * (1 + 1/30) ~ weight; rounds to nearest 5.
    assert compute_1rm(200, 1) == 205  # 200 * 1.0333 = 206.7 -> 205
    assert compute_1rm(225, 1) == 235  # 232.5 -> nearest 5, halves up -> 235


def test_compute_1rm_rejects_bad_input() -> None:
    with pytest.raises(ValueError, match="weight_lb must be positive"):
        compute_1rm(0, 5)
    with pytest.raises(ValueError, match="weight_lb must be positive"):
        compute_1rm(-10, 5)
    with pytest.raises(ValueError, match="reps must be >= 1"):
        compute_1rm(200, 0)


# ---------------------------------------------------------------------------
# compute_training_max
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("est_1rm", "expected_tm"),
    [
        (259, 220),  # Josh back squat: 220.15 -> 220
        (182, 155),  # Josh bench: 154.7 -> 155
        (336, 285),  # Josh deadlift: 285.6 -> 285
        (123, 105),  # Josh press: 104.55 -> 105
        (248, 210),  # Josh front squat: 210.8 -> 210
    ],
)
def test_compute_training_max_default_conservatism(est_1rm: int, expected_tm: int) -> None:
    assert compute_training_max(est_1rm) == expected_tm


def test_compute_training_max_custom_conservatism() -> None:
    assert compute_training_max(300, 0.90) == 270
    assert compute_training_max(300, 1.0) == 300


def test_compute_training_max_rejects_bad_input() -> None:
    with pytest.raises(ValueError, match="est_1rm must be positive"):
        compute_training_max(0)
    with pytest.raises(ValueError, match="conservatism"):
        compute_training_max(300, 0.4)
    with pytest.raises(ValueError, match="conservatism"):
        compute_training_max(300, 1.1)


# ---------------------------------------------------------------------------
# compute_macros
# ---------------------------------------------------------------------------


def test_compute_macros_protein_and_carbs_for_josh() -> None:
    moderate = compute_macros(175, "moderate")
    assert moderate["protein_g"] == 175  # 1.0 g/lb
    assert moderate["carbs_g"] == 263  # 1.5 g/lb, 262.5 -> 263
    rest = compute_macros(175, "rest")
    assert rest["carbs_g"] == 88  # 0.5 g/lb, 87.5 -> 88
    hard = compute_macros(175, "hard")
    assert hard["carbs_g"] == 350  # 2.0 g/lb
    light = compute_macros(175, "light")
    assert light["carbs_g"] == 175  # 1.0 g/lb


def test_compute_macros_calories_are_self_consistent() -> None:
    for day in ("rest", "light", "moderate", "hard"):
        m = compute_macros(175, day)  # type: ignore[arg-type]
        recomputed = 4 * m["protein_g"] + 4 * m["carbs_g"] + 9 * m["fat_g"]
        assert m["calories"] == recomputed


def test_compute_macros_respects_fat_floor() -> None:
    # On a hard, very high-carb day for a light athlete, fat must not go below floor.
    m = compute_macros(130, "hard")
    assert m["fat_g"] >= round_half_up(0.4 * 130)


def test_compute_macros_enforces_calorie_floor() -> None:
    # A deep-cut request (low cal_per_lb) is clamped UP toward max(BW*10, 1200).
    # (Within one fat-gram of the floor due to integer-gram rounding.)
    m = compute_macros(145, "rest", cal_per_lb=8.0)  # 8*145 = 1160 requested
    assert m["calories"] >= 1440  # clamped up from 1160 to ~1450 (BW*10)
    # A light athlete floors at the 1200 absolute, not BW*10 (=1050).
    light = compute_macros(105, "rest", cal_per_lb=8.0)
    assert light["calories"] >= 1195
    # The macro tool can never emit a 1,200-cal target for a 145-lb adult.
    assert compute_macros(145, "rest")["calories"] >= 1440


def test_compute_macros_rejects_bad_input() -> None:
    with pytest.raises(ValueError, match="bw_lb must be positive"):
        compute_macros(0, "rest")
    with pytest.raises(ValueError, match="day_type"):
        compute_macros(175, "extreme")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# compute_maf
# ---------------------------------------------------------------------------


def test_compute_maf() -> None:
    assert compute_maf(34) == 146  # Josh
    assert compute_maf(20) == 160


def test_compute_maf_rejects_bad_input() -> None:
    with pytest.raises(ValueError, match="age"):
        compute_maf(0)
    with pytest.raises(ValueError, match="age"):
        compute_maf(120)


# ---------------------------------------------------------------------------
# get_periodization_template
# ---------------------------------------------------------------------------


def test_get_periodization_template_531_bbb_structure() -> None:
    t = get_periodization_template("531_bbb")
    assert t["name"] == "531_bbb"
    assert len(t["weeks"]) == 4
    week1 = t["weeks"][0]
    assert [s["pct"] for s in week1["main_sets"]] == [0.65, 0.75, 0.85]
    assert week1["main_sets"][2]["amrap"] is True
    # Week 4 is the deload.
    assert t["weeks"][3]["is_deload"] is True
    assert [s["pct"] for s in t["weeks"][3]["main_sets"]] == [0.40, 0.50, 0.60]


@pytest.mark.parametrize("name", ["531_bbb", "rat6", "juggernaut", "tactical_barbell_operator"])
def test_get_periodization_template_all_valid(name: str) -> None:
    t = get_periodization_template(name)  # type: ignore[arg-type]
    assert t["weeks"]
    assert t["weekly_split"]
    for week in t["weeks"]:
        assert week["main_sets"]
        for s in week["main_sets"]:
            assert 0.0 < s["pct"] <= 1.0
            assert s["reps"] >= 1


def test_get_periodization_template_juggernaut_rep_brackets() -> None:
    t = get_periodization_template("juggernaut")
    assert [w["main_sets"][0]["reps"] for w in t["weeks"]] == [10, 8, 5, 3]


def test_get_periodization_template_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="name must be one of"):
        get_periodization_template("starting_strength")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# compute_warmup_ramp
# ---------------------------------------------------------------------------


def test_compute_warmup_ramp_matches_cycle1_wave1_squat() -> None:
    # Wave 1 squat TM = 220 (Cycle_1 reference).
    assert compute_warmup_ramp(220, 1, 1) == 145  # 65% -> 143 -> 145
    assert compute_warmup_ramp(220, 1, 2) == 165  # 75%
    assert compute_warmup_ramp(220, 1, 3) == 185  # 85% -> 187 -> 185


def test_compute_warmup_ramp_matches_cycle1_wave1_bench() -> None:
    # Wave 1 bench TM = 155.
    assert compute_warmup_ramp(155, 1, 1) == 100  # 65% -> 100.75 -> 100
    assert compute_warmup_ramp(155, 1, 3) == 130  # 85% -> 131.75 -> 130


def test_compute_warmup_ramp_deload_week() -> None:
    assert compute_warmup_ramp(220, 4, 1) == 90  # 40% -> 88 -> 90
    assert compute_warmup_ramp(220, 4, 3) == 130  # 60% -> 132 -> 130


def test_compute_warmup_ramp_rejects_bad_input() -> None:
    with pytest.raises(ValueError, match="week must be 1-4"):
        compute_warmup_ramp(220, 5, 1)
    with pytest.raises(ValueError, match="set_num must be 1-3"):
        compute_warmup_ramp(220, 1, 4)
    with pytest.raises(ValueError, match="tm must be positive"):
        compute_warmup_ramp(0, 1, 1)


# ---------------------------------------------------------------------------
# lookup_advisor_principle
# ---------------------------------------------------------------------------


def test_lookup_advisor_principle_finds_relevant_section() -> None:
    result = lookup_advisor_principle("hangboard finger strength")
    assert "Climbing" in result or "Hangboard" in result or "Hörst" in result


def test_lookup_advisor_principle_polarized_conditioning() -> None:
    result = lookup_advisor_principle("polarized conditioning 80 20")
    assert "polariz" in result.lower() or "aerobic" in result.lower()


def test_lookup_advisor_principle_handles_no_match() -> None:
    result = lookup_advisor_principle("quantum blockchain cryptocurrency")
    assert "No Advisor Brief section" in result or "##" in result


def test_lookup_advisor_principle_empty_query() -> None:
    assert "No searchable terms" in lookup_advisor_principle("a")
