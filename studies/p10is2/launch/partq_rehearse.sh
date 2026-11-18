#!/bin/sh
# P10IS2 Part Q rehearsal (ADR-0025 section 10): "measuring" (steps 1 to 8, one generation block per capability and one Q_check block, fixed cap 3.0 charged hours, cannot be frozen on) or
# "counting" (the candidate plan file itself, two generation blocks per capability and one Q_check block, one forced pause and resume, one forced PAUSED - IDENTITY and restore).
# Uses the real teachers, so the 28 packages go on the path of this process ONLY from the verified durable copy, by absolute path, offline, never through uv's cache. Values of Q1-Q4 and every per-item
# score go to <run-dir>/sealed and are not displayed. Not run by the implementation.
set -eu
export PYTHONDONTWRITEBYTECODE=1  # the durable package copy is hashed into the plan: nothing may write .pyc files into it
export UV_OFFLINE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=6 MKL_NUM_THREADS=6 VECLIB_MAXIMUM_THREADS=6
if [ "$#" -ne 2 ]; then
    echo "usage: $0 <measuring|counting> <run-dir>" >&2
    exit 2
fi
KIND=$1
case "$KIND" in
    measuring|counting) ;;
    *)
        echo "unknown kind: $KIND" >&2
        exit 2
        ;;
esac
case "$2" in
    /*) RUN_DIR=$2 ;;
    *) RUN_DIR=$PWD/$2 ;;
esac
DURABLE_PACKAGES=/Users/daniellaloush/dandush03/ArborLM/data/datagen-packages
cd "$(dirname "$0")/../../.."
PYTHONPATH="$DURABLE_PACKAGES" exec uv run --locked --offline --extra pilot python -m studies.p10is2.partq.stages rehearse --kind "$KIND" --run-dir "$RUN_DIR"
