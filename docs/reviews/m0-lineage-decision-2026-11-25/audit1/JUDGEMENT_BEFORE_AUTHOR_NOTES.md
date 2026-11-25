# M0 R1 lineage distinctness: auditor's judgement written BEFORE reading the author's notes

Auditor model: Opus 5.5 (claude-opus-5-5), from session metadata. Astra review: NOT_PERFORMED. Not human approval.
Target: worktree agent-a0c9d741ea96ce52f, branch claude/m0-impl, commit 16720d78921978c2ff4826563badbe4b21e609bd.
Not read before this file was hashed: studies/m0/NOTES_LINEAGE_REPAIR.md, studies/m0/manifests/r1_pilot_stats*.{json,md}, the manifest's text, generator docstrings (code was read through an AST round trip that drops docstrings and comments: strip_docs.py). R1_PILOT_SCHEMA.md was read (structured-form descriptions only).

## Rule applied (ADR-0033 section 6.2, quoted)

"Each rule shape is registered with a lineage: the hand-written base rule, a distinct solution procedure, from which it derives. Shapes made mechanically from one base rule (by changing parameters, order, negation, names or surface frame) share a lineage. **The cluster, for G and for every bootstrap, is the lineage.** G is the number of lineages per part." and "The auditor reads one rendered item from each of 50 random pairs of lineages in one family and records any pair that is the same procedure. Such a pair is merged into one lineage before the record."

Test used: two lineages are the same procedure when a correct solver for one becomes a correct solver for the other by changing only parameters, order, negation, names, parsing or rendering, i.e. the core algorithm on the same abstract data structure and dependency graph is unchanged.

Genuinely ambiguous: the phrase "a distinct solution procedure" together with "changing parameters" does not say at what granularity a procedure is identified. STRICT reading: algorithmic schema; the value domain (Z, Z mod 7, Z^2, Q*), the mix of constraint types, and the read-out (argmax vs one value) count as parameters. LENIENT reading: those count as different procedures; only identical algorithm, data structure and read-out merge.

## 1. Procedure per lineage (what a solver must execute)

Old 15 (studies/m0/lineages_r1.py):
1. order_extreme: chain of taller facts forming one total order; find the source/sink (the one never on the shorter/taller side), i.e. in-degree-0 in the comparison digraph.
2. order_compare: transitive closure / DFS reachability in a DAG of taller facts, both directions; yes / no / cannot be determined.
3. kinship_ancestor: chase parent pointers k (2..4) steps up a tree from a named child.
4. kinship_cousins: chase 1 and 2 parent steps from two nodes; cousins iff grandparents equal and parents differ.
5. categories_follow: syllogisms; closure of "All A are B" (subset reachability), lift "No P are Q" to all subsets, three query kinds (all / none / some), three-valued.
6. conditional_chain: propositional forward chaining of literal-antecedent rules from facts to a fixpoint; three-valued (generator checks against full model enumeration).
7. knights_knaves: search over 2^n knight/knave assignments; keep the one where each statement's truth equals its speaker's type.
8. seating_row: unique permutation consistent with positional/adjacency/between constraints (elimination over permutations).
9. pet_owners: unique bijection people->pets from unary owns / not / either constraints (grid elimination).
10. event_timeline: tree of signed day differences; propagate offsets from any root, take argmin or argmax.
11. swap_tracking: compose a sequence of swaps and 3-cycles on a people->object map; read one entry.
12. road_reachability: directed reachability (BFS/DFS) in a digraph with cycles; yes/no.
13. one_culprit: for each candidate culprit count the true statements; the unique candidate whose count equals the stated k.
14. attribute_rule: evaluate a nested and/or/not formula over each badge's three attributes; the unique satisfier.
15. compass_turns: sum rotations mod 4 (several surface forms of the same rotation), ignore walk steps.

