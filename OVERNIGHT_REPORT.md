# Overnight report — 2026-11-14 (UTC)

Prepared by Claude Fable 5.2 as scientific lead. **Astra review: NOT_PERFORMED.** Everything below is pending your review. Simulated page misses are not physical I/O.

## In one paragraph

Both stacked pull requests are merged and `main` holds the full P1–P7-B history. P8 was preregistered, independently reviewed and audited, frozen, and run exactly once. **It is a negative and incomplete result:** no case met the locality criteria, and five of sixty cells could not be simulated. Every locality objective made the memory use far fewer slots (46–92% fewer); simulated misses fell only because the working set shrank into the cache. There is no evidence that explicit locality training, at this dose, creates structure beyond slot popularity, and no evidence of a tree-specific benefit. I stopped at the review boundary.

## Phase 0 — merges

| | |
|---|---|
| PR #3 (P7-A) | merged with a merge commit, `8d52862` (CI on the PR passed; CI on `main` after the merge passed) |
| PR #4 (P7-B) | retargeted to `main`; its diff was exactly the P7-B files (1,233 added, 3 edited), and the merged tree is identical to the tree its CI tested; merged with a merge commit |
| **Final merged `main`** | **`57be5ff4e5e0ed319da90bcb2ac161bc6574e709`** — CI passed |
| P7-B disclosed defects | untouched (null-fit flag and record-reporting defects remain as written) |
| Not done | no squash, rebase, force-push or hook bypass; both PRs were drafts and were marked ready in order to merge; no branch, checkpoint or dataset was deleted |

## Phase 8 — delivery

| | |
|---|---|
| Draft PR | **https://github.com/Dandush03/ArborLM/pull/5** (draft, not merged) |
| Branch | `claude/p8-locality-aware-training`, from merged `main` |
| Head when this report was written | `b78f53840fabf6c02fea3c2bd101a46f2d2c43a7`; the commit adding this file follows it (see the PR for the final head) |
| Freeze commit | cited as `80f46ae` in all records; pushed as `378aeac` (messages were reduced to single signed lines for your pre-push hook; file contents identical — [COMMIT_MAP.md](docs/reviews/p8-results-2026-11-14/COMMIT_MAP.md)) |

## Completed versus expected

| Stage | Completed | Expected |
|---|---:|---:|
| Training cells | 60 | 60 |
| Restore gate | 10 | 10 |
| Evaluated on Panels A and B | 60 | 60 |
| **Simulated** | **55** | **60** |
| Analysis | run once, **study status INCOMPLETE**, denominator kept at 60 | |

The five missing cells are concentration controls (C04 ×2, C05 ×3) that select the same eight slots on every query; the unchanged P7-A null generator could not build their null. I did not repair, rerun or substitute them.

## CI, tests, audits

- At the freeze: ruff and mypy clean; 798 tests passed, 3 skipped (skips need local data).
- CI on PR #5: started at push; check the PR for its result — I did not wait for it before writing this file.
- Opus 5.5 audits: spec review (NOT READY → fixed in revision 2); independent panel proof (eligible, unused, disjoint); training audit; evaluation/simulation/analysis audit; re-check (READY TO FREEZE); independent recomputation of results (1,232 analysis values and 2,032 trace statistics, **zero differences**).

## All ten cases

Means over six cells, Panel A / Panel B. Full table with every setting: [scorecard.csv](results/p8-2026-11-14/report/scorecard.csv).

| Case | Architecture + objective | NLL change vs baseline | Slots in use vs baseline | Simulated misses vs baseline | Class |
|---|---|---|---|---|---|
| C01 | flat, standard | baseline (NLL 2.3637 / 2.3452) | 127 effective slots | 2.29 per query | — |
| C02 | fixed tree, standard | −0.0002 / 0.0000 vs flat | 103 | 1.75 | — |
| C03 | learned tree, standard | +0.0011 / +0.0013 vs flat | 84 | 1.32 | — |
| C04 | flat + concentration | +0.0106 / +0.0100 | 8% | 0 in the 4 simulated cells | **INCOMPLETE** |
| C05 | learned tree + concentration | +0.0117 / +0.0106 | 11% | 0 in the 3 simulated cells | **INCOMPLETE** |
| C06 | flat + co-access | +0.0033 / +0.0034 | 37% | 15% | **COLLAPSED** |
| C07 | learned tree + co-access | +0.0009 / +0.0011 | 54% | 16–19% | **CONCENTRATION-ONLY** |
| C08 | flat + temporal reuse | +0.0042 / +0.0044 | 17% | ~0 | **QUALITY-FAILED** |
| C09 | learned tree + temporal reuse | +0.0041 / +0.0038 | 25% | ~0 | **NOT REPLICATED** (quality-failed on A, collapsed on B) |
| C10 | learned tree + both | +0.0067 / +0.0062 | 24% | ~0 | **QUALITY-FAILED** |

The locality measure beyond the count-preserving null (E) is **undefined for every regularized case**: the null's own misses also went to about zero.

## Strongest findings

**Positive (measured, not claimed as success):**
- The pipeline is sound: the standard path reproduces P5 bit for bit, the simulator reproduces P7-B exactly, both panels agree to the third decimal, and an independent recomputation matches with zero differences.
- Differentiable locality terms do change routing strongly in 512 updates, and the learned tree with the co-access term kept 95% of the memory's predictive gain on roughly 46 effective slots.

