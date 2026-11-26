# M0-M1: final independent re-measurement of the 29 M1 survivors after fix 4

Auditor: arbor-auditor (Claude Opus 5.5, `claude-opus-5-5`), 2026-11-25. This is independent engineering and mathematical evidence. It is not Astra validation and not human approval, and it registers nothing. Scientific choices are marked PENDING LEAD REVIEW.

Code audited: implementation worktree `agent-a0c9d741ea96ce52f`, branch `claude/m0-impl`, read only. At the start (22:17) HEAD was `9bcec484` with the fix-4 files uncommitted. Another session committed them as `7cd0ac5a` (22:33:58) while I was working. Every input file's mtime is before 22:17, so I audited the same bytes that were committed. SHA-256: `lineages_m1_fix4.py` da6027f4…, `m1_fix4_survivors.json` 153e6837…, `m1_fix4_battery_raw.json` af6087d0….

Independence: before I wrote the solver I read `NOTES_FIX4_M1.md`, the manifest, `lineages_m1_fix4.py` (which includes the six r4 builders and their answer lines), `lineages_m1_fix3.py`, `lineages_m1_fix3_common.py`, `core.py`, the battery and capacity scripts, and the audit-3 and audit-4 rule scripts. I did not read the r3 builder bodies, `solve_text_a3.py`, `solve_text_a4.py`, `m1_fix3_verify.py` or `m1_fix4_verify.py`. I read the r3 builders' docstrings only after the key checks, for the level step. The solver was written from item texts (`samples_L036.txt`, `templates.txt`, `asks.txt`) and the printed conventions. Where the generators compute an answer one way, the solver takes a different route: minute-by-minute clock counts, Lagrange interpolation plus a consistency check of every printed term, divisor counting by search, a coin table cross-checked by brute force, unit-side ownership for grids, axis-class enumeration for cubes, search over the smallest term for consecutive sums, a sieve on the largest modulus for CRT, and a unit search for tiered bills.

## 0. Environment, seeds, commands

- macOS 27.2.1 arm64. Generators run through `uv run --locked --offline python` (Python 3.12.14, uv 0.12.15) from the worktree with `PYTHONPATH=.` and `PYTHONDONTWRITEBYTECODE=1`. `PYTHONHASHSEED=0` unless stated. Standard-library summarisers use system `python3` 3.15.1. Nothing was written in any worktree. A `find -newermt 22:17` check before 22:33 found no changed file. The entries that appear after 22:33 (`docs/reviews/.ruff_cache`, `docs/reviews/m0-lineage-decision-2026-11-25/cross_evaluation_map`) belong to the other session's commit and ruff run. I never ran ruff. `git status` shows only the two pre-existing `.bak` files.
- Fresh audit seeds (throwaway integers, label `final-m1-a5`; none is a registered study seed): 2611251 keys, 2611257 keys (second set), 2611252 rules, 2611253 levels, 2611254 capacity, 2611255 reproducibility, 2611256 samples.
- `S` = `/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_final_m1_20261125/deliver`. All commands were run from the worktree:
  - `python $S/check_keys_a5.py 500 2611251 $S/keys_n500.json` and, under `PYTHONHASHSEED=1`, `python $S/check_keys_a5.py 1000 2611257 $S/keys_n1000_seed2611257_h1.json`
  - `python $S/rules_a5.py repro 2000 $S/rules_repro_n2000.json`, then `python3 $S/compare_repro_a5.py $S/rules_repro_n2000.json studies/m0/manifests/m1_fix4_battery_raw.json`
  - `python $S/rules_a5.py fresh 4000 2611252 $S/rules_fresh_n4000.json`, then `python3 $S/pool_a5.py $S/rules_fresh_n4000.json studies/m0/manifests/m1_fix4_battery_raw.json $S/pooled_a5.json`
  - `python $S/levels_a5.py $S/levels_a5.json`
  - `python $S/capacity_a5.py 30000 $S/capacity_M30000_v2.json`; `python $S/cap_summary_a5.py $S/capacity_M30000_v2.json $S/capacity_summary.json`; `python $S/cap_cascade_a5.py $S/capacity_M30000_v2.json $S/cap_cascade.json`
  - `PYTHONHASHSEED={0,1,987654} python $S/repro_a5.py > $S/repro_h*.txt`, compared with `cmp`
  - `python $S/exclusion_a5.py`; `python3 $S/build_final_a5.py > $S/final_table.md`

