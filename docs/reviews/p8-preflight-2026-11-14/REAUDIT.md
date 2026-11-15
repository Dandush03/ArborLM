# P8 pre-freeze narrow re-audit (training + eval/sim/analysis fixes)

- Auditor: Claude Opus 5.5 (`claude-opus-5-5`, from session metadata). Independent engineering evidence only: **not Astra validation, not human approval**. `Astra review: NOT_PERFORMED`.
- Date: 2026-11-14 UTC. Worktree HEAD `74851bd30546ae1cafacaf6e330e191016721f3a` (all P8 source untracked).
- Scope: verify the fixes requested by `AUDIT_TRAINING.md` and `AUDIT_EVAL_SIM_ANALYSIS.md` and the lead's rulings in ADR-0015 revision 3. Real Panel A/B were not opened, traced or evaluated. No real P8 training was run. Only synthetic `--dry-run` data was used.
- Environment: uv 0.12.15, Python 3.12.14, macOS arm64. `uv.lock` 07c61871…a81d and `pyproject.toml` d1be91a1…0439 are unchanged from the first audits.

## Verdict: **READY TO FREEZE**

There are no blocking items. Every MAJOR and every adopted MINOR is fixed. Training MINOR-6 is still open, as the lead decided (λ = 0 reason label only). Four non-blocking observations are listed at the end.

## 1. Files the audits examined

| File | Audited hash | Now |
|---|---|---|
| `p8_objective.py` | b48bf53d…f25e | **b48bf53d1ce3a3eaeef0502b4304022c9c417427795d00e214d8c26243bef25e**, identical |
| `p8_checkpoint.py` | 7923516a…713e (both audits) | identical |
| `p8_panel.py` | 73578c86…e020f (eval audit) | identical |
| `p8_core.py`, `p8_train.py` | 552c7eca… / f263f600… (eval-audit list); d3a8e949… / 71f6362b… (training audit) | identical to the eval-audit list. They changed after the training audit, and no copy of those versions survives, so §3 checks the change by behaviour. |

Full list: `outputs/reaudit_examined_hashes.txt`. I rechecked it with `shasum -c` at the end of the audit: ALL_UNCHANGED.

## 2. Fixes verified by reading the code and running it

**Training audit**

- **MAJOR-1**
  - `RETENTION_MIN, QUALITY_PAIRS_ABOVE_MAX, E_NULL_FLOOR = 0.75, 1, 0.05` are in `p8_core.py:131`, `_REGISTERED["margins"]` (213-215) and the config `[margins]` (104-106).
  - `gain_min`/`GAIN_MIN` is gone everywhere.
  - The analysis uses the core constants. `T_NULL_FLOOR` is a `Fraction(1,20)` literal, and `test_margin_constants_and_agreement_with_analysis_module` pins it equal to the core constant.
- **MAJOR-2: the `restore-gate` subcommand** (`p8_train.py:849-907`)
  - It runs the ten `b101-o301-s601-C01…C10` cells as supervised subprocesses.
  - `passed` requires all ten workers to have exited with code 0, a result file for each, and `final == recorded == checkpoint` digests.
  - It refuses if `restore_gate.json` exists. It writes only `restore_gate.json` and `restore_gate/`.
  - Run on a fresh 10-cell dry run: PASSED 10/10. All 40 stage files (30 checkpoints and 10 train.json) had the same sha256 after the gate as before.
  - Tampered copy (C03 cell deleted, C05 recorded step-512 digest altered): `passed: false`, with C03 and C05 failed and the other eight passed. A rerun on the existing record was refused. Output: `outputs/reaudit_restore_gate_checks.json`.
- **MINOR-1:** the p5-invariance gate checks the local `checkpoint-512/state.pt`, `index.json` and the local `result.json` against the committed P5 record (`p8_train.py:930-938`).
- **MINOR-2/3:** a missing file in the freeze commit is reported as a `FreezeError`, and `uv.lock` and `pyproject.toml` are now bound (`p8_train.py:88-96`).
- **MINOR-5:** `--continue-after-failure` without `--dry-run` is refused with exit 2 (`outputs/reaudit_registered_stage_refusals.log`).

**Eval/sim/analysis audit**

- **MAJOR-1, freeze binding.** `p8_pool.require_freeze` is called non-optionally by eval `run_stage`, sim `run_stage` and `run_analysis`, and the train stage calls `verify_freeze` directly. It covers `src/arborlm/*.py`, the config, the spec, `uv.lock` and `pyproject.toml`.
  - `git_gate` raises if there is no freeze commit.
  - Sim and analysis also require the eval manifest to have the same freeze commit and the same source digest as the current source.
  - Observed: each registered stage refused without `--freeze-commit`, and refused with `--freeze-commit HEAD` (FreezeError listing every differing file). No run directory was created.
- **MAJOR-1, provenance.** `check_provenance` (`p8_analysis.py:387-425`) runs whenever `dry_run` is given, which is always the case from `run_analysis`.
  - Fixtures that changed one record's `source_sha256`, `dry_run` flag or `panel_record_sha256` were each REFUSED, with no output written.
  - **MINOR-6 (TOCTOU):** the eval worker re-hashes the panel record against the job's hash (`p8_eval.py:326-327`).
