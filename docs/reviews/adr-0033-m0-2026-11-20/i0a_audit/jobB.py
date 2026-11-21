# ruff: noqa
# ruff: noqa
"""M0-I0a audit, job B: numbers for the design options (auditor's own arithmetic; standard library).
Usage: python3 -I jobB.py
Conventions: one-sided alpha 0.05; overall power 0.8 by Boole over M tests -> per-test target 1 - 0.2/M;
paired item variance bounded by d (discordance); ADR-0033 section 9.4 ladder.
"""
import math, random
from statistics import NormalDist
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from kt_lib import t_q

N = NormalDist(); Z = N.inv_cdf
LADDER = (500, 1000, 1500, 2000, 3000, 4000, 6000, 8000, 12000, 16000, 20000)
z95 = Z(0.95)


def ladder(n):
    for x in LADDER:
        if x >= n: return x
    return None


print("== Option (i): lineages as fixed strata, items the unit. n = (z_.95 + z_target)^2 d / delta^2 (normal; within-lineage variance <= d)")
for M in (55, 70, 77):
    tgt = 1 - 0.2 / M; k = (z95 + Z(tgt)) ** 2
    print(f"M={M}: per-test target {tgt:.5f}, factor (z+z)^2 = {k:.2f}")
    for d in (0.2, 0.3, 0.4):
        row = []
        for dl in (0.02, 0.03, 0.05):
            n = k * d / dl ** 2
            row.append(f"delta={dl}: n={math.ceil(n):,} (ladder {ladder(n)})")
        print(f"   d={d}: " + "; ".join(row))

print("\n== Option (i) with the t branch at small df is irrelevant (item df ~ n); per-lineage counts at G=7: n/7")

print("\n== Option (ii): clusters kept. Smallest delta reachable at ANY n (cluster SD tau), M=55 target 0.99636")
rng = random.Random(953901)


def ncp_needed(df, tgt, R=60000):
    tc = t_q(0.95, df)
    zs = [rng.gauss(0, 1) for _ in range(R)]; cs = [math.sqrt(rng.gammavariate(df / 2, 2) / df) for _ in range(R)]
    lo, hi = 0.0, 60.0
    for _ in range(40):
        mid = (lo + hi) / 2
        p = sum(1 for z, c in zip(zs, cs) if (z + mid) / c > tc) / R
        if p < tgt: lo = mid
        else: hi = mid
    return hi


tgt = 1 - 0.2 / 55
for G in (6, 7, 8, 10, 30, 75, 300):
    ncp = ncp_needed(G - 1, tgt)
    normal = z95 + Z(tgt)
    cells = []
    for tau in (0.03, 0.05, 0.10):
        cells.append(f"tau={tau}: t-based {ncp * tau / math.sqrt(G):.3f} | ADR normal floor {normal * tau / math.sqrt(G):.3f}")
    print(f"G={G} (df {G-1}): ncp needed {ncp:.2f} (normal {normal:.2f}); " + "; ".join(cells))

print("\n   at the sealed pool n=20,000 and d=0.3 (cluster-mean SD sqrt(tau^2 + d G/n)):")
for G in (6, 7, 8, 10):
    ncp = ncp_needed(G - 1, tgt)
    cells = []
    for tau in (0.0, 0.03, 0.05, 0.10):
        cells.append(f"tau={tau}: {ncp * math.sqrt(tau ** 2 / G + 0.3 / 20000):.3f}")
    print(f"G={G}: " + "; ".join(cells))

print("\n== Option (iii): public sets, sealed part after 1,650 development (+1,000 reserve if > 6,000 items); delta reachable, d=0.3, M=55, items independent")
k55 = (z95 + Z(1 - 0.2 / 55)) ** 2
for name, tot in (("MMLU-Pro (K1)", 12032), ("PopQA (K2)", 14000), ("L1 pooled, 4,000 cap per task", 3200 + 3270 + 4000 + 4000 + 638 + 277),
                  ("BIG-Bench Hard", 6511), ("GSM8K", 1319), ("CRUXEval output", 800)):
    if tot <= 1650: sealed = tot - round(tot / 3)
    else: sealed = tot - 1650 - (1000 if tot > 6000 else 0)
    print(f"{name}: total {tot:,}, sealed about {sealed:,}, smallest delta {math.sqrt(k55 * 0.3 / sealed):.3f} (d=0.3), {math.sqrt(k55 * 0.2 / sealed):.3f} (d=0.2)")

print("\n== Option (iv): G needed so that the normal floor reaches the target: G >= ((z.95+z_t) tau / delta)^2, M=55")
for tau in (0.03, 0.05, 0.10):
    print(f"tau={tau}: " + "; ".join(f"delta={dl}: G>={math.ceil(((z95 + Z(tgt)) * tau / dl) ** 2)}" for dl in (0.02, 0.03, 0.05)))

print("\n== tau^2 upper confidence bound (90 % one-sided, chi-square on V's df): ratio UCB/point of V")
def gammainc_lower(a, x):
    # regularised lower incomplete gamma P(a, x), series (fine for x < a + 50 here)
    if x <= 0: return 0.0
    term = 1.0 / a; tot = term; k = 0
    while True:
        k += 1; term *= x / (a + k); tot += term
        if term < tot * 1e-15: break
    return tot * math.exp(-x + a * math.log(x) - math.lgamma(a))


def chi2_q(p, df):
    lo, hi = 0.0, 10.0 * df + 100
    for _ in range(200):
        mid = (lo + hi) / 2
        if gammainc_lower(df / 2, mid / 2) < p: lo = mid
        else: hi = mid
    return (lo + hi) / 2


for df in (1, 2, 4, 6, 9, 299):
    q = chi2_q(0.05, df)
    print(f"V df={df}: chi2_0.05={q:.5f}; 95 % upper bound of V = {df / q:.1f} x V")
