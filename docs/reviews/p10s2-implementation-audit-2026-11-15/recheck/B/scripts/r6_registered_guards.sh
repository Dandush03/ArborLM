#!/bin/sh
# Re-check B, R6: registered-mode guards, on the KEPT end-to-end clone (stand-ins, test seeds; the clone's configuration is the exercise's). Each probe edits only the run directory or the
# git-ignored ledger, and restores them afterwards. Usage: sh r6_registered_guards.sh <e2e parent dir> <python>
set -u
E=$1; PY=$2
CL=$E/clone; REG=$E/registered-run; PRE=$E/pre-run; BK=$E/r6-backup
LED=$CL/experiments/P10S2/ledger.jsonl
FC=$(git -C "$CL" rev-parse HEAD~1); DC=$(git -C "$CL" rev-parse HEAD)
export PATH="$E/bin:$PATH" E2E_PYTHON="$PY" PYTHONPATH="$CL/src" PYTHONDONTWRITEBYTECODE=1
rm -rf "$BK"; mkdir -p "$BK"; cp -p "$LED" "$BK/ledger.jsonl"; cp -Rp "$REG" "$BK/registered-run"
run() { echo "--- $1"; shift; (cd "$CL" && "$@") > "$BK/out.txt" 2>&1; c=$?; grep -v 'NumPy\|_conversion\|oracle-assisted' "$BK/out.txt" | tail -3; echo "exit $c"; }
restore() { rm -rf "$REG"; cp -Rp "$BK/registered-run" "$REG"; cp -p "$BK/ledger.jsonl" "$LED"; }
undo_report() { rm -f "$REG/stages/report.json" "$REG/REPORT.md" "$REG/memory/report.json"; }

echo "freeze commit $FC; decision commit $DC"
# P1: the report stage, not yet run, with a FRESH (empty) study ledger: is P (the pre-freeze charges) required?
undo_report; mv "$LED" "$BK/ledger.moved"
run "P1 report.sh with the study ledger moved aside (fresh ledger, P = 0, cap 36 = plan cap)" sh studies/p10s2/launch/report.sh "$REG" "$FC"
restore
# P2: the same with the ledger holding 35.99 h: the room check reads it
undo_report; printf '%s\n' '{"kind": "audit-other", "status": "completed", "charged_hours": 35.99, "wall_seconds": 129564, "workers": 1, "registered": false, "run_id": "x", "t_start": 0, "process": "recheck", "note": "", "at": ""}' >> "$LED"
run "P2 report.sh with 35.99 h already charged" sh studies/p10s2/launch/report.sh "$REG" "$FC"
restore
# P3: a cap raise recorded by hand in the ledger after the registered stages (Ledger.append_cap_raise has no guard of its own)
undo_report; (cd "$CL" && "$PY" -c "from studies.p10s2.ledger import Ledger; Ledger().append_cap_raise(54.0, {'by': 'recheck, by hand'})")
run "P3 report.sh after a hand-appended cap-raise entry (54 h)" sh studies/p10s2/launch/report.sh "$REG" "$FC"
restore
# P4: raise-cap and freeze after registered processes; also with the ledger moved aside (only the committed plan is left as evidence)
run "P4a raise-cap after the registered run" "$PY" -m studies.p10s2.stages raise-cap --run-dir "$PRE"
run "P4b freeze again after the registered run" "$PY" -m studies.p10s2.stages freeze --pre-run-dir "$PRE" --run-dir "$REG" --data-dir data/p10s2-bundle
mv "$LED" "$BK/ledger.moved"
run "P4c raise-cap with a fresh ledger (plan committed in history)" "$PY" -m studies.p10s2.stages raise-cap --run-dir "$PRE"
run "P4d freeze with a fresh ledger" "$PY" -m studies.p10s2.stages freeze --pre-run-dir "$PRE" --run-dir "$REG" --data-dir data/p10s2-bundle
restore
git -C "$CL" status --porcelain
# P5: analysis before the recomputation: the recompute, analysis and report records removed
rm -f "$REG/stages/recompute.json" "$REG/stages/analysis.json" "$REG/stages/report.json" "$REG/outcome.json" "$REG/REPORT.md" "$REG/memory/analysis.json" "$REG/memory/report.json" "$REG/seeds/analysis.json"
run "P5 analysis.sh without a recompute completion record" sh studies/p10s2/launch/analysis.sh "$REG" "$FC"
restore
# P6: the run decision commit given as the freeze commit; a typed caps path; an extra argument
undo_report
run "P6a report.sh with the decision commit as --freeze-commit" sh studies/p10s2/launch/report.sh "$REG" "$DC"
run "P6b registered report with --caps ./studies/p10s2/freeze/stage_caps.json (same file, typed differently)" "$PY" -m studies.p10s2.stages registered report --run-dir "$REG" --freeze-commit "$FC" --caps ./studies/p10s2/freeze/stage_caps.json
run "P6c registered report with --device cpu" "$PY" -m studies.p10s2.stages registered report --run-dir "$REG" --freeze-commit "$FC" --caps studies/p10s2/freeze/stage_caps.json --device cpu
restore
# P7: train with a gates record whose G4 is false (the gates stage record says completed)
cp -Rp "$REG" "$BK/reg-for-p7"
rm -rf "$REG/stages/train.json" "$REG/stages/evaluate.json" "$REG/stages/timing.json" "$REG/stages/recompute.json" "$REG/stages/analysis.json" "$REG/stages/report.json"
"$PY" -c "import json,sys; p=sys.argv[1]; g=json.load(open(p)); g['G4']['ok']=False; json.dump(g, open(p,'w'))" "$REG/gates.json"
run "P7 train.sh with gates.json G4 ok = false" sh studies/p10s2/launch/train.sh "$REG" "$FC"
restore
git -C "$CL" status --porcelain
echo "restored: $(diff -rq "$REG" "$BK/registered-run" | wc -l | tr -d ' ') differences in the run directory; ledger identical: $(cmp -s "$LED" "$BK/ledger.jsonl" && echo yes || echo no)"
