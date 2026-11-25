# R1 revision-4 capacity on structure (MEASURED by exhibition; names, setting and presentation order do not count)

Required distinct structures = 10 x (ceil(24,000 / G) + 100) on core levels 1-5, 10 x 100 on reserve levels 0 and 6 (derivation in the module docstring of `r1_rev4_capacity.py`). G = 13 gives 19,470 on a core level; G = 8 gives 31,000.

## Scenario G13: G = 13 (core-level requirement 19,470)

### Clusters that fail (sum over their shapes' exhibited structures, an upper bound)

| cluster | level | need | cluster sum | best single shape |
|---|---|---|---|---|
| R1.containers_queue_line | 0 | 1,000 | 532 | 500 |
| R1.containers_queue_line | 1 | 19,470 | 2,105 | 2,065 |
| R1.containers_queue_line | 2 | 19,470 | 6,797 | 6,750 |
| R1.containers_queue_line | 3 | 19,470 | 12,069 | 12,035 |
| R1.graph_bipartite | 0 | 1,000 | 110 | 110 |
| R1.graph_bipartite | 1 | 19,470 | 1,614 | 1,614 |
| R1.graph_bipartite | 2 | 19,470 | 16,473 | 16,473 |

### Single shapes below the whole-cluster requirement (least favourable: one shape carries its cluster)

| shape | level | need | exhibited | draws |
|---|---|---|---|---|
| R1.containers_queue_line_r2 | 0 | 1,000 | 500 | 5,000 |
| R1.containers_queue_line_r2 | 1 | 19,470 | 2,065 | 95,000 |
| R1.containers_queue_line_r2 | 2 | 19,470 | 6,750 | 95,000 |
| R1.containers_queue_line_r2 | 3 | 19,470 | 12,035 | 95,000 |
| R1.elimination_josephus | 0 | 1,000 | 32 | 5,000 |
| R1.elimination_josephus | 1 | 19,470 | 40 | 95,000 |
| R1.elimination_josephus | 2 | 19,470 | 47 | 95,000 |
| R1.elimination_josephus | 3 | 19,470 | 34 | 95,000 |
| R1.elimination_josephus | 4 | 19,470 | 33 | 95,000 |
| R1.elimination_josephus | 5 | 19,470 | 36 | 95,000 |
| R1.elimination_josephus | 6 | 1,000 | 40 | 5,000 |
| R1.equivalence_classes_r2 | 1 | 19,470 | 11,315 | 95,000 |
| R1.graph_bipartite | 0 | 1,000 | 110 | 5,000 |
| R1.graph_bipartite | 1 | 19,470 | 1,614 | 95,000 |
| R1.graph_bipartite | 2 | 19,470 | 16,473 | 95,000 |
| R1.kinship_cousins | 0 | 1,000 | 368 | 5,000 |
| R1.kinship_cousins | 1 | 19,470 | 372 | 95,000 |
| R1.kinship_cousins | 2 | 19,470 | 1,214 | 95,000 |
| R1.kinship_cousins | 3 | 19,470 | 1,213 | 95,000 |
| R1.kinship_cousins | 4 | 19,470 | 2,870 | 95,000 |
| R1.kinship_cousins | 5 | 19,470 | 2,877 | 95,000 |
| R1.knights_knaves | 0 | 1,000 | 52 | 5,000 |
| R1.knights_knaves | 1 | 19,470 | 5,780 | 95,000 |
| R1.knights_knaves | 2 | 19,470 | 5,740 | 95,000 |
| R1.order_extreme | 0 | 1,000 | 2 | 5,000 |
| R1.order_extreme | 1 | 19,470 | 2 | 95,000 |
| R1.order_extreme | 2 | 19,470 | 2 | 95,000 |
| R1.order_extreme | 3 | 19,470 | 2 | 95,000 |
| R1.order_extreme | 4 | 19,470 | 2 | 95,000 |
| R1.order_extreme | 5 | 19,470 | 2 | 95,000 |
| R1.order_extreme | 6 | 1,000 | 2 | 5,000 |
| R1.order_tournament_wins | 0 | 1,000 | 4 | 5,000 |
| R1.order_tournament_wins | 1 | 19,470 | 14 | 95,000 |
| R1.order_tournament_wins | 2 | 19,470 | 14 | 95,000 |
| R1.order_tournament_wins | 3 | 19,470 | 68 | 95,000 |
| R1.order_tournament_wins | 4 | 19,470 | 68 | 95,000 |
| R1.order_tournament_wins | 5 | 19,470 | 524 | 95,000 |
| R1.order_tournament_wins | 6 | 1,000 | 522 | 5,000 |
| R1.pet_owners | 0 | 1,000 | 655 | 5,000 |
| R1.seating_row | 0 | 1,000 | 521 | 5,000 |

