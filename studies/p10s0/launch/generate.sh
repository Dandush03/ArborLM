#!/bin/sh
# P10S0 registered generation (ADR-0020 section 13 step 8: fixed launch script). Run BEFORE the freeze commit, as in P9-I and P9-II: generating a draw and checking it with G1 is not an
# observation of a registered seed by a model. NOT RUN by the implementer: step 8 waits for the human lead's recorded acceptance of the P9-II outcome (ADR-0020 sections 11 and 18).
# Takes exactly two arguments, the run directory and the commit the generating code is at (it must equal HEAD, with a clean tree, so the identity written into every data manifest is the
# code that will be frozen). Generates and G1-checks the thirteen registered draws and the two reserve draws (each holding all three fact sets), then writes the draw plan (the reserve
# substitution of ADR-0019 section 9). A draw that fails G1 keeps its failed record and the next draw is still generated.
# Every call passes --generation-cap-from-config: the driver takes the stage cap from the config's [generation] block (2 x the rehearsal draw's measured generation time, floor 60 s per draw; set by the
# rehearsal before the freeze) and refuses a typed cap, a provisional cap, a missing run decision (results/p10s0-freeze-*/DECISION.md) and a tree without the recorded acceptance of the P9-II outcome.
set -eu
if [ "$#" -ne 2 ]; then
    echo "usage: $0 <run-dir> <code-commit>" >&2
    exit 2
fi
case "$1" in
    /*) RUN_DIR=$1 ;;
    *) RUN_DIR=$PWD/$1 ;;
esac
CODE_COMMIT=$2
cd "$(dirname "$0")/../../.."
if [ "$(git rev-parse HEAD)" != "$(git rev-parse --verify "$CODE_COMMIT^{commit}")" ]; then
    echo "refused: HEAD is not $CODE_COMMIT" >&2
    exit 2
fi
if [ -n "$(git status --porcelain --untracked-files=all)" ]; then
    echo "refused: the working tree is not clean" >&2
    exit 2
fi
for k in 1 2 3 4 5 6 7 8 9 10 11 12 13; do
    uv run --locked python -m studies.p10s0.stages generate --mode registered --draw "$k" --run-dir "$RUN_DIR" --generation-cap-from-config --i-understand-freeze-time || echo "draw $k: generation or G1 failed; the record is kept and the draw plan decides" >&2
done
for r in 1 2; do
    uv run --locked python -m studies.p10s0.stages generate --mode registered --reserve "$r" --run-dir "$RUN_DIR" --generation-cap-from-config --i-understand-freeze-time || echo "reserve $r: generation or G1 failed; the record is kept and the draw plan decides" >&2
done
exec uv run --locked python -m studies.p10s0.stages draw-plan --run-dir "$RUN_DIR"
