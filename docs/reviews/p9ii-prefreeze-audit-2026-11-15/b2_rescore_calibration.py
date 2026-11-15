"""B2 (auditor, Opus 5.5): independent re-scoring of the 22 P9-II calibration snapshots (u0008192) and an
independent recomputation of the ADR-0019 section 6 calibration rule.

Independent of studies.p9ii and studies.p9i: the backbone blocks, the W7 window query, the A5-C centring with the
saved buffer, the top-8 cosine read (ties by lowest slot id), the R1 oracle codes (A6), the D7 dense read (A7), the
answer extraction, the probe set (first 256 trained facts of the calibration stream, both occurrences) and the
ties-wrong alphabet scoring are written here from the ADR text. Data are regenerated with studies.p9.data (the P9
generator, audited earlier); the frozen backbone is loaded with studies.p9.controls.load_backbone and compared with
each snapshot's own backbone tensors. Nothing is trained.

usage: b2_rescore_calibration.py RUN_DIR EXPERIMENTS_ROOT
"""
import json
import math
import statistics
import sys
from pathlib import Path

import torch

from studies.p9 import controls, data as p9data
from studies.p9 import core as p9core

torch.set_num_threads(4)
RUN, ROOT = Path(sys.argv[1]), Path(sys.argv[2])
SITES = [8 * r + 6 for r in range(8)]
ALPHA = list(range(0x40, 0x60))
M64 = (1 << 64) - 1
G = 0x9E3779B97F4A7C15
FACTS = 2048


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


def ln(x, w, b):
    m = x.mean(-1, keepdim=True)
    v = ((x - m) ** 2).mean(-1, keepdim=True)
    return (x - m) / torch.sqrt(v + 1e-5) * w + b


def block(sd, i, h):
    p = f"backbone.blocks.{i}."
    b, t, _ = h.shape
    qkv = ln(h, sd[p + "attn_norm.weight"], sd[p + "attn_norm.bias"]) @ sd[p + "qkv.weight"].T + sd[p + "qkv.bias"]
    qkv = qkv.reshape(b, t, 3, 4, 8)
    q, k, v = (qkv[:, :, j].permute(0, 2, 1, 3) for j in range(3))
    s = q @ k.transpose(-1, -2) / math.sqrt(8)
    s = s.masked_fill(torch.ones(t, t, dtype=torch.bool).triu(1), -math.inf)
    a = (s.softmax(-1) @ v).permute(0, 2, 1, 3).reshape(b, t, 32)
    h = h + a @ sd[p + "attn_out.weight"].T + sd[p + "attn_out.bias"]
    f = ln(h, sd[p + "ffn_norm.weight"], sd[p + "ffn_norm.bias"]) @ sd[p + "ffn_in.weight"].T + sd[p + "ffn_in.bias"]
    f = 0.5 * f * (1 + torch.erf(f / math.sqrt(2)))
    return h + f @ sd[p + "ffn_out.weight"].T + sd[p + "ffn_out.bias"]


def ident_codes(tokens):
    out = torch.zeros(tokens.shape[0], 8, dtype=torch.int64)
    for r in range(8):
        for i in range(4):
            out[:, r] += ((tokens[:, 8 * r + 1 + i] - 0x40) % 32) * 32**i
    return out


def window(h):  # [B, 8, 224]: h_{t-6..t} at t = 8r+6, oldest first
    return torch.stack([h[:, 8 * r: 8 * r + 7].reshape(h.shape[0], -1) for r in range(8)], 1)


