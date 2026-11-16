# P9-II rehearsal 2 and gates at real size (ADR-0019 §9–§12) — 2026-11-15 UTC

- **Why a second rehearsal:** the pre-freeze audit found that the first rehearsal used the costliest grid values instead of the calibrated ones, omitted per-task start-up time from the projection and ignored evaluation memory peaks. Code at commit `2e47e16`; the rehearsal is bound to the calibration record (sha256 `ad5d7ee2…`), on rehearsal seed set 5; time, memory, shapes and counts only.
- Run directories: `experiments/P9IIH-20261115T082413529266Z-cafbe1b47e1d478ba3c2882732830ffa` (rehearsal, 84 s charged) and `experiments/P9IIG-rehearsal-gates2-20261115T082352Z` (generation and gates, 20 s charged). Budget A charged in total: 534 s of 14,400 s.
- **Gates G1, G2, G4, G5, G6 at real size on the real backbones: all passed, no defect.**
- Not yet re-checked by the auditor. Astra review: NOT_PERFORMED.

## Projections with the calibrated values (projections, not results)

| Stage | Projected | Doubled | Budget left | Outcome of the rule |
|---|---|---|---|---|
| Stage 1, 128 cells | 2,072 s | 4,143 s | Budget A: 13,866 s | runs |
| Stage 2, A0 only | 1,154 s | 2,308 s | Budget B: 10,800 s | runs |
| Stage 2 with one or two of A1, A2, A5-C, A5-D | 1,706–3,519 s | 3,411–7,038 s | 10,800 s | runs |
| Stage 2 with A4 (alone or with any other arm) | 5,781–7,330 s | 11,561–14,660 s | 10,800 s | **NOT RUN — BUDGET** |
| Stage 3 (A0, A1, A5-C or A5-D selected) | 316–721 s | 631–1,441 s | what Stage 2 leaves | runs if it fits |

- Peak memory over all items, evaluation included: 1.00 GiB; doubled it is under the 3 GiB per-worker cap.
- **Consequence fixed before any registered data exist:** if the top-k curriculum arm A4 is among the arms that pass the Stage 1 gate, Stage 2 does not fit Budget B with 2× headroom and is not run, as §10 states (there is no reduced Stage 2). The outcome would then be read at 4,096 only for every arm.
