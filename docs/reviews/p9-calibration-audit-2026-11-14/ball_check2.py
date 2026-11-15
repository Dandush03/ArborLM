"""Audit item 3, second attempt (ball_check.py and unembed_geometry.py pmax_* under-converged: the record
exceeded them by 0.005). log softmax_a(E(gamma*u + beta)) is CONCAVE in u, so its maximum over the
convex set {1'u = 0, ||u|| <= sqrt(32)} is found by projected gradient ascent (float64, 20,000 steps,
step 0.05 with 1/sqrt(t) decay, best iterate kept). Weighted by the 2,048-fact Panel A answers.
"""

import json

import _common as c
import torch

R = 32**0.5


def proj(u):
    u = u - u.mean(-1, keepdim=True)
    n = u.norm(dim=-1, keepdim=True).clamp_min(1e-12)
    return u * torch.clamp(R / n, max=1.0)


def pmax(bb, steps=20000):
    E = bb.token.weight.double()
    gam, bet = bb.final_norm.weight.double(), bb.final_norm.bias.double()
    u = torch.zeros(32, 32, dtype=torch.float64)  # one row per symbol
    rows = torch.arange(32)
    best = torch.zeros(32, dtype=torch.float64)
    for t in range(1, steps + 1):
        u.requires_grad_(True)
        lp = ((gam * u + bet) @ E.T).log_softmax(-1)[rows, c.ALPHABET]
        g, = torch.autograd.grad(lp.sum(), u)
        with torch.no_grad():
            best = torch.maximum(best, lp.exp())
            u = proj(u + 0.05 / t**0.5 * g)
    return best


def main():
    s = c.study()
    _, ids = c.restrict(s.streams["panel_a"], 2048)
    w = torch.bincount(s.facts.answer[ids.reshape(-1)], minlength=32).double()
    w = w / w.sum()
    out = {}
    for parent in ("b101", "b102"):
        pm = pmax(c.backbone(parent))
        out[parent] = {"pmax_ball": pm.tolist(), "weighted_mean": float((w * pm).sum())}
        print(parent, out[parent]["weighted_mean"], [round(float(x), 4) for x in pm])
    (c.OUT / "ball_check2.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
