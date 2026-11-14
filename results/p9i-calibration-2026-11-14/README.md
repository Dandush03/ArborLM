# P9-I calibration (ADR-0017 Part I, §I.6) — 2026-11-14

- **What ran:** the controls and the two oracle rungs R1 and R2 only, at 4,096 / 16,384 / 65,536 slots, alphabet loss, on rehearsal draw 1 (data seeds 179101 upward), initialization seeds 1791 and 1792 on B101/O301 and 1791 on B102/O302. 19 tasks, all completed. No interface arm ran; the code refuses any other arm in this stage.
- **Code:** commit `939b4bf`. Run directory `experiments/P9IC-20261114T225847947431Z-b0cf703a0d7c4f7ab8f308c3de6ddf78` (git-ignored, 1.4 GB). Charged time 829 s of the 14,400 s cap.
- **Status:** the lead's reading. Not audited at the time of writing. Rehearsal seeds, not registered seeds. Astra review: NOT_PERFORMED.
- Files: `calibration.json` (the rule's inputs and output), `calibration_controls.json`, `manifest.json`, `ledger_after_calibration.json`.

## Rule

U is the smallest of {2,048, 4,096, 8,192, 16,384} updates at which, at every size, R2 ≥ 0.95 and R1 ≥ 0.90, each taken as the minimum over the two B101 runs and both panels.

## Numbers (minimum accuracy over the two B101 runs and Panels A and B)

| Slots / facts | Rung | 1,024 | 2,048 | 4,096 | 8,192 | 16,384 |
|---|---|---|---|---|---|---|
| 4,096 / 2,048 | R2 | 0.914 | 1.000 | 1.000 | 1.000 | 1.000 |
| 4,096 / 2,048 | R1 | 0.297 | 0.911 | 0.999 | 1.000 | 1.000 |
| 16,384 / 8,192 | R2 | 0.770 | 0.975 | 1.000 | 1.000 | 1.000 |
| 16,384 / 8,192 | R1 | 0.095 | 0.427 | 0.973 | 0.999 | 1.000 |
| 65,536 / 32,768 | R2 | 0.405 | 0.928 | 0.997 | 1.000 | 1.000 |
| 65,536 / 32,768 | R1 | 0.058 | 0.100 | 0.430 | **0.965** | 0.997 |

B102 replicate (reported, not in the rule) at 8,192 updates: R1 1.000 / 1.000 / 0.980, R2 1.000 at every size.

## Outcome

- **U = 8,192 updates. No size failed.** The binding cell is R1 at 65,536 slots: 0.430 at 4,096 updates, 0.965 at 8,192.
- Exposures per fact at U = 8,192: 512 / 128 / 32 at the three sizes.
- Controls: exact retrieval 1.000 at every size. The no-memory backbone is inside the chance interval in all 8 tests (for example 68 of 2,048 correct against an interval of 36–96), so G2 passes.

## What it means and does not mean

- With the alphabet loss and equal updates, both oracle rungs reach their thresholds at every size, including 4,096 slots, which failed its ceiling under the previous design. The earlier block was the loss and the update budget, as the audit said.
- The oracle-query rung needs more updates as the memory grows (it learns keys); the oracle-address rung is close to its ceiling by 2,048–4,096 updates.
- This says nothing about any interface arm, about capacity, or about locality. The sizes differ sixteenfold in exposures per fact.
