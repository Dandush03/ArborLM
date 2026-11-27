| lineage | n/level | const (max L1-5) | O1 shape-const CV | O5 best literal rule CV | O7 best rule per shape CV | author best single rule (A.*) | oracle any literal | oracle stat | key '0' rate | best R.* rule | min distinct keys |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C1.bubble_pass (old) | 1000 | 0.001 (L5) | 0.000 (L5) | 0.043 (L2) | 0.043 (L2) | list1_sorted 0.051 (L2) | 0.003 | 0.100 | 0.000 |  0.000 (L-) | 1000 |
| C1.cond_chain (old) | 1000 | 0.234 (L5) | 0.299 (L5) | 0.227 (L5) | 0.299 (L5) | lit_mode 0.232 (L5) | 0.322 | 0.000 | 0.007 | gcd_of_literals 0.366 (L5) | 29 |
| C1.counter_list (old) | 1000 | 0.092 (L2) | 0.092 (L2) | 0.000 (L5) | 0.092 (L2) | str1_self 0.000 (L5) | 0.000 | 0.000 | 0.000 |  0.000 (L-) | 122 |
| C1.fib_like (old) | 1000 | 0.035 (L3) | 0.034 (L3) | 0.057 (L4) | 0.057 (L4) | echo_printed_initial 0.052 (L4) | 0.092 | 0.000 | 0.032 |  0.000 (L-) | 116 |
| C1.func_branch (old) | 1000 | 0.027 (L2) | 0.050 (L2) | 0.023 (L1) | 0.051 (L2) | lit_min 0.027 (L2) | 0.096 | 0.000 | 0.027 |  0.000 (L-) | 199 |
| C1.func_compose (old) | 1000 | 0.211 (L5) | 0.184 (L5) | 0.211 (L5) | 0.176 (L5) | lit_first 0.157 (L5) | 0.371 | 0.000 | 0.206 |  0.000 (L-) | 9 |
| C1.list_build (old) | 1000 | 0.153 (L3) | 0.164 (L3) | 0.053 (L2) | 0.164 (L3) | lit_min 0.055 (L3) | 0.119 | 0.000 | 0.013 | m_minus_1 0.158 (L3) | 203 |
| C1.loop_sum (old) | 1000 | 0.012 (L1) | 0.005 (L3) | 0.081 (L1) | 0.081 (L1) | lit_first 0.081 (L1) | 0.083 | 0.000 | 0.012 |  0.000 (L-) | 490 |
| C1.minmax_track (old) | 1000 | 0.089 (L1) | 0.087 (L2) | 0.228 (L5) | 0.252 (L2) | list1_min 0.228 (L5) | 0.530 | 0.434 | 0.055 |  0.000 (L-) | 56 |
| C1.nested_pairs (old) | 1000 | 0.138 (L1) | 0.138 (L1) | 0.095 (L1) | 0.138 (L1) | lit_max 0.095 (L1) | 0.228 | 0.000 | 0.037 |  0.000 (L-) | 62 |
| C1.slices (old) | 1000 | 0.072 (L4) | 0.009 (L3) | 0.072 (L4) | 0.041 (L1) | list1_sum 0.020 (L1) | 0.087 | 0.069 | 0.072 |  0.000 (L-) | 792 |
| C1.string_build (old) | 1000 | 0.082 (L3) | 0.077 (L3) | 0.087 (L4) | 0.079 (L3) | lit_max 0.087 (L4) | 0.087 | 0.000 | 0.000 | iterations(stop-start) 0.350 (L4) | 654 |
| C1.string_methods (old) | 1000 | 0.300 (L3) | 0.408 (L1) | 0.300 (L3) | 0.485 (L1) | str1_len 0.117 (L1) | 0.130 | 0.159 | 0.300 |  0.000 (L-) | 319 |
| C1.while_counter (old) | 1000 | 0.155 (L1) | 0.155 (L1) | 0.119 (L1) | 0.155 (L1) | lit_first 0.044 (L1) | 0.198 | 0.000 | 0.007 |  0.000 (L-) | 34 |
| C1.bfs_queue (new) | 2000 | 0.153 (L1) | 0.221 (L1) | 0.153 (L1) | 0.228 (L1) | list1_len 0.106 (L1) | 0.515 | 0.571 | 0.019 |  0.000 (L-) | 400 |
| C1.binary_search (new) | 2000 | 0.080 (L1) | 0.080 (L1) | 0.080 (L1) | 0.080 (L1) | lit_min 0.080 (L1) | 0.256 | 0.036 | 0.080 |  0.000 (L-) | 103 |
| C1.bracket_matching (new) | 2000 | 0.211 (L1) | 0.197 (L1) | 0.236 (L1) | 0.233 (L1) | lit_mode 0.211 (L1) | 0.377 | 0.448 | 0.051 | standard_code 0.713 (L1) | 20 |
| C1.bytecode_loop (new) | 2000 | 0.060 (L2) | 0.060 (L2) | 0.072 (L3) | 0.072 (L3) | lit_min 0.060 (L2) | 0.299 | 0.129 | 0.060 | sum_all_args 0.436 (L1) | 133 |
| C1.cellular_update (new) | 2000 | 0.051 (L1) | 0.043 (L3) | 0.096 (L1) | 0.096 (L1) | echo_printed_initial 0.096 (L1) | 0.218 | 0.216 | 0.047 |  0.000 (L-) | 80 |
| C1.circle_elimination (new) | 2000 | 0.100 (L1) | 0.082 (L1) | 0.099 (L1) | 0.099 (L1) | lit_min 0.100 (L1) | 0.384 | 0.211 | 0.100 | first_live_index 0.116 (L1) | 45 |
| C1.coin_change_table (new) | 2000 | 0.158 (L1) | 0.212 (L1) | 0.149 (L2) | 0.213 (L1) | lit_min 0.140 (L1) | 0.430 | 0.322 | 0.140 | greedy_fewest 0.206 (L1) | 104 |
| C1.digit_peel (new) | 2000 | 0.095 (L1) | 0.095 (L1) | 0.123 (L1) | 0.123 (L1) | lit_mode 0.084 (L1) | 0.239 | 0.000 | 0.084 | decimal_digit_sum_of_literal 0.161 (L1) | 480 |
| C1.euclid_gcd (new) | 2000 | 0.135 (L2) | 0.135 (L2) | 0.076 (L2) | 0.135 (L2) | lit_max 0.042 (L2) | 0.098 | 0.000 | 0.000 | gcd_of_literals 0.427 (L1) | 86 |
| C1.fast_power (new) | 2000 | 0.129 (L1) | 0.129 (L1) | 0.141 (L1) | 0.141 (L1) | lit_first 0.129 (L1) | 0.333 | 0.000 | 0.065 | pow(base,exp,mod) 0.451 (L3) | 77 |
| C1.grid_path_table (new) | 2000 | 0.089 (L1) | 0.089 (L1) | 0.102 (L1) | 0.102 (L1) | list1_sum 0.102 (L1) | 0.222 | 0.254 | 0.000 | greedy_min_path 0.333 (L1) | 42 |
| C1.insertion_sort (new) | 2000 | 0.110 (L1) | 0.118 (L1) | 0.154 (L1) | 0.316 (L1) | echo_printed_initial 0.144 (L1) | 0.637 | 0.431 | 0.067 | inversions_prefix 0.361 (L3) | 636 |
| C1.kadane_scan (new) | 2000 | 0.035 (L1) | 0.034 (L3) | 0.099 (L1) | 0.099 (L1) | list1_sum 0.099 (L1) | 0.119 | 0.147 | 0.009 | max_subarray 0.350 (L3) | 185 |
| C1.majority_vote_scan (new) | 2000 | 0.166 (L1) | 0.261 (L1) | 0.207 (L2) | 0.295 (L1) | list1_max 0.132 (L3) | 0.399 | 0.259 | 0.000 | mode_space_0 0.163 (L1) | 25 |
| C1.merge_two_sorted (new) | 2000 | 0.146 (L1) | 0.146 (L1) | 0.122 (L1) | 0.146 (L1) | list1_len 0.126 (L1) | 0.460 | 0.422 | 0.000 | len_a+len_b-1 0.177 (L1) | 582 |
| C1.mirror_pointers (new) | 2000 | 0.107 (L1) | 0.097 (L2) | 0.097 (L2) | 0.097 (L2) | str1_first 0.129 (L1) | 0.186 | 0.154 | 0.079 | unequal_pairs 0.130 (L1) | 609 |
| C1.partition_pass (new) | 2000 | 0.088 (L1) | 0.088 (L1) | 0.088 (L1) | 0.088 (L1) | echo_printed_initial 0.088 (L1) | 0.241 | 0.127 | 0.088 | stable_partition 0.217 (L1) | 1211 |
| C1.postfix_evaluation (new) | 2000 | 0.016 (L1) | 0.015 (L3) | 0.015 (L3) | 0.015 (L3) | list1_posum 0.016 (L1) | 0.078 | 0.069 | 0.015 | first_operand 0.013 (L1) | 564 |
| C1.recursive_calls (new) | 2000 | 0.022 (L1) | 0.061 (L2) | 0.011 (L1) | 0.064 (L2) | lit_mode 0.010 (L1) | 0.034 | 0.009 | 0.004 |  0.000 (L-) | 343 |
| C1.run_length_scan (new) | 2000 | 0.008 (L1) | 0.004 (L1) | 0.000 (L5) | 0.004 (L1) | str1_self 0.000 (L5) | 0.000 | 0.000 | 0.000 |  0.000 (L-) | 1361 |
| C1.shared_lists (new) | 2000 | 0.037 (L2) | 0.054 (L4) | 0.021 (L2) | 0.054 (L2) | list1_max 0.023 (L3) | 0.140 | 0.129 | 0.000 |  0.000 (L-) | 787 |
| C1.sieve_marking (new) | 2000 | 0.200 (L1) | 0.222 (L1) | 0.057 (L1) | 0.222 (L1) | specific 0.035 (L3) | 0.060 | 0.060 | 0.007 | ones_minus_strikes_naive 0.225 (L1) | 58 |
| C1.string_pair_table (new) | 2000 | 0.158 (L1) | 0.204 (L1) | 0.158 (L1) | 0.204 (L1) | str1_len 0.084 (L1) | 0.084 | 0.320 | 0.011 | hamming_plus_lendiff 0.192 (L2) | 88 |
| C1.turtle_walk (new) | 2000 | 0.150 (L1) | 0.158 (L1) | 0.150 (L1) | 0.155 (L1) | lit_max 0.150 (L1) | 0.440 | 0.585 | 0.013 | count_F 0.530 (L1) | 96 |
| C1.union_find_links (new) | 2000 | 0.062 (L4) | 0.079 (L1) | 0.062 (L4) | 0.068 (L4) | lit_min 0.062 (L4) | 0.241 | 0.231 | 0.062 | naive_links_v->u 0.029 (L1) | 961 |
