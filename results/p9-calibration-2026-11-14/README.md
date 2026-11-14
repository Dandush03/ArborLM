# P9 testbed calibration (ADR-0017 §12 step 4) — rehearsal seeds only, not a study result

Run `P9C-20261114T182513034263Z-a529fd1946ff4e52b19980bd6d3b6fcd`, rehearsal draw 0 (seeds 179001+), code at commit `44ebcbd`. Allowed arms only: no-memory and exact controls, frozen-hidden probes, the R2 readout rung. **Not yet audited.**

## Numbers

Chance accuracy is 1/32 = 0.031.

| Measurement | 2,048 facts / 4,096 slots | 8,192 / 16,384 | 32,768 / 65,536 |
|---|---|---|---|
| No-memory baseline, panel A (B101) | 0.037 | 0.031 | 0.032 |
| Exact retrieval | 1.000 | 1.000 | 1.000 |
| Frozen-hidden nearest stored state (B101 / B102) | 0.041 / 0.041 | 0.039 / 0.042 | 0.036 / 0.035 |
| Frozen-hidden linear probe, best identifier position (B101 / B102) | 0.073 / 0.075 | 0.076 / 0.083 | 0.082 / 0.083 |
| R2 accuracy at E = 32 (minimum over runs and panels) | 0.044 | 0.530 | 0.969 |
| R2 accuracy at E = 64 | 0.212 | 0.929 | 0.970 |
| R2 accuracy at E = 128 | 0.723 | 0.971 | 0.970 |
| Updates at E = 32 / 64 / 128 | 512 / 1,024 / 2,048 | 2,048 / 4,096 / 8,192 | 8,192 / 16,384 / 32,768 |

G2 (8 tests) and the Lane D G2 family (4 tests) pass.

## Output of the registered rule

`selected_exposure = 128`; `task_ceiling_fail = [4096]`.

## Lead's reading (not audited)

1. **The frozen block exposes almost none of the identifier at the answer site.** Nearest stored state is 0.035–0.042 against chance 0.031; the best per-position linear probe is 0.07–0.08.
2. **R2 accuracy follows the number of optimizer updates, not exposures per fact.** About 2,048 updates give 0.68–0.89 at either size; 4,096 or more give 0.97. The smallest size has the fewest updates at a given E and therefore fails the 0.95 ceiling, which is an artefact of the matched-exposure rule, not a readout limit.
3. **B101 plateaus at 0.9697** (about 31/32) while B102 reaches 0.999: one answer symbol appears unreachable through B101's frozen final layers. Hypothesis, to be checked.

Under ADR-0017 as approved, a size marked TASK_CEILING_FAIL is not run and every step involving it is NOT_EVALUATED. With 4,096 excluded, neither CAPACITY_POSITIVE nor CAPACITY_PARTIAL can be assigned and Lane C's gate cannot pass. The lead has stopped before rehearsal and referred this to the human lead.
