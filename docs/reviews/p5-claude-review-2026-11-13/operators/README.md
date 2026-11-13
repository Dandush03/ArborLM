# EXPLORATORY — synthetic tensors, single machine, not preregistered, not evidence for any speedup

Operator-level inspection of the EXISTING `Memory.lookup` / `tree_candidates` / `stable_top` (src/arborlm/pilot_model.py), written by the implementer role (claude-sonnet-5-5). It is diagnosis to inform a future preregistration. Status: **not Astra validated, not independently reviewed, not human approved.** All numbers below are **measured** (this machine, synthetic inputs) unless labelled otherwise. No optimized, cached, reordered or alternative retrieval implementation was written, run or timed. No checkpoint, dataset or registered seed was used.

## What was run

Command (repo root):

```
uv run --locked --extra pilot python docs/reviews/p5-claude-review-2026-11-13/operators/operator_profile.py
uv run --locked python -I docs/reviews/p5-claude-review-2026-11-13/operators/retained_summary.py   # reads retained P5 JSON only
python3 docs/reviews/p5-claude-review-2026-11-13/operators/make_readme.py                           # tables.md only
```

- Weights: `Memory(variant, 9001).eval()` (fresh random-normal init, std 0.02). Queries: `F.normalize(torch.randn(N,16))` from a CPU generator seeded 9001 (the N=64 queries are the first 64 of the N=512 queries). Seed 9001 is not a registered project seed. No other seeds.
- Protocol mirror: CPU, float32, `torch.set_num_threads(1)`, `set_num_interop_threads(1)`, `torch.inference_mode()`, `time.perf_counter_ns`, GC disabled inside timed blocks (collected between rounds), 2 warmups + 10 timed calls per round, 8 rounds, median and p10/p90 over 80 samples. Each round interleaves all end-to-end entries and all stages (fixed order flat, fixed_tree, learned_tree; end-to-end first, then stages in code order). Results are freed after `t1` (deallocation is outside the timed region, for the end-to-end and for every stage).
- Stage decomposition: each stage re-executes one operation from the original code with real intermediate tensors (computed once, by the same ops, from the previous stage) as inputs. `stable_top` is unrolled line by line (including the `ids is not None` branch and the no-ties fast path; the tie fallback is asserted not to trigger on the synthetic data). Bitwise equality (`torch.equal`) of weights, selected, candidate_ids, branch_ids and route_scores to `Memory.lookup` was asserted for every variant and N (all True).
- Bytes materialized = numel x itemsize of each stage's output tensors that own new storage (views count 0). Internal temporaries of an op (e.g. norm tensor inside `F.normalize`, transposes) are NOT counted, so allocation volume is a lower bound.
- Profiler cross-check: `torch.profiler` CPU, 20 calls (3 untimed warmups) of the unmodified lookup for flat and fixed_tree at N=512 and N=64: `profiler_flat_N512.txt`, `profiler_fixed_tree_N512.txt`, `profiler_flat_N64.txt`, `profiler_fixed_tree_N64.txt`, sorted by self CPU time. Profiler overhead inflates small ops.

Environment: macOS-27.2.1-arm64-arm-64bit; CPU Apple M5 Max; torch 2.8.0; Python 3.12.14; threads 1/1 (intra/inter); timer `mach_absolute_time()`, resolution 41.7 ns; an empty-lambda timed call costs a median 42 ns. Full `torch.__config__.show()` and parallel info are in `operator_profile.json` under `environment`.

## End-to-end and stage-sum (measured)

| N | variant | end-to-end median us | p10-p90 us | stage sum us | sum/e2e | bitwise equal |
|---|---|---:|---|---:|---:|---|
| 512 | flat | 2,377.7 | 2,267.7-2,561.6 | 2,312.4 | 0.973 | True |
| 512 | fixed_tree | 6,529.3 | 6,231.2-6,802.0 | 6,190.1 | 0.948 | True |
| 512 | learned_tree | 6,469.9 | 6,256.1-6,867.5 | 6,167.5 | 0.953 | True |
| 64 | flat | 294.1 | 277.2-330.1 | 291.8 | 0.992 | True |
| 64 | fixed_tree | 669.7 | 633.1-818.8 | 626.1 | 0.935 | True |
| 64 | learned_tree | 671.6 | 638.7-735.6 | 619.4 | 0.922 | True |

