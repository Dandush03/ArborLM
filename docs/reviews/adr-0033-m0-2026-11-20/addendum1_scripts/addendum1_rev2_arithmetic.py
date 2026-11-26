# ruff: noqa
"""Arithmetic for ADR-0033 addendum 1, draft 2. Formulas only: no model output, no item, no score, no cluster map
is read. Standard library only. Imports nothing from studies/ and nothing from the other scripts.

Run:  uv run --locked python -I docs/reviews/adr-0033-m0-2026-11-20/addendum1_scripts/addendum1_rev2_arithmetic.py

Part A  capacity demand per cluster and level (review 1, R1; lead ruling R-11), and per lineage in a cluster of k.
Part B  exact per-test power of the t test on G - 1 degrees of freedom at n = 20,000, d = 0.3 (normal cluster
        means; an idealisation of the registered simulation, not the simulation): largest tau at which each
        margin is reachable inside the pool, and the power at tau = 0.
Part C  how the registered reading behaves at small G (chi-square approximation for the M0 draw's cluster
        means, s_w^2 treated as known, 1,500 M0-draw items balanced over G clusters):
        P(tau_hat = 0) and P(part reads "reachable within 20,000") under choice 18 (a) the point estimate and
        (b) an upper bound. The interval used for (b) is the chi-square interval of the between-cluster
        variance. ADR-0033 registers no interval for tau_hat below 30 clusters, so (b) is an ASSUMPTION here.
Part D  t quantiles at very few clusters.
Part E  quotas of the per-cluster pool builder proposed in the addendum, on a made-up part.
Part F  the normal formulas of ADR-0033 sections 8 and 9.4 at small G, and the smallest margin the t test reaches.
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
M0_DRAW = 1_500
M_TESTS = 55
TARGET = 1 - 0.2 / M_TESTS
G_LIST = (3, 4, 5, 6, 8, 10, 11, 13, 14, 15, 19)


# ---------- chi-square, Student t, noncentral t ----------
def chi2_pdf(v: float, k: int) -> float:
    if v <= 0:
        return 0.0
    return math.exp((k / 2 - 1) * math.log(v) - v / 2 - (k / 2) * math.log(2) - math.lgamma(k / 2))


def chi2_cdf(x: float, k: int, steps: int = 4000) -> float:
    """P(chi2_k <= x). Substitution v = u^2 removes the singularity of the density at 0 for k = 1, 2."""
    if x <= 0:
        return 0.0
    top = math.sqrt(x)
    h = top / steps
    tot = 0.0
    for i in range(steps + 1):
        u = i * h
        w = 1 if i in (0, steps) else (4 if i % 2 else 2)
        tot += w * (chi2_pdf(u * u, k) * 2 * u if u > 0 else (math.sqrt(2 / math.pi) if k == 1 else 0.0))
    return tot * h / 3


def chi2_q(p: float, k: int) -> float:
    lo, hi = 0.0, 400.0
    for _ in range(70):
        mid = (lo + hi) / 2
        if chi2_cdf(mid, k) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def expect_chi2(f, k: int, steps: int = 4000) -> float:
    """E[f(V)], V ~ chi2_k, with v = u^2."""
    top = math.sqrt(k + 14 * math.sqrt(2 * k) + 60)
    h = top / steps
    tot = 0.0
    for i in range(steps + 1):
        u = i * h
        w = 1 if i in (0, steps) else (4 if i % 2 else 2)
        dens = chi2_pdf(u * u, k) * 2 * u if u > 0 else (math.sqrt(2 / math.pi) if k == 1 else 0.0)
        tot += w * dens * f(u * u)
    return tot * h / 3


def nct_sf(c: float, df: int, ncp: float) -> float:
    """P(T > c), T = (Z + ncp) / sqrt(V / df)."""
    return expect_chi2(lambda v: N.cdf(ncp - c * math.sqrt(v / df)), df)


def t_quantile(p: float, df: int) -> float:
    lo, hi = 0.0, 200.0
    for _ in range(70):
        mid = (lo + hi) / 2
        if 1 - nct_sf(mid, df, 0.0) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


TQ = {g: t_quantile(0.95, g - 1) for g in G_LIST + (2,)}


def t_power(delta: float, g: int, tau: float, n: float = POOL, d: float = D) -> float:
    se = math.sqrt(tau * tau / g + d / n)
    return nct_sf(TQ[g], g - 1, delta / se)


def tau_crit(delta: float, g: int) -> float | None:
    """Largest tau with per-test power >= TARGET at n = 20,000; None if not reached even at tau = 0."""
    if t_power(delta, g, 0.0) < TARGET:
        return None
    lo, hi = 0.0, 0.5
    for _ in range(50):
        mid = (lo + hi) / 2
        if t_power(delta, g, mid) >= TARGET:
            lo = mid
        else:
            hi = mid
    return lo


# ---------- parts ----------
def demand(g: int) -> int:
    return 10 * (math.ceil(DEV / g) + math.ceil(POOL / g) + TUNING)


def demand_draft1(g: int) -> int:
    return 10 * (math.ceil((DEV + POOL) / g) + TUNING)


def demand_lineage(g: int, k: int) -> int:
    return 10 * (math.ceil(math.ceil(DEV / g) / k) + math.ceil(math.ceil(POOL / g) / k) + math.ceil(TUNING / k))


def part_a() -> None:
    print("== A. Capacity demand per cluster and level: D(G) = 10 x (ceil(4,000/G) + ceil(20,000/G) + 100), every one of the seven levels")
    print("   (draft 1's formula 10 x (ceil(24,000/G) + 100) beside it; draft 1 put 1,000 on a reserve level)")
    for g in (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 19, 300):
        print(f"  G={g:>3}: D = {demand(g):>7,}   draft 1: {demand_draft1(g):>7,}   difference {demand(g) - demand_draft1(g):>3}")
    print("   per registered lineage in a cluster of k registered lineages:")
    print("   D_lin(G, k) = 10 x (ceil(ceil(4,000/G)/k) + ceil(ceil(20,000/G)/k) + ceil(100/k))")
    for g in (5, 8, 10, 13, 19):
        print(f"  G={g:>2}: " + "  ".join(f"k={k}: {demand_lineage(g, k):,}" for k in (1, 2, 3, 4, 6)))


def part_b() -> dict[int, dict[float, float | None]]:
    print(f"== B. t test on G - 1 degrees of freedom, n = 20,000, d = 0.3, {M_TESTS} tests, per-test target {TARGET:.5f}")
    crit: dict[int, dict[float, float | None]] = {g: {} for g in G_LIST}
    print("   t_0.95 on G - 1 df: " + "  ".join(f"G={g}: {TQ[g]:.3f}" for g in G_LIST))
    print("   largest tau at which delta is reachable inside the 20,000 pool ('-' = not reachable even at tau = 0)")
    for delta in GRID:
        row = []
        for g in G_LIST:
            c = tau_crit(delta, g)
            crit[g][delta] = c
            row.append(f"G={g}: {c:.4f}" if c is not None else f"G={g}: -")
        print(f"  delta={delta:.2f}  " + "  ".join(row))
    print("   per-test power at n = 20,000")
    for tau in (0.0, 0.01, 0.02, 0.03, 0.05, 0.10):
        for delta in GRID:
            print(f"  tau={tau:.2f} delta={delta:.2f}  " + "  ".join(f"G={g}: {t_power(delta, g, tau):.4f}" for g in G_LIST))
    return crit


def part_c(crit: dict[int, dict[float, float | None]]) -> None:
    print("== C. The registered reading at small G (chi-square approximation; M0 draw of 1,500 items balanced over G clusters)")
    print("   V = variance (divisor G - 1) of the cluster means; V (G-1) / (tau^2 + s_w^2/m) ~ chi2(G-1); s_w^2 = d - tau^2")
    print("   (a) tau_hat^2 = max(0, V - s_w^2/m)      (b) tau_up^2 = max(0, V (G-1)/chi2_{0.05,G-1} - s_w^2/m)  [ASSUMED interval]")
    for g in (5, 8, 10, 13, 19):
        nu = g - 1
        m = M0_DRAW / g
        q05 = chi2_q(0.05, nu)
        print(f"  G={g}, m={m:.1f} items per cluster, chi2_0.05,{nu} = {q05:.3f}")
        for tau in (0.0, 0.01, 0.03, 0.05, 0.10):
            a = (D - tau * tau) / m
            scale = tau * tau + a
            p_zero = chi2_cdf(nu * a / scale, nu)
            ra, rb = [], []
            for delta in GRID:
                c = crit[g][delta]
                if c is None:
                    ra.append(f"{delta:.2f}: 0.000")
                    rb.append(f"{delta:.2f}: 0.000")
                    continue
                truth = "T" if tau <= c else "F"
                ra.append(f"{delta:.2f}: {chi2_cdf(nu * (c * c + a) / scale, nu):.3f}{truth}")
                rb.append(f"{delta:.2f}: {chi2_cdf(q05 * (c * c + a) / scale, nu):.3f}{truth}")
            print(f"    true tau={tau:.2f}: P(tau_hat=0)={p_zero:.3f}   reads reachable (a) " + "  ".join(ra) + "   (b) " + "  ".join(rb))
    print("   T = the margin is truly reachable at that tau inside the pool; F = it is not")


def part_f() -> None:
    z = N.inv_cdf(0.95) + N.inv_cdf(TARGET)
    print(f"== F. Normal formulas of ADR-0033 sections 8 and 9.4 at small G ({M_TESTS} tests; z sum {z:.4f})")
    print("   floor of section 9.4: largest tau at which Phi(delta sqrt(G)/tau - z_0.95) meets the target (tau <= delta sqrt(G)/z sum)")
    for delta in GRID:
        print(f"  delta={delta:.2f}  " + "  ".join(f"G={g}: {delta * math.sqrt(g) / z:.4f}" for g in G_LIST))
    print("   smallest delta reachable, normal formula: at n = 20,000 / at any n (d = 0.3)")
    for tau in (0.01, 0.02, 0.03, 0.05, 0.10, 0.15):
        print(f"  tau={tau:.2f}  " + "  ".join(f"G={g}: {z * math.sqrt(D / POOL + tau * tau / g):.3f}/{z * tau / math.sqrt(g):.3f}" for g in G_LIST))
    print("   smallest delta reachable with the t test (exact, n = 20,000): bisection on delta")
    for tau in (0.03, 0.05, 0.10):
        row = []
        for g in G_LIST:
            lo, hi = 0.0, 2.0
            for _ in range(40):
                mid = (lo + hi) / 2
                if t_power(mid, g, tau) >= TARGET:
                    hi = mid
                else:
                    lo = mid
            row.append(f"G={g}: {hi:.3f}")
        print(f"  tau={tau:.2f}  " + "  ".join(row))


def part_d() -> None:
    print("== D. t quantile (0.95, one-sided) at very few clusters")
    print("  G=1: 0 degrees of freedom: no standard error, no t quantile, no interval")
    for g in (2, 3, 4, 5, 6, 8, 10):
        q = TQ[g] if g in TQ else t_quantile(0.95, g - 1)
        print(f"  G={g}: df {g - 1}: t_0.95 = {q:.3f}")
    print(f"  normal quantile for comparison: {N.inv_cdf(0.95):.3f}")


def allocate(total: int, weights: list[float]) -> list[int]:
    """Largest remainder; ties to the lower index."""
    s = sum(weights)
    raw = [total * w / s for w in weights]
    base = [int(x) for x in raw]
    rest = total - sum(base)
    order = sorted(range(len(weights)), key=lambda i: (-(raw[i] - base[i]), i))
    for i in order[:rest]:
        base[i] += 1
    return base


def part_e() -> None:
    print("== E. Per-cluster builder against the builder as written, on a MADE-UP part: 7 clusters holding 3, 2, 1, 1, 1, 1, 1 registered lineages")
    sizes = [3, 2, 1, 1, 1, 1, 1]
    g, n_lin = len(sizes), sum(sizes)
    for name, total in (("development pool", DEV), ("sealed pool", POOL), ("M0 draw", M0_DRAW)):
        per_lin = allocate(total, [1.0] * n_lin)
        as_written, i = [], 0
        for k in sizes:
            as_written.append(sum(per_lin[i : i + k]))
            i += k
        per_cluster = allocate(total, [1.0] * g)
        inside = [allocate(q, [1.0] * k) for q, k in zip(per_cluster, sizes)]
        print(f"  {name} ({total:,}): as written, items per cluster {as_written}; share of the largest cluster {max(as_written) / total:.3f}")
        print(f"      per-cluster builder, items per cluster {per_cluster}; per lineage inside {inside}")
    print(f"  equal share of one cluster of {g}: {1 / g:.3f}")
    print("  level split of one cluster's quota (example quota 572, mix 0.2 on each of five levels): ", allocate(572, [0.2] * 5))


if __name__ == "__main__":
    part_a()
    crit = part_b()
    part_c(crit)
    part_d()
    part_e()
    part_f()
