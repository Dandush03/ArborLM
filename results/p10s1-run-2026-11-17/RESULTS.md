# P10S1 results (ADR-0021, revision 5)

**Every positive label below carries `STORE ONLY; ORACLE-ADDRESSED`. Addressing was supplied by an oracle.** S1 establishes nothing about an autonomous learned memory, about the language model forming queries, about capability beyond recall of the trained facts, or about natural-language knowledge.

Self-checked analysis. Not independent review, not Astra validation, not human approval. **Astra review: NOT_PERFORMED.**

- Status: **COMPLETE**
- Addressing: addressing was supplied by an oracle (S1 measures the store, not the interface).
- S0 status (ADR-0020, K7(c)): S0 ADDRESSING-QUALIFIED (4,096 AND 16,384)
- Learned-address lane (lane L): OMITTED — NOT OVERLOAD-QUALIFIED
- Cells read: 185; missing: 0; failed: 0; failed tasks: 0
- Plan: {"dense_cut": [], "lane_l": false, "placeholder": false, "row_u_p": [8192, 8192, 16384], "sat256": false, "seed_block_draws": [1, 2], "toq_not_loaded": [], "u_l": [393216, 786432], "u_l_256": 0, "unit": 8192}; cuts: none

## Outcomes

- **Capacity line:** CAPACITY-INCONCLUSIVE: F-OQ: DEPENDENCE_FAILED; F-OQ-IVF: DEPENDENCE_FAILED; T-OQ: INTERMEDIATE [16,384→65,536 NOT TESTED]
- **Saturation line:** SATURATION-INCONCLUSIVE: F-OQ: INTERMEDIATE; T-OQ: SATURATION_NOT_MEASURED [16,384 NOT MEASURED — NOT FUNDED; 256 NOT MEASURED — NOT FULL WITHIN CEILING]
- **Efficiency line:** EFFICIENCY-NEGATIVE (DENSE FASTER) [SIZES 1,024–16,384]
- **Reading for milestone question 1 (capacity line with the saturation line and the dense labels, never the efficiency line):** Not established | S0 ADDRESSING-QUALIFIED (4,096 AND 16,384) | addressing was supplied by an oracle
- The three lines are separate; none implies another. The reading for milestone question 1 uses the capacity line, the saturation line and the dense labels, never the efficiency line.

## Capacity line: arms and steps

| Arm | Arm class | Dense label | Active work | Step C1 (class; replicate verdicts) | Step C2 (class; replicate verdicts) | Step N1 (class; replicate verdicts) | Step N2 (class; replicate verdicts) |
|---|---|---|---|---|---|---|---|
| F-OQ | DEPENDENCE_FAILED | DENSE AHEAD | LINEAR KEY SCORING | MIXED; CAPACITY [STORE ONLY; ORACLE-ADDRESSED], CAPACITY [STORE ONLY; ORACLE-ADDRESSED], CAPACITY [STORE ONLY; ORACLE-ADDRESSED], DEPENDENCE_FAILED, CAPACITY [STORE ONLY; ORACLE-ADDRESSED] | CAPACITY STEP [STORE ONLY; ORACLE-ADDRESSED]; CAPACITY [STORE ONLY; ORACLE-ADDRESSED], CAPACITY [STORE ONLY; ORACLE-ADDRESSED], CAPACITY [STORE ONLY; ORACLE-ADDRESSED], CAPACITY [STORE ONLY; ORACLE-ADDRESSED], CAPACITY [STORE ONLY; ORACLE-ADDRESSED] | NOT LOADED; CEILING, CEILING, DEPENDENCE_FAILED, CEILING, CEILING | DEPENDENCE_FAILED; GAIN WITHIN BUDGET ONLY, DEPENDENCE_FAILED, GAIN WITHIN BUDGET ONLY, DEPENDENCE_FAILED, GAIN WITHIN BUDGET ONLY |
| F-OQ-IVF | DEPENDENCE_FAILED | DENSE NOT READ | n/a | MIXED; PANEL-DISAGREE, CAPACITY [STORE ONLY; ORACLE-ADDRESSED], CAPACITY [STORE ONLY; ORACLE-ADDRESSED], CAPACITY [STORE ONLY; ORACLE-ADDRESSED], CAPACITY [STORE ONLY; ORACLE-ADDRESSED] | GAIN WITHIN BUDGET; GAIN WITHIN BUDGET ONLY, GAIN WITHIN BUDGET ONLY, GAIN WITHIN BUDGET ONLY, CAPACITY [STORE ONLY; ORACLE-ADDRESSED], GAIN WITHIN BUDGET ONLY | MIXED; UNRESOLVED, UNRESOLVED, DEPENDENCE_FAILED, PANEL-DISAGREE, UNRESOLVED | DEPENDENCE_FAILED; CAPACITY [STORE ONLY; ORACLE-ADDRESSED], DEPENDENCE_FAILED, CAPACITY [STORE ONLY; ORACLE-ADDRESSED], CAPACITY [STORE ONLY; ORACLE-ADDRESSED], DEPENDENCE_FAILED |
| H8 | CAPACITY_ONE_TRANSITION [STORE ONLY; ORACLE-ADDRESSED] UNDERTRAINED-AT-U_P | DENSE AHEAD | SUBLINEAR | MIXED; CAPACITY [STORE ONLY; ORACLE-ADDRESSED], CAPACITY [STORE ONLY; ORACLE-ADDRESSED], CAPACITY [STORE ONLY; ORACLE-ADDRESSED], DEPENDENCE_FAILED, CAPACITY [STORE ONLY; ORACLE-ADDRESSED] | CAPACITY STEP [STORE ONLY; ORACLE-ADDRESSED]; CAPACITY [STORE ONLY; ORACLE-ADDRESSED], CAPACITY [STORE ONLY; ORACLE-ADDRESSED], CAPACITY [STORE ONLY; ORACLE-ADDRESSED], CAPACITY [STORE ONLY; ORACLE-ADDRESSED], CAPACITY [STORE ONLY; ORACLE-ADDRESSED] | NOT REPLICATED; PANEL-DISAGREE, CAPACITY [STORE ONLY; ORACLE-ADDRESSED], PANEL-DISAGREE, CAPACITY [STORE ONLY; ORACLE-ADDRESSED], CAPACITY [STORE ONLY; ORACLE-ADDRESSED] | MIXED; CAPACITY [STORE ONLY; ORACLE-ADDRESSED], CAPACITY [STORE ONLY; ORACLE-ADDRESSED], CAPACITY [STORE ONLY; ORACLE-ADDRESSED], DEPENDENCE_FAILED, CAPACITY [STORE ONLY; ORACLE-ADDRESSED] |
| T-OQ | INTERMEDIATE | DENSE NOT READ | n/a | GAIN WITHIN BUDGET; GAIN WITHIN BUDGET ONLY, GAIN WITHIN BUDGET ONLY, GAIN WITHIN BUDGET ONLY, GAIN WITHIN BUDGET ONLY, GAIN WITHIN BUDGET ONLY | GAIN WITHIN BUDGET; GAIN WITHIN BUDGET ONLY, GAIN WITHIN BUDGET ONLY, GAIN WITHIN BUDGET ONLY, GAIN WITHIN BUDGET ONLY, GAIN WITHIN BUDGET ONLY | MIXED; GAIN WITHIN BUDGET ONLY, GAIN WITHIN BUDGET ONLY, PANEL-DISAGREE, GAIN WITHIN BUDGET ONLY, GAIN WITHIN BUDGET ONLY | GAIN WITHIN BUDGET; GAIN WITHIN BUDGET ONLY, GAIN WITHIN BUDGET ONLY, GAIN WITHIN BUDGET ONLY, GAIN WITHIN BUDGET ONLY, GAIN WITHIN BUDGET ONLY |

