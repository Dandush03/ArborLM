# ADR-0021 (P10-S1) revision 2: auditor confirmation review

- **Reviewer:** Claude Opus 5.5 (`claude-opus-5-5`), the same specification auditor who wrote `REVIEW.md` in this folder, in a context separate from the integration work. No git or GitHub action, no tracked-file edit, no commit, no download. **Astra review: NOT_PERFORMED. This is not Astra validation and not a human approval.**
- **Object:** `ADR-0021-p10-s1-useful-capacity-scaling.rev2.md` (682 lines; read in full), against `REVIEW.md`, revision 1, the coordinator's twelve rulings (relayed in my task), `ADR-0020-p10-s0-addressing-qualification.rev2.md` (§7, §8.7, §9, §17; cross-references only) and `ADR-0022 … rev4.md` §9 (seed ranges only).
- **Ran:** `k1_confirm_arithmetic.py` → `outputs/k1_confirm_arithmetic.txt` (stdlib arithmetic: Fano inverses, reachability, budget slack). Command, from this folder: `uv run --project <worktree> --locked python -I k1_confirm_arithmetic.py`. Nothing else was run; no model, no ArborLM seed.
- **Discrepancy in the request:** the coordinator refers to twelve conflicts in §19; revision 2's §19 has **eleven** items. The ruling "12: accepted as the drafter did it" has no object. I treat it as void; if a twelfth item exists elsewhere, it is unreviewed.

## Verdict: **READY AFTER LISTED TEXT EDITS**

Every blocker and major of `REVIEW.md` is applied, B2 and M5 under rulings I accept. Seven findings remain (K1–K7 below), none needing a redesign or a new cell. Four of them would make a label wrong or the plan unexecutable as written: the load calibration reads its plateau at a different update count from the registered run (K1); the rule table can declare the 4,096-slot rows loaded when neither registered 4,096-slot cell is (K1); cut 2 can remove the only loaded route to a positive (K3); and the efficiency line can print FASTER or SLOWER from grid rounding and censoring (K4). The texts in §3 are complete and paste-ready. If they are applied verbatim (bracketed numbers may be changed by the lead before calibration without re-review), the specification is ready for the lead's self-approval under the delegation in §15. If they are not applied, it is NOT READY.

## 1. Status of REVIEW.md findings

