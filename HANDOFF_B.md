# HANDOFF_B — fix lane B (stages, ledger, budget, freeze, rehearsal, calibration, recomputation, gates, launch scripts)

Claude (Sonnet 5.5) implementation, self-checks only; Astra review: NOT_PERFORMED; not independent review and not a human approval. Branch `claude/p10-s2-fix-B`, based on `e7a397e`.

This file lists (1) the interfaces lane B codes against in files it does not own, with the exact change wanted, (2) tests of other lanes' files that fail because of lane B's interface changes, (3) points that need
the lead. Nothing in a file outside lane B's list was edited.

## 1. Changes wanted in files lane B does not own (file, function, what, why)

### Lane A (`datagen.py`, `fetch.py`, `core.py`, `data.py` ...)

1. `studies/p10s2/datagen.py`, `run`/`main` — charge and cap the data-generation step on the ONE study ledger. Lane B's interface (`studies/p10s2/ledger.py`, already in this branch):
   ```python
   from .ledger import Ledger
   led = Ledger()                                   # experiments/P10S2/ledger.jsonl under core.ROOT
   led.refuse_if_over(args.stage_cap_seconds / 3600.0, None, "data generation")   # refuse to start without room
   with led.measure("datagen", process="data generation"):        # start marker first, end entry even on failure
       ...                                                        # and enforce the cap while it runs: stages.StageGuard("datagen", cap_seconds=args.stage_cap_seconds)
   ```
   `Ledger.charge(stage, seconds)` records a finished charge directly; `charge(stage)` with no seconds is the same context as `measure`. The fetch step: kind `"fetch"` (already in `STAGE_KINDS`). Why: audit B B3 — datagen
   wrote no ledger entry and ignored `--stage-cap-seconds`, so the freeze could never pass and P was understated by 1.0-1.8 h.
2. `datagen.py` output layout that lane B's pre-freeze commands read (unchanged from the current layout): `<out>/bundle/` (the `write_bundle` files plus `manifest.json`) and `<out>/prefreeze_record.json`
   (`launch/*.sh` pass `--data-dir "$RUN_DIR/data/bundle"`; `prefreeze-gates` and `freeze` read `<run-dir>/data/prefreeze_record.json`).
