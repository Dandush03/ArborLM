"""Checks on the auditor's e2e variant clone (test profile, test seeds, tiny, synthetic backbone), after its registered sequence ran:
 (1) scan every product of the registered run directory for A5-D mentions without the three strings;
 (2) does any product say that it is a TEST-PROFILE run?
 (3) a TYPED registered worker after the freeze (`work train --mode registered` for a cell outside the plan: WX-A1, the candidate being A5-D): refused or not, ledger charged or not;
 (4) the real per-worker guard (registered_state) against measure_guard_seconds on the same tree.
Run with cwd = the clone and PYTHONPATH = the clone. Usage: python r7_post_e2e_checks.py <clone> <run_dir> <freeze_commit>
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval."""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

clone, run_dir, freeze = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
sys.path.insert(0, str(clone))
from studies.p10s0 import core, stages  # noqa: E402

out: dict = {}
# (1) provenance scan
bad, named = [], 0
for p in sorted(run_dir.rglob("*")):
    if not p.is_file() or p.suffix not in (".json", ".csv", ".md", ".jsonl", ".txt", ".log"):
        continue
    t = p.read_text(encoding="utf-8", errors="replace")
    if p.suffix == ".json":
        try:
            t = json.dumps(json.loads(t), ensure_ascii=False)
        except ValueError:
            pass
    if core.mentions_a5d(t):
        named += 1
        if not core.has_provenance(t):
            bad.append(str(p.relative_to(run_dir)))
out["files_naming_A5-D"] = named
out["files_naming_A5-D_without_the_three_strings"] = bad[:40]
out["n_without"] = len(bad)
# (2) test-profile labelling of the products
res = run_dir / "results"
out["products_mention_test_profile"] = {p.name: ("TEST" in p.read_text(errors="replace").upper() and "PROFILE" in p.read_text(errors="replace").upper()) for p in sorted(res.glob("*"))}
an = json.loads((run_dir / "analysis.json").read_text())
out["analysis_record_dry_flag"] = an.get("dry")
out["analysis_unit_updates"] = an.get("unit_updates")
# (3) a typed registered worker after the freeze
ledger = core.ledger_for(core.default_experiments_root(clone))
before = len(ledger.entries())
label = next(c.label for c in core.wx_cells("A1"))
env = {**os.environ, "PYTHONPATH": str(clone)}
t0 = time.monotonic()
r = subprocess.run([sys.executable, "-m", "studies.p10s0.stages", "work", "train", "--mode", "registered", "--run-dir", str(run_dir), "--freeze-commit", freeze, "--labels", label], cwd=clone, env=env, capture_output=True, text=True)
out["typed_worker"] = {"label": label, "exit": r.returncode, "stdout": r.stdout.strip()[-300:], "stderr": r.stderr.strip()[-300:], "seconds": time.monotonic() - t0,
                       "train_record_written": (core.cell_dir(run_dir, label) / "train.json").is_file(), "ledger_entries_before": before, "ledger_entries_after": len(core.ledger_for(core.default_experiments_root(clone)).entries())}
r2 = subprocess.run(["git", "-C", str(clone), "status", "--porcelain", "--untracked-files=all"], capture_output=True, text=True)
out["clone_clean_after"] = r2.stdout.strip()[:300]
# (4) guard timings
ns = argparse.Namespace(mode="registered", run_dir=str(run_dir), freeze_commit=freeze, repo=str(clone))
reals = []
for _ in range(5):
    t0 = time.monotonic()
    stages.registered_state(ns)
    reals.append(time.monotonic() - t0)
meas = [stages.measure_guard_seconds(clone) for _ in range(5)]
out["guard_registered_state_seconds"] = [round(x, 3) for x in reals]
out["guard_measure_guard_seconds"] = [round(x, 3) for x in meas]
proj = json.loads((clone / "experiments/E2E-projection.json").read_text())
out["projection_guard_seconds_per_task"] = proj.get("guard_seconds_per_task")
print(json.dumps(out, indent=1, default=str))
