# ruff: noqa
"""Cross-evaluation map (M0), step 2: write cross_evaluation_procedures_proposed.json.

Inputs: the four fix-4 survivor manifests (read-only worktree on claude/m0-impl, uncommitted files read as they are) for the
lineage lists and the per-evaluation strict cluster maps; the procedure statements and pair grades below are this auditor's
judgement, made from the generators' rendered items (s01_samples.out.txt, s02_unregistered_neighbours.out.txt) BEFORE reading
any author's notes or the audit3/audit4 overlap lists. Standard library only.

Attempt 1 (kept as s03_build_map_attempt1_failed.py) used "M1."-prefixed M1 cluster ids; the M1 map has none.
Run: uv run --locked --project <impl worktree> python s03_build_map.py <impl worktree> > s03_build_map.out.txt
"""
import hashlib, json, sys
from pathlib import Path

W = Path(sys.argv[1])
MAN = W / "studies/m0/manifests"
OUT = Path(__file__).resolve().parent / "cross_evaluation_procedures_proposed.json"

# ---------------------------------------------------------------- per-lineage procedure statements (one line each)
PROC = {
    # R1
    "R1.boolean_lights_r4": "Bit-vector toggling: for the asked lamp, XOR its start state with the parity of presses of switches that cover it (simulate XOR updates).",
    "R1.compass_turns": "Heading accumulation modulo 4: sum the turns (right=+1, left=-1, around=+2, k*90 deg) mod 4 from the start heading; walks are no-ops.",
    "R1.categories_default_exceptions_r4": "Inheritance with exceptions: walk up the is-a chain from the entity and return the property value of the first (most specific) ancestor that has a rule.",
    "R1.conditional_decision_tree_r6": "Evaluate a nested if-then-else decision tree on a given truth assignment (follow one root-to-leaf path).",
    "R1.conditional_threshold_rule_r4": "Signed weighted sum: sum the weights of yes voters minus no voters and compare with the threshold.",
    "R1.equivalence_exchange_rates_r6": "Path in a ratio graph: find a chain of stated equivalences linking the two goods and multiply/divide the ratios along it.",
    "R1.temporal_weekday_shift_r6": "Path in an offset graph: find a chain of stated day offsets from the anchored event to the asked one, sum the signed offsets, read the weekday mod 7.",
    "R1.graph_shortest_route_r6": "Single-pair shortest path on a small weighted undirected graph (Dijkstra or exhaustive path comparison).",
    "R1.knights_knaves_r6": "Boolean constraint satisfaction: find the (unique) knight/knave assignment consistent with every statement (enumeration or propagation).",
    "R1.spatial_grid_walk_r5": "Grid position simulation: apply unit moves N/S/E/W from the start cell, skipping moves into walls or off the map; read the final cell.",
    "R1.swap_tracking_r5": "Permutation tracking: apply the sequence of transpositions and 3-cycles to the holder->item map and read one holder's item.",
    "R1.venn_counting_r5": "Inclusion-exclusion over 2-4 sets: recover Venn region counts from the stated intersections and read none / exactly-k.",
    # R2
    "R2.binary_search_trace": "Binary search on a sorted list with the stated midpoint and update rules; report the probed values in order.",
    "R2.caesar_shift": "Caesar cipher: shift each letter by k mod 26.",
    "R2.cellular_automaton": "Elementary 1-D cellular automaton: apply the stated 3-neighbour rule table synchronously for t steps with zero boundary.",
    "R2.cheapest_network": "Minimum spanning tree total weight (Kruskal or Prim) on a small weighted graph.",
    "R2.count_divisible": "Filter-and-accumulate: sum (with multiplicity) the list entries satisfying a divisibility and threshold predicate.",
    "R2.crt_smallest": "Smallest positive solution of a system of 2-3 congruences (Chinese remainder theorem / sieving).",
    "R2.dictionary_rank": "Lexicographic rank / unrank of a k-permutation of a letter set (mixed-radix counting of permutations).",
    "R2.digit_root": "Digital root: repeatedly sum decimal digits until one digit remains (equivalently n mod 9 rule).",
    "R2.expression_eval": "Evaluate an infix arithmetic expression with parentheses under a stated precedence rule (usual or strictly left-to-right).",
    "R2.from_base": "Positional base-b to decimal conversion (Horner evaluation of the digit string).",
    "R2.grid_sum": "Sum the entries of one stated row or column of a small matrix.",
    "R2.interval_scheduling": "Greedy interval scheduling: repeatedly take the compatible meeting with the earliest end (tie: smaller number); list chosen.",
    "R2.list_ops": "Simulate a sequence of list operations (remove first/last, append, move first to end, reverse) and print the list.",
    "R2.luhn_check": "Luhn checksum: double every second digit from the right, cast out nines, sum, test (or solve for) a multiple of 10.",
    "R2.min_heap_ops": "Binary min-heap: insert with sift-up and extract-min with sift-down as stated; print the array.",
    "R2.run_length": "Run-length encoding of a letter string (letter followed by run length).",
    "R2.sort_list": "Sort a list of integers ascending or descending.",
    "R2.string_rewrite_nonidentity": "Sequential string rewriting: for each rule in order, replace all non-overlapping left-to-right matches (str.replace semantics).",
    # M1
    "M1.ages_r3": "Linear equation in one unknown (ratio of ages now, sum later): solve k*x + x + 2t = S.",
    "M1.arithmetic_series_r3": "Sum of an arithmetic progression (iterate the constant step or closed form n/2*(2a+(n-1)d)).",
    "M1.average_missing_r4": "Linear equation in one unknown: required next score = target mean * n - sum of known scores.",
    "M1.change_ways_r3": "Count the multisets of coins (unbounded) summing to an amount (counting DP or nested enumeration).",
    "M1.clock_duration_r4": "Time arithmetic: convert hh:mm to minutes, sum the per-leg arrival-minus-departure differences.",
    "M1.consecutive_r3": "Linear equation in one unknown: k terms of an arithmetic sequence with known step summing to S; solve for the first and read the last.",
    "M1.crt_congruence_r3": "Smallest positive solution of a system of 2-4 congruences (Chinese remainder theorem / sieving).",
    "M1.division_counting_r3": "Two-level floor division and remainder (mixed-radix decomposition: items -> full boxes -> full pallets; read a leftover).",
    "M1.finite_differences_r4": "Polynomial extrapolation by a finite-difference table (degree stated), extending to the asked position.",
    "M1.fraction_remainder_r3": "Multiplicative chain: apply successive 'spend fraction of what is left' multipliers to an amount.",
    "M1.gcd_lcm_r4": "GCD or LCM of 2-4 integers (Euclid's algorithm, lcm via a*b/gcd; or prime factorisation).",
    "M1.grid_perimeter_r3": "Exposed-face count: perimeter of a polyomino as 4*cells - 2*shared edges.",
    "M1.inclusion_exclusion_r3": "Inclusion-exclusion over 3 sets: |A u B u C| from singles, pairwise and triple counts.",
    "M1.last_digit_power_r3": "Power remainder: (sum of) a^n mod m, by fast modular exponentiation or the cycle of powers mod m.",
    "M1.linear_equation_r3": "Linear equation in one unknown: a*x + b = c*x + d.",
    "M1.median_list_r3": "Sort the values and take the middle (mean of the two middle values for an even count).",
    "M1.mixture_r4": "Weighted sum then divide: (sum of mass*price + extra per kg) / total mass.",
    "M1.painted_cube_r3": "Exposed-face count on a box of unit cubes with one unpainted face: count cubes with exactly k painted faces by face/edge/corner classes.",
    "M1.percent_change_r3": "Multiplicative chain: apply successive percentage multipliers (1 +/- p/100) to a price.",
    "M1.pipes_work_r3": "Linear rate equation: time = volume / (sum of inflow rates - outflow rate).",
    "M1.prime_factors_r3": "Prime factorisation by trial division; read the largest prime factor or the divisor count.",
    "M1.quadratic_area_r3": "Solve w*(w+d) = A for positive integer w (quadratic formula or search).",
    "M1.ratio_share_r3": "Multiplicative chain: share = total / (sum of ratio parts) * own parts.",
    "M1.rectangle_r3": "Linear equation from perimeter and side difference, then area = w*(w+d).",
    "M1.recurrence_iterate_r3": "Iterate a first-order additive recurrence a_n = a_{n-1} + c*n from a_1 to position N.",
    "M1.shopping_r3": "Weighted sum: sum of quantity*unit price, then change = paid - total.",
    "M1.speed_distance_r3": "Weighted sum: sum of hours*speed over legs.",
    "M1.tiered_pricing": "Tiered (piecewise-linear) charge: split the quantity across brackets and sum units*rate per bracket.",
    "M1.tip_split_r3": "Multiplicative chain: bill * (1 + tip%) / people.",
    # C1 (the program's algorithm)
    "C1.binary_search_f3": "Program: binary search (classic or lower-bound variant) over a sorted list, printing the probe/direction trace.",
    "C1.bracket_matching_f3": "Program: stack-based bracket matching over a bracket string, accumulating matched positions / mismatch counts.",
    "C1.bytecode_loop_f3": "Program: interpreter loop over (opcode, argument) pairs with an accumulator, a register and conditional skips.",
    "C1.circle_elimination_r2": "Program: Josephus-style circular elimination with a step count over a 0/1 occupancy array.",
    "C1.cond_chain_f3": "Program: subtractive-Euclid-like two-variable loop (subtract smaller from larger; extra equal/halving branches), accumulating one variable.",
    "C1.counter_list_f3": "Program: finite-state machine over a list (state c updated mod 5 by parity rules) incrementing a counter array at the state.",
    "C1.digit_peel_f3": "Program: peel base-b digits by repeated % and // and recombine them (Horner in another base, or position-weighted digit sum).",
    "C1.euclid_gcd_traced_f3": "Program: Euclid's remainder steps (a, b) -> (b, a mod b), capped at 2 rounds, accumulating weighted remainders.",
    "C1.fast_power_f4": "Program: square-and-multiply loop over the exponent's bits, but the squaring step is perturbed (r = r*r + c mod n), so it is not a power.",
    "C1.fib_like_f3": "Program: iterate a two-term linear recurrence (Fibonacci-like) for n steps.",
    "C1.fib_shapes_recursive_f3": "Program: recursive two-term recurrence f(n) = a*f(n-1) + b*f(n-2) + c with base cases.",
    "C1.func_branch_f4": "Program: evaluate a piecewise (if/elif/else) integer function at a few arguments and combine.",
    "C1.func_compose_f4": "Program: evaluate composed small integer functions at a few arguments and combine.",
    "C1.list_build_f3": "Program: loop over a range, filter by a modulus test and append a computed value (filter-map).",
    "C1.merge_two_sorted_f3": "Program: two-pointer merge of two sorted lists, accumulating a statistic of the compared pairs.",
    "C1.nested_pairs_f3": "Program: double loop over index pairs with a condition, accumulating a function of the pair.",
    "C1.postfix_evaluation": "Program: stack-based postfix (RPN) arithmetic evaluation, accumulating intermediate results.",
    "C1.recursive_calls_r2": "Program: divide-style recursion h(j) = a*h(j//2) + b*h(j - j//2) + j%2 with base case.",
    "C1.run_length_scan": "Program: run-length encoding scan of a string (letter followed by run length).",
    "C1.shared_lists_f3": "Program: Python list aliasing / copy semantics through assignments and a mutating function.",
    "C1.sieve_marking_f4": "Program: Eratosthenes-style marking of multiples over a pre-marked 0/1 array, summing the marked indices.",
    "C1.slices_f4": "Program: Python slice semantics (start/stop/step incl. negatives) on a list, concatenated.",
    "C1.string_build_f3": "Program: loop over a range appending a character chosen by modulus tests, then reverse.",
    "C1.string_methods_f3": "Program: a chain of Python string methods (replace, slicing, upper/lower, concatenation).",
    "C1.turtle_walk_f3": "Program: turtle interpreter: heading mod 4 changed by turn opcodes, position (x, y) changed by move opcodes; print position.",
    "C1.union_find_links_f3": "Program: union-find with find by parent-pointer chasing and link of the larger root under the smaller; print the parent array.",
    "C1.while_counter_f3": "Program: Collatz iteration (n/2 or 3n+1) until 1, summing the values.",
}

