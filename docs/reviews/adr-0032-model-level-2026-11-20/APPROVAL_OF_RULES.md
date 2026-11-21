# ADR-0032: approval of five rules by the lead under the weekend delegation (2026-11-20)

**Who:** the scientific lead (Claude Fable 5.2, main session), under the human lead's delegation recorded in `DELEGATION.md` ("well actually you can aprove it yourself this weekend / I'll review all the work on monday"). Not the human lead in person. `Astra review: NOT_PERFORMED`. Claude review is not Astra review.

**What is approved (ADR-0032 revision 4, section E2), and nothing else:**

1. The two levels of evidence (Part B, section 1): component evidence and model-level evidence are never mixed; a component result is never reported as progress toward parity.
2. The margin rule (section 4): a substantive margin per evaluation set before any score of the system, noise used only for sample size, the cap as a flag. Not the values, the fraction or the timing.
3. The power rule (section 5): paired comparison, the conjunction and what it contains, power by simulation, sample size fixed for a registered power, the sealed pool, NOT EVALUABLE (UNDERPOWERED). Not alpha or the power value.
4. The label structure of sections 5 and 6 (parity, conventional adaptation, no harm, retention).
5. The order of the M ladder, M0 to M6. Each rung still needs its own specification and approval.

**Not approved:** every number; the reference, domain and model lists; any download; any run decision; the final-acceptance definition; section 7's labels; the whole self-learning part (Part S); the scorecard scores. Three points were decided by the human lead himself (`HUMAN_LEAD_DECISIONS_2026-11-20.md`).

**Basis:** three independent reviews by the auditor (Claude Opus 5.5): `REVIEW_1.md` (READY AFTER THE LISTED EDITS, 19 findings), `REVIEW_2.md` (18 findings), `REVIEW_3.md` (rules 1, 2 and 5 fit to approve; rule 3 after H2; rule 4 after H3; 8 findings). All 45 findings were applied; the ADR's three tables record how. No choice was taken against the reviewer's advice. Disclosed: revision 4's edits H1 to H8 use the reviewer's own wording and were not reviewed again after being applied; both literature notes are unreviewed and their numbers must be re-read at the source before entering a specification.

**Effect:** these rules bind the specification of M0 that the lead will now draft. They authorise no implementation, download, training or run. The human lead may overrule any of them at his review on Monday 2026-11-23; no frozen study, outcome or threshold is affected either way.
