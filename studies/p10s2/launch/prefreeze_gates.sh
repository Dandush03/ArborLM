#!/bin/sh
# P10S2 pre-freeze stage "prefreeze-gates" (ADR-0022 section 12.3): the gates stage at real size on rehearsal seeds, before the freeze, on calibration items (no evaluation panel is scored; the lead's ruling).
# Takes exactly the run directory and the code commit (which must equal a clean HEAD; the driver refuses otherwise). The stage cap is passed here and equals configs/p10s2_transfer.toml
# [rehearsal] prefreeze_gates_cap_seconds (a test compares them). The frozen data files are in <run-dir>/data/bundle. It needs <run-dir>/calibration.json (the read layer and the LoRA learning rate). The device is the
# configured training device (MPS): there is no typed value.
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
exec uv run --locked python -m studies.p10s2.stages prefreeze-gates --run-dir "$RUN_DIR" --code-commit "$CODE_COMMIT" --stage-cap-seconds 1440 --data-dir "$RUN_DIR/data/bundle"
