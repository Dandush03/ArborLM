# Disclosures owed in the outcome record of P10-I-S1 (evaluate-cap extension)

`Astra review: NOT_PERFORMED`

Copy into the outcome / acceptance record when it is written (the frozen report cannot carry them):

1. The human lead approved a 1-hour extension of the evaluate cap on 2026-11-21 ("Approve 1 h", `APPROVAL.md`). It was applied as a ledger credit of −3,600 s on `evaluate` with an equal +3,600 s on the stage `evaluate-cap-extension-offset` (both entries' `run` begins `EXTENSION`). The plan's frozen `stage_caps.evaluate_hours` is unchanged (1.0).
2. The frozen report prints an evaluate cap of 1.0 h; the effective evaluate-and-baselines cap was 2.0 h.
3. The ledger's `evaluate` sum is 3,600 s below evaluate's true charged wall time and `evaluate-cap-extension-offset` shows +3,600 s that was never run. Evaluate's true charged time is the sum of the stage manifests' `charged_seconds` (equivalently the ledger sum excluding the two `EXTENSION` entries). The total charged seconds, every other stage's sum and the 52 h total cap are as the ledger says.
4. The registered analysis and report stages could not run (ENGINEERING STOP — ANALYSIS LOADER DEFECT); see `docs/decisions/ADR-0024-addendum-analysis-loader-defect.md` and `results/p10is1-analysis-supplement-20261121/`.
