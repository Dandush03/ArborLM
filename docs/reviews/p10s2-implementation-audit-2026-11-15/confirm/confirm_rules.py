"""Independent confirmation checks (auditor code; does not import arborlm.*_analysis or the implementer's summary scripts).

Run: cd <worktree> && PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -I? no: plain .venv/bin/python <this> (cwd = worktree so studies/ imports)
"""

import random
import re
import sys

sys.path.insert(0, ".")
from studies.p10s2 import classes as C  # noqa: E402
from studies.p10s2 import core, output, report  # noqa: E402

out = []


def say(s):
    out.append(s)
    print(s)


# ---- 1. thresholds as configured ----
say(f"GAP_MIN={core.GAP_MIN} acq_gap_min={C.G['acq_gap_min']} composes_ratio_min={C.G['composes_ratio_min']} composes_negative={C.G['composes_negative']} gen_loss_margin={C.G['gen_loss_margin']}")
assert (core.GAP_MIN, C.G["acq_gap_min"], C.G["composes_ratio_min"], C.G["composes_negative"], C.G["gen_loss_margin"]) == (0.30, 0.50, 0.80, 0.50, 0.02)


# ---- 2. my own rule from the addendum text ----
def my_cell(x, xs, k0, s0, t):
    """per answer: returns (h or None, reason)"""
    if any(v is None or v != v or v in (float("inf"), float("-inf")) for v in (x, xs, k0, s0, t)):
        return None, "undef"
    if t - s0 < 0.30:
        return None, "teacher"
    if (xs - s0) / (t - s0) < 0.50:
        return None, "single"
    return (x - max(k0, s0)) / (xs - s0), ""


def my_class(orders):
    # orders: {o: [cell or None]}, cell = {a: h or None}
    for o, cells in orders.items():
        if not cells:
            return "NOT_EVALUATED"
        for c in cells:
            if c is None or any(v is None for v in c.values()):
                return "NOT_EVALUATED"
    if all(all(v >= 0.80 for v in c.values()) for cells in orders.values() for c in cells):
        return "COMPOSES"
    for cells in orders.values():
        for a in ("A", "B"):
            if all(c[a] < 0.50 for c in cells):
                return "DOES NOT COMPOSE"
    return "COMPOSITION INCONCLUSIVE"


rng = random.Random(229911)
dis = 0
counts = {}
trials = 30000
for _ in range(trials):
    orders_impl, orders_mine = {}, {}
    rejected = rng.random() < 0.03
    for o in rng.choice([["AB", "BA"], ["-"]]):
        ci, cm = [], []
        for _r in range(rng.choice([3, 4])):
            if rng.random() < 0.01:
                ci.append(None)
                cm.append(None)
                continue
            vals = {}
            for a in ("A", "B"):
                s0 = rng.uniform(0, 0.4)
                t = s0 + (rng.uniform(0.25, 0.35) if rng.random() < 0.02 else rng.uniform(0.3, 0.7))
                xs = s0 + (t - s0) * (rng.uniform(0.45, 0.55) if rng.random() < 0.02 else rng.uniform(0.5, 1.1))
                k0 = s0 + rng.uniform(-0.1, 0.1)
                x = max(k0, s0) + (xs - s0) * (rng.uniform(0.8, 1.2) if rng.random() < 0.9 else rng.choice([rng.uniform(0.75, 0.85), rng.uniform(0.45, 0.55), rng.uniform(-0.2, 0.5)]))
                if rng.random() < 0.0005:
                    x = float("nan")
                vals[a] = (x, xs, k0, s0, t)
            cell = C.comp_cell({a: vals[a][0] for a in vals}, {a: vals[a][1] for a in vals}, {a: vals[a][2] for a in vals}, {a: vals[a][3] for a in vals}, {a: vals[a][4] for a in vals})
            mine = {a: my_cell(*vals[a])[0] for a in vals}
            for a in vals:
                hi, hm = cell.h[a], mine[a]
                if (hi is None) != (hm is None) or (hi is not None and abs(hi - hm) > 1e-12):
                    dis += 1
            ci.append(cell)
            cm.append(mine)
        orders_impl[o], orders_mine[o] = ci, cm
    ni, _ = C.composition_class(orders_impl, rejected=rejected)
    nm = "NOT_EVALUATED" if rejected else my_class(orders_mine)
    counts[nm] = counts.get(nm, 0) + 1
    if ni != nm:
        dis += 1
say(f"composition rule: {trials} random arms, outcome counts {counts}, disagreements {dis}")

# boundary cases (exact thresholds)
b = C.comp_cell({"A": 0.8, "B": 0.8}, {"A": 1.0, "B": 1.0}, {"A": 0.0, "B": 0.0}, {"A": 0.0, "B": 0.0}, {"A": 1.0, "B": 1.0})
say(f"H exactly 0.80 both answers -> passes={b.passes} (spec: >= 0.80 passes)")
b2 = C.comp_cell({"A": 0.5, "B": 0.5}, {"A": 0.5, "B": 0.5}, {"A": 0.0, "B": 0.0}, {"A": 0.0, "B": 0.0}, {"A": 1.0, "B": 1.0})
say(f"G exactly 0.50 -> h={b2.h} (spec: defined at >= 0.50)")
b3 = C.comp_cell({"A": 0.3, "B": 0.3}, {"A": 0.3, "B": 0.3}, {"A": 0.0, "B": 0.0}, {"A": 0.0, "B": 0.0}, {"A": 0.3, "B": 0.3})
say(f"teacher gap exactly 0.30 -> h={b3.h} reasons={b3.reasons} (spec: defined at >= 0.30; IEEE: 0.3-0.0 == 0.3)")