- Hierarchy (T-OQ against F-OQ-IVF at equal candidate count): TREE_BEHIND
- KEY-LEARNING-LIMITED: False
- Conventional retrieval, F-OQ: not sufficient
- Conventional retrieval, F-OQ-IVF: not sufficient
- Conventional retrieval, T-OQ: not sufficient
- DICT DOMINATES ON THIS TASK

## Efficiency line: arms and steps

| Arm | Arm class | Dense label | Step N1 (class; replicate verdicts) | Step N2 (class; replicate verdicts) |
|---|---|---|---|---|
| F-OQ | EFFICIENCY_NOT_SUPPORTED | n/a | NO DIFFERENCE; SAME, SAME, SAME, SAME, SAME | NO DIFFERENCE; SAME, SAME, SAME, SAME, SAME |
| T-OQ | EFFICIENCY_SUPPORTED [STORE ONLY; ORACLE-ADDRESSED] | DENSE FASTER | FASTER STEP [STORE ONLY; ORACLE-ADDRESSED]; FASTER [STORE ONLY; ORACLE-ADDRESSED], FASTER [STORE ONLY; ORACLE-ADDRESSED], FASTER [STORE ONLY; ORACLE-ADDRESSED], FASTER [STORE ONLY; ORACLE-ADDRESSED], FASTER [STORE ONLY; ORACLE-ADDRESSED] | FASTER STEP [STORE ONLY; ORACLE-ADDRESSED]; FASTER [STORE ONLY; ORACLE-ADDRESSED], REACHED ONLY BY THE LARGER [STORE ONLY; ORACLE-ADDRESSED], REACHED ONLY BY THE LARGER [STORE ONLY; ORACLE-ADDRESSED], FASTER [STORE ONLY; ORACLE-ADDRESSED], FASTER [STORE ONLY; ORACLE-ADDRESSED] |

## Row movement (section 7.3; printed with every budget and efficiency verdict; no class depends on it)

| Line | Arm | Step | Row-movement ratio, total (larger / smaller, per replicate) | Without-gradient share ratio | OPTIMIZER-ASSISTED (replicates) |
|---|---|---|---|---|---|
| capacity | F-OQ | C1 | 3.40, 3.36, 3.37, 3.38, 3.38 | 2.03, 2.03, 2.04, 2.06, 2.03 | 5/5 |
| capacity | F-OQ | C2 | 2.98, 2.95, 2.96, 2.97, 2.95 | 1.21, 1.21, 1.21, 1.21, 1.21 | 0/5 |
| capacity | F-OQ | N1 | 2.70, 2.66, 2.70, 2.79, 2.62 | 1.96, 1.98, 1.98, 2.01, 1.98 | 5/5 |
| capacity | F-OQ | N2 | 2.58, 2.56, 2.59, 2.60, 2.52 | 1.20, 1.20, 1.20, 1.20, 1.20 | 0/5 |
| capacity | F-OQ-IVF | C1 | 3.40, 3.36, 3.37, 3.38, 3.38 | 2.03, 2.03, 2.04, 2.06, 2.03 | 5/5 |
| capacity | F-OQ-IVF | C2 | 2.98, 2.95, 2.96, 2.97, 2.95 | 1.21, 1.21, 1.21, 1.21, 1.21 | 0/5 |
| capacity | F-OQ-IVF | N1 | 2.70, 2.66, 2.70, 2.79, 2.62 | 1.96, 1.98, 1.98, 2.01, 1.98 | 5/5 |
| capacity | F-OQ-IVF | N2 | 2.58, 2.56, 2.59, 2.60, 2.52 | 1.20, 1.20, 1.20, 1.20, 1.20 | 0/5 |
| capacity | H8 | C1 | 3.71, 3.71, 3.65, 3.64, 3.69 | 2.13, 2.13, 2.12, 2.13, 2.13 | 5/5 |
| capacity | H8 | C2 | 3.20, 3.19, 3.17, 3.18, 3.21 | 1.21, 1.21, 1.21, 1.21, 1.21 | 0/5 |
| capacity | H8 | N1 | 3.22, 3.19, 3.25, 3.29, 3.15 | 2.14, 2.13, 2.14, 2.13, 2.14 | 5/5 |
| capacity | H8 | N2 | 2.46, 2.47, 2.47, 2.44, 2.41 | 1.21, 1.21, 1.21, 1.21, 1.21 | 0/5 |
| capacity | T-OQ | C1 | 2.93, 2.82, 2.78, 2.65, 3.00 | 2.61, 2.47, 2.56, 2.43, 2.73 | 5/5 |
| capacity | T-OQ | C2 | 2.93, 2.91, 2.95, 2.94, 2.97 | 1.47, 1.52, 1.51, 1.51, 1.51 | 4/5 |
| capacity | T-OQ | N1 | 2.56, 2.28, 2.26, 2.19, 2.36 | 3.08, 2.69, 2.74, 2.65, 2.75 | 5/5 |
| capacity | T-OQ | N2 | 2.50, 2.63, 2.48, 2.42, 2.58 | 1.54, 1.58, 1.56, 1.51, 1.54 | 5/5 |
| efficiency | F-OQ | N1 | 2.70, 2.66, 2.70, 2.79, 2.62 | 1.96, 1.98, 1.98, 2.01, 1.98 | 5/5 |
| efficiency | F-OQ | N2 | 2.58, 2.56, 2.59, 2.60, 2.52 | 1.20, 1.20, 1.20, 1.20, 1.20 | 0/5 |
| efficiency | T-OQ | N1 | 2.56, 2.28, 2.26, 2.19, 2.36 | 3.08, 2.69, 2.74, 2.65, 2.75 | 5/5 |
| efficiency | T-OQ | N2 | 2.50, 2.63, 2.48, 2.42, 2.58 | 1.54, 1.58, 1.56, 1.51, 1.54 | 5/5 |

## Saturation line (section 8.10; eight facts per slot; full = plateau rule within registered run lengths)

- F-OQ: INTERMEDIATE; pairs read: 256→1024, 1024→4096; 1024→4096 PROPORTIONAL STEP [STORE ONLY; ORACLE-ADDRESSED]; 256→1024 NOT FULL (256 NOT MEASURED — NOT FULL WITHIN CEILING)
  - F-OQ 1024→4096 replicate 1: PROPORTIONAL, rho A/B = 3.78 / 3.78; b(N) 19.16 -> 18.13 bits per slot (panel A); last doubling gains 0.087 / 0.053
  - F-OQ 1024→4096 replicate 2: PROPORTIONAL, rho A/B = 3.85 / 3.86; b(N) 18.74 -> 18.02 bits per slot (panel A); last doubling gains 0.024 / 0.061
  - F-OQ 1024→4096 replicate 3: PROPORTIONAL, rho A/B = 3.82 / 3.82; b(N) 18.95 -> 18.08 bits per slot (panel A); last doubling gains 0.066 / 0.042
  - F-OQ 1024→4096 replicate 4: PROPORTIONAL, rho A/B = 3.88 / 3.89; b(N) 18.66 -> 18.08 bits per slot (panel A); last doubling gains 0.060 / 0.029
  - F-OQ 1024→4096 replicate 5: PROPORTIONAL, rho A/B = 3.82 / 3.84; b(N) 18.76 -> 17.92 bits per slot (panel A); last doubling gains 0.024 / 0.017
