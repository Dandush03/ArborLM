# AUDIT3_C1: independent re-audit of the C1 lineage set after its fix round (M0, ADR-0033)

- Auditor: Claude Opus 5.5 (`claude-opus-5-5`), arbor-auditor role. **Astra review: NOT_PERFORMED.** Not Astra validation, not human approval.
- Audited: worktree `.claude/worktrees/agent-a0c9d741ea96ce52f`, branch `claude/m0-impl`, HEAD `f122e6bc`. Nothing written there except one EMPTY
  directory `docs/reviews/m0-lineage-decision-2026-11-25/audit3_c1/` (created by `mkdir` before a write hook refused writes into another worktree).
  **All files of this audit are in `/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_audit3_c1_20261125/`** (reached through the
  session worktree's `experiments` symlink); the coordinator has to copy them into the review folder. No git command changing state was run.
- Environment: macOS arm64, uv 0.12.15, Python 3.12.14 (`uv run --locked --offline`, `PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0`, cwd = audited
  worktree) and system Python 3.15.1 for the second execution interpreter. Throwaway seeds 7 (items) and 11 (capacity); no registered seed used.
- Independence: findings were written and hashed before opening any author note (`b0_findings_before_notes.txt`, SHA-256 `d03c4a11...8567`).
  Afterwards I opened `NOTES_LINEAGE_REPAIR.md` (it holds no C1 fix-round text), the rev2 manifest's note/shortcut summary and the rev2 capacity JSON.
  I could NOT locate the fix round's list of "eight new tells"; my own list below is independent of it.

## Scripts (each starts `# ruff: noqa`) and commands

| step | script | command | output |
|---|---|---|---|
| draw 400/level, 45 lineages | `a1_gen.py` | `uv run --locked --offline python $D/a1_gen.py --per-level 400 --seed 7 --out $D/gen7` | `gen7/`, `a1_gen_out2.txt` (`a1_gen_out.txt` = first attempt, wrong path, failed) |
| execute every program | `a2_exec.py` | `python3 a2_exec.py gen7 a2_exec_gen7.json <venv py3.12> /opt/homebrew/bin/python3` | `a2_exec_gen7.json`, `a2_exec_out.txt` |
| shapes, formulas, shortcuts | `a3_shortcuts.py`, `a4_table.py` | venv python `-I a3_shortcuts.py gen7 ...`; `python3 a4_table.py` | `a3_shortcuts_gen7.json`, `a4_table_gen7.txt` |
| cross-eval docstrings | `a5_xeval_docs.py` | `python3 a5_xeval_docs.py studies/m0` | `a5_xeval_docs_out.txt` |
| capacity K0/K1/K2 | `a6_capacity.py`, `a9_capacity_table.py` | `uv run ... a6_capacity.py --target 25000 --budget 75000` | `a6_capacity_seed11.json`, `a9_capacity_table.txt` (`a6_smoke.json` = smoke run) |
| hazards, corrected formulas | `a7_hazards_and_fixes.py` | venv python `-I` | `a7_hazards_gen7.json`, `a7_out.txt` |
| cluster map | `a8_clusters.py` | `uv run ... a8_clusters.py` | `a8_clusters_out.txt` |
| tests | | `uv run --locked --offline pytest -p no:cacheprovider tests/test_m0_*.py -q` | `a10_pytest_out.txt` |

## 1. Current set and keys

Current set (own reading of `SUPERSEDES`/`PROPOSED`): 40 lineages (equal to `current_ids()`) + 5 PROPOSED traced shapes. 126,000 items (45 x 7 levels x 400)
run in fresh subprocesses (2 s alarm, 300 s process timeout), full builtins, stdout redirected, under 3.12.14 and 3.15.1, each with PYTHONHASHSEED 0 and
98765: **0 errors, 0 key mismatches, 0 run disagreements, 0 outputs not exactly one line, 0 question/source mismatches.** Hazards (Python-defined, not
version-dependent): mixed-sign `//`/`%` in 531/2800 bytecode_loop_r2 and 147/2800 func_compose items; negative slice bounds/steps in slices 2454,
string_methods 1172, string_build 877 items; max call depth 17 (recursive_calls_r2). Wording: no ambiguity found; the question frame is fixed. Slip:
bytecode_loop_r2 docstring says 4-12 pairs, code gives up to 14.

## 2. Clusters ("procedure = the program's algorithm", strict)

Mine **28**, map **29**. Pairwise disagreements: 2, both from one merge: I put `recursive_calls_r2` with `fib_like`/`fib_shapes_recursive` (a recursive
integer function whose call tree is expanded; split/mutual/listfold differ from two/tri only in the argument map and coefficients; the map's own B4 merges
different recurrences filled by one method). All B1-B8 accepted. Strictest with the map's S1-S3: mine 22 (map 23); with my two further borderline pairs
(postfix~bytecode: coded-instruction interpreters; kadane~minmax): 20. Lenient 40.

Cross-evaluation (same algorithm; read from docstrings, `a5`): strong: B5 = R2.gcd_euclid, M1.gcd_lcm; fast_power = R2.modular_power; binary_search =
R2.binary_search_trace; B8 = R2.bracket_match; B4 = R2.coin_change_min, R2.lcs_length, M1.S5_unbounded_table (change_ways); cellular_update =
R2.cellular_automaton; circle_elimination = R1.containers_queue_line (elimination_josephus); run_length_scan = R2.run_length; kadane = R2.max_subarray_sum;
B6 = M1.S7_step_rule (recurrence_iterate); digit_peel = R2.from_base/to_base. Medium: postfix ~ R2.stack_machine/expression_eval; mirror ~
R2.palindrome_check; bubble/insertion ~ R2.sort_list; minmax ~ R1.order_extreme; counter_list/majority ~ M1.mode_tally; B1 ~ R2.count_divisible,
M1.arithmetic_series; B7 ~ R1.boolean_lights (compass_turns), R1.spatial_grid_walk; bfs/union_find ~ R1.categories_follow; B3 ~ R2.list_ops,
string_rewrite. `manifests/cross_evaluation_procedures.json` (R-7) does not exist at f122e6bc.

## 3. Formula-answerable (verified by my code = key in 100 % of the shape at all 7 levels)

string_build[len] = b - a; while_counter[shrink] = x0 - d*ceil((x0-T)/d); euclid_gcd[gcd] = gcd(x,y); fast_power_r2[res] = pow(b,e,m), [base] =
pow(b,2^L,m), [bsum] = b + sum_{k=1..L-1} pow(b,2^k,m); fast_power_traced[res_after] = pow(b, e mod 2^s, m), [oddsum] = sum over set bits of the
same terms; insertion_sort[list] = sorted(first K)+rest, [at] = that[i], [shifts] = inversions of the first K; **insertion_sort_traced[hole] =
#{x in xs[:K-1]: not(x op key)} - 1, [holesum] = sum of those ranks**; kadane_scan[best] = max subarray, [cur] = max suffix sum, [curs] = sum of
prefix max-suffix sums; **kadane_scan_traced[cur_at] = max suffix sum of xs[:p]**, [restarts] = sum of i with max-suffix(xs[:i]) < 0 (per-position,
about the work of tracing); minmax_track[all] = max/min, first index, their sum; partition_pass[swapj] = sum of j < m-1 with xs[j] op pivot (xs[j] is
still the input value); digit_peel[base-10 sum/even/countge, about 44 % of items] = read the digits of the printed literal; binary_search[last,
closed, target present, 13 %] = index of the target; counter_list = residue histogram. My first fast_power bsum/oddsum formula reduced the round-0 base
mod m and scored 0.74-0.99 (my mistake, kept in `a3`); corrected in `a7`: 1.000.
Traced replacements: euclid_gcd_traced forces tracing (no formula; best rule <= MF 0.05-0.14). insertion_sort_traced and kadane_scan_traced[cur_at] and
fast_power_traced[res_after] do NOT. bracket_matching_traced is not formula but has cheap tells (below).

## 4. Shortcuts (rate inside the shape, core levels L1-L5; open answers, chance 0; MF = most frequent key, 2-fold CV)

cond_chain gcd: a 0.33-0.48, b 0.44-0.71 (MF in shape 0.17-0.24); sieve_marking_r2[indexsum] "flagged primes and 0, 1": 0.34-0.53 (MF 0.08) -- the
dropped count shape's tell survives in the kept shape; string_methods[count]: key '0' in 0.83-0.89; merge_two_sorted_r2: MF 0.21-0.32 (10 distinct keys at
L3); func_compose L3+: MF 0.15-0.23 (9 distinct keys); insertion_sort[at] input echo 0.42-0.55; while_counter[grow] floor(log) 0.49-0.58;
euclid_gcd[rsum] literal y 0.19-0.22 (L1-L3, MF 0.03); bracket_matching[height] opens-closes 0.47-0.51 (L1-L2); bracket_matching_traced[height_at]
0.41-0.63, [pops] sum of all closer positions 0.16-0.57; kadane_scan_traced[restarts] '0' 0.27-0.37; insertion_sort_traced MF 0.16-0.28;
bytecode_loop_r2 "ignore the skips" 0.28-0.39 (sum-of-arguments tell now 0.03-0.08); majority_vote_scan_r2[pair]: printed count is even in 100 % (n even);
turtle_walk_r2 '0' 0.21 at L1 (count-F tell gone).
**R-1: redraws conditioned on a heuristic remain** (lineages the fix round did not touch): kadane_scan (best not max/sum+/sum: those rules score
exactly 0.00; cur not last), euclid_gcd (gcd not a literal: 0.00), partition_pass (list not the input), union_find_links (root not the query node: 0.00),
shared_lists (answer not the naive-copy answer). bracket_matching rejects answers 0 / -1 / height 0 (validity-like; PENDING LEAD REVIEW).

