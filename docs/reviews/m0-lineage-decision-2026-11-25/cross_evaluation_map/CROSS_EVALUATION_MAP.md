# M0 cross-evaluation procedure map: a proposal (R1, R2, M1, C1)

Status: a proposal by an independent `arbor-auditor` context (Claude Opus 5.5, `claude-opus-5-5`), 2026-11-25, written between 22:17 and 22:40 EST. It is not the map of record. Nothing is registered, merged, dropped or repaired here. The same-procedure test, the treatment of borderline pairs and the partition mechanics are for the human lead to decide. This is engineering evidence. It is not Astra validation and not human approval.

## 1. What was read, and in what order

- **Working definition.** `docs/decisions/ADR-0033-addendum-1-lineage-clusters.md` on `claude/m0-spec`, **DRAFT 2** (commit `a2fb316f`, SHA-256 `0df152b115928d34e939d0e01e641097a743694ac23787848a6cb394554e087f`), section 1 item 1 (the test), section 3 (cross-evaluation rule) and section 4 (partition). **DRAFT 3** (commit `9788a8ef`, SHA-256 `2df30a29…`) was committed while I worked. I re-read its sections 1, 3, 4 and 4A, and step 4 below is computed under both drafts. Draft 3 changes three things that matter here: X is dealt B first; "candidate" replaces "registered"; and it states that "a lineage that is not registered still joins" (section 3 item 1, vector V4), which draft 2 implied but did not say. It also specifies the borderline-group option (section 4 item 9).
- **Inputs** (read-only worktree on `claude/m0-impl`, uncommitted fix-4 files read as they are; hashes were the same at 22:17 and 22:28):
  `r1_fix4_survivors.json` `e1a7a092…`, `r2_fix4_survivors.json` `2456dac6…`, `m1_fix4_survivors.json` `153e6837…`, `c1_fix4_survivors.json` `eaedec75…`, `c1_fix4_clusters.json` `6cefaf9e…` (full hashes in the JSON's `inputs`).
- **Order.**
  1. Survivor lists and strict cluster maps from the manifests.
  2. Generators run through the repository's own loaders, three levels per lineage (`s01`, `s02`).
  3. Procedures and pair grades written and hashed: `judgement_before_reading_notes_or_audit_overlap_lists.json`, SHA-256 `8d25b2f40d48257da673d894cde4853779ad675f043d774aa8a041485e78876c`.
  4. Only then did I read the audit3/audit4 overlap sections, `NOTES_FIX4_*.md`, the per-evaluation `CROSS_EVALUATION` dicts and `LEAD_RULINGS_2..6.md`.

  Changes after reading are additions, marked `added_after_reading` (`s02b`, `s03b`). The hashed file is not edited.
- **Survivor counts read.** R1: 12 shapes in 10 clusters. R2: **18** lineages in 18 clusters. M1: 29 lineages in 17 clusters. C1: 27 lineages in 18 clusters, 16 without the two variant clusters. The brief and `LEAD_RULINGS_6.md` say R2 has 19. See section 9, discrepancy 1.

## 2. Environment and commands

macOS 27.2.1 arm64. uv 0.12.15. Python 3.12.14 from the implementation worktree's locked environment. `uv sync --locked --dry-run` reported "Would make no changes". I ran no model, download, training, commit or seed of record. Every random draw used a throwaway string seed, `random.Random(f"xeval-map-sample|{lid}|{level}")`. I computed no shuffle and no split of the real clusters with seed 400004.

```sh
W=/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f
cd /Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_crosseval_map_20261125/deliver
R="env PYTHONDONTWRITEBYTECODE=1 uv run --locked --project $W python"
PYTHONPATH=$W $R s01_samples.py $W > s01_samples.out.txt                     # every survivor + K0, levels 0/3/6
PYTHONPATH=$W $R s02_unregistered_neighbours.py > s02_unregistered_neighbours.out.txt
PYTHONPATH=$W $R s02b_unregistered_members_of_surviving_clusters.py > s02b_unregistered_members_of_surviving_clusters.out.txt
$R s03_build_map.py $W > s03_build_map.out.txt                               # writes the JSON (pre-reading judgement)
$R s03b_post_reading_update.py > s03b_post_reading_update.out.txt            # additions after reading
$R s04_recompute.py cross_evaluation_procedures_proposed.json > s04_recompute.out.txt
$R s04_recompute.py cross_evaluation_procedures_proposed.json --promote B14 [--promote B16]      # sensitivity
$R s04_recompute.py cross_evaluation_procedures_proposed.json --drop-file drops_scenario_<x>.txt  # scenarios
$R s05_bounds_by_enumeration.py cross_evaluation_procedures_proposed.json > s05_bounds_by_enumeration.out.txt
$R s06_partition_bounds_drafts.py cross_evaluation_procedures_proposed.json > s06_partition_bounds_drafts.out.txt
$R s07_attach_global_clusters.py > s07_attach_global_clusters.out.txt
```

**Recomputing after drops.** Put the dropped lineage ids, one per line, in `dropped_lineages.txt` (empty at delivery), or in the JSON's `dropped_since_fix4`. Then run `s04_recompute.py cross_evaluation_procedures_proposed.json --drop-file dropped_lineages.txt`. A strict cluster with no lineage left vanishes, and so does every pair touching it. `s05` and `s06` take the same `--drop-file`. `s04` and `s06` use separate component code. `s05` re-enumerates every deal outcome. All three agree on every count (section 6). `SHA256SUMS.txt` lists every file.

## 3. Procedures

The JSON (`lineages[].procedure`, `strict_clusters[].cluster_procedure`) holds one line for each of the 86 survivors, from rendered items and builder code. For C1 the procedure is the program's algorithm (addendum section 2). The statements that decide pairs are quoted in the pair table below.

## 4. Cross-evaluation pairs of strict clusters

### STRONG (7): the same algorithm under the written test

| id | pair (eval:cluster) | lineages compared | evidence |
|---|---|---|---|
| S1 | R2:binary_search_trace ~ C1:binary_search | R2.binary_search_trace ~ C1.binary_search_f3 | Both are binary search on a sorted list, read out as the probe trace. C1's lower-bound variant is a tie-break or parameter change. |
| S2 | R2:run_length ~ C1:run_length_scan | same names | Identical run-length encoding (letter + count). |
| S3 | R2:crt_smallest ~ M1:crt_congruence | R2.crt_smallest ~ M1.crt_congruence_r3 | Smallest positive solution of 2 to 4 congruences. Only the frame differs. |
| S4 | M1:gcd_lcm ~ C1:B5 | M1.gcd_lcm_r4 ~ C1.euclid_gcd_traced_f3 | Euclid's remainder step. C1 reads weighted remainders after at most 2 rounds, a different read-out of the same state. *Against:* M1 is often solved by factorisation, and lcm adds a·b/gcd. |
| S5 | R1:venn_counting ~ M1:inclusion_exclusion | R1.venn_counting_r5 ~ M1.inclusion_exclusion_r3 | Inclusion-exclusion over Venn regions. The read-out (none / exactly k / union) and the number of sets are parameters. |
| S6 | R2:kth_smallest (holds the survivor R2.sort_list) ~ M1:median_list | R2.sort_list ~ M1.median_list_r3 | The median is the middle order statistic. R2's own map already merged sorting with k-th smallest. |
| S7 | R2:from_base ~ C1:digit_peel | R2.from_base ~ C1.digit_peel_f3 | Positional base conversion. C1 peels base-b digits with `%` and `//`, then usually recombines them by Horner. Inverting the question is a same-cluster change, and R2's map put to/from base in one cluster. *Against:* the survivor R2.from_base is the Horner direction only. |

### BORDERLINE (16): related; reasons both ways are in the JSON

| id | pair | for | against |
|---|---|---|---|
| B1 | R1:boolean_lights (compass_turns) ~ C1:B7 (turtle_walk) | the turtle keeps heading mod 4, as compass_turns does | the turtle also keeps (x, y) and reads out the position (a different data structure) |
| B2 | R1:spatial_grid_walk ~ C1:B7 (turtle_walk) | both are unit-vector position updates | R1 moves are absolute and stop at walls; C1 moves are heading-relative with variable lengths |
| B3 | R1:categories_default_exceptions ~ C1:union_find_links | both chase parent pointers up a forest | union-find also does unions and prints the parent array |
| B4 | R1:graph_shortest_route ~ R2:cheapest_network | Dijkstra and Prim are the same frontier greedy | different problems; Kruskal is the usual MST route |
| B5 | R1:equivalence_exchange_rates ~ M1:S3_multiplicative_chain | both multiply ratios along a chain | R1's core step is finding the path in a graph |
| B6 | R1:conditional_threshold_rule ~ M1:S2_weighted_sum | both are a weighted sum, then a read-out | only generic arithmetic is shared |
| B7 | R2:cheapest_network ~ C1:union_find_links | Kruskal is union-find | Prim needs no union-find, and C1 reads the parent array |
| B8 | R2:expression_eval ~ C1:B8 (postfix_evaluation) | both evaluate expressions with a stack | R2 is infix with stated precedence (it needs parsing); C1 is postfix |
| B9 | R2:string_rewrite_nonidentity ~ C1:B3 (string_methods) | R2's rewrite is `str.replace` in sequence | in C1, replace is one step among slices and case changes |
| B10 | R2:count_divisible ~ C1:B1 (list_build, nested_pairs) | both filter by a modulus test and accumulate | a generic loop |
| B11 | R2:kth_smallest (sort_list) ~ C1:merge_two_sorted | merging is merge sort's step | sorting needs no merge; C1 reads statistics of the comparisons |
| B12 | R2:digit_root ~ C1:digit_peel | both are digit sums | R2 gives the decimal string, so no division is needed |
| B13 | M1:last_digit_power ~ C1:fast_power_square_map | the C1 loop has the square-and-multiply skeleton | its squaring is perturbed (`b*b + c`), so it computes no power |
| B14 | M1:S7_step_rule ~ C1:B6 | both iterate a recurrence | first-order with a position term vs second-order; **the audits grade this STRONG** |
| B15 | M1:division_counting ~ C1:digit_peel | both extract mixed-radix digits with `%` and `//` | M1 is two fixed steps with different divisors |
| B16 | M1:S7_step_rule ~ C1:B1 **through the unregistered C1.loop_sum** (added after reading) | loop_sum sums an affine function over an arithmetic range (audit 4 C1: closed form 1.000) | its filter and mixed-sign updates make it B1's filter-accumulate loop |

I considered ten more pairs and did not link them (JSON `considered_not_linked`): weekday shift ~ clock duration, decision tree ~ func_branch, tiered_pricing ~ func_branch, prime_factors ~ sieve_marking, swap_tracking ~ list_ops, list_ops ~ C1 slices, luhn ~ digit_peel, from_base ~ clock_duration, cellular_automaton ~ boolean_lights, finite_differences ~ S7/B6.

### Unregistered lineages attached to a survivor's procedure

These are nodes of the addendum's graph. They carry the teaching ban (A9) but do not make a cluster cross-evaluation.

- **Rendered here:**
  - STRONG: R2.gcd_euclid ~ M1.gcd_lcm/C1.B5; R2.modular_power (with R2.permutation_power) ~ M1.last_digit_power; R2.prime_factor_query ~ M1.prime_factors; R2.bracket_match and R2.stack_machine ~ C1.B8; C1.coin_change_table_f3 ~ M1.S5 (change_ways); C1.cellular_update_f3 ~ R2.cellular_automaton.
  - BORDERLINE: C1.bfs_queue ~ R1.graph_shortest_route.
- **From the audits, not rendered here:** R1.activity_selection_r5 ~ R2.interval_scheduling; R1.mst_cost_r4 ~ R2.cheapest_network; R1.containers_queue_line_r5 ~ R2.list_ops (the r5 builder, which I read, is a queue simulation, not Josephus); C1.bubble_pass ~ R2.sort_list/M1.median_list; and weaker links in the JSON.

## 5. Within-evaluation findings (findings only; nothing changed)

- **R1:** the `boolean_lights` cluster merges a bit-vector XOR (boolean_lights_r4) with a scalar heading mod 4 (compass_turns). Under the test's "data structure" clause these may be distinct. The merge is in the conservative direction.
- **R2:** grid_sum and count_divisible (select-and-sum) are kept apart; they may be one procedure.
- **M1:**
  - tiered_pricing may belong to S2 (weighted sum). Audit 4 M1 lists the same.
  - clock_duration ~ S2, and S1 ~ S7 via consecutive/arithmetic_series, are the audit's borderlines. I have no further view on either.
- **C1:**
  - B6 merges recursive_calls_r2 (a divide recursion on j//2 and j − j//2) with Fibonacci-type order-2 recurrences. By the "dependency structure" clause they may be distinct; the merge is conservative.
  - fast_power_f4's bit scan is digit_peel's base-2 scan. Audit 4 C1 also lists this as borderline.

## 6. Global clusters (transitive merging) and counts per evaluation

**Reading 1: STRONG only.** 56 global clusters, 7 of them cross-evaluation, each joining two strict clusters: S1 to S7 as listed. No evaluation loses a cluster to transitive merging. The largest global cluster is {M1:gcd_lcm, C1:B5}: 2 strict clusters and 3 lineages. Every other cross cluster has 2 lineages.

**Reading 2: STRONG + BORDERLINE.** 40 global clusters, 15 of them cross-evaluation. Transitive merges inside an evaluation:
- R1: boolean_lights + spatial_grid_walk (via B7); categories_default_exceptions + graph_shortest_route (via union_find and cheapest_network).
- R2: digit_root + from_base (via digit_peel).
- C1: B1 + B6 (via M1:S7).

The four largest components:
- {C1:B1, C1:B6, M1:S7, R2:count_divisible}: 4 strict clusters, 9 lineages. The largest.
- {C1:digit_peel, R2:from_base, R2:digit_root, M1:division_counting}: 4 strict clusters, 4 lineages.
- {C1:union_find, R1:categories, R1:graph_shortest_route, R2:cheapest_network}: 4 strict clusters, 4 lineages.
- {C1:B7, R1:boolean_lights, R1:spatial_grid_walk}: 3 strict clusters, 5 lineages.

The full member lists are in `s04_recompute.out.txt` and in the JSON (`reading_1_strong_only`, `reading_2_strong_plus_borderline`).

| Independent units per evaluation (a global cluster counts once in each evaluation it touches) | R1 | R2 | M1 | C1 |
|---|---|---|---|---|
| strict clusters (fix-4) | 10 | 18 | 17 | 18 |
| reading 1, G_e (cross / single) | **10** (1 / 9) | **18** (5 / 13) | **17** (4 / 13) | **18** (4 / 14) |
| reading 2, G_e (cross / single) | **8** (5 / 3) | **17** (9 / 8) | **17** (9 / 8) | **17** (11 / 6) |
| reading 1 with B14 STRONG (the audits' grade) | 10 | 18 | 17 (5 / 12) | 18 (5 / 13) |
| reading 1 with B14 and B16 STRONG | 10 | 18 | 17 | 17 (B1 + B6 merge) |
| reading 1, C1 variant clusters not counted | 10 | 18 | 17 | 16 |
| reading 1, the 6 M1 PENDING-LEAD-REVIEW lineages dropped | 10 | 18 | 13 (S4 vanishes) | 18 (3 cross) |
| reading 1, the 8 M1 R-36 held lineages dropped | 10 | 18 | 17 | 18 |

## 7. Part sizes the partition text allows (counts only; enumeration over every shuffle outcome; `s04`, `s05`, `s06`)

| reading / text | R1 A..B | R2 | M1 | C1 |
|---|---|---|---|---|
| 1, draft 2 (deal A first) | 5 / 5, fixed | 9 / 9 | 8 / 9 | 9 / 9 |
| 1, draft 3 (deal B first) | 5 / 5 | 9 / 9 | 8 / 9 | 9 / 9 |
| 1, draft 3 option item 9 (borderline groups kept in one part) | A 3..7; smaller part 3..5 | A 8..9; smaller part 8..9 | 8 / 9 | A 8..9; smaller part 8..9 |
| 2, draft 2 or draft 3 | A 3..5; smaller part **3..4**; off the 4/4 split in 2.56 % of shuffles (165 of 6,435 deal subsets) | 8 / 9 | 8 / 9 | 8 / 9 |

Under reading 1, step 3 absorbs every outcome of the X shuffle, so the parts are exactly ⌊G/2⌋ / ⌈G/2⌉ whatever the seed. Imbalance appears only under reading 2, in R1, where 5 of 8 units are cross-evaluation. These are partition-stage sizes. Under draft 3 stage 4, capacity drops after the partition do not rebalance, so registered G per part can be lower.

## 8. Where the text is not determinate (for the human lead)

1. **Unregistered lineages join components.** Draft 3 states this; draft 2 implies it ("nodes … registered or not"). The map of record must judge every written lineage: about 38 in R1, 40 in R2, 36 in M1 and more than 40 in C1. **This map judged the survivors fully and the unregistered ones only in part.** One such bridge was found after reading the audits: C1.loop_sum, NOT REGISTERED and still in B1, links B1 to M1.S7. Others may exist, and they can change the counts above.
2. **Candidate vs survivor.** Draft 3 partitions candidates, whose conditions include second solvers and the auditor's wording read. I took the survivors to be the candidates.
3. **C1 variant clusters** (fast_power_square_map, counter_list_state_machine). Neither draft says whether they count (C1: 18 or 16).
4. **Borderline pairs.**
   - Draft 2 leaves them free and gives no mechanics for keeping them together.
   - Draft 3 item 9 gives mechanics. Under it, R1's parts range from 3/7 to 7/3 clusters, because groups have unequal size.
   - Section 1 item 3 asks for the "strictest" count beside every G. Reading 2 is that count.
5. **Transitive merging vs binding parts only** (section 13 item 5). Under "bind only", reading 2 keeps G at 10 / 18 / 17 / 18, but how bound units enter steps 1 to 3 is not written (draft 3 item 9 covers borderline groups, not this).
6. **Identity.** The identity is the smallest id over all nodes, unregistered included, so it depends on the unfinished unregistered judgements. This changes the shuffle order, not the counts.
7. **Deal order.** It changed between drafts (A first → B first). With odd |X| (7 in reading 1, 15 in reading 2) it decides which part gets the extra X cluster; the counts above do not change.

## 9. Discrepancies, including my own errors

1. **R2: 18 vs 19.** The manifest (22:16) marks R2.to_base_wide NOT_REGISTERED: capacity under `core.generate_pool` at G = 9, where L0 supplied 15,928 of 27,680, and the lineage "passes only under a per-cluster builder". `NOTES_FIX4_R2.md` ("all 19") and `LEAD_RULINGS_6.md` count 19. M1 keeps its R-36 lineages in the same situation as survivors (29), while R2 marks them NOT_REGISTERED (R-28). The evaluations are treated inconsistently. No cluster count changes, because the from_base cluster survives.
2. **My judgement against the audits.**
   - B14 (M1.S7 ~ C1.B6): I say BORDERLINE; audit3_m1, audit4_m1, audit4_c1 and the C1 map say STRONG. Sensitivity runs are in the files.
   - R2.list_ops ~ C1.B3: I did not link them; three sources say medium.
   - B4, B5, B6, B7, B11 and B15 are mine alone.
   - B3 is close to the audits' union_find ~ R1.categories_follow and equivalence_classes. Those lineages are in a dropped cluster.
3. **My own errors, kept.**
   - `s03_build_map_attempt1_failed.py` used `M1.`-prefixed M1 cluster ids. The M1 map has none.
   - `s06_*_attempt1_smaller_part_bug.*` took the smaller part from the extremes only and under-reported reading 2's R1 range as 3..3. The correct range is 3..4, which `s04` and `s05` agree on.
   - I missed the loop_sum bridge until I read the audits.
4. **Draft changed mid-task.** Draft 2 → draft 3 (see section 1).
5. Some R1 unregistered lineages (kinship_ancestor_r4, kinship_cousins_r5, minimax_tree_r5, attribute_rule_r5 and others) could not be rendered with the loaders I used. Their links are unverified.

## 10. K0 and the teaching ban

K0 has one lineage, `K0.invented_fact` (lookup of invented facts with four options). It has no solution procedure and **overlaps with no survivor**. Other teaching material the addendum bans from held-out use is the unregistered lineages of part-B global clusters (A9). The ones attached to a survivor's procedure are listed in section 4.

## 11. Open questions (PENDING LEAD REVIEW)

1. The same-procedure test (section 13 item 4). In particular, does "data structure it maintains" separate a superset state (turtle) from a subset read-out (compass)? And does "dependency structure" separate order-1 from order-2 recurrences (B14)?
2. Whether borderline pairs merge, bind parts only, or stay free.
3. Whether unregistered lineages may join components. Do the C1.loop_sum bridge (B16) and the 9 unregistered links to survivors count?
4. Whether C1's variant clusters count.
5. The treatment of R2.to_base_wide against M1's R-36 lineages.
6. Whether the within-evaluation findings of section 5 should be re-judged.

Astra review: NOT_PERFORMED
