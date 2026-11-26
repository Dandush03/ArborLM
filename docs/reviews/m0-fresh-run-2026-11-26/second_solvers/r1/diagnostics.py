"""Alternative-reading and boundary diagnostics (no answers are changed by this script)."""
import json, os, sys
from itertools import product, combinations
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import solver2_r1 as S
D = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126/R1/"
def rows(lin): return [json.loads(l) for l in open(D + lin + "/fixtures.jsonl")]

# threshold: items exactly on the boundary (net == D), where "at least" (>=) vs "more than" (>) differ
b = []
for r in rows("R1.conditional_threshold_rule_r4"):
    s = r["structured"]; w = dict(map(tuple, s["members"]))
    net = sum(w[n] if v == "yes" else -w[n] if v == "no" else 0 for n, v in s["votes"].items())
    if net == s["margin"]: b.append((r["level"], r["index"]))
print("threshold: net == D on", len(b), "items", b)

# venn: alternative reading 'both A and B' = exactly those two (exclusive counts)
diff = []; n34 = 0
for r in rows("R1.venn_counting_r5"):
    s = r["structured"]; g = s["groups"]; m = len(g)
    if m < 3: continue
    n34 += 1
    # exclusive reading: sizes inclusive, pair/triple numbers = exactly-that-region
    ex2 = sum(s["pairs"].values()); ex3 = sum(s["triples"].values()) if m == 4 else s["triple"]
    ex4 = s["quad"] or 0
    if m == 3: ex3 = s["triple"]
    exactly = {2: ex2, 3: ex3, 4: ex4}
    in_some = sum(s["sizes"].values()) - ex2 - 2 * ex3 - 3 * ex4  # each person counted k times in sizes
    alt = {"none": s["total"] - in_some, "one": in_some - ex2 - ex3 - ex4, "two": ex2, "atleast_two": ex2 + ex3 + ex4}[s["ask"]]
    if str(alt) != S.venn("", s): diff.append((r["level"], r["index"], s["ask"], S.venn("", s), alt))
print("venn: 3/4-group items", n34, "; answer differs under exclusive-pair reading on", len(diff))
print("   e.g.", diff[:5])

# knights: number of consistent full assignments
cnt = {}
for r in rows("R1.knights_knaves_r6"):
    s = r["structured"]; n = len(s["people"]); sol = 0
    for k in product((True, False), repeat=n):
        if all(k[i] == S._stmt(kd, ix, k) for i, (kd, ix) in enumerate(s["statements"])): sol += 1
    cnt[sol] = cnt.get(sol, 0) + 1
print("knights: distribution of number of consistent worlds:", cnt)

# categories: depth of the deciding rule; items where the general-most rule disagrees
dec = {}; flip = 0
for r in rows("R1.categories_default_exceptions_r4"):
    s = r["structured"]
    rel = [(s["chain"].index(gp), c) for gp, v, c in s["rules"] if v == s["verb"]]
    rel.sort(); dec[rel[0][0]] = dec.get(rel[0][0], 0) + 1
    if rel[0][1] != rel[-1][1]: flip += 1
print("categories: chain position of deciding rule:", dict(sorted(dec.items())), "; items where most-general rule disagrees:", flip)

# compass: left = counterclockwise check of reading; count items where swapping left/right would change answer
ch = 0
for r in rows("R1.compass_turns"):
    s = r["structured"]
    s2 = {"start": s["start"], "seq": [[k, {"left": "right", "right": "left"}.get(a, a) if k == "turn" else a] for k, a in s["seq"]]}
    if S.compass("", s) != S.compass("", s2): ch += 1
print("compass: items whose answer depends on left=ccw/right=cw:", ch)

# swap: rotate direction reversed reading
ch = 0
for r in rows("R1.swap_tracking_r5"):
    s = r["structured"]
    s2 = dict(s, ops=[["rotate", o[1], o[3], o[2]] if o[0] == "rotate" else o for o in s["ops"]])
    if S.swap_tracking("", s) != S.swap_tracking("", s2): ch += 1
print("swap: items whose answer would change under reversed rotation:", ch)

# exchange: items with a cycle (more rates than needed for connectivity)
cyc = sum(1 for r in rows("R1.equivalence_exchange_rates_r6") if len(r["structured"]["rates"]) >= len(r["structured"]["items"]))
print("exchange: items with redundant rates (cycles):", cyc)
cyc = sum(1 for r in rows("R1.temporal_weekday_shift_r6") if len(r["structured"]["links"]) >= len({e for l in r["structured"]["links"] for e in l[:2]} | {r["structured"]["anchor"][0]}))
print("weekday: items with redundant links (cycles):", cyc)
