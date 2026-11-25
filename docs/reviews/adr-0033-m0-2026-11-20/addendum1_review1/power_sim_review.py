# ruff: noqa
"""Direct simulation (reviewer's own code; locked torch only; imports nothing from studies/) of ADR-0033 section 9.4
as the reviewer reads it, one stratum per private part (addendum 1, section 9 item 1), at small G.

Synthetic truth: paired difference D in {-1, 0, +1}; cluster g has mean u_g ~ N(0, tau^2) (clipped to |u| <= d),
P(D=+1) = (d+u)/2, P(D=-1) = (d-u)/2, so discordance d and within-cluster variance d - u^2.

Part A, "known power": the M5 test on fresh clusters and items, n = 20,000 over G clusters (sizes as even as integers
allow), passes if mean - t_{0.95,G-1} * SE_CR1 > -delta. Checks the exact noncentral-t figures with discrete outcomes.

Part B, "the registered reading": synthetic M0 draws of 1,500 items balanced over G clusters. For each draw: tau_hat^2 =
max(0, V - s_w^2 * mean(1/m_g)) (V sample variance of cluster means, divisor G-1; s_w^2 pooled within variance); the
floor; and pi(20,000, delta) by the two-stage simulation of 9.4 (shrunk deviations lambda_g (xbar_g - xbar), residuals
scaled by sqrt(m/(m-1)), estimate and SE scaled by sqrt(d_e/(d_e - mu^2)), t on G-1 df). The part reads
"reachable at delta within the pool" when the floor and pi(20,000) both meet 1 - 0.2/55. Printed: share of M0 draws
with tau_hat = 0, and share reading reachable, against the true per-test power at that tau.

Run: uv run --locked python docs/reviews/adr-0033-m0-2026-11-20/addendum1_review1/power_sim_review.py
"""
import math
import sys
from statistics import NormalDist

import torch

N = NormalDist()
TARGET = 1 - 0.2 / 55
Z95 = N.inv_cdf(0.95)
D = 0.3
TQ = {10: 1.8125, 12: 1.7823, 13: 1.7709, 14: 1.7613, 18: 1.7341}  # t_{0.95,nu}, printed tables; checked below


