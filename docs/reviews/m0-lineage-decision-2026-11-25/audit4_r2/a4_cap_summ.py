# ruff: noqa
"""Audit 4 (R2): capacity verdicts per cluster-level from a4_capacity JSON, on MY strict map (4 merges, 36 clusters), at a given G.
Demand (R-11): 10 x (ceil(4000/G) + ceil(20000/G) + 100), the same at reserve levels (R-10). Cluster capacity = sum of members' distinct counts.
PASS: sum of D >= demand (D is a lower bound on the space). FAIL: sum of Chao1 < demand. UNRESOLVED otherwise.
Usage: python3 -I a4_cap_summ.py a4_capacity_100k.json G"""
import json
import math
import sys

d = json.load(open(sys.argv[1]))
G = int(sys.argv[2])
need = 10 * (math.ceil(4000 / G) + math.ceil(20000 / G) + 100)
MERGES = [("sort_list", "kth_smallest"), ("count_letter", "count_divisible"), ("to_base_wide", "from_base"), ("permutation_power", "modular_power")]
ids = sorted(x.split(".")[1] for x in d["lineages"])
cl = {i: [i] for i in ids}
for a, b in MERGES:
    cl[a] = cl[a] + cl.pop(b)
print(f"N draws = {d['N']}; clusters = {len(cl)}; G = {G}; demand per cluster-level = {need}")
for rd in "abc":
    fails, unres, partner = [], [], []
    for key, mem in sorted(cl.items()):
        for lv in range(7):
            D = sum(d["lineages"]["R2." + m][str(lv)][rd]["D"] for m in mem)
            C = sum(d["lineages"]["R2." + m][str(lv)][rd]["chao1"] for m in mem)
            if D >= need:
                if len(mem) > 1:
                    for m in mem:
                        dm = d["lineages"]["R2." + m][str(lv)][rd]
                        if dm["D"] < need and dm["chao1"] < need:
                            partner.append(f"{m} L{lv} (alone D={dm['D']}, Chao1={dm['chao1']:.0f})")
                continue
            if C < need:
                fails.append(f"{key} L{lv}: D={D} Chao1={C:.0f}")
            else:
                unres.append(f"{key} L{lv}: D={D} Chao1={C:.0f}")
    print(f"\nreading {rd}: FAIL {len(fails)}, UNRESOLVED {len(unres)}")
    for x in fails:
        print("   FAIL", x)
    for x in unres:
        print("   UNRESOLVED", x)
    for x in partner:
        print("   passes only through its cluster partner:", x)
