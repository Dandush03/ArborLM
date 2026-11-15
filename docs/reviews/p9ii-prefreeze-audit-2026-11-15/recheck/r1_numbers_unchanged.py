"""R1 (auditor, Opus 5.5, re-check): does any number a cell computes differ between the calibration commit 3d779e1 and HEAD?
The calibration-commit package studies/p9ii is extracted (git archive 3d779e1) and imported as ``oldp9ii`` next to HEAD's ``studies.p9ii``
(studies/p9, studies/p9i, src, uv.lock are unchanged between the two commits). TEST seeds only.

  mode train SLOTS: every arm trained with the old and the new trainer on the same job (unit 256, 192 updates: A2 switches at 96, A4 anneals
                    to 128, diagnostics every 64); compare every parameter and buffer, every per-update record field and every diagnostics field
                    except timing and memory.
  mode eval SLOTS:  every arm trained briefly (64 updates, new trainer), then the OLD evaluate_readout and HEAD's evaluate_readout (chunked, the
                    registered default) on the same model; compare the whole eval record except identity/environment.

usage: r1_numbers_unchanged.py EXPERIMENTS_ROOT OLD_PKG_PARENT SCRATCH MODE SLOTS ARMS(comma)
"""
import json
import sys
from pathlib import Path

ROOT, OLD, SCRATCH, MODE, SLOTS, ARMS = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), sys.argv[4], int(sys.argv[5]), sys.argv[6].split(",")
sys.path.insert(0, OLD)
import torch  # noqa: E402

import oldp9ii.core as ocore  # noqa: E402
import oldp9ii.evaluate as oeval  # noqa: E402
import oldp9ii.train as otrain  # noqa: E402
from studies.p9 import controls, data as p9data  # noqa: E402
from studies.p9 import core as p9core  # noqa: E402
from studies.p9ii import core, evaluate, train  # noqa: E402
from studies.p9i.train import training_stream_for  # noqa: E402

train.configure()
ocore.repo_root = core.repo_root  # attempt 2 failed: the extracted old package hashed sources relative to the scratch tree (identity fields only; they are excluded from every comparison)
seeds = core.test_seeds(10 + {4096: 0, 16384: 1, 65536: 2}[SLOTS])
study = p9data.build_study_data(seeds, p9core.load_trained_corpus(ROOT))
backbone = controls.load_backbone(p9core.PRIMARY_PARENT, ROOT)[0]
facts = core.FACTS_PROPORTIONAL[SLOTS]
stream = training_stream_for(study, facts)
stage = {4096: 1, 16384: 2, 65536: 3}[SLOTS]
DROP = {"seconds", "rss_bytes", "mean_update_seconds", "peak_rss_bytes"}


def job(pkg_core, pkg_train, arm, name, updates, unit, max_updates=None):
    hy = pkg_core.Hyper(lambda_=1.0, u_pre=3072.0, k0_fraction=0.125, mu=1.0)  # with unit 256: U_pre 96 at Stage 1
    st = stage if not (arm in ("A2", "A4") and stage == 3) else 1
    return pkg_train.TrainJob(cell=pkg_core.make_cell(arm, SLOTS, stage=st), hyper=hy, updates=updates, unit=unit, stage=st, mode="calibration", data=study, stream=stream, backbone=backbone,
                              out_dir=SCRATCH / name, init_seed=919301, r1_seed=seeds.r1_codes, target_seed=core.target_seed(seeds, 0), stream_seed=core.stream_seed(seeds, 0), snapshots=(), max_updates=max_updates)


def strip(rows):
    return [{k: v for k, v in r.items() if k not in DROP} for r in rows]


out = {}
for arm in ARMS:
    if MODE == "train":
        unit = 256
        a = otrain.run_job(job(ocore, otrain, arm, f"r1/{SLOTS}/old_{arm}", core.stage_updates(1 if stage == 3 else stage, unit), unit, max_updates=192))
        b = train.run_job(job(core, train, arm, f"r1/{SLOTS}/new_{arm}", core.stage_updates(1 if stage == 3 else stage, unit), unit, max_updates=192))
        params = all(torch.equal(p, dict(b.model.named_parameters())[n]) for n, p in a.model.named_parameters())
        bufs = all(torch.equal(x, dict(b.model.named_buffers())[n]) for n, x in a.model.named_buffers())
        ups = strip(a.updates) == strip(b.updates)
        diag = json.dumps(strip(a.diagnostics), sort_keys=True, default=str) == json.dumps(strip(b.diagnostics), sort_keys=True, default=str)
        out[arm] = {"parameters_identical": params, "buffers_identical": bufs, "update_records_identical": ups, "diagnostics_identical": diag, "updates": len(b.updates), "schedule": tuple(b.trainer.schedule)}
    else:
        run = train.run_job(job(core, train, arm, f"r1/{SLOTS}/evaltrain_{arm}", core.stage_updates(1 if stage == 3 else stage, 256), 256, max_updates=64))
        cell = run.trainer.cell
        rows = evaluate.corpus_rows(p9core.load_trained_corpus(ROOT))
        old = oeval.evaluate_readout(cell, run.model, study, facts, 64, frozen_backbone=backbone, rows=rows, target_seed=core.target_seed(seeds, 0))
        new = evaluate.evaluate_readout(cell, run.model, study, facts, 64, frozen_backbone=backbone, rows=rows, target_seed=core.target_seed(seeds, 0))
        unch = evaluate.evaluate_readout(cell, run.model, study, facts, 64, frozen_backbone=backbone, rows=rows, target_seed=core.target_seed(seeds, 0), chunked=False)
        norm = lambda r: json.dumps(core.jsonable({k: v for k, v in r.items() if k not in ("identity", "environment")}), sort_keys=True)
        out[arm] = {"old_equals_new_chunked": norm(old) == norm(new), "new_unchunked_equals_chunked": norm(unch) == norm(new), "acc_A": new["panels"]["A"]["accuracy"], "probe_distinct": new["probe"].get("distinct_top1")}
    print(arm, SLOTS, out[arm], flush=True)
Path(__file__).parent.joinpath("outputs", f"r1_{MODE}_{SLOTS}.json").write_text(json.dumps(out, indent=1, default=str))
print("ALL IDENTICAL" if all(all(v for k, v in o.items() if isinstance(v, bool)) for o in out.values()) else "DIFFERENCES FOUND")
