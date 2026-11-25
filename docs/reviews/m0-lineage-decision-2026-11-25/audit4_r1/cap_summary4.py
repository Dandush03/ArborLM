# ruff: noqa
"""Audit 4 (R1): capacity verdicts from capacity4.py rows.
Demand per cluster and level (R-11, R-10: reserve levels the same): 10 x (ceil(4,000/G) + ceil(20,000/G) + 100), G = 11 -> 22,830.
S_lo = N(N-1) / (2 C_up), C_up = C + 1.645 sqrt(C) + 1, on the isomorphism-invariant (LOW) key: a conservative effective-support figure
(1/sum p^2 <= support): S_lo >= requirement proves a pass; S_lo below it does NOT prove a failure (exact counts decide those).
Readings of allocation: CLUSTER-SUM (sum over the cluster's shapes) and EVEN-SHARE (each of m shapes needs requirement / m).
usage: python cap_summary4.py <G> <rows.jsonl ...>"""
import json, math, re, sys
from collections import defaultdict
G = int(sys.argv[1]); files = sys.argv[2:]
req = 10 * (math.ceil(4000 / G) + math.ceil(20000 / G) + 100)
MERGES = [("order_compare", "road_reachability", "categories_follow", "equivalence_classes"), ("event_timeline", "temporal_weekday_shift", "spatial_relative_directions", "equivalence_exchange_rates"),
          ("kinship_ancestor", "kinship_cousins", "categories_default_exceptions"), ("knights_knaves", "one_culprit", "conditional_chain"),
          ("attribute_rule", "conditional_decision_tree", "minimax_tree", "elimination_bracket"), ("compass_turns", "boolean_lights")]
def base(l): return re.sub(r"_r\d+$", "", l.split(".", 1)[1])
def cluster(l):
    b = base(l)
    for g in MERGES:
        if b in g: return min(g)
    return b
rows = {}
for f in files:
    for line in open(f):
        if line.startswith("{"):
            r = json.loads(line); rows[(r["lineage"], r["level"])] = r
def s_lo(r):
    C = r["low_pairs"]; N = r["N"]; cu = C + 1.645 * math.sqrt(C) + 1
    return N * (N - 1) / (2 * cu)
cl = defaultdict(list)
for l in sorted({k[0] for k in rows}): cl[cluster(l)].append(l)
print(f"G = {G}; requirement per cluster and level {req:,} at every level 0-6; {len(rows)} rows; {len(cl)} clusters")
fails = 0
for c, ms in sorted(cl.items()):
    for lv in range(7):
        miss = [m for m in ms if (m, lv) not in rows]
        if miss: print(f"  {c} L{lv}: NOT MEASURED {miss}"); continue
        tot = sum(s_lo(rows[(m, lv)]) for m in ms); share = req / len(ms)
        weak = [(base(m), round(s_lo(rows[(m, lv)])), rows[(m, lv)]["low_distinct"], rows[(m, lv)]["N"]) for m in ms if s_lo(rows[(m, lv)]) < share]
        if tot < req or weak:
            fails += 1
            print(f"  {c} L{lv}: cluster-sum S_lo {round(tot):,} {'BELOW' if tot < req else 'ok'}; even share {round(share):,}; shapes below share (shape, S_lo, distinct seen, N): {weak}")
print(f"cluster-levels flagged (not proven failures): {fails}")
