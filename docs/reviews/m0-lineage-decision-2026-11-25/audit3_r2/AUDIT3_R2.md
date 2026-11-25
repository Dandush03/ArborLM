# M0 R2 lineage audit 3 (re-audit of the R2 set after fix round e11ce14d)

- Auditor: arbor-auditor, model claude-opus-5-5 (Opus 5.5), from session metadata. Independent engineering and mathematical evidence; NOT Astra validation and NOT human approval.
- Astra review: NOT_PERFORMED
- Audited: worktree `.claude/worktrees/agent-a0c9d741ea96ce52f`, branch `claude/m0-impl`, HEAD `f122e6bcac5f4d641c54b00a9277e9130b01e970`. Read only; no git state changed.
- LOCATION DEVIATION: the session's write hook refused every write into the audited worktree ("belongs to a different worktree") and into the base checkout. All scripts and this report are therefore in `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1/experiments/_scratch/m0_audit3_r2_20261125/` (git-ignored). Before I learned this, `mkdir -p` (Bash) created two EMPTY directories that are left in place: `<audited worktree>/docs/reviews/m0-lineage-decision-2026-11-25/audit3_r2/` and `/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_audit3_r2_20261125/`. The lead must copy the files into `audit3_r2/` if wanted.
- Independence disclosure: I did NOT open `studies/m0/NOTES_LINEAGE_REPAIR.md`. Before measuring I DID read the author's `FIXES` dispositions in `studies/m0/r2_rev2_build.py` and the `defect_and_fix` fields of `manifests/r2_rev2_manifest.json` (they quote residual rates), and the author's `canon()` in `r2_rev2_measure.py`. My solvers, heuristics and capacity code import nothing from the author's measurement, summary or `*_analysis` code; they import generators only (`core`, `lineages_r2*`).

## Environment and commands

Apple arm64, uv 0.12.15, `uv run --locked --offline python` = Python 3.12.14 (generators), `python3 -I` = 3.15.1 (summaries). Run from the audited worktree with `PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:<scratch>`. Seeds are my own string seeds `random.Random(f"a3r2|<lineage>|<level>|k")`, k in {1, 2, 5, 6}, plus `a3r2-cap|…|7` and `a3r2-render|…|3`; none is a registered study seed.

| Script | Command | Output |
|---|---|---|
| a3_set.py | `python a3_set.py` | a3_set.out (current set, my clusters, map count) |
| a3_solvers.py, a3_check.py | `python a3_check.py 400 1`; again with PYTHONHASHSEED=12345; `python a3_check.py 2000 2` | a3_check_attempt1.out, a3_check_2000_k2.out |
| a3_heur.py, a3_shortcuts.py, a3_summ.py | `python a3_shortcuts.py 2000 a3_shortcuts_2000.json`; `python3 -I a3_summ.py a3_shortcuts_2000.json 0.2` | a3_shortcuts_2000.json, a3_summ_020.out |
| a3_extra.py, a3_extra2.py | `python a3_extra.py 2000`; `python a3_extra2.py 2000` | a3_extra.out, a3_extra2.out |
| a3_capacity.py, a3_cap_summ.py, a3_cap_tight.py | `python a3_capacity.py 40000 8000 a3_capacity.json`; `python3 -I a3_cap_summ.py a3_capacity.json 18` (and 19); `python3 -I a3_cap_tight.py a3_capacity.json` | a3_cap_g18.out, a3_cap_g19.out, a3_cap_tight.out |
| list_other_evals.py, a3_render.py | as named | list_other_evals.out, a3_render.out |
| tests | `PYTHONDONTWRITEBYTECODE=1 uv run --locked pytest tests/test_m0_*.py -q` (once) | pytest_m0.out |

## 1. Current set, correctness, determinism

