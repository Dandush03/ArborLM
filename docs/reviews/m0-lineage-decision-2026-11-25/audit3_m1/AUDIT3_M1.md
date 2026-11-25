# M0 M1: independent re-audit 3 of the M1 lineage set after its fix round

Auditor: arbor-auditor (Claude Opus 5.5, `claude-opus-5-5`), 2026-11-25. Code audited: implementation worktree `agent-a0c9d741ea96ce52f`, branch `claude/m0-impl`, HEAD `f122e6bc`.
This is independent engineering and mathematical evidence. It is not Astra validation and not human approval. Nothing is registered by it.
`studies/m0/NOTES_LINEAGE_REPAIR.md` and the author's self-assessment were NOT read. The implementer's manifest (`m1_batch1_rev2_manifest.json`) was read only AFTER my own capacity numbers existed, to compare.

Astra review: NOT_PERFORMED

## 0. Where the files are and why

The harness hook refused the Write tool for any path in the implementation worktree ("do not write to other worktrees' files from this session"). I did not route around that refusal with shell writes. The report, scripts and small outputs were therefore written to the scratch directory
`/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_audit3_m1_20261125/` (reached through my own worktree's `experiments` symlink), with a ready-to-copy set in its `deliver/` subfolder. The coordinator copies them into `docs/reviews/m0-lineage-decision-2026-11-25/audit3_m1/`.
Leftover: an EMPTY directory `docs/reviews/m0-lineage-decision-2026-11-25/audit3_m1/` was created in the implementation worktree by my first `mkdir`, before the hook refused the first Write. Nothing else was written there. No git state was touched.

## 1. Environment, seeds and commands

- Machine: macOS (Darwin 27.2.0), Apple silicon. Generators run with `uv run --locked --offline` in the implementation worktree (its `uv.lock`), `PYTHONPATH=<impl worktree>`, `PYTHONHASHSEED=0` unless stated. `check_fixtures_a3.py` and the summarisers use only the standard library and were run with the system `python3` (3.15.1).
- Audit seeds (small throwaway integers, not registered study seeds; passed through `core.stream` with audit labels): 3 (key check), 5 (shortcuts), 7 (capacity), 9 (digit_puzzle extras, failing-first, sample rendering).
- Commands (from the implementation worktree, `W` = its path, `S` = scratch path):
  - `PYTHONHASHSEED=0 PYTHONPATH=$W uv run --locked --offline python $S/common_a3.py > $S/samples.txt`
  - `PYTHONHASHSEED=0 PYTHONPATH=$W uv run --locked --offline python $S/check_keys_a3.py 400 $S/keys_n400_h0.json` (and again with `PYTHONHASHSEED=1` -> `keys_n400_h1.json`)
  - `PYTHONHASHSEED=0 PYTHONPATH=$W uv run --locked --offline python $S/shortcuts_a3.py 1000 $S/short_n1000.json`; `python3 $S/short_summary_a3.py $S/short_n1000.json`
  - `PYTHONHASHSEED=0 PYTHONPATH=$W uv run --locked --offline python $S/capacity_a3.py 30000 $S/cap_M30000.json` (1,507 s CPU); `python3 $S/capacity_clusters_a3.py $S/cap_M30000.json`
  - `PYTHONHASHSEED=0 PYTHONPATH=$W uv run --locked --offline python $S/digit_puzzle_extra_a3.py 1000`
  - `PYTHONHASHSEED=0 PYTHONPATH=$W uv run --locked --offline python $S/failing_first_a3.py`
  - `python3 $S/check_fixtures_a3.py $W`
  - `PYTHONDONTWRITEBYTECODE=1 uv run --locked pytest tests/test_m0_*.py -q -p no:cacheprovider` (the two flags were added so the run wrote nothing into the implementation worktree)

## 2. The current set

Read from the code: 16 lineages in `core.REGISTRY` (`lineages_m1.py`) + `load_rev2()` = 17 rev2 shapes (`lineages_m1_rev2.py`, each superseding a batch-1 shape) + 4 batch-1 lineages carried over unchanged (finite_differences, quadratic_area, recurrence_iterate, tiered_pricing) = 37. `M1.min_cost_packs_r2` is in `NOT_REGISTERED`, leaving 36 proposed.

min_cost_packs is NOT excluded everywhere. It is excluded only by a dictionary flag:
- `load_rev2()` returns it (its docstring says "the effective 21");
- it is in the capacity stage, the fixtures (`M1.min_cost_packs_r2.jsonl`), the schema and the manifest (flagged);
- `lineages_m1_clusters.ALL_STEMS` (37) and group S5 contain it, and the 22-cluster test counts over 37 ids including it (the count is unchanged because change_ways keeps S5 alive).
None of the rev2 or batch-1 lineages is in `core.REGISTRY`.

## 3. Correctness, determinism, wording

My solver (`solve_text_a3.py`) reads only the question TEXT, never `structured` or the generator's helpers, and uses exact arithmetic (`fractions`, integers, brute force where cheap: minute-by-minute pipes, enumeration for linear/ages/coins/quadratics/change ways/digit puzzles, Lagrange interpolation with a degree check for finite differences, region counting for painted cubes, bitmask DP for codes, exact big-integer powers for power_remainder, a CRT sieve).

- 400 items x 7 levels x 37 lineages (103,600 items, seed 3): 0 mismatches, 0 solver errors (`keys_n400_h0.txt`).
- All 2,380 rev2 fixture items on disk: 0 mismatches; every fixture SHA-256 matches the manifest (`fixtures_check.txt`).
- Determinism: per lineage-level SHA-256 of (question, answer, structured) identical under `PYTHONHASHSEED=0` and `=1` for all 259 lineage-levels.
- FAILED FIRST ATTEMPT (kept): `keys_trial_n20.json`. My solver forgot to strip the `_r2` suffix, so every rev2 lineage raised a solver error; fixed, re-run as `keys_trial2_n20.json`, then the full run. Shortcut attempt 1 (`shortcuts_a3_attempt1.py`, output `short_trial_n200.json`) scored several rules that are the correct procedure where the omitted step is idle (no drain below L3, no packing below L3, odd-length medians, asks one step ahead in finite differences); attempt 2 applies them only where the step is active. Both kept.

Wording (R-4):
- grid_perimeter_r2: DEFECT. "The perimeter is the total length of all the sides of squares that do not touch another square" also parses as "the sides of [squares that do not touch another square]" (4 x the isolated squares); the sentence before it ("some squares touch and some do not") primes that reading. The key changes on 399-400 of 400 items at every level.
- digit_puzzle_r2: DEFECT (new clue kind of the fix round). "one of its digits is d" read as "exactly one" leaves 45 / 115 / 124 / 139 / 107 / 114 / 145 items in 1,000 (L0..L6) with no unique answer (the key never moves to another number).
- The 16 existing lineages state no answer format ("Answer with a ..."); their keys do not change under an alternative reading. Minor.
- Minor: slot_permutations_r2's example "a code such as 012" appears in 4- and 5-digit items; power_remainder_r2's three-term sum list nests commas.

## 4. Strict clusters

My map: two lineages are one cluster when the same algorithm solves both up to renaming, presentation and parameter values. Over the 36 proposed lineages it gives 22, identical to `lineages_m1_clusters.py`:
S1 linear solve (linear_equation, ages, consecutive, average_missing, pipes_work, rectangle, coins); S2 weighted sum (shopping, speed_distance, mixture); S3 multiplicative chain (percent_change, fraction_remainder, tip_split, ratio_share); S4 product-rule counting (binomial_choose, slot_permutations); S5 unbounded table (change_ways; min_cost_packs not registered); S6 exposed faces (grid_perimeter, painted_cube); S7 step rule (arithmetic_series, recurrence_iterate); and 15 singletons (clock_duration, inclusion_exclusion, pigeonhole_worst_case, gcd_lcm, crt_congruence, prime_factors, power_remainder, quadratic_area, digit_puzzle, pythagoras, tiered_pricing, finite_differences, median_list, mode_tally, division_counting).
Disagreements with the map: none in the groups. One borderline I add (listed, not merged): gcd_lcm's lcm ask is the CRT sieve with all remainders 0; merging gcd_lcm with crt_congruence gives 21. clock_duration vs S2 stays borderline as recorded (21 if merged).

Cross-evaluation duplicates (`studies/m0/manifests/cross_evaluation_procedures.json`, named by ruling R-7, does NOT exist):

| M1 | Same algorithm in |
|---|---|
| crt_congruence | R2.crt_smallest |
| gcd_lcm | R2.gcd_euclid (gcd and lcm asks); C1.euclid_gcd(_traced) |
| prime_factors | R2.prime_factor_query |
| power_remainder | R2.modular_power (cluster with permutation_power); C1.fast_power(_r2) |
| change_ways (S5) | C1.coin_change_table (ways[T] shape); R2.coin_change_min (by S5's own count-vs-min merge) |
| inclusion_exclusion | R1.venn_counting(_r4) |
| median_list | R2 sort_list / kth_smallest cluster |
| recurrence_iterate, arithmetic_series (S7) | C1.fib_like, C1.loop_sum |
| borderline | division_counting ~ R2.multiples_between; mode_tally ~ C1.counter_list / R2.count_letter |

## 5. Shortcuts

My battery: per lineage-specific "ignore a condition", "one step instead of several", extremes and off-by-one rules, plus an echo-the-number-at-the-best-position rule and the most frequent answer (both fitted on one half and scored on the other, two folds). Base = the held-out most-frequent-answer rate. N = 1,000 per level, seed 5; 95% half-width about +-0.03. Signed difference (two-sided) is in `short_n1000_summary.txt`. Rules that are the correct procedure on the item class are not counted as shortcuts.

| Lineage | Rule | rate - base, L0..L6 |
|---|---|---|
| pythagoras_r2 | scale a memorised small triple (3-4-5, 5-12-13, 8-15-17, 7-24-25) | +0.50 +0.41 +0.40 +0.39 +0.36 +0.40 +0.37 |
| gcd_lcm_r2 | gcd of the two smallest values only | (k=2) +0.38 +0.35 +0.33 +0.32 at L3..L6 |
| gcd_lcm_r2 | smallest difference of two values | +0.06 at every level |
| mixture | unweighted mean of the two prices (the validity retry in `fmt` favours equal weights) | +0.27 +0.27 +0.28 +0.26 +0.28 +0.24 +0.25 |
| digit_puzzle_r2 | smallest number meeting the first two printed clues | 0.43 0.14 0.15 0.13 0.15 0.15 0.16 (base 0.00-0.01); some clue redundant in 0.73-0.97 of items |
| pigeonhole_worst_case_r2 | ignore the caps, (k-1)c+1 | +0.16 +0.18 +0.13 +0.14 +0.10 +0.11 +0.11 |
| coins | total value / larger coin | +0.17 +0.14 +0.12 +0.15 +0.13 +0.14 +0.12 |
| crt_congruence_r2 | remainder of the largest modulus | +0.12 +0.10 +0.09 then ~0 |
| crt_congruence_r2 | least solution of all but the last condition | +0.09 +0.08 +0.05 +0.11 +0.10 +0.10 +0.08 |
| power_remainder_r2 | exponent's last digit; Fermat with p+1 | +0.03 to +0.10 |
| mode_tally_r2 | first repeated value (mode asks) | +0.17 to +0.23 within its asks (+0.01 to +0.08 overall) |
| speed_distance | sum of speeds x mean hours (right when hours are equal) | +0.21 +0.17 at L0-L1 |
| ratio_share | largest share | +0.55 at L0 down to +0.27 (equals chance over the asked person; not cheaper than the procedure) |
| base rate itself | most frequent answer: grid_perimeter_r2 0.13-0.24; mode_tally_r2 0.06-0.15; power_remainder_r2 0.15-0.16 at L0-L1; division_counting_r2 0.07-0.14 | |

No measurable rule beyond base: ages, arithmetic_series, average_missing, binomial_choose, change_ways (+0.04 at L0-L1, T // max + 1), clock_duration, consecutive, finite_differences, fraction_remainder, inclusion_exclusion, linear_equation, painted_cube, percent_change, prime_factors (cheap rules), quadratic_area, recurrence_iterate, rectangle, shopping, slot_permutations (its large "parity fraction" rate is the correct symmetry argument where no lead rule applies), tiered_pricing, tip_split, median_list (mode of values +0.05 to +0.16; lower middle on even lists +0.03 to +0.07: small).
min_cost_packs_r2 (not registered): continuous relaxation, rounded up: +0.55 to +0.67.

R-1: no rev2 builder redraws on a heuristic's outcome; its loops (`_until`) are on validity only (distinct values, coprime moduli, size caps, uniqueness). The carried-over finite_differences and recurrence_iterate and several existing lineages still raise `Retry`, on validity (non-negative terms, representable decimals); the fix-round no-Retry test does not cover them. mixture shows that a validity retry can itself create a tell.

## 6. Capacity

Spec check. ADR-0033 section 6.2 asks, for every cluster and level, distinct items >= 10 x what the pools demand. Section 8: development pool 4,000 + sealed 20,000 per part, spread over the G clusters; section 6.5 can put a part on a single level. Worst case per cluster-level = ceil(24,000 / G) + tuning; x 10 gives R-5's formula. I agree with R-5, with two notes: (i) its tuning term of 100 per cluster is conservative (the tuning draw is 100 per level and part, shared by the G clusters); (ii) section 6.5 scores the reserve levels and applies the range rule again when no range works, so a reserve level can carry the core demand; R-5's 1,000 is not worst case for them (PENDING LEAD REVIEW). G per part with 22 clusters shuffled into two parts: 11 -> 22,820 per core level; with 21 clusters the smaller part has 10 -> 25,000. Reserve: 1,000.

Counting. Distinct = a different structural item. Numeric parameter values count (6.2 counts distinct items; R-5 lists only names, setting sentence and presentation order as non-distinct). Not distinct: names, setting sentence, object/activity/colour words, order of commutative parts, and (stricter than the implementer) a change of setting with the same computation (pythagoras walk = diagonal; ladder_top = ladder_base; binomial two_groups with genders swapped). M = 30,000 draws per lineage-level (seed 7). n_eff = M(M-1) / (2 x colliding pairs) (a lower bound on support; a level with no collision is given M(M-1)/6); Chao1 = support estimate. Cluster: equal-weight mixture over its lineages, n_eff = L^2 / sum(1/n_i); Chao1 summed.

Per cluster, n_eff of the mixture, L0..L6, and failing levels at G = 11 (the same at G = 10):

| Cluster | n_eff L0..L6 | fails (n_eff basis) | fails (Chao1 basis) |
|---|---|---|---|
| S1 linear solve | 1948, 2562, 4386, 5505, 7733, 8793, 11523 | 1-5 | none |
| S2 weighted sum | 82475, 120000, 189654, 222215, 254037, 281632, 322878 | none | none |
| S3 multiplicative chain | 2636, 4142, 6121, 8134, 9845, 11255, 13087 | 1-5 | 1-2 |
| S4 product-rule counting | 749, 1176, 1811, 2294, 1271, 2104, 2259 | 0-5 (L0 reserve too) | 1-3 |
| S5 unbounded table | 11221, 20752, 28374, 37446, 44877, 52648, 60833 | 1 (G=10 too) | none |
| S6 exposed faces | 67205 ... 591113 | none | none |
| S7 step rule | 2513, 3463, 4562, 5632, 6888, 8096, 9477 | 1-5 | 1-4 (1-5 at G=10) |
| clock_duration | > 1e8 | none | none |
| inclusion_exclusion | 4356, 66734, 337320, >1e8 ... | none | none |
| pigeonhole_worst_case | 16147, 33581, 734070, ... | none | none |
| gcd_lcm | 18475, 38926, 67830, 3.7e6, ... | none | none |
| crt_congruence | 20811, 56059, 137149, 221014, 410945, ... | none | none |
| prime_factors | 1802, 2570, 4547, 28175, 44868, 64119, 95477 | 1-2 | 1-2 |
| power_remainder | 108561, 190027, >1e8 ... | none | none |
| quadratic_area | 1858, 3256, 5088, 7315, 9846, 13049, 16419 | 1-5 | 1-5 |
| digit_puzzle | 5342, 50379, 51036, 50674, 50272, 48122, 45508 | none | none |
| pythagoras | 1059, 2442, 3930, 5447, 7097, 8701, 10371 | 1-5 | 1-5 |
| tiered_pricing | 200171, 519613, >1e7 ... | none | none |
| finite_differences | 3608, 3899, 5314, 5660, 7284, 5681, 5668 | 1-5 | 1-5 |
| median_list | > 3e6 | none | none |
| mode_tally | > 1e8 | none | none |
| division_counting | 20040, 40514, 65196, 96295, 135988, 171162, 221232 | none | none |

If the reserve levels carried the core demand, almost every cluster with a level-0 n_eff below 22,820 would also fail at L0 (and S1, S3, S4, S7, quadratic_area, pythagoras, finite_differences at L6).

Failing CLUSTERS at core levels: 9 on the n_eff basis (S1, S3, S4, S5 at L1, S7, prime_factors, quadratic_area, pythagoras, finite_differences); 7 on the Chao1 basis (S1 and S5 pass there).

Compared with the author. The manifest's eight failing lineages at G = 11 (binomial_choose_r2 0-5, change_ways_r2 1, finite_differences 1-5, prime_factors_r2 1-2, pythagoras_r2 1-5, quadratic_area 1-5, recurrence_iterate 1-5, slot_permutations_r2 1-6): CONFIRMED, same levels, n_eff within sampling error (my pythagoras is lower because of my stricter key; it fails either way). The fix round did NOT measure the 16 existing lineages, many of which fail:

| Lineage | n_eff L0..L6 | fails at G=11 (incl. reserve 1,000) |
|---|---|---|
| rectangle | 57, 72, 116, 136, 195, 220, 294 | 0-6 |
| consecutive | 221, 321, 841, 1042, 1240, 1443, 1644 | 0-5 |
| fraction_remainder | 500, 624, 749, 875, 998, 1123, 1245 | 0-5 |
| tip_split | 500, 1004, 1405, 1739, 2232, 2637, 3517 | 0-5 |
| ages | 841, 1087, 1822, 2237, 3354, 3971, 5574 | 0-5 |
| pipes_work | 615, 983, 1477, 23041, 33724, 47906, 65121 | 0-2 |
| ratio_share | 726, 1403, 9069, 16174, 89997, ... | 0-3 |
| percent_change | 1448, 1813, 2190, 5332, 6116, 6868, 7626 | 1-5 |
| arithmetic_series | 1265, 1797, 2348, 2880, 3431, 3944, 4477 | 1-5 |
| coins | 3917, 5793, 8019, 10571, 13366, 16881, 20672 | 1-5 |
| mixture | 16701, 18571, 21093, 24708, ... | 1-2 |
| passing | linear_equation, average_missing, shopping, speed_distance, clock_duration | none |

Full per-lineage table: `cap_clusters_M30000.txt` (first block).

## 7. Failing-first judgement of the fix-round tests

Pre-fix code had no `lineages_m1_rev2` / `m1_rev2_gates` module, so every new test fails there only by ImportError. The real question is whether each assertion would fail on the batch-1 shapes. I applied the same assertions read-only to them (`failing_first_a3.py`, seed 9):
- `test_shape_mix_is_the_designs_uniform_mix_at_every_level`: WOULD FAIL for gcd_lcm (gcd 0.66-0.68), division_counting (three shapes, 0.07/0.30/0.64), pigeonhole (0.35-0.40 / 0.60-0.65). WOULD PASS for binomial_choose, mode_tally, prime_factors, pythagoras, painted_cube (not discriminating for those).
- `test_inclusion_exclusion_ask_mix...`: WOULD FAIL (any 0.70-0.75 at L0-L1).
- `test_no_revised_builder_ever_raises_retry`: WOULD FAIL (18 batch-1 builders raise Retry). It covers REV2 only; the carried-over finite_differences and recurrence_iterate raise Retry and escape it.
- `test_revised_source_has_no_retry...`: a source grep; would fail on old source; superficial.
- Wording tests: slot_permutations and power_remainder discriminate (phrase checks plus an independent brute force or literal solver). digit_puzzle: only the phrase check discriminates; its uniqueness check uses the same reversal definition as batch 1 and would pass there; it does not test the new "one of its digits is" ambiguity. `test_every_revised_question_states_its_answer_format` would pass on batch 1 (not discriminating).
- Shortcut tests: the screen (max(0.25, 2 x constant) + 0.05) with the author's battery passes rev2, but that battery lacks the rules in section 5 (memorised triple, gcd of the two smallest, first two digit clues).
- Capacity tests: demand arithmetic (tautological); "passes where claimed" at M = 8,000 (`ne is None` passes); `binomial_choose_r2_still_fails` pins a failure, not a fix.
- Cluster tests: tautological on the map's own data; "merged_into_s2 == 21" removes clock_duration rather than merging it.
- Fixture de-duplication test: tautological against the fixture writer, which de-duplicates.

## 8. Tests

`PYTHONDONTWRITEBYTECODE=1 uv run --locked pytest tests/test_m0_*.py -q -p no:cacheprovider`: 522 passed, 2 xfailed, 1 warning (NumPy not installed, from torch) in 1,008.88 s. As expected. Run concurrently with my capacity sampling.

## 9. Verdict per lineage (37)

Capacity entries refer to core levels at G = 11 on the n_eff basis; a lineage in a failing cluster needs the cluster to pass, not necessarily the lineage.

| Lineage | Cluster | Verdict | Reason |
|---|---|---|---|
| linear_equation | S1 | REGISTRABLE AS IS (cluster S1 fails capacity) | |
| ages | S1 | NEEDS FIX | capacity 0-5 |
| consecutive | S1 | NEEDS FIX | capacity 0-5 |
| average_missing | S1 | REGISTRABLE AS IS (cluster S1 fails) | |
| pipes_work | S1 | NEEDS FIX | capacity 0-2 |
| rectangle | S1 | NEEDS FIX | capacity 0-6 (57-294 items) |
| coins | S1 | NEEDS FIX | tell +0.12 to +0.17 (PENDING LEAD REVIEW); capacity 1-5 |
| shopping | S2 | REGISTRABLE AS IS | no format sentence (minor) |
| speed_distance | S2 | REGISTRABLE AS IS | equal-hours rule +0.21 at L0 (minor) |
| mixture | S2 | NEEDS FIX | unweighted-mean tell +0.24 to +0.28; capacity 1-2 |
| percent_change | S3 | NEEDS FIX | capacity 1-5 |
| fraction_remainder | S3 | NEEDS FIX | capacity 0-5 |
| tip_split | S3 | NEEDS FIX | capacity 0-5 |
| ratio_share | S3 | NEEDS FIX | capacity 0-3 |
| binomial_choose_r2 | S4 | NEEDS FIX | capacity 0-5 |
| slot_permutations_r2 | S4 | NEEDS FIX | capacity 1-6 |
| change_ways_r2 | S5 | NEEDS FIX (marginal) | capacity L1 on n_eff only |
| min_cost_packs_r2 | S5 | SHOULD NOT BE REGISTERED | relaxation +0.55 to +0.67; also remove from `load_rev2()` output and the map |
| grid_perimeter_r2 | S6 | NEEDS FIX | R-4 wording, 399-400/400 keys change; base 0.13-0.24 |
| painted_cube_r2 | S6 | REGISTRABLE AS IS | |
| arithmetic_series | S7 | NEEDS FIX | capacity 1-5 |
| recurrence_iterate | S7 | NEEDS FIX | capacity 1-5 |
| clock_duration | own | REGISTRABLE AS IS | |
| inclusion_exclusion_r2 | own | REGISTRABLE AS IS | duplicate of R1.venn_counting (R-7) |
| pigeonhole_worst_case_r2 | own | NEEDS FIX (PENDING LEAD REVIEW) | ignore-caps rule +0.10 to +0.18 |
| gcd_lcm_r2 | own | NEEDS FIX | gcd of the two smallest +0.32 to +0.38 at L3-L6; duplicate of R2.gcd_euclid |
| crt_congruence_r2 | own | REGISTRABLE AS IS (PENDING LEAD REVIEW on +0.09 to +0.12) | duplicate of R2.crt_smallest |
| prime_factors_r2 | own | NEEDS FIX | capacity 1-2; duplicate of R2.prime_factor_query |
| power_remainder_r2 | own | REGISTRABLE AS IS | duplicate of R2.modular_power / C1.fast_power |
| quadratic_area | own | NEEDS FIX | capacity 1-5 |
| digit_puzzle_r2 | own | NEEDS FIX | "one of its digits" ambiguity; first-two-clues rule 0.13-0.43 |
| pythagoras_r2 | own | NEEDS FIX | memorised-triple route +0.36 to +0.50 (PENDING LEAD REVIEW); capacity 1-5 |
| tiered_pricing | own | REGISTRABLE AS IS | |
| finite_differences | own | NEEDS FIX | capacity 1-5 |
| median_list_r2 | own | REGISTRABLE AS IS | duplicate of the R2 sort / kth cluster |
| mode_tally_r2 | own | REGISTRABLE AS IS (PENDING LEAD REVIEW on base 0.06-0.15) | |
| division_counting_r2 | own | REGISTRABLE AS IS | |

Resulting cluster count: 22 written (21 with the borderline gcd_lcm / crt merge, 21 with clock_duration merged). Clusters with every member REGISTRABLE AS IS on my checks: S2 is not (mixture), S6 is not (grid_perimeter); clean singletons are clock_duration, inclusion_exclusion, crt_congruence, power_remainder, tiered_pricing, median_list, mode_tally, division_counting. Not a success.

## 10. Not verified

The implementer's second solvers (not read). The part A / B partition. Support by enumeration (mine is sampled; n_eff and Chao1 are estimates). Whether the pool builder draws lineages within a cluster with equal weight (my cluster numbers assume it). Any model behaviour. The batch-1 shapes beyond the failing-first assertions.

## 11. Files (scratch; `deliver/` holds the copy set)

Scripts: `common_a3.py`, `solve_text_a3.py`, `check_keys_a3.py`, `shortcuts_a3.py`, `shortcuts_a3_attempt1.py`, `short_summary_a3.py`, `capacity_a3.py`, `capacity_clusters_a3.py`, `digit_puzzle_extra_a3.py`, `failing_first_a3.py`, `check_fixtures_a3.py` (each starts with `# ruff: noqa`).
Outputs: `cap_clusters_M30000.txt`, `cap_M30000.txt`, `short_n1000_summary.txt`, `keys_n400_h0.txt`, `keys_n400_h1.txt`, `failing_first.txt`, `fixtures_check.txt`, `digit_puzzle_extra_n1000.txt`, `pytest_m0.txt`, `samples.txt`. Large JSON outputs stay in scratch only (`keys_trial_n20.json` failed attempt, `keys_trial2_n20.json`, `keys_n400_h0/h1.json`, `short_trial_n200.json`, `short_n1000.json`, `cap_M30000.json`).

Astra review: NOT_PERFORMED
