"""A6 (auditor, Opus 5.5): forward-only replay of the recorded training loss of calibration cells.

For snapshot u of a calibration cell, the batch of update u + 1 is rebuilt from rehearsal draw 1 with
studies.p9.data (training schedule over the first F facts), the auditor's own forward (a2's function
definitions, loaded from a2's source) gives the 32-way alphabet cross-entropy at the 8 answer sites and the 256-way one; both
are compared with line u + 1 of the cell's updates.jsonl ("task_loss", "answer_loss_256"). Agreement
to float precision shows that the run trained on draw 1's stream with the alphabet loss at answer sites.
Nothing is trained.
"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import torch
from torch.nn import functional as F

from studies.p9 import data as p9data
from studies.p9 import core as p9core

sys.argv, _jobs = sys.argv[:3], sys.argv[3:]
RUN, ROOT = Path(sys.argv[1]), Path(sys.argv[2])
SITES = [8 * r + 6 for r in range(8)]
ALPHA = list(range(0x40, 0x60))

# re-use the auditor's own forward from a2 without running a2's main: exec only its function definitions
src = Path(__file__).with_name("a2_rescore_snapshots.py").read_text().split("corpus = p9core.load_trained_corpus")[0]
src = src.replace("RUN, ROOT = Path(sys.argv[1]), Path(sys.argv[2])", "")
ns: dict = {"__name__": "a2funcs"}
exec(compile(src, "a2_functions", "exec"), ns)  # noqa: S102
forward = ns["forward"]

corpus = p9core.load_trained_corpus(ROOT)
seeds = p9core.rehearsal_seeds(1)
study = p9data.build_study_data(seeds, corpus)
for job in _jobs:
    label, ups = job.split(":")
    parts = label.split("-")
    arm, slots = parts[1], int(parts[2][1:])
    F_ = {4096: 2048, 16384: 8192, 65536: 32768}[slots]
    stream = p9data.training_stream_for(study, SimpleNamespace(is_lane_d=False, facts=F_))
    enc = (study.facts.ident[:F_, :4] * torch.tensor([1, 32, 1024, 32768])).sum(-1).tolist()
    slot_of = {c: i for i, c in enumerate(enc)}
    lines = (RUN / "cells" / label / "updates.jsonl").read_text().splitlines()
    print(label, "updates.jsonl lines:", len(lines), "| first/last update:", json.loads(lines[0])["update"], json.loads(lines[-1])["update"])
    for u in map(int, ups.split(",")):
        sd = torch.load(RUN / "cells" / label / "snapshots" / f"u{u:07d}" / "model.pt", weights_only=True)["model"]
        tokens = stream.batch(u + 1).tokens  # [16, 64]
        with torch.no_grad():
            z = forward(sd, arm, tokens[:, :63], seeds.r1_codes, slot_of, {})  # [16, 8, 256]
        target = tokens[:, [s + 1 for s in SITES]]
        l32 = float(F.cross_entropy(z[..., ALPHA].reshape(-1, 32), (target - 0x40).reshape(-1)))
        l256 = float(F.cross_entropy(z.reshape(-1, 256), target.reshape(-1)))
        rec = json.loads(lines[u])
        assert rec["update"] == u + 1
        print(f"  snapshot {u} -> update {u + 1}: auditor 32-way {l32:.7f} vs recorded {rec['task_loss']:.7f} (diff {abs(l32 - rec['task_loss']):.1e}); "
              f"256-way {l256:.6f} vs {rec['answer_loss_256']:.6f}; clip norm {rec['clip_total_norm']:.3f}")
