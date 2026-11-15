"""C8 (auditor, Opus 5.5, confirmation of ADR-0019 revision 3) -- DIAGNOSTIC, NOT A RESULT.

Revision 3's LM-capability criterion: next-byte loss (256-way, all 64 targets) on the backbone's 2,048 corpus rows
(65 bytes each) with the memory ACTIVE at its fixed read positions 8r + 6, relative to the frozen backbone. Is the
oracle reference A6 (= R1) above 5% (TESTBED-LIMITED), and how do learned W7 models compare? Models as c7 (P9-I
registered R1 / W7 snapshots, historical; the P9-I review's d4 W7 models on unit-test sets). Own forward.
Usage: c8_lm_capability.py <scratchpad dir with d4_test*_W7.pt> <P9-I run dir>
"""

import json
import math
import sys
from pathlib import Path

import torch
from torch.nn import functional as F

from studies.p9 import controls
from studies.p9 import core as p9core
from studies.p9 import data as p9data

torch.set_num_threads(2)
ROOT = Path("/Users/daniellaloush/dandush03/ArborLM/experiments")
SCR, RUN = Path(sys.argv[1]), Path(sys.argv[2])
SITES = [8 * r + 6 for r in range(8)]
ALPHA = list(range(0x40, 0x60))
M64 = (1 << 64) - 1
G = 0x9E3779B97F4A7C15


def mix(x):
    x = (x + G) & M64
    x = ((x ^ (x >> 30)) * 0xBF58476D1CE4E5B9) & M64
    x = ((x ^ (x >> 27)) * 0x94D049BB133111EB) & M64
    return x ^ (x >> 31)


def code(seed, ident):
    st = mix(mix(seed & M64) + ident)
    out = []
    for j in range(8):
        a = mix((st + (2 * j + 1) * G) & M64)
        b = mix((st + (2 * j + 2) * G) & M64)
        u1 = ((a >> 11) + 1) / float(1 << 53)
        u2 = (b >> 11) / float(1 << 53)
        r = math.sqrt(-2.0 * math.log(u1))
        out += [r * math.cos(2 * math.pi * u2), r * math.sin(2 * math.pi * u2)]
    n = math.sqrt(sum(v * v for v in out))
    return [v / n for v in out]


def ident_codes(tokens):
    out = torch.zeros(tokens.shape[0], 8, dtype=torch.int64)
    for r in range(8):
        for i in range(4):
            out[:, r] += ((tokens[:, 8 * r + 1 + i] - 0x40) % 32) * 32**i
    return out


def ln(x, w, b):
    m = x.mean(-1, keepdim=True)
    v = ((x - m) ** 2).mean(-1, keepdim=True)
    return (x - m) / torch.sqrt(v + 1e-5) * w + b


def block(sd, i, h):
    p = f"blocks.{i}."
    b, t, _ = h.shape
    qkv = (ln(h, sd[p + "attn_norm.weight"], sd[p + "attn_norm.bias"]) @ sd[p + "qkv.weight"].T + sd[p + "qkv.bias"]).reshape(b, t, 3, 4, 8)
    q, k, v = (qkv[:, :, j].permute(0, 2, 1, 3) for j in range(3))
    s = (q @ k.transpose(-1, -2) / math.sqrt(8)).masked_fill(torch.ones(t, t, dtype=torch.bool).triu(1), -math.inf)
    h = h + (s.softmax(-1) @ v).permute(0, 2, 1, 3).reshape(b, t, 32) @ sd[p + "attn_out.weight"].T + sd[p + "attn_out.bias"]
    f = ln(h, sd[p + "ffn_norm.weight"], sd[p + "ffn_norm.bias"]) @ sd[p + "ffn_in.weight"].T + sd[p + "ffn_in.bias"]
    return h + (0.5 * f * (1 + torch.erf(f / math.sqrt(2)))) @ sd[p + "ffn_out.weight"].T + sd[p + "ffn_out.bias"]


def seedset(name, base, nulls_registered):
    names = list(p9core.DATA_SEEDS)
    vals = {n: base + i for i, n in enumerate(names)}
    if nulls_registered:
        top = base + len(names)
        na, nb = tuple(top + i for i in range(3)), tuple(top + 3 + i for i in range(3))
    else:
        na, nb = tuple(base + 20 + i for i in range(3)), tuple(base + 30 + i for i in range(3))
    return p9core.SeedSet(name, **vals, null_seeds_a=na, null_seeds_b=nb)



