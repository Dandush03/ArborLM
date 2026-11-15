"""R3 (auditor, Opus 5.5, re-check): time of the per-draw work the REGISTERED gates stage adds (HEAD's work_gates, registered branch):
for each of the 14 draw slots, verified_data (build + stream hashes) and evaluate.controls_record (G2) at the size the draw is used at
(8 draws at 2,048 facts, 4 at 8,192, 2 at 32,768). Measured here on TEST seeds (p9ii-test-20..22), single thread, one draw per size; the
registered total is extrapolated by count. The rehearsal-mode gates run that set the gates cap (8.3 s) did this for one draw only.

usage: r3_registered_gates_time.py EXPERIMENTS_ROOT
"""
import sys
import time
from pathlib import Path

import torch

from studies.p9 import controls, data as p9data
from studies.p9 import core as p9core
from studies.p9ii import core, evaluate

torch.set_num_threads(1)
ROOT = Path(sys.argv[1])
corpus = p9core.load_trained_corpus(ROOT)
backbone = controls.load_backbone(p9core.PRIMARY_PARENT, ROOT)[0]
per = {}
for i, (facts, count) in enumerate(((2048, 8), (8192, 4), (32768, 2))):
    t0 = time.monotonic()
    study = p9data.build_study_data(core.test_seeds(20 + i), corpus)
    study.sha256s()
    t1 = time.monotonic()
    rec = evaluate.controls_record(study, {p9core.PRIMARY_PARENT: backbone}, [facts])
    t2 = time.monotonic()
    per[facts] = (t1 - t0, t2 - t1, count, bool(rec["g2"]["passed"]))
    print(f"facts {facts}: build+hash {t1 - t0:.2f} s, controls_record (G2) {t2 - t1:.2f} s, used by {count} draws, g2 passed {rec['g2']['passed']}", flush=True)
total = sum((b + c) * n for b, c, n, _ in per.values())
print(f"extrapolated per-draw work of the registered gates stage: {total:.1f} s (+ the rehearsal-mode gates work, 8.3 s measured) against the cap max(60, 2 x 8.3) = 60 s")
