"""Re-check B, R7: what the freeze accepts from the pre-freeze records (defect class b: typed values, stand-in or mismatched records, wrong units).

A NEW throwaway repository is made from the kept end-to-end clone at its pre-freeze commit (the exercise's configuration, test seeds, stand-ins), with the pre-freeze ledger entries only (no registered
entry, no plan in history). The freeze command of that repository is then run on edited copies of the exercise's pre-freeze records:
  control  : the records as written by the exercise                                   (expected: accepted)
  pilot    : calibration pilot ok = false                                               (expected: refused; sanity)
  bundle   : --data-dir names a DIFFERENT stand-in bundle from the one calibration and the rehearsal read
  cal_upd  : calibration.json says it ran 6 updates (the configuration says 150 in the exercise, 2,000 registered): a typed --updates
  full_upd : rehearsal.json says the full-length cells ran 1 update (a typed --full-updates)
  device   : rates.json says the rehearsal trained on CPU with a typed reason (no failed MPS attempt exists)
  dry_rec  : calibration.json carries {"synthetic": true, "mode": "test"} markers (a stand-in record)
Usage: python r7_freeze_inputs.py <e2e parent dir> <work dir> <python>
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

E, W, PY = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(), sys.argv[3]
CL = E / "clone"
G = ["git", "-c", "user.name=r", "-c", "user.email=r@example.invalid", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null"]


def sh(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, check=False)


pre_commit = sh(["git", "log", "--format=%H", "--grep", "pilot threshold", "-1"], CL).stdout.strip()
if W.exists():
    shutil.rmtree(W)
N = W / "repo"
N.mkdir(parents=True)
arch = subprocess.run(["git", "-C", str(CL), "archive", pre_commit], capture_output=True, check=True).stdout
subprocess.run(["tar", "-x", "-C", str(N)], input=arch, check=True)
sh([*G, "init", "-q", "-b", "main"], N)
sh([*G, "add", "-A"], N)
sh([*G, "commit", "-q", "-m", "pre-freeze source (exercise configuration)"], N)
shutil.copytree(CL / "data" / "p10s2-bundle", N / "data" / "p10s2-bundle")
env = {**os.environ, "PYTHONPATH": str(N / "src"), "PYTHONDONTWRITEBYTECODE": "1"}
# a second, different stand-in bundle (replicates = 2, so a different manifest), built with the repository's own stand-in code and test seeds
r = sh([PY, "-c", "from pathlib import Path; from studies.p10s2 import standins; from studies.p10s2.worldio import write_bundle; b, _ = standins.build_synthetic_bundle(2); write_bundle(b, Path('data/other-bundle'))"], N, env)
assert r.returncode == 0, r.stderr[-1500:]
led_lines = [ln for ln in (CL / "experiments" / "P10S2" / "ledger.jsonl").read_text().splitlines() if ln.strip()]
pre_lines = []
for ln in led_lines:
    e = json.loads(ln)
    if e["kind"] in ("gates-registered", "train", "evaluate", "timing", "recompute", "analysis", "report"):
        break
    pre_lines.append(ln)


def case(name: str, edit, data_dir: str = "data/p10s2-bundle") -> dict:  # noqa: ANN001
    sh(["git", "clean", "-fdq", "studies/p10s2/freeze"], N)
    sh(["git", "checkout", "-q", "--", "studies/p10s2/freeze"], N)
    (N / "experiments" / "P10S2").mkdir(parents=True, exist_ok=True)
    (N / "experiments" / "P10S2" / "ledger.jsonl").write_text("\n".join(pre_lines) + "\n")
    pre = W / f"pre-{name}"
    if pre.exists():
        shutil.rmtree(pre)
    shutil.copytree(E / "pre-run", pre, ignore=shutil.ignore_patterns("rehearsal-scratch"))
    edit(pre)
    p = sh([PY, "-m", "studies.p10s2.stages", "freeze", "--pre-run-dir", str(pre), "--run-dir", str(W / f"reg-{name}"), "--data-dir", data_dir], N, env)
    tail = [ln for ln in (p.stdout + p.stderr).splitlines() if "NumPy" not in ln and "_conversion" not in ln and "oracle-assisted" not in ln][-2:]
    plan = N / "studies" / "p10s2" / "freeze" / "plan.json"
    design = json.loads(plan.read_text())["design"] if plan.exists() else None
    return {"case": name, "exit": p.returncode, "accepted": p.returncode == 0, "design": design, "tail": tail}


def jedit(rel: str, fn):  # noqa: ANN001
    def _e(pre: Path) -> None:
        f = pre / rel
        d = json.loads(f.read_text())
        fn(d)
        f.write_text(json.dumps(d))
    return _e


rows = [
    case("control", lambda pre: None),
    case("pilot", jedit("calibration.json", lambda d: d["pilot"].update(ok=False, outcome="NOT STARTED: STUDENT CANNOT USE THE MEMORY ON THIS TASK"))),
    case("bundle", lambda pre: None, data_dir="data/other-bundle"),
    case("cal_upd", jedit("calibration.json", lambda d: d.update(updates=6, snapshot_updates=3))),
    case("full_upd", jedit("rehearsal.json", lambda d: d["raw"]["full_length"].update(updates=1.0))),
    case("device", jedit("rates.json", lambda d: d.update(train_device="cpu", train_device_reason="typed by hand; no MPS attempt was made"))),
    case("dry_rec", jedit("calibration.json", lambda d: d.update(synthetic=True, mode="test"))),
]
other = json.loads((N / "data" / "other-bundle" / "manifest.json").read_text())
orig = json.loads((N / "data" / "p10s2-bundle" / "manifest.json").read_text())
res = {"pre_freeze_commit_of_clone": pre_commit, "ledger_entries_copied": len(pre_lines), "bundles_differ": other != orig, "cases": rows}
(W / "r7.json").write_text(json.dumps(res, indent=1))
for row in rows:
    print(json.dumps(row))
