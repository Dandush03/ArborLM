# P10-S0 pre-freeze audit (ADR-0020 rev 4 and addenda): N1–N9 fixes, rehearsal and gates records, projection, the cap raise

**Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.**

## Scope and environment

- **What was audited.** Worktree `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-afc8a4b295465fecc`, branch `claude/p10-s0`, HEAD `af18a59`. The fix commits were `3a9a742..9cca808`; the cap commit was `af18a59`. Nothing in the repository was edited and nothing was committed. The working tree was clean before and after.
- **Auditor.** Opus 5.5 (`claude-opus-5-5`). I did not write this code, run these stages, or write the earlier audits.
- **Environment.** macOS-27.2.1-arm64. The worktree's `.venv` was used: Python 3.12.14, torch 2.8.0, uv 0.12.15. My independent recomputations (p2–p6) ran under `/usr/bin/python3 -I` (3.9.6, json only, with no repository import).
- **Not done.** I generated no registered draw and read none. I ran no registered stage and did not re-run the rehearsal. I did not run the end-to-end exercise (to keep CPU use modest).
  - The test seeds used were the S0 unit-test sets (920001–920999) and the TEST_PROFILE names.
  - `experiments/` was compared before and after: the listing and the ledger sha256 are unchanged (`outputs/experiments_listing_*.txt`).

## Verdict: READY AFTER LISTED FIXES

None of the fixes requires repeating the rehearsal or the rehearsal-draw gates, because `train.py`, `evaluate.py`, `model.py`, `studies/p9*`, `src/`, `uv.lock` and `pyproject.toml` stay untouched.

Two majors must be fixed before the freeze:

- **F1.** The S0 suite is red at `af18a59` (9 tests).
- **F2.** The end-to-end exercise's default variant cannot pass with a 22-hour cap.

After the fixes under `studies/`, the e2e (both variants) and the S0 suite must be re-run on the final pre-freeze commit.

## 1. N1–N9 and the informational items (task 1)

| Item | Fixed? | Evidence |
|---|---|---|
| N1 state-dependent tests / pytest starting registered generation | **Yes for the N1 class.** In a throwaway frozen clone (`git clone` of HEAD, plus a committed `DECISION.md`, `stage_caps.json` from the real `caps` command, and a stand-in `plan.json`), no test started a registered stage. The clone got no `experiments/` directory and no `RUNNING.json`, and the real `experiments/` was unchanged. **But the suite is red for a new state reason (F1).** | `outputs/pytest_p10s0_frozen_clone.txt` (9 failed, 400 passed, 2 skipped), identical failures to HEAD |
| N2 typed registered worker / generation worker | **Yes.** Typed `work train --mode registered` without a token: refused ("no P10S0_STAGE_TOKEN"). A cell outside the stage's tasks: refused. A cell outside the frozen matrix: refused. A token of another kind: refused. A wrong nonce: refused. `work generate --mode registered` without a token: refused. A forged, matching `RUNNING.json` passes the token check and reaches `registered_state`; the README discloses this limit. | `outputs/p8_demos.json` a, b1–b6 |
| N3 test-profile labelling | Yes. `freeze-plan --test-profile` without `P10S0_E2E_CLONE` is refused. `profile` is in the analysis, q1_gate and results records, with a banner. | p8 h; code `report.py:159-182` |
| N4 reserve = frozen caps | Yes. `frozen_reserve` = (analysis cap + report cap)/2 in both rules and in the plan. | `stages.py:1101-1111`, `budget.py:281-287` |
| N5 one place for the cap | Code yes: `core.cap_hours()` reads the config, and `set-generation-cap` preserves `cap_hours` (p8 d: 22.0 kept). **Incomplete in effect:** a raise is not "exactly one changed value", because 9 tests encode 16 h (F1). | |
| N6 set-generation-cap manifests | Yes. DRY: refused. Check mode: refused. Rehearsal mode on another stage: refused. Rehearsal stage: accepted (max(60, 2×40) = 80). | p8 d_* |
| N7 implementer strings | Yes. The table is generated and test-enforced. | README table; `test_the_readme_lists_every_implementer_worded_string` |
| N8 plan added twice | Yes. With the plan removed and re-added, the first addition is refused ("is not the commit that added") and the latest is accepted. | `outputs/p9_readd.json` |
| N9 typed cap in registered mode | Yes. `stage_cap` ignores a typed value in registered mode. `generate --mode registered --stage-cap-seconds 5` and `registered q1 … --stage-cap-seconds 5` are both refused by name. | p8 f1–f3 |
| I4 unused generate entry | Yes. `freeze-plan` requires `caps.generate == config cap` (exact float equality; see F9). | `stages.py:1051` |
| I5 deleted tests | Yes. It uses the union of the test names at HEAD and at the freeze commit. | `stages.py:273-280` |

