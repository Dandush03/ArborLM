# ruff: noqa
"""Independent recomputation (reviewer's own code, standard library only) of addendum 1, section 6.

Written from ADR-0033 section 9.4 as written, not from the drafter's script.

Model ("normal cluster means"): the M5 sealed sample has G clusters of n/G items each. The paired difference of an
item has mean u_g in cluster g, u_g ~ N(0, tau^2) (true overall difference zero, as the registered simulation makes
it), and within-cluster variance sw2. Cluster means are then N(0, tau^2 + sw2*G/n). The registered test passes if
mean - t_{0.95,G-1} * SE > -delta. With SE = sample sd of the G cluster means / sqrt(G) (the CR1 / "G-1" form) the
statistic (mean + delta)/SE is noncentral t on G-1 df with ncp = delta*sqrt(G)/sqrt(tau^2 + sw2*G/n), so the power
is exact: P(T' > t_{0.95,G-1}).

Variants printed because ADR-0033 does not fix them:
  sw2 = d (section 8's arithmetic) or d - tau^2 (the exact within variance under the cluster model);
  SE in the CR1 form (sample sd, divisor G-1) or the CR0 form (divisor G), i.e. critical value scaled by sqrt((G-1)/G).

Per-test target 1 - 0.2/M, M = 55 (and 70). Pool 20,000 = the top of the ladder, where power is largest.
Run: uv run --locked python docs/reviews/adr-0033-m0-2026-11-20/addendum1_review1/power_exact_review.py
"""
import math
from statistics import NormalDist

N = NormalDist()


def chi2_pdf(v, nu):
    if v <= 0:
        return 0.0
    return math.exp((nu / 2 - 1) * math.log(v) - v / 2 - (nu / 2) * math.log(2) - math.lgamma(nu / 2))


def upper_tail(c, nu, ncp, steps=6000):
    """P((Z + ncp) / sqrt(V/nu) > c), V ~ chi2(nu): integrate over V with composite Simpson."""
    hi = nu + 60 * math.sqrt(2 * nu) + 60
    h = hi / steps
    s = 0.0
    for i in range(steps + 1):
        v = i * h
        w = 1 if i in (0, steps) else (4 if i % 2 else 2)
        s += w * chi2_pdf(v, nu) * (1 - N.cdf(c * math.sqrt(v / nu) - ncp))
    return s * h / 3


def t_quantile(p, nu):
    lo, hi = 0.0, 20.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if 1 - upper_tail(mid, nu, 0.0) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def power(delta, tau, G, n, d, crit, sw_minus_tau=False):
    sw2 = d - tau * tau if sw_minus_tau else d
    sc = math.sqrt(tau * tau + sw2 * G / n)
    return upper_tail(crit, G - 1, delta * math.sqrt(G) / sc)


def largest_tau(delta, G, n, d, crit, target, **kw):
    if power(delta, 0.0, G, n, d, crit, **kw) < target:
        return None
    lo, hi = 0.0, 0.5
    for _ in range(50):
        mid = (lo + hi) / 2
        if power(delta, mid, G, n, d, crit, **kw) >= target:
            lo = mid
        else:
            hi = mid
    return lo


def main():
    GS = (11, 13, 14, 15, 19)
    DELTAS = (0.02, 0.03, 0.05)
    d, n = 0.3, 20000
    print("check: t_{0.95,12} =", round(t_quantile(0.95, 12), 4), "(tables: 1.7823)")
    for M in (55, 70):
        target = 1 - 0.2 / M
        zsum = N.inv_cdf(target) + N.inv_cdf(0.95)
        print(f"\n== M = {M}: per-test target {target:.5f}; normal z sum {zsum:.4f}")
        print("(a) floor as written, largest tau with delta*sqrt(G)/tau >= z sum")
        for de in DELTAS:
            print(f"  delta={de}: " + "  ".join(f"G={G}: {de * math.sqrt(G) / zsum:.4f}" for G in GS))
        crits = {G: t_quantile(0.95, G - 1) for G in GS}
        for label, kw, cr0 in (
            ("CR1 SE, sw2 = d", {}, False),
            ("CR1 SE, sw2 = d - tau^2", {"sw_minus_tau": True}, False),
            ("CR0 SE (divisor G), sw2 = d", {}, True),
        ):
            print(f"(b) exact noncentral t, n = 20,000, d = 0.3, {label}: largest tau at which power >= target")
            for de in DELTAS:
                row = []
                for G in GS:
                    c = crits[G] * (math.sqrt((G - 1) / G) if cr0 else 1.0)
                    lt = largest_tau(de, G, n, d, c, target, **kw)
                    row.append(f"G={G}: {'-' if lt is None else f'{lt:.4f}'}")
                print(f"  delta={de}: " + "  ".join(row))
        print("(b') exact power at n = 20,000, d = 0.3, CR1, sw2 = d")
        for tau in (0.0, 0.02, 0.03, 0.05, 0.10):
            for de in DELTAS:
                print(f"  tau={tau:.2f} delta={de}: " + "  ".join(f"G={G}: {power(de, tau, G, n, d, crits[G]):.4f}" for G in GS))
        if M == 55:
            print("(c) smallest delta reachable, normal formula z sum * sqrt(tau^2/G + d/n), n = 20,000 / n -> inf")
            for tau in (0.03, 0.05, 0.10, 0.15):
                print(f"  tau={tau}: " + "  ".join(
                    f"G={G}: {zsum * math.sqrt(tau * tau / G + d / n):.3f}/{zsum * tau / math.sqrt(G):.3f}" for G in (11, 13, 15, 19)))

    # tau-hat truncation at zero: tau2_hat = max(0, V - sw2_hat/m), V the sample variance (divisor G-1) of G cluster
    # means of m items each. Normal approximation: V*(G-1)/(tau^2 + sw2/m) ~ chi2(G-1), sw2 treated as known.
    print("\n== P(tau_hat = 0): G clusters of m = round(1500/G) M0-draw items, d = 0.3, sw2 = d - tau^2")
    for G in (11, 13, 15, 19):
        m = 1500 / G
        for tau in (0.0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.10):
            sw2 = d - tau * tau
            ratio = (sw2 / m) / (tau * tau + sw2 / m)
            x1 = (G - 1) * ratio          # divisor G-1 (the implementation's pooled V)
            x0 = (G - 1) * ratio * G / (G - 1)  # divisor G (population variance), for comparison
            p1 = 1 - upper_tail(x1, G - 1, 0.0) if False else chi2_cdf(x1, G - 1)
            p0 = chi2_cdf(x0, G - 1)
            print(f"  G={G} m={m:.1f} tau={tau:.2f}: P(trunc) divisor G-1 {p1:.3f}; divisor G {p0:.3f}")


def chi2_cdf(x, nu, steps=4000):
    h = x / steps
    s = 0.0
    for i in range(steps + 1):
        w = 1 if i in (0, steps) else (4 if i % 2 else 2)
        s += w * chi2_pdf(i * h, nu)
    return s * h / 3


if __name__ == "__main__":
    main()
