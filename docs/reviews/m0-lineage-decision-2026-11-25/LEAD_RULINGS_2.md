# M0 lineage repair: lead rulings after the four independent audits (2026-11-25)

By the lead (arbor-lead, Claude Fable 5.2). Lead rulings, not human approval. `Astra review: NOT_PERFORMED`.
Audits (arbor-auditor, Claude Opus 5.5): `audit2_r1/AUDIT_M0_R1_2.md`, `audit_r2/AUDIT_M0_R2_1.md`, `audit_m1/AUDIT_M0_M1_1.md`, `audit_c1/AUDIT_M0_C1_1.md`. No model has been loaded or scored; everything here concerns item generators.

## What the audits found (auditors' strict counts; authors' counts in brackets)

| Evaluation | Lineages written | Strict clusters | Strictest / lenient |
|---|---|---|---|
| R1 | 43 registered shapes | 27 (author 31) | 14 / 42 |
| R2 | 42 | 38 (author about 38-40), 36 with two merges implied by the author's own log | - / 41 |
| M1 | 37 | 22 (author 22-28) | - / 36 |
| C1 | 39 | 28 (author 34), 22 with the author's borderline groups | 22 / 39; 1 if "procedure" is the act of tracing |

No wrong answer key was found in any evaluation by the auditors' own solvers. Found instead: over-counted clusters, ambiguous wordings that change keys, cheap shortcuts the authors' screens missed, three bugs in the R1 shortcut gate, repairs that created new tells, clusters spanning parts A and B, the same algorithm in more than one evaluation, capacity that depends on names or presentation order, and new lineages not wired into the registry that builds pools.

## Rulings

R-1. WITHDRAWN: the lead's earlier ruling that a shortcut may be repaired by redrawing items conditional on a heuristic's outcome. Three audits show it moves the tell to a correlated heuristic, is miscalibrated by level, and can change what the item measures. From now: a tell is removed BY CONSTRUCTION (the generator's structure makes the heuristic uninformative at every level), or the lineage is marked NOT REGISTERED with the reason. No probability fitted to a heuristic's outcome. Shapes already repaired by redraw are superseded, kept on file.

R-2. Cluster map: the auditors' strict maps are adopted as the working maps (over-counting is the harmful error). Where an author disagrees with a merge, the disagreement is written beside the map with reasons; it does not un-merge. Borderline groups ("strictest") are listed, not merged, and go to the human lead as the range.

R-3. Shortcut measurement: per level, two-sided, with the auditors' heuristics added to each author's battery, and with the three R1 gate bugs fixed (possessive forms, direction of a stated pair, signed numbers). Still measured, not thresholded: the bound is a new registered number for the human lead.

R-4. Wording: every convention an answer depends on is stated in the item. Items whose key changes under an ordinary alternative reading are defects (R1 categories_follow_r2 "no", boolean_lights "every other"; R2 expression_eval both shapes, merge_smallest_cost; M1 slot_permutations leading zero, last_digit_power gloss, digit_puzzle reversal).

R-5. Capacity is counted on structure: a change of names, setting sentence or presentation order alone is not a distinct item (least favourable reading of section 6.2's capacity sentence, which does not define "distinct items"). The demand is computed at the G actually written, not at 300. Lineage-levels that fail are widened or the lineage is NOT REGISTERED at that level set; the human lead is told which.

R-6. Parts: no strict cluster may have members in both parts of an evaluation. The partition is recomputed on the final working map. The reading "families joined by a cluster form one key of the registered rule" stays provisional; its imbalance is reported; the alternative readings and their splits go to the human lead.

R-7. Cross-evaluation duplicates (the same algorithm in two evaluations) are recorded in one map, `studies/m0/manifests/cross_evaluation_procedures.json`. Section 6.2 does not address them. Nothing is merged or dropped on this account by the lead; whether a held-out part may contain a procedure taught in another evaluation's teaching part is a question for the human lead.

R-8. C1: the working reading is that the procedure is the program's algorithm (the reading under which the existing 14 were written). The auditor's observation that under "the act of tracing" C1 has one cluster, and that several lineages are answerable by formula without tracing, goes to the human lead.

R-9. Registration: no new lineage enters `core.REGISTRY` until its cluster map, wording, construction-level shortcut fixes and capacity have passed a second audit, and its second solver exists from a separate context. Authoring of further lineages stops until then.

## For the human lead (not decided here)

1. The granularity of "a distinct solution procedure" (strict / strictest / lenient ranges above), per evaluation.
2. What a C1 item's procedure is.
3. Cross-evaluation duplicates and the held-out claim.
4. The partition reading.
5. The shortcut bound (a new registered number).
6. The minimum number of lineages registered before G-gen's record, given roughly 11 to 19 strict clusters per part.
