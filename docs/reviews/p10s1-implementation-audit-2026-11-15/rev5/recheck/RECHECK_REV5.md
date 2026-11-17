# P10-S1: narrow re-check of the fixes to AUDIT_REV5 (commit f1e8ebb against fe38842)

- **Auditor:** Claude Opus 5.5 (`claude-opus-5-5`), the author of AUDIT_REV5. This is a Claude review. **It is not Astra review and not human approval. Astra review: NOT_PERFORMED.**
- **Scope:** `git diff f1e8ebb^ f1e8ebb` (18 files) against AUDIT_REV5 and ADR-0021 §25.13. Branch `claude/p10-s1`, HEAD f1e8ebb, worktree clean. I only read the repository. Nothing was timed, calibrated, rehearsed or run at real size. No registered seed was generated, no network was used and no new environment was created. Nothing under `experiments/P10S0*` was read or touched. The live S0 processes were listed once with `ps`, read only.
- **Environment:** Apple M5 Max, macOS 27.2, the worktree's locked `.venv` (Python 3.12), CPU only, `OMP_NUM_THREADS=1`. Every command ran under `nice`, one test process at a time. P10-S0's registered q1 stage was training on six workers throughout.
- `R` = this folder. Each script imports `studies.p10s1` only as the code under audit. Every expected value and every schedule comes from my own code.

## 0. Commands

| id | Command (from the worktree root) | Output |
|---|---|---|
| suite | `P10S1_E2E=1 OMP_NUM_THREADS=1 UV_NO_SYNC=1 nice uv run --locked pytest tests/test_p10s1_*.py -q -p no:cacheprovider -rfEs --durations=15 --basetemp <scratch>/s1recheck/bt` | **253 passed, 0 failed, 0 skipped, 0 errors** in 1,167.7 s (19:29 wall), one process, the e2e included. `R/pytest_all.out`. The basetemp was deleted afterwards. |
| r0 | `python3 -I R/r0_rev4_overheads.py <rev-4 run dir>` | Per-task non-training time in revision 4: start-up about 6–16 s, evaluation 4.6–51 s per snapshot. `R/r0_rev4_overheads.out` |
| r3 | `UV_NO_SYNC=1 nice uv run --locked python -I R/r3_itemcap_schedule.py <worktree>` | a3 re-run: new dispatch order and caps, with start-up, evaluation and contention. `R/r3_itemcap_schedule.out` |
| r4 | `... python -I R/r4_finalize_midrun.py <worktree> <scratch>/s1recheck/r4run` | a4 re-run, plus the deadlock probes. `R/r4_finalize_midrun.out` |
| r5 | `... python -I R/r5_freeze_evidence.py <worktree> <scratch>/s1recheck/r5` | What the freeze accepts as evidence about S0. `R/r5_freeze_evidence.out`. Attempt 1 failed (my import error) and is kept. |
| r6 | Source copies of f1e8ebb from `git archive`, each made a git repository. One keeps the original config (control); in the other, `R/r6_m5_postfreeze_config.py` rewrites the config the way `set-cap` and `set-generation-cap` would (cap 23 h, measured generation cap). The five config-reading test files run in each with `nice .venv/bin/python -m pytest ...` | control: 1 failed (directory-name artifact of the copy) / 127 passed. post: **4 failed** / 124 passed. `R/r6_m5_pytest_control.out`, `R/r6_m5_pytest_post.out`. Attempt 1 used a copy without `.git` and is kept: `R/r6_m5_pytest_all.attempt1_nogit.out`, `R/r6_m5_pytest.attempt1_nogit_x.out` |
| r7 | The suite (e2e skipped) with a logging `ps` shim first on PATH (`R/r7_ps_shim.sh`) | Does any test read the real process list? `R/r7_pytest.out`, `R/r7_ps_calls.log` (§4) |

## 1. Findings: status after f1e8ebb

