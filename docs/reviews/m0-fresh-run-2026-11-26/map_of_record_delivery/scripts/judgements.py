"""The map-of-record auditor's pair judgements (ADR-0033 addendum 1, draft 7 at d70ba38d, section 1 item 1 test).
Data only. Written by the auditor from the generators' code (studies/m0 at 7cd0ac5a / 206d45a9, code unchanged between them)
and a handful of rendered items (e04). Earlier judgements are quoted with their source; MINE is this auditor's re-reading.

Operational reading of the test (stated once, applied to every pair):
  LINK  - an algorithm that is the procedure of one of the two lineages as its code computes it, with only the listed changes
          (renaming; setting/surface frame; order of presentation; parameter values incl. sizes, depths, number systems, moduli,
          tie-break rules, asked position/extremum; negation/inversion; a different read-out of the same computed state),
          gives the answer of every item of the other, maintaining the same data structure with the same step dependencies.
  BORDERLINE - the core step or data structure is shared but the test does not decide: an added step or constraint type,
          a different maintained data structure for part of the work, an op set that differs, or only some shapes covered;
          also every pair the test leaves undecided where an earlier auditor had LINK or BORDERLINE (brief + section 1 item 3).
  NONE  - only topic, vocabulary, answer type or generic arithmetic is shared, or the algorithms differ outright.
Revisions of one written base rule (a later id that REPLACES/SUPERSEDES/re-files an earlier id of the same stem) are judged
LINK unless the procedure changed (listed explicitly below)."""

# (id_a, id_b, earlier, earlier_source, mine, reason)
P = []
def add(a, b, earlier, src, mine, reason):
    P.append((a, b, earlier, src, mine, reason))
def group(ids, earlier, src, mine, reason):
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            add(ids[i], ids[j], earlier, src, mine, reason)

A2 = "audit2_r1 JUDGEMENT_PART1_CLUSTERS.md (= lineages_r1_clusters_v2.STRICT_MERGES_V2)"
A3R1 = "audit3_r1 AUDIT3_R1.md s2"
A4R1 = "audit4_r1 my_clusters4.py MINE/BORDER"
A1 = "audit1 pairs_judgement.csv"
V2B = "lineages_r1_clusters_v2.BORDERLINE (audit 2 strictest)"
# ---------------------------------------------------------------- R1 within
group(["R1.order_compare", "R1.road_reachability", "R1.categories_follow", "R1.equivalence_classes"], "LINK", f"{A2}; {A3R1}; {A4R1} (audit1: order~road and categories~equivalence LINK, order~categories near-miss)", "LINK",
      "Closure of a stated binary relation, read three-valued (or two-valued). categories_follow's procedure (closure of 'All' edges + lifting of 'No' through the closure) answers road (reachability = read-out), order_compare (inverted question for 'no') and equivalence (symmetric relation = setting; 'different' = 'No').")
group(["R1.event_timeline", "R1.temporal_weekday_shift", "R1.spatial_relative_directions", "R1.equivalence_exchange_rates"], "LINK", f"{A1}; {A2}; {A4R1}", "LINK",
      "Propagate potentials along a path of a tree of pairwise offset facts and read a difference; Z, Z mod 7, Z^2 (L1 read-out) and Q* are number systems, which the test lists as parameters.")
group(["R1.kinship_ancestor", "R1.kinship_cousins", "R1.categories_default_exceptions"], "LINK", f"{A1}; {A2}; {A4R1}", "LINK",
      "Follow parent pointers up a chain (k steps; compare two chases; stop at the first node with a rule): same data structure (parent map), same walk; stopping rule and read-out are parameters.")
group(["R1.knights_knaves", "R1.one_culprit", "R1.conditional_chain"], "LINK", f"{A1}/{A2} (knights~culprit); {A3R1} and {A4R1} add conditional_chain", "LINK",
      "Enumerate assignments of a finite hypothesis space, keep those consistent with every stated clause, read the asked variable; knights_knaves' procedure answers conditional_chain (entailed / refuted / neither = read-out over the consistent models) and one_culprit (one-hot hypotheses, true-count constraint).")
group(["R1.attribute_rule", "R1.conditional_decision_tree", "R1.minimax_tree", "R1.elimination_bracket"], "LINK", f"{A1} (attribute~tree); {A2} (+minimax); {A3R1}/{A4R1} (+bracket)", "LINK",
      "Evaluate an expression tree bottom-up (AND/OR, if-then-else, MIN/MAX, head-to-head winner): the node operator is a number system/parameter; same tree, same dependency of a node on its children.")
add("R1.compass_turns", "R1.boolean_lights", "LINK", f"{A1}; {A2}; {A4R1}", "LINK",
    "Fold a command sequence into a cyclic-group accumulator (Z4 heading, Z2 lamp parity), ignoring the other commands; number system is a parameter.")
add("R1.seating_row", "R1.pet_owners", "LINK", f"{A1}; {A2}", "LINK",
    "Find the unique permutation (people to seats / pets) consistent with every clue by elimination; clue types are parameter values of one constraint test over permutations.")
add("R1.order_extreme", "R1.order_tournament_wins", "LINK", f"{A1}; {A2}", "LINK",
    "Tally per-person counts of a stated pairwise relation and take the extremum (zero losses in a chain = most wins); which extremum is asked is a listed parameter.")
