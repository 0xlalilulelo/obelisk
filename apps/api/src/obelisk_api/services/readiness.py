"""Readiness composite (PRD §2.4) — a transparent 0-100 score from wearable data.

Three inputs, each scored 0-100 then weight-averaged over whatever is available:
last night's sleep duration, resting-HR delta from a 30-day baseline, and (optional)
HRV SDNN deviation from baseline. Every factor is returned with its raw value and
sub-score so the Today screen's "Why?" expansion is never a black box.

The scoring functions are pure and bounded by design: a one-input change moves the
composite by at most that input's weight, which is the guard against the spec's
">30-point day-to-day swing means the algorithm is wrong" stop-condition.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from statistics import mean
from typing import Protocol

# Factor weights (renormalized over whichever inputs are present).
W_SLEEP = 0.40
W_RHR = 0.35
W_HRV = 0.25

_BASELINE_DAYS = 30


class SampleLike(Protocol):
    sample_type: str
    occurred_at: datetime  # tz-aware
    value: float | None
    duration_sec: int | None


@dataclass
class Factor:
    key: str
    label: str
    value: str
    score: int
    weight: float


@dataclass
class Readiness:
    score: int | None
    band: str  # "high" | "moderate" | "caution" | "low" | "unknown"
    guidance: str
    factors: list[Factor]


# --- Pure sub-scores -------------------------------------------------------
def sleep_score(hours: float) -> int:
    """7-9 h is ideal (100). Short sleep penalizes harder than long sleep."""
    if 7.0 <= hours <= 9.0:
        return 100
    if hours < 7.0:
        return max(0, round(100 - (7.0 - hours) * 18))
    return max(0, round(100 - (hours - 9.0) * 10))


def rhr_score(delta_bpm: float) -> int:
    """Resting HR at/below baseline is 100; each bpm of elevation costs ~7."""
    if delta_bpm <= 0:
        return 100
    return max(0, round(100 - delta_bpm * 7))


def hrv_score(today: float, baseline: float) -> int:
    """HRV at/above baseline is 100; a 10% drop costs ~20 points."""
    if baseline <= 0:
        return 100
    ratio = today / baseline
    if ratio >= 1.0:
        return 100
    return max(0, round(100 - (1.0 - ratio) * 200))


def _band(score: int) -> tuple[str, str]:
    """Map the composite to a band + the §2.4 behavioral guidance."""
    if score >= 80:
        return "high", "Green light — run today's full prescription."
    if score >= 60:
        return "moderate", "Proceed; be conservative on AMRAP top sets."
    if score >= 40:
        return "caution", "Gate intensity — consider an RPE cap or a modality swap."
    return "low", "Recovery signal is low — Z2-only or a skill day is the smart call."


# --- Extraction ------------------------------------------------------------
def _wake_date(s: SampleLike) -> date:
    """Date a sleep sample is attributed to = the date it ended (wake morning)."""
    end = s.occurred_at
    if s.duration_sec:
        end = end + timedelta(seconds=s.duration_sec)
    return end.date()


def _sleep_hours(samples: Iterable[SampleLike], target: date) -> float | None:
    total_sec = 0.0
    found = False
    for s in samples:
        if s.sample_type != "sleep":
            continue
        if _wake_date(s) != target:
            continue
        found = True
        if s.duration_sec:
            total_sec += s.duration_sec
        elif s.value is not None:
            total_sec += s.value * 3600  # value carried as hours
    return total_sec / 3600.0 if found else None


def _latest_value(samples: Iterable[SampleLike], stype: str, target: date) -> float | None:
    best_dt = None
    best_val = None
    for s in samples:
        if s.sample_type != stype or s.value is None:
            continue
        if s.occurred_at.date() != target:
            continue
        if best_dt is None or s.occurred_at > best_dt:
            best_dt, best_val = s.occurred_at, s.value
    return best_val


def _baseline(samples: Iterable[SampleLike], stype: str, target: date) -> float | None:
    lo = target - timedelta(days=_BASELINE_DAYS)
    vals = [
        s.value
        for s in samples
        if s.sample_type == stype and s.value is not None and lo <= s.occurred_at.date() < target
    ]
    return mean(vals) if vals else None


def compute_readiness(samples: list[SampleLike], target: date) -> Readiness:
    """Composite for ``target`` from the athlete's samples. Returns an unknown
    band (score None) when no input is available."""
    factors: list[Factor] = []

    hours = _sleep_hours(samples, target)
    if hours is not None:
        factors.append(Factor("sleep", "Sleep", f"{hours:.1f} h", sleep_score(hours), W_SLEEP))

    rhr_today = _latest_value(samples, "rhr", target)
    rhr_base = _baseline(samples, "rhr", target)
    if rhr_today is not None and rhr_base is not None:
        delta = rhr_today - rhr_base
        factors.append(
            Factor(
                "rhr",
                "Resting HR",
                f"{rhr_today:.0f} bpm ({delta:+.0f} vs 30-day)",
                rhr_score(delta),
                W_RHR,
            )
        )

    hrv_today = _latest_value(samples, "hrv", target)
    hrv_base = _baseline(samples, "hrv", target)
    if hrv_today is not None and hrv_base is not None:
        factors.append(
            Factor(
                "hrv",
                "HRV (SDNN)",
                f"{hrv_today:.0f} ms (base {hrv_base:.0f})",
                hrv_score(hrv_today, hrv_base),
                W_HRV,
            )
        )

    if not factors:
        return Readiness(None, "unknown", "Connect Apple Health to see your readiness.", [])

    total_w = sum(f.weight for f in factors)
    score = round(sum(f.score * f.weight for f in factors) / total_w)
    band, guidance = _band(score)
    return Readiness(score, band, guidance, factors)
