# ADR-0024 — P10-I-S1 — useful capacity scaling

**Status: BLOCK M APPROVED FOR IMPLEMENTATION AND REHEARSAL (Decision 1) by the lead under the human lead's delegation of 2026-11-18. Lane L and block X are not approved. Not frozen. No registered run is approved.**

- **Date:** 2026-11-18 (UTC). Draft 3 with the edits of the third review applied. Draft 1 was revised after the independent specification review (`docs/reviews/p10-i-spec-reviews-2026-11-17/REVIEW_ADR-0024.md`, NOT READY), draft 2 after the confirmation review (`REVIEW2_ADR-0024_ADR-0029.md` beside it, NOT READY), and draft 3 after the third review (`REVIEW3_ADR-0024.md` beside it; block M READY AFTER THE LISTED EDITS, block X NOT READY, lane L outside the approval). §22 maps every finding of all three to its disposition; §23 holds the rulings for the implementer; §24 is the approval record. The text with the third review's edits applied has not been reviewed again. Nothing under this ADR is implemented, calibrated, frozen or run. **SPEC: PENDING ASTRA REVIEW.** `Astra review: NOT_PERFORMED`. Claude review is not Astra review.
- **Study code** P10IS1. **Package** `studies/p10is1/` (new code only). **Config** `configs/p10is1_capacity.toml`. **Tests** `tests/test_p10is1_*.py`.
- **Origin.** `docs/reviews/p10-i-direction-2026-11-17/DIRECTION.md` (sections 2, 4, 5, 7). Successor of P10-S1 (ADR-0021), whose registered outcome the human lead accepted as recorded (`results/p10s1-run-2026-11-17/ACCEPTANCE.md`).
- **The routing diagnosis moved to ADR-0029.** Draft 1 held a second lane, the frozen-checkpoint routing diagnosis. It is now `docs/decisions/ADR-0029-p10-i-r-routing-diagnosis.md`. Reason: the two lanes share no rule, budget or frozen input, and one ADR hashed into two freezes repeats the failure that cost P10-S1 attempt 1. The human lead's direction (`LITERATURE_AND_ROUTING_NOTE.md` §5.4) placed that lane inside ADR-0024; the split was the reviewer's and the lead's recommendation and the human lead ruled on 2026-11-17: "Keep ADR-0029" (§21 item 8). This file was renamed accordingly.
- **Immutability.** P1–P10 code, configs, records, thresholds, seeds and outcomes are not edited, revised or reopened. P10-S1's labels stand as registered. ArborLM is unproven research; no label below is a success claim.
- **Approval.** The P10 delegation of 2026-11-15 does not cover P10-I. Decision 1 for block M was taken by the lead under the human lead's delegation of 2026-11-18 (`docs/reviews/p10-i-direction-2026-11-17/DELEGATION_2026-11-18.md`; §24). It covers implementation and rehearsal of block M only. Block X, lane L, the freeze and the registered run are not approved. The choices of §21 are ruled there; a few stay with the human lead himself and are marked so.
- **Roles.** Specification review, implementation audit and recomputation: Opus 5.5 in a context separate from the implementation. Implementation: Sonnet 5.5. Inventory: Haiku 5.5. The model that ran each delegated task is recorded from session metadata. ADR-0012 stays not approved.

## 0. Structure

| Part | What | Outcome lines | Status in this text |
|---|---|---|---|
| **Block M** | P10-S1's seven cells and 2K/256 on fresh seeds, with the audit's corrections and an equal rate search | C-CAPACITY, C-SATURATION, C-EFFICIENCY | Specified in full. **Approved for implementation and rehearsal (Decision 1, §24).** Not frozen; no registered run approved |
| **Block X** (later, own decision) | The transition 16,384 → 65,536 slots, on its own fresh draws | X-CAPACITY | **Not approved with this text.** Reduced to what is settled and a list of what a revision must add (§12) |
| **Lane L** (later, own decision) | Learned addressing at the cells ADR-0023 licenses | L-CAPACITY, tagged LEARNED-ADDRESS | **Not specified enough to approve; not approved with this text** (§13) |

No line implies, substitutes for or is merged with another. Block X and lane L change no block M label. **Nothing in block M depends on block X or on lane L**: no cell, snapshot, seed, rule, budget, rehearsal or freeze.

## 1. Question, and what each outcome would mean

With addressing supplied by an oracle, and every trained arm given the same rate search: does a larger store retain more useful information about a fixed fact set at matched updates, at matched compute and against the smaller store when full; does a full store keep its bits per slot as it grows; does a larger store reach a fixed level sooner; and how does each compare with a dense map of equal parameters?

| Line | Positive would mean | Negative would mean | Inconclusive / not tested |
|---|---|---|---|
| C-CAPACITY | Within the sizes read, the store passes a necessary condition of the storage claim, and the dense map of equal size is not ahead in any of the dense readings or when full | The store does not gain from slots, or it does and the dense map is ahead in any one reading at any cell read, or holds more at saturation at any loaded cell (as ADR-0021) | No decision; the reason is printed |
| C-SATURATION | A full store kept at least three quarters of its bits per slot per fourfold step | It did not, for both the flat and the tree memory | A size was not full within its budget, or the arms disagree |
| C-EFFICIENCY | A larger store reached 3.0 bits per fact in fewer updates and less cost under **both** cost readings, and the dense map was not faster at any cell under either | No arm did in one of the readings, or the dense map was faster at one or more cells in one or more readings | The readings disagree on the store's own classes; each is printed |

X-CAPACITY (the transition 16,384 → 65,536) is block X's line. It is not specified or approved here (§12); block M's report prints "16,384→65,536 NOT TESTED — BLOCK X NOT APPROVED" beside every capacity outcome.

Every label carries `STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK`. No outcome of this ADR can establish milestone question 1. The reading available is "necessary condition met / not met / not established"; it is never paraphrased as part or half of the storage claim.

## 2. Background: registered findings (quoted from the records)

From `results/p10s1-run-2026-11-17/OUTCOME.md`, `ACCEPTANCE.md`, `audit/AUDIT.md`:

1. Registered outcome: CAPACITY-INCONCLUSIVE (F-OQ DEPENDENCE_FAILED; F-OQ-IVF DEPENDENCE_FAILED; T-OQ INTERMEDIATE; 16,384→65,536 NOT TESTED); SATURATION-INCONCLUSIVE (F-OQ INTERMEDIATE; T-OQ SATURATION_NOT_MEASURED); EFFICIENCY-NEGATIVE (DENSE FASTER); milestone question 1 not established. Also TREE_BEHIND, DICT DOMINATES ON THIS TASK, DENSE HOLDS MORE AT SATURATION for F-OQ, F-OQ-IVF and T-OQ.
2. **Dependence (audit §2, D7).** Every DEPENDENCE_FAILED verdict comes from `a_use ≥ 0.95 × raw accuracy` at 1,024–2,048 updates, at a_use 0.256–0.414 (ratios 0.9262–0.9486 across arms; 0.9425–0.9471 for the F-OQ and F-OQ-IVF failures at 2,048 updates). The reference arm R2 fails the same condition 12 times at 512–1,024 updates.
3. **Dense speed (audit §3, D4).** DENSE FASTER for T-OQ holds in 5 of 5 replicates at 2K/4K and 0 of 5 at 8K/16K. At 8K/16K, D-OQ's cost to reach the level is 0.27–0.38 of T-OQ's in measured CPU seconds and 1.32–1.87 of it in analytic multiply-adds. The code applied an any-cell rule (`studies/p10s1/analysis.py`, line 631) that ADR-0021 §8.8 does not state.
4. **Dense quality (audit §5, D3).** At 32K/16K, F-OQ against D-OQ: matched updates d = −0.238 to −0.450 bits (4 of 5 at or below −0.25); matched compute d = +0.24 to +0.33 (F-OQ ahead, 5 of 5); D-OQ's best snapshot d = −0.68 to −0.87 (5 of 5). At saturation D-OQ holds 1.76–1.87 bits per fact more than F-OQ at both loaded cells (5 of 5).
5. **Seed block (audit D1; `ERRATUM_SEED_BLOCK.md`).** `analysis.py` lines 167–169 store two reads under one key; 28 printed lines are wrong (corrected: the data draw dominates in 24 of 28).
6. **Saturation (audit §4).** 1,024→4,096: F-OQ ρ 3.785–3.875 (PROPORTIONAL, 5 of 5); T-OQ ρ 2.389–2.922 with two replicates NOT FULL at 8K/1K (last-doubling gains 0.1059 and 0.132 against the limit 0.10). 2K/256 was not full within its ceiling of 262,144 updates and was not run; 128K/16K was not funded (ADR-0021 §5.1, §25.15). The registered run lengths of the loaded cells were 393,216 (8K/1K) and 786,432 (32K/4K).
7. **Rates.** Memory arms ran at 0.003, untuned by design; D-OQ at its calibrated 0.1 or 0.03 (audit §6; ADR-0021 §10.1 item 3).
8. **Lane L** was OMITTED — NOT OVERLOAD-QUALIFIED (ADR-0021 §25.17). No study has registered capacity under learned addressing.
9. **Never run:** any cell at 65,536 slots under ADR-0021 revision 5; 128K/16K beyond 65,536 updates (revision 4's calibration saw 1.46–1.52 bits per fact there, still gaining 0.54–0.62 per doubling; ADR-0021 §1 fact 13).

From the first review (`REVIEW_ADR-0024.md` F6, F18; the reviewer's own scripts on P10-S1's recorded counts; the lead has not recomputed them):

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
| **H8** | Hashed exact address: 8 distinct slots from a seeded hash of the fact's identifier, weights 1/8, slots shared between facts — ADR-0021 §3 | values, projection, gate | The fixed-address control: what learned keys add |
| **R2** | One dedicated slot per fact | values, projection, gate | Reference rung; validity of every check (§8.1) |
| F-OQ-IVF (evaluation only) | F-OQ's keys read through the registered index (N/256 lists, at least 512 candidates) | nothing | Post-hoc sparse retrieval, as P10-S1 read it |
| DICT, no-memory, unseen-fact control, KNN-W, KNN-W-IVF | ADR-0021 §5.5 | nothing | Lookup baseline; chance; leakage; a non-oracle baseline |

One change per comparison: cells of one row differ only in slots; arms at one cell differ only in the addition.

- **No product-key arm.** Draft 1 added one. The note's §5.2 places product-key memory in Stage B of the routing work, and a new architecture is a separate study (§5.4). It is removed from this ADR.
- **H8 is kept, at all seven cells ADR-0021 ran it** (2K/1K, 2K/4K, 8K/1K, 8K/4K, 8K/16K, 32K/4K, 32K/16K; not 2K/256). Drafts 1–3 left it out and listed that as an open choice; the third review (F17) pointed out that H8 is the only check that can count against learned keys, so leaving it out leans towards the store. The open choice is removed (§21 item 5). Its rules are ADR-0021's, unchanged:
  - H8 carries the capacity step verdicts and arm class of §9.1 and the saturation pair 1,024 → 4,096 of §9.4. **H8 alone cannot give CAPACITY-POSITIVE or SATURATION-PROPORTIONAL**, and it does not enter §9.3 row 4 (a) (ADR-0021 §8.7, §8.10, §22.1). Its classes are printed beside the outcomes.
  - **KEY-LEARNING-LIMITED** if H8 is CAPACITY_SUPPORTED and F-OQ is not (ADR-0021 §8.5). It is a printed label and enters no outcome.
  - **UNDERTRAINED-AT-U_P** is carried by H8's classes at any cell where its calibration a_use was below 0.90 at U_P on either calibration draw or panel (ADR-0021 §8.4, §10.1 item 2). The calibration reads H8 at U_P at the selection cells of its rate units (§7.1) and, at its selected rate, at 2K/4K and 8K/16K (four runs to U_P). At the two loaded cells, whose rate unit is read at 65,536 updates, its classes carry **H8 NOT CALIBRATED AT U_P AT cell**. H8 gates nothing.
  - H8 goes through the equal rate search like every trained arm (§7.1). In P10-S1 it ran at 0.003, untuned. Its hash seed is the draw set's base + 40 (P10-S1's in-set layout).

## 5. Grid and steps (block M)

"8K/1K" is 8,192 facts in 1,024 slots. Load is facts per slot.

| Facts \ Slots | 256 | 1,024 | 4,096 | 16,384 |
|---|---|---|---|---|
| 2,048 | 2K/256 (8; F-OQ only) | 2K/1K (2) | 2K/4K (0.5) | |
| 8,192 | | 8K/1K (8) | 8K/4K (2) | 8K/16K (0.5) |
| 32,768 | | | 32K/4K (8) | 32K/16K (2) |

