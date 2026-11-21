#!/bin/sh
# P10IS0 registered stage "x8" (ADR-0023 sections 10 and 14: fixed launch script, no free arguments).
# Takes exactly the run directory and the freeze commit; every other value (items, caps, seeds, paths) comes from studies/p10is0/freeze/plan.json and configs/p10is0_overload.toml.
# The driver refuses unless the tree is clean, the freeze commit is an ancestor of HEAD, the frozen inputs match their recorded hashes, the plan verifies, a committed
# results/p10is0-freeze-*/DECISION_2.md names the freeze commit, and the run directory is git-ignored and untracked. A stage that reaches its cap is PAUSED: run this script again to resume it.
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
exec uv run --locked python -m studies.p10is0.stages registered x8 --run-dir "$RUN_DIR" --freeze-commit "$FREEZE_COMMIT"
