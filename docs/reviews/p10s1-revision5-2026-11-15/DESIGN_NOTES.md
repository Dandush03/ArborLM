# P10-S1 revision 5 — design notes (2026-11-15 UTC)

- **Status: DRAFT by the lead (Claude Fable 5.2). Not reviewed, not approved.** Specification work only: nothing was trained, no stage of `studies/p10s1` was run, no code or config was edited, nothing was downloaded. Astra review: NOT_PERFORMED.
- **No delegation happened.** The lead read the records and wrote this alone; no implementer, auditor or clerk task was started. The arithmetic here has not been checked by anyone else.
- Spec: `docs/decisions/ADR-0021-p10-s1-useful-capacity-scaling.md`, revision 5 (§25 is its record). Revision 4 with §22–§24 is kept beside this file as `ADR-0021-rev4-with-s22-s24.md`.
- Arithmetic: `rev5_arithmetic.py` → `rev5_arithmetic.out` (standard library only; `python3 -I rev5_arithmetic.py`). It reads nothing and imports no study code. Its rates are copied by hand from `docs/reviews/p10s1-load-search-2026-11-15/audit_curves.out` (Part D) and `audit_costs.out`.
- Every number from the calibration is calibration, never a result. **Every U_L, every saturation level and every figure at 1,024 slots is an extrapolation.**

## 1. The registered rows

Seven cells, three sizes (1,024 / 4,096 / 16,384 slots), three fact counts.

| Cell | Facts | Slots | Load | Role | Run length |
|---|---|---|---|---|---|
| 2K/1K | 2,048 | 1,024 | 2 | smaller cell of control step N1 | 6·U_P |
| 2K/4K | 2,048 | 4,096 | 0.5 | larger cell of N1 | 6·U_P |
| 8K/1K | 8,192 | 1,024 | 8 | **loaded**; smaller cell of C1; saturation cell | U_L (search) |
| 8K/4K | 8,192 | 4,096 | 2 | larger cell of C1; smaller cell of N2 | 6·U_P |
| 8K/16K | 8,192 | 16,384 | 0.5 | larger cell of N2 | 6·U_P |
| 32K/4K | 32,768 | 4,096 | 8 | **loaded**; smaller cell of C2; saturation cell | U_L (search) |
| 32K/16K | 32,768 | 16,384 | 2 | larger cell of C2 | 6·U_P |
| *128K/16K* (block S3, off unless funded) | 131,072 | 16,384 | 8 | third saturation cell, F-OQ only | U_L (search) |

Steps: C1 8K/1K→8K/4K and N1 2K/1K→2K/4K in the transition 1K→4K; C2 32K/4K→32K/16K and N2 8K/4K→8K/16K in the transition 4K→16K.

Arms: F-OQ, T-OQ, H8 at all seven (21); D-OQ at 2K/4K, 8K/4K, 8K/16K, 32K/16K and at the loaded cells 8K/1K, 32K/4K (6); R2 at 2K/4K, 8K/16K, 32K/32K (3). 30 configurations per replicate, 150 cells over five replicates. The equality with revision 4's 30 and 150 is a coincidence.

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
- With S3 off there is one pair, 1,024 → 4,096. Nothing seen bears on its ratio: the 1,024-slot side has never been run and the 4,096-slot side has not reached a plateau.
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
- **Risk, not settled:** `classes.mc_pair` returns MC-AMBIGUOUS when the two cost measures disagree on which cell is costlier. If T-OQ's (or H8's) measured CPU-seconds per update exceed D-OQ's at some size, that pair is ambiguous and the §22 M5 label applies. T-OQ has never been timed. H8's measured rate (0.0101–0.0110 at 16,384) is well under D-OQ's (0.0235–0.0245), so H8 is safe at 16,384.
- Between the two cells of a step the multipliers are 1.21 (F-OQ, 1K→4K) and 1.70 (F-OQ, 4K→16K), about 1.0 for T-OQ and H8. The smaller cell of a loaded step runs U_L, far beyond any matched snapshot; MC-SHORT cannot occur there.

**Dense at saturation.** Read at equal updates U_L. Where D-OQ costs at least as much per update as the arm (true analytically at every size), D-OQ has had at least the arm's compute, and i\* cannot fall with updates, so "store ahead at equal updates" implies "store ahead at matched compute". A dense lead at equal updates may shrink at matched compute; it still blocks, as any single reading does in §8.5.

## 6. U_P and U_L

**U_P per row** (smallest of {8,192, 16,384, 32,768} with F-OQ ≥ 0.90 at the larger step cell and R2 ≥ 0.95). From the calibration curves: 8K/4K is at 4.37–4.54 bits at 8,192 (a_use about 0.94–0.955); 32K/16K is at 1.96–2.61 at 8,192 (about 0.6) and 4.12–4.23 at 16,384 (about 0.91–0.92). Expected U_P: 8,192, 8,192, 16,384. R2 at 32K/32K has never been run (R2 at 32K/64K passed at 8,192).