**Code identity.**

- `train.py`, `evaluate.py` and `model.py` are byte-identical at `3a9a742`, `9cca808` and `af18a59` (sha256 `453b762c…`, `8c742bd2…`, `ac558df8…`). `git diff 3a9a742 af18a59` is empty for `studies/p9ii studies/p9i studies/p9 src uv.lock pyproject.toml`.
- The predecessor's `a5_arms_identity.py`, re-run at HEAD (test set 920701), gives output identical to the re-check's at `3a9a742`.
- G4's `identity_against_p9ii` passed at real size on the rehearsal draw at `9cca808`.
- ruff: all checks passed. mypy `src/arborlm studies/p10s0`: no issues.

## 2. Records (task 2; the re-check's checklist 1–8)

1. **Generation cap.** The source is `generate-p10s0-rehearsal/manifest.json`: mode `rehearsal`, COMPLETE, one task of 33.44888391700806 s, identity `9cca808`. The config holds `provisional = false` and `cap_seconds = 66.89776783401612` = max(60, 2 × 33.4489). **OK.**
2. **Rehearsal-draw gates.** G1, G2, G4, G5, G6, G9 and G10 are all `true`; `harness_errors` and `g4_defects` are both `[]`; a recursive scan finds no `passed`/`identical` false.
   - The stage manifest is COMPLETE (rc 0, 39.755 s). `timing.per_draw_seconds` = 3.1943. The identity is `9cca808`.
   - G10 ran the auditor script (`auditor_script_run: true`, no disagreements, table row 3, "ADDRESSING-RELIABLE, carried arm A0"). The recorded `script_sha256` 886e2d27… and `sibling_sha256` c3629201… equal the current files, which are what the freeze will pin.
   - In rehearsal mode there is no plan, so the pinned-hash refusal path itself is exercised only by the unit test.
   - `stage_caps.json` does not exist yet.
3. **Projection** (`P10S0J-projection-20261115/projection.json`, sha256 `d6f6e6be36ca6a69…3e53aa7`, as the addendum says).
   - `unit_updates` 8192, `missing_items` [], candidates [A5-D, A1].
   - The alone and busy rehearsals are distinct directories, with `busy_processes` 12 in every busy training record and 0 in the alone ones.
   - All 24 items are present: A2 pre and post at 2K/4K and 8K/16K, WX-A5-D and WX-A1 at both sizes, and 32K/64K for A5-D, A1 and A6.
   - `guard_seconds_per_task` = 0.387 s.
4. **Memory.** Every block peak is ≤ 1.5 GiB: Q1 0.616, WX 0.664/0.679, probe 1.043 GiB (A6 at 65,536 in the alone run). 2 × peak × 6 = 12.5 GiB, within 18 GiB.
5. **Probe evaluation margin.** One evaluation at 65,536 takes 83.2 s (A1, busy), 71.6 s (A5-D) and 51.1 s (A6). The cap is 175.4 s (A1) / 152.4 s (A5-D), which is 2× the round including ~4.5 s of start-up and guard. The fixed parts of a registered evaluation (data rebuild with hash check, snapshot load, guard ≈0.5–0.9 s) are small at real size. Adequate.
6. **Analysis/report times on synthetic full-registry records.** Not measured yet: README step 8 is pending, with no record found. If both are ≤ 30 s, the reserve is the 60 s floor.
7. **Freeze record.** Not yet; see §7.
8. **q1_start.** Not applicable yet.

