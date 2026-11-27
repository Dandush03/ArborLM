# ruff: noqa
"""Write the auditor's own judgement (procedures, all 861 pair verdicts, cluster counts, cross-evaluation duplicates,
quality, shortcut and capacity findings, feasibility) BEFORE reading the author's manifest. Prints its SHA-256."""
import hashlib
import itertools
import json
import sys

OUT = sys.argv[1]

PROC = {
    # existing 16 (studies/m0/lineages_r2.py)
    "R2.count_letter": "scan the words and count occurrences of one letter",
    "R2.count_divisible": "scan a number list and count items passing a predicate (divisible by m and > t)",
    "R2.sort_list": "sort the list (ascending or descending) and write it out",
    "R2.kth_smallest": "sort ascending and read off position k",
    "R2.list_ops": "apply a sequence of deque edits (reverse, drop first/last, append, move first to end)",
    "R2.to_base": "decimal to base b by repeated division, remainders as digits",
    "R2.from_base": "base b to decimal by positional (Horner) evaluation",
    "R2.string_rewrite": "apply global left-to-right non-overlapping replacement rules in sequence",
    "R2.caesar_shift": "shift each letter forward by k modulo 26",
    "R2.run_length": "scan maximal runs and emit letter + run length",
    "R2.palindrome_check": "drop spaces and compare the string with its reverse",
    "R2.grid_sum": "pick a row, column or main diagonal of a grid and add its cells",
    "R2.permutation_power": "iterate a given mapping t times from s (or reduce t modulo the cycle length)",
    "R2.stack_machine": "simulate a stack under push/pop/dup/swap/add/sub/mul and read the top",
    "R2.multiples_between": "count multiples of m in [a, b] by floor division",
    "R2.digit_root": "repeated digit sum to one digit (equivalently 1 + (n-1) mod 9)",
    # new 26 (studies/m0/lineages_r2_<family>.py)
    "R2.lcs_length": "longest common subsequence via the 2-D match/skip table",
    "R2.coin_change_min": "unbounded minimum-coin DP over amounts 0..A",
    "R2.lis_length": "longest strictly increasing subsequence (O(n^2) DP or patience piles)",
    "R2.max_subarray_sum": "maximum contiguous block sum (Kadane running sum)",
    "R2.gcd_euclid": "Euclid's remainder iteration: gcd, lcm = ab/gcd, or the number of steps",
    "R2.modular_power": "a^e mod m by repeated multiplication with reduction, square-and-multiply or the cycle of powers",
    "R2.crt_smallest": "smallest x meeting 2-3 congruences (step through one congruence class, or CRT construction)",
    "R2.prime_factor_query": "trial-division factorisation; largest prime or sum with multiplicity",
    "R2.subtraction_game": "label pile sizes 0..n win/lose by backward induction over the move set",
    "R2.binary_search_trace": "simulate floor-midpoint binary search on 1-based positions, record probed values",
    "R2.longest_palindromic_substring": "search all centres/substrings for the longest palindromic block",
    "R2.dictionary_rank": "lexicographic rank/unrank of a permutation via factorial-base (Lehmer) digits",
    "R2.bst_traversal": "insert into an unbalanced BST, then pre-, post- or level-order traversal",
    "R2.min_heap_ops": "binary min-heap array: sift-up insertions, sift-down extract-min",
    "R2.cache_eviction": "simulate a capacity-c cache under LRU or FIFO; misses or final membership",
    "R2.hash_probe": "linear-probing insertion mod m; final slot or probe count",
    "R2.bracket_match": "stack matching of bracket kinds; validity or partner position",
    "R2.expression_eval": "evaluate an infix expression with parentheses under usual precedence or strict left-to-right",
    "R2.interval_scheduling": "maximum set of non-overlapping intervals (earliest-finish greedy)",
    "R2.merge_smallest_cost": "Huffman merging: repeatedly join the two smallest, sum the costs",
    "R2.cheapest_network": "minimum spanning tree weight (Kruskal or Prim)",
    "R2.deferred_acceptance_partner": "proposer-proposing Gale-Shapley; report one partner",
    "R2.cellular_automaton": "synchronous 1-D three-neighbour rule-table update, zero boundary, k steps",
    "R2.chip_toppling": "1-D abelian sandpile (threshold 2, sinks at both ends) stabilisation",
    "R2.luhn_check": "Luhn checksum (double every second digit from the right, minus 9); validity or check digit",
    "R2.hamming_error_position": "Hamming-code syndrome: parity of each check group, failing checks sum to the position",
}
EXISTING = list(PROC)[:16]
NEW = list(PROC)[16:]
assert len(PROC) == 42 and len(NEW) == 26