## 5. Capacity at worst-case demand

Reading confirmed in `ggen.demand_per_level`/`lineage_gates.demand_at_g` and ADR 6.2/8: need = 10 x (ceil(24,000/G) + 100) on core levels, 1,000 on
reserve levels: G=14 18,150; G=15 17,000; G=20 13,000; G=11 22,820; G=10 25,000. Fix round used the even spread (3,400 at G=20). Reading difference
(PENDING LEAD REVIEW): ADR 6.5 can put the pools on a reserve level, so 1,000 is not least favourable.
- K1 (names do not count; my criterion for R-5): **per cluster (my map, traced shapes in their clusters) 0 failing cluster-levels at G = 11, 14, 15, 20**;
  G=10: sieve_marking_r2 L1 24,990 (budget hit, Chao1 52k). Reserve: digit_peel L0 16,555 and sieve L0 10,371 pass 1,000, fail 18,150.
  **Per lineage** (what `core.generate_pool` actually allocates): G=14 28 failing cells, G=20 19: nested_pairs L1-L5 (2,586-6,991), list_build L1-L5
  (about 4,700), fib_shapes_recursive L1-L5 (about 8,300), func_compose L1-L2 (about 8,500), cond_chain L1-L2 (about 6,500), plus at G=14 fib_like
  L1-L5 (about 16,700), euclid_gcd L1-L2, euclid_gcd_traced L1-L2. Fix-round counts (cond_chain 2,020, list_build 2,226, nested_pairs 704 at L1) are
  lower because its exhibit stopped at 3 x 3,400 + 1,000 draws; same renaming criterion (verified by reading `alpha_key`).
