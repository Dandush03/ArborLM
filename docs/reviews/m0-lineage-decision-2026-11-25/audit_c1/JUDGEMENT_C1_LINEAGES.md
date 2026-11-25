# C1 lineage judgement (auditor, written BEFORE reading the author's manifest, shortcut outputs or NOTES)

Auditor: Claude Opus 5.5 (model id claude-opus-5-5, from session metadata). Astra review: NOT_PERFORMED. Not human approval.
Audited worktree: .claude/worktrees/agent-a0c9d741ea96ce52f, HEAD 1b33b7b2 (C1 batch = commit 44b22f7e).
Evidence read: generator source of all 39 lineages; 3 rendered items per level per lineage (819 programs,
`a01_render.py`, seed 20261125, output `a01_render_out.txt`).

Exposure disclosure (before this file was written): a `grep` of `fixtures/C1_BATCH1_SCHEMA.md` printed its 25 lineage
headings, which carry the author's "strict confidence: clear/borderline" labels; and while reading generators I read module
docstrings that say (tables) "a lead may judge them one 'tabulation' cluster, see the manifest log", (functions)
"func_branch and func_compose are non-recursive calls", (swaps) "the existing bubble_pass is the adjacent-swap pass".
I did not read the manifest, the shortcut outputs or NOTES*.md.

## The rule (ADR-0033 section 6.2, quoted)

"Each rule shape is registered with a lineage: the hand-written base rule, a distinct solution procedure, from which it
derives. Shapes made mechanically from one base rule (by changing parameters, order, negation, names or surface frame)
share a lineage. **The cluster, for G and for every bootstrap, is the lineage.** G is the number of lineages per part."

What ADR-0033 says about C1 (section 6.2 table): "Output prediction. Small deterministic Python programs from a typed
grammar: arithmetic, strings, lists, loops, conditionals, small functions. No imports, no input, bounded loops. Each prints
exactly one line. The question is that line" and "The program is run in the locked interpreter, twice, in a fresh
restricted process with a time limit." Section 6.3: "C1 measures reading and tracing code. It does not measure writing it."
Nothing in ADR-0033 says what the "solution procedure" of a C1 item is.

Ambiguous sentence: "the hand-written base rule, a distinct solution procedure". For C1 it can mean
(P) the algorithm the program implements, or (T) the procedure the solver uses, which for every C1 item is the same act:
trace the statements in order, keeping a table of variable values.

## What each reading does to the count (judgement)

- Reading T (the act of tracing is the procedure): every C1 item has the same solution procedure. G = 1 for C1 as a whole;
  the family partition into parts A and B then separates no procedures, and a registered minimum of 300 per part is
  unreachable by any number of generators. A weaker form of T (procedure = the set of language constructs a tracer must
  handle: counted loops, while loops, string ops, non-recursive calls, recursion, list mutation, aliasing, 2-D indexing,
  dispatch chains) gives roughly 8 to 10 clusters for all 39 lineages. Judgement, not measured.
- Reading P (the program's algorithm is the procedure; the lead's STRICT ruling: number system, constraint mix, final
  question, names, order, negation, surface frame are parameters): counts below.

## Procedures, one line each (reading P)

Existing 14 (core.REGISTRY):
- loop_sum: counted loop over an arithmetic range; a modular predicate on the index gates adding c*i (else a constant) to an int accumulator.
- while_counter: three bundled procedures: count iterations of x = a*x + b until a threshold; Collatz step count; repeated subtraction until below a threshold.
- string_build: counted loop; the index's residue class picks a letter appended to a string accumulator; print string, its length or its reverse.
- string_methods: evaluate a left-to-right chain of string operations (upper, lower, replace, slice, reverse, concatenate, repeat) on a literal; print text, length or a count.
- func_branch: evaluate a piecewise (two- or three-branch) function at 2-3 literal arguments and add/subtract the results.
- func_compose: evaluate a composition g(x) = f(f(x)) +- c of affine functions, optionally reduced mod m.
- list_build: append f(i) mod m (f affine or square) for i in range(n); print list, sum or max.
- counter_list: histogram: counts[x % k] += 1 over a literal list.
- nested_pairs: double counted loop over a rectangle; a predicate on (i, j) gates adding 1 or i + j.
- bubble_pass: P left-to-right adjacent compare-and-swap passes.
- cond_chain: k iterations of a subtractive-Euclid-like two-variable update (a > b: a -= b; equal: a *= 2; else b -= a), optional halving at level >= 3.
- minmax_track: running max/min with its index over a literal list.
- slices: evaluate two slice expressions (start/stop/step, negatives) on a literal string or list and concatenate, or sum one.
- fib_like: two-term recurrence t = a + b (optionally mod m), rotated n times.

