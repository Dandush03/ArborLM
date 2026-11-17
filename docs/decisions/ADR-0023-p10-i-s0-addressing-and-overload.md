# ADR-0023 — P10-I-S0: Robust addressing and generalisation, including overload

**Status: DRAFT — NOT APPROVED. Nothing under this ADR is implemented, calibrated, frozen or run.**

- **Date:** 2026-11-17 (UTC). Draft 2: draft 1 revised after the independent specification review (`docs/reviews/p10-i-spec-reviews-2026-11-17/REVIEW_ADR-0023.md`, verdict NOT READY). Section 18 maps every finding to its disposition.
- **Study code:** P10IS0. Proposed package `studies/p10is0/`, config `configs/p10is0_overload.toml`, tests `tests/test_p10is0_*.py`.
- **Direction it follows:** `docs/reviews/p10-i-direction-2026-11-17/DIRECTION.md` section 4 (P10-I-S0) and section 5 (policy on limits). Its constraints are binding here.
- **Standing.** ArborLM is unproven research. `Astra review: NOT_PERFORMED`. A Claude review is neither Astra validation nor a human approval. The P10 delegation ("p10 can be self approve but p10-I need my review", ADR-0020 section 18) does not cover this study: every decision gate below is the human lead's.
- **Immutability.** P10-S0 (ADR-0020) is complete and accepted as registered. Nothing here revises its outcome, thresholds, seeds or records, and nothing is "reopened". This is a new study on new draws. No existing file is edited; all code is in new files.
- **Marking.** Numbers that are the drafter's judgment are marked **[choice]**; each is `PENDING LEAD REVIEW` and listed in section 16.

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
| Positive: Line Q holds at load 2 or above | On this synthetic task the recipe keeps at least 0.90 of the oracle-query reference's accuracy on trained-template panels, and on held-out templates at least 0.90 of its own panel accuracy (so at least 0.81 of the reference's panel accuracy) | Not capacity, not efficiency, not natural language, not a success of the ArborLM concept. Where the reference is itself far below 1.0 the label says so (section 6.5) |
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
- **Identity gate, part (a):** at 4,096 and at 16,384 slots, for A5-D, A0 and A6, the new path's initial model, one forward, one update and one full evaluation record are bit-identical to P10-S0's path on a shared rehearsal seed.
- **Identity gate, part (b):** at each new slot count (512, 1,024, 2,048, 8,192), the new path's model equals `p9ii.model.build_model(arm, N, seed)` tensor for tensor, and one update equals a direct reference implementation written for the gate (the auditor writes its own).
- **End-to-end gate at small stores:** the read swap (no fixed point; swapping twice restores the logits), the probe-set slot counts and ADDRESS STABLE run end to end at 512 and 1,024 slots on the rehearsal draw.

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
| Condition 6 decided no class | Accepted as a design note: condition 6 stays in the composite unchanged, and the report prints for every cell type whether it decided any cell. Risk stated: P10-S1's reference failed the same condition at low accuracy (`ACCEPTANCE.md` ruling 1); if A6 fails it at a loaded cell type in Stage R, that cell type is NOT EVALUABLE (section 5.2) |
| Record-length-free variant WX (candidate) | **Declined.** A different interface question; by ADR-0020 a WX failure can never be read as evidence. The drafter proposes the ledger mark it CLOSED AS RECORDED (unresolved) or name another study |
| 65,536 slots (candidate) | **Declined.** The question here is load, not size, and a 32,768-fact series at converged durations would cost more than the rest of the study. The drafter proposes the ledger route it to P10-I-S1's 16,384→65,536 item or close it as recorded |

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
- **Initialization seeds needed:** 2 registered (A5-D and A0 use the first on odd draws and the second on even draws; A6 uses the first on every draw); 2 for calibration, one per calibration draw, so that the two calibration runs differ in initialization as well as data; 1 for rehearsal and pipeline check.
- One seed per draw because P10-S1's corrected seed-block record shows the data draw dominating the spread in 24 of 28 comparisons (`results/p10s1-run-2026-11-17/ERRATUM_SEED_BLOCK.md`), and the per-draw bound depends on draws.
- **No seed value is proposed here.** Draft 1's initialization seeds (3001, 3002, 3091, 3092) were wrong: the memory initializers derive generator seeds as seed + 1000·k for k = 1…5 (`studies/p9/model.py` lines 272–276; `studies/p10s1/core.py` `DERIVED_INIT_OFFSETS`), so those values are P10-S0's derived seeds. Data, initialization and test seed ranges for all P10-I studies are assigned in one programme-wide registry that the lead will write, `docs/reviews/p10-i-direction-2026-11-17/SEED_REGISTRY.md`. Before any freeze the registry is checked by code against every literal **and derived** seed in the repository (the seed + 1000·k rule included), read from the code and configs and not from an ADR's list. This study's seed gate asserts its assigned ranges, with their derived sets, against that check.
- All registered and reserve draws are generated, hashed and G1-checked at the freeze, before any model sees them.

