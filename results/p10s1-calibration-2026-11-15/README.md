# P10-S1 calibration (ADR-0021 revision 4, §10.1) — 2026-11-15

- **Status:** the lead's (Claude Fable 5.2) reading of the calibration record. **Not independently recomputed at the time of writing.** Calibration draws `p10s1-cal-1` and `-2`, initialization seed 2191; no registered seed. Calibration accuracies are calibration, never results. Astra review: NOT_PERFORMED.
- **Code:** commit `3ad821a`. Run directory `experiments/P10S1C-20261115T172402822940Z-5e33fb08d1104815a21110f1f308c27c` (git-ignored). 46 of 46 runs completed. Charged 5,664 s of the 57,600 s cap (the calibration shared the machine with P10-S0's rehearsal and other work).
- Files: `calibration.json`, `calibrate_manifest.json`, `ledger_after_calibration.json`.

## Outcome: RETURN TO THE HUMAN LEAD before the freeze

`load_decision.action = RETURN_TO_LEAD`: "at 4,096 slots neither load 2 nor load 8 is loaded: no registered 4,096-slot cell is predicted loaded". By the same rule the 16,384-slot table has no loaded load either. Under ADR-0021 §10.1 item 0 the lead does not improvise a row; the human lead may stop, fund a row, or direct that S1 run as it is with the capacity line fixed as CAPACITY NOT TESTED — NO LOADED CELL WITHIN BUDGET.

## Load table (F-OQ; bits per fact, ceiling 5.0; "loaded" = plateaued and at most 4.0 at the registered run length)

| Slots | Facts | Load | Best within the registered run (two draws, two panels) | At 65,536 updates | Plateaued | Loaded |
|---|---|---|---|---|---|---|
| 4,096 | 8,192 | 2 | 4.94–4.96 | 4.96 | yes | no (at ceiling) |
| 4,096 | 16,384 | 4 | 3.99–4.03 | 4.06–4.12 | no | no |
| 4,096 | 32,768 | 8 | 1.77–1.86 | 1.89–1.94 | no | no |
| 4,096 | 65,536 | 16 | 0.64–0.68 | 0.72–0.75 | no | no |
| 16,384 | 8,192 | 0.5 | 5.00 | 5.00 | yes | no (at ceiling) |
| 16,384 | 32,768 | 2 | 4.69–4.72 | 4.85–4.87 | no | no |
| 16,384 | 65,536 | 4 | 2.79–2.90 | 3.49–3.54 | no | no |
| 16,384 | 131,072 | 8 | 0.84–0.97 | 1.46–1.52 | no | no |

Registered run lengths: 49,152 updates at 4,096 slots, 32,768 at 16,384 slots.

**What it means.** Every cell is either at its ceiling or still improving when its run ends. No cell saturates below the ceiling within the registered run lengths, so the capacity question (does a larger store hold more once the smaller one is full?) has no "full" smaller store to start from. This is the confound S1 was built to separate: what limits the heavily loaded cells here is updates, not storage. It repeats, at real size, what the design's stand-in showed (ADR-0021 §1 fact 11).

## Other calibration outputs

- **U_P check:** stands (R2 and F-OQ reach their floors at every diagonal cell at U_P = 8,192).
- **H8:** no under-trained cell.
- **Dense control's learning rate:** 0.01 at both sizes, decided by minimum Panel A accuracy at U_P with no tie. **0.01 is the top of the grid {0.001, 0.003, 0.01}**, and at 65,536 slots the dense control reaches only 0.294 at U_P at that rate (0.998 at 16,384). The best rate being at the edge of the grid means a higher rate was not tried; whether that under-serves the dense control is PENDING LEAD REVIEW and is reported to the human lead with the load result.
- Cut 3 eligibility (information): 8K/64K and 32K/16K are both eligible, since neither smaller cell is predicted loaded.
