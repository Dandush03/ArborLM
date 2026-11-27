# R1 fix round 4 ("fix 4"): notes for the lead

Implementer: Claude Sonnet 5.5 (`arbor-implementer`), evaluation R1 only. Narrow repair round under the human lead's fifth decision (shortcut bound 0.15, two-sided; only hygiene, wording and collapsed-level repairs; everything else that fails is dropped) and
`LEAD_RULINGS_5.md` (R-24 to R-29). Nothing here is a registration, an independent review, Astra validation or human approval. No model was run, nothing downloaded or trained. Every number below is MEASURED (generator output scored by the rules named, or a
count) unless it says otherwise. The private sets are descriptive readings wherever a margin reads NOT EVALUABLE (R-29). Self-checks only.

## Result in five lines

- 37 shapes entered (the fix-round-3 set). 25 are NOT REGISTERED (23 by the audit-4 numbers before any re-run, 2 by the re-run); 12 SURVIVE.
- Survivors (12): boolean_lights_r4, compass_turns, categories_default_exceptions_r4, conditional_decision_tree_r6, conditional_threshold_rule_r4, equivalence_exchange_rates_r6, temporal_weekday_shift_r6, graph_shortest_route_r6, knights_knaves_r6,
  spatial_grid_walk_r5, swap_tracking_r5, venn_counting_r5. They fall in **10 strict clusters** (round-3 map unchanged; two clusters have two members).
- Largest counted rule excess among the survivors: **0.149** (graph_shortest_route_r6, level 1, 'fewest roads, then length'; primary run). In a replicate run at other seeds the same rule reads 0.158 and boolean_lights_r4 reads 0.155 (primary 0.121): see 'Noise'.
- Levels: all 14 shapes that entered the re-run produce 7 distinct level generators (7 of 7 classes under the auditor's level-identity test); 7 of them were repaired here.
- Capacity against `core.generate_pool` as written: 14 of 14 (part, level) cells pass at the stricter demand 49,000 per cluster and level (G = 5, R-11); no shortfall, no repeated text. Keys: 0 mismatches in 39,200 items against each of two independent solver sets.

## (a) Hygiene: two in-place edits (R-27)

`tests/test_m0_generators.py::test_no_hash_builtin_and_no_unsorted_set_or_dict_iteration_in_the_package` failed on four lines at the start of the round: `lineages_m1_fix3_c.py:116`, `lineages_r2_fix3_c.py:172` (other implementers' files; they now show as modified in the shared
worktree and the test passes, not my edits) and the two of mine:
1. `studies/m0/r1_fix3_battery.py` line 624, `h_mst`: `sum(w for w, _, _ in set(cheapest.values()))` is now `sum(w for w, _, _ in sorted(set(cheapest.values())))` (a sum of integers: order-free).
2. `studies/m0/r1_fix3_capacity.py` line 346, `_Canon.key`: `for w in set(words):` is now `for w in sorted(set(words)):` (the contexts are sorted before they are hashed).
Outputs unchanged, MEASURED: the structural key (`keys_of`) of 5,180 items (20 per level of each of the 37 fix-3 shapes) hashes to the same digest with the old file (from `git show HEAD:`) and the edited file, under PYTHONHASHSEED 0, 7 and 123; `h_mst` returns the identical dict on every mst_cost_r4 item
of those. `git diff` shows exactly these two one-line changes. After the edits `tests/test_m0_generators.py` passes (81 passed at the end of the round).

## What the drop rule was applied to, and how

The cheap-rule bound was applied as the fourth audit measured it. Rule classes are the auditor's (`final_table4.py`, copied into `r1_fix4_table.py`): C cheap (a count, one feature, a fitted constant / ratio / lookup), A approximate or partial procedure; both are counted. M (a misreading of a stated
convention) and exact algorithms are not counted (listed beside the counted value). Excess = max(eff, anti) of a rule over the base rate (a non-firing item scores chance); the raw 'low' of a closed-answer rule that always names one option is a floor (-1/k), not an exploitable gain, and is not counted, exactly as the
audit did. Union of batteries: the auditor's battery (`r1_fix4_a4_heur`, which includes audit 3's), the implementer's round-3 battery (`r1_fix3_battery.measure`, unchanged) and the fitted count-feature lookups (`r1_fix4_tells`).