# ---- 3. GEN at <= 0.02 under both decisions ----
say(f"gen_gate(0.02,0.02)={C.gen_gate(0.02, 0.02)} gen_gate(0.02,0.0200001)={C.gen_gate(0.02, 0.0200001)} gen_gate(0.03,None)={C.gen_gate(0.03, None)} gen_gate(0.01,None)={C.gen_gate(0.01, None)} gen_gate(0.01,nan)={C.gen_gate(0.01, float('nan'))}")
assert C.gen_gate(0.02, 0.02) is True and C.gen_gate(0.02, 0.0200001) is False and C.gen_gate(0.03, None) is False and C.gen_gate(0.01, None) is None

# ---- 4. m9 colon extension in cut_windows (toy char-pair tokenizer) ----
from studies.p10s2 import windows as W  # noqa: E402


class CharTok:
    def encode_offsets(self, text):
        ids, offs = [], []
        for i, ch in enumerate(text):
            ids.append(ord(ch) % 997)
            offs.append((i, i + 1))
        return ids, offs


txt = "ab German: xyz" + "q" * 60
ws = W.cut_windows(CharTok(), txt, {}, 64, 40)
say(f"m9 toy: text 'ab German: ...' (char tokens); marker_end={ws[0].marker_end}, char at marker_end={txt[ws[0].marker_end]!r} (expected ':' at index 9)")
assert ws[0].marker_end == 9
txt2 = "ab German xyz" + "q" * 60
ws2 = W.cut_windows(CharTok(), txt2, {}, 64, 40)
say(f"m9 toy: no colon -> marker_end={ws2[0].marker_end} char {txt2[ws2[0].marker_end]!r} (expected 'n' at 8)")
assert ws2[0].marker_end == 8
txt3 = "q" * 33 + "German:" + "q" * 40  # 'German' ends at token 38 (index 38), colon at 39, decision span tokens 0..39 (40 tokens)
ws3 = W.cut_windows(CharTok(), txt3, {}, 80, 39)
say(f"m9 toy: colon just beyond the decision span -> marker_end={ws3[0].marker_end} (expected 38, never beyond the span)")
assert ws3[0].marker_end == 38

# ---- 5. fixed lines and the composition block ----
comp_all_ne = {"n_replicates": 4, "arms": {"C2": {"L-joint": {"composition": "NOT_EVALUATED", "reasons": ["order -, replicate 0: teacher gap on E_C below 0.30 (A)"], "orders": {"-": [None]}, "mean_pass_rate": None, "revision5_ratio_replaced": {}, "label": "revision 5's raw-score rule, replaced by the human lead", "by_construction_answers": {"A": "x"}, "rests_on": "the French answer alone", "n_items": 500, "items_per_answer": {"A": 500, "B": 500}}}}}
txt = output.block(report.composition_lines(comp_all_ne, "(4 replicates, U = 2,000)"), composition=True)
lines = txt.splitlines()
say(f"all-NOT_EVALUATED composition block: line0==ORACLE {lines[0] == core.ORACLE_LINE}, line1==COMBINED {lines[1] == core.COMBINED_LINE}")
output.check_text(txt)
comp_c = {"n_replicates": 4, "arms": {"C2": {"L-sep": {"composition": "COMPOSES", "reasons": [], "orders": {"-": [{"replicate": 0, "n_items": 500, "items_per_answer": {"A": 500, "B": 500}, "H": {"A": 1.0, "B": 0.9}, "single_task_G": {"A": 0.7, "B": 0.8}, "s_combined": {}, "s_single": {}}]}, "mean_pass_rate": 0.05, "revision5_ratio_replaced": {}, "label": "revision 5's raw-score rule, replaced by the human lead", "by_construction_answers": {"A": "x"}, "rests_on": "the French answer alone", "n_items": 500, "items_per_answer": {"A": 500, "B": 500}}}}}
cl = report.composition_lines(comp_c, "(4 replicates, U = 2,000)")
say("C2 L-sep COMPOSES line: " + cl[1])
say("C2 L-sep cell line: " + cl[2])
assert "rests on the French answer alone" in cl[1] and "BY CONSTRUCTION (1.0)" in cl[2] and "contamination, not composition" in cl[1]
# guard: a bare composition word or H line without the second line is refused
for bad in [core.ORACLE_LINE + "\nC1 M-ii r0: COMPOSES", core.ORACLE_LINE + "\nC1 M-ii r0: H_a 0.91 / 0.88 on the second answer", "M-ii composes C1"]:
    try:
        output.check_text(bad)
        say(f"NOT refused: {bad[-50:]!r}")
    except output.OracleLineMissing:
        say(f"refused as required: {bad[-50:]!r}")
# autonomy wording: lines that would word an oracle result as autonomous success
for bad in ["M-append-frozen learned the new capability autonomously: TRANSFER-POSITIVE", "The memory learned French on its own: success", "autonomous learned-memory success on French"]:
    try:
        output.check_text(bad)
        say(f"check_text did NOT refuse (no oracle line above): {bad!r}")
    except output.OracleLineMissing:
        say(f"refused as required: {bad!r}")
print("done")