| # | Status | Evidence |
|---|---|---|
| **B1** item caps vs dispatch order | **Closed** | `calibration_tasks` now builds its tasks from `budget.dispatch_order`: the 12 row-U_P runs first, then the longest load-search runs. `item_projection` simulates that same list-order dispatch, and the cap is 2 × the item's last projected end, measured from the stage start. r3 repeats a3 over 48 settings per item group: rates ×1 and ×2, start-up 0/16/30/60 s, c 1.0/1.25/1.5, evaluation ×1/×2. **Under the code's order, no load-search or row-U_P run is stopped in any setting.** The smallest slack between the deadline and the end of training is 2,352 s for load and 192 s for row-up (start-up 60 s, c 1.5, evaluation ×2). Under the old order all 12 row-U_P runs are still stopped (B1 reproduced). New tests cover the dispatch order, the simulation and an in-flight deadline that has not yet passed. |
| **M1** finalize preconditions | **Closed** (one residual, §3a) | r4. A: no manifest, two T-OQ runs in progress → exit 2, no record. B: manifest says `completed` but there is no `train.json` → exit 2. C: manifest says `killed_cap` → finalized, with the runs listed in `stage_complete.no_record`. E: a run stopped at its cap → finalized from its `train.json`. `--finalize` now requires the items record and the h8-dense stage manifest. A dense run without a record now returns the unit to the lead; it is no longer counted as a diverged rate. |
| **M2** c from the rehearsal only | **Closed** (stale docstring, n1) | `contention_from` returns the rehearsal's c; the calibration's ratio is recorded as `calibration_descriptive`; there is a test. The `cmd_project` docstring (`stages.py` 1224) still says "the larger of the ratios … over the calibration's" (n1). |
| **M3** milestone reading | **Closed** as ruled in §25.13 | `established()` now reads only the capacity dense label. The double sub-label branch is removed: a sub-label is printed only when exactly one condition fails. Tests cover both directions. |
| **M4** freeze vs S0 | **Partly closed** | The refusal works: `freeze_concurrency` raises `OtherStudyRunning` while a `studies.p10s0`/`p10s2` line is alive (r5). The evidence check does not: r5 shows the freeze **accepts any readable file** as `--s0-training-manifest` and states "P10-S0's last training stage has finished": an empty file, `{}`, plain text, an *INCOMPLETE* S0 manifest, a P10-S1 calibration manifest. `--s0-refusal-record` is not checked either. Between two S0 stages only the shell wrapper is alive, and that passes. §25.13 requires S0's last due registered training manifest, so the statement is currently binding a hash, not checking evidence. |
| **M5** tests vs post-freeze config | **Partly closed — still fails** | r6: with the config rewritten as `set-cap` and `set-generation-cap` would leave it, 3 tests fail that pass on the control copy. (1) `test_p10s1_core.py:175` `text == core.render_config_toml(cap)` ignores `[generation]`. (2) `test_p10s1_audit_fixes.py` `test_set_generation_cap_writes_the_config_from_a_measurement` asserts `16.0 == 23.0` (line 378 compares a temporary config rendered at 16 h with the repository cap). (3) **`test_no_in_process_work_command_leaks_process_state`** relies on `work generate --mode registered` being refused because the cap is provisional. Once the cap is not provisional, the test starts an in-process registered-seed generation (it reached P5's `frozen-data/train.bytes` in the copy). In the real tree it would generate a registered draw inside pytest. The freeze commit therefore still cannot pass its own suite, and one test would touch registered seeds. |
| m1 placeholder plan | **Closed** | `Plan.placeholder` is set when U_L is left at its default. `freeze` refuses it, except under DRY or the test switch, and so does `verify_plan`. `from_json` carries the flag. `project` builds its plan from `plan_values` (explicit U_L), so a calibrated plan is never flagged, and no legitimate path is refused. An explicit U_L equal to the first candidate is still accepted, but only by typing it; that is acceptable. |
| m2 exact 0.02 | **Closed** per §25.13 | `>= 0.02 - EPS` → return. |
| m3 caveats | **Partly closed** | The CANNOT list gains the four §12 items. A crowding line for SUBPROPORTIONAL and a readable separability line are added. The printed SATURATION-SUBPROPORTIONAL label itself still carries no crowding caveat; it appears only on a separate RESULTS line. |
| m4 printed labels | **Open** | The CAPACITY-POSITIVE and SATURATION-PROPORTIONAL printed labels are unchanged (no bits per slot, b(N) range or dense-at-saturation label). |
| m5 directed transition | **Partly closed** | `saturation_line` fixes pairs that use the unloaded cell as NOT FULL. `--no-loaded-transitions` is validated and needs `--direction-record`, bound by hash. Still no run length exists for an unloaded cell: `plan_values` refuses any open return, so the path stays unreachable. |
| m6 stale text | **Closed** in the places named (READINGS, four docstrings, report heading) | New stale text: n1, n2. |
| m7 H8 failed or missing | **Closed** | `h8_report` gives `calibrated_cells` (all four views present). A cell missing any view prints H8 NOT CALIBRATED AT. This is carried through `project` and `freeze`, and tested. |
| m8 registered `generate` with an open return | **Open** | The rehearsal now refuses a calibration with an open return (`frozen_of` turns `TieNeedsLead` into a refusal), and a missing `--calibration` file now refuses. But `cmd_generate` / `verify_worker_plan` check only the provisional flag. `set-generation-cap --generation-seconds` (typed) clears that flag without any calibration. So registered draws can be generated while a return is open. The freeze later refuses a typed cap, but the generation has already happened. |
| m9 guard coverage | **Partly closed** | Rehearsal `gates`/`generate` and `calibrate` are now covered. The gap between two S0 stages (only the wrapper alive) is still not detected by the start-of-stage guard; see §3d. |
| m10 ADR text 1.7 vs 1.646 | **Open (ADR text)** | Not code. |
| m11 calibration vs S0 | **Closed** per §25.13 | The guard covers `calibrate-*` (the test is updated; its name `..._and_calibration_may` is stale, n2). The gap in m9 applies. |
| m12 e2e uses six workers | **Open** | Unchanged. |

New minors: **n1**, the `cmd_project` docstring describes the rejected contention reading. **n2**, the test name `test_the_stages_that_must_not_overlap_refuse_and_calibration_may` now asserts the opposite. The `stages.py` 733 preview note still says "the caps bound training wall seconds", which is accurate. **n3**, in the DRY profile `require_stage_complete` looks cells up by `CAL_…` label, but DRY tasks are grouped as `cal-…`, so one failed DRY run makes DRY finalize refuse permanently. This is DRY only.

## 2. When the implementer's open items must close

| Item | Before timing preview | Before calibration | Before freeze | May stand |
|---|---|---|---|---|
| m8 (registered `generate` ignores open returns) | | | **yes**: registered generation is a freeze-procedure step; it must refuse unless a calibration record with no open return is bound | |
| m4 (printed labels) | | | **yes**: the report code is part of the frozen identity | |
| m3 remainder (caveat in the SUBPROPORTIONAL label) | | | **yes** (same reason) | |
| m6 remainder (n1, n2) | | | yes (text) | |
| m10 (ADR 1.7 vs 1.646) | | | | **may stand** until the lead next amends the ADR; it is text only and changes no snapshot (the grid gives 2.0 either way) |
| m12 (e2e six workers) | | | | **may stand**: DRY-size processes, and S1 does not run alongside S0 under m11 |
| Caps bound training only, no allowance for start-up or evaluation | no | **lead ruling before the calibration (PENDING LEAD REVIEW)**, see below | | |

**Simulation for the last item (r3).** The start-up comes before training, and only the training loop checks the deadline. Earlier runs' evaluation delays later starts in the same stage, and the cap includes neither. Results:

- **No run loses its U_L or row U_P.** Items 0b+1 under the code's order have no stopped run in any of the 48 settings. Worst slack is load 2,352 s and row-up 192 s (start-up 60 s, c 1.5, evaluation ×2). At revision 4's start-up (about 16 s), c 1.0 and evaluation ×1, slack is 5,501 s and 836 s.
- **Items 2+3 at the largest row candidates** have no stopped run in any setting. Worst slack is H8 110 s and dense 163 s.
- **Items 2+3 at the smallest row candidates** are the exposed case: the H8 cap is 246 s and the dense cap 5,787 s.
  - H8 loses 2 runs when start-up is ≥ 30 s with c 1.5, or at start-up 60 s.
  - Dense loses 4–12 runs at c ≥ 1.25 with evaluation ×2, or at c 1.5 with evaluation ×2. Those dense runs are queued behind other dense runs' evaluation at 32K facts (about 46 s per snapshot).
  - At revision 4's start-up and evaluation (×1) with c ≤ 1.25, nothing is stopped; the margins are H8 83 s and dense ≥ 1,853 s.
- **Consequences differ.** A stopped H8 run only gives H8 NOT CALIBRATED. A dense run stopped at its cap has a `train.json` and is counted as **diverged** (`finalize_h8_dense`; §25.12 item 3 "run not completed"). That can remove a rate from the selection, without a return, **for a scheduling reason** (PENDING LEAD REVIEW).
- With the preview measuring neither start-up nor evaluation, I recommend that, before the calibration, the lead either rules an allowance (for example per-task start-up plus evaluation per snapshot from revision 4's records, as in r0) or accepts these margins on the record. This is not needed before the timing preview: the preview does not use the caps.

## 3. What the fixes might have broken

a. **M1, can a failed run deadlock finalize?** A failed, cap-stopped or killed run does not: it has a `train.json` or a manifest status other than `completed` (r4 C, E). The pool writes the manifest even when tasks fail. **One case does deadlock:** if the driver itself dies (SIGKILL, reboot, sleep-kill) before writing `calibrate-load-row-up/manifest.json`, `--finalize-items` refuses forever (r4 D). The runs cannot be relaunched either, because `cmd_calibrate` refuses any cell whose directory exists (the code path is read; my probe was refused earlier, at the missing timing file). This fails safe, since nothing is decided from partial records, but no recovery path exists. **PENDING LEAD REVIEW** before the calibration: name the recovery in advance, for example a lead-signed manifest substitute. This is not a code blocker.

b. **M4 `--s0-training-manifest`:** any file is accepted (r5). It is not checked to be S0's stage manifest (`kind == stage_manifest`, `study == P10S0`, a training stage, `status == COMPLETE`, registered mode). It is bound by hash only. S0's code is not on this branch, so S1 cannot import S0's schema; it can still check those fields. Must close before the freeze. Otherwise the lead must verify the hashed file at Decision 2 and say so in the record.

c. **Placeholder refusal:** no legitimate path is refused (§1 m1). DRY and the test switch are exempt, and the e2e passed.

d. **Guard now covering calibration:** correct under §25.13 m11. It still runs once, at stage start, and cannot see the gap between two S0 stages. The timing preview and the calibration are both guarded only by that check. Ruling m11 requires them to start "after S0's last training stage has finished", so I recommend the preview and the calibration take the same S0 evidence the freeze takes (a lead check is the minimum). Answer before the timing preview: PENDING LEAD REVIEW on whether a lead confirmation is enough.

## 4. Tests

- **Whole S1 suite, one run, one process, e2e included: 253 passed, 0 failed, 0 skipped** (1,167.7 s; the e2e test took 832 s, the clone test 11 s). Ruff was not re-run. This is the first all-green single run of the suite at f1e8ebb that I know of.
- **Do tests see the real S0 processes?** The autouse fixture `no_other_study_running` (defined in `test_p10s1_stages.py`, imported into `test_p10s1_audit_fixes.py`, `test_p10s1_rev5_audit_fixes.py` and, since f1e8ebb, into `test_p10s1_core.py`) and explicit injection in `test_p10s1_rev5_model_and_guards.py` cover the guard tests. The e2e runs DRY/test-switch stages, which never call the guard. r7 (`PATH=<shim dir>:$PATH OMP_NUM_THREADS=1 UV_NO_SYNC=1 nice uv run --locked pytest tests/test_p10s1_*.py -q -p no:cacheprovider --basetemp <scratch>/s1recheck/bt7`, e2e not opted in): **252 passed, 1 skipped (the e2e)** in 295.8 s, and the shim logged **0 calls to `ps`**: no test read the real process list while six S0 workers were alive.
- **M5 under a post-freeze config:** 3 regressions (§1 M5), one of which would start a registered generation inside pytest.

## 5. Verdict

**READY FOR TIMING PREVIEW AND CALIBRATION**, with the lead recording three rulings before the calibration: the cap allowance (§2, including "a cap-stopped dense run counts as diverged"), the recovery after a driver death (§3a), and whether a lead confirmation that S0 has finished is enough at the preview and calibration starts (§3d). None of the code findings bears on the timing preview or the calibration commands.

**Must close before the freeze:** M4 evidence check (§3b); M5 (three tests, including the in-process registered generation); m8; m4; m3 remainder; m5 remainder (if a directed transition is ever used); n1, n2.

This is a Claude review (Opus 5.5). It is not Astra review and not human approval. Astra review: NOT_PERFORMED.

## 6. My own mistakes (kept)

- r5 attempt 1 (`r5_freeze_evidence.attempt1_failed.out`): I imported `pool` from `studies.p10s1`; it lives in `studies.p9`.
- r6 attempt 1 (`r6_m5_pytest_all.attempt1_nogit.out`, `r6_m5_pytest.attempt1_nogit_x.out`): my copy had no `.git`, so 8 of the 9 failures were my artifact. I re-ran it with a git-initialised copy and a control copy. One control failure (`test_generate_and_stage_codes_use_the_experiments_root`, which expects the parent directory to be named `ArborLM`) is also an artifact of the copy and is the same in both.
- My first r3 printed only stopped settings. I re-ran it with a worst-slack summary; the file holds the second run.
- My r4 re-launch probe was refused at the missing timing file before reaching the cell-exists check. That check is established by reading the code (`stages.py` `cmd_calibrate`, "a calibration run is never re-run").
