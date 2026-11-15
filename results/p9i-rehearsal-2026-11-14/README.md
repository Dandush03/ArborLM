# P9-I rehearsal (ADR-0017 Part I, §I.12 step 5) — 2026-11-14

- **What ran:** all 57 cells for 64 updates each and one full evaluation each, on rehearsal draw 2, six single-thread workers, code at commit `939b4bf`. Only time, memory, shapes, counts and identity were written; no loss or accuracy was read out (whitelist enforced in code). Run directory `experiments/P9IH-20261114T231255388625Z-8c6758d15894479b840ff5b5afd93630`. Charged 101 s.
- Files: `rehearsal_cells.csv`, `manifest.json`, `ledger_after_rehearsal.json`.

## Measurements (with six workers running)

| Size | Seconds per update (memory arms) | Peak memory, training | Evaluation per cell | Peak memory, evaluation |
|---|---|---|---|---|
| 4,096 | 0.008–0.012 | 0.33 GiB | about 1 s | 0.47 GiB |
| 16,384 | 0.013–0.015 | 0.36 GiB | about 3 s | 0.74 GiB |
| 65,536 | 0.035–0.049 | 0.48 GiB | 20–27 s | 1.49 GiB |

## Projection at U = 8,192 (from these measurements; a projection, not a result)

- Training: 2.32 hours summed over cells, so about 25–30 minutes with six workers; the longest cell about 7 minutes.
- Evaluation: about 6 minutes summed, about 1–2 minutes with six workers.
- Largest worker memory 1.49 GiB against the 3 GiB cap; six workers stay far below 24 GiB.
- Charged so far 930 s of 14,400 s. The run is projected at under 2,400 s.

## Stage caps fixed for the run (lead)

generate 300 s, gates 600 s, train 3,600 s, evaluate 900 s, analyze 300 s, report 300 s.

Astra review: NOT_PERFORMED.
