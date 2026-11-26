"""Detail of drops and near-bound survivors from the auditor's rows. Usage: python detail.py MY_DIR THEIR_PER_LINEAGE"""
import json, sys
from fractions import Fraction as F
from collections import defaultdict
MY, TP = sys.argv[1], sys.argv[2]
rows = [json.loads(l) for l in open(f"{MY}/rows.jsonl")]
per = json.load(open(f"{MY}/per_lineage.json"))
theirs = json.load(open(TP))
B = F(3, 20)
def fx(d): return F(d["fraction"])
print("=== DROPPED: every counted row over the bound (and, per rule, the levels)")
for lid, v in sorted(per.items()):
    if not v["dropped"]:
        continue
    print(f"\n## {lid}: {v['n_rows_over']} rows over")
    g = defaultdict(list)
    for r in v["over_rows"]:
        g[(r["unit"], r["src"], r["rule"], r["reading"], r["shape"])].append(r)
    for k, rs in sorted(g.items(), key=lambda kv: str(kv[0])):
        lv = ", ".join(f"L{r['level']} {r['excess']['fraction']}={float(fx(r['excess'])):+.6f} (n={r['items']}, u={r['unc']['fraction']})" for r in sorted(rs, key=lambda r: r["level"]))
        print(f"  {k[0]}/{k[1]} [{k[3]}] {k[2]}{' shape='+k[4] if k[4] else ''}: {lv}")
    # largest uncounted rows, for context
print("\n=== per lineage: largest counted |excess|+u (max over levels), mine vs theirs")
out = []
for lid in sorted(per):
    best = None
    for lv, x in per[lid]["levels"].items():
        if x and (best is None or fx(x["abs_plus_unc"]) > fx(best[1]["abs_plus_unc"])):
            best = (lv, x)
    t = theirs[lid]
    tb = None
    for lv, x in t["levels"].items():
        if x:
            val = F(x["largest_counted_abs_excess"]["fraction"]) + F(x["rounding_uncertainty"]["fraction"])
            if tb is None or val > tb[0]:
                tb = (val, lv, x)
    out.append((fx(best[1]["abs_plus_unc"]), lid, best, tb))
for v, lid, best, tb in sorted(out, reverse=True):
    lv, x = best
    same = "same" if (tb[2]["rule"] == x["rule"] and tb[1] == lv and tb[2]["unit"] == x["unit"]) else f"THEIRS {tb[2]['unit']} {tb[2]['rule']} L{tb[1]} {float(tb[0]):.6f}"
    print(f"{lid:40s} {'DROP' if per[lid]['dropped'] else 'keep'} {float(v):.6f} L{lv} {x['unit']}/{x['src']} [{x['reading']}] {x['rule'][:70]} ex={x['excess']['fraction']} n={x['items']} u={x['unc']['fraction']} | {same} theirs_dropped={theirs[lid]['dropped']}")
