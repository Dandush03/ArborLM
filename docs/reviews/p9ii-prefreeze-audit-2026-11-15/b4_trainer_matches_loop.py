"""B4 (auditor, Opus 5.5): DIAGNOSTIC. The implementer's trainer (studies.p9ii.train.run_job, mode calibration, TEST seeds
p9ii-test-5, init 919001, U_pre 1024) against my own loop of b3 (variant R) on the same draw: the per-update losses of
the first updates and around the switch, and the probe trajectory after the switch. Writes into a scratch directory.

usage: b4_trainer_matches_loop.py EXPERIMENTS_ROOT SCRATCH_DIR
"""
import json
import sys
from pathlib import Path

from studies.p9 import controls, data as p9data
from studies.p9 import core as p9core
from studies.p9ii import core, train
from studies.p9i.train import training_stream_for

ROOT, SCRATCH = Path(sys.argv[1]), Path(sys.argv[2])
train.configure()
seeds = core.test_seeds(5)
study = p9data.build_study_data(seeds, p9core.load_trained_corpus(ROOT))
backbone = controls.load_backbone(p9core.PRIMARY_PARENT, ROOT)[0]
cell = core.make_cell("A2", 4096, stage=1)
job = train.TrainJob(cell=cell, hyper=core.Hyper(u_pre=1024.0), updates=8192, mode="calibration", data=study, stream=training_stream_for(study, 2048), backbone=backbone,
                     out_dir=SCRATCH / "b4_a2", init_seed=919001, r1_seed=seeds.r1_codes, target_seed=core.target_seed(seeds, 0), stream_seed=core.stream_seed(seeds, 0), snapshots=(), max_updates=1600)
run = train.run_job(job)
mine = json.loads((Path(__file__).parent / "outputs" / "b3_R_test5_upre1024.json").read_text())
theirs = {r["update"]: r for r in run.updates}
print("my loop target seed = facts + 40 =", seeds.facts + 40, "; theirs", job.target_seed)
for u, loss in mine["loss_first"] + mine["loss_around_switch"]:
    t = theirs[u]
    ref = t["address_loss"] if t["phase"] == 1 else t["task_loss"]
    print(f"update {u} phase {t['phase']}: mine {loss:.7f} theirs {ref:.7f} diff {abs(loss - ref):.2e}")
mine_log = {r["update"]: r for r in mine["log"]}
for d in run.diagnostics:
    if d["update"] in (960, 1024, 1088, 1152, 1280, 1536) and d["update"] in mine_log:
        m = mine_log[d["update"]]
        print(d["update"], "theirs: acc", round(d["probe_accuracy"], 4), "distinct", d["distinct_top1"], "top1", round(d["target_top1_recall"], 4), "top8", round(d["target_top8_recall"], 4), "| mine:", m["acc"], m["distinct"], m["top1_recall"], m["top8_recall"])
