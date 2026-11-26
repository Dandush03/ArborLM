# ruff: noqa
"""Review 2 of ADR-0033 addendum 1, draft 2: independent recomputation of the numbers of sections 4 (N6), 6, 9 and 10.

Standard library only. Imports nothing from studies/ and nothing from the drafter's or review 1's scripts.
Written from the formulas stated in the addendum and in ADR-0033 lines 396-468 and 518.

Model (the drafter's and review 1's idealisation, restated): n = 20,000 sealed items over G clusters; cluster
means of the paired difference N(0, tau^2 + d G / n), d = 0.3; test passes if mean - t_{0.95,G-1} SE > -delta,
SE = sample s.d. of cluster means / sqrt(G). Then (mean + delta)/SE is noncentral t on G-1 df with
ncp = delta sqrt(G) / sqrt(tau^2 + d G / n). Per-test target 1 - 0.2/55.
M0 draw: 1,500 items balanced over G clusters (m = 1500/G); s_w^2 = d - tau^2;
V (G-1) / (tau^2 + s_w^2/m) ~ chi2(G-1) (normal cluster means).
"""
import math
import random
import sys
from statistics import NormalDist

N = NormalDist()
D = 0.3
NPOOL = 20000
TARGET = 1 - 0.2 / 55
GS = [5, 8, 10, 13, 19]


def Phi(x):
    return 0.5 * math.erfc(-x / math.sqrt(2))


def lower_gamma_reg(a, x):
    if x <= 0:
        return 0.0
    if x < a + 1:
        s = term = 1.0 / a
        k = a
        for _ in range(10000):
            k += 1
            term *= x / k
            s += term
            if abs(term) < 1e-16 * abs(s):
                break
        return s * math.exp(-x + a * math.log(x) - math.lgamma(a))
    # continued fraction for Q
    b = x + 1 - a
    c = 1e300
    d = 1 / b
    h = d
    for i in range(1, 10000):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        d = 1e-300 if abs(d) < 1e-300 else d
        c = b + an / c
        c = 1e-300 if abs(c) < 1e-300 else c
        d = 1 / d
        de = d * c
        h *= de
        if abs(de - 1) < 1e-15:
            break
    return 1 - math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def chi2_cdf(x, k):
    return lower_gamma_reg(k / 2, x / 2)


def bisect(f, lo, hi, it=200):
    flo = f(lo)
    for _ in range(it):
        mid = (lo + hi) / 2
        fm = f(mid)
        if (fm > 0) == (flo > 0):
            lo, flo = mid, fm
        else:
            hi = mid
    return (lo + hi) / 2


def chi2_ppf(p, k):
    return bisect(lambda x: chi2_cdf(x, k) - p, 1e-12, 1000)


def nct_sf(t, nu, lam, npts=6000):
    """P(T > t), T = (Z + lam) / sqrt(W/nu), W ~ chi2(nu); integrate over u = sqrt(W) (chi density)."""
    hi = math.sqrt(nu) + 14
    h = hi / npts
    logc = -((nu / 2 - 1) * math.log(2) + math.lgamma(nu / 2))
    tot = 0.0
    for i in range(npts + 1):
        u = i * h
        if u == 0:
            f = 0.0 if nu > 1 else math.exp(logc)
        else:
            f = math.exp(logc + (nu - 1) * math.log(u) - u * u / 2)
        g = f * Phi(lam - t * u / math.sqrt(nu))
        w = 1 if i in (0, npts) else (4 if i % 2 else 2)
        tot += w * g
    return tot * h / 3


def t_ppf(p, nu):
    return bisect(lambda t: (1 - nct_sf(t, nu, 0.0)) - p, 0, 50, it=80)


TQ = {}


def tq(G):
    if G not in TQ:
        TQ[G] = t_ppf(0.95, G - 1)
    return TQ[G]


def power(G, tau, delta, n=NPOOL, d=D):
    s = math.sqrt(tau * tau + d * G / n)
    return nct_sf(tq(G), G - 1, delta * math.sqrt(G) / s)


def tau_star(G, delta):
    if power(G, 0.0, delta) < TARGET:
        return None
    return bisect(lambda tau: power(G, tau, delta) - TARGET, 0.0, 0.5, it=50)