add("R1.order_extreme", "R1.topological_order", "LINK", A2, "LINK",
    "Kahn's ordering of a precedence DAG read at a position; order_extreme is that ordering read at position 1 or n of a chain (asked position is a listed parameter).")
add("R1.order_tournament_wins", "R1.topological_order", "LINK", A2 + " (same merge group)", "BORDERLINE",
    "Tally-and-argmax over a round robin (cyclic in general) is not Kahn's ordering; the test does not decide this pair on its own (joined transitively through order_extreme in any case).")
add("R1.containers_queue_line", "R1.elimination_josephus", "LINK", A2, "LINK",
    "Simulate a FIFO line under front-to-back and serve operations; Josephus counting is that operation pattern (k-1 moves, then serve); same queue, same dependency.")
# R1 borderline (earlier)
for a, b, src, why in [
    ("R1.knights_knaves", "R1.seating_row", V2B + "; " + A4R1, "Generate-and-test over a finite hypothesis space, but Boolean vectors versus permutations: the maintained data structure differs."),
    ("R1.one_culprit", "R1.seating_row", A4R1, "As knights_knaves~seating_row."),
    ("R1.temporal_critical_path", "R1.graph_shortest_route", V2B, "Optimal path weight by relaxation: max-plus DP on a DAG versus Dijkstra (min-plus, priority queue) on an undirected graph; frontier structure differs."),
    ("R1.mst_cost", "R1.graph_shortest_route", V2B, "Prim is Dijkstra with a different key; but MST by Kruskal (sort + union-find) is a different structure, so not decided."),
    ("R1.activity_selection", "R1.mst_cost", V2B, "Sort by a key and greedily accept compatible items; the compatibility test (interval overlap / cycle) differs."),
    ("R1.instant_runoff", "R1.order_tournament_wins", V2B, "Tally and take an extremum, iterated with elimination in instant_runoff: added elimination and transfer steps."),
    ("R1.nim_xor", "R1.boolean_lights", V2B, "XOR/parity fold, but the game needs the Bouton reduction (not a listed change) before the fold."),
    ("R1.graph_bipartite", "R1.equivalence_classes", V2B + "; " + A4R1, "Propagation of same/different constraints; parity propagation with conflict detection versus union of equals."),
    ("R1.spatial_grid_walk", "R1.compass_turns", V2B + "; " + A4R1, "Fold moves into a state; grid walk keeps a position with walls, compass keeps a heading: different maintained state."),
    ("R1.temporal_critical_path", "R1.topological_order", V2B + "; " + A4R1, "Process a prerequisite DAG in topological order; critical path adds max-plus accumulation, topological_order reads the priority order."),
    ("R1.conditional_chain", "R1.order_compare", "audit4_r1 ALT (PENDING LEAD REVIEW) / " + V2B + " had conditional_chain~knights_knaves", "Forward chaining is a Horn closure (exact on the shape, audit 4), but some rules have two antecedents (hypergraph closure), so it is not the plain relation closure of order_compare."),
    ("R1.tracking_accounts", "R1.swap_tracking", V2B + "; " + A4R1, "Multi-register transfer simulation; additive transfers versus permutations of items."),
    ("R1.tracking_accounts", "R1.containers_queue_line", A4R1, "Same borderline group (simulate operations on registers / a line); data structures differ."),
    ("R1.tracking_accounts", "R1.containers_stack_piles", A4R1, "Same borderline group; ledger versus stacks."),
    ("R1.swap_tracking", "R1.containers_queue_line", A4R1, "Same borderline group; permutation of a holder map versus a FIFO line."),
    ("R1.swap_tracking", "R1.containers_stack_piles", A4R1, "Same borderline group; permutation versus stacks with reversal."),
    ("R1.containers_queue_line", "R1.containers_stack_piles", A4R1 + " (audit1: near-miss)", "FIFO line versus several LIFO piles with reversal."),
    ("R1.instant_runoff", "R1.conditional_threshold_rule", V2B, "Weighted vote tally; runoff iterates elimination, threshold compares one signed sum."),
    ("R1.kinship_descendants", "R1.order_tournament_wins", V2B, "Count per element and take the argmax; subtree aggregation versus a flat tally."),
    ("R1.kinship_descendants", "R1.kinship_ancestor", A4R1 + " (audit1: near-miss)", "Same parent map; downward subtree aggregation versus upward chase."),
]:
    add(a, b, "BORDERLINE", src, "BORDERLINE", why)