- K2 (also literals that do not change control flow do not count; the coordinator's stricter criterion): G=14 **101 of 140** cluster-levels fail; G=20 90.
  Collapsed examples: cellular_update_r2 13, counter_list 12, kadane_scan 16, func_branch+func_compose 20-218, fib cluster 319-6,166.
  K1 is my reading of the spec: ADR 6.2 counts "distinct items", R-5 excludes names, setting sentence and order, and 6.2 lists parameters as shape
  variation within a lineage, not as item identity. Which criterion applies: PENDING LEAD REVIEW.

## 6. Verdicts (count after them)

REGISTRABLE AS IS: bfs_queue, bubble_pass, cellular_update_r2, circle_elimination_r2, coin_change_table, fib_like, fib_shapes_recursive, func_branch,
grid_path_table, postfix_evaluation, recursive_calls_r2, run_length_scan, slices, string_pair_table, turtle_walk_r2, euclid_gcd_traced (as the gcd
replacement), bytecode_loop_r2 (no-skip rule 0.28-0.39 noted), loop_sum, list_build, nested_pairs, mirror_pointers (the last four have no loop-carried state
other than an accumulator of independent terms: PENDING LEAD REVIEW whether that is "tracing"); capacity per lineage fails for list_build, nested_pairs,
fib_shapes_recursive unless the pools are allocated per cluster.
NEEDS FIX: cond_chain (gcd tell), sieve_marking_r2 (indexsum tell), string_methods (count '0'), merge_two_sorted_r2 (answer concentration),
func_compose (L3+ modulus), string_build (drop len), while_counter (shrink formula, grow log tell), digit_peel (drop base 10), binary_search (last shape),
partition_pass (swapj formula; R-1 redraw), shared_lists (R-1), union_find_links (R-1), bracket_matching (height tell; answer-conditioned redraws),
bracket_matching_traced (tells 0.4-0.6), majority_vote_scan_r2 (even-count tell, minor), fast_power_traced (drop res_after; oddsum is a trace of b).
REPLACE BY TRACED-STATE SHAPE: euclid_gcd (gcd shape -> euclid_gcd_traced; rsum tell also), fast_power_r2 (res shape), kadane_scan (all shapes; R-1).
SHOULD NOT BE REGISTERED (as written): insertion_sort and insertion_sort_traced (both closed form), minmax_track (every shape closed form; no
non-formula state exists), kadane_scan_traced[cur_at], counter_list (histogram; PENDING LEAD REVIEW).
Cluster count: 28 strict now; if the four SHOULD-NOT lineages are dropped and kadane gets no valid shape, the insertion, minmax, kadane and
counter_list clusters disappear: **24** (12/12 per part, G=12, need 21,000 under K1; not re-run at that G, but every per-cluster K1 count except
sieve L1 reached 25,000 or the cluster sum exceeds 21,000 -- read from `a9`; fast_power_r2 alone has 18,289 at L1, so the fast_power cluster passes only with fast_power_traced in it).

## Tests

`522 passed, 2 xfailed, 1 warning in 896.86s` (torch/NumPy warning), as expected.

## 7. Not verified

No second solver checked; no fixture file re-read; the 50-item human-style read was not done; part split by cluster shuffle not recomputed; capacity
is a lower bound where the budget was hit; K2 counts are lower bounds where K1 reached its target first; the "eight new tells" list was not found.