| Finding | Status in rev 2 | Note |
|---|---|---|
| B1 vacuous negative | APPLIED | §8.7 row 4 and the synthetic-record tests of §10.2 |
| B2 dense gate | APPLIED WITH RULING | three readings; DENSE AHEAD at −0.25 blocks every arm; BEATS DENSE at r ≥ 1.10 (ADR-0017's standard). §6.2 still says BEATS DENSE uses "at least 4 of 5"; ruling 2 says all 5 → K2 |
| B3 D-OQ | APPLIED | bias, conventional init, 49h + 1 match, lr grid {0.001, 0.003, 0.01} per slot count |
| B4 load | APPLIED, DEFECTS | plateau read at 65,536 updates against registered runs of 49,152 / 32,768; per-cell loadedness missing; three thresholds → K1 |
| M1 iso cells | APPLIED | |
| M2 plateau | APPLIED | §8.2 row 4 lists "plateaued" but not "loaded" → K1 (ruling 5) |
| M3 negatives | APPLIED | renames accepted |
| M4 IVF | APPLIED | SUBLINEAR for F-OQ-IVF must be judged on measured W → K5 |
| M5 cuts | APPLIED WITH RULING | cut 2 can remove the only loaded route → K3 |
| M6 seed block | APPLIED | draw-1 block is not in the cut list → K6 |
| M7 H8 | APPLIED | |
| M8 reading | APPLIED | ruling 1 text → K2; "within registered run lengths" missing from the printed label → K2 |
| M9 Study B | APPLIED | |
| M10 movement | APPLIED | |
| M11 governance | APPLIED | §15 quotations still unchecked against the record (the draft says so); the lead must check before approving |
| m1–m17 | APPLIED | m6: test range must be 921001–921999 and S2 named as 220001–228999 / 229001–229999 → K7 |

## 2. The coordinator's rulings, judged

| Ruling | Judgment |
|---|---|
| 1 Milestone reading | **Agree.** Text K2(c). Adds: F-OQ-IVF's SUBLINEAR read from measured W (K5). |
| 2 DENSE AHEAD first; BEATS DENSE in all 5 | **Agree.** Text K2(a). Add a printed dense accuracy so a BEATS DENSE against a control at chance is visible. |
| 3 Drafter's load rule | **Agree in structure, not as written.** Three defects: (i) "plateaued" is judged at 65,536 updates, but registered smaller cells run 6·U_P = 49,152 (4,096 slots) and 4·U_P = 32,768 (16,384 slots), so calibration can call a load "loaded" that the run cannot show; (ii) "L\* at 4,096 ≤ 8 → no change" assumes loadedness is monotone in load, but heavier loads learn more slowly: on the stand-in load 4 plateaus near ceiling while load 8 is still rising, so L\* = 4 would leave both registered 4,096-slot cells (loads 2 and 8) unloaded; (iii) a_use ≤ 0.80 differs from the registered "loaded". Text K1. |
| 4 No overload row without R2 | **Agree.** At 16,384 slots L\* = 4 gives 65,536 facts, and R2 exists at 65,536 slots (one fact per slot); L\* = 8 gives 131,072 facts, R2 undefined → returned. Text K1. |
| 5 One threshold i\* ≤ 4.0 | **Agree; no rule becomes unreachable.** A loaded smaller cell at i\* = 4.0 with the maximal plateau slope 0.10 needs the larger cell at ≥ 4.70 bits (a_use 0.974) for CAPACITY; that is below 5 (`k1`). NULL, NOT LOADED and the calibration rule stay reachable. i = 4.0 ↔ a_use 0.8956. Text K1. |
| 6 m7 via the row's reference cell | Agree. |
| 7 Second cut against M5 | Superseded by ruling 8; see K3. |
| 8 Cut 2 never weakens the dense gate | **Agree, with one condition:** cut 2 may not remove the dense cell of a step that the load calibration predicts is the loaded route. On the stand-in the loaded 4,096-slot cell is 32K/4K (B1), whose larger cell 32K/16K is exactly what cut 2 removes; CAPACITY_SUPPORTED would then be unreachable. Text K3. |
| 9 Efficiency line | **Reviewed; needs corrections.** Text K4. |
| 10 D7 dropped | Agree. "Strong dense alternatives" is met by one dense family with a three-rate grid; state that only one dense family is run (in K2(d)). |
| 11 Quotations | Agree; they must be checked against the chat record before §15 records any approval. |
| 12 | No §19 item 12 exists (see header). |

### Efficiency line (ruling 9), reviewed as a new section

- **Passable by a trivial or artificial difference?** Yes, in three ways.
  1. *Grid rounding.* u_T is the first snapshot on a doubling grid. A larger memory reaching 3.0 bits at 0.99·U_P against the smaller at 1.01·U_P is recorded as U_P against 2·U_P: "half the updates". FASTER in all 5 replicates is then possible for a 2% difference that sits on a grid boundary. Fix: interpolate u_T in log-updates.
  2. *Censoring.* u_T = ∞ when not reached within the cell's own run. Runs differ by slot count (6, 4, 2·U_P). "u_T(4N) ≥ 2·u_T(N)" with u_T(4N) = ∞ prints SLOWER whenever the larger cell's shorter run ended first, even if it would have reached i_T sooner than 2·u_T(N). Fix: censored values are bounds, and a verdict is printed only when the bound decides it.
  3. *Dependence.* u_T requires DEP at the snapshot, but a DEP failure only makes u_T = ∞, which then prints SLOWER (or FASTER for the other cell). Fix: a DEPENDENCE_FAILED verdict.
- **Capacity mislabelled as efficiency:** when the smaller cell never reaches i_T (it may be loaded below 3 bits), FASTER means "the larger reached it, the smaller did not"; the efficiency text "learned the same facts sooner" is then wrong. Fix: a separate verdict REACHED ONLY BY THE LARGER, which counts as FASTER for the class but is printed.
- **M10 consistency:** the ratio is printed, as required. Add the annotation OPTIMIZER-ASSISTED when the larger cell's share of value-row movement on updates without gradient exceeds the smaller's by a factor of [1.5], so a FASTER driven by AdamW's √K effect is visible on the label. No class change (consistent with M10).
- The 3.0-bit level, the 0.8 compute ratio and DENSE FASTER blocking: no defect found. At the 16K→64K step the compute condition needs at least about 3.2× fewer updates on P9-I's per-update costs; that is a consequence, not a defect.

## 3. Remaining findings with paste-ready text

### K1 (MAJOR) — Load rule: read at the registered run length, per registered cell, one threshold

Replace §8.2's definitions block lines "Saturated below the ceiling" and "Loaded" with:

> - **Loaded** (a smaller cell): plateaued and i\*(N; U_run) ≤ 4.0 bits per fact (a_use ≤ about 0.896) *(lead's choice)*. This one threshold is used for CAPACITY (row 4), NULL (row 8), FLAT, NOT LOADED (row 9) and the load calibration (§10.1 item 0).

In §8.2 row 4 (CAPACITY), replace "the smaller cell has plateaued" with "**the smaller cell is loaded**".

Replace §10.1 item 0 (both paragraphs and the table) with:

> **0. Load calibration.** F-OQ only, on both calibration draws, at 4,096 slots with 8,192 / 16,384 / 32,768 / 65,536 facts (loads 2, 4, 8, 16), and at 16,384 slots with 32,768 / 65,536 / 131,072 facts (loads 2, 4, 8), run to 65,536 updates with snapshots on the doubling grid and at the registered U_run/2 and U_run of the slot count (24,576 and 49,152 at 4,096 slots; 16,384 and 32,768 at 16,384 slots). 14 runs, about 3 CPU-hours. A load is **loaded at a slot count** if, on both draws and both calibration panels, the cell is loaded by the definition of §8.2 **read at the registered U_run of that slot count** (not at 65,536 updates). The 65,536-update snapshots are reported for information and enter no rule. A load is judged on its own cell; loadedness is not assumed to carry from one load to another.
>
> **Rule fixed now** (registered smaller cells: 8K/4K and 32K/4K at 4,096 slots; 8K/16K and 32K/16K at 16,384 slots):
>
> | Measured | Consequence |
> |---|---|
> | At 4,096 slots, load 2 or load 8 is loaded | the 4K→16K transition is tested by the registered rows; no change |
> | At 4,096 slots, neither load 2 nor load 8 is loaded | no registered 4,096-slot cell is predicted loaded: the work returns to the human lead before the freeze |
> | At 16,384 slots, load 2 is loaded | the row of 32,768 facts tests the 16K→64K transition; the grid of §5.1 stands |
> | At 16,384 slots, load 2 is not loaded and load 4 is loaded | the row that tests the 16K→64K transition becomes 65,536 facts at 16,384 and 65,536 slots, for F-OQ, T-OQ, H8, D-OQ and R2 (R2 at 65,536 slots, one fact per slot, is its REF cell). Its U_P is the smallest of {8,192, 16,384, 32,768} *(lead's choice)* at which F-OQ ≥ 0.90 and R2 ≥ 0.95 at its larger cell on both draws and panels, read in a calibration of that cell (2 arms × 2 draws, added to the calibration count); its run lengths are 4·U_P and 2·U_P of that U_P. The row of 32,768 facts keeps its cells and only its 4K→16K step. If the headroom rule of §10.3 does not hold with this row after the allowed cuts, the work returns to the human lead with the row's cost |
> | At 16,384 slots, only load 8 is loaded, or none | the 16K→64K transition cannot be loaded with an R2 reference within the budget (131,072 facts exceed 65,536 slots): the work returns to the human lead before the freeze. The lead never runs a row without R2 |
>
> The lead does not improvise a row. When the work returns, the human lead may stop, fund a row, or direct that S1 run as it is, with the capacity line fixed in the freeze record as CAPACITY NOT TESTED — NO LOADED CELL WITHIN BUDGET for the transition concerned; the efficiency line is unaffected. A prediction of loadedness from calibration does not make a registered cell loaded: the run judges every cell on its own snapshots.

In §19, items 3–5: replace by "Resolved by the confirmation review, K1."

### K2 (MAJOR) — Dense labels and the milestone reading (rulings 1 and 2)

(a) Replace the label table of §8.5 with:

> | Order | Label | Rule |
> |---|---|---|
> | 1 | **DENSE AHEAD** | d ≤ −0.25 *(lead's choice)* in at least 4 replicates, in any one reading (MU, MC, D-BEST), at any such cell. Takes precedence over every other label |
> | 2 | **BEATS DENSE** | r ≥ 1.10 in **all 5** replicates, under MU and under MC, on both panels, at every such cell (ADR-0017's standard). r with a zero denominator counts as ≥ 1.10 and the label is then printed **BEATS DENSE (DENSE AT CHANCE AT cell)** |
> | 3 | **DENSE MATCHES** | otherwise; printed as "a dense map with the same parameters, input and compute retained as much; the memory did it with W_arm / W_dense of the counted work" |
>
> Every dense label is printed with D-OQ's a_use at each such cell in each reading.

(b) In §6.2 "Statistical meaning", replace the last sentence with: "'At least 4 of 5' is used for negatives, ceilings and DENSE AHEAD. Every positive condition, BEATS DENSE included, needs all 5."

(c) Replace the "Reading for milestone question 1" paragraph of §8.7 with:

> **Reading for milestone question 1, fixed now.** S1 tests the storage half of question 1 under oracle addressing, on the capacity line only.
> - **"Storage half supported, as a necessary condition"** only if the capacity outcome is CAPACITY-POSITIVE for an arm whose counted work is SUBLINEAR (T-OQ, or F-OQ-IVF by §7.4 rule 4), that arm is not DENSE AHEAD, and the hierarchy label comparing T-OQ with F-OQ-IVF (§8.5) is printed with it. It means: given the identity of the fact, this store retained more trained random facts as it grew, within the registered run lengths, at bounded counted work, and at least as well as a dense map of equal size, input and compute. It says nothing about addressing by the model, about use of the store by a language model, or about useful capability beyond recall of the trained facts.
> - **"Capacity shown; sublinear active work not shown"** if CAPACITY-POSITIVE holds only for exhaustive F-OQ.
> - **"Storage half not supported for this store, backbone, task and budget"** if CAPACITY-NEGATIVE.
> - **"Not tested"** or **"not established"** for CAPACITY NOT TESTED or CAPACITY-INCONCLUSIVE.
> - Every reading is printed with S0's status line of K7(c).

(d) Replace the "Printed label" line of §8.7 with: "**Printed label:** CAPACITY-POSITIVE [STORE ONLY; ORACLE-ADDRESSED; WITHIN REGISTERED RUN LENGTHS; arm(s); BEATS DENSE or DENSE MATCHES, with D-OQ's a_use; active-work label; hierarchy label; conventional-retrieval label; S0 status (K7(c)); learned-address lane status]." Add to §12: "That a dense architecture other than D-OQ would not do as well: one dense family is run, with a three-rate grid."

In §19 items 1–2: "Resolved by the confirmation review, K2."

### K3 (MAJOR) — Cut 2 may remove the only loaded route

Replace §10.3 cut list with:

> **Cuts, fixed now, in this order, until the headroom rule holds; nothing else may be cut:**
> 1. The seed block on draw 2 (added only if it fits in the first place).
> 2. The seed block on draw 1 *(lead's choice of order; it is descriptive and enters no rule)*.
> 3. D-OQ at a larger cell (among 8K/64K and 32K/16K) **only if the load calibration predicted that step's smaller cell not loaded** (8K/16K for A2; 32K/4K for B1). A D-OQ cell at the larger cell of a step whose smaller cell was predicted loaded is never cut. A step whose D-OQ cell is cut prints DENSE NOT READ and cannot support CAPACITY_SUPPORTED.
> 4. If the rule still does not hold, the work stops and returns to the human lead.

In §8.5, replace "(only after cut 2 of §10.3)" with "(only after cut 3 of §10.3)". In §19 item 7: "Resolved by ruling 8 and the confirmation review, K3."

### K4 (MAJOR) — Efficiency line corrections

Replace §8.8 from "**Level.**" through the step-verdict table and the sentence after it with:

> **Level.** i_T = 3.0 bits per fact (a_use about 0.758) *(lead's choice)*. At each snapshot s of a cell, the snapshot **qualifies** if i ≥ i_T on both panels and DEP passes. s_hit is the first qualifying snapshot within the cell's run, s_prev the snapshot before it. **u_T** is found by linear interpolation of the minimum of the two panels' i against log₂(updates) between s_prev and s_hit; if s_hit is the first snapshot, u_T is **left-censored** in (0, s_hit]; if no snapshot qualifies, u_T is **right-censored** above the cell's run length U_run. c_T is u_T times the cell's cost per update, in each of the two cost measures of §5.4 (bounds carry over).
>
> **Step verdict in one replicate (first match wins).** A condition on a censored value holds only if it holds for every value the bound allows.
>
> | Order | Verdict | Rule |
> |---|---|---|
> | 1 | NOT_EVALUATED | REF fails for the row, or LEAKAGE |
> | 2 | DEPENDENCE_FAILED | in either cell, some snapshot has i ≥ i_T on both panels with DEP failing, and no earlier snapshot qualifies |
> | 3 | NOT_ASSESSED | both cells right-censored, or the conditions of rows 4–7 are all undecidable from the bounds |
> | 4 | REACHED ONLY BY THE LARGER | the smaller cell is right-censored, and u_T(4N) ≤ U_run(N)/2 and c_T(4N) ≤ 0.8 · cost(N; U_run(N)) in both cost measures |
> | 5 | FASTER | u_T(4N) ≤ u_T(N)/2, and c_T(4N) ≤ 0.8 · c_T(N) in both cost measures *(lead's choice)* |
> | 6 | FASTER IN UPDATES ONLY | u_T(4N) ≤ u_T(N)/2, not row 5 |
> | 7 | SLOWER | u_T(4N) ≥ 2 · u_T(N) (with the larger cell right-censored, only if U_run(4N) ≥ 2 · u_T(N)) |
> | 8 | SAME | otherwise, with both u_T known |
>
> Every verdict is printed with the row-movement ratio of §7.3 and, where the larger cell's share of value-row movement on updates without gradient exceeds the smaller cell's by more than [1.5] times, the annotation **OPTIMIZER-ASSISTED**. No class depends on either.

In the step-class line, insert after NOT_EVALUATED: "DEPENDENCE_FAILED (at least 2)", and replace "FASTER STEP (FASTER in all 5)" with "FASTER STEP (FASTER or REACHED ONLY BY THE LARGER in all 5; the number of each is printed)". Replace the closing sentence of §8.8 with: "EFFICIENCY-POSITIVE says that a larger store reached a fixed level of useful information in fewer updates and less compute; where the smaller store never reached it within its run, the label says so (REACHED ONLY BY THE LARGER), and that is not a capacity statement. It does not enter the milestone reading." In the arm-class line, add DEPENDENCE_FAILED (any step) after NOT_EVALUATED. In §19 item 8: "Reviewed by the confirmation review, K4."

### K5 (minor) — F-OQ-IVF's SUBLINEAR from measured work

Add §7.4 rule 4: "**F-OQ-IVF's W is measured, not analytic.** SUBLINEAR for F-OQ-IVF is judged on the mean measured W per query on Panel A at both cells of the step, in every replicate; its 99th percentile is printed beside it."

### K6 (minor) — Budget honesty

Replace the bullet "On this projection: …" in §10.3 with:

> - On this projection the draw-1 seed block needs 1.4 + 2 × 5.3 = **12.0 hours: zero slack.** The projection rests on unmeasured items: T-OQ at twice F-OQ (the largest item; at 2.5× the twofold rule needs about 0.8 hours more), the new D-OQ, the index builds and the evaluation hour (each 20% over adds about 0.4 hours under the twofold rule). **It is likely that the rehearsal measures more than the projection.** The cuts of this section then apply in order: the draw-1 seed block saves about 0.7 hours under the twofold rule, the permitted D-OQ cut about 0.6. Beyond that the work returns to the human lead, with the measured shortfall and the options: raise the cap, or shorten the run lengths (which changes the registered design and needs a re-review). The lead does not choose between them.

### K7 (minor) — Cross-references to ADR-0020 and the seed ranges

(a) §6.3: replace "Unit tests: **921001–929999**" with "Unit tests: **921001–921999**". In G9's list replace "S2 (220001–229999)" with "S2 (220001–228999, tests 229001–229999)". (ADR-0022 rev 4 still declares 220001–229999; that is S2's correction to make, ADR-0020 §9.3.)

(b) §5.6 items 1, 2 and 4, replaced, to match ADR-0020 §8.7 and §9.1:

> 1. Lane L exists only if, before S1's freeze, S0 (ADR-0020) has the outcome **ADDRESSING-QUALIFIED (4,096 AND 16,384)**, with Q1 recomputed by the auditor from raw records (ADR-0020 §9.1).
> 2. The lane prints **OMITTED — QUALIFIED AT 4,096 ONLY**; **OMITTED — NOT OVERLOAD-QUALIFIED** (qualified candidate not OVERLOAD-QUALIFIED); **OMITTED — SUPERVISED ARM HAS NO 8K/4K CELL** (candidate A1 or A2); or **OMITTED — no interface qualified before the freeze** (ADDRESSING-NOT-QUALIFIED, INCONCLUSIVE, ENGINEERING_FAIL, INCOMPLETE, NOT STARTED, or nothing recorded at the freeze).
> 4. If it runs: arm F-LA, the candidate exactly as S0 froze it (S0's code hash; P9-II's calibrated value from the arm-selection record; no tuning), at 2K/4K, 8K/4K and 8K/16K, five replicates, each cell run for 4·F updates (8,192 at 2K/4K; 32,768 at 8K/4K and 8K/16K), with F-OQ read at the same update count. S0's cell-success rule is applied at all three cells. No 65,536-slot cell. 15 cells.

In §6.1 replace the lane row with "Lane L (only if qualified and it fits) | F-LA × 3 cells × 5 | +15". Add to §5.6: "In the expected timeline (ADR-0020 §9.2) S1 freezes before S0's Q1 is recomputed, so the lane is expected to be omitted; 'learned addressing evaluated separately if qualified' is then met only by a later study that needs the human lead's review."

(c) ADR-0020 §17 item 0 has a question pending with the human lead that bears on S1's labels. Add to §13 as item 5, and to every printed outcome:

> 5. **Pending human answer (ADR-0020 §17 item 0).** If S0 qualifies no interface, every S1 outcome and reading is printed with "ORACLE-ADDRESSED — NO LEARNED ADDRESSING QUALIFIED (ADR-0020)" and is never summarised as "ArborLM's capacity scales". If the human lead answers that S1's capacity labels are withheld in that case, S1 follows that answer; it is recorded verbatim in §15 and needs no other change to this specification. Until S0 has an outcome, the S0 status printed is "S0 NOT YET DECIDED".

## 4. Checks the coordinator asked for

- **Recount:** 30 configurations × 5 = **150** registered cells; calibration 14 + 12 + 6 + 12 = **44** runs (with K1's overload row, +4); seed block **14** (draw 1) or **28** (draws 1 and 2); lane L **15** with K7(b). Confirmed.
- **Headroom:** 1.4 + 2 × (3.57 + 0.33 + 1.0 + 0.4) = **12.0 h**, zero slack (`k1`); 12.6 h with both seed blocks. Training per replicate 15,440 s matches my `c4b` variant (15,437 s). The plan's original text was honest in §19 item 9 but not in §10.3; K6 moves it into the rule and adds what happens next.
- **Can CAPACITY-POSITIVE be printed for faster learning only?** Within the registered run lengths, no: CAPACITY needs a loaded smaller cell (plateaued at ≤ 0.10 bits per doubling and ≤ 4.0 bits), Δ_SAT ≥ 0.5 against the smaller cell's best snapshot, and a gap that survives two further doublings at its last rate. A smaller memory that is still learning slowly beyond that horizon could close the gap later; that residual risk is why K2(d) puts WITHIN REGISTERED RUN LENGTHS in the label.
- **Table precedence:** §8.2, §8.3, §8.4, §8.5 (after K2), §8.7 and §8.8 (after K4) have no overlap or unreachable row that I found. §8.4 row 4 (ONE TRANSITION) precedes row 5 (NOT_TESTED_BY_LOAD), so an arm with one capacity step and one unloaded transition is INCONCLUSIVE "ONE TRANSITION ONLY", not NOT TESTED; that is acceptable and the reason is printed.
- **Human lead's S1 requirements:** all met after K1–K7. Oracle addressing and no autonomous claim (§3, §12, K7(c)); Study A sizes, recall, efficiency line, robustness, held-out (§5, §7.2, §8); parameter control and a strong dense (§5.3, K2); Study B with flat, hierarchical, IVF sparse retrieval, exact-address references and dense (§5.5, §8.6); the three regimes separately (§5.4); dependence, ablations, utilization, separability, routing, throughput, traffic, the SSD sentence (§7); gates and CAPACITY-POSITIVE independent of TRANSFER- and SYSTEM-POSITIVE (§8.7); M5 Max, twofold headroom, training apart from timing, no cloud (§10.3, K6); learned addressing separately if qualified (§5.6, K7(b)). One weak point is stated rather than fixed: only one dense family is run (K2(d)).
- **Seeds:** S1 210001–219999 and init 2101–2105, 2111, 2112, 2121, 2122, 2191, 2192 are disjoint from S0 (200001–209999; 2001–2002, 2091–2092; tests 920001–920999), P9-II (190001–191599; tests 910001–919999) and S2 (220001–228999; tests 229001–229999). The derived generator seeds (init + 1000·k) end in 101–105, 111, 112, 121, 122, 191, 192 modulo 1000, against 001, 002, 091, 092 (S0), 891, 901, 902 (P9-II), 701, 702, 791, 792, 801, 802 (P9, P9-I): no collision. `REVIEW.md`'s scan (`s9c`) found no use of S1's ranges.

## 5. Files

`k1_confirm_arithmetic.py` → `outputs/k1_confirm_arithmetic.txt`, in this folder. Everything else cited is in `REVIEW.md` §8.