## Tree path, N = 512 (fixed_tree; learned_tree is in `operator_profile.json` and `tables.md` and agrees within noise)

| Stage | median us | p10-p90 us | share of stage-sum | bytes materialized (outputs only) | output shape / dtype |
|---|---:|---|---:|---:|---|
| T1 normalize(router) | 2.5 | 2.3-3.0 | 0.0% | 1,024 | [16, 16] float32 |
| T2 route q@rn.T / TEMP | 4.1 | 3.9-4.5 | 0.1% | 32,768 | [512, 16] float32 |
| T3 topk(3) | 29.2 | 27.0-34.4 | 0.5% | 18,432 | [512, 3] float32; [512, 3] int64 |
| T3 tie-safety check | 4.4 | 4.1-5.4 | 0.1% | 512 | [512] bool; bool |
| T3 slice+contiguous | 1.0 | 1.0-1.2 | 0.0% | 8,192 | [512, 2] int64 |
| T3 final gather scores | 1.0 | 0.9-1.0 | 0.0% | 4,096 | [512, 2] float32 |
| T4 candidate index build | 64.1 | 62.0-76.4 | 1.0% | 2,097,152 | [512, 512] int64 |
| T5 keys[indices] gather | 1,950.4 | 1,879.3-2,250.3 | 31.5% | 16,777,216 | [512, 512, 16] float32 |
| T6 normalize(gathered) | 893.6 | 827.8-1,125.3 | 14.4% | 16,777,216 | [512, 512, 16] float32 |
| T7 bmm + squeeze + / TEMP | 1,103.5 | 1,063.8-1,312.3 | 17.8% | 2,097,152 | [512, 512, 1] float32; [512, 512] float32 |
| T8a routes.log_softmax | 6.5 | 6.0-8.8 | 0.1% | 32,768 | [512, 16] float32 |
| T8b prior gather(branch_ids) | 1.0 | 0.9-1.4 | 0.0% | 4,096 | [512, 2] float32 |
| T8c prior.repeat_interleave | 10.1 | 9.5-11.5 | 0.2% | 1,048,576 | [512, 512] float32 |
| T8d scores + prior | 24.8 | 24.0-27.3 | 0.4% | 1,048,576 | [512, 512] float32 |
| T9 ids.argsort | 388.8 | 364.4-428.2 | 6.3% | 2,097,152 | [512, 512] int64 |
| T9 gather scores by_id | 83.7 | 76.1-99.0 | 1.4% | 1,048,576 | [512, 512] float32 |
| T9 gather ids by_id | 88.8 | 80.1-110.0 | 1.4% | 2,097,152 | [512, 512] int64 |
| T9 topk(9) | 1,519.5 | 1,368.8-1,728.4 | 24.5% | 55,296 | [512, 9] float32; [512, 9] int64 |
| T9 tie-safety check | 6.0 | 5.5-8.3 | 0.1% | 512 | [512] bool; bool |
| T9 slice+contiguous | 1.4 | 1.2-2.1 | 0.0% | 32,768 | [512, 8] int64 |
| T9 final gather scores | 2.8 | 2.6-3.4 | 0.0% | 16,384 | [512, 8] float32 |
| T9 final gather ids | 2.9 | 2.8-3.7 | 0.0% | 32,768 | [512, 8] int64 |
| **stage-median sum** | **6,190.1** | | 100% | 45,328,384 | |
| **end-to-end Memory.lookup** | **6,529.3** | 6,231.2-6,802.0 | | | |
| stage sum / end-to-end | 0.948 | | | | |

Grouped:

| Group | summed median us | share | bytes materialized |
|---|---:|---:|---:|
| final stable_top(scores, 8, indices) | 2,094.0 | 33.8% | 5,380,608 |
| gather keys | 1,950.4 | 31.5% | 16,777,216 |
| bmm+div | 1,103.5 | 17.8% | 2,097,152 |
| normalize gathered | 893.6 | 14.4% | 16,777,216 |
| candidate indices | 64.1 | 1.0% | 2,097,152 |
| prior | 42.4 | 0.7% | 2,134,016 |
| branch stable_top(routes, 2) | 35.6 | 0.6% | 31,232 |
| route matmul+div | 4.1 | 0.1% | 32,768 |
| router normalize | 2.5 | 0.0% | 1,024 |

