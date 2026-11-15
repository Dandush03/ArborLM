"""C7 (auditor, Opus 5.5, confirmation of ADR-0019 revision 3) -- DIAGNOSTIC, NOT A RESULT.

Reachability of revision 3's success condition 3 (on the probe set at the readout: distinct top-1 slots >= 0.50 x probe
facts AND largest top-1 share <= 0.02) and of the slot-based onset/escape thresholds (onset: distinct top-1 <= 32;
escape: >= 0.25 x probe facts). Probe = the first 512 answer sites, in stream order, of the draw's calibration stream
restricted to the cell's trained facts (contexts whose 8 facts are all trained; first 64 such contexts).

Models (no training; own forward as c3/c4; nothing imported from studies.p9i):
 * the P9-I review's d4 W7 models on unit-test sets p9i-test-0/1/2 (escape partial / starting / complete);
 * P9-I REGISTERED snapshots (historical, already observed and re-scored by the P9-I review): R1 (oracle query, a
   genuinely working memory) at 4,096 / 16,384 / 65,536 slots, and W7 (collapsed) at 4,096, on P9-I's registered draw
   (data seeds 182001 + i), regenerated here.
 * A spread-but-useless control: W7 at initialization (untrained) on p9i-test-2.
Usage: c7_probe_condition3.py <scratchpad dir with d4_test*_W7.pt> <P9-I run dir>
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


def run(P, tokens, kind, r1_seed=None):
    e = bb["token.weight"][tokens] + bb["position.weight"][: tokens.shape[1]]
    h = block(bb, 0, e)
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
    add = torch.sigmoid(P["gate"]) * (read.reshape(tokens.shape[0], 8, 32) @ P["wo"].T)
    delta = torch.zeros_like(h)
    delta[:, SITES] = add
    out = ln(block(bb, 1, h + delta), bb["final_norm.weight"], bb["final_norm.bias"])
    return (out @ bb["token.weight"].T)[:, SITES][..., ALPHA], idx[:, 0]


def probe_stats(study, facts, P, kind, r1_seed=None, stream="calibration", contexts=64):
    st = study.streams[stream]
    keep = (st.fact_ids < facts).all(1)
    toks, ids = st.tokens[keep][:contexts], st.fact_ids[keep][:contexts]
    with torch.no_grad():
        lg, t1 = run(P, toks[:, :63], kind, r1_seed)
    ans = toks[:, [p + 1 for p in SITES]] - 0x40
    mine = lg.gather(-1, ans[..., None]).squeeze(-1)
    other = lg.scatter(-1, ans[..., None], -math.inf).amax(-1)
    acc = float((mine > other).float().mean())
    n_sites = t1.numel()
    n_facts = int(ids.reshape(-1).unique().numel())
    distinct = int(t1.unique().numel())
    share = float(t1.bincount().max()) / n_sites
    return {"sites": n_sites, "probe_facts": n_facts, "probe_accuracy": round(acc, 4), "distinct_top1": distinct,
            "distinct_over_facts": round(distinct / n_facts, 3), "largest_top1_share": round(share, 4),
            "largest_top1_count": int(t1.bincount().max()),
            "cond3_holds": bool(distinct >= 0.5 * n_facts and share <= 0.02),
            "onset(<=32)": bool(distinct <= 32), "escape_level(>=0.25)": bool(distinct >= 0.25 * n_facts)}


res = {"DIAGNOSTIC": True}
# --- d4 W7 models on test sets ---
for k in (0, 1, 2):
    study = p9data.build_study_data(seedset(f"p9i-test-{k}", 900001 + 100 * k, False), corpus)
    sd = torch.load(SCR / f"d4_test{k}_W7.pt")
    P = {n.split(".", 1)[1]: v for n, v in sd.items()}
    res[f"W7 d4 p9i-test-{k} (4096)"] = probe_stats(study, 2048, P, "W7")
    res[f"W7 d4 p9i-test-{k} (4096) on Panel A first 512"] = probe_stats(study, 2048, P, "W7", stream="panel_a")
    if k == 2:
        def mat(seed, *shape):
            return torch.empty(shape).normal_(0, 0.02, generator=torch.Generator().manual_seed(seed))
        P0 = {"keys": mat(500001 + 1000, 4096, 16), "values": mat(500001 + 2000, 4096, 32), "wq": mat(500001 + 3000, 16, 224),
              "wo": mat(500001 + 4000, 32, 32), "gate": torch.tensor(-2.0)}
        res["W7 at init (spread-but-useless) p9i-test-2"] = probe_stats(study, 2048, P0, "W7")
        # R1 codes with untrained keys: a spread, fact-consistent but useless arm
        P0r = dict(P0)
        res["R1 codes, untrained keys/values (spread, consistent, useless) p9i-test-2"] = probe_stats(study, 2048, P0r, "R1", r1_seed=900001 + 200 + 11)
    print(json.dumps({k: "done"}), file=sys.stderr, flush=True)

# --- P9-I registered draw: R1 at three sizes, W7 at 4,096 ---
reg = seedset("p9i-registered", 182001, True)
study = p9data.build_study_data(reg, corpus)
r1_seed = reg.r1_codes
for label, facts, kind in (("R1-n4096-b101-o301-s1801", 2048, "R1"), ("R1-n4096-b101-o301-s1802", 2048, "R1"),
                           ("R1-n16384-b101-o301-s1801", 8192, "R1"), ("R1-n16384-b101-o301-s1802", 8192, "R1"),
                           ("R1-n65536-b101-o301-s1801", 32768, "R1"), ("W7-n4096-b101-o301-s1801", 2048, "W7"),
                           ("W7-n4096-b101-o301-s1802", 2048, "W7")):
    m = torch.load(RUN / "cells" / label / "snapshots" / "u0008192" / "model.pt", weights_only=False)["model"]
    P = {k.split(".", 1)[1]: v for k, v in m.items() if k.startswith("addition.")}
    res[label + " (P9-I registered, historical)"] = probe_stats(study, facts, P, kind, r1_seed=r1_seed)
    print(json.dumps({label: res[label + " (P9-I registered, historical)"]}), file=sys.stderr, flush=True)
print(json.dumps(res, indent=1))
