"""G3c (auditor, Opus 5.5): the train -> evaluate hand-off at registered sizes and U = 8,192, through the
implementer's stage commands and pool, on the SYNTHETIC backbone and TEST seeds (p9i-test-0), calibration
mode, scratch directories and a private ledger. Not a measurement: no accuracy or loss is read or printed.

Why not rehearsal draw 2 on the real backbone: in rehearsal mode ``train.run_job`` writes no train.json
(only rehearsal.json), so ``evaluate_cell(require_train_record=True)`` cannot be reached; on the real
backbone the only non-rehearsal draw is the calibration draw, which may train only R1/R2 (section I.6).

Cells: N-n4096-b101-o301-s1801 and BB-n4096-b101-o301-s1801 (registered labels, registered sizes: 2,048
facts of 32,768; BB covers the next-byte rows and the block-0 snapshot). Steps: generate, gates (the fixed
harness at real proportion), train --only, evaluate --only; then file names, snapshot stems, snapshot
hashes, calibration binding and data-manifest refusals.

Usage: PYTHONPATH=. uv run --locked python <this> <scratch dir>
"""
import json
import shutil
import sys
from pathlib import Path

from arborlm.io import file_sha256, read_json, write_json
from studies.p9i import core, stages

R = Path(sys.argv[1])
RUN = R / "run"
CAL = Path("results/p9i-calibration-2026-11-14/calibration.json").resolve()
LABELS = ("N-n4096-b101-o301-s1801", "BB-n4096-b101-o301-s1801")
BASE = ["--mode", "calibration", "--synthetic-backbone", "--experiments-root", str(R), "--ledger", str(R / "ledger.json"), "--workers", "2", "--stage-cap-seconds", "1800"]
ONLY = [x for label in LABELS for x in ("--only", label)]
FAIL: list[str] = []


def check(name, ok, detail=""):
    print(f"[{'ok' if ok else 'FAIL'}] {name}{(': ' + detail) if detail else ''}")
    if not ok:
        FAIL.append(name)


code = stages.main(["generate", *BASE, "--run-dir", str(RUN)])
dm = read_json(RUN / "data_manifest.json")
check("generate", code == 0 and dm["seed_set"] == "p9i-test-0" and dm["g1_passed"] is True and dm["dry"] is False, f"exit {code}, seed set {dm['seed_set']}")
code = stages.main(["gates", *BASE, "--run-dir", str(RUN)])
g = read_json(RUN / "gates.json")
check("gates (fixed harness, real proportion, synthetic backbone)", code == 0 and g["g4_passed"] and all(v["all_reached"] for v in g["gradient_reach"].values()), f"exit {code}, defects {g['g4_defects']}")
code = stages.main(["train", *BASE, "--run-dir", str(RUN), "--calibration", str(CAL), *ONLY])
check("train exit", code == 0, f"exit {code}")
binding = read_json(RUN / "calibration_binding.json")
check("calibration_binding.json", binding == {"calibration_sha256": file_sha256(CAL), "calibration_selected_updates": 8192, "calibration_failed_sizes": {}}, json.dumps(binding))
check("updates.json", read_json(RUN / "updates.json") == {"updates": 8192, "dry": False})
tm = read_json(RUN / "train" / "manifest.json")
check("train manifest: exactly the two cells, completed", sorted((t["label"], t["status"]) for t in tm["tasks"]) == sorted((lab, "completed") for lab in LABELS), str([(t["label"], t["status"]) for t in tm["tasks"]]))
for label in LABELS:
    d = core.cell_dir(RUN, label)
    t = read_json(d / "train.json")
    snap = d / "snapshots" / core.snapshot_stem(8192)
    check(f"{label}: snapshot dir name", snap.name == "u0008192" and (snap / "model.pt").is_file() and sorted(p.name for p in (d / "snapshots").iterdir()) == ["u0008192"])
    check(f"{label}: train.json U, facts, mode, snapshot hash", t["matched_updates"] == 8192 and t["run_updates"] == 8192 and t["facts"] == 2048 and t["mode"] == "calibration" and t["snapshot_sha256"] == {"8192": file_sha256(snap / "model.pt")}, f"facts {t['facts']}, keys {list(t['snapshot_sha256'])}, unique facts {t['unique_facts']}")
    check(f"{label}: train.json carries the binding", all(t.get(k) == v for k, v in binding.items()))
    check(f"{label}: updates.jsonl lines", sum(1 for _ in (d / "updates.jsonl").open()) >= 8192)
code = stages.main(["evaluate", *BASE, "--run-dir", str(RUN), "--calibration", str(CAL), *ONLY])
check("evaluate exit", code == 0, f"exit {code}")
for label in LABELS:
    p = core.eval_path(RUN, label, 8192, "eval").with_name("eval.json")
    e = read_json(p)
    check(f"{label}: eval path and record", str(p.relative_to(RUN)) == f"cells/{label}/eval/u0008192/eval.json" and e["update"] == 8192 and e["facts"] == 2048 and sorted(e["panels"]) == ["A", "B"] and all(e.get(k) == v for k, v in binding.items()), str(p.relative_to(RUN)))
    check(f"{label}: panel fact counts", all(e["panels"][x]["facts"] == 2048 and e["panels"][x]["chance_interval"] == [36, 96] and e["panels"][x]["unseen_facts"] == 2048 for x in "AB"))
    check(f"{label}: language-modelling record iff BB", ("language_modelling" in e) == label.startswith("BB"))

# refusals on the hand-off
bad = R / "calibration_plus_one_byte.json"
bad.write_bytes(CAL.read_bytes() + b"\n")
code = stages.main(["evaluate", *BASE, "--run-dir", str(RUN), "--calibration", str(bad), *ONLY])
check("evaluate with a different calibration file is REFUSED", code == 2, f"exit {code}")
clone = R / "run_tampered"
shutil.copytree(RUN, clone, ignore=shutil.ignore_patterns("evaluate", "eval"))
m = read_json(clone / "data_manifest.json")
m["sha256s"]["panel_a"] = "0" * 64
(clone / "data_manifest.json").unlink()
write_json(clone / "data_manifest.json", m)
code = stages.main(["evaluate", *BASE, "--run-dir", str(clone), "--calibration", str(CAL), *ONLY])
em = read_json(clone / "evaluate" / "manifest.json") if (clone / "evaluate" / "manifest.json").is_file() else None
check("evaluate against a tampered data manifest: every task fails, no eval written", code == 1 and em is not None and all(t["status"] == "failed" for t in em["tasks"]) and not list((clone / "cells").glob("*/eval/*/eval.json")), f"exit {code}")
snap = core.cell_dir(clone, LABELS[0]) / "snapshots" / "u0008192" / "model.pt"
print(f"\nFAILED CHECKS: {len(FAIL)} {FAIL}")
print("ledger (private):", json.dumps(read_json(R / "ledger.json")["entries"], indent=0))
