# P7-B results and review — co-access layout equivalence

- Label: `RESULT: FABLE-REVIEWED, OPUS-AUDITED — ASTRA NOT_PERFORMED — PENDING HUMAN REVIEW`. Run under a study-specific Claude workflow for P7-B only; ADR-0012 remains pending.
- Specification: [ADR-0014](../../decisions/ADR-0014-p7b-coaccess-layout-equivalence.md), revision 4, human-approved for execution 2026-11-13. Frozen at commit `03ea952`.
- The study ran exactly once, on two evaluation streams, in the registered order. Nothing was rerun, retuned or selected, and no change was made between the streams. P1–P7-A outcomes are unchanged.
- Reviewer: Claude Fable 5.2. Independent recomputation: Claude Opus 5.5, [`../p7b-results-audit-2026-11-13/RESULTS_AUDIT.md`](../p7b-results-audit-2026-11-13/RESULTS_AUDIT.md): 6,103 values compared with the implementation's analysis, zero differences. Who did what: [DELEGATION.md](DELEGATION.md).
- This is a simulation of value-page cache misses on traces. No storage device was used. Nothing here is a measurement of I/O, latency, throughput or hardware speed.

## 1. Registered outcome

| | Fixed tree | Learned tree |
|---|---|---|
| Stream A (existing evaluation stream) | **WITHIN 10% OF FLAT CO-ACCESS** | **WITHIN 10% OF FLAT CO-ACCESS** |
| Stream B (fresh, validation ranks 2560–3071) | **WITHIN 10% OF FLAT CO-ACCESS** | **WITHIN 10% OF FLAT CO-ACCESS** |
| Pairing | **REPLICATED** | **REPLICATED** |
| Decision class | **N** — no storage-locality case for the hierarchy | **N** |

**The hierarchy-specific locality hypothesis H-P7B failed**, as the lead predicted. In the registered wording: a flat memory whose slots are arranged by observed co-access gets locality within 10% of the existing hierarchy's.

**Registered recommendation (ADR-0014 §9, row 2): do not scale the existing hierarchy on storage-locality grounds.** The options are to redesign it or to stop the hierarchy line. That choice is the human lead's.

## 2. The main comparison

