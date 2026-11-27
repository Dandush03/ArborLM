# AUDIT_M0_C1_1: independent audit of the C1 lineages after authoring batch 1 (M0, ADR-0033 revision 4)

- Auditor: Claude Opus 5.5 (model id `claude-opus-5-5`, from session metadata), `arbor-auditor` role.
- **Astra review: NOT_PERFORMED.** This is not Astra validation and not human approval. It is independent engineering and
  mathematical evidence only.
- Audited: worktree `.claude/worktrees/agent-a0c9d741ea96ce52f`, branch `claude/m0-impl`, HEAD `1b33b7b2`; the C1 batch is commit
  `44b22f7e`. I wrote nothing in that worktree (`git status --short` empty before and after; 0 lines).
- Output folder: `experiments/_scratch/m0_lineage_audit_c1_20261125/` of the consolidation worktree. Note: `experiments` there is a
  symlink to `/Users/daniellaloush/dandush03/ArborLM/experiments`, so the files physically sit in the main checkout's git-ignored
  `experiments/_scratch/`. Nothing else under `experiments/` was touched.
- Environment: macOS-27.2.1-arm64; `uv 0.12.15`; project Python 3.12.14 via `uv run --locked --offline` from the audited worktree with
  `PYTHONDONTWRITEBYTECODE=1` (and `PYTHONHASHSEED=0` unless stated). Some stdlib-only analysis steps were first run with the system
  `python3` 3.15.1; every one of them was re-run under uv/3.12.14 and gave identical numbers (see section 11).
- Judgement written before reading the manifest, shortcut outputs or NOTES: `JUDGEMENT_C1_LINEAGES.md`, SHA-256
  `3bed12e3c606a3d839f5c43bffe36eb2d4e4dc09c664f65568ace5d66993fb0a`, hashed 2026-11-25T14:22:29Z (`JUDGEMENT_C1_LINEAGES.sha256`).
