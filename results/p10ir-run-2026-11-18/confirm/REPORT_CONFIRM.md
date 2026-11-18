# P10-I-R confirmation (ADR-0029 section 10; stage `confirm`, group A2)

ArborLM is unproven research. This report is a diagnosis of read-time reads over memories trained under the registered read; it is neither a positive nor a negative result for ArborLM. Implementation self-checked only: not independent review, not Astra validation, not human approval. `Astra review: NOT_PERFORMED`.

Mode: registered. Plan SHA-256 a52da5fbea0fa2123b091562ed8502d776f2bf09a94bc43c3d9e3c3a118b5e56.

Against A1's analysis record, SHA-256 0ea94efec822605953b1e7177464401e362453b0edfd2c6b55a2b161685ff6da; that record is not rewritten.

## R-CONFIRM (does not change R-DIAGNOSIS)

- **R-CONFIRM-TREE: CONFIRMED** (A1: EXACT SEARCH HARMS; A2: EXACT SEARCH HARMS)
- **R-CONFIRM-INDEX: CONFIRMED** (A1: INDEX APPROACHES FLAT ONLY ABOVE 512; A2: INDEX APPROACHES FLAT ONLY ABOVE 512)

- A statement that the tree's gap is caused by a named factor at read time requires R-CONFIRM-TREE: CONFIRMED. Allowed here: True.

ITEM ERRORS (worker code raised inside an item; counted apart from gate failures): 0

## Stage A2

**R-DIAGNOSIS: EVALUABLE [FRESH CHECKPOINTS; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK]**

- **tree component: EXACT SEARCH HARMS [FRESH CHECKPOINTS; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK]**
  - at U_P: EXACT SEARCH HARMS (8K/4K = EXACT SEARCH HARMS, 32K/16K = EXACT SEARCH HARMS)
  - at RUN: EXACT SEARCH HARMS (8K/4K = EXACT SEARCH HARMS, 32K/16K = EXACT SEARCH HARMS)
- **index component: INDEX APPROACHES FLAT ONLY ABOVE 512 [FRESH CHECKPOINTS; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK]**
  - at U_P: INDEX APPROACHES FLAT ONLY ABOVE 512 (8K/4K = INDEX APPROACHES FLAT ONLY ABOVE 512, 32K/16K = INDEX APPROACHES FLAT ONLY ABOVE 512)
  - at RUN: INDEX APPROACHES FLAT ONLY ABOVE 512 (8K/4K = INDEX APPROACHES FLAT ONLY ABOVE 512, 32K/16K = INDEX APPROACHES FLAT ONLY ABOVE 512)
- pair (tree, index): (EXACT SEARCH HARMS, INDEX APPROACHES FLAT ONLY ABOVE 512)
- recommended action, tree component: none
- recommended action, index component: none

A limit printed with every label: these are read-time changes to memories trained under the registered read. The tree's values and output projection were trained with the prior in the weights and two branches visited. A read-time change that does not help does not show that training without it would not; one that helps shows only that the trained content tolerates it. Causes that act during training need Stage B.

### R-DIAGNOSIS-LOADED (descriptive; printed only; recommends nothing; no combination rule)


### Cells and checkpoints

#### 8K/4K (primary; facts 8192, slots 4096)