# ---------------------------------------------------------------- R2 within
A3R2 = "audit_r2 AUDIT_M0_R2_1.md s2; audit3_r2 AUDIT3_R2.md s2; audit4_r2 AUDIT4_R2.md s5"
add("R2.sort_list", "R2.kth_smallest", "LINK", A3R2, "LINK", "Sort the list; the k-th smallest is a read-out of the sorted list.")
add("R2.count_letter", "R2.count_divisible", "LINK", A3R2, "LINK", "One linear scan with an integer accumulator gated by a predicate (letter match / divisible and above t); the predicate is a parameter value, the accumulator and dependency are the same.")
add("R2.to_base", "R2.from_base", "LINK", A3R2, "LINK", "Positional base conversion; from_base is the inverted question (the test lists inversion).")
add("R2.permutation_power", "R2.modular_power", "LINK", A3R2, "LINK", "Iterate a map t times from a start (x -> img[x]; x -> a*x mod m), shortened by reducing t on the cycle; number system is a parameter.")
for a, b, src, why in [
    ("R2.bracket_match", "R2.stack_machine", "audit3_r2 s2 'about 32' grain (r2_fix3_clusters.BORDERLINE_GROUPS)", "Both a single stack scanned left to right; matching versus arithmetic actions."),
    ("R2.bracket_match", "R2.list_ops", "audit3_r2 s2 grain", "Stack matching versus list operations; data structure differs (LIFO / general list)."),
    ("R2.stack_machine", "R2.list_ops", "audit3_r2 s2 grain; author's earlier borderline (audit_r2 kept apart)", "Command programs over a sequence; stack versus list, op sets differ."),
    ("R2.coin_change_min", "R2.lcs_length", "audit3_r2 s2 grain (C1 B4)", "Both DP tables, but a 1-D table over amounts versus a 2-D prefix table: dependency structure differs."),
    ("R2.count_letter", "R2.grid_sum", "audit3_r2 s2 grain (C1 B1)", "Fold over values; grid_sum has no predicate and reads a row/column/diagonal."),
    ("R2.count_divisible", "R2.grid_sum", "audit3_r2 s2 grain (C1 B1)", "As count_letter~grid_sum."),
    ("R2.to_base", "R2.digit_root", "audit3_r2 s2 grain (C1 digit_peel)", "Digit handling; digit_root reads given decimal digits and iterates a sum, no division by a base."),
    ("R2.from_base", "R2.digit_root", "audit3_r2 s2 grain", "As to_base~digit_root."),
    ("R2.subtraction_game", "R2.coin_change_min", "author's log via audit_r2 s8 (strictest); r2 cluster maps STRICTEST_EXTRA", "Same 1-D table over amounts with a move set, but a win/lose (mex) cell rule versus min-plus."),
    ("R2.dictionary_rank", "R2.to_base", "author's log via audit_r2 s8; r2 cluster maps STRICTEST_EXTRA", "Mixed-radix (factorial base) ranking versus fixed-base conversion; the Lehmer step adds counting of the remaining letters."),
]:
    add(a, b, "BORDERLINE", src, "BORDERLINE", why)
for a, b, why in [
    ("R2.digit_root", "R2.permutation_power", "Iterating a digit-sum to a fixed point versus applying a map t times: different maps and stopping rules (audit_r2 kept apart; the author's log merged)."),
    ("R2.palindrome_check", "R2.longest_palindromic_substring", "Compare a text with its reverse versus an outer search over centres."),
    ("R2.lcs_length", "R2.lis_length", "Two-sequence prefix table versus one-sequence LIS DP."),
    ("R2.lis_length", "R2.max_subarray_sum", "LIS DP versus best-ending-here scan."),
    ("R2.cheapest_network", "R2.interval_scheduling", "Both sort-then-accept, but the acceptance test (cycle / overlap) and structures differ."),
    ("R2.count_divisible", "R2.multiples_between", "List scan with a predicate versus a floor-division formula on a range."),
]:
    add(a, b, "NONE", "audit_r2 AUDIT_M0_R2_1.md s2 near-misses", "NONE", why)
# ---------------------------------------------------------------- M1 within
AM1 = "audit_m1 JUDGEMENT_1_clusters.txt; audit3_m1; audit4_m1 AUDIT4_M1.md s5 (= lineages_m1_fix3_clusters.GROUPS)"
group(["M1.linear_equation", "M1.ages", "M1.consecutive", "M1.average_missing", "M1.pipes_work", "M1.rectangle", "M1.coins"], "LINK", AM1, "LINK",
      "Set up one linear relation from the story and solve it for the unknown (coins: substitute the count equation into the value equation); the story is setting/frame, the asked read-out (area, the larger number) is a read-out.")
group(["M1.shopping", "M1.speed_distance", "M1.mixture"], "LINK", AM1, "LINK", "Sum of quantity x rate products, then a read-out (change, total or average, cost per kilogram).")
group(["M1.percent_change", "M1.fraction_remainder", "M1.tip_split", "M1.ratio_share"], "LINK", AM1 + " (ratio_share 'weakest')", "LINK",
      "Apply a chain of multiplicative factors to an amount; ratio_share is a chain of one factor (part / sum of parts), the factor's value a parameter.")
add("M1.binomial_choose", "M1.slot_permutations", "LINK", AM1 + " (audit_m1: AMBIGUOUS, strict only)", "BORDERLINE",
    "Both are the product rule, but unordered selection divides by the order (binomial coefficients) while slot filling counts ordered positions most-restricted-first: the test does not decide.")
add("M1.change_ways", "M1.min_cost_packs", "LINK", "audit_m1 S5 (AMBIGUOUS, strict only)", "LINK",
    "One table over amounts with unbounded reuse of each coin/pack; counting versus minimising is a change of semiring (number system), overbuying a parameter of the target.")
