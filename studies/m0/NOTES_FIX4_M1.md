# M1 fix round 4 (narrow repair round): notes

Implementer: arbor-implementer (Claude Sonnet 5.5). Brief: the lead's M0-M1 narrow repair round ("fix 4"), under the human lead's fifth decision (`HUMAN_LEAD_WORDS_5.md`) and rulings R-24 to R-29 (`LEAD_RULINGS_5.md`). These are the implementer's own measurements: not independent review, not Astra validation, not human approval. Nothing is registered, nothing enters `core.REGISTRY`, no model was run, nothing was downloaded. `Astra review: NOT_PERFORMED`.

Every number below is MEASURED (sampled, with the seed given) unless marked ANALYTICAL. The private sets, where a margin reads NOT EVALUABLE, are descriptive readings (R-29); nothing here is a registration.

## 1. Result in one paragraph

29 of the 36 written lineages survive, in 17 strict clusters (round 3: 33 candidates in 20 clusters). Four more lineages are dropped (NOT REGISTERED, excluded everywhere): `coins_r3` (+0.160 at level 0), `pigeonhole_worst_case_r3` (+0.287 at level 1), `mode_tally_r3` (+0.382 at level 1), all three named by audit 4, and `slot_permutations_r4`, the round-4 repair of `slot_permutations`, which after the repair scores +0.188 at level 6 on an audit-4 rule and is dropped, not repaired again (R-26). The three round-3 drops (`pythagoras`, `binomial_choose`, `digit_puzzle`) stay dropped. Five lineages were repaired and survive as new revisions `_r4` (`mixture`, `gcd_lcm`, `finite_differences`, `average_missing`, `clock_duration`). The largest remaining rule excess over the base among the 29 survivors is +0.093 (`last_digit_power_r3`, level 0, audit-3 rule `exp_mod_p`). Two points are put to the lead and NOT decided here: six survivors have a rule that the auditor / the implementer judged to be the correct procedure and that is above 0.15 (section 5), and capacity fails for eight survivors under `core.generate_pool` as written (section 8). Neither is a claim of readiness.

## 2. Edits to existing files (R-27, brief item (a))

One edit to one existing file, listed here and in the manifest (`hygiene_edit`):

- `studies/m0/lineages_m1_fix3_c.py` line 116, inside `digit_puzzle_r3`: `for d in set(ds) if ds.count(d) == 1]` became `for d in sorted(set(ds)) if ds.count(d) == 1]`. The line made `tests/test_m0_generators.py` fail (iteration over `set()`).
- **The generated items are NOT byte-identical before and after.** Measured with `hash_digit.py` (scratch): 60 items at levels 0-4 and 10 at levels 5-6, stream seed 4001, label `fix4-hygiene`, SHA-256 of the items' JSON; the same under `PYTHONHASHSEED` 0 and 1. Old total `60cbdf1e35e8d6ac15e6db206e46c51f69d3fe592c524b7277870e14aefc351d`, new total `78989ef5a9997b132d49d0810cd12cd4d30008fe3012acd6d364906467b97ebf`. Per level (first 8 hex digits) old `46e8ee48 0b1a20fa ed71cf9a 029b5f92 1ce9051e 98c09225 12c06b84`, new `0f6052a3 fd2d2883 84314adb 8ca88965 f505308e 316cb9ec b5d3b522`: every level changed. Cause: the order of the candidate clues followed the set's iteration order, and the later `r.shuffle(cand)` consumes the random stream in that order. The lineage is NOT REGISTERED since round 3 and was not re-measured, so no survivor is affected.
- `tests/test_m0_generators.py` now passes (see section 10). No test, no `pyproject.toml`, no `uv.lock`, no other earlier lineage file was edited. The untracked `studies/m0/m1_rev2_gates.py.bak` and `tests/test_m0_m1_fix3_capacity.py.bak2` were left alone.

## 3. Repairs (brief items (b) and (c); new files only)

