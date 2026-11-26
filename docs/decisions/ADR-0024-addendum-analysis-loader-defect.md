# ADR-0024 addendum — P10-I-S1 — the analysis loader defect and the supplement driver

**Status: ADDENDUM, 2026-11-21. The route (c) below was ruled by the lead under the human lead's delegation for S1, on the independent audit's recommendation (`experiments/_scratch/audits/AUDIT_P10IS1_CAP_EXTENSION.md`), BEFORE any outcome value of P10-I-S1 was read by anyone and before the analysis was run in any form. The human lead may overrule it in favour of an amending freeze (route (a)). The text and the driver are not reviewed. No registered stage is started by this text.**

`Astra review: NOT_PERFORMED`

## 1. The defect

`studies/p10is1/stages.py::build_registry` (frozen, registry of the analysis) reads every file of `run_dir/baselines/*.json` with `core.read_record(p, "baseline")`. The baselines STAGE MANIFEST is written by `execute_stage` to `run_dir/baselines/manifest.json` (kind `stage_manifest`), whether the stage ends PAUSED or COMPLETE. `read_record` raises `ValueError: expected a 'baseline' record, got 'stage_manifest'`; `ValueError` is not a `StageRefused`, so `cmd_registered` does not catch it and the registered `analysis` stage dies with a traceback and no record; `report` then dies on the missing `analysis/analysis.json`. The ADR asks for a status, never a crash. Both crashes occurred on 2026-11-21 in the registered run: **the registered analysis stage was launched once, at 10:45 local, and crashed inside `build_registry`, before `analysis.analyze`, so it produced no value** (its seconds were charged to the `analysis` cap key); the report stage, launched three seconds later, crashed on the missing `analysis/analysis.json`. The captured output is `experiments/P10IS1-registered-20261121-stages.out`, in which **each stage's output was cut to its last 1,500 bytes**: the file holds the tail of each traceback (the analysis section begins with a caret line, the report section in the middle of a frame line) and no `Traceback (most recent call last):` header. It was reproduced on a tiny synthetic run (`tests/test_p10is1_evaluate_cap_extension.py::test_known_defect_the_analysis_registry_refuses_the_baselines_stage_manifest`). It recurs whenever `baselines/manifest.json` exists, so it recurs after the baselines stage is COMPLETE.

## 2. Why the rehearsal, the tests and the audits missed it

- The counting rehearsal runs the seven record-producing stages through `execute_stage` and then calls `analysis.analyze(synthetic_registry_for(pl))`, a registry built in memory from the plan's labels; it never called `build_registry` on a real run directory.
- `run_synthetic` runs the baselines stage through `execute_stage` but, by its docstring, does not run the analysis; the tests that call `do_analysis` or `build_registry` use run directories in which no baselines stage manifest exists. No test combined the two.
- The audits examined the quiet rule, the freeze and the rehearsal records, not the loader's inputs. The independent recomputation's own loader crashed on the same file and was patched around without being connected to the study's `build_registry`.

## 3. The routes

(a) A one-line fix (`glob("d*_f*.json")`) under `studies/p10is1` and an amending freeze: a new plan, a new freeze record, a counting rehearsal naming the new plan file, a new Decision 2. Heavy for a defect that cannot touch any value.
(b) Moving or renaming `baselines/manifest.json`: tampering with the run directory; rejected.
**(c) RULED: an out-of-tree driver** (`results/p10is1-analysis-supplement-20261121/run_analysis_supplement.py`, a new file outside every frozen root, so the identity checks stay green), following the P10-S1 ADR-0021 section 25.21 precedent. Nothing under `studies/p10is1`, the plan, the config or the freeze changes.

## 4. What the driver does (and does not)

