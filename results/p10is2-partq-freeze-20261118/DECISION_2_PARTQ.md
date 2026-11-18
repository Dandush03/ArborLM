# P10-I-S2 Part Q — Decision 2 (2026-11-18 UTC)

DECISION: RUN

Freeze commit: cb628159b5f1c895ef99c3ebf9501b797f14b35b

Taken by the lead (Claude Fable 5.2) under the human lead's delegation of 2026-11-18 (`docs/reviews/p10-i-direction-2026-11-17/DELEGATION_2026-11-18.md`, sections 1 and 7). It is a decision of the lead under that delegation, not the human lead's own approval of this run. It covers Part Q only (inputs, partition, qfit, qcheck, generation, regeneration, outputs, analysis), run once, as frozen. Part T is not decided here and starts only after Part Q is recomputed and accepted as TEACHERS-QUALIFIED.

Stated before anything registered runs:

1. Caps, by code from the measuring rehearsal `P10IS2-Q-rehearsal-measure3-20261118`: projected 37,120 s (10.3 h; generation 35,088 s); stage caps 2 x projected (generation 19.5 h); total 22.49 charged hours, which includes 6,698 s charged before the freeze. The rates were measured on a machine shared with other studies, so the caps are larger than quiet rates would give.
2. Not in the pre-freeze charge: the first measuring attempt (`P10IS2-Q-rehearsal-measure-20261118`), which failed in `outputs` with a code error and wrote no ledger (959.3 s by the auditor's reading), and its later resume to test the fix (about 252 s). The omission makes the total cap stricter. The counting rehearsals' charge (the stopped first one and the completed second, about 3,070 s) is outside the total by rule (the total is fixed before the counting rehearsal).
3. Rehearsal history, all kept: measuring attempt 1 failed (missing attribute handed to an imported P10-S2 function; fixed in 890125e); attempt 2 completed but timed no regeneration and cannot give caps; attempt 3 is the record frozen on. Counting attempt 1 was stopped by the lead after the auditor found that the inputs file stored 19 git-blob SHA-1 values as SHA-256 (fixed in 44eb797, plan superseded); counting attempt 2 completed against plan 1118c745.
4. Seal attestation (lead, implementer, auditor: no sealed value opened). Disclosed beside it: the implementer inferred, from the public record of measuring attempt 2 (no regeneration rate, 20,000 sources per capability) and the code path, that that rehearsal's draws ended DATA-EXHAUSTED, and made one existence check on the name `sealed/regeneration.json` without opening or listing anything. The lead has read that inference. It concerns rehearsal draws of a superseded record, not the registered draws. The teacher outputs and references of the rehearsals are public files; the seal on them is "not read before the registered analysis".
5. The 28 packages outside the lock were used by the rehearsals from the verified durable copy before the delegation record (section 7) was on THIS branch; it was then on `claude/p10-i-r` and on `main`, and was brought here unchanged before the freeze, which checks for it.
6. Analysis is projected at a fixed 60 s (the implementer's figure, accepted by the auditor; the analysis cap is not enforced inside that stage). The lead's ruling of this study recorded here: a missing shared ledger refuses the candidate plan in registered mode.
7. The machine is shared during this run (P10-I-S1's counting rehearsal now; other studies' quiet-machine stages may require the lead to let this run reach a block boundary and pause). This part registers no wall-time or throughput reading.

`Astra review: NOT_PERFORMED`. Claude review is not Astra review.
