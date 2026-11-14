# P8 figures

Study status: INCOMPLETE: 55 of 60 cells; 55 of 60 with complete evaluation and simulation records; 60 of 60 with training records. Astra review: NOT_PERFORMED. Simulated misses are not physical I/O.

- `fig01_scorecard.png`: Ten-case table of final NLL, change in NLL against baseline, M-ratio, E-ratio, utilization-adjusted E-ratio, U-ratio and class, per panel (L-COAX, R=2 hypothetical rows/page, C=32 pages, ascending tie rule).
- `fig02_quality_vs_locality.png`: Mean final NLL against mean simulated value-page misses (m) and against E under L-COAX at the primary setting, per panel, with cell points, case means, the lower-left Pareto set of case means and the baseline + 0.005 nats/byte lines.
- `fig03_utilization.png`: Entropy-effective slots, distinct slots, share of selections on the 64 most-selected slots and mean distinct slots per 64-query context, per case and panel.
- `fig04_null_vs_actual.png`: Mean simulated misses of the actual trace under L-FREQ and L-COAX and of the count-preserving null under L-FREQ, per case, panel and cache setting, with the tie-rule range as whiskers.
- `fig05_flat_vs_tree_pairs.png`: Per (parent, seed) pair values of m under L-COAX, E under L-COAX and final NLL for C03 vs C01, C02 vs C01, C05 vs C04, C07 vs C06 and C09 vs C08, both panels.
- `fig06_temporal_branch.png`: Temporal reuse of the actual trace and of the count-preserving null per case, and branch persistence of the actual and order-shuffled trace for tree cases, per panel.
- `fig07_heatmaps.png`: Per (parent, seed) pair m ratio, E ratio (both under L-COAX) and change in NLL against baseline for the seven regularized cases, per panel.
- `fig08_training_resources.png`: Per-case wall seconds and peak RSS of the training cells and training curves (loss, regularizer values, lambda, 8th-9th score gap, pi mass outside the top 8, parameter-change norms).
- `fig09_layout_controls.png`: Mean L-PCOAX over L-COAX, L-BCOAX over L-COAX (trees) and L-ID over L-COAX simulated misses per case and panel at both cache settings.
