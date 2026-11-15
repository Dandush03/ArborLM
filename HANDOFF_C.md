# HANDOFF_C: what lane C needs from files it does not own

Lane C (analysis, classes, report, output, routing, evaluate, cells, combined, retrieval, memory, model). Self-check only: not independent review, not Astra validation, not human approval. Astra review: NOT_PERFORMED.

## 1. The verdict function for lane B's recomputation (`studies/p10s2/analysis.py`)

```python
analysis.verdicts(study: Mapping[str, Any]) -> dict[str, Any]
analysis.verdicts_of_outcome(outcome: Mapping[str, Any]) -> dict[str, Any]
analysis.verdict_changes(a: Mapping, b: Mapping) -> list[str]      # the paths whose verdict differs
```

- Pure: no file access, no randomness, no interval, no seed draw. `verdicts(study)` is `verdicts_of_outcome(analyze(study))`.
- Flat mapping of path to a boolean, None (NOT_EVALUATED) or a word. No number enters it. Paths: `label_row`, `label`, `control_failed`; `gate/G1..G9` (True, False, or None if the record is missing); `ensemble/r<k>`; `class/<mechanism>/<order>`; `cell/<mechanism>/<order>/<replicate>/{acq1,acq2,ret,neg_acq,neg_ret,rejected,below_floor}`; `annotation/<name>` (booleans only; APPEND COST is a number and is excluded); `composition/<C1|C2>/<arm>`; `gen/<cell>/{registered,first_marker,both}` (GEN under each decision and under both); `gen_status/<mechanism>/<order>` (holds, fails, not_evaluated); `control/<cell>/<panel>/<value_perm|code_perm>` (True: CONTROL-FAILED, None: control not evaluated).
- `analysis.analyze_with_recomputation` now compares registered and recomputed verdicts with `verdict_changes` (not `recompute.outcome_changes`), so a difference within tolerance in a number that feeds APPEND COST no longer changes anything (C-M3 a), and the GEN gate of every snapshot, `control_failed` and every control are compared (C-M3 b).
- Optional new argument `recomputed_study=` (a full study record assembled from `recompute/`, as `stages.assemble_study(..., subdir="recompute")` does): if given, the recomputed analysis uses its `baseline` and each replicate's `assembled`, `retrieval`, `routers`, `ensemble` instead of the registered ones (B-M9). **Needed in `stages.py` (lane B):** `stage_analysis` must pass `recomputed_study=rec_study` where it builds `rec_study`. Lane B still owns the comparison of those records under tolerance in `recompute.compare_cells`: this function only makes the recomputed verdicts honest.
- `recompute.outcome_changes` is no longer called by `analysis.py`; lane B may keep it or make it call `verdict_changes`.

## 2. The analysis stage must switch the intervals on (`stages.py`, lane B)

- `analysis.analyze(..., bootstrap_mode=..., bootstrap_resamples=None)` and `analyze_with_recomputation(..., bootstrap_mode=...)`: with `bootstrap_mode=None` (the default) no interval is computed and listed seed 220906 is not drawn, so it is drawn in the analysis stage and nowhere else. **`stage_analysis` must pass `bootstrap_mode`**: `"test"` in tests and the dry stage, anything else (`"registered-run"`) in the registered run. Without it the report prints "Table 5 ... NOT_EVALUATED (not computed)".
- `analysis.bootstrap_generator(mode, name)` makes one fresh generator per printed interval via `core.seeded_generator(...)`: seed 220906 (`core.PARTITION_STREAMS["bootstrap"]`) with seed mode `"registered-data"` (the only existing mode that allows it), or the test stand-in `core.partition_seeds("test")["bootstrap"]` with mode `"test"`. **Gate G9 (lane A or B):** the ruling says G9 lists 220906 for the analysis stage; today `core.allowed_seeds` allows it only under "registered-data". Add an explicit analysis-stage seed mode in `core.py` and have `g9`/`seed_gate` accept 220906 for it, then tell lane C (or the lead) to change the two lines of `analysis.bootstrap_generator` that name the mode. Until then the draws are recorded in `core.seed_record()` as mode "registered-data".
- Order of the intervals (fixed, documented in `analysis.interval_targets`): Stage 0 student and teacher panels (sorted by panel name), Stage 0 and ensemble combined records, every cell in registry order (its snapshot, then `@append`; each panel, then C1 and C2), the assembled arms and retrieval baselines of each replicate. A score with no per-item values, or a non-finite one, has no interval and draws nothing (printed NOT_EVALUATED).
- 10,000 resamples is `core.CFG["scoring"]["bootstrap_resamples"]` (the registered count; `bootstrap_resamples=` exists for tests only).

