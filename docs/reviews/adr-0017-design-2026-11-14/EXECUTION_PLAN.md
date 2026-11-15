# ADR-0017 — exact execution plan (design revision 3)

Nothing below is authorized until the step's approval is recorded. Each step names who does it and what stops it.

## Phase 0 — design (now)

| Step | Who | Output | Stops if |
|---|---|---|---|
| 0.1 Evidence inventory | Haiku | `EVIDENCE_INVENTORY.md` | — |
| 0.2 Indicative timing | lead | `benchmark/` | — |
| 0.3 Design revision 1, plan, budget | Fable | ADR-0017, this file, `RESOURCE_BUDGET.md` | — |
| 0.4 Independent scientific review | Opus | `REVIEW.md` | verdict NOT READY → revise |
| 0.5 Revisions answering the review and re-check | Fable | ADR-0017 revisions 2 and 3 | — |
| 0.6 Auditor re-check of revision 2 | Opus | `RECHECK.md` | NOT READY → revise |
| 0.6b Confirmation check of revision 3 | Opus | `CONFIRM.md` | fixes F1–F15 applied verbatim, else revise |
| **0.7 Human decision 1: approve the specification for implementation, calibration and rehearsal; the departures of ADR §0; the calibration/rehearsal cap; the delegation** | human | approval record in ADR §15 | not given → stop here |

## Phase 1 — implementation (after decision 1)

New files only. Three implementers never edit the same file.

| Package | Who | Files (new) | Depends on |
|---|---|---|---|
| I1 task generator, streams, panels, leakage checks, exact retrieval, no-memory baseline, frozen-hidden probes (nearest stored answer-site state; 32-way linear probe per identifier position), attainable answer probability | Sonnet | `src/arborlm/p9_data.py`, `p9_controls.py`, tests | — |
| I2 scalable memory (sizes, key widths, constant-candidate tree, ladder rungs), training loop, snapshots, instrumentation, objectives (global usage floor with the b-free gradient of ADR §7; λ_c on R_co − 1/8), row-lazy Adam on key and value tables only at learning rate 0.012 (A10) | Sonnet | `p9_model.py`, `p9_train.py`, `p9_objective.py`, tests | I1 interfaces |
| I3 evaluation: I_acc with the chance floor, seven-position knock-outs, minimal supports, specificity, value-only group ablations, hard and soft usage, per-row movement split, LEAKAGE check | Sonnet | `p9_eval.py`, tests | I1, I2 interfaces |
| I4 locality: general-N page simulator with exact equivalence to P7-B at 4,096 on P7-B's recorded traces, sparse co-access layouts; identity, frequency-packing, random-partition and (tree) branch-constrained control layouts; pages per query and cross-query reuse; planted-trace generator, cache rule, identity null | Sonnet | `p9_sim.py`, `p9_layout.py`, tests | — |
| I5 Lane D: sequential phases from V1 parameters with a fresh optimizer state for every phase-B arm (V1 optimizer state stored for the restoration test only), replay, version store | Sonnet | `p9_incremental.py`, `p9_store.py`, tests | I2 |
| I6 job manager (dependent-cell stop rule in every stage, tested), manifests, limits; one analysis module per lane; report | Sonnet | `p9_pool.py`, `p9_analysis_a.py` … `_d.py`, report generator | all |

I1, I2 and I4 start together; I3 and I5 follow I2's interface; I6 last. Interfaces are fixed by the lead in a short contract file before I1–I4 start.

Required tests: P5 invariance at 4,096/16; gradient reach per parameter group; ladder rungs; top-k tie handling at every size; generator checks; identity null; every class rule triggered on synthetic inputs (collapsed, degenerate, entropy inflation, undertrained, incomplete, ceiling failure, near-chance step, COLLAPSED before DEGENERATE, SOFT-USAGE ONLY, LEAKAGE, OPTIMIZER-ARM UNINFORMATIVE, seed disagreement → INTERMEDIATE); margin-saturation detector on a constructed state; version-store consistency; checkpoint restoration.

## Phase 2 — rehearsal and audit

| Step | Who | Rule |
|---|---|---|
| 2.0 Testbed calibration on rehearsal seeds (ADR §12 step 4): frozen-hidden probes, R2 curves to E = 128, controls, attainable answer probability | Sonnet runs, Opus audits | written in full; selects E by the registered rule and may mark a size TASK_CEILING_FAIL; nothing else changes (ADR §8 opening); no compared arm is run |
| 2.1 Full-size rehearsal on rehearsal seeds, isolated machine | Sonnet runs, lead reads | records written only through a validator whose allowed keys are the whitelist (time, RSS, finiteness, shapes); stdout and stderr to a file the auditor checks for loss or accuracy values; no progress display shows loss |
| 2.2 Stage caps = 2 × measured; any registered reduction chosen now, with its rule change (RESOURCE_BUDGET.md) | lead | recorded revision, approved at decision 2 |
| 2.3 Implementation audit: generator, leakage, gradients, optimizer state, null, simulator, classes, budget controls | Opus | READY TO FREEZE or findings |
| 2.4 Data and panel generation for registered seeds; hashes recorded | Sonnet | no model touches them before the freeze |
| 2.5 Freeze commit: specification, code, configs, data hashes, panel identities | lead | — |
| **2.6 Human decision 2: approve the final revision and the registered run** | human | not given → stop |

## Phase 3 — registered run (after decision 2), once

Order within the caps; two to four training workers as fixed in the freeze from the rehearsal, four simulation workers, 24 GiB aggregate (decision 1).

1. Generator and chance gates (G1, G2) for every size. Failure stops that size.
2. Lane C synthetic part and Lane D version-store test (no model needed) run alongside.
3. R2 diagnostic cells at each size (gate G3 was decided in the calibration).
4. Lane A cells, smallest size first; Lane D phase A in parallel.
5. Lane B and C1 cells (16,384 slots); Lane D phase B.
6. Evaluation, knock-outs, ablations per cell as it finishes.
7. Layouts on calibration streams; simulations.
8. Analysis once; classes by the registered rules.

A failed cell stops cells that depend on it; other lanes continue; nothing is re-run with changed settings.

## Phase 4 — audit and delivery

- Opus recomputes from raw records with separate code.
- Lead writes `RESULTS.md`, the review and the decision memo; dashboard with the plots listed in the human draft §13, each tied to its question.
- Draft pull request. No merge.

## Dependency between lanes

- Lane B reads Lane A's dose-zero 16,384-slot cells as its controls.
- Lane C's trained interpretation needs the architecture's 4K→16K step supported (Lane A 4K and 16K cells, including B102) and its B1 α_u = 0.25, α_c = 0 cell UTILIZATION_PRESERVED or IMPROVED (Lane B).
- Lane D is independent in training after the common freeze; it is NOT_EVALUATED if 16,384 slots is TASK_CEILING_FAIL.