**Rehearsals.**

- Each rehearsal has 24/24 items, a COMPLETE manifest, 24 completed tasks and 48 record files.
- Every record and both manifests carry identity = `9cca808` (source 6e56d4c7…, spec bb3d213e…, config 6261db92…). I recomputed it by `code_identity()` on a `git archive` of `9cca808`.
- The keys written are only the whitelist: time, memory, shapes, counts, identity, and the `loss_finite`/`parameters_finite`/`gradients_finite` booleans. There is no loss, accuracy, recall or AUC key, and no log line mentions loss, accuracy or recall.
- Load averages: alone 11.6–14.6, busy 22.0–59.3.

**Pipeline check** (`P10S0K-…`).

- Complete: train-check and evaluate-check COMPLETE, 3/3 tasks each, rc 0.
- Its identity is `3a9a742` (before the N1–N9 fixes; `train/evaluate/model` are identical).
- The controls are at chance: disabled, permuted and unseen accuracies are 0.024–0.037, inside the chance interval [36, 96]/2,048, with every `*_at_chance` flag true (A7 has no permuted control).
- **These accuracies are not results and select nothing (ADR-0020 §10.1).**

## 3. Projection, recomputed (task 3)

My own code (`scripts/p3_projection.py`) builds the matrix from ADR §6 and applies the formula below. Each field takes the larger of alone and busy. Training is updates × s/update + task start-up + guard; A2 runs `U_pre` (2,048 / 8,192) at the pre rate and the rest at the post rate. Evaluation is readouts × eval + start-up + guard. Both makespans are taken in rounds of six, sorted by decreasing time.

| Block | Mine (h) | `projection.json` (h) | Diff | Literal §10.3 (no start-up/guard) | Alone only | Peak GiB |
|---|---|---|---|---|---|---|
| Q1 full (230) | **8.413** | 8.413 | 0.0 s | 8.327 | 5.066 | 0.616 |
| Q1 cut 3 (190) | **5.840** | 5.840 | 0.0 s | 5.770 | 3.510 | 0.616 |
| WX A5-D / A1 | **0.843 / 1.089** | same | 0.0 s | 0.834 / 1.081 | 0.490 / 0.666 | 0.664 / 0.679 |
| Probe A5-D / A1 | **3.285 / 5.505** | same | 0.0 s | 3.282 / 5.503 | 2.084 / 3.636 | 1.043 / 1.043 |

- **Agreement.** Every training and evaluation makespan agrees to 0.0 s, and the lead's read is confirmed.
- **The binding run.** The busy rehearsal binds for every item. Busy/alone is about 1.52–1.75. Most of the 2.2× over the ADR's design-time slowest rates (Q1 3.89 h) is the busy condition; alone gives Q1 5.07 h (1.30×).
- **The rounds model is conservative.** I simulated the pool's FIFO dispatch in the registry's task order. Q1 train comes to 29,218 s against 29,425 s for the rounds model, and Q1 eval to 856.5 s against 860.4 s. WX and the probe are equal.
- **A2 pre fields (informational).** The A2 `pre` items' `evaluation_seconds`/`task_overhead_seconds` in `projection.json` are the `post` item's, because the records' labels collide (`REH-Q1-A2-2K4K-d01-j0`). No projection uses them, so there is no effect.

## 4. The cap raise (task 4)

**Inputs.**

- Charged now: 486.26 s.
- Registered generation of 15 draws: 501.7 s at the measured rate (1,003.5 s at the 66.9 s cap).
- Registered gates: G + 12P = 39.755 + 12 × 3.194 = 78.09 s.
- Reserve: 60 s, assuming A and R ≤ 30 s.
- Charged at Q1 start: 0.296 h.

