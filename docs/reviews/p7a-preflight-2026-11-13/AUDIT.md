# P7-A pre-freeze audit (ADR-0013 implementation)

- Date: 2026-11-13. Auditor role: Claude Opus 5.5 (`claude-opus-5-5`).
- Branch `claude/p7a-storage-locality-proposal`, HEAD `3617fc6`. The code under audit is untracked: `src/arborlm/p7a_{core,sim,trace,stage,analysis,study}.py` and `tests/test_p7a_{sim,trace,analysis,study}.py`. Source hashes as recorded by the study's own dry-run manifest (`outputs/dryrun_manifests/trace_stage_manifest.json`): analysis `7da8ecf5…`, core `73635abc…`, sim `84ea0d90…`, stage `cb683e6e…`, study `ded303a4…`, trace `396c956e…`. Spec ADR-0013 sha256 `5a239db5…`.
- **This is independent engineering and mathematical evidence. It is not Astra validation and not human approval.** Astra review: NOT_PERFORMED.
- Nothing here ran a model on a real checkpoint, generated a real trace, simulated a real trace or ran a registered stage. Real-data inputs used: only the 81 published P5 compact records (`results/p5-2026-11-13/<cell>/result.json`, `final.retrieval.selected_slot_counts`). No page or cache metric was computed on them (deliberately, so the null choice below is not informed by outcome-adjacent numbers).
- Environment: macOS 27.2 arm64 (Darwin 27.2.0); project Python 3.12.14 via `uv run --locked`; torch 2.8.0; system `python3` 3.15.1 for the standard-library scripts.

## Counts

BLOCKER 1 · MAJOR 3 · MINOR 9 · NOTE 9.

## Commands run and results

| Command (repo root) | Result | Output |
|---|---|---|
| `uv run --locked --extra pilot pytest -q tests/test_p7a_sim.py tests/test_p7a_trace.py tests/test_p7a_analysis.py tests/test_p7a_study.py` | 75 passed, 32 s | `outputs/pytest_p7a.txt` |
| `uv run --locked ruff check src/arborlm/p7a_*.py tests/test_p7a_*.py`; `uv run --locked mypy src/arborlm` | clean; no issues (64 files) | (console) |
| `uv run --locked --extra pilot python -m arborlm.p7a_study budget` | flat 16.55 s, fixed 14.03 s per checkpoint; projected 1,204 s; margin 2.99 | `outputs/budget.txt` |
| `uv run --locked --extra pilot python -m arborlm.p7a_study dry-run` | trace/simulate/analyze 0; outcomes INCOMPLETE (expected, 6 checkpoints); experiments/results unchanged | `outputs/dry_run.txt` |
| `uv run --locked --extra pilot python docs/reviews/p7a-preflight-2026-11-13/check_fm_distortion.py` | see Q4 | `outputs/fm_distortion.{txt,json}` |
| `… check_fm_chunking.py` | chunked (2048 rows) == one call per query, full size, 2 cells x 2 seeds | `outputs/fm_chunking.txt` |
| `python3 docs/reviews/p7a-preflight-2026-11-13/check_exact_null.py` | exact count-preserving null feasible for 81/81 | `outputs/exact_null.out.txt`, `outputs/exact_null.json` |
| `python3 docs/reviews/p7a-preflight-2026-11-13/check_tie_sensitivity.py` | see MINOR-1 | `outputs/tie_sensitivity.{txt,json}` |
| `uv run --locked --extra pilot python docs/reviews/p7a-preflight-2026-11-13/harness_synthetic.py <scratch>/p7a2` | synthetic stage pipeline + 4 full-size synthetic checkpoints | `outputs/harness_run2.txt`, `outputs/harness_paths.json`, `outputs/dryrun_manifests/` |
| `python3 -I docs/reviews/p7a-preflight-2026-11-13/independent_sim.py …` (see Part B) | AGREE on 6 + 4 checkpoints; negative controls DIFFER | `outputs/indep_vs_study_*.txt/json`, `outputs/negative_control_*.txt` |
| `uv run --locked --extra pilot python docs/reviews/p7a-preflight-2026-11-13/check_analyze_source_guard.py <scratch>/guard` | analyze completes with changed sources | `outputs/analyze_source_guard.txt` |
| `uv run --locked --extra pilot python docs/reviews/p7a-preflight-2026-11-13/check_thread_independence.py` | FM, order permutation and bootstrap indices identical at 6 threads and 1 thread | `outputs/thread_independence.txt` |

