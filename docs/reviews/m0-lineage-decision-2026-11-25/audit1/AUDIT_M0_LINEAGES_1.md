# AUDIT_M0_LINEAGES_1: independent distinctness audit of the 35 R1 lineages (15 old + 20 pilot)

- Auditor model: Opus 5.5 (claude-opus-5-5), from session metadata. Role: independent engineering/mathematical audit.
- **Astra review: NOT_PERFORMED.** This is not Astra validation and not human approval.
- Target: worktree `.claude/worktrees/agent-a0c9d741ea96ce52f`, branch `claude/m0-impl`, commit `16720d78921978c2ff4826563badbe4b21e609bd`. Target worktree was read only; `git status --short` there is empty after the audit.
- Environment: macOS 27.2.1 arm64; uv 0.12.15; Python 3.12.14 from the locked env of this worktree. Every Python run: `cd <this worktree> && PYTHONDONTWRITEBYTECODE=1 [PYTHONHASHSEED=0] uv run --locked --offline python experiments/_scratch/m0_lineage_audit_20261125/<script> <args>` (exact args below). `show.py` was run with system `python3` (it only prints JSON).
- Order of work: judgement written and hashed in `JUDGEMENT_BEFORE_AUTHOR_NOTES.md` (SHA-256 `145590aacf7d13f1cdec5a778071e8a0214599c6066b903118b2b33322def06a`, hashed 2026-11-25T12:32:58Z, `JUDGEMENT_SHA256.txt`) BEFORE `NOTES_LINEAGE_REPAIR.md`, `r1_pilot_stats*` and the manifest note were read. Generator code was read through `strip_docs.py` (AST round trip that drops docstrings and comments) so author prose about similarity was not seen first.

## Scripts and runs (all in this directory)

| Script | Command args | Output |
|---|---|---|
| strip_docs.py | `<module paths>` | code without docstrings (read on screen) |
| sample_items.py | `<agent worktree> samples` | `samples/R1.<id>.jsonl`: 3 items per level 0..6 for each of 35 lineages (old 15 rendered by calling their builders through `core.build_item` with auditor seeds `"20261125|<id>|<level>"`; new 20 sampled from fixtures) |
| show.py | `samples <k> <maxchars> <ids>` | printed items; `new_part2.txt` |
| text_solvers.py | `<agent worktree>/studies/m0/fixtures/r1_pilot` | `text_solvers_run1.txt` (attempt 1, failed by my bug), `text_solvers_run2.txt` |
| shortcuts.py | same fixtures dir | `shortcuts_run1.txt` |
| pairs.py | `pairs_judgement.csv` | `pairs_run1.txt`, `pairs_judgement.csv` (595 rows) |
| per_part.py | `<this dir> <agent worktree>` | `per_part_run1.txt`; uses `parts.txt` (read-only call of `core.family_partition('R1')` and `lineages_r1_common.load_pilot()`) |

Reading coverage, stated exactly: I read the full generator code of all 35, and on screen one rendered item per level (7 per lineage, 245 items; long items truncated in the middle). The remaining 2 sampled items per level were not read by eye; for the new 20 all 140 fixture items per lineage were checked by my own code instead. This is less than "3 read per level" by eye.

## 1. Solution procedure per lineage

Recorded in `JUDGEMENT_BEFORE_AUTHOR_NOTES.md` section 1 (one line each, 35 lines). Not repeated here.

## 2. Pairwise decision under section 6.2

Rule quoted (ADR-0033 section 6.2): "Each rule shape is registered with a lineage: the hand-written base rule, a distinct solution procedure, from which it derives. Shapes made mechanically from one base rule (by changing parameters, order, negation, names or surface frame) share a lineage. **The cluster, for G and for every bootstrap, is the lineage.**" and "records any pair that is the same procedure. Such a pair is merged into one lineage before the record."

Ambiguous sentence: "a distinct solution procedure" with "changing parameters". It does not fix the granularity. STRICT = algorithmic schema (value domain, constraint-type mix and read-out are parameters). LENIENT = only identical algorithm + data structure + read-out merge.

Merged pairs (all 595 considered; `pairs_judgement.csv`):

Both readings:
- order_compare = road_reachability (directed reachability; ynu only adds the reverse query).

