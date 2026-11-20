#!/bin/sh
# P10IS3 data preparation (ADR-0026 section 4): `prepare-data` and `window-spans` read the pinned WikiText-2 parquet, which needs pyarrow from the lock's `pilot` extra, so both run with `--extra pilot`.
# Usage: prepare-data.sh <prepare-data|window-spans> [options of that command]   (e.g. window-spans --source <wikitext2 dir> --bundle <P10-S2 bundle dir> --out <file> --ledger-absent)
# Reads recorded text and recorded windows only: it trains nothing and reads no result. Every expansion is quoted; no loop, no sleep.
set -eu
if [ "$#" -lt 1 ]; then
    echo "usage: $0 <prepare-data|window-spans> [options]" >&2
    exit 2
fi
CMD=$1
shift
cd "$(dirname "$0")/../../.."
exec uv run --locked --extra pilot python -m studies.p10i_s3.stages "$CMD" "$@"
