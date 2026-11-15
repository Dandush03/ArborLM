"""A3 (auditor, Opus 5.5): replay rehearsal cells on rehearsal draw 2 and compare bit for bit.

Re-runs the first 64 updates of chosen rehearsal cells with the implementer's own job builder (rehearsal
mode, draw 2, scratch output directory) and compares every tensor of the written model.pt and
optimizer.pt with the rehearsal run's. Equality shows (i) the rehearsal used draw 2 and the rehearsal
initialization seeds, (ii) training is deterministic across processes. Also checks, from the rehearsal
snapshot alone, that every frozen backbone tensor equals the verified frozen backbone and, for BB cells,
that exactly the 4,224 block-0 attention parameters moved. No loss or accuracy is computed or printed.

usage: a3_rehearsal_replay.py REHEARSAL_RUN EXPERIMENTS_ROOT SCRATCH LABEL...
"""
import argparse
import sys
from pathlib import Path

import torch

from studies.p9 import controls
from studies.p9i import core, stages, train

RUN, ROOT, SCRATCH = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
train.configure()
args = argparse.Namespace(mode="rehearsal", draw=2, dry=False, synthetic_backbone=False, experiments_root=str(ROOT), updates=64, calibration=None)
study = stages.study_data(args)
print("seed set", study.seeds.name)
ATT = ("blocks.0.qkv.weight", "blocks.0.qkv.bias", "blocks.0.attn_out.weight", "blocks.0.attn_out.bias")
for label in sys.argv[4:]:
    cell = core.parse_label(label)
    frozen = controls.load_backbone(cell.parent, ROOT)[0].state_dict()
    theirs = torch.load(RUN / "cells" / label / "snapshots" / "u0000064" / "model.pt", weights_only=True)["model"]
    moved = {k: int((theirs["backbone." + k] != v).sum()) for k, v in frozen.items() if not torch.equal(theirs["backbone." + k], v)}
    att_numel = sum(frozen[k].numel() for k in ATT)
    out = SCRATCH / label
    job = stages.build_job(args, cell, study, out, 64, snapshots=(64,), max_updates=64, mode="rehearsal")
    print(label, "init_seed", job.init_seed)
    train.train_cell(job)
    mine = torch.load(out / "snapshots" / "u0000064" / "model.pt", weights_only=True)["model"]
    same_model = mine.keys() == theirs.keys() and all(torch.equal(mine[k], theirs[k]) for k in mine)
    o1 = torch.load(out / "snapshots" / "u0000064" / "optimizer.pt", weights_only=True)["optimizers"]
    o2 = torch.load(RUN / "cells" / label / "snapshots" / "u0000064" / "optimizer.pt", weights_only=True)["optimizers"]
    same_opt = len(o1) == len(o2) == 1 and all(
        all(torch.equal(a, b) if torch.is_tensor(a) else a == b for a, b in zip(o1[0]["state"][i].values(), o2[0]["state"][i].values(), strict=True))
        for i in o1[0]["state"]
    ) and o1[0]["param_groups"] == o2[0]["param_groups"]
    groups = o2[0]["param_groups"]
    print(f"  replay model identical: {same_model}; optimizer identical: {same_opt}; optimizers: {len(o2)}; groups: {len(groups)}; lr {groups[0]['lr']} wd {groups[0]['weight_decay']}; params in the group: {len(groups[0]['params'])}")
    print(f"  backbone tensors that differ from the frozen backbone: {sorted(moved)} (block-0 attention numel {att_numel})")