## 1. Result

- **Keys:** 0 mismatches in 304,500 items: 10,500 per lineage across 29 lineages, every level, two seeds and two hash seeds. 0 solver errors in the final runs. That includes the five repaired lineages and `average_missing_r4`, which the audit-4 solver could not read.
- **Wording:** 0 items with no unique answer under the stated convention, in all 304,500 items (checks in section 3).
- **Cheap rules (R-24, R-31, R-32, R-34):** all 29 **STAY** at 0.15 two-sided. The largest pooled counted excess is +0.086 (`last_digit_power`, audit-3 `exp_mod_p`, level 0). Next come grid_perimeter at -0.087 (`a3:bbox`, L2) and median_list at +0.082. In absolute value, grid_perimeter's -0.087 is the largest.
- **Rules not counted:** six lineages would drop if the rules classed as "correct procedure" counted: consecutive, division_counting, finite_differences, gcd_lcm, prime_factors and ratio_share. I checked each rule. All six are the procedure, or the procedure plus a guess of which person is asked, not a shortcut (section 4.3). gcd_lcm keeps its construct-validity issue: a false general rule is exact on 100 % of items at levels 3-6.
- **NEW rules:** nothing above 0.15 except my "share of the first or last named person" rules on ratio_share (+0.53). Those belong to the same not-counted class as largest_share.
- **Levels:** no identical level pair in any of the 29 lineages, and the distributions of adjacent levels differ. The stated parameter rises (section 5). gcd_lcm's mean log answer dips from level 2 to level 3.
- **Capacity, as written:** the implementer's eight are confirmed on the audit-4 structural key, with identical failing levels at a fresh seed. On the text key the builder de-duplicates on, only three fail: consecutive, percent_change and rectangle. Read with "the smaller part decides", tip_split L0 fails as well. If the failing lineages were dropped and the partition recomputed until stable, 16 clusters would remain on the audit-4 key (S3 lost) and 17 on the text key.
- **Capacity, per-cluster builder (hypothetical):** S1 fails equal share at L0-2 on every key. S3 fails equal share at L0-1 on the audit-4 key. prime_factors L0 Chao1 is 30,913 against 31,000 at my seed, which is at the edge.
- **Reproducibility:** same seed gives byte-identical items under PYTHONHASHSEED 0, 1 and 987654.
- **Exclusions:** the dropped lineages are excluded from the loaders, the cluster map, the manifest and `core.REGISTRY`. They are still present in the round-3 fixtures, and no fix-4 fixture set exists.

## 2. Per-lineage table

Columns:
- **Key mismatches / n:** text solver against the stored key, over both key runs.
- **No unique answer:** section 3.
- **Largest pooled excess:** largest |pooled excess| over counted rules (R-31) and levels.
- **Verdict:** at 0.15 two-sided.
- **Levels:** identical level pairs, and whether the observed maximum of the stated parameter rises strictly ("see note" = section 5).
- **Capacity as written:** failing levels for the text key and the audit-4 key, under the own-part reading and the smaller-part reading (section 6). "pass" means no failing level.
- **Per-cluster builder (hypothetical):** bases failing for the lineage's cluster at G = 8 (demand 31,000), text key / audit-4 key.

