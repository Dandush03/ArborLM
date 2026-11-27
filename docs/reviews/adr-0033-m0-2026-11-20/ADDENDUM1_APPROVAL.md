# ADR-0033 addendum 1 (M0, lineage clusters): approval by the human lead, 2026-11-26

**Status: APPROVED by the human lead on 2026-11-26 as draft 7 with one amendment.** `SPEC: PENDING ASTRA REVIEW`. `Astra review: NOT_PERFORMED`. Claude review is not Astra review. ArborLM is unproven research; this record claims no result.

**Who approved:** the human research lead, in person. Not the scientific lead and not under a delegation. This record was written by the drafter of the approved text (`arbor-lead`, Claude Fable 5.2, `claude-fable-5-2`, as the session states it) on the coordinating lead's brief. `APPROVAL.md` in this folder is the earlier record for ADR-0033 itself and is not changed.

## His words

The question put to him: "Do you approve draft 7 with the amendment (my recommendation), or approve it as written?"

> Approve with amendment

Record of the words: `docs/reviews/m0-lineage-decision-2026-11-25/HUMAN_LEAD_WORDS_9.md` on branch `claude/m0-impl`, commit `f627389a` (SHA-256 of that file `fcc382813d61bf3434f3476866e5fc711a2ccf3275cbcfc0170b8975d43e8105`). Row 50 of `docs/PARAMETER_CHANGELOG.md` on `origin/main` records the approval.

## The texts

| Text | Commit | SHA-256 of `docs/decisions/ADR-0033-addendum-1-lineage-clusters.md` |
|---|---|---|
| Draft 7, as put to him | `d70ba38d` on `claude/m0-spec` | `6430394bc9c85d85ee298e3ad6fb30bea2cf88a99dc9c9d9c864df93df27e032` |
| The approved text: draft 7 with the status changed and the amendment written in | this commit | `154d16a0597dc8b2d41179ded63a5da3e6e92aa4f7b414fefda1f93cd4d0923c` |

From this commit on the approved text is immutable, like every approved ADR.

## The amendment, as `HUMAN_LEAD_WORDS_9.md` reads it

Limited to the cases named: (M1) rules whose committed source differs from a labelled procedure rule; (R1) rules not labelled `M` or `EXCL`; (C1) the components of the composite `EFF_F`. For these only, an independent auditor reads committed code at `b78e58b1` before the run, without running any rule on any item and without any fresh figure. A rule is uncounted only where the auditor shows, in writing and per lineage, that it is the same computation as that lineage's solution procedure. For the C1 composite the amendment can apply only if the components can be read apart from committed outputs; if they cannot, the composite counts as written. The auditor's list is hashed with the class table before the run. Anything the auditor cannot show counts.

The amendment leans toward passing and is recorded as such: "observed before: yes (item-side measurements only)". It is section 13 item 23 of the approved text and is written into section 4A stage 1S point 8. Draft 7 found that the components of `EFF_F` cannot be read apart from committed outputs, and the run copy rules allow no change of an output line, so in the approved text `EFF_F` counts whole.

## The six independent checks

Each was by an `arbor-auditor` context (Claude Opus 5.5, as the reports state). Each was of an earlier draft.

| Check | Of | Folder (under `docs/reviews/adr-0033-m0-2026-11-20/`) | Report | Verdict |
|---|---|---|---|---|
| 1 | draft 1 | `addendum1_review1/` | `REVIEW_ADDENDUM1_1.md` | approvable after required changes: 2 blocking, 10 required, 8 notes |
| 2 | draft 2 | `addendum1_review2/` | `REVIEW_ADDENDUM1_2.md` | approvable after required changes: 1 blocking, 13 required, 10 notes |
| 3 | draft 3, limited scope | `addendum1_review3/` | `REVIEW.md` | approvable after required changes: 0 blocking, 7 required, 5 notes |
| 4 | draft 4, narrow scope | `addendum1_review4/` | `REVIEW.md` | approvable after required changes: 0 blocking, 4 required, 6 notes |
| 5 | draft 5, narrow scope | `addendum1_review5/` | `REVIEW.md` | approvable after required changes: 0 blocking, 8 required, 5 notes |
| 6 | draft 6, narrow scope (the fresh run of section 4A stage 1S) | `addendum1_review6/` | `REVIEW.md` | approvable after required changes: 0 blocking, 12 required, 8 notes |

**Not independently reviewed:** draft 7, which applied check 6; and the wording by which the amendment is written into the approved text, with the drafter's readings listed in its section 12 item 30. The second derivation of the closed list of uncounted rules had not been made when he approved. No check found a draft approvable without required changes.

## What is authorised, and what is not

From `HUMAN_LEAD_WORDS_9.md`, the lead's reading of his words:

- **Authorised:** the steps of stage 1S (survivor list of record, derivations, class table, stage-2 judgements, run copies, pooling script, dry run, hashes, the fresh run), then the report of its results to him. G-gen's record and the split follow the order of section 4A after that report.
- **Not authorised:** any model run on M0 items, any download, any training, any change to a registered number.

The approval covers his 22 itemised decisions and everything draft 7's top list states as carried by approval. Nothing is registered by it: no G-gen record exists, and no split with the registered seed has been computed. No model has been loaded, run or scored on any M0 item.

Astra review: NOT_PERFORMED