- **U_P, update 8192**
  - tree label: EXACT SEARCH HARMS [FRESH CHECKPOINTS; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK]
    - replicates: d1: EXACT SEARCH HARMS; d2: EXACT SEARCH HARMS; d3: EXACT SEARCH HARMS; d4: EXACT SEARCH HARMS; d5: EXACT SEARCH HARMS
    - retention against F0 per panel A/B: the rule in bits, with the accuracy version [acc(X) - acc0] / [acc(F0) - acc0] beside it (acc0 = memory-disabled accuracy; it decides nothing):
      - d1: T1 A: NOT RESTORED (accuracy version 0.369) / B: NOT RESTORED (accuracy version 0.379); T3 A: NOT RESTORED (accuracy version 0.426) / B: NOT RESTORED (accuracy version 0.433); T2 A: NOT RESTORED (accuracy version 0.043) / B: NOT RESTORED (accuracy version 0.043)
      - d2: T1 A: NOT RESTORED (accuracy version 0.363) / B: NOT RESTORED (accuracy version 0.359); T3 A: NOT RESTORED (accuracy version 0.414) / B: NOT RESTORED (accuracy version 0.409); T2 A: NOT RESTORED (accuracy version 0.044) / B: NOT RESTORED (accuracy version 0.047)
      - d3: T1 A: NOT RESTORED (accuracy version 0.354) / B: NOT RESTORED (accuracy version 0.357); T3 A: NOT RESTORED (accuracy version 0.418) / B: NOT RESTORED (accuracy version 0.418); T2 A: NOT RESTORED (accuracy version 0.038) / B: NOT RESTORED (accuracy version 0.038)
      - d4: T1 A: NOT RESTORED (accuracy version 0.337) / B: NOT RESTORED (accuracy version 0.338); T3 A: NOT RESTORED (accuracy version 0.383) / B: NOT RESTORED (accuracy version 0.389); T2 A: NOT RESTORED (accuracy version 0.038) / B: NOT RESTORED (accuracy version 0.040)
      - d5: T1 A: NOT RESTORED (accuracy version 0.382) / B: NOT RESTORED (accuracy version 0.380); T3 A: NOT RESTORED (accuracy version 0.433) / B: NOT RESTORED (accuracy version 0.435); T2 A: NOT RESTORED (accuracy version 0.043) / B: NOT RESTORED (accuracy version 0.044)
  - index label: INDEX APPROACHES FLAT ONLY ABOVE 512 [FRESH CHECKPOINTS; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK]
    - replicates: d1: INDEX APPROACHES FLAT ONLY ABOVE 512; d2: INDEX APPROACHES FLAT ONLY ABOVE 512; d3: INDEX APPROACHES FLAT ONLY ABOVE 512; d4: INDEX APPROACHES FLAT ONLY ABOVE 512; d5: INDEX APPROACHES FLAT ONLY ABOVE 512
    - retention against F0 per panel A/B: the rule in bits, with the accuracy version [acc(X) - acc0] / [acc(F0) - acc0] beside it (acc0 = memory-disabled accuracy; it decides nothing):
      - d1: 128 A: NOT RESTORED (accuracy version 0.498) / B: NOT RESTORED (accuracy version 0.501); 256 A: NOT RESTORED (accuracy version 0.687) / B: NOT RESTORED (accuracy version 0.685); 512 A: NOT RESTORED (accuracy version 0.865) / B: NOT RESTORED (accuracy version 0.863); 1024 A: RESTORED (accuracy version 0.970) / B: NOT RESTORED (accuracy version 0.970); 2048 A: RESTORED (accuracy version 0.998) / B: RESTORED (accuracy version 0.998)
      - d2: 128 A: NOT RESTORED (accuracy version 0.493) / B: NOT RESTORED (accuracy version 0.494); 256 A: NOT RESTORED (accuracy version 0.675) / B: NOT RESTORED (accuracy version 0.679); 512 A: NOT RESTORED (accuracy version 0.857) / B: NOT RESTORED (accuracy version 0.858); 1024 A: NOT RESTORED (accuracy version 0.967) / B: NOT RESTORED (accuracy version 0.970); 2048 A: RESTORED (accuracy version 0.999) / B: RESTORED (accuracy version 0.999)
      - d3: 128 A: NOT RESTORED (accuracy version 0.496) / B: NOT RESTORED (accuracy version 0.496); 256 A: NOT RESTORED (accuracy version 0.672) / B: NOT RESTORED (accuracy version 0.671); 512 A: NOT RESTORED (accuracy version 0.862) / B: NOT RESTORED (accuracy version 0.860); 1024 A: RESTORED (accuracy version 0.971) / B: NOT RESTORED (accuracy version 0.970); 2048 A: RESTORED (accuracy version 0.999) / B: RESTORED (accuracy version 0.999)
      - d4: 128 A: NOT RESTORED (accuracy version 0.491) / B: NOT RESTORED (accuracy version 0.491); 256 A: NOT RESTORED (accuracy version 0.671) / B: NOT RESTORED (accuracy version 0.673); 512 A: NOT RESTORED (accuracy version 0.855) / B: NOT RESTORED (accuracy version 0.856); 1024 A: NOT RESTORED (accuracy version 0.968) / B: NOT RESTORED (accuracy version 0.968); 2048 A: RESTORED (accuracy version 0.999) / B: RESTORED (accuracy version 0.999)
      - d5: 128 A: NOT RESTORED (accuracy version 0.498) / B: NOT RESTORED (accuracy version 0.503); 256 A: NOT RESTORED (accuracy version 0.677) / B: NOT RESTORED (accuracy version 0.678); 512 A: NOT RESTORED (accuracy version 0.858) / B: NOT RESTORED (accuracy version 0.858); 1024 A: RESTORED (accuracy version 0.971) / B: NOT RESTORED (accuracy version 0.970); 2048 A: RESTORED (accuracy version 0.999) / B: RESTORED (accuracy version 0.999)
    - median c*: 2048.0 keys, share of N: 0.500, N/8 for comparison: 512.0; replicates without c*: []
  - printed with the tree label (means over the replicates present):
    - T0: i 1.488, a_use 0.493, T1: i 0.857, a_use 0.353, T1w: i 1.221, a_use 0.436, T2: i 0.020, a_use 0.064, T3: i 1.065, a_use 0.402, F0: i 4.454, a_use 0.949
    - g_P -0.213, g_C -0.142, g_PC -0.495; i(F0) - i(T2) 4.434
    - visit sweep Tv: v=1: i on 0.621, off 0.621, CR8(on) 0.039, keys scored 272; v=2: i on 1.488, off 0.857, CR8(on) 0.073, keys scored 528; v=4: i on 1.145, off 0.221, CR8(on) 0.139, keys scored 1040; v=8: i on 1.069, off 0.064, CR8(on) 0.273, keys scored 2064
    - T0: CR8 0.073, CR1 0.107, SR8 0.071, AM_C 0.076, AM_S 0.075
    - prior effect: i(T1)-i(T0) -0.631, i(T1w)-i(T0) -0.267, i(T2)-i(T3) -1.046; selection changed T0->T1 0.801; facts spanning both branches 0.828; TV distance T0->T1 0.255
    - testability of the candidate restriction: share of facts whose T3 selection equals T0's 0.315 (near 1: T3 could not differ from T0, and the row CANDIDATES was not testable at this cell)
  - printed with the index label:
    - F0: i 4.454, a_use 0.949; I256@512: i 2.221, a_use 0.631, CR8 0.650, measured candidates mean 628.0, p99 787.2
    - I64@128: i 1.412, a_use 0.477, CR8 0.477, CR1 0.694, AM_C 0.522, candidates mean 158.7, p99 201.5
    - I64@256: i 2.302, a_use 0.645, CR8 0.634, CR1 0.836, AM_C 0.676, candidates mean 287.2, p99 328.6
    - I64@512: i 3.396, a_use 0.816, CR8 0.802, CR1 0.941, AM_C 0.832, candidates mean 543.6, p99 583.6
    - I64@1024: i 4.199, a_use 0.920, CR8 0.936, CR1 0.991, AM_C 0.948, candidates mean 1055.8, p99 1095.1
    - I64@2048: i 4.443, a_use 0.948, CR8 0.995, CR1 1.000, AM_C 0.996, candidates mean 2079.8, p99 2118.5
