# ADR-0033 (M0): approval as a specification, and Decision 1 limited to locked-environment work (2026-11-20)

**Who:** the scientific lead (Claude Fable 5.2, main session), under the human lead's weekend delegation (`docs/reviews/adr-0032-model-level-2026-11-20/DELEGATION.md`). Not the human lead in person. `SPEC: PENDING ASTRA REVIEW`. `Astra review: NOT_PERFORMED`. Claude review is not Astra review.

**Approved:**

1. ADR-0033 revision 4 as the specification of M0.
2. Decision 1, limited to work that runs on the locked environment and touches no model: stage I0-a (item generators, second solvers, scorers, analysis and the power simulation with its known-truth test) and a rehearsal of stage G-gen at the proposed numbers. A rehearsal's output is not the record of record.

**Not approved, held for the human lead (ADR-0033 section 17):** the package route for running the models (three options; the reviewer recommends the pinned package file for M0, the drafter the plain-torch re-implementation); the model list; the domain list; the number of lineages G, the sealed pool size, the margins δ_e (before any model scores any item), the planning worst-case τ and which τ figure the floor uses; every config number before the freeze; the smaller design; the ruling on the unledgered WikiText-2 bytes; starting Colima; any model or dataset download; Decision 2.

**Basis:** three independent reviews by the auditor (Claude Opus 5.5), `REVIEW_1.md` to `REVIEW_3.md`; every finding applied (the ADR's tables record how). No choice was taken against the reviewer's advice.

**Disclosed:**

- The power simulation's wording was wrong in three successive versions, each written by the reviewer and each found by the reviewer's next check. The current wording recovered a known power within noise in six scenarios (`checks/shrink_check3c.py`). Because of this history the specification makes the known-truth test a freeze gate, requires its recomputation by an auditor context that did not write the wording, and forbids any use of a simulated size before both pass.
- Revision 4's last edits (P1 and the gate block, including the drafter's rule that the recovered power is a mean over enough draws for a Monte Carlo standard error of at most 0.01) were not reviewed again after being applied; the implementation audit is to check them.
- At the proposed numbers a 3-point margin is not reachable under the planning worst case (it needs about 20,400 to 23,100 sealed items per part against a pool of 20,000). The margin, the pool and G must be chosen together by the human lead.
- Coding is measured as code tracing only; code writing is NOT MEASURED.
- The literature note the specification leans on is unreviewed; its facts are re-read at source before they bind anything.

**Effect:** implementation of the locked-environment part may start. No frozen study, outcome or threshold is affected.