add("M1.grid_perimeter", "M1.painted_cube", "LINK", AM1, "LINK", "Count, per unit cell, the sides not shared with a neighbour of the shape; 2-D/3-D is a parameter, perimeter (total) versus cubes with f painted faces is a read-out of the same per-cell counts.")
add("M1.arithmetic_series", "M1.recurrence_iterate", "LINK", AM1, "LINK", "Apply a stated step rule n times, accumulating (add_index is an arithmetic-series sum; sum_prev_two / affine are other coefficient values of one linear recurrence).")
for a, b, src, why in [
    ("M1.gcd_lcm", "M1.crt_congruence", "audit3_m1/audit4_m1 borderline", "The lcm ask is a CRT sieve with every remainder 0; gcd ask and the coprime combination step differ."),
    ("M1.clock_duration", "M1.shopping", "audit4_m1 borderline (clock_duration + S2)", "Sum of differences of clock readings versus sum of products: shared summation only."),
    ("M1.tiered_pricing", "M1.shopping", "audit4_m1 borderline (tiered_pricing + S2)", "Weighted sum after allocating units to tiers; the allocation (and the inverse ask) is an added step."),
    ("M1.consecutive", "M1.arithmetic_series", "audit4_m1 borderline (S1 + S7)", "The same arithmetic-series sum, evaluated in one and inverted in the other; S1 solves a linear equation, S7 iterates."),
]:
    add(a, b, "BORDERLINE", src, "BORDERLINE", why)
for a, b, src, why in [
    ("M1.median_list", "M1.mode_tally", "audit_m1 near-miss (author's borderline)", "Sort and select versus tally and argmax."),
    ("M1.gcd_lcm", "M1.prime_factors", "audit_m1 near-miss", "Euclid / multiples versus trial-division factorisation."),
    ("M1.digit_puzzle", "M1.change_ways", "author's docstring note; audit_m1 distinct", "Filter candidates by clues versus count solutions with a table."),
    ("M1.finite_differences", "M1.recurrence_iterate", "cross_evaluation_map considered_not_linked", "Extrapolate an unknown polynomial from a difference table versus apply a stated rule."),
]:
    add(a, b, "NONE", src, "NONE", why)
# ---------------------------------------------------------------- C1 within
AC1 = "audit_c1 JUDGEMENT_C1_LINEAGES.md tier B; audit3_c1 s2; audit4_c1 AUDIT4_C1.md s6"
group(["C1.loop_sum", "C1.list_build", "C1.nested_pairs", "C1.string_build"], "LINK", AC1 + " (B1)", "BORDERLINE",
      "One loop skeleton (index range, predicate, fold), but the maintained data differ (integer, list, string) and nested_pairs adds a second loop; the test's last sentence (data structure) leaves this undecided.")
add("C1.func_branch", "C1.func_compose", "LINK", AC1 + " (B2)", "LINK", "Substitute literal arguments into small non-recursive function bodies and evaluate the calls; piecewise versus composed bodies are parameter values of one evaluation.")
add("C1.slices", "C1.string_methods", "LINK", AC1 + " (B3)", "LINK", "Evaluate a chain of Python sequence operations on a literal; string_methods' chain contains slicing, so its procedure answers slices (lists: same slicing semantics).")
group(["C1.coin_change_table", "C1.string_pair_table", "C1.grid_path_table"], "LINK", AC1 + " (B4)", "BORDERLINE",
      "All fill a DP table from earlier cells, but a 1-D table over amounts with coin offsets versus 2-D prefix tables (up/left, and diagonal for LCS/edit): dependency structure differs, so undecided.")
add("C1.cond_chain", "C1.euclid_gcd", "LINK", AC1 + " (B5; audit_c1: 'near the edge')", "BORDERLINE",
    "Subtractive rounds with a doubling and a halving branch versus the remainder form: the per-step update (and so the traced state) differs; same reduction idea.")
group(["C1.fib_like", "C1.fib_shapes_recursive", "C1.recursive_calls_r2", "C1.recursive_calls"], "LINK", AC1 + " (B6)", "LINK",
      "Evaluate an integer recurrence (iteratively or by expanding the call tree); recursive_calls was written as ONE lineage covering fib-like, halving, list and mutual recursions, so its revisions share it.")
add("C1.bytecode_loop", "C1.turtle_walk", "LINK", AC1 + " (B7)", "BORDERLINE",
    "Command-dispatch interpreter loops, but the maintained state differs (accumulator, register, pc skips versus position and heading).")
add("C1.bracket_matching", "C1.postfix_evaluation", "LINK", AC1 + " (B8)", "LINK", "Scan tokens with one array stack: push on one token class, pop and act on another; compare-kinds versus apply-operator is a parameter of the action.")
for a, b, src, why in [
    ("C1.bytecode_loop", "C1.postfix_evaluation", "audit3_c1 s2 borderline; audit4_c1 B7~B8", "Coded-instruction interpreters; accumulator machine versus stack."),
    ("C1.bubble_pass", "C1.partition_pass", "audit4_c1 borderline", "In-place swap passes; adjacent compare-swap versus Lomuto partition."),
    ("C1.mirror_pointers", "C1.run_length_scan", "audit4_c1 borderline", "String pointer scans; converging pair comparison versus run closing."),
    ("C1.fast_power_f3", "C1.digit_peel_f3", "audit4_c1 borderline", "The exponent loop is digit_peel's base-2 scan, but the carried squaring chain is extra state."),
    ("C1.counter_list_f3", "C1.bytecode_loop", "audit4_c1 borderline (counter_list_f3 ~ B7)", "Input-driven state machine update versus opcode dispatch."),
    ("C1.kadane_scan", "C1.minmax_track", "audit3_c1 borderline (audit_c1 near-miss)", "Running extremum; kadane keeps a second derived state (best-ending-here)."),
    ("C1.fast_power_f3", "C1.while_counter_f3", "audit4_c1 caveat (strictest reading merges base/bsum shapes)", "fast_power_f3's base and bsum shapes iterate a map a counted number of times, as while_counter's loops do; res shape uses the bits."),
]:
    add(a, b, "BORDERLINE", src, "BORDERLINE", why)
