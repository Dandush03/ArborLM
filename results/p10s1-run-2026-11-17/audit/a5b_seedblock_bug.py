# ruff: noqa
"""Hypothesis check: the reported seed-block spreads equal F-OQ (main seed) against the F-OQ-IVF read of the two extra seeds."""
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
from auditlib import View, load_cells, U_P_ROW, RUN
cells = load_cells()
an = json.load(open(f"{RUN}/analysis.json"))["result"]["capacity"]["seed_block"]["cells"]
mism_correct, match_bug = 0, 0
for key, v in sorted(an.items()):
    dr, cell, ro = key.split()
    d = int(dr[4:]); fs, ns = cell.split("/"); f = int(fs[:-1]) * 1024; n = int(ns[:-1]) * 1024
    seeds = (2111, 2121) if d == 1 else (2112, 2122)
    main = View(cells[("P", "F-OQ", f, n, d, 2100 + d)], "A")
    u = main.u_p if ro == "U_P" else main.run
    right = [main.i(u)] + [View(cells[("SB", "F-OQ", f, n, d, s)], "A").i(u) for s in seeds]
    bug = [main.i(u)] + [View(cells[("SB", "F-OQ-IVF", f, n, d, s)], "A").i(u) for s in seeds]
    sr, sb = max(right) - min(right), max(bug) - min(bug)
    match_bug += abs(sb - v["spread_within_draw"]) < 1e-9
    mism_correct += abs(sr - v["spread_within_draw"]) > 1e-9
    print(f"{key:24s} reported {v['spread_within_draw']:.4f}  F-OQ seeds (correct) {sr:.4f}  F-OQ main vs F-OQ-IVF extras {sb:.4f}  across {v['spread_across_draws']:.4f} reported dominates {v['dominates']}; correct dominates {'init seed' if sr > v['spread_across_draws'] else 'data draw'}")
print("entries:", len(an), "reported == bug hypothesis:", match_bug, " reported != correct:", mism_correct)
