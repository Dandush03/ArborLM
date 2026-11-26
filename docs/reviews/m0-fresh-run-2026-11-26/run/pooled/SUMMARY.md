# Pooling of the fresh run: summary (generated from the JSON files beside it)

Seed set: run (seeds 1, 2, 3). Pooled rows: 33545. Bound: 0.15, two-sided, on the point estimate plus the rounding uncertainty (point 7).

## Lineages before and after, per evaluation

| evaluation | before | dropped | after |
|---|---|---|---|
| R1 | 10 | 4 | 6 |
| R2 | 17 | 1 | 16 |
| M1 | 29 | 5 | 24 |
| C1 | 26 | 5 | 21 |

## Lineages dropped (rule, unit, level, figure of the row with the largest |excess| + uncertainty)

- C1.circle_elimination_r2: rule `EFF_F`, unit C1c, level 0, shape None, reading rate, excess 0.281666666667 (169/600), uncertainty 0.000500000000; 14 row(s) over the bound.
- C1.cond_chain_f3: rule `EFF_F`, unit C1c, level 0, shape None, reading rate, excess 0.237333333333 (89/375), uncertainty 0.000500000000; 4 row(s) over the bound.
- C1.func_branch_f4: rule `EFF_F`, unit C1a, level 2, shape None, reading rate, excess 0.678000000000 (339/500), uncertainty 0.000500000000; 24 row(s) over the bound.
- C1.shared_lists_f3: rule `EFF_F`, unit C1a, level 6, shape None, reading rate, excess 0.153000000000 (153/1000), uncertainty 0.000500000000; 2 row(s) over the bound.
- C1.union_find_links_f3: rule `EFF_F`, unit C1c, level 0, shape None, reading rate, excess 0.313333333333 (47/150), uncertainty 0.000500000000; 4 row(s) over the bound.
- M1.division_counting_r3: rule `a3:k_minus_remainder_ignores_exact_fit`, unit M1a, level 3, shape None, reading vs_chance, excess 0.495000000000 (99/200), uncertainty 0.000050000000; 42 row(s) over the bound.
- M1.grid_perimeter_r3: rule `im:bbox_plus_4`, unit M1a, level 0, shape None, reading vs_chance, excess 0.165066666667 (619/3750), uncertainty 0.000050000000; 8 row(s) over the bound.
- M1.last_digit_power_r3: rule `a3:fermat_misapplied_e_mod_p_plus_1`, unit M1a, level 0, shape None, reading vs_chance, excess 0.198566666667 (5957/30000), uncertainty 0.000050000000; 13 row(s) over the bound.
- M1.prime_factors_r3: rule `a3:largest_le_sqrt`, unit M1c, level 5, shape None, reading vs_chance, excess 0.248833333333 (1493/6000), uncertainty 0.000005000000; 39 row(s) over the bound.
- M1.ratio_share_r3: rule `new:ratio_first_named`, unit M1c, level 1, shape None, reading vs_chance, excess 0.535916666667 (6431/12000), uncertainty 0.000005000000; 56 row(s) over the bound.
- R1.equivalence_exchange_rates_r6: rule `a4:direction_ignored_q_over_p`, unit R1a, level 0, shape None, reading eff, excess 1.000000000000 (1/1), uncertainty 0.000050000000; 14 row(s) over the bound.
- R1.spatial_grid_walk_r5: rule `constant_mfk_fitted`, unit R1a, level 1, shape None, reading eff, excess -0.164633333333 (-4939/30000), uncertainty 0.000050000000; 8 row(s) over the bound.
- R1.swap_tracking_r5: rule `constant_mfk_fitted`, unit R1a, level 0, shape None, reading eff, excess -0.161100000000 (-1611/10000), uncertainty 0.000050000000; 8 row(s) over the bound.
- R1.venn_counting_r5: rule `a3:ignore_triples`, unit R1a, level 0, shape None, reading eff, excess 1.000000000000 (1/1), uncertainty 0.000050000000; 20 row(s) over the bound.
- R2.list_ops: rule `[NEW] (artifact) final list = start list with adds appended and removals applied, all moves and reverses ignored`, unit R2b, level 0, shape None, reading k_over_n, excess 0.399750000000 (1599/4000), uncertainty 0.000000000000; 3 row(s) over the bound.

## Counts for the report (the lists are in report_extras.json)

- exact R1 rows: 2
- uncounted rule groups: 343
- a3 wrapper fallbacks: 6
- groups of rows with an item count other than the plan's: 12
- s5 recovery alternatives that would change a decision: 0
