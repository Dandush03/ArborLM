"""D5 (auditor, Opus 5.5): gradient check of the frozen implementation against the auditor's own forward,
at initialization and at REGISTERED trained snapshots (read only, nothing trained or written).

For each case the implementer's model (studies.p9i.model.build_model, parameters loaded from the
snapshot where given) computes the alphabet loss (studies.p9i.train.alphabet_loss) and its gradient on one
REHEARSAL draw-2 training batch; the auditor's forward (written from the ADR, as s3/d1) computes the same
loss and gradient from the same parameter values with torch.autograd. Reported: loss difference and the
largest absolute and relative gradient difference per parameter, and the gradient norm per parameter (to
show that wq / the interface receives gradient in the trained, collapsed state).

Usage: d5_gradient_check.py RUN_DIR EXPERIMENTS_ROOT
"""
import math
import sys
from pathlib import Path
from types import SimpleNamespace

import torch
from torch.nn import functional as F

from studies.p9 import controls
from studies.p9 import core as p9core
from studies.p9 import data as p9data
from studies.p9i import model as m, train

torch.set_num_threads(4)
RUN, ROOT = Path(sys.argv[1]), Path(sys.argv[2])
SITES = [8 * r + 6 for r in range(8)]
ALPHA = list(range(0x40, 0x60))


def ln(x, w, b):
    mu = x.mean(-1, keepdim=True)
    v = ((x - mu) ** 2).mean(-1, keepdim=True)
    return (x - mu) / torch.sqrt(v + 1e-5) * w + b


def block(sd, i, h):
    p = f"backbone.blocks.{i}."
    b, t, _ = h.shape
    qkv = (ln(h, sd[p + "attn_norm.weight"], sd[p + "attn_norm.bias"]) @ sd[p + "qkv.weight"].T + sd[p + "qkv.bias"]).reshape(b, t, 3, 4, 8)
    q, k, v = (qkv[:, :, j].permute(0, 2, 1, 3) for j in range(3))
    s = (q @ k.transpose(-1, -2) / math.sqrt(8)).masked_fill(torch.ones(t, t, dtype=torch.bool).triu(1), -math.inf)
    h = h + (s.softmax(-1) @ v).permute(0, 2, 1, 3).reshape(b, t, 32) @ sd[p + "attn_out.weight"].T + sd[p + "attn_out.bias"]
    f = ln(h, sd[p + "ffn_norm.weight"], sd[p + "ffn_norm.bias"]) @ sd[p + "ffn_in.weight"].T + sd[p + "ffn_in.bias"]
    return h + (0.5 * f * (1 + torch.erf(f / math.sqrt(2)))) @ sd[p + "ffn_out.weight"].T + sd[p + "ffn_out.bias"]


def my_loss(arm, sd, tokens):
    x_in = tokens[:, :63]
    e = sd["backbone.token.weight"][x_in] + sd["backbone.position.weight"][:63]
    h = block(sd, 0, e)
    x = e if arm in ("E7", "A4E") else h
    a = lambda n: sd["addition." + n]  # noqa: E731
    if arm in ("W7", "E7"):
        f = torch.stack([torch.cat([x[:, s - 6 + j] for j in range(7)], -1) for s in SITES], 1)
    elif arm in ("A4", "A4E"):
        outs = []
        for t in SITES:
            heads = []
            for hd in range(4):
                sl = slice(8 * hd, 8 * hd + 8)
                q = x[:, t] @ a("attn_q")[sl].T
                k = x[:, : t + 1] @ a("attn_k")[sl].T
                v = x[:, : t + 1] @ a("attn_v")[sl].T
                w = ((k @ q[:, :, None]).squeeze(-1) / math.sqrt(8)).softmax(-1)
                heads.append((w[:, :, None] * v).sum(1))
            outs.append(torch.cat(heads, -1))
        f = torch.stack(outs, 1)
    else:
        f = x[:, SITES]
    z = f.reshape(-1, f.shape[-1]) @ a("wq").T
    q = z / z.norm(dim=-1, keepdim=True).clamp_min(1e-8)
    kn = a("keys") / a("keys").norm(dim=-1, keepdim=True).clamp_min(1e-8)
    sc = q @ kn.T / 0.2
    with torch.no_grad():
        idx = sc.argsort(dim=-1, descending=True, stable=True)[:, :8]
    top = sc.gather(1, idx)
    read = (top.softmax(-1)[..., None] * a("values")[idx]).sum(1)
    delta = torch.zeros_like(h)
    delta[:, SITES] = torch.sigmoid(a("gate")) * (read.reshape(tokens.shape[0], 8, 32) @ a("wo").T)
    out = ln(block(sd, 1, h + delta), sd["backbone.final_norm.weight"], sd["backbone.final_norm.bias"])
    logits = (out @ sd["backbone.token.weight"].T)[:, SITES][..., ALPHA]
    tgt = tokens[:, 1:][:, SITES] - 0x40
    return F.cross_entropy(logits.reshape(-1, 32), tgt.reshape(-1))


seeds = p9core.rehearsal_seeds(2)
study = p9data.build_study_data(seeds, p9core.load_trained_corpus(ROOT))
backbone = controls.load_backbone((101, 301), ROOT)[0]
cases = [("W7", 4096, None), ("A4", 4096, None), ("E7", 16384, None),
         ("W7", 4096, "W7-n4096-b101-o301-s1801"), ("W7", 16384, "W7-n16384-b101-o301-s1801"),
         ("A4", 16384, "A4-n16384-b101-o301-s1801"), ("E7", 16384, "E7-n16384-b101-o301-s1801")]
for arm, slots, label in cases:
    net = m.build_model(arm, slots, 500001, backbone, seed_rng=False)
    if label:
        snap = torch.load(RUN / "cells" / label / "snapshots" / "u0008192" / "model.pt", weights_only=True)["model"]
        net.load_state_dict(snap, strict=False)
    facts = {4096: 2048, 16384: 8192}[slots]
    stream = p9data.training_stream_for(study, SimpleNamespace(is_lane_d=False, facts=facts))
    tokens = stream.batch(1).tokens
    net.train()
    named = [(n, p) for n, p in net.named_parameters() if p.requires_grad]
    logits, _ = net(tokens[:, :-1])
    loss = train.alphabet_loss(logits, tokens)
    grads = torch.autograd.grad(loss, [p for _, p in named])
    sd = {k: v.detach().clone() for k, v in net.state_dict().items()}
    leaves = {n: sd[n].requires_grad_(True) for n, _ in named}
    sd.update(leaves)
    mine = my_loss(arm, sd, tokens)
    mg = torch.autograd.grad(mine, [leaves[n] for n, _ in named])
    print(f"{arm} {slots} {'init seed 500001' if not label else 'registered snapshot ' + label}: loss impl {float(loss):.6f} own {float(mine):.6f} diff {abs(float(loss) - float(mine)):.2e}")
    for (n, _), g1, g2 in zip(named, grads, mg, strict=True):
        d = float((g1 - g2).abs().max())
        rel = d / max(float(g1.abs().max()), 1e-30)
        print(f"    {n:22s} |grad| impl {float(g1.norm()):.3e} own {float(g2.norm()):.3e}  max|diff| {d:.2e}  rel {rel:.2e}")
