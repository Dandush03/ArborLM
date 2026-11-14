# P8 results audit: independent recomputation of the single registered run

- Auditor: **Claude Opus 5.5 (`claude-opus-5-5`)**, auditor role, per this session's own metadata. **This is not Astra validation and not human approval.** Astra review: NOT_PERFORMED.
- Date: 2026-11-14 UTC. Worktree HEAD `e63a202`, freeze commit `80f46ae` (ADR-0015 revision 3).
- Scope: the registered records of runs `P8T-…5da1f4d2…`, `P8E-…ab076488…`, `P8S-…088e6814…`, `P8A-…4a9976ed…` under `/Users/daniellaloush/dandush03/ArborLM/experiments/` (read only), and their committed copies under `results/p8-2026-11-14/`.
- I edited no existing file. I ran no training, no evaluation, no simulation and no alternative null. I wrote files only in this folder. `ruff.toml` is copied from `docs/reviews/p8-preflight-2026-11-14/`.
- Environment: macOS 27.2.1 arm64, Python 3.12.14, run with `uv run --locked python -I …` from the worktree root. My code imports nothing from `arborlm`, with one exception: the frozen pre-freeze trace tool imports only `arborlm.p7a_core.query_order`, for the registered permutation indices.
- Conflict-of-interest note: I wrote the pre-freeze tools used here (`independent_recompute_p8.py`, `independent_trace_stats_p8.py`) and the pre-freeze audits. This audit checks the **implementation's** records against those tools. It is not a review of my own earlier audits, but finding 6.1 below is something those audits missed.

## 1. Independent recomputation (task 1)

Tool: `docs/reviews/p8-preflight-2026-11-14/independent_recompute_p8.py`, sha256 `dc3e7269976b6fdcb8accf5189ab5709f1db9b94bf03b73c3d274b655e6f1acb`. I checked the hash before the run, ran the tool unchanged, and found it handles the incomplete run without modification.

```
uv run --locked python -I docs/reviews/p8-preflight-2026-11-14/independent_recompute_p8.py \
  --eval-run …/P8E-20261114T043753008527Z-ab07648862054617b63d9e4d83e5407f \
  --sim-run  …/P8S-20261114T043952694180Z-088e6814edcd465894aebd125d53ddc3 \
  --out docs/reviews/p8-results-audit-2026-11-14/outputs/recompute_p8_real_run1.json \
  --analysis …/P8A-20261114T044147896561Z-4a9976ed3c7d493c8a92293786f2572c/analysis.json
```

**Result: 1,232 values compared, maximum absolute difference 0.0, 0 mismatches.** Study status INCOMPLETE, 55/60 cells, the same five missing labels, `concentration_controls_bind = false`, decision `none`. Every per-panel class, study class, beats-flat flag and architecture-advantage flag agrees.

The comparison exercised all complete comparisons: vs baseline, vs C01, and vs flat counterpart(s). It compared M-ratio, E-ratio, ρ_adj, pair counts, parent counts, ΔNLL (exact), pairs above, both retentions (exact), U-ratio (≤1e-12 relative) and guard results at four conditions × L-COAX/L-BCOAX × both panels. Comparisons involving C04 or C05 were compared on status only, because both tools mark them INCOMPLETE.

The committed `analysis.json` is byte-identical to the local one (§5).

Outputs: `outputs/recompute_p8_real_run1.json`, `outputs/recompute_p8_real_run1_summary.log`.

## 2. Headline numbers and all registered criteria (task 2)

Script: `results_tables_p8.py`. It loads the frozen tool by path with a hash check and adds descriptive fields. Output: `outputs/tables_p8_run1.json` and `.log`. All means are over the six cells. ΔNLL is the mean over pairs of NLL_case − NLL_baseline. Units are nats/byte.

### 2.1 Unregularized cases (no class; 6/6 cells complete)

