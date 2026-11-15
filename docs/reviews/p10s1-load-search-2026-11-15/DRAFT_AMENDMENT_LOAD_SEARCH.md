# ADR-0021 §24 — extension of the load calibration (DRAFT)

- **Status: DRAFT AMENDMENT. SPEC: PENDING ASTRA REVIEW. Not reviewed, not approved, nothing in it has run.** It must pass the independent check (Opus 5.5, separate context) and be recorded by the lead before any run. Astra review: NOT_PERFORMED.
- **Date:** 2026-11-15 (UTC). **Author:** the lead (Claude Fable 5.2, model id `claude-fable-5-2`). No task was delegated in writing it.
- **Origin:** ADR-0021 §23. The human lead, verbatim: "prioritize resolving S1's no-loaded-cell condition over adding runtime margin to S0."
- **Inputs (read-only):** `results/p10s1-calibration-2026-11-15/` and run directory `experiments/P10S1C-20261115T172402822940Z-5e33fb08d1104815a21110f1f308c27c` (commit `3ad821a`, calibration draws `p10s1-cal-1`, `-2`, initialization seed 2191). Analysis script and output beside this file: `load_curve_analysis.py`, `load_curve_analysis.out`.
- **Marking.** **[lead's choice]** marks a judgment-call number or rule, with the alternative not taken.
- Calibration numbers below are calibration, never results. Every extrapolation is marked as one.

## 24.0 What the calibration curves show (the basis of this amendment)

### 24.0.1 Curves i(u), bits per fact (range over two draws and two panels)

| Slots | Facts | Load | 8,192 | 16,384 | 32,768 | 65,536 | Last three increments per doubling (16K, 32K, 65K) |
|---|---|---|---|---|---|---|---|
| 4,096 | 8,192 | 2 | 4.37–4.54 | 4.81–4.85 | 4.92 | 4.96 | 0.30–0.46, 0.07–0.11, 0.03–0.04 |
| 4,096 | 16,384 | 4 | 1.66–2.15 | 3.13–3.28 | 3.85–3.86 | 4.06–4.12 | 1.13–1.47, 0.57–0.73, 0.21–0.26 |
| 4,096 | 32,768 | 8 | 0.30–0.42 | 0.96–1.14 | 1.56–1.65 | 1.89–1.94 | 0.66–0.72, 0.51–0.60, 0.29–0.33 |
| 4,096 | 65,536 | 16 | 0.03–0.06 | 0.19–0.25 | 0.47–0.55 | 0.72–0.75 | 0.16–0.19, 0.28–0.30, 0.20–0.25 |
| 16,384 | 8,192 | 0.5 | 4.99–5.00 | 5.00 | 5.00 | 5.00 | 0.00 |
| 16,384 | 32,768 | 2 | 1.96–2.61 | 4.12–4.23 | 4.69–4.72 | 4.85–4.87 | 1.62–2.15, 0.48–0.58, 0.15–0.16 |
| 16,384 | 65,536 | 4 | 0.23–0.37 | 1.44–1.71 | 2.79–2.90 | 3.49–3.54 | 1.21–1.34, 1.19–1.35, 0.64–0.71 |
| 16,384 | 131,072 | 8 | 0.01–0.02 | 0.20–0.28 | 0.84–0.97 | 1.46–1.52 | 0.20–0.26, 0.64–0.70, 0.54–0.62 |

The full table (every snapshot, draw and panel, with a_use) is part 1 of `load_curve_analysis.out`; the increments and their ratios are part 2; the rule of §8.2 read at every available run length is part 3.

### 24.0.2 Measured facts (not extrapolations)

1. **Load 4 at 4,096 slots can never be loaded.** Its i\* is already 4.06–4.12 at 65,536 updates. i\* does not decrease with run length, so i\* ≤ 4.0 fails at every run length from 65,536 up; below that the cell is not plateaued (increment 0.33–0.42 at 49,152).
2. **Loads 0.5 and 2 are at the ceiling** at both sizes (4.85–5.00) and cannot be loaded.
3. Every other cell is below 4.0 and its last increment per doubling is 0.20–0.71, two to seven times the plateau limit of 0.10.
4. The ratio of successive increments (a doubling's increment over the previous one's) at the last doubling: 0.29–0.46 (4K, load 4), 0.55–0.57 (4K, load 8), 0.67–0.89 (4K, load 16), 0.52–0.54 (16K, load 4), 0.78–0.97 (16K, load 8). Loads 16 at 4K and 8 at 16K have barely begun to decelerate.
5. A property of the registered rule that the data expose: before learning begins a cell is "plateaued and at most 4.0" (load 16 at 4,096 slots read at 8,192 updates: i\* 0.03–0.06, increment below 0.10). It does not affect the cells of this amendment, which are far past onset, but see Open point 6.

### 24.0.3 Extrapolation (NOT a measurement)

Assumptions, stated: **G** — from 65,536 updates on, each further doubling adds r times the previous doubling's increment, with r fixed at that curve's last observed ratio. **S** — the decay relaxes: √r in place of r. **C** — no decay. Three post-onset doublings carry every fit. A curve may decay faster (a hard storage limit) or slower (a long tail) than any of these.

| Cell | Under G: plateau rule first met at / i there | Under S | Asymptote under G |
|---|---|---|---|
| 4K, load 4 | 131,072–262,144 / 4.13–4.28 (**above 4.0: not loaded**) | 262,144–524,288 / 4.25–4.48 | 4.16–4.33 bits = 68–71k bits in the store |
| 4K, load 8 | 262,144 / 2.17–2.20 (increment 0.09–0.10: **on the edge**) | 1,048,576 / 2.5 | 2.29–2.32 = 75–76k bits |
| 4K, load 16 | 262,144 (draw 1) / never (draw 2; r = 0.88) | 1,048,576 / never | not identified |
| 16K, load 4 | 524,288–1,048,576 / 4.17–4.21 (**above 4.0: not loaded**; crosses 4.0 between 131,072 and 262,144) | not within 4M | 4.27–4.29 = 280–281k bits |
| 16K, load 8 | not within 4M | not within 4M | not identified |

### 24.0.4 Information budget

F-OQ has slots × 48 + 1,025 trainable parameters: 197,633 at 4,096 slots, 787,457 at 16,384. Demand is facts × 5 bits.

| Slots | Load | Demand, bits | Demand per parameter | Retained at 65,536 updates | Retained per slot | Asymptote under G per slot |
|---|---|---|---|---|---|---|
| 4,096 | 4 | 81,920 | 0.41 | 67.0k | 16.4 | 17.0 |
| 4,096 | 8 | 163,840 | 0.83 | 62.7k | 15.3 | 18.4 |
| 4,096 | 16 | 327,680 | 1.66 | 48.3k (rising) | 11.8 | not identified |
| 16,384 | 4 | 327,680 | 0.42 | 230.6k (rising) | 14.1 | 17.1 |
| 16,384 | 8 | 655,360 | 0.83 | 194.7k (rising) | 11.9 | not identified |

What it suggests:

- The counting budget does not bind anywhere: 32-bit parameters could hold all of it, and even against a heuristic of about 2 bits per parameter (a rule of thumb for memorization in trained networks, not a law) only load 16 comes near (1.66 bits per parameter; 2.5 per value parameter). **A parameter-counting argument therefore does not predict a plateau below the ceiling at loads 4 and 8.**
- The curves suggest something tighter than the parameter count. The three cells whose deceleration is measurable extrapolate to **about 17–18 bits per slot** (0.35–0.38 bits per parameter) at both sizes: 68–76k bits at 4,096 slots, about 280k at 16,384. If that holds, the plateau level is about 17.7 × slots / facts bits per fact: **about 4.2–4.4 at load 4, 2.2–2.3 at load 8, 1.1 at load 16, about 2.9–3.1 at load 6.** This is a fit to three cells under assumption G; it is a hypothesis the extension tests, not a finding.
- Consequence for the 4.0 threshold: under that hypothesis a plateau at or below 4.0 needs a load of about 4.4–4.6 or more. **Load 4 is predicted to plateau just above the threshold at both sizes** (measured for 4,096 slots: already above 4.0).

### 24.0.5 Answer to "can a cell be loaded within a fundable run length, and where" (extrapolated)

- **4,096 slots: plausibly yes, not assured.** Load 8 (32,768 facts) is predicted to meet the plateau rule near 2.2 bits between 262,144 and 524,288 updates if its increments keep shrinking at the observed ratio, and only near 1,048,576 if the decay relaxes. A load between 4 and 8 should plateau sooner (if the time to plateau scales with facts, as loads 4 and 8 suggest: about 1,000 exposures per fact) and still well below 4.0; load 6 (24,576 facts) is predicted near 2.9–3.1 bits at 196,608–393,216 updates.
- **16,384 slots: probably not, with an R2 reference.** A row needs facts ≤ 65,536 (R2 at 65,536 slots), so load 4 is the highest admissible load, and it is predicted to pass 4.0 before it plateaus. Load 8 (131,072 facts) is far from a plateau and has no R2 reference.
- So the most likely outcome of the extension is: **a loaded cell for 4K→16K at 262,144–524,288 updates, and CAPACITY NOT TESTED for 16K→64K.** See Open point 1 for what that would and would not buy.

## 24.1 The extension's runs

F-OQ only, learning rate 0.003, the two calibration draws (`p10s1-cal-1`, `-2`; bases 219001, 219101), initialization seed 2191, six single-thread workers, the calibration fact table (131,072 facts; each cell uses its first F facts). No registered seed, panel or draw is generated, read or evaluated.

**Cells (six runs):**

| Tag | Slots | Facts | Load | Start | Why this cell |
|---|---|---|---|---|---|
| X8 | 4,096 | 32,768 | 8 | continues the calibration run from its stored 65,536-update checkpoint | the registered cell 32K/4K; lowest measured cell at 4,096 slots that is below 4.0 and decelerating |
| X6 | 4,096 | 24,576 | 6 | from zero | **[lead's choice]** hedge: predicted to plateau one grid step sooner than X8, near 3.0 bits. Alternatives not taken: 20,480 facts (load 5; predicted 3.4–3.7, too close to 4.0), no intermediate cell (X8 alone; if X8 is not plateaued at the ceiling the 4K→16K question stays open) |
| Y4 | 16,384 | 65,536 | 4 | continues from its stored 65,536-update checkpoint | the highest load at 16,384 slots that has an R2 reference |

Not run, with reasons: 4,096 slots load 4 (cannot be loaded, §24.0.2 item 1); 4,096 slots load 16 **[lead's choice]** (barely decelerating; under every assumption it plateaus no sooner than load 8 and would give the costliest row; alternative not taken: run it as a third 4,096-slot cell); 16,384 slots load 8 (no R2 reference: 131,072 facts exceed 65,536 slots; ADR §10.1 "The lead never runs a row without R2"); loads 0.5 and 2 (ceiling). No T-OQ, H8, R2 or D-OQ cell is run in the load search.

**Candidate run lengths** **[lead's choice]**: U ∈ {131,072, 196,608, 262,144, 393,216, 524,288}. Alternative not taken: the pure doubling grid (131,072, 262,144, 524,288), which costs the registered rows up to a third more updates than needed.

**Hard ceilings on run length** **[lead's choice]**: **U_max = 524,288 at 4,096 slots; U_max = 262,144 at 16,384 slots.** Reason: the registered row costs about 2.5 hours of cap per 131,072 updates at 4,096 slots and about 4.8 at 16,384 (§24.4); beyond these lengths a row alone would need a cap above 32 hours. Alternatives not taken: 1,048,576 at 4,096 slots (a cap near 40 hours for that row alone); 262,144 at both sizes (stops short of where load 8 is predicted to plateau under the less favourable half of assumption G).

**Snapshots.** Every run is evaluated, exactly as the load calibration was (Panels A and B of the calibration draw), at 98,304 and at every candidate up to its last update; X6 also at the load calibration's grid (512 … 65,536, and 24,576 and 49,152). The optimizer state is kept at each candidate. Nothing else is evaluated.

**Continuation.** X8 and Y4 resume from `snapshots/u0065536` (model, optimizer, RNG, trainer state) of the calibration cells; the training stream is indexed by update, so the continued run is the longer run. Before stage E1, two checks, both on calibration seeds: (a) the stored checkpoint's SHA-256 equals `snapshot_sha256["65536"]` of the cell's `train.json`, and re-evaluating the restored model reproduces the recorded counts of `eval/u0065536/eval.json` exactly; (b) `train.restore_check` on X8 draw 1 with a split at 512 updates is bit-identical. If either fails for a cell, that cell is run from zero (cost: at most 1,479 s more on stage E1) and the failure is recorded; the stored calibration records are never modified. The extension writes to a new run directory.

**Order: stages E1 … E5,** one per candidate, in increasing order. Stage Ek runs every cell that is still OPEN (§24.2) from its last checkpoint to candidate U_k, each run on its own worker. If fewer than six workers are free the queue order is X8 d1, X8 d2, X6 d1, X6 d2, Y4 d1, Y4 d2. After each stage the stopping rule is evaluated by code from the eval records and written to the extension record before the next stage starts.

**Cost, from the measured rates** (`calibrate/manifest.json`; wall seconds per update including snapshot evaluations, six workers, shared machine: 0.01091 for X8, 0.01053 for X6 by interpolation, 0.02256 for Y4):

| Stage | To | X8 | X6 | Y4 | Stage wall | Cumulative charged |
|---|---|---|---|---|---|---|
| E1 | 131,072 | 715 s | 1,381 s | 1,479 s | 1,479 s | 0.41 h |
| E2 | 196,608 | 715 s | 690 s | 1,479 s | 1,479 s | 0.82 h |
| E3 | 262,144 | 715 s | 690 s | 1,479 s | 1,479 s | 1.23 h |
| E4 | 393,216 | 1,431 s | 1,381 s | — | 1,431 s | 1.63 h |
| E5 | 524,288 | 1,431 s | 1,381 s | — | 1,431 s | 2.03 h |

CPU-seconds of all six runs to their ceilings: about 29,900 (8.3 CPU-hours). The row-U_P step of §24.3 adds at most 0.51 h (four runs, the slowest 1,830 s). The dense grid of §24.5 adds at most 1.22 h. **Projected worst case 3.8 charged hours; expected about 2.3** (load search to 262,144, one row-U_P step, two dense rates).

**Hard ceiling on charged hours for the extension** **[lead's choice]**: **7.5 charged hours in total** (twice the projected worst case, as §10.2 caps stages at twice their measured time): 5.0 for the load search with the row-U_P step, 2.5 for the dense grid. Each stage has a cap of twice its projected wall; a stage that would pass its cap or the total is not started, and the cell concerned is treated as having reached its ceiling without being loaded (§24.2 rule 3b). Alternative not taken: 3.8 hours with no margin. All of it is charged to S1's ledger. With 1.57 h already charged, the extension at its expected cost leaves the present 16-hour cap just sufficient for the unchanged registered study on the old projection (1.57 + 2.3 + 0.45 + 2 × 5.6 = 15.5); at its ceiling it does not. Any raise is the lead's, under the recorded delegation, before any registered seed is observed, and is written into §15 with the measured projection (see Open point 3).

## 24.2 Stopping rule (reads only the calibration draws' own curves)

Definitions. A **view** is one cell on one calibration draw and one calibration panel (four views per cell). For a candidate U, d(U) = i\*(U) − i\*(U/2), on the cell's own snapshots (U/2 is always a snapshot: 65,536, 98,304, 131,072, 196,608, 262,144).

1. **LOADED AT U.** A cell is loaded at candidate U if, on all four views, it is loaded by §8.2 with U in the place of U_run: d(U) ≤ 0.10 and i\*(U) ≤ 4.0. The thresholds and the comparison (`classes.View.plateaued`, `.loaded`) are those of §8.2, unchanged.
2. **Stop on success, per slot count.** After stage Ek, if a cell of a slot count is LOADED AT U_k, the search at that slot count stops and U_L = U_k. At 4,096 slots, if X8 and X6 are both loaded at the same candidate, X8 is taken **[lead's choice]** (it is the registered cell and creates no new row; alternative not taken: X6, the lower load).
3. **EXCLUDED** (the cell is closed and never run further) as soon as one of these holds:
   a. **Above the level:** i\* > 4.0 on any view at any snapshot. i\* cannot decrease, so the cell cannot be loaded at any longer run length.
   b. **Ceiling:** the cell has been read at its U_max, or a stage was not started under §24.1's hour ceiling, and it is not LOADED.
   c. **Cannot plateau in time** **[lead's choice]**: at candidate U_k, on any view, d(U_k) × (1/8)^log₂(U_max/U_k) > 0.10. That is: even if every further doubling cut the increment to one eighth, the plateau rule would not be met at the ceiling. One eighth is below every ratio observed after onset (smallest 0.17, load 2 at 4,096 slots nearing the ceiling) except in the load-0.5 cell as it reached exactly 5.0 (0.01–0.08); a cell that hit a hard limit below 4.0 as abruptly would be closed wrongly, which is the risk of this rule. In practice this bites only at the candidate before the ceiling (d > 0.237) and saves the last stage. Alternative not taken: no such rule (run to the ceiling always).
4. **OPEN** otherwise; an OPEN cell runs in the next stage.
5. **End of the search at a slot count:** a cell is loaded (outcome LOADED(F\*, U_L)), or every cell of the slot count is EXCLUDED (outcome NO LOADED CELL). The two slot counts end independently. Stages continue while any cell is OPEN.
6. Nothing else stops, extends or redirects the search. No cell, load, candidate or ceiling is added after a stage has been read. The extension record keeps every stage, including excluded cells.
7. The extension is audited from its raw eval records by the auditor before its outcome is used.

## 24.3 Decision rule: from the extension's outcome to the registered design

The same sentence as §10.1 governs every case: **a prediction of loadedness from calibration does not make a registered cell loaded; the registered run judges every cell, in every arm and replicate, on its own snapshots.** The registered run has fixed run lengths; nothing in it stops adaptively.

### (a1) 4,096 slots: LOADED(F\*, U_L), F\* ∈ {32,768, 24,576}

The 4K→16K transition gets a **loaded row L** with F\* facts.

| Item | What it becomes | Changed? |
|---|---|---|
| Cells of row L | F\*/4K (smaller) and F\*/16K (larger). For F\* = 32,768 these are the registered cells 32K/4K and 32K/16K, trained once to the longer of their run lengths and read at both snapshot sets. For F\* = 24,576 they are new cells; the draw's 24,576-fact set is the first 24,576 facts of its 32,768-fact table (as the 8,192 and 2,048 sets are), with its own training stream from the same generator. No new seed name | new or lengthened |
| Arms | F-OQ, T-OQ, H8 at both cells; D-OQ at the larger cell only; F-OQ-IVF is F-OQ's cells read through the index. As every other row | no change of arm |
| R2 reference | R2 at F\*/64K (one dedicated slot per fact), run and read at 8,192 updates, a_use ≥ 0.95 on both panels: REF for row L. For F\* = 32,768 this is the registered R2 cell 32K/64K, unchanged. **[lead's choice]**: read at 8,192, the registered R2 run length; alternative not taken: read at the row's U_P′ (never stricter) | new cell only for 24,576 |
| Row U_P′ | By the rule §10.1 already fixes for an added row: the smallest of {8,192, 16,384, 32,768} at which F-OQ's a_use ≥ 0.90 at the row's larger cell on both calibration draws and panels, with R2 ≥ 0.95 at the row's REF cell at 8,192 updates. For F\* = 32,768 no run is needed: the load calibration holds 32K/16K to 65,536 updates and item 1 holds R2 at 32K/64K (by those records U_P′ = 16,384: a_use 0.910–0.923 at 16,384 and 0.58–0.70 at 8,192). For F\* = 24,576: F-OQ at 24K/16K to 32,768 updates with snapshots at the three values, and R2 at 24K/64K to 8,192, on both calibration draws (4 runs, about 0.16 h). If no value qualifies the work returns to the human lead | row-specific, by the existing rule |
| Run lengths | Smaller cell: **U_L** for F-OQ, T-OQ and H8. Larger cell: 4·U_P′ (the registered multiplier at 16,384 slots), D-OQ included. **[lead's choice]** for both: alternatives not taken — a smaller-cell run one candidate longer than U_L, for margin on the plateau rule (Open point 2); a larger cell run to U_L, so that Δ_FULL compares equal updates (about 2.7 charged hours, 5.3 of cap, per 131,072 updates) | changed |
| Snapshot grid | Smaller cell: U_P′ × {1/16, 1/8, 1/4, 1/2, 1, 2, 4}, the matched-compute snapshots m·U_P′ of the MC grid up to U_L, U_L/2, U_L. Larger cell: the rule of §5.4 with U_P′ and 4·U_P′. For F\* = 32,768 the registered snapshots of both cells are kept as well | changed |
| Step | **L1: F\*/4K → F\*/16K**, the Study-B-side step of the 4K→16K transition on the capacity line. It **replaces B1 on the capacity line** (for either F\*), as the overload row of §10.1 replaces the 32,768-fact row's 16K→64K step. A1 stays. The 32,768-fact row keeps all its cells | changed |
| MU | i of both cells at U_P′; Δ_MU as §8.2 | U_P′ in place of U_P |
| MC | §5.4 unchanged with U_P′: the costlier cell at U_P′, the cheaper at the smallest m·U_P′ of the MC grid that matches cost in the larger of the two cost measures; beyond the cheaper cell's run length it is MC-SHORT; MC-AMBIGUOUS as ruled | U_P′ in place of U_P |
| SAT, plateau, loaded, fifth condition, Δ_FULL, CEILING | §8.2 unchanged, with U_run(smaller) = U_L, U_run(larger) = 4·U_P′, and CEILING read at U_P′ | run lengths only |
| DEP | every snapshot of both cells up to their run lengths (§22 (g)) | more snapshots |
| Dense labels (§8.5, §22 M5) | at F\*/16K if L1 is a CAPACITY STEP, in the readings MU (U_P′), MC and D-BEST (D-OQ's best up to 4·U_P′), with the calibrated dense rate of 16,384 slots | U_P′ in place of U_P |
| Cut 3 of §10.3 | D-OQ at F\*/16K is never cut (its step's smaller cell is predicted loaded). 8K/64K stays eligible. 32K/16K stays eligible only if F\* = 24,576 | eligibility only |
| Seed block | the seven cells of §6.2 at their registered run lengths and snapshots (§22 m2). Row L adds nothing to it. **[lead's choice]**; alternative not taken: 32K/4K of the seed block run to U_L | no change |
| Cut order | §10.3 unchanged: seed block draw 2, seed block draw 1, D-OQ by cut 3, then return to the human lead. Row L is never cut and never shortened | no change |
| Study A (A1, A2), B2, the diagonal, Study B's label, U_P = 8,192 for every registered row, five replicates, every threshold | | no change |
| Efficiency line | reads steps A1, A2, B1, B2 at the registered snapshots at or below the registered run lengths of §5.4 only. A longer run of 32K/4K or 32K/16K is, up to those snapshots, the registered run (G4); the added snapshots, row L's U_P′ and any new cell enter no efficiency rule | no change |

### (a2) 16,384 slots: LOADED(65,536, U_L)

Row 4 of §10.1's table applies as written (the row of 65,536 facts at 16,384 and 65,536 slots; F-OQ, T-OQ, H8; D-OQ at the larger cell; R2 at 65,536 slots as its REF cell; the 65,536-fact table nesting the 32,768-fact one; its U_P from {8,192, 16,384, 32,768} by a calibration of its larger cell, 2 arms × 2 draws; return to the human lead if none qualifies; the 32,768-fact row keeps its cells and only its 4K→16K step), **with one change: the smaller cell 65K/16K runs U_L in place of 4·U_P′**, with the snapshot grid of (a1). The larger cell runs 2·U_P′. Everything in the "changed?" column of (a1) applies in the same way. If (a1) also holds, the 32,768-fact row has no capacity step of its own left; its cells stay for Study B, the efficiency line, the seed block and cut 3.

### (b) Cost of the registered design as a function of U_L, and where it stops being fundable

Projections from the calibration's measured rates; **T-OQ is unmeasured and taken at twice F-OQ**, as in §10.3; evaluation, index builds and ablations at the added snapshots are not included. The rehearsal, repeated with the new rows, decides; these figures do not.

- 4,096 slots: the smaller cell costs 3 × 0.01091 + 0.00827 = 0.0410 s per update per replicate (F-OQ, T-OQ, H8): **1.24 charged hours, 2.5 hours of cap under the twofold rule, per 131,072 updates of U_L.**
- 16,384 slots: 3 × 0.02256 + 0.01104 = 0.0787 s per update per replicate: **2.4 charged hours, 4.8 hours of cap, per 131,072 updates.**

| Row | U_L | Added charged hours (5 replicates, six workers) | Cap needed by the twofold rule, that row alone |
|---|---|---|---|
| L, F\* = 32,768, U_P′ = 16,384 | 131,072 / 196,608 / 262,144 / 393,216 / 524,288 | 1.5 / 2.1 / 2.7 / 4.0 / 5.2 | 18.5 / 19.7 / 21.0 / 23.5 / 26.0 |
| L, F\* = 24,576, U_P′ = 16,384 | same | 2.6 / 3.2 / 3.8 / 5.0 / 6.3 | 20.8 / 22.0 / 23.2 / 25.6 / 28.0 |
| L, F\* = 24,576, U_P′ = 32,768 | same | 4.0 / 4.6 / 5.3 / 6.5 / 7.7 | 23.6 / 24.8 / 26.0 / 28.4 / 30.9 |
| 65,536 facts, U_P′ = 16,384 | 131,072 / 196,608 / 262,144 | 4.6 / 5.8 / 7.0 | adds 9.2 / 11.5 / 13.9 to the cap |
| 65,536 facts, U_P′ = 32,768 | same | 6.8 / 8.0 / 9.2 | adds 13.5 / 15.9 / 18.3 |

The "cap needed" column takes 1.57 h charged, 2.3 h for the extension, 0.45 h for the rehearsal and 5.6 h remaining for the unchanged study (15.5 h in all under the twofold rule).

**Fundability rule** **[lead's choice]**: the registered design with the rows of (a1) and (a2) is adopted only if the headroom rule of §10.3, evaluated at the repeated rehearsal, holds under a cap of at most **C_max = 32 charged hours** (twice the present cap), after the cuts of §10.3 in their order if needed. Up to C_max the lead raises the cap under the recorded delegation, before any registered seed is observed, and records it in §15 with the measured projection. If the rule does not hold under C_max, the work returns to the human lead with each row's measured cost; the lead does not choose which transition to keep, shorten a run, or drop an arm. On the projection: either 4K row alone is fundable up to 524,288 updates; the 16K row alone except at U_P′ = 32,768 with U_L = 262,144; both together only when their added cap is at most about 16.5 hours (for example L at 262,144 with the 16K row at 131,072 and U_P′ = 16,384). Alternatives not taken: C_max = 24 (the 4K row to about 393,216 only, no 16K row beyond 131,072) and C_max = 40.

### (c) NO LOADED CELL at a slot count

For the transition concerned (4K→16K for 4,096 slots, 16K→64K for 16,384 slots) the capacity line is fixed in the freeze record as **CAPACITY NOT TESTED — NO LOADED CELL WITHIN BUDGET**, with the extension's record (cells, last run length read, the rule that closed each cell) beside it. The registered grid, run lengths and snapshots of that transition stay as revision 4 has them. §8.7 row 5 and §22 m13 apply as written: no arm is CAPACITY_SUPPORTED when either transition is not tested, and the outcome names the transition. The efficiency line runs unchanged. The capacity question for that transition goes to P10-I with the extension's curves and the cost table of (b). No further load search is run in S1.

## 24.4 What does not change

- **No threshold of §8 changes.** Loaded is "plateaued and i\* ≤ 4.0 at the run length"; plateaued is "i\*(U_run) − i\*(U_run/2) ≤ 0.10"; 0.5, 0.25, 4.5, 0.80, 0.85, 1.10, −0.25, 3.0 and every other number of §8 stand. The extension reads the same two definitions at longer run lengths; it changes which run length a row has, never what loaded means.
- **No arm changes.** No arm is added, removed or retuned; the memory arms keep 0.003.
- **The efficiency line is untouched** (§8.8: steps, level, censoring, classes, outcome), except that D-OQ's learning rate, which §8 already lets change before the freeze, may change under §24.5 and with it the input of the DENSE FASTER label.
- Five replicates; U_P = 8,192 for every row of revision 4; the cut order; the stop rules of §11; the memory caps; the rulings of §22 and §22.1.
- The lead believes one threshold stands in the way of the 16K→64K question. It is **not** changed here; the evidence is under Open point 1.

## 24.5 The dense control's learning-rate grid — PROPOSAL for the independent check and the lead

Observed: the selection of §10.1 item 3 chose 0.01, the top of {0.001, 0.003, 0.01}, at both sizes, with no tie. Minimum Panel A accuracy over the two draws: at 16,384 slots 0.091 / 0.443 / 0.998 at U_P; at 65,536 slots 0.044 / 0.062 / 0.294 at U_P and 0.054 / 0.145 / 0.969 at 16,384 updates. Accuracy rises with the rate at every snapshot of both sizes, so the best rate was not bracketed.

Proposed rule:

1. **Rates added, in order: 0.03, then 0.1, then 0.3** **[lead's choice]** (the grid's own spacing of about threefold; alternatives not taken: 0.02 and 0.05, a finer step that may need more rounds; stopping at 0.1).
2. **Runs per added rate:** D-OQ at 8K/16K and 32K/64K, both calibration draws, to the run length of the slot count (32,768 and 16,384), evaluated at the snapshots the dense-rate calibration used. Four runs, about 1,463 s of wall, 0.41 charged hours; a rate is run only at a slot count that is still open.
3. **Selection, unchanged:** over all rates tried at a slot count, the higher minimum Panel A accuracy at U_P; among rates within 0.02, the tie rule of §22 M7 and §22.1 (the faster learner down the doubling grid to U_P/16, then the smaller rate). The 16,384 choice also serves 4,096 slots.
4. **A rate has diverged** at a slot count if a run of it ended on the trainer's non-finite refusal (loss, gradient norm or parameter), or its minimum Panel A accuracy at U_P or at its run length is inside the chance interval of G2. A diverged rate is not eligible for selection and is kept in the record.
5. **Stop, per slot count,** after a round, when (i) the selected rate is below the largest rate tried (the best rate is interior), or (ii) the largest rate tried has diverged, or (iii) 0.3 has been tried. In case (iii), if 0.3 is selected, the rate stands and every dense label carries **DENSE RATE AT GRID EDGE**; the lead is told.
6. **Cost:** at most three rounds, 1.22 charged hours, inside §24.1's ceiling of 2.5 hours for this part. It runs after the load search and its row-U_P step.
7. The memory arms are not retuned. The tuning is one-sided in the control's favour, which is the conservative direction for BEATS DENSE and makes DENSE AHEAD and DENSE FASTER easier to reach; it is stated so that it can be weighed.

## 24.6 Provenance

- This amendment is written **after** the 46 calibration runs were observed and **before** any registered seed, draw, panel or record of S1 exists. The registered data have not been generated.
- **Informed by the calibration curves:** the choice of the three cells and the exclusion of the others; the intermediate load of 24,576 facts; the candidate grid and both run-length ceilings; the one-eighth bound of rule 3c; the fact that U_P′ would be 16,384 for a 32,768-fact row; the cost figures; the dense rates proposed.
- **Not informed by them, and unchanged:** every threshold, the definitions of plateaued and loaded, the verdict tables, the arms, the replicate count, the efficiency line.
- **Why this does not bias a registered result.** (1) The registered draws are new data and new initializations; no calibration draw or panel enters a verdict. (2) Every rule here is fixed before those draws exist, and maps the extension's outcome to the design with no choice left. (3) A loaded smaller cell is a precondition of the positive verdict (CAPACITY) and of the negative one (NULL) alike; finding a row where the test can be run does not favour either answer. (4) The registered run judges loadedness again on its own snapshots; the calibration only predicts.
- **Limits of that argument, stated.** (i) U_L is the first candidate at which two calibration draws pass the plateau rule, so the registered cells will sit close to the 0.10 limit and some replicates may fail it (Open point 2). (ii) The row-U_P rule places the readout where the larger cell has reached 0.90, which helps Δ_MU and Δ_SAT; it is the rule §10.1 already fixes for an added row, applied here for the same reason. (iii) The search is adaptive over two draws and one initialization seed; it is a search for a testable design, and its curves are never reported as capacity results.

## Open for the lead

1. **The 4.0 threshold against the R2 rule at 16,384 slots (scientific decision; not changed here).** Evidence: load 4 at 4,096 slots is measured at 4.06–4.12 and still rising slowly (extrapolated plateau 4.2–4.3); load 4 at 16,384 slots is at 3.50–3.54 with increments 0.64–0.71 and is extrapolated to pass 4.0 between 131,072 and 262,144 updates and to level near 4.3. A row needs facts ≤ 65,536 for its R2 reference, so load 4 is the ceiling at 16,384 slots. If the extension confirms this, **16K→64K is CAPACITY NOT TESTED under the present threshold whatever is spent**, and by §22 m13 no arm can then be CAPACITY_SUPPORTED: a loaded 4K→16K row would buy step classes at one transition and no CAPACITY-POSITIVE or CAPACITY-NEGATIVE outcome. The options, none taken: (a) accept that and decide whether a one-transition result is worth the row's cost (about 3–15 hours of cap, §24.3 (b)); (b) a new revision that moves the loaded threshold toward the CEILING boundary of 4.5 — this also closes a gap in §8.2, where a plateaued smaller cell between 4.0 and 4.5 is neither CEILING nor loaded — which is a threshold change after calibration and needs a full re-review; (c) a 262,144-slot R2 reference for a 131,072-fact row, a new size and a new budget; (d) carry 16K→64K to P10-I. The lead should also confirm the reading of §8.7 row 5 with §22 m13 for the mixed case (one transition tested, one fixed NOT TESTED).
2. **Margin on the plateau rule.** The registered smaller cell runs exactly U_L, the first length at which the calibration draws pass d ≤ 0.10. With the calibration's draw-to-draw spread in d of about 0.03, a row found at the edge may have one or more of five replicates not plateaued, and CAPACITY needs all five. A margin can be bought only with a longer registered run (one candidate more: about +33–50% of the row's cost), and at 16,384 slots a longer run also risks i\* passing 4.0. I fixed U_L with no margin because it is the only length at which the calibration cell was actually read as loaded; the alternative is the lead's to weigh.
3. **The cap.** The recorded delegation limits a raise to cases where the headroom rule "would otherwise cut registered cells or stop the study" and says a cap is never raised "to add cells, arms, updates or replicates beyond what the specification registers". §23 records the human lead's direction as the use of "fund a row", and this section would become the specification; even so, a raise from 16 to as much as 32 hours to carry rows this section adds is larger than anything recorded so far. Whether C_max = 32 is within the delegation, or needs the human lead's word, is not mine to settle.
4. **Fixing CAPACITY NOT TESTED by rule.** §8.7 row 5 and §10.1 give that direction to the human lead. Case (c) fixes the label by rule once the extension is exhausted. If the human lead's direction of §23 does not cover that, case (c) must end in a return to the human lead instead.
5. **Dropping B1 from the capacity line** when row L exists follows the precedent of the overload row. The alternative, keeping B1 as registered beside L1, gives the 4K→16K transition three steps and one more chance of a positive step class; I did not take it.
6. **A cell that has not begun to learn is "loaded" by the letter of §8.2** (load 16 at 4,096 slots read at 8,192 updates). No rule of this amendment can meet that case, and the registered rows are far past onset, but the definition has no floor and the lead may want it noted in the freeze record.
7. **T-OQ's cost is unmeasured.** Every registered-cost figure assumes twice F-OQ. T-OQ carries half of each row's cost; the rehearsal must measure it before any fundability statement is relied on.
8. **X6 needs a 24,576-fact stream and panels.** The generator takes the first F facts of the table for any F; I read that from the code and did not run it. The implementer must confirm G1 at 24,576 facts on a calibration draw before stage E1; if it cannot be generated without touching P9 code, X6 is dropped and the amendment proceeds with X8 and Y4 only.
9. **Implementation and audit.** The extension needs new code (cells, stages, the stopping rule, the row plan with U_L and U_P′) and an implementation audit before it runs; the registered-row changes need the rehearsal and its audit repeated. Neither is costed above beyond the rehearsal's 0.45 hours.
