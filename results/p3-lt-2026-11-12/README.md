# P3-LT: longer training improved prediction but missed memory-dependence thresholds

All 36 [preregistered continuations](../../docs/decisions/ADR-0008-bounded-longer-training.md)
completed. The 27 learned cells and nine controls resumed their P2 checkpoints at
step 256 and continued through step 1024 with the same optimizer state and the
same 2,048 examples in the same order each epoch. Every trajectory improved
validation loss. Mean sensitivity to disabling memory and shuffling its values
also increased, but both registered memory-dependence flags failed. The endpoint
quality guard passed. P1 and P2 outcomes remain unchanged.

All comparisons below use the previously unevaluated 512-chunk panel at eligible
validation ranks 1024–1535. Values are means in nats per UTF-8 byte. D is disabled
minus enabled loss; P is shuffled-values minus enabled loss; G is the paired
trained control minus enabled loss; S is that control minus disabled loss.

| Step | Learned NLL | Nine controls' NLL | D | P | G | S | Both D and P positive | Both at least 0.005 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 2.594546346 | 2.601781534 | 0.000691395 | 0.000688672 | 0.007235188 | 0.006543793 | 21/27 | 0/27 |
| 512 | 2.513888440 | 2.516370131 | 0.002010756 | 0.001940696 | 0.002481690 | 0.000470934 | 21/27 | 4/27 |
| 1024 | 2.371057345 | 2.374478857 | 0.003416745 | 0.003204836 | 0.003421512 | 0.000004767 | 24/27 | 6/27 |

- **Duration dependence: failed.** At step 1024, mean paired ΔD was 0.002725350
  and mean ΔP was 0.002516165. Both changes were positive in 22/27 cells, meeting
  the sign-count condition, but both means fell below 0.005. Four individual
  cells had both increments at least 0.005.
- **Endpoint dependence: failed.** Both effects were positive in 24/27 cells,
  but neither endpoint mean reached 0.005. The six cells with both absolute
  effects at least 0.005 all used backbone seed 103; this is a descriptive
  observation, not a basis for selecting a seed or claiming a causal effect.
- **Endpoint quality guard: passed.** Mean learned loss fell from 2.594546346 to
  2.371057345, and endpoint mean G remained positive. All 27 learned cells and
  all nine controls improved from step 256 to both step 512 and 1024; 15 learned
  cells beat their paired control at 1024 and 12 did worse.

The mean advantage over separately trained controls narrowed from 0.007235188 to
0.003421512 even as intervention effects grew. At the endpoint mean S was
0.000004767, close to zero: the disabled learned backbones and the separately
trained controls had similar average loss. This decomposition does not identify
an optimization mechanism. Longer training increased measured dependence on this
panel, but it did not satisfy the preregistered requirement that all three flags
pass. Individual positive trajectories and aggregate misses are both preserved.

The primary paired changes from step 256 to 1024 had the following descriptive
factor ranges and additive residual root mean square (RMS). Full marginal means,
sample standard deviations, minima, maxima, sign counts, and the secondary
step-512 analysis are in [the recomputation](root-analysis.json) and
[the suite summary](suite/result.json).

| Primary change | Backbone range | Memory range | Order range | Interaction RMS |
|---|---:|---:|---:|---:|
| ΔD | 0.003902689 | 0.001060478 | 0.001262004 | 0.002403000 |
| ΔG | 0.038510257 | 0.035498074 | 0.011358652 | 0.039964669 |

The same validation split supplied the earlier panels. Exact chunk exclusion
does not rule out shared articles or near-duplicates. The cells share data,
factors, and controls, and the durations repeat measurements on the same
trajectory. This design tests duration on fixed examples; it does not settle
what more unique data or a different design would do. It establishes no
statistical significance, generalization, semantic storage, matched-compute
advantage, or scaling authorization.

## Run and audit records

- Source freeze: `861c137a7fcccf27e3371ca2217fd7d956753ca9`. Preflight passed
  Ruff, mypy (31 files), 90 tests, and all 11 E0 smoke gates; see
  [preflight evidence](../p3-lt-preflight-2026-11-12/). Sol ran the suite; each
  completed cell was reported in chat and pushed as a separate compact bundle.
- Local suite: `experiments/P3LT-20261113T033545902673Z-befd369dda744953a2ed6fc3a8108d1d`;
  execution log: `experiments/review/p3-lt-execution.w8OqaT`. Suite worker wall
  time was 871.734423 seconds; peak sampled process-tree RSS was 650,657,792 bytes.
  The worker cap covered verification, training, evaluation, and evidence
  packaging. The supervisor finalized the terminal record and closed logs
  after worker exit. No reporting pauses were inserted.
- There were 27,648 continuation updates and 14,155,776 additional targets
  (18,874,368 lifetime targets). The 108 snapshot indexes cover zero-new-training
  conversion at 256 and continuation at 512 and 1024. There were 459 new-panel
  evaluations (108 reference and 351 intervention/replay) and 36 old-panel
  bitwise integrity checks. Old-panel checks were excluded from all scientific
  metrics. All 108 new-panel replay checks and 81 joint-permutation checks passed.
- All cells retained their recorded HEAD and dirty flags: 35 reported
  `dirty=true` while result-only tracking was active. Shared source archive
  SHA-256 `7be7aaccde57383961e530b64bdc6902df3f3b690af2857f68db0c5f96ad75a0`
  matched across cells. The [suite manifest](suite/manifest.json) records
  config, spec, data, and lock identities; the new panel SHA-256 was
  `a2d63d4ed5300c74f49374c0e0c5bd6e70d4361bc0b2933a8d5ad33a08d724b0`.
  Parent checkpoint binaries, source archives, and corpus bytes remain local.
- Root independently recomputed counts, paired effects, factor summaries, and
  flags from the compact raw records; all agreed. See the
  [audit output](independent-analysis.log) and [per-duration CSV](per-duration.csv).
  The CSV records each learned and control trajectory's NLL change from step 256;
  the recomputation also lists and summarizes all nine paired control changes at
  each later duration.
  Luna's separate artifact audit is pending at this entry. Astra review was not
  performed under the human-authorized reviewer exception; human merge and
  publication approval remain pending.

From the repository root, the executed command was:

```sh
uv run --locked --extra pilot python -m arborlm.longer_training \
  --data-dir data/wikitext2 --output-root experiments
```

The continuation requires the exact registered local P2 suite and original
checkpoint binaries, the pinned local corpus, and the matched numerical
environment. Freshly regenerated parents have different registered identities.
For an authorized repeat, use a fresh `--results-root`; the existing export is
protected from overwrite. Compact records alone support the independent
recomputation without model training or access to the corpus:

```sh
python3 results/p3-lt-2026-11-12/independent-analysis.py
```
