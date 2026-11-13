# P2 controlled follow-up — small memory effects below registered sensitivity

All 36 preregistered training runs completed: 27 crossed backbone/memory/order combinations and 9 controls with memory disabled throughout. Every run consumed 131,072 training targets; total 4,718,592. Model size, optimizer and training budget were fixed. All settings and flags were frozen in ADR-0007 before outcomes. Sol implemented/executed, Luna supplied independent engineering checks, and root independently reviewed/recomputed under the human scientific-reviewer exception. **Astra review NOT PERFORMED.**

## Results

All values are nats per UTF-8 byte on the previously unevaluated 512-chunk panel; positive D/P means the intervention worsens prediction, positive G/S means the control has higher loss.

| Paired quantity over 27 learned cells | Mean | Sample SD | Range | Positive / negative |
|---|---:|---:|---:|---:|
| D: disabled minus enabled | 0.000693748 | 0.001008201 | -0.000697263 to 0.003419571 | 22 / 5 |
| P: shuffled values minus enabled | 0.000685635 | 0.001002791 | -0.000656441 to 0.003406301 | 22 / 5 |
| G: trained control minus enabled | 0.006731979 | 0.025953640 | -0.048181299 to 0.063023124 | 17 / 10 |
| S: trained control minus disabled | 0.006038231 | 0.025615544 | -0.048242029 to 0.059603553 | 17 / 10 |

The 9 distinct controls have mean NLL **2.593168491**, sample SD **0.025300423**. The 27 learned models have mean **2.586436512**, sample SD **0.021776935**. Each control is reused for three paired comparisons; those comparisons are correlated and are not independent control replications.

Both D and P are positive in 22/27 cells, but **zero cells reach 0.005 for either intervention**. Their maxima are 0.003419571 and 0.003406301. All three registered descriptive flags are **false**: consistent dependence at the registered sensitivity; heterogeneous useful dependence at that sensitivity; and D-factor sensitivity. Flags were not relaxed, and no seed was excluded. Original P1 promotion remains failed.

For D, marginal ranges are backbone 0.000664190, memory 0.000945885, order 0.000332065; combined interaction RMS 0.000858668. All are below 0.005. For G the corresponding ranges are 0.011154403, 0.015191942, 0.015612490, with interaction RMS 0.023140163. These are descriptive grid summaries, not significance tests or population variance estimates.

## Interpretation and limits

The controlled runs demonstrate variation in final training outcomes with initialization and order, while the measured final-checkpoint memory contribution is small at this budget. The seed-44-sized intervention benefit from P1 was not reproduced in these 27 new combinations at the registered sensitivity. This does not invalidate the preserved seed-44 observation or show that memory never helps: 22 new checkpoints worsen when memory is disabled or shuffled, and 5 improve.

Most of the mean gain against separately trained controls persists with memory disabled: G = D + S, and the root audit checked this identity in every cell. Training-trajectory effects remain an explanation to investigate; this experiment does not identify a specific optimization mechanism or establish semantic memory. Memory initialization bundles keys, values, adapters and router; their separate contributions were not isolated. Only one value permutation per cell was tested. Longer training, other objectives and different architectures remain untested.

The panel is new to model evaluation but from the same approved corpus split. Exact chunk overlap with the prior panel and full training candidates is zero; shared articles, near-duplicates and corpus-specific effects remain possible. The grid has shared factors/data/controls; no p-values, independent-replicate confidence intervals, generalization, novelty, matched-compute superiority, inference-speed or SSD claims are made. The experiment grants no automatic scaling authorization. Human merge/publication approval remains pending.

## Integrity and reproduction

- Code freeze: `fd61cb7a69b8d29484cf8bef0170c1eb168da1fe`; preregistration commit `3c0dd8c`. Each completed cell was reported in chat and committed/pushed separately. Actual Git HEADs vary due to result-only commits, while all 36 source archives, config/spec/data/lock hashes are identical. No source or scientific setting changed during execution.
- Command: `uv run --locked --extra pilot python -m arborlm.optimization_followup --data-dir data/wikitext2 --output-root experiments`. For a repeat, use a fresh `--results-root` to preserve this export; the CLI refuses to overwrite existing results. Same-environment determinism only; no cross-platform bitwise promise.
- Local full suite: `experiments/P2-20261113T030106857200Z-d08b874d11e74a7391b15f762e40f0c7`; execution log: `experiments/review/p2-execution.lbqdqS`.
- Runtime 321.710462 seconds; peak sampled process-tree RSS 676,052,992 bytes, within 1,800 seconds / 2 GiB. 9,216 training events, 72 initial/final training evaluations and 117 frozen-checkpoint evaluations are retained. All 36 enabled replays and 27 joint permutations matched bitwise; intervention evaluations did zero training. All original saved checkpoint bytes remained unchanged.
- P2 panel SHA-256 `8cd4ab927f9ff17f12bba56b011cf11a94d66e1b77f5f4eba97dd100fb455cd2`; source archive `6fea4b684a364ef85c8cda6ea1df683f9e7f8332dd4645caf7094b620da02801`. Complete identities, seeds, hardware, installed versions, commands, routing metrics, order/permutation IDs and checkpoint indexes are in each cell and `suite/`.
- `root-analysis.json`, `per-training-run.csv` and `paired-effects.csv` are derived records. Root independently recomputed all deltas, counts, marginal means/ranges, interaction RMS and flags directly from raw per-cell records without importing the implementation analysis code; no discrepancy found. Separate independent artifact audit is recorded alongside these results when complete.
- 79 tests, lint, typecheck and E0 smoke passed before execution; see `../p2-preflight-2026-11-12/`. Optional NumPy integration warning remains nonblocking. Corpus and checkpoint binaries/source archives stay local; only compact evidence is published. Dataset rights discrepancy remains documented in ADR-0004; no corpus/weight redistribution rights are inferred.
