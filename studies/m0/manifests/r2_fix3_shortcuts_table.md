# R2 fix round 3: worst two-sided cheap-rule effect per lineage and level, before and after (measured, 2,000 items per level and shape draw; not thresholded)

Effect = accuracy for open answers (chance 0), |accuracy - 0.5| for yes/no. 'cue' excludes the valid-alternative (P) rules and the most-frequent-answer rule (the 'mode' column). 'before' = the shape held by the registries before this round, measured with the auditor's battery only; 'after' = this round, auditor's battery plus this round's own rules. The lead's +-0.10 is a working target, not a registered bound.

| Lineage | state | cue L0..L6 | mode L0..L6 | (P) max | worst rule after (level) |
|---|---|---|---|---|---|
| R2.binary_search_trace | before | 0.38 0.28 0.40 0.20 0.23 0.35 0.20 | 0.04 0.06 0.02 0.02 0.01 0.02 0.02 | 0.00 | |
| R2.binary_search_trace | after | 0.06 0.08 0.04 0.04 0.03 0.06 0.03 | 0.01 0.01 0.01 0.00 0.00 0.00 0.00 | 0.84 | [sum] sum: midpoint rounded UP (L1) |
| R2.bracket_match | before | 0.52 0.44 0.43 0.43 0.38 0.39 0.36 | 0.22 0.19 0.21 0.17 0.14 0.14 0.12 | 0.00 | |
| R2.bracket_match | after | 0.16 0.17 0.15 0.13 0.12 0.12 0.10 | 0.12 0.10 0.11 0.09 0.10 0.09 0.09 | 0.00 | [first_error] first_error: the position after the first adjacent closer pair of different  (L1) |
| R2.bst_traversal | before | 0.36 0.17 0.08 0.04 0.01 0.01 0.00 | 0.00 0.00 0.00 0.00 0.00 0.00 0.00 | 0.41 | |
| R2.bst_traversal | after | 0.04 0.01 0.01 0.00 0.00 0.00 0.00 | 0.00 0.00 0.00 0.00 0.00 0.00 0.00 | 0.07 | [level] insertion order (L0) |
| R2.cache_eviction | before | 0.49 0.41 0.52 0.39 0.43 0.40 0.42 | 0.28 0.24 0.20 0.21 0.17 0.15 0.16 | 0.59 | |
| R2.cache_eviction | after | 0.09 0.09 0.09 0.05 0.05 0.07 0.05 | 0.00 0.00 0.00 0.00 0.00 0.00 0.00 | 0.09 | [fifo/contents] contents: the last cap distinct requests, oldest first (the LRU contents) (L0) |
| R2.caesar_shift | before | 0.03 0.04 0.04 0.04 0.05 0.03 0.05 | 0.00 0.00 0.00 0.00 0.00 0.00 0.00 | 0.00 | |
| R2.caesar_shift | after | 0.03 0.04 0.04 0.04 0.05 0.03 0.05 | 0.00 0.00 0.00 0.00 0.00 0.00 0.00 | 0.00 | [-] shift backwards (L4) |
| R2.cellular_automaton | before | 0.72 0.73 0.58 0.59 0.55 0.56 0.51 | 0.25 0.13 0.16 0.13 0.08 0.08 0.08 | 0.58 | |
| R2.cellular_automaton | after | 0.04 0.02 0.05 0.05 0.01 0.01 0.04 | 0.01 0.01 0.01 0.00 0.00 0.00 0.00 | 0.19 | [row] one step only (L2) |
| R2.cheapest_network | before | 1.00 1.00 1.00 0.77 0.77 0.77 0.57 | 0.09 0.09 0.10 0.07 0.07 0.06 0.06 | 0.00 | |
| R2.cheapest_network | after | 0.07 0.07 0.04 0.04 0.03 0.03 0.02 | 0.04 0.04 0.05 0.04 0.04 0.04 0.04 | 0.00 | [-] sum of each town's cheapest cable (L1) |
| R2.coin_change_min | before | 0.20 0.24 0.24 0.12 0.15 0.17 0.17 | 0.20 0.24 0.24 0.10 0.15 0.17 0.17 | 0.13 | |
| R2.coin_change_min | after | 0.11 0.09 0.08 0.08 0.08 0.06 0.05 | 0.00 0.00 0.00 0.00 0.00 0.00 0.00 | 0.00 | [fewest] ceil(amount / largest coin) for each amount (L0) |
| R2.count_divisible | before | 0.99 0.98 0.99 0.99 0.99 0.99 0.98 | 0.46 0.32 0.27 0.22 0.20 0.18 0.15 | 0.00 | |
| R2.count_divisible | after | 0.03 0.02 0.01 0.01 0.00 0.00 0.00 | 0.03 0.01 0.01 0.00 0.00 0.00 0.00 | 0.00 | [sum] constant 0 (L0) |
| R2.count_letter | before | 0.87 0.83 0.79 0.76 0.73 0.72 0.67 | 0.59 0.40 0.30 0.23 0.19 0.18 0.15 | 0.00 | |
| R2.count_letter | after | 0.08 0.07 0.07 0.05 0.05 0.04 0.03 | 0.09 0.07 0.05 0.05 0.03 0.04 0.04 | 0.00 | [-] number of words (L0) |
| R2.crt_smallest | before | 0.05 0.04 0.03 0.00 0.00 0.00 0.00 | 0.01 0.00 0.00 0.00 0.00 0.00 0.00 | 0.02 | |
| R2.crt_smallest | after | 0.05 0.04 0.03 0.00 0.00 0.00 0.00 | 0.01 0.00 0.00 0.00 0.00 0.00 0.00 | 0.02 | [-] r1 + m1 * r2 (first two) (L0) |
| R2.dictionary_rank | before | 0.01 0.00 0.00 0.00 0.00 0.00 0.00 | 0.04 0.04 0.01 0.01 0.00 0.00 0.00 | 0.00 | |
| R2.dictionary_rank | after | 0.04 0.04 0.00 0.01 0.00 0.00 0.00 | 0.00 0.00 0.00 0.00 0.00 0.00 0.00 | 0.00 | [position] position: index in the FULL sorted alphabet (no removal of used letters) (L0) |
| R2.digit_root | before | 0.09 0.10 0.09 0.10 0.10 0.10 0.10 | 0.10 0.11 0.11 0.12 0.12 0.11 0.10 | 1.00 | |
| R2.digit_root | after | 0.09 0.10 0.09 0.10 0.10 0.10 0.10 | 0.10 0.11 0.11 0.12 0.12 0.11 0.10 | 1.00 | [-] last digit (L3) |
| R2.expression_eval | before | 0.90 0.84 0.80 0.77 0.73 0.70 0.65 | 0.04 0.03 0.03 0.02 0.01 0.01 0.01 | 0.00 | |
| R2.expression_eval | after | 0.09 0.08 0.04 0.06 0.01 0.03 0.02 | 0.03 0.03 0.02 0.02 0.01 0.01 0.00 | 0.00 | [ranked] ranked item: strict left to right (ignore precedence) (L0) |
| R2.from_base | before | 0.16 0.08 0.04 0.02 0.01 0.00 0.01 | 0.01 0.01 0.00 0.00 0.00 0.00 0.00 | 0.00 | |
| R2.from_base | after | 0.16 0.08 0.04 0.02 0.01 0.00 0.01 | 0.01 0.01 0.00 0.00 0.00 0.00 0.00 | 0.00 | [-] digits read right to left (L0) |
| R2.gcd_euclid | before | 0.89 0.86 0.86 0.83 0.81 0.76 0.74 | 0.08 0.05 0.03 0.03 0.02 0.02 0.02 | 0.00 | |
| R2.gcd_euclid | after | 0.08 0.06 0.05 0.06 0.05 0.03 0.03 | 0.03 0.03 0.02 0.01 0.01 0.01 0.01 | 0.00 | [gcd] gcd: a mod b (one Euclid step) (L0) |
| R2.grid_sum | before | 0.06 0.04 0.04 0.05 0.05 0.02 0.05 | 0.08 0.07 0.06 0.06 0.06 0.05 0.06 | 0.00 | |
| R2.grid_sum | after | 0.06 0.04 0.04 0.05 0.05 0.02 0.05 | 0.08 0.07 0.06 0.06 0.06 0.05 0.06 | 0.00 | [-] row i read as column i (or the reverse) (L0) |
| R2.hamming_error_position | before | 0.13 0.22 0.23 0.18 0.17 0.18 0.15 | 0.08 0.10 0.10 0.11 0.10 0.10 0.11 | 0.00 | |
| R2.hamming_error_position | after | 0.13 0.22 0.23 0.18 0.17 0.18 0.15 | 0.08 0.10 0.10 0.11 0.10 0.10 0.11 | 0.00 | [-] first failing check position only (L2) |
| R2.hash_probe | before | 0.93 0.96 0.94 0.95 0.97 0.95 0.98 | 0.35 0.30 0.26 0.21 0.23 0.20 0.20 | 0.00 | |
| R2.hash_probe | after | 0.13 0.10 0.09 0.06 0.04 0.06 0.03 | 0.07 0.07 0.08 0.04 0.04 0.04 0.03 | 0.74 | [checksum] checksum: all slots 0..n-1 filled from the lowest home (L0) |
| R2.interval_scheduling | before | 0.21 0.19 0.19 0.17 0.19 0.18 0.17 | 0.24 0.26 0.22 0.23 0.23 0.22 0.22 | 1.00 | |
| R2.interval_scheduling | after | 0.15 0.14 0.10 0.10 0.06 0.06 0.05 | 0.00 0.00 0.00 0.00 0.00 0.00 0.00 | 0.61 | [chosen] shortest first (L0) |
| R2.kth_smallest | before | 0.34 0.19 0.14 0.10 0.09 0.07 0.07 | 0.00 0.00 0.00 0.00 0.00 0.00 0.00 | 0.00 | |
| R2.kth_smallest | after | 0.34 0.19 0.14 0.10 0.09 0.07 0.07 | 0.00 0.00 0.00 0.00 0.00 0.00 0.00 | 0.00 | [-] k-th largest (L0) |
| R2.lcs_length | before | 0.46 0.36 0.29 0.27 0.25 0.22 0.18 | 0.27 0.24 0.22 0.20 0.17 0.15 0.15 | 0.00 | |
| R2.lcs_length | after | 0.21 0.19 0.16 0.13 0.12 0.11 0.09 | 0.14 0.11 0.10 0.09 0.10 0.09 0.08 | 0.00 | [-] letter-count overlap - 2 (L0) |
| R2.lis_length | before | 0.31 0.24 0.19 0.14 0.12 0.09 0.08 | 0.19 0.15 0.12 0.11 0.11 0.09 0.07 | 0.00 | |
| R2.lis_length | after | 0.31 0.24 0.19 0.14 0.12 0.09 0.08 | 0.19 0.15 0.12 0.11 0.11 0.09 0.07 | 0.00 | [-] best greedy over every start (L0) |
| R2.list_ops | before | 0.67 0.58 0.47 0.43 0.36 0.32 0.26 | 0.00 0.00 0.00 0.00 0.00 0.00 0.00 | 0.00 | |
| R2.list_ops | after | 0.67 0.58 0.47 0.43 0.36 0.32 0.26 | 0.00 0.00 0.00 0.00 0.00 0.00 0.00 | 0.00 | [-] ignore reverses (L0) |
| R2.longest_palindromic_substring | before | 0.51 0.52 0.52 0.52 0.51 0.53 0.52 | 0.14 0.15 0.15 0.14 0.14 0.14 0.15 | 0.00 | |
| R2.longest_palindromic_substring | after | 0.51 0.52 0.52 0.52 0.51 0.53 0.52 | 0.14 0.15 0.15 0.14 0.14 0.14 0.15 | 0.00 | [-] longest odd palindrome only (L5) |
| R2.luhn_check | before | 0.12 0.10 0.11 0.10 0.12 0.10 0.11 | 0.11 0.10 0.10 0.13 0.11 0.10 0.10 | 0.00 | |
| R2.luhn_check | after | 0.12 0.10 0.11 0.10 0.12 0.10 0.11 | 0.11 0.10 0.10 0.13 0.11 0.10 0.10 | 0.00 | [check_digit] doubling the other parity (L4) |
| R2.max_subarray_sum | before | 1.00 1.00 1.00 1.00 1.00 1.00 1.00 | 0.05 0.06 0.06 0.05 0.05 0.05 0.06 | 0.00 | |
| R2.max_subarray_sum | after | 0.18 0.17 0.19 0.14 0.15 0.14 0.11 | 0.04 0.04 0.05 0.04 0.04 0.04 0.03 | 0.00 | [-] best sum of positive numbers and dips of at most 3 in one stretch (dips over 3 end the (L2) |
| R2.merge_smallest_cost | before | 0.31 0.08 0.01 0.02 0.00 0.00 0.00 | 0.01 0.01 0.00 0.01 0.00 0.00 0.00 | 0.34 | |
| R2.merge_smallest_cost | after | 0.31 0.08 0.01 0.02 0.00 0.00 0.00 | 0.01 0.01 0.00 0.01 0.00 0.00 0.00 | 0.34 | [-] ascending chain (sorted, merge left to right) (L0) |
| R2.min_heap_ops | before | 0.17 0.07 0.04 0.01 0.01 0.00 0.00 | 0.00 0.00 0.00 0.00 0.00 0.00 0.00 | 1.00 | |
| R2.min_heap_ops | after | 0.00 0.00 0.00 0.00 0.00 0.00 0.00 | 0.00 0.00 0.00 0.00 0.00 0.00 0.00 | 1.00 | [removals=0] insertion order with the minimum swapped to the front (L0) |
| R2.modular_power | before | 0.30 0.30 0.24 0.20 0.16 0.21 0.20 | 0.10 0.09 0.08 0.06 0.06 0.06 0.07 | 1.00 | |
| R2.modular_power | after | 0.30 0.30 0.24 0.20 0.16 0.21 0.20 | 0.10 0.09 0.08 0.06 0.06 0.06 0.07 | 1.00 | [-] a^(e mod (m-1)) mod m (Fermat misuse) (L0) |
| R2.multiples_between | before | 0.88 0.89 0.89 0.88 0.88 0.89 0.89 | 0.06 0.03 0.02 0.01 0.01 0.01 0.01 | 0.00 | |
| R2.multiples_between | after | 0.00 0.00 0.00 0.00 0.00 0.00 0.00 | 0.02 0.01 0.01 0.01 0.00 0.00 0.00 | 1.00 |  (L0) |
| R2.palindrome_check | before | 0.47 0.47 0.47 0.46 0.47 0.46 0.47 | 0.04 0.03 0.01 0.02 0.00 0.02 0.01 | 0.00 | |
| R2.palindrome_check | after | 0.21 0.17 0.17 0.15 0.13 0.15 0.14 | 0.05 0.03 0.04 0.03 0.01 0.04 0.03 | 0.00 | [-] outer two letters each side match (L0) |
| R2.permutation_power | before | 0.83 0.58 0.76 0.48 0.61 0.55 0.57 | 0.25 0.19 0.17 0.15 0.13 0.11 0.09 | 0.00 | |
| R2.permutation_power | after | 0.11 0.10 0.09 0.08 0.08 0.07 0.05 | 0.09 0.08 0.07 0.07 0.06 0.06 0.05 | 0.00 | [-] one application (L0) |
| R2.prime_factor_query | before | 0.00 0.00 0.00 0.00 0.00 0.00 0.00 | 0.08 0.05 0.06 0.04 0.06 0.06 0.05 | 1.00 | |
| R2.prime_factor_query | after | 0.00 0.00 0.00 0.00 0.00 0.00 0.00 | 0.06 0.05 0.06 0.04 0.06 0.06 0.05 | 1.00 |  (L0) |
| R2.run_length | before | 0.00 0.00 0.00 0.00 0.00 0.00 0.00 | 0.00 0.00 0.00 0.00 0.00 0.00 0.00 | 0.00 | |
| R2.run_length | after | 0.00 0.00 0.00 0.00 0.00 0.00 0.00 | 0.00 0.00 0.00 0.00 0.00 0.00 0.00 | 0.00 |  (L0) |
| R2.sort_list | before | 0.00 0.00 0.00 0.00 0.00 0.00 0.00 | 0.00 0.00 0.00 0.00 0.00 0.00 0.00 | 0.00 | |
| R2.sort_list | after | 0.00 0.00 0.00 0.00 0.00 0.00 0.00 | 0.00 0.00 0.00 0.00 0.00 0.00 0.00 | 0.00 |  (L0) |
| R2.stack_machine | before | 1.00 1.00 1.00 1.00 1.00 1.00 1.00 | 0.09 0.06 0.07 0.06 0.07 0.08 0.08 | 0.00 | |
| R2.stack_machine | after | 0.04 0.02 0.02 0.02 0.02 0.02 0.02 | 0.03 0.03 0.03 0.04 0.03 0.04 0.04 | 0.00 | [-] sum of pushed values (L0) |
| R2.string_rewrite_nonidentity | before | 1.00 0.25 0.25 0.04 0.04 0.01 0.01 | 0.01 0.01 0.01 0.01 0.00 0.01 0.00 | 1.00 | |
| R2.string_rewrite_nonidentity | after | 1.00 0.25 0.25 0.04 0.04 0.01 0.01 | 0.01 0.01 0.01 0.01 0.00 0.01 0.00 | 1.00 | [-] only the first rule (L0) |
| R2.subtraction_game | before | 0.30 0.30 0.30 0.30 0.31 0.31 0.30 | 0.01 0.00 0.02 0.02 0.00 0.01 0.03 | 0.10 | |
| R2.subtraction_game | after | 0.13 0.11 0.09 0.09 0.08 0.09 0.10 | 0.01 0.01 0.01 0.01 0.00 0.01 0.01 | 0.33 | [-] count of piles that are a win alone is odd -> yes (L0) |
| R2.to_base_wide | before | 0.05 0.03 0.01 0.00 0.00 0.00 0.00 | 0.00 0.00 0.00 0.00 0.00 0.00 0.00 | 0.00 | |
| R2.to_base_wide | after | 0.05 0.03 0.01 0.00 0.00 0.00 0.00 | 0.00 0.00 0.00 0.00 0.00 0.00 0.00 | 0.00 | [-] digits reversed (least significant first) (L0) |
