#!/bin/sh
# P10IS5 stage "r0" (ADR-0028 sections 8 and 12: fixed launch script, no free arguments).
# Decision 1: the device record (EC3, hygiene, counters, the third review's three probes; at most 64 MiB written). Runs on a shared machine. DATA_DIR must end in .noindex and lie outside every git worktree.
# No loop, no sleep, no wait here: every wait inside the driver has a deadline. No word splitting: every expansion is quoted.
set -eu
if [ "$#" -ne 2 ]; then
    echo "usage: $0 <run-dir> <data-dir>" >&2
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
cd "$(dirname "$0")/../../.."
exec uv run --locked python -m studies.p10is5.stages r0 --run-dir "$RUN_DIR" --data-dir "$DATA_DIR"
