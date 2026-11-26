"""Review 3 of ADR-0033 addendum 1, draft 3: independent recomputation of section 6 (a), (b), (c), the CR0 effect,
G = 3 and 4, power at tau = 0, and of the capacity arithmetic of section 10 (D, D_lin, D_w, shares, 9.3 figures).

Standard library only; imports nothing from studies/ or from any drafter or reviewer script.
Model (section 6 'rules used'): per-cluster mean of the paired difference ~ N(0, tau^2 + d/m), m = 20000/G,
d = 0.3, mu = 0. Test passes if est - t_{0.95,G-1} * SE > -delta. CR1: SE = sample sd (divisor G-1) / sqrt(G);
CR0: SE = sd with divisor G over sqrt(G) = CR1 * sqrt((G-1)/G). Exact power = P(T' > c) with T' noncentral t,
computed by numerical integration over the chi distribution. Target 1 - 0.2/55.
"""

import math

D = 0.3
POOL = 20_000
M_E = 55
TARGET = 1 - 0.2 / M_E


def Phi(x):
    return 0.5 * math.erfc(-x / math.sqrt(2))


def z(p):
    lo, hi = -40.0, 40.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if Phi(mid) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def s_density(s, nu):
    # density of S = sqrt(V/nu), V ~ chi2_nu
    if s <= 0:
        return 0.0
    v = nu * s * s
    logf = (nu / 2 - 1) * math.log(v) - v / 2 - (nu / 2) * math.log(2) - math.lgamma(nu / 2)
    return math.exp(logf) * 2 * nu * s


def nct_sf(c, nu, ncp, n=6000, smax=None):
    """P((Z + ncp)/S > c) = E_S[ Phi(ncp - c S) ]."""
    if smax is None:
        smax = 1 + 14 / math.sqrt(nu) + 4
    h = smax / n
    tot = 0.0
    for i in range(n + 1):
        s = i * h
        w = 1 if i in (0, n) else (4 if i % 2 else 2)
        tot += w * s_density(s, nu) * Phi(ncp - c * s)
    return tot * h / 3


_tq = {}


def tq(p, nu):
    key = (p, nu)
    if key not in _tq:
        lo, hi = 0.0, 50.0
        for _ in range(80):
            mid = (lo + hi) / 2
            if 1 - nct_sf(mid, nu, 0.0) < p:
                lo = mid
            else:
                hi = mid
        _tq[key] = (lo + hi) / 2
    return _tq[key]


def power(G, tau, delta, form="CR1", n=POOL):
    nu = G - 1
    m = n / G
    sd_mean = math.sqrt(tau * tau + D / m)
    ncp = delta / (sd_mean / math.sqrt(G))
    c = tq(0.95, nu)
    if form == "CR0":
        c = c * math.sqrt((G - 1) / G)
    return nct_sf(c, nu, ncp)


def max_tau(G, delta, form="CR1"):
    if power(G, 0.0, delta, form) < TARGET:
        return None
    lo, hi = 0.0, 0.5
    for _ in range(40):
        mid = (lo + hi) / 2
        if power(G, mid, delta, form) >= TARGET:
            lo = mid
        else:
            hi = mid
    return lo


def min_delta(G, tau, form="CR1"):
    lo, hi = 0.0, 2.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if power(G, tau, mid, form) >= TARGET:
            hi = mid
        else:
            lo = mid
    return hi


print(f"target 1-0.2/55 = {TARGET:.6f}; z0.95 + z_target = {z(0.95) + z(TARGET):.4f}")
print("check t quantiles: t0.95 df=4", round(tq(0.95, 4), 4), "(2.1318); df=12", round(tq(0.95, 12), 4), "(1.7823)")
GS = (5, 8, 10, 13, 19)
print("== (a) floor: largest tau = delta*sqrt(G)/4.3289")
zz = z(0.95) + z(TARGET)
for dl in (0.02, 0.03, 0.05):
    print(f"  delta {dl}: " + "  ".join(f"G={G}: {dl * math.sqrt(G) / zz:.3f}" for G in GS))
print("== (b) largest tau with power >= target inside 20,000, t test, CR1 and CR0, and CR0 - CR1")
for dl in (0.02, 0.03, 0.05):
    row = []
    for G in (3, 4) + GS:
        a = max_tau(G, dl, "CR1")
        b = max_tau(G, dl, "CR0")
        fa = "none" if a is None else f"{a:.4f}"
        fb = "none" if b is None else f"{b:.4f}"
        dd = "" if (a is None or b is None) else f" (+{b - a:.4f})"
        row.append(f"G={G}: {fa} / {fb}{dd}")
    print(f"  delta {dl}: " + "; ".join(row))
print("== power at tau = 0, delta = 0.02, CR1 (and CR0)")
for G in (3, 4, 5, 6, 8, 10, 11, 13, 19):
    print(f"  G={G}: {power(G, 0.0, 0.02):.4f} ({power(G, 0.0, 0.02, 'CR0'):.4f})")
print("== (c) smallest delta reachable inside 20,000, CR1")
for tau in (0.03, 0.05, 0.10):
    print(f"  tau {tau}: " + "  ".join(f"G={G}: {min_delta(G, tau):.3f}" for G in GS))

print("== capacity arithmetic (section 10)")
c = math.ceil


def Dg(G):
    return 10 * (c(4000 / G) + c(20000 / G) + 100)


def Dlin(G, k):
    return 10 * (c(c(4000 / G) / k) + c(c(20000 / G) / k) + c(100 / k))


for G in (1, 2, 3, 4, 5, 8, 10, 11, 13, 14, 15, 19, 300):
    print(f"  D({G}) = {Dg(G):,}")
print(f"  D(G)/D(300) for G 19..5: {Dg(19) / Dg(300):.2f} .. {Dg(5) / Dg(300):.2f}")
print(f"  D_lin(10,2) = {Dlin(10, 2):,}; D_lin(13,3) = {Dlin(13, 3):,}")
for G in (1, 2, 3, 4):
    print(f"  D_lin({G}, k=1..3) = " + ", ".join(f"{Dlin(G, k):,}" for k in (1, 2, 3)))
for L in (3, 5, 8, 10, 12, 15, 20, 25, 30):
    print(f"  D_w({L}) = {Dg(L):,}")
# does every lineage meeting D_lin imply the cluster meets D (no collisions)?
bad = [(G, k) for G in range(1, 40) for k in range(1, 8) if k * Dlin(G, k) < Dg(G)]
print("  (G,k) with k*D_lin < D (cluster condition not implied by lineage conditions):", bad[:10], len(bad))
print("  part E / table C shares: 3/10 =", 3 / 10, "; 4/15 =", round(4 / 15, 3), "; 4/9 =", round(4 / 9, 3),
      "; 1/7 =", round(1 / 7, 3))
print(f"  9.3: M0 draw 1500/G at G=19..5: {1500 / 19:.1f} .. {1500 / 5:.0f}; sealed 20000/G: {20000 / 19:.1f} .. {20000 / 5:.0f}")
