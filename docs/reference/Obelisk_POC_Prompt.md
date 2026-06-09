# Obelisk Block Coach POC — Kickoff Prompt

Copy this prompt and paste it as the kickoff message for a Claude Code (or Claude Agent SDK) session. Provide the referenced files alongside it.

---

## Role

You are a senior LLM application engineer. Build a Python POC for **Obelisk's Block Coach** — the core agent that generates and adapts periodized training cycles for hybrid athletes.

## Purpose

This is a **validation experiment**, not a production system. We have a PRD (Obelisk_PRD.docx) outlining a full multi-agent fitness coaching platform. This POC tests one specific hypothesis before we invest in the full build:

> Can Claude, grounded in the Obelisk Advisor Brief and equipped with deterministic tools, produce coach-quality 12-week cycle plans from athlete baseline data, refine them conversationally, and do so at acceptable cost per user?

The reference artifacts attached (`Cycle_1_12wk_Plan.xlsx`, `Claude_SC_Advisor_Brief.docx`, `Hybrid_SC_Reference.docx`) were generated manually in a coaching engagement with a real athlete (Josh). Your POC should reproduce work of equivalent quality automatically, then improve from there.

## Success criteria

1. Generates a 12-week periodized cycle plan from a structured baseline JSON. Output shape matches `Cycle_1_12wk_Plan.xlsx` — 3 waves × 4 weeks, training maxes per lift, weekly day split, loading scheme, aerobic progression, hangboard schedule, nutrition profile.
2. Supports conversational refinement: athlete asks "swap deadlifts for trap bar," "I'm traveling next week, adapt," "why did you pick these TMs?" — the agent answers and modifies the plan as needed.
3. Plan changes return as a structured diff (what was, what will be) for athlete approval before commit.
4. Every recommendation cites its rationale — both the Advisor Brief principle (e.g., "≤85% of 1RM most weeks") and the athlete-specific inputs driving it (RPE trend, HRV, goal).
5. Total Claude API cost for one full session (Block creation + 10 follow-up messages) is **under $1.50 USD**.
6. Wall-clock latency for the largest single call (Block creation) is **under 30 seconds**.

## Scope — build this

- Python 3.11+ project using the Anthropic SDK directly (no LangChain or other agent frameworks — we want to see the bare loop and understand the cost model).
- `src/system_prompt.py` — loads Sections 1–3 of `Claude_SC_Advisor_Brief.docx` as the Block Coach base system prompt. Extract content with `python-docx`.
- `src/tools.py` — deterministic tools exposed via Anthropic function calling:
  - `compute_1rm(weight_lb: float, reps: int) -> int` — Epley formula, rounded to 5 lb.
  - `compute_training_max(est_1rm: int, conservatism: float = 0.85) -> int` — TM with rounding.
  - `compute_macros(bw_lb: float, day_type: Literal["rest","light","moderate","hard"]) -> dict` — Renaissance scheme: 1.0 g/lb protein; carbs 0.5/1.0/1.5/2.0 g/lb by day type; fat fills calories.
  - `compute_maf(age: int) -> int` — 180 − age HR cap.
  - `get_periodization_template(name: Literal["531_bbb","rat6","juggernaut","tactical_barbell_operator"]) -> dict` — returns the weekly loading scheme as structured JSON.
  - `compute_warmup_ramp(tm: int, week: int, set_num: int) -> int` — returns prescribed weight for a given week/set in a 5/3/1-style wave.
  - `render_cycle_plan_xlsx(plan: dict, output_path: str) -> str` — renders the cycle as an Excel workbook matching the structure of `Cycle_1_12wk_Plan.xlsx` (use the existing `build_cycle1.py` as a reference; adapt the structure to consume the plan JSON the agent produces).
  - `lookup_advisor_principle(topic: str) -> str` — keyword search over the Advisor Brief, returns the relevant section for grounding.
- `src/agent.py` — the Block Coach agent loop. Single Claude agent (default `claude-sonnet-4-5`, configurable to `claude-opus-4-6`). Implements the tool-use loop until the model returns a final response.
- `src/cost_tracker.py` — logs input/output tokens per call and the running USD total. Print after every agent response.
- `src/cli.py` — interactive CLI for testing. Two modes:
  - `obelisk-poc new-block --athlete data/sample_athlete.json --goal "12-week aerobic base + submax strength; bench priority"` — generates the initial plan.
  - `obelisk-poc chat --block-id <id>` — drops into a REPL conversation tied to the Block.
- `data/sample_athlete.json` — Josh's baseline (see Validation Run below for the values).
- `tests/test_tools.py` — pytest unit tests for every deterministic tool (correctness, edge cases). `pytest --cov=src` should pass at >90% coverage on `tools.py`.
- `README.md` — setup, run instructions, sample session transcript, and a short writeup (see Deliverables).
- `pyproject.toml` — dependencies, ruff/black/isort/mypy config.

## Scope — do NOT build

- No web UI, mobile app, or desktop app. CLI only.
- No database. Persist sessions to JSON files in `runs/<timestamp>/`.
- No auth, payments, user accounts.
- No multi-agent specialty layer yet. Single Block Coach.
- No wearable integrations.
- No nutrition meal plan or mobility plan generation — just the strength + conditioning cycle (with macro targets, since they come from `compute_macros` for free).
- No RAG over user library. The Advisor Brief alone is the grounding source.
- No fancy UX. The CLI is a developer test harness, not a product.

