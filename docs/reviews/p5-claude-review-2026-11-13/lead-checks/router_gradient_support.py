"""Lead check (synthetic, float64): which router rows receive gradient in the tree path.

Not a registered experiment. Fresh random Memory("learned_tree", 9002) and random hidden
states; no checkpoint, no dataset. Run:
  uv run --locked --extra pilot python \
    docs/reviews/p5-claude-review-2026-11-13/lead-checks/router_gradient_support.py
"""

import torch

from arborlm.pilot_model import PER_BRANCH, Memory

m = Memory("learned_tree", 9002).double()
g = torch.Generator().manual_seed(9002)
h = torch.randn(4, 64, 32, generator=g, dtype=torch.float64)
N = 256
single = 0
single_max = 0.0
straddle = []
for i in range(N):
    m.zero_grad()
    out, look = m(h)
    (out - h).reshape(N, -1)[i].sum().backward()
    row_norm = m.router.grad.norm(dim=1)
    visited = look.branch_ids[i].tolist()
    selected_branches = set((look.selected[i] // PER_BRANCH).tolist())
    unvisited = max(row_norm[b].item() for b in range(16) if b not in visited)
    if len(selected_branches) == 1:
        single += 1
        single_max = max(single_max, row_norm.max().item() / m.keys.grad.norm().item())
    else:
        straddle.append(unvisited / row_norm[visited].max().item())
print(f"queries={N}")
print(f"queries whose 8 selected slots lie in one branch: {single}")
print(f"  max router-gradient / key-gradient norm ratio for those: {single_max:.3e}")
print(f"queries whose selection spans both visited branches: {len(straddle)}")
print(f"  max unvisited-row / visited-row router-gradient ratio: {max(straddle):.3e}")
