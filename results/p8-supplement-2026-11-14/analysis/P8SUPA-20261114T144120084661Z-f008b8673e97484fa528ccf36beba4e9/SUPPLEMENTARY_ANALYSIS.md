# SUPPLEMENTARY (ADR-0016) — not the registered P8 output

- Registered P8 study status: **INCOMPLETE**; registered decision: **none** (unchanged).
- The nested study_status and decision describe the 60-record supplementary input only. They are not the registered study's: the registered P8 study remains INCOMPLETE (55/60 simulated) with decision 'none'.
- Nested (supplementary, 60-record input) status: `COMPLETE`; mechanical decision-map letter: `c`. It authorizes nothing and is not a registered decision.
- Status: implementation self-check output. Not independent review, not Astra validation, not human approval. Astra review: NOT_PERFORMED.
- All values below are computed from the records (measured), none is hypothetical.

## Supplementary classes of the concentration controls (not registered classes)

| case | panel A | panel B | study class |
|---|---|---|---|
| C04 | QUALITY-FAILED | QUALITY-FAILED | QUALITY-FAILED |
| C05 | QUALITY-FAILED | QUALITY-FAILED | QUALITY-FAILED |

## Predictions of ADR-0016 section 2 (derived on paper before execution)

All nine hold: **True**.

| # | statement | checked | violations | holds |
|---|---|---|---|---|
| 1 | counted (post-warm-up) miss count is 0 for the actual stream | 344 | 0 | True |
| 2 | null and order-shuffled records equal the actual record | 200 | 0 | True |
| 3 | temporal-reuse ratio to null is exactly 1.0 | 10 | 0 | True |
| 4 | E is undefined (null mean below 0.05) in all five cells | 344 | 0 | True |
| 5 | supplementary class of C04 and C05 is QUALITY-FAILED on both panels | 6 | 0 | True |
| 6 | misses_warm = first_touch_warm = 0, misses_all = first_touch_all = distinct pages, and distinct pages <= 8 | 664 | 0 | True |
| 7 | the three null stream_sha256 values of a panel are identical | 10 | 0 | True |
| 8 | concentration_controls_bind is false and open_questions is [C09] | 2 | 0 | True |
| 9 | supplementary mechanical decision letter is 'c' (not a registered decision) | 1 | 0 | True |

## Comparison with the registered analysis (section 5, W5)

- analysis.json: ok = True; allowed differences seen: cases.C04, cases.C05, cells_with_complete_records, decision_inputs, missing_cells, study_status; disallowed: 0.
- cells.csv: ok = True
- pairs.csv: ok = True
- scorecard.csv: ok = True

## Claims this output does not make

- It is not the registered P8 output and does not supersede `analysis.json`.
- The registered study is not complete and its decision is not (c).
- The identity null carries no locality information; with one set E is undefined by construction. The supplement reuses the same traces and replicates nothing.
- No positive result for locality-aware training.
