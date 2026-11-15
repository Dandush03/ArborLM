#!/bin/sh
# R7 (auditor, Opus 5.5, re-check): the freeze procedure of studies/p9ii/freeze/README.md and the registered driver's accept and refuse paths in a THROW-AWAY
# clone at HEAD. NO registered or reserve data are generated: the sixteen data manifests are FABRICATED stand-ins (envelope-valid records with g1_passed,
# draw 5 marked failed so the draw plan substitutes reserve 1); generate.sh is exercised only on its refusal branches (wrong commit, dirty tree, wrong
# argument count), which exit before any generation. Registered stages run: stage1_gate, analysis, report (none reads data); stage1/stage2/stage3 are
# invoked only to show their cap lookup and that they refuse at the gates record before any data are built. Ledgers point at the scratch dir.
# usage: r7_freeze_clone.sh WORKTREE SCRATCH EXPERIMENTS_ROOT PROJECTION CALIBRATION
set -eu
WT=$1; S=$2/r7; EXP=$3; PRJ=$4; CAL=$5
PY="$WT/.venv/bin/python"
rm -rf "$S"; mkdir -p "$S"
git clone --quiet --no-hardlinks "$WT" "$S/clone"
cd "$S/clone"; git -c advice.detachedHead=false checkout --quiet "$(git -C "$WT" rev-parse HEAD)"
RUN="$S/registered-run"
say() { echo "--- $1"; }
drv() { env PYTHONPATH="$S/clone" "$PY" -m studies.p9ii.stages "$@" 2>&1 | grep -v "Warn\|cpu = " | tail -2; }
say "generate.sh refusals (exit before any generation)"
sh studies/p9ii/launch/generate.sh "$RUN" 2>&1 | tail -1 || true
sh studies/p9ii/launch/generate.sh "$RUN" deadbeef 2>&1 | tail -1 || true
echo x > dirt.txt; sh studies/p9ii/launch/generate.sh "$RUN" "$(git rev-parse HEAD)" 2>&1 | tail -1 || true; rm dirt.txt
say "fabricated data manifests (stand-ins), then the draw plan (pure function of the manifests)"
env PYTHONPATH="$S/clone" "$PY" - "$RUN" <<'PYEOF'
import sys
from pathlib import Path
from studies.p9ii import core
run = Path(sys.argv[1])
for name in (*core.DRAW_NAMES, *core.RESERVE_NAMES):
    core.write_record(run / "draws" / name / "data_manifest.json", {**core.envelope("data_manifest"), "seed_set": name, "g1_passed": name != "p9ii-draw-5", "sha256s": {"stand-in": "audit r7, not data"}, "dry": False})
PYEOF
drv draw-plan --run-dir "$RUN"
say "caps (pure function of the rehearsal-2 projection; analysis/report walls from r4)"
drv caps --projection "$PRJ" --gates-wall-seconds 8.3 --analysis-wall-seconds 8.1 --report-wall-seconds 0.1 --out studies/p9ii/freeze/stage_caps.json
env PYTHONPATH="$S/clone" "$PY" - "$RUN" "$PRJ" "$CAL" <<'PYEOF'
import hashlib, json, sys
from pathlib import Path
run, prj, cal = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
h = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
names = sorted(p.parent.name for p in (run / "draws").glob("*/data_manifest.json"))
plan = {"calibration": {"path": cal, "sha256": h(cal)}, "projection": {"path": prj, "sha256": h(prj)}, "stage_caps_sha256": h("studies/p9ii/freeze/stage_caps.json"),
        "run_dir": str(run), "draw_plan": {"sha256": h(run / "draw_plan.json")}, "data_manifests": {n: h(run / "draws" / n / "data_manifest.json") for n in names}}
