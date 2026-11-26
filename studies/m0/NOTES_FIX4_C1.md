# NOTES_FIX4_C1: C1 narrow repair round (implementer's notes; self-checked only)

Implementer: Claude Sonnet 5.5 (`claude-sonnet-5-5`), arbor-implementer role. **Astra review: NOT_PERFORMED.** Not independent review, not Astra validation, not human approval. Nothing is registered and nothing is in
`core.REGISTRY`; no model was run, nothing was downloaded. Every number is MEASURED (a run described here) unless it says analytical. Rules followed: LEAD_RULINGS_5 (R-24 to R-29), R-19, R-20, R-21, R-12; the
human lead's bound 0.15 (two-sided). The private sets are descriptive readings wherever a margin reads NOT EVALUABLE (R-29). Lineages are clusters; no strata are proposed.

## Result in one table

| | count |
|---|---|
| fix-3 current lineages (audit 4 section 1) | 37 |
| dropped (NOT REGISTERED) | 10 lineages: partition_pass_f3, loop_sum, grid_path_table, string_pair_table, coin_change_table_f3, bubble_pass, mirror_pointers, cellular_update_f3, majority_vote_scan_f3, bfs_queue (insertion_sort, minmax_track, kadane_scan stay out, as in fix 3) |
| shape dropped | sieve_marking_f3 flags shape (closed form); fast_power_f3 base and bsum shapes (R-20) |
| level repairs (c) | func_branch -> func_branch_f4, func_compose_f3 -> func_compose_f4, slices -> slices_f4 |
| surviving lineages | **27** |
| surviving clusters | **18 with the two variants, 16 without** (`manifests/c1_fix4_clusters.json`) |
| G (smaller part, N // 2) | 9 (8 without the variants); demand 10 x (ceil(4000/9) + ceil(20000/9) + 100) = **27,680** per cluster and level (analytical) |
| largest level-wide cheap excess among survivors | 0.115 (slices_f4, level 3, audit-4 best-strategy-per-shape `EFF_S`); next 0.110 (circle_elimination_r2 L0, func_compose_f4 L4, sieve_marking_f4 L0) |
| capacity | all 27 lineages x 7 levels supply 35,300 (the largest count asked, G = 7) under `core.draw_items` as `generate_pool` calls it: every level passes at G = 9 per lineage and per cluster |
| answer keys | 28,350 items (27 x 7 x 150): 0 errors, 0 key mismatches, 0 run disagreements, 0 not-one-line, 0 second-solver mismatches |

Surviving clusters (18): B1 {string_build_f3, list_build_f3, nested_pairs_f3}, B2 {func_branch_f4, func_compose_f4}, B3 {slices_f4, string_methods_f3}, B5 {euclid_gcd_traced_f3, cond_chain_f3},
B6 {fib_like_f3, fib_shapes_recursive_f3, recursive_calls_r2}, B7 {bytecode_loop_f3, turtle_walk_f3}, B8 {bracket_matching_f3, postfix_evaluation}, and single-lineage clusters while_counter,
digit_peel, run_length_scan, sieve_marking, binary_search, merge_two_sorted, union_find_links, circle_elimination, shared_lists; plus the two variant clusters fast_power_square_map (fast_power_f4) and
counter_list_state_machine (counter_list_f3). B4 (all three table lineages), bubble, partition, mirror, bfs, cellular, majority left the count. The clusters are the audit's strict map (audit 3 section 2, audit 4
section 6); they are not re-derived here.

## What was repaired

(a) Hygiene. `tests/test_m0_generators.py` has no failure in a C1 file; no existing file was edited (no R-27 in-place edit was needed). At the start of the round that test showed 2 failures
(`r1_fix4_a3_heur.py` iterating `set()` and importing `gen`), in another implementer's new R1 files, not C1; they were gone when I ran the suite again at the end (81 passed). The new C1 files import only the
standard library and `studies`, and call no `hash()`; the auditors' scripts are run by path as subprocesses, never imported.