**Negative:**
- No case is LOCALITY-POSITIVE; none beats an optimized flat layout; no architecture advantage.
- All three terms reduce to concentration. Temporal reuse relative to the null did not rise (ratio 1.00–1.03); branch persistence is below chance order.
- The pure concentration control lost about half the memory's gain and collapsed to eight slots in five cells.
- The registered measure became degenerate once utilization fell: this design could not have detected locality beyond popularity at these cache settings.

## Blockers and caveats

1. **Study incomplete** (55/60 simulated), for the reason above.
2. **A deviation I need you to rule on:** the freeze record says a failed cell stops the launch of further cells. Training implements that; the simulation stage does not, and kept going after the first failure. The C06–C10 classes rest on complete records but exist because of that. My wording, and the audits missed it.
3. One registered dose, 512 updates, three correlated parents, two seeds, one corpus, hypothetical row sizes. Panel B is a same-corpus check.
4. The baselines use only about 3% of their 4,096 slots, so this pilot says little about a memory under capacity pressure.
5. The matched-pressure rule did not give a controlled dose (the step coefficient reached about 6·10⁵ after the proxy saturated).
6. The report generator needed a one-line fix after the run (division by zero); it is analysis-only and in its own commit.
7. All roles are Claude models.

Full defect list: [results review §7](docs/reviews/p8-results-2026-11-14/README.md).

## Graphs and datasets

- [report.html](results/p8-2026-11-14/report/report.html) — self-contained report
- [SUMMARY.md](results/p8-2026-11-14/SUMMARY.md) — Markdown summary
- Figures: [scorecard](results/p8-2026-11-14/report/fig01_scorecard.png) · [quality vs locality](results/p8-2026-11-14/report/fig02_quality_vs_locality.png) · [utilization](results/p8-2026-11-14/report/fig03_utilization.png) · [null vs actual misses](results/p8-2026-11-14/report/fig04_null_vs_actual.png) · [flat vs tree pairs](results/p8-2026-11-14/report/fig05_flat_vs_tree_pairs.png) · [temporal reuse and branch persistence](results/p8-2026-11-14/report/fig06_temporal_branch.png) · [per-parent and per-seed heatmaps](results/p8-2026-11-14/report/fig07_heatmaps.png) · [training and resources](results/p8-2026-11-14/report/fig08_training_resources.png) · [layout controls](results/p8-2026-11-14/report/fig09_layout_controls.png)
- Data: [scorecard.csv](results/p8-2026-11-14/report/scorecard.csv) · [cells.csv](results/p8-2026-11-14/report/cells.csv) · [pairs.csv](results/p8-2026-11-14/report/pairs.csv) · [analysis.json](results/p8-2026-11-14/report/analysis.json) · [p8_results_compact.json](results/p8-2026-11-14/report/p8_results_compact.json)
- Raw records: [`results/p8-2026-11-14/`](results/p8-2026-11-14/) (train, evaluate, simulate, analysis, logs, panel)
- Specification: [ADR-0015](docs/decisions/ADR-0015-p8-locality-aware-memory-training.md) · Review: [results](docs/reviews/p8-results-2026-11-14/README.md) · Audits: [spec](docs/reviews/p8-spec-review-2026-11-14/REVIEW.md), [pre-freeze](docs/reviews/p8-preflight-2026-11-14/), [results](docs/reviews/p8-results-audit-2026-11-14/RESULTS_AUDIT.md) · [Delegation record](docs/reviews/p8-results-2026-11-14/DELEGATION.md)

## Resource usage

| | Used | Limit |
|---|---:|---:|
| Active wall time, whole overnight task | about 1 h 45 min | 8 h |
| Training (60 cells, 4 workers) | 393 s | 5,400 s |
| Evaluation and traces | 106 s | 1,800 s |
| Simulation | 74 s | 5,400 s |
| Analysis | 1 s | 600 s |
| Peak RSS per worker | 0.47 GiB | 2 GiB |
| Peak aggregate RSS | 1.93 GB | 8 GiB |
| Cloud, paid APIs, downloads, SSD work, capacity changes | none | none allowed |

Local only, not published: P8 checkpoints and traces (about 460 MB under `experiments/P8*`), a local backup branch `backup/p8-before-single-line-rewrite`.

## Recommendation for the next phase

Do not proceed toward learned topology on this evidence, and do not read the lower simulated misses as progress toward the storage goal. If the line continues, the next question is **utilization before locality**: the memory uses about 3% of its slots, and a locality objective can only be tested on a memory that is using its capacity, with an explicit mechanism that keeps it so and cache settings scaled to the working set. That would be a new specification. Nothing of the kind has been started.

## Decisions that need you

1. Accept the C06–C10 classes as registered despite the stop-rule deviation (caveat 2)?
2. Complete the five missing simulations? It needs a repaired null construction for fully collapsed cells and cannot change any class.
3. Direction: stop this line at this scale, or authorize a new specification (utilization-preserving locality training)?
4. ADR-0012 governance is still pending.
5. Merge PR #5 or leave it as a draft record.
