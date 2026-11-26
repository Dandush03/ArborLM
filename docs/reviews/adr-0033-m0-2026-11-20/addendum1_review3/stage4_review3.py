"""Review 3: section 4A stage 4 (capacity fixed point) implemented from the text, and the claim
'the result does not depend on the order ... it is the largest set of lineages that meets its own demand'.

(1) The drafter's part-4 example (made-up capacities on V1; partition of V1 as computed by my own
    partition_from_text_review3.py) is recomputed with the cluster-level condition included
    (union = sum of lineage counts, i.e. no collisions between lineages).
(2) Random small instances, counts independent of the other lineages: fixed point == largest
    self-consistent set (brute force).
(3) Random small instances where a lineage's count depends on which other lineages are in S (as when
    one used-text set is shared across lineages during generation, section 10 part B item 6):
    search for a self-consistent set not contained in the fixed point.
Standard library only.  Seeded: random.Random(20261126).
"""

import itertools
import math
import random

c = math.ceil


def D(G):
    return 10 * (c(4000 / G) + c(20000 / G) + 100)


def Dlin(G, k):
    return 10 * (c(c(4000 / G) / k) + c(c(20000 / G) / k) + c(100 / k))


def ok_set(S, cl, supply):
    """Every lineage of S meets its own demand in S (both conditions)."""
    G = len({cl[x] for x in S})
    for x in S:
        k = sum(1 for y in S if cl[y] == cl[x])
        if supply(x, S) < Dlin(G, k):
            return False
        if sum(supply(y, S) for y in S if cl[y] == cl[x]) < D(G):
            return False
    return True


def fixed_point(S0, cl, supply, trace=None):
    S = set(S0)
    while True:
        if not S:
            if trace is not None:
                trace.append((0, []))
            return S
        G = len({cl[x] for x in S})
        fail = set()
        for x in S:
            k = sum(1 for y in S if cl[y] == cl[x])
            if supply(x, S) < Dlin(G, k):
                fail.add(x)
        for cid in {cl[x] for x in S}:
            mem = [y for y in S if cl[y] == cid]
            if sum(supply(y, S) for y in mem) < D(G):
                fail |= set(mem)
        if trace is not None:
            trace.append((G, sorted(fail)))
        if not fail:
            return S
        S -= fail


# (1) drafter's example, V1 parts from my partition output
PART_A = {"C1.alpha", "C1.beta", "C1.epsilon", "M1.delta", "M1.gamma", "R1.alpha"}
CL = {"R1.alpha": "R1.alpha", "R1.beta": "R1.alpha", "R1.gamma": "R1.delta", "R1.epsilon": "C1.epsilon",
      "R1.zeta": "R1.zeta", "R2.alpha": "C1.alpha", "R2.beta": "C1.beta", "R2.gamma": "M1.alpha",
      "R2.delta": "R2.delta", "R2.epsilon": "R2.epsilon", "M1.alpha": "M1.alpha", "M1.beta": "C1.gamma",
      "M1.gamma": "M1.gamma", "M1.delta": "M1.delta", "C1.alpha": "C1.alpha", "C1.beta": "C1.beta",
      "C1.gamma": "C1.gamma", "C1.delta": "C1.delta"}
CAP = {"R1.alpha": 70_000, "R1.beta": 9_000, "R1.gamma": 300_000, "R1.epsilon": 300_000, "R1.zeta": 300_000,
       "R2.alpha": 300_000, "R2.beta": 300_000, "R2.gamma": 90_000, "R2.delta": 50_000, "R2.epsilon": 300_000,
       "M1.alpha": 300_000, "M1.beta": 300_000, "M1.gamma": 300_000, "M1.delta": 300_000,
       "C1.alpha": 300_000, "C1.beta": 300_000, "C1.gamma": 130_000, "C1.delta": 100}
print("== (1) drafter's part-4 example, cluster condition included")
for e in ("R1", "R2", "M1", "C1"):
    for p in ("A", "B"):
        S0 = {x for x in CL if x.startswith(e + ".") and (CL[x] in PART_A) == (p == "A")}
        tr = []
        S = fixed_point(S0, CL, lambda x, S: CAP[x], tr)
        print(f"  {e} {p}: start G={len({CL[x] for x in S0})} -> G={len({CL[x] for x in S})}; rounds {tr}")

rng = random.Random(20261126)


def brute_max(S0, cl, supply):
    best = set()
    for r in range(len(S0), 0, -1):
        for T in itertools.combinations(sorted(S0), r):
            if ok_set(set(T), cl, supply):
                return set(T)
    return best


def all_consistent(S0, cl, supply):
    out = []
    for r in range(1, len(S0) + 1):
        for T in itertools.combinations(sorted(S0), r):
            if ok_set(set(T), cl, supply):
                out.append(set(T))
    return out


print("== (2) independent counts: fixed point vs brute-force largest consistent set")
mism = 0
for trial in range(1500):
    n = rng.randint(1, 7)
    S0 = [f"x{i}" for i in range(n)]
    cl = {x: f"c{rng.randint(0, 3)}" for x in S0}
    cap = {x: rng.choice([20_000, 30_000, 45_000, 65_000, 90_000, 130_000, 250_000]) for x in S0}
    sup = lambda x, S, cap=cap: cap[x]
    fp = fixed_point(S0, cl, sup)
    cons = all_consistent(S0, cl, sup)
    union = set().union(*cons) if cons else set()
    if fp != union or any(not T <= fp for T in cons):
        mism += 1
print(f"  1500 instances: mismatches {mism}")

print("== (3) counts that depend on the other lineages in S (shared used-text set)")
found = 0
example = None
for trial in range(4000):
    n = rng.randint(2, 5)
    S0 = [f"x{i}" for i in range(n)]
    cl = {x: f"c{rng.randint(0, 2)}" for x in S0}
    base = {x: rng.choice([40_000, 60_000, 80_000, 100_000, 125_000, 150_000, 250_000]) for x in S0}
    ov = {(a, b): rng.choice([0, 0, 20_000, 40_000, 60_000]) for a in S0 for b in S0 if a < b}

    def sup(x, S, base=base, ov=ov):
        # generation in id order with one shared used set: x loses the texts already taken by earlier members of S
        return base[x] - sum(ov[(y, x)] for y in S if y < x)

    fp = fixed_point(S0, cl, sup)
    cons = all_consistent(S0, cl, sup)
    out = [T for T in cons if not T <= fp]
    if out:
        found += 1
        if example is None:
            example = (cl, base, {k: v for k, v in ov.items() if v}, fp, out[0])
print(f"  4000 instances: {found} with a self-consistent set not contained in the fixed point")
if example:
    cl, base, ov, fp, T = example
    print("  first example: clusters", cl, "base", base, "overlaps", ov)
    print("    fixed point", sorted(fp), "; a consistent set outside it", sorted(T))