New 20 (studies/m0/lineages_r1_<family>.py):
16. boolean_lights: parity of presses of switches wired to the asked lamp, XOR its initial state (bit-vector toggling).
17. categories_default_exceptions: walk up a linear "Every A is a B" chain from the member's group to the first group with a rule about the verb (most-specific wins).
18. conditional_decision_tree: descend a nested if/else tree by looking up each tested fact; return the leaf action.
19. conditional_threshold_rule: weighted sum of yes votes >= threshold AND no veto holder voted no.
20. containers_queue_line: simulate a deque (push back, push front, pop front, remove by name); read front or back.
21. containers_stack_piles: simulate three LIFO stacks (move top, reverse a pile); read a top.
22. elimination_josephus: simulate counting-out elimination on a circular list with step k; read last or j-th eliminated.
23. elimination_bracket: simulate single-elimination rounds by pairwise max of ratings; read the final loser or who eliminated X.
24. equivalence_classes: union-find over "same" facts; "different" edge between the two classes gives no; else cannot be determined.
25. equivalence_exchange_rates: propagate multiplicative value ratios over a spanning tree; argmax of value per unit.
26. graph_shortest_route: single-pair shortest path on a weighted undirected graph (Dijkstra); report the first hop.
27. graph_bipartite: 2-colouring by BFS / odd-cycle detection; yes/no.
28. kinship_descendants: per-node grandchildren count or subtree size in a rooted tree; argmax.
29. order_tournament_wins: tally wins per player from complete round-robin results; argmax / argmin.
30. spatial_grid_walk: simulate a position on a grid with walls and edges under N/S/E/W moves; read the cell.
31. spatial_relative_directions: propagate 2D offsets over a tree of "k blocks <dir> of" facts; argmax of Manhattan distance from an anchor.
32. temporal_interval_overlap: normalise two interval encodings (range / start+duration, inclusive) and test intersection.
33. temporal_weekday_shift: propagate signed day offsets over a tree from the anchor event; weekday of the asked event mod 7.
34. temporal_critical_path: earliest-finish times in a precedence DAG (longest path, max-plus DP); argmax.
35. tracking_accounts: simulate integer balances under pay / earn / give-half; argmax or argmin.

## 2. Pairwise decision (all 595 pairs in pairs_judgement.csv; generated by pairs.py)

Merged under BOTH readings:
- order_compare = road_reachability: directed reachability; the ynu form only adds the reverse query (order change); DAG vs cyclic is a parameter.

Merged under the STRICT reading only:
- event_timeline = temporal_weekday_shift = spatial_relative_directions = equivalence_exchange_rates: potential propagation over a tree of pairwise relations then a read-out. weekday_shift even reuses event_timeline's sentence template ("X took place k days after/before Y") on the same random tree; Z vs Z mod 7 vs Z^2 vs Q* (log makes it additive) and argmax vs single read-out are parameters under the strict reading.
- kinship_ancestor = kinship_cousins = categories_default_exceptions: chase pointers up a parent chain (fixed k; compare two chases; until the first node with a rule).
- knights_knaves = one_culprit: enumerate hypotheses, evaluate all statements under each, keep the one meeting a truth constraint.
- seating_row = pet_owners: unique permutation by constraint elimination (constraint types differ).
- attribute_rule = conditional_decision_tree: evaluate a propositional structure under a complete assignment.
- compass_turns = boolean_lights: fold a command sequence into a cyclic-group accumulator (Z4 heading / Z2 lamp parity), dropping irrelevant steps.
- categories_follow = equivalence_classes: close a positive relation, lift a negative relation through the closure, answer yes/no/cbd.
- order_extreme = order_tournament_wins: per-person degree of a pairwise win/taller relation, take the extremum.

Near-misses kept apart (both readings) and why: listed with reasons in pairs.py NEAR (23 pairs), the main ones: order_compare vs categories_follow (superset procedure); equivalence_classes vs graph_bipartite (equality union-find vs parity propagation); graph_shortest_route vs temporal_critical_path (Dijkstra min-plus vs DAG max-plus DP); containers_queue_line vs containers_stack_piles (FIFO vs LIFO) and vs elimination_josephus (implied vs listed operations); elimination_bracket vs order_tournament_wins; swap_tracking vs tracking_accounts; spatial_grid_walk vs compass_turns; temporal_weekday_shift vs compass_turns (tree path vs linear fold); kinship_descendants vs order_extreme (intended subtree aggregation, but 132/140 fixture answers are the parentless root: quality defect, see 3); categories_follow vs conditional_chain; conditional_threshold_rule vs attribute_rule / decision_tree (arithmetic).

Counts (pairs.py, run recorded in pairs_run1.txt):

