# M0 map of record (ADR-0033 addendum 1, section 4A stage 1): the auditor's report

Auditor: `arbor-auditor` context, model Claude Opus 5.5 (`claude-opus-5-5`, from session metadata). I wrote none of the lineages, none of the rule scripts and none of the earlier maps.
This is independent engineering evidence. It is not Astra validation and not human approval. **Astra review: NOT_PERFORMED.**
Nothing here registers anything, and no result is called a success.

## 1. Inputs and environment

- Specification: `ADR-0033-addendum-1-lineage-clusters.md` at `d70ba38d` (`claude/m0-spec`), sections 0, 1, 2, 3, 4 (item 9), 4A stage 1, 13 (items 4, 9, 17, 21). Approval record read for its effect on the map only: `HUMAN_LEAD_WORDS_9.md` (`f627389a`): the amendment is about the fresh run's uncounted rules and does not touch the map.
- Generators: `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f` (`claude/m0-impl`). HEAD was `206d45a9` when I started and `128a02a7` when I finished (three fresh-run preparation commits landed meanwhile). `git diff --quiet 7cd0ac5a HEAD -- studies/m0/lineages_*.py studies/m0/core.py` is empty, so the code I read is the code as at `7cd0ac5a`. I did not open `studies/m0/fresh_run/{r1,r2,m1,c1}/` (untracked, appeared during my work) or any fresh-run file.
- Earlier maps read (evidence, not the answer): `cross_evaluation_map/cross_evaluation_procedures_proposed.json` and `s04_recompute_after_final_checks.out.txt`; `audit1/` (pairs_judgement.csv, JUDGEMENT_BEFORE_AUTHOR_NOTES.md); `audit2_r1/JUDGEMENT_PART1_CLUSTERS.md`; the cluster sections of `audit3_r1`, `audit3_r2`, `audit3_c1`; `audit4_r1/my_clusters4.py` and its output; `AUDIT4_R2.md` s5, `AUDIT4_M1.md` s5, `AUDIT4_C1.md` s6; `audit_m1/JUDGEMENT_1_clusters.txt`, `pairs_666.tsv`; `audit_c1/JUDGEMENT_C1_LINEAGES.md`; `audit_r2/AUDIT_M0_R2_1.md` (grep). The auditors' maps are also recorded in the implementer's cluster files (`lineages_r1_clusters_v2.py`, `r2_fix3_clusters.py`, `lineages_r2_clusters.py`, `lineages_m1_clusters.py`, `lineages_m1_fix3_clusters.py`, `lineages_c1_fix3_clusters.py`, `lineages_c1_fix4_clusters.py`), which I read for that reason. `LEAD_RULINGS_*.md`: grep only, for R-2, R-7, R-15, R-20.
- Environment: macOS 27.2.1 arm64; `uv 0.12.15`; CPython 3.12.14 via `uv run --locked python`, standard library only; `PYTHONDONTWRITEBYTECODE=1` was set in the shell (no `.pyc` written in the implementation worktree; checked).
- Commands (cwd = the implementation worktree; `D=/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_fr_map_of_record_20261126/deliver`):
  - `uv run --locked python $D/scripts/e01_enumerate_all_code.py > $D/e01_enumerate_all_code.out.txt`
  - `uv run --locked python $D/scripts/e02_manifest_ids.py $D/e01_enumerate_all_code.out.txt > $D/e02_manifest_ids.out.txt`
  - `for e in R1 R2 M1 C1; do uv run --locked python $D/scripts/e03_docstrings.py $e > $D/e03_docstrings_$e.out.txt; done`
  - `uv run --locked python $D/scripts/e04_render_examples.py > $D/e04_render_examples.out.txt` (12 items, level 2, seed `random.Random(20261126 + i)` for the i-th id in the script's list)
  - `uv run --locked python $D/scripts/build_map.py $D` (attempt 1, kept: `map_of_record_attempt1.json`, `MAP_REASONS_attempt1.md`, `build_map_attempt1.out.txt`)
  - `uv run --locked python $D/scripts/build_map_v2.py $D > $D/build_map_v2.out.txt` (the map of record); run again under `PYTHONHASHSEED=0` and `4242`: identical SHA-256
  - `uv run --locked python $D/scripts/e05_checks.py $D studies/m0/manifests/survivor_list_of_record.json > $D/e05_checks.out.txt`
- No rule script was run, no rate was computed, no model was run, nothing was downloaded, no partition stream was computed.

## 2. How the written lineages were enumerated

1. Code (`e01`): every module `studies/m0/lineages_*.py` (98 modules) was imported; every `core.Lineage` object held in any module-level list or dict, and every entry of `core.REGISTRY`, was collected by id. That covers every round (batch 1, rev2, rev3, rev4, fix 3, fix 4, traced proposals). Result: 346 ids; `K0.invented_fact` is not a node (section 3 item 5), leaving **345 nodes**. R2 reuses one id across rounds (e.g. `R2.cheapest_network` has four builders); such an id is one node, and its citation lists every builder.
2. Manifests (`e02`): every lineage-id-shaped string in every file of `studies/m0/manifests/` (79 files).
3. In code, in no manifest: `K0.invented_fact` only (not a node).
4. In a manifest, not in code: `C1.counter_list_state_machine` and `C1.fast_power_square_map` (cluster names in `c1_fix4_clusters.json` and `c1_fix4_survivors.json`, not lineages), and `C1.bubble` (a prose fragment, "C1.bubble/insertion sorts", in `r2_fix3_cluster_map.json`). None is a lineage.
5. All 82 ids of `survivor_list_of_record.json` are nodes (a presence check only; the list decided nothing).

**PENDING LEAD REVIEW (scope).** I read "every written lineage whatever its status" as every id that any round wrote, superseded revisions included (e.g. `R1.seating_row` and `R1.seating_row_r5`). The earlier cross-evaluation map covered 86 ids (the survivors and a few dropped ones). A revision is linked to its stem, because it is the same written base rule rewritten, so including revisions changes no count by itself. It does change two things:
- Cluster identities. The smallest id is now often a batch-1 id, e.g. `C1.fast_power` instead of `C1.fast_power_f4`.
- What can join a cluster. An earlier round's shapes can now bring a lineage in: `C1.recursive_calls` was written as one lineage, so its fib shapes go into the same cluster as its split-off `C1.recursive_calls_r2`.

K0: `K0.invented_fact` is a multiple-choice lookup of invented facts. It implements none of the procedures in the map (section 3 item 5: nothing to list).

## 3. The reading of the written test (applied to every pair)

- **LINK:** an algorithm that is the procedure of one of the two lineages, as its code computes it, gives the answer of every item of the other, keeping the same data structure and step dependencies. Only the changes the test lists are allowed: renaming; the setting or frame; order; parameter values, including sizes, depths, number systems, moduli, tie-break rules and the asked position or extremum; negation or inversion; a different read-out of the same computed state.
- **BORDERLINE:** the test does not decide. The two share a core, but one has an added step, a different maintained data structure for part of the work, a different set of operations, or only some of its shapes are covered. Every undecided pair that an earlier auditor had as LINK or BORDERLINE is also BORDERLINE.
- **NONE:** the two share only topic, vocabulary, answer type or generic arithmetic, or the algorithms plainly differ.
- Revisions of one written base rule are LINK unless the procedure changed. Three were judged explicitly because the procedure changed or was contested: `C1.counter_list`~`_f3`, `C1.fast_power`~`_f3`, and the `C1.recursive_calls` split.

## 4. Counts (all from `build_map_v2.out.txt` and `e05_checks.out.txt`)

| | R1 | R2 | M1 | C1 | all |
|---|---|---|---|---|---|
| written lineages (nodes) | 122 | 44 | 95 | 84 | 345 |
| global clusters holding a lineage of the evaluation | 25 | 37 | 23 | 34 | 92 global clusters |
| of which single-evaluation clusters | 18 | 18 | 14 | 19 | 69 |

- Judged pairs (rows of `MAP_REASONS.md`): 425 = 245 explicit + 180 revision-chain rows. LINK 294 (180 revision + 114 explicit), BORDERLINE 99, NONE 32.
- Cross-evaluation components (clusters with lineages of two or more evaluations): **23** (listed in `build_map_v2.out.txt`). Four span three evaluations: `C1.circle_elimination` (C1, R1, R2), `C1.coin_change_table`, `C1.euclid_gcd` and `C1.fast_power` (each C1, M1, R2).
- Groups (components of the borderline graph over clusters): 30. Four hold more than one cluster, with 57, 5, 2 and 2 clusters. The group of 57 is the chaining of many borderline pairs, most of them carried from earlier maps; it is reported here and not judged further.
- Four borderline pairs fall inside one cluster and have no effect on groups: `C1.bfs_queue`~`R1.categories_follow`, `C1.union_find_links`~`R1.categories_follow`, `R1.order_tournament_wins`~`R1.topological_order`, `R2.bracket_match`~`R2.stack_machine`.
- Transitive merging inside an evaluation (section 3 item 2): lineages joined only through another evaluation.
  - R2: `R2.bracket_match` + `R2.stack_machine`, through C1 B8.
  - C1: `C1.bfs_queue` + `C1.union_find_links`, through R1's closure cluster.
  - C1: `C1.fib_like` + `C1.loop_sum`, through M1's step-rule cluster.

  I withdraw none of these links; the reasons are in `MAP_REASONS.md`. PENDING LEAD REVIEW: `audit_c1` had `C1.bfs_queue`~`C1.union_find_links` as NONE (a near-miss); they are merged here only by transitivity.

## 5. Where I differ from the earlier maps

23 explicit pairs changed against an earlier judgement (rows marked CHANGED in `MAP_REASONS.md`).

**Toward more links (BORDERLINE or NONE to LINK):**
- The fast_power variants:
  - `C1.fast_power`~`C1.fast_power_f3`: NONE to LINK. The earlier maps gave f3 its own cluster `fast_power_square_map` (audit4_c1, lead ruling R-20).
  - `C1.fast_power_f3`~`R2.modular_power`: medium to LINK.
  - `C1.fast_power_f4`~`M1.last_digit_power`: cross map B13 BORDERLINE to LINK.

  Reason: the program is the same square-and-multiply loop, with the offset c as a literal (rendered in `e04`). PENDING LEAD REVIEW: this departs from lead ruling R-20, which was made before the written test existed.
- `C1.fib_like`~`M1.recurrence_iterate`: cross map B14 BORDERLINE (STRONG in three audits) to LINK.
- `C1.loop_sum`~`M1.arithmetic_series`: cross map B16 BORDERLINE (STRONG in two maps) to LINK.
- `C1.mirror_pointers`~`R2.palindrome_check`: weak or medium (strong in audit4_r2) to LINK.
- `C1.union_find_links`~`R1.equivalence_classes`: medium to LINK.
- `C1.bfs_queue`~`R1.road_reachability`: medium to LINK.
- `C1.counter_list`~`M1.mode_tally`: borderline or medium to LINK.

**Toward fewer links (LINK to BORDERLINE).** In each pair the test does not decide, and section 1 item 3 and the brief both say that an unsure pair is borderline:
- C1 B1: all six pairs of `loop_sum`, `list_build`, `nested_pairs`, `string_build` (integer, list and string accumulators; nested_pairs has a second loop).
- C1 B4: `coin_change_table`~`grid_path_table`, `coin_change_table`~`string_pair_table`, `grid_path_table`~`string_pair_table` (1-D versus 2-D tables).
- C1 B5: `cond_chain`~`euclid_gcd` (subtractive rounds with extra branches versus remainder steps).
- C1 B7: `bytecode_loop`~`turtle_walk` (different maintained state).
- M1 S4: `binomial_choose`~`slot_permutations`.
- R1: `order_tournament_wins`~`topological_order` (in one cluster anyway, through `order_extreme`).

PENDING LEAD REVIEW: for an undecided pair the brief says both "record BORDERLINE if the earlier auditor had LINK" and "never resolve a doubt toward fewer links". I followed the first, which is also section 1 item 3's wording. The pairs listed above under "toward fewer links" are where the two instructions pull apart; under the other reading they would be LINK.

**Other changes:**
- `C1.counter_list`~`C1.counter_list_f3` was NONE (own cluster, R-20) and is BORDERLINE here. The state bucket reduces to the residue bucket at mul = 0 (mod k), but it adds a loop-carried dependency.
- Six pairs that no earlier map judged:
  - LINK: `R1.stable_matching`~`R2.deferred_acceptance_partner` (identical deferred acceptance).
  - BORDERLINE: `R1.swap_tracking`~`R2.permutation_power`, `M1.digit_puzzle`~`R1.one_culprit`, `C1.while_counter`~`M1.recurrence_iterate`, `C1.loop_sum`~`R2.count_divisible`, `C1.grid_path_table`~`R1.temporal_critical_path`.

**Differences from the cross-evaluation proposal:**
- Its 7 STRONG pairs are all LINK here. Of its 16 BORDERLINE pairs, 13 stay BORDERLINE and B13, B14 and B16 become LINK.
- Its unregistered links are judged here as nodes. All are LINK except `C1.bfs_queue`~`R1.graph_shortest_route`, which stays BORDERLINE as before.
- The audits' links to dropped lineages are LINK: `R1.activity_selection`~`R2.interval_scheduling`, `R1.mst_cost`~`R2.cheapest_network`, `R1.containers_queue_line`~`R2.list_ops`, `R1.nim_xor`~`R2.subtraction_game`, `C1.circle_elimination`~`R1.elimination_josephus`.
- Cluster identities differ, because the identity is now the smallest id over all written lineages.

**Attempt 1 to v2 (both kept; my slip).** audit3_c1 counted the C1 map's strictest groups S1 (numeric while loops) and S2 (in-place reordering) as borderline. In attempt 1 I recorded `bubble_pass`~`insertion_sort`, `insertion_sort`~`partition_pass` and `digit_peel`~`while_counter` as NONE, using audit_c1's near-miss list alone. v2 records them as BORDERLINE, adds the other S1 pairs as BORDERLINE, and adds two "weak" likenesses as NONE. The map's hash changed from `f83785105ecdad889c5eda2fc98ae9403a50876f11b393899cf7fafca362f535` (attempt 1) to the final hash below.

## 6. Pairs the test did not decide

Every BORDERLINE row (99) is a pair the test did not decide as one procedure:
- the pairs listed under "toward fewer links" in section 5, where an earlier auditor had LINK;
- `C1.counter_list`~`C1.counter_list_f3`, where the earlier maps had NONE;
- the rest, which carry an earlier BORDERLINE (or medium) judgement or are new findings of mine.

## 7. What I could not do, and disclosures

- **Independence.** Section 1 item 3 wants the judgement hashed before any author's notes are read. Before judging I read the builder docstrings (part of the code) and the implementer's cluster files, because those files record the earlier auditors' maps. They also contain the author's `DISAGREEMENTS` and borderline notes, which I therefore saw. I did not read `studies/m0/NOTES*.md`. My judgements were not hashed before that reading. PENDING LEAD REVIEW.
- I read the builder code and docstrings for every lineage, but I rendered items for only 12 ids (`e04`). Most judgements rest on reading the code.
- I did not re-judge all 595 audit1 pairs or all 666 audit_m1 pairs one by one. I re-judged every pair those audits marked as a merge, borderline or near-miss.
- I did not read `LEAD_RULINGS_*.md` in full (grep only, to avoid counts), so I may have missed a ruling about a specific link other than R-2, R-7, R-15 and R-20.
- No partition, no status, and no count of candidates or registered lineages was computed. The survivor list, the cheap-rule figures and the capacity counts decided nothing. I saw the earlier working counts in files I had to read for the maps (`s04_recompute_after_final_checks.out.txt`, `my_clusters_run1.txt`, a line of `LEAD_RULINGS_7.md`); they played no part in any judgement.

## 8. Outputs

- `map_of_record.json`: SHA-256 `1ba6ddd520dfe6514dfd282883ce4bc84660b7dca1abfefdac58285dcab5809c` (sorted keys, indent 2, trailing newline, no timestamp, no status field; the format checks are in `e05_checks.out.txt`).
- `MAP_REASONS.md`: one row per judged pair (425). Each row gives the earlier judgement and its source, my judgement, unchanged or CHANGED, the reason, and the builders of both ids (file:line, every round).
- `scripts/`: e01 to e05, `judgements.py` (attempt 1), `judgements_v2.py`, `build_map.py`, `build_map_v2.py`. `SHA256SUMS.txt` covers every file in the folder except itself.

Astra review: NOT_PERFORMED. Not human approval.
