# ruff: noqa
"""Independent check 4 of ADR-0033 addendum 1 draft 4: section 6 (G = 2 to 5, CR1 / CR0) and section 4A stage 4
(capacity slack, knife-edge, monotonicity proviso). Auditor's own code, standard library only.

Power model (as section 6 states it): cluster means of the paired difference are normal; the mean over G clusters has
variance tau^2/G + d/n with d = 0.3, n = 20,000; the test is one-sided at 0.95 with the t quantile on G - 1 df;
CR1 uses the sample SD of the cluster means (divisor G - 1), CR0 the divisor G, i.e. the critical value is scaled by
sqrt((G - 1)/G). Per-test target 1 - 0.2/55. Method (different from the drafter's chi-integration): integrate over the
normal variable, P(T > c) = int phi(z) F_chi2_df(df (z + ncp)^2 / c^2) 1{z + ncp > 0} dz, with closed-form chi-square
CDFs for integer df, composite Simpson.
Run: uv run --locked python -I -B <this file>
"""
from __future__ import annotations

import math
from statistics import NormalDist

N = NormalDist()
D, POOL, DEV, TUN = 0.3, 20_000, 4_000, 100
TARGET = 1 - 0.2 / 55
GRID = (0.02, 0.03, 0.05)


def chi2_cdf(x: float, k: int) -> float:
    if x <= 0:
        return 0.0
    h = x / 2
    if k % 2 == 0:
        s, term = 0.0, 1.0
        for j in range(k // 2):
            if j:
                term *= h / j
            s += term
        return 1 - math.exp(-h) * s
    # odd k: P = erf(sqrt(h)) - exp(-h) * sum_{j=1}^{(k-1)/2} h^{j-1/2} / Gamma(j + 1/2)
    s = 0.0
    for j in range(1, (k - 1) // 2 + 1):
        s += math.exp((j - 0.5) * math.log(h) - math.lgamma(j + 0.5))
    return math.erf(math.sqrt(h)) - math.exp(-h) * s


def t_sf(c: float, df: int, ncp: float, steps: int = 4000) -> float:
    lo, hi = -ncp, -ncp + 40.0
    lo = max(lo, -12.0)
    hi = min(hi, 12.0)
    if hi <= lo:
        return 0.0
    hstep = (hi - lo) / steps
    tot = 0.0
    for i in range(steps + 1):
        z = lo + i * hstep
        wgt = 1 if i in (0, steps) else (4 if i % 2 else 2)
        y = z + ncp
        f = chi2_cdf(df * y * y / (c * c), df) if y > 0 else 0.0
        tot += wgt * math.exp(-z * z / 2) / math.sqrt(2 * math.pi) * f
    return tot * hstep / 3


def tq(df: int) -> float:
    lo, hi = 0.0, 100.0
    for _ in range(70):
        m = (lo + hi) / 2
        if t_sf(m, df, 0.0) > 0.05:
            lo = m
        else:
            hi = m
    return (lo + hi) / 2


TQ = {}


def power(delta, g, tau, form):
    if g not in TQ:
        TQ[g] = tq(g - 1)
    c = TQ[g] * (math.sqrt((g - 1) / g) if form == "CR0" else 1.0)
    return t_sf(c, g - 1, delta / math.sqrt(tau * tau / g + D / POOL))


def tau_max(delta, g, form):
    if power(delta, g, 0.0, form) < TARGET:
        return None
    lo, hi = 0.0, 0.2
    for _ in range(36):
        m = (lo + hi) / 2
        if power(delta, g, m, form) >= TARGET:
            lo = m
        else:
            hi = m
    return lo


def delta_min(g, tau, form):
    lo, hi = 0.0, 5.0
    for _ in range(40):
        m = (lo + hi) / 2
        if power(m, g, tau, form) >= TARGET:
            hi = m
        else:
            lo = m
    return hi


def f(x):
    return "none" if x is None else f"{x:.4f}"


def section6():
    print(f"== 1. section 6, target {TARGET:.5f}")
    print("   t quantiles 0.95: " + "; ".join(f"df={k}: {tq(k):.4f}" for k in (1, 2, 3, 4, 5)))
    zz = N.inv_cdf(0.95) + N.inv_cdf(TARGET)
    print(f"   (a) floor: largest tau = delta sqrt(G) / {zz:.4f}")
    for dl in GRID:
        print(f"     delta {dl}: " + "; ".join(f"G={g}: {dl * math.sqrt(g) / zz:.3f}" for g in (2, 3, 4, 5, 8, 10, 13, 19)))
    gs = (2, 3, 4, 5, 6, 8, 10, 13, 19)
    print("   power at tau = 0, CR1 / CR0")
    for dl in GRID:
        print(f"     delta {dl}: " + "; ".join(f"G={g}: {power(dl, g, 0, 'CR1'):.4f}/{power(dl, g, 0, 'CR0'):.4f}" for g in gs))
    print("   (b) largest tau at which delta is reachable, CR1 / CR0")
    tm = {}
    for dl in GRID:
        cells = []
        for g in gs:
            a, b = tau_max(dl, g, "CR1"), tau_max(dl, g, "CR0")
            tm[(dl, g)] = (a, b)
            cells.append(f"G={g}: {f(a)}/{f(b)}")
        print(f"     delta {dl}: " + "; ".join(cells))
    print("   CR0 - CR1 increment of table (b), per G (cells where both exist):")
    for g in (5, 8, 10, 13, 19):
        inc = [tm[(dl, g)][1] - tm[(dl, g)][0] for dl in GRID if tm[(dl, g)][0] is not None]
        print(f"     G={g}: {min(inc):.4f} to {max(inc):.4f}  (delta 0.02 at G=5: CR1 {f(tm[(0.02, 5)][0])}, CR0 {f(tm[(0.02, 5)][1])})")
    print("   (c) smallest delta reachable, CR1 (CR0)")
    for tau in (0.0, 0.03, 0.05, 0.10):
        print(f"     tau {tau:.2f}: " + "; ".join(f"G={g}: {delta_min(g, tau, 'CR1'):.3f} ({delta_min(g, tau, 'CR0'):.3f})" for g in (2, 3, 4, 5, 8, 10, 13, 19)))


def dG(g):
    return 10 * (math.ceil(DEV / g) + math.ceil(POOL / g) + TUN)


def dL(g, k):
    return 10 * (math.ceil(math.ceil(DEV / g) / k) + math.ceil(math.ceil(POOL / g) / k) + math.ceil(TUN / k))


def capacity():
    print("== 2. capacity: D(G), D_lin(G, k), slack k*D_lin - D")
    print("   D: " + "; ".join(f"{g}: {dG(g):,}" for g in (1, 2, 3, 4, 5, 8, 10, 11, 13, 14, 15, 19, 300)))
    print(f"   D_lin(10,2) = {dL(10, 2):,}; D_lin(13,3) = {dL(13, 3):,}")
    neg = [(g, k) for g in range(1, 401) for k in range(1, 21) if k * dL(g, k) < dG(g)]
    print(f"   (G, k), G 1..400, k 1..20, with k*D_lin < D: {neg}")
    for k in range(2, 9):
        z = [g for g in range(1, 41) if k * dL(g, k) == dG(g)]
        print(f"   k={k}: G in 1..40 with slack exactly 0: {z}")
    print("   slack at k=2,3,4 for G 1..10: " + "; ".join(f"G={g}: " + "/".join(str(k * dL(g, k) - dG(g)) for k in (2, 3, 4)) for g in range(1, 11)))


def draw(seq, target):
    """Section 4A stage 4 count on a made-up item sequence of keys (None = build_item gives up): stop at target keys,
    or when attempts exceed 40*target + 1000, or at a give-up."""
    keys, att = set(), 0
    for k in seq:
        if len(keys) >= target:
            break
        att += 1
        if att > 40 * target + 1000:
            break
        if k is None:
            break
        keys.add(k)
    return len(keys)


def proviso():
    print("== 3. the proviso of stage 4 ('a lineage that fails a target also fails every larger target')")
    # first 5,000 attempts cycle over 99 keys; after that every item is new
    seq = [i % 99 for i in range(5000)] + list(range(1000, 1000 + 200_000))
    c100, c200 = draw(seq, 100), draw(seq, 200)
    print(f"   made-up generator: count at target 100 = {c100} (fails), at target 200 = {c200} (passes)")
    print("   so the proviso can fail when the attempt budget binds (duplicates in a long run); stated in the text as unchecked")


def stage4_4b():
    print("== 4. stage 4 example 4b recomputed (made-up capacities of the drafter; weakest level only)")
    members = {"c1": ["c1.x", "c1.y"], "c2": ["c2.x", "c2.y"], "c3": ["c3.x"], "c4": ["c4.x"], "c5": ["c5.x"]}
    cap = {"c1.x": 300_000, "c1.y": 9_000, "c2.x": 300_000, "c2.y": 300_000, "c3.x": 300_000, "c4.x": 300_000, "c5.x": 300_000}
    shared = {frozenset(("c2.x", "c2.y")): 1}
    for reading in ("A23 (union only if all pass (i))", "simultaneous (review 3's reading)"):
        S = {c: list(v) for c, v in members.items()}
        trail = []
        while True:
            G = len(S)
            fail = set()
            for c, v in S.items():
                t = dL(G, len(v))
                bad = [x for x in v if min(cap[x], t) < t]
                fail |= set(bad)
                if bad and reading.startswith("A23"):
                    continue
                counts = {x: min(cap[x], t) for x in v}
                union = sum(counts.values()) - sum(n for p, n in shared.items() if p <= set(v))
                if union < dG(G):
                    fail |= set(v)
            trail.append((G, sorted(fail)))
            if not fail:
                break
            S = {c: [x for x in v if x not in fail] for c, v in S.items()}
            S = {c: v for c, v in S.items() if v}
        print(f"   {reading}: {trail} -> registered {sorted(x for v in S.values() for x in v)}")


if __name__ == "__main__":
    capacity()
    proviso()
    stage4_4b()
    section6()