- Runs the registered pre-checks (`check_preconditions`, `load_registered_plan`, `verify_plan`, `require_decision_2`, `require_ignored_run_dir`: the same frozen functions as `cmd_registered`); refuses unless the evaluate and baselines stage manifests are COMPLETE.
- Builds the registry by calling the FROZEN `stages.build_registry` unchanged, on a path object (`RunDir`) whose `baselines/` directory lists only baseline record files (`d<draw>_f<facts>.json`, never `manifest.json`). That is the only difference from the registered loader; every other read is the frozen function's, including `rehearsal_record_of` (the R2 table), the quiet-stage statuses and the `*/manifest.json` statuses.
- Calls the FROZEN `analysis.analyze` and `report.render` unchanged on that registry.
- Writes ONLY to a NEW directory beside the run (`<run dir>-analysis-supplement`, or `--supplement-dir`): `analysis/analysis_supplement.json`, `report/REPORT_SUPPLEMENT.md`, `ENGINEERING_STOP_ANALYSIS_LOADER_DEFECT.json`, `SUPPLEMENT_MANIFEST.json`. Never under the run directory (not `analysis/`, not `report/`), never overwriting (it refuses if the directory exists).
- Labels every output: **"frozen analysis function on the registered records, through a disclosed corrected loader — not the registered analysis stage"**.
- Records the registered analysis and report stages as **ENGINEERING STOP — ANALYSIS LOADER DEFECT**, with the two captured traceback TAILS: the lines between `=== analysis <date>` and `=== analysis exit=`, and between `=== report <date>` and `=== report exit=`, keeping only frame lines, indented source and caret lines and the final exception line, and dropping every line that begins with `{` (the file also holds stage result lines, which never reach an output; tested on a fixture with the real file's structure). The record says that these are the truncated tails that were captured, and the driver refuses unless exactly two are found.
- `--supplement-dir` is refused inside the repository or worktree (it would dirty the tree and break every later identity check). The analysis is deterministic, so a second supplement directory carries no selection risk, but **any second supplement directory is disclosed** in the outcome record, with the reason.
- The supplement is a disclosed substitute, not the registered analysis stage; the outcome record must say so, and that the registered stages did not run.

## 5. Verification (no outcome value)

- The corrected loader's registry equals, field for field, the registry of the frozen `build_registry` with its one glob line fixed IN MEMORY (a compiled copy of its source; the tree is untouched), on a synthetic run and on the counting rehearsal's run directory (`experiments/P10IS1-counting-20261121`, rehearsal draw, read-only; 3 baselines, all cells); the unpatched frozen function raises on both.
- `verify_resume_identity.py` stays green after the commit that adds the driver (tested on a throw-away frozen repository and run on the real run directory).
- Tests: `tests/test_p10is1_analysis_supplement.py`.

## 6. Does anything else read `analysis/analysis.json` or the registered report? Can throughput still run as registered?

`analysis/analysis.json` is written by `do_analysis` and read by `do_report` only (a static test over `studies/p10is1/*.py` and over the functions `cmd_registered`, `execute_stage`, `_execute_stage_body`, `measure_throughput`). The throughput branch of the stage body calls neither, and the registered pre-checks do not look at it. So **the throughput stage can still run as registered**; it needs only the gates record and a quiet machine, and the registry reads its record when it exists (`quiet.throughput_label`). Because the supplement's report prints the throughput state, it is best run AFTER throughput.

## 7. Command (the lead's; after evaluate and baselines are COMPLETE, and throughput if wanted; not run by the author)

`PYTHONPATH=<worktree>/src:<worktree> timeout 3000 <venv python> results/p10is1-analysis-supplement-20261121/run_analysis_supplement.py --run-dir /Users/daniellaloush/dandush03/ArborLM/experiments/P10IS1-pre-20261118 --freeze-commit 46bf55a5cc0eda11b7201c4ab777e69c6970c4cd --stages-out /Users/daniellaloush/dandush03/ArborLM/experiments/P10IS1-registered-20261121-stages.out`

The independent recomputation compares with `analysis_supplement.json` once pointed at it.
