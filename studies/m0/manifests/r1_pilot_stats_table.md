# R1 pilot batch 1: generator statistics for new and existing R1 lineages (measurements, no threshold)

400 items at each of the five core levels per lineage (2,000), test seed block 953601. `top/chance` = the score of always giving the commonest key divided by mean(1/k). `item skel` = distinct item skeletons among the 400 level-3 items (names, numbers, vocabulary abstracted). `sent skel` = distinct sentence skeletons over all 2,000 items. `max sent J` = largest sentence-skeleton Jaccard with any other R1 lineage (new or old). `max op sim` = largest weighted Jaccard of the builders' operation multisets. `cap fail` = levels at which 10 x the G = 300 demand (1,800 core, 1,000 reserve) distinct items were not exhibited.

| id | new | family | top share | chance | top/chance | distinct answers | item skel | sent skel | max sent J (with) | max op sim (with) | cap fail |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R1.attribute_rule | old | rules | 0.014 | 0.1519 | 0.092 | 122 | 400/400 | 2734 | 0.001 (containers_queue_line) | 0.756 (graph_bipartite) | - |
| R1.boolean_lights | new | boolean_state | 0.5125 | 0.5 | 1.025 | 2 | 343/400 | 22 | 0.04 (road_reachability) | 0.757 (conditional_decision_tree) | - |
| R1.categories_default_exceptions | new | categories | 0.5045 | 0.5 | 1.009 | 2 | 367/400 | 22 | 0.04 (road_reachability) | 0.786 (order_tournament_wins) | - |
| R1.categories_follow | old | categories | 0.776 | 0.3333 | 2.328 | 3 | 127/400 | 6 | 0.125 (order_compare) | 0.834 (equivalence_classes) | - |
| R1.compass_turns | old | spatial | 0.269 | 0.25 | 1.076 | 4 | 400/400 | 1964 | 0.0 (tracking_accounts) | 0.714 (elimination_josephus) | - |
| R1.conditional_chain | old | conditional | 0.368 | 0.3333 | 1.104 | 3 | 400/400 | 5120 | 0.0 (order_compare) | 0.71 (graph_shortest_route) | - |
| R1.conditional_decision_tree | new | conditional | 0.107 | 0.2609 | 0.41 | 10 | 400/400 | 2837 | 0.0 (tracking_accounts) | 0.787 (one_culprit) | - |
| R1.conditional_threshold_rule | new | conditional | 0.6255 | 0.5 | 1.251 | 2 | 257/400 | 717 | 0.001 (road_reachability) | 0.77 (temporal_critical_path) | - |
| R1.containers_queue_line | new | containers | 0.0155 | 0.1265 | 0.123 | 122 | 399/400 | 22 | 0.192 (kinship_descendants) | 0.774 (temporal_interval_overlap) | - |
| R1.containers_stack_piles | new | containers | 0.0485 | 0.1491 | 0.325 | 24 | 356/400 | 45 | 0.081 (containers_queue_line) | 0.805 (swap_tracking) | - |
| R1.elimination_bracket | new | elimination | 0.015 | 0.175 | 0.086 | 122 | 2/400 | 7 | 0.0 (tracking_accounts) | 0.757 (order_compare) | - |
| R1.elimination_josephus | new | elimination | 0.0135 | 0.1491 | 0.091 | 122 | 2/400 | 9 | 0.0 (tracking_accounts) | 0.727 (order_extreme) | - |
| R1.equivalence_classes | new | equivalence | 0.3665 | 0.3333 | 1.1 | 3 | 84/400 | 4 | 0.0 (tracking_accounts) | 0.834 (categories_follow) | - |
| R1.equivalence_exchange_rates | new | equivalence | 0.0515 | 0.1769 | 0.291 | 24 | 37/400 | 13 | 0.0 (tracking_accounts) | 0.754 (order_tournament_wins) | - |
| R1.event_timeline | old | temporal | 0.064 | 0.1769 | 0.362 | 18 | 344/400 | 295 | 0.049 (temporal_weekday_shift) | 0.802 (swap_tracking) | - |
| R1.graph_bipartite | new | graph | 0.507 | 0.5 | 1.014 | 2 | 5/400 | 8 | 0.091 (road_reachability) | 0.82 (order_compare) | - |
| R1.graph_shortest_route | new | graph | 0.0505 | 0.1752 | 0.288 | 24 | 5/400 | 6 | 0.176 (spatial_relative_directions) | 0.746 (equivalence_classes) | - |
| R1.kinship_ancestor | old | kinship | 0.014 | 0.1208 | 0.116 | 122 | 398/400 | 132 | 0.044 (kinship_descendants) | 0.788 (order_extreme) | - |
| R1.kinship_cousins | old | kinship | 0.506 | 0.5 | 1.012 | 2 | 15/400 | 5 | 0.167 (kinship_descendants) | 0.873 (order_compare) | - |
| R1.kinship_descendants | new | kinship | 0.0145 | 0.1291 | 0.112 | 122 | 2/400 | 9 | 0.192 (containers_queue_line) | 0.826 (kinship_cousins) | - |
| R1.knights_knaves | old | truth | 0.532 | 0.5 | 1.064 | 2 | 187/400 | 593 | 0.0 (tracking_accounts) | 0.849 (swap_tracking) | - |
| R1.one_culprit | old | culprit | 0.0135 | 0.1967 | 0.069 | 122 | 194/400 | 801 | 0.0 (tracking_accounts) | 0.804 (knights_knaves) | - |
| R1.order_compare | old | order | 0.3505 | 0.3333 | 1.052 | 3 | 2/400 | 3 | 0.125 (categories_follow) | 0.873 (kinship_cousins) | - |
| R1.order_extreme | old | order | 0.0135 | 0.1769 | 0.076 | 122 | 64/400 | 12 | 0.071 (order_compare) | 0.788 (kinship_ancestor) | - |
| R1.order_tournament_wins | new | order | 0.0135 | 0.1752 | 0.077 | 122 | 2/400 | 6 | 0.0 (tracking_accounts) | 0.838 (temporal_critical_path) | - |
| R1.pet_owners | old | arrangement | 0.0135 | 0.19 | 0.071 | 122 | 400/400 | 126 | 0.0 (tracking_accounts) | 0.733 (categories_follow) | - |
| R1.road_reachability | old | graph | 0.5055 | 0.5 | 1.011 | 2 | 15/400 | 4 | 0.125 (kinship_cousins) | 0.759 (spatial_relative_directions) | - |
| R1.seating_row | old | arrangement | 0.0145 | 0.1967 | 0.074 | 122 | 388/400 | 10 | 0.0 (tracking_accounts) | 0.714 (graph_shortest_route) | - |
| R1.spatial_grid_walk | new | spatial | 0.002 | 0.089 | 0.022 | 1788 | 400/400 | 2058 | 0.006 (containers_queue_line) | 0.804 (spatial_relative_directions) | - |
| R1.spatial_relative_directions | new | spatial | 0.0515 | 0.2186 | 0.236 | 24 | 373/400 | 14 | 0.176 (graph_shortest_route) | 0.804 (spatial_grid_walk) | - |
| R1.swap_tracking | old | tracking | 0.0495 | 0.19 | 0.261 | 24 | 208/400 | 27 | 0.083 (tracking_accounts) | 0.849 (knights_knaves) | - |
| R1.temporal_critical_path | new | temporal | 0.013 | 0.1769 | 0.073 | 122 | 400/400 | 678 | 0.0 (tracking_accounts) | 0.838 (order_tournament_wins) | - |
| R1.temporal_interval_overlap | new | temporal | 0.5425 | 0.5 | 1.085 | 2 | 267/400 | 15 | 0.056 (road_reachability) | 0.776 (temporal_weekday_shift) | - |
| R1.temporal_weekday_shift | new | temporal | 0.157 | 0.1429 | 1.099 | 7 | 338/400 | 47 | 0.049 (event_timeline) | 0.776 (temporal_interval_overlap) | - |
| R1.tracking_accounts | new | tracking | 0.0175 | 0.2133 | 0.082 | 122 | 398/400 | 12 | 0.13 (spatial_relative_directions) | 0.763 (swap_tracking) | - |
