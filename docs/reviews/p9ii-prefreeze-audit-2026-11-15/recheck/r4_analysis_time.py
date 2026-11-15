"""R4 (auditor, Opus 5.5, re-check; helpers copied from c3): wall time of work analyze + work report on synthetic records of the LARGEST registry (128 Stage 1 cells, the 40-cell Stage 2 A5-C+A2 configuration with both readouts, 8 Stage 3 cells) whose update and diagnostics logs have the REAL size (8,192 / 32,768 update lines, 128 / 512 diagnostics lines, copied from a calibration cell and renumbered). The caps of analysis and report are 2 x a measured time with a 60 s floor; this measures it at real log size. -- was: C3 (auditor, Opus 5.5): the implementer's analysis and report workers (``stages work analyze`` / ``work report``, i.e. load_stage ->
analyze_study -> write_report) on SYNTHETIC on-disk records of the full registry (128 Stage 1 cells with the registered labels and U =
8,192; Stage 2 configurations with both readouts; Stage 3), in scenarios. The expected outcome of each scenario is stated from the ADR text
before the run; the script prints expected and observed. No model is trained and no real record is read.

usage: c3_synthetic_registry.py SCRATCH_DIR
"""
import contextlib
import io
import json
import math
import shutil
import sys
from pathlib import Path

from studies.p9ii import core, stages

SCRATCH = Path(sys.argv[1]) / "r4"
TEMPLATE = Path(sys.argv[2])
U = core.UPDATES
GOOD = {"acc": 0.98, "distinct": 250, "share": 0.008, "h": 0.97, "lm": 0.13, "dep": True}
BAD = {"acc": 0.05, "distinct": 3, "share": 0.9, "h": 0.05, "lm": 0.05, "dep": True}


def eval_record(cell, update, o, a6=False, a7=False, extra=None):
    probe = {} if a7 else {"distinct_top1": o["distinct"], "largest_top1_share": o["share"], "probe_facts": 256, "probe_accuracy": o["acc"], "mean_cosine_different": 0.02 if o["distinct"] > 100 else 0.99, "target_top8_recall": 0.95}
    rec = {**core.envelope("eval"), "label": cell.label, "arm": cell.arm, "stage": cell.stage, "slots": cell.slots, "draw": cell.draw, "seed_index": cell.seed_index, "update": update,
           "panels": {p: {"accuracy": o["acc"], "memory_dependence_chance": o["dep"], "leakage": o.get("leak", False)} for p in "AB"},
           "secondary": {"H1": {"accuracy": o["h"]}, "H2": {"accuracy": o["h"]}}, "probe": probe,
           "panel_statistics": {"address_stability": 0.9, "target_top8_recall_A": 0.95, "target_top8_recall_B": 0.95}, "language_modelling": {"relative_rise": o["lm"]}}
    rec.update(extra or {})
    return core.jsonable(rec)


def write_cell(run, cell, outcomes, stage, u_pre=None):
    folder = core.cell_dir(run, cell.label)
    folder.mkdir(parents=True, exist_ok=True)
    readouts = core.stage_readouts(stage)
    total = core.stage_updates(stage)
    core.write_record(folder / "train.json", {**core.envelope("train"), "label": cell.label, "status": "completed", "schedule": {"u_pre": u_pre, "total": total}, "matched_updates": total, "arm": cell.arm, "stage": cell.stage, "slots": cell.slots, "draw": cell.draw, "seed_index": cell.seed_index, "facts": cell.facts,
                                                     "exposure_per_fact_analytical": 0, "exposure_per_fact_mean": 0, "trainable_parameters": 0, "trainable_backbone_parameters": 0, "stored_parameters": 0, "optimizer_state_bytes": 0, "wall_seconds": 1.0, "peak_rss_bytes": 1, "snapshot_sha256": {}, "target_seed": 0})
    final = outcomes[readouts[-1]]
    good = final["distinct"] > 100
    lines = []
    for u in range(64, total + 1, 64 if total <= U else 512):
        sep = good and u >= 1024
        acc = final["acc"] if (good and u >= 2048) else 0.03
        lines.append(json.dumps({"update": u, "distinct_top1": 250 if sep else 3, "largest_top1_share": 0.008 if sep else 0.9, "probe_facts": 256, "mean_cosine_different": 0.02 if sep else 0.99, "probe_accuracy": acc, "target_top8_recall": 1.0 if (u_pre and u <= u_pre) else 0.5}))
    (folder / "diagnostics.jsonl").write_text("\n".join(lines) + "\n")
    ups = [json.dumps({"update": u, "grad_norm": {"wq": 1e-5, "wo": 1e-2}, "param_change_norm": {"wq": 0.01, "keys": 0.01}}) for u in range(1, 1100, 7)]
    (folder / "updates.jsonl").write_text("\n".join(ups) + "\n")
    for u in readouts:
        p = core.eval_path(run, cell.label, u)
        p.parent.mkdir(parents=True, exist_ok=True)
        core.write_record(p, eval_record(cell, u, outcomes[u], a7=cell.arm == "A7"))