def forward(sd, arm, tokens, r1_seed, cache):
    """logits [B, 8, 256] at the answer sites, the queries [B*8,16] (None for A7) and the top-8 ids [B*8, 8] (None for A7)."""
    x = sd["backbone.token.weight"][tokens] + sd["backbone.position.weight"][: tokens.shape[1]]
    h = block(sd, 0, x)
    B = tokens.shape[0]
    q = top = None
    if arm == "A7":
        f = window(h) @ sd["addition.w1"].T
        f = 0.5 * f * (1 + torch.erf(f / math.sqrt(2)))
        out = torch.sigmoid(sd["addition.gate"]) * (f @ sd["addition.w2"].T)
    else:
        if arm == "A6":
            flat = ident_codes(tokens).reshape(-1).tolist()
            for c in set(flat):
                if c not in cache:
                    cache[c] = code(r1_seed, c)
            q = torch.tensor([cache[c] for c in flat], dtype=torch.float32)
        else:
            z = window(h) @ sd["addition.wq"].T
            if arm == "A5-C":
                z = z - sd["addition.centre"]
            q = (z / z.norm(dim=-1, keepdim=True).clamp_min(1e-8)).reshape(-1, 16)
        k = sd["addition.keys"]
        kn = k / k.norm(dim=-1, keepdim=True).clamp_min(1e-8)
        sc = (q @ kn.T) / 0.2
        top = sc.argsort(dim=-1, descending=True, stable=True)[:, :8]
        w = sc.gather(1, top).softmax(-1)
        read = (w[..., None] * sd["addition.values"][top]).sum(1)
        out = torch.sigmoid(sd["addition.gate"]) * (read.reshape(B, 8, 32) @ sd["addition.wo"].T)
    delta = torch.zeros_like(h)
    delta[:, SITES] = out
    h = block(sd, 1, h + delta)
    h = ln(h, sd["backbone.final_norm.weight"], sd["backbone.final_norm.bias"])
    return (h @ sd["backbone.token.weight"].T)[:, SITES], q, top


def correct_of(logits, answers):
    z = logits[..., ALPHA]
    mine = z.gather(-1, answers[..., None]).squeeze(-1)
    other = z.scatter(-1, answers[..., None], -math.inf).amax(-1)
    return mine > other


corpus = p9core.load_trained_corpus(ROOT)
frozen = {k: v.detach().clone() for k, v in controls.load_backbone(p9core.PRIMARY_PARENT, ROOT)[0].state_dict().items()}
studies = {}
for d in (3, 4):
    seeds = p9core.rehearsal_seeds(d)
    studies[d] = (seeds, p9data.build_study_data(seeds, corpus))
    print(f"draw {d}: seed set {seeds.name}, facts seed {seeds.facts}, r1 seed {seeds.r1_codes}, trained facts in table {studies[d][1].facts.trained}")

out = {}
for celldir in sorted((RUN / "cells").iterdir()):
    label = celldir.name
    parts = label.split("-")
    arm = parts[1] if parts[2].startswith(("v", "n")) else parts[1] + "-" + parts[2]
    d = int([p for p in parts if p.startswith("d")][-1][1:])
    seeds, study = studies[d]
    snap = torch.load(celldir / "snapshots" / "u0008192" / "model.pt", weights_only=True)["model"]
    same_bb = all(torch.equal(snap["backbone." + k], v) for k, v in frozen.items())
    tr = json.loads((celldir / "train.json").read_text())
    stream = study.streams["calibration"]
    keep = (stream.fact_ids < FACTS).all(1) | (stream.fact_ids >= study.facts.trained).all(1)
    toks, ids = stream.tokens[keep], stream.fact_ids[keep]
    answers = toks[:, 1:][:, SITES] - 0x40
    cache = {}
    corr = []
    with torch.no_grad():
        for s in range(0, toks.shape[0], 256):
            lg, _, _ = forward(snap, arm, toks[s:s + 256, :63], seeds.r1_codes, cache)
            corr.append(correct_of(lg, answers[s:s + 256]))
    corr = torch.cat(corr)
    trained = ids < FACTS
    acc = float(corr[trained].float().mean())
    # probe: first 256 trained facts by first appearance in the restricted calibration stream, both occurrences
    flat = ids.reshape(-1).tolist()
    first, seen = [], set()
    for f in flat:
        if f < FACTS and f not in seen:
            seen.add(f)
            first.append(f)
            if len(first) == 256:
                break
    chosen = torch.tensor(first)
    mask = torch.isin(ids, chosen)
    probe_correct = corr[mask]
    occurrences = torch.bincount(ids[mask], minlength=FACTS)[chosen]
    rec = json.loads((celldir / "calibration_cell.json").read_text())
    row = {"arm": arm, "draw": d, "value": rec["value"], "backbone_equals_frozen": same_bb, "calibration_sites_trained": int(trained.sum()),
           "accuracy_auditor": acc, "accuracy_recorded": rec["accuracy"], "probe_sites": int(mask.sum()), "probe_occurrences_min_max": [int(occurrences.min()), int(occurrences.max())],
           "probe_accuracy_auditor": float(probe_correct.float().mean()), "init_seed": tr["init_seed"], "seed_set": tr["seed_set"], "mode": tr["mode"], "run_updates": tr["run_updates"], "status": tr["status"],
           "schedule": tr["schedule"], "hyper_used": tr["hyper"], "trainable_backbone": tr["trainable_backbone_parameters"]}
    if (celldir / "diagnostics.jsonl").is_file():
        diag = [json.loads(x) for x in (celldir / "diagnostics.jsonl").read_text().splitlines() if x.strip()]
        row["probe_accuracy_recorded_u8192"] = diag[-1]["probe_accuracy"] if diag and diag[-1]["update"] == 8192 else None
        row["probe_curve"] = [(r["update"], r["probe_accuracy"]) for r in diag]
    # independent unseen-control check present?
    out[label] = row
    print(label, {k: v for k, v in row.items() if k not in ("probe_curve", "hyper_used", "schedule")})