**Stage 1 (23 shapes dropped with the audit's own numbers, not re-measured):** the audit-4 value (max over levels, counted classes) exceeds 0.15, or another named audit-4 defect applies. Values: queue +0.794, attribute_rule +0.580, equivalence_classes +0.616, categories_follow +0.543, kinship_cousins +0.444,
graph_bipartite +0.474, order_compare +0.454, road_reachability +0.438, elimination_bracket +0.430, activity_selection +0.399, tracking_accounts +0.390, conditional_chain +0.345, nim_xor +0.330, kinship_descendants +0.304, minimax_tree +0.216, critical_path +0.208, stack_piles +0.205, seating_row +0.192,
mst_cost +0.191, one_culprit +0.191, topological_order +0.190, kinship_ancestor +0.187, interval_overlap +0.180. I reproduced these numbers from the audit's own data files with my table code (the manifest lists the rule and level of each); I did not re-run the rules on these shapes.

**R-19, the two shapes named (shown, not assumed):**
- `categories_follow_r5`: the builder replants until the closure gives the drawn class (answer-conditional: it keeps the draw whose computed answer equals the drawn one; the audit measured 2.3 to 7.5 plantings per item depending on the class). It is NOT needed for well-posedness: the answer is computed by the closure of the premises, so an item whose planting gives another class is still well posed with
  that other answer. So it falls under R-13. Dropped anyway on the numbers (kind + group count +0.543).
- `kinship_ancestor_r4`: the `Retry` when fewer than two other people share the answer's profile (number of children, has-a-parent) is conditional on a property of the answer; it exists only to build the matched option set, and the item would be well posed without it. So it also falls under R-13. Dropped anyway on the numbers ('options in the child's own family tree' +0.187).

## (b) Wording defects

Audit 4 names one wording defect: `attribute_rule_r5` (negation scope unstated). It is dropped (rule +0.580), so no wording repair was made. The audit lists every other convention as stated. No wording or convention was changed in any survivor. One docstring claim was corrected in the new knights builder: the old docstring said the statement kind is 'independent of the speaker's type by
construction'; the redraw until the solution is unique makes that approximate (audit 4: +0.11 to +0.14).

## (c) Collapsed levels: seven shapes repaired in `lineages_r1_fix4_a.py` (ids end `_r6`)

Each `_r6` builder is the earlier builder with one change: a level term that differs at every level and grows with it. Procedure, answer rule, statement forms and conventions are unchanged; no rejection was added or removed. At level 0 each `_r6` builder reproduces the earlier builder's questions and answers exactly (tested, same stream).
Stated parameter (measured means in `manifests/r1_fix4_levels.json`; the tests assert the exact formulas):

| shape | stated parameter (level 0 to 6) | earlier |
|---|---|---|
| event_timeline_r6 | spine statements L = 4 + level (4..10); 2 + level // 3 other events | 4 + level // 2 |
| temporal_weekday_shift_r6 | spine links L = 5 + level (5..11) | 5 + level // 3 |
| spatial_relative_directions_r6 | spine facts L = 5 + level (5..11) | 5 + level // 3 |
| equivalence_exchange_rates_r6 | spine rates L = 3 + level (3..9) | 3 + level // 2 |
| knights_knaves_r6 | people n = 4 + level (4..10) | 4 + level // 2 |
| graph_shortest_route_r6 | decoy towns 2 + level (planted route h = 3,3,4,4,5,5,6 as before) | 2 + level // 2 |
| conditional_decision_tree_r6 | lights stated = depth + 2 + level (depth 3,3,4,4,4,5,5; 4 actions, 8 at level 6 as before) | depth + 2 |

