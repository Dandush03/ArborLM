# P8 pre-freeze implementation audit, part 2: evaluation, simulation, analysis

- Auditor: **Claude Opus 5.5 (`claude-opus-5-5`)**, from this session's metadata, acting in the auditor role. I did not write any of the audited code.
- Date: 2026-11-14 UTC (2026-11-13 EST). Worktree `claude/p8-locality-aware-training` at HEAD `74851bd`, with uncommitted P8 files.
- Scope: `src/arborlm/p8_panel.py`, `p8_eval.py`, `p8_sim.py`, `p8_analysis.py`, `p8_pool.py`, `tests/test_p8_{panel,eval,sim,analysis}.py`, `tests/p8_fake.py`, `tests/p8_dry.py`, checked against ADR-0015 revision 2 (§6, §7, §8, §10, §11, §12).
- Audited source hashes: `outputs/eval_sim_analysis_audited_source_hashes.txt`. They were taken after `p8_core.py` changed during the audit and were identical again at the end.
- This is independent engineering and mathematical evidence only. It is **not Astra validation and not human approval**. No P8 model was evaluated, traced or simulated on the real Panel A or Panel B. Only synthetic dry-run data and published P5/P7-B artifacts were used.

## Verdict: **FIX REQUIRED** (0 BLOCKER, 2 MAJOR, 7 MINOR)

Everything that sets a registered number agrees exactly with my independent code: the m formula, E, the ratios, the OLS adjustment, pair and parent counts, the guards, the classification, study class, beats-flat, architecture advantage, the binding of the concentration controls, and the decision map. That holds on the dry run and on three perturbed fixtures that reach every class.

Layouts can only be built from the calibration trace. The P7-B reproduction gate passes, and it detects a perturbed value, so it is not vacuous.

Two problems must be fixed before the freeze:
- The evaluation, simulation and analysis stages are not bound to the freeze commit.
- The retention rule needs a lead decision for a baseline gain of zero or less.

## Findings

### MAJOR-1: the eval, sim and analysis stages are not bound to the freeze commit or to consistent provenance

**Where:**
- `p8_eval.py:366-383` (`git_gate`): `freeze_commit` is optional.
- `p8_eval.py:400-409`: a registered run checks only that the panel record is tracked and clean.
- `p8_sim.py:424-428`: the only check is that the reproduction record has the same `source_digest()`.
- `p8_analysis.py:1017-1033` and `load_cells` `:347-376`: no freeze check and no check that the inputs are consistent.

**Contrast:** training refuses to run without `--freeze-commit` and verifies the working tree against it (`p8_train.py:67-100, 680-685`).

**Why it matters:** ADR §12 requires that no P8 checkpoint is evaluated on a panel before the freeze, and that the freeze covers source, config, spec and panel hashes. As written, `evaluate` can open both panels with source that differs from the frozen source. This is a live risk: `p8_core.py` was edited while this audit ran (mtime 22:58:09 EST), and the source digest changed from `ee6645b3…` (the digest in my reproduction record) to `727209c2…` (the digest in my dry-run stages). Separately, the analysis never checks that its 60 eval and sim records share one `source_sha256`, `spec_sha256` and `panel_record_sha256`, or that their `dry_run` flag matches. A registered analysis (prefix `P8A`) would accept dry-run records.

**Fix:**
1. Move `verify_freeze` into `p8_core`, or import it.
2. In `p8_eval.run_stage`, `p8_sim.run_stage` and `p8_analysis.run_analysis`, when `dry_run` is false: require `--freeze-commit`, call `verify_freeze`, and write the result into the stage manifest. In `git_gate`, raise `GateError` if `freeze_commit is None`.
3. In `load_cells`, refuse unless every eval.json and sim.json, and both stage manifests, carry the same `source_sha256` and `spec_sha256`, and the same `dry_run` value as the `dry_run` argument. Every eval.json must also carry the same `panel_record_sha256`, equal to the sha256 of the frozen record.
4. In `p8_eval.worker_main` (`:325-327`), check that `file_sha256(record_path) == job["panel_record_sha256"]` before using the record. This is the MINOR-6 TOCTOU fix.

### MAJOR-2: retention is wrong when the baseline's mean gain is zero or negative (PENDING LEAD REVIEW; decide before the freeze)

**Where:** `p8_analysis.py:516-517` uses `ratio()`, which is undefined only when the denominator is exactly 0 (`:248`).

**What goes wrong:** with a negative baseline mean, the sign of the retention ratio flips.

I demonstrated this on fixture `stress_negbase`, built from the dry run with `outputs/recompute_stress_fixture_builder.py negbase`: C01's gain was set to −0.002 and C06's to −0.004.
- **False pass.** C06, whose memory hurts twice as much as its baseline's, gets gain retention 2.0. It passes the guard and is classified LOCALITY-POSITIVE.
- **False fail.** C04 and C08 have a healthy +0.02 gain, but get retention −10 and become QUALITY-FAILED.

