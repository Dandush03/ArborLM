"""D2 (auditor, Opus 5.5): timing of the parts of a registered ``work evaluate`` task that the rehearsal's evaluation_wall_seconds does
not contain (process start and imports are measured by the caller with /usr/bin/time): building a full-size draw (TEST seeds
p9ii-test-9), hashing its streams (verified_data), loading the backbone. Single thread, as the workers run.

usage: d2_task_overhead.py EXPERIMENTS_ROOT
"""
import sys
import time
from pathlib import Path

t0 = time.monotonic()
import torch  # noqa: E402

from studies.p9 import controls, data as p9data  # noqa: E402
from studies.p9 import core as p9core  # noqa: E402
from studies.p9ii import core, stages  # noqa: E402,F401

torch.set_num_threads(1)
t1 = time.monotonic()
ROOT = Path(sys.argv[1])
corpus = p9core.load_trained_corpus(ROOT)
t2 = time.monotonic()
study = p9data.build_study_data(core.test_seeds(9), corpus)
t3 = time.monotonic()
study.sha256s()
t4 = time.monotonic()
controls.load_backbone(p9core.PRIMARY_PARENT, ROOT)
t5 = time.monotonic()
print(f"imports {t1 - t0:.2f} s | corpus {t2 - t1:.2f} s | build draw {t3 - t2:.2f} s | stream hashes {t4 - t3:.2f} s | backbone {t5 - t4:.2f} s | total in-process {t5 - t0:.2f} s")