| | 16 h | 21 h | 22 h |
|---|---|---|---|
| Before Q1, full: 0.296 + 2(8.413 + 0.017) | 17.15 h → **cut 3** (cut-3 need 12.01) | full | full |
| After Q1 at projection, A5-D: both blocks need | 14.42 h (after cut 3) → WX + probe | 17.00 → both | 17.00 → both (margin 18,011 s) |
| After Q1 at projection, A1 | 19.36 → **cut 1** | 21.93 → **cut 1** | 21.93 → both (**margin 249 s**) |

- **Smallest whole number.** The real thresholds are 17.15 h (Q1 uncut) and 21.93 h (A1's WX + probe after a Q1 at projection). **22 is the smallest whole number with the stated property**, under nominal assumptions. If generation runs at its cap and the gates at theirs, the need is 22.09 h, and A1's probe is cut even with Q1 at projection.
- **Q1 slower than projected (22 h).**
  - A5-D keeps WX + probe up to a Q1 1.59× its projection: at +10/+25/+50 % it keeps both (margins 14,983 / 10,440 / 2,869 s).
  - A1 keeps the probe only up to **1.008×**: at +10/+25/+50 % the probe is cut (cut 1) and WX runs.
  - WX fits up to 2.3× for both candidates, which is beyond Q1's own 2× cap. So WX always fits when Q1 completes.
  - At 16 h with cut 3, A5-D keeps both up to 1.27×.
- **Compliance with the lead's own limits.**
  - Made before any registered seed: there is no registered run directory or ledger entry.
  - Made to avoid registered cuts: cut 3 at 17.15 > 16, and cut 1 for A1.
  - Nothing added: the config diff is only `cap_hours` and the generation block, and seeds, thresholds and cells are unchanged.
  - Recorded in the ADR with the measured projection (sha256), the old and new cap, and what it protects. Memory caps are unchanged.
  - **Compliant.**
  - Two statements in the addendum need correcting (F5):
    - At 16 h, the probe would be cut only if A1 is the candidate, and WX would not be cut at projection for either candidate.
    - The A1 probe is "protected" only within a 249 s (0.8 %) margin.
- **Generation cap (66.9 s per draw, from one 33.4 s measurement at load ≈11).**
  - Busy-like load slowed the rehearsal by about 1.65×, which gives ≈55 s, under the cap with ≈18 % margin. At heavier load (59 was observed) a draw can exceed it.
  - A timed-out draw has no G1 result, and `core.plan_draws` counts that as a G1 failure. So it is replaced by a reserve labelled REPLACED BY RESERVE; more than two timeouts stop everything (F7, PENDING LEAD REVIEW).
  - Adequate if registered generation runs at a load comparable to the measurement.

## 5. Consistency with the measured rates; the cap table (task 5)

I computed the table myself (`scripts/p6_caps.py`). The implementer's `caps` command, run in my throwaway clone with the same inputs (A = 2, R = 4 as placeholders), wrote an identical table: `outputs/p6_caps_theirs_A2_R4.json` against `p6_caps_mine.json`.

| Entry | Cap (s) | Against 2× the measured busy figure |
|---|---|---|
| q1 full train / evaluate | 58,850.8 / 1,720.8 | = 2× busy (ratio 1.000) |
| q1 cut3 train / evaluate | 40,780.0 / 1,267.9 | = 2× busy |
| wx A5-D train / evaluate | 5,874.3 / 192.7 | = 2× busy |
| wx A1 train / evaluate | 7,653.1 / 189.1 | = 2× busy |
| probe A5-D train / evaluate | 23,497.3 / 152.4 | = 2× busy |
| probe A1 train / evaluate | 39,461.8 / 175.4 | = 2× busy |
| generate (per draw) | 66.90 | 2× one measurement at load ≈11, **not busy** |
| gates (13 draws) | 156.17 = 2 × (39.755 + 12 × 3.194) | 2× a measurement at load ≈11, **not busy**. With the re-check's I1 ratio (1.6 per draw) the estimate is ≈103 s; with an additional busy factor of 1.65 it is ≈170 s, **above the cap** (F7) |
| analysis / report | 60 / 60 (floor) | measured values pending (step 8) |
| reserve | 60 | |

- **`require_room` and the pool backstop.** Under a passing headroom decision, every later stage fits: Q1 train needs 58,851 ≤ 78,134 remaining; after WX and the probe at their caps, 2 × reserve = 120 s remain for the 60 s analysis and 60 s report.
- **Design-time figures.** `PROJECTED_OTHER_HOURS` = 0.8 is only informational; the measured "other" is ≈0.3 h. The ADR's §10.4 multiples ("Q1 uncut up to m ≈ 1.85") are superseded: the measured Q1 is 2.16× the slowest design rates. The frozen `projection.json`'s `freeze_information` was computed at 16 h with 0.8 h of "other" (F4).

## 6. The intermittent watchdog test (task 6)

**Cause, reproduced.**

- On this macOS, `os.killpg` on a process group whose only member is an unreaped zombie raises `PermissionError: [Errno 1]` (5/5 trials, `outputs/p7_killpg_zombie.txt`).
- `arborlm.watchdog._stop` (`src/arborlm/watchdog.py:60-68`, graceful=False) first SIGKILLs the child through psutil, then calls `os.killpg`, and catches only `ProcessLookupError`.
- If the child has exited before `killpg`, the call raises. `supervise` then records "watchdog error: PermissionError …" instead of "process wall-time limit exceeded", and the test fails. Whether it raises depends on timing, which is why the failure is intermittent.
- Reproduced directly: `watchdog._stop` on a zombie raised `PermissionError` (`outputs/p10_watchdog_stop.txt`).

**Effect on S0: none.**

- S0's registered stages use `studies/p9/pool.py:_kill`, which catches `(ProcessLookupError, PermissionError)`. The same zombie state passed with no error.
- S0 does not import `arborlm.watchdog`.
- `src/` is immutable; a fix there needs an approved amendment.

## 7. Unexercised before the freeze, and the freeze record (task 7)

**Unexercised.**

- **The e2e at `9cca808` or `af18a59`.** No evidence was committed, and the default variant is broken by the raise (F2).
- **Analysis and report timing on the full registry** (step 8).
- **The cap table and plan.** `caps` and `stage_caps.json` have not been written (my clone's table was a stand-in). `freeze-plan` has not been run on a real registered run directory.
- **Registered generation of 15 draws.** Only one draw was timed. `draw-plan` and reserve replacement have not been run.
- **Registered gates on 13 draws at real size.** The I1 per-draw ratio at real size is unknown. G10 under pins in registered mode is exercised only by the unit test.
- **Q1-gate cuts and stops.** Cuts 1 and 2 by budget, Q1 NOT RUN — MEMORY, and a block stopped at its cap at real size have not been exercised.
- **The candidate.** A candidate produced by the analysis has not been exercised; the e2e forces one.
- **The ledger cap.** The ledger file still records `cap_seconds` 57,600 (16 h). `remaining()` uses the config's 22 h, and the file is rewritten at the next charge (cosmetic).

**The freeze record must contain:**

- **README step 10 items.**
  - Code hashes (source, spec, config, frozen source).
  - The arm-selection record and its sha256 (e8bbd2c0…).
  - Data identities: all 15 data manifests and the draw plan.
  - The rehearsal-draw gates record.
  - `stage_caps.json` and its sha256, with the source file and field of every typed input: G = gates manifest task seconds, P = `gates.json` `timing.per_draw_seconds`, A, R, and N = 33.44888391700806 at full precision (F9).
  - The projection sha256 d6f6e6be…, with the recomputed informational values at 22 h (F4).
  - Cut 3 and its label.
  - The launch commands.
  - The §18 conditions.
  - The generation cap and its measurement.
  - The pinned auditor scripts (886e2d27…, c3629201…).
  - The auditor's recomputation file and its sha256.
  - Every implementer-worded string, as in the generated README table plus the step 10 list.
- **From the rulings and the re-check.**
  - `guard_seconds_per_task` = 0.387 s, as an implementer addition.
  - `plan.json` with `"profile": "registered"`, no TEST_PROFILE marker, and added exactly once.
  - The S0 suite green on the frozen tree.
  - The e2e (both variants) green at the pre-freeze commit.
- **From this audit.**
  - The rehearsal and gates were run at `9cca808`, and `train/evaluate/model/p9*` are byte-identical at the freeze.
  - The pipeline check ran at `3a9a742`.
  - The cap raise from 16 to 22 h, with the A1 probe margin of 249 s.
  - The generation and gates caps were measured at load ≈11, not busy.

## Findings (file:line, fix, whether the rehearsal must be repeated)

- **F1 (major).** S0 suite red at `af18a59`: 9 tests read the real config's cap and assert 16-h behaviour.
  - The tests: `tests/test_p10s0_budget.py:136,147,158,173,180`, `tests/test_p10s0_core.py:249`, `tests/test_p10s0_governance.py:330`, `tests/test_p10s0_recheck.py:194`, `tests/test_p10s0_stages.py:111`.
  - With `cap_hours = 16.0` in my clone all 9 pass (`outputs/pytest_9_with_cap16.txt`).
  - Fix: pass `cap_seconds=16*3600` to the worked-example tests of ADR §10.4, assert `== core.cap_hours()*3600` for the ledger tests, and assert the config's value equals the ADR-recorded raise.
  - Must be done before the freeze, since tests are compared with the freeze commit. **No rehearsal repeat** (tests are outside the source digest).
- **F2 (major, by code reading; not executed).** `studies/p10s0/e2e.py:29` fixes `SCALED_Q1_FULL_HOURS = 8.3` for a 16-h cap.
  - At 22 h, 2 × 8.3 + ε ≤ 22, so no cut 3 applies, and `e2e.py:225-226` raises "the Q1 start record does not carry cut 3".
  - Fix: derive the scaled hours from `core.cap_hours()` of the clone, for example 0.55 × cap, so that 2 × full > cap ≥ 2 × cut 3. Re-run both variants.
  - **No rehearsal repeat** (`train/evaluate/model` untouched). The e2e must be re-run.
- **F3 (minor).** `stages.py:1271-1276` writes `q1_start.json` before `run_block`'s `require_gates_passed` (`:865-867`).
  - Launching `q1.sh` before `gates.sh` leaves Q1 permanently refused ("already started").
  - Likewise, `q1_gate.sh` launched before Q1 has finished writes a once-only `q1_gate.json` with no candidate.
  - Fix: check `require_gates_passed` before the start record. Make `q1_gate` require the `train-q1` and `evaluate-q1` manifests.
  - No rehearsal repeat; re-run the e2e.
- **F4 (minor).** The frozen `projection.json`'s `freeze_information` says `rule_holds_before_q1: false` and `rule_would_hold_after_q1_at_its_projection: false`.
  - Both were computed at 16 h with 0.8 h of design "other".
  - At 22 h, the code's own formula gives true and false (22.40 h); with the measured charges and the reserve it gives true and true (21.93 h).
  - Fix: state both in the freeze record. Nothing is re-run.
- **F5 (minor, ADR addendum text).** The addendum's "after Q1 the probe, and possibly WX, would be cut" is too broad.
  - At 16 h with cut 3, at projection, A5-D keeps both blocks and A1 loses only the probe.
  - Fix: state the 249 s A1 margin in the freeze record.
- **F6 (minor, stale text).** Stale 16-hour wording remains in:
  - README:147 ("at most 16 hours");
  - the docstrings at `budget.py:192`, `core.py:3,941,943` and `stages.py:9`.
  - Fix together with F2/F3.
- **F7 (PENDING LEAD REVIEW).** Generation (66.9 s per draw) and the gates (156 s) are capped at 2× measurements taken at load ≈11, not under busy load.
  - A timed-out draw counts as a G1 failure (`core.py:565-579`) and consumes a reserve.
  - Gates INCOMPLETE stops the run.
  - Either run `generate.sh` and `gates.sh` at a load no higher than measured, or rule on the treatment of a generation timeout. The formula is the lead's ruling, and no threshold is to be relaxed here.
- **F8 (informational).** `stages.py:1262` `ran` includes the rehearsal-draw run's `gates` ledger entry. `before_q1_projected_seconds` is therefore never counted. This is harmless, because the registered gates must have run and been charged.
- **F9 (informational).** `caps` takes typed numbers. Its `generate` must equal the config cap exactly (`stages.py:1051` compares floats), so pass `--generate-wall-seconds 33.44888391700806` (the manifest task seconds), not the ledger's 33.455. Name each input's source in the freeze record.
- **F10 (informational).** The A2 pre-item rate fields in `projection.json` are the post item's (label collision). Unused.
- **F11 (informational).** `work rehearse-cell` has no `registered_worker_guard`.
  - A typed `--mode registered` builds the data of the named draw, but `train.check_job` refuses before any training ("mode 'rehearsal' cannot use … seed set"; shown on a test-profile stand-in, p8 g).
  - Defence in depth holds. Optionally add the guard.
- **F12 (informational).** The watchdog test (§6): `src/arborlm/watchdog.py:65-68` should also catch `PermissionError`. This needs an approved amendment. S0 is unaffected.

## Commands

The scratch directory is `/private/tmp/claude-501/-Users-daniellaloush-dandush03-ArborLM--claude-worktrees-arborlm-consolidation-experiment-2b31c1/cfc0efd5-b7ca-4602-959a-07fe6b8d4e7d/scratchpad/p10s0-prefreeze/` (written `$S` below). The worktree is written `<W>`.

- **S0 suite at HEAD:** `cd <W> && UV_NO_SYNC=1 nice -n 10 uv run --locked --offline pytest tests/test_p10s0_*.py -q -p no:cacheprovider --basetemp $S/tmp/pytest_head` → 9 failed, 400 passed, 2 skipped (188 s).
- **Frozen clone:**
  1. `git clone --no-hardlinks <W> $S/tmp/frozen_clone`, checkout `af18a59`.
  2. `stages.main(['caps', …])` with the real projection.
  3. Commit `results/p10s0-freeze-auditclone/DECISION.md` and a stand-in `plan.json`.
  4. `<W>/.venv/bin/python -m pytest tests/test_p10s0_*.py -q -rs --basetemp $S/tmp/pytest_clone` → the same 9 failed and 400 passed.
  5. With `cap_hours = 16.0`, the 9 failing tests pass.
- **Demonstrations:**
  - `PYTHONPATH=<clone> <W>/.venv/bin/python scripts/p8_demos.py <clone> <W>/.venv/bin/python $S/outputs/p8_demos.json`;
  - `scripts/p9_readd.py` in a second clone.
- **Independent recomputations:** `/usr/bin/python3 -I scripts/p2_records.py`, `p3_projection.py`, `p4_schedule.py`, `p5_headroom.py`, `p6_caps.py`.
- **Identity:** `scripts/p1_identity.py` on `git archive` trees of `9cca808`, `af18a59` and `3a9a742`.
- **Arms:** `docs/reviews/p10s0-implementation-audit-2026-11-15/scripts/a5_arms_identity.py` at HEAD.
- **Watchdog:** `scripts/p7_killpg_zombie.py` and `scripts/p10_watchdog_stop.py`.
- **Linters:** `uv run --locked --offline ruff check .` and `mypy src/arborlm studies/p10s0`.
- **Clean-up:** the temporary directories (clones, archives, pytest temps of about 11 GB) were deleted.

**Failed checker attempt, kept:** `failed_attempts/01_p8_demos_tmpdir_path_wrong.txt` (my own path error; it was rerun after the fix).

Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.