Branch-constrained co-access placement for the tree against unconstrained co-access clustering for flat, in incremental-locality terms (E: misses relative to the checkpoint's own count-preserving null). ρ is the tree-to-flat ratio; below 1 favours the tree. Ranges cover both eviction tie rules.

| Setting | Tree | ρ, stream A | ρ, stream B | Utilization-adjusted, A / B | Cells where the tree is lower | Class |
|---|---|---|---|---|---|---|
| Primary: 2 rows per page, 32-page cache | Fixed | 0.994–0.996 | 0.995–0.996 | 0.985–0.991 / 0.989–0.995 | 14–16 of 27 | WITHIN 10% |
| | Learned | 1.024–1.027 | 1.023–1.026 | 0.989–0.992 / 0.991–0.995 | 10–11 of 27 | WITHIN 10% |
| Confirmation: 8 rows per page, 8-page cache | Fixed | 1.083–1.102 | 1.085–1.104 | 0.962–0.990 / 0.966–0.993 | 5 of 27 | TIE-RULE DEPENDENT |
| | Learned | 1.199–1.214 | 1.201–1.217 | 0.995–1.010 / 0.996–1.012 | 0–2 of 27 | INTERMEDIATE |

Both settings use hypothetical row sizes. In the primary setting the ratio is within 3% of 1 with no consistent direction. In the confirmation setting the raw comparison consistently favours **flat** (fixed tree higher in 22 of 27 cells, learned in 25–27), by 8–10% and 20–22%; at common utilization the ratio is about 1.0. The outcome depends only on the primary class; the confirmation classes are reported beside it, as registered.

**The two streams agree almost exactly.** No ratio differs between streams by more than 0.0034, no quantity changes sign, and the direction of each tree-versus-flat pair is the same in 26 or 27 of 27 pairs. The streams come from the same corpus, so this is replication on unseen text from the same articles, not on an independent corpus.

## 3. Does flat gain as much from co-access clustering as trees gain from branch-aware placement?

Misses relative to plain frequency packing (lower is better; both streams within ±0.003):

| Layout | Flat | Fixed tree | Learned tree |
|---|---:|---:|---:|
| Co-access clustering, no hierarchy information — primary / confirmation | 0.755 / 0.587 | 0.752 / 0.607 | 0.782 / 0.660 |
| Branch-constrained co-access — primary / confirmation | — | 0.776 / 0.663 | 0.800 / 0.708 |
| Branch-aware frequency packing (the layout behind P7-A's 15%) — primary / confirmation | — | 0.849 / 0.671 | 0.867 / 0.717 |

**Flat gains more.** Co-access clustering cuts flat's misses by 25% and 41%. Branch-constrained co-access placement cuts the trees' by 20–22% and 29–34%. The 15% P7-A saw from branch-aware frequency packing was the benefit of using a layout with more structure than frequency packing, and flat gets a larger one from clustering its own slots.

**Keeping branches contiguous costs the tree a little.** Branch-constrained placement gives 2–3% more misses than unconstrained clustering of the same tree in the primary setting and 7–8% more in the confirmation setting.

## 4. Are branches better than arbitrary groups?

On exploited structure (each layout's misses relative to its own cost on a popularity-only null), real branches against the mean of the five registered random partitions:

| | Primary | Confirmation |
|---|---|---|
| Fixed tree | 0.768–0.770 | 0.465–0.488 |
| Learned tree | 0.780–0.786 | 0.505–0.524 |
| Worst single partition | 0.774 (fixed), 0.790 (learned) | 0.492, 0.528 |

PART_K is **REAL BRANCHES BETTER** in all eight combinations of tree kind, setting and stream, in 27 of 27 cells and 9 of 9 parents, under both tie rules. In the learned tree's primary setting the worst partition is 0.790 against the 0.80 margin, so that one is close.

How to read it: **branches are not arbitrary groups.** They hold rows that are used together far more than a random partition of the same shape does. But that does not make them better than what clustering finds unaided: in exploited-structure terms branch-constrained placement is about level with unconstrained clustering of the same tree, and on flat traces unconstrained clustering beats the same random partitions by about the same factors. PART_K was registered as a guard on a tree advantage; since no tree advantage appeared, it enters no outcome.

## 5. Controls and checks

- **Fresh panel.** Two independent reconstructions of validation ranks 2560–3071 agreed byte for byte, reproduced the recorded hashes of all five earlier panels, and showed zero overlap with earlier panels, the calibration stream and the training pool.
- **Layouts frozen before either stream.** Every layout was built from calibration traces only and hashed; the auditor's independent rebuild matched on all 81 checkpoints before the fresh stream was traced or anything was simulated.
- **Stream A reproduces P7-A** on all 33,210 shared configurations with no difference.
- **Independent re-simulation** of both criterion settings under both tie rules agreed on the 18 registered checkpoints per stream before analysis, and on three further checkpoints per stream afterwards.
- **Null-fit control (L-NCOAX): flagged.** A co-access layout fitted to a structureless calibration null should cost the same as frequency packing (registered band 0.97–1.03). It did for flat and in the primary setting; in the confirmation setting it cost 1.060 for fixed trees and 1.036 for learned trees. So the clustering does not manufacture locality; on chance affinities it packs popular rows slightly worse, which works against the trees there, not for them. Under the registered rule every co-access result is flagged accordingly. The implementation raised the flag in its records but did not carry it into the combined recommendation text; it is stated here.
- **Sensitivity.** The windowed affinity and the greedy-only layouts give the same primary classes. The robustness grid has no cell where either side is materially better. Every cell at ArborLM's actual row sizes (32, 128, 512 rows per page) is degenerate.
- **Quality.** Unchanged P5 losses: the trees are +0.0008 and +0.0014 nats/byte above flat, within 0.005 in 26 of 27 cells, as P5 found.
- **Layout noise.** Fitting the same layout on different halves of the calibration stream moves a checkpoint's misses by 1.4–4.8% on average and up to 16%.
- **Resources.** 3,330 s of 14,700 s; every stage under its cap; peak RSS 578 MB.

## 6. How this result should be weighed

- **It was anticipated.** The auditor's calibration-stream analogues, computed before approval and disclosed at the top of the ADR, predicted these ratios nearly to the second decimal (primary 0.999 and 1.032 against 0.994 and 1.027). The run on the existing stream was confirmation. The fresh stream is what nobody had looked at, and it agrees.
- **"Within 10%" is a size band, not equivalence.** In the primary setting the difference is under 3% with no consistent direction. In the confirmation setting the raw difference favours flat by more than 10% for the learned tree, which is why that class is INTERMEDIATE and not WITHIN 10%.
- **The optimizer is a heuristic.** One greedy pass and a bounded refinement. The review found a stronger optimizer would probably help flat more, so this result is unlikely to reverse in the trees' favour.
- **Hypothetical row sizes, one memory size (768 KiB), one corpus, 27 correlated cells in nine parents.**
- **All roles are Claude models.** The implementer's layout code resembles the auditor's earlier review script; the auditor's registered rebuild tool was written with a different structure for that reason.

## 7. What this means for the project

Together with P7-A:

- The trees read fewer simulated pages than flat because they use fewer rows (P7-A).
- Beyond that, a flat memory arranged by observed co-access matches the trees' locality, and gains more from clustering than the trees gain from their branches (P7-B).
- Branches do group co-used rows better than chance, but no better than a clustering that knows nothing about the hierarchy.

So the existing hierarchy offers nothing for storage locality that a post-hoc layout of a flat memory does not also provide. H4 has no support from the existing design at this size. H3 is untested: no locality objective has ever been trained. H5 is untouched.

## 8. Defects in the records

- The L-NCOAX flag is present in the per-stream records but missing from the combined recommendation text.
- A note in the robustness grid says sensitivity variants have descending-rule runs at the criterion settings; none were run.
- Quality is reported as per-architecture means only; paired differences in E against NLL were not computed by the implementation (the auditor's recomputation has them).
- No memory figure is recorded for the panel and analysis stages, and the cache-capacity hard check leaves no record of having run.
- The freeze and every intermediate commit were local until one push, as the human lead directed; ordering rests on local history and author timestamps.

None changes a registered result.

## 9. Questions for the human research lead

1. **Redesign or stop.** The registered recommendation is not to scale the existing hierarchy. The remaining options are:
   - **Stop the hierarchy line** for storage and efficiency, keeping "sparse learned memory adds capacity to a frozen backbone" (P4, P5) as the positive finding, and write up P1–P7 including the negative results.
   - **Test H3 directly:** train with a locality-aware objective, or with routing designed so that branches persist across consecutive queries, and judge it with the tools built here (count-preserving nulls, co-access-clustered flat baseline, arbitrary-partition control). This involves training.
2. **Governance.** ADR-0012 is still pending; P7-B ran under a study-specific direction.
3. **Merging.** PRs #3 (P7-A) and #4 (P7-B) are open drafts and unmerged.
