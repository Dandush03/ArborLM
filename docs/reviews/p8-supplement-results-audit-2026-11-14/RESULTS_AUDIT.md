# P8 supplement (ADR-0016) results audit: independent recomputation of the single run

- Auditor: **Claude Opus 5.5 (`claude-opus-5-5`)**, auditor role, per this session's metadata. **This is independent engineering and mathematical evidence. It is not Astra validation and not human approval.** Astra review: NOT_PERFORMED.
- Date: 2026-11-14. Worktree HEAD `e71d433` (tree `3db6ae93…`). Supplement freeze `3018126` (tree `671c184a19f183812588c5da491fa6733a1c88a3`).
- Scope: ADR-0016 gate 8.
  - Run `experiments/P8SUP-20261114T144104227089Z-fbfb3d18513749b081f9cdd93f22ad81` and its committed copy.
  - Analysis `results/p8-supplement-2026-11-14/analysis/P8SUPA-20261114T144120084661Z-f008b8673e97484fa528ccf36beba4e9/`.
  - Logs under `results/p8-supplement-2026-11-14/logs/`.
  - Inputs: evaluation run `P8E-…ab076488…`, registered sim run `P8S-…088e6814…`, registered analysis `P8A-…4a9976ed…`.
- What I did and did not do:
  - I edited no existing file and wrote only in this folder. I ran no training, evaluation, registered stage or supplement stage.
  - I imported nothing from `supplements.p8s` and no `arborlm.*_analysis` module. The only `arborlm` import is `arborlm.p7a_core.query_order`, used for the registered order-shuffle permutation indices. This is the same single import as in my P8 results audit.
- Environment: macOS 27.2.1 arm64, Python 3.12.14, uv 0.12.15. Commands were run from the worktree root with `uv run --locked python -I …`.
- Conflict-of-interest note. I wrote the reused auditor tools before this run, in the P7-B and P8 pre-freeze audits. Each is loaded unchanged and checked against a pinned hash:
  - `p7b-preflight-2026-11-13/tools/independent_layouts.py` `bfb21a57…77b9`
  - `independent_resim.py` `4e53ebbc…02f1`
  - `p8-preflight-2026-11-14/independent_recompute_p8.py` `dc3e7269…1acb`

  None of them is implementation code. I did not write the supplement code.

## Commands

| # | Command | Result | Output |
|---|---|---|---|
| 1 | `uv run --locked python -I docs/reviews/p8-supplement-results-audit-2026-11-14/integrity_p8s.py docs/reviews/p8-supplement-results-audit-2026-11-14/outputs/integrity_run1.json` | 41 checks, 0 problems | `outputs/integrity_run1.json` |
| 2 | `uv run --locked python -I docs/reviews/p8-supplement-results-audit-2026-11-14/resim_p8s.py docs/reviews/p8-supplement-results-audit-2026-11-14/outputs/resim_run2.json` | 5,934 values, 0 differences, max float diff 0.0, 15.7 s | `outputs/resim_run2.json` (`resim_run1.json` is the same content from the script before a lint-only edit) |
| 3 | `uv run --locked python -I docs/reviews/p8-supplement-results-audit-2026-11-14/analysis_p8s.py <scratchpad>/p8s_audit docs/reviews/p8-supplement-results-audit-2026-11-14/outputs/analysis_run3.json` | see §3 | `outputs/analysis_run3.json` (byte-identical to `analysis_run2.json`), `outputs/recompute_merged60_vs_supplementary_run1.*`, `outputs/recompute_registered55_control_run1.*` |
| 3a (failed, kept) | the same command with the first version of the script | 8 mean differences (≤ 5.8e-5 relative); all were my error | `failed_attempts/analysis_p8s.attempt1.py`, `failed_attempts/analysis_attempt1_FAILED_auditor_ratio_of_means_reading.json` |
| 4 | `uv run --locked ruff check .` | All checks passed | — |