def manifest(run, name, labels, failed=()):
    p = run / name / "manifest.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"stage": name, "tasks": [{"label": l, "status": "failed" if l in failed else "completed", "task_id": l} for l in labels]}))


def gates(run, **over):
    rec = {**core.envelope("gates"), "g1_passed": True, "g2_passed": True, "g4_passed": True, "g5_passed": True, "g6_passed": True, "g4_defects": []}
    rec.update(over)
    core.write_record(run / "gates.json", rec)


def build(name, s1, a6_by_draw=None, stage2=None, stage3=None, gate_over=None, missing=(), extra_manifests=(), s2_gate=None, s3_gate=None, s2_missing=()):
    """s1(arm, draw, j) -> outcome dict; stage2 = (advancing, f(arm, draw, j, update)); stage3 = (selected, f)."""
    run = SCRATCH / name
    shutil.rmtree(run, ignore_errors=True)
    run.mkdir(parents=True)
    gates(run, **(gate_over or {}))
    labels1 = []
    for c in core.stage1_cells():
        labels1.append(c.label)
        if c.label in missing:
            continue
        if c.arm == "A6":
            o = {**GOOD, "acc": (a6_by_draw or {}).get(c.draw, 1.0), "lm": 0.14}
        elif c.arm == "A7":
            o = {**GOOD, "acc": 0.99}
        else:
            o = s1(c.arm, c.draw, c.seed_index)
        write_cell(run, c, {U: o}, 1, u_pre=2048 if c.arm == "A2" else None)
    manifest(run, "train1", labels1)
    manifest(run, "evaluate1", labels1)
    for m, fl in extra_manifests:
        manifest(run, m, [m], failed=fl)
    if stage2 is not None:
        adv, f2 = stage2
        core.write_record(run / "stage_gate_1.json", {**core.envelope("stage_gate"), "run": True, "advancing": adv, "status": None})
        cells2 = core.stage2_cells(adv)
        for c in cells2:
            if c.label in s2_missing:
                continue
            if c.arm == "A6":
                outs = {u: {**GOOD, "acc": 1.0, "lm": 0.14} for u in core.stage_readouts(2)}
            elif c.arm == "A7":
                outs = {u: {**GOOD, "acc": 0.8} for u in core.stage_readouts(2)}
            else:
                outs = {u: f2(c.arm, c.draw, c.seed_index, u) for u in core.stage_readouts(2)}
            write_cell(run, c, outs, 2, u_pre=8192 if c.arm == "A2" else None)
        manifest(run, "train2", [c.label for c in cells2])
        manifest(run, "evaluate2", [c.label for c in cells2])
    elif s2_gate is not None:
        core.write_record(run / "stage_gate_1.json", {**core.envelope("stage_gate"), **s2_gate})
    if stage3 is not None:
        sel, f3 = stage3
        core.write_record(run / "stage_gate_3.json", {**core.envelope("stage_gate"), "run": True, "selected": sel, "status": None})
        cells3 = core.stage3_cells(sel)
        for c in cells3:
            o = {**GOOD, "acc": 1.0, "lm": 0.14} if c.arm == "A6" else ({**GOOD, "acc": 0.9} if c.arm == "A7" else f3(c.arm, c.draw, c.seed_index))
            write_cell(run, c, {U: o}, 3)
        manifest(run, "train3", [c.label for c in cells3])
        manifest(run, "evaluate3", [c.label for c in cells3])
    elif s3_gate is not None:
        core.write_record(run / "stage_gate_3.json", {**core.envelope("stage_gate"), **s3_gate})
    return run


