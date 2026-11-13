# P5 — hierarchical memory architecture ablation

All 117 quality cells and 36 timing workers completed under the approved [ADR-0010](../../docs/decisions/ADR-0010-hierarchical-memory-ablation.md). Every quality cell and timing worker was reported in the research conversation and committed/pushed separately. No result was selected, retuned or rerun. P1–P4 remain unchanged.

**Final review:** independent arithmetic, binary-artifact, utilization and reporting/resource audits passed; root read the checkers and reproduced their outputs byte for byte. The [authorized scientific review](authorized-scientific-review.md) accepts the bounded findings and preserves the failed composite criterion. Astra review: **NOT_PERFORMED**. Root Codex is the authorized scientific reviewer under the human's recorded exception; Sol implemented/executed and Luna supplied separate engineering review.

## Result

All three memory architectures added useful predictive capacity to frozen backbones. Training the router did not improve upon fixed routing at the registered criterion. Both trees stayed within the allowed quality loss relative to flat memory and reduced observed score work, but took substantially longer on the registered CPU workload. **The full learned-hierarchy criterion failed.** Dense adapters had the lowest mean NLL; none of the memory variants passed the separate dense-reference consistency criterion.

| Variant | Mean final NLL ↓ | Mean gain over frozen baseline ↑ | Mean value-shuffle penalty ↑ |
|---|---:|---:|---:|
| Frozen baseline, 9 parents | 2.356630572 | — | — |
| Flat, 27 cells | 2.333691890 | 0.022938682 | 0.022679532 |
| Fixed tree, 27 cells | 2.334497243 | 0.022133329 | 0.021944248 |
| Learned tree, 27 cells | 2.335080704 | 0.021549867 | 0.021603653 |
| Dense adapter, 27 cells | 2.329312946 | 0.027317625 | — |

Losses are nats per byte. These are correlated paired observations sharing nine parents, seed factors and one validation panel, not 27 independent experimental replications. Full dispersion, parent summaries, marginals and raw measurements are retained.

| Registered criterion | Result |
|---|---|
| Useful memory U, separately for all three architectures | PASS: positive gain and shuffle effect in 27/27 cells and 9/9 parent means for each |
| Learned routing improvement R | FAIL: mean fixed-minus-learned NLL −0.000583461; positive in 10/27 cells and 3/9 parents |
| Tree quality tolerance relative to flat Q | PASS for both: 26/27 cells and 9/9 parent means within +0.005 NLL |
| Observed key/router score-work reduction W | PASS for both: 528/4096 = 0.12890625 of flat score work |
| Primary measured latency L | FAIL for both; all 27 primary pairs reliable, none meets the pairwise latency margins |
| Dense-reference quality tolerance | FAIL for flat, fixed and learned; respectively 15/27, 14/27 and 13/27 cells within tolerance |
| Full learned-hierarchy criterion | FAIL |

## Quality versus retrieval work

| Measure | Flat | Fixed tree | Learned tree |
|---|---:|---:|---:|
| Trainable addition scalars | 198,145 | 198,145 | 198,401 |
| Persistent fixed-router buffer scalars | 0 | 256 | 0 |
| Key comparisons per query | 4,096 | 512 | 512 |
| Router dot products per query | 0 | 16 | 16 |
| Logical candidate-key + router elements/query | 65,536 | 8,448 | 8,448 |
| Selected value elements/query | 256 | 256 | 256 |
| Mean NLL difference from flat | 0 | +0.000805353 | +0.001388814 |
| Addition latency ratio to flat, geometric mean | 1 | 2.603052 | 2.598485 |
| Full-forward latency ratio to flat, geometric mean | 1 | 2.190282 | 2.184086 |

Ratios use each paired worker's median for CPU batch 8 × sequence length 64. They describe this implementation and workload. Logical elements and operand counts are not physical memory traffic, FLOPs, SSD reads, RAM savings or decode throughput. All values remain resident. Secondary batch-1 measurements and all raw timing samples are preserved without substituting them for the primary criterion.

## Reproducibility and evidence