# one-line statement per strict cluster (survivor members define it)
CPROC = {
    "R1.boolean_lights": "Modular state accumulation (bit-vector XOR toggles; heading mod 4) -- the R1 map's merge.",
    "S1_linear_solve": "Set up and solve one linear equation in one unknown.",
    "S2_weighted_sum": "Sum of products (quantity x rate), then a final arithmetic read-out.",
    "S3_multiplicative_chain": "Apply a chain of multiplicative factors to an amount.",
    "S5_unbounded_table": "Count coin combinations (unbounded).",
    "S6_exposed_faces": "Count exposed unit faces/edges of a cell arrangement.",
    "S7_step_rule": "Iterate / sum a sequence defined by an additive step rule.",
    "B1": "Loop over a range with a condition, building or accumulating (filter-map / filter-sum).",
    "B2": "Evaluate small user-defined integer functions (branching, composition).",
    "B3": "Python sequence/string semantics (slicing, string methods).",
    "B5": "Euclid-style two-variable remainder/subtraction loop.",
    "B6": "Recurrence evaluation (iterative or recursive).",
    "B7": "Opcode interpreter loop (accumulator machine; turtle).",
    "B8": "Stack algorithms over a token sequence (bracket matching; postfix evaluation).",
}

# ---------------------------------------------------------------- cross-evaluation pairs of strict clusters
# (cluster ids as in the four maps; 'via' names the lineages compared)
PAIRS = [
    # STRONG
    ("S1", "R2", "R2.binary_search_trace", "C1", "C1.binary_search", "STRONG", "R2.binary_search_trace ~ C1.binary_search_f3",
     "Both are binary search over a sorted list with a probe trace as the read-out; C1's lower-bound variant is a tie-break/parameter change under section 1 item 1."),
    ("S2", "R2", "R2.run_length", "C1", "C1.run_length_scan", "STRONG", "R2.run_length ~ C1.run_length_scan",
     "Identical algorithm: scan, count maximal runs, emit letter+count."),
    ("S3", "R2", "R2.crt_smallest", "M1", "crt_congruence", "STRONG", "R2.crt_smallest ~ M1.crt_congruence_r3",
     "Identical task: smallest positive x meeting 2-4 congruences; only the frame (a person thinking of a number) differs."),
    ("S4", "M1", "gcd_lcm", "C1", "B5", "STRONG", "M1.gcd_lcm_r4 ~ C1.euclid_gcd_traced_f3 (B5 also holds C1.cond_chain_f3)",
     "Euclid's remainder step is the shared algorithm; C1 reads a weighted remainder sum after at most 2 rounds (a different read-out of the same state). Against: M1 items are often solved by prime factorisation and the C1 trace is only 2 rounds; lcm needs a*b/gcd on top."),
    ("S5", "R1", "R1.venn_counting", "M1", "inclusion_exclusion", "STRONG", "R1.venn_counting_r5 ~ M1.inclusion_exclusion_r3",
     "Both recover Venn-region counts by inclusion-exclusion; R1 reads none/exactly-k over 2-4 sets, M1 reads the union over 3 sets (different read-out, set count is a parameter)."),
    ("S6", "R2", "R2.kth_smallest", "M1", "median_list", "STRONG", "R2.sort_list (cluster R2.kth_smallest, which also holds the unregistered R2.kth_smallest) ~ M1.median_list_r3",
     "The median is the middle order statistic of the sorted list; R2's own map already merged sorting with k-th smallest."),
    ("S7", "R2", "R2.from_base", "C1", "C1.digit_peel", "STRONG", "R2.from_base (cluster also holds the unregistered R2.to_base_wide) ~ C1.digit_peel_f3",
     "Positional base conversion: C1 peels base-b digits by % and // (to-base) and usually recombines them by Horner (from-base). Inverting the question is a same-cluster change under section 1 item 1, and R2's own map put both directions in one cluster. Against: survivor-to-survivor, R2.from_base is only the Horner direction."),
    # BORDERLINE
    ("B1", "R1", "R1.boolean_lights", "C1", "B7", "BORDERLINE", "R1.compass_turns ~ C1.turtle_walk_f3",
     "For: a turtle interpreter keeps heading mod 4 exactly as compass_turns does; R1 asks a different read-out (heading). Against: the turtle also keeps (x, y) and the read-out is the position, so the maintained data structure differs (section 1 item 1, last sentence); and merging would pull R1's bit-toggle lineage and C1's bytecode interpreter into one component."),
    ("B2", "R1", "R1.spatial_grid_walk", "C1", "B7", "BORDERLINE", "R1.spatial_grid_walk_r5 ~ C1.turtle_walk_f3",
     "For: both update a grid position by unit direction vectors and read the end point. Against: R1 moves are absolute with walls/edges; C1 moves are heading-relative with variable lengths and no walls."),
    ("B3", "R1", "R1.categories_default_exceptions", "C1", "C1.union_find_links", "BORDERLINE", "R1.categories_default_exceptions_r4 ~ C1.union_find_links_f3",
     "For: both chase parent pointers up a forest (find the first ancestor with a rule vs find the root). Against: union-find also performs unions and prints the whole parent array; R1 has no union step."),
    ("B4", "R1", "R1.graph_shortest_route", "R2", "R2.cheapest_network", "BORDERLINE", "R1.graph_shortest_route_r6 ~ R2.cheapest_network",
     "For: Dijkstra and Prim are the same greedy frontier expansion with a different key. Against: shortest path and minimum spanning tree are different problems and Kruskal (sort + union-find) is the usual MST route."),
    ("B5", "R1", "R1.equivalence_exchange_rates", "M1", "S3_multiplicative_chain", "BORDERLINE", "R1.equivalence_exchange_rates_r6 ~ M1.percent_change_r3 / fraction_remainder_r3",
     "For: both multiply a chain of ratios. Against: R1's core step is finding the path through a graph of equivalences; M1 gives the chain in order."),
    ("B6", "R1", "R1.conditional_threshold_rule", "M1", "S2_weighted_sum", "BORDERLINE", "R1.conditional_threshold_rule_r4 ~ M1.shopping_r3 / speed_distance_r3",
     "For: both are a weighted sum then a comparison/read-out. Against: the shared step is generic arithmetic; topic does not make lineages one (section 1 item 1) and neither does 'add numbers' alone."),
    ("B7", "R2", "R2.cheapest_network", "C1", "C1.union_find_links", "BORDERLINE", "R2.cheapest_network ~ C1.union_find_links_f3",
     "For: Kruskal's MST is union-find over sorted edges. Against: MST can be done by Prim without union-find, and C1 reads the parent array, which an MST total never needs."),
    ("B8", "R2", "R2.expression_eval", "C1", "B8", "BORDERLINE", "R2.expression_eval ~ C1.postfix_evaluation",
     "For: both evaluate arithmetic expressions with a stack. Against: R2 is infix with parentheses and a stated precedence rule (parsing), C1 is postfix (no parsing)."),
    ("B9", "R2", "R2.string_rewrite_nonidentity", "C1", "B3", "BORDERLINE", "R2.string_rewrite_nonidentity ~ C1.string_methods_f3",
     "For: R2 rewriting is exactly Python str.replace applied in sequence, which C1 string_methods uses. Against: C1 composes replace with slicing and case changes; replace is one step of several."),
    ("B10", "R2", "R2.count_divisible", "C1", "B1", "BORDERLINE", "R2.count_divisible ~ C1.list_build_f3 / nested_pairs_f3",
     "For: filter by a modulus/threshold test and accumulate. Against: generic loop-with-condition; C1 B1 is the 'no named algorithm' cluster."),
    ("B11", "R2", "R2.kth_smallest", "C1", "C1.merge_two_sorted", "BORDERLINE", "R2.sort_list ~ C1.merge_two_sorted_f3",
     "For: merging two sorted lists is merge sort's step. Against: sorting does not require merging, and C1 reads a statistic of the merge comparisons."),
    ("B12", "R2", "R2.digit_root", "C1", "C1.digit_peel", "BORDERLINE", "R2.digit_root ~ C1.digit_peel_f3",
     "For: digit extraction and digit sums (C1's level-0 variant is a weighted digit sum). Against: R2 gives the decimal string, so no division is needed, and the digital root repeats the sum."),
    ("B13", "M1", "last_digit_power", "C1", "C1.fast_power_square_map", "BORDERLINE", "M1.last_digit_power_r3 ~ C1.fast_power_f4",
     "For: the C1 program has the square-and-multiply skeleton of fast modular exponentiation. Against: its squaring is perturbed (r*r + c), so it computes no power, and M1 is usually solved by the cycle of powers mod m."),
    ("B14", "M1", "S7_step_rule", "C1", "B6", "BORDERLINE", "M1.recurrence_iterate_r3 ~ C1.fib_like_f3",
     "For: iterate a recurrence to position n. Against: first-order with a position term (closed form exists) vs second-order linear; B6 also holds a divide recursion."),
    ("B15", "M1", "division_counting", "C1", "C1.digit_peel", "BORDERLINE", "M1.division_counting_r3 ~ C1.digit_peel_f3",
     "For: both extract mixed-radix digits by % and //. Against: M1 has two fixed steps with different divisors and a word-problem read-out; C1 iterates one base to zero."),
]

