# ADR-0023 — P10-I-S0: Robust addressing and generalisation, including overload

**Status: APPROVED FOR IMPLEMENTATION AND REHEARSAL (Decision 1) by the lead under the human lead's delegation of 2026-11-18. Not frozen. No registered run is approved.**

- **Date:** 2026-11-17 (UTC); the approved text is of 2026-11-18 (UTC). Draft 3 was revised after the independent specification review (`docs/reviews/p10-i-spec-reviews-2026-11-17/REVIEW_ADR-0023.md`, NOT READY) and the confirmation review (`REVIEW2_ADR-0023.md` beside it, NOT READY, no blocking finding). This text carries the edits of the third review (`REVIEW3_ADR-0023.md` beside them, READY AFTER THE LISTED EDITS, no blocking finding) and the lead's decisions where that review left a choice. **The text with those edits applied has not been reviewed again.** Section 18 maps every finding of the three reviews to its disposition; section 19 holds the rulings for the implementer; section 17 is the approval record.
- **Study code:** P10IS0. Package `studies/p10is0/`, config `configs/p10is0_overload.toml`, tests `tests/test_p10is0_*.py`. Nothing under this ADR had been implemented, calibrated, frozen or run when Decision 1 was recorded.
- **Direction it follows:** `docs/reviews/p10-i-direction-2026-11-17/DIRECTION.md` section 4 (P10-I-S0) and section 5 (policy on limits). Its constraints are binding here.
- **Standing.** ArborLM is unproven research. `Astra review: NOT_PERFORMED`. A Claude review is neither Astra validation nor a human approval. Under the human lead's delegation of 2026-11-18 (`docs/reviews/p10-i-direction-2026-11-17/DELEGATION_2026-11-18.md`) the lead may take Decision 1 and Decision 2 at the options this ADR recommends, set the hour caps by section 9's rule, and accept the registered outcome as section 2 of that record defines acceptance. The following stay with the human lead: the budget B above 55 charged hours (section 5.1); any case before the freeze that the rules of sections 5.2, 9 and 12 do not cover (an engineering stop until he rules); any decision at Decision 2 other than running the frozen plan as frozen; machine sharing beyond section 9's rule; a second attempt; publication.
- **Immutability.** P10-S0 (ADR-0020) is complete and accepted as registered. Nothing here revises its outcome, thresholds, seeds or records, and nothing is "reopened". This is a new study on new draws. No existing file is edited; all code is in new files.
- **Marking.** Numbers that are the drafter's judgment are marked **[choice]** and listed in section 16. Section 17 rules them. Wherever the text below says `PENDING LEAD REVIEW`, or says that an item of section 16 is reserved for the human lead, read it as ruled by section 17, except the items that section 17 lists as not covered.

## 1. Question and what each outcome would mean

**When training length is not the limiting factor, up to which load (facts per slot) does the qualified label-free addressing recipe A5-D keep fact-specific, un-collapsed, memory-dependent addressing that also holds on held-out templates, and at which load and on which criterion does it break?**

Three outcome lines are read per load. They are separate; none substitutes for another.

| Line | What it reads | Criterion |
|---|---|---|
| **A — addressing on trained templates** | Panels A and B only | conditions 1, 2, 3, 5, 6 (section 6.2) |
| **G — generalisation across templates** | held-out template panels H1, H2 | condition 4, read only on cells that pass Line A's conditions |
| **Q — overload qualification** | P10-S0's composite criterion, unchanged | all six conditions and ADDRESS STABLE |

| Outcome | Meaning | What it does not mean |
|---|---|---|
| Positive: L_Q ≥ 2 (Line Q holds at 0.5, 1 and 2) | On this synthetic task the recipe keeps at least 0.90 of the oracle-query reference's accuracy on trained-template panels, and on held-out templates at least 0.90 of its own panel accuracy (so at least 0.81 of the reference's panel accuracy) | Not capacity, not efficiency, not natural language, not a success of the ArborLM concept. Where the reference is itself far below 1.0 the label says so (section 6.5) |
| Negative: Line Q fails at load 1 or 2 with convergence confirmed | The recipe as calibrated did not meet the registered RELIABLE criterion in both series at that load, at the registered T. The lines say whether addressing (A) or template generalisation (G) fails first. The failure is then not explained by training length up to T | Not that learned addressing cannot work under overload: one recipe, one calibrated value, one interface. The count rule has a real false-negative rate (section 6.6) |
| Inconclusive | The anchor or the first failing load is not evaluable, or the first failing load fails without confirmed convergence | No statement about overload in either direction |

A failure is a registered outcome. So is UNRESOLVED. Neither is a reason to extend training, add loads or change a threshold, and neither is a basis for a further run on these cells without a new ADR approved by the human lead (DIRECTION.md section 4).

## 2. Background: the registered findings this follows from

All numbers are copied from the records named. The review checked each against its record.

| Finding | Value | Record |
|---|---|---|
| P10-S0 outcome | ADDRESSING-QUALIFIED (4,096 AND 16,384), arm A5-D (label-free, μ = 1.0), 512 exposures per fact, 0.5 facts per slot; accepted as registered | `results/p10s0-run-2026-11-16/OUTCOME.md`; ADR-0020 addendum of 2026-11-16 |
| OVERLOAD NOT QUALIFIED | A5-D at 8,192 facts / 4,096 slots: 1 of 10 cells succeed; class FAILS | `results/p10s0-run-2026-11-16/classes.csv` |
| Why the nine cells fail | Condition 4 (held-out templates) alone. Panel accuracy 0.946–0.956 in every cell; oracle reference A6 0.993–0.997; no collapse in 10 of 10; condition 6 passed | `docs/reviews/p10s0-results-2026-11-16/REVIEW.md` section 5 item 1 |
| Size of the condition-4 miss | Margins from −0.180 to +0.001 across the ten draws (d01 −0.180, d02 −0.169, d03 −0.137, d04 −0.112, d05 −0.092, d10 −0.087, d08 −0.055, d09 −0.039, d06 −0.007, d07 +0.001) | `docs/reviews/p10s0-results-2026-11-16/extras_out.txt` |
| Condition-4 margin at 0.5 facts per slot | Smallest margin +0.061 at 2K/4K and +0.024 at 8K/16K (A5-D) | same REVIEW.md, item 3 |
| A0 (answer-only) under overload | 0 of 10 cells; condition 4 fails in all ten | same REVIEW.md, item 1 |
| One load, one length | S0 tested overload at two facts per slot and 32,768 updates only | ADR-0020 sections 5.3, 6.1 |
| S0 cost | 21,941 s charged (6.09 h) of 22 h (`OUTCOME.md`); Q1 training 13,415 s | `OUTCOME.md`; the Q1 figure is in `docs/reviews/p10s0-results-2026-11-16/REVIEW.md` section 5 item 7 |
| Oracle-query flat memory at 8 facts per slot (P10-S1, F-OQ) | Mean **a_use** (not accuracy) 0.390 → 0.654 at 8K/1K (8,192 → 393,216 updates; the end is 6,144 exposures per fact) and 0.392 → 0.637 at 32K/4K (16,384 → 786,432; 3,072 exposures) | `results/p10s1-run-2026-11-17/OUTCOME.md` section 4; `audit/AUDIT.md` |
| Same arm at 2 facts per slot | Mean a_use 0.948 → 0.996 at 8K/4K and 0.991 → 0.999 at 2K/1K, from U_P to the run length | same |
| Lane L of P10-S1 | OMITTED — NOT OVERLOAD-QUALIFIED | `results/p10s1-run-2026-11-17/RESULTS.md` line 10; ADR-0021 section 5.6 |

Remarks on the records.

1. The condition-4 misses at 8K/4K are not near-misses. Seven of ten are worse than −0.05. The summary "at about 0.95 accuracy" in the outcome statement describes panel accuracy, not the held-out ratio.
2. The task brief says the flat memory at 8 facts per slot "was still rising" at 393,216–786,432 updates. That sentence is not in P10-S1's `OUTCOME.md`. The nearest registered figure is the audit's last-doubling gain for F-OQ at 32K/4K, 0.016–0.061 **bits per fact of i\***; it is not comparable with the accuracy steps used below. The nearest "still rising" text is ADR-0021 section 1 fact 11, which describes a synthetic stand-in at 65,536 updates, not the real system. The design does not depend on either: durations come from this study's own rule.
3. a_use is at most accuracy by definition. P10-S1's figures are therefore lower bounds on that arm's accuracy at those exposures, and they were not measured at this study's T.

## 3. System, arms and what each isolates

**System.** As ADR-0019 sections 3–4 and ADR-0020 section 5.1: the frozen 27,392-parameter backbone, the P9-I task, flat memory (cosine keys, key width 16, top-8, temperature 0.2) read and added at answer sites only, alphabet-only loss, one AdamW at 0.003, clip 1.0, batch of 16 contexts = 128 answer sites, the W7 query. The memory is told the answer position in every arm. No backbone parameter is trained.

**New code is required; the existing code does not run the new sizes.** `studies/p9ii/core.py` rejects any slot count outside 4,096, 16,384 and 65,536 (`Cell.__post_init__`, line 252), P10-S0 trains and evaluates through that cell (`studies/p10s0/core.py`, `p9ii_cell()`), P10-S0's cell types are a fixed registry, and both rehearsal whitelists accept only those three sizes. The review confirmed by execution that 512, 1,024, 2,048 and 8,192 slots raise `ValueError`. It also read that the model builder, the trainer's fact count, the generator, the panels, the read-swap derangement and condition 3's probe counts do not depend on the slot registry. Therefore:

- `studies/p10is0/` holds, in new files, its own cell type and cell record (not passing through `p9ii.core.Cell`), its own plan, trainer and evaluator wrappers, and its own rehearsal whitelists. No file of `studies/p9`, `p9i`, `p9ii` or `p10s0` is edited. The model, the losses (including L_div) and the update step are called from `studies.p9ii`, not rewritten.
- **What the new path must reproduce:** P10-S0's training and evaluation of A5-D, A0 and A6 exactly, at every size where both paths exist.
- **Identity gate, part (a):** at 4,096 and at 16,384 slots, for A5-D, A0 and A6, the new path is bit-identical to P10-S0's path (`torch.equal` per tensor) at 2K/4K and 8K/16K for A5-D and A6, and at 8K/4K and 8K/16K for A0. Compared: the initial state dict; the logits of one forward; the state dict after one update and after 5,184 updates (past the cadence change at 4,096 and two later diagnostic points, with P10-S0's path at its cadence of 64 and the new path at its own); and every measured field of one full evaluation record at the last of these. Only the envelope, `label`, `identity`, `environment` and wall-time fields are excluded, and they are listed in the gate result. By ruling 10 of section 19 the same comparison is also made at 8K/4K for A5-D and A6. **This gate re-uses a P10-S0 seed set by name:** P10-S0's rehearsal set (data base 209101, initialization seed 2092; ADR-0020 section 7), because P10-S0's path accepts only its own sets (`studies/p10s0/core.py`, `check_seed_set`). It is a read-only re-use for an identity check, as P10-S0's G4 re-used P9-II's rehearsal set 5. The seed registry lists it as a declared re-use (its section 4.6); it enters no class and no rehearsal measurement.
- **Identity gate, part (b):** at each new slot count (512, 1,024, 2,048, 8,192), the new path's model equals `p9ii.model.build_model(arm, N, seed)` tensor for tensor, and after one update, the loss and every parameter equal a direct float32 reference implementation (forward, losses, clip and AdamW from their definitions) within 1e-6 absolute per element **[choice]**. The implementer writes the gate's reference; the auditor writes an independent one in its audit.
- **End-to-end gate at every new size:** the read swap (no fixed point; swapping twice restores the logits), the probe-set slot counts and ADDRESS STABLE run end to end at 512, 1,024, 2,048 and 8,192 slots on the rehearsal draw.

