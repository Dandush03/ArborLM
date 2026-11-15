"""A2 (auditor, Opus 5.5): independent re-scoring of calibration snapshots and forward-only loss checks.

Independent of studies.p9i and of studies.p9.model / evaluate: the backbone blocks, the R1 / R2 memory
read, the oracle codes, the R2 slot table, the answer extraction and the ties-wrong alphabet scoring are
written here from the ADR text. Data are regenerated with studies.p9.data (the generator, gated by G1 and
audited in the P9 calibration audit) from rehearsal draw 1 (studies.p9.core.rehearsal_seeds(1)); the
frozen backbones are loaded with studies.p9.controls.load_backbone and compared with the snapshot's own
backbone tensors. Nothing is trained.

usage: a2_rescore_snapshots.py RUN_DIR EXPERIMENTS_ROOT LABEL:UPDATE[,UPDATE...] ... [--dtype float64]
"""
import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace

import torch
from torch.nn import functional as F

from studies.p9 import controls, data as p9data
from studies.p9 import core as p9core

torch.set_num_threads(2)
RUN, ROOT = Path(sys.argv[1]), Path(sys.argv[2])
DTYPE = torch.float64 if "--dtype" in sys.argv and sys.argv[sys.argv.index("--dtype") + 1] == "float64" else torch.float32
JOBS = [a for a in sys.argv[3:] if ":" in a]
SITES = [8 * r + 6 for r in range(8)]
ALPHA = list(range(0x40, 0x60))
M64 = (1 << 64) - 1
G = 0x9E3779B97F4A7C15


def mix(x: int) -> int:
    x = (x + G) & M64
    x = ((x ^ (x >> 30)) * 0xBF58476D1CE4E5B9) & M64
    x = ((x ^ (x >> 27)) * 0x94D049BB133111EB) & M64
    return x ^ (x >> 31)


def code(seed: int, ident: int) -> list[float]:
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


def ln(x, w, b):
    m = x.mean(-1, keepdim=True)
    v = ((x - m) ** 2).mean(-1, keepdim=True)
    return (x - m) / torch.sqrt(v + 1e-5) * w + b


def block(sd, i, h):
    p = f"backbone.blocks.{i}."
    b, t, _ = h.shape
    qkv = ln(h, sd[p + "attn_norm.weight"], sd[p + "attn_norm.bias"]) @ sd[p + "qkv.weight"].T + sd[p + "qkv.bias"]
    qkv = qkv.reshape(b, t, 3, 4, 8)
    q, k, v = (qkv[:, :, j].permute(0, 2, 1, 3) for j in range(3))  # [b, 4, t, 8]
    s = q @ k.transpose(-1, -2) / math.sqrt(8)
    s = s.masked_fill(torch.ones(t, t, dtype=torch.bool).triu(1), -math.inf)
    a = (s.softmax(-1) @ v).permute(0, 2, 1, 3).reshape(b, t, 32)
    h = h + a @ sd[p + "attn_out.weight"].T + sd[p + "attn_out.bias"]
    f = ln(h, sd[p + "ffn_norm.weight"], sd[p + "ffn_norm.bias"]) @ sd[p + "ffn_in.weight"].T + sd[p + "ffn_in.bias"]
    f = 0.5 * f * (1 + torch.erf(f / math.sqrt(2)))
    return h + f @ sd[p + "ffn_out.weight"].T + sd[p + "ffn_out.bias"]


def ident_codes(tokens):  # [B, 8] sum symbol_i * 32**i over the first four identifier bytes
    out = torch.zeros(tokens.shape[0], 8, dtype=torch.int64)
    for r in range(8):
        for i in range(4):
            out[:, r] += ((tokens[:, 8 * r + 1 + i] - 0x40) % 32) * 32**i
    return out


