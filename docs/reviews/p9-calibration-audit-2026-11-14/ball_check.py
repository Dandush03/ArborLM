"""Audit item 3 follow-up: the LayerNorm output u satisfies ||u||^2 = 32 var/(var + eps) <= 32, so if the
added delta cancels the residual's spread the reachable set is the BALL, not only the sphere. Maximum
full-softmax probability per symbol over the mean-zero ball ||u|| <= sqrt(32) (radius parametrised by
a sigmoid), weighted by the 2,048-fact Panel A answer distribution as in attainable_check.py.
"""

import json

import _common as c
import torch

R = 32**0.5


def pmax_ball(bb, a, restarts=32, steps=1500):
    g = torch.Generator().manual_seed(900 + a)
    v = torch.randn(restarts, 32, generator=g, dtype=torch.float64)
    r = torch.zeros(restarts, 1, dtype=torch.float64)
    v.requires_grad_(True)
    r.requires_grad_(True)
    opt = torch.optim.Adam([v, r], lr=0.05)
    E = bb.token.weight.double()
    gam, bet = bb.final_norm.weight.double(), bb.final_norm.bias.double()
    best = 0.0
    for _ in range(steps):
        p = v - v.mean(-1, keepdim=True)
        u = R * torch.sigmoid(r) * p / p.norm(dim=-1, keepdim=True)
        lp = ((gam * u + bet) @ E.T).log_softmax(-1)[:, c.ALPHABET[a]]
        best = max(best, float(lp.detach().exp().max()))
        opt.zero_grad()
        (-lp.sum()).backward()
        opt.step()
    return best


def main():
    s = c.study()
    _, ids = c.restrict(s.streams["panel_a"], 2048)
    w = torch.bincount(s.facts.answer[ids.reshape(-1)], minlength=32).double()
    w = w / w.sum()
    out = {}
    for parent in ("b101", "b102"):
        bb = c.backbone(parent)
        pm = torch.tensor([pmax_ball(bb, a) for a in range(32)], dtype=torch.float64)
        out[parent] = {"pmax_ball": pm.tolist(), "weighted_mean": float((w * pm).sum()), "fraction_symbols_ge_0.95": float((pm >= 0.95).double().mean())}
        print(parent, out[parent]["weighted_mean"])
    (c.OUT / "ball_check.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
