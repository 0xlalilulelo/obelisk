"""Build the Cycle 1 — Aerobic Base + Submaximal Strength (12 weeks) xlsx."""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

ACCENT = "1F4E79"
HEADER_FILL = "D9E2F3"
INPUT_FILL = "FFF2CC"
COMPUTED_FILL = "E2EFDA"
DELOAD_FILL = "FCE4D6"
DAY_FILL = "F2F2F2"
SUBTLE = "595959"

thin = Side(border_style="thin", color="BFBFBF")
border = Border(top=thin, bottom=thin, left=thin, right=thin)

title_font = Font(name="Calibri", size=18, bold=True, color=ACCENT)
h2_font = Font(name="Calibri", size=14, bold=True, color=ACCENT)
h3_font = Font(name="Calibri", size=12, bold=True, color=ACCENT)
day_font = Font(name="Calibri", size=12, bold=True, color="FFFFFF")
label_font = Font(name="Calibri", size=11, bold=True)
text_font = Font(name="Calibri", size=11)
note_font = Font(name="Calibri", size=10, italic=True, color=SUBTLE)
small_font = Font(name="Calibri", size=10)

input_fill = PatternFill("solid", fgColor=INPUT_FILL)
computed_fill = PatternFill("solid", fgColor=COMPUTED_FILL)
header_fill = PatternFill("solid", fgColor=ACCENT)
sub_header_fill = PatternFill("solid", fgColor=HEADER_FILL)
deload_fill = PatternFill("solid", fgColor=DELOAD_FILL)
day_fill = PatternFill("solid", fgColor=DAY_FILL)

# ---- Athlete baseline (from assessment) ----
BW = 175
EST_1RM = {
    "Back Squat": 259,
    "Deadlift": 336,
    "Bench Press": 182,
    "Strict Press": 123,
    "Front Squat": 248,
    "Power Clean": 182,
}
# TMs at 85% of est 1RM (conservative for concurrent training)
TM = {lift: round(rm * 0.85 / 5) * 5 for lift, rm in EST_1RM.items()}  # round to nearest 5
# Bench is the priority weak lift, so accelerate TM growth
TM_INCREMENT = {
    "Back Squat": 10, "Front Squat": 10, "Deadlift": 10,
    "Bench Press": 5, "Strict Press": 5, "Power Clean": 5
}

wb = Workbook()

# ---------- OVERVIEW TAB ----------
ws = wb.active
ws.title = "Overview"
for col, w in [(1, 4), (2, 22), (3, 14), (4, 14), (5, 14), (6, 14), (7, 14), (8, 40)]:
    ws.column_dimensions[get_column_letter(col)].width = w

ws['B2'] = "Cycle 1 — Aerobic Base + Submaximal Strength"
ws['B2'].font = title_font
ws.merge_cells('B2:H2')

ws['B3'] = "12 weeks  •  3 waves × 4 weeks  •  Built from baseline (BW 175, age 34, RHR 59)"
ws['B3'].font = note_font
ws.merge_cells('B3:H3')

# Goals
r = 5
ws.cell(row=r, column=2, value="Cycle goals (in priority order)").font = h2_font
ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=8)
r += 1
goals = [
    "1. Bench Press. Close the gap to 1.25x BW (~220 lb) — biggest absolute strength deficit.",
    "2. Pull-ups. 10 strict → 15 strict (Gym Jones Operator IV/V prereq).",
    "3. Finger strength. Lattice load 108.5% → ≥125% BW. Hangboard 2x/wk.",
    "4. Run-pace at MAF. 13:43/mi → ≤12:00/mi. RHR 59 baseline is healthy; just develop running economy.",
    "5. Maintain squat, deadlift, front squat, power clean — don't lose ground while bench catches up.",
]
for g in goals:
    ws.cell(row=r, column=2, value=g).font = text_font
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=8)
    ws.cell(row=r, column=2).alignment = Alignment(wrap_text=True, vertical='top')
    r += 1
r += 1

