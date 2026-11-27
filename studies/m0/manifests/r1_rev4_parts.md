# R1: the split of the strict clusters under each partition reading (ruling R-6; REPORTED, NOT CHOSEN)

27 strict clusters (43 registered shapes in the revision-4 set). Rule for every reading: sorted keys shuffled with stream(400004, "family-partition", "R1"), first half A. Whether a held-out part may contain a cluster whose procedure also sits in the teaching part is a question for the human lead (ruling R-7).

| reading | keys | shapes A / B | clusters wholly A | wholly B | in BOTH parts | families split across parts |
|---|---|---|---|---|---|---|
| literal | 22 | 21 / 22 | 9 | 10 | 8 | 0 |
| family_closure | 10 | 10 / 33 | 8 | 19 | 0 | 0 |
| cluster_keys | 27 | 16 / 27 | 13 | 14 | 0 | 7 |
| literal_move_to_B | 22 | 9 / 34 | 9 | 18 | 0 | 4 |

## literal

- wholly A (9): elimination_bracket, instant_runoff, kinship_descendants, mst_cost, nim_xor, swap_tracking, temporal_critical_path, temporal_interval_overlap, tracking_accounts
- wholly B (10): activity_selection, conditional_chain, conditional_threshold_rule, containers_stack_piles, graph_bipartite, graph_shortest_route, pet_owners, spatial_grid_walk, stable_matching, venn_counting
- in BOTH parts (8):
  - attribute_rule: attribute_rule (A), conditional_decision_tree_r4 (B), minimax_tree_r4 (A)
  - boolean_lights: boolean_lights_r4 (A), compass_turns (B)
  - categories_default_exceptions: categories_default_exceptions_r4 (B), kinship_ancestor_r4 (A), kinship_cousins (A)
  - categories_follow: categories_follow_r4 (B), equivalence_classes_r2 (B), order_compare_r4 (A), road_reachability (B)
  - containers_queue_line: containers_queue_line_r2 (B), elimination_josephus (A)
  - equivalence_exchange_rates: equivalence_exchange_rates (B), event_timeline (A), spatial_relative_directions_r4 (B), temporal_weekday_shift (A)
  - knights_knaves: knights_knaves (B), one_culprit (A)
  - order_extreme: order_extreme (A), order_tournament_wins (A), topological_order_r4 (B)

## family_closure

- wholly A (8): containers_queue_line, containers_stack_piles, elimination_bracket, instant_runoff, mst_cost, pet_owners, swap_tracking, tracking_accounts
- wholly B (19): activity_selection, attribute_rule, boolean_lights, categories_default_exceptions, categories_follow, conditional_chain, conditional_threshold_rule, equivalence_exchange_rates, graph_bipartite, graph_shortest_route, kinship_descendants, knights_knaves, nim_xor, order_extreme, spatial_grid_walk, stable_matching, temporal_critical_path, temporal_interval_overlap, venn_counting
- in BOTH parts: none

## cluster_keys

- wholly A (13): activity_selection, conditional_chain, containers_queue_line, containers_stack_piles, graph_shortest_route, instant_runoff, mst_cost, nim_xor, order_extreme, spatial_grid_walk, temporal_critical_path, temporal_interval_overlap, venn_counting
- wholly B (14): attribute_rule, boolean_lights, categories_default_exceptions, categories_follow, conditional_threshold_rule, elimination_bracket, equivalence_exchange_rates, graph_bipartite, kinship_descendants, knights_knaves, pet_owners, stable_matching, swap_tracking, tracking_accounts
- in BOTH parts: none
- families with shapes in both parts: conditional, elimination, games, graph, order, spatial, temporal

## literal_move_to_B

- wholly A (9): elimination_bracket, instant_runoff, kinship_descendants, mst_cost, nim_xor, swap_tracking, temporal_critical_path, temporal_interval_overlap, tracking_accounts
- wholly B (18): activity_selection, attribute_rule, boolean_lights, categories_default_exceptions, categories_follow, conditional_chain, conditional_threshold_rule, containers_queue_line, containers_stack_piles, equivalence_exchange_rates, graph_bipartite, graph_shortest_route, knights_knaves, order_extreme, pet_owners, spatial_grid_walk, stable_matching, venn_counting
- in BOTH parts: none
- families with shapes in both parts: elimination, games, kinship, temporal
