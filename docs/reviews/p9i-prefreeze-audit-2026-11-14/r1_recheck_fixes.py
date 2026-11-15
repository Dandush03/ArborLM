"""R1 (auditor, Opus 5.5): re-check of the pre-freeze fixes in dd8b205.

(a) my synthetic M1/M2 cases (built with my own table builder from a5, not the implementer's test helpers)
    against stages.assess; (b) report rendering of the NOT_INTERPRETED outcomes; (c) registered-mode
    refusals called at function level in temporary directories (nothing is generated, trained or
    evaluated; no registered seed is touched); (d) the calibration snapshots' model.pt hashes against the
    hashes their train.json records (the new evaluate check must accept genuine snapshots).

usage: r1_recheck_fixes.py CALIBRATION_RUN_DIR
"""
import argparse
import json
import sys
import tempfile
from pathlib import Path

from arborlm.io import file_sha256, write_json
from studies.p9 import pool
from studies.p9i import classes as C
from studies.p9i import core, report, stages

CAL_RUN = Path(sys.argv[1])
CAL_REC = Path("results/p9i-calibration-2026-11-14/calibration.json")
SIZES = core.SLOTS_BY_SIZE
P1, P2 = core.PRIMARY_PARENT, core.REPLICATE_PARENT
SEEDS, PANELS = core.INIT_SEEDS, core.PANELS
CH = {4096: 96 / 2048, 16384: 318 / 8192, 65536: 1147 / 32768}
ARMS_AT = {16384: ("N", "W7", "E7", "A4", "A4E", "R1", "R2", "D", "D7", "BB", "BB-D", "BB-0"),
           65536: ("N", "W7", "A4", "R1", "D7", "BB", "BB-D", "BB-0"),
           4096: ("N", "W7", "A4", "R1", "BB", "BB-0")}
REPL = ("W7", "A4", "R1", "D7", "BB")
GOOD = {"g1_passed": True, "g2_passed": True, "g4_passed": True, "g4_defects": []}
fails = 0


def check(name, cond, detail=""):
    global fails
    fails += 0 if cond else 1
    print(f"{'ok  ' if cond else 'FAIL'} {name}" + (f"  [{detail}]" if detail else ""))


def all_ok(**over):
    tab = {}
    for s in SIZES:
        for arm in ARMS_AT[s]:
            for par, sd in [(P1, SEEDS[0]), (P1, SEEDS[1])] + ([(P2, SEEDS[0])] if s == 16384 and arm in REPL else []):
                for p in PANELS:
                    acc = over.get(arm, {"R1": 1.0, "R2": 1.0, "BB-0": 0.03, "D": 0.03, "D7": 0.5, "BB-D": 0.5}.get(arm, 0.95))
                    tab[(arm, s, par, sd, p)] = C.Measure(acc, CH[s], True)
    return tab


def run(table, **kw):
    a = {"table": table, "lm": {}, "size_status": {}, "sizes": SIZES, "missing": [], "failed_tasks": [], "gates": dict(GOOD), "leakage": []}
    a.update(kw)
    return stages.assess(**a)


def summary(v):
    sel = v["analysis"]["selection"]
    return f"status={v['status']} interpretable={v['interpretable']} outcome={sel['outcome']} reasons={v['gate_reasons']} classes={'yes' if v['analysis']['classes'] else 'none'}"


print("== (a) assess on synthetic tables ==")
base = all_ok()
v = run(base); print(summary(v))
check("complete, gates pass -> BB selected step 1, interpretable", v["status"] == "COMPLETE" and v["interpretable"] and v["analysis"]["selection"]["outcome"] == "BB" and v["analysis"]["selection"]["step"] == 1)

t = all_ok(); t[("BB-0", 4096, P1, SEEDS[0], "A")] = C.Measure(0.5, CH[4096], True)
check("control: BB-0 above chance present -> MODEL_STORES_FACTS, selection A4", run(t)["analysis"]["classes"]["BB"]["4096"] == C.MODEL_STORES_FACTS and run(t)["analysis"]["selection"]["outcome"] == "A4")
t2 = dict(t); del t2[("BB-0", 4096, P1, SEEDS[0], "A")]
lab = core.make_cell("BB-0", 4096).label if hasattr(core, "make_cell") else "BB-0-n4096"
v = run(t2, missing=[lab]); print(summary(v))
check("missing BB-0 cell -> INCOMPLETE, NOT_INTERPRETED (INCOMPLETE), no class, no BB selection",
      v["status"] == "INCOMPLETE" and not v["interpretable"] and v["analysis"]["selection"]["outcome"] == C.NOT_INTERPRETED_INCOMPLETE and v["analysis"]["classes"] == {} and v["analysis"]["annotations"] == {} and v["analysis"]["selection"]["missing"] == [lab])