# Training Maxes
ws.cell(row=r, column=2, value="Training Maxes (TM = 85% of est 1RM)").font = h2_font
ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=8)
r += 1
headers = ["Lift", "Est. 1RM", "TM Wave 1", "TM Wave 2", "TM Wave 3", "Increment", "Notes"]
for i, h in enumerate(headers):
    c = ws.cell(row=r, column=2+i, value=h)
    c.font = label_font
    c.fill = sub_header_fill
    c.border = border
    c.alignment = Alignment(horizontal='center', wrap_text=True)
r += 1
tm_rows_start = r
for lift in ["Back Squat", "Bench Press", "Deadlift", "Strict Press", "Front Squat", "Power Clean"]:
    inc = TM_INCREMENT[lift]
    tm1 = TM[lift]
    tm2 = tm1 + inc
    tm3 = tm2 + inc
    notes = {
        "Back Squat": "High-bar full depth (matches your tested style)",
        "Bench Press": "Paused, some arch — priority lift this cycle",
        "Deadlift": "Conventional, 1 work set only — high stress",
        "Strict Press": "Standing, no leg drive",
        "Front Squat": "Used as squat #2 light/technique day",
        "Power Clean": "Used 1x/wk as speed work (not main lift)",
    }[lift]
    row = [lift, EST_1RM[lift], tm1, tm2, tm3, f"+{inc}/wave", notes]
    for i, v in enumerate(row):
        c = ws.cell(row=r, column=2+i, value=v)
        c.font = text_font
        c.border = border
        c.alignment = Alignment(wrap_text=True, vertical='top')
        if i == 0:
            c.font = label_font
    r += 1
r += 1

ws.cell(row=r, column=2, value="Weekly Schedule").font = h2_font
ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=8)
r += 1
schedule = [
    ("Mon", "Strength A — Squat main + Press accessory + pulling"),
    ("Tue", "MAF aerobic — build 30 → 60 min over the cycle"),
    ("Wed", "Strength B — Bench main + Squat light + rows"),
    ("Thu", "MAF aerobic (Wk 1-6) → 30/30 intervals (Wk 7-12) + Hangboard #1"),
    ("Fri", "Strength C — Deadlift main + Bench light + Power Clean speed"),
    ("Sat", "Long pack hike (60 → 120 min @ 25-35#) + Hangboard #2"),
    ("Sun", "Rest"),
]
ws.cell(row=r, column=2, value="Day").font = day_font
ws.cell(row=r, column=2).fill = header_fill
ws.cell(row=r, column=2).alignment = Alignment(horizontal='center')
ws.cell(row=r, column=2).border = border
ws.cell(row=r, column=3, value="Session").font = day_font
ws.cell(row=r, column=3).fill = header_fill
ws.cell(row=r, column=3).border = border
ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=8)
r += 1
for d, s in schedule:
    ws.cell(row=r, column=2, value=d).font = label_font
    ws.cell(row=r, column=2).alignment = Alignment(horizontal='center')
    ws.cell(row=r, column=2).border = border
    ws.cell(row=r, column=2).fill = day_fill
    ws.cell(row=r, column=3, value=s).font = text_font
    ws.cell(row=r, column=3).border = border
    ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=8)
    r += 1
r += 1

# Loading scheme
ws.cell(row=r, column=2, value="5/3/1-style loading scheme (per 4-week wave)").font = h2_font
ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=8)
r += 1
scheme = [
    ("Week 1 (5s)",   "65% × 5",  "75% × 5",  "85% × 5+",  "Top set is AMRAP — leave 1-2 RIR"),
    ("Week 2 (3s)",   "70% × 3",  "80% × 3",  "90% × 3+",  "Top set AMRAP — leave 1-2 RIR"),
    ("Week 3 (5/3/1)", "75% × 5",  "85% × 3",  "95% × 1+",  "Top set AMRAP, but stop at RPE 9"),
    ("Week 4 (deload)", "40% × 5", "50% × 5", "60% × 5",   "NO AMRAP — full rest"),
]
ws.cell(row=r, column=2, value="Week").font = label_font
ws.cell(row=r, column=2).fill = sub_header_fill
ws.cell(row=r, column=2).border = border
for i, h in enumerate(["Set 1", "Set 2", "Set 3 (top)", "Notes"]):
    ws.cell(row=r, column=3+i, value=h).font = label_font
    ws.cell(row=r, column=3+i).fill = sub_header_fill
    ws.cell(row=r, column=3+i).border = border
    ws.cell(row=r, column=3+i).alignment = Alignment(horizontal='center')
