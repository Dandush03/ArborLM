"""Auditor's idealized probe for ADR-0022 review (not an experiment, no real data, no training).

Question: if Memory B's N new slots are appended to Memory A's store and read with ONE top-8
(cosine, temperature 0.2) instead of behind an oracle route, how much of an A query's read weight
lands on B's slots, with A frozen?  This shows whether retention is non-vacuous in such an arm.

Idealization: random 16-dim unit codes per (task, word) as in ADR-0017 R1; each memory's 4,096 keys
are set to the code of the word they serve (slot i -> word i mod W) plus Gaussian noise of std
`noise` per coordinate before normalization (a stand-in for imperfectly trained keys).  Trained keys
will differ; this only bounds the order of magnitude.
"""

import sys

import torch

N, W, KW, TOPK, TEMP = 4096, 2001, 16, 8, 0.2


def unit(x: torch.Tensor) -> torch.Tensor:
    return x / x.norm(dim=-1, keepdim=True)


def run(seed: int, noise: float) -> tuple[float, float, float]:
    g = torch.Generator().manual_seed(seed)
    codes_a = unit(torch.randn(W, KW, generator=g, dtype=torch.float64))
    codes_b = unit(torch.randn(W, KW, generator=g, dtype=torch.float64))
    owner = torch.arange(N) % W
    keys_a = unit(codes_a[owner] + noise * torch.randn(N, KW, generator=g, dtype=torch.float64))
    keys_b = unit(codes_b[owner] + noise * torch.randn(N, KW, generator=g, dtype=torch.float64))
    keys = torch.cat([keys_a, keys_b])
    scores = codes_a @ keys.T  # A queries against the union store
    top, idx = scores.topk(TOPK, dim=-1)
    w = torch.softmax(top / TEMP, dim=-1)
    mass_b = (w * (idx >= N)).sum(-1)
    any_b = (idx >= N).any(-1).double().mean().item()
    return mass_b.mean().item(), (mass_b > 0.10).double().mean().item(), any_b


if __name__ == "__main__":
    print(f"torch {torch.__version__}; N={N} per memory, W={W} codes per task, top-{TOPK}, T={TEMP}")
    print("noise  seed  mean_B_mass  frac_queries_B_mass>0.10  frac_queries_any_B_slot")
    for noise in (0.0, 0.1, 0.3):
        for seed in (1, 2, 3):
            m, f, a = run(seed, noise)
            print(f"{noise:5.1f} {seed:5d} {m:12.4f} {f:26.4f} {a:24.4f}")
    sys.stdout.flush()
