# C1 shortcut battery, revision 2 (measured; 2000 distinct items per lineage and level, seed 953801; no threshold registered)

Rules: the batch-1 battery plus the independent auditor's O1, O5, O6, O7 and R.* rules (copied and adapted with attribution, see `c1_shortcut_check_rev2.py`). `rate` is the best single rule's exact-match rate in the worst cell; `const` is the most frequent key of that same cell. A rate of 1.000 is a closed form that answers without tracing (decision reserved to the human lead). Maxima over many rules are optimistic in small cells; the cross-validated O columns are printed beside them.

| lineage | status | worst cell: rule | rate | const in cell | cell n | level | O1 max | O5 max | O7 max | O7 (all rules) max | min distinct keys |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C1.bfs_queue | unchanged (batch 1 or existing) | O.const_2 | 0.490 | 0.490 | 516 | 1 | 0.242 | 0.163 | 0.247 | 0.247 | 374 |
| C1.binary_search | unchanged (batch 1 or existing) | O.const_2 | 0.253 | 0.253 | 652 | 1 | 0.125 | 0.076 | 0.133 | 0.133 | 104 |
| C1.bracket_matching | unchanged (batch 1 or existing) | R.standard_code | 1.000 | 0.202 | 1164 | 1 | 0.247 | 0.251 | 0.247 | 1.000 | 20 |
| C1.bracket_matching_traced | PROPOSED shape (additional) | A.lit_last | 0.301 | 0.301 | 1014 | 2 | 0.188 | 0.176 | 0.188 | 0.188 | 16 |
| C1.bytecode_loop | SUPERSEDED (before) | R.sum_all_args | 0.870 | 0.047 | 1003 | 2 | 0.091 | 0.070 | 0.108 | 0.504 | 127 |
| C1.bytecode_loop_r2 | revised (supersedes bytecode_loop) | O.num[1] | 0.291 | 0.211 | 422 | 3 | 0.111 | 0.092 | 0.118 | 0.155 | 99 |
| C1.cellular_update | SUPERSEDED (before) | O.len_list1_minus1 | 0.107 | 0.107 | 844 | 1 | 0.102 | 0.093 | 0.104 | 0.104 | 80 |
| C1.cellular_update_r2 | revised (supersedes cellular_update) | A.echo_printed_initial | 0.102 | 0.102 | 991 | 2 | 0.082 | 0.090 | 0.082 | 0.082 | 80 |
| C1.circle_elimination | SUPERSEDED (before) | R.first_live_index | 0.274 | 0.233 | 687 | 1 | 0.135 | 0.107 | 0.133 | 0.147 | 45 |
| C1.circle_elimination_r2 | revised (supersedes circle_elimination) | R.last_live_index | 0.138 | 0.121 | 652 | 1 | 0.080 | 0.072 | 0.081 | 0.090 | 46 |
| C1.coin_change_table | unchanged (batch 1 or existing) | R.greedy_fewest | 0.280 | 0.216 | 1466 | 1 | 0.163 | 0.148 | 0.166 | 0.223 | 124 |
| C1.digit_peel | unchanged (batch 1 or existing) | R.decimal_digit_sum_of_literal | 0.610 | 0.052 | 503 | 4 | 0.129 | 0.128 | 0.129 | 0.254 | 478 |
| C1.euclid_gcd | unchanged (batch 1 or existing) | R.gcd_of_literals | 1.000 | 0.144 | 633 | 1 | 0.124 | 0.084 | 0.192 | 0.492 | 87 |
| C1.euclid_gcd_traced | PROPOSED shape (additional) | O.count_nums | 0.195 | 0.195 | 978 | 4 | 0.098 | 0.096 | 0.098 | 0.098 | 484 |
| C1.fast_power | SUPERSEDED (before) | R.pow(base,exp,mod) | 1.000 | 0.116 | 648 | 1 | 0.129 | 0.131 | 0.154 | 0.697 | 76 |
| C1.fast_power_r2 | revised (supersedes fast_power) | R.pow(base,exp,mod) | 1.000 | 0.133 | 646 | 1 | 0.122 | 0.126 | 0.142 | 0.694 | 76 |
| C1.fast_power_traced | PROPOSED shape (additional) | R.base_mod | 0.313 | 0.290 | 964 | 1 | 0.144 | 0.145 | 0.143 | 0.221 | 538 |
| C1.fib_shapes_recursive | revised (supersedes recursive_calls) | O.max#2 | 0.013 | 0.011 | 2000 | 1 | 0.006 | 0.006 | 0.006 | 0.006 | 907 |
| C1.grid_path_table | unchanged (batch 1 or existing) | R.greedy_max_path | 0.323 | 0.087 | 2000 | 1 | 0.087 | 0.107 | 0.107 | 0.311 | 40 |
| C1.insertion_sort | unchanged (batch 1 or existing) | R.sorted_prefix_list | 1.000 | 0.003 | 659 | 1 | 0.107 | 0.147 | 0.248 | 1.000 | 629 |
| C1.insertion_sort_traced | PROPOSED shape (additional) | A.lit_min | 0.272 | 0.272 | 1005 | 1 | 0.252 | 0.252 | 0.252 | 0.252 | 11 |
| C1.kadane_scan | unchanged (batch 1 or existing) | R.max_subarray | 1.000 | 0.072 | 544 | 1 | 0.030 | 0.105 | 0.119 | 0.435 | 183 |
| C1.kadane_scan_traced | PROPOSED shape (additional) | A.echo_printed_initial | 0.337 | 0.337 | 964 | 1 | 0.194 | 0.191 | 0.200 | 0.205 | 50 |
| C1.majority_vote_scan | SUPERSEDED (before) | O.num[-9] | 0.850 | 0.232 | 379 | 4 | 0.254 | 0.210 | 0.371 | 0.451 | 26 |
| C1.majority_vote_scan_r2 | revised (supersedes majority_vote_scan) | R.mode_space_0 | 0.293 | 0.176 | 1005 | 1 | 0.122 | 0.045 | 0.121 | 0.184 | 41 |
| C1.merge_two_sorted | SUPERSEDED (before) | R.sorted_all_but_last | 0.568 | 0.004 | 690 | 1 | 0.181 | 0.113 | 0.198 | 0.481 | 642 |
| C1.merge_two_sorted_r2 | revised (supersedes merge_two_sorted) | O.const_3 | 0.296 | 0.296 | 2000 | 1 | 0.296 | 0.283 | 0.292 | 0.292 | 9 |
| C1.mirror_pointers | unchanged (batch 1 or existing) | A.str1_first | 0.383 | 0.040 | 677 | 1 | 0.110 | 0.100 | 0.110 | 0.241 | 630 |
| C1.partition_pass | unchanged (batch 1 or existing) | R.stable_partition | 0.381 | 0.001 | 1191 | 1 | 0.104 | 0.104 | 0.144 | 0.332 | 1202 |
| C1.postfix_evaluation | unchanged (batch 1 or existing) | A.list1_posum | 0.038 | 0.021 | 1017 | 1 | 0.021 | 0.019 | 0.019 | 0.023 | 520 |
| C1.recursive_calls | SUPERSEDED (before) | O.min#3 | 0.023 | 0.022 | 1583 | 1 | 0.013 | 0.018 | 0.021 | 0.021 | 329 |
| C1.recursive_calls_r2 | revised (supersedes recursive_calls) | A.lit_first | 0.014 | 0.008 | 662 | 1 | 0.002 | 0.004 | 0.005 | 0.005 | 1178 |
| C1.run_length_scan | unchanged (batch 1 or existing) | - | -1.000 | 0.000 | 0 |  | 0.003 | 0.000 | 0.003 | 0.003 | 1360 |
| C1.shared_lists | unchanged (batch 1 or existing) | O.last_set_int | 0.175 | 0.117 | 103 | 5 | 0.058 | 0.029 | 0.066 | 0.066 | 771 |
| C1.sieve_marking | SUPERSEDED (before) | R.ones_minus_strikes_naive | 0.498 | 0.300 | 670 | 1 | 0.266 | 0.058 | 0.266 | 0.332 | 64 |
| C1.sieve_marking_r2 | revised (supersedes sieve_marking) | R.mine_allones_dbl_indexsum | 0.131 | 0.131 | 950 | 1 | 0.159 | 0.018 | 0.159 | 0.159 | 60 |
| C1.string_pair_table | unchanged (batch 1 or existing) | R.multiset_overlap | 0.575 | 0.465 | 643 | 1 | 0.197 | 0.150 | 0.197 | 0.233 | 91 |
| C1.turtle_walk | SUPERSEDED (before) | R.F_minus_B | 0.816 | 0.227 | 673 | 1 | 0.153 | 0.139 | 0.144 | 0.536 | 97 |
| C1.turtle_walk_r2 | revised (supersedes turtle_walk) | R.sum_forward_minus_back | 0.290 | 0.207 | 507 | 1 | 0.173 | 0.169 | 0.166 | 0.195 | 233 |
| C1.union_find_links | unchanged (batch 1 or existing) | A.list1_first | 0.333 | 0.333 | 333 | 1 | 0.086 | 0.058 | 0.086 | 0.106 | 901 |

