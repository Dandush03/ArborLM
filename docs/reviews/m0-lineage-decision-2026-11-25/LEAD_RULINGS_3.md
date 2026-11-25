# M0 lineage repair: lead rulings after the third audits (2026-11-25)

By the scientific lead (Claude Fable 5.2). These are working rulings on how the approved text is read; none relaxes a registered rule, none registers a lineage, and each stays open to the human lead. The audits are in `audit3_r1/`, `audit3_r2/`, `audit3_m1/`, `audit3_c1/` (four `arbor-auditor` subagents, Claude Opus 5.5, one per evaluation). The auditors could not write into this worktree (a hook refused); the lead copied each auditor's report and scripts here unchanged from the auditor's scratch directory. The M1 auditor declined to write through the shell and prepared a delivery set instead; the lead copied it.

## What the audits found, in one table

| Evaluation | Clusters, auditor (map) | After the auditor's verdicts | Registrable as is | Need fixing | Should not be registered |
|---|---|---|---|---|---|
| R1 | 25 (27) | 23 | 11 lineages (13 more only if a shortcut bound admits them) | 14 | 5 |
| R2 | 37 (38) | 36-37 if every fix lands | 17 clusters | 20 lineages | 1 (pending) |
| M1 | 22 (22); 21 with one borderline merge | 22 | the remainder | 7 for wording or tells, plus every capacity-failing lineage | 1 |
| C1 | 28 (29) | about 24 | 21 lineages | 16, and 3 to be replaced | 4 |

Answer keys: zero mismatches against the auditors' independent solvers in all four sets (120,400; 574,000; 11,200 x 37 lineages checked at 400 per level; 126,000 items). The M0 suite reads 522 passed, 2 xfailed in each auditor's run. No count above is net of the cross-evaluation rule; 18 of R2's 37 clusters also appear in another evaluation.

## Rulings

- **R-10 (reserve levels).** Three auditors and the addendum reviewer independently read section 6.5 the same way: a reserve level can enter the chosen range, so its worst-case demand is the core demand, not 1,000. Adopted. This is stricter than R-5.
- **R-11 (demand formula).** The demand per cluster and level is 10 x (ceil(4,000/G) + ceil(20,000/G) + 100), the addendum reviewer's reading of the pools; it is at least the earlier 10 x (ceil(24,000/G) + 100). G is the smaller part's cluster count after exclusions.
- **R-12 (NOT REGISTERED means excluded).** A lineage marked NOT REGISTERED is removed from the cluster map's count, from G, from fixtures and from capacity runs. `min_cost_packs_r2` and `deferred_acceptance_partner` are not yet excluded everywhere; that is a defect to fix.
- **R-13 (R-1 applies to every lineage).** Redraw conditional on a heuristic is still present in five C1 and six R2 lineages the fix rounds did not touch. Each is rebuilt by construction or marked NOT REGISTERED. A rejected rule that scores exactly 0.00 is itself a tell.
- **R-14 (traced-state replacements).** Three of the four drafted C1 traced-state shapes are answerable by closed form (insertion sort, the Kadane running value, fast power after s rounds). They are not accepted as replacements.
- **R-15 (the cross-evaluation map is missing).** `manifests/cross_evaluation_procedures.json`, named in R-7, does not exist. It is built from the four auditors' duplicate lists before any further count is quoted.
- **R-16 (what "distinct item" means for capacity) — NOT RULED; put to the human lead.** Readings measured: names relabelled only (few failures); labels and letters also relabelled; literal values that do not change control flow or the solution path also discounted (C1: 90-101 of 140 cluster-levels fail). The lead's recommendation is the first reading with exact duplicates of the rendered question removed, because the gate's sentence counts "distinct items"; it is the most favourable of the three, which is why it is not adopted here.
- **R-17 (stop).** No further authoring or fix round starts until the human lead has seen the power result in ADR-0033 addendum 1 (all three private margins most likely NOT EVALUABLE (UNDERPOWERED) at 11-19 clusters) and said how to proceed.

## Slips recorded

- The lead's brief told the auditors to write into this worktree with a tool the hook refuses there; all four lost time to it.
- The R2 auditor read the author's fix summaries in `r2_rev2_build.py` and the manifest before measuring (not `NOTES_LINEAGE_REPAIR.md`).
- The lead's earlier statement to the human lead that only the 0.02 and 0.03 margins would be affected was wrong; the 0.05 margin is in the same position (addendum 1, section 6; reproduced by the reviewer).

Astra review: NOT_PERFORMED
