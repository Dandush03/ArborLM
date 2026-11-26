# ADR-0035 (P10-I-S2-D0) — approval record

Written by the lead (Claude Fable 5.2) on 2026-11-24 (Panama time). `Astra review: NOT_PERFORMED`. Claude review is not Astra review.

## Decision

**ADR-0035, draft 3, is APPROVED AS A SPECIFICATION, and its single run and its independent recomputation are approved within the 16 worker-hour bound of its section 10.** Approved by the lead under the human lead's delegation recorded in `HUMAN_LEAD_WORDS.md` (section 2). This is not the human lead's own approval. He said he will review it on the morning of 2026-11-25 and can overrule it; if he does, D0's records are kept and marked as run under an approval that was withdrawn.

## Basis

- Review 1 (arbor-auditor, Claude Opus 5.5): SOUND AFTER THE LISTED CHANGES, six required and nine advisory; all applied in draft 2.
- Review 2 (same role, own context): draft 2 applies all of them correctly; SOUND AFTER THE LISTED CHANGES, two required (R7, R8) and three advisory (A10 to A12); all applied in draft 3.
- The lead checked draft 3 against Review 2's change list (section 17 of the ADR) and found each applied. Draft 3 has not had a third independent review; that is a limit of this approval.
- Drafts 1 and 2 and both reviews are kept beside this record.

## One reading fixed here, before anything is computed

Section 4 says the route is "the registered one" and section 3 says every pass is under the oracle route. They are the same thing for D0: every pass uses the oracle route, as Part T's registered item scores for these panels did, and the reproduction gate of section 8 fails if that is not so.

## Limits

- No training. No change to Part T's code, records, labels or outcome. No new registered label. Nothing here authorises a bank-isolation experiment or any other training run.
- D0 is post-hoc and exploratory on a run whose outcome is known. Its readings are hypotheses.
- Implementation by arbor-implementer and the independent recomputation by arbor-auditor with its own code, in separate contexts; the model that actually ran each is recorded from session metadata.
