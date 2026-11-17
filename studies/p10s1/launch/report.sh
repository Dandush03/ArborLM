#!/bin/sh
# P10S1 registered stage "report" (ADR-0021 section 10.3 and 11: fixed launch script, no free arguments).
# Takes exactly the run directory and the freeze commit; every other value (the stage cap from the frozen cap table, the plan, the seeds, the calibrated values)
# comes from the frozen plan and the frozen cap table, so no registered stage is launched by a typed command. The charged-hour cap is the config value
# resources.cap_hours; the driver refuses to start a stage whose cap exceeds what remains of it.
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
exec uv run --locked python -m studies.p10s1.stages registered report --run-dir "$RUN_DIR" --freeze-commit "$FREEZE_COMMIT" --caps studies/p10s1/freeze/stage_caps.json