The unperturbed dry run already has a non-positive baseline mean in 21 of 42 gain comparisons and 35 of 42 association comparisons, because random-init memories have gain ≈ 0.

P5 measured a positive gain and shuffle penalty in 27 of 27 cells (≈0.02), so this situation is unlikely in the real run. But it cannot be repaired after observation.

**Proposed rule (lead to decide):** retention is undefined, so the quality guard fails and the case is QUALITY-FAILED, when the baseline mean is ≤ 0. Change `paired_quality` to:

```python
gain_ret, why_g = (None, "gain retention: baseline mean gain <= 0") if fmean(gains_r) <= 0 else ratio(...)
assoc_ret, why_a = (None, "association retention: baseline mean effect <= 0") if fmean(effects_r) <= 0 else ratio(...)
```

My tool reports the literal-ADR result and also this alternative (`quality_passes_if_nonpositive_baseline_undefined`).

### MINOR findings

1. **LOC holds but the U-ratio is undefined: the code returns CONCENTRATION-ONLY instead of INTERMEDIATE** (`p8_analysis.py:151-154`). Rule 5 requires LOC to fail, so rule 8 (INTERMEDIATE) should apply. This cannot happen in practice, because N_eff = exp(H) ≥ 1. Fix: `if loc: return INTERMEDIATE if u_ratio is None else (POSITIVE if ... else REDUCED)`.
2. **Misleading reason text** (`p8_analysis.py:491`): it says "null denominator zero" when E is undefined because of the < 0.05 floor. Reword it to "null mean under L-FREQ below 0.05".
3. **ADR §7.1 descriptive quantities are recorded but not reported.** First-touch misses, cold (from-empty) misses and distinct pages per query are in the raw counts in sim.json, but no analysis output (`cells.csv`, `scorecard.csv`) shows them. Add columns.
4. **Sim per-cell deadline** (`p8_sim.py:450`): each cell is given the whole stage cap (5,400 s), not the time remaining. The pool still enforces the stage cap, so this is cosmetic.
5. **Decision map, PENDING LEAD REVIEW.** Option (a) is returned whenever C07 or C09 has an architecture advantage, even if other cases are NOT REPLICATED. ADR §8 says "mixed or non-replicated outcomes … default to (c)". The implementation and my tool share the reading that (a) takes precedence; the lead should confirm it.
6. **TOCTOU on the panel record in the eval worker.** Covered by the MAJOR-1 fix.
7. **Scientific observation, PENDING LEAD REVIEW, not a code defect.** ρ_adj against C01 or against the flat counterpart is undefined when the tree's and the flat memory's ln N_eff ranges do not overlap (ADR §7.2, literal). This is what blocked C09's "beats optimized flat" on the stress fixture.
   - On P5's diagonal parents (P7-B stream-A records), flat x lies in [4.44, 5.03] and learned-tree x in [4.08, 4.71]. The overlap is only 0.27 nats.
   - A tree regularizer that concentrates selection could remove that overlap. "Beats optimized flat", and therefore option (a), would then be unreachable for that case.
   - The implementation follows the ADR correctly. I am only flagging that this criterion may be impossible to meet.

## Item-by-item checks

**1. p8_eval**
- Panels come from `panel_tensors`, in (panel_A, panel_B) order. Ranks are [3072,3584) and [3584,4096), from `PANEL_RANKS`. Whole-panel and per-row SHA-256 are checked against the frozen record before use (`p8_panel.verify_panel_bytes`).
- Calibration is training ranks 2048–2559, checked against P1's training-pool hash and against `record["calibration_stream"]`.
- P5's `evaluate` refuses to run unless there are exactly 32,768 targets.
- Memory disabled is `model.bypass = True`, as in P5's `intervene`. Values permuted uses P5's `randperm(4096)` construction with seed 80000 + cell.index; I verified this on all 60 dry-run cells.
- Each condition runs on a freshly restored model. State digests are compared before and after the traces and after a final restore.
- Traces come from the unchanged `p7a_trace.collect_trace`, in context-major order. Branch column 0 is the top branch (`stable_top`, sorted).
- I recomputed the utilization statistics on every dry-run trace with my own struct-based code. That covers distinct slots, N_eff, hot-64 share, per-context breadth, and branch statistics both over all visits and over the top column. Result: **2,076 values, max abs diff 0.0**. The hand-constructed checks also pass.

