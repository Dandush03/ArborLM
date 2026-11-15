"""C1: stand-in for the S1 store under oracle addressing (NO ArborLM backbone, NO ArborLM data
generator, NO registered or calibration seed). Synthetic seeds 941001+.

Read path as ADR-0021 section 3 / studies.p9.model.ScalableMemory.delta: top-8 by cosine against
learned keys at temperature 0.2, softmax over the 8, weighted sum of values, wo, sigmoid(gate) (init
-2). The frozen upper block, final LayerNorm and unembedding are replaced by a fixed stand-in readout
logits = A . LN(b + delta) (A fixed random 32x32, b fixed random, LayerNorm without affine). Loss is
32-way cross-entropy; AdamW lr 0.003, no weight decay, clip 1.0, batch 128 facts, every fact once per
epoch. Init N(0, 0.02) as P9. Arms: FOQ (oracle code, learned keys), H8 (8 hashed slots, weight 1/8),
R2 (dedicated slot), DOQ (16 -> h -> 32 GELU MLP, h matched to FOQ's parameter count), FOQW (FOQ with
value width dv). Prints accuracy at snapshots. A stand-in: it says what the read path and optimizer can
do with a linear readout, not what the frozen backbone allows.
"""
import json
import math
import sys
import time
from multiprocessing import Pool

import torch
import torch.nn.functional as F

TEMP, TOP, BATCH, LR = 0.2, 8, 128, 0.003


def mat(gen, *shape):
    return (torch.randn(*shape, generator=gen) * 0.02).requires_grad_(True)


def run(job):
    torch.set_num_threads(1)
    arm, facts, slots, dv, updates, seed = (job[k] for k in ("arm", "facts", "slots", "dv", "updates", "seed"))
    snaps = sorted(set(job.get("snaps", [])) | {updates})
    g = torch.Generator().manual_seed(seed)
    codes = F.normalize(torch.randn(facts, 16, generator=g), dim=-1)
    answers = torch.randint(0, 32, (facts,), generator=g)
    A = torch.randn(32, 32, generator=g)
    b = torch.randn(32, generator=g)
    hashed = torch.stack([torch.randperm(slots, generator=g)[:8] for _ in range(1)])  # placeholder
    # H8: 8 distinct slots per fact from a seeded hash
    h8 = torch.argsort(torch.rand(facts, slots, generator=g), dim=1)[:, :8] if (arm.startswith("H8") and facts * slots <= 2**28) else None
    if arm.startswith("H8") and h8 is None:
        rows = []
        for f0 in range(0, facts, 512):
            rows.append(torch.argsort(torch.rand(min(512, facts - f0), slots, generator=g), dim=1)[:, :8])
        h8 = torch.cat(rows)
    del hashed
    gi = torch.Generator().manual_seed(seed + 1)
    params = {}
    if arm in ("FOQ", "FOQW"):
        params["keys"] = mat(gi, slots, 16)
    if arm in ("FOQ", "FOQW", "H8", "R2"):
        params["values"] = mat(gi, slots, dv)
        params["wo"] = mat(gi, 32, dv)
    if arm == "DOQ":
        hidden = round((48 * slots + 1025 - 1) / 48)
        params["w1"] = mat(gi, hidden, 16)
        params["w2"] = mat(gi, 32, hidden)
    if arm == "DOQS":  # conventionally scaled dense: PyTorch default Linear init with biases, same parameter count
        hidden = round((48 * slots + 1025 - 1) / 49)
        params["w1"] = ((torch.rand(hidden, 16, generator=gi) * 2 - 1) / 4).requires_grad_(True)
        params["b1"] = ((torch.rand(hidden, generator=gi) * 2 - 1) / 4).requires_grad_(True)
        params["w2"] = ((torch.rand(32, hidden, generator=gi) * 2 - 1) / hidden ** 0.5).requires_grad_(True)
    params["gate"] = torch.tensor(-2.0, requires_grad=True)
    nparam = sum(p.numel() for p in params.values())
    opt = torch.optim.AdamW(list(params.values()), lr=job.get("lr", LR), weight_decay=0.0)

    def forward(idx):
        c = codes[idx]
        if arm in ("FOQ", "FOQW"):
            kn = F.normalize(params["keys"], dim=-1, eps=1e-8)
            s = (c @ kn.T) / TEMP
            v, i = torch.topk(s, TOP, dim=-1)
            w = v.softmax(-1)
            comb = (w[..., None] * params["values"][i]).sum(-2)
            delta = params["gate"].sigmoid() * comb @ params["wo"].T
        elif arm == "H8":
            comb = params["values"][h8[idx]].mean(-2)
            delta = params["gate"].sigmoid() * comb @ params["wo"].T
        elif arm == "R2":
            comb = params["values"][idx]
            delta = params["gate"].sigmoid() * comb @ params["wo"].T
        elif arm == "DOQS":
            delta = params["gate"].sigmoid() * F.gelu(c @ params["w1"].T + params["b1"]) @ params["w2"].T
        else:
            delta = params["gate"].sigmoid() * F.gelu(c @ params["w1"].T) @ params["w2"].T
        x = F.layer_norm(b + delta, (32,))
        return x @ A.T

    def accuracy():
        correct = 0
        with torch.no_grad():
            for f0 in range(0, facts, 2048):
                idx = torch.arange(f0, min(facts, f0 + 2048))
                lg = forward(idx)
                top2 = lg.topk(2, dim=-1)
                ok = (top2.indices[:, 0] == answers[idx]) & (top2.values[:, 0] > top2.values[:, 1])
                correct += int(ok.sum())
        return correct / facts

    out = {**job, "params": nparam, "acc": {}}
    t0 = time.process_time()
    perm = torch.randperm(facts, generator=g)
    pos = 0
    for u in range(1, updates + 1):
        if pos + BATCH > facts:
            perm = torch.randperm(facts, generator=g)
            pos = 0
        idx = perm[pos:pos + BATCH]
        pos += BATCH
        loss = F.cross_entropy(forward(idx), answers[idx])
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(list(params.values()), 1.0)
        opt.step()
        if u in snaps:
            out["acc"][u] = accuracy()
    out["cpu_s"] = round(time.process_time() - t0, 1)
    return out


def fano(a):
    e = 1 - a
    if a <= 1 / 32:
        return 0.0
    h2 = 0.0 if e in (0, 1) else -(e * math.log2(e) + (1 - e) * math.log2(1 - e))
    return 5 - h2 - e * math.log2(31)


if __name__ == "__main__":
    jobs = json.load(open(sys.argv[1]))
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    with Pool(workers) as pool:
        for r in pool.imap_unordered(run, jobs):
            accs = " ".join(f"{u}:{a:.3f}/{fano(a):.2f}b" for u, a in sorted(r["acc"].items(), key=lambda t: int(t[0])))
            print(f"{r["arm"]:5s} lr={r.get("lr", LR)} dv={r['dv']:3d} F={r['facts']:6d} N={r['slots']:6d} seed={r['seed']} params={r['params']:8d} cpu={r['cpu_s']:7.1f}s | {accs}", flush=True)
