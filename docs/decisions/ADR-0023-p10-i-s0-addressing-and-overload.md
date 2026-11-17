# ADR-0023 — P10-I-S0: Robust addressing and generalisation, including overload

**Status: DRAFT — NOT APPROVED. Nothing under this ADR is implemented, calibrated, frozen or run.**

- **Date:** 2026-11-17 (UTC). Draft 1, written by the lead's drafting session (Claude Fable 5.2) for an independent specification review (Opus 5.5) and then the human lead's review.
- **Study code:** P10IS0. Proposed package `studies/p10is0/`, config `configs/p10is0_overload.toml`, tests `tests/test_p10is0_*.py`.
- **Direction it follows:** `docs/reviews/p10-i-direction-2026-11-17/DIRECTION.md` section 4 (P10-I-S0) and section 5 (policy on limits). Its constraints are binding here.
- **Standing.** ArborLM is unproven research. `Astra review: NOT_PERFORMED`. A Claude review is neither Astra validation nor a human approval. The P10 delegation ("p10 can be self approve but p10-I need my review", ADR-0020 section 18) does not cover this study: every decision gate below is the human lead's.
- **Immutability.** P10-S0 (ADR-0020) is complete and accepted as registered. Nothing here revises its outcome, thresholds, seeds or records, and nothing is "reopened". This is a new study on new draws.
- **Marking.** Numbers that are the drafter's judgment are marked **[choice]** and listed for the reviewer in section 16.

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
| Positive: Line Q holds at load 2 or above, with convergence confirmed | On this synthetic task the recipe keeps at least 0.90 of what an oracle-addressed store holds at that load, on trained and on held-out templates | Not capacity, not efficiency, not natural language, not a success of the ArborLM concept. Where the oracle is itself far below 1.0 the label says so (section 6.5) |
| Negative: Line Q fails at load 2 (or at 1) with convergence confirmed | The recipe as calibrated does not carry over to more facts than slots, and the lines say whether addressing (A) or template generalisation (G) breaks first. P10-S0's finding is then not a training-length artefact | Not that learned addressing cannot work under overload: one recipe, one calibrated value, one interface |
| Inconclusive | The anchor is not evaluable, or the first failing load fails while the convergence rule was not met (UNDERTRAINING NOT EXCLUDED) | No statement about overload in either direction |

A failure is a registered outcome. It is not a reason to extend training, add loads or change a threshold (DIRECTION.md section 4).

## 2. Background: the registered findings this follows from

All numbers are copied from the records named.

| Finding | Value | Record |
|---|---|---|
| P10-S0 outcome | ADDRESSING-QUALIFIED (4,096 AND 16,384), arm A5-D (label-free, μ = 1.0), 512 exposures per fact, 0.5 facts per slot; accepted as registered | `results/p10s0-run-2026-11-16/OUTCOME.md`; ADR-0020 addendum of 2026-11-16 |
| OVERLOAD NOT QUALIFIED | A5-D at 8,192 facts / 4,096 slots: 1 of 10 cells succeed; class FAILS | `results/p10s0-run-2026-11-16/classes.csv` |
| Why the nine cells fail | Condition 4 (held-out templates) alone. Panel accuracy 0.946–0.956 in every cell; oracle reference A6 0.993–0.997; no collapse in 10 of 10; condition 6 passed | `docs/reviews/p10s0-results-2026-11-16/REVIEW.md` section 5 item 1 |
| Size of the condition-4 miss | Margins from −0.180 to +0.001 across the ten draws (d01 −0.180, d02 −0.169, d03 −0.137, d04 −0.112, d05 −0.092, d10 −0.087, d08 −0.055, d09 −0.039, d06 −0.007, d07 +0.001) | `docs/reviews/p10s0-results-2026-11-16/extras_out.txt` |
| Condition-4 margin at 0.5 facts per slot | Smallest margin +0.061 at 2K/4K and +0.024 at 8K/16K (A5-D) | same REVIEW.md, item 3 |
| A0 (answer-only) under overload | 0 of 10 cells; condition 4 fails in all ten | same REVIEW.md, item 1 |
| One load, one length | S0 tested overload at two facts per slot and 32,768 updates only | ADR-0020 sections 5.3, 6.1 |
| S0 cost | 21,941 s charged (6.09 h) of 22 h; Q1 training 13,415 s | `results/p10s0-run-2026-11-16/OUTCOME.md` |
| Oracle-addressed flat memory at 8 facts per slot (P10-S1, F-OQ) | Mean a_use 0.390 → 0.654 at 8K/1K (8,192 → 393,216 updates) and 0.392 → 0.637 at 32K/4K (16,384 → 786,432) | `results/p10s1-run-2026-11-17/OUTCOME.md` section 4; `audit/AUDIT.md` |
| Same arm at 2 facts per slot | 0.948 → 0.996 at 8K/4K; 0.991 → 0.999 at 2K/1K | same |
| Lane L of P10-S1 | OMITTED — NOT OVERLOAD-QUALIFIED | `results/p10s1-run-2026-11-17/RESULTS.md` line 10; ADR-0021 section 5.6 |

