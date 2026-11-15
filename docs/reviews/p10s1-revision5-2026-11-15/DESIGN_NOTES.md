# P10-S1 revision 5 — design notes (2026-11-15 UTC)

- **Status: updated after the independent review (`review/REVIEW.md`, READY AFTER M1–M7) and the lead's rulings (`LEAD_RULINGS.md`). Written by a Claude Fable 5.2 drafting context for the lead. Not approved by anyone.** Specification work only: nothing was trained, no stage of `studies/p10s1` was run, no code or config was edited, nothing was downloaded. Astra review: NOT_PERFORMED.
- **Delegation.** The drafting context started no implementer, auditor or clerk task. The independent review was started by the lead; it reproduced `rev5_arithmetic.out` of the draft byte for byte and recomputed the calibration facts from raw counts. The figures added after the review (the 256-slot cell, the C_max table) have not been checked by anyone else.
- Spec: `docs/decisions/ADR-0021-p10-s1-useful-capacity-scaling.md`, revision 5 (§25 is its record). Revision 4 with §22–§24 is kept beside this file as `ADR-0021-rev4-with-s22-s24.md`.
- Arithmetic: `rev5_arithmetic.py` → `rev5_arithmetic.out` (standard library only; `python3 -I rev5_arithmetic.py`). It reads nothing and imports no study code. Its rates are copied by hand from `docs/reviews/p10s1-load-search-2026-11-15/audit_curves.out` (Part D) and `audit_costs.out`.
- Every number from the calibration is calibration, never a result. **Every U_L, every saturation level and every figure at 1,024 slots is an extrapolation.**

## 1. The registered rows

Seven grid cells, three sizes (1,024 / 4,096 / 16,384 slots), three fact counts; and one saturation-only cell, 2K/256, for F-OQ.

| Cell | Facts | Slots | Load | Role | Run length |
|---|---|---|---|---|---|
| 2K/256 (saturation only; F-OQ only; the lead's addition) | 2,048 | 256 | 8 | saturation cell; no step, no dense label, no seed block | U_L (search, 8K/1K's candidates) |
| 2K/1K | 2,048 | 1,024 | 2 | smaller cell of control step N1 | 6·U_P |
| 2K/4K | 2,048 | 4,096 | 0.5 | larger cell of N1 | 6·U_P |
| 8K/1K | 8,192 | 1,024 | 8 | **loaded**; smaller cell of C1; saturation cell | U_L (search) |
| 8K/4K | 8,192 | 4,096 | 2 | larger cell of C1; smaller cell of N2 | 6·U_P |
| 8K/16K | 8,192 | 16,384 | 0.5 | larger cell of N2 | 6·U_P |
| 32K/4K | 32,768 | 4,096 | 8 | **loaded**; smaller cell of C2; saturation cell | U_L (search) |
| 32K/16K | 32,768 | 16,384 | 2 | larger cell of C2 | 6·U_P |
| *128K/16K* (block S3; **not funded**, not run) | 131,072 | 16,384 | 8 | third saturation cell, F-OQ only | U_L (search) |

Steps: C1 8K/1K→8K/4K and N1 2K/1K→2K/4K in the transition 1K→4K; C2 32K/4K→32K/16K and N2 8K/4K→8K/16K in the transition 4K→16K.

Arms: F-OQ at all seven and at 2K/256 (8); T-OQ and H8 at all seven (14); D-OQ at 2K/4K, 8K/4K, 8K/16K, 32K/16K and at the loaded cells 8K/1K, 32K/4K (6); R2 at 2K/4K, 8K/16K, 32K/32K (3). **31 configurations per replicate, 155 cells over five replicates.** If the search finds no U_L for 2K/256 the cell is not run and the registry is 30 and 150.

**The trap, worked.** At 8,192 facts the 4,096-slot cell has load 2. In the calibration it reached 4.94–4.96 bits within 49,152 updates: the ceiling. So "8K/4K → 8K/16K" has no full smaller cell, and the second transition needs 4,096 slots at eight facts each = 32,768 facts. That is the long cell.

**Why control steps.** Without them each transition has only a step expected to be positive. N1 and N2 test H21-2 (no gain where the smaller cell is not loaded) and carry the efficiency line. N2 is revision 4's A1 and costs nothing new except 8K/16K, which lane L and the R2 reference also use.