add("C1.counter_list", "C1.counter_list_f3", "NONE", "audit4_c1 s6 and lead ruling R-20 (own cluster); fix-3 implementer map filed both under C1.counter_list", "BORDERLINE",
    "Tally into k counters; f3's bucket is a loop-carried machine state (the dependency structure differs) although mul = 0 mod k gives the residue bucket of counter_list: undecided.")
add("C1.fast_power", "C1.fast_power_f3", "NONE", "audit4_c1 s6 and lead ruling R-20 (own cluster 'fast_power_square_map'); fix-3 implementer map filed f3 under C1.fast_power", "LINK",
    "The same square-and-multiply loop over the exponent's bits with the same variables and dependencies; the squaring step b = (b*b + c) % m has c = 0 in fast_power, a parameter value of one program (rendered items e04).")
for a, b, why in [
    ("C1.bubble_pass", "C1.insertion_sort", "Different traversal schedules (adjacent swaps per pass versus shifting into a hole); partial-round states differ."),
    ("C1.insertion_sort", "C1.partition_pass", "Insertion versus Lomuto partition."),
    ("C1.majority_vote_scan", "C1.run_length_scan", "Both keep (value, count); cancel-on-mismatch versus close-and-emit."),
    ("C1.sieve_marking", "C1.circle_elimination", "Arithmetic-progression strikes versus counting live flags round a ring."),
    ("C1.counter_list", "C1.list_build", "Indirect bucket increment versus append."),
    ("C1.mirror_pointers", "C1.merge_two_sorted", "Converging two-pointer comparison versus two-pointer merge."),
    ("C1.merge_two_sorted", "C1.binary_search", "Merge advance versus halving."),
    ("C1.bfs_queue", "C1.union_find_links", "Queue frontier versus parent-pointer chasing."),
    ("C1.cellular_update", "C1.list_build", "Neighbourhood table lookup versus index expression."),
    ("C1.cond_chain", "C1.fib_like", "Both rotate two variables a fixed number of times; branching subtraction versus a linear recurrence."),
    ("C1.digit_peel", "C1.euclid_gcd", "Both % and // in a while loop; different state update."),
    ("C1.while_counter", "C1.digit_peel", "Affine growth / Collatz / subtraction versus digit extraction."),
]:
    add(a, b, "NONE", "audit_c1 JUDGEMENT_C1_LINEAGES.md near-misses", "NONE", why)
# ---------------------------------------------------------------- cross-evaluation
XM = "cross_evaluation_map/cross_evaluation_procedures_proposed.json"
for a, b, eid, why in [
    ("R2.binary_search_trace", "C1.binary_search", "S1", "Binary search over a sorted list with the probe trace as read-out; C1's lower-bound style is a tie-break/parameter change."),
    ("R2.run_length", "C1.run_length_scan", "S2", "Identical scan: count maximal runs, emit letter + count."),
    ("R2.crt_smallest", "M1.crt_congruence", "S3", "Smallest positive x meeting 2-4 congruences; only the frame differs."),
    ("M1.gcd_lcm", "C1.euclid_gcd", "S4 (compared gcd_lcm_r4 ~ euclid_gcd_traced_f3)", "Euclid's remainder algorithm; the C1 trace after R rounds and the M1 gcd/lcm (lcm = a*b/gcd folded over the values) are read-outs of the same state sequence."),
    ("R1.venn_counting", "M1.inclusion_exclusion", "S5", "Recover Venn region counts by inclusion-exclusion; none / exactly-k / union are read-outs, the number of sets a parameter."),
    ("R2.kth_smallest", "M1.median_list", "S6", "The median is the middle order statistic of the sorted list."),
    ("R2.sort_list", "M1.median_list", "S6 (lineages compared)", "Sorting, read at the middle (mean of the two middle values for an even count)."),
    ("R2.from_base", "C1.digit_peel", "S7", "Positional base conversion: digit_peel's % and // loop is to-base, its fold acc*k + d is Horner (from-base); inversion and read-out are listed changes."),
]:
    add(a, b, "LINK", f"{XM} {eid} STRONG", "LINK", why)
