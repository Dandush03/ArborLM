# ruff: noqa
"""Arithmetic for ADR-0033 addendum 1, draft 4. Formulas only: no model output, no item, no score and no cluster map
is read. Standard library only. Imports nothing from studies/ and nothing from the other scripts.

Run:  uv run --locked python -I -B docs/reviews/adr-0033-m0-2026-11-20/addendum1_scripts/addendum1_rev4_arithmetic.py

Part A  the form of the standard error (review 3, G6). Exact per-test power of the t test on G - 1 degrees of freedom
        at n = 20,000, d = 0.3, normal cluster means (an idealisation of the registered simulation, not the
        simulation), under CR1 (sample standard deviation of the cluster means, divisor G - 1, over sqrt(G)) and
        under CR0 (divisor G; CR0 = CR1 x sqrt((G - 1) / G)). Power at tau = 0 and the largest tau at which each
        margin of the grid is reachable inside the pool, for G = 2, 3, 4, 5, 6, 8, 10, 13, 19.
Part B  G = 2, 3 and 4 (review 3, G11): the floor as written (normal quantiles), the smallest margin reachable inside
        the pool with the t test, and the t quantiles.
Part C  capacity at the counts of draft 4: D(G), D_lin(G, k), and the slack k x D_lin(G, k) - D(G), which is the
        number of keys two sibling lineages may share before the union condition of stage 4 fails (review 3, G2).
"""

from __future__ import annotations

import math
from statistics import NormalDist

N = NormalDist()
GRID = (0.02, 0.03, 0.05)
D = 0.30
POOL = 20_000
DEV = 4_000
TUNING = 100
M_TESTS = 55
TARGET = 1 - 0.2 / M_TESTS


def chi2_dens_u(u: float, k: int) -> float:
    """Density of U = sqrt(V), V ~ chi2_k (the substitution removes the singularity at 0 for k = 1)."""
    if u <= 0:
        return math.sqrt(2 / math.pi) if k == 1 else 0.0
    v = u * u
    return math.exp((k / 2 - 1) * math.log(v) - v / 2 - (k / 2) * math.log(2) - math.lgamma(k / 2)) * 2 * u


def expect_chi2(f, k: int, steps: int = 8000) -> float:
    top = math.sqrt(k + 14 * math.sqrt(2 * k) + 60)
    h = top / steps
    tot = 0.0
    for i in range(steps + 1):
        u = i * h
        w = 1 if i in (0, steps) else (4 if i % 2 else 2)
        tot += w * chi2_dens_u(u, k) * f(u * u)
    return tot * h / 3


def nct_sf(c: float, df: int, ncp: float) -> float:
    """P(T > c), T = (Z + ncp) / sqrt(V / df)."""
    return expect_chi2(lambda v: N.cdf(ncp - c * math.sqrt(v / df)), df)


def t_quantile(p: float, df: int) -> float:
    lo, hi = 0.0, 400.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if 1 - nct_sf(mid, df, 0.0) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


G_LIST = (2, 3, 4, 5, 6, 8, 10, 13, 19)
TQ = {g: t_quantile(0.95, g - 1) for g in G_LIST}


def power(delta: float, g: int, tau: float, form: str) -> float:
    se = math.sqrt(tau * tau / g + D / POOL)
    c = TQ[g] * (math.sqrt((g - 1) / g) if form == "CR0" else 1.0)
    return nct_sf(c, g - 1, delta / se)


def tau_crit(delta: float, g: int, form: str) -> float | None:
    if power(delta, g, 0.0, form) < TARGET:
        return None
    lo, hi = 0.0, 0.5
    for _ in range(50):
        mid = (lo + hi) / 2
        if power(delta, g, mid, form) >= TARGET:
            lo = mid
        else:
            hi = mid
    return lo


def min_delta(g: int, tau: float, form: str) -> float:
    lo, hi = 0.0, 20.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if power(mid, g, tau, form) >= TARGET:
            hi = mid
        else:
            lo = mid
    return hi


def fmt(x: float | None) -> str:
    return "none" if x is None else f"{x:.4f}"