| lineage | cluster | key mismatches / n | no unique answer | largest pooled excess (rule, level) | verdict 0.15 | levels: identical pairs; stated parameter max rising | as written, text key (own part / smaller part) | as written, audit-4 key (own part / smaller part) | per-cluster builder (hypothetical), G=8 text / a4key |
|---|---|---|---|---|---|---|---|---|---|
| `ages` | S1_linear_solve | 0 / 10,500 | 0 / 10,500 | +0.022 (a4:sum_over_k_plus_1, L6) | STAYS | none; yes | pass / pass | L0,1,2 / L0,1,2 | equal_share L0,1,2 / equal_share L0,1,2 |
| `arithmetic_series` | S7_step_rule | 0 / 10,500 | 0 / 10,500 | -0.003 (a3:last_day_only, L0) | STAYS | none; yes | pass / pass | pass / pass | pass / pass |
| `average_missing` (r4) | S1_linear_solve | 0 / 10,500 | 0 / 10,500 | +0.008 (a3:target_mean_rounded, L0) | STAYS | none; yes | pass / pass | pass / pass | equal_share L0,1,2 / equal_share L0,1,2 |
| `change_ways` | S5_unbounded_table | 0 / 10,500 | 0 / 10,500 | -0.036 (a4:T_over_min_coin, L0) | STAYS | none; see note | pass / pass | pass / pass | pass / pass |
| `clock_duration` (r4) | clock_duration | 0 / 10,500 | 0 / 10,500 | -0.015 (a3:span_incl_waits, L0) | STAYS | none; yes | pass / pass | pass / pass | pass / pass |
| `consecutive` | S1_linear_solve | 0 / 10,500 | 0 / 10,500 | +0.000 (echo_best_position, L0) | STAYS | none; yes | L0,1 / L0,1 | L0,1 / L0,1 | equal_share L0,1,2 / equal_share L0,1,2 |
| `crt_congruence` | crt_congruence | 0 / 10,500 | 0 / 10,500 | +0.054 (a3:largest_mod_remainder, L0) | STAYS | none; see note | pass / pass | pass / pass | pass / pass |
| `division_counting` | division_counting | 0 / 10,500 | 0 / 10,500 | -0.066 (echo_best_position, L0) | STAYS | none; yes | pass / pass | pass / pass | pass / pass |
| `finite_differences` (r4) | finite_differences | 0 / 10,500 | 0 / 10,500 | -0.002 (a4:echo_pos, L0) | STAYS | none; yes | pass / pass | pass / pass | pass / pass |
| `fraction_remainder` | S3_multiplicative_chain | 0 / 10,500 | 0 / 10,500 | +0.017 (a4:spends_not_left, L6) | STAYS | none; yes | pass / pass | L0,1,2,3,4,5,6 / L0,1,2,3,4,5,6 | pass / equal_share L0,1 |
| `gcd_lcm` (r4) | gcd_lcm | 0 / 10,500 | 0 / 10,500 | -0.022 (a4:smallest_pairwise_gcd, L5) | STAYS | none; yes | pass / pass | pass / pass | pass / pass |
| `grid_perimeter` | S6_exposed_faces | 0 / 10,500 | 0 / 10,500 | -0.087 (a3:bbox, L2) | STAYS | none; yes | pass / pass | L0 / L0 | pass / pass |
| `inclusion_exclusion` | inclusion_exclusion | 0 / 10,500 | 0 / 10,500 | -0.036 (a3:any_ignore_overlap, L0) | STAYS | none; yes | pass / pass | pass / pass | pass / pass |
| `last_digit_power` | last_digit_power | 0 / 10,500 | 0 / 10,500 | +0.086 (a3:exp_mod_p, L0) | STAYS | none; yes | pass / pass | pass / pass | pass / pass |
| `linear_equation` | S1_linear_solve | 0 / 10,500 | 0 / 10,500 | -0.016 (a3:ignore_constant, L0) | STAYS | none; yes | pass / pass | pass / pass | equal_share L0,1,2 / equal_share L0,1,2 |
| `median_list` | median_list | 0 / 10,500 | 0 / 10,500 | +0.082 (im:mode_value, L0) | STAYS | none; yes | pass / pass | pass / pass | pass / pass |
| `mixture` (r4) | S2_weighted_sum | 0 / 10,500 | 0 / 10,500 | +0.033 (a3:unweighted_mean, L4) | STAYS | none; yes | pass / pass | pass / pass | pass / pass |
| `painted_cube` | S6_exposed_faces | 0 / 10,500 | 0 / 10,500 | -0.007 (a3:inner_block_on_unpainted_bottom, L3) | STAYS | none; yes | pass / pass | pass / pass | pass / pass |
| `percent_change` | S3_multiplicative_chain | 0 / 10,500 | 0 / 10,500 | +0.006 (a3:first_step_only, L5) | STAYS | none; yes | L0,1 / L0,1 | L0,1,3 / L0,1,3,4 | pass / equal_share L0,1 |
| `pipes_work` | S1_linear_solve | 0 / 10,500 | 0 / 10,500 | -0.028 (im:ignore_drain, L0) | STAYS | none; yes | pass / pass | L0,1,2 / L0,1,2 | equal_share L0,1,2 / equal_share L0,1,2 |
| `prime_factors` | prime_factors | 0 / 10,500 | 0 / 10,500 | -0.077 (im:omega_plus_one, L0) | STAYS | none; yes | pass / pass | pass / pass | pass / chao1 L0 |
| `quadratic_area` | quadratic_area | 0 / 10,500 | 0 / 10,500 | -0.007 (a3:quarter_perimeter, L3) | STAYS | none; yes | pass / pass | pass / pass | pass / pass |
| `ratio_share` | S3_multiplicative_chain | 0 / 10,500 | 0 / 10,500 | +0.057 (a3:equal_split, L0) | STAYS | none; yes | pass / pass | L0 / L0 | pass / equal_share L0,1 |
| `rectangle` | S1_linear_solve | 0 / 10,500 | 0 / 10,500 | +0.014 (a4:echo_pos_offset, L0) | STAYS | none; yes | L0,1,2,3,4,5,6 / L0,1,2,3,4,5,6 | L0,1,2,3,4,5,6 / L0,1,2,3,4,5,6 | equal_share L0,1,2 / equal_share L0,1,2 |
| `recurrence_iterate` | S7_step_rule | 0 / 10,500 | 0 / 10,500 | +0.006 (a4:echo_pos_offset, L0) | STAYS | none; yes | pass / pass | pass / pass | pass / pass |
| `shopping` | S2_weighted_sum | 0 / 10,500 | 0 / 10,500 | +0.028 (a3:ignore_counts, L0) | STAYS | none; see note | pass / pass | pass / pass | pass / pass |
| `speed_distance` | S2_weighted_sum | 0 / 10,500 | 0 / 10,500 | +0.034 (a4:median_speed, L2) | STAYS | none; see note | pass / pass | pass / pass | pass / pass |
| `tiered_pricing` | tiered_pricing | 0 / 10,500 | 0 / 10,500 | -0.005 (a3:all_at_first_rate, L3) | STAYS | none; yes | pass / pass | pass / pass | pass / pass |
| `tip_split` | S3_multiplicative_chain | 0 / 10,500 | 0 / 10,500 | -0.001 (a4:tip_only_per_person, L0) | STAYS | none; yes | pass / L0 | pass / L0 | pass / equal_share L0,1 |

