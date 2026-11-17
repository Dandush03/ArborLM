# P10-S1 — Decision 2 for the second attempt (ADR-0021 §22 M4, §25.19, §25.20)

Freeze commit: `76334ba6697b40f50aad8abb196628f4fd4cb739`

DECISION: RUN

Decided by the scientific lead (Claude Fable 5.2) on 2026-11-17 UTC. The second attempt itself is the human lead's decision, given on 2026-11-17 after the lead reported that attempt 1 had ended S1-INCOMPLETE through the lead's own error: "Yes, second attempt". The first Decision 2 (`results/p10s1-freeze-2026-11-16/DECISION_2.md`) stays as written and names the first freeze commit only.

- **What is run.** The plan of the first freeze, unchanged: 178 cells, the same draws, seeds, calibrated values, stage caps, thresholds and analysis rules, in a new run directory.
- **What changed.** The ceiling of charged time, C_max 50 → 54 hours, and the computed cap, 49 → 53 hours, because attempt 1's time stays on the ledger. Reported to the human lead before the freeze.
- **Check.** An independent read-only check (Opus 5.5) confirmed the diff, the ledger arithmetic and the projection, and returned READY WITH NOTES; the notes are answered in ADR-0021 §25.20.
- **Observation.** No evaluation has run on a registered draw. Attempt 1 trained seven cells; their records have not been opened and are not used.
- **Condition.** From the commit of this file until the report stage has finished, nothing is committed or written in this working tree.

Whatever this attempt gives is recorded, including null and negative results and any stage stopped by its cap. Nothing in its result is autonomous learned memory: addressing is supplied by an oracle. Astra review: NOT_PERFORMED.
