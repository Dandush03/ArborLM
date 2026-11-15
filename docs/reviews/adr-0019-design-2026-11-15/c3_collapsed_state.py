"""C3 (auditor, Opus 5.5) -- DIAGNOSTIC ON REHEARSAL DRAW 0 ONLY, NOT A RESULT, NOT A REGISTERED CELL.

Own trainer (no studies.p9i import; data generator and backbone loader from studies.p9 as in the P9-I review's
d1). W7 answer-only at 4,096 slots / 2,048 facts, init seed 600001, trained for 256 updates (the collapse window).
Checks for the ADR-0019 draft:

 (1) gradient norms on the query projection wq and on the keys of: the answer loss; A1's address loss L_addr
     (fixed random injection s(f), tau_a = 0.2, softmax over all N); A1-S's loss (target redrawn per occurrence);
     at initialization and in the collapsed state (update 256);
 (2) A5's centring: mean pairwise cosine of raw and of centred-normalised probe queries, participation-ratio rank,
     and the share of query variance explained by (separator byte, record index) groups -- a fact-independent
     structure the global mean m cannot remove;
 (3) the batch composition: distinct facts among the 128 answer sites of each of the first 64 batches at 2,048 and
     8,192 facts (does L_div ever repel two occurrences of the same fact within a batch?);
 (4) G5 as drafted: logits of a W7 memory model at initialization against the frozen backbone on corpus rows.
"""
import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace

import torch
from torch.nn import functional as F

from studies.p9 import controls
from studies.p9 import core as p9core
from studies.p9 import data as p9data

torch.set_num_threads(2)
DRAW, SEED, N, FACTS, UPD = 0, 600001, 4096, 2048, 256
ROOT = Path("/Users/daniellaloush/dandush03/ArborLM/experiments")
SITES = [8 * r + 6 for r in range(8)]
ALPHA = list(range(0x40, 0x60))
out = {"DIAGNOSTIC": True, "draw": f"rehearsal-{DRAW}", "seed": SEED, "slots": N, "facts": FACTS}


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


seeds = p9core.rehearsal_seeds(DRAW)
corpus = p9core.load_trained_corpus(ROOT)
study = p9data.build_study_data(seeds, corpus)
stream = p9data.training_stream_for(study, SimpleNamespace(is_lane_d=False, facts=FACTS))
bbm = controls.load_backbone((101, 301), ROOT)[0]
bb = {k: v.detach() for k, v in bbm.state_dict().items()}
nblocks = len({k.split(".")[1] for k in bb if k.startswith("blocks.")})
out["backbone_blocks"] = nblocks
P = {"keys": mat(SEED + 1000, N, 16), "values": mat(SEED + 2000, N, 32), "wq": mat(SEED + 3000, 16, 224),
     "wo": mat(SEED + 4000, 32, 32), "gate": torch.tensor(-2.0)}
for p in P.values():
    p.requires_grad_(True)
gperm = torch.Generator().manual_seed(SEED + 77)
target_slot = torch.randperm(N, generator=gperm)[:FACTS]  # s(f): a fixed injection facts -> slots


def h0(tokens):
    with torch.no_grad():
        e = bb["token.weight"][tokens] + bb["position.weight"][: tokens.shape[1]]
        return block(bb, 0, e)


def zq(h):
    x = torch.stack([torch.cat([h[:, s - 6 + j] for j in range(7)], -1) for s in SITES], 1)
    return x.reshape(-1, 224) @ P["wq"].T  # pre-normalisation query z


def forward(tokens, all_positions=False, memory=True):
    h = h0(tokens)
    z = zq(h)
    q = F.normalize(z, dim=-1, eps=1e-8)
    kn = F.normalize(P["keys"], dim=-1, eps=1e-8)
    a = q @ kn.T
    top, idx = (a / 0.2).topk(8, dim=-1)
    read = (top.softmax(-1)[..., None] * P["values"][idx]).sum(1)
    add = torch.sigmoid(P["gate"]) * (read.reshape(tokens.shape[0], 8, 32) @ P["wo"].T)
    delta = torch.zeros_like(h)
    if memory:
        delta[:, SITES] = add
    hl = h + delta
    for i in range(1, nblocks):
        hl = block(bb, i, hl)
    logits = ln(hl, bb["final_norm.weight"], bb["final_norm.bias"]) @ bb["token.weight"].T
    if all_positions:
        return logits
    return logits[:, SITES][..., ALPHA], z, q, a, idx


def answer_loss(tokens):
    lg, z, q, a, idx = forward(tokens[:, :63])
    tgt = tokens[:, 1:][:, SITES] - 0x40
    return F.cross_entropy(lg.reshape(-1, 32), tgt.reshape(-1)), a


def addr_loss(a, fact_ids, random_target=False, gen=None):
    if random_target:
        t = torch.randint(0, N, (a.shape[0],), generator=gen)
    else:
        t = target_slot[fact_ids.reshape(-1)]
    return F.cross_entropy(a / 0.2, t)


def grad_norms(loss, names=("wq", "keys", "wo", "values")):
    g = torch.autograd.grad(loss, [P[n] for n in names], allow_unused=True, retain_graph=True)
    return {n: (0.0 if x is None else float(x.norm())) for n, x in zip(names, g)}


panel = study.streams["panel_a"]
keep = (panel.fact_ids < FACTS).all(1)
ptoks, pids = panel.tokens[keep][:64], panel.fact_ids[keep][:64]  # 512 probe sites (as the draft's probe)


