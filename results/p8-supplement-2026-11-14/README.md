# P8 supplement (ADR-0016) — not the registered P8 output

Simulation records for the five fully collapsed P8 cells, produced once on 2026-11-14 under [ADR-0016](../../docs/decisions/ADR-0016-p8-supplement-collapsed-cell-simulations.md) with a human-approved exception to ADR-0015 §11. The registered P8 study in `results/p8-2026-11-14/` is unchanged and remains INCOMPLETE with decision `none`.

- `preflight/` — gate checks before the freeze (run 1 superseded by run 2).
- `simulate/` — the single run's manifest and per-cell records (layout binaries stay in the git-ignored run directory).
- `analysis/` — the labelled supplementary analysis; start with `SUPPLEMENTARY_ANALYSIS.md`.
- `logs/` — stage and analysis console output.

Outcome: 5 of 5 cells completed; all nine predictions written before the run hold; supplementary classes of C04 and C05 are QUALITY-FAILED on both panels. Independent recomputation: `docs/reviews/p8-supplement-results-audit-2026-11-14/RESULTS_AUDIT.md`. Astra review: NOT_PERFORMED.
