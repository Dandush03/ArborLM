"""Audit item 2: why B101 R2 plateaus at 0.9697 (all failures have answer '\\' = 0x5C).

(a) On the reachable sphere S of the final norm (see unembed_geometry.py), for every symbol a: the
    point that maximises the FULL 256-way probability of a (what the 256-way training loss pushes
    towards), and whether a is the argmax within the alphabet there; which byte wins instead.
(b) On the converged B101 65,536-slot R2 snapshot (u32768, seed 1701 cell): for Panel A facts whose
    answer is '\\', the predicted symbol, the full-softmax top byte, and p_full / p_sigma.
"""

import json

import _common as c
import torch

R = 32**0.5
SIG = c.ALPHABET
SITES = torch.tensor([8 * r + 6 for r in range(8)])


def sphere(v):
    v = v - v.mean(-1, keepdim=True)
    return R * v / v.norm(dim=-1, keepdim=True)


def argmax_full_point(bb, a, restarts=32, steps=1500):
    g = torch.Generator().manual_seed(500 + a)
    v = torch.randn(restarts, 32, generator=g, dtype=torch.float64)
    v[0] = (bb.final_norm.weight * bb.token.weight[SIG[a]]).double()
    v.requires_grad_(True)
    opt = torch.optim.Adam([v], lr=0.05)
    E = bb.token.weight.double()
    gam, bet = bb.final_norm.weight.double(), bb.final_norm.bias.double()
    for _ in range(steps):
        lp = ((gam * sphere(v) + bet) @ E.T).log_softmax(-1)[:, SIG[a]]
        opt.zero_grad()
        (-lp.sum()).backward()
        opt.step()
    with torch.no_grad():
        z = (gam * sphere(v) + bet) @ E.T
        i = z.log_softmax(-1)[:, SIG[a]].argmax()
        z = z[i]
        inside = z[SIG]
        top_sigma = int(inside.argmax())
        top_full = int(z.argmax())
        return {
            "symbol": chr(int(SIG[a])),
            "p_full_at_point": float(z.softmax(-1)[SIG[a]]),
            "p_sigma_at_point": float(inside.softmax(-1)[a]),
            "is_sigma_argmax": top_sigma == a,
            "sigma_winner": chr(int(SIG[top_sigma])),
            "sigma_gap_logits": float(inside[a] - inside[torch.arange(32) != a].max()),
            "full_top_byte": top_full,
        }


def main():
    out = {}
    for parent in ("b101", "b102"):
        bb = c.backbone(parent)
        rows = [argmax_full_point(bb, a) for a in range(32)]
        out[parent] = rows
        bad = [r for r in rows if not r["is_sigma_argmax"]]
        print(parent, "symbols NOT the alphabet argmax at their full-softmax optimum:", json.dumps(bad))
    # (b) the converged snapshot
    s = c.study()
    bb = c.backbone("b101")
    snap = c.RUN / "cells/CAL-A5-flat-R2-n65536-b101-o301-s1701/snapshots/u0032768/model.pt"
    m = torch.load(snap, weights_only=True)["model"]
    values, wo, gate = m["addition.values"], m["addition.wo"], m["addition.gate"]
    tok, ids = c.restrict(s.streams["panel_a"], 32768)
    preds, tops, pf, ps, ans_all = [], [], [], [], []
    with torch.no_grad():
        for st in range(0, len(tok), 512):
            tk, sl = tok[st : st + 512], ids[st : st + 512]
            h = c.hidden0(bb, tk[:, :63])
            h = h.index_add(1, SITES, torch.sigmoid(gate) * values[sl] @ wo.T)
            lg = c.head(bb, h)[:, SITES].reshape(-1, 256)
            ans = (tk.reshape(-1, 8, 8)[:, :, 7] - 0x40).reshape(-1)
            sel = ans == 28
            preds.append(lg[sel][:, SIG].argmax(-1))
            tops.append(lg[sel].argmax(-1))
            pf.append(lg[sel].softmax(-1)[:, SIG[28]])
            ps.append(lg[sel][:, SIG].softmax(-1)[:, 28])
            ans_all.append(ans)
    preds, tops = torch.cat(preds), torch.cat(tops)
    b = {
        "facts_with_answer_backslash": int(len(preds)),
        "predicted_symbol_counts": {chr(0x40 + int(k)): int((preds == k).sum()) for k in preds.unique()},
        "full_top_byte_counts": {int(k): int((tops == k).sum()) for k in tops.unique()},
        "p_full_mean": float(torch.cat(pf).mean()),
        "p_sigma_mean": float(torch.cat(ps).mean()),
    }
    print("b101 n65536 u32768 answer '\\\\' facts:", json.dumps(b))
    out["snapshot_backslash"] = b
    (c.OUT / "backslash.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
