#!/bin/sh
# C5 (auditor, Opus 5.5): registered-mode preconditions and the ACCEPT path of the registered driver in a THROW-AWAY clone
# (never in the repository): a synthetic freeze plan and caps file are committed in the clone, pointing at the real calibration
# record and the real rehearsal projection by sha256. The only registered stage invoked is stage1_gate on an empty scratch run
# directory (it trains nothing, reads no registered seed and charges no ledger). The ledgers are redirected to the scratch dir.
# usage: c5_preconditions_clone.sh WORKTREE SCRATCH EXPERIMENTS_ROOT
set -eu
WT=$1; S=$2/c5; EXP=$3
PY="$WT/.venv/bin/python"
rm -rf "$S"; mkdir -p "$S"
git clone --quiet --no-hardlinks "$WT" "$S/clone"
cd "$S/clone"
git -c advice.detachedHead=false checkout --quiet "$(git -C "$WT" rev-parse HEAD)"
CAL="$EXP/P9IIC-20261115T071159540788Z-1a93c3ded92e40628c2abb9bd4235188/calibration.json"
PRJ="$EXP/P9IIH-20261115T071753736302Z-733bbf7ebca44117a5bdf2792f90940b/projection.json"
mkdir -p studies/p9ii/freeze
"$PY" - "$CAL" "$PRJ" <<'PYEOF'
import hashlib, json, sys
cal, prj = sys.argv[1], sys.argv[2]
h = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
caps = {"gates": 600, "stage1": {"train": 4000, "evaluate": 200}, "stage2": {"train": 7000, "evaluate": 300}, "stage3": {"train": 1400, "evaluate": 100}, "analysis": 600, "report": 600}
json.dump(caps, open("studies/p9ii/freeze/stage_caps.json", "w"))
json.dump({"caps": caps, "calibration": {"path": cal, "sha256": h(cal)}, "projection": {"path": prj, "sha256": h(prj)}}, open("studies/p9ii/freeze/plan.json", "w"))
PYEOF
git add studies/p9ii/freeze
git -c user.name=auditor -c user.email=auditor@invalid -c commit.gpgsign=false commit --quiet --no-verify -m "throw-away freeze (audit c5)"
FREEZE=$(git rev-parse HEAD)
echo "freeze commit in the clone: $FREEZE"
run() { echo "--- $1"; shift; set +e; "$@" 2>&1 | grep -v "Warn\|cpu = " | tail -3; echo "exit: $?"; set -e; }
# 1. accept path: preconditions, plan, hash binding, then the stage-1 gate on an empty run dir
mkdir -p "$S/run"
run "accept: registered stage1_gate (clean tree, freeze = HEAD)" env PYTHONPATH="$S/clone" "$PY" -m studies.p9ii.stages registered stage1_gate --run-dir "$S/run" --freeze-commit "$FREEZE" --repo "$S/clone" --ledger-root "$S" --experiments-root "$EXP"
echo "stage_gate_1.json:"; cat "$S/run/stage_gate_1.json" | "$PY" -c "import json,sys; r=json.load(sys.stdin); print({k: r[k] for k in ('run','status','reason') if k in r})"
# 2. refusals
echo "x" > untracked.txt
run "dirty tree (untracked file)" env PYTHONPATH="$S/clone" "$PY" -m studies.p9ii.stages registered stage1_gate --run-dir "$S/run2" --freeze-commit "$FREEZE" --repo "$S/clone" --ledger-root "$S" --experiments-root "$EXP"
rm untracked.txt
run "freeze commit not a commit" env PYTHONPATH="$S/clone" "$PY" -m studies.p9ii.stages registered stage1_gate --run-dir "$S/run2" --freeze-commit deadbeef --repo "$S/clone" --ledger-root "$S" --experiments-root "$EXP"
run "no freeze commit" env PYTHONPATH="$S/clone" "$PY" -m studies.p9ii.stages registered stage1_gate --run-dir "$S/run2" --repo "$S/clone" --ledger-root "$S" --experiments-root "$EXP"
echo "# change" >> studies/p9ii/report.py
git -c user.name=auditor -c user.email=auditor@invalid -c commit.gpgsign=false commit --quiet --no-verify -am "post-freeze code change"
run "code changed after the freeze (committed)" env PYTHONPATH="$S/clone" "$PY" -m studies.p9ii.stages registered stage1_gate --run-dir "$S/run2" --freeze-commit "$FREEZE" --repo "$S/clone" --ledger-root "$S" --experiments-root "$EXP"
git reset --quiet --hard "$FREEZE"
"$PY" - <<'PYEOF'
import json
p = "studies/p9ii/freeze/plan.json"; d = json.load(open(p)); d["calibration"]["sha256"] = "0" * 64; json.dump(d, open(p, "w"))
PYEOF
git -c user.name=auditor -c user.email=auditor@invalid -c commit.gpgsign=false commit --quiet --no-verify -am "tampered calibration hash"
T2=$(git rev-parse HEAD)
run "calibration record does not hash to the frozen value" env PYTHONPATH="$S/clone" "$PY" -m studies.p9ii.stages registered stage1_gate --run-dir "$S/run3" --freeze-commit "$T2" --repo "$S/clone" --ledger-root "$S" --experiments-root "$EXP"
git reset --quiet --hard "$FREEZE"
run "launch script with one argument" sh studies/p9ii/launch/stage1.sh "$S/run4"
run "registered generate without the freeze-time flag" env PYTHONPATH="$S/clone" "$PY" -m studies.p9ii.stages generate --mode registered --run-dir "$S/run5" --ledger-root "$S" --experiments-root "$EXP"
run "--dry with registered" env PYTHONPATH="$S/clone" "$PY" -m studies.p9ii.stages registered stage1 --dry --run-dir "$S/run6" --freeze-commit "$FREEZE" --repo "$S/clone" --ledger-root "$S"
ls "$S"