| Case | Panel | mean NLL | mean gain | mean assoc. effect | mean N_eff | mean distinct slots | x = ln N_eff range | min cell null m (L-FREQ) |
|---|---|---|---|---|---|---|---|---|
| C01 | A | 2.363677 | 0.023677 | 0.023045 | 127.06 | 391.3 | [4.570, 5.036] | 1.815 |
| C01 | B | 2.345227 | 0.022925 | 0.022166 | 127.68 | 396.3 | [4.577, 5.034] | 1.828 |
| C02 | A | 2.363506 | 0.023848 | 0.023872 | 103.18 | 397.5 | [4.398, 4.926] | 1.500 |
| C02 | B | 2.345159 | 0.022994 | 0.022948 | 103.51 | 395.0 | [4.404, 4.925] | 1.498 |
| C03 | A | 2.364806 | 0.022548 | 0.022850 | 83.63 | 312.3 | [4.273, 4.636] | 1.038 |
| C03 | B | 2.346473 | 0.021680 | 0.021920 | 83.76 | 308.5 | [4.274, 4.631] | 1.032 |

No baseline cell has a null mean below 0.05.

### 2.2 Regularized cases, against their baseline (C01 for flat, C03 for trees)

Guard conditions: (i) mean ΔNLL ≤ 0.005; (ii) at most one pair > 0.005; (iii) gain retention ≥ 0.75; (iv) association retention ≥ 0.75. M-ratio is listed in the order R2C32 asc / R2C32 desc / R8C8 asc / R8C8 desc, under L-COAX.

| Case | P | mean NLL | ΔNLL | pairs > .005 | gain ret. | assoc. ret. | guard (failed) | mean N_eff | distinct | U-ratio | M-ratio (4 cond.) | pairs m_c<m_b | Class |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C04 | A | 2.374279 | +0.010602 | 6 | 0.552 | 0.569 | FAIL (i, ii, iii, iv) | 9.74 | 17.8 | 0.0756 | not determinable | — | **INCOMPLETE** |
| C04 | B | 2.355272 | +0.010045 | 6 | 0.562 | 0.583 | FAIL (i, ii, iii, iv) | 9.73 | 16.8 | 0.0752 | not determinable | — | **INCOMPLETE** |
| C05 | A | 2.376512 | +0.011706 | 6 | 0.481 | 0.456 | FAIL (i, ii, iii, iv) | 8.83 | 19.5 | 0.1046 | not determinable | — | **INCOMPLETE** |
| C05 | B | 2.357106 | +0.010634 | 6 | 0.510 | 0.483 | FAIL (i, ii, iii, iv) | 8.82 | 15.2 | 0.1044 | not determinable | — | **INCOMPLETE** |
| C06 | A | 2.367010 | +0.003333 | 1 | 0.859 | 0.881 | pass | 49.48 | 103.2 | 0.3709 | 0.1494 / 0.1498 / 0.1427 / 0.1438 | 6/6 all | COLLAPSED |
| C06 | B | 2.348642 | +0.003415 | 1 | 0.851 | 0.879 | pass | 49.84 | 102.7 | 0.3718 | 0.1512 / 0.1512 / 0.1446 / 0.1459 | 6/6 all | COLLAPSED |
| C07 | A | 2.365740 | +0.000934 | 0 | 0.959 | 0.950 | pass | 45.63 | 96.3 | 0.5384 | 0.1613 / 0.1612 / 0.1830 / 0.1890 | 6/6 all | CONCENTRATION-ONLY |
| C07 | B | 2.347558 | +0.001086 | 0 | 0.950 | 0.947 | pass | 45.78 | 93.0 | 0.5392 | 0.1615 / 0.1618 / 0.1835 / 0.1889 | 6/6 all | CONCENTRATION-ONLY |
| C08 | A | 2.367874 | +0.004197 | 2 | 0.823 | 0.843 | FAIL (ii only) | 21.63 | 32.8 | 0.1727 | 0 / 0 / 5.3e-5 / 5.5e-5 | 6/6 all | QUALITY-FAILED |
| C08 | B | 2.349592 | +0.004365 | 2 | 0.810 | 0.836 | FAIL (ii only) | 21.60 | 32.7 | 0.1715 | 0 / 0 / 0 / 0 | 6/6 all | QUALITY-FAILED |
| C09 | A | 2.368897 | +0.004091 | 2 | 0.819 | 0.785 | FAIL (ii only) | 20.91 | 37.7 | 0.2508 | 7.7e-5 / 8.8e-5 / 2.2e-4 / 2.4e-4 | 6/6 all | QUALITY-FAILED |
| C09 | B | 2.350258 | +0.003785 | 1 | 0.825 | 0.788 | pass | 20.89 | 34.8 | 0.2502 | 7.8e-6 / 8.0e-6 / 6.3e-5 / 6.7e-5 | 6/6 all | COLLAPSED |
| C10 | A | 2.371535 | +0.006730 | 4 | 0.702 | 0.691 | FAIL (i, ii, iii, iv) | 20.09 | 27.5 | 0.2385 | 0 / 0 / 0 / 0 | 6/6 all | QUALITY-FAILED |
| C10 | B | 2.352676 | +0.006203 | 5 | 0.714 | 0.705 | FAIL (i, ii, iii, iv) | 20.06 | 27.3 | 0.2378 | 0 / 0 / 1.05e-5 / 1.12e-5 | 6/6 all | QUALITY-FAILED |