## Flat path, N = 512

| Stage | median us | p10-p90 us | share of stage-sum | bytes materialized (outputs only) | output shape / dtype |
|---|---:|---|---:|---:|---|
| F1 normalize(keys) | 16.6 | 14.8-22.8 | 0.7% | 262,144 | [4096, 16] float32 |
| F2 q@nk.T / TEMP | 320.8 | 290.3-530.7 | 13.9% | 8,388,608 | [512, 4096] float32 |
| F3 topk(9) | 1,964.9 | 1,854.5-2,190.1 | 85.0% | 55,296 | [512, 9] float32; [512, 9] int64 |
| F3 tie-safety check | 6.0 | 5.4-6.8 | 0.3% | 512 | [512] bool; bool |
| F3 slice+contiguous | 1.4 | 1.2-1.5 | 0.1% | 32,768 | [512, 8] int64 |
| F3 final gather scores | 2.8 | 2.6-3.0 | 0.1% | 16,384 | [512, 8] float32 |
| **stage-median sum** | **2,312.4** | | 100% | 8,755,712 | |
| **end-to-end Memory.lookup** | **2,377.7** | 2,267.7-2,561.6 | | | |
| stage sum / end-to-end | 0.973 | | | | |

## N = 64 (secondary)

Tree (fixed_tree):

| Stage | median us | p10-p90 us | share of stage-sum | bytes materialized (outputs only) | output shape / dtype |
|---|---:|---|---:|---:|---|
| T1 normalize(router) | 2.4 | 2.2-2.7 | 0.4% | 1,024 | [16, 16] float32 |
| T2 route q@rn.T / TEMP | 2.5 | 2.3-2.9 | 0.4% | 4,096 | [64, 16] float32 |
| T3 topk(3) | 3.9 | 3.6-5.0 | 0.6% | 2,304 | [64, 3] float32; [64, 3] int64 |
| T3 tie-safety check | 2.6 | 2.4-3.0 | 0.4% | 64 | [64] bool; bool |
| T3 slice+contiguous | 0.8 | 0.8-0.9 | 0.1% | 1,024 | [64, 2] int64 |
| T3 final gather scores | 0.5 | 0.5-0.5 | 0.1% | 512 | [64, 2] float32 |
| T4 candidate index build | 9.8 | 9.4-11.0 | 1.6% | 262,144 | [64, 512] int64 |
| T5 keys[indices] gather | 238.1 | 226.2-255.6 | 38.0% | 2,097,152 | [64, 512, 16] float32 |
| T6 normalize(gathered) | 110.7 | 103.1-125.1 | 17.7% | 2,097,152 | [64, 512, 16] float32 |
| T7 bmm + squeeze + / TEMP | 115.1 | 111.5-121.0 | 18.4% | 262,144 | [64, 512, 1] float32; [64, 512] float32 |
| T8a routes.log_softmax | 1.1 | 1.0-1.4 | 0.2% | 4,096 | [64, 16] float32 |
| T8b prior gather(branch_ids) | 0.5 | 0.5-0.6 | 0.1% | 512 | [64, 2] float32 |
| T8c prior.repeat_interleave | 3.1 | 2.7-3.5 | 0.5% | 131,072 | [64, 512] float32 |
| T8d scores + prior | 3.3 | 3.2-3.6 | 0.5% | 131,072 | [64, 512] float32 |
| T9 ids.argsort | 47.7 | 44.9-49.5 | 7.6% | 262,144 | [64, 512] int64 |
| T9 gather scores by_id | 10.1 | 9.3-12.4 | 1.6% | 131,072 | [64, 512] float32 |
| T9 gather ids by_id | 11.0 | 9.6-12.8 | 1.8% | 262,144 | [64, 512] int64 |
| T9 topk(9) | 58.0 | 46.3-83.9 | 9.3% | 6,912 | [64, 9] float32; [64, 9] int64 |
| T9 tie-safety check | 2.9 | 2.6-3.3 | 0.5% | 64 | [64] bool; bool |
| T9 slice+contiguous | 0.9 | 0.8-1.0 | 0.1% | 4,096 | [64, 8] int64 |
| T9 final gather scores | 0.6 | 0.5-0.7 | 0.1% | 2,048 | [64, 8] float32 |
| T9 final gather ids | 0.6 | 0.5-0.7 | 0.1% | 4,096 | [64, 8] int64 |
| **stage-median sum** | **626.1** | | 100% | 5,666,944 | |
| **end-to-end Memory.lookup** | **669.7** | 633.1-818.8 | | | |
| stage sum / end-to-end | 0.935 | | | | |

