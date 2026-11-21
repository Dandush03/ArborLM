# ruff: noqa
"""Confirmation checks for ADR-0033 revision 2 (auditor's own code, stdlib only).

Run: python3 -I power_check2.py   (trivial CPU)
"""

from __future__ import annotations

import math
import random
from statistics import NormalDist, fmean, pvariance

N = NormalDist()
ZA = N.inv_cdf(0.95)


def z_boole(m_total: int) -> float:
    return ZA + N.inv_cdf(1 - 0.2 / m_total)


def z_prod(m_total: int) -> float:
    return ZA + N.inv_cdf(0.8 ** (1 / m_total))


def a_corrected_figure() -> None:
    print("== A. Review 1's figure (tau=0.10, G=300, delta=0.03, d=0.3), product vs Boole")
    d, tau, g, delta = 0.30, 0.10, 300, 0.03
    for m in (55, 70):
        for name, z in (("product", z_prod(m)), ("Boole", z_boole(m))):
            rem = (delta / z) ** 2 - tau**2 / g
            n = d / rem if rem > 0 else math.inf
            print(f"  M={m} {name:7s}: z={z:.3f} n={n:8.0f}")


def b_reachable_delta() -> None:
    print("== B. Smallest delta reachable (Boole, M=55, d=0.3) at n=20,000 and at n=infinity")
    z = z_boole(55)
    for tau in (0.03, 0.05, 0.10, 0.15):
        row = []
        for g in (60, 150, 300, 600, 1200):
            fin = z * math.sqrt(0.3 / 20000 + tau**2 / g)
            inf = z * tau / math.sqrt(g)
            row.append(f"G={g}: {fin:.4f}/{inf:.4f}")
        print(f"  tau={tau}: " + "  ".join(row))


def c_two_stage_bias(seed: int = 953001) -> None:
    """Two-stage resampling from m_obs observed items per cluster inflates tau."""
    print("== C. Between-cluster SD seen by naive two-stage resampling vs shrunk resampling")
    rng = random.Random(seed)
    d_base = 0.30
    for g, m_obs, tau in ((300, 5, 0.05), (60, 25, 0.05), (300, 5, 0.0)):
        # true cluster mean differences mu_g ~ N(0, tau), items D in {-1,0,1} with
        # P(+1)=(d+mu)/2, P(-1)=(d-mu)/2
        clusters = []
        for _ in range(g):
            mu = max(-0.29, min(0.29, rng.gauss(0.0, tau)))
            a, b = (d_base + mu) / 2, (d_base - mu) / 2
            items = []
            for _ in range(m_obs):
                u = rng.random()
                items.append(1 if u < a else (-1 if u < a + b else 0))
            clusters.append(items)
        means = [fmean(c) for c in clusters]
        s_w2 = fmean([pvariance(c) * m_obs / (m_obs - 1) for c in clusters])
        between_naive = pvariance(means)
        tau2_hat = max(0.0, between_naive - s_w2 / m_obs)
        lam = math.sqrt(tau2_hat / between_naive) if between_naive > 0 else 0.0
        print(f"  G={g} m_obs={m_obs} true tau={tau}: naive resampled between-SD="
              f"{math.sqrt(between_naive):.4f}; method-of-moments tau_hat={math.sqrt(tau2_hat):.4f};"
              f" shrink factor={lam:.3f}")
        # floor of SE at G clusters, and the per-test power cap at delta=0.03 (Boole M=55)
        z = z_boole(55)
        for label, t2 in (("naive", between_naive), ("shrunk", tau2_hat), ("true", tau**2)):
            se_floor = math.sqrt(t2 / g)
            cap = N.cdf(0.03 / se_floor - ZA) if se_floor > 0 else 1.0
            print(f"    {label:6s}: SE floor={se_floor:.4f}; max per-test power at delta=0.03="
                  f"{cap:.4f} (need {N.cdf(z - ZA):.4f})")
        # precision of tau^2 from the M0 draw (approximate SE of method of moments)
        se_t2 = math.sqrt(2 / g) * (s_w2 / m_obs + tau2_hat)
        print(f"    approx SE of tau^2_hat = {se_t2:.4f} (tau^2_hat = {tau2_hat:.4f})")


if __name__ == "__main__":
    a_corrected_figure()
    b_reachable_delta()
    c_two_stage_bias()
