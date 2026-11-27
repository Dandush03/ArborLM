# M0 R2 lineage audit 1 (ADR-0033 revision 4, R2 batch 1 plus the 16 existing R2 lineages)

- Auditor model: claude-opus-5-5 (Opus 5.5), from session metadata.
- Astra review: NOT_PERFORMED. This is independent engineering and mathematical evidence. It is not Astra validation and it is not human approval.
- Audited: worktree `.claude/worktrees/agent-a0c9d741ea96ce52f`, branch `claude/m0-impl`, HEAD `1b33b7b2d1e75765b56c90bffb08286471852d85`. The R2 batch is commit `e83df603`. Read only. `git status` in that worktree was clean at the end.
- Own judgement written and hashed before the manifest was read: `judgement_before_manifest.json`, SHA-256 `260734b96a2f6c00d902149a14f608a619282668f818fecd966cb2fc855037fa` (written 2026-11-25 14:31 UTC). Section 8 is the only part written after reading `studies/m0/manifests/r2_batch1_manifest.json` and the NOTES.
- Exposure disclosure: I read the generators with docstrings and comments stripped (`strip_src.py`). One comment survived in the source text I saw later, in `cache_eviction` (`# does "in the last cap requests" give the right answer?`). I read the author's `r2_shortcut_check.py` (allowed) for the heuristic definitions. `R2_BATCH1_SCHEMA.md` was only grepped for similarity words; it contains none.

## Environment and commands

Apple M5 Max (arm64), uv 0.12.15. Generator runs: `uv run --locked --offline python` (Python 3.12.14) from the audited worktree with `PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PYTHONPATH=.`. Stdlib-only checkers ran under system `python3 -I` (3.15.1). Note: `-I` ignores `PYTHONDONTWRITEBYTECODE`, so a `__pycache__` was created inside this scratch directory only. Nothing was deleted. Scripts, all in this directory, each starting with `# ruff: noqa`:

| Script | Command (D = this directory, W = audited worktree) | Output |
|---|---|---|
| strip_src.py | `python3 strip_src.py W/studies/m0/lineages_r2*.py` | read on screen |
| render_samples.py | `uv run ... python D/render_samples.py --full` (seed 777123) | render_samples.out (3 items per level for all 42 lineages, one full question per lineage) |
| list_other_evals.py, show_full.py | `uv run ... python D/list_other_evals.py 230`; `show_full.py 3 <ids>` | list_other_evals.out (R1 15+49, C1 14+25, M1 16+21 lineages) |
| solvers.py + check_fixtures.py | `python3 -I D/check_fixtures.py W/studies/m0/fixtures/r2_batch1` | check_fixtures_attempt1.out |
| heuristics.py + audit_run.py | `uv run ... python D/audit_run.py D/audit_main.json 5000 1000` (seed 2025112501; a 60-item smoke run → audit_smoke.json) | audit_main.json, audit_main.log |
| summarise.py | `python3 -I D/summarise.py D/audit_main.json {solver,capacity,shortcuts}` | shortcuts_summary.out |
| ambiguity_fixtures.py | `python3 -I D/ambiguity_fixtures.py W/studies/m0/fixtures/r2_batch1` | ambiguity_fixtures.out |
| cache_split.py | `uv run ... python D/cache_split.py` (seed 2025112502) | cache_split.out |
| write_judgement.py | `python3 -I D/write_judgement.py D/judgement_before_manifest.json` | the judgement file and its .sha256 |

The seeds above are the auditor's own. None of them is a registered seed.

## 1. Procedure per lineage (generator read; samples rendered for every level)

Existing 16 (`lineages_r2.py`):
- count_letter: scan the words and count one letter.
- count_divisible: scan a list and count the items that pass a predicate (divisible by m and greater than t).
- sort_list: sort ascending or descending.
- kth_smallest: sort ascending and read off position k.
- list_ops: apply deque edits (reverse, drop first or last, append, move first to end).
- to_base: repeated division by b; the remainders are the digits.
- from_base: positional (Horner) evaluation.
- string_rewrite: apply global, left-to-right, non-overlapping replacement rules one after another.
- caesar_shift: shift each letter by k modulo 26.
- run_length: replace each maximal run by letter + count.
- palindrome_check: compare with the reverse.
- grid_sum: add up one row, column or the main diagonal.
- permutation_power: iterate a mapping t times (or reduce t modulo the cycle length).
- stack_machine: simulate push/pop/dup/swap/add/sub/mul and read the top.
- multiples_between: floor-division count of multiples of m in [a, b].
- digit_root: repeated digit sum.

