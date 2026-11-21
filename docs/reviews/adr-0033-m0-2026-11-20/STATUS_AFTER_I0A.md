# M0 after the locked-environment implementation (I0-a): engineering stop before any freeze (2026-11-20)

Recorded by the lead (Claude Fable 5.2). Nothing here is a result. No model, package or dataset was downloaded; no model ran.

**State.** I0-a is implemented on branch `claude/m0-impl` (implementer: arbor-implementer, Claude Sonnet 5.5 per the agent definition; commits 8230033, 8178aa0, 145e76b), self-checked (ruff, mypy on `src/arborlm`, 120 unit tests passed, 1 strict expected failure). It was audited by a fresh auditor context (arbor-auditor, Claude Opus 5.5): `AUDIT_I0A.md`. The branch is not merged.

**Two findings stop the freeze, both verified independently:**

1. **The power simulation of ADR-0033 section 9.4 fails its own known-truth gate.** Long run, tolerance 0.03: S2, S3 and S6 fail (recovered power 0.05 to 0.10 below the known power); S5 sits on the line. Cause: the truncated plug-in estimate of the between-lineage variance. With few lineages in few families the same procedure errs the other way, overstating power by 0.13 to 0.19.
2. **The design needs hundreds of lineages per part; 6 to 10 were written without padding, and the auditor counts 5 to 7 genuinely distinct procedures per part.** Some procedures appear in both parts, and one lineage (`R1.categories_follow`) is ambiguous in 236 of 500 items although both solvers agree.

**Also found (implementation):** two blocking defects (the required-size search uses the per-part test count instead of the whole conjunction; the simulation does not reproduce the M5 test below 30 clusters), seven required and five recommended edits; the second solvers were written by the implementer, which section 6.2 does not allow.

**What is needed, and whose it is.** The auditor recommends option (v): lineages as registered strata with items as the sampling unit, the between-lineage spread printed as a descriptive record. A PARITY on a private evaluation would then mean "on these registered task families", not "on reasoning of this kind". This amends a rule the lead approved under the weekend delegation (ADR-0032 section 5, the cluster sentence) and ADR-0033 section 6.2. **It is the human lead's decision.** Under his delegation of 2026-11-20 (`../adr-0032-model-level-2026-11-20/DELEGATION_NEXT_PHASE.md`) the lead takes it only if he has not returned and the P10-I work in progress is finished first; until then M0 stands at this stop.

`Astra review: NOT_PERFORMED`.
