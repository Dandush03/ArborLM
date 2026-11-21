#!/bin/sh
# P10IS2 Part Q: the PRE-FREEZE check of the R-gloss-icl prompt texts (ADR-0025 addendum, attempt 3): tokenization test (a) over the prompts of every E_A, E_B and D_cal item with placeholder glosses and a sweep of
# every reference word type as a gloss word. It reads no teacher output and opens nothing sealed; it recomputes the registered partition (a pure function of the corpus and the registered seeds) and writes only its
# record, once. It needs the tokenizer and the corpus, so the 28 packages go on the path ONLY from the verified durable copy, absolute path, offline, never through uv's cache. Usage: <out.json>
set -eu
export PYTHONDONTWRITEBYTECODE=1  # the durable package copy is hashed into the plan: nothing may write .pyc files into it
export UV_OFFLINE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=6 MKL_NUM_THREADS=6 VECLIB_MAXIMUM_THREADS=6
if [ "$#" -ne 1 ]; then
    echo "usage: $0 <out.json (absolute path, outside the repository)>" >&2
    exit 2
fi
case "$1" in
    /*) OUT=$1 ;;
    *) OUT=$PWD/$1 ;;
esac
DURABLE_PACKAGES=/Users/daniellaloush/dandush03/ArborLM/data/datagen-packages
cd "$(dirname "$0")/../../.."
PYTHONPATH="$DURABLE_PACKAGES" exec uv run --locked --offline --extra pilot python -m studies.p10is2.partq.stages prompt-check --out "$OUT"
