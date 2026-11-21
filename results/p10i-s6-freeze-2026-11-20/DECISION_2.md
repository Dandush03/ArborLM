# P10-I-S6 — Decision 2 (registered run)

DECISION: RUN

Freeze commit: cedfbe2842e8eb8bcc99c4303f5191fe0b3861e1

Date: 2026-11-20 (about 06:00 Panama time).

## Who decided

The scientific lead (Claude, Fable 5.2), under the human lead's delegation of 2026-11-19 recorded in
`docs/reviews/p10-i-s6-spec-reviews-2026-11-19/DELEGATION_DECISION_2.md` (asked "May I take S6's run decision
myself so its registered run starts overnight, or should it wait for you?", he answered "Yes, start it").
ADR-0031 records Decision 2 as the human lead's own; this record is taken under that delegation and not by him
in person. He has not seen the figures below at the time of this decision.

## The delegation's conditions, each checked

| Condition | Reading | Met |
|---|---|---|
| Rehearsals pass | R1 COMPLETE (3 rounds, 29,349 charged s); R2 COMPLETE; R3 COMPLETE (gates, train, eval, analysis, report all exit 0) | yes |
| Calibration does not end at the edge of its grid | interior true at every rung -1..4 for M-FLAT and D-ADAPT | yes |
| Gates | identity true (both arms); negative reference true (c0, c1, c2); planted positive true | yes |
| Cost projection at most 40 h | projected 11.17 h; registered cap 22.34 h (charged + 2 x projected, from R2's record) | yes |
| Freeze succeeds | freeze record committed at the commit above; plan sha256 21742752dcf7b3145c7ed152dbe0c3c0cb179e0d580e975d50686a3a47b0aa03; caps not provisional | yes |
| Counting rehearsal complete against that plan | R3 names the same plan sha256 | yes |

Rate table (sha256 6a0b548d78d063b125abcec4c9e3588c34fb155dfdf6549ee92032f0b361de78): M-FLAT 0.01, 0.03, 0.1,
0.03, 0.1, 0.003 and D-ADAPT 0.01 at every rung, rungs -1..4. Plan: 189 training items, 837 evaluations, 6 workers.

## Conditions of the run

- No threshold, label rule, seed, cell or cap is changed by this decision. Thresholds stand as approved in
  ADR-0031 (0.005; 22 of 27; 8 of 9; epsilon 0.001).
- If a stage reaches its cap, an extension is decided on the cost ledger alone, before any registered value is
  read, and is recorded in `docs/PARAMETER_CHANGELOG.md`.
- An identity failure or a code or environment error is an engineering stop, not a scientific outcome.
- The lead's implementation rulings 1-22 (ADR-0031 addenda 1 and 2) are pending the human lead's confirmation;
  he may overrule any of them before the outcome is accepted.
- Disclosures: R1 was paused and restarted several times for another study's quiet stages and once died with
  the terminal that had started it (2026-11-19 about 22:33; restarted 00:36); in-flight items restarted from
  update 0 and their partial directories are kept. R2's unit costs were measured while P10-I-S0's registered
  workers were running on the same machine, and the registered run starts under the same condition.
- The outcome is whatever the registered labels say. Nothing here is a claim of success.

Astra review: NOT_PERFORMED