ws.merge_cells(start_row=r, start_column=6, end_row=r, end_column=8)
r += 1
for week, s1, s2, s3, note in scheme:
    ws.cell(row=r, column=2, value=week).font = label_font
    ws.cell(row=r, column=2).border = border
    if "deload" in week:
        ws.cell(row=r, column=2).fill = deload_fill
    for i, v in enumerate([s1, s2, s3]):
        c = ws.cell(row=r, column=3+i, value=v)
        c.font = text_font
        c.border = border
        c.alignment = Alignment(horizontal='center')
    ws.cell(row=r, column=6, value=note).font = small_font
    ws.cell(row=r, column=6).border = border
    ws.merge_cells(start_row=r, start_column=6, end_row=r, end_column=8)
    r += 1
r += 2

# Aerobic build
ws.cell(row=r, column=2, value="Aerobic build schedule (MAF cap = 146 bpm)").font = h2_font
ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=8)
r += 1
aerobic = [
    ("Wk 1-2", "30-40 min", "60 min", "60 min", "MAF Tue+Thu, Sat long"),
    ("Wk 3-4", "40-50 min", "75 min", "75 min", "Build slowly"),
    ("Wk 5-6", "50 min",   "90 min", "90 min", "Re-test MAF end of Wk 6"),
    ("Wk 7-8", "50 min", "Intervals: 30/30 × 2×10", "100 min", "Intro 30/30 — only after RHR drops"),
    ("Wk 9-10", "60 min", "30/30 × 2×15", "110 min", ""),
    ("Wk 11", "60 min", "30/30 × 1×20", "120 min", ""),
    ("Wk 12 (deload)", "30 min", "30 min", "60 min", "Final week — easy only"),
]
ws.cell(row=r, column=2, value="Weeks").font = label_font
ws.cell(row=r, column=2).fill = sub_header_fill
ws.cell(row=r, column=2).border = border
for i, h in enumerate(["Tue (MAF)", "Thu", "Sat (Long)", "Notes"]):
    ws.cell(row=r, column=3+i, value=h).font = label_font
    ws.cell(row=r, column=3+i).fill = sub_header_fill
    ws.cell(row=r, column=3+i).border = border
    ws.cell(row=r, column=3+i).alignment = Alignment(horizontal='center')
ws.merge_cells(start_row=r, start_column=6, end_row=r, end_column=8)
r += 1
for wks, tue, thu, sat, note in aerobic:
    ws.cell(row=r, column=2, value=wks).font = label_font
    ws.cell(row=r, column=2).border = border
    if "deload" in wks:
        ws.cell(row=r, column=2).fill = deload_fill
    for i, v in enumerate([tue, thu, sat]):
        c = ws.cell(row=r, column=3+i, value=v)
        c.font = text_font
        c.border = border
        c.alignment = Alignment(horizontal='center', wrap_text=True)
    ws.cell(row=r, column=6, value=note).font = small_font
    ws.cell(row=r, column=6).border = border
    ws.merge_cells(start_row=r, start_column=6, end_row=r, end_column=8)
    r += 1
r += 2

# Hangboard
ws.cell(row=r, column=2, value="Hangboard schedule (Hörst 7-53 protocol)").font = h2_font
ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=8)
r += 1
hb_notes = [
    "Protocol: 20mm edge, half-crimp, 7s hang / 53s rest, 6 hangs per set, 3 sets per session.",
    "Start load: BW + 5 lb (~50% of your max 7s load). Add 5 lb total whenever last set is clean.",
    "Target by Wk 12: BW + 40-50 lb (~125-130% BW load). Re-test in Wk 13.",
    "ALWAYS warm up fingers fully (10-15 min) before loaded hangs.",
    "If pain or sharpness in fingers/forearms: STOP. 7-14 days of antagonist work only.",
]
for n in hb_notes:
    ws.cell(row=r, column=2, value="• " + n).font = small_font
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=8)
    ws.cell(row=r, column=2).alignment = Alignment(wrap_text=True, vertical='top')
    r += 1
