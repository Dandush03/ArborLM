# P9-I registered run, attempt 1 — stopped at the gates stage (2026-11-14)

- **Status: STOPPED BEFORE TRAINING. No cell was trained or evaluated; no interface arm has been observed.** Freeze commit `da9d077`, code `dd8b205`, run directory `experiments/P9IP-20261114T235955649302Z-8756ef5f9d1541bd9e0efaece6f7c27b` (kept).
- **What ran:** data generation (G1 passed) and the gates stage. The gates stage ended INCOMPLETE: G1 passed, G2 passed (the no-memory backbone is at chance on the registered panels), **G4 recorded one defect: "gradient reach failed for R2"**. By the frozen rule a failed gate stops the run; the train stage was not started.
- **A first launch command was refused by the argument parser** (the lead's shell passed all options as one word); nothing ran and nothing was charged.

## Cause (the lead's diagnosis; not yet audited)

The defect is in the gate's own test harness, not in arm R2. The gate checks gradient reach on the first 8 contexts of Panel A with a 4,096-slot model whose oracle-address table covers the first 2,048 facts. On real-proportion data those 8 contexts hold 64 facts with ids 2,482–29,279, none below 2,048, so R2 reads no slot and no gradient flows to its values, output projection or gate. The tiny DRY sizes hid this. `lead_diagnostic_r2_gradient_reach.py` reproduces it (output: all three R2 parameters unreached; 0 of 64 facts in the table). R2 itself reached 1.000 in the calibration and its forward was matched by the auditor.

## What this is and is not

- An engineering failure of a pre-training check. Not a result about any interface; nothing can be interpreted.
- Observed on registered seeds so far: the generated data's G1 checks, and the no-memory control counts of G2 (chance). No trained model.
- The lead's delegated approval (ADR-0017 §15.6) covered a single run of the frozen code and no re-run. A corrected gate is a code change after the freeze, so a second attempt needs the human lead's decision.

Charged: 5.6 s for the gates stage (947 s in total of 14,400 s). Astra review: NOT_PERFORMED.