Flat:

| Stage | median us | p10-p90 us | share of stage-sum | bytes materialized (outputs only) | output shape / dtype |
|---|---:|---|---:|---:|---|
| F1 normalize(keys) | 15.6 | 14.4-17.2 | 5.4% | 262,144 | [4096, 16] float32 |
| F2 q@nk.T / TEMP | 46.5 | 43.8-47.5 | 15.9% | 1,048,576 | [64, 4096] float32 |
| F3 topk(9) | 225.5 | 214.0-232.8 | 77.3% | 6,912 | [64, 9] float32; [64, 9] int64 |
| F3 tie-safety check | 2.8 | 2.6-3.5 | 1.0% | 64 | [64] bool; bool |
| F3 slice+contiguous | 0.8 | 0.8-1.0 | 0.3% | 4,096 | [64, 8] int64 |
| F3 final gather scores | 0.6 | 0.5-0.7 | 0.2% | 2,048 | [64, 8] float32 |
| **stage-median sum** | **291.8** | | 100% | 1,323,840 | |
| **end-to-end Memory.lookup** | **294.1** | 277.2-330.1 | | | |
| stage sum / end-to-end | 0.992 | | | | |

## Comparison with the retained P5 records

`p5_retained_timing_summary.json` is derived only from `results/p5-2026-11-13/timing/*/result.json` (36 workers found; 27 contain memory variants) with no new measurement. **These are not the same measurement as the synthetic one**: P5 used its own weights, queries (from model hidden states), process and workers; this script uses fresh random weights, random unit queries, one process. Only the order of magnitude and the ratios are comparable.

| workload | variant | P5 retained lookup_score_select: median across 27 workers of median_ns (us) [worker min-max] | synthetic end-to-end median (us) | synthetic / P5 |
|---|---|---:|---:|---:|
| batch 8 x ctx 64 (512 queries) | flat | 2,323.4 [2,148.3-2,461.5] | 2,377.7 | 1.023 |
| batch 8 x ctx 64 (512 queries) | fixed_tree | 6,209.3 [5,807.0-6,675.1] | 6,529.3 | 1.052 |
| batch 8 x ctx 64 (512 queries) | learned_tree | 6,195.6 [5,628.5-6,781.8] | 6,469.9 | 1.044 |
| batch 1 x ctx 64 (64 queries) | flat | 312.7 [297.6-333.5] | 294.1 | 0.941 |
| batch 1 x ctx 64 (64 queries) | fixed_tree | 797.7 [753.0-870.9] | 669.7 | 0.840 |
| batch 1 x ctx 64 (64 queries) | learned_tree | 800.1 [740.3-862.3] | 671.6 | 0.839 |

| N | synthetic fixed_tree/flat | retained P5 fixed_tree/flat |
|---|---:|---:|
| 512 | 2.75 | 2.67 |
| 64 | 2.28 | 2.55 |

## Observations

(Facts read off the tables above; single machine, single process, 80 samples each.)

