# ruff: noqa: E501
"""M1 fix round 3: structural capacity of the new revisions against the demand of rulings R-10 and R-11, per lineage, per cluster and level. No model involved; deterministic.

Distinct = a different STRUCTURAL item: every numeric parameter value counts; names, the setting sentence, object / activity / colour words, the order of commutative parts, and (stricter than rev2)
a change of setting that leaves the computation identical do not (``canon_key``). Demand (R-10, R-11): per cluster and level 10 x (ceil(4000 / G) + ceil(20000 / G) + 100), reserve levels included;
G = 11 (22 clusters in two parts) gives 22,830; G = 10 (21 or 20 clusters) gives 25,000.

Measures (all MEASURED on generator output unless stated): (a) ``n_eff`` of a lineage-level = M (M - 1) / (2 P), P the colliding pairs among M draws (the inverse collision probability, a LOWER BOUND on the
number of distinct items; a level with no collision is given M (M - 1) / 6, as the auditor did); (b) the cluster's n_eff of the equal-weight mixture of its lineages, L^2 / sum(1 / n_i) (the auditor's basis);
(c) the sum of Chao1 support estimates (the auditor's second basis); (d) the stricter equal-share test: every registered member must reach demand / L on its own (the pool builder's split inside a cluster is
not specified; this is the reading under which each member supplies 1 / L of the cluster's draws); (e) ANALYTICAL exact support (enumeration) where the space is small enough to enumerate, as a cross-check.

Run: PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.m1_fix3_gates --stage capacity --m 30000 --out <cap.json>
     PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.m1_fix3_gates --stage report --capacity <cap.json> [--out <report.json>]
     PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.m1_fix3_gates --stage exact --out <exact.json>
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import time
from collections import Counter
from pathlib import Path
from typing import Any

from studies.m0.core import ALL_LEVELS, build_item, stream

SEED = 410301  # a throwaway integer for these measurements; not a registered study seed
G_WRITTEN, G_ALT = 11, 10


def J(x: Any) -> str:
    return json.dumps(x, sort_keys=True)


def demand(g: int) -> int:
    return 10 * (math.ceil(4000 / g) + math.ceil(20000 / g) + 100)


def _ie_canon(s: dict[str, Any]) -> str:
    if s["triple"] is None:
        return J([s["total"], sorted(s["sizes"]), s["pairs"], s["ask"]])
    a = s["sizes"]
    p = {frozenset((0, 1)): s["pairs"][0], frozenset((0, 2)): s["pairs"][1], frozenset((1, 2)): s["pairs"][2]}
    best = min((tuple(a[q[i]] for i in range(3)), tuple(p[frozenset((q[i], q[j]))] for i, j in ((0, 1), (0, 2), (1, 2)))) for q in itertools.permutations(range(3)))
    return J([s["total"], best, s["triple"], s["ask"]])


def _grid_canon(rows: list[list[list[int]]]) -> str:
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


def canon_key(lid: str, s: dict[str, Any]) -> str:
    n = lid.split(".", 1)[1].removesuffix("_r3").removesuffix("_r2")
    if n == "shopping":
        return J([sorted(map(tuple, s["items"])), s["paid"]])
    if n == "speed_distance":
        return J([sorted(map(tuple, s["legs"])), s["average"]])
    if n == "mixture":
        return J([sorted([(s["x"], s["a"]), (s["y"], s["b"])]), s["packing"]])
    if n == "percent_change":
        return J([s["price"], sorted(map(tuple, s["steps"]))])
    if n == "ratio_share":
        return J([sorted(s["parts"]), s["parts"][s["who"]], s["total"]])
    if n == "linear_equation":
        return J(["two", sorted([(s["k"], s["m"]), (s["j"], s["n"])])]) if s["j"] else J(["one", s["k"], s["m"], s["n"]])
    if n == "average_missing":
        return J([sorted(s["scores"]), s["mean_cents"]])
    if n == "pipes_work":
        return J([sorted([s["a"], s["b"]]), s["drain"], s["volume"]])
    if n == "gcd_lcm":
        return J([s["ask"], sorted(s["values"])])
    if n == "crt_congruence":
        return J(sorted(map(tuple, s["conditions"])))
    if n == "last_digit_power":
        return J([s["modulus"], s["op"] if len(s["terms"]) > 1 else "one", sorted(map(tuple, s["terms"]))])
    if n == "inclusion_exclusion":
        return _ie_canon(s)
    if n == "binomial_choose":
        return J(sorted(map(tuple, s["groups"])))
    if n == "pigeonhole_worst_case":
        return J([sorted(s["counts"]), s["goal"], s["k"]])
    if n == "median_list":
        return J(sorted(s["values"]))
    if n == "mode_tally":
        return J([sorted(s["values"]), s["ask"]])
    if n == "digit_puzzle":
        return J([s["digits"], sorted(J(c) for c in s["clues"])])
    if n == "quadratic_area":
        if s["shape"] in ("rect_area", "product"):
            return J(["prod", s["d"], s["area"]])
        return J(["rp", s["perimeter"], s["area"]]) if s["shape"] == "rect_perimeter" else J(["sq", s["d"], s["total"]])
    if n == "pythagoras":
        a, b = s["legs"]
        if s["shape"] in ("walk", "diagonal"):
            return J(["hyp", sorted([a, b])])
        if s["shape"] == "perimeter":
            return J(["per", sorted([a, b])])
        return J(["leg", s["given"]])
    if n == "grid_perimeter":
        return _grid_canon(s["rows"])
    if n == "painted_cube":
        a, b, c = s["dims"]
        return J([sorted([a, b, c]) if not s["bottom_unpainted"] else sorted([a, b]) + [c], s["bottom_unpainted"], s["faces"]])
    s2 = dict(s)
    s2.pop("item", None)
    s2.pop("sets", None)
    return J(s2)


def _all_lineages() -> dict[str, Any]:
    from studies.m0.lineages_m1_fix3 import load_all

    return {x.id: x for x in load_all()}


def capacity_one(args: tuple[str, int, int]) -> tuple[str, int, dict[str, Any]]:
    lid, lv, m = args
    lin = _all_lineages()[lid]
    rng = stream(SEED, "fix3-capacity", lid, str(lv))
    t0 = time.time()
    cnt: Counter[str] = Counter(canon_key(lid, build_item(lin, lv, rng, "A", "cap").structured) for _ in range(m))
    pairs = sum(c * (c - 1) // 2 for c in cnt.values())
    f = Counter(cnt.values())
    f1, f2 = f.get(1, 0), f.get(2, 0)
    chao = len(cnt) + (f1 * f1 / (2 * f2) if f2 else f1 * (f1 - 1) / 2)
    return lid, lv, {"M": m, "D": len(cnt), "pairs": pairs, "n_eff": (m * (m - 1) / (2 * pairs)) if pairs else None, "f1": f1, "f2": f2, "chao1": round(chao), "sec": round(time.time() - t0, 1)}


def run_capacity(m: int, workers: int, only: list[str] | None = None, skip: list[str] | None = None) -> dict[str, Any]:
    import multiprocessing as mp

    ids = sorted(_all_lineages())
    if only:
        ids = [i for i in ids if any(o in i for o in only)]
    if skip:
        ids = [i for i in ids if not any(o in i for o in skip)]
    tasks = [(i, lv, m) for i in ids for lv in ALL_LEVELS]
    with mp.get_context("spawn").Pool(workers) as pool:
        res = pool.map(capacity_one, tasks, chunksize=1)
    out: dict[str, Any] = {}
    for lid, lv, r in res:
        out.setdefault(lid, {})[str(lv)] = r
    return {"m": m, "seed": SEED, "levels": out}


def ne(r: dict[str, Any]) -> float:
    return float(r["n_eff"] if r["n_eff"] is not None else r["M"] * (r["M"] - 1) / 6)


def evaluate(cap: dict[str, Any], not_registered: dict[str, str] | None = None) -> dict[str, Any]:
    from studies.m0.lineages_m1_fix3_clusters import strict_clusters

    nr = not_registered or {}
    lv = cap["levels"]
    reg = [i for i in sorted(lv) if i not in nr]
    clusters = strict_clusters(reg)
    rep: dict[str, Any] = {"demand": {f"G={g}": demand(g) for g in (G_WRITTEN, G_ALT)}, "m": cap["m"], "lineages": {}, "clusters": {}}
    for lid in sorted(lv):
        rep["lineages"][lid] = {"n_eff": {l_: round(ne(lv[lid][l_])) for l_ in lv[lid]}, "chao1": {l_: lv[lid][l_]["chao1"] for l_ in lv[lid]}, "not_registered": nr.get(lid)}
    for cl, members in clusters.items():
        row: dict[str, Any] = {"members": members, "levels": {}}
        for g in (G_WRITTEN, G_ALT):
            row[f"fails_G={g}"] = {"mixture": [], "chao1_sum": [], "equal_share": []}
        for level in ALL_LEVELS:
            rs = [lv[m_][str(level)] for m_ in members]
            mix = len(rs) ** 2 / sum(1 / ne(r) for r in rs)
            c1 = sum(r["chao1"] for r in rs)
            share_min = min(ne(r) for r in rs) * len(rs)  # smallest member's n_eff scaled to the cluster: member i supplies demand / L, so test n_i * L >= demand
            row["levels"][str(level)] = {"mixture_n_eff": round(mix), "chao1_sum": c1, "min_member_n_eff_times_L": round(share_min)}
            for g in (G_WRITTEN, G_ALT):
                d = demand(g)
                if mix < d:
                    row[f"fails_G={g}"]["mixture"].append(level)
                if c1 < d:
                    row[f"fails_G={g}"]["chao1_sum"].append(level)
                if share_min < d:
                    row[f"fails_G={g}"]["equal_share"].append(level)
        rep["clusters"][cl] = row
    return rep


# ------------------------------------------------------------------ exact enumeration (ANALYTICAL) where the space is small


def exact_support() -> dict[str, dict[str, int]]:
    """Exact number of distinct structural items by enumeration of the parameter space (not by sampling), for the lineages whose space is a product or a small search."""
    from studies.m0.lineages_m1_fix3_b import (
        _RULES_FIRST,
        _RULES_LAST,
        _SUBSETS,
        _smooth,
        slot_count,
    )

    out: dict[str, dict[str, int]] = {}
    for lv in ALL_LEVELS:
        d: dict[str, int] = {}
        d["rectangle"] = (59 + 10 * lv) * 11 + (59 + 10 * lv) * 60
        d["consecutive"] = (4201 + 2000 * lv) * (2 if lv >= 2 else 1) * 2
        d["ages"] = (68 + 10 * lv) * (5 + lv // 2) * (15 + lv) * 2
        n = 0
        for a in range(2, 13):
            for b in range(2, 13):
                step = a * (b // math.gcd(b, a - 1))
                n += (3000 + 500 * lv) // step
        d["fraction_remainder"] = n
        n = 0
        for people in range(2, 7 + lv):
            for tip in range(5, 31):
                step = people // math.gcd(people, 100 + tip)
                n += (400 + 100 * lv) // step - (-(-20 // step)) + 1
        d["tip_split"] = n
        d["arithmetic_series"] = 99 * 30 * (12 + 3 * lv - 3)
        vals = (1, 2, 5, 10, 20, 25, 50, 100, 200)
        cmax = 30 + 4 * lv
        n = 0
        for lo in vals:
            for hi in vals:
                if lo < hi <= 10 * lo:
                    n += (cmax - max(2, -(-hi // lo)) + 1) * (cmax - 1) * 2
        d["coins"] = n
        d["prime_factors"] = 4 * len(_smooth(lv))
        d["gcd_lcm"] = 2 * _gcd_sets(lv)
        d["finite_differences"] = (15 * 26 * 61 * 2) if lv < 5 else (61 * 21 * 10 * 4 * 2)
        d["quadratic_area_prod_class"] = (149 + 25 * lv) * (121 + 15 * lv)
        n = 0
        for digits in _SUBSETS:
            s_hi = 3 + (lv + 1) // 3 + (lv >= 5)
            for s in range(3, s_hi + 1):
                if s > len(digits):
                    continue
                for rep in (False, True):
                    firsts = [f for f in _RULES_FIRST if f != "not0" or 0 in digits]
                    for f in firsts:
                        for la in _RULES_LAST:
                            n += slot_count(list(digits), s, rep, f, la) > 0
        d["slot_permutations"] = n
        d["binomial_choose"] = _binom_support(lv)
        out[str(lv)] = d
    return out


def _gcd_sets(lv: int) -> int:
    k = 2 if lv < 3 else (3 if lv < 5 else 4)
    top, gmax = {2: (50, 40), 3: (30, 24), 4: (24, 24)}[k]
    n = sum(1 for c in itertools.combinations(range(2, top + 1), k) if all(math.gcd(a, b) == 1 for a, b in itertools.combinations(c, 2)))
    return n * (gmax - 1)


def _binom_support(lv: int) -> int:
    g = 2 if lv < 3 else 3
    cap = 10 ** (4 + lv)
    opts = [(x, j) for x in range(3, 15 + 2 * lv) for j in range(1, min(x, 3 + lv // 2) + 1)]
    seen = set()
    for combo in itertools.combinations_with_replacement(opts, g) if g == 2 else itertools.combinations_with_replacement(opts, g):
        if math.prod(math.comb(x, j) for x, j in combo) <= cap:
            seen.add(combo)
    return len(seen)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stage", choices=["capacity", "report", "exact"], required=True)
    ap.add_argument("--m", type=int, default=30000)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--only", default="")
    ap.add_argument("--skip", default="")
    ap.add_argument("--capacity", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    t0 = time.time()
    if a.stage == "capacity":
        res = run_capacity(a.m, a.workers, [x for x in a.only.split(",") if x] or None, [x for x in a.skip.split(",") if x] or None)
        if a.out:
            Path(a.out).write_text(json.dumps(res, indent=1, sort_keys=True))
        for lid, rows in sorted(res["levels"].items()):
            print(lid, " ".join(f"L{lv}:{round(ne(rows[str(lv)]))}" for lv in ALL_LEVELS), flush=True)
    elif a.stage == "report":
        from studies.m0.lineages_m1_fix3 import NOT_REGISTERED

        rep = evaluate(json.loads(Path(a.capacity).read_text()), NOT_REGISTERED)
        if a.out:
            Path(a.out).write_text(json.dumps(rep, indent=1, sort_keys=True))
        print("demand", rep["demand"])
        for cl, row in rep["clusters"].items():
            print(f"{cl:28s} mix {[row['levels'][str(lv)]['mixture_n_eff'] for lv in ALL_LEVELS]} fails G=11 {row['fails_G=11']}")
    else:
        res2 = exact_support()
        if a.out:
            Path(a.out).write_text(json.dumps(res2, indent=1, sort_keys=True))
        for name in sorted(res2["0"]):
            print(f"{name:28s}", [res2[str(lv)][name] for lv in ALL_LEVELS])
    print("seconds", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
