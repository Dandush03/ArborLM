# P8 — human decision record (2026-11-14)

This file records one decision by the human lead. It does not change any raw record, class, threshold or the ADR-0015 outcome record.

## Question put to the human lead

> Accept the C06–C10 classes as registered despite the simulation stop-rule deviation?

Context given with the question: the ADR-0015 §16 freeze record says a failed cell stops the launch of further cells; the simulation pool did not enforce that and kept launching after the first failure (review README §7, defect 1). The C06–C10 classes rest on complete records but exist because of that deviation.

## Answer (verbatim, in chat, 2026-11-14)

> yeah

## What this covers, as interpreted by the Claude lead

- The classes for C06 (COLLAPSED), C07 (CONCENTRATION-ONLY), C08 (QUALITY-FAILED), C09 (NOT REPLICATED) and C10 (QUALITY-FAILED) stand as registered, with the deviation disclosed.

The answer was a single word; the scope above is the narrowest reading of it. If the human lead meant something else, this file should be corrected by a new dated entry, not edited silently.

## What this does not cover

- The study remains **INCOMPLETE** (55/60 simulated); C04 and C05 remain INCOMPLETE. No case is LOCALITY-POSITIVE.
- No decision on completing the five missing simulations.
- No decision on stopping or continuing this research line; no next phase is authorized.
- ADR-0012 remains not approved.
- PR #5 remains an unmerged draft.
- Astra review: NOT_PERFORMED.
