# ruff: noqa
"""Planning arithmetic for ADR-0033 addendum 1 (draft): what a small number of clusters G can reach.

Arithmetic from formulas only. No model output, no item, no score is read. Standard library only.
Run:  uv run --locked python -I docs/reviews/adr-0033-m0-2026-11-20/addendum1_scripts/power_small_g.py

Part 0 reproduces the table of ADR-0033 section 8 (review 2, power_check2.py part B) as a check of this script.
Part 1 uses the SAME normal formula at small G (the "floor from the clusters" of section 9.4, as written).
Part 2 uses the t quantile on G - 1 degrees of freedom that section 9.4's simulated test and section 9.2's
       small-sample rule prescribe (exact noncentral-t power for normal cluster means; an idealisation of the
       registered simulation, not the simulation itself).
Part 3 is the capacity demand of section 6.2 at the G written (worst-case reading of the implementation).
"""

from __future__ import annotations

import math
from statistics import NormalDist

N = NormalDist()
ZA = N.inv_cdf(0.95)
GRID = (0.02, 0.03, 0.05)
D = 0.30  # discordance used in section 8's arithmetic
POOL = 20_000
G_LIST = (8, 11, 13, 14, 15, 19, 27, 38)
TAUS = (0.0, 0.01, 0.02, 0.03, 0.05, 0.10, 0.15)


def target(m_total: int) -> float:
    return 1 - 0.2 / m_total


def z_boole(m_total: int) -> float:
    return ZA + N.inv_cdf(target(m_total))


# ---------- Student t and noncentral t, standard library only ----------
def _chi2_logpdf(v: float, k: int) -> float:
    return (k / 2 - 1) * math.log(v) - v / 2 - (k / 2) * math.log(2) - math.lgamma(k / 2)


def _expect_chi2(f, k: int, steps: int = 4000) -> float:
    """E[f(V)] for V ~ chi-square(k), Simpson's rule on a wide range."""
    lo = 1e-9
    hi = k + 14 * math.sqrt(2 * k) + 60
    h = (hi - lo) / steps
    tot = 0.0
    for i in range(steps + 1):
        v = lo + i * h
        w = 1 if i in (0, steps) else (4 if i % 2 else 2)
        tot += w * math.exp(_chi2_logpdf(v, k)) * f(v)
    return tot * h / 3


def nct_sf(c: float, df: int, ncp: float) -> float:
    """P(T > c) for T = (Z + ncp) / sqrt(V / df)."""
    return _expect_chi2(lambda v: N.cdf(ncp - c * math.sqrt(v / df)), df)


def t_quantile(p: float, df: int) -> float:
    lo, hi = 0.0, 50.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if 1 - nct_sf(mid, df, 0.0) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def t_power(delta: float, g: int, tau: float, n: float, d: float = D) -> float:
    """Per-test power of 'estimate - t_{0.95,G-1} SE > -delta' at a true difference of zero.

    G cluster means, each with variance tau^2 + d * G / n (n / G items per cluster, item variance d).
    """
    se = math.sqrt(tau**2 / g + (d / n if math.isfinite(n) else 0.0))
    if se == 0:
        return 1.0
    return nct_sf(t_quantile(0.95, g - 1), g - 1, delta / se)


def ncp_needed(g: int, tgt: float) -> float:
    c = t_quantile(0.95, g - 1)
    lo, hi = 0.0, 60.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if nct_sf(c, g - 1, mid) < tgt:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def part0() -> None:
    print("== 0. Check: section 8's table (Boole, 55 tests, d = 0.3): smallest delta at n = 20,000 / at any n")
    z = z_boole(55)
    for tau in (0.03, 0.05, 0.10, 0.15):
        row = [f"G={g}: {z * math.sqrt(D / POOL + tau**2 / g):.3f}/{z * tau / math.sqrt(g):.3f}" for g in (60, 150, 300, 600, 1200)]
        print(f"  tau={tau:.2f}  " + "  ".join(row))


def part1() -> None:
    for m in (55, 70):
        z = z_boole(m)
        print(f"== 1. Normal formula of sections 8 and 9.4 at small G; {m} tests; per-test target {target(m):.5f}; z sum {z:.3f}")
        print("   smallest delta reachable at n = 20,000 / at any n (d = 0.3)")
        for tau in TAUS:
            row = [f"G={g}: {z * math.sqrt(D / POOL + tau**2 / g):.3f}/{z * tau / math.sqrt(g):.3f}" for g in G_LIST]
            print(f"  tau={tau:.2f}  " + "  ".join(row))
        print("   largest tau at which the floor of section 9.4 is met at any n (tau <= delta sqrt(G) / z sum)")
        for delta in GRID:
            row = [f"G={g}: {delta * math.sqrt(g) / z:.4f}" for g in G_LIST]
            print(f"  delta={delta:.2f}  " + "  ".join(row))
        print("   largest tau at which delta is reached within the 20,000 pool (d = 0.3); '-' = not even at tau = 0")
        for delta in GRID:
            row = []
            for g in G_LIST:
                rem = (delta / z) ** 2 - D / POOL
                row.append(f"G={g}: {math.sqrt(rem * g):.4f}" if rem > 0 else f"G={g}: -")
            print(f"  delta={delta:.2f}  " + "  ".join(row))


def part2() -> None:
    for m in (55, 70):
        tgt = target(m)
        print(f"== 2. With the t quantile on G - 1 degrees of freedom (section 9.4's test, section 9.2's rule); {m} tests; target {tgt:.5f}")
        need = {g: ncp_needed(g, tgt) for g in G_LIST}
        print("   delta / SE needed: " + "  ".join(f"G={g}: {need[g]:.2f}" for g in G_LIST) + f"   (normal formula: {z_boole(m):.2f})")
        print("   largest tau at which delta is reachable at any n")
        for delta in GRID:
            print(f"  delta={delta:.2f}  " + "  ".join(f"G={g}: {delta * math.sqrt(g) / need[g]:.4f}" for g in G_LIST))
        for d in (0.10, 0.20, 0.30):
            print(f"   largest tau at which delta is reached within the 20,000 pool, d = {d:.2f}; '-' = not even at tau = 0")
            for delta in GRID:
                row = []
                for g in G_LIST:
                    rem = (delta / need[g]) ** 2 - d / POOL
                    row.append(f"G={g}: {math.sqrt(rem * g):.4f}" if rem > 0 else f"G={g}: -")
                print(f"  delta={delta:.2f}  " + "  ".join(row))
        print("   per-test power at n = 20,000, d = 0.3 (needed: %.5f)" % tgt)
        for tau in (0.0, 0.02, 0.03, 0.05, 0.10):
            for delta in GRID:
                row = [f"G={g}: {t_power(delta, g, tau, POOL):.4f}" for g in G_LIST]
                print(f"  tau={tau:.2f} delta={delta:.2f}  " + "  ".join(row))


def part3() -> None:
    print("== 3. Capacity demand of section 6.2 at the G written: 10 x (ceil((4,000 + 20,000) / G) + 100) on a core level; 10 x 100 on a reserve level")
    for g in (8, 11, 13, 14, 15, 19, 300):
        print(f"  G={g}: core level {10 * (math.ceil(24000 / g) + 100):,}   reserve level {10 * 100:,}   (sealed items per cluster {math.ceil(20000 / g):,}; M0-draw items per cluster about {1500 / g:.0f})")


if __name__ == "__main__":
    part0()
    part1()
    part2()
    part3()