## 3. Keys and wording

- 304,500 items checked: 500 per lineage and level at 2611251 (hash seed 0) plus 1,000 at 2611257 (hash seed 1). 0 key mismatches, 0 solver errors, 0 items with no unique answer (`keys_n500.txt`, `keys_n1000_seed2611257_h1.txt`).
- My failed attempt: the attempt-1 solver could not read item names with a hyphen ("yo-yos") in shopping, giving 43 errors in a 40-per-level trial (`../keys_trial_n40.json`). That was my error, not a key error. I fixed it in attempt 2 and kept attempt 1 as `solve_text_a5_attempt1.py`.
- What "no unique answer" checks, item by item:
  - a non-integer exact value where a whole number is asked;
  - more than two decimals where "no more than two decimal places" is the only rounding rule;
  - inconsistent Venn counts, i.e. a negative region or a union above the total;
  - printed polynomial terms that are not on one polynomial of the stated degree, or a lower degree than stated;
  - more or fewer than one whole root in quadratic_area;
  - more or fewer than one unit count in a tiered bill;
  - no CRT solution, or a remainder not below its divisor;
  - a repeated name used in the ask (ages, ratio_share);
  - a needed mark outside 0..M (average_missing);
  - times not increasing within one day (clock);
  - a box dimension below 2 (painted_cube);
  - equal multipliers in two-sided linear equations;
  - a non-positive net filling rate (pipes);
  - "Answer with ..." absent.
