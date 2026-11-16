# P9-II rehearsal (ADR-0019 §10, §12) — 2026-11-15 UTC

- **What ran:** 30 rehearsal items covering every arm, phase and size of the matrix, on rehearsal seed set 5, six single-thread workers, code at commit `3d779e1`. Only time, memory, shapes, counts and identity are written (whitelist enforced in code); no loss or accuracy. Run directory `experiments/P9IIH-20261115T071753736302Z-733bbf7ebca44117a5bdf2792f90940b`. Charged 88 s to Budget A.
- The rehearsal ran with the costliest value of each grid (A4 reading all N slots at the start), not the calibrated values, so the projections are upper estimates for A4.
- Not yet audited. Astra review: NOT_PERFORMED.

## Measured rates (with six workers)

| Size | Seconds per update | Peak memory |
|---|---|---|
| 4,096 slots | 0.009–0.011 (A4's first phase 0.032) | 0.36–0.40 GiB |
| 16,384 slots | 0.012–0.018 (A4: 0.137 reading all slots, 0.060 mid-schedule) | 0.46–0.68 GiB |
| 65,536 slots | 0.035–0.060 | 0.73 GiB peak overall |

## Projections from these rates (projections, not results)

| Stage | Projected | Doubled (the headroom rule) | Budget left | Fits |
|---|---|---|---|---|
| Stage 1, 128 cells | 2,029 s (0.56 h) | 4,058 s | Budget A: 13,970 s of 14,400 s | yes |
| Stage 2, A0 only | 1,134 s | 2,267 s | Budget B: 10,800 s | yes |
| Stage 2 with A1, or A2, or A5-C, or two of these | 1,650–3,450 s | 3,300–6,900 s | 10,800 s | yes |
| Stage 2 with A4 (alone or with another arm) | 5,720–7,230 s | 11,440–14,460 s | 10,800 s | **no at the rehearsed worst-case setting** |
| Stage 3, 6–8 cells | 310–705 s | 620–1,410 s | what Stage 2 leaves | depends |

- Memory: the largest worker peaks at 0.73 GiB against 3 GiB; six workers stay far below 24 GiB.
- Charged to Budget A so far: 430 s (generation and gates on rehearsal seeds, calibration, rehearsal).
