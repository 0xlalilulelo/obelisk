"""Bound-check coverage for compute_macros' optional override params.

The deterministic tools file is held at 100% (correctness-critical surface). The
ported POC suite exercises defaults + the calorie floor; these cover the override
validation branches that the agent could reach via calibrated macro requests.
"""

from __future__ import annotations

import pytest

from obelisk_api.tools.deterministic import compute_macros


def test_protein_override_out_of_range_raises() -> None:
    with pytest.raises(ValueError, match="protein_g_per_lb"):
        compute_macros(175, "hard", protein_g_per_lb=2.0)


def test_carb_override_out_of_range_raises() -> None:
    with pytest.raises(ValueError, match="carb_g_per_lb"):
        compute_macros(175, "hard", carb_g_per_lb=9.0)


def test_cal_override_out_of_range_raises() -> None:
    with pytest.raises(ValueError, match="cal_per_lb"):
        compute_macros(175, "hard", cal_per_lb=5.0)


def test_marathon_style_overrides_apply() -> None:
    """A marathoner's calibrated macros: high carbs, lower protein (within bounds)."""
    result = compute_macros(150, "hard", protein_g_per_lb=0.75, carb_g_per_lb=4.0)
    assert result["protein_g"] == 113  # 0.75 * 150, rounded
    assert result["carbs_g"] == 600  # 4.0 * 150
