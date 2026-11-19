#!/bin/sh
# P10IS6 stage D0, data preparation (ADR-0031 section 16): single process, RSS guard 8 GiB; reads the pinned parquet files, writes the chunk table, panels and the D0 manifest; appends the two new panels to the shared panel ledger.
# python -I: no user site, no current directory, no PYTHONPATH (downloaded files are untrusted input). Run from any directory that is NOT the data directory.
set -eu
cd "$(dirname "$0")/../../.."
exec uv run --locked python -I studies/p10i_s6/launch/isolated.py studies.p10i_s6.d0 "$@"