- **RUN, update 49152**
  - tree label: EXACT SEARCH HARMS [FRESH CHECKPOINTS; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK] [plateau check NOT CHECKED]
    - replicates: d1: EXACT SEARCH HARMS; d2: EXACT SEARCH HARMS; d3: EXACT SEARCH HARMS; d4: EXACT SEARCH HARMS; d5: EXACT SEARCH HARMS
    - retention against F0 per panel A/B: the rule in bits, with the accuracy version [acc(X) - acc0] / [acc(F0) - acc0] beside it (acc0 = memory-disabled accuracy; it decides nothing):
      - d1: T1 A: NOT RESTORED (accuracy version 0.503) / B: NOT RESTORED (accuracy version 0.501); T3 A: NOT RESTORED (accuracy version 0.581) / B: NOT RESTORED (accuracy version 0.580); T2 A: NOT RESTORED (accuracy version 0.033) / B: NOT RESTORED (accuracy version 0.033)
      - d2: T1 A: NOT RESTORED (accuracy version 0.515) / B: NOT RESTORED (accuracy version 0.515); T3 A: NOT RESTORED (accuracy version 0.590) / B: NOT RESTORED (accuracy version 0.591); T2 A: NOT RESTORED (accuracy version 0.037) / B: NOT RESTORED (accuracy version 0.037)
      - d3: T1 A: NOT RESTORED (accuracy version 0.521) / B: NOT RESTORED (accuracy version 0.521); T3 A: NOT RESTORED (accuracy version 0.608) / B: NOT RESTORED (accuracy version 0.605); T2 A: NOT RESTORED (accuracy version 0.030) / B: NOT RESTORED (accuracy version 0.037)
      - d4: T1 A: NOT RESTORED (accuracy version 0.503) / B: NOT RESTORED (accuracy version 0.505); T3 A: NOT RESTORED (accuracy version 0.585) / B: NOT RESTORED (accuracy version 0.582); T2 A: NOT RESTORED (accuracy version 0.035) / B: NOT RESTORED (accuracy version 0.033)
      - d5: T1 A: NOT RESTORED (accuracy version 0.550) / B: NOT RESTORED (accuracy version 0.547); T3 A: NOT RESTORED (accuracy version 0.621) / B: NOT RESTORED (accuracy version 0.623); T2 A: NOT RESTORED (accuracy version 0.042) / B: NOT RESTORED (accuracy version 0.041)
  - index label: INDEX APPROACHES FLAT ONLY ABOVE 512 [FRESH CHECKPOINTS; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK] [plateau check NOT CHECKED]
    - replicates: d1: INDEX APPROACHES FLAT ONLY ABOVE 512; d2: INDEX APPROACHES FLAT ONLY ABOVE 512; d3: INDEX APPROACHES FLAT ONLY ABOVE 512; d4: INDEX APPROACHES FLAT ONLY ABOVE 512; d5: INDEX APPROACHES FLAT ONLY ABOVE 512
    - retention against F0 per panel A/B: the rule in bits, with the accuracy version [acc(X) - acc0] / [acc(F0) - acc0] beside it (acc0 = memory-disabled accuracy; it decides nothing):
      - d1: 128 A: NOT RESTORED (accuracy version 0.532) / B: NOT RESTORED (accuracy version 0.533); 256 A: NOT RESTORED (accuracy version 0.715) / B: NOT RESTORED (accuracy version 0.714); 512 A: NOT RESTORED (accuracy version 0.886) / B: NOT RESTORED (accuracy version 0.887); 1024 A: RESTORED (accuracy version 0.979) / B: RESTORED (accuracy version 0.980); 2048 A: RESTORED (accuracy version 0.999) / B: RESTORED (accuracy version 1.000)
      - d2: 128 A: NOT RESTORED (accuracy version 0.538) / B: NOT RESTORED (accuracy version 0.537); 256 A: NOT RESTORED (accuracy version 0.722) / B: NOT RESTORED (accuracy version 0.722); 512 A: NOT RESTORED (accuracy version 0.895) / B: NOT RESTORED (accuracy version 0.895); 1024 A: RESTORED (accuracy version 0.982) / B: RESTORED (accuracy version 0.982); 2048 A: RESTORED (accuracy version 0.999) / B: RESTORED (accuracy version 0.999)
      - d3: 128 A: NOT RESTORED (accuracy version 0.529) / B: NOT RESTORED (accuracy version 0.532); 256 A: NOT RESTORED (accuracy version 0.716) / B: NOT RESTORED (accuracy version 0.719); 512 A: NOT RESTORED (accuracy version 0.891) / B: NOT RESTORED (accuracy version 0.892); 1024 A: RESTORED (accuracy version 0.981) / B: RESTORED (accuracy version 0.981); 2048 A: RESTORED (accuracy version 1.000) / B: RESTORED (accuracy version 1.000)
      - d4: 128 A: NOT RESTORED (accuracy version 0.531) / B: NOT RESTORED (accuracy version 0.530); 256 A: NOT RESTORED (accuracy version 0.713) / B: NOT RESTORED (accuracy version 0.713); 512 A: NOT RESTORED (accuracy version 0.893) / B: NOT RESTORED (accuracy version 0.894); 1024 A: RESTORED (accuracy version 0.981) / B: RESTORED (accuracy version 0.982); 2048 A: RESTORED (accuracy version 0.999) / B: RESTORED (accuracy version 0.999)
      - d5: 128 A: NOT RESTORED (accuracy version 0.540) / B: NOT RESTORED (accuracy version 0.541); 256 A: NOT RESTORED (accuracy version 0.722) / B: NOT RESTORED (accuracy version 0.723); 512 A: NOT RESTORED (accuracy version 0.889) / B: NOT RESTORED (accuracy version 0.888); 1024 A: RESTORED (accuracy version 0.981) / B: RESTORED (accuracy version 0.981); 2048 A: RESTORED (accuracy version 1.000) / B: RESTORED (accuracy version 1.000)
    - median c*: 1024.0 keys, share of N: 0.250, N/8 for comparison: 512.0; replicates without c*: []
  - printed with the tree label (means over the replicates present):
    - T0: i 3.103, a_use 0.773, T1: i 1.629, a_use 0.521, T1w: i 2.551, a_use 0.687, T2: i 0.018, a_use 0.062, T3: i 2.036, a_use 0.598, F0: i 4.947, a_use 0.996
    - g_P -0.800, g_C -0.579, g_PC -1.673; i(F0) - i(T2) 4.929
    - visit sweep Tv: v=1: i on 1.200, off 1.200, CR8(on) 0.032, keys scored 272; v=2: i on 3.103, off 1.629, CR8(on) 0.062, keys scored 528; v=4: i on 2.217, off 0.340, CR8(on) 0.125, keys scored 1040; v=8: i on 2.042, off 0.071, CR8(on) 0.261, keys scored 2064
    - T0: CR8 0.062, CR1 0.073, SR8 0.061, AM_C 0.063, AM_S 0.062
    - prior effect: i(T1)-i(T0) -1.475, i(T1w)-i(T0) -0.552, i(T2)-i(T3) -2.017; selection changed T0->T1 0.811; facts spanning both branches 0.831; TV distance T0->T1 0.261
    - testability of the candidate restriction: share of facts whose T3 selection equals T0's 0.290 (near 1: T3 could not differ from T0, and the row CANDIDATES was not testable at this cell)
  - printed with the index label:
    - F0: i 4.947, a_use 0.996; I256@512: i 2.698, a_use 0.711, CR8 0.654, measured candidates mean 640.1, p99 787.2
    - I64@128: i 1.717, a_use 0.538, CR8 0.471, CR1 0.698, AM_C 0.518, candidates mean 158.8, p99 200.9
    - I64@256: i 2.742, a_use 0.718, CR8 0.627, CR1 0.839, AM_C 0.672, candidates mean 287.1, p99 327.9
    - I64@512: i 3.939, a_use 0.888, CR8 0.796, CR1 0.943, AM_C 0.828, candidates mean 543.5, p99 583.1
    - I64@1024: i 4.732, a_use 0.977, CR8 0.933, CR1 0.991, AM_C 0.947, candidates mean 1055.6, p99 1094.4
    - I64@2048: i 4.940, a_use 0.996, CR8 0.995, CR1 1.000, AM_C 0.996, candidates mean 2079.7, p99 2117.9

