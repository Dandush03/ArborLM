"""D1 (auditor, Opus 5.5) -- DIAGNOSTIC TRAINING, NOT A RESULT, NOT A RE-RUN OF A REGISTERED CELL.

Mechanism tests for the chance-level W7 / A4 arms of P9-I, on REHEARSAL draws only (0 or 2; draw 1 is the
calibration draw and is refused; registered seeds are refused). The trainer is the auditor's own: the
frozen backbone forward, the window query, the flat top-8 memory, the alphabet loss, one AdamW (lr 0.003,
betas 0.9/0.999, eps 1e-8, no weight decay), clip 1.0 over all trainable parameters, batch = the P9
training stream (16 contexts, 128 answer sites per update), N(0, 0.02) initialization from torch
generators seeded seed + 1000 / 2000 / 3000 / 4000 (keys, values, wq, wo), gate -2.0. Nothing is imported
from studies.p9i; the data generator and training schedule come from studies.p9.data (audited generator),
the frozen backbone from studies.p9.controls.

Variants (``--variant``):
  W7        the registered recipe for W7 (window of 7 block-0 states, wq 16 x 224)
  W7bias    W7 plus a trainable fact-independent 32-vector added at every answer site (init 0): gives the
            optimizer a path for the fact-independent part of the loss that does not go through addressing
  W7keyinit W7 with key row f (f < facts) initialized to fact f's initial query (from its first training
            occurrence), other rows as usual
  E7        W7 on token + position embeddings
  A4        4 heads x 8 over the causal prefix of block-0 states, then wq 16 x 32
  R1        fixed random unit code per fact (sanity check of this trainer against the registered R1)

Usage: d1_diag_train.py --draw 2 --variant W7 --slots 4096 --facts 2048 --updates 8192 --seed 500001
"""
import argparse
import json
import math
import time
from pathlib import Path
from types import SimpleNamespace

import torch
from torch.nn import functional as F

from studies.p9 import controls
from studies.p9 import core as p9core
from studies.p9 import data as p9data

ap = argparse.ArgumentParser()
ap.add_argument("--draw", type=int, required=True)
ap.add_argument("--variant", required=True)
ap.add_argument("--slots", type=int, default=4096)
ap.add_argument("--facts", type=int, default=2048)
ap.add_argument("--updates", type=int, default=8192)
ap.add_argument("--seed", type=int, default=500001)
ap.add_argument("--root", default="/Users/daniellaloush/dandush03/ArborLM/experiments")
ap.add_argument("--checkpoints", default="0,64,256,512,1024,2048,4096,8192")
args = ap.parse_args()
if args.draw not in (0, 2):
    raise SystemExit("diagnostics use rehearsal draws 0 or 2 only")
if args.seed in (1801, 1802, 1791, 1792) or 182001 <= args.seed <= 182100:
    raise SystemExit("registered or calibration seed refused")
torch.set_num_threads(2)
torch.manual_seed(args.seed)
ROOT = Path(args.root)
SITES = [8 * r + 6 for r in range(8)]
ALPHA = list(range(0x40, 0x60))
M64 = (1 << 64) - 1
G = 0x9E3779B97F4A7C15
V = args.variant


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
    p = f"blocks.{i}."
    b, t, _ = h.shape
    qkv = (ln(h, sd[p + "attn_norm.weight"], sd[p + "attn_norm.bias"]) @ sd[p + "qkv.weight"].T + sd[p + "qkv.bias"]).reshape(b, t, 3, 4, 8)
    q, k, v = (qkv[:, :, j].permute(0, 2, 1, 3) for j in range(3))
    s = (q @ k.transpose(-1, -2) / math.sqrt(8)).masked_fill(torch.ones(t, t, dtype=torch.bool).triu(1), -math.inf)
    h = h + (s.softmax(-1) @ v).permute(0, 2, 1, 3).reshape(b, t, 32) @ sd[p + "attn_out.weight"].T + sd[p + "attn_out.bias"]
    f = ln(h, sd[p + "ffn_norm.weight"], sd[p + "ffn_norm.bias"]) @ sd[p + "ffn_in.weight"].T + sd[p + "ffn_in.bias"]
    return h + (0.5 * f * (1 + torch.erf(f / math.sqrt(2)))) @ sd[p + "ffn_out.weight"].T + sd[p + "ffn_out.bias"]


def mat(seed, *shape):
    return torch.empty(shape).normal_(0, 0.02, generator=torch.Generator().manual_seed(seed))


def ident_codes(tokens):
    out = torch.zeros(tokens.shape[0], 8, dtype=torch.int64)
    for r in range(8):
        for i in range(4):
            out[:, r] += ((tokens[:, 8 * r + 1 + i] - 0x40) % 32) * 32**i
    return out


seeds = p9core.rehearsal_seeds(args.draw)
corpus = p9core.load_trained_corpus(ROOT)
study = p9data.build_study_data(seeds, corpus)
stream = p9data.training_stream_for(study, SimpleNamespace(is_lane_d=False, facts=args.facts))
bb = {k: v.detach() for k, v in controls.load_backbone((101, 301), ROOT)[0].state_dict().items()}
N, S = args.slots, args.seed
P = {"keys": mat(S + 1000, N, 16), "values": mat(S + 2000, N, 32), "wo": mat(S + 4000, 32, 32), "gate": torch.tensor(-2.0)}
if V in ("W7", "W7bias", "W7keyinit", "E7"):
    P["wq"] = mat(S + 3000, 16, 224)
if V == "A4":
    P["wq"] = mat(S + 3000, 16, 32)
    P["aq"], P["ak"], P["av"] = mat(S + 6000, 32, 32), mat(S + 7000, 32, 32), mat(S + 8000, 32, 32)
