"""M6 re-check: the whole-update multiply-add count of ADR-0021 section 22 M6 / 22.1, recomputed three ways for every arm and slot count.

1. My own hand count from the architecture (width 32, 2 blocks, 4 heads x 8, FFN 64, vocabulary 256, T = 63, B = 16, Q = 8 B = 128 answer-site queries),
   written from the section 22.1 text: every matrix product AND every gather-weighted sum of the forward and backward pass, plus 4 x trainable for AdamW.
   The gather-weighted sum is the value read  combined = sum_k w_k * values[chosen_k]  (studies/p9/model.py ScalableMemory.delta); its forward is Q k 32,
   its backward Q k 32 for the value rows and, where the weights carry a gradient (F-OQ, T-OQ: learned keys), Q k 32 for the weights.
2. torch.utils.flop_counter over one real Trainer.step (forward + backward; AdamW and the clip are elementwise and are not counted), after one warm-up step,
   on the real frozen backbone B101/O301 and test-seed data (p10s1-test-6), as the predecessor's c3 did.
3. studies.p10s1.frozen.analytic_madds_per_update (the implementation; the config formula) and matmul_madds_per_update.
Then the MC multipliers of every capacity, dense and diagonal pair under the madds measure alone (the CPU measure can only raise a multiplier, as the larger is used).

Run (worktree root): PYTHONPATH=. uv run --locked python docs/reviews/p10s1-implementation-audit-2026-11-15/recheck/r2_madds.py
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.
"""

import json
import sys

import torch
from torch.utils.flop_counter import FlopCounterMode

from studies.p9 import controls
from studies.p9 import core as p9core
from studies.p9 import data as d
from studies.p10s1 import core
from studies.p10s1 import frozen as fz
from studies.p10s1 import model as M
from studies.p10s1 import train as T

torch.set_num_threads(1)
CORPUS = bytes((i * 7 + 3) % 256 for i in range(p9core.CORPUS_ROW_BYTES * 64))
SLOTS = (4096, 16384, 65536)
ARMS = ("F-OQ", "T-OQ", "H8", "R2", "D-OQ")
B, TT, W, FFN, V, HEADS, HW = 16, 63, 32, 64, 256, 4, 8
Q = 8 * B
GRID = (1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0)
U_P = 8192


def my_backbone():
    attn = HEADS * TT * TT * HW
    block = TT * W * 3 * W + 2 * attn + TT * W * W + 2 * TT * W * FFN
    fwd = B * (2 * block + TT * W * V)
    # weights frozen; the addition enters after block 0, so input gradients flow through block 1 and the head only; both attention products need both operands' gradients
    bwd = B * (TT * W * 3 * W + TT * W * W + 2 * TT * W * FFN + 2 * 2 * attn + TT * W * V)
    return fwd, bwd