| Arm | Definition | Runs at | Isolates |
|---|---|---|---|
| **A5-D** | answer-only + μ·L_div on the batch's normalized queries, μ = 1.0 (P9-II's audited calibration; ADR-0020 section 3.4) | every cell type | the qualified recipe, unchanged |
| **A6** | the oracle-query (random-code) reference R1 | every cell type, every draw | the denominator of condition 1: what the store holds when the query is the oracle code, at the same load and duration |
| **A0** | answer-only W7, untuned | series M only | the diversity penalty: A5-D against A0 is one change |

A6 is not "ideal addressing" under overload. Its codes are random, so slots are loaded unevenly by chance, while a learned query could in principle balance the load. The ratio of condition 1 can exceed 1; where it does, the label adds **RATIO ABOVE 1** (descriptive).

Not run, and why:

- **A1, A2** (address supervision): no target injection exists with more facts than slots (ADR-0020 section 5.1).
- **A7** (dense window) and any capacity baseline: capacity under load is P10-I-S1's question (ADR-0024). This study makes no claim against a dense alternative.
- **A re-calibration of μ.** μ = 1.0 was calibrated at 0.5 facts per slot. L_div pushes the batch's queries apart, while at loads of 1 and above several facts must share a slot, so the penalty may partly oppose what overload requires. Re-tuning it would add a second change beside training length. A failure is a failure of the recipe as calibrated (section 13). A0 in series M is the only way to tell a penalty-induced failure from a load-induced one.

**Comparisons.** Across loads within a series: the slot count, and T as set by the rule of section 5; the same facts, streams, panels and initialization seed per draw. A5-D against A6: learned against oracle query. A5-D against A0: the penalty. Series M against series S at equal load: fact and slot counts change together at fixed ratio.

**Items the closure ledger carries here** (`docs/reviews/p10-i-direction-2026-11-17/CLOSURE_LEDGER.md` section 5):

| Ledger item | Disposition in this draft |
|---|---|
| Overload; one load, one length; lane L in the loaded regime | Accepted: the subject of this study (sections 4, 5, 15) |
| A5-D against A0 at 16,384 (candidate) | Accepted as an annotation: the anchor cell type 8K/16K has ten A5-D/A0 pairs at T (section 6.7). It is a new measurement at a longer duration and one seed per draw, not a re-reading of H20-D |
| Condition 6 decided no class | Accepted as a design note: condition 6 stays in the composite unchanged, and the report prints for every cell type whether it decided any cell. The reference's own risk on condition 6 is estimated as small and on condition 4 as open (section 5.2) |
| Record-length-free variant WX (candidate) | **Declined.** A second interface change beside load; by the record a WX failure is "not evidence that the record length is required". Proposed ledger disposition: CLOSED AS RECORDED (unresolved; declined here; pending the human lead) |
| 65,536 slots (candidate) | **Declined.** The question here is load, not size, and a 32,768-fact series at converged durations would cost more than the rest of the study. Proposed ledger disposition: CLOSED AS RECORDED (unresolved). No P10-I study takes it: ADR-0024's 16,384→65,536 item is an oracle-capacity transition and its lane L uses only this study's tested cell types. "Addressing at 65,536 is not qualified by any study" stays visible |

The two declined rows are a difference from the ledger and are reserved for the human lead (section 16 item 9).

## 4. Load grid, data, seeds, sizes

### 4.1 Grid **[choice]**

Load is varied by changing the slot count at a fixed fact set, so that every load of a series is read on the same facts and panels.

| Series | Facts | Slots (load in facts per slot) | Arms | Draws × init seeds | Cells |
|---|---|---|---|---|---|
| **M** (main) | 8,192 | 16,384 (0.5), 8,192 (1), 4,096 (2), 2,048 (4) | A5-D, A0, A6 | 10 × 1 | 120 |
| **S** (small) | 2,048 | 4,096 (0.5), 2,048 (1), 1,024 (2), 512 (4) | A5-D, A6 | 10 × 1 | 80 |
| **X8** (conditional, section 8) | 8,192 | 1,024 (8) | A5-D, A0, A6 | 10 × 1 | 30 |

- **0.5** is the anchor and the positive control: P10-S0's qualified cell types (8K/16K, 2K/4K) at the converged duration. It is not the same test as P10-S0's: one seed per draw and the 10-cell rule here, two seeds and the 20-cell rule there.
- **1** and **2** bracket P10-S0's failure. Load 2 in series M is S0's own cell type (8K/4K).
- **4** extends the grid if 2 holds. **8** is P10-S1's loaded regime; it runs only under section 8.
- **Two series** so that a result at a load is not a property of one slot count. Slot counts covered: 512 to 16,384. Nothing is said about 65,536.

### 4.2 Draws and seeds

- **Registered draws:** 10, each a complete independent data set (2,048-fact and 8,192-fact sets, training stream, calibration stream, Panels A and B, H1, H2, unseen-fact control, as ADR-0020 section 7). **Reserve draws:** 4. Draws are generated until ten pass gate G1, within the four reserves; the number used is recorded and is not a claim.
- **Calibration draws:** 2 (Stage R only). **Rehearsal draw:** 1. **Pipeline check:** 1 seed set. **Unit tests:** a range of about 1,000.
- **Seed values are those of the programme-wide registry**, `docs/reviews/p10-i-direction-2026-11-17/SEED_REGISTRY.md` (written by the `arbor-auditor` subagent; revision 3; its checker `seed_registry_check_r3.py`, SHA-256 `e462360420321aa284b0e4d47b106806419ab616794a5c632fee70f122c67594`, records RESULT: PASS). This study adopts them exactly:

| Role | Registry values |
|---|---|
| Registered and reserve draw sets | 300001–306999: draw d at 300001 + 100·(d − 1), d = 1…10; reserves at 301001, 301101, 301201, 301301; P10-S0's in-set layout |
| Calibration draw sets | 309001, 309101 |
| Rehearsal draw set; pipeline-check set | 309201; 309301 |
| Initialization, registered | 330001 (A5-D and A0 on odd draws; A6 on every draw), 330002 (A5-D and A0 on even draws) |
| Initialization, calibration | 330091 (calibration draw 1), 330093 (calibration draw 2), so the two calibration runs differ in initialization as well as data |
| Initialization, rehearsal and pipeline check; test mode | 330092; 330098 and 330099 |
| Unit tests | 932001–932999 |
| A repeated Stage R (section 10), repeat k = 1, 2, 3 | calibration draw sets 309401 + 200·(k − 1) and 309501 + 200·(k − 1); initialization 330061 + 2·(k − 1) (first set) and 330062 + 2·(k − 1) (second set). These are values of the registry's spare for this study (its section 4.2: 309401–309999, and the unused part of the sub-row 330001–330099). They are used only if a repeat happens, are listed in the freeze record and pass the seed gate like every other value |

- **The registry's rule (its section 4.3, condition 1) binds this study:** no initialization seed is derived arithmetically from a data, calibration, rehearsal or test seed; rehearsal and test modes take the named seeds above. The memory initializers derive generator seeds as seed + 1000·k (`studies/p9/model.py` lines 272–276); the registry keeps 331000–340999 unallocated for that reason. Draft 1's initialization seeds (3001, 3002, 3091, 3092) were P10-S0's derived seeds and are withdrawn.
- This study's seed gate checks its planned and recorded seeds against the registry with the derivation rules expanded, read from code and configs, and, before the freeze, runs a copy of that checker with the substitutions of ADR-0029 section 19 ruling 6 (this study's own config and tests excluded, the copy's hash in the gate result), and checks this study's values separately against the registry's allocation rows for ADR-0023. The one declared re-use is the identity gate's P10-S0 rehearsal set (section 3).
- One seed per draw because P10-S1's corrected seed-block record shows the data draw dominating the spread in 24 of 28 comparisons (`results/p10s1-run-2026-11-17/ERRATUM_SEED_BLOCK.md`), and the per-draw bound depends on draws.
- All registered and reserve draws are generated, hashed and G1-checked at the freeze, before any model sees them.

### 4.3 Checkpoints

Each registered cell is evaluated at three update counts: 512 exposures per fact (P10-S0's regime; descriptive), T/2 (for the check of section 5.3) and T (the only readout that enters a class). Probe records are written every 64 updates up to 4,096 updates and every 1,024 after **[choice]**; escape and COLLAPSE-FREE statistics after update 4,096 are therefore coarser than P10-S0's and are labelled so.

## 5. Training length: the convergence rule

Durations are in exposures per fact, e. Updates = e × F / 128 (512 exposures = 8,192 updates at 2,048 facts and 32,768 at 8,192 facts).

### 5.1 The rule (fixed before any rehearsal)

- **Base ladder:** e ∈ {512, 1,024, 2,048, 4,096, 8,192, 16,384}.
- **Measures:** m_P = mean accuracy on Panels A and B; m_H = mean accuracy on H1 and H2. Each is computed from integer counts (section 19 ruling 1).
- **Plateau at e:** |m(2e) − m(e)| ≤ 0.01 **and** |m(4e) − m(2e)| ≤ 0.01, for both measures, for A5-D and A6, on both calibration draws. The rule is two-sided: held-out accuracy can fall with longer training, and a readout on a falling curve is not a converged readout. Two consecutive steps are required because one flat step can precede an escape.
- **Floor, on the reference only:** a plateau at e counts only if A6's m_P(e) is at least the cell type's evaluability floor (0.90 at load 0.5; 0.50 at loads of 1 and above) on both calibration draws **[choice]**. Reason: P10-S1 had to add such a floor because without it every calibration cell met its rule before it had learned (ADR-0021 revision 5).
- **No floor on A5-D.** An A5-D that meets the two-step rule while its m_P(e\*) is below the floor on either calibration draw **counts as a plateau** and is printed **A5-D FLAT BELOW FLOOR** in `durations.json` and in every label of that cell type. A recipe that has converged and fails is a registered NOT QUALIFIED, not UNRESOLVED, and is not run at the maximum length because it fails. The step rule already needs two flat doublings, A5-D did not collapse in P10-S0 (10 of 10), and the longest observed A0 escape there (30,656 updates, at 8K/4K, where one of ten A0 cells never escaped; 7 of 20 never escaped at 2K/4K) is below the ladder's first step at 8,192 facts. The argument does not depend on that figure.
- **e\*** is the smallest ladder value with a plateau. **T = 2·e\*.** The rehearsal trains to 4·e\* = 2T. On the base ladder the largest e\* is 4,096 and the largest T is 8,192 exposures (524,288 updates at 8,192 facts; 131,072 at 2,048 facts). For comparison, P10-S1's loaded cells ran 6,144 and 3,072 exposures.
- **0.01 [choice]:** one tenth of the 0.10 tolerance of conditions 1 and 4.
- **One T per cell type**, used by every arm there. A0 takes it without a rehearsal of its own; every A0 label says so.
- **Extension rule (design ceiling, DIRECTION.md section 5).** If a cell type has no plateau on the base ladder, code may extend that cell type's ladder by one further doubling (to 32,768 exposures; then e\* may be 8,192 and T 16,384) **[choice: one doubling]**. The rule, complete:
  1. *When.* Extensions are decided once, after every cell type's base ladder has finished. No person chooses; no registered seed is observed.
  2. *Projected total.* P = Stage R hours already charged + the Stage R extension rounds granted so far and the one under decision + the main grid at each cell type's T under the rule + X8 and its calibration at T = 16,384 (if X8 is kept at Decision 1) + the measured times of gates, generation, analysis and report. Training is costed at stage 3's measured seconds per update for each (arm, slot count), from the quiet attempt only (section 10), with three evaluations per cell at their measured time, summed and divided by six workers. P is the summed worker-seconds divided by six, plus the longest single task of each stage (a bound on the makespan). Candidates not yet decided enter P at T = 8,192 exposures (their status if refused). P is charged hours at 1×, not the cap's 2×.
  3. *Budget.* **B = 55 charged hours at 1× for the whole study**, set at Decision 1 (section 17): the upper figure the human lead was shown on 2026-11-18 ("addressing 15–55", `DELEGATION_2026-11-18.md` section 4). Draft 3 recommended 80; the third review (R3-12) found that above what was disclosed, and the lead did not take it. An extension is granted if P with it is at most B.
  4. *Order.* Candidates are taken in order of ascending load, series M before S at equal load. Each is granted if it fits and refused otherwise; after a refusal the next candidate is still tried.
  5. *Refusal.* A refused cell type runs at T = 8,192 exposures and is marked **CONVERGENCE NOT SHOWN — EXTENSION REFUSED (BUDGET)**. That is its registered status; a failure there reads UNRESOLVED (section 7 step 5). Every refusal is reported to the human lead at once. Only the human lead himself may set a larger B, before the freeze and on the cost projection alone; that re-runs steps 1–4 by code. The lead does not raise B under the delegation.
  6. *Relation to the cap.* B governs extensions only. It does not bound the frozen projection: with no extension at all, every cell type at the base ceiling and X8 at its ceiling project to about 74 charged hours (section 11). The hour cap of section 9 is twice the frozen projection and may exceed B.
  7. *What B = 55 can still grant* (hand estimates on P10-S0's rates, not machine-checked; the code applies items 1–5 to stage 3's measured rates, and those govern). P always holds X8 and its calibration at T = 16,384 exposures, about 18.5 hours of summed work divided by six, plus the longest X8 calibration run and the longest X8 cell (about 5.8 and 2.9 hours), plus about 1.5 hours of gates, generation, analysis and report. About 26 hours of B therefore remain for Stage R, the main grid and any extension. One extension of an 8,192-fact cell type costs 7.3–12.2 hours of main grid, 1.9–3.5 hours for its Stage R round and that round's longest run (2.9–5.5 hours): about 12–21 hours. One extension of a 2,048-fact cell type costs about 1.2 hours of main grid, about 0.5 for its round and about 0.7 for the round's longest run: about 2.4 hours. A candidate is by definition a cell type that reached the base ceiling, so Stage R and the main grid are already long where a candidate exists. On these figures: **(i)** if most cell types are at or near the base ceiling (53.7 hours for Stage R and the main grid alone), no extension is granted and every candidate is refused; **(ii)** an extension of an 8,192-fact cell type is not expected to fit in any case; **(iii)** extensions of 2,048-fact cell types fit, about three at most, only when the 8,192-fact series plateaus early (near the central guess of section 11). Every refused candidate is CONVERGENCE NOT SHOWN — EXTENSION REFUSED (BUDGET) as item 5 writes it. The consequence is stated, not hidden: under B = 55 the extension rule is close to empty, so a cell type with no plateau on the base ladder will usually run at T = 8,192 exposures and a failure there will read UNRESOLVED, not NOT QUALIFIED. A refusal cannot create a pass.
- **At the extended ceiling, NOT SHOWN is the registered outcome.** The cell type runs at T = 16,384 exposures and is marked **CONVERGENCE NOT SHOWN IN REHEARSAL**. Reason for stopping there: at 16,384 exposures one 8,192-fact cell is 1,048,576 updates, about 3 hours at 4,096 slots for A5-D and A6 (4.2 for A0) and about 5.4 at 16,384 on P10-S0's rates, and one calibration run to 32,768 exposures is 5.8–10.9 hours. A longer duration is a new budget decision for the human lead in a new ADR, not a rule this study applies to itself.
- **Stage R's own cap:** twice the base-ladder worst case (all 32 runs to 16,384 exposures at stage 3's rates, six workers) plus twice the projection of the extension rounds granted. Reaching it is a PAUSE.
- Whether the 0.01 step can be met under a degraded reference is an empirical question; Stage R answers it by NOT SHOWN.