C04/C05 rows: the quality and utilization columns come from the evaluation records, which exist for all 60 cells. The class column is the registered output. See §4.

### 2.3 Undefined ratios

For C06–C10, the E-ratio, the utilization-adjusted E-ratio, pairs with E_c < E_b, and the parent count are **undefined at every panel, setting and tie rule**. There are two independent reasons.

1. **E undefined (null mean under L-FREQ < 0.05 misses per query).** The case cells below the floor are the same at all four conditions and on both panels:

| Case | Cells below floor |
|---|---|
| C06 | b101-o301-s601-C06 |
| C07 | b101-o301-s601-C07, b101-o301-s602-C07 |
| C08 | all six |
| C09 | all six |
| C10 | all six |
| C04 (4 sim-complete cells) | all four |
| C05 (3 sim-complete cells) | all three |

These checkpoints' selections nearly fit in the 64 cached rows. No baseline cell is below the floor.

2. **ρ_adj would be undefined even with every E defined, because the x = ln N_eff ranges do not overlap with the baseline's on either panel:**

| Case | x range (A) | Baseline | Baseline x range (A) |
|---|---|---|---|
| C06 | [3.100, 4.313] | C01 | [4.570, 5.036] |
| C07 | [3.420, 4.097] | C03 | [4.273, 4.636] |
| C08 | [2.979, 3.158] | C01 | [4.570, 5.036] |
| C09 | [2.828, 3.154] | C03 | [4.273, 4.636] |
| C10 | [2.619, 3.135] | C03 | [4.273, 4.636] |

Panel B ranges are within ±0.01 of these.

Every M-ratio is defined. Six of six pairs have m_c < m_b in every condition for C06–C10. Parent counts on E are undefined. The implementation writes `pairs_e_lower: 0` and `parents_e_below_one: 0` in these places (see 6.4).

### 2.4 Study-level results, and whether I agree

