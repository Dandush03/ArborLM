"""R5 (auditor, Opus 5.5, re-check): the 22 calibration snapshots scored with HEAD's evaluation code (evaluate.calibration_accuracy, plain and
inside evaluate.eval_chunking, and HEAD's probe: diagnostics.build_probe / probe_reads / probe_measures), compared with the calibration records and
with my independent re-scoring of the audit (b2, identical to the records). Then the section 6 selection with HEAD's corrected tie rule
(core.first_success_key + core.select_value) and with my own reading of the corrected rule, from the raw diagnostics.

usage: r5_calibration_head.py RUN_DIR EXPERIMENTS_ROOT AUDIT_B2_JSON
"""
import json
import math
import sys
from pathlib import Path

import torch

from studies.p9 import controls, data as p9data
from studies.p9 import core as p9core
from studies.p9ii import core, evaluate, model, train
from studies.p9ii.diagnostics import build_probe, probe_measures, probe_reads

torch.set_num_threads(2)
RUN, ROOT, B2 = Path(sys.argv[1]), Path(sys.argv[2]), json.loads(Path(sys.argv[3]).read_text())["cells"]
corpus = p9core.load_trained_corpus(ROOT)
backbone = controls.load_backbone(p9core.PRIMARY_PARENT, ROOT)[0]
studies = {d: p9data.build_study_data(core.calibration_seeds(d), corpus) for d in (3, 4)}
worst = 0.0
acc, curves = {}, {}
for folder in sorted((RUN / "cells").iterdir()):
    cell = core.parse_label(folder.name)
    tr = json.loads((folder / "train.json").read_text())
    net = model.build_model(cell.arm, cell.slots, tr["init_seed"], backbone, r1_seed=studies[cell.draw].seeds.r1_codes, seed_rng=False)
    train.load_model_state(folder / "snapshots" / "u0008192", net)
    net.eval()
    a_plain = evaluate.calibration_accuracy(net, studies[cell.draw], 2048)
    with evaluate.eval_chunking(net):
        a_chunk = evaluate.calibration_accuracy(net, studies[cell.draw], 2048)
    probe = build_probe(studies[cell.draw], 2048)
    p = probe_measures(probe_reads(net, probe), probe)["probe_accuracy"]
    rec = json.loads((folder / "calibration_cell.json").read_text())["accuracy"]
    b2 = B2[folder.name]
    worst = max(worst, abs(a_plain - rec), abs(a_chunk - rec), abs(a_plain - b2["accuracy_auditor"]), abs(p - b2["probe_accuracy_auditor"]))
    acc[folder.name] = a_chunk
    curves[folder.name] = [(json.loads(x)["update"], json.loads(x)["probe_accuracy"]) for x in (folder / "diagnostics.jsonl").read_text().splitlines() if x.strip()] if (folder / "diagnostics.jsonl").is_file() else []
    print(folder.name, "HEAD plain", a_plain, "HEAD chunked", a_chunk, "record", rec, "| probe HEAD", p, "audit b2", b2["probe_accuracy_auditor"])
print("max |difference| over 22 cells (accuracy plain/chunked vs record, vs audit b2; probe vs audit b2):", worst)
a6 = {d: acc[f"CAL-A6-n4096-d{d}-j0"] for d in (3, 4)}


def first(curve, line):
    return next((u for u, a in curve if a >= line), math.inf)


def my_key(times):  # corrected rule as the audit asked: fewer never-successes first, then the earlier median of the finite times
    finite = sorted(t for t in times if math.isfinite(t))
    med = (finite[0] if len(finite) == 1 else (finite[0] + finite[1]) / 2) if finite else 0.0
    return (len(times) - len(finite), med)


for arm, (name, values) in core.GRID.items():
    mins, keys_head, keys_mine = {}, {}, {}
    for v in values:
        labels = [l for l in acc if core.parse_label(l).arm == arm and core.parse_label(l).value == v]
        mins[v] = min(acc[l] for l in labels)
        times = [first(curves[l], 0.9 * a6[core.parse_label(l).draw]) for l in labels]
        keys_head[v], keys_mine[v] = core.first_success_key(times), my_key(times)
    sel_head = core.select_value(values, mins, keys_head)
    best = max(mins.values())
    cont = [v for v in values if best - mins[v] < 0.02]
    sel_mine = cont[0] if len(cont) == 1 else min(cont, key=lambda v: (keys_mine[v], values.index(v)))
    print(arm, name, "min", mins, "keys", keys_head, "-> HEAD selects", sel_head, "| mine", sel_mine)
