"""C3 (auditor, Opus 5.5): the implementer's analysis and report workers (``stages work analyze`` / ``work report``, i.e. load_stage ->
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

SCRATCH = Path(sys.argv[1]) / "c3"
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


SCN = {}
# S1: A5-C RELIABLE, improves on A0 (A0 succeeds on draws 1-2 only), A5-D UNRELIABLE; Stage 2 with A5-C, reliable there; Stage 3 A5-C
def s1_a(arm, d, j):
    if arm == "A5-C":
        return dict(GOOD)
    if arm == "A0":
        return dict(GOOD) if d <= 2 else dict(BAD)
    if arm == "A5-D":
        return dict(GOOD) if d <= 5 else dict(BAD)
    return dict(BAD)


SCN["S1 arm RELIABLE and improving on A0"] = ("row 4 ADDRESSING-RELIABLE A5-C (LABEL-FREE) IMPROVES; Stage 2 COMPLETE; Stage 3 SCALE PROBE POSITIVE; H19-F supported", build("S1", s1_a, stage2=(["A5-C"], lambda a, d, j, u: dict(GOOD) if a == "A5-C" else dict(BAD)), stage3=("A5-C", lambda a, d, j: dict(GOOD))))
SCN["S2 answer-only reliable"] = ("row 3 ANSWER-ONLY RELIABLE; Stage 2 A0-only; readings at 16,384", build("S2", lambda a, d, j: dict(GOOD) if a in ("A0", "A1", "A5-D") else dict(BAD), stage2=(["A5-D", "A1"], lambda a, d, j, u: dict(GOOD) if a == "A0" else dict(BAD))))
SCN["S3 negative control failed"] = ("row 2 INCONCLUSIVE (A1-S RELIABLE, no label-free arm RELIABLE)", build("S3", lambda a, d, j: dict(GOOD) if a in ("A1", "A1-S") else dict(BAD), s2_gate={"run": False, "status": "NOT RUN — NO ARM PASSED", "advancing": []}))
SCN["S4 nothing reliable"] = ("row 7 ADDRESSING-UNRELIABLE (A4 has 8 successes); Stage 2 NOT RUN — NO ARM PASSED", build("S4", lambda a, d, j: dict(GOOD) if (a == "A4" and d <= 4) else dict(BAD), s2_gate={"run": False, "status": "NOT RUN — NO ARM PASSED", "advancing": []}))
SCN["S4b everything fails"] = ("row 8 ADDRESSING-FAILS", build("S4b", bad, s2_gate={"run": False, "status": "NOT RUN — NO ARM PASSED", "advancing": []}))
SCN["S5 one NOT_EVALUATED draw"] = ("A6 0.85 on draw 3: 14 evaluated cells, A5-C RELIABLE remains possible; row 6 with Stage 2 NOT RUN — BUDGET", build("S5", lambda a, d, j: dict(GOOD) if a == "A5-C" else dict(BAD), a6_by_draw={3: 0.85}, s2_gate={"run": False, "status": "NOT RUN — BUDGET", "advancing": ["A5-C"]}))
SCN["S5b two NOT_EVALUATED draws"] = ("row 2 INCONCLUSIVE (Stage 1 NOT_EVALUATED)", build("S5b", ok, a6_by_draw={3: 0.85, 4: 0.5}, s2_gate={"run": False, "status": "NOT RUN — NO ARM PASSED", "advancing": []}))
SCN["S6 missing cell"] = ("row 1 NOT_INTERPRETED (INCOMPLETE), no class", build("S6", ok, missing=("S1-A4-n4096-d05-j1",)))
SCN["S7 failed G2"] = ("NOT_INTERPRETED (G2 failed) with a descriptive outcome", build("S7", ok, gate_over={"g2_passed": False}, s2_gate={"run": False, "status": "NOT RUN — BUDGET", "advancing": []}))
SCN["S7b G4 defect"] = ("ENGINEERING_FAIL", build("S7b", ok, gate_over={"g4_passed": False, "g4_defects": ["x"]}))
SCN["S8 non-finite values"] = ("A0 cells with NaN accuracy and +inf LM rise fail / are flagged; analysis completes", build("S8", lambda a, d, j: ({**GOOD, "acc": math.nan, "lm": math.inf} if a == "A0" else dict(GOOD) if a == "A5-D" else dict(BAD)), s2_gate={"run": False, "status": "NOT RUN — BUDGET", "advancing": ["A5-D"]}))
SCN["S9 Stage 2 NOT RUN — BUDGET"] = ("ADR 10: Stage 2 AND Stage 3 status NOT RUN — BUDGET; row 6", build("S9", lambda a, d, j: dict(GOOD) if a == "A4" else dict(BAD), s2_gate={"run": False, "status": "NOT RUN — BUDGET", "advancing": ["A4"]}))
SCN["S10 row 3 with Stage 2 NOT RUN — BUDGET"] = ("ADR 8.6: row 3; B-G read at 16,384, which does not exist -> none supported", build("S10", lambda a, d, j: (dict(GOOD) if a in ("A0", "A5-C") or (a == "A5-C") else (dict(GOOD) if (a == "A5-C") else dict(BAD))) if a != "A5-C" else dict(GOOD), s2_gate={"run": False, "status": "NOT RUN — BUDGET", "advancing": ["A5-C"]}))
SCN["S11 a draw replaced after G1 (generate manifest with a failed task)"] = ("ADR 9: replacement allowed -> analysis COMPLETE as in S1", build("S11", s1_a, stage2=(["A5-C"], lambda a, d, j, u: dict(GOOD) if a == "A5-C" else dict(BAD)), stage3=("A5-C", lambda a, d, j: dict(GOOD)), extra_manifests=(("generate-p9ii-draw-3", ("generate-p9ii-draw-3",)), ("generate-p9ii-reserve-1", ()))))
SCN["S12 Stage 2 INCOMPLETE (one cell missing)"] = ("Stage 2 INCOMPLETE -> row 6; nothing carried forward from an incomplete stage", build("S12", s1_a, stage2=(["A5-C"], lambda a, d, j, u: dict(GOOD) if a == "A5-C" else dict(BAD)), s2_missing=("S2-A5-C-n16384-d12-j1",), s3_gate={"run": False, "status": "NOT RUN — STAGE NOT INTERPRETABLE"}))
SCN["S13 A2 RELIABLE at 16,384 (scheduled arm selected)"] = ("Stage 3 NOT RUN — SCHEDULED ARM; MID-SCHEDULE at U for A2", build("S13", lambda a, d, j: dict(GOOD) if a in ("A2",) else (dict(GOOD) if a == "A0" and d <= 2 else dict(BAD)), stage2=(["A2"], lambda a, d, j, u: dict(GOOD) if a == "A2" else dict(BAD)), s3_gate={"run": False, "status": "NOT RUN — SCHEDULED ARM", "selected": "A2"}))
for name, (exp, run) in SCN.items():
    try:
        show(name, exp, run)
    except Exception as exc:  # keep going: a crash is a finding
        print(f"\n### {name}\n expected: {exp}\n CRASH: {type(exc).__name__}: {exc}")
