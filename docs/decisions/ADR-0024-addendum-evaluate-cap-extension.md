# ADR-0024 addendum — P10-I-S1 — a 1-hour extension of the evaluate cap, applied as a ledger credit

**Status: ADDENDUM, 2026-11-21. The extension is the human lead's decision (`results/p10is1-evaluate-cap-extension-20261121/APPROVAL.md`, quoting his words). The mechanism below is the implementer's and is NOT reviewed. No registered stage is started by this text. No outcome value of P10-I-S1 has been read by the author of this addendum; no sealed value was opened.**

`Astra review: NOT_PERFORMED`

## 1. What happened

The registered run (freeze commit `46bf55a5cc0eda11b7201c4ab777e69c6970c4cd`, run directory `experiments/P10IS1-pre-20261118`) has gates, timing, train and ladder COMPLETE. The evaluate stage charged 3,600.03 s against its cap of 1.0 h (`stage_caps.evaluate_hours`, frozen in `studies/p10is1/freeze/plan.json` and equal to the config's `[caps]`) with 12 of 110 cells not started; the baselines stage then returned PAUSED because **it shares the cap key `evaluate`** (`stages.CAP_KEY`: evaluate and baselines both map to `evaluate`; `stage_cap_seconds` = min(plan cap − seconds charged on the key, ledger remaining) = 0). The ledger holds the charged seconds (`experiments/P10IS1-ledger.json`).

The human lead, asked "Do you approve extending S1's evaluate cap by 1 hour so the last 12 cells can finish?", answered "Approve 1 h" (2026-11-21, in person, as relayed). ADR-0024 section 15: a cap is extended by the human lead on cost projections only; the total cap (52 h) is not extended and about 15.6 h of it are charged.

## 2. Why not an edit of the cap itself

The cap is in three frozen places: the plan's `stage_caps`, the config's `[caps]` (`verify_plan` refuses a difference) and the freeze record's hash of the plan. `check_preconditions` refuses unless `studies/p10is1/**`, the config and `uv.lock` at HEAD equal their content at the freeze commit, and `verify_plan` refuses any frozen file whose hash differs. So a change to the plan, the config, or any code under `studies/p10is1` (for example code that reads an "extension record") is PAUSED — IDENTITY for every later stage and worker; it would need a new freeze that amends the first. That route was not taken.

## 3. The mechanism: a ledger credit with an equal offsetting debit

`apply_extension.py` (beside the approval record, outside every frozen root) appends TWO entries to the run's ledger, changes none of the existing ones, and writes the ledger's pre-image to a new file first:

| stage | seconds | effect |
|---|---|---|
| `evaluate` | −3,600.0 | spent on the cap key `evaluate` falls by one hour: the effective evaluate-and-baselines cap is 2.0 h |
| `evaluate-cap-extension-offset` | +3,600.0 | a stage of NO cap key: the TOTAL charged seconds, and so the total cap's headroom, are exactly unchanged |

Both entries carry the SHA-256 of the approval record in their `run` field. The script is applied once (it refuses if the offset stage exists), refuses an approval record without the machine-read lines and the quoted answer, and asserts after writing that the total charged seconds are unchanged and every earlier entry is intact. Its default is a dry run.

**Disclosure.** The plan's frozen `stage_caps.evaluate_hours` stays 1.0, and `do_report` prints the plan's caps: the report will show 1.0 h for evaluate while the ledger shows the credit. The effective cap is 2.0 h as the ledger arithmetic reads it. This is a ledger adjustment, not a change of the frozen cap, and it is the reason this addendum and the approval record exist.

## 4. What stays valid (read-only check)

The resumed command performs, in this order (`stages.cmd_registered`): `gates.configure_worker`; `check_preconditions` (clean tree; the freeze commit an ancestor of HEAD; `studies/p10is1`, the config, `uv.lock` and the imported roots equal their freeze-commit content; platform of record); `load_registered_plan`; `verify_plan` (frozen file hashes, config caps equal plan caps, run directory, data manifests, freeze record, imported files); `require_decision_2`; `require_ignored_run_dir`; then `ledger.require_room` and the stage. `verify_resume_identity.py` runs all of these except the stage and prints each. **A commit in this worktree changes none of them** provided it touches only files outside `studies/p10is1/**`, `studies/p10s1`, `studies/p9*`, `src/arborlm`, the config and `uv.lock`, and leaves the tree clean: this addendum, the approval record, the two scripts and the tests are such files. The glob of Decision 2 (`results/p10is1-freeze-*/DECISION_2.md`) does not match the new `results/p10is1-evaluate-cap-extension-20261121/`. Completed cells, records and every ledger entry are untouched: the evaluate worker pool skips tasks whose done files exist.

## 5. What is unchanged

No scientific parameter, threshold, seed, cell, label rule, grid or run length; the plan, the config and the freeze record; the total cap; the other caps (train, timing, throughput, analysis).

## 6. Known defect, found while checking (NOT fixed here): the analysis stage crashes on the baselines stage manifest

`stages.build_registry` reads `run_dir/baselines/*.json` and requires each to be a `baseline` record, but `execute_stage` writes the baselines STAGE MANIFEST to `run_dir/baselines/manifest.json` (kind `stage_manifest`). So the analysis refuses with "expected a 'baseline' record, got 'stage_manifest'" **whenever `baselines/manifest.json` exists** (a PAUSED baselines stage writes one, and a COMPLETE one writes one too). It was reproduced on a tiny synthetic test-mode run (`experiments/_scratch/p10is1_evalcap_20261121/repro_analysis_defect.py`, output kept in `tests/test_p10is1_evaluate_cap_extension.py`): after `baselines` COMPLETE, `build_registry` raises. **It will therefore recur after baselines completes; the analysis stage cannot run on this run under the frozen code.** The ADR asks for a status, never a crash. The one-line fix (`glob("d*_f*.json")`) is a change under `studies/p10is1` and needs a new freeze amending the first, or a ruling; it was not made. The counting rehearsal never exercised `build_registry` on a real run directory (it analysed a synthetic registry), which is why it was not seen.

## 7. Resume commands (the lead's, in the worktree that holds the freeze, after this addendum is committed and the tree is clean)

1. `PYTHONPATH=<worktree>/src:<worktree> timeout 600 <venv python> results/p10is1-evaluate-cap-extension-20261121/verify_resume_identity.py --run-dir /Users/daniellaloush/dandush03/ArborLM/experiments/P10IS1-pre-20261118 --freeze-commit 46bf55a5cc0eda11b7201c4ab777e69c6970c4cd` (exit 0 required)
2. `PYTHONPATH=<worktree>/src:<worktree> timeout 300 <venv python> results/p10is1-evaluate-cap-extension-20261121/apply_extension.py --ledger /Users/daniellaloush/dandush03/ArborLM/experiments/P10IS1-ledger.json` (dry run; read it), then the same with `--apply`
3. `sh studies/p10is1/launch/evaluate.sh /Users/daniellaloush/dandush03/ArborLM/experiments/P10IS1-pre-20261118 46bf55a5cc0eda11b7201c4ab777e69c6970c4cd`, then `sh studies/p10is1/launch/baselines.sh ...` the same way; stop there (do not run `analysis` or `report` until section 6 is ruled on).
