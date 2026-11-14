"""Indicative timing only: an ad hoc stand-in for the memory forward/backward/AdamW step.
Not ArborLM code, no real data, no model quality. Machine not isolated."""
import json, resource, sys, time
import torch
import torch.nn.functional as F
N, kind, Q, threads = int(sys.argv[1]), sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
torch.set_num_threads(threads); torch.manual_seed(0)
keys = torch.nn.Parameter(torch.randn(N, 16) * 0.02)
vals = torch.nn.Parameter(torch.randn(N, 32) * 0.02)
wq = torch.nn.Parameter(torch.randn(16, 32) * 0.02)
B = N // 256
router = torch.nn.Parameter(torch.randn(B, 16) * 0.02)
ps = [keys, vals, wq] + ([router] if kind == "tree" else [])
opt = torch.optim.AdamW(ps, lr=0.003, weight_decay=0, foreach=False)
def step():
    h = torch.randn(Q, 32)
    q = F.normalize(h @ wq.T, dim=-1)
    if kind == "flat":
        s = q @ F.normalize(keys, dim=-1).T / 0.2
        w, idx = s.topk(8)
    else:
        r = q @ F.normalize(router, dim=-1).T / 0.2
        _, b = r.topk(2)
        cand = (b[..., None] * 256 + torch.arange(256)).flatten(1)
        local = F.normalize(keys[cand], dim=-1)
        s = torch.bmm(local, q.unsqueeze(-1)).squeeze(-1) / 0.2
        w, j = s.topk(8); idx = cand.gather(-1, j)
    out = (w.softmax(-1)[..., None] * vals[idx]).sum(1)
    loss = (out - h).pow(2).mean()
    opt.zero_grad(set_to_none=True); loss.backward(); opt.step()
for _ in range(3): step()
t = time.perf_counter(); n = 15
for _ in range(n): step()
dt = (time.perf_counter() - t) / n
print(json.dumps({"slots": N, "kind": kind, "positions": Q, "threads": threads, "s_per_update": round(dt, 4),
                  "maxrss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20, 1)}))
