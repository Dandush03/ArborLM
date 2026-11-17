#!/bin/sh
# P10S2 pre-freeze stage "calibrate" (ADR-0022 sections 12.1, 12.2): calibration and the pilot gate, calibration seeds, D_cal only.
# Takes exactly the run directory and the code commit (which must equal a clean HEAD; the driver refuses otherwise). The stage cap is passed here and equals configs/p10s2_transfer.toml
# [prefreeze_caps] calibrate (a test compares them). The frozen data files are in <run-dir>/data/bundle. The number of updates is read from the configuration ([calibration] updates) and the device is the configured training device (MPS): there is no typed value.
# No word splitting: every expansion is quoted and no argument is ever re-parsed by the shell.
set -eu
if [ "$#" -ne 2 ]; then
    echo "usage: $0 <run-dir> <code-commit>" >&2
    exit 2
fi
case "$1" in
    /*) RUN_DIR=$1 ;;
    *) RUN_DIR=$PWD/$1 ;;
esac
CODE_COMMIT=$2
cd "$(dirname "$0")/../../.."
exec uv run --locked python -m studies.p10s2.stages calibrate --run-dir "$RUN_DIR" --code-commit "$CODE_COMMIT" --stage-cap-seconds 7920 --data-dir "$RUN_DIR/data/bundle"
