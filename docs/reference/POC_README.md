# Obelisk Block Coach — POC

A Python validation experiment for **Obelisk's Block Coach**: a single Claude
agent, grounded in the *Claude S&C Advisor Brief* and equipped with deterministic
tools, that generates a 12-week periodized training cycle from an athlete's
baseline, refines it conversationally, and does so at a tractable cost per user.

> **Hypothesis under test:** Can Claude produce coach-quality 12-week cycle plans
> from baseline data, refine them in conversation with a diff-before-commit gate,
> cite its reasoning, and stay under **\$1.50 / session** and **30s** for the
> largest call?

---

## Status

| Area | State |
|------|-------|
| Deterministic tools + tests | ✅ Built, **100% line coverage** on `src/tools.py` |
| Plan builder + xlsx renderer | ✅ Built; output **271/276 prescribed weights byte-identical** to the reference `Cycle_1_12wk_Plan.xlsx` |
| Agent loop, cost tracking, persistence, CLI | ✅ Built; tool loop & diff-gate verified offline + live |
| **Live validation run** (Josh) | ✅ **Executed.** Session cost **\$0.38**, largest call **25.7s**. Transcript: [`docs/validation_run/transcript.md`](docs/validation_run/transcript.md). |
| **Out-of-distribution validation** (Sarah, Marcus) | ✅ **Executed.** Both scored **5/5** differentiation at \$0.37 / \$0.29. See [`docs/ood_validation/comparison.md`](docs/ood_validation/comparison.md). |
| **Safety & refusal battery** (14 scenarios, 7 categories) | ✅ **14/14 PASS** after building a safety layer (prompt protocols + tool rails). See [`docs/safety_validation/refusal_battery.md`](docs/safety_validation/refusal_battery.md). |
| Quality gates | ✅ `mypy --strict` clean, `ruff` clean, `black` formatted, **81 tests, ~92% coverage** |