`<scratchpad>` is `/private/tmp/claude-501/-Users-daniellaloush-dandush03-ArborLM--claude-worktrees-arborlm-consolidation-experiment-2b31c1/cfc0efd5-b7ca-4602-959a-07fe6b8d4e7d/scratchpad`. It holds a symlinked merged 60-cell sim directory (55 registered + 5 supplement `sim.json`) and the nested `supplementary_analysis` extracted to a file.

Final script sha256 values:

| Script | sha256 |
|---|---|
| `integrity_p8s.py` | `04757a2a…dc11d` |
| `resim_p8s.py` | `897236d0…0d0d` |
| `analysis_p8s.py` | `fcb192be…4be2` |

Note: `analysis_p8s.py` writes the two `recompute_*_run1.*` files under a fixed name, so runs 2 and 3 overwrote them. The tool is deterministic. The values cited are those of the final run.

## 1. Integrity (task 1): all hold

- **One run.**
  - There is exactly one `P8SUP-*` directory under `/Users/daniellaloush/dandush03/ArborLM/experiments`. A `find` over the repository and `/tmp` found no other, and the worktree has no `experiments/`.
  - The run has no `*.failed.json` file and no traceback. The worker logs contain only the NumPy-missing `UserWarning`.
  - The manifest shows 5/5 `completed`, return code 0, and labels equal to the five ADR labels in order.
  - The preflight records simulate none of the five cells' panel traces. They contain no miss counts; the preflight checks are layouts, replay, analysis and blobs.
- **Freeze.**
  - `3018126db5f8…` has tree `671c184a…` and `supplements` tree `20c6eaef…`. These equal the record in the manifest, all five `sim.json` and all five `job.json`.
  - The freeze commit time is 14:40:56Z. The run started at 14:41:04Z and finished at 14:41:15Z, and the analysis finished at 14:41:20Z.
  - `git diff 3018126 HEAD` touches only `results/p8-supplement-2026-11-14/`.
  - The stage refuses a dirty tree. I cannot observe the tree state at run time directly. The digests below are consistent with a clean tree.
- **Identity fields (re-typed recipes).**
  - `supplement_source_sha256` `88b86f48…5377`: recomputed from the 9 `supplements/p8s/*.py` blobs at `3018126` and from disk. Equal.
  - `supplement_spec_sha256` `22d25195…4458`: equals ADR-0016 at `3018126` and on disk. Equal.
  - Frozen digest `8b5a03a0…0507`: recomputed over the 85 `src/arborlm/*.py` blobs at `378aeac` and on disk. Equal.
  - `378aeac` → tree `b13a9f9c…` and `b8302c2` → tree `290d15de…`, as recorded in `frozen_inputs`.
  - `frozen_inputs.spec_sha256_registered_records` = `979274e9…40ba` = each `eval.json`'s `spec_sha256`.
  - No `sim.json` carries a top-level `spec_sha256` or `reproduction_record_sha256`, so none claims the P8 spec as its own.
  - `eval_json_sha256` equals the local `eval.json` and its blob at `b8302c2` for all five cells.
  - The P7-B citation `86608f87…f9a8` equals `reproduction_gate.sha256` of the registered P8S manifest at `b8302c2` and the sha256 of `results/p8-2026-11-14/logs/p7b_reproduction_frozen_source.json`.
- **Committed copies.** All 16 committed files equal the run directory byte for byte. The five `layouts.int16.bin` are not committed, the same practice as the registered P8S run, where 0 layout files are committed.
- **Limits.** 1 worker. Peak worker RSS 242,270,208 B (sampled); the largest `ru_maxrss` is 243,417,088 B, against a 2 GiB limit. Stage 11.20 s plus analysis 0.31 s, against 1,800 s. Cap not hit.
- **Untouched material.**
  - For all five cells, each `sim.failed.json` in `P8S-…` equals the committed copy and its blob at `b8302c2`, and none of those cells has a `sim.json`.
  - No file in the P8S or P8E run directories was modified within ±1 h of the supplement start.
  - All 669 tracked files under `results/p8-2026-11-14/` equal HEAD, with nothing untracked. Changes there since `b8302c2` all predate the supplement freeze: commits `be6c08a`, `d47a9fd` and `2d10338`.
  - `src/arborlm`, `configs`, `uv.lock`, `pyproject.toml` and the ten P8 test files are unchanged since `378aeac`.
  - ADRs are unchanged since `3018126`.
  - The registered `analysis.json` (committed = local, sha256 `4f53453a…076b`) is the one cited in the supplement inputs.

