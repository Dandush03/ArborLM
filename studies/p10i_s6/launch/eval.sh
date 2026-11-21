#!/bin/sh
# P10IS6 registered stage "eval" (ADR-0031 section 16: fixed launch script, no free arguments).
# Takes exactly the run directory and the freeze commit; every other value (items, caps, seeds, paths, rate table) comes from studies/p10i_s6/freeze/plan.json and configs/p10i_s6_flat_lead_persistence.toml.
# The driver refuses unless the tree is clean, the freeze commit is an ancestor of HEAD, the frozen files equal their content at that commit, the plan and freeze record verify, and a committed
# results/p10i-s6-freeze-*/DECISION_2.md names the freeze commit. A stage that reaches its cap, or whose run directory holds a pause-request file, is PAUSED: run this script again to resume it.
# The keep-awake watcher (caffeinate, waiting on this very process) is part of the stage's own process family; this study registers no timing reading and has no quiet rule.
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
if command -v caffeinate >/dev/null 2>&1; then
    caffeinate -i -w "$$" &
fi
exec uv run --locked python -m studies.p10i_s6.stages registered eval --run-dir "$RUN_DIR" --freeze-commit "$FREEZE_COMMIT"
