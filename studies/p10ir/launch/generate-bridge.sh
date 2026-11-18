#!/bin/sh
# P10IR: the five bridge draws' manifests (ADR-0029 section 5 and 10), before the freeze. Generating a draw is not an observation of a seed by a model.
set -eu
if [ "$#" -ne 1 ]; then
    echo "usage: $0 <run-dir>" >&2
    exit 2
fi
case "$1" in
    /*) RUN_DIR=$1 ;;
    *) RUN_DIR=$PWD/$1 ;;
esac
cd "$(dirname "$0")/../../.."
exec uv run --locked python -m studies.p10ir.stages generate-bridge --run-dir "$RUN_DIR"