MERGE_BOTH = {
    ("R2.kth_smallest", "R2.sort_list"): "same procedure (sort); only the final question differs (whole order vs position k). Lead ruling: final question is a parameter.",
}
MERGE_STRICT_ONLY = {
    ("R2.count_divisible", "R2.count_letter"): "same procedure (linear scan with a predicate counter); differ in objects and predicate. Ambiguous sentence: whether a predicate is 'constraint mix / surface frame' (parameter) or part of 'a distinct solution procedure' (ADR-0033 s6.2 first bullet). Strict: merge; lenient: keep.",
    ("R2.from_base", "R2.to_base"): "inverse directions of positional base conversion; lead ruling lists 'number system' and 'final question' as parameters, and the same batch already bundles inverse directions as one lineage (dictionary_rank: rank and unrank). Lenient: keep (division vs Horner are different update rules).",
    ("R2.modular_power", "R2.permutation_power"): "both iterate a map from a start t times and are solved fastest by finding the cycle and reducing t; the map (table lookup vs multiply mod m) is data. Lenient: keep (square-and-multiply exists only for modular_power; map is not in the lead's parameter list).",
}
NEAR_MISS = {
    ("R2.count_divisible", "R2.multiples_between"): "both count multiples of m under a bound, but explicit list scan vs floor-division formula over a range; kept apart (algorithm differs).",
    ("R2.count_letter", "R2.grid_sum"): "scan-and-aggregate, but grid_sum's work is 2-D indexing of a line; kept apart.",
    ("R2.count_divisible", "R2.grid_sum"): "as above; kept apart.",
    ("R2.longest_palindromic_substring", "R2.palindrome_check"): "LPS adds an outer search over centres; a one-shot reverse comparison is a different algorithm; kept apart.",
    ("R2.dictionary_rank", "R2.to_base"): "unrank is mixed-radix (factorial) digit extraction, but the Lehmer step (k-th remaining letter) is extra; kept apart.",
    ("R2.dictionary_rank", "R2.from_base"): "rank is mixed-radix evaluation, but the Lehmer step (count smaller remaining letters) is extra; kept apart.",
    ("R2.coin_change_min", "R2.subtraction_game"): "same table over 0..N looking back by each move, but cell rule differs (min+1 vs exists-losing-predecessor); kept apart.",
    ("R2.lcs_length", "R2.lis_length"): "LIS = LCS(xs, sorted xs) is a known reduction, but nobody solves LIS that way; different recurrences; kept apart.",
    ("R2.lis_length", "R2.max_subarray_sum"): "1-D DPs with different recurrences (subsequence vs contiguous); kept apart.",
    ("R2.cheapest_network", "R2.interval_scheduling"): "both 'sort by key, accept if compatible' greedies; compatibility test differs (cycle/union-find vs last end); kept apart.",
    ("R2.merge_smallest_cost", "R2.min_heap_ops"): "Huffman uses a priority queue conceptually, but the task is the greedy, not the heap layout; kept apart.",
    ("R2.binary_search_trace", "R2.bst_traversal"): "binary search walks an implicit BST, but midpoint arithmetic vs explicit insertion + traversal; kept apart.",
    ("R2.cellular_automaton", "R2.chip_toppling"): "both 1-D local dynamics; synchronous table rule vs asynchronous threshold toppling; kept apart.",
    ("R2.hamming_error_position", "R2.luhn_check"): "both check-digit codes; parity groups/XOR vs weighted digit sum mod 10; kept apart.",
    ("R2.crt_smallest", "R2.gcd_euclid"): "extended Euclid can build CRT solutions, but the generated items are solved by stepping a congruence class; kept apart.",
    ("R2.gcd_euclid", "R2.prime_factor_query"): "gcd can be found by factorising; intended procedures differ; kept apart.",
    ("R2.bracket_match", "R2.stack_machine"): "both use a stack, but matching vs executing an op list; kept apart.",
    ("R2.expression_eval", "R2.stack_machine"): "evaluation of infix with precedence vs executing explicit stack ops (postfix-like); kept apart.",
    ("R2.bracket_match", "R2.expression_eval"): "parenthesis matching is a sub-step of expression parsing only; kept apart.",
    ("R2.cache_eviction", "R2.list_ops"): "FIFO cache is a queue simulation, list_ops is deque editing; different op sets; kept apart.",
    ("R2.digit_root", "R2.luhn_check"): "both add digits; Luhn's doubling/positions make it a different procedure; kept apart.",
    ("R2.modular_power", "R2.to_base"): "square-and-multiply reads the exponent's binary digits; kept apart.",
    ("R2.caesar_shift", "R2.permutation_power"): "both apply a fixed map; caesar applies once per letter with modular arithmetic; kept apart.",
}


def key(a, b):
    return tuple(sorted((a, b)))


for d in (MERGE_BOTH, MERGE_STRICT_ONLY, NEAR_MISS):
    for k in list(d):
        assert k == key(*k), k
        assert k[0] in PROC and k[1] in PROC, k