def part_a() -> None:
    print(f"== A. CR1 against CR0. Per-test target 1 - 0.2/{M_TESTS} = {TARGET:.5f}; n = {POOL:,}; d = {D}")
    print("   power at tau = 0 (the clusters do not differ at all), CR1 / CR0; 'yes' = target met")
    for delta in GRID:
        cells = []
        for g in G_LIST:
            p1, p0 = power(delta, g, 0.0, "CR1"), power(delta, g, 0.0, "CR0")
            cells.append(f"G={g}: {p1:.4f} {'yes' if p1 >= TARGET else 'no'} / {p0:.4f} {'yes' if p0 >= TARGET else 'no'}")
        print(f"   delta {delta}: " + "; ".join(cells))
    print("   largest tau at which delta is reachable inside the pool, CR1 / CR0 ('none' = not at any tau)")
    for delta in GRID:
        cells = [f"G={g}: {fmt(tau_crit(delta, g, 'CR1'))} / {fmt(tau_crit(delta, g, 'CR0'))}" for g in G_LIST]
        print(f"   delta {delta}: " + "; ".join(cells))
    print("   at G = 5, delta = 0.02 (the case the choice of form decides):")
    for form in ("CR1", "CR0"):
        p = power(0.02, 5, 0.0, form)
        print(f"     {form}: power at tau = 0 is {p:.4f} against {TARGET:.4f}: "
              f"{'reachable for tau up to ' + fmt(tau_crit(0.02, 5, form)) if p >= TARGET else 'not reachable at any tau'}")
    print("   width of every t interval: CR0 / CR1 = sqrt((G-1)/G): "
          + "; ".join(f"G={g}: {math.sqrt((g - 1) / g):.3f}" for g in G_LIST))


def part_b() -> None:
    print("== B. G = 2, 3, 4")
    zz = N.inv_cdf(0.95) + N.inv_cdf(TARGET)
    print(f"   t quantile 0.95: " + "; ".join(f"df={g - 1}: {TQ[g]:.3f}" for g in (2, 3, 4, 5)) + f"; normal: {N.inv_cdf(0.95):.3f}")
    print(f"   (a) floor as written, largest tau = delta x sqrt(G) / {zz:.4f}")
    for delta in GRID:
        print(f"   delta {delta}: " + "; ".join(f"G={g}: {delta * math.sqrt(g) / zz:.3f}" for g in (2, 3, 4, 5)))
    print("   (c) smallest delta reachable inside the pool with the t test, CR1 (CR0)")
    for tau in (0.0, 0.03, 0.05, 0.10):
        print(f"   tau {tau:.2f}: " + "; ".join(
            f"G={g}: {min_delta(g, tau, 'CR1'):.3f} ({min_delta(g, tau, 'CR0'):.3f})" for g in (2, 3, 4, 5)))


def d_cluster(g: int) -> int:
    return 10 * (math.ceil(DEV / g) + math.ceil(POOL / g) + TUNING)


def d_lin(g: int, k: int) -> int:
    return 10 * (math.ceil(math.ceil(DEV / g) / k) + math.ceil(math.ceil(POOL / g) / k) + math.ceil(TUNING / k))


def part_c() -> None:
    print("== C. capacity: D(G) per cluster and level; D_lin(G, k) per lineage; slack k x D_lin - D")
    gs = (1, 2, 3, 4, 5, 8, 9, 10, 13, 19)
    print("   D(G): " + "; ".join(f"G={g}: {d_cluster(g):,}" for g in gs))
    for k in (2, 3, 4):
        print(f"   k={k}: " + "; ".join(f"G={g}: D_lin {d_lin(g, k):,}, slack {k * d_lin(g, k) - d_cluster(g):,}" for g in gs))
    zero = [(g, k) for g in range(1, 20) for k in (2, 3, 4) if k * d_lin(g, k) == d_cluster(g)]
    neg = [(g, k) for g in range(1, 40) for k in range(1, 8) if k * d_lin(g, k) < d_cluster(g)]
    print(f"   (G, k) with slack exactly 0, G = 1..19, k = 2..4: {zero}")
    print(f"   (G, k) with k x D_lin < D, G = 1..39, k = 1..7: {neg}")
    print("   attempt budget of core.draw_items as written, 40 x target + 1,000: "
          + "; ".join(f"target {t:,}: {40 * t + 1000:,}" for t in (d_cluster(2), d_cluster(5), d_cluster(8), d_lin(8, 2))))


if __name__ == "__main__":
    part_a()
    part_b()
    part_c()