## 3. Changes of record shape that `recompute`, `stages` and the freeze see (all in files lane C owns)

- `evaluate.general_quality` records, besides `loss_increase` (the decision at token 64, as registered): `loss_increase_first_marker`, `nll_router_first_marker`, `false_trigger_count_first_marker`, `passes_registered_decision`, `passes_first_marker_decision`; `passes` is now the existing threshold under both (C-M6).
- `evaluate.score_panel(...).to_json()` records `reference_counts` and `single_reference` ({n, mean}). R-exact and R-icl now record `items`. `cells.router_record` records `general_prefixes` and each router's `training.held_out_piece_indices`; route accuracy on general prefixes is measured on those unseen WikiText-2 train pieces, not on the GEN windows (C-m7).
- `routing.train_router` draws the initialization from one +3 generator and the prefixes, lengths and batch order from a second fresh +3 generator (A-M5). `RouterSpec` has a new last field `general_prefix_count` (default 200, the number of GEN windows). Seed uses on +3 per router are now two ("router initialization", "router sampling"); the freeze's seed accounting (G9, `core.seed_record()` consumers) sees two uses, both in the listed set.
- Panels whose name starts with `E_open` (none exists today) are guarded: scored under the oracle route only, never in a gap, ablation or learned route (`cells.gap_panels`). **E_open is still never scored.** Scoring it needs `worldio.build_world` (unowned file) to add `E_open_A` and `E_open_B` `PanelData` to `ctx.panels` (prompts per task, the item's references per capability), and `data`/`prefreeze` to generate teacher outputs on E_open if a gap is wanted (the ADR says "descriptive only"). The report prints "E_open ... not scored in this record (NOT_EVALUATED)".

## 4. Changes needed outside lane C

- `stages.py` (lane B): (a) pass `bootstrap_mode` and `recomputed_study` as above. (b) `cmd_rehearse` line 388 printed an outcome containing "NOT STARTED: BUDGET" through `emit_plain`, which used to raise `OracleLineMissing`; `emit_plain` now routes any guarded-looking line through `emit` (printed under the oracle-assisted line) and never crashes, so no change is required, but the call should use `output.emit` if the line is a result. (c) `assemble_study` gives `gates: {}` when `gates.json` is absent: the label is now INCOMPLETE ("the gates record is missing"), as the ruling requires; the registered `train` stage should still refuse to run without a passed gates record (the audit's C-M2 second half, lane B).
- `gates.py` (lane B): `g2` writes `ok` = scored identically twice (undefined gaps listed separately); the analysis reads `G2.ok` and turns a failed G2 into ENGINEERING-FAILURE. A missing G2 is NOT required by the analysis (the brief lists G1 and G4-G9 as required; G2 only as a failure): see the ambiguity note in the report.
- `core.py` (lane A): nothing is required. `core.GUARDED_WORDS` is unchanged; `output.py` matches it case-insensitively and adds structural markers and key stems of its own (`output.KEY_STEMS`, `output.MARKERS`).

## 5. Tests of other lanes that fail or may fail because of lane C's interface changes

`pytest tests/test_p10s2_*.py` as a whole was run after the changes: 331 passed (measured), none failed. No test owned by another lane fails because of lane C's changes. Tests not owned by lane C that exercise lane C code and that lane B or the lead should re-check after the merge, because lane A and B change their own sides:

- `tests/test_p10s2_train.py` (topic "train", owned by nobody in the brief): `test_router_recipe_prefix_lengths_seed_order_and_scratch_initialization`, `test_router_separates_keyword_prompts_and_false_triggers_are_counted`, `test_general_quality_with_no_router_read_is_exactly_the_student`, `test_retrieval_baselines_and_ensemble`, `test_all_eighteen_cells_trained_and_scored_with_the_right_sections` call `routing`, `evaluate` and `cells`. They passed in lane C's run. None was edited.
- `tests/test_p10s2_dry.py` (topic "dry", lane B?): `test_dry_stage_end_to_end` runs the whole analysis and report on the dry stage. It passed in lane C's run, but `stage_analysis` there does not pass `bootstrap_mode`, so the report has "Table 5 ... NOT_EVALUATED" until lane B passes it.