## Scenario G8: G = 8 (core-level requirement 31,000)

### Clusters that fail (sum over their shapes' exhibited structures, an upper bound)

| cluster | level | need | cluster sum | best single shape |
|---|---|---|---|---|
| R1.containers_queue_line | 0 | 1,000 | 532 | 500 |
| R1.containers_queue_line | 1 | 31,000 | 2,105 | 2,065 |
| R1.containers_queue_line | 2 | 31,000 | 6,797 | 6,750 |
| R1.containers_queue_line | 3 | 31,000 | 12,069 | 12,035 |
| R1.containers_queue_line | 4 | 31,000 | 23,715 | 23,682 |
| R1.graph_bipartite | 0 | 1,000 | 110 | 110 |
| R1.graph_bipartite | 1 | 31,000 | 1,614 | 1,614 |
| R1.graph_bipartite | 2 | 31,000 | 16,473 | 16,473 |

### Single shapes below the whole-cluster requirement (least favourable: one shape carries its cluster)

| shape | level | need | exhibited | draws |
|---|---|---|---|---|
| R1.containers_queue_line_r2 | 0 | 1,000 | 500 | 5,000 |
| R1.containers_queue_line_r2 | 1 | 31,000 | 2,065 | 95,000 |
| R1.containers_queue_line_r2 | 2 | 31,000 | 6,750 | 95,000 |
| R1.containers_queue_line_r2 | 3 | 31,000 | 12,035 | 95,000 |
| R1.containers_queue_line_r2 | 4 | 31,000 | 23,682 | 95,000 |
| R1.elimination_josephus | 0 | 1,000 | 32 | 5,000 |
| R1.elimination_josephus | 1 | 31,000 | 40 | 95,000 |
| R1.elimination_josephus | 2 | 31,000 | 47 | 95,000 |
| R1.elimination_josephus | 3 | 31,000 | 34 | 95,000 |
| R1.elimination_josephus | 4 | 31,000 | 33 | 95,000 |
| R1.elimination_josephus | 5 | 31,000 | 36 | 95,000 |
| R1.elimination_josephus | 6 | 1,000 | 40 | 5,000 |
| R1.equivalence_classes_r2 | 1 | 31,000 | 11,315 | 95,000 |
| R1.graph_bipartite | 0 | 1,000 | 110 | 5,000 |
| R1.graph_bipartite | 1 | 31,000 | 1,614 | 95,000 |
| R1.graph_bipartite | 2 | 31,000 | 16,473 | 95,000 |
| R1.kinship_cousins | 0 | 1,000 | 368 | 5,000 |
| R1.kinship_cousins | 1 | 31,000 | 372 | 95,000 |
| R1.kinship_cousins | 2 | 31,000 | 1,214 | 95,000 |
| R1.kinship_cousins | 3 | 31,000 | 1,213 | 95,000 |
| R1.kinship_cousins | 4 | 31,000 | 2,870 | 95,000 |
| R1.kinship_cousins | 5 | 31,000 | 2,877 | 95,000 |
| R1.knights_knaves | 0 | 1,000 | 52 | 5,000 |
| R1.knights_knaves | 1 | 31,000 | 5,780 | 95,000 |
| R1.knights_knaves | 2 | 31,000 | 5,740 | 95,000 |
| R1.one_culprit | 1 | 31,000 | 30,135 | 95,000 |
| R1.order_extreme | 0 | 1,000 | 2 | 5,000 |
| R1.order_extreme | 1 | 31,000 | 2 | 95,000 |
| R1.order_extreme | 2 | 31,000 | 2 | 95,000 |
| R1.order_extreme | 3 | 31,000 | 2 | 95,000 |
| R1.order_extreme | 4 | 31,000 | 2 | 95,000 |
| R1.order_extreme | 5 | 31,000 | 2 | 95,000 |
| R1.order_extreme | 6 | 1,000 | 2 | 5,000 |
| R1.order_tournament_wins | 0 | 1,000 | 4 | 5,000 |
| R1.order_tournament_wins | 1 | 31,000 | 14 | 95,000 |
| R1.order_tournament_wins | 2 | 31,000 | 14 | 95,000 |
| R1.order_tournament_wins | 3 | 31,000 | 68 | 95,000 |
| R1.order_tournament_wins | 4 | 31,000 | 68 | 95,000 |
| R1.order_tournament_wins | 5 | 31,000 | 524 | 95,000 |
| R1.order_tournament_wins | 6 | 1,000 | 522 | 5,000 |
| R1.pet_owners | 0 | 1,000 | 655 | 5,000 |
| R1.seating_row | 0 | 1,000 | 521 | 5,000 |
| R1.seating_row | 1 | 31,000 | 24,676 | 95,000 |