add("R2.to_base", "C1.digit_peel", "LINK", "audit3_c1/audit4_c1 strong (digit_peel ~ R2.to_base/to_base_wide/from_base)", "LINK", "digit_peel's loop d = n % b, n = n // b is the to-base procedure; the fold is a read-out.")
for a, b, eid, why in [
    ("R1.compass_turns", "C1.turtle_walk", "B1", "Heading mod 4 is kept by both, but the turtle also keeps (x, y) and reads the position: maintained state differs."),
    ("R1.spatial_grid_walk", "C1.turtle_walk", "B2", "Unit moves on a grid; absolute moves with walls versus heading-relative moves of varying length."),
    ("R1.categories_default_exceptions", "C1.union_find_links", "B3", "Parent-pointer chasing up a forest; union-find also links roots and prints the array."),
    ("R1.graph_shortest_route", "R2.cheapest_network", "B4", "Dijkstra and Prim share the greedy frontier with a different key; Kruskal is the usual MST route."),
    ("R1.equivalence_exchange_rates", "M1.percent_change", "B5", "Multiply a chain of ratios; R1 must first find the path through a tree of rates, M1 gives the chain in order."),
    ("R1.equivalence_exchange_rates", "M1.fraction_remainder", "B5", "As above."),
    ("R1.conditional_threshold_rule", "M1.shopping", "B6", "Weighted sum then a comparison / read-out; shared generic arithmetic plus a sign split."),
    ("R1.conditional_threshold_rule", "M1.speed_distance", "B6", "As above."),
    ("R2.cheapest_network", "C1.union_find_links", "B7", "Kruskal's MST runs union-find over sorted edges; Prim does not, and C1 reads the parent array."),
    ("R2.expression_eval", "C1.postfix_evaluation", "B8", "Stack evaluation of arithmetic; infix with parentheses and a stated precedence (parsing) versus postfix."),
    ("R2.string_rewrite", "C1.string_methods", "B9", "Sequential str.replace is one of C1's chain operations, among slicing and case changes."),
    ("R2.count_divisible", "C1.list_build", "B10", "Filter by a modulus/threshold test and accumulate; list accumulator versus integer."),
    ("R2.count_divisible", "C1.nested_pairs", "B10", "As above, with a double loop."),
    ("R2.sort_list", "C1.merge_two_sorted", "B11", "Merging two sorted lists is merge sort's step; sorting does not require it and C1 reads comparison statistics."),
    ("R2.digit_root", "C1.digit_peel", "B12", "Digit sums; R2 gives the decimal string (no division) and repeats the sum."),
    ("M1.division_counting", "C1.digit_peel", "B15", "Mixed-radix floor division and remainder; two fixed steps with different divisors versus one base iterated to zero."),
]:
    add(a, b, "BORDERLINE", f"{XM} {eid} BORDERLINE", "BORDERLINE", why)
add("M1.last_digit_power", "C1.fast_power_f4", "BORDERLINE", f"{XM} B13 BORDERLINE", "LINK",
    "M1's powers are a^e mod p (or mod 10) by square-and-multiply; fast_power_f4 is that loop with the squaring offset c as a parameter value (c = 0 gives the power).")
add("M1.recurrence_iterate", "C1.fib_like", "BORDERLINE", f"{XM} B14 BORDERLINE (STRONG in audit3_m1, audit4_m1, audit4_c1)", "LINK",
    "Iterate a linear recurrence to a position: fib_like's t = a + b (+c, 2a + b, a + 2b, mod m) and M1's sum_prev_two / affine / add_index are coefficient values of one first/second-order linear recurrence.")
add("M1.arithmetic_series", "C1.loop_sum", "BORDERLINE", f"{XM} B16 BORDERLINE (STRONG in M1 map and audit4_c1; medium in audit4_m1)", "LINK",
    "loop_sum sums c*i over i in range(start, stop, step) with a residue filter; with step d, c = 1 and an always-true filter (parameter values) it is the day-by-day series sum (rendered item e04).")
for a, b, why in [
    ("R2.gcd_euclid", "M1.gcd_lcm", "Same gcd / lcm asks by Euclid's remainder algorithm."),
    ("R2.modular_power", "M1.last_digit_power", "a^e mod m by repeated squaring; mod 10 or mod p is a modulus parameter; sum/product of the terms is a read-out."),
    ("R2.prime_factor_query", "M1.prime_factors", "Trial-division factorisation; largest prime / sums / divisor count are read-outs."),
    ("R2.bracket_match", "C1.bracket_matching", "Stack bracket matching; number of kinds is a parameter."),
    ("R2.stack_machine", "C1.postfix_evaluation", "Explicit push / arithmetic stack machine; op set is a parameter of one stack interpreter."),
    ("C1.coin_change_table", "M1.change_ways", "Counting DP over coins with unbounded supply."),
    ("C1.cellular_update", "R2.cellular_automaton", "Elementary CA from an 8-entry table, fresh row per step; ring / zero boundary is a parameter."),
]:
    add(a, b, "LINK", f"{XM} unregistered_links STRONG; audit maps", "LINK", why)
add("C1.bfs_queue", "R1.graph_shortest_route", "BORDERLINE", f"{XM} unregistered_links BORDERLINE", "BORDERLINE", "BFS distances (unit weights, FIFO queue) versus Dijkstra on weights.")
add("R1.activity_selection", "R2.interval_scheduling", "LINK", f"{XM} unregistered_links_from_audits (strong in audit3_r2, audit4_r2)", "LINK", "Earliest-finish greedy over intervals; the count (R1, R2 batch 1) and the chosen list (R2 fix 3) are read-outs.")
add("R1.mst_cost", "R2.cheapest_network", "LINK", f"{XM} unregistered_links_from_audits (strong)", "LINK", "Minimum spanning tree weight.")
add("R1.containers_queue_line", "R2.list_ops", "LINK", f"{XM} unregistered_links_from_audits (strong audit3_r2 / medium audit4_r2)", "LINK",
    "Apply a stated sequence of operations (append, drop first, move first to end, cut, leave, reverse) to one list in order and read it; the operations' semantics are stated in the item, the op set a parameter value (rendered items e04).")