Strict only:
- event_timeline = temporal_weekday_shift = spatial_relative_directions = equivalence_exchange_rates (tree potential propagation; Z, Z mod 7, Z^2, Q* via log; weekday_shift reuses event_timeline's sentence template on the same random tree).
- kinship_ancestor = kinship_cousins = categories_default_exceptions (chase pointers up a parent chain).
- knights_knaves = one_culprit (enumerate hypotheses, evaluate statements, filter by truth constraint).
- seating_row = pet_owners (unique permutation by constraint elimination).
- attribute_rule = conditional_decision_tree (evaluate a propositional structure under a full assignment).
- compass_turns = boolean_lights (fold commands into a cyclic-group accumulator, Z4 / Z2).
- categories_follow = equivalence_classes (close positive relation, lift negative relation, three-valued).
- order_extreme = order_tournament_wins (degree tally of a pairwise relation, extremum).

Near-misses kept apart: 23 pairs with reasons in `pairs.py` (NEAR), notably queue vs stacks (FIFO vs LIFO), queue vs Josephus, swap_tracking vs tracking_accounts, shortest_route vs critical_path, equivalence_classes vs bipartite, conditional_threshold_rule vs attribute_rule, kinship_descendants vs kinship_ancestor and vs order_extreme.

Distinct clusters:

| | old 15 | new 20 | overall 35 |
|---|---|---|---|
| strict | 11 | 18 | 23 |
| lenient | 14 | 20 | 34 |

Net new procedures contributed by the 20 pilot lineages beyond the old 15: 12 strict, 20 lenient.

Per part (new: intended parts; old: `core.family_partition('R1')` seed 400004 on the current registry): strict A 10 clusters wholly inside (12 touching), B 11 (13 touching); lenient A 17, B 17.

Findings, PENDING LEAD REVIEW:
- Two strict clusters span both parts: attribute_rule(A) + conditional_decision_tree(B); event_timeline(A) + spatial_relative_directions(A) + temporal_weekday_shift(A) + equivalence_exchange_rates(B). Under the strict reading a held-out part B procedure is also present in part A.
- Applying `core.family_partition`'s own rule to the 16-family union yields {A: elimination, spatial, rules, arrangement, graph, conditional, equivalence, kinship; B: boolean_state, culprit, order, tracking, truth, temporal, containers, categories}, which differs from the pilot's intended parts (author acknowledges the registered partition is by seed). Any cross-part distinctness check must be redone after the final partition.

## 3. Quality of the 20 new lineages

Keys. `text_solvers.py` parses question text only (never `structured`, never generator code, never `answer`) and uses brute force where cheap (bipartite over 2^(n-1) colourings; shortest route over all simple paths with first-hop uniqueness; equivalence over all set partitions; Josephus by literal counting). Result attempt 2: 2,800 / 2,800 keys agree and every answer is unique. Attempt 1: 140 mismatches, all on conditional_threshold_rule, caused by my regex also matching "or no." in "Answer yes or no."; fixed (comment in the file) and rerun. Kept as `text_solvers_run1.txt`. Hand solves: level-0 item of each of the 20 (ids in `JUDGEMENT_...md` / show.py output, e.g. R1.elimination_josephus/fixture/0/6 = Ines, R1.temporal_weekday_shift/fixture/0/15 = Sunday, R1.containers_stack_piles/fixture/0/12 = violin, R1.tracking_accounts/fixture/0/7 = Kai): all correct. No wrong key found. Note: this is the auditor's check, not the registered second solver of section 6.2.

Ambiguity:
- **R1.spatial_grid_walk (all levels):** row orientation is stated ("row 1 is the northernmost"), column orientation is not. 113/140 keys change if columns are read east-to-west (e.g. /fixture/0/1, /0/3, /0/4, /0/5). Unstated convention.
- Surface hazards, not logical ambiguity: containers_stack_piles uses "orange" as both a pile colour and a block (e.g. /fixture/6/11); boolean_lights renders "lamps 1, 2, 3 and 4 are on and the rest are off" when none remain (/fixture/0/1).

Answer leakage / shortcuts (`shortcuts_run1.txt`, 140 fixture items each):
- **kinship_descendants:** answer = the only person never stated as a child in 132/140 (65/65 for "descendants", structural; 67/75 for "grandchildren"). The intended aggregation is almost never needed.
- **equivalence_classes:** query pair stated verbatim in 68/140 (37 of 42 "yes" keys); a queried entity is never mentioned in 26/140 (always cbd; e.g. /fixture/0/7, /0/15); 94/140 decidable from surface.
- elimination_bracket: "Who loses the final?" (69/140) = top rating in the half without the overall top; no simulation.
- containers_queue_line: last joiner / last let-in is right on 99/140.
- categories_default_exceptions: 87/140 have all rules about the asked verb agreeing (priority rule unused); 54/140 the member's own group carries the rule.
- conditional_threshold_rule: 44/140 decided by a vetoing "no"; keys 92 no / 48 yes (author reports 62.6 % no on 2,000 items; consistent).
- boolean_lights: 31/140 asked lamp never toggled.
- graph_shortest_route: greedy nearest neighbour right on 97/140.

## 4. Feasibility (JUDGEMENT, not measurement)

Reachable genuinely distinct R1 lineages under section 6.2 as written: about 40-70 per evaluation strict (20-35 per part), 70-120 lenient (35-60 per part). 300 per part is not reachable under either reading.

Reasoning: R1's scope is deduction over stated relations; R2 already owns counting, sorting, list operations, base conversion and string rewriting. Short closed-answer items that a rule can key and a model can read in a paragraph draw on a limited set of algorithmic primitives: reachability/closure, connectivity/union-find, parity/2-colouring, shortest and longest paths, topological constraints, tree aggregation and pointer chasing, potential propagation, interval and Allen-relation reasoning, modular calendar/clock arithmetic, permutation and assignment CSPs, propositional forward chaining, truth-teller and count-of-truths hypothesis search, syllogisms and defaults, decision-rule evaluation, voting rules (plurality, runoff, Borda, Condorcet, weighted threshold are distinct), elimination schemes, game evaluation on tiny trees, and container/state simulations (stack, queue, deque, priority queue, register transfers, grid motion). Even counting each data-structure variant and each voting rule separately, I can list roughly 60-120 under the lenient reading; under the strict reading many collapse (all potentials, all modular folds, all hypothesis enumerations), leaving roughly 40-70. Halving across parts gives the ranges above. The pilot itself is consistent with this: the first 20, chosen from the easiest ideas, added 12 strict / 20 lenient new procedures, and the remaining space is smaller.

What would have to change for 300 per part (stated, not recommended): the definition would have to identify a lineage below the procedure level, for example (a) count each (procedure x query type x relation vocabulary / value domain) shape as its own lineage, i.e. drop "parameters" and "surface frame" from the merge list; or (b) define lineages as compositions of primitives (ordered pairs or short pipelines of about 20-25 primitives give several hundred distinct dependency graphs), with the cluster being the composition graph; or (c) decouple the bootstrap cluster from the lineage (cluster = shape), which section 6.2 currently forbids in bold. Each moves the cluster away from "a distinct solution procedure" and would weaken what the between-cluster variance protects against (Review 1, B1). PENDING LEAD REVIEW.

## 5. Comparison with the author's grouping (read after hashing)

Author (`NOTES_LINEAGE_REPAIR.md`, Sonnet 5.5 implementer): 12-14 of the 20 distinct; 25-28 for all 35; overlaps named: (i) offset propagation {weekday_shift, relative_directions, exchange_rates, event_timeline}; (ii) simulation {stack_piles, queue_line, tracking_accounts, swap_tracking}; (iii) conditional_threshold_rule with attribute_rule; (iv) kinship_descendants as downward counterpart of kinship_ancestor. Feasibility: 40-75 per evaluation, 20-40 per part.

Where I agree: (i) exactly (strict). Counts are close: my strict 12 net-new of 20 and 23 overall vs author 12-14 and 25-28. Feasibility ranges overlap (author 20-40 per part; mine 20-35 strict, 35-60 lenient).

Where I differ:
1. (ii) Simulation group: I do NOT merge stack_piles / queue_line / tracking_accounts / swap_tracking under either reading; their data structures differ (LIFO stacks, deque, additive registers, permutation). The author's own new-lineage definition in the same notes ("the algorithm, the data structure or the dependency graph must differ") makes them distinct; the author's overlap claim contradicts that definition.
2. (iii) I keep conditional_threshold_rule apart from attribute_rule (weighted-sum threshold arithmetic vs formula evaluation), and instead merge (strict) attribute_rule with conditional_decision_tree, which the author does not mention.
3. (iv) I keep kinship_descendants apart from kinship_ancestor (downward aggregation vs upward chase), but find what the author missed: 132/140 of its keys are the parentless root, i.e. the order_extreme in-degree-0 shortcut.
4. Strict merges the author does not list: categories_default_exceptions with kinship_ancestor/cousins (chain walk); boolean_lights with compass_turns (cyclic accumulator); equivalence_classes with categories_follow (positive closure + negative lifting; also the author's nearest op-profile neighbour, 0.834, though the author dismissed that metric); order_tournament_wins with order_extreme (degree tally). Old-old merges (order_compare = road_reachability in both readings; kinship_ancestor = kinship_cousins, knights_knaves = one_culprit, seating_row = pet_owners strict) are not itemised by the author; the author's 25-28 implies about 13-14 distinct old lineages, mine is 11 strict / 14 lenient.
5. Quality issues the author's notes and statistics do not report: kinship_descendants root leak, equivalence_classes verbatim/unmentioned-entity leak (author's top/chance 1.10 does not detect it), bracket final shortcut, queue last-joiner shortcut, grid-walk unstated column orientation, and cross-part strict clusters.
6. Author's "not verified by any independent solver": my text-level solvers now agree on all 2,800 fixture keys; this does not replace the registered second solver and its separate audit.

## Discrepancies and own mistakes

- Attempt 1 of my text solver: 140 false mismatches on conditional_threshold_rule from my own regex bug; kept.
- `text_solvers.py` was modified once (the fix) after attempt 1; the judgement hash covers the fixed version.
- No numeric discrepancy found against the author's table where comparable (threshold "no" share; categories_follow top share seen qualitatively in my renders).
