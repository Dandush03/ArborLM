# ruff: noqa
"""Auditor's structural capacity count for the 21 M1 batch-1 lineages, all 7 levels (own code).

Three counts of distinct items among M draws per level from the frozen generator (auditor seed 777005):
  text   = distinct normalised question text (NFKC, casefold, whitespace) -- what the code's gate counts;
  struct = distinct structural content: every number and the question type, with names, towns, the one-sentence setting,
           activity/colour/object words removed (least favourable reading of "distinct item": a name or setting change is NOT a new item);
  canon  = struct with presentational order also removed (sorted where the order of the statement does not change the problem; grids translated
           to column 1; painted-cube length/width interchangeable) -- the lead's "order is a parameter" applied to capacity.
Saturation: the same counts on the first half of the draws; if struct(M/2) is close to struct(M), the space is (nearly) exhausted.
Exact enumerations (no sampling) are added for binomial_choose, prime_factors and pythagoras.

Demand (studies/m0/lineage_gates.py constants, read, not imported): core level 10 x (ceil(24000/G) + 100), reserve level 10 x 100.

Run from the audited worktree:
  PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PYTHONPATH=. uv run --locked --offline python <this> [M] > capacity_out.txt
"""
import json
import math
import re
import sys
import unicodedata
from pathlib import Path

from studies.m0.core import ALL_LEVELS, build_item, stream
from studies.m0.lineages_m1_common import load_batch

M = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
SKIP = set(sys.argv[2].split(",")) if len(sys.argv) > 2 else set()  # v2: skip lineages already counted by the first (slow) run
SEED = 777005


def norm(t):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", t).casefold()).strip()


def J(x):
    return json.dumps(x, sort_keys=True)


def struct_key(lid, s):
    s = dict(s)
    for k in ("sets", "item"):
        s.pop(k, None)
    return J(s)


def ie_canon(s):
    if s["triple"] is None:
        return J([s["total"], sorted(s["sizes"]), s["pairs"], s["ask"]])
    import itertools
    A = s["sizes"]; P = {(0, 1): s["pairs"][0], (0, 2): s["pairs"][1], (1, 2): s["pairs"][2]}
    best = None
    for perm in itertools.permutations(range(3)):
        sz = [A[perm[i]] for i in range(3)]
        pr = [P[tuple(sorted((perm[i], perm[j])))] for i, j in ((0, 1), (0, 2), (1, 2))]
        cand = (sz, pr)
        best = cand if best is None or cand < best else best
    return J([s["total"], best, s["triple"], s["ask"]])


def canon_key(lid, s):
    n = lid.split(".")[1]
    if n == "inclusion_exclusion":
        return ie_canon(s)
    if n == "pigeonhole_worst_case":
        return J([sorted(s["counts"]), s["goal"], s["k"]])
    if n == "gcd_lcm":
        return J([s["ask"], sorted(s["values"])])
    if n == "crt_congruence":
        return J(sorted(s["conditions"]))
    if n == "last_digit_power":
        return J([s["op"], sorted(s["terms"])])
    if n == "digit_puzzle":
        return J([s["digits"], sorted(J(c) for c in s["clues"])])
    if n == "pythagoras":
        if s["shape"] in ("walk", "diagonal", "perimeter"):
            return J([s["shape"], sorted(s["legs"]), s["hyp"]])
        return J([s["shape"], s["given"]])
    if n == "grid_perimeter":
        m = min(a for a, _ in s["rows"])
        rows = [[a - m + 1, b - m + 1] for a, b in s["rows"]]
        hi = max(b for _, b in rows)
        mirror = [[hi - b + 1, hi - a + 1] for a, b in rows]
        flips = [rows, mirror, rows[::-1], mirror[::-1]]
        return J(min(flips))
    if n == "painted_cube":
        a, b, c = s["dims"]
        dims = sorted([a, b, c]) if not s["bottom_unpainted"] else sorted([a, b]) + [c]
        return J([dims, s["bottom_unpainted"], s["faces"]])
    if n == "median_list":
        if s["shape"] == "list":
            return J(["v", sorted(s["values"])])
        return J(["v", sorted(v for v, c in s["values"] for _ in range(c))])  # a table is the same multiset as a list
    if n == "mode_tally":
        return J([sorted(s["values"]), s["ask"]])
    return struct_key(lid, s)


