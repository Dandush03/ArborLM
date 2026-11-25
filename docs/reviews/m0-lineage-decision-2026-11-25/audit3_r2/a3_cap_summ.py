# ruff: noqa
"""Audit 3 (R2): capacity per CLUSTER (my strict map: sum of member lineages' structural counts) against the demand
need(G) = 10 * (ceil(24000 / G) + 100) on core levels 1-5 and 1000 on reserve levels 0, 6 (LEAD_RULINGS_2 R-5 as given in the brief).
Also prints the alternative reading in which a reserve level carries the core demand (ADR-0033 6.5: reserve levels can enter the chosen range).
A count is 'saturated' when distinct < 0.9 * draws (the draw sample has seen most of the space); otherwise the true space is larger than the count.
Usage: python3 -I a3_cap_summ.py a3_capacity.json G"""
import json
import math
import sys

d = json.load(open(sys.argv[1]))
G = int(sys.argv[2])
need_core = 10 * (math.ceil(24000 / G) + 100)
MERGES = [("R2.sort_list", "R2.kth_smallest"), ("R2.count_letter", "R2.count_divisible"), ("R2.to_base_wide", "R2.from_base"), ("R2.permutation_power", "R2.modular_power")]
ids = sorted(d["lineages"])
cl = {i: i for i in ids}
for a, b in MERGES:
    cl[b] = cl[a]
clusters = {}
for i in ids:
    clusters.setdefault(cl[i], []).append(i)
print(f"G={G}: core need {need_core}, reserve need 1000; clusters {len(clusters)}")
for reading in "ABC":
    fails, fails_alt = [], []
    for c, mem in sorted(clusters.items()):
        for lv in range(7):
            tot = 0
            sat = True
            parts = []
            for m in mem:
                row = d["lineages"][m][str(lv)]
                x = row[reading]
                tot += x["distinct"]
                parts.append(f"{m.split('.')[1]}={x['distinct']}/{row['draws']} chao1~{x['chao1']:.0f}")
            need = need_core if 1 <= lv <= 5 else 1000
            if tot < need:
                fails.append(f"  {c} L{lv}: {tot} < {need}  [{'; '.join(parts)}]")
            if lv in (0, 6) and tot < need_core:
                fails_alt.append(f"  {c} L{lv}: {tot} < {need_core}")
    print(f"reading {reading}: {len(fails)} failing cluster-levels")
    for f in fails:
        print(f)
    print(f"reading {reading}, reserve levels at the core demand (alternative reading): {len(fails_alt)} more")
    for f in fails_alt:
        print(f)