## 2. Predicted saturation of the loaded cells (extrapolation)

The check fits loads 4 and 8 at 4,096 slots to about 17–18 bits per slot under the constant-ratio family. Carried to the loaded cells (`rev5_arithmetic.out` §3):

| Bits per slot | Bits per fact at load 8 | a_use |
|---|---|---|
| 16 | 2.00 | 0.59 |
| 17 | 2.12 | 0.61 |
| 18 | 2.25 | 0.64 |

- This is one number for all three sizes only if bits per slot do not depend on size. That is the hypothesis the saturation line tests, so it must not be used as a prediction of the ratio.
- Measured at 65,536 updates, not saturated: 32K/4K 1.89–1.94 bits per fact = 15.1–15.5 bits per slot; 16K/4K 16.3–16.5; 128K/16K 1.46–1.52 = 11.7–12.1; 64K/16K 14.0–14.2. The 16,384-slot cells are further from their plateau, so these figures do not show a lower capacity per slot at 16,384.
- At load 2 the same 16–18 bits per slot give more than 5 bits per fact, so 2K/1K is expected at the ceiling (not storage-limited). Nothing at 1,024 slots was ever run.
- All thresholds are well clear: the loaded limit is 4.0 bits and the plateau guard 0.473.

## 3. What each step can return, given what was seen