## Before and after (superseded lineage, its revision), worst cell over levels 1-5

| superseded | rate (rule) | const | revised | rate (rule) | const |
|---|---|---|---|---|---|
| C1.bytecode_loop | 0.870 (R.sum_all_args) | 0.047 | C1.bytecode_loop_r2 | 0.291 (O.num[1]) | 0.211 |
| C1.cellular_update | 0.107 (O.len_list1_minus1) | 0.107 | C1.cellular_update_r2 | 0.102 (A.echo_printed_initial) | 0.102 |
| C1.circle_elimination | 0.274 (R.first_live_index) | 0.233 | C1.circle_elimination_r2 | 0.138 (R.last_live_index) | 0.121 |
| C1.fast_power | 1.000 (R.pow(base,exp,mod)) | 0.116 | C1.fast_power_r2 | 1.000 (R.pow(base,exp,mod)) | 0.133 |
| C1.recursive_calls | 0.023 (O.min#3) | 0.022 | C1.fib_shapes_recursive | 0.013 (O.max#2) | 0.011 |
| C1.majority_vote_scan | 0.850 (O.num[-9]) | 0.232 | C1.majority_vote_scan_r2 | 0.293 (R.mode_space_0) | 0.176 |
| C1.merge_two_sorted | 0.568 (R.sorted_all_but_last) | 0.004 | C1.merge_two_sorted_r2 | 0.296 (O.const_3) | 0.296 |
| C1.recursive_calls | 0.023 (O.min#3) | 0.022 | C1.recursive_calls_r2 | 0.014 (A.lit_first) | 0.008 |
| C1.sieve_marking | 0.498 (R.ones_minus_strikes_naive) | 0.300 | C1.sieve_marking_r2 | 0.131 (R.mine_allones_dbl_indexsum) | 0.131 |
| C1.turtle_walk | 0.816 (R.F_minus_B) | 0.227 | C1.turtle_walk_r2 | 0.290 (R.sum_forward_minus_back) | 0.207 |
