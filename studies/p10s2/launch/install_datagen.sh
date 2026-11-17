#!/bin/sh
# P10S2 pre-freeze step "install_datagen" (ADR-0022 section 14.2; the lead's ruling R2 and the confirmation's F1): installs the data-generation packages ONCE, with hashes required, into the git-ignored
# data/datagen-packages (see studies/p10s2/install_datagen.py: the requirements file is checked from the locked environment first, a download-ledger row is written before and completed after, the installed
# versions are asserted). It needs the network (PyPI wheels, within the standing 30 GB permission). It is run by the lead BEFORE datagen.sh; afterwards the lead commits the download-ledger change
# (docs/reviews/p10-design-2026-11-15/DOWNLOAD_LEDGER.md), because datagen.sh refuses a dirty tree and checks that the committed ledger holds the completed row.
# Takes exactly the code commit (which must equal a clean HEAD). No word splitting: every expansion is quoted.
set -eu
if [ "$#" -ne 1 ]; then
    echo "usage: $0 <code-commit>" >&2
    exit 2
fi
CODE_COMMIT=$1
cd "$(dirname "$0")/../../.."
exec uv run --locked --extra pilot python -m studies.p10s2.install_datagen --code-commit "$CODE_COMMIT"
