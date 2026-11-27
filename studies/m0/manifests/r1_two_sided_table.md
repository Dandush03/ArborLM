# R1 two-sided shortcut reading (measured, not thresholded)

Ruling 2 of 2025-11-25: a heuristic pushed clearly below chance is as exploitable as one above it. Closed answers: each heuristic's accuracy minus chance, and the accuracy of picking uniformly among the options the heuristic did NOT choose, minus chance. Open answers (ruling 5): the heuristic's absolute exact-match rate beside the most-frequent-answer rate and the exact-match rate per level (never 'excess over chance'). Rows are the registered lineages and the superseded shapes, so the retuned revisions can be read beside the shapes they replace. A heuristic that names an option the item does not offer does not fire.

| id | answers | chance | heuristic (largest two-sided departure) | accuracy | accuracy - chance | anti accuracy - chance | most-frequent-answer rate | per-level accuracy (levels 1-5) |
|---|---|---|---|---|---|---|---|---|
| R1.activity_selection | open | n/a | greedy_by_start | exact-match rate 0.2555 | n/a | n/a | 0.2075 | 0.4025 / 0.3425 / 0.22 / 0.1725 / 0.14 |
| R1.attribute_rule | closed (k about 6.8) | 0.1519 | constant_most_frequent_key | 0.1603 | +0.0083 | -0.0014 | 0.018 | 0.2065 / 0.1733 / 0.1514 / 0.135 / 0.135 |
| R1.boolean_lights | closed (k about 2.0) | 0.5 | never_toggled_means_initial | 0.6095 | +0.1095 | -0.1095 | 0.5285 | 0.6512 / 0.62 / 0.605 / 0.575 / 0.5962 |
| R1.boolean_lights_r2 | closed (k about 2.0) | 0.5 | initial_state | 0.4505 | -0.0495 | +0.0495 | 0.5215 | 0.415 / 0.4325 / 0.4075 / 0.505 / 0.4925 |
| R1.categories_default_exceptions | closed (k about 2.0) | 0.5 | majority_sign | 0.8475 | +0.3475 | -0.3475 | 0.5035 | 0.8938 / 0.8325 / 0.865 / 0.805 / 0.8413 |
| R1.categories_default_exceptions_r2 | closed (k about 2.0) | 0.5 | least_specific_rule | 0.012 | -0.488 | +0.488 | 0.5015 | 0.0 / 0.0075 / 0.01 / 0.02 / 0.0225 |
| R1.categories_default_exceptions_r3 | closed (k about 2.0) | 0.5 | last_listed | 0.4885 | -0.0115 | +0.0115 | 0.508 | 0.51 / 0.4675 / 0.465 / 0.48 / 0.52 |
| R1.categories_follow | closed (k about 3.0) | 0.3333 | constant_most_frequent_key | 0.775 | +0.4417 | -0.2208 | 0.775 | 0.775 / 0.7525 / 0.765 / 0.76 / 0.8225 |
| R1.categories_follow_r2 | closed (k about 3.0) | 0.3333 | constant_most_frequent_key | 0.398 | +0.0647 | -0.0323 | 0.398 | 0.43 / 0.4175 / 0.4 / 0.3825 / 0.36 |
| R1.compass_turns | closed (k about 4.0) | 0.25 | constant_most_frequent_key | 0.259 | +0.009 | -0.003 | 0.259 | 0.255 / 0.25 / 0.275 / 0.2375 / 0.2775 |
| R1.conditional_chain | closed (k about 3.0) | 0.3333 | constant_most_frequent_key | 0.365 | +0.0317 | -0.0158 | 0.365 | 0.465 / 0.345 / 0.42 / 0.305 / 0.29 |
| R1.conditional_decision_tree | closed (k about 4.21) | 0.26 | most_mentioned | 0.409 | +0.1491 | -0.0695 | 0.109 | 0.595 / 0.435 / 0.391 / 0.3254 / 0.2988 |
| R1.conditional_threshold_rule | closed (k about 2.0) | 0.5 | veto_no_means_no | 0.6633 | +0.1633 | -0.1633 | 0.62 | 0.6138 / 0.6275 / 0.6837 / 0.695 / 0.6963 |
| R1.conditional_threshold_rule_r2 | closed (k about 2.0) | 0.5 | yes_count_majority | 0.5587 | +0.0587 | -0.0588 | 0.5075 | 0.48 / 0.5663 / 0.5775 / 0.5825 / 0.5875 |
| R1.conditional_threshold_rule_r3 | closed (k about 2.0) | 0.5 | constant_most_frequent_key | 0.5275 | +0.0275 | -0.0275 | 0.5275 | 0.495 / 0.5225 / 0.545 / 0.53 / 0.545 |
| R1.containers_queue_line | closed (k about 8.76) | 0.1268 | last_joiner_or_last_cutter | 0.6852 | +0.5584 | -0.0768 | 0.014 | 0.6654 / 0.6796 / 0.693 / 0.7046 / 0.6835 |
| R1.containers_queue_line_r2 | closed (k about 7.97) | 0.1343 | least_mentioned | 0.1749 | +0.0406 | -0.1059 | 0.0135 | 0.2307 / 0.1883 / 0.1696 / 0.1495 / 0.1363 |
| R1.containers_stack_piles | closed (k about 7.0) | 0.1491 | last_block_moved_onto_asked | 0.5576 | +0.4085 | -0.0726 | 0.0485 | 0.6275 / 0.5842 / 0.4993 / 0.5663 / 0.5108 |
| R1.containers_stack_piles_r2 | closed (k about 7.0) | 0.1491 | last_block_moved_onto_asked | 0.2023 | +0.0531 | -0.0089 | 0.0495 | 0.225 / 0.2246 / 0.2121 / 0.1641 / 0.1856 |
| R1.containers_stack_piles_r3 | closed (k about 7.0) | 0.1491 | constant_most_frequent_key | 0.1586 | +0.0094 | -0.0016 | 0.055 | 0.211 / 0.1679 / 0.1575 / 0.1272 / 0.1292 |
| R1.elimination_bracket | closed (k about 6.4) | 0.175 | runner_up_is_best_of_other_half | 0.5946 | +0.4196 | -0.0879 | 0.0135 | 0.6288 / 0.6062 / 0.5778 / 0.5778 / 0.5822 |
| R1.elimination_bracket_r2 | closed (k about 5.6) | 0.2 | most_wins_logic | 0.125 | -0.075 | +0.0201 | 0.013 | 0.175 / 0.165 / 0.1625 / 0.06 / 0.0625 |
| R1.elimination_bracket_r3 | closed (k about 5.6) | 0.2 | most_wins_logic | 0.188 | -0.012 | +0.0011 | 0.0135 | 0.2625 / 0.27 / 0.2325 / 0.1075 / 0.0675 |
| R1.elimination_josephus | closed (k about 7.0) | 0.1491 | constant_most_frequent_key | 0.1535 | +0.0044 | -0.0009 | 0.0135 | 0.206 / 0.1792 / 0.1432 / 0.1216 / 0.1175 |
| R1.equivalence_classes | closed (k about 3.0) | 0.3333 | asked_pair_stated_verbatim | 0.6557 | +0.3223 | -0.1612 | 0.37 | 0.665 / 0.6083 / 0.6683 / 0.6733 / 0.6633 |
| R1.equivalence_classes_r2 | closed (k about 3.0) | 0.3333 | constant_most_frequent_key | 0.3595 | +0.0262 | -0.0131 | 0.3595 | 0.4025 / 0.3525 / 0.3475 / 0.385 / 0.31 |
| R1.equivalence_exchange_rates | closed (k about 6.0) | 0.1769 | constant_most_frequent_key | 0.1885 | +0.0116 | -0.0021 | 0.057 | 0.25 / 0.201 / 0.1875 / 0.1832 / 0.1209 |
| R1.event_timeline | closed (k about 6.0) | 0.1769 | constant_most_frequent_key | 0.1042 | -0.0727 | +0.0185 | 0.066 | 0.115 / 0.099 / 0.1163 / 0.0946 / 0.0963 |
| R1.graph_bipartite | closed (k about 2.0) | 0.5 | constant_most_frequent_key | 0.504 | +0.004 | -0.004 | 0.504 | 0.53 / 0.54 / 0.485 / 0.525 / 0.44 |
| R1.graph_shortest_route | closed (k about 5.8) | 0.1752 | nearest_neighbour_of_start | 0.7025 | +0.5273 | -0.1123 | 0.0505 | 0.7125 / 0.7325 / 0.695 / 0.69 / 0.6825 |
| R1.graph_shortest_route_r2 | open | n/a | constant_most_frequent_key | exact-match rate 0.0595 | n/a | n/a | 0.0595 | 0.05 / 0.065 / 0.055 / 0.0625 / 0.065 |
| R1.instant_runoff | closed (k about 3.6) | 0.2833 | plurality_winner | 0.3509 | +0.0676 | -0.0373 | 0.0135 | 0.53 / 0.4325 / 0.2562 / 0.2938 / 0.2421 |
| R1.instant_runoff_r2 | closed (k about 3.6) | 0.2833 | plurality_winner | 0.3049 | +0.0216 | -0.0172 | 0.0145 | 0.4375 / 0.4225 / 0.2171 / 0.2371 / 0.2104 |
| R1.kinship_ancestor | closed (k about 8.8) | 0.1208 | parentless_person | 1.0 | +0.8792 | -0.1208 | 0.0135 | 1.0 / 1.0 / 1.0 / 1.0 / 1.0 |
| R1.kinship_ancestor_r2 | closed (k about 10.33) | 0.1015 | parentless_person | 0.0 | -0.1015 | +0.0122 | 0.014 | 0.0 / 0.0 / 0.0 / 0.0 / 0.0 |
| R1.kinship_ancestor_r3 | closed (k about 10.29) | 0.1018 | parentless_person | 0.0 | -0.1018 | +0.0122 | 0.0145 | 0.0 / 0.0 / 0.0 / 0.0 / 0.0 |
| R1.kinship_cousins | closed (k about 2.0) | 0.5 | constant_most_frequent_key | 0.5045 | +0.0045 | -0.0045 | 0.5045 | 0.52 / 0.47 / 0.5275 / 0.4725 / 0.5325 |
| R1.kinship_descendants | closed (k about 8.0) | 0.1291 | parentless_person | 0.9465 | +0.8174 | -0.1215 | 0.013 | 0.9625 / 0.9575 / 0.95 / 0.9275 / 0.935 |
| R1.kinship_descendants_r2 | closed (k about 7.0) | 0.1491 | least_mentioned | 0.0 | -0.1491 | +0.1648 | 0.0125 | 0.0 / 0.0 / 0.0 / 0.0 / 0.0 |
| R1.kinship_descendants_r3 | closed (k about 7.0) | 0.1491 | least_mentioned | 0.0 | -0.1491 | +0.1723 | 0.0125 | 0.0 / 0.0 / 0.0 / 0.0 / 0.0 |
| R1.knights_knaves | closed (k about 2.0) | 0.5 | constant_most_frequent_key | 0.518 | +0.018 | -0.018 | 0.518 | 0.5425 / 0.5325 / 0.4825 / 0.5325 / 0.5 |
| R1.minimax_tree | open | n/a | smallest_number | exact-match rate 0.159 | n/a | n/a | 0.0905 | 0.1725 / 0.185 / 0.15 / 0.115 / 0.1725 |
| R1.mst_cost | open | n/a | smallest_n_minus_1_roads | exact-match rate 0.0565 | n/a | n/a | 0.037 | 0.085 / 0.0675 / 0.0475 / 0.0525 / 0.03 |
| R1.nim_xor | closed (k about 2.0) | 0.5 | constant_most_frequent_key | 0.506 | +0.006 | -0.006 | 0.506 | 0.5175 / 0.4975 / 0.5025 / 0.5175 / 0.495 |
| R1.one_culprit | closed (k about 5.2) | 0.1967 | constant_most_frequent_key | 0.2021 | +0.0054 | -0.0015 | 0.0145 | 0.265 / 0.2015 / 0.204 / 0.1688 / 0.1713 |
| R1.order_compare | closed (k about 3.0) | 0.3333 | asked_pair_stated_verbatim | 0.42 | +0.0867 | -0.0433 | 0.346 | 0.4575 / 0.405 / 0.3958 / 0.4342 / 0.4075 |
| R1.order_extreme | closed (k about 6.0) | 0.1769 | constant_most_frequent_key | 0.182 | +0.0051 | -0.0012 | 0.015 | 0.2525 / 0.2105 / 0.1746 / 0.1479 / 0.1247 |
| R1.order_tournament_wins | closed (k about 5.8) | 0.1752 | constant_most_frequent_key | 0.1793 | +0.0041 | -0.0008 | 0.0135 | 0.2065 / 0.1955 / 0.1787 / 0.1737 / 0.1421 |
| R1.pet_owners | closed (k about 5.4) | 0.19 | constant_most_frequent_key | 0.1956 | +0.0056 | -0.0015 | 0.0145 | 0.2644 / 0.1995 / 0.1688 / 0.1771 / 0.1683 |
| R1.road_reachability | closed (k about 2.0) | 0.5 | asked_entity_never_mentioned | 0.5302 | +0.0302 | -0.0302 | 0.505 | 0.5288 / 0.5363 / 0.5275 / 0.5275 / 0.5312 |
| R1.seating_row | closed (k about 5.2) | 0.1967 | constant_most_frequent_key | 0.201 | +0.0043 | -0.0008 | 0.014 | 0.245 / 0.2015 / 0.2105 / 0.1704 / 0.1775 |
| R1.spatial_grid_walk | closed (k about 12.44) | 0.0884 | last_mentioned | 0.1495 | +0.0611 | -0.007 | 0.002 | 0.2125 / 0.1775 / 0.14 / 0.115 / 0.1025 |
| R1.spatial_grid_walk_r2 | closed (k about 12.42) | 0.0884 | last_mentioned | 0.159 | +0.0706 | -0.0076 | 0.002 | 0.2025 / 0.1725 / 0.1475 / 0.155 / 0.1175 |
| R1.spatial_relative_directions | closed (k about 5.0) | 0.2186 | most_mentioned | 0.0651 | -0.1535 | +0.0948 | 0.051 | 0.1367 / 0.0892 / 0.0451 / 0.0369 / 0.0177 |
| R1.stable_matching | closed (k about 4.2) | 0.2467 | first_choice | 0.3555 | +0.1088 | -0.034 | 0.0155 | 0.405 / 0.33 / 0.36 / 0.3275 / 0.355 |
| R1.stable_matching_r2 | closed (k about 4.2) | 0.2467 | first_mentioned | 0.1425 | -0.1042 | +0.0375 | 0.0145 | 0.1825 / 0.1225 / 0.1425 / 0.115 / 0.15 |
| R1.swap_tracking | closed (k about 5.4) | 0.19 | first_mentioned | 0.175 | -0.015 | +0.0025 | 0.0535 | 0.2825 / 0.165 / 0.1475 / 0.13 / 0.15 |
| R1.temporal_critical_path | closed (k about 6.0) | 0.1769 | longest_job | 0.0883 | -0.0886 | +0.0234 | 0.0145 | 0.1531 / 0.0925 / 0.0808 / 0.0614 / 0.0537 |
| R1.temporal_interval_overlap | closed (k about 2.0) | 0.5 | constant_most_frequent_key | 0.5305 | +0.0305 | -0.0305 | 0.5305 | 0.5025 / 0.58 / 0.5575 / 0.52 / 0.4925 |
| R1.temporal_weekday_shift | closed (k about 7.0) | 0.1429 | anchor_weekday | 0.1365 | -0.0064 | +0.0011 | 0.149 | 0.1475 / 0.13 / 0.15 / 0.11 / 0.145 |
| R1.topological_order | closed (k about 7.0) | 0.1491 | jth_alphabetical | 0.078 | -0.0711 | +0.013 | 0.015 | 0.1125 / 0.0925 / 0.0725 / 0.06 / 0.0525 |
| R1.topological_order_r2 | closed (k about 7.0) | 0.1491 | most_mentioned | 0.1238 | -0.0254 | +0.0047 | 0.0145 | 0.1412 / 0.1462 / 0.1228 / 0.1077 / 0.1008 |
| R1.tracking_accounts | closed (k about 4.8) | 0.2133 | richest_or_poorest_at_start | 0.3415 | +0.1281 | -0.0474 | 0.015 | 0.4296 / 0.4058 / 0.3402 / 0.302 / 0.2298 |
| R1.venn_counting | open | n/a | constant_most_frequent_key | exact-match rate 0.0895 | n/a | n/a | 0.0895 | 0.0925 / 0.1075 / 0.1 / 0.0675 / 0.08 |