- **MAJOR-2, retention.** `retention()` returns undefined when the baseline mean is ≤ 0 (`p8_analysis.py:273-279`). An undefined input makes `quality_guard` fail.
- **vii, LOC with undefined U-ratio:** returns INTERMEDIATE (`p8_analysis.py:163-165`).
- **ii:** the reason text now says "null mean … < 0.05".
- **iii:** first-touch and cold-miss columns were added.
- **iv:** the sim per-cell deadline is the stage time remaining.
- **Decision map** (`decision_option`, `decision_inputs`). The order is: (a) if C07/C09 has an architecture advantage; else (b) if C06/C08 is LOCALITY-POSITIVE and beats optimized flat; else (c). If the controls bind, the result is (c). An INCOMPLETE study gives "none". `open_questions` lists NOT REPLICATED and INTERMEDIATE cases, and these do not void (a) or (b). This matches ADR §8 revision 3 as I read it.

## 3. Training trajectory unchanged

I read `cells()`, `seed_everything`, `build_model`, `advance` and the `train_step_p8` call path.

Behavioural check:
- I ran a fresh dry-run stage of the ten s601 cells with the fixed source.
- I compared the result with the training audit's pre-fix dry run of C01, C02 and C10 (`outputs/training_dry_stage3_manifest.json`, source ee6645b3…).
- **State digests at steps 0, 256 and 512: 9/9 equal. Backbone before/after: 6/6 equal.**
- The checkpoint *file* hashes differ (9/9), as expected, because the files embed the source identity.

Tool: `outputs/reaudit_compare_train_digests.py`. Log: `outputs/reaudit_train_digest_compare.log`.

## 4. Independent recomputation, tool v2 (sha256 dc3e7269…1acb, unchanged)

All runs used a fresh dry run of the fixed implementation. The stress fixtures were rebuilt from it with `outputs/recompute_stress_fixture_builder.py`. `stress_inc` is `stress_main` with `b101-o301-s601-C07/sim.json` removed and analysed with `--allow-incomplete`.

| Fixture | Values compared | Max abs diff | Mismatches | Outcome (both tools) |
|---|---:|---:|---:|---|
| Fresh dry run | 2,060 | 0.0 | **0** | all QUALITY-FAILED, decision (c) |
| stress_main | 2,060 | 0.0 | **0** | C06, C09 LOCALITY-POSITIVE; decision (b); open_questions [C10] |
| stress_negbase | 2,060 | 0.0 | **0** | C04, C06, C08 QUALITY-FAILED (retention undefined); decision (c) |
| stress_inc | 1,736 | 0.0 | **0** | INCOMPLETE 59/60; decision "none" |

The tool does not compare `open_questions`. I checked them by hand: [C10] in all three stress fixtures, as expected. Summaries are in `outputs/reaudit_recompute_summaries.json`.

## 5. Tests and lint

- `ARBORLM_DATA_DIR=… ARBORLM_EXPERIMENTS_ROOT=… uv run --locked --extra pilot pytest tests/test_p8_*.py -q -rs`: **123 passed, 1 skipped** in 33.7 s (`outputs/reaudit_pytest.log`).
- The skipped test reads `ARBOR_EXPERIMENTS_ROOT`, not `ARBORLM_…`. It passed when I ran it with `ARBOR_EXPERIMENTS_ROOT` set (`outputs/reaudit_pytest_local_rows.log`).
- `ruff check` on the P8 files: clean. `mypy src/arborlm`: no issues in 85 files.

## Non-blocking observations (not defects of the fixes)

1. `restore-gate` does not itself call `verify_freeze`, and it does not check that the run is a registered (non-dry) run. It relies on the stage's own freeze record. The runbook should point it at the registered `P8TS-*` run.
2. The eval worker hashes the panel record and then reads it in two separate steps. This leaves a residual microsecond TOCTOU window, which is negligible.
3. The ADR §8 text for (b) does not repeat "beats optimized flat". The code and the lead's ruling both require it, and §7.4 says it is required for a positive reading. **PENDING LEAD REVIEW** only as a wording consistency.
4. The skip-condition environment variable name `ARBOR_EXPERIMENTS_ROOT` differs from the `ARBORLM_*` convention, so the default run skips that test.

## Commands (S = scratchpad/reaudit)

```sh
uv run --locked --extra pilot python -m arborlm.p8_eval evaluate --dry-run --out-root $S/eval          # 2:14
uv run --locked --extra pilot python -m arborlm.p8_sim simulate --dry-run --eval-run $S/eval/P8ED-… --out-root $S/sim   # 2:04
uv run --locked --extra pilot python -m arborlm.p8_analysis analyse --dry-run --eval-run … --sim-run … --out-root $S/analysis
uv run --locked --extra pilot python -I docs/reviews/p8-preflight-2026-11-14/independent_recompute_p8.py --eval-run … --sim-run … --analysis …/analysis.json --out …
python3 -I outputs/recompute_stress_fixture_builder.py <eval> <sim> $S/stress_{main,negbase} {main,negbase}
uv run --locked --extra pilot python -m arborlm.p8_train stage --dry-run --labels b101-o301-s601-C01..C10 --workers 4 …   # 1:35
uv run --locked --extra pilot python -m arborlm.p8_train restore-gate --run-dir $S/train/P8TD-… …                         # 0:50
```

There were no failed checker attempts in this re-audit. One shell command, which would have built the provenance fixtures with `rm -rf`, was blocked by a safety check. I rebuilt them in new directories without any removal.
