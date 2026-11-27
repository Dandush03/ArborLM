# ruff: noqa
"""Audit 3 (R2): summarise a3_shortcuts output. Prints, per lineage and shape, every heuristic whose effect (acc - chance; two-sided |acc-0.5| for yes/no)
reaches THR at some level, with the per-level effects L0..L6. Usage: python3 -I a3_summ.py IN.json THR"""
import json
import sys

d = json.load(open(sys.argv[1]))
thr = float(sys.argv[2])
for lid, res in sorted(d["lineages"].items()):
    shapes = sorted({sh for lv in res.values() for sh in lv})
    lines = []
    for sh in shapes:
        hn_all = sorted({hn for lv in res.values() if sh in lv for hn in lv[sh]["heur"]})
        for hn in hn_all:
            effs = []
            for lv in map(str, range(7)):
                e = res.get(lv, {}).get(sh, {}).get("heur", {}).get(hn)
                if e is None:
                    effs.append(None)
                    continue
                at = res[lv][sh]["answer_type"]
                effs.append((e.get("two_sided") if at == "yn" else e["minus_chance"], e["acc"], e["n"]))
            mx = max((x[0] for x in effs if x), default=0)
            if mx >= thr:
                cells = " ".join("  -  " if x is None else f"{x[1]:.2f}" for x in effs)
                lines.append(f"   [{sh}] {hn}: acc L0..L6 = {cells}  (max effect {mx:+.2f})")
    yn = []
    for sh in shapes:
        ys = [res[lv][sh].get("yes_share") for lv in map(str, range(7)) if sh in res.get(lv, {})]
        if ys and ys[0] is not None:
            yn.append(f"[{sh}] yes share " + " ".join(f"{y:.2f}" for y in ys))
    if lines or yn:
        print(lid)
        for y in yn:
            print("   " + y)
        for l in lines:
            print(l)
