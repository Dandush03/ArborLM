# ADR-0024 — P10-I-S1 — useful capacity scaling

**Status: DRAFT — NOT APPROVED. Nothing under this ADR is implemented, calibrated, frozen or run.**

- **Date:** 2026-11-17 (UTC). Draft 2: draft 1 revised after the independent specification review (`docs/reviews/p10-i-spec-reviews-2026-11-17/REVIEW_ADR-0024.md`, verdict NOT READY). §22 maps every finding to its disposition. **SPEC: PENDING ASTRA REVIEW.** `Astra review: NOT_PERFORMED`. Claude review is not Astra review.
- **Study code** P10IS1. **Package** `studies/p10is1/` (new code only). **Config** `configs/p10is1_capacity.toml`. **Tests** `tests/test_p10is1_*.py`.
- **Origin.** `docs/reviews/p10-i-direction-2026-11-17/DIRECTION.md` (sections 2, 4, 5, 7). Successor of P10-S1 (ADR-0021), whose registered outcome the human lead accepted as recorded (`results/p10s1-run-2026-11-17/ACCEPTANCE.md`).
- **The routing diagnosis moved to ADR-0029.** Draft 1 held a second lane, the frozen-checkpoint routing diagnosis. It is now `docs/decisions/ADR-0029-p10-i-r-routing-diagnosis.md`. Reason: the two lanes share no rule, budget or frozen input, and one ADR hashed into two freezes repeats the failure that cost P10-S1 attempt 1 (review §C, F12). The human lead's direction (`LITERATURE_AND_ROUTING_NOTE.md` §5.4) placed that lane inside ADR-0024; the split is the reviewer's and the lead's recommendation, **PENDING HUMAN LEAD RULING**, and the lane's content does not depend on where it lives. The bridge block of draft 1 moved with it.
- **Immutability.** P1–P10 code, configs, records, thresholds, seeds and outcomes are not edited, revised or reopened. P10-S1's labels stand as registered. ArborLM is unproven research; no label below is a success claim.
- **Approval.** The human lead alone approves this specification, its budget and each run. The P10 delegation does not cover P10-I. Lead's choices open to his ruling are marked **PENDING HUMAN LEAD RULING** and collected in §21.
- **Roles.** Specification review, implementation audit and recomputation: Opus 5.5 in a context separate from the implementation. Implementation: Sonnet 5.5. Inventory: Haiku 5.5. The model that ran each delegated task is recorded from session metadata. ADR-0012 stays not approved.

## 0. Structure: one registered block, two conditional parts

| Part | What | Outcome lines | Status |
|---|---|---|---|
| **Block M** | P10-S1's seven cells and 2K/256 on fresh seeds, with the audit's corrections and an equal rate search | C-CAPACITY, C-SATURATION, C-EFFICIENCY | Registered if this ADR is approved |
| **Block X** (conditional) | The transition 16,384 → 65,536 slots | X-CAPACITY | Separately frozen and separately funded, after block M (§12) |
| **Lane L** (conditional) | Learned addressing at the cells ADR-0023 licenses | L-CAPACITY, tagged LEARNED-ADDRESS | Runs only under ADR-0023's licence (§13) |

No line implies, substitutes for or is merged with another. Block X and lane L change no block M label.

## 1. Question, and what each outcome would mean

With addressing supplied by an oracle, and every trained arm given the same rate search: does a larger store retain more useful information about a fixed fact set at matched updates, at matched compute and against the smaller store when full; does a full store keep its bits per slot as it grows; does a larger store reach a fixed level sooner; and how does each compare with a dense map of equal parameters?

| Line | Positive would mean | Negative would mean | Inconclusive / not tested |
|---|---|---|---|
| C-CAPACITY | Within the sizes read, the store passes a necessary condition of the storage claim, and the dense map of equal size is not ahead at matched compute, at matched updates or when full | The store does not gain from slots, or it does and the dense map is ahead at every cell read | No decision; the reason is printed |
| C-SATURATION | A full store kept at least three quarters of its bits per slot per fourfold step | It did not, for both the flat and the tree memory | A size was not full within its budget, or the arms disagree |
| C-EFFICIENCY | A larger store reached 3.0 bits per fact in fewer updates and less cost under **both** cost readings, and the dense map was not faster at any cell under either | No arm did, or the dense map was faster at every cell under both readings | The readings or the cells disagree; each is printed |
| X-CAPACITY | The same necessary condition for the one transition 16,384 → 65,536 | As C-CAPACITY, for that transition | NOT TESTED — NOT FUNDED / ENTRY NOT MET; NOT FULL WITHIN BUDGET |
| L-CAPACITY | With the licensed learned addressing, more slots held more at the licensed steps | They did not | OMITTED — NOT LICENSED; inconclusive |

Every oracle-line label carries `STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK`. No outcome of this ADR can establish milestone question 1. The reading available is "necessary condition met / not met / not established"; it is never paraphrased as part or half of the storage claim.

## 2. Background: registered findings (quoted from the records)

From `results/p10s1-run-2026-11-17/OUTCOME.md`, `ACCEPTANCE.md`, `audit/AUDIT.md`:

