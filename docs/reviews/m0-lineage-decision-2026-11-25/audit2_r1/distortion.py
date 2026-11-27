# ruff: noqa
"""Structural features per level, registered (redrawn) vs unconditioned sample; plus capacity counts and per-level firing
of the categories_r3 immediate-supergroup tell. Usage: distortion.py ITEMSDIR"""
import gzip, json, os, sys
from collections import Counter, defaultdict
from itertools import product

d = sys.argv[1]


def load(lid, mode):
    p = os.path.join(d, f"{lid}.{mode}.jsonl.gz")
    return [json.loads(x) for x in gzip.open(p, "rt")] if os.path.exists(p) else []


def table(lid, feat, desc):
    print(f"\n## {lid}: {desc}")
    for mode in ("unc", "reg"):
        rows = load(lid, mode)
        if not rows:
            continue
        by = defaultdict(list)
        for r in rows:
            v = feat(r)
            if v is not None:
                by[r["level"]].append(v)
        cells = []
        for lv in range(7):
            xs = by[lv]
            if xs and isinstance(xs[0], (int, float)):
                cells.append(f"L{lv}:{sum(xs)/len(xs):.2f}")
            else:
                c = Counter(xs)
                cells.append(f"L{lv}:" + ",".join(f"{k}={v/len(xs):.2f}" for k, v in sorted(c.items())))
        print(f"  {mode}: " + " | ".join(cells))


def irv_rounds_leader_changes(r):
    s = r["s"]
    C, B = s["candidates"], s["ballots"]
    first = Counter()
    for c, rk in B:
        first[rk[0]] += c
    return int(max(C, key=lambda x: first[x]) == r["a"])


def sm_rank(r):
    s = r["s"]
    return s["prefs_p"][s["ask"]].index(r["a"]) + 1


def kd_depth(r):
    par = r["s"]["parent"]
    x, k = r["a"], 0
    while x in par:
        x, k = par[x], k + 1
    return k


def br_round(r):
    s = r["s"]
    if s["ask"][0] != "beaten_by":
        return None
    pl = s["players"]
    beat = {(a, b) for a, b in s["results"]}
    rnd, rd = pl[:], 0
    x = s["ask"][1]
    while len(rnd) > 1:
        rd += 1
        nx = []
        for a, b in zip(rnd[0::2], rnd[1::2]):
            w, l = (a, b) if (a, b) in beat else (b, a)
            if l == x:
                return rd
            nx.append(w)
        rnd = nx


def thr_gap(r):
    s = r["s"]
    w = dict((p, x) for p, x in s["members"])
    diff = sum(w[p] for p in w if s["votes"][p] == "yes") - sum(w[p] for p in w if s["votes"][p] == "no")
    return abs(diff - s["margin"])


def thr_margin(r):
    return r["s"]["margin"]


def st_moves_onto(r):
    s = r["s"]
    return sum(1 for o in s["ops"] if o[0] == "move" and o[2] == s["ask"])


def act_ratio(r):
    return int(r["a"]) / len(r["s"]["meetings"])


def topo_alpha_rank(r):
    s = r["s"]
    return sorted(p for p, _ in s["jobs"]).index(r["a"]) + 1 - s["day"]


table("instant_runoff_r2", irv_rounds_leader_changes, "share of items whose IRV winner is the first-round plurality leader")
table("stable_matching_r2", sm_rank, "mean rank of the answer on the asker's list (1 = first choice)")
table("stable_matching_r2", lambda r: min(sm_rank(r), 3), "distribution of the asker's partner rank (3 = third or worse)")
table("kinship_descendants_r3", kd_depth, "mean depth of the answer (1 = child of the root)")
table("elimination_bracket_r3", br_round, "beaten_by items: round in which the asked player is knocked out")
table("conditional_threshold_rule_r3", thr_gap, "mean |(yes - no weight) - margin| (distance from the threshold)")
table("conditional_threshold_rule_r3", lambda r: int(r["s"]["margin"] <= 0) if True else None, "share with margin <= 0")
table("containers_stack_piles_r3", st_moves_onto, "mean number of moves onto the asked pile")
table("activity_selection", act_ratio, "answer / number of meetings")
table("mst_cost", lambda r: int(r["a"]), "mean answer")
table("topological_order_r2", topo_alpha_rank, "answer's alphabetical rank minus asked day (0 = jth alphabetical)")
table("topological_order_r2", lambda r: r["s"]["day"], "mean asked day j")