r += 1

# Nutrition
ws.cell(row=r, column=2, value="Nutrition profile for this cycle").font = h2_font
ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=8)
r += 1
nutr = [
    f"Calories: BW × 18-20 = {175*18:,}-{175*20:,} cal/day (maintenance with slight surplus on hard days)",
    f"Protein: 1.0 g/lb = {175} g/day, split across 5-6 meals (~30-35 g/meal)",
    "Carbs (Renaissance scheme): Rest day 0.5 g/lb (88 g) • Light day 1.0 (175 g) • Moderate 1.5 (263 g) • Hard 2.0 (350 g)",
    "Fat: fills remaining calories. Minimum 0.4 g/lb (70 g).",
    "Peri-workout: 15% pre / 40% during-and-immediately-post / 35% post-post / 10% rest. Near zero fat around training.",
    "Saturday long-pack overlay: add electrolytes hourly, omega-3 3-6 g/day continuous, sodium phosphate 1 g per 3-4 hr if effort >2 hrs.",
    "Track BW twice/wk (Mon and Thu morning fasted). Target: stable ±2 lb; aerobic goal supersedes mass gain this cycle.",
]
for n in nutr:
    ws.cell(row=r, column=2, value="• " + n).font = small_font
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=8)
    ws.cell(row=r, column=2).alignment = Alignment(wrap_text=True, vertical='top')
    r += 1
r += 1

# Legend
ws.cell(row=r, column=2, value="Legend").font = h2_font
r += 1
ws.cell(row=r, column=2, value="Yellow").fill = input_fill
ws.cell(row=r, column=2).font = label_font
ws.cell(row=r, column=3, value="Fill in your actual loads / times / RPE").font = text_font
ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=8)
r += 1
ws.cell(row=r, column=2, value="Green").fill = computed_fill
ws.cell(row=r, column=2).font = label_font
ws.cell(row=r, column=3, value="Auto-computed prescribed load (rounded to 5 lb)").font = text_font
ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=8)
r += 1
ws.cell(row=r, column=2, value="Orange").fill = deload_fill
ws.cell(row=r, column=2).font = label_font
ws.cell(row=r, column=3, value="Deload week — no AMRAP, easy aerobic, full recovery").font = text_font
ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=8)

# ---------- WAVE TAB BUILDER ----------
# Build one tab per wave with all 4 weeks laid out

# Helper: round to nearest 5
def r5(x):
    return f"=MROUND({x},5)"

