#!/bin/sh
# P10S2 registered stage "timing" (ADR-0022 section 16: fixed launch script, no free arguments): the timing benchmark, after all training, one process, CPU, six threads.
# Takes exactly the run directory and the freeze commit; every other value (design, data, calibration and projection records, caps, cap in force) comes from the
# frozen plan and the frozen cap table, so no registered stage is launched by a typed command.
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
exec uv run --locked python -m studies.p10s2.stages registered timing --run-dir "$RUN_DIR" --freeze-commit "$FREEZE_COMMIT" --caps studies/p10s2/freeze/stage_caps.json
