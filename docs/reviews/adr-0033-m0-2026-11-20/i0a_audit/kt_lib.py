# ruff: noqa
# ruff: noqa
"""M0-I0a audit (arbor-auditor, Claude Opus 5.5): independent recomputation library for the
ADR-0033 section 9.4 known-truth test. Standard library only; imports nothing from studies.m0.

Written from the TEXT of ADR-0033 revision 4 section 9.4 and the truth model of
docs/reviews/adr-0033-m0-2026-11-20/checks/shrink_check3c.py (read, not imported).

Differences from the implementer's code that are deliberate (to be independent):
- exact Student t quantile (incomplete beta + bisection), not a Cornish-Fisher series;
- fresh-cluster truth sampled through two binomials per cluster (exactly equivalent in law
  to m iid trinomial items), not uniform thresholds;
- Python's random.Random, not torch generators.
"""
from __future__ import annotations

import math
import random
from statistics import NormalDist, fmean

N = NormalDist()


# ---------- exact Student t quantile ----------
def _betacf(a, b, x):
    MAXIT, EPS, FPMIN = 500, 3e-16, 1e-300
    qab, qap, qam = a + b, a + 1, a - 1
    c, d = 1.0, 1 - qab * x / qap
    d = 1 / (d if abs(d) > FPMIN else FPMIN)
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1 + aa * d; d = 1 / (d if abs(d) > FPMIN else FPMIN)
        c = 1 + aa / c; c = c if abs(c) > FPMIN else FPMIN
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1 + aa * d; d = 1 / (d if abs(d) > FPMIN else FPMIN)
        c = 1 + aa / c; c = c if abs(c) > FPMIN else FPMIN
        de = d * c
        h *= de
        if abs(de - 1) < EPS:
            break
    return h


def betai(a, b, x):
    if x <= 0: return 0.0
    if x >= 1: return 1.0
    lb = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x)
    if x < (a + 1) / (a + b + 2):
        return math.exp(lb) * _betacf(a, b, x) / a
    return 1 - math.exp(lb) * _betacf(b, a, 1 - x) / b


def t_cdf(t, nu):
    x = nu / (nu + t * t)
    p = 0.5 * betai(nu / 2, 0.5, x)
    return 1 - p if t > 0 else p


_TQ = {}
def t_q(p, nu):
    key = (p, nu)
    if key not in _TQ:
        lo, hi = -50.0, 50.0
        for _ in range(200):
            mid = (lo + hi) / 2
            if t_cdf(mid, nu) < p: lo = mid
            else: hi = mid
        _TQ[key] = (lo + hi) / 2
    return _TQ[key]


# ---------- truth model (Review 3, shrink_check3c.py) ----------
def sizes_of(kind, g=300):
    if kind == "bal5": return [5] * g
    if kind == "unbal":
        k = g // 5
        return [1] * k + [2] * k + [3] * k + [5] * k + [16] * (g - 4 * k)
    if kind.startswith("bal"): return [int(kind[3:])] * g
    raise ValueError(kind)


def cluster_sum(rng, mu, d, m):
    """Sum of m iid items in {+1,-1,0} with P(+1)=(d+mu)/2, P(-1)=(d-mu)/2: exact via two binomials."""
    k = rng.binomialvariate(m, d) if d < 1 else m
    if k == 0: return 0, 0
    pos = rng.binomialvariate(k, (d + mu) / (2 * d))
    return 2 * pos - k, k  # sum, number of nonzero (= sum of squares)


def clamp(mu, d):
    return max(-d + 1e-9, min(d - 1e-9, mu))


def m5_pass(sums, m_list, delta, tq, scale=1.0):
    n = sum(m_list); g = len(sums)
    est = sum(sums) / n
    ss = sum((s - m * est) ** 2 for s, m in zip(sums, m_list))
    se = math.sqrt(ss * g / (g - 1)) / n
    return scale * est - tq * scale * se > -delta


def known_power(rng, g, n, d, tau, delta, runs):
    m = n // g
    tq = t_q(0.95, g - 1)
    ml = [m] * g
    ok = 0
    for _ in range(runs):
        sums = [cluster_sum(rng, clamp(rng.gauss(0, tau), d), d, m)[0] for _ in range(g)]
        ok += m5_pass(sums, ml, delta, tq)
    return ok / runs


def m0_draw(rng, d, tau, sizes):
    """Item-level synthetic M0 draw: list of clusters, each a list of item differences."""
    out = []
    for m in sizes:
        mu = clamp(rng.gauss(0, tau), d)
        out.append(rng.choices((1, -1, 0), weights=((d + mu) / 2, (d - mu) / 2, 1 - d), k=m))
    return out


# ---------- section 9.4 as worded (one stratum unless strata given) ----------
def components(m0, tau2_override=None, tau2_rule="mom"):
    g = len(m0)
    m_g = [len(c) for c in m0]
    means = [sum(c) / len(c) for c in m0]
    allx = [x for c in m0 for x in c]
    n0 = len(allx)
    mu = sum(allx) / n0
    d = sum(1 for x in allx if x != 0) / n0
    multi = [i for i in range(g) if m_g[i] > 1]
    ssw = [sum((x - means[i]) ** 2 for x in m0[i]) for i in range(g)]
    s_w2 = sum(ssw[i] for i in multi) / sum(m_g[i] - 1 for i in multi)
    xh = sum(means) / g
    V = sum((v - xh) ** 2 for v in means) / (g - 1)
    inv_m = sum(1 / m for m in m_g) / g
    raw = V - s_w2 * inv_m
    tau2 = max(0.0, raw) if tau2_override is None else tau2_override
    lam = [math.sqrt(tau2 / (tau2 + s_w2 / m)) if tau2 > 0 else 0.0 for m in m_g]
    dev = [lam[i] * (means[i] - xh) for i in range(g)]
    pool = []
    for i in multi:
        k = math.sqrt(m_g[i] / (m_g[i] - 1))
        pool.extend((x - means[i]) * k for x in m0[i])
    den = d - mu * mu
    scale = math.sqrt(d / den) if den > 1e-12 else 1.0
    return dict(tau2=tau2, raw_tau2=raw, s_w2=s_w2, V=V, inv_m=inv_m, dev=dev, pool=pool,
                scale=scale, mu=mu, d=d, m_g=m_g, means=means, g=g)


def procedure_power(rng, comp, n, g_e, delta, sims):
    """Share of simulated M5 samples that pass (section 9.4 bullet 2, as worded)."""
    base, extra = divmod(n, g_e)
    ml = [base + (1 if j < extra else 0) for j in range(g_e)]  # n spread over G_e clusters
    tq = t_q(0.95, g_e - 1)
    dev, pool, g = comp["dev"], comp["pool"], comp["g"]
    scale = comp["scale"]
    ok = 0
    for _ in range(sims):
        idx = [rng.randrange(g) for _ in range(g_e)]
        xs = rng.choices(pool, k=n) if pool else [0.0] * n
        sums = []
        p = 0
        for j, m in zip(idx, ml):
            sums.append(m * dev[j] + sum(xs[p:p + m]))
            p += m
        ok += m5_pass(sums, ml, delta, tq, scale)
    return ok / sims