This rule changes what C2 can show, after the curves were seen. The ADR says so in §25.6 and asks for confirmation (§25.8 question 8).

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
| New calibration, load search to the ceilings | 2.6–3.6 |
| Rehearsal | about 0.5 |
| Training, 150 cells, U_L 131,072 and 393,216 | 8.0–10.9 |
| Seed block, draw 1 | 0.8–0.9 |
| Evaluation | 1.5–2.5 |
| Gates, timing, simulation, analysis, report | about 0.5 |
| Remaining | 10.8–14.8 |
| **C_need = charged + 2 × remaining** | **26.2–35.2** |

| U_L 8K/1K | U_L 32K/4K | C_need |
|---|---|---|
| 98,304 | 196,608 | 21.8–29.2 |
| 131,072 | 262,144 | 23.7–31.7 |
| 131,072 | 393,216 | 26.2–35.2 |
| 196,608 | 393,216 | 27.4–36.8 |
| 262,144 | 524,288 | 31.1–41.8 |

**The long cell 32K/4K alone** (F-OQ, T-OQ, H8, D-OQ; five replicates; charged hours): 1.7–2.4 at 196,608; 2.3–3.2 at 262,144; 3.5–4.8 at 393,216; 4.6–6.5 at 524,288. Doubled in C_need.

**Does it fit under about 32 hours?** Not reliably.

- It fits if T-OQ costs about what F-OQ costs (C_need 26–30 at the central U_L), or if the loaded cells stop by about 262,144 updates (24–32).
- At the central U_L with T-OQ at 2× it needs 31–35 hours. At both ceilings it needs 31–42.
- T-OQ's cost is the largest unknown: 4.6–5.2 hours of C_need between 1× and 2×. Analytically T-OQ is cheaper than F-OQ at 4,096 and 16,384 slots; the 2× figure is revision 4's planning assumption and was never measured. The timing preview settles it in minutes.

**Cheapest sound alternatives, in the lead's order of preference** (hours of C_need saved at the central U_L):

1. Drop the draw-1 seed block: 1.6–1.7. Already cut 2; it is descriptive. Cost: no measure of initialization spread, which the check flagged as unsampled.
2. Drop D-OQ at 8K/16K: 0.5–0.6. Already cut 3.
3. Drop H8 at the two loaded cells: 1.8–2.0. Loses H8's capacity step and its bits per slot when full (the reference without key learning). H8 alone cannot give a positive outcome.
4. Drop the row of 2,048 facts: 1.9–2.0. Loses control step N1 and the efficiency line's first transition; EFFICIENCY_SUPPORTED becomes unreachable, so the efficiency line would have to become descriptive.
5. Lower the 32K/4K ceiling to 393,216: 0.2–0.4 off the calibration, and the worst case becomes about 28–38 in place of 31–42. Risk: the check's upper range for U_L is 524,288; a cell that needs it returns NOT LOADED.
6. Drop D-OQ at the loaded cells: 2.7–2.8 (4.0–4.1 at the ceilings). The lead would not: it is the one dense comparison whose answer is unknown.

Items 3–6 are not rules in the ADR. They are choices for the human lead (§25.8 question 3).

**Block S3** (128K/16K, F-OQ only, five replicates): one run is 2.7–3.8 hours at 524,288 updates, 4.1–5.7 at 786,432, 5.5–7.5 at 1,048,576; its search runs two draws to 1,048,576. C_need with it: 36–54 hours. It does not fit under 32 on any assumption. A cheaper third size (2,048 facts in 256 slots, F-OQ and H8 only) lies outside the sizes of §24 and is not in the revision; it is question 2.

**The cap rule.** cap = ceil(C_need) from the rehearsal's rates, recorded by the lead only if ≤ C_max, which is the human lead's and is not recorded. No figure is picked.

## 8. The new calibration, in short

| Item | Runs | What it fixes | If it fails |
|---|---|---|---|
| 0a timing preview | time only | projections and item caps; T-OQ and 1,024-slot rates for the first time | — |
| 0b load search: F-OQ, T-OQ at 8K/1K (to 262,144) and 32K/4K (to 524,288), two draws, once each | 8 | U_L per loaded cell: two consecutive candidates pass on all four views | F-OQ has no U_L → NOT LOADED, return to the human lead; T-OQ alone has none → recorded, study proceeds |
| 1 row U_P | 12 | U_P per row | no value qualifies → return |
| 2 H8 reported | 8 | UNDERTRAINED-AT-U_P annotations | gates nothing |
| 3 dense rate, five rates × four units | 40 | D-OQ's rate per unit | best rate is 0.1, or all diverged → return |
| 4 S3 search (only if funded) | +4 | U_L and U_P of 128K/16K | not full → 16,384 NOT MEASURED, fixed |

