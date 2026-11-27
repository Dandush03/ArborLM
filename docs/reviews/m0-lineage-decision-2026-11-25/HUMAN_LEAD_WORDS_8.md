# M0 lineage repair: the human lead's eighth decision (2026-11-26)

Recorded by the scientific lead (Claude Fable 5.2). The human lead's words are quoted exactly.

## What was put to the human lead

After the check of addendum draft 5 (`620ff787` on `claude/m0-spec`: approvable after required changes, 0 blocking, 8 required J1 to J8, 5 notes), the lead reported that the rule for which past cheap-rule runs count toward the bound of 0.15 was still not mechanical after three rounds (the checker needed judgement in nine places when applying it to M1), and that the cause is structural: every one of those runs has already been seen.

The lead recommended: stop pooling history; keep the survivor list exactly as it stands as a fixed, committed list; then run one fresh check, with a named and hashed list of rule scripts, fresh seeds written in the text and the pooling script written and hashed before the run; the run can only remove lineages and nothing dropped comes back; past runs become descriptive and decide nothing further. The cost was stated: lineages close to the bound may fall (R2's largest excess is 0.141, R1's is 0.126, and R1 has 8 clusters); the option is unfavourable to passing.

The question asked: "Do you want the fresh pre-registered run that can only remove lineages (my recommendation), or keep the pooling rule and have me tighten it again?"

## The human lead's words

> Yes, fresh run

## The lead's reading

- The membership rule for pooling past runs (draft 5, section 4A stage 0, points 1 to 10) is withdrawn. The candidate set is the survivor list of record: the fix-4 manifests less `cross_evaluation_map/drops_after_final_checks.txt`, with the capacity-held lineages as ruling R-39 leaves them. It is fixed by hash before the fresh run.
- One fresh run decides further drops under the bound: script list, seeds, pooling script, base rate, rule matching and rule classes all fixed and hashed before it runs. A lineage that exceeds the bound in it is dropped. No dropped lineage returns, whatever the fresh run shows for it.
- This supersedes the part of his item 18 (seventh decision) that had the list of past runs fixed by a written rule and audited against git history. The rule classes counted stay as item 18 decided: cheap rules and closed forms only.
- Taken with item-side measurements in view: "observed before: yes (item-side measurements only)". The option is unfavourable to passing.
- **These words do not approve addendum 1 and do not start the run.** The fresh run is specified in draft 6 and runs only after he approves the addendum. No model run, download or training is authorised.

Astra review: NOT_PERFORMED