pairs = []
for a, b in itertools.combinations(sorted(PROC), 2):
    k = (a, b)
    if k in MERGE_BOTH:
        v, why = "MERGE (strict and lenient)", MERGE_BOTH[k]
    elif k in MERGE_STRICT_ONLY:
        v, why = "MERGE strict / KEEP lenient (ambiguous)", MERGE_STRICT_ONLY[k]
    elif k in NEAR_MISS:
        v, why = "KEEP (near miss)", NEAR_MISS[k]
    else:
        v, why = "KEEP", "different update rule or data structure (see the two procedure lines)"
    pairs.append({"a": a, "b": b, "verdict": v, "reason": why})
assert len(pairs) == 861


def clusters(merges, ids):
    parent = {i: i for i in ids}

    def f(x):
        while parent[x] != x:
            x = parent[x]
        return x

    for a, b in merges:
        if a in parent and b in parent:
            parent[f(a)] = f(b)
    return len({f(i) for i in ids})


strict = list(MERGE_BOTH) + list(MERGE_STRICT_ONLY)
lenient = list(MERGE_BOTH)
counts = {
    "existing_16": {"strict": clusters(strict, EXISTING), "lenient": clusters(lenient, EXISTING)},
    "new_26": {"strict": clusters(strict, NEW), "lenient": clusters(lenient, NEW)},
    "overall_42": {"strict": clusters(strict, list(PROC)), "lenient": clusters(lenient, list(PROC))},
}

CROSS = {
    "strong (same algorithm, same kind of question)": [
        ["R2.interval_scheduling", "R1.activity_selection"],
        ["R2.cheapest_network", "R1.mst_cost"],
        ["R2.deferred_acceptance_partner", "R1.stable_matching", "R1.stable_matching_r2"],
        ["R2.crt_smallest", "M1.crt_congruence"],
        ["R2.prime_factor_query", "M1.prime_factors"],
        ["R2.gcd_euclid", "C1.euclid_gcd (traced)", "M1.gcd_lcm"],
        ["R2.modular_power", "C1.fast_power (traced)", "M1.last_digit_power"],
        ["R2.lcs_length", "C1.string_pair_table (traced LCS table)"],
        ["R2.coin_change_min", "C1.coin_change_table (traced min-coin / ways DP)", "M1.min_cost_packs (unbounded min-cost)"],
        ["R2.max_subarray_sum", "C1.kadane_scan (traced)"],
        ["R2.binary_search_trace", "C1.binary_search (traced)"],
        ["R2.bracket_match", "C1.bracket_matching (traced)"],
        ["R2.cellular_automaton", "C1.cellular_update (traced, periodic boundary)"],
        ["R2.run_length", "C1.run_length_scan (traced)"],
        ["R2.stack_machine", "C1.postfix_evaluation (traced)"],
        ["R2.list_ops", "R1.containers_queue_line (deque edits)"],
    ],
    "weaker (same paradigm or a sub-step)": [
        ["R2.subtraction_game", "R1.nim_xor", "R1.minimax_tree"],
        ["R2.coin_change_min", "M1.change_ways"],
        ["R2.digit_root", "C1.digit_peel"],
        ["R2.to_base", "C1.digit_peel"],
        ["R2.palindrome_check", "C1.mirror_pointers"],
        ["R2.sort_list", "C1.bubble_pass", "C1.insertion_sort"],
        ["R2.kth_smallest", "M1.median_list"],
        ["R2.multiples_between", "M1.division_counting"],
        ["R2.count_divisible", "C1.counter_list"],
        ["R2.stack_machine", "R1.containers_stack_piles"],
    ],
}

QUALITY = {
    "key_check": "auditor question-only solvers: 3,640/3,640 fixture items agree (26 x 140); 182,000/182,000 freshly drawn items agree (26 x 7 levels x 1,000, seed 2025112501); 0 errors",
    "ambiguous_wording": {
        "R2.expression_eval (left_to_right)": "does the left-to-right rule also apply INSIDE parentheses? 24/65 LTR fixture items change key if usual precedence is used inside parentheses",
        "R2.expression_eval (ranked)": "'operators of the same kind are done from left to right' can be read as same symbol; 15/75 ranked fixture items change key if '+' is done before '-'",
        "R2.merge_smallest_cost": "does not say that ANY two piles may be joined; 101/140 fixture items change key under the classic adjacent-piles reading",
    },
    "existing_16_notes": ["R2.string_rewrite draws identity rules (e.g. replace 'c' with 'c'), seen in rendered samples", "R2.to_base level 0 has only 755 possible items (151 values x 5 bases)"],
}

