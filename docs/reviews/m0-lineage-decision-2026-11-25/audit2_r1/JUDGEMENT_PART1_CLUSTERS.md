# Judgement part 1 (clusters), written before reading lineages_r1_clusters.py, NOTES_LINEAGE_REPAIR.md, manifest notes or similarity docstrings

Auditor: Opus 5.5 (claude-opus-5-5), from session metadata. Astra review: NOT_PERFORMED. Not human approval.
Target: worktree agent-a0c9d741ea96ce52f, branch claude/m0-impl, HEAD 1b33b7b2. Code read through strip_doc.py (docstrings and comments removed).

Rule (ADR-0033 section 6.2, quoted): "Each rule shape is registered with a lineage: the hand-written base rule, a distinct
solution procedure, from which it derives. Shapes made mechanically from one base rule (by changing parameters, order,
negation, names or surface frame) share a lineage. **The cluster, for G and for every bootstrap, is the lineage.**"
Lead ruling applied: strict; the general algorithm is the procedure; number system, constraint mix, final question, names,
order, negation and surface frame are parameters; over-counting is the harmful error.

Registered set: 64 loaded lineages minus the 21 ids in fixtures/r1_pilot/SUPERSEDED.txt = 43 (registry_run1.txt), 22 families.

## Strict procedure of each of the 8 new lineages (lineages_r1_new2.py; three are registered as their rev3 wrappers)

1. topological_order (registered as topological_order_r2): Kahn's topological sort with a min-alphabetical priority queue
   over a prerequisite DAG; read the job at position j. Strict: topological sort read at a position.
2. activity_selection: maximum set of pairwise non-overlapping intervals by the earliest-finish greedy (touching allowed); read
   the count.
3. mst_cost: minimum spanning tree weight (Kruskal: sort edges, accept if it joins two components).
4. instant_runoff (registered as instant_runoff_r2): iterated plurality tally over ranked ballots with elimination of the unique
   minimum until one is left.
5. stable_matching (registered as stable_matching_r2): proposer-proposing deferred acceptance (Gale-Shapley); read one
   proposer's final partner (proposer-optimal stable matching, unique regardless of proposal order).
6. nim_xor: normal-play Nim; first player wins iff the XOR of pile sizes is non-zero (Bouton). Constraint: sum of piles even.
7. minimax_tree: bottom-up evaluation of a complete binary game tree with alternating MAX/MIN levels.
8. venn_counting: inclusion-exclusion over 2 or 3 sets; none = total - |union|.

## Pairwise decisions for the 8 (against each other and against the 35 earlier; all 8x42 pairs considered)

