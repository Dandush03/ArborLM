# P10-I-S3 — Decision 2 (2026-11-18 UTC)

DECISION: RUN

Freeze commit: 2e985787c466c5ac66356635d4c68704d3730c55

Taken by the lead (Claude Fable 5.2) under the human lead's delegation of 2026-11-18 (`docs/reviews/p10-i-direction-2026-11-17/DELEGATION_2026-11-18.md` on branch `claude/p10-i-r`, sections 1 and 7: "accept the results as they come and continue with the next simulations until you conclude P10-I-*"; "you have my permission to auto approve everything until you complete P10-I"). It is a decision of the lead under that delegation, not the human lead's own approval of this run.

Stated before anything registered runs, and to be reported to the human lead first:

1. **Every arm was NOT CONVERGED in the calibration at 16,384 updates** (rehearsal R1, calibration seeds, all eight arm × regime pairs; public tags only, the sealed values were not opened). The registered run uses the same fixed duration, so its arms are expected to carry the NOT CONVERGED tag, and ADR-0026's rules cap what any label can then claim. The fixed duration was chosen at approval against the reviewer's advice to prefer a larger corpus; that choice is the lead's under the delegation and is the first weakness of this study.
2. The rate selected by code for M-TREE|FRESH at 16,384 updates (0.3) is at the edge of the extended grid (edge flag true). The other seven are interior.
3. Rehearsals: R1 3.08 h wall (11,101 s); R2 timing; the counting rehearsal was run three times. The first passed against plan `32c9fe4a…` but the freeze refused because the config still said `caps.provisional = true`; the config was changed (commit `9adafe6`: provisional false, no threshold touched), the plan superseded (old file kept in `studies/p10i_s3/freeze/superseded/`), and rehearsed again. The second was made in a folder without R1's and R2's records, so the freeze refused it. The third (`experiments/P10IS3-rehearsal-20261118`) holds byte-identical copies of R1's `rehearsal_public.json` (sha256 753a0c66…) and R2's `r2.json` (sha256 04dee109…) and the counting rehearsal against plan `2c02a026…`; the freeze accepted it. The two refused attempts are kept (`experiments/P10IS3-R3-20261118`, `P10IS3-R3b-20261118`).
4. Plan: 621 training items, 1,755 evaluation items, 6 workers. Projection 5.09 charged hours; registered cap 10.18 charged hours (2 × projection, computed by code from R2).
5. The machine is shared during this run with P10-I-S1's calibration (6 workers) and with subagents. This study registers no wall-time or throughput reading; charged hours may exceed the projection, and the cap binds as frozen.

This decision covers the registered stages gates, train, eval, analysis and report, run once, as frozen.

`Astra review: NOT_PERFORMED`. Claude review is not Astra review.
