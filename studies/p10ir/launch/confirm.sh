#!/bin/sh
# P10IR registered stage "confirm" (ADR-0029 sections 11 and 13: fixed launch script, no free arguments).
# Takes exactly the run directory and the freeze commit; every other value (items, caps, seeds, paths) comes from studies/p10ir/freeze/plan.json and configs/p10ir_routing.toml.
# The driver refuses unless the tree is clean, the freeze commit is an ancestor of HEAD, the frozen files equal their content at that commit, the plan verifies, and a committed
# results/p10ir-freeze-*/DECISION_2_<group>.md names the freeze commit. A stage that reaches its cap is PAUSED: run this script again to resume it.
# No loop, no sleep, no wait: the driver's own wait has a deadline (the stage cap). No word splitting: every expansion is quoted.
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
exec uv run --locked python -m studies.p10ir.stages registered confirm --run-dir "$RUN_DIR" --freeze-commit "$FREEZE_COMMIT"
