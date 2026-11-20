#!/bin/sh
# P10IS3 registered stage "analysis" (ADR-0026 sections 10 and 11: fixed launch script, no free arguments).
# Takes exactly the run directory and the freeze commit; every other value (items, caps, seeds, paths, rate table) comes from studies/p10i_s3/freeze/plan.json and configs/p10i_s3_longer_training.toml.
# The driver refuses unless the tree is clean, the freeze commit is an ancestor of HEAD, the frozen files equal their content at that commit, the plan and freeze record verify, and a committed
# results/p10i-s3-freeze-*/DECISION_2.md names the freeze commit. A stage that reaches its cap, or whose lead pause file (<run-dir>/PAUSE_BY_LEAD) exists, is PAUSED: run this script again to resume it.
# No commit is made in this worktree while a registered stage runs. No loop, no sleep, no wait: the driver's own wait has a deadline (the stage cap). Every expansion is quoted.
set -eu
if [ "$#" -ne 2 ]; then
    echo "usage: $0 <run-dir> <freeze-commit>" >&2
    exit 2
fi
case "$1" in
    /*) RUN_DIR=$1 ;;
    *) RUN_DIR=$PWD/$1 ;;
esac
FREEZE_COMMIT=$2
cd "$(dirname "$0")/../../.."
exec uv run --locked python -m studies.p10i_s3.stages registered analysis --run-dir "$RUN_DIR" --freeze-commit "$FREEZE_COMMIT"