t3 = {k: m for k, m in all_ok().items() if not (k[0] == "BB" and k[1] == 65536 and k[3] == SEEDS[1])}
v = run(t3, missing=["BB-n65536-seed2"]); print(summary(v))
check("missing BB seed at 65536 -> NOT_INTERPRETED (INCOMPLETE), not A4", v["analysis"]["selection"]["outcome"] == C.NOT_INTERPRETED_INCOMPLETE and v["analysis"]["classes"] == {})

t4 = all_ok(); t4[("A4", 16384, P2, SEEDS[0], "A")] = C.Measure(0.03, CH[16384], True)
t5 = {k: m for k, m in t4.items() if not (k[0] == "A4" and k[2] == P2)}
v = run(t5, missing=["A4-B102"]); print(summary(v))
check("missing B102 replicate -> NOT_INTERPRETED (INCOMPLETE)", v["analysis"]["selection"]["outcome"] == C.NOT_INTERPRETED_INCOMPLETE)

v = run(base, gates={**GOOD, "g2_passed": False}); print(summary(v))
check("failed G2 -> status COMPLETE (not ENGINEERING_FAIL), NOT_INTERPRETED, reason 'G2 failed', classes kept descriptive",
      v["status"] == "COMPLETE" and not v["interpretable"] and v["analysis"]["selection"]["outcome"] == C.NOT_INTERPRETED and v["gate_reasons"] == ["G2 failed"] and v["analysis"]["classes"] != {})
v = run(base, gates={**GOOD, "g1_passed": False}); print(summary(v))
check("failed G1 -> status COMPLETE (not ENGINEERING_FAIL), NOT_INTERPRETED", v["status"] == "COMPLETE" and v["analysis"]["selection"]["outcome"] == C.NOT_INTERPRETED and v["gate_reasons"] == ["G1 failed"])
v = run(base, gates={**GOOD, "g1_passed": None}); print(summary(v))
check("G1 not recorded -> NOT_INTERPRETED (fail closed)", v["analysis"]["selection"]["outcome"] == C.NOT_INTERPRETED and v["gate_reasons"] == ["G1 not recorded"])
v = run(base, leakage=["W7-n4096-x/A"]); print(summary(v))
check("LEAKAGE flag -> NOT_INTERPRETED with the cell named", v["status"] == "COMPLETE" and v["analysis"]["selection"]["outcome"] == C.NOT_INTERPRETED and v["gate_reasons"] == ["LEAKAGE: W7-n4096-x/A"])
v = run(base, gates={**GOOD, "g4_passed": False, "g4_defects": ["checkpoint restoration is not bit-identical for BB"]}); print(summary(v))
check("G4 defect -> ENGINEERING_FAIL and NOT_INTERPRETED", v["status"] == "ENGINEERING_FAIL" and v["analysis"]["selection"]["outcome"] == C.NOT_INTERPRETED)
v = run(base, gates=None); print(summary(v))
check("no gates record -> INCOMPLETE, NOT_INTERPRETED (INCOMPLETE)", v["status"] == "INCOMPLETE" and v["analysis"]["selection"]["outcome"] == C.NOT_INTERPRETED_INCOMPLETE and v["analysis"]["selection"]["missing"] == ["gates record"])
v = run(base, failed_tasks=["evaluate:X"], gates={**GOOD, "g2_passed": False}, leakage=["Y/B"]); print(summary(v))
check("failed task + G2 + LEAKAGE -> INCOMPLETE outcome, both reasons listed", v["analysis"]["selection"]["outcome"] == C.NOT_INTERPRETED_INCOMPLETE and v["gate_reasons"] == ["G2 failed", "LEAKAGE: Y/B"])
v = run(all_ok(R1=0.4999)); print(summary(v))
check("R1 < 0.5 everywhere, gates pass -> INCONCLUSIVE (step 0 unchanged)", v["analysis"]["selection"]["outcome"] == C.INCONCLUSIVE)