(b) Wording defects. Audit 4 names none for a surviving lineage (section 2: "the frame is fixed; I found no ambiguity"); its hazards (negative operands of `//` and `%` in func_compose_f3 and bytecode_loop_f3,
negative slice bounds in slices, string_methods_f3, string_build_f3) are Python-defined for "a Python program". Nothing was changed for (b).

(c) Collapsed levels. Method (`c1_fix4_levels.py`, measured on 400 items per level, seed 71): a level step is COLLAPSED if, with the same per-item random stream at L and L+1, at least 99 per cent of the items
are textually identical (the generator ignores the level), or more than 1 per cent of a level's items repeat at another level. These two thresholds were set after I had seen the pre-repair figures (100 per cent for
the collapsed steps, at most 87 per cent elsewhere); the criterion is mine, not the lead's. Found collapsed (`manifests/c1_fix4_levels_pre_repair.json`): `func_branch` (L0->L1 and L3->L4, L4->L5, L5->L6: 100 per
cent identical), `func_compose_f3` (the same four steps). `slices` was not collapsed by the criterion (46-48 per cent identical at the pairs L0/L1, L2/L3, L4/L5) but its string half drew the same length
`1 + level // 2 + 1` for each pair of levels; I repaired it too. Repairs, each in `lineages_c1_fix4.py` with its stated parameters in the docstring:
- `func_branch_f4`: threshold t up to 12 + 2 x level, call arguments up to 20 + 4 x level, multiplier up to 5 + level // 2, offsets up to 9 + level; even branch from level 2; 2 calls, 3 from level 3, 4 from level 5.
- `func_compose_f4`: a up to 3 + level, b and c up to 13 + level, argument -9..24 + level, modulus up to 17 + 2 x level (level 6 equals the fix-3 ranges); h from level 3; two calls from level 2.
- `slices_f4`: string of 2 + level // 2 pseudo-words plus level % 2 extra letters; list of 6 + level values as before.
Re-measured (final set, `manifests/c1_fix4_levels_final_set.json`): no step collapsed in any of the 27 lineages (largest shared-stream identity share 87 per cent, nested_pairs_f3 L5->L6, which widens its
loop-bound upper limit 8 + level by one per level). REPORTED, NOT A CRITERION: the steps at which none of five features (executed lines, AST nodes, characters, largest literal, longest list; two-sample KS at the
1 per cent critical value 0.115) separates the two levels: func_compose_f4 L0->L1, L3->L4, L4->L5, L5->L6 (a range grows by one per level; the effect is nominal), while_counter_f3 L4->L5 and L5->L6,
euclid_gcd_traced_f3 L2->L3. The stated parameter rises at those steps; I cannot show it in these features at 400 items.

