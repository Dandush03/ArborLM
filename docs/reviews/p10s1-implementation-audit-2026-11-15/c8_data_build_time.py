"""Per-task data cost at the registered table size, on a TEST seed set (p10s1-test-8, base 921801): no model is trained, nothing registered is read.
Every registered train / evaluate / simulate task and every draw of the registered gates stage rebuilds the draw (studies.p9.data.build_study_data) and, in registered
mode, hashes it (verified_data -> StudyData.sha256s); the rehearsal tasks build it without hashing. This measures both, and a training_stream_for at 32,768 facts.

Run: PYTHONPATH=. uv run --locked python docs/reviews/p10s1-implementation-audit-2026-11-15/c8_data_build_time.py
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.
"""

import json
import sys
import time

import torch

from studies.p9 import core as p9core
from studies.p9 import data as d
from studies.p10s1 import core
from studies.p10s1 import train as T

torch.set_num_threads(1)
CORPUS = bytes((i * 7 + 3) % 256 for i in range(p9core.CORPUS_ROW_BYTES * 64))
out = {}
for facts in (32768, 65536):
    t0 = time.process_time()
    data = d.build_study_data(core.test_seeds(8), CORPUS, sizes=d.DataSizes(main_trained=facts, unseen=core.UNSEEN_FACTS, lane_d_per_set=core.LANE_D_STUB))
    t1 = time.process_time()
    h = data.sha256s()
    t2 = time.process_time()
    s = T.training_stream_for(data, min(facts, 32768))
    t3 = time.process_time()
    out[facts] = {"build_cpu_s": t1 - t0, "sha256s_cpu_s": t2 - t1, "training_stream_cpu_s": t3 - t2, "streams": len(h)}
json.dump(out, sys.stdout, indent=1)
print()
