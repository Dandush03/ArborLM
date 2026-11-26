# ruff: noqa
"""Review 2: does 'with the other form [CR0, divisor G] every figure of table (b) rises by 0.0004 to 0.0008'
(draft 2, section 6, rules used) hold at G = 5, 8, 10? Review 1 measured that range at G = 11 to 19 only.
CR0 SE = CR1 SE * sqrt((G-1)/G), so the test passes iff the noncentral t statistic exceeds t_{0.95,G-1} sqrt((G-1)/G).
Standard library only; the numerical routines are copied from arithmetic_review2.py in this folder (same author).
Also prints table (b) at G = 3, 4 (below the draft's range; section 12 item 11 says a part may end below 5).
"""
import math
import sys

def Phi(x):
    return 0.5 * math.erfc(-x / math.sqrt(2))

def bisect(f, lo, hi, it=60):
    flo = f(lo)
    for _ in range(it):
        mid = (lo + hi) / 2
        fm = f(mid)
        if (fm > 0) == (flo > 0):
            lo, flo = mid, fm
        else:
            hi = mid
    return (lo + hi) / 2

def nct_sf(t, nu, lam, npts=6000):
    hi = math.sqrt(nu) + 14
    h = hi / npts
    logc = -((nu / 2 - 1) * math.log(2) + math.lgamma(nu / 2))
    tot = 0.0
    for i in range(npts + 1):
        u = i * h
        f = (0.0 if nu > 1 else math.exp(logc)) if u == 0 else math.exp(logc + (nu - 1) * math.log(u) - u * u / 2)
        w = 1 if i in (0, npts) else (4 if i % 2 else 2)
        tot += w * f * Phi(lam - t * u / math.sqrt(nu))
    return tot * h / 3

TARGET = 1 - 0.2 / 55
def tq(G):
    return bisect(lambda t: (1 - nct_sf(t, G - 1, 0.0)) - 0.95, 0, 50)

def tau_star(G, dl, cr0):
    t = tq(G) * (math.sqrt((G - 1) / G) if cr0 else 1.0)
    pw = lambda tau: nct_sf(t, G - 1, dl * math.sqrt(G) / math.sqrt(tau * tau + 0.3 * G / 20000))
    if pw(0.0) < TARGET:
        return None
    return bisect(lambda tau: pw(tau) - TARGET, 0.0, 0.5, it=45)

print("python", sys.version.split()[0])
for G in [3, 4, 5, 8, 10, 13, 19]:
    row = []
    for dl in [0.02, 0.03, 0.05]:
        a, b = tau_star(G, dl, False), tau_star(G, dl, True)
        fa = "none" if a is None else f"{a:.4f}"
        fb = "none" if b is None else f"{b:.4f}"
        diff = "" if (a is None or b is None) else f" (+{b-a:.4f})"
        row.append(f"d={dl}: CR1 {fa} CR0 {fb}{diff}")
    print(f"G={G}: " + " | ".join(row))