corpus = p9core.load_trained_corpus(ROOT)
bb = {k: v.detach() for k, v in controls.load_backbone((101, 301), ROOT)[0].state_dict().items()}
code_cache = {}
rows = torch.tensor(list(corpus), dtype=torch.int64).reshape(-1, 65)


def logits_all(P, tokens, kind, r1_seed=None):
    e = bb["token.weight"][tokens] + bb["position.weight"][: tokens.shape[1]]
    h = block(bb, 0, e)
    delta = torch.zeros_like(h)
    if P is not None:
        if kind == "R1":
            flat = ident_codes(tokens).reshape(-1).tolist()
            for c in set(flat):
                if (r1_seed, c) not in code_cache:
                    code_cache[(r1_seed, c)] = code(r1_seed, c)
            q = torch.tensor([code_cache[(r1_seed, c)] for c in flat])
        else:
            x = torch.stack([torch.cat([h[:, s - 6 + j] for j in range(7)], -1) for s in SITES], 1)
            q = F.normalize(x.reshape(-1, 224) @ P["wq"].T, dim=-1, eps=1e-8)
        kn = F.normalize(P["keys"], dim=-1, eps=1e-8)
        top, idx = (q @ kn.T / 0.2).topk(8, dim=-1)
        read = (top.softmax(-1)[..., None] * P["values"][idx]).sum(1)
        delta[:, SITES] = torch.sigmoid(P["gate"]) * (read.reshape(tokens.shape[0], 8, 32) @ P["wo"].T)
    out = ln(block(bb, 1, h + delta), bb["final_norm.weight"], bb["final_norm.bias"])
    return out @ bb["token.weight"].T


def nbl(P, kind="W7", r1_seed=None):
    tot = n = 0.0
    at_sites = n_s = 0.0
    with torch.no_grad():
        for s in range(0, rows.shape[0], 256):
            ch = rows[s : s + 256]
            lg = logits_all(P, ch[:, :64], kind, r1_seed)
            ce = F.cross_entropy(lg.reshape(-1, 256), ch[:, 1:65].reshape(-1), reduction="none").reshape(ch.shape[0], 64)
            tot += float(ce.sum()); n += ce.numel()
            at_sites += float(ce[:, SITES].sum()); n_s += ce[:, SITES].numel()
    return tot / n, at_sites / n_s


base, base_s = nbl(None)
res = {"DIAGNOSTIC": True, "backbone_next_byte_loss": round(base, 4), "backbone_loss_at_read_positions": round(base_s, 4), "models": {}}
reg = seedset("p9i-registered", 182001, True)
for label, kind in (("R1-n4096-b101-o301-s1801", "R1"), ("R1-n4096-b101-o301-s1802", "R1"), ("R1-n16384-b101-o301-s1801", "R1"),
                    ("R1-n65536-b101-o301-s1801", "R1"), ("W7-n4096-b101-o301-s1801", "W7"), ("W7-n16384-b101-o301-s1801", "W7")):
    m = torch.load(RUN / "cells" / label / "snapshots" / "u0008192" / "model.pt", weights_only=False)["model"]
    P = {k.split(".", 1)[1]: v for k, v in m.items() if k.startswith("addition.")}
    lo, ls = nbl(P, kind, reg.r1_codes)
    res["models"][label + " (P9-I registered)"] = {"loss": round(lo, 4), "rise_rel": round(lo / base - 1, 4), "loss_at_read_positions": round(ls, 4)}
    print(label, res["models"][label + " (P9-I registered)"], file=sys.stderr, flush=True)
for k in (0, 1, 2):
    sd = torch.load(SCR / f"d4_test{k}_W7.pt")
    P = {n.split(".", 1)[1]: v for n, v in sd.items()}
    lo, ls = nbl(P)
    res["models"][f"W7 d4 p9i-test-{k}"] = {"loss": round(lo, 4), "rise_rel": round(lo / base - 1, 4), "loss_at_read_positions": round(ls, 4)}
print(json.dumps(res, indent=1))