Two remarks on the records.

1. The condition-4 misses at 8K/4K are not near-misses. Seven of ten are worse than −0.05. The summary "at about 0.95 accuracy" in the outcome statement describes panel accuracy, not the held-out ratio.
2. The task brief says the flat memory at 8 facts per slot "was still rising" at 393,216–786,432 updates. The drafter did not find that sentence in `OUTCOME.md`. The nearest registered figure is the audit's last-doubling gain of 0.016–0.061 for F-OQ at 32K/4K (`audit/AUDIT.md`, capacity section). The design below does not depend on the sentence: durations come from this study's own convergence rule.

P10-S1's update counts are evidence that loaded cells need far more than 512 exposures per fact under oracle addressing. They are not carried over as durations.

## 3. System, arms and what each isolates

**System.** Exactly ADR-0019 sections 3–4 and ADR-0020 section 5.1: the frozen 27,392-parameter backbone, the P9-I task, flat memory (cosine keys, key width 16, top-8, temperature 0.2) read and added at answer sites only, alphabet-only loss, one AdamW at 0.003, clip 1.0, batch of 16 contexts = 128 answer sites, the W7 query. The memory is told the answer position in every arm. No backbone parameter is trained. Arm code is imported unedited from `studies.p9ii` and `studies.p10s0`; a gate asserts bit-identity of one forward and one update against them.

| Arm | Definition | Runs at | Isolates |
|---|---|---|---|
| **A5-D** | answer-only + μ·L_div on the batch's normalized queries, μ = 1.0 (P9-II's audited calibration; ADR-0020 section 3.4) | every cell type | the qualified recipe, unchanged |
| **A6** | oracle-query reference (R1) | every cell type, every draw | the denominator of condition 1: what the store holds under ideal addressing at the same load and duration |
| **A0** | answer-only W7, untuned | series M only | the diversity penalty: A5-D against A0 is one change |

Not run, and why:

- **A1, A2** (address supervision): no target injection exists with more facts than slots (ADR-0020 section 5.1). Both were contradicted at 16,384 in P10-S0.
- **A7** (dense window) and any capacity baseline: capacity under load is P10-I-S1's question (ADR-0024). This study makes no claim against a dense alternative. Flagged in section 16.
- **A re-calibration of μ.** μ = 1.0 was calibrated at 0.5 facts per slot. Under overload it is an untested transfer, as it was in P10-S0. Re-tuning it here would add a second change beside training length. A failure is therefore a failure of the recipe as calibrated (section 13). Flagged in section 16.
- **WX and the 65,536 probe**: other shortfalls of P10-S0; not this study's question.

**Comparisons, one change each.** Across loads within a series: only the slot count changes (same facts, streams, panels and initialization seed per draw). A5-D against A6: learned against oracle query. A5-D against A0: the penalty. Series M against series S at equal load: fact and slot counts change together at fixed ratio.

## 4. Load grid, data, seeds, sizes

### 4.1 Grid **[choice]**

Load is varied by changing the slot count at a fixed fact set, so that every load of a series is read on the same facts and panels.

| Series | Facts | Slots (load in facts per slot) | Arms | Draws × init seeds | Cells |
|---|---|---|---|---|---|
| **M** (main) | 8,192 | 16,384 (0.5), 8,192 (1), 4,096 (2), 2,048 (4) | A5-D, A0, A6 | 10 × 1 | 120 |
| **S** (small) | 2,048 | 4,096 (0.5), 2,048 (1), 1,024 (2), 512 (4) | A5-D, A6 | 10 × 1 | 80 |
| **X8** (conditional, section 8) | 8,192 | 1,024 (8) | A5-D, A0, A6 | 10 × 1 | 30 |

Reasons.

- **0.5** is the anchor: P10-S0's qualified regime at both of its sizes (8K/16K and 2K/4K), now at the converged duration. It is the positive control of the study.
- **1** and **2** bracket P10-S0's failure: S0 passed at 0.5 and failed at 2, so the break lies in between or is a training-length effect. Load 2 in series M is S0's own cell type (8K/4K).
- **4** extends the grid if 2 holds. **8** is P10-S1's loaded regime; it is run only under the rule of section 8.
- **Two series** so that a result at a load is not a property of one slot count: load 2 is read at 4,096 slots and at 1,024 slots. 32,768 facts are not used: at the durations expected, a third series would cost more than the other two together (section 11).
- **Slot counts covered:** 512 to 16,384. Nothing is said about 65,536.

### 4.2 Draws and seeds

