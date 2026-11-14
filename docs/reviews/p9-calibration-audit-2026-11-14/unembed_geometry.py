"""Audit items 2-3: what the frozen final norm and tied unembedding allow, per answer symbol.

At the answer site the logits are z = E (gamma * u + beta), u = LayerNorm-normalised residual after
block 1: u is mean-zero with ||u||^2 = 32 (up to eps). For a large added delta the block-1 attention
and FFN contributions are bounded, so u can approach any point of the sphere S = {1'u = 0,
||u|| = sqrt(32)}: S is exactly the asymptotically reachable set. Per answer symbol a:

  margin(a) = max_{u in S} min_{c in Sigma, c != a} (z_a - z_c)      (> 0: a can be the strict argmax)
     - primal: projected gradient ascent on a soft-min, 64 random restarts + annealing (lower bound)
     - dual certificate on the ball relaxation ||u|| <= sqrt(32) (upper bound):
          for any lambda in the simplex, max_ball sum_c lambda_c (w_c.u + b_c) = R ||P sum lambda_c w_c||
          + sum lambda_c b_c >= margin(a); minimised over lambda by Adam on a softmax parametrisation
  pmax_full(a)  = max_{u in S} softmax_256(z)[a]     (gradient ascent, restarts; lower bound on sup)
  pmax_sigma(a) = max_{u in S} softmax over Sigma of z[a]

Usage: uv run --locked python docs/reviews/p9-calibration-audit-2026-11-14/unembed_geometry.py
"""

import json

import _common as c
import torch

R = 32**0.5
SIG = c.ALPHABET


def project(v):
    return v - v.mean(-1, keepdim=True)


def on_sphere(v):
    v = project(v)
    return R * v / v.norm(dim=-1, keepdim=True)


def logits_of(bb, u):
    return (bb.final_norm.weight * u + bb.final_norm.bias) @ bb.token.weight.T


def primal_margin(bb, a, restarts=64, steps=600, seed=0):
    g = torch.Generator().manual_seed(seed + a)
    v = torch.randn(restarts, 32, generator=g, dtype=torch.float64)
    # include the direction of gamma * e_a as one start
    v[0] = (bb.final_norm.weight * bb.token.weight[SIG[a]]).double()
    v.requires_grad_(True)
    opt = torch.optim.Adam([v], lr=0.05)
    others = torch.tensor([i for i in range(32) if i != a])
    E = bb.token.weight.double()
    gam, bet = bb.final_norm.weight.double(), bb.final_norm.bias.double()
    best = -1e9
    for step in range(steps):
        temp = 1.0 * (0.01 ** (step / steps))
        u = on_sphere(v)
        z = (gam * u + bet) @ E.T
        diff = z[:, SIG[a]][:, None] - z[:, SIG[others]]
        hard = diff.min(1).values
        best = max(best, float(hard.max()))
        soft = -temp * torch.logsumexp(-diff / temp, 1)
        opt.zero_grad()
        (-soft.sum()).backward()
        opt.step()
    return best


def dual_bound(bb, a, steps=3000):
    E = bb.token.weight.double()
    gam, bet = bb.final_norm.weight.double(), bb.final_norm.bias.double()
    others = [i for i in range(32) if i != a]
    W = project(gam * (E[SIG[a]] - E[SIG[others]]))  # [31, 32]
    B = (E[SIG[a]] - E[SIG[others]]) @ bet  # [31]
    th = torch.zeros(31, dtype=torch.float64, requires_grad=True)
    opt = torch.optim.Adam([th], lr=0.05)
    best = float("inf")
    for _ in range(steps):
        lam = th.softmax(0)
        val = R * (lam @ W).norm() + lam @ B
        best = min(best, float(val))
        opt.zero_grad()
        val.backward()
        opt.step()
    return best


def pmax(bb, a, which, restarts=32, steps=800, seed=0):
    g = torch.Generator().manual_seed(seed + 100 + a)
    v = torch.randn(restarts, 32, generator=g, dtype=torch.float64)
    v[0] = (bb.final_norm.weight * bb.token.weight[SIG[a]]).double()
    v.requires_grad_(True)
    opt = torch.optim.Adam([v], lr=0.05)
    E = bb.token.weight.double()
    gam, bet = bb.final_norm.weight.double(), bb.final_norm.bias.double()
    best = 0.0
    for _ in range(steps):
        z = (gam * on_sphere(v) + bet) @ E.T
        lp = z.log_softmax(-1)[:, SIG[a]] if which == "full" else z[:, SIG].log_softmax(-1)[:, a]
        best = max(best, float(lp.exp().max()))
        opt.zero_grad()
        (-lp.sum()).backward()
        opt.step()
    return best


def main():
    out = {}
    for parent in ("b101", "b102"):
        bb = c.backbone(parent)
        rows = []
        for a in range(32):
            row = {
                "symbol": a,
                "byte": int(SIG[a]),
                "char": chr(int(SIG[a])),
                "emb_norm": float(bb.token.weight[SIG[a]].norm()),
                "margin_primal": primal_margin(bb, a),
                "margin_dual_upper": dual_bound(bb, a),
                "pmax_full": pmax(bb, a, "full"),
                "pmax_sigma": pmax(bb, a, "sigma"),
            }
            rows.append(row)
            print(parent, json.dumps(row))
        out[parent] = rows
        pf = torch.tensor([r["pmax_full"] for r in rows])
        print(parent, "mean pmax_full over symbols", float(pf.mean()), "frac >= 0.95", float((pf >= 0.95).float().mean()))
    (c.OUT / "unembed_geometry.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
