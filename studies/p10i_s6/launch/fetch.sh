#!/bin/sh
# P10IS6 fetch (ADR-0031 section 6.3): `fetch.sh pin --files <names>` then `fetch.sh get --out-dir <git-ignored dir>`; the ledger of record is appended through P10-S2's own functions. The lead runs it; it uses the network.
# python -I: no user site, no current directory, no PYTHONPATH (downloaded files are untrusted input). Run from any directory that is NOT the data directory.
set -eu
cd "$(dirname "$0")/../../.."
exec uv run --locked python -I studies/p10i_s6/launch/isolated.py studies.p10i_s6.fetch "$@"
