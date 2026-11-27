# AUDIT_M0_M1_1 — independent audit of the M1 lineages after authoring batch 1

- Auditor model (session metadata): Claude Opus 5.5, `claude-opus-5-5`, run as the `arbor-auditor` context.
- **Astra review: NOT_PERFORMED.** This is independent engineering and mathematical evidence. It is not Astra validation and not human approval.
- Audited tree: worktree `agent-a0c9d741ea96ce52f`, branch `claude/m0-impl`, HEAD `1b33b7b2`. Nothing in the repository was written. All files listed here are in this folder (`experiments/_scratch/m0_lineage_audit_m1_20261125/`, git-ignored).
- Environment: macOS (Darwin 27.2.0, arm64), Python 3.12.14 through `uv run --locked --offline`, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONHASHSEED=0` for every generator run, cwd = the audited worktree, `PYTHONPATH=.`. No model, download or training was used.
- Order of work: generators and rendered items were read, then `JUDGEMENT_1_clusters.txt` was written and hashed (SHA-256 `b07cbbb3…644978`, 14:20Z). After that came solvers, shortcuts and capacity, and then `JUDGEMENT_2_quality_shortcuts_capacity.txt` was hashed (`bf6aa15a…51b6db`). Only after both hashes did I read the author's manifest (step 8). `NOTES*.md` were never read.
- **Contamination disclosure.** Generator docstrings name three "borderline" pairs. A grep of `M1_BATCH1_SCHEMA.md` headings also showed the per-lineage firmness labels. I saw both before I formed my pairwise judgement. Nothing else from the author's opinions was seen before the hashes.

## 0. Rule as applied

ADR-0033 §6.2, quoted: *"Each rule shape is registered with a lineage: the hand-written base rule, a distinct solution procedure, from which it derives. Shapes made mechanically from one base rule (by changing parameters, order, negation, names or surface frame) share a lineage. **The cluster, for G and for every bootstrap, is the lineage.**"*

Lead ruling: read strictly. The general algorithm is the procedure. Number system, constraint mix, final question, names, order, negation and surface frame are parameters.

The ambiguous sentence is *"a distinct solution procedure"*: at what granularity is "procedure" read?

- **STRICT** merges whenever, after translating the words, two lineages run one general algorithm and differ only in the lead's listed parameters.
- **LENIENT** merges only mechanical variants on the ADR's own list, with the core computation and the final question unchanged.

## 1. Procedure per lineage (37)

Rendered with `render_samples.py`: 3 items per level × 7 levels × 37 lineages, seed 777001, output in `samples.txt`. The fixtures (20 per level) were also read for the new 21.

| Lineage | Procedure a solver must run |
|---|---|
| shopping (E) | Σ quantity×price, then subtract from the amount paid |
| speed_distance (E) | Σ hours×speed; for 40 % of L≥2 items, ÷ Σ hours (weighted mean) |
| pipes_work (E) | V ÷ (a+b−drain): solve r·t = V |
| percent_change (E) | multiply by successive factors (1 ± p/100) |
| tip_split (E) | ×(1+tip/100), ÷ n |
| ratio_share (E) | total ÷ Σparts × part_i |
| mixture (E) | weighted mean (xa+yb)/(x+y), +2 at L≥3 |
| linear_equation (E) | solve kx+m = n, or kx+m = jx+e |
| consecutive (E) | solve n·a + step·n(n−1)/2 = S, report the last term |
| ages (E) | solve (k+1)b + 2t = S |
| average_missing (E) | n·mean − Σ scores |
| rectangle (E) | w = P/(2(k+1)), report k·w² |
| arithmetic_series (E) | sum of an AP (formula, or day-by-day accumulation) |
| coins (E) | 2×2 linear system (count and value) |
| clock_duration (E) | Σ (arrival − departure) in hh:mm, in minutes |
| fraction_remainder (E) | n·(1−1/a)(1−1/b) |
| inclusion_exclusion | inclusion–exclusion over 2 or 3 sets: none / any / exactly one / exactly two |
| binomial_choose | C(n,k); C(n−1,k−1) with a forced member; C(x,j)·C(y,k−j) |
| slot_permutations | product rule over digit slots: repetition, leading zero, parity of the last digit |
| change_ways | count non-negative solutions of c₁x + c₂y + c₃z = T |
| pigeonhole_worst_case | 1 + Σ min(nᵢ, k−1), or total − min + 1 |
| gcd_lcm | gcd or lcm of 2–4 numbers |
| crt_congruence | least x with x ≡ rᵢ (mod mᵢ), coprime moduli |
| prime_factors | factorise, then τ(N) / largest p / Σ distinct p / Ω(N) |
| last_digit_power | last-digit cycle (e mod 4), combined by sum or product mod 10 |
| quadratic_area | positive root of x(x+d) = A, x²+(x+d)² = S, or sides from P and A |
| digit_puzzle | generate-and-test over all 2- or 3-digit numbers against digit clues |
| pythagoras | a²+b² = c² (hypotenuse, a leg, or the perimeter) |
| grid_perimeter | 4·cells − 2·shared edges of a row-convex polyomino |
| painted_cube | count cubes with exactly f exposed painted faces (bottom optionally unpainted) |
| min_cost_packs | least cost of buying at least N from singles and 2–3 pack sizes (unbounded min-cost cover) |
| tiered_pricing | marginal-rate split over tiers, or the inverse (bill → units) |
| recurrence_iterate | iterate a Fibonacci-like, affine, or +position recurrence |
| finite_differences | extend a degree-2 or degree-3 polynomial by its difference table |
| median_list | sort (expanding a frequency table) and take the middle value or the mean of the two middle values |
| mode_tally | tally, then report the argmax value or its count |
| division_counting | ceiling and floor division (nested ceil, multiples in a range, empty seats) |

## 2. Pairwise sameness: all 666 pairs

The full table is in `pairs_666.tsv` (script `pairs_table.py`). It has 1 merge under both readings, 33 merges under strict only, 19 near-misses kept apart, and 613 distinct pairs.

**Merges (strict):**
- **S1 linear-solve** = {linear_equation, ages, consecutive, average_missing, pipes_work, rectangle, coins}. Each reduces to isolating an unknown in a linear relation. Coins and ages substitute one unknown first. Rectangle and consecutive differ in the final question.
- **S2 weighted-sum** = {shopping, speed_distance, mixture}. Σ wᵢxᵢ; mixture and speed_distance's average shape divide by Σw. Shopping subtracts the sum from the amount paid.
- **S3 multiplicative-scaling** = {percent_change, fraction_remainder, tip_split, ratio_share}. A chain of rational factors. Percent versus unit fraction is the number system. ratio_share is the weakest member (strict only).
- **S4** binomial_choose + slot_permutations: counting by the product rule; ordered versus unordered and the restrictions are the constraint mix. Strict only.
- **S5** change_ways + min_cost_packs: the same unbounded table over amounts; counting versus minimising is the final question. Strict only.
- **S6** grid_perimeter + painted_cube: "for each unit cell, count faces not shared with the shape" answers both; 2-D versus 3-D and the final question differ. Strict only.
- **S7** arithmetic_series (E) + recurrence_iterate (N): add_index is exactly an AP sum, and both are "apply the step rule n times". Strict only; this is the only cross merge between existing and new.

**Merge (lenient):** percent_change + fraction_remainder. "Spend 1/a, then 1/b of what is left" is "fall by 100/a %, then by 100/b %": number system plus surface frame.

**Near-misses kept apart (both readings):**
- median/mode (sort-and-select vs tally)
- change_ways/digit_puzzle
- last_digit_power/crt
- gcd_lcm/prime_factors
- gcd_lcm(lcm)/crt
- recurrence/finite_differences (the latter must infer the rule)
- quadratic_area/pythagoras
- quadratic_area/rectangle
- tiered_pricing/shopping
- coins/change_ways
- division_counting/pipes_work
- pigeonhole/division_counting
- clock_duration/shopping
- tip_split/ratio_share (lenient)
- arithmetic_series/consecutive (lenient)
- min_cost/tiered
- average_missing/median
- average_missing/mode
- finite_differences/arithmetic_series

**Distinct-cluster counts:**

| | Existing 16 | New 21 | Overall 37 |
|---|---|---|---|
| **Strict** | **5** | **18** | **22** |
| **Lenient** | **15** | **21** | **36** |

My central estimate is 6 / 21 / 27: S1, S2, S3 without ratio_share, plus the lenient merge.

## 3. Cross-evaluation duplicates (finding for the lead; not merged)

**Strong** (same procedure, near-identical question):
- M1.crt_congruence = R2.crt_smallest
- M1.gcd_lcm = R2.gcd_euclid (gcd and lcm asks)
- M1.prime_factors = R2.prime_factor_query ("What is the largest prime number that divides N exactly?" appears verbatim in both)
- M1.division_counting (multiples shape) = R2.multiples_between (same formula and near-identical wording)
- M1.inclusion_exclusion = R1.venn_counting
- M1.last_digit_power = R2.modular_power with m = 10

**Moderate:**
- min_cost_packs ~ R2.coin_change_min
- median_list ~ R2.kth_smallest

**Code-tracing twins in C1:**
- change_ways ~ C1.coin_change_table (combos shape)
- gcd_lcm ~ C1.euclid_gcd
- last_digit_power ~ C1.fast_power
- recurrence_iterate ~ C1.fib_like

**Related partition finding.** Under the registered M1 family partition (seed 400004), strict clusters S1, S2 and S3 each span part A and part B. For example, ages, average_missing, coins and pipes_work are in A, while linear_equation, consecutive and rectangle are in B. So part B is not held out at the procedure level, either inside M1 or across evaluations. **PENDING LEAD REVIEW.**

## 4. Quality of the 21 new lineages

**Keys.** My own solvers (`audit_solvers.py`) read only the question text and mostly use a different method from the generator: brute force, Lagrange interpolation, closed forms, adversary simulation.
- Fixtures: **2,940 of 2,940 agree with the key** (`fixture_check_attempt2.txt`). Attempt 1 is kept in `fixture_check_attempt1.txt`: 11 parser errors on "yo-yo", my mistake.
- Generated items: 147,000 more (1,000 per level, seed 777003) were re-solved with **0 disagreements**.
- **No wrong key under the stated reading. Every lineage was covered.**

**Ambiguous items** (key correct only under one reading):
- **slot_permutations, leading zero.** When 0 is among the digits and no leading-zero rule is stated, the key counts strings that start with 0 as "s-digit numbers". Under the ordinary definition this key is wrong.
  - Fixture ids (13 of 140): 0/13, 0/18, 1/7, 1/9, 2/18, 3/7, 3/10, 4/2, 4/14, 4/18, 5/10, 6/4, 6/16. For example, 0/13 has key 405; the ordinary reading gives 360.
  - In generated items this affects 9–13.5 % per level.
- **last_digit_power, the gloss.** "(the power means 23 multiplied by itself 295 times)" read literally means 23^296. That reading changes 116 of 140 fixture keys. Use R2's wording instead: "a product of 295 factors, each equal to 23".
- **digit_puzzle, reversal with a trailing zero** (minor). This needs 089 to be accepted as "a number". Fixture ids: 1/12, 2/15, 4/15, 4/17, 6/5, 6/9, 6/19.

**Keys printed in the question** (fixtures):
- mode_tally 97/140 and median_list 84/140: inherent, because the answer is a value from the list.
- change_ways 18, prime_factors 8.
- Two or fewer for every other lineage.

**Generator defects:**
- **D1. gcd_lcm's mix collapses.** gcd items are 0.65–0.69 of L0–L2, 0.01 of L3–L4 and **0.00 of L5–L6** (`shape_mix_N2000.txt`). The k≥3 gcd rejections almost always fail, and the Retry redraws the ask. L3–L6 is in effect an lcm-only lineage. My ad-hoc gcd check crashed with ZeroDivisionError at L5 for exactly this reason (there were no gcd items).
- **D2. division_counting mix.** The multiples shape is only 0.07–0.11, crates 0.28–0.29, and empty_seats 0.60–0.65.
- **D3. last_digit_power rejection artefact.** The rejection pow(b,e,10) ≠ b mod 10 forces **even exponents for bases ending 4 or 9**, so those terms are always 6 and 1 (about 25 % of terms at t ≥ 2). At t = 1 the answer is never the base digit.
- **D4. Structural repeats inside the fixtures** (`fixture_dups_out.txt`):
  - binomial_choose: 28 of 140 items repeat another item's structure.
  - slot_permutations: 5 text-identical groups. Items 4/14 and 6/16 have the same text at L4 and L6.
  - digit_puzzle: 10 order-canonical repeats. Items 1/12 and 6/5 are the same puzzle at L1 and L6.
  - Smaller counts in pythagoras, prime_factors, quadratic_area, recurrence_iterate and grid_perimeter.

## 5. Shortcuts

Own code: `shortcuts_audit.py`, 1,000 items per level, the author's heuristics re-implemented, plus 5–10 of my own per lineage. Results are in `shortcuts_summary_v2_N1000.txt` and `shortcuts_out_N1000.json`. The two-sided comparison against counterfactual generators without the rejection is in `overshoot_audit.py` and `overshoot_N2000.txt`.

The screen I apply is the author's own display rule, rate ≥ max(0.25, 2×constant). It is not a registered threshold. Summariser v1 mis-tagged three procedure-equivalent heuristics as shortcuts; v2 corrects that, and both outputs are kept.

**Author's named worst cases, re-measured:**

| Lineage | Heuristic | Author | Mine |
|---|---|---|---|
| mode_tally | last number stated | 0.254 | 0.248 (L0), falling to 0.151 by L6 |
| last_digit_power | base last digit | 0.204 | 0.200 (max, at L3) |
| painted_cube | inner-block formula | 0.190 | 0.155–0.181 |

**New shortcuts above the screen.** Open numeric answers; the absolute exact-match rate is shown beside the most-frequent-answer rate.

| Lineage | Heuristic | Rate | Constant (most-frequent-answer) rate |
|---|---|---|---|
| **min_cost_packs** | greedy: largest pack as often as it fits, then the next pack, then singles | **0.41–0.46** (L0–L4), 0.255–0.270 (L5–L6) | 0.010–0.024 |
| min_cost_packs | best unit price × need, rounded up | 0.17–0.29 | 0.010–0.024 |
| **last_digit_power** | (last digit of base)^(last digit of exponent) | **0.335–0.435** | 0.15–0.22 |
| last_digit_power | square of the base's last digit | 0.32–0.37 (L0–L4) | 0.15–0.22 |
| **mode_tally** | the last value listed is the mode (or report its count) | **0.265–0.41** (above the screen at L1–L6) | 0.07–0.21 |
| **grid_perimeter** | bounding-box perimeter + 4 | **0.30–0.35** (L0–L3; above the screen at L2–L3) | 0.15–0.22 |
| grid_perimeter | 2·cells + 2 | 0.36–0.37 (L0–L1) | 0.15–0.22 |

The author's five naive plans for min_cost_packs do not include the greedy mix.

**Below the screen but at 4–8× the constant rate:**
- crt: largest modulus + its remainder, 0.17–0.21 at L0–L2.
- division_counting: floor the boxes, then ceil, 0.20–0.24. Note also that crates is a single ceiling, ceil(N/(k·m)), an identity.
- median_list: the mode of the table, 0.15–0.20 at L3–L6.

**Two-sided (overshoot): real rate versus the same generator without its rejection.**

| Lineage | Heuristic | Real | Without rejection |
|---|---|---|---|
| mode_tally | first repeated value | 0.08–0.14 | 0.36–0.50 |
| gcd_lcm | smallest pairwise difference | 0.000 | 0.22–0.33 |
| change_ways | T // biggest coin + 1 | 0.000 | 0.07–0.14 |
| median_list (table) | median of the distinct values | 0.000 | 0.25–0.34 |
| min_cost_packs | minimum of the five naive plans | 0.38–0.42 | ≈0.89 |
| min_cost_packs | "no naive plan reaches the optimum" | 0.58–0.62 | 0.11–0.24 |
| last_digit_power | answer = base digit (t = 1) | 0 | 0.25 |

How much these anti-cues can be exploited depends on how many candidate answers remain. For last_digit_power three candidates remain after the exclusion; for mode_tally the candidates are the list values. The mass the redraws displaced is what feeds the "last value" and "bbox+4" shortcuts.

## 6. Capacity

ADR-0033 §6.2, quoted: *"Capacity gate (G-gen). For every cluster and level, the number of distinct items the generator can produce is at least 10 times the number the pools demand. Otherwise engineering stop."*

"Distinct" is not defined there. The neighbouring bullets say "unique after normalisation", and the code's normalisation (NFKC, casefold, whitespace) counts a new name or setting sentence as a distinct item. **The text does not exclude the least favourable reading**, under which a name or setting change is not a new item. The ambiguous sentence is *"the number of distinct items the generator can produce"*.

The setting sentence alone gives 122 names × 24 towns × 4 wordings = 11,712 variants.

Demand at G = 300 is 1,800 per core level and 1,000 per reserve level. Results under the least favourable reading (`capacity_M4000.txt`, `capacity_v2_M4000.txt`; exact enumerations where stated):

| Lineage | Structural count L0…L6 | Fails at G = 300 |
|---|---|---|
| binomial_choose (exact) | 180 / 571 / 1,367 / 2,756 / 4,958 / 8,073 / 11,845 | **L0–L2**. The author says L0–L3, because only 1,536 forms appear in 6,000 draws; the exact space passes at L3. |
| prime_factors (exact) | distinct N: 236 / 302 / 785 / 1,611 / …; N × 4 asks: 944 / 1,208 / 3,140 / … | **L0–L1**. If N alone counts (the ask treated as a parameter): L0–L3. |
| pythagoras (exact) | 260 / 790 / 1,410 / 2,090 / 2,800 / 3,530 / 4,230 | **L0–L2**. With order removed: L0–L3. |
| digit_puzzle (sampled; L0–L2 saturated) | 311 / 1,062 / 1,040 / 2,714 / … | **L0–L2**. With clue order removed (164 / 566 / 554 / ~1,400): probably L0–L6. |

Failures that appear **only when presentational order is removed:**
- gcd_lcm L0 (557, saturated) and L1 (1,344)
- grid_perimeter L0–L1 (618 / 621, saturated, once translation and mirror images are removed)
- painted_cube L0–L2 (535 / 1,103 / 1,720)
- pigeonhole_worst_case L0 (942)

All other lineages pass at G = 300 under every reading I measured.

**At the G actually written,** demand per lineage grows:
- strict 22 lineages, about 11 per part: 10 × 2,282 = **22,820** per core level;
- lenient 36, about 18 per part: **14,340** per core level.

Structurally, binomial_choose, pythagoras and digit_puzzle then fail at every level except reserve L6, and prime_factors fails at L0–L4. With the setting sentence, everything passes. Whether the gate is applied at G = 300 or at the G written is **PENDING LEAD REVIEW**.

**Erratum to my hashed `JUDGEMENT_2`, section I:** it says these three fail "at EVERY level". Reserve L6 demands only 1,000 and passes. I also kept the earlier, less exact "fails L0–L3" wording for binomial_choose as the author's figure.

## 7. Feasibility (judgement, labelled as such)

Rule-generated school mathematics with exact keys can reach about **25–45 strict lineages per part** (50–90 overall). Distinctness falls off beyond about 60. Under the lenient reading, perhaps 40–70 per part.

Today M1 has about 11 per part (strict) or about 18 per part (lenient). Either way it is far below the proposed minimum of 300. The cross-evaluation duplicates in §3 lower the independent count further if the lead dedupes across evaluations.

## 8. Differences from the author's manifest (read after both hashes)

- **Existing groups.** The author has S1 = {shopping, speed_distance, mixture, clock_duration}, S2 = {percent, tip, fraction_remainder}, S3 = pipes ("arguably S5"), S4 = ratio_share, S5 = {ages, average_missing, consecutive, linear_equation, rectangle}, S6 = arithmetic_series, S7 = coins. That is 7 (or 6).
  - Mine is 5. I also merge coins and pipes into the linear group and ratio_share into scaling.
  - The author is stricter than me on clock_duration, which he puts in S1 and I kept apart. Taking his merge as well would make the existing strict count 4. The defensible strict range for the existing 16 is therefore **4–7**.
- **New 21.** The author has 21 distinct, with 3 borderline. I agree with keeping all three borderline pairs apart.
  - I add three strict-only merges the author does not discuss: S4, S5, S6.
  - I add one cross merge, S7, which the author does not make. His rejected log treats "Gauss pairing" as arithmetic_series and "geometric doubling" as recurrence.
- **Inconsistencies in the author's own log:**
  - He rejects "lattice paths (additive DP)" as a borderline duplicate of change_ways, but keeps min_cost_packs, a min-plus DP over amounts, separate.
  - He rejects "area by formula" and "clock-hand angle" as S1 formula evaluation, but keeps painted_cube's and pythagoras-perimeter's formula paths separate.
  - **PENDING LEAD REVIEW:** one consistent granularity is needed.
- **Capacity.** We agree on the four lineages that rely on names and settings. We differ on binomial L3 (exact count versus sample). The author does not measure the order-canonical reading or the demand at the G actually written.
- **Shortcuts.** The author flags none. I find four above his own screen (§5) and the overshoot pattern.
- **Not in the manifest at all:** D1–D4, the leading-zero and power-gloss ambiguities, the cross-evaluation duplicates, and the partition spanning strict clusters.

## 9. Must be fixed before registration

1. **slot_permutations:** always state the leading-zero rule. As written, 13 fixture items are wrong under the ordinary reading.
2. **last_digit_power:** reword the gloss. Remove the even-exponent artefact for bases ending 4 or 9, and the "never the base digit" anti-cue.
3. **gcd_lcm:** fix the ask collapse at L3–L6. Draw the ask outside the retry loop, or relax the k≥3 gcd rejections.
4. **division_counting:** fix the shape mix the same way. Decide whether "crates" (one ceiling) is the intended two-step procedure.
5. **Shortcuts:** min_cost_packs greedy (redraw against it, or accept it as registered); mode_tally "last listed"; grid_perimeter "bbox+4"; last_digit_power "exponent's last digit". Re-check both sides after any redraw.
6. **Lineage count:** the lead rules on the S4–S7 granularity and on clock_duration, and registers a strict and a lenient count. Over-counting is the harmful error.
7. **Duplicates:** the lead rules on the cross-evaluation duplicates and on partitioning by strict cluster rather than by template family (§3).
8. **Capacity:** the lead rules on what "distinct items" means and on which G the gate uses. Under the least favourable reading, binomial_choose, prime_factors, pythagoras and digit_puzzle (and more, under the order-canonical reading) fail at low levels.
9. **Second solvers:** none are registered yet. The audit solvers here are evidence, not the registered second solvers, and §6.2 requires a separate auditor context to audit the solver pair.

## Commands (all from the audited worktree)

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PYTHONPATH=. uv run --locked --offline python $D/render_samples.py > $D/samples.txt
PYTHONDONTWRITEBYTECODE=1 uv run --locked --offline python $D/check_fixtures.py studies/m0/fixtures/m1_batch1   # attempt1 and attempt2 outputs kept
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PYTHONPATH=. uv run --locked --offline python $D/shortcuts_audit.py 1000     # also re-solves 147,000 items
PYTHONDONTWRITEBYTECODE=1 uv run --locked --offline python $D/shortcuts_summarise.py $D/shortcuts_out_N1000.json  (v1) / shortcuts_summarise_v2.py (v2)
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PYTHONPATH=. uv run --locked --offline python $D/overshoot_audit.py 2000
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PYTHONPATH=. uv run --locked --offline python $D/shape_mix.py 2000
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PYTHONPATH=. uv run --locked --offline python $D/capacity_audit.py 4000
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PYTHONPATH=. uv run --locked --offline python $D/capacity_audit_v2.py 4000 <skip list>
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. uv run --locked --offline python $D/fixture_dups_v2.py studies/m0/fixtures/m1_batch1   # fixture_dups.py attempt 1 failed (argv clash), kept
PYTHONDONTWRITEBYTECODE=1 uv run --locked --offline python $D/pairs_table.py > $D/pairs_666.tsv
```

`$D` is this folder.

**Process deviations, recorded:**
- System `python3` was used for three in-place edits of my own scripts and for a first run of `pairs_table.py`; that run was repeated under uv.
- One ad-hoc gcd check was run from stdin and crashed (see D1).
- One wait loop used a bounded `sleep` (at most 10 minutes).
