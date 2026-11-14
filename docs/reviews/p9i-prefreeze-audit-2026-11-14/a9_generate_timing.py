"""A9 (auditor, Opus 5.5): time of the generate stage's work (data generation + G1 with the registered
permutation count) at full size on rehearsal draw 2, single thread, against the lead's 300 s stage cap.
The rehearsal did not time this stage. Prints the G1 pass flag and timings only."""
import sys
import time
from pathlib import Path

import torch

from studies.p9 import core as p9core
from studies.p9 import data as p9data

torch.set_num_threads(1)
ROOT = Path(sys.argv[1])
t0 = time.monotonic()
study = p9data.build_study_data(p9core.rehearsal_seeds(2), p9core.load_trained_corpus(ROOT))
t1 = time.monotonic()
g1 = p9data.run_g1(study, permutations=None, train_epochs=None)
t2 = time.monotonic()
print(f"data generation {t1 - t0:.1f} s; G1 {t2 - t1:.1f} s; total {t2 - t0:.1f} s; G1 passed {g1['passed']}; checks {len(g1['checks'])}")