- Minor wording, not key-changing: "all 2 flash together" in gcd_lcm k = 2; "1 kilograms" in mixture; nested commas in last_digit_power sums (already noted by audit 4).

## 4. Cheap rules

### 4.1 Method
- **Rule definitions:** read unchanged with importlib from `audit3_m1/shortcuts_a3.py` (`spec`), `audit4_m1/shortcuts_a4.py` (`mine`, `visible_class`) and the implementer's `studies.m0.m1_fix3_shortcuts.spec`.
- **Scoring:** re-implemented to the same definitions:
  - base = held-out most frequent answer, two folds by index parity;
  - rates over all items;
  - echo at the best fitted position;
  - audit-4 offset echo and mode by visible ask.
- **Check against the implementer's figures:** I recomputed all 3,190 implementer values at their own streams (a4 seed 17, own seed 410302, a3 seed 5, N = 2,000) and found 0 differences (`compare_repro.txt`). My attempt 1 had 1 difference (mixture L3 audit-3 echo, 0.000 against 0.002) because I broke ties in the audit-4 candidate order. That was my error, kept in `rules_a5_attempt1.py` and `compare_repro_attempt1.txt`.
- **Fresh run:** N = 4,000 per lineage and level at 2611252. All three rule sets were scored on the same items. The audit-3 rules raised on 0 survivor items.
- **Pooling (R-32):** item-weighted mean of (rate - base) over every measurement of the same rule definition:
  - im:X = implementer own (2,000) + implementer a4 copy (2,000) + mine (4,000);
  - a4:X and a3:X = implementer (2,000) + mine (4,000);
  - echo = implementer own + implementer a3 + mine.
- **Classes (R-31):** the rules not counted are exactly `short_summary_a4.PROC` (parsed from the file). I added the audit-3 rule with the same name and definition for the same lineage: `largest_share`, `largest_le_sqrt`, `k_minus_remainder_ignores_exact_fit`, `next_term_only` and `fermat_misapplied_e_mod_p_plus_1`. That addition is mine, by name. Within-shape rates are reported but not counted (R-34).

### 4.2 Result
All 29 STAY. Full per-level values are in `pooled_a5.txt` and `pooled_a5.json`. Largest pooled counted |excess| per lineage:

| lineage | value | rule, level |
|---|---|---|
| grid_perimeter | -0.087 | a3:bbox, L2 |
| last_digit_power | +0.086 | a3:exp_mod_p, L0 |
| median_list | +0.082 | im:mode_value, L0 |
| prime_factors | -0.077 | im:omega_plus_one, L0 |
| division_counting | -0.066 | echo, L0 |
| ratio_share | +0.057 | a3:equal_split, L0 |
| crt_congruence | +0.054 | a3:largest_mod_remainder, L0 |
| every other lineage | within ±0.036 | |

The implementer's own largest was +0.093 (last_digit_power L0); pooled it is +0.086.

### 4.3 Rules not counted (the six above 0.15)
Pooled maxima, and my judgement of whether each rule is the registered procedure or a shortcut:
- **consecutive, `im:mean_plus_step`: +0.501 (L1).** For 3 numbers (L0-1) it is the procedure: middle = S/3, then add the step. For 4 numbers (L2-3) it is a wrong rule that is right through round-half-even coincidence, +0.12/+0.13, under the bound. It is 0 at L4-6. Agree: not a shortcut.
- **division_counting, `k - (N mod k)`: +0.438 (L6).** The procedure without the exact-fit case; 96-97 % right within the bus items. Agree.
- **finite_differences, `next_term_when_asked_later`: +0.505 (L3).** Exactly 100 % within the m+1 asks at L0-4 (one extension of the difference table, which is the procedure). It is 0 % at L5-6 (degree 3). Agree.
- **gcd_lcm, `product_over_gcd_of_all` (k = 2): +0.493 (L1).** The textbook lcm. Agree. The false general rules product/gcd^(k-1) and product/lcm^(k-1) are exact on 100 % of items at L3-6 (pooled +0.47 to +0.49). They need the gcd or lcm of all values, so they are not cheaper than the procedure. A model holding the misconception still scores full marks at L3-6. This construct-validity issue was not repaired in fix 4. PENDING LEAD REVIEW.
- **prime_factors, `largest_le_sqrt`: +0.192 (L5).** It needs trial division up to sqrt(n). Within the "largest" ask it is right 87 % (L0) to 99 % (L6) of the time, so the step that checks for a large prime cofactor is almost never exercised at high levels. Agree it is the procedure; construct note.
- **ratio_share, `largest_share` / `smallest_share`: +0.532 (L1).** A person guess on top of the full procedure. The observed share of items where the asked person holds the largest part equals the uniform expectation: L0 0.525 against 0.531, L6 0.285 against 0.282. So there is no selection tell. Agree.
- `last_digit_power`'s not-counted Fermat rule reads +0.114 (L0), under 0.15.