CONSIDERED_NOT_LINKED = [
    ("R1.temporal_weekday_shift_r6", "M1.clock_duration_r4", "Both are calendar/clock arithmetic, but R1 sums offsets along a graph path mod 7, and M1 subtracts base-60 times per leg."),
    ("R1.conditional_decision_tree_r6", "C1.func_branch_f4", "Both pick a branch of a conditional; this is generic, and the tree walk is not a piecewise numeric function."),
    ("M1.tiered_pricing", "C1.func_branch_f4", "Piecewise rates, but the tiered charge sums across brackets while func_branch selects one branch."),
    ("M1.prime_factors_r3", "C1.sieve_marking_f4", "Both are about primes, but trial-division factorisation and sieve marking are different algorithms; the topic alone does not link them."),
    ("R1.swap_tracking_r5", "R2.list_ops", "Both simulate operations on a sequence; the operations differ (permutations vs insert/delete/reverse)."),
    ("R2.list_ops", "C1.slices_f4", "List reversal appears in both; slice index arithmetic with steps is not deque simulation."),
    ("R2.luhn_check", "C1.digit_peel_f3", "Weighted digit sums appear in both; Luhn reads digits from text, with no division by a base."),
    ("R2.from_base", "M1.clock_duration_r4", "hh:mm to minutes is a two-digit base-60 conversion, but it is incidental to the duration procedure."),
    ("R2.cellular_automaton", "R1.boolean_lights_r4", "Synchronous bit-vector updates in both; the neighbourhood rule table and switch toggles are different updates."),
    ("M1.finite_differences_r4", "M1.recurrence_iterate_r3 / C1.B6", "Extrapolating an unknown polynomial from a difference table is not applying a stated rule."),
]