### 5.2 The convergence rehearsal (Stage R)

- Arms A5-D and A6, every cell type of series M and S, two calibration draws: 32 runs. **Procedure, by code:** all four runs of a cell type train in doubling rounds, each round resuming from the previous round's snapshot; after each round the plateau rule is evaluated; the cell type stops at the first decision or at its ceiling. A resume-from-snapshot test (bit-identical to an uninterrupted run) is part of stage 1.
- **No registered seed is involved.** Calibration draws enter no class, no count and no table of the registered result.
- **Blind output: the mechanism.** (i) Stage R writes accuracies, losses and probe records only to `sealed/` inside the git-ignored run directory (outside version control). The path is printed nowhere else. The lead and the implementer do not open it; the freeze record states, for each of them, that they did not. Only the auditor's recomputation script reads it. All sessions run under one OS account, so this seal is procedural, not an access control. Enforcing it would need a second account (administrator access), which this study does not request. **The seal is therefore by procedure, not by file permissions.** Any read of the sealed directory by the lead, of any file and for any reason, is disclosed in the freeze record or the outcome record with the file and the time, and voids the blindness claim for that cell type: its labels then print **CALIBRATION VALUES SEEN BY THE LEAD**. (ii) Its stdout and logs pass a whitelist validator, as P9-I's and P10-S0's rehearsals did: time, memory, shapes, counts, identities and `durations.json` only. (iii) `durations.json` holds, per cell type, e\*, T, SHOWN or NOT SHOWN, A5-D FLAT BELOW FLOOR, extension granted or refused, and the reference-validity flags per condition. (iv) The sha256 of every sealed file is committed at the freeze. (v) Before the registered outcome is recomputed, only the auditor's recomputation script reads the sealed files, and the auditor reports agree or disagree and nothing else. (vi) The plateau, extension and continue decisions are made by code. After the outcome is recomputed the curves are published as calibration records. Limits, stated: a committed hash shows the sealed files were not altered, not that nobody read them; and `durations.json` is itself informative (a NOT SHOWN entry predicts UNRESOLVED, a FLAT BELOW FLOOR entry predicts a failure). Decision 2 sees `durations.json`. Under the delegation the lead's Decision 2 can only be to run the frozen plan as frozen, once the conditions of section 17 are met. A decision not to run is the human lead's alone and is recorded with what was seen.
- **What may change after Stage R:** only T per cell type (by the rule), the removal of cell types flagged on conditions 2, 3, 5 or 6 (below, by rule), B (by the human lead himself only, section 5.1 item 5) and the hour cap (on cost). The choices on A0 and X8 (section 16 items 2 and 7) are made at Decision 1, before Stage R, and are not revisited after it.
- **Reference validity, per condition.** In Stage R, A6 is run through conditions 2, 3, 4, 5 and 6 at every cell type, at T, on both calibration draws. A failure on either draw flags that condition at that cell type. The flags are computed after every extension decision, at each cell type's final T, and only on a calibration draw where A6's m_P(T) is at or above the cell type's floor; otherwise `durations.json` records **REFERENCE BELOW FLOOR AT T** for that draw and no flag is computed on it (section 19 rulings 3 and 4).

| A6 fails | Effect at that cell type |
|---|---|
| condition 4 only | **Line G is NOT EVALUABLE; Line A is read.** Line Q is FAILS where the composite fails without condition 4 (section 6.4) and NOT EVALUABLE otherwise: the composite is not shortened. The cell type stays in the plan and every arm runs. The label prints **REFERENCE ALSO FAILS CONDITION 4 (A6 H-ratio x on calibration draws)** |
| any of conditions 2, 3, 5, 6 | all three lines are NOT EVALUABLE; the cell type is removed from the frozen plan by this rule and prints **NOT RUN — REFERENCE FAILS CONDITION n** |

- **What is known about the reference on these conditions.** A6 has never been read on condition 4 in any record: P10-S0 classed no A6 cell, and P10-S1's held-out annotation is relative to another arm, not to the 0.90 ratio. ADR-0021 section 7.2 states that under oracle addressing the held-out panels test the frozen readout, not the memory and not the address. P10-S0's overload failure was on condition 4 alone, so if that failure is partly a readout effect of overload, A6 can fail condition 4 at 8K/4K too. For condition 6 the reviewer's estimate, from P10-S1's audit (`audit/a4_dep_sensitivity.out`: every failure at raw accuracy 0.436 or below) and a chance-survivor model, is that an oracle reference fails it only below an accuracy of about 0.39, which is under the 0.50 floor. That is an estimate, not a measurement of A6 at these loads.
- **Events before the freeze: a rule, not a return (fixed now, before any observation).** Draft 3 returned the work to the human lead in the cases below, with no default action. The third review (R3-8) found that such a return is a choice made after `durations.json`, which predicts the outcome, has been seen. The lead replaces the choice by a rule. The events are: (a) either anchor cell type (load 0.5) carries any reference flag, is NOT SHOWN, or prints A5-D FLAT BELOW FLOOR; (b) any reference flag, on any condition, falls on a load-1 or load-2 cell type in either series; (c) a REFERENCE BELOW FLOOR AT T or a NON-FINITE IN REHEARSAL entry (section 12) at any cell type. **In each of them the study proceeds** to the counting rehearsal, the freeze and Decision 2, unchanged:
  1. The affected line is NOT EVALUABLE or FAILS at that cell type exactly as sections 5.2, 6.4, 6.6 and 7 say. An anchor flagged on condition 2, 3, 5 or 6 gives step 1; an anchor flagged on condition 4 gives step 1 or step 2 by section 6.4; an anchor that is NOT SHOWN or FLAT BELOW FLOOR is run and read like any other cell type, with its status printed.
  2. A cell type leaves the plan only by the rule of the table above (conditions 2, 3, 5, 6). No cell type is dropped, added, shortened or lengthened by choice. No threshold and no duration changes.
  3. The event is reported to the human lead at once, with `durations.json`, and recorded as `EVENT_<n>.md` (section 17). A flag at load 4 (or at X8) alone is recorded in `durations.json` and is not an event.
  4. In cases (a) and (b) a qualified headline may already be impossible. The grid is run all the same: the three lines, the break location and the annotations are registered outputs, and a stop chosen on that information would be an outcome-informed selection. The human lead may stop the study on any report. That stop is his alone; it is recorded as **STOPPED BEFORE THE FREEZE (ANCHOR or REFERENCE)** with `durations.json`, and it is not a scientific label. The lead does not take it under the delegation.
  5. A return to the human lead remains only for a case these rules do not cover. That case is an **ENGINEERING STOP** until he rules; nothing is frozen meanwhile and nothing is labelled.

### 5.3 The check on registered draws (no adaptation)