New revisions `M1.<stem>_r4` in `studies/m0/lineages_m1_fix4.py` (own registry `FIX4`; every other lineage is the very same object as in round 3, a test checks it). Each repaired builder has the SAME `structured` fields as its r3 predecessor (a test checks it), so every cheap rule and canonical key written for r3 reads it unchanged; the solution procedure is unchanged; nothing is redrawn conditional on a heuristic or on the answer. Level 0 of `mixture`, `finite_differences` and `gcd_lcm` draws from the r3 ranges (a test checks the first item equals r3's), because the capacity widening of round 3 was needed at the bottom.

Stated rising parameter per repaired lineage, its seven values, and the mean log10 of the answer per level (MEASURED, 300 items per level, seed 13):

| stem | parameter | values at levels 0-6 | mean log10(answer + 1) |
|---|---|---|---|
| `mixture` | ceiling of the two prices per kilogram, 30 + 6 x level dollars (the weights are as in r3; packing from level 3) | [30, 36, 42, 48, 54, 60, 66] | [1.194, 1.254, 1.327, 1.468, 1.511, 1.528, 1.545] |
| `gcd_lcm` | ceiling of the answer: gcd ask g <= gmax and the lcm ask g x prod(q) <= gmax x top x (top-1) x ... over k factors, with (k, top, gmax) from the table GCD_LCM_TABLE (strictly rising) | [98000, 177000, 333000, 584640, 1285200, 6120576, 13759200] | [2.66, 2.82, 2.833, 2.813, 2.975, 3.107, 3.393] |
| `finite_differences` | ceiling of the answer: every coefficient at its ceiling (``fd_ceilings``: 60 + 10 x level, 25 + 5 x level, 15 + 3 x level; degree 3 from level 5 as in r3) evaluated at the farthest asked position m + 2 | [970, 1162, 1354, 1946, 2188, 3885, 4822] | [2.609, 2.662, 2.742, 2.91, 2.931, 3.237, 3.348] |
| `average_missing` | ceiling of the marks, 100 + 10 x level (number of tests 4 + level // 2 as in r3) | [100, 110, 120, 130, 140, 150, 160] | [1.836, 1.87, 1.877, 1.911, 1.943, 1.946, 1.961] |
| `clock_duration` | ceilings of the waits (40 + 4 x level minutes) and of the rides (110 + 6 x level minutes); number of legs 2 + level // 2 as in r3 | [150, 160, 170, 180, 190, 200, 210] | [2.095, 2.115, 2.316, 2.337, 2.477, 2.498, 2.607] |
| `slot_permutations` | longest code length 3 + level digits (r3: 3 up to 6) | [3, 4, 5, 6, 7, 8, 9] | [1.513, 1.785, 1.999, 2.172, 2.225, 2.425, 2.556] |

Notes: (1) mean log10(answer) is not strictly rising for `gcd_lcm` between levels 2 and 3 (2.833 to 2.813, the change of k from 2 to 3 with smaller number caps); the stated parameter (the ceiling of the answer) is rising. (2) `clock_duration` level 0 is narrower than r3's (waits 5..40, rides 20..110 against 5..60 and 20..150); its measured n_eff has no collision at M = 30,000. (3) `average_missing` and `clock_duration` are not named in the brief's list of collapsed levels (it names mixture, gcd_lcm, finite_differences, slot_permutations). Audit 4's level profile (section 4, `level_profile.txt`) shows both with levels 0=1, 2=3, 4=5 identical, unchanged since batch 1. I read this as the same collapsed-level defect under R-25 (c) and R-21 and repaired them in the same way; if the lead reads the list as exhaustive, the two would be dropped instead and the cluster count falls from 17 to 16 (clock_duration is a singleton cluster; average_missing is one of six members of S1).

- (b) `slot_permutations_r4`: the sentence "A code may start with the digit 0 whenever the rules below allow it (for example 012 is a 3-digit code)." is printed in EVERY item where 0 is an allowed digit and the first-digit rule is not "may not be 0" (r3 printed a leading-zero sentence only for the rule "any", which left 17.6-19.0 % of items where the key depends on the reading: "even" and "less than 5" accept 0). Check: the key equals the enumeration with leading zeros counted (the audit's example, digits 0 1 3 5 7, first digit even, last odd: key 100), and the check fails on the r3 wording (failing-first test). The wording repair works; the lineage is nevertheless dropped for the level repair, below.
- (c) `slot_permutations_r4`: the longest code length is 3 + level (r3: 3, 3, 4, 4, 4, 6, 6). Measured after the repair (the one measurement R-26 allows): the audit-4 rule `mode_by_visible_ask` (the most frequent answer among items with the same visible first-digit rule, last-digit rule, repeat flag and code length, two-fold held out) scores -0.062, +0.070, +0.075, +0.080, +0.125, +0.123, +0.188 above the base at levels 0-6. Level 6 is above 0.15, so the lineage is dropped, not repaired again. Diagnostic (MEASURED, 3,000 items per level, no repair made): the code length equals the number of allowed digits in 0, 12, 25, 40, 51, 59 and 65 % of items at levels 0-6 (r3: 0, 0, 12, 12.5, 12, 39, 38 %), so the visible length fixes the digit count and the answer class. I did not try another level parameter; that would be a second pass.

## 4. Dropped lineages

| lineage | cluster | why | measured |
|---|---|---|---|
| `M1.coins_r3` | S1_linear_solve | R-24: audit-4 rule `floor(total / hi) - 1` (`a4:hi_is_value_over_hi_minus_1`) | +0.160 (L0), +0.140, +0.128, +0.114, +0.110, +0.087, +0.076; same value as audit 4's (same script, seed and ids). Within sampling noise of the bound (half-width about 0.02 at N = 2,000) but above it. |
| `M1.pigeonhole_worst_case_r3` | pigeonhole_worst_case | R-24: `a4:all_other_colours_then_k` | +0.273, +0.287 (L1), +0.275, +0.252, +0.229, +0.243, +0.257 |
| `M1.mode_tally_r3` | mode_tally | R-24: `a4:mode_by_visible_ask` (the 'others' key from the printed list length) | +0.377, +0.382 (L1), +0.371, +0.376, +0.372, +0.367, +0.376 |
| `M1.slot_permutations_r4` | S4_product_rule_counting | R-26: above the bound after the (b)+(c) repair (section 3) | -0.062 ... +0.188 (L6) |
| `M1.pythagoras_r3`, `M1.binomial_choose_r3`, `M1.digit_puzzle_r3` | pythagoras, S4, digit_puzzle | NOT REGISTERED in round 3 and stay so (R-24/R-25: no new lineage, no replacement); re-measured here for the record: +0.257 (L0), +0.131 (L0), +0.277 (L0) | digit_puzzle at N = 300 |

`min_cost_packs` stays excluded everywhere (R-12). The cluster S4_product_rule_counting disappears (no registered member); S1 stays (6 members).

## 5. Rule measurement for every candidate (the union battery)

Union (R-24): (1) the implementer's battery `m1_fix3_shortcuts` by its own scoring, (2) the audit-4 script `shortcuts_a4.py` (its own `a4:` rules, three fitted generic rules, and the `im:` copy of (1)), (3) the audit-3 rule definitions `shortcuts_a3.spec` scored as `shortcuts_a3.py` scores them. Scripts read from `docs/reviews/m0-lineage-decision-2026-11-25/audit3_m1` and `audit4_m1` with `importlib`, unmodified; only their loader is replaced, in memory, by the fix-4 set (`studies/m0/m1_fix4_battery.py`). N = 2,000 per level (digit_puzzle 300), seeds own 410302, audit-4 17, audit-3 5; rates over all items (a rule that does not apply is a miss), base = held-out most frequent answer; 95 % half-width about +-0.02. The audit-3 rules were written for the rev2 fields: where a rule raises on a fix-3/4 field it is skipped for that item (it happened for all items of `slot_permutations_r4` and `binomial_choose_r3`: no audit-3 rule ran on them beyond the echo rule; the 34 other lineages raised on no item). Table: largest |rule - base| over the levels (signed value and its rule), then the signed largest per level 0-6. Raw numbers: `manifests/m1_fix4_battery_raw.json`; per-lineage and per-level in `manifests/m1_fix4_survivors.json`.

| lineage | cluster | status | largest | rule | per level |
|---|---|---|---|---|---|
| `M1.ages_r3` | S1_linear_solve | SURVIVES | +0.022 (L6) | `a4:sum_over_k_plus_1` | -0.015 -0.012 +0.011 +0.015 +0.022 -0.016 +0.022 |
| `M1.arithmetic_series_r3` | S7_step_rule | SURVIVES | -0.004 (L0) | `a3:echo_best_position[first/first]` | -0.004 -0.002 -0.001 -0.002 -0.001 -0.001 -0.002 |
| `M1.average_missing_r4` | S1_linear_solve | SURVIVES | +0.011 (L1) | `a4:echo_pos_offset` | +0.008 +0.011 +0.007 -0.004 +0.006 +0.007 +0.005 |
| `M1.binomial_choose_r3` | S4_product_rule_counting | NOT_REGISTERED | +0.131 (L0) | `own:product_of_x_times_j` | +0.131 +0.128 +0.074 +0.029 +0.015 +0.009 +0.010 |
| `M1.change_ways_r3` | S5_unbounded_table | SURVIVES | +0.042 (L0) | `own:T_over_max_plus_1` | +0.042 -0.025 -0.021 -0.011 -0.013 -0.009 -0.011 |
| `M1.clock_duration_r4` | clock_duration | SURVIVES | -0.012 (L0) | `a3:span_incl_waits` | -0.012 -0.009 -0.007 -0.007 -0.007 -0.007 -0.004 |
| `M1.coins_r3` | S1_linear_solve | NOT_REGISTERED | +0.160 (L0) | `a4:hi_is_value_over_hi_minus_1` | +0.160 +0.140 +0.128 +0.114 +0.110 +0.087 +0.076 |
| `M1.consecutive_r3` | S1_linear_solve | SURVIVES | -0.001 (L0) | `a4:echo_pos_offset` | -0.001 +0.000 -0.001 +0.000 +0.001 +0.001 +0.001 |
| `M1.crt_congruence_r3` | crt_congruence | SURVIVES | +0.062 (L0) | `a3:largest_mod_remainder` | +0.062 +0.051 +0.049 +0.053 +0.054 +0.056 +0.043 |
| `M1.digit_puzzle_r3` | digit_puzzle | NOT_REGISTERED | +0.277 (L0) | `own:smallest_meeting_all_but_first` | +0.277 +0.113 +0.147 +0.233 +0.207 +0.217 +0.210 |
| `M1.division_counting_r3` | division_counting | SURVIVES | -0.075 (L0) | `own:echo_best_position[second/second]` | -0.075 -0.062 -0.067 -0.067 -0.049 -0.055 -0.048 |
| `M1.finite_differences_r4` | finite_differences | SURVIVES | -0.003 (L1) | `a4:echo_pos` | -0.002 -0.003 -0.003 -0.002 -0.002 -0.001 -0.001 |
| `M1.fraction_remainder_r3` | S3_multiplicative_chain | SURVIVES | +0.021 (L3) | `a4:spends_not_left` | +0.011 +0.017 +0.015 +0.021 +0.017 +0.017 +0.019 |
| `M1.gcd_lcm_r4` | gcd_lcm | SURVIVES | +0.028 (L0) | `a3:min_difference` | +0.028 +0.025 +0.021 -0.022 -0.021 -0.023 -0.018 |
| `M1.grid_perimeter_r3` | S6_exposed_faces | SURVIVES | -0.088 (L3) | `a3:echo_best_position[first/first]` | -0.087 -0.085 -0.083 -0.088 -0.075 -0.072 -0.070 |
| `M1.inclusion_exclusion_r3` | inclusion_exclusion | SURVIVES | -0.034 (L0) | `im:any_ignore_overlap` | -0.034 -0.030 -0.025 -0.015 -0.009 +0.009 -0.007 |
| `M1.last_digit_power_r3` | last_digit_power | SURVIVES | +0.093 (L0) | `a3:exp_mod_p` | +0.093 +0.070 +0.021 +0.020 +0.023 +0.019 +0.015 |
| `M1.linear_equation_r3` | S1_linear_solve | SURVIVES | -0.017 (L0) | `own:ignore_constant` | -0.017 -0.013 -0.013 +0.011 +0.007 +0.011 +0.007 |
| `M1.median_list_r3` | median_list | SURVIVES | +0.089 (L0) | `im:mode_value` | +0.089 +0.056 +0.068 +0.050 +0.051 +0.043 +0.041 |
| `M1.mixture_r4` | S2_weighted_sum | SURVIVES | +0.033 (L3) | `own:unweighted_mean` | +0.030 +0.028 +0.028 +0.033 +0.029 +0.032 +0.026 |
| `M1.mode_tally_r3` | mode_tally | NOT_REGISTERED | +0.382 (L1) | `a4:mode_by_visible_ask` | +0.377 +0.382 +0.371 +0.376 +0.372 +0.367 +0.376 |
| `M1.painted_cube_r3` | S6_exposed_faces | SURVIVES | -0.007 (L2) | `own:echo_best_position[first/first]` | -0.007 +0.007 -0.007 -0.004 -0.004 -0.004 -0.005 |
| `M1.percent_change_r3` | S3_multiplicative_chain | SURVIVES | +0.007 (L3) | `own:first_step_only` | -0.003 +0.003 +0.004 +0.007 -0.005 +0.005 +0.006 |
| `M1.pigeonhole_worst_case_r3` | pigeonhole_worst_case | NOT_REGISTERED | +0.287 (L1) | `a4:all_other_colours_then_k` | +0.273 +0.287 +0.275 +0.252 +0.229 +0.243 +0.257 |
| `M1.pipes_work_r3` | S1_linear_solve | SURVIVES | -0.032 (L0) | `im:ignore_drain` | -0.032 -0.025 -0.021 +0.030 +0.031 +0.025 +0.028 |
| `M1.prime_factors_r3` | prime_factors | SURVIVES | -0.083 (L1) | `own:omega_plus_one` | -0.077 -0.083 -0.065 -0.066 -0.064 -0.063 +0.056 |
| `M1.pythagoras_r3` | pythagoras | NOT_REGISTERED | +0.257 (L0) | `im:memorised_16_scaled` | +0.257 +0.132 +0.072 +0.053 +0.046 +0.040 +0.034 |
| `M1.quadratic_area_r3` | quadratic_area | SURVIVES | -0.010 (L1) | `a3:quarter_perimeter` | +0.006 -0.010 -0.006 -0.005 -0.004 -0.004 -0.004 |
| `M1.ratio_share_r3` | S3_multiplicative_chain | SURVIVES | +0.059 (L0) | `own:equal_split` | +0.059 +0.055 +0.028 +0.029 +0.021 +0.020 +0.022 |
| `M1.rectangle_r3` | S1_linear_solve | SURVIVES | +0.015 (L2) | `a4:echo_pos_offset` | +0.010 +0.011 +0.015 +0.013 +0.009 +0.012 +0.011 |
| `M1.recurrence_iterate_r3` | S7_step_rule | SURVIVES | +0.005 (L0) | `a4:echo_pos_offset` | +0.005 -0.002 -0.001 -0.001 -0.001 -0.001 -0.002 |
| `M1.shopping_r3` | S2_weighted_sum | SURVIVES | +0.031 (L0) | `a3:ignore_counts` | +0.031 +0.002 +0.001 +0.004 -0.004 -0.004 -0.003 |
| `M1.slot_permutations_r4` | S4_product_rule_counting | NOT_REGISTERED | +0.188 (L6) | `a4:mode_by_visible_ask` | -0.062 +0.070 +0.075 +0.080 +0.125 +0.123 +0.188 |
| `M1.speed_distance_r3` | S2_weighted_sum | SURVIVES | +0.035 (L3) | `a4:mean_speed_rounded` | +0.026 +0.017 +0.034 +0.035 +0.025 +0.022 +0.019 |
| `M1.tiered_pricing` | tiered_pricing | SURVIVES | -0.007 (L3) | `im:all_at_first_rate` | -0.004 +0.003 +0.001 -0.007 -0.005 -0.005 -0.003 |
| `M1.tip_split_r3` | S3_multiplicative_chain | SURVIVES | -0.001 (L0) | `a4:echo_pos` | -0.001 -0.001 -0.001 -0.001 -0.001 -0.001 +0.000 |

The audit-4 values for the unchanged lineages are reproduced (coins +0.160, pigeonhole +0.287, mode_tally +0.382, median_list +0.089, grid_perimeter -0.087/-0.088).

**PENDING LEAD REVIEW (not decided here).** Rules that audit 4 (`short_summary_a4.PROC`) or the round-3 implementer (`PROCEDURE`) judged to be the correct procedure are NOT counted as cheap rules, exactly as in audit 4's own distribution. Six survivors have such a rule above 0.15, listed in the manifest (`survivors_with_an_excluded_procedure_rule_above_the_bound_PENDING_LEAD_REVIEW`): `consecutive` (`mean_plus_step`, +0.51 at levels 0-1: for three numbers it is the procedure), `division_counting` (`k_minus_remainder_ignores_exact_fit`, +0.45: wrong only on exact fits), `finite_differences` (`next_term_when_asked_later`, +0.51: one extension of the table), `gcd_lcm` (`product_over_gcd_of_all` for k = 2, and the false general rules `product / gcd^(k-1)`, `product / lcm^(k-1)`, exact at k >= 3: audit 4 section 3, a construct-validity issue), `prime_factors` (`largest_le_sqrt`, +0.20: needs the factorisation) and `ratio_share` (`largest_share`/`smallest_share`, +0.54: a guess of which person is asked). If R-24 is read as "any rule, procedure or not", these six lineages would be dropped; the exclusion list is in the manifest (`procedure_rule_exclusions`). `last_digit_power`'s excluded rule reads +0.116 (below 0.15).

## 6. Levels (R-21, R-25 (c), R-26)

For every written lineage except `digit_puzzle` (slow, not registered): the audit-4 no-op test over ALL 21 level pairs (300 items from the same stream at both levels; a pair is flagged when every item is byte-identical): no pair is identical for any of the 35 (`manifests/m1_fix4_checks.json`), including the 29 survivors. The same check reports the audit's identical levels on the r3 shapes (tests: mixture 0=1, 1=2, 3=4, 4=5, 5=6; gcd_lcm 0=1, 1=2, 3=4, 5=6; finite_differences 0=1, 1=2, 3=4, 5=6; slot 0=1, 2=3, 3=4, 5=6; average_missing and clock_duration 0=1, 2=3, 4=5). For the repaired lineages the stated parameter rises strictly (table in section 3). What this does not show: that levels differ in difficulty for a reader (no model was run), or that the adjacent distributions are far apart (mixture's price ceiling moves by 6 dollars per level).

## 7. Clusters

Strict map unchanged (`lineages_m1_fix3_clusters.GROUPS`, the audit-4 map), minus the dropped lineages: **17 surviving clusters**: S1_linear_solve, S2_weighted_sum, S3_multiplicative_chain, S5_unbounded_table, S6_exposed_faces, S7_step_rule, clock_duration, crt_congruence, division_counting, finite_differences, gcd_lcm, inclusion_exclusion, last_digit_power, median_list, prime_factors, quadratic_area, tiered_pricing. S1 has 6 members (coins left), S2 3, S3 4, S5 1, S6 2, S7 2, and eleven singletons. Lineages are clusters; no strata are proposed. The borderline merges of round 3 and audit 4 (gcd_lcm + crt, clock_duration + S2, tiered_pricing + S2, S1 + S7) are listed there, not merged; the cross-evaluation map (R-15) was not part of this brief.

## 8. Capacity (R-22, R-28)

Method: the audit-4 script `capacity_a4.py` read unchanged (canonical structural key; M = 30,000 draws per lineage and level, seed 23; n_eff = M(M-1)/(2P), a level without a collision is given M(M-1)/6 = 149,995,000; Chao1 as a second estimate); `studies/m0/m1_fix4_capacity.py`. Sampled lower bounds. The sampled n_eff of all 29 unchanged lineages sampled (24 survivors and the five dropped ones coins, pigeonhole, mode_tally, pythagoras, binomial_choose) equals audit 4's `cap_M30000.txt` exactly, level by level (same script, seed and ids).

Demand (ANALYTICAL, R-11): 10 x (ceil(4000/G) + ceil(20000/G) + 100) per cluster and level, reserve levels the same. **Reading of G:** the brief says "G is the number of surviving clusters"; R-11 says the smaller part's cluster count. With 17 surviving clusters I took the smaller part: G = 17 // 2 = 8, demand **31,000** (it was 25,000 at G = 10 in round 3 and 27,680 at G = 9). Taken literally, G = 17 gives 15,130 (also in the manifest). The reading is the lead's to confirm.

**As written (`core.generate_pool`, R-28).** The builder allocates the pool equally per LINEAGE over `part_lineages` (the lineages whose family is in the part) and `m0_draw` balances per lineage id, so the unit that must meet the demand is a lineage, and G is the number of lineages in its part. The surviving set is not in `core.REGISTRY`, so I applied `family_partition`'s own rule (SHA-256 shuffle of the sorted family names, partition seed 400004, part A the smaller half) to the survivors' 18 families: part A 14 lineages, part B 15 lineages, per-lineage demand **18,150** (A) and **17,010** (B). Structural n_eff against that demand fails for **8 survivors** (LISTED for the lead, not dropped; their status is SURVIVES): ages (levels 0-2), consecutive (0-1), fraction_remainder (0-6), grid_perimeter (0), percent_change (0, 1, 3), pipes_work (0-2), ratio_share (0), rectangle (0-6). All five repaired survivors pass as written (the rule that would have dropped them, R-25 (c)). Per-lineage table, smallest margin first (n_eff per level 0-6; margin = smallest n_eff / demand):

| lineage | part | demand | n_eff per level | min margin | failing levels |
|---|---|---|---|---|---|
| `M1.rectangle_r3` | A | 18,150 | 3,625 4,207 4,829 5,421 6,040 6,652 7,298 | 0.20 | [0, 1, 2, 3, 4, 5, 6] |
| `M1.fraction_remainder_r3` | B | 17,010 | 6,283 7,242 8,351 9,308 10,432 11,518 12,718 | 0.37 | [0, 1, 2, 3, 4, 5, 6] |
| `M1.consecutive_r3` | B | 17,010 | 8,419 12,382 32,636 40,771 48,954 56,917 64,699 | 0.49 | [0, 1] |
| `M1.ages_r3` | A | 18,150 | 10,241 12,582 17,943 20,988 28,786 33,531 43,168 | 0.56 | [0, 1, 2] |
| `M1.pipes_work_r3` | A | 18,150 | 10,262 13,772 17,933 556,224 760,110 894,602 1,282,009 | 0.56 | [0, 1, 2] |
| `M1.percent_change_r3` | B | 17,010 | 14,024 16,220 18,689 15,334 17,073 18,878 20,425 | 0.82 | [0, 1, 3] |
| `M1.ratio_share_r3` | B | 17,010 | 15,154 20,119 219,827 263,766 1,562,448 1,999,933 2,284,188 | 0.89 | [0] |
| `M1.grid_perimeter_r3` | A | 18,150 | 17,420 885,797 449,985,000 149,995,000 149,995,000 149,995,000 149,995,000 | 0.96 | [0] |
| `M1.tip_split_r3` | B | 17,010 | 17,613 21,937 28,942 34,834 42,435 47,855 56,276 | 1.03 | - |
| `M1.arithmetic_series_r3` | B | 17,010 | 26,623 36,062 44,026 53,487 62,016 72,567 80,455 | 1.56 | - |
| `M1.mixture_r4` | B | 17,010 | 30,367 44,121 61,574 749,975 941,391 1,174,896 1,437,652 | 1.78 | - |
| `M1.prime_factors_r3` | B | 17,010 | 31,055 43,807 68,252 105,383 166,538 252,659 370,053 | 1.83 | - |
| `M1.painted_cube_r3` | A | 18,150 | 34,374 51,129 70,652 101,807 135,947 168,597 221,996 | 1.89 | - |
| `M1.speed_distance_r3` | A | 18,150 | 35,078 72,555 9,374,688 18,749,375 149,995,000 149,995,000 149,995,000 | 1.93 | - |
| `M1.linear_equation_r3` | B | 17,010 | 44,259 66,448 87,427 661,743 945,347 988,978 1,159,755 | 2.60 | - |
| `M1.change_ways_r3` | A | 18,150 | 47,292 66,763 88,825 105,161 122,279 141,638 166,046 | 2.61 | - |
| `M1.gcd_lcm_r4` | B | 17,010 | 56,845 101,052 188,357 48,230 101,738 44,513 93,068 | 2.62 | - |
| `M1.finite_differences_r4` | A | 18,150 | 47,688 79,293 123,963 180,862 245,893 102,293 214,688 | 2.63 | - |
| `M1.quadratic_area_r3` | B | 17,010 | 47,417 63,468 80,802 98,357 119,613 145,156 171,947 | 2.79 | - |
| `M1.recurrence_iterate_r3` | A | 18,150 | 103,540 136,029 147,150 170,513 187,807 205,943 226,693 | 5.71 | - |
| `M1.division_counting_r3` | A | 18,150 | 128,420 177,159 248,886 328,217 383,946 488,053 474,168 | 7.08 | - |
| `M1.inclusion_exclusion_r3` | A | 18,150 | 161,459 641,919 1,867,158 149,995,000 149,995,000 149,995,000 149,995,000 | 8.90 | - |
| `M1.tiered_pricing` | B | 17,010 | 202,696 493,946 149,995,000 149,995,000 149,995,000 149,995,000 149,995,000 | 11.92 | - |
| `M1.last_digit_power_r3` | B | 17,010 | 213,770 410,570 149,995,000 149,995,000 149,995,000 149,995,000 149,995,000 | 12.57 | - |
| `M1.crt_congruence_r3` | B | 17,010 | 492,864 896,384 1,557,042 4,591,684 14,062,031 149,995,000 149,995,000 | 28.98 | - |
| `M1.shopping_r3` | B | 17,010 | 627,594 112,496,250 149,995,000 149,995,000 149,995,000 149,995,000 149,995,000 | 36.90 | - |
| `M1.average_missing_r4` | A | 18,150 | 2,307,615 3,912,913 89,997,000 224,992,500 149,995,000 149,995,000 149,995,000 | 127.14 | - |
| `M1.clock_duration_r4` | A | 18,150 | 224,992,500 224,992,500 149,995,000 149,995,000 149,995,000 149,995,000 149,995,000 | 8264.19 | - |
| `M1.median_list_r3` | A | 18,150 | 149,995,000 149,995,000 149,995,000 149,995,000 149,995,000 149,995,000 149,995,000 | 8264.19 | - |

Informational (not the pass criterion): `draw_items` de-duplicates on the normalised TEXT including names; the n_eff on the text, measured the same way, is below the demand only for `consecutive` (levels 0-1), `percent_change` (0-1) and `rectangle` (0-6), because those items print no name or setting; the other five lineages above fail only on the structural count. The count that is the unit of R-16 is not ruled; I used the stricter structural key, as in rounds 3 and 4 of the audit.

**HYPOTHETICAL per-cluster builder (no such builder exists; nothing below is a pass under `generate_pool`).** Equal split by cluster, then equally inside the cluster, de-duplicated structurally; G = 8, demand 31,000. Bases per cluster and level: mixture n_eff, Chao1 sum, and equal share (every member alone supplies demand / L, the strictest and the one that matches an equal split inside a cluster). All 17 clusters pass the mixture and Chao1 bases at every level. The equal-share basis FAILS for S1_linear_solve at levels 0-2 (rectangle) and S3_multiplicative_chain at levels 0-1 (fraction_remainder); these two clusters pass only on the more favourable bases. `prime_factors` level 0 is the tightest pass: 31,055 sampled (31,236 exact by audit 4, ANALYTICAL) against 31,000.

| cluster | members | equal share n_eff x L per level 0-6 | mixture / Chao1 at level 0 | fails equal share | fails mixture | fails Chao1 |
|---|---|---|---|---|---|---|
| S1_linear_solve | 6 | 21,752 25,239 28,972 32,527 36,242 39,915 43,788 | 58,752 / 2,355,469 | [0, 1, 2] | - | - |
| S2_weighted_sum | 3 | 91,102 132,362 184,723 2,249,925 2,824,174 3,524,687 4,312,955 | 142,787 / 711,335 | - | - | - |
| S3_multiplicative_chain | 4 | 25,134 28,967 33,406 37,233 41,729 46,072 50,873 | 45,297 / 66,610 | [0, 1] | - | - |
| S5_unbounded_table | 1 | 47,292 66,763 88,825 105,161 122,279 141,638 166,046 | 47,292 / 58,435 | - | - | - |
| S6_exposed_faces | 2 | 34,841 102,258 141,305 203,613 271,894 337,194 443,991 | 46,245 / 404,964 | - | - | - |
| S7_step_rule | 2 | 53,246 72,125 88,051 106,974 124,031 145,133 160,910 | 84,711 / 168,566 | - | - | - |
| clock_duration | 1 | 224,992,500 224,992,500 149,995,000 149,995,000 149,995,000 149,995,000 149,995,000 | 224,992,500 / 224,970,002 | - | - | - |
| crt_congruence | 1 | 492,864 896,384 1,557,042 4,591,684 14,062,031 149,995,000 149,995,000 | 492,864 / 524,885 | - | - | - |
| division_counting | 1 | 128,420 177,159 248,886 328,217 383,946 488,053 474,168 | 128,420 / 180,689 | - | - | - |
| finite_differences | 1 | 47,688 79,293 123,963 180,862 245,893 102,293 214,688 | 47,688 / 47,724 | - | - | - |
| gcd_lcm | 1 | 56,845 101,052 188,357 48,230 101,738 44,513 93,068 | 56,845 / 57,422 | - | - | - |
| inclusion_exclusion | 1 | 161,459 641,919 1,867,158 149,995,000 149,995,000 149,995,000 149,995,000 | 161,459 / 163,998 | - | - | - |
| last_digit_power | 1 | 213,770 410,570 149,995,000 149,995,000 149,995,000 149,995,000 149,995,000 | 213,770 / 218,566 | - | - | - |
| median_list | 1 | 149,995,000 149,995,000 149,995,000 149,995,000 149,995,000 149,995,000 149,995,000 | 149,995,000 / 450,015,000 | - | - | - |
| prime_factors | 1 | 31,055 43,807 68,252 105,383 166,538 252,659 370,053 | 31,055 / 31,275 | - | - | - |
| quadratic_area | 1 | 47,417 63,468 80,802 98,357 119,613 145,156 171,947 | 47,417 / 50,313 | - | - | - |
| tiered_pricing | 1 | 202,696 493,946 149,995,000 149,995,000 149,995,000 149,995,000 149,995,000 | 202,696 / 201,178 | - | - | - |

## 9. Answer keys

(1) The implementer's existing second derivation (`m1_fix3_verify`, extended to the fix-4 builders by `m1_fix4_verify`, because its window for `average_missing` (marks up to 100) and `slot_permutations` (codes up to 6 digits) is too small for the new ranges): 200 items per level, all seven levels, for all 35 written lineages except `digit_puzzle`: 0 mismatches (`manifests/m1_fix4_checks.json`). This is a self-check from the structured form, not a second solver from a separate context (R-9 is still open). (2) The audit-4 text-only solver `solve_text_a4.py`, read unchanged, on the 29 survivors, 150 items per level (30,450 items, seed 11, label `keys4`): 0 mismatches, 308 solver errors, all in `average_missing_r4` levels 1-6 (the solver asserts "marked out of 100", which no longer holds; the answer was checked by (1) only); every other lineage 0 errors. Script in scratch (`a4_text_keys.py`).

## 10. Commands, seeds, environment, tests (MEASURED)

`PYTHONHASHSEED=0 PYTHONPATH=<worktree> PYTHONDONTWRITEBYTECODE=1 uv run --locked --offline python -m ...` in the worktree `agent-a0c9d741ea96ce52f`, branch `claude/m0-impl`, Python 3.12, `uv.lock` untouched. Final provenance runs ("run2" in the scratch directory `/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_fix4_m1_20261125/`):

- `python -m studies.m0.m1_fix4_battery --n 2000 --workers 6 --out <battery.json>` (109 s)
- `python -m studies.m0.m1_fix4_capacity --m 30000 --workers 6 --all --out <cap.json>` and the same with `--text` for the text-dedup n_eff
- `python -m studies.m0.m1_fix4_survivors checks --out <checks.json>`
- `python -m studies.m0.m1_fix4_survivors build --battery studies/m0/manifests/m1_fix4_battery_raw.json --capacity studies/m0/manifests/m1_fix4_capacity_raw.json --checks studies/m0/manifests/m1_fix4_checks.json --text studies/m0/manifests/m1_fix4_text_capacity_raw.json --out studies/m0/manifests/m1_fix4_survivors.json`

Input hashes (SHA-256): battery af6087d05234b198e25232baee626838201c73d441d337b04f45d69aeed2204c, capacity 125dcf4773c286b4297d031dd32f4c1171eec21861a2e995cb101aaefd3b0329, checks b84c53e84b9de70f42a4a3bee3b78a193cb1015df9c8b009090b626c2d664e2d, text capacity ee8a9506684728eb54ab4f7b088e65d03f4701cc66e5123261d58230e4307f46. A first run (run1, before two cosmetic changes to the rule labels and the text capacity field) gave the same raw rates and the same decisions.

Decision rules (fixed before the measurement, stated in `m1_fix4_survivors.py`): bound 0.15 two-sided ("more than 0.15" drops; exactly 0.15 does not); levels identical or parameter not rising; key mismatch; a REPAIRED lineage failing the as-written capacity; round-3 drops stay.

Tests (MEASURED, `-p no:cacheprovider`, `uv run --locked`): `pytest tests/test_m0_generators.py tests/test_m0_m1_fix4_*.py -q`: **152 passed, 0 failed** in 17 s (the two new files hold 71 tests: lineages 52, survivors 19); `pytest tests/test_m0_m1_fix3_*.py -q`: **215 passed, 0 failed**; `pytest tests/test_m0_m1_*.py -q` (all M1 tests, fix 3 and fix 4 together): **328 passed, 0 failed**, 541 s. `uv run --locked ruff check .` reports one I001 import-order error in a file of another implementer (`tests/` file importing `lineages_r1_fix4_clusters`), none in the M1 files (`ruff check` on every `m1_fix4_*`, `lineages_m1_fix4*` and `tests/test_m0_m1_fix4_*` file passes). The whole M0 suite was not run by me. New files: `studies/m0/lineages_m1_fix4.py`, `lineages_m1_fix4_clusters.py`, `m1_fix4_battery.py`, `m1_fix4_capacity.py`, `m1_fix4_checks.py`, `m1_fix4_survivors.py`, `m1_fix4_verify.py`, `studies/m0/manifests/m1_fix4_survivors.json` (and the four raw inputs `m1_fix4_battery_raw.json`, `m1_fix4_capacity_raw.json`, `m1_fix4_text_capacity_raw.json`, `m1_fix4_checks.json`), `tests/test_m0_m1_fix4_lineages.py`, `tests/test_m0_m1_fix4_survivors.py`, this file.

## 11. Not verified, open points, slips

- No second solver from a separate context (R-9); the round-4 survivors have had no independent audit. The auditors' rules were run by me; I did not judge new rules beyond the union.
- `slot_permutations` loop on a positive answer (`until(cnt > 0)`) and `linear_equation`'s `while m == 0` are unchanged from round 3 (audit 4 section 3: answer-conditional redraws, no measurable tell, verdict REGISTRABLE AS IS). Under R-19 whether they are needed for well-posedness is not shown here; `slot_permutations` is dropped anyway. `linear_equation_r3` survives with its loop; flagged for the lead.
- `gcd_lcm`'s k >= 3 false general rule (audit 4 section 3, PENDING LEAD REVIEW) is not repaired and the lineage survives on the audit's judgement that the rule is not cheap.
- Sampling: the rule rates carry about +-0.02 at N = 2,000; coins (+0.160) is inside that of the bound and was dropped on the measured value. Capacity n_eff is a sampled lower bound; the margins at prime_factors level 0 (31,055 against 31,000) and rectangle are thin.
- Mean log10 of the answer is not strictly rising for gcd_lcm between levels 2 and 3 (section 3). Difficulty for a reader was not measured.
- The part partition used for the as-written demand is `family_partition`'s rule applied to the survivors' families, not a registered partition; the strict-cluster partition (R-6) is not computed here.
- Audit 4 section 9 items still open: exact support for clock_duration, median_list, shopping, speed_distance (sampled only); the fixture files (`fixtures/m1_fix3`) were NOT regenerated for the round-4 revisions, so the fix-3 fixtures still contain the r3 versions of the five repaired lineages and the dropped ones.
- Slips: (1) I ran `ruff check --fix studies/m0/` once by mistake (it should have been my own files): at 21:58:13 it rewrote files of other implementers working in the same worktree (the changed mtimes are `c1_fix4_draw.py`, `lineages_r1_fix4_a.py`, `r1_fix4_capacity.py`, `r1_fix4_measure.py`, `r2_fix3_battery.py`); ruff's fix is limited to import ordering and unused imports, but I did not record the originals and cannot undo it; the lead should check those five files. (2) The Edit tool refused writes in this worktree from the session worktree, so I wrote files through Bash with Python heredocs (allowed by the brief). (3) One `sleep 60` was blocked by the harness; no forbidden command was run (no rm, chmod, chown, sudo, mv, pkill, killall, sed -i, no signal by pattern, nothing under /tmp or /private/tmp by me). No commit, push or branch switch.

Astra review: NOT_PERFORMED