| Case | Class A | Class B | Study class | Beats optimized flat | Architecture advantage | Agree? |
|---|---|---|---|---|---|---|
| C04 | INCOMPLETE | INCOMPLETE | INCOMPLETE | false (INCOMPLETE) | n/a (flat) | yes |
| C05 | INCOMPLETE | INCOMPLETE | INCOMPLETE | false (INCOMPLETE) | false | yes |
| C06 | COLLAPSED | COLLAPSED | COLLAPSED | false | n/a (flat) | yes: guard passes, U = 0.371 < 0.50 |
| C07 | CONC.-ONLY | CONC.-ONLY | CONCENTRATION-ONLY | false | false | yes: guard passes, U = 0.538, M ≤ 0.80 at all four conditions, LOC fails on undefined E |
| C08 | QUALITY-FAILED | QUALITY-FAILED | QUALITY-FAILED | false | n/a (flat) | yes: only condition (ii) fails |
| C09 | QUALITY-FAILED | COLLAPSED | NOT REPLICATED ACROSS PANELS | false | false | yes, mechanically (see note) |
| C10 | QUALITY-FAILED | QUALITY-FAILED | QUALITY-FAILED | false | n/a (no counterpart) | yes: all four conditions fail |

- **Beats optimized flat and architecture advantage** are false for every case because no case is LOCALITY-POSITIVE.
- **`concentration_controls_bind = false`.** Agree; it is safe. See §4b.
- **Decision map.** The registered output is `none` (INCOMPLETE). Agree with the handling. `open_questions = [C09]`.
- **Note on C09.** The panels differ only through guard condition (ii). On Panel A two pairs exceed 0.005 (0.00756 and 0.00551). On Panel B one does (0.00592), and the pair that was 0.00551 on A is 0.00486. On both panels U = 0.25 < 0.50, so neither panel can be positive under any rule order. "NOT REPLICATED" here is a product of the rule order at the 0.005 threshold. It does not mean one panel was favourable.
- **INCOMPLETE handling.** ADR-0015 §8 does not itself define the decision for an INCOMPLETE study. Returning `none` is a convention the implementer and I both adopted before the freeze. It is conservative, and I agree with it. **PENDING LEAD REVIEW** as a convention, not a registered rule.

## 3. Trace-level check (task 3)

- **Frozen tool, run unchanged on all 55 cells that have sim.json.** sha256 `5105387379ae…c16c2`. **1,903 values compared, max abs diff 0.0, 0 mismatches.** Hand checks PASS. The values cover utilization on calibration, A and B; branch statistics; temporal reuse, actual and order-shuffled; and branch persistence, actual and shuffled. Every case is covered 3–6 times. Log: `outputs/trace_stats_unchanged_tool_all55_complete.log`.
- **Failed attempt (kept).** Run unchanged on the 5 failed cells, the tool raises `FileNotFoundError` on the missing sim.json. Log: `failed_attempts/trace_stats_attempt2_FAILED_unchanged_tool_missing_sim_json.log`.
- **Fixed copy.** `trace_stats_p8_failed_cells.py` is a wrapper that loads the frozen tool by hash and uses its functions unchanged. The only change: when sim.json is missing, it still compares utilization with eval.json and reports reuse and persistence without a comparison. The order-shuffled statistics are skipped. Result on the 5 failed cells: **129 values, max diff 0.0, 0 mismatches.**
  - Every failed cell has 8 distinct slots on calibration, A and B.
  - Temporal reuse = 1.0 on both panels.
  - Trees: top-branch persistence is 1.0 / 0.95 / 1.0 and pair persistence is 0.61 / 1.0 / 0.99 (b101-s601-C05 / b101-s602-C05 / b102-s601-C05).
  - Output: `outputs/trace_stats_failed_cells_run1.json`.

## 4. The five failures (task 4)

Script: `null_failure_analysis_p8.py`. It reads traces, checks feasibility, and replays the registered greedy (re-typed from its docstring, no `arborlm` import) with the registered seeds. **It is not an alternative null and produces no registered quantity.** Output: `outputs/null_failure_analysis_run1.json`.