| Step | Smaller cell | Larger cell at the row's U_P | Expected verdict | Can a negative be reached? |
|---|---|---|---|---|
| C1 | 8K/1K, about 2.0–2.3 when full (extrapolation; never run) | 8K/4K: 4.37–4.54 at 8,192 (seen) | CAPACITY if the plateau holds (Δ_SAT about 2.1–2.5) | Not NO GAIN or REVERSED for F-OQ. It can be GAIN WITHIN BUDGET, NOT REPLICATED, DEPENDENCE_FAILED, MIXED |
| C2 | 32K/4K, about 1.9–2.3 when full (the check's extrapolation) | 32K/16K: 4.12–4.23 at 16,384 (seen); 1.96–2.61 at 8,192 | CAPACITY at U_P = 16,384 if the plateau holds (Δ_SAT about 1.8–2.3) | As C1. At U_P = 8,192 it would be GAIN WITHIN BUDGET ONLY |
| N1 | 2K/1K: expected at the ceiling (extrapolation) | 2K/4K: at least 0.90 at 8,192 (seen in the U_P check) | CEILING or FLAT, NOT LOADED | Yes, both ways: nothing at 1,024 slots was run |
| N2 | 8K/4K: 4.37–4.54 at 8,192; 4.94–4.96 at 49,152 (seen) | 8K/16K: 4.99–5.00 at 8,192 (seen) | Draw 1: CEILING. Draw 2: GAIN WITHIN BUDGET ONLY (Δ_MU 0.62, Δ_SAT 0.05). Likely class MIXED | Already largely seen; it favours no positive |

The positive on C1 and C2 is close to foregone for F-OQ. The ADR says so (§25.4) and does not let the milestone reading rest on it.

**Efficiency on N2, read by the lead from the calibration curves (Panel A; log₂ interpolation as §8.8 defines).** 8K/4K: draw 1 between 4,096 (2.989) and 8,192 (4.539) → u_T ≈ 4,116; draw 2 between 4,096 (1.843) and 8,192 (4.373) → ≈ 5,624. 8K/16K: draw 1 between 2,048 (1.979) and 4,096 (4.835) → ≈ 2,624; draw 2 between 2,048 (0.906) and 4,096 (4.679) → ≈ 3,009. Ratios 0.64 and 0.54, both above 0.5; the larger cell costs 1.6–1.7 times per update, so compute is not lower. Expected: SAME, or FASTER IN UPDATES ONLY in a replicate that crosses 0.5. One initialization seed, two draws.

## 4. The saturation line

- S(N) = F·i\*(saturation cell; U_L); b(N) = S(N)/N; ρ = S(4N)/S(N).
- PROPORTIONAL if ρ ≥ 3.0 on both panels, both cells full. 3.0 is H21-3's factor from revision 1. It means b(4N) ≥ 0.75·b(N).
- Precision: at 8,192 facts and a_use ≈ 0.6 the standard error of a_use is 0.0054, about 0.03 bits (1.5% of S); at 32,768 facts half that. ρ ≈ 4 is known to about ±0.07 per replicate. The plateau rule allows up to 0.10 bits of gain over the last doubling (about 5% of S) in either cell, which moves ρ by a few percent either way; both gains are printed.
- Two pairs: 256 → 1,024 (F-OQ only) and 1,024 → 4,096 (F-OQ, F-OQ-IVF, T-OQ, H8). F-OQ's class needs both.
- **1,024 → 4,096 is bounded on one side by what was seen (review M2).** 32K/4K held 1.89–1.94 bits per fact = 15.1–15.5 bits per slot at 65,536 updates, i\* does not fall, and every possible U_L there is at least 196,608. ρ < 3.0 needs i\*(8K/1K) > (4/3)·i\*(32K/4K): more than 2.52 bits per fact (20.1 bits per slot) if 32K/4K stops where it was seen, 2.67–3.00 (21.3–24.0) at the extrapolated 2.0–2.25. PROPORTIONAL is the likelier verdict. The negative is reachable.
- **256 → 1,024 has no observed side.** The reviewer checked the read at 256 random keys: 7.2 effective slots of the top 8 (7.5 at 1,024, 7.8 at 16,384); about 465 other facts share a slot with a given fact at load 8 (about 500 at larger sizes). T-OQ has one branch there and is undefined; F-OQ-IVF would read every key.
- **A confound that grows with the fact set (review M3).** The oracle codes have width 16. Share of facts with a neighbour above cosine 0.8: 0.10 at 2,048 facts, 0.38 at 8,192, 0.85 at 32,768. Each pair compares a fact set with one four times larger, so SUBPROPORTIONAL may be crowding of the oracle's codes, not the store. Separability is printed beside every ρ.
- What could make it fail: the output projection (32×32) and the gate are shared by all slots and do not grow; key interference among more keys; a plateau that is really a slow optimizer and stops at a lower level in the larger store.

## 5. Dense control

**Parameters.** F-OQ has 48N + 1,025 trainable parameters: 50,177 / 197,633 / 787,457 at 1,024 / 4,096 / 16,384 slots. D-OQ's width h is 1,024 / 4,033 / 16,071.

**Per parameter.** At 17.5 bits per slot the store holds 17.5/48 = 0.36 bits per parameter (extrapolation). A loaded cell's fact set is 5F bits = 40 bits per slot, 0.83 bits per parameter. A dense map that stores more than about 0.36 bits per parameter holds more than the store at the loaded cells. The lead does not know which way this goes; it is why D-OQ is run at the loaded cells and why that reading is binding.

**At the larger cells.** D-OQ at 8K/16K reached 0.998 at U_P = 8,192 (rate 0.01). F-OQ at 8K/4K reached 4.37–4.54 bits there. If D-OQ at 8K/4K (h = 4,033) is near the ceiling at 8,192 updates, d is about −0.4 to −0.6 and DENSE AHEAD fires in the MU reading. D-OQ has never been run at 8K/4K or 32K/16K, so this is a possibility, not a finding.

**Matched compute (analytic multiply-adds of a whole update, §22 M6; `rev5_arithmetic.out` §1–§2).** Backbone 57.5 M per update.

| Slots | F-OQ | T-OQ | H8 | D-OQ | D-OQ / F-OQ → grid | D-OQ / T-OQ → grid | D-OQ / H8 → grid |
|---|---|---|---|---|---|---|---|
| 1,024 | 62.4 M | 60.4 | 58.1 | 74.5 | 1.19 → 1.25 | 1.23 → 1.25 | 1.28 → 1.5 |
| 4,096 | 75.6 | 61.0 | 58.5 | 124.4 | 1.65 → 2.0 | 2.04 → 2.5 | 2.13 → 2.5 |
| 16,384 | 128.3 | 63.5 | 60.1 | 324.0 | 2.53 → 3.0 | 5.10 → 6.0 | 5.39 → 6.0 |

- The arm is the cheaper cell and is read at grid·U_P. The largest is 6·U_P, so every non-loaded cell runs 6·U_P at every size. That is the whole reason for the uniform multiplier.
- The T-OQ router's parameter count is approximated in the script; it moves the T-OQ figures by less than 0.1 M.
- Measured CPU-time multipliers exist only for F-OQ: D-OQ/F-OQ at 16,384 is 1.40–1.55; F-OQ 16,384/4,096 is 1.60–1.65. Both are below the analytic ones, so the analytic multiplier decides and the reading is established.
- **Disagreeing cost measures (review M7; the reviewer's rule, adopted).** `classes.mc_pair` now returns MC-AMBIGUOUS when the two measures disagree on which cell is costlier. Under revision 5 the pair is then read in the comparator's favour: the cell whose advantage would be claimed is read at U_P, the other at the smallest grid snapshot with multiplier ≥ the largest of r and 1/r over both measures; MC-AMBIGUOUS becomes an annotation. For T-OQ against D-OQ at 16,384 slots that means T-OQ at U_P against D-OQ at 6·U_P. The analytic step multipliers for T-OQ and H8 between sizes are 1.01–1.04, so the CPU direction decides those pairs. T-OQ has never been timed. H8's measured rate (0.0101–0.0110 at 16,384) is well under D-OQ's (0.0235–0.0245), so H8 is safe at 16,384.
- Between the two cells of a step the multipliers are 1.21 (F-OQ, 1K→4K) and 1.70 (F-OQ, 4K→16K), 1.01–1.04 for T-OQ and H8. The smaller cell of a loaded step runs U_L, far beyond any matched snapshot; MC-SHORT cannot occur there.

**Dense at saturation.** Read at equal updates U_L. Where D-OQ costs at least as much per update as the arm (true analytically at every size), D-OQ has had at least the arm's compute, and i\* cannot fall with updates, so "store ahead at equal updates" implies "store ahead at matched compute". A dense lead at equal updates may shrink at matched compute; it still blocks, as any single reading does in §8.5.

## 6. U_P and U_L

**U_P per row** (smallest of {8,192, 16,384, 32,768} with F-OQ ≥ 0.90 at the larger step cell and R2 ≥ 0.95). From the calibration curves: 8K/4K is at 4.37–4.54 bits at 8,192 (a_use about 0.94–0.955); 32K/16K is at 1.96–2.61 at 8,192 (about 0.6) and 4.12–4.23 at 16,384 (about 0.91–0.92). Expected U_P: 8,192, 8,192, 16,384. R2 at 32K/32K has never been run (R2 at 32K/64K passed at 8,192).

This rule changes what C2 can show, after the curves were seen. The ADR says so in §25.6; the lead accepted it with that declaration. The review (M4) added that the same rule makes the 0.80 floor of §8.4 near-automatic: 32K/16K was at a_use 0.910–0.923 at 16,384 against 0.585–0.697 at 8,192.

**U_L, extrapolations.**

| Cell | Basis | First pass | U_L (two consecutive passes) | Ceiling in the search |
|---|---|---|---|---|
| 32K/4K | the check, six families | 131,072–393,216 | most likely 262,144–393,216; range 196,608–524,288 | 524,288 |
| 8K/1K | no data. Time shift read off the curves at load 8: i = 0.970 is reached at 32,768 updates at 16,384 slots and about 13,970 at 4,096 (×2.35); i = 1.508 at 65,536 and about 26,560 (×2.47). Dividing 32K/4K's range by 2.4 | 55K–165K | about 82K–220K; central 131,072 | 262,144 |
| 128K/16K | the same shift upward (×2.4), or ×4 if time scales with facts | 315K–943K, or more | about 630K–940K; 1.05M–1.57M under ×4 | 1,048,576 |

The time shift assumes both stores saturate at the same bits per fact, which is the hypothesis under test. The 8K/1K and 128K/16K rows are an extrapolation of an extrapolation.

## 7. Hours

**Rates (measured on calibration draws; seconds per update; training wall / task).** F-OQ 0.0093 / 0.0099–0.0109 at 4,096; 0.0153–0.0154 / 0.0158–0.0175 at 16,384 with up to 32,768 facts, 0.0187 / 0.0259 with 131,072. H8 0.0075 / 0.0082 and 0.0101 / 0.0110. D-OQ 0.0235 / 0.0245 at 16,384. R2 0.0091 / 0.0101 and 0.0102 / 0.0113.

**Assumed, never measured:** T-OQ (1× and 2× F-OQ are both carried); everything at 1,024 slots (set to the 4,096-slot rate); D-OQ at 4,096 (half its 16,384 rate, 0.0118 / 0.0123) and at 1,024 (0.0091 / 0.0095); R2 at 32,768 rows (interpolated); the registered evaluation (1.5–2.5 hours: the calibration's evaluation seconds per snapshot × about 4.5 for the added ablations, H1/H2 and the index read × about 12 snapshots per cell). Revision 4 allowed 1.0 hour for evaluation; the check found the measured training 26–40% over that projection.

**Ranges.** Low end: training wall, T-OQ = F-OQ, evaluation 1.5. High end: task seconds, T-OQ = 2× F-OQ, evaluation 2.5.

| Item | Hours |
|---|---|
| Charged so far (ledger, measured) | 1.57 |
| New calibration, load search to the ceilings (70 runs) | 2.8–3.9 |
| Rehearsal | about 0.5 |
| Training, 155 cells, U_L 98,304 (2K/256), 131,072 and 393,216 | 8.2–11.1 |
| Seed block, draw 1 | 0.8–0.9 |
| Evaluation | 1.5–2.5 |
| Gates, timing, simulation, analysis, report | about 0.5 |
| Remaining | 11.0–15.0 |
| **C_need = charged + 2 × remaining** | **26.9–35.9** |

| U_L 8K/1K | U_L 32K/4K | C_need | After cut 2 / cut 3 (high end) | Against C_max = 36 |
|---|---|---|---|---|
| 98,304 | 196,608 | 22.5–29.9 | — | fits |
| 131,072 | 262,144 | 24.3–32.4 | — | fits |
| 131,072 | 393,216 | 26.9–35.9 | — | fits |
| 196,608 | 393,216 | 28.0–37.5 | 35.6 | fits after cut 2 |
| 262,144 | 524,288 | 31.8–42.5 | 40.2 / 39.7 | the highest corner returns (NOT STARTED: BUDGET) |

- The 256-slot cell: about 0.2 charged hours registered and two search runs of about 0.7 hours inside the calibration; about 0.7 hours of C_need.
- The high end counts evaluation twice (task seconds include the calibration's evaluations; review m10). The reviewer's own figures, with longest-first packing, are 21.0–26.8, 25.5–32.3 and 30.4–38.5 for the first, third and last rows, and 35.9 after cut 2 in the highest corner. Packing here is total/6.
- Neither set includes contention. At 1.25× it adds 6–8 hours. By the lead's ruling on M5, S1's timing preview, isolated timing, rehearsal and registered run start after P10-S0's last training stage.
- **The cap rule after the review (M5):** training is projected from isolated rates × c, where c is the largest ratio of six-worker to isolated training seconds per update over the calibration's configurations (never below 1.0); evaluation from rehearsed seconds per snapshot × registered snapshot counts; longest-first packing on six workers.

**The long cell 32K/4K alone** (F-OQ, T-OQ, H8, D-OQ; five replicates; charged hours): 1.7–2.4 at 196,608; 2.3–3.2 at 262,144; 3.5–4.8 at 393,216; 4.6–6.5 at 524,288. Doubled in C_need.

**Does it fit?** Under C_max = 36, on these figures, every case fits, at worst after cut 2, except the corner where T-OQ costs twice F-OQ and both loaded cells run to their ceilings. Under 32 hours it would fit only with T-OQ near F-OQ's cost or with the loaded cells stopping by about 262,144 updates. T-OQ's cost is the largest unknown (4.6–5.2 hours of C_need between 1× and 2×); the timing preview settles it in minutes.

**Cheapest sound alternatives, in the lead's order of preference** (hours of C_need saved at the central U_L):

1. Drop the draw-1 seed block: 1.6–1.7. Already cut 2; it is descriptive. Cost: no measure of initialization spread, which the check flagged as unsampled.
2. Drop D-OQ at 8K/16K: 0.5–0.6. Already cut 3.
3. Drop H8 at the two loaded cells: 1.8–2.0. Loses H8's capacity step and its bits per slot when full (the reference without key learning). H8 alone cannot give a positive outcome.
4. Drop the row of 2,048 facts: 1.9–2.0. Loses control step N1 and the efficiency line's first transition; EFFICIENCY_SUPPORTED becomes unreachable, so the efficiency line would have to become descriptive.
5. Lower the 32K/4K ceiling to 393,216: 0.2–0.4 off the calibration, and the worst case becomes about 28–38 in place of 31–42. Risk: the check's upper range for U_L is 524,288; a cell that needs it returns NOT LOADED.
6. Drop D-OQ at the loaded cells: 2.7–2.8 (4.0–4.1 at the ceilings). The lead would not: it is the one dense comparison whose answer is unknown.

Items 3–6 are not rules in the ADR. A need above 36 hours after the three cuts is NOT STARTED: BUDGET and returns to the human lead, who may choose among them.

**Block S3** (128K/16K, F-OQ only, five replicates): one run is 2.7–3.8 hours at 524,288 updates, 4.1–5.7 at 786,432, 5.5–7.5 at 1,048,576; its search runs two draws to 1,048,576. C_need with it: 36–54 hours. It is not funded (the lead's ruling 2). The cheaper third size, 2,048 facts in 256 slots for F-OQ only, is in the revision as cell 2K/256.

**The cap rule.** cap = ceil(C_need), recorded by the lead only if ≤ C_max = 36 hours, which the lead set under the Addendum's delegation and reports to the human lead.

## 8. The new calibration, in short

| Item | Runs | What it fixes | If it fails |
|---|---|---|---|
| 0a timing preview | time only | projections and item caps; T-OQ and 1,024-slot rates for the first time | — |
| 0b load search: F-OQ, T-OQ at 8K/1K (to 262,144) and 32K/4K (to 524,288), F-OQ at 2K/256 (to 262,144), two draws, once each | 10 | U_L per loaded cell: two consecutive candidates pass on all four views | F-OQ has no U_L at a loaded cell → NOT LOADED, return to the human lead (not automated; review M1); T-OQ alone has none → recorded, study proceeds; 2K/256 has none → '256 NOT MEASURED', cell not run, no return |
| 1 row U_P | 12 | U_P per row | no value qualifies → return |
| 2 H8 reported | 8 | UNDERTRAINED-AT-U_P annotations | gates nothing |
| 3 dense rate, five rates × four units | 40 | D-OQ's rate per unit | 0.1 best by more than 0.02 at the readout, or all diverged → return; 0.1 chosen only by the tie walk → taken, EDGE BY TIE-WALK |

- The plateau artefact is closed in §8.2 itself (i\* ≥ 0.473 at half the run length), so the registered verdicts and the search use one definition.
- Runs go once to their ceilings and the rule is applied to the finished record. This costs about 0.5–0.8 hours more than a staged search and needs no resume code and no decision while runs are in progress.
- Calibration draw 2 uses initialization seed 2193, so "all four views" samples two initializations.
- Wall time 2.7–3.8 hours plus the preview (`rev5_arithmetic.out` §7). 70 runs.
- An item's cap is twice its projected wall time at six workers; a run still running at the cap is stopped, kept, and has no U_L (review m5).

## 9. The draft's questions: all ruled

The twelve questions of the draft are ruled by the lead; the table is §25.8 of the ADR and the record is `LEAD_RULINGS.md`. Two things go to the human lead as reports, not questions: C_max = 36 hours and the 256-slot cell.

## 10. What the lead could not settle

- T-OQ's cost per update, the cost of anything at 1,024 slots, D-OQ's cost below 16,384 slots, and the cost of the registered evaluation. All are assumptions until the timing preview and the rehearsal.
- Every U_L. For 8K/1K there is no data at all.
- Whether 2K/1K reaches the ceiling, whether H8 is loaded at the loaded cells, whether T-OQ plateaus where F-OQ does.
- Whether a dense rate chosen at 65,536 updates is the best rate at U_L. If it is not, STORE HOLDS MORE AT SATURATION is weaker than it reads; DENSE HOLDS MORE is unaffected.
- Whether T-OQ, the index read and gate G4 behave at 1,024 slots (four branches, four centroids). The formulas are defined; no code was run to check.
- Whether initialization spread makes the "all 5" plateau condition fail. The seed block measures it afterwards and cannot inform U_L.
- Sections 17–21 of the ADR still name revision 4's cells; they are historical and were left as they are. §18 lists revision 2–4's choices; revision 5's are in §25.5.

## 11. Code and config changes

See `IMPLEMENTER_BRIEF.md` beside this file. It replaces the list that stood here in the draft.
