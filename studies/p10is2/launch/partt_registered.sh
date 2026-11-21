#!/bin/sh
# P10IS2 Part T registered stage (ADR-0025 sections 10, 11, 13 item 6). Takes the stage, the run directory and the FULL freeze commit.
# The entry point refuses unless the tree is clean, the freeze commit is an ancestor of HEAD and the Part T frozen files equal their content there, the plan and freeze record exist and agree, and a COMMITTED
# Decision 2 (results/p10is2-partt-freeze-*/DECISION_2_PARTT.md) names the freeze commit. Nothing is frozen today, so it refuses today.
# Part T uses the lock ALONE: PYTHONPATH is unset here and the entry point refuses if the durable package copy is on it. Training runs on MPS, scoring and recomputation on CPU at six threads with
# deterministic algorithms (configs/p10is2_partt.toml). Charged time is the sum of each worker process's wall time. At most three workers (two while another study runs). No word splitting.
set -eu
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
cd "$(dirname "$0")/../../.."
unset PYTHONPATH
export OMP_NUM_THREADS=6 MKL_NUM_THREADS=6 VECLIB_MAXIMUM_THREADS=6  # the ADR's six threads for scoring and recomputation
exec uv run --locked python -m studies.p10is2.partt_stages work --stage "$STAGE" --run-dir "$RUN_DIR" --freeze-commit "$FREEZE_COMMIT"