- **Trace counts.** All five failed cells, on both panels, have exactly 8 distinct slots, each selected 32,768 times (= queries). There is **one distinct query set: every query selects the same 8 slots.** These are exactly the five cells in the run with 8 distinct slots. The next smallest C04/C05 cells have 16–17 distinct slots (max count 26,636), and their nulls succeeded. My replay with the registered seeds on b102-s602-C05 and b102-s601-C04 also succeeds.
- **Feasibility.** With every row sum 8, Gale–Ryser reduces to Σc = 8Q and max c ≤ Q. Both hold (max c = Q exactly). The actual trace is itself a witness, so a count-preserving stream always exists. Here it is unique as a multiset: every query must hold all 8 slots, so the only valid "null" equals the actual stream.
- **Why the greedy failed.** The repair moves a duplicate x only into a row that lacks x and holds some y not in row q. Near the end of the pass (rows 32,747–32,763) every row lacking x was a subset of row q, so no single swap existed. A multi-swap chain would have been needed. **This is an incompleteness of the registered greedy, not infeasibility.**
- **Which panel failed.** My replay of Panel A reproduces the recorded error exactly for all five cells:

| Cell | Recorded error | Replicate that failed (Panel A) |
|---|---|---|
| b101-o301-s601-C04 | slot 776, row 32763 | third replicate, seed 91333003; the first two succeed |
| b101-o301-s601-C05 | slot 1889, row 32760 | first, seed 91331004 |
| b101-o301-s602-C04 | slot 1862, row 32761 | first, seed 91331013 |
| b101-o301-s602-C05 | slot 275, row 32756 | first, seed 91331014 |
| b102-o302-s601-C05 | slot 1524, row 32747 | first, seed 91331024 |

  `simulate_cell` processes panel A, then B, inside one call. The exception therefore aborted the worker and **Panel B was never attempted.**
- **No rerun.** There is one P8S run directory. Each label appears exactly once in the manifest outcomes. Each failed cell has `sim.failed.json` ("failed record kept; the cell is not re-run"), a `worker.log` traceback, and no sim.json.

**(a) What is still determinable for C04/C05 (NON-REGISTERED DESCRIPTIVE READING; the registered output is INCOMPLETE).** The quality guard and U-ratio need only evaluation records, which are complete.

- C04 fails **all four** guard conditions on both panels: ΔNLL +0.0106 / +0.0100, 6/6 pairs above, gain retention 0.55 / 0.56, association retention 0.57 / 0.58. U = 0.076.
- C05 fails all four on both panels: ΔNLL +0.0117 / +0.0106, 6/6 pairs, gain retention 0.48 / 0.51, association retention 0.46 / 0.48. U = 0.105.
- Rule 1 would therefore give **QUALITY-FAILED** on both panels for both cases. Rule 2 would give COLLAPSED if rule 1 did not fire.
- M-ratio and anything else from the simulation is not determinable, because the actual-stream simulation never ran in the failed cells: the nulls are built first.
- Independently, every sim-complete C04/C05 cell already has E undefined (null < 0.05). In the 8-slot cells, ≤ 8 pages always fit in either cache (32 pages at R = 2; 8 pages at R = 8), so their warm capacity misses would be 0 for the actual and the unique null alike. E would be undefined there too. This last point is an analytic argument, not a simulation.

**(b) `concentration_controls_bind = false` is a safe statement.** The code reaches it because INCOMPLETE ≠ LOCALITY-POSITIVE, which is an artefact of incompleteness. The statement is nevertheless determinable from complete records: under the ADR's own order, rule 1 fires for C04 and C05 on both panels from evaluation data alone. So neither can be LOCALITY-POSITIVE for any outcome of the missing simulations.

**(c) No other registered number is affected.** All 12 cells of each of C01–C03 and C06–C10 are complete; the failures are only in C04/C05. Every comparison for C06–C10 involves only complete cells: vs baseline (C01/C03), vs C01, vs flat counterpart (C07↔C06, C09↔C08, C10↔C06/C08). The recomputation shows their status as `complete` in both tools.

The only registered outputs that incompleteness changes are:
- C04/C05 classes and their comparisons, including C05 vs C04;
- the study status;
- the decision (`none`).

