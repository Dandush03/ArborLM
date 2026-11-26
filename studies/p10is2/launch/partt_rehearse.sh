#!/bin/sh
# P10IS2 Part T rehearsals (ADR-0025 section 10; audit B1, B4): "measuring" (every stage of the registered order against a plan built from the config with the caps unset; it records the per-kind rates,
# the per-process overhead, the peak memory, the disk and the load; cannot be frozen on) or "counting" (the candidate plan file itself, one forced pause and resume, one forced PAUSED - IDENTITY and restore).
# Both drive studies/p10is2/launch/partt_registered.sh <stage> <run-dir> - --rehearsal ... for each stage in a FRESH process: the same launch script, entry point, task runner and workers as the registered run.
# Training runs on MPS and scoring on CPU; the rehearsal trains on its own draw (seed 252002) and scores D_cal only. Part T uses the lock ALONE. Run only when the lead has said so: it takes hours on the real data.
set -eu
if [ "$#" -lt 2 ]; then
    echo "usage: $0 <measuring|counting> <run-dir> --part-q-dir <dir> [--calibration <calibration_<n>.json>] [--part-q-plan <file>] [--manifests <json>] [--charged-ledger <file>]..." >&2
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
shift 2  # what remains (--part-q-dir, --calibration, --charged-ledger ...) goes to the command
cd "$(dirname "$0")/../../.."
unset PYTHONPATH
export OMP_NUM_THREADS=6 MKL_NUM_THREADS=6 VECLIB_MAXIMUM_THREADS=6
# keep the machine awake for exactly the life of this stage: the watcher follows THIS shell's pid, which the exec below keeps, and ends when the stage ends (caffeinate -i -w <pid>); never a bare caffeinate
if command -v caffeinate >/dev/null 2>&1; then
    caffeinate -i -w $$ >/dev/null 2>&1 &
fi
exec uv run --locked python -m studies.p10is2.partt_stages rehearse --kind "$KIND" --run-dir "$RUN_DIR" "$@"
