"""B3 (auditor, Opus 5.5): DIAGNOSTIC trainings on P9-II TEST seeds (core.test_seeds(k), 910001+; never calibration,
rehearsal 3/4/5 or registered seeds) to test why A2 ends near chance. Not registered evidence; not a result.

My own training loop (AdamW lr 0.003, betas (0.9, 0.999), eps 1e-8, no weight decay, one global clip at 1.0, the
alphabet loss at the eight answer sites, my own L_addr = CE over all N cosine scores / 0.2 against an injection drawn
as randperm(N, seed)[:F]). The model object (frozen backbone + W7 memory) is studies.p9ii.model.P9IIModel at 4,096
slots / 2,048 facts; the training stream is studies.p9i.train.training_stream_for (the P9 generator). Variants of the
phase-2 recipe after U_pre updates of L_addr-only on (wq, keys):

  R  registered: L_addr removed, everything trainable, a fresh AdamW (all moments and counters reset)
  F  addresses frozen: wq and keys frozen in phase 2, fresh AdamW over values, wo, gate
  K  no reset for the addresses: wq and keys keep their phase-1 AdamW moments and counters; values, wo, gate fresh
  S  slow addresses: as R but the learning rate of wq and keys is 0.0003 in phase 2
  P  as R, but the first 256 phase-2 updates train only values, wo and gate (answer path first), then everything

Measured every 64 updates on the draw's calibration stream (trained facts, both occurrences of the first 256 facts:
the probe of ADR-0019 section 8.1, rebuilt here): probe accuracy (ties wrong), distinct top-1 slots, largest top-1
share, top-1 / top-8 recall of the target slot, mean cosine between different facts' queries.

usage: b3_a2_mechanism.py EXPERIMENTS_ROOT TEST_OFFSET VARIANT U_PRE TOTAL [compare-out-dir]
"""
import json
import math
import sys
from pathlib import Path

import torch
from torch.nn import functional as F

from studies.p9 import controls, data as p9data
from studies.p9 import core as p9core
from studies.p9ii import core
from studies.p9ii.model import build_model
from studies.p9i.train import training_stream_for

torch.set_num_threads(1)
torch.use_deterministic_algorithms(True)
ROOT, OFFSET, VARIANT, U_PRE, TOTAL = Path(sys.argv[1]), int(sys.argv[2]), sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
SITES = [8 * r + 6 for r in range(8)]
ALPHA = list(range(0x40, 0x60))
FACTS, SLOTS, INIT = 2048, 4096, 919001

seeds = core.test_seeds(OFFSET)
assert seeds.name.startswith("p9ii-test") and 910001 <= seeds.facts <= 919999
corpus = p9core.load_trained_corpus(ROOT)
backbone = controls.load_backbone(p9core.PRIMARY_PARENT, ROOT)[0]
study = p9data.build_study_data(seeds, corpus)
stream = training_stream_for(study, FACTS)
gen = torch.Generator().manual_seed(seeds.facts + 40)
injection = torch.randperm(SLOTS, generator=gen)[:FACTS]

# probe (section 8.1): first 256 trained facts of the restricted calibration stream, both occurrences
cs = study.streams["calibration"]
keep = (cs.fact_ids < FACTS).all(1)
ptoks, pids = cs.tokens[keep], cs.fact_ids[keep]
first, seen = [], set()
for f in pids.reshape(-1).tolist():
    if f not in seen:
        seen.add(f)
        first.append(f)
        if len(first) == 256:
            break
pmask = torch.isin(pids, torch.tensor(first))
rows = pmask.any(1)
ptoks, pids, pmask = ptoks[rows], pids[rows], pmask[rows]

model = build_model("A2", SLOTS, INIT, backbone)
mem = model.addition
named = dict(mem.named_parameters())


def query(tokens):
    h = model.embed_block0(tokens[:, :63])
    z = model.answer_z(h, tokens)  # [B, 8, 16]
    return z / z.norm(dim=-1, keepdim=True).clamp_min(1e-8)


def addr_loss(tokens, fact_ids):
    q = query(tokens).reshape(-1, 16)
    k = mem.keys / mem.keys.norm(dim=-1, keepdim=True).clamp_min(1e-8)
    return F.cross_entropy((q @ k.T) / 0.2, injection[fact_ids.reshape(-1)])


def answer_loss(tokens):
    logits, _ = model(tokens[:, :-1])
    z = logits[:, SITES][..., ALPHA]
    return F.cross_entropy(z.reshape(-1, 32), (tokens[:, 1:][:, SITES] - 0x40).reshape(-1))