**Descriptive, non-registered observation (PENDING LEAD REVIEW).** No case among C06–C10 is LOCALITY-POSITIVE, and C04/C05 cannot bind. So under any completion of the five missing simulations, the §8 mechanical map would give (c). This must not be reported as the registered decision. The registered decision is `none`.

## 5. Integrity (task 5)

Script: `integrity_p8.py`. Output: `outputs/integrity_run2.json`. Run 1 failed because I used the wrong key names for train.json; it is kept in `failed_attempts/integrity_attempt1_FAILED_auditor_wrong_train_json_key_names.json`.

- **Freeze identity**, recomputed from `git show 80f46ae:` with the declared recipe over 85 `src/arborlm/*.py` files: source `8b5a03a0…0570507`, spec `979274e9…fa40ba`. The ADR on disk is unchanged since the freeze. **All 60 train.json, 60 eval.json and 55 sim.json carry exactly these two hashes.**
- **Backbone.** `backbone_sha256_before == after` in all 60 train.json, equal to the identity and to eval's `backbone_expected`. eval's step-0 and step-512 backbone digests are equal. The eval step-512 state digest equals train's `step-0512` in all 60.
- **Restore gate.** `restore_gate.json` passed. 10/10 cells (b101-o301-s601-C01…C10) have recorded final digest = restored-retrained final digest.
- **Panel record.** sha256 `2a767b5f…5c5f586d` in all 60 eval.json.
- **Committed vs local.** All 639 committed files under `results/p8-2026-11-14/{train,evaluate,simulate,analysis}/<run>/` are byte-identical to the local run directories. None differ and none are missing. The P7-B reproduction record committed at `logs/p7b_reproduction_frozen_source.json` has sha256 `86608f87…` = the hash in every sim job and manifest.
- **λ = 0 events.** 0 in every regularized cell, for every objective.
- **Clipping.** 0 clipped updates in all 60 cells. The largest pre-clip norm is 0.374 (C05).
- **Resources vs §11 caps:**

| Item | Value | Cap |
|---|---|---|
| Training stage | 392.9 s | 5,400 s |
| Largest cell | 48.1 s | 600 s |
| Sum of cells | 1,382 s | — |
| Peak training worker | 0.465 GiB | 2 GiB |
| Peak training aggregate | 1.93 GB | 8 GiB |
| Restore-gate aggregate | 1.79 GB | 8 GiB |
| Evaluation stage | 105.5 s | 1,800 s |
| Evaluation peak worker / aggregate | 0.42 GB / 1.65 GB | 2 GiB / 8 GiB |
| Simulation stage | 74.4 s | 5,400 s |
| Simulation peak worker / aggregate | 0.27 GB / 1.05 GB | 2 GiB / 8 GiB |
| Analysis | 1.0 s | 600 s |

No cap was hit.

### Proxy diagnostics

Script: `proxy_diagnostics_p8.py`, all 60 cells, means over 6 cells. Output: `outputs/proxy_diagnostics_run1.json`. See also `outputs/descriptive_extras_run1.json`.

