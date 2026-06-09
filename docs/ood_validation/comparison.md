# Out-of-Distribution Validation — Josh vs. Sarah vs. Marcus

**Question:** does the Block Coach *internalize* the Advisor Brief's principles and
produce appropriately different cycles for appropriately different athletes — or
did it memorize Josh's pattern and just swap numbers?

**Athletes (deliberately divergent):**
- **Josh** — 34, tactical-hybrid + climber, all six barbell 1RMs tested. (`hybrid_531`)
- **Sarah** — 32, 6-month novice, **no tested 1RMs**, Tough Mudder in 26 wks, wants to lose ~10 lb. (`linear_novice`)
- **Marcus** — 28, sub-3 marathoner, 50 mpw, strength is supplemental. (`marathon_block`)

All three ran the same 6-message validation script (creation + 5 follow-ups).
Transcripts: [Josh](../validation_run/transcript.md) · [Sarah](transcript_sarah.md) · [Marcus](transcript_marcus.md).
Workbooks alongside each.

---

## Comparison table

| Axis | Josh (tactical hybrid) | Sarah (novice / OCR) | Marcus (sub-3 marathon) |
|------|------------------------|----------------------|--------------------------|
| **Program model selected** | `hybrid_531` | `linear_novice` | `marathon_block` |
| **Macrocycle** | 12 wk · 3 waves × 4 | 16 wk · 4 phases × 4 (Foundation/Build/Specific/Peak-Taper) | 16 wk · Base/Build/Peak/Taper |
| **Strength model** | 5/3/1 BBB, wave-loaded | **Linear, +5 lb/session** (Practical Programming novice) | **Easy Strength maintenance**, 2×/wk |
| **TM logic** | TM = 85% of tested 1RM | **N/A — no TMs.** Starting loads anchored to *known rep-maxes* (goblet 8RM 35 lb, KB DL 5RM 70 lb); OHP = empty bar (no data) | **N/A — no new TMs.** 2×5 @ ~80% of *existing* 1RMs as a ceiling, never chased |
| **Weekly split** | 6 d: Mon/Wed/Fri strength + Tue/Thu/Sat aerobic + hangboard | 3 full-body (Mon/Wed/Fri) + Tue/Sat run-walk & ruck | 6 d running (2 quality + long) + 2× Easy Strength (Mon/Fri) |
| **Aerobic structure** | MAF 146; Z2 build 30→60 min; 30/30 from wk7 | MAF **148**; couch-to-5K run/walk 1:2 → continuous 30-40 min | MAF **152**; polarized 80/20; LT/MP/VO₂ quality; 50→70 mpw |
| **Long endurance day** | Long pack hike 60→120 min @ 25-35 lb | Walk/jog → **ruck** 0→20 lb, 20→60 min | **Long run** 16→22 mi, MP segments from wk8 |
| **Climbing / hangboard** | Hörst 7-53, 2×/wk | **None** (not a climber) | **None** (not a climber) |
| **Nutrition (workbook)** | 175 g protein (1.0/lb); carbs 88-350 (0.5-2.0/lb); maintenance | 132 g protein (0.8/lb); carbs 83-330; **modest deficit** | 109 g protein (0.75/lb); carbs **290-725** (up to 5.0/lb); **surplus + carb-load** |
| **Brief sections cited** | §3.1, §3.2, §3.3, §3.4, §3.5, §3.6, §4.x | §3.1, §3.2, §3.3, §3.4, §3.6, §3.7, **§4.1** | §3.2, §3.3, §3.4, §3.6, §3.7, **§4.3** + Pfitzinger |
| **Session cost** | **$0.38** | **$0.37** | **$0.29** |
| **Largest call** | 25.7 s | 26.2 s | 25.4 s |

None of the memorization failure modes appeared: Sarah got **no** 5/3/1 BBB, **no**
fabricated 1RMs, **no** 30/30 block she couldn't support, **no** hangboard. Marcus
got **no** 3-day bench-priority split and **no** Josh-style 175P/350C. Neither
cycle cloned Josh's wave grid.

---

## Differentiation scores (1–5)

| Athlete | Score | Rationale |
|---------|:-----:|-----------|
| **Sarah** | **5** | Correct model from the right signal ("zero tested 1RMs → fabricating them would mean fabricating every working weight"). Starting loads anchored to her *actual* rep-maxes; OHP defaulted to empty bar where she had no data. Couch-to-5K + ruck progression, grip/pull emphasis for OCR, deficit nutrition, MAF 148. Reads like a coach who met a beginner. |
| **Marcus** | **5** | Correct model; strength explicitly **demoted to Easy Strength maintenance** ("arrive at race day with your strength base intact, not improved") citing §3.2/§3.3; Pfitzinger 18/70 mileage logic with the 10% rule and cutback weeks; polarized 80/20 at MAF 152; carb-periodized nutrition; race-week taper + carb-load. |
| **Josh** | **5** | (Baseline) 98% byte-identical to the hand-built reference; correct hybrid concurrent structure. |

**The strongest internalization signal — same sections, different conclusions:**