- Exposure before the judgement (disclosed in the judgement file too): a `grep` of `fixtures/C1_BATCH1_SCHEMA.md` printed its 25
  headings with the author's "strict confidence: clear/borderline" labels, and three module docstrings state author opinions
  (tables "may be one tabulation cluster", functions "func_branch/func_compose are non-recursive", swaps "bubble_pass is the
  adjacent-swap pass").

## Scripts and commands (all in the output folder; each starts with `# ruff: noqa`)

| step | script | command (cwd = audited worktree unless noted) | output |
|---|---|---|---|
| render 3 items/level, 39 lineages | `a01_render.py` | `PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 uv run --locked --offline python $D/a01_render.py` | `a01_render_out.txt` (819 programs) |
| own evaluator, ast-to-tree, renaming | `a02_myeval.py` | library | |
| all 3,500 fixtures | `a03_fixtures.py --isolated` | same prefix | `a03_fixtures_out.txt`, `a03_fixtures_result.json` |
| draw, key-check, capacity | `a04_generate.py gen1 --workers 14` | same prefix | `gen1/` (gzip trees + keys, `summary.json`) |
| hash-seed dependence | `a05_hashseed.py` | run with `PYTHONHASHSEED` = 0, 4242, random | `a05_hashseed_*.txt` |
| literal features from the tree | `a06_feats.py`, `a06_validate.py` | same prefix | `a06_validate_out.txt` |
| shortcuts v1 (failed shape key, kept) | `a07_shortcuts.py gen1` | cwd = $D, `uv run --project <audited> --locked --offline python` | `a07_shortcuts_gen1.json`, `a08_table_gen1.md` |
| shortcuts v2 | `a07b_shortcuts_v2.py gen1` / `gen1uv` | system python3, then uv (identical rates) | `a07_shortcuts_gen1_v2.json`, `a07b_per_shape_gen1.json`, `a08_table_gen1v2.md` |
| tables | `a08_table.py` | `python3 a08_table.py gen1v2 [--detail]` | `a08_*` |
| name collisions | `a09_name_collisions.py` | uv, cwd = $D | `a09_name_collisions_out.txt` |
| capacity estimates | `a10_capacity.py` | uv, cwd = $D | `a10_capacity_out.txt` |
| self-test of my evaluator | `a11_selftest_myeval.py` | same prefix | `a11_selftest_out.txt` |
| failing test | | `PYTHONDONTWRITEBYTECODE=1 uv run --locked --offline pytest -p no:cacheprovider tests/test_m0_generators.py tests/test_m0_c1_*.py -q` | 1 failed, 98 passed |

`$D` = the output folder. No model, download, training or registered benchmark was run.

## 1. The rule and the two readings of "procedure" for C1

ADR-0033 section 6.2: "Each rule shape is registered with a lineage: the hand-written base rule, a distinct solution procedure, from
which it derives. Shapes made mechanically from one base rule (by changing parameters, order, negation, names or surface frame)
share a lineage. **The cluster, for G and for every bootstrap, is the lineage.** G is the number of lineages per part."
On C1 the ADR says only (6.2 table) "Output prediction. Small deterministic Python programs from a typed grammar: arithmetic,
strings, lists, loops, conditionals, small functions. No imports, no input, bounded loops. Each prints exactly one line. The
question is that line", and (6.3) "C1 measures reading and tracing code. It does not measure writing it." It never says what a
C1 item's "solution procedure" is.

Ambiguous sentence: "the hand-written base rule, a distinct solution procedure". **PENDING LEAD REVIEW.**
- Reading P (the program's algorithm is the procedure): counts below.
- Reading T (the act of tracing is the procedure): every C1 item is solved by the same act (step through statements keeping a
  value table). Then G = 1 for all of C1, the A/B family partition separates no procedures, and no amount of authoring reaches
  any minimum. A weaker T (procedure = the set of language constructs a tracer must handle) gives roughly 8 to 10 clusters for
  the 39 lineages (judgement).

One line per lineage (the procedure under P) is in `JUDGEMENT_C1_LINEAGES.md`; I read every generator and 21 rendered items per
lineage (3 per level, `a01_render_out.txt`).

## 2. Cluster counts and merges (reading P)

| set | lenient | strict (mine) | maximal strict (mine + the author's borderline groupings I did not adopt) |
|---|---|---|---|
| existing 14 | 14 | 9 | 8 |
| new 25 among themselves | 25 | 21 | |
| new clusters not merging into an existing one | 25 | 19 | 14 |
| overall 39 | 39 | **28** | **22** |
| reading T | 1 (weak T: about 8-10) | | |

Merged under the strict reading only (none under lenient; no pair is the same named algorithm with only parameter changes):
- B1 loop_sum + string_build + list_build + nested_pairs: one "iterate an index range, evaluate a predicate/expression of the index, fold into an accumulator" skeleton (int vs str = number system; predicate = constraint mix; len/rev/sum/max = final question). nested_pairs is the weakest member (second loop).
- B2 func_branch + func_compose: substitute literal arguments into small non-recursive function bodies.
- B3 slices + string_methods: evaluate a chain of sequence operations on a literal (string_methods already contains slice/reverse).
- B4 coin_change_table + string_pair_table + grid_path_table: fill a DP table cell by cell from earlier cells with min/max/+; grid path-count `best[j] += best[j-1]` and coin `ways[a] += ways[a-c]` are the same update form; grid max-path and LCS share `max(up, left) + local`.
- B5 euclid_gcd (new) + cond_chain (existing): division vs fixed-count subtractive form of the same two-variable reduction. Measured support: cond_chain's key equals gcd of its two literals in 43-68% of items within its shapes (L1-L5).
- B6 recursive_calls (new) + fib_like (existing): recursive shapes "two" and "tri" are the linear recurrence fib_like iterates (a = b = 1, c = 0 is Fibonacci); 3 of 5 recursive shapes are other procedures, so this is a partial overlap.
- B7 bytecode_loop + turtle_walk: read a command sequence, dispatch on the command, update a small fixed state.
- B8 bracket_matching + postfix_evaluation: array stack with pointer; push on one token class, pop and act on the other.

Near-misses kept apart under both readings (reason in the judgement file): kadane/minmax_track, majority_vote/run_length,
insertion/bubble/partition, digit_peel/fast_power, digit_peel/euclid, postfix/bytecode, sieve/circle, counter_list/list_build,
mirror/merge/binary_search, bfs/union_find, cellular/list_build, cond_chain/fib_like, while_counter/digit_peel/euclid.
Within-lineage heterogeneity (under-counting, harmless to G but makes clusters less homogeneous): while_counter (3 procedures),
recursive_calls (5), string_pair_table (2), coin_change_table (2), grid_path_table (2).

The "maximal strict" column adds the author's borderline groupings: numeric while-loop group {while_counter, cond_chain, euclid,
digit_peel, fast_power}, in-place reordering {bubble, insertion, partition}, string pointer scans {mirror, run_length}.

## 3. Cross-evaluation duplicates (finding for the lead; nothing merged)

Same named algorithm in C1 and another evaluation (read from the other files' code/docstrings, parse only):
- strong: euclid_gcd = R2.gcd_euclid (remainder Euclid; also M1.gcd_lcm asks gcd); fast_power = R2.modular_power (repeated
  squaring); binary_search = R2.binary_search_trace; bracket_matching = R2.bracket_match; coin_change_table = R2.coin_change_min
  (fewest) and M1.change_ways (combinations); string_pair_table (LCS) = R2.lcs_length; cellular_update = R2.cellular_automaton;
  circle_elimination = R1.elimination_josephus; run_length_scan = R2.run_length (same letter+count format); kadane_scan =
  R2.max_subarray_sum; fib_like/recursive_calls "two" = M1.recurrence_iterate (sum_prev_two); digit_peel = R2.to_base (repeated
  % and //).
- medium/weak: postfix_evaluation ~ R2.stack_machine; bytecode_loop ~ R2.stack_machine; turtle_walk ~ R1.compass_turns /
  R1.spatial_grid_walk; union_find_links ~ R1.equivalence_classes; bfs_queue ~ R1.road_reachability / graph_shortest_route;
  bubble_pass/insertion_sort ~ R2.sort_list; mirror_pointers ~ R2.palindrome_check; minmax_track ~ R1.order_extreme /
  R2.kth_smallest; counter_list / majority_vote_scan ~ M1.mode_tally; loop_sum ~ R2.multiples_between / M1.arithmetic_series;
  string_methods ~ R2.string_rewrite; slices ~ R2.list_ops; sieve_marking ~ R2.prime_factor_query / M1.prime_factors (different
  procedure, same topic).
Why it matters (PENDING LEAD REVIEW): clusters are per evaluation part, so these do not inflate C1's G, but if a held-out (part B)
C1 family's algorithm is taught through another evaluation's part A, the held-out claim of section 6.4 is weakened; and
"complementarity" readings across evaluations partly measure the same procedure.

## 4. Keys and safety

My evaluator (`a02_myeval.py`) is written from the grammar description and Python semantics; it imports nothing from
`solvers_c1` or the generators, never calls exec/eval/compile, implements Python scoping (a name assigned in a function is local,
others read globals and are flagged), in-place `+=` on lists, slice index adjustment, floor division/modulo and int-to-text by
hand, and records constructs and hazards. Self-test (`a11`): 0 mismatches against the host's operators on 200,000 random slices,
200,000 floor div/mod pairs, 20,000 str() values, 20,000 count/replace cases; a one-literal mutation changes the output or raises
in 2,234/3,500 fixture programs, so the checker can fail.

Coverage and results:
- **All 3,500 fixture items** (25 lineages x 7 levels x 20; ids unique; no duplicate questions): question frame OK; `ast.parse`
  of the question source converted to a tree equals `structured.program` (render fidelity) for 3,500/3,500; my evaluator equals
  the key for 3,500/3,500; the repo's isolated runner `c1grammar.run_isolated` run twice: 0 nondeterministic, 0 differing from the
  key; all keys already normalised; `answer_type` line, `k` null.
- **448,000 further distinct items** I drew (`a04`, seed 20261125): 2,000 per level for each new lineage (350,000) and 1,000 per
  level for each existing one (98,000): 0 key disagreements with my evaluator, 0 render mismatches, 0 evaluator errors.
- Constructs vs the existing second solver (read, not imported; it supports calls len/sum/max/min/abs/str + user functions, methods
  upper/lower/replace/count, aug ops + - only correctly, `*` and others are computed as `*`): no item in the fixtures or in the
  448,000 uses anything else (no sorted/range calls, no other methods, aug ops only + and -, no aug on a list, no global read inside a
  function, no nested def). The author's statement that dict, set, break, bit operators, floats and most string methods are
  unavailable is correct: the renderer and tree have no such nodes.
- Termination: every while loop has a strictly monotone variant (Euclid b; digit n//base; fast_power e//2; sieve j += i, i >= 2;
  binary search interval; merge i or j; insertion j; mirror i < j; BFS head with each node enqueued once; union-find links only root
  to root, so no cycle; Josephus inner loop has at least one live flag because rounds <= live - 1; bytecode pc += 2; recursion
  arguments strictly decrease to a base case). Max evaluator steps over all 448,000 items: 2,740; max call depth 17 (fixtures).
- Hash and order: the grammar has no set/dict/hash. Generation is identical under `PYTHONHASHSEED` = 0, 4242 and random (one digest
  `a8180a21...92cc` over 39 lineages x 7 levels x 150 items). Generator-internal sets (bfs `arcs`, `seen`; shared_lists `used`) are
  sorted before iteration or used for membership only; `Counter.most_common` in majority_vote is tie-safe.
- Hazards (not errors; Python semantics are fixed and the question says "Python program"): mixed-sign floor `//`/`%` in 1,346 of
  14,000 bytecode_loop items (16 fixtures) and 398 func_compose items; negative slice steps/bounds in slices, string_build,
  string_methods.

**Defective items (key correct, program not what the lineage intends):** cellular_update writes a fixed accumulator name `w`, but
`w` is in `VARS`. When the inner loop variable is drawn as `w`, the "weighted" shape becomes `for w in range(n): w += w * x[w]`, which
prints `(n-1) * (1 + x[n-1])`, not the weighted sum. Fixtures affected: `C1.cellular_update/fixture/1/4` ('10'), `/1/14` ('10'),
`/1/16` ('10'), `/6/6` ('20'). In my draws: 256 of 6,904 weighted-shape items (3.7%); the cells variable cannot be `w` (such draws
raise and are redrawn). Other fixed names (`tot`, `far`, `cst`, `find`) are not in `VARS`.
No wrong, nondeterministic or ambiguous key was found.

## 5. The failing test

`tests/test_m0_generators.py::test_no_hash_builtin_and_no_unsorted_set_or_dict_iteration_in_the_package` fails with exactly
`AssertionError: [('c1_shortcut_check.py', 115, 'iterates set()')]`. The line is
`ans in {str(s.count(c)) for c in set(s)}` inside `oracle_list_stat`. It iterates a set of one-character strings (hash order), but
builds a set of counts used only for membership, so the result is order-independent. `c1_shortcut_check.py` does not generate items;
no generated item and no recorded statistic can depend on this order (my re-implementation with `sorted(set(s))` reproduces the
author's oracle values within sampling). It still makes the package test red; fix by `sorted(set(s))`. With it, the M0 generator
and C1 test files give 1 failed, 98 passed.

## 6. Shortcuts (own code; open answers, so the absolute rate is shown beside the most-frequent-key rate)

C1 keys are open lines (`k` null); no two-sided closed-answer analysis applies. Per lineage and level I measured the author's
battery (re-implemented, validated against an ast reading on 3,500 fixtures, 0 mismatches) and my own: O1 shape-constant (most
frequent key per printed expression, 2-fold cross-validated), O2 last int literal assigned, O3 first loop bound, O4 longest list
length, O5 best single literal rule out of about 60 (chosen on one half, scored on the other), O6 key '0' rate, O7 best rule per
printed expression (cross-validated), and lineage-specific rules R.*. Full table: `a08_table_gen1v2.md`; per shape:
`a07b_per_shape_gen1.json`.

Single simple rules that explain a large share (rate inside the shape where the rule applies; share of that shape in brackets):
- **turtle_walk: "count the F commands"** = key in 0.53 of all items at L1 (0.62 L0, 0.44 L2); inside the Manhattan shape 0.79 (L1),
  inside the max-distance shape 0.81 (L1); with B from L3, "F minus B" 0.56 (L3), 0.44 (L5) inside Manhattan. Cause: with only L/R
  turns the walker rarely faces backwards, so distance = number of steps.
- **bytecode_loop: "sum of all arguments"** (ignoring skips) = key in 0.86 (L1, share 0.50), 0.89 (L3, 0.42), 0.82 (L5, 0.38) of the
  sum-of-arguments shape; 0.30-0.44 of all items at every level >= 1. The skip rarely fires.
- merge_two_sorted, partial-output shape: "sorted(a + b) without the last element" 0.50-0.52 (share about 0.33).
- sieve_marking, count shape: "ones at indices 0, 1 and at primes" 0.36-0.48.
- existing lineages: string_build length shape = stop - start exactly (1.00); list_build max shape = m - 1 in 0.36-0.46;
  cond_chain = gcd of the two literals 0.43-0.68; string_methods O7 0.485 at L1 (count shape mostly '0').
Exact closed forms (not shortcuts in the sense of guessing, but they let a reader answer without tracing; PENDING LEAD REVIEW for the
"code tracing" construct): insertion_sort is entirely closed-form (list/element = first K sorted, rest unchanged; shifts = inversion
count of the first K) at 1.00 in every shape; fast_power result = pow(b, e, m) and final base = b^(2^bits) mod m, 1.00; euclid gcd
shape 1.00; kadane best shape = maximum subarray 1.00; bracket_matching all shapes = the standard matcher 1.00.

The author's "oracle" 0.64 (insertion_sort; mine 0.637 at L1, 0.705 at L0): no single literal-position rule explains it (best
cross-validated literal rule 0.154 at L1; best per-shape rule 0.34). It is high because in the element shape the key is by
construction one of the list's literals and small shift counts coincide with literals. The rule that does explain insertion_sort is
the closed form above. Other high oracles (bfs 0.52/0.57, turtle 0.44/0.59, minmax 0.53) are likewise mostly "the key is some
number on the page", not one rule; the best single rules there are 0.23 (bfs O7), 0.53 (turtle, count F) and 0.28 (minmax O7).

## 7. Capacity (own count)

Distinct programs after renaming every identifier (variables, parameters, function names) in first-appearance order: **all 175
cells of the 25 new lineages reach 2,000** (`a04`, up to 30,000 draws per cell). Draws needed: at most 5,659 (recursive_calls L6);
my figures match the author's (e.g. recursive L0 5,638 vs 5,672; fast_power L0 5,260 vs 5,283; circle L0 5,291 vs 5,529). Headroom
is thin where the late new-program rate is low: recursive_calls about 0.25 at every level (one shape, the list fold, is unbounded,
the four others saturate near a few hundred programs, so large distinct pools fill up with list folds), fast_power L0 0.15, circle L0
0.25, sieve L0 0.33, turtle L0 0.39. Existing lineages: nested_pairs saturates at 396 / 704 / 1,100 / 1,584 programs (L0-L3) and
fails 2,000; cond_chain L0-L2 and list_build all levels saturate just above 2,000. Whether 2,000 satisfies the ADR's gate (10 x the
pool demand per cluster and level) depends on G and the chosen level mix: with about 20 C1 lineages per part, 4,000 + 20,000 items
per part and a uniform five-level mix, demand is about 240 per level, so 10 x is about 2,400 (judgement; PENDING LEAD REVIEW).

## 8. Feasibility (judgement, not measured)

Under the current grammar and reading P strict, C1 has 28 (or 22) clusters, about 11-14 per part. Algorithms still expressible
(DFS with an explicit stack, Kahn topological order, O(n^2) Dijkstra, heap sift, linked list by next-array, ring buffer, KMP prefix
function, matrix rotation/spiral, backtracking by recursion, Hanoi, 3-way partition ...) many of which merge into existing clusters
under the strict reading: perhaps +15 to +30 strict clusters, i.e. about 20-28 per part. A grammar extension (dict/set, tuples,
break/continue, split/join/find, ord/chr, bit operators, floats, try/except, classes, closures/global/nonlocal, comprehensions,
lambdas, generators; each needing second-solver work) might add another +15 to +30 overall, about 28-42 per part. Under reading T:
1 (weak T: about 8-12, perhaps +6-10 with extensions). The proposed minimum of 300 per part is out of reach under every reading.
I do not recommend an extension; that is the lead's call.

## 9. Where I differ from the author (manifest read after the hash)

- Existing 14: we agree exactly (9 strict; groups loop/nested/list/string-build, string_methods/slices, func_branch/func_compose).
- New 25: the author delivers 25 (13 clear, 12 borderline) and merges none, implying 34 strict overall; I count 28 strict (22
  maximal). Specific differences:
  - recursive_calls is marked "clear" with no neighbour except the non-recursive functions; it overlaps fib_like (shapes "two",
    "tri"). Not flagged by the author.
  - bytecode_loop is "clear" (neighbour turtle_walk noted); I merge it with turtle_walk under strict.
  - tables, stacks, euclid/cond_chain: the author's "borderline" matches my strict merges.
  - the author groups digit_peel/euclid/fast_power/while_counter, the three swap lineages, and mirror/run_length as borderline; I
    keep them apart even under strict (reasons in section 2); adopting them gives 22.
- Shortcuts: the author's worst single rule is at most 0.211; the battery missed turtle "count F" (0.53 overall, about 0.8 within
  shapes), bytecode "sum of arguments" (about 0.85 within shape), merge "sorted without last" (0.5 within shape), and did not report
  the exact closed forms (insertion_sort entirely; fast_power, euclid, kadane, bracket by shape).
- Keys: agree (3,500 fixtures). The author did not detect the cellular_update `w` collision (4 fixtures).
- Capacity: agree (2,000 per level after renaming in every cell).
- Not addressed by the author: the reading-T question; cross-evaluation duplicates.
- Minor: `check_family`'s docstring says it checks "no node kind the second solver lacks", but the code only counts prints (it
  relies on `c1_trace` raising); the schema says recursion reaches "at most about 12 nested calls", I measured depth 17 in the
  fixtures; NOTES.md says the isolated runs are batched per process, not one fresh process per program (ADR 6.2 table: "in a fresh
  restricted process").

## 10. What must be fixed or decided before registration

1. cellular_update: draw the accumulator name with `names()` or use a name outside `VARS`; regenerate the fixtures (4 affected).
2. Make the suite green: `sorted(set(s))` in `c1_shortcut_check.py:115`.
3. turtle_walk and bytecode_loop: redraw or redesign so that "count F" and "sum of arguments" do not answer most items of their
   shapes (e.g. require a reversal / a fired skip). No threshold is registered; PENDING LEAD REVIEW.
4. The lead's choice of reading for C1 (P or T) and, under P, of the cluster map (strict 28, maximal strict 22, lenient 39), with
   recursive_calls/fib_like resolved (merge, or split the recursive shapes). PENDING LEAD REVIEW.
5. Register the batch in `core.REGISTRY` and `solvers_c1.SOLVERS` so the two-process pool-hash test and pool tests cover it. The
   second solver is implementer-written ("ruling needed 3"); my evaluator is an audit check, not a registered second solver.
6. Capacity against the registered demand (10 x) once G and the level mix are fixed; nested_pairs (existing) fails 2,000 at L0-L3.
7. The closed-form and cross-evaluation findings, for the construct claim and the part-B held-out claim. PENDING LEAD REVIEW.

## 11. My own mistakes and failed attempts (kept)

- `a07_shortcuts.py` (v1) canonicalised only the print statement, so every printed bare variable became `_0` and the shape was lost
  (O1/O7 understated). Kept with its output (`a07_shortcuts_gen1.json`, `a08_table_gen1.md`); v2 (`a07b_shortcuts_v2.py`) canonicalises
  the whole program. Apart from O1/O7 and the R.* rules added in v2 (insertion element-at-index, turtle F+B), rates are unchanged between v1 and v2.
- v2 was first run with system Python 3.15.1, then under uv/3.12.14 (`gen1uv` symlink): all 10,262 numeric fields identical, but the
  diagnostic `O5.chosen`/`O7.chosen` lists differ in the order of tied entries: my `cv_best_rule` iterates `set(score) | set(consts)`
  (hash order). Only those logs are affected, not any rate.
- `a09` and `a10` were first run inline (heredoc); saved as files afterwards and re-run under uv with identical output.
- The `gen1v2/summary.json` symlink and `gen1uv -> gen1` symlink exist only to let the table script find the summary.
