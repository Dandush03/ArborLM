# R1 revision-4 registered set: worst heuristic per shape and level, two-sided (1000 items per level, levels 0..6, test-block seed)

Gain = the better of following a heuristic and avoiding it (accuracy minus chance, or minus the commonest-answer share for open answers), on the items it fires on. EFFECTIVE gain = gain x the share
of items the heuristic fires on (what a solver gains by using it where it fires and guessing elsewhere); the worst heuristic is picked by effective gain, per level.
Cells with fewer than 100 firings are not shown; a cell where the heuristic is right on at least 99 % of the items it fires on and fires on at least 90 % of all items is the SOLUTION at that level (its exact special case: for example the two-step ancestor when the asked term is grandparent) and is listed under `procedure` instead of being picked as the worst shortcut. MEASURED, not thresholded. `z` is gain over its standard error (about 3 or more is not noise; with about 40 heuristics x 7 levels a few cells reach 3 by chance).

| shape | status | answers | worst cell: level, heuristic, effective gain (gain, z), accuracy vs baseline | per level 0..6: worst effective gain | procedure cells (excluded) |
|---|---|---|---|---|---|
| R1.activity_selection_r4 | rev4 | open | L1, constant_most_frequent_key, +0.000 (+0.000, z 0.0), 0.27 vs 0.27 | -0.09 / +0.00 / -0.15 / -0.20 / -0.18 / -0.16 / -0.15 | - |
| R1.attribute_rule | unchanged | closed | L1, first_mentioned, +0.036 (+0.036, z 2.85), 0.236 vs 0.2 | +0.02 / +0.04 / +0.01 / +0.03 / +0.02 / +0.00 / +0.00 | - |
| R1.boolean_lights_r4 | rev4 | closed | L4, M:press_parity_ignoring_initial, +0.033 (+0.033, z 2.09), 0.533 vs 0.5 | +0.03 / +0.03 / +0.03 / +0.03 / +0.03 / +0.01 / +0.02 | - |
| R1.categories_default_exceptions_r4 | rev4 | closed | L2, M:second_most_specific_rule, +0.074 (+0.074, z 4.68), 0.426 vs 0.5 | +0.06 / +0.06 / +0.07 / +0.04 / +0.04 / +0.04 / +0.04 | - |
| R1.categories_follow_r4 | rev4 | closed | L2, M:all_x_subject_yes, +0.089 (+0.247, z 9.95), 0.5806 vs 0.3333 | +0.05 / +0.07 / +0.09 / +0.06 / +0.05 / +0.07 / +0.06 | - |
| R1.compass_turns | unchanged | closed | L5, constant_most_frequent_key, +0.017 (+0.017, z 1.24), 0.267 vs 0.25 | +0.01 / +0.01 / +0.01 / +0.00 / +0.01 / +0.02 / +0.00 | - |
| R1.conditional_chain | unchanged | closed | L1, constant_most_frequent_key, +0.177 (+0.177, z 11.85), 0.51 vs 0.3333 | +0.08 / +0.18 / +0.01 / +0.05 / +0.02 / +0.00 / +0.04 | - |
| R1.conditional_decision_tree_r4 | rev4 | closed | L0, A:first_mentioned, +0.020 (+0.020, z 1.46), 0.27 vs 0.25 | +0.02 / +0.01 / +0.02 / +0.02 / +0.01 / +0.01 / +0.02 | - |
| R1.conditional_threshold_rule_r4 | rev4 | closed | L3, X:count_margin_times_weight_mean, +0.074 (+0.074, z 4.68), 0.574 vs 0.5 | +0.06 / +0.07 / +0.05 / +0.07 / +0.06 / +0.06 / +0.04 | - |
| R1.containers_queue_line_r2 | unchanged | closed | L0, M:simulate_ignoring_leaves, +0.474 (+0.474, z 36.5), 0.69 vs 0.2155 | +0.47 / +0.41 / +0.32 / +0.27 / +0.28 / +0.22 / +0.22 | - |
| R1.containers_stack_piles_r4 | rev4 | closed | L1, M:simulate_ignoring_reversals, +0.199 (+0.199, z 16.91), 0.366 vs 0.1667 | +0.08 / +0.20 / +0.19 / +0.15 / +0.14 / +0.10 / +0.09 | M:simulate_ignoring_reversals L0 |
| R1.elimination_bracket_r4 | rev4 | closed | L5, M:beater_in_own_half, +0.276 (+0.276, z 36.08), 0.3387 vs 0.0625 | +0.07 / +0.01 / +0.04 / +0.02 / +0.01 / +0.28 / +0.10 | - |
| R1.elimination_josephus | unchanged | closed | L5, F:first_mentioned, +0.169 (+0.169, z 16.99), 0.28 vs 0.1111 | +0.07 / +0.02 / +0.13 / +0.01 / +0.04 / +0.17 / +0.01 | - |
| R1.equivalence_classes_r2 | unchanged | closed | L2, M:common_same_neighbour_yes_else_cbd, +0.282 (+0.282, z 18.89), 0.615 vs 0.3333 | +0.24 / +0.25 / +0.28 / +0.27 / +0.25 / +0.28 / +0.28 | - |
| R1.equivalence_exchange_rates | unchanged | closed | L0, F:last_mentioned, +0.025 (+0.025, z 1.65), 0.358 vs 0.3333 | +0.02 / +0.01 / +0.02 / +0.01 / +0.01 / +0.00 / +0.00 | - |
| R1.event_timeline | unchanged | closed | L0, constant_most_frequent_key, +0.141 (+0.167, z 10.27), 0.0 vs 0.3333 | +0.14 / +0.06 / +0.04 / +0.02 / +0.01 / +0.01 / +0.01 | - |
| R1.graph_bipartite | unchanged | closed | L3, constant_most_frequent_key, +0.044 (+0.044, z 2.78), 0.544 vs 0.5 | +0.02 / +0.01 / +0.01 / +0.04 / +0.03 / +0.04 / +0.03 | - |
| R1.graph_shortest_route_r4 | rev4 | open | L0, M:greedy_nearest_walk, +0.022 (+0.033, z 2.67), 0.1462 vs 0.113 | +0.02 / +0.02 / -0.01 / -0.03 / -0.02 / -0.02 / -0.02 | - |
| R1.instant_runoff_r4 | rev4 | closed | L1, M:top_two_runoff, +0.382 (+0.382, z 27.9), 0.632 vs 0.25 | +0.37 / +0.38 / +0.38 / +0.29 / +0.30 / +0.27 / +0.29 | - |
| R1.kinship_ancestor_r4 | rev4 | closed | L0, M:childs_parent, +0.044 (+0.080, z 4.44), 0.0 vs 0.2328 | +0.04 / +0.04 / +0.03 / +0.02 / +0.02 / +0.02 / +0.02 | M:two_steps_regardless_of_term L0; M:two_steps_regardless_of_term L1; M:two_steps_regardless_of_term L2 |
| R1.kinship_cousins | unchanged | closed | L3, constant_most_frequent_key, +0.027 (+0.027, z 1.71), 0.527 vs 0.5 | +0.02 / +0.01 / +0.01 / +0.03 / +0.01 / +0.01 / +0.01 | - |
| R1.kinship_descendants_r4 | rev4 | closed | L2, M:last_mentioned, +0.021 (+0.021, z 1.53), 0.271 vs 0.25 | +0.02 / +0.01 / +0.02 / +0.02 / +0.01 / +0.01 / +0.02 | - |
| R1.knights_knaves | unchanged | closed | L6, constant_most_frequent_key, +0.043 (+0.043, z 2.72), 0.543 vs 0.5 | +0.01 / +0.03 / +0.01 / +0.03 / +0.03 / +0.03 / +0.04 | - |
| R1.minimax_tree_r4 | rev4 | open | L0, M:median_leaf_low, +0.469 (+0.469, z 51.07), 0.562 vs 0.093 | +0.47 / +0.21 / +0.15 / +0.10 / -0.01 / +0.17 / -0.04 | - |
| R1.mst_cost_r4 | rev4 | open | L0, M:shortest_path_tree_from_first_town, +0.069 (+0.069, z 8.04), 0.149 vs 0.08 | +0.07 / +0.06 / +0.02 / -0.04 / -0.04 / -0.04 / -0.03 | - |
| R1.nim_xor_r4 | rev4 | closed | L3, M:two_equal_piles_second, +0.052 (+0.052, z 3.29), 0.448 vs 0.5 | +0.04 / +0.03 / +0.04 / +0.05 / +0.03 / +0.03 / +0.01 | - |
| R1.one_culprit | unchanged | closed | L6, F:most_mentioned, +0.132 (+0.132, z 11.92), 0.2747 vs 0.1429 | +0.08 / +0.07 / +0.09 / +0.08 / +0.12 / +0.10 / +0.13 | - |
| R1.order_compare_r4 | rev4 | closed | L1, M:always_cbd, +0.024 (+0.024, z 1.59), 0.357 vs 0.3333 | +0.00 / +0.02 / +0.02 / +0.01 / +0.01 / +0.01 / +0.01 | - |
| R1.order_extreme | unchanged | closed | L6, F:least_mentioned, +0.389 (+0.389, z 39.13), 0.5 vs 0.1111 | +0.17 / +0.25 / +0.30 / +0.33 / +0.36 / +0.38 / +0.39 | - |
| R1.order_tournament_wins | unchanged | closed | L0, F:alphabetical_last, +0.083 (+0.083, z 6.09), 0.0 vs 0.25 | +0.08 / +0.05 / +0.05 / +0.03 / +0.03 / +0.02 / +0.02 | - |
| R1.pet_owners | unchanged | closed | L1, F:alphabetical_last, +0.021 (+0.021, z 1.53), 0.271 vs 0.25 | +0.01 / +0.02 / +0.02 / +0.01 / +0.02 / +0.02 / +0.01 | - |
| R1.road_reachability | unchanged | closed | L2, constant_most_frequent_key, +0.040 (+0.040, z 2.53), 0.54 vs 0.5 | +0.03 / +0.02 / +0.04 / +0.02 / +0.03 / +0.03 / +0.03 | - |
| R1.seating_row | unchanged | closed | L2, F:last_mentioned, +0.014 (+0.014, z 1.11), 0.214 vs 0.2 | +0.01 / +0.01 / +0.01 / +0.01 / +0.01 / +0.00 / +0.00 | - |
| R1.spatial_grid_walk_r2 | unchanged | closed | L0, M:ignore_walls, +0.652 (+0.742, z 65.38), 0.8716 vs 0.1301 | +0.65 / +0.62 / +0.58 / +0.56 / +0.55 / +0.52 / +0.49 | - |
| R1.spatial_relative_directions_r4 | rev4 | open | L0, X:sum_of_two_largest_offsets, +0.043 (+0.043, z 4.9), 0.127 vs 0.084 | +0.04 / +0.00 / -0.01 / +0.00 / -0.01 / -0.01 / -0.01 | - |
| R1.stable_matching_r4 | rev4 | closed | L4, M:receiver_optimal_partner, +0.516 (+0.516, z 40.79), 0.716 vs 0.2 | +0.46 / +0.51 / +0.51 / +0.51 / +0.52 / +0.51 / +0.51 | - |
| R1.swap_tracking | unchanged | closed | L0, own_initial_item, +0.033 (+0.033, z 2.19), 0.366 vs 0.3333 | +0.03 / +0.02 / +0.02 / +0.02 / +0.01 / +0.01 / +0.02 | - |
| R1.temporal_critical_path_r4 | rev4 | open | L0, largest_number, +0.002 (+0.002, z 0.28), 0.058 vs 0.056 | +0.00 / -0.01 / +0.00 / -0.00 / -0.01 / +0.00 / -0.01 | - |
| R1.temporal_interval_overlap | unchanged | closed | L0, constant_most_frequent_key, +0.162 (+0.162, z 10.25), 0.662 vs 0.5 | +0.16 / +0.07 / +0.06 / +0.01 / +0.01 / +0.01 / +0.01 | - |
| R1.temporal_weekday_shift | unchanged | closed | L6, constant_most_frequent_key, +0.039 (+0.039, z 3.54), 0.182 vs 0.1429 | +0.03 / +0.01 / +0.01 / +0.00 / +0.02 / +0.01 / +0.04 | - |
| R1.topological_order_r4 | rev4 | closed | L0, M:sort_by_depth_then_name, +0.677 (+0.677, z 57.47), 0.844 vs 0.1667 | +0.68 / +0.65 / +0.59 / +0.54 / +0.50 / +0.47 / +0.44 | - |
| R1.tracking_accounts | unchanged | closed | L6, M:received_minus_given_events, +0.418 (+0.418, z 35.48), 0.5848 vs 0.1667 | +0.36 / +0.37 / +0.37 / +0.37 / +0.40 / +0.38 / +0.42 | - |
| R1.venn_counting_r4 | rev4 | open | L1, constant_most_frequent_key, +0.000 (+0.000, z 0.0), 0.092 vs 0.092 | -0.01 / +0.00 / -0.00 / -0.01 / -0.01 / -0.00 / -0.01 | M:forget_triple L0; M:sign_error_triple_added L0; PROCEDURE_CHECK:inclusion_exclusion L0; PROCEDURE_CHECK:inclusion_exclusion L2; X:forget_the_triples L0; X:total_minus_sizes_plus_pairs_minus_triples L0; X:total_minus_sizes_plus_pairs_minus_triples L2 |
