# ADR-0017 — projected M5 resource budget (design revision 3)

**Update after decision 1 (2026-11-14):** the human lead raised the aggregate RSS cap to 24 GiB and raised the hour budget without giving a figure. The tables below are the pre-decision projection. With 24 GiB, three or four training workers fit in memory; whether they help depends on thread contention on six performance cores, which the rehearsal measures. Calibration and rehearsal are capped at 4 hours together. The run's hour cap is proposed at decision 2 as twice the rehearsal-based projection.

**A projection, not a measurement of the study.** It rests on one indicative timing of a stand-in memory update (`benchmark/indicative_update_timing.py`, output `benchmark/indicative_update_timing_run1.jsonl`) on a machine that was not isolated (load average about 3). The stand-in has no backbone, no real data and no ArborLM code. The auditor reproduced the training arithmetic and found the first version left out evaluation and under-costed the dense adapter (`REVIEW.md` M14); both are corrected here. The full-size rehearsal replaces every number before the freeze, and the caps are fixed only at the human lead's second decision.

## Machine

Apple M5 Max, 18 cores (6 performance + 12 efficiency), 48 GB unified memory, torch 2.8.0, CPU only. MPS is available and not used.

## Indicative timing (1,024 positions per update, 6 threads)

| Slots | Flat s/update | Tree (512 candidates) s/update | Peak RSS flat | Peak RSS tree |
|---|---|---|---|---|
| 4,096 | 0.004 | 0.033 | 0.31 GB | 0.50 GB |
| 16,384 | 0.013 | 0.032 | 0.47 GB | 0.51 GB |
| 65,536 | 0.043 | 0.032 | 1.11 GB | 0.57 GB |

The tree's time does not grow with N; the flat memory's grows about tenfold for a 16-fold memory. With 3 threads the 65,536-slot flat update took 0.058 s.

## Planning allowance

Three times the indicative time per update (backbone, exact top-k tie handling, instrumentation, regularizers, snapshots): flat 0.013 / 0.04 / 0.13 s; tree 0.10 s. The dense adapter at 65,536 slots does about three times the flat memory's arithmetic per position and is costed at 0.39 s (unmeasured). The R2 rung has no key scoring and is costed at 0.035 s.

## Training, exposure E = 32 (100 cells)

| Group | Cells | Updates | Minutes per cell | Serial hours |
|---|---|---|---|---|
| 65,536 flat-like (A1, A5 R1, A5b, A7, A10) | 13 | 8,192 | 18 | 3.8 |
| 65,536 learned tree (A2) | 3 | 8,192 | 14 | 0.7 |
| 65,536 dense (A8) | 2 | 8,192 | 53 | 1.8 |
| 65,536 R2 (A5) and fixed facts (A4) | 4 | 8,192 / 2,048 | 5 | 0.3 |
| 16,384 (A, B1, C1, D) | 64 | 1,024–2,048 | 1.5–7 | 2.9 |
| 4,096 | 14 | 2,048 | 0.5–3.5 | 0.35 |
| **Training, serial** | 100 | | | **about 9.9** |

## Evaluation and simulation