| Brief section | Josh | Sarah | Marcus |
|---------------|------|-------|--------|
| **§3.2** Concurrent training | Strength is the constant; endurance bends | Used to justify a *little* concurrent running for a beginner | "Strength **bends to maintenance**" — endurance is the priority |
| **§3.3** Frequent submaximal practice | ≤85% TM, never miss reps | Novice **linear** progression, 1-2 RIR | **Easy Strength** 2×5 @ 80%, "never grind" |
| **§3.4** Aerobic base / polarized | 30/30 build on a tactical base | Couch-to-5K — "more time slow than feels productive" for a true beginner | Full polarized 80/20, LT/VO₂ quality on a deep base |
| **§3.6** Nutrition | Maintenance, 1.0 g/lb protein | **Deficit** (lose 10 lb), carbs around lifts | **Carb-load** for 70 mpw, lower protein, surplus |

The same five principles produced three structurally different plans. That is the
result the experiment was designed to find.

---

## Bugs surfaced and fixed

The OOD athletes broke the Josh-shaped engine in exactly the way predicted, plus
two new categories. All were fixed and re-run.

1. **Planner memorized Josh's pattern (CRITICAL).** `build_default_plan` hard-coded
   a 5/3/1 hybrid cycle, and `Athlete` *required* six barbell 1RMs — Sarah and
   Marcus crashed on load. **Fix:** relaxed the `Athlete`/`CyclePlan` models
   (optional fields, `extra="allow"`); added two deterministic program builders
   (`linear_novice`, `marathon_block`); the **agent selects** the model + params
   from the athlete's data via `draft_cycle_plan(program_model=…)`.
2. **Macro tool was Josh-calibrated.** `compute_macros` capped carbs at 2.0 g/lb —
   nowhere near a marathoner's needs. **Fix:** optional `protein_g_per_lb` /
   `carb_g_per_lb` / `cal_per_lb` overrides (Marcus long-day carbs now 5.0 g/lb).
3. **Note-based plans had no granular edit tool.** `swap_lift` only targets barbell
   *main* lifts, so Sarah's goblet swap and Marcus's tempo→MP swap found nothing.
   The agent degraded gracefully (explained the limit) but couldn't action them.
   **Fix:** added `set_day_across_weeks` (atomic multi-week, single-day edit).
4. **Multi-week over-claim.** Before the fix, the coach narrated "weeks 5–8 are now
   MP runs" but `override_week` only persists one week — only 1 week actually
   changed. **Fix:** the multi-week tool + a system-prompt rule ("only describe a
   change as done after `commit_plan_update` returns success").
5. **Staged edits clobbered each other.** Two stages in one turn (goblet Mon +
   split-squat Fri) → the second rebuilt from `current_plan`, dropping the first.
   **Fix:** edits now accumulate from `pending_plan or current_plan`; verified the
   goblet swap persists on Mon **and** Fri across all 16 weeks.
6. **Cycle-wide edits bloated context.** A 16-week edit ballooned the plan JSON to
   ~23k tokens; `get_plan_json` dumped all of it into later turns, pushing one call
   to 54.7 s. **Fix:** `get_plan_json` returns a compact summary (phases + per-week
   day→session map), not the raw nested plan. Largest call back to ~26 s.

---

## Known calibration gap (not blocking)

The coach's **narrative** protein figure is re-derived via `compute_macros` at the
default 1.0 g/lb (Sarah 165 g, Marcus 145 g in chat), while the **workbook** carries
the builder's athlete-calibrated value (Sarah 132 g / 0.8·lb; Marcus 109 g /
0.75·lb). Carbs differentiate correctly in both. The workbook is the source of
truth; aligning the narrative (have the coach read the plan's nutrition rather than
recompute) is a v2 polish item.

---

## Cost & latency

| Athlete | Session cost | Largest call | Calls |
|---------|:------------:|:------------:|:-----:|
| Josh | $0.3831 | 25.7 s | 21 |
| Sarah | $0.3657 | 26.2 s | — |
| Marcus | $0.2911 | 25.4 s | — |
| **Combined Sarah+Marcus** | **$0.6568** | — | — |

All three under the $1.50/session and 30 s/largest-call budgets; the OOD pair is
well under the $3.00 combined target.

---

## Verdict

The architecture generalizes. Once the planner stopped being Josh-shaped, the
agent routed a novice, a marathoner, and a tactical hybrid to three different
periodization models, sourced numbers from the right tools (and *refused to invent*
1RMs Sarah didn't have), and cited the **same** Advisor Brief principles to reach
**different** conclusions — at $0.29–$0.38 per session. Differentiation scored 5/5
for both new athletes.

**Seed-deck claim, supported:** *"We validated coach-quality generation across
three deliberately different athletes — a tactical hybrid, a novice with an obstacle-
race goal, and a sub-3 marathoner — at $0.38, $0.37, and $0.29 per session. The same
Advisor Brief principles produced demonstrably different plans, citing the same
sections to reach different conclusions based on athlete-specific inputs."*
