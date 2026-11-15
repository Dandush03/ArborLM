#!/bin/sh
# P10S0 registered stage "wx" (ADR-0020 section 10.2: fixed launch script, no free arguments).
# Takes exactly the run directory and the freeze commit; every other value (stage caps, arm-selection record, projection
# record, draw plan, the headroom decision) comes from the frozen plan and the frozen cap table, so no registered stage is
# launched by a typed command. The script passes its stage cap file with --caps; the driver refuses any other path.
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
exec uv run --locked python -m studies.p10s0.stages registered wx --run-dir "$RUN_DIR" --freeze-commit "$FREEZE_COMMIT" --caps studies/p10s0/freeze/stage_caps.json
