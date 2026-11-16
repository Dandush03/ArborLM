"""Recheck script r5 (Claude Opus 5.5 auditor; not Astra review). M4: what does the freeze accept as evidence that
P10-S0's last training stage has finished? Calls stages.freeze_concurrency (the code under audit) with an injected empty
process list and an injected live S0 line (never the real list), and arbitrary evidence files written by me.
  UV_NO_SYNC=1 nice uv run --locked python -I r5_freeze_evidence.py <worktree root> <scratch dir>
"""
import argparse, json, shutil, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from studies.p10s1 import stages, timing
from studies.p9 import pool  # noqa: E402
D = Path(sys.argv[2]); D.mkdir(parents=True, exist_ok=True)
files = {
    "empty file": "",
    "JSON {}": "{}",
    "an S0 manifest that is INCOMPLETE": json.dumps({"kind": "stage_manifest", "study": "P10S0", "stage": "train-probe", "status": "INCOMPLETE"}),
    "a P10-S1 calibration manifest": json.dumps({"kind": "stage_manifest", "study": "P10S1", "stage": "calibrate-load-row-up", "status": "COMPLETE"}),
    "plain text": "hello",
}
timing.running_commands = lambda: []
for name, text in files.items():
    p = D / (name.replace(" ", "_") + ".json"); p.write_text(text)
    ns = argparse.Namespace(dry=False, s0_training_manifest=str(p), s0_refusal_record=None)
    try:
        rec = stages.freeze_concurrency(ns)
        print(f"{name:40s}: ACCEPTED; statement: {rec['statement']!r}")
    except pool.StageRefused as exc:
        print(f"{name:40s}: refused ({exc})")
ns = argparse.Namespace(dry=False, s0_training_manifest=str(D / "JSON_{}.json"), s0_refusal_record=str(D / "plain_text.json"))
rec = stages.freeze_concurrency(ns); print(f"{'WX manifest {} + refusal record plain text':40s}: ACCEPTED, keys {sorted(rec)}")
timing.running_commands = lambda: ["sh -c run_s0.sh"]  # the S0 shell wrapper between two stages (no 'studies.p10s0' in its command line)
print("between two S0 stages (wrapper only alive):", stages.freeze_concurrency(argparse.Namespace(dry=False, s0_training_manifest=str(D / "JSON_{}.json"), s0_refusal_record=None))["statement"])
timing.running_commands = lambda: ["/x/.venv/bin/python -m studies.p10s0.stages work train --labels a"]
try:
    stages.freeze_concurrency(argparse.Namespace(dry=False, s0_training_manifest=str(D / "JSON_{}.json"), s0_refusal_record=None)); print("live S0 worker: ACCEPTED (bad)")
except timing.OtherStudyRunning as exc:
    print("live S0 worker: refused (OtherStudyRunning)")
shutil.rmtree(D)
