# ruff: noqa
"""Audit 4 of M1: EXACT support and EXACT n_eff (1 / sum p^2 over distinct structural items) by enumerating the builders' draw distributions, written from the builders'
parameter ranges by the auditor (no import of the implementer's exact_support or canon_key). Standard library only (no generator import), so it is an
independent derivation of the space; it is cross-checked against the sampled n_eff of capacity_a4.py.
Canonical items follow capacity_a4.key (commutative order, names, setting not distinct). For fraction_remainder both readings are given: (a, b) ordered
(the two spends in the printed order) and {a, b} unordered.
Usage: python3 exact_a4.py"""
import itertools
import math
from collections import defaultdict


def neff(p):
    s = sum(v * v for v in p.values())
    return round(1 / s), len(p)


def rectangle(L):
    W = list(range(2, 61 + 10 * L))
    p = defaultdict(float)
    for w in W:
        for k in range(2, 13):
            p[("r", 2 * (w + k * w), k)] += 0.3 / len(W) / 11
        for d in range(1, 61):
            p[("e", 2 * (2 * w + d), d)] += 0.7 / len(W) / 60
    return p


def fraction_remainder(L, ordered):
    p = defaultdict(float)
    for a in range(2, 13):
        for b in range(2, 13):
            step = a * (b // math.gcd(b, a - 1))
            m = (3000 + 500 * L) // step
            for j in range(1, m + 1):
                key = (step * j, a, b) if ordered else (step * j, min(a, b), max(a, b))
                p[key] += 1 / 121 / m
    return p


def tip_split(L):
    p = defaultdict(float)
    ns = list(range(2, 7 + L))
    for n in ns:
        for tip in range(5, 31):
            step = n // math.gcd(n, 100 + tip)
            lo, hi = -(-20 // step), (400 + 100 * L) // step
            m = hi - lo + 1
            for j in range(lo, hi + 1):
                p[(step * j, tip, n)] += 1 / len(ns) / 26 / m
    return p


def percent_change(L):
    p = defaultdict(float)
    ups, downs = list(range(5, 81, 5)), list(range(5, 76, 5))
    if L >= 3:
        prices = [80 * i for i in range(1, 7 + L)]
        u3 = list(range(5, 61, 5))
        for pr in prices:
            for u in ups:
                for d in downs:
                    for v in u3:
                        p[(pr, tuple(sorted((u, v))), d)] += 1 / len(prices) / 16 / 15 / 12
    else:
        prices = [4 * i for i in range(3, 61 + 10 * L)]
        for pr in prices:
            for u in ups:
                for d in downs:
                    p[(pr, u, d)] += 1 / len(prices) / 16 / 15
    return p


def coins(L):
    vals = (1, 2, 5, 10, 20, 25, 50, 100, 200)
    pairs = [(lo, hi) for lo in vals for hi in vals if hi > lo and hi <= 10 * lo]
    cmax = 30 + 4 * L
    p = defaultdict(float)
    for lo, hi in pairs:
        nls = range(max(2, -(-hi // lo)), cmax + 1)
        for nl in nls:
            for nh in range(2, cmax + 1):
                for ask in ("lo", "hi"):
                    p[(lo, hi, nl + nh, nl * lo + nh * hi, ask)] += 1 / len(pairs) / len(nls) / (cmax - 1) / 2
    return p


def mixture(L):
    p = defaultdict(float)
    S = (5, 10, 20, 25, 50, 100)
    ps = list(range(1, 10)) if L >= 3 else [0]
    for s in S:
        for x in range(1, s):
            y = s - x
            for a in range(2, 31):
                for b in range(2, 31):
                    if b == a:
                        continue
                    for pk in ps:
                        p[(tuple(sorted([(x, a), (y, b)])), pk)] += 1 / 6 / (s - 1) / 29 / 28 / len(ps)
    return p


def slot_permutations(L):
    RF = {"any": lambda d: True, "not0": lambda d: d != 0, "odd": lambda d: d % 2 == 1, "even": lambda d: d % 2 == 0, "ge5": lambda d: d >= 5, "lt5": lambda d: d < 5}
    RL = {"odd": lambda d: d % 2 == 1, "even": lambda d: d % 2 == 0, "ge5": lambda d: d >= 5, "lt5": lambda d: d < 5}
    subsets = [c for n in range(4, 10) for c in itertools.combinations(range(10), n)]
    s_hi = 3 + (L + 1) // 3 + (L >= 5)
    raw = defaultdict(float)
    for dg in subsets:
        for s0 in range(3, s_hi + 1):
            s = min(s0, len(dg))
            for rep in (False, True):
                firsts = ["any", "not0", "odd", "even", "ge5", "lt5"] if 0 in dg else ["any", "odd", "even", "ge5", "lt5"]
                for f in firsts:
                    for la in RL:
                        nf = sum(1 for d in dg if RF[f](d))
                        npl = sum(1 for d in dg if RL[la](d))
                        both = sum(1 for d in dg if RF[f](d) and RL[la](d))
                        cnt = nf * npl * len(dg) ** (s - 2) if rep else (nf * npl - both) * math.perm(len(dg) - 2, s - 2)
                        if cnt > 0:
                            raw[(dg, s, rep, f, la)] += 1 / len(subsets) / (s_hi - 2) / 2 / len(firsts) / 4
    tot = sum(raw.values())
    return {k: v / tot for k, v in raw.items()}


def gcd_lcm(L):
    k = 2 if L < 3 else (3 if L < 5 else 4)
    top, gmax = {2: (50, 40), 3: (30, 24), 4: (24, 24)}[k]
    sets = [c for c in itertools.combinations(range(2, top + 1), k) if all(math.gcd(a, b) == 1 for a, b in itertools.combinations(c, 2))]
    n = 2 * (gmax - 1) * len(sets)
    return n, n  # uniform: n_eff == support


def prime_factors(L):
    P = [p for p in range(2, 98) if all(p % q for q in range(2, int(p ** 0.5) + 1))]
    nmax = (30000, 50000, 100000, 200000, 400000, 800000, 1600000)[L]
    cnt = 0

    def rec(i, n, kd):
        nonlocal cnt
        if i == len(P):
            if kd >= 2 and n >= 12:
                cnt += 1
            return
        rec(i + 1, n, kd)
        m = n * P[i]
        while m <= nmax:
            rec(i + 1, m, kd + 1)
            m *= P[i]
    rec(0, 1, 0)
    return 4 * cnt, 4 * cnt


def binomial_choose(L):
    g = 2 if L < 3 else 3
    cap = 10 ** (4 + L)
    xs = list(range(3, 15 + 2 * L))
    opts = []
    for x in xs:
        js = list(range(1, min(x, 3 + L // 2) + 1))
        for j in js:
            opts.append(((x, j), 1 / len(xs) / len(js)))
    raw = defaultdict(float)
    for combo in itertools.product(opts, repeat=g):
        if math.prod(math.comb(x, j) for (x, j), _ in combo) <= cap:
            raw[tuple(sorted(c for c, _ in combo))] += math.prod(w for _, w in combo)
    tot = sum(raw.values())
    return {k: v / tot for k, v in raw.items()}


def pythagoras_triangles(limit):
    n, m = 0, 2
    while m * m + 1 <= limit:
        for k in range(1, m):
            if (m - k) % 2 and math.gcd(m, k) == 1 and m * m + k * k <= limit:
                n += limit // (m * m + k * k)
        m += 1
    return n


if __name__ == "__main__":
    rows = {}
    for L in range(7):
        r = {}
        r["rectangle"] = neff(rectangle(L))
        r["fraction_remainder_ordered"] = neff(fraction_remainder(L, True))
        r["fraction_remainder_unordered"] = neff(fraction_remainder(L, False))
        r["tip_split"] = neff(tip_split(L))
        r["percent_change"] = neff(percent_change(L))
        r["coins"] = neff(coins(L))
        r["mixture"] = neff(mixture(L))
        r["consecutive"] = ((4201 + 2000 * L) * (2 if L >= 2 else 1) * 2,) * 2
        r["ages"] = ((68 + 10 * L) * (5 + L // 2) * (15 + L) * 2,) * 2
        r["arithmetic_series"] = (99 * 30 * (12 + 3 * L - 3),) * 2
        r["finite_differences"] = ((61 * 26 * 15 * 2) if L < 5 else (61 * 21 * 10 * 4 * 2),) * 2
        r["gcd_lcm"] = gcd_lcm(L)
        r["prime_factors"] = prime_factors(L)
        r["slot_permutations"] = neff(slot_permutations(L))
        r["binomial_choose (NR)"] = neff(binomial_choose(L))
        rows[L] = r
    print("lineage: (exact n_eff, exact support) per level L0..L6")
    for name in rows[0]:
        print(f"{name:30s}", " ".join(f"{rows[L][name][0]}/{rows[L][name][1]}" for L in range(7)))
    print("pythagoras (NR): integer right triangles with hypotenuse <= 400, 2000, 3200:", [pythagoras_triangles(h) for h in (400, 2000, 3200)])
