# M0 stage 4: independent recomputation of the capacity stage of record

**Verdict: REPRODUCED.** I recounted 616 cell comparisons (469 cells in round 1 and 147 cells in the two round-2 parts) with my own counting loop. Count, attempts, how the draw ended, and solver disagreements agree with `capacity_of_record.json` in every cell. My own rounds and fixed point register the same lineages in all eight parts, with the same unions for condition (ii). This is independent engineering and arithmetic evidence. It is not a success claim, not Astra validation and not human approval.

- Ran as: `arbor-auditor` task, model **Opus 5.5** (`claude-opus-5-5`, from session metadata). I wrote none of the code under audit: `capacity.py`, `distinct_key.py`, `pool_builder.py`, the generators or the second solvers. I also wrote none of the earlier capacity audit.
- Astra review: NOT_PERFORMED.
- Specification: ADR-0033 addendum 1 at `2c944302`, section 4A stages 4 and 5, and section 10 part A.
- Environment:
  - macOS 27.2.1 arm64, CPython 3.12.14, uv 0.12.15.
  - Every command ran from the implementation worktree root `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f` as `PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 timeout <=590 uv run --locked python <deliver>/<script> [args]`. The worktree was at commit `f9f4ca74`.
  - Up to 16 processes (`multiprocessing`, spawn).
  - Standard library only.
- Stream: the registered label `capacity` (seed 400002), drawn after the run as the brief allows. One extra draw used the label `capacity-recompute-extra` (item 4 (i)).

## What I reused and what is mine

- **Mine, written from the text:**
  - `rc_common.py`: the stream derivation, D and D_lin, the parts from the three inputs, the count loop and the solver check.
  - `e_rounds.py`: the rounds and fixed point.
  - All the comparison scripts.
  - Nothing imports `capacity.py`, `pool_builder.py`, `partition.py` or any `*_analysis` module.
- **Reused as the thing being counted:**
  - `studies/m0/core.build_item`;
  - the lineage objects, loaded from the same four modules the pair audit and `capacity.RealSource` use: `lineages_r1_fix4_clusters` (`candidates_v4`/`registered_v4`), `r2_fix4_set.fix4_set`, `lineages_m1_fix4.load_registered` and `lineages_c1_fix4.all_written`;
  - the second solvers `studies/m0/solvers2/solver2_*.py` (`SOLVERS`).

  The module list follows the earlier auditor's `a_common.py`, as an interface fact; no code was copied from it. The R1 ids that both `candidates_v4` and `registered_v4` return are bound to the identical builder function (checked: 12 overlaps, all `is`-identical), so the order of merging does not matter.
- **The key:** the committed `studies/m0/registration/distinct_key.py` (SHA-256 `08a0526b…42e1`, checked). **I have no relabelling of my own;** every count uses the committed key. The rename test in item 4 (i) is the only independent check of the key that I made.
- **Solver check:** my own code. The input is `copy.deepcopy(json.loads(json.dumps(structured)))`. An exception, a non-`str` answer, or an answer `!=` `Item.answer` counts as a disagreement. There is no wall-clock alarm; the largest call time is recorded instead.

## 1. Integrity (`a_integrity_parts.py` → `.out`, `.json`)

- **The record.** `capacity_of_record.json` has SHA-256 `33c393fbd0770520c489c8bd8591a1a0febd3f4273961499619a1d6eaa12fb34`, as stated. It is the same as the blob at `f9f4ca74`. It is absent at `c01b7f89`, the run commit.
- **The record's input hashes** match the files:
  - candidates `8dcc796c…946a`;
  - map `1ba6ddd5…809c`;
  - partition `750715d8…37e9`.
- **`HASH_RECORD_STAGES_2_TO_4.json` against the files:** all 14 entries equal, in the working tree and as blobs at both `c01b7f89` and `f9f4ca74`. The entries are:
  - candidate list;
  - `capacity.py` `00638afa…2152`;
  - `distinct_key.py` `08a0526b…42e1`;
  - map;
  - `partition.py` `4e43d280…4d03`;
  - partition of record;
  - `pool_builder.py` `728856b6…4862`;
  - the seven second solvers.