def my_doq_hidden(n):
    p_f = n * (16 + 32) + 32 * 32 + 1
    return min(range(max(1, p_f // 49 - 2), p_f // 49 + 3), key=lambda h: (abs(49 * h + 1 - p_f), h))


def my_trainable(arm, n):
    if arm == "D-OQ":
        return 49 * my_doq_hidden(n) + 1
    if arm in ("F-OQ",):
        return n * 48 + 32 * 32 + 1
    if arm == "T-OQ":
        return n * 48 + (n // 256) * 16 + 32 * 32 + 1
    if arm in ("H8", "R2"):
        return n * 32 + 32 * 32 + 1
    raise ValueError(arm)


def my_arm(arm, n, k_read):
    wo = 3 * Q * W * W
    if arm == "F-OQ":
        mm = 2 * Q * n * 16 + wo
        gws = 3 * Q * k_read * W
    elif arm == "T-OQ":
        mm = 2 * Q * ((n // 256) * 16 + 512 * 16) + wo
        gws = 3 * Q * k_read * W
    elif arm in ("H8", "R2"):
        mm = wo
        gws = 2 * Q * k_read * W
    else:
        h = my_doq_hidden(n)
        mm = 2 * Q * 16 * h + 3 * Q * h * W
        gws = 0
    return mm, gws


def counted(arm, n, backbone, data):
    facts = 2048
    cell = core.make_cell("P", arm, facts, n, 1, 2101, run_updates=8, test=True)
    lut = T.fact_lut_for(data, facts) if arm == "R2" else None
    job = T.TrainJob(cell=cell, data=data, stream=T.training_stream_for(data, facts), backbone=backbone, out_dir=None, r1_seed=data.seeds.r1_codes, hash_seed=core.h8_seed(data.seeds), mode="calibration", updates=8, fact_lut=lut)
    model = T.job_model(job)
    tr = T.Trainer(job, model)
    tr.step(job.stream.batch(1))
    fc = FlopCounterMode(display=False)
    with fc:
        tr.step(job.stream.batch(2))
    k_read = None
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    if arm != "D-OQ":
        tok = job.stream.batch(3).tokens[:, :-1]
        with torch.no_grad():
            sel = model.select(model.embed_block0(tok), tok)
        k_read = int(sel.selected.shape[-1])
    return fc.get_total_flops(), k_read, trainable


def mc(ratio, run_cheaper):
    for g in GRID:
        if g >= ratio - 1e-12:
            return g, ("OK" if g * U_P <= run_cheaper else "MC-SHORT")
    return None, "MC-SHORT"


def main():
    backbone, _ = controls.load_backbone(p9core.PRIMARY_PARENT, p9core.default_experiments_root())
    data = d.build_study_data(core.test_seeds(6), CORPUS, sizes=d.DataSizes(main_trained=2048, unseen=64, lane_d_per_set=128))
    bf, bb = my_backbone()
    out = {"my_backbone": {"forward": bf, "backward": bb, "total": bf + bb}, "impl_backbone": fz.backbone_madds(16), "cells": {}}
    mine_total, impl_total = {}, {}
    for arm in ARMS:
        for n in SLOTS:
            flops, k_read, trainable_built = counted(arm, n, backbone, data)
            mm, gws = my_arm(arm, n, k_read or 0)
            my_tr = my_trainable(arm, n)
            mine = bf + bb + mm + gws + 4 * my_tr
            impl = fz.analytic_madds_per_update(arm, n)
            mine_total[(arm, n)], impl_total[(arm, n)] = mine, impl
            out["cells"][f"{arm}|{n}"] = {
                "k_read": k_read, "my_matmul": bf + bb + mm, "torch_counter_madds": flops / 2, "impl_matmul": fz.matmul_madds_per_update(arm, n),
                "my_gather_weighted_sum": gws, "my_trainable": my_tr, "built_trainable": trainable_built, "impl_trainable": fz.trainable_parameters(arm, n),
                "my_whole_update": mine, "impl_whole_update": impl, "impl_minus_mine": impl - mine, "relative": (impl - mine) / mine,
            }
    run = {4096: 6 * U_P, 16384: 4 * U_P, 65536: 2 * U_P}
    pairs = []
    for arm in ("F-OQ", "T-OQ", "H8"):
        for s, l in ((4096, 16384), (16384, 65536)):
            pairs.append((f"cap|{arm}|{s}->{l}", (arm, s), (arm, l)))
        for n in (16384, 65536):
            pairs.append((f"dense|{arm}|{n}", (arm, n), ("D-OQ", n)))
    rows = {}
    for key, a, b in pairs:
        row = {}
        for name, table in (("mine", mine_total), ("impl", impl_total)):
            ratio = table[b] / table[a]
            cheaper_run = run[a[1]] if ratio >= 1 else run[b[1]]
            row[name] = {"ratio": ratio, **dict(zip(("grid", "status_madds_only"), mc(max(ratio, 1 / ratio), cheaper_run), strict=True))}
        rows[key] = row
    out["pairs"] = rows
    # the implementation's own frozen MC plan with a CPU table of all-equal costs (so madds decides) for comparison
    flat_cpu = {(a, n): 1.0 for a in ARMS for n in SLOTS}
    fro = fz.Frozen.build(core.Plan(seed_block_draws=()), flat_cpu)
    out["impl_mc_plan_with_flat_cpu"] = {k: (v.status, v.small_update, v.large_update, round(v.multiplier, 4)) for k, v in sorted(fro.mc.items())}
    json.dump(out, sys.stdout, indent=1, default=str)
    print()


if __name__ == "__main__":
    main()