New 26:
- lcs_length: 2-D LCS table.
- coin_change_min: unbounded minimum-coin DP.
- lis_length: longest strictly increasing subsequence.
- max_subarray_sum: Kadane.
- gcd_euclid: Euclid's algorithm (gcd, lcm or step count).
- modular_power: a^e mod m.
- crt_smallest: smallest x satisfying 2 or 3 congruences.
- prime_factor_query: trial division (largest prime, or the sum with multiplicity).
- subtraction_game: win/lose backward induction over pile sizes.
- binary_search_trace: floor-midpoint binary search on 1-based positions.
- longest_palindromic_substring: centre expansion.
- dictionary_rank: Lehmer / factorial-base rank and unrank.
- bst_traversal: BST insertion, then pre-, post- or level-order.
- min_heap_ops: sift-up insert and sift-down pop on a heap array.
- cache_eviction: LRU or FIFO simulation (misses, or membership at the end).
- hash_probe: linear probing (slot, or number of probes).
- bracket_match: stack matching (validity, or partner position).
- expression_eval: infix evaluation under usual precedence or strict left-to-right.
- interval_scheduling: earliest-finish greedy.
- merge_smallest_cost: Huffman.
- cheapest_network: MST.
- deferred_acceptance_partner: proposer-proposing Gale-Shapley.
- cellular_automaton: synchronous 3-neighbour rule table with a zero boundary.
- chip_toppling: 1-D abelian sandpile with sinks at both ends.
- luhn_check: Luhn (validity, or check digit).
- hamming_error_position: Hamming syndrome.

## 2. Sameness over all 861 pairs (the full table with a reason per pair is in the judgement file)

Rule quoted (ADR-0033 section 6.2, first bullet): "Each rule shape is registered with a lineage: the hand-written base rule, a distinct solution procedure, from which it derives. Shapes made mechanically from one base rule (by changing parameters, order, negation, names or surface frame) share a lineage. **The cluster, for G and for every bootstrap, is the lineage.**" The lead's ruling adds number system, constraint mix and final question as parameters.

Merged under both readings:
- sort_list + kth_smallest. The procedure is the same (sort). Only the final question differs.

Merged under the strict reading, kept apart under the lenient one. The ambiguous phrase is "a distinct solution procedure" against the parameter list.
- count_letter + count_divisible: a linear scan with a predicate counter. Is the predicate a parameter ("constraint mix") or part of the procedure?
- to_base + from_base: inverse directions of positional conversion. "Number system" and "final question" are parameters, and the batch itself puts the inverse pair rank/unrank in one lineage (dictionary_rank). The lenient reading keeps them apart because division and Horner are different update rules.
- permutation_power + modular_power: both iterate a map from a start t times, and both are fastest by reducing t modulo the cycle length. The lenient reading keeps them apart because the map is not in the parameter list and square-and-multiply applies only to modular_power.

Near misses kept apart under both readings: count_divisible / multiples_between (list scan against a floor formula); count_* / grid_sum; palindrome_check / longest_palindromic_substring (an outer search over centres); dictionary_rank / to_base and from_base (the Lehmer step); coin_change_min / subtraction_game (same 1-D table over amounts with a move set, but a different cell rule); lcs / lis; lis / max_subarray; cheapest_network / interval_scheduling (sort then accept-if-compatible); merge_smallest_cost / min_heap_ops; binary_search / bst; cellular_automaton / chip_toppling; luhn / hamming; crt / gcd; gcd / prime_factor; bracket / stack_machine; expression / stack_machine; bracket / expression; cache / list_ops; digit_root / luhn; modular_power / to_base; caesar / permutation_power.

Distinct-cluster counts:

| | strict | lenient |
|---|---|---|
| existing 16 | 13 | 15 |
| new 26 | 26 | 26 |
| overall 42 | 38 | 41 |

