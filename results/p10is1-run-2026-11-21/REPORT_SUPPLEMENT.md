> **frozen analysis function on the registered records, through a disclosed corrected loader — not the registered analysis stage**
> Registered analysis and report stages: ENGINEERING STOP — ANALYSIS LOADER DEFECT. See docs/decisions/ADR-0024-addendum-analysis-loader-defect.md.

# P10-I-S1 block M report (ADR-0024)
_Run: P10IS1-pre-20261118 (registered). Every label carries: STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK. Lane L and block X are not implemented: 16,384→65,536 NOT TESTED — BLOCK X NOT APPROVED._

Caps (the plan's figures, in charged hours): analysis_hours 1.0, calibration_hours 20.0, evaluate_hours 1.0, rehearsal_hours 13.0, throughput_hours 1.0, timing_hours 1.0, total_hours 52.0, train_hours 31.0

Status: **COMPLETE**
Counts: 155 planned cells (cells); 2395 read records of 2395 expected (reads; a cell has one read per snapshot, F-OQ cells two); 45 ladder-cell labels with snapshots recorded NOT REACHED (cells).

## C-CAPACITY
_Run: P10IS1-pre-20261118 (registered); stage: analysis (capacity) (the registered run's records)._

**CAPACITY-NEGATIVE**
saturation outcome beside it: SATURATION-PROPORTIONAL [STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK]
LANE L: OMITTED — NOT LICENSED

### F-OQ: arm class CAPACITY_SUPPORTED [STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK]; arm-level dense label DENSE AHEAD; a_use >= 0.80 at 32K/16K at U_P in all 5 replicates: True

| step | replicate | verdict | d_MU (A) | d_MU (B) | smaller cell full | smaller loaded | U_run smaller | U_run larger |
|---|---|---|---|---|---|---|---|---|
| C1 | 1 | CAPACITY | 2.791 | 2.791 | True | True | 98304 | 49152 |
| C1 | 2 | CAPACITY | 2.758 | 2.754 | True | True | 98304 | 49152 |
| C1 | 3 | CAPACITY | 2.821 | 2.820 | True | True | 98304 | 49152 |
| C1 | 4 | CAPACITY | 2.756 | 2.758 | True | True | 98304 | 49152 |
| C1 | 5 | CAPACITY | 2.795 | 2.796 | True | True | 98304 | 49152 |
| N1 | 1 | CEILING | 0.037 | 0.037 | True | False | 49152 | 49152 |
| N1 | 2 | CEILING | 0.016 | 0.016 | True | False | 49152 | 49152 |
| N1 | 3 | CEILING | 0.050 | 0.056 | True | False | 49152 | 49152 |
| N1 | 4 | CEILING | 0.016 | 0.016 | True | False | 49152 | 49152 |
| N1 | 5 | CEILING | 0.043 | 0.043 | True | False | 49152 | 49152 |
| C2 | 1 | CAPACITY | 2.577 | 2.576 | True | True | 393216 | 49152 |
| C2 | 2 | CAPACITY | 2.494 | 2.496 | True | True | 393216 | 49152 |
| C2 | 3 | CAPACITY | 2.514 | 2.511 | True | True | 393216 | 49152 |
| C2 | 4 | CAPACITY | 2.521 | 2.520 | True | True | 393216 | 49152 |
| C2 | 5 | CAPACITY | 2.464 | 2.466 | True | True | 393216 | 49152 |
| N2 | 1 | CEILING | 0.128 | 0.128 | True | False | 49152 | 49152 |
| N2 | 2 | CEILING | 0.147 | 0.147 | True | False | 49152 | 49152 |
| N2 | 3 | CEILING | 0.137 | 0.138 | True | False | 49152 | 49152 |
| N2 | 4 | CEILING | 0.148 | 0.143 | True | False | 49152 | 49152 |
| N2 | 5 | CEILING | 0.100 | 0.097 | True | False | 49152 | 49152 |

step classes: C1: CAPACITY STEP [STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK]; N1: NOT LOADED; C2: CAPACITY STEP [STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK]; N2: NOT LOADED
- dense, larger cell 8K/4K: STORE NOT BEHIND [STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK]; replicates holding a dense lead (d <= -0.25 on either panel), per reading (cells of 5 replicates): MU: 0, MC-A: 0, MC-T: 0, MC-C: 0, D-BEST: 0
- dense, larger cell 32K/16K: DENSE AHEAD (NOT AT MATCHED COMPUTE); replicates holding a dense lead (d <= -0.25 on either panel), per reading (cells of 5 replicates): MU: 0, MC-A: 0, MC-T: 0, MC-C: 0, D-BEST: 5
- dense at saturation, loaded cell 8K/1K: DENSE HOLDS MORE AT SATURATION; replicates with a dense lead: 5; r1: arm length 98304, D-OQ length 98304, d_sat -1.730/-1.733, d_sat at the shorter length -1.730/-1.733, D-OQ a_use at U_P 0.774/0.772; r2: arm length 98304, D-OQ length 98304, d_sat -1.694/-1.692, d_sat at the shorter length -1.694/-1.692, D-OQ a_use at U_P 0.781/0.778; r3: arm length 98304, D-OQ length 98304, d_sat -1.713/-1.711, d_sat at the shorter length -1.713/-1.711, D-OQ a_use at U_P 0.763/0.763; r4: arm length 98304, D-OQ length 98304, d_sat -1.670/-1.667, d_sat at the shorter length -1.670/-1.667, D-OQ a_use at U_P 0.769/0.769; r5: arm length 98304, D-OQ length 98304, d_sat -1.763/-1.766, d_sat at the shorter length -1.763/-1.766, D-OQ a_use at U_P 0.783/0.783
- dense at saturation, loaded cell 32K/4K: DENSE HOLDS MORE AT SATURATION; replicates with a dense lead: 5; r1: arm length 131072, D-OQ length 393216, d_sat -1.731/-1.729, d_sat at the shorter length -1.402/-1.399, D-OQ a_use at U_P 0.361/0.360; r2: arm length 98304, D-OQ length 393216, d_sat -1.792/-1.793, d_sat at the shorter length -1.284/-1.288, D-OQ a_use at U_P 0.376/0.376; r3: arm length 131072, D-OQ length 393216, d_sat -1.748/-1.749, d_sat at the shorter length -1.424/-1.426, D-OQ a_use at U_P 0.382/0.382; r4: arm length 98304, D-OQ length 393216, d_sat -1.859/-1.859, d_sat at the shorter length -1.308/-1.306, D-OQ a_use at U_P 0.372/0.372; r5: arm length 98304, D-OQ length 393216, d_sat -1.762/-1.763, d_sat at the shorter length -1.269/-1.270, D-OQ a_use at U_P 0.365/0.365

### F-OQ-IVF: arm class CAPACITY_ONE_TRANSITION [STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK]; arm-level dense label DENSE AHEAD; a_use >= 0.80 at 32K/16K at U_P in all 5 replicates: False

| step | replicate | verdict | d_MU (A) | d_MU (B) | smaller cell full | smaller loaded | U_run smaller | U_run larger |
|---|---|---|---|---|---|---|---|---|
| C1 | 1 | CAPACITY | 1.293 | 1.300 | True | True | 98304 | 49152 |
| C1 | 2 | CAPACITY | 1.258 | 1.262 | True | True | 98304 | 49152 |
| C1 | 3 | CAPACITY | 1.295 | 1.289 | True | True | 98304 | 49152 |
| C1 | 4 | CAPACITY | 1.296 | 1.297 | True | True | 98304 | 49152 |
| C1 | 5 | CAPACITY | 1.357 | 1.363 | True | True | 98304 | 49152 |
| N1 | 1 | UNRESOLVED | 0.370 | 0.375 | True | False | 49152 | 49152 |
| N1 | 2 | UNRESOLVED | 0.270 | 0.266 | True | False | 49152 | 49152 |
| N1 | 3 | UNRESOLVED | 0.348 | 0.343 | True | False | 49152 | 49152 |
| N1 | 4 | UNRESOLVED | 0.305 | 0.305 | True | False | 49152 | 49152 |
| N1 | 5 | UNRESOLVED | 0.350 | 0.350 | True | False | 49152 | 49152 |
| C2 | 1 | CAPACITY | 1.017 | 1.018 | True | True | 393216 | 49152 |
| C2 | 2 | CAPACITY | 1.057 | 1.058 | True | True | 393216 | 49152 |
| C2 | 3 | CAPACITY | 1.062 | 1.061 | True | True | 393216 | 49152 |
| C2 | 4 | CAPACITY | 1.010 | 1.010 | True | True | 393216 | 49152 |
| C2 | 5 | CAPACITY | 1.033 | 1.030 | True | True | 393216 | 49152 |
| N2 | 1 | CAPACITY | 1.585 | 1.576 | True | True | 49152 | 49152 |
| N2 | 2 | CAPACITY | 1.565 | 1.567 | True | True | 49152 | 49152 |
| N2 | 3 | CAPACITY | 1.521 | 1.524 | True | True | 49152 | 49152 |
| N2 | 4 | CAPACITY | 1.582 | 1.582 | True | True | 49152 | 49152 |
| N2 | 5 | CAPACITY | 1.500 | 1.495 | True | True | 49152 | 49152 |

step classes: C1: CAPACITY STEP [STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK]; N1: MIXED; C2: CAPACITY STEP [STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK]; N2: CAPACITY STEP [STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK]
- dense, larger cell 8K/4K: DENSE AHEAD; replicates holding a dense lead (d <= -0.25 on either panel), per reading (cells of 5 replicates): MU: 5, MC-A: 5, MC-T: 5, MC-C: 5, D-BEST: 5
- dense, larger cell 32K/16K: DENSE AHEAD; replicates holding a dense lead (d <= -0.25 on either panel), per reading (cells of 5 replicates): MU: 5, MC-A: 4, MC-T: 4, MC-C: 4, D-BEST: 5
- dense, larger cell 8K/16K: DENSE AHEAD; replicates holding a dense lead (d <= -0.25 on either panel), per reading (cells of 5 replicates): MU: 5, MC-A: 5, MC-T: 5, MC-C: 5, D-BEST: 5
- dense at saturation, loaded cell 8K/1K: DENSE HOLDS MORE AT SATURATION; replicates with a dense lead: 5; r1: arm length 98304, D-OQ length 98304, d_sat -2.509/-2.511, d_sat at the shorter length -2.509/-2.511, D-OQ a_use at U_P 0.774/0.772; r2: arm length 98304, D-OQ length 98304, d_sat -2.498/-2.496, d_sat at the shorter length -2.498/-2.496, D-OQ a_use at U_P 0.781/0.778; r3: arm length 98304, D-OQ length 98304, d_sat -2.494/-2.491, d_sat at the shorter length -2.494/-2.491, D-OQ a_use at U_P 0.763/0.763; r4: arm length 98304, D-OQ length 98304, d_sat -2.455/-2.454, d_sat at the shorter length -2.455/-2.454, D-OQ a_use at U_P 0.769/0.769; r5: arm length 98304, D-OQ length 98304, d_sat -2.644/-2.646, d_sat at the shorter length -2.644/-2.646, D-OQ a_use at U_P 0.783/0.783
- dense at saturation, loaded cell 32K/4K: DENSE HOLDS MORE AT SATURATION; replicates with a dense lead: 5; r1: arm length 98304, D-OQ length 393216, d_sat -3.345/-3.342, d_sat at the shorter length -2.811/-2.808, D-OQ a_use at U_P 0.361/0.360; r2: arm length 98304, D-OQ length 393216, d_sat -3.337/-3.337, d_sat at the shorter length -2.829/-2.832, D-OQ a_use at U_P 0.376/0.376; r3: arm length 98304, D-OQ length 393216, d_sat -3.344/-3.343, d_sat at the shorter length -2.828/-2.826, D-OQ a_use at U_P 0.382/0.382; r4: arm length 98304, D-OQ length 393216, d_sat -3.384/-3.383, d_sat at the shorter length -2.833/-2.830, D-OQ a_use at U_P 0.372/0.372; r5: arm length 98304, D-OQ length 393216, d_sat -3.327/-3.326, d_sat at the shorter length -2.833/-2.833, D-OQ a_use at U_P 0.365/0.365

### T-OQ: arm class CAPACITY_ONE_TRANSITION [STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK]; arm-level dense label DENSE AHEAD; a_use >= 0.80 at 32K/16K at U_P in all 5 replicates: False

| step | replicate | verdict | d_MU (A) | d_MU (B) | smaller cell full | smaller loaded | U_run smaller | U_run larger |
|---|---|---|---|---|---|---|---|---|
| C1 | 1 | CAPACITY | 2.557 | 2.545 | True | True | 98304 | 49152 |
| C1 | 2 | CAPACITY | 2.676 | 2.676 | True | True | 98304 | 49152 |
| C1 | 3 | CAPACITY | 2.700 | 2.703 | True | True | 98304 | 49152 |
| C1 | 4 | CAPACITY | 2.632 | 2.638 | True | True | 98304 | 49152 |
| C1 | 5 | CAPACITY | 2.597 | 2.592 | True | True | 98304 | 49152 |
| N1 | 1 | CEILING | 0.105 | 0.105 | True | False | 49152 | 49152 |
| N1 | 2 | CEILING | 0.069 | 0.063 | True | False | 49152 | 49152 |
| N1 | 3 | CEILING | 0.078 | 0.078 | True | False | 49152 | 49152 |
| N1 | 4 | CEILING | 0.056 | 0.056 | True | False | 49152 | 49152 |
| N1 | 5 | CEILING | 0.087 | 0.087 | True | False | 49152 | 49152 |
| C2 | 1 | CAPACITY | 1.452 | 1.452 | True | True | 393216 | 49152 |
| C2 | 2 | CAPACITY | 1.410 | 1.408 | True | True | 393216 | 49152 |
| C2 | 3 | CAPACITY | 1.464 | 1.463 | True | True | 393216 | 49152 |
| C2 | 4 | CAPACITY | 1.433 | 1.433 | True | True | 393216 | 49152 |
| C2 | 5 | CAPACITY | 1.503 | 1.503 | True | True | 393216 | 49152 |
| N2 | 1 | GAIN WITHIN BUDGET ONLY | 0.500 | 0.502 | True | False | 49152 | 49152 |
| N2 | 2 | CEILING | 0.455 | 0.458 | True | False | 49152 | 49152 |
| N2 | 3 | CEILING | 0.446 | 0.444 | True | False | 49152 | 49152 |
| N2 | 4 | UNRESOLVED | 0.439 | 0.439 | True | False | 49152 | 49152 |
| N2 | 5 | CEILING | 0.359 | 0.363 | True | False | 49152 | 49152 |

step classes: C1: CAPACITY STEP [STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK]; N1: NOT LOADED; C2: CAPACITY STEP [STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK]; N2: MIXED
- dense, larger cell 8K/4K: DENSE AHEAD; replicates holding a dense lead (d <= -0.25 on either panel), per reading (cells of 5 replicates): MU: 5, MC-A: 4, MC-T: 5, MC-C: 5, D-BEST: 5
- dense, larger cell 32K/16K: DENSE AHEAD (NOT AT MATCHED COMPUTE); replicates holding a dense lead (d <= -0.25 on either panel), per reading (cells of 5 replicates): MU: 0, MC-A: 0, MC-T: 0, MC-C: 0, D-BEST: 5
- dense at saturation, loaded cell 8K/1K: DENSE HOLDS MORE AT SATURATION; replicates with a dense lead: 5; r1: arm length 98304, D-OQ length 98304, d_sat -1.902/-1.900, d_sat at the shorter length -1.902/-1.900, D-OQ a_use at U_P 0.774/0.772; r2: arm length 98304, D-OQ length 98304, d_sat -1.997/-1.996, d_sat at the shorter length -1.997/-1.996, D-OQ a_use at U_P 0.781/0.778; r3: arm length 98304, D-OQ length 98304, d_sat -1.984/-1.980, d_sat at the shorter length -1.984/-1.980, D-OQ a_use at U_P 0.763/0.763; r4: arm length 98304, D-OQ length 98304, d_sat -1.944/-1.941, d_sat at the shorter length -1.944/-1.941, D-OQ a_use at U_P 0.769/0.769; r5: arm length 98304, D-OQ length 98304, d_sat -1.984/-1.988, d_sat at the shorter length -1.984/-1.988, D-OQ a_use at U_P 0.783/0.783
- dense at saturation, loaded cell 32K/4K: DENSE HOLDS MORE AT SATURATION; replicates with a dense lead: 5; r1: arm length 98304, D-OQ length 393216, d_sat -2.413/-2.411, d_sat at the shorter length -1.879/-1.876, D-OQ a_use at U_P 0.361/0.360; r2: arm length 131072, D-OQ length 393216, d_sat -2.334/-2.334, d_sat at the shorter length -1.958/-1.958, D-OQ a_use at U_P 0.376/0.376; r3: arm length 131072, D-OQ length 393216, d_sat -2.389/-2.388, d_sat at the shorter length -2.064/-2.066, D-OQ a_use at U_P 0.382/0.382; r4: arm length 98304, D-OQ length 393216, d_sat -2.453/-2.453, d_sat at the shorter length -1.902/-1.901, D-OQ a_use at U_P 0.372/0.372; r5: arm length 98304, D-OQ length 393216, d_sat -2.414/-2.415, d_sat at the shorter length -1.921/-1.922, D-OQ a_use at U_P 0.365/0.365

### H8: arm class CAPACITY_SUPPORTED [STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK] (printed with its annotations; enters no outcome); arm-level dense label DENSE AHEAD; a_use >= 0.80 at 32K/16K at U_P in all 5 replicates: True

| step | replicate | verdict | d_MU (A) | d_MU (B) | smaller cell full | smaller loaded | U_run smaller | U_run larger |
|---|---|---|---|---|---|---|---|---|
| C1 | 1 | CAPACITY | 2.996 | 3.008 | True | True | 98304 | 49152 |
| C1 | 2 | CAPACITY | 2.986 | 2.999 | True | True | 98304 | 49152 |
| C1 | 3 | CAPACITY | 3.045 | 3.080 | True | True | 98304 | 49152 |
| C1 | 4 | CAPACITY | 3.104 | 3.098 | True | True | 98304 | 49152 |
| C1 | 5 | CAPACITY | 3.011 | 3.016 | True | True | 98304 | 49152 |
| N1 | 1 | CAPACITY | 1.155 | 1.155 | True | True | 49152 | 49152 |
| N1 | 2 | CAPACITY | 1.193 | 1.193 | True | True | 49152 | 49152 |
| N1 | 3 | CAPACITY | 1.106 | 1.109 | True | True | 49152 | 49152 |
| N1 | 4 | CAPACITY | 1.106 | 1.098 | True | True | 49152 | 49152 |
| N1 | 5 | CAPACITY | 1.193 | 1.193 | True | True | 49152 | 49152 |
| C2 | 1 | CAPACITY | 2.952 | 2.950 | True | True | 393216 | 49152 |
| C2 | 2 | CAPACITY | 2.935 | 2.936 | True | True | 393216 | 49152 |
| C2 | 3 | CAPACITY | 2.957 | 2.959 | True | True | 393216 | 49152 |
| C2 | 4 | CAPACITY | 2.924 | 2.925 | True | True | 393216 | 49152 |
| C2 | 5 | CAPACITY | 2.914 | 2.917 | True | True | 393216 | 49152 |
| N2 | 1 | CAPACITY | 1.186 | 1.182 | True | True | 49152 | 49152 |
| N2 | 2 | CAPACITY | 1.203 | 1.202 | True | True | 49152 | 49152 |
| N2 | 3 | CAPACITY | 1.130 | 1.121 | True | True | 49152 | 49152 |
| N2 | 4 | CAPACITY | 1.103 | 1.105 | True | True | 49152 | 49152 |
| N2 | 5 | CAPACITY | 1.175 | 1.178 | True | True | 49152 | 49152 |

step classes: C1: CAPACITY STEP [STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK]; N1: CAPACITY STEP [STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK]; C2: CAPACITY STEP [STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK]; N2: CAPACITY STEP [STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK]
- dense, larger cell 8K/4K: DENSE AHEAD; replicates holding a dense lead (d <= -0.25 on either panel), per reading (cells of 5 replicates): MU: 5, MC-A: 5, MC-T: 5, MC-C: 5, D-BEST: 5
- dense, larger cell 2K/4K: STORE NOT BEHIND [STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK]; replicates holding a dense lead (d <= -0.25 on either panel), per reading (cells of 5 replicates): MU: 0, MC-A: 0, MC-T: 0, MC-C: 0, D-BEST: 0
- dense, larger cell 32K/16K: DENSE AHEAD (NOT AT MATCHED COMPUTE); replicates holding a dense lead (d <= -0.25 on either panel), per reading (cells of 5 replicates): MU: 0, MC-A: 0, MC-T: 0, MC-C: 0, D-BEST: 5
- dense, larger cell 8K/16K: STORE NOT BEHIND [STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK]; replicates holding a dense lead (d <= -0.25 on either panel), per reading (cells of 5 replicates): MU: 0, MC-A: 0, MC-T: 0, MC-C: 0, D-BEST: 0
- dense at saturation, loaded cell 8K/1K: DENSE HOLDS MORE AT SATURATION; replicates with a dense lead: 5; r1: arm length 98304, D-OQ length 98304, d_sat -3.191/-3.199, d_sat at the shorter length -3.191/-3.199, D-OQ a_use at U_P 0.774/0.772; r2: arm length 98304, D-OQ length 98304, d_sat -3.221/-3.221, d_sat at the shorter length -3.221/-3.221, D-OQ a_use at U_P 0.781/0.778; r3: arm length 98304, D-OQ length 98304, d_sat -3.203/-3.206, d_sat at the shorter length -3.203/-3.206, D-OQ a_use at U_P 0.763/0.763; r4: arm length 98304, D-OQ length 98304, d_sat -3.210/-3.205, d_sat at the shorter length -3.210/-3.205, D-OQ a_use at U_P 0.769/0.769; r5: arm length 98304, D-OQ length 98304, d_sat -3.332/-3.338, d_sat at the shorter length -3.332/-3.338, D-OQ a_use at U_P 0.783/0.783
- dense at saturation, loaded cell 32K/4K: DENSE HOLDS MORE AT SATURATION; replicates with a dense lead: 5; r1: arm length 98304, D-OQ length 393216, d_sat -3.105/-3.103, d_sat at the shorter length -2.571/-2.568, D-OQ a_use at U_P 0.361/0.360; r2: arm length 98304, D-OQ length 393216, d_sat -3.123/-3.124, d_sat at the shorter length -2.616/-2.619, D-OQ a_use at U_P 0.376/0.376; r3: arm length 98304, D-OQ length 393216, d_sat -3.098/-3.098, d_sat at the shorter length -2.582/-2.580, D-OQ a_use at U_P 0.382/0.382; r4: arm length 98304, D-OQ length 393216, d_sat -3.142/-3.142, d_sat at the shorter length -2.591/-2.590, D-OQ a_use at U_P 0.372/0.372; r5: arm length 98304, D-OQ length 393216, d_sat -3.096/-3.097, d_sat at the shorter length -2.602/-2.604, D-OQ a_use at U_P 0.365/0.365

H8 annotations: {'2K/1K': 'UNDERTRAINED-AT-U_P', '8K/1K': 'H8 NOT CALIBRATED AT U_P AT 8K/1K', '8K/4K': 'UNDERTRAINED-AT-U_P', '32K/4K': 'H8 NOT CALIBRATED AT U_P AT 32K/4K', '32K/16K': 'UNDERTRAINED-AT-U_P'}; KEY-LEARNING-LIMITED absent

sparse arms, T-OQ against F-OQ-IVF at equal candidates, read at U_P: AHEAD (descriptive; enters no outcome; may not be cited to select a routing design)
sparse arms, T-OQ against F-OQ-IVF at equal candidates, read at run: AHEAD (descriptive; enters no outcome; may not be cited to select a routing design)

## C-SATURATION
_Run: P10IS1-pre-20261118 (registered); stage: analysis (saturation) (the registered run's records)._

**SATURATION-PROPORTIONAL [STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK; arms F-OQ; EIGHT FACTS PER SLOT; 16,384→65,536 NOT TESTED — BLOCK X NOT APPROVED]**
The crowding of the fixed width-16 oracle codes grows with the fact set: a SUBPROPORTIONAL verdict is NOT A PROPERTY OF THE STORE ALONE.

### F-OQ: saturation arm class SATURATION_PROPORTIONAL_ALL_PAIRS [STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK]

| pair | replicate | panel | verdict | rho | b(N) bits/slot | b(4N) | last ladder gain N | last ladder gain 4N | full (per cell) |
|---|---|---|---|---|---|---|---|---|---|
| 256→1K | 1 | A | PROPORTIONAL | 3.648 | 20.256 | 18.475 | 0.044 | 0.006 | {'2K/256': True, '8K/1K': True} |
| 256→1K | 1 | B | PROPORTIONAL | 3.649 | 20.233 | 18.457 | 0.047 | 0.003 | {'2K/256': True, '8K/1K': True} |
| 256→1K | 2 | A | PROPORTIONAL | 3.744 | 20.114 | 18.829 | 0.000 | 0.012 | {'2K/256': True, '8K/1K': True} |
| 256→1K | 2 | B | PROPORTIONAL | 3.736 | 20.162 | 18.829 | 0.000 | 0.011 | {'2K/256': True, '8K/1K': True} |
| 256→1K | 3 | A | PROPORTIONAL | 3.649 | 20.589 | 18.783 | 0.000 | 0.031 | {'2K/256': True, '8K/1K': True} |
| 256→1K | 3 | B | PROPORTIONAL | 3.654 | 20.541 | 18.765 | 0.000 | 0.026 | {'2K/256': True, '8K/1K': True} |
| 256→1K | 4 | A | PROPORTIONAL | 3.748 | 20.162 | 18.892 | 0.024 | 0.066 | {'2K/256': True, '8K/1K': True} |
| 256→1K | 4 | B | PROPORTIONAL | 3.760 | 20.114 | 18.909 | 0.021 | 0.070 | {'2K/256': True, '8K/1K': True} |
| 256→1K | 5 | A | PROPORTIONAL | 3.698 | 20.709 | 19.145 | 0.000 | 0.088 | {'2K/256': True, '8K/1K': True} |
| 256→1K | 5 | B | PROPORTIONAL | 3.685 | 20.781 | 19.145 | 0.000 | 0.089 | {'2K/256': True, '8K/1K': True} |
| 1K→4K | 1 | A | PROPORTIONAL | 3.824 | 18.475 | 17.663 | 0.006 | 0.093 | {'8K/1K': True, '32K/4K': True} |
| 1K→4K | 1 | B | PROPORTIONAL | 3.827 | 18.457 | 17.659 | 0.003 | 0.093 | {'8K/1K': True, '32K/4K': True} |
| 1K→4K | 2 | A | PROPORTIONAL | 3.691 | 18.829 | 17.374 | 0.012 | 0.053 | {'8K/1K': True, '32K/4K': True} |
| 1K→4K | 2 | B | PROPORTIONAL | 3.690 | 18.829 | 17.370 | 0.011 | 0.052 | {'8K/1K': True, '32K/4K': True} |
| 1K→4K | 3 | A | PROPORTIONAL | 3.731 | 18.783 | 17.517 | 0.031 | 0.060 | {'8K/1K': True, '32K/4K': True} |
| 1K→4K | 3 | B | PROPORTIONAL | 3.733 | 18.765 | 17.514 | 0.026 | 0.060 | {'8K/1K': True, '32K/4K': True} |
| 1K→4K | 4 | A | PROPORTIONAL | 3.591 | 18.892 | 16.961 | 0.066 | 0.041 | {'8K/1K': True, '32K/4K': True} |
| 1K→4K | 4 | B | PROPORTIONAL | 3.587 | 18.909 | 16.958 | 0.070 | 0.041 | {'8K/1K': True, '32K/4K': True} |
| 1K→4K | 5 | A | PROPORTIONAL | 3.629 | 19.145 | 17.369 | 0.088 | 0.075 | {'8K/1K': True, '32K/4K': True} |
| 1K→4K | 5 | B | PROPORTIONAL | 3.628 | 19.145 | 17.363 | 0.089 | 0.076 | {'8K/1K': True, '32K/4K': True} |

pair classes: 256→1K: PROPORTIONAL STEP [STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK]; 1K→4K: PROPORTIONAL STEP [STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK]

### F-OQ-IVF: saturation arm class SATURATION_DOES_NOT_SCALE

| pair | replicate | panel | verdict | rho | b(N) bits/slot | b(4N) | last ladder gain N | last ladder gain 4N | full (per cell) |
|---|---|---|---|---|---|---|---|---|---|
| 1K→4K | 1 | A | SUBPROPORTIONAL | 1.551 | 12.246 | 4.749 | 0.022 | 0.000 | {'8K/1K': True, '32K/4K': True} |
| 1K→4K | 1 | B | SUBPROPORTIONAL | 1.554 | 12.227 | 4.750 | 0.018 | 0.000 | {'8K/1K': True, '32K/4K': True} |
| 1K→4K | 2 | A | SUBPROPORTIONAL | 1.617 | 12.397 | 5.013 | 0.018 | 0.000 | {'8K/1K': True, '32K/4K': True} |
| 1K→4K | 2 | B | SUBPROPORTIONAL | 1.617 | 12.402 | 5.015 | 0.018 | 0.000 | {'8K/1K': True, '32K/4K': True} |
| 1K→4K | 3 | A | SUBPROPORTIONAL | 1.517 | 12.533 | 4.752 | 0.077 | 0.000 | {'8K/1K': True, '32K/4K': True} |
| 1K→4K | 3 | B | SUBPROPORTIONAL | 1.520 | 12.524 | 4.759 | 0.074 | 0.000 | {'8K/1K': True, '32K/4K': True} |
| 1K→4K | 4 | A | SUBPROPORTIONAL | 1.510 | 12.612 | 4.761 | 0.052 | 0.000 | {'8K/1K': True, '32K/4K': True} |
| 1K→4K | 4 | B | SUBPROPORTIONAL | 1.512 | 12.612 | 4.766 | 0.052 | 0.000 | {'8K/1K': True, '32K/4K': True} |
| 1K→4K | 5 | A | SUBPROPORTIONAL | 1.604 | 12.101 | 4.853 | 0.002 | 0.000 | {'8K/1K': True, '32K/4K': True} |
| 1K→4K | 5 | B | SUBPROPORTIONAL | 1.608 | 12.101 | 4.865 | 0.004 | 0.000 | {'8K/1K': True, '32K/4K': True} |

pair classes: 1K→4K: SUBPROPORTIONAL STEP

### T-OQ: saturation arm class SATURATION_DOES_NOT_SCALE

| pair | replicate | panel | verdict | rho | b(N) bits/slot | b(4N) | last ladder gain N | last ladder gain 4N | full (per cell) |
|---|---|---|---|---|---|---|---|---|---|
| 1K→4K | 1 | A | SUBPROPORTIONAL | 2.856 | 17.098 | 12.207 | 0.000 | 0.072 | {'8K/1K': True, '32K/4K': True} |
| 1K→4K | 1 | B | SUBPROPORTIONAL | 2.851 | 17.120 | 12.203 | 0.000 | 0.071 | {'8K/1K': True, '32K/4K': True} |
| 1K→4K | 2 | A | PROPORTIONAL | 3.179 | 16.405 | 13.037 | 0.000 | 0.053 | {'8K/1K': True, '32K/4K': True} |
| 1K→4K | 2 | B | PROPORTIONAL | 3.180 | 16.400 | 13.039 | 0.000 | 0.054 | {'8K/1K': True, '32K/4K': True} |
| 1K→4K | 3 | A | SUBPROPORTIONAL | 2.984 | 16.617 | 12.396 | 0.035 | 0.054 | {'8K/1K': True, '32K/4K': True} |
| 1K→4K | 3 | B | SUBPROPORTIONAL | 2.985 | 16.611 | 12.397 | 0.037 | 0.056 | {'8K/1K': True, '32K/4K': True} |
| 1K→4K | 4 | A | SUBPROPORTIONAL | 2.923 | 16.704 | 12.206 | 0.045 | 0.052 | {'8K/1K': True, '32K/4K': True} |
| 1K→4K | 4 | B | SUBPROPORTIONAL | 2.920 | 16.715 | 12.203 | 0.048 | 0.051 | {'8K/1K': True, '32K/4K': True} |
| 1K→4K | 5 | A | SUBPROPORTIONAL | 2.797 | 17.380 | 12.152 | 0.042 | 0.082 | {'8K/1K': True, '32K/4K': True} |
| 1K→4K | 5 | B | SUBPROPORTIONAL | 2.798 | 17.369 | 12.151 | 0.043 | 0.083 | {'8K/1K': True, '32K/4K': True} |

pair classes: 1K→4K: SUBPROPORTIONAL STEP

### H8: saturation arm class SATURATION_PROPORTIONAL_ALL_PAIRS [STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK] (H8 alone cannot give SATURATION-PROPORTIONAL [STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK])

| pair | replicate | panel | verdict | rho | b(N) bits/slot | b(4N) | last ladder gain N | last ladder gain 4N | full (per cell) |
|---|---|---|---|---|---|---|---|---|---|
| 1K→4K | 1 | A | PROPORTIONAL | 3.929 | 6.789 | 6.668 | 0.000 | 0.000 | {'8K/1K': True, '32K/4K': True} |
| 1K→4K | 1 | B | PROPORTIONAL | 3.965 | 6.725 | 6.667 | 0.000 | 0.000 | {'8K/1K': True, '32K/4K': True} |
| 1K→4K | 2 | A | PROPORTIONAL | 4.065 | 6.615 | 6.722 | 0.000 | 0.000 | {'8K/1K': True, '32K/4K': True} |
| 1K→4K | 2 | B | PROPORTIONAL | 4.074 | 6.599 | 6.721 | 0.000 | 0.000 | {'8K/1K': True, '32K/4K': True} |
| 1K→4K | 3 | A | PROPORTIONAL | 3.918 | 6.860 | 6.720 | 0.000 | 0.001 | {'8K/1K': True, '32K/4K': True} |
| 1K→4K | 3 | B | PROPORTIONAL | 3.949 | 6.809 | 6.721 | 0.000 | 0.001 | {'8K/1K': True, '32K/4K': True} |
| 1K→4K | 4 | A | PROPORTIONAL | 4.071 | 6.575 | 6.692 | 0.002 | 0.000 | {'8K/1K': True, '32K/4K': True} |
| 1K→4K | 4 | B | PROPORTIONAL | 4.053 | 6.603 | 6.691 | 0.004 | 0.000 | {'8K/1K': True, '32K/4K': True} |
| 1K→4K | 5 | A | PROPORTIONAL | 4.065 | 6.595 | 6.701 | 0.006 | 0.001 | {'8K/1K': True, '32K/4K': True} |
| 1K→4K | 5 | B | PROPORTIONAL | 4.080 | 6.564 | 6.696 | 0.000 | 0.001 | {'8K/1K': True, '32K/4K': True} |

pair classes: 1K→4K: PROPORTIONAL STEP [STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK]

## C-EFFICIENCY
_Run: P10IS1-pre-20261118 (registered); stage: analysis (efficiency) (the registered run's records and the isolated timing record)._

**EFFICIENCY-INCONCLUSIVE**
Each cell is printed under both cost readings; the analytic reading is counted multiply-adds (MC-A), never measured efficiency.

### reading E-A

- F-OQ: arm class NOT_EVALUATED; steps: N1: NOT_ASSESSED; N2: NOT_ASSESSED; dense speed: no FASTER STEP [STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK]
  - N1: verdicts per replicate ['NOT_ASSESSED', 'NOT_ASSESSED', 'NOT_ASSESSED', 'NOT_ASSESSED', 'NOT_ASSESSED']; u_T (smaller, larger) of replicate 1: ['left', '0.000', '512.000'] / ['left', '0.000', '512.000']
  - N2: verdicts per replicate ['NOT_ASSESSED', 'NOT_ASSESSED', 'NOT_ASSESSED', 'NOT_ASSESSED', 'NOT_ASSESSED']; u_T (smaller, larger) of replicate 1: ['exact', '796.346', '796.346'] / ['left', '0.000', '512.000']
- T-OQ: arm class NOT_EVALUATED; steps: N1: NOT_ASSESSED; N2: NO DIFFERENCE; dense speed: no FASTER STEP [STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK]
  - N1: verdicts per replicate ['NOT_ASSESSED', 'NOT_ASSESSED', 'NOT_ASSESSED', 'NOT_ASSESSED', 'NOT_ASSESSED']; u_T (smaller, larger) of replicate 1: ['left', '0.000', '512.000'] / ['left', '0.000', '512.000']
  - N2: verdicts per replicate ['SAME', 'SAME', 'SAME', 'SAME', 'SAME']; u_T (smaller, larger) of replicate 1: ['exact', '1289.557', '1289.557'] / ['exact', '703.801', '703.801']

### reading E-T

- F-OQ: arm class NOT_EVALUATED; steps: N1: NOT_ASSESSED; N2: NOT_ASSESSED; dense speed: no FASTER STEP [STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK]
  - N1: verdicts per replicate ['NOT_ASSESSED', 'NOT_ASSESSED', 'NOT_ASSESSED', 'NOT_ASSESSED', 'NOT_ASSESSED']; u_T (smaller, larger) of replicate 1: ['left', '0.000', '512.000'] / ['left', '0.000', '512.000']
  - N2: verdicts per replicate ['NOT_ASSESSED', 'NOT_ASSESSED', 'NOT_ASSESSED', 'NOT_ASSESSED', 'NOT_ASSESSED']; u_T (smaller, larger) of replicate 1: ['exact', '796.346', '796.346'] / ['left', '0.000', '512.000']
- T-OQ: arm class NOT_EVALUATED; steps: N1: NOT_ASSESSED; N2: NO DIFFERENCE; dense speed: no FASTER STEP [STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK]
  - N1: verdicts per replicate ['NOT_ASSESSED', 'NOT_ASSESSED', 'NOT_ASSESSED', 'NOT_ASSESSED', 'NOT_ASSESSED']; u_T (smaller, larger) of replicate 1: ['left', '0.000', '512.000'] / ['left', '0.000', '512.000']
  - N2: verdicts per replicate ['SAME', 'SAME', 'SAME', 'SAME', 'SAME']; u_T (smaller, larger) of replicate 1: ['exact', '1289.557', '1289.557'] / ['exact', '703.801', '703.801']

## Loaded cells and ladder stops
_Run: P10IS1-pre-20261118 (registered); stage: train (ladder) (ladder decisions)._

| ladder cell | U_run (the whole cell stopped here) |
|---|---|
| 8K/1K | 98304 |
| 32K/4K | 393216 |
| 2K/256 | 196608 |

Items beyond the stop are recorded NOT REACHED, not missing: P_D-OQ_f32768_n4096_d1_i330101_y786432_lr0.03: 2, P_D-OQ_f32768_n4096_d2_i330102_y786432_lr0.03: 2, P_D-OQ_f32768_n4096_d3_i330103_y786432_lr0.03: 2, P_D-OQ_f32768_n4096_d4_i330104_y786432_lr0.03: 2, P_D-OQ_f32768_n4096_d5_i330105_y786432_lr0.03: 2, P_D-OQ_f8192_n1024_d1_i330101_y393216_lr0.03: 4 ...

## Reference qualification
_Run: P10IS1-pre-20261118 (registered); stage: rehearsal (R2 table) and registered R2 re-read (stage record not given)._

no condition is unqualified at a fraction

## Readings taken here (departures and readings the specification leaves to the implementation)
- DEPARTURE (stricter for the store): a dependence failure on EITHER panel of either cell blocks the capacity step on both panels and gives DEPENDENCE_FAILED, never PANEL-DISAGREE (ADR-0024 section 9: a blocking condition needs one panel; P10-S1's code read DEP per panel; the lead's ruling).
- DEPARTURE (stricter for the store): DENSE NOT FASTER is not established in a replicate in which D-OQ failed a qualified dependence condition at ANY snapshot it read, where ruling 17 names only s_prev and s_hit (the lead's ruling: kept).
- READING: a snapshot at a fraction of U_P that has no reference-arm read (off the grid) has every dependence condition applied (nothing is disqualified): the stricter reading for the store.
- READING: where the larger cell of a capacity step costs no more per update than the smaller, the larger cell is read at U_P in every matched-compute reading, MC-C included (ruling 1), never later.
- READING: DENSE NOT FASTER needs the dense map's c_T above 0.8 of the arm's in all 5 replicates, on both panels, for every value the censoring bounds allow.
- READING: `STORE HOLDS MORE` and DENSE HOLDS MORE read D-OQ's dependence at the snapshot attaining i* and at U_RUN/2 of the cell (ruling 17).
- READING: the edge test of the rate search is 0.02 or more over the next rate (as P10-S1 did); the second extension steps (1.0 upwards, 0.0001 downwards) are not named by the ADR and were ruled by the lead on 2026-11-18, to be recorded in ADR-0024's rulings.
- CHECK: the whole cell's recorded stop (U_run) is recomputed from the data; a difference is an engineering failure, never a label.


## Counted work per query (logical counts; not measured efficiency)

| arm | cell | K | V | W |
|---|---|---|---|---|
| F-OQ | 2K/1K | 1024 | 8 | 17664 |
| F-OQ | 2K/4K | 4096 | 8 | 66816 |
| F-OQ | 8K/1K | 1024 | 8 | 17664 |
| F-OQ | 8K/4K | 4096 | 8 | 66816 |
| F-OQ | 8K/16K | 16384 | 8 | 263424 |
| F-OQ | 32K/4K | 4096 | 8 | 66816 |
| F-OQ | 32K/16K | 16384 | 8 | 263424 |
| F-OQ | 2K/256 | 256 | 8 | 5376 |
| T-OQ | 2K/1K | 516 | 8 | 9536 |
| T-OQ | 2K/4K | 528 | 8 | 9728 |
| T-OQ | 8K/1K | 516 | 8 | 9536 |
| T-OQ | 8K/4K | 528 | 8 | 9728 |
| T-OQ | 8K/16K | 576 | 8 | 10496 |
| T-OQ | 32K/4K | 528 | 8 | 9728 |
| T-OQ | 32K/16K | 576 | 8 | 10496 |
| H8 | 2K/1K | 0 | 8 | 1280 |
| H8 | 2K/4K | 0 | 8 | 1280 |
| H8 | 8K/1K | 0 | 8 | 1280 |
| H8 | 8K/4K | 0 | 8 | 1280 |
| H8 | 8K/16K | 0 | 8 | 1280 |
| H8 | 32K/4K | 0 | 8 | 1280 |
| H8 | 32K/16K | 0 | 8 | 1280 |
| D-OQ | 2K/4K | 0 | 0 | 193584 |
| D-OQ | 8K/4K | 0 | 0 | 193584 |
| D-OQ | 8K/16K | 0 | 0 | 771408 |
| D-OQ | 32K/16K | 0 | 0 | 771408 |
| D-OQ | 8K/1K | 0 | 0 | 49152 |
| D-OQ | 32K/4K | 0 | 0 | 193584 |
| R2 | 2K/4K | 0 | 1 | 1056 |
| R2 | 8K/16K | 0 | 1 | 1056 |
| R2 | 32K/32K | 0 | 1 | 1056 |

## Read-path throughput
_Run: P10IS1-pre-20261118 (registered); stage: throughput (MEASURED)._
measured, RAM, one process, quiet condition met: descriptive only; not storage I/O, not latency

### Labels that cannot be reached without measured CPU cost (ADR-0024 section 10)
| Line | Unreachable | Still reachable | Printed |
|---|---|---|---|
| C-CAPACITY | `CAPACITY-POSITIVE` (`STORE NOT BEHIND` needs MC-T) | NEGATIVE (a); NEGATIVE (b) through MU, MC-A, D-BEST or saturation; NOT TESTED; INCONCLUSIVE | MEASURED COST NOT AVAILABLE: a positive was not reachable |
| C-EFFICIENCY | `EFFICIENCY-POSITIVE` (needs E-T) | NEGATIVE through E-A; INCONCLUSIVE | the outcome with '(E-A ONLY; MEASURED COST NOT AVAILABLE)' |
| Dense at saturation (a label of section 9.2, not a C-SATURATION outcome) | `STORE HOLDS MORE AT SATURATION` (cost condition) | DENSE HOLDS MORE; SAME AT SATURATION; every C-SATURATION outcome | the same sentence beside the dense-at-saturation label |