def build_wave_tab(wave_num, tm_dict):
    name = f"Wave {wave_num} (Wk {(wave_num-1)*4+1}-{wave_num*4})"
    ws = wb.create_sheet(name)
    for col, w in [(1, 3), (2, 22), (3, 11), (4, 9), (5, 13), (6, 9), (7, 9), (8, 28)]:
        ws.column_dimensions[get_column_letter(col)].width = w

    ws['B2'] = f"Wave {wave_num} — Weeks {(wave_num-1)*4+1} through {wave_num*4}"
    ws['B2'].font = title_font
    ws.merge_cells('B2:H2')
    ws['B3'] = f"TMs this wave: Squat {tm_dict['Back Squat']} • Bench {tm_dict['Bench Press']} • DL {tm_dict['Deadlift']} • Press {tm_dict['Strict Press']} • FS {tm_dict['Front Squat']} • PC {tm_dict['Power Clean']}"
    ws['B3'].font = note_font
    ws.merge_cells('B3:H3')

    # 5/3/1 loading patterns per week
    week_patterns = {
        1: [(0.65, 5, False), (0.75, 5, False), (0.85, 5, True)],   # 5s, AMRAP top
        2: [(0.70, 3, False), (0.80, 3, False), (0.90, 3, True)],   # 3s, AMRAP top
        3: [(0.75, 5, False), (0.85, 3, False), (0.95, 1, True)],   # 5/3/1, AMRAP top
        4: [(0.40, 5, False), (0.50, 5, False), (0.60, 5, False)],  # deload
    }

    r = 5
    for week in range(1, 5):
        week_num_global = (wave_num - 1) * 4 + week
        is_deload = (week == 4)
        # Week header
        c = ws.cell(row=r, column=2, value=f"Week {week_num_global} — {['5s','3s','5/3/1','Deload'][week-1]}")
        c.font = day_font
        c.fill = deload_fill if is_deload else header_fill
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=8)
        c.alignment = Alignment(horizontal='center')
        c.border = border
        r += 1

        # Each day this week
        days_this_week = [
            ("Mon", "Strength A", [
                ("Back Squat — main", "Back Squat", week_patterns[week]),
                ("Strict Press — accessory", "Strict Press", [(0.60, 8, False), (0.70, 8, False), (0.70, 8, False)]),
                ("Pull-ups", None, [("Strict pull-ups, 4 sets x 5 reps with 5-lb belt (or BW if 5 lb impossible)", "", "")]),
                ("Optional finisher", None, [("3 rounds: 10 KB swings 53# + 10 push-ups, no rest. 5 min.", "", "")]),
            ]),
            ("Tue", "MAF Aerobic", [
                ("MAF run/bike/ruck", None, [(f"Wk {week_num_global}: see Overview Aerobic Build table for duration. ≤146 bpm.", "", "")]),
            ]),
            ("Wed", "Strength B", [
                ("Bench Press — main", "Bench Press", week_patterns[week]),
                ("Back Squat — light technique", "Back Squat", [(0.60, 5, False), (0.60, 5, False), (0.60, 5, False)]),
                ("DB row", None, [("4 sets x 10 each side, heavy. 60s rest.", "", "")]),
                ("Face pulls + band pull-aparts", None, [("3 sets x 15 each, supersetted.", "", "")]),
            ]),
            ("Thu", "Aerobic + Hangboard", [
                ("MAF or 30/30 (see Overview)", None, [(f"Wk {week_num_global}: per aerobic build table.", "", "")]),
                ("Hangboard — Hörst 7-53", None, [("3 sets x 6 hangs. 7s on / 53s off. Add weight when last set is clean.", "", "")]),
                ("Antagonist work", None, [("Band ext rot 3x12 + scap pull-ups 3x10 + narrow push-ups 3x12 + wrist ext 3x15.", "", "")]),
            ]),
            ("Fri", "Strength C", [
                ("Deadlift — main", "Deadlift", week_patterns[week]),
                ("Bench Press — light", "Bench Press", [(0.60, 5, False), (0.60, 5, False), (0.60, 5, False)]),
                ("Power Clean — speed", "Power Clean", [(0.65, 3, False), (0.65, 3, False), (0.65, 3, False), (0.65, 3, False), (0.65, 3, False)]),
                ("Loaded carry", None, [("3 sets x 50m farmer carry @ 2×70# DB, fast walk.", "", "")]),
            ]),
            ("Sat", "Long Pack + Hangboard", [
                ("Long pack hike", None, [(f"Wk {week_num_global}: see aerobic build table. 25-35# pack. ≤146 bpm.", "", "")]),
                ("Hangboard — Hörst 7-53", None, [("3 sets x 6 hangs. Same load as Thu (or +5 lb if Thu went clean).", "", "")]),
            ]),
            ("Sun", "Rest", [
                ("Active recovery optional", None, [("20 min walk + 15 min mobility on any tight spots.", "", "")]),
            ]),
        ]

        for day_name, session_name, blocks in days_this_week:
            # Day header
            c = ws.cell(row=r, column=2, value=f"{day_name} — {session_name}")
            c.font = label_font
            c.fill = day_fill
            c.border = border
            ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=8)
            r += 1

            for block_label, lift_key, sets in blocks:
                # If it's a strength lift block, write headers + computed sets
                if lift_key and isinstance(sets[0], tuple) and len(sets[0]) == 3 and isinstance(sets[0][0], float):
                    # Block label row
                    ws.cell(row=r, column=2, value=block_label).font = text_font
                    ws.cell(row=r, column=2).border = border
                    # Sub-header
                    for i, h in enumerate(["Set", "% TM", "Reps", "Prescribed lb", "Actual lb", "Actual reps", "RPE / notes"]):
                        c = ws.cell(row=r, column=2+i if i > 0 else 3, value=h if i > 0 else "")
                        if i > 0:
                            c.font = small_font
                            c.fill = sub_header_fill
                            c.border = border
                            c.alignment = Alignment(horizontal='center')
                    r += 1
                    for set_i, (pct, reps, is_amrap) in enumerate(sets, start=1):
                        ws.cell(row=r, column=2, value=f"  Set {set_i}").font = small_font
                        ws.cell(row=r, column=2).border = border
                        ws.cell(row=r, column=3, value=f"{int(pct*100)}%").font = small_font
                        ws.cell(row=r, column=3).border = border
                        ws.cell(row=r, column=3).alignment = Alignment(horizontal='center')
                        reps_txt = f"{reps}+" if is_amrap else str(reps)
                        ws.cell(row=r, column=4, value=reps_txt).font = small_font
                        ws.cell(row=r, column=4).border = border
                        ws.cell(row=r, column=4).alignment = Alignment(horizontal='center')
                        prescribed = round(tm_dict[lift_key] * pct / 5) * 5
                        ws.cell(row=r, column=5, value=prescribed).font = Font(name="Calibri", size=11, bold=True)
                        ws.cell(row=r, column=5).fill = computed_fill
                        ws.cell(row=r, column=5).border = border
                        ws.cell(row=r, column=5).alignment = Alignment(horizontal='center')
                        ws.cell(row=r, column=6).fill = input_fill
                        ws.cell(row=r, column=6).border = border
                        ws.cell(row=r, column=7).fill = input_fill
                        ws.cell(row=r, column=7).border = border
                        ws.cell(row=r, column=8).fill = input_fill
                        ws.cell(row=r, column=8).border = border
                        r += 1
                else:
                    # Plain text block (notes only)
                    ws.cell(row=r, column=2, value=block_label).font = text_font
                    ws.cell(row=r, column=2).border = border
                    note_txt = sets[0][0] if isinstance(sets[0], tuple) else str(sets[0])
                    ws.cell(row=r, column=3, value=note_txt).font = small_font
                    ws.cell(row=r, column=3).border = border
                    ws.cell(row=r, column=3).alignment = Alignment(wrap_text=True, vertical='top')
                    ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=7)
                    ws.cell(row=r, column=8).fill = input_fill
                    ws.cell(row=r, column=8).border = border
                    r += 1
            r += 1  # space between days
        r += 1  # space between weeks

