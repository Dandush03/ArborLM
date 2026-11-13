# P6 results and review — P6-E and P6-Q

- Label: `RESULT: FABLE-REVIEWED, OPUS-AUDITED — ASTRA NOT_PERFORMED — PENDING HUMAN REVIEW`.
- Specification: [ADR-0011](../../decisions/ADR-0011-p6-retrieval-optimization-and-routing-fidelity.md), human-approved 2026-11-13, frozen at commit `a786c5d`. Raw records committed at `c389fe7` before interpretation, with no source change since the freeze.
- Each study was run exactly once. Nothing was re-timed, rerun, retuned or selected. P1–P5 are unchanged; the P5 composite criterion remains FAILED.
- Reviewer: Claude Fable 5.2. Independent recomputation: Claude Opus 5.5, [`../p6-results-audit-2026-11-13/AUDIT.md`](../p6-results-audit-2026-11-13/AUDIT.md), which matched every verdict, flag, clause and ratio of the implementation's analysis with zero numerical discrepancies. Who did what: [DELEGATION.md](DELEGATION.md).

## 1. Registered outcomes

| Criterion | Fixed tree | Learned tree |
|---|---|---|
| **EQ** — numerical equivalence of the selected variant | PASS | PASS |
| **SP** — material speedup over the original implementation | **INCONCLUSIVE** | **INCONCLUSIVE** |
| **PAR** — no slower than flat | **INCONCLUSIVE** | **INCONCLUSIVE** |
| **PR** — P5's latency margins against flat | **INCONCLUSIVE** | **INCONCLUSIVE** |
| **FID** — recall ≥ 0.95 against exhaustive search under the tree's own rule | **FAIL** | **FAIL** |
| **COS** — recall ≥ 0.95 against exhaustive cosine search | **FAIL** | **FAIL** |
| **LOSS** — exhaustive search improves prediction by ≥ 0.005 | **FAIL** | **FAIL** |
| **PRIOR** — the prior changes prediction by ≥ 0.005 | **FAIL** | **FAIL** |

Predictions: E-H1 (T1, T2 bitwise) held. E-H2 (T3–T5, F2 at least bounded) held. E-H3 (material speedup) and E-H4 (practicality) are **undecided**.

**P6-E has no registered pass.** The timing criteria are inconclusive because about a quarter of the timing records failed the stability rule fixed in advance. That is not a failure of the optimization and not a success either.

## 2. P6-E — equivalence (measured, registered)

All seven variants passed the equivalence gate on every checkpoint, on the full P5 panel (32,768 queries per checkpoint), both timing input shapes and the constructed-tie fixtures.

| Variant | Class | Checkpoints |
|---|---|---|
| F1 cached flat keys; F2 + selection kernel | STRICT (bitwise) | 27/27 each |
| T1 cached normalization; T2 + ID-ordered candidates; T3 + block layout | STRICT (bitwise) | 54/54 each |
| T4 gather-free branch-grouped scoring; T5 + selection kernel | BOUNDED | 54/54 each |

For T4 and T5: zero queries with a different selected slot or order, largest score difference 1.9e-6, largest logit difference 4.8e-6, largest panel-NLL difference 3.7e-8, zero tie-rule violations. The guard band sent 0.29% of panel queries to the exact fallback. Every checkpoint replayed its recorded P5 NLL bitwise; checkpoint files, model state and RNG were unchanged.

So the tree retrieval can be reimplemented for inference without changing which slots it selects. That part is established for these checkpoints on this machine and build.

## 3. P6-E — timing (measured; registered verdict INCONCLUSIVE)