- [Preregistration and human/reviewer approval](../../docs/decisions/ADR-0010-hierarchical-memory-ablation.md); proposal `dabb5db22b38977838da36a801c410ee3544e738`, human approval `f2c5c939e1f94b4eafd04b59043256af1603cc0e`.
- [Preflight](../p5-preflight-2026-11-13/): Sol implementation, Luna independent contracts, root source/math/data/strict-restore review. Final preflight: 161 tests, Ruff, mypy (47 files), and 11 E0 gates passed. Frozen implementation acceptance commit: `9028507844c500bc4d296202e7c6c6e4ae552ecc`.
- [Execution freeze](../p5-preflight-2026-11-13/execution-freeze/), pushed before training as `6b3e25726d709ab0efe05777ab8205bea5b59464`: 95 source files, archive `6be82b23ae0c453c30c588a2ded4c3df0300ac7c20e0d7ff929bd02fc2a7d56e`, spec `b6923c46ac7c2b1997b645ac65542e23a3b432e8b4a25eaf6397b74518958f3f`, lock `07c61871ce8a049deb83a0c353aae4ac75c193023433b86ade1581921a2af761`, resolved config `0341809f966b5f27b1856de91d33f11ba3c80450f87c719b648623768778c4df`.
- Cell folders preserve manifests, raw training/evaluation/routing events, checkpoint indexes/hashes, source/config/environment/data identities, exact training order and intervention permutations. [Quality suite](quality-suite/) and [final suite](suite/) preserve aggregate records and accounting; [timing](timing/) preserves all 36 worker bundles and raw operator/timing evidence.
- [Independent arithmetic](audit/independent-arithmetic.py) imports no ArborLM analysis. [Final root rerun](audit/root-final-arithmetic-run.json) reproduces its output exactly. [Independent engineering audit](audit/independent-engineering-audit.md) and [root artifact rerun](audit/root-artifacts-run.json) verify all 333 actual snapshots and 648 operator traces. [Utilization audit](audit/independent-utilization.md) reconstructs slot/branch counts and entropy. [Reporting/resource audit](audit/root-orchestration-README.md) binds 154 commits to original/compact bytes, preserves 37 ACK files and checks caps and historical preservation. Early failed artifact-checker versions 01–02 were not archived; their error/exit logs remain. The final checker is fully retained and independently reproduced; experiment source and outcomes were preserved throughout.
- [Execution record](implementation-execution.md) contains exact commands, run identifiers, dates and artifact retention.

The single executed command, after preflight and freeze, was:

```sh
uv run --locked --extra pilot python -m arborlm.hierarchy_ablation \
  --data-dir data/wikitext2 --output-root experiments \
  --results-root results/p5-2026-11-13
```

Reproduction requires the original nine P4 baseline parents (with their P3 provenance), pinned local WikiText-2 files, Python/dependency environment and fresh output paths. The CLI refuses to overwrite results and pauses at the quality-stage boundary and after each timing worker for an exact worker-specific reporting ACK. The ACK contract and charged/excluded time are specified in ADR-0010; do not bypass it or run background audits during timing. No corpus or binary checkpoint is redistributed here. Original binaries, optimizer/RNG states and source archives remain in the local experiment tree; GitHub contains reproducible records and checksums. Cross-platform bitwise identity is not promised.

The fresh panel comprises 512 eligible chunks at ranks 2048–2559, SHA-256 `d50cbe4c303791148c922bfe9201fe00b192c44deef855077860ffc98cc72b98`. Independent raw-data checks found no exact overlap with any prior evaluation panel or the full training candidate pool. Same-corpus article overlap and near duplicates remain possible. The existing dataset approval, attribution and upstream license-label caveat remain applicable; no new data was downloaded and the test split was unused.

## Resource record and limits

108 additions × 512 updates = 55,296 updates and 28,311,552 additional targets. There are 333 snapshots, 612 scientific evaluations (20,054,016 targets), nine separate parent-integrity evaluations (294,912 targets), and 58,752 timing calls (9,792 warmups + 48,960 timed calls). No extra real-data forward was added for post-run audits.

Quality-stage wall time: **1,281.554949 / 1,800 seconds**. Active timing: **214.904311 / 600 seconds**. Combined: **1,496.459260 / 2,400 seconds**. Exactly 822.690904 seconds of successful reporting-ACK waits were excluded as preregistered; timing-stage wall time including waits was 1,037.595215 seconds. Setup, restoration, probes, supervision and finalization remain charged. Peak sampled suite RSS: **858,423,296 bytes**, below 2 GiB. No scientific worker failed or exceeded a cap; audit-tooling failures are preserved separately.

This study does not establish novelty, a general architectural impossibility, storage scalability, physical I/O savings, learned topology, or a reason to skip further scientific review. Human approval remains required for merge, publication and any further phase or scaling.