#### 32K/16K (primary; facts 32768, slots 16384)

- **U_P, update 16384**
  - tree label: EXACT SEARCH HARMS [FRESH CHECKPOINTS; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK]
    - replicates: d1: EXACT SEARCH HARMS; d2: EXACT SEARCH HARMS; d3: EXACT SEARCH HARMS; d4: EXACT SEARCH HARMS; d5: EXACT SEARCH HARMS
    - retention against F0 per panel A/B: the rule in bits, with the accuracy version [acc(X) - acc0] / [acc(F0) - acc0] beside it (acc0 = memory-disabled accuracy; it decides nothing):
      - d1: T1 A: NOT RESTORED (accuracy version 0.368) / B: NOT RESTORED (accuracy version 0.368); T3 A: NOT RESTORED (accuracy version 0.320) / B: NOT RESTORED (accuracy version 0.318); T2 A: NOT RESTORED (accuracy version 0.014) / B: NOT RESTORED (accuracy version 0.014)
      - d2: T1 A: NOT RESTORED (accuracy version 0.364) / B: NOT RESTORED (accuracy version 0.363); T3 A: NOT RESTORED (accuracy version 0.313) / B: NOT RESTORED (accuracy version 0.310); T2 A: NOT RESTORED (accuracy version 0.014) / B: NOT RESTORED (accuracy version 0.013)
      - d3: T1 A: NOT RESTORED (accuracy version 0.348) / B: NOT RESTORED (accuracy version 0.352); T3 A: NOT RESTORED (accuracy version 0.298) / B: NOT RESTORED (accuracy version 0.301); T2 A: NOT RESTORED (accuracy version 0.013) / B: NOT RESTORED (accuracy version 0.014)
      - d4: T1 A: NOT RESTORED (accuracy version 0.351) / B: NOT RESTORED (accuracy version 0.350); T3 A: NOT RESTORED (accuracy version 0.307) / B: NOT RESTORED (accuracy version 0.307); T2 A: NOT RESTORED (accuracy version 0.011) / B: NOT RESTORED (accuracy version 0.013)
      - d5: T1 A: NOT RESTORED (accuracy version 0.365) / B: NOT RESTORED (accuracy version 0.368); T3 A: NOT RESTORED (accuracy version 0.317) / B: NOT RESTORED (accuracy version 0.314); T2 A: NOT RESTORED (accuracy version 0.013) / B: NOT RESTORED (accuracy version 0.013)
  - index label: INDEX APPROACHES FLAT ONLY ABOVE 512 [FRESH CHECKPOINTS; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK]
    - replicates: d1: INDEX APPROACHES FLAT ONLY ABOVE 512; d2: INDEX APPROACHES FLAT ONLY ABOVE 512; d3: INDEX APPROACHES FLAT ONLY ABOVE 512; d4: INDEX APPROACHES FLAT ONLY ABOVE 512; d5: INDEX APPROACHES FLAT ONLY ABOVE 512
    - retention against F0 per panel A/B: the rule in bits, with the accuracy version [acc(X) - acc0] / [acc(F0) - acc0] beside it (acc0 = memory-disabled accuracy; it decides nothing):
      - d1: 128 A: NOT RESTORED (accuracy version 0.404) / B: NOT RESTORED (accuracy version 0.402); 256 A: NOT RESTORED (accuracy version 0.564) / B: NOT RESTORED (accuracy version 0.562); 512 A: NOT RESTORED (accuracy version 0.747) / B: NOT RESTORED (accuracy version 0.747); 1024 A: NOT RESTORED (accuracy version 0.901) / B: NOT RESTORED (accuracy version 0.900); 2048 A: RESTORED (accuracy version 0.977) / B: RESTORED (accuracy version 0.977)
      - d2: 128 A: NOT RESTORED (accuracy version 0.405) / B: NOT RESTORED (accuracy version 0.402); 256 A: NOT RESTORED (accuracy version 0.564) / B: NOT RESTORED (accuracy version 0.563); 512 A: NOT RESTORED (accuracy version 0.746) / B: NOT RESTORED (accuracy version 0.745); 1024 A: NOT RESTORED (accuracy version 0.896) / B: NOT RESTORED (accuracy version 0.895); 2048 A: RESTORED (accuracy version 0.976) / B: RESTORED (accuracy version 0.975)
      - d3: 128 A: NOT RESTORED (accuracy version 0.403) / B: NOT RESTORED (accuracy version 0.404); 256 A: NOT RESTORED (accuracy version 0.562) / B: NOT RESTORED (accuracy version 0.563); 512 A: NOT RESTORED (accuracy version 0.744) / B: NOT RESTORED (accuracy version 0.745); 1024 A: NOT RESTORED (accuracy version 0.896) / B: NOT RESTORED (accuracy version 0.897); 2048 A: RESTORED (accuracy version 0.976) / B: RESTORED (accuracy version 0.977)
      - d4: 128 A: NOT RESTORED (accuracy version 0.404) / B: NOT RESTORED (accuracy version 0.403); 256 A: NOT RESTORED (accuracy version 0.563) / B: NOT RESTORED (accuracy version 0.562); 512 A: NOT RESTORED (accuracy version 0.746) / B: NOT RESTORED (accuracy version 0.746); 1024 A: NOT RESTORED (accuracy version 0.897) / B: NOT RESTORED (accuracy version 0.897); 2048 A: RESTORED (accuracy version 0.976) / B: RESTORED (accuracy version 0.976)
      - d5: 128 A: NOT RESTORED (accuracy version 0.401) / B: NOT RESTORED (accuracy version 0.401); 256 A: NOT RESTORED (accuracy version 0.560) / B: NOT RESTORED (accuracy version 0.560); 512 A: NOT RESTORED (accuracy version 0.743) / B: NOT RESTORED (accuracy version 0.743); 1024 A: NOT RESTORED (accuracy version 0.896) / B: NOT RESTORED (accuracy version 0.895); 2048 A: RESTORED (accuracy version 0.975) / B: RESTORED (accuracy version 0.975)
    - median c*: 2048.0 keys, share of N: 0.125, N/8 for comparison: 2048.0; replicates without c*: []
  - printed with the tree label (means over the replicates present):
    - T0: i 1.105, a_use 0.411, T1: i 0.810, a_use 0.341, T1w: i 0.973, a_use 0.381, T2: i 0.001, a_use 0.039, T3: i 0.642, a_use 0.298, F0: i 4.180, a_use 0.917
    - g_P -0.096, g_C -0.150, g_PC -0.359; i(F0) - i(T2) 4.179
    - visit sweep Tv: v=1: i on 0.441, off 0.441, CR8(on) 0.008, keys scored 320; v=2: i on 1.105, off 0.810, CR8(on) 0.016, keys scored 576; v=4: i on 0.825, off 0.267, CR8(on) 0.029, keys scored 1088; v=8: i on 0.676, off 0.070, CR8(on) 0.059, keys scored 2112
    - T0: CR8 0.016, CR1 0.017, SR8 0.016, AM_C 0.016, AM_S 0.016
    - prior effect: i(T1)-i(T0) -0.294, i(T1w)-i(T0) -0.131, i(T2)-i(T3) -0.641; selection changed T0->T1 0.724; facts spanning both branches 0.909; TV distance T0->T1 0.201
    - testability of the candidate restriction: share of facts whose T3 selection equals T0's 0.098 (near 1: T3 could not differ from T0, and the row CANDIDATES was not testable at this cell)
  - printed with the index label:
    - F0: i 4.180, a_use 0.917; I256@512: i 1.440, a_use 0.483, CR8 0.526, measured candidates mean 639.4, p99 790.8
    - I64@128: i 0.971, a_use 0.380, CR8 0.403, CR1 0.624, AM_C 0.439, candidates mean 158.7, p99 201.6
    - I64@256: i 1.630, a_use 0.521, CR8 0.539, CR1 0.766, AM_C 0.576, candidates mean 287.2, p99 328.3
    - I64@512: i 2.545, a_use 0.686, CR8 0.694, CR1 0.887, AM_C 0.726, candidates mean 543.6, p99 583.3
    - I64@1024: i 3.454, a_use 0.824, CR8 0.841, CR1 0.963, AM_C 0.862, candidates mean 1055.9, p99 1094.5
    - I64@2048: i 3.999, a_use 0.895, CR8 0.947, CR1 0.994, AM_C 0.956, candidates mean 2079.9, p99 2118.6
