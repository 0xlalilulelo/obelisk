"""Interactive CLI test harness for the Block Coach POC.

Commands:
  new-block  --athlete data/sample_athlete.json --goal "..."   generate a cycle
  chat       --block-id <id>                                    REPL on a Block
  demo-offline --athlete data/sample_athlete.json              build+render, no API
  list                                                         list saved Blocks
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from obelisk_api.agent.block import Block, list_blocks, new_block_id
from obelisk_api.agent.loop import BlockCoach, MissingAPIKeyError, resolve_model
from obelisk_api.domain.models import Athlete
from obelisk_api.services.planbuilder import build_default_plan
from obelisk_api.services.render import render_plan

_NEW_BLOCK_PROMPT = (
    "Create my 12-week cycle. Goal: {goal}\n\n"
    "Draft the plan with the tool, then explain — concisely — the training maxes, "
    "the weekly split, the aerobic progression, the hangboard plan, and the nutrition "
    "profile. For each major decision cite both the Advisor Brief principle and the "
    "specific baseline number of mine that drives it."
)


def _load_athlete(path: str) -> Athlete:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return Athlete.model_validate(data)


def _fmt_cap(max_cost: float | None) -> str:
    return f"${max_cost:.2f}" if max_cost and max_cost > 0 else "none"


def _print_response(text: str) -> None:
    print("\n" + "─" * 64)
    print(text)
    print("─" * 64 + "\n")


def cmd_new_block(args: argparse.Namespace) -> int:
    athlete = _load_athlete(args.athlete)
    block = Block(block_id=new_block_id(), model=resolve_model(), athlete=athlete)
    coach = BlockCoach.create(block, max_cost_usd=args.max_cost)
    print(
        f"Block id: {block.block_id}  (model: {block.model}, cost ceiling: {_fmt_cap(args.max_cost)})"
    )
    reply = coach.send(_NEW_BLOCK_PROMPT.format(goal=args.goal))
    _print_response(reply)
    print(coach.tracker.format_summary())
    print(f"\nWorkbook: {block.xlsx_path}")
    print(f"Continue with: obelisk-poc chat --block-id {block.block_id}")
    return 0


def cmd_chat(args: argparse.Namespace) -> int:
    block = Block.load(args.block_id)
    coach = BlockCoach.create(block, max_cost_usd=args.max_cost)
    print(
        f"Chatting on Block {block.block_id} ('{block.name}'). Cost ceiling: "
        f"{_fmt_cap(args.max_cost)}. Type 'exit' to quit, 'cost' for the cost summary."
    )
    while True:
        try:
            user = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if user.lower() in {"exit", "quit"}:
            break
        if user.lower() == "cost":
            print(coach.tracker.format_summary())
            continue
        if not user:
            continue
        reply = coach.send(user)
        _print_response(reply)
    print(coach.tracker.format_summary())
    return 0


def cmd_demo_offline(args: argparse.Namespace) -> int:
    """Build and render the default plan deterministically — no API key needed."""
    athlete = _load_athlete(args.athlete)
    block_id = new_block_id()
    out = Path("runs") / block_id / "cycle_plan.xlsx"
    plan = build_default_plan(
        athlete,
        title="Cycle 1 — Aerobic Base + Submaximal Strength",
        goals=[
            "1. Bench Press — close the gap (biggest absolute strength deficit).",
            "2. Pull-ups — 10 strict → 15 strict.",
            "3. Finger strength — Lattice 108.5% → ≥125% BW.",
            "4. MAF run pace — develop running economy.",
            "5. Maintain squat, deadlift, front squat, power clean.",
        ],
        priority_lifts=["bench_press"],
    )
    render_plan(plan, str(out))
    print(f"Built deterministic plan (no LLM). Rendered: {out}")
    print("Training maxes wave1→wave3:")
    for row in plan.training_maxes:
        print(f"  {row.display_name:<14} {row.tm_wave1} → {row.tm_wave3}  (+{row.increment}/wave)")
    return 0


def cmd_list(_args: argparse.Namespace) -> int:
    ids = list_blocks()
    if not ids:
        print("No saved Blocks under runs/.")
        return 0
    for bid in ids:
        print(bid)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="obelisk-poc", description="Obelisk Block Coach POC")
    sub = parser.add_subparsers(dest="command", required=True)

    cost_help = (
        "Hard USD ceiling for the session; the loop stops before any call that "
        "would push past it. Default 1.50; pass 0 to disable."
    )

    p_new = sub.add_parser("new-block", help="Generate a new 12-week cycle")
    p_new.add_argument("--athlete", default="data/sample_athlete.json")
    p_new.add_argument("--goal", required=True)
    p_new.add_argument("--max-cost", type=float, default=1.50, help=cost_help)
    p_new.set_defaults(func=cmd_new_block)

    p_chat = sub.add_parser("chat", help="REPL conversation tied to a Block")
    p_chat.add_argument("--block-id", required=True)
    p_chat.add_argument("--max-cost", type=float, default=1.50, help=cost_help)
    p_chat.set_defaults(func=cmd_chat)

    p_demo = sub.add_parser("demo-offline", help="Build+render deterministically (no API key)")
    p_demo.add_argument("--athlete", default="data/sample_athlete.json")
    p_demo.set_defaults(func=cmd_demo_offline)

    p_list = sub.add_parser("list", help="List saved Blocks")
    p_list.set_defaults(func=cmd_list)

    return parser


def _ensure_utf8_streams() -> None:
    """Make stdout/stderr UTF-8 so domain glyphs (× • → ≤) print on Windows."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_streams()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = args.func(args)
        return int(result)
    except MissingAPIKeyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