def forward(sd, arm, tokens, r1_seed, slot_of, cache):
    """logits at the 8 answer sites, [B, 8, 256]; tokens [B, 63]."""
    x = sd["backbone.token.weight"][tokens] + sd["backbone.position.weight"][: tokens.shape[1]]
    h = block(sd, 0, x)
    ids = ident_codes(tokens)
    gate = torch.sigmoid(sd["addition.gate"])
    values, wo = sd["addition.values"], sd["addition.wo"]
    if arm == "R1":
        flat = ids.reshape(-1).tolist()
        for c in set(flat):
            if c not in cache:
                cache[c] = code(r1_seed, c)
        q = torch.tensor([cache[c] for c in flat], dtype=DTYPE)
        k = sd["addition.keys"]
        kn = k / k.norm(dim=-1, keepdim=True).clamp_min(1e-8)
        sc = (q @ kn.T) / 0.2  # [Q, N]
        # top 8, ties by lowest slot id: sort by (-score, id) via a stable descending sort
        order = sc.argsort(dim=-1, descending=True, stable=True)[:, :8]
        top = sc.gather(1, order)
        w = top.softmax(-1)
        read = (w[..., None] * values[order]).sum(1)
    else:
        slots = torch.tensor([slot_of.get(c, -1) for c in ids.reshape(-1).tolist()])
        read = values[slots.clamp_min(0)] * (slots >= 0).to(DTYPE)[:, None]
    delta = torch.zeros_like(h)
    delta[:, SITES] = gate * (read.reshape(tokens.shape[0], 8, 32) @ wo.T)
    h = block(sd, 1, h + delta)
    h = ln(h, sd["backbone.final_norm.weight"], sd["backbone.final_norm.bias"])
    return (h @ sd["backbone.token.weight"].T)[:, SITES]


def score(logits, answers):
    z = logits[..., ALPHA]  # [B, 8, 32]
    mine = z.gather(-1, answers[..., None]).squeeze(-1)
    other = z.scatter(-1, answers[..., None], -math.inf).amax(-1)
    return mine > other  # ties wrong


corpus = p9core.load_trained_corpus(ROOT)
seeds = p9core.rehearsal_seeds(1)
study = p9data.build_study_data(seeds, corpus)
print("seed set:", seeds.name, "facts seed", seeds.facts, "r1 seed", seeds.r1_codes)
backbones = {}
results = {}
for job in JOBS:
    label, ups = job.split(":")
    parts = label.split("-")
    arm, slots = parts[1], int(parts[2][1:])
    parent = (int(parts[3][1:]), int(parts[4][1:]))
    F_ = {4096: 2048, 16384: 8192, 65536: 32768}[slots]
    if parent not in backbones:
        backbones[parent] = {k: v.detach().clone() for k, v in controls.load_backbone(parent, ROOT)[0].state_dict().items()}
    frozen = backbones[parent]
    idents = study.facts.ident[:F_]  # symbols
    enc = (idents[:, :4] * torch.tensor([1, 32, 1024, 32768])).sum(-1).tolist()
    slot_of = {c: i for i, c in enumerate(enc)}
    answer_of = dict(zip(enc, study.facts.answer[:F_].tolist(), strict=True))
    cal = json.loads((RUN / "cells" / label / "calibration_cell.json").read_text())
    cache: dict = {}
    for u in map(int, ups.split(",")):
        snap = torch.load(RUN / "cells" / label / "snapshots" / f"u{u:07d}" / "model.pt", weights_only=True)["model"]
        same_bb = all(torch.equal(snap["backbone." + k], v) for k, v in frozen.items())
        sd = {k: v.to(DTYPE) if v.is_floating_point() else v for k, v in snap.items()}
        row = {"backbone_equals_frozen": same_bb}
        for panel, name in (("A", "panel_a"), ("B", "panel_b")):
            toks = study.streams[name].tokens
            correct = trained = unseen_c = unseen_n = 0
            with torch.no_grad():
                for s in range(0, toks.shape[0], 512):
                    t = toks[s : s + 512]
                    ids = ident_codes(t[:, :63])
                    is_tr = torch.tensor([[c in slot_of for c in r] for r in ids.tolist()])
                    keep = is_tr.all(1) | (~is_tr).all(1)  # contexts of trained facts at this size, or unseen controls
                    # contexts mixing trained and not-at-this-size facts are dropped (restricted panel)
                    t = t[keep]
                    if t.shape[0] == 0:
                        continue
                    ids = ids[keep]
                    is_tr = is_tr[keep]
                    ans = t[:, [p + 1 for p in SITES]] - 0x40
                    ok = score(forward(sd, arm, t[:, :63], seeds.r1_codes, slot_of, cache), ans)
                    correct += int(ok[is_tr].sum())
                    trained += int(is_tr.sum())
                    unseen_c += int(ok[~is_tr].sum())
                    unseen_n += int((~is_tr).sum())
            row[panel] = {"correct": correct, "facts": trained, "accuracy": correct / trained, "not_trained_correct": unseen_c, "not_trained": unseen_n,
                          "run_accuracy": cal["accuracy"][str(u)][panel], "count_difference": correct - round(cal["accuracy"][str(u)][panel] * F_)}
        results[f"{label}@{u}"] = row
        print(label, u, json.dumps(row))
print("DTYPE", DTYPE)