- F-OQ-IVF: SATURATION_DOES_NOT_SCALE; pairs read: 1024→4096; 1024→4096 SUBPROPORTIONAL STEP
  - F-OQ-IVF 1024→4096 replicate 1: SUBPROPORTIONAL, rho A/B = 1.42 / 1.41; b(N) 12.48 -> 4.43 bits per slot (panel A); last doubling gains 0.046 / 0.000
  - F-OQ-IVF 1024→4096 replicate 2: SUBPROPORTIONAL, rho A/B = 1.42 / 1.42; b(N) 12.25 -> 4.34 bits per slot (panel A); last doubling gains 0.013 / 0.019
  - F-OQ-IVF 1024→4096 replicate 3: SUBPROPORTIONAL, rho A/B = 1.46 / 1.47; b(N) 12.11 -> 4.41 bits per slot (panel A); last doubling gains 0.000 / 0.015
  - F-OQ-IVF 1024→4096 replicate 4: SUBPROPORTIONAL, rho A/B = 1.50 / 1.49; b(N) 11.79 -> 4.42 bits per slot (panel A); last doubling gains 0.020 / 0.000
  - F-OQ-IVF 1024→4096 replicate 5: SUBPROPORTIONAL, rho A/B = 1.43 / 1.43; b(N) 12.28 -> 4.39 bits per slot (panel A); last doubling gains 0.000 / 0.018
- H8: SATURATION_PROPORTIONAL_ALL_PAIRS [STORE ONLY; ORACLE-ADDRESSED]; pairs read: 1024→4096; 1024→4096 PROPORTIONAL STEP [STORE ONLY; ORACLE-ADDRESSED]
  - H8 1024→4096 replicate 1: PROPORTIONAL, rho A/B = 4.13 / 4.14; b(N) 6.46 -> 6.67 bits per slot (panel A); last doubling gains 0.014 / 0.000
  - H8 1024→4096 replicate 2: PROPORTIONAL, rho A/B = 4.00 / 4.01; b(N) 6.63 -> 6.63 bits per slot (panel A); last doubling gains 0.000 / 0.001
  - H8 1024→4096 replicate 3: PROPORTIONAL, rho A/B = 4.07 / 4.08; b(N) 6.49 -> 6.60 bits per slot (panel A); last doubling gains 0.004 / 0.000
  - H8 1024→4096 replicate 4: PROPORTIONAL, rho A/B = 4.09 / 4.05; b(N) 6.50 -> 6.66 bits per slot (panel A); last doubling gains 0.009 / 0.003
  - H8 1024→4096 replicate 5: PROPORTIONAL, rho A/B = 3.95 / 3.95; b(N) 6.70 -> 6.62 bits per slot (panel A); last doubling gains 0.015 / 0.003
- T-OQ: SATURATION_NOT_MEASURED; pairs read: 1024→4096; 1024→4096 NOT FULL
  - T-OQ 1024→4096 replicate 2: SUBPROPORTIONAL, rho A/B = 2.65 / 2.64; b(N) 8.41 -> 5.57 bits per slot (panel A); last doubling gains 0.051 / 0.062
  - T-OQ 1024→4096 replicate 3: SUBPROPORTIONAL, rho A/B = 2.54 / 2.58; b(N) 9.54 -> 6.06 bits per slot (panel A); last doubling gains 0.079 / 0.022
  - T-OQ 1024→4096 replicate 4: SUBPROPORTIONAL, rho A/B = 2.39 / 2.38; b(N) 9.91 -> 5.92 bits per slot (panel A); last doubling gains 0.059 / 0.028