- Selections and weights are cached once per snapshot and panel; knock-outs, value permutation and group ablations reuse them and need no further key scoring.
- Interventions are evaluated only at the matched-exposure and fixed-compute snapshots.
- Allowance: 30% of training, about 3 serial hours, spread over four simulation workers. Uncached evaluation at 65,536 slots would cost about 15 hours (auditor's estimate) and is not permitted by the design.
- General-N simulator with sparse co-access counts: unmeasured; P8's simulation of 55 cells took 74 s at 4,096 slots.

## Projected charged wall time

| Exposure E (set by calibration) | 2 training workers | 3 training workers |
|---|---|---|
| 32 | about 5.8 h | about 4.1 h |
| 64 | about 10.7 h | about 7.4 h |
| 128 | about 20.6 h | about 14.0 h |

These contain the threefold timing allowance. Three workers assume no thread contention, which the rehearsal must test (6 performance cores).

## Calibration and rehearsal (before the freeze)

- Calibration: probes on frozen states; R2 curves to E = 128 at three sizes (the largest is 32,768 updates at about 0.035 s, about 20 minutes); controls. Projected under 1 hour.
- Rehearsal: one cell of each kind at full size for a fixed number of updates, plus one full evaluation and one simulation. Projected under 1 hour.
- **Proposed cap for both together at decision 1: 3 hours, 3 GiB sampled RSS per worker, 8 GiB aggregate.**

## Caps for the registered run (proposed now, fixed at decision 2)

| Limit | Human draft | Projection-based proposal | Reason |
|---|---|---|---|
| Sampled RSS per worker | 2 GiB | 3 GiB | the 65,536-slot flat stand-in peaked at 1.11 GB; real code is expected near 1.5 GB |
| Aggregate RSS | 8 GiB | 8 GiB with two training workers (default); 12 GiB only if a third worker is granted at decision 2 | 2 × 3 GiB plus four simulation workers |
| Charged execution | 8 h | twice the rehearsal-based projection: about 8–12 h at E = 32, about 15–21 h at E = 64 | twofold headroom |

**By this budget's figures, twice the E = 32 projection with three workers is 8.2 h, just above 8 h (the auditor's recount gives 7.6 h, or 8.4 h if key-32 cells cost twice key-16, which this table does not yet assume). With two workers — the draft's limit and this design's default — or at E ≥ 64, 8 hours do not hold twofold headroom even after the registered reductions. The human lead must then raise the cap or the study does not run as registered.**

## Registered reductions, in this order, if the human lead keeps 8 hours

1. Drop the B102 replicates at 65,536 slots (2 cells). Rule change: the 16K→64K step uses the two B101 seeds.
2. Drop block A7 at 65,536 slots (4 cells). Rule change: KEY-WIDTH-LIMITED is not assessed.
3. Drop the dense adapter's second seed at 65,536 slots (1 cell). Rule change: beats-dense at 64K compares both memory seeds with the single dense seed.
4. If E = 128 is selected: the 65,536-slot size is run for flat R0, tree R0, R2 and dense only. Rule change: EMPTY-SLOT-EFFECT (defined from 4K to 64K), KEY-WIDTH-LIMITED, OPTIMIZER-DEPENDENT at 16K→64K, and the 64K ladder terms R2 − R1, R1 − R0a and R0a − R0, are not assessed; a CAPACITY_POSITIVE class is then printed with "OPTIMIZER-DEPENDENT: not assessed", and decision item 1 needs the human lead's explicit acceptance of that.

No reduction changes a threshold; each changes the rule stated with it. A reduction chosen after the rehearsal is recorded as a revision and approved at decision 2. The batch is never changed at one size only; if memory is short the score matrix is chunked, which leaves gradients identical.

## Isolation

- Timing (the rehearsal's per-update times) runs alone: no other study worker, no git or publishing activity; load average and thermal state recorded before and after.
- Scientific cells are not timing evidence. Their wall times are recorded and no efficiency claim rests on them.

## Disk

Snapshots carry optimizer state: about 50 MB at 65,536 slots. About 4 snapshots × 24 cells ≈ 5 GB at that size, under 8 GB in total, git-ignored.

## What the rehearsal must settle

1. Real per-update time and RSS for flat, tree, dense, R2 and regularized cells at 65,536 slots.
2. Cost of cached evaluation, knock-outs and group ablations.
3. Contention with two and with three training workers.
4. Cost of the general-N simulator and sparse co-access layouts at 65,536 slots.
5. RSS of a simulation worker at 65,536 slots: with two training workers at 3 GiB, the 8 GiB aggregate leaves about 0.5 GiB for each of four simulation workers.
