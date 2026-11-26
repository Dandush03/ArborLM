| lineage | cluster | key mismatches / n | no unique answer | largest pooled excess (rule, level) | verdict 0.15 | levels: identical pairs; stated parameter max rising | as written, text key (own part / smaller part) | as written, audit-4 key (own part / smaller part) | per-cluster builder (hypothetical), G=8 text / a4key |
|---|---|---|---|---|---|---|---|---|---|
| `ages` | S1_linear_solve | 0 / 10,500 | 0 / 10,500 | +0.022 (a4:sum_over_k_plus_1, L6) | STAYS | none; yes | pass / pass | L0,1,2 / L0,1,2 | equal_share L0,1,2 / equal_share L0,1,2 |
| `arithmetic_series` | S7_step_rule | 0 / 10,500 | 0 / 10,500 | -0.003 (a3:last_day_only, L0) | STAYS | none; yes | pass / pass | pass / pass | pass / pass |
| `average_missing` (r4) | S1_linear_solve | 0 / 10,500 | 0 / 10,500 | +0.008 (a3:target_mean_rounded, L0) | STAYS | none; yes | pass / pass | pass / pass | equal_share L0,1,2 / equal_share L0,1,2 |
| `change_ways` | S5_unbounded_table | 0 / 10,500 | 0 / 10,500 | -0.036 (a4:T_over_min_coin, L0) | STAYS | none; see note | pass / pass | pass / pass | pass / pass |
| `clock_duration` (r4) | clock_duration | 0 / 10,500 | 0 / 10,500 | -0.015 (a3:span_incl_waits, L0) | STAYS | none; yes | pass / pass | pass / pass | pass / pass |
| `consecutive` | S1_linear_solve | 0 / 10,500 | 0 / 10,500 | +0.000 (echo_best_position, L0) | STAYS | none; yes | L0,1 / L0,1 | L0,1 / L0,1 | equal_share L0,1,2 / equal_share L0,1,2 |
| `crt_congruence` | crt_congruence | 0 / 10,500 | 0 / 10,500 | +0.054 (a3:largest_mod_remainder, L0) | STAYS | none; see note | pass / pass | pass / pass | pass / pass |
| `division_counting` | division_counting | 0 / 10,500 | 0 / 10,500 | -0.066 (echo_best_position, L0) | STAYS | none; yes | pass / pass | pass / pass | pass / pass |
| `finite_differences` (r4) | finite_differences | 0 / 10,500 | 0 / 10,500 | -0.002 (a4:echo_pos, L0) | STAYS | none; yes | pass / pass | pass / pass | pass / pass |
| `fraction_remainder` | S3_multiplicative_chain | 0 / 10,500 | 0 / 10,500 | +0.017 (a4:spends_not_left, L6) | STAYS | none; yes | pass / pass | L0,1,2,3,4,5,6 / L0,1,2,3,4,5,6 | pass / equal_share L0,1 |
| `gcd_lcm` (r4) | gcd_lcm | 0 / 10,500 | 0 / 10,500 | -0.022 (a4:smallest_pairwise_gcd, L5) | STAYS | none; yes | pass / pass | pass / pass | pass / pass |
| `grid_perimeter` | S6_exposed_faces | 0 / 10,500 | 0 / 10,500 | -0.087 (a3:bbox, L2) | STAYS | none; yes | pass / pass | L0 / L0 | pass / pass |
| `inclusion_exclusion` | inclusion_exclusion | 0 / 10,500 | 0 / 10,500 | -0.036 (a3:any_ignore_overlap, L0) | STAYS | none; yes | pass / pass | pass / pass | pass / pass |
| `last_digit_power` | last_digit_power | 0 / 10,500 | 0 / 10,500 | +0.086 (a3:exp_mod_p, L0) | STAYS | none; yes | pass / pass | pass / pass | pass / pass |
| `linear_equation` | S1_linear_solve | 0 / 10,500 | 0 / 10,500 | -0.016 (a3:ignore_constant, L0) | STAYS | none; yes | pass / pass | pass / pass | equal_share L0,1,2 / equal_share L0,1,2 |
| `median_list` | median_list | 0 / 10,500 | 0 / 10,500 | +0.082 (im:mode_value, L0) | STAYS | none; yes | pass / pass | pass / pass | pass / pass |
| `mixture` (r4) | S2_weighted_sum | 0 / 10,500 | 0 / 10,500 | +0.033 (a3:unweighted_mean, L4) | STAYS | none; yes | pass / pass | pass / pass | pass / pass |
| `painted_cube` | S6_exposed_faces | 0 / 10,500 | 0 / 10,500 | -0.007 (a3:inner_block_on_unpainted_bottom, L3) | STAYS | none; yes | pass / pass | pass / pass | pass / pass |
| `percent_change` | S3_multiplicative_chain | 0 / 10,500 | 0 / 10,500 | +0.006 (a3:first_step_only, L5) | STAYS | none; yes | L0,1 / L0,1 | L0,1,3 / L0,1,3,4 | pass / equal_share L0,1 |
| `pipes_work` | S1_linear_solve | 0 / 10,500 | 0 / 10,500 | -0.028 (im:ignore_drain, L0) | STAYS | none; yes | pass / pass | L0,1,2 / L0,1,2 | equal_share L0,1,2 / equal_share L0,1,2 |
| `prime_factors` | prime_factors | 0 / 10,500 | 0 / 10,500 | -0.077 (im:omega_plus_one, L0) | STAYS | none; yes | pass / pass | pass / pass | pass / chao1 L0 |
| `quadratic_area` | quadratic_area | 0 / 10,500 | 0 / 10,500 | -0.007 (a3:quarter_perimeter, L3) | STAYS | none; yes | pass / pass | pass / pass | pass / pass |
| `ratio_share` | S3_multiplicative_chain | 0 / 10,500 | 0 / 10,500 | +0.057 (a3:equal_split, L0) | STAYS | none; yes | pass / pass | L0 / L0 | pass / equal_share L0,1 |
| `rectangle` | S1_linear_solve | 0 / 10,500 | 0 / 10,500 | +0.014 (a4:echo_pos_offset, L0) | STAYS | none; yes | L0,1,2,3,4,5,6 / L0,1,2,3,4,5,6 | L0,1,2,3,4,5,6 / L0,1,2,3,4,5,6 | equal_share L0,1,2 / equal_share L0,1,2 |
| `recurrence_iterate` | S7_step_rule | 0 / 10,500 | 0 / 10,500 | +0.006 (a4:echo_pos_offset, L0) | STAYS | none; yes | pass / pass | pass / pass | pass / pass |
| `shopping` | S2_weighted_sum | 0 / 10,500 | 0 / 10,500 | +0.028 (a3:ignore_counts, L0) | STAYS | none; see note | pass / pass | pass / pass | pass / pass |
| `speed_distance` | S2_weighted_sum | 0 / 10,500 | 0 / 10,500 | +0.034 (a4:median_speed, L2) | STAYS | none; see note | pass / pass | pass / pass | pass / pass |
| `tiered_pricing` | tiered_pricing | 0 / 10,500 | 0 / 10,500 | -0.005 (a3:all_at_first_rate, L3) | STAYS | none; yes | pass / pass | pass / pass | pass / pass |
| `tip_split` | S3_multiplicative_chain | 0 / 10,500 | 0 / 10,500 | -0.001 (a4:tip_only_per_person, L0) | STAYS | none; yes | pass / L0 | pass / L0 | pass / equal_share L0,1 |
