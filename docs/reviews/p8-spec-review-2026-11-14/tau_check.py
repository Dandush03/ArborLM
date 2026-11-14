"""Verify that check E4 of proxy_checks.py leaves tau and the hard top-8 set unchanged."""

import torch

torch.set_default_dtype(torch.float64)
base = torch.full((64,), -3.0)
sel = [0, 1, 8, 16, 24, 32, 40, 48]
for k, i in enumerate(sel):
    base[i] = 1.0 - 0.05 * k
base[56] = 0.2
for bump in (0.0, 1.0, 2.0, 3.0):
    s = base.clone()
    s[0] += bump
    v = s.topk(9)
    print(bump, "tau", 0.5 * (v.values[7] + v.values[8]).item(), "top8", sorted(v.indices[:8].tolist()))
