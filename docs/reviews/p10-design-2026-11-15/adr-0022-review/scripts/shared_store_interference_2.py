"""Follow-up to shared_store_interference.py: read-weight mass on the query word's own slots,
in A's store alone versus after B's slots are appended (same idealization, noise 0.0 and 0.1).
Also the L1 change of the read weights restricted to A's slots (how much A's read output changes
when B is appended with A frozen, before any B value is considered)."""
import torch

N, W, KW, TOPK, TEMP = 4096, 2001, 16, 8, 0.2


def unit(x):
    return x / x.norm(dim=-1, keepdim=True)


for noise in (0.0, 0.1):
    for seed in (1, 2, 3):
        g = torch.Generator().manual_seed(seed)
        ca = unit(torch.randn(W, KW, generator=g, dtype=torch.float64))
        cb = unit(torch.randn(W, KW, generator=g, dtype=torch.float64))
        owner = torch.arange(N) % W
        ka = unit(ca[owner] + noise * torch.randn(N, KW, generator=g, dtype=torch.float64))
        kb = unit(cb[owner] + noise * torch.randn(N, KW, generator=g, dtype=torch.float64))
        words = torch.arange(W)
        out = []
        dense_w = []
        for keys in (ka, torch.cat([ka, kb])):
            top, idx = (ca @ keys.T).topk(TOPK, dim=-1)
            w = torch.softmax(top / TEMP, dim=-1)
            own = ((idx < N) & (owner[idx.clamp(max=N - 1)] == words[:, None])).double()
            out.append((w * own).sum(-1).mean().item())
            full = torch.zeros(W, keys.shape[0], dtype=torch.float64)
            full.scatter_(1, idx, w)
            dense_w.append(full[:, :N])
        l1 = (dense_w[0] - dense_w[1]).abs().sum(-1).mean().item()
        print(f"noise {noise:.1f} seed {seed}: own-slot mass A-only {out[0]:.4f}, after append {out[1]:.4f}; "
              f"mean L1 change of weights on A slots {l1:.4f}")
