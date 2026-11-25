# ruff: noqa
"""Audit 4 of M1: structural capacity, sampled, with the auditor's OWN canonical key (not m1_fix3_gates.canon_key).
Distinct = a different structural item: every numeric value counts; names, setting sentence, object / activity / colour words, the order of commutative parts
(legs of a trip, items bought, the two pipes, the two ingredients, multiplicative percent steps, the two fractions spent, ratio parts with their names, sets of a Venn
problem, rows of a grid under translation / rotation / reflection, the two horizontal box dimensions) and a change of setting with the same computation
(quadratic rect_area == product) do not count.
n_eff = M(M-1) / (2 * colliding pairs) (inverse collision probability; a lower bound on support); Chao1 = support estimate; D = distinct keys seen.
Seed 23 (audit throwaway). Usage: PYTHONHASHSEED=0 PYTHONPATH=<impl> uv run --locked --offline python capacity_a4.py M out.json [only]
"""
import itertools
import json
import sys
import time
from collections import Counter
from multiprocessing import get_context

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common_a4 import ALL_LEVELS, current_set, items, stem

SEED = 23


def J(x):
    return json.dumps(x, sort_keys=True)


def grid_key(rows):
    cells = [(y, x) for y, rr in enumerate(rows) for a, b in rr for x in range(a, b + 1)]
    best = None
    for sy, sx, tr in itertools.product((1, -1), (1, -1), (0, 1)):
        pts = [(sy * y, sx * x) for y, x in cells]
        if tr:
            pts = [(x, y) for y, x in pts]
        my, mx = min(p[0] for p in pts), min(p[1] for p in pts)
        k = tuple(sorted((p[0] - my, p[1] - mx) for p in pts))
        best = k if best is None or k < best else best
    return J(best)


def ie_key(s):
    if s["triple"] is None:
        return J(["2", s["total"], sorted(s["sizes"]), s["pairs"], s["ask"]])
    a, p = s["sizes"], s["pairs"]
    pair = {(0, 1): p[0], (0, 2): p[1], (1, 2): p[2]}
    best = None
    for q in itertools.permutations(range(3)):
        k = (tuple(a[q[i]] for i in range(3)), tuple(pair[tuple(sorted((q[i], q[j])))] for i, j in ((0, 1), (0, 2), (1, 2))))
        best = k if best is None or k < best else best
    return J(["3", s["total"], best, s["triple"], s["ask"]])


