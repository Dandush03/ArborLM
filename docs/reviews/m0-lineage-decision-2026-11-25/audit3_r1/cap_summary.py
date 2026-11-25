# ruff: noqa
"""Audit 3 (R1): capacity verdicts from capacity3.py output.

S_lo = N(N-1) / (2 C_up), C_up = C + 1.645 sqrt(C) + 1 (a rough one-sided 95 % upper bound on the colliding pairs), on the LOW
(isomorphism-invariant) key: a conservative estimate of the number of structures. Requirement per cluster and level:
  core levels 1-5: 10 x (ceil(24,000 / G) + 100); reserve levels 0 and 6: 1,000 (plan reading) or the core figure (audit reading:
  section 6.5 lets the reserve levels enter the chosen range, so the pools can be drawn there).
Two allocations: CLUSTER-SUM (the cluster's shapes pooled: sum of S_lo) and EVEN-SHARE (the plan's section 2.4 spreads a cluster's
items evenly over its shapes: each shape needs requirement / m).
usage: python cap_summary.py <G> <map: v2|mine> <files...>
"""
import json, math, sys
from collections import defaultdict

G = int(sys.argv[1]); which = sys.argv[2]; files = sys.argv[3:]
core = 10 * (math.ceil(24000 / G) + 100)
V2 = [("order_compare", "road_reachability", "categories_follow", "equivalence_classes"), ("event_timeline", "temporal_weekday_shift", "spatial_relative_directions", "equivalence_exchange_rates"),
      ("kinship_ancestor", "kinship_cousins", "categories_default_exceptions"), ("knights_knaves", "one_culprit"), ("seating_row", "pet_owners"),
      ("attribute_rule", "conditional_decision_tree", "minimax_tree"), ("compass_turns", "boolean_lights"), ("order_extreme", "order_tournament_wins", "topological_order"),
      ("containers_queue_line", "elimination_josephus")]
MINE_EXTRA = {"conditional_chain": "knights_knaves", "elimination_bracket": "attribute_rule"}
import re


def base(lid):
    return re.sub(r"_r\d+$", "", lid.split(".", 1)[1])


def cluster(lid):
    b = base(lid)
    if which == "mine" and b in MINE_EXTRA:
        b = MINE_EXTRA[b]
    for g in V2:
        if b in g:
            return min(g)
    return b


rows = {}
for f in files:
    for line in open(f):
        line = line.strip()
        if line.startswith("{"):
            r = json.loads(line)
            rows[(r["lineage"], r["level"])] = r


def s_lo(r):
    N, C = r["N"], r["low_pairs"]
    cu = C + 1.645 * math.sqrt(C) + 1
    return min(N * (N - 1) / (2 * cu), 10 ** 9)


lids = sorted({k[0] for k in rows})
cl = defaultdict(list)
for l in lids:
    cl[cluster(l)].append(l)
print(f"G = {G}, map = {which}, core requirement {core:,}; shapes measured {len(lids)}; clusters {len(cl)}")
for reading in ("plan", "audit"):
    print(f"\n== reserve levels at {'1,000' if reading == 'plan' else f'{core:,}'} ({reading} reading)")
    for c, ms in sorted(cl.items()):
        for lv in range(7):
            req = core if (lv in (1, 2, 3, 4, 5) or reading == "audit") else 1000
            if any((m, lv) not in rows for m in ms):
                print(f"  {c} L{lv}: NOT MEASURED for {[m for m in ms if (m, lv) not in rows]}")
                continue
            tot = sum(s_lo(rows[(m, lv)]) for m in ms)
            share = req / len(ms)
            weak = [(m.split('.')[1], round(s_lo(rows[(m, lv)]))) for m in ms if s_lo(rows[(m, lv)]) < share]
            if tot < req or weak:
                print(f"  {c} L{lv}: need {req:,}; cluster-sum {round(tot):,} {'FAIL' if tot < req else 'ok'}; even-share need {round(share):,} per shape; below share: {weak}")