- **What changed between the run commit and the record commit:** `git diff c01b7f89 f9f4ca74 -- studies src tests` changes only the record file. `core.py` and `vocab.py` are unchanged from `7cd0ac5a` to `c01b7f89`.
- **Round-1 inputs.** From the three inputs with my own code, the round-1 parts, G, D(G), k_c and D_lin are equal to the record's `start` and round-1 figures in all eight parts. That gives 469 round-1 cells, and at least 13,800,570 attempts if every cell ended on its target with no discard.

## 2. The recount

**Round 1** (`c_make_round1_cells.py`, `b_run_cells.py` → `round1_text.jsonl`, `round1_c1.jsonl`; comparison `d_compare_round1.py` → `.out`/`.json`):
- **All 469 cells agree with the record on all five fields:** target, count, attempts, ended and solver_disagreements.
- 0 differences.
- My round 1 built 16,543,835 items.
- 0 solver disagreements.
- The slowest single second-solver call was 0.057 s.
- The record uses only the `ended` values `target` and `budget`. No cell gave up in my recount or in the record.

**Round 2** (`e_rounds.py` found the 77 cells at new targets; `round2.jsonl`; 1,968,556 items built, 0 disagreements, slowest call 0.031 s):
- **R2 part B:** G = 6, D(6) = 41,010 = D_lin(6, 1). 6 lineages × 7 levels.
- **M1 part A:** G stays 8, so D(8) = 31,000. Cluster `M1.ages` at k = 5 has D_lin(8, 5) = 10 × (⌈500/5⌉ + ⌈2,500/5⌉ + ⌈100/5⌉) = 6,200. 5 lineages × 7 levels.
- **The other 10 M1A lineages** keep their round-1 targets. Their 70 round-2 cells are my round-1 results at the identical target. My draw is deterministic in (lineage, level, target), so I did not draw them again; the record drew them again under R-63.
- **The record's round 2 has 147 cells** (M1A 105, R2B 42). All 147 agree with mine on all five fields, and the unions agree.

**Total: 616 cell comparisons (469 + 147), 0 differences.**

## 3. The rounds (`e_rounds.py` → `e_rounds.out`, `e_rounds.json`)

My rounds apply the text as written:
- G and k_c are taken per part.
- (i) is read at all seven levels against D_lin(G, k_c).
- (ii) is read only on clusters all of whose lineages meet (i). It is the union of the stored key sets per level, against D(G).
- (iii) is any disagreement on any item built.
- All failing lineages are removed at once, and the round is repeated until a round removes nothing.

| Part | Rounds | Removed | Registered clusters / lineages | Record |
|---|---|---|---|---|
| R1 A | 1 | none | 4 / 5 | 4 / 5 |
| R1 B | 1 | none | 1 / 1 | 1 / 1 |
| R2 A | 1 | none | 8 / 9 | 8 / 9 |
| R2 B | 2 | `R2.cellular_automaton` (round 1; (i), level 0: 32,768 < 35,300, ended on budget) | 6 / 6 | 6 / 6 |
| M1 A | 2 | `M1.rectangle_r3` (round 1; (i), level 0: 4,189 and level 1: 4,899 < 5,180, both ended on budget) | 8 / 15 | 8 / 15 |
| M1 B | 1 | none | 6 / 8 | 6 / 8 |
| C1 A | 1 | none | 13 / 17 | 13 / 17 |
| C1 B | 1 | none | 4 / 4 | 4 / 4 |

- **65 of 67 lineages registered.** The registered lists are equal to the record's, id for id, in all eight parts.
- **Round by round:** G, D(G), and every cluster's k, D_lin, `union_evaluated` and union by level are equal to the record's.
- **Removals:** the two removed lineages, with their round, level, count and ending, are equal to the record's `removed` entries.
- **Condition (ii)** removed nothing.
- **Condition (iii)** removed nothing: 0 disagreements on 18,512,391 items built across both rounds.
- **The partition is kept:** `C1.cellular_update` stays in R2 part B with no lineage.

## 4. Three facts

**(i) `R1.temporal_weekday_shift_r6`, 241,000 keys in 241,000 attempts at all seven levels.** My recount gives the same, and the zero repeat rate is real.

What varies in an item besides the event names (builder `lineages_r1_fix4_a.py:63`):
- The anchor weekday: 7 values.
- For each of the L + ex links (level 0: 5 + 2 = 7):
  - a day count k uniform on 1..300;
  - a sign, before or after;
  - a sentence form, "after" or "before".
