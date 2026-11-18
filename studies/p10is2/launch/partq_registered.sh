#!/bin/sh
# P10IS2 Part Q registered stage (ADR-0025 sections 10, 11, 13 item 6). Takes the stage, the run directory and the FULL freeze commit.
# The entry point refuses unless the tree is clean, the freeze commit is an ancestor of HEAD and the frozen files equal their content there, the plan and freeze record exist and agree, and a COMMITTED
# Decision 2 (results/p10is2-partq-freeze-*/DECISION_2_PARTQ.md) names the freeze commit. Nothing is frozen today, so it refuses today.
# The 28 packages outside the lock (126,182,132 bytes) are put on the path of the stages that need them ONLY from the verified durable copy, by its ABSOLUTE path, offline (--offline), and never
# through uv's cache: the requirements file is never an argument of uv run. Part T never uses them. No word splitting: every expansion is quoted.
set -eu
export UV_OFFLINE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
if [ "$#" -ne 3 ]; then
    echo "usage: $0 <stage> <run-dir> <freeze-commit>" >&2
    exit 2
fi
STAGE=$1
case "$2" in
    /*) RUN_DIR=$2 ;;
    *) RUN_DIR=$PWD/$2 ;;
esac
FREEZE_COMMIT=$3
DURABLE_PACKAGES=/Users/daniellaloush/dandush03/ArborLM/data/datagen-packages
cd "$(dirname "$0")/../../.."
case "$STAGE" in
    inputs|qfit|qcheck|generation|regeneration|outputs)
        PYTHONPATH="$DURABLE_PACKAGES" exec uv run --locked --offline --extra pilot python -m studies.p10is2.partq.stages work --stage "$STAGE" --run-dir "$RUN_DIR" --freeze-commit "$FREEZE_COMMIT"
        ;;
    partition|analysis)
        exec uv run --locked --offline --extra pilot python -m studies.p10is2.partq.stages work --stage "$STAGE" --run-dir "$RUN_DIR" --freeze-commit "$FREEZE_COMMIT"
        ;;
    *)
        echo "unknown stage: $STAGE" >&2
        exit 2
        ;;
esac
