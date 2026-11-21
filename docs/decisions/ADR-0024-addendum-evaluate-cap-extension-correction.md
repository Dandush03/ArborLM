# ADR-0024 addendum — evaluate-cap extension — CORRECTION of §3 (2026-11-21)

`Astra review: NOT_PERFORMED`

The committed addendum `ADR-0024-addendum-evaluate-cap-extension.md` (§3) and `results/p10is1-evaluate-cap-extension-20261121/OWED_DISCLOSURES.md` (item 3) say that evaluate's true charged time is "the sum of the stage manifests' `charged_seconds` (one per invocation)", "equivalently" the ledger's sum without the two extension entries. **The first half is false.** `execute_stage` overwrites `run_dir/<stage>/manifest.json` at every invocation, so a stage's manifest holds only its LAST invocation: the evaluate manifest holds the second run (125.67 s), not the first (3,600.03 s). Found by the independent recomputation (`results/p10is1-run-2026-11-21/recomputation/RECOMPUTATION.md` §6) and confirmed against the run directory.

The committed addendum is not edited in place; this file corrects it.

- **The true charged figure** of a stage is the ledger's entries for that stage WITHOUT the credit entry (the entry whose `run` begins `EXTENSION`): for evaluate 3,600.03 + 125.67 = **3,725.7 s (1.035 h)**; for baselines 0.0075 + 26.42 = 26.4 s.
- The ledger's `evaluate` SUM (125.7 s) and the evaluate stage manifest (125.7 s) both understate evaluate by 3,600 s. A reader who takes either would believe evaluate took 125.7 s.
- What stays true as the addendum said: the total charged seconds (15.676 h including the 7.966 h charged before the freeze; the credit and the offset cancel), every other stage's ledger sum, the 52 h total cap, and the effective evaluate-and-baselines cap of 2.0 h as the ledger arithmetic read it. The frozen report prints the plan's cap, 1.0 h.
- Evaluate's charged time, 1.035 h, exceeded the frozen 1.0 h and stayed within the approved 2.0 h on the `evaluate` key (evaluate plus baselines 1.042 h).
- The outcome record (`results/p10is1-run-2026-11-21/OUTCOME.md`) uses these figures. Changelog row 28 repeats the false statement ("the stage manifests do") and row 27 says baselines was "PAUSED with nothing charged" (the ledger holds 0.0075 s for that invocation); both rows are the lead's and are listed as owed corrections in the outcome record.
