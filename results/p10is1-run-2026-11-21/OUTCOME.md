# P10-I-S1 outcome record (ADR-0024, block M): useful capacity scaling of the trained oracle-addressed store against the dense map

Status: registered run executed once, 2026-11-21 03:08 to 12:32 (local, Panama time), at freeze `46bf55a5cc0eda11b7201c4ab777e69c6970c4cd` (plan SHA-256 `e1479e36…`, 155 cells, five replicates). Gates, timing, train and ladder COMPLETE; evaluate PAUSED once at its cap and COMPLETE after a human-lead-approved extension; baselines and throughput COMPLETE. **The registered `analysis` and `report` stages did not run: ENGINEERING STOP — ANALYSIS LOADER DEFECT.** The labels below come from the frozen analysis and report functions applied to the registered records through a disclosed corrected loader (`results/p10is1-analysis-supplement-20261121/`), **not from the registered analysis stage.** Labels independently recomputed (below). **Not accepted by the human lead yet. Astra review: NOT_PERFORMED.** Nothing here is a success claim.

This is component evidence only: recall of trained random facts, oracle-addressed, one frozen backbone (27,392 parameters), synthetic scale. It says nothing about capability parity with any reference model, about natural language, learned addressing or a language model forming queries, nor about cost or efficiency of any system.

Decision 2 (to run) was taken by the lead (Claude) under the human lead's delegation of 2026-11-18, not by him in person; its text says "about 03:25 Panama time" while its commit is timestamped 03:08:02 and the run started 03:08:15 (disclosure 6). The registered-analysis route (c) was the lead's ruling under the same delegation, taken before any outcome value was read; he may overrule it in favour of an amending freeze (disclosure 1).

## Registered labels (exactly as printed in `report/REPORT_SUPPLEMENT.md`)

**C-CAPACITY: CAPACITY-NEGATIVE** (printed bare; the analysis JSON gives `row 4`, `clause (b)`, `arms [F-OQ]`, reason "(b) every CAPACITY_SUPPORTED arm is DENSE AHEAD"). Printed beside it: "saturation outcome beside it: SATURATION-PROPORTIONAL [STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK]"; "LANE L: OMITTED — NOT LICENSED".

**C-SATURATION: SATURATION-PROPORTIONAL [STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK; arms F-OQ; EIGHT FACTS PER SLOT; 16,384→65,536 NOT TESTED — BLOCK X NOT APPROVED]**, with the printed sentence "The crowding of the fixed width-16 oracle codes grows with the fact set: a SUBPROPORTIONAL verdict is NOT A PROPERTY OF THE STORE ALONE."

**C-EFFICIENCY: EFFICIENCY-INCONCLUSIVE** (printed bare; the analysis JSON gives the reasons "E-A: F-OQ: NOT_EVALUATED, T-OQ: NOT_EVALUATED" and the same for E-T).

### What CAPACITY-NEGATIVE rests on (read this beside the label)