- The plateau artefact is closed in §8.2 itself (i\* ≥ 0.473 at half the run length), so the registered verdicts and the search use one definition.
- Runs go once to their ceilings and the rule is applied to the finished record. This costs about 0.5–0.8 hours more than a staged search and needs no resume code and no decision while runs are in progress.
- Calibration draw 2 uses initialization seed 2193, so "all four views" samples two initializations.
- Wall time 2.5–3.5 hours plus the preview (`rev5_arithmetic.out` §7).

## 9. Open questions for the human lead

These are §25.8 of the ADR, in the same order.

1. **C_max**: the ceiling for the delegated cap. Need: 26–35 central, 22–29 early, 31–42 at the ceilings.
2. **Block S3**: fund (36–54 hours) or accept one saturation pair. Or the 256-slot cell, outside §24's sizes.
3. **If C_need > C_max after the three cuts**: which item goes (§7 above).
4. **Dense at saturation is binding** (counts as DENSE AHEAD): confirm or make descriptive.
5. **The 0.80 floor of §8.4 at 32K/16K**: value unchanged, cell forced. This is the one place a threshold is not "as it was" in every respect.
6. **R2 at 32K/32K** versus a 65,536-row reference table.
7. **The plateau guard** reuses the DEP floor.
8. **U_P per row by rule** (16,384 expected for the row of 32,768 facts).
9. **NOT LOADED** returns to you; or fix it automatically as NOT TESTED.
10. **Efficiency line kept** on the control steps; the row of 2,048 facts is worth about 2 hours.
11. **T-OQ may be MC-AMBIGUOUS against D-OQ**; no rule change proposed.
12. **One number (3.0) for both sides of the saturation line.**

## 10. What the lead could not settle

- T-OQ's cost per update, the cost of anything at 1,024 slots, D-OQ's cost below 16,384 slots, and the cost of the registered evaluation. All are assumptions until the timing preview and the rehearsal.
- Every U_L. For 8K/1K there is no data at all.
- Whether 2K/1K reaches the ceiling, whether H8 is loaded at the loaded cells, whether T-OQ plateaus where F-OQ does.
- Whether a dense rate chosen at 65,536 updates is the best rate at U_L. If it is not, STORE HOLDS MORE AT SATURATION is weaker than it reads; DENSE HOLDS MORE is unaffected.
- Whether T-OQ, the index read and gate G4 behave at 1,024 slots (four branches, four centroids). The formulas are defined; no code was run to check.
- Whether initialization spread makes the "all 5" plateau condition fail. The seed block measures it afterwards and cannot inform U_L.
- Sections 17–21 of the ADR still name revision 4's cells; they are historical and were left as they are. §18 lists revision 2–4's choices; revision 5's are in §25.5.

## 11. Code and config changes revision 5 implies (for briefing an implementer; nothing here is approved)

Revision 4's code is at commit `3ad821a` (the calibration's code identity) and must stay recoverable. `results/` and `experiments/` are not touched. Whether to edit `studies/p10s1/` in place or start a sibling package is the lead's call at Decision 1; in place is assumed below.

**`configs/p10s1_capacity.toml`** (generated by `core.render_config_toml`; regenerate, do not hand-edit): spec revision 5; `[grid]` slots, cells, doq_cells, r2_cells; remove `overload_*`; `[training]` run multiplier 6 at every size, `dense_rates` = five values, row-U_P candidates; new `[calibration]` block (candidates and ceilings per loaded cell, two-pass rule, dense units and readouts, calibration init seeds 2191 and 2193); `[resources]` cap rule and a `cap_max_hours` field with no default; `[generation] table_facts` (131,072 only with S3). `[thresholds]` unchanged; add the derived plateau floor (0.473 from `dep_use_floor`) as a derived, not free, value.

**`core.py`**
- `SLOT_COUNTS = (1024, 4096, 16384)`; `GRID_CELLS`, `DOQ_CELLS`, `R2_CELLS` (with `(32768, 32768)`); remove `DIAGONAL`, `DIAGONAL_STEPS`, `OVERLOAD_*`, `B3`.
- Steps C1, N1, C2, N2 with a kind (loaded / control); `TRANSITIONS = ("1K→4K", "4K→16K")`; efficiency steps = control steps.
- `Plan`: drop `overload_u_p`; add per-row U_P, per-loaded-cell U_L, the S3 switch with its U_L and U_P; `dense_cut` ⊂ {"8K/16K"}; `plan_configurations`, `key`, `as_json`, `from_json`.
- `run_length`: U_L at a loaded cell (all arms), else 6·U_P of the row; R2 U_P. `RUN_MULTIPLIER`. `u_p_of` by row.
- `snapshot_updates`: add 32,768, 49,152 and the candidates up to U_L at loaded cells.
- `registered_cells`: D-OQ's rate is keyed by unit (the loaded cell, or the slot count), not by slot count alone. Seed block over the new seven cells. S3 cells.
- `DENSE_RATES`; calibration cell builders (load search, row U_P, H8, dense units, S3); per-draw calibration init seed; `_check_calibration_counts` (68).
- Counted-work and multiply-add formulas at 1,024 slots; `doq_hidden(1024)`; `chance_interval(131072)` only with S3; `size_name(131072)` is "128K".
- `CALIBRATION_TABLE_FACTS`, `FACT_TABLE`.

