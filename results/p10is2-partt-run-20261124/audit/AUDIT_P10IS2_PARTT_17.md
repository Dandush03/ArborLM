# Audit 17: P10-I-S2 Part T cap amendment (ruling 51), commit f84b928b

VERDICT: AFTER FIXES. One blocking defect (D1): the second freeze would refuse after the targeted rehearsal had
already been spent. One minor defect (D2). With D1 fixed, the amendment is ready for the targeted rehearsal.

Auditor: arbor-auditor, run as Claude Opus 5.5 (claude-opus-5-5). Date 2026-11-23.
Worktree agent-acd0bce1f7811562f at f84b928bd7058e63e40c71d68884a8bbb27b01df, clean.
In the worktree I ran only the two permitted commands. I opened only the registered run directory's file and
directory names (`ls`). I read no ledger value, timing record, checkpoint or outcome there.

Simulations ran in my own clone, experiments/_scratch/p10is2_audit10_clone, checked out at f84b928b (fetched
locally, no network). Output: experiments/_scratch/p10is2_audit17_out/walk_diff.txt.
This is engineering evidence from a Claude review. It is not Astra review and not human approval.

## Commands
- `uv run --locked ruff check studies/p10is2 tests/test_p10is2_partt_amendment.py` printed: All checks passed.
- `uv run --locked pytest tests/test_p10is2_partt_amendment.py -q -p no:cacheprovider` (nice 10, CPU): 14 passed.
- Clone, worktree .venv python, PYTHONPATH=clone:
  - `import_walk(clone, "T")` plus `plan_diff_problems(old plan at c25d4f0b, simulated new plan)`: see D1.
  - config_diff_problems on the old config vs the current config, and vs the current config with train 125.8,
    combined 6.0 and total 204.02: [] both times.
  - seed_registry_check_r7.py, unedited: RESULT: PASS.

## Defects
**D1 (BLOCKING): the second freeze will refuse at `plan differs at .import_walk.python_files`.**
- Cause: `entry_modules` (common/plan.py:121-131) imports every studies/p10is2 module, so the new walk adds
  `studies/p10is2/partt_targeted.py` and `studies/p10is2/partt_amendment/__init__.py`.
- `plan_diff_problems` (partt_amendment/__init__.py:110-114) excuses only changed files containing
  `studies/p10is2/partt_amendment/`. partt_targeted.py lies outside that directory, so it is reported.
- Simulated result: plan_diff_problems returned ['.import_walk.python_files']. The added python_files were exactly
  those two files, none were removed.
- The unit test (tests/test_p10is2_partt_amendment.py:117) uses a synthetic walk that never includes partt_targeted,
  so the tests could not catch this.
- Effect: the refusal comes after the targeted rehearsal (about 1.3 h). Fixing it then changes a frozen file, which
  needs a new plan and a new targeted rehearsal.
- Fix, one line at partt_amendment/__init__.py:113:
  `if all(own in c or c in amend["exempt_files"] for c in changed):`
  Then add a test that runs the real `planmod.import_walk` on the repository.
- Once this fix is in, the simulated plan differences come only from the frozen files of the config, the four
  changed exempt files, the new exempt file and the three own files. All of these are allowed.

**D2 (MINOR): `--rehearsal-arms` is not refused in a registered launch.**
- `plan_for` (partt_stages.py:109-112) refuses --plan-file and --pause-after-updates in registered mode, but not
  --rehearsal-arms.
- `execute_stage` passes `arms` to `run_stage_tasks` in both modes. A registered `train` launched with
  `--rehearsal-arms X` would train a subset and then write `stages/train.complete.json` with cells missing.
- Fix: add `getattr(args, "rehearsal_arms", None)` to the condition at partt_stages.py:111. Do it in the same commit
  as D1.

## 1. Scope
- **Changed frozen files:** the simulation diffed every frozen file between c25d4f0b and f84b928b. The changed files
  are configs/p10is2_partt.toml, common/runner.py, partt_caps.py, partt_stages.py and partt_tasks.py, plus the three
  new partt_amendment files and partt_targeted.py.
- **No training, scoring, label or calibration file changed.** engine, partt_run, scoring, labels, annotations,
  partt_items, partt_real, calibration and quantities are all unchanged.
- **Config:** the only changes are the four allowed [caps] keys and the new [cap_amendment] section. No threshold,
  seed, cell, rate or U changed.
- **Changed lines outside the cap and memory logic:**
  - partt_stages.py:126 adds the `arms=` passthrough.
  - partt_stages.py:600-609 adds `rehearse --kind targeted`.
  - Freeze changes (partt_stages.py:796-860):
    - accepts the first counting record against the pre-amendment plan hash;
    - adds the targeted gate;
    - adds the exempt-file filter on the calibration code-identity check.
  - None of these changes a scientific rule.
  - The exemption is a stated departure from §7.1 rule 4. The PROTECTED list stops any training or scoring file from
    being exempted.