- **RUN, update 98304**
  - tree label: EXACT SEARCH HARMS [FRESH CHECKPOINTS; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK] [plateau check NOT CHECKED]
    - replicates: d1: EXACT SEARCH HARMS; d2: EXACT SEARCH HARMS; d3: EXACT SEARCH HARMS; d4: EXACT SEARCH HARMS; d5: EXACT SEARCH HARMS
    - retention against F0 per panel A/B: the rule in bits, with the accuracy version [acc(X) - acc0] / [acc(F0) - acc0] beside it (acc0 = memory-disabled accuracy; it decides nothing):
      - d1: T1 A: NOT RESTORED (accuracy version 0.534) / B: NOT RESTORED (accuracy version 0.535); T3 A: NOT RESTORED (accuracy version 0.400) / B: NOT RESTORED (accuracy version 0.399); T2 A: NOT RESTORED (accuracy version 0.003) / B: NOT RESTORED (accuracy version 0.005)
      - d2: T1 A: NOT RESTORED (accuracy version 0.537) / B: NOT RESTORED (accuracy version 0.537); T3 A: NOT RESTORED (accuracy version 0.405) / B: NOT RESTORED (accuracy version 0.405); T2 A: NOT RESTORED (accuracy version 0.005) / B: NOT RESTORED (accuracy version 0.003)
      - d3: T1 A: NOT RESTORED (accuracy version 0.531) / B: NOT RESTORED (accuracy version 0.532); T3 A: NOT RESTORED (accuracy version 0.397) / B: NOT RESTORED (accuracy version 0.397); T2 A: NOT RESTORED (accuracy version 0.004) / B: NOT RESTORED (accuracy version 0.006)
      - d4: T1 A: NOT RESTORED (accuracy version 0.542) / B: NOT RESTORED (accuracy version 0.543); T3 A: NOT RESTORED (accuracy version 0.408) / B: NOT RESTORED (accuracy version 0.408); T2 A: NOT RESTORED (accuracy version 0.005) / B: NOT RESTORED (accuracy version 0.005)
      - d5: T1 A: NOT RESTORED (accuracy version 0.535) / B: NOT RESTORED (accuracy version 0.536); T3 A: NOT RESTORED (accuracy version 0.405) / B: NOT RESTORED (accuracy version 0.408); T2 A: NOT RESTORED (accuracy version 0.005) / B: NOT RESTORED (accuracy version 0.004)
  - index label: INDEX APPROACHES FLAT ONLY ABOVE 512 [FRESH CHECKPOINTS; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK] [plateau check NOT CHECKED]
    - replicates: d1: INDEX APPROACHES FLAT ONLY ABOVE 512; d2: INDEX APPROACHES FLAT ONLY ABOVE 512; d3: INDEX APPROACHES FLAT ONLY ABOVE 512; d4: INDEX APPROACHES FLAT ONLY ABOVE 512; d5: INDEX APPROACHES FLAT ONLY ABOVE 512
    - retention against F0 per panel A/B: the rule in bits, with the accuracy version [acc(X) - acc0] / [acc(F0) - acc0] beside it (acc0 = memory-disabled accuracy; it decides nothing):
      - d1: 128 A: NOT RESTORED (accuracy version 0.415) / B: NOT RESTORED (accuracy version 0.415); 256 A: NOT RESTORED (accuracy version 0.579) / B: NOT RESTORED (accuracy version 0.580); 512 A: NOT RESTORED (accuracy version 0.770) / B: NOT RESTORED (accuracy version 0.770); 1024 A: NOT RESTORED (accuracy version 0.918) / B: NOT RESTORED (accuracy version 0.918); 2048 A: RESTORED (accuracy version 0.985) / B: RESTORED (accuracy version 0.985)
      - d2: 128 A: NOT RESTORED (accuracy version 0.419) / B: NOT RESTORED (accuracy version 0.418); 256 A: NOT RESTORED (accuracy version 0.586) / B: NOT RESTORED (accuracy version 0.586); 512 A: NOT RESTORED (accuracy version 0.772) / B: NOT RESTORED (accuracy version 0.772); 1024 A: NOT RESTORED (accuracy version 0.919) / B: NOT RESTORED (accuracy version 0.918); 2048 A: RESTORED (accuracy version 0.985) / B: RESTORED (accuracy version 0.985)
      - d3: 128 A: NOT RESTORED (accuracy version 0.416) / B: NOT RESTORED (accuracy version 0.417); 256 A: NOT RESTORED (accuracy version 0.582) / B: NOT RESTORED (accuracy version 0.582); 512 A: NOT RESTORED (accuracy version 0.772) / B: NOT RESTORED (accuracy version 0.772); 1024 A: NOT RESTORED (accuracy version 0.920) / B: NOT RESTORED (accuracy version 0.920); 2048 A: RESTORED (accuracy version 0.985) / B: RESTORED (accuracy version 0.985)
      - d4: 128 A: NOT RESTORED (accuracy version 0.414) / B: NOT RESTORED (accuracy version 0.415); 256 A: NOT RESTORED (accuracy version 0.582) / B: NOT RESTORED (accuracy version 0.582); 512 A: NOT RESTORED (accuracy version 0.773) / B: NOT RESTORED (accuracy version 0.773); 1024 A: NOT RESTORED (accuracy version 0.921) / B: NOT RESTORED (accuracy version 0.921); 2048 A: RESTORED (accuracy version 0.985) / B: RESTORED (accuracy version 0.985)
      - d5: 128 A: NOT RESTORED (accuracy version 0.418) / B: NOT RESTORED (accuracy version 0.419); 256 A: NOT RESTORED (accuracy version 0.584) / B: NOT RESTORED (accuracy version 0.583); 512 A: NOT RESTORED (accuracy version 0.773) / B: NOT RESTORED (accuracy version 0.772); 1024 A: NOT RESTORED (accuracy version 0.918) / B: NOT RESTORED (accuracy version 0.918); 2048 A: RESTORED (accuracy version 0.985) / B: RESTORED (accuracy version 0.985)
    - median c*: 2048.0 keys, share of N: 0.125, N/8 for comparison: 2048.0; replicates without c*: []
  - printed with the tree label (means over the replicates present):
    - T0: i 2.653, a_use 0.703, T1: i 1.707, a_use 0.536, T1w: i 2.272, a_use 0.640, T2: i 0.000, a_use 0.034, T3: i 1.094, a_use 0.409, F0: i 4.884, a_use 0.991
    - g_P -0.424, g_C -0.699, g_PC -1.189; i(F0) - i(T2) 4.884
    - visit sweep Tv: v=1: i on 0.839, off 0.839, CR8(on) 0.003, keys scored 320; v=2: i on 2.653, off 1.707, CR8(on) 0.006, keys scored 576; v=4: i on 1.603, off 0.389, CR8(on) 0.014, keys scored 1088; v=8: i on 1.190, off 0.072, CR8(on) 0.035, keys scored 2112
    - T0: CR8 0.006, CR1 0.005, SR8 0.006, AM_C 0.006, AM_S 0.006
    - prior effect: i(T1)-i(T0) -0.946, i(T1w)-i(T0) -0.381, i(T2)-i(T3) -1.094; selection changed T0->T1 0.743; facts spanning both branches 0.923; TV distance T0->T1 0.211
    - testability of the candidate restriction: share of facts whose T3 selection equals T0's 0.062 (near 1: T3 could not differ from T0, and the row CANDIDATES was not testable at this cell)
  - printed with the index label:
    - F0: i 4.884, a_use 0.991; I256@512: i 1.710, a_use 0.537, CR8 0.521, measured candidates mean 635.0, p99 788.2
    - I64@128: i 1.155, a_use 0.422, CR8 0.397, CR1 0.620, AM_C 0.433, candidates mean 158.6, p99 201.4
    - I64@256: i 1.948, a_use 0.582, CR8 0.532, CR1 0.762, AM_C 0.570, candidates mean 287.0, p99 328.3
    - I64@512: i 3.059, a_use 0.766, CR8 0.687, CR1 0.885, AM_C 0.720, candidates mean 543.5, p99 583.1
    - I64@1024: i 4.127, a_use 0.911, CR8 0.835, CR1 0.963, AM_C 0.858, candidates mean 1055.9, p99 1094.3
    - I64@2048: i 4.721, a_use 0.976, CR8 0.944, CR1 0.994, AM_C 0.954, candidates mean 2079.9, p99 2118.5

`Astra review: NOT_PERFORMED`.
