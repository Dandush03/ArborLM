# Corrections to README.md (found by the Opus 5.5 results audit, 2026-11-15)

`README.md` is kept as first written. Two statements in it are corrected here:

1. "Peak worker memory 0.75 GiB" is wrong. The largest peaks are 0.702 GiB in training and 0.881 GiB in evaluation, both under the 3 GiB per-worker limit.
2. "H1 0.888 against 0.888" (A1, 16,384 slots, draw 11, seed 1) hides a miss: the cell is below the line by half a fact.

The audited statement of the outcome is `OUTCOME.md`.