def demand(level, G):
    return 100 if level in (0, 6) else math.ceil(24000 / G) + 100


def exact_binomial(level):
    top = 12 + 2 * level
    out = set()
    for n in range(7, top + 1):
        for k in range(3, n - 2):
            if 10 <= math.comb(n, k) <= 3_000_000:
                out.add(("plain", n, k))
            if 10 <= math.comb(n - 1, k - 1) <= 3_000_000:
                out.add(("include", n, k))
    for x in range(3, top - 1):
        for y in range(3, top - 1):
            for k in range(3, min(x + y - 2, 3 + level) + 1):
                for j in range(max(1, k - y), min(x, k - 1) + 1):
                    if 10 <= math.comb(x, j) * math.comb(y, k - j) <= 3_000_000:
                        out.add(("two", x, y, k, j))
    return len(out)


def exact_prime_factors(level):
    import itertools
    P = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29)
    npr_opts = (2, 3) if level < 3 else (3, 4) if level < 5 else (3, 4, 5)
    pool = P[: min(10, 7 + level // 2)]
    ns = set()
    for npr in npr_opts:
        for ps in itertools.combinations(pool, npr):
            ranges = [range(1, 2 + level // 2 + (1 if p == 2 else 0) + 1) for p in ps]
            for es in itertools.product(*ranges):
                n = math.prod(p**e for p, e in zip(ps, es))
                if 12 <= n <= 3000 * 3**level:
                    ns.add(n)
    return len(ns), 4 * len(ns)


def exact_pythagoras(level):
    limit = 60 + 80 * level
    T = []
    for a in range(3, 600):
        for b in range(a + 1, 600):
            c2 = a * a + b * b; c = math.isqrt(c2)
            if c * c == c2 and c <= 600 and c <= limit:
                T.append((a, b, c))
    keys, canon = set(), set()
    for a, b, c in T:
        for (x, y) in ((a, b), (b, a)):
            for sh in ("ladder_top", "ladder_base", "walk", "diagonal", "perimeter"):
                keys.add((sh, x, y, c))
                canon.add((sh, x, y, c) if sh.startswith("ladder") else (sh, min(x, y), max(x, y), c))
    return len(T), len(keys), len(canon)


def main():
    res = {}
    for lin in [x for x in load_batch() if x.id not in SKIP]:
        rec = {}
        for lv in ALL_LEVELS:
            rng = stream(SEED, "audit-capacity", lin.id, str(lv))
            T, S, C = set(), set(), set()
            half = None
            for i in range(M):
                it = build_item(lin, lv, rng, "A", "cap")
                T.add(norm(it.question)); S.add(struct_key(lin.id, it.structured)); C.add(canon_key(lin.id, it.structured))
                if i == M // 2 - 1:
                    half = (len(T), len(S), len(C))
            rec[lv] = {"M": M, "text": len(T), "struct": len(S), "canon": len(C), "half": half}
        res[lin.id] = rec
        print(lin.id, " ".join(f"L{lv}:{r['text']}/{r['struct']}/{r['canon']}(h{r['half'][1]}/{r['half'][2]})" for lv, r in rec.items()), flush=True)
    ex = {"binomial_choose": {lv: exact_binomial(lv) for lv in ALL_LEVELS},
          "prime_factors": {lv: exact_prime_factors(lv) for lv in ALL_LEVELS},
          "pythagoras": {lv: exact_pythagoras(lv) for lv in ALL_LEVELS}}
    print("EXACT binomial_choose structural forms per level:", ex["binomial_choose"])
    print("EXACT prime_factors (distinct N, N x 4 asks) per level:", ex["prime_factors"])
    print("EXACT pythagoras (triples, shape x order forms, order-canonical forms) per level:", ex["pythagoras"])
    Path(Path(__file__).resolve().parent / f"capacity_out_v2_M{M}.json").write_text(json.dumps({"sampled": res, "exact": {k: {str(a): b for a, b in v.items()} for k, v in ex.items()}}, indent=1))


if __name__ == "__main__":
    main()
