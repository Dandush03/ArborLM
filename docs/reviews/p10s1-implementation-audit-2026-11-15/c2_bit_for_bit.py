"""Bit-for-bit: P10S1 F-OQ and R2 against P9-I's R1 and R2 (ADR-0021 section 4), on the real frozen backbone (B101/O301) and test-seed data
(p10s1-test-5, base 921501). Three trainers on the same batches: (a) P9-I's own Trainer, (b) P10S1's Trainer, (c) the auditor's own loop written
from the ADR text (alphabet CE at the 8 answer sites, one AdamW lr 0.003 betas (0.9, 0.999) eps 1e-8 wd 0, clip 1.0, zero grad for unused).
Compares initial parameters, forward logits on 4 batches, and every parameter and optimizer moment after each of K steps, with torch.equal.

Run: PYTHONPATH=. uv run --locked python docs/reviews/p10s1-implementation-audit-2026-11-15/c2_bit_for_bit.py
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.
"""

import json
import sys

import torch
from torch import nn
from torch.nn import functional as F

from studies.p9 import controls
from studies.p9 import core as p9core
from studies.p9 import data as d
from studies.p9i import core as p9icore
from studies.p9i import model as p9imodel
from studies.p9i import train as p9itrain
from studies.p10s1 import core
from studies.p10s1 import model as M
from studies.p10s1 import train as T

torch.set_num_threads(1)
torch.use_deterministic_algorithms(True)

SITES = torch.tensor([8 * r + 6 for r in range(8)])
CORPUS = bytes((i * 7 + 3) % 256 for i in range(p9core.CORPUS_ROW_BYTES * 64))
FACTS = 2048
STEPS = 6


def my_loss(logits, tokens):
    inside = logits[:, SITES][..., 0x40:0x60]
    targets = tokens[:, 1:][:, SITES] - 0x40
    assert int(targets.min()) >= 0 and int(targets.max()) < 32
    return F.cross_entropy(inside.reshape(-1, 32), targets.reshape(-1))


def my_step(model, opt, params, tokens):
    opt.zero_grad(set_to_none=True)
    logits, _ = model(tokens[:, :-1])
    loss = my_loss(logits, tokens)
    grads = torch.autograd.grad(loss, params, allow_unused=True)
    for p, g in zip(params, grads, strict=True):
        p.grad = torch.zeros_like(p) if g is None else g
    nn.utils.clip_grad_norm_(params, 1.0)
    opt.step()
    return float(loss.detach())


def addition_params(model):
    return {n: p for n, p in model.named_parameters() if n.startswith("addition.")}


def moments(opt):
    return [(s["exp_avg"], s["exp_avg_sq"]) for s in opt.state.values()]


def run(arm, slots, backbone, data):
    p9arm = {"F-OQ": "R1", "R2": "R2"}[arm]
    seeds = data.seeds
    lut = T.fact_lut_for(data, FACTS) if arm == "R2" else None
    stream = T.training_stream_for(data, FACTS)
    seed = 2101
    cell = core.make_cell("P", arm, FACTS, slots, 1, seed, run_updates=64, test=True)
    job = T.TrainJob(cell=cell, data=data, stream=stream, backbone=backbone, out_dir=None, r1_seed=seeds.r1_codes, hash_seed=core.h8_seed(seeds), mode="calibration", updates=64, fact_lut=lut)
    theirs_p9 = p9imodel.build_model(p9arm, slots, seed, backbone, fact_lut=lut, r1_seed=seeds.r1_codes)
    p9_trainer = p9itrain.Trainer(p9icore.make_cell(p9arm, slots), theirs_p9, p9itrain.build_optimizers(theirs_p9))
    s1_trainer = T.Trainer(job, T.job_model(job))
    mine_model = p9imodel.build_model(p9arm, slots, seed, backbone, fact_lut=lut, r1_seed=seeds.r1_codes)
    mine_params = [p for _, p in mine_model.named_parameters() if p.requires_grad]
    mine_opt = torch.optim.AdamW(mine_params, lr=0.003, betas=(0.9, 0.999), eps=1e-8, weight_decay=0.0, foreach=False, fused=False)
    out = {"arm": arm, "slots": slots, "init_equal": all(torch.equal(p, addition_params(theirs_p9)[n]) for n, p in addition_params(s1_trainer.model).items()),
           "same_param_names": sorted(addition_params(s1_trainer.model)) == sorted(addition_params(theirs_p9)), "trainable_s1": sum(p.numel() for p in s1_trainer.params)}
    with torch.no_grad():
        theirs_p9.eval(); s1_trainer.model.eval()
        out["forward_equal_4_batches"] = all(torch.equal(theirs_p9(stream.batch(u).tokens[:, :-1])[0], s1_trainer.model(stream.batch(u).tokens[:, :-1])[0]) for u in (1, 2, 3, 4))
    steps = []
    for u in range(1, STEPS + 1):
        b = stream.batch(u)
        l9 = p9_trainer.step(b.tokens)["task_loss"]
        l1 = s1_trainer.step(b)["task_loss"]
        lm = my_step(mine_model, mine_opt, mine_params, b.tokens)
        pa, pb, pc = addition_params(theirs_p9), addition_params(s1_trainer.model), addition_params(mine_model)
        steps.append({
            "update": u, "loss_p9i": l9, "loss_s1": l1, "loss_mine": lm, "loss_equal": l9 == l1 == lm,
            "params_s1_eq_p9i": all(torch.equal(pb[n], pa[n]) for n in pa), "params_mine_eq_p9i": all(torch.equal(pc[n], pa[n]) for n in pa),
            "moments_s1_eq_p9i": all(torch.equal(x[0], y[0]) and torch.equal(x[1], y[1]) for x, y in zip(moments(s1_trainer.optimizers[0]), moments(p9_trainer.optimizers[0]), strict=True)),
        })
    out["steps"] = steps
    out["all_equal"] = out["init_equal"] and out["forward_equal_4_batches"] and all(s["loss_equal"] and s["params_s1_eq_p9i"] and s["params_mine_eq_p9i"] and s["moments_s1_eq_p9i"] for s in steps)
    return out


def main():
    root = p9core.default_experiments_root()
    backbone, _ = controls.load_backbone(p9core.PRIMARY_PARENT, root)
    data = d.build_study_data(core.test_seeds(5), CORPUS, sizes=d.DataSizes(main_trained=FACTS, unseen=64, lane_d_per_set=128))
    res = []
    for arm, slots in (("F-OQ", 4096), ("F-OQ", 16384), ("F-OQ", 65536), ("R2", 4096), ("R2", 65536)):
        r = run(arm, slots, backbone, data)
        res.append(r)
        print(arm, slots, r["all_equal"], file=sys.stderr)
    json.dump({"backbone": "B101/O301 from " + str(root), "data": data.seeds.name, "steps": STEPS, "results": res}, sys.stdout, indent=1)
    print()


if __name__ == "__main__":
    main()
