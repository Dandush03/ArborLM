#!/bin/sh
# P10-I-S1: independent recomputation of the REGISTERED run, to be launched only after the report stage has finished.
# Writes only into a NEW directory under this folder; reads the run directory, the frozen plan and the rehearsal record named by the freeze record.
# Every step has a timeout. No delete, no move, nothing under /tmp.
set -u
HERE=/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/p10is1_recompute_20261121
E=/Users/daniellaloush/dandush03/ArborLM/experiments
RUN=$E/P10IS1-pre-20261118
PLAN=$HERE/frozen/studies/p10is1/freeze/plan.json            # git archive of freeze commit 46bf55a; SHA-256 must be e1479e36...
REH=$E/P10IS1-counting-20261121-rehearsal.json                # the rehearsal record the freeze record names; SHA-256 must be 87854244...
PY=/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-ab0efbf6bb233cc02/.venv/bin/python   # used as a plain Python 3.12 with -I (no project import)
OUT=$HERE/registered_$(date -u +%Y%m%dT%H%M%SZ)
[ -e "$OUT" ] && { echo "refused: $OUT exists"; exit 2; }
SUP=$E/P10IS1-pre-20261118-analysis-supplement   # route (c): the registered analysis/report stages are ENGINEERING STOP; the frozen analysis runs through the supplement driver
[ -f "$RUN/report/REPORT.md" ] || [ -f "$SUP/report/REPORT_SUPPLEMENT.md" ] || { echo "refused: neither the registered report nor the analysis supplement exists yet"; exit 2; }
[ "$(shasum -a 256 "$PLAN" | cut -c1-64)" = "e1479e365300fb92f63522ae69cec79e928c5f458d86fde91e8beeb64f0f1864" ] || { echo "refused: plan hash"; exit 2; }
[ "$(shasum -a 256 "$REH" | cut -c1-64)" = "87854244262efd6cbdb9b0f65b68c7086b0b0ec6434cde68dfe3b6eb78f5c3d5" ] || { echo "refused: rehearsal record hash"; exit 2; }
mkdir "$OUT"
cd "$HERE" || exit 2
timeout 3600 nice -n 10 "$PY" -I -B recompute.py --run-dir "$RUN" --plan "$PLAN" --config "$HERE/frozen/configs/p10is1_capacity.toml" \
  --qualification "$REH" --madds "$HERE/madds_per_update.json" --out "$OUT/recompute.json" > "$OUT/recompute.log" 2>&1
echo "recompute exit $?" >> "$OUT/recompute.log"
if [ -f "$RUN/analysis/analysis.json" ]; then STUDY_A="$RUN/analysis/analysis.json"; else STUDY_A="$SUP/analysis/analysis_supplement.json"; fi
if [ -f "$STUDY_A" ]; then
  echo "comparing with $STUDY_A" > "$OUT/compare.out"
  timeout 600 "$PY" -I -B compare.py "$OUT/recompute.json" "$STUDY_A" >> "$OUT/compare.out" 2>&1
  echo "compare exit $?" >> "$OUT/compare.out"
else
  echo "no study analysis file found: no comparison" > "$OUT/compare.out"
fi
cat "$OUT/recompute.log"; head -40 "$OUT/compare.out"
echo "outputs in $OUT"