3. `studies/p10s2/core.py` — (a) `SeedPlan.code_seed()` should record its use (a public `core.record_seed(seed, purpose, mode)` or equivalent), and `core.seed_gate([], [])` should not be ok. Lane B does not depend on
   either: `gates.record_code_seeds` records the +10 seeds itself through `core.seeded_generator` and `gates.g9` refuses an empty record on its own. (b) The partition seed set must include 220912 (the lead's ruling);
   `gates.LISTED_PARTITION_SEEDS` is `range(220901, 220913)` and `gates.g9` refuses any of them in a `registered-run` process. (c) 220906 in the analysis stage: lane B's `gates.analysis_seed_check(records)` accepts
   a record whose seeds are all 220906, whatever mode label lane A / lane C give it (it reads the seed value), and `stages.stage_analysis` calls it on the seeds drawn during the analysis.
4. `core.py` `seed_gate` is still called by `gates.g9` with its current signature `seed_gate(records, planned, planned_mode=, extra_foreign=)`; if lane A changes that signature, `gates.g9` is the one caller.

### Lane C (`analysis.py`, `cells.py`, `classes.py`, `report.py`, `output.py`, `evaluate.py` ...)

5. `analysis.py`, `analyze_with_recomputation` — superseded by `recompute.outcome_under_recomputation(registered_study, recomputed_study_or_None, mode, memory_exceeded=False)` (lane B, in this branch), which
   compares EVERY recomputed quantity (cells, `baseline`, per replicate `assembled`, `retrieval`, `routers`, `ensemble`) and every verdict (gates, classes, annotations, composition, GEN, CONTROL-FAILED, label)
   through `recompute.verdict_view`. `stages.stage_analysis` calls it; it does not call `analyze_with_recomputation`. Lane C may delete the old function or reimplement it as a call to the new one. Lane B needs
   from `analysis`: `analyze(study, recompute_ne=None)` (same signature), `strip_classes_if_incomplete(out)`, `outcome_record(outcome)`; the keys of `analyze`'s output that `recompute.verdict_view` reads are all keys
   except `design`, `recomputation`, `cost_lines`, `not_evaluated_reasons`, `reasons`, `oracle_line`, `combined_line`, `label_with_design`, `by_construction` (numbers are dropped, strings with a numeral are dropped
   except under the keys `control_failed`, `cell`, `replicate`, `router_tasks`, the lists `engineering` and `incomplete` are compared by length). If lane C adds a verdict key whose strings carry numerals, add it to
   `recompute.KEEP_STRING_KEYS`.
6. `analysis.py`, `analyze` — a failed G2 and a failed G3 should be ENGINEERING-FAILURE / NOT_EVALUATED as §11 defines (audit C), and a gates record that is empty or lacks a gate must not read as passed. Lane B
   already passes `engineering=[...]` notes for a missing gates record or a gate with no record (`stages.gates_problems`), so the analysis labels it ENGINEERING-FAILURE without lane C's change.
7. `analysis.py` — the bootstrap intervals draw seed 220906 in the analysis stage only, "a fresh generator per printed interval in the registry's order". `stages.stage_analysis` records the seeds drawn during the
   analysis in `<run-dir>/seeds/analysis.json` and fails the stage if any is not 220906.
8. `cells.py`, `train_replicate` — optional: an `on_record(label, record)` callback and a per-cell `try/except`, so that a cell's record is written as it completes. Lane B does not need it: `train.train_arm` now
   never raises out of a cell (a device error, an out-of-memory, a stop request end the cell as a kept `failed` record) and `stages._recover_records` rebuilds a replicate's records from its snapshots after any other
   exception.
9. Names lane B calls (keep them): `cells.train_replicate, stage0_scores, build_routers, score_replicate, assembled_scores, retrieval_scores, router_record`; `evaluate.score_panel, timing_benchmark, general_by_construction`;
   `combined.score_combined_cell, check_continuation`; `worldio.build_world, read_bundle, write_bundle, RunConfig.registered(layer, updates, store_lr, lora_lr, device)`.
10. `evaluate.py`/`cells.py` combined-task scoring: lane B measures the combined scoring inside the real `stages.stage_evaluate` on the rehearsal world, so the rehearsal's combined time follows lane C's implementation
    with no further interface. `Rates.combined_cell_seconds` and `combined_stage0_seconds` are now 0 (folded into the measured replicate time); the budget formulas still carry the fields.

## 2. Tests in other lanes' files that fail because of lane B's interface changes (not edited)

From `pytest tests/test_p10s2_*.py` on this branch alone (lane A and C changes are not merged). Each is superseded by a lane-B test of the same property under the new interface; the lead should delete or port them at the merge.

- `tests/test_p10s2_combined.py::test_rehearsal_scorings_never_touch_e_c_or_any_registered_panel_and_check_the_continuation` — calls the old `rehearsal.measure_rates(world, 0, updates=, full_updates=, overhead=, timing_items=)`. The new signature needs
  `gates2_seconds`, `scratch`, `data_dir` and the scoring half runs in a child process (`rehearsal._probe`). Superseded by `tests/test_p10s2_dry.py::test_rehearsal_measures_the_registered_stage_functions_on_d_cal_and_feeds_the_rate_rule`, which
  runs the same poisoned world (`poison_world` imported from the combined tests), the continuation check and the combined rate fields.
- `tests/test_p10s2_prefreeze.py` (the launch-script and freeze tests; the fetch-guard tests in the same file are lane A's and unaffected):
  - `test_every_launch_script_exists_is_executable_and_parses_as_shell` — the new `prefreeze_gates.sh` (superseded by `tests/test_p10s2_launch.py`).
  - `test_freeze_writes_the_frozen_plan_and_cap_files_and_verify_plan_checks_every_identity`, `test_freeze_records_the_cap_raise_and_binds_it`, `test_freeze_refuses_not_started_budget_a_registered_seed_and_missing_inputs`,
    `test_the_study_stops_before_the_freeze_when_teachers_or_data_do_not_qualify`, `test_the_freeze_refuses_while_a_prefreeze_cap_is_provisional_and_replaces_it_with_twice_the_measured_time` — they call
    `write_freeze(..., design_layer=, store_lr=, lora_lr=)` and `budget.record_raise(proposal, path, ledger)`; the new `write_freeze` takes no typed design value and `record_raise` recomputes the amount (superseded by
    `tests/test_p10s2_fixB_freeze.py` and `tests/test_p10s2_budget.py`).
  - `test_registered_stage_refuses_without_a_freeze` — passes `--repo` (removed from the registered parser) and asserts `plan.json` and `stage_caps.json` do NOT exist under `core.ROOT`, which fails once the freeze commit adds them
    (audit B M11). Superseded by `tests/test_p10s2_fixB_stages.py` (parser has no override; refusal before anything) and `tests/test_p10s2_fixB_e2e.py`.
- `tests/test_p10s2_core.py::test_only_the_output_module_prints` failed on `e2e.py` and `rehearsal.py` printing directly; fixed in lane B's files (they write to `sys.stdout`), no change wanted.
- `tests/test_p10s2_classes.py` uses `analysis.analyze_with_recomputation`, `recompute.compare_cells`, `reported_cells`, `outcome_changes`: all still exist and pass. `outcome_changes` now reads verdicts through `verdict_view` (numbers dropped);
  its returned paths still begin with the outcome key (`classes/...`, `label`).

## 3. For the lead

See the final report: readings made by lane B (quoted there, not chosen silently) and PENDING LEAD REVIEW points.
