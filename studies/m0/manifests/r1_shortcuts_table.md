# R1 shortcut gate (measured, not thresholded)

Per lineage: the worst heuristic of the battery of `lineages_r1_shortcuts.py` on 2,000 items (400 per core level), excess = accuracy minus mean chance 1/k (open answers: chance 0). A heuristic that does not fire guesses at chance. Lineage-specific heuristics read the structured form.

| id | chance | worst heuristic (largest excess above chance) | accuracy | excess over chance | fires | worst level (excess) | note |
|---|---|---|---|---|---|---|---|
| R1.activity_selection | open | greedy_by_start | exact-match rate 0.2555 (most-frequent answer 0.2075) | n/a (open answer) | 2000 | per level: {'1': 0.4025, '2': 0.3425, '3': 0.22, '4': 0.1725, '5': 0.14} |  |
| R1.attribute_rule | 0.1519 | constant_most_frequent_key | 0.1603 | 0.0083 | 130 | 4 (0.01) |  |
| R1.boolean_lights | 0.5 | never_toggled_means_initial | 0.6095 | 0.1095 | 438 | 1 (0.1512) | superseded |
| R1.boolean_lights_r2 | 0.5 | constant_most_frequent_key | 0.5215 | 0.0215 | 2000 | 1 (0.0325) |  |
| R1.categories_default_exceptions | 0.5 | majority_sign | 0.8475 | 0.3475 | 1578 | 1 (0.3938) | superseded |
| R1.categories_default_exceptions_r2 | 0.5 | constant_most_frequent_key | 0.5015 | 0.0015 | 2000 | 2 (0.0175) | superseded |
| R1.categories_default_exceptions_r3 | 0.5 | constant_most_frequent_key | 0.508 | 0.008 | 2000 | 2 (0.0275) |  |
| R1.categories_follow | 0.3333 | constant_most_frequent_key | 0.775 | 0.4417 | 2000 | 5 (0.4892) | superseded |
| R1.categories_follow_r2 | 0.3333 | constant_most_frequent_key | 0.398 | 0.0647 | 2000 | 1 (0.0967) |  |
| R1.compass_turns | 0.25 | constant_most_frequent_key | 0.259 | 0.009 | 2000 | 5 (0.0275) |  |
| R1.conditional_chain | 0.3333 | constant_most_frequent_key | 0.365 | 0.0317 | 2000 | 1 (0.1317) |  |
| R1.conditional_decision_tree | 0.26 | most_mentioned | 0.409 | 0.1491 | 2000 | 1 (0.2146) |  |
| R1.conditional_threshold_rule | 0.5 | veto_no_means_no | 0.6633 | 0.1633 | 653 | 5 (0.1963) | superseded |
| R1.conditional_threshold_rule_r2 | 0.5 | yes_count_majority | 0.5587 | 0.0587 | 1131 | 5 (0.0875) | superseded |
| R1.conditional_threshold_rule_r3 | 0.5 | constant_most_frequent_key | 0.5275 | 0.0275 | 2000 | 3 (0.045) |  |
| R1.containers_queue_line | 0.1268 | last_joiner_or_last_cutter | 0.6852 | 0.5584 | 1809 | 4 (0.6089) | superseded |
| R1.containers_queue_line_r2 | 0.1343 | least_mentioned | 0.1749 | 0.0406 | 2000 | 1 (0.0468) |  |
| R1.containers_stack_piles | 0.1491 | last_block_moved_onto_asked | 0.5576 | 0.4085 | 1974 | 4 (0.4413) | superseded |
| R1.containers_stack_piles_r2 | 0.1491 | last_block_moved_onto_asked | 0.2023 | 0.0531 | 1939 | 5 (0.0744) | superseded |
| R1.containers_stack_piles_r3 | 0.1491 | constant_most_frequent_key | 0.1586 | 0.0094 | 634 | 5 (0.0181) |  |
| R1.elimination_bracket | 0.175 | runner_up_is_best_of_other_half | 0.5946 | 0.4196 | 1015 | 5 (0.4572) | superseded |
| R1.elimination_bracket_r2 | 0.2 | constant_most_frequent_key | 0.2041 | 0.0041 | 100 | 3 (0.0081) | superseded |
| R1.elimination_bracket_r3 | 0.2 | constant_most_frequent_key | 0.2038 | 0.0038 | 104 | 4 (0.0113) |  |
| R1.elimination_josephus | 0.1491 | constant_most_frequent_key | 0.1535 | 0.0044 | 125 | 2 (0.0125) |  |
| R1.equivalence_classes | 0.3333 | asked_pair_stated_verbatim | 0.6557 | 0.3223 | 967 | 4 (0.34) | superseded |
| R1.equivalence_classes_r2 | 0.3333 | constant_most_frequent_key | 0.3595 | 0.0262 | 2000 | 1 (0.0692) |  |
| R1.equivalence_exchange_rates | 0.1769 | constant_most_frequent_key | 0.1885 | 0.0116 | 543 | 4 (0.0404) |  |
| R1.event_timeline | 0.1769 | constant_most_frequent_key | 0.1042 | -0.0727 | 1333 | 5 (-0.0287) |  |
| R1.graph_bipartite | 0.5 | constant_most_frequent_key | 0.504 | 0.004 | 2000 | 2 (0.04) |  |
| R1.graph_shortest_route | 0.1752 | nearest_neighbour_of_start | 0.7025 | 0.5273 | 2000 | 5 (0.5396) | superseded |
| R1.graph_shortest_route_r2 | open | constant_most_frequent_key | exact-match rate 0.0595 (most-frequent answer 0.0595) | n/a (open answer) | 2000 | per level: {'1': 0.05, '2': 0.065, '3': 0.055, '4': 0.0625, '5': 0.065} |  |
| R1.instant_runoff | 0.2833 | plurality_winner | 0.3509 | 0.0676 | 2000 | 1 (0.1967) | superseded |
| R1.instant_runoff_r2 | 0.2833 | plurality_winner | 0.3049 | 0.0216 | 2000 | 1 (0.1042) |  |
| R1.kinship_ancestor | 0.1208 | parentless_person | 1.0 | 0.8792 | 2000 | 5 (0.9167) | superseded |
| R1.kinship_ancestor_r2 | 0.1015 | first_mentioned | 0.1775 | 0.076 | 2000 | 1 (0.0862) | superseded |
| R1.kinship_ancestor_r3 | 0.1018 | first_mentioned | 0.158 | 0.0562 | 2000 | 1 (0.0787) |  |
| R1.kinship_cousins | 0.5 | constant_most_frequent_key | 0.5045 | 0.0045 | 2000 | 5 (0.0325) |  |
| R1.kinship_descendants | 0.1291 | parentless_person | 0.9465 | 0.8174 | 2000 | 5 (0.835) | superseded |
| R1.kinship_descendants_r2 | 0.1491 | alphabetical_first | 0.157 | 0.0079 | 2000 | 2 (0.0383) | superseded |
| R1.kinship_descendants_r3 | 0.1491 | alphabetical_first | 0.1625 | 0.0134 | 2000 | 3 (0.0271) |  |
| R1.knights_knaves | 0.5 | constant_most_frequent_key | 0.518 | 0.018 | 2000 | 1 (0.0425) |  |
| R1.minimax_tree | open | smallest_number | exact-match rate 0.159 (most-frequent answer 0.0905) | n/a (open answer) | 2000 | per level: {'1': 0.1725, '2': 0.185, '3': 0.15, '4': 0.115, '5': 0.1725} |  |
| R1.mst_cost | open | smallest_n_minus_1_roads | exact-match rate 0.0565 (most-frequent answer 0.037) | n/a (open answer) | 2000 | per level: {'1': 0.085, '2': 0.0675, '3': 0.0475, '4': 0.0525, '5': 0.03} |  |
| R1.nim_xor | 0.5 | constant_most_frequent_key | 0.506 | 0.006 | 2000 | 1 (0.0175) |  |
| R1.one_culprit | 0.1967 | constant_most_frequent_key | 0.2021 | 0.0054 | 92 | 1 (0.015) |  |
| R1.order_compare | 0.3333 | asked_pair_stated_verbatim | 0.42 | 0.0867 | 1067 | 1 (0.1242) |  |
| R1.order_extreme | 0.1769 | constant_most_frequent_key | 0.182 | 0.0051 | 116 | 2 (0.0105) |  |
| R1.order_tournament_wins | 0.1752 | constant_most_frequent_key | 0.1793 | 0.0041 | 108 | 3 (0.0121) |  |
| R1.pet_owners | 0.19 | constant_most_frequent_key | 0.1956 | 0.0056 | 95 | 1 (0.0144) |  |
| R1.road_reachability | 0.5 | asked_entity_never_mentioned | 0.5302 | 0.0302 | 121 | 2 (0.0363) |  |
| R1.seating_row | 0.1967 | constant_most_frequent_key | 0.201 | 0.0043 | 101 | 5 (0.0108) |  |
| R1.spatial_grid_walk | 0.0884 | last_mentioned | 0.1495 | 0.0611 | 2000 | 2 (0.0779) | superseded |
| R1.spatial_grid_walk_r2 | 0.0884 | last_mentioned | 0.159 | 0.0706 | 2000 | 4 (0.0811) |  |
| R1.spatial_relative_directions | 0.2186 | least_mentioned | 0.3522 | 0.1336 | 2000 | 1 (0.1933) |  |
| R1.stable_matching | 0.2467 | first_choice | 0.3555 | 0.1088 | 2000 | 5 (0.155) | superseded |
| R1.stable_matching_r2 | 0.2467 | last_mentioned | 0.2615 | 0.0148 | 2000 | 3 (0.035) |  |
| R1.swap_tracking | 0.19 | constant_most_frequent_key | 0.2003 | 0.0103 | 467 | 3 (0.0217) |  |
| R1.temporal_critical_path | 0.1769 | constant_most_frequent_key | 0.1705 | -0.0064 | 72 | 3 (-0.0042) |  |
| R1.temporal_interval_overlap | 0.5 | constant_most_frequent_key | 0.5305 | 0.0305 | 2000 | 2 (0.08) |  |
| R1.temporal_weekday_shift | 0.1429 | constant_most_frequent_key | 0.149 | 0.0061 | 2000 | 5 (0.0371) |  |
| R1.topological_order | 0.1491 | first_mentioned | 0.161 | 0.0119 | 2000 | 2 (0.0333) | superseded |
| R1.topological_order_r2 | 0.1491 | first_mentioned | 0.158 | 0.0089 | 2000 | 4 (0.0225) |  |
| R1.tracking_accounts | 0.2133 | richest_or_poorest_at_start | 0.3415 | 0.1281 | 2000 | 1 (0.1796) |  |
| R1.venn_counting | open | constant_most_frequent_key | exact-match rate 0.0895 (most-frequent answer 0.0895) | n/a (open answer) | 2000 | per level: {'1': 0.0925, '2': 0.1075, '3': 0.1, '4': 0.0675, '5': 0.08} |  |