(d) Map correction (R-20): `lineages_c1_fix4_clusters.py` (new file; the fix-3 map is unchanged) files `fast_power_f4` in the cluster `C1.fast_power_square_map` and `counter_list_f3` in
`C1.counter_list_state_machine`; neither is under `fast_power` or `counter_list`. `fast_power_f4` is the fix-3 builder with its `res` shape only (the shape draw removed; no redraw).
`sieve_marking_f4` is the fix-3 builder with the strike-sum shape only (the audit's advice; the flag-list shape has an order-free closed form).

## What was dropped and why (reasons in `lineages_c1_fix4.DROPPED_AUDIT4`; measured numbers in `manifests/c1_fix4_survivors.json`)

Measured with the audit-4 script (`s4_rules_v2.py` + `s5_analyse_v2.py`, seed 71), the fix-3 battery re-run (`c1_fix4_battery.py`, seed 83) and the audit-3 script (`a3_shortcuts.py` via `c1_fix4_a3_run.py`, seed 71):
level-wide largest cheap excess over levels 0-6 (the audit-4 `EFF_S`, its most-frequent key, the best single S or F rule's level share, closed forms over all shapes summed, the battery's and audit 3's most-frequent key,
best generic and per-rule level shares).

| lineage | this round's largest | audit-4 reference | finding |
|---|---|---|---|
| partition_pass_f3 | 1.000 (closed forms over the three shapes) | 1.000 | closed form |
| loop_sum | 1.000 (`F.arith_series`) | 1.000 | closed form |
| grid_path_table | 0.775 | 0.780 | greedy path; count-0 reject is not needed for well-posedness (R-19) |
| string_pair_table | 0.360 | 0.395 | edit-cell and LCS-cell formulas |
| coin_change_table_f3 | 0.318 | 0.328 | greedy and ceil(T / max coin); the sentinel-99 reject is a valid answer rejected (R-19) |
| bubble_pass | 0.547 | 0.585 | 'move the extreme to the end' at L0, L1 |
| mirror_pointers | 0.215 | 0.230 | poss-shape MF; the no-unequal-pair reject is the answer 0 for the poss shape (R-19) |
| cellular_update_f3 | 0.215 | 0.188 | above 0.15; capacity L0 at the draw budget in audit 4 |
| majority_vote_scan_f3 | 0.145 | 0.190 | dropped on the audit's figure: my draw gives 0.145 (below), the audit's gives 0.190 (above); a measurement above the bound exists |
| bfs_queue | 0.268 | 0.247 | above 0.15 (target shape: answer 2 in 0.36-0.58 of the shape) |
| sieve_marking_f3, flags shape | in shape 1.000 at every level (`F.order_free_divisor_test`) | 1.000 | closed form; shape dropped, strike-sum kept: 0.110 |
| fast_power_f3, base and bsum shapes | in shape <= 0.03 | audit caveat | R-20: res only |

R-19 (answer-conditional rejects) for the survivors, shown one by one (`lineages_c1_fix4.RETRY_SITES`; `tests/test_m0_c1_fix4_lineages.py::test_reject_table_*` pins the set of survivors that have a reject of their own):
- run_length_scan: rejects the `long` shape when nothing is kept, i.e. an EMPTY answer. Needed for well-posedness: the scorer treats an empty answer as no answer (`scoring.extract`, `in_grammar('line', '')` is False).
- string_methods_f3: rejects an empty string at any step of the chain or as the answer; same reason, and an empty intermediate string leaves no letter for the next replace.
- euclid_gcd_traced_f3 (equal operands; fewer than max(4, 3 + level // 2) rounds), shared_lists_f3 (an alias of a name to itself), circle_elimination_r2 (fewer than 4 live flags): conditions on the structure of the
  program or the trace, not on the printed answer; validity. Audit 4 section 4 lists them as "trace-conditioned" and "structural"; the euclid reject biases toward small quotients (5,369 retries per 2,800 items in
  my draw); I left it as audit 4 did not name it a defect.
- every builder's shared `_finish` rejects an answer that is not a fixed point of the scorer's normalisation (upper case, padding, a double space, empty, a final full stop) and a program that cannot run; needed:
  a key that normalisation would change could never be matched.
- coin_change_table_f3 (99), grid_path_table (0), mirror_pointers (poss shape: 0) reject VALID answers: not needed, and removing them is not an allowed repair: dropped.

## Measurements that fix the survivors (R-26: the rule scripts re-run on every survivor, every level)

Largest level-wide excess per survivor and level is in `manifests/c1_fix4_survivors.json` (`level_wide_cheap_per_level`, rule named) and `manifests/c1_fix4_rules_final_set.json`. The maximum over the 27 survivors
and 7 levels is 0.115. Nothing in a survivor is above 0.15 level-wide, so nothing fell in the re-run (`DROPPED_AFTER_REMEASURE` is empty).
Counted: the audit-4 S, F and generic rules, the battery's rules (its control rules `C.*`, which re-run the program itself, are excluded), the audit-3 rules and generic rules (its four rules that run a mutated copy of the
program are excluded: that script scores a mutation that changes nothing as a hit, e.g. `no_back` where no command 6 exists, 0.67 of turtle_walk_f3 L0).

REPORTED, NOT COUNTED, PENDING LEAD REVIEW (these decide counts if the lead reads R-24 differently):
- Partial-trace mutations (audit class M: one feature ignored, the rest traced; audit 4 does not count them in its "cheap" figures, and neither did the lead's table). Survivors above 0.15 under them: func_branch_f4
  0.662 (the even branch is rarely taken), union_find_links_f3 0.270, circle_elimination_r2 0.268, cond_chain_f3 0.233, string_build_f3 0.155. If they counted: 22 lineages, 16 clusters (14 without the variants).
- In-shape excess (a rule's hit rate inside one shape; the lead's table and audit 4 count level-wide, and a shape is a part of the level): survivors above 0.15 in a shape: slices_f4 0.286 (sum_list, most frequent key),
  circle_elimination_r2 0.198, binary_search_f3 0.175, nested_pairs_f3 0.151 (all most-frequent-key in shape). I did not drop shapes for this.

Capacity (`c1_fix4_capacity.py`, throwaway seed 4242, `core.draw_items` as `generate_pool` calls it; text de-duplication after NFKC, case fold, whitespace collapse, identifiers included; per-lineage `taken`
set, so cross-lineage collisions are not simulated): all 189 lineage-levels supplied 35,300, the count asked (G = 7 demand), so every one passes the demand at G = 9 (27,680), and at the literal reading G = N = 18
(14,350). Per cluster the sum is at least 35,300 at every level. Nothing here is a per-cluster-builder result: every lineage passes on its own (R-28). NOT re-measured: the stricter readings of a "distinct item"
(R-16, unruled): audit 4 section 7 found that discounting literals that do not change control flow fails for most clusters (124 of 175 cluster-levels at G = 12); that measurement was not repeated for this set.

Answer keys (`c1_fix4_exec.py`, seed 5): 150 items per level, each program run in a FRESH `python -I -S` subprocess under the venv Python 3.12.14 and under /opt/homebrew/bin/python3.15, each with PYTHONHASHSEED 0 and 98765,
and the second solver `solvers_c1.c1_trace`: 28,350 items, all zero (above). An independent simulation of fast_power_f4's key (the test) agrees on 7 x 60 items.

## Commands (cwd = the worktree; throwaway seeds 71, 83, 4242, 5, 20261125; `PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0`)

```
uv run --locked python -m studies.m0.c1_fix4_draw --per-level 400 --seed 71 --out <gen71> --workers 8          # the 37 fix-3 lineages (+ sieve/fast_power f4 under their originals' names)
uv run --locked python -m studies.m0.c1_fix4_draw --per-level 400 --seed 71 --out <gen72> --ids <the 27> --workers 8
.venv/bin/python -I docs/reviews/m0-lineage-decision-2026-11-25/audit4_c1/s4_rules_v2.py <gen72> <rules72>
.venv/bin/python -I docs/reviews/m0-lineage-decision-2026-11-25/audit4_c1/s5_analyse_v2.py <rules72> <s5_72.json>
uv run --locked python -m studies.m0.c1_fix4_battery --per-level 400 --seed 83 --only <aliases of the 27> --out <battery83b.json>
python -m studies.m0.c1_fix4_a3_run --gen <gen72> --a3 docs/reviews/m0-lineage-decision-2026-11-25/audit3_c1/a3_shortcuts.py --out <a3run72>
uv run --locked python -m studies.m0.c1_fix4_rules_table --a4 <s5_72.json> --battery <battery83b.json> --a3-dir <a3run72> --out studies/m0/manifests/c1_fix4_rules_final_set.json
uv run --locked python -m studies.m0.c1_fix4_levels --gen <gen72> --out studies/m0/manifests/c1_fix4_levels_final_set.json --aliased
uv run --locked python -m studies.m0.c1_fix4_capacity --ids <the 27> --count 35300 --seed 4242 --out studies/m0/manifests/c1_fix4_capacity_raw.json --workers 9
uv run --locked python -m studies.m0.c1_fix4_exec --per-level 150 --seed 5 --interpreters <venv py>,/opt/homebrew/bin/python3.15 --hash-seeds 0,98765 --ids <the 27> --out studies/m0/manifests/c1_fix4_exec.json
uv run --locked python -m studies.m0.c1_fix4_survivors --rules72 ... --out studies/m0/manifests/c1_fix4_survivors.json      # input hashes are in the manifest
```
The same draw/rules/battery/a3 commands on the 37-lineage draw (gen71, seed 71; battery seed 83) give `c1_fix4_rules_fix3_set.json` (the dropped lineages' numbers) and `c1_fix4_levels_pre_repair.json`.
Environment: macOS arm64, Python 3.12.14 (uv venv, `--locked`), 18 cores shared; `uv.lock` and `pyproject.toml` untouched. Checks run: `uv run --locked ruff check .` (All checks passed);
`uv run --locked pytest tests/test_m0_generators.py tests/test_m0_c1_fix4_*.py -q`: 153 passed (81 + 72); `uv run --locked pytest tests/test_m0_c1_fix3_*.py -q`: 117 passed. mypy was not run (the repository checks only `src/arborlm`).

## Files written (all new)

`studies/m0/lineages_c1_fix4.py`, `lineages_c1_fix4_clusters.py`, `c1_fix4_draw.py`, `c1_fix4_battery.py`, `c1_fix4_a3_run.py`, `c1_fix4_rules_table.py`, `c1_fix4_levels.py`, `c1_fix4_capacity.py`, `c1_fix4_exec.py`,
`c1_fix4_survivors.py`, this file; `studies/m0/manifests/c1_fix4_survivors.json`, `c1_fix4_clusters.json`, `c1_fix4_rules_final_set.json`, `c1_fix4_rules_fix3_set.json`, `c1_fix4_levels_final_set.json`,
`c1_fix4_levels_pre_repair.json`, `c1_fix4_capacity_raw.json`, `c1_fix4_exec.json`; `tests/test_m0_c1_fix4_lineages.py`, `_clusters.py`, `_pipeline.py` (72 tests). Raw draws, rule outputs and run logs are in the
git-ignored scratch directory `experiments/_scratch/m0_fix4_c1_20261125/` (nothing deleted).

## What I could not verify, and judgement calls

- The "level-wide" reading of the bound (above) is my reading of R-24 and of how the lead's counts were made; the in-shape and mutation readings are reported above.
- The audit-3 script's shape rules target the OLD programs; run on fix-3 programs under the old ids they mostly parse and score near 0, and I do not know which of its rules are still meaningful. The battery's shape rules
  are keyed on ids ending `_f3`, so for `func_branch_f4` and `slices_f4` (aliases of older ids) only its generic rules ran.
- The level criterion and its two thresholds are mine and were set after seeing the pre-repair figures. A level step I call distinct may differ only slightly (func_compose_f4).
- func_branch_f4's and func_compose_f4's repairs widen ranges; they were measured once and not tuned (R-26: no second pass). Whether widening the func_branch argument range changed the share of items that reach the
  else branches was not measured.
- No 50-item human-style read; no independent second solver other than `solvers_c1.c1_trace` (the repository's own tree walker); the cluster map is the auditor's, not re-derived; the cross-evaluation entries are
  copied from audits 3 and 4 and unchanged except for the variants.
- Capacity is not measured under the unruled stricter readings of a distinct item (R-16).
- Single throwaway draws (400 per level); the figures near the bound carry sampling error (majority_vote_scan_f3: 0.145 here, 0.190 in the audit).

## Slips

No forbidden command was run. I started one background capacity run as `( ... &)` inside a shell command (not a tool background task); it finished by itself and `ps` showed no leftover process. The Write tool was
refused for this worktree by a hook (it names a different worktree), so every file was written through Bash heredocs or small python scripts, as the brief allowed. I used one foreground `sleep 20`.
