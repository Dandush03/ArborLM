# ADR-0025 addendum: Part T's study budget bound raised to 151 h (the human lead's decision of 2026-11-21) and its carrier (ruling 46)

Status: **the bound is the human lead's decision**, recorded in `results/p10is2-partt-budget-bound-20261121/APPROVAL.md` (SHA-256 `2dd7aa9012e9c699714c3544ef6fa9a0c803e228ecf514085768aeeb5f39148e`) from the coordinator's message; the carrier (ruling 46) is a choice of the implementer for the lead's review. Existing ADR and addendum files are not edited. `Astra review: NOT_PERFORMED`.

## The decision

After calibration ended (U = 8,000, NOT CONVERGED AT U) the registered `candidate-plan` refused: total cap 150.17 h against the bound of 95.68 h (ruling 41), pre-freeze charge 9.633 h, counting allowance 18.26 h, stage caps 122.31 h; it wrote no plan. The human lead was asked whether to raise Part T's budget bound from 95.68 h to 151 h and answered, verbatim, in chat on 2026-11-21 (evening, local): **"Raise to 151 h"**.

**It covers only that:** `caps.study_budget_hours` = 151 h. It does not change any rule, threshold, grid, seed, cell count, U, padding factor or stage-cap rule; calibration is not repeated; ruling 33's check (a total above the bound still refuses) and rulings 20, 30 and 37 stand. It approves no result and no later step.

## Ruling 46: the carrier

**What had to be decided.** The bound is read from `configs/p10is2_partt.toml` (`caps.study_budget_hours`) by `require_study_budget` and `check_study_budget` (`candidate-plan`, `caps-config`, `freeze`). Calibration's record `calibration_0.json` carries the SHA-256 of every file of the Part T frozen set (41 keys, `planmod.frozen_file_hashes`). The question was whether changing the bound breaks the record's identity checks.

**Measured, read-only** (`experiments/_scratch/p10is2_budget_bound_20261121/identity_check.py`, run on this tree before and after the config edit): the checks the plan and the freeze apply to a calibration record are `calibration.code_identity_problems(record, frozen_files, files)` with `files` = the frozen `studies/p10is2/*.py` only (`partt_stages` around the freeze's "calibration records do not match the frozen files"; `calibration.repetition_used` uses the same). Before the edit: 0 problems, 0 differing keys of 41. After editing the one config line: **0 problems; exactly one differing key, `configs/p10is2_partt.toml`**, which no plan or freeze check compares against the record. The plan's own `config_sha256` and `frozen_files` are computed after the edit, so the plan, the counting rehearsal, the freeze and the registered stages (which compare against the plan and the freeze record, not the calibration record) hold on the edited config. The calibration therefore stays valid and is not rerun. Calibration's own session identity (ruling 31) covered the config during its sessions only; it has ended.

**Routes considered.**
1. **A new code path** (an approval-record input read by `candidate-plan`): any change to a `studies/p10is2/*.py` file, or a new one, makes the record's `.py` hashes differ from the frozen files ("the record's hash differs" / "carries no hash") and forces calibration's repetition (ADR-0025 section 7.1 rule 4). **Closed.**
2. **A config edit of the one named non-calibration key** (the bound; it is no training or scoring file). Touches `configs/p10is2_partt.toml`, which is in the calibration record's hash set but is not among the files the record's validity is checked on. **Chosen.**

**Mechanism.** (a) `caps.study_budget_hours = 151.0` in `configs/p10is2_partt.toml`, the comment naming the decision and the earlier 95.68. (b) The plan names the approval: the `--manifests` JSON of `candidate-plan` carries a third entry `budget_bound_approval` (`results/p10is2-partt-budget-bound-20261121/manifest_entry.json` holds it: `path` of `APPROVAL.md`, its `sha256`, `registered_bound_hours` 95.68, `approved_bound_hours` 151.0). The code records `manifests` in the plan verbatim and `planmod.verify_plan` re-hashes every manifest entry by `path` and `sha256` at every registered stage (a difference is PAUSED, IDENTITY); the freeze reads only `part_q_acceptance` and `panel_ledger` by name, so the extra entry is inert to the code and checked by hash. **Stated limit:** no code compares the config's 151 with the entry's `approved_bound_hours`; a test pins that the two and `APPROVAL.md` agree, and the audit checks it.

**Files changed:** `configs/p10is2_partt.toml` (one line, a calibration-record hash key; not a checked identity file), new `results/p10is2-partt-budget-bound-20261121/APPROVAL.md` and `manifest_entry.json`, this addendum, `tests/test_p10is2_partt_budget_bound.py`. No `studies/` file, `uv.lock` or `pyproject.toml` changed.

## Timing

The config line changes after calibration's end line; the candidate plan is written after an independent audit of this change; the counting rehearsal and the freeze follow the plan.
