# ruff: noqa
"""What choice 18 decides at small G (reviewer's own code, standard library only; normal approximation for the M0
cluster means, s_w^2 treated as known). Illustrative: ADR-0033 does not define tau_hat's 90 % interval below 30
clusters (line 457 says "cluster-bootstrap"; line 435 replaces the percentile bootstrap below 30 clusters but names no
interval for a variance component). The reviewer uses the chi-square interval for the between-cluster variance, an
ASSUMPTION, to show the order of magnitude only.

M0 draw: G clusters, m = 1500/G items each, d = 0.3. V = sample variance (divisor G-1) of the cluster means;
V (G-1) / (tau^2 + sw2/m) ~ chi2(G-1).
 (a) point estimate: tau_hat^2 = max(0, V - sw2/m).
 (b) upper end of a two-sided 90 % interval: tau_up^2 = max(0, V (G-1) / chi2_{0.05,G-1} - sw2/m).
A part reads "reachable at delta within the 20,000 pool" when the tau used is at most tau_crit(delta, G), the largest
tau at which the exact noncentral-t power at n = 20,000 meets 1 - 0.2/55 (values from power_exact_review.out.txt,
CR1, sw2 = d). P(reachable) = P(chi2(G-1) <= x) for the matching x.
Run: uv run --locked python docs/reviews/adr-0033-m0-2026-11-20/addendum1_review1/choice18_review.py
"""
import math

TAU_CRIT = {  # from power_exact_review.out.txt, M = 55, CR1, sw2 = d
    11: {0.02: 0.0060, 0.03: 0.0170, 0.05: 0.0331},
    13: {0.02: 0.0071, 0.03: 0.0189, 0.05: 0.0366},
    15: {0.02: 0.0079, 0.03: 0.0206, 0.05: 0.0397},
    19: {0.02: 0.0094, 0.03: 0.0236, 0.05: 0.0453},
}
TRUE_POWER_REACHED = {}  # filled for the printout: is the truth itself reachable?


def chi2_pdf(v, nu):
    if v <= 0:
        return 0.0
    return math.exp((nu / 2 - 1) * math.log(v) - v / 2 - (nu / 2) * math.log(2) - math.lgamma(nu / 2))


def chi2_cdf(x, nu, steps=6000):
    if x <= 0:
        return 0.0
    h = x / steps
    s = sum((1 if i in (0, steps) else (4 if i % 2 else 2)) * chi2_pdf(i * h, nu) for i in range(steps + 1))
    return s * h / 3


def chi2_q(p, nu):
    lo, hi = 0.0, 200.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if chi2_cdf(mid, nu) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def main():
    d = 0.3
    for G in (11, 13, 15, 19):
        nu = G - 1
        m = 1500 / G
        q05 = chi2_q(0.05, nu)
        print(f"== G={G}, m={m:.1f}, chi2_0.05,{nu} = {q05:.3f}")
        for tau in (0.0, 0.01, 0.02, 0.03, 0.05, 0.10):
            sw2 = d - tau * tau
            a = sw2 / m
            scale = tau * tau + a
            row_a, row_b = [], []
            for dl in (0.02, 0.03, 0.05):
                tc2 = TAU_CRIT[G][dl] ** 2
                # (a) tau_hat^2 <= tc2  <=>  V <= tc2 + a  <=>  chi2 <= nu (tc2 + a)/scale
                pa = chi2_cdf(nu * (tc2 + a) / scale, nu)
                # (b) V nu / q05 - a <= tc2  <=>  chi2 <= q05 (tc2 + a)/scale
                pb = chi2_cdf(q05 * (tc2 + a) / scale, nu)
                truth = "truly reachable" if tau <= TAU_CRIT[G][dl] else "truly NOT reachable"
                row_a.append(f"d={dl}: {pa:.3f}")
                row_b.append(f"d={dl}: {pb:.3f} ({truth})")
            print(f"  true tau={tau:.2f}  P(reads reachable) (a) point: " + "  ".join(row_a))
            print(f"                     (b) upper bound: " + "  ".join(row_b))


if __name__ == "__main__":
    main()
