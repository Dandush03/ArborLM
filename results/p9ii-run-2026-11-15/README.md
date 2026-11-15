# P9-II registered run (ADR-0019 revision 4) — 2026-11-15

- **Status of this file:** the lead's (Fable 5.2) description of the records. **Not independently recomputed at the time of writing.** No outcome is accepted by the human lead. Astra review: NOT_PERFORMED.
- **Freeze commit:** `d2746d3ba57b9666a6100bda8b5d0e7414883e3a`. Run directory `experiments/P9IIP-registered-20261115b` in the main checkout (git-ignored, 3.1 GB; snapshots, per-update logs and data stay there).
- **How it was launched:** the fixed scripts `studies/p9ii/launch/<stage>.sh <run-dir> <freeze-commit>` in the order generate, gates, stage1, stage1_gate, stage2, stage3_gate, stage3, analysis, report, through the two wrapper scripts kept here (`p9ii_run_a.sh`, `p9ii_run_b.sh`). `launch_log.txt` is the unedited log. The first generation attempt was refused before generating anything; see `results/p9ii-freeze-2026-11-15/GENERATE_ATTEMPT1.md`.
- **Every stage ended COMPLETE.** 174 cells trained and evaluated (Stage 1: 128, Stage 2: 40, Stage 3: 6); none failed.
- **Charged time:** Budget A 2,554 s of 14,400 s (calibration, rehearsals, generation, gates, Stage 1); Budget B 4,089 s of 10,800 s (Stages 2 and 3). Peak worker memory 0.75 GiB.

## Files

| File | Contents |
|---|---|
| `RESULTS.md`, `classes.csv`, `cells.csv`, `results.json` | the run's own report, copied unmodified |
| `analysis.json` | the analysis stage's full output |
| `gates.json`, `stage_gate_1.json`, `stage_gate_3.json`, `draw_plan.json` | gates, the two stage decisions, the frozen draw plan |
| `manifests/` | each stage's manifest |
| `cells/<label>/train.json`, `cells/<label>/eval/` | per-cell training record and evaluation records |
| `P9II-ledger-A.json`, `P9II-ledger-B.json` | charged-time ledgers |
| `SHA256SUMS` | checksums of everything above |

## The run's registered outcome (as printed, unaudited)

**ADDRESSING-RELIABLE: A5-D (LABEL-FREE), paired against A0 at 4,096: IMPROVES ON A0; at 16,384: NOT DISTINGUISHED FROM A0.** Interface carried forward by the registered order: A0. Stage 3 probe: SCALE PROBE UNINFORMATIVE.

| Stage | Slots | Arm | Class | Successes | Paired against A0 |
|---|---|---|---|---|---|
| 1 | 4,096 | A0 answer-only | UNRELIABLE | 4 / 16 | |
| 1 | 4,096 | A1 address loss kept | RELIABLE | 16 / 16 | IMPROVES ON A0 (d = 12) |
| 1 | 4,096 | A1-S random targets | FAILS | 0 / 16 | HARMS |
| 1 | 4,096 | A2 staged | FAILS | 0 / 16 | HARMS |
| 1 | 4,096 | A4 top-k anneal | FAILS | 0 / 16 | HARMS |
| 1 | 4,096 | A5-C centring | UNRELIABLE | 9 / 16 | IMPROVES ON A0 (d = 5) |
| 1 | 4,096 | A5-D diversity | RELIABLE | 16 / 16 | IMPROVES ON A0 (d = 12) |
| 2 | 16,384 (4U) | A0 | RELIABLE | 8 / 8 | |
| 2 | 16,384 (4U) | A1 | UNRELIABLE | 6 / 8 | NOT DISTINGUISHED (d = −2) |
| 2 | 16,384 (4U) | A1-S | FAILS | 0 / 8 | HARMS |
| 2 | 16,384 (4U) | A5-D | RELIABLE | 8 / 8 | NOT DISTINGUISHED (d = 0) |

Hypothesis readings printed by the run: H19-A not supported; H19-B supported; H19-C CONTRADICTED; H19-D CONTRADICTED; H19-F not supported; H19-G supported; H19-E supported for A1 and A5-D only.

## Observations by the lead (descriptive; enter no rule unless the ADR says so)

- At 16,384 slots and matched updates U, A0's Panel A accuracy is 0.030–0.037 in all 8 cells (chance), with 4–27 distinct top-1 slots; at 4U it is 0.994–0.998 in all 8. A5-D is 0.982–0.988 at U and 0.999 at 4U and is never in the collapsed category. The registered reading at 16,384 is at 4U, where both are RELIABLE.
- A5-C's seven Stage 1 failures have Panel A accuracy 0.989–0.999; they fail the held-out-template condition (H1 or H2 below 0.90 × own Panel A), e.g. H2 0.690 on draw 2.
- A1's two Stage 2 failures are also held-out-template failures (H2 0.876 against a line of 0.887; H1 0.888 against 0.888).
- The dense control A7 is 0.997–1.000 at 4,096 and 0.974–0.982 at 16,384 (4U), with H1/H2 0.80–0.89 there; the run prints DENSE AT CEILING. No memory arm is shown ahead of the dense model.
- Stage 3 (65,536 slots, 32 exposures per fact, A0 only): A0 0.031 and 0.030, A6 0.973 and 0.971, A7 0.132 and 0.123. By registration the probe can only be positive or uninformative.

## What this does not show

Everything in `RESULTS.md` under "What must not be claimed" applies. In particular: nothing about capacity, locality or natural language; A0 is untuned and the other arms are calibrated; no efficiency claim; no breakthrough is claimed.
