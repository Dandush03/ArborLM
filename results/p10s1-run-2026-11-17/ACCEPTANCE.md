# P10-S1: acceptance by the human lead (2026-11-17)

The human lead read the registered outcome (`OUTCOME.md` section 2) and the independent recomputation (`audit/AUDIT.md`) and wrote, on 2026-11-17:

> accept P10-S1 as recorded, preserve its original labels, and explicitly disclose the audit findings.

and, in the ruling supplied with that message:

> I accept the P10-S1 result as recorded, unchanged, with every audit finding preserved alongside it.

This acceptance is of a registered result in which no line is positive for the store. It is not a success claim, and it authorizes no P10-I experiment ("No P10-I experiment is authorized by this acceptance."). `Astra review: NOT_PERFORMED`. Claude review is not Astra review.

## The registered labels, unchanged

| Line | Outcome |
|---|---|
| Capacity | CAPACITY-INCONCLUSIVE: F-OQ DEPENDENCE_FAILED; F-OQ-IVF DEPENDENCE_FAILED; T-OQ INTERMEDIATE; 16,384→65,536 NOT TESTED |
| Saturation | SATURATION-INCONCLUSIVE: F-OQ INTERMEDIATE; T-OQ SATURATION_NOT_MEASURED |
| Efficiency | EFFICIENCY-NEGATIVE (DENSE FASTER), sizes 1,024–16,384 |
| Milestone question 1 | Not established |

Every positive sub-label carries `STORE ONLY; ORACLE-ADDRESSED`.

## Rulings

1. **Dependence failures at early snapshots.** CAPACITY-INCONCLUSIVE is retained. Disclosure: all DEPENDENCE_FAILED verdicts come from the condition a_use ≥ 0.95 × raw accuracy at 2,048 updates (ratios 0.9425–0.9471), a condition the reference arm R2 also fails 12 times at 512–1,024 updates; read only at the snapshots the verdicts use, the capacity outcome would be CAPACITY-NEGATIVE (b). The alternative reading is disclosed, not adopted. The registered label is the one more favourable to the store.
2. **DENSE FASTER across cells.** The frozen code's EFFICIENCY-NEGATIVE is retained ("Do not reinterpret the registered result as EFFICIENCY-POSITIVE after seeing the data."). Disclosure: DENSE FASTER holds in 5 of 5 replicates at 2K/4K and 0 of 5 at 8K/16K. At 8K/16K the two registered cost measures disagree: D-OQ's cost to reach the level is 0.27–0.38 of T-OQ's in measured CPU seconds and 1.32–1.87 of it in analytic multiply-adds. The any-cell rule the code applied was not registered (ADR-0021 section 8.8 does not say how cells combine). This is an interpretive limitation: the label is not evidence that dense is cheaper under both cost measures at every size.
3. **Seed-block section.** The original `RESULTS.md` is kept as the frozen code wrote it. The auditor's corrected 28 comparisons are published in `ERRATUM_SEED_BLOCK.md`.
4. **Supplementary throughput.** Accepted as descriptive engineering evidence only. It does not repair the failed registered throughput stage and changes no registered result.

## Carried into P10-I-S1 (proposed ADR-0024)

- The early-snapshot dependence condition (a better-founded dependence test across training stages).
- An explicit, registered rule for combining cells in the dense-speed comparison; each cell reported; analytic compute and measured training cost kept apart.
- The matched-compute observation at 32K/16K (F-OQ ahead of D-OQ by 0.24–0.33 bits in 5 of 5 replicates) against DENSE AHEAD at matched updates and at D-OQ's best snapshot.
- The seed-block reporting defect (`analysis.py`, lines 167–169).
- Also noted by the human lead for P10-I: the untested 16,384→65,536 transition; the quality gap between flat and hierarchical memory; DICT DOMINATES ON THIS TASK (a later study must show value a plain lookup cannot provide).

## What follows

The human lead directed: once the repository checks pass, proceed with the agreed P10-S1 integration sequence, then prepare the P10-I specifications for review. "All original results, audits, thresholds and provenance remain unchanged."