**Failed attempt kept.** The first harness run failed: its trace stage ended `failed: a version-controlled file changed while the stage ran`, because my concurrent background job created `outputs/fm_distortion.txt` inside the repository during the stage (`outputs/harness_run_attempt1_FAILED_concurrent_untracked_write.txt`, `outputs/harness_attempt1_trace_stage_result.json`). This was my error, not a study defect. It does show how sensitive the end-of-stage check is (MINOR-5). The rerun with no concurrent writes succeeded.

---

## BLOCKER

### B1 — The registered frequency-matched generator cannot meet §9's "reproduce target frequencies", and its distortion leans toward a STRUCTURAL ADVANTAGE (spec conflict: PENDING LEAD REVIEW)

Evidence: `p7a_core.py:354-386` follows clarification 2 literally (per-query `torch.multinomial(counts, 8, replacement=False)`; I checked that 2,048-row chunking equals one call per query at full size, `outputs/fm_chunking.txt`). §9 also requires "the frequency-matched generator checked to reproduce target frequencies". Weighted sampling without replacement (successive / Plackett-Luce sampling) does not keep marginals: a slot can appear at most once per query, so hot slots are under-drawn and cold slots over-drawn. The implementer's test (`tests/test_p7a_sim.py:320-340`) checks only that the frequency ordering is monotone (line 329) and that uniform weights give uniform output. Neither case can detect the distortion, so §9 is effectively marked as checked when it is not.

Measured on the 81 published histograms with the exact registered procedure, mean of 3 replicates per cell (`outputs/fm_distortion.txt`; per cell in `.json`):

| | flat | fixed_tree | learned_tree |
|---|---:|---:|---:|
| top-1 share, target → realized | 0.0293 → 0.0273 | 0.0408 → 0.0369 | 0.0432 → 0.0391 |
| top-8 share, target → realized | 0.1986 → 0.1887 | 0.2480 → 0.2333 | 0.2627 → 0.2468 |
| top-8 realized/target (min–max) | 0.950 (0.938–0.964) | 0.943 (0.921–0.958) | 0.941 (0.920–0.965) |
| top-32 share, target → realized | 0.508 → 0.496 | 0.620 → 0.605 | 0.660 → 0.644 |
| effective slots exp(H), target → realized | 132.3 → 135.8 | 96.2 → 100.0 | 83.0 → 86.3 |
| effective slots realized/target (min–max) | 1.027 (1.018–1.043) | 1.041 (1.025–1.087) | 1.041 (1.019–1.066) |
| total variation distance (min–max) | 0.017 (0.014–0.021) | 0.021 (0.016–0.036) | 0.021 (0.015–0.029) |

The distortion is architecture-dependent: the more concentrated trees are flattened more. The null shrinks the concentration gap the CONC criterion is meant to reproduce. The tree/flat effective-slot ratio is 0.727 in the target and 0.736 in the realized stream (fixed), and 0.627 against 0.635 (learned). The frequency-matched tree stream therefore looks somewhat less concentrated than the tree really is, relative to flat. That pushes the frequency-matched tree/flat miss ratio upward, which makes CONC_K ("tree ≤ 0.80 × flat") less likely to hold and STRUCTURAL ADVANTAGE more likely. The aggregate effect is about 1% of the concentration ratio. It could change CONC_K's verdict only if the ratio of means lands within roughly a percent or two of 0.80, or if the 22/27 or 8/9 counts sit at their boundary. Per cell it is larger (fixed tree up to +8.7% effective slots), so individual pair comparisons are more exposed than the mean. I did not compute any m on these histograms, so I cannot say how close the study will be to the threshold. The direction, though, is the one that favours a hierarchy claim. The distortion also contaminates the registered decomposition: the "frequency-matched → order-shuffled" step (labelled co-selection) also contains the effect of restoring the true marginals.

