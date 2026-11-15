# P9-I (ADR-0017 Part I) — registered outcome and review, 2026-11-15 UTC

- **Study status: COMPLETE.** 57 of 57 cells, each 8,192 updates on registered seeds; gates G1, G2, G4 passed; no LEAKAGE flag. Freeze `dd39aa6`, code `8261f22`. Charged 2,691 s of the 14,400 s cap.
- **Registered outcome: NO_INTERFACE_SELECTED (§I.8.3 step 4).** No tested interface reached INTERFACE_WORKS at all three sizes within U updates. Lanes A–D of ADR-0017 stay blocked on this backbone.
- **Independent recomputation (Opus 5.5): no difference.** All 57 snapshots re-scored with a separate forward; every count, class, annotation and the selection match. `docs/reviews/p9i-results-2026-11-15/REVIEW.md`.
- Astra review: NOT_PERFORMED. Not a human approval of anything.

## Accuracy (Panels A and B, both B101 seeds; chance interval about 0.02–0.05)

| Arm | 4,096 slots / 2,048 facts | 16,384 / 8,192 | 65,536 / 32,768 | Class |
|---|---|---|---|---|
| R1 oracle-query reference | 1.000 | 0.999–1.000 | 0.967–0.972 | reference |
| R2 oracle address | — | 1.000 | — | reference |
| N natural query | 0.039–0.044 | 0.028–0.030 | 0.030–0.031 | FAILS |
| W7 window query | 0.037–0.041 | 0.028 | 0.030 | FAILS |
| E7 embedding window | — | 0.028 | — | FAILS |
| A4 attention | 0.040–0.043 | 0.028 | 0.030 | FAILS |
| A4E | — | 0.028 | — | FAILS |
| D plain | — | 0.036 | — | control |
| D7 dense window | — | 0.78–0.80 (B102: 0.44) | 0.127–0.131 | control |
| BB (block-0 attention trained) | 0.54–0.65 | 0.044–0.046 | 0.033–0.034 | PARTIAL / FAILS / FAILS |
| BB-0 (no memory) | 0.083–0.089 | 0.044–0.045 | 0.033–0.034 | control |
| BB-D | — | 0.040–0.044 | 0.030 | control |

- Dense comparison: NOT COMPARED everywhere (no arm is WORKS or PARTIAL where a dense comparator exists). Backbone contrast: not printed (both arms of each pair FAIL).
- BB arms: next-byte loss 2.35 → 3.92–4.69 nats (rise 67–100%): LANGUAGE MODELLING DEGRADED.
- BB at 16,384 is above the chance interval (361–374 of 8,192) and FAILS because it is below 0.25; that accuracy comes from the trained attention, not the memory (8 distinct slots; disabling the memory changes nothing).

## What the review found about why (diagnostic, not registered results)

- **No implementation defect.** The auditor's forward matches every trained snapshot and its gradients match the implementation's.
- **Address collapse, as in P8.** In the learned-query arms the mean cosine between queries of different facts is 0.95–1.00; 91–99% of the query is the same vector for every fact; 1–6 distinct top-1 slots; the loss stops at about ln 32, the answer-symbol marginal. In the collapsed state the query projection's gradient is about 2.7e-6 against 1.9e-2 on the output projection.
- **Draw sensitivity of W7 at 4,096.** On rehearsal and test draws (never registered seeds) the frozen code collapses within 64 updates and then, in 9 of 11 runs, escapes and reaches 0.94–0.98 within 8,192 updates at 4,096 slots; on the registered draw the escape had not started. At 16,384 the escape had begun but reached only 0.04 by 8,192 updates. A4 never escaped. A trainable bias or keys initialized at the queries did not prevent the collapse.
- D7 shows the seven-position window carries the identity and that the answer loss can use it through a dense map; W7's failure is about addressing, not missing information.

## What may and may not be said

- May: within 8,192 updates, on this backbone, with this loss, no tested interface worked; the oracle rungs show the memory stores and returns answers; the learned interfaces collapsed onto a few slots.
- Diagnostic only, moderate strength: "representable but not learned through the answer loss within U on the registered draw".
- May not: anything about capacity, utilization or locality; a failure of the ArborLM concept; that W7 cannot learn, or that it works; that BB shows a model communicating what it needs; any dense label from D7; anything about natural language.

## Deviations and process notes

- Attempt 1 stopped at the gates stage (`results/p9i-run-attempt1-2026-11-14/`); attempt 2 was approved by the human lead (ADR-0017 §15.7).
- The lead mistyped launch commands on three occasions in total across the two attempts (one before the gates of attempt 1; one covering evaluate, analyze and report of attempt 2); the argument parser refused each before anything ran. No stage ran twice.
- The before-training comparisons C4–C8 with attempt 1 were run by the lead and all held (output in `c4_c8_comparison_output.txt`, transcribed from the session); the auditor re-checked them independently.
- BB-0's two seeds are bit-identical runs (nothing in BB-0 depends on the seed); they count as one run.
