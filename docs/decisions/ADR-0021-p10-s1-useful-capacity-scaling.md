# ADR-0021 — P10-S1: Useful-capacity scaling under controlled addressing

- **Status: DESIGN REVISION 4 — REVISION 3 RE-CHECKED BY THE AUDITOR: READY SUBJECT TO R1, R2 AND m1–m11 (`docs/reviews/p10-design-2026-11-15/adr-0021-review/RECHECK_REV3.md`), WHICH THIS REVISION APPLIES (§21). SPEC: PENDING ASTRA REVIEW. Nothing is implemented or run.**
- **Date:** 2026-11-15
- **Study code:** P10S1. Package `studies/p10s1/`. Config `configs/p10s1_capacity.toml`. Tests `tests/test_p10s1_*.py`.
- **Revision history.**
  - Revision 1: `ADR-0021-p10-s1-useful-capacity-scaling.md` (unchanged). Reviewed by Opus 5.5: **NOT READY**, 4 blockers, 11 majors, 17 minors — `adr-0021-review/REVIEW.md`, scripts and outputs beside it.
  - Revision 2: `ADR-0021-p10-s1-useful-capacity-scaling.rev2.md` (unchanged). It applied the review under the lead's rulings. Confirmation review by Opus 5.5: **READY AFTER LISTED TEXT EDITS**, K1–K7 — `adr-0021-review/CONFIRM.md`.
  - Revision 3 (this text) applies K1–K7 with the auditor's text and the auditor's bracketed values, and the lead's final rulings. §17 maps every finding to its change. §18 lists the lead's choices. §19 records how each conflict of revision 2 was closed. §20 lists what differs from the auditor's text.
