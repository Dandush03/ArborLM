#!/bin/sh
# P10S2 pre-freeze stage "datagen" (ADR-0022 sections 14.2, 16): the data-generation step, once, before the freeze. It is the only place where packages outside the lock are used and it needs the
# human lead's recorded confirmation of the package wheels with sizes (nothing is fetched or installed by this script alone).
# The packages are installed ONCE by launch/install_datagen.sh (run by the lead before this script; the lead then commits the download ledger); this script only VERIFIES the completed install (versions, no shadowing, the committed ledger row for this requirements file) so it can be re-run after an engineering stop. The install is studies.p10s2.install_datagen (requirements checked from the locked environment first, uv pip install --require-hashes --target data/datagen-packages, a download-ledger row
# before and after, installed versions asserted) and that directory is on the path of the datagen process ONLY (re-check A, R2). The requirements file is never an argument of uv run.
# Takes exactly the run directory and the code commit (which must equal a clean HEAD; the driver refuses otherwise). The stage cap is passed here and equals configs/p10s2_transfer.toml
# [prefreeze_caps] datagen (a test compares them). The downloads are in <run-dir>/downloads.
# No word splitting: every expansion is quoted and no argument is ever re-parsed by the shell.
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
uv run --locked --extra pilot python -m studies.p10s2.install_datagen --verify --code-commit "$CODE_COMMIT"
PYTHONPATH="$PWD/data/datagen-packages" exec uv run --locked --extra pilot python -m studies.p10s2.datagen --downloads "$RUN_DIR/downloads" --out "$RUN_DIR/data" --code-commit "$CODE_COMMIT" --stage-cap-seconds 6480