def main():
    print("python", sys.version.split()[0], "| target", round(TARGET, 5), "| z sum", round(N.inv_cdf(TARGET) + N.inv_cdf(0.95), 4))
    print("== t quantiles (0.95):", {G: round(tq(G), 3) for G in [2, 3, 5, 8, 10, 13, 19]})
    print("== (a) floor: largest tau with delta sqrt(G)/tau >= z sum")
    zs = N.inv_cdf(TARGET) + N.inv_cdf(0.95)
    for dl in [0.02, 0.03, 0.05]:
        print(f"  delta={dl}:", "  ".join(f"G={G}: {dl*math.sqrt(G)/zs:.4f}" for G in GS))
    print("== (b) largest tau at which delta reachable within 20,000 (t, exact power, d=0.3)")
    TS = {}
    for dl in [0.02, 0.03, 0.05]:
        row = []
        for G in GS:
            ts = tau_star(G, dl)
            TS[(G, dl)] = ts
            row.append(f"G={G}: {'none' if ts is None else f'{ts:.4f}'}")
        print(f"  delta={dl}:", "  ".join(row))
    print("  power at tau=0, delta=0.02:", "  ".join(f"G={G}: {power(G,0,0.02):.4f}" for G in [5, 8, 10, 11, 13, 19]))
    print("  largest tau at any n (n -> inf), delta=0.05:", "  ".join(
        f"G={G}: {0.05*math.sqrt(G)/(tq(G)+N.inv_cdf(TARGET)):.4f} (approx, normal-in-mean)" for G in [5, 19]))
    print("== (c) smallest delta reachable within 20,000 (t)")
    for tau in [0.03, 0.05, 0.10]:
        row = []
        for G in GS:
            dl = bisect(lambda x: power(G, tau, x) - TARGET, 1e-4, 1.0, it=40)
            row.append(f"G={G}: {dl:.3f}")
        print(f"  tau={tau}:", "  ".join(row))
    print("== (d) chi2 approximation: P(tau_hat = 0) and P(reads reachable), (a) point, (b) chi2 upper bound")
    for G in GS:
        m = 1500 / G
        c05 = chi2_ppf(0.05, G - 1)
        print(f"  G={G}, m={m:.1f}, chi2_0.05,{G-1}={c05:.3f}")
        for tau in [0.0, 0.01, 0.03, 0.05, 0.10]:
            a = (D - tau * tau) / m
            p0 = chi2_cdf((G - 1) * a / (tau * tau + a), G - 1)
            pa, pb = [], []
            for dl in [0.02, 0.03, 0.05]:
                ts = TS[(G, dl)]
                if ts is None:
                    pa.append("0.000 "); pb.append("0.000 "); continue
                lab = "T" if tau <= ts else "F"
                pa.append(f"{chi2_cdf((G-1)*(ts*ts+a)/(tau*tau+a), G-1):.3f}{lab}")
                pb.append(f"{chi2_cdf(c05*(ts*ts+a)/(tau*tau+a), G-1):.3f}{lab}")
            print(f"    tau={tau:.2f}: P0={p0:.3f}  (a) {' '.join(pa)}  (b) {' '.join(pb)}")
    print("  with s_w^2 = d (not d - tau^2), P0 at tau=0.03:", "  ".join(
        f"G={G}: {chi2_cdf((G-1)*(D/(1500/G))/(0.0009+D/(1500/G)), G-1):.3f}" for G in GS))
    print("== section 9 item 1: one-df stratum case P(chi2_1 <= 0.742) =", round(chi2_cdf(0.742, 1), 3),
          "; one stratum G=13 tau=0.03:", round(chi2_cdf(12 * (0.2991 / (1500 / 13)) / (0.0009 + 0.2991 / (1500 / 13)), 12), 3))
    print("== section 4 closing (N6): hypergeometric 27 of 116, 58 to A: mean",
          27 * 58 / 116, "sd", round(math.sqrt(27 * 0.5 * 0.5 * (116 - 27) / 115), 3))
    print("== section 9 item 3: items per cluster 1500/G:", {G: round(1500 / G, 1) for G in [5, 19]},
          "sealed per cluster 20000/G:", {G: round(20000 / G, 1) for G in [5, 19]})
    print("== section 10: D(G) = 10 (ceil(4000/G) + ceil(20000/G) + 100)")
    Dg = lambda G: 10 * (math.ceil(4000 / G) + math.ceil(20000 / G) + 100)
    for G in [5, 8, 10, 11, 13, 14, 15, 19, 300]:
        print(f"  D({G}) = {Dg(G):,}")
    print("  ratio to D(300):", round(Dg(19) / Dg(300), 2), "to", round(Dg(5) / Dg(300), 2))
    Dl = lambda G, k: 10 * (math.ceil(math.ceil(4000 / G) / k) + math.ceil(math.ceil(20000 / G) / k) + math.ceil(100 / k))
    print("  D_lin(10,2) =", f"{Dl(10,2):,}", " D_lin(13,3) =", f"{Dl(13,3):,}")
    # builder as written on lineages: demand per lineage at L lineages in the part (not in the draft)
    print("  builder as written (equal per lineage), part of 7 clusters with 3,2,1,1,1,1,1 lineages (L=10):",
          "per-lineage demand", f"{Dg(10):,}", "; cluster of 3 holds", 3 * (math.ceil(4000 / 10) + math.ceil(20000 / 10)), "pool items =",
          round(3 / 10, 3), "of each pool")
    print("== direct simulation, item level, outcomes in {-1,0,+1}, P(+-1) = 0.15 +- mu_g/2, mu_g ~ N(0, tau^2); seed 20261125")
    print("   reads reachable (a) := tau_hat <= tau*(G, delta) computed at d = 0.3 (the floor is then met as well)")
    rng = random.Random(20261125)
    REPS = 3000
    for G in [5, 10]:
        m = 1500 // G
        for tau in [0.0, 0.03, 0.05]:
            z = 0
            ra = {0.02: 0, 0.03: 0, 0.05: 0}
            for _ in range(REPS):
                means, wv = [], []
                for g in range(G):
                    mu = rng.gauss(0, tau) if tau > 0 else 0.0
                    pp = min(max(0.15 + mu / 2, 0), 1); pm = min(max(0.15 - mu / 2, 0), 1 - pp)
                    s = s2 = 0
                    for _ in range(m):
                        u = rng.random()
                        x = 1 if u < pp else (-1 if u < pp + pm else 0)
                        s += x; s2 += x * x
                    mean = s / m
                    means.append(mean); wv.append((s2 - m * mean * mean) / (m - 1))
                gm = sum(means) / G
                V = sum((x - gm) ** 2 for x in means) / (G - 1)
                sw2 = sum(wv) / G
                t2 = max(0.0, V - sw2 / m)
                z += t2 == 0
                th = math.sqrt(t2)
                for dl in ra:
                    ts = TS[(G, dl)]
                    ra[dl] += (ts is not None and th <= ts)
            print(f"  G={G} m={m} tau={tau:.2f}: P0={z/REPS:.3f}  reads reachable (a) " + " ".join(
                f"{dl}: {ra[dl]/REPS:.3f}" for dl in ra) + f"   (MC s.e. <= {0.5/math.sqrt(REPS):.3f})")


main()