def t_q(nu):
    # check against the stdlib integrator of power_exact_review.py would need an import; use torch's StudentT icdf
    # is not implemented, so bisection on a numerically integrated cdf:
    lo, hi = 0.0, 10.0
    for _ in range(60):
        mid = (lo + hi) / 2
        # P(T <= mid) via regularised incomplete beta by series is long; use numeric integration of the t density
        xs = torch.linspace(0, mid, 20001, dtype=torch.float64)
        dens = torch.exp(torch.lgamma(torch.tensor((nu + 1) / 2, dtype=torch.float64)) - torch.lgamma(torch.tensor(nu / 2, dtype=torch.float64))
                         - 0.5 * math.log(nu * math.pi) - (nu + 1) / 2 * torch.log1p(xs * xs / nu))
        cdf = 0.5 + float(torch.trapezoid(dens, xs))
        if cdf < 0.95:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def sizes(total, g):
    base = [total // g] * g
    for i in range(total - sum(base)):
        base[i] += 1
    return torch.tensor(base, dtype=torch.float64)


def draw_cluster_sums(u, m, gen):
    """u: (R, G) cluster means; m: (G,) items per cluster. Returns sums of D per cluster, and the counts (+, -)."""
    R, G = u.shape
    mm = m.view(1, G).expand(R, G)
    p_disc = torch.full_like(u, D)
    k_disc = torch.binomial(mm, p_disc, generator=gen)
    p_plus = ((D + u) / 2) / D
    k_plus = torch.binomial(k_disc, p_plus.clamp(0, 1), generator=gen)
    k_minus = k_disc - k_plus
    return k_plus - k_minus, k_plus, k_minus


def known_power(tau, delta, G, n, reps, gen, tq):
    m = sizes(n, G)
    passes = 0
    done = 0
    while done < reps:
        R = min(20000, reps - done)
        u = (torch.randn(R, G, generator=gen, dtype=torch.float64) * tau).clamp(-D, D)
        s, _, _ = draw_cluster_sums(u, m, gen)
        tot = m.sum()
        est = s.sum(1) / tot
        ss = ((s - m.view(1, -1) * est.view(-1, 1)) ** 2).sum(1)
        se = torch.sqrt(ss * G / (G - 1)) / tot
        passes += int(((est - tq * se) > -delta).sum())
        done += R
    p = passes / reps
    return p, math.sqrt(p * (1 - p) / reps)


def registered_reading(tau, G, deltas, n, m0_draws, sims, gen, tq):
    m = sizes(1500, G)
    out = {"trunc": 0, "reach": {dl: 0 for dl in deltas}, "tauhat": []}
    for _ in range(m0_draws):
        u = (torch.randn(1, G, generator=gen, dtype=torch.float64) * tau).clamp(-D, D)
        s, kp, km = draw_cluster_sums(u, m, gen)
        s, kp, km = s[0], kp[0], km[0]
        xbar = s / m
        # per-item second moment: E[D^2] = (kp + km)/m
        ssw_g = (kp + km) - m * xbar * xbar  # sum of squared deviations within cluster
        s_w2 = float(ssw_g.sum() / (m - 1).sum())
        V = float(xbar.var(unbiased=True))
        tau2 = max(0.0, V - s_w2 * float((1 / m).mean()))
        out["tauhat"].append(math.sqrt(tau2))
        if tau2 == 0:
            out["trunc"] += 1
        mu = float(s.sum() / m.sum())
        d_e = float((kp + km).sum() / m.sum())
        scale = math.sqrt(d_e / (d_e - mu * mu))
        lam = torch.sqrt(tau2 / (tau2 + s_w2 / m)) if tau2 > 0 else torch.zeros(G, dtype=torch.float64)
        dev = lam * (xbar - xbar.mean())
        # pooled residual distribution: in cluster g, value (x - xbar_g) * sqrt(m/(m-1)) for x in {+1, 0, -1}
        c = torch.sqrt(m / (m - 1))
        vals = torch.stack([(1 - xbar) * c, (0 - xbar) * c, (-1 - xbar) * c], 1).reshape(-1)
        wts = torch.stack([kp, m - kp - km, km], 1).reshape(-1)
        probs = wts / wts.sum()
        n_g = sizes(n, G)
        # simulate: sims samples, G clusters drawn with replacement; per cluster sum of n_g residual draws.
        # sum of n_g draws from a finite distribution = multinomial counts . vals; exact via sequential binomials.
        idx = torch.randint(0, G, (sims, G), generator=gen)
        tot_items = n_g.view(1, G).expand(sims, G).clone()
        remaining = tot_items.clone()
        rem_p = torch.ones(sims, G, dtype=torch.float64)
        resid_sum = torch.zeros(sims, G, dtype=torch.float64)
        K = probs.numel()
        for k in range(K):
            pk = probs[k]
            if k == K - 1:
                cnt = remaining
            else:
                q = (pk / rem_p).clamp(0, 1)
                cnt = torch.binomial(remaining, q, generator=gen)
            resid_sum += cnt * vals[k]
            remaining = remaining - cnt
            rem_p = rem_p - pk
            rem_p = torch.clamp(rem_p, min=1e-300)
        sums = dev[idx] * n_g.view(1, G) + resid_sum
        tot = float(n_g.sum())
        est = sums.sum(1) / tot
        ss = ((sums - n_g.view(1, -1) * est.view(-1, 1)) ** 2).sum(1)
        se = torch.sqrt(ss * G / (G - 1)) / tot
        th = math.sqrt(tau2)
        for dl in deltas:
            floor = 1.0 if th == 0 else N.cdf(dl * math.sqrt(G) / th - Z95)
            pi = float(((scale * est - tq * scale * se) > -dl).double().mean())
            if floor >= TARGET and pi >= TARGET:
                out["reach"][dl] += 1
    return out


def main():
    torch.set_num_threads(4)
    gen = torch.Generator().manual_seed(20261125)
    for nu in (10, 12, 14, 18):
        print(f"t_0.95,{nu}: integrated {t_q(nu):.4f}  table {TQ[nu]}")
    tq = {G: t_q(G - 1) for G in (11, 13, 15, 19)}
    print("\n== A. known power, n = 20,000, d = 0.3, discrete outcomes, 400,000 reps each (exact noncentral t beside)")
    cases = [(13, 0.0071, 0.02, 0.9964), (13, 0.0189, 0.03, 0.9964), (13, 0.0366, 0.05, 0.9964),
             (13, 0.02, 0.02, 0.8726), (13, 0.03, 0.02, 0.6588), (13, 0.05, 0.05, 0.9477),
             (19, 0.05, 0.05, 0.9899), (19, 0.0453, 0.05, 0.9964), (11, 0.0331, 0.05, 0.9964)]
    for G, tau, dl, exact in cases:
        p, se = known_power(tau, dl, G, 20000, 400000, gen, tq[G])
        print(f"  G={G} tau={tau} delta={dl}: simulated {p:.4f} (MC se {se:.4f}); exact {exact}")
    sys.stdout.flush()
    print("\n== B. registered reading from synthetic M0 draws (1,500 items over G clusters), point estimate tau_hat")
    print("   share of draws with tau_hat = 0, and share reading 'reachable within 20,000' at each delta; 4,000 sims per draw")
    for G in (13,):
        for tau in (0.0, 0.01, 0.03, 0.05, 0.10):
            R = 400
            o = registered_reading(tau, G, (0.02, 0.03, 0.05), 20000, R, 4000, gen, tq[G])
            th = sorted(o["tauhat"])
            print(f"  G={G} true tau={tau:.2f}: P(tau_hat=0)={o['trunc'] / R:.3f}; tau_hat median {th[R // 2]:.4f}, 90th pct {th[int(0.9 * R)]:.4f}; "
                  + "  ".join(f"reach@{dl}={o['reach'][dl] / R:.3f}" for dl in (0.02, 0.03, 0.05)))
            sys.stdout.flush()


if __name__ == "__main__":
    main()
