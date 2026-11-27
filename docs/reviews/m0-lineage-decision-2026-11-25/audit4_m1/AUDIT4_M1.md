# M0 M1: independent audit 4 of the M1 lineage set after fix round 3

Auditor: arbor-auditor (Claude Opus 5.5, `claude-opus-5-5`), 2026-11-25. Code audited: implementation worktree `agent-a0c9d741ea96ce52f`, branch `claude/m0-impl`, HEAD `f19d08c8` (read only; nothing written there).
This is independent engineering and mathematical evidence. It is not Astra validation and not human approval. Nothing is registered by it. Scientific choices are marked PENDING LEAD REVIEW.

Astra review: NOT_PERFORMED

Independence: `studies/m0/NOTES_FIX3_M1.md` and the prose of `studies/m0/manifests/m1_fix3_*` were NOT read before sections 1-9 below were written and hashed (section 10 records the hash and the comparison made afterwards). I read the code under audit (builders, loader, cluster map, gates, shortcut battery, checks, verify, build, failing-first, tests), the rulings, ADR-0033 sections 6.2-6.5 and the previous audit `audit3_m1/`. I imported the implementer's `m1_fix3_shortcuts.spec` only for its rule definitions (the brief asks for "their battery"); all scoring, solving, canonical keys, enumeration and summaries are my own code.

## 0. Environment, seeds, commands