- **Registered draws:** 10, each a complete independent data set (2,048-fact and 8,192-fact sets, training stream, calibration stream, Panels A and B, H1, H2, unseen-fact control, as ADR-0020 section 7). **Reserve draws:** 4. Draws are generated until ten pass gate G1, within the budget of four reserves; the count of reserves used is recorded and is not a claim.
- **Calibration draws:** 2, used only by the convergence rehearsal (section 5). **Rehearsal draw:** 1, for the pipeline and timing rehearsals. **Pipeline check and unit tests** have their own seeds.
- **Initialization seeds** 3001 and 3002. A5-D and A0 use 3001 on odd draws and 3002 on even draws (as P10-S0 at 8K/4K); A6 uses 3001 on every draw. One seed per draw because P9-I's diagnostics and P10-S0 found outcomes clustered by draw, and the per-draw bound depends on draws.
- **Proposed namespaces [choice; to be reconciled across the six P10-I drafts]:** data 300001–309999 (registered bases 300001 + 100·(d − 1); reserves from 301001; calibration 308001 and 308101; rehearsal 309001; pipeline check 309101); initialization 3001–3002, rehearsal and calibration 3091–3092; unit tests 930001–930999. None overlaps an earlier study: P9 (170001–179933, 1701–1702), P9-I (180101–182020, 1791–1802, 900001–900233), P9-II (190001–191599, 1891–1902, 910001–919999), P10-S0 (200001–209999, 2001–2002, 2091–2092, 920001–920999), P10-S1 (210001–219999, 2101–2192, 921001–921999), P10-S2 (220001–229999), as listed in ADR-0020 section 7. A gate asserts disjointness in code, and the specification review repeats the repository search.
- All registered and reserve draws are generated, hashed and G1-checked at the freeze, before any model sees them.

### 4.3 Checkpoints

