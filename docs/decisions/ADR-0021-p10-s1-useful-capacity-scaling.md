# ADR-0021 — P10-S1: Useful-capacity scaling under controlled addressing

- **Status: DESIGN REVISION 5 — ADOPTED BY THE LEAD FOR IMPLEMENTATION, CALIBRATION AND REHEARSAL (§25.12, Decision 1); NOT IMPLEMENTED YET, NOTHING RUN UNDER IT; THE REGISTERED RUN IS NOT DECIDED.** It redesigns the capacity line after revision 4's calibration returned to the human lead (§23) and the human lead chose to shift the grid down (§24). The independent review (Opus 5.5: READY AFTER M1–M7, no blocker; `docs/reviews/p10s1-revision5-2026-11-15/review/REVIEW.md`) and the lead's rulings (`LEAD_RULINGS.md` beside it) are applied in this text; §25.10 maps every finding to its change and §25.11 lists where the text differs from the reviewer's. The lead has still to check this application and take Decision 1 for revision 5 (§25.9). The lead's approval in §15 covered revision 4 and does not cover this revision. The code in `studies/p10s1/` and `configs/p10s1_capacity.toml` implements revision 4 and is not valid for revision 5. **SPEC: PENDING ASTRA REVIEW.** No registered seed has been observed.
- **Date:** 2026-11-15
- **Study code:** P10S1. Package `studies/p10s1/`. Config `configs/p10s1_capacity.toml`. Tests `tests/test_p10s1_*.py`.
- **Revision history.**
  - Revision 1: `ADR-0021-p10-s1-useful-capacity-scaling.md` (unchanged). Reviewed by Opus 5.5: **NOT READY**, 4 blockers, 11 majors, 17 minors — `adr-0021-review/REVIEW.md`, scripts and outputs beside it.
  - Revision 2: `ADR-0021-p10-s1-useful-capacity-scaling.rev2.md` (unchanged). It applied the review under the lead's rulings. Confirmation review by Opus 5.5: **READY AFTER LISTED TEXT EDITS**, K1–K7 — `adr-0021-review/CONFIRM.md`.
  - Revision 3 (this text) applies K1–K7 with the auditor's text and the auditor's bracketed values, and the lead's final rulings. §17 maps every finding to its change. §18 lists the lead's choices. §19 records how each conflict of revision 2 was closed. §20 lists what differs from the auditor's text.
  - Revision 4 applied the re-check of revision 3 (§21) and was implemented. Its calibration ran (46 runs, calibration draws only) and returned to the human lead (§23). Revision 4 with §22–§24 is kept unchanged as `docs/reviews/p10s1-revision5-2026-11-15/ADR-0021-rev4-with-s22-s24.md`.
  - **Revision 5 (the current text)** applies the human lead's choice of §24. §25 is its record; the arithmetic is in `docs/reviews/p10s1-revision5-2026-11-15/DESIGN_NOTES.md`. §15, §17–§24, the Addendum and every verbatim quotation are unchanged. Sections 17–21 describe revisions 2–4 and still name the old cells.