## Constraints

- **Type annotations on every function signature.** No `Any`. Use `Literal` and `TypedDict` (or Pydantic) for tool schemas.
- Formatted with `black` and `ruff` (line length 100).
- `mypy --strict` passes.
- **Numeric outputs come from tools, not LLM free-generation.** If you find Claude inventing a weight number, the tool design is wrong — make it call a tool.
- Tool schemas use Anthropic's function-calling format, not parsed JSON from the model output.
- Cost tracking is always on. Never silently exceed budget.
- Secrets via `.env` + `python-dotenv`. `ANTHROPIC_API_KEY` required; fail loudly if absent.

## Inputs you'll be given

| File | Purpose |
|------|---------|
| `Obelisk_PRD.docx` | Background context. Do not implement the whole PRD; consult Sections 3 (personas), 5 (data model), 8 (agent architecture) for grounding. |
| `Claude_SC_Advisor_Brief.docx` | System prompt source. Extract Sections 1–3. |
| `Hybrid_SC_Reference.docx` | Reference for sourcing citations (Westside, 5/3/1, Renaissance, Uphill Athlete, etc.). |
| `Cycle_1_12wk_Plan.xlsx` | Target output shape. Mimic structure. |
| `Assessment_Week_Tracker.xlsx` | Sample baseline input data lives in the Baseline Summary tab. |
| `build_cycle1.py` | Reference Python that produces the target xlsx output. Adapt for the `render_cycle_plan_xlsx` tool. |

## Validation run (do this; include the transcript in README)

After building, execute this session end-to-end and report.

**Athlete baseline (Josh):**

```json
{
  "name": "Josh",
  "age": 34,
  "bodyweight_lb": 175,
  "height_in": 74,
  "resting_hr_bpm": 59,
  "estimated_1rm": {
    "back_squat": 259,
    "deadlift": 336,
    "bench_press": 182,
    "strict_press": 123,
    "front_squat": 248,
    "power_clean": 182
  },
  "max_strict_pullups": 10,
  "weighted_pullup_3rm_total_lb": 190,
  "lattice_20mm_load_pct_bw": 108.5,
  "max_bw_hang_sec": 12,
  "maf_test_distance_mi": 2.26,
  "maf_pace_min_per_mi": "13:43",
  "row_2k_time": "8:04",
  "ruck_60min_distance_mi_at_35lb": 4.38,
  "mobility_screen_all_pass": true,
  "primary_goals": ["tactical readiness", "climbing"],
  "equipment": "full_gym",
  "days_per_week": 6,
  "injuries": []
}
```

**Session script:**

1. `new-block --goal "12-week aerobic base + submaximal strength; bench priority (biggest gap); finger strength priority"`. Save the generated plan.
2. Chat: "Why did you pick these training maxes?"
3. Chat: "Swap the Friday deadlifts for trap bar deadlifts for the first 4 weeks."
4. Chat: "I'm traveling Mon-Fri next week with no gym, only a kettlebell. Adapt the week."
5. Chat: "Explain the 30/30 interval progression you scheduled."
6. Chat: "Show me the diff of the last plan change."

**Report:**

- Total tokens (input/output) and cost in USD across the full session.
- Wall-clock time for the largest call.
- Subjective quality assessment: was the generated cycle substantively comparable to `Cycle_1_12wk_Plan.xlsx`? Same 3-wave structure? TMs at ~85% of est 1RM? Sensible weekly split? Cited rationale?
- What surprised you, what's brittle, what's the next experiment.

## Deliverables

1. `obelisk-poc/` Python project (see file layout above).
2. README.md including:
   - Setup + run instructions.
   - Full transcript of the validation run above.
   - The generated cycle xlsx + a screenshot or markdown diff vs. `Cycle_1_12wk_Plan.xlsx`.
   - Cost table: total tokens + USD for the run, plus a per-message breakdown.
   - A 200-word writeup: did it work, what surprised you, what's the per-Block cost projection, what would you change for v2.
3. The generated cycle artifact: `runs/<timestamp>/cycle_plan.xlsx` for comparison.

## Quality bar

The generated cycle should be **substantively similar** to `Cycle_1_12wk_Plan.xlsx` in structure and reasoning — 3 waves × 4 weeks, TMs at 85% of estimated 1RM, weekly split with strength on Mon/Wed/Fri and aerobic on Tue/Thu/Sat, accessory selection aligned to gap priorities (bench priority means more bench volume), citations to the Advisor Brief for each major decision.

If the output is wildly off — wrong wave structure, hallucinated lifts, no citations, missing the priority lifts — the system prompt or tool design is wrong. Fix the prompt/tools, not the model.

## Stop conditions

- If a tool's correctness can't be proven via test, escalate and ask before shipping.
- If the cost per session exceeds $5 USD, stop and report why before continuing.
- If you find yourself implementing features outside this scope (multi-agent, web UI, database), stop and confirm.

---

**Start by reading the four input documents fully before writing any code. The Advisor Brief is load-bearing.**
