# ruff: noqa
"""Review 3 of ADR-0033: does section 9.4's shrinkage simulation (revision 3 text) recover a
known tau and a known power? Auditor's own code, standard library only.

Truth model (one stratum): G clusters, cluster effect mu_g ~ N(0, tau) (clamped so that
probabilities stay valid), item D in {+1, -1, 0} with P(+1) = (d + mu_g)/2, P(-1) = (d - mu_g)/2.
"Known power": the M5 test (mean, cluster-robust SE over G clusters, t quantile, pass if
est - t*SE > -delta) applied to fresh clusters and fresh items, n/G per cluster.

Procedure "as written" (section 9.4): from ONE M0 draw, resample G clusters with replacement,
shrink each cluster's deviation by lambda = sqrt(tau2 / (tau2 + s_w2 / m_bar)), draw n/G items
from the cluster's OWN items centred on its own mean, recentre, scale by sqrt(d/(d - mu^2)).
Variant "pooled": the same, but within-cluster deviations are drawn from the pooled,
(m_g/(m_g-1))-corrected residuals of all clusters.

Run: python3 -I shrink_check3.py   (trivial CPU, well under a minute)
"""

from __future__ import annotations

import math
import random
from statistics import NormalDist, fmean

N = NormalDist()


def tq(nu: int, p: float = 0.95) -> float:
    z = N.inv_cdf(p)
    return z + (z**3 + z) / (4 * nu)


def draw_cluster(rng: random.Random, mu: float, d: float, m: int) -> list[int]:
    mu = max(-d + 1e-9, min(d - 1e-9, mu))
    return rng.choices((1, -1, 0), weights=((d + mu) / 2, (d - mu) / 2, 1 - d), k=m)


def test_pass(clusters: list[list[float]], delta: float, scale: float = 1.0) -> bool:
    n = sum(len(c) for c in clusters)
    g = len(clusters)
    tot = sum(sum(c) for c in clusters)
    mean = tot / n
    ss = sum((sum(c) - len(c) * mean) ** 2 for c in clusters)
    se = math.sqrt(ss * g / (g - 1)) / n
    return scale * mean - tq(g - 1) * scale * se > -delta


def truth_power(rng, g, n, d, tau, delta, sims) -> float:
    m = n // g
    ok = 0
    for _ in range(sims):
        cl = [draw_cluster(rng, rng.gauss(0, tau), d, m) for _ in range(g)]
        ok += test_pass(cl, delta)
    return ok / sims


def m0_draw(rng, g, d, tau, sizes):
    return [draw_cluster(rng, rng.gauss(0, tau), d, sizes[i]) for i in range(g)]


def procedure(rng, m0, n, g_e, delta, sims, variant):
    allx = [x for c in m0 for x in c]
    n0 = len(allx)
    mu = fmean(allx)
    d_hat = sum(1 for x in allx if x != 0) / n0
    means = [fmean(c) for c in m0]
    multi = [c for c in m0 if len(c) > 1]
    s_w2 = sum(sum((x - fmean(c)) ** 2 for x in c) for c in multi) / sum(len(c) - 1 for c in multi)
    m_bar = n0 / len(m0)
    grand = fmean(means)
    var_means = sum((v - grand) ** 2 for v in means) / (len(means) - 1)
    tau2 = max(0.0, var_means - s_w2 / m_bar)
    lam = math.sqrt(tau2 / (tau2 + s_w2 / m_bar)) if tau2 > 0 else 0.0
    pooled = []
    for c in multi:
        cm, k = fmean(c), math.sqrt(len(c) / (len(c) - 1))
        pooled.extend((x - cm) * k for x in c)
    scale = math.sqrt(d_hat / (d_hat - mu**2))
    m = n // g_e
    ok = 0
    for _ in range(sims):
        cl = []
        for _ in range(g_e):
            j = rng.randrange(len(m0))
            c = m0[j]
            centre = grand + lam * (means[j] - grand) - mu  # recentred
            if variant == "own":
                cm = means[j]
                cl.append([centre + (x - cm) for x in rng.choices(c, k=m)])
            else:
                cl.append([centre + e for e in rng.choices(pooled, k=m)])
        ok += test_pass(cl, delta, scale)
    return ok / sims, math.sqrt(tau2), s_w2


def scenario(name, g, d, tau, sizes, n, delta, reps=6, sims=600, seed=953101):
    rng = random.Random(seed)
    truth = truth_power(rng, g, n, d, tau, delta, 2000)
    own, pool, taus = [], [], []
    for _ in range(reps):
        m0 = m0_draw(rng, g, d, tau, sizes)
        p1, th, _ = procedure(rng, m0, n, g, delta, sims, "own")
        p2, _, _ = procedure(rng, m0, n, g, delta, sims, "pooled")
        own.append(p1)
        pool.append(p2)
        taus.append(th)
    mc = math.sqrt(truth * (1 - truth) / 2000)
    print(f"{name}: true tau={tau} mean tau_hat={fmean(taus):.4f} (range {min(taus):.4f}-{max(taus):.4f});"
          f" known power={truth:.3f} (MC se {mc:.3f}); as written (own items)={fmean(own):.3f}"
          f" [{min(own):.3f}-{max(own):.3f}]; pooled residuals={fmean(pool):.3f}"
          f" [{min(pool):.3f}-{max(pool):.3f}]")


if __name__ == "__main__":
    G = 300
    bal5 = [5] * G
    unbal = ([1] * 60 + [2] * 60 + [3] * 60 + [5] * 60 + [16] * 60)  # 1,620 items, very unbalanced
    print("n = 6,000 items (20 per cluster), G = 300; deltas chosen for mid-range power")
    scenario("S1 balanced m=5, d=0.3, tau=0.05", G, 0.30, 0.05, bal5, 6000, 0.020)
    scenario("S2 balanced m=5, d=0.3, tau=0   ", G, 0.30, 0.00, bal5, 6000, 0.018)
    scenario("S3 unbalanced,   d=0.3, tau=0.05", G, 0.30, 0.05, unbal, 6000, 0.020)
    scenario("S4 s_w near 0,   d=0.02, tau=0.01", G, 0.02, 0.01, bal5, 6000, 0.004)
    scenario("S5 s_w near 0.5, d=0.5, tau=0.05", G, 0.50, 0.05, bal5, 6000, 0.025)
    scenario("S6 unbalanced,   d=0.3, tau=0   ", G, 0.30, 0.00, unbal, 6000, 0.018)