- **Origin.** The human lead's P10 milestone direction: three parallel, independent experiments (S0 addressing qualification, ADR-0020; S1 capacity, this ADR; S2 two-teacher transfer, ADR-0022).
- **Milestone question 1 (verbatim).** "Can increasing ArborLM's learned-memory capacity produce measurable gains in retained knowledge and useful capability without proportional increases in active inference work?"
- **Roles (study-specific).** Lead: Claude Fable 5.2. Specification review, implementation audit and recomputation from raw records: Opus 5.5, in a context separate from the implementation. Implementation: Sonnet 5.5. Inventory: Haiku 5.5. The model that actually ran each delegated task is recorded from session metadata. ADR-0012 stays not approved. **Astra review: NOT_PERFORMED.**
- **Relation to other work.** S1 does not wait for S0 and does not depend on S2. ADR-0017 Lanes A–D stay calibration blocked. P1–P9-I code, configs, records and ADRs are not edited.
- **Marking.** *(lead's choice)* marks a number or rule the lead chose; §18 collects them.

## 0. What S1 is a study of (lines 1 and 3 decided before any calibration; line 2 added in revision 5, after revision 4's calibration)

S1 registers **three separate result lines** (two until revision 5). None implies another.

1. **CAPACITY.** A smaller memory that is loaded (§8.2), and a larger memory that holds more useful information at matched updates and at matched compute. Labels: CAPACITY-POSITIVE, CAPACITY-NEGATIVE, CAPACITY-INCONCLUSIVE, and **CAPACITY NOT TESTED — NO LOADED CELL WITHIN BUDGET**, which is not a negative. Under oracle addressing, a positive step is close to foregone once the smaller cell is full (§25.4). The line is kept, with its thresholds unchanged, as a check of a necessary condition.
2. **SATURATION (new in revision 5, §8.10).** What a full store holds per slot at 256, 1,024 and 4,096 slots, and whether that amount keeps pace with the number of slots. The 256-slot cell is read for F-OQ only and is the lead's addition (§5.1). Labels: SATURATION-PROPORTIONAL, SATURATION-SUBPROPORTIONAL, SATURATION-INCONCLUSIVE, SATURATION NOT MEASURED. The dense control is read on the same full cells (§8.5).
3. **LEARNING EFFICIENCY.** A larger memory that reaches a fixed level of useful information in fewer updates and less compute. Labels: EFFICIENCY-POSITIVE, EFFICIENCY-NEGATIVE, EFFICIENCY-INCONCLUSIVE. Every efficiency verdict is printed with the row-movement ratio of §7.3.

The reading for milestone question 1 uses the capacity line, the saturation line and the dense labels (§8.7). It never uses the efficiency line.

**The registered memory sizes of the capacity line are 1,024, 4,096 and 16,384 slots. Capacity from 16,384 to 65,536 slots is not tested in S1.** That question goes to the proposed P10-I, which needs the human lead's review.

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

Calibration of revision 4 and its independent check (calibration draws, initialization seed 2191; **calibration, never results**; `results/p10s1-calibration-2026-11-15/`; `docs/reviews/p10s1-load-search-2026-11-15/CHECK_LOAD_SEARCH.md` and the `audit_*.out` files beside it):

13. F-OQ, useful bits per fact (ceiling 5.0), range over two draws and two panels:

    | Slots | Facts | Load | At 8,192 updates | At 16,384 | At 65,536 | Last doubling (32,768 → 65,536) |
    |---|---|---|---|---|---|---|
    | 4,096 | 8,192 | 2 | 4.37–4.54 | 4.81–4.85 | 4.96 | +0.03–0.04 |
    | 4,096 | 16,384 | 4 | 1.66–2.15 | 3.13–3.28 | 4.06–4.12 | +0.21–0.26 |
    | 4,096 | 32,768 | 8 | 0.30–0.42 | 0.96–1.14 | 1.89–1.94 | +0.29–0.33 |
    | 4,096 | 65,536 | 16 | 0.03–0.06 | 0.19–0.25 | 0.72–0.75 | +0.20–0.25 |
    | 16,384 | 8,192 | 0.5 | 4.99–5.00 | 5.00 | 5.00 | 0.00 |
    | 16,384 | 32,768 | 2 | 1.96–2.61 | 4.12–4.23 | 4.85–4.87 | +0.15–0.16 |
    | 16,384 | 65,536 | 4 | 0.23–0.37 | 1.44–1.71 | 3.49–3.54 | +0.64–0.71 |
    | 16,384 | 131,072 | 8 | 0.01–0.02 | 0.20–0.28 | 1.46–1.52 | +0.54–0.62 |

14. No cell was loaded within revision 4's run lengths: every cell was at its ceiling or still improving. By the letter of §8.2 as revision 4 wrote it, every cell was "plateaued and loaded" at 1,024–8,192 updates, before it had learned anything (the check, §1). Revision 5 closes that (§8.2).
15. **Extrapolations by the check, not measurements.** Over six curve families, 4,096 slots at eight facts per slot first meets the plateau rule between 131,072 and 393,216 updates, at about 1.9–2.3 bits per fact; with two consecutive passes required, most likely at 262,144–393,216 (range 196,608–524,288). The loads 4 and 8 at 4,096 slots converge to about 17–18 bits per slot under the constant-ratio family. In a hold-out test that family and the power law were pessimistic (they predicted slower saturation than was then seen) and the saturating exponential was the most accurate one step ahead.
16. Dense control, minimum Panel A accuracy at U_P over two draws, at rates 0.001 / 0.003 / 0.01: 0.091 / 0.443 / 0.998 at 8K/16K; 0.044 / 0.062 / 0.294 at 32K/64K (0.969 at 16,384 updates at 0.01). The best rate was the top of the grid at both sizes, so a higher rate was never tried.
17. Measured seconds per update (training wall; the task figure with the calibration's evaluations is in brackets): F-OQ 0.0093 (0.0099–0.0109) at 4,096 slots, 0.0153–0.0187 (0.0158–0.0259) at 16,384; H8 0.0075 (0.0082) and 0.0101 (0.0110); D-OQ 0.0235 (0.0245) at 16,384 and 0.071–0.077 (0.089–0.091) at 65,536; R2 0.0091–0.0188.
18. **Never run in S1:** anything at 1,024 slots; T-OQ at any size (it has not been timed either; the rehearsal has not run); D-OQ at 1,024 or 4,096 slots, at more than half a fact per slot, or at a rate above 0.01; any run beyond 65,536 updates.

Facts 13–18 are the basis of revision 5 and are declared in §25.3 as seen before the redesign.

## 2. Question, scope and hypotheses

**Question.** With addressing controlled, does a larger learned memory retain more useful information about a fixed set of facts than a smaller one, under matched budgets and against a dense map of equal parameters; does what a full store holds keep pace with its number of slots; and does a larger memory learn the same facts sooner?

**Scope.** Every memory arm is given the identity of the queried fact by an oracle (§3). S1 measures the store, not the interface.

Hypotheses. Each can fail.

- **H21-1 (capacity under load).** For the flat oracle-query memory, at a fixed fact set, a step to four times the slots is a capacity step (§8.2) when the smaller memory is loaded.
- **H21-2 (saturation).** When the smaller memory is not loaded, four times the slots does not change what is retained.
- **H21-3 (saturation in proportion; restated in revision 5).** At eight facts per slot, the useful information a full store holds grows at least 3.0 times per fourfold step in slots; that is, the store keeps at least three quarters of its bits per slot (§8.10). Revision 4 stated H21-3 on a diagonal at half a fact per slot up to 65,536 slots, which no longer exists; the factor 3.0 is unchanged.
- **H21-4 (not parameters alone; restated after review M1, extended in revision 5).** A dense map with the same parameter count and input does not retain more than the memory: not at the larger cell of a capacity step at matched updates or compute (DENSE AHEAD), and not at a loaded cell when both have run its full length (DENSE HOLDS MORE AT SATURATION), §8.5.
- **H21-5 (dependence).** The retained information disappears when values are shuffled or addresses are swapped.
- **H21-6 (counted work).** The tree and the flat memory read through a conventional index show capacity steps while their counted work per query at most doubles per fourfold step; the tree retains at least 0.97 of what the indexed flat memory retains.
- **H21-7 (key learning).** The hashed exact-address memory shows the same step pattern as the flat oracle-query memory.
- **H21-8 (learning efficiency).** At fixed facts, a memory with four times the slots reaches 3.0 bits per fact in at most half the updates and at most 0.8 of the compute.

**The lead's expectation for revisions 2–4, written after seeing facts 11–12 and before any S1 observation (kept as written; its cells are revision 4's).** The capacity line is most likely to print NOT TESTED or INCONCLUSIVE at loads up to 2, and the registered cell 32K/4K (load 8) is the most likely loaded cell. For H21-8 fact 5 suggests the opposite direction (larger memories learn more slowly); Study A separates slots from facts for the first time. Either line may be negative. A negative is recorded and kept.

**The lead's expectation for revision 5, written after seeing facts 13–18 and before any run under revision 5.**

1. *Capacity steps C1 and C2 (§5.1).* For F-OQ a CAPACITY verdict is expected wherever the smaller cell's plateau holds; the larger cells are already 1.9–2.4 bits per fact above what the smaller ones are extrapolated to hold. The check said so (its M4) and it is true of both loaded steps. Whether the plateau holds in all five replicates, and for T-OQ, is not known.
2. *Saturation in proportion (H21-3).* Nothing has been run at 1,024 slots, and no cell has been run to a plateau at any size. The lead has no confident expectation of the ratio. The 4,096-slot side is bounded below by revision 4's calibration (§8.10), so a negative needs a 1,024-slot slot to hold at least about 20 bits. Nothing has been run at 256 slots either, so the pair 256 → 1,024 is open at both ends.
3. *Dense control (H21-4).* If a slot holds 17–18 bits when full (an extrapolation), the store holds about 0.36 bits per trainable parameter. A dense map of equal size would need 0.83 bits per parameter to hold the whole fact set of a loaded cell. D-OQ reached 0.998 at 8K/16K at U_P where F-OQ at 8K/4K reached 4.37–4.54 bits. The lead considers DENSE AHEAD at U_P and DENSE HOLDS MORE AT SATURATION both live, and CAPACITY-NEGATIVE by clause (b) of §8.7 a real possibility. D-OQ has not been run at any cell where this is decided.
4. *Efficiency (H21-8).* The earlier expectation, that larger memories learn the same facts more slowly, is contradicted by fact 13 at 8,192 facts: the lead's reading of those curves on Panel A puts the 3.0-bit level at about 4,100–5,600 updates at 4,096 slots and 2,600–3,000 at 16,384, a ratio of 0.54–0.64. That is above the 0.5 the rule requires, and the larger cell costs about 1.6 times as much per update, so the expected verdict of step N2 is SAME or FASTER IN UPDATES ONLY. Step N1 has never been run.

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
4. **What it cannot support.** That a learned memory works autonomously; that the language model can address or use this capacity; that learned addressing would reach the same capacity (R1 is a reference, not a ceiling or a floor); useful capability beyond recall of the trained facts; anything about natural language. **Every positive label of S1 carries STORE ONLY; ORACLE-ADDRESSED and may not be printed without it.** This covers the outcome labels and every intermediate or descriptive positive: CAPACITY STEP, CAPACITY_SUPPORTED, CAPACITY-POSITIVE, EFFICIENCY_SUPPORTED, EFFICIENCY-POSITIVE, BEATS DENSE, KNOWLEDGE SCALES WITH MEMORY, TREE_AHEAD and the "storage half supported" reading; and, from revision 5, PROPORTIONAL STEP, SATURATION_PROPORTIONAL_ALL_PAIRS, SATURATION-PROPORTIONAL and STORE HOLDS MORE AT SATURATION.
5. D-OQ receives the same code tensor as F-OQ, so the dense comparison is at equal information.
6. D7 (the dense window of P9-I) is not run. It entered no rule. S1 therefore has no learned arm that addresses facts by itself unless lane L runs (§5.6); KNN-W (§5.5) is the non-oracle baseline.
7. **At 1,024 slots (revision 5)** T-OQ has four branches and reads two of them, 512 of the 1,024 keys, and F-OQ-IVF has four centroids. Both are defined by the same formulas. The tree is shallow there; the hierarchy label is not read at 1,024 slots (§8.5).

## 4. System common to all arms

- Frozen backbone as P9-I; no backbone parameter is trained. FP32, CPU only.
- Task, identifiers, records, contexts, templates and streams as ADR-0017 §4 (family 1), from the generator of `studies/p9/data.py`, with gate G1. The planted clusters are kept; no S1 rule uses them.
- Reads and additions **at answer sites only**. **Loss: cross-entropy over the 32 alphabet symbols at answer sites.** Scoring: most probable alphabet symbol, ties wrong. One AdamW, learning rate 0.003 (D-OQ's rate by §10.1 item 3), no weight decay, clip 1.0, constant rate. A batch is 16 contexts = 128 answer-site exposures.
- Key width 16, value width 32, top-8, temperature 0.2. No other width is run.
- New code only, in `studies/p10s1/`, importing `studies.p9` and `studies.p9i` unedited. New in S1: H8, the D-OQ of §5.3, the index read of §5.5, work counters, the evaluation of §7. F-OQ and R2 must reproduce the P9-I R1 and R2 forward and one training step bit for bit.

## 5. Design

### 5.1 The grid of facts and slots (revision 5)

Seven cells of the capacity grid, and one cell for the saturation line only. "8K/1K" means 8,192 facts in 1,024 slots. Load is facts per slot. The memory sizes are 1,024, 4,096 and 16,384 slots (the human lead's choice, §24). **No memory cell has 65,536 slots.**

| Facts \ Slots | 1,024 | 4,096 | 16,384 |
|---|---|---|---|
| 2,048 | **2K/1K** (2) | **2K/4K** (0.5) | — |
| 8,192 | **8K/1K** (8) | **8K/4K** (2) | **8K/16K** (0.5) |
| 32,768 | — | **32K/4K** (8) | **32K/16K** (2) |
| 131,072 (block S3; not funded) | — | — | *128K/16K* (8) |

Outside the grid: **2K/256** (2,048 facts in 256 slots, load 8), F-OQ only, for the saturation line.

- **Loaded cells:** 8K/1K and 32K/4K, the two grid cells with eight facts per slot. Each runs to its own length U_L, found by §10.1 item 0b. They are the smaller cells of the two loaded steps and the cells of the saturation line (§8.10).
- **Why two fact counts.** At a fixed 8,192 facts the 4,096-slot cell has two facts per slot and reached the ceiling in revision 4's calibration (§1 fact 13). It cannot be the loaded smaller cell of the second transition. The second transition therefore has its own row, 32,768 facts, where 4,096 slots again hold eight facts each.
- Every claim about memory size compares cells of one row, so facts and slots are not confounded. The saturation line compares rows on purpose and says so (§8.10).
- **Cell 2K/256 (saturation line only; the lead's addition, outside the sizes of §24).** F-OQ only, the 2,048 facts and training stream of the row of 2,048 facts, in 256 slots (load 8). T-OQ is not defined at 256 slots and F-OQ-IVF would read every key, so neither is run or read there. The cell enters no capacity step (2K/256 → 2K/1K is not a step), no efficiency step, no dense label and no seed block. Its run length U_L is found by §10.1 item 0b for F-OQ alone, on both calibration draws, with the candidates and ceiling of 8K/1K ({65,536, 98,304, 131,072, 196,608, 262,144}; ceiling 262,144). If F-OQ has no U_L there, the pair 256 → 1,024 is fixed as NOT FULL and printed '256 NOT MEASURED — NOT FULL WITHIN CEILING'; this does not return to the human lead. Snapshots as for a loaded cell. REF and DEP as for its row. Gates G1, G2, G4 (restoration), G5, G6 and G7 (W = 16·256 + 1,280 = 5,376) apply. It is reported to the human lead as the lead's addition (§25.9).
- **Block S3** is the cell 128K/16K (131,072 facts), for F-OQ only: the saturation cell of 16,384 slots. **It is not funded (the lead's ruling 2) and is not in the registered matrix.** Its specification is kept in §10.1 item 4 and §10.3 so that a later study can take it up. The saturation line prints '16,384 NOT MEASURED — NOT FUNDED'.
- No rule adds a row, changes a load or changes a size. The overload-row rule of revision 4 is withdrawn.

**Steps (same facts, four times the slots):**

| Step | Cells | Load | Transition | Kind |
|---|---|---|---|---|
| C1 | 8K/1K → 8K/4K | 8 → 2 | 1K→4K | loaded step |
| N1 | 2K/1K → 2K/4K | 2 → 0.5 | 1K→4K | control step |
| C2 | 32K/4K → 32K/16K | 8 → 2 | 4K→16K | loaded step |
| N2 | 8K/4K → 8K/16K | 2 → 0.5 | 4K→16K | control step |

- A **loaded step** tests H21-1: its smaller cell is meant to be full. A **control step** tests H21-2 at two facts per slot, where the smaller cell is expected to reach the ceiling, and carries the efficiency line (§8.8).
- N2 is revision 4's step A1, unchanged. C2 is revision 4's step B1 with a new run length for its smaller cell and a row U_P set by rule (§5.4). C1 and N1 are new, and so is everything at 1,024 slots.
- Every verdict rule of §8.2 is applied to all four steps. The names "Study A" and "Study B" of earlier revisions are no longer used: the rows of 2,048 and 8,192 facts are the fixed-fact comparisons, and the saturation line replaces Study B.

### 5.2 What more slots can buy when the facts are fixed

1. **Less interference** → the capacity line (§8.2–§8.7).
2. **Faster or slower learning** → the efficiency line (§8.8).
3. **Robustness.** Accuracy retained when a random 5% or 20% of value rows are zeroed, and under Gaussian value noise of 0.1 and 0.5 of the row RMS (three seeded masks each). Descriptive label, §8.6.
4. **Redundancy.** Length of a fact's minimal support; facts per slot (§7.3). Descriptive.

Generalization across facts is not among them (§7.2).

### 5.3 Parameter control

1. **No iso-parameter memory cell is run.** In this read path a slot's contribution is W_o·v_s, a vector of width 32. Value widths above 32 add only redundant parameters; widths below 32 restrict the rank. Neither is "the same parameters in fewer slots". A slot has 48 expressive parameters, and "more slots" cannot be separated from "more store parameters" inside the memory. (Review M1; revision 1's wide-value cells are withdrawn.)
2. **Total trainable parameters are controlled by D-OQ at equal parameter count.** D-OQ: the oracle code (the same tensor as F-OQ's) → `w1 [h, 16]` with bias `b1 [h]` → exact GELU → `w2 [32, h]` → sigmoid(gate) (gate initialized at −2), added at the answer site. Initialization is the conventional one for a fan-in layer: `w1`, `b1` ~ U(−1/4, 1/4), `w2` ~ U(−1/√h, 1/√h), from seeded generators. h is set so that 49h + 1 equals F-OQ's parameter count within 0.1%. Same loss, optimizer, clip and updates. Its learning rate is chosen in calibration (§10.1 item 3).
3. D-OQ is run at the larger cell of every step (2K/4K, 8K/4K, 8K/16K, 32K/16K) and at both loaded cells (8K/1K, 32K/4K), where it runs the cell's full length U_L (§8.5, dense at saturation). Six cells.

### 5.4 Budget regimes and run lengths (revision 5)

Every cell is trained once, at a constant learning rate, and read at snapshots. A snapshot is a valid shorter run (gate G4).

- **U_P is set per row, by rule** (§10.1 item 1): the smallest of {8,192, 16,384, 32,768} at which, on both calibration draws and both panels, F-OQ reaches a_use ≥ 0.90 at the row's larger step cell and R2 reaches a_use ≥ 0.95 at the row's reference cell. It is not tuned in any other way. Revision 4 fixed U_P = 8,192 for its own rows and wrote this rule for an added row only. At 8,192 updates the cell 32K/16K was at 1.96–2.61 bits on the calibration draws (§1 fact 13), about what 32K/4K is extrapolated to hold when full, so step C2 could not be read there (§25.6).
- **Run lengths U_run.** A loaded cell runs U_L, for every arm trained at it, D-OQ included; 2K/256 runs its own U_L, for F-OQ. Every other memory or dense cell runs 6·U_P of its row, at every slot count *(lead's choice; revision 4 ran 6 / 4 / 2·U_P by size; 6 at every size lets the dense matched-compute readout exist for every arm, §25.7)*. R2 runs U_P of its row.
- **Snapshots:** U_P × {1/16, 1/8, 1/4, 1/2, 1, 2, 4} up to the run length, U_run/2, U_run, and every matched-compute snapshot. A loaded cell also has a snapshot at 32,768, at 49,152 and at every candidate of §10.1 item 0b up to U_L.
- **MU — matched updates:** both cells at U_P.
- **ME — matched exposures per fact.** Within a row MU and ME are the same readout. No rule compares rows at matched exposures.
- **MC — matched training compute.** The costlier cell is read at U_P; the cheaper at the smallest snapshot of {1, 1.25, 1.5, 2, 2.5, 3, 4, 6}·U_P whose cumulative cost is at least the costlier cell's. Cost is measured two ways: single-thread process CPU-seconds per update from the isolated timing part of the rehearsal (§10.2), and analytic multiply-adds per update (§22 M6). **The larger of the two multipliers is used**, and both are fixed in the freeze record. If the required snapshot exceeds the cheaper cell's run length the comparison is **MC-SHORT** and counts as not established. **If the two cost measures disagree on which cell of a pair costs more (MC-AMBIGUOUS), the pair is read in the direction that favours the comparator** *(revision 5; the reviewer's rule, adopted by the lead; it replaces §22 (i) for this revision, §25.10)*. The cell whose advantage would be claimed (the larger cell on the capacity line; the memory arm in the dense labels) is treated as the costlier and read at U_P. The other cell (the smaller cell; D-OQ) is read at the smallest grid snapshot whose multiplier is at least the largest of r and 1/r over both measures, r being the ratio of the two cells' costs per update in a measure. MC-AMBIGUOUS is then printed as an annotation, and the pair counts as established. If that snapshot exceeds the other cell's run length the pair is MC-SHORT. The rule is fixed before item 0a of §10.1, when no cost direction at the new sizes is known.
- **SAT — saturation:** the smaller cell at the best of its snapshots up to U_run, with the plateau rule of §8.2.
- The registered run records process CPU-seconds per snapshot. The ratio between two readouts compared under MC is reported; above 1.25 it is flagged **MC-MISMATCH**. It changes no class: the registered run has six workers contending, and a larger cell slows more under contention than a small one.

**Which regimes a claim needs, and why.**

1. Every capacity and efficiency class compares cells of one row. Updates and exposures per fact are then equal by construction.
2. A capacity step needs **MU (= ME), MC and SAT, all three.** MU alone gives the larger memory more compute. MC removes that. SAT removes "the smaller memory is only slower".
3. The efficiency line uses updates and compute only, and never the word capacity.
4. The saturation line (§8.10) matches no budget. It compares cells that have each stopped improving by the plateau rule, each at its own U_L. A cell that has not stopped is NOT FULL and gives no ratio. Updates, exposures per fact and compute to U_L are printed beside every value.
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
6. Lane L changes no S1 class or outcome. It is considered only after the cuts of §10.3 are settled and is added only if C_need with it is then at most C_max (§10.3); no cut is made to admit it.
7. In the expected timeline (ADR-0020 §9.2) S1 freezes before S0's Q1 is recomputed, so the lane is expected to be omitted; 'learned addressing evaluated separately if qualified' is then met only by a later study that needs the human lead's review.

## 6. Matrix, replicates and seeds

### 6.1 Trained cells

| Arm | Grid cells | Configurations |
|---|---|---|
| F-OQ | all seven, and 2K/256 | 8 |
| T-OQ | all seven | 7 |
| H8 | all seven | 7 |
| D-OQ | 2K/4K, 8K/4K, 8K/16K, 32K/16K (the larger cell of each step); 8K/1K, 32K/4K (the loaded cells) | 6 |
| R2 | 2K/4K, 8K/16K, 32K/32K | 3 |
| **Per replicate** | | **31** |
| **Registered total, 5 replicates** | | **155** |
| Seed block (§6.2), draw 1 (unless cut 2 of §10.3 removes it) | F-OQ × the 7 grid cells × 2 extra seeds | +14 |
| Seed block, draw 2 (only if the cap rule admits it) | as above | +14 |
| Block S3 (not funded; not run) | F-OQ at 128K/16K × 5; R2 at 128K/128K × 5 | 0 |
| Lane L (only if qualified and it fits) | F-LA × 3 cells × 5 | +15 |
| Calibration of revision 5 (§10.1) | load search 10 (8 and the two F-OQ runs at 2K/256), row U_P 12, H8 reported 8, dense rate 40 | 70 runs, and the timing preview |

- **R2 at 32K/32K** is a table of 32,768 dedicated rows, one per fact. It is the reference rung of the row of 32,768 facts (revision 4 used 32K/64K). It is not a memory size of the study and enters no step. *(lead's choice; §25.8 question 6)*
- Revision 4 had 30 configurations and 150 cells on a different grid; the 31 and 155 here are not comparable with them cell by cell.

Evaluation only, no training: F-OQ-IVF, KNN-W, KNN-W-IVF, DICT, no-memory, unseen-fact control. No cell depends on another.

### 6.2 Replicates

- **Five replicates; never reduced.** Replicate r is data draw r with initialization seed 2100 + r. Each draw is a complete independent data set: a fact table of 32,768 facts whose first 8,192 and first 2,048 are the smaller sets, a training stream per fact count, Panels A and B, held-out template panels H1 and H2, the unseen-fact control.
- **Pairing.** Within a replicate and row, every slot count and arm sees the same facts and the same training contexts in the same order. Only the output projection and the gate share an initialization across slot counts; key and value tables are drawn per size.
- **Seed block (descriptive, enters no rule).** On draw 1, F-OQ is also trained at initialization seeds 2111 and 2121 on all seven cells, unless cut 2 of §10.3 removes the block. If C_need with it is at most C_max (§10.3), the same is done on draw 2 at seeds 2112 and 2122; the decision is made by that rule and recorded before the freeze. The report gives, per cell and readout, the spread of i over the three seeds of a draw against the spread over the five draws, and states which dominates.
- **Statistical meaning.** If a paired condition held with probability at most 1/2 in each replicate, "all five" has probability at most 1/32 = 0.031 and "at least 4 of 5" at most 6/32 = 0.19. "All five" is required for every positive step. 'At least 4 of 5' is used for negatives, ceilings and DENSE AHEAD. Every positive condition of a capacity or efficiency verdict, class or outcome, BEATS DENSE included, needs all 5. The hierarchy labels of §8.5 are descriptive and use at least 4 of 5.
- **At the level of the outcome** the bound is weaker. Three arms can each reach CAPACITY_SUPPORTED through a step of the first transition (C1 or N1), so by the union bound the chance of some positive step class under that null is at most 6/32 = 0.19 (crude: the arms share data and a second transition is also required). Replicates protect against noise, not against systematic confounds.
- Sampling error within a cell is small beside the thresholds: with 8,192 facts the standard error of an accuracy is at most 0.006, about 0.03 bits per fact.
- One backbone (B101/O301).

### 6.3 Seeds and partitions

- Registered data seed sets `p10s1-draw-1` … `p10s1-draw-5`, bases 210001, 210101, 210201, 210301, 210401; each set uses base + i as the P9 generator does (14 names; null seeds at +20 and +30). H8 hash seed base + 40. Derangement and mask seeds base + 50 … 59. Index seed base + 60. Initialization seeds 2101–2105; seed block 2111, 2121, 2112, 2122.
- Calibration draws: bases 219001 and 219101, initialization seed 2191. Rehearsal draw: base 219201, initialization seed 2192. Unit tests: **921001–921999**.
- **Revision 5's calibration** uses the same two calibration draws, with initialization seed 2191 on draw 1 and **2193** on draw 2 *(lead's choice)*. The two runs of a calibration cell then differ in initialization as well as in data; revision 4's calibration used one initialization seed for both draws, and the check noted that this under-samples what the registered replicates vary (its §7 item 2). 2193 is added to the seeds gate G9 declares. The fact table of a draw has 32,768 facts, whose first 8,192 and 2,048 are the smaller sets; 2K/256 uses the 2,048-fact set.
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
- **Separability:** nearest-neighbour cosine between oracle codes; share of facts with a neighbour above 0.8; overlap of the top-8 sets of a fact and its nearest neighbour; share of facts with a private slot. For T-OQ and F-OQ-IVF: share of the exhaustive top-8 found among the candidates. The first four figures are also computed at each saturation cell (2K/256, 8K/1K, 32K/4K) and printed beside every ρ of §8.10.
- **Row movement.** Per cell, the cumulative movement of value rows on updates with and without their own gradient. **Every GAIN WITHIN BUDGET, BEHIND WITHIN BUDGET, FASTER and SLOWER verdict is printed with the ratio of that movement between the two cells.** No class depends on it. Under AdamW a row that rarely receives a gradient still moves, and rows receive gradients less often in a larger memory (ADR-0017 §5.5). SAT is the control for the capacity line; it is not a control for the efficiency line, which is why the ratio is printed there. No row-lazy arm is run.

### 7.4 Active memory work per query

Counted by instrumented counters in the forward. Gate G7 requires the counters to equal the formulas.

| Arm | Key scores K (each 16 wide) | Value rows V | W = 16·K + 32·V + 1,024 (output projection) |
|---|---|---|---|
| F-OQ | N | 8 | 17,664 / 66,816 / 263,424 (at 1,024 / 4,096 / 16,384 slots); 5,376 at 256 slots |
| F-OQ-IVF | N/256 + candidates (at least 512) | 8 | measured per query; about the T-OQ figure |
| T-OQ | N/256 + 512 | 8 | 9,536 / 9,728 / 10,496 |
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

After the outputs of revision 5's calibration are written, only these may change before the freeze: U_L of each loaded cell and U_P of each row, by the rules of §10.1; D-OQ's learning rates; the MC snapshots from the timing rule; the seed block on draw 2; whether 2K/256 is run (§10.1 item 0b); the cuts of §10.3; the cap by the rule of §10.3; lane L by §5.6. Anything else is a new revision.

### 8.1 Gates

**Engineering gates (a failure is S1-ENGINEERING-FAILURE):**

- **G1** generator checks per draw and fact count (ADR-0017 §4.6).
- **G2** chance: the no-memory baseline on the three fact sets and the unseen set, both panels, five draws: 40 tests, each inside the exact binomial central interval of level 1 − 0.001/40 around 1/32 ([34, 100], [192, 325], [894, 1,159]). That interval is "chance" in every rule.
- **G4** determinism and identity: stream hashes; checkpoint restoration bit for bit for one cell of every arm at real size; train-restore-continue equals the straight run; F-OQ and R2 identical to P9-I's R1 and R2; logits on the backbone's corpus rows identical to the frozen backbone's; the index of §5.5 is identical on rebuild.
- **G5** gradient reach, **for every one of the 31 configurations at its real facts and slots, on a batch of that cell's own training stream:** every trainable group receives a non-zero gradient; in H8 exactly the hashed rows do; R2's table covers every fact of the cell; nothing reaches the backbone.
- **G6** controlled-addressing integrity: query and selection of F-OQ, T-OQ, H8 and R2 are unchanged when the context is permuted and when the answer table is replaced; D-OQ's input tensor has the same hash as F-OQ's codes; no forward takes the answer as input.
- **G7** work counters equal §7.4. **G8** D-OQ's parameter count within 0.1% of F-OQ's. **G9** seeds (§6.3).
- **The gates stage runs at real size on the rehearsal draw before the freeze** and again on registered seeds before training. A harness error is reported separately from a gate failure.

**Scientific gates (a failure is a recorded result):**

- **REF**, per replicate and row: R2 a_use ≥ 0.95 on both panels at the row's U_P, at 2K/4K for the row of 2,048 facts, at 8K/16K for the row of 8,192, at 32K/32K for the row of 32,768. 2K/256 uses the reference of the row of 2,048 facts. If it fails, the replicate is NOT_EVALUATED for the row.
- **DEP**, per memory cell with a_use ≥ 0.25, **at every snapshot a rule reads**: memory disabled gives chance; value shuffle gives chance; a_use ≥ 0.95 × raw accuracy; unseen facts at chance (else LEAKAGE). H1 and H2 are not part of DEP (§7.2).

### 8.2 Capacity line: step verdict in one replicate

For an arm and a step N → 4N at fixed facts, on Panels A and B separately.

- Δ_MU = i(4N; U_P) − i(N; U_P). Δ_MC = i(4N; U_P) − i(N; U_MC).
- **Δ_SAT = i(4N; U_P) − i\*(N; U_run).**
- **Plateaued:** i\*(c; U_run) − i\*(c; U_run/2) ≤ 0.10 bits per fact *(lead's choice)*, **and i\*(c; U_run/2) ≥ 0.473 bits per fact** (a_use ≥ 0.25), for either cell on its own snapshots. The second condition is new in revision 5. An a_use of 0.25 is the floor below which DEP is not evaluated (§8.1): a cell under it has stored nothing that has been checked, and cannot be called flat. Without the condition every calibration cell met the rule at 1,024–8,192 updates, before it had learned (§1 fact 14). It introduces no new number, and it changes the plateau status of no calibration cell read at a run length revision 4 registered. A cell that meets the gain condition but not the floor is printed FLAT BELOW THE DEP FLOOR, not as still improving.
- **Loaded** (a smaller cell): plateaued and i\*(N; U_run) ≤ 4.0 bits per fact (a_use ≤ about 0.896) *(lead's choice)*. This one threshold is used for CAPACITY (row 4), NULL (row 8), FLAT, NOT LOADED (row 9) the load search (§10.1 item 0b) and the saturation line (§8.10).
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

### 8.4 Capacity line: arm class (F-OQ, F-OQ-IVF, T-OQ, H8; steps C1 and N1 in the transition 1K→4K, C2 and N2 in the transition 4K→16K; first match wins)

| Order | Arm class | Rule |
|---|---|---|
| 1 | NOT_EVALUATED | every step of one transition is NOT_EVALUATED |
| 2 | DEPENDENCE_FAILED | any step is DEPENDENCE_FAILED |
| 3 | CAPACITY_SUPPORTED | a CAPACITY STEP in each transition; no step REVERSED; a_use ≥ 0.80 at 32K/16K at its row's U_P in all 5 replicates *(lead's choice of 0.80, unchanged; read at 32K/16K because 32K/64K no longer exists. Since U_P of this row is the smallest value at which F-OQ reaches a_use ≥ 0.90 at this same cell on the calibration draws (§10.1 item 1), the floor is implied by the U_P rule up to the spread between calibration and registered replicates, and tests nothing beyond that spread; §25.6)* |
| 4 | CAPACITY_ONE_TRANSITION | at least one CAPACITY STEP, not row 3 |
| 5 | NOT_TESTED_BY_LOAD | in some transition every step is NOT LOADED |
| 6 | CAPACITY_NOT_SUPPORTED | at least one step per transition is NO GAIN or REVERSED, and no step is a CAPACITY STEP |
| 7 | INTERMEDIATE | otherwise |

H8's classes carry **UNDERTRAINED-AT-U_P** at any cell where its calibration accuracy was below 0.90 at U_P. At a cell where H8 was not calibrated, its classes carry H8 NOT CALIBRATED AT cell (2K/1K, 8K/1K and 32K/4K).

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
- **Matched compute on the new sizes (revision 5; the ruling of §22 M5 stands).** The analytic multipliers of D-OQ over an arm are at most 2.5 for F-OQ, 5.1 for T-OQ and 5.4 for H8 at 16,384 slots (`rev5_arithmetic.out` §2), so the matching snapshot is at most 6·U_P and every arm's cell now runs that long (§5.4). On the analytic measure every matching snapshot exists. The pair is established only if the CPU-time measure of §10.2 agrees on which cell costs more, or by the comparator rule of §5.4 when it does not. Where the analytic difference is small (T-OQ and H8 between sizes, 1.01–1.04; D-OQ against an arm at 1,024 slots, 1.19–1.28) the CPU direction decides, and a disagreement gives MC-AMBIGUOUS. Under the rule of §5.4 the pair is then read with D-OQ at the later snapshot and the arm at U_P, which is the harsher reading for the store, and the annotation is printed. If T-OQ's measured cost exceeds D-OQ's and the snapshot that rule requires lies beyond D-OQ's run length, the pair is MC-SHORT, the label of §22 M5 is printed, and the "storage half supported" reading is reachable only through F-OQ-IVF (§25.8 question 11).

**Dense at saturation (new in revision 5), at each loaded cell (8K/1K, 32K/4K), the arm and D-OQ both read at the cell's run length U_L.** d_sat = i\*(arm; U_L) − i\*(D-OQ; U_L) and r_sat = F·i\*(arm; U_L) / F·i\*(D-OQ; U_L), per panel and replicate. First match wins:

| Order | Label | Rule |
|---|---|---|
| 1 | **DENSE HOLDS MORE AT SATURATION** | d_sat ≤ −0.25 in at least 4 replicates (a replicate counts if either panel satisfies it, §22 (h)), at any loaded cell |
| 2 | **STORE HOLDS MORE AT SATURATION** | r_sat ≥ 1.10 in **all 5** replicates on both panels at every loaded cell; D-OQ is plateaued (§8.2) at each of those cells in all 5; and D-OQ's cost per update is at least the arm's in both cost measures of §5.4 |
| 3 | **SAME AT SATURATION** | otherwise. When row 2 fails only because D-OQ is not plateaued, the label is printed with DENSE STILL RISING, or with DENSE NOT LEARNED where D-OQ fails the plateau only by the floor of §8.2; when it fails only on the cost condition, with DENSE NOT ESTABLISHED AT MATCHED COMPUTE |

- The numbers are those of DENSE AHEAD and BEATS DENSE (−0.25 bits per fact; a ratio of 1.10), unchanged. No new number is introduced.
- **Why equal updates suffice.** Where D-OQ costs at least as much per update as the arm, D-OQ at U_L has had at least the arm's compute. i\* never falls as updates grow, so a store that is ahead at equal updates is ahead at matched compute as well. A dense lead at equal updates might shrink at matched compute; it blocks all the same, as any single reading does in the rule above.
- **DENSE HOLDS MORE AT SATURATION counts as DENSE AHEAD** for the arm in rows 3 and 4 of §8.7 and in the milestone reading. This makes CAPACITY-POSITIVE harder to reach and CAPACITY-NEGATIVE by clause (b) easier. It is stated here so that it can be weighed (§25.5).
- D-OQ's rate at a loaded cell is chosen on that cell at 65,536 updates (§10.1 item 3), not at U_L. STORE HOLDS MORE AT SATURATION is therefore a statement about one dense family with a rate chosen early in the run (§12).
- STORE HOLDS MORE AT SATURATION carries STORE ONLY; ORACLE-ADDRESSED.

**Active work, per CAPACITY STEP:** SUBLINEAR (analytic; measured for F-OQ-IVF, §7.4 rule 4) or LINEAR KEY SCORING (§7.4).

**Hierarchy:** T-OQ against **F-OQ-IVF** at equal candidate count, on I_use at 8K/4K and 32K/16K at the row's U_P (the larger cells of the loaded steps; revision 4 read 8K/16K and 32K/64K). TREE_AHEAD if the ratio is ≥ 1.03 in at least 4 replicates at both cells; TREE_COMPETITIVE if ≥ 0.97 in at least 4 replicates at both cells; otherwise TREE_BEHIND. T-OQ against exhaustive F-OQ is printed beside it.

**Conventional retrieval:** CONVENTIONAL RETRIEVAL SUFFICES if KNN-W's or KNN-W-IVF's i is within 0.25 of the arm's, or above it, on both panels in at least 4 replicates at 32K/16K (each evaluated and printed; KNN-W depends on the facts, not on the slots). DICT DOMINATES ON THIS TASK is always printed.

**Key learning:** KEY-LEARNING-LIMITED if H8 is CAPACITY_SUPPORTED and F-OQ is not.

### 8.6 Descriptive labels (enter no class)

- **Study B is replaced by the saturation line (§8.10), which is a registered line and not a descriptive label.** Revision 4's label KNOWLEDGE SCALES WITH MEMORY was read on a diagonal at half a fact per slot up to 65,536 slots, which no longer exists. Its growth factor of 3.0 per fourfold step is kept as the saturation line's threshold. Its accuracy floor of 0.85 cannot apply to a full cell (about 0.6 is expected there) and is not used; MEMORY-ATTRIBUTED is not used.
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
| 5 | **CAPACITY NOT TESTED — NO LOADED CELL WITHIN BUDGET** | for F-OQ and for T-OQ, every step is NOT LOADED; or the human lead directed, after the load calibration, that the study run with a transition that has no loaded cell (§10.1 item 0b), in which case the label is fixed in the freeze record for that transition (§22 m13) |
| 6 | **CAPACITY-INCONCLUSIVE** | otherwise; the reason is printed: NOT_EVALUATED, DEPENDENCE_FAILED, NOT_TESTED_BY_LOAD (which transition), ONE TRANSITION ONLY (which), INTERMEDIATE |

- **Reachability (revision 5).** On the registered grid clause (a) cannot be reached for F-OQ on what was seen and extrapolated (NO GAIN and NULL need a loaded smaller cell whose step is flat, §25.4; REVERSED needs the larger cell behind at its full run length). CAPACITY-NEGATIVE can therefore arise only from clause (b), that is from the dense labels.
- **Printed label:** CAPACITY-POSITIVE [STORE ONLY; ORACLE-ADDRESSED; WITHIN REGISTERED RUN LENGTHS; 1,024 TO 16,384 SLOTS, 16,384→65,536 NOT TESTED; arm(s); BEATS DENSE or DENSE MATCHES, with D-OQ's a_use; the dense-at-saturation label; the saturation outcome with bits per slot at each size; active-work label; hierarchy label; conventional-retrieval label; S0 status (K7(c)); learned-address lane status]. Every capacity outcome, positive or not, is printed with "16,384→65,536 NOT TESTED".
- H8 alone cannot give CAPACITY-POSITIVE: the label requires learned keys *(lead's choice)*. Its class is printed beside the outcome.
- Row 5 is not a negative and not a positive. It says the registered sizes and run lengths could not load the store.
- **Reading for milestone question 1, fixed now.** S1 tests the storage half of question 1 under oracle addressing, on the capacity line with the saturation line and the dense labels, and never on the efficiency line.
  - **"Storage half supported, as a necessary condition, from 1,024 to 16,384 slots"** only if all of the following hold for one arm whose counted work is SUBLINEAR (T-OQ, or F-OQ-IVF by §7.4 rule 4): the capacity outcome is CAPACITY-POSITIVE for that arm; the arm is not DENSE AHEAD, the dense-at-saturation label of §8.5 included; its dense matched-compute reading is established (§22 M5); its saturation class is SATURATION_PROPORTIONAL_ALL_PAIRS (§8.10); and the hierarchy label comparing T-OQ with F-OQ-IVF (§8.5) is printed with it. It means: given the identity of the fact, this store retained more trained random facts as it grew, within the registered run lengths, at bounded counted work; when full it kept at least three quarters of its bits per slot per fourfold step over the sizes measured, which the label names; and a dense map of equal size and input was not ahead by 0.25 bits per fact or more in 4 of 5 replicates, at matched updates, at matched compute or when both had run the full length. It says nothing about addressing by the model, about use of the store by a language model, about useful capability beyond recall of the trained facts, or about any size above 16,384 slots. (Revision 5 adds the saturation and dense-at-saturation conditions and the size range to the wording the confirmation review supplied; §25.2.)
  - **"Capacity steps shown; proportional saturation not shown"** if CAPACITY-POSITIVE holds for such an arm, it is not DENSE AHEAD, and its saturation class is not SATURATION_PROPORTIONAL_ALL_PAIRS. The class is printed.
  - **"Capacity shown; sublinear active work not shown"** if CAPACITY-POSITIVE holds only for exhaustive F-OQ.
  - **"Storage half not supported for this store, backbone, task and budget"** if CAPACITY-NEGATIVE.
  - **"Not tested"** or **"not established"** for CAPACITY NOT TESTED or CAPACITY-INCONCLUSIVE.
  - Every reading is printed with S0's status line of K7(c).
- **Independence.** No line of S1 uses, implies or depends on TRANSFER-POSITIVE or SYSTEM-POSITIVE. S1's contribution to SYSTEM-POSITIVE is descriptive input only: the three outcomes with their annotations, the cost table, and the sentence "addressing was supplied by an oracle".

### 8.8 Efficiency line

**Steps (revision 5; the line is kept and adapted).** The efficiency line reads the control steps only: N1 (2K/1K → 2K/4K) in the transition 1K→4K and N2 (8K/4K → 8K/16K) in the transition 4K→16K. The loaded steps C1 and C2 are not read on this line. Their smaller cells are expected (an extrapolation, §1 fact 15) to stop near 2.0–2.3 bits per fact, below i_T = 3.0, so the only verdicts they could give are REACHED ONLY BY THE LARGER and NOT_ASSESSED, and the first would report a capacity difference under the name of efficiency. Every rule and threshold below is unchanged. U_run in this section is 6·U_P of the row. N2 was run on the calibration draws as revision 4's step A1; what was seen is in §2 and §25.3.

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
| 3 | **EFFICIENCY-POSITIVE** | F-OQ or T-OQ is EFFICIENCY_SUPPORTED and is not DENSE FASTER. Printed as EFFICIENCY-POSITIVE [STORE ONLY; ORACLE-ADDRESSED; SIZES 1,024–16,384; arm(s); row-movement ratios; dense label; S0 status (K7(c))]. Every efficiency outcome is printed with SIZES 1,024–16,384 |
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
8. Inconclusive on any line → no decision on that line.
9. SATURATION-SUBPROPORTIONAL → what a slot holds falls as the store grows; any scaling plan must budget for it, and the cause (the shared output projection, interference between keys, or crowding of the fixed width-16 oracle codes) is the next question.
10. SATURATION-PROPORTIONAL → the same measurement at 16,384 slots and above, which S1 does not fund, is the next question, for P10-I.
11. DENSE HOLDS MORE AT SATURATION → per parameter, the dense map is the better store on this task; whatever the memory offers is then in its counted work and its sparse updates, and a scaling plan must say so.
12. Whatever the outcome, capacity from 16,384 to 65,536 slots stays untested and is proposed for P10-I.

### 8.10 Saturation line (new in revision 5)

**What is read.** The saturation cell of a size N is the registered cell with eight facts per slot: 2K/256 at 256 slots (F-OQ only), 8K/1K at 1,024 and 32K/4K at 4,096. The cell of 16,384 slots, 128K/16K, is block S3 and is not funded. For an arm, replicate and panel, S(N) = F · i\*(cell; U_L) bits and b(N) = S(N)/N bits per slot. A saturation cell is **full** on a panel if it is loaded there by §8.2: plateaued, and i\* ≤ 4.0. b(N) is printed for every arm, size, replicate and panel, with the last doubling's gain and whether the cell is full.

**Pair verdict in one replicate, for the sizes N and 4N.** ρ = S(4N) / S(N). First match wins.

| Order | Verdict | Rule |
|---|---|---|
| 1 | NOT_EVALUATED | REF fails for either row, or LEAKAGE in either cell |
| 2 | DEPENDENCE_FAILED | either cell fails DEP at a snapshot up to its run length |
| 3 | NOT FULL | either cell is not full on either panel |
| 4 | PROPORTIONAL | ρ ≥ 3.0 on both panels |
| 5 | SUBPROPORTIONAL | otherwise: ρ < 3.0 on at least one panel |

**Pair class over the five replicates (first match wins; the denominator is always 5):** NOT_EVALUATED (at least 2 replicates); DEPENDENCE_FAILED (at least 2); NOT FULL (at least 2); PROPORTIONAL STEP (PROPORTIONAL in all 5); SUBPROPORTIONAL STEP (SUBPROPORTIONAL in at least 4); MIXED otherwise.

**Registered pairs.** 256 → 1,024 for F-OQ only; 1,024 → 4,096 for F-OQ, F-OQ-IVF, T-OQ and H8. F-OQ's arm class reads both pairs; every other arm reads one. The printed outcome names the pairs read for each arm.

**Arm class (first match wins):** SATURATION_NOT_MEASURED (every registered pair of the arm is NOT FULL or NOT_EVALUATED); DEPENDENCE_FAILED (some registered pair is DEPENDENCE_FAILED); SATURATION_DOES_NOT_SCALE (some registered pair is a SUBPROPORTIONAL STEP); SATURATION_PROPORTIONAL_ALL_PAIRS (every registered pair is a PROPORTIONAL STEP); INTERMEDIATE otherwise.

**Saturation outcome (first match wins; rows 1–2 of §8.7 apply first):**

| Order | Outcome | Rule |
|---|---|---|
| 3 | **SATURATION-PROPORTIONAL** | F-OQ, T-OQ or F-OQ-IVF is SATURATION_PROPORTIONAL_ALL_PAIRS. Printed as SATURATION-PROPORTIONAL [STORE ONLY; ORACLE-ADDRESSED; EIGHT FACTS PER SLOT; FULL = PLATEAU RULE WITHIN REGISTERED RUN LENGTHS; arm(s), with the pairs read for each; "16,384 NOT MEASURED — NOT FUNDED"; "256 NOT MEASURED — NOT FULL WITHIN CEILING" where it applies; b(N) per size with its range over replicates; the separability figures of §7.3 at each saturation cell; the dense-at-saturation label; S0 status (K7(c))] |
| 4 | **SATURATION-SUBPROPORTIONAL** | F-OQ and T-OQ are both SATURATION_DOES_NOT_SCALE |
| 5 | **SATURATION NOT MEASURED** | F-OQ and T-OQ are both SATURATION_NOT_MEASURED |
| 6 | **SATURATION-INCONCLUSIVE** | otherwise, with the reason. An arm class of DEPENDENCE_FAILED gives SATURATION-INCONCLUSIVE with reason DEPENDENCE_FAILED |

- **The threshold and its reason.** 3.0 is the growth factor H21-3 has carried since revision 1, fixed before any S1 record of any kind existed. ρ ≥ 3.0 is the same as b(4N) ≥ 0.75 · b(N). No number is introduced for this line. The negative uses the same 3.0 with "at least 4 of 5", as every negative in this ADR does.
- **It can return a negative.** If a full store of 4,096 slots holds less than three times what a full store of 1,024 holds, in 4 of 5 replicates for both F-OQ and T-OQ, the outcome is SATURATION-SUBPROPORTIONAL. What was seen bounds it from one side. On the calibration draws 32K/4K held 1.89–1.94 bits per fact (15.1–15.5 bits per slot) at 65,536 updates; i\* does not fall and every possible U_L of 32K/4K is at least 196,608. SUBPROPORTIONAL on 1,024 → 4,096 therefore needs 8K/1K to hold more than 2.52 bits per fact (20.1 bits per slot) if 32K/4K stops where it was seen, and more than 2.67–3.00 (21.3–24.0 bits per slot) if it stops at the check's extrapolated 2.0–2.25 — about a third more per slot than the 4,096-slot store was already seen to hold. Nothing has been run at 1,024 slots. PROPORTIONAL is the more likely verdict of this pair; the line is kept because its negative is reachable and its threshold predates every record. For F-OQ the outcome also needs the pair 256 → 1,024, where nothing has been run at either end.
- **Precision.** With 8,192 facts the standard error of i near 2 bits is about 0.03 bits, about 1.5% of S; ρ is then known to about ±0.07 in a replicate. "Full" allows up to 0.10 bits of gain over the last doubling, about 5% of S, in either cell, so ρ can be off by a few percent in either direction for that reason alone. Both cells' last-doubling gains are printed with ρ.
- **What it does not say.** It compares two rows, so facts and slots change together; that is the definition of the line, not a confound to be removed. "Full" means the plateau rule within the registered run length, not an asymptote. It holds for eight facts per slot only. H8 alone cannot give SATURATION-PROPORTIONAL, as it cannot give CAPACITY-POSITIVE. The line says nothing about 16,384 slots, and b(256) is an F-OQ-only figure. It is never summarised as "ArborLM's capacity scales".
- **A confound that grows with the fact set.** The oracle codes have width 16 and do not grow with the store; the share of facts whose code has a neighbour above cosine 0.8 is 0.10 at 2,048 facts, 0.38 at 8,192 and 0.85 at 32,768 (at initialization; auditor's computation). Each pair compares a fact set with one four times larger, so a SUBPROPORTIONAL verdict may come from crowding of the oracle's query codes rather than from the store. The separability figures of §7.3 are printed beside every ρ, and SATURATION-SUBPROPORTIONAL is never read as a property of the store alone.

## 9. How S1 avoids the earlier traps

| Trap | Source | What S1 does |
|---|---|---|
| Learned interface collapses | P9-I | no class depends on a learned interface |
| Oracle rung needs more updates as memory grows (seen only where facts grew with slots) | calibration | every step compares cells of one row of fixed facts; the efficiency line measures it; SAT and the plateau rule keep it out of the capacity line |
| Readout learns by updates of shared parameters | ADR-0017 §I.1 | cells compared in a class have equal updates; ME is not binding across rows |
| Sixteenfold exposure difference | P9-I | cannot arise inside a row; the saturation line compares rows only when each cell has stopped improving, and matches no budget |
| Calibration blocked | ADR-0017 §15.2 | U_P is set per row by a fixed rule (§10.1 item 1), not tuned; each loaded cell's run length is found by a fixed search with fixed outcomes; anything outside the rule returns to the human lead |
| Task validity unmeasured before the single run | ADR-0017 review B3; review B4 here | the load calibration |
| Classes passed or failed by budget | ADR-0017 Lane A | a capacity step needs MU, MC and SAT; a negative needs both cells plateaued, a loaded smaller cell, and the difference at the full run lengths; a slower larger memory gives BEHIND WITHIN BUDGET, never NO GAIN |
| A control that cannot learn | review B3 | D-OQ rebuilt and its rate chosen in calibration; DENSE AHEAD read in three readings |
| Slots selected mistaken for capacity | P8 | a_use needs per-fact dependence |
| Working set shrinks, misses fall | P7-B, P8 | counted work is analytic and gated; simulated traffic carries nulls and the working set |
| Hierarchy credited with a property of any index | P7-B; review M4 | the tree is compared with the flat store read through a standard index |
| Gate harness first run at registration; mistyped launch commands | P9-I attempts 1 and 2 | gates at real size on the rehearsal draw for all 31 configurations; fixed launch scripts for every registered stage, part of the freeze |
| One data draw | ADR-0017 §0 item 12 | five draws, never reduced; a seed block |
| No cell full within the run lengths | revision 4's calibration (§23) | two loaded cells at eight facts per slot, each run to a length found by a fixed search (§10.1 item 0b); the human lead's choice of sizes (§24) |
| A positive that is close to foregone under oracle addressing | the check, M4 | the capacity step is kept as a necessary condition; the milestone reading also needs the saturation line and the dense labels at saturation and at matched compute, none of which has been seen |
| A plateau rule met before the cell has learned | the check, §1 | a plateau needs i\* ≥ 0.473 bits at half the run length (§8.2) |
| A run length fitted to a threshold crossing on two calibration views | the check, §7 | two consecutive candidates must pass; the two calibration runs differ in initialization |
| Loadedness predicted for one arm only | the check, M6 | T-OQ is in the load search; H8 is declared unpredicted |
| A control whose best rate is the edge of its grid | revision 4's calibration | grid extended to 0.1; a best rate at the top returns to the human lead |
| A cap computed from a projection that the measurements overran | the check, M3 | the cap is computed from the rehearsal's rates by a rule, against a ceiling the human lead sets |

## 10. Calibration, rehearsal, resources

### 10.1 Calibration (revision 5; replaces revision 4's for the new cells)

Revision 4's calibration is kept as a record (§1 facts 13–17). Revision 5 takes no run length, row U_P or dense rate from it; each is set again by the rules below. The new calibration runs on the two calibration draws, initialization seed 2191 on draw 1 and 2193 on draw 2 (§6.3). Every run starts from initialization, under revision 5's code, in a new run directory; nothing is continued from revision 4's checkpoints. Order: 0a; then 0b together with 1; then 2 and 3. Calibration accuracies are never results. No step verdict, class, label or outcome is computed on calibration draws. The calibration is audited before the freeze. 70 training runs.

**0a. Timing preview (time and memory only).** On the rehearsal draw, through the whitelist validator of §10.2, so that no loss or accuracy is written or displayed: seconds per update (wall and process CPU) and peak memory for F-OQ, T-OQ, H8 and D-OQ at 1,024, 4,096 and 16,384 slots, for F-OQ at 256 slots and for R2 at its three cells (median of three runs of 256 updates after 32 warm-up updates, one process, nothing else of the project running). Its outputs are the projected wall time of every item below and each item's cap. An item's cap is twice its projected wall time at six workers. A run still running when its item's cap is reached is stopped, kept, and has no U_L. T-OQ and everything at 1,024 slots have never been timed (§1 fact 18); no item below is started on an assumed cost.

**0b. Load search.** F-OQ and T-OQ at 8K/1K and at 32K/4K, and F-OQ alone at 2K/256, on both draws: 10 runs. Each runs once, from initialization to its ceiling: **262,144 updates at 8K/1K and at 2K/256, and 524,288 at 32K/4K** *(lead's choice; §25.5)*. Candidates: {65,536, 98,304, 131,072, 196,608, 262,144} at 8K/1K and at 2K/256, and {131,072, 196,608, 262,144, 393,216, 524,288} at 32K/4K. Snapshots at every candidate, at half of every candidate, and on the doubling grid from 512. The rule is applied to the finished record. Nothing is decided, stopped or extended while the runs are in progress.

- **Pass at U.** An arm passes at candidate U if each of its four views (two draws × two panels) is loaded by §8.2 read with U in place of U_run: i\*(U) − i\*(U/2) ≤ 0.10, i\*(U/2) ≥ 0.473, and i\*(U) ≤ 4.0.
- **U_L of an arm** is the smallest candidate U_k such that the arm passes at U_{k−1} and at U_k. Two consecutive candidates must pass, so the first candidate cannot be U_L. This is the margin against choosing a length at the first noisy crossing of the threshold (the check, §3 and §7).
- An arm has **no U_L** if no such candidate exists. That covers a view above 4.0 bits, a run that ends `failed` (kept and never re-run), and a run not started or stopped by its item cap.
- H8 and D-OQ are not searched. They run the cell's U_L in the registered run and are judged on their own snapshots; nothing predicts whether H8 is loaded there.

**Fixed outcomes of 0b, per loaded cell:**

| Measured | Consequence |
|---|---|
| F-OQ and T-OQ both have a U_L | The cell's U_L is the larger of the two. The rows of §5.1 stand |
| F-OQ has a U_L, T-OQ has none | The cell's U_L is F-OQ's. The freeze record states T-OQ PREDICTED NOT LOADED AT that cell. Nothing else changes; the run judges T-OQ on its own snapshots |
| F-OQ has no U_L | The cell is NOT LOADED WITHIN ITS CEILING. The record (curves, the candidate and condition that failed on each view) returns to the human lead before the freeze, and nothing registered is generated. The lead adds no row, changes no load, raises no ceiling and substitutes no arm. The human lead may stop S1, or direct that it run with that transition fixed in the freeze record as CAPACITY NOT TESTED — NO LOADED CELL WITHIN BUDGET; then no arm can be CAPACITY_SUPPORTED (§22 m13), and the saturation pair that uses the cell is fixed as NOT FULL |

This return is not automated: the human lead's direction of §23 stands. A loaded cell that is NOT LOADED WITHIN ITS CEILING makes CAPACITY_SUPPORTED unreachable in every arm (§22 m13) and fixes the saturation pair that uses it as NOT FULL, so the lead does not proceed without the human lead's recorded answer.

**2K/256** is not a loaded cell of a step. If F-OQ has a U_L there, that is its run length. If it has none, the pair 256 → 1,024 is fixed as NOT FULL, printed '256 NOT MEASURED — NOT FULL WITHIN CEILING', the cell is not run in the registered matrix, and the work does not return to the human lead (§5.1).

A U_L from calibration is a prediction. The registered run judges every cell, in every replicate, on its own snapshots.

**1. U_P of each row.** F-OQ at the row's larger step cell and R2 at the row's reference cell, both draws, run to 32,768 updates: F-OQ at 2K/4K, 8K/4K and 32K/16K; R2 at 2K/4K, 8K/16K and 32K/32K. 12 runs. A row's U_P is the smallest of {8,192, 16,384, 32,768} *(lead's choice, as in revision 4)* at which F-OQ's a_use ≥ 0.90 and R2's a_use ≥ 0.95 on both draws and both panels (a_use, §22 (j)). If no value qualifies for a row, the work returns to the human lead before the freeze; no other value is substituted. From §1 fact 13 the lead expects 8,192 for the rows of 2,048 and 8,192 facts and 16,384 for the row of 32,768. That is an expectation; the rule decides.

**2. H8, reported only.** H8 at 2K/4K, 8K/4K, 8K/16K and 32K/16K to the row's U_P, both draws. 8 runs. Where H8's a_use is below 0.90, its classes at that cell carry UNDERTRAINED-AT-U_P. At a cell where H8 was not calibrated (2K/1K, 8K/1K, 32K/4K), its classes carry H8 NOT CALIBRATED AT cell. H8 gates nothing.

**3. Dense learning rate.** Rates **{0.001, 0.003, 0.01, 0.03, 0.1}** *(lead's choice; revision 4's three and two above them)*, on both draws, in four units. 40 runs.

| Unit | Selection cell | Run to | Readout | Used for D-OQ at |
|---|---|---|---|---|
| 4,096 slots | 8K/4K | the row's U_P | minimum Panel A a_use over the two draws at U_P | 2K/4K, 8K/4K |
| 16,384 slots | 32K/16K | the row's U_P | the same | 8K/16K, 32K/16K |
| loaded cell 8K/1K | 8K/1K | 65,536 | the same at 65,536 | 8K/1K |
| loaded cell 32K/4K | 32K/4K | 65,536 | the same at 65,536 | 32K/4K |

- The rate with the highest readout is chosen in each unit. Rates within 0.02 of the best are separated by the walk of §22 M7 and §22.1, down the doubling grid from the readout to one sixteenth of it; if several remain, the smallest is taken.
- **A diverged rate** is one whose run ends `failed` (the trainer's non-finite refusal included) or whose readout is inside the chance interval. It is recorded, left out of the selection, and is not an engineering stop.
- **The work returns to the human lead before the freeze if, in any unit, 0.1 has the highest readout by more than 0.02 at the selection readout, or if every rate diverged.** A 0.1 chosen only by the walk of §22 M7 among rates within 0.02 at the readout is taken and recorded as EDGE BY TIE-WALK. No further rate is tried by rule.
- The memory arms keep 0.003, untuned. A stronger dense control makes DENSE AHEAD, DENSE HOLDS MORE AT SATURATION and DENSE FASTER easier to reach, and so makes CAPACITY-NEGATIVE by clause (b) and EFFICIENCY-NEGATIVE by its second clause easier (the check, §6). That is the purpose of a control and is stated here.
- At a loaded cell the rate is chosen at 65,536 updates although the cell runs to U_L. Choosing at U_L would cost about 2 to 3.5 more charged hours of calibration (`rev5_arithmetic.out` §9), and is not done *(lead's choice; §12 states the limit)*.

**4. Block S3: not funded (the lead's ruling 2); not run.** Kept as a specification only: F-OQ at 128K/16K on both draws, once, to 1,048,576 updates, with candidates {262,144, 393,216, 524,288, 786,432, 1,048,576} and the rule of 0b for F-OQ alone; R2 at 128K/128K to 32,768 updates for the row's U_P. The saturation line prints '16,384 NOT MEASURED — NOT FUNDED'.

### 10.2 Rehearsal (rehearsal draw; time, memory and correctness only)

- All 31 configurations at real size for 64 updates and one full evaluation each, including the index build, six single-thread workers, through the whitelist validator of P9-I (no loss or accuracy is written or displayed).
- The gates stage at real size.
- **Isolated timing part,** one process: CPU-seconds and wall seconds per update for every arm at 1,024, 4,096 and 16,384 slots, for F-OQ at 256 slots and for R2 at its cells, D-OQ and T-OQ included (median of three runs of 256 updates after 32 warm-up updates).
- Analysis and report exercised on **synthetic records of the full registry**: missing cells, failed gates, non-finite values, every verdict, class, label and outcome of §8 on both lines. This includes records in which no arm is CAPACITY_SUPPORTED and every arm is in turn NOT_EVALUATED, DEPENDENCE_FAILED, NOT_TESTED_BY_LOAD, CAPACITY_ONE_TRANSITION and INTERMEDIATE; each must give CAPACITY-INCONCLUSIVE (or NOT TESTED) with the right reason, never CAPACITY-NEGATIVE.
- Outputs: the MC snapshots; the projection; stage caps (twice the measured stage time); the measured seconds per evaluated snapshot of every configuration; C_need and the cap by the rule of §10.3; the seed-block decisions.

### 10.3 Resources

- Apple M5 Max, 18 cores, 48 GB; CPU only. No cloud, paid service, download, new dependency, change to `uv.lock` or `pyproject.toml`, or SSD work.
- **Stages:** generate → gates → train (six single-thread workers) → evaluate (six workers) → timing (isolated) → simulate → analyze → report. **Each registered stage is started by a fixed launch script that is part of the freeze.** Training and evaluation never overlap a timing stage of any study. Item 0a of §10.1, the isolated timing part of §10.2 and the throughput stage run only when no other study of the project is training or evaluating on the machine. S1's rehearsal and registered stages do not overlap another study's rehearsal or registered stage (EXECUTION_PLAN item 3) unless the human lead decides otherwise (§13 item 2). If he does, c is measured under that overlap. Calibration training may overlap another study's training. Its charged hours are recorded as measured and enter C_need as charged. **By the lead's ruling on M5, S1's timing preview, isolated timing, rehearsal and registered run do not overlap P10-S0's registered run: they start after S0's last training stage has finished.** The human lead's recorded permission for concurrent studies is not used here. An overlap with P10-S2 follows the conditions already recorded for it and is rehearsed under that load, or is not used.

**Caps (the human lead's figures, §15):** **16 charged hours** (raised from 12 by the human lead on 2026-11-15, §15) for calibration, rehearsal and the registered stages together; **3 GiB per worker; 18 GiB aggregate.**

**The hour cap for the registered run is set by a rule (revision 5). No figure is chosen here.**

- Until the freeze the cap in force is the 16 hours above. Revision 5's calibration and rehearsal run under it; on the projection they bring the ledger to about 4.9–5.9 hours.
- After the rehearsal, **C_need = charged so far + 2 × the projected remaining time of the registered stages.** Training is projected from the isolated timing rates of §10.2 multiplied by c, the largest ratio, over the configurations run in revision 5's calibration, of measured six-worker training seconds per update to isolated seconds per update of the same configuration (c is never below 1.0). Evaluation is projected from the rehearsal's measured seconds per evaluated snapshot times each cell's registered snapshot count. Packing is longest first on six workers. Both sides of c are wall seconds of training only (the calibration's training wall, and the isolated wall of the same arm and slot count). The registered cap is C_need rounded up to the next whole hour. This is the twofold headroom rule of earlier revisions, read as the definition of the cap instead of as a test against a figure fixed in advance.
- **C_max = 36 charged hours, set by the lead under the Addendum's delegation on 2026-11-15, before any registered seed was observed; it is reported to the human lead with the adoption of revision 5.** It is the upper end of the central projection below (35.2 hours in the draft) rounded up to the hour. The lead records the computed cap only if it is at most C_max, only before any registered seed is observed, and only for the cells this revision registers.
- If C_need exceeds C_max, the cuts below apply in order and C_need is recomputed after each. If it still exceeds C_max after the last cut, nothing is started (NOT STARTED: BUDGET) and the work returns to the human lead with the measured figure. No further cut is improvised (the lead's ruling 3).
- Twice the measured peak memory must be at most the memory caps (peak at most 1.5 GiB per worker; otherwise the evaluation batch is reduced and the rehearsal repeated). The memory caps are not changed.

**Projection (not a measurement; `docs/reviews/p10s1-revision5-2026-11-15/rev5_arithmetic.out`).** Rates are those of revision 4's calibration (§1 fact 17). The low end of each range uses training wall seconds and T-OQ at F-OQ's rate; the high end uses task seconds and T-OQ at twice F-OQ's rate. **Unmeasured and assumed:** T-OQ at any size; everything at 1,024 slots (set to the 4,096-slot rate); D-OQ at 4,096 and 1,024 slots; R2 at 32,768 rows; the evaluation, which is the lead's estimate from the calibration's evaluation seconds. **Every U_L is an extrapolation.** The central row takes U_L = 131,072 at 8K/1K and 393,216 at 32K/4K.

| Item | Charged hours (six workers) |
|---|---|
| Charged so far (revision 4's calibration; measured) | 1.57 |
| Revision 5's calibration, every load-search run to its ceiling | 2.8–3.9 |
| Rehearsal with isolated timing | about 0.5 |
| **Charged before the cap rule** | **about 4.9–5.9** |
| Training, 155 cells (per replicate 35,370–48,010 s: F-OQ 9,470–10,500, of which 2K/256 about 920–970; T-OQ 8,550–19,060; H8 6,510–7,130; D-OQ 10,450–10,880; R2 about 400) | 8.2–11.1 |
| Seed block, draw 1 (14 cells) | 0.8–0.9 |
| Evaluation, with index builds and DEP at every snapshot (estimate) | 1.5–2.5 |
| Gates, timing stage, simulation, analysis, report | about 0.5 |
| **Remaining** | **11.0–15.0** |
| **C_need** | **26.9–35.9** |

C_need by where the loaded cells stop (2K/256 at 98,304 throughout):

| U_L at 8K/1K | U_L at 32K/4K | C_need (hours) | Against C_max = 36, on these figures |
|---|---|---|---|
| 98,304 | 196,608 | 22.5–29.9 | fits |
| 131,072 | 262,144 | 24.3–32.4 | fits |
| 131,072 | 393,216 | 26.9–35.9 | fits |
| 196,608 | 393,216 | 28.0–37.5 | the high end needs cut 2 (35.6) |
| 262,144 | 524,288 (both ceilings) | 31.8–42.5 | needs cut 2 except at the low end; the highest corner (task rates, T-OQ at twice F-OQ) is 39.7 after all cuts and returns |

- **The long cell.** 32K/4K by itself (F-OQ, T-OQ, H8 and D-OQ, five replicates) is 1.7–2.4 charged hours at U_L = 196,608, 3.5–4.8 at 393,216 and 4.6–6.5 at 524,288. The cap rule counts it twice.
- **The 256-slot cell** is about 0.2 charged hours of registered training and two search runs of about 0.7 hours each inside the calibration; about 0.7 hours of C_need in all.
- **Plain statement.** The largest unknown is T-OQ's cost, which moves C_need by 4.6–5.2 hours between the two assumptions; the timing preview of §10.1 measures it before anything long runs. Under C_max = 36 every case fits, at worst after cut 2, except the corner in which T-OQ costs twice F-OQ and both loaded cells run to their ceilings. The reviewer's recomputation, with longest-first packing and its own evaluation estimate, puts that corner at 35.9 hours after cut 2 (`review/a2_cost.out`); this text's cruder figures put it at 39.7 after all cuts. The two differ mainly because the high end here counts evaluation twice (task seconds already include the calibration's evaluations; review m10). Contention is not in either figure: at 1.25 times it adds 6–8 hours, which is why the registered run does not overlap S0's (the Stages paragraph).
- **Block S3** would add a search of 5.5–7.5 charged hours and five registered runs of 2.7–7.5 hours each; C_need with it would be about 36–54 hours. It is not funded.
- **What each removable item is worth in C_need, at the central row** (none of this is a rule; a need above C_max after the three cuts returns to the human lead, who may choose among these): the draw-1 seed block 1.6–1.7 hours; D-OQ at 8K/16K 0.5–0.6; the row of 2,048 facts (step N1, and with it the efficiency line's first transition) 1.9–2.0; H8 at the two loaded cells 1.8–2.0; D-OQ at the two loaded cells (the dense-at-saturation label) 2.7–2.8, and 4.0–4.1 at both ceilings; a ceiling of 393,216 in place of 524,288 at 32K/4K takes 0.2–0.4 off the calibration and bounds the worst case at about 28–38 in place of 32–43.

**Block S3 is not admitted.** It is not funded (the lead's ruling 2); the saturation line prints '16,384 NOT MEASURED — NOT FUNDED'. Omitting it is not a cut.

**Cuts, fixed now, in this order, until C_need is at most C_max; nothing else may be cut:**

1. The seed block on draw 2 (added only if C_need with it is at most C_max in the first place).
2. The seed block on draw 1 *(lead's choice of order; it is descriptive and enters no rule)*.
3. D-OQ at 8K/16K, the larger cell of control step N2, whose smaller cell 8K/4K was measured at the ceiling in revision 4's calibration (§1 fact 13). N2 then prints DENSE NOT READ on both lines. No other D-OQ cell is ever cut.
4. If C_need still exceeds C_max, nothing is started (NOT STARTED: BUDGET) and the work returns to the human lead.

The five replicates, the rule-set values of U_P and U_L, the run lengths and every threshold are never changed to make the study fit. Each cut is written in the freeze record with the rules it changes.

## 11. Order of work and stop rules

1. Independent review of revision 5 by the auditor (done: READY AFTER M1–M7, applied in §25.10) and the lead's rulings (§25.8); the lead's check that this text applies them; revise until confirmed. Anything the human lead says about the two items reported to him (§25.9) is recorded there verbatim.
2. **Decision 1 for revision 5** (the code changes, the calibration of §10.1 and the rehearsal): taken by the lead under the human lead's delegation quoted in §15, only after item 1, and recorded in §25.9. The decision recorded in §15 was for revision 4 and does not carry over.
3. Implementation of the changes with tests (every gate; every verdict, class, label and outcome on synthetic records, the saturation line and the dense-at-saturation label included; registered-mode refusals; fixed launch scripts), and an independent implementation audit of them. The audit of revision 4's code does not cover them.
4. Calibration (§10.1) in the order 0a; 0b together with 1; then 2 and 3; audited. Any return to the human lead named in §10.1 happens here.
5. Rehearsal (§10.2); C_need and the cap by the rule of §10.3; implementation audit ending READY TO FREEZE.
6. Lane L status by §5.6, recorded.
7. Registered data generated and hashed; G1. Freeze of specification, code, config, launch scripts, seeds, thresholds, calibration records, U_L of each loaded cell, U_P of each row, MC snapshots, D-OQ rates, the cap, c, cuts, the seed-block decision and data identities.
8. **Decision 2** (the single registered run): taken by the lead under the same delegation, only if the audits end with no open blocker or major, nothing changed after calibration except what §8 allows, the cap was set by the rule of §10.3 at or below C_max, and no registered seed has been observed. Otherwise it returns to the human lead. Recorded in §15 before anything registered runs.
9. The registered run, once.
10. Independent recomputation of every verdict, class, label and both outcomes from raw records and snapshots by the auditor; outcome report with deviations, failed attempts and negative results kept.

**Stop rules.**

- A failed engineering gate stops the run before training.
- Any difference between frozen and running code, config, launch scripts or data identities stops the run.
- A stage that would exceed its cap is not started; the study is S1-INCOMPLETE.
- A failed cell is kept and not re-run; the study is S1-INCOMPLETE.
- No stage is re-run with changed settings. A second attempt after an engineering stop is the human lead's decision.
- No registered seed is observed before decision 2, apart from G1.
- The caps are the human lead's. The lead raises the hour cap only under the Addendum's delegation, by the rule of §10.3, and never above C_max. The memory caps are not raised.

## 12. What S1 cannot establish

- That a learned memory works without an oracle. **No autonomous learned-memory success may be claimed from S1**, whatever lane L shows.
- That the language model can form the queries, or that any interface reaches the capacity measured here.
- **Useful capability beyond recall of the trained facts; any improvement of a language model's behaviour.**
- Efficiency, speed, latency or I/O. Counted work is logical. Simulated traffic is not a storage measurement. Throughput is an in-RAM CPU figure for a 27,392-parameter backbone.
- Capacity where no cell is loaded; anything beyond the registered slots, facts and run lengths.
- **Capacity from 16,384 to 65,536 slots, or at any size above 16,384.** Revision 5 does not test it. It is proposed for P10-I.
- What a full store of 16,384 slots holds: block S3 is not funded. The saturation line covers 256 → 1,024 for F-OQ only and 1,024 → 4,096; b(256) is an F-OQ-only figure.
- That a SUBPROPORTIONAL saturation verdict is a property of the store: the oracle's fixed-width codes crowd as the fact set grows (§8.10).
- A capacity "per slot" in general. b(N) is for eight facts per slot, this read path, this optimizer and these run lengths; "full" is the plateau rule, not an asymptote.
- That the store holds more than a dense map when full, beyond one dense family whose rate was chosen on calibration draws at 65,536 updates.
- That a capacity step under oracle addressing is a discovery. Once the smaller cell is full it is close to foregone (§25.4).
- Anything about natural-language knowledge, composition, reasoning, skewed fact frequency, another backbone, or a trainable backbone.
- That DENSE AHEAD or CONVENTIONAL RETRIEVAL SUFFICES means memory is not needed in general, or that BEATS DENSE holds off this task.
- That a hierarchy helps locality, or that sublinear counted work is a finding about the tree.
- That "more slots" differs from "more store parameters": this read path cannot separate them (§5.3).
- Generalization across facts.
- That a dense architecture other than D-OQ would not do as well: one dense family is run, with a five-rate grid.
- After D7 was dropped there is one dense family in S1, and no learned arm that addresses facts without the oracle.
- TRANSFER-POSITIVE, SYSTEM-POSITIVE, a failure of the ArborLM concept, Astra validation, or a human approval that is not recorded.

## 13. Decisions reserved for the human lead

1. Every return named in §10.1 and §10.3 (a loaded cell NOT LOADED WITHIN ITS CEILING, a row with no qualifying U_P, a dense rate chosen at the top of its grid or a unit whose rates all diverged, C_need above C_max after the allowed cuts). Whether S1's rehearsal or registered stages may overlap another study's. The human lead is told of C_max = 36 hours and of the 256-slot cell, both set by the lead (§25.9).
2. The caps; whether S0, S1 and S2 training stages may overlap on the machine.
3. Any second attempt; any change after the freeze.
4. P10-I and any integrated study; the use of S1's outcomes in SYSTEM-POSITIVE; merge; publication; weight release; ADR-0012.
5. **Pending human answer (ADR-0020 §17 item 0).** If S0 qualifies no interface, every S1 outcome and reading is printed with "ORACLE-ADDRESSED — NO LEARNED ADDRESSING QUALIFIED (ADR-0020)" . If the human lead answers that S1's capacity labels are withheld in that case, S1 follows that answer; it is recorded verbatim in §15 and needs no other change to this specification. Until S0 has an outcome, the S0 status printed is "S0 NOT YET DECIDED". Whatever S0 shows, no S1 outcome is ever summarised as "ArborLM's capacity scales".

"K7(c)" in §8.7 and §8.8 means item 5 above. The question is pending; no answer is recorded.

## 14. Requirements map

| Requirement of the human lead | Where |
|---|---|
| Oracle or controlled addressing; no claim of autonomous success | §3, §8.7, §12 |
| Study A: fixed facts, 4K / 16K / 64K; recall, learning efficiency, robustness, generalization | §5.1, §5.2, §8.2–§8.8, §7.2. The sizes are 1K / 4K / 16K by the human lead's choice of §24; 16K→64K is not tested |
| Control for total trainable parameters; strong dense alternatives | §5.3, §8.5, §10.1 item 3 |
| Study B: more facts with more memory; flat, hierarchical, conventional sparse retrieval, exact-address references, dense controls | §5.1, §3, §5.5, §8.5, §8.10 (the saturation line) |
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

The questions revision 5 raised are ruled by the lead in §25.8. Two things are reported to the human lead and one earlier question is still pending with him (§25.9; §13 item 5).

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

### 22.1 Five further points the implementer raised on §22 (ruled 2026-11-15 UTC, before any S1 record exists)

| Point | Ruling |
|---|---|
| §10.2 ("every arm in turn" gives INCONCLUSIVE, never NEGATIVE) against §8.7 row 4(a) | §8.7 governs outcomes. §10.2's requirement applies to the arms row 4(a) reads, F-OQ and T-OQ: a NOT_EVALUATED or DEPENDENCE_FAILED F-OQ or T-OQ can never yield CAPACITY-NEGATIVE. H8's status does not enter row 4(a); the synthetic scenario with H8 DEPENDENCE_FAILED and both read arms NOT_SUPPORTED is NEGATIVE by the rule and is recorded as such |
| M7 with more than two rates tied | At each snapshot of the walk, keep the rates within 0.02 of the best at that snapshot and continue; if more than one remains at U_P/16, the smallest learning rate is taken |
| (j) and the overload row | The overload row's U_P check uses a_use, like calibration items 1 and 2 |
| M6 terms beyond the matrix products | The count is the multiply-adds of every matrix product and gather-weighted sum in the forward and backward pass of the whole update, plus 4 per trainable parameter for AdamW. Elementwise activations, normalizations and the loss are not counted. The formula is in the config |
| (h) for DENSE FASTER | Per replicate: a replicate counts if either panel satisfies the blocking condition |

## 23. The calibration's return to the human lead, and the human lead's direction (2026-11-15 UTC)

The calibration of §10.1 (`results/p10s1-calibration-2026-11-15/`, 46 of 46 runs, calibration draws only) returned to the human lead by the rule of item 0: no load is loaded at 4,096 slots or at 16,384 slots within the registered run lengths. Every cell is at its ceiling or still improving when its run ends. The lead reported this with three options (run S1 as it is with the capacity line fixed as CAPACITY NOT TESTED; fund longer runs; stop and carry the question to P10-I), recommended the first, and raised the dense control's learning rate being at the top of its grid.

The human lead answered, verbatim (the second half concerns ADR-0020, whose cap stays at 22 hours):

> prioritize resolving S1's no-loaded-cell condition over adding runtime margin to S0.

Recorded by the lead:

- **The human lead directs that the no-loaded-cell condition be resolved**, not accepted. S1 does not proceed to its freeze with the capacity line fixed as NOT TESTED while a resolution is being worked out. This is the human lead's use of §10.1's "fund a row".
- **How.** The lead does not improvise a row (§10.1). It specifies, before running anything further, a rule-bound extension of the load calibration that searches for a cell that saturates below the ceiling within a fundable run length, and a fixed rule that turns its outcome into registered rows or into CAPACITY NOT TESTED. The extension is reviewed independently before it runs, uses calibration draws only, and is charged to S1's ledger; the hour cap may be raised under the recorded delegation, before any registered seed is observed.
- No registered seed of S1 has been observed. The efficiency line is unaffected by this section.
- The dense control's learning-rate grid is taken up in the same extension, as a proposal for the independent check; no answer on it has been recorded from the human lead.


## 24. The human lead's choice after the load-search check: shift the capacity grid down (2026-11-15 UTC)

The lead drafted the extension §23 called for and had it checked independently before running anything (`docs/reviews/p10s1-load-search-2026-11-15/`: the draft, not adopted, and `CHECK_LOAD_SEARCH.md`). The check confirmed the curves and found that the row the extension would add (4,096 → 16,384 slots at 32,768 facts) can only return a positive, that the second transition is unlikely to be loadable, that the study as registered needs 17.6–20.2 hours on the calibration's measured rates against the 16-hour cap, and that both loaded rows together do not fit under 32 hours. It suggested shifting the grid down one size instead.

The lead put two options to the human lead: (A) run the extension as drafted; (B) shift the capacity line to 1,024 → 4,096 → 16,384 slots at eight facts per slot, a redesign needing a revision of this specification, an independent review, code changes and a new calibration. The lead recommended B and said it changes registered rows after calibration data was seen, with no registered seed observed. The human lead answered, verbatim:

> im ok with b

Recorded by the lead:

- **Option B is approved by the human lead.** The draft extension of `docs/reviews/p10s1-load-search-2026-11-15/DRAFT_AMENDMENT_LOAD_SEARCH.md` is not adopted and is not run.
- Revision 5 of this specification is drafted next, reviewed independently before any code changes or runs, and replaces the grid, rows and run lengths that depend on it. Everything seen in the calibration of §10.1 and in the check is declared in revision 5 as seen before the redesign; revision 5 says which thresholds are unchanged and why each changed row is not chosen for its predicted answer.
- The dense control's learning-rate grid: the lead extends it upward in revision 5 (the selected rate was the top of the grid, which weakens the control). This strengthens a control before any registered seed and is the lead's decision under the P10 delegation; the human lead was not asked a separate question on it.
- The hour cap is set again from the new calibration's measured rates under the recorded delegation, before any registered seed is observed.
- No registered seed of S1 has been observed. Nothing in S1 has run since the calibration.


## 25. Revision 5: the shifted capacity grid (2026-11-15 UTC) — independent review applied; not adopted

Drafted by a Claude Fable 5.2 drafting context for the lead, after the human lead's choice recorded in §24; reviewed independently by Opus 5.5; the review and the lead's rulings are applied in §25.10. Nothing has been implemented or run under it. It is not a human approval and not an Astra review. **Astra review: NOT_PERFORMED.** The arithmetic behind every figure is in `docs/reviews/p10s1-revision5-2026-11-15/DESIGN_NOTES.md` and `rev5_arithmetic.py` / `.out` beside it.

### 25.1 What revision 5 is

- The memory sizes of the capacity line are 1,024, 4,096 and 16,384 slots. No cell has 65,536 slots. One further cell, 2,048 facts in 256 slots for F-OQ only, serves the saturation line alone; it is the lead's addition, outside the sizes of §24. **Capacity from 16,384 to 65,536 slots is not tested and goes to the proposed P10-I.**
- Each transition has a loaded step, whose smaller cell holds eight facts per slot, and a control step at two facts per slot. The second transition has its own fact count, 32,768.
- The capacity line and its thresholds are kept. A third line, saturation, asks whether a full store's content keeps pace with its slots. The dense control is also read on the full cells, and its matched-compute reading can now be established for every arm.
- The calibration is replaced by a rule-bound procedure with fixed outcomes. The hour cap is computed by a rule against a ceiling of 36 hours, set by the lead under the Addendum's delegation.

### 25.2 Every change and its reason

| Where | Change | Reason |
|---|---|---|
| Header, §0 | Status; three result lines; the sizes; 16K→64K not tested | §24; the lead's brief for this revision |
| §1 facts 13–18 | Revision 4's calibration and the check, as known facts | They were seen before the redesign and are its basis (§25.3) |
| §2 | H21-3 restated on full cells; H21-4 extended to full cells; a new expectation paragraph | The diagonal H21-3 was written for no longer exists; the check's M4 (§25.4) |
| §3 | Four positive labels added to the list that must carry the tag; T-OQ and F-OQ-IVF at 1,024 slots | New labels; a new size |
| §5.1 | Grid of seven cells at 1,024 / 4,096 / 16,384; steps C1, N1, C2, N2; block S3; the overload-row rule withdrawn | §24. At a fixed 8,192 facts the 4,096-slot cell is not loaded, so the second transition needs 32,768 facts. Control steps keep H21-2 testable in each transition |
| §5.3 | D-OQ at six cells: the larger cell of each step and both loaded cells | Dense at saturation (§8.5) |
| §5.4 | U_P per row by rule; run lengths U_L and 6·U_P; snapshots; no cross-row ME; MC-AMBIGUOUS named | C2 cannot be read at 8,192 updates (§25.6); 6·U_P makes the dense matched-compute snapshot exist for every arm (§25.7) |
| §6.1, §6.3 | The matrix; R2 at 32K/32K; calibration seed 2193 | No 65,536-slot table; the check's §7 item 2 |
| §7.4 | Counted work at the new sizes | Arithmetic |
| §8 opening | What may change after the new calibration | New rule outputs (U_L, U_P, the cap, S3) |
| §8.1 | REF cells | The row of 32,768 facts needs a reference without 65,536 slots |
| §8.2 | A plateau needs i\* ≥ 0.473 bits at half the run length | The artefact the check found (§1 fact 14) |
| §8.4 | Steps and transitions renamed; the 0.80 floor read at 32K/16K | 32K/64K no longer exists; the value is unchanged (§25.8 question 5) |
| §8.5 | Matched compute on the new sizes; dense at saturation; hierarchy and conventional-retrieval cells | The lead's brief; §22 M5 revisited (§25.7); the old cells no longer exist |
| §8.6 | Study B replaced by the saturation line | Its diagonal no longer exists |
| §8.7 | Printed label; the milestone reading needs the saturation class and the dense-at-saturation label, and names the size range | §25.4. This edits wording the confirmation review supplied (K2), in the direction of a harder positive |
| §8.8 | The efficiency line reads the control steps only | Loaded steps could only report a capacity difference under the name of efficiency |
| §8.9, §8.10 | Decision map; the saturation line | §25.4 |
| §9 | Seven rows | The traps the calibration and the check found |
| §10.1 | New calibration: timing preview, load search with two consecutive passes and fixed outcomes, row U_P, H8, a five-rate dense grid in four units, block S3 (since ruled not funded, §25.10) | The lead's brief; the check's E1, E9, M6 |
| §10.2 | The new sizes in the rehearsal; C_need among its outputs | Consistency |
| §10.3 | The cap by rule against C_max; projection from measured rates; three cuts | The check's M3; the lead's brief |
| §11, §12, §13, §14, §16 | Order of work for revision 5; limits; returns; pointers | Consistency |

Changes made after the independent review are mapped in §25.10 and are not repeated in the table above.

Withdrawn with their sections: every 65,536-slot cell; the overload row and its U_P rule as a special case; revision 4's load table and its rule table; cut 3 as it applied to 8K/64K and 32K/16K; the label KNOWLEDGE SCALES WITH MEMORY. The draft extension of `docs/reviews/p10s1-load-search-2026-11-15/` was not adopted (§24) and nothing of it is in force, although revision 5 takes several of the check's edits to it (two consecutive passes, the failed-run rule, the diverged-rate rule).

### 25.3 What had been seen before the redesign

Everything below was known to the lead when this revision was drafted. All of it is from calibration draws; no registered seed has been generated or observed.

1. Revision 4's calibration, 46 runs (§1 facts 13–17): F-OQ's curves to 65,536 updates at 4,096 slots with 8,192 / 16,384 / 32,768 / 65,536 facts and at 16,384 slots with 8,192 / 32,768 / 65,536 / 131,072 facts; R2, F-OQ and H8 at 2K/4K, 8K/16K and 32K/64K to 8,192 updates; D-OQ at 8K/16K and 32K/64K at three rates; the time of every run.
2. The check's recomputation of those curves, its six extrapolation families and their hold-out test, its cost tables, and its findings M1–M6 (§1 fact 15).
3. The lead's own reading of step N2 from the same curves (§2, expectation 4).
4. Of the cells of revision 5, these were run in that calibration, on the same two draws: 8K/4K, 8K/16K, 32K/4K and 32K/16K for F-OQ to 65,536 updates; 2K/4K for F-OQ, R2 and H8 to 8,192; 8K/16K for D-OQ. **Not run by anyone:** anything at 1,024 slots (2K/1K, 8K/1K); T-OQ anywhere; D-OQ at 2K/4K, 8K/4K, 32K/16K, 8K/1K or 32K/4K; R2 at 32K/32K; any run beyond 65,536 updates; any rate above 0.01.
5. From P9-I and the review stand-in: §1 facts 1–12.
6. Seen after the draft and before this text was finished, from the independent review (no training; `review/a1_calibration.out`, `a2_cost.out`, `a3_read_geometry.out`): the recomputation of facts 13–17 from raw counts; that 32K/4K at 15.1–15.5 bits per slot at 65,536 updates bounds one side of the saturation pair 1,024 → 4,096; the crowding of the oracle codes with the size of the fact set (0.10 / 0.38 / 0.85 / 0.999 of facts with a neighbour above cosine 0.8 at 2,048 / 8,192 / 32,768 / 131,072 facts); the read geometry of top-8 at 256, 1,024 and 16,384 random keys; a fitted cost model; and that the 0.80 floor is implied by the row U_P rule. The 256-slot cell, the comparator rule for matched compute and C_max were fixed after these were seen. None of them is an observation of any revision-5 cell.

### 25.4 The check's point that the capacity step is close to foregone

The check found (M4) that a loaded 4K→16K row "can only yield a positive": at matched updates the larger store is about 3 bits per fact ahead, so NO GAIN, REVERSED and NOT LOADED are out of reach. The same holds for both loaded steps of revision 5. Once F-OQ's smaller cell is full at about 2 bits per fact and the larger cell holds the same facts at two per slot, "a larger memory holds more once the smaller is full" follows almost by construction when an oracle supplies the address. The lead accepts this and answers it in the design, not in the wording:

1. **The capacity line is kept, unchanged, as a check of a necessary condition.** It can still fail to be positive: if a plateau does not hold in all five replicates, if dependence fails, if T-OQ or the indexed read does not show what exhaustive F-OQ shows, or if the dense control is ahead. It cannot return NO GAIN for F-OQ on a loaded step, and this ADR says so.
2. **The saturation line (§8.10) is the measurement whose answer was not seen; one side of it is bounded (§8.10).** It asks whether a full store keeps its bits per slot as it grows. It has a negative, SATURATION-SUBPROPORTIONAL, fixed with a threshold that predates every S1 record.
3. **The dense control is read where it is informative.** At the larger cell of a step, both the store and the dense map are near the ceiling. At a loaded cell the store is full, and the question "does a dense map of the same parameter count hold more?" has a real answer. DENSE HOLDS MORE AT SATURATION blocks the positive and can make the outcome CAPACITY-NEGATIVE.
4. **Matched compute against the dense map is now affordable**: the matching snapshot exists on the analytic measure for every arm; whether it is established depends on the CPU measure, and a disagreement is read in the comparator's favour (§5.4, §25.7).
5. **The milestone reading needs all of them** (§8.7). A capacity step alone gives "capacity steps shown; proportional saturation not shown".

### 25.5 Thresholds

**Unchanged, every value in the config's `[thresholds]` table:** the reference floor 0.95; the DEP floor 0.25 and ratio 0.95; the gain 0.5 and the null band 0.25; the plateau 0.10; the loaded limit 4.0; the ceiling 4.5; the a_use floors 0.5 and 0.80; DENSE AHEAD at −0.25; BEATS DENSE at 1.10; the tree ratios 1.03 and 0.97; conventional retrieval within 0.25; the growth factor 3.0; SUBLINEAR at 2.0; held-out 0.90; the efficiency level 3.0 bits with factors 0.5 and 0.8; OPTIMIZER-ASSISTED at 1.5; DENSE FASTER at 0.8; MC-MISMATCH at 1.25; robustness 0.05; "all 5" and "at least 4". The lead found none of them ill-defined on the new grid.

**Read at a different cell, value unchanged (forced by the grid):** the 0.80 floor of §8.4 (32K/16K in place of 32K/64K); REF for the row of 32,768 facts (32K/32K in place of 32K/64K); the hierarchy label (8K/4K and 32K/16K); the conventional-retrieval label (32K/16K).

**No longer used:** the Study B accuracy floor 0.85 and its 0.5 ratio floor. A full cell at eight facts per slot is expected near 0.6, so the floor would make the line unreachable by construction.

**New rules, each built from a number that already existed:**

| Rule | Number | Why this number | Can it return a negative? |
|---|---|---|---|
| A plateau needs the cell to have learned (§8.2) | a_use 0.25, as 0.473 bits | It is the floor below which DEP is not evaluated; below it nothing stored has been checked | It only removes a false "loaded" |
| Saturation in proportion (§8.10) | 3.0 per fourfold step | H21-3's factor since revision 1, before any S1 record | Yes: SATURATION-SUBPROPORTIONAL |
| Dense at saturation (§8.5) | −0.25 bits; ratio 1.10 | The numbers of DENSE AHEAD and BEATS DENSE | Yes: DENSE HOLDS MORE AT SATURATION, which blocks the positive and can give CAPACITY-NEGATIVE (b) |
| U_L needs two consecutive candidates to pass (§10.1) | the plateau rule itself, twice | The check's margin against a noisy first crossing | If no candidate qualifies, the cell is NOT LOADED and the work returns |
| Cost measures that disagree are read in the comparator's favour (§5.4) | none | The reviewer's rule (M7), fixed before any cost direction at the new sizes is known; it can only make the store's readings harsher | It replaces "not established" by a reading against the store |

**New choices of the lead that are not thresholds of a verdict.** Each was made after seeing §25.3, and each is marked *(lead's choice)* where it stands:

- The ceilings and candidate lists of the load search: 262,144 at 8K/1K, 524,288 at 32K/4K, 1,048,576 at 128K/16K. 524,288 is the top of the check's range for 32K/4K. 262,144 and 1,048,576 follow from a time shift of about 2.4 per fourfold step read off the calibration curves, which is an extrapolation. They bound cost. A cell that needs more is NOT LOADED and returns to the human lead; a ceiling is never raised by the lead.
- Run length 6·U_P at every size for cells that are not loaded: the smallest uniform value at which every arm's dense matched-compute snapshot exists (§25.7).
- The dense rates 0.03 and 0.1, added above the three of revision 4. The check judged 0.03 a reasonable next point and 0.1–0.3 likely to be unstable; 0.1 is kept as the bracket, and a best rate at 0.1 returns to the human lead.
- The dense rate at a loaded cell is chosen at 65,536 updates.
- Calibration seed 2193 on the second draw; every calibration run from initialization.
- R2 at 32K/32K; the efficiency line on the control steps only; three cuts.
- The cell 2K/256 for F-OQ, with the candidates and ceiling of 8K/1K (the lead's ruling 2, the reviewer's text). It adds a measurement, removes none and enters no capacity step. Nothing has been run at 256 or 1,024 slots.
- C_max = 36 hours (the lead's ruling 1): the upper end of the draft's central projection, rounded up to the hour. It was set after the projection was seen and before any revision-5 run.
- The contention ratio c in the cap rule (review M5).

### 25.6 Each changed row, and why it is not chosen for its predicted answer

| Row | What is predicted, and from what | Why the choice does not rest on that prediction |
|---|---|---|
| The sizes 1,024 / 4,096 / 16,384 and eight facts per slot | Loaded cells that plateau near 2 bits per fact (extrapolation from 4,096 slots only) | The human lead's choice (§24), made so that the test has a full smaller cell at all. A full smaller cell is the condition of the test, not its answer |
| C1: 8K/1K → 8K/4K | CAPACITY for F-OQ, if the plateau holds. 8K/4K was seen at 4.37–4.54 bits at 8,192 updates; 8K/1K was never run | The lead states plainly that this prediction is positive and that the step cannot return NO GAIN for F-OQ (§25.4). The row is there because the first transition must have a loaded step; the milestone reading does not rest on it alone |
| C2: 32K/4K → 32K/16K | CAPACITY for F-OQ, if the plateau holds. Both cells were seen to 65,536 updates | The same. It is revision 4's step B1; revision 5 changes how long its smaller cell runs, by a search fixed before it runs, and its U_P, by a rule (next row) |
| U_P of the row of 32,768 facts, by rule (expected 16,384) | At 8,192 updates 32K/16K holds about what 32K/4K holds when full, so C2 would be GAIN WITHIN BUDGET ONLY (a gain at matched updates, none against saturation); at 16,384 it holds 4.12–4.23 bits and C2 can be CAPACITY | **This choice does change what C2 can show, in the direction of a positive, and it is made after seeing the curves.** The check said so (its §7 item 4). The rule is the one revision 4 wrote for any added row, before any S1 record; its inputs are a_use floors on the larger cell and on R2, not the step's verdict; and it is applied to every row alike. The lead accepted it with this declaration (§25.8 question 8). It also makes the 0.80 floor of §8.4 near-automatic (0.910–0.923 at 16,384 against 0.585–0.697 at 8,192 on the calibration draws). In the other direction, it doubles D-OQ's run at 32K/16K. |
| N1: 2K/1K → 2K/4K | CEILING or FLAT, NOT LOADED, if a slot holds 17–18 bits (extrapolation); nothing at 1,024 slots was run | A control: it tests H21-2 and can contradict the capacity story if the larger memory gains where the smaller is not loaded |
| N2: 8K/4K → 8K/16K | CEILING on one calibration draw and GAIN WITHIN BUDGET ONLY on the other, read from §1 fact 13; efficiency SAME or FASTER IN UPDATES ONLY | Revision 4's step A1, unchanged in cells, U_P and thresholds. Its predicted answers favour neither positive outcome |
| Saturation pair 1,024 → 4,096 | PROPORTIONAL is the more likely verdict: the 4,096-slot side is bounded below by what was seen (15.1–15.5 bits per slot at 65,536 updates), so SUBPROPORTIONAL needs at least 20.1 bits per slot at 1,024 slots (§8.10). Nothing was run at 1,024 slots. | The threshold predates every S1 record. The likely answer is stated; the negative stays reachable |
| Saturation pair 256 → 1,024 (cell 2K/256, F-OQ only) | Nothing: no run exists at either end | Added because it is the one pair with no observed side. The reviewer found top-8 of 256 a sound read for F-OQ (7.2 effective slots against 7.5 at 1,024; the same interference per fact) |
| D-OQ at the loaded cells | Possibly DENSE HOLDS MORE (per-parameter arithmetic, §2 expectation 3); never run | A control added where it can block. If the prediction is right the capacity outcome is negative |
| D-OQ at 8K/4K and 32K/16K, with higher rates | Possibly DENSE AHEAD at U_P; never run at these cells | A stronger control; it can only make the store's positives harder |
| Block S3 | Nothing reliable: 128K/16K was at 1.46–1.52 bits and rising fast at 65,536 updates | Not funded; not run |
| Rows removed: everything at 65,536 slots | 8K/64K and 32K/64K were at or near the ceiling at 8,192 updates | Removed by the human lead's choice of sizes. What they would have shown is not claimed: 16K→64K is NOT TESTED |

### 25.7 The rulings of §22 and §22.1 on the new grid

- **M5 (dense matched compute).** The ruling and its label stand. Its plain statement was that S1 could not establish the dense comparison at matched compute at 65,536 slots, and nowhere for T-OQ and H8. On the new grid the analytic multipliers of D-OQ over an arm are 1.2 / 1.7 / 2.5 for F-OQ, 1.2 / 2.0 / 5.1 for T-OQ and 1.3 / 2.1 / 5.4 for H8 at 1,024 / 4,096 / 16,384 slots. The matching snapshots are at most 6·U_P, and every arm's cell now runs 6·U_P. The only measured CPU-time multiplier is F-OQ's at 16,384 (1.40–1.55); the others are measured by the rehearsal. If T-OQ's or H8's measured CPU cost per update exceeds D-OQ's while the analytic count says the opposite, that pair is MC-AMBIGUOUS; it is then read in the comparator's favour by the rule of §5.4, and the ruling's label applies only if that reading is MC-SHORT (§25.8 question 11).
- **(i)** (MC-AMBIGUOUS is not established) is replaced for revision 5 by the comparator rule of §5.4, on the reviewer's proposal and the lead's ruling; §22's own text is not edited.
- **M6, M7, (g), (h), (j), (k), (m), (n)** stand unchanged. M7's walk is applied in each of the four dense-rate units. (h) is applied to the two new labels as written in §8.5 and §8.10.
- **(b) lane L** stands; its three cells (2K/4K, 8K/4K, 8K/16K) are cells of the new grid.
- **m2** the seed block is the seven grid cells. **m13** stands and is cited in §10.1.
- **M4** Decision 2 is recorded outside the hashed specification, as ruled.
- Revision 4's implementation, its audit and its fixes do not cover revision 5. The changes revision 5 implies are listed in `IMPLEMENTER_BRIEF.md`, beside the design notes.

### 25.8 The questions the draft raised, and the lead's rulings

The draft put twelve questions. The lead ruled on them before the independent review and again after it (`docs/reviews/p10s1-revision5-2026-11-15/LEAD_RULINGS.md`, both parts). These are the lead's rulings under the P10 delegation, not the human lead's answers.

| # | Question | Ruling in force |
|---|---|---|
| 1 | The cap ceiling | C_max = 36 hours. The cap itself is computed by the rule of §10.3 |
| 2 | Bits per slot at 16,384 slots (block S3) | Not funded. The cell 2K/256 is added for F-OQ, with the reviewer's text (§5.1) |
| 3 | A need above the ceiling after the three cuts | NOT STARTED: BUDGET; returns to the human lead. No further cut is improvised |
| 4 | Dense at saturation | Binding: it counts as DENSE AHEAD |
| 5 | The 0.80 floor of §8.4 read at 32K/16K | Accepted. The value is unchanged; the cell is forced, and the U_P rule makes it near-automatic (§8.4) |
| 6 | R2 for the row of 32,768 facts | A table of 32,768 rows |
| 7 | The plateau guard | Accepted; the reviewer confirmed it cannot hide a result against the store (m2) |
| 8 | U_P per row by rule | Accepted, with the declaration of §25.6, which now also names the effect on the 0.80 floor |
| 9 | A loaded cell that is NOT LOADED WITHIN ITS CEILING | Returns to the human lead, as drafted. The lead's first ruling (fix it as NOT TESTED and proceed) was withdrawn after review M1 |
| 10 | The efficiency line | Kept on the two control steps |
| 11 | T-OQ against D-OQ when the cost measures disagree | The comparator rule of §5.4 (review M7) |
| 12 | One number, 3.0, on both sides of the saturation line | Kept. The negative is reachable; the text says which verdict is more likely (review M2) |

### 25.9 Approval record for revision 5

Nothing is recorded as approved by the human lead, and the lead's Decision 1 for revision 5 has not been taken.

- Independent review (Opus 5.5, 2026-11-15): **READY AFTER M1–M7**, no blocker; `review/REVIEW.md`. It is a Claude review, not Astra review and not human approval.
- The lead's rulings on the draft's questions and on the review: recorded in `LEAD_RULINGS.md` and in §25.8 and §25.10. The lead's check that this text applies them: PENDING.
- **Reported to the human lead, not yet acknowledged in any record:** (a) C_max = 36 hours, 2.25 times his last explicit figure of 16 hours, set by the lead under the Addendum's delegation; (b) the cell 2K/256, which is outside the sizes he was told of in §24.
- Decision 1 for revision 5 (code changes, calibration, rehearsal): NOT TAKEN.
- Decision 2 (the registered run): NOT TAKEN.
- Astra review: NOT_PERFORMED. Claude review is not Astra review.
- No registered seed of S1 has been observed. Nothing in S1 has run since revision 4's calibration.

### 25.10 The independent review, finding by finding

| Finding | What this text does |
|---|---|
| **M1** ruling 9 should not be adopted | Ruling 9 withdrawn by the lead. §10.1 item 0b keeps the return to the human lead and carries the reviewer's sentence after the outcome table |
| **M2** what was seen about the saturation line was not disclosed | §8.10 "It can return a negative", §25.6, §2 expectation 2 and §25.4 item 2 take the reviewer's text |
| **M3** crowding of the oracle codes | §8.10 "A confound that grows with the fact set" and §8.9 item 9 take the reviewer's text; §12 adds a line; the printed label carries the separability figures |
| **M4** the U_P rule makes the 0.80 floor near-automatic | §8.4 row 3, §25.6 and §25.8 question 5 take the reviewer's text |
| **M5** the cap rule's inputs; concurrency | §10.3: the reviewer's C_need text (c, evaluation from rehearsed seconds per snapshot, longest-first packing) and the reviewer's Stages text, followed by the lead's ruling that S1's timing preview, isolated timing, rehearsal and registered run do not overlap P10-S0's registered run |
| **M6** the 256-slot cell was not specified | §5.1 takes the reviewer's bullet. §6.1: 31 configurations, 155 cells, 70 calibration runs. §8.10: the pairs per arm. §10.1 items 0a, 0b and 4. §10.3 and §12: S3 not funded, b(256) F-OQ only |
| **M7** no rule for nearly equal costs; over-statement in §8.5 and §25.7 | The reviewer's optional rule is adopted (§5.4), replacing §22 (i) for this revision. §8.5 takes the reviewer's minimum text, adjusted for the adopted rule (§25.11 item 1). §25.4 item 4 and §25.7 are corrected |
| m1 dense-rate edge | §10.1 item 3: the reviewer's text, EDGE BY TIE-WALK |
| m2 plateau guard labels | §8.2: FLAT BELOW THE DEP FLOOR. §8.5: DENSE NOT LEARNED |
| m3 H8 where it was not calibrated | §8.4 and §10.1 item 2: H8 NOT CALIBRATED AT cell |
| m4 no DEPENDENCE_FAILED row in the saturation arm class | §8.10: the row, and the matching reason in the outcome table |
| m5 item caps | §10.1 item 0a: the reviewer's text |
| m6 §9 "Calibration blocked" row | The reviewer's text |
| m7 printed labels | §8.8: SIZES 1,024–16,384. §8.10: EIGHT FACTS PER SLOT; FULL = PLATEAU RULE WITHIN REGISTERED RUN LENGTHS. The arm class SATURATION_SCALES is renamed SATURATION_PROPORTIONAL_ALL_PAIRS throughout |
| m8 reachability of CAPACITY-NEGATIVE | §8.7: the reviewer's text, with five words added (§25.11 item 2) |
| m9 recording C_max | §10.3: the reviewer's text. §25.9 lists it as reported to the human lead |
| m10 evaluation counted twice at the high end | Stated in §10.3 and in the design notes; the projection is left conservative. The implementer brief forbids test fixtures in which the 1,024-slot cost equals the 4,096-slot cost |

The review's confirmations (its §0) needed no change.

### 25.11 Where this text differs from the reviewer's, and what is disputed

No finding is disputed. Four places differ from the reviewer's wording or go beyond it; each is for the lead to accept or strike.

1. **§8.5 (M7).** The reviewer's minimum text says a disagreement of the cost measures gives MC-AMBIGUOUS and that, if T-OQ's measured cost exceeds D-OQ's, the "storage half supported" reading is reachable only through F-OQ-IVF. That described the draft, in which MC-AMBIGUOUS meant "not established". The lead also adopted the reviewer's optional rule, under which the pair is read in the comparator's favour and counts as established. The two cannot both stand as written, so §8.5 says: the pair is read with D-OQ at the later snapshot; it is MC-SHORT, and the reading goes through F-OQ-IVF only, if that snapshot lies beyond D-OQ's run length.
2. **§8.7 (m8).** "cannot be reached for F-OQ" has "on what was seen and extrapolated" added. Nothing at 1,024 slots was run; if 2K/1K were full and flat, NULL would be reachable on step N1.
3. **§10.3 (M5).** One sentence is added to the reviewer's C_need text: both sides of c are wall seconds of training only, the isolated side being that of the same arm and slot count. The reviewer's text did not say which seconds, and the isolated timing is by arm and slot count, not by fact count.
4. **§10.1 item 0b (M6).** The text states that 2K/256 with no U_L is not run in the registered matrix (the registry is then 30 configurations and 150 cells). The reviewer's bullet fixes the pair as NOT FULL and does not say whether the cell still runs.

A consequence of the comparator rule that the lead should see: for T-OQ against D-OQ at 16,384 slots the analytic multiplier is 5.1. If the CPU measure points the other way, T-OQ is read at U_P against D-OQ at 6·U_P. That is a harsh reading for the store, by design; it makes DENSE AHEAD in the MC reading more likely for T-OQ than under the draft, where the pair would simply not have been established.

### 25.12 The lead's Decision 1 for revision 5, and rulings on the points left open (2026-11-15 UTC)

Taken by the scientific lead under the human lead's recorded delegation that P10 studies may be self-approved. It is not human approval of any result and not Decision 2.

- **The lead's check of the application.** The text was checked against `LEAD_RULINGS.md` and `review/REVIEW.md` on the points of M1–M7 (the return of an unloaded cell, the seen saturation figure, the crowding confound, the U_P declaration, the cap rule and the no-overlap rule, the 256-slot cell, the comparator rule). The implementation audit re-checks the code against this text line by line; that audit, not this check, is the independent one.
- **§25.11's four differences from the reviewer's text are accepted** as written, including that cell 2K/256 is not run if the calibration gives it no run length (registry 30 / 150 in that case, printed as such).
- **Points the implementer brief lists as open (its §6):**
  1. Item caps are per item, not per pooled step.
  2. The contention ratio uses the rehearsal's rates on both sides (alone and under the load that will hold in the registered run), matched by arm and slot count. With no overlap planned it is expected near 1; it is measured, not assumed.
  3. A dense rate is "diverged" if its loss is non-finite at any logged update, or if its raw correct count at the end of the run lies inside the chance interval. Selection among rates that did not diverge reads a_use.
  4. "Another study running" means any live process of `studies.p10s0` or `studies.p10s2` stages. S1's timing preview, isolated timing, rehearsal and registered stages refuse to start while one is alive, and the freeze record states that P10-S0's last training stage has finished.
  5. Covered by the acceptance above.
  6. The saturation class of F-OQ when 2K/256 is not full is INTERMEDIATE as the table gives it. It is not changed.
- **Decision 1: implement revision 5, audit it independently, then calibrate and rehearse on calibration and rehearsal draws only.** No registered seed is generated or observed before the freeze and Decision 2.
- **Still to be acknowledged by the human lead** (reported, no answer recorded): C_max = 36 hours; the cell 2K/256.