- **Origin.** The human lead's P10 milestone direction: three parallel, independent experiments (S0 addressing qualification, ADR-0020; S1 capacity, this ADR; S2 two-teacher transfer, ADR-0022).
- **Milestone question 1 (verbatim).** "Can increasing ArborLM's learned-memory capacity produce measurable gains in retained knowledge and useful capability without proportional increases in active inference work?"
- **Roles (study-specific).** Lead: Claude Fable 5.2. Specification review, implementation audit and recomputation from raw records: Opus 5.5, in a context separate from the implementation. Implementation: Sonnet 5.5. Inventory: Haiku 5.5. The model that actually ran each delegated task is recorded from session metadata. ADR-0012 stays not approved. **Astra review: NOT_PERFORMED.**
- **Relation to other work.** S1 does not wait for S0 and does not depend on S2. ADR-0017 Lanes A–D stay calibration blocked. P1–P9-I code, configs, records and ADRs are not edited.
- **Marking.** *(lead's choice)* marks a number or rule the lead chose; §18 collects them.

## 0. What S1 is a study of (decided before calibration)

S1 registers **two separate result lines**. Neither implies the other.

1. **CAPACITY.** A smaller memory that is loaded (§8.2), and a larger memory that holds more useful information at matched updates and at matched compute. Labels: CAPACITY-POSITIVE, CAPACITY-NEGATIVE, CAPACITY-INCONCLUSIVE, and **CAPACITY NOT TESTED — NO LOADED CELL WITHIN BUDGET**, which is not a negative.
2. **LEARNING EFFICIENCY.** A larger memory that reaches a fixed level of useful information in fewer updates and less compute. Labels: EFFICIENCY-POSITIVE, EFFICIENCY-NEGATIVE, EFFICIENCY-INCONCLUSIVE. Every efficiency verdict is printed with the row-movement ratio of §7.3.

The reading for milestone question 1 uses the capacity line only.

## 1. What is known, with sources

Registered (P9-I, one data draw, U = 8,192 updates, alphabet loss, reads at answer sites only):

1. Oracle-query retrieval (R1) reached 1.000 at 4,096 slots / 2,048 facts, 0.999–1.000 at 16,384 / 8,192 and 0.967–0.972 at 65,536 / 32,768. Oracle address (R2) reached 1.000 at 16,384 (`results/p9i-run-attempt2-2026-11-15/OUTCOME.md`; `docs/reviews/p9i-results-2026-11-15/REVIEW.md` §1).
2. Every learned query interface collapsed and stayed at chance. Outcome NO_INTERFACE_SELECTED.
3. The dense window control D7 reached 0.78–0.80 at 16,384 and 0.13 at 65,536, and was still improving at U.

Calibration and rehearsal (rehearsal draws; not results):

4. The readout learns by number of updates of the shared output projection and gate, not by exposures per fact (ADR-0017 §I.1).
5. The oracle-query rung needed more updates as the memory grew (0.90 reached at 2,048 / 4,096 / 8,192 updates). In that calibration facts grew with slots, so it does not say whether slots or facts cause the slowdown (`results/p9i-calibration-2026-11-14/README.md`).
6. Under matched updates the three sizes differ sixteenfold in exposures per fact.
7. Cost with six single-thread workers: 0.008–0.012 s per update at 4,096 slots, 0.013–0.015 at 16,384, 0.035–0.049 at 65,536; peak worker memory 1.49 GiB (`results/p9i-rehearsal-2026-11-14/README.md`).

Earlier studies:

8. ADR-0017 Lanes A–D were calibration blocked (§15.2); their classes could be passed or failed by the update budget alone (§5.5, §I.13).
9. P7-A and P7-B found no hierarchy-specific locality; in P8 every locality term cut the slots in use by 46–92% (`docs/RESEARCH_LOG.md`).
10. The backbone is frozen, byte-level, 27,392 parameters, context 64. Facts are synthetic 8-byte records, 5 bits each.

Diagnostic, from the review of revision 1 (a **synthetic stand-in** of the store, no ArborLM backbone, generator or seed; it learns faster than the real system and over-states what a slot holds; `adr-0021-review/REVIEW.md` §0):

11. On the stand-in a flat oracle-query store held 2 facts per slot at ceiling, 4 at 0.99–1.00, and 8 at 0.96 (4,096 slots, still rising at 65,536 updates). No load plateaued below 0.80 within 65,536 updates. What kept loaded cells below ceiling was updates, not storage.
12. On the stand-in the dense control as revision 1 specified it hardly learned (0.16–0.20 where the store was at 1.00); a conventionally initialized dense map with biases reached 0.98–1.00 at 8,192 facts.

Facts 11 and 12 are not results. They are why revision 2 measures load before the freeze (§10.1) and rebuilds the dense control (§5.3).

## 2. Question, scope and hypotheses

**Question.** With addressing controlled, does a larger learned memory retain more useful information about a fixed set of facts, and about a larger set, than a smaller one, under matched budgets and against a dense map of equal parameters; and does it learn the same facts sooner?

**Scope.** Every memory arm is given the identity of the queried fact by an oracle (§3). S1 measures the store, not the interface.

Hypotheses. Each can fail.

- **H21-1 (capacity under load).** For the flat oracle-query memory, at a fixed fact set, a step to four times the slots is a capacity step (§8.2) when the smaller memory is loaded.
- **H21-2 (saturation).** When the smaller memory is not loaded, four times the slots does not change what is retained.
- **H21-3 (knowledge with memory).** Along the proportional track, retained information grows at least 3.0 times per fourfold step under matched updates and under matched compute, with accuracy at least 0.85 at every cell.
- **H21-4 (not parameters alone; restated after review M1).** A dense map with the same parameter count, input and compute does not retain more than the memory (DENSE AHEAD, §8.5).
- **H21-5 (dependence).** The retained information disappears when values are shuffled or addresses are swapped.
- **H21-6 (counted work).** The tree and the flat memory read through a conventional index show capacity steps while their counted work per query at most doubles per fourfold step; the tree retains at least 0.97 of what the indexed flat memory retains.
- **H21-7 (key learning).** The hashed exact-address memory shows the same step pattern as the flat oracle-query memory.
- **H21-8 (learning efficiency).** At fixed facts, a memory with four times the slots reaches 3.0 bits per fact in at most half the updates and at most 0.8 of the compute.

**The lead's expectation, written after seeing facts 11–12 and before any S1 observation.** The capacity line is most likely to print NOT TESTED or INCONCLUSIVE at loads up to 2, and the registered cell 32K/4K (load 8) is the most likely loaded cell. For H21-8 fact 5 suggests the opposite direction (larger memories learn more slowly); Study A separates slots from facts for the first time. Either line may be negative. A negative is recorded and kept.

## 3. Controlled addressing: what it is in each arm

| Arm | Query | Address (which slots are read) | Learned | Role |
|---|---|---|---|---|
| **F-OQ** flat, oracle query (R1 of ADR-0017 §5.3) | fixed random unit code per fact, a seeded hash of the identifier, width 16 | top-8 by cosine against learned keys, temperature 0.2, all keys scored | keys, values, output projection, gate | primary |
| **F-OQ-IVF** (evaluation only) | as F-OQ | the trained F-OQ keys read through a conventional inverted-file index (§5.5) | nothing (F-OQ's snapshot) | conventional sparse retrieval over the learned store |
| **T-OQ** learned tree, oracle query | as F-OQ | learned router picks 2 of N/256 branches of 256 slots; top-8 among their 512 keys | router, keys, values, output projection, gate | hierarchical memory |
| **H8** hashed exact address | none | 8 distinct slots from a seeded hash of the identifier, weights 1/8; slots shared between facts | values, output projection, gate | exact-address reference with sharing |
| **R2** oracle address | none | one dedicated slot per fact; defined only where facts ≤ slots | values, output projection, gate | reference rung |
| **D-OQ** dense, oracle input | the same code as F-OQ | none: code → hidden layer → output | both layers, gate | parameter-matched dense control |

1. In F-OQ and T-OQ the query is controlled and the address is learned. In H8 and R2 both are controlled and only the content is learned.
2. The oracle is not causal and not available to a real system. The frozen backbone exposes about 0.4 bits of the 20-bit identifier at the answer site (ADR-0017 §I.1).
3. **Why a capacity effect under oracle addressing is still informative.** Whether gradient descent through a sparse top-8 read can write more facts into more slots, and how interference grows with facts per slot, are properties of the store and its optimizer. They are a **necessary condition** of ArborLM's storage claim, whatever forms the query.
4. **What it cannot support.** That a learned memory works autonomously; that the language model can address or use this capacity; that learned addressing would reach the same capacity (R1 is a reference, not a ceiling or a floor); useful capability beyond recall of the trained facts; anything about natural language. **Every positive label of S1 carries STORE ONLY; ORACLE-ADDRESSED and may not be printed without it.** This covers the outcome labels and every intermediate or descriptive positive: CAPACITY STEP, CAPACITY_SUPPORTED, CAPACITY-POSITIVE, EFFICIENCY_SUPPORTED, EFFICIENCY-POSITIVE, BEATS DENSE, KNOWLEDGE SCALES WITH MEMORY, TREE_AHEAD and the "storage half supported" reading.
5. D-OQ receives the same code tensor as F-OQ, so the dense comparison is at equal information.
6. D7 (the dense window of P9-I) is not run. It entered no rule. S1 therefore has no learned arm that addresses facts by itself unless lane L runs (§5.6); KNN-W (§5.5) is the non-oracle baseline.

## 4. System common to all arms

- Frozen backbone as P9-I; no backbone parameter is trained. FP32, CPU only.
- Task, identifiers, records, contexts, templates and streams as ADR-0017 §4 (family 1), from the generator of `studies/p9/data.py`, with gate G1. The planted clusters are kept; no S1 rule uses them.
- Reads and additions **at answer sites only**. **Loss: cross-entropy over the 32 alphabet symbols at answer sites.** Scoring: most probable alphabet symbol, ties wrong. One AdamW, learning rate 0.003 (D-OQ's rate by §10.1 item 3), no weight decay, clip 1.0, constant rate. A batch is 16 contexts = 128 answer-site exposures.
- Key width 16, value width 32, top-8, temperature 0.2. No other width is run.
- New code only, in `studies/p10s1/`, importing `studies.p9` and `studies.p9i` unedited. New in S1: H8, the D-OQ of §5.3, the index read of §5.5, work counters, the evaluation of §7. F-OQ and R2 must reproduce the P9-I R1 and R2 forward and one training step bit for bit.

## 5. Design

### 5.1 The grid of facts and slots

Seven cells. "8K/4K" means 8,192 facts in 4,096 slots. Load is facts per slot.

| Facts \ Slots | 4,096 | 16,384 | 65,536 |
|---|---|---|---|
| 2,048 | **2K/4K** (0.5) | — | — |
| 8,192 | **8K/4K** (2) | **8K/16K** (0.5) | **8K/64K** (0.125) |
| 32,768 | **32K/4K** (8) | **32K/16K** (2) | **32K/64K** (0.5) |

- **Study A — fixed knowledge, expanding memory:** the row of 8,192 facts *(lead's choice)*.
- **Study B — expanding knowledge, expanding memory:** the diagonal 2K/4K → 8K/16K → 32K/64K, with the row of 32,768 facts as its off-diagonal cells.
- Every claim about memory size compares cells of one row, so facts and slots are not confounded.
- The load calibration (§10.1 item 0) may add one overload row by a fixed rule. The lead adds no row otherwise.

**Steps (same facts, four times the slots):**

| Step | Cells | Load | Transition |
|---|---|---|---|
| A1 | 8K/4K → 8K/16K | 2 → 0.5 | 4K→16K |
| A2 | 8K/16K → 8K/64K | 0.5 → 0.125 | 16K→64K |
| B1 | 32K/4K → 32K/16K | 8 → 2 | 4K→16K |
| B2 | 32K/16K → 32K/64K | 2 → 0.5 | 16K→64K |

A1 is the off-diagonal test for the lower diagonal step and B2 for the upper one.

### 5.2 What more slots can buy when the facts are fixed (Study A)

1. **Less interference** → the capacity line (§8.2–§8.7).
2. **Faster or slower learning** → the efficiency line (§8.8).
3. **Robustness.** Accuracy retained when a random 5% or 20% of value rows are zeroed, and under Gaussian value noise of 0.1 and 0.5 of the row RMS (three seeded masks each). Descriptive label, §8.6.
4. **Redundancy.** Length of a fact's minimal support; facts per slot (§7.3). Descriptive.

Generalization across facts is not among them (§7.2).

### 5.3 Parameter control

1. **No iso-parameter memory cell is run.** In this read path a slot's contribution is W_o·v_s, a vector of width 32. Value widths above 32 add only redundant parameters; widths below 32 restrict the rank. Neither is "the same parameters in fewer slots". A slot has 48 expressive parameters, and "more slots" cannot be separated from "more store parameters" inside the memory. (Review M1; revision 1's wide-value cells are withdrawn.)
2. **Total trainable parameters are controlled by D-OQ at equal parameter count.** D-OQ: the oracle code (the same tensor as F-OQ's) → `w1 [h, 16]` with bias `b1 [h]` → exact GELU → `w2 [32, h]` → sigmoid(gate) (gate initialized at −2), added at the answer site. Initialization is the conventional one for a fan-in layer: `w1`, `b1` ~ U(−1/4, 1/4), `w2` ~ U(−1/√h, 1/√h), from seeded generators. h is set so that 49h + 1 equals F-OQ's parameter count within 0.1%. Same loss, optimizer, clip and updates. Its learning rate is chosen in calibration (§10.1 item 3).
3. D-OQ is run at 2K/4K, 8K/16K, 8K/64K, 32K/16K and 32K/64K: the larger cell of every step, and every diagonal cell.

### 5.4 Budget regimes and run lengths

Every cell is trained once, at a constant learning rate, and read at snapshots. A snapshot is a valid shorter run (gate G4).

- **U_P = 8,192** updates *(lead's choice of value; the P9-I audited value)*. It is not tuned. §10.1 item 1 checks it; if the check fails the work returns to the human lead. An overload row, if the rule of §10.1 creates one, has its own U_P by that rule.
- **Run lengths U_run:** cells at 4,096 slots run 6·U_P; at 16,384, 4·U_P; at 65,536, 2·U_P; R2 runs U_P *(lead's choice, review B4)*.
- **Snapshots:** U_P × {1/16, 1/8, 1/4, 1/2, 1, 2, 4} up to the run length, U_run/2, U_run, and every matched-compute snapshot.
- **MU — matched updates:** both cells at U_P.
- **ME — matched exposures per fact.** Within a row MU and ME are the same readout. Across rows ME is read at 128·U_P/32,768 exposures per fact: cells with 8,192 facts at U_P/4, with 2,048 facts at U_P/16.
- **MC — matched training compute.** The costlier cell is read at U_P; the cheaper at the smallest snapshot of {1, 1.25, 1.5, 2, 2.5, 3, 4, 6}·U_P whose cumulative cost is at least the costlier cell's. Cost is measured two ways: single-thread process CPU-seconds per update from the isolated timing part of the rehearsal (§10.2), and analytic multiply-adds per update. **The larger of the two multipliers is used**, and both are fixed in the freeze record. If the required snapshot exceeds the cheaper cell's run length the comparison is **MC-SHORT** and counts as not established.
- **SAT — saturation:** the smaller cell at the best of its snapshots up to U_run, with the plateau rule of §8.2.
- The registered run records process CPU-seconds per snapshot. The ratio between two readouts compared under MC is reported; above 1.25 it is flagged **MC-MISMATCH**. It changes no class: the registered run has six workers contending, and a 65,536-slot cell slows more under contention than a small one.

**Which regimes a claim needs, and why.**

1. Every class compares cells of one row. Updates and exposures per fact are then equal by construction.
2. A capacity step needs **MU (= ME), MC and SAT, all three.** MU alone gives the larger memory more compute. MC removes that. SAT removes "the smaller memory is only slower".
3. The efficiency line uses updates and compute only, and never the word capacity.
4. Along the diagonal the three regimes are reported separately. MU and MC are binding; ME is not: at the ME readout the smaller cells have had 4 and 16 times fewer updates of their shared parameters, and fact 4 of §1 says that is what limits them. An ME readout matched to the small cell's exposures would need 16·U_P updates at 65,536 slots and is not run.
5. A difference that appears under MU and not under MC is reported as a training-budget difference, not as memory scaling.

### 5.5 Conventional retrieval and other baselines without training

- **F-OQ-IVF (conventional sparse retrieval over the learned store).** At every evaluated snapshot of F-OQ, the unit-normalized trained keys are clustered by k-means into N/256 centroids (10 Lloyd iterations *(lead's choice)*, seeded k-means++ initialization, seed base + 60). A query scores the centroids, visits lists in order of score until at least 512 candidate keys are collected, takes the top 8 of those by cosine, and reads values exactly as F-OQ does. Counted work K = N/256 + candidates scored, recorded per query. Reported: a_use and i on every panel, recall of the exhaustive top-8, and W. F-OQ-IVF is a separate arm in every step rule; its cells are F-OQ's cells read through the index.
- **DICT (conventional exact retrieval).** A hash table from the identifier bytes to the answer symbol. Exactly 1.0 on trained facts by construction; one probe; 25 bits per fact. On this task it dominates every learned arm, and the cost table says so.
- **KNN-W (exhaustive nearest neighbour over the model's states, no oracle, no learning).** One stored key per fact: the 224-wide vector of the seven frozen states of its record at its first training occurrence, mean stored key subtracted, unit-normalized; the stored value is the answer symbol. Prediction: the stored answer of the nearest key by cosine, exhaustive, ties wrong. Its storage of 224 values per fact and 224·F multiply-adds per query are printed beside it.
- **KNN-W-IVF.** KNN-W read through the same index construction (F/256 centroids, 512 candidates).
- **No-memory baseline** and the **unseen-fact control** (2,048 identifiers never trained).

### 5.6 Optional lane L — learned addressing (separately labelled, descriptive)

1. Lane L exists only if, before S1's freeze, S0 (ADR-0020) has the outcome **ADDRESSING-QUALIFIED (4,096 AND 16,384)**, with Q1 recomputed by the auditor from raw records (ADR-0020 §9.1).
2. The lane prints **OMITTED — QUALIFIED AT 4,096 ONLY**; **OMITTED — NOT OVERLOAD-QUALIFIED** (qualified candidate not OVERLOAD-QUALIFIED); **OMITTED — SUPERVISED ARM HAS NO 8K/4K CELL** (candidate A1 or A2); or **OMITTED — no interface qualified before the freeze** (ADDRESSING-NOT-QUALIFIED, INCONCLUSIVE, ENGINEERING_FAIL, INCOMPLETE, NOT STARTED, or nothing recorded at the freeze).
3. **A qualification recorded after S1's freeze changes nothing in S1** (ADR-0020 §9.2).
4. If it runs: arm F-LA, the candidate exactly as S0 froze it (S0's code hash; P9-II's calibrated value from the arm-selection record; no tuning), at 2K/4K, 8K/4K and 8K/16K, five replicates, each cell run for 4·F updates (8,192 at 2K/4K; 32,768 at 8K/4K and 8K/16K), with F-OQ read at the same update count. S0's cell-success rule is applied at all three cells. No 65,536-slot cell. 15 cells.
5. **Lane L gives no step verdict.** It reports, per cell, the ratio of F-LA's I_use to F-OQ's at the same update count, and the difference in bits per fact between F-LA at 8K/16K and at 8K/4K with the words "not a step verdict". S0's full annotation list is printed with every lane result.
6. Lane L changes no S1 class or outcome. It is considered only after the cuts of §10.3 are settled and is added only if the headroom rule then holds with it; no cut is made to admit it.
7. In the expected timeline (ADR-0020 §9.2) S1 freezes before S0's Q1 is recomputed, so the lane is expected to be omitted; 'learned addressing evaluated separately if qualified' is then met only by a later study that needs the human lead's review.

## 6. Matrix, replicates and seeds

### 6.1 Trained cells

| Arm | Grid cells | Configurations |
|---|---|---|
| F-OQ | all seven | 7 |
| T-OQ | all seven | 7 |
| H8 | all seven | 7 |
| D-OQ | 2K/4K, 8K/16K, 8K/64K, 32K/16K, 32K/64K | 5 |
| R2 | 2K/4K, 8K/16K, 8K/64K, 32K/64K | 4 |
| **Per replicate** | | **30** |
| **Registered total, 5 replicates** | | **150** |
| Seed block (§6.2), draw 1 (unless cut 2 of §10.3 removes it) | F-OQ × 7 cells × 2 extra seeds | +14 |
| Seed block, draw 2 (only if the rehearsal rule admits it) | as above | +14 |
| Lane L (only if qualified and it fits) | F-LA × 3 cells × 5 | +15 |
| Calibration (§10.1) | load 16, U_P check 12, H8 reported 6, dense rate 12 | 46 runs (+4 if the rule of §10.1 adds the 65,536-fact row) |

Evaluation only, no training: F-OQ-IVF, KNN-W, KNN-W-IVF, DICT, no-memory, unseen-fact control. No cell depends on another.

### 6.2 Replicates

- **Five replicates; never reduced.** Replicate r is data draw r with initialization seed 2100 + r. Each draw is a complete independent data set: a fact table of 32,768 facts whose first 8,192 and first 2,048 are the smaller sets, a training stream per fact count, Panels A and B, held-out template panels H1 and H2, the unseen-fact control.
- **Pairing.** Within a replicate and row, every slot count and arm sees the same facts and the same training contexts in the same order. Only the output projection and the gate share an initialization across slot counts; key and value tables are drawn per size.
- **Seed block (descriptive, enters no rule).** On draw 1, F-OQ is also trained at initialization seeds 2111 and 2121 on all seven cells, unless cut 2 of §10.3 removes the block. If the rehearsal shows that the cap holds with twofold headroom with it, the same is done on draw 2 at seeds 2112 and 2122; the decision is made by that rule and recorded before the freeze. The report gives, per cell and readout, the spread of i over the three seeds of a draw against the spread over the five draws, and states which dominates.
- **Statistical meaning.** If a paired condition held with probability at most 1/2 in each replicate, "all five" has probability at most 1/32 = 0.031 and "at least 4 of 5" at most 6/32 = 0.19. "All five" is required for every positive step. 'At least 4 of 5' is used for negatives, ceilings and DENSE AHEAD. Every positive condition of a capacity or efficiency verdict, class or outcome, BEATS DENSE included, needs all 5. The hierarchy labels of §8.5 are descriptive and use at least 4 of 5.
- **At the level of the outcome** the bound is weaker. Three arms can each reach CAPACITY_SUPPORTED through A1 or B1 in the first transition, so by the union bound the chance of some positive step class under that null is at most 6/32 = 0.19 (crude: the arms share data and a second transition is also required). Replicates protect against noise, not against systematic confounds.
- Sampling error within a cell is small beside the thresholds: with 8,192 facts the standard error of an accuracy is at most 0.006, about 0.03 bits per fact.
- One backbone (B101/O301).

### 6.3 Seeds and partitions

- Registered data seed sets `p10s1-draw-1` … `p10s1-draw-5`, bases 210001, 210101, 210201, 210301, 210401; each set uses base + i as the P9 generator does (14 names; null seeds at +20 and +30). H8 hash seed base + 40. Derangement and mask seeds base + 50 … 59. Index seed base + 60. Initialization seeds 2101–2105; seed block 2111, 2121, 2112, 2122.
- Calibration draws: bases 219001 and 219101, initialization seed 2191. Rehearsal draw: base 219201, initialization seed 2192. Unit tests: **921001–921999**.
- **Gate G9** asserts that S1's declared seeds and the seeds the generators derive from them (initialization seed + 1000·k, as `_matrix` uses) are disjoint from each other and from: P9 (170001–171343, 179001–179933, 1701–1702); P9-I (182001–182020, 180101–181900, 1791–1792, 1801–1802, 900001–900233); the review diagnostics (500001–500004) and the review stand-in (941001); P9-II (190001–191599, 1891–1892, 1901–1902, tests 910001–919999); S0 (200001–209999, 2001–2002, 2091–2092, tests 920001–920999); S2 (220001–228999, tests 229001–229999); the seeds of P1–P8 read from their configs. The review's scan found no use of S1's ranges in the worktree or in `experiments/` (`adr-0021-review/outputs/s9c_seed_keys.txt`).
- Within a draw: training contexts, Panel A, Panel B, H1 and H2 are disjoint (verified by hash); H1 and H2 use byte sets never used in training; no fact's record precedes its own answer site. No registered panel is used in calibration or rehearsal.

## 7. Measurements

### 7.1 Useful retained information (primary)

For a cell, snapshot and panel:

- A fact is **usefully retained** if (1) the model with its memory gives the fact's answer, and (2) when the fact's read is replaced by the read of another fact π(f) it no longer gives that answer. π is a seeded derangement of the cell's facts with a different answer symbol. For D-OQ the input code is swapped the same way.
- **a_use** is the share of usefully retained facts. **i = 5 − h₂(e) − e·log₂31** bits per fact, e = 1 − a_use (1.523 at 0.5, 3.287 at 0.8, 4.036 at 0.9, 4.466 at 0.95). i is 0 when the count is at or below the upper end of the chance interval (G2). **I_use = F·i**.
- **i\*(cell; U)** is the maximum of i over the cell's snapshots at or below U.
- Every rule uses i, i\* or I_use. Raw accuracy, the Σ-renormalized log-loss gain and the 256-way loss are descriptive.
- Slot counts, distinct selected slots and entropy of use enter no rule.

### 7.2 Held-out queries and what generalization means here

1. The answers are independent random symbols. Accuracy on **unseen facts must be at chance**; it is a leakage control (flag LEAKAGE).
2. **Generalization means the same fact asked in a context never trained on.** Primary panels A and B: training templates, new co-records, positions and order. H1 and H2: separator and binding bytes never seen in training.
3. Under oracle addressing the query does not depend on the context. H1 and H2 therefore test the **shared readout through the frozen upper block**, not the memory and not the address. A failure there is not a dependence failure.
4. **HELD-OUT FRAGILE** (annotation, enters no class): the arm's ratio of H1 (or H2) accuracy to Panel A accuracy is below 0.90 × the same ratio for R2 of the same replicate at the row's reference cell *(lead's choice)*.

### 7.3 Memory dependence, utilization, separability, movement

- **Ablations, every memory cell, at every snapshot used by a rule:** memory disabled; value shuffle (a seeded derangement of value rows over slots); address swap (§7.1). Slot dropout and value noise at U_P.
- **Minimal support** (ADR-0017 §6.2 restricted to the answer-site read), at U_P on a seeded sample of 2,048 facts per cell on Panel A *(lead's choice)*: mean length; U*.
- **Utilization:** distinct selected slots; U* over the sample; facts per slot; dead slots.
- **Separability:** nearest-neighbour cosine between oracle codes; share of facts with a neighbour above 0.8; overlap of the top-8 sets of a fact and its nearest neighbour; share of facts with a private slot. For T-OQ and F-OQ-IVF: share of the exhaustive top-8 found among the candidates.
- **Row movement.** Per cell, the cumulative movement of value rows on updates with and without their own gradient. **Every GAIN WITHIN BUDGET, BEHIND WITHIN BUDGET, FASTER and SLOWER verdict is printed with the ratio of that movement between the two cells.** No class depends on it. Under AdamW a row that rarely receives a gradient still moves, and rows receive gradients less often in a larger memory (ADR-0017 §5.5). SAT is the control for the capacity line; it is not a control for the efficiency line, which is why the ratio is printed there. No row-lazy arm is run.

### 7.4 Active memory work per query

Counted by instrumented counters in the forward. Gate G7 requires the counters to equal the formulas.

| Arm | Key scores K (each 16 wide) | Value rows V | W = 16·K + 32·V + 1,024 (output projection) |
|---|---|---|---|
| F-OQ | N | 8 | 66,816 / 263,424 / 1,049,856 |
| F-OQ-IVF | N/256 + candidates (at least 512) | 8 | measured per query; about the T-OQ figure |
| T-OQ | N/256 + 512 | 8 | 9,728 / 10,496 / 13,568 |
| H8 | 0 | 8 | 1,280 |
| R2 | 0 | 1 | 1,056 |
| D-OQ | h ≈ N | h | 48·h, plus h bias additions |
| KNN-W | F keys, 224 wide | 1 | 224·F |

1. These are logical counts. **They are not measured efficiency, latency or I/O.** Top-k comparisons are counted separately and reported.
2. **SUBLINEAR** means W at most doubles across a fourfold step in slots *(lead's choice)*. It is a property of the read path, not a finding: any tree, hashed table or indexed flat memory has it. F-OQ is printed **LINEAR KEY SCORING**.
3. No reduction of counted or simulated traffic is reported without the working set beside it, and none is called locality (P7-B, P8).
4. **F-OQ-IVF's W is measured, not analytic.** SUBLINEAR for F-OQ-IVF is judged on the mean measured W per query on Panel A at both cells of the step, in every replicate; its 99th percentile is printed beside it.

### 7.5 Throughput and estimated storage traffic

- **Throughput (measured, RAM only).** A separate timing stage after all training and evaluation, one process, nothing else of the project running. Refused if the load average exceeds 1.0 at start; retried until quiet up to 3 times within the cap; if never quiet, **THROUGHPUT NOT MEASURED**, which does not make S1 incomplete. Read-path queries per second at batch 1 and 128 for F-OQ, F-OQ-IVF, T-OQ, H8 and D-OQ at each slot count, replicate-1 snapshots, five repeats. Stable only if the coefficient of variation is at most 5%; otherwise UNSTABLE.
- **Estimated storage traffic (arithmetic and simulation, no device).** The estimate assumes keys in RAM and values on storage. Value bytes read per query. Distinct pages touched per query at 8 and 32 rows per page under the identity layout. Page misses from `studies/p9/sim.py` at one setting with three count-preserving nulls, the ratio to the null, and the working set; a null miss rate below 0.05 is DEGENERATE. Key bytes scored per query if keys were on storage is printed as an identity from §7.4, not an estimate.
- **Actual SSD inference and latency claims require physical measurements in a later experiment.**

### 7.6 Cost table and manifests

- Per cell, every arm and baseline: I_use; trainable and stored parameters and bytes; retained bits per stored byte; K, V, W; updates, exposures per fact, CPU-seconds and multiply-adds to each readout; throughput; estimated traffic.
- **Every run manifest records** operating system, hardware, Python and torch versions, thread settings, code, spec, config and data identities, and the model that ran each delegated task.

## 8. Gates, rules and classes

After the calibration outputs are written, only these may change before the freeze: the rows by the rule of §10.1 item 0; D-OQ's learning rate; the MC snapshots from the timing rule; the seed block on draw 2; the cuts of §10.3; lane L by §5.6. Anything else is a new revision.

### 8.1 Gates

**Engineering gates (a failure is S1-ENGINEERING-FAILURE):**

- **G1** generator checks per draw and fact count (ADR-0017 §4.6).
- **G2** chance: the no-memory baseline on the three fact sets and the unseen set, both panels, five draws: 40 tests, each inside the exact binomial central interval of level 1 − 0.001/40 around 1/32 ([34, 100], [192, 325], [894, 1,159]). That interval is "chance" in every rule.
- **G4** determinism and identity: stream hashes; checkpoint restoration bit for bit for one cell of every arm at real size; train-restore-continue equals the straight run; F-OQ and R2 identical to P9-I's R1 and R2; logits on the backbone's corpus rows identical to the frozen backbone's; the index of §5.5 is identical on rebuild.
- **G5** gradient reach, **for every one of the 30 configurations at its real facts and slots, on a batch of that cell's own training stream:** every trainable group receives a non-zero gradient; in H8 exactly the hashed rows do; R2's table covers every fact of the cell; nothing reaches the backbone.
- **G6** controlled-addressing integrity: query and selection of F-OQ, T-OQ, H8 and R2 are unchanged when the context is permuted and when the answer table is replaced; D-OQ's input tensor has the same hash as F-OQ's codes; no forward takes the answer as input.
- **G7** work counters equal §7.4. **G8** D-OQ's parameter count within 0.1% of F-OQ's. **G9** seeds (§6.3).
- **The gates stage runs at real size on the rehearsal draw before the freeze** and again on registered seeds before training. A harness error is reported separately from a gate failure.

**Scientific gates (a failure is a recorded result):**

- **REF**, per replicate and row: R2 a_use ≥ 0.95 on both panels at U_P, at 8K/16K for the row of 8,192 facts, at 32K/64K for the row of 32,768, and at 2K/4K for the diagonal. If it fails, the replicate is NOT_EVALUATED for the row. R2 at 8K/64K enters no rule.
- **DEP**, per memory cell with a_use ≥ 0.25, **at every snapshot a rule reads**: memory disabled gives chance; value shuffle gives chance; a_use ≥ 0.95 × raw accuracy; unseen facts at chance (else LEAKAGE). H1 and H2 are not part of DEP (§7.2).

### 8.2 Capacity line: step verdict in one replicate

For an arm and a step N → 4N at fixed facts, on Panels A and B separately.

- Δ_MU = i(4N; U_P) − i(N; U_P). Δ_MC = i(4N; U_P) − i(N; U_MC).
- **Δ_SAT = i(4N; U_P) − i\*(N; U_run).**
- **Plateaued:** i\*(c; U_run) − i\*(c; U_run/2) ≤ 0.10 bits per fact *(lead's choice)*, for either cell on its own snapshots.
- **Loaded** (a smaller cell): plateaued and i\*(N; U_run) ≤ 4.0 bits per fact (a_use ≤ about 0.896) *(lead's choice)*. This one threshold is used for CAPACITY (row 4), NULL (row 8), FLAT, NOT LOADED (row 9) and the load calibration (§10.1 item 0).
- Δ_FULL = i\*(4N; U_run(4N)) − i\*(N; U_run(N)).

If the panels give different verdicts the verdict is PANEL-DISAGREE. First match wins.

| Order | Verdict | Rule |
|---|---|---|
| 1 | NOT_EVALUATED | REF fails for the row, or LEAKAGE in either cell |
| 2 | DEPENDENCE_FAILED | either cell fails DEP at a snapshot this verdict reads |
| 3 | CEILING | i(N; U_P) ≥ 4.5 (a_use about 0.954) |
| 4 | CAPACITY | Δ_MU ≥ 0.5; Δ_MC ≥ 0.5; Δ_SAT ≥ 0.5; **the smaller cell is loaded**; Δ_SAT − 2·[i\*(N; U_run) − i\*(N; U_run/2)] ≥ 0.5; a_use(4N; U_P) ≥ 0.5 |
| 5 | GAIN WITHIN BUDGET ONLY | Δ_MU ≥ 0.5, not row 4 |
| 6 | REVERSED | Δ_MU ≤ −0.5 and Δ_FULL ≤ −0.5 |
| 7 | BEHIND WITHIN BUDGET | Δ_MU ≤ −0.5, not row 6 |
| 8 | NULL | \|Δ_MU\| < 0.25 and \|Δ_FULL\| < 0.25; both cells plateaued; the smaller cell is loaded |
| 9 | FLAT, NOT LOADED | as row 8 except that the smaller cell is not loaded |
| 10 | UNRESOLVED | otherwise |

- Rows 5 and 7 are the review's EFFICIENCY and SLOWER, renamed so that they are not confused with the efficiency line of §8.8. They enter no negative and no positive.
- 0.5 bits per fact *(lead's choice)* is 5.7 to 12 points of accuracy between 0.3 and 0.9. The fifth condition of row 4 means the gap survives two further doublings at the smaller cell's last rate.
- "Capacity" means within the registered run lengths. A loaded smaller cell at 4.0 bits with the largest plateau slope needs the larger cell at 4.70 bits or more (a_use 0.974) for CAPACITY; the rule is reachable (`adr-0021-review/outputs/k1_confirm_arithmetic.txt`).

### 8.3 Capacity line: step class over the five replicates (first match wins)

| Order | Step class | Rule |
|---|---|---|
| 1 | NOT_EVALUATED | at least 2 replicates NOT_EVALUATED |
| 2 | DEPENDENCE_FAILED | at least 2 replicates DEPENDENCE_FAILED |
| 3 | NOT REPLICATED | at least 2 replicates PANEL-DISAGREE |
| 4 | CAPACITY STEP | CAPACITY in all 5 |
| 5 | GAIN WITHIN BUDGET | CAPACITY or GAIN WITHIN BUDGET ONLY in all 5 |
| 6 | NOT LOADED | CEILING or FLAT, NOT LOADED in at least 4 |
| 7 | REVERSED | REVERSED in at least 4 |
| 8 | NO GAIN | NULL or REVERSED in at least 4 |
| 9 | MIXED | otherwise |

The denominator is always 5.

### 8.4 Capacity line: arm class (F-OQ, F-OQ-IVF, T-OQ, H8; steps A1, A2, B1, B2, or the rows the rule of §10.1 fixes; first match wins)

| Order | Arm class | Rule |
|---|---|---|
| 1 | NOT_EVALUATED | every step of one transition is NOT_EVALUATED |
| 2 | DEPENDENCE_FAILED | any step is DEPENDENCE_FAILED |
| 3 | CAPACITY_SUPPORTED | a CAPACITY STEP in each transition; no step REVERSED; a_use ≥ 0.80 at 32K/64K at U_P in all 5 replicates *(lead's choice)* |
| 4 | CAPACITY_ONE_TRANSITION | at least one CAPACITY STEP, not row 3 |
| 5 | NOT_TESTED_BY_LOAD | in some transition every step is NOT LOADED |
| 6 | CAPACITY_NOT_SUPPORTED | at least one step per transition is NO GAIN or REVERSED, and no step is a CAPACITY STEP |
| 7 | INTERMEDIATE | otherwise |

H8's classes carry **UNDERTRAINED-AT-U_P** at any cell where its calibration accuracy was below 0.90 at U_P.

### 8.5 Control and cost labels

**Dense, at the larger cell of each CAPACITY STEP of the arm.** d = i(arm) − i(D-OQ) and r = I_use(arm) / I_use(D-OQ), per panel and replicate, in three readings: **MU** (both at U_P); **MC** (the cheaper of the two at its matched-cost snapshot); **D-BEST** (the arm at U_P against D-OQ at the best of its snapshots up to its U_run). First match wins:

| Order | Label | Rule |
|---|---|---|
| 1 | **DENSE AHEAD** | d ≤ −0.25 *(lead's choice)* in at least 4 replicates, in any one reading (MU, MC, D-BEST), at any such cell. Takes precedence over every other label |
| 2 | **BEATS DENSE** | r ≥ 1.10 in **all 5** replicates, under MU and under MC, on both panels, at every such cell (ADR-0017's standard). r with a zero denominator counts as ≥ 1.10 and the label is then printed **BEATS DENSE (DENSE AT CHANCE AT cell)** |
| 3 | **DENSE MATCHES** | otherwise; printed as "a dense map with the same parameters, input and compute retained as much; the memory did it with W_arm / W_dense of the counted work" |

Every dense label is printed with D-OQ's a_use at each such cell in each reading.

- **DENSE AHEAD blocks every arm.** Counted work never offsets a dense lead. DOMINATED BY DENSE is withdrawn.
- BEATS DENSE cannot be reached where the dense control's i exceeds 4.545 bits (a_use above about 0.958).
- A CAPACITY STEP whose larger cell has no D-OQ cell (only after cut 3 of §10.3) is printed DENSE NOT READ and cannot by itself support CAPACITY_SUPPORTED.

**Active work, per CAPACITY STEP:** SUBLINEAR (analytic; measured for F-OQ-IVF, §7.4 rule 4) or LINEAR KEY SCORING (§7.4).

**Hierarchy:** T-OQ against **F-OQ-IVF** at equal candidate count, on I_use at 8K/16K and 32K/64K at U_P. TREE_AHEAD if the ratio is ≥ 1.03 in at least 4 replicates at both cells; TREE_COMPETITIVE if ≥ 0.97 in at least 4 replicates at both cells; otherwise TREE_BEHIND. T-OQ against exhaustive F-OQ is printed beside it.

**Conventional retrieval:** CONVENTIONAL RETRIEVAL SUFFICES if KNN-W's or KNN-W-IVF's i is within 0.25 of the arm's, or above it, on both panels in at least 4 replicates at 32K/64K (each evaluated and printed). DICT DOMINATES ON THIS TASK is always printed.

**Key learning:** KEY-LEARNING-LIMITED if H8 is CAPACITY_SUPPORTED and F-OQ is not.

### 8.6 Descriptive labels (enter no class)

- **STUDY B (knowledge with memory), per arm among F-OQ, F-OQ-IVF, T-OQ.** **KNOWLEDGE SCALES WITH MEMORY** if, in all 5 replicates and on both panels, under MU and under MC separately: a_use ≥ 0.85 *(lead's choice)* at every diagonal cell; I_use grows ≥ 3.0 times at both diagonal steps; both diagonal steps are MEMORY-ATTRIBUTED; and the arm's counted work is SUBLINEAR. **KNOWLEDGE DOES NOT SCALE** if a_use < 0.5 at the largest diagonal cell in at least 4 replicates. **NOT ESTABLISHED** otherwise. A ratio is computed only when both cells have a_use ≥ 0.5; otherwise NOT ASSESSED. A diagonal step is **MEMORY-ATTRIBUTED** only if its off-diagonal step (A1 for the lower, B2 for the upper) is a CAPACITY STEP. The ME line is printed with the sentence of §5.4 rule 4. This line is printed beside the outcome.
- **Robustness,** per step, cells with a_use ≥ 0.5: RISES WITH SLOTS if accuracy retained under 20% slot dropout rises by ≥ 0.05 in all 5; FALLS if it drops by ≥ 0.05 in at least 4; otherwise UNCHANGED.
- **HELD-OUT FRAGILE** (§7.2).
- **Seed block** (§6.2).

### 8.7 Capacity outcome (first match wins)

| Order | Outcome | Rule |
|---|---|---|
| 1 | **S1-ENGINEERING-FAILURE** | any engineering gate fails, or frozen and running code, config, launch scripts or data identities differ. No scientific label on either line. |
| 2 | **S1-INCOMPLETE** (status) | any registered cell lacks a record. No outcome on either line; the denominator is never reduced. |
| 3 | **CAPACITY-POSITIVE** | F-OQ, T-OQ or F-OQ-IVF is CAPACITY_SUPPORTED and is not DENSE AHEAD |
| 4 | **CAPACITY-NEGATIVE** | (a) F-OQ and T-OQ are both CAPACITY_NOT_SUPPORTED; or (b) at least one of F-OQ, T-OQ, F-OQ-IVF is CAPACITY_SUPPORTED, and every arm among them that is CAPACITY_SUPPORTED is DENSE AHEAD. An empty set never satisfies (b). |
| 5 | **CAPACITY NOT TESTED — NO LOADED CELL WITHIN BUDGET** | for F-OQ and for T-OQ, every step is NOT LOADED; or the human lead directed, after the load calibration, that the study run with no loaded row (§10.1 item 0), in which case the label is fixed in the freeze record |
| 6 | **CAPACITY-INCONCLUSIVE** | otherwise; the reason is printed: NOT_EVALUATED, DEPENDENCE_FAILED, NOT_TESTED_BY_LOAD (which transition), ONE TRANSITION ONLY (which), INTERMEDIATE |

- **Printed label:** CAPACITY-POSITIVE [STORE ONLY; ORACLE-ADDRESSED; WITHIN REGISTERED RUN LENGTHS; arm(s); BEATS DENSE or DENSE MATCHES, with D-OQ's a_use; active-work label; hierarchy label; conventional-retrieval label; S0 status (K7(c)); learned-address lane status].
- H8 alone cannot give CAPACITY-POSITIVE: the label requires learned keys *(lead's choice)*. Its class is printed beside the outcome.
- Row 5 is not a negative and not a positive. It says the registered sizes and run lengths could not load the store.
- **Reading for milestone question 1, fixed now.** S1 tests the storage half of question 1 under oracle addressing, on the capacity line only.
  - **"Storage half supported, as a necessary condition"** only if the capacity outcome is CAPACITY-POSITIVE for an arm whose counted work is SUBLINEAR (T-OQ, or F-OQ-IVF by §7.4 rule 4), that arm is not DENSE AHEAD, and the hierarchy label comparing T-OQ with F-OQ-IVF (§8.5) is printed with it. It means: given the identity of the fact, this store retained more trained random facts as it grew, within the registered run lengths, at bounded counted work, with no dense lead of 0.25 bits per fact or more in 4 of 5 replicates over a dense map of equal size, input and compute (BEATS DENSE or DENSE MATCHES, printed). It says nothing about addressing by the model, about use of the store by a language model, or about useful capability beyond recall of the trained facts.
  - **"Capacity shown; sublinear active work not shown"** if CAPACITY-POSITIVE holds only for exhaustive F-OQ.
  - **"Storage half not supported for this store, backbone, task and budget"** if CAPACITY-NEGATIVE.
  - **"Not tested"** or **"not established"** for CAPACITY NOT TESTED or CAPACITY-INCONCLUSIVE.
  - Every reading is printed with S0's status line of K7(c).
- **Independence.** Neither line uses, implies or depends on TRANSFER-POSITIVE or SYSTEM-POSITIVE. S1's contribution to SYSTEM-POSITIVE is descriptive input only: both outcomes with their annotations, the Study B line, the cost table, and the sentence "addressing was supplied by an oracle".

### 8.8 Efficiency line

**Level.** i_T = 3.0 bits per fact (a_use about 0.758) *(lead's choice)*. At each snapshot s of a cell, the snapshot **qualifies** if i ≥ i_T on both panels and DEP passes. s_hit is the first qualifying snapshot within the cell's run, s_prev the snapshot before it. **u_T** is found by linear interpolation of the minimum of the two panels' i against log₂(updates) between s_prev and s_hit; if s_hit is the first snapshot, u_T is **left-censored** in (0, s_hit]; if no snapshot qualifies, u_T is **right-censored** above the cell's run length U_run. c_T is u_T times the cell's cost per update, in each of the two cost measures of §5.4 (bounds carry over).

**Step verdict in one replicate (first match wins).** A condition on a censored value holds only if it holds for every value the bound allows.

| Order | Verdict | Rule |
|---|---|---|
| 1 | NOT_EVALUATED | REF fails for the row, or LEAKAGE |
| 2 | DEPENDENCE_FAILED | in either cell, some snapshot has i ≥ i_T on both panels with DEP failing, and no earlier snapshot qualifies |
| 3 | NOT_ASSESSED | both cells right-censored; or at least one u_T is censored and no condition of rows 4–7 holds for every value the bounds allow |
| 4 | REACHED ONLY BY THE LARGER | the smaller cell is right-censored, and u_T(4N) ≤ U_run(N)/2 and c_T(4N) ≤ 0.8 · cost(N; U_run(N)) in both cost measures |
| 5 | FASTER | u_T(4N) ≤ u_T(N)/2, and c_T(4N) ≤ 0.8 · c_T(N) in both cost measures *(lead's choice)* |
| 6 | FASTER IN UPDATES ONLY | u_T(4N) ≤ u_T(N)/2, not row 5 |
| 7 | SLOWER | u_T(4N) ≥ 2 · u_T(N) (with the larger cell right-censored, only if U_run(4N) ≥ 2 · u_T(N)) |
| 8 | SAME | otherwise; both u_T known (neither left- nor right-censored) |

Every verdict is printed with the row-movement ratio of §7.3 and, where the larger cell's share of value-row movement on updates without gradient exceeds the smaller cell's by more than 1.5 times *(lead's choice)*, the annotation **OPTIMIZER-ASSISTED**. No class depends on either.

**Step class:** NOT_EVALUATED (at least 2); DEPENDENCE_FAILED (at least 2); NOT_ASSESSED (at least 2); FASTER STEP (FASTER or REACHED ONLY BY THE LARGER in all 5; the number of each is printed); UPDATES-ONLY STEP (FASTER or FASTER IN UPDATES ONLY in all 5); SLOWER STEP (SLOWER in at least 4); NO DIFFERENCE (SAME in at least 4); MIXED otherwise. First match wins in that order.

**Arm class (F-OQ, T-OQ; first match wins):** NOT_EVALUATED (every step of one transition NOT_EVALUATED or NOT_ASSESSED); DEPENDENCE_FAILED (any step); EFFICIENCY_SUPPORTED (a FASTER STEP in each transition, no SLOWER STEP); EFFICIENCY_ONE_TRANSITION (at least one FASTER STEP); EFFICIENCY_NOT_SUPPORTED (at least one step per transition is SLOWER STEP or NO DIFFERENCE, and no FASTER STEP); INTERMEDIATE.

**Dense label for this line,** at the larger cell of each FASTER STEP: **DENSE FASTER** if D-OQ's c_T is at most 0.8 of the arm's, in both cost measures, in at least 4 replicates; otherwise DENSE NOT FASTER. DENSE FASTER blocks the positive *(lead's choice; not covered by a ruling, see §19)*.

**Efficiency outcome (first match wins; rows 1–2 of §8.7 apply first):**

| Order | Outcome | Rule |
|---|---|---|
| 3 | **EFFICIENCY-POSITIVE** | F-OQ or T-OQ is EFFICIENCY_SUPPORTED and is not DENSE FASTER. Printed as EFFICIENCY-POSITIVE [STORE ONLY; ORACLE-ADDRESSED; arm(s); row-movement ratios; dense label; S0 status (K7(c))] |
| 4 | **EFFICIENCY-NEGATIVE** | F-OQ and T-OQ are both EFFICIENCY_NOT_SUPPORTED; or at least one is EFFICIENCY_SUPPORTED and every such arm is DENSE FASTER. An empty set never satisfies the second clause. |
| 5 | **EFFICIENCY-INCONCLUSIVE** | otherwise, with the reason |

EFFICIENCY-POSITIVE says that a larger store reached a fixed level of useful information in fewer updates and less compute; where the smaller store never reached it within its run, the label says so (REACHED ONLY BY THE LARGER), and that is not a capacity statement. It does not enter the milestone reading.

### 8.9 Decision map (recommendations only; nothing is authorized)

1. CAPACITY-POSITIVE with a SUBLINEAR arm → propose a study of the same store with a qualified learned interface, and separately a physical storage measurement.
2. CAPACITY-POSITIVE with F-OQ only → the index or the tree is the next question.
3. KEY-LEARNING-LIMITED → study key learning under load.
4. CAPACITY-NEGATIVE by NO GAIN → the store keeps several facts per slot at these counts; larger fact sets or another task are needed.
5. CAPACITY-NEGATIVE by DENSE AHEAD → the dense map is the better use of these parameters on this task.
6. CAPACITY NOT TESTED → return to the human lead with the cost of the smallest loaded row.
7. EFFICIENCY-NEGATIVE with SLOWER steps → larger memories cost more updates at equal facts; any scaling plan must budget for it.
8. Inconclusive on either line → no decision on that line.

## 9. How S1 avoids the earlier traps

| Trap | Source | What S1 does |
|---|---|---|
| Learned interface collapses | P9-I | no class depends on a learned interface |
| Oracle rung needs more updates as memory grows (seen only where facts grew with slots) | calibration | Study A fixes the facts; the efficiency line measures it; SAT and the plateau rule keep it out of the capacity line |
| Readout learns by updates of shared parameters | ADR-0017 §I.1 | cells compared in a class have equal updates; ME is not binding across rows |
| Sixteenfold exposure difference | P9-I | arises only on the diagonal, which enters no class |
| Calibration blocked | ADR-0017 §15.2 | U_P is fixed, not tuned; the load is measured before the freeze and mapped to rows by a fixed rule; anything outside the rule returns to the human lead |
| Task validity unmeasured before the single run | ADR-0017 review B3; review B4 here | the load calibration |
| Classes passed or failed by budget | ADR-0017 Lane A | a capacity step needs MU, MC and SAT; a negative needs both cells plateaued, a loaded smaller cell, and the difference at the full run lengths; a slower larger memory gives BEHIND WITHIN BUDGET, never NO GAIN |
| A control that cannot learn | review B3 | D-OQ rebuilt and its rate chosen in calibration; DENSE AHEAD read in three readings |
| Slots selected mistaken for capacity | P8 | a_use needs per-fact dependence |
| Working set shrinks, misses fall | P7-B, P8 | counted work is analytic and gated; simulated traffic carries nulls and the working set |
| Hierarchy credited with a property of any index | P7-B; review M4 | the tree is compared with the flat store read through a standard index |
| Gate harness first run at registration; mistyped launch commands | P9-I attempts 1 and 2 | gates at real size on the rehearsal draw for all 30 configurations; fixed launch scripts for every registered stage, part of the freeze |
| One data draw | ADR-0017 §0 item 12 | five draws, never reduced; a seed block |

## 10. Calibration, rehearsal, resources

### 10.1 Calibration (two calibration draws, one initialization seed, before the freeze)

**0. Load calibration.** F-OQ only, on both calibration draws, at 4,096 slots with 8,192 / 16,384 / 32,768 / 65,536 facts (loads 2, 4, 8, 16), and at 16,384 slots with 8,192 / 32,768 / 65,536 / 131,072 facts (loads 0.5, 2, 4, 8; load 0.5 is the registered cell 8K/16K and is measured only so that cut 3 of §10.3 has a defined input), run to 65,536 updates with snapshots on the doubling grid and at the registered U_run/2 and U_run of the slot count (24,576 and 49,152 at 4,096 slots; 16,384 and 32,768 at 16,384 slots). 16 runs, about 3.5 CPU-hours. A load is **loaded at a slot count** if, on both draws and both calibration panels, the cell is loaded by the definition of §8.2 **read at the registered U_run of that slot count** (not at 65,536 updates). The 65,536-update snapshots are reported for information and enter no rule. A load is judged on its own cell; loadedness is not assumed to carry from one load to another.

**Rule fixed now** (registered smaller cells: 8K/4K and 32K/4K at 4,096 slots; 8K/16K and 32K/16K at 16,384 slots):

| Measured | Consequence |
|---|---|
| At 4,096 slots, load 2 or load 8 is loaded | the 4K→16K transition is tested by the registered rows; no change |
| At 4,096 slots, neither load 2 nor load 8 is loaded | no registered 4,096-slot cell is predicted loaded: the work returns to the human lead before the freeze |
| At 16,384 slots, load 2 is loaded | the row of 32,768 facts tests the 16K→64K transition; the grid of §5.1 stands |
| At 16,384 slots, load 2 is not loaded and load 4 is loaded | the row that tests the 16K→64K transition becomes 65,536 facts at 16,384 and 65,536 slots, for F-OQ, T-OQ, H8 and R2 at both cells and D-OQ at its larger cell only, as in every other row (R2 at 65,536 slots, one fact per slot, is its REF cell). The 65,536-fact table of a draw contains that draw's 32,768-fact table as its first 32,768 facts *(lead's choice)*; its seeds are inside 210001–219999. Load 4 was judged at 32,768 updates while this row's smaller cell runs 4·U_P; that is a prediction only, and the run judges the cell on its own snapshots. Its U_P is the smallest of {8,192, 16,384, 32,768} *(lead's choice)* at which F-OQ ≥ 0.90 and R2 ≥ 0.95 at its larger cell on both draws and panels, read in a calibration of that cell (2 arms × 2 draws, added to the calibration count); its run lengths are 4·U_P and 2·U_P of that U_P. If none of the three values qualifies, the work returns to the human lead before the freeze. The row of 32,768 facts keeps its cells and only its 4K→16K step. If the headroom rule of §10.3 does not hold with this row after the allowed cuts, the work returns to the human lead with the row's cost |
| At 16,384 slots, only load 8 is loaded, or none | the 16K→64K transition cannot be loaded with an R2 reference within the budget (131,072 facts exceed 65,536 slots): the work returns to the human lead before the freeze. The lead never runs a row without R2 |

The lead does not improvise a row. When the work returns, the human lead may stop, fund a row, or direct that S1 run as it is, with the capacity line fixed in the freeze record as CAPACITY NOT TESTED — NO LOADED CELL WITHIN BUDGET for the transition concerned; the efficiency line is unaffected. A prediction of loadedness from calibration does not make a registered cell loaded: the run judges every cell on its own snapshots.

**1. U_P check.** R2 and F-OQ on the three diagonal cells to U_P = 8,192, 12 runs. U_P stands if R2 ≥ 0.95 and F-OQ ≥ 0.90 at every diagonal cell on both draws and both panels. If not, the work stops and returns to the human lead; no larger U_P is substituted by rule.

**2. H8, reported only.** H8 on the diagonal cells to U_P, 6 runs. If H8 is below 0.90 at a cell, its classes there carry UNDERTRAINED-AT-U_P. H8 gates nothing.

**3. Dense learning rate.** D-OQ at 8K/16K and at 32K/64K, at learning rates {0.001, 0.003, 0.01} *(lead's choice)*, on both draws, to the run length of its slot count. 12 runs. The rate with the higher minimum Panel A accuracy at U_P is chosen separately for 16,384 and 65,536 slots (the 16,384 choice is also used at 4,096); a difference below 0.02 goes to the faster of the two. The memory arms keep 0.003 untuned.

**4.** No T-OQ cell and no registered step is run in calibration. Calibration accuracies are never results. The calibration is audited before the freeze.

### 10.2 Rehearsal (rehearsal draw; time, memory and correctness only)

- All 30 configurations, and any row added by §10.1, at real size for 64 updates and one full evaluation each, including the index build, six single-thread workers, through the whitelist validator of P9-I (no loss or accuracy is written or displayed).
- The gates stage at real size.
- **Isolated timing part,** one process: CPU-seconds per update for every arm and slot count, including the new D-OQ (median of three runs of 256 updates after 32 warm-up updates).
- Analysis and report exercised on **synthetic records of the full registry**: missing cells, failed gates, non-finite values, every verdict, class, label and outcome of §8 on both lines. This includes records in which no arm is CAPACITY_SUPPORTED and every arm is in turn NOT_EVALUATED, DEPENDENCE_FAILED, NOT_TESTED_BY_LOAD, CAPACITY_ONE_TRANSITION and INTERMEDIATE; each must give CAPACITY-INCONCLUSIVE (or NOT TESTED) with the right reason, never CAPACITY-NEGATIVE.
- Outputs: the MC snapshots; the projection; stage caps (twice the measured stage time); the headroom proof; the seed-block decisions.

### 10.3 Resources

- Apple M5 Max, 18 cores, 48 GB; CPU only. No cloud, paid service, download, new dependency, change to `uv.lock` or `pyproject.toml`, or SSD work.
- **Stages:** generate → gates → train (six single-thread workers) → evaluate (six workers) → timing (isolated) → simulate → analyze → report. **Each registered stage is started by a fixed launch script that is part of the freeze.** Training and evaluation never overlap a timing stage of any study.

**Caps (the human lead's figures, §15):** **16 charged hours** (raised from 12 by the human lead on 2026-11-15, §15) for calibration, rehearsal and the registered stages together; **3 GiB per worker; 18 GiB aggregate.**

**Projection (not a measurement).** Per-update costs from the P9-I rehearsal, as tabulated in `adr-0021-review/outputs/c4b_matrix_budget_final.txt`; T-OQ assumed at twice F-OQ; the new D-OQ and the index build are unmeasured; the evaluation figure is the lead's estimate.

| Item | CPU-hours | Charged hours (six workers) |
|---|---|---|
| Calibration: load 2.9, U_P check and H8 0.5, dense rate 2.1 | 5.5 | about 0.9 |
| Rehearsal with isolated timing | — | about 0.45 |
| **Charged before the headroom rule** | | **about 1.4** |
| Training, 150 cells (per replicate 15,440 s: F-OQ 3,540, T-OQ 7,060, H8 1,540, D-OQ 3,000, R2 290) | 21.4 | 3.6 |
| Seed block, draw 1 (14 cells) | 2.0 | 0.3 |
| Seed block, draw 2 (14 cells) | 2.0 | 0.3 |
| Evaluation, with index builds and the ablations at every rule snapshot | — | about 1.0 |
| Gates, timing stage, simulation, analysis, report | — | about 0.4 |
| **Remaining, seed block on draw 1 only** | | **about 5.3** |
| **Remaining, seed block on draws 1 and 2** | | **about 5.6** |

- **Headroom rule:** after the rehearsal, charged-so-far plus twice the projected remaining time must be at most the cap (16 hours since the human lead's decision of 2026-11-15; 12 before), and twice the measured peak memory at most the memory caps (peak at most 1.5 GiB per worker; otherwise the evaluation batch is reduced and the rehearsal repeated).
- On this projection the draw-1 seed block needs 1.4 + 2 × 5.3 = **12.0 hours: zero slack.** The projection rests on unmeasured items: T-OQ at twice F-OQ (the largest item; at 2.5× the twofold rule needs about 0.8 hours more), the new D-OQ, the index builds and the evaluation hour (each 20% over adds about 0.4 hours under the twofold rule). **It is likely that the rehearsal measures more than the projection.** The cuts of this section then apply in order: the draw-1 seed block saves about 0.7 hours under the twofold rule, the D-OQ cut, where cut 3 permits it, about 0.37 hours (8K/64K) and 0.22 hours (32K/16K) under the twofold rule. Revision 4 adds two load-calibration runs (about 0.09 charged hours before the rule), so on this projection the draw-1 seed block exceeds a 12-hour cap by about that amount and cut 2 applies unless the rehearsal measures less. Beyond that the work returns to the human lead, with the measured shortfall and the options: raise the cap, or shorten the run lengths (which changes the registered design and needs a re-review). The lead does not choose between them.

**Cuts, fixed now, in this order, until the headroom rule holds; nothing else may be cut:**

1. The seed block on draw 2 (added only if it fits in the first place).
2. The seed block on draw 1 *(lead's choice of order; it is descriptive and enters no rule)*.
3. D-OQ at a larger cell (among 8K/64K and 32K/16K) **only if the load calibration predicted that step's smaller cell not loaded** (8K/16K for A2, read from its own load-0.5 calibration cell; 32K/4K for B1). If both cells are eligible and one suffices, 8K/64K is cut first, then 32K/16K *(lead's choice)*. A D-OQ cell at the larger cell of a step whose smaller cell was predicted loaded is never cut. A step whose D-OQ cell is cut prints DENSE NOT READ and cannot support CAPACITY_SUPPORTED.
4. If the rule still does not hold, the work stops and returns to the human lead.

The five replicates, U_P, the run lengths and every threshold are never changed to make the study fit. Each cut is written in the freeze record with the rules it changes.

## 11. Order of work and stop rules

1. Confirmation review of this revision by the auditor; revise until confirmed.
2. **Decision 1** (implementation, calibration, rehearsal): taken by the lead under the human lead's delegation quoted in §15, after the confirmation review, and recorded in §15.
3. Implementation with tests (every gate; every verdict, class, label and outcome on synthetic records; registered-mode refusals; fixed launch scripts).
4. Calibration (§10.1) in the order 0, 1, 2, 3; audited. Any return to the human lead named in §10.1 happens here.
5. Rehearsal (§10.2); implementation audit ending READY TO FREEZE.
6. Lane L status by §5.6, recorded.
7. Registered data generated and hashed; G1. Freeze of specification, code, config, launch scripts, seeds, thresholds, calibration records, rows, MC snapshots, D-OQ rates, cuts, seed-block decision and data identities.
8. **Decision 2** (the single registered run): taken by the lead under the same delegation, only if the audits end with no open blocker or major, nothing changed after calibration except what §8 allows, the headroom rule holds, and no registered seed has been observed. Otherwise it returns to the human lead. Recorded in §15 before anything registered runs.
9. The registered run, once.
10. Independent recomputation of every verdict, class, label and both outcomes from raw records and snapshots by the auditor; outcome report with deviations, failed attempts and negative results kept.

**Stop rules.**

- A failed engineering gate stops the run before training.
- Any difference between frozen and running code, config, launch scripts or data identities stops the run.
- A stage that would exceed its cap is not started; the study is S1-INCOMPLETE.
- A failed cell is kept and not re-run; the study is S1-INCOMPLETE.
- No stage is re-run with changed settings. A second attempt after an engineering stop is the human lead's decision.
- No registered seed is observed before decision 2, apart from G1.
- The caps are the human lead's. The lead does not raise them.

## 12. What S1 cannot establish

- That a learned memory works without an oracle. **No autonomous learned-memory success may be claimed from S1**, whatever lane L shows.
- That the language model can form the queries, or that any interface reaches the capacity measured here.
- **Useful capability beyond recall of the trained facts; any improvement of a language model's behaviour.**
- Efficiency, speed, latency or I/O. Counted work is logical. Simulated traffic is not a storage measurement. Throughput is an in-RAM CPU figure for a 27,392-parameter backbone.
- Capacity where no cell is loaded; anything beyond the registered slots, facts and run lengths.
- Anything about natural-language knowledge, composition, reasoning, skewed fact frequency, another backbone, or a trainable backbone.
- That DENSE AHEAD or CONVENTIONAL RETRIEVAL SUFFICES means memory is not needed in general, or that BEATS DENSE holds off this task.
- That a hierarchy helps locality, or that sublinear counted work is a finding about the tree.
- That "more slots" differs from "more store parameters": this read path cannot separate them (§5.3).
- Generalization across facts.
- That a dense architecture other than D-OQ would not do as well: one dense family is run, with a three-rate grid.
- After D7 was dropped there is one dense family in S1, and no learned arm that addresses facts without the oracle.
- TRANSFER-POSITIVE, SYSTEM-POSITIVE, a failure of the ArborLM concept, Astra validation, or a human approval that is not recorded.

## 13. Decisions reserved for the human lead

1. Every return named in §10.1 and §10.3 (no registered cell predicted loaded, a row that would need 131,072 facts, an overload row that does not fit, a failed U_P check, headroom that does not hold after the allowed cuts; in the last case the choice between raising the cap and shortening the run lengths).
2. The caps; whether S0, S1 and S2 training stages may overlap on the machine.
3. Any second attempt; any change after the freeze.
4. P10-I and any integrated study; the use of S1's outcomes in SYSTEM-POSITIVE; merge; publication; weight release; ADR-0012.
5. **Pending human answer (ADR-0020 §17 item 0).** If S0 qualifies no interface, every S1 outcome and reading is printed with "ORACLE-ADDRESSED — NO LEARNED ADDRESSING QUALIFIED (ADR-0020)" . If the human lead answers that S1's capacity labels are withheld in that case, S1 follows that answer; it is recorded verbatim in §15 and needs no other change to this specification. Until S0 has an outcome, the S0 status printed is "S0 NOT YET DECIDED". Whatever S0 shows, no S1 outcome is ever summarised as "ArborLM's capacity scales".

"K7(c)" in §8.7 and §8.8 means item 5 above. The question is pending; no answer is recorded.

## 14. Requirements map

| Requirement of the human lead | Where |
|---|---|
| Oracle or controlled addressing; no claim of autonomous success | §3, §8.7, §12 |
| Study A: fixed facts, 4K / 16K / 64K; recall, learning efficiency, robustness, generalization | §5.1, §5.2, §8.2–§8.8, §7.2 |
| Control for total trainable parameters; strong dense alternatives | §5.3, §8.5, §10.1 item 3 |
| Study B: more facts with more memory; flat, hierarchical, conventional sparse retrieval, exact-address references, dense controls | §5.1, §3, §5.5, §8.6 |
| Matched updates, exposures and compute analysed separately | §5.4, §8.2, §8.6 |
| Useful memory dependence, not slots selected | §7.1, §7.3, gate DEP |
| Ablations, value shuffling, held-out queries, utilization, separability, routing costs, throughput, estimated traffic | §7.2–§7.5 |
| Quantitative gates and CAPACITY-POSITIVE with its counterparts | §8 |
| Independence from TRANSFER-POSITIVE and SYSTEM-POSITIVE | §8.7 |
| Resources, caps, twofold headroom, training apart from timing | §10 |
| Own identity, seeds, partitions, freeze, audit, report | header, §6.3, §11 |

## 15. Approval record

The coordinating session states that the two quotations below are verbatim from the chat record, misspellings included. The author of this text did not read the chat record itself.

**Delegation (human lead, verbatim):**

> we can change it to  p10 can be self approve but p10-I need my review

**Budget (human lead, verbatim; the numbers shown to the human lead were S0 16 h, S1 12 h, S2 36 h):**

> im confortable with does number if it mean it will resolve most dough and close any posible misguidence due to a small set

Recorded by the lead:

- The lead may approve P10 studies, S1 among them. P10-I needs the human lead's review.
- S1's caps are 12 charged hours, 3 GiB per worker and 18 GiB aggregate. The delegation does not name the caps; the budget sentence does. The lead does not raise them.
- Independent review of revision 1 (Opus 5.5): NOT READY. Confirmation review of revision 2 (Opus 5.5): READY AFTER LISTED TEXT EDITS, K1–K7. Revision 3 applies them.
- Pending with the human lead: ADR-0020 §17 item 0 (§13 item 5). No answer is recorded.
- **Lead's approval:** given for implementation, calibration and rehearsal only (record below); the registered run is PENDING.
- Astra review: NOT_PERFORMED. Claude review is not Astra review.

### Lead's approval for implementation, calibration and rehearsal — 2026-11-15 (UTC)

Taken by the lead (Claude Fable 5.2) under the delegation quoted above. It is not a human approval of the study and not an Astra review.

- **Approved:** implementation of revision 4 in `studies/p10s1/`, its independent implementation audit, the calibration of §10.1 and the rehearsal of §10.2, all on calibration and rehearsal seeds only.
- **Not approved here:** the registered run. It needs a clean implementation audit, a rehearsal that satisfies the twofold headroom rule under the cap in force, a freeze record, and a separate recorded decision.
- **Basis:** the specification reviews have no open blocker or major (revision 1 review, revision 2 confirmation K1–K7, revision 3 re-check R1, R2, m1–m11, all applied in revision 4; R1 in the auditor's words, R2 by the auditor's option (c)). No S1 record exists and no registered seed has been observed.
- **Open with the human lead and unchanged by this approval:** the cap (12 hours; the lead asked whether to raise it to 16 and has no answer), and the answer of §13 item 5.
- S1 uses oracle or controlled addressing. No autonomous learned-memory success may be claimed from it.

### Human lead's decision on the cap — 2026-11-15 (UTC)

The lead asked: "Raise S1's cap from 12 to 16 hours? I recommend 16." The human lead answered, verbatim (the sentence also answers a P9-II and an S2 question, recorded in ADR-0019 and ADR-0022):

> yes I do, yes we can raise to 16 and I approve the package

Recorded by the lead:

- **S1's cap is 16 charged hours.** The memory caps are unchanged (3 GiB per worker, 18 GiB aggregate). The programme total is 16 + 16 + 36 = 68 hours.
- The decision was made before any S1 calibration, rehearsal or registered record exists. No rule, cut order, run length, threshold or cell changes; only the number the headroom rule of §10.3 compares against. Passages of this ADR that compute slack against 12 hours (§10.3's projection bullets, §21) describe the earlier cap and are kept as written.
- On the projection (about 1.5 hours before the rule, 5.3 hours remaining), 1.5 + 2 × 5.3 = 12.1 ≤ 16: both seed blocks (12.7 hours doubled) and every dense-control cell fit, with about 3.3 hours of doubled slack. The rehearsal decides.

## 16. Open questions

None are left for the lead. One question is pending with the human lead (§13 item 5).

## 17. Finding-by-finding map

| Finding | Change in revision 2 |
|---|---|
| B1 negative fires on an unevaluated study | §8.7 row 4 replaced as written; empty set never satisfies (b); synthetic-record tests in §10.2 |
| B2 dense gate cannot block | §8.5 dense paragraph replaced: three readings, DENSE AHEAD at −0.25 blocks every arm, DOMINATED withdrawn; §8.7 row 3 replaced. **Ruling differs from the review on BEATS DENSE:** ratio ≥ 1.10 in all 5 under MU and MC (ADR-0017's standard; K2), in place of +0.5 bits in all 5 in all three readings. Milestone reading conditioned on the dense label (§8.7) |
| B3 D-OQ not a strong control | §5.3 item 2 and §10.1 item 3 replaced as written; rehearsal times the new D-OQ (§10.2) |
| B4 grid unlikely to load the memory | §10.1 item 0 (load calibration) and its rule; run lengths 6 / 4 / 2·U_P (§5.4). Ruling: no load limit within budget returns to the human lead; no improvised row. Rule table replaced by K1 |
| What S1 is a study of (review §6) | §0, §8.8: two registered lines; CAPACITY NOT TESTED label (§8.7 row 5); milestone reading on the capacity line only |
| M1 iso-parameter cells | dropped (§5.3 item 1); H21-4 restated; parameter label removed |
| M2 plateau rule | §8.2: i\*, Δ_SAT on i\*, plateau at 0.10, two-doublings condition |
| M3 negatives under the budget | §8.2 rows 6–9, §8.3 row 6, §8.4 rows 5–6, §9 row. The review's EFFICIENCY and SLOWER verdicts are kept and renamed GAIN WITHIN BUDGET ONLY and BEHIND WITHIN BUDGET (accepted by the confirmation review) |
| M4 conventional sparse retrieval | F-OQ-IVF and KNN-W-IVF (§5.5); KNN-W renamed; hierarchy label against F-OQ-IVF (§8.5); milestone reading (§8.7) |
| M5 cut rule | U_P = 8,192 only (§5.4, §10.1 item 1); replicates never cut; T-OQ on all seven cells. **Ruling differs on the cut list:** seed block on draw 2, seed block on draw 1, then a D-OQ cell only where calibration predicted the step's smaller cell not loaded (§10.3, K3) |
| M6 seed block | §6.2; enlarged by ruling to draws 1 and 2 if the rehearsal rule admits it |
| M7 U_P gated by H8 | §10.1 items 1–2; UNDERTRAINED-AT-U_P (§8.4) |
| M8 label and reading overreach | STORE ONLY; ORACLE-ADDRESSED; reading as a necessary condition (§8.7); §12 line on useful capability |
| M9 Study B line | §8.6 KNOWLEDGE SCALES WITH MEMORY with floors |
| M10 exposure confound | §7.3 row-movement ratio, printed with every budget and efficiency verdict |
| M11 governance | §11 items 2 and 8; §15 with the delegation and budget quotations; caps stay the human lead's |
| m1 | §8.2 row 3: a_use about 0.954 |
| m2 | 1/16 snapshot (§5.4); dense rate read at U_P (§10.1 item 3) |
| m3 | MC-SHORT when the snapshot exceeds the run length (§5.4) |
| m4 | output projection in W; top-k comparisons counted separately (§7.4) |
| m5 | outcome-level bound and the limit of replication (§6.2). With T-OQ on all seven cells the union bound is 6/32, not the review's 4/32 |
| m6 | bounded ranges and named sibling ranges in G9; derived seeds checked (§6.3); ranges corrected by K7(a) |
| m7 | H1/H2 out of DEP; HELD-OUT FRAGILE against R2 (§7.2, §8.1). R2 does not exist at overloaded cells, so the row's reference cell is used (accepted by the confirmation review) |
| m8 | DEP at every snapshot a rule reads (§7.3, §8.1) |
| m9 | lane L descriptive, no step verdict; ADR-0020's labels and timing rule (§5.6) |
| m10 | timing retries; THROUGHPUT NOT MEASURED (§7.5) |
| m11 | MC under both cost measures, larger multiplier (§5.4) |
| m12, m13 | moot (M5, M1) |
| m14 | pairing sentence (§6.2) |
| m15 | keys in RAM assumed; key bytes an identity (§7.5) |
| m16 | MC-MISMATCH reported, no class change (§5.4) |
| m17 | caveat kept in §1 fact 5 and §9 |
| Review §5 matrix | adopted: 30 configurations, 150 cells; D7 dropped |
| **K1** load rule | §8.2 one "loaded" definition; row 4 requires a loaded smaller cell; §10.1 item 0 replaced; §0 wording |
| **K2** dense labels and milestone reading | §8.5 table; §6.2 sentence; §8.7 printed label and reading; §12 dense-family line |
| **K3** cut list | §10.3 cuts; §8.5 reference; §6.1, §6.2, §8 opening, §13 item 1 made consistent |
| **K4** efficiency line | §8.8 level, censoring, verdict table, OPTIMIZER-ASSISTED, step and arm classes, closing sentence |
| **K5** F-OQ-IVF work measured | §7.4 rule 4 |
| **K6** budget honesty | §10.3 projection bullet |
| **K7** ADR-0020 and seeds | §6.3 ranges; §5.6 items 1, 2, 4, 7; §6.1 lane row; §13 item 5; S0 status in both printed labels |
| Coordinator's process items | manifests (§7.6); fixed launch scripts (§10.3, §11); gates at real size on rehearsal seeds (§8.1); synthetic full-registry analysis (§10.2) |

## 18. The lead's choices in this revision

| Where | Choice |
|---|---|
| §5.1 | Study A row at 8,192 facts; largest registered fact set 32,768 unless the load rule adds a row |
| §5.4 | U_P = 8,192; run lengths 6 / 4 / 2·U_P |
| §5.5 | 10 Lloyd iterations; N/256 centroids; 512 candidates |
| §5.6 | no 65,536-slot lane cell |
| §6.2 | five draws; seed-block seeds |
| §7.2 | HELD-OUT FRAGILE at 0.90 × R2's ratio |
| §7.3 | minimal supports on a sample of 2,048 facts |
| §7.4 | SUBLINEAR = W at most doubles per fourfold step |
| §8.2 | 0.5 and 0.25 bits; plateau 0.10; one loaded threshold, i\* ≤ 4.0 at the registered run length; ceiling at 4.5 |
| §8.4 | a_use ≥ 0.80 at 32K/64K; learned keys required for the outcome |
| §8.5 | DENSE AHEAD at −0.25 in any reading, first; BEATS DENSE at r ≥ 1.10 in all 5 |
| §8.6 | Study B floor 0.85; ratio floor 0.5 |
| §8.8 | level 3.0 bits; half the updates; 0.8 of the compute; DENSE FASTER blocks; OPTIMIZER-ASSISTED at 1.5 times |
| §10.1 | load grid; loadedness read at the registered run length; overload-row U_P grid; no row without an R2 reference; dense rates {0.001, 0.003, 0.01} |
| §10.3 | the three cuts and their order (ruling, K3) |

## 19. The conflicts of revision 2 and how each was closed

1. Milestone reading from three sources. Resolved by the confirmation review, K2.
2. BEATS DENSE against DENSE AHEAD. Resolved by the confirmation review, K2.
3. Load rule completed by the lead. Resolved by the confirmation review, K1.
4. Overload row at load 8. Resolved by the confirmation review, K1.
5. Definitions of a loaded cell. Resolved by the confirmation review, K1.
6. m7 where R2 does not exist: R2 at the row's reference cell. Accepted by the confirmation review.
7. The second cut against M5's clause. Resolved by ruling 8 and the confirmation review, K3.
8. Efficiency line rules. Reviewed by the confirmation review, K4.
9. Budget with no slack. Moved into the rule of §10.3 by K6.
10. D7 dropped. Accepted by the confirmation review; §12 states that one dense family is run.
11. The quotations in §15. The coordinating session states they are verbatim from the chat record; the author of this text did not read the record.

## 20. What differs from the auditor's text

K1–K7 are applied with the auditor's wording. These points differ or go beyond it:

1. **Bracketed value.** K4's "[1.5]" is written as "1.5 times *(lead's choice)*".
2. **"K7(c)".** The auditor's texts for §8.7 refer to "K7(c)". They are kept as written; §13 says that K7(c) is §13 item 5.
3. **K2(c) layout.** The reading is one bullet with five sub-bullets, to fit the list it sits in. The words are unchanged.
4. **Consistency edits the auditor did not write out:** §0 says "loaded" in place of "saturated below the ceiling"; §6.1 and §6.2 say the draw-1 seed block can be removed by cut 2; "the two cuts" became "the cuts" in §8, §13 and §18; the calibration count notes +4 runs if the 65,536-fact row is added; the efficiency label also prints the S0 status; §13 item 1 names the returns K1 and K6 add; a reachability sentence from the auditor's arithmetic was added under §8.2.
5. **Not changed, and left open:** the efficiency step class UPDATES-ONLY STEP still reads "FASTER or FASTER IN UPDATES ONLY in all 5". A step with REACHED ONLY BY THE LARGER in some replicates and FASTER IN UPDATES ONLY in others is therefore MIXED. The auditor's text does not say otherwise.
6. **§12** carries the auditor's dense-family sentence and one more line on D7, as the lead asked.

## 21. Revision 4: the re-check of revision 3 (2026-11-15 UTC)

The auditor re-read revision 3 (`adr-0021-review/RECHECK_REV3.md`): K1–K7 were applied faithfully; two majors lay in the confirmation's own paste-ready text. Revision 3 is kept as `docs/reviews/p10-design-2026-11-15/revisions/ADR-0021-rev3.md`. No S1 record of any kind exists; nothing here was chosen after an observation.

| Finding | What revision 4 does |
|---|---|
| R1 efficiency verdict table not exhaustive | §8.8 rows 3 and 8 take the auditor's text |
| R2 cut 3 had no input for step A2 | option (c), lead's choice: 8K/16K is added to the load calibration (2 runs, about 0.09 charged hours); §10.1 item 0, §6.1 count, §10.3 |
| m1 | return to the human lead if no U_P of the added row qualifies |
| m2 | D-OQ in the added row at its larger cell only |
| m3 | the load-4 judgment is a prediction; the run judges the cell |
| m4 | the 65,536-fact table nests the 32,768-fact table |
| m5 | lane L is considered after the cuts; no cut is made to admit it |
| m6, m7, m11 | wording of §8.5, §6.2 and the storage reading |
| m8 | G9 lists P9-II's 1892 |
| m9 | the tag is required on every positive label, listed; the ban on "ArborLM's capacity scales" is unconditional |
| m10 | order of the two D-OQ cuts |

**Consequence for the budget, stated:** at a 12-hour cap the projection had zero slack; with the two added calibration runs the draw-1 seed block is projected not to fit, by about 0.09 hours. The cap is the human lead's and is not changed here.

## Addendum — the human lead's delegation on the hour cap (2026-11-15 UTC)

The human lead, verbatim (the first clause concerns ADR-0022):

> I Aprove the link files with 6.2mb and you can extend the hour cap if needed across all p10

Recorded by the lead, with the limits the lead puts on its own use of this:

- The lead may raise a P10 study's charged-hours cap when the study's own headroom rule would otherwise cut registered cells or stop the study.
- A cap is raised only **before that study's registered seeds are observed** (at the rehearsal's headroom check, or at a stage gate that reads time and memory only). It is never raised in response to a result, and never to add cells, arms, updates or replicates beyond what the specification registers.
- Each raise is recorded in the study's ADR with the measured projection that required it, the old and new cap, and what it protects. Memory caps (3 GiB per worker, 18 GiB aggregate, and S2's own) are not hour caps and are not changed.
- The human lead's words do not extend to downloads, cloud or paid services, models, data, thresholds or designs.

S1's cap is unchanged by this record (16 hours). Programme-level record: `docs/reviews/p10-design-2026-11-15/HUMAN_DECISIONS_2026-11-15.md`.

## 22. The lead's rulings on the implementation audit, fixed before calibration (2026-11-15 UTC)

The independent implementation audit (Opus 5.5, `docs/reviews/p10s1-implementation-audit-2026-11-15/AUDIT.md`) found the implementation READY AFTER LISTED FIXES: no blocker, 8 majors, 16 minors, and several passages of this ADR that an implementer cannot apply without a choice. The rulings below are the lead's (Claude Fable 5.2), made **before any S1 calibration, rehearsal or registered record exists**; no S1 observation of any kind bears on them. Where the auditor named the most conservative option, it is taken unless a reason is given. They are part of the specification from here on. Astra review: NOT_PERFORMED.

| Finding | Ruling |
|---|---|
| **M5** the dense matched-compute reading cannot be established at 65,536 slots (and nowhere for T-OQ and H8), so BEATS DENSE is unreachable for a supported arm and DENSE MATCHES would be printed without a comparison | The rule of §8.5 is **not changed**. Where the dense matched-compute pair is MC-SHORT or MC-AMBIGUOUS, the label printed is **DENSE NOT ESTABLISHED AT MATCHED COMPUTE (\<status\>)**, never DENSE MATCHES, and the DENSE MATCHES sentence is printed only where the reading is established. The matched-updates comparison with D-OQ (D-OQ then has at least the arm's compute) is printed beside it, descriptively, with its sign and size. An arm that is CAPACITY_SUPPORTED with this label can give CAPACITY-POSITIVE only as **CAPACITY-POSITIVE [… DENSE COMPARISON NOT ESTABLISHED AT MATCHED COMPUTE]**, and the reading "storage half supported, as a necessary condition" (§8.7) is **not available** to it. Stated plainly: as designed, S1 cannot show that the store beats or matches a dense map at matched compute at 65,536 slots. Closing that gap needs longer runs or another matched-compute definition; that is a design change for P10-I, not for this study |
| **M6** (reading d) the analytic multiply-add count | The count is of **one whole training update, including the frozen backbone's forward and backward pass**, which every arm pays (the auditor's option 2). Reason: §5.4 pairs it with a CPU-time measure of the whole step and takes the larger multiplier of the two; a count that omits the largest shared term is not a measure of the step. The formula is written out in the config and checked against a FLOP count at tiny size by a test. Alternative not taken: the implemented memory-plus-optimizer formula, which is harsher on the efficiency line and puts F-OQ's matched-compute readout on the run-length edge. This ruling makes matched-compute readouts easier to establish than the implemented formula did; it is made before any record exists and is stated so that it can be weighed |
| **M7** (reading a) the dense-rate tie, "goes to the faster of the two" | "Faster" is the faster learner: among rates within 0.02 at the selection readout, compare a_use at U_P/2, then U_P/4, down the doubling grid to U_P/16; at the first of these where they differ by at least 0.02 the higher wins; if they differ nowhere, the smaller learning rate is taken. The dense-rate calibration cells are evaluated on the doubling snapshots (evaluation only, no added training) |
| (b) lane L | As implemented (off; OMITTED labels). If S0 qualifies an interface before S1's freeze, the question returns to the lead; nothing is printed OMITTED by default in that case |
| (c) page-miss setting | Ratified: 8 rows per page, rho = 1/4, ascending tie rule. Descriptive; enters no rule |
| (g) which snapshots DEP reads | Every snapshot up to the run length (the stricter reading) |
| (h) "in at least 4 replicates" and the two panels | For a label that favours the store (TREE_AHEAD, TREE_COMPETITIVE and every positive condition) a replicate counts only if both panels satisfy it. For a label that blocks (DENSE AHEAD, DENSE FASTER) a replicate counts if either panel satisfies it |
| (i) MC-AMBIGUOUS | As implemented: not established |
| (j) calibration items 1 and 2 | a_use, as REF uses, not raw accuracy |
| (k), m3 the efficiency line without a decided dense reading | A FASTER STEP with no D-OQ cell prints DENSE NOT READ, and one whose dense-speed comparison is undecided from the bounds prints DENSE SPEED UNDECIDED; neither blocks, and EFFICIENCY-POSITIVE carries the label in its bracket |
| (m), (n) | Seed-block spread at U_P and U_run; robustness is read on Panel A and printed for both panels. Descriptive |
| m2 seed block with the overload row | The seed block is seven cells, as the ADR says |
| m13 a no-loaded row for one transition | CAPACITY NOT TESTED — NO LOADED CELL WITHIN BUDGET applies to the transition concerned; since CAPACITY_SUPPORTED needs a step in each transition, no arm is CAPACITY_SUPPORTED when either transition is not tested, and the outcome names the transition |
| **M4** recording Decision 2 | Decision 2 is recorded in a file outside the hashed specification (`results/p10s1-freeze-<date>/DECISION_2.md`), named in the freeze README; this ADR is amended with it after the registered run |
| M1, M2, M3, M8 and the other minors | Implementation defects; fixed as the audit states. M8: the whole registered sequence is exercised end to end on test seeds before the freeze |

Readings (e), (f), (l) and (o) were found correct and stand.

