"""Drive the full validation session non-interactively and save a transcript.

Mirrors the README runbook: Block creation + 5 follow-ups. When the coach stages
a plan change and asks for approval (block.pending_plan set), we auto-approve so
the diff -> approve -> commit gate is exercised end to end. Hard-stops at $5
(the POC's cost stop-condition).
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

from src.agent import BlockCoach
from src.models import Athlete
from src.persistence import Block, new_block_id

# Make stdout UTF-8 so domain glyphs (× • → ≤) print on the Windows console.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

COST_STOP_USD = 5.0

NEW_BLOCK_GOAL = (
    "12-week aerobic base + submaximal strength; bench priority (biggest gap); "
    "finger strength priority"
)
NEW_BLOCK_MSG = (
    f"Create my 12-week cycle. Goal: {NEW_BLOCK_GOAL}\n\n"
    "Draft the plan with the tool, then explain — concisely — the training maxes, "
    "the weekly split, the aerobic progression, the hangboard plan, and the nutrition "
    "profile. For each major decision cite both the Advisor Brief principle and the "
    "specific baseline number of mine that drives it."
)
# (message, optional clarification the "athlete" gives if the coach asks before staging)
FOLLOWUPS: list[tuple[str, str | None]] = [
    ("Why did you pick these training maxes?", None),
    (
        "Swap the Friday deadlifts for trap bar deadlifts for the first 4 weeks.",
        "Yes — the Friday deadlift (Strength C), wave 1 only. Carry over the same training max. "
        "Go ahead and stage it.",
    ),
    (
        "I'm traveling Mon-Fri next week with no gym, only a kettlebell. Adapt the week.",
        "It's week 2 of the cycle. Replace that whole week with sensible kettlebell-only "
        "sessions (keep the aerobic/rest days). Go ahead and stage it.",
    ),
    ("Explain the 30/30 interval progression you scheduled.", None),
    ("Show me the diff of the last plan change.", None),
]
APPROVAL = "Yes, that looks right — approve and commit it."

transcript: list[str] = []


def record(role: str, text: str) -> None:
    transcript.append(f"### {role}\n\n{text}\n")
    print(f"\n{'='*70}\n{role}\n{'='*70}\n{text}")


def main() -> int:
    athlete = Athlete.model_validate(
        json.loads(Path("data/sample_athlete.json").read_text(encoding="utf-8"))
    )
    block = Block(block_id=new_block_id(), model="claude-sonnet-4-6", athlete=athlete)
    coach = BlockCoach.create(block)
    print(f"Block id: {block.block_id} (model {block.model})")

    steps: list[tuple[str, str, str | None]] = [("[1] Block creation", NEW_BLOCK_MSG, None)] + [
        (f"[{i + 2}] Follow-up", msg, clar) for i, (msg, clar) in enumerate(FOLLOWUPS)
    ]

    def over_budget() -> bool:
        if coach.tracker.total_usd > COST_STOP_USD:
            record("STOP", f"Cost ${coach.tracker.total_usd:.2f} exceeded ${COST_STOP_USD}.")
            return True
        return False

    def approve_if_pending() -> None:
        if block.pending_plan is not None:
            record("USER [approval]", APPROVAL)
            record("COACH [approval]", coach.send(APPROVAL))

    for label, msg, clarification in steps:
        record(f"USER {label}", msg)
        record(f"COACH {label}", coach.send(msg))
        if over_budget():
            break
        # If the coach asked for clarification before staging, answer it once.
        if clarification is not None and block.pending_plan is None:
            record(f"USER {label} [clarify]", clarification)
            record(f"COACH {label} [clarify]", coach.send(clarification))
            if over_budget():
                break
        approve_if_pending()
        if over_budget():
            break

    summary = coach.tracker.format_summary()
    print(summary)
    print(f"\nLargest single API call: {coach.tracker.max_latency_s:.1f}s " f"(budget < 30s)")
    print(f"Session total: ${coach.tracker.total_usd:.4f} (budget < $1.50)")

    out = block.run_dir / "transcript.md"
    out.write_text(
        "# Validation run transcript\n\n"
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