- SATURATION-SUBPROPORTIONAL, where printed, is never read as a property of the store alone: the oracle codes' crowding grows with the fact set (section 8.10).
- 16,384 NOT MEASURED — NOT FUNDED
- Separability at the saturation cells (printed beside every rho): 32K/4K replicate 1: nn_cosine_mean 0.829, share_neighbour_above_0_8 0.849, share_with_private_slot 0.000, top8_overlap_with_nearest 0.261; 32K/4K replicate 2: nn_cosine_mean 0.829, share_neighbour_above_0_8 0.849, share_with_private_slot 0.000, top8_overlap_with_nearest 0.260; 32K/4K replicate 3: nn_cosine_mean 0.829, share_neighbour_above_0_8 0.848, share_with_private_slot 0.000, top8_overlap_with_nearest 0.260; 32K/4K replicate 4: nn_cosine_mean 0.829, share_neighbour_above_0_8 0.851, share_with_private_slot 0.000, top8_overlap_with_nearest 0.262; 32K/4K replicate 5: nn_cosine_mean 0.829, share_neighbour_above_0_8 0.848, share_with_private_slot 0.000, top8_overlap_with_nearest 0.262; 8K/1K replicate 1: nn_cosine_mean 0.791, share_neighbour_above_0_8 0.379, share_with_private_slot 0.000, top8_overlap_with_nearest 0.298; 8K/1K replicate 2: nn_cosine_mean 0.791, share_neighbour_above_0_8 0.376, share_with_private_slot 0.000, top8_overlap_with_nearest 0.298; 8K/1K replicate 3: nn_cosine_mean 0.791, share_neighbour_above_0_8 0.375, share_with_private_slot 0.000, top8_overlap_with_nearest 0.297; 8K/1K replicate 4: nn_cosine_mean 0.791, share_neighbour_above_0_8 0.378, share_with_private_slot 0.000, top8_overlap_with_nearest 0.300; 8K/1K replicate 5: nn_cosine_mean 0.791, share_neighbour_above_0_8 0.368, share_with_private_slot 0.000, top8_overlap_with_nearest 0.300
- Dense at saturation (section 8.5): F-OQ: DENSE HOLDS MORE AT SATURATION; F-OQ-IVF: DENSE HOLDS MORE AT SATURATION; T-OQ: DENSE HOLDS MORE AT SATURATION
- H8 annotations: {"2K/1K": "H8 NOT CALIBRATED AT 2K/1K", "32K/16K": "UNDERTRAINED-AT-U_P", "32K/4K": "H8 NOT CALIBRATED AT 32K/4K", "8K/1K": "H8 NOT CALIBRATED AT 8K/1K", "8K/4K": "UNDERTRAINED-AT-U_P"}
- MC-AMBIGUOUS pairs (the two cost measures disagreed on the costlier cell; the pair counts as established and was read in the comparator's favour): dense|F-OQ|2K/4K (small at 8192, large at 16384, multiplier 1.65, OK), dense|F-OQ|8K/4K (small at 8192, large at 16384, multiplier 1.65, OK), dense|T-OQ|2K/4K (small at 8192, large at 20480, multiplier 2.04, OK), dense|T-OQ|8K/4K (small at 8192, large at 20480, multiplier 2.04, OK)
- Pairs read per arm: F-OQ 256→1024, 1024→4096; F-OQ-IVF 1024→4096; H8 1024→4096; T-OQ 1024→4096

## Robustness (descriptive)

- F-OQ: C1: NOT ASSESSED (a_use below 0.5); C2: NOT ASSESSED (a_use below 0.5); N1: RISES WITH SLOTS; N2: RISES WITH SLOTS
- H8: C1: NOT ASSESSED (a_use below 0.5); C2: NOT ASSESSED (a_use below 0.5); N1: RISES WITH SLOTS; N2: RISES WITH SLOTS
- T-OQ: C1: NOT ASSESSED (a_use below 0.5); C2: NOT ASSESSED (a_use below 0.5); N1: RISES WITH SLOTS; N2: NOT ASSESSED (a_use below 0.5)

## Seed block (descriptive, enters no rule)

- draw1 2K/1K U_P: spread within draw 0.835, across draws 0.040; dominates: init seed
- draw1 2K/1K U_run: spread within draw 1.071, across draws 0.030; dominates: init seed
- draw1 2K/4K U_P: spread within draw 0.519, across draws 0.008; dominates: init seed
- draw1 2K/4K U_run: spread within draw 0.496, across draws 0.000; dominates: init seed
- draw1 32K/16K U_P: spread within draw 2.769, across draws 0.191; dominates: init seed
- draw1 32K/16K U_run: spread within draw 3.172, across draws 0.010; dominates: init seed
- draw1 32K/4K U_P: spread within draw 0.665, across draws 0.238; dominates: init seed
- draw1 32K/4K U_run: spread within draw 1.750, across draws 0.026; dominates: init seed
- draw1 8K/16K U_P: spread within draw 0.859, across draws 0.013; dominates: init seed
- draw1 8K/16K U_run: spread within draw 0.794, across draws 0.000; dominates: init seed
- draw1 8K/1K U_P: spread within draw 0.325, across draws 0.250; dominates: init seed
- draw1 8K/1K U_run: spread within draw 0.925, across draws 0.062; dominates: init seed
- draw1 8K/4K U_P: spread within draw 2.227, across draws 0.238; dominates: init seed
- draw1 8K/4K U_run: spread within draw 2.385, across draws 0.017; dominates: init seed
- draw2 2K/1K U_P: spread within draw 0.834, across draws 0.040; dominates: init seed
- draw2 2K/1K U_run: spread within draw 0.844, across draws 0.030; dominates: init seed
- draw2 2K/4K U_P: spread within draw 0.621, across draws 0.008; dominates: init seed
- draw2 2K/4K U_run: spread within draw 0.422, across draws 0.000; dominates: init seed
- draw2 32K/16K U_P: spread within draw 2.708, across draws 0.191; dominates: init seed
- draw2 32K/16K U_run: spread within draw 3.180, across draws 0.010; dominates: init seed
- draw2 32K/4K U_P: spread within draw 0.668, across draws 0.238; dominates: init seed
- draw2 32K/4K U_run: spread within draw 1.746, across draws 0.026; dominates: init seed
- draw2 8K/16K U_P: spread within draw 0.883, across draws 0.013; dominates: init seed
- draw2 8K/16K U_run: spread within draw 0.786, across draws 0.000; dominates: init seed
- draw2 8K/1K U_P: spread within draw 0.292, across draws 0.250; dominates: init seed
- draw2 8K/1K U_run: spread within draw 0.875, across draws 0.062; dominates: init seed
- draw2 8K/4K U_P: spread within draw 2.220, across draws 0.238; dominates: init seed
- draw2 8K/4K U_run: spread within draw 2.302, across draws 0.017; dominates: init seed

## MC-MISMATCH (a flag; changes no class)

- dense|F-OQ|8K/4K replicate 1: CPU ratio 2.12
- dense|F-OQ|8K/4K replicate 2: CPU ratio 2.09
- dense|F-OQ|8K/4K replicate 3: CPU ratio 2.16
- dense|F-OQ|8K/4K replicate 4: CPU ratio 2.14
- dense|F-OQ|8K/4K replicate 5: CPU ratio 2.16
- cap|F-OQ|N1 replicate 4: CPU ratio 1.26
- cap|F-OQ|N1 replicate 5: CPU ratio 1.29
- dense|F-OQ|2K/4K replicate 1: CPU ratio 1.59
- dense|F-OQ|2K/4K replicate 2: CPU ratio 1.63
- dense|F-OQ|2K/4K replicate 3: CPU ratio 1.68
- dense|F-OQ|2K/4K replicate 4: CPU ratio 1.76
- dense|F-OQ|2K/4K replicate 5: CPU ratio 1.81
- cap|F-OQ|C2 replicate 1: CPU ratio 1.51
- cap|F-OQ|C2 replicate 2: CPU ratio 1.46
- cap|F-OQ|C2 replicate 3: CPU ratio 1.27
- cap|F-OQ|C2 replicate 4: CPU ratio 1.27
- cap|F-OQ|C2 replicate 5: CPU ratio 1.29
- dense|F-OQ|32K/16K replicate 1: CPU ratio 2.23
- dense|F-OQ|32K/16K replicate 2: CPU ratio 2.20
- dense|F-OQ|32K/16K replicate 3: CPU ratio 2.09
- dense|F-OQ|32K/16K replicate 4: CPU ratio 2.07
- dense|F-OQ|32K/16K replicate 5: CPU ratio 2.06
- cap|F-OQ|N2 replicate 1: CPU ratio 1.37
- cap|F-OQ|N2 replicate 2: CPU ratio 1.37
- cap|F-OQ|N2 replicate 3: CPU ratio 1.34
- cap|F-OQ|N2 replicate 4: CPU ratio 1.35
- cap|F-OQ|N2 replicate 5: CPU ratio 1.35
- dense|F-OQ|8K/16K replicate 1: CPU ratio 2.37
- dense|F-OQ|8K/16K replicate 2: CPU ratio 2.36
- dense|F-OQ|8K/16K replicate 3: CPU ratio 2.37
- dense|F-OQ|8K/16K replicate 4: CPU ratio 2.32
- dense|F-OQ|8K/16K replicate 5: CPU ratio 2.32
- dense|T-OQ|8K/4K replicate 1: CPU ratio 1.96
- dense|T-OQ|8K/4K replicate 2: CPU ratio 1.94
- dense|T-OQ|8K/4K replicate 3: CPU ratio 1.93
- dense|T-OQ|8K/4K replicate 4: CPU ratio 1.93
- dense|T-OQ|8K/4K replicate 5: CPU ratio 1.96
- dense|T-OQ|2K/4K replicate 1: CPU ratio 1.69
- dense|T-OQ|2K/4K replicate 2: CPU ratio 1.71
- dense|T-OQ|2K/4K replicate 3: CPU ratio 1.69
- dense|T-OQ|2K/4K replicate 4: CPU ratio 1.69
- dense|T-OQ|2K/4K replicate 5: CPU ratio 1.70
- dense|T-OQ|32K/16K replicate 1: CPU ratio 4.71
- dense|T-OQ|32K/16K replicate 2: CPU ratio 4.91
- dense|T-OQ|32K/16K replicate 3: CPU ratio 4.88
- dense|T-OQ|32K/16K replicate 4: CPU ratio 4.87
- dense|T-OQ|32K/16K replicate 5: CPU ratio 4.85
- dense|T-OQ|8K/16K replicate 1: CPU ratio 5.15
- dense|T-OQ|8K/16K replicate 2: CPU ratio 5.17
- dense|T-OQ|8K/16K replicate 3: CPU ratio 5.16
- dense|T-OQ|8K/16K replicate 4: CPU ratio 5.14
- dense|T-OQ|8K/16K replicate 5: CPU ratio 5.13
- dense|H8|8K/4K replicate 1: CPU ratio 1.33
- dense|H8|8K/4K replicate 2: CPU ratio 1.36
- dense|H8|8K/4K replicate 3: CPU ratio 1.39
- dense|H8|8K/4K replicate 4: CPU ratio 1.44
- dense|H8|8K/4K replicate 5: CPU ratio 1.41
- dense|H8|2K/4K replicate 1: CPU ratio 1.65
- dense|H8|2K/4K replicate 2: CPU ratio 1.61
- dense|H8|2K/4K replicate 3: CPU ratio 1.63
- dense|H8|2K/4K replicate 4: CPU ratio 1.58
- dense|H8|2K/4K replicate 5: CPU ratio 1.58
- dense|H8|32K/16K replicate 1: CPU ratio 2.33
- dense|H8|32K/16K replicate 2: CPU ratio 2.30
- dense|H8|32K/16K replicate 3: CPU ratio 2.29
- dense|H8|32K/16K replicate 4: CPU ratio 2.30
- dense|H8|32K/16K replicate 5: CPU ratio 2.30
- dense|H8|8K/16K replicate 1: CPU ratio 2.31
- dense|H8|8K/16K replicate 2: CPU ratio 2.34
- dense|H8|8K/16K replicate 3: CPU ratio 2.32
- dense|H8|8K/16K replicate 4: CPU ratio 2.31
- dense|H8|8K/16K replicate 5: CPU ratio 2.26

## Cost table (replicate 1; logical counts and measured CPU seconds; not measured efficiency)

| Arm | Cell | I_use (A / B) bits | Trainable | Stored | Bits per stored byte (A) | K | V | W | Exposures per fact (U_P / U_run) | CPU s to U_P | Analytic multiply-adds to U_P |
|---|---|---|---|---|---|---|---|---|---|---|---|
| D-OQ | 2K/4K | 10240.0 / 10240.0 | 197618 | 225010 | 0.0114 | 0 | 0 | 193584 | 512.0 / 3072.0 | 57.9 | 1.02e+12 |
| D-OQ | 8K/1K | 24325.0 / 24128.6 | 50177 | 77569 | 0.0784 | 0 | 0 | 49152 | 128.0 / 6144.0 | 34.9 | 6.1e+11 |
| D-OQ | 8K/4K | 40564.7 / 40564.7 | 197618 | 225010 | 0.0451 | 0 | 0 | 193584 | 128.0 / 768.0 | 73.7 | 1.02e+12 |
| D-OQ | 8K/16K | 40874.6 / 40874.6 | 787480 | 814872 | 0.0125 | 0 | 0 | 771408 | 128.0 / 768.0 | 138.2 | 2.65e+12 |
| D-OQ | 32K/4K | 62560.0 / 62522.3 | 197618 | 225010 | 0.0695 | 0 | 0 | 193584 | 64.0 / 3072.0 | 103.7 | 2.04e+12 |
| D-OQ | 32K/16K | 147920.4 / 147854.8 | 787480 | 814872 | 0.0454 | 0 | 0 | 771408 | 64.0 / 384.0 | 288.9 | 5.31e+12 |
| F-OQ | 2K/1K | 10013.8 / 9944.1 | 50177 | 77569 | 0.0323 | 1024 | 8 | 17664 | 512.0 / 3072.0 | 48.4 | 5.11e+11 |
| F-OQ | 2K/4K | 10240.0 / 10240.0 | 197633 | 225025 | 0.0114 | 4096 | 8 | 66816 | 512.0 / 3072.0 | 82.5 | 6.19e+11 |
| F-OQ | 8K/1K | 8098.5 / 8214.1 | 50177 | 77569 | 0.0261 | 1024 | 8 | 17664 | 128.0 / 6144.0 | 42.0 | 5.11e+11 |
| F-OQ | 8K/4K | 36352.0 / 36243.0 | 197633 | 225025 | 0.0404 | 4096 | 8 | 66816 | 128.0 / 768.0 | 75.7 | 6.19e+11 |
| F-OQ | 8K/16K | 40799.3 / 40843.9 | 787457 | 814849 | 0.0125 | 16384 | 8 | 263424 | 128.0 / 768.0 | 108.7 | 1.05e+12 |
| F-OQ | 32K/4K | 31335.4 / 31525.8 | 197633 | 225025 | 0.0348 | 4096 | 8 | 66816 | 64.0 / 3072.0 | 163.8 | 1.24e+12 |
| F-OQ | 32K/16K | 135343.5 / 135701.7 | 787457 | 814849 | 0.0415 | 16384 | 8 | 263424 | 64.0 / 384.0 | 215.6 | 2.1e+12 |
| F-OQ-IVF | 2K/1K | 8527.4 / 8527.4 | 50177 | 77569 | 0.0275 | 1024 | 8 | 11645.4 | 512.0 / 3072.0 | 48.4 | 5.11e+11 |
| F-OQ-IVF | 2K/4K | 9270.8 / 9280.3 | 197633 | 225025 | 0.0103 | 4096 | 8 | 11991.6 | 512.0 / 3072.0 | 82.5 | 6.19e+11 |
| F-OQ-IVF | 8K/1K | 5011.1 / 5191.4 | 50177 | 77569 | 0.0162 | 1024 | 8 | 10955.2 | 128.0 / 6144.0 | 42.0 | 5.11e+11 |
| F-OQ-IVF | 8K/4K | 17429.7 / 17757.3 | 197633 | 225025 | 0.0194 | 4096 | 8 | 11398.5 | 128.0 / 768.0 | 75.7 | 6.19e+11 |
| F-OQ-IVF | 8K/16K | 33917.1 / 33933.8 | 787457 | 814849 | 0.0104 | 16384 | 8 | 12610.5 | 128.0 / 768.0 | 108.7 | 1.05e+12 |
| F-OQ-IVF | 32K/4K | 10131.1 / 10022.6 | 197633 | 225025 | 0.0113 | 4096 | 8 | 11843.2 | 64.0 / 3072.0 | 163.8 | 1.24e+12 |
| F-OQ-IVF | 32K/16K | 45836.7 / 46072.5 | 787457 | 814849 | 0.0141 | 16384 | 8 | 12401.7 | 64.0 / 384.0 | 215.6 | 2.1e+12 |
| H8 | 2K/1K | 7090.0 / 7126.0 | 33793 | 61185 | 0.0290 | 0 | 8 | 1280 | 512.0 / 3072.0 | 36.4 | 4.76e+11 |
| H8 | 2K/4K | 10240.0 / 10240.0 | 132097 | 159489 | 0.0161 | 0 | 8 | 1280 | 512.0 / 3072.0 | 37.7 | 4.79e+11 |
| H8 | 8K/1K | 2597.7 / 2648.2 | 33793 | 61185 | 0.0106 | 0 | 8 | 1280 | 128.0 / 6144.0 | 31.8 | 4.76e+11 |
| H8 | 8K/4K | 24999.3 / 24892.9 | 132097 | 159489 | 0.0392 | 0 | 8 | 1280 | 128.0 / 768.0 | 39.2 | 4.79e+11 |
| H8 | 8K/16K | 40923.2 / 40940.6 | 525313 | 552705 | 0.0185 | 0 | 8 | 1280 | 128.0 / 768.0 | 52.0 | 4.92e+11 |
| H8 | 32K/4K | 13811.1 / 13990.1 | 132097 | 159489 | 0.0216 | 0 | 8 | 1280 | 64.0 / 3072.0 | 82.4 | 9.59e+11 |
| H8 | 32K/16K | 108570.7 / 108654.6 | 525313 | 552705 | 0.0491 | 0 | 8 | 1280 | 64.0 / 384.0 | 114.1 | 9.85e+11 |
| R2 | 2K/4K | 10240.0 / 10240.0 | 132097 | 159489 | 0.0161 | 0 | 1 | 1056 | 512.0 / 512.0 | 38.4 | 4.79e+11 |
| R2 | 8K/16K | 40960.0 / 40960.0 | 525313 | 552705 | 0.0185 | 0 | 1 | 1056 | 128.0 / 128.0 | 50.9 | 4.92e+11 |
| R2 | 32K/32K | 163840.0 / 163840.0 | 1049601 | 1076993 | 0.0380 | 0 | 1 | 1056 | 64.0 / 64.0 | 138.7 | 1.02e+12 |
| T-OQ | 2K/1K | 5886.1 / 5905.5 | 50241 | 77633 | 0.0190 | 516 | 8 | 9536 | 512.0 / 3072.0 | 96.6 | 4.94e+11 |
| T-OQ | 2K/4K | 9932.7 / 9955.5 | 197889 | 225281 | 0.0110 | 528 | 8 | 9728 | 512.0 / 3072.0 | 101.6 | 5e+11 |
| T-OQ | 8K/1K | 1758.5 / 1745.5 | 50241 | 77633 | 0.0057 | 516 | 8 | 9536 | 128.0 / 6144.0 | 85.7 | 4.94e+11 |
| T-OQ | 8K/4K | 10898.0 / 10950.0 | 197889 | 225281 | 0.0121 | 528 | 8 | 9728 | 128.0 / 768.0 | 104.6 | 5e+11 |
| T-OQ | 8K/16K | 33867.1 / 33742.4 | 788481 | 815873 | 0.0104 | 576 | 8 | 10496 | 128.0 / 768.0 | 115.3 | 5.21e+11 |
| T-OQ | 32K/4K | 5332.4 / 5477.8 | 197889 | 225281 | 0.0059 | 528 | 8 | 9728 | 64.0 / 3072.0 | 206.2 | 9.99e+11 |
| T-OQ | 32K/16K | 32556.4 / 32882.3 | 788481 | 815873 | 0.0100 | 576 | 8 | 10496 | 64.0 / 384.0 | 226.8 | 1.04e+12 |

## Isolated timing

```json
{
 "cpu_per_update": {
  "D-OQ|1024": 0.0033967695312499824,
  "D-OQ|16384": 0.012042339843750027,
  "D-OQ|4096": 0.005090183593749992,
  "F-OQ|1024": 0.004152144531249999,
  "F-OQ|16384": 0.009252121093750003,
  "F-OQ|256": 0.0034214921875,
  "F-OQ|4096": 0.007013417968749998,
  "H8|1024": 0.002974480468749985,
  "H8|16384": 0.004588148437499995,
  "H8|4096": 0.003311808593749993,
  "R2|16384": 0.004507867187499959,
  "R2|32768": 0.006305117187499987,
  "R2|4096": 0.0032380820312500336,
  "T-OQ|1024": 0.009136261718749997,
  "T-OQ|16384": 0.011560464843750007,
  "T-OQ|4096": 0.009714371093750007
 },
 "dry": false,
 "environment": {
  "cpu_count": 18,
  "delegated_models": "recorded from session metadata by the lead, not by this code",
  "machine": "arm64",
  "platform": "macOS-27.2.1-arm64-arm-64bit",
  "processor": "arm",
  "psutil": "7.0.0",
  "python": "3.12.14 (main, Sep  1 2026, 14:09:38) [Clang 22.1.3 ]",
  "python_implementation": "CPython",
  "release": "27.2.0",
  "system": "Darwin",
  "threads": {
   "deterministic_algorithms": true,
   "env": {
    "MKL_NUM_THREADS": null,
    "OMP_NUM_THREADS": null,
    "OPENBLAS_NUM_THREADS": null,
    "PYTHONHASHSEED": null,
    "VECLIB_MAXIMUM_THREADS": null
   },
   "torch_interop_threads": 1,
   "torch_num_threads": 1
  },
  "torch": "2.8.0"
 },
 "evaluation_seconds": {},
 "identity": {
  "config_sha256": "edc8e0534c8b5ca8e732aa801195d7637029d1024481110e5ba82ab389a4d73f",
  "frozen_source_sha256": "8b5a03a08fc10a4ac29bdf9c6dd2d21945b9bb3aff459766b58304545d570507",
  "source_sha256": "c22399d52ac48ecbb0b5c1a4c6b222a02c77cb07a7dd5edc57db256c2db5d03f",
  "spec_sha256": "2344a875d7e58b757f268125597f43de943e021051ad580968ba2201debe044c"
 },
 "kind": "timing",
 "load_average_max": 1.0,
 "quiet": {
  "attempts": 2,
  "load_averages": [
   1.3427734375,
   0.728515625
  ],
  "quiet": true
 },
 "runs": {
  "D-OQ|1024": {
   "cpu_seconds_per_update": 0.0033967695312499824,
   "peak_rss_bytes": 376045568,
   "runs": [
    0.003513824218749989,
    0.0033902656249999996,
    0.0033967695312499824
   ],
   "updates_per_run": 256,
   "wall_runs": [
    0.003516578937706072,
    0.0033930556642189913,
    0.003399534504296753
   ],
   "wall_seconds_per_update": 0.003399534504296753,
   "warmup_updates": 32
  },
  "D-OQ|16384": {
   "cpu_seconds_per_update": 0.012042339843750027,
   "peak_rss_bytes": 376045568,
   "runs": [
    0.012138667968749989,
    0.012039292968750004,
    0.012042339843750027
   ],
   "updates_per_run": 256,
   "wall_runs": [
    0.012148944987984578,
    0.012049532715082023,
    0.01205254817932655
   ],
   "wall_seconds_per_update": 0.01205254817932655,
   "warmup_updates": 32
  },
  "D-OQ|4096": {
   "cpu_seconds_per_update": 0.005090183593749992,
   "peak_rss_bytes": 376045568,
   "runs": [
    0.005094355468750006,
    0.005085765625000016,
    0.005090183593749992
   ],
   "updates_per_run": 256,
   "wall_runs": [
    0.005098645183352346,
    0.005090165039291605,
    0.005094431804536725
   ],
   "wall_seconds_per_update": 0.005094431804536725,
   "warmup_updates": 32
  },
  "F-OQ|1024": {
   "cpu_seconds_per_update": 0.004152144531249999,
   "peak_rss_bytes": 322174976,
   "runs": [
    0.004152144531249999,
    0.004156058593750001,
    0.004147371093750001
   ],
   "updates_per_run": 256,
   "wall_runs": [
    0.004155540851570549,
    0.004159389484357234,
    0.00415061751164103
   ],
   "wall_seconds_per_update": 0.004155540851570549,
   "warmup_updates": 32
  },
  "F-OQ|16384": {
   "cpu_seconds_per_update": 0.009252121093750003,
   "peak_rss_bytes": 354369536,
   "runs": [
    0.009337843750000005,
    0.009252121093750003,
    0.009251160156249993
   ],
   "updates_per_run": 256,
   "wall_runs": [
    0.009346040363197972,
    0.009260567054752755,
    0.009259316570478404
   ],
   "wall_seconds_per_update": 0.009260567054752755,
   "warmup_updates": 32
  },
  "F-OQ|256": {
   "cpu_seconds_per_update": 0.0034214921875,
   "peak_rss_bytes": 320716800,
   "runs": [
    0.0034276835937499996,
    0.0034214921875,
    0.003418781250000001
   ],
   "updates_per_run": 256,
   "wall_runs": [
    0.0034305188828511746,
    0.0034242827150592348,
    0.003421550781240512
   ],
   "wall_seconds_per_update": 0.0034242827150592348,
   "warmup_updates": 32
  },
  "F-OQ|4096": {
   "cpu_seconds_per_update": 0.007013417968749998,
   "peak_rss_bytes": 325533696,
   "runs": [
    0.006998496093750001,
    0.00701755078125,
    0.007013417968749998
   ],
   "updates_per_run": 256,
   "wall_runs": [
    0.00700424739443406,
    0.007023344074241322,
    0.007018958656317409
   ],
   "wall_seconds_per_update": 0.007018958656317409,
   "warmup_updates": 32
  },
  "H8|1024": {
   "cpu_seconds_per_update": 0.002974480468749985,
   "peak_rss_bytes": 376045568,
   "runs": [
    0.002974480468749985,
    0.0029822851562499864,
    0.0029702539062499977
   ],
   "updates_per_run": 256,
   "wall_runs": [
    0.0029768732110824203,
    0.0029845616836610134,
    0.0029727036130680062
   ],
   "wall_seconds_per_update": 0.0029768732110824203,
   "warmup_updates": 32
  },
  "H8|16384": {
   "cpu_seconds_per_update": 0.004588148437499995,
   "peak_rss_bytes": 376045568,
   "runs": [
    0.004641042968749981,
    0.004588148437499995,
    0.00458212890625001
   ],
   "updates_per_run": 256,
   "wall_runs": [
    0.004644893554996088,
    0.0045921070973236056,
    0.00458602897288074
   ],
   "wall_seconds_per_update": 0.0045921070973236056,
   "warmup_updates": 32
  },
  "H8|4096": {
   "cpu_seconds_per_update": 0.003311808593749993,
   "peak_rss_bytes": 376045568,
   "runs": [
    0.0033110000000000084,
    0.003311808593749993,
    0.0033169179687499994
   ],
   "updates_per_run": 256,
   "wall_runs": [
    0.0033138740232061537,
    0.0033146985701932863,
    0.0033197270508935617
   ],
   "wall_seconds_per_update": 0.0033146985701932863,
   "warmup_updates": 32
  },
  "R2|16384": {
   "cpu_seconds_per_update": 0.004507867187499959,
   "p
```

## Estimated storage traffic (arithmetic and simulation, no device)

```json
{
 "P_F-OQ_f2048_n1024_d1_i2101": {
  "actual_capacity_misses": 6047,
  "arm": "F-OQ",
  "degenerate": false,
  "disclaimer": "arithmetic and simulation, no device: not a storage measurement; value pages only, keys assumed in RAM; no reduction is called locality",
  "e_ratio": 1.024741569225555,
  "facts": 2048,
  "key_bytes_label": "identity from section 7.4 (K x 16 x 4), not an estimate",
  "key_bytes_scored_per_query_if_keys_on_storage": 65536,
  "kind": "simulation",
  "label": "P_F-OQ_f2048_n1024_d1_i2101",
  "null_capacity_misses": [
   5922,
   5918,
   5863
  ],
  "null_miss_rate": 5.7626953125,
  "pages_per_query_identity_layout": {
   "32": 7.2197265625,
   "8": 7.81787109375
  },
  "queries": 2048,
  "schema": 1,
  "setting": {
   "cache_fraction": 0.25,
   "rows_per_page": 8,
   "tie": "asc"
  },
  "setting_note": "READING / PENDING LEAD REVIEW: the ADR says 'at one setting' without naming it",
  "slots": 1024,
  "study": "P10S1",
  "update": 8192,
  "value_bytes_per_query": 1024,
  "working_set_slots": 1024
 },
 "P_F-OQ_f2048_n4096_d1_i2101": {
  "actual_capacity_misses": 6437,
  "arm": "F-OQ",
  "degenerate": false,
  "disclaimer": "arithmetic and simulation, no device: not a storage measurement; value pages only, keys assumed in RAM; no reduction is called locality",
  "e_ratio": 1.150834326579261,
  "facts": 2048,
  "key_bytes_label": "identity from section 7.4 (K x 16 x 4), not an estimate",
  "key_bytes_scored_per_query_if_keys_on_storage": 262144,
  "kind": "simulation",
  "label": "P_F-OQ_f2048_n4096_d1_i2101",
  "null_capacity_misses": [
   5646,
   5564,
   5570
  ],
  "null_miss_rate": 5.462239583333333,
  "pages_per_query_identity_layout": {
   "32": 7.80078125,
   "8": 7.95361328125
  },
  "queries": 2048,
  "schema": 1,
  "setting": {
   "cache_fraction": 0.25,
   "rows_per_page": 8,
   "tie": "asc"
  },
  "setting_note": "READING / PENDING LEAD REVIEW: the ADR says 'at one setting' without naming it",
  "slots": 4096,
  "study": "P10S1",
  "update": 8192,
  "value_bytes_per_query": 1024,
  "working_set_slots": 3381
 },
 "P_F-OQ_f32768_n16384_d1_i2101_u16384": {
  "actual_capacity_misses": 98481,
  "arm": "F-OQ",
  "degenerate": false,
  "disclaimer": "arithmetic and simulation, no device: not a storage measurement; value pages only, keys assumed in RAM; no reduction is called locality",
  "e_ratio": 1.0201267894507862,
  "facts": 32768,
  "key_bytes_label": "identity from section 7.4 (K x 16 x 4), not an estimate",
  "key_bytes_scored_per_query_if_keys_on_storage": 1048576,
  "kind": "simulation",
  "label": "P_F-OQ_f32768_n16384_d1_i2101_u16384",
  "null_capacity_misses": [
   96598,
   96495,
   96521
  ],
  "null_miss_rate": 5.8922119140625,
  "pages_per_query_identity_layout": {
   "32": 7.943756103515625,
   "8": 7.986175537109375
  },
  "queries": 32768,
  "schema": 1,
  "setting": {
   "cache_fraction": 0.25,
   "rows_per_page": 8,
   "tie": "asc"
  },
  "setting_note": "READING / PENDING LEAD REVIEW: the ADR says 'at one setting' without naming it",
  "slots": 16384,
  "study": "P10S1",
  "update": 16384,
  "value_bytes_per_query": 1024,
  "working_set_slots": 16384
 },
 "P_F-OQ_f32768_n4096_d1_i2101_u16384_y786432": {
  "actual_capacity_misses": 97686,
  "arm": "F-OQ",
  "degenerate": false,
  "disclaimer": "arithmetic and simulation, no device: not a storage measurement; value pages only, keys assumed in RAM; no reduction is called locality",
  "e_ratio": 1.0048931697933348,
  "facts": 32768,
  "key_bytes_label": "identity from section 7.4 (K x 16 x 4), not an estimate",
  "key_bytes_scored_per_query_if_keys_on_storage": 262144,
  "kind": "simulation",
  "label": "P_F-OQ_f32768_n4096_d1_i2101_u16384_y786432",
  "null_capacity_misses": [
   97099,
   97349,
   97183
  ],
  "null_miss_rate": 5.933247884114583,
  "pages_per_query_identity_layout": {
   "32": 7.787841796875,
   "8": 7.95098876953125
  },
  "queries": 32768,
  "schema": 1,
  "setting": {
   "cache_fraction": 0.25,
   "rows_per_page": 8,
   "tie": "asc"
  },
  "setting_note": "READING / PENDING LEAD REVIEW: the ADR says 'at one setting' without naming it",
  "slots": 4096,
  "study": "P10S1",
  "update": 16384,
  "value_bytes_per_query": 1024,
  "working_set_slots": 4096
 },
 "P_F-OQ_f8192_n1024_d1_i2101_y393216": {
  "actual_capacity_misses": 23986,
  "arm": "F-OQ",
  "degenerate": false,
  "disclaimer": "arithmetic and simulation, no device: not a storage measurement; value pages only, keys assumed in RAM; no reduction is called locality",
  "e_ratio": 1.0042426103218243,
  "facts": 8192,
  "key_bytes_label": "identity from section 7.4 (K x 16 x 4), not an estimate",
  "key_bytes_scored_per_query_if_keys_on_storage": 65536,
  "kind": "simulation",
  "label": "P_F-OQ_f8192_n1024_d1_i2101_y393216",
  "null_capacity_misses": [
   23931,
   23805,
   23918
  ],
  "null_miss_rate": 5.831217447916667,
  "pages_per_query_identity_layout": {
   "32": 7.1922607421875,
   "8": 7.8099365234375
  },
  "queries": 8192,
  "schema": 1,
  "setting": {
   "cache_fraction": 0.25,
   "rows_per_page": 8,
   "tie": "asc"
  },
  "setting_note": "READING / PENDING LEAD REVIEW: the ADR says 'at one setting' without naming it",
  "slots": 1024,
  "study": "P10S1",
  "update": 8192,
  "value_bytes_per_query": 1024,
  "working_set_slots": 1024
 },
 "P_F-OQ_f8192_n16384_d1_i2101": {
  "actual_capacity_misses": 24672,
  "arm": "F-OQ",
  "degenerate": false,
  "disclaimer": "arithmetic and simulation, no device: not a storage measurement; value pages only, keys assumed in RAM; no reduction is called locality",
  "e_ratio": 1.070446163858558,
  "facts": 8192,
  "key_bytes_label": "identity from section 7.4 (K x 16 x 4), not an estimate",
  "key_bytes_scored_per_query_if_keys_on_storage": 1048576,
  "kind": "simulation",
  "label": "P_F-OQ_f8192_n16384_d1_i2101",
  "null_capacity_misses": [
   22991,
   23168,
   22986
  ],
  "null_miss_rate": 5.627034505208333,
  "pages_per_query_identity_layout": {
   "32": 7.94677734
```

## Readings and open items that need the lead's review

- RULED (section 22 M6): analytic multiply-adds are those of one whole training update including the frozen backbone's forward and backward pass (formula in the config, checked against a FLOP count by a test) plus 4 x trainable parameters for AdamW
- RULED (section 22 (k), m3): a FASTER STEP [STORE ONLY; ORACLE-ADDRESSED] with no D-OQ cell prints DENSE NOT READ, one whose dense-speed comparison is undecided from the bounds prints DENSE SPEED UNDECIDED; neither blocks
- RULED (section 22 M5): where the dense matched-compute pair is MC-SHORT or MC-AMBIGUOUS the label is DENSE NOT ESTABLISHED AT MATCHED COMPUTE (<status>), never DENSE MATCHES; the matched-updates comparison with D-OQ is printed beside it, descriptively; as designed S1 cannot show that the store beats or matches a dense map at matched compute at 65,536 slots
- RULED (section 22 M7): among dense rates within 0.02 at the selection readout, the faster learner (a_use at U_P/2, U_P/4, down to U_P/16; the first difference of at least 0.02 decides), else the smaller learning rate
- RULED (section 22 (g)): DEP is read at every snapshot up to the run length, of both cells
- READING: i of KNN-W, KNN-W-IVF and DICT is computed from raw accuracy (there is no memory to swap)
- the costlier cell of a pair is read at U_P and the cheaper at the smallest snapshot of the MC grid whose cumulative cost is at least that; where the two cost measures give different costlier cells (MC-AMBIGUOUS, revision 5, section 5.4) the cell whose advantage would be claimed is read at U_P and the other at the smallest grid snapshot with multiplier at least the larger of r and 1/r: the pair counts as established, with the annotation, or is MC-SHORT
- READING: a multiplier above 6 has no snapshot on the MC grid and is MC-SHORT
- READING: the row-movement ratio printed with a verdict is the larger cell's total value-row movement over the smaller's at U_P, with the without-gradient share ratio beside it; OPTIMIZER-ASSISTED tests the share ratio; efficiency verdicts also print both at each cell's hit snapshot
- RULED (ADR-0021 section 22 (h)): for a label that favours the store (TREE_AHEAD [STORE ONLY; ORACLE-ADDRESSED], TREE_COMPETITIVE and every positive condition) a replicate counts only if both panels satisfy it; for a label that blocks (DENSE AHEAD, DENSE FASTER) a replicate counts if either panel satisfies it; PANEL-DISAGREE is the verdict when the panels give different verdicts
- RULED (section 22 (n)): robustness is read on Panel A and printed for both panels, accuracy retained = mean raw accuracy over three seeded masks; descriptive
- RULED (section 22 (m)): the seed block's spread is reported at U_P and U_run; descriptive
- RATIFIED (section 22 (c)): page misses at 8 rows per page, rho = 1/4, ascending tie rule; descriptive, enters no rule

## Decision map (recommendations only; nothing is authorized)

- 8. Capacity line inconclusive: no decision on that line.
- 11. DENSE HOLDS MORE AT SATURATION: per parameter, the dense map is the better store on this task; whatever the memory offers is then in its counted work and its sparse updates, and a scaling plan must say so.
- 12. Whatever the outcome, capacity from 16,384 to 65,536 slots stays untested and is proposed for P10-I.

## What S1 cannot establish (section 12)

- That a learned memory works without an oracle (no autonomous learned-memory success may be claimed from S1).
- That the language model can form the queries, or that any interface reaches the capacity measured here.
- Useful capability beyond recall of the trained facts; any improvement of a language model's behaviour.
- Efficiency, speed, latency or I/O: counted work is logical, simulated traffic is not a storage measurement, throughput is an in-RAM CPU figure for a 27,392-parameter backbone.
- Capacity where no cell is loaded; anything beyond the registered slots, facts and run lengths.
- Anything about natural-language knowledge, composition, reasoning, skewed fact frequency, another backbone, or a trainable backbone.
- That a dense lead (DENSE AHEAD) or a conventional retrieval that suffices means memory is not needed in general, or that a win over the dense control holds off this task.
- That a hierarchy helps locality, or that sublinear counted work is a finding about the tree.
- That 'more slots' differs from 'more store parameters': this read path cannot separate them.
- Generalization across facts. That a dense architecture other than D-OQ would not do as well.
- Capacity from 16,384 to 65,536 slots (16,384→65,536 NOT TESTED); bits per slot at 16,384 slots (not funded) and the 256-slot figure b(256), which is F-OQ's alone.
- That what a slot holds when full is a property of 'slots in general': it is one measurement at eight facts per slot, and a SATURATION-SUBPROPORTIONAL reading may come from crowding of the fixed width-16 oracle codes as the fact set grows, never from the store alone.
- That the dense control at saturation is more than one dense family with a rate chosen early in the run (at 65,536 updates at the loaded cells).
- That a capacity step is more than a necessary condition: under oracle addressing a positive step is close to foregone once the smaller cell is full.
- TRANSFER-POSITIVE, SYSTEM-POSITIVE, a failure of the ArborLM concept, Astra validation, or a human approval that is not recorded. No S1 outcome is ever summarised as 'ArborLM's capacity scales'.
