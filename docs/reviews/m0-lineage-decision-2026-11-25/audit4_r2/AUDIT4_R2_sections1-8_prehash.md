# M0 R2 lineage audit 4 (final audit of the R2 set after fix round 3)

- Auditor: arbor-auditor, Claude Opus 5.5 (model id claude-opus-5-5, from session metadata). Independent engineering and mathematical evidence. Not Astra validation, not human approval.
- Astra review: NOT_PERFORMED
- Audited: worktree `.claude/worktrees/agent-a0c9d741ea96ce52f`, branch `claude/m0-impl`, HEAD `f19d08c810d63821e2a76efa5b81ea67839302f3` (read only; `git status` showed the same two pre-existing untracked `.bak` files before and after my test run; no git state changed by me).
- Nothing here is registered, nothing fixed. The shortcut bound is not registered; every verdict that depends on it says so. Scientific choices are marked PENDING LEAD REVIEW.
- Independence: sections 1-8 were written before I opened `studies/m0/NOTES_FIX3_R2.md`, the manifests' prose or the summaries in `r2_fix3_build.py`. I did read, before measuring: the builders (`lineages_r2_fix3*.py` with their docstrings, which describe each fix and quote some of the implementer's rates), `r2_fix3_set.py`, `r2_fix3_clusters.py` (including its `CROSS_EVAL` notes), the interface of `r2_fix3_heuristics.py` and `r2_fix3_battery.py`, the first 30 lines of `r2_fix3_capacity.py` (the module docstring says G = 17 "as briefed"), the numeric keys of the three JSON manifests (`G_used`, `cluster_count`, `demand_per_cluster_level`, `failing`), and the tests. The brief itself quoted the implementer's headline rates. Section 9 (comparison) was written after the hash of sections 1-8 was taken.

## Environment and commands