add("R1.equivalence_classes", "C1.union_find_links", "BORDERLINE", f"{XM} unregistered_links_from_audits (medium, audit4_c1)", "LINK",
    "Union-find over the 'same' pairs; 'yes' iff one root, 'no' iff a 'different' pair joins the two classes: a read-out of the same parent forest; C1's link rule is a tie-break parameter (rendered items e04).")
add("R1.road_reachability", "C1.equivalence_classes" if False else "C1.bfs_queue", "BORDERLINE", "audit4_c1 s6 (medium: bfs ~ R1.graph_shortest_route, R1.road_reachability)", "LINK",
    "BFS from the start; reachability of y is a read-out of the distance list that C1 prints from (distance / enqueue order / sum).")
add("R2.permutation_power", "M1.last_digit_power", "LINK", f"{XM} unregistered_links_from_audits (R2 map merge)", "LINK", "Through R2.modular_power: iterate a map t times / a^e mod m (judged as the modular_power pair; recorded because the earlier map listed it).")
add("C1.bubble_pass", "R2.sort_list", "BORDERLINE", f"{XM} unregistered_links_from_audits (medium)", "BORDERLINE", "Bubble passes are a sorting procedure, but C1 prints the list after K passes (a partial sort).")
add("C1.bubble_pass", "M1.median_list", "BORDERLINE", f"{XM} unregistered_links_from_audits (medium)", "BORDERLINE", "As bubble~sort_list.")
add("R2.multiples_between", "M1.division_counting", "BORDERLINE", f"{XM} unregistered_links_from_audits (weak/borderline); lineages_m1_fix3_clusters.CROSS_EVALUATION_BORDERLINE", "BORDERLINE",
    "M1.division_counting's batch-1 'multiples' shape is the same floor count; its other shapes (crates, pallets, empty seats) are other floor/ceil computations.")
add("M1.mode_tally", "C1.counter_list_f3", "BORDERLINE", f"{XM} unregistered_links_from_audits (weak/borderline); audit4_m1", "BORDERLINE", "Tally into buckets; f3's bucket is a machine state.")
add("M1.mode_tally", "R2.count_letter", "BORDERLINE", "audit4_m1 s5; lineages_m1_fix3_clusters.CROSS_EVALUATION_BORDERLINE", "BORDERLINE", "Count occurrences of one key versus the whole frequency table and its argmax.")
add("M1.mode_tally", "R2.count_divisible", "BORDERLINE", "audit4_m1 s5 (borderline: R2.count_letter / count_divisible)", "BORDERLINE", "As above.")
add("M1.mode_tally", "C1.majority_vote_scan", "BORDERLINE", "audit4_m1 s5 borderline; audit3_c1 medium", "BORDERLINE", "Boyer-Moore pairing versus a full tally.")
add("M1.mode_tally", "C1.counter_list", "BORDERLINE", "lineages_m1_fix3_clusters.CROSS_EVALUATION_BORDERLINE; audit3_c1 medium", "LINK",
    "Tally values into a count table (keyed by x % k, a modulus parameter, or by x); the mode and 'n minus its count' are read-outs of the printed table (rendered items e04).")
add("M1.slot_permutations", "R2.dictionary_rank", "BORDERLINE", f"{XM} unregistered_links_from_audits (auditor's guess, not rendered)", "BORDERLINE", "Ranking needs the product-rule count of the remaining positions at each step; the rank walk is an added procedure.")
add("M1.binomial_choose", "R2.dictionary_rank", "BORDERLINE", f"{XM} unregistered_links_from_audits (auditor's guess)", "BORDERLINE", "As slot_permutations~dictionary_rank.")
add("R1.nim_xor", "R2.subtraction_game", "LINK", "audit3_r2 s2 / audit4_r2 s5 (strong; 'Grundy part not')", "LINK",
    "Sprague-Grundy: label pile sizes by mex over the move set, XOR the labels; with every move allowed the label is the size, which is Nim (move set = parameter value).")
add("C1.circle_elimination", "R1.elimination_josephus", "LINK", "audit3_c1 s2, audit4_c1 s6 (strong)", "LINK", "Josephus counting round a ring of live flags / people.")
add("C1.fast_power", "R2.modular_power", "LINK", "audit3_c1 s2; audit3_r2 s2 (strong)", "LINK", "Modular exponentiation by repeated squaring.")
add("C1.fast_power", "M1.last_digit_power", "LINK", "lineages_m1_fix3_clusters.CROSS_EVALUATION (audit3_m1 s4)", "LINK", "As above; sum/product of terms is a read-out.")
add("C1.fast_power_f3", "R2.modular_power", "BORDERLINE", "audit4_c1 s6 (medium: same skeleton, different function)", "LINK", "Same loop as C1.fast_power with the squaring offset c a parameter value.")
add("C1.kadane_scan", "R2.max_subarray_sum", "LINK", "audit3_c1 s2; audit3_r2 s2 (strong)", "LINK", "Best-ending-here scan (Kadane).")
add("C1.string_pair_table", "R2.lcs_length", "LINK", "audit3_c1 s2; audit3_r2 s2 (strong)", "LINK", "LCS prefix table (C1 also has edit distance, another cell rule of the same table).")
add("C1.coin_change_table", "R2.coin_change_min", "LINK", "audit3_c1 s2 (strong)", "LINK", "Table over amounts with unbounded coins; fewest versus ways is a semiring (number system).")
add("R2.coin_change_min", "M1.change_ways", "LINK", "audit3_r2 s2; lineages_m1_fix3_clusters.CROSS_EVALUATION", "LINK", "As above.")
add("R2.gcd_euclid", "C1.euclid_gcd", "LINK", "audit3_c1 s2; audit3_r2 s2 (strong)", "LINK", "Euclid's remainder algorithm.")
add("C1.mirror_pointers", "R2.palindrome_check", "BORDERLINE", "audit4_r2 s5 (strong: 'the same two-pointer comparison'); audit3_c1 medium; audit3_r2 weak", "LINK",
    "Compare s[i] with s[j] converging from both ends; 'is it a palindrome' is a read-out (no unequal pair) of the same comparisons.")