1. The synthetic unmodified lookup reproduces the P5 pattern at N=512: fixed_tree is 2.75x flat end-to-end (P5 retained: 2.67x). At N=64 the synthetic ratio is 2.28x versus 2.55x retained; the synthetic tree is 16% faster than the retained P5 tree median at N=64, a difference not explained here.
2. Tree stage-sum at N=512 is 6.19 ms; four groups account for about 97%: the `keys[indices]` gather 31.5% (1.95 ms), the final `stable_top` 33.8% (of which `topk(9)` 24.5% and `ids.argsort` 6.3%), the `bmm`+division 17.8%, and `F.normalize` of the gathered tensor 14.4%.
3. The router stages (normalize, route matmul, branch `stable_top(.,2)`) total about 0.04 ms (0.7% of the tree stage-sum); the prior stages about 0.04 ms (0.7%).
4. Flat stage-sum at N=512 is 2.31 ms; `topk(9)` over [512,4096] is 85% of it (1.96 ms), the score matmul+division 13.9% (0.32 ms), key normalization 0.7%.
5. `topk(9)` on the tree's [512,512] scores (1.52 ms) costs 77% of flat's `topk(9)` on [512,4096] (1.96 ms) although each row is 8x shorter. `topk(3)` on [512,16] (branch selection) costs 29 us.
6. The tree path materializes about 45.3 MB of stage outputs per call at N=512 (two [512,512,16] float32 tensors of 16.8 MB each, plus int64 [512,512] index tensors of 2.1 MB each in three stages) versus about 8.8 MB for flat (dominated by the [512,4096] float32 score matrix, 8.4 MB). Internal temporaries are not included.
7. Sum of stage medians vs end-to-end: tree 0.948 (N=512) / 0.935 (N=64), flat 0.973 / 0.992. The stage sum is slightly below the end-to-end median in every case; the unattributed 5-8% of the tree end-to-end is not isolated by this design (see Hypotheses).
8. The profiler cross-check agrees in ranking with the manual stages: tree self-CPU is led by `aten::index` (29.5%), `aten::topk` (25.5%), `aten::bmm` (13.4%), `aten::linalg_vector_norm` (7.8%), `aten::div` (5.2%), `aten::sort` (5.1%); flat is 83.5% `aten::topk`, 7.3% `aten::div`, 7.1% `aten::mm`. The profiler also lists ~30,700 `aten::select`, ~31,100 `aten::as_strided` and ~10,300 `aten::resolve_conj` events over the 20 tree calls (about 1,540 / 1,560 / 520 per call; 3 and 1 per query), and 4.4% self time in `aten::select` (profiler overhead likely inflates this).
9. Decomposition output is bitwise identical to `Memory.lookup` for both flat and both tree variants at both N. No tie fallback triggered on the synthetic queries.

## Hypotheses (not established by these measurements)

- H1. The gather `keys[indices]` ([512,512,16] from a 4096x16 table) is costly because it is an advanced-indexing copy of 8.4M elements, i.e. memory-bound/index-op overhead, not arithmetic. These measurements show its time and bytes but cannot separate copy bandwidth from indexing overhead.
- H2. `topk` cost on CPU may be dominated by per-row setup or partial-sort behaviour that does not shrink in proportion to row length (observation 5); the data show a sub-linear relation across two row lengths only, which is insufficient to establish the mechanism.
- H3. The ~1,540 `aten::select` events per tree call (3 per query) may originate inside `topk` or `index` row loops; the profiler table cannot attribute them to a caller without a stack-attributed profile, which was not collected.
- H4. The 5-8% stage-sum deficit may reflect warm caches when a stage re-reads the same input repeatedly in isolation (stage inputs stay resident), versus a cold pass through freshly allocated 16.8 MB tensors in the end-to-end call; allocator behaviour and the cost of the `Lookup` dataclass construction and allocation of temporaries inside ops are other candidates. Not tested.
- H5. The tree's lower arithmetic work (512 + 16 dot products per query vs 4,096) is outweighed by the cost of materializing and traversing per-query candidate tensors; only an operation-level experiment under preregistration could test this, and none was run here.
- H6. The 16% difference to retained P5 at N=64 may come from input distribution (real hidden-state queries vs random), allocator/cache state across the P5 worker schedule, or process-level effects. Not investigated.

## Limits

Single machine and process, one weight draw, one query draw, no repeats of the whole script (run-to-run variance across invocations is not measured: the script was executed twice during development, the first run before fixing a double-`bmm` in the T7 stage lambda; the reported run is the second). Stage inputs are cached/warm by construction. Stages under about 5 us are near the timer-call overhead (42 ns) and should be read as upper-bound magnitudes.

## Files

- `operator_profile.py`, `operator_profile.json`, `profiler_*.txt`
- `retained_summary.py`, `p5_retained_timing_summary.json`
- `make_readme.py`, `tables.md` (generated tables), this README

## PENDING LEAD REVIEW

- Whether a future preregistration should include any operator-level or alternative-implementation timing, and on what weights/queries; this document makes no recommendation on which optimization (if any) to test.
- Whether the 16% N=64 gap versus retained P5 warrants investigation before relying on synthetic proxies.