# unregistered lineages (NOT REGISTERED in their evaluation) whose procedure matches a survivor's cluster elsewhere: nodes of the
# addendum's graph (section 3 item 1) that carry the teaching ban (item 3, A9) but do not make a cluster cross-evaluation (section 4 step 1)
UNREG_LINKS = [
    ("R2.gcd_euclid", "M1.gcd_lcm / C1.B5", "STRONG", "R2 item asks an lcm of two numbers (s02)."),
    ("R2.modular_power", "M1.last_digit_power", "STRONG", "a^n mod m (s02); R2's map puts R2.permutation_power in the same cluster."),
    ("R2.prime_factor_query", "M1.prime_factors", "STRONG", "largest prime factor (s02)."),
    ("R2.bracket_match", "C1.B8 (bracket_matching_f3)", "STRONG", "stack bracket matching (s02)."),
    ("R2.stack_machine", "C1.B8 (postfix_evaluation)", "STRONG", "explicit push/arith stack machine (s02)."),
    ("C1.coin_change_table_f3 (dropped cluster B4)", "M1.S5_unbounded_table (change_ways_r3)", "STRONG", "counting DP over coins (s02)."),
    ("C1.cellular_update_f3 (dropped cluster C1.cellular_update)", "R2.cellular_automaton", "STRONG", "elementary CA, wrap-around boundary (s02)."),
    ("C1.bfs_queue (dropped cluster)", "R1.graph_shortest_route", "BORDERLINE", "BFS distances (unit weights) vs Dijkstra."),
    ("R1.activity_selection_r5 (NOT REGISTERED, name only)", "R2.interval_scheduling", "UNVERIFIED", "name suggests interval scheduling; not rendered by this auditor."),
]


