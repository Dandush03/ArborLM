# P10-S1 outcome record (ADR-0021 revision 5, sections 25.15–25.21)

Status of this record: the registered outcome of attempt 2, the independent recomputation, and the items that wait for the human lead. **No acceptance by the human lead is recorded yet.** Nothing here is a success claim. `Astra review: NOT_PERFORMED`. Claude review is not Astra review.

Every positive label carries `STORE ONLY; ORACLE-ADDRESSED`: addressing was supplied by an oracle.

## 1. The run

| Item | Value |
|---|---|
| Freeze commit | `76334ba6697b40f50aad8abb196628f4fd4cb739` (second freeze); Decision 2 at `cbde677` |
| Run directory | `experiments/P10S1-registered-attempt2-20261117` (not in git) |
| Training | COMPLETE, 178 of 178 cells, 0 failed, 49,251.2 s charged (stage cap 142,872 s) |
| Evaluation | COMPLETE, 193 tasks, 1,866 snapshot evaluations, 0 failed, 1,899.0 s charged (stage cap 5,444 s) |
| Throughput (`timing`) | INCOMPLETE: failed after 1.4 s on a code defect, before any measurement (section 3) |
| Simulate, analysis, report | COMPLETE (21 tasks, 1, 1) |
| Charged time, all attempts | 91,416.7 s (25.39 h) of the 53-hour cap (190,800 s); no cut |
| Study status (registered) | COMPLETE: 185 reads, 0 missing, 0 failed |

Attempt 1 ended S1-INCOMPLETE on an engineering stop caused by the lead (ADR-0021 sections 25.19 and 25.20). Its training manifest is in `attempt1/`. Its cells were not opened, evaluated or compared.

The hour cap was raised from 49 to 53 hours (C_max 50 to 54) so that the second attempt fitted after the time charged to attempt 1. The human lead, told of this before the second freeze, wrote on 2026-11-17: "im ok with you increasing the caps".

## 2. Registered outcome (from `RESULTS.md`, by the registered rules)

| Line | Outcome |
|---|---|
| Capacity | CAPACITY-INCONCLUSIVE: F-OQ DEPENDENCE_FAILED; F-OQ-IVF DEPENDENCE_FAILED; T-OQ INTERMEDIATE; 16,384→65,536 NOT TESTED |
| Saturation | SATURATION-INCONCLUSIVE: F-OQ INTERMEDIATE; T-OQ SATURATION_NOT_MEASURED |
| Efficiency | EFFICIENCY-NEGATIVE (DENSE FASTER), sizes 1,024–16,384 |
| Milestone question 1 | Not established |

Also registered: H8 CAPACITY_ONE_TRANSITION, UNDERTRAINED-AT-U_P; F-OQ and H8 DENSE AHEAD; DENSE HOLDS MORE AT SATURATION for F-OQ, F-OQ-IVF and T-OQ; hierarchy TREE_BEHIND; DICT DOMINATES ON THIS TASK; conventional retrieval not sufficient for the three memory arms.

No line is positive for the store. Capacity from 16,384 to 65,536 slots was not tested.

## 3. Throughput

The registered stage failed on a defect of the frozen code (it asks for the F-OQ cell at 2,048 facts and 256 slots, which the frozen plan does not run). The failed record and log are in `manifests/`. For the registered run, throughput is NOT MEASURED, for an engineering reason. No outcome line uses it.

A supplementary measurement (ADR-0021 section 25.21; `studies/p10s1/throughput_supplement.py`, run once at commit `7007caf` with a clean tree) is in `supplement/throughput_supplement.json`. It is not the registered stage and enters no outcome line. Load average at its single check: 0.998. Read path only, in RAM, one process; median queries per second over five repeats:

| Arm | Slots | Batch 1 | Batch 128 |
|---|---|---|---|
| F-OQ | 1,024 | 19,177 | 186,189 (UNSTABLE, CV 6.0%) |
| F-OQ | 4,096 | 14,029 | 42,675 |
| F-OQ | 16,384 | 7,292 | 36,770 |
| F-OQ-IVF | 1,024 | 8,543 (UNSTABLE, CV 5.2%) | 126,146 |
| F-OQ-IVF | 4,096 | 7,097 | 45,766 |
| F-OQ-IVF | 16,384 | 4,341 | 21,291 |
| T-OQ | 1,024 | 10,106 | 89,358 |
| T-OQ | 4,096 | 10,211 | 88,569 |
| T-OQ | 16,384 | 10,132 | 85,761 |
| H8 | 1,024 | 126,893 | 4,241,055 |
| H8 | 4,096 | 128,003 | 4,216,190 |
| H8 | 16,384 | 126,684 | 4,171,348 |
| D-OQ | 1,024 | 107,879 | 549,481 |
| D-OQ | 4,096 | 45,367 | 111,604 |
| D-OQ | 16,384 | 16,768 | 40,775 |

Skipped: F-OQ at 2,048 facts / 256 slots (no registered cell). Two of 30 figures are UNSTABLE under the registered 5% rule and stand as such; the measurement is not repeated. These are in-RAM CPU figures for a 27,392-parameter backbone: not storage I/O, not latency of a language model, not measured efficiency of a system.