The seven shapes that already had 7 distinct levels are unchanged: boolean_lights_r4 (presses 3 + 2 level, lamps 4 + level), compass_turns (commands 3 + 2 level), categories_default_exceptions_r4 (chain 17 to 35 groups), conditional_threshold_rule_r4 (members 6 + level), spatial_grid_walk_r5 (grid size DIMS[level], moves 4 + level + 0..3, blocked 3 + level // 3),
swap_tracking_r5 (operations 6 + 2 level), venn_counting_r5 (groups 2,2,3,3,3,4,4 and the asked quantity by level, region size 1 to 24 + 4 level: the groups count is not strictly rising; the level is distinct through the magnitude and the asked quantity). Level distinctness MEASURED by `r1_fix4_levels.level_classes` (seeds 4242 / 777): 7 classes for all 14. Mean question length per level
rises monotonically for every shape (e.g. knights 316 to 573 characters, decision tree 655 to 2,263, graph route 621 to 1,758).

## Re-run (R-26): seeds, results

Primary run: 1,000 items per level; auditor's battery seeds 5200 / 5300, implementer's battery 6200 / 6300 (the audit's own seeds, so the seven unchanged shapes reproduce the audit's values: 0.121, 0.095, 0.087, 0.082, 0.063, 0.044, 0.056). A replicate at other seeds (5400 / 5500, 6400 / 6500) is reported, not used to decide: the decision rule (primary run decides)
was fixed before the replicate was run. Largest counted excess per level L0 to L6 (primary), and the replicate maximum:

| shape | L0 | L1 | L2 | L3 | L4 | L5 | L6 | replicate max |
|---|---|---|---|---|---|---|---|---|
| boolean_lights_r4 | 0.121 | 0.092 | 0.093 | 0.037 | 0.048 | 0.041 | 0.029 | **0.155** |
| categories_default_exceptions_r4 | 0.095 | 0.061 | 0.063 | 0.068 | 0.051 | 0.042 | 0.035 | 0.084 |
| compass_turns | 0.087 | 0.017 | 0.011 | 0.018 | 0.019 | 0.016 | 0.011 | 0.092 |
| conditional_decision_tree_r6 | 0.041 | 0.032 | 0.016 | 0.022 | 0.021 | 0.025 | 0.023 | 0.041 |
| conditional_threshold_rule_r4 | 0.077 | 0.056 | 0.076 | 0.069 | 0.065 | 0.082 | 0.058 | 0.079 |
| equivalence_exchange_rates_r6 | 0.058 | 0.051 | 0.064 | 0.061 | 0.065 | 0.068 | 0.064 | 0.070 |
| temporal_weekday_shift_r6 | 0.044 | 0.021 | 0.017 | 0.015 | 0.017 | 0.005 | 0.012 | 0.023 |
| graph_shortest_route_r6 | 0.140 | **0.149** | 0.119 | 0.105 | 0.081 | 0.081 | 0.087 | **0.158** |
| knights_knaves_r6 | 0.129 | 0.123 | 0.135 | 0.107 | 0.133 | 0.138 | 0.130 | 0.138 |
| spatial_grid_walk_r5 | 0.033 | 0.032 | 0.040 | 0.047 | 0.041 | 0.063 | 0.039 | 0.052 |
| swap_tracking_r5 | 0.044 | 0.022 | 0.033 | 0.018 | 0.011 | 0.018 | 0.013 | 0.039 |
| venn_counting_r5 | 0.056 | 0.039 | 0.036 | 0.030 | 0.029 | 0.026 | 0.013 | 0.051 |
| (dropped at stage 2) event_timeline_r6 | 0.145 | 0.081 | 0.056 | 0.027 | 0.022 | 0.019 | 0.015 | 0.135 |
| (dropped at stage 2) spatial_relative_directions_r6 | 0.125 | 0.073 | 0.053 | 0.049 | 0.045 | 0.049 | 0.042 | 0.114 |

The rule behind each cell is in `manifests/r1_fix4_survivors.json` (per level: value, rule name, class). The level repairs did not raise any rule above 0.15 in the primary run (graph_shortest_route's 'fewest roads then length' stays near its audit value 0.146; the audit's value for the earlier builder was 0.146).

**Stage 2 (dropped by the re-run, 2 shapes):** `event_timeline_r6` and `spatial_relative_directions_r6` read at or below 0.15 on every rule but redraw when the answer is 0 (`raise Retry` on a zero sum; audit 4 section 3: 10 and 7 per 2,100 items; here 0.3 to 0.7 % and 0.0 to 1.0 % of draws). R-19 reading: a zero answer is a well-posed answer ('the same day', 'the same place'), so the
rejection is answer-conditional and not needed for well-posedness; removing it is not an R-25 repair; so both are dropped. **PENDING LEAD REVIEW**: audit 4 listed them under section 3 but its verdict table and R-19 did not name them; if the lead reads the zero rejection as needed or as outside R-13, both survive on their numbers (0.145 and 0.125 primary) and the cluster count stays 10
(the cluster has two other members). The code restores them by emptying two entries of `SECOND_STAGE_DROPS`; the capacity run would then be repeated.

**Not counted but listed (M class):** spatial_relative_directions_r6 'signed_axis_merged' +0.548; conditional_threshold_rule_r4 'abstain_as_no' +0.158 (primary max over levels); spatial_grid_walk 'east_west_mirrored' +0.056; others at most +0.024. If the lead counts M-class rules, conditional_threshold_rule_r4 (a singleton cluster) would be dropped and the cluster count would be 9; spatial_relative_directions is already dropped.
PENDING LEAD REVIEW on the C / A / M split (the auditor's own open point).

## Other rejections in the survivors (R-19 check of the whole set)

Only validity or feasibility rejections remain in the twelve: knights (a unique solution; no retries seen in 2,100 items), grid walk (a place for a blocked move exists; 5 to 17 % of draws), swap_tracking (a person whose item was moved by both kinds of operation exists; 0 to 3.7 %), boolean_lights_r4 (a non-empty set of pressed switches with the drawn parity exists; 7.7 % at level 0, 0.3 % at level 1, none after;
it depends on the drawn parity and the pressed multiset, not on the initial state, so the answer, initial xor parity, stays a fair coin). I judge these feasibility rejections; that judgement is mine and is flagged for the lead's review. Retry rates per level are in `manifests/r1_fix4_levels.json`.

## Capacity (R-28): `core.generate_pool` as written

`r1_fix4_capacity.py` calls `core.generate_pool` unchanged (per-lineage balance, de-duplication on the SHA-256 of the normalised question text, names included) with `core.part_lineages` pointed at the surviving shapes of the part (the shapes are not in `core.REGISTRY`). Parts by the cluster-keys partition at seed 400004: part A 5 clusters (5 shapes), part B 5 clusters (7 shapes);
G_total = 10, G_part = 5 (R-11: the smaller part). Demand 10 x (ceil(4,000 / G) + ceil(20,000 / G) + 100): 25,000 at G = 10 (the brief's reading) and 49,000 at G = 5 (R-11's reading); the pool was drawn for 49,000, so a pass is a pass at both. The builder gives every lineage the same quota, so to guarantee the smallest cluster (one shape: every cluster with a single lineage) its demand
each lineage is asked for 49,000 distinct questions at each level (reserve levels 0 and 6 included, R-10): one `generate_pool` call per (part, level), pool seed 7500 (throwaway), `shortfalls` recorded. Result MEASURED: 14 of 14 cells, 0 shortfalls, 0 repeated texts; every lineage supplied 49,000 (A: 245,000 items per level; B: 343,000). Wall time 10 to 160 s per cell.
Clusters passing at all 7 levels: 10 of 10 (`manifests/r1_fix4_capacity.json`, summary in `r1_fix4_survivors.json`). Reading is 'two items differ if their normalised texts differ'. The structural readings (a) and (b) of round 3 (names, labels relabelled: R-16, still not ruled) were NOT recomputed; under them the round-3 capacity of the unchanged shapes passed
(round-3 notes), and the repaired shapes only get larger items at each level, but I did not measure that.

## Answer keys (R-26)

(1) The existing second solvers of the test suite (`test_m0_r1_fix3_keys.SOLVERS`, `test_m0_r1_rev4_shapes.CHECKS`, `solvers_r1`) on 400 items per level, 14 shapes x 7 levels (seed block 9100): **39,200 items, 0 mismatches**. (2) The fourth auditor's text-only solvers (`solvers3.py`, `solvers4.py`, run from the audit directory, mapped from the `_r5` / `_r4` ids to the `_r6` ids:
the wording of the item is unchanged) on 400 per level (seed block 9200): **39,200 items, 0 mismatches, 0 ambiguous, 0 errors**. Both are self-checks; the R-9 second solver from a separate context does not exist for these shapes.

## Noise and the bound

The per-cell standard error is about 0.016 at 1,000 items and the maximum over many rules and 7 levels is biased upward by a few points. Two survivors sit within noise of the bound: graph_shortest_route_r6 (primary 0.149, replicate 0.158) and boolean_lights_r4 (primary 0.121, replicate 0.155; the shape is unchanged, the audit read 0.121 at the same seeds).
Under the rule fixed in advance (primary run decides) both survive. If the replicate decided instead, both would be dropped; boolean_lights shares its cluster with compass_turns (so the cluster count stays 10) and graph_shortest_route is a singleton (the count would be 9). PENDING LEAD REVIEW. I did not run a third seed to break the tie.
Also not counted anywhere: rules that are not in any script (the battery is a finite list), the one-sided 'low' floor of closed answers, and the structural uniformity of the draws.

## What was not done or not verified

- No independent second solver (R-9) and no check by a separate context; the checks above are mine and the auditor's earlier scripts rerun by me.
- The dropped shapes were not re-measured (stage 1 uses audit-4 numbers). A shape the audit measured at 0.18 to 0.22 might read lower on another seed; by the brief it is dropped, not re-opened.
- The cross-evaluation duplicates (R-15), fixtures for the `_r6` shapes (`fixtures/r1_fix3/` still holds round-3 files for the dropped shapes; I did not touch it), the addendum, power, and any model run: not done and not asked.
- Readability: level-6 items are long (decision tree about 2,260 characters, graph route 1,760); not reviewed by a person.
- Cluster ids are the round-3 map's group keys (the smallest base id of the group), so a surviving shape can sit in a cluster named after a dropped one (for example `R1.attribute_rule` holds only conditional_decision_tree_r6; `R1.conditional_chain` holds only knights_knaves_r6). The map itself was not changed.
- The partition (cluster keys, seed 400004) was recomputed on the survivors: it gives the 5 / 5 clusters above; the earlier 11 / 12 split no longer applies.

## Files

New: `studies/m0/lineages_r1_fix4_{common,a,clusters}.py`, `r1_fix4_{gen,levels,table,tells,measure,survivors,capacity}.py`, copies with attribution `r1_fix4_a3_solvers.py`, `r1_fix4_a3_heur.py`, `r1_fix4_a4_heur.py` (the auditor's `solvers3.py`, `heuristics3.py`, `heuristics4.py`; edits: imports, one `sorted(set(...))` in `h_mst`, `_r6` accepted where `_r5` was);
`manifests/r1_fix4_{survivors,levels,capacity}.json`; `tests/test_m0_r1_fix4_{sets,keys,tools}.py`. Edited in place (R-27): `r1_fix3_battery.py` (1 line), `r1_fix3_capacity.py` (1 line). Scratch (not removed): `/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_fix4_r1_20261125/` (run1, run2_replicate, capacity runs, key checks, hygiene comparison).

## Commands

`PYTHONHASHSEED=0 uv run --locked python -m studies.m0.r1_fix4_measure 1000 5200 5300 6200 6300 <dir>` (primary) and `... 1000 5400 5500 6400 6500 <dir>` (replicate); `... -m studies.m0.r1_fix4_capacity <out.json> 7500 5`; `... -m studies.m0.r1_fix4_levels studies/m0/manifests/r1_fix4_levels.json`;
`... -m studies.m0.r1_fix4_survivors <run dir> studies/m0/manifests/r1_fix4_capacity.json studies/m0/manifests/r1_fix4_survivors.json <replicate dir>`. Checks: `uv run --locked ruff check .` (all checks passed); `uv run --locked pytest tests/test_m0_generators.py tests/test_m0_r1_fix4_*.py -q` (143 passed); `uv run --locked pytest tests/test_m0_r1_fix3_*.py -q` (71 passed);
`uv run --locked pytest tests/test_m0_r1_*.py -q` (299 passed, includes both). `mypy` was not run (it covers `src/arborlm` only, untouched).

## Slips

One forbidden command was typed by mistake: `sed -i 's/^x//' /dev/null` (run once, targeting /dev/null, no file affected). A stray `mkdir -p /dev/null` also ran (failed harmlessly). The Write and Edit tools were refused in this worktree (hook); files were written through Bash heredocs and one-off python replacements, as the brief allowed. No commit, push, branch switch, delete or permission command.

Astra review: NOT_PERFORMED