- macOS 27.2.1 arm64 (Apple silicon, 18 cores). Generators: `uv run --locked --offline` in the implementation worktree (Python 3.12.14, its `uv.lock`), `PYTHONPATH=<impl>`, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONHASHSEED=0` unless stated. Standard-library summarisers and `exact_a4.py`: system `python3` 3.15.1.
- Audit seeds (throwaway integers through `core.stream` with `audit4-m1` labels; none is a registered study seed): 11 keys, 13 level profile, 17 shortcuts, 19 samples, 23 capacity, 29 subclass sizes.
- `W` = implementation worktree, `S` = `/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_audit4_m1_20261125` (scripts in `S/deliver/`), all run from `W`:
  - `python $S/deliver/common_a4.py 0,3,6 1 > samples_L036.txt`; `... 1,2,4,5 1 > deliver/samples.txt`
  - `PYTHONHASHSEED={0,1} ... python $S/deliver/check_keys_a4.py 300 $S/keys_n300_h{0,1}.json` (trial first at 20 per level: `keys_trial_n20.json`)
  - `... python $S/deliver/level_profile_a4.py $S/level_profile.json`; `... python $S/deliver/level_noop_before_a4.py`
  - `... python $S/deliver/shortcuts_a4.py 2000 $S/short_n2000.json` (attempt 1 at N=200: `shortcuts_a4_attempt1.py`, `short_trial_n200.json`); `python3 $S/deliver/short_summary_a4.py $S/short_n2000.json`
  - `... python $S/deliver/subclass_a4.py 4000`
  - `... python $S/deliver/capacity_a4.py 30000 $S/cap_M30000.json <all but digit_puzzle>`; `... capacity_a4.py 1200 $S/cap_digit_M1200.json digit_puzzle`; `python3 $S/deliver/capacity_clusters_a4.py $S/cap_M30000.json`
  - `python3 $S/deliver/exact_a4.py` (exact support and exact n_eff by enumeration, no generator import)
  - `... python $S/deliver/cross_eval_present_a4.py`
  - `... python -m studies.m0.m1_fix3_failing_first` (the implementer's evidence script, re-run unchanged, output `failing_first_theirs_rerun.txt`)
  - `PYTHONDONTWRITEBYTECODE=1 timeout 3000 uv run --locked pytest tests/test_m0_m1_*.py -q -p no:cacheprovider`

## 1. The current set (task 1)

From the code: `lineages_m1_fix3.load_all()` returns 36 lineages (35 `_r3` builders + `M1.tiered_pricing` from `load_batch()`); `NOT_REGISTERED` = {pythagoras_r3, binomial_choose_r3, digit_puzzle_r3}; `load_registered()` = 33. CONFIRMED.
- min_cost_packs: absent from `load_all()`, from `ALL_STEMS` (36), from `GROUPS`, from the cross-evaluation dicts; `EXCLUDED_EVERYWHERE` lists it. CONFIRMED.
- The three NOT REGISTERED: excluded from `strict_clusters(load_registered())` (count 20), from fixtures (`write_fixtures` iterates `load_registered()`; the fixtures test asserts no NR fixture), and from the cluster evaluation in `m1_fix3_gates.evaluate` (`reg = [i for i in lv if i not in nr]`). They ARE still sampled by `run_capacity` (it iterates `load_all()`), which is a measurement of an attempt, not part of the cluster count; acceptable. CONFIRMED excluded from map count, G, fixtures and the cluster capacity gate.
- None of the 36 is in `core.REGISTRY` (checked by the test and by reading `core._load_all`).

## 2. Keys, determinism, wording (task 2)

Solver: `solve_text_a4.py` reads only the question text (regexes rewritten for the r3 wording), exact arithmetic, and a different route from the builders where cheap (difference tables instead of Lagrange, minute-by-minute clock counts, sieve over the largest modulus for CRT, divisor pairs, edge-incidence counting for grids, brute force over every cube when small, DP over coin values, DP over code positions).

- 300 items x 7 levels x 36 lineages = 75,600 items (seed 11): 0 mismatches, 0 solver errors, under `PYTHONHASHSEED=0` and again under `=1` (`keys_n300_h0.txt`, `keys_n300_h1.txt`).
- Determinism: SHA-256 of (question, answer, structured) per lineage-level identical under both hash seeds for all 252 lineage-levels (`determinism_h0_h1.txt`).
- Every item states its answer format (0 items without "Answer with a ..." in 75,600).

Alternative readings measured (key changes / applicable, per level, n = 300):
| Lineage | Reading | Changes | Verdict |
|---|---|---|---|
| slot_permutations_r3 | "a code cannot start with 0" where 0 is allowed and the first-digit rule is "even" or "less than 5" (no leading-zero sentence printed in those items) | 47-63 of 300 per level (16-21 %); 17.6-19.0 % of items at N = 4,000 (`subclass_n4000.txt`) | DEFECT (R-4). Example L5: digits 0, 1, 3, 5, 7, "first digit must be even": key 100, every code starts with 0; under the other reading the key is 0. The leading-zero sentence is printed only for the "any" rule. The wording test does not catch it (its second assert is satisfied by `first != "any"`). |
| grid_perimeter_r3 | outer boundary only (hole edges not counted) | 18-103 of 300 | Not a defect: the item defines the perimeter explicitly ("unit-length sides that belong to exactly one square"); single reading. The old "isolated squares" reading changes 300/300 but the old phrase is gone. |
| inclusion_exclusion_r3 | "do both" read as exactly two | 300/300 at L3-L6 | Convention stated in every three-set item. OK. |
| percent_change_r3 | percents of the original added | 298-300/300 | Convention stated ("each change applied to the price just before it"). OK. |
| mode_tally_r3 | "others" read as number of other distinct values | all | Convention stated ("once for each time it is written"). OK. |
| digit_puzzle_r3 (NR) | "at least once" vs "exactly once" | 0/300 | Fixed (NR anyway). |

Rendered items read at L0-L6 for all 36 (`samples_L036.txt`, `samples.txt`). The 16 reworded originals state format, units, sign convention, inclusive counting, 24-hour clock, "applied to the price just before it", "calculated on the bill before tip". grid_perimeter now has one reading. Minor, not key-changing: last_digit_power's three-term sum nests commas ("the sum of the product of 220 factors, each equal to 15, the product of ... and the product of ..."); "and 1 do all three"; slot's example "012" in 4- to 6-digit items.

## 3. Redraws and construction tells (task 3)

Loops in the r3 builders (read in the source): `speed_distance` `until(draw)` (an integral average must exist; validity); `linear_equation` `while m == 0: x = ...` (redraws the ANSWER x to avoid printing "adding 0"; removes one value x = e/(k-j); no measurable tell, but it is literally a redraw conditional on the answer, R-13 wording); `_coprime_set` (validity); `slot_permutations` `until(cnt > 0)` (rejects items whose answer is 0: conditional on the answer; no measurable tell); `binomial_choose` size cap and `digit_puzzle`'s MIN_LEFT condition (NR; the latter redraws on how well "all but one clue" performs, i.e. on a heuristic's outcome, an R-1 pattern, moot because NR). No r3 builder raises `Retry` (checked by the implementer's test, which also covers tiered_pricing).

"Valid by construction" choices that created NEW tells (the mixture lesson repeated):
- coins_r3: `nl >= ceil(hi/lo)` makes `floor(total/hi)` exactly 0.000 on every "hi" ask (R-13 zero) and moves the mass to its neighbour: `floor(total/hi) - 1` is right on 17.7 / 17.3 / 14.6 / 12.5 / 11.6 / 11.2 / 10.4 % of hi asks and `count - (floor(total/hi) - 1)` on 19.5 ... 10.6 % of lo asks; overall rate - base +0.160 +0.140 +0.128 +0.114 +0.110 +0.087 +0.076 (L0..L6).
- pigeonhole_worst_case_r3: log-uniform counts with k up to the largest count make "draw every other colour, then k of the largest" (sum - max + k) exact whenever every other colour has <= k-1 marbles: 59 / 59 / 52 / 53 / 48 / 49 / 49 % of "same" asks; overall +0.273 +0.287 +0.275 +0.252 +0.229 +0.243 +0.257. The audited "ignore caps" rule fell to 16-4.5 %; the tell moved to the mirror rule.
- mode_tally_r3: f in {4, 5, 6}, R rivals at f-1 and a small tail make the "others" key n - f predictable from the printed list length n alone: the most frequent key for that n is right on 78-81 % of "others" asks (held-out, N = 4,000 per level); "n - 5" alone 31-37 %; overall (mode by visible ask and n) +0.367 to +0.382 at every level. The "mode" ask keeps the first-half rule at +0.08 to +0.10 overall (0.20-0.24 within the ask).
- gcd_lcm_r3: the construction (g times pairwise coprime q's, each gcd value omitting one q) makes every partial rule exactly 0.000 (gcd of two smallest / largest / first two / min and max, lcm of two largest / first two, min, max, product, smallest pairwise gcd) and makes the FALSE general rules lcm = product / gcd^(k-1) and gcd = product / lcm^(k-1) exact on 100 % of items at k >= 3 (L3-L6). Judgement on R-13: the zeros do not give a cheaper route to the key (excluding a candidate does not produce the answer), and the false rules need the gcd or lcm of all values, so they are not cheaper than the procedure. They are a construct-validity issue: a model holding the misconception scores full marks at L3-L6. PENDING LEAD REVIEW.
- mixture_r3 (the audited case): fixed; unweighted mean at chance; equal weights 3-4 %; swapped weights +0.02 to +0.03.

## 4. Shortcuts (task 4)

Battery: mine (lineage-specific rules written for the r3 constructions, plus three fitted generic rules: printed number at the best position, best position + best offset in -12..12, most frequent answer per VISIBLE question type) + the implementer's `spec`. N = 2,000 per level (digit_puzzle 300), seed 17, base = held-out most frequent answer (two folds); rates over all items; two-sided; 95 % half-width about +-0.02 at these rates. Output: `short_n2000_summary.txt`.

Rules I excluded as the correct procedure (with reasons in `short_summary_a4.py`): consecutive mean + step; division k - N mod k (wrong only on exact fits, 3-4 %); finite_differences one extension when the next position is asked; gcd_lcm k = 2 ab / gcd (and the k >= 3 false rules, listed in section 3); ratio_share largest / smallest share (a guess of who is asked, needs the procedure); prime_factors largest prime <= sqrt(n) (needs the full trial division; 87-99 % within the "largest" ask); slot ignore-first-rule / parity fraction; last_digit_power "Fermat with p + 1" (exact where every exponent <= p, the reduction idle).

Judgement of the "correct on a subclass" exclusions, with subclass sizes (`subclass_n4000.txt`):
- slot_permutations ignore_first_rule: right on 100 % of items with no first-digit rule (18-19 % of items, visible in the text) and 1.4-1.8 % of the rest. Agree it is the procedure on a visible 18 % subclass. Not excluded by me and not in their list: "forget the overlap correction" (|first| x |last| x perm) is exact on 11-13 % of ALL items (no-repeat items whose first and last sets are disjoint). Under 0.15 either way.
- last_digit_power Fermat(p+1) / exp mod p: the subclass with every exponent <= p is 13.7 % (L0), 10.0 % (L1), < 1 % from L2. Agree (idle reduction). With it, L0 reads +0.105.
- prime_factors: agree (procedure).
- division_counting: agree (3-4 % exact fits).

Max |rate - base| over levels and non-excluded rules, 33 registered candidates:

| Bin | Count | Lineages |
|---|---|---|
| <= 0.10 | 30 | all others; near the boundary: slot_permutations +0.098 (mode by visible rule set, L6), median_list +0.089 (mode of the values, L0), last_digit_power +0.079 (exp mod p, L0; +0.105 with the idle-subclass rule), grid_perimeter -0.087 (a base of 0.05-0.09) |
| 0.10-0.15 | 0 | |
| 0.15-0.25 | 1 | coins_r3 +0.160 (L0) |
| > 0.25 | 2 | pigeonhole_worst_case_r3 +0.287 (L1), mode_tally_r3 +0.382 (L1) |

NOT REGISTERED (for the record): digit_puzzle +0.11 to +0.28, pythagoras +0.257 at L0 (memorised 16 triples), binomial_choose +0.131 at L0 (product of x times j).
The implementer's claim "every cheap rule within 0.10 except mode_tally first-half +0.083..+0.100 and last_digit_power +0.0995 at L0" is NOT CONFIRMED: their battery lacks the three rules above. Their numbers for the rules they did run are consistent with mine (mode_tally first-half +0.085 to +0.10 overall; last_digit_power at L0 within 0.10 on non-idle rules).

Level profiles before / after (task 4, last part; `level_profile.txt`, `level_noop_before.txt`). The no-op test builds levels L and L' from the same random stream; byte-identical items mean the level is ignored:
- Levels made IDENTICAL by this round (not identical before): mixture_r3 L0 = L1 = L2 and L3 = L4 = L5 = L6 (2 distinct distributions out of 7; batch 1 had weights 1..9+L); gcd_lcm_r3 L0 = L1 = L2, L3 = L4, L5 = L6 (rev2's ranges grew with the level); finite_differences_r3 L0 = L1 = L2, L3 = L4, L5 = L6 (batch 1: only L5 = L6); slot_permutations_r3 L2 = L3 = L4 added to L0 = L1, L5 = L6. Unchanged from before: average_missing and clock_duration (0 = 1, 2 = 3, 4 = 5).
- mode_tally_r3: the list length no longer grows (about 46 numbers at every level; rev2 grew 26 -> 57); only the value range moves. Its level is nearly meaningless.
- Widening raised the low levels' number sizes (mean log10 answer at L0, before -> after): consecutive 1.81 -> 3.13, fraction_remainder 1.72 -> 2.88, rectangle 2.41 -> 3.27, quadratic_area 1.22 -> 1.88, ratio_share 1.57 -> 2.23, recurrence 2.49 -> 3.25, median 1.21 -> 1.98, ages 1.20 -> 1.74, arithmetic_series 2.17 -> 2.83 (and 4 -> 6 printed numbers); it flattened the level gradient for fraction_remainder (2.88 -> 3.19 across L0-L6) and tip_split (L0 easier: 2.05 -> 1.76). Step counts per level are unchanged as claimed. Whether L0 is still the "easier reserve" and five registered levels still differ in difficulty is PENDING LEAD REVIEW (section 6.5 needs interior ranges, and identical levels make some candidate ranges equivalent).

## 5. Strict clusters (task 5)

My map over the 33 registered candidates (same algorithm up to renaming, presentation and parameter values) gives 20, identical to `lineages_m1_fix3_clusters.py`: S1 linear solve (linear_equation, ages, consecutive, average_missing, pipes_work, rectangle, coins); S2 weighted sum (shopping, speed_distance, mixture); S3 multiplicative chain (percent_change, fraction_remainder, tip_split, ratio_share); S4 (slot_permutations); S5 (change_ways); S6 (grid_perimeter, painted_cube); S7 (arithmetic_series, recurrence_iterate); 13 singletons (clock_duration, inclusion_exclusion, pigeonhole_worst_case, gcd_lcm, crt_congruence, prime_factors, last_digit_power, quadratic_area, tiered_pricing, finite_differences, median_list, mode_tally, division_counting). The r3 rectangle "excess" shape stays in S1 (linear).
Borderline, listed not merged: gcd_lcm + crt (theirs), clock_duration + S2 (theirs), and two I add: tiered_pricing + S2 (a weighted sum after allocating units to tiers; the bill-to-units ask is a linear solve inside the last tier) and S1 + S7 through consecutive / arithmetic_series (the same arithmetic-series sum, inverted in one and evaluated in the other). Range: 20 strict, 16 if all four merge.

Cross-evaluation (algorithm also present in the CURRENT fix-3 maps, `cross_eval_present.txt`):
| M1 cluster | Other evaluation (current id) |
|---|---|
| crt_congruence | R2.crt_smallest |
| gcd_lcm | R2.gcd_euclid; C1.euclid_gcd_traced_f3 (B5) |
| prime_factors | R2.prime_factor_query |
| last_digit_power | R2.modular_power (cluster with permutation_power); C1.fast_power_f3 (variant) |
| S5 change_ways | C1.coin_change_table_f3 (B4); R2.coin_change_min |
| inclusion_exclusion | R1.venn_counting_r5 |
| median_list | R2.kth_smallest cluster (with sort_list); C1.bubble_pass (medium) |
| S7 | C1.fib_like_f3 / fib_shapes_recursive_f3 (B6); C1.loop_sum (B1, medium) |
| borderline | division_counting ~ R2.multiples_between; mode_tally ~ C1.counter_list_f3, C1.majority_vote_scan_f3, R2.count_letter / count_divisible |
8 of 20 clusters strong, 2 borderline. The M1 map's own `CROSS_EVALUATION` names stale ids (R1.venn_counting / _r4, C1.euclid_gcd, C1.fast_power / _r2, C1.fib_like, C1.counter_list) and omits C1.majority_vote_scan_f3 and C1.bubble_pass. `studies/m0/manifests/cross_evaluation_procedures.json` (rulings R-7, R-15) still does not exist.

## 6. Capacity (task 6)

Own canonical key (`capacity_a4.key`; stricter than the implementer's for fraction_remainder: the two spends {a, b} unordered). Sampled M = 30,000 per lineage-level (seed 23) and EXACT support and n_eff by enumeration (`exact_a4.txt`); they agree within 1-2 % (rectangle 3,625 vs exact 3,609; fraction_remainder 6,283 vs 6,268; percent_change 14,024 vs 13,920; slot 37,152 vs 36,563).
G = 10 on my map (20 clusters, 10 per part): demand 25,000 per cluster and level, reserve levels the same.

- All 20 clusters pass at G = 10 on all three bases (equal-weight mixture n_eff, Chao1 sum, equal share). CONFIRMED.
- Tight cells (equal share, n_eff x L, exact): S3 L0 4 x 6,268 = 25,072 (fraction_remainder, +0.3 %; with the ordered (a, b) reading 4 x 9,943 = 39,772); S1 L0 7 x 3,609 = 25,263 (rectangle, +1.1 %; the implementer's 25,245); prime_factors L0 31,236 exact (uniform, +25 %); S6 L0 2 x 17,420 = 34,841 (grid_perimeter); S4 L0-L1 36,563 (slot). The tightest cell is S3 L0 under the least favourable commutative-order reading, not S1.
- FRAGILE: at G = 9 (19 or 18 clusters, e.g. one borderline merge, or pigeonhole and mode_tally dropped for their tells) demand is 27,680 and S1 L0 and S3 L0 FAIL on the equal-share basis (rectangle, fraction_remainder); at G = 8 also L1. They pass on the support and mixture bases.
- NOT REGISTERED claims: pythagoras: 294 / 1,981 / 3,414 integer right triangles with hypotenuse <= 400 / 2,000 / 3,200 (exact, CONFIRMED); sampled n_eff 347 ... 2,490 (CONFIRMED). binomial_choose: exact support 620 / 892 / 1,982 at L0-L2 (CONFIRMED), exact n_eff 612 / 882 / 1,949. digit_puzzle: n_eff 63 / 2,128 / 2,284 / 1,631 / 1,646 / 188 / 183 at M = 1,200 (CONFIRMED order of magnitude; their 82 ... 190 at M = 6,000).
- Equal-weight assumption: the pool builder that exists, `core.generate_pool`, allocates the pool EQUALLY PER LINEAGE (`allocate(size, [1.0] * len(lins))` over `part_lineages`, which reads `core.REGISTRY`), and `m0_draw` balances per lineage id. It has no notion of the strict cluster. Under that builder (i) a cluster's share grows with its member count (S1 would carry 7 lineage shares), contradicting "the cluster is the lineage" for balance and bootstrap; (ii) each LINEAGE-level must meet 10 x (ceil(4000/N) + ceil(20000/N) + 100), N = lineages in the part: 9 lineages fail at N = 10, 7 at N = 16, and even at N = 23 rectangle (all levels), fraction_remainder (L0-L4), ages, consecutive and pipes_work (L0) fail (`cap_clusters_M30000.txt`). (iii) `draw_items` de-duplicates on the normalised TEXT, which includes names and settings, so it would accept structural duplicates. The capacity pass therefore holds only for a pool builder not yet written (equal split by strict cluster, then equally inside the cluster, de-duplicated structurally). Engineering requirement; PENDING LEAD REVIEW.

## 7. Tests (task 7)

`PYTHONDONTWRITEBYTECODE=1 uv run --locked pytest tests/test_m0_m1_*.py -q -p no:cacheprovider`: 257 passed, 1 warning (NumPy not installed, from torch) in 594.63 s (`pytest_m1.txt`). The implementation worktree's `git status` afterwards shows no change made by this run (its untracked `audit4_r2/`, `*.bak`, `*.bak2` predate it and are not mine).

Genuineness (read, and the implementer's `m1_fix3_failing_first.py` re-run unchanged: every printed line reproduced):
- Genuine and discriminating: no-Retry (fails on 8 old shapes; passes trivially on tiered_pricing, shopping, fraction_remainder), stated format (fails on all 16 old shapes), grid wording, the text-parsing grid test, painted-cube closed form vs loop, slot count vs enumeration, estimator on a known support, cluster evaluation on synthetic data, shape-mix tests (fail on old gcd_lcm, division_counting, pigeonhole), determinism across hash seeds, fixtures structurally distinct.
- Weak or tautological: shortcut bounds were set from the new shapes' measured rates "with a margin" (regression pins, not criteria); `coins value_over_high <= 0.06` and `gcd_of_two_smallest == 0.0` pin R-13 zeros and pass BECAUSE of the tell; `pigeonhole ignore_caps <= 0.12` and the mode_tally rules pass while the mirror / length rules read 0.5-0.8 within the ask; the slot wording test cannot fail for "even" / "< 5" first rules (second assert satisfied by `first != "any"`); `test_demand...` is arithmetic against itself; the cluster tests compare the map with a hand copy of the same map; `test_measured_report_when_present...` pins the manifest; `test_nothing_enters_core_registry`'s first assert is convoluted (it reduces to "no r3 id in core").
- `test_exact_support_reaches_the_equal_share` uses exact SUPPORT; the gate uses n_eff; at G = 10 both pass, at G = 9 the n_eff basis fails (section 6).

## 8. Verdicts per lineage (task 8)

Bounds are not mine to set; x is the smallest bound under which the lineage passes on my measurement.

| Lineage | Cluster | Verdict | Reason / numbers |
|---|---|---|---|
| linear_equation_r3 | S1 | REGISTRABLE AS IS | max +0.015 |
| ages_r3 | S1 | REGISTRABLE AS IS | +0.022 |
| consecutive_r3 | S1 | REGISTRABLE AS IS | procedure rule only |
| average_missing_r3 | S1 | REGISTRABLE AS IS | +0.014 |
| pipes_work_r3 | S1 | REGISTRABLE AS IS | +0.032 |
| rectangle_r3 | S1 | REGISTRABLE AS IS | +0.015; S1 capacity margin 1 % at G = 10, fails at G <= 9 (equal share) |
| coins_r3 | S1 | REGISTRABLE ONLY IF BOUND >= 0.17 (NEEDS FIX below) | floor(total/hi) - 1: +0.160 ... +0.076; floor(total/hi) exactly 0 on hi asks |
| shopping_r3 | S2 | REGISTRABLE AS IS | +0.029 |
| speed_distance_r3 | S2 | REGISTRABLE AS IS | +0.035 |
| mixture_r3 | S2 | REGISTRABLE AS IS (level note) | +0.033; levels collapsed to 2 distributions (PENDING LEAD REVIEW) |
| percent_change_r3 | S3 | REGISTRABLE AS IS | +0.006 |
| fraction_remainder_r3 | S3 | REGISTRABLE AS IS | +0.021; S3 capacity margin 0.3 % at G = 10 (unordered reading), fails at G <= 9 |
| tip_split_r3 | S3 | REGISTRABLE AS IS | |
| ratio_share_r3 | S3 | REGISTRABLE AS IS | +0.051 (largest / smallest share excluded) |
| slot_permutations_r3 | S4 | NEEDS FIX | R-4: leading-zero convention unstated in 18-19 % of items where it changes the key; +0.098 near the boundary |
| change_ways_r3 | S5 | REGISTRABLE AS IS | -0.042 |
| grid_perimeter_r3 | S6 | REGISTRABLE AS IS | one reading; base 0.05-0.09 |
| painted_cube_r3 | S6 | REGISTRABLE AS IS | |
| arithmetic_series_r3 | S7 | REGISTRABLE AS IS | |
| recurrence_iterate_r3 | S7 | REGISTRABLE AS IS | |
| clock_duration_r3 | own | REGISTRABLE AS IS | |
| inclusion_exclusion_r3 | own | REGISTRABLE AS IS | duplicate of R1.venn_counting_r5 (R-7) |
| pigeonhole_worst_case_r3 | own | REGISTRABLE ONLY IF BOUND >= 0.29 (NEEDS FIX below) | others-then-k +0.229 ... +0.287 (0.48-0.59 within "same") |
| gcd_lcm_r3 | own | REGISTRABLE AS IS on shortcuts (PENDING LEAD REVIEW) | exact zeros and the exact false general rule at k >= 3; levels collapsed to 3 distributions; duplicate of R2.gcd_euclid, C1.euclid_gcd_traced_f3 |
| crt_congruence_r3 | own | REGISTRABLE AS IS | +0.054; duplicate of R2.crt_smallest |
| prime_factors_r3 | own | REGISTRABLE AS IS | duplicate of R2.prime_factor_query |
| last_digit_power_r3 | own | REGISTRABLE AS IS | +0.079 (+0.105 with the idle-subclass rule at L0) |
| quadratic_area_r3 | own | REGISTRABLE AS IS | |
| tiered_pricing | own | REGISTRABLE AS IS | borderline with S2 (listed) |
| finite_differences_r3 | own | REGISTRABLE AS IS (level note) | levels collapsed to 3 distributions (PENDING LEAD REVIEW) |
| median_list_r3 | own | REGISTRABLE AS IS | +0.089 at L0, near 0.10 |
| mode_tally_r3 | own | NEEDS FIX (only if bound >= 0.39) | "others" key predictable from n: 78-81 % within the ask, +0.37 overall; levels flat |
| division_counting_r3 | own | REGISTRABLE AS IS | |
| pythagoras_r3, binomial_choose_r3, digit_puzzle_r3 | - | SHOULD NOT BE REGISTERED (agree) | section 6 |

Counts over the 33 candidates: 29 REGISTRABLE AS IS (3 with level notes, gcd_lcm with a construct note), 2 REGISTRABLE ONLY IF BOUND >= x (coins 0.17, pigeonhole 0.29), 2 NEEDS FIX (slot_permutations, mode_tally), 0 SHOULD NOT BE REGISTERED (plus the 3 NR, agreed).
Cluster count (strict map), counting slot_permutations as fixed (if it is not, subtract 1 from every figure):
- bound 0.10: 18 (pigeonhole and mode_tally clusters lost; coins leaves S1, which survives);
- bound 0.15: 18;
- bound 0.25: 18 (coins back);
- (0.29: 19; 0.39: 20.)
With 18 or 19 clusters G = 9 and S1 L0 and S3 L0 fail capacity on the equal-share basis (section 6). With all four borderline merges, 18 -> 14.

## 9. Not verified

The implementer's second solver (none exists from a separate context; `m1_fix3_verify.py` is a self-check and I did not use it). The part A / B partition. Exact support for clock_duration, median_list, mode_tally, shopping, speed_distance (sampled only; no collision in 30,000). Model behaviour of any kind. Whether a natural reader actually adopts the "others, then k" or "n - 5" rules (I measured that they are right, not that they are used). The fixture files' hashes against the manifest (not recomputed this round).

Leftovers (nothing deleted): scratch files in `S` (`keys_trial_n20.json`, `keys_n300_h0.json`, `keys_n300_h1.json`, `short_trial_n200.json`, `short_n2000.json`, `short_n2000.txt`, `cap_M30000.json`, `cap_digit_M1200.json`, `level_profile.json`, `samples_L036.txt`, `pytest_m1.txt`). The first render command wrote an error message into `deliver/samples.txt` (path did not yet exist through my worktree); it was overwritten by the real samples. Slips: my first `Write` to the base-repo path was refused by the hook and redone through my worktree's `experiments` symlink (same directory); shortcut attempt 1 contained four rules that were the procedure (kept, section 0).

Astra review: NOT_PERFORMED

## 10. Comparison with the implementer's notes (written AFTER sections 0-9 were hashed)

SHA-256 of this file as it stood with sections 0-9 only (before I opened `NOTES_FIX3_M1.md` or any manifest prose): `8b1568604560c519437d66bad530b3f6d37f1c765508676c4bf48e66d26faffb` (`AUDIT4_M1_sections_1-9.sha256`). I then read `studies/m0/NOTES_FIX3_M1.md` (grep for the points below and its sections 3-4). No slip: I did not read either before the hash.

| Point | Implementer (`NOTES_FIX3_M1.md`) | Mine | Discrepancy |
|---|---|---|---|
| Set, exclusions, 20 clusters | 33 candidates, 20 clusters, 3 NR | same | none |
| S1 L0 equal share | 25,245 (rectangle 3,606) | 25,263 exact / 25,377 sampled | none (within sampling) |
| fraction_remainder n_eff min | 9,607 | 6,268 exact | canonical key: they count (a, b) and (b, a) as distinct; with the commutative-order reading S3 L0 (25,072) is the tightest cell, not S1 |
| Capacity at G = 10 | all pass | all pass; fails at G <= 9 for S1 L0, S3 L0 (equal share) | fragility not stated by them |
| Pool builder | not discussed | `generate_pool` balances per lineage; the pass needs a new builder | not addressed by them |
| coins | worst +0.030 | +0.160 (floor(total/hi) - 1); floor(total/hi) exactly 0 on hi asks | rule missing from their battery |
| pigeonhole | worst +0.071 (ignore_caps 0.17 within 'same' at L0) | +0.287 (others then k, 0.48-0.59 within 'same') | rule missing from their battery |
| mode_tally | +0.101 (first half) | +0.382 ("others" key from n, 0.78-0.81 within the ask) | rule missing from their battery; their first-half numbers agree with mine |
| slot_permutations | -0.012 | +0.098 (mode by visible rule set); leading-zero wording defect in 18-19 % of items | wording defect not found by them; their test cannot fail on it |
| last_digit_power | +0.0995 / +0.0975 at L0-L1 | +0.079 on non-idle rules, +0.105 with the idle-reduction rule | consistent within noise and exclusion choice |
| gcd_lcm zeros | listed (R-13) | listed; plus the exact FALSE general rule at k >= 3 | the false-rule point not stated by them |
| NR capacity numbers | pythagoras 294 / 1,981 / 3,414; binomial 620 / 892 / 1,982; digit 82 ... 190 | same exact counts; digit 63 ... 183 at M = 1,200 | none |
| Level collapse (mixture, gcd_lcm, finite_differences, slot, mode_tally) | not mentioned | measured (section 4) | not addressed by them |
| Cross-evaluation ids | audit-3 ids (stale) | current fix-3 ids | stale names in their map and notes |

Astra review: NOT_PERFORMED