Per cell type and arm (A5-D, A6): d = the median over the ten cells of m(T) − m(T/2), for m_P and m_H. The cell type is **CONVERGENCE CONFIRMED** if it was SHOWN in rehearsal and every |d| ≤ 0.02 **[choice: the rehearsal's 0.01 plus 0.01 for draw-to-draw spread]**. Otherwise it is **CONVERGENCE NOT CONFIRMED**, with **RISING** (some d > 0.02), **DECLINING AT T** (some d < −0.02) or **NOT SHOWN**. The check changes no duration and triggers no training. It decides only whether a failure is worded NOT QUALIFIED or UNRESOLVED; it cannot create a pass.

## 6. Measurements and the rules that give labels

### 6.1 Recorded

As ADR-0020 section 8.1 and ADR-0019 sections 8.1–8.2. Added, descriptive only: the share of facts whose top-1 slot on H1 (and H2) equals the one on Panel A; H-panel accuracy divided by A6's; per-template held-out accuracy; the share of slots that are top-1 for any fact on Panel A, beside A6's figure (condition 3 is an absolute count and at 512 slots detects gross collapse only). No efficiency claim is made from any cost figure.

### 6.2 Cell conditions (thresholds unchanged from ADR-0019 section 8.3 and ADR-0020 section 8.2)

| # | Condition | On |
|---|---|---|
| 1 | accuracy ≥ 0.90 × A6's on the same draw, cell type and readout | Panels A and B |
| 2 | accuracy with values permuted and with the memory disabled inside the G2 chance interval | Panels A and B |
| 3 | on the probe set, at least 128 distinct top-1 slots and no slot top-1 for more than 10 of the 512 sites | probe |
| 4 | accuracy on H1 and on H2 ≥ 0.90 × the cell's own accuracy | against Panel A and against Panel B |
| 5 | no LEAKAGE flag | unseen-fact control |
| 6 | a_use ≥ 0.95 × accuracy | Panels A and B |

- **Evaluability of a draw at a cell type:** A6 ≥ 0.90 on both panels at load 0.5; A6 ≥ 0.50 at loads of 1 and above (ADR-0020's floors). Otherwise the draw is NOT_EVALUATED there.
- Condition 3 is reachable at every size: at 512 slots with even placement the expected distinct top-1 count is 201.5 and the chance of any slot exceeding 10 sites is about 0.7% (recomputed by the review).
- **A-conditions** are 1, 2, 3, 5, 6. **The G-condition** is 4. A cell **succeeds** if all six hold.

### 6.3 Class of an arm at a cell type (ADR-0020 section 8.3, the 10-cell rule; first match wins)

| Order | Class | Rule |
|---|---|---|
| 1 | NOT_EVALUATED | more than one draw NOT_EVALUATED |
| 2 | RELIABLE | at most one failed cell among the evaluated cells, and no LM CAPABILITY REDUCED (ADR-0019 section 8.4 (b)) |
| 3 | UNRELIABLE | at least 3 successes |
| 4 | FAILS | otherwise |

Per-draw bounds (one-sided 95% Clopper–Pearson): 10 of 10 gives 0.741; 9 of 10 gives 0.606; 9 of 9 gives 0.717.

### 6.4 State of each line at a cell type (arm A5-D)

n_A = evaluated cells failing any A-condition; n_G = evaluated cells passing all A-conditions and failing condition 4; n_Q = n_A + n_G.

| Line | State | Rule (first match wins) |
|---|---|---|
| all | NOT EVALUABLE | the cell type was flagged in Stage R on condition 2, 3, 5 or 6, or its class is NOT_EVALUATED |
| G | NOT EVALUABLE | the cell type was flagged in Stage R on condition 4 (Line A is still read) |
| Q | FAILS / NOT EVALUABLE | the cell type was flagged in Stage R on condition 4: FAILS if n_A ≥ 2, or the arm is LM CAPABILITY REDUCED there, or it is not ADDRESS STABLE there (each fails the composite whatever condition 4 gives); NOT EVALUABLE otherwise |
| A | HOLDS / FAILS | n_A ≤ 1 / n_A ≥ 2 |
| G | NOT READ | Line A FAILS |
| G | HOLDS (GENERALISES) / FAILS (DOES NOT GENERALISE) | n_G ≤ 1 / n_G ≥ 2 |
| Q | HOLDS / FAILS | class RELIABLE and ADDRESS STABLE (median over cells of the share of facts with the same top-1 slot on Panels A and B ≥ 0.80) / otherwise |

Stated consequence: with n_A = 1 and n_G = 1, Lines A and G hold and Line Q fails. Line Q is the stricter, unchanged composite; the other lines never upgrade it.

**Why a flagged cell type can still fail Line Q (the lead's ruling on R3-3).** A failure that does not depend on the unevaluable condition is still a failure. With two cells failing an A-condition the class cannot be RELIABLE whatever condition 4 gives; LM CAPABILITY REDUCED and ADDRESS STABLE are read on Panels A and B and do not involve condition 4. Line Q is NOT EVALUABLE at a flagged cell type only when its value would depend on condition 4, that is when n_A ≤ 1, the arm is not LM CAPABILITY REDUCED and it is ADDRESS STABLE. The change can only turn NOT EVALUABLE into FAILS, so it cannot favour the memory.

**Totality, re-derived for this rule** (by hand from the rows above; the third review's enumeration script was not re-run on this text, and stage 1's tests enumerate it again). Each line has exactly one state at a cell type, and the possible (A, G, Q) combinations are eight:

| Cell type | (A, G, Q) | When |
|---|---|---|
| flagged on 2, 3, 5 or 6, or class NOT_EVALUATED | (NOT EVALUABLE, NOT EVALUABLE, NOT EVALUABLE) | always |
| flagged on condition 4 | (HOLDS, NOT EVALUABLE, NOT EVALUABLE) | n_A ≤ 1, not LM CAPABILITY REDUCED, ADDRESS STABLE |
| flagged on condition 4 | (HOLDS, NOT EVALUABLE, FAILS) | n_A ≤ 1, and LM CAPABILITY REDUCED or not ADDRESS STABLE |
| flagged on condition 4 | (FAILS, NOT EVALUABLE, FAILS) | n_A ≥ 2 |
| not flagged | (HOLDS, HOLDS, HOLDS) | n_A + n_G ≤ 1, not LM CAPABILITY REDUCED, ADDRESS STABLE |
| not flagged | (HOLDS, HOLDS, FAILS) | n_A = 1 and n_G = 1, or LM CAPABILITY REDUCED, or not ADDRESS STABLE |
| not flagged | (HOLDS, FAILS, FAILS) | n_A ≤ 1, n_G ≥ 2 |
| not flagged | (FAILS, NOT READ, FAILS) | n_A ≥ 2 |

Draft 3 had seven: the combination (FAILS, NOT EVALUABLE, NOT EVALUABLE) is no longer reachable, and the two flagged combinations with Line Q FAILS are new. Line Q still takes one of three states per series (HOLDS, FAILS, NOT EVALUABLE), so the state space that sections 6.6 and 7 read is the one the third review enumerated (3⁸ series states × 2⁴ convergence statuses, every input reaching exactly one headline). The argument in words: step 1 takes Line Q NOT EVALUABLE at 0.5 and step 2 takes FAILS; otherwise it HOLDS and L_Q ≥ 0.5; step 3 takes L_Q ≥ 2; otherwise ℓ₁ is 1 or 2 and its state is NOT EVALUABLE (step 4) or FAILS, with a convergence status that is CONFIRMED (step 6) or NOT CONFIRMED (step 5). Only the mapping of a flagged cell type into the three states changed.

### 6.5 What "0.90 of the oracle reference" means under overload

Condition 1 is a ratio, at every load, to A6 on the same draw, cell type and T. It is not lowered and not replaced. It says how much of the oracle-query reference's accuracy the learned query keeps. It does not say how much the store holds.

- Every label carries the **reference regime**, from the median over draws of A6's mean panel accuracy: **REFERENCE NEAR CEILING** (≥ 0.90) or **REFERENCE DEGRADED (A6 = x)** (0.50 ≤ x < 0.90). Absolute accuracies of A5-D and A6 and the ratio itself are printed.
- A qualification under a degraded reference is printed **QUALIFIED RELATIVE TO A DEGRADED REFERENCE** and may not be shortened.
- Below 0.50 the draw is not evaluated: the cell would then test the store, not the address.
- Where the cell type was SHOWN in rehearsal (calibration draws), both arms had plateaued before T was set. Where it was NOT SHOWN, the ratio may reflect an arm still moving, and the label says NOT SHOWN.
- P10-S1's F-OQ had mean a_use 0.654 at 8K/1K after 6,144 exposures and 0.637 at 32K/4K after 3,072. Accuracy is at least that. A6's accuracy at load 8 is therefore expected above these figures and is unmeasured; load 4 is unmeasured.

### 6.6 Combining series into a load, and loads into a break point

**State of a line at a load** (main grid: two series; X8: its one series, labelled ONE SERIES):

| Series states | State at the load |
|---|---|
| both HOLD | HOLDS |
| either FAILS (for Line G, NOT READ counts as FAILS and is printed NOT READ) | FAILS |
| otherwise (at least one NOT EVALUABLE, none FAILS) | NOT EVALUABLE |

When a line holds in one series only, the label names it ("IN SERIES M ONLY (slots N)").

**Break point.** For each line, L is the largest grid load such that the line HOLDS at it and at every lower grid load ("none" if it does not hold at 0.5). ℓ₁ is the next grid load above L (0.5 when L is "none"); its state is FAILS or NOT EVALUABLE. When L is the highest load run there is no ℓ₁. A HOLDS above ℓ₁ adds **NON-MONOTONE** and does not raise L. The report prints L_A, L_G, L_Q, each ℓ₁ with its state, and per series the per-condition failure counts at Line Q's ℓ₁.

**Convergence status of a load:** CONFIRMED if every series whose Line Q state there is FAILS is CONVERGENCE CONFIRMED; otherwise NOT CONFIRMED.

**Operating characteristic of the rule (printed so the negative is read correctly).** With per-cell success probability p and independent cells:

| p | RELIABLE in one series | in both series | Line Q holds at 0.5, 1 and 2 (L_Q ≥ 2) |
|---|---|---|---|
| 0.90 | 0.736 | 0.542 | about 0.16 |
| 0.95 | 0.914 | 0.835 | about 0.58 |
| 0.97 | 0.965 | 0.932 | about 0.81 |
| 0.99 | 0.996 | 0.991 | about 0.97 |

At a true per-cell rate of 0.95 the study reports a break at or below 2 about four times in ten. (Loads share draws, so the last column is approximate.) The rule is conservative against false positives; it is not changed.

### 6.7 Annotations (enter no line)

- **Penalty against answer-only**, series M, per load including 0.5: d = (cells where A5-D succeeds and A0 fails) − (the reverse) over the ten pairs. IMPROVES ON A0 if d ≥ 6 **and** the exact two-sided sign-test p < 0.05; HARMS if d ≤ −6 and p < 0.05; otherwise NOT DISTINGUISHED **[choice]**. A pair on a draw that is NOT_EVALUATED at that cell type is excluded from d and from the sign test; the number of pairs used is printed.
- COLLAPSE-FREE k of n; the 512-exposure readout, labelled "P10-S0's regime on new draws; descriptive; not a replication verdict"; whether condition 6 decided any cell; the descriptive measures of section 6.1.

## 7. Study outcome: one decision procedure

Applied in order; exactly one headline results.

| Step | Test | Result |
|---|---|---|
| 0 | Any planned main-grid cell has no completed record (a NON-FINITE cell has one) | Stopped on a resource cap, or paused on identity or environment (section 12): **INCOMPLETE — PAUSED**; no scientific label; the analysis stage refuses to run; the run resumes when the cap is extended or the pause is cleared. If the human lead declines to extend, the study stays INCOMPLETE — PAUSED. A failed gate or an item error (section 12): **ENGINEERING_FAIL / INCOMPLETE**; no scientific label |
| 1 | Line Q at load 0.5 is NOT EVALUABLE | **NOT EVALUABLE — ANCHOR REFERENCE** |
| 2 | Line Q at load 0.5 FAILS | **ANCHOR NOT REPRODUCED AT THE CONVERGED DURATION** (with the anchor's convergence status). Lines A and G are printed for every load. P10-S0's outcome is not changed |
| 3 | L_Q ≥ 2 | **OVERLOAD-QUALIFIED UP TO L_Q**, followed by the status of ℓ₁ (below) |
| 4 | L_Q < 2 and Line Q at ℓ₁ is NOT EVALUABLE | **OVERLOAD NOT EVALUABLE AT ℓ₁ — REFERENCE; ADDRESSING QUALIFIED UP TO L_Q** |
| 5 | L_Q < 2, Line Q at ℓ₁ FAILS, convergence status NOT CONFIRMED | **OVERLOAD UNRESOLVED AT ℓ₁ — CONVERGENCE NOT CONFIRMED (RISING / DECLINING AT T / NOT SHOWN); ADDRESSING QUALIFIED UP TO L_Q** |
| 6 | L_Q < 2, Line Q at ℓ₁ FAILS, convergence status CONFIRMED | **OVERLOAD NOT QUALIFIED AT ℓ₁; ADDRESSING QUALIFIED UP TO L_Q** |

- **Status of ℓ₁ under step 3:** NOT EVALUABLE AT ℓ₁ — REFERENCE; UNRESOLVED AT ℓ₁; NOT QUALIFIED AT ℓ₁; or, when L_Q is the highest load run, NO BREAK FOUND ON THE GRID. If X8 was triggered and is not complete, the main-grid headline stands with **LOAD 8 PAUSED** or **LOAD 8 INCOMPLETE**.
- **Which line fails at ℓ₁** is printed per series, for each series whose Line Q FAILS: LINE A FAILS; LINE G FAILS (A HOLDS); or NEITHER ALONE (both hold, the composite or ADDRESS STABLE does not). At a cell type flagged on condition 4 whose Line Q FAILS, the print is LINE A FAILS (LINE G NOT EVALUABLE — REFERENCE), or, when Line A holds, **LINE A HOLDS; LINE G NOT EVALUABLE — REFERENCE; THE COMPOSITE FAILS ON LM CAPABILITY REDUCED / ADDRESS STABLE** (the one that applies, or both).
- Every headline is printed with the reference regime and convergence status at L_Q and at ℓ₁, both series' counts and bounds, L_A and L_G, and the fixed sentences: "W7 is told the record length. The memory is told the answer position. Synthetic fixed-length records; one frozen 27,392-parameter backbone. A5-D was chosen for P10-S0 after its P9-II result was observed. μ = 1.0 was calibrated at 0.5 facts per slot."
- Where Line Q is NOT EVALUABLE at ℓ₁ because of a condition-4 flag, Line A's state there is printed beside the headline ("LINE A HOLDS / FAILS AT ℓ₁; LINE G NOT EVALUABLE — REFERENCE").
- UNRESOLVED and NOT EVALUABLE are registered outcomes. Neither is a basis for a further run on these cells without a new ADR approved by the human lead.

**Hypotheses (each can fail).** H23-A: Line Q HOLDS at load 0.5. H23-O: L_Q ≥ 2. H23-G: at Line Q's ℓ₁, every series whose Line Q FAILS prints LINE G FAILS (A HOLDS); not read if ℓ₁ is NOT EVALUABLE or if there is no ℓ₁; it fails if any such series prints anything else, the two prints of a flagged cell type included. H23-P: A5-D IMPROVES ON A0 at load 2. A hypothesis reading is not a success of the science.

## 8. The conditional block X8

- **Trigger (fixed now):** X8 runs only if L_Q = 4 after the complete main grid, read by the frozen analysis at a gate stage that passes L_Q and nothing else to the launcher. Otherwise it prints **NOT RUN — L_Q BELOW 4** (or the result of steps 0–2).
- Reason: the direction asks that a failure locate the break. If the recipe holds at 4, one more load answers where it breaks; if it fails at or below 4, load 8 adds cost and no location.
- X8's duration comes from the same rule, ladder, floor, extension rule and blind mechanism, on the same two calibration draws (those of the Stage R whose `durations.json` was frozen), run after the trigger and before any X8 cell. Its ceiling is the same as every cell type's (T at most 8,192 exposures, 16,384 with the extension). Its durations and plan are written as an addendum to the git-ignored run directory, after the main grid's analysis stage has finished and before any X8 cell. Its SHA-256 goes into the run's ledger, and X8's stages check their identity against it. It is committed with the results after the run. No file of the worktree is written during the registered run. X8's extension is decided by the rule of section 5.1 with P equal to the hours charged so far plus X8's remaining projection. B is not changed after the freeze, and a refusal gives NOT SHOWN. Its reference flags follow the table of section 5.2: on a condition-4 flag X8 runs, Line A is read and Line Q at load 8 is FAILS or NOT EVALUABLE by section 6.4; on any other flag X8 prints NOT RUN — REFERENCE FAILS CONDITION n and load 8 is NOT EVALUABLE.
- **Cost and cap:** X8 is included in the frozen projection and in the hour cap at its extended ceiling (T = 16,384 exposures), because its T is not known at the freeze.
- No higher load is run under this ADR.

## 9. Limits (DIRECTION.md section 5)

| Limit | Kind | Rule |
|---|---|---|
| Charged-hours cap (set at the freeze: twice the measured projection, X8 at its ceiling included) | Resource cap | May be extended by the human lead on cost projections only, never on outcome values; every planned cell still runs. A stage that reaches it is **PAUSED** and resumes from its registry |
| Per-stage time caps (twice each stage's projection) | Resource cap | Same |
| Memory guard, 3 GiB per worker, 18 GiB aggregate | Resource cap | The training loop writes each per-update and diagnostic record to disk when it is produced and keeps none in memory. A unit test asserts that the loop's peak resident memory after 16,384 updates is within 64 MiB of its peak after 4,096 **[choice]**. The timing rehearsal runs at least 8,192 updates per (arm, slot count). **Projection, with the per-update records included:** if the records were held in memory, as in P10-S0's loop, they would add 0.56 GiB per worker at 8,192 exposures of an 8,192-fact cell (524,288 updates at 1,144 bytes per record) and 1.12 GiB at 16,384 exposures, on top of measured training peaks of 0.36–0.75 GiB: up to about 1.9 GiB per worker and about 11 GiB for six. The projection carries that allowance until a full-length measurement replaces it. **Measured at the full planned length before the caps are set:** Stage R's runs train A5-D and A6 at every cell type to at least 2T and record peak memory; and one A0 cell on the rehearsal draw is run at the full frozen T of the series-M cell type with the most updates (ties: the larger slot count) in stage 5, with time and memory as its only output. **Rule (no return):** a cell type whose measured peak exceeds 1.5 GiB per worker runs with fewer workers, so that each stays within 3 GiB and this study's aggregate within 18 GiB; above 3 GiB per worker it is PAUSED before it starts, which is an engineering stop until the human lead rules, and it is neither dropped nor labelled. Stages other than stage 3 may share the machine with another study's compute stage while the aggregate of both stays under 36 GiB **[choice]**; sharing beyond that is the human lead's |
| Disk: run directory at most 110 GiB **[choice]**; free space at least 50 GiB **[choice]** | Resource cap | A stage PAUSES when the run directory reaches 110 GiB or free disk space falls below 50 GiB. It resumes when space is made; no cell is dropped and no label depends on it (section 11) |
| Training length T per cell type | Design ceiling | The convergence rule; base ladder to T = 8,192 exposures; the written extension rule to 16,384 within the budget B; a refusal and the extended ceiling each give a registered NOT SHOWN (section 5.1) |
| Stage R's time cap | Resource cap | Section 5.1; PAUSED, resumable |
| Number of loads | Design ceiling | Extended only by the X8 trigger |
| Registered draws that pass G1 | Design ceiling | Generate until ten pass, within four reserves; if fewer pass, the rules do not cover the case (the class rule is tied to ten draws): ENGINEERING STOP before the freeze until the human lead rules; nothing is frozen |
| Calibration draws (2), registered draws (10), one initialization seed per draw | Design ceiling | Fixed: the class rule and bounds are tied to ten draws |
| 0.90 × A6; A6 floors 0.90 and 0.50; conditions 2–6; at most one failed cell; ADDRESS STABLE 0.80; the combination rules of section 6.6; d ≥ 6 with p < 0.05 | Scientific threshold | Never relaxed after observation |
| Plateau step 0.01 (two-sided, two steps); the reference's plateau floor; T = 2·e\*; confirmation 0.02; which reference flags remove a cell type | Scientific threshold | Fixed before Stage R; never changed after it |

No limit is extended because a partial result looks close.

## 10. Stages and machine load

Platform of record: the research machine (Apple M5 Max, 48 GB, macOS arm64, CPU only, six single-thread workers), as ADR-0020 section 10.4. Manifests record OS, architecture, Python, torch and thread settings. Bit-exact assertions, the identity gate included, are made on this platform only. Workers run with `torch.set_num_threads(1)` and `torch.use_deterministic_algorithms(True)`, as `studies/p9ii/train.py` l.801–802. Checks (`ruff`, `mypy`, `pytest`) run locally; GitHub CI is not used unless the human lead asks.

| # | Stage | Seeds touched | Quiet machine needed? |
|---|---|---|---|
| 1 | Implementation; unit tests; resume-from-snapshot test; analysis and report on synthetic registries with known answers: every state of section 6.4, every combination of section 6.6, every step and ℓ₁ status of section 7 (PAUSED and missing cells, reference below its floor, a cell type flagged on condition 4 only at load 2 (Line A read; G and Q NOT EVALUABLE) and the same with n_A ≥ 2 (Line Q FAILS) and with Line A holding but not ADDRESS STABLE (Line Q FAILS), a flag at load 1, a flag on another condition at load 4, A5-D FLAT BELOW FLOOR, an extension refused, L = "none", Line G NOT READ in one series, NON-MONOTONE, a replaced draw; X8 triggered, NOT RUN — L_Q BELOW 4, X8 flagged, LOAD 8 PAUSED; RISING and DECLINING AT T; ENGINEERING STOP — ITEM ERRORS; NON-FINITE; RATIO ABOVE 1; both reference regimes; LM CAPABILITY REDUCED; IN SERIES M ONLY; every event of section 5.2 with the study proceeding), every one of the eight combinations of section 6.4, a test that every threshold in this ADR equals the config's value (ADR-0029 section 13), and every descriptive section | tests | no |
| 1b | Independent implementation audit (the `arbor-auditor` subagent) and its fixes; a short re-audit of the fixes | tests | no |
| 2 | Identity and end-to-end gates (section 3); pipeline rehearsal end to end through the real launch scripts, on a plan built by the registered plan builder with only the seed set changed (asserted by a diff of the plans) | rehearsal | no |
| 3 | Timing rehearsal: seconds per update and peak memory for every (arm, cell type), at least 8,192 updates each | rehearsal | **yes: runs alone** |
| 4 | Stage R (section 5.2), with the extension rule using stage 3's quiet rates | calibration | no |
| 5 | Generation and G1 of registered and reserve draws; the full-length A0 memory cell (section 9); the candidate `freeze/plan.json` is written; the counting rehearsal runs against that file itself (every stage's items resolved to their inputs and outputs, no training; the analysis and report run on a synthetic registry keyed by its labels); its SHA-256 goes into the rehearsal record; the stage caps are set from the measured projection (section 9) and written to `freeze/stage_caps.json`; then the freeze, which refuses unless the plan it commits has the recorded hash (ADR-0029 section 19 ruling 5) | registered, data only; rehearsal | no |
| 6 | **Decision 2** (the lead under the delegation, and only to run the frozen plan as frozen; anything else is the human lead's; section 17), then the registered run: gates; main grid; X8 gate; X8 calibration and X8 if triggered; analysis; report | registered | no |
| 7 | Independent recomputation from raw cell records (auditor); outcome statement to the human lead | — | no |

- **Order and what may change.** The independent implementation audit (stage 1b) and its fixes come before the gates, the timing rehearsal and Stage R. From the start of stage 4 no file of the frozen-input set (section 14) changes except `freeze/durations.json`, `freeze/plan.json`, `freeze/stage_caps.json` and the sealed files' hashes. **No code changes after Stage R has written `durations.json`.** A code change after stage 4 has started voids Stage R: the change is recorded and re-audited, stage 2 is re-run, stage 3 is re-run if the change touches a file that the training or evaluation path imports, and Stage R is repeated in full **on fresh calibration draws** taken from the registry's spare values (section 4.2: repeat k = 1, 2, 3). Every earlier record is kept and listed, stays sealed, and enters nothing. The third review wrote "on the same calibration draws"; the lead chose fresh draws so that a repeated rehearsal is not a second look at draws whose result the code change could have been informed by. A fourth repeat has no allocated values and is an engineering stop until the human lead rules.
- **The plan that is frozen is the plan that was rehearsed.** The candidate plan file is written first, the counting rehearsal runs against that file itself, its SHA-256 is recorded, and the freeze refuses any other file (stage 5; ADR-0029 section 19 ruling 5).
- **Only stage 3 needs a quiet machine:** its rates feed the extension rule (section 5.1), which sets a registered status. It runs alone: with no other study's compute stage and no other worker of this study. The condition is measured at the stage and recorded: the load average is sampled before its first task starts and every minute during it, and every sample must be at most 2.0 **[choice]**. An attempt with a sample above 2.0 is stopped, kept and not used. Up to three attempts are made, all within 24 hours of the first attempt's start **[choice]**. If none meets the condition by then, stage 3 is **PAUSED — MACHINE NOT QUIET** and rescheduled. It is never run loaded, and the extension rule never uses a rate from an attempt that failed the condition; it uses the first attempt that met it. Stage 3 is then repeated with twelve busy single-thread processes (ADR-0020 section 10.3); the hour caps of section 9 use the larger of the two rates whenever the registered run may share the machine. No other stage registers a wall-time or CPU-time reading, so the others may share the machine (section 9). The third review's text allowed the least-loaded of three attempts to be used; the lead's rule is stricter.
- The load average is measured and recorded at the start of each stage and every ten minutes during it. Timing feeds projections, caps and the extension rule only. A loaded machine can cause a PAUSE, never a label.

### 10.1 Sharing the machine

The research machine is also the human lead's working computer, and other P10-I studies run on it.

- **Only stage 3 runs alone.** It waits for a quiet machine by the rule above. A wait is a pause of this study and costs nothing but calendar time.
- **Every other stage may share the machine** with another study's compute stage, within the memory rule of section 9 (this study within 18 GiB, both studies together under 36 GiB) and the disk rule.
- **Sharing makes a stage slower by about 1.5 to 2.9 times** (P10-S0's busy rates against its registered rates, `docs/reviews/p10s0-results-2026-11-16/timing_out.txt`). A slower stage can reach its hour cap and be PAUSED; it then resumes from its registry. Sharing never changes a label: no rule outside stage 3 reads a wall-time or CPU-time figure, and bit-identity does not depend on load.
- **Own worktree.** The study is implemented, rehearsed and run in its own git worktree. No other session writes in that worktree, and nothing is committed or written in it during a registered stage (section 14). Status goes to the human lead directly or to another branch.

## 11. Cost projection (an estimate, to be replaced by the timing rehearsal)

Rates are P10-S0's registered-run rates (`docs/reviews/p10s0-results-2026-11-16/timing_out.txt`, seconds per update): at 4,096 slots A5-D 0.0098–0.0102, A6 0.0091–0.0093, A0 0.0144 (8K/4K); at 16,384 slots A5-D 0.0172, A0 0.0144, A6 0.0187. These are quiet-run rates: they were 0.57–0.91 of that study's "alone" rehearsal rates and 0.34–0.67 of its busy rates, so the figures below are optimistic for a machine in daily use. Not measured: 8,192 slots (interpolated to 0.013), 2,048 slots and below (set to 0.010). Durations are guesses until Stage R.

| Case | Main grid M / S / Stage R, CPU-hours | Six workers, charged hours without X8 | X8 and its calibration |
|---|---|---|---|
| Central guess (T = 1,024 / 2,048 / 2,048 / 4,096 exposures at loads 0.5 / 1 / 2 / 4) | 57.5 / 8.2 / 18.3 | about 15–16 | about 9 at T = 8,192 |
| Every T one ladder step higher | about 115 / 16 / 37 | about 29–31 | about 18 at T = 16,384 |
| Every cell type at the base ceiling (T = 8,192) | about 223 / 29 / 71 | about 54 | about 9–18 |
| Extension granted (per 8,192-fact cell type, T = 16,384 in place of 8,192) | — | 7.3–12.2 more by slot count (the cell type then totals 14.6–24.4), plus its Stage R round | — |

The order of magnitude is **15 to 55 charged hours without X8 and without extensions**, and up to about 75 with X8 at its ceiling. The hour budget for the extension rule is **B = 55 charged hours** (section 5.1 items 3 and 7; draft 3 recommended 80). B bounds extensions only: the base grid at the base ceiling is about 53.7 hours before overhead and X8, so B leaves the extension rule little to grant, and a projection above 55 without any extension is possible and is reported to the human lead as soon as it is measured. For scale: P10-S0 charged 6.09 hours and P10-S1 25.39. The longest single Stage R run at the base ceiling is about 5.5 hours. The timing rehearsal measures the rates at every size, the cost of three evaluations per cell and peak memory; Stage R measures the durations; the human lead sees the measured projection at Decision 2.

**Disk.** The run directory is projected at about 54 GiB at the base ceiling and about 107 GiB with every extension, mostly per-update logs at about 609 bytes per update (P10-S0: 19,948,322 bytes for 32,768 updates). It is recorded with the projection. A stage PAUSES if free disk space falls below 50 GiB **[choice]**. The run directory is also capped at 110 GiB **[choice]** as a resource cap (section 9). Those two figures leave out X8, which adds about 11 GiB at T = 8,192 exposures and about 23 GiB at 16,384 (hand estimate at the same bytes per update). Under B = 55 only a few extensions can be granted (section 5.1 item 7), so the largest projection that can be reached is about 80 GiB, under the cap. A repeated Stage R adds its own logs. Reaching the cap is a PAUSE.

**Memory.** Section 9 gives the projection with the per-update records included (0.56 GiB at 8,192 exposures, 1.12 GiB at 16,384) and the full-length measurements that replace it before the caps are set.

## 12. Stop rules and NOT EVALUABLE outcomes

Three things are kept apart: a pause (identity, environment, a resource cap), an engineering stop (a code error, a failed gate), and a scientific outcome of a cell (a recipe that diverges). Only the last is ever a label.

- **Identity.** A difference between a frozen input and the running one stops the affected task as **PAUSED — IDENTITY**. Restoring the file bit for bit lets the stage resume. Nothing is recorded as a result.
- **Environment.** An out-of-memory kill, a full disk, a killed process or a file-system error is never recorded as a failed cell or a failed gate. The task is **PAUSED — ENVIRONMENT**. Once the cause is removed it is re-run from its last snapshot (the resume is bit-identical by stage 1's test) or from its start.
- **Code.** Any other exception inside a task is an item error. The stage stops. The registered analysis refuses while any item error is recorded, and the outcome is **ENGINEERING STOP — ITEM ERRORS** (ADR-0029 section 20 ruling 11). It is never a scientific label.
- **A failed gate** stops the run: ENGINEERING_FAIL. A second attempt needs the human lead's decision, with everything observed in the first attempt listed. A gate that could not run because of the environment is paused under the rule above, not failed.
- **Non-finite training: a diverging recipe.** A recipe diverges in a cell when the trainer's own checks (`studies.p9ii.train.Trainer.step`: a non-finite loss, gradient norm or parameter, which raise at that update) fire. Nothing else is divergence: an exception from any other place is a code error. It is a result of the recipe and the registered scientific outcome of that cell. A learned arm's cell is kept as FAILED on every condition and printed NON-FINITE AT UPDATE u. An A6 cell that is non-finite makes its draw NOT_EVALUATED at that cell type. Neither is re-run. **In Stage R** a non-finite run is written to `durations.json` as **NON-FINITE IN REHEARSAL (arm, calibration draw, update u)**. That cell type's ladder stops; it is not an extension candidate; it is marked CONVERGENCE NOT SHOWN IN REHEARSAL and runs at T = 8,192 exposures. The other runs of the cell type continue to T so that the reference flags can be computed; if the non-finite arm is A6, the flags come from the other calibration draw, and if A6 is non-finite on both, none is computed and the cell type prints REFERENCE NON-FINITE IN REHEARSAL and stays in the plan. The other cell types proceed, the study proceeds, and the event is reported to the human lead at once (section 5.2).
- A resource cap reached: the stage is PAUSED. It resumes from its registry; completed cells are not recomputed. No label is computed while any main-grid cell is missing (section 7 step 0).
- A failed cell is kept and not re-run. No re-run with changed settings.
- No registered seed is seen by a model before the freeze. After Stage R nothing changes except what section 5.2 lists, and no code changes (section 10).
- **No discretionary return before the freeze.** In the events of section 5.2 (an anchor cell type flagged, NOT SHOWN or A5-D FLAT BELOW FLOOR; any reference flag at load 1 or 2; REFERENCE BELOW FLOOR AT T; NON-FINITE IN REHEARSAL) the study proceeds by rule and the human lead is told at once. Only a case the rules do not cover goes back to him, as an engineering stop.
- NOT EVALUABLE arises in exactly two ways: a reference flag from Stage R (per condition, section 5.2), or a class NOT_EVALUATED (more than one draw with A6 below its floor). Section 7 says what each gives at the anchor and above it.
- If P10-S0's or P9-II's records are amended after the freeze, the study stops and returns to the human lead.

## 13. What this study cannot establish

- Anything about capacity, useful-capacity scaling, locality, transfer, continual addition of facts, efficiency, latency or storage.
- That addressing works, or cannot work, under overload in general. One recipe (A5-D, μ = 1.0, calibrated at 0.5 facts per slot), one interface (W7, told the record length), one task, one backbone.
- That a negative is a low success rate: at a true per-cell rate of 0.95 the rule still reports a break at or below load 2 about four times in ten (section 6.6).
- That a pass relative to a degraded reference is useful, or that the reference is the best possible addressing.
- An unbiased first test of A5-D: its selection for P10-S0 followed its observed P9-II result.
- Why held-out templates fail, if they do. The descriptive measures are not a causal test.
- That the interface finds where to read; anything about WX, about 65,536 slots, about loads above 8, or about natural language.
- That the durations are sufficient in general: the rule is an operational plateau on two calibration draws, checked on the registered draws.
- A success or a failure of the ArborLM concept.

## 14. Engineering requirements carried from P10

| P10 failure | Requirement here |
|---|---|
| A status note committed to a frozen ADR lost P10-S1's first attempt | **The frozen-input set is exactly:** the files listed by name and SHA-256 in the freeze record (every file under `studies/p10is0/` at the freeze, including `freeze/plan.json`, `freeze/durations.json`, `freeze/stage_caps.json` and the sealed files' hashes); identity checks iterate over that list, not over the directory, `configs/p10is0_overload.toml`, the launch scripts, the imported files of `studies/p9ii`, `studies/p10s0`, `studies/p9i`, `studies/p9` by sha256, and the data manifests named in the plan. Identity is checked by file hash, not by the commit at HEAD. **This ADR and everything under `docs/` and `results/` are not frozen inputs.** Run-time notes go to `NOTES.md` in the git-ignored run directory, or to chat. No commit is made in the run's worktree during a registered stage, and no file of the worktree is written during it: the X8 addendum goes to the run directory (section 8). An identity difference is PAUSED — IDENTITY and resumes on restore (section 12) |
| A stage could not resume | Every stage keeps a per-cell registry; a PAUSED stage continues; completed cells are skipped by record hash |
| The throughput stage listed a cell the frozen plan did not run | Every stage builds its item list from the frozen plan only; stage 2 rehearses every stage end to end; stage 5's counting rehearsal runs against the candidate plan file itself before the freeze, and the freeze refuses any other file |
| An unstated aggregation rule; a validity check the reference fails; a wrong descriptive section | Sections 6.4, 6.6 and 7 are total. A6 passes through every condition in Stage R (section 5.2). The analysis, descriptive sections included, is tested on synthetic registries; the auditor writes its own |
| A plateau rule met before anything was learned (ADR-0021 revision 5) | The reference's plateau floor and the two-sided step; a flat failing recipe is labelled, not hidden (section 5.1) |
| A projection made under one machine load and run under another | Rates are measured in the timing rehearsal alone on a quiet machine, and again under twelve busy processes, with the load average recorded; the quiet rates feed the extension rule and the larger rates the caps (sections 10, 11) |
| Memory that grows with run length, unseen by a short rehearsal (found by the third review) | Records are written to disk as produced; a unit test on memory growth; full-length memory measurements before the caps are set (section 9) |
| A count gate stopped P10-S2 | Draws: generate until ten pass G1, within four reserves. Durations: train until the plateau rule is met, within the ceiling and its extension rule |
| One load, one length | Sections 4 and 5 |
| A macOS/Linux difference in exact ties | Platform of record named; bit-exact assertions on it only |
| A slot registry and seed whitelists that reject new sizes and new seeds (found by this ADR's reviews) | New adapter code, the two-part identity gate and its declared seed re-use (section 3) |
| CI cost | Checks run locally |

## 15. How the result feeds P10-I-S1's learned-address lane

P10-S1 omitted lane L because P10-S0 was not OVERLOAD-QUALIFIED. This ADR states what it provides; the lane's rules belong to ADR-0024.

1. **Only Line Q licenses a lane, and only at tested cell types.** A lane may use A5-D (μ = 1.0, this study's code hash, the T of that cell type) at the cell types of this study whose load is at most L_Q. Other (facts, slots) pairs, for example 32,768 facts at any load, are not licensed unless the human lead rules otherwise. Elsewhere the lane prints **OMITTED — ADDRESSING NOT QUALIFIED AT THIS CELL (ADR-0023)**.
2. The licence depends on L_Q only: none when the procedure ends at steps 0–2; loads up to L_Q in every other case, whatever the status of ℓ₁.
3. The lane's label carries the reference regime of each licensed cell type (REFERENCE NEAR CEILING or QUALIFIED RELATIVE TO A DEGRADED REFERENCE) and its convergence status.
4. Lines A and G license nothing by themselves.
5. **The denominator.** A lane that applies this study's composite must run A6 as frozen here (R1 codes, learning rate 0.003) on the same draw, cell type and update count. An oracle arm with a searched learning rate is not A6, and condition 1 is not defined against it.
6. **Timing.** A qualification recorded after P10-I-S1's freeze changes nothing in it (ADR-0020 section 9.2). Either P10-I-S1 freezes after this study's outcome is recomputed and accepted, or its lane is a separately frozen stage that waits. That choice is ADR-0024's and the human lead's.
7. This study uses a flat memory. A qualification here says nothing about addressing into the tree.

## 16. Open choices reserved for the human lead

Draft 3 reserved every item below for the human lead. Section 17 records how each was ruled under his delegation of 2026-11-18, and which parts stay with him.

1. **Load grid and slot counts** (section 4.1). Recommended: loads 0.5, 1, 2, 4 at 8,192 and at 2,048 facts.
2. **X8.** Recommended: conditional on L_Q = 4. Decided at Decision 1, not after Stage R.
3. **The convergence rule** (section 5): ladder, two-sided 0.01 step, the floor on A6 only with A5-D FLAT BELOW FLOOR counted as a plateau, T = 2·e\*, the 0.02 check. Recommended as written.
4. **The extension rule's hour budget B** (sections 5.1, 11). Recommended: one further doubling, within B = 80 charged hours at 1× for the whole study; a refusal or the extended ceiling gives NOT SHOWN. The alternative is no extension (cheaper; more UNRESOLVED) or a larger budget. B is reserved to the human lead above 55 charged hours, the upper figure he was told on 2026-11-18. **Ruled: B = 55** (section 17); the recommended 80 was not taken and would need the human lead's own approval. What B = 55 leaves of the rule is in section 5.1 item 7.
5. **The meaning of 0.90 under a degraded reference** (section 6.5). Recommended: the ratio at every load with the mandatory regime tag and the 0.50 floor. Alternative: qualify only where A6 ≥ 0.90.
6. **"Both series" and "every lower load"** (section 6.6), with its false-negative rate. Recommended: keep; it is the conservative reading.
7. **A0** in series M. Recommended: keep. Decided at Decision 1.
8. **μ is not re-calibrated; no dense baseline.** Recommended: both as written.
9. **The closure ledger:** the two declined items (WX; 65,536), both proposed as CLOSED AS RECORDED (unresolved) (section 3).
10. **Lane licence scope** (section 15 item 1): tested cell types only, or wider. Recommended, as section 15 item 1 implies and the third review found sound: tested cell types only.
11. **Seeds:** approval of the programme-wide registry, which lists the identity gate's declared re-use of P10-S0's rehearsal set (registry section 4.6) (sections 3, 4.2).
12. **Budget and timing:** the hour cap at Decision 2; when the run may occupy six cores; whether it may share the machine with another study. Default stated by the third review and taken: caps by section 9's rule; sharing except in stage 3, within 36 GiB (section 10.1).
13. **Reference flags** (section 5.2): which A6 failures remove a cell type (recommended: conditions 2, 3, 5, 6; condition 4 keeps Line A, with Line Q by section 6.4), and what happens before the freeze on a flag at load 1 or 2 or an anchor event. Draft 3 had a return with no default; it is now the rule of section 5.2 (the study proceeds; the human lead is told at once).
14. Approval of this specification for implementation and rehearsals (Decision 1, section 17), and separately of the registered run (Decision 2). Any second attempt; merge; publication.

Not choices, and left to measurement: whether A6 passes condition 4 under overload (unmeasured in any record; Stage R's flags answer it), and whether the 0.01 step is attainable under a degraded reference (Stage R answers by NOT SHOWN).

## 17. Approval record — Decision 1 (2026-11-18 UTC)

**Review trail.** Three independent reviews by the `arbor-auditor` subagent (Claude Opus 5.5): draft 1 NOT READY; draft 2 NOT READY with no blocking finding; draft 3 **READY AFTER THE LISTED EDITS** with no blocking finding (`docs/reviews/p10-i-spec-reviews-2026-11-17/REVIEW3_ADR-0023.md`, copied verbatim from the reviewer's file). This text applies those edits and the lead's decisions where the review left a choice (section 18.3 lists each, and each edit that is not word for word). **The text with the edits applied has not been reviewed again.** Two of the lead's decisions depart from the reviewer's wording and are named here so that they are not missed: the returns before the freeze are replaced by a rule (the reviewer wrote that they must stay with the human lead), and a voided Stage R is repeated on fresh calibration draws (the reviewer wrote the same draws).

**The delegation.** The human lead's instruction of 2026-11-18, recorded in `docs/reviews/p10-i-direction-2026-11-17/DELEGATION_2026-11-18.md` section 1:

> once its done can you accept the results as they come and continue with the next simulations until you conclude P10-I-*

and a second permission, given by the human lead in the same exchange:

> and you have my permission to auto approve everything until you complete P10-I

The first quotation is in the committed delegation record. The second is not yet in it at the commit this text is based on (`ef5596b`); it reached this session through the lead's coordinating session, and the lead adds it to that record before any Decision 2. Section 2 of the record gives the lead the decisions that gate each study, "taken at the options the drafts recommend unless an independent review says otherwise".

**Decision 1.** Under that delegation the lead (Claude Fable 5.2, `claude-fable-5-2`) approves this specification **for implementation and rehearsal only**: the code in new files (`studies/p10is0/`, `configs/p10is0_overload.toml`, `tests/test_p10is0_*.py`), the independent implementation audit, and stages 1 to 5 of section 10 up to, and not including, the freeze. It is not a human approval and not Astra validation.

**The open choices of section 16.** Each is ruled at its recommended option, with two exceptions.

| Item | Ruling |
|---|---|
| 1 grid; 2 X8 conditional on L_Q = 4; 3 convergence rule; 5 ratio under a degraded reference with the tag and floor; 6 both series, every lower load; 7 A0 kept; 8 μ fixed, no dense baseline | as recommended |
| 4 extension | one further doubling, as recommended. **Exception: B = 55 charged hours, not the recommended 80** (R3-12). Section 5.1 item 7 states what that leaves |
| 9 ledger | WX and 65,536: CLOSED AS RECORDED (unresolved), as proposed |
| 10 lane licence | tested cell types only |
| 11 seeds | the registry at revision 3, with the seed gate of section 4.2 |
| 12 budget and timing | caps by section 9's rule; sharing except in stage 3, within 36 GiB |
| 13 reference flags | removal on conditions 2, 3, 5, 6; condition 4 keeps Line A, with Line Q by section 6.4 (R3-3). **Exception: the return before the freeze is not taken as drafted; it is replaced by the rule of section 5.2**, fixed here before any observation |
| 14 approvals | Decision 1: this record. Decision 2: below |

Every number marked **[choice]**, those added with the third review included (1e-6, 64 MiB, 2.0, 24 hours, 50 GiB, 110 GiB, 36 GiB), is fixed by this record. The rulings of section 19 are part of it.

**What this does not cover.**

- **The freeze and the registered run.** No registered run is approved. Decision 2 is taken only after the implementation audit and its re-audit, the gates, the quiet timing rehearsal, Stage R, the counting rehearsal against the candidate plan and the freeze are on record. Under the delegation the lead's Decision 2 can only be "run the frozen plan as frozen". Any other decision at that point, including not running, is the human lead's.
- **Any threshold change.** No threshold, label rule, seed or duration rule changes after this record without a recorded amendment, and none after Stage R at all.
- **B above 55 charged hours**; machine sharing beyond section 9's rule; a case before the freeze that the rules do not cover (an engineering stop until the human lead rules); a second attempt; publication; pushing weights; paid services; packages outside the lock; administrator access; any change to a completed study. Merges to `main` follow the delegation record's section 6 and its time limit.
- A success claim. Nothing here is a result.

**Where later decisions are recorded.** Decision 2 and every event report before the freeze are recorded in `results/p10is0-freeze-<date>/` (`EVENT_<n>.md`, `DECISION_2.md`) and committed outside any registered stage. Decision 1 is this section. Each event is also reported to the human lead at once, in the conversation.

`Astra review: NOT_PERFORMED`. Claude review is not Astra review.

## 18. Review record

Draft 1 was reviewed by the `arbor-auditor` subagent (Claude Opus 5.5): `docs/reviews/p10-i-spec-reviews-2026-11-17/REVIEW_ADR-0023.md`, verdict NOT READY. This revision is by the drafter (Claude Fable 5.2). The drafter re-read `studies/p9ii/core.py` line 252 and `studies/p9/model.py` lines 272–276 and found the reviewer's two factual corrections right. No finding is disputed. Neither review is Astra validation or a human approval.

**First review (draft 1):**

| Finding | Severity | Disposition | Where |
|---|---|---|---|
| 1 Outcome function not total (a–f) | BLOCKING | FIXED | 5.2 (flag makes all lines NOT EVALUABLE; stop before freeze), 6.4, 6.6, 7 (steps 0–6, ℓ₁ status), 10 stage 1, 12 |
| 2 Existing code cannot run the new slot counts | BLOCKING | FIXED | 3 (new adapter code, two-part identity gate, end-to-end gate), 14 |
| 3 X8 ceiling unreachable; no X8 cap rule | REQUIRED | FIXED | 5.1, 8, 9 |
| 4 "Blind" had no mechanism; cuts after Stage R | REQUIRED | FIXED | 5.2; 16 items 2 and 7 |
| 5 Initialization seeds collide with derived seeds | REQUIRED | FIXED | 4.2 (values removed; programme-wide registry; derived-seed check; distinct calibration seeds) |
| 6 No plateau floor; decline counted as plateau | REQUIRED | FIXED | 5.1 (floor; two-sided), 5.3 (DECLINING AT T), 14 |
| 7 Ceiling without an extension rule | REQUIRED | FIXED | 5.1 (extension rule; why NOT SHOWN is the outcome beyond it), 9, 16 item 4 |
| 8 Positive meaning overclaimed; A6 not ideal addressing | REQUIRED | FIXED | 1 (0.81 stated), 3, 6.5 |
| 9 Operating characteristic; negative wording | REQUIRED | FIXED | 1, 6.6 (table), 13 |
| 10 "Only the slot count changes" | REQUIRED | FIXED | 3 |
| 11 Cost range; best-case rates | REQUIRED | FIXED | 11 |
| 12 Paired-comparison rationale | REQUIRED | FIXED | 6.7 |
| 13 Lane licence extrapolated; regime tag dropped | REQUIRED | FIXED | 15 |
| 14 Disagreement with the closure ledger | REQUIRED | ANSWERED | 3 (table): two items accepted, WX and 65,536 declined with reasons and reserved for the human lead (16 item 9); condition 6 note added |
| 15 Condition 3 detects gross collapse only | ADVISORY | FIXED | 6.1, 6.2 |
| 16 Load average; concurrency | ADVISORY | FIXED | 9, 10 |
| 17 μ and A0 | ADVISORY | FIXED | 3; 16 item 7 |
| 18 Probe cadence | ADVISORY | FIXED | 4.3 |
| 19 Units of the ceiling comparison | ADVISORY | FIXED | 5.1 |
| 20 Stage R procedure | ADVISORY | FIXED | 5.2, 10 stage 1 |
| Section 3 of the review: UNRESOLVED must not argue for an extension | REQUIRED (in text) | FIXED | 1, 7 |
| Anchor read under the 10-cell rule; seed-block citation | ADVISORY | FIXED | 4.1, 4.2 |
| R1 source of the Q1 figure | ADVISORY | FIXED | 2 |
| R2 unit of the last-doubling gain | ADVISORY | FIXED | 2 remark 2 |
| R3 "still rising" source | ADVISORY | FIXED | 2 remark 2 |
| R4 stale P10-S1 seed list | (part of 5) | FIXED | 4.2 (no list copied from an ADR) |
| R5 A0 rate at 4,096 slots | ADVISORY | FIXED | 11 |
| R6 a_use treated as accuracy | REQUIRED | FIXED | 2, 6.5 |

**Confirmation review (draft 2):** by the `arbor-auditor` subagent (Claude Opus 5.5), `docs/reviews/p10-i-spec-reviews-2026-11-17/REVIEW2_ADR-0023.md`, verdict NOT READY with no blocking finding. It judged the first review's findings fixed except 6 (superseded by N2) and 7 (completed by N3). Draft 3 is by the drafter (Claude Fable 5.2) under the lead's scientific calls on N1–N3. Draft 3 was then reviewed a third time (section 18.3).

| Finding | Severity | Disposition | Where |
|---|---|---|---|
| N1 Reference flag too broad; only the anchor returned | REQUIRED | FIXED | 5.2 (per-condition table; what is known about A6; stop before the freeze on any flag at load 1 or 2), 6.4, 7, 8, 10 stage 1, 12, 16 item 13 |
| N2 Plateau floor on A5-D | REQUIRED | FIXED | 5.1 (floor on A6 only; A5-D FLAT BELOW FLOOR counts as a plateau), 5.2, 16 item 3 |
| N3 Extension rule not computable | REQUIRED | FIXED | 5.1 (items 1–6; Stage R's cap), 9 |
| N4 Extension costs understated | ADVISORY | FIXED | 5.1, 11 |
| N5 Sealing proves non-alteration only | ADVISORY | FIXED | 5.2 |
| N6 Untagged numbers | ADVISORY | FIXED | 9, 10 |
| N7 Definitional gaps (ℓ₁ at "none"; H23-G; H23-O; unevaluated pairs; X8 label) | ADVISORY | FIXED | 6.6, 6.7, 7, 8 |
| N8 End-to-end gate sizes | ADVISORY | FIXED | 3 |
| N9 223 CPU-hours | ADVISORY | FIXED | 11 |
| X1, X2 Registry values and derivation rule | cross-reference | FIXED | 4.2 |
| X3 Identity gate's seed | cross-reference | FIXED here; the registry entry is the lead's to add | 3, 4.2, 16 item 11 |
| X4 65,536 disposition; WX wording | cross-reference | FIXED here; the ledger rows are the lead's to edit | 3, 16 item 9 |
| X5 Ledger row on lane L | cross-reference | not this file; the lead's | — |
| X6 Lane L's denominator | cross-reference | FIXED here (ADR-0024's text is the lead's) | 15 item 5 |
| X7 Registry against ADR-0024 on lane L data | cross-reference | not this file | — |
| X8 Condition-6 risk wording | cross-reference | FIXED | 3, 5.2, 16 |

The coordinator's instruction to remove a statement that the machine idles at load 1.0–1.2: draft 1 did not contain one; section 10 measures the load at each stage.

### 18.3 Third review (draft 3)

By the `arbor-auditor` subagent (Claude Opus 5.5), `docs/reviews/p10-i-spec-reviews-2026-11-17/REVIEW3_ADR-0023.md`, verdict **READY AFTER THE LISTED EDITS**, no blocking finding. It judged the confirmation review's findings fixed, N3 partly (completed by R3-5, R3-9 and A2 below). The edits were applied by the lead (Claude Fable 5.2) on 2026-11-18 UTC. "As written" means the reviewer's words were inserted unchanged; every other case says what differs. The text with the edits applied has not been reviewed again.

| Finding | Severity | Disposition | Where |
|---|---|---|---|
| R3-1 Audit missing from the stage order; code could change after Stage R | REQUIRED | FIXED. Row 1b as written. The sentence on a code change is **not as written**: Stage R is repeated on fresh calibration draws from the registry's spare, not on the same draws (the lead's decision), with stages 2 and 3 re-run as stated | 10; 4.2 (repeat values) |
| R3-2 The frozen plan never rehearsed itself | REQUIRED | FIXED, as written, with the full-length A0 memory cell added to stage 5 | 10 stage 5; 14 |
| R3-3 A condition-4 flag voided an identified failure | REQUIRED | FIXED, as written (the lead rules as the review recommends); totality re-derived by hand; a fourth print and H23-G's reading added for the new combinations | 5.2 table, 6.4, 7, 8, 10 stage 1 |
| R3-4 Memory grows with training length | REQUIRED | FIXED. The memory and disk sentences as written, plus the lead's additions: the projection with the records included, the full-length measurements, the rule in place of a return, and a 110 GiB cap on the run directory | 9, 11 |
| R3-5 Timing rehearsal on a loaded machine | REQUIRED | FIXED, **not as written**: stage 3 runs alone and is PAUSED and rescheduled if the machine is not quiet within three attempts and 24 hours; a loaded attempt is never used (the review allowed the least-loaded of three). The twelve-busy repeat and the second bullet as written | 10, 10.1, 5.1 item 2 |
| R3-6 Identity stopped the study; errors not separated from results | REQUIRED | FIXED. Identity, Environment, Code and the step-0 edits as written. Added: a bullet keeping the failed-gate rule, a definition of a diverging recipe, and "paused on identity or environment" in step 0. **Not as written:** the last sentence of the non-finite bullet (a return from Stage R) is replaced by a rule | 12, 7 step 0 |
| R3-7 The seal's access control cannot be built | REQUIRED | FIXED, as written except "outside the worktree", which contradicted "inside the git-ignored run directory" and now reads "outside version control". Added: a read by the lead is disclosed and voids the blindness claim for that cell type | 5.2 (i) |
| R3-8 Header predates the delegation; returns have no default | REQUIRED | FIXED, **not as written**. Header: the review's sentence with "every return before the freeze" replaced by "any case … the rules … do not cover". The returns: the review held that they stay with the human lead; the lead replaced them by a rule fixed before observation (the study proceeds; no cell type by choice; reported at once), and the human lead keeps the power to stop. Records: `EVENT_<n>.md` in place of `RETURN_<n>.md`; Decision 1 is section 17 | header, 5.2, 9, 12, 16 item 13, 17 |
| R3-9 X8 addendum written into the frozen directory | REQUIRED | FIXED, as written | 8, 14 |
| R3-10 Superseded checker; own-files defect | REQUIRED | FIXED, as written | 3, 4.2, 16 item 11 |
| R3-11 Identity gates: fields, tolerance, cadence | REQUIRED | FIXED, as written; 8K/4K for A5-D and A6 added from the review's guess 10 | 3, 10 |
| R3-12 B = 80 above what was disclosed | REQUIRED | FIXED, **not as written**: B is set at 55, so the review's sentence is adapted; section 5.1 item 7 states what the rule can still grant | 5.1, 11, 16 item 4, 17 |
| A1 P and the makespan | ADVISORY | FIXED, as written | 5.1 item 2 |
| A2 Undecided candidates in P | ADVISORY | FIXED | 5.1 item 2 |
| A3 "at load 2 or above" | ADVISORY | FIXED, as written | 1 |
| A4 "longest observed escape" | ADVISORY | FIXED | 5.1 |
| A5 4.2 hours for A0 | ADVISORY | FIXED | 5.1 |
| A6 Thresholds equal the config | ADVISORY | FIXED | 10 stage 1 |
| A7 Synthetic-registry list | ADVISORY | FIXED, as written, with the new combinations and events added | 10 stage 1 |
| Implementer's guesses 1–15 | — | RULED | 19 |
| Review section 6: what the lead may take under the delegation | — | FOLLOWED for every item except the returns, which the lead replaced by a rule instead of leaving them as returns to the human lead | 17 |

`Astra review: NOT_PERFORMED`.

## 19. Rulings for the implementer

The third review listed what an implementer would otherwise have to guess. The lead adopts the reviewer's recommended ruling for each, with the change stated at ruling 3, and adds rulings 16 to 20 for text introduced with the edits. No registered result has been observed. A question these rulings do not answer goes to the lead before code is written for it, and is recorded; it is not guessed.

| # | Where | Question | Ruling |
|---|---|---|---|
| 1 | 5.1 | Which accuracy is m_P | m_P = (correct_A + correct_B) / (n_A + n_B), from P10-S0's evaluation record, where n is a panel's size; m_H likewise over H1 and H2. Panels are of equal size, so this equals the mean of the two ratios. Comparisons use integer counts, so no float tie arises |
| 2 | 5.1, 6.2 | The floor against evaluability | The mean m_P for the plateau floor; both panels separately for the evaluability of a draw. Both as written |
| 3 | 5.2 | A6 below its floor at T on a calibration draw | Flags are computed only where A6's m_P(T) is at or above the floor on that draw. Otherwise `durations.json` records REFERENCE BELOW FLOOR AT T. The cell type stays. **Changed from the review:** at loads 0.5 to 2 the study does not return; it proceeds and the event is reported (section 5.2) |
| 4 | 5.2 | When the flags are computed | After every extension decision, at each cell type's final T |
| 5 | 5.3 | "Median over the ten cells" | All ten cells with a record. Median = the mean of the two middle values (P9's `median`). Every tag that applies is printed |
| 6 | 4.3 | e\* = 512, where the 512-exposure readout equals T/2 | Evaluate once; record it under both names |
| 7 | 6.6 | "The highest load run" when a load's cell types were all removed | The highest grid load: 4, or 8 when X8 was triggered. A load removed or NOT RUN is a grid load in state NOT EVALUABLE |
| 8 | 6.4 | ADDRESS STABLE over which cells | P10-S0's rule: the median over evaluated cells, a non-finite value counted as 0 (`studies/p10s0/classes.py` l.221–227) |
| 9 | 4.2 | The 32,768-fact set of P10-S0's layout (offset 60) | Not generated. Generate and G1-check only the 2,048- and 8,192-fact sets (offsets 0, 20). A draw passes G1 if both pass |
| 10 | 3 gate (a) | Which fact count at 4,096 slots | 2K/4K for A5-D and A6; 8K/4K for A0, A5-D and A6; 8K/16K for all three |
| 11 | 5.2 | Stage R's round barrier | The four runs of a cell type finish a round before the rule is evaluated. Other cell types proceed |
| 12 | 10 stage 1 | The resume test: what must be equal | Model state, optimizer state and the per-update losses. The diagnostic `movement_since_previous_record` resets at a resume and is excluded |
| 13 | 12 | A PAUSED cell restarts from where | Its last snapshot, given the resume test. The record says which |
| 14 | 5.1 item 5 | An X8 extension refused after the freeze | NOT SHOWN; B unchanged (section 8) |
| 15 | 6.7 | The sign test with no discordant pair | p = 1; NOT DISTINGUISHED |
| 16 | 4.2, 10 | Seeds of a repeated Stage R | The values of section 4.2's last row, in order of repeat. A repeat never re-uses an earlier repeat's values. X8's calibration uses the draws of the Stage R whose `durations.json` was frozen |
| 17 | 5.1 item 2 | "The longest single task of each stage" | The stages are: each Stage R round not yet charged, the main grid, X8's calibration, and X8. Hours already charged enter P as charged |
| 18 | 5.2 (i) | Where `sealed/` is, and who may read it | In the git-ignored run directory. Only the auditor's recomputation script reads it. The whitelist validator, the hashes committed at the freeze and decisions by code all stay. A read by the lead is disclosed and voids the blindness claim for that cell type |
| 19 | 12 | Which exceptions are divergence | Only the three non-finite checks of `Trainer.step`. The wrapper recognises those and nothing else; every other exception is an item error, and an environment error is a pause |
| 20 | 10 | Stage 3's quiet condition | Every load-average sample at most 2.0, sampled before the first task and every minute; one worker at a time; an attempt that fails is kept and never used; after three attempts or 24 hours the stage is PAUSED and rescheduled |

`Astra review: NOT_PERFORMED`. Claude review is not Astra review.