Apple arm64, uv 0.12.15. Generators: `uv run --locked --offline python` = Python 3.12.14, cwd = audited worktree, `PYTHONPATH=.:<deliver>`, `PYTHONDONTWRITEBYTECODE=1`. Summaries: `python3 -I` = 3.15.1 from `deliver/`. `<deliver>` = `/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_audit4_r2_20261125/deliver` (reached through the session worktree's `experiments` symlink, which points there). Seeds are throwaway string seeds `a4r2|<id>|<level>|k` (k = 1, 2, 5, 6), `a4r2-cap|…|7`, `a4r2-render|…`, `a4r2-word|…`; none is a registered study seed.

| Script | Command | Output |
|---|---|---|
| a4_render.py | `PYTHONHASHSEED=0 … python a4_render.py` | a4_render.out (FAILED attempt 1: PYTHONPATH missing), a4_render_attempt2.out |
| a4_solvers.py, a4_check.py | `PYTHONHASHSEED=0 … python a4_check.py 400 1`; same with `PYTHONHASHSEED=12345`; `PYTHONHASHSEED=0 … a4_check.py 1000 2` | a4_check_400_k1_h0.out, a4_check_400_k1_h12345.out, a4_check_1000_k2_h0.out |
| a4_heur.py, a4_shortcuts.py | `PYTHONHASHSEED=0 … python a4_shortcuts.py 2000 a4_shortcuts_2000.json` (smoke runs at N = 100 first: run 1 crashed on a syntax error in a4_heur.py, run 2 = ../a4_sc_smoke2.json) | a4_shortcuts_2000.json |
| a4_summ.py, a4_summ2.py | `python3 -I a4_summ.py a4_shortcuts_2000.json 0.10`; `python3 -I a4_summ2.py a4_shortcuts_2000.json` (v1, then v2 after reclassifying two of my rules) | a4_summ_2000_raw_attempt1.out, a4_summ2_2000.out, a4_summ2_2000_v2.out |
| a4_capacity.py, a4_cap_summ.py, a4_bounds.py | `… python a4_capacity.py 100000 a4_capacity_100k.json`; `python3 -I a4_cap_summ.py a4_capacity_100k.json 18` (and 17); a4_bounds.py run from deliver/ via `python3 -I -c "exec(...)"` | a4_cap_g18.out, a4_cap_g17.out, a4_bounds.out |
| a4_wording.py | `PYTHONPATH=. … python a4_wording.py 2000` | a4_wording.out |
| tests | `PYTHONDONTWRITEBYTECODE=1 uv run --locked pytest tests/test_m0_r2_*.py -q -p no:cacheprovider` (once) | pytest_r2.out: **221 passed, 1 warning in 36.79 s** |

## 1. The candidate set and the two exclusions

`r2_fix3_set.fix3_set()` returns **40 lineages**: 24 fix-round-3 shapes (`lineages_r2_fix3*.py`, registry `FIX3`, 24 `SUPERSEDES` entries) + 7 unchanged core R2 + 7 unchanged rev2 + 2 unchanged batch-1 (hamming, luhn). `chip_toppling` and `deferred_acceptance_partner` are not in the set, not in `r2_fix3_clusters.clusters()` (36 clusters, 40 ids), not in `r2_fix3_capacity.json` `per_lineage` (40 ids), and have no file in `fixtures/r2_fix3/` (24 files). `core.REGISTRY` was not touched by this round. Residue: their old fixture files remain in `fixtures/r2_batch1/` and `fixtures/r2_batch1_rev2/` (kept on file, as policy requires); `r2_batch1_rev2/` has no marker saying chip_toppling and deferred acceptance are NOT REGISTERED, and the 16 unchanged lineages' fixtures are spread over older directories (no single fixture index for the set). Records, not a key defect.

G: 36 clusters → parts 18/18 → G = 18 → demand 14,350. The implementer's code and manifest use **G = 17 → 15,130** ("as briefed"): stricter than my map requires, so not an error, but the manifest's `G_used` does not follow from its own `cluster_count`.

## 2. Keys, determinism, wording

- My solvers (`a4_solvers.py`) read **only the question text** (regex parsing; stdlib; nothing from `studies.m0`). Different methods where practical: literal "rounds" for interval scheduling, bracket matching by deleting adjacent pairs, BST level order by depth then value, BFS for coins, top-down LCS, patience LIS, O(n²) subarray sums, brute-force palindromic substring, Stein gcd, two-queue Huffman, Prim, brute force for dictionary rank when ≤ 40,000 words, repeated multiplication for powers, manual scan for string rewriting.
- **0 mismatches, 0 errors on 112,000 items** (400 per lineage and level, k = 1) and **280,000 items** (1,000 per lineage and level, k = 2). Generation hash `b47bc4a7…f650eb` identical under PYTHONHASHSEED 0 and 12345 (separate processes); `eacffa64…fd43c` for the k = 2 run. Parsing the text also confirms that every structured field the key uses is stated in the question.
- Wording (one item per shape at L0 and L6 read, a4_render_attempt2.out): conventions are stated in every rebuilt lineage I read (touching meetings, tie by smaller number, floor midpoint, zero edge, loaded-vs-requested order, both ends counted, prime repeats counted).
  - **New ambiguity, count_divisible (R-4):** "the sum of the numbers in this list that are divisible by m and greater than t" does not say whether a repeated value counts once or every time. Lists are drawn with replacement; the set-of-values reading changes the key on **0.27-0.38 of items** at every level (a4_wording.out). The old count shape had the same gap; the sum makes it bite. Needs one clause ("each entry counts, repeats included").
  - Not ambiguities but untested conventions: luhn "start at the rightmost" — every number is odd in length, so doubling from the left gives the same key on 100 % of items; stack_machine "second from top minus top" agrees with the reversed reading on 38-62 %, and ignoring `swap` agrees on 72-92 %.

## 3. Redraws and rejections (R-1, R-13), every builder's loops read

| Lineage | Loop / Retry | Conditioned on | Reading |
|---|---|---|---|
| subtraction_game | `until(800, make, ok)` until `(xor != 0) == (want == "yes")` | **the answer value** | Rejection sampling on the key. Allowed by the implementer and its test as "balancing on the key"; it is conditional on the answer value, which the brief lists as banned. PENDING LEAD REVIEW; under the brief's wording NEEDS FIX (construct the yes/no positions, e.g. set the last pile's position value). |
| palindrome_check | `Retry` if the swapped text is still a palindrome | **the answer value** (a wanted "no" that came out "yes") | Rare (equal letters or mirror positions); could be removed by construction (pick j with a different letter, not the mirror of i). Minor. |
| gcd_euclid | `Retry` if gcd(p,q) ≠ 1 (validity) **or |p−q| < 2** | |p−q| = 1 is exactly when one Euclid step (a mod b) returns g | A deterministic exclusion keyed to a heuristic's outcome (audit 3 called it borderline). Minor. |
| string_rewrite_nonidentity (unchanged) | `Retry` if a rule is an identity, or the string becomes empty | the final/intermediate string | Validity plus one answer-value exclusion (empty answer). Minor. |
| cellular_automaton | `Retry` if the table is constant | — | Dead code: the mirror constraint makes a constant table impossible. |
| bracket_match, cheapest_network, coin_change_min (`Retry` if < 10 payable amounts; `while True` on smallest coin ≤ 6), crt_smallest | validity / structure | not the answer, not a heuristic | Fine. |
| count_letter | `while w in words` | word distinctness | Fine. |
| all other 30 builders | none | — | Fine. No fitted probability anywhere. |

