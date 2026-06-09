"""Drive an out-of-distribution validation session for Sarah or Marcus.

Usage: python run_ood.py sarah | marcus

Same 6-message structure as Josh's run: Block creation + 5 follow-ups + a final
question. Change-requests carry a clarification the "athlete" supplies if the
coach asks before staging; staged diffs are auto-approved. Saves transcript +
workbook + cost summary to runs/<id>_<tag>/. Hard-stops at $5.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

from src.agent import BlockCoach
from src.models import Athlete
from src.persistence import RUNS_DIR, Block, new_block_id

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

COST_STOP_USD = 5.0
APPROVAL = "Yes, that looks right — approve and commit it."

# (message, optional clarification if the coach asks before staging a change)
Followup = tuple[str, str | None]

CONFIGS: dict[str, dict[str, object]] = {
    "sarah": {
        "athlete": "data/sample_sarah.json",
        "goal": "16-week build to finish my first Tough Mudder; lose ~10 lb; "
        "never tested 1RMs so start conservative",
        "followups": [
            ("Why did you pick these starting weights?", None),
            (
                "Swap any heavy back squat work for goblet squats since I haven't "
                "barbell-squatted in months.",
                "Yes — goblet squats in place of barbell back squat for the whole cycle. "
                "Go ahead and stage it.",
            ),
            (
                "I have a busy work trip in week 6 — only a hotel gym for 4 days, full rest "
                "the 5th day.",
                "It's week 6. The hotel gym has dumbbells, a bench, and a treadmill. "
                "Stage a kettlebell/dumbbell-only week with the runs kept. Go ahead.",
            ),
            ("Explain the run/walk progression you scheduled.", None),
            ("Show me the diff of the last plan change.", None),
            ("What's the single biggest mistake I could make in the next 6 months?", None),
        ],
    },
    "marcus": {
        "athlete": "data/sample_marcus.json",
        "goal": "16-week build to sub-3 marathon; strength is maintenance only; "
        "current 50 mpw base",
        "followups": [
            ("Why did you pick this weekly mileage progression?", None),
            (
                "Swap the Tuesday tempo for a marathon-pace progression run — I prefer those.",
                "Yes — replace the Tuesday tempo with a marathon-pace progression run for the "
                "build phase (weeks 5-8). Go ahead and stage it.",
            ),
            (
                "I'm getting a slight Achilles niggle — adapt this week to protect it.",
                "Call it week 5. Cut the hard running, keep easy aerobic + cross-train, protect "
                "the Achilles. Stage it.",
            ),
            ("Explain how you're using strength training during this block.", None),
            ("Show me the diff of the last plan change.", None),
            ("What's my projected race-week sharpening look like?", None),
        ],
    },
}

NEW_BLOCK_TMPL = (
    "Create my cycle. Goal: {goal}\n\n"
    "First pick the program model that fits me, draft the plan with the tool, then "
    "explain — concisely — the structure, the strength approach, the endurance/aerobic "
    "progression, and the nutrition profile. For each major decision cite both the Advisor "
    "Brief principle and the specific baseline fact of mine that drives it."
)


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in CONFIGS:
        print("usage: python run_ood.py sarah|marcus")
        return 2
    tag = sys.argv[1]
    cfg = CONFIGS[tag]
    athlete = Athlete.model_validate(
        json.loads(Path(str(cfg["athlete"])).read_text(encoding="utf-8"))
    )
    block = Block(block_id=f"{new_block_id()}_{tag}", model="claude-sonnet-4-6", athlete=athlete)
    coach = BlockCoach.create(block, max_cost_usd=2.0)
    print(f"Block id: {block.block_id} (model {block.model})")

    transcript: list[str] = []

    def record(role: str, text: str) -> None:
        transcript.append(f"### {role}\n\n{text}\n")
        print(f"\n{'=' * 70}\n{role}\n{'=' * 70}\n{text}")

    def over_budget() -> bool:
        if coach.tracker.total_usd > COST_STOP_USD:
            record("STOP", f"Cost ${coach.tracker.total_usd:.2f} exceeded ${COST_STOP_USD}.")
            return True
        return False

    followups: list[Followup] = cfg["followups"]  # type: ignore[assignment]
    steps: list[tuple[str, str, str | None]] = [
        ("[1] Block creation", NEW_BLOCK_TMPL.format(goal=cfg["goal"]), None)
    ] + [(f"[{i + 2}] Follow-up", msg, clar) for i, (msg, clar) in enumerate(followups)]

    for label, msg, clarification in steps:
        record(f"USER {label}", msg)
        record(f"COACH {label}", coach.send(msg))
        if over_budget():
            break
        if clarification is not None and block.pending_plan is None:
            record(f"USER {label} [clarify]", clarification)
            record(f"COACH {label} [clarify]", coach.send(clarification))
            if over_budget():
                break
        if block.pending_plan is not None:
            record("USER [approval]", APPROVAL)
            record("COACH [approval]", coach.send(APPROVAL))
            if over_budget():
                break

    summary = coach.tracker.format_summary()
    print(summary)
    print(f"\nLargest single API call: {coach.tracker.max_latency_s:.1f}s (budget < 30s)")
    print(f"Session total: ${coach.tracker.total_usd:.4f} (budget < $1.50)")

    out = RUNS_DIR / block.block_id / "transcript.md"
    out.write_text(
        f"# OOD validation transcript — {tag}\n\n"
        f"Model: {block.model}  •  Block: {block.block_id}\n\n"
        + "\n".join(transcript)
        + "\n\n## Cost summary\n\n```\n"
        + summary
        + f"\n\nLargest single API call: {coach.tracker.max_latency_s:.1f}s"
        + f"\nSession total: ${coach.tracker.total_usd:.4f}\n```\n",
        encoding="utf-8",
    )
    print(f"\nTranscript: {out}")
    print(f"Workbook:   {block.xlsx_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
