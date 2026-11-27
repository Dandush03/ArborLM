# R1 registration plan, revision 4: what would be registered, what it replaces, what would have to change

Written by the implementer (Claude Sonnet 5.5) after the second audit of R1, for the lead's review. **Nothing here is registered, approved or validated.** Ruling R-9 stands: no new shape enters
`core.REGISTRY` until its cluster map, wording, construction-level shortcut fixes and capacity have passed a second audit and its second solver exists from a separate context. Self-checked only:
not independent review, not Astra validation, not human approval. All numbers are MEASURED (generator runs, no model) unless a line says analytical.

Files: shapes `studies/m0/lineages_r1_rev4.py`, `_rev4_b.py`, `_rev4_c.py` (own registry in `lineages_r1_rev4_common.py`, ids end `_r4`); map `lineages_r1_clusters_v2.py` (`registered_v2()` is the set below);
measurement `r1_rev4_battery.py`, `r1_rev4_measure.py` (tables `manifests/r1_rev4_two_sided.md`, `r1_rev4_named_tells.md`); capacity `r1_rev4_capacity.py` (`manifests/r1_rev4_capacity.md`);
parts `r1_rev4_parts.py` (`manifests/r1_rev4_parts.md`); fixtures `fixtures/r1_rev4/`, schema `fixtures/R1_REV4_SCHEMA.md`, manifests `manifests/r1_rev4_manifest.json`, `r1_clusters_v2.json`.

## 1. The set that would be registered: 43 shapes in 27 strict clusters

21 revision-4 shapes (each replaces one shape that is registered today in the working set):

| revision-4 shape | replaces | cluster | family | answer |
|---|---|---|---|---|
| R1.activity_selection_r4 | R1.activity_selection | R1.activity_selection | scheduling | open number |
| R1.boolean_lights_r4 | R1.boolean_lights_r2 | R1.boolean_lights | boolean_state | yes/no |
| R1.categories_default_exceptions_r4 | R1.categories_default_exceptions_r3 | R1.categories_default_exceptions | categories | yes/no |
| R1.categories_follow_r4 | R1.categories_follow_r2 | R1.categories_follow | categories | yes/no/cannot be determined |
| R1.conditional_decision_tree_r4 | R1.conditional_decision_tree | R1.attribute_rule | conditional | closed, 4 actions |
| R1.conditional_threshold_rule_r4 | R1.conditional_threshold_rule_r3 | R1.conditional_threshold_rule | conditional | yes/no |
| R1.containers_stack_piles_r4 | R1.containers_stack_piles_r3 | R1.containers_stack_piles | containers | closed, 5 to 11 blocks |
| R1.elimination_bracket_r4 | R1.elimination_bracket_r3 | R1.elimination_bracket | elimination | closed, 8 or 16 players |
| R1.graph_shortest_route_r4 | R1.graph_shortest_route_r2 | R1.graph_shortest_route | graph | open number |
| R1.instant_runoff_r4 | R1.instant_runoff_r2 | R1.instant_runoff | voting | closed, 4 to 6 candidates |
| R1.kinship_ancestor_r4 | R1.kinship_ancestor_r3 | R1.categories_default_exceptions | kinship | closed, 3 to 6 options |
| R1.kinship_descendants_r4 | R1.kinship_descendants_r3 | R1.kinship_descendants | kinship | closed, 3 to 6 candidates |
| R1.minimax_tree_r4 | R1.minimax_tree | R1.attribute_rule | games | open number |
| R1.mst_cost_r4 | R1.mst_cost | R1.mst_cost | network | open number |
| R1.nim_xor_r4 | R1.nim_xor | R1.nim_xor | games | first/second |
| R1.order_compare_r4 | R1.order_compare | R1.categories_follow | order | yes/no/cannot be determined |
| R1.spatial_relative_directions_r4 | R1.spatial_relative_directions | R1.equivalence_exchange_rates | spatial | open number |
| R1.stable_matching_r4 | R1.stable_matching_r2 | R1.stable_matching | matching | closed, 3 to 6 receivers |
| R1.temporal_critical_path_r4 | R1.temporal_critical_path | R1.temporal_critical_path | temporal | open number |
| R1.topological_order_r4 | R1.topological_order_r2 | R1.order_extreme | scheduling | closed, 5 to 11 jobs |
| R1.venn_counting_r4 | R1.venn_counting | R1.venn_counting | sets | open number |

