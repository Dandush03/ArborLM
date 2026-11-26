#!/bin/sh
# The one fixed launch of P10-I-S2-D0 (ADR-0035 section 8.3). Run from the repository root of the D0 worktree on a clean, committed tree.
# Output directory: new, git-ignored; the driver refuses an existing one. CPU only; 3 worker processes of 6 threads; cap 8 worker-hours.
set -eu
OUT="/Users/daniellaloush/dandush03/ArborLM/experiments/P10IS2D0-run-20261124"
exec uv run --locked --offline python -m studies.p10is2d0.driver run --out "$OUT" "$@"