Current set (from the registries): 16 core R2 lineages with `to_base` → `to_base_wide` and `string_rewrite` → `string_rewrite_nonidentity`; 8 unchanged batch-1 lineages (binary_search_trace, bst_traversal, cellular_automaton, dictionary_rank, hamming_error_position, interval_scheduling, luhn_check, min_heap_ops); 17 rev2 shapes; `deferred_acceptance_partner` excluded = **41 lineages/shapes**.

- Keys: my independent solvers (stdlib, mostly different methods: shunting-yard, minimax on two piles, Prim, brute-force LPS/LCS/CRT/max-block, repeated multiplication, Stein gcd, parallel toppling, recursive BST split, bracket pair deletion, exhaustive merge for n ≤ 7) agree on **114,800 of 114,800** items (400 per lineage and level) and **574,000 of 574,000** (2,000 per lineage and level). 0 errors.
- Determinism: identical generation hash `5a9bf5d5…4417` under PYTHONHASHSEED 0 and 12345 in separate processes; `58907c4c…3172` for the 2,000 run.
- Wording: one rendered item per lineage at L0 and L3 read (a3_render.out). Conventions are stated in every lineage I read. expression_eval: the old readings now disagree with the stated key on 6–42 % (LTR, parentheses) and 12–33 % (ranked, "+ before −") of items, so the new explicit wording matters. No new ambiguity found. Not done: an alternative-reading key test for every lineage.

## 2. Clusters

My strict map: 4 merges (sort_list+kth_smallest, count_letter+count_divisible, to_base_wide+from_base, permutation_power+modular_power), giving **37 clusters**. `lineages_r2_clusters.py` gives **38**, but only because its 42 ids still include deferred_acceptance_partner. I found no disagreement on any merge.

PENDING LEAD REVIEW: the sister maps use a stricter grain for the same algorithms. C1 B8 merges bracket_matching with postfix_evaluation, C1 B4 merges the coin table with the LCS table, C1 B7 merges command-dispatch programs, C1 B1 merges folds, and C1 digit_peel holds both digit-sum and base-digit shapes. Applied to R2, that grain gives bracket_match+stack_machine(+list_ops), coin_change_min+lcs_length, grid_sum into the count cluster, and digit_root into the base cluster: **about 32 clusters**.

Cross-evaluation duplicates (R-7). Strong: interval_scheduling = R1.activity_selection; cheapest_network = R1.mst_cost_r4 (same grouped-towns construction); subtraction_game ~ R1.nim_xor_r4 (now an XOR of two piles); list_ops = R1.containers_queue_line; sort/kth ~ M1.median_list_r2; coin_change_min (now counts ways) = M1.change_ways_r2 and C1.coin_change_table (new duplicates created by the fix); crt = M1.crt_congruence_r2; prime_factor_query = M1.prime_factors_r2; gcd_euclid = M1.gcd_lcm_r2 and C1.euclid_gcd; permutation/modular_power = M1.power_remainder_r2 and C1.fast_power_r2; lcs = C1.string_pair_table; max_subarray = C1.kadane_scan; binary_search_trace = C1.binary_search; bracket_match and stack_machine = C1 B8; cellular_automaton = C1.cellular_update_r2; run_length = C1.run_length_scan; to/from_base = C1.digit_peel. That is 18 of 37 clusters. Weak: digit_root ~ C1.digit_peel, palindrome_check ~ C1.mirror_pointers, count_divisible ~ C1.counter_list, multiples_between ~ M1.division_counting_r2, stack_machine ~ R1.containers_stack_piles.

## 3. Shortcuts

Accuracy per level, L0..L6, on 2,000 test items, with the mode learned on a separate draw. For open answers chance = 0. For yes/no the two-sided effect is |acc − 0.5|. A "(P)" rule is a valid alternative procedure or a full solve under a misreading; I report it but do not call it a cue.

