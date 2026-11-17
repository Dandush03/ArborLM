#!/bin/sh
# P9II registered stage "stage1" (ADR-0019 section 9: fixed launch script, no free arguments).
# Takes exactly the run directory and the freeze commit; every other value (caps, calibration record, projection
# record, draw plan) comes from the frozen plan, so no registered stage is launched by a typed command.
# No word splitting: every expansion is quoted and no argument is ever re-parsed by the shell.
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
exec uv run --locked python -m studies.p9ii.stages registered stage1 --run-dir "$RUN_DIR" --freeze-commit "$FREEZE_COMMIT" --caps studies/p9ii/freeze/stage_caps.json
