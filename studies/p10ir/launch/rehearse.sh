#!/bin/sh
# P10IR rehearsal (ADR-0029 section 13): every stage end to end against a plan of its own, on a synthetic memory and on one real-size tree cell and one flat cell of the rehearsal draw,
# and gates 1 and 2 on the registered checkpoints. Not a registered stage: it needs no freeze, and it opens no sealed value.
# Takes the new rehearsal directory and P10-S1's run directory (read only).
set -eu
if [ "$#" -ne 2 ]; then
    echo "usage: $0 <new-rehearsal-dir> <p10s1-run-dir>" >&2
    exit 2
fi
case "$1" in
    /*) RUN_DIR=$1 ;;
    *) RUN_DIR=$PWD/$1 ;;
esac
case "$2" in
    /*) S1_RUN_DIR=$2 ;;
    *) S1_RUN_DIR=$PWD/$2 ;;
esac
cd "$(dirname "$0")/../../.."
exec uv run --locked python -m studies.p10ir.stages rehearse --run-dir "$RUN_DIR" --s1-run-dir "$S1_RUN_DIR"