- Residuals from the prior round, confirmed: bracket match "last same-kind closer" 0.51 0.50 0.41 0.40 0.40 0.31 0.32; next same-kind 0.37–0.45; second 0.35–0.42. cache misses "other policy" (P) 0.42–0.60. subtraction "residues xor" 0.50–0.59. hash slot "home + same-home" 0.40–0.57. lcs greedy 0.46 0.36 0.25 0.19 0.15 0.12 0.08. expression "ignore the stated rule": ranked 0.40–0.79, LTR 0.32–0.73.
- New tells, several created by the fix constructions:
  - hash_probe probes: block-start rule 0.95–0.98; `len(keys) − home` 0.86–0.94. Slot: `max(home, min home + insertion index)` 0.73–0.83.
  - cache_eviction present (FIFO): "among the last cap distinct requests" 0.88–0.91 (two-sided +0.38 to +0.41); "in the last cap requests" 0.85–0.86. Batch 1 had 0.60–0.64.
  - max_subarray_sum: "best window of 7" and "two long runs + the dip" are **1.00 at every level**. The planted +++−+++ template is the answer.
  - cheapest_network: "triangles minus their dearest + the (g−1) cheapest dear cables" 1.00 1.00 1.00 0.74 0.75 0.76 0.58.
  - gcd_euclid gcd: "smallest common prime factor" 1.00 1.00 1.00 0.94 0.92 0.90 0.90 (g is prime by construction at L0–L2).
  - chip_toppling: a closed form (Dirichlet Green's function with the conservation final row) is right on 0.98–1.00 for both remaining shapes. That is the same reason the fix gave for dropping `final` and `lost`.
  - subtraction_game: "each pile's own win/lose status equal → no" 0.79–0.82 (+0.29 to +0.32). No leak through the move set (≤ 0.54).
  - bracket_match valid: "check only top-level pairs" 0.79–0.84 (+0.29 to +0.34); 58–69 % of the "no" items have a mismatched top-level pair.
- Existing 16 (not measured in the fix round):
  - palindrome_check: "at most one odd letter count" 0.96 at every level (+0.46).
  - count_letter: "words containing the letter" 0.69–0.88; mode 0.59 at L0, 0.40 at L1.
  - count_divisible: "ignore > t" 0.65–0.74; mode 0.47 at L0.
  - stack_machine: "last pushed value" 0.41–0.59. It is exact on the 31–45 % of items that end with a push.
  - permutation_power: "the start" 0.29–0.52; "one application" 0.30–0.53; "t even → start, t odd → one step" 0.41–0.71.
  - multiples_between: round((b−a+1)/m) 0.75–0.77; b//m − a//m 0.87–0.89.
  - digit_root: n mod 9 (P) 1.00.
- Smaller: coin "1" 0.12–0.25; binary_search third "1/8–7/8 position" 0.21–0.32; LIS greedy 0.07–0.29; Fermat 0.17–0.32.
- R-1 is **not** met. Redraws conditional on a heuristic remain in shapes the fix did not touch:
  - fitted 0.8: interval_scheduling (earliest-start and shortest-first) and binary_search_trace (third = target);
  - deterministic exclusion: bst_traversal and min_heap_ops (insertion or sorted order), cellular_automaton (final = start), dictionary_rank (one redraw on rank 1 or n!).
  - Borderline: gcd_euclid |p−q| ≥ 2. Key balancing in subtraction_game is on the key, not on a heuristic.

## 4. Capacity

Demand: 10 × (ceil(24,000/G) + 100) for core levels and 1,000 for reserve levels. With DA excluded there are 37 clusters, so the parts are 18 and 19 and the worst case is **G = 18 → 14,340**. The code and manifest use G = 19 (13,640) because they still count DA. The formula matches ADR §6.2/§8 under the worst case of a one-level range; the tuning term of +100 per cluster is conservative. Different reading, PENDING LEAD REVIEW: under §6.5 the reserve levels can enter the chosen range, and then they carry the core demand.

- Reading A (proper names relabelled, order-free where the answer ignores order): **no failing cluster-level**, at 40,000 draws for core levels and 8,000 for reserve levels.
- Reading B (letters and labels also relabelled) fails dictionary_rank L0 46, L1 46, L2–L3 238, L4–L5 1,436, and run_length L0 54 and L1 1,280. permutation_power fails alone but passes inside its cluster.
- Reading C (only the order of values matters) also fails bst_traversal L0 275, L1 1,895, L2 13,349 and min_heap_ops L0 169, L1 1,310, L2 9,420.
- Under the reserve-at-core-demand reading, prime_factor_query L0 (Chao1 about 4,000), run_length L0 (about 4,100) and stack_machine L0 (about 10,300) would fail. Everything else at L0/L6 is unverified, because 8,000 draws cannot show 14,340.
- The manifest's capacity section covers only the 26 batch-1 ids (including DA), not the 16 core lineages or the two new shape ids.

## 5. Verdicts

The bound on shortcuts is the lead's and is not registered. Where I write "fix" for a cue, it applies only if the bound is below the measured value. For R-1 violations and closed forms the verdict follows the rule.

| Lineage | Verdict |
|---|---|
| sort_list, kth_smallest, to_base_wide, from_base, caesar_shift, grid_sum, list_ops, string_rewrite_nonidentity, hamming_error_position, luhn_check, merge_smallest_cost, modular_power, lis_length, longest_palindromic_substring, prime_factor_query, crt_smallest, coin_change_min | REGISTRABLE AS IS on my checks (coin, crt, prime, gcd-cluster: cross-evaluation duplicates PENDING) |
| run_length, dictionary_rank | AS IS under reading A; NEEDS FIX (capacity) under reading B. dictionary_rank also NEEDS FIX (R-1 redraw) |
| digit_root | AS IS; mod-9 formula PENDING LEAD REVIEW |
| bst_traversal, min_heap_ops, cellular_automaton, binary_search_trace, interval_scheduling | NEEDS FIX: remove the heuristic-conditional redraws (R-1) |
| hash_probe, cache_eviction, max_subarray_sum, cheapest_network, gcd_euclid, bracket_match, subtraction_game | NEEDS FIX: tells by construction (section 3) |
| palindrome_check, count_letter, count_divisible, stack_machine, permutation_power, multiples_between, expression_eval, lcs_length | NEEDS FIX if the bound is below the values in section 3 |
| chip_toppling | SHOULD NOT BE REGISTERED under the fix round's own closed-form criterion (PENDING LEAD REVIEW) |
| deferred_acceptance_partner | Not in the set; still counted in the map (38), in G = 19, in the fixtures and in revised_shapes |

Resulting count: 37 strict clusters if every fix lands (about 32 at the C1/M1 grain). Clusters with no lineage needing a fix today: 17. With chip_toppling withdrawn: 36.

## 6. Slips and my own mistakes

- Code and records: DA is not excluded everywhere (above). `manifests/cross_evaluation_procedures.json` (R-7) does not exist at HEAD. The lineage id `coin_change_min` now asks for the number of ways. The author's `canon()` keeps dictionary_rank's letters as distinct.
- Mine, all kept in the outputs:
  - Attempt-1 coverage artefacts: list_ops "ignore X" scored items without X (0.20–0.69; restricted, 0.00–0.17); string_rewrite L0, min_heap removals=0 and count_divisible "≥ t" coincide with the solver; interval "latest start first" (1.00) is a valid mirror greedy; prime "≤ √n" is trial division itself.
  - My LTR old-reading heuristic crashed on negative intermediate values (57–391 items per level); it was redone in a3_extra.py.
  - The location deviation and the two empty directories (header).

## 7. Not verified

- The second solvers from a separate context (they do not exist).
- Sealed-pool disjointness.
- The reserve-at-core-demand capacity, except as listed.
- Isomorphism-exact graph counts (I used an invariant, which gives a lower bound).
- Alternative-reading key changes beyond expression_eval and merge_smallest_cost.
- Wording of every level (I read L0 and L3 only).
- Whether a closed form or a valid alternative procedure counts as a shortcut (PENDING LEAD REVIEW).
- Tests: `522 passed, 2 xfailed, 1 warning in 791.40s`.