def load_clusters():
    cl = {}
    d = json.loads((MAN / "r1_fix4_survivors.json").read_text())
    surv = set(d["surviving_shapes"])
    for c, mem in d["cluster_members"].items():
        cl[("R1", c)] = [m for m in mem if m in surv]
    d = json.loads((MAN / "r2_fix4_survivors.json").read_text())
    for c, v in d["clusters"].items():
        s = [m for m in v["members"] if v["member_status"].get(m) == "SURVIVES"]
        if s:
            cl[("R2", c)] = s
    d = json.loads((MAN / "m1_fix4_survivors.json").read_text())
    for c, mem in d["surviving_clusters"].items():
        cl[("M1", c)] = list(mem)
    d = json.loads((MAN / "c1_fix4_survivors.json").read_text())
    surv = set(d["surviving_lineages"]["list"])
    m = json.loads((MAN / "c1_fix4_clusters.json").read_text())["members"]
    for c in d["surviving_clusters"]["list"]:
        cl[("C1", c)] = [x for x in m[c] if x in surv]
    return cl, d["surviving_clusters"]["variant_clusters"]


def main():
    cl, c1_variants = load_clusters()
    lineages = []
    for (ev, c), mem in sorted(cl.items()):
        for lid in sorted(mem):
            lineages.append({"id": lid, "eval": ev, "strict_cluster": c, "procedure": PROC[lid]})
    ids = {x["id"] for x in lineages}
    missing = sorted(ids - set(PROC))
    extra = sorted(set(PROC) - ids)
    assert not missing, missing
    keys = set(cl)
    pairs = []
    for pid, e1, c1, e2, c2, g, via, why in PAIRS:
        assert (e1, c1) in keys and (e2, c2) in keys, (pid, e1, c1, e2, c2)
        assert e1 != e2
        pairs.append({"id": pid, "a": [e1, c1], "b": [e2, c2], "grade": g, "lineages_compared": via, "reason": why})
    doc = {
        "title": "M0 cross-evaluation procedure map -- PROPOSED by an independent auditor; not the map of record, not registered, nothing decided",
        "status": "PROPOSAL. The same-procedure test is the human lead's (addendum 1 draft 2, section 13 item 4). Astra review: NOT_PERFORMED.",
        "inputs": {k: hashlib.sha256((MAN / k).read_bytes()).hexdigest() for k in
                   ["r1_fix4_survivors.json", "r2_fix4_survivors.json", "m1_fix4_survivors.json", "c1_fix4_survivors.json", "c1_fix4_clusters.json"]},
        "c1_variant_clusters": c1_variants,
        "strict_clusters": [{"eval": ev, "cluster": c, "survivors": sorted(mem), "cluster_procedure": CPROC.get(c, PROC[sorted(mem)[0]] if len(mem) == 1 else "")}
                            for (ev, c), mem in sorted(cl.items())],
        "lineages": lineages,
        "pairs": pairs,
        "considered_not_linked": [{"a": a, "b": b, "reason": r} for a, b, r in CONSIDERED_NOT_LINKED],
        "unregistered_links": [{"unregistered": a, "survivor_cluster": b, "grade": g, "note": n} for a, b, g, n in UNREG_LINKS],
        "dropped_since_fix4": [],
    }
    OUT.write_text(json.dumps(doc, indent=1, sort_keys=False) + "\n")
    print("clusters per eval:", {e: sum(1 for (ev, _) in cl if ev == e) for e in ("R1", "R2", "M1", "C1")})
    print("lineages per eval:", {e: sum(1 for x in lineages if x["eval"] == e) for e in ("R1", "R2", "M1", "C1")})
    print("procedure statements not used (should be empty):", extra)
    print("pairs:", sum(p["grade"] == "STRONG" for p in pairs), "STRONG,", sum(p["grade"] == "BORDERLINE" for p in pairs), "BORDERLINE")
    print("wrote", OUT, "sha256", hashlib.sha256(OUT.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
