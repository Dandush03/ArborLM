#!/bin/sh
# P10IS5 stage "e2" (ADR-0028 sections 8 and 12: fixed launch script, no free arguments).
# Takes exactly the run directory and the freeze commit; every other value (geometry, seeds, paths, caps) comes from studies/p10is5/freeze/plan.json and configs/p10is5_ssd.toml.
# The driver refuses unless the tree is clean, the freeze commit is an ancestor of HEAD, the frozen files equal their content at that commit, the plan and freeze record verify, and a committed
# results/p10is5-freeze-*/DECISION_2.md names the freeze commit. A PAUSED stage (quiet rule, write budget, hours) is resumed by running this script again.
# No loop, no sleep, no wait here: every wait inside the driver has a deadline. No word splitting: every expansion is quoted.
set -eu
if [ "$#" -ne 2 ]; then
    echo "usage: $0 <run-dir> <freeze-commit>" >&2
    exit 2
fi
abs() {
    case "$1" in
        /*) printf '%s\n' "$1" ;;
        *) printf '%s\n' "$PWD/$1" ;;
    esac
}
RUN_DIR=$(abs "$1")
FREEZE_COMMIT=$2
cd "$(dirname "$0")/../../.."
exec caffeinate -i uv run --locked python -m studies.p10is5.stages registered e2 --run-dir "$RUN_DIR" --freeze-commit "$FREEZE_COMMIT"