## 2. Five cells × two panels: precondition, identity null, re-simulation (task 2)

Method (`resim_p8s.py`):

- Traces are read with `struct` and checked against the hashes in `eval.json`.
- Layouts are rebuilt from the calibration trace only, using the auditor's P7-B layout tool. L-ID (identity) and L-FREQ (descending count, then slot ID) are added.
- LRU is the auditor's `independent_resim.lru`. It is a stamp-heap implementation, structurally different from the frozen `OrderedDict` and shortcut path. Page statistics, temporal reuse and branch persistence are re-typed.
- Every leaf of `panels.A` and `panels.B` and of `layouts.{hash_table,meta}` is compared type-strictly. Floats are compared exactly and reported.

Results:

- **Precondition.** It holds in all 10 panel traces: exactly 8 non-zero counts, each = 32,768. The redundant check also holds: every query's set equals S. S is the same on A and B in every cell. The recorded `supplement_null_preconditions` entries (`holds`, `nonzero_slots`, `queries`, `slots`, `reasons`) all match.
- **Identity null = trace as sets.** True in all 10 panels. My `sha256(pack('<h', rows of sorted S))` equals the recorded `stream_sha256` for all 30 replicates. The replicate seeds are 91331–3 (A) and 91341–3 (B), and generator seed = s·1000 + cell index. Indices 3, 4, 13, 14, 23 equal the registry.
- **Layouts.**
  - The canonical hashes of all 16 (trees) or 14 (flat) layout×R keys equal `hash_table`.
  - Page membership of every entry, read at both R for L-ID and L-FREQ, equals my pages. This holds for the run's `layouts.int16.bin` and for the failed P8S directory's `layouts.int16.bin`, and the two files are byte-identical (`file_sha256` as recorded).
  - Refinement meta (passes, swaps, converged, within-page affinity before/after), `affinity_nonzero_entries` = 56, `unique_selected_slots` = 8 and `calibration_counts_sha256` all match.
- **Simulation.** The following were compared with the record:
  - Configurations: actual under every layout; order-shuffled and three nulls under L-FREQ and L-COAX; at R2/C32 and R8/C8; ascending and descending tie rules.
  - Fields: `stats` (hist, pages_sum, distinct_stream, distinct_first_half) and `misses_all`, `first_touch_all`, `misses_warm`, `first_touch_warm` and `ctx_q`.
  - Also: `evaluation_counts`, `null_streams`, `temporal_reuse` (5 streams), `branch_persistence` (actual and shuffled, trees) and `trace_files`.

  **Total: 5,934 values, 0 differences, max absolute float difference 0.0.** No recorded panel leaf was left uncompared. The only uncompared leaves are 324 structural layout entries (`index`, `file`, `note`, `built_from`), and `index` is used to read the files.

### Predictions, checked on my own recomputation (not on the tool's check)

| # | My check | Checked | Holds |
|---|---|---|---|
| 1 | actual: misses_warm − first_touch_warm = 0, every layout/setting/tie | 344 | yes |
| 2 | each null and order-shuffled group equals the actual group (stats + counts), and temporal reuse is equal | 160 + 40 = 200 | yes |
| 3 | temporal reuse actual / mean null = 1.0 exactly (hits 258,048 / 32,256 counted) | 10 | yes |
| 4 | mean L-FREQ null m < 0.05 (it is exactly 0) at each panel × setting × tie | 40 | yes |
| 5 | C04, C05 QUALITY-FAILED on A and B and as study class (§3) | 6 | yes |
| 6 | misses_warm = first_touch_warm = 0 and misses_all = first_touch_all = distinct pages ≤ 8 | 664 | yes |
| 7 | the three null hashes of a panel are identical | 10 | yes |
| 8 | `concentration_controls_bind` false; `open_questions` = [C09], equal to the registered one | 2 | yes |
| 9 | mechanical letter `c` (my unchanged tool and the nested output) | 1 | yes |