**Exact count-preserving null.** One exists for every checkpoint. A 0/1 slot-by-query incidence with row sums c_i and 32,768 columns of sum 8 exists iff max c_i ≤ 32,768 (Gale-Ryser with a uniform side of 8: for k < 8 the k largest sum to at most kQ, and the total is exactly 8Q). The largest published count is 18,460 (a fixed tree), so the condition holds for 81/81. `check_exact_null.py` builds one per cell in about 0.06 s with the standard library: shuffle the multiset of 262,144 occurrences with `random.Random(seed)`, deal 8 per query, then repair. For q ascending, while query q holds a duplicate x (take the later position), scan r = q+1, q+2, … cyclically for the first query that lacks x and has a slot not in q (lowest position), and swap. Every slot count is preserved exactly and each swap removes one duplicate. This took 9.6k / 13.1k / 14.3k swaps on average for flat / fixed / learned. **Required addition before any use:** finish with a seeded permutation of the 32,768 queries, because the cyclic repair puts moved occurrences in nearby queries and that would create artificial temporal reuse. My feasibility script omits this step and is not a registration candidate as written.

**Recommendation (PENDING LEAD REVIEW; not implemented in study code):** register the exact count-preserving null as the frequency-matched stream, keeping three replicates with seeds s·1000 + cell_index for the shuffle and the final permutation, and add a §9 test that marginals are reproduced exactly. If the lead keeps clarification 2 instead, §9 must be amended to state the tolerance and the known direction of bias, and the per-cell distortion must be reported beside CONC_K. Either way a recorded decision is needed before the freeze, because the current §9 requirement and clarification 2 cannot both hold (AGENTS.md: "If documents disagree, stop and request a recorded … decision").

**My own earlier mistake.** My revision-1 review (B2 fix, `irm_null_lru.py`) proposed exactly this successive weighted sampling without noting that it does not preserve marginals. The defect originates partly in my recommendation.

---

## MAJOR

### M1 — The analyze stage does not refuse when sources or spec differ from the simulate stage it consumes

`p7a_study.py:454-486` (`check_linkage`) compares the trace manifest with the simulate manifest and each record with the simulate manifest. Nothing compares the **current** `core.source_hashes()` / `spec_sha256()` with the simulate run's values before analysis. `run_analyze` (`:489-523`) then opens a stage that records whatever is current, and the end-of-stage check (`p7a_stage.py:165-175`) only compares the analyze stage against itself. Demonstrated: with `p7a_analysis.py`'s hash changed after simulate, analyze completes with status `completed` (`outputs/analyze_source_guard.txt`). The criteria code could therefore be edited after the miss counts exist without anything stopping the run; the evidence would remain only as a hash difference across two manifests.
*Fix:* in `run_analyze`, before `open_stage`, refuse unless `core.source_hashes() == sim_manifest["p7a_source_sha256"]`, `core.spec_sha256() == sim_manifest["spec_sha256"]` and `git_head` matches. Add a test equivalent to my demonstration.

### M2 — The clarification-7 stop ("any difference in a miss count stops the study before analysis") is not enforced

`run_analyze` (`p7a_study.py:489-552`) has no input for, or check of, the independent simulator's verdict. Analysis can be run with no independent comparison, or after a failed one. *Fix:* require `--independent-check <path to independent_sim summary JSON>`, and refuse unless `verdict == "AGREE"`, its `selection` equals the clarification-7 selection, every listed label's `sim-workers` path belongs to the simulate run being analysed, and `tie_rule == "asc"` (or the registered rule). Record the file's sha256 in the analyze linkage. If the lead prefers a procedural control, record that decision.

