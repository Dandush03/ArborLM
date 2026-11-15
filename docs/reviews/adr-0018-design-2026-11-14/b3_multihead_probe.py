"""B3 - extra variants for the B2 probe (same data, objective, oracle store and read; B2's code is imported
unchanged so its recorded outputs stay valid).

Question: is ADR-0018's A1 failing because it is ONE head (a weighted bag of one shared value map),
and would the backbone's own attention SHAPE (4 heads x 8, as in block 0) expose the identifier at
the answer site? These are interfaces on top of the frozen states, not a retrained backbone.

  A4-16    4 heads x 8 wide (q, k, v 32 x 32 each, bias-free, 3,072 parameters as A1), over h_{t-15..t}
  A4E-16   the same over embeddings e (what a retrained block-0 attention would see, without its FFN)
  A1-16L   A1-16 with 3x the probe steps (checks that A1's result is not optimization-limited)

Usage: PYTHONPATH=docs/reviews/p9-calibration-audit-2026-11-14:docs/reviews/adr-0018-design-2026-11-14 \
       uv run --locked python docs/reviews/adr-0018-design-2026-11-14/b3_multihead_probe.py <parent> <F> [variants]
"""

import math
import sys

import b2_window_query_probe as b2
import torch


class MultiHead(torch.nn.Module):
    def __init__(self, d, heads=4):
        super().__init__()
        self.h = heads
        self.q, self.k, self.v = (torch.nn.Parameter(torch.randn(32, 32) / math.sqrt(32)) for _ in range(3))
        self.w = torch.nn.Parameter(torch.randn(d, 32) / math.sqrt(32))
        self.last_attention = None

    def forward(self, x, mask):
        n, length, _ = x.shape
        hd = 32 // self.h
        q = (x[:, -1] @ self.q.T).reshape(n, self.h, hd)
        k = (x @ self.k.T).reshape(n, length, self.h, hd)
        v = (x @ self.v.T).reshape(n, length, self.h, hd)
        s = torch.einsum("nhd,nlhd->nhl", q, k) / math.sqrt(hd)
        s = s.masked_fill(~mask[:, None, :], float("-inf"))
        a = s.softmax(-1)
        self.last_attention = a.mean(1).detach()
        return torch.einsum("nhl,nlhd->nhd", a, v).reshape(n, 32) @ self.w.T


_make = b2.make
_Head = b2.Head


def make(variant):
    if variant == "A4-16":
        return MultiHead(16), "h", 16
    if variant == "A4E-16":
        return MultiHead(16), "e", 16
    if variant == "A1-16L":
        b2.STEPS = 6000  # run A1-16L in its own process: STEPS is read by b2.main for later variants too
        return _Head(16), "h", 16
    return _make(variant)


b2.make = make
b2.Head = (_Head, MultiHead)  # b2.main's attention report tests isinstance(model, Head); b2.make is replaced

if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.argv += ["A4-16", "A4E-16"]
    b2.main()