- It is **clause (b), carried by F-OQ alone.** Of the three outcome arms, only F-OQ is CAPACITY_SUPPORTED (a_use ≥ 0.80 at 32K/16K at U_P in all five replicates on both panels: minimum 0.907). H8 is also CAPACITY_SUPPORTED (minimum 0.861) but enters no outcome. T-OQ and F-OQ-IVF are CAPACITY_ONE_TRANSITION: both have a CAPACITY STEP in each transition, but a_use at 32K/16K falls below 0.80 (minima 0.679 and 0.516). The minima were read from the analysis JSON (step C2, `a_use_large_up`, both panels, five replicates) and equal the auditor's.
- **F-OQ's arm-level DENSE AHEAD at 32K/16K comes only from the D-BEST reading** (D-OQ's best snapshot up to its run length against F-OQ at U_P), in 5 of 5 replicates (the report prints "DENSE AHEAD (NOT AT MATCHED COMPUTE)"; the auditor's hand check gives d from −0.80 to −0.85). At equal updates and at matched compute (MU, MC-A, MC-T) F-OQ is AHEAD of the dense map at 32K/16K, by +1.7 to +2.7 bits (auditor's hand check; the analysis JSON holds the counts 0, 0, 0, 0 of five replicates with a dense lead, and 5 for D-BEST). At 8K/4K F-OQ is STORE NOT BEHIND in every reading (auditor: worst d −0.16).
- The other support is **DENSE HOLDS MORE AT SATURATION** at both loaded cells in 5 of 5 replicates (F-OQ: d_sat −1.67 to −1.77 at 8K/1K, −1.73 to −1.86 at 32K/4K, from the analysis JSON; D-OQ's a_use at U_P 0.76 to 0.78 at 8K/1K and 0.36 to 0.38 at 32K/4K; D-OQ is recorded not full at either loaded cell in any replicate (`dense_full` false; lengths 98,304 and 393,216), so its i* there is a lower bound on its value at a longer length: the dense side is understated, not overstated).
- **The label is the rule as written and is not changed. It must not be read as a dense lead at matched compute.**

### What ADR-0024 says these labels mean, and do not mean

ADR-0024 §19 (decision map): "CAPACITY-NEGATIVE (b) → on this task the dense map is the better use of the parameters; what the store offers must then be shown elsewhere (sparse updates, measured cost, storage), in studies designed for it." "Any INCONCLUSIVE → no decision on that line." SATURATION-PROPORTIONAL (ADR-0021 §8.10): "It compares two rows, so facts and slots change together; that is the definition of the line, not a confound to be removed. 'Full' means the plateau rule within the registered run length, not an asymptote. It holds for eight facts per slot only"; H8 alone cannot give it; F-OQ gives it here on both pairs read (256→1K and 1K→4K). EFFICIENCY-INCONCLUSIVE (§9.5 row 5): "otherwise", with the reason: here F-OQ and T-OQ are NOT_EVALUATED in both readings because the control step N1 is NOT_ASSESSED (F-OQ and T-OQ reach i ≥ 3.0 at their first snapshot at 2K/1K and 2K/4K, so both are left-censored); it says nothing about the speed of either map.

What none of them says (ADR-0024 §20): anything about the language model forming queries, natural language, learned addressing, or capability beyond recall of trained random facts; efficiency, latency, energy or I/O of any system; capacity above 16,384 slots (block X is not approved; "16,384→65,536 NOT TESTED"); that a SUBPROPORTIONAL verdict is a property of the store; that the store or the dense map is better "when tuned"; why the tree is behind the flat memory. Lane L is not implemented.

**The ADR's pre-registered expectation, quoted, not celebrated** (§9.3, written before any observation): "F-OQ shows capacity steps; DENSE HOLDS MORE at saturation is likely again; CAPACITY-NEGATIVE by clause (b) is the single most likely outcome unless the rate search changes the picture." The registered result matches it in all three clauses. A result that matches an expectation is not thereby validated; the dense rule that gives (b) was written stricter for the store than P10-S1's, and F-OQ's label rests on the D-BEST reading and the saturation label, as stated above. In the ADR's own words, on this task the dense map is the better use of the parameters.

## Descriptive figures (never labels)

Computed from `analysis_supplement.json` (the Δ and ρ figures and counts are the analysis function's own; the per-reading d values of the dense cells exist in the auditor's recomputation, not in the analysis JSON, and are marked so).

### Capacity steps (per arm and step: Δ_MU over the 5 replicates and both panels; verdict counts; step class; the report prints every replicate)

| arm | step | cells | Δ_MU range | replicate verdicts (of 5) | step class |
|---|---|---|---|---|---|
| F-OQ | C1 | 8K/1K→8K/4K | 2.754 to 2.821 | CAPACITY 5 | CAPACITY STEP |
| F-OQ | C2 | 32K/4K→32K/16K | 2.464 to 2.577 | CAPACITY 5 | CAPACITY STEP |
| F-OQ | N1 | 2K/1K→2K/4K | 0.016 to 0.056 | CEILING 5 | NOT LOADED |
| F-OQ | N2 | 8K/4K→8K/16K | 0.097 to 0.148 | CEILING 5 | NOT LOADED |
| F-OQ-IVF | C1 | 8K/1K→8K/4K | 1.258 to 1.363 | CAPACITY 5 | CAPACITY STEP |
| F-OQ-IVF | C2 | 32K/4K→32K/16K | 1.010 to 1.062 | CAPACITY 5 | CAPACITY STEP |
| F-OQ-IVF | N1 | 2K/1K→2K/4K | 0.266 to 0.375 | UNRESOLVED 5 | MIXED |
| F-OQ-IVF | N2 | 8K/4K→8K/16K | 1.495 to 1.585 | CAPACITY 5 | CAPACITY STEP |
| H8 | C1 | 8K/1K→8K/4K | 2.986 to 3.104 | CAPACITY 5 | CAPACITY STEP |
| H8 | C2 | 32K/4K→32K/16K | 2.914 to 2.959 | CAPACITY 5 | CAPACITY STEP |
| H8 | N1 | 2K/1K→2K/4K | 1.098 to 1.193 | CAPACITY 5 | CAPACITY STEP |
| H8 | N2 | 8K/4K→8K/16K | 1.103 to 1.203 | CAPACITY 5 | CAPACITY STEP |
| T-OQ | C1 | 8K/1K→8K/4K | 2.545 to 2.703 | CAPACITY 5 | CAPACITY STEP |
| T-OQ | C2 | 32K/4K→32K/16K | 1.408 to 1.503 | CAPACITY 5 | CAPACITY STEP |
| T-OQ | N1 | 2K/1K→2K/4K | 0.056 to 0.105 | CEILING 5 | NOT LOADED |
| T-OQ | N2 | 8K/4K→8K/16K | 0.359 to 0.502 | CEILING 3, GAIN WITHIN BUDGET ONLY 1, UNRESOLVED 1 | MIXED |

### Dense map against the store (counts of replicates of 5 with a dense lead, d ≤ −0.25 on either panel, per reading)

| arm | larger cell | MU | MC-A | MC-T | MC-C | D-BEST | cell label |
|---|---|---|---|---|---|---|---|
| F-OQ | 32K/16K | 0 | 0 | 0 | 0 | 5 | DENSE AHEAD (NOT AT MATCHED COMPUTE) |
| F-OQ | 8K/4K | 0 | 0 | 0 | 0 | 0 | STORE NOT BEHIND |
| F-OQ-IVF | 32K/16K | 5 | 4 | 4 | 4 | 5 | DENSE AHEAD |
| F-OQ-IVF | 8K/16K | 5 | 5 | 5 | 5 | 5 | DENSE AHEAD |
| F-OQ-IVF | 8K/4K | 5 | 5 | 5 | 5 | 5 | DENSE AHEAD |
| H8 | 2K/4K | 0 | 0 | 0 | 0 | 0 | STORE NOT BEHIND |
| H8 | 32K/16K | 0 | 0 | 0 | 0 | 5 | DENSE AHEAD (NOT AT MATCHED COMPUTE) |
| H8 | 8K/16K | 0 | 0 | 0 | 0 | 0 | STORE NOT BEHIND |
| H8 | 8K/4K | 5 | 5 | 5 | 5 | 5 | DENSE AHEAD |
| T-OQ | 32K/16K | 0 | 0 | 0 | 0 | 5 | DENSE AHEAD (NOT AT MATCHED COMPUTE) |
| T-OQ | 8K/4K | 5 | 4 | 5 | 5 | 5 | DENSE AHEAD |

Arm-level: F-OQ: class CAPACITY_SUPPORTED, dense label DENSE AHEAD, dense at saturation at 32K/4K, 8K/1K (5 of 5 replicates each by the report); F-OQ-IVF: class CAPACITY_ONE_TRANSITION, dense label DENSE AHEAD, dense at saturation at 32K/4K, 8K/1K (5 of 5 replicates each by the report); H8: class CAPACITY_SUPPORTED, dense label DENSE AHEAD, dense at saturation at 32K/4K, 8K/1K (5 of 5 replicates each by the report); T-OQ: class CAPACITY_ONE_TRANSITION, dense label DENSE AHEAD, dense at saturation at 32K/4K, 8K/1K (5 of 5 replicates each by the report)

### Saturation pair 1K→4K (ρ = S(4N)/S(N) over the 5 replicates and both panels; threshold 3.0 as ADR-0021 §8.10)

| arm | pair | ρ range | replicate-panel verdicts | pair class | arm class |
|---|---|---|---|---|---|
| F-OQ | 1K→4K | 3.587 to 3.827 | PROPORTIONAL 5 | PROPORTIONAL STEP | SATURATION_PROPORTIONAL_ALL_PAIRS |
| F-OQ | 256→1K | 3.648 to 3.760 | PROPORTIONAL 5 | PROPORTIONAL STEP | SATURATION_PROPORTIONAL_ALL_PAIRS |
| F-OQ-IVF | 1K→4K | 1.510 to 1.617 | SUBPROPORTIONAL 5 | SUBPROPORTIONAL STEP | SATURATION_DOES_NOT_SCALE |
| H8 | 1K→4K | 3.918 to 4.080 | PROPORTIONAL 5 | PROPORTIONAL STEP | SATURATION_PROPORTIONAL_ALL_PAIRS |
| T-OQ | 1K→4K | 2.797 to 3.180 | PROPORTIONAL 1, SUBPROPORTIONAL 4 | SUBPROPORTIONAL STEP | SATURATION_DOES_NOT_SCALE |

### Efficiency (the two readings; the dense-speed verdicts)

| reading | arm | arm class | step classes | dense speed |
|---|---|---|---|---|
| E-A | F-OQ | NOT_EVALUATED | N1: NOT_ASSESSED, N2: NOT_ASSESSED | no FASTER STEP |
| E-A | T-OQ | NOT_EVALUATED | N1: NOT_ASSESSED, N2: NO DIFFERENCE | no FASTER STEP |
| E-T | F-OQ | NOT_EVALUATED | N1: NOT_ASSESSED, N2: NOT_ASSESSED | no FASTER STEP |
| E-T | T-OQ | NOT_EVALUATED | N1: NOT_ASSESSED, N2: NO DIFFERENCE | no FASTER STEP |


### Dense-map readings at F-OQ's two dense-compared cells (auditor's hand check, `recomputation/handcheck_run1.out`; d = store minus dense in bits, negative = dense ahead; min over panels per replicate, range over the five replicates)

| cell | MU | MC-A | MC-T | D-BEST | replicates with d ≤ −0.25 |
|---|---|---|---|---|---|
| 32K/16K | +1.728 to +2.145 | +2.304 to +2.747 | +1.991 to +2.483 | −0.846 to −0.800 | MU 0, MC-A 0, MC-T 0, D-BEST 5 |
| 8K/4K | −0.148 to −0.071 | −0.088 to −0.011 | −0.138 to −0.092 | −0.160 to −0.110 | 0 in every reading |

### a_use at 32K/16K at U_P (minimum over five replicates and both panels; analysis JSON, step C2)

| arm | minimum a_use | ≥ 0.80 in all five | arm class |
|---|---|---|---|
| F-OQ | 0.907 | yes | CAPACITY_SUPPORTED |
| H8 | 0.861 | yes | CAPACITY_SUPPORTED (enters no outcome) |
| T-OQ | 0.679 | no | CAPACITY_ONE_TRANSITION |
| F-OQ-IVF | 0.516 | no | CAPACITY_ONE_TRANSITION |

### Loaded cells and ladder stops (analysis JSON)

| cell | U0 | granted (projection) | recorded U_run (whole cell stopped) | rounds |
|---|---|---|---|---|
| 2K/256 | 196,608 | 786,432 | 196,608 | stopped at U0 |
| 8K/1K | 98,304 | 393,216 | 98,304 | stopped at U0 |
| 32K/4K | 196,608 | 786,432 | 393,216 | one round beyond U0 |

NOT REACHED: 45 ladder-cell labels (nine arm-and-cell families × five replicates: D-OQ, F-OQ, H8 and T-OQ at 8K/1K and 32K/4K, F-OQ at 2K/256) carry 140 snapshots recorded NOT REACHED (2 per 32K/4K label, 4 per 8K/1K and 2K/256 label). They are not missing: the whole cell stopped (ADR-0024 §7.2; ruling 27: no per-arm early stop).

### Timing (isolated, MC-T; `timing.json`, alone, one quiet reading at the first poll) and read-path throughput (`throughput.json`; RAM, one process; descriptive only, not storage I/O, not latency)

| item | CPU seconds per update (median of 3 repeats) | spread (max−min)/median |
|---|---|---|
| D-OQ / 1024 | 0.003227 | 0.0347 |
| D-OQ / 16384 | 0.012010 | 0.0096 |
| D-OQ / 4096 | 0.004953 | 0.0179 |
| F-OQ / 1024 | 0.003929 | 0.0087 |
| F-OQ / 16384 | 0.008989 | 0.0149 |
| F-OQ / 256 | 0.003205 | 0.0011 |
| F-OQ / 4096 | 0.006726 | 0.0466 |
| H8 / 1024 | 0.002790 | 0.0030 |
| H8 / 16384 | 0.004443 | 0.0060 |
| H8 / 4096 | 0.003117 | 0.0020 |
| R2 / 16384 | 0.004345 | 0.0054 |
| R2 / 32768 | 0.006129 | 0.0060 |
| R2 / 4096 | 0.003040 | 0.0003 |
| T-OQ / 1024 | 0.008884 | 0.0002 |
| T-OQ / 16384 | 0.011270 | 0.0087 |
| T-OQ / 4096 | 0.009404 | 0.0054 |

Timing: spread bound 0.05, largest 0.0466; waited 0.09 s, charged 198.5 s; retimed: False.

| arm / facts / slots | queries/s, batch 1 (median of 5) | label | CV | queries/s, batch 128 | label | CV |
|---|---|---|---|---|---|---|
| D-OQ / 2048 / 4096 | 52554 | STABLE | 0.0015 | 157996 | STABLE | 0.0053 |
| D-OQ / 32768 / 16384 | 17231 | STABLE | 0.0005 | 39722 | STABLE | 0.0010 |
| D-OQ / 32768 / 4096 | 52882 | STABLE | 0.0008 | 157127 | STABLE | 0.0052 |
| D-OQ / 8192 / 1024 | 133220 | STABLE | 0.0012 | 568406 | STABLE | 0.0002 |
| D-OQ / 8192 / 16384 | 17334 | STABLE | 0.0004 | 39712 | STABLE | 0.0036 |
| D-OQ / 8192 / 4096 | 52489 | STABLE | 0.0019 | 157828 | STABLE | 0.0011 |
| F-OQ-IVF / 2048 / 1024 | 13147 | STABLE | 0.0043 | 138367 | STABLE | 0.0308 |
| F-OQ-IVF / 2048 / 4096 | 10084 | STABLE | 0.0012 | 50427 | STABLE | 0.0201 |
| F-OQ-IVF / 32768 / 16384 | 5314 | STABLE | 0.0028 | 21778 | STABLE | 0.0063 |
| F-OQ-IVF / 32768 / 4096 | 10096 | STABLE | 0.0036 | 48671 | STABLE | 0.0259 |
| F-OQ-IVF / 8192 / 1024 | 13292 | STABLE | 0.0024 | 119512 | STABLE | 0.0221 |
| F-OQ-IVF / 8192 / 16384 | 5322 | STABLE | 0.0021 | 21788 | STABLE | 0.0063 |
| F-OQ-IVF / 8192 / 4096 | 10068 | STABLE | 0.0020 | 48460 | STABLE | 0.0171 |
| F-OQ / 2048 / 1024 | 30379 | STABLE | 0.0131 | 195398 | STABLE | 0.0497 |
| F-OQ / 2048 / 256 | 36018 | STABLE | 0.0026 | 797208 | UNSTABLE | 0.0531 |
| F-OQ / 2048 / 4096 | 17802 | STABLE | 0.0025 | 41140 | STABLE | 0.0148 |
| F-OQ / 32768 / 16384 | 8147 | STABLE | 0.0009 | 37420 | STABLE | 0.0148 |
| F-OQ / 32768 / 4096 | 17554 | STABLE | 0.0011 | 43658 | STABLE | 0.0168 |
| F-OQ / 8192 / 1024 | 31252 | STABLE | 0.0018 | 180308 | STABLE | 0.0386 |
| F-OQ / 8192 / 16384 | 8139 | STABLE | 0.0006 | 25636 | STABLE | 0.0175 |
| F-OQ / 8192 / 4096 | 18276 | STABLE | 0.0011 | 45096 | STABLE | 0.0185 |
| H8 / 2048 / 1024 | 215492 | STABLE | 0.0041 | 4783775 | STABLE | 0.0015 |
| H8 / 2048 / 4096 | 212875 | STABLE | 0.0180 | 4727617 | STABLE | 0.0007 |
| H8 / 32768 / 16384 | 215356 | STABLE | 0.0011 | 4707965 | STABLE | 0.0007 |
| H8 / 32768 / 4096 | 215582 | STABLE | 0.0016 | 4721139 | STABLE | 0.0011 |
| H8 / 8192 / 1024 | 215272 | STABLE | 0.0020 | 4783997 | STABLE | 0.0004 |
| H8 / 8192 / 16384 | 214306 | STABLE | 0.0080 | 4687678 | STABLE | 0.0080 |
| H8 / 8192 / 4096 | 216500 | STABLE | 0.0034 | 4743441 | STABLE | 0.0005 |
| T-OQ / 2048 / 1024 | 14944 | STABLE | 0.0023 | 85150 | STABLE | 0.0330 |
| T-OQ / 2048 / 4096 | 15002 | STABLE | 0.0016 | 89324 | STABLE | 0.0236 |
| T-OQ / 32768 / 16384 | 14917 | STABLE | 0.0018 | 86068 | STABLE | 0.0213 |
| T-OQ / 32768 / 4096 | 15060 | STABLE | 0.0013 | 89938 | STABLE | 0.0217 |
| T-OQ / 8192 / 1024 | 14961 | STABLE | 0.0075 | 92532 | STABLE | 0.0265 |
| T-OQ / 8192 / 16384 | 14851 | STABLE | 0.0007 | 85874 | STABLE | 0.0227 |
| T-OQ / 8192 / 4096 | 14992 | STABLE | 0.0019 | 88363 | STABLE | 0.0206 |

Throughput: read path only, RAM, CPU, one process: not storage I/O, not latency of a language model; waited 1200 s (not charged), charged 181.3 s.

### Cost against the projection (hours; analytical projection `P10IS1-projection-v2.json` against charged, measured)

| stage | projected (h) | charged, true (h) | charged (s) |
|---|---|---|---|
| gates | 0.000 | 0.0102 | 36.63 |
| timing | 0.031 | 0.0551 | 198.53 |
| train | 5.600 | 4.5929 | 16534.44 |
| ladder | 9.584 | 1.9582 | 7049.56 |
| evaluate | 0.102 | 1.0349 | 3725.70 |
| baselines | 0.022 | 0.0073 | 26.43 |
| analysis | 0.000 | 0.0001 | 0.37 |
| report | 0.000 | 0.0000 | 0.00 |
| throughput | 0.117 | 0.0504 | 181.30 |

Charged before the freeze (H_c) 7.967 h; registered stages 7.709 h; ledger total 15.676 h of the 52 h total cap (headroom 36.32 h). Evaluate's true charge is its ledger entries without the credit (3,600.03 s + 125.67 s); the ledger's `evaluate` sum with the credit is 125.7 s and the evaluate manifest 125.7 s: both understate it. Projected total 29.89 h (analytical, includes the counting rehearsal's 6.47 h).

## Independent recomputation

By the auditor (arbor-auditor, Claude Opus 5.5 per the agent definition), 2026-11-21, own standard-library code written from ADR-0024 and ADR-0021, importing nothing from the study: `recomputation/`. Result: the three lines, every per-panel capacity verdict and Δ (MU, MC-A, MC-T, MC-C), step, arm and dense labels, ρ and saturation classes, efficiency verdicts, sparse ratios, the R2 failures (none), the ladder stops — **2,652 values compared, 0 differences** against `analysis_supplement.json`; 149 printed report rows checked, 0 differences. Engineering statuses recomputed from the run directory: gates passed, no item errors, no failed cells, 2,395 of 2,395 reads, the recorded U_run of every ladder cell equal to the stop rule recomputed from the data. The recomputation itself was tested first on the counting rehearsal (0 of 628 differences), on 18 synthetic five-replicate runs (about 43,000 values, 0 differences) and on 20,000 random efficiency cases; the registered branches those tests never reached were hand-checked (`RECOMPUTATION.md` §4). Inputs taken, not recomputed: MC-A's analytic multiply-adds per update (frozen formula run read-only); the model's evaluation (the records' counts are taken as recorded); H8 annotations, the counted-work table and the throughput figures are printed only. The auditor lists its own errors and misses in `RECOMPUTATION.md` §8, including that its own loader crashed on the same `baselines/manifest.json` and the study's `build_registry` was not connected to that. The recomputation is evidence, not Astra validation and not acceptance.

## Disclosures

1. **The labels come through a disclosed corrected loader; the registered analysis and report stages are ENGINEERING STOP — ANALYSIS LOADER DEFECT.** The frozen `build_registry` reads every `baselines/*.json` as a baseline record and the baselines stage manifest `baselines/manifest.json` matches; the registered analysis stage was launched once, at 10:45 local, and crashed inside `build_registry` before `analyze` (no value was produced; 0.37 s charged to the `analysis` key); the report stage, launched three seconds later, crashed on the missing `analysis/analysis.json` (0.0005 s). Both tracebacks (truncated tails: the captured output is cut to its last 1,500 bytes) are in `ENGINEERING_STOP_ANALYSIS_LOADER_DEFECT.json`. The defect recurs after baselines COMPLETE, so the registered analysis cannot run under the frozen code. The lead ruled route (c), an out-of-tree driver calling the frozen `build_registry` (on a path object whose `baselines/` lists baseline record files only), `analyze` and `render` unchanged, before any outcome value was read, following the P10-S1 ADR-0021 §25.21 precedent (`docs/decisions/ADR-0024-addendum-analysis-loader-defect.md`). **The human lead may overrule it in favour of an amending freeze (route (a))**, which would run the registered stages. The driver ran once (exit 0, 2026-11-21 12:34 local; its SHA-256 `4e89db6c…` equals the committed file's); the supplement is in this folder with its manifest. Why the rehearsal, tests and audits missed it: see the addendum §2.
2. **Evaluate's cap and the extension.** Evaluate ran 09:45:37 to 10:45:38 and stopped at its frozen 1.0 h cap (ledger 3,600.03 s) with, as the lead reports, 98 of 110 cells done (74 in the first 15 minutes) and 12 not started; the cause was inferred (the 18 GiB aggregate memory guard, with available memory near 17.7 GiB while other work ran), not measured during the stall, and the first run's manifest was overwritten so the 98 cannot be checked from the records. The human lead approved +1 hour in person on 2026-11-21 ("Approve 1 h", `results/p10is1-evaluate-cap-extension-20261121/APPROVAL.md`, as relayed). It is carried as a ledger credit of −3,600 s on `evaluate` and an equal offset on `evaluate-cap-extension-offset`; the frozen plan, config and code are untouched and the total cap is unchanged. **Consequences:** the ledger no longer gives evaluate's per-stage time; the frozen report prints an evaluate cap of 1.0 h against an effective 2.0 h; **evaluate's true charged time is the ledger's evaluate entries without the credit: 3,600.03 + 125.67 = 3,725.7 s (1.035 h)**, not the manifest's 125.7 s (a manifest holds only a stage's last invocation; the earlier addendum text and `OWED_DISCLOSURES.md` item 3 said otherwise and are corrected in `ADR-0024-addendum-evaluate-cap-extension-correction.md`; changelog row 28 repeats the false statement). Total charged 15.676 h of the 52 h total cap (7.966 h before the freeze, 7.709 h by the registered stages). Evaluate took 1.035 h against 0.102 h projected. Full text: `OWED_DISCLOSURES.md`.
3. **The lead's stage loop went on after the pause.** Baselines was launched at 10:45:38 and returned PAUSED (shared cap key spent) having charged 0.0075 s (changelog row 27 says "nothing charged"); analysis (10:45:42, exit 1, 0.3726 s) and report (10:45:45, exit 1, 0.0005 s) were then launched and crashed (disclosure 1); none wrote a record (the run directory holds no `analysis/` or `report/` content).
4. **Machine sharing during train, ladder and the first evaluate attempt** (as reported by the lead; not independently verifiable from the run records): the human at the machine from about 09:37 (a Colima VM of about 8 GiB, browsers), the ArborML Lab session (at most four niced cores), and the lead's own audit agents and a full test suite beside the run. **C-SATURATION does not depend on wall time** (it reads trained-model correctness counts and update counts). **The quantities that depend on CPU seconds are:** the timing stage (MC-T, and MC-C, which is built on it), the E-T reading of the efficiency line, and the throughput stage; **the timing and throughput stages ran alone** under the study's quiet rule (disclosure 5). C-CAPACITY reads Δ_MC in MC-A, MC-T and MC-C in its capacity-step verdicts (§9.1 row 4) and MC-T in STORE NOT BEHIND, so it does use the timing stage's CPU seconds: F-OQ's Δ_MC are 2.24 to 2.82 in MC-A, 2.32 to 2.70 in MC-T and 2.24 to 2.70 in MC-C (steps C1 and C2, both panels, five replicates) against the 0.5 threshold, with MC-T multipliers 1.712 (C1) and 1.336 (C2); a margin that the timing spread (0.0466 at most) cannot close. F-OQ's dense lead (D-BEST) uses no cost reading. The efficiency line is INCONCLUSIVE in E-A and E-T alike because N1 is not assessable.
5. **The quiet rule and the Lab session.** Timing ran 03:08:57 to 03:12:16 local: one quiet reading at the first poll (one-minute load 1.31, five-minute 1.41, limit L = 2.17, input idle 17,909 s, six Claude processes, no tool-call shell, no other study process), 21 child-watch ticks without a failure, no measurement discarded, no re-timing; the largest timing spread 0.0466 (F-OQ at 4,096 slots) against the 0.05 bound. Throughput ran 12:09:06 to 12:32:08: the first poll failed (input idle 0 s, loads 2.29 and 5.50), the second failed (idle 558 s, five-minute 2.23), the third at 12:29:06 passed (idle 1,158 s, loads 1.26 and 1.51, limit 2.17); 1,200 s waited (not charged), 181.3 s charged, 19 watch ticks without a failure, no measurement discarded. The same 11 Claude process ids stood through all three polls and the measurement (pids 369, 370, 2786, 2787, 2788, 40449, 54306, 63224, 63225, 65713, 99328: other Claude sessions were present, idle; the full record is in the run directory). Colima was stopped 12:01–12:32. The Lab session's statements, as the lead relays them: silent from 23:11 (2026-11-20) to 09:17; the lead's end message of 03:12 was never delivered (the session was gone); quiet 12:09–12:32. Peer-session statements are words, not enforced controls (see also `results/p10is1-quiet-baseline/DISCLOSURE.md`).
6. **Decision 2** was taken by the lead under the 2026-11-18 delegation (`results/p10is1-freeze-2026-11-21/DECISION_2.md`); its text says "about 03:25 Panama time"; its commit is timestamped 03:08:02 −05:00 and the gates stage began 03:08:15, so the run started before the time the text states.
7. **The ladder** charged 7,049.6 s (1.96 h) against 9.584 h projected (train 4.593 h against 5.600 h projected). 45 ladder-cell labels carry NOT REACHED snapshots (140 snapshots; table above). **The ladder's continuation path ran for the first time in this registered run**: 32K/4K went one round past U0 to 393,216, and the recomputed stop equals the recorded one; no rehearsal had exercised it (the counting rehearsal's ladder stopped at round 0).
8. **Commits made in this worktree while the run was paused** (10:45 to 12:03): `2506c99`, `d5720ea`, `4c6754e`, `e22ae49`; none touches `studies/`, `configs/`, `src/` or `uv.lock` (checked: no such path in the diff from the Decision 2 commit `76185ef` to HEAD before this record); the registered launches' own preconditions passed at each resumed stage (they ran), and a read-only copy of the same checks (`verify_resume_identity.py`) passed at `2506c99`, `4c6754e` and `e22ae49`.
9. **How panels combine in the dense-speed label.** The frozen reading counts a replicate for a dense lead if either panel meets the condition (ADR-0024 §9.2, review row 5), and u_T handling of a dependence-failing first hit follows the frozen code. The lead ruled that the frozen reading is registered and that differences of interpretation are disclosures only (the auditor's words, `RECOMPUTATION.md` §8 item 3). **No dense-speed label occurs in this result** (no FASTER-STEP cell is assessed). The text of the lead's ruling and of the auditor's limit on it was not in the records given to the author of this record: pending the lead's text.
10. **The eight pool/worker tests** that could not run on low memory ran on 2026-11-21 with 22.79 GiB available (measured as the study measures it): 8 passed in 23 s (`test_f2_pool_caps…`, `test_f2_and_f12…`, `test_f4_the_pool…`, `test_f4_the_cumulative…`, `test_f4_cmd_calibrate…`, `test_identity_exit…`, `test_environment_errors…`, `test_hour_caps…`); the whole S1 pattern (`tests/test_p10is1_*.py`), pool tests included, then ran with the files of this record in place: **315 passed, 7 skipped** (the same 7 as in every earlier run of this suite); ruff and `mypy src/arborlm` clean.
11. **Earlier S1 disclosures:** `results/p10is1-quiet-baseline/DISCLOSURE.md` (machine sharing at the baseline; attempt 1 discarded for a Claude process change; accepted baseline L = 2.17, application and Claude Code present) and the parameter changelog rows 20 (quiet rule), 21 (measured `[quiet]`, second projection with `total_hours` 51 → 52 from the incomplete rehearsal's 1.2628 h), 22 (the old candidate plan set aside by hand), 23 (freeze and Decision 2), 27 (evaluate cap) and 28 (the ledger carriage and the loader defect). Rows 27 and 28 contain the two statements corrected in disclosures 2 and 3 above; the changelog is the lead's file and is not edited here.
12. **Other things a reviewer should see.**
    (a) **What the frozen report omits that the ADR asks for:** C-CAPACITY is printed bare (no clause (b), no carrying arm F-OQ, no reason, no "1,024 TO 16,384 SLOTS", which §9.3 requires; the analysis JSON holds them and the label's header above states them); C-EFFICIENCY is printed bare (no reason, no sizes "SIZES 1,024–16,384"); the capacity-step dense labels carry counts per reading but not the d values per reading or D-OQ's a_use (§9.2; D-OQ's a_use is printed only at the saturation cells; the per-reading d values are in the auditor's hand check, the a_use at the capacity-step dense cells is not given here); the throughput section prints the state MEASURED and no figures (given above from `throughput.json`); the separability figures of ADR-0021 §8.10 are not printed.
    (b) **The report prints the §10 table "labels that cannot be reached without measured CPU cost" in every report, although MC-T was measured** (`mct_measured: true`; no 'MEASURED COST NOT AVAILABLE' tail on any label): it must not be read as MC-T missing.
    (c) The caps line of the report shows the plan's figures (evaluate 1.0 h).
    (d) Analysis status COMPLETE, refused false, no item errors, 0 reference dependence failures, R2 table "no condition is unqualified at a fraction".
    (e) Dense DENSE AHEAD labels for T-OQ and F-OQ-IVF (8K/4K, 32K/16K, 8K/16K) and the sparse label AHEAD (T-OQ against F-OQ-IVF) are descriptive and enter no outcome here; H8's cells are printed with its annotations (UNDERTRAINED-AT-U_P at 2K/1K, 8K/4K, 32K/16K; NOT CALIBRATED at 8K/1K, 32K/4K) and enter none.
    (f) The static `ADR-0024` rule for "DENSE AHEAD" counts any one reading including D-BEST; a rule requiring matched compute would not have given F-OQ DENSE AHEAD at 32K/16K. That is the rule's, registered, and stated here only so the label is not read as more.
    (g) The timing spread margin (0.0466 of 0.05), the evaluate overrun against its projection (ten times), and the two statements corrected in the changelog rows are the figures a reviewer is most likely to want.

## Files

`REPORT_SUPPLEMENT.md`, `analysis_supplement.json`, `ENGINEERING_STOP_ANALYSIS_LOADER_DEFECT.json`, `SUPPLEMENT_MANIFEST.json`: copies from `experiments/P10IS1-pre-20261118-analysis-supplement/` (SHA-256 equal to the manifest's). `stage_manifests/`: each stage's last-invocation manifest (gates, timing, train, ladder, evaluate, baselines, throughput; a manifest holds only the last invocation). `ledger.json` and `ledger.before-evaluate-cap-extension.json`: the run ledger and its pre-image (the pre-image is a prefix of the ledger). `timing.json`, `throughput.json`: the stage records. `recomputation/`: the auditor's folder copied from `experiments/_scratch/p10is1_recomputation_record_20261121/` (its `RECOMPUTATION.md` is the record; nine `.py` files carry a first line `# ruff: noqa` that the repository's lint needed, so their SHA-256 differ from the folder's `SHA256SUMS.txt` by that line only). `audits/`: the three cap-extension and loader audits (`AUDIT_P10IS1_CAP_EXTENSION{,_2,_3}.md`); the pre-freeze audit is in `results/p10is1-freeze-2026-11-21/AUDIT_PREFREEZE_3.md`. The run directory (`experiments/P10IS1-pre-20261118`) is git-ignored.

`Astra review: NOT_PERFORMED`