My counts for predictions 1, 2, 3, 6 and 7 equal the tool's. For prediction 4 the tool reports 344, counting per layout configuration, and I count the 40 null denominators. This is a difference of granularity, not of outcome.

## 3. Supplementary analysis (task 3)

- **Unchanged auditor tool on the merged 60 records vs the nested `supplementary_analysis`: 1,548 values, max abs diff 0.0, 0 mismatches.** These are exact fractions where the output gives them, and include every C04/C05 comparison now `complete`.
- Control on the 55 registered records vs registered `analysis.json`: 1,232 values, 0 mismatches, reproducing my P8 audit.
- My recomputed classes:

| | A | B | Study class |
|---|---|---|---|
| C04 | QUALITY-FAILED | QUALITY-FAILED | QUALITY-FAILED |
| C05 | QUALITY-FAILED | QUALITY-FAILED | QUALITY-FAILED |

  C06–C10 are unchanged: COLLAPSED, CONCENTRATION-ONLY, QUALITY-FAILED, NOT REPLICATED ACROSS PANELS, QUALITY-FAILED. Nested status COMPLETE, letter `c`. These are supplementary only (§6).
- **C04/C05 guard (vs baseline, all six pairs; exact).** All four conditions fail on both panels:

| | ΔNLL | pairs > 0.005 | gain ret. | assoc. ret. | U-ratio |
|---|---|---|---|---|---|
| C04 A | 5692021/536870912 = 0.010602 | 6 | 0.5522 | 0.5686 | 0.0756 |
| C04 B | 0.010045 | 6 | 0.5619 | 0.5830 | 0.0752 |
| C05 A | 0.011706 | 6 | 0.4808 | 0.4560 | 0.1046 |
| C05 B | 0.010634 | 6 | 0.5095 | 0.4827 | 0.1044 |

  These equal the evaluation-only values in my P8 audit §4(a).
- **Case means.** I re-typed them from `eval.json` and `sim.json` for C04/C05 over all six cells, and over the sim-complete subset for the registered partial means. They cover 16 mean fields per case and panel, including branch persistence and its ratios for C05. Compared with the nested and registered `means`: **128 values, max relative diff 0.0.** Every C04/C05 E-ratio and ρ_adj is undefined, and every M-ratio vs baseline is 0 at R2/C32. Both are covered by the 1,548 values above.
- **W5 (my own deep diff, excluding `dry_run` and `inputs`).**
  - 257 differing leaf paths, all within the allowed set: `study_status`, `cells_with_complete_records`, `missing_cells`, `cases.C04.*`, `cases.C05.*`, `decision_inputs.section_8_option_indicated` (`c` vs `none`) and `decision_inputs.section_8_reason`. **0 disallowed.**
  - 10,439 registered leaves outside the allowed set are equal.
  - No path outside `cases.C04/C05` names C04 or C05, and no other case carries C04 or C05 as a value.
- **CSVs.** In each file the first line is the label and the headers are equal.
  - `cells.csv`: the 440 registered rows are equal; there are 40 new rows, all from the five cells, and the registered file has none of them.
  - `pairs.csv`: the 1,536 non-C04/C05 rows are equal; C04/C05 rows go from 208 to 384; no other row references C04 or C05.
  - `scorecard.csv`: row order is equal, and the 8 non-C04/C05 rows differ only in `study_status` (INCOMPLETE → COMPLETE).

## 4. C04/C05 registered partial means vs supplementary all-six means (task 4; my P8 audit defect 3)

Registered partial means use 4 cells for C04 and 3 for C05. Supplementary means use all 6. I recomputed both independently, and both equal the outputs exactly.