- **Test changes:**
  - tests/p10is2_partt_unset.py zeroes the stage caps, sets provisional = true and strips [cap_amendment] in
    synthetic copies. This restores the pre-freeze state those tests were written for. No scientific rule is weakened.
  - conftest.py adds one strict xfail, for a test that asserts the real config has no caps. That has been false since
    the first freeze; it is justified.
  - test_p10is2_partt_budget_bound.py now asserts config 205 and approval 151. The test no longer ties the config
    bound to an approval record. See departure (a).

## 2. Resuming from 50 cells
(a) Gates is not re-run. Train needs only stages/gates.complete.json (partt_tasks.require_predecessor), and that
file exists.
- The 50 completed cells have result files. The runner records them COMPLETED with 0.0 s and starts no process,
  so nothing is re-charged.
- The registered directory listing shows M-ii results for r0 AB and r0 BA only. Checkpoints exist for r1 AB, r1 BA
  and r2 AB. There is no failed or item_errors record, so no task is blocked as FAILED.

(b) WAVES (partt_tasks.py:29) puts M-ii alone in wave 3.
- wave_workers (partt_tasks.py:47-53) returns 1 for an all-M-ii wave in every mode. This is not limited to
  rehearsals.
- engine.train_cell (engine.py:312, 323-328) resumes from checkpoints/r{rep}__M-ii__{order}.ckpt when one exists,
  and starts fresh otherwise (r2 BA). Plan item order gives r1 AB, r1 BA, r2 AB, r2 BA, one at a time.

(c) No run-directory record pins a plan hash or a freeze commit:
- The checkpoint holds only update, params, opt and losses.
- run_mode.json holds only the mode.
- The stage markers hold stage, status, mode and utc.
- The manifest is rewritten at each invocation.
- Every worker re-runs refuse_unless_registered_ready against the freeze commit given on the command line.

(d) ledger_of uses the new plan's total. stage_cap_for = min(125.8 h − charged(train) 95.87 h = 29.93 h,
204.02 − (24.22 + t) − ledger total). Here t is the targeted charge, which the freeze holds to ≤ 3.0 h.

What the lead must commit, in order:
1. The D1 and D2 fixes.
2. A move of freeze/partt_freeze_record.json into freeze/<first-freeze dir>/. Until then candidate-plan --supersede
   (partt_stages.py:685), the rehearsal entry (partt_stages.py:89) and freeze (partt_stages.py:771) all refuse.
3. The superseding plan with the amended caps.
4. After the targeted rehearsal, the second freeze record. Call its commit F2.
5. A new results/p10is2-partt-freeze-<date>/DECISION_2_PARTT.md, in a new directory, holding the exact line
   `DECISION: RUN` and the full 40-character F2 hash, with no `DECISION: DO NOT RUN` line
   (plan.py:286-293).

The first thing that would refuse today is the freeze, on D1. If the first freeze record is not moved, the first
refusal is candidate-plan.

## 3. Caps
- **Arithmetic:**
  - Sum of the amended stage caps = 176.80 h.
  - Total = ceil(87,178.16 s + 3.0 h + 176.80 h) = 204.02 h, below the 205 bound (recomputed).
  - The plan charge of 87,178.16 s is measuring 22,379.0 + calibration 12,300.46 + first counting 52,498.70.
- **Room after train:** gates charged 0.40 h, about 0.40 h, so the worst case after train at its full cap is
  204.02 − 24.22 − t − 0.40 − 125.8 = 53.6 − t h. The later caps sum to 50.46 h, so they fit for t ≤ 3.14 h.
- **Projections:** evaluate 14.7 / 21.77 h, combined 3.9 / 6.0 h, recompute 15.3 / 22.66 h. All fit.
- **Charged-time check:**
  - The cap is checked at every poll before any start and while tasks run (runner.py:85). The check sums the
    seconds of finished tasks and the elapsed time of running ones.
  - Overrun is bounded by the poll interval plus the kill time (≤ 30 s per worker), so a wave no longer overruns
    silently.
  - A new cap is computed at each wave start (partt_tasks.py:170).

## 4. Memory admission
- runner.py:94 starts a further worker only if `not running` or psutil available ≥ 16 GiB. When memory is short the
  runner waits, and the time spent waiting is not charged.
- It cannot deadlock: the first task always starts, and running tasks end or hit the cap. It does not pause the run.
- Admission is irrelevant to the M-ii wave, which has one worker.
- It can serialize evaluate if other processes hold memory. That costs wall time, not charge.

## 5. The targeted rehearsal
- **Isolation:** it runs in rehearsal mode with rehearsal seeds and stand-in panels. Evaluation scoring is refused
  in rehearsal mode (scoring.py:41). claim_run_dir refuses the plan's registered directory, and the registered
  directory is only read (preflight reads run_mode.json and the ledger).