- Loaded steps: C1 (8K/1K→8K/4K), C2 (32K/4K→32K/16K). Control steps: N1 (2K/1K→2K/4K), N2 (8K/4K→8K/16K). Transitions 1K→4K and 4K→16K. Saturation cells (load 8): 2K/256, 8K/1K, 32K/4K.
- **Trained configurations per replicate:** F-OQ 8, T-OQ 7, H8 7, D-OQ 6 (2K/4K, 8K/4K, 8K/16K, 32K/16K, 8K/1K, 32K/4K), R2 3 (2K/4K, 8K/16K, 32K/32K) = 31. Five replicates: **155 cells** (150 if the calibration fixes 2K/256 as not run, §7.2). No seed block: P10-S1's corrected seed block already shows the data draw dominating in 24 of 28 comparisons.
- The oracle codes have width 16 at every size; their crowding grows with the fact set (§2 item 11) and is printed beside every saturation figure.

## 6. Data, seeds, replicates

- Generator, task, panels A and B, held-out panels H1 and H2, unseen-fact control: ADR-0021 §4 and §6.2. Each block M draw has a fact table of 32,768 facts whose first 8,192 and 2,048 are the smaller sets.
- **Five replicates, never reduced.** Replicate r is data draw r with one initialisation seed. Pairing as ADR-0021 §6.2.
- **Seeds are those of `docs/reviews/p10-i-direction-2026-11-17/SEED_REGISTRY.md` §4.2** (checker result PASS):