| Case | P | Quantity | Registered partial | Supplementary all six | Change |
|---|---|---|---|---|---|
| C04 | A | NLL | 2.379714 | 2.374279 | −0.005435 |
| C04 | A | memory gain | 0.015405 | 0.013074 | −15.1% |
| C04 | A | value-association effect | 0.015500 | 0.013104 | −15.5% |
| C04 | A | N_eff | 10.610 | 9.740 | −8.2% |
| C04 | A | distinct slots | 22.75 | 17.83 | −21.6% |
| C04 | A | context breadth | 12.533 | 11.022 | |
| C04 | A | temporal reuse | 0.97561 | 0.98374 | |
| C04 | A | reuse ratio to null | 1.00151 | 1.00100 | |
| C04 | B | NLL | 2.359056 | 2.355272 | −0.003784 |
| C04 | B | memory gain | 0.015954 | 0.012881 | −19.3% |
| C04 | B | value-association effect | 0.016061 | 0.012923 | |
| C04 | B | N_eff | 10.593 | 9.729 | |
| C04 | B | distinct slots | 21.25 | 16.83 | |
| C04 | B | context breadth | 12.517 | 11.011 | |
| C04 | B | temporal reuse | 0.97616 | 0.98411 | |
| C04 | B | reuse ratio to null | 1.00219 | 1.00146 | |
| C05 | A | NLL | 2.381162 | 2.376512 | −0.004650 |
| C05 | A | memory gain | 0.013857 | 0.010842 | −21.8% |
| C05 | A | value-association effect | 0.012983 | 0.010420 | −19.7% |
| C05 | A | N_eff | 9.664 | 8.832 | −8.6% |
| C05 | A | distinct slots | 31.00 | 19.50 | −37.1% |
| C05 | A | context breadth | 10.726 | 9.363 | |
| C05 | A | temporal reuse | 0.98630 | 0.99315 | |
| C05 | A | branch persistence top / pair | 0.7799 / 0.6690 | 0.8815 / 0.7665 | |
| C05 | B | NLL | 2.360655 | 2.357106 | |
| C05 | B | memory gain | 0.014796 | 0.011046 | −25.3% |
| C05 | B | value-association effect | 0.013828 | 0.010581 | |
| C05 | B | N_eff | 9.648 | 8.824 | |
| C05 | B | distinct slots | 22.33 | 15.17 | −32.1% |
| C05 | B | context breadth | 10.691 | 9.346 | |
| C05 | B | temporal reuse | 0.98670 | 0.99335 | |
| C05 | B | branch persistence top / pair | 0.7810 / 0.6688 | 0.8820 / 0.7665 | |

The bias I flagged runs in the stated direction. Excluding the most collapsed cells made the partial means look less collapsed and better on memory gain, although the partial NLL was higher. The all-six means are more collapsed, with lower gain and lower NLL. The registered `scorecard.csv` C04/C05 rows still show the partial values without a cell count. That file is registered and unchanged, so this is a reporting point, not a defect of the supplement.

Descriptive aside: `nll.step512.disabled` is identical across all ten cases within every (parent, seed) and panel (spread 0.0). This is why the supplementary C04 and C05 `nll_disabled` means coincide. It is consistent with a disabled memory leaving only the shared frozen backbone.

## 5. Labels and §8 claims (task 5)

- The label `SUPPLEMENTARY (ADR-0016) — not the registered P8 output` is present in the following files, and each states the registered status INCOMPLETE / `none` where it carries a result:
  - the first line of `SUPPLEMENTARY_ANALYSIS.md`, `cells.csv`, `pairs.csv` and `scorecard.csv`;
  - the top level of `supplementary_analysis.json`, together with `registered_study_status: INCOMPLETE`, `registered_decision: none` and the note;
  - the analysis `manifest.json` and the stage `manifest.json`.