def key(n, s):
    if n == "shopping":
        return J([sorted(map(tuple, s["items"])), s["paid"]])
    if n == "speed_distance":
        return J([sorted(map(tuple, s["legs"])), s["average"]])
    if n == "mixture":
        return J([sorted([(s["x"], s["a"]), (s["y"], s["b"])]), s["packing"]])
    if n == "percent_change":
        ups = sorted(p for k, p in s["steps"] if k == "up")
        downs = sorted(p for k, p in s["steps"] if k == "down")
        return J([s["price"], ups, downs])
    if n == "tip_split":
        return J([s["bill"], s["tip"], s["people"]])
    if n == "fraction_remainder":
        return J([s["start"], sorted([s["a"], s["b"]])])
    if n == "ratio_share":
        return J([sorted(s["parts"]), s["parts"][s["who"]], s["total"]])
    if n == "linear_equation":
        return J(["two", sorted([(s["k"], s["m"]), (s["j"], s["n"])])]) if s["j"] else J(["one", s["k"], s["m"], s["n"]])
    if n == "ages":
        return J([s["k"], s["t"], s["sum"], s["ask"]])
    if n == "consecutive":
        return J([s["count"], s["step"], s["sum"], s["ask"]])
    if n == "average_missing":
        return J([sorted(s["scores"]), s["mean_cents"], s["n"]])
    if n == "pipes_work":
        return J([sorted([s["a"], s["b"]]), s["drain"], s["volume"]])
    if n == "rectangle":
        return J([s["shape"], s["perimeter"], s["ratio"], s["excess"]])
    if n == "coins":
        return J([s["lo"], s["hi"], s["count"], s["cents"], s["ask"]])
    if n == "arithmetic_series":
        return J([s["first"], s["step"], s["days"]])
    if n == "clock_duration":
        return J(s["legs"])
    if n == "gcd_lcm":
        return J([s["ask"], sorted(s["values"])])
    if n == "crt_congruence":
        return J(sorted(map(tuple, s["conditions"])))
    if n == "prime_factors":
        return J([s["n"], s["ask"]])
    if n in ("last_digit_power", "power_remainder"):
        return J([s["modulus"], s["op"] if len(s["terms"]) > 1 else "-", sorted(map(tuple, s["terms"]))])
    if n == "inclusion_exclusion":
        return ie_key(s)
    if n == "binomial_choose":
        return J(sorted(map(tuple, s["groups"])))
    if n == "slot_permutations":
        return J([s["digits"], s["length"], s["repeat"], s["first"], s["last"]])
    if n == "change_ways":
        return J([s["coins"], s["target"]])
    if n == "pigeonhole_worst_case":
        return J([sorted(s["counts"]), s["goal"], s["k"]])
    if n == "median_list":
        return J(sorted(s["values"]))
    if n == "mode_tally":
        return J([sorted(s["values"]), s["ask"]])
    if n == "division_counting":
        return J(sorted(s.items()))
    if n == "quadratic_area":
        sh = s["shape"]
        if sh in ("rect_area", "product"):
            return J(["xx+d", s["d"], s["area"]])
        if sh == "rect_perimeter":
            return J(["PA", s["perimeter"], s["area"]])
        return J(["sq", s["d"], s["total"]])
    if n == "pythagoras":
        a, b = s["legs"]
        if s["shape"] in ("walk", "diagonal"):
            return J(["hyp", sorted([a, b])])
        if s["shape"] == "perimeter":
            return J(["per", sorted([a, b])])
        return J(["leg", s["hyp"], s["given"][1]])
    if n == "grid_perimeter":
        return grid_key(s["rows"])
    if n == "painted_cube":
        a, b, c = s["dims"]
        dims = sorted([a, b, c]) if not s["bottom_unpainted"] else sorted([a, b]) + [c]
        return J([dims, s["bottom_unpainted"], s["faces"]])
    if n == "recurrence_iterate":
        return J([s["shape"], s["first"], s["mult"], s["add"], s["position"]])
    if n == "finite_differences":
        return J([s["terms"], s["degree"], s["ask"]])
    if n == "digit_puzzle":
        return J([s["digits"], sorted(J(c) for c in s["clues"])])
    if n == "tiered_pricing":
        return J(sorted((k, v) for k, v in s.items()))
    raise KeyError(n)


def one(args):
    lid, lv, M = args
    lin = current_set(True)[lid]
    n = stem(lid)
    t0 = time.time()
    cnt = Counter(key(n, it.structured) for it in items(lin, lv, M, SEED, "cap"))
    pairs = sum(c * (c - 1) // 2 for c in cnt.values())
    f = Counter(cnt.values())
    f1, f2 = f.get(1, 0), f.get(2, 0)
    chao = len(cnt) + (f1 * f1 / (2 * f2) if f2 else f1 * (f1 - 1) / 2)
    return lid, lv, {"M": M, "D": len(cnt), "pairs": pairs, "n_eff": (M * (M - 1) / (2 * pairs)) if pairs else None, "chao1": round(chao), "sec": round(time.time() - t0, 1)}


if __name__ == "__main__":
    M, path = int(sys.argv[1]), sys.argv[2]
    ids = sorted(current_set(True))
    if len(sys.argv) > 3:
        ids = [i for i in ids if any(o in i for o in sys.argv[3].split(","))]
    tasks = [(i, lv, M) for i in ids for lv in ALL_LEVELS]
    with get_context("spawn").Pool(14) as p:
        res = p.map(one, tasks, chunksize=1)
    out = {}
    for lid, lv, r in res:
        out.setdefault(lid, {})[str(lv)] = r
    json.dump({"M": M, "seed": SEED, "levels": out}, open(path, "w"), indent=1, sort_keys=True)
    for lid in ids:
        print(f"{lid:32s}", " ".join(f"{round(out[lid][str(l)]['n_eff']) if out[lid][str(l)]['n_eff'] else 'inf'}" for l in ALL_LEVELS))