Screening selected T5 for both tree kinds and F1 as the flat comparator (F1 2,584 µs, F0 2,594 µs, F2 5,999 µs: the successive-maxima kernel is much slower than `topk` on flat's 4,096-wide rows). Confirmation then timed only T0, T5, F0 and F1 in fresh processes.

Confirmation stage, primary workload (batch 8 × context 64), geometric mean over 27 pairs of median ratios:

| Ratio | Fixed | Learned | Registered limit | Clause arithmetic |
|---|---:|---:|---:|---|
| T5 / T0, addition | 0.292 | 0.286 | ≤ 0.50 | met, 27/27 pairs, 9/9 parents |
| T5 / F1, addition | 0.747 | 0.729 | ≤ 0.80 (PR), ≤ 1.00 (PAR) | met, 27/27, 9/9 |
| T5 / F1, full forward | 0.812 | 0.789 | ≤ 1.05 | met, 27/27, 9/9 |

Absolute medians, addition scope: T0 6,823 / 6,789 µs; T5 1,951 / 1,912 µs; F0 2,651 µs; F1 2,639 µs.

**Why this is not a pass.** The reliability rule requires, for all 27 pairs, that the largest and smallest round medians differ by no more than 1.25×. In confirmation 344 of 1,296 records (26.5%) failed it; in screening 792 of 3,240 (24.4%). In P5 the figure was 4 of 612 (0.65%). Only 17–18 of 27 pairs per tree kind have both records usable. The instability hit the unmodified references (T0 21%, F0 24%) nearly as much as T5 (31–36%), clustered by worker and by time period. A load reading taken by the lead immediately after confirmation showed a load average near 20 from unrelated processes on the same machine (node, a virtual machine, headless browsers). That reading is one snapshot after the fact; no load was recorded during the stage, so the cause is plausible and unproven.

**Not registered results, shown only as context:** restricted to pairs where both records were usable, the ratios are 0.286 / 0.278 (T5/T0), 0.742 / 0.720 (addition vs F1) and 0.804 / 0.782 (forward), over 16–18 pairs covering 6–7 of 9 parents. They cannot substitute for the registered verdict.

**The advantage is specific to the large batch.** Descriptive secondary workloads, T5 / F1 at the addition scope:

| Workload | Queries per call | Fixed | Learned |
|---|---:|---:|---:|
| W8, batch 8 × 64 | 512 | 0.747 | 0.729 |
| W1, batch 1 × 64 | 64 | 1.456 | 1.368 |
| Wtok, batch 1 × 1 | 1 | 3.38 | 3.33 |

At 64 queries per call the optimized tree is slower than flat in every pair, and at a single query it is more than three times slower, and also slower than the original tree (1.89× / 1.83×). The per-branch grouping that helps large batches costs more than it saves for small ones. Single-token decoding is the workload closest to the project's goal, so this matters more than the W8 estimate.

**Memory (allocator-level, as recorded):** persistent extra state for T5 is 265,216 bytes. Per W8 addition call, allocated / peak: T0 51.0 / 36.8 MB; T5 12.4 / 5.4 MB; F0 18.6 / 16.8 MB. No statement about cache misses, bandwidth or physical I/O is supported.

**Resources:** equivalence 411 s, screening 820 s, confirmation 341 s; 1,572 of 3,000 s; peak RSS 617 MB.

## 4. P6-Q — routing fidelity (measured, registered)

54 final checkpoints, P5 panel, same weights evaluated under four selection rules.

| Quantity | Fixed | Learned |
|---|---:|---:|
| Recall of exhaustive selection under the tree's own rule (`recall_P`) | 0.791 | 0.915 |
| Fraction of queries with identical selection | 0.320 | 0.655 |
| Same recall weighted by the attention weight of each slot | 0.882 | 0.956 |
| Recall of exhaustive cosine selection (`recall_C`) | 0.262 | 0.273 |
| Branches needed for recall ≥ 0.97 | 6 | 3 |
| NLL change with exhaustive search, prior on (`Δ_restrict`) | +0.00044 | +0.00002 |
| NLL change with prior removed, top-2 (`Δ_prior`) | +0.00386 | +0.00393 |
| NLL change with exhaustive cosine search (`Δ_both`) | +0.0128 | +0.0110 |
| Queries with all 8 selected slots in the top-1 branch | 14.9% | 29.0% |
| Lost candidates that were never trained | 0.14% | 0.14% |

Positive NLL change means the alternative rule predicts worse than the registered rule.

Engineering gates: the registered rule reproduced P5's NLL and concentration statistics exactly on every checkpoint; the structural identities held; the frozen and float64 references disagreed on selected sets in 12 queries overall, all at boundary gaps ≤ 8.3e-7, within the predeclared near-tie exemption. 16 of 27 descriptive step-0 checkpoints ran before the 1,800 s budget ended (1,751 s used); the 11 unexecuted ones are b102-o303 seeds 502–503 and all of backbone 103.

**Reading, within the interpretations fixed before the run (ADR-0011 §4.5, row "FID fails, LOSS fails"):** the top-2 restriction changes the selection relative to exhaustive search under the tree's own rule, but these weights do not predict better with exhaustive search. Whether a model *trained* with wider search would do better is not answered.

What this adds:

1. **Candidate loss is real but light.** One in five reference slots is missed by the fixed tree, yet those slots carry little attention weight (weighted recall 0.88) and adding them does not help. Nearly all lost slots are trained slots in the third- or fourth-ranked branch, so the earlier worry that low recall would just reflect untrained slots is not what happened.
2. **The learned tree's higher recall is not better routing.** Its router produces a sharper prior (median route gap 1.70 vs 1.15). Exhaustive search under the prior then penalizes unvisited branches more, so agreement rises by construction. Without the prior the two trees' recall differs by 0.011. Across the 54 checkpoints recall correlates with route gap at r = 0.71.
3. **The prior helps these weights a little.** Removing it raises NLL in all 54 checkpoints and all 18 parent means, by about 0.0039. That is 0.0011 short of the registered 0.005 magnitude, so PRIOR is a registered FAIL. The hypothesis that the prior is a design fault (P5 review H-c, in its harmful form) is not supported. The uniformly positive sign on 27 correlated cells and one already observed panel cannot settle more than that.
4. **The tree's keys are not a usable flat index.** Exhaustive cosine search over the tree's keys agrees with the tree on only about a quarter of slots and predicts worse by about 0.012. The weights are adapted to the routed rule they were trained under.

## 5. What P6 establishes, and what it does not

Established for these checkpoints, this machine and build:

- The hierarchical retrieval can be computed by a faster inference path that selects exactly the same slots.
- The 2.6× slowdown P5 measured belonged to how the tree was written. At 512 queries per call every one of the 27 pairs ran faster with the optimized path than with the original, with point estimates near 0.29×.
- Top-2 routing does not select the same slots as exhaustive search, and exhaustive search does not improve prediction with these weights.

Not established:

- **That the tree is faster than flat.** The estimate at 512 queries (about 0.73–0.75× on the addition) is unconfirmed under the registered reliability rule, and at 64 queries and at one query the optimized tree is slower than flat.
- That flat could not be made faster. Five tree variants were tried against two flat ones, and neither flat variant reduced flat's dominant cost, `topk` over 4,096-wide rows. The comparison is "optimized tree versus flat with cached normalization", as registered.
- Anything about larger memories, SSD, physical I/O, capacity scaling, training cost, or learned routing as a concept.
- That the routing restriction is harmless. Only retraining under a different rule could show that.

Against the decision matrix fixed in ADR-0011 §5: EQ passed and the timing criteria are inconclusive, a combination the matrix did not list. The nearest listed rows would recommend a kernel size-scaling study; that recommendation is **not** triggered by an inconclusive result.

## 6. Known defects in the records

- All 81 P6-E worker manifests and the 70 P6-Q cell manifests carry template text inherited from the E0 record helper: they cite `ADR-0003-e0-approved-spec.md`, `question_id: G0` and "infrastructure validation only". The stage-level manifests and source hashes are correct, and no number is affected. The records are left as written and the defect is stated here.
- The stage-level P6-E manifests have empty review fields.
- No machine load was recorded during timing.
- **Post-run test-only repair.** Two tests in `tests/test_p6_retrieval.py` asserted that `results/p6-e-2026-11-13` did not exist, as a guard that dry runs never write there. They passed at the freeze and failed once the registered run had written its records. They now assert that a dry run leaves that folder unchanged. No study source, record or number changed; `git diff c389fe7 -- src results` is empty.
- The freeze was committed locally and not pushed before execution, at the human lead's instruction; see ADR-0011 §7.
- The float64 reference used in P6-Q's gate (iv) was written by the auditor role, so the auditor's review of that gate is not independent of its own code.

## 7. Questions for the human research lead

1. **P6-E timing.** The registered verdict is INCONCLUSIVE and will stay so. Do you want a fresh, separately registered confirmation timing (new run identity, same protocol, on a machine with nothing else running, with load recorded)? It would take about six minutes of quiet machine time. It would be a new study record, not a rerun of this one.
2. **Workload.** The optimized tree loses to flat at small batches and single queries. Should the next efficiency question be registered on single-token decoding, since that is the target use?
3. **Flat baseline.** Should a future study give flat an equal optimization effort before any tree-versus-flat claim?
4. **Direction.** P6-Q says routing changes selection without costing prediction for these weights, and the learned router mostly sharpens the prior. Options, each needing its own specification: a kernel size-scaling study on synthetic tensors; a routing-design study with retraining; or stopping the hierarchy line.
5. **Governance.** ADR-0012 is still awaiting your decision.