**2. p8_sim**
- **Layouts come only from the calibration trace.**
  - `simulate_cell` loads the "calibration" entry and wraps it with `CalibrationTrace.declared`. `build_p8_layouts` calls `require_calibration`.
  - Panel traces go only to `simulate_panel`, then `simulate_trace`, then `page_sets`. No call path from them reaches a layout builder.
  - In all 60 dry-run sim.json files, `calibration_counts_sha256` equals the eval calibration counts hash and differs from both panels' hashes.
- **Constructions.** The layouts are the unchanged `p7b_layout` and `p7a_core` constructions: L-ID, L-FREQ, L-COAX, L-BCOAX (trees only) and L-PCOAX-1..5 (seeds 91601–91605), at R = 2 and R = 8. Each setting has exactly one capacity (32 and 8), with both tie rules.
- **Simulation plan.** Nulls and the order-shuffled stream are simulated under L-FREQ and L-COAX, which I verified for every cell.
- **Null seeds.** Replicate seeds are 91331–3 (Panel A) and 91341–3 (Panel B). The generator seed is s·1000 + index. Verified for all 60 cells.
- **m.** m = (misses_warm − first_touch_warm) / (q − q//2), the same definition as `p7b_analysis` (lines 316 and 1038). Warm-up is the first 16,384 queries (256 contexts).
- **Temporal reuse and branch persistence** match ADR §7.1. My recomputation agrees exactly, including the order-shuffled stream (seed 91201, a full query permutation).
- **P7-B reproduction gate** (`outputs/p7b_reproduction_auditor_rerun.json`): ALL_EQUAL.
  - It compared against `results/p7b-2026-11-13/simulate-a/P7BSA-…` and `layouts/P7BL-…`: 58 and 62 count configurations, 16 and 18 layout hashes, and 8 and 12 m values. Six configurations per label had no P7-B counterpart (the desc tie rule for L-ID and for order-shuffled).
  - **Not vacuous.** With one recorded P7-B count changed in memory (`outputs/p7b_reproduction_perturbation_check.py`), the gate reports DIFFERENT. That holds for actual misses_warm, actual first_touch_warm and null_1 misses_warm.
  - The record is tied to `source_digest`. Mine is now stale (`ee6645…`), so it must be regenerated on the frozen source.

**3. p8_analysis.** I checked it line by line against §7.2–§7.4 and §8. Only MAJOR-2 and MINOR-1 and MINOR-5 depart from the ADR. My recomputation results are summarised below.

**5. Incomplete studies.**
- Analysis refuses to run without `--allow-incomplete`. With it, the study is stamped INCOMPLETE with denominator 60, and the decision is "none". Tested by removing one sim.json, and my tool agrees.
- A cell counts only if its sim.json holds both panels and is linked by hash to its eval.json. The simulate stage always does both panels within one cell job.
- Vacuous-gate risks are the ones in MAJOR-1.

**6. Tests.** `ARBORLM_DATA_DIR=/Users/daniellaloush/dandush03/ArborLM/data/wikitext2 ARBORLM_EXPERIMENTS_ROOT=/Users/daniellaloush/dandush03/ArborLM/experiments uv run --locked --extra pilot pytest tests/test_p8_panel.py tests/test_p8_eval.py tests/test_p8_sim.py tests/test_p8_analysis.py -q -rs` gave **44 passed, 0 skipped** (24.5 s; `outputs/eval_sim_analysis_pytest.log`).

## Item 4: the implementer's interpretations

| # | Interpretation | Ruling | Reason |
|---|---|---|---|
| i | Branch utilization counts both visited branches; top-branch-only figures shown alongside | ACCEPT | The ADR does not specify. The figures are descriptive, both are reported, and both are verified. |
| ii | Tree L-BCOAX is paired with flat L-COAX; classification uses L-COAX only | ACCEPT | Flat memory has no L-BCOAX. §7.2 makes L-BCOAX reporting-only. This follows ADR-0014's precedent. |
| iii | Parent count uses the parent E-ratio | ACCEPT | This is the literal §7.2 definition. |
| iv | LOC clauses, including the 5-of-6 pair count and the parent count, are applied at each of the four conditions | ACCEPT | E, and therefore the pair counts, depend on the condition. "At both settings under both tie rules" covers every clause, and this is the stricter reading. |
| v | "Beats optimized flat" needs LOCALITY-POSITIVE on both panels | ACCEPT | §7.4 says "both panels", and the §8 claim requires it. |
| vi | Retention is undefined only when the baseline mean is exactly 0 | REJECT (PENDING LEAD REVIEW) | MAJOR-2: a baseline mean ≤ 0 flips the sign and gives both false passes and false failures. |
| vii | An undefined U-ratio falls through to CONCENTRATION-ONLY or lower | REJECT (no practical effect) | With LOC true, rule 5 does not apply and rule 8 gives INTERMEDIATE (MINOR-1). This branch cannot be reached. |
| viii | Evaluate's git gate is tracked-and-clean, with an optional freeze commit | REJECT | MAJOR-1: in registered mode the freeze commit must be required and the source verified against it. |
| ix | Simulate requires the reproduction record | ACCEPT | The gate is real and not vacuous, and it is keyed to the source digest. It must be rerun on the frozen source. |

## Independent recomputation compared with the implementation

My tool is `independent_recompute_p8.py`. It reads only eval.json and sim.json, imports nothing from `arborlm`, and uses exact Fractions with Cramer's-rule OLS. Results against the implementation's analysis.json:

| Data | Cells | Values compared | Max abs diff | Mismatches | Classes reached |
|---|---|---|---|---|---|
| Implementer's full-size dry run | 60/60 | 2,060 | 0.0 | 0 | all QUALITY-FAILED (random memories); decision (c) |
| `stress_main` (perturbed copy) | 60/60 | 2,060 | 0.0 | 0 | COLLAPSED, CONCENTRATION-ONLY, LOCALITY-POSITIVE, WORSE, INTERMEDIATE, NOT REPLICATED; decision (b) |
| `stress_negbase` | 60/60 | 2,060 | 0.0 | 0 | as above plus the MAJOR-2 behaviour (both tools follow the literal ADR) |
| `stress_inc` (one sim.json removed) | 59/60 | 1,736 | 0.0 | 0 | study INCOMPLETE, C07 INCOMPLETE, decision "none" |

On the dry run, 288 of 288 M- and E-ratio conditions were defined and 256 of 288 ρ_adj were defined, so the comparison is not vacuous. The two tools disagree on nothing. The ADR-level disagreements are MAJOR-2 and MINOR-1, and in those cases my tool records the literal-ADR value plus an alternative flag.

## Commands run

Environment: macOS (Darwin 27.2.0), Apple M5 Max, uv 0.12.15, Python 3.12 (project `.venv`), torch from `uv.lock`, `--extra pilot`. `S=/private/tmp/claude-501/-Users-daniellaloush-dandush03-ArborLM--claude-worktrees-arborlm-consolidation-experiment-2b31c1/cfc0efd5-b7ca-4602-959a-07fe6b8d4e7d/scratchpad/audit2`.

```sh
uv run --locked --extra pilot python -m arborlm.p8_sim p7b-reproduction --experiments-root /Users/daniellaloush/dandush03/ArborLM/experiments --out $S/repro/repro.json   # ALL_EQUAL, 5.6 s
uv run --locked --extra pilot python $S/repro/perturb.py "<stream|counter>" /Users/daniellaloush/dandush03/ArborLM/experiments   # DIFFERENT x3 (one failed attempt, see failed_attempts/)
uv run --locked --extra pilot python -m arborlm.p8_eval evaluate --dry-run --out-root $S/dry/eval             # 60/60, 136 s wall, peak worker RSS 0.86 GB
uv run --locked --extra pilot python -m arborlm.p8_sim simulate --dry-run --eval-run $S/dry/eval/P8ED-… --out-root $S/dry/sim   # 60/60, 141 s
uv run --locked --extra pilot python -m arborlm.p8_analysis analyse --dry-run --eval-run … --sim-run … --out-root $S/dry/analysis
python3 -I docs/reviews/p8-preflight-2026-11-14/independent_recompute_p8.py --eval-run … --sim-run … --analysis …/analysis.json --out $S/recompute_p8_dry_run1.json
uv run --locked --extra pilot python docs/reviews/p8-preflight-2026-11-14/independent_trace_stats_p8.py --eval-run … --sim-run …   # 2,076 values, 0 mismatches
python3 -I $S/stress.py <eval> <sim> $S/stress_{main,negbase} {main,negbase}; then analyse --dry-run [--allow-incomplete] and the recompute tool on each
```

## Files written

All files are new, under `docs/reviews/p8-preflight-2026-11-14/`:
- `AUDIT_EVAL_SIM_ANALYSIS.md` (this report)
- `independent_recompute_p8.py` (reusable unchanged after the real run)
- `independent_trace_stats_p8.py`
- `failed_attempts/eval_sim_analysis_auditor_attempts.log`
- `outputs/`:
  - `recompute_p8_dryrun_run1.json`, `recompute_p8_dryrun_run1_summary.log`
  - `recompute_p8_stress_{main,negbase,inc}_summary.json`, `recompute_stress_fixture_builder.py`
  - `independent_trace_stats_p8_dryrun_run1.log`
  - `p7b_reproduction_auditor_rerun.json`, `p7b_reproduction_perturbation_check.py`
  - `eval_sim_analysis_pytest.log`, `eval_sim_analysis_audited_source_hashes.txt`