All six success criteria are met (see [Validation run](#validation-run)); the
architecture generalizes across athlete types (see [OOD Validation](#out-of-distribution-validation)).

---

## Quickstart

Requires Python 3.11+.

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate     macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env          # then put your real key in .env
#   ANTHROPIC_API_KEY=sk-ant-...
```

`ANTHROPIC_API_KEY` is required for any command that talks to Claude; the app
fails loudly if it's missing. The default model is `claude-sonnet-4-6`
(override with `OBELISK_MODEL`).

### Verify the build with no API key

```bash
pytest --cov=src --cov-report=term-missing      # 74 tests, 95% coverage
python -m src.cli demo-offline                  # build + render a cycle, no LLM
```

`demo-offline` runs the full deterministic pipeline (plan builder → xlsx) and
writes `runs/<id>/cycle_plan.xlsx`, proving the structural backbone without
spending a token.

---

## Running it

```bash
# 1. Generate the initial 12-week cycle for the sample athlete (Josh)
python -m src.cli new-block \
  --athlete data/sample_athlete.json \
  --goal "12-week aerobic base + submaximal strength; bench priority (biggest gap); finger strength priority"

# 2. Drop into a REPL tied to that Block (id is printed by step 1)
python -m src.cli chat --block-id <id>

# Other commands
python -m src.cli list                          # list saved Blocks
python -m src.cli demo-offline                   # deterministic build, no API
```

After installing the console script (`pip install -e .`) you can also use
`obelisk-poc new-block …` directly.

In `chat`, type `cost` for the running cost summary, `exit`/`quit` to leave.
Cost is printed after **every** agent response; it is never silently exceeded.

**Cost safety rail:** both `new-block` and `chat` take `--max-cost <USD>`
(default **1.50**). The loop checks the running total before each paid call and
stops the moment the ceiling is reached — so a runaway tool loop can't quietly
spend past it. Pass `--max-cost 0` to disable.

---

## Validation run

Executed end-to-end against `claude-sonnet-4-6` with the Josh baseline. Full
transcript (all 6 messages + the two staged diffs): **[`docs/validation_run/transcript.md`](docs/validation_run/transcript.md)**;
the resulting workbook: [`docs/validation_run/cycle_plan.xlsx`](docs/validation_run/cycle_plan.xlsx).

Reproduce it interactively:

```bash
python -m src.cli new-block --athlete data/sample_athlete.json \
  --goal "12-week aerobic base + submaximal strength; bench priority (biggest gap); finger strength priority"
python -m src.cli chat --block-id <id>
# then: "Why did you pick these training maxes?" / "Swap the Friday deadlifts for
# trap bar deadlifts for the first 4 weeks." / "I'm traveling Mon-Fri next week,
# only a kettlebell — adapt week 2." / "Explain the 30/30 progression." /
# "Show me the diff of the last plan change."
```

(Or run the whole thing non-interactively with `python run_validation.py`, which
auto-approves the staged diffs and saves the transcript.)

### Results vs. success criteria

| # | Criterion | Result |
|---|-----------|--------|
| 1 | 12-week plan, 3 waves × 4 weeks, TMs/split/aerobic/hangboard/nutrition | ✅ Generated; structure + TMs match the reference (below) |
| 2 | Conversational refinement (swap, travel adapt, explain, why) | ✅ All four handled |
| 3 | Plan changes return a structured diff for approval before commit | ✅ `swap_lift` + `override_week` each staged a diff; committed only after approval |
| 4 | Every recommendation cites Brief principle + athlete input | ✅ Quoted §3.1/§3.2/§3.3/§3.5/§3.6/§4.2 alongside Josh's BW, MAF pace, Lattice load, 2k row |
| 5 | Full session cost < \$1.50 | ✅ **\$0.3831** |
| 6 | Largest single call (Block creation) < 30s | ✅ **25.7s** |

### What the coach actually did

- **Block creation** → drafted the cycle and explained TMs, the Mon/Wed/Fri +
  Tue/Thu/Sat split, the 30/30 aerobic build, the Hörst 7-53 hangboard plan, and
  Renaissance macros — each with a Brief citation and Josh's driving number.
- **Swap** (Friday deadlift → trap bar, first 4 weeks) → staged `waves[0]` diff,
  carried the 285 TM, **committed only after approval**; weeks 5–12 untouched.
- **Travel week** → asked which week (reasonable — the POC has no calendar), then
  staged a kettlebell-only Week 2 with hangboard deliberately dropped (tendon
  recovery, §3.5), committed after approval.
- **Explain 30/30 / show diff** → answered from the live plan; no invented numbers.

### Cost (measured)

21 API calls across the 8 turns (some turns ran multiple tool round-trips).

| Phase | Input tok* | Output tok | USD |
|-------|-----------:|-----------:|----:|
| Block creation (4 calls) | 26,556 | 2,639 | \$0.0700 |
| 5 follow-ups + 2 approvals (17 calls) | 272,384 | 4,149 | \$0.3131 |
| **Session total (21 calls)** | **298,940** | **6,788** | **\$0.3831** |

*Input includes cache reads/writes; the cached system prompt keeps later turns
cheap. Largest single call **25.7s** (the Block-creation explanation). See the
transcript for the full per-call table.

---

## Out-of-Distribution Validation

Josh's run validated the architecture for *one* athlete. The OOD experiment tests
whether it **generalizes** — whether the agent internalized the Advisor Brief's
principles or just memorized Josh's pattern. Two deliberately different athletes
([`data/sample_sarah.json`](data/sample_sarah.json), a 6-month novice with **no
tested 1RMs** prepping a Tough Mudder; [`data/sample_marcus.json`](data/sample_marcus.json),
a sub-3 marathoner) ran the same 6-message script. Full analysis, scores, and
citation breakdown: **[`docs/ood_validation/comparison.md`](docs/ood_validation/comparison.md)**.

**Result — the architecture generalizes.** The agent routed each athlete to a
different periodization model and cited the **same** Brief sections to reach
**different** conclusions:

| | Josh | Sarah | Marcus |
|--|------|-------|--------|
| Program model | `hybrid_531` | `linear_novice` | `marathon_block` |
| Strength | 5/3/1 BBB wave | linear +5 lb/session | Easy Strength maintenance |
| 1RMs | tested → 85% TM | **none — not fabricated** | existing, held as a ceiling |
| Long day | pack hike | ruck progression | long run + MP segments |
| Hangboard | yes | no | no |
| Nutrition | 175 g P, maint. | 132 g P, deficit | 109 g P, carb-load 5 g/lb |
| Cost / largest call | $0.38 / 25.7 s | $0.37 / 26.2 s | $0.29 / 25.4 s |
| **Differentiation** | (baseline) | **5/5** | **5/5** |

Sarah correctly got **no** fabricated 1RMs (starting loads anchored to her real
rep-maxes; OHP defaulted to empty bar), **no** 5/3/1, **no** hangboard. Marcus got
strength explicitly **demoted to maintenance**, not a concurrent strength block.

**This required fixing the Josh-shaped planner** (the predicted bug) plus five
others the OOD athletes surfaced — missing-data crashes, a Josh-calibrated macro
tool, no granular edit tool for note-based plans, a multi-week over-claim, staged
edits clobbering each other, and context bloat from cycle-wide edits. All fixed,
documented in the comparison doc, and re-run green. Reproduce with
`python run_ood.py sarah` / `python run_ood.py marcus`.

---

## Safety Validation

The last gate before beta: does the agent **detect, route, defer, adapt, or
refuse** on harmful-coaching scenarios? A 14-test battery across 7 categories
(disordered eating, pregnancy/lactation, injury, medication, minors, mental
health, adversarial) — full results and verbatim transcripts in
**[`docs/safety_validation/refusal_battery.md`](docs/safety_validation/refusal_battery.md)**.

**Result: 14/14 PASS + 3/3 persistence follow-ups PASS** — but only after building
a safety layer the POC didn't have. Calibration found the unmodified agent was
safety-*aware* but not protocol-compliant, and **HARD-FAILED the subtle case**
(built a full cut for a BMI-21 athlete). The fixes:

- **System-prompt safety protocols** — 7 categories, each with the correct
  response (hard refuse / defer / adapt+clearance / reframe+resources), specific
  hotlines (NEDA, 988), and a BMI check on every cut request.
- **Architectural rails (code, not prompt):** `compute_macros` clamps to a hard
  calorie floor (`max(BW×10, 1200)` — can't emit a sub-floor target even if asked);
  `draft_cycle_plan` refuses for under-18 athletes. Both unit-tested.

Representative passes: an active-crisis cue → "**988**, the plan will be here";
persistent finger pain → the exact 7-14 day rest protocol; a 1,200-cal demand →
"won't build it, your floor is 1,750"; ACL history *remembered 3 messages later*.
Run it with `python run_safety.py`.

---

## Architecture

A single agent over a **bare, framework-free tool-use loop** (no LangChain) so
the cost model is fully visible. The loop lives in `src/agent.py`:

```
user msg ─▶ Claude ──(stop_reason=tool_use)──▶ dispatch tool ─▶ tool_result ─┐
              ▲                                                               │
              └───────────────────────────── loop ◀───────────────────────────┘
            (stop_reason=end_turn) ─▶ final text answer
```

| Module | Responsibility |
|--------|----------------|
| `src/tools.py` | The 8 deterministic tools (Epley 1RM, training max, macros, MAF, periodization templates, warm-up ramp, xlsx render, Advisor-Brief lookup). Pure, 100%-tested. |
| `src/planbuilder.py` | Three deterministic program builders — `build_default_plan` (hybrid 5/3/1), `build_linear_novice_plan` (Practical-Programming novice tier), `build_endurance_block_plan` (Pfitzinger-style marathon block). The agent selects which via `draft_cycle_plan(program_model=…)`. Every number sourced from `tools`. |
| `src/render.py` | Renders a `CyclePlan` to the Excel workbook (adapted from `build_cycle1.py`, now plan-driven). |
| `src/models.py` | Pydantic models: `Athlete`, `CyclePlan` (template-level, not per-set), `PlanDiff`. |
| `src/diff.py` | Structured plan diff powering the approval gate. |
| `src/brief.py` | Loads/indexes the Advisor Brief; serves sections 1–3 as the system prompt and keyword search for citations. |
| `src/system_prompt.py` | Builds the Block Coach system prompt (Brief §1–3 + operating rules + **safety protocols** + athlete baseline). |
| `src/coach_tools.py` | Anthropic function-calling specs + dispatch; the plan-lifecycle tools (`draft_cycle_plan`, the targeted edits `swap_lift` / `override_week`, `commit_plan_update`, `show_plan_diff`). |
| `src/cost_tracker.py` | Per-call and running USD/token accounting, cache-aware. |
| `src/persistence.py` | The "Block": athlete + plan + pending change + conversation, saved as JSON under `runs/<id>/`. |
| `src/agent.py`, `src/cli.py` | The loop and the CLI test harness. |

### Two design decisions worth flagging

1. **Numbers come from tools, never the LLM.** The model chooses goals,
   priorities, template, and *narrative*; it calls `draft_cycle_plan` to get a
   structured skeleton, and the renderer computes every prescribed weight from
   `training_max × loading_%` (the same `compute_warmup_ramp` math the tool
   exposes). If the model ever needs a number, it must call a tool.

2. **The plan is stored at the template level, not fully expanded.** A wave holds
   its training maxes; the loading scheme holds per-week percentages; the
   renderer expands them. This keeps the agent's emitted JSON small (cheap) and
   makes conversational adaptation a small, well-typed edit. Adaptations are
   modelled as `days_override` (per wave) or `week_overrides` (one-off weeks like
   a travel week) — exactly the two validation scenarios.

3. **No silent plan changes, via small-payload edit tools.** Edits use
   `swap_lift` / `override_week` — each takes a *tiny* argument (a day + new lift,
   or one week of free-text sessions), applies it server-side, and returns a diff
   *without committing*. The athlete approves, then `commit_plan_update` re-renders.
   (An earlier design had the model emit the entire updated plan as a tool
   argument; the live run proved that blows past `max_tokens` and corrupts the
   loop — see [What's brittle](#whats-brittle--what-the-live-run-found).)

---

## Fidelity vs. `Cycle_1_12wk_Plan.xlsx`

Generated from the same Josh baseline, the deterministic plan reproduces the
reference's structure: **Overview + 3 wave tabs**, 3 waves × 4 weeks, the
Mon/Wed/Fri strength + Tue/Thu/Sat aerobic split, hangboard schedule, and
nutrition profile.

**Training maxes (TM = 85% of est 1RM), generated == reference:**

| Lift | Est 1RM | TM W1 | TM W2 | TM W3 |
|------|--------:|------:|------:|------:|
| Back Squat | 259 | 220 | 230 | 240 |
| Bench Press | 182 | 155 | 160 | 165 |
| Deadlift | 336 | 285 | 295 | 305 |
| Strict Press | 123 | 105 | 110 | 115 |
| Front Squat | 248 | 210 | 220 | 230 |
| Power Clean | 182 | 155 | 160 | 165 |

**Prescribed weights:** **271 / 276 (98.2%) byte-identical** to the reference
workbook across all three waves. The 5 differences are all rounding tie-breaks
(e.g. 230 × 75% = 172.5 → **175** here vs **170** in the reference): this POC
rounds halves **up** (the gym-plate convention), while the hand-made
`build_cycle1.py` used Python's banker's rounding. All five differ by a single
5-lb increment, four of them on accessory/deload sets.

---

## Cost model & per-Block projection

Pricing (`claude-sonnet-4-6`, per MTok): **\$3 input, \$15 output, cache read
\$0.30, cache write \$3.75** (`src/cost_tracker.py`). The ~5k-token system prompt
(Brief §1–3 + rules + baseline) is marked for **prompt caching**, so it is paid
once and read cheaply on every later turn.

Measured session (Block creation + 5 follow-ups + 2 approvals): **\$0.3831**.
A realistic full onboarding session is one Block creation plus ~10 follow-ups,
which projects to **~\$0.45–0.70/Block** — roughly **half the \$1.50 budget**.
The cost-sensitive operations are the long markdown explanations (output tokens),
not the edits — the small-payload `swap_lift`/`override_week` tools keep edits
cheap (~\$0.02–0.04 each including the approval round-trip).

---

## Quality

```bash
pytest --cov=src --cov-report=term-missing   # 74 passed, 95% total, tools.py 100%
mypy src                                     # strict: clean
ruff check src tests                         # clean
black --check src tests                      # formatted
```

Coverage policy: `src/tools.py` is the correctness-critical surface and is held
at 100% (spec requires >90%); the only meaningfully uncovered code is the
interactive `chat` REPL loop.

---

## Writeup (≈200 words)

**Did it work?** Yes — the hypothesis holds. The generated cycle is 98.2%
byte-identical to a coaching artifact a human built by hand for this athlete; the
live session refined it conversationally (lift swap scoped to weeks 1–4, a
kettlebell travel week), gated both changes behind an approval diff, cited the
Advisor Brief plus Josh's own numbers for every decision, and cost **\$0.38** with
the largest call at **25.7s** — comfortably inside both budgets.

**What surprised me:** how much the live run taught that offline tests couldn't.
Two real bugs only showed up against the model: (1) the first edit tool forced the
model to re-emit the *entire* plan as a tool argument, which blew past
`max_tokens`, truncated mid-`tool_use`, and corrupted the message history;
(2) `draft_cycle_plan` returned only TMs, so the model *confabulated* the weekly
split (put deadlift on the wrong day) when explaining it. Both are now fixed —
small-payload edit tools, and a draft response that returns the ground-truth
schedule.

**Per-Block cost:** ~\$0.45–0.70 for a full onboarding session; long explanations
(output tokens) dominate, not edits.

**For v2:** stream responses to cut latency; add an eval harness scoring cycles
against Brief principles; persist re-test weeks and multi-Block state; semantic
(not keyword) Brief retrieval at library scale.

---

## What's brittle / what the live run found

- **The model narrates from memory unless you ground it.** It invented the weekly
  split until `draft_cycle_plan` started returning the real day→lift map. Lesson:
  tool *returns*, not just tool *inputs*, must carry ground truth.
- **Heavyweight tool arguments break the loop.** Emitting a whole plan per edit
  hit `max_tokens`; the fix was targeted edits + a loop that always pairs every
  `tool_use` with a `tool_result` regardless of stop reason.
- **Latency tracks output length.** The Block-creation explanation was the only
  call near budget (41s → 25.7s after a brevity instruction). Streaming is the
  real fix.
- **`lookup_advisor_principle` is keyword search**, not semantic — fine for one
  document, wants embeddings at library scale.
- **No re-test (Wk 13) tab** — the reference has one; out of scope here.

## Scope

CLI only; JSON-file persistence (no DB); single Block Coach (no multi-agent
layer); strength + conditioning cycle with macro targets; the Advisor Brief is
the sole grounding source — all per the POC brief's "do NOT build" list.
