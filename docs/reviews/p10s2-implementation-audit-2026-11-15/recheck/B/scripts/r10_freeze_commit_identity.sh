#!/bin/sh
# Re-check B, R10 (defect class e): which commit freeze.check_freeze_identity takes as "the commit that added plan.json" (added[-1] of `git log --diff-filter=A`, newest first => the OLDEST add on
# the current branch). Usage: sh r10_freeze_commit_identity.sh <dir>
set -eu
D=$1; rm -rf "$D"; mkdir -p "$D"; cd "$D"
G="git -c user.name=r -c user.email=r@example.invalid -c commit.gpgsign=false -c core.hooksPath=/dev/null"
$G init -q -b main; mkdir -p studies/p10s2/freeze; echo a > x; $G add -A; $G commit -qm base
echo '{"v":1}' > studies/p10s2/freeze/plan.json; $G add -A; $G commit -qm "freeze A"; A=$(git rev-parse HEAD)
git rm -q studies/p10s2/freeze/plan.json; $G commit -qm "delete"
mkdir -p studies/p10s2/freeze; echo '{"v":1}' > studies/p10s2/freeze/plan.json; $G add -A; $G commit -qm "re-add B (same content)"; B=$(git rev-parse HEAD)
echo "A=$A"; echo "B=$B"; echo "git log --diff-filter=A (newest first):"; git log --diff-filter=A --format='%H %s' -- studies/p10s2/freeze/plan.json
git checkout -qb side "$A~1"; mkdir -p studies/p10s2/freeze; echo '{"v":2}' > studies/p10s2/freeze/plan.json; $G add -A; $G commit -qm "side add S"; git checkout -q main
$G merge -q --no-ff -s ours side -m "merge side (ours)"
echo "after merging (strategy ours) a side branch that also added plan.json:"; git log --diff-filter=A --format='%H %s' -- studies/p10s2/freeze/plan.json
echo "with --all (what plan_in_history uses):"; git log --all --format='%H %s' -1 -- studies/p10s2/freeze/plan.json
