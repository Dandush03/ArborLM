# P10-I-S2 Part Q, attempt 3: confirmation of 0306c8b (`git diff a7611cd 0306c8b`)

- **Auditor.** The `arbor-auditor` subagent, model Claude Opus 5.5 (`claude-opus-5-5`), 2026-11-19, 17:15–17:20 local time.
- **Method.** I read the diff by commit. The archive is at `/Users/daniellaloush/dandush03/ArborLM-sealed/audit-s2-a4/repo`. I ran only `tests/test_p10is2_reusecheck.py` and `tests/test_p10is2_gloss_segment_rule.py` (6.7 s), and no end-to-end test.
- **Limits observed.** No process of mine was left running. No git writes, no `/tmp`, no network. Nothing of attempt 2 was read. The only file outside the archive I touched was the preserved ledger copy, read for its hash.
- **Status.** This audit is independent engineering evidence. It is not Astra validation and not human approval. `Astra review: NOT_PERFORMED`.

## Verdict: READY FOR THE COUNTING REHEARSAL AND FREEZE. REUSE STILL CERTIFIED

## R1: attempt-3 caps in their own section: FIXED

**The config.**
- `[stage_caps_attempt3]` (reuse, regeneration, outputs, analysis, total) is new, all `0.0`.
- `[stage_caps]` and `caps.provisional` are **identical to `55017df`** (parsed and compared: the same nine values, `provisional = false`). The `reuse_hours` line of `a7611cd` is gone.

**The writers.**
- `apply_caps_attempt3` writes only inside `section_span("stage_caps_attempt3")`, and refuses unless each key reads exactly `0.0`. The pattern `0\.0(?![0-9])` cannot match `0.05`.
- `apply_caps` and `reset_caps_text` are now confined to `[stage_caps]`.
- `caps-config --attempt3 --apply` calls only `apply_caps_attempt3`. `caps.provisional` is never touched on that path.

**The readers.**
- `qplan.build_candidate` stores `stage_caps` from `[stage_caps_attempt3]` (and `caps_section`) when the inputs carry a `reuse` block.
- `common/plan.verify_plan` compares the config section that matches the plan.
- `cmd_freeze` compares `proposal_attempt3` with `[stage_caps_attempt3]`.
- `run_stage` reads `plan.data["stage_caps"]`, as before.

**The reuse check.** `reusecheck.CONFIG_FREE_SECTIONS` is now `{stage_caps_attempt3, paths.panel_ledger}`, and `config_diff` skips added keys under a free section. **Any edit of `[stage_caps]` or `caps.provisional` is now refused.** `test_p10is2_reusecheck.py` covers this.

**The projection.** Each remaining stage adds `HASH_PASSES_PER_STAGE × HASH_PASS_SECONDS = 2 × 5.3 = 10.6 s`. The 5.3 s is my warm-cache measurement; the 2× of the rule covers a cold cache.

## Certification of `common/plan.py::verify_plan`: CERTIFIED

The only change is the choice of section: `"stage_caps_attempt3" if plan.inputs has "reuse" else "stage_caps"`.
- Attempt 2's plan had no `reuse` input, so the branch reads `[stage_caps]`: the same expression and the same comparison as at `55017df`.
- `verify_plan` checks identity only. It computes and writes nothing stages 1–6 produced.
- **It could not have altered anything those stages computed or wrote.**

## R2: the ledger pin: FIXED

`paths.panel_ledger` names `/Users/daniellaloush/dandush03/ArborLM-sealed/p10i-s6-backups/panel_ledger.before-s6.json`, and that file hashes `62f8111614207fec…` (checked now). Its comment still says "the SHARED ledger … reads and writes"; that is cosmetic.

## R3: import-walk files compared: FIXED

`confined_diff` now loads the earlier plan's `frozen_files` from `<old_commit>:studies/p10is2/freeze/partq_plan.json`. It compares, by SHA-256, every entry that lies outside the current Part Q set and outside the earlier commit's Part Q names, which are the import-walk files. **Any difference or missing file is refused.**

That is 33 files: my count of 37 files outside `studies/p10is2/` in attempt 2's plan, minus the config, `uv.lock`, `pyproject.toml` and the requirements file, which the main loop already compares.

## Advisories

**The freeze requires attempt 2's run directory to be read-only.** `reuse.require_read_only` checks every path for any write bit, registered sources only. The freeze calls it after `verify_block`. Run `chmod -R a-w` on that directory before the freeze; it changes only metadata, so the hashes are unchanged.

**A failed regeneration re-check: correct.**
- `step_regeneration` already calls `fail()`, which writes `engineering_failures.json`, and records `regeneration.json` with `ok: false`.
- The new code then raises `RegisteredTestStop` when a reuse block is present. `execute` keeps the existing failure record and writes no completion record, so `outputs` refuses for want of a completed `regeneration`.
- The registered `analysis` is allowed by the failure record and derives row 1, QUALIFICATION-ENGINEERING-FAILURE.
- A resumed `regeneration` re-reads `ok: false` and stops again. That behaviour is right.
- The message "the stages are redone with the same registered seeds" matches addendum §4 ("If any condition cannot be met, attempt 3 redoes the stages concerned"). Whether to redo after such a stop remains the human lead's decision, because Q values exist (row 28).

**One test fails, and the cause is my environment, not the code.** `test_the_reuse_file_command_adds_the_block_to_a_copy_of_the_inputs_and_refuses_a_short_commit` fails only because my archive is not a git repository (`git rev-parse HEAD`: "not a git repository"). Result: 24 passed, 1 failed. The suite should pass in the worktree; run that one test there to confirm.

## The open point (the counting rehearsal's own charge)

Leave it out of the cap. The cap must exist before the counting rehearsal runs against the plan, and re-planning to include the rehearsal's charge would require another counting rehearsal. The omission only makes the total cap stricter. Record the rehearsal's charged seconds in Decision 2, as an addition to the "charge so far".

`Astra review: NOT_PERFORMED`. Claude review is not Astra review. This audit is not human approval.