# Build the three waves
build_wave_tab(1, {lift: TM[lift] for lift in TM})
build_wave_tab(2, {lift: TM[lift] + TM_INCREMENT[lift] for lift in TM})
build_wave_tab(3, {lift: TM[lift] + 2*TM_INCREMENT[lift] for lift in TM})

# ---------- RE-TEST WEEK TAB ----------
ws = wb.create_sheet("Wk 13 Re-test")
for col, w in [(1, 3), (2, 30), (3, 18), (4, 18), (5, 40)]:
    ws.column_dimensions[get_column_letter(col)].width = w

ws['B2'] = "Week 13 — Re-test"
ws['B2'].font = title_font
ws.merge_cells('B2:E2')
ws['B3'] = "Use the same protocols as the original assessment week. Compare to baseline."
ws['B3'].font = note_font
ws.merge_cells('B3:E3')

r = 5
ws.cell(row=r, column=2, value="Strength re-tests (3-5RM)").font = h2_font
ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=5)
r += 1
ws.cell(row=r, column=2, value="Lift").font = label_font
ws.cell(row=r, column=2).fill = sub_header_fill
ws.cell(row=r, column=2).border = border
ws.cell(row=r, column=3, value="Baseline est 1RM").font = label_font
ws.cell(row=r, column=3).fill = sub_header_fill
ws.cell(row=r, column=3).border = border
ws.cell(row=r, column=4, value="New est 1RM").font = label_font
ws.cell(row=r, column=4).fill = sub_header_fill
ws.cell(row=r, column=4).border = border
ws.cell(row=r, column=5, value="Delta").font = label_font
ws.cell(row=r, column=5).fill = sub_header_fill
ws.cell(row=r, column=5).border = border
r += 1
for lift in ["Back Squat", "Deadlift", "Bench Press", "Strict Press", "Front Squat", "Power Clean"]:
    ws.cell(row=r, column=2, value=lift).font = text_font
    ws.cell(row=r, column=2).border = border
    ws.cell(row=r, column=3, value=EST_1RM[lift]).font = text_font
    ws.cell(row=r, column=3).border = border
    ws.cell(row=r, column=3).alignment = Alignment(horizontal='center')
    ws.cell(row=r, column=4).fill = input_fill
    ws.cell(row=r, column=4).border = border
    ws.cell(row=r, column=5, value=f"=IF(ISNUMBER(D{r}),D{r}-C{r},\"\")").fill = computed_fill
    ws.cell(row=r, column=5).font = Font(name="Calibri", size=11, bold=True)
    ws.cell(row=r, column=5).border = border
    ws.cell(row=r, column=5).alignment = Alignment(horizontal='center')
    r += 1