22 shapes kept exactly as they are (no defect in the audit's list; their measured residuals are in section 5):

| shape | defined in | cluster | family |
|---|---|---|---|
| R1.attribute_rule | core.REGISTRY (lineages_r1.py) | R1.attribute_rule | rules |
| R1.compass_turns | core.REGISTRY | R1.boolean_lights | spatial |
| R1.conditional_chain | core.REGISTRY | R1.conditional_chain | conditional |
| R1.containers_queue_line_r2 | lineages_r1_rev2.py | R1.containers_queue_line | containers |
| R1.elimination_josephus | lineages_r1_elimination.py | R1.containers_queue_line | elimination |
| R1.equivalence_classes_r2 | lineages_r1_rev2.py | R1.categories_follow | equivalence |
| R1.equivalence_exchange_rates | lineages_r1_equivalence.py | R1.equivalence_exchange_rates | equivalence |
| R1.event_timeline | core.REGISTRY | R1.equivalence_exchange_rates | temporal |
| R1.graph_bipartite | lineages_r1_graph.py | R1.graph_bipartite | graph |
| R1.kinship_cousins | core.REGISTRY | R1.categories_default_exceptions | kinship |
| R1.knights_knaves | core.REGISTRY | R1.knights_knaves | truth |
| R1.one_culprit | core.REGISTRY | R1.knights_knaves | culprit |
| R1.order_extreme | core.REGISTRY | R1.order_extreme | order |
| R1.order_tournament_wins | lineages_r1_order.py | R1.order_extreme | order |
| R1.pet_owners | core.REGISTRY | R1.pet_owners | arrangement |
| R1.road_reachability | core.REGISTRY | R1.categories_follow | graph |
| R1.seating_row | core.REGISTRY | R1.pet_owners | arrangement |
| R1.spatial_grid_walk_r2 | lineages_r1_rev2.py | R1.spatial_grid_walk | spatial |
| R1.swap_tracking | core.REGISTRY | R1.swap_tracking | tracking |
| R1.temporal_interval_overlap | lineages_r1_temporal.py | R1.temporal_interval_overlap | temporal |
| R1.temporal_weekday_shift | lineages_r1_temporal.py | R1.equivalence_exchange_rates | temporal |
| R1.tracking_accounts | lineages_r1_tracking.py | R1.tracking_accounts | tracking |

NOT REGISTERED (`lineages_r1_clusters_v2.NOT_REGISTERED_V2`): none. Every shape named by the second audit has a revision-4 shape; the residuals are stated per shape in section 5 so the lead can decide.

Shapes that stay on file and are NOT registered: the 21 replaced shapes above (`fixtures/r1_rev4/SUPERSEDED.txt` lists them) and the 21 shapes already superseded before this round
(`fixtures/r1_pilot/SUPERSEDED.txt`). The redraw machinery (`lineages_r1_rev3.P`, `lineages_r1_shortcuts.ANTI_P`, `anti_override`, `_anti` in `_rev2`, `_new2`, `_rev3`) is not used by any
revision-4 shape (a test, `test_no_revision_4_module_conditions_items_on_a_heuristic_outcome`, scans the four modules).

## 2. What in `core.py` and the pool builders would have to change (nothing is changed here)

1. **`REGISTRY["R1"]` content.** Today it holds the 15 original lineages (`@lineage("R1", family)` in `lineages_r1.py`). The set above holds 12 of them (`attribute_rule`, `compass_turns`, `conditional_chain`,
   `event_timeline`, `kinship_cousins`, `knights_knaves`, `one_culprit`, `order_extreme`, `pet_owners`, `road_reachability`, `seating_row`, `swap_tracking`). `kinship_ancestor`, `categories_follow` and `order_compare`
   are superseded and must leave the registry (they are in it today, so `family_partition`, `part_lineages` and `generate_pool` would build pools from the wrong 15 lineages; audit 2, section 2). 31 shapes
   would be added: 10 from the pilot files and 21 revision-4 shapes. The pilot decorator (`lineages_r1_common.pilot`) and the revision-4 decorator (`lineages_r1_rev4_common.rev4`) keep their own lists today;
   registration would re-declare them with `core.lineage("R1", family)` (ids unchanged: `R1.<function name>`).
2. **Second solvers (`solvers_r1.py`).** `SOLVERS` has 15 entries keyed by the original ids. It would need entries for the 31 added ids and none for the 3 removed ones. The 21 revision-4 structured forms
   and their fixtures are in `fixtures/r1_rev4/` with the schema in `fixtures/R1_REV4_SCHEMA.md`; per ruling 7 the solver is written by a separate agent from the structured form only. Not written here.
3. **`family_partition` / `part_lineages`.** They split the families of `lineages_of(eval)`. The registered reading (ruling R-6, provisional) is not chosen: `manifests/r1_rev4_parts.md` tabulates four readings. Whatever is chosen
   needs the cluster of a lineage inside core (today only `lineages_r1_clusters_v2.cluster_of_v2` knows it, by base id), e.g. a `cluster` field on `Lineage` (default: its own id) or a registered map. Under "families joined by a cluster are one key"
   the keys are the 10 groups listed there (A 8 clusters, B 19); under "clusters are the keys" the unit of the rule changes from family to cluster.
4. **`generate_pool` allocation.** It spreads a pool evenly over `part_lineages(...)`, i.e. over SHAPES (`per_cluster = allocate(size, [1.0] * len(lins))`). With cluster = lineage (ADR-0033 section 6.2) it must spread over CLUSTERS and then
   over each cluster's shapes, otherwise a four-shape cluster gets four times the weight of a one-shape cluster (18 clusters have one shape, 4 have two, 3 have three and 2 have four in this set). `core.m0_draw` ("balanced over clusters") groups by `Item.lineage` and would group by cluster.
5. **Capacity gate.** `lineage_gates.exhibit` and `ggen.demand_per_level` count distinct normalised texts (`core.text_hash`). Ruling R-5 counts structure; `r1_rev4_capacity.structure_key` is the
   candidate key (name-, setting- and sentence-order-free; derivation in its docstring) and `demand_at_g(G, level)` is evaluated at the G actually written (27 clusters, so G about 13 per part, not 300).
6. **Tests.** `tests/test_m0_generators.py` parametrises over `lineages_of(ev)` and requires a second solver per id; `test_every_private_evaluation_has_at_least_twelve_families_and_both_parts_are_nonempty` stays true (22 families).
   The immutable tests under `tests/` are not touched here; registration would add its own `tests/test_m0_*.py` files.
7. **Registry check at G-gen.** The auditor's 50-pair pair check (section 6.2) and ruling 6 (cross-family and cross-part distinctness) use the map `lineages_r1_clusters_v2.STRICT_MERGES_V2` and the borderline list; cross-evaluation duplicates
   go to `manifests/cross_evaluation_procedures.json` (ruling R-7, not written here).

## 3. Conditions of ruling R-9, status

| condition | status after this round |
|---|---|
| cluster map | 27 strict clusters reproduced by a test; four merges added; borderline pairs listed not merged; authors' notes beside the map. Awaiting the second audit. |
| wording | `categories_follow_r4` states what yes, no and cannot be determined mean and that named groups are non-empty; `boolean_lights_r4` says "all the lamps not named here are off". Other R1 wordings are not in the audit's list. |
| construction-level shortcut fixes | every shape of the audit's list rebuilt by construction (no redraw); measured per level, two-sided (`r1_rev4_two_sided.md`, `r1_rev4_named_tells.md`); residuals in section 5. Awaiting the second audit. |
| capacity | MEASURED on structure (`manifests/r1_rev4_capacity.md`; key and demand derivation in `r1_rev4_capacity.py`). Demand = 10 x (ceil(24,000 / G) + 100) on core levels, 10 x 100 on reserve levels, at the G written: 27 clusters, so G about 13 per part (19,470 on a core level) and, for the smallest part of any reading, G = 8 (31,000). All 21 revision-4 shapes reach the requirement alone at every level in both scenarios. **Failing lineage-levels (clusters, summing their shapes' structures, an upper bound): R1.containers_queue_line at levels 0 to 3 (G = 13; 532, 2,105, 6,797, 12,069 against 1,000 / 19,470) and level 4 as well at G = 8 (23,715 against 31,000); R1.graph_bipartite at levels 0 to 2 (110, 1,614, 16,473).** Single shapes below the whole-cluster requirement, all unchanged shapes (40 at G = 13, 43 at G = 8; clusters that contain them still pass): `elimination_josephus` 32 to 47 structures at every level (a fixed procedure on a circular queue); `order_extreme` 2 per level (one chain, tallest or shortest); `order_tournament_wins` 4 to 524; `kinship_cousins` 368 to 2,877 (levels 0 to 5); `knights_knaves` levels 0 to 2; `equivalence_classes_r2` level 1; `pet_owners`, `seating_row` level 0 (`seating_row` level 1 and `one_culprit` level 1 also at G = 8); `graph_bipartite`, `containers_queue_line_r2` as above. The count is a lower bound for order-erased simulations and an upper bound where a phrasing is a random choice that the key does not know; none of this widens or drops anything (ruling R-5: the lead is told which). |
| second solver from a separate context | does not exist. |

## 4. Disposition of each defect of the second audit

Status: FIXED = the named tell is removed by the way the item is built (no redraw) and measured near zero at every level; REDUCED = removed in kind but a smaller residual of the same family is measured;
REPLACED = the question was changed so the heuristic does not apply; NOT DONE = not done. "eff" is the effective gain (gain on the items a heuristic fires on times its fire rate), 1,000 items per level, levels 0 to 6.

| defect (audit 2) | status | what was done | measured after (eff; worst level) |
|---|---|---|---|
| gate (a) possessive "Flynn's" | FIXED | one word rule for counts and entity lists (`words`, `_AFTER` in `lineages_r1_shortcuts`) | temporal_critical_path longest job: -0.095 before, +0.118 after (2,000 items) |
| gate (b) direction of the stated pair | FIXED | `_stated_reading` reads the comparative and the order | order_compare stated-pair heuristic: +0.077 before (fires 1,078), accuracy 0.693 / +0.359 after (same items) |
| gate (c) signed numbers, structure counts | FIXED | `numbers()` keeps the minus sign, drops "N choices/piles/..." | minimax smallest number: +0.170 before, +0.032 after |
| per-level reporting | DONE | `per_level_rows` in `run_battery` rows (key `per_level`); `r1_rev4_battery` | all tables |
| categories_default_exceptions_r3: rule on the first-named group always right | FIXED | nearest-rule distance uniform over 1..c-T (c = T+8+2 level); Y yes-signs uniform 1..T-1 independent of the answer; T odd | chain[1] rule: +0.037 (fires 7 %, right 100 % when it fires: a prefix of the true procedure); majority +0.009, last listed +0.006, odd count +0.003, least specific +0.035, second most specific +0.049 (a -1/(2(T-1)) hole, by construction); worst level +0.074 |
| conditional_threshold_rule_r3: margin alone 0.77 (0.96 L0) | FIXED | threshold set from the computed margin (offset 0 or 1 for yes, -1 or -2 for no); weights 1..9; 6 to 12 members | margin <= 0: +0.026 (+0.05 L1); heaviest voter +0.004; yes-count majority +0.004; worst now an approximate sum (count margin x mean weight) +0.060 |
| kinship_descendants_r3: parent of the hub 0.86; answer a child of the root | FIXED | candidates = children of one named person (one depth); children and grandchildren counts drawn independently of the number of descendants | parent of most-children person +0.003 (fires 11 %); most children, most mentioned, grandchildren swap: all <= +0.03; worst cell +0.021 |
| elimination_bracket_r3: first-round neighbour 0.69 vs 0.20 | FIXED (named tell), geometry REMAINS | near-regular tournament (wins say nothing); asks champion, runner-up, or who knocks out a round-3 loser (never round 1 or 2) | round-1 neighbour +0.001; most wins +0.025; "beater in own half" +0.276 at L5 (fires 19 % overall; +0.10 at L6): bracket geometry, a partial procedure |
| stable_matching_r2: second choice 0.46, first-mentioned 0.15 | FIXED (named), residuals REMAIN | planted matching with the asked proposer last in the planting order, so the rank of the partner is uniform on 1..n; deferred acceptance still computes the key | first choice +0.002, second choice +0.002; first mentioned +0.054 (L0 +0.12); receiver ranking ask highest +0.087; the receivers' own deferred acceptance agrees with the key in 73 % (a different run of the same procedure) |
| containers_stack_piles_r3: initial bottom 0.30 | REDUCED | 12+3 level random moves of 5+level blocks, reversals from level 1; the asked pile is one whose latest change was a removal or a turn | initial bottom +0.053 (accuracy 0.188 vs chance 0.133; L1 0.256 vs 0.167); last onto +0.011; initial top +0.037; "ignore reversals" is the solution at L0 (no reversals) |
| boolean_lights_r2: flip the initial state 0.68 at L0; "every other lamp is off" | FIXED | toggle parity of the asked lamp drawn first, independent of its initial state; wording "all the lamps not named here are off" | initial state / flipped +0.005 (L0 +0.01, accuracy 0.512); worst cell +0.033 |
| categories_follow_r2: shared-sentence pair never yes; kind leaves two answers; "no" undefined | FIXED (wording, kind, shared sentence), one partial-proof residual | answer and kind drawn first; "Some" premises and a stated non-empty convention make every answer reachable for every kind (9 of 9 combinations, each > 5 % of items); frame defines yes, no, cannot be determined | shared sentence +0.013; kind default +0.004; no sentence mentions x or y +0.025; "x has an outgoing All premise" +0.063 (gain +0.19 on the 34 % of items it fires on: a yes needs an edge) |
| instant_runoff_r2: the redraw changed what is measured | REPLACED by construction | 4 to 6 candidates, first-place totals 18 + (0 to 2), random remaining ranks; no redraw | plurality leader wins 21 to 37 % by level, plurality +0.083 (+0.10 to +0.11 at L0 to L2); other rules agree: top-two runoff +0.310, Condorcet +0.267 (fires 61 %). Residual stated |
| graph_shortest_route_r2: two roads in 58 to 77 % | FIXED | planted route of 3,3,4,4,5,5,6 roads by level (potentials; every other route strictly longer; decoys near the route) | best within two roads -0.04; nearest-neighbour walk +0.004; worst cell +0.022 |
| order_compare: 55.8 % decided by one stated fact | FIXED | the asked pair is stated in neither direction; x stated taller than someone and y shorter than someone; answer drawn first | stated pair never fires; worst cell +0.027 |
| activity_selection: shortest-first scores 0.93 | FIXED | zone construction: every item holds a trap for shortest-first and one for earliest-start | both wrong rules are wrong in every item (tested); their gain is -0.09 to -0.29, no heuristic is above 0 |
| mst_cost: each town's cheapest road 0.93 at L0 | FIXED | towns in groups of 3 or 4, roads inside groups cheaper than roads between | each town's cheapest road and the n-1 cheapest roads differ from the answer in every item (tested); worst cell +0.069 (L0, shortest-path tree from the first town) |
| spatial_relative_directions: least mentioned 0.38 | REPLACED | asks the street distance between two places no fact links directly (open number) | worst cell +0.043 (L0); all others <= +0.01 |
| conditional_decision_tree: most mentioned 0.41 | FIXED | four actions, each at the same number of leaves | most mentioned 0.000; worst cell +0.029 |
| temporal_critical_path: longest job +0.12, deepest chain 0.72 | REPLACED | asks the day on which the last job finishes (open number) | worst cell +0.002 |
| minimax_tree: levels identical; smallest-number artefact | FIXED (levels), order statistic REMAINS | seven distinct (depth, branching) pairs; first mover drawn | median leaf (low) +0.47 at L0, +0.21 L1, +0.15 L2, <= +0.17 after: the root value is an order statistic of the leaves (honest mathematics) |
| nim_xor: identical levels; L0 had 270 pile tuples | FIXED | even number of piles 4/4/4/6/6/8/8, piles in [m,2m), total even; levels differ in piles and size class | worst cell +0.052; L0 now >= 1,000 distinct multisets (tested) |
| venn_counting: identical generators by level | FIXED | 2, 3 or 4 groups and four different questions across levels; every region occupied | all non-solution heuristics <= +0.03; the exact formula is the solution at L0 and L2 |
| kinship_ancestor_r3: redraw; the root never the answer | FIXED | three families; the answer is the root in 7.2 % of items; options = the answer plus people with the same number of children and parent status | parentless +0.000; most/least mentioned +0.002; "the child's parent" is never right (+0.044 at L0 as an elimination) |
| topological_order_r2: redraw on the j-th alphabetical | REPLACED, residual REMAINS | 6 to 12 jobs with 1 to 3 prerequisites each, no redraw | j-th alphabetical +0.057; "sort by depth then name" +0.554 (L0 +0.68, L6 +0.44): a layered topological sort (a different tie-break) agrees with the key |
| wording R-4 (categories_follow "no"; boolean_lights "every other") | FIXED | see above | tests assert the sentences |
| cluster map (27, not 31) | DONE | `lineages_r1_clusters_v2` | 43 shapes, 27 clusters; strictest 14 listed |
| parts under each reading | DONE, NOT CHOSEN | `r1_rev4_parts.py` | `manifests/r1_rev4_parts.md` |
| registry wiring | PLAN ONLY (ruling R-9) | section 2 | none in core.REGISTRY |

## 5. Residuals and findings outside the audit's list (measured, not fixed, no bound registered)

Shapes kept unchanged, with the largest measured effective gain per shape (none is in the audit's list except where marked; nothing is fixed here, no bound exists; "pooled" = all seven levels). A heuristic reading, not a proof of absence: the battery is the generic text battery, the author's and the auditor's heuristics, and the mention-order readings added this round for questions without a "Choose from" list (`F:` names).

- `order_extreme`: the LEAST mentioned person is the answer in 50 % of items (chance 0.19; +0.31 pooled, +0.39 at level 6): the extreme of a chain is named once. New finding (the fallback mention battery found it); structural capacity is also 2 per level.
- `tracking_accounts`: the person with most (fewest) payments received minus made, +0.38 (+0.36 to +0.42 by level).
- `containers_queue_line_r2`: simulate while ignoring "leave", +0.31 (+0.47 at level 0). (In audit 2 as "no strong tell"; its strict merge with `elimination_josephus` is the cluster issue.)
- `equivalence_classes_r2`: "a common 'same' neighbour means yes, else cannot be determined", +0.26 at every level (audit 2: 0.588 against 0.333, an approximate procedure).
- `spatial_grid_walk_r2`: simulate ignoring the walls, +0.57 pooled (+0.65 at level 0; right on 75 % of the 86 % of items it fires on).
- `one_culprit`: most mentioned, +0.09 (+0.13 at level 6). `elimination_josephus`: first mentioned, +0.05 pooled (+0.17 at level 5).
- `conditional_chain` level 1: the constant most frequent key, +0.18 (accuracy 0.51 against 0.33); `temporal_interval_overlap` level 0: constant key, +0.16 (0.66 against 0.5); `event_timeline` level 0: the commonest key is never right (-0.33; +0.14 as an elimination).
- `road_reachability`: "an asked town is never mentioned, so no" is right on all 483 of the 7,000 items it fires on (6.9 %), +0.035 effective.
- `order_tournament_wins` level 0: the alphabetically last name is never the answer (+0.083 as an elimination).

Residuals of revised shapes (rows of section 4): topological_order_r4 (a layered topological sort agrees with the key, +0.55), stable_matching_r4 (the receivers' own deferred acceptance agrees in 73 %; receiver ranking ask highest +0.087), instant_runoff_r4 (top-two runoff +0.31, Condorcet +0.27, plurality +0.083), minimax_tree_r4 (median leaf +0.47 at level 0), elimination_bracket_r4 (beater in own half +0.28 at level 5), categories_follow_r4 (an outgoing premise +0.063), containers_stack_piles_r4 (initial bottom +0.053). In each the correlated heuristic is a different rule or a partial run of the same procedure, which the audit calls an approximate procedure; whether that is a shortcut for the gate is for the lead.

Tables made before this round by the earlier gate (`r1_shortcuts_table.md`, `r1_two_sided_table.md`, `r1_stats_table_v2.md`, `r1_shortcuts.json`, `r1_two_sided.json`) carry the three gate bugs of audit 2 (possessive forms, direction of a stated pair, unsigned numbers). They are kept unchanged and are not to be read for shortcut numbers; `r1_rev4_two_sided.md`, `r1_rev4_named_tells.md` and `r1_rev4_gate_bugs.md` replace them.

Not done: no second solver; nothing in `core.REGISTRY`; no cross-evaluation duplicate map (ruling R-7); no choice of partition reading, shortcut bound, or granularity of "distinct procedure".