**`classes.py`**
- `View.plateaued`: add the floor on i\*(run // 2).
- New: saturation pair verdict, pair class, arm class, outcome (§8.10); dense-at-saturation label (§8.5) and its inclusion in `_is_ahead`; the cost and D-OQ-plateau conditions of STORE HOLDS MORE.
- `capacity_arm_class`: transitions map and the cell of the 0.80 floor come from the caller; check both.
- `milestone_reading`: the saturation and dense-at-saturation conditions, the size range, the new reading "capacity steps shown; proportional saturation not shown".
- Positive-label registry (`tagged`, `is_positive`, `untagged_positive_labels`): add PROPORTIONAL STEP, SATURATION_SCALES, SATURATION-PROPORTIONAL, STORE HOLDS MORE AT SATURATION.
- Retire `study_b_label`. Efficiency arm class over the control steps only.

**`calibrate.py`**: replace `loaded_at_slot_count`, `LoadDecision`, `load_decision`, `cut3_eligibility`, `overload_u_p` with: pass-at-U, arm U_L (two consecutive candidates), cell U_L and the three fixed outcomes; row U_P for every row; H8 report cells; `select_dense_rate` per unit over five rates with diverged rates left out and "top of grid" and "all diverged" as returns; the S3 search; `finalize` and `_returns`. A `failed` run in the load search or the dense grid is data for the rule, not an engineering stop.

**`stages.py`**: the calibration stage (cell lists, snapshots, the new run directory, failed runs kept); a timing-preview step through the whitelist validator; the uses of `core.DIAGONAL` at lines 665 and 693; generation table size; rehearsal items for the new sizes and S3.

**`analysis.py`**: `REF_CELL` (2K/4K, 8K/16K, 32K/32K, 128K/128K); the four steps; hierarchy cells (8K/4K, 32K/16K); conventional-retrieval cell (32K/16K); saturation records and b(N) table; dense at saturation; efficiency on control steps; "16,384→65,536 NOT TESTED" on every capacity outcome.

**`budget.py`**: rates for 1,024 slots and R2 at 32,768; C_need and the cap rule against C_max; `cut_sequence` (seed block draw 2, draw 1, D-OQ at 8K/16K); S3 admission; `caps_table` over the new plans.

**`frozen.py`**: freeze record fields (U_L, row U_P, dense rates per unit, the cap, S3, cuts); the loop over `SLOT_COUNTS` at line 215.

**`gates.py`**: slot counts; G5 over the new 30 configurations; G8 at 1,024; G9 with seed 2193; G2 with a 131,072 set only under S3; G4's P9-I identity at a size P9-I has (4,096 or 16,384).

**`train.py`**: the whitelist check `slots in core.SLOT_COUNTS` (line 155) must admit R2's 32,768 (and 131,072 under S3); snapshot marks and optimizer keep-set at loaded cells.

**`model.py`, `index.py`, `evaluate.py`**: confirm T-OQ with four branches (visit 2), F-OQ-IVF with four centroids and at least 512 candidates of 1,024 keys, and an R2 table of 32,768 rows. No formula changes are expected; tests are.

**`timing.py`, `traffic.py`, `synthetic.py`, `report.py`, `e2e.py`**: sizes; synthetic full-registry records exercising every new verdict, class, label and outcome, including saturation NOT FULL, SUBPROPORTIONAL and DENSE HOLDS MORE; the report's new tables and the "NOT TESTED" line; the end-to-end test of the registered sequence.

**`launch/*.sh`, `freeze/`**: regenerate; the freeze of revision 4 does not carry over.

**Tests (`tests/test_p10s1_*.py`)**: update the registry counts and cells; new tests for the plateau floor (the artefact case at 1,024–8,192 updates must now fail), the two-pass rule and each fixed outcome, the dense-rate rule (ties, diverged, top of grid), the saturation line on synthetic records, dense at saturation including the blocking path into CAPACITY-NEGATIVE (b), the cap rule, the plan options and the cuts.

**Order for the implementer.** `core` and config → `classes` → `calibrate` and the calibration stage → the rest. The calibration needs only the first three plus the timing preview. An independent implementation audit comes before any run (§11 item 3).
