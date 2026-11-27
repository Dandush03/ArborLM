# C1 batch 1 shortcut check (measured; 2000 distinct items per lineage and level, seed 953701)

Rates are exact-match accuracies of a rule that does not trace the program. `constant` is the most frequent key of that lineage and level (the reference); `worst rule` is the best single non-constant rule; both are the MAXIMUM over core levels 1-5. `oracle` columns are upper bounds over many guesses (coverage, not one rule). No threshold is registered.

| lineage | constant (core max) | constant (all 7 levels max) | worst rule | accuracy | at level | oracle: any literal | oracle: any list/string statistic | min distinct answers |
|---|---|---|---|---|---|---|---|---|
| C1.bfs_queue | 0.158 | 0.173 | list1_len | 0.108 | 1 | 0.519 | 0.577 | 375 |
| C1.binary_search | 0.082 | 0.094 | lit_min | 0.082 | 1 | 0.243 | 0.035 | 101 |
| C1.bracket_matching | 0.211 | 0.299 | lit_mode | 0.211 | 1 | 0.393 | 0.440 | 20 |
| C1.bytecode_loop | 0.060 | 0.060 | lit_min | 0.060 | 2 | 0.303 | 0.121 | 124 |
| C1.cellular_update | 0.053 | 0.061 | echo_printed_initial | 0.095 | 1 | 0.219 | 0.218 | 80 |
| C1.circle_elimination | 0.117 | 0.124 | lit_min | 0.117 | 1 | 0.378 | 0.225 | 44 |
| C1.coin_change_table | 0.172 | 0.223 | lit_min | 0.141 | 1 | 0.463 | 0.341 | 104 |
| C1.digit_peel | 0.099 | 0.133 | lit_mode | 0.083 | 1 | 0.240 | 0.000 | 450 |
| C1.euclid_gcd | 0.124 | 0.134 | lit_max | 0.046 | 2 | 0.113 | 0.000 | 90 |
| C1.fast_power | 0.114 | 0.120 | lit_mode | 0.115 | 1 | 0.347 | 0.000 | 77 |
| C1.grid_path_table | 0.081 | 0.113 | list1_sum | 0.102 | 1 | 0.212 | 0.249 | 39 |
| C1.insertion_sort | 0.105 | 0.141 | list1_mode | 0.152 | 1 | 0.643 | 0.445 | 680 |
| C1.kadane_scan | 0.042 | 0.042 | list1_sum | 0.102 | 2 | 0.131 | 0.145 | 187 |
| C1.majority_vote_scan | 0.161 | 0.187 | list1_max | 0.119 | 3 | 0.398 | 0.241 | 24 |
| C1.merge_two_sorted | 0.143 | 0.158 | list1_len | 0.128 | 1 | 0.468 | 0.411 | 548 |
| C1.mirror_pointers | 0.105 | 0.179 | str1_first | 0.140 | 1 | 0.179 | 0.157 | 604 |
| C1.partition_pass | 0.087 | 0.110 | echo_printed_initial | 0.087 | 1 | 0.239 | 0.141 | 1217 |
| C1.postfix_evaluation | 0.017 | 0.026 | list1_posum | 0.015 | 1 | 0.077 | 0.065 | 540 |
| C1.recursive_calls | 0.022 | 0.030 | lit_first | 0.011 | 1 | 0.035 | 0.008 | 345 |
| C1.run_length_scan | 0.009 | 0.017 | str1_self | 0.000 | 5 | 0.000 | 0.000 | 1347 |
| C1.shared_lists | 0.044 | 0.044 | list1_last | 0.023 | 2 | 0.141 | 0.134 | 784 |
| C1.sieve_marking | 0.185 | 0.185 | lit_max | 0.044 | 5 | 0.071 | 0.066 | 62 |
| C1.string_pair_table | 0.179 | 0.181 | str1_len | 0.098 | 1 | 0.074 | 0.347 | 89 |
| C1.turtle_walk | 0.135 | 0.188 | lit_max | 0.129 | 3 | 0.433 | 0.595 | 97 |
| C1.union_find_links | 0.062 | 0.062 | lit_min | 0.062 | 3 | 0.257 | 0.251 | 925 |
