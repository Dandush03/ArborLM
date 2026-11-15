"""D2 (auditor, Opus 5.5) -- DIAGNOSTIC, NOT A RESULT, NOT A RE-RUN OF A REGISTERED CELL.

Runs the implementer's frozen P9-I code path (studies.p9i.model.build_model, train.build_optimizers,
train.Trainer.step) on REHEARSAL draw 2 for one arm at one size, with a non-registered init seed, and
evaluates checkpoints with the auditor's own ties-wrong scoring of the model's logits on draw-2 Panel A.
Purpose: decide whether a difference between d1 (auditor's trainer) and the registered result comes from
the implementation or from the data / seed. Optionally (--lockstep K) runs the auditor's d1-style step
side by side for the first K updates from identical parameters and prints the largest parameter
difference after each of them.

Usage: d2_their_trainer_draw2.py --arm W7 --slots 4096 --facts 2048 --updates 8192 --seed 500001 [--draw 2]
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
from studies.p9i import core, model as m, train

ap = argparse.ArgumentParser()
ap.add_argument("--arm", required=True)
ap.add_argument("--slots", type=int, default=4096)
ap.add_argument("--facts", type=int, default=2048)
ap.add_argument("--updates", type=int, default=8192)
ap.add_argument("--seed", type=int, default=500001)
ap.add_argument("--draw", type=int, default=2)
ap.add_argument("--root", default="/Users/daniellaloush/dandush03/ArborLM/experiments")
ap.add_argument("--checkpoints", default="0,64,256,512,1024,2048,4096,8192")
args = ap.parse_args()
if args.draw not in (0, 2):
    raise SystemExit("diagnostics use rehearsal draws 0 or 2 only")
if args.seed in (1801, 1802, 1791, 1792):
    raise SystemExit("registered or calibration seed refused")
torch.set_num_threads(2)
ROOT = Path(args.root)
SITES = list(core.ANSWER_SITE_POSITIONS)
ALPHA = list(range(0x40, 0x60))
seeds = p9core.rehearsal_seeds(args.draw)
study = p9data.build_study_data(seeds, p9core.load_trained_corpus(ROOT))
stream = p9data.training_stream_for(study, SimpleNamespace(is_lane_d=False, facts=args.facts))
backbone = controls.load_backbone((101, 301), ROOT)[0]
lut = train.fact_lut_for(study, args.facts) if args.arm == "R2" else None
model = m.build_model(args.arm, args.slots, args.seed, backbone, fact_lut=lut, r1_seed=seeds.r1_codes)
opts = train.build_optimizers(model)
trainer = train.Trainer(core.make_cell(args.arm, args.slots), model, opts)
panel = study.streams["panel_a"]
keep = (panel.fact_ids < args.facts).all(1)
ptoks = panel.tokens[keep]
marks = sorted({int(x) for x in args.checkpoints.split(",") if int(x) <= args.updates})
wq0 = model.addition.wq.detach().clone() if hasattr(model.addition, "wq") else None


def evaluate():
    model.eval()
    ok, qs, sel = [], [], []
    with torch.no_grad():
        for s in range(0, ptoks.shape[0], 256):
            t = ptoks[s : s + 256]
            logits, selection = model(t[:, :63])
            z = logits[:, SITES][..., ALPHA]
            ans = t[:, [p + 1 for p in SITES]] - 0x40
            mine = z.gather(-1, ans[..., None]).squeeze(-1)
            other = z.scatter(-1, ans[..., None], -math.inf).amax(-1)
            ok.append((mine > other).reshape(-1))
            q = model.answer_queries(model.embed_block0(t[:, :63]), t[:, :63])
            if q is not None:
                qs.append(q.reshape(-1, q.shape[-1]))
            if selection is not None:
                sel.append(selection.selected.reshape(-1, selection.selected.shape[-1]))
    out = {"accuracy": float(torch.cat(ok).float().mean())}
    if qs:
        Q = torch.cat(qs).double()
        n = Q.shape[0]
        tot = Q.sum(0)
        out["mean_cos"] = float((tot @ tot - n) / (n * (n - 1)))
    if sel:
        S = torch.cat(sel)
        out["distinct_selected"] = int(torch.unique(S[S >= 0]).numel())
        out["distinct_top1"] = int(torch.unique(S[:, 0]).numel())
    if wq0 is not None:
        out["wq_change_rel"] = float((model.addition.wq.detach() - wq0).norm() / wq0.norm())
    return out


t0 = time.time()
losses = []
for u in range(0, args.updates + 1):
    if u in marks:
        r = {"update": u, "train_loss_recent": round(sum(losses) / len(losses), 4) if losses else None} | evaluate()
        print(json.dumps(r), flush=True)
        losses = []
    if u == args.updates:
        break
    rec = trainer.step(stream.batch(u + 1).tokens)
    losses.append(rec["task_loss"])
print(json.dumps({"DIAGNOSTIC": True, "implementation": "studies.p9i (frozen code)", "draw": args.draw, "arm": args.arm, "slots": args.slots,
                  "facts": args.facts, "updates": args.updates, "seed": args.seed, "seconds": round(time.time() - t0, 1)}))