1. Registered outcome: CAPACITY-INCONCLUSIVE (F-OQ DEPENDENCE_FAILED; F-OQ-IVF DEPENDENCE_FAILED; T-OQ INTERMEDIATE; 16,384→65,536 NOT TESTED); SATURATION-INCONCLUSIVE (F-OQ INTERMEDIATE; T-OQ SATURATION_NOT_MEASURED); EFFICIENCY-NEGATIVE (DENSE FASTER); milestone question 1 not established. Also TREE_BEHIND, DICT DOMINATES ON THIS TASK, DENSE HOLDS MORE AT SATURATION for F-OQ, F-OQ-IVF and T-OQ.
2. **Dependence (audit §2, D7).** Every DEPENDENCE_FAILED verdict comes from `a_use ≥ 0.95 × raw accuracy` at 1,024–2,048 updates, at a_use 0.256–0.414 (ratios 0.9262–0.9486 across arms; 0.9425–0.9471 for the F-OQ and F-OQ-IVF failures at 2,048 updates). The reference arm R2 fails the same condition 12 times at 512–1,024 updates.
3. **Dense speed (audit §3, D4).** DENSE FASTER for T-OQ holds in 5 of 5 replicates at 2K/4K and 0 of 5 at 8K/16K. At 8K/16K, D-OQ's cost to reach the level is 0.27–0.38 of T-OQ's in measured CPU seconds and 1.32–1.87 of it in analytic multiply-adds. The code applied an any-cell rule (`studies/p10s1/analysis.py`, line 631) that ADR-0021 §8.8 does not state.
4. **Dense quality (audit §5, D3).** At 32K/16K, F-OQ against D-OQ: matched updates d = −0.238 to −0.450 bits (4 of 5 at or below −0.25); matched compute d = +0.24 to +0.33 (F-OQ ahead, 5 of 5); D-OQ's best snapshot d = −0.68 to −0.87 (5 of 5). At saturation D-OQ holds 1.76–1.87 bits per fact more than F-OQ at both loaded cells (5 of 5).
5. **Seed block (audit D1; `ERRATUM_SEED_BLOCK.md`).** `analysis.py` lines 167–169 store two reads under one key; 28 printed lines are wrong (corrected: the data draw dominates in 24 of 28).
6. **Saturation (audit §4).** 1,024→4,096: F-OQ ρ 3.785–3.875 (PROPORTIONAL, 5 of 5); T-OQ ρ 2.389–2.922 with two replicates NOT FULL at 8K/1K (last-doubling gains 0.1059 and 0.132 against the limit 0.10). 2K/256 was not full within its ceiling of 262,144 updates and was not run; 128K/16K was not funded (ADR-0021 §5.1, §25.15).
7. **Rates.** Memory arms ran at 0.003, untuned by design; D-OQ at its calibrated 0.1 or 0.03 (audit §6; ADR-0021 §10.1 item 3).
8. **Lane L** was OMITTED — NOT OVERLOAD-QUALIFIED (ADR-0021 §25.17). No study has registered capacity under learned addressing.
9. **Never run:** any cell at 65,536 slots under ADR-0021 revision 5; 128K/16K beyond 65,536 updates (revision 4's calibration saw 1.46–1.52 bits per fact there, still gaining 0.54–0.62 per doubling; ADR-0021 §1 fact 13).

From the review of draft 1 (`REVIEW_ADR-0024.md` F6, F18; the reviewer's own scripts on P10-S1's recorded counts; the lead has not recomputed them):

10. The dependence condition of §8.1 below fails **0 of 4,394** recorded reads of P10-S1 attempt 2. All 32 reads that failed the 0.95 condition pass it; R2 passes at all 150 of its reads (largest excess +0.0038 of n). The largest excess on any memory read is +0.0101 of n, at a_use 0.055.
11. For independent unit codes of width 16, the share of facts with a neighbour above cosine 0.8 is 0.111, 0.377, 0.849 and **0.999** at 2,048, 8,192, 32,768 and 131,072 facts (the first three match P10-S1's measured 0.10, 0.38, 0.85).

## 3. What a capacity result on this task can and cannot show

The task is recall of trained random facts: 8-byte synthetic records, a 5-bit answer, the fact's identity given by an oracle. A hash table solves it exactly with one probe (DICT: 32,768 of 32,768 correct in P10-S1).

- **It can show** properties of the store and its optimizer: whether gradient descent through a sparse top-8 read writes more facts into more slots, how interference grows with facts per slot, what a full slot holds, and how these compare with a dense map of equal parameters. These are necessary conditions of ArborLM's storage claim.
- **It cannot show** value that a lookup does not provide: generalisation, updating beyond key-value recall, use by a language model. A positive here is not "useful capability".
- **Decision: the task is not changed.** Changing it together with the audit's corrections would confound them. Every label is printed with DICT DOMINATES ON THIS TASK. Value beyond lookup needs a study designed for it (§21 item 1).

## 4. Arms, controls and baselines

| Arm | What it is | Learned | Isolates |
|---|---|---|---|
| **F-OQ** | Flat memory, oracle query code (width 16), all keys scored, top-8, temperature 0.2 — ADR-0021 §3 | keys, values, output projection, gate | The store with exhaustive retrieval |
| **T-OQ** | Learned tree: router picks 2 of N/256 branches, top-8 of their 512 keys — ADR-0021 §3 | router, keys, values, projection, gate | Hierarchical sparse retrieval trained jointly |
| **D-OQ** | Dense map of the same code, parameters within 0.1% of F-OQ's — ADR-0021 §5.3 | both layers, gate | Parameters alone |
| **R2** | One dedicated slot per fact | values, projection, gate | Reference rung; validity of every check (§8.1) |
| F-OQ-IVF (evaluation only) | F-OQ's keys read through the registered index (N/256 lists, at least 512 candidates) | nothing | Post-hoc sparse retrieval, as P10-S1 read it |
| DICT, no-memory, unseen-fact control, KNN-W, KNN-W-IVF | ADR-0021 §5.5 | nothing | Lookup baseline; chance; leakage; a non-oracle baseline |
| **F-LA** (lane L only) | A5-D as ADR-0023 freezes it | as ADR-0023 | Learned addressing (§13) |

One change per comparison: cells of one row differ only in slots; arms at one cell differ only in the addition.

- **No product-key arm.** Draft 1 added one. The note's §5.2 places product-key memory in Stage B of the routing work, and a new architecture is a separate study (§5.4). It is removed from this ADR.
- **H8 is not run** (lead's recommendation; §21 item 5). Its label KEY-LEARNING-LIMITED was False in P10-S1 and F-OQ was at or above H8 at every cell at the run length (audit §6). **What is lost:** H8 is the only fixed-address control, and P10-S1 read it at an untuned rate; under the equal rate search the comparison could differ, and this study will not see it.

## 5. Grid and steps (block M)

"8K/1K" is 8,192 facts in 1,024 slots. Load is facts per slot.

| Facts \ Slots | 256 | 1,024 | 4,096 | 16,384 |
|---|---|---|---|---|
| 2,048 | 2K/256 (8; F-OQ only) | 2K/1K (2) | 2K/4K (0.5) | |
| 8,192 | | 8K/1K (8) | 8K/4K (2) | 8K/16K (0.5) |
| 32,768 | | | 32K/4K (8) | 32K/16K (2) |

- Loaded steps: C1 (8K/1K→8K/4K), C2 (32K/4K→32K/16K). Control steps: N1 (2K/1K→2K/4K), N2 (8K/4K→8K/16K). Transitions 1K→4K and 4K→16K. Saturation cells (load 8): 2K/256, 8K/1K, 32K/4K.
- **Trained configurations per replicate:** F-OQ 8, T-OQ 7, D-OQ 6 (2K/4K, 8K/4K, 8K/16K, 32K/16K, 8K/1K, 32K/4K), R2 3 (2K/4K, 8K/16K, 32K/32K) = 24. Five replicates: **120 cells.** No seed block: P10-S1's corrected seed block already shows the data draw dominating in 24 of 28 comparisons.
- The oracle codes have width 16 at every size; their crowding grows with the fact set (§2 item 11) and is printed beside every saturation figure.

## 6. Data, seeds, replicates

- Generator, task, panels A and B, held-out panels H1 and H2, unseen-fact control: ADR-0021 §4 and §6.2. Each draw has a fact table of 32,768 facts whose first 8,192 and 2,048 are the smaller sets.
- **Five replicates, never reduced.** Replicate r is data draw r with one initialisation seed. Pairing as ADR-0021 §6.2.
- **Data seeds: namespace 240001–249999** (no overlap with any earlier study; the review checked it against the sibling drafts, F27). Registered draws at bases 240001, 240101, 240201, 240301, 240401; two calibration draws and one rehearsal draw inside the same namespace.
- **Every other seed is assigned in `docs/reviews/p10-i-direction-2026-11-17/SEED_REGISTRY.md`** (being written), and none is fixed here. Roles and counts this study needs: initialisation seeds, 5 registered, 2 calibration, 1 rehearsal; a unit-test range; for block X, the same draws extended to 131,072 facts (no new data seed); for lane L, the seeds ADR-0023's recipe needs per cell (5 replicates). Before any freeze, gate G9 checks every literal and derived seed (initialisation seed + 1000·k, as the P9 generators derive them) against the registry and against every range ADR-0021 §6.3 lists.

## 7. Rates, U_P and run lengths

### 7.1 Equal rate search, and its order (F1)

**Rule: every trained arm gets the same search.** Grid {0.001, 0.003, 0.01, 0.03, 0.1}, both calibration draws, the selection rule of ADR-0021 §10.1 item 3 and §22 M7 (highest minimum Panel A a_use over the two draws at the readout; ties within 0.02 by the walk down the doubling grid; then the smaller rate).

| Arm | Unit → selection cell → cells that use the rate |
|---|---|
| F-OQ, T-OQ | 1,024 slots → 2K/1K → 2K/1K. 4,096 → 8K/4K → 2K/4K, 8K/4K. 16,384 → 32K/16K → 8K/16K, 32K/16K |
| D-OQ | 4,096 → 8K/4K → 2K/4K, 8K/4K. 16,384 → 32K/16K → 8K/16K, 32K/16K. D-OQ has no cell at 1,024 slots that is not loaded, so no such unit |
| R2 | One unit per reference cell: 2K/4K, 8K/16K, 32K/32K |
| every arm trained there | Each loaded cell (8K/1K, 32K/4K) and 2K/256 is its own unit, read at 65,536 updates |

**Order, fixed now, so that rates and U_P do not each wait for the other:**

1. Rates of the units that are not loaded are selected at a **provisional readout** per row: 8,192, 8,192 and 16,384 updates for the rows of 2,048, 8,192 and 32,768 facts (P10-S1's U_P values; ADR-0021 §25.15).
2. U_P of each row is computed at those rates by the rule of §7.2.
3. If a row's U_P differs from its provisional readout, the rates of that row's units are selected **once more** at U_P. U_P is not recomputed. There is no further iteration.
4. Both selections are printed. Loaded-cell units are selected last, at 65,536 updates.

- **Edge rule (design ceiling, extended by rule).** If the best rate of a unit is at an end of the grid by more than 0.02, the grid is extended one step in that direction (0.3; 0.0003), at most twice per unit. A diverged rate is recorded and left out. If the best is still at the edge after two extensions, the unit prints RATE AT EDGE and the work returns to the human lead before the freeze.
- **Reason.** `docs/EXPERIMENT_PROTOCOL.md` §3 requires a comparable tuning budget across alternatives. In P10-S1 one side was tuned and the other was not.
- **Limit.** At a loaded cell the rate is chosen at 65,536 updates although the cell runs for hundreds of thousands; this favours fast rates. Stated in §20.

### 7.2 U_P and run lengths

- **U_P per row** (ADR-0021 §10.1 item 1): the smallest value on the doubling ladder from 8,192 at which, on both calibration draws and both panels, F-OQ reaches a_use ≥ 0.90 at the row's larger step cell and R2 reaches a_use ≥ 0.95. The ladder extends by doubling within the calibration budget (§15).
- **Cells that are not loaded** run 6 · U_P of their row; R2 runs U_P. Snapshots: U_P × {1/16, 1/8, 1/4, 1/2, 1, 1.25, 1.5, 2, 2.5, 3, 4, 6}.
- **Loaded cells: run until full, within a budget.** The fixed ceiling of ADR-0021 §10.1 item 0b is replaced.
  1. *Ladder.* 65,536 × {1, 1.5, 2, 3, 4, 6, 8, 12, 16, …} (alternating ×1.5 and ×4/3).
  2. *Snapshots.* At every ladder point and at **half of every ladder point** (so 32,768, 49,152, 65,536, 98,304, …), and on the doubling grid from 512 below 32,768.
  3. *Full at U* (a cell, on its own snapshots): on both panels, i\*(U) − i\*(U/2) ≤ 0.10 bits and i\*(U/2) ≥ 0.473 bits (ADR-0021 §8.2, unchanged), at two consecutive ladder points, of which U is the second.
  4. *Calibration* runs F-OQ and T-OQ at each loaded cell on both calibration draws up the ladder until full at U on all four views; that U is the arm's starting length U₀. **D-OQ** starts at the larger of F-OQ's and T-OQ's U₀. At 2K/256 only F-OQ runs.
  5. *Registered run.* Each registered cell (arm, replicate) trains to its U₀ and continues ladder point by ladder point until it is full or reaches **4 · U₀**. The frozen code applies the rule to the cell's own plateau statistic and to nothing else. Continuation uses checkpoint restoration (gate G4).
  6. A cell not full at 4 · U₀ is **NOT FULL WITHIN BUDGET**: a registered value, not a negative. The figure 4 is two further doublings, the horizon ADR-0021 §8.2 row 4 already uses.
  7. **Loaded:** full, and i\* ≤ 4.0 bits (ADR-0021 §8.2, unchanged).

## 8. Measurements and validity checks

The primary measure (a_use, i, i\*, I_use), the address-swap derangement, the ablations and gates G1–G9 are those of ADR-0021 §7.1–§7.4 and §8.1, with the changes below.

### 8.1 The dependence test

P10-S1's third condition compared useful answers with all correct answers. Near the floor the backbone alone answers about 1 in 32 of the facts the store has not retained, so the ratio falls below 0.95 even when every other correct answer depends on the read. The condition is replaced by a test against that null.

DEP applies to a memory cell, snapshot and panel with a_use ≥ 0.25 (ADR-0021 §8.1, unchanged). With n facts, c correct answers, u usefully retained facts, m = n − u, and b the no-memory baseline's correct count on the same panel and fact set of the same draw:

| Condition | Rule |
|---|---|
| DEP-a | Memory disabled gives chance (the G2 interval). Unchanged |
| DEP-b | Value shuffle gives chance. Unchanged |
| DEP-c (new) | Fails only if **both**: (i) c − u exceeds the upper 1 − 10⁻⁴ quantile of Binomial(m, p⁺), where p⁺ is the upper end of the G2 chance interval for n divided by n; and (ii) (c − u − m · b/n) / n > 0.01 |
| LEAKAGE | Unseen facts above chance. Unchanged |

- **What the figures are.** (i) is a one-sided test of "the facts not usefully retained are answered at the backbone's rate". p⁺ is above the measured rate b/n (0.035–0.049 against about 0.028–0.031), so the test is deliberately conservative and its real false-failure rate is far below 10⁻⁴. (ii) is an effect-size floor: more than one fact in a hundred answered correctly without depending on the read and beyond the backbone's own rate. The two parts use different nulls on purpose: (i) guards against noise, (ii) against a real but negligible excess. c − u does not enter i; the floor is a judgement of what excess is worth invalidating a cell for (**PENDING HUMAN LEAD RULING**). The review computed what it detects: an excess of 1.2% of n at n = 8,192 and a_use 0.5; 3.0% at n = 2,048 and a_use 0.25.
- **Disclosure.** On P10-S1's records this condition fails nothing (§2 item 10). The figure 0.01 was written before that audit; it is kept, and it is now known to sit just below the largest excess seen on any read (+0.0101, at a cell under the a_use floor).
- **Where DEP is read: at every snapshot up to the run length. Ruling 22 (g) of ADR-0021 is kept.** Each verdict of §9 fails on a DEP failure at any snapshot of either cell up to its run length; this includes the snapshots that attain i\*. Draft 1 read DEP only at a verdict's own snapshots; that would have been a second weakening made after observation, and it is withdrawn (F6).
- **Reference qualification (binding).** In the rehearsal, R2 is run through DEP-a, b and c at every snapshot fraction of U_P, at each of its cells, on the rehearsal and both calibration draws. A condition that R2 fails at a fraction on any view is **not used at that fraction for any arm of that row**, and the report prints NOT QUALIFIED AT that fraction. In the registered run R2 is read again at the same snapshots; if it fails a qualified condition in a replicate, that condition is not applied at that snapshot in that replicate and REFERENCE FAILED DEP is printed. Fixed before any registered seed is observed; applies to every arm alike.

### 8.2 Cost readings

Two readings, never merged:

- **MC-A, analytic.** Multiply-adds of one whole training update (ADR-0021 §22 M6 and §22.1), checked against a FLOP count at small size. Deterministic. It is a matching rule and a counted quantity. **It is never reported as measured efficiency.**
- **MC-T, measured.** Single-thread process CPU-seconds per update from the isolated timing stage (§16). If the quiet condition is not met, MC-T is NOT MEASURED and no measured-cost comparison is made.

For each reading, the matched snapshot of the cheaper cell is the smallest of {1, 1.25, 1.5, 2, 2.5, 3, 4, 6} · U_P whose cumulative cost is at least the costlier cell's at U_P; beyond the run length the pair is MC-SHORT in that reading. The "larger of the two multipliers" rule and the comparator rule of ADR-0021 §5.4 are not used: disagreement is reported, not resolved.

## 9. Rules of block M

Panels are read separately. A favouring condition needs both panels in a replicate; a blocking condition needs either (ADR-0021 §22 (h)). The denominator is always 5.

### 9.1 Capacity step, one replicate (ADR-0021 §8.2, restated; first match wins)

Δ_MU = i(4N; U_P) − i(N; U_P). Δ_MC = i(4N; U_P) − i(N; U_MC), in reading MC-A. Δ_SAT = i(4N; U_P) − i\*(N; U_run). Δ_FULL = i\*(4N; U_run) − i\*(N; U_run).

| Order | Verdict | Rule |
|---|---|---|
| 1 | NOT_EVALUATED | REF fails for the row (R2 a_use < 0.95 at U_P on a panel), or LEAKAGE |
| 2 | DEPENDENCE_FAILED | either cell fails a qualified DEP condition at any snapshot up to its run length |
| 3 | CEILING | i(N; U_P) ≥ 4.5 |
| 4 | CAPACITY | Δ_MU ≥ 0.5; Δ_MC ≥ 0.5; Δ_SAT ≥ 0.5; the smaller cell is loaded; Δ_SAT − 2 · [i\*(N; U_run) − i\*(N; U_run/2)] ≥ 0.5; a_use(4N; U_P) ≥ 0.5 |
| 5 | GAIN WITHIN BUDGET ONLY | Δ_MU ≥ 0.5, not row 4 |
| 6 | REVERSED | Δ_MU ≤ −0.5 and Δ_FULL ≤ −0.5 |
| 7 | BEHIND WITHIN BUDGET | Δ_MU ≤ −0.5, not row 6 |
| 8 | NULL | \|Δ_MU\| < 0.25 and \|Δ_FULL\| < 0.25; both cells full; the smaller cell loaded |
| 9 | FLAT, NOT LOADED | as row 8, the smaller cell not loaded |
| 10 | UNRESOLVED | otherwise |

Different verdicts on the two panels give PANEL-DISAGREE. Where MC-T is measured, Δ_MC is also computed in it and printed; a CAPACITY verdict whose MC-T value is below 0.5 carries NOT CONFIRMED AT MEASURED CPU COST. Every threshold is ADR-0021's, fixed there before any S1 record.

**Step class** (first match): NOT_EVALUATED (≥ 2 replicates); DEPENDENCE_FAILED (≥ 2); NOT REPLICATED (≥ 2 PANEL-DISAGREE); CAPACITY STEP (CAPACITY in all 5); GAIN WITHIN BUDGET (rows 4–5 in all 5); NOT LOADED (CEILING or FLAT, NOT LOADED in ≥ 4); REVERSED (≥ 4); NO GAIN (NULL or REVERSED in ≥ 4); NOT FULL WITHIN BUDGET (the smaller cell not full in ≥ 2); MIXED.

**Arm class** (F-OQ, F-OQ-IVF, T-OQ; first match): NOT_EVALUATED (every step of a transition); DEPENDENCE_FAILED (any step); CAPACITY_SUPPORTED (a CAPACITY STEP in each of the two transitions, no step REVERSED, a_use ≥ 0.80 at 32K/16K at U_P in all 5); CAPACITY_ONE_TRANSITION (at least one CAPACITY STEP); NOT_TESTED_BY_LOAD (in some transition every step is NOT LOADED or NOT FULL WITHIN BUDGET); CAPACITY_NOT_SUPPORTED (a NO GAIN or REVERSED step in every transition and no CAPACITY STEP); INTERMEDIATE.

### 9.2 Dense comparison

**The readings.** Per arm, per larger cell of each CAPACITY STEP, d = i(arm) − i(D-OQ) in four readings: **MC-A** and **MC-T** (the cheaper of the two at its matched snapshot), **MU** (both at U_P), and **D-BEST** (the arm at U_P against D-OQ's best snapshot).

**Disclosure, placed with the rule.** In P10-S1 the readings disagreed at 32K/16K: matched compute favoured F-OQ in 5 of 5 replicates (+0.24 to +0.33 bits), matched updates favoured D-OQ in 4 of 5, and D-OQ's best snapshot in 5 of 5; ADR-0021 let any one reading block. This rule is written knowing that. It is built so that nothing the store gains from it is a relaxation: **a label that favours the store needs matched compute under both cost measures and matched updates as well.**

| Cell label | Rule |
|---|---|
| DENSE AHEAD (cell) | d ≤ −0.25 in ≥ 4 replicates in MC-A, and in MC-T where measured |
| STORE NOT BEHIND (cell) | d > −0.25 on both panels in all 5 replicates in **MC-A, MC-T and MU**; MC-T must be measured; neither matched-compute pair MC-SHORT |
| DENSE COMPARISON SPLIT (cell) | otherwise; every reading and replicate count is printed |

- *Why matched compute decides the blocking side.* An update is not a resource. D-OQ costs more per update than the store (0.0216 against 0.0124 seconds at 32K/16K in P10-S1's six-worker training, `manifests/train.manifest.json`; up to 2.5 times in multiply-adds, ADR-0021 §8.5), so at equal updates it has had more compute. A dense lead at matched updates alone gives SPLIT, not DENSE AHEAD.
- *Why matched updates is required for the favouring side.* A store that is not behind even when the dense map has had more compute is the more convincing case; requiring it removes the post-observation relaxation.
- *D-BEST is descriptive.* It gives D-OQ up to six times the updates against the store at U_P; the saturation reading already compares each at its full length.

**Dense at saturation,** per loaded cell, each arm at its own full length: DENSE HOLDS MORE (d_sat ≤ −0.25 in ≥ 4); STORE HOLDS MORE (I_use ratio ≥ 1.10 on both panels in all 5, D-OQ full, and D-OQ's cost per update at least the arm's in both cost measures, as ADR-0021 §8.5); SAME AT SATURATION otherwise, with DENSE STILL RISING if D-OQ is not full. Every dense label is printed for every cell with all four readings and D-OQ's a_use.

**Arm-level combination across cells, explicit:** DENSE AHEAD (arm) if DENSE AHEAD at every such cell, or DENSE HOLDS MORE at every loaded cell. NOT BEHIND DENSE (arm) if STORE NOT BEHIND at every such cell and DENSE HOLDS MORE at no loaded cell. DENSE SPLIT (arm) otherwise.

### 9.3 C-CAPACITY outcome (first match wins)

| Order | Outcome | Rule |
|---|---|---|
| 1 | ENGINEERING-FAILURE | an engineering gate fails, or frozen and running identities differ and cannot be restored (§18) |
| 2 | PAUSED / INCOMPLETE (status) | a registered cell has no record. PAUSED if the cause is a resource cap or a restorable identity stop; no outcome is printed and the run is resumable |
| 3 | CAPACITY-POSITIVE | F-OQ, T-OQ or F-OQ-IVF is CAPACITY_SUPPORTED and NOT BEHIND DENSE |
| 4 | CAPACITY-NEGATIVE | (a) F-OQ and T-OQ are both CAPACITY_NOT_SUPPORTED; or (b) at least one of the three is CAPACITY_SUPPORTED and every such arm is DENSE AHEAD |
| 5 | CAPACITY NOT TESTED | for F-OQ and T-OQ, every step is NOT LOADED or NOT FULL WITHIN BUDGET |
| 6 | CAPACITY-INCONCLUSIVE | otherwise, with the reason |

Printed with "1,024 TO 16,384 SLOTS", each cell's dense labels in each reading, the saturation outcome, the sparse-arm label and the tags of §1. **The lead's expectation, written before any observation under this ADR:** F-OQ shows capacity steps; DENSE HOLDS MORE at saturation is likely again; CAPACITY-NEGATIVE by clause (b) is the single most likely outcome unless the rate search changes the picture.

### 9.4 C-SATURATION

S(N) = F · i\*(cell at its full length), ρ = S(4N)/S(N), b(N) = S(N)/N. Pair verdict, class, arm class and outcome are ADR-0021 §8.10's with the threshold 3.0 unchanged and two changes: NOT FULL means NOT FULL WITHIN BUDGET under §7.2; and every replicate is printed on both panels with ρ, the last ladder gain and its full status, including replicates that are not full (audit D2, D9). Registered pairs: 256→1,024 (F-OQ) and 1,024→4,096 (F-OQ, F-OQ-IVF, T-OQ). Outcomes: SATURATION-PROPORTIONAL, -SUBPROPORTIONAL, NOT MEASURED, -INCONCLUSIVE. The crowding figures are printed beside every ρ; a SUBPROPORTIONAL verdict is never read as a property of the store alone.

### 9.5 C-EFFICIENCY and the dense-speed rule

The line reads the control steps N1 and N2. Level i_T = 3.0 bits; u_T, censoring, c_T and the step verdicts are ADR-0021 §8.8's, with one change: **every verdict that uses cost is computed once per cost reading**, giving readings E-A and E-T, each with its own step and arm classes.

**Dense speed, per FASTER-STEP larger cell, per reading:** DENSE FASTER if D-OQ's c_T is at most 0.8 of the arm's in ≥ 4 replicates; DENSE NOT FASTER if it is above 0.8 in all 5; DENSE SPEED UNDECIDED otherwise. **Every cell and reading is printed.**

| Order | Outcome | Rule |
|---|---|---|
| 1 | ENGINEERING-FAILURE | as §9.3 row 1 |
| 2 | PAUSED / INCOMPLETE | as §9.3 row 2 |
| 3 | EFFICIENCY-POSITIVE | F-OQ or T-OQ is EFFICIENCY_SUPPORTED in **both** E-A and E-T, and is DENSE NOT FASTER at **every** FASTER-STEP cell in **both** readings |
| 4 | EFFICIENCY-NEGATIVE | F-OQ and T-OQ are both EFFICIENCY_NOT_SUPPORTED in both readings; or at least one is EFFICIENCY_SUPPORTED in both and every such arm is DENSE FASTER at **every** FASTER-STEP cell in **both** readings |
| 5 | EFFICIENCY-INCONCLUSIVE | otherwise, with the reason: DENSE SPEED SPLIT (cells and readings named), READINGS DISAGREE, MEASURED COST NOT AVAILABLE |

**Disclosure, placed with the rule.** For a positive this is the same as P10-S1's any-cell block. The change is on the negative side, which becomes harder to reach, and it was written after P10-S1's values were seen. On P10-S1's records D-OQ was faster at 2K/4K in both readings (CPU ratio 0.083–0.118, multiply-adds 0.32–0.46) and at 8K/16K in CPU only (0.27–0.38 against 1.32–1.87). Under this rule P10-S1's registered EFFICIENCY-NEGATIVE would have been **EFFICIENCY-INCONCLUSIVE (DENSE SPEED SPLIT; READINGS DISAGREE)**. P10-S1's label is not revised. The reason for the rule is the acceptance's ruling 2: a label is not evidence about a cell or a reading it did not hold in.

### 9.6 Descriptive labels (enter no outcome)

- **Sparse arms.** T-OQ against F-OQ-IVF at equal candidate count, on I_use at 8K/4K and 32K/16K: ratio ≥ 1.03 AHEAD, ≥ 0.97 COMPETITIVE, otherwise BEHIND, in ≥ 4 replicates at both cells. Read at U_P and at the run length; both labels are printed and neither is called "the" label. It may not be cited to select a routing design; that is ADR-0029's subject.
- Counted work per query, ADR-0021 §7.4. Logical counts; not measured efficiency.
- Read-path throughput (RAM, one process, quiet condition met), ADR-0021 §7.5; THROUGHPUT NOT MEASURED otherwise.

## 10. What an unmet quiet condition makes unreachable

If MC-T is NOT MEASURED (§16):

| Line | Unreachable | Still reachable | Printed |
|---|---|---|---|
| C-CAPACITY, X-CAPACITY | CAPACITY-POSITIVE (STORE NOT BEHIND needs MC-T) | NEGATIVE (a); NEGATIVE (b) through MC-A or saturation; NOT TESTED; INCONCLUSIVE | "MEASURED COST NOT AVAILABLE: a positive was not reachable" |
| C-EFFICIENCY | POSITIVE and NEGATIVE (both need E-T) | INCONCLUSIVE only | EFFICIENCY-INCONCLUSIVE (MEASURED COST NOT AVAILABLE), with E-A printed as counted work |
| C-SATURATION | STORE HOLDS MORE AT SATURATION (cost condition) | every saturation outcome | the same sentence beside the dense-at-saturation label |

The study is still complete. The human lead is told before training starts if the timing stage ended NOT MEASURED, so that he can give it a window first.

## 11. Order of work

Independent review of this draft → the human lead's approval → implementation with tests and an independent implementation audit → calibration (§7.1 order) → rehearsal of every registered stage end to end against the frozen plan itself → freeze of block M → the human lead's Decision 2 → one registered run → independent recomputation from raw records (the auditor receives the specification, code and records, not the lead's conclusions) → outcome record → the human lead's acceptance. Block X and lane L each have their own freeze and decision after that.

## 12. Block X — the transition 16,384 → 65,536 (conditional, separately funded)

The human lead named this transition for P10-I (`ACCEPTANCE.md`). It stays in this ADR as its own stage with its own line, so that adding cells cannot make block M's outcome harder to reach in either direction (review §C).

- **Cells.** 128K/16K (load 8) and 128K/64K (load 2): loaded step C3. 32K/16K (re-used from block M) and 32K/64K (load 0.5): control step N3. R2 at 128K/128K. Arms F-OQ, T-OQ, D-OQ. Per replicate 3 × 3 + 1 = 10; five replicates: **50 cells.** The draws are block M's, their fact tables extended to 131,072.
- **Entry condition, fixed now (PENDING HUMAN LEAD RULING, §21 item 2).** Block M is complete and accepted, and F-OQ's step C2 (4,096 → 16,384) is a CAPACITY STEP there. Reason: without a replicated step at the transition below, a step above it has nothing to extend. The dense labels of block M do not enter the condition. If it is not met: X-CAPACITY is NOT TESTED — ENTRY NOT MET.
- **Rules.** Rates, U_P, run-until-full, DEP, step verdicts and the dense labels are those of §7–§9 applied to C3 and N3 alone, with units 65,536 slots (selection cell 128K/64K; provisional readout 32,768) and the loaded cell 128K/16K. X-CAPACITY is §9.3's table with "CAPACITY_SUPPORTED" read as "C3 is a CAPACITY STEP and a_use ≥ 0.80 at 128K/64K at U_P in all 5". No saturation or efficiency outcome is registered for block X: the pair 4,096 → 16,384 compares code crowding of 0.85 with 0.999 (§2 item 11) and is printed as CONFOUNDED BY CODE CROWDING; N3 is printed descriptively.
- **Budget rule.** The loaded cell runs until full within **the block's hour budget, which the human lead sets after the block's rehearsal**. A cell stopped by that budget is PAUSED and resumable; a cell that reaches 4 · U₀ is NOT FULL WITHIN BUDGET.
- **Cost: it cannot be bounded without a rehearsal, and funding is a separate decision after it.** Nothing at 65,536 slots was timed in P10-S1; the only figures are 0.035–0.049 s per update for the flat memory (P9-I rehearsal) and 0.071–0.077 for D-OQ (revision 4's calibration), ADR-0021 §1 facts 7 and 17. U₀ at 128K/16K and U_P of the 131,072-fact row are unknown.

| Case | 128K/16K (3 arms × 5) | 128K/64K and 32K/64K | Calibration | Block X, charged hours (six workers) |
|---|---|---|---|---|
| Low | U₀ ≈ 0.79 million updates, full at U₀: about 9 | U_P 16,384: about 8 | about 8 | **about 25** |
| Central | U₀ ≈ 1.57 million (twice 32K/4K's 786,432, as that was twice 8K/1K's), full at U₀: about 19 | U_P 32,768: about 14 | about 14 | **about 45–50** |
| Upper | every cell to 4 · U₀: about 75; one D-OQ cell alone about 38 hours of wall time | U_P 65,536: about 28 | about 20 | **over 120** |

The figures use P10-S1's measured seconds per update at 16,384 slots (F-OQ 0.0124, T-OQ 0.0147, D-OQ 0.0216) and the older figures above at 65,536; T-OQ at 65,536 is assumed, not measured. The central case is about twice the whole of P10-S1 (25.39 charged hours). The block's rehearsal measures: seconds per update of every arm at 65,536 slots; evaluation seconds per snapshot at 131,072 facts; peak memory (the separability measure alone forms blocks of about 1 GiB at 131,072 facts, against the 3 GiB guard); and the crowding figure. It observes no registered seed.

## 13. Lane L — learned addressing (conditional on ADR-0023's licence)

Without this lane nothing in the programme registers capacity under learned addressing.

- **Entry.** ADR-0023's outcome, recomputed and accepted before this lane's freeze, with a qualified load L_Q (ADR-0023 §15). The lane uses A5-D exactly as ADR-0023 freezes it (μ = 1.0, its code hash, the duration T of each cell type) and nothing else.
- **Cells: licensed cell types only.** Of this ADR's grid, ADR-0023 tests 2K/4K and 8K/16K (load 0.5), 2K/1K and 8K/4K (load 2), and 8K/1K (load 8, only if its conditional series runs). A cell is run only if its load is at most L_Q. The rows of 32,768 and 131,072 facts are not licensed. An unlicensed cell prints OMITTED — ADDRESSING NOT QUALIFIED AT THIS CELL (ADR-0023).
- **Steps available.** N1 and N2 if L_Q ≥ 2; C1 also if L_Q ≥ 8. If L_Q < 2 no step exists and the lane is OMITTED — NO LICENSED STEP.
- **Arm and comparator.** F-LA at each licensed cell, five replicates on this study's draws, each cell at ADR-0023's T. F-OQ of the same cell and replicate is read at the same update count (a snapshot is added there). One change: the query.
- **Measure.** A fact is dependently retained if it is answered correctly with the memory and not with the memory disabled; i_L is the information measure on that share. ADR-0023's cell-success composite is applied unchanged as a validity gate: a cell that fails it is NOT QUALIFIED AT RUN and its steps are NOT EVALUABLE. (The oracle's address swap is not defined for a learned query; **this measure is the lead's choice, PENDING HUMAN LEAD RULING**.)
- **L-CAPACITY** (first match): OMITTED — NOT LICENSED (with the reason); NOT EVALUABLE (a licensed step has a NOT QUALIFIED AT RUN cell in ≥ 2 replicates); **LEARNED-ADDRESS GAIN FROM SLOTS** (i_L(4N) − i_L(N) ≥ 0.5 on both panels in all 5 replicates at every licensed step); **LEARNED-ADDRESS NO GAIN** (|difference| < 0.25 on both panels in ≥ 4 replicates at every licensed step); LEARNED-ADDRESS INCONCLUSIVE otherwise. Printed with the licensed steps, the ratio of F-LA's to F-OQ's information per cell, and ADR-0023's reference regime and convergence status per cell type. It carries `LEARNED-ADDRESS; FLAT MEMORY; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK`. It is never merged with, and never changes, an oracle line.
- **Timing (§21 item 3).** A qualification recorded after block M's freeze changes nothing in block M. Lane L is its own frozen stage: if ADR-0023's outcome is not accepted when block M freezes, block M's report prints **Lane L: OMITTED — NOT LICENSED AT THE FREEZE**, and the lane may be frozen and run later under its own decision.
- **Cost.** Unknown until ADR-0023 fixes its durations (it allows up to 16,384 exposures per fact, about 1 million updates and 3 hours for one 8,192-fact cell). At most 25 cells; of the order of 5–15 charged hours. Funded by a separate decision.

## 14. Stop rules and NOT EVALUABLE outcomes

- A failed engineering gate stops a stage before training.
- A registered cell that fails for a reason other than a cap or a restorable identity stop is kept and not re-run; the stage is INCOMPLETE and a second attempt is the human lead's decision.
- A stop on a resource cap is PAUSED. Completed cells are not recomputed.
- No registered seed is observed before Decision 2, apart from G1. The frozen code's own use of a cell's plateau statistic (§7.2) is not an observation by the lead.
- REF failure: the replicate is NOT_EVALUATED for the row. LEAKAGE: NOT_EVALUATED for the cells concerned.
- No stage is re-run with changed settings. No threshold, seed, replicate count or rule changes after the freeze.

## 15. Limits, classified (DIRECTION.md §5)

| Limit | Kind | Rule |
|---|---|---|
| Hour cap of block M, of block X, of lane L; per-stage caps; 3 GiB per worker, 18 GiB aggregate | Resource cap | Set after the rehearsal as charged + 2 × projected remaining, rounded up to the hour. Extended by the human lead on cost projections only, never on outcome values. A stage that reaches its cap is **PAUSED**, keeps its completed cells and resumes |
| Calibration budget (U_P ladder, rate search, load search) | Resource cap | As above; a search stopped by it is PAUSED, not "no U₀" |
| Loaded-cell run length (4 · U₀); rate grid (two extensions); one re-selection of rates | Design ceiling | Extended only by the rules of §7. Reaching it gives NOT FULL WITHIN BUDGET or RATE AT EDGE. No ceiling is raised because a partial result looks close |
| Five replicates; block X and lane L entered or not | Design ceiling | Never reduced after a freeze; entry by the conditions of §12 and §13 |
| 0.5, 0.25, 0.10, 0.473, 4.0, 4.5, 3.0, 0.8, 1.10, 0.90, 0.95 (REF), 0.80, 4-of-5 and 5-of-5, the DEP-c figures | Scientific threshold | Never changed after the freeze |

## 16. Stages and machine load

The machine is also the human lead's working computer. Platform of record: macOS arm64 (the M5 Max of ADR-0021 §10.3), CPU only. Bit-exact assertions are made on it only. Checks (`ruff`, `mypy`, `pytest`) run locally; a GitHub run is not required.

| Stage | Quiet condition? | How it is met, and what follows if it is not |
|---|---|---|
| Timing preview and isolated timing (202–376 s each in P10-S1's ledger) | **Yes.** One-minute load average ≤ 1.0, **measured at the stage's start**; no figure for the machine's usual load is assumed. P10-S1 passed at 0.98–0.998 on its first to third reading | Retried every 10 minutes for up to 6 hours, or run in a window the human lead names. After the deadline: MC-T NOT MEASURED, with the consequences of §10 |
| Read-path throughput (about 7 minutes) | **Yes**, same rule and deadline | THROUGHPUT NOT MEASURED (descriptive only) |
| Calibration, rehearsal, generate, gates, train, evaluate, analyze, report | No | No rule uses their wall time. CPU-seconds per snapshot are recorded descriptively |

## 17. Cost projection for block M (estimates, to be replaced by the rehearsal)

Measured basis: P10-S1 attempt 2 charged 49,251 s for 178 training cells and 1,899 s for evaluation with six workers; all attempts and calibration charged 25.39 h, of which revision 5's calibration was 18,683 s (`ledger_after_run.json`, `OUTCOME.md` §1). Median training seconds per update in that run (`manifests/train.manifest.json`): F-OQ 0.0060 at 2K/1K and 0.0050 at 8K/1K (1,024 slots), 0.0081–0.0092 at 4,096, 0.0124–0.0136 at 16,384; T-OQ 0.0116–0.0147; D-OQ 0.0051, 0.0088–0.0104, 0.0177–0.0216; peak 0.39 GiB per worker. The rehearsal's contention ratio was 1.946 (worst D-OQ at 1,024 slots), measured while the desktop was under unrelated load of about 5.4 (ADR-0021 §25.16).

| Item | Low | Central | Upper |
|---|---|---|---|
| Training, 120 cells, at P10-S1's lengths (H8 and the seed block out) | 9 | 10 | 12 |
| Loaded cells continuing beyond U₀ | 0 | 3 | about 25 (every loaded cell to 4 · U₀) |
| Calibration: five rates × two draws for four arms, one re-selection, run-until-full load search, 2K/256 | 8 | 10 | 14 |
| Evaluation, rehearsal, gates, timing | 2 | 3 | 4 |
| **Block M, charged hours** | **about 19** | **about 26** | **about 55** |

The cap by the twofold rule would be of the order of 50 hours in the central case. The rehearsal measures, before any cap is set: seconds per update per arm and size; the contention ratio at six workers and at one higher count; evaluation seconds per snapshot with DEP at every snapshot; peak memory.

## 18. Engineering requirements carried from P10

| P10 failure | Requirement here |
|---|---|
| A status note committed to a frozen ADR stopped 171 cells (ADR-0021 §25.19–25.20) | **One frozen-input set per freeze (block M, block X, lane L), and the ADR text is not in it.** The set is: `studies/p10is1/**`, the stage's config (which holds every threshold and rule parameter), launch scripts, `freeze/plan.json`, stage caps, calibration records and data manifests. Identity is by SHA-256 of each listed file, recorded in the freeze record; no task compares against a commit. The freeze record also stores the ADR's hash for provenance only. Nothing is written in the frozen files between Decision 2 and the end of the report stage; status and notes go to the human lead directly or to another branch. A task that finds an identity difference stops as PAUSED — IDENTITY; if the file is restored bit for bit the stage resumes and completed cells are kept. A test asserts that every threshold in this ADR's tables equals the config's value |
| The throughput stage's item list did not match the frozen plan; the tests used another plan (§25.21) | Every registered stage is rehearsed end to end on the rehearsal draw **against the frozen plan file itself**; each stage's item list is derived from that file only; a stage whose items are not all in the plan refuses at the freeze |
| An unstated combination rule; a check the reference fails; a report section comparing the wrong reads (audit D4, D7, D1) | Every reading and combination rule is in §8–§9, §12, §13. R2 is run through every validity check in the rehearsal and a check it fails is not used (§8.1). **The analysis and the report are tested on a synthetic registry with known answers that covers every verdict, class, label and outcome and every descriptive section:** each registry key carries the read's name, two reads of one cell can never share a key, and a test plants distinct values in every read and asserts each printed figure. The report prints every replicate, panel, cell and reading a rule names (audit D2, D3, D6, D9, D10, D12) |
| A count gate stopped P10-S2 although its quality criteria were met | Loaded cells run until full within a stated budget; searches extend by rule (§7) |
| P10-S0 tested overload at one load and one length | Not this study's question (ADR-0023); loaded cells here run to a convergence rule |
| A tie test passed on macOS and failed on Linux (§25.23) | The platform of record is named (§16); exact reproduction (G4) is asserted on it only |
| GitHub CI is costly | Checks run locally (§16) |

## 19. Hypothesis-level expectations and decision map (recommendations only)

CAPACITY-NEGATIVE (b) → on this task the dense map is the better use of the parameters; what the store offers must then be shown elsewhere (sparse updates, measured cost, storage), in studies designed for it. CAPACITY-POSITIVE → the necessary condition is met at these sizes; block X asks whether it extends. Any INCONCLUSIVE → no decision on that line. L-CAPACITY, whatever it is, is the first registered reading of capacity under learned addressing and is reported apart.

## 20. What this study cannot establish

- Anything about the language model forming queries, natural language, or capability beyond recall of trained random facts. Lane L's result holds for one recipe, a flat memory and the licensed cells only.
- Value beyond a lookup table (§3). Efficiency, latency, energy or I/O of any system: counted work and MC-A are logical; MC-T and throughput are in-RAM CPU figures for a 27,392-parameter backbone on one machine.
- Capacity above 16,384 slots unless block X runs; then for one transition, one row and crowded codes.
- That a SUBPROPORTIONAL saturation verdict is a property of the store. A capacity "per slot" in general.
- That the store or the dense map is better "when tuned": each has one family and one grid, with the rate chosen at 65,536 updates at loaded cells.
- Whether learned keys add anything over hashed slots under tuned rates (H8 is not run).
- Why the tree is behind the flat memory, or what would fix it (ADR-0029). Whether longer training closes that gap (ADR-0026).
- TRANSFER or SYSTEM outcomes, Astra validation, or any approval not recorded.

## 21. Open choices reserved for the human lead

1. **Task (§3).** Keep the task with every label capped at "necessary condition" (recommended), or hold the study until a task a lookup cannot solve is designed.
2. **Block X (§12).** Keep it conditional with the entry condition stated, and decide funding after its rehearsal (recommended); or enter it unconditionally; or leave 16,384→65,536 NOT FUNDED. **PENDING HUMAN LEAD RULING.**
3. **Lane L and the freeze (§13).** Block M does not wait for P10-I-S0; lane L is a later frozen stage (recommended). Or block M's freeze waits. **PENDING HUMAN LEAD RULING.**
4. **Dense reading (§9.2).** Favouring needs MC-A, MC-T and MU; blocking needs matched compute; D-BEST descriptive (recommended, as the review proposes). Or keep P10-S1's "any one reading blocks". **PENDING HUMAN LEAD RULING.**
5. **H8.** Not run (recommended), or kept at the two loaded cells at about 1 more charged hour at P10-S1's lengths (H8 took 1,619 s and 3,204 s per cell there), or at all seven cells at about 1.5.
6. **Symmetric split rule (§9.2, §9.5).** Positive and negative each need every cell and both readings (recommended), or a conservative any-cell block.
7. **DEP-c's floor of 0.01 and lane L's dependence measure** (§8.1, §13). **PENDING HUMAN LEAD RULING.**
8. **The split of the routing diagnosis into ADR-0029.** Recommended by the reviewer and the lead. **PENDING HUMAN LEAD RULING.**
9. **Worker count.** Six as in P10-S1, or the count the rehearsal finds cheaper in charged hours.

## 22. Review record

Independent review by the `arbor-auditor` subagent (Claude Opus 5.5): `docs/reviews/p10-i-spec-reviews-2026-11-17/REVIEW_ADR-0024.md`, verdict NOT READY (2 blocking, 15 required, 12 advisory by its own count). This revision is by the lead's workflow (Claude Fable 5.2). It has not been re-reviewed. Neither is Astra validation or a human approval.

| Finding | Severity | Disposition | Where |
|---|---|---|---|
| F1 U_P and rates circular; R2 and D-OQ units | BLOCKING | FIXED | §7.1 |
| F2 tree label misassigns causes | BLOCKING | MOVED TO ADR-0029 | ADR-0029 §6–§8 |
| F3 N/8 | REQUIRED | MOVED TO ADR-0029 | ADR-0029 §8 |
| F4 matched compute primary after observation | REQUIRED | FIXED | §9.2 |
| F5 efficiency rule's effect on P10-S1; rows 1–2 | REQUIRED | FIXED | §9.5 |
| F6 DEP snapshots; i\* snapshots; audit result | REQUIRED | FIXED | §2 item 10, §8.1, §9.1 row 2 |
| F7 DEP-c reasons | ADVISORY | FIXED (reasons rewritten); p⁺ kept and stated as deliberately conservative | §8.1 |
| F8 U_P / run length | REQUIRED | MOVED TO ADR-0029 | ADR-0029 §9 |
| F9 R-CONFIRM not like for like | REQUIRED | MOVED TO ADR-0029 | ADR-0029 §10 |
| F10 cost projection | REQUIRED | FIXED: low, central, upper for both blocks; block X stated as unbounded before its rehearsal | §12, §17 |
| F11 recall records misdescribed, unsealed | REQUIRED | MOVED TO ADR-0029 | ADR-0029 §4, §11 |
| F12 one ADR, two freezes | REQUIRED | FIXED: split; ADR text is not a frozen input | header, §18 |
| F13 PK-OQ | REQUIRED | FIXED: removed | §4 |
| F14 quiet-machine rule | REQUIRED | FIXED | §10, §16 |
| F15 disclosure placement | REQUIRED | FIXED | §8.1, §9.2, §9.5 |
| F16 Lane R gates | REQUIRED | MOVED TO ADR-0029 | ADR-0029 §11 |
| F17 snapshot schedule; arm names; cost of NOT FULL | REQUIRED | FIXED | §7.2, §12 |
| F18 crowding at 131,072 | ADVISORY | FIXED: figure printed; saturation pair descriptive | §2 item 11, §12 |
| F19 dropping H8 | ADVISORY | ANSWERED: still not run; the loss is stated and the choice is open | §4, §20, §21 item 5 |
| F20 bridge duplication | ADVISORY | MOVED TO ADR-0029 (the bridge is always at 0.003 on its own draws there) | ADR-0029 §10 |
| F21 measurement definitions | ADVISORY | MOVED TO ADR-0029 | ADR-0029 §6–§7 |
| F22 STORE HOLDS MORE cost condition | ADVISORY | FIXED | §9.2 |
| F23 quotation details | ADVISORY | FIXED (0.0060 / 0.0050; idle load removed). ANSWERED for 1.946: "under unrelated load" is from ADR-0021 §25.16, now cited | §16, §17 |
| F24 replicate accounting | ADVISORY | MOVED TO ADR-0029 | ADR-0029 §8 |
| F25 tags; "necessary condition" wording | ADVISORY | FIXED | §1 |
| F26 a_use floor; "in bits" | ADVISORY | FIXED here for the floor; the rest MOVED TO ADR-0029 | §8.1 |
| F27 seeds | ADVISORY | ANSWERED: data namespace kept; all other seeds go to the seed registry | §6 |
| §C block X conditional; smallest coherent study | — | FIXED: block M is the reviewer's smallest study; block X is conditional with its own line | §0, §12 |

Added in this revision and not yet reviewed: lane L (§13), block X's entry condition and separate line (§12), §10.

`Astra review: NOT_PERFORMED`.