- Where each of the ex extra events hangs: level 0 gives 6 × 7 = 42 combinations.
- The order of the 7 link sentences (shuffled).
- The weekday, the day counts and the sentence words stay in the key; only the event names are relabelled.

Size of the key space at level 0:
- **Lower bound:** the key determines the ordered 7-tuple of day counts in text order. That tuple is uniform on 300^7 = 2.19 × 10^17 values (iid counts; a shuffle of iid values is iid).
- So the expected number of pairs sharing even that tuple is 1.3 × 10^-7 in 241,000 draws and 5.7 × 10^-7 in 500,000 draws.
- **Upper bound:** about 7 × 42 × 1,200^7 × 7! ≈ 5 × 10^27 generator outcomes.
- Higher levels have more links, so the space is larger.

Further draws at level 0 (`g_facts.py`):
- Under `capacity`, the same stream continued: **500,000 keys in 500,000 attempts.**
- Under an independent label `capacity-recompute-extra`: **500,000 in 500,000.**
- No repeat ever occurred.

Names-only collision test: the same random state is rebuilt with `EVENTS` in the builder's module replaced by a fixed permutation of itself, so only the event names differ.
- **2,000 of 2,000 pairs at each of levels 0, 3 and 6 have different texts and the SAME key, and the same answer.**
- An example pair with its key texts is in `g_facts.json`.
- Changing one day count by 1 changes the key.

**(ii) `R2.cellular_automaton` at level 0: 32,768 = 2^15 distinct keys.**

Why, from the builder (`lineages_r2_fix3.py:236`):
- The row has 11 + 2·level cells with both end cells fixed at 1. At level 0 that leaves 9 free bits.
- The table has 8 triples drawn 0/1, then `001 := 1 − 100` and `011 := 1 − 110`. That leaves 6 free bits.
- That forcing makes a constant table impossible, so the `Retry` never fires.
- The number of steps is fixed at 2 + level // 2 (2 at level 0).
- The question contains no vocabulary names, so the key is the text.
- So the space is 2^9 × 2^6 = 2^15.

Checks:
- An exhaustive rendering of all 2^15 bit settings through the builder gives **32,768 distinct texts and 32,768 distinct keys.**
- A draw to 32,768 reaches it at attempt 369,491.
- 2,000,000 attempts give 32,768 and no more.

Space and counts by level, against the round-1 demand of 35,300 (G = 7, k = 1):

| Level | Space | Count | Attempts | Ended |
|---|---|---|---|---|
| 0 | 32,768 | 32,768 | 1,413,000 | budget |
| 1 | 131,072 | 35,300 | 41,069 | target |
| 2 | 524,288 | 35,300 | 36,525 | target |
| 3 | 2,097,152 | 35,300 | 35,608 | target |
| 4 | 8,388,608 | 35,300 | 35,364 | target |
| 5 | 33,554,432 | 35,300 | 35,317 | target |
| 6 | 134,217,728 | 35,300 | 35,301 | target |

- Level 1 matches the birthday expectation N ln(N/(N − m)) ≈ 41,120.
- Only level 0 fails, by 2,532 keys.

**(iii) `M1.rectangle_r3`.**

