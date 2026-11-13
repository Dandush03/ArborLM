# P4: frozen-backbone memory helped; the dense adapter did better

New hierarchical memory improved next-byte prediction in every registered
comparison with an unchanged frozen backbone. Shuffling its values raised loss
in every learned memory run. Both effects passed their registered criteria.
The equal-parameter dense adapter nevertheless had lower loss in all 27 matched
pairs. The dense tolerance and composite P4 criteria failed. P1–P3 outcomes
remain unchanged.

All 63 [preregistered cells](../../docs/decisions/ADR-0009-frozen-backbone-capacity.md)
completed: nine unchanged P3 controls, 27 memory additions, and 27 dense
additions. Each addition trained 198,401 parameters for 512 updates on the same
batch stream as its paired alternative. Each of the 27,392 backbone parameters
remained frozen. Every loss below is in nats per UTF-8 byte on the previously
unevaluated 512-chunk P4 panel at eligible ranks 1536–2047.

| Variant | Runs | Mean initial NLL | Mean final NLL | Runs with lower final NLL than their initial NLL |
|---|---:|---:|---:|---:|
| Frozen baseline | 9 | — | 2.378856373 | — |
| Hierarchical memory | 27 | 2.378856566 | 2.356867678 | 27/27 |
| Dense adapter | 27 | 2.378920873 | 2.350685041 | 27/27 |

| Paired effect over 27 cells | Mean | Sample SD | Minimum to maximum | Positive / negative |
|---|---:|---:|---:|---:|
| C: baseline minus memory | 0.021988695 | 0.005463392 | 0.012238812 to 0.030320093 | 27 / 0 |
| D: disabled memory minus memory | 0.021988695 | 0.005463392 | 0.012238812 to 0.030320093 | 27 / 0 |
| P: shuffled values minus memory | 0.022221519 | 0.005334219 | 0.012295876 to 0.030177221 | 27 / 0 |
| C_dense: baseline minus dense | 0.028171332 | 0.005893031 | 0.019236114 to 0.037502293 | 27 / 0 |
| Q: dense minus memory | −0.006182638 | 0.002503768 | −0.013191983 to −0.002779022 | 0 / 27 |

- **Added predictive capacity: passed.** Mean C exceeded 0.005, all 27 cells
  and all nine parent means were positive, and mean memory loss fell during
  training. Disabling the addition reproduced the frozen baseline bitwise, so
  D equals C exactly; these are not independent pieces of evidence.
- **Useful slot-association dependence: passed.** Mean P exceeded 0.005.
  Both C and P were positive in all 27 pairs, and all nine parent means for P
  were positive. Joint permutations of keys and values within branches passed
  the invariance control.
- **Within dense quality tolerance: failed.** Mean Q was below −0.005, and
  only 10/27 pairs and 2/9 parent means were within the tolerance. The secondary
  memory-advantage flag also failed. The composite criterion required all
  three primary flags.

Freezing the backbone rules out concurrent backbone updates as the source of
these gains. It does not show that the additions learned semantic knowledge or
that hierarchical lookup is better than flat or fixed memory. P4 also does not
establish that freezing is better than joint training: P3 used a different
memory initialization and evaluation panel. The dense and
memory additions match in trainable parameter count and updates; active
computation, lookup cost, initialization effects, and optimal tuning can
differ. These nine parents, shared seeds, and the same corpus split do not give
27 independent replications. Exact chunk exclusion cannot rule out shared
articles or near-duplicates. These are bounded descriptive results, with no
significance, generalization, efficiency-frontier, SSD, or scaling claim.

The [per-run CSV](per-run.csv) records initial, final, and intervention losses,
timing and memory. [Paired effects](paired-effects.csv) and the
[independent recomputation](root-analysis.json) preserve full precision,
individual signs, parent means and seed/backbone/order marginal summaries.
The [suite result](suite/result.json) records every clause and cell.

