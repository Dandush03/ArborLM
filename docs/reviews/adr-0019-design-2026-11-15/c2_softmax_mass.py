"""C2 (auditor, Opus 5.5) -- synthetic, no data, no backbone. Key width 16, cosine scores.

(a) A4 (soft-to-hard curriculum): with the read softmax(a/tau) over ALL N slots, how much weight falls on the
    query's own (best) key and on its top 8, at tau = 0.2 (the end of the anneal) and at other tau? Best case for
    the curriculum: the query equals its target key exactly (score 1). Keys: (i) i.i.d. uniform on the sphere
    (spread memory), (ii) the same, but every key is pushed to score <= c with every other fact's query is impossible
    to arrange for all queries at once in 16 dimensions; we report (i) only and the exact expectation
    E[exp(a/tau)] for a uniform direction, which is what the bulk contributes on average over queries for ANY key set
    whose directions are uniformly spread.
(b) A1's address loss: L_addr = -log softmax_s(a_s / tau_a)[target], tau_a = 0.2, over all N slots. Its floor at
    the best case (query == target key, other keys uniform), and its gradient with respect to the query at that point.
(c) Mean pairwise cosine of centred, normalised vectors (A5): a fully slot-collapsed query set whose fact-dependent
    residual is rank 1 or 2 still has mean cosine about 0 after centring, so 'mean query cosine' cannot detect
    collapse for A5.
"""
import math

import torch

torch.manual_seed(0)
D = 16


def uniform_exp_moment(t, d=D, grid=200001):
    # E[exp(a/t)] for a = first coordinate of a uniform unit vector in R^d: density ∝ (1-a^2)^((d-3)/2)
    a = torch.linspace(-1, 1, grid, dtype=torch.float64)
    w = (1 - a**2).clamp_min(0) ** ((d - 3) / 2)
    return float((w * torch.exp(a / t)).sum() / w.sum())


print("== (a) soft read over all N slots, query == its target key (score 1), other keys uniform on S^15")
print("   E[exp(a/0.2)] for a uniform direction =", round(uniform_exp_moment(0.2), 4))
for n in (4096, 16384, 65536):
    keys = torch.nn.functional.normalize(torch.randn(n, D), dim=-1)
    q = keys[0]
    a = keys @ q
    for tau in (5.0, 1.0, 0.2, 0.1, 0.05, 0.02):
        w = torch.softmax(a / tau, 0)
        top8 = w.topk(8).values.sum()
        expected_target = math.exp(1 / tau) / (math.exp(1 / tau) + (n - 1) * uniform_exp_moment(tau))
        print(f"   N={n:6d} tau={tau:5.2f}: weight on target {float(w[0]):.4f} (expected {expected_target:.4f}); "
              f"on top-8 {float(top8):.4f}; outside top-8 {1 - float(top8):.4f}")

print("\n== (b) A1 address loss floor at tau_a = 0.2 (query == target key; other keys uniform)")
for n in (4096, 16384, 65536):
    keys = torch.nn.functional.normalize(torch.randn(n, D, dtype=torch.float64), dim=-1)
    q = keys[0].clone().requires_grad_(True)
    loss = -torch.log_softmax((keys @ q) / 0.2, 0)[0]
    loss.backward()
    g = q.grad
    g_tan = g - (g @ keys[0]) * keys[0]  # component the normalisation passes on
    print(f"   N={n:6d}: L_addr = {float(loss):.3f} nats (ln N = {math.log(n):.3f}); |dL/dq| = {float(g.norm()):.3f}, "
          f"tangential {float(g_tan.norm()):.3f}; target is top-1: True by construction")
print("   Reading: the loss cannot fall below about ln N - 5 + ln E[exp(5a)], so it never saturates and keeps a")
print("   gradient of order 1/tau_a on every key in the softmax bulk for the whole run (a perpetual key-spreading term).")

print("\n== (c) mean pairwise cosine before and after centring (A5)")
n = 512
common = torch.nn.functional.normalize(torch.randn(D), dim=0) * 10.0
v = torch.nn.functional.normalize(torch.randn(D), dim=0)
u = torch.nn.functional.normalize(torch.randn(D), dim=0)
for name, resid in (
    ("rank-1 residual (+/- v)", torch.where(torch.rand(n, 1) < 0.5, 1.0, -1.0) * v),
    ("rank-2 residual", torch.randn(n, 1) * v + torch.randn(n, 1) * u),
    ("isotropic residual (healthy)", torch.randn(n, D) / math.sqrt(D)),
):
    z = common + resid
    def mean_cos(x):
        x = torch.nn.functional.normalize(x, dim=-1)
        s = x.sum(0)
        return float((s @ s - n) / (n * (n - 1)))
    zc = z - z.mean(0)
    ev = torch.linalg.eigvalsh(torch.cov(zc.T))
    pr = float(ev.sum() ** 2 / (ev**2).sum())
    print(f"   {name:30s}: raw mean cos {mean_cos(z):.3f}; centred mean cos {mean_cos(zc):+.3f}; participation-ratio rank {pr:.2f}")
