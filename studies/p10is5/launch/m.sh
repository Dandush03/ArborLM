#!/bin/sh
# P10IS5 stage "m" (ADR-0028 sections 8 and 12: fixed launch script, no free arguments).
# Decision 1: the measuring rehearsal on the rehearsal file (provisional caps; cannot be frozen on). Runs ALONE on a quiet machine. Writes nothing but records.
# No loop, no sleep, no wait here: every wait inside the driver has a deadline. No word splitting: every expansion is quoted.
set -eu
if [ "$#" -ne 3 ]; then
    echo "usage: $0 <run-dir> <data-dir> <r1-record>" >&2
    exit 2
fi
abs() {
    case "$1" in
        /*) printf '%s\n' "$1" ;;
        *) printf '%s\n' "$PWD/$1" ;;
    esac
}
RUN_DIR=$(abs "$1")
DATA_DIR=$(abs "$2")
R1_RECORD=$(abs "$3")
cd "$(dirname "$0")/../../.."
exec caffeinate -i uv run --locked python -m studies.p10is5.stages m --run-dir "$RUN_DIR" --data-dir "$DATA_DIR" --r1-record "$R1_RECORD"
