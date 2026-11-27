# M0: the human lead approves ADR-0033 addendum 1 (draft 7 with one amendment), 2026-11-26

Recorded by the scientific lead (Claude Fable 5.2). The human lead's words are quoted exactly.

## What was put to the human lead

Addendum 1, draft 7 (`d70ba38d` on `claude/m0-spec`, SHA-256 of the text beginning `6430394b`), after six independent checks of earlier drafts; draft 7 itself not reviewed, and the second derivation of the closed list of uncounted rules not yet made. The lead stated what approval carries beyond his 22 itemised decisions (the lead rulings in the text; the places that lean toward passing; rows run on fewer items than stated), that the private margins will most likely still read NOT EVALUABLE, and that approval would authorise the fresh shortcut run and, after its results come back to him, registration, and no model run, download or training.

The lead recommended one amendment. As put to him: the strict rulings count a rule unless committed code labels it the lineage's own procedure, and the labels are incomplete (three M1 rules that look like the correct computation under a renamed variable or helper; any R1 rule right on every item that is not labelled; one C1 composite rule that counts whole and pulls in partial-trace rules his item 18 excludes). "My amendment: before the run, an independent auditor reads the code for these cases only. A rule is uncounted only if the auditor shows it is the same computation as the lineage's procedure. That list is hashed with the rest. This leans toward passing, which is why it is your call and not mine."

The question asked: "Do you approve draft 7 with the amendment (my recommendation), or approve it as written?"

## The human lead's words

> Approve with amendment

## The lead's reading

- ADR-0033 addendum 1 is approved as the text of draft 7 with the amendment written in. The approval covers his 22 itemised decisions and everything draft 7's top list states as carried by approval.
- The amendment, limited to the cases named: (M1) rules whose committed source differs from a labelled procedure rule; (R1) rules not labelled `M` or `EXCL`; (C1) the components of the composite `EFF_F`. For these only, an independent auditor reads committed code at `b78e58b1` before the run, without running any rule on any item and without any fresh figure. A rule is uncounted only where the auditor shows, in writing and per lineage, that it is the same computation as that lineage's solution procedure (for the C1 composite: the amendment can apply only if the components can be read apart from committed outputs; if they cannot, the composite counts as written). The auditor's list is hashed with the class table before the run. Anything the auditor cannot show counts. The amendment leans toward passing and is recorded as such: "observed before: yes (item-side measurements only)".
- Authorised: the steps of stage 1S (survivor list of record, derivations, class table, stage-2 judgements, run copies, pooling script, dry run, hashes, the fresh run), then the report of its results to him. G-gen's record and the split follow the order of section 4A after that report.
- Not authorised: any model run on M0 items, any download, any training, any change to a registered number.

Astra review: NOT_PERFORMED
