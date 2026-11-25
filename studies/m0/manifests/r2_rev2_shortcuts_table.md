# R2 rev2: worst two-sided shortcut accuracy per lineage, before (batch-1 shapes) and after (rev2 shapes)

Per level, two-sided (yes/no read as max(acc, 1-acc)), auditor's battery plus the author's, 2,000 items per level (seed 953901). Measured, not thresholded. 'before' is shown for lineages whose shape changed; 'after' for all.

| Lineage | state | worst heuristic (acc, its chance, level, name) | worst constant key (share, chance, level) |
|---|---|---|---|
| R2.binary_search_trace | after | 0.640 / 0.00 / L0 / X:first three of the true trace only | 0.050 / 0.00 / L0 |
| R2.bracket_match | before | 0.785 / 0.00 / L0 / X:second closer of the same kind | 0.359 / 0.00 / L0 |
| R2.bracket_match | after | 0.508 / 0.00 / L0 / X:last closer of the same kind | 0.251 / 0.00 / L0 |
| R2.bst_traversal | after | 0.627 / 0.00 / L0 / X:root, smaller in insertion order, larger in insertion orde | 0.002 / 0.00 / L0 |
| R2.cache_eviction | before | 1.000 / 0.50 / L0 / X:item among the last cap distinct items (=LRU answer) | 0.287 / 0.00 / L0 |
| R2.cache_eviction | after | 0.591 / 0.00 / L0 / A:other policy | 0.256 / 0.00 / L1 |
| R2.cellular_automaton | after | 0.509 / 0.00 / L6 / X:one step too many | 0.248 / 0.00 / L0 |
| R2.cheapest_network | before | 0.694 / 0.00 / L0 / X:cheapest per town minus cheapest cable | 0.042 / 0.00 / L1 |
| R2.cheapest_network | after | 0.305 / 0.00 / L2 / X:nearest-neighbour walk | 0.099 / 0.00 / L0 |
| R2.chip_toppling | before | 1.000 / 0.00 / L6 / X:invariant formula: ones with a 0 at (n(n+1)/2 - sum i*c_i) | 0.182 / 0.00 / L0 |
| R2.chip_toppling | after | 0.211 / 0.00 / L1 / X:chips minus n | 0.153 / 0.00 / L0 |
| R2.coin_change_min | before | 0.702 / 0.00 / L0 / X:amount/largest rounded up + 1 | 0.221 / 0.00 / L6 |
| R2.coin_change_min | after | 0.291 / 0.00 / L2 / B:amount // product of two smallest coins + 1 | 0.254 / 0.00 / L2 |
| R2.crt_smallest | before | 0.195 / 0.00 / L0 / A:largest remainder | 0.033 / 0.00 / L0 |
| R2.crt_smallest | after | 0.118 / 0.00 / L0 / A:largest remainder | 0.012 / 0.00 / L0 |
| R2.deferred_acceptance_partner | before | 0.669 / 0.20 / L5 / X:responder-proposing stable partner | 0.000 / 0.00 / L-1 |
| R2.deferred_acceptance_partner | after | 0.681 / 0.14 / L6 / X:responder-proposing stable partner | 0.000 / 0.00 / L-1 |
| R2.dictionary_rank | after | 0.491 / 0.00 / L0 / X:first two letters only | 0.073 / 0.00 / L1 |
| R2.expression_eval | before | 0.023 / 0.00 / L0 / B:first number in the question | 0.042 / 0.00 / L0 |
| R2.expression_eval | after | 0.028 / 0.00 / L0 / X:sum of all numbers | 0.038 / 0.00 / L0 |
| R2.gcd_euclid | before | 0.870 / 0.00 / L0 / X:common small primes (2,3,5,7) product | 0.348 / 0.00 / L4 |
| R2.gcd_euclid | after | 0.135 / 0.00 / L0 / X:a mod b | 0.090 / 0.00 / L0 |
| R2.hamming_error_position | after | 0.236 / 0.00 / L1 / A:lowest failing check | 0.115 / 0.00 / L6 |
| R2.hash_probe | before | 0.798 / 0.00 / L1 / X:home + earlier keys with the same home | 0.558 / 0.00 / L1 |
| R2.hash_probe | after | 0.619 / 0.00 / L0 / X:home + earlier keys with the same home | 0.338 / 0.00 / L1 |
| R2.interval_scheduling | after | 0.392 / 0.00 / L0 / X:meetings in written order, keep if no clash | 0.257 / 0.00 / L0 |
| R2.lcs_length | before | 0.622 / 0.00 / L0 / X:greedy matching, better of both directions | 0.293 / 0.00 / L1 |
| R2.lcs_length | after | 0.469 / 0.00 / L0 / X:greedy matching, better of both directions | 0.248 / 0.00 / L0 |
| R2.lis_length | before | 0.390 / 0.00 / L0 / X:round(2*sqrt(n)) - 2 | 0.326 / 0.00 / L4 |
| R2.lis_length | after | 0.374 / 0.00 / L0 / A:ascents + 1 | 0.185 / 0.00 / L0 |
| R2.longest_palindromic_substring | before | 0.611 / 0.00 / L0 / X:longest odd-length palindrome only | 0.299 / 0.00 / L0 |
| R2.longest_palindromic_substring | after | 0.548 / 0.00 / L3 / X:longest odd-length palindrome only | 0.151 / 0.00 / L6 |
| R2.luhn_check | after | 0.134 / 0.00 / L0 / X:check digit without subtracting 9 | 0.124 / 0.00 / L0 |
| R2.max_subarray_sum | before | 0.574 / 0.00 / L0 / X:best run of non-negative numbers | 0.106 / 0.00 / L0 |
| R2.max_subarray_sum | after | 0.000 / 0.00 / L-1 /  | 0.063 / 0.00 / L2 |
| R2.merge_smallest_cost | before | 0.726 / 0.00 / L0 / X:join in ascending order (chain) | 0.041 / 0.00 / L0 |
| R2.merge_smallest_cost | after | 0.321 / 0.00 / L0 / X:join in ascending order (chain) | 0.018 / 0.00 / L0 |
| R2.min_heap_ops | after | 0.159 / 0.00 / L0 / X:minimum swapped to the front | 0.001 / 0.00 / L0 |
| R2.modular_power | before | 0.698 / 0.00 / L0 / X:a^(e mod (m-1)) mod m (Fermat, valid only for prime m) | 0.204 / 0.00 / L0 |
| R2.modular_power | after | 0.320 / 0.00 / L0 / X:a^(e mod (m-1)) mod m (Fermat, valid only for prime m) | 0.107 / 0.00 / L0 |
| R2.prime_factor_query | before | 0.835 / 0.00 / L0 / X:sum of distinct prime factors | 0.215 / 0.00 / L6 |
| R2.prime_factor_query | after | 0.028 / 0.00 / L0 / X:largest prime factor * 2 | 0.095 / 0.00 / L0 |
| R2.subtraction_game | before | 0.622 / 0.50 / L5 / A:n mod (largest+1) != 0 | 0.529 / 0.50 / L3 |
| R2.subtraction_game | after | 0.594 / 0.50 / L0 / B:(n1 mod (max+1)) xor (n2 mod (max+1)) nonzero | 0.515 / 0.50 / L3 |