- Each `sim.json` carries `supplement_label: "… not a registered P8 record"`.
- Unlabelled: `timing.json`, `logs/*.log`, `job.json` and `worker.log`. These are not result outputs.
- A regex scan for each §8 claim found only negated statements, for example "does not supersede", "its decision is not (c)", "replicates nothing" and "No positive result". Other matches were `replicate_seed`, the registered C09 class "NOT REPLICATED ACROSS PANELS", and "SUPERSEDED" in the preflight README, which refers to an old preflight record. **No forbidden claim was found.** The nested `study_status: COMPLETE` and letter `c` appear only inside the labelled envelope.

## 6. Findings, graded

**No blocker and no major finding. No discrepancy between my recomputation and any recorded value.**

1. **Minor, documentation: ADR-0016 still says "Not yet executed" (status line) and "None. Not executed." (§10).** The lead must add the outcome record. Editing the ADR will change its on-disk sha256 away from `supplement_spec_sha256`. The records correctly cite the hash at the freeze, so the change should be disclosed the same way as ADR-0015's §17. PENDING LEAD REVIEW.
2. **Minor, reporting granularity.** `comparison_with_registered.analysis.allowed_differences_seen` lists `decision_inputs` as a whole. W5 allows only two of its keys. My diff shows that only those two differ, so the claim is true but the evidence printed is coarser than the rule.
3. **Informational, wording of prediction 2.** "The order-shuffled record equals the actual record in every simulated quantity" holds for the simulation and temporal reuse. Branch persistence of the order-shuffled stream does differ from the actual stream in the tree cells; for example, b101-s601-C05 A has pair fraction 0.606 actual and 0.530 shuffled. The selected set is constant, but the second visited branch varies by query. This is a hard-trace statistic, not a simulated quantity, and both the tool and I exclude it from prediction 2. It should not be read as a violation.
4. **Informational.** Prediction-4 counts differ in granularity (344 in the tool, 40 null denominators in mine). The outcome is the same.
5. **Informational.** Provenance: the run used the main checkout's `experiments/` while executing from this worktree. `refuse_if_previous_run` checks only that root. I found no other `P8SUP-*` anywhere under the repository or `/tmp`.
6. **Carried over, not new.** The registered `scorecard.csv` and `analysis.json` partial C04/C05 means (defect 3 of my P8 audit) remain as registered. The supplement sits beside them and does not correct them (§4).
7. **My own errors (kept).**
   - Analysis attempt 1 computed `temporal_reuse_ratio_to_null` as a ratio of means. The output uses the mean of per-cell ratios. The result was 8 apparent differences of at most 5.8e-5 relative. After I switched to the per-cell reading, which also matches the registered partial means, the differences are 0. The ADR text names "ratio to null" without fixing the order of the mean. Both readings are near 1.00. Files: `failed_attempts/`.
   - ruff found an unused import and a `UP038` style issue in my final scripts. I fixed them and re-ran; the outputs are content-identical (`resim_run1` = `resim_run2` except `seconds`, and `analysis_run2` = `analysis_run3` byte for byte). The failed-attempt script is kept byte-identical. `failed_attempts/ruff.toml` ignores F401 there.

## 7. What may and may not be claimed

May be claimed:

- The single supplementary execution ran once, at the supplement freeze tree `671c184a…`, against unchanged frozen P8 material and inputs, within the ADR-0016 limits.
- It produced simulation records for the five collapsed cells. These records agree value for value with an independent recomputation from the raw traces.
- All nine §2 predictions, which were derived on paper beforehand, hold on that recomputation.
- The 60-record supplementary analysis differs from the registered analysis only where W5 allows.
- On all six cells, C04 and C05 fail every quality-guard condition on both panels. Their all-six means are more collapsed than the registered partial means.

May not be claimed:

- That the registered P8 study is complete or that its decision is (c). It remains INCOMPLETE with decision `none`.
- That QUALITY-FAILED for C04/C05 is a registered class, or that the supplementary means supersede `analysis.json`.
- That the supplement tested, replicated or discovered anything. Its outcome was fixed in advance, it reuses the same traces, and the identity null carries no locality information, so E is undefined by construction.
- That the null generator is repaired.
- Any positive result for locality-aware training.

This audit is not Astra validation and not human approval.