r += 2
ws.cell(row=r, column=2, value="Other re-tests").font = h2_font
ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=5)
r += 1
other_tests = [
    ("Max strict pull-ups", "10", "(target: 15)"),
    ("Lattice 20mm 2-arm load (%BW)", "108.5%", "(target: ≥125%)"),
    ("BW hang time (sec)", "12", ""),
    ("MAF distance (30 min @ 146 bpm)", "2.26 mi", "(target: ≥2.50 mi)"),
    ("MAF avg pace", "13:43/mi", "(target: ≤12:00)"),
    ("Resting HR (7-day avg)", "80 bpm", "(target: ≤70)"),
    ("2K row time", "8:04", "(target: <7:45)"),
    ("Saturday long pack distance", "—", "(noting endurance growth)"),
    ("Bodyweight", "175 lb", "(track for trend)"),
]
ws.cell(row=r, column=2, value="Metric").font = label_font
ws.cell(row=r, column=2).fill = sub_header_fill
ws.cell(row=r, column=2).border = border
ws.cell(row=r, column=3, value="Baseline").font = label_font
ws.cell(row=r, column=3).fill = sub_header_fill
ws.cell(row=r, column=3).border = border
ws.cell(row=r, column=4, value="New result").font = label_font
ws.cell(row=r, column=4).fill = sub_header_fill
ws.cell(row=r, column=4).border = border
ws.cell(row=r, column=5, value="Notes").font = label_font
ws.cell(row=r, column=5).fill = sub_header_fill
ws.cell(row=r, column=5).border = border
r += 1
for metric, baseline, note in other_tests:
    ws.cell(row=r, column=2, value=metric).font = text_font
    ws.cell(row=r, column=2).border = border
    ws.cell(row=r, column=3, value=baseline).font = text_font
    ws.cell(row=r, column=3).border = border
    ws.cell(row=r, column=3).alignment = Alignment(horizontal='center')
    ws.cell(row=r, column=4).fill = input_fill
    ws.cell(row=r, column=4).border = border
    ws.cell(row=r, column=5, value=note).font = note_font
    ws.cell(row=r, column=5).border = border
    r += 1

# Save
output_path = '/sessions/tender-vibrant-hamilton/mnt/workout_programs/Cycle_1_12wk_Plan.xlsx'
wb.save(output_path)
print(f"Saved to {output_path}")
print(f"Sheets: {wb.sheetnames}")