The corpus was the pinned local WikiText-2 acquisition under the research lead's
[local-use approval](../../docs/decisions/ADR-0004-real-data-pilot-prerequisite.md).
The publisher card lists CC BY-SA 3.0 and GFDL in its front matter, but CC BY-SA
4.0 in its body. The discrepancy remains unresolved. No corpus bytes or
binary model weights were published.

## Execution and verification

- The design was preregistered at `049bd1f77383151c9e15be561c4b63af6beaca42`.
  The nine registered parents came from
  [P3-LT](../p3-lt-2026-11-12/), suite
  `P3LT-20261113T033545902673Z-befd369dda744953a2ed6fc3a8108d1d`.
  [Parent and data preflight](../p4-preflight-2026-11-12/) records the exact
  checkpoint and data identities.
- The registered run was
  `P4CAP-20261113T043320081674Z-d109080245df457da81e95c6b7300ccd`,
  code freeze `812b3fd02d81124b0665cc96d1364a32e40d403d`. All 63 compact
  bundles were reported and pushed separately. Full local evidence is in the
  matching `experiments/` directory; the command log is
  `experiments/review/p4-execution.v4w9bN`.
- The suite took 652.374330791 seconds and sampled a peak process-tree RSS
  of 670,498,816 bytes. Mean supervised cell wall times were 1.208 seconds
  for baselines, 17.686 for memory and 6.014 for dense; these include run
  overhead and the different evaluation conditions and are not inference
  speed measurements.
- Accounting: 27,648 optimizer updates, 14,155,776 additional training targets,
  171 snapshots and 288 scientific evaluations (54 initial, 63 final, 171
  replay/intervention). Nine separate P3-panel integrity checks passed
  bitwise and do not enter the P4 metrics. All 63 enabled replays, 54
  disabled-baseline checks and 27 joint-permutation checks passed.
- The new panel SHA-256 is
  `4c6fb3f3a8f22d2e5b14c6703d3d8e02b40681482d5b93ba491e2df0583dc28f`.
  The invariant source archive SHA-256 is
  `18ef61bc3608eed4382ba922dd02b714c9810279d8abed6227579be0b3a9f8c0`.
  [The suite manifest](suite/manifest.json) records the config, spec, lock
  and dataset identities. Actual HEAD and dirty flags are retained while
  result-only commits were made. The
  [final freeze proof](../p4-preflight-2026-11-12/final-freeze-proof.md)
  matched all 63 source maps and the P3 source records before any portability
  repair.
- Local [preflight](../p4-preflight-2026-11-12/) passed Ruff, mypy (38 files),
  all 116 tests and 11 E0 smoke gates. The
  [original Linux CI log](../p4-preflight-2026-11-12/code-freeze-ci-43366259292.log)
  preserves a failure caused by one synthetic test's floating-point reduction
  expectation. After a test-only portability repair, the
  [final local checks](root-final-checks.log) passed all 117 tests, Ruff,
  mypy (38 files), and all [11 E0 smoke gates](root-final-e0-result.json).
  The experiment evaluator and raw outcomes were unchanged. GitHub CI status
  is tracked on [draft PR #1](https://github.com/Dandush03/ArborLM/pull/1).
- Root independently reproduced the arithmetic and decision flags from raw
  events; see the [audit output](independent-analysis.log). The
  [independent artifact audit](independent-artifact-audit.md) passed for all
  171 checkpoints; root reviewed and reran the published audit, which exited
  successfully with byte-identical output. The
  [authorized scientific review](authorized-scientific-review.md) records the
  interpretation. Astra review was not performed under the human-authorized
  reviewer exception. Human merge, publication and scaling approval remain
  pending.

The registered command, run once from the repository root, was:

```sh
uv run --locked --extra pilot python -m arborlm.frozen_capacity \
  --data-dir data/wikitext2 --output-root experiments
```

This requires the original registered P3 checkpoints, pinned local Parquet
files, and a matched numerical environment. The checkpoints and corpus
remain local. An authorized repeat must use a fresh `--results-root`.
The compact records suffice for the independent arithmetic audit, which
regenerates the derived tables without reading the corpus or training:

```sh
python3 results/p4-2026-11-12/independent-analysis.py
```
