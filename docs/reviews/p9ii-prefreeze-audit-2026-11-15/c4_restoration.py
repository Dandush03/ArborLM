"""C4 (auditor, Opus 5.5): determinism and checkpoint restoration at real size (4,096 slots / 2,048 facts, the real backbone) on TEST
seeds p9ii-test-8, straddling A2's switch (U_pre 96 with a split at 64 and a total of 192), A4's schedule (T_A = 128 of 256 updates, k0 =
N/8) and a diagnostics record (every 64 updates), for every learned arm; also two identical runs of A5-C and A1-S, and the diagnostics
lines of the straight and resumed runs after the split.

usage: c4_restoration.py EXPERIMENTS_ROOT SCRATCH_DIR
"""
import json
import sys
from pathlib import Path

import torch

from studies.p9 import controls, data as p9data
from studies.p9 import core as p9core
from studies.p9ii import core, train
from studies.p9i.train import training_stream_for

ROOT, SCRATCH = Path(sys.argv[1]), Path(sys.argv[2]) / "c4"
train.configure()
seeds = core.test_seeds(8)
study = p9data.build_study_data(seeds, p9core.load_trained_corpus(ROOT))
backbone = controls.load_backbone(p9core.PRIMARY_PARENT, ROOT)[0]
stream = training_stream_for(study, 2048)
hy = core.Hyper(lambda_=1.0, u_pre=96.0 * core.UPDATES / 256, k0_fraction=0.125, mu=1.0)


def job(arm, name, **kw):
    return train.TrainJob(cell=core.make_cell(arm, 4096), hyper=hy, updates=256, unit=256, mode="calibration", data=study, stream=stream, backbone=backbone, out_dir=SCRATCH / name,
                          init_seed=919201, r1_seed=seeds.r1_codes, target_seed=core.target_seed(seeds, 0), stream_seed=core.stream_seed(seeds, 0), snapshots=(), **kw)


for arm in core.LEARNED_ARMS:
    j = job(arm, f"restore_{arm}")
    r = train.checkpoint_restoration_check(j, 64)
    straight = [json.loads(x) for x in (SCRATCH / f"restore_{arm}" / "restore_check" / "straight" / "diagnostics.jsonl").read_text().splitlines()]
    resumed = [json.loads(x) for x in (SCRATCH / f"restore_{arm}" / "restore_check" / "resumed" / "diagnostics.jsonl").read_text().splitlines()]
    s_after = [d for d in straight if d["update"] > 64]
    drop = ("mean_update_seconds", "peak_rss_bytes")
    same_diag = [{k: v for k, v in d.items() if k not in drop} for d in s_after] == [{k: v for k, v in d.items() if k not in drop} for d in resumed]
    sched = train.Trainer(j, __import__("studies.p9ii.model", fromlist=["x"]).build_model(arm, 4096, 919201, backbone, seed_rng=False), __import__("studies.p9ii.diagnostics", fromlist=["x"]).build_probe(study, 2048)).schedule
    print(arm, "identical:", r["identical"], "tensors:", r["tensors_compared"], "mismatches:", r["mismatches"][:3], "| diagnostics after the split identical (except timing):", same_diag, "| schedule:", tuple(sched))
for arm in ("A5-C", "A1-S", "A4"):
    a = train.run_job(job(arm, f"det1_{arm}", max_updates=130))
    b = train.run_job(job(arm, f"det2_{arm}", max_updates=130))
    same = all(torch.equal(p, dict(b.model.named_parameters())[n]) for n, p in a.model.named_parameters()) and all(torch.equal(x, dict(b.model.named_buffers())[n]) for n, x in a.model.named_buffers())
    print(arm, "two identical runs bit-identical (parameters and buffers):", same)