Path("studies/p9ii/freeze/plan.json").write_text(json.dumps(plan, indent=1))
print("plan.json written;", len(names), "data manifests;", json.loads((run / "draw_plan.json").read_text())["replacements"])
PYEOF
git add studies/p9ii/freeze; git -c user.name=auditor -c user.email=auditor@invalid -c commit.gpgsign=false commit --quiet --no-verify -m "throw-away freeze (audit r7)"
F=$(git rev-parse HEAD); echo "freeze commit in the clone: $F"
COMMON="--freeze-commit $F --repo $S/clone --ledger-root $S --experiments-root $EXP"
say "ACCEPT: registered stage1_gate (no Stage 1 records -> INCOMPLETE, nothing trained)"; drv registered stage1_gate --run-dir "$RUN" $COMMON
say "ACCEPT: registered analysis and report (no records -> NOT_INTERPRETED)"; drv registered analysis --run-dir "$RUN" $COMMON; drv registered report --run-dir "$RUN" $COMMON
"$PY" -c "import json,sys; a=json.load(open('$RUN/analysis.json'))['result']; print('analysis outcome:', a['outcome']['outcome'], '| replaced draws:', a['assessment']['replaced_draws'])"
say "cap lookup of stage2/stage3 from a gate record, then refusal at the gates record (no data built)"
rm -f "$RUN/stage_gate_1.json"
env PYTHONPATH="$S/clone" "$PY" - "$RUN" <<'PYEOF'
import sys
from pathlib import Path
from studies.p9ii import core
run = Path(sys.argv[1])
core.write_record(run / "stage_gate_1.json", {**core.envelope("stage_gate"), "run": True, "advancing": ["A5-C", "A2"], "status": None})
core.write_record(run / "stage_gate_3.json", {**core.envelope("stage_gate"), "run": True, "selected": "A1", "status": None})
PYEOF
drv registered stage2 --run-dir "$RUN" $COMMON
drv registered stage3 --run-dir "$RUN" $COMMON
env PYTHONPATH="$S/clone" "$PY" -c "
import json; from pathlib import Path; from studies.p9ii import stages
caps=json.load(open('studies/p9ii/freeze/stage_caps.json')); run=Path('$RUN')
print('stage2 cap for A5-C+A2:', stages.stage_caps_for('stage2', caps, run)); print('stage3 cap for A1:', stages.stage_caps_for('stage3', caps, run))
try:
    stages.require_draw_plan(run); print('draw plan ok accepted')
except Exception as e: print('draw plan refused:', e)
" 2>&1 | grep -v "Warn\|cpu = "
say "REFUSALS"
cp "$RUN/draws/p9ii-draw-7/data_manifest.json" "$S/keep.json"; echo " " >> "$RUN/draws/p9ii-draw-7/data_manifest.json"
drv registered stage1_gate --run-dir "$RUN" $COMMON; cp "$S/keep.json" "$RUN/draws/p9ii-draw-7/data_manifest.json"
mkdir -p "$S/other-run"; drv registered stage1_gate --run-dir "$S/other-run" $COMMON
drv registered stage1_gate --run-dir "$RUN" $COMMON --caps other_caps.json
env PYTHONPATH="$S/clone" "$PY" - "$RUN" <<'PYEOF' 2>&1 | grep -v "Warn\|cpu = "
import json, sys
from pathlib import Path
from studies.p9ii import core, stages
run = Path(sys.argv[1])
p = run / "draw_plan.json"; keep = p.read_text()
rec = json.loads(keep); rec["ok"] = False; p.write_text(json.dumps(rec))
try:
    stages.require_draw_plan(run); print("draw plan with ok false: ACCEPTED (finding)")
except Exception as e:
    print("draw plan with ok false: refused:", str(e)[:100])
p.write_text(keep)
m = run / "draws" / "p9ii-reserve-1" / "data_manifest.json"; mk = m.read_text(); r = json.loads(mk); r["g1_passed"] = False; m.write_text(json.dumps(r))
try:
    stages.require_draw_plan(run); print("reserve used with failed G1: ACCEPTED (finding)")
except Exception as e:
    print("reserve used with failed G1: refused:", str(e)[:100])
m.write_text(mk)
PYEOF
"$PY" - <<'PYEOF'
import json
p = "studies/p9ii/freeze/plan.json"; d = json.load(open(p)); d["projection"]["sha256"] = "0" * 64; json.dump(d, open(p, "w"))
PYEOF
git -c user.name=auditor -c user.email=auditor@invalid -c commit.gpgsign=false commit --quiet --no-verify -am "tampered projection hash"
drv registered stage1_gate --run-dir "$RUN" --freeze-commit "$(git rev-parse HEAD)" --repo "$S/clone" --ledger-root "$S" --experiments-root "$EXP"
git reset --quiet --hard "$F"
echo "# post-freeze edit" >> docs/decisions/ADR-0019-robust-sparse-address-learning.md
git -c user.name=auditor -c user.email=auditor@invalid -c commit.gpgsign=false commit --quiet --no-verify -am "ADR edited after the freeze"
drv registered stage1_gate --run-dir "$RUN" $COMMON
git reset --quiet --hard "$F"
say "launch script argument check"; sh studies/p9ii/launch/stage2.sh "$RUN" 2>&1 | tail -1 || true
grep -h "exec uv run" studies/p9ii/launch/*.sh | sed 's/.*stages registered //' | sort
