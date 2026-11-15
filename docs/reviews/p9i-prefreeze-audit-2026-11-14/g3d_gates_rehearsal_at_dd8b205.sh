#!/bin/sh
# G3d (auditor, Opus 5.5): at the frozen code dd8b205 the gates stage could not run on rehearsal seeds, so
# its first real-size execution was the registered run. Throw-away clone at dd8b205, rehearsal draw 2, real
# B101/B102 backbones read from EXPERIMENTS, private ledger, scratch run directory. Nothing is trained
# beyond what the gates stage does before it fails.
# usage: g3d_gates_rehearsal_at_dd8b205.sh WORKTREE EXPERIMENTS SCRATCH
W=$1; E=$2; S=$3
rm -rf "$S/clone" "$S/run"
git clone -q "$W" "$S/clone" && (cd "$S/clone" && git checkout -q dd8b205 && git log --oneline -1)
for st in generate gates; do
  (cd "$S/clone" && PYTHONPATH="$S/clone" "$W/.venv/bin/python" -m studies.p9i.stages $st --mode rehearsal --draw 2 --run-dir "$S/run" --experiments-root "$E" --ledger "$S/ledger.json" --stage-cap-seconds 600 --workers 1 2>/dev/null)
  echo "$st exit $?"
done
echo "--- gates.log (last 3 lines)"; tail -3 "$S/run/gates/gates.log"
echo "--- gates.json written: $(test -f "$S/run/gates.json" && echo yes || echo no)"
