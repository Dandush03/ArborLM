# M0 and what follows it: the human lead's answers to seven recommendations (2026-11-27)

Recorded by the scientific lead (Claude Fable 5.2). The human lead's words are quoted exactly.

## What was put to the human lead

After registration (65 lineages) and G-gen's record, he asked "any recommendations?". The lead gave seven, numbered:

1. Review the two irreversible things before anything builds on them: the split (the large group landed in the teaching part, so every held-out part is the small one) and the fifteen fresh-run drops (seven from the rule's wording).
2. Fix the margins before anything else in ADR-0033: they must be set before any model scores an item; at these cluster counts no registered margin is expected to be reachable for the private sets, so the choice mostly governs the public sets.
3. Decide how the models are run (ADR-0033 choice 8), which the lead cannot take: a separate hash-pinned package file (the reviewer's recommendation) or a plain-torch re-implementation verified once against the library (the drafter's). The lead leaned to the pinned file for M0.
4. Take the model list with the downloads in view; the standing delegation covers downloads under 50 GB once the list is chosen.
5. Do not try to rescue R1 inside M0: new R1 lineages need an amendment and a fresh pass through the pipeline; write that up as a follow-on proposal and do not hold M0 for it.
6. Start P11-S1's specification now: it was blocked only on M0's sets.
7. The two other held decisions still wait: the testbed choice for P10-I-S2-D1, where the lead recommended moving learned composition into P11-S1, and revision 7 of P10-II-S5.

## The human lead's words

> 1, the split
> 2 agreed
> 3 pinned package
> 4 agree
> 5 agree
> 6 yes
> 7 agree

## The lead's reading

1. He reviews the split first. The lead lays the partition of record out for him (which lineage is in which part). Nothing about the split is changed by these words; it was computed once and stands unless he says otherwise after reviewing it.
2. **ADR-0033 choice 3 is decided as option (a):** δ_e is fixed per evaluation before stage R1, that is before any model scores any item; R1 waits until he has fixed it. The values themselves are not given by these words; the lead puts them to him with the registered grid {0.02, 0.03, 0.05}.
3. **ADR-0033 choice 8 is decided as option (2):** the models are run from a separate hash-pinned package file; `uv.lock` and `pyproject.toml` do not change. This unblocks stage D0a (resolve and install the packages, with ledger rows) and stage I0-b (harness and loaders, tested on a tiny random model). It unblocks no model or dataset download.
4. The model list (choice 1) is still his and is not chosen by these words. The lead first re-reads at source the facts ADR-0033 section 4.2 marks unverified (the thinking switch, release dates, library support for sets A and B), then puts choice 1 to him. Under the standing delegation, the downloads of the chosen set need no further asking once each licence has been re-read at its source.
5. R1 is not repaired inside M0. A follow-on proposal for new R1 lineages is drafted as a proposal only; it needs its own approval before anything is written or run.
6. P11-S1's specification (ADR-0034, at draft 9) is revised against M0's registered sets. Drafting only; nothing is implemented or run under it without his approval.
7. The lead reads "agree" as agreement with the one recommendation that item contained: learned composition (P10-I-S2-D1, ADR-0036 draft, reviewed NOT APPROVABLE as designed) moves into P11-S1 and is not run on the earlier testbed. Revision 7 of P10-II-S5 carried no recommendation in that message and is not decided by these words; the lead puts it to him separately.

No model run, model or dataset download, or training is authorised by these words. Package installation for D0a is authorised by choice 8 within ADR-0033 section 5 and the standing download limit.

Astra review: NOT_PERFORMED