print("\n== (b) report rendering ==")
for name, verdict in (("G2 failed", run(base, gates={**GOOD, "g2_passed": False})), ("missing cell", run(t2, missing=[lab]))):
    analysis = {"status": verdict["status"], "interpretable": verdict["interpretable"], "gate_reasons": verdict["gate_reasons"], "updates": 8192,
                "g1_passed": verdict["g1_passed"], "g2_passed": verdict["g2_passed"], "g4_passed": verdict["g4_passed"], "leakage": [], "missing_cells": [], "failed_tasks": [], "analysis": verdict["analysis"]}
    md = report.render_markdown(analysis, report._rows_classes(analysis), [], None)
    first = [ln for ln in md.splitlines() if ln.strip()][:4]
    print(name, "->", first)
    check(f"report ({name}) shows NOT INTERPRETED before the selection", md.index("NOT INTERPRETED") < md.index("## Selection"))

print("\n== (c) registered-mode refusals (function level, temporary directories) ==")


def ns(**kw):
    d = {"dry": False, "mode": stages.REGISTERED, "calibration": str(CAL_REC), "calibration_sha256": None, "updates": None, "only": None, "group": None}
    d.update(kw)
    return argparse.Namespace(**d)


def refused(fn):
    try:
        fn()
    except pool.StageRefused as e:
        return str(e)
    return None


print("updates_for(registered, audited calibration) =", stages.updates_for(ns()))
check("registered U from the audited record is 8192", stages.updates_for(ns()) == 8192)
r = refused(lambda: stages.updates_for(ns(calibration=None))); check("registered without --calibration refused", r is not None, r)
r = refused(lambda: stages.updates_for(ns(updates=8192))); check("registered with --updates refused", r is not None, r)
r = refused(lambda: stages.updates_for(ns(calibration_sha256="0" * 64))); check("calibration file not hashing to the launch hash refused", r is not None, r)
b = stages.calibration_binding(ns())
print("binding:", json.dumps(b))
check("binding hash = audited 087bf0b5..., U 8192, no failed sizes", b == {"calibration_sha256": "087bf0b5885859a78781e32cb0e0ce8d3b154dfcc471965cf82f06718c509f44", "calibration_selected_updates": 8192, "calibration_failed_sizes": {}})
with tempfile.TemporaryDirectory() as tmp:
    rd = Path(tmp)
    r = refused(lambda: stages.require_gates_passed(rd)); check("train: no gates record -> refused", r is not None, r)
    for bad in ({"g2_passed": False}, {"g1_passed": None}, {"g4_passed": False, "g4_defects": ["x"]}):
        write_json(rd / "gates.json", {**core.envelope("gates"), **GOOD, **bad})
        r = refused(lambda: stages.require_gates_passed(rd)); check(f"train: gates {bad} -> refused", r is not None, r)
    write_json(rd / "gates.json", {**core.envelope("gates"), **GOOD})
    check("train: all gates passed -> accepted", refused(lambda: stages.require_gates_passed(rd)) is None)
    r = refused(lambda: stages.check_binding(ns(), rd)); check("evaluate/analyze before train recorded the binding -> refused", r is not None, r)
    write_json(rd / "calibration_binding.json", {**b, "calibration_selected_updates": 4096})
    r = refused(lambda: stages.check_binding(ns(), rd)); check("binding differs -> refused", r is not None, r)
    write_json(rd / "calibration_binding.json", b)
    check("binding equal -> accepted", refused(lambda: stages.check_binding(ns(), rd)) is None)
    r = refused(lambda: stages.check_binding(ns(calibration=None), rd)); check("registered evaluate without --calibration -> refused", r is not None, r)
    other = rd / "other.json"; other.write_text(CAL_REC.read_text() + " ")
    r = refused(lambda: stages.check_binding(ns(calibration=str(other)), rd)); check("a different calibration file (same content + 1 byte) -> refused", r is not None, r)

print("\n== (d) calibration snapshots: model.pt hash vs train.json (what evaluate_cell now verifies) ==")
n = bad = 0
for tj in sorted(CAL_RUN.glob("cells/*/train.json")):
    rec = json.loads(tj.read_text())
    for u, h in rec["snapshot_sha256"].items():
        n += 1
        bad += file_sha256(tj.parent / "snapshots" / core.snapshot_stem(int(u)) / "model.pt") != h
print(f"snapshots checked {n}, mismatches {bad}")
check("every calibration snapshot hash matches its train.json", n == 90 and bad == 0, f"{n} snapshots")

print(f"\nchecks failed: {fails}")