SHORTCUTS = {
    "R2.chip_toppling": "ask=lost: chips - (n-1) correct 0.82-0.90 per level; ask=final: conservation-invariant formula correct 0.97-1.00 (n=1.6-1.7k per level)",
    "R2.bracket_match": "valid: 'no adjacent wrong-kind pair' 0.84-0.87 (two-sided vs 0.5); match: 'second same-kind closer' 0.58-0.76, 'last position' (mode) 0.18-0.39 - overshoot from excluding the next same-kind closer",
    "R2.coin_change_min": "ceil(amount/largest)+1 correct 0.55-0.69 - overshoot from rejecting ceil(amount/largest)",
    "R2.hash_probe": "slot: home + earlier same-home keys 0.67-0.79, home+1 0.56-0.68; probes: constant '2' 0.38-0.51 - overshoot from 80% displaced targets",
    "R2.cache_eviction": "present: author's 'item among last cap requests' 0.60-0.64 (LRU 0.75, FIFO 0.50), 'requested in second half' 0.62-0.67, 'is the last request' 0.61-0.62; all above 0.5 with CI excluding it",
    "R2.subtraction_game": "author's n mod (largest+1) raw 0.39-0.41 (overshoot: inverted 0.59-0.61); n mod (smallest+largest) 0.55-0.60; n mod sum 0.54-0.57",
    "R2.deferred_acceptance_partner": "own second choice 0.44-0.61 (chance 1/n = 0.17-0.33) - overshoot from excluding first choice; responder-optimal partner 0.62-0.76",
    "R2.cheapest_network": "cheapest-per-town minus cheapest cable 0.71 (L0), 0.49-0.51 (L1-2); n-1 cheapest + 1 step 0.55 (L0)",
    "R2.max_subarray_sum": "best run of non-negative numbers 0.36-0.59",
    "R2.gcd_euclid": "gcd: product of common primes 2,3,5,7 0.60-0.86 (partial factorisation); steps: constant '3' 0.27-0.38",
    "R2.merge_smallest_cost": "L0: ascending chain 0.735, sum*ceil(log2 n) 0.39",
    "R2.modular_power": "a^2 mod m 0.42 at L0 (0.17-0.29 elsewhere); Fermat reduction 0.46-0.69 (a valid method for prime m)",
    "R2.lcs_length": "mode 0.21-0.30; overlap-2 0.27-0.35; greedy both directions 0.64 at L0",
    "R2.lis_length": "mode 0.29-0.32 at every level; round(2 sqrt n)-2 0.28-0.41",
    "R2.longest_palindromic_substring": "mode 0.29 at L0",
    "R2.prime_factor_query": "ask=largest: constant 'largest prime of the pool' 0.17-0.21",
}

CAPACITY = {
    "method": "5,000 draws per lineage and level (seed 2025112501); distinct structured forms with names relabelled by first appearance; order-free counts for merge_smallest_cost, interval_scheduling, cheapest_network (isomorphism-invariant lower bound) and deferred_acceptance at n=3 (exact up to renaming)",
    "below_threshold": ["R2.merge_smallest_cost L0: 3,498 ordered but 488 order-free (<1,000); the answer depends only on the multiset", "R2.to_base (existing) L0: 755 (<1,000); exact space 151 x 5"],
    "tight_but_passing": ["R2.deferred_acceptance_partner L1: 1,820 up to renaming in 5,000 draws (>=1,800)", "R2.crt_smallest L0 1,212, L1 2,215", "R2.subtraction_game L0 1,319, L1 2,316", "R2.prime_factor_query L0 1,431", "R2.coin_change_min L0 1,456", "R2.modular_power L0 1,579"],
}

FEAS = "JUDGEMENT (not measured): with the present material, strict 38 lineages over 23 family names ~ 19 per part; if the strong cross-evaluation duplicates were removed from R2 (lead's call), ~24 strict, ~12 per part. With further authoring under the strict reading I judge about 25-45 strict lineages per part reachable for R2; 300 per part is not reachable under the strict reading."

J = {"auditor_model": "claude-opus-5-5 (Opus 5.5), from session metadata", "astra_review": "NOT_PERFORMED", "not_human_approval": True,
     "written_before_reading": ["studies/m0/manifests/r2_batch1_manifest.json", "studies/m0/manifests/r2_batch1_shortcuts.json", "studies/m0/NOTES*.md"],
     "procedures": PROC, "pairs": pairs, "cluster_counts": counts, "cross_evaluation": CROSS, "quality": QUALITY,
     "shortcuts": SHORTCUTS, "capacity": CAPACITY, "feasibility": FEAS}
blob = json.dumps(J, indent=1, sort_keys=True).encode()
open(OUT, "wb").write(blob)
h = hashlib.sha256(blob).hexdigest()
open(OUT + ".sha256", "w").write(f"{h}  {OUT.rsplit('/', 1)[-1]}\n")
print(json.dumps(counts))
print(h)