| Role | Values |
|---|---|
| Registered draw sets, block M | 240001, 240101, 240201, 240301, 240401 (P10-S1's in-set layout; index seed at base + 60) |
| Initialisation, block M | replicate r → 330100 + r (330101–330105) |
| Calibration draws and initialisation | 249001 with 330191; 249101 with 330193 |
| Rehearsal draw and initialisation | 249201 with 330192 |
| Test mode; unit tests | 330198, 330199; 933001–933999 |

- **Block X** (registry revision 2, confirmed): draw sets 240501, 240601, 240701, 240801, 240901 (fact tables of 131,072 facts, P10-S1 in-set layout) and initialisation 330121–330125 (draw r → 330120 + r). Block X's calibration and rehearsal draws are requested from the registry in block X's revision (§12). Lane L's values stay PENDING there (247001–247999, 330111–330115) until lane L is specified.
- **Gate G9** runs a new copy of `seed_registry_check_r3.py` (SHA-256 `e462360420321aa284b0e4d47b106806419ab616794a5c632fee70f122c67594`) extended with this study's named values, with R2 and R3 expanded (registry §4.3 item 5, §4.5 item 5). The copy excludes from the inventory the files of every P10-I study's own package, config and tests (as ADR-0029 §19 ruling 6); each study's own values are checked separately against its own allocation rows. The copy's hash and its exclusions are recorded in the gate result. G9 requires RESULT: PASS and an empty MISSING list before each freeze. (On 2026-11-18 the unmodified r3 checker returned FAIL with 34 problems, all of them P10-I-R's own literals against P10-I-R's own allocation.) No seed is derived arithmetically from a data seed except in-set offsets below 100 (registry §4.3 item 1). Block M uses none of block X's or lane L's values.

## 7. Rates, U_P and run lengths

### 7.1 Equal rate search, and its order

**Rule: every trained arm gets the same search.** Grid {0.001, 0.003, 0.01, 0.03, 0.1}, both calibration draws, the selection rule of ADR-0021 §10.1 item 3 and §22 M7 (highest minimum Panel A a_use over the two draws at the readout; ties within 0.02 by the walk down the doubling grid; then the smaller rate).

| Arm | Unit → selection cell → cells that use the rate |
|---|---|
| F-OQ, T-OQ, H8 | 1,024 slots → 2K/1K → 2K/1K. 4,096 → 8K/4K → 2K/4K, 8K/4K. 16,384 → 32K/16K → 8K/16K, 32K/16K |
| D-OQ | 4,096 → 8K/4K → 2K/4K, 8K/4K. 16,384 → 32K/16K → 8K/16K, 32K/16K. D-OQ has no cell at 1,024 slots that is not loaded, so no such unit |
| R2 | One unit per reference cell: 2K/4K, 8K/16K, 32K/32K |
| every arm trained there | Each loaded cell (8K/1K, 32K/4K) and 2K/256 is its own unit, read at 65,536 updates |

**Order, fixed now, so that rates and U_P do not each wait for the other:**

1. Rates of the units that are not loaded are selected at a **provisional readout** per row: 8,192, 8,192 and 16,384 updates for the rows of 2,048, 8,192 and 32,768 facts (P10-S1's U_P values; ADR-0021 §25.15).
2. U_P of each row is computed at those rates by the rule of §7.2.
3. If a row's U_P differs from its provisional readout, the rates of **the units whose selection cell lies in that row** (R2's unit for that row included) are selected **once more** at U_P. U_P is not recomputed and **is not re-checked at the re-selected rates**. There is no further iteration. If a registered replicate then fails REF, it is NOT_EVALUATED as §9.1 row 1 states.
4. Both selections are printed. Loaded-cell units are selected last, at 65,536 updates.

- **Edge rule (design ceiling, extended by rule).** If the best rate of a unit is at an end of the grid by more than 0.02, the grid is extended one step in that direction (0.3; 0.0003), **at most twice per unit in total, across both selections**. If the best is still at the edge after two extensions, the unit prints RATE AT EDGE and the work returns to the human lead before the freeze. A best rate that is within 0.02 of an edge rate and was chosen by the tie walk is taken, recorded as EDGE BY TIE-WALK, and not extended (ADR-0021 §10.1 item 3).
- **A diverged rate (calibration only).** A calibration run is DIVERGED if it ends with a non-finite value (§14), ends `failed`, or has a raw Panel A correct count inside the G2 chance interval at the readout on either draw (ADR-0021 §10.1 item 3, as P10-S1's calibration applied it). A diverged rate is recorded, kept and left out of the selection. If every rate of a unit diverges, the work returns to the human lead before the freeze. A run stopped by a cap is never diverged; it is PAUSED and resumes. "Diverged" is not a verdict of the registered run: there, a finite cell at chance is data that the rules of §9 read, and a non-finite cell is an engineering stop (§14).
- **Reason.** `docs/EXPERIMENT_PROTOCOL.md` §3 requires a comparable tuning budget across alternatives. In P10-S1 one side was tuned and the other was not.
- **Limit.** At a loaded cell the rate is chosen at 65,536 updates although the cell runs for hundreds of thousands; this favours fast rates. Stated in §20.

### 7.2 U_P and run lengths

- **U_P per row** (ADR-0021 §10.1 item 1): the smallest of {8,192, 16,384, 32,768, 65,536} at which, on both calibration draws and both panels, F-OQ reaches a_use ≥ 0.90 at the row's larger step cell and R2 reaches a_use ≥ 0.95. **Ceiling 65,536** (three doublings; P10-S1 found 8,192 and 16,384). If no value qualifies for a row, the work returns to the human lead before the freeze; no other value is substituted.
- **Cells that are not loaded** run 6 · U_P of their row; R2 runs U_P. Snapshots: U_P × {1/16, 1/8, 1/4, 1/2, 1, 1.25, 1.5, 2, 2.5, 3, 4, 6}.
- **Loaded cells: run until full, within a budget.** The fixed ceiling of ADR-0021 §10.1 item 0b is replaced.
  1. *Ladder.* 65,536 × {1, 1.5, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, …} (alternating ×1.5 and ×4/3).
  2. *Snapshots.* At every ladder point and at half of every ladder point (so 32,768, 49,152, 65,536, 98,304, …); on the doubling grid from 512 below 32,768; **and at U_P × {1, 1.25, 1.5, 2, 2.5, 3, 4, 6} of the cell's row**, which the matched-compute readings of §8.2 need (the loaded cell is the smaller and cheaper cell of its step and is the one read at a multiplied snapshot).
  3. *Full at U* (a cell, on its own snapshots): on both panels, i\*(U) − i\*(U/2) ≤ 0.10 bits and i\*(U/2) ≥ 0.473 bits (ADR-0021 §8.2, unchanged), at two consecutive ladder points, of which U is the second. i\*(U) is the maximum of i over the cell's snapshots up to U, on each panel. DEP is not consulted by this rule; DEP enters the verdicts of §9.
  4. *Calibration* first selects the rate of each loaded-cell unit at 65,536 updates (§7.1). It then continues the selected rate's runs of F-OQ and T-OQ at each loaded cell, and of F-OQ at 2K/256, from their 65,536 checkpoints (restoration as gate G4; no new run is started) on both calibration draws up the ladder until full at U on all four views; that U is the arm's starting length U₀. In the calibration, "full" also requires i\*(U) ≤ 4.0 on every view, as ADR-0021 §10.1 item 0b did. **D-OQ and H8** are not searched; each starts at the larger of F-OQ's and T-OQ's U₀ and is judged on its own snapshots (ADR-0021 §10.1 item 0b).
  5. *Calibration ceiling (design ceiling, written rule).* The calibration ladder stops at **four times P10-S1's registered run length of the cell**: 1,572,864 updates at 8K/1K and at 2K/256 (which shares its row and candidates in ADR-0021), 3,145,728 at 32K/4K. Both are ladder points. The figure 4 is the same two doublings as item 7. Registered outcomes on reaching it:

     | Not full on all four views at the ceiling | Outcome, fixed now |
     |---|---|
     | F-OQ at 2K/256 | The cell is not run; the pair 256 → 1,024 is fixed as NOT FULL and prints "256 NOT MEASURED — NOT FULL WITHIN CEILING" (as ADR-0021 §5.1). No return |
     | T-OQ at 8K/1K or 32K/4K, F-OQ full | T-OQ starts at F-OQ's U₀; the freeze record states T-OQ PREDICTED NOT FULL AT that cell; the run judges it on its own snapshots |
     | F-OQ at 8K/1K or 32K/4K (a view above 4.0 bits at its U₀ counts as this case) | The work returns to the human lead before the freeze, with the curves (as for RATE AT EDGE). His options are those of ADR-0021 §10.1 item 0b: stop, or run with that transition fixed in the freeze record as NOT TESTED. The lead changes no load, ceiling or arm |

     A calibration search stopped by its hour cap before its ceiling is PAUSED and resumes; that is a resource cap, not this ceiling.
  6. *Registered run.* Each registered cell (arm, replicate) trains to its U₀ and continues ladder point by ladder point until it is full or reaches its **granted length G**. G is one of U₀ × {1, 1.5, 2, 3, 4}, at most **4 · U₀**, fixed per loaded cell and arm in the frozen plan by the block-budget rule of §17.1 from rehearsal rates only. The frozen code applies the stop rule to the cell's own plateau statistic and to nothing else; the statistic is not displayed. Continuation uses checkpoint restoration (gate G4). The plan lists every loaded cell with U₀, G and every snapshot up to G; items beyond the point at which a cell stopped are recorded NOT REACHED, not missing. **U_run** of a loaded cell is the ladder point at which it was found full, or G.
  7. A registered cell not full at G is **NOT FULL WITHIN BUDGET**: a registered value, not a negative. The figure 4 is two further doublings, the horizon ADR-0021 §8.2 row 4 already uses. Where G is below 4 · U₀ the report prints the cell's G beside the label.
  8. **Loaded:** full, and i\* ≤ 4.0 bits (ADR-0021 §8.2, unchanged).

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

- **What the figures are.** (i) is a one-sided test of "the facts not usefully retained are answered at the backbone's rate". p⁺ is above the measured rate b/n (0.035–0.049 against about 0.028–0.031), so the test is deliberately conservative and its real false-failure rate is far below 10⁻⁴. (ii) is an effect-size floor: more than one fact in a hundred answered correctly without depending on the read and beyond the backbone's own rate. The two parts use different nulls on purpose: (i) guards against noise, (ii) against a real but negligible excess. c − u does not enter i; the floor is a judgement of what excess is worth invalidating a cell for (kept at 0.01 by Decision 1, §21 item 7). The quantile in (i) is the smallest k with P(X ≤ k) ≥ 1 − 10⁻⁴, computed exactly in log space with no package outside the lock; "exceeds" means strictly greater. The first review computed what it detects: an excess of 1.2% of n at n = 8,192 and a_use 0.5; 3.0% at n = 2,048 and a_use 0.25.
- **Disclosure.** On P10-S1's records this condition fails nothing (§2 item 10). The figure 0.01 was written before that audit; it is kept, and it is now known to sit just below the largest excess seen on any read (+0.0101, at a cell under the a_use floor).
- **Where DEP is read: at every snapshot up to the run length. Ruling 22 (g) of ADR-0021 is kept.** Each verdict of §9 fails on a DEP failure at any snapshot of either cell up to its run length; this includes the snapshots that attain i\*.
- **Reference qualification (binding).** In the rehearsal, R2 is run through DEP-a, b and c at every snapshot fraction of U_P, at each of its cells, on the rehearsal and both calibration draws. A condition that R2 fails at a fraction on any view is **not used at that fraction for any arm of that row**, and the report prints NOT QUALIFIED AT that fraction. In the registered run R2 is read again at the same snapshots; if it fails a qualified condition in a replicate, that condition is not applied at that snapshot in that replicate and REFERENCE FAILED DEP is printed. Fixed before any registered seed is observed; applies to every arm alike.

### 8.2 Cost readings

Two readings, never merged:

- **MC-A, analytic.** Multiply-adds of one whole training update (ADR-0021 §22 M6 and §22.1), checked against a FLOP count at small size. Deterministic. It is a matching rule and a counted quantity. **It is never reported as measured efficiency.**
- **MC-T, measured.** Single-thread process CPU-seconds per update from the isolated timing stage (§16): one stage after Decision 2 and before training, on the rehearsal draw, covering every arm and size, 256 slots and R2's cells included; it is all or nothing. The stage runs alone. If its quiet condition is not met it is PAUSED and rescheduled; MC-T is NOT MEASURED only by the recorded decision of §16, never by a timeout, and then no measured-cost comparison is made (§10).

For each reading, the matched snapshot of the cheaper cell is the smallest of {1, 1.25, 1.5, 2, 2.5, 3, 4, 6} · U_P whose cumulative cost is at least the costlier cell's at U_P; beyond the run length the pair is MC-SHORT in that reading. F-OQ-IVF's costs per update in both measures, and its cost in STORE HOLDS MORE, are F-OQ's training costs; the index build is not counted, and its matched snapshots are F-OQ's.

**The larger multiplier is binding, as in ADR-0021 §5.4.** ADR-0021 read the cheaper cell at the larger of the two measures' multipliers and, where the measures disagreed on which cell of a pair costs more (MC-AMBIGUOUS), read the pair in the direction that favours the comparator. Both are kept, as a third reading **MC-C** that exists only where MC-T is measured: the cell whose advantage would be claimed (the larger cell in §9.1; the memory arm in §9.2) is read at U_P, and the other at the smallest grid snapshot whose multiplier is at least the largest of r and 1/r over both measures, r being the ratio of the two cells' costs per update in a measure. Where the measures agree on the direction, MC-C is the one of MC-A and MC-T with the larger multiplier. Where they disagree, MC-AMBIGUOUS is printed and MC-C is a snapshot of its own. MC-C counts as a matched-compute reading wherever a rule names matched compute: a store-favouring condition must also hold in it, and a dense lead in it counts. Beyond the run length it is MC-SHORT. **Disclosure:** draft 3 read the capacity step's matched compute in analytic cost alone and dropped both ADR-0021 rules; that could only make a CAPACITY verdict easier, and the third review found it (F1). MC-A, MC-T and MC-C are all printed; they are never merged into one figure.

### 8.3 Rulings fixed now (from the third review)

The third review listed twenty points an implementer would have had to guess, and a disclosure. The adopted ruling for each is in §23 and binds the implementation; where §23 and another section differ, the stricter reading for the store applies and the difference is reported to the lead before the freeze. The disclosure (the review's item 21) is placed beside the rule it concerns, in §9.3.

## 9. Rules of block M

Panels are read separately. A favouring condition needs both panels in a replicate; a blocking condition needs either (ADR-0021 §22 (h)). The denominator is always 5.

### 9.1 Capacity step, one replicate (ADR-0021 §8.2, restated; first match wins)

Δ_MU = i(4N; U_P) − i(N; U_P). Δ_MC = i(4N; U_P) − i(N; U_MC), computed separately in MC-A and, where measured, in MC-T. In a reading in which the larger cell costs no more per update than the smaller, U_MC = U_P in that reading. Where MC-T is measured, Δ_MC is also computed in MC-C (§8.2). Δ_SAT = i(4N; U_P) − i\*(N; U_run). Δ_FULL = i\*(4N; U_run) − i\*(N; U_run).

| Order | Verdict | Rule |
|---|---|---|
| 1 | NOT_EVALUATED | REF fails for the row (R2 a_use < 0.95 at U_P on a panel), or LEAKAGE |
| 2 | DEPENDENCE_FAILED | either cell fails a qualified DEP condition at any snapshot up to its run length |
| 3 | CEILING | i(N; U_P) ≥ 4.5 |
| 4 | CAPACITY | Δ_MU ≥ 0.5; Δ_MC ≥ 0.5 in MC-A and, where MC-T is measured, in MC-T (a pair MC-SHORT in either reading fails this condition); where MC-T is measured, Δ_MC ≥ 0.5 in MC-C as well; Δ_SAT ≥ 0.5; the smaller cell is loaded; Δ_SAT − 2 · [i\*(N; U_run) − i\*(N; U_run/2)] ≥ 0.5; a_use(4N; U_P) ≥ 0.5 |
| 5 | GAIN WITHIN BUDGET ONLY | Δ_MU ≥ 0.5, not row 4 |
| 6 | REVERSED | Δ_MU ≤ −0.5 and Δ_FULL ≤ −0.5 |
| 7 | BEHIND WITHIN BUDGET | Δ_MU ≤ −0.5, not row 6 |
| 8 | NULL | \|Δ_MU\| < 0.25 and \|Δ_FULL\| < 0.25; both cells full; the smaller cell loaded |
| 9 | FLAT, NOT LOADED | as row 8, the smaller cell not loaded |
| 10 | UNRESOLVED | otherwise |

Different verdicts on the two panels give PANEL-DISAGREE. Where MC-T is NOT MEASURED, Δ_MC is read in MC-A alone and every CAPACITY verdict carries MATCHED COMPUTE IN MC-A ONLY. Disclosure: ADR-0021 §5.4 read the smaller cell at the larger of the two measures' multipliers (1.689 at F-OQ's C1 and 1.697 at C2 in P10-S1, `analysis.json`); requiring Δ_MC ≥ 0.5 in each measure is at least as strict wherever MC-T is measured. The MC-C condition is the lead's addition to the review's text: it keeps ADR-0021's reading exactly, including its comparator rule where the two measures disagree on the direction, a case the per-measure condition alone would read more leniently than ADR-0021 did. Every threshold is ADR-0021's, fixed there before any S1 record.

**Step class** (first match): NOT_EVALUATED (≥ 2 replicates); DEPENDENCE_FAILED (≥ 2); NOT REPLICATED (≥ 2 PANEL-DISAGREE); CAPACITY STEP (CAPACITY in all 5); GAIN WITHIN BUDGET (rows 4–5 in all 5); NOT LOADED (CEILING or FLAT, NOT LOADED in ≥ 4); REVERSED (≥ 4); NO GAIN (NULL or REVERSED in ≥ 4); NOT FULL WITHIN BUDGET (the smaller cell not full in ≥ 2); MIXED.

**Arm class** (F-OQ, F-OQ-IVF, T-OQ, H8; first match; H8's is printed with its annotations of §4 and enters no outcome): NOT_EVALUATED (every step of a transition); DEPENDENCE_FAILED (any step); CAPACITY_SUPPORTED (a CAPACITY STEP in each of the two transitions, no step REVERSED, a_use ≥ 0.80 at 32K/16K at U_P in all 5); CAPACITY_ONE_TRANSITION (at least one CAPACITY STEP); NOT_TESTED_BY_LOAD (in some transition every step is NOT LOADED or NOT FULL WITHIN BUDGET); CAPACITY_NOT_SUPPORTED (a NO GAIN or REVERSED step in every transition and no CAPACITY STEP); INTERMEDIATE.

### 9.2 Dense comparison

**The readings.** Per arm, per larger cell of each CAPACITY STEP, d = i(arm) − i(D-OQ) in four readings: **MC-A** and **MC-T** (the cheaper of the two at its matched snapshot), **MU** (both at U_P), and **D-BEST** (the arm at U_P against the best of D-OQ's snapshots up to its run length, as ADR-0021 §8.5). Where MC-T is measured, the comparator reading **MC-C** of §8.2 (the arm at U_P, D-OQ at the later snapshot) is computed as well and belongs to the matched-compute readings on both sides of the rule; "all four readings" below includes it.

| Cell label | Rule |
|---|---|
| DENSE AHEAD (cell) | d ≤ −0.25 on either panel in ≥ 4 replicates in at least one reading: MU, MC-A, MC-T (where measured) or D-BEST (ADR-0021 §8.5). The count in each reading is printed. Where the lead holds only in MU or D-BEST, the label is printed DENSE AHEAD (NOT AT MATCHED COMPUTE). A replicate whose pair is MC-SHORT in a reading does not count towards this label in that reading |
| STORE NOT BEHIND (cell) | d > −0.25 on both panels in all 5 replicates in **all four readings: MC-A, MC-T, MU and D-BEST** (and in MC-C); MC-T must be measured; no matched-compute pair MC-SHORT |
| DENSE COMPARISON SPLIT (cell) | otherwise; every reading and replicate count is printed |

A dense lead in MC-C counts for DENSE AHEAD as a matched-compute reading. The annotation NOT AT MATCHED COMPUTE says only where the lead was found; it changes no label and no outcome: DENSE AHEAD (NOT AT MATCHED COMPUTE) is DENSE AHEAD in every rule below.

**Disclosure, placed with the rule.** In P10-S1 the readings disagreed at 32K/16K: matched compute favoured F-OQ in 5 of 5 replicates (+0.24 to +0.33 bits), matched updates favoured D-OQ in 4 of 5, and D-OQ's best snapshot favoured D-OQ in 5 of 5; ADR-0021 §8.5 let any one reading give DENSE AHEAD. This rule is written knowing that. Against ADR-0021:

- **For a positive, nothing is relaxed.** A store-favouring label needs every reading ADR-0021 could block on (MU, matched compute, D-BEST), with matched compute now required under both cost measures separately and in ADR-0021's own comparator reading. Draft 2 left D-BEST out of this side; the confirmation review showed that was a relaxation in the store's favour, chosen after D-BEST favoured D-OQ. It is restored. Draft 3 still read the capacity step's matched compute in analytic cost alone; that is corrected in §8.2 and §9.1.
- **For a negative, nothing is narrowed relative to ADR-0021 §8.5:** any one reading at any such cell, or DENSE HOLDS MORE at any loaded cell, gives DENSE AHEAD. Draft 3 proposed a narrower negative (a dense lead at matched compute required, every cell, every loaded cell). It was written after P10-S1's readings were seen and would move P10-S1's pattern at 32K/16K from DENSE AHEAD to SPLIT. It is reserved to the human lead (§21 item 4) and is not adopted under the delegation.
- **What was removed, and why.** Three narrowings of the negative stood in the earlier drafts and are gone: (1) a dense lead at matched updates alone or at D-OQ's best snapshot alone gave SPLIT, and so CAPACITY-INCONCLUSIVE, where ADR-0021 gave CAPACITY-NEGATIVE (b); (2) an arm was DENSE AHEAD only if it was so at **every** cell, where ADR-0021 said **any** cell; (3) DENSE HOLDS MORE counted only at **every** loaded cell, where ADR-0021 said **any**. Draft 3 disclosed the first and not the other two (third review, B-M4). All three were written after P10-S1's readings were seen, and all three favoured the store. **The lead records that he asked for one of these narrowings himself in an earlier draft, and that two independent reviews removed them.** The reason draft 3 gave ("an update is not a resource; D-OQ costs more per update") holds for F-OQ and not for T-OQ at 4,096 slots, where D-OQ was the cheaper per update in P10-S1 (T-OQ 0.0129 against D-OQ 0.0104 seconds at 8K/4K; third review, section B). What that reason wanted to convey is kept as the printed annotation NOT AT MATCHED COMPUTE.
- **Effect on P10-S1's records.** The rule as adopted moves no P10-S1 label. F-OQ at 32K/16K is DENSE AHEAD (NOT AT MATCHED COMPUTE), as ADR-0021 read it, and DENSE HOLDS MORE AT SATURATION stands at both loaded cells. P10-S1's capacity line stays CAPACITY-INCONCLUSIVE as registered, because its arm classes (DEPENDENCE_FAILED and INTERMEDIATE) decide it before any dense label is read; its efficiency line stays EFFICIENCY-NEGATIVE as registered (§9.5). What the new dependence test of §8.1 would change on those records is stated beside §9.3.

**Dense at saturation,** per loaded cell, each arm at its own full length: DENSE HOLDS MORE (d_sat ≤ −0.25 in ≥ 4; a replicate counts if either panel satisfies it); STORE HOLDS MORE (I_use ratio ≥ 1.10 on both panels in all 5, D-OQ full, and D-OQ's cost per update at least the arm's in both cost measures, as ADR-0021 §8.5); SAME AT SATURATION otherwise, with DENSE STILL RISING if D-OQ is not full. Every dense label is printed for every cell with all four readings and D-OQ's a_use. Each arm's length is printed beside d_sat, and d_sat at the shorter of the two lengths is printed descriptively.

**Arm-level combination across cells, explicit.** For an arm with no CAPACITY STEP the arm-level dense label is **NOT APPLICABLE**. Otherwise: DENSE AHEAD (arm) if DENSE AHEAD at any such cell, or DENSE HOLDS MORE at any loaded cell (ADR-0021 §8.5). NOT BEHIND DENSE (arm) if STORE NOT BEHIND at every such cell and DENSE HOLDS MORE at no loaded cell. DENSE SPLIT (arm) otherwise. SPLIT is now only the middle case, in which no reading shows a dense lead in 4 replicates and the store is not clear of −0.25 in all 5 in every reading; ADR-0021 would have allowed CAPACITY-POSITIVE there, and this text gives INCONCLUSIVE.

### 9.3 C-CAPACITY outcome (first match wins)

| Order | Outcome | Rule |
|---|---|---|
| 1 | ENGINEERING-FAILURE | an engineering gate fails, or frozen and running identities differ and cannot be restored (§18). ENGINEERING STOP — ITEM ERRORS if a registered stage holds an item error (§14, §18): the analysis refuses and no label is printed on any line |
| 2 | PAUSED / INCOMPLETE (status) | a registered cell has no record. PAUSED if the cause is a resource cap, an environment stop, an unmet quiet condition or a restorable identity stop; no outcome is printed and the run is resumable. INCOMPLETE: no outcome is printed on any line (ADR-0021 §8.7 row 2). |
| 3 | CAPACITY-POSITIVE | F-OQ, T-OQ or F-OQ-IVF is CAPACITY_SUPPORTED and NOT BEHIND DENSE |
| 4 | CAPACITY-NEGATIVE | (a) F-OQ and T-OQ are both CAPACITY_NOT_SUPPORTED; or (b) at least one of the three is CAPACITY_SUPPORTED and every such arm is DENSE AHEAD |
| 5 | CAPACITY NOT TESTED | for F-OQ and T-OQ, every step is NOT LOADED or NOT FULL WITHIN BUDGET |
| 6 | CAPACITY-INCONCLUSIVE | otherwise, with the reason |

- Printed with "1,024 TO 16,384 SLOTS", "16,384→65,536 NOT TESTED — BLOCK X NOT APPROVED", the arms that carry the label, each cell's dense labels in each reading, the saturation outcome, H8's classes and KEY-LEARNING-LIMITED or its absence, the sparse-arm label and the tags of §1. H8 is not one of the arms of rows 3–5.
- **Disclosure, placed with the rule (third review, F13).** On P10-S1's records DEP-c fails none of the 32 reads that failed the 0.95 condition (third review), and the audit's run without those failures gives F-OQ CAPACITY_SUPPORTED (`audit/a4_dep_sensitivity.out`). C-CAPACITY would then turn on the dense labels; with DENSE HOLDS MORE at both loaded cells in 5 of 5 replicates it would be CAPACITY-NEGATIVE (b). So the new dependence test, taken with the dense rule of §9.2, would have read P10-S1's records as a negative where the registered label is INCONCLUSIVE. P10-S1's label is not revised.
- **Which arms may carry a label another study uses for entry.** Only a trained arm, F-OQ or T-OQ. F-OQ-IVF has no training, no rate search and no training cost of its own: its CAPACITY_SUPPORTED is printed and enters C-CAPACITY as in ADR-0021, but it names F-OQ's trained memory read post hoc and **qualifies no arm for entry elsewhere** (for example ADR-0027). A C-CAPACITY positive carried by F-OQ-IVF alone prints "POST-HOC READ ONLY; NO TRAINED ARM QUALIFIES". Whether F-OQ-IVF should enter C-CAPACITY at all is §21 item 10.
- **The lead's expectation, written before any observation under this ADR:** F-OQ shows capacity steps; DENSE HOLDS MORE at saturation is likely again; CAPACITY-NEGATIVE by clause (b) is the single most likely outcome unless the rate search changes the picture.

### 9.4 C-SATURATION

S(N) = F · i\*(cell at its full length), ρ = S(4N)/S(N), b(N) = S(N)/N. Pair verdict, class, arm class and outcome are ADR-0021 §8.10's with the threshold 3.0 unchanged and two changes: NOT FULL means NOT FULL WITHIN BUDGET under §7.2; and every replicate is printed on both panels with ρ, the last ladder gain and its full status, including replicates that are not full (audit D2, D9). Registered pairs: 256→1,024 (F-OQ) and 1,024→4,096 (F-OQ, F-OQ-IVF, T-OQ, H8). H8's pair is printed and, as in ADR-0021 §8.10, H8 alone cannot give SATURATION-PROPORTIONAL. Outcomes: SATURATION-PROPORTIONAL, -SUBPROPORTIONAL, NOT MEASURED, -INCONCLUSIVE. The crowding figures are printed beside every ρ; a SUBPROPORTIONAL verdict is never read as a property of the store alone.

### 9.5 C-EFFICIENCY and the dense-speed rule

The line reads the control steps N1 and N2. Level i_T = 3.0 bits; u_T, censoring, c_T and the step verdicts are ADR-0021 §8.8's, with one change: **every verdict that uses cost is computed once per cost reading**, giving readings E-A and E-T, each with its own step and arm classes.

**Dense speed, per FASTER-STEP larger cell, per reading:** DENSE FASTER if D-OQ's c_T is at most 0.8 of the arm's in ≥ 4 replicates; DENSE NOT FASTER if it is above 0.8 in all 5; DENSE SPEED UNDECIDED otherwise. **Every cell and reading is printed.**

| Order | Outcome | Rule |
|---|---|---|
| 1 | ENGINEERING-FAILURE | as §9.3 row 1 |
| 2 | PAUSED / INCOMPLETE | as §9.3 row 2 |
| 3 | EFFICIENCY-POSITIVE | F-OQ or T-OQ is EFFICIENCY_SUPPORTED in **both** E-A and E-T, and is DENSE NOT FASTER at **every** FASTER-STEP cell in **both** readings |
| 4 | EFFICIENCY-NEGATIVE | F-OQ and T-OQ are both EFFICIENCY_NOT_SUPPORTED in E-A, or both in E-T; or at least one is EFFICIENCY_SUPPORTED in both readings and every such arm is DENSE FASTER at one or more FASTER-STEP cells in one or more readings |
| 5 | EFFICIENCY-INCONCLUSIVE | otherwise, with the reason: DENSE SPEED UNDECIDED (cells and readings named), READINGS DISAGREE, MEASURED COST NOT AVAILABLE |

**Disclosure, placed with the rule.** The positive is P10-S1's any-cell block, applied in each reading. The negative keeps the any-cell combination that P10-S1's frozen code applied (`studies/p10s1/analysis.py` line 631) and that the human lead accepted in the registered label (`ACCEPTANCE.md` ruling 2); it is now written down and applied per reading, with each cell and reading printed. On P10-S1's records it gives EFFICIENCY-NEGATIVE again (D-OQ faster at 2K/4K in both readings). Draft 3's negative, which needed every cell in both readings, would have turned P10-S1's registered negative into INCONCLUSIVE and was written knowing that; it is reserved to the human lead (§21 item 6).

The figures on P10-S1's records, for the reader: D-OQ was faster at 2K/4K in both readings (CPU ratio 0.083–0.118, multiply-adds 0.32–0.46) and at 8K/16K in CPU only (0.27–0.38 against 1.32–1.87). P10-S1's label is not revised. Where a dense-speed lead holds at some cells or in one reading only, the outcome is negative and the report names each cell and reading in which it held and each in which it did not, so that the label is not read as evidence about a cell or a reading it did not hold in.

### 9.6 Descriptive labels (enter no outcome)

- **Sparse arms.** T-OQ against F-OQ-IVF at equal candidate count, on I_use at 8K/4K and 32K/16K: ratio ≥ 1.03 AHEAD, ≥ 0.97 COMPETITIVE, otherwise BEHIND, in ≥ 4 replicates at both cells. Read at U_P and at the run length; both labels are printed and neither is called "the" label. It may not be cited to select a routing design; that is ADR-0029's subject.
- Counted work per query, ADR-0021 §7.4. Logical counts; not measured efficiency.
- Read-path throughput (RAM, one process, quiet condition met), ADR-0021 §7.5; THROUGHPUT NOT MEASURED otherwise.

## 10. What a decision to record MC-T as NOT MEASURED makes unreachable

An unmet quiet condition never ends the timing stage: the stage is PAUSED and rescheduled, and training does not start while it is paused (§16). MC-T is NOT MEASURED only by the explicit recorded decision of §16, after the stated number of rescheduled attempts. That decision is recorded before training starts, with this table, so that whoever takes it sees which labels it gives up:

| Line | Unreachable | Still reachable | Printed |
|---|---|---|---|
| C-CAPACITY | CAPACITY-POSITIVE (STORE NOT BEHIND needs MC-T) | NEGATIVE (a); NEGATIVE (b) through MU, MC-A, D-BEST or saturation; NOT TESTED; INCONCLUSIVE | "MEASURED COST NOT AVAILABLE: a positive was not reachable" |
| C-EFFICIENCY | POSITIVE (needs E-T) | NEGATIVE through E-A; INCONCLUSIVE | the outcome with '(E-A ONLY; MEASURED COST NOT AVAILABLE)' |
| Dense at saturation (a label of §9.2, not a C-SATURATION outcome) | STORE HOLDS MORE AT SATURATION (cost condition) | DENSE HOLDS MORE; SAME AT SATURATION; every C-SATURATION outcome | the same sentence beside the dense-at-saturation label |

The study is still complete in that case. No store-favouring label becomes reachable through it, and no negative becomes unreachable.

## 11. Order of work

Independent review of this draft (done, three rounds, §22) → **Decision 1 for block M** (taken, §24) → implementation with tests and an independent implementation audit → timing preview and calibration (§7.1 order) → the candidate plan, with the granted lengths of §17.1 → the measuring rehearsal on provisional caps → caps by §15's rule, written into the candidate plan → the counting rehearsal of every registered stage end to end against that exact file (§18) → freeze of block M, which refuses any other plan file → **Decision 2** (not approved by this text; taken on the rehearsal records and the implementation audit) → the isolated timing stage, alone (§16) → one registered run → the throughput stage, alone → independent recomputation from raw records (the auditor receives the specification, code and records, not the lead's conclusions) → outcome record → acceptance.

Block X and lane L are not in this order. Each needs a revision of this ADR, its own review and its own decision (§12, §13), and block M waits for neither.

## 12. Block X — 16,384 → 65,536, to be specified in a revision and decided on its own after block M's outcome; the funding figure H_X is set by the human lead himself

The human lead named this transition for P10-I (`ACCEPTANCE.md`). Draft 3 specified a conditional block for it. The third review found that it cannot be implemented as written (F8) and that its cost is not the delegation's to set. **Block X is not approved with this text.** Approval of block M approves no block X cell, rule, entry condition, budget or run. Block M depends on nothing here.

**Settled now** (constraints the revision must keep; they approve nothing):

- **Its own line.** The transition has its own outcome line, **X-CAPACITY**, never merged with C-CAPACITY. Adding it cannot move block M's outcome in either direction, and no block X result changes a block M label.
- **Fresh draws.** Block X runs on five draws of its own (fact tables of 131,072 facts), not on block M's. Reason: block M's draws are the ones on which any entry condition would be observed; a step read on draws selected for a favourable C2 would be conditioned on them.
- **Seeds, from the registry** (revision 2, confirmed; §6): draw sets 240501, 240601, 240701, 240801, 240901 and initialisation 330121–330125. Block M uses none of them.
- **Its own decision, after block M's outcome.** Block X is specified in a revision of this ADR, reviewed independently, and decided on its own after block M has a recorded and accepted outcome. Its funding is fixed by rule from rehearsal rates before any block X seed is observed, never on a partial block X result.
- **H_X is set by the human lead himself.** It is not set under the delegation. With an evaluation term, the third review puts the central projection for draft 3's design at about 102–112 charged hours, against about 26 for block M as the human lead was told (review F9).
- **Printed by block M's report:** "16,384→65,536 NOT TESTED — BLOCK X NOT APPROVED".

**What the revision must add before block X can be approved** (third review, F8, F9, F14):

1. Calibration and rehearsal draws of 131,072 facts and their seeds, assigned by the registry.
2. The G2 chance interval at n = 131,072, which DEP-a, DEP-b, DEP-c and p⁺ all use.
3. U_P of the 32,768-fact row on block X's draws, and its selection cell.
4. The isolated MC-T timing at 65,536 slots, under §16's rule (§16 covers 256 to 16,384 slots only).
5. F-OQ-IVF at 65,536 slots (256 lists).
6. The evaluation term and the peak memory at 131,072 facts in the cost projection, against the 3 GiB guard.
7. The cells, the entry condition, the arm classes and the X-CAPACITY rule, restated in full under §8–§9 as adopted here (the stricter dense rule, the larger-multiplier rule, H8 or the reason it is absent), with the funding rule and a block budget of its own.
8. Whether the control step N3 (32K/16K → 32K/64K) is worth its cost: in draft 3 it was about a third of the 65,536-slot work and entered only a dependence row.
9. Its limits table, stop rules, frozen-input set and cost table, low, central and upper, with the bound its ceilings allow.

Draft 3's text for the block (cells C3 and N3, the entry condition "F-OQ's step C2 is a CAPACITY STEP", the funding rule P_X ≤ H_X, the X arm classes and the cost table of 26 / 48 / over 120 charged hours) is kept in the repository history at commit `ef5596b` and in the third review. It is a starting point for the revision and binds nothing.

## 13. Lane L — to be specified in a revision of this ADR before its own freeze; not approved with this text

Without a learned-address lane nothing in the programme registers capacity under learned addressing. Draft 2 specified one; the confirmation review found it not specified enough to approve (B-M5), and the lead agrees. Approval of block M approves no lane L cell, rule or budget.

**Constraints the revision must keep** (recorded with this draft; they approve no lane L cell, rule or budget):

- **Entry:** ADR-0023's licence only (its Line Q and qualified load L_Q, ADR-0023 §15), with ADR-0023's outcome recomputed and accepted before lane L's freeze.
- **Cells:** licensed cell types only, at loads up to L_Q. An unlicensed cell prints OMITTED — ADDRESSING NOT QUALIFIED AT THIS CELL (ADR-0023).
- **Line:** its own, **L-CAPACITY**, tagged `LEARNED-ADDRESS`, never merged with and never changing an oracle line.
- **Registered values now:** **OMITTED — NOT LICENSED**, and **OMITTED — NOT LICENSED AT THE FREEZE** if P10-I-S0 has no accepted outcome when block M freezes. Block M's report prints the applicable one. Lane L is a separate, later frozen stage; block M does not wait for it (§21 item 3). If ADR-0023 has an accepted outcome that licenses a cell when block M freezes, block M's report prints LANE L LICENSED — NOT YET SPECIFIED; NOT RUN UNDER THIS APPROVAL.

**What the revision must settle before lane L can be approved** (from the confirmation review):

1. **The dependence measure is the existing read-swap a_use** for learned queries (ADR-0020 §8.1; ADR-0023's composite, condition 6). Draft 2's new measure (correct with memory, wrong with memory disabled) is withdrawn: it is not fact-specific and a shared or collapsed read would pass it. Draft 2's statement that the swap is not defined for a learned query was wrong.
2. **The denominator.** ADR-0023 requires its reference A6 (oracle codes, learning rate 0.003) for its composite; F-OQ here goes through a rate search and is not A6. The lane must run A6 as ADR-0023 freezes it, or state exactly where F-OQ may stand in.
3. **Equal training lengths within a step.** ADR-0023 fixes a duration T per cell type; the two cells of a step may have different T. A step must compare equal lengths, by a rule.
4. **The comparator snapshot.** ADR-0023's T may exceed block M's run lengths at those cells (49,152 updates at the rows of 2,048 and 8,192 facts), and block M is frozen first. The comparator cells must be defined, and trained anew if needed, inside lane L.
5. **Its own data.** ADR-0023's composite needs its generator's panels and probe sets. Whether lane L uses data sets of its own in ADR-0023's layout (the registry holds 247001– and 330111–330115 as PENDING) or this study's draws must be fixed, and never both layouts in one set.
6. **Ceiling and not-loaded rows.** At the 2,048-fact steps both cells are near the ceiling under the oracle (F-OQ a_use 0.999 at 2K/1K at the run length), so a "no gain" there must not read as a negative.
7. Its cost projection, limits table, stop rules and seeds.

## 14. Stop rules and NOT EVALUABLE outcomes

- A failed engineering gate stops a stage before training.
- A registered cell that fails for a reason other than a cap or a restorable identity stop is kept and not re-run; the stage is INCOMPLETE and a second attempt is the human lead's decision.
- A stop on a resource cap is PAUSED. Completed cells are not recomputed.
- **A code error, an environment error or a non-finite value is an engineering stop, never a scientific label** (ADR-0029 §20 ruling 11).
  - *Code error.* An exception inside an item that is not a gate failure, a resource cap or an identity stop is recorded as an `item_error`. It is never NOT_EVALUATED, DEPENDENCE_FAILED or a failed cell. If any registered stage has one, the analysis refuses and every line prints ENGINEERING STOP — ITEM ERRORS.
  - *Environment error.* Out of memory, a file-system error or a killed worker stops the task as PAUSED — ENVIRONMENT. It is never recorded as a failed gate or a failed cell, and the task resumes once the environment is fixed without a code change.
  - *Non-finite value.* A value is non-finite if it is NaN, +∞ or −∞. The check covers the training loss at every update, every trainable parameter at every snapshot, and every logit and count input at every evaluation. A registered training cell in which one appears stops at that update and is recorded FAILED — NON-FINITE with the update index. It is kept and not re-run; the stage is INCOMPLETE, no outcome is printed on any line, and a second attempt is the human lead's decision. It never becomes a verdict of §9.
  - *A diverging run* exists in the calibration only, where it is defined in §7.1 and removes a rate from a selection. The registered run has no such verdict.
- No registered seed is observed before Decision 2, apart from G1. The frozen code's own use of a cell's plateau statistic (§7.2) is not an observation by the lead.
- REF failure: the replicate is NOT_EVALUATED for the row. LEAKAGE: NOT_EVALUATED for the cells concerned. A step class is NOT_EVALUATED at 2 or more such replicates (§9.1).
- No stage is re-run with changed settings. No threshold, seed, replicate count or rule changes after the freeze.

## 15. Limits, classified (DIRECTION.md §5)

| Limit | Kind | Rule |
|---|---|---|
| Hour cap of block M; per-stage caps; 3 GiB per worker, 18 GiB aggregate | Resource cap | Set after the rehearsal as charged + 2 × projected remaining, rounded up to the hour. Extended by the human lead on cost projections only, never on outcome values. A stage that reaches its cap is **PAUSED**, keeps its completed cells and resumes; the projection's assumption for loaded cells is stated (§17). The caps of block M set under the delegation sum to at most 60 charged hours; a cap or an extension beyond that is the human lead's own decision (§17.1) |
| Calibration hour budget | Resource cap | As the first row; a search stopped by it is PAUSED |
| **Block budget of block M: 60 projected charged hours at 1×** | Design ceiling, with a written rule | §17.1. Ladder extensions at loaded cells are granted in a fixed order while the projection stays within 60; a cell whose next step would exceed it stops there and, if not full, is NOT FULL WITHIN BUDGET. The projection uses rehearsal rates only; no partial result enters |
| Calibration ladder ceiling (4 × P10-S1's run length); U_P ceiling 65,536; rate grid (two extensions in total); one re-selection of rates | Design ceiling | Fixed, with the registered outcome on reaching each (§7.1, §7.2) |
| Registered loaded-cell run length (the granted length G, at most 4 · U₀) | Design ceiling | Reaching it gives NOT FULL WITHIN BUDGET. No ceiling is raised because a partial result looks close |
| Quiet-condition attempts (each a session of at most 6 hours; the first and five rescheduled) | Design ceiling | Fixed. Reaching it does not end the stage: it stays PAUSED. Only then may MC-T NOT MEASURED or THROUGHPUT NOT MEASURED be recorded, by an explicit decision (§16, §10) |
| Five replicates | Design ceiling | Never reduced |
| 0.5, 0.25, 0.10, 0.473, 4.0, 4.5, 3.0, 0.8, 1.10, 0.90, 0.95 (REF), 0.80, 4-of-5 and 5-of-5, the DEP-c figures | Scientific threshold | Never changed after the freeze |

## 16. Stages and machine load

The machine is also the human lead's working computer. Platform of record: macOS arm64 (the M5 Max of ADR-0021 §10.3), CPU only. The settings P10-S1's cells recorded (`environment.threads` of every `train.json`: one torch thread and one interop thread per worker, deterministic algorithms as recorded) are fixed in the config and asserted by each worker. The OS build is recorded with every gate result. The locked torch is 2.8.0 (`uv.lock`), as in ADR-0029 §13. Bit-exact assertions are made on it only. Checks (`ruff`, `mypy`, `pytest`) run locally; a GitHub run is not required.

| Stage | Runs alone, with the quiet condition? | How it is met, and what follows if it is not |
|---|---|---|
| Isolated timing, the source of MC-T (202–376 s in P10-S1's ledger) | **Yes.** No figure for the machine's usual load is assumed. In P10-S1 the rehearsal timing passed at 0.73 on its second reading after 1.34 (ADR-0021 §25.16), the registered timing stage started at 0.98, and the supplement passed at 0.998 on its first reading | **Yes, for the isolated timing stage (MC-T).** At its start: one-minute load average ≤ 1.0, no process of another ArborLM study's stage alive (P10-S1's `concurrency_check`), mains power, not in Low Power Mode. At its end: no such process alive, and none started during it; otherwise its figures are discarded and the run is repeated. Retried every 10 minutes for up to 6 hours in a session. A session without a quiet run is **PAUSED** and rescheduled; the rule for NOT MEASURED is below the table. The calibration's timing preview needs no quiet condition: it sets item caps only and enters no rule. |
| Read-path throughput (about 7 minutes), after all training and evaluation | **Yes**, the same conditions at its start and its end, the same sessions | PAUSED and rescheduled by the same rule; THROUGHPUT NOT MEASURED only by the same kind of recorded decision. Descriptive only |
| Timing preview, calibration, both rehearsals, generate, gates, train, evaluate, analyze, report | No | No rule uses their wall time. CPU-seconds per snapshot are recorded descriptively. They may share the machine (§16.1) |

**The timing stage and the throughput stage run alone, and neither ends NOT MEASURED by a timeout** (DIRECTION.md §5: a study does not end on a limit of convenience).

- **Alone** means: no process of this study's other stages and no process of any other ArborLM study's stage is alive at the start, during, or at the end. Both the load average and the process check are made at the start; the process check is repeated at the end.
- **An attempt** is one session: the conditions are checked at the start and, if they are not met, every 10 minutes for at most 6 hours. The wait is bounded; a session that ends without a quiet run is recorded PAUSED — QUIET CONDITION NOT MET, with each reading, and is rescheduled.
- **Training does not start while the timing stage is PAUSED.** The stage reads no registered seed, so a pause changes nothing but the calendar.
- **NOT MEASURED is a decision, not a timeout.** It may be recorded only after the first attempt and **five rescheduled attempts** have all ended PAUSED, and only by an explicit decision written into the run's records before training starts (the human lead's, or the lead's under a delegation then in force), together with the table of §10 naming the labels that become unreachable. Before that number of attempts it may not be recorded at all. The code never writes it by itself.
- The decision can only remove store-favouring labels (§10). It is taken before any registered training result exists.
- E6 of the third review gave three further sessions and then NOT MEASURED automatically. The lead's ruling is five rescheduled attempts and an explicit decision.

### 16.1 Sharing the machine with another study

Everything in block M except the isolated timing stage and the throughput stage may run while another study runs, under these conditions:

1. **Its own worktree.** Block M's work is never done in the worktree of another study, least of all one with a registered run in progress (P10-I-R's tasks refuse on a dirty tree, `studies/p10ir/plan.py`). Run directories are git-ignored. Nothing is written in block M's own frozen files during its registered run (§18).
2. **A machine-wide memory check.** The guards of §15 are per study (3 GiB per worker, 18 GiB aggregate). Two studies at their guards would hold 36 of the machine's 48 GiB. A stage therefore does not start, and a worker is not added, unless the free memory of the whole machine covers the stage's aggregate guard. If it does not, the stage waits with a deadline and is then PAUSED — ENVIRONMENT. P10-S1's measured peaks were 0.39 GiB per worker in training and 1.415 GiB in evaluation.
3. **Caps may pause a stage sooner.** Sharing raises charged hours, so a cap can be reached earlier. The stage is then PAUSED, keeps its completed cells and resumes. The measuring rehearsal measures the contention ratio under the conditions the run is expected to have, and the record says what else was running.
4. **A pause never changes a label.** No rule of §7–§9 reads wall time, load or the number of pauses, and gate G4's bit-exactness does not depend on load. A paused and resumed cell must equal an uninterrupted one bit for bit (G4), or the stage stops as an engineering failure.
5. The projection of §17.1 is made at the rehearsal's rates and is not redone because the machine was busier during the run; a busier machine reaches a cap, not a different plan.

## 17. Cost projection for block M (estimates, to be replaced by the rehearsal)

Measured basis: P10-S1 attempt 2 charged 49,251 s for 178 training cells and 1,899 s for evaluation with six workers; all attempts and calibration charged 25.39 h, of which revision 5's calibration was 18,683 s (`ledger_after_run.json`, `OUTCOME.md` §1). Median training seconds per update in that run (`manifests/train.manifest.json`): F-OQ 0.0060 at 2K/1K and 0.0050 at 8K/1K (1,024 slots), 0.0081–0.0092 at 4,096, 0.0124–0.0136 at 16,384; T-OQ 0.0116–0.0147; D-OQ 0.0051, 0.0088–0.0104, 0.0177–0.0216; peak 0.39 GiB per worker in training and 1.415 GiB in evaluation. The rehearsal's contention ratio was 1.946 (worst D-OQ at 1,024 slots), measured while the desktop was under unrelated load of about 5.4 (ADR-0021 §25.16).

Charged hours, six workers. "Upper" is what the design ceilings of §7 alone would allow, **before** the block budget of §17.1.

| Item | Low | Central | Upper within the design ceilings alone |
|---|---|---|---|
| Training, 120 cells, at P10-S1's lengths (the seed block out; the confirmation review computes 10.0). Of this, the loaded cells of F-OQ, T-OQ and D-OQ are about 7.7 | 9 | 10 | 12 |
| H8 at its seven cells, at P10-S1's lengths (35 cells; of this, the two loaded cells are about 1.1) | 1.5 | 1.5 | 2 |
| Loaded cells beyond P10-S1's lengths | 0 | 3 | about 116 for F-OQ, T-OQ and D-OQ (U₀ at the calibration ceiling and every cell to 4 · U₀: about 124 for those cells in total, third review), and about 17 more for H8 |
| Calibration: five rates × two draws for five arms, one re-selection, run-until-full load search, 2K/256, H8's four runs to U_P | 9 | 11 | about 21 (every load search to its ceiling: about 54 worker-hours, longest run about 11 hours, third review) |
| Evaluation, both rehearsals, gates, timing | 2 | 3 | 4 |
| **Block M, charged hours** | **about 21** | **about 29** | **about 170** |
| **With the block budget of §17.1** | about 21 | about 29 | **at most 60 projected, by rule** |

**Correction.** Draft 3 printed 19 / 26 / 60. Its upper case assumed U₀ equal to P10-S1's lengths and so was not the bound its own ceilings allow (third review, F7). The low and central cases rise by H8 and by its share of the calibration. The figure the human lead was told is "capacity about 26" (`DELEGATION_2026-11-18.md` §4), and 60 was the upper figure he was shown.

**Bound within the design ceilings.** If every loaded cell's U₀ is at its calibration ceiling and every loaded cell runs to 4·U₀, the loaded cells alone cost about 124 charged hours at P10-S1's six-worker seconds per update, with one T-OQ cell at 32K/4K taking about 43 hours of wall time. The calibration's load search to its ceilings costs about 54 worker-hours, with its longest run about 11 hours. The projection behind each cap states its assumption for loaded cells: U₀ for the projection, with the bound at 4·U₀ printed beside it. A cap or an extension whose bound exceeds 60 charged hours (this table's upper case) goes to the human lead; it is not set under the delegation.

Which figures are whose: 124, 43, 54 and 11 are the third review's (its section B). The split "7.7 of 10.0", H8's 1.1 and 17, and the totals 21 / 29 / 170 are the lead's arithmetic from P10-S1's manifests (H8 took 1,619 s and 3,204 s per loaded cell there) and have not been reviewed. All of them are replaced by the rehearsal's measurements.

### 17.1 The block budget: a design ceiling with a written rule

**Block M's total projected charged time at 1× is at most 60 hours.** "At 1×" means the plain projection, without the factor 2 of the cap rule in §15. The total counts the hours already charged by the timing preview, the calibration and both rehearsals, and the projection of every registered stage.

1. **When and from what.** The projection is computed once, by the frozen projection code, when the candidate plan is written, and it is part of the plan the freeze commits. Its inputs are the measuring rehearsal's rates only (seconds per update per arm and size at the worker count chosen, evaluation seconds per snapshot, the contention ratio), the plan's lengths and snapshot counts, and the ledger of hours already charged. No registered seed has been observed at that point.
2. **Base plan.** Every cell that is not loaded at its length of §7.2, R2 at U_P, every loaded cell at its U₀, and the evaluation, gates, timing, throughput, analysis and report stages. **If the base plan alone projects above 60 hours, the work returns to the human lead before the freeze**, with the projection. The lead drops no cell, arm or replicate and shortens no length to make it fit.
3. **Extensions, granted by rule in a fixed order.** A loaded cell type is a loaded cell and an arm; a grant covers all five of its replicates at once and is costed as if every replicate used it. The steps are the ladder points above U₀: 1.5 · U₀, 2 · U₀, 3 · U₀, 4 · U₀. Steps are considered level by level (all cell types at 1.5 · U₀ first, then 2 · U₀, and so on). Within a level the order is: **ascending load, then ascending facts, then the arm order D-OQ, F-OQ, T-OQ, H8.** The three loaded cells all have load 8, so the order within a level is 2K/256 (F-OQ), then 8K/1K, then 32K/4K, each in the arm order.
4. **The test.** A step is granted if the projected total with it stays within 60 hours. A cell type whose next step would exceed the budget **stops there**: it is closed and receives no later step. Consideration goes on with the next cell type in the order.
5. **The dense control is never given less than a store arm.** F-OQ, T-OQ or H8 is granted a level at a cell only if D-OQ holds that level at that cell. D-OQ comes first in the arm order for this reason: the budget must not leave the dense map with fewer multiples of U₀ than the store it is compared with at saturation. (2K/256 has no D-OQ cell and no dense label; the condition does not apply there.)
6. **Result.** Each loaded cell type has a granted length G in the plan (§7.2 item 6). In the run a cell continues until it is full or reaches G. Not full at G: **NOT FULL WITHIN BUDGET**, a registered value, not a negative; the report prints G and 4 · U₀ beside it.
7. **No partial result decides a grant.** Grants are fixed in the frozen plan before Decision 2. Budget left unused because cells were full early is not redistributed, since that would make a grant depend on registered results. No grant is added during or after the run because a cell looks close (DIRECTION.md §5 rule 4). A later extension of G is a new decision of the human lead on cost projections only, recorded before the cells concerned are read further, and it applies to a cell type as a whole.
8. **The budget and the caps.** The hour caps are still set by §15's rule from the rehearsal (charged + 2 × projected remaining). Under the delegation their sum for block M is at most 60 charged hours; where the rule gives more, the caps are set to sum to 60 and a stage that reaches its cap is PAUSED. Raising the sum above 60 is the human lead's own decision.

**What the budget is expected to cut off** (the lead's arithmetic at P10-S1's rates; estimates, not reviewed):

| If the calibration finds U₀ at | Base plan | All extensions to 4 · U₀ would add | Expected effect of the budget |
|---|---|---|---|
| P10-S1's lengths (the central case) | about 26 | about 26 | Nothing is cut: every loaded cell can be granted 4 · U₀ (about 52 in total) |
| twice P10-S1's lengths | about 36 | about 53 | The levels 1.5 · U₀ and 2 · U₀ fit (about 54); 3 · U₀ fits only for the cheaper cell types early in the order; 4 · U₀ for none or almost none. Cells not full by then are NOT FULL WITHIN BUDGET |
| three times P10-S1's lengths | about 46 | about 79 | About one level (1.5 · U₀), and not for every cell type |
| the calibration ceiling (four times) | about 64 | about 106 | The base plan does not fit. The work returns to the human lead before the freeze |

So the budget removes roughly the upper two thirds of what the design ceilings alone would allow (about 170 hours against 60). What it can cost scientifically is stated in §20: a loaded cell that needed more than its granted length is NOT FULL WITHIN BUDGET, and its step and its saturation pair are then not decided.

The rehearsal measures, before any cap is set: seconds per update per arm and size; the contention ratio at six workers and at one higher count (the count with the lower projected charged hours is used; a cost rule, not a scientific choice); evaluation seconds per snapshot with DEP at every snapshot; peak memory.

## 18. Engineering requirements carried from P10

| P10 failure | Requirement here |
|---|---|
| A status note committed to a frozen ADR stopped 171 cells (ADR-0021 §25.19–25.20) | **One frozen-input set for block M's freeze, and the ADR text is outside it.** The set is: `studies/p10is1/**`, the stage's config (which holds every threshold and rule parameter), launch scripts, `freeze/plan.json` (with the granted lengths and the projection of §17.1), stage caps, calibration records and data manifests, every module imported from outside `studies/p10is1/` (from `studies/p10s1/`, `studies/p9/` and `src/arborlm/`) and `uv.lock`, each by SHA-256. In detail: the study's own files and `uv.lock` are identified by the SHA-256 of each file, recorded in the freeze record. The imported code (`studies/p10s1/`, every `studies/p9*/` package that is imported, and `src/arborlm/`) is identified **by comparison with the freeze commit**: each imported file in the working tree must equal the same path at the commit named in the freeze record. `HEAD` itself is never compared, so a later commit that touches none of these paths stops nothing (the failure of P10-S1 attempt 1). The freeze record also stores the ADR's hash for provenance only; no task reads it. Nothing is written in the frozen files between Decision 2 and the end of the report stage; status and notes go to the human lead directly or to another branch. A task that finds an identity difference stops as PAUSED — IDENTITY; if the file is restored bit for bit the stage resumes and completed cells are kept. A test asserts that every threshold in this ADR's tables equals the config's value |
| The throughput stage's item list did not match the frozen plan; the tests used another plan (§25.21) | Every registered stage is rehearsed end to end on the rehearsal draw **against the frozen plan file itself**; each stage's item list is derived from that file only; a stage whose items are not all in the plan refuses at the freeze |
| The plan's caps and the rehearsal depend on each other (ADR-0029 §19 ruling 5, §20) | Two rehearsals. A measuring rehearsal on provisional caps measures seconds per update, contention, evaluation seconds per snapshot and peak memory. The caps are set from it by §15's rule and written into the candidate `freeze/plan.json`. A counting rehearsal then runs every registered stage end to end against that file, and its SHA-256 goes into the rehearsal record. The freeze refuses unless the committed plan has that hash. Nothing is frozen on the measuring rehearsal. **Order, as in ADR-0029:** the candidate plan is written first (cells, lengths, snapshots, items); the measuring rehearsal runs against it on provisional caps; the caps (charged + 2 × projected remaining, within §17.1) and the granted lengths are then written into it; the counting rehearsal runs against that exact file; the freeze refuses any other. Both rehearsals use the rehearsal draw only, with the analysis and the report run on a synthetic registry keyed by the plan's labels |
| A code error recorded as a result (ADR-0029 §20 ruling 11) | An exception inside an item that is not a gate failure, a resource cap or an identity stop is never a NOT_EVALUATED, DEPENDENCE_FAILED or failed cell. If any registered stage has one, the analysis refuses and every line prints ENGINEERING STOP — ITEM ERRORS. An environment error (out of memory, file system) stops the task as PAUSED — ENVIRONMENT, and the task resumes once the environment is fixed without a code change. A registered training cell that ends with a non-finite loss is a recorded failed cell: kept, not re-run, the stage INCOMPLETE (§14). §14 defines non-finite and states that such a cell never becomes a scientific verdict |
| An unstated combination rule; a check the reference fails; a report section comparing the wrong reads (audit D4, D7, D1) | Every reading and combination rule is in §8–§9. R2 is run through every validity check in the rehearsal and a check it fails is not used (§8.1). **The analysis and the report are tested on a synthetic registry with known answers that covers every verdict, class, label and outcome and every descriptive section:** each registry key carries the read's name, two reads of one cell can never share a key, and a test plants distinct values in every read and asserts each printed figure |
| Report defects of P10-S1 (audit D2, D3, D6, D9–D12) | The report prints every replicate, panel, cell and reading a rule names, not-full replicates included (D2, D9); every dense label with all four readings (D3); every annotation in the cell it belongs to (D10). **Each count says what it counts** (cells and reads are counted separately; P10-S1 printed "185 cells read" for 150 cells and 35 reads, D6). **Every section names the run and stage it came from** (P10-S1 printed the rehearsal's timing unlabelled, D12). **One cap figure** appears in the plan and the manifests (P10-S1's plan held two, D11) |
| A count gate stopped P10-S2 although its quality criteria were met | Loaded cells run until full within a stated budget; searches extend by rule and end at written ceilings (§7) |
| P10-S0 tested overload at one load and one length | Not this study's question (ADR-0023); loaded cells here run to a convergence rule |
| A tie test passed on macOS and failed on Linux (§25.23) | The platform of record is named (§16); exact reproduction (G4) is asserted on it only |
| GitHub CI is costly | Checks run locally (§16) |

## 19. Decision map (recommendations only; nothing is authorized)

CAPACITY-NEGATIVE (b) → on this task the dense map is the better use of the parameters; what the store offers must then be shown elsewhere (sparse updates, measured cost, storage), in studies designed for it. CAPACITY-POSITIVE carried by a trained arm → the necessary condition is met at these sizes; whether it extends to 65,536 slots is block X's question, once that block is specified and decided (§12). KEY-LEARNING-LIMITED → study key learning under load (ADR-0021 §8.9). Any INCONCLUSIVE → no decision on that line.

## 20. What this study cannot establish

- Anything about the language model forming queries, natural language, learned addressing, or capability beyond recall of trained random facts.
- Value beyond a lookup table (§3). Efficiency, latency, energy or I/O of any system: counted work and MC-A are logical; MC-T and throughput are in-RAM CPU figures for a 27,392-parameter backbone on one machine.
- Capacity above 16,384 slots. Block X is not approved; block M says nothing about 65,536 slots.
- What a loaded cell would hold beyond its granted length. The block budget of §17.1 can stop a cell before 4 · U₀; such a cell is NOT FULL WITHIN BUDGET, and its step and saturation pair are then undecided, not negative.
- That a SUBPROPORTIONAL saturation verdict is a property of the store. A capacity "per slot" in general.
- That the store or the dense map is better "when tuned": each has one family and one grid, with the rate chosen at 65,536 updates at loaded cells.
- More about learned keys than one comparison with one hashed-address control (H8) at one rate grid; H8 is not searched at the loaded cells and is not calibrated at U_P there.
- Why the tree is behind the flat memory, or what would fix it (ADR-0029). Whether longer training closes that gap (ADR-0026).
- TRANSFER or SYSTEM outcomes, Astra validation, or any approval not recorded.

## 21. The choices that were open, and how each is ruled

Drafts 1–3 listed these as open choices for the human lead. Each is now ruled by Decision 1 (§24), taken by the lead under the human lead's delegation of 2026-11-18, at the recommended option unless the third review said otherwise. Where the review said otherwise, the stricter text for the store is adopted. Items that stay with the human lead himself say so. He can change any of them before the freeze.

1. **Task (§3).** RULED: the task is kept, with every label capped at "necessary condition". The alternative was to hold the study until a task a lookup cannot solve is designed.
2. **Block X (§12).** The block is deferred to a revision and its own approval, after block M's outcome. H_X is set by the human lead himself (the lead's earlier suggestion was 100 charged hours; with evaluation, the central P_X of draft 3's design is about 102–112). **PENDING HUMAN LEAD RULING; not taken under the delegation.** The review's edit E10 would have kept block X's rules fixed in this text; the lead's ruling goes further and fixes none of them: §12 keeps only what is settled (its own line, fresh draws, the registry's seeds, H_X with the human lead) and lists what the revision must add.
3. **Lane L and the freeze (§13).** RULED: block M does not wait for P10-I-S0; lane L is specified in a later revision and frozen separately. Lane L is not approved.
4. **Dense reading (§9.2).** A positive needs all four readings; a negative is ADR-0021's (any one reading, any cell, any loaded cell) (adopted). The narrower negative of draft 3 is reserved to the human lead and is not taken under the delegation. The lead asked for one of the removed narrowings himself in an earlier draft; two independent reviews removed them (§9.2).
5. **H8.** RULED: kept at all seven cells ADR-0021 ran it, with ADR-0021's UNDERTRAINED-AT-U_P rule (§4), at about 1.5 charged hours at P10-S1's lengths. The choice is no longer open. Drafts 1–3 recommended leaving it out.
6. **Split rule (§9.2, §9.5).** A positive needs every cell and both readings; a negative needs one cell in one reading (adopted). The symmetric alternative of draft 3 is reserved to the human lead and is not taken under the delegation.
7. **DEP-c's floor of 0.01** (§8.1). RULED: kept. It was written before the audit, is disclosed, and decides none of P10-S1's 32 failing reads (third review, section H).
8. **The split of the routing diagnosis into ADR-0029.** Recommended by the reviewer and the lead. **RULED by the human lead on 2026-11-17: "Keep ADR-0029".** The routing diagnosis stays its own ADR; this file was renamed accordingly.
9. **The calibration ceilings** (§7.2: four times P10-S1's run lengths; U_P at most 65,536). RULED: kept as rules. Their cost bound is not left open: the block budget of §17.1 holds block M to 60 projected charged hours, the upper figure the human lead was shown, and anything beyond it goes to him.
10. **F-OQ-IVF in C-CAPACITY (§9.3).** RULED: it enters the outcome as in ADR-0021 and qualifies no arm for another study's entry.

## 22. Review record

All three reviews are by the `arbor-auditor` subagent (Claude Opus 5.5, as each review states of itself). All revisions are by the lead's workflow (Claude Fable 5.2). Draft 3 was reviewed in `REVIEW3_ADR-0024.md`; the edits that review lists are applied as §22.3 records, and **the text with them applied has not been reviewed again.** No review is Astra validation or a human approval.

### 22.1 First review (`REVIEW_ADR-0024.md`, NOT READY: 2 blocking, 15 required, 12 advisory)

| Finding | Severity | Disposition | Where |
|---|---|---|---|
| F1 U_P and rates circular; R2 and D-OQ units | BLOCKING | FIXED | §7.1 |
| F2 tree label misassigns causes | BLOCKING | MOVED TO ADR-0029 | ADR-0029 §8 |
| F3 N/8 | REQUIRED | MOVED TO ADR-0029 | ADR-0029 §8.4 |
| F4 matched compute primary after observation | REQUIRED | FIXED (completed in draft 3: D-BEST restored on the favouring side) | §9.2 |
| F5 efficiency rule's effect on P10-S1; rows 1–2 | REQUIRED | FIXED | §9.5 |
| F6 DEP snapshots; i\* snapshots; audit result | REQUIRED | FIXED | §2 item 10, §8.1, §9.1 row 2 |
| F7 DEP-c reasons | ADVISORY | FIXED; p⁺ kept and stated as deliberately conservative | §8.1 |
| F8 U_P / run length | REQUIRED | MOVED TO ADR-0029 | ADR-0029 §9 |
| F9 R-CONFIRM not like for like | REQUIRED | MOVED TO ADR-0029 | ADR-0029 §10 |
| F10 cost projection | REQUIRED | FIXED | §12, §17 |
| F11 recall records misdescribed, unsealed | REQUIRED | MOVED TO ADR-0029 | ADR-0029 §4, §11 |
| F12 one ADR, two freezes | REQUIRED | FIXED: split; ADR text is not a frozen input | header, §18 |
| F13 PK-OQ | REQUIRED | FIXED: removed | §4 |
| F14 quiet-machine rule | REQUIRED | FIXED | §10, §16 |
| F15 disclosure placement | REQUIRED | FIXED | §8.1, §9.2, §9.5 |
| F16 Lane R gates | REQUIRED | MOVED TO ADR-0029 | ADR-0029 §11 |
| F17 snapshot schedule; arm names; cost of NOT FULL | REQUIRED | FIXED (completed in draft 3: U_P multiples at loaded cells) | §7.2, §12 |
| F18 crowding at 131,072 | ADVISORY | FIXED | §2 item 11, §12 |
| F19 dropping H8 | ADVISORY | ANSWERED in draft 3 (not run, the loss stated, the choice open); **REVERSED after the third review: H8 is kept** | §4, §21 item 5 |
| F20 bridge duplication | ADVISORY | MOVED TO ADR-0029 | ADR-0029 §10 |
| F21 measurement definitions | ADVISORY | MOVED TO ADR-0029 | ADR-0029 §3, §6, §7 |
| F22 STORE HOLDS MORE cost condition | ADVISORY | FIXED | §9.2 |
| F23 quotation details | ADVISORY | FIXED; ANSWERED for 1.946 (ADR-0021 §25.16; the confirmation review agrees) | §16, §17 |
| F24 replicate accounting | ADVISORY | MOVED TO ADR-0029 | ADR-0029 §8.2 |
| F25 tags; "necessary condition" wording | ADVISORY | FIXED | §1 |
| F26 a_use floor; "in bits" | ADVISORY | FIXED here for the floor; the rest MOVED TO ADR-0029 | §8.1 |
| F27 seeds | ADVISORY | FIXED in draft 3: registry values cited | §6 |

### 22.2 Confirmation review (`REVIEW2_ADR-0024_ADR-0029.md`, NOT READY)

| Finding | Severity | Disposition | Where |
|---|---|---|---|
| B-M1 matched compute not readable at loaded steps | REQUIRED | FIXED | §7.2 item 2 |
| B-M2 calibration ladders without a ceiling | REQUIRED | FIXED: ceilings with registered outcomes | §7.2, §12, §15 |
| B-M3 three ambiguities in the order rule | REQUIRED | FIXED | §7.1 |
| B-M4 inaccurate disclosure; D-BEST dropped | REQUIRED | FIXED: D-BEST required for a positive; disclosure rewritten; the narrower negative stated | §9.2 |
| B-M5 lane L not specified enough | BLOCKING for lane L | FIXED: lane L reduced to what is settled and a list of what a revision must settle; not approved with this draft | §0, §13 |
| B-M6 block X's draws and funding | REQUIRED | FIXED: fresh draws; funding by a rule fixed at Decision 1 | §12 |
| B-M7 block X's arm classes | ADVISORY | FIXED | §12 |
| B-M8 quiet-reading wording | ADVISORY | FIXED | §16 |
| B-M9 vacuous arm-level dense label | ADVISORY | FIXED: NOT APPLICABLE | §9.2 |
| B-M10 report defects not named | ADVISORY | FIXED | §18 |
| B-M11 file name | ADVISORY | FIXED after the ruling of 2026-11-17: renamed to `ADR-0024-p10-i-s1-capacity-scaling.md` | header |
| B-M12 stale seed text | REQUIRED | FIXED | §6 |
| B-M13 arms that may carry an entry label | REQUIRED | FIXED | §9.3, §21 item 10 |
| §G lane L's measure is not a free choice; worker count is a cost rule | — | FIXED | §13, §17, §21 |

Changed in draft 3 and reviewed in the third review: block X's fresh draws, N3 trained on them, the funding rule P_X ≤ H_X; the calibration ceilings; §13 as reduced. The third review's status for each finding above is in its section C: B-M4 and B-M12 PARTLY FIXED (completed below), the rest FIXED, with a new problem under B-M6 (block X, F8). Where a row of §22.1 or §22.2 points to §12 for a block X rule (F10, F17, F18, B-M2, B-M6, B-M7), it points to draft 3's block X text, which §12 no longer holds (§22.3, F8); those dispositions are history and approve nothing.

### 22.3 Third review (`REVIEW3_ADR-0024.md`; block M READY AFTER THE LISTED EDITS; block X NOT READY; lane L outside the approval)

"As written" means the review's replacement text stands in this ADR word for word. Every other disposition says what differs and why.

| Finding / edit | Severity | Disposition | Where |
|---|---|---|---|
| F1 / E2 Δ_MC read in analytic cost alone | REQUIRED | FIXED: E2 as written, **plus** the comparator reading MC-C, which keeps ADR-0021's larger multiplier and its rule for disagreeing measures (lead's addition, stricter); disclosed | §8.2, §9.1 |
| F2 / E3 dense negative narrowed after observation | REQUIRED | FIXED: E3 as written (the DENSE AHEAD row, the arm-level sentence, the disclosure bullet, §21 item 4). Added: MC-C among the readings, the three removed narrowings named, the lead's own part recorded, the effect on P10-S1's records | §9.2, §21 item 4 |
| F2 / E4 efficiency negative narrowed after observation | REQUIRED | FIXED: E4 as written (row 4, the disclosure, the §10 row, §21 item 6). Row 5's reason DENSE SPEED SPLIT is renamed DENSE SPEED UNDECIDED, since a split now gives a negative | §9.5, §10, §21 item 6 |
| F3 / E1 seeds and gate G9 | REQUIRED | FIXED: E1 as written; one sentence of the old bullet (no arithmetic derivation) kept after it | §6 |
| F4 / E6 quiet condition | REQUIRED | FIXED, **not as written**: E6's start and end conditions are as written; its "three further sessions, then NOT MEASURED" is replaced by the lead's ruling (five rescheduled attempts, then PAUSED; NOT MEASURED only by an explicit recorded decision). The §15 row is rewritten to match | §10, §15, §16 |
| F5 / E8a two rehearsals | REQUIRED | FIXED: E8a as written, with ADR-0029's order spelled out after it | §11, §18 |
| F6 / E8b code and environment errors | REQUIRED | FIXED: E8b as written in §18 and §9.3 row 2; §14 adds the definitions of non-finite and of a diverging run and states that none of these is ever a scientific label | §7.1, §9.3, §14, §18 |
| F7 / E5 cost within the ceilings | REQUIRED | FIXED: E5's paragraph and the §15 clause as written; the cost table corrected (21 / 29 / about 170); **and a block budget of 60 projected hours added as a design ceiling with a written rule** (lead's ruling) | §15, §17, §17.1 |
| F8 / E10 block X cannot be implemented as written | REQUIRED | **NOT APPLIED AS WRITTEN; superseded by a stricter ruling.** E10 kept block X's rules fixed and deferred its approval. The lead's ruling removes the block's rules from this text: §12 holds what is settled and the list of what a revision must add (F8's items among them). §0 and §11 are rewritten accordingly | §0, §1, §11, §12, §21 item 2 |
| F9 block X probably not funded at 100 hours | ADVISORY | ANSWERED: recorded for the human lead, who sets H_X himself | §12 |
| F10 / E7 imported code and the lock file | REQUIRED | FIXED: E7's inserted words as written; the lead's ruling on the method follows them (the study's files and `uv.lock` by hash, the imported code by comparison with the freeze commit, never `HEAD`) | §18 |
| F11 / E9 platform settings | REQUIRED | FIXED: E9 as written | §16 |
| F12 / E11 lane L wording; a missing printed state | ADVISORY | FIXED: E11 as written | §13 |
| F13 no counterfactual disclosure for capacity | ADVISORY | FIXED: the review's item 21 as written, beside the rule | §9.3 |
| F14 N3 costly and descriptive | ADVISORY | MOVED to block X's revision | §12 item 8 |
| F15 options on the F-OQ-not-full return | ADVISORY | FIXED | §7.2 item 5 |
| F16 two wording points | ADVISORY | FIXED: the cost reason is stated as holding for F-OQ only; the §10 row names the dense-at-saturation label | §9.2, §10 |
| F17 dropping H8 | ADVISORY, PENDING LEAD REVIEW | FIXED: H8 kept at all seven cells, with the equal rate search and ADR-0021's annotation rule | §4, §5, §7, §9, §21 item 5 |
| E12 a subsection §8.3 with rulings 1–21 | — | APPLIED IN ANOTHER PLACE: §8.3 points to §23, which holds the twenty rulings with the review's text and the adopted ruling for each; item 21 stands beside §9.3 | §8.3, §9.3, §23 |
| Section B: totals "0 of 4,394" and "+0.0101" | — | NOT RECOMPUTED by the third review (they need per-read counts); they remain the first review's figures, as §2 says | §2 item 10 |
| Section G: running beside another study | — | FIXED: adopted | §16, §16.1 |
| Section H: which open choices may be taken under the delegation | — | FOLLOWED: items 2, 4 and 6 are not taken at draft 3's option; H8 is kept; the cost bound is held by the block budget | §21, §24 |

**Narrowings and relaxations that draft 3 did not disclose** (third review, B-M4, F1, F2), and what became of each:

| Undisclosed in draft 3 | Direction | Now |
|---|---|---|
| An arm was DENSE AHEAD only at **every** CAPACITY STEP cell (ADR-0021: any) | Narrowed the negative | Removed; "any" restored (§9.2) |
| DENSE HOLDS MORE counted only at **every** loaded cell (ADR-0021 §8.5 row 1: any) | Narrowed the negative | Removed; "any" restored (§9.2) |
| The capacity step's Δ_MC read in MC-A alone (ADR-0021: the larger of the two multipliers) | Relaxed the positive | Removed; both measures and the comparator reading required (§8.2, §9.1) |
| The efficiency negative needed every cell in both readings | Narrowed the negative. Draft 3 disclosed it; it is listed because it was not to be taken under the delegation | Removed; the any-cell negative restored (§9.5) |
| A dense lead needed matched compute | Narrowed the negative. Draft 3 disclosed it as "one thing is narrower" | Removed; the annotation NOT AT MATCHED COMPUTE is printed in its place (§9.2) |
| H8 left out | Removed the only check that can count against learned keys. Disclosed as a loss, offered as a recommendation | Reversed; H8 kept (§4) |

`Astra review: NOT_PERFORMED`.

## 23. Rulings for the implementer

The third review (its section F) listed what an implementer would have had to guess. Each row gives the review's recommended ruling in its own words and the ruling adopted. "Adopted" alone means adopted as recommended. Where the lead's rulings of §24 change a recommendation, or where the more conservative reading for the store was taken, the row says so. No registered result has been observed. These rulings bind the implementation and the implementation audit.

| # | Point | The review's recommended ruling | Adopted ruling |
|---|---|---|---|
| 1 | Δ_MC direction in a reading where the larger cell is the cheaper | U_MC = U_P in that reading (E2) | Adopted. In addition the comparator reading MC-C of §8.2 is computed wherever MC-T is measured and must also give Δ_MC ≥ 0.5. More conservative than the recommendation: it keeps ADR-0021's larger multiplier where the two measures disagree on the direction |
| 2 | F-OQ-IVF's cost | F-OQ-IVF's MC-A and MC-T costs per update, and its cost in STORE HOLDS MORE, are F-OQ's training costs; the index build is not counted. Its matched snapshots are F-OQ's | Adopted |
| 3 | DEP qualification beyond U_P | A snapshot at update u maps to the fraction u/U_P. At fractions above 1, the qualification at fraction 1 applies. A condition stays qualified at a fraction where R2 is under the a_use floor; only an actual R2 failure disqualifies it | Adopted |
| 4 | Registered R2 failure | "Not applied at that snapshot in that replicate" means: at that fraction, for every arm of that row, in that replicate. It is printed per arm | Adopted |
| 5 | DENSE AHEAD counts | Counts are per reading, and a replicate counts if either panel meets the condition (as E3). MC-SHORT replicates do not count in that reading | Adopted. MC-C is a reading for this purpose |
| 6 | MC-SHORT in row 4 | A pair MC-SHORT in either reading fails Δ_MC (E2) | Adopted; MC-SHORT in MC-C fails it too |
| 7 | Calibration "full" | It includes ADR-0021's i\* ≤ 4.0. F-OQ full but above 4.0 on a view at its U₀ is treated as "F-OQ not full at the ceiling", which returns the work to the human lead before the freeze | Adopted (§7.2 items 4 and 5), with his two options named |
| 8 | Order of the loaded-cell work | The loaded-cell rate units (at 65,536) precede the load search. The load search continues each selected rate's calibration runs from their 65,536 checkpoint (G4 restoration); no new runs are started | Adopted. H8 and D-OQ have loaded-cell rate units and are not load-searched |
| 9 | Plan items for run-until-full | The plan lists every loaded cell with U₀, the maximal length 4·U₀ and every snapshot up to it. A cell stops at the first ladder point at which it is full. Later items are recorded NOT REACHED, not missing. The stop statistic is computed by the frozen code and not displayed (whitelist) | Adopted, with the granted length G of §17.1 in place of 4·U₀ as the maximal length; the plan prints both |
| 10 | i\* in the stop rule | i\* is the maximum of i over snapshots ≤ U on each panel. DEP is not consulted; DEP enters the verdicts, not the stopping rule | Adopted |
| 11 | U_run of a loaded cell | U_run is the ladder point at which the cell was found full, or 4·U₀ | Adopted, with G in place of 4·U₀ |
| 12 | MC-T source | One isolated timing stage after Decision 2 and before training, on the rehearsal draw, covering every arm × size including 256 slots and R2's cells. It is all or nothing | Adopted; H8 is among the arms. The stage runs alone, and training does not start while it is PAUSED (§16) |
| 13 | Timing preview | No quiet condition; it sets caps only (E6) | Adopted |
| 14 | Cap projection | U₀ with the 4·U₀ bound printed beside it (E5) | Adopted. The projection also carries the block budget and the granted lengths (§17.1) |
| 15 | Item, environment and non-finite errors | As E8b | Adopted, with the lead's ruling stated in §14: each is an engineering stop and never a scientific label; non-finite and a diverging run are defined there and in §7.1 |
| 16 | INCOMPLETE | No outcome on any line (E8b) | Adopted |
| 17 | DEP for D-OQ | DEP-a, DEP-b and DEP-c apply to D-OQ wherever a rule reads D-OQ at a_use ≥ 0.25 (efficiency qualification, dense readings), with the same R2 qualification. **PENDING LEAD REVIEW**; ADR-0021's text says "memory cell" | **Adopted in a more conservative form.** DEP-a (the dense addition disabled gives chance) and DEP-c are computed and printed for D-OQ at a_use ≥ 0.25, with the same R2 qualification; DEP-b is not defined for a map without a value table and is not applied. A D-OQ failure blocks every store-favouring label that reads that D-OQ snapshot in that replicate (STORE NOT BEHIND, STORE HOLDS MORE, DENSE NOT FASTER count as not established there). It never removes a reading that counts against the store: a dense lead stands, and D-OQ's snapshot still qualifies for u_T. Reason: applied as recommended, a dependence failure of the dense control could delete a dense lead, which favours the store |
| 18 | U_P's "row's larger step cell" | It is 2K/4K, 8K/4K and 32K/16K for the three rows, as ADR-0021 §10.1 item 1 | Adopted |
| 19 | Edge walk | A best rate within 0.02 of an edge chosen by the walk is taken, recorded as EDGE BY TIE-WALK, and not extended (ADR-0021 §10.1 item 3). A diverged rate is a run that ends `failed` or whose readout is inside the chance interval | Adopted (§7.1). A run that ends with a non-finite value is diverged as well; "inside the chance interval" is read as P10-S1's calibration read it (the raw Panel A correct count, on either draw) |
| 20 | Binomial quantile in DEP-c | It is the smallest k with P(X ≤ k) ≥ 1 − 10⁻⁴, computed exactly in log space (no package outside the lock). "Exceeds" means strictly greater | Adopted (§8.1) |

The review's item 21 is a disclosure, not a guess; it stands beside §9.3.

Further rulings the kept and changed parts need, by the lead, not reviewed:

| # | Point | Ruling |
|---|---|---|
| 21 | H8's rate | The equal rate search of §7.1, in the same units as F-OQ and T-OQ. ADR-0021 ran H8 at 0.003 untuned; "every trained arm gets the same search" is this ADR's rule and H8 is a trained arm |
| 22 | H8 at the loaded cells | Not load-searched; starts at the larger of F-OQ's and T-OQ's U₀, as D-OQ does, and follows the ladder to its granted length |
| 23 | H8's annotations | UNDERTRAINED-AT-U_P and H8 NOT CALIBRATED AT U_P AT cell, as §4 states. They are annotations on H8's printed classes and gate nothing |
| 24 | Order of grants | §17.1 items 3–5. The projection code is part of the frozen set and is tested on planted rates with known answers, including a base plan above the budget |
| 25 | The quiet-condition decision | The code offers no path that writes MC-T NOT MEASURED or THROUGHPUT NOT MEASURED without a decision file naming the six PAUSED attempts; a test asserts this |
| 26 | The machine-wide memory check | Free memory of the whole machine is read at the start of each stage and before each worker is added; the wait has a deadline and ends PAUSED — ENVIRONMENT (§16.1) |

`Astra review: NOT_PERFORMED`.

## 24. Approval record — Decision 1 for block M only (2026-11-18 UTC)

**The review trail.** Three independent reviews by the `arbor-auditor` subagent (Opus 5.5): the first, of draft 1, NOT READY; the confirmation review, of draft 2, NOT READY; the third, of draft 3: **block M READY AFTER THE LISTED EDITS**, block X NOT READY, lane L outside the approval. The edits are applied as §22.3 records, with the departures named there. **The text with the edits applied has not been reviewed again.** It also contains rulings of the lead that no review has read: the comparator reading MC-C, the block budget and its grant order, the quiet-condition rule, H8's rate search and annotations, and the conservative form of ruling 17.

**The delegation.** The human lead delegated the decisions that gate each P10-I study to the lead (`docs/reviews/p10-i-direction-2026-11-17/DELEGATION_2026-11-18.md`). His words, verbatim:

> once its done can you accept the results as they come and continue with the next simulations until you conclude P10-I-*

> and you have my permission to auto approve everything until you complete P10-I

The first sentence is recorded in section 1 of that file. The second was given later and is **not yet in the committed delegation record** at the commit this text is based on (`ef5596b`); the lead adds it to that record, and does so before any Decision 2. Until it is there, this approval rests on the first sentence as section 2 item 2 of that file reads it ("approval for implementation and rehearsal", taken "at the options the drafts recommend unless an independent review says otherwise").

**Decision 1.** The lead (Claude Fable 5.2), under that delegation, approves **block M only** of this ADR for **implementation and rehearsal**.

**What this approves.** Implementation of block M in new files (`studies/p10is1/`, `configs/p10is1_capacity.toml`, `tests/test_p10is1_*.py`) by the `arbor-implementer` subagent, an independent implementation audit by the `arbor-auditor` subagent in a separate context, the timing preview and the calibration of §7 on the calibration draws, and the two rehearsals of §18 on the rehearsal draw. The choices of §21 are ruled as that section states. The rulings of §23 bind the implementation. Wherever an earlier section still says PENDING HUMAN LEAD RULING for a block M choice, read it as ruled by this record; the human lead can change any of it before the freeze.

**What it does not approve.**

- **Lane L** (§13): no cell, rule, seed or budget.
- **Block X** (§12): no cell, rule, entry condition, seed use or budget. H_X is the human lead's own figure.
- **The freeze** of block M, and **the registered run**: these need Decision 2, taken on the rehearsal records and the implementation audit. No registered seed is observed before it, apart from gate G1.
- **Any threshold change.** No threshold, label, rule, seed or replicate count changes after this point without a recorded amendment, and none is ever relaxed after observation.
- A base plan above the block budget, a sum of caps above 60 charged hours, or an extension of a granted length: each goes to the human lead himself (§17.1).
- Recording MC-T as NOT MEASURED before the attempts of §16 are exhausted.
- Merges to `main`, publication, pushing weights, paid services, packages outside the lock, and any change to a completed study.

**Stated plainly.** Nothing under this ADR has been implemented or run. No result exists. The lead's expectation, written in §9.3 before any observation, is that CAPACITY-NEGATIVE by clause (b) is the single most likely outcome; the stricter dense rule adopted here makes that more likely, not less. This approval is not a success claim, not Astra validation and not the human lead's own approval of the text.

`Astra review: NOT_PERFORMED`. Claude review is not Astra review.