def analyze(run):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = stages.main(["work", "analyze", "--run-dir", str(run), "--mode", "calibration"])
        code2 = stages.main(["work", "report", "--run-dir", str(run), "--mode", "calibration"])
    a = core.read_record(run / "analysis.json", "analysis")["result"]
    md = (run / "results" / "RESULTS.md").read_text()
    return code, code2, a, md


def show(name, expected, run):
    code, code2, a, md = analyze(run)
    o = a["outcome"]
    s1 = a.get("stage1") or {}
    classes = {k: v["class"] for k, v in (s1.get("arms") or {}).items()}
    s2 = a.get("stage2") or {}
    print(f"\n### {name}\n expected: {expected}\n observed: outcome={o['outcome']!r} row={o['row']} arm={o.get('arm')} status={a['assessment']['status']} interpretable={a['assessment']['interpretable']}")
    print(" stage2 status:", s2.get("status"), "| stage3:", {k: v for k, v in (a.get("stage3") or {}).items() if k in ("status", "label", "selected", "successes")})
    print(" stage1 classes:", classes)
    if s2.get("arms"):
        print(" stage2 classes:", {k: v["class"] for k, v in s2["arms"].items()}, "| U readout:", {k: v.get("readout_u") for k, v in s2["arms"].items()})
    print(" NC failed s1:", s1.get("negative_control_failed"), "| hypotheses:", {k: v["reading"] for k, v in (a.get("hypotheses") or {}).items()})
    print(" carried:", a.get("carried_forward"), "| exit codes", code, code2, "| RESULTS.md lines", len(md.splitlines()))
    return a


def ok(arm, d, j):
    return dict(GOOD)


def bad(arm, d, j):
    return dict(BAD)


import time  # noqa: E402

up_lines = (TEMPLATE / "updates.jsonl").read_text().splitlines()
dg_lines = (TEMPLATE / "diagnostics.jsonl").read_text().splitlines()


def renumber(lines, total):
    out, n = [], len(lines)
    for rep in range(total // n):
        for line in lines:
            r = json.loads(line)
            r["update"] = r["update"] + rep * json.loads(lines[-1])["update"]
            out.append(json.dumps(r))
    return "\n".join(out) + "\n"


s1 = lambda a, d, j: dict(GOOD) if a in ("A5-C", "A2") else (dict(GOOD) if a == "A0" and d <= 2 else dict(BAD))
run = build("big", s1, stage2=(["A5-C", "A2"], lambda a, d, j, u: dict(GOOD) if a in ("A5-C", "A2") else dict(BAD)), stage3=("A5-C", lambda a, d, j: dict(GOOD)))
big = {1: (renumber(up_lines, 8192), renumber(dg_lines, 8192 // 64)), 2: (renumber(up_lines, 32768), renumber(dg_lines, 32768 // 64)), 3: (renumber(up_lines, 8192), renumber(dg_lines, 8192 // 64))}
n = 0
for folder in (run / "cells").iterdir():
    if folder.name.startswith(("S1-", "S2-", "S3-")) and "-A6-" not in folder.name and "-A7-" not in folder.name:
        st = int(folder.name[1])
        (folder / "updates.jsonl").write_text(big[st][0])
        (folder / "diagnostics.jsonl").write_text(big[st][1])
        n += 1
print("cells with real-size logs:", n, "| Stage 2 update lines per cell:", big[2][0].count("\n"), "| diagnostics:", big[2][1].count("\n"))
t0 = time.monotonic()
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    stages.main(["work", "analyze", "--run-dir", str(run), "--mode", "calibration"])
t1 = time.monotonic()
with contextlib.redirect_stdout(buf):
    stages.main(["work", "report", "--run-dir", str(run), "--mode", "calibration"])
t2 = time.monotonic()
a = core.read_record(run / "analysis.json", "analysis")["result"]
print(f"work analyze {t1 - t0:.1f} s, work report {t2 - t1:.1f} s; outcome {a['outcome']['outcome']} row {a['outcome']['row']}")