# --- the section 6 rule, recomputed ---------------------------------------------------------------------------
a6 = {out[l]["draw"]: out[l]["accuracy_auditor"] for l in out if out[l]["arm"] == "A6"}
grid = {"A1": [0.1, 1.0], "A2": [1024.0, 2048.0], "A4": [0.125, 1.0], "A5-D": [0.1, 1.0]}


def first_success(curve, line):
    for u, a in curve:
        if a >= line:
            return u
    return math.inf


def med(xs):
    xs = sorted(xs)
    n = len(xs)
    if n % 2:
        return xs[n // 2]
    a, b = xs[n // 2 - 1], xs[n // 2]
    return a if a == b else (a + b) / 2


rule = {}
for arm, values in grid.items():
    mins, meds = {}, {}
    for v in values:
        cells = [l for l in out if out[l]["arm"] == arm and float(out[l]["value"]) == v]
        assert len(cells) == 2, cells
        mins[v] = min(out[l]["accuracy_auditor"] for l in cells)
        meds[v] = med([first_success(out[l]["probe_curve"], 0.9 * a6[out[l]["draw"]]) for l in cells])
    best = max(mins.values())
    contenders = [v for v in values if best - mins[v] < 0.02]
    if len(contenders) == 1:
        sel, why = contenders[0], "primary"
    else:
        e = min(meds[v] for v in contenders)
        winners = [v for v in contenders if meds[v] == e]
        sel, why = winners[0], ("secondary" if len(winners) == 1 else "first listed")
    rule[arm] = {"min_accuracy": mins, "median_first_success": meds, "selected": sel, "decided_by": why}
    print("RULE", arm, rule[arm])
recorded = json.loads((RUN / "calibration.json").read_text())
print("recorded hyper:", recorded["hyper"])
agree = all(abs(rule[a]["selected"] - float(recorded["table"][a]["selected"])) < 1e-12 for a in grid)
print("selected values agree with the record:", agree)
print("max |accuracy auditor - recorded|:", max(abs(r["accuracy_auditor"] - r["accuracy_recorded"]) for r in out.values()))
print("max |probe accuracy auditor - recorded at u8192|:", max(abs(r["probe_accuracy_auditor"] - r["probe_accuracy_recorded_u8192"]) for r in out.values() if r.get("probe_accuracy_recorded_u8192") is not None))
json.dump({"cells": {k: {kk: vv for kk, vv in v.items() if kk != "probe_curve"} for k, v in out.items()}, "rule": {a: {k: (str(v) if isinstance(v, dict) else v) for k, v in r.items()} for a, r in rule.items()}}, open(Path(__file__).parent / "outputs" / "b2_rescore_calibration.json", "w"), indent=1, default=str)
