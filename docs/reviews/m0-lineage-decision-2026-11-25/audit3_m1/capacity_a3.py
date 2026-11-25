# ruff: noqa
"""Audit 3 of M1: structural capacity, my own canonical keys (written without copying the implementer's canon_key; where we agree it is by the same reading).
Not distinct: names, the setting sentence, object/activity/colour words, presentation order of commutative parts, and (stricter than the implementer)
a change of SETTING that leaves the computation identical (pythagoras walk == diagonal; ladder_top == ladder_base; binomial two_groups with the genders swapped).
Distinct: any change of a numeric parameter value (ADR-0033 6.2 counts 'distinct items'; R-5 names only names, setting and order as non-distinct).
Per lineage and level: M draws (seed 7), D distinct keys, f1/f2 singletons/doubletons, n_eff = M(M-1)/(2 P) (inverse collision probability; a lower
bound on support), Chao1 = D + f1^2 / (2 f2) (support estimate).
Usage: PYTHONHASHSEED=0 PYTHONPATH=<impl> uv run --locked --offline python capacity_a3.py M out.json
"""
import itertools
import json
import sys
import time
from collections import Counter
from multiprocessing import get_context

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common_a3 import ALL_LEVELS, current_set, items

SEED = 7


def J(x):
    return json.dumps(x, sort_keys=True)


def key(n, s):
    if n == "shopping":
        return J([sorted(map(tuple, s["items"])), s["paid"]])
    if n == "speed_distance":
        return J([sorted(map(tuple, s["legs"])), s["average"]])
    if n == "pipes_work":
        return J([sorted([s["a"], s["b"]]), s["drain"], s["volume"]])
    if n == "percent_change":
        return J([s["price"], sorted(map(tuple, s["steps"]))])
    if n == "ratio_share":
        return J([sorted(s["parts"]), s["parts"][s["who"]], s["total"]])
    if n == "mixture":
        return J([sorted([(s["x"], s["a"]), (s["y"], s["b"])]), s["packing"]])
    if n == "linear_equation":
        if s["j"]:
            return J(["two", sorted([(s["k"], s["m"]), (s["j"], s["n"])])])
        return J(["one", s["k"], s["m"], s["n"]])
    if n == "average_missing":
        return J([sorted(s["scores"]), s["mean_cents"]])
    if n == "gcd_lcm":
        return J([s["ask"], sorted(s["values"])])
    if n == "crt_congruence":
        return J(sorted(map(tuple, s["conditions"])))
    if n == "power_remainder":
        return J([s["modulus"], s["op"] if len(s["terms"]) > 1 else "one", sorted(map(tuple, s["terms"]))])
    if n == "inclusion_exclusion":
        if s["triple"] is None:
            return J([s["total"], sorted(s["sizes"]), s["pairs"], s["ask"]])
        A = s["sizes"]
        P = {frozenset((0, 1)): s["pairs"][0], frozenset((0, 2)): s["pairs"][1], frozenset((1, 2)): s["pairs"][2]}
        best = min((tuple(A[p[i]] for i in range(3)), tuple(P[frozenset((p[i], p[j]))] for i, j in ((0, 1), (0, 2), (1, 2)))) for p in itertools.permutations(range(3)))
        return J([s["total"], best, s["triple"], s["ask"]])
    if n == "binomial_choose":
        if s["shape"] == "two_groups":
            return J(["two", sorted([(s["x"], s["j"]), (s["y"], s["k"] - s["j"])])])
        return J([s["shape"], s["n"], s["k"]])
    if n == "pigeonhole_worst_case":
        return J([sorted(s["counts"]), s["goal"], s["k"]])
    if n == "median_list":
        return J(sorted(s["values"]))
    if n == "mode_tally":
        return J([sorted(s["values"]), s["ask"]])
    if n == "digit_puzzle":
        return J([s["digits"], sorted(J(c) for c in s["clues"])])
    if n == "pythagoras":
        a, b = s["legs"]
        if s["shape"] in ("walk", "diagonal"):
            return J(["hyp", sorted([a, b])])
        if s["shape"] == "perimeter":
            return J(["per", sorted([a, b])])
        return J(["leg", s["given"]])  # given = [hyp, known leg] for both ladder shapes
    if n == "grid_perimeter":
        cells = [(y, x) for y, rr in enumerate(s["rows"]) for a, b in rr for x in range(a, b + 1)]
        best = None
        for sy, sx, tr in itertools.product((1, -1), (1, -1), (0, 1)):
            pts = [(sy * y, sx * x) for y, x in cells]
            if tr:
                pts = [(x, y) for y, x in pts]
            my, mx = min(p[0] for p in pts), min(p[1] for p in pts)
            k = tuple(sorted((p[0] - my, p[1] - mx) for p in pts))
            best = k if best is None or k < best else best
        return J(best)
    if n == "painted_cube":
        a, b, c = s["dims"]
        d = sorted([a, b, c]) if not s["bottom_unpainted"] else sorted([a, b]) + [c]
        return J([d, s["bottom_unpainted"], s["faces"]])
    s2 = dict(s)
    s2.pop("item", None)
    s2.pop("sets", None)
    return J(s2)


def one(args):
    lid, lv, M = args
    lin = current_set(True)[lid]
    n = lid.split(".")[1].removesuffix("_r2")
    t0 = time.time()
    cnt = Counter(key(n, it.structured) for it in items(lin, lv, M, SEED, "cap"))
    P = sum(c * (c - 1) // 2 for c in cnt.values())
    f = Counter(cnt.values())
    f1, f2 = f.get(1, 0), f.get(2, 0)
    D = len(cnt)
    chao = D + (f1 * f1 / (2 * f2) if f2 else f1 * (f1 - 1) / 2)
    return lid, lv, {"M": M, "D": D, "pairs": P, "n_eff": (M * (M - 1) / (2 * P)) if P else None, "f1": f1, "f2": f2, "chao1": round(chao), "sec": round(time.time() - t0, 1)}


if __name__ == "__main__":
    M, path = int(sys.argv[1]), sys.argv[2]
    ids = sorted(current_set(True))
    tasks = [(i, lv, M) for i in ids for lv in ALL_LEVELS]
    tasks.sort(key=lambda t: (not t[0].endswith(("painted_cube_r2", "crt_congruence_r2")), -t[1]))  # slow ones first
    with get_context("spawn").Pool(8) as p:
        res = p.map(one, tasks, chunksize=1)
    out = {}
    for lid, lv, r in res:
        out.setdefault(lid, {})[str(lv)] = r
    json.dump(out, open(path, "w"), indent=1, sort_keys=True)
    for lid in ids:
        print(lid, " ".join(f"L{lv}:D={out[lid][str(lv)]['D']},ne={out[lid][str(lv)]['n_eff'] and round(out[lid][str(lv)]['n_eff'])},c1={out[lid][str(lv)]['chao1']}" for lv in ALL_LEVELS))