### 4.4 NEW rules (mine, fresh seed only, not pooled, reported separately)
Rules:
- `new:one_op_two_numbers`: x op y on printed numbers at the first 6 and last 3 positions, op in + - * /, the best (i, j, op) fitted on one half and scored on the other;
- `new:mode_by_template`: most frequent answer per masked text template, held out;
- `median_midrange`;
- `avg_ignore_count`;
- `clock_hhmm_subtract`: clock times read as plain numbers;
- `fd_deg2_last3`: degree-3 items extrapolated with a constant second difference;
- `ratio_first_named` / `ratio_last_named`.

Results:
- Above 0.15: only ratio_share's first/last-named rules, +0.531 (L0). They are a person guess plus the procedure, the same class as largest_share, so not a cheap rule.
- Next largest:
  - linear_equation one-op (c1 - c2), +0.110 (L3). It is exact when the two multipliers differ by 1.
  - grid_perimeter template mode, +0.101 (L0).
  - prime_factors template mode, +0.062.
  - Everything else is at most 0.05.

## 5. Levels
How I tested:
- **No-op test:** 300 items built from the same random stream at each pair of levels, all 21 pairs; a pair is flagged if every item is byte-identical.
- **Parameter profile:** 2,000 items per level. For every structured field (and for list lengths and maxima) I recorded the observed maximum and mean. I also tracked the stated parameter's observed maximum, the mean and median log10 answer, and the count of printed numbers.

Results:
- No identical pair in any of the 29 lineages.
- Every adjacent pair of levels differs in at least one feature distribution.
- The stated parameter's observed maximum rises strictly in 25 lineages. For the repaired lineages:
  - mixture: 30 … 66;
  - average_missing: 100 … 160;
  - clock_duration: 150 … 210;
  - gcd_lcm answer maximum: 89,300 … 8,259,300;
  - finite_differences answer maximum: 954 … 4,819.
- The four "see note" lineages:
  - change_ways: the stated range (x_i up to 5 + 2L) rises; the observed T maximum is noisy at L6, while the mean T and the mean log answer rise strictly.
  - crt_congruence: the pair (number of conditions, largest modulus) rises in lexicographic order: (2, 60), (2, 70), (2, 80), (3, 36), (3, 40), (4, 44), (4, 48).
  - shopping: item lines 2, 3, 4, 4, 5, 5, 6, with the price and payment ranges rising.
  - speed_distance: legs 2, 2, 3, 3, 4, 4, 5, with the maximum speed 60 … 120 strictly rising.
- gcd_lcm: mean log10 answer by level is 2.558, 2.701, 2.923, **2.745**, 2.918, 3.162, 3.329; the implementer measured 2.833 → 2.813 from L2 to L3. The dip comes from the gcd ask, whose cap falls from 60 to 24 when k goes from 2 to 3. The stated ceiling, the observed maximum and k all rise.
- Answers in last_digit_power and shopping do not grow in size (remainder mod p, and change), as expected.
- Not measured: difficulty for a reader. PENDING LEAD REVIEW on whether "ceiling of the answer" is an acceptable difficulty parameter for gcd_lcm and finite_differences.

## 6. Capacity

