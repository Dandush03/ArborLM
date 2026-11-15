#!/bin/sh
# P10S1 registered generation (ADR-0021 section 8.1 and 11: fixed launch script). Run BEFORE the freeze commit: generating a draw and checking it with G1 is not an observation of
# a registered seed by a model. Takes exactly two arguments, the run directory and the commit the generating code is at (it must equal HEAD, with a clean tree, so that the
# identity written into every data manifest is the code that will be frozen). Generates and G1-checks the five registered draws p10s1-draw-1 .. p10s1-draw-5, each with its own
# stage cap, read from [generation] of the config (set by `stages set-generation-cap` from twice the G1 time measured on the rehearsal draw and committed before this script is run; the
# driver refuses while the cap is still provisional, and takes no cap from the command line). A draw that fails G1 keeps its failed
# record, the other draws are still generated, and the script exits 1: there are no reserve draws (a failed engineering gate stops the run before training).
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
STATUS=0
for k in 1 2 3 4 5; do
    uv run --locked python -m studies.p10s1.stages generate --mode registered --draw "$k" --run-dir "$RUN_DIR" --i-understand-freeze-time || { echo "draw $k: generation or G1 failed; the record is kept" >&2; STATUS=1; }
done
exit "$STATUS"