Primary strict MERGES:
- minimax_tree = attribute_rule (and so with conditional_decision_tree, the first audit's strict merge): bottom-up evaluation
  of an AND/OR expression tree; over Booleans AND = MIN and OR = MAX, so the integer MIN/MAX tree is the same algorithm with a
  different number system (a parameter by the ruling). The game framing is surface frame.
- topological_order(_r2) = order_extreme (and so with order_tournament_wins): order_extreme is mechanically topological_order
  with the constraint graph restricted to a chain and the asked position restricted to first/last ("needs X first" <->
  "X is taller than"). Constraint mix and final question are parameters.
- All other new-lineage pairs: no primary merge.

Borderline (counted only in my strictest bound):
- activity_selection ~ mst_cost (sort-by-key greedy with a compatibility test).
- mst_cost ~ graph_shortest_route_r2 (Prim is Dijkstra with a different key).
- instant_runoff_r2 ~ order_tournament_wins (tally, extremum; iterated) and ~ conditional_threshold_rule_r3 (weighted tally).
- nim_xor ~ boolean_lights_r2 (XOR/parity fold; Bouton's theorem maps the game to it).
- topological_order_r2 ~ temporal_critical_path (DAG processed in topological order).
Kept apart with no borderline: stable_matching (no other proposal/rejection procedure), venn_counting (no other
inclusion-exclusion), nim_xor vs minimax_tree (closed-form theorem vs backward induction).

## Changes to the earlier 35 under the lead's strict ruling (my own reading; differs from audit 1 in places)

- NEW (introduced by a repair): containers_queue_line_r2 = elimination_josephus. The r2 shape added "the person at the front
  goes to the back of the line" to the queue; with that op and "serve", the Josephus count is the fixed op pattern
  (front-to-back k-1 times, serve). Same data structure (circular queue), same operations.
- order_compare = categories_follow_r2 = equivalence_classes_r2 (with road_reachability): closure of a positive relation plus
  lifting of stated negative pairs, read three-valued. Audit 1 kept order_compare apart from categories_follow; under the
  explicit ruling (constraint mix is a parameter) I merge.
- Kept from audit 1: order_compare=road_reachability; potentials {event_timeline, temporal_weekday_shift,
  spatial_relative_directions, equivalence_exchange_rates}; upward chase {kinship_ancestor(_r3), kinship_cousins,
  categories_default_exceptions(_r3)}; knights_knaves=one_culprit; seating_row=pet_owners; attribute_rule=conditional_decision_tree;
  compass_turns=boolean_lights(_r2); order_extreme=order_tournament_wins (fewest-losses tally solves both).
- Revised shapes keep their original's lineage (they change parameters, the asked quantity or the rendering only):
  elimination_bracket_r3 (head-to-head lookup instead of ratings: still bracket simulation), graph_shortest_route_r2 (asks the
  distance instead of the first hop: still Dijkstra), conditional_threshold_rule_r3 (margin with abstentions: still a weighted
  threshold), etc.
- Further borderline among the 35: knights/culprit ~ seating/pet (generate-and-test); temporal_critical_path ~
  graph_shortest_route_r2; graph_bipartite ~ equivalence_classes_r2; spatial_grid_walk_r2 ~ compass_turns; conditional_chain ~
  knights_knaves; tracking_accounts ~ swap_tracking; kinship_descendants_r3 ~ order_tournament_wins.

## Counts (my_clusters.py, my_clusters_run1.txt)

- Primary strict: 27 clusters for the 43 registered lineages (9 multi-member clusters holding 25 lineages, 18 singletons).
- Strictest bound (primary + all borderline): 14 clusters.
- Lenient (identical algorithm and data structure only): 42.
- New 8 contribute, primary strict: 6 new clusters (activity_selection, mst_cost, instant_runoff_r2, stable_matching_r2,
  nim_xor, venn_counting); minimax_tree and topological_order_r2 join existing clusters.

## Partition readings (registered rule reproduced: sorted keys, stream(400004, "family-partition", "R1").shuffle, A = first floor(n/2))

Primary strict map:
- Literal (22 families): A = boolean_state, culprit, elimination, games, kinship, network, order, rules, temporal, tracking,
  voting. 21/22 lineages; clusters wholly A 9, wholly B 10, STRADDLING 8.
- Family-closure keys (families joined by a strict cluster become one key; 10 keys): A keys = arrangement,
  containers+elimination, network, tracking, voting; B = the nine-family key, conditional+games+rules, culprit+truth, matching,
  sets. Lineages A 10 / B 33; clusters A 8 / B 19; straddling 0.
- Cluster keys shuffled (not the registered unit): clusters 13/14; lineages 16/27.
Strictest map: literal -> 8 straddling clusters (3 wholly A, 3 wholly B); family-closure -> 5 keys, A = containers+elimination
and sets only: lineages 5/38, clusters 4/10.

Judgement: the literal family split is faithful to the words "splits the families ... half each" but leaves 8 strict clusters
in both parts, which contradicts the purpose of part B ("no teaching item, template or family of part B may ever be used for
teaching") once lineage = cluster. Family closure removes straddling but breaks "half each" in substance (10 vs 33 lineages,
8 vs 19 clusters) and depends entirely on how strictly clusters are drawn. Neither reading is clearly the registered one:
PENDING LEAD REVIEW. Least favourable to a held-out claim: family closure computed on the STRICTEST cluster map (no strict or
borderline relative of any part-B procedure in part A), at the cost of a tiny part A.