### 4.3 Checkpoints

Each registered cell is evaluated at three update counts: 512 exposures per fact (P10-S0's regime; descriptive), T/2 (for the check of section 5.3) and T (the only readout that enters a class). Probe records are written every 64 updates up to 4,096 updates and every 1,024 after **[choice]**; escape and COLLAPSE-FREE statistics after update 4,096 are therefore coarser than P10-S0's and are labelled so.

## 5. Training length: the convergence rule

Durations are in exposures per fact, e. Updates = e × F / 128 (512 exposures = 8,192 updates at 2,048 facts and 32,768 at 8,192 facts).

### 5.1 The rule (fixed before any rehearsal)

- **Base ladder:** e ∈ {512, 1,024, 2,048, 4,096, 8,192, 16,384}.
- **Measures:** m_P = mean accuracy on Panels A and B; m_H = mean accuracy on H1 and H2.
- **Plateau at e:** |m(2e) − m(e)| ≤ 0.01 **and** |m(4e) − m(2e)| ≤ 0.01, for both measures, for A5-D and A6, on both calibration draws. The rule is two-sided: held-out accuracy can fall with longer training, and a readout on a falling curve is not a converged readout. Two consecutive steps are required because one flat step can precede an escape.
- **Floor:** a plateau at e counts only if m_P(e) of A5-D and of A6 is at least the cell type's evaluability floor (0.90 at load 0.5; 0.50 at loads of 1 and above) on both calibration draws **[choice]**. Reason: P10-S1 had to add such a floor because without it every calibration cell met its rule before it had learned (ADR-0021 revision 5), and in P10-S0 A0 sat collapsed and then escaped (median 13,664 updates). Stated consequence: an A5-D that settles below the floor never has a plateau, the cell type is NOT SHOWN, and a failure there reads UNRESOLVED.
- **e\*** is the smallest ladder value with a plateau. **T = 2·e\*.** The rehearsal trains to 4·e\* = 2T. On the base ladder the largest e\* is 4,096 and the largest T is 8,192 exposures (524,288 updates at 8,192 facts; 131,072 at 2,048 facts). For comparison, P10-S1's loaded cells ran 6,144 and 3,072 exposures.
- **0.01 [choice]:** one tenth of the 0.10 tolerance of conditions 1 and 4.
- **One T per cell type**, used by every arm there. A0 takes it without a rehearsal of its own; every A0 label says so.
- **Extension rule (design ceiling, DIRECTION.md section 5).** If a cell type has no plateau on the base ladder, code extends that cell type's ladder by one further doubling (to 32,768; then e\* may be 8,192 and T 16,384 exposures) **[choice: one doubling]**, provided the study's projected total charged hours, computed from measured rates and durations only, stays within the hour budget the human lead sets at Decision 1 (recommended: 80 hours, section 11). Extensions are granted in order of ascending load, series M before S. The rule runs inside Stage R, before the freeze, with no registered seed observed and no person choosing.
- **At the extended ceiling, NOT SHOWN is the registered outcome.** The cell type runs at T = 16,384 exposures (8,192 if the budget refused the extension) and is marked **CONVERGENCE NOT SHOWN IN REHEARSAL**. Reason for stopping there: at 16,384 exposures one 8,192-fact cell is about 1,048,576 updates (about 3 hours), and one cell type about 15 hours on six workers; a longer duration is a new budget decision for the human lead in a new ADR, not a rule this study applies to itself.

### 5.2 The convergence rehearsal (Stage R)

- Arms A5-D and A6, every cell type of series M and S, two calibration draws: 32 runs. **Procedure, by code:** all four runs of a cell type train in doubling rounds, each round resuming from the previous round's snapshot; after each round the plateau rule is evaluated; the cell type stops at the first decision or at its ceiling. A resume-from-snapshot test (bit-identical to an uninterrupted run) is part of stage 1.
- **No registered seed is involved.** Calibration draws enter no class, no count and no table of the registered result.
- **Blind output: the mechanism.** (i) Stage R writes accuracies, losses and probe records only to a sealed directory outside the worktree. (ii) Its stdout and logs pass a whitelist validator, as P9-I's and P10-S0's rehearsals did: time, memory, shapes, counts, identities and `durations.json` only. (iii) `durations.json` holds, per cell type, e\*, T, SHOWN or NOT SHOWN, extension granted or refused, and reference-validity flags. (iv) The sha256 of every sealed file is committed at the freeze. (v) Before the registered outcome is recomputed, only the auditor's recomputation script reads the sealed files, and the auditor reports agree or disagree and nothing else. (vi) The plateau, extension and continue decisions are made by code. After the outcome is recomputed the curves are published as calibration records.
- **What may change after Stage R:** only T per cell type (by the rule), the removal of flagged cell types (below) and the hour cap (on cost). The choices on A0 and X8 (section 16 items 2 and 7) are made at Decision 1, before Stage R, and are not revisited after it.
- **Reference validity.** In Stage R, A6 is run through conditions 2, 3, 4, 5 and 6 at every cell type, at T. If A6 fails any of them on either calibration draw, the cell type is flagged: **all three lines are NOT EVALUABLE there**, it is removed from the frozen plan by this rule and prints **NOT RUN — REFERENCE FAILS CONDITION n**. No condition is dropped from the composite.
- **Stop before the freeze:** if either anchor cell type (load 0.5) is flagged or NOT SHOWN, the work returns to the human lead before the freeze. The grid is not run to print NOT EVALUABLE.

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
| all | NOT EVALUABLE | the cell type was flagged in Stage R, or its class is NOT_EVALUATED |
| A | HOLDS / FAILS | n_A ≤ 1 / n_A ≥ 2 |
| G | NOT READ | Line A FAILS |
| G | HOLDS (GENERALISES) / FAILS (DOES NOT GENERALISE) | n_G ≤ 1 / n_G ≥ 2 |
| Q | HOLDS / FAILS | class RELIABLE and ADDRESS STABLE (median over cells of the share of facts with the same top-1 slot on Panels A and B ≥ 0.80) / otherwise |

Stated consequence: with n_A = 1 and n_G = 1, Lines A and G hold and Line Q fails. Line Q is the stricter, unchanged composite; the other lines never upgrade it.

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

**Break point.** For each line, L is the largest grid load such that the line HOLDS at it and at every lower grid load ("none" if it does not hold at 0.5). ℓ₁ is the next grid load above L; its state is FAILS or NOT EVALUABLE. A HOLDS above ℓ₁ adds **NON-MONOTONE** and does not raise L. The report prints L_A, L_G, L_Q, each ℓ₁ with its state, and per series the per-condition failure counts at Line Q's ℓ₁.

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

- **Penalty against answer-only**, series M, per load including 0.5: d = (cells where A5-D succeeds and A0 fails) − (the reverse) over the ten pairs. IMPROVES ON A0 if d ≥ 6 **and** the exact two-sided sign-test p < 0.05; HARMS if d ≤ −6 and p < 0.05; otherwise NOT DISTINGUISHED **[choice]**.
- COLLAPSE-FREE k of n; the 512-exposure readout, labelled "P10-S0's regime on new draws; descriptive; not a replication verdict"; whether condition 6 decided any cell; the descriptive measures of section 6.1.

## 7. Study outcome: one decision procedure

Applied in order; exactly one headline results.

| Step | Test | Result |
|---|---|---|
| 0 | Any planned main-grid cell has no completed record | Stopped on a resource cap: **INCOMPLETE — PAUSED**; no scientific label; the analysis stage refuses to run; the run resumes when the cap is extended. If the human lead declines to extend, the study stays INCOMPLETE — PAUSED. Any other cause (failed gate, changed frozen input, failed cell record missing): **ENGINEERING_FAIL / INCOMPLETE**; no scientific label |
| 1 | Line Q at load 0.5 is NOT EVALUABLE | **NOT EVALUABLE — ANCHOR REFERENCE** |
| 2 | Line Q at load 0.5 FAILS | **ANCHOR NOT REPRODUCED AT THE CONVERGED DURATION** (with the anchor's convergence status). Lines A and G are printed for every load. P10-S0's outcome is not changed |
| 3 | L_Q ≥ 2 | **OVERLOAD-QUALIFIED UP TO L_Q**, followed by the status of ℓ₁ (below) |
| 4 | L_Q < 2 and Line Q at ℓ₁ is NOT EVALUABLE | **OVERLOAD NOT EVALUABLE AT ℓ₁ — REFERENCE; ADDRESSING QUALIFIED UP TO L_Q** |
| 5 | L_Q < 2, Line Q at ℓ₁ FAILS, convergence status NOT CONFIRMED | **OVERLOAD UNRESOLVED AT ℓ₁ — CONVERGENCE NOT CONFIRMED (RISING / DECLINING AT T / NOT SHOWN); ADDRESSING QUALIFIED UP TO L_Q** |
| 6 | L_Q < 2, Line Q at ℓ₁ FAILS, convergence status CONFIRMED | **OVERLOAD NOT QUALIFIED AT ℓ₁; ADDRESSING QUALIFIED UP TO L_Q** |

- **Status of ℓ₁ under step 3:** NOT EVALUABLE AT ℓ₁ — REFERENCE; UNRESOLVED AT ℓ₁; NOT QUALIFIED AT ℓ₁; or, when L_Q is the highest load run, NO BREAK FOUND ON THE GRID. If X8 was triggered and is not complete, the main-grid headline stands with **LOAD 8 PAUSED** or **LOAD 8 INCOMPLETE**.
- **Which line fails at ℓ₁** is printed per series, for each series whose Line Q FAILS: LINE A FAILS; LINE G FAILS (A HOLDS); or NEITHER ALONE (both hold, the composite or ADDRESS STABLE does not).
- Every headline is printed with the reference regime and convergence status at L_Q and at ℓ₁, both series' counts and bounds, L_A and L_G, and the fixed sentences: "W7 is told the record length. The memory is told the answer position. Synthetic fixed-length records; one frozen 27,392-parameter backbone. A5-D was chosen for P10-S0 after its P9-II result was observed. μ = 1.0 was calibrated at 0.5 facts per slot."
- UNRESOLVED and NOT EVALUABLE are registered outcomes. Neither is a basis for a further run on these cells without a new ADR approved by the human lead.

**Hypotheses (each can fail).** H23-A: Line Q HOLDS at load 0.5. H23-O: Line Q HOLDS at load 2. H23-G: at Line Q's ℓ₁, every series whose Line Q FAILS prints LINE G FAILS (A HOLDS); not read if ℓ₁ is NOT EVALUABLE. H23-P: A5-D IMPROVES ON A0 at load 2. A hypothesis reading is not a success of the science.

## 8. The conditional block X8

- **Trigger (fixed now):** X8 runs only if L_Q = 4 after the complete main grid, read by the frozen analysis at a gate stage that passes L_Q and nothing else to the launcher. Otherwise it prints **NOT RUN — BREAK LOCATED BELOW 8** (or the result of steps 0–2).
- Reason: the direction asks that a failure locate the break. If the recipe holds at 4, one more load answers where it breaks; if it fails at or below 4, load 8 adds cost and no location.
- X8's duration comes from the same rule, ladder, floor, extension rule and blind mechanism, on the same two calibration draws, run after the trigger and before any X8 cell. Its ceiling is the same as every cell type's (T at most 8,192 exposures, 16,384 with the extension). Its plan is frozen as an addendum listed in section 14; no main-grid file changes. If its reference is flagged, X8 prints NOT RUN — REFERENCE FAILS CONDITION n and the status of load 8 is NOT EVALUABLE.
- **Cost and cap:** X8 is included in the frozen projection and in the hour cap at its extended ceiling (T = 16,384 exposures), because its T is not known at the freeze.
- No higher load is run under this ADR.

## 9. Limits (DIRECTION.md section 5)

| Limit | Kind | Rule |
|---|---|---|
| Charged-hours cap (set at the freeze: twice the measured projection, X8 at its ceiling included) | Resource cap | May be extended by the human lead on cost projections only, never on outcome values; every planned cell still runs. A stage that reaches it is **PAUSED** and resumes from its registry |
| Per-stage time caps (twice each stage's projection) | Resource cap | Same |
| Memory guard, 3 GiB per worker, 18 GiB aggregate | Resource cap | A cell type whose rehearsed peak exceeds 1.5 GiB per worker is PAUSED before it starts and returns to the human lead. The registered run does not share the machine with another study's compute stage unless the human lead allows it and the aggregate of both stays under 36 GiB |
| Training length T per cell type | Design ceiling | The convergence rule; base ladder to T = 8,192 exposures; the written extension rule to 16,384 within the hour budget; beyond that NOT SHOWN is the registered outcome (section 5.1) |
| Number of loads | Design ceiling | Extended only by the X8 trigger |
| Registered draws that pass G1 | Design ceiling | Generate until ten pass, within four reserves; if fewer pass, return to the human lead before the freeze |
| Calibration draws (2), registered draws (10), one initialization seed per draw | Design ceiling | Fixed: the class rule and bounds are tied to ten draws |
| 0.90 × A6; A6 floors 0.90 and 0.50; conditions 2–6; at most one failed cell; ADDRESS STABLE 0.80; the combination rules of section 6.6; d ≥ 6 with p < 0.05 | Scientific threshold | Never relaxed after observation |
| Plateau step 0.01 (two-sided, two steps); plateau floor; T = 2·e\*; confirmation 0.02 | Scientific threshold | Fixed before Stage R; never changed after it |

No limit is extended because a partial result looks close.

## 10. Stages and machine load

Platform of record: the research machine (Apple M5 Max, 48 GB, macOS arm64, CPU only, six single-thread workers), as ADR-0020 section 10.4. Manifests record OS, architecture, Python, torch and thread settings. Bit-exact assertions, the identity gate included, are made on this platform only. Checks (`ruff`, `mypy`, `pytest`) run locally; GitHub CI is not used unless the human lead asks.

| # | Stage | Seeds touched | Quiet machine needed? |
|---|---|---|---|
| 1 | Implementation; unit tests; resume-from-snapshot test; analysis and report on synthetic registries with known answers: every state of section 6.4, every combination of section 6.6, every step and ℓ₁ status of section 7 (PAUSED and missing cells, reference below its floor, a flagged cell type at the anchor and above it, Line G NOT READ in one series, NON-MONOTONE, a replaced draw), and every descriptive section | tests | no |
| 2 | Identity and small-store gates (section 3); pipeline rehearsal end to end through the real launch scripts, on a plan built by the registered plan builder with only the seed set changed (asserted by a diff of the plans) | rehearsal | no |
| 3 | Timing rehearsal: seconds per update and peak memory for every (arm, cell type) | rehearsal | preferred, not required |
| 4 | Stage R (section 5.2), with the extension rule using stage 3's rates | calibration | no |
| 5 | Generation and G1 of registered and reserve draws; freeze; enumeration of every stage against the frozen plan itself (every item resolved to its inputs and outputs, no training) | registered, data only | no |
| 6 | **Decision 2 (human lead)**, then the registered run: gates; main grid; X8 gate; X8 calibration and X8 if triggered; analysis; report | registered | no |
| 7 | Independent recomputation from raw cell records (auditor); outcome statement to the human lead | — | no |

- **No stage needs a quiet machine for validity.** Every rule is in updates, exposures and accuracies. No wall-time comparison is registered. CPU seconds are descriptive.
- The load average is measured and recorded at the start of each stage and every ten minutes during it. Timing feeds projections and caps only; a loaded machine can cause a PAUSE, never a label. If the load average during the timing rehearsal exceeds 2.0, that is recorded and the projection is used as measured.

## 11. Cost projection (an estimate, to be replaced by the timing rehearsal)

Rates are P10-S0's registered-run rates (`docs/reviews/p10s0-results-2026-11-16/timing_out.txt`, seconds per update): at 4,096 slots A5-D 0.0098–0.0102, A6 0.0091–0.0093, A0 0.0144 (8K/4K); at 16,384 slots A5-D 0.0172, A0 0.0144, A6 0.0187. These are quiet-run rates: they were 0.57–0.91 of that study's "alone" rehearsal rates and 0.34–0.67 of its busy rates, so the figures below are optimistic for a machine in daily use. Not measured: 8,192 slots (interpolated to 0.013), 2,048 slots and below (set to 0.010). Durations are guesses until Stage R.

| Case | Main grid M / S / Stage R, CPU-hours | Six workers, charged hours without X8 | X8 and its calibration |
|---|---|---|---|
| Central guess (T = 1,024 / 2,048 / 2,048 / 4,096 exposures at loads 0.5 / 1 / 2 / 4) | 57.5 / 8.2 / 18.3 | about 15–16 | about 9 at T = 8,192 |
| Every T one ladder step higher | about 115 / 16 / 37 | about 29–31 | about 18 at T = 16,384 |
| Every cell type at the base ceiling (T = 8,192) | about 216 / 29 / 71 | about 54 | about 9–18 |
| Extension granted (per 8,192-fact cell type, T = 16,384) | — | about 15 more per cell type, plus its Stage R rounds | — |

The order of magnitude is **15 to 55 charged hours without X8 and without extensions**, and up to about 75 with X8 at its ceiling. The recommended hour budget for the extension rule is 80 hours **[choice]**. For scale: P10-S0 charged 6.09 hours and P10-S1 25.39. The longest single Stage R run at the base ceiling is about 5.5 hours. The timing rehearsal measures the rates at every size, the cost of three evaluations per cell and peak memory; Stage R measures the durations; the human lead sees the measured projection at Decision 2.

## 12. Stop rules and NOT EVALUABLE outcomes

- A failed gate, or a difference between frozen and running inputs, stops the run: ENGINEERING_FAIL. A second attempt needs the human lead's decision, with everything observed in the first attempt listed.
- A resource cap reached: the stage is PAUSED. It resumes from its registry; completed cells are not recomputed. No label is computed while any main-grid cell is missing (section 7 step 0).
- A failed cell is kept and not re-run. No re-run with changed settings.
- No registered seed is seen by a model before the freeze. After Stage R nothing changes except what section 5.2 lists.
- An anchor cell type flagged or NOT SHOWN in Stage R returns the work to the human lead before the freeze.
- NOT EVALUABLE arises in exactly two ways: a cell type flagged in Stage R, or a class NOT_EVALUATED (more than one draw with A6 below its floor). Section 7 says what each gives at the anchor and above it.
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
| A status note committed to a frozen ADR lost P10-S1's first attempt | **The frozen-input set is exactly:** every file under `studies/p10is0/` (which holds `freeze/plan.json`, `freeze/durations.json`, `freeze/stage_caps.json`, the sealed files' hashes and, if triggered, the X8 addendum), `configs/p10is0_overload.toml`, the launch scripts, the imported files of `studies/p9ii`, `studies/p10s0`, `studies/p9i`, `studies/p9` by sha256, and the data manifests named in the plan. Identity is checked by file hash, not by the commit at HEAD. **This ADR and everything under `docs/` and `results/` are not frozen inputs.** Run-time notes go to `NOTES.md` in the git-ignored run directory, or to chat. No commit is made in the run's worktree during a registered stage |
| A stage could not resume | Every stage keeps a per-cell registry; a PAUSED stage continues; completed cells are skipped by record hash |
| The throughput stage listed a cell the frozen plan did not run | Every stage builds its item list from the frozen plan only; stage 2 rehearses every stage end to end; stage 5 enumerates every stage against the frozen plan itself before Decision 2 |
| An unstated aggregation rule; a validity check the reference fails; a wrong descriptive section | Sections 6.4, 6.6 and 7 are total. A6 passes through every condition in Stage R (section 5.2). The analysis, descriptive sections included, is tested on synthetic registries; the auditor writes its own |
| A plateau rule met before anything was learned (ADR-0021 revision 5) | The plateau floor and the two-sided step (section 5.1) |
| A projection made under one machine load and run under another | Rates are measured in the timing rehearsal with the load average recorded; projections feed caps only (sections 10, 11) |
| A count gate stopped P10-S2 | Draws: generate until ten pass G1, within four reserves. Durations: train until the plateau rule is met, within the ceiling and its extension rule |
| One load, one length | Sections 4 and 5 |
| A macOS/Linux difference in exact ties | Platform of record named; bit-exact assertions on it only |
| A slot registry that rejects new sizes (found by this review) | New adapter code and the two-part identity gate (section 3) |
| CI cost | Checks run locally |

## 15. How the result feeds P10-I-S1's learned-address lane

P10-S1 omitted lane L because P10-S0 was not OVERLOAD-QUALIFIED. This ADR states what it provides; the lane's rules belong to ADR-0024.

1. **Only Line Q licenses a lane, and only at tested cell types.** A lane may use A5-D (μ = 1.0, this study's code hash, the T of that cell type) at the cell types of this study whose load is at most L_Q. Other (facts, slots) pairs, for example 32,768 facts at any load, are not licensed unless the human lead rules otherwise. Elsewhere the lane prints **OMITTED — ADDRESSING NOT QUALIFIED AT THIS CELL (ADR-0023)**.
2. The licence depends on L_Q only: none when the procedure ends at steps 0–2; loads up to L_Q in every other case, whatever the status of ℓ₁.
3. The lane's label carries the reference regime of each licensed cell type (REFERENCE NEAR CEILING or QUALIFIED RELATIVE TO A DEGRADED REFERENCE) and its convergence status.
4. Lines A and G license nothing by themselves.
5. **Timing.** A qualification recorded after P10-I-S1's freeze changes nothing in it (ADR-0020 section 9.2). Either P10-I-S1 freezes after this study's outcome is recomputed and accepted, or its lane is a separately frozen stage that waits. That choice is ADR-0024's and the human lead's.
6. This study uses a flat memory. A qualification here says nothing about addressing into the tree.

## 16. Open choices reserved for the human lead

1. **Load grid and slot counts** (section 4.1). Recommended: loads 0.5, 1, 2, 4 at 8,192 and at 2,048 facts.
2. **X8.** Recommended: conditional on L_Q = 4. Decided at Decision 1, not after Stage R.
3. **The convergence rule** (section 5): ladder, two-sided 0.01 step, floor, T = 2·e\*, the 0.02 check. Recommended as written.
4. **The extension rule and its hour budget** (sections 5.1, 11). Recommended: one further doubling, within 80 charged hours for the whole study; beyond it NOT SHOWN is the outcome. The alternative is no extension (cheaper; more UNRESOLVED) or a larger budget.
5. **The meaning of 0.90 under a degraded reference** (section 6.5). Recommended: the ratio at every load with the mandatory regime tag and the 0.50 floor. Alternative: qualify only where A6 ≥ 0.90.
6. **"Both series" and "every lower load"** (section 6.6), with its false-negative rate. Recommended: keep; it is the conservative reading.
7. **A0** in series M. Recommended: keep. Decided at Decision 1.
8. **μ is not re-calibrated; no dense baseline.** Recommended: both as written.
9. **The closure ledger:** the two declined items (WX; 65,536) and where they go (section 3).
10. **Lane licence scope** (section 15 item 1): tested cell types only, or wider.
11. **Seeds:** the programme-wide registry (section 4.2) before any freeze.
12. **Budget and timing:** the hour cap at Decision 2; when the run may occupy six cores; whether it may share the machine with another study.
13. Approval of this specification for implementation and rehearsals (Decision 1), and separately of the registered run (Decision 2). Any second attempt; merge; publication.

Still unsure, for the confirmation review: whether the plateau floor applied to A5-D (not only to A6) is the right choice; whether the 0.01 step can be met under a degraded reference; whether condition 6 holds for A6 at loaded cell types.

## 17. Approval record

None. No approval of this specification exists. Nothing is implemented, calibrated, frozen or run.

## 18. Review record

Draft 1 was reviewed by the `arbor-auditor` subagent (Claude Opus 5.5): `docs/reviews/p10-i-spec-reviews-2026-11-17/REVIEW_ADR-0023.md`, verdict NOT READY. This revision is by the drafter (Claude Fable 5.2). The drafter re-read `studies/p9ii/core.py` line 252 and `studies/p9/model.py` lines 272–276 and found the reviewer's two factual corrections right. No finding is disputed. A confirmation review of this draft has not been performed. Neither review is Astra validation or a human approval.

| Finding | Severity | Disposition | Where |
|---|---|---|---|
| 1 Outcome function not total (a–f) | BLOCKING | FIXED | 5.2 (flag makes all lines NOT EVALUABLE; stop before freeze), 6.4, 6.6, 7 (steps 0–6, ℓ₁ status), 10 stage 1, 12 |
| 2 Existing code cannot run the new slot counts | BLOCKING | FIXED | 3 (new adapter code, two-part identity gate, small-store gate), 14 |
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

The coordinator's instruction to remove a statement that the machine idles at load 1.0–1.2: draft 1 did not contain one; section 10 measures the load at each stage.

`Astra review: NOT_PERFORMED`.