(Section 8 records two further merges that the author's own rejection rules imply. Under those rules: new 24, overall 36.)

## 3. Cross-evaluation duplicates (finding for the lead; not merged; section 6.2 does not address them) — PENDING LEAD REVIEW

Strong (same algorithm, same kind of question):
- R2.interval_scheduling = R1.activity_selection.
- R2.cheapest_network = R1.mst_cost.
- R2.deferred_acceptance_partner = R1.stable_matching and R1.stable_matching_r2.
- R2.crt_smallest = M1.crt_congruence.
- R2.prime_factor_query = M1.prime_factors.
- R2.gcd_euclid = C1.euclid_gcd (traced) and M1.gcd_lcm.
- R2.modular_power = C1.fast_power (traced) and M1.last_digit_power.
- R2.lcs_length = C1.string_pair_table (traces an LCS table).
- R2.coin_change_min = C1.coin_change_table (traces the min-coin and ways DP) and M1.min_cost_packs.
- R2.max_subarray_sum = C1.kadane_scan.
- R2.binary_search_trace = C1.binary_search.
- R2.bracket_match = C1.bracket_matching.
- R2.cellular_automaton = C1.cellular_update (C1 uses a periodic boundary).
- R2.run_length = C1.run_length_scan.
- R2.stack_machine = C1.postfix_evaluation.
- R2.list_ops = R1.containers_queue_line.

Weaker (same paradigm or a sub-step):
- subtraction_game ~ R1.nim_xor and R1.minimax_tree.
- coin_change_min ~ M1.change_ways.
- digit_root and to_base ~ C1.digit_peel.
- palindrome_check ~ C1.mirror_pointers.
- sort_list ~ C1.bubble_pass and C1.insertion_sort.
- kth_smallest ~ M1.median_list.
- multiples_between ~ M1.division_counting.
- count_divisible ~ C1.counter_list.
- stack_machine ~ R1.containers_stack_piles.

## 4. Quality of the 26 new lineages

- Keys:
  - My question-only solvers agree on 3,640 of 3,640 fixture items (26 × 140), with no disagreement and no error, on the first attempt (check_fixtures_attempt1.out).
  - They also agree on 182,000 of 182,000 freshly drawn items (26 × 7 levels × 1,000).
  - Several solvers deliberately use a different method from the generator: round-based simultaneous proposals; parallel, right-to-left toppling; DP for interval scheduling; Prim; exhaustive search for merging when n ≤ 7; brute force for CRT, LPS, max block and rank; BFS for coins.
  - Fixture SHA-256 values match the manifest (0 mismatches).
  - Coverage: every fixture item of every lineage. Nothing was left uncovered.
- Stated conventions that I checked and found clear:
  - binary search midpoint: floor. 0-based and 1-based floor give identical traces (100% on 5,000 per level), so they are not an ambiguity.
  - Positions are 1-based where asked (bracket, hamming).
  - BST direction, heap sift rules, LRU/FIFO wording, linear-probe wrap and counting, CA neighbour order and boundary, chip order-independence, Luhn parity (the check-digit wording handles the shift), and the Hamming parity rule are all stated.
  - Python heapq gives identical heaps on 100% of 35,000 items.
- Ambiguous items, with fixture ids in ambiguity_fixtures.out:
  - expression_eval, left_to_right shape. The wording does not say whether the left-to-right rule also applies inside parentheses. 24 of 65 LTR fixture items change key if usual precedence is used inside: fixture/0/11, 0/12, 0/16, 1/6, 1/8, 1/19, 2/5, 2/7, 2/9, 2/14, 2/16, 2/17, 2/18, 3/0, 3/3, 3/5, 3/6, 3/12, 4/3, 5/6, 5/7, 5/13, 5/15, 5/16.
  - expression_eval, ranked shape. "Operators of the same kind are done from left to right" can be read as "same symbol". 15 of 75 ranked fixture items change key if + is done before −: 2/6, 2/8, 3/14, 4/1, 4/5, 4/6, 4/7, 4/9, 4/11, 5/0, 5/1, 6/0, 6/6, 6/9, 6/19.
  - merge_smallest_cost. The wording never says that *any* two piles may be joined. Under the classic adjacent-piles reading, 101 of 140 fixture items change key (the full list is in the output file).
- Leakage from surface form:
  - bracket_match, match shape: the most frequent answer is the last position, 0.39 at L0 falling to 0.18 at L6.
  - chip_toppling, final shape: always all ones with at most one 0 (section 5).
- Existing 16 (not in scope for item-level checks):
  - string_rewrite draws identity rules ("replace every 'c' with 'c'", rendered L1.0 and L4.1).

## 5. Shortcuts

Method: 5,000 items per lineage and level (all 7 levels). Each heuristic is scored as exact-match accuracy with a Wilson 95% interval, shown next to the most-frequent-answer rate. Yes/no answers are read two-sided: raw accuracy is reported, and a value below 0.5 is an overshoot. All of the author's heuristics were re-coded, plus at least 5 of my own per lineage. Per-level numbers are in shortcuts_summary.out.

- chip_toppling:
  - lost shape: chips − (n − 1) is right on 0.82–0.90 per level.
  - final shape: the conservation formula (ones, with a 0 at (n(n+1)/2 − Σ i·cᵢ) mod (n+1)) is right on 0.97–1.00.
  - Two of the three shapes do not need the simulation.
- bracket_match:
  - valid shape: "no adjacent wrong-kind pair" is right on 0.84–0.87, against 0.5. The author's heuristics (counts, ends) sit at 0.49–0.52.
  - match shape: excluding the next same-kind closer overshoots. "Second same-kind closer" is right on 0.58–0.76, and the mode (last position) on 0.18–0.39.
- coin_change_min: ceil(amount/largest) + 1 is right on 0.55–0.69. This overshoots from rejecting ceil(amount/largest).
- hash_probe:
  - slot shape: home + number of earlier same-home keys 0.67–0.79; home + 1 0.56–0.68.
  - probes shape: the constant "2" 0.38–0.51.
  - Overshoot from drawing 80% displaced targets.
- cache_eviction, present shape: none of these is near 0.5.
  - The author's "item among the last cap requests" is 0.60–0.64, every CI above 0.5. Split by policy it is LRU 0.75 and FIFO 0.50 (cache_split.out). The cause is `agree = r.random() < 0.5 or (policy == "lru" and not want_yes)`.
  - "Requested in the second half" 0.62–0.67; "is the last request" 0.61–0.62.
- subtraction_game:
  - The author's n mod (largest + 1) has raw accuracy 0.39–0.41, an overshoot; inverted it gives 0.59–0.61.
  - n mod (smallest + largest) 0.55–0.60.
  - n mod Σ moves 0.54–0.57.
- deferred_acceptance_partner:
  - "Own second choice" 0.44–0.61, against chance 1/n of 0.17–0.33 (overshoot from excluding the first choice).
  - Responder-optimal partner 0.62–0.76.
- cheapest_network: "cheapest per town minus the cheapest cable" 0.71 at L0 and 0.49–0.51 at L1–2; "n−1 cheapest + 1 step" 0.55 at L0.
- max_subarray_sum: best run of non-negative numbers 0.36–0.59.
- gcd_euclid:
  - gcd shape: product of the common primes 2, 3, 5, 7 gives 0.60–0.86. That is partial factorisation, not Euclid.
  - steps shape: the constant "3" 0.27–0.38.
- merge_smallest_cost, L0: ascending chain 0.735; sum·⌈log₂ n⌉ 0.39.
- modular_power: a² mod m 0.42 at L0 (0.17–0.29 elsewhere). Fermat reduction 0.46–0.69 (a valid method only for prime m).
- lcs_length and lis_length: the author's flag is confirmed. Most-frequent-answer rates are 0.21–0.30 (LCS) and 0.29–0.32 (LIS). Also overlap − 2 0.27–0.35, and round(2√n) − 2 0.28–0.41.
- Others:
  - longest_palindromic_substring: mode 0.29 at L0.
  - prime_factor_query, largest shape: a constant "largest pool prime" 0.17–0.21.
  - Nothing of note in bst_traversal, min_heap_ops, binary_search_trace, dictionary_rank, hamming, luhn, crt or cellular_automaton.

My own mistakes in the heuristic list. These rows are reported but are not shortcuts:
- LPS "capped at 7" uses the true answer and is invalid.
- Luhn "total ends in 0 or 5" (0.94) needs the full Luhn total, so it is a loosened version of the rule.
- interval "fewest clashes first" (0.98–0.99) is an alternative greedy procedure, not a cheap cue.
- The deferred-acceptance "top half" row also needs the preference tables.

## 6. Capacity (thresholds 1,800 core and 1,000 reserve, as given in the brief)

Method: 5,000 draws per lineage and level, counting distinct structured forms with names relabelled by first appearance.

- All 26 new lineages pass at every level on ordered structured forms.
- merge_smallest_cost L0 has 3,498 ordered forms but only **488** order-free ones. The answer depends only on the multiset.
- Existing to_base L0: **755** (< 1,000). That is the exact space: 151 values × 5 bases.
- Tight but passing: deferred_acceptance_partner L1 has 1,820 up to renaming people (≥ 1,800); crt L0 1,212 and L1 2,215; subtraction_game L0 1,319 and L1 2,316; prime_factor L0 1,431; coin L0 1,456; modular_power L0 1,579.
- Whether presentation order makes an item distinct is PENDING LEAD REVIEW. The manifest notes that the registered gate counts distinct question texts.

## 7. Feasibility (JUDGEMENT, not measured)

- With the present material: 38 strict lineages over 23 family names (note that `numtheory` is used both by the existing and by the new lineages), about 19 per part.
- If the strong cross-evaluation duplicates were removed (the lead's call): about 24, roughly 12 per part.
- With further authoring under the strict reading, I judge about 25–45 strict lineages per part reachable for R2.
- The proposed 300 per part is not reachable under the strict reading.

## 8. Differences from the author's manifest (read after the hash)

- Existing 16. The author gives 12–14 strict procedures; I give 13 (strict) and 15 (lenient).
  - The author treats list_ops + stack_machine as one procedure on the strictest reading. I keep them apart, because the op sets and the data structure differ.
  - The author always merges count_letter + count_divisible. I merge them only under the strict reading.
- permutation_power / modular_power. The author's note calls them distinct, but the author's own rejection log says "Collatz / digit-sum iteration / cycle detection ... same strict procedure as the existing permutation_power and digit_root". That rule would merge digit_root with permutation_power (the author counts them separately) and would cover modular_power too. This is internally inconsistent.
- The author's rejection rules imply further merges that the delivered set does not apply:
  - "edit distance = LCS with a different cell rule" and "subset sum / ways / stair paths = coin_change_min (capacity table)". Under these, subtraction_game is a capacity table with a boolean cell rule, the same as coin_change_min. I had this as a near miss.
  - "factorial base conversion = a shape of the base-conversion lineages". Under this, dictionary_rank (whose own procedure text is "factorial-base ranking or unranking") is a shape of to_base/from_base. I had this as a near miss.
  - Applying both gives new 24 and overall 36. I report this as the strictest count consistent with the author's own log. The choice is PENDING LEAD REVIEW.
- Cross-evaluation.
  - The author rejected Dijkstra, Josephus and queue/stack piles as "already R1 pilot lineages ... not repeated", yet delivered interval_scheduling, cheapest_network and deferred_acceptance_partner, which duplicate R1.activity_selection, R1.mst_cost and R1.stable_matching.
  - The cheapest_network note compares only with R1.graph_shortest_route and misses R1.mst_cost.
  - By the author's own rule "Nim, minimax ... same strict procedure as subtraction_game", R1.nim_xor and R1.minimax_tree are R2.subtraction_game's lineage.
  - None of the C1 or M1 duplicates in section 3 is mentioned.
- Shortcut flags.
  - The author flags only lcs and lis. Where we measured the same heuristic, the author's numbers agree with mine:
    - cache "last cap requests" 0.645 at L4, mine 0.636;
    - subtraction 0.617 two-sided at L0, mine 0.598;
    - bracket "equal counts" 0.545 at L5, mine 0.525;
    - coin greedy 0.22, mine 0.19–0.21;
    - hash "one slot" 0.228, mine 0.19–0.22.
  - The author's screen misses every strong shortcut listed in section 5.
  - The brief's description of cache_eviction and subtraction_game as "balanced near 0.5" is not supported by the manifest (0.645 and 0.617) or by my measurements. No R2 note in `studies/m0/NOTES*.md` makes that claim.
  - The subtraction game result is an overshoot. Bracket validity is balanced only for the author's two heuristics.
- Capacity. The author records every level as passing on text and on structured forms. My numbers agree for the ordered forms. The differences are merge_smallest_cost L0 order-free (488) and existing to_base L0 (755), which is outside the batch's record.
- Ambiguity. The manifest records no wording ambiguity. I found three (section 4).
- My own reversal while drafting: I first had count_divisible / multiples_between as a strict merge, then moved it to a near miss before hashing. The hashed file has the near miss.

## What must be fixed before registration (engineering; the scientific choices are PENDING LEAD REVIEW)

1. Wording:
   - expression_eval LTR: say that the left-to-right rule applies inside parentheses too.
   - expression_eval ranked: say "addition and subtraction together, from left to right".
   - merge_smallest_cost: say "any two piles, not only neighbours".
2. chip_toppling: the lost and final shapes are solvable by closed form. Drop them, or change the rule (for example a threshold > 2, or a sink at one end only) and re-screen.
3. Repair the overshoots (bracket match / adjacent mismatch, coin ceil+1, hash home+1 and "2", subtraction mod, deferred second choice, cache present). Balance a heuristic by drawing its right/wrong share at 0.5 per shape, not by excluding the heuristic's answer. Then re-screen with an auditor's heuristic list as well as the author's.
4. Capacity: decide whether order counts. If it does not, widen merge_smallest_cost L0. Widen existing to_base L0 (755 < 1,000).
5. Existing string_rewrite: reject identity rules.
6. The lead to rule on:
   - the strict/lenient pairs (section 2);
   - the two merges implied by the author's own log (section 8);
   - cross-evaluation duplicates (section 3);
   - the "numtheory" family-name collision before the family partition.
7. Second solvers for the 26 do not exist in the repository yet. My solvers here are audit evidence and are not those. ADR-0033 section 6.2 requires a separate auditor context to audit the solver pair.
