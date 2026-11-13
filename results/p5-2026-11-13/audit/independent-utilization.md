# Independent P5 utilization recount

Run from the repository root with Python 3:

```sh
python3 results/p5-2026-11-13/audit/independent-utilization.py > /tmp/p5-utilization.json
cmp /tmp/p5-utilization.json results/p5-2026-11-13/audit/independent-utilization.json
sha256sum -c results/p5-2026-11-13/audit/independent-utilization.sha256
```

The standard-library script uses only compact result and metric records. It
reconstructs 162 initial and final utilization records across all 81 memory
cells, using absolute tolerance `1e-12` for entropy-based and other
floating-point recomputations. It verifies exact initial utilization equality
for each fixed/learned pair and checks all 512 recorded gradient norms in
every learned-router cell. The published output retains each cell and
per-variant means, sample standard deviations, minima and maxima.

Per-query router entropy cannot be derived from aggregate branch counts;
the summary uses the recorded mean. Router movement is read from the
saved scalar and is not a binary-state audit. These are descriptive
measurements and add no scientific gate.

Ruff format and check passed. The first pass, which checked saved gradient
counts only, passed and is retained locally as
`experiments/review/p5-utilization-attempt-01.{stdout,stderr}`. The second
pass added verification from the raw per-step gradient and gate logs; it
also passed with empty stderr and is the published output. No model or
training code was imported or run.
