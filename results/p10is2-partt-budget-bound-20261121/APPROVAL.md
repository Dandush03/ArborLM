# P10-I-S2 Part T: the human lead's decision on the study budget bound, 2026-11-21

`Astra review: NOT_PERFORMED`. This is a record of a human decision, written by the implementer from the coordinator's message; the implementer did not witness the chat. It is not Astra validation.

## The question as put

Part T's `candidate-plan` refused against the registered bound (ruling 33, ruling 41):

`REFUSED: refused: PENDING LEAD REVIEW: the total cap 150.17 h exceeds the study's budget bound 95.68 h (the counting allowance is 18.26 h): the human lead decides; nothing is extended here`

The human lead was shown these figures (all from the refusal and the plan's own cost model, at the calibrated U = 8,000, NOT CONVERGED AT U):

| Figure | Value |
|---|---|
| Total cap the plan would carry | 150.17 h |
| Registered bound `caps.study_budget_hours` | 95.68 h |
| Pre-freeze charge (measuring attempts 1 to 3 and calibration) | 9.633 h |
| Counting allowance (ruling 20) | 18.26 h |
| Registered stage caps, sum | 122.31 h |
| Unpadded projection of Part T (charge + half the allowance + half the stage caps), analytical | about 80 h |

and was asked: **"do you raise Part T's budget bound from 95.68 h to 151 h so the plan can be written?"**

## The answer, verbatim

Given in chat on 2026-11-21 (evening, local):

> **Raise to 151 h**

## What it covers

- `caps.study_budget_hours` for Part T becomes **151 h** (from 95.68 h). That is the whole approval.
- It lets `candidate-plan` write the plan, whose total cap is 150.17 h.

## What it does not cover

No rule, threshold, grid, seed, cell count, U, padding factor or stage-cap rule changes. Calibration is not repeated. The padding of ruling 30 (stage caps at 2 x the projection), the counting allowance of ruling 20, the ruling-33 bound check itself (a total above the bound still refuses) and every label rule are unchanged. It is not an approval of any result, of the counting rehearsal, of the freeze or of any registered stage.

## How it is carried

See `docs/decisions/ADR-0025-addendum-part-t-budget-bound.md` (ruling 46): the config key holds 151 h; the plan names this file by path and SHA-256 together with both numbers (95.68 registered, 151 approved).
