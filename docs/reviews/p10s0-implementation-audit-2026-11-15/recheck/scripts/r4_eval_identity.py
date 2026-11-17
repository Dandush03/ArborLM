"""Re-check task 4: every evaluated quantity of studies.p10s0.evaluate.evaluate_readout, at tiny size, under whichever studies/ tree is first on PYTHONPATH
(run once with the d27ba7f tree and once with the 3a9a742 tree; r4_compare.py compares the dumps). Arms: A0, A1, A2, A5-D, A6, A7, WX-A5-D, WX-A1 at 2K/4K,
A0/A5-D/A6 at 8K/4K, chunked and unchunked evaluation. Synthetic backbone, S0 unit-test seeds (p10s0-test-8, base 920801) only; single thread.
Usage: PYTHONPATH=<tree> python r4_eval_identity.py <out.json>
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval."""

import json
import math
import sys
import tempfile
from pathlib import Path

import torch

import studies
from studies.p9 import controls
from studies.p9.data import DataSizes, build_study_data
from studies.p10s0 import core, evaluate, train

train.configure()
core.code_identity = lambda *a, **k: {"stub": True}  # identical in both trees (the old tree is not a git repository)
core.environment = lambda *a, **k: {"stub": True}
SPEC = core.test_set(8)
assert 920801 <= SPEC.base <= 920999 - 99
torch.manual_seed(0)
backbone = controls.synthetic_backbone()
g = torch.Generator().manual_seed(12)
corpus = bytes(torch.randint(0, 256, (2048 * 65,), generator=g).tolist())
INIT, FACTS, UNIT = SPEC.base + 41, 128, 8
rows = evaluate.corpus_rows(corpus)
HY = core.HYPER._replace(u_pre=2048.0)


def data_for(real):
    return build_study_data(SPEC.seeds(real), corpus, sizes=DataSizes(main_trained=FACTS, unseen=64, lane_d_per_set=128))


def clean(x):
    if isinstance(x, dict):
        return {k: clean(v) for k, v in x.items() if not any(s in k for s in ("seconds", "wall", "utc", "time"))}
    if isinstance(x, list | tuple):
        return [clean(v) for v in x]
    if isinstance(x, float):
        return repr(x) if not math.isfinite(x) else x.hex()
    if isinstance(x, torch.Tensor):
        return clean(x.tolist())
    return x


out = {"tree": str(Path(studies.__file__).resolve().parent.parent), "records": {}}
for ct, real in (("2K/4K", 2048), ("8K/4K", 8192)):
    data = data_for(real)
    arms = ("A0", "A1", "A2", "A5-D", "A6", "A7", "WX-A5-D", "WX-A1") if ct == "2K/4K" else ("A0", "A5-D", "A6")
    for arm in arms:
        block = "WX" if arm.startswith("WX-") else "Q1"
        cell = core.make_cell(arm, ct, block, 1, 0, "TEST-")
        job = train.Job(cell=cell, mode="dry", data=data, stream=train.training_stream_for(data, FACTS), backbone=backbone, out_dir=Path(tempfile.mkdtemp()) / arm.replace("/", "_"), init_seed=INIT,
                        r1_seed=data.seeds.r1_codes, target_seed=SPEC.base + 40, hyper=HY, unit=UNIT, snapshots=(), max_updates=6, diag_every=10**9)
        ex = train.run_job(job)
        for chunked in (True, False):
            rec = evaluate.evaluate_readout(cell, ex.model, data, FACTS, 6, frozen_backbone=backbone, rows=rows, target_seed=SPEC.base + 40, swap_seed=SPEC.swap_seed(real), chunked=chunked)
            out["records"][f"{arm}@{ct}@chunked={chunked}"] = clean(rec)
Path(sys.argv[1]).write_text(json.dumps(out, indent=0, sort_keys=True, default=str))
print("written", sys.argv[1], len(out["records"]))