if V == "W7bias":
    P["bias"] = torch.zeros(32)
code_cache: dict = {}


def states(tokens):
    with torch.no_grad():
        e = bb["token.weight"][tokens] + bb["position.weight"][: tokens.shape[1]]
        return e, block(bb, 0, e)


def features(e, h):
    if V == "E7":
        x = e
    else:
        x = h
    if V == "A4":
        out = []
        for t in SITES:
            q = (x[:, t] @ P["aq"].T).reshape(-1, 4, 8)
            k = (x[:, : t + 1] @ P["ak"].T).reshape(x.shape[0], t + 1, 4, 8)
            v = (x[:, : t + 1] @ P["av"].T).reshape(x.shape[0], t + 1, 4, 8)
            w = (torch.einsum("bhd,bthd->bht", q, k) / math.sqrt(8)).softmax(-1)
            out.append(torch.einsum("bht,bthd->bhd", w, v).reshape(-1, 32))
        return torch.stack(out, 1)
    return torch.stack([torch.cat([x[:, s - 6 + j] for j in range(7)], -1) for s in SITES], 1)


def queries(tokens, e, h):
    if V == "R1":
        flat = ident_codes(tokens).reshape(-1).tolist()
        for c in set(flat):
            if c not in code_cache:
                code_cache[c] = code(seeds.r1_codes, c)
        return torch.tensor([code_cache[c] for c in flat])
    z = features(e, h).reshape(-1, P["wq"].shape[1]) @ P["wq"].T
    return F.normalize(z, dim=-1, eps=1e-8)


def forward(tokens):
    e, h = states(tokens)
    q = queries(tokens, e, h)
    kn = F.normalize(P["keys"], dim=-1, eps=1e-8)
    sc = q @ kn.T / 0.2
    top, idx = sc.topk(8, dim=-1)
    read = (top.softmax(-1)[..., None] * P["values"][idx]).sum(1)
    add = torch.sigmoid(P["gate"]) * (read.reshape(tokens.shape[0], 8, 32) @ P["wo"].T)
    if "bias" in P:
        add = add + P["bias"]
    delta = torch.zeros_like(h)
    delta[:, SITES] = add
    out = ln(block(bb, 1, h + delta), bb["final_norm.weight"], bb["final_norm.bias"])
    return (out @ bb["token.weight"].T)[:, SITES][..., ALPHA], q, idx


if V == "W7keyinit":  # key row f := fact f's query at initialization, from its first training occurrence
    with torch.no_grad():
        seen = torch.zeros(args.facts, dtype=torch.bool)
        u = 1
        while not bool(seen.all()):
            b = stream.batch(u)
            _, q, _ = forward(b.tokens[:, :63])
            ids = b.fact_ids.reshape(-1)
            for j, f in enumerate(ids.tolist()):
                if f < args.facts and not seen[f]:
                    P["keys"][f] = q[j]
                    seen[f] = True
            u += 1

for p in P.values():
    p.requires_grad_(True)
opt = torch.optim.AdamW(list(P.values()), lr=0.003, betas=(0.9, 0.999), eps=1e-8, weight_decay=0.0)
panel = study.streams["panel_a"]
keep = (panel.fact_ids < args.facts).all(1)
ptoks, pids = panel.tokens[keep], panel.fact_ids[keep]
marks = sorted({int(x) for x in args.checkpoints.split(",") if int(x) <= args.updates})


def evaluate():
    with torch.no_grad():
        ok, qs, sel = [], [], []
        for s in range(0, ptoks.shape[0], 256):
            t = ptoks[s : s + 256]
            lg, q, idx = forward(t[:, :63])
            ans = t[:, [p + 1 for p in SITES]] - 0x40
            mine = lg.gather(-1, ans[..., None]).squeeze(-1)
            other = lg.scatter(-1, ans[..., None], -math.inf).amax(-1)
            ok.append((mine > other).reshape(-1))
            qs.append(q)
            sel.append(idx)
        Q = torch.cat(qs).double()
        n = Q.shape[0]
        tot = Q.sum(0)
        top1 = torch.cat(sel)[:, 0]
        return {"accuracy": float(torch.cat(ok).float().mean()), "mean_cos": float((tot @ tot - n) / (n * (n - 1))),
                "distinct_selected": int(torch.unique(torch.cat(sel)).numel()), "distinct_top1": int(torch.unique(top1).numel())}


t0 = time.time()
log = []
window_loss = []
for u in range(0, args.updates + 1):
    if u in marks:
        r = {"update": u, "train_loss_recent": round(sum(window_loss) / len(window_loss), 4) if window_loss else None} | evaluate()
        if "bias" in P:
            r["bias_norm"] = float(P["bias"].norm())
        r["wq_change_rel"] = float((P["wq"] - mat(S + 3000, *P["wq"].shape)).norm() / mat(S + 3000, *P["wq"].shape).norm()) if "wq" in P else None
        log.append(r)
        print(json.dumps(r), flush=True)
        window_loss = []
    if u == args.updates:
        break
    b = stream.batch(u + 1)
    lg, _, _ = forward(b.tokens[:, :63])
    tgt = b.tokens[:, 1:][:, SITES] - 0x40
    loss = F.cross_entropy(lg.reshape(-1, 32), tgt.reshape(-1))
    opt.zero_grad()
    loss.backward()
    torch.nn.utils.clip_grad_norm_(list(P.values()), 1.0)
    opt.step()
    window_loss.append(float(loss))
print(json.dumps({"DIAGNOSTIC": True, "draw": args.draw, "variant": V, "slots": N, "facts": args.facts, "updates": args.updates,
                  "seed": S, "seconds": round(time.time() - t0, 1), "final": log[-1]}))
