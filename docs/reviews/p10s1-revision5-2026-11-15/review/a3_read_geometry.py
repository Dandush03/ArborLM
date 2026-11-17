"""Auditor check A3: is a top-8 / temperature-0.2 cosine read over 256 slots a sound store, compared with 1,024 / 4,096 / 16,384?
And how crowded are the oracle codes (random unit vectors, width 16) at 2,048 / 8,192 / 32,768 / 131,072 facts?

Geometry at initialization only (keys N(0, 0.02) normalised = uniform random unit vectors in R^16, as studies/p9/model.py does;
oracle codes are fixed random unit vectors of width 16). This is not the trained system and predicts no accuracy.
torch only (in uv.lock): uv run --locked python -I a3_read_geometry.py (attempt 1 used numpy, which is not in the lock, and failed).
Seeded: 941777 (an auditor-only seed outside every S1 range; no study generator is used).
"""
import math

import torch

g = torch.Generator().manual_seed(941777)
torch.set_num_threads(4)
KW, TOP, T = 16, 8, 0.2


def unit(n):
    x = torch.randn(n, KW, generator=g, dtype=torch.float64)
    return x / x.norm(dim=1, keepdim=True)


print("## 1. Read at initialisation: top-8 cosines, softmax(score/0.2) over the top 8, 4,000 random queries")
print("  N      top1cos  8thcos  9thcos  gap8-9   w_top1  eff_slots(1/sum w^2)  share of store read  facts sharing >=1 slot with a fact (load 8)")
for n in (256, 1024, 4096, 16384):
    keys = unit(n)
    q = unit(4000)
    s = q @ keys.T
    part = s.topk(9, dim=1).values
    w = (part[:, :8] / T).softmax(dim=1)
    eff = 1 / (w ** 2).sum(dim=1)
    facts = 8 * n
    # expected facts (other than f) whose top-8 set meets f's, if each slot is used by 64 facts at load 8 and sets were random
    p_disjoint = math.prod((n - 8 - k) / (n - k) for k in range(8))
    print(f"  {n:6d} {part[:, 0].mean().item():7.3f} {part[:, 7].mean().item():7.3f} {part[:, 8].mean().item():7.3f} {(part[:, 7] - part[:, 8]).mean().item():7.4f} {w[:, 0].mean().item():8.3f} {eff.mean().item():10.2f}            {8 / n:8.4f}            {(1 - p_disjoint) * (facts - 1):8.0f} of {facts - 1} ({1 - p_disjoint:.3f})")

print("\n## 2. Oracle-code crowding (random unit codes, width 16): nearest-neighbour cosine among the cell's facts")
print("  facts    mean NN cos  p50    p99    share with a neighbour above 0.8   above 0.9")
for f in (2048, 8192, 32768, 131072):
    c = unit(f).float()
    nn = torch.empty(f)
    for a in range(0, f, 4096):
        s = c[a:a + 4096] @ c.T
        idx = torch.arange(s.shape[0])
        s[idx, a + idx] = -2
        nn[a:a + 4096] = s.max(dim=1).values
    print(f"  {f:7d}  {nn.mean():10.3f}  {nn.median():5.3f}  {nn.quantile(0.99):5.3f}  {(nn > 0.8).float().mean():10.3f}                         {(nn > 0.9).float().mean():6.3f}")
