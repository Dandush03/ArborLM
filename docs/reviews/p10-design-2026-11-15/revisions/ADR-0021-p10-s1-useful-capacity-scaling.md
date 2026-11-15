# ADR-0021 — P10-S1: Useful-capacity scaling under controlled addressing

- **Status: DESIGN REVISION 1 — DRAFT FOR THE LEAD, NOT YET REVIEWED. SPEC: PENDING ASTRA REVIEW. Nothing is implemented, calibrated, rehearsed or run. No approval exists.**
- **Date:** 2026-11-15
- **Study code:** P10S1. Package `studies/p10s1/`. Config `configs/p10s1_capacity.toml`. Tests `tests/test_p10s1_*.py`.
- **Origin.** The human lead's P10 milestone direction: three parallel, scientifically independent experiments (S0 robust addressing, S1 capacity, S2 two-teacher transfer). This document is S1 only.
- **Milestone question 1 (verbatim).** "Can increasing ArborLM's learned-memory capacity produce measurable gains in retained knowledge and useful capability without proportional increases in active inference work?"
- **Evidence it rests on.** P9-I (ADR-0017 Part I): `results/p9i-run-attempt2-2026-11-15/OUTCOME.md`, `docs/reviews/p9i-results-2026-11-15/REVIEW.md`, `results/p9i-calibration-2026-11-14/README.md`, `results/p9i-rehearsal-2026-11-14/README.md`; ADR-0017 §4–§8 and §15.2; P7-A, P7-B, P8 as summarized in `docs/RESEARCH_LOG.md`.
- **Roles (study-specific).** Lead: Claude Fable 5.2. Specification review, implementation audit and recomputation from raw records: Opus 5.5, in a context separate from the implementation. Implementation: Sonnet 5.5. Inventory: Haiku 5.5. The model that actually ran each delegated task is recorded from session metadata. ADR-0012 stays not approved. **Astra review: NOT_PERFORMED.**
- **Relation to other work.** S1 does not wait for S0 (ADR-0019) and does not depend on S2. ADR-0017 Lanes A–D stay calibration blocked; S1 is a new study and does not revive them. P1–P9-I code, configs, records and ADRs are not edited.
- **Marking.** Every number that is a judgment call is marked **[lead's choice]**.

## 1. What is known, with sources

Registered (P9-I, one data draw, U = 8,192 updates, alphabet loss, reads at answer sites only):

1. Oracle-query retrieval (R1) reached 1.000 at 4,096 slots / 2,048 facts, 0.999–1.000 at 16,384 / 8,192 and 0.967–0.972 at 65,536 / 32,768. Oracle address (R2) reached 1.000 at 16,384 (OUTCOME.md; REVIEW.md §1).
2. Every learned query interface collapsed and stayed at chance (0.028–0.044). The outcome was NO_INTERFACE_SELECTED (OUTCOME.md).
3. The dense window control D7 reached 0.78–0.80 at 16,384 (0.44 on the second backbone) and 0.13 at 65,536, and was still improving at U (REVIEW.md §4).

Calibration and rehearsal (rehearsal draws; not results):

4. The readout learns by number of updates of the shared output projection and gate, not by exposures per fact (ADR-0017 §I.1). R2 is near its ceiling by 2,048–4,096 updates at every size.
5. The oracle-query rung needs more updates as the memory grows: R1 reached 0.90 at 2,048 updates at 4,096 slots, 4,096 at 16,384 and 8,192 at 65,536 (calibration README). In that calibration facts grew with slots, so it does not say whether slots or facts cause the slowdown.
6. Under matched updates the three sizes differ sixteenfold in exposures per fact (512 / 128 / 32 at U = 8,192).
7. Cost with six single-thread workers: 0.008–0.012 s per update at 4,096 slots, 0.013–0.015 at 16,384, 0.035–0.049 at 65,536; peak worker memory 1.49 GiB, reached in evaluation at 65,536 (rehearsal README).

Earlier studies:

8. ADR-0017 Lanes A–D were calibration blocked (§15.2). Their capacity classes compared cells with different fact counts under one exposure rule, so a class could be passed or failed by the update budget alone (§5.5, §I.13).
9. P7-A and P7-B found no hierarchy-specific locality: a count-preserving null reproduced 98–103% of the tree's page-miss gap, and the tree was within 10% of flat co-access placement. In P8 every locality term cut the slots in use by 46–92%, and misses fell because the working set shrank (RESEARCH_LOG.md).
10. The backbone is frozen, byte-level, 27,392 parameters, context 64. Facts are synthetic 8-byte records with a 5-symbol identifier and a 1-symbol answer over a 32-symbol alphabet (5 bits per fact).

Not known, and tested here: whether a memory given the right query retains more facts when it has more slots; how many facts per slot it can hold; whether a tree keeps that at lower counted work; whether a dense map with the same parameters and the same oracle input does as well.

## 2. Question, scope and hypotheses

**Question.** With addressing controlled, does a larger learned memory retain more useful information about a fixed set of facts, and about a larger set of facts, than a smaller one, under matched training budgets and matched parameters, and at what counted work per query?

**Scope.** Every memory arm in S1 is given the identity of the queried fact by an oracle (§3). S1 measures the store, not the interface. It cannot show that a language model can use the capacity it measures.

Hypotheses. Each can fail.

- **H21-1 (capacity under load).** For the flat oracle-query memory, at a fixed fact set, a step to four times the slots is a capacity step (§8.2) whenever the smaller memory holds 2 or more facts per slot.
- **H21-2 (saturation).** When the smaller memory already holds 0.5 facts per slot, four times the slots neither helps nor hurts (the step is CEILING or NULL).
- **H21-3 (scaling with knowledge).** Along the proportional track, retained information grows at least 3.0 times per fourfold step under matched updates and under matched compute.
- **H21-4 (not parameters alone).** A dense map with the same parameter count and the same oracle input does not retain 0.5 bits per fact more than the memory, and a memory with the same parameters in fewer, wider slots does not reproduce the gain.
- **H21-5 (dependence).** The retained information disappears when values are shuffled or addresses are swapped, and survives held-out templates.
- **H21-6 (counted work).** The tree and the hashed memory show capacity steps while their counted work per query at most doubles per fourfold step; the tree retains at least 0.97 of the flat memory's information.
- **H21-7 (key learning).** The hashed exact-address memory shows the same step pattern as the flat oracle-query memory. A difference localizes a limit to key learning.

The lead's expectation, written before any observation: 8K/4K → 8K/16K and both steps at 32,768 facts are capacity steps; 8K/16K → 8K/64K is CEILING. A 4,096-slot memory has 196,608 parameters and 8,192 facts carry only 40,960 bits, so H21-1 can fail by the small memory storing several facts per slot without loss. That would be a registered negative.

## 3. Controlled addressing: what it is in each arm

| Arm | Query | Address (which slots are read) | Learned | Role |
|---|---|---|---|---|
| **F-OQ** flat, oracle query (R1 of ADR-0017 §5.3) | fixed random unit code per fact, a seeded hash of the identifier, width 16 | top-8 by cosine against learned keys, temperature 0.2 | keys, values, output projection, gate | primary |
| **T-OQ** learned tree, oracle query | as F-OQ | learned router picks 2 of N/256 branches of 256 slots; top-8 among their 512 keys | router, keys, values, output projection, gate | hierarchical memory |
| **H8** hashed exact address | none | 8 distinct slots given by a seeded hash of the identifier, weights 1/8; slots are shared between facts | values, output projection, gate | exact-address reference with sharing |
| **R2** oracle address (ADR-0017 §5.3) | none | one dedicated slot per fact, weight 1; defined only where facts ≤ slots | values, output projection, gate | reference rung |
| **D-OQ** dense, oracle input | the same code as F-OQ | none: code → hidden layer → output, all units active | both layers, gate | parameter-matched dense control |
| **D7** dense window (P9-I §I.3.3) | none (reads the seven frozen states) | none | adapter | dense alternative without an oracle |

1. In F-OQ and T-OQ the query is controlled and the address is learned: the memory must still decide which slots each code selects and what they hold. In H8 and R2 query and address are both controlled and only the content is learned.
2. The oracle is not causal and not available to a real system. The frozen backbone exposes about 0.4 bits of the 20-bit identifier at the answer site (ADR-0017 §I.1).
3. **Why a capacity effect under oracle addressing is still informative.** Whether gradient descent through a sparse top-8 read can write more facts into more slots, how interference grows with facts per slot, and whether a tree keeps this at lower counted work are properties of the store and its optimizer. They are needed by the ArborLM concept whatever forms the query. If capacity does not grow when the query is given, a learned interface is unlikely to rescue it. If it does grow, the open problem is the interface alone, which S0 studies.
4. **What it cannot support.** Any claim that a learned memory works autonomously; that the language model can address or use this capacity; that learned addressing would reach the same capacity (R1 is a reference, not a ceiling or a floor: ADR-0017 §I.3.1); anything about natural language. **Every positive label of S1 carries the annotation ORACLE-ADDRESSED and may not be printed without it.**
5. D-OQ receives the same code tensor as F-OQ, so the dense comparison is at equal information. D7 receives no oracle; it is the only learned arm of S1 that addresses facts by itself.

## 4. System common to all arms

- Frozen backbone as P9-I; no backbone parameter is trained in any arm. FP32, CPU only.
- Task, identifiers, records, contexts, templates and streams exactly as ADR-0017 §4 (family 1), from the audited generator of `studies/p9/data.py`, with gate G1. The planted clusters are produced by that generator and kept; no S1 rule uses them.
- Reads and additions **at answer sites only**. **Loss: cross-entropy over the 32 alphabet symbols at answer sites.** Scoring: most probable alphabet symbol, ties wrong. One AdamW, learning rate 0.003, no weight decay, clip 1.0, constant rate. A batch is 16 contexts = 128 answer-site exposures.
- Key width 16, value width 32, top-8, temperature 0.2, except the width controls of §5.3.
- New code only, in `studies/p10s1/`, importing `studies.p9` and `studies.p9i` unedited. New in S1: the hashed arm H8, a value width other than 32 with a 32 × d output projection, the dense control on the oracle code, the work counters, the evaluation of §7. At value width 32, F-OQ and R2 must reproduce the P9-I R1 and R2 forward and one training step bit for bit.

## 5. Design

### 5.1 The grid of facts and slots

Seven cells. "8K/4K" means 8,192 facts in 4,096 slots. Load is facts per slot.

| Facts \ Slots | 4,096 | 16,384 | 65,536 |
|---|---|---|---|
| 2,048 | **2K/4K** (0.5) | — | — |
| 8,192 | **8K/4K** (2) | **8K/16K** (0.5) | **8K/64K** (0.125) |
| 32,768 | **32K/4K** (8) | **32K/16K** (2) | **32K/64K** (0.5) |

- **Study A — fixed knowledge, expanding memory:** the row of 8,192 facts **[lead's choice; 8,192 rather than 2,048 so that the smallest memory is loaded above one fact per slot]**.
- **Study B — expanding knowledge, expanding memory:** the diagonal 2K/4K → 8K/16K → 32K/64K (the proportional track), with the row of 32,768 facts as its off-diagonal cells.
- Facts and slots are not confounded: every claim about memory size compares cells of one row.
- Loads 2 and 0.5 occur in both rows, so the report can say whether a step depends on load alone or also on absolute size.
- No cell overloads the 65,536-slot memory. Its capacity is bounded below only. Largest fact count 32,768 **[lead's choice; 131,072 facts would add about 1.5 hours per arm]**.

**Steps (same facts, four times the slots):**

| Step | Cells | Load | Transition |
|---|---|---|---|
| A1 | 8K/4K → 8K/16K | 2 → 0.5 | 4K→16K |
| A2 | 8K/16K → 8K/64K | 0.5 → 0.125 | 16K→64K |
| B1 | 32K/4K → 32K/16K | 8 → 2 | 4K→16K |
| B2 | 32K/16K → 32K/64K | 2 → 0.5 | 16K→64K |

A1 is the off-diagonal test for the lower diagonal step and B2 for the upper one: growth along the diagonal is attributed to memory only if the smaller memory, given the larger fact set, retains less.

### 5.2 What more slots can buy when the facts are fixed (Study A)

Under oracle addressing more slots cannot supply information the facts lack. They can do four things, each measured:

1. **Less interference.** Fewer facts share a slot, so more facts are retained. Quantity: retained bits per fact (§7.1). Prediction H21-1; rule §8.2.
2. **Faster or slower learning.** Quantity: u50 and u90, the first snapshot of the learning grid at which Panel A accuracy reaches 0.5 and 0.9. Fact 5 of §1 predicts slower learning with more slots; Study A separates slots from facts. Label §8.6.
3. **Robustness.** Quantity: accuracy retained when a random 5% or 20% of value rows are zeroed, and under Gaussian value noise of 0.1 and 0.5 of the row RMS (three seeded masks each). Label §8.6.
4. **Redundancy.** Quantity: length of a fact's minimal support and the number of facts per slot (§7.3). Descriptive.

Generalization across facts is not among them: the answers are independent random symbols (§7.2).

### 5.3 Parameter controls

Memory parameters grow with slots (48 per slot at key width 16 and value width 32). Three controls separate "more slots" from "more parameters":

1. **D-OQ, the parameter-matched dense control**, in every grid cell: hidden width set so its trainable parameter count equals F-OQ's at the same slot count within 0.1% (about 4,117 / 16,405 / 65,557 hidden units; the implementation computes them and the audit checks them). Same code input, loss, optimizer and updates.
2. **Fewer, wider slots at equal parameters (iso-parameter cells), on the Study A row:**
   - **F-OQ-wide at 8K/4K:** 4,096 slots, value width 175, 787,937 parameters against 787,457 for F-OQ at 16,384 (0.06%). Key width stays 16 so the oracle code is unchanged.
   - **H8 at three slot counts with one parameter count:** 4,096 slots × value width 127, 16,384 × 32 (the standard cell), 65,536 × 8; each within 0.25% of 525,313. **[lead's choice: tolerance 0.25% for these cells; 0.1% is not reachable with integer widths. Flagged as a relaxation.]**
   - F-OQ has no iso-parameter cell at 65,536: it would need 3 parameters per slot, which leaves no usable key.
3. **Counted work goes with the control:** a wide slot reads 8 × 175 values per query instead of 8 × 32. The control therefore also says whether the gain can be had only by raising the work per read.

### 5.4 Budget regimes

Every cell is trained once, at a constant learning rate, and read at snapshots. A snapshot is a valid shorter run (gate G4 checks it).

- **U_P**, the primary update count, is the same for every cell and is fixed by calibration (§10.1).
- **MU — matched updates:** both cells at U_P.
- **ME — matched exposures per fact.** Within a row the facts are the same, so MU and ME are the same readout. Across rows ME is read at E_0 = 128·U_P/32,768 exposures per fact (32 at U_P = 8,192): cells with 8,192 facts at U_P/4, with 2,048 facts at U_P/16.
- **MC — matched training compute.** The costlier cell is read at U_P; the cheaper cell at the smallest snapshot of {1, 1.25, 1.5, 2, 2.5, 3, 4}·U_P whose cumulative cost is at least the costlier cell's. Rounding up gives the cheaper cell the benefit. Cost is single-thread process CPU-seconds per update, measured for each arm and slot count in the isolated timing part of the rehearsal (§10.2: median of three runs of 256 updates after 32 warm-up updates), and **fixed in the freeze record**. Analytic multiply-adds per update are reported beside it. If the ratio exceeds 4 the comparison is MC-SHORT and counts as not established.
- **SAT — saturation:** the smaller cell at its last snapshot U_run, with a plateau check (§8.2).
- **Run lengths, fixed at the freeze by this rule:** 65,536-slot cells run 2·U_P. Every other cell runs max(2, g)·U_P, g being the largest MC multiplier it needs, capped at 4. Projected from P9-I costs: 2·U_P at 4,096 slots, 3·U_P at 16,384.
- The registered run records process CPU-seconds per snapshot. If two readouts compared under MC differ by more than 25% in recorded CPU-seconds, **MC-MISMATCH** is printed with the comparison. It does not change a class **[lead's choice; the registered run has six workers contending, the freeze timing is isolated]**.

**Which regimes a capacity claim needs, and why.**

1. **Every class compares cells of one row.** Updates and exposures per fact are then equal by construction. The sixteenfold exposure difference of P9-I and the budget-driven classes of ADR-0017 Lane A cannot arise in a class.
2. A capacity step needs **MU (= ME), MC and SAT, all three.** MU alone gives the larger memory more compute. MC removes that. SAT removes the reading "the smaller memory is only slower".
3. Along the diagonal the three regimes are reported separately. **MU and MC are binding; ME is not.** At E_0 the smaller cells have had 4 and 16 times fewer updates of their shared parameters, and fact 4 of §1 says that is what limits them. ME therefore favours the larger memory and cannot support a claim. An ME readout matched to the small cell's exposures would need 16·U_P updates at 65,536 slots and is not run; that is stated in the report.
4. Any difference that appears under MU and not under MC is reported as a training-budget difference, not as memory scaling.

### 5.5 Baselines without training

- **DICT (conventional exact retrieval).** A hash table from the identifier bytes to the answer symbol (ADR-0017 D01). Exactly 1.0 on trained facts by construction; one probe per query; 25 bits per fact. On this task it dominates every learned arm in accuracy, storage and work, and the report says so in the cost table.
- **KNN-W (conventional sparse retrieval over the model's own states, no learning, no oracle).** For each fact one stored key: the 224-wide vector of the seven frozen states of its record at its first training occurrence, with the mean stored key subtracted, unit-normalized; the stored value is the answer symbol. A query is built the same way at the test site; the prediction is the stored answer of the nearest key by cosine, exhaustive and exact, ties wrong. Storage F × 224 values; F × 224 multiply-adds per query.
- **No-memory baseline** and the **unseen-fact control** (2,048 identifiers never trained), as ADR-0017 §5.6.

### 5.6 Optional lane L — learned addressing (separately labelled)

1. Lane L runs only if, **before S1's freeze**, S0 (ADR-0019) has a registered outcome ADDRESSING-RELIABLE with an interface carried forward, recomputed by the auditor and accepted by the human lead.
2. If so: arm **F-LA**, the flat memory with that interface exactly as S0 froze it (S0's code, S0's calibrated settings, no tuning in S1), on cells 2K/4K, 8K/4K and 8K/16K, five replicates, 15 cells, each run to S0's qualified update count for its slot count.
3. Lane L reports step A1 by the rule of §8.2 with F-LA in place of F-OQ, and the ratio of F-LA's to F-OQ's retained bits per cell. If F-LA fails S0's own cell-success rule at 2K/4K or 8K/16K, lane L is NOT_EVALUATED.
4. Lane L changes no S1 class or outcome. Its label reads LEARNED-ADDRESS LANE: A1 CAPACITY / NOT SUPPORTED / NOT_EVALUATED, with S0's annotations (for example that training used a target slot per fact).
5. If no interface is qualified at the freeze, lane L is omitted, the freeze record says so, and the report prints **LEARNED-ADDRESS LANE: OMITTED — no interface qualified before the freeze**. S1's freeze is not delayed for S0.

## 6. Matrix, replicates and seeds

### 6.1 Trained cells

| Arm | Grid cells | Configurations |
|---|---|---|
| F-OQ | all seven | 7 |
| H8 | all seven | 7 |
| D-OQ | all seven | 7 |
| T-OQ | 2K/4K, 8K/16K, 32K/4K, 32K/16K, 32K/64K | 5 |
| R2 | 2K/4K, 8K/16K, 8K/64K, 32K/64K (run to U_P only) | 4 |
| D7 | 2K/4K, 8K/16K, 32K/64K | 3 |
| Iso-parameter | F-OQ-wide 8K/4K; H8 width 127 at 8K/4K; H8 width 8 at 8K/64K | 3 |
| **Per replicate** | | **36** |
| **Registered total, 5 replicates** | | **180** |
| Lane L (only if qualified) | F-LA × 3 cells × 5 | +15 |
| Calibration (§10.1) | | 22 runs |

No cell depends on another. Without training, per replicate: no-memory, DICT, KNN-W and the unseen-fact control at each of the three fact counts.

### 6.2 Replicates

- **Five replicates [lead's choice].** Replicate r is data draw r with initialization seed 2100 + r. Each draw is a complete independent data set: a fact table of 32,768 facts whose first 8,192 and first 2,048 are the smaller sets, a training stream per fact count, Panels A and B, held-out template panels H1 and H2, the unseen-fact control.
- Draw and initialization vary together. The study does not separate them and does not need to.
- **Pairing.** Within a replicate and row, every slot count and arm sees the same facts, the same training contexts in the same order, and the same initialization of the shared parameters where their shapes agree.
- **Statistical meaning of "all five".** If the paired difference exceeded the threshold with probability at most 1/2 in each replicate, all five would do so with probability at most 1/32 = 0.031. "At least 4 of 5" has probability at most 6/32 = 0.19 under the same null and is used only for negative, ceiling and annotation rules, never for a positive step. No correction is made across the four steps and three arms; the family is stated instead: the primary family is F-OQ's four steps.
- Sampling error within a cell is small beside the thresholds: with 8,192 facts the standard error of an accuracy is at most 0.006, about 0.03 bits per fact.
- One backbone (B101/O301). Backbone variation is not studied.

### 6.3 Seeds and partitions

- Registered data seed sets `p10s1-draw-1` … `p10s1-draw-5`, bases 210001, 210101, 210201, 210301, 210401; each set uses base + i as the P9 generator does (14 names, null seeds at +20 and +30). Hash-address seed for H8: base + 40. Derangement and dropout-mask seeds: base + 50 to base + 59. Initialization seeds 2101–2105.
- Calibration draws: bases 219001 and 219101, initialization seed 2191. Rehearsal draw: base 219201, initialization seed 2192. Unit tests: 921001 upward.
- The implementation asserts that these ranges are disjoint from each other and from every earlier namespace, listed in the config: P9 (170001–171343, 179001–179933, 1701–1702), P9-I (182001–182020, 1791–1792, 1801–1802, 180101–181900, 900001–900233), the review's diagnostic seeds (500001–500004), ADR-0019's declared ranges (190001–190733, 1891, 1901–1902), the seeds of P1–P8 read from their configs, and whatever range S2 declares. The assertion is gate G9.
- Within a draw: training contexts, Panel A, Panel B, H1 and H2 are disjoint (verified by hash); H1 and H2 use byte sets never used in training; no fact's record precedes its own answer site. No registered panel is used in calibration or rehearsal.

## 7. Measurements

### 7.1 Useful retained information (primary)

For a cell, snapshot and panel:

- A fact is **usefully retained** if (1) the model with its memory gives the fact's answer, and (2) when the fact's read is replaced by the read of another fact π(f) it no longer gives that answer. π is a seeded derangement of the cell's facts with a different answer symbol. For D-OQ the input code is swapped the same way. For D7, condition (2) is the adapter disabled.
- Condition (2) removes facts answered by a fact-independent output (P9-I's collapsed arms scored exactly 230 of 8,192 by predicting one symbol).
- **a_use** is the share of usefully retained facts. **i = 5 − h₂(e) − e·log₂31** bits per fact, with e = 1 − a_use (the Fano bound of ADR-0017 §6.1; 1.52 at a_use = 0.5, 4.04 at 0.9). i is set to 0 when the count is at or below the upper end of the chance interval (gate G2). **I_use = F·i** bits.
- Every rule uses i or I_use. Raw accuracy, the Σ-renormalized log-loss gain and the 256-way loss are reported descriptively.
- Slot counts, distinct selected slots and entropy of use never enter a capacity rule.

### 7.2 Held-out queries and what generalization means here

1. The answers are independent random symbols. Nothing about one fact predicts another. Accuracy on **unseen facts must be at chance**; it is a leakage control (flag LEAKAGE), not a generalization score.
2. **Generalization means the same fact asked in a context never trained on.** Primary panels A and B: training templates, new co-records, positions and order. Held-out panels H1 and H2: separator and binding bytes never seen in training.
3. Under oracle addressing the query does not depend on the context. Held-out panels therefore test whether the **readout through the frozen upper block** holds on unseen surrounding states. They do not test address generalization; that is S0's question. For D7 and KNN-W, which read the states, they test both.
4. Rule (part of gate DEP, §8.1): raw accuracy on H1 and on H2 at least 0.90 of the cell's Panel A accuracy.

### 7.3 Memory dependence, utilization and separability

- **Ablations, every memory cell, at U_P:** memory disabled; value shuffle (a seeded derangement of value rows over slots, addresses kept); address swap (§7.1); slot dropout and value noise (§5.2).
- **Minimal support** (ADR-0017 §6.2 restricted to the answer-site read), at U_P on a seeded sample of 2,048 facts per cell on Panel A **[lead's choice; the full set would triple evaluation time]**: its mean length; U*, the slots in at least one minimal support.
- **Utilization:** distinct selected slots; U* over the sample; facts per slot (mean, maximum, distribution); dead slots.
- **Separability:** nearest-neighbour cosine between oracle codes; share of facts with a neighbour above 0.8; Jaccard overlap of the top-8 sets of a fact and its nearest neighbour; share of facts with a private slot; accuracy split by having such a neighbour. For T-OQ: share of the exhaustive top-8 found in the two visited branches (routing recall).
- **Training diagnostics** of ADR-0017 §6.3, including movement of rows on updates where they had no gradient.

### 7.4 Active memory work per query

Counted by instrumented counters in the forward. Gate G7 requires the counters to equal the formulas exactly.

| Arm | Key scores K (each 16 wide) | Value rows read V | W = 16·K + d_v·V multiply-adds |
|---|---|---|---|
| F-OQ | N | 8 | 16·N + 256 |
| T-OQ | N/256 + 512 | 8 | 8,704 / 9,472 / 12,544 at the three sizes |
| H8 | 0 | 8 | 256 |
| R2 | 0 | 1 | 32 |
| D-OQ | hidden width h ≈ N | h (the non-zero units are also counted) | about 48·N |
| KNN-W | F keys, 224 wide | 1 | 224·F |
| DICT | one hash probe | 1 | — |

1. These are logical counts. **They are not measured efficiency, latency or I/O.**
2. **Sublinear** in a rule means W at most doubles across a fourfold step in slots **[lead's choice; exponent at most 0.5]**. By the formulas only T-OQ, H8 and R2 can meet it. F-OQ reads a constant number of value rows and scores every key: it is printed **LINEAR KEY SCORING**.
3. The P7-B and P8 lesson: no reduction of counted or simulated traffic is reported without the working set (distinct selected slots) beside it, and none is called locality.

### 7.5 Throughput and estimated storage traffic

- **Throughput (measured, RAM only).** A separate timing stage after all training and evaluation, one process, nothing else of the project running, load average recorded and the stage refused if it exceeds 1.0 at start. Read-path queries per second at batch 1 and 128 for F-OQ, T-OQ, H8 and D-OQ at each slot count, on the replicate-1 snapshots, five repeats. A figure is reported as stable only if its coefficient of variation is at most 5%; otherwise UNSTABLE (P6-E lost 26.5% of its timing records to instability).
- **Estimated storage traffic (arithmetic and simulation, no device).** Value bytes read per query (V·d_v·4). Key bytes scored per query if keys were on storage (an identity from §7.4). Distinct pages touched per query at 8 and 32 rows per page under the identity layout. Page misses from `studies/p9/sim.py` at one setting (cache = 1/4 of the pages of the working set, 32 rows per page) with three count-preserving nulls, the ratio to the null, and the working set. A setting with a null miss rate below 0.05 is DEGENERATE.
- **Actual SSD inference and latency claims require physical measurements in a later experiment.** Nothing in S1 is one.

### 7.6 Cost table (per cell, every arm and baseline)

I_use; trainable and stored parameters and bytes; retained bits per stored byte; K, V, W; training updates, exposures per fact, CPU-seconds and analytic multiply-adds to each readout; throughput; estimated traffic.

## 8. Gates, rules and classes

After the calibration outputs are written only U_P, the dense learning rate, a failed row, the run lengths and MC readouts from the timing rule, and the registered cuts of §10.3 may change. Anything else is a new revision.

### 8.1 Gates

**Engineering gates (a failure is ENGINEERING-FAILURE, §8.7):**

- **G1** generator checks per draw and fact count (ADR-0017 §4.6).
- **G2** chance: the no-memory baseline on the three fact sets and the unseen set, both primary panels, all five draws: 40 tests, each inside the exact binomial central interval of level 1 − 0.001/40 around 1/32. That interval is "chance" in every rule.
- **G4** determinism and identity: stream hashes; checkpoint restoration bit for bit (model and optimizer) for one cell of every arm at real size; training to a snapshot, restoring and continuing equals the straight run; F-OQ and R2 at value width 32 identical to P9-I's R1 and R2; logits on the backbone's corpus rows identical to the frozen backbone's.
- **G5** gradient reach, **for every one of the 36 configurations instantiated at its real facts and slots, on a batch of that cell's own training stream:** every trainable group receives a non-zero gradient; in H8 exactly the hashed rows do; R2's table covers every fact of the cell; nothing reaches the backbone.
- **G6** controlled-addressing integrity: the query and selection of F-OQ, T-OQ, H8 and R2 are unchanged when the context around a record is permuted and when the answer table is replaced; D-OQ's input tensor has the same hash as F-OQ's codes; no forward takes the answer as input.
- **G7** work counters equal §7.4. **G8** parameter matches within tolerance (§5.3). **G9** seed disjointness (§6.3).
- **The gates stage must run at real size on the rehearsal draw before the freeze** and again on registered seeds before training. A harness error is reported separately from a gate failure. (P9-I attempt 1 stopped because its gate harness had never run at real size.)

**Scientific gates (a failure is a recorded result, not an engineering failure):**

- **REF** (reference rung), per replicate and row: R2 a_use ≥ 0.95 on both panels at U_P, at 8K/16K for the row of 8,192 facts and at 32K/64K for the row of 32,768 (and at 2K/4K for the diagonal). If it fails, that replicate is NOT_EVALUATED for the row: the readout did not work, so no capacity statement is possible. R2 at 8K/64K enters no rule; it is reported as a check that a dedicated-slot memory does not change when unused slots are added.
- **DEP** (dependence and generalization), per memory cell with a_use ≥ 0.25: memory disabled gives chance; value shuffle gives chance; a_use ≥ 0.95 × raw accuracy; unseen facts at chance (else LEAKAGE); H1 and H2 as §7.2 rule 4.

### 8.2 Step verdict in one replicate

For an arm and a step N → 4N at fixed facts, with i read on Panels A and B separately. Δ_MU = i(4N; U_P) − i(N; U_P). Δ_MC = i(4N; U_P) − i(N; U_MC). Δ_SAT = i(4N; U_P) − i(N; U_run). A cell has **plateaued** if i(U_run) − i(U_run/2) ≤ 0.25. If the panels give different verdicts the verdict is PANEL-DISAGREE. First match wins.

| Order | Verdict | Rule |
|---|---|---|
| 1 | NOT_EVALUATED | REF fails for the row, or LEAKAGE in either cell |
| 2 | DEPENDENCE_FAILED | either cell fails DEP |
| 3 | CEILING | i(N; U_P) ≥ 4.5 (a_use about 0.95; less than 0.5 bits of room) |
| 4 | CAPACITY | Δ_MU ≥ 0.5, Δ_MC ≥ 0.5, Δ_SAT ≥ 0.5; the smaller cell has plateaued; a_use(4N; U_P) ≥ 0.5 |
| 5 | EFFICIENCY | Δ_MU ≥ 0.5, not row 4 (the gain depends on the budget, or the smaller memory was still learning) |
| 6 | REVERSED | Δ_MU ≤ −0.5 |
| 7 | NULL | \|Δ_MU\| < 0.25 and the larger cell has plateaued |
| 8 | UNRESOLVED | otherwise |

- 0.5 bits per fact **[lead's choice; ADR-0017 §8.2 called a gap of that size material]** is 7 to 10 points of accuracy between 0.5 and 0.9. 0.25 **[lead's choice]** is half of it.
- Plateau is judged over the last doubling only. "Capacity" in S1 means within U_run updates; nothing is claimed about longer training.

### 8.3 Step class over the five replicates (first match wins)

| Order | Step class | Rule |
|---|---|---|
| 1 | NOT_EVALUATED | at least 2 replicates NOT_EVALUATED |
| 2 | DEPENDENCE_FAILED | at least 2 replicates DEPENDENCE_FAILED |
| 3 | NOT REPLICATED | at least 2 replicates PANEL-DISAGREE |
| 4 | CAPACITY STEP | CAPACITY in all 5 |
| 5 | EFFICIENCY STEP | CAPACITY or EFFICIENCY in all 5 |
| 6 | CEILING | CEILING in at least 4 |
| 7 | REVERSED | REVERSED in at least 4 |
| 8 | NO GAIN | NULL or REVERSED in at least 4 |
| 9 | MIXED | otherwise |

The denominator is always 5. A replicate that is not evaluated cannot be dropped to reach "all".

### 8.4 Arm class (F-OQ and H8 on steps A1, A2, B1, B2; T-OQ on B1, B2; first match wins)

| Order | Arm class | Rule |
|---|---|---|
| 1 | NOT_EVALUATED | every step of one transition is NOT_EVALUATED |
| 2 | DEPENDENCE_FAILED | any step is DEPENDENCE_FAILED |
| 3 | CAPACITY_SUPPORTED | a CAPACITY STEP in the 4K→16K transition and one in the 16K→64K transition; no step REVERSED; a_use ≥ 0.80 at 32K/64K at U_P in all 5 replicates **[lead's choice: "good retrieval accuracy"]** |
| 4 | CAPACITY_ONE_TRANSITION | at least one CAPACITY STEP, not row 3 |
| 5 | NOT_TESTED_BY_LOAD | every step is CEILING |
| 6 | CAPACITY_NOT_SUPPORTED | every step is NO GAIN, REVERSED or CEILING |
| 7 | INTERMEDIATE | otherwise |

### 8.5 Control and cost labels (printed with every arm class; first match wins within each)

**Dense, at the larger cell of each CAPACITY STEP,** with d = i(arm) − i(D-OQ), under MU (both at U_P) and under MC (the cheaper of the two read at its matched-cost snapshot):

| Label | Rule |
|---|---|
| BEATS DENSE | d ≥ +0.5 in all 5, under MU and MC, at every such cell |
| DENSE AHEAD | d ≤ −0.5 in at least 4, under MU and MC, at every such cell |
| MATCHES DENSE | otherwise |

**DOMINATED BY DENSE** = DENSE AHEAD and the arm is not SUBLINEAR: the dense control retains more at equal parameters and compute, and the memory does not save counted work.

**Parameters, on the Study A row,** with d = i(standard cell at 4N) − i(iso-parameter cell at N), at U_P: SLOT-SPECIFIC if d ≥ 0.5 in all 5; PARAMETER-DRIVEN if d < 0.25 in at least 4; UNRESOLVED otherwise; NOT ASSESSED where no iso-parameter cell exists (F-OQ step A2; T-OQ). For H8 both steps are assessed.

**Active work, per CAPACITY STEP:** SUBLINEAR (analytic) if W at most doubles; otherwise LINEAR KEY SCORING.

**Hierarchy,** T-OQ against F-OQ on I_use at 8K/16K and 32K/64K at U_P: TREE_AHEAD if the ratio is ≥ 1.03 in at least 4 replicates at both cells; TREE_COMPETITIVE if ≥ 0.97; otherwise TREE_BEHIND (thresholds of ADR-0017 §8.2).

**Conventional retrieval:** CONVENTIONAL RETRIEVAL SUFFICES if KNN-W's i is within 0.25 of the arm's, or above it, on Panels A and B in at least 4 replicates at 32K/64K. DICT DOMINATES ON THIS TASK is always printed.

**Key learning:** KEY-LEARNING-LIMITED if H8 is CAPACITY_SUPPORTED and F-OQ is not.

### 8.6 Descriptive labels (enter no class)

- **Diagonal scaling,** per arm, under MU, ME and MC separately: PROPORTIONAL if I_use grows ≥ 3.0 times at both diagonal steps in all 5 replicates; SUBPROPORTIONAL if below 2.0 at some step in at least 4; otherwise INTERMEDIATE. The ME line always carries the sentence of §5.4 rule 3. **MEMORY-ATTRIBUTED** is printed for a diagonal step only if its off-diagonal step (A1 for the lower, B2 for the upper) is a CAPACITY STEP.
- **Learning efficiency,** per step: MORE SLOTS LEARN SLOWER if u50(4N) ≥ 2·u50(N) in at least 4 replicates; FASTER if ≤ 0.5·u50(N); otherwise SAME. Learning grid: U_P × {1/8, 1/4, 1/2, 1} and the later snapshots.
- **Robustness,** per step, cells with a_use ≥ 0.5: ROBUSTNESS RISES WITH SLOTS if accuracy retained under 20% slot dropout rises by ≥ 0.05 in all 5; FALLS if it drops by ≥ 0.05 in at least 4; otherwise UNCHANGED.
- **D7** (no oracle): its I_use beside each oracle arm at the diagonal cells, with the sentence "D7 addresses facts without an oracle; the oracle arms do not."
- **Optimizer note.** Under AdamW a row that rarely receives a gradient still moves (ADR-0017 §5.5), and rows receive gradients less often in a larger memory. The SAT condition is the control; the share of movement on updates without gradient is reported per cell. No row-lazy arm is run.

### 8.7 Study outcome (first match wins)

| Order | Outcome | Rule |
|---|---|---|
| 1 | **S1-ENGINEERING-FAILURE** | any engineering gate of §8.1 fails, or frozen and running code, config or data identities differ. No scientific label is derived. |
| 2 | **S1-INCOMPLETE** (status) | any registered cell lacks a record. No outcome is derived; the denominator is never reduced. |
| 3 | **CAPACITY-POSITIVE** | F-OQ or T-OQ is CAPACITY_SUPPORTED and is not DOMINATED BY DENSE |
| 4 | **CAPACITY-NEGATIVE** | F-OQ is CAPACITY_NOT_SUPPORTED and T-OQ is neither CAPACITY_SUPPORTED nor CAPACITY_ONE_TRANSITION; or every learned-key arm that is CAPACITY_SUPPORTED is DOMINATED BY DENSE |
| 5 | **CAPACITY-INCONCLUSIVE** | otherwise; the reason is printed: NOT_EVALUATED, DEPENDENCE_FAILED, NOT_TESTED_BY_LOAD, ONE TRANSITION ONLY (which), INTERMEDIATE |

- **CAPACITY-POSITIVE means:** increasing memory supported more useful learned information under valid controls — at fixed facts, equal updates and exposures, matched compute and a saturated smaller memory; in all five replicates on both panels; memory-dependent; holding on held-out templates; not dominated by a dense map with the same parameters, input and compute.
- **It is always printed as** CAPACITY-POSITIVE [ORACLE-ADDRESSED; arm(s); dense label; parameter label; active-work label; hierarchy label; conventional-retrieval label; learned-address lane status].
- H8 alone cannot give CAPACITY-POSITIVE **[lead's choice: the label requires learned keys]**. Its class is printed beside the outcome.
- CAPACITY-NEGATIVE is a statement about this store, backbone, task and budget under oracle queries. It is recorded and kept.
- **Independence.** The outcome does not use, imply or depend on TRANSFER-POSITIVE or SYSTEM-POSITIVE. S1's contribution to SYSTEM-POSITIVE is descriptive input only: the outcome with its annotations, the cost table, and the sentence "addressing was supplied by an oracle". S1 never asserts SYSTEM-POSITIVE or any part of it.
- **Reading for milestone question 1, fixed now.** S1 supports question 1 under oracle addressing only if the outcome is CAPACITY-POSITIVE for an arm labelled SUBLINEAR (in the matrix: T-OQ). CAPACITY-POSITIVE for F-OQ alone reads: retained knowledge grew with memory at a constant number of value rows read and key scoring proportional to memory.

### 8.8 Decision map (recommendations only; nothing is authorized)

1. CAPACITY-POSITIVE with T-OQ → propose a study of the same store with a qualified learned interface, and separately a physical storage measurement.
2. CAPACITY-POSITIVE with F-OQ only → the tree or its router is the next question.
3. KEY-LEARNING-LIMITED → study key learning under load.
4. CAPACITY-NEGATIVE by NO GAIN → the store keeps several facts per slot at these counts; larger fact sets or a different task are needed before capacity can be tested.
5. CAPACITY-NEGATIVE by dominance → the dense map is the better use of these parameters on this task; the memory line needs a reason other than retention.
6. CAPACITY-INCONCLUSIVE → no capacity decision.

## 9. How S1 avoids the earlier traps

| Trap | Source | What S1 does |
|---|---|---|
| Learned interface collapses | P9-I | no class depends on a learned interface; lane L is optional and separate |
| Oracle rung needs more updates as memory grows | calibration | Study A fixes the facts so slots are separated from facts; SAT and plateau conditions; EFFICIENCY is a separate verdict from CAPACITY |
| Readout learns by updates of shared parameters | ADR-0017 §I.1 | cells compared in a class have equal updates; ME is not binding across rows |
| Sixteenfold exposure difference | P9-I | arises only on the diagonal, which enters no class; reported in three regimes |
| Calibration blocked | ADR-0017 §15.2 | calibration tunes one number on rungs already shown to reach their thresholds with this loss; a failed row has a fixed consequence; the reference rung is also checked per replicate in the run |
| Classes passed or failed by budget | ADR-0017 Lane A | a capacity step needs MU, MC and SAT; a negative needs a plateaued larger cell; undertrained cells give UNRESOLVED or EFFICIENCY, never NO GAIN |
| Slots selected mistaken for capacity | P8 | a_use needs per-fact dependence; slot statistics enter no rule |
| Working set shrinks, misses fall | P7-B, P8 | counted work is analytic and gated; simulated traffic carries nulls and the working set; no locality claim |
| Gate harness first run at registration | P9-I attempt 1 | gates run at real size on the rehearsal draw before the freeze, for all 36 configurations |
| One data draw | ADR-0017 §0 item 12 | five independent draws |

## 10. Calibration, rehearsal, resources

### 10.1 Calibration (two calibration draws, one initialization seed, before the freeze)

**What may be tuned, and by what rule. Nothing else.**

1. **U_P.** Arms R2, F-OQ and H8 on the diagonal cells, snapshots at 2,048 / 4,096 / 8,192 / 16,384 updates. U_P is the smaller of {8,192, 16,384} **[lead's choice of grid]** at which, at every diagonal cell, on both draws and both panels, R2 ≥ 0.95, F-OQ ≥ 0.90 and H8 ≥ 0.90. 18 runs.
2. **A failed row.** If 32K/64K qualifies at neither value, the row of 32,768 facts is REFERENCE_FAIL. The outcome is then CAPACITY-INCONCLUSIVE before the run, and the human lead decides whether the remaining cells are run. If 2K/4K or 8K/16K fails at both values, the work stops and returns to the human lead.
3. **Dense learning rate.** D-OQ at 8K/16K at learning rates 0.003 and 0.001, both draws, to 16,384 updates: the rate with the higher minimum Panel A accuracy at 8,192 updates; a difference below 0.02 goes to 0.003. 4 runs. The memory arms keep 0.003 untuned, so the tuning favours the control.
4. No T-OQ, D7, iso-parameter or off-diagonal cell is run in calibration. No step of §5.1 is observed before the registered run.
5. Calibration accuracies are reported as calibration, never as results. The calibration is audited before the freeze.

### 10.2 Rehearsal (rehearsal draw; time, memory and correctness only)

- All 36 configurations at real size for 64 updates and one full evaluation each, six single-thread workers, through the whitelist validator of P9-I (time, RSS, shapes, counts, identity; no loss or accuracy is written or displayed).
- The gates stage at real size.
- **Isolated timing part**, one process, nothing else of the project running: CPU-seconds per update for every arm and slot count (the MC rule of §5.4). Kept apart from the six-worker part because it is timing-sensitive.
- Analysis and report exercised on synthetic records of the full registry, including missing cells, failed gates, non-finite values and every class, label and outcome of §8.
- Outputs: the run lengths and MC readouts; the projection; the stage caps (twice the measured stage time); the proof of headroom.

### 10.3 Resources

- Apple M5 Max, 18 cores, 48 GB; CPU only. No cloud, no paid service, no download, no new dependency, no change to `uv.lock` or `pyproject.toml`, no SSD work.
- **Stages:** generate → gates → train (six single-thread workers) → evaluate (six workers) → timing (isolated, one process) → simulate → analyze → report. Training and evaluation never overlap the timing stage of any study.

**Projection (not a measurement of this study).** From the P9-I per-update costs. Assumed, to be measured in rehearsal: T-OQ at twice F-OQ; D-OQ at the cost of P9-I's dense arms; H8 near R2.

| Item | U_P = 8,192 | U_P = 16,384 |
|---|---|---|
| Training, summed over 180 cells | 15.8 CPU-hours | 31.5 CPU-hours |
| Training with six workers | about 2.9 h | about 5.8 h |
| Evaluation with six workers | about 0.7 h | about 0.9 h |
| Calibration | about 0.3 h | about 0.3 h |
| Rehearsal with isolated timing | about 0.45 h | about 0.45 h |
| Gates, timing stage, simulation, analysis, report | about 0.4 h | about 0.4 h |
| **Charged total** | **about 4.8 h** | **about 7.9 h** |

Per replicate at U_P = 8,192 the training sum is about 11,400 s: F-OQ 2,500, H8 1,200, D-OQ 2,800, T-OQ 3,400, R2 350, D7 650, iso-parameter 540. The longest cell is about 12 to 24 minutes.

**Proposed caps for S1 alone [lead's choice; fixed by the human lead at decision 2 on rehearsal evidence]:**

- **3 GiB per worker.** P9-I's peak was 1.49 GiB. The rehearsal must show a peak of at most 1.5 GiB; otherwise evaluation batch size is reduced and the rehearsal repeated before the freeze.
- **18 GiB aggregate** (six workers × 3 GiB), leaving room on a 48 GB machine for S0 and S2.
- **12 hours of charged execution** for calibration, rehearsal and the registered stages together, lane L included.
- **Headroom rule:** after the rehearsal, twice the projected remaining time must fit in the remaining cap, and twice the measured peak memory in the memory caps.

**Cut rule, fixed now, applied in this order until the headroom rule holds, each cut recorded in the freeze record:**

1. Drop lane L.
2. Drop D7 (15 cells; the D7 line of §8.6 becomes NOT RUN).
3. Drop replicate 5 everywhere. Every "all 5" becomes "all 4" (probability at most 1/16 = 0.0625 under the null of §6.2, stated with every label) and every "at least 4" becomes "at least 3".
4. Drop cell 32K/4K for every arm (step B1 is NOT RUN; the 4K→16K transition then rests on A1 alone).
5. If the rule still does not hold, stop and return to the human lead. No threshold, U_P or run length is changed to make the study fit.

At U_P = 16,384 the projection needs cuts 1 to 4 to fit 12 hours with twofold headroom.

## 11. Order of work and stop rules

1. Auditor review of this revision; revise until ready.
2. **Human decision 1:** approve the specification for implementation, calibration and rehearsal; accept or change the items of §13.
3. Implementation with tests (every gate; every class, label and outcome triggered on synthetic records; the dependent-free job registry; registered-mode refusals).
4. Calibration (§10.1); audited.
5. Rehearsal (§10.2); implementation audit ending READY TO FREEZE.
6. Lane L decision by the rule of §5.6, recorded.
7. Registered data generated and hashed; G1. Freeze of specification, code, config, seeds, thresholds, calibration record, run lengths, MC readouts, caps, cuts and data identities.
8. **Human decision 2:** approve the frozen revision, the caps and the single registered run. Recorded verbatim in §15 before anything registered runs.
9. The registered run, once.
10. Independent recomputation of every verdict, class, label and the outcome from the raw records and snapshots by the auditor; outcome report with deviations, failed attempts and negative results kept.

**Stop rules.**

- A failed engineering gate stops the run before training.
- Any difference between frozen and running code, config or data identities stops the run.
- A stage that would exceed its cap is not started; the study is S1-INCOMPLETE.
- A failed cell is kept and not re-run; the study is S1-INCOMPLETE.
- No stage is re-run with changed settings. A second attempt after an engineering stop needs the human lead's decision, with everything observed in the first attempt listed.
- No registered seed is observed before decision 2, apart from G1's generator checks.

## 12. What S1 cannot establish

- That a learned memory works without an oracle. **No autonomous learned-memory success may be claimed from S1**, whatever lane L shows.
- That the language model can form the queries, or that any interface reaches the capacity measured here.
- Efficiency, speed, latency or I/O. Counted work is logical. Simulated traffic is not a storage measurement. Throughput is an in-RAM CPU figure for a 27,392-parameter backbone.
- The capacity of the 65,536-slot memory (no cell overloads it), anything beyond 65,536 slots or 32,768 facts, or behaviour under training longer than U_run.
- Anything about natural-language knowledge, composition, reasoning, skewed fact frequency, another backbone, or a trainable backbone.
- That DENSE AHEAD or CONVENTIONAL RETRIEVAL SUFFICES means memory is not needed in general, or that BEATS DENSE holds off this task.
- That a hierarchy helps locality. S1 does not test locality.
- Generalization across facts. There is none to find in independent random facts.
- TRANSFER-POSITIVE, SYSTEM-POSITIVE, or a failure of the ArborLM concept.

## 13. Decisions reserved for the human lead

1. Decision 1 and decision 2 (§11).
2. The caps of §10.3, in particular 12 charged hours, and whether S0, S1 and S2 training stages may overlap on the machine.
3. Every item marked [lead's choice], and the open questions of §16.
4. Whether to run the remaining cells if calibration marks the row of 32,768 facts REFERENCE_FAIL.
5. Any second attempt; any change after the freeze; the use of S1's outcome in SYSTEM-POSITIVE; merge; publication; weight release; ADR-0012.

## 14. Requirements map

| Requirement of the human lead | Where |
|---|---|
| Oracle or controlled addressing; no claim of autonomous success | §3, §8.7, §12 |
| Study A: fixed facts, 4K / 16K / 64K; recall, learning efficiency, robustness, generalization | §5.1, §5.2, §8.2, §8.6, §7.2 |
| Control for total trainable parameters; strong dense alternatives | §5.3, §8.5, §10.1 item 3 |
| Study B: more facts with more memory; flat, hierarchical, conventional sparse retrieval, exact-address references, dense controls | §5.1, §3, §5.5 |
| Matched updates, exposures and compute analysed separately | §5.4, §8.2, §8.6 |
| Useful memory dependence, not slots selected | §7.1, §7.3, gate DEP |
| Ablations, value shuffling, held-out queries, utilization, separability, routing costs, throughput, estimated traffic | §7.2–§7.5 |
| Quantitative gates and CAPACITY-POSITIVE with its counterparts | §8 |
| Independence from TRANSFER-POSITIVE and SYSTEM-POSITIVE | §8.7 |
| Resources, caps, twofold headroom, training apart from timing | §10 |
| Own identity, seeds, partitions, freeze, audit, report | header, §6.3, §11 |

## 15. Approval record

Empty. To be filled with the human lead's words, verbatim, before any implementation (decision 1) and before the registered run (decision 2). Astra review: NOT_PERFORMED.

## 16. Open questions for the lead

1. **Dominance rule.** CAPACITY-POSITIVE is withheld only when the dense control is ahead and the arm saves no counted work. Should it instead require the memory to match or beat dense outright, as ADR-0017 §8.2 did?
2. **Hashed arm.** H8 alone cannot give CAPACITY-POSITIVE. Is "learned keys required" the right reading of "learned memory"?
3. **Five draws with one initialization seed each,** against three draws with two seeds. The first gives 1/32 for "all five" with draws as the unit and cannot separate draw from seed.
4. **Fact counts.** No cell overloads 65,536 slots. Add 131,072 facts at 16K and 64K (about 1.5 hours per arm) or accept a lower bound?
5. **Matched compute by rehearsal-measured CPU-seconds fixed at the freeze,** with the run's own CPU-seconds only flagged (MC-MISMATCH). Should a mismatch block the step instead?
6. **Row-lazy optimizer arm** (ADR-0017 A10) is not run; SAT is offered as the control for the AdamW movement effect. Is that enough?
7. **Twelve charged hours** is three times any earlier cap. Is U_P = 16,384 worth cuts 1 to 4, or should the grid be {8,192} only, with a failed reference returning to the human lead?
8. **Tree cells.** T-OQ runs on five cells and has no iso-parameter control. Add it to the Study A row (10 cells), or keep the hierarchy in Study B only?