add("R2.list_ops", "C1.slices", "BORDERLINE", "audit4_r2 s5 medium; audit3_c1 medium; " + XM + " considered_not_linked", "BORDERLINE", "Reversal appears in both; list-operation simulation versus slice index arithmetic.")
add("R2.list_ops", "C1.string_methods", "BORDERLINE", "audit3_c1/audit4_c1 medium (B3 ~ R2.list_ops)", "BORDERLINE", "As above.")
add("C1.insertion_sort", "R2.sort_list", "BORDERLINE", "audit3_c1 s2 medium", "BORDERLINE", "Insertion sort for K rounds (a partial sort).")
add("C1.minmax_track", "R1.order_extreme", "BORDERLINE", "audit3_c1 s2 medium", "BORDERLINE", "Running extremum of values versus the extreme of an order given by facts.")
add("C1.bfs_queue", "R1.categories_follow", "BORDERLINE", "lineages_c1_fix3_clusters.CROSS_EVALUATION medium (audit3_c1)", "BORDERLINE", "Graph traversal; categories also lifts 'No' / 'Some' premises (joined transitively through road_reachability).")
add("C1.union_find_links", "R1.categories_follow", "BORDERLINE", "lineages_c1_fix3_clusters.CROSS_EVALUATION medium (audit3_c1)", "BORDERLINE", "Undirected union-find versus directed closure (joined transitively through equivalence_classes).")
for a, b, why in [
    ("R1.temporal_weekday_shift", "M1.clock_duration", "Calendar/clock arithmetic only; path offsets mod 7 versus base-60 differences per leg."),
    ("R1.conditional_decision_tree", "C1.func_branch", "Generic branch selection; tree walk versus a piecewise numeric function."),
    ("M1.tiered_pricing", "C1.func_branch", "Piecewise rates summed across brackets versus one branch selected."),
    ("M1.prime_factors", "C1.sieve_marking", "Primes as topic; factorisation versus sieve marking."),
    ("R1.swap_tracking", "R2.list_ops", "Permutations of a holder map versus insert/delete/reverse on a list."),
    ("R2.luhn_check", "C1.digit_peel", "Weighted digit sums; Luhn reads the written digits, no division by a base."),
    ("R2.from_base", "M1.clock_duration", "hh:mm to minutes is incidental to the duration procedure."),
    ("R2.cellular_automaton", "R1.boolean_lights", "Synchronous neighbourhood table update versus switch toggles."),
]:
    add(a, b, "NONE", f"{XM} considered_not_linked", "NONE", why)
add("R1.containers_stack_piles", "R2.stack_machine", "NONE", "audit3_r2 s2 weak; lineages_r2_fix3_clusters CROSS_EVAL weak", "NONE", "Several piles with moves and reversal versus one arithmetic stack.")
add("R2.cache_eviction", "R1.containers_queue_line", "NONE", "audit4_r2 s5 weak", "NONE", "Cache hit/miss with LRU or FIFO eviction versus listed line operations.")
add("C1.counter_list_f3", "R2.hash_probe", "NONE", "audit4_c1 s6 weak", "NONE", "Machine-state tally versus linear probing.")
# ---------------------------------------------------------------- found by this auditor (no earlier judgement)
add("R1.stable_matching", "R2.deferred_acceptance_partner", "-", "not judged by any earlier map read", "LINK",
    "Identical procedure: proposer-proposing deferred acceptance, read one proposer's final partner (R2 code lineages_r2_graphs.py:102 states the same rounds).")
add("R1.swap_tracking", "R2.permutation_power", "-", "not judged earlier", "BORDERLINE", "Trace one element through successive permutations; a sequence of different swaps/rotations versus one mapping applied t times (cycle reduction).")
add("M1.digit_puzzle", "R1.one_culprit", "-", "not judged earlier", "BORDERLINE", "Enumerate a finite candidate list and keep the one meeting the stated clue tests (all true / exactly k true); candidates and test differ.")
add("C1.while_counter", "M1.recurrence_iterate", "-", "not judged earlier", "BORDERLINE", "Iterate an affine numeric map; until a threshold versus to a stated position, and while_counter also has Collatz / subtraction shapes.")
add("C1.loop_sum", "R2.count_divisible", "-", "not judged earlier (B10 named list_build / nested_pairs)", "BORDERLINE", "Integer accumulator gated by a residue test over a generated range versus over a given list.")
add("C1.grid_path_table", "R1.temporal_critical_path", "-", "not judged earlier", "BORDERLINE", "Max-plus DP over a DAG (grid cells with up/left predecessors; jobs with stated predecessors); C1 keeps a rolling row and also has min-sum and path-count shapes.")