## 4. Independent recomputation

Performed by the `arbor-auditor` subagent (Opus 5.5, from session metadata) with its own code from the raw cell records; report and scripts in `audit/`. The lead (Fable 5.2) designed and ran the study and wrote this record.

- All registered labels reproduce: 1,085 comparisons against `analysis.json`, 0 differences. Stage manifests, code and data identities and gates G1–G9 check.
- The throughput diagnosis is confirmed, and that no outcome line depends on that stage.

Findings that bear on how the result is read:

1. **The DEPENDENCE_FAILED labels rest on four early snapshots.** Every failure is the condition a_use ≥ 0.95 × raw accuracy at 2,048 updates (ratios 0.9425–0.9471). The reference arm R2, whose dependence is given by construction, fails the same condition 12 times at 512–1,024 updates. Ruling section 22 (g) (DEP read at every snapshot) does produce the registered label. Read only at the snapshots the verdicts use, F-OQ would be CAPACITY_SUPPORTED and, being DENSE AHEAD, the capacity outcome would be CAPACITY-NEGATIVE (b). The registered CAPACITY-INCONCLUSIVE is therefore the label more favourable to the store. The registered label stands; the alternative reading is recorded, not adopted.
2. **DENSE FASTER holds at one of the two cells.** At 2K/4K, 5 of 5 replicates; at 8K/16K, 0 of 5 (D-OQ costs 1.32–1.87 times T-OQ's multiply-adds). The code labels the arm DENSE FASTER if any cell qualifies (`analysis.py`, line 631); ADR section 8.8 does not say how two cells combine, and the choice is not among the listed readings. If every cell had to qualify, the efficiency line would be EFFICIENCY-POSITIVE [STORE ONLY; ORACLE-ADDRESSED] for T-OQ. This is an unregistered reading that decided an outcome line. PENDING HUMAN LEAD RULING. The registered label is not changed here.
3. **The seed-block section of `RESULTS.md` is wrong.** `analysis.py` (lines 167–169) stores the F-OQ-IVF read over the F-OQ read of a seed-block cell, so the 28 lines compare the wrong reads (for example 3.172 bits printed where the F-OQ spread is 0.0025; "init seed dominates" printed 28 of 28 where the correct comparison gives the data draw in 24 of 28). The section is descriptive and enters no rule. `RESULTS.md` is kept as the frozen code wrote it; the correct figures are in `audit/a5b_seedblock_bug.out`.
4. **At matched compute, F-OQ is ahead of D-OQ at 32K/16K** by 0.24–0.33 bits in 5 of 5 replicates; the DENSE AHEAD label comes from matched updates (4 of 5) and D-OQ's best snapshot (5 of 5). The report prints the label without this, against section 8.5.
5. Smaller report defects: not-full replicates are dropped from the saturation printout and only Panel A is printed; "185 cells read" counts 150 cells plus 35 F-OQ-IVF reads (178 cells exist, 28 of them seed-block); T-OQ SATURATION_NOT_MEASURED hides that rho is below 3.0 in all five replicates; the "Isolated timing" section is the rehearsal's record, unlabelled; `plan.json` prints a headroom cap of 194,400 s beside the cap of 190,800 s.

Mean a_use over five replicates and both panels, at U_P → at the run length:

| Cell | F-OQ | T-OQ | H8 | D-OQ |
|---|---|---|---|---|
| 2K/1K | 0.991 → 0.999 | 0.787 → 0.931 | 0.828 → 0.879 | not run |
| 2K/4K | 1.000 → 1.000 | 0.989 → 1.000 | 1.000 → 1.000 | 1.000 → 1.000 |
| 8K/1K | 0.390 → 0.654 | 0.176 → 0.416 | 0.209 → 0.344 | 0.770 → 0.918 |
| 8K/4K | 0.948 → 0.996 | 0.469 → 0.769 | 0.770 → 0.879 | 0.996 → 1.000 |
| 8K/16K | 0.999 → 1.000 | 0.920 → 0.996 | 1.000 → 1.000 | 0.999 → 1.000 |
| 32K/4K | 0.392 → 0.637 | 0.151 → 0.323 | 0.243 → 0.346 | 0.576 → 0.901 |
| 32K/16K | 0.916 → 0.992 | 0.401 → 0.697 | 0.812 → 0.879 | 0.957 → 0.999 |

The memory arms use learning rate 0.003, untuned by design; D-OQ uses its calibrated rate (0.1 or 0.03).

## 5. Waiting for the human lead

1. Acceptance of the registered outcome as recorded in section 2, with the audit's findings beside it.
2. A ruling on finding 2 (how DENSE FASTER combines across cells). Whatever the ruling, the label the frozen code printed stays in the record as printed.
3. Whether findings 1 and 2 are carried into P10-I as rules written in advance (an early-snapshot DEP rule; an explicit rule for combining cells).

No merge to main, no P10-I drafting and no further run follows from this record without the human lead's word.
