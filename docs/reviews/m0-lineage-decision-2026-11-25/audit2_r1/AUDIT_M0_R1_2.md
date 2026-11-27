# AUDIT_M0_R1_2: second independent audit of the R1 lineages after the repair round (ADR-0033 rev 4, M0)

- Auditor model: Opus 5.5 (claude-opus-5-5), from session metadata. Role: independent engineering/mathematical audit.
- **Astra review: NOT_PERFORMED.** This is not Astra validation and not human approval. Scientific choices are marked PENDING LEAD REVIEW.
- Target (read only): worktree `.claude/worktrees/agent-a0c9d741ea96ce52f`, branch `claude/m0-impl`, HEAD `1b33b7b2d1e75765b56c90bffb08286471852d85` (R1 work in f328c279, 476e6c24). `git status --short` there is empty after the audit.
- Environment: macOS 27.2.1 arm64; uv 0.12.15; Python 3.12.14 (locked env). Numeric runs: `cd <consolidation worktree> && PYTHONDONTWRITEBYTECODE=1 [PYTHONHASHSEED=0] timeout <s> uv run --locked --offline python experiments/_scratch/m0_lineage_audit2_r1_20261125/<script> <args>`. `strip_doc.py`, `show.py` and text_solvers attempt 1 ran under system python3 3.15.1 (deviation, PROCESS_LOG.md).
- Order of work: judgement part 1 (clusters, partition) hashed 2026-11-25T14:22:22Z (`JUDGEMENT_PART1_SHA256.txt`); judgement part 2 (shapes, keys, shortcuts) and all scripts hashed 14:35:23Z (`JUDGEMENT_SHA256.txt`, part 2 = `f90c3084...`), BEFORE reading NOTES_LINEAGE_REPAIR.md and the manifest tables. **Deviation:** after part 1 was hashed, a grep printed NOTES lines 76, 80 and 107 and one manifest note (rulings A-E, the author's partition reading, 43/31/13/18). Nothing on the similarity of the new lineages or on the shape defects was in those lines. Logged in PROCESS_LOG.md.
- Code was read through `strip_doc.py` (AST-based, docstrings and comments removed).

## Scripts and runs (all in this directory; every file starts with `# ruff: noqa`)

| Script | Args | Output |
|---|---|---|
| registry.py | - | registry_run1.txt (64 loaded, 21 superseded, 43 registered, 22 families) |
| my_clusters.py | - | my_clusters_run1.txt |
| author_map_check.py | - | author_map_check_run1.txt (author's 31 / 13 / 18 reproduced with my code and with theirs) |
| author_part_vs_my_map.py | - | author_part_vs_my_map_run1.txt |
| render.py | `items 500` | items/*.jsonl.gz: 500 items x levels 0-6 for 25 lineages ("reg") + 10 redraw-disabled ("unc", `credit` patched to 0 in new2/rev2/rev3); render_run1.txt; 0 build failures |
| text_solvers.py | `items reg` / `items unc` | run1 (failed: my bug), text_solvers_run2.txt, text_solvers_unc_run1.txt |
| heuristics.py | `items reg` / `items unc` | heuristics_reg_run1.txt (contains my mislabelled venn heuristic), heuristics_reg_run2.txt, heuristics_unc_run1.txt |
| distortion.py | `items` | distortion_run1.txt |
| defect_checks.py | `items` | defect_checks_run1.txt |
| diagnose_discrepancies.py, diagnose_possessive.py | `items` | *_run1.txt (author functions imported read-only for diagnosis only) |

Seeds: `random.Random(core.derive_seed(20261125, "audit2", <lineage id>, <mode>, <level>))`, items through `core.build_item`.

## 1. The 8 new lineages and the strict cluster count

Rule (ADR-0033 section 6.2): "Each rule shape is registered with a lineage: the hand-written base rule, a distinct solution procedure, from which it derives. Shapes made mechanically from one base rule (by changing parameters, order, negation, names or surface frame) share a lineage. **The cluster, for G and for every bootstrap, is the lineage.**" I applied the lead's strict ruling: the general algorithm is the procedure, and number system, constraint mix, final question, names, order, negation and surface frame are parameters.

Strict procedures: topological_order(_r2): Kahn's topological sort with an alphabetical priority, read at position j. activity_selection: maximum non-overlapping intervals, earliest finish. mst_cost: MST weight. instant_runoff(_r2): iterated plurality with elimination. stable_matching(_r2): proposer-proposing deferred acceptance. nim_xor: Bouton (XOR != 0). minimax_tree: bottom-up MIN/MAX tree evaluation. venn_counting: inclusion-exclusion.

All 8 x 42 pairs were considered. Primary strict merges for the new lineages:
- **minimax_tree = attribute_rule (+ conditional_decision_tree).** It is bottom-up evaluation of an AND/OR expression tree; over Booleans AND = MIN and OR = MAX, so only the number system differs.
- **topological_order_r2 = order_extreme (+ order_tournament_wins).** order_extreme is topological_order with the constraint graph cut to a chain and the question cut to first/last position.

No two of the 8 merge with each other. Borderline (counted only in the strictest bound):
- activity~mst (sort-and-accept greedy);
- mst~shortest_route (Prim = Dijkstra);
- IRV~tournament tally and IRV~threshold tally;
- nim~lights (XOR fold);
- topological~critical_path.

Changes to the earlier 35:
- **NEW, caused by a repair: containers_queue_line_r2 = elimination_josephus.** The r2 shape added "the person at the front goes to the back" (present in 3,232/3,500 items). Josephus is the fixed pattern (front-to-back k-1 times, serve) on the same circular queue.
- **order_compare/road_reachability = categories_follow_r2/equivalence_classes_r2.** All four are closure of a positive relation plus lifted negative pairs, read three-valued; the constraint mix is a parameter. Audit 1 kept these apart; I differ from it here.
- All nine audit-1 merges stand. Revised shapes stay in their original's lineage.

| Count | Mine (primary strict) | Mine (strictest, + borderline) | Lenient | Author |
|---|---|---|---|---|
| Clusters, 43 registered lineages | **27** | 14 | 42 | 31 |

Disagreements with `lineages_r1_clusters.STRICT_MERGES` (author = audit 1's nine groups, nothing added): (1) minimax_tree; (2) topological_order_r2; (3) queue_line_r2 + josephus; (4) the reachability and closure clusters joined. 31 - 4 = 27.

## 2. Partition reading

`core.family_partition` shuffles the sorted family names with `stream(400004, "family-partition", eval)` and gives part A the first floor(n/2). ADR section 6.4: "a registered seed splits the families of each private evaluation into part A ... and part B ... Half each", and no part-B "item, template or family" may be used for teaching.

| Reading | Author map (31) | My primary (27) | Strictest (14) |
|---|---|---|---|
| Literal, 22 families (11/11), lineages 21/22 | A 12, B 13, **6 straddle** | A 9, B 10, **8 straddle** | A 3, B 3, **8 straddle** |
| Family closure (author's reading) | 14 keys: **A 13, B 18**, lineages 16/27 | 10 keys: A 8, B 19, lineages 10/33 | 5 keys: A 4, B 10, lineages 5/38 |
| Author's current assignment applied to my map | 0 straddle | **3 straddle**: minimax(A) with attribute/decision_tree(B); order_compare+road(A) with follow+equivalence(B); queue_r2(A) with josephus(B) | 6 straddle |
| Cluster keys shuffled instead of families | A 15, B 16 | A 13, B 14 | A 7, B 7 |

Judgement:
- **Faithfulness.** The literal reading is faithful to the words but leaves strict clusters in both parts, which defeats the purpose of part B once cluster = lineage.
- The author's closure is the most faithful extension I can see. Its keys are unions of whole families, the registered rule and seed are kept, and no family or cluster is split. It is still not "half each" in substance (16/27), and **its result depends entirely on the cluster map**: with my four merges the current assignment leaves 3 straddling clusters, and recomputing gives 8/19 clusters.
- **The author's alternative is not more faithful.** It applies the raw rule and moves cross-part clusters whole to B, which splits families across parts. For example, moving the minimax cluster puts games/minimax in B while games/nim stays in A.
- **Engineering defect.** The 30 pilot-registry lineages are not in `core.REGISTRY`, while the superseded `kinship_ancestor` and `categories_follow` still are (registry_run1.txt). So `core.family_partition`, `part_lineages` and `generate_pool` would build pools from the wrong 15 lineages; the author's `partition()` is a parallel function.
- **Least favourable to a held-out claim:** family closure on the strictest map, which leaves no strict or borderline relative of a part-B procedure in part A. Part A shrinks to containers+elimination and sets (5 lineages). PENDING LEAD REVIEW.

## 3. Revised shapes: original defect gone? new defects (500 items x 7 levels each; reg vs unc)

All values are heuristic accuracy against chance, two-sided.

| Shape | Original defect | New or remaining defect |
|---|---|---|
| spatial_grid_walk_r2 | gone (convention in 3,500/3,500) | none material (start cell 0.165 vs 0.089: random-walk return) |
| kinship_descendants_r3 | gone (root not an option) | **Answer is a child of the root 86-100% by level.** "Parent of the person with most children": 1,775 fires at 0.863 (unc: 798 fires). Root's child with most children: 0.660 vs 0.157. The redraw on most_children (0.619 -> 0.151) moved accuracy here. |
| kinship_ancestor_r3 | gone (root no longer the answer) | Root is never the answer (0/3,500, from the r2 design): an elimination of -0.10. Parent and leaves are never the answer: honest logic. |
| equivalence_classes_r2 | gone (verbatim 0, unmentioned 0) | Common 'same' neighbour 0.588 vs 0.333 (an approximate procedure). Keys skew to "no" (37.7%). |
| elimination_bracket_r3 | gone (no ratings) | **"Who knocks X out?" is answered by X's round-1 neighbour 0.693 vs 0.195** (unc 0.613; the redraw pushed knockouts into round 1). most_wins 0.181 vs 0.196. |
| containers_queue_line_r2 | gone | No strong tell (last cut at j=1: 0.33 vs 0.13). Strict merge with Josephus. |
| categories_default_exceptions_r3 | gone (all-agree and own-group cases now 0) | **SEVERE.** There are always exactly 5 rules about the asked verb, never on the member's group. The rule on the group named in the first sentence (chain[1]) is the answer whenever it exists: it fires 100% at L0-L1 (c=6 forces it), 61-84% at L2-L6, and is right 100% of the time (2,853/3,500). The second-most-specific rule scores 0.325 (anti, by design). |
| conditional_threshold_rule_r3 | gone (veto removed, keys 50/50) | **Margin alone (d <= 0 -> yes): 0.771; 0.958 at L0, 0.922 at L1** (unc 0.633). Heaviest voter 0.816. The author's yes-count majority is anti at L0 (-0.22) and L1 (-0.17) but positive at L2-L6. The redraw pulls items toward the threshold (distance 1.88 -> 1.39 at L0). |
| boolean_lights_r2 | gone (never-toggled 0; "the rest" wording gone) | "Flip the initial state" 0.68 at L0, 0.58 at L1. The new wording "every other lamp is off" (3,374 items) can be read as "alternate lamps". |
| graph_shortest_route_r2 | gone (asks the length) | Shallow: the shortest route has 2 roads in 58-77% of items at every level. Best within 2 roads: 0.841 when it fires. |
| containers_stack_piles_r3 | gone (no colour-word blocks) | Last onto 0.595 -> 0.169, but initial bottom of the asked pile rises 0.199 -> 0.295. |
| categories_follow_r2 | verbatim pairs excluded; convention stated | When x and y share any sentence the key is never "yes" (693 items, 0.000). The question kind leaves 2 possible keys (chance 1/2, not 1/3). **Frame ambiguity** (section 4). |
| topological_order_r2 | jth_alphabetical 0.292 -> 0.161 (chance 0.157) | none strong (layering by depth: 0.564, an approximate procedure) |
| instant_runoff_r2 | plurality 0.795 -> 0.294 (chance 0.279) | By level: L0 +0.18, L3-L6 -0.03 to -0.05. **The construct changes:** "plurality leader wins" drops from 93% to 52% at L0 and from 65% to 15% at L6. |
| stable_matching_r2 | first choice 0.572 -> 0.245 | **Second choice 0.264 -> 0.456; first-mentioned receiver 0.255 -> 0.148** (z -13.7, so its opposite is informative). The rev3 extra first_mentioned redraw has probability 0.0 and does nothing. Partner rank 1.48 -> 1.88 at L0. |

Judgement on redraw-by-heuristic. It works on the pooled sample for the named heuristic, but it:
- (a) moves accuracy onto correlated heuristics: in the table above, plus MST "each town's cheapest road" 0.455 -> 0.537 (0.93 at L0);
- (b) is miscalibrated by level, because one probability is fitted over pooled levels;
- (c) changes what the lineage measures.

It is not a neutral repair. If it is kept, it must be fitted per level and registered as part of each lineage's definition; construction-level fixes are preferable. PENDING LEAD REVIEW.

Level design among the new 8:
- minimax: L0=L1=L2, L3=L4 and L5=L6 are identical generators.
- venn and nim: levels differ only in magnitudes (venn: 2 groups at L0-L1, 3 at L2-L6; nim: 3/4/5 piles).
- nim capacity: only 270 / 426 / 678 distinct ordered "second" tuples at L0 / L1 / L2 (my 247 L0 "second" draws gave 161 distinct). The balanced first/second key binds before total capacity does.

## 4. Keys: independent text-only solvers

My solvers read only the rendered text and use different algorithms (Prim, Floyd-Warshall, LIFO deferred acceptance plus a stability check, brute-force Nim with up to 4 piles, set-partition enumeration, model enumeration for syllogisms, interval DP).

**Results: 70,000 reg and 35,000 unc items, 0 mismatches** (attempt 2). No ties, unstable matchings, IRV ties or inconsistent venn counts.

Hand solves, all correct:
- stable_matching_r2 L2/0 (Sean), L4/0 (Tom), L0/0 (Esme). The author never hand-checked this lineage; these, plus 7,000 solver agreements, cover it.
- topological L2/0, IRV L2/0, minimax L2/0, venn L2/0, mst L2/0, nim L2/0, activity L2/0.

**No wrong key found.** Ambiguous:
- **categories_follow_r2, all levels.** "Does it follow that ...? Answer yes, no or cannot be determined" does not define "no"; the key uses "the negation follows". Read literally ("no, it does not follow"), all 1,394/3,500 cbd keys would be "no". Example: R1.categories_follow_r2/audit2reg/L1/0, key cbd, "Does it follow that some badex are remix?". The original shape uses the same frame.
- boolean_lights_r2: the "every other lamp is off" wording hazard (e.g. R1.boolean_lights_r2/audit2reg/L1/0).

Stated conventions decide many keys but are not ambiguity: activity's touching rule (2,015/3,500 reg vs 1,589 unc; the redraw raised it), and categories_follow's empty groups (153).

This is the auditor's check; it is not the registered second solver of section 6.2.

## 5. Residual shortcuts (re-measured, 3,500 items each, levels 0-6)

| Lineage | Measured | Judgement |
|---|---|---|
| order_compare verbatim pair | Asked order stated 959/3,500 (always yes); reverse stated 993 (always no): **55.8% decided by one stated fact** | REAL DEFECT (same class as the repaired equivalence_classes) |
| conditional_decision_tree most-mentioned | 0.408 vs 0.271 | Honest base rate, but readable from the option text: design defect with a cheap fix |
| tracking_accounts richest at start | 0.370 vs 0.224 (net flow count 0.598) | Honest property |
| spatial_relative_directions least / most mentioned | 0.383 / 0.083 vs 0.245; anchor's direct neighbour 0.072 | Design defect, moderate (farthest place is a leaf of the fact tree) |
| order_compare | see above | |
| kinship_*_r3 least-mentioned / parentless | leaves never the answer (logic); root never the answer in ancestor_r3 (artefact, -0.10) | Mostly honest. The real problems are descendants_r3's hub tells (section 3). |
| containers_queue_line_r2 | most-mentioned 0.030 vs 0.134 (people who left); no strong positive tell | Honest elimination |
| temporal_critical_path | longest job **0.319 vs 0.190 (+0.13)**; deepest job 0.718 | Design weakness: durations rarely decide |
| stable_matching_r2 first mentioned | 0.148 vs 0.248 | REAL, caused by the first_choice redraw (unc 0.255) |
| activity_selection greedy | greedy by start 0.278 vs per-level modal 0.387; **shortest-first greedy (a wrong algorithm) 0.927** | REAL: the items do not separate earliest-finish from shortest-first |
| minimax_tree smallest leaf | signed smallest leaf 0.028 (math); at depth 2 the 2nd-smallest leaf is the answer ~2/3 of the time | Honest maths; identical levels are a real defect |
| venn_counting constant | modal rate about 0.1 per level (uniform none) | Honest |

## 6. Where I differ from the author's notes (read after hashing)

1. **Cluster count:** 27, not 31 (four merges, section 1). The author's own notes anticipate the minimax merge, and its stopping list treats "logic-gate circuit evaluation" as formula evaluation, which implies minimax merges too. Its first notes rejected topological-order items as "the same procedure as reachability", yet topological_order was added later.
2. **Partition:** the author's "move to B is least favourable" alternative splits families; see section 2. Also, `core.REGISTRY` is not wired to the registered set.
3. **Bugs in the author's shortcut gate:**
   - (a) `_valid` tokenises "Flynn's" as one word. In temporal_critical_path the key appears only in possessive form in **3,500/3,500** items, so every heuristic naming it is discarded. The author's "longest job -0.09" is an artefact; the true value is +0.13. On the same items, author credit is 0.083 vs mine 0.304 (L1-5).
   - (b) "minimax smallest leaf 0.159" is the generic `smallest_number`, which parses unsigned digits and includes the depth "2" (0.171 on my L1-5 items). The signed smallest leaf scores 0.030.
   - (c) The order_compare verbatim heuristic ignores direction: it fires on 1,301/2,500 items but is right on 635, so +0.087 understates a 52-56% leak.
4. **Not reported by the author:** the categories_r3 chain[1] tell (author: "all three heuristics within 0.02"); the threshold margin tell and per-level anti; the descendants hub tells; the bracket neighbour tell; second choice in stable matching; MST each-town's-cheapest; activity shortest-first; minimax identical levels; nim 'second' capacity; the categories_follow frame ambiguity; the "every other lamp" wording; the queue/Josephus merge created by the repair.
5. **stable_matching_r2 first-mentioned (-0.10)** is listed by the author as "not caused by a redraw". It is caused by one (unc 0.255). The rev3 first_mentioned redraw at probability 0.0 is a no-op.
6. **Agreements:** 43 / 31 / 13 / 18 reproduced. Pooled retuned values agree within about 0.01-0.02 (first choice -0.003 vs -0.004; jth alphabetical +0.005 vs +0.003; IRV +0.015 vs +0.022, different levels). Residual values agree for kinship_descendants_r3, kinship_ancestor_r3, spatial_relative_directions, conditional_decision_tree, tracking_accounts and queue most-mentioned.

## Must be fixed before registration (engineering view; scientific choices PENDING LEAD REVIEW)

1. Cluster map: add the four merges, or record a ruling against each. The strictest bound is 14.
2. Get a ruling on the partition reading, then recompute it on the final map. Wire the registered set into the registry that `generate_pool` uses, and remove the superseded core shapes from it.
3. Redesign or mark NOT REGISTERED (lead's call):
   - categories_default_exceptions_r3: chain[1] tell;
   - conditional_threshold_rule_r3: margin tell;
   - order_compare: stated pairs;
   - kinship_descendants_r3: hub tells;
   - elimination_bracket_r3: neighbour tell;
   - stable_matching_r2: second choice / first-mentioned;
   - activity_selection: shortest-first;
   - mst_cost: low-level Boruvka tell.
4. Make minimax, nim and venn levels distinct. Check nim's capacity per answer class at G-gen.
5. Reword the categories_follow_r2 frame and the boolean_lights_r2 start sentence.
6. Fix the gate bugs in section 6.3 before the gate's numbers are used for anything. Measure per level and two-sided, including correlated heuristics.

## Discrepancies and own mistakes (kept)

- text_solvers attempt 1 gave 3,500 false mismatches on threshold_r3: my regex matched "or no." in the answer instruction. Fixed and rerun; run1 kept.
- heuristics run1: my venn heuristic "sign_error_on_triple" is the correct formula (1.000 is expected). Renamed in run2; run1 kept.
- The process deviations above (early grep of three NOTES lines; system python3 for three non-numeric or failed runs).
- My partition "cluster keys" rows use the first lineage id as the key name and the label "R1". That is an illustration of a non-registered reading, not a registered computation.
- Independence: audit 1 was the same model in another context, and I read it before forming my judgement (allowed by the brief).
