"""R2 (auditor, Opus 5.5, re-check; helpers copied from c3) -- was: C3 (auditor, Opus 5.5): the implementer's analysis and report workers (``stages work analyze`` / ``work report``, i.e. load_stage ->
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

SCRATCH = Path(sys.argv[1]) / "r2"
PROJECTION = Path(sys.argv[2])
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


def build(name, s1, a6_by_draw=None, stage2=None, stage3=None, gate_over=None, missing=(), extra_manifests=(), s2_gate=None, s3_gate=None, s2_missing=(), draw_plan=None):
    """s1(arm, draw, j) -> outcome dict; stage2 = (advancing, f(arm, draw, j, update)); stage3 = (selected, f)."""
    run = SCRATCH / name
    shutil.rmtree(run, ignore_errors=True)
    run.mkdir(parents=True)
    gates(run, **(gate_over or {}))
    if draw_plan is not None:
        core.write_record(run / "draw_plan.json", {**core.envelope("draw_plan"), **draw_plan})
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


def stagegate(run):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = stages.main(["stagegate", "--run-dir", str(run), "--after", "1", "--projection", str(PROJECTION), "--ledger-root", str(run), "--mode", "calibration"])
    return code, core.read_record(run / "stage_gate_1.json", "stage_gate")


def a4_reliable(arm, d, j):  # A4 and A5-D RELIABLE, A0 UNRELIABLE (succeeds on draws 1-3), A5-C fails: the gate advances A5-D and A4
    if arm in ("A4", "A5-D"):
        return dict(GOOD)
    return dict(GOOD) if (arm == "A0" and d <= 3) else dict(BAD)


def a0_and_a4(arm, d, j):  # A0 RELIABLE (row 3), A4 RELIABLE: the gate advances A4 alone
    return dict(GOOD) if arm in ("A0", "A4") else dict(BAD)


plan_ok = {"ok": True, "seed_set_of": {str(k): (f"p9ii-reserve-1" if k == 3 else f"p9ii-draw-{k}") for k in range(1, 15)}, "replacements": {"3": "p9ii-reserve-1"}, "labels": {"3": "REPLACED BY RESERVE 1"}, "reason": None, "g1": {}}
plan_bad = {"ok": False, "seed_set_of": {str(k): f"p9ii-draw-{k}" for k in range(1, 15)}, "replacements": {}, "labels": {}, "reason": "3 draws failed G1", "g1": {}}
s1_a = lambda a, d, j: dict(GOOD) if a == "A5-C" else (dict(GOOD) if a == "A0" and d <= 2 else dict(BAD))
S2C = (["A5-C"], lambda a, d, j, u: dict(GOOD) if a == "A5-C" else dict(BAD))
S3C = ("A5-C", lambda a, d, j: dict(GOOD))
SCN = {}
SCN["R-a reserve substitution (failed generate task + draw plan with a replacement)"] = ("complete, row 4; draw 3 printed REPLACED BY RESERVE 1", build("Ra", s1_a, stage2=S2C, stage3=S3C, extra_manifests=(("generate-p9ii-draw-3", ("generate-p9ii-draw-3",)),), draw_plan=plan_ok))
SCN["R-b reserve list exhausted (draw plan not ok)"] = ("NOT_INTERPRETED (INCOMPLETE)", build("Rb", s1_a, draw_plan=plan_bad))
SCN["R-c failed G2 on draw 7 only"] = ("NOT_INTERPRETED (G2 failed on draw 7)", build("Rc", s1_a, gate_over={"g2_by_draw": {str(k): k != 7 for k in range(1, 15)}}, s2_gate={"run": False, "status": "NOT RUN — NO ARM PASSED", "advancing": []}))
SCN["R-d INCOMPLETE Stage 2"] = ("row 6 with INCOMPLETE; nothing carried; Stage 3 INCOMPLETE", build("Rd", s1_a, stage2=(["A5-C"], S2C[1]), s2_missing=("S2-A5-C-n16384-d12-j1",), s3_gate={"run": False, "status": "INCOMPLETE"}))
run_e = build("Re", a4_reliable)
SCN["R-e A4 and A5-D RELIABLE: gate on the real projection"] = ("gate: advancing A5-D+A4, NOT RUN — BUDGET; row 6 'AT 4,096; 16,384 NOT RUN — BUDGET'; A4, A5-D print RELIABLE; Stage 3 NOT RUN — BUDGET; H19-D/G read at 4,096", run_e)
run_f = build("Rf", a0_and_a4)
SCN["R-f A0 RELIABLE and A4 advances: gate on the real projection"] = ("gate: advancing A4, NOT RUN — BUDGET; row 3; B-G NOT TESTED AT 16,384; Stage 3 NOT RUN — BUDGET", run_f)
SCN["R-g A2 advances (A1-S with it); stage 2 runs"] = ("Stage 2 COMPLETE, A2 MID-SCHEDULE at U", build("Rg", lambda a, d, j: dict(GOOD) if a == "A2" else (dict(GOOD) if a == "A0" and d <= 2 else dict(BAD)), stage2=(["A2"], lambda a, d, j, u: dict(GOOD) if a == "A2" else dict(BAD)), s3_gate={"run": False, "status": "NOT RUN — SCHEDULED ARM", "selected": "A2"}))
for name, (exp, run) in SCN.items():
    try:
        if name.startswith(("R-e", "R-f")):
            code, rec = stagegate(run)
            print(f"\n### {name}\n stage gate (driver, real projection 6895b920): run={rec['run']} status={rec['status']} advancing={rec.get('advancing')} budget={ {k: round(v, 1) if isinstance(v, float) else v for k, v in (rec.get('budget') or {}).items()} }")
        a = show(name, exp, run)
        md = (run / "results" / "RESULTS.md").read_text()
        for key in ("REPLACED BY RESERVE", "NOT TESTED AT 16,384", "NOT RUN — BUDGET", "NEGATIVE CONTROL FAILED", "SUPERVISION-DEPENDENT", "ADDRESS STABLE", "MID-SCHEDULE"):
            if key in md:
                print(f"   RESULTS.md mentions: {key}")
        print("   hypotheses detail:", {k: v.get("reading") for k, v in a.get("hypotheses", {}).items() if k in ("H19-B", "H19-D", "H19-G")}, "| outcome label:", a["outcome"]["label"][:160])
    except Exception as exc:
        import traceback
        print(f"\n### {name}\n expected: {exp}\n CRASH: {type(exc).__name__}: {exc}")
        traceback.print_exc()

# every Stage 2 / Stage 3 configuration finds its cap in the table built from the real projection
from studies.p9ii import budget  # noqa: E402

proj = core.read_record(PROJECTION, "projection")
rates = {stages._parse_item(k): budget.Rate(**{f: v[f] for f in budget.Rate.__dataclass_fields__ if f in v}) for k, v in proj["rates"].items()}
table = budget.caps_table(rates, core.Hyper.from_json(proj["hyper"]), gates_wall_seconds=8.3, analysis_wall_seconds=5.0, report_wall_seconds=1.0)
missing, rows = [], []
for adv in budget.stage2_configurations():
    run = SCRATCH / "caps_probe"
    run.mkdir(parents=True, exist_ok=True)
    core.write_record(run / "stage_gate_1.json", {**core.envelope("stage_gate"), "run": True, "advancing": list(adv), "status": None})
    try:
        c = stages.stage_caps_for("stage2", table, run)
        rows.append((budget.config_key(adv), round(c["train"]), round(c["evaluate"]), round(2 * proj["stage2_table"][budget.config_key(adv)]["total_seconds"])))
    except Exception as exc:
        missing.append((adv, str(exc)))
    (run / "stage_gate_1.json").unlink()
for sel in ("A0", "A1", "A5-C", "A5-D", "A2", "A4"):
    core.write_record(run / "stage_gate_3.json", {**core.envelope("stage_gate"), "run": True, "selected": sel, "status": None})
    try:
        c = stages.stage_caps_for("stage3", table, run)
        rows.append(("stage3 " + sel, round(c["train"]), round(c["evaluate"]), None))
    except Exception as exc:
        missing.append(("stage3 " + sel, str(exc)[:80]))
    (run / "stage_gate_3.json").unlink()
print("\ncaps (train, evaluate, 2 x projected total):")
for r in rows:
    print("  ", r)
print("refused (no entry):", missing)
print("stage1 cap:", {k: round(v, 1) for k, v in table["stage1"].items()}, "gates:", table["gates"], "analysis:", table["analysis"], "report:", table["report"])
