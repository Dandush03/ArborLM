#!/bin/sh
# P10IS3 rehearsal launcher (ADR-0026 sections 5.3 and 8). Usage: rehearse.sh <r1|r2|r3|synthetic> <run-dir> [options of `stages rehearse`]
# Rehearsals are not registered stages: they never run a trained addition on the registered panel (the BASE gates alone read it), they print no loss value, and they write only under <run-dir> (ignored by
# version control or outside the repository) and, for r1, the sealed archive at --sealed-path (outside the repository). Every expansion is quoted; no loop, no sleep.
set -eu
if [ "$#" -lt 2 ]; then
    echo "usage: $0 <r1|r2|r3|synthetic> <run-dir> [options]" >&2
    exit 2
fi
PHASE=$1
case "$2" in
    /*) RUN_DIR=$2 ;;
    *) RUN_DIR=$PWD/$2 ;;
esac
shift 2
cd "$(dirname "$0")/../../.."
exec uv run --locked python -m studies.p10i_s3.stages rehearse "$PHASE" --run-dir "$RUN_DIR" "$@"