| Case | gap₈₋₉ @1 → @512 | π outside top 8 @1 → @512 | R_conc | R_co | R_temp | λ @512 (mean) |
|---|---|---|---|---|---|---|
| C01 | 0.033 → 0.100 | 9.91 → 4.22 | 0.780 → 0.663 | 0.985 → 0.993 | 0.759 → 0.587 | — |
| C02 | 0.053 → 0.193 | 5.53 → 1.57 | 0.735 → 0.586 | 0.908 → 0.952 | 0.724 → 0.492 | — |
| C03 | 0.053 → 0.214 | 5.53 → 1.61 | 0.735 → 0.562 | 0.908 → 0.948 | 0.724 → 0.442 | — |
| C04 | 0.033 → **6.89** | 9.91 → **0.03** | 0.780 → 0.265 | 0.985 → 1.000 | 0.759 → 0.033 | **1.7·10⁵** |
| C05 | 0.053 → **8.54** | 5.53 → **0.00** | 0.735 → 0.260 | 0.908 → 0.875 | 0.724 → 0.007 | **2.2·10⁵** |
| C06 | 0.033 → 0.99 | 9.91 → 2.73 | 0.780 → 0.501 | 0.985 → **0.190** | 0.759 → 0.303 | 0.058 |
| C07 | 0.053 → 0.92 | 5.53 → 3.19 | 0.735 → 0.499 | 0.908 → **0.186** | 0.724 → 0.281 | 0.069 |
| C08 | 0.033 → 0.080 | 9.91 → 4.23 | 0.780 → 0.385 | 0.985 → 0.994 | 0.759 → **0.027** | 0.111 |
| C09 | 0.053 → 0.79 | 5.53 → 1.24 | 0.735 → 0.367 | 0.908 → 0.890 | 0.724 → **0.031** | 0.228 |
| C10 | 0.053 → **4.13** | 5.53 → **0.21** | 0.735 → 0.360 | 0.908 → 0.343 | 0.724 → 0.050 | 4.5·10³ (co), 6.3·10³ (temp) |

Reading (descriptive; the proxies falling is not a result, §9):

- Every targeted proxy fell.
- **Margin widening dominated in C04, C05 and C10.** The gap grew by 2–3 orders of magnitude, soft mass outside the top 8 went to about 0, ‖g_R‖ fell to about 3·10⁻⁸–7·10⁻⁸, and λ rose to as much as 6.0·10⁵.
- In C06/C07 the gap grew to about 1, and R_co fell to 0.19, close to the closed-form value for whole-group selections.
- In C08 the gap stayed at the baseline's level (0.08 vs 0.10) while R_temp fell to 0.027. This route is not margin widening. The hard traces show it is concentration: N_eff 21.6, warm misses about 0, and hard reuse 0.933 against a null of 0.927.

## 6. Defects and discrepancies (task 6)

1. **The simulation stage did not stop launching cells after the first failure. Spec/implementation conflict, PENDING LEAD REVIEW.**
   - ADR-0015 §16 item 6 says: "A failed cell stops the launch of further cells; the study is then INCOMPLETE". `p8_pool.run_pool`, used by evaluation and simulation, stops only on the wall cap. Training uses a separate supervisor that marks the remaining cells unexecuted.
   - b101-o301-s601-C04 failed at 04:39:55, about 2.5 s into the stage. All 60 cells were nevertheless launched, and 55 completed.
   - Under a literal reading of §16.6, most of the 55 sim records, and hence the registered classes of C06–C10, would not exist. §11 ("A cell that fails at run time is kept as a failed record; the study is then INCOMPLETE") does not require stopping. The two sections disagree.
   - It does not change the study status (INCOMPLETE) or the decision (`none`). It does decide whether the C06–C10 classes are registered outputs.
   - My pre-freeze audits did not flag this for the evaluation/simulation pool. Per AGENTS.md, the lead or human must decide; I do not choose.
2. **The registered null generator is incomplete.** It fails on feasible histograms (§4). This was not anticipated in ADR-0013/0014/0015 or by the pre-freeze audits. P7-A/P7-B never produced a single-set trace. No registered number is wrong; the five cells are INCOMPLETE as the ADR requires.
3. **Selection-biased partial means in `analysis.json` (`means`, flagged `cells: 4` / `3`) and in `scorecard.csv` (no cell-count column) for C04/C05.**
   - Evaluation-only quantities are averaged over sim-complete cells only. The excluded cells are the most collapsed ones.
   - C04 A: distinct slots 22.75 vs 17.83 over all six; memory gain 0.0154 vs 0.0131; N_eff 10.6 vs 9.74.
   - C05 A: distinct slots 31.0 vs 19.5; N_eff 9.66 vs 8.83.
   - `cells.csv` omits the five cells entirely, including their evaluation values.
   - This changes no registered result, because the classes are INCOMPLETE. The report must not present these as case means.