New 25 (lineages_c1_<family>.py, registry BATCH1):
- euclid_gcd: Euclid remainder form (a, b) -> (b, a % b) to b = 0; print gcd, sum of quotients or sum of remainders.
- digit_peel: base-b digit extraction (d = n % b, n //= b) folded into an accumulator (sum, reversed number, count >= t, even-digit sum).
- fast_power: modular exponentiation by squaring; print result, final base, or sum of base values per round.
- sieve_marking: sieve marking pass on a literal 0/1 flag list with start i*i, 2i or 3i; print live count, live-index sum or strike count.
- binary_search: closed or half-open binary search; print probe-value sum, last probe index or l/r/h path string.
- merge_two_sorted: two-pointer merge loop until one list runs out; print comparisons, partial output list or source switches.
- insertion_sort: K outer rounds of insertion sort (shift larger/smaller prefix elements right); print list, shift count or one element.
- partition_pass: Lomuto partition around a pivot; print the list or the sum of swap positions.
- kadane_scan: cur = max(cur + x, x), best = max(best, cur); print best, final cur or sum of cur values.
- majority_vote_scan: Boyer-Moore candidate/counter scan; print candidate, "candidate count" or number of candidate takes.
- run_length_scan: run-length encoding by comparing each char with the current run; print full encoding, runs >= 2 only, or the lengths.
- mirror_pointers: i, j walk inward comparing s[i], s[j]; collect left chars, left indices or both chars of unequal pairs.
- recursive_calls: evaluate a recursive definition: two-term or three-term linear recurrence, halving split, list fold by parity, or mutual recursion.
- bracket_matching: array stack with pointer for two bracket kinds; print 10*errors + height, height, or first error index.
- postfix_evaluation: reverse Polish evaluation on an array stack with randomly assigned operator codes; print final top or sum of written results.
- coin_change_table: 1-D coin table: combinations (coin-outer), ordered sequences (amount-outer) or fewest coins; print an entry or table sum.
- string_pair_table: 2-D flat table of LCS or edit distance; print corner cell, last row or table sum.
- grid_path_table: 1-D rolling row of a right/down grid DP: max path sum, min path sum, or path count with blocked cells.
- bfs_queue: BFS with array queue, head/tail pointers and dist array; print a distance, enqueue order, sum of dequeued distances or last enqueued node.
- union_find_links: parent array, find loop, link rule (first-under-second, second-under-first, larger-under-smaller); print a root, the array or root sum.
- circle_elimination: Josephus counting of K live flags around a ring, striking each landing; print last struck, sum struck or survivor.
- cellular_update: synchronous 1-D ring CA with an 8-entry rule table for G generations; print row or sum of i*cell.
- turtle_walk: command string F/L/R/B updating (x, y, heading mod 4); print Manhattan distance, "x,y" or max distance.
- bytecode_loop: accumulator VM: pc fetches (opcode, arg) pairs; add/mul/sub/skip-if/mod/store/load; print acc, sum of executed args or reg.
- shared_lists: object identity under alias, copy, concat, append, setidx and two helper functions (mutate vs rebind); print list/sum/len/element.

## Pairwise sameness over 741 pairs (reading P)

All 741 pairs were considered by grouping on procedure skeleton (data structure + per-step state update). Pairs not listed
below are distinct under both readings: their per-step state updates differ in kind, not by a listed parameter.

### Tier A: same procedure under both strict and lenient reading
None found. No two lineages implement the same named algorithm with only parameter changes.

### Tier B: merged under the STRICT reading only (with the reason)
- B1 {loop_sum, string_build, list_build, nested_pairs}: one skeleton, "iterate an index range, evaluate a predicate or
  expression of the index, fold into an accumulator". Int vs string accumulator = number system; predicate choice =
  constraint mix; print len/rev/sum/max = final question. nested_pairs adds a second loop over a rectangle (weakest member;
  strict keeps it in because the per-iteration rule is the same predicate-gated fold). 4 -> 1.
- B2 {func_branch, func_compose}: "substitute literal arguments into small non-recursive function bodies and evaluate";
  piecewise vs composed bodies = constraint mix. 2 -> 1.
- B3 {slices, string_methods}: "evaluate a chain of sequence operations on a literal"; string_methods already contains
  slice and reverse operations; list vs string = number system. 2 -> 1.
- B4 {coin_change_table, string_pair_table, grid_path_table}: "fill a DP table cell by cell from earlier cells with
  min/max/+"; grid path-count (best[j] += best[j-1]) and coin combinations (ways[a] += ways[a-c]) have the same update
  form; grid max-path and LCS share cell = max(up, left) + local. Which recurrence = constraint mix under the strict
  ruling. 3 -> 1.
- B5 {euclid_gcd (new), cond_chain (existing)}: Euclid's algorithm in division form vs a fixed-count subtractive form of
  the same two-variable reduction. Near the edge: cond_chain's equal-case doubling and halving are not Euclid.
- B6 {recursive_calls (new), fib_like (existing)}: shapes "two" (and "tri") of recursive_calls are the linear recurrence
  fib_like iterates (with a = b = 1, c = 0 it is Fibonacci). Partial overlap: 3 of 5 recursive shapes are other procedures.
- B7 {bytecode_loop, turtle_walk}: "read a command sequence, dispatch on the command, update a small fixed state";
  arithmetic accumulator vs position/heading = surface frame.
- B8 {bracket_matching, postfix_evaluation}: "scan tokens with an array stack and pointer; push on one token class, pop
  and act on another". Matching vs evaluating = final question / constraint mix.

### Near-misses kept apart under both readings (reasons)
- kadane_scan vs minmax_track: kadane adds the best-ending-here recurrence; the tracer must keep a second derived state.
- majority_vote_scan vs run_length_scan: both keep (value, count); cancel-on-mismatch vs close-and-emit-run are different updates.
- insertion_sort vs bubble_pass (and partition_pass): different traversal schedules; partial-round states differ.
- digit_peel vs fast_power: same peel skeleton on e (e % 2, e // 2) but fast_power carries a squared base chain mod m.
- digit_peel vs euclid_gcd: both % and // in a while loop; different state update.
- postfix_evaluation vs bytecode_loop: both dispatch on random opcode numbers; stack discipline vs accumulator/pc-skip.
- sieve_marking vs circle_elimination: both strike flags; arithmetic-progression strikes vs counting live flags around a ring.
- counter_list vs list_build: indirect bucket indexing vs direct append.
- mirror_pointers vs merge_two_sorted vs binary_search: three different two-index schedules (converge by 1, advance one, halve).
- bfs_queue vs union_find_links: queue frontier vs parent-pointer chasing.
- cellular_update vs list_build: neighbourhood rule-table lookup vs index expression.
- cond_chain vs fib_like: both rotate two variables a fixed number of times; branching subtract vs add.
- while_counter vs digit_peel / euclid_gcd: different loop bodies (affine growth, Collatz, repeated subtraction).

Within-lineage heterogeneity (under-counting, not over-counting): while_counter bundles 3 procedures; recursive_calls 5;
string_pair_table 2 (LCS, edit distance); coin_change_table 2 (counting, fewest); grid_path_table 2 (best path, path count).
These do not inflate G, but they make a lineage's cluster less homogeneous and create the cross-lineage overlap in B6.

## Counts (reading P)

| set | lenient | strict |
|---|---|---|
| existing 14 | 14 | 9 (B1 -3, B2 -1, B3 -1) |
| new 25, among themselves | 25 | 21 (B4 -2, B7 -1, B8 -1) |
| new clusters not merging into an existing one | 25 | 19 (B5, B6 merge into existing) |
| overall 39 | 39 | 28 |

Reading T: 1 overall (weak form: about 8-10). Reading P lenient 39; P strict 28.
