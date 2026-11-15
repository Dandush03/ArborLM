"""C1 - TOY, no backbone, no study data: can a dense adapter of the D7 shape memorize F random
answers from an ideal identifier window within the ADR-0018 update menu?

This is NOT the D7 arm. The input is the ideal window (one-hot of the 5 identifier symbols, 160 dims,
no context noise), and the adapter's output goes straight to 32-way logits (no frozen block 1, final
norm, tied unembedding or gate), so it is OPTIMISTIC about D7. It answers only: is memorizing F facts
with a w1 [h, in] -> GELU -> w2 [32, h] adapter of the parameter-matched width h hard at U updates of
128 answer sites?

Widths h: parameters of D7 = 256 h + 1 (w1 [h, 224], w2 [32, h], gate) matched to the flat key-16
memory plus the W7 interface: N * 48 + 512 + 1,024 + 1 + 3,072  ->  h = 786 / 3,090 / 12,306.
Here w1 is [h, 160]; h is kept at the matched value.

Usage: uv run --locked python docs/reviews/adr-0018-design-2026-11-14/c1_dense_window_toy.py
"""

import json
import sys
import warnings

warnings.filterwarnings("ignore", message="Failed to initialize NumPy")
import torch
from torch.nn import functional as F

S = 32
torch.set_num_threads(8)


def identifiers(f, seed):
    g = torch.Generator().manual_seed(seed)
    flat = torch.randperm(S**4, generator=g)[:f]
    s4 = torch.stack([(flat // S**k) % S for k in (3, 2, 1, 0)], 1)
    return torch.cat([s4, (s4.sum(1) % S)[:, None]], 1)


def width(slots):
    params = slots * 48 + 512 + 1024 + 1 + 3072
    return (params - 1) // 256


def main():
    sizes = {2048: 4096, 8192: 16384, 32768: 65536}
    for f, slots in sizes.items():
        h = width(slots)
        ids = identifiers(f, 181000 + f)
        x = F.one_hot(ids, S).float().reshape(f, 5 * S)
        g = torch.Generator().manual_seed(181500 + f)
        y = torch.randint(0, S, (f,), generator=g)
        torch.manual_seed(f)
        w1 = torch.nn.Parameter(torch.randn(h, 5 * S) * 0.02)
        w2 = torch.nn.Parameter(torch.randn(S, h) * 0.02)
        opt = torch.optim.AdamW([w1, w2], lr=0.003, weight_decay=0.0)
        order_g = torch.Generator().manual_seed(181900 + f)
        perm, at = torch.randperm(f, generator=order_g), 0
        for u in range(1, 8193):
            if at + 128 > f:
                perm, at = torch.randperm(f, generator=order_g), 0
            b = perm[at : at + 128]
            at += 128
            loss = F.cross_entropy(F.gelu(x[b] @ w1.T) @ w2.T, y[b])
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_([w1, w2], 1.0)
            opt.step()
            if u in (1024, 2048, 4096, 8192):
                with torch.no_grad():
                    acc = float(((F.gelu(x @ w1.T) @ w2.T).argmax(1) == y).float().mean())
                print(json.dumps({"facts": f, "hidden": h, "params": int(w1.numel() + w2.numel()),
                                  "updates": u, "exposures_per_fact": u * 128 // f, "train_accuracy": round(acc, 4)}),
                      flush=True)
    print(json.dumps({"python": sys.version.split()[0], "torch": torch.__version__}))


if __name__ == "__main__":
    main()
