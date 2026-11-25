# P10-I-S2 Part Q — acceptance record (ADR-0025 section 19, ruling L1)

Written by the lead (Claude Fable 5.2) on 2026-11-21 local. `Astra review: NOT_PERFORMED`. Claude review is not Astra review. This record accepts a qualification of two teachers and of training material. It is not a transfer result and not a success claim.

## Why this file is written now

Ruling L1 requires Part Q's acceptance to be recorded in `ACCEPTANCE.md` beside the recomputation. Until today the acceptance existed only as the "Acceptance" section of `OUTCOME.md` (written 2026-11-20 UTC). Part T audit 13 found the separate file missing. This file states the same acceptance, with the same content and no new decision; `OUTCOME.md` is unchanged.

## What is accepted

- Registered label, as the frozen code wrote it: **TEACHERS-QUALIFIED (DISJOINT DRAWS)**. Accepted sources: teacher A 24,187, teacher B 24,796.
- Freeze commit `83595e07da303031a0d3ec840c2c40d6408da756`; Decision 2 at `results/p10is2-partq-freeze-20261119-attempt3/DECISION_2_PARTQ.md`.
- Stages 1 to 6 (inputs, partition, qfit, qcheck, generation, regeneration) were computed under freeze `55017df4616a81795918e21e0792fa742f77bdc4` in registered attempt 2 and reused in attempt 3, not recomputed (`docs/decisions/ADR-0025-addendum-part-q-attempt-3.md`).
- Outcome record: `results/p10is2-partq-run-20261119-attempt3/OUTCOME.md`, SHA-256 `75c1a188eae2dc325f1b7cdfe6b9de771ed23dabab61a1266019cec205c725e2`.
- Independent recomputation (arbor-auditor subagent, Claude Opus 5.5, own code): `results/p10is2-partq-run-20261119-attempt3/audit/RECOMPUTE_P10IS2_PARTQ.md`, SHA-256 `404c34e2b3f8eb6a7c7a396a8e643a092068d182f7795b80a5d09d5bf7aabe4d`. Verdict **REPRODUCED WITH CORRECTIONS**: 341 quantities compared, largest real difference 0.0; regeneration redone, 0 differing token sequences.

## Who accepts, and on what authority

The lead accepts the outcome as registered, unchanged, under the human lead's delegation of 2026-11-18, whose words were: "once its done can you accept the results as they come and continue with the next simulations until you conclude P10-I-* so we can discard what's not working and redesign our weakest point so we can achive the main idea?" (recorded in `docs/reviews/p10-i-direction-2026-11-17/DELEGATION_2026-11-18.md`). This is an acceptance by the lead under that delegation. It is not the human lead's own acceptance, and it stays on the human lead's review list.

## Corrections carried with the acceptance (the registered records are kept as written)

1. A term of Q2 cannot be recomputed: only the untrained student's two mean scores were stored, not the per-item scores (a departure from ADR-0025 section 4.3 rule 8). Q2 passes for any student mean up to 0.463.
2. Teacher B's Q4 Wilson lower bound is 0.8906, below 0.90. Q4 is registered as a point-precision gate (0.9404), so B passes as registered.
3. Pool margins: teacher A cleared 24,000 by 187; teacher B had 23,998 after 30 blocks and needed a 31st.
4. The attempt-3 counting rehearsals (2,022 s and 963 s by their ledgers) are outside the total by the ruling in Decision 2; counted, the total would be 14.31 h against the 13.83 h cap.

## Departure found after the outcome was written

Part Q stored gate G8's verdicts but not the reference logits (ADR-0022 section 14.2 step 3), found by Part T audit 10 and recorded in ruling 44. Consequence for Part T: its G8 is NOT RUN and is disclosed in its gates record, freeze record and Decision 2.

## What it licenses

The use of the two teachers and of the accepted pools as training material for Part T, as ADR-0025 defines. It licenses no statement about transfer, retention, a memory, or a student compared with a teacher. Every statement carries the oracle line: oracle-assisted (word-level addresses supplied by rule); lexical translation of short closed-vocabulary sentences, two capabilities of one kind; frozen English student; teacher-only training material verified by measured-precision filter; not autonomous learned memory.