What bounds the space (builder `lineages_m1_fix3_a.py:241`):
- Width w is in 2..60 + 10·level: 59 values at level 0 and 69 at level 1.
- The "ratio" shape has k in 2..12 (11 values).
- The "excess" shape has d in 1..60 (60 values).
- The perimeter, k and d are in the text, there are no names, and the frame is constant per shape.
- So the space is 71 × (#widths): **4,189 at level 0 and 4,899 at level 1.** Enumeration of (shape, perimeter, parameter) gives the same numbers.
- The draws reached exactly those full spaces and then ended on the budget of 208,200.
- From level 2 up the space is 5,609 or more (level 6: 8,449), which is above 5,180.

The demand depends on k:
- D_lin(8, k) = 31,000, 15,500, 10,350, 7,750, 6,200, **5,180**, 4,450, 3,890 for k = 1..8.
- At k = 6 it is 5,180, above 4,189.
- Only at k ≥ 8 would levels 0 and 1 fit (fact; not a recommendation).

Cluster `M1.ages` in M1 part A:
- Round 1 (k = 6): `M1.ages_r3`, `M1.average_missing_r4`, `M1.consecutive_r3`, `M1.linear_equation_r3`, `M1.pipes_work_r3`, `M1.rectangle_r3`. Condition (ii) is not read, because one lineage failed (i).
- Round 2 (k = 5, rectangle removed): every lineage reaches 6,200 at every level. **The union is 31,000 at every level, equal to D(8) = 31,000.** That is zero slack and zero shared keys between siblings. Condition (ii) holds.

## 5. Smallest margins (`f_margins.py` → `f_margins.out`)

All 455 cells of the 65 registered lineages at their final targets ended on the target (count = target), so count − target is 0 everywhere. 203 of the 455 had no discard at all.

**The ten passing cells with the highest attempts/count:**

| # | Part | Cluster | Lineage | Level | T | Attempts | Attempts/count | Share of budget |
|---|---|---|---|---|---|---|---|---|
| 1 | R2A | C1.digit_peel | R2.from_base | 0 | 15,500 | 127,954 | 8.26 | 0.206 |
| 2 | M1B | M1.fraction_remainder | M1.percent_change_r3 | 0 | 13,690 | 59,624 | 4.36 | 0.109 |
| 3 | R2A | C1.digit_peel | R2.to_base_wide | 0 | 15,500 | 57,891 | 3.73 | 0.093 |
| 4 | R2A | C1.digit_peel | R2.from_base | 1 | 15,500 | 41,717 | 2.69 | 0.067 |
| 5 | M1B | M1.fraction_remainder | M1.fraction_remainder_r3 | 0 | 13,690 | 33,672 | 2.46 | 0.061 |
| 6 | M1B | M1.fraction_remainder | M1.percent_change_r3 | 1 | 13,690 | 29,739 | 2.17 | 0.054 |
| 7 | M1B | M1.fraction_remainder | M1.fraction_remainder_r3 | 1 | 13,690 | 28,320 | 2.07 | 0.052 |
| 8 | M1B | M1.fraction_remainder | M1.fraction_remainder_r3 | 2 | 13,690 | 25,500 | 1.86 | 0.046 |
| 9 | C1A | C1.while_counter | C1.while_counter_f3 | 0 | 19,470 | 36,247 | 1.86 | 0.046 |
| 10 | M1A | M1.ages | M1.consecutive_r3 | 0 | 6,200 | 11,362 | 1.83 | 0.046 |

- No passing cell used more than 21 % of its budget.
- For comparison, the two failing lineages ran at 43 to 50 attempts per key.

**Zero slack.** In every multi-lineage cluster, at every level, the union equals k × D_lin exactly, so no sibling shares a key with another. The union equals D(G) exactly (zero slack) at all seven levels in four multi-lineage clusters:
- R1A `R1.boolean_lights` (k = 2, 2 × 30,500 = 61,000);
- R2A `C1.digit_peel` (k = 2, 2 × 15,500 = 31,000);
- M1A `C1.fib_like` (k = 2, 2 × 15,500 = 31,000);
- M1A `M1.ages` (k = 5, 5 × 6,200 = 31,000; round 2).

Positive slack:
- C1A `C1.bracket_matching` and `C1.slices`: 10;
- C1A `C1.fib_like`: 30;
- M1A `M1.mixture`: 50;
- M1B `M1.fraction_remainder`: 60.

Every k = 1 cluster (41 of them) also has union = D(G) exactly, trivially, because D_lin(G, 1) = D(G) and the draw stops at its target. In those clusters one more key could never be wanted: that is what counting to the target means, as section 4A stage 4 states in its "two limits".

## 6. Departures of the record from the text

**None found in what I checked.** Observations, as facts:
- **Budget reading.** The text says the draw stops "when the number of attempts exceeds 40 × T + 1,000". The record's `attempts` on a budget stop equals 40T + 1,000, for example 1,413,000 and 208,200. That is the number of items built, as `draw_items` counts them: the counter is raised and tested before the build, so at most 40T + 1,000 items are built. My loop gives the same.
- **Give-up attempts.** The record gives no `attempts` convention for a give-up, but no cell gave up.
- **Condition (ii)** is evaluated only for clusters whose lineages all pass (i) (`union_evaluated` false for `C1.cellular_update` in R2B round 1 and for `M1.ages` in M1A round 1), as the text's first limit says.
- **Round 2 re-draws everything** in the two parts that had a round 2, including cells whose target did not change (R-63, no cache). This changes no figure: their values equal round 1.
- **Process departure R-61 is not re-examined here.** The key, the runner and the pool builder were hashed after the partition. This recount reproduces the record under the committed key; it does not test whether a different key would have given different registrations. The `R2.caesar_shift` exception (R-62 (c)) and the breadth of the name classes (R-62 (b)) are PENDING LEAD REVIEW as already recorded. I take no position.
- **The record does not carry** the key sets, their hashes, or the per-cell solver time. My per-cell key-sequence SHA-256 is in my JSONL files, but there is nothing in the record to compare it with.

## Not covered

- **The key.** I did not write an independent relabelling. Every count uses the committed `distinct_key.py`.
- **The second solvers.** I did not check whether they are correct; only whether they agree with the builder's answer.
- **The "largest set" proviso** (a lineage that fails a target also fails every larger one) was not tested.
- **Stage 5 and 6 items.** I did not read the stage-5 family count or anything else of stage 6.
- **Prefix check.** `h_details.py` prints the hash of the round-1 temporal level-0 key file but does not compare it with the 500,000 draw's prefix. It does not need to: the same stream with 500,000 distinct keys in 500,000 attempts implies no repeat in its first 241,000.
- **Timing.** No per-cell timing beyond the `seconds` field.

## Attempts and leftovers

- **First run of the rounds script.** `e_rounds_attempt1.out` is the first run of `e_rounds.py`. It stopped by design (exit 3), listing the 77 missing round-2 cells (`work/missing_cells_1.json`). It is kept.
- **Smoke test.** `b_smoke_T2000.out` is a timing smoke test at T = 2,000 under `capacity`, with no keys saved.
- **A redundant line.** `rc_common.lineages()` contains an always-true assertion line (`… or True`). It has no effect and is left as written.
- **Key sets.** These are in `work/keys/` (about 240 MB, not delivered, not deleted). `work/` also holds the cell lists.

## Files (`deliver/`, hashed in `SHA256SUMS.txt`)

- Common code: `rc_common.py`.
- Item 1: `a_integrity_parts.py` and its `.out`/`.json`.
- Count runner: `b_run_cells.py`.
- Cell lists: `c_make_round1_cells.py` and its `.out`.
- Counts: `round1_text.jsonl`/`.out`, `round1_c1.jsonl`/`.out` and `round2.jsonl`/`.out`.
- Item 2: `d_compare_round1.py` and its `.out`/`.json`.
- Item 3: `e_rounds.py` and its `.out`/`.json`, plus `e_rounds_attempt1.out`.
- Item 5: `f_margins.py` and its `.out`.
- Item 4: `g_facts.py` and its `.out`/`.json`.
- Items 4 and 6: `h_details.py` and its `.out`.

Commands, from the implementation worktree root, each prefixed `PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 timeout <s> uv run --locked python`, with `$S = /Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_capacity_recompute_20261126`:
1. `$S/deliver/a_integrity_parts.py`
2. `$S/deliver/c_make_round1_cells.py`
3. `$S/deliver/b_run_cells.py $S/work/round1_cells_text.json $S/deliver/round1_text.jsonl` (146 s)
4. `$S/deliver/b_run_cells.py $S/work/round1_cells_c1.json $S/deliver/round1_c1.jsonl` (137 s)
5. `$S/deliver/d_compare_round1.py`
6. `$S/deliver/e_rounds.py $S/deliver/round1_text.jsonl $S/deliver/round1_c1.jsonl` (stops with the missing list)
7. `$S/deliver/b_run_cells.py $S/work/missing_cells_1.json $S/deliver/round2.jsonl` (9 s)
8. `$S/deliver/e_rounds.py $S/deliver/round1_text.jsonl $S/deliver/round1_c1.jsonl $S/deliver/round2.jsonl`
9. `$S/deliver/f_margins.py`
10. `$S/deliver/g_facts.py`
11. `$S/deliver/h_details.py`

Astra review: NOT_PERFORMED. This recomputation is independent engineering evidence only; it is not Astra validation and not human approval.
