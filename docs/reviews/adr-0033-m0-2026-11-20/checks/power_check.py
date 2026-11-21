# ruff: noqa
"""Independent checks of ADR-0033 draft 1, section 9.4 and section 8 ("Why 20,000").

Auditor's own code, standard library only. Imports nothing from the repository.
Run: python3 -I power_check.py  (trivial CPU, a few seconds).
"""

from __future__ import annotations

import math
import random
from statistics import NormalDist

N = NormalDist()
Z_A = N.inv_cdf(0.95)  # one-sided alpha 0.05


def k_product(m_total: int, power: float = 0.8) -> float:
    """(z_a + z_pi)^2 with pi = power^(1/M): the draft's product rule."""
    pi = power ** (1.0 / m_total)
    return (Z_A + N.inv_cdf(pi)) ** 2


def k_boole(m_total: int, power: float = 0.8) -> float:
    """(z_a + z_pi)^2 with pi = 1 - (1-power)/M: valid under any dependence."""
    pi = 1.0 - (1.0 - power) / m_total
    return (Z_A + N.inv_cdf(pi)) ** 2


def section_a() -> None:
    print("== A. Coefficient k in n = k * d / delta^2 (independence, no cluster effect)")
    for m in (1, 5, 40, 55, 70):
        print(f"  M={m:3d} tests: product k={k_product(m):6.2f}   Boole k={k_boole(m):6.2f}"
              f"   ratio={k_boole(m) / k_product(m):.4f}")
    print("  ADR-0032 quotes: 6.2 (M=1), 11.5 (M=5), 17.5 (M=40); draft: 18 to 19 (M=55..70)")
    print("== A2. Draft's example sizes")
    for m in (55, 70):
        for d, delta in ((0.3, 0.03), (0.3, 0.02), (0.2, 0.03), (0.3, 0.05)):
            n_p = k_product(m) * d / delta**2
            n_b = k_boole(m) * d / delta**2
            print(f"  M={m} d={d} delta={delta}: product n={n_p:8.0f}  Boole n={n_b:8.0f}")
        dmax = 20000 * 0.02**2 / k_product(m)
        print(f"  M={m}: largest d coverable by 20,000 at delta 0.02 (product) = {dmax:.3f}")


def section_b(seed: int = 400009) -> None:
    """Recentre + scale by sqrt(d/(d-mu^2)) reproduces the null with discordance d."""
    print("== B. Recentring and variance scaling, item-level (no clusters)")
    rng = random.Random(seed)
    a, b = 0.30, 0.06  # P(D=+1), P(D=-1): d=0.36, mu=0.24 (teacher well ahead of S0)
    d, mu = a + b, a - b
    n0 = 1500
    base = [1 if u < a else (-1 if u < a + b else 0) for u in (rng.random() for _ in range(n0))]
    mu_hat = sum(base) / n0
    d_hat = sum(1 for x in base if x != 0) / n0
    scale = math.sqrt(d_hat / (d_hat - mu_hat**2))
    print(f"  measured d={d_hat:.4f} mu={mu_hat:.4f} scale={scale:.4f} (true d={d}, mu={mu})")
    for n, delta in ((1000, 0.05), (2000, 0.03)):
        sims, passed = 2000, 0
        for _ in range(sims):
            s = [base[rng.randrange(n0)] for _ in range(n)]
            m = sum(s) / n
            var = sum((x - m) ** 2 for x in s) / (n - 1)
            est = (m - mu_hat) * scale
            se = math.sqrt(var / n) * scale
            if est - Z_A * se > -delta:
                passed += 1
        analytic = N.cdf(delta * math.sqrt(n / d_hat) - Z_A)
        print(f"  n={n} delta={delta}: simulated power={passed / sims:.4f}  analytic={analytic:.4f}")


def section_c() -> None:
    """Fixed number of templates G in the sealed split versus the draft's resampling."""
    print("== C. Cluster design: sealed split has G fixed templates; draft resamples n/25 clusters")
    d = 0.30
    for tau in (0.03, 0.05, 0.10):
        print(f"  between-template SD of the recentred difference, within family: tau={tau}")
        for g in (60, 300):
            floor = tau / math.sqrt(g)
            for delta in (0.02, 0.03, 0.05):
                # per-test power needed for 11 parts x 5 tests (product rule) and achievable cap
                need = 0.8 ** (1 / 55)
                cap = N.cdf(delta / floor - Z_A)
                # required n under the true design: Var = d/n + tau^2/G
                z = Z_A + N.inv_cdf(need)
                rem = (delta / z) ** 2 - tau**2 / g
                n_true = d / rem if rem > 0 else math.inf
                # draft's construction: clusters drawn = n/25, Var = d/n + tau^2*25/n
                n_draft = (d + 25 * tau**2) * z**2 / delta**2
                print(f"    G={g:3d} delta={delta}: max per-test power={cap:.4f} (need {need:.4f});"
                      f" n draft={n_draft:8.0f}  n true design="
                      f"{'UNREACHABLE' if math.isinf(n_true) else f'{n_true:8.0f}'}")


def section_d(seed: int = 400010, sims: int = 3000, n: int = 2000, delta: float = 0.03) -> None:
    """Two tests sharing S can be negatively dependent: product is then NOT a lower bound."""
    print("== D. Dependence between the parity tests against two complementary teachers")
    rng = random.Random(seed)
    p = 0.6  # both teachers 0.6, independent across systems on an item (complementary)
    both = one1 = one2 = 0
    for _ in range(sims):
        s1 = s2 = 0
        q1 = q2 = 0.0
        for _ in range(n):
            t1 = rng.random() < p
            t2 = rng.random() < p
            s = t1 if rng.random() < 0.5 else t2  # student copies one teacher per item
            x1, x2 = s - t1, s - t2
            s1 += x1
            s2 += x2
            q1 += x1 * x1
            q2 += x2 * x2
        m1, m2 = s1 / n, s2 / n
        se1 = math.sqrt((q1 / n - m1 * m1) / n)
        se2 = math.sqrt((q2 / n - m2 * m2) / n)
        p1 = m1 - Z_A * se1 > -delta
        p2 = m2 - Z_A * se2 > -delta
        one1 += p1
        one2 += p2
        both += p1 and p2
    pi1, pi2, pj = one1 / sims, one2 / sims, both / sims
    mc = math.sqrt(pj * (1 - pj) / sims)
    print(f"  n={n} delta={delta} sims={sims}: P(pass1)={pi1:.4f} P(pass2)={pi2:.4f}"
          f" product={pi1 * pi2:.4f} joint={pj:.4f} (MC se {mc:.4f})"
          f" Boole bound={1 - (1 - pi1) - (1 - pi2):.4f}")


def section_e() -> None:
    print("== E. Monte Carlo resolution of the per-test power near the target")
    need = 0.8 ** (1 / 5 / 1) ** 1  # per part, m=5: pi^5 >= 0.8^(1/P)
    for p_parts in (11, 14):
        target_part = 0.8 ** (1 / p_parts)
        pi = target_part ** (1 / 5)
        for sims in (2000, 20000):
            se = math.sqrt(pi * (1 - pi) / sims)
            print(f"  P={p_parts}: per-test pi needed={pi:.5f}; expected failures in {sims} sims="
                  f"{(1 - pi) * sims:.1f}; MC se of pi={se:.5f}; se of pi^5 ~ {5 * se:.4f}"
                  f" vs target {target_part:.4f}")
    del need


if __name__ == "__main__":
    section_a()
    section_b()
    section_c()
    section_d()
    section_e()