So the claim "24 rebuilt with no redraws" holds for heuristic-conditioned redraws except the borderline gcd exclusion; it does not hold for answer-conditioned rejection (subtraction_game, palindrome_check).

## 4. Shortcuts (2,000 test items per lineage and level, mode learned on a separate 2,000, two-sided)

Batteries: mine (a4_heur.py, 162 rules), audit 3's (a3_heur.py, read-only from the review folder), the implementer's (`r2_fix3_heuristics.OWN`). Open answers: effect = accuracy (chance 0, a rule's "does not apply" counted wrong; `[cond]` rules use accuracy where they apply). Yes/no: |acc − 0.5|. Max over levels and shapes. Every rule is put in one class (a4_summ2.py, the whole table is in the script): **cue**; **partial** (a truncated procedure: checks a subset of what the procedure checks); **construct** (a fixed reduction valid only because of a construction regularity); **P** (valid alternative or full solve under a misreading; not counted); **artifact** (equals the procedure on items lacking the feature; not counted).

Distribution over the 40 lineages (max effect):

| Classes counted | ≤ 0.10 | (0.10, 0.15] | (0.15, 0.25] | > 0.25 |
|---|---|---|---|---|
| cues only | 18 | 6 | 4 | 12 |
| cues + partial | 15 | 7 | 4 | 14 |
| cues + partial + construct | 15 | 6 | 4 | 15 |

Per lineage, cue max (level of max) [partial / construct where higher]:
- **> 0.25:** gcd_euclid **0.91** (L0; 0.62 at L6), merge_smallest_cost 0.72 (L0; 0.28 L1/L4), kth_smallest 0.58 (L0; 0.28 L6), max_subarray_sum **0.46** (L0-L2; 0.29 L6), lis_length 0.38, modular_power 0.38, cache_eviction **0.37** (contents shape), coin_change_min **0.32**, bst_traversal 0.31 (L0, pre; 0.20 L1), count_letter **0.31**, palindrome_check **0.29** [partial 0.46], lcs_length **0.27** (L0; 0.09 L6).
- **(0.15, 0.25]:** stack_machine 0.22 (L0; 0.14 L6), bracket_match 0.19, longest_palindromic_substring 0.17 (mode) [partial 0.54], hash_probe 0.154 (L0 checksum).
- **(0.10, 0.15]:** interval_scheduling 0.147, digit_root 0.12 (mode; n mod 9 = P 1.00), luhn_check 0.11 [partial 0.12], crt_smallest 0.11, permutation_power 0.11 [**construct 1.00**], hamming_error_position 0.103 [partial 0.22].
- **≤ 0.10:** binary_search_trace 0.08, expression_eval 0.08, subtraction_game 0.08 [partial 0.13; P parity bit 0.31], grid_sum 0.07, prime_factor_query 0.07 [partial 0.74], cheapest_network 0.06, caesar 0.05, cellular 0.05, dictionary_rank 0.05, to_base_wide 0.04, count_divisible 0.03, from_base 0.02, string_rewrite 0.02, list_ops 0.01 [partial 0.14], multiples_between 0.01 (definition rule 1.00, see below), min_heap 0.00 (Floyd = P 0.25), run_length 0, sort_list 0.

**New cheap rules, several created by the rebuilds:**
1. **gcd_euclid — "gcd from the common powers of 2, 3, 5, 7 only": 0.91 0.86 0.78 0.73 0.67 0.67 0.62 (gcd), 0.90-0.62 (lcm).** Created by the fix: g is drawn among NON-squarefree numbers 8..60+30L, which are mostly 7-smooth (20 of the 22 at L0), and gcd(p,q) = 1 means the small-prime part of gcd(a,b) is exactly g.
2. **max_subarray_sum — "cut the row at any two adjacent negatives, trim, take the best segment's total": 0.46 0.46 0.46 0.36 0.38 0.38 0.29.** Created by the phase construction: rising phases never contain two adjacent negatives, falling phases almost always do, so the best block is one visible phase.
3. **count_letter — "words containing the letter, plus 1": 0.31 0.29 0.25 0.22 0.20 0.18 0.16.** Created by planting exactly one double: when no other word holds the letter twice (likely when the per-item chance is 0.15-0.3), the total is that count + 1.
4. **permutation_power — "apply the mapping t mod (n−1) times": 1.00 at L0 and L6, 0.38-0.51 at L1-L5.** a must be coprime to n; at n = 12 (L0) and n = 18 (L6) only a = 1 qualifies, so the start's cycle always has n − 1 elements and the visible fixed point tells it. Under label relabelling the lineage has only **61 (L0) to 666 distinct items** per level (section 6).
5. **cache_eviction (FIFO contents) — "the last cap distinct names, in order of first appearance": 0.37 0.31 0.27 0.22 0.18 0.15 0.14** (the 0.65 hit rate keeps the cache equal to the recent distinct requests).
6. **coin_change_min — "largest coin k, k−1 or k−2 times, greedy for the rest" on all five amounts: 0.30 0.30 0.32 0.19 0.16 0.16 0.16** (the implementer's own greedy and ceil rules are ≤ 0.11).
7. **palindrome_check** — partial checks of the outer k letter pairs: k = 3 0.18-0.24, k = 5 0.26-0.35, k = 8 0.37-0.46; "the two halves have the same letters" 0.26-0.29. A swap of two letters is a local defect, so a check of a share f of the pairs reads about 0.5 + f/2 — the same structure for which the implementer dropped bracket_match `valid`.
8. lcs_length greedy from both ends 0.27 (L0); bst "root, then the smaller ones, then the larger ones, in insertion order" 0.31 (L0 pre) / 0.20 (L1); stack_machine "last operation on the last two pushed values" 0.22 (L0); hash_probe checksum "slots filled contiguously from the lowest home" (implementer's) 0.15 (L0).

Also: hash_probe `checksum` does not depend on the insertion order at all (the occupied set of linear probing is order-independent; inserting in reverse or home order is right on 100 %), so that shape tests the occupancy sweep, not the order-dependent probing. PENDING LEAD REVIEW whether that is the procedure.

**The implementer's exclusions:**
- (P) rules: legitimate where the rule is a full solve (Kruskal, factorisation, Euler/Carmichael reduction, any-order occupancy, n mod 9, misread tie/touching rules in interval scheduling, LRU contents with load order, no wrap-around which needs the full simulation). The subtraction_game "parity of the sum of position values" (0.31) is a near-full solve (all Grundy values computed) — I accept the (P) label. Whether n mod 9 (digit_root) and exponent reduction (modular_power) are the lineage's procedure is PENDING LEAD REVIEW, as in audit 3.
- The constant-guess rule: kept by me as a cue (digit_root 0.12, longest palindrome 0.17, luhn 0.11 are mode rules near 1/9-1/6 chance); none is above 0.17.
- **"Rule is the definition" (multiples_between): not legitimate as an exclusion.** With both ends multiples, (b − a)/m + 1 answers 100 % with no floor division, which was the lineage's distinctive step; the sum is the arithmetic series of the same count. The cue is not a shortcut around the procedure — the procedure itself has collapsed into a fencepost subtraction. NEEDS FIX or a lead ruling that the fencepost count is the procedure (PENDING LEAD REVIEW).
- list_ops "0.67 is an artifact": **confirmed**. audit 3's "ignore reverses/moves" equal the procedure on items without that step; restricted to items that contain it, ignoring reverses reads 0.10-0.14 (partial), ignoring moves ≤ 0.10, "append at the front" 0.01.

**The six untouched lineages above 0.25 (implementer's readings in brackets):** longest_palindromic_substring odd centres only 0.51-0.54, even only 0.46-0.49 [0.53: confirmed; it is a half procedure]; kth_smallest "list value nearest to min + (max−min)(k−1)/(n−1)" **0.58** at L0, 0.28 at L6 [0.34: mine is higher]; lis_length "ascents + 1" **0.38** [0.31: higher]; merge_smallest_cost "pairwise rounds in sorted order" **0.72** at L0 (n = 5), "sorted chain" 0.33 [0.31: higher]; modular_power "a^(e mod 10) mod m" **0.38**, Fermat misuse 0.31 [0.30: higher]; list_ops artifact [confirmed]; digit_root n mod 9 (P) 1.00 [confirmed].

## 5. Did a rebuild change what the lineage tests? Clusters and cross-evaluation

| Rebuilt lineage | New question | Same cluster identity? | Still requires the algorithm? |
|---|---|---|---|
| interval_scheduling | chosen meetings (list) | yes | yes |
| binary_search_trace | looked-at values / their sum | yes | yes |
| bst_traversal, min_heap_ops | larger n | yes | yes |
| cellular_automaton | row, more steps, ends 1 | yes | yes |
| dictionary_rank | partial words from a larger alphabet | yes (mixed radix) | yes |
| run_length | more runs | yes | yes |
| hash_probe | whole table / occupied-slot sum | yes | table yes; **checksum: only the occupied set (order-free)** |
| cache_eviction | evicted list / FIFO contents | yes | yes (contents has a cue, 0.37) |
| bracket_match | match_all / first_error | yes (stack matching) | yes |
| expression_eval | planted misreadings | yes | yes |
| subtraction_game | four piles | yes (Sprague-Grundy); the XOR step is now R1.nim_xor's | yes |
| cheapest_network | grid points | yes (MST) | yes |
| max_subarray_sum | phases | yes | **no on 29-46 % (segment rule)** |
| coin_change_min | fewest coins for five amounts | yes; restored to *fewest*, which is C1.coin_change_table_f3's fewest shape | yes (cue 0.32) |
| lcs_length | longer strings | yes | yes |
| gcd_euclid | non-squarefree g | yes | **no on 62-91 % (small-prime factorisation)** |
| multiples_between | both ends multiples | nominally | **no: floor counting collapsed to (b−a)/m + 1** |
| count_letter | planted double | yes | mostly (cue 0.31) |
| count_divisible | SUM of the qualifying entries | yes (fold with a predicate; still merges with count_letter) | yes |
| palindrome_check | two letters swapped | yes | partial checks 0.46 |
| stack_machine | final step arithmetic | yes | yes |
| permutation_power | one long cycle | nominally | **no at L0/L6 (t mod (n−1))**; tiny label-free space |
| prime_factor_query | L0 widened | yes | yes |

My strict map: the same 4 merges as audit 3 (sort_list+kth_smallest, count_letter+count_divisible, to_base_wide+from_base, permutation_power+modular_power) → **36 clusters (implementer: 36)**. No rebuild moved a lineage across clusters. Borderline groups (not merged) as in `r2_fix3_clusters.BORDERLINE_GROUPS`; at the C1/M1 grain about 32.

Clusters whose algorithm also appears in another evaluation's current fix-3 map (strong unless noted): interval_scheduling — R1.activity_selection_r5; cheapest_network — R1.mst_cost_r4; subtraction_game — R1.nim_xor_r5 (XOR step; Grundy part not); list_ops — R1.containers_queue_line_r5 (medium), C1 B3 (medium); sort/kth — M1.median_list; coin_change_min — C1 B4 coin_change_table_f3 (fewest shape), M1.S5 change_ways; lcs_length — C1 B4 string_pair_table; crt_smallest — M1.crt_congruence; prime_factor_query — M1.prime_factors; gcd_euclid — M1.gcd_lcm, C1 B5 euclid_gcd_traced_f3; permutation/modular_power — M1.last_digit_power, C1.fast_power_f3 (variant, medium); binary_search_trace — C1.binary_search_f3; bracket_match — C1 B8 bracket_matching_f3; stack_machine — C1 B8 postfix_evaluation (and R1.containers_stack_piles, weak); cellular_automaton — C1.cellular_update_f3; run_length — C1.run_length_scan; to/from_base — C1.digit_peel_f3; palindrome_check — C1.mirror_pointers (the same two-pointer comparison); string_rewrite — C1 B3 string_methods_f3 (medium); expression_eval — C1 B8 postfix (medium). **19 of 36 clusters** (21 with the mediums), unchanged from audit 3's 18 except: max_subarray_sum no longer duplicates C1 (kadane_scan is NOT REGISTERED there), palindrome_check upgraded to strong. Weak: count cluster — C1 B1 / counter_list_f3; multiples_between — M1.division_counting; digit_root, longest palindrome — C1.digit_peel / mirror_pointers; cache_eviction — R1 queue. No merge or drop on this account (R-7); the held-out question is the human lead's.

## 6. Capacity (100,000 draws per lineage and level; my map)

Readings: (a) names, setting and presentation order relabelled (graphs by a weighted WL hash = lower bound); (b) also letters/labels (letters by first appearance, bracket kinds, the numbers of a mapping → cycle type + start's cycle + t, dictionary letters by index; count_letter by the multiset of (word length, letter count), which is coarser than relabelling and closer to R-16's third reading); (c) also only the order of values where the path depends only on order (sort, kth, BST, heap, LIS, binary search, interval endpoints, hash homes).

At **G = 18 (14,350)** and at **G = 17 (15,130)**: reading (a) **0 failing cluster-levels**; reading (b) **0 failing**, but **count_letter (36-190 distinct per level) and permutation_power (61-666) pass only through their cluster partners**; reading (c) **8 failing: binary_search_trace L0-L6 (288-672 distinct: n × target position) and sort_list L0 (48 alone; kth carries L1-L3)**. The implementer's "passes on two readings at 15,130" is reproduced for (a) and (b), with the partner dependence above.

At the smaller G that the bounds below imply, the demand rises (G = 7: 35,300; G = 6: 41,010) and cellular_automaton L0 (Chao1 ≈ 32,900), to_base_wide L0 (D 29,454 of 100,000 draws, unresolved), dictionary_rank L0 (Chao1 ≈ 31,600, reading b) and string_rewrite L0 (Chao1 ≈ 30,600, reading b) become failures or unresolved (a4_bounds.out).

## 7. Tests

`221 passed, 1 warning (torch: numpy missing)`. Genuineness:
- `R2_FIX3_TEST_OLD=1` does switch `SET` to `current_set()` (the pre-round shapes), so the property tests do target the old shapes. Not run by me (brief: run only the one command); several tests would fail on old shapes through a missing key (`ask`) rather than the property, which is weaker failing-first evidence.
- The static redraw test **exempts subtraction_game's `until()` by name** and lists palindrome_check and gcd_euclid as "validity" retries (section 3); it checks source strings only.
- Thresholds are loose (0.2-0.35) and miss every new rule in section 4: gcd tests only `a mod b`; count_letter tests only "words containing" (0.0 by construction — near-tautological); permutation tests start / one step / t mod n, not t mod (n−1); palindrome tests the odd-count rule (0.5 by construction); max_subarray tests window-7 and two-runs only.
- Second solvers (`test_m0_r2_fix3_keys.py`): written on the structured form, no generator import; several use different methods (BFS coins, all-subarray sums, permutation enumeration for dictionary rank, Prim, OrderedDict cache, recursive search); some are near copies of the generator (cellular, hash, stack, permutation). Same author and context, structured-only (do not test that the text states what the key uses), 60 items per level (12 for dictionary_rank). Genuine checks; not independent in the R-9 sense.

## 8. Verdicts (bound not registered; x = the measured cue maximum)

| Verdict | Lineages |
|---|---|
| REGISTRABLE AS IS (16) | binary_search_trace (fails capacity reading c), caesar_shift, cellular_automaton, cheapest_network, dictionary_rank, expression_eval, from_base, grid_sum, hamming_error_position (cue 0.103 = the 10 % no-flip constant; partial 0.22), list_ops (partial 0.14), min_heap_ops, prime_factor_query (partial "scan to 61" 0.74: PENDING), run_length, sort_list (fails reading c at L0), string_rewrite_nonidentity, to_base_wide |
| ONLY IF BOUND ≥ x (16) | crt 0.11, luhn 0.11 (0.12 with partial), digit_root 0.12 (and n mod 9 accepted as its procedure, PENDING), interval 0.15, hash_probe 0.16, longest_palindromic_substring 0.17 (0.54 with partial), bracket_match 0.19, stack_machine 0.22, lcs 0.27, bst 0.31, coin_change_min 0.32, cache_eviction 0.37, lis 0.38, modular_power 0.38, kth 0.58, merge_smallest_cost 0.72 |
| NEEDS FIX (8) | gcd_euclid (0.91, created by the fix), max_subarray_sum (0.46, created), count_letter (0.31, created), permutation_power (t mod (n−1) 1.00 at L0/L6; 61-666 label-free items), palindrome_check (partial checks 0.46, cues 0.29; answer-conditioned Retry), multiples_between (procedure collapsed), subtraction_game (answer-value redraw, PENDING LEAD REVIEW), count_divisible (wording: repeats, 27-38 % key change) |
| SHOULD NOT BE REGISTERED | none on my evidence; multiples_between if the lead rules that the fencepost count is not the lineage's procedure |

16 + 16 + 8 = 40.

Cluster count with the NEEDS FIX lineages out (count cluster kept through count_divisible, assuming its one-clause wording fix): **cues only: 15 at 0.10, 20 at 0.15, 24 at 0.25; with partial procedures counted: 13, 18, 22** (a4_bounds.out; G = 7/10/12 and 6/9/11). If every NEEDS FIX lands cleanly and reads within the bound, at most 5 more clusters return (gcd, max_subarray, palindrome, multiples, subtraction; permutation_power's cluster then rests on modular_power at 0.38), i.e. up to 20/25/29 (cues only).

Not verified: sealed-pool disjointness; isomorphism-exact graph counts (WL lower bound); exact (not sampled) capacity spaces; wording at levels other than L0 and L6; alternative-reading key changes beyond count_divisible, luhn and stack_machine; the `R2_FIX3_TEST_OLD=1` run; any model behaviour (no model was run).