Each registered cell is evaluated at three update counts: 512 exposures per fact (P10-S0's regime; descriptive), T/2 (for the convergence check of section 5.3) and T (the only readout that enters a class). Probe records are written every 64 updates up to 4,096 updates and every 1,024 updates after **[choice; bounds record size at long durations]**.

## 5. Training length: the convergence rule

Durations are in exposures per fact, e. Updates = e × F / 128 (512 exposures = 8,192 updates at 2,048 facts and 32,768 at 8,192 facts).

### 5.1 The rule (fixed before any rehearsal)

- **Ladder:** e ∈ {512, 1,024, 2,048, 4,096, 8,192, 16,384}.
- **Measures:** m_P = mean accuracy on Panels A and B; m_H = mean accuracy on H1 and H2. Both are used because P10-S0's failure was on held-out templates and that is the quantity that must not be undertrained.
- **Plateau at e:** m(2e) − m(e) ≤ 0.01 **and** m(4e) − m(2e) ≤ 0.01, for both measures, for A5-D and A6, on both calibration draws. The rule is one-sided: a decline counts as no further gain. Two consecutive steps are required because a single flat step can be a pause before an escape (P10-S0: A0 escaped at a median of 13,664 updates).
- **e\*** is the smallest ladder value with a plateau. **The registered duration is T = 2·e\*.** The rehearsal therefore trains to 4·e\* = 2T.
- **0.01 [choice]:** one tenth of the 0.10 tolerance of conditions 1 and 4, so that two further doublings are not expected to move a ratio across its threshold by training alone.
- **One T per cell type** (facts, slots), used by every arm at that cell type. A0 takes it without a rehearsal of its own; every A0 label says so.
- **Ceiling (design ceiling).** T may be at most 8,192 exposures (524,288 updates at 8,192 facts; 131,072 at 2,048 facts), and 16,384 for X8. If no plateau exists with T at or under the ceiling, the cell type runs at the ceiling and is marked **CONVERGENCE NOT SHOWN IN REHEARSAL**. The ceiling is not raised after any accuracy has been seen. Reason for the figure: P10-S1's oracle-addressed cell at 8K/1K ran 393,216 updates; the ceiling for loads up to 4 is above that, and X8's is 2.7 times it.

### 5.2 The convergence rehearsal (Stage R) and what the lead may see

- Arms A5-D and A6, every cell type of series M and S, the two calibration draws, initialization seed 3091: 32 runs. Each run continues up the ladder only until the plateau rule can be decided for its cell type ("train until the rule is met, within the ceiling").
- **No registered seed is involved.** Calibration draws enter no class, no count and no descriptive table of the registered result.
- **Blind output [choice].** Stage R writes two things: `durations.json` (per cell type: e\*, T, and SHOWN or NOT SHOWN) and a sealed curve file. The lead reads only `durations.json`. The auditor recomputes it from the sealed curves with its own code and reports agree or disagree, and nothing else. The curves are opened after the registered outcome is recomputed and are then printed as calibration records. Reason: the rehearsal necessarily measures A5-D under overload on two draws, and those accuracies must not shape any choice between the rehearsal and the freeze. After Stage R only T per cell type, the caps and the cuts of section 11 may change.
- **Reference validity.** During Stage R, A6 is run through every condition of section 6.2 that applies to a learned arm (2, 3, 4, 5, 6) at every cell type, at T. A condition that A6 fails on either calibration draw at a cell type is not applied at that cell type; the label there prints **CONDITION n NOT APPLIED — REFERENCE FAILS IT**, and Line Q is then NOT EVALUABLE at that cell type (the composite is not shortened). This flag is part of the blind output.

### 5.3 The check on registered draws (no adaptation)

Per cell type and arm (A5-D, A6), after the run: the median over the ten cells of m(T) − m(T/2), for m_P and m_H. **CONVERGENCE CONFIRMED** if every such median is ≤ 0.02 **[choice: the rehearsal's 0.01 plus 0.01 for draw-to-draw spread]** and the cell type was SHOWN in rehearsal; otherwise **CONVERGENCE NOT CONFIRMED**. The check changes no duration and triggers no further training. It decides only how a failure is worded (section 7).

## 6. Measurements and the rules that give labels

### 6.1 Recorded

As ADR-0020 section 8.1 and ADR-0019 sections 8.1–8.2: probe records during training; at each readout, accuracy on Panels A, B, H1, H2, memory-off and value-permuted accuracy, the unseen-fact control, the probe-set slot counts, address stability, the read swap and a_use, LM capability, CPU seconds and peak memory. Added, descriptive only: the share of facts whose top-1 slot on H1 (and H2) equals the one on Panel A; H-panel accuracy divided by A6's H-panel accuracy; per-template held-out accuracy. No efficiency claim is made from any cost figure.

### 6.2 Cell conditions (thresholds carried unchanged from ADR-0019 section 8.3 and ADR-0020 section 8.2)

| # | Condition | On |
|---|---|---|
| 1 | accuracy ≥ 0.90 × A6's on the same draw, cell type and readout | Panels A and B |
| 2 | accuracy with values permuted and with the memory disabled inside the G2 chance interval | Panels A and B |
| 3 | on the probe set, at least 128 distinct top-1 slots and no slot top-1 for more than 10 of the 512 sites | probe |
| 4 | accuracy on H1 and on H2 ≥ 0.90 × the cell's own accuracy | against Panel A and against Panel B |
| 5 | no LEAKAGE flag | unseen-fact control |
| 6 | a_use ≥ 0.95 × accuracy | Panels A and B |

- **Evaluability of a draw at a cell type:** A6 ≥ 0.90 on both panels at load 0.5 (as P10-S0's core cells); A6 ≥ 0.50 at loads 1 and above (as P10-S0 at 8K/4K). Otherwise the draw is NOT_EVALUATED there.
- Condition 3 at the smallest store: with 256 probe facts spread evenly over 512 slots, the expected number of distinct top-1 slots is about 201 and the chance that some slot is top-1 for more than 10 sites is under 1% (drafter's Poisson estimate; the reviewer is asked to recompute it). The condition is therefore reachable at every cell type and is not changed.
- **A-conditions** are 1, 2, 3, 5, 6. **The G-condition** is 4. A cell **succeeds** (P10-S0's criteria) if all six hold.

### 6.3 Class of an arm at a cell type (ADR-0020 section 8.3, the 10-cell rule, unchanged; first match wins)

| Order | Class | Rule |
|---|---|---|
| 1 | NOT_EVALUATED | more than one draw NOT_EVALUATED |
| 2 | RELIABLE | at most one failed cell among the evaluated cells, and no LM CAPABILITY REDUCED (ADR-0019 section 8.4 (b)) |
| 3 | UNRELIABLE | at least 3 successes |
| 4 | FAILS | otherwise |

One-sided 95% Clopper–Pearson per-draw bounds are printed: 10 of 10 gives 0.741; 9 of 10 gives 0.606; 9 of 9 gives 0.717.

### 6.4 The three lines at a cell type (arm A5-D)

Let n_A be the number of evaluated cells failing any A-condition, n_G the number of evaluated cells that pass all A-conditions and fail condition 4, and n_Q = n_A + n_G.

| Line | Label | Rule |
|---|---|---|
| A | HOLDS / BREAKS | n_A ≤ 1 / n_A ≥ 2 |
| G | GENERALISES / DOES NOT GENERALISE / NOT READ | n_G ≤ 1 / n_G ≥ 2 / Line A BREAKS |
| Q | QUALIFIED AT THIS CELL TYPE | class RELIABLE (n_Q ≤ 1, no LM flag) **and** ADDRESS STABLE (median over cells of the share of facts with the same top-1 slot on Panels A and B ≥ 0.80) |

Every line is NOT EVALUABLE where the class is NOT_EVALUATED. Stated consequence: with n_A = 1 and n_G = 1, Lines A and G read HOLDS and GENERALISES and Line Q reads not qualified. Line Q is the stricter, unchanged composite; the other two lines never upgrade it.

### 6.5 What "0.90 of the oracle reference" means under overload

Condition 1 is a ratio, at every load, to A6 trained on the same draw, at the same cell type, for the same T. It is not lowered and not replaced. It answers an addressing question only: how much of what the store holds under ideal addressing the learned query keeps. It is not a statement about how much the store holds. So that a pass cannot be read as one:

- Every label of a cell type carries the **reference regime**, from the median over draws of A6's mean panel accuracy: **REFERENCE NEAR CEILING** (≥ 0.90) or **REFERENCE DEGRADED (A6 = x)** (0.50 ≤ x < 0.90). The absolute accuracies of A5-D and A6 are printed beside every ratio.
- A qualification under a degraded reference is printed **QUALIFIED RELATIVE TO A DEGRADED REFERENCE** and may not be shortened.
- Below 0.50 the draw is not evaluated: most facts are then not retrievable under ideal addressing, and the cell would test the store, not the address **[choice; the 0.50 floor is ADR-0020's]**.
- Because both arms must plateau before T is set (section 5.1), the ratio is not an artefact of one arm still rising.

On P10-S1's figures the reference is expected near ceiling at loads up to 2 and degraded at 8 (0.637–0.654); load 4 is unmeasured. These are expectations, not rules.

### 6.6 Combining cell types into a load, and loads into a break point

- **At a load ℓ of the main grid (0.5, 1, 2, 4):** a line holds at ℓ only if it holds at ℓ in **both** series. If it holds in one series only, the label reads "IN SERIES M ONLY (slots N)" or "IN SERIES S ONLY (slots N)" and the load counts as not holding. X8 has one series; its labels say "ONE SERIES".
- **Break point of a line:** L is the largest grid load such that the line holds at that load and at every lower grid load. If the line fails at 0.5, L is "none". If a line holds at a load above its first failure, the label adds **NON-MONOTONE** and L is not raised.
- The study prints L_A, L_G and L_Q, the first failing load of each, and for the first failing load of Line Q the per-condition failure counts in each series.

### 6.7 Annotations (enter no line)

- **Penalty against answer-only**, series M, per load: d = (cells where A5-D succeeds and A0 fails) − (the reverse) over the ten pairs; IMPROVES ON A0 if d ≥ 6, HARMS if d ≤ −6, otherwise NOT DISTINGUISHED; exact sign-test p printed. **[choice: 6–0 is the smallest split of ten pairs with a two-sided exact p below 0.05 (0.031)]**
- COLLAPSE-FREE k of n; the 512-exposure readout beside the readout at T, labelled "P10-S0's regime on new draws; descriptive; not a replication verdict"; the added descriptive measures of section 6.1.

## 7. Study outcome (first match wins)

| Order | Outcome | Rule |
|---|---|---|
| 1 | **ENGINEERING_FAIL / INCOMPLETE** | a failed gate; a difference between frozen and running inputs (section 14); a main-grid cell without a record that is not PAUSED. No scientific label is derived |
| 2 | **NOT EVALUABLE — ANCHOR REFERENCE** | at load 0.5, either series is NOT_EVALUATED |
| 3 | **ANCHOR NOT REPRODUCED AT THE CONVERGED DURATION** | Line Q does not hold at load 0.5. Lines A and G are still printed for every load; L_Q is "none". P10-S0's outcome is not changed by this |
| 4 | **OVERLOAD-QUALIFIED UP TO ℓ** (ℓ = L_Q ≥ 2) | printed with the reference regime at ℓ, the convergence status at ℓ, both series' counts and bounds, and L_A, L_G |
| 5 | **OVERLOAD UNRESOLVED AT ℓ — UNDERTRAINING NOT EXCLUDED** | L_Q < 2 and, at the first failing load ℓ, either series is CONVERGENCE NOT CONFIRMED or NOT EVALUABLE |
| 6 | **OVERLOAD NOT QUALIFIED; ADDRESSING QUALIFIED UP TO L_Q** | L_Q < 2 and the first failing load is CONVERGENCE CONFIRMED in both series. Printed with which line fails there: Line A, Line G, or neither alone |

Under row 4, a first failing load above ℓ is worded the same way: "NOT QUALIFIED AT ℓ′" if convergence is confirmed there, "UNRESOLVED AT ℓ′" if not. Rows 4–6 are always printed with the fixed sentences: "W7 is told the record length. The memory is told the answer position. Synthetic fixed-length records; one frozen 27,392-parameter backbone. A5-D was chosen for P10-S0 after its P9-II result was observed. μ = 1.0 was calibrated at 0.5 facts per slot."

**Hypotheses (each can fail).** H23-A: Line Q holds at load 0.5 in both series at T. H23-O: Line Q holds at load 2 in both series with convergence confirmed. H23-G: at the first load where Line Q fails, Line A HOLDS and Line G reads DOES NOT GENERALISE (the failure is template generalisation, as in P10-S0). H23-P: A5-D IMPROVES ON A0 at load 2. A hypothesis reading is not a success of the science.

## 8. The conditional block X8

- **Trigger (fixed now):** X8 runs only if L_Q = 4 after the main grid, read by the frozen analysis at a gate stage that prints L_Q and nothing else to the launcher. Otherwise X8 prints **NOT RUN — BREAK LOCATED BELOW 8** (or the reason of rows 1–3).
- Reason: the direction asks that a failure locate the break. If the recipe still holds at 4, the break is not located and one more load answers it. If it fails at or below 4, a load of 8 adds cost and no location.
- X8's duration comes from the same rule, on the same two calibration draws, run after the trigger and before any X8 cell. Its `durations.json` entry and plan are frozen as an addendum whose inputs are listed in section 14; no main-grid file changes.
- If Line Q holds at 8 the outcome reads OVERLOAD-QUALIFIED UP TO 8 — NO BREAK FOUND ON THE GRID. No higher load is run under this ADR.

## 9. Limits (DIRECTION.md section 5)

| Limit | Kind | Rule |
|---|---|---|
| Charged-hours cap (set at the freeze from the timing rehearsal: twice the projection) | Resource cap | May be extended by the human lead on cost projections only, never on outcome values; every planned cell still runs. A stage that reaches it is **PAUSED** and resumes from its registry |
| Per-stage time caps (twice each stage's projection) | Resource cap | Same. PAUSED, resumable |
| Memory guard, 3 GiB per worker, 18 GiB aggregate | Resource cap | A cell type whose rehearsed peak exceeds 1.5 GiB per worker is PAUSED before it starts and returns to the human lead. Nothing is changed to make it fit |
| Training length T per cell type | Design ceiling | Set by the convergence rule of section 5; ladder ceiling 8,192 exposures (16,384 for X8); not raised after observation; a cell type at the ceiling is marked NOT SHOWN |
| Number of loads | Design ceiling | Extended only by the X8 trigger of section 8 |
| Registered draws that pass G1 | Design ceiling | Generate until ten pass, within four reserves; if fewer than ten pass, return to the human lead before the freeze |
| Calibration draws (2), registered draws (10), one initialization seed per draw | Design ceiling | Fixed. Not extended: the class rule and the bounds are tied to ten draws |
| 0.90 × A6 (condition 1); A6 floors 0.90 and 0.50; conditions 2–6; at most one failed cell; ADDRESS STABLE 0.80; "both series"; d ≥ 6 | Scientific threshold | Never relaxed after observation |
| Plateau step 0.01; confirmation 0.02; two consecutive steps; T = 2·e\* | Scientific threshold | Fixed before Stage R; never changed after it |

No limit is extended because a partial result looks close.

## 10. Stages and machine load

Platform of record: the research machine (Apple M5 Max, 48 GB, macOS, CPU only, six single-thread workers), as ADR-0020 section 10.4. Manifests record OS, architecture, Python, torch and thread settings. Bit-exact assertions are made on this platform only; any test that depends on exact ties is platform-conditional. Checks (`ruff`, `mypy`, `pytest`) run locally; GitHub CI is not used for this study's branches ([skip ci]) unless the human lead asks.

| # | Stage | Seeds touched | Quiet machine needed? |
|---|---|---|---|
| 1 | Implementation, unit tests, analysis and report on synthetic registries with known answers (every label, every row of section 7, every descriptive section, NOT_EVALUATED, NON-MONOTONE, PAUSED, a replaced draw) | tests | no |
| 2 | Pipeline rehearsal, end to end through the real launch scripts, on a plan built by the registered plan builder with only the seed set changed (asserted by a diff of the two plans) | rehearsal | no |
| 3 | Stage R, convergence rehearsal (section 5.2) | calibration | no |
| 4 | Timing rehearsal: seconds per update and peak memory for every (arm, cell type), run alone | rehearsal | preferred, not required |
| 5 | Generation and G1 of registered and reserve draws; freeze; enumeration run of every stage against the frozen plan itself (every item of every stage resolved to its inputs and outputs, no training) | registered, data only | no |
| 6 | **Decision 2 (human lead)**, then the registered run: gates; main grid; X8 gate; X8 calibration and X8 if triggered; analysis; report | registered | no |
| 7 | Independent recomputation from raw cell records (auditor); outcome statement to the human lead | — | no |

- **No stage needs a quiet machine for validity.** Every rule is in updates, exposures and accuracies. No wall-time comparison is registered. CPU seconds are descriptive and are printed with the load average at the start of each stage.
- Timing is used for projections and caps only. If the load average at the timing rehearsal is above 2.0, the fact is recorded and the projection is used as measured (it can only be pessimistic). A slow registered run can cause a PAUSE, never a label.
- The registered run is long (section 11). The human lead decides when it may occupy six cores; it can be paused and resumed between cells.

## 11. Cost projection (an estimate, to be replaced by the timing rehearsal)

Rates measured in P10-S0's registered run (`docs/reviews/p10s0-results-2026-11-16/timing_out.txt`, seconds per update): A5-D 0.0098–0.0102 and A6 0.0091–0.0093 at 4,096 slots; A5-D 0.0172, A0 0.0144, A6 0.0187 at 16,384 slots. Not measured: 8,192 slots (interpolated to 0.013) and 2,048 slots and below (set to 0.010, the 4,096-slot rate). Durations are guesses until Stage R: T of 1,024 / 2,048 / 2,048 / 4,096 exposures at loads 0.5 / 1 / 2 / 4, and 8,192 at load 8.

| Block | Cells | Summed CPU-hours (central guess) | Six workers, hours |
|---|---|---|---|
| Main grid, series M | 120 | 56 | 9.4 |
| Main grid, series S | 80 | 8 | 1.4 |
| Stage R (32 runs to 2T) | — | 18 | 3.0 |
| Pipeline and timing rehearsals, generation, gates, evaluation, analysis | — | — | about 1.5 |
| **Without X8** | **200** | | **about 15–16** |
| X8 and its calibration | 30 + 4 runs | 44 + 12 | about 10 |
| **With X8** | **230** | | **about 26** |

If every T is one ladder step higher than guessed, the totals are about 31 and 51 hours. For scale: P10-S0 charged 6.09 hours and P10-S1 25.39 hours. The order of magnitude is **15 to 50 charged hours**, and the single largest uncertainty is T at load 4. Stage R measures the durations; the timing rehearsal measures the rates at 512–2,048 and 8,192 slots, the cost of three evaluations per cell, and peak memory. The cap is set from those, and the human lead sees the measured projection at Decision 2.

Cuts, if the human lead prefers a smaller study (recommendation in section 16): drop A0 (saves about a third of series M); drop X8.

## 12. Stop rules and NOT EVALUABLE outcomes

- A failed gate, or a difference between frozen and running inputs, stops the run: ENGINEERING_FAIL. A second attempt needs the human lead's decision, with everything observed in the first attempt listed.
- A resource cap reached: the stage is PAUSED, not failed. It resumes from its registry; completed cells are not recomputed and not re-evaluated.
- A failed cell is kept and not re-run. No re-run with changed settings.
- No registered seed is seen by a model before the freeze. No duration, threshold, load or arm changes after Stage R's output is written, except the caps and the cuts of section 11 before the freeze.
- NOT EVALUABLE cases: the anchor reference (row 2); a load where more than one draw has A6 below its floor (that load ends the readable grid and is not a failure of addressing); a cell type where the reference fails a validity condition in Stage R (section 5.2).
- If P10-S0's or P9-II's records are amended after the freeze, the study stops and returns to the human lead.

## 13. What this study cannot establish

- Anything about capacity, useful-capacity scaling, locality, transfer, continual addition of facts, efficiency, latency or storage.
- That addressing works under overload in general. One recipe (A5-D, μ = 1.0, calibrated at 0.5 facts per slot), one interface (W7, told the record length), one task, one backbone. A failure is a failure of the recipe as calibrated, not of learned addressing.
- That a pass relative to a degraded reference is useful: at such a load the store itself holds little.
- An unbiased first test of A5-D: its selection for P10-S0 followed its observed P9-II result.
- Why held-out templates fail, if they do. The descriptive measures of section 6.1 indicate whether the top-1 slot moves with the template; they are not a causal test.
- That the interface finds where to read: the memory is told the answer position.
- Anything about slot counts above 16,384, loads above 8, or natural language.
- That the durations are sufficient in general: the convergence rule is an operational plateau on two calibration draws, checked on the registered draws.
- A success or a failure of the ArborLM concept.

## 14. Engineering requirements carried from P10

| P10 failure | Requirement here |
|---|---|
| A status note committed to a frozen ADR lost P10-S1's first attempt | **The frozen-input set is exactly:** every file under `studies/p10is0/` (which holds `freeze/plan.json`, `freeze/durations.json`, `freeze/stage_caps.json`), `configs/p10is0_overload.toml`, the launch scripts, the imported files of `studies/p9ii`, `studies/p10s0`, `studies/p9i`, `studies/p9` by sha256, and the data manifests named in the plan. Identity is checked by file hash, not by the commit at HEAD. **This ADR and everything under `docs/` and `results/` are not frozen inputs.** Run-time notes go to `NOTES.md` in the git-ignored run directory, or to chat. No commit is made in the run's worktree during a registered stage |
| A stage could not resume | Every stage keeps a per-cell registry; a PAUSED stage continues; completed cells are skipped by record hash |
| The throughput stage listed a cell the frozen plan did not run | Every stage builds its item list from the frozen plan only. Stage 2 rehearses every stage end to end; stage 5 enumerates every stage against the frozen plan itself before Decision 2 |
| An unstated aggregation rule; a validity check the reference fails; a wrong descriptive section | Every combination rule is in sections 6.3–6.6 and 7. A6 passes through every condition in Stage R and a condition it fails is not applied (section 5.2). The analysis, including each descriptive section, is tested on synthetic registries with known answers; the auditor writes its own |
| A count gate stopped P10-S2 | Draws: generate until ten pass G1, within four reserves. Durations: train until the plateau rule is met, within the ceiling |
| One load, one length | Sections 4 and 5 |
| A macOS/Linux difference in exact ties | Platform of record named (section 10); bit-exact assertions on it only |
| CI cost | Checks run locally |

## 15. How the result feeds P10-I-S1's learned-address lane

P10-S1 omitted lane L because P10-S0 was not OVERLOAD-QUALIFIED. This ADR states what it provides; the lane's own rules belong to ADR-0024.

1. **Only Line Q licenses a lane.** A learned-address lane may use A5-D (μ = 1.0, this study's code hash, the duration rule of section 5) at a cell whose load is at most L_Q and whose slot count lies in 512–16,384. At any higher load the lane prints **OMITTED — ADDRESSING NOT QUALIFIED AT THIS LOAD (ADR-0023)**.
2. With outcome rows 1–3, 5 or L_Q = "none", no lane at any load. With row 6 and L_Q of 0.5 or 1, a lane at unloaded cells only.
3. Lines A and G license nothing by themselves. A lane restricted to trained templates where only Line A holds is not proposed (section 16, item 6).
4. **Timing.** A qualification recorded after P10-I-S1's freeze changes nothing in it (the P10 lesson, ADR-0020 section 9.2). Either P10-I-S1 freezes after this study's outcome is recomputed and accepted, or its lane is a separately frozen stage that waits for it. That choice is ADR-0024's and the human lead's.
5. This study uses a flat memory. A qualification here says nothing about addressing into the tree; ADR-0024 must say which store its lane reads.

## 16. Open choices reserved for the human lead, and questions for the reviewer

1. **Load grid and slot counts** (section 4.1). Recommended: loads 0.5, 1, 2, 4 at 8,192 facts and at 2,048 facts. Alternative: add 1.5 (not a power-of-two slot count), or a 32,768-fact series at higher cost.
2. **X8** (section 8). Recommended: keep it conditional on L_Q = 4. Alternatives: always run it (about 10 more hours) or leave it out.
3. **The convergence rule** (section 5): ladder, 0.01 step, two consecutive steps, T = 2·e\*, ceilings, and the blind output of Stage R. Recommended as written. The reviewer is asked whether the blind output is workable and whether 0.01 is too strict to be met under a degraded reference.
4. **The meaning of 0.90 under a degraded reference** (section 6.5). Recommended: keep the ratio at every load, with the mandatory reference-regime tag and the 0.50 floor. Alternative: read qualification only where A6 ≥ 0.90, which makes higher loads NOT EVALUABLE.
5. **Held-out templates as their own line** (sections 1, 6.4). Recommended: three lines, with Line Q the unchanged composite.
6. **Lane L** (section 15). Recommended: Line Q only. Alternative: allow a lane labelled TRAINED TEMPLATES ONLY where Line A holds.
7. **A0** in series M. Recommended: keep (it isolates the penalty). Dropping it saves about a third of series M.
8. **μ is not re-calibrated.** Recommended: keep μ = 1.0 so that the label refers to the qualified recipe. A μ search under overload would be a separate, later question.
9. **No dense or capacity baseline** in this study. Recommended: none; ADR-0024 owns it.
10. **Seed namespaces** across the six P10-I drafts (section 4.2): the lead reconciles them before any review confirms disjointness.
11. **Budget:** the hour cap, after the timing rehearsal, at Decision 2. When the run may occupy six cores.
12. Approval of this specification for implementation and rehearsals (Decision 1), and separately of the registered run (Decision 2). Any second attempt; merge; publication.

Points where the drafter is unsure, for the reviewer: whether the generator's panels and the read swap behave as specified at 512 and 1,024 slots (untested sizes for learned arms); whether condition 3's probe counts are the right collapse test when several facts share a slot by design; whether "both series" is too strict a combination for Line Q; whether one initialization seed per draw is enough; the Poisson estimate in section 6.2.

## 17. Approval record

None. No approval of this specification exists. Nothing is implemented, calibrated, frozen or run.

`Astra review: NOT_PERFORMED`.