# categories_r3: the immediate-supergroup tell, per level
print("\n## categories_default_exceptions_r3: share of items where the member's immediate supergroup (named in the first sentence) carries a rule about the asked verb, and accuracy of that rule")
rows = load("categories_default_exceptions_r3", "reg")
by = defaultdict(lambda: [0, 0, 0])
for r in rows:
    s = r["s"]
    rr = [x for x in s["rules"] if x[1] == s["verb"] and x[0] == s["chain"][1]]
    by[r["level"]][0] += 1
    if rr:
        by[r["level"]][1] += 1
        by[r["level"]][2] += int(("yes" if rr[0][2] else "no") == r["a"])
    first_sentence = r["q"].split(".")[0]
    assert first_sentence == f"Every {s['chain'][0]} is a {s['chain'][1]}"
print("  " + " | ".join(f"L{lv}: fires {v[1]/v[0]:.3f}, correct when fires {v[2]/max(1,v[1]):.3f}" for lv, v in sorted(by.items())))
n_ask_rules = Counter(sum(1 for x in r["s"]["rules"] if x[1] == r["s"]["verb"]) for r in rows)
own = sum(1 for r in rows if any(x[0] == r["s"]["chain"][0] and x[1] == r["s"]["verb"] for x in r["s"]["rules"]))
print(f"  number of rules about the asked verb: {dict(n_ask_rules)}; items where the member's own group has a rule about the asked verb: {own}")

# nim capacity: ordered k-tuples in [1, m] with XOR 0 (answer 'second') and with XOR != 0 and even sum (answer 'first')
print("\n## nim_xor capacity (exact counts of distinct ordered pile tuples per level)")
for lv in range(7):
    k, m = 3 + lv // 3, 20 + 4 * lv
    if k <= 4:
        z = nz = 0
        for t in product(range(1, m + 1), repeat=k - 1):
            x = 0
            for v in t:
                x ^= v
            # last pile c: XOR zero iff c == x
            if 1 <= x <= m:
                z += 1
            # even total and nonzero xor: count c in [1,m] with c != x and parity(c) == parity(sum t)
            par = sum(t) % 2
            cnt = sum(1 for c in range(1, m + 1) if c % 2 == par and c != x)
            nz += cnt
        print(f"  L{lv}: k={k}, piles 1..{m}: 'second' tuples {z}, 'first' tuples {nz}")
    else:
        print(f"  L{lv}: k={k}, piles 1..{m}: large (not enumerated)")
rows = load("nim_xor", "reg")
for lv in range(7):
    rs = [r for r in rows if r["level"] == lv]
    for ans in ("first", "second"):
        qs = [r["q"] for r in rs if r["a"] == ans]
        print(f"  sample L{lv} {ans}: {len(qs)} drawn, {len(set(qs))} distinct")

# minimax and venn level structure
print("\n## level structure: minimax depth by level, venn group count by level, nim pile count by level")
for lid, f in (("minimax_tree", lambda r: int(r["q"].split("game with ")[1].split(" ")[0])), ("venn_counting", lambda r: len(r["s"]["groups"])), ("nim_xor", lambda r: len(r["s"]["piles"]))):
    rows = load(lid, "reg")
    print(f"  {lid}: " + " ".join(f"L{lv}={sorted(set(f(r) for r in rows if r['level']==lv))}" for lv in range(7)))