def probe():
    with torch.no_grad():
        lg, z, q, a, idx = forward(ptoks[:, :63])
        n = q.shape[0]
        s = q.sum(0)
        res = {"mean_cos": float((s @ s - n) / (n * (n - 1))), "distinct_top1": int(idx[:, 0].unique().numel()),
               "largest_top1_share": float(idx[:, 0].bincount().max() / n)}
        zc = z - z.mean(0)
        qc = F.normalize(zc, dim=-1)
        sc = qc.sum(0)
        res["centred_mean_cos"] = float((sc @ sc - n) / (n * (n - 1)))
        ev = torch.linalg.eigvalsh(torch.cov(zc.T.double()))
        res["participation_rank_centred"] = float(ev.sum() ** 2 / (ev**2).sum())
        res["common_share_E|z|^2"] = float((z.mean(0) @ z.mean(0)) / (z * z).sum(-1).mean())
        # fact-independent structure beyond the global mean: (separator byte, record index) groups
        sep = ptoks[:, [8 * r for r in range(8)]].reshape(-1)
        rec = torch.arange(8).repeat(ptoks.shape[0])
        key = sep * 8 + rec
        tot = float((zc * zc).sum())
        between = 0.0
        for k in key.unique():
            m = key == k
            g = zc[m].mean(0)
            between += float(m.sum()) * float(g @ g)
        res["template_x_record_share_of_centred_variance"] = between / tot
        res["groups"] = int(key.unique().numel())
        # the same with q normalised after removing the group means (what an oracle per-template centring would leave)
        return res


log = {}
log["probe_u0"] = probe()
b1 = stream.batch(1)
la, a = answer_loss(b1.tokens)
log["grad_u0_answer"] = grad_norms(la)
log["grad_u0_addr"] = grad_norms(addr_loss(a, b1.fact_ids))
gr = torch.Generator().manual_seed(SEED + 99)
log["grad_u0_addr_random_A1S"] = grad_norms(addr_loss(a, b1.fact_ids, True, gr))
opt = torch.optim.AdamW(list(P.values()), lr=0.003, betas=(0.9, 0.999), eps=1e-8, weight_decay=0.0)
for u in range(1, UPD + 1):
    b = stream.batch(u)
    loss, _ = answer_loss(b.tokens)
    opt.zero_grad()
    loss.backward()
    torch.nn.utils.clip_grad_norm_(list(P.values()), 1.0)
    opt.step()
    if u in (64, 128, 256):
        log[f"probe_u{u}"] = probe()
        print(json.dumps({u: log[f"probe_u{u}"]}), file=sys.stderr, flush=True)
bn = stream.batch(UPD + 1)
la, a = answer_loss(bn.tokens)
log[f"grad_u{UPD}_answer"] = grad_norms(la)
log[f"grad_u{UPD}_addr"] = grad_norms(addr_loss(a, bn.fact_ids))
log[f"grad_u{UPD}_addr_random_A1S"] = grad_norms(addr_loss(a, bn.fact_ids, True, gr))
# directional diversity of the L_addr gradient across facts: per-site query gradients of L_addr vs the answer loss
with torch.no_grad():
    h = h0(bn.tokens[:, :63])
z = zq(h).detach().requires_grad_(True)
q = F.normalize(z, dim=-1)
kn = F.normalize(P["keys"].detach(), dim=-1)
aa = q @ kn.T
lad = F.cross_entropy(aa / 0.2, target_slot[bn.fact_ids.reshape(-1)], reduction="sum")
gz = torch.autograd.grad(lad, z)[0]
gzn = F.normalize(gz, dim=-1)
s = gzn.sum(0)
m = gzn.shape[0]
log["addr_grad_on_z_mean_pairwise_cos_across_sites"] = float((s @ s - m) / (m * (m - 1)))
log["addr_grad_on_z_mean_norm"] = float(gz.norm(dim=-1).mean())

# (3) batch composition
comp = {}
for facts in (2048, 8192):
    st = p9data.training_stream_for(study, SimpleNamespace(is_lane_d=False, facts=facts))
    d = [int(st.batch(u).fact_ids.reshape(-1).unique().numel()) for u in range(1, 65)]
    sites = int(st.batch(1).fact_ids.numel())
    comp[str(facts)] = {"sites_per_batch": sites, "min_distinct": min(d), "max_distinct": max(d)}
log["batch_composition_first_64_batches"] = comp

# (4) G5 as drafted: memory model at init vs frozen backbone on corpus rows (64-byte rows)
with torch.no_grad():
    for p_name, p0 in (("keys", mat(SEED + 1000, N, 16)), ("values", mat(SEED + 2000, N, 32)), ("wq", mat(SEED + 3000, 16, 224)),
                       ("wo", mat(SEED + 4000, 32, 32))):
        P[p_name].copy_(p0)
    P["gate"].fill_(-2.0)
    rows = torch.tensor(list(corpus[: 256 * 64]), dtype=torch.int64).reshape(256, 64)[:, :63]
    with_mem = forward(rows, all_positions=True, memory=True)
    without = forward(rows, all_positions=True, memory=False)
    ref = controls.logits_from_hidden(bbm, controls.insertion_hidden(bbm, rows))  # attempt 1 called bbm(rows): no forward()
    diff = (with_mem - without).abs().amax(dim=(0, 2))
    log["G5_as_drafted"] = {
        "own_no_memory_equals_backbone_module": bool(torch.allclose(without, ref, atol=1e-5)),
        "max_abs_logit_diff_at_read_positions": float(diff[SITES].max()),
        "max_abs_logit_diff_elsewhere": float(diff[[t for t in range(63) if t not in SITES]].max()),
        "rows": 256,
    }
out["results"] = log
print(json.dumps(out, indent=1))