### M3 — CONC_K uses the actual stream's non-degeneracy only; a degenerate frequency-matched stream can turn into STRUCTURAL ADVANTAGE, and the UNSPECIFIED branch is unreachable

`p7a_analysis.py:199-242`: non-degeneracy is computed on the actual stream (`:215`), and CONC is HOLDS/FAILS whenever the actual stream is non-degenerate (`:236-241`). No floor is checked on the frequency-matched stream. As a reading this is coherent: §7 checks non-degeneracy "per setting", and the primary setting is defined to include "actual evaluation stream". The consequence is that `outcome_for(HOLDS, DEGENERATE)` → UNSPECIFIED (`:110-123`) can never happen: CONC is DEGENERATE only when LRU is DEGENERATE. The docstring and `tests/test_p7a_analysis.py:105` describe a path the pipeline cannot reach.
*What could go wrong:* if both frequency-matched means are 0 or near the floor, the mean clause passes (0 ≤ 0) and the count clauses fail on ties, so CONC FAILS. With LRU HOLDS the result is **STRUCTURAL ADVANTAGE**, a positive claim produced by a null that cannot discriminate. This is unlikely in the primary setting (independent draws generally miss more than the actual stream, and B1's flattening adds misses), but it is a false-positive path. *Fix (engineering, rule PENDING LEAD REVIEW):* compute and report the floors on the frequency-matched stream as well. If the frequency-matched flat mean is below 0.05, set CONC = DEGENERATE and the outcome to UNSPECIFIED, never STRUCTURAL. If only the tree's frequency-matched mean is below 0.01 while flat's is at or above 0.05, keep CONC HOLDS (concentration alone reproduces the advantage). Add a test for each case.

---

## MINOR (each with fix)

1. **LRU tie rule (open in the spec; PENDING LEAD REVIEW).** The spec leaves it open: "least recently used pages not used by the current query" is a *set* when a new query evicts only part of an older query's pages, and §5's "order within a query does not matter" is not true for counts. The implementer evicts the lowest page of the oldest query first (`p7a_sim.py:10-14, 149-178`). Under L-FREQ that is the calibration-*hottest* page, a perverse choice. Synthetic sensitivity (`outputs/tie_sensitivity.txt`, Zipf streams with effective slots ~148 and ~94): at R=2, C=32, ascending gives 2.6–2.7% more warm capacity misses than descending, and the tree/flat ratio moves by 0.001–0.002. The largest shift is at R=2, C=8 (0.8324 against 0.8059). On the harness traces the direction differs between checkpoints (`outputs/negative_control_tie_desc.txt`: one +0.1%, one −0.4%). So it is small, not consistently architecture-favouring, and not zero. *Fix:* the lead records the rule (ascending, or a layout-independent seeded page priority) before the freeze, and the descending variant is reported descriptively at the primary setting.
2. **Decomposition is per kind, not per checkpoint.** §5 registers it "per checkpoint and metric". `p7a_analysis.py:387-438` reports only means over cells. *Fix:* emit per-checkpoint rows (the records already contain the inputs). The uniform step for cache misses is null, which the implementer correctly flags (`:435-437`). The ADR itself conflicts here: its null table says "each is run through the same simulator", while §10 enumerates no uniform stream (NOTE for the lead).
3. **Descriptive outputs missing from the analysis:** cold misses from an empty cache, cached read amplification (§5), the cumulative distinct-page curve and distinct pages per context are stored in the records but not tabulated (`p7a_analysis.py:337-472`). *Fix:* add tables. Nothing would need recomputing.
4. **Sim workers do not apply the registered environment** ("single thread, deterministic algorithms", §3). `_sim_worker` (`p7a_study.py:141-226`) never calls `configure_deterministic_cpu`. I checked that the frequency-matched draws, the order permutation and the bootstrap indices are bit-identical at 6 threads and at 1 thread on torch 2.8.0 (`outputs/thread_independence.txt`), so no result changes. *Fix:* call it anyway, or record the deviation.
5. **End-of-stage tracked-state check is both too wide and too narrow.** `tracked_state_sha256` (`p7a_stage.py:65-78`) hashes `git diff HEAD` plus untracked *file names*. Any new file anywhere in the repo during a stage fails the stage (this is what failed my attempt 1). Edits to the *content* of an untracked file outside results/experiments/data are not detected. *Fix:* write in the runbook that nothing may be created in the repository, including `docs/reviews/`, while a stage runs, and that the independent simulator's `--out` is written only between simulate and analyze. Optionally hash untracked file contents.
6. **Trace workers write a P6 label into their environment record.** `common.load_real_cell` calls `record_environment(run, family=FAMILY)` with P6's family (`p6_common.py:152`). Every real P7-A trace worker folder will therefore hold `environment.json` with `"storage_device_reason": "no storage experiment in P6E_RETRIEVAL_OPTIMIZATION"`. This is not a manifest (clarification 6 is satisfied by the manifests, which I checked in a dry run: `outputs/dryrun_manifests/`, no E0 or G0 text, `question_id` P7-A, ADR-0013 cited), but it is a mislabel in the evidence. *Fix:* the P7-A worker overwrites `environment.json` with `core.FAMILY`, or the mislabel is listed in `KNOWN_LIMITS`.
7. **The budget projection omits per-worker overhead.** `budget` (`p7a_study.py:658-704`) times in process. It leaves out worker start-up, importing torch, reading and hashing traces, re-reading the P5 record and the second `check_trace`, which is about 1–2 s per checkpoint, roughly +80–160 s. The margin is still about 2.6×. *Fix:* state it in the report, or time one supervised synthetic worker.
8. **The trace stage has no timing projection.** The trace cap is 900 s for 27 workers (each: P5/P4 provenance verification, 3 bitwise replays and 6 trace passes). P6-E's equivalence workers took 411 s in total (max 18.6 s) for comparable loading, so it probably fits, but this is unmeasured. A breach stops the study and needs `--supersede`. *Fix:* use `loader-smoke` timing (operator step; I did not run it) to project the trace stage before the registered run.
9. **Tests compare code with itself or miss claims.** See Q8. The concrete gaps to close before the freeze: the frequency-matched target-reproduction test (B1), the analyze source guard (M1), the frequency-matched degenerate path (M3), and the real-path slicing `train[2048:2560]` / `shape[0] == 4096` (`p7a_study.py:103-105`), which is untested apart from the loader-smoke route.

## NOTE

1. L-RAND direction: slot s sits at position `randperm(4096)[s]` (`p7a_core.py:281-285`). The spec is silent, but both directions are uniformly random. It is applied consistently to values, keys and the uniform reference (`p7a_sim.py:63-87, 288-310`).
2. Key cache with a query needing more pages than C (tree keys under L-RAND at 4 KiB need up to 64 pages) holds the whole query, then trims (`p7a_sim.py:13-14, 175`). This is not defined by the spec and carries no criterion. It is monotone in C as implemented.
3. The bootstrap interval uses the 26th and 975th of 1,000 sorted means (`p7a_sim.py:383-392`). This is a convention.
4. Trace workers do not re-check p7a source hashes themselves. The stage-end check covers this.
5. The stage environment says "no storage experiment in P7A_STORAGE_PAGE_LOCALITY" (`records.py:129`). For a simulation with no device this is literally true.
6. The robust rule considers only the L-FREQ actual-stream (R, C) grid as "other settings" (`p7a_analysis.py:287-296`). This is a reasonable reading of §7.
7. The chunked frequency-matched generator equals the literal per-query reading at full size (`outputs/fm_chunking.txt`).
8. Simulation RSS: the budget process peaked at 0.92 GB for two checkpoints including torch. The cap is 2 GiB per process tree.
9. A dry-run trace worker manifest was inspected for E0 text: `hypothesis_null_reason` is null, `question_id` is "P7-A", and `authorized_spec_reference` is ADR-0013. Template fields that are still present (`astra_*: NOT_PERFORMED`, `human_*: PENDING`, `schema_version` 1) are accurate.

---

## Per-question findings (Part A)

**Q1 Trace generation.** Correct as far as can be checked without real data.
- Order: `collect_trace` (`p7a_trace.py:51-73`) uses P5's batching (8 contexts) and `lookup.selected` rows are context-major (`pilot_model.py:145`: `reshape(-1, 16)` of [B, T, ·]). A fixture test compares row j·64+t against a single-context forward (`tests/test_p7a_trace.py:167-178`).
- Streams: evaluation = `source.panel` = P5 `validation.bytes` (ranks 2048–2559, `p5_data.py:59, 166`). Calibration = `train[2048:2560]` of the 4,096 ranked chunks (`p7a_study.py:103-105`). Training used ranks 0–2047 (`p5_config.py:58`, `p2_config.py:41`).
- Context: `batch[:, :-1]` exactly as in `p5_model.evaluate`.
- Selected IDs in returned (score) order and branch IDs in rank order come from `stable_top` (`pilot_model.py:74, 83`).
- Integrity checks (`p7a_core.py:217-265`): range, distinctness, distinct visited branches, membership, and exact P5 histogram and unique count. All are re-checked in the simulate worker.
- Bitwise NLL replay (`p7a_trace.py:103-110`). State digest and file hashes are taken before and after, with isolated RNG.

**Q2 Layouts.** Definitions, tie rules and permutation checks match §4 (`p7a_core.py:273-324`). L-FREQ and L-BFREQ use only calibration counts (also tested). L-BFREQ preserves branch membership (checked at build). L-RAND direction: NOTE 1.

**Q3 Cache model.** Per-query service, misses counted before admission, eviction only of pages not in the current query, C ≥ 8, warm boundary at query 16,384 by stream position, and first-touch over the whole stream are all correct (`p7a_sim.py:149-178`). The criterion metric is `misses_warm − first_touch_warm` (`p7a_analysis.py:135-145`). The invariants (`p7a_sim.py:204-231`) are right. Because eviction order is a capacity-independent recency stack, the "capacity misses never grow with C" invariant is a real stack property and not a tautology. Tie rule: MINOR-1. The spec leaves it open. My synthetic checks show it is small and not consistently architecture-favouring, but it is not neutral under L-FREQ (it evicts hot pages first).

**Q4 Streams.** Actual, order-shuffled (one randperm(32768), seed 91201) and context-shuffled (randperm(512), seed 91202) are correct and shared by every checkpoint (`p7a_core.py:328-346`). The frequency-matched stream follows clarification 2 exactly, but see B1 for the distortion, the numbers and the recommendation.

**Q5 Uniform closed form, branch locality, reuse, keys, bootstrap.** The closed form uses exact `Fraction` arithmetic and reproduces the ADR's 7.79 / 6.49 / 7.99 / 7.95 (tests) plus Monte Carlo. The tree reference is averaged over the trace's visited pairs, per layout. Branch locality, reuse (pooled, within and across contexts) and run lengths match §5 (`p7a_sim.py:91-145, 244-284`). My simulator reproduces reuse and distinct-per-context exactly. Flat keys are analytical (all key pages per query when C < pages, 0 after the first query otherwise). Tree keys are simulated in a separate cache. The bootstrap uses seed 91401 and 1,000 resamples over contexts.

**Q6 Analysis.** Floors 0.05 (flat) and 0.01 (tree) are applied to actual-stream m at the setting for LRU_K and CONC_K (M3). BR_K uses only the tree floor on L-RAND, which matches "non-degenerate for K under L-RAND". The ADV clauses are exact rationals: `≤ 0.80` with equality passing, strictly lower in ≥ 22 of 27, parent means strictly lower in ≥ 8 of 9 with parents = (backbone, order), ties counted as not lower, and ratios taken between means. The outcome table is correct for every reachable combination. "Robust" means another non-degenerate L-FREQ setting with R ≤ 8 where LRU holds and CONC fails. INCOMPLETE: any missing or incomplete record makes every criterion INCOMPLETE. A failed simulate stage also cannot be analysed at all (`require_completed`). The only paths I found from a degenerate input to a positive outcome are M3 (frequency-matched stream degenerate) and, in a weaker form, B1.

**Q7 Stage machinery.** Single-run and supersede guard are inherited from P6 and tested. Linkage: simulate records the trace run's manifest and result hashes, and analyze checks them, but not its own sources (M1). Manifests cite ADR-0013 with no E0 template text (inspected in a dry run). Source and spec are re-checked at stage end. The caps are trace 900 s, simulate min(3600, 4500 − trace), and analyze the remainder. Partial worker output is copied and unexecuted rows are kept. loader-smoke computes and writes nothing: this is tested with monkeypatched compute functions, and I read the code path. It writes only `environment.json` and the source snapshot into a temporary folder.

**Q8 Tests.** These test real claims: the hand-computed LRU traces (exactly 8, larger than the store, repeated pages, first-touch versus capacity, warm boundary), the closed form against the ADR numbers and Monte Carlo, ADV boundaries (22/21, 8/7, equality at 0.80, zero means), INCOMPLETE handling, trace-order equality against single-context forwards, integrity stops, and replay and hash stops.

These compare code with itself or are weak: the frequency-matched test (ordering only; B1); `test_shuffles_are_the_registered_permutations` and the L-RAND test (these restate the definition, which is acceptable); the outcome UNSPECIFIED test (M3, an unreachable state).

Untested: real-path calibration slicing and the 4,096-chunk check; the sim worker with a non-None P5 record (synthetic passes `None`); the analyze source guard (M1); the independent-check gate (M2); the frequency-matched degenerate CONC (M3); tie-rule sensitivity; the trace-stage time; the key-cache behaviour beyond one hand case.

Real-data paths that remain unexercised: `load_real_cell` inside a trace worker, the bitwise replay on real checkpoints (loader-smoke is the operator's pre-step), and the P5-record comparison inside the simulate worker.

---

## Part B — independent simulator

File: `docs/reviews/p7a-preflight-2026-11-13/independent_sim.py`. Standard library only; it imports nothing from arborlm, torch or numpy.

**Independence, stated honestly.** It was written from the ADR text, but after I had read `p7a_sim.py`/`p7a_core.py` for this audit. It uses a different data structure: a last-use dictionary plus a lazily invalidated min-heap, rather than an OrderedDict. Three choices the ADR leaves open were matched to the study so that a comparison is possible: the tie rule (ascending, with `--tie desc` available), the "slot → position = rank" reading of L-FREQ/L-BFREQ, and the record field names. It cannot reproduce L-RAND or the torch-generated streams, so those are not checked.

**What it checks.** On the actual stream, for L-ID and L-FREQ (all kinds) and L-BFREQ (trees), at every R ∈ {1, 2, 8, 32, 128, 512} and C ∈ {8, 16, 32, 64, 128}:
- the per-query distinct-page histogram and page touches;
- distinct pages over the stream and over the warm half;
- pooled reuse within and across contexts, and the distinct-per-context sum;
- misses_all, first_touch_all, misses_warm, first_touch_warm, and warm capacity misses.

It also checks:
- trace integrity, recomputed independently;
- optionally, the trace file SHA-256 against the trace-stage record, and that the simulation record cites the same files;
- optionally, the P5 histogram and unique count.

It prints every difference and exits 1 on any difference or integrity problem, and 2 on missing input.

**Synthetic agreement.**
- Stage pipeline (dry-run flag, synthetic fixture models, 6 checkpoints × 512 queries, with trace SHA-256 linkage): **AGREE**, 480 cache configurations, 0 differences (`outputs/indep_vs_study_stage_pipeline.txt`).
- Full size (32,768 queries), 4 checkpoints: flat and fixed_tree from the implementer's generator, plus a flat with heavy count ties and a learned_tree with tied weights and within-context branch persistence from my own generator: **AGREE**, 300 configurations, 0 differences (`outputs/indep_vs_study_fullsize.txt`; Python 3.12: `…_py312.txt`).
- Negative controls (both expected to DIFFER, both did, exit 1): `--tie desc` gives 298 difference lines (`outputs/negative_control_tie_desc.txt`), and one study count altered by +1 gives exactly that count flagged (`outputs/negative_control_corrupted_record.txt`).

**Run time.** 14.5 s for 4 full-size checkpoints under project Python 3.12.14 (3.0–4.2 s each), and 17.7 s under Python 3.15.1. The 18-checkpoint clarification-7 run is projected at about 80 s, far below the 1,800 s cap.

**Selection (clarification 7, built into `--registered-selection`).** For each architecture in the order flat, fixed_tree, learned_tree: its first three checkpoints in the registered order, plus `random.Random(91501).sample(remaining 24 in registered order, 3)`, using one generator shared across the three architectures in that order. Result (`outputs/registered_selection.txt`):
- flat: b101-o301-s501/502/503, b101-o303-s501, b103-o302-s501, b103-o302-s502;
- fixed_tree: b101-o301-s501/502/503, b102-o302-s503, b103-o302-s502, b103-o303-s502;
- learned_tree: b101-o301-s501/502/503, b102-o302-s502, b102-o303-s501, b103-o303-s502.

**Post-run command.** Run it after the registered simulate stage completes and before analyze starts. Nothing else may run in the repository at the time (MINOR-5).

```sh
uv run --locked python -I docs/reviews/p7a-preflight-2026-11-13/independent_sim.py \
  --trace-root experiments/<P7AT-…trace run id>/traces \
  --sim-workers results/p7a-2026-11-13/simulate/<P7AS-…simulate run id>/workers \
  --trace-records results/p7a-2026-11-13/trace/<P7AT-…trace run id>/checkpoints \
  --p5-results results/p5-2026-11-13 \
  --registered-selection \
  --out docs/reviews/<p7a results-audit folder>/independent_sim_actual.json
```

Exit 0 means every compared count agrees. Any other exit is the registered stop in clarification 7. If the lead changes the tie rule (MINOR-1), pass the matching `--tie`. If B1 is resolved with a different frequency-matched null, this tool is unaffected, because it checks the actual stream only.

## What I did not check

- Nothing on real checkpoints or real traces. That includes bitwise replay, real trace-stage timing, real RSS, and whether the P5 histograms reproduce exactly. `loader-smoke` was not run.
- L-RAND, order-shuffled, context-shuffled and frequency-matched streams were not checked by my simulator. The shuffles were checked only as definitions.
- Tree key-read counts, branch-locality numbers and the bootstrap were not recomputed independently. They were read, and the hand tests were reviewed.
- The full analysis on a realistic 81-record set was not recomputed independently. I relied on reading the code and on the implementer's fabricated-record tests.
- The full test suite outside `tests/test_p7a_*.py` was not run.
- `p5_checkpoint.py` and `hierarchy_ablation._timing_models` beyond the calls used were not re-audited.

## Freeze recommendation

**NOT READY TO FREEZE.** Conditions:
1. B1: a recorded lead decision on the frequency-matched null (exact count-preserving null with a final query permutation, as recommended, or keep clarification 2 and amend §9 with the stated tolerance and bias direction), followed by the matching test.
2. M1: the analyze source, spec and HEAD guard, with a test.
3. M2: an independent-check gate in analyze, or a recorded lead decision that it stays procedural.
4. M3: a recorded rule for a degenerate frequency-matched stream, and the guard so it never yields STRUCTURAL ADVANTAGE, with tests.
5. MINOR-1: the tie rule recorded by the lead.

After these changes: rerun the P7-A tests, `dry-run` and `budget`, and run `independent_sim.py` again on the harness. I should re-audit the diff, and should not be the author of any of these code changes.