4. **Undefined E counts are written as 0.** `pairs_e_lower` and `parents_e_below_one` are written as 0, not null, where E is undefined (C06–C10). A reader could take this as "no pair lower". It changes no class, because LOC fails either way. `undefined_reasons` is present.
5. **The ADR §4 statement "λ is bounded" is false in practice.** λ reached 6.0·10⁵ (C05) and 4.6·10⁵ (C10) because ‖g_R‖ fell to about 10⁻⁸ in float32 under saturation. By construction ‖λ g_R‖ stays at 0.5‖g_L,Θ‖, and clipping never activated. The regularizer's direction at that magnitude may be dominated by round-off. This changes no registered number. **PENDING LEAD REVIEW** for interpretation of C04, C05 and C10.
6. **Two RSS instruments disagree slightly.** Sim manifest `peak_worker_rss_bytes` is 268,206,080, a sampled process tree. The largest sim.json `ru_maxrss` is 268,894,208, and eval shows the same pattern. Both are far under the caps. This is cosmetic.
7. **The P7-B reproduction record path in the sim manifest points to an ephemeral session scratchpad (`/private/tmp/…`).** The committed copy matches by hash. Provenance only.
8. **Implementation output does not report the determinable evaluation-only C04/C05 guard and U-ratio.** This is consistent with the registered rule, but it hides the fact that the controls could not have bound. Reporting only.
9. **The frozen report generator is being edited after the run. Observed, not my change.**
   - At the time of this audit, the working tree shows an **uncommitted modification** of `results/p8-2026-11-14/report/make_report.py`. That file was registered at the freeze as written and tested before observation.
   - The 4-line change guards a ZeroDivisionError in `fig09` (L-BCOAX / L-COAX with zero L-COAX misses). Its comment says "fixed after the registered run; the first real render raised ZeroDivisionError here".
   - Untracked report outputs exist beside it.
   - The generator is analysis-only and enters no class. However, a post-observation change to a frozen file must be disclosed, and the failed first render kept as a failed attempt. **PENDING LEAD REVIEW.** I did not touch it.
10. **Auditor's own errors (kept):**
   - `failed_attempts/trace_stats_attempt1_FAILED_auditor_shell_error_zsh_no_word_split.log`: a zsh word-splitting mistake.
   - The integrity attempt 1 key-name error described in §5.
   - An unused `import math` in `results_tables_p8.py`, found by ruff and removed. The output was regenerated and is byte-identical.

## 7. What the interpretation must not claim

- No case is LOCALITY-POSITIVE.
- Locality beyond concentration was **not** shown: every E-ratio is undefined.
- The large M-ratio reductions (0–0.19) occur together with U-ratios of 0.17–0.54. They are concentration or collapse, not locality.
- C09's NOT REPLICATED is not a positive reading on either panel.
- The registered decision is `none` (INCOMPLETE), **not (c)**, even though (c) follows under any completion (descriptive only).
- C04/C05 have no registered class. "QUALITY-FAILED" for them is a non-registered reading.
- Do not attribute the null failures to infeasibility. They are a limitation of the greedy.
- Whether the C06–C10 classes stand given defect 6.1 needs a lead/human decision.
- No statistical significance, no I/O, no SSD claim.
- This audit is not Astra validation and not human approval.

## Files

- Scripts: `results_tables_p8.py`, `trace_stats_p8_failed_cells.py`, `null_failure_analysis_p8.py`, `integrity_p8.py`, `proxy_diagnostics_p8.py`, `descriptive_extras_p8.py`.
- Outputs: `outputs/`.
- Failed attempts: `failed_attempts/`.
- sha256 of the scripts (final): tables `20f8724d…`, failed-cell trace wrapper `64233d2a…`, null analysis `3ca6bafa…`, integrity `6a5fb48d…`, proxy `9702f091…`, extras `860d9203…`.
- `uv run --locked ruff check .` passes from the repository root.