| | old 15 | new 20 | overall 35 |
|---|---|---|---|
| strict | 11 | 18 | 23 |
| lenient | 14 | 20 | 34 |

Per part (intended parts of the new 20; old 15 from core.family_partition seed 400004 on the current registry; per_part_run1.txt): strict A 10 clusters wholly inside (12 touching), B 11 (13 touching); lenient A 17, B 17. Two strict clusters cross parts: attribute_rule(A)+conditional_decision_tree(B), and event_timeline(A)+spatial_relative_directions(A)+temporal_weekday_shift(A)+equivalence_exchange_rates(B). Under the strict reading the part B procedure is then also in part A (held-out leak). PENDING LEAD REVIEW.
Also: applying core.family_partition's rule to the 16-family union gives a different split from the pilot's intended parts (e.g. temporal->B, graph->A, equivalence->A). The intended-part labels are not what the registered partition code would produce. PENDING LEAD REVIEW.

## 3. Quality of the 20 new lineages

Keys: my own text-parsing solvers (text_solvers.py; parse question text only; brute force where cheap: bipartite by 2^n, shortest route by all simple paths with first-hop uniqueness, equivalence by all set partitions, Josephus by literal counting) agree with all 2,800 fixture keys and find a unique answer on all 2,800 (text_solvers_run2.txt). Attempt 1 (text_solvers_run1.txt) reported 140 mismatches on conditional_threshold_rule: my parser bug (the vote regex also matched "or no." in "Answer yes or no."); fixed and rerun as attempt 2. Hand solves (one per lineage, level 0 fixtures shown in show.py output): all 20 keys correct.

Answer leakage / surface shortcuts (shortcuts.py, shortcuts_run1.txt; 140 items each):
- kinship_descendants (serious): for ask=descendants the answer is always the unique person with no recorded parent (65/65, structural: the generator builds one tree rooted at ps[0]); for grandchildren 67/75. Overall 132/140 answered by "the one name never stated as a child".
- equivalence_classes (serious): the queried pair is stated verbatim in 68/140 (37 of 42 'yes' keys, 31 of 55 'no' keys); in 26/140 a queried entity never appears in the facts (answer then always cbd). 94/140 decidable from surface without union-find.
- elimination_bracket: 'Who loses the final?' (69/140) is always the top rating of the half not containing the overall top rating; no round simulation needed.
- containers_queue_line: "back -> last joiner, front -> last let-in" is right on 99/124 where it fires (71% of all items).
- categories_default_exceptions: in 87/140 all rules about the asked verb agree (the stated priority rule is never exercised); in 54/140 the member's own group carries the rule (one lookup).
- conditional_threshold_rule: 44/140 decided by "a veto holder voted no" without arithmetic; keys 92 no / 48 yes.
- boolean_lights: 31/140 asked lamp is never toggled (answer = initial state).
- graph_shortest_route: greedy nearest neighbour of the start is right on 97/140.

Ambiguity / unstated conventions:
- spatial_grid_walk: the item states "row 1 is the northernmost" but never states that column 1 is westernmost. 113/140 fixture keys change if columns are read east-to-west. Ids include R1.spatial_grid_walk/fixture/0/1, /0/3, /0/4, /0/5. Convention is conventional for maps but unstated while the row convention is stated.
- containers_stack_piles: "orange" is both a pile colour and a block (e.g. R1.containers_stack_piles/fixture/6/11: "the orange pile" and block "orange"); not logically ambiguous, a surface hazard.
- boolean_lights: "lamps 1, 2, 3 and 4 are on and the rest are off" when no lamp remains (R1.boolean_lights/fixture/0/1); wording only.
- equivalence_classes: queries about an entity never mentioned (26 items, e.g. R1.equivalence_classes/fixture/0/7) are logically answerable (cbd) but degenerate.
No item found with a wrong key or two defensible answers apart from the grid column convention.

## 4. Feasibility (JUDGEMENT, not measurement)

See the final report. Range recorded here before reading the author's notes: genuinely distinct R1 procedures reachable under section 6.2 as written, within R1's stated scope (deduction over stated relations; R2 owns algorithmic list/string/number tasks): about 40-70 for the evaluation under the strict reading, 70-120 under the lenient reading; per part about 20-35 strict, 35-60 lenient. 300 per part is not reachable under either reading.