### Setup
- M = 30,000 draws per lineage and level at 2611254. n_eff = M(M-1)/(2P); with no collision I use the bound M(M-1)/6. Chao1 is a second estimate.
- Three keys:
  - **TEXT:** `core.text_hash`, the key `draw_items` de-duplicates on. This is the brief's unit.
  - **STRUCT:** the structured JSON, my own key.
  - **audit-4 key:** `capacity_a4.key`, read unchanged; the implementer's basis.
- 17 clusters (the audit-4 map typed from AUDIT4_M1 section 5, minus the drops; it equals the manifest's map), so G = 8: D(8) = 31,000 and D(7) = 35,300.
- The family partition rule (seed 400004) applied to the survivors' 18 families gives part A 14 lineages and part B 15.

### (i) `core.generate_pool` as written: per-lineage allocation
The builder cannot pool these lineages at all, because `part_lineages` reads `core.REGISTRY['M1']`, which holds the 16 batch-1 lineages and no fix-3 or fix-4 id. Below is its allocation rule applied to the survivors.

Failing lineages by demand reading and key:

| reading (demand per lineage) | text key | audit-4 key |
|---|---|---|
| own part count (A 18,150; B 17,010) | consecutive L0-1, percent_change L0-1, rectangle L0-6 | **the implementer's eight, confirmed with identical levels**: ages L0-2, consecutive L0-1, fraction_remainder L0-6, grid_perimeter L0 (17,795), percent_change L0, 1, 3, pipes_work L0-2, ratio_share L0, rectangle L0-6 |
| smaller part decides (R-30; 18,150 in both parts) | the three above + tip_split L0 (17,617) | the eight + tip_split L0 |
| G one lower (A 13 lineages: 19,470; B 14: 18,150) | 4 (as the line above) | 9 (as the line above) |
| per-cluster demand applied to each lineage (31,000; 35,300) | 5 (+ pipes_work) | 11 (+ arithmetic_series, mixture); 13 at 35,300 |

The struct key falls in between: 5 fail under the own-part reading.

**If every failing lineage were dropped:**

| key, reading | single pass | iterated until no lineage fails |
|---|---|---|
| audit-4 key, own part | 17 clusters (each cluster keeps a member) | 19 lineages, **16 clusters**: the partition changes, then tip_split and mixture fail, and S3 is lost |
| audit-4 key, smaller part | 16 clusters | 18 lineages, 16 clusters |
| text key | 17 clusters | 25 lineages (own part) or 24 lineages (smaller part), 17 clusters either way |

See `cap_cascade.txt`.

### (ii) Per-cluster builder: HYPOTHETICAL, no such builder exists
Bases as the implementer used them: mixture k^2 / sum(1/n_i), Chao1 sum, equal share k x min n_i.

| key, G | demand | failing clusters |
|---|---|---|
| text, G = 8 | 31,000 | S1 equal share L0-2 (21,738 / 25,353 / 29,202; rectangle) |
| text, G = 7 | 35,300 | S1 equal share L0-3 |
| audit-4 key, G = 8 | 31,000 | S1 equal share L0-2; S3 equal share L0-1 (24,714 / 29,443; fraction_remainder); prime_factors Chao1 L0 (30,913) |
| audit-4 key, G = 7 | 35,300 | S1 L0-3; S3 L0-2; prime_factors L0 on all bases |

Every other cluster passes on every basis. The implementer reported prime_factors passing at G = 8 (Chao1 31,275, n_eff 31,055). Mine is n_eff 31,093 (pass) and Chao1 30,913 (fail), against audit 4's exact 31,236. This is sampling noise at a +0.8 % margin.

## 7. Reproducibility
`repro_a5.py`: 300 items per lineage and level, SHA-256 over `Item.to_json()`. Three fresh processes under PYTHONHASHSEED 0, 1 and 987654 produce byte-identical output; total `04b87cae…a4229a6`.

## 8. Exclusions (`exclusion.txt`)
PASS:
- `load_registered` excludes every NOT REGISTERED lineage (round 3 and round 4) and equals the manifest's 29;
- min_cost_packs and the six replaced r3 ids are absent from `load_all`;
- `strict_clusters(load_registered())` gives 17 clusters with no dropped id;
- `core.REGISTRY['M1']` holds no fix-3 or fix-4 id;
- the manifest's survivor, cluster and capacity sections name no dropped id;
- the as-written partition counts only the 29.

FAIL:
- `studies/m0/fixtures/m1_fix3` still holds coins_r3, pigeonhole_worst_case_r3 and mode_tally_r3, plus the r3 versions of the six replaced lineages;
- there is no fix-4 fixture set. The implementer disclosed this.

The implementer's measurement scripts sample the dropped lineages with `--all`. That is a measurement of attempts, not part of the set.

## 9. Final list (on this measurement; nothing is registered)

**Rule bound 0.15:** 29 of 29 lineages stay, in 17 clusters:
- S1_linear_solve: ages, average_missing_r4, consecutive, linear_equation, pipes_work, rectangle
- S2_weighted_sum: mixture_r4, shopping, speed_distance
- S3_multiplicative_chain: fraction_remainder, percent_change, ratio_share, tip_split
- S5_unbounded_table: change_ways
- S6_exposed_faces: grid_perimeter, painted_cube
- S7_step_rule: arithmetic_series, recurrence_iterate
- Singletons: clock_duration_r4, crt_congruence, division_counting, finite_differences_r4, gcd_lcm_r4, inclusion_exclusion, last_digit_power, median_list, prime_factors, quadratic_area, tiered_pricing

No lineage drops on the counted rules. Under R-36 the eight capacity failures (audit-4 key) stay held: ages, consecutive, fraction_remainder, grid_perimeter, percent_change, pipes_work, ratio_share, rectangle. With them held aside, 21 lineages stand without a capacity condition, and they still cover all 17 clusters.

## 10. Discrepancies (including my own)
1. **Implementer's battery:** 3,190 values reproduced with 0 differences. The as-written eight and their failing levels were reproduced at a fresh seed.
2. **Capacity unit (not a disagreement, a different key):** on the text key only 3 lineages fail as written, not 8. Which unit counts (R-16) is not ruled. PENDING LEAD REVIEW.
3. **The R-30 "smaller part decides" reading of the as-written demand** adds tip_split, so all four S3 members fail. The implementer used each part's own count. PENDING LEAD REVIEW.
4. **Iterated drop:** 16 clusters on the audit-4 key, against the implementer's single-pass 17.
5. **prime_factors L0 Chao1** under the hypothetical builder: fail at my seed, pass at theirs; it sits at the noise edge.
6. **gcd_lcm level dip:** confirmed, larger at my seed (2.923 → 2.745).
7. **Audit 4's PROC list** includes `im:next_term_only` although its own reason says "kept as a rule". Its value is about -0.002, so it has no effect.
8. **Fixtures:** not regenerated for round 4 (section 8).
9. **My own slips:**
   - solver attempt 1 (hyphen; section 3);
   - rules attempt 1 (tie order; section 4.1);
   - my first edit adding the audit-4 key to the capacity scripts failed with a quoting error, so the rerun wrote v1's numbers into `capacity_M30000_v2.json`. That file was then overwritten by the real v2 run on the same items. The v1 numbers remain in `capacity_M30000.json`, and the edit script is `../edit_cap_v2.py`.
10. **HEAD moved during the audit** (`7cd0ac5a`, another session); the audited bytes are unchanged.

## 11. Not verified
- Exact support: only sampled n_eff and Chao1.
- Model behaviour of any kind.
- Whether difficulty rises for a reader.
- The M0 test suite: I did not run pytest.
- The cross-evaluation map.
- Fixture hashes.
- Whether the as-written builder would actually draw the pools; it cannot run on these lineages at all (section 6).

## 12. PENDING LEAD REVIEW
- The capacity unit: text or structural.
- The as-written demand reading: each part's own count or the smaller part, and whether to iterate after drops.
- gcd_lcm's exact false general rule at k >= 3.
- Whether "ceiling of the answer" is an acceptable rising parameter for gcd_lcm and finite_differences.
- The prime_factors construct note: the large-cofactor case almost never occurs.
- The pool builder (R-36).
- The fix-4 fixture set.

Astra review: NOT_PERFORMED
