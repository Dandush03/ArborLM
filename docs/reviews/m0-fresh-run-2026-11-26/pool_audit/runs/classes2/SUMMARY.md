# Pooling of the fresh run: summary (generated from the JSON files beside it)

Seed set: run (seeds 1, 2, 3). Pooled rows: 5683. Bound: 0.15, two-sided, on the point estimate plus the rounding uncertainty (point 7).

## Lineages before and after, per evaluation

| evaluation | before | dropped | after |
|---|---|---|---|
| R1 | 14 | 9 | 5 |
| R2 | 15 | 10 | 5 |
| M1 | 7 | 5 | 2 |
| C1 | 19 | 11 | 8 |

## Lineages dropped (rule, unit, level, figure of the row with the largest |excess| + uncertainty)

- C1.c_a3above: rule `S.foo`, unit C1a, level 3, shape None, reading rate, excess 0.158333333333 (19/120), uncertainty 0.000000000000; 1 row(s) over the bound.
- C1.c_a3fb: rule `S.foo`, unit C1a, level 3, shape None, reading rate, excess 0.600000000000 (3/5), uncertainty 0.000000000000; 1 row(s) over the bound.
- C1.c_closed: rule `M.no_back`, unit C1c, level 5, shape None, reading rate, excess 0.500000000000 (1/2), uncertainty 0.000050000000; 1 row(s) over the bound.
- C1.c_mnot: rule `M.not_entry`, unit C1a, level 2, shape None, reading rate, excess 0.400000000000 (2/5), uncertainty 0.000500000000; 1 row(s) over the bound.
- C1.c_msh: rule `MF_shape_cv`, unit C1b, level 4, shape None, reading rate, excess 0.150000000000 (3/20), uncertainty 0.000500000000; 1 row(s) over the bound.
- C1.c_printform: rule `MF_printform_cv`, unit C1a, level 3, shape None, reading rate, excess 0.200000000000 (1/5), uncertainty 0.000500000000; 1 row(s) over the bound.
- C1.c_s5edge: rule `S.foo`, unit C1a, level 2, shape None, reading rate, excess 0.150000000000 (3/20), uncertainty 0.000500000000; 1 row(s) over the bound.
- C1.c_s5rec: rule `S.foo`, unit C1a, level 2, shape None, reading rate, excess 0.175000000000 (7/40), uncertainty 0.000500000000; 1 row(s) over the bound.
- C1.c_srcs: rule `S.no_back`, unit C1b, level 4, shape None, reading rate, excess 0.600000000000 (3/5), uncertainty 0.000000000000; 1 row(s) over the bound.
- C1.c_srcs3: rule `C.self_check`, unit C1a, level 3, shape None, reading rate, excess 0.600000000000 (3/5), uncertainty 0.000000000000; 1 row(s) over the bound.
- C1.slices_f4: rule `EFF_F`, unit C1a, level 2, shape None, reading rate, excess 0.200000000000 (1/5), uncertainty 0.000500000000; 1 row(s) over the bound.
- M1.base_r3: rule `base_r`, unit M1c, level 6, shape None, reading vs_base, excess -0.200000000000 (-1/5), uncertainty 0.000010000000; 2 row(s) over the bound.
- M1.gamma_r3: rule `im:largest_share`, unit M1a, level 2, shape None, reading vs_chance, excess 0.900000000000 (9/10), uncertainty 0.000050000000; 2 row(s) over the bound.
- M1.prime_factors_r3: rule `a3:largest_le_sqrt`, unit M1a, level 2, shape None, reading vs_chance, excess 0.900000000000 (9/10), uncertainty 0.000050000000; 2 row(s) over the bound.
- M1.vsbase_r3: rule `im:base_r`, unit M1a, level 3, shape None, reading vs_base, excess -0.149933333333 (-2249/15000), uncertainty 0.000100000000; 2 row(s) over the bound.
- M1.vschance_r3: rule `new:foo`, unit M1b, level 1, shape None, reading vs_chance, excess 0.160000000000 (4/25), uncertainty 0.000005000000; 1 row(s) over the bound.
- R1.beta_r5: rule `my_rule`, unit R1a, level 3, shape None, reading eff, excess 0.300000000000 (3/10), uncertainty 0.000050000000; 1 row(s) over the bound.
- R1.delta: rule `im:abstain_as_no`, unit R1b, level 2, shape None, reading eff, excess 0.400000000000 (2/5), uncertainty 0.000050000000; 1 row(s) over the bound.
- R1.eps_r4: rule `exact_x`, unit R1a, level 0, shape None, reading eff, excess 0.500000000000 (1/2), uncertainty 0.000050000000; 7 row(s) over the bound.
- R1.eta_r4: rule `e_neg`, unit R1a, level 5, shape None, reading eff, excess -0.150100000000 (-1501/10000), uncertainty 0.000050000000; 1 row(s) over the bound.
- R1.gamma_r6: rule `ccw_as_cw`, unit R1b, level 2, shape None, reading eff, excess 0.400000000000 (2/5), uncertainty 0.000050000000; 1 row(s) over the bound.
- R1.kappa_r4: rule `abstain_as_no`, unit R1c, level 0, shape None, reading eff, excess 0.200000000000 (1/5), uncertainty 0.000550000000; 1 row(s) over the bound.
- R1.mu_r4: rule `mu_r`, unit R1c, level 4, shape None, reading eff, excess 0.150000000000 (3/20), uncertainty 0.000550000000; 1 row(s) over the bound.
- R1.nu_r4: rule `nu_anti`, unit R1a, level 6, shape None, reading anti, excess 0.200000000000 (1/5), uncertainty 0.000050000000; 1 row(s) over the bound.
- R1.zeta_r4: rule `z_rule`, unit R1a, level 1, shape None, reading eff, excess 0.150000000000 (3/20), uncertainty 0.000050000000; 1 row(s) over the bound.
- R2.b_open: rule `[impl] x`, unit R2a, level 2, shape None, reading k_over_n, excess 0.158333333333 (19/120), uncertainty 0.000000000000; 1 row(s) over the bound.
- R2.count_divisible: rule `[NEW] (partial) largest modulus: try r, r+m, r+2m against the other congruences, else r`, unit R2b, level 4, shape None, reading k_over_n, excess 1.000000000000 (1/1), uncertainty 0.000000000000; 1 row(s) over the bound.
- R2.crt_smallest: rule `[NEW] (P) misread: each distinct value counted once (the wording now excludes it)`, unit R2b, level 3, shape None, reading k_over_n, excess 1.000000000000 (1/1), uncertainty 0.000000000000; 1 row(s) over the bound.
- R2.d_yn: rule `[mine] yn lo2`, unit R2a, level 2, shape None, reading k_over_napp, excess -0.158333333333 (-19/120), uncertainty 0.000000000000; 1 row(s) over the bound.
- R2.f_cond: rule `[mine] [cond] foo`, unit R2b, level 2, shape None, reading k_over_napp, excess 0.250000000000 (1/4), uncertainty 0.000000000000; 1 row(s) over the bound.
- R2.h_sd: rule `[a3] removal by deleting the minimum and keeping the order of the rest`, unit R2b, level 2, shape removals=1, reading k_over_n, excess 0.200000000000 (1/5), uncertainty 0.000000000000; 1 row(s) over the bound.
- R2.i_sdsum: rule `[a3] removal by deleting the minimum and keeping the order of the rest`, unit R2b, level 2, shape -, reading k_over_n, excess 0.200000000000 (1/5), uncertainty 0.000000000000; 1 row(s) over the bound.
- R2.k_klass2: rule `[a3] only the first rule`, unit R2a, level 1, shape None, reading k_over_n, excess 1.000000000000 (1/1), uncertainty 0.000000000000; 1 row(s) over the bound.
- R2.l_construct: rule `[mine] t mod 10 applications`, unit R2a, level 1, shape None, reading k_over_n, excess 1.000000000000 (1/1), uncertainty 0.000000000000; 1 row(s) over the bound.
- R2.m_new: rule `[NEW] (P) misread: each distinct value counted once (the wording now excludes it)`, unit R2b, level 3, shape None, reading k_over_n, excess 1.000000000000 (1/1), uncertainty 0.000000000000; 2 row(s) over the bound.

## Counts for the report (the lists are in report_extras.json)

- exact R1 rows: 2
- uncounted rule groups: 65
- a3 wrapper fallbacks: 3
- groups of rows with an item count other than the plan's: 3
- s5 recovery alternatives that would change a decision: 0
