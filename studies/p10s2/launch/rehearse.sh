#!/bin/sh
# P10S2 pre-freeze stage "rehearse" (ADR-0022 section 13.3): the rehearsal on rehearsal seeds: rates, memory peaks, headroom check, rung rule.
# Takes exactly the run directory and the code commit (which must equal a clean HEAD; the driver refuses otherwise). The stage cap is passed here and equals configs/p10s2_transfer.toml
# [prefreeze_caps] rehearse (a test compares them). The calibrated read layer is read from <run-dir>/calibration.json. The frozen data files are in <run-dir>/data/bundle.
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
exec uv run --locked python -m studies.p10s2.stages rehearse --run-dir "$RUN_DIR" --code-commit "$CODE_COMMIT" --stage-cap-seconds 11520 --data-dir "$RUN_DIR/data/bundle" --updates 200 --full-updates 2000