@torch.no_grad()
def probe(update, phase):
    model.eval()
    logits, _ = model(ptoks[:, :63])
    z = logits[:, SITES][..., ALPHA]
    ans = ptoks[:, 1:][:, SITES] - 0x40
    mine = z.gather(-1, ans[..., None]).squeeze(-1)
    other = z.scatter(-1, ans[..., None], -math.inf).amax(-1)
    corr = (mine > other)[pmask]
    q = query(ptoks)[pmask]
    k = mem.keys / mem.keys.norm(dim=-1, keepdim=True).clamp_min(1e-8)
    top8 = (q @ k.T).argsort(dim=-1, descending=True, stable=True)[:, :8]
    tgt = injection[pids[pmask]]
    counts = torch.bincount(top8[:, 0])
    f = pids[pmask]
    diff = f[:, None] != f[None, :]
    model.train()
    return {"update": update, "phase": phase, "acc": round(float(corr.float().mean()), 4), "distinct": int((counts > 0).sum()), "largest": round(float(counts.max()) / q.shape[0], 4),
            "top1_recall": round(float((top8[:, 0] == tgt).float().mean()), 4), "top8_recall": round(float((top8 == tgt[:, None]).any(-1).float().mean()), 4),
            "mean_cos": round(float((q @ q.T)[diff].mean()), 4), "gate": round(float(torch.sigmoid(mem.gate)), 4)}


def adamw(params, lr=0.003):
    return torch.optim.AdamW(params, lr=lr, betas=(0.9, 0.999), eps=1e-8, weight_decay=0, amsgrad=False, foreach=False, fused=False)


for p in model.parameters():
    p.requires_grad_(False)
for n in ("wq", "keys"):
    named[n].requires_grad_(True)
opt = adamw([named["wq"], named["keys"]])
log = []
losses = []
model.train()
for u in range(1, TOTAL + 1):
    b = stream.batch(u)
    if u == U_PRE + 1:
        for n in ("values", "wo", "gate"):
            named[n].requires_grad_(True)
        if VARIANT == "R":
            opt = adamw([named[n] for n in ("keys", "values", "wq", "wo", "gate")])
        elif VARIANT == "F":
            named["wq"].requires_grad_(False)
            named["keys"].requires_grad_(False)
            opt = adamw([named[n] for n in ("values", "wo", "gate")])
        elif VARIANT == "K":
            opt.add_param_group({"params": [named[n] for n in ("values", "wo", "gate")]})
        elif VARIANT == "S":
            opt = torch.optim.AdamW([{"params": [named["wq"], named["keys"]], "lr": 0.0003}, {"params": [named[n] for n in ("values", "wo", "gate")]}], lr=0.003, betas=(0.9, 0.999), eps=1e-8, weight_decay=0, foreach=False)
        elif VARIANT == "P":
            named["wq"].requires_grad_(False)
            named["keys"].requires_grad_(False)
            opt = adamw([named[n] for n in ("values", "wo", "gate")])
    if VARIANT == "P" and u == U_PRE + 257:
        named["wq"].requires_grad_(True)
        named["keys"].requires_grad_(True)
        opt = adamw([named[n] for n in ("keys", "values", "wq", "wo", "gate")])
    phase = 1 if u <= U_PRE else 2
    params = [p for p in model.parameters() if p.requires_grad]
    opt.zero_grad(set_to_none=True)
    loss = addr_loss(b.tokens, b.fact_ids) if phase == 1 else answer_loss(b.tokens)
    loss.backward()
    torch.nn.utils.clip_grad_norm_(params, 1.0)
    opt.step()
    losses.append((u, float(loss)))
    if u % 64 == 0:
        log.append(probe(u, phase))
out = {"variant": VARIANT, "seed_set": seeds.name, "facts_seed": seeds.facts, "u_pre": U_PRE, "total": TOTAL, "init": INIT, "log": log, "loss_first": losses[:3], "loss_around_switch": [x for x in losses if U_PRE - 1 <= x[0] <= U_PRE + 3]}
print(json.dumps({"variant": VARIANT, "seed_set": seeds.name, "u_pre": U_PRE}))
for r in log:
    if r["update"] in (U_PRE - 64, U_PRE, U_PRE + 64, U_PRE + 128, U_PRE + 256, U_PRE + 512) or r["update"] % 512 == 0:
        print(r)
Path(__file__).parent.joinpath("outputs", f"b3_{VARIANT}_test{OFFSET}_upre{U_PRE}.json").write_text(json.dumps(out, indent=0))
