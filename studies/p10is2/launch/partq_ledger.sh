#!/bin/sh
# P10IS2 Part Q: THE pre-freeze ledger command (ADR-0025 section 4.1): this study's 44 marker-like and 100 ordinary GEN windows into the SHARED panel ledger, once, with seed 250907 (252907 and a candidate file in the
# run directory in "rehearsal" mode). It needs the tokenizer, so the 28 packages go on the path ONLY from the verified durable copy, absolute path, offline, never through uv's cache. It refuses once a plan or a
# freeze record exists; the registered `inputs` stage only VERIFIES the ledger.
set -eu
export UV_OFFLINE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=6 MKL_NUM_THREADS=6 VECLIB_MAXIMUM_THREADS=6
if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    echo "usage: $0 <registered|rehearsal> [run-dir]" >&2
    exit 2
fi
MODE=$1
DURABLE_PACKAGES=/Users/daniellaloush/dandush03/ArborLM/data/datagen-packages
cd "$(dirname "$0")/../../.."
if [ "$#" -eq 2 ]; then
    case "$2" in
        /*) RUN_DIR=$2 ;;
        *) RUN_DIR=$PWD/$2 ;;
    esac
    PYTHONPATH="$DURABLE_PACKAGES" exec uv run --locked --offline --extra pilot python -m studies.p10is2.partq.stages ledger --mode "$MODE" --run-dir "$RUN_DIR"
fi
PYTHONPATH="$DURABLE_PACKAGES" exec uv run --locked --offline --extra pilot python -m studies.p10is2.partq.stages ledger --mode "$MODE"