- **Is the timed M-ii cell representative?** Yes. Its parent is M-append (engine.py:240), so training M1 and
  M-append at 200 updates changes the parent's content, not the store size. The M-ii cell trains U = 8,000 updates
  with replay, as registered. The unit check requires units == U.
- **Record pinning (weakness, see departure (b)):** AMENDMENT_RECORD.json is pinned only through the plan, which
  lists it in its frozen files and in its manifests.
  - The record defines its own allowed config paths and exempt files, and plan_diff_problems excuses any change in
    its own directory.
  - So an edit to the record or to partt_amendment/__init__.py before the new plan would be accepted by the freeze.
  - Fix (advisory): ruling 51 and Decision 2 should cite these sha256 values at f84b928b:
    - AMENDMENT_RECORD.json: 10463ef919f9ec534d2d3e573d55810e2521fac5a003c51d3d6186d6c3c3b7ad
    - __init__.py: d08c8fa4507b9ff943947ecfb7bb4a7de0b6b1c138ffb8e7b96df9a14c27b5e7 (it changes with D1)
    - partt_targeted.py: 8d7e1f5f6a347ff49d1dd71623f02e89a613c966d8ad1d93412bca1f6511fa52
  - The auditor should then diff the second plan's frozen_files against them.

## 6. Preflight
- partt_targeted.preflight (partt_targeted.py:32-63) is read-only. It checks foreign records, the platform, a clean
  tree, PYTHONPATH, the registered directory's mode and git-ignore status, the amendment manifest and the cap
  headroom.
- It is NOT the registered entry point's function set. It does not call check_preconditions (freeze-commit
  ancestry and identity), verify_plan in registered mode, verify_freeze_record or require_decision_2. These cannot
  pass before F2 exists.
- Advisory: after F2 and Decision 2 are committed, run refuse_unless_registered_ready's read-only parts before the
  launch: check_preconditions, load_registered_plan, verify_plan, require_decision_2 and require_ignored_run_dir.
  This is the same call sequence I used in audit 15.

## 7. Departures to add to AMENDMENT_NOTES
- (a) The 205 h bound rests on a relayed, ambiguous reply ("ok, yes continue at night how many ours you have
  left?"). There is no approval file like results/p10is2-partt-budget-bound-20261121/APPROVAL.md, and the
  budget-bound test no longer checks the config against an approval record. PENDING LEAD REVIEW.
- (b) The amendment record is self-referential; it is pinned only by the new plan (§5).
- (c) The combined cap is 3.7× its rule value, beyond the lead's one-time 2× extension. PENDING LEAD REVIEW (the
  notes already say so).
- (d) The tiny-task checks and the targeted driver process are not charged to any ledger. Only seconds are involved.
- (e) The three killed M-ii checkpoints were written with a non-atomic torch.save. A kill during a save leaves a
  corrupt file, which makes the cell ERROR on resume and then FAILED, and a retry fails the same way.
  - Their integrity is unverified.
  - Advisory: before the launch, a read-only torch.load of `update` only.
- (f) The descriptive timing benchmark charges the ledger but has no cap in the total. Running it uses up the
  headroom.
- (g) Merging main before the run ends would restore the six foreign freeze records, and every worker would then
  refuse under L11 (audit 15).

## Expected command sequence (after D1 and D2 are fixed and committed)
1. Commit `git mv studies/p10is2/freeze/partt_freeze_record.json studies/p10is2/freeze/first-freeze-c25d4f0b/`.
2. Build the plan:
   - `partt_stages candidate-plan --supersede --run-dir /Users/daniellaloush/dandush03/ArborLM/experiments/P10IS2-T-registered-20261121`
     with these arguments:
     - `--measuring-rehearsal <measuring3 record>`
     - `--part-q-dir <Part Q registered3>`
     - `--manifests <the old four entries plus cap_amendment_record>`
     - `--charged-ledger` for measuring 1, measuring 2 and measuring 3, calibration, and
       P10IS2-T-counting-20261121/charged_ledger.json. NOT the registered ledger.
   - Then `caps-config --apply`.
   - Then `candidate-plan --supersede` again.
   - Commit and push.
3. `partt_stages rehearse --kind targeted --run-dir <new experiments dir> --part-q-dir <Part Q dir>`, on a clean
   tree.
4. Freeze, then commit and push:
   ```
   partt_stages freeze --measuring-rehearsal <measuring3> \
     --counting-rehearsal experiments/P10IS2-T-counting-20261121/rehearsal_counting.json \
     --targeted-rehearsal <dir>/rehearsal_targeted.json \
     --attest-sealed-unopened lead,implementer,auditor
   ```
   The resulting commit is F2.
5. Commit results/p10is2-partt-freeze-<date>/DECISION_2_PARTT.md (`DECISION: RUN` plus the full F2 hash).
6. Run the read-only preflight from §6.
7. `sh studies/p10is2/launch/partt_registered.sh train /Users/daniellaloush/dandush03/ArborLM/experiments/P10IS2-T-registered-20261121 <F2>`.

Astra review: NOT_PERFORMED
