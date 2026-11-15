# P10-S0 re-check of the fixes after the implementation audit (ADR-0020 rev 4) — before the rehearsal and the freeze

**Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.**

- Re-checked: worktree `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-afc8a4b295465fecc`, branch `claude/p10-s0`, HEAD `3a9a74235b49b53cfd72497edc8f081d1a1829d1` (fix commit; diff against `d27ba7f`). Working tree clean before and after; nothing in the repository edited; no commit.
- Re-checker: Opus 5.5 (`claude-opus-5-5`). I did not write the audited code or the first audit.
- Environment: macOS-27.2.1-arm64, Python 3.12.14, torch 2.8.0, uv 0.12.15, the worktree's `.venv` (no environment created). Commands were run with `cd <worktree> && PYTHONPATH=<worktree> .venv/bin/python …` or `UV_NO_SYNC=1 uv run --locked --offline …`. The machine was loaded (load average 7.7–27 at start: the lead's pipeline check and other studies), which matters for every timing below.
- Not done: no pipeline check, no gates on the rehearsal draw, no rehearsal, no registered stage in the real repository, nothing under `experiments/` read or written. Test seeds only (S0 unit-test sets 920001–920999 and the TEST_PROFILE sets). **One deviation, disclosed in §5:** running the S0 suite inside my throwaway frozen clone made a test start a *registered* generation of `p10s0-draw-1`; it failed before building any data (the clone has no corpus). No registered draw was built or seen.

## Verdict: READY AFTER LISTED FIXES

The rehearsal may proceed: no fix below touches `train.py`, `evaluate.py`, `model.py` or the P9-II code, and every evaluated quantity is bit-identical before and after the fix commit. **Before the generation cap is committed (README step 4) and before the freeze, N1 and N2 must be fixed, and the end-to-end exercise repeated.**

- **N1 (major — same class as M4, and it reaches registered generation):** two new S0 tests depend on the pre-freeze state of the real tree. Once the lead sets the generation cap (step 4) the suite is red, and once `DECISION.md` exists as well, a test **launches a registered-seed generation of draw 1 from inside pytest**, charged to the default (real) S0 ledger.
- **N2 (major, narrow — residual of M1):** a typed `work <worker> --mode registered` after the freeze trains or evaluates any registered cell with no ledger charge, no stage cap, no headroom decision and no Q1-gate check. Before the freeze, `work generate --mode registered` skips the acceptance, `DECISION.md` and provisional-cap guards of `cmd_generate`.
- Minors N3–N9 and the informational notes follow. The ruling on `guard_seconds_per_task` is **acceptable as an engineering correction to a projection** (§3).

## 1. M1–M10 and m1–m14: before / after

| Finding | Before (first audit / my rerun at `d27ba7f`) | After (3a9a742) | Fixed? | Evidence |
|---|---|---|---|---|
| M1 registered mode without the plan | typed `train --block q1` defaulted to registered, reached the pool with 190 tasks, no `load_plan`, no `q1_start.json` (`a7_registered_bypass.json`) | `train`/`q1-gate` without a mode: "has no default mode"; `train`/`gates`/`q1-gate`/`analyze`/`report --mode registered`: refused; `work … --mode registered` without a freeze commit: refused; with `--freeze-commit HEAD`: "plan.json does not exist at 3a9a742…"; `registered q1 --freeze-commit HEAD`: same. The predecessor's a7 run against HEAD with `check_preconditions` stubbed now stops in `run_stage_tasks → registered_state → load_plan` ("no freeze plan"). The commit that added the plan is required; HEAD is not a freeze | **Yes before the freeze**; residual after it (N2) | `outputs/r3_demos.json` (M1_typed), `outputs/after_a7_at_3a9a742.txt` |
| M2 driver overrides | cap 100 s → 1e9 s, RSS 1 TB, synthetic backbone, fresh ledger | each of `--stage-cap-seconds`, `--ledger-root`, `--experiments-root`, `--rss-*`, `--synthetic-backbone`, `--only`, `--cut3`, `--restore-split` refused by name; ledger and experiments roots fixed to the main checkout in registered mode; `limits()` ignores overrides in registered mode. `stage_cap()` still returns a typed value first (N9) | Yes | r3 `M2_driver`, `M2_functions…` |
| M3 A5-D strings | results.json lacked F1 + sentence; classes.csv lacked all three | analysis.json, q1_gate.json, RESULTS.md, results.json, classes.csv and stdout carry all three (synthetic row-4 A5-D, and in the e2e variant's real run directory). Records that are not products (stage manifests, gate_runs, per-cell train/eval/snapshot records, `gates.json`) name A5-D only as an arm identifier, without the strings (note I3) | Yes | `outputs/before_a6_at_d27ba7f.json`, r3 `M3_products`, `outputs/r7b_noncell_scan.txt` |
| M4 test fails once freeze files exist | `plan.json`/`stage_caps.json` absent asserted | "both or neither"; `test_no_s0_test_asserts_that_a_freeze_file_is_absent`. In my frozen clone 388 of 390 tests pass; **the 2 that fail are new state-dependent tests (N1)** | Partly — N1 | `outputs/m4_full_s0_suite_in_frozen_clone.txt` |
| M5 post-freeze records / cap raise | deadlock on records in hashed paths | `DECISION.md` under `results/` (not hashed, test covers a post-freeze commit there); cap fixed at the freeze (constant; config, studies, ADR, tests compared). The README's raise procedure is incomplete (N5) | Yes (N5 doc) | `test_records_after_the_freeze…`, r3 `cap_raise_config_only` |
| M6 analysis/report lock-out | no reserve | reserve = rehearsed analysis + report, doubled, in both rules; changes a full start into cut 3 at the margin and tips cut 1 at the Q1 gate. **Residual with the 60 s floor** (N4) | Partly — N4 | r3 `M6_*` |
| M8 gates cap | 2 × one-draw gates | 2 × (G + 12 P), P = `timing.per_draw_seconds`; registered gates time per draw also recorded. In the e2e variant the registered per-draw part was 1.6 × the rehearsal's (I1) | Yes | `outputs/e2e_variant_kept/stage_caps.json`, `gates.json` |
| M7 end to end | never run | the implementer's `python -m studies.p10s0.e2e` passed (exit 0, 727 s) here; my variant (probe allowed) ran the probe through the driver | Yes at tiny size (§6) | `e2e_implementer/summary.json`, `e2e_variant/summary.json` |
| M9 banner / branch | "has not accepted" | banner reads ADR-0019 §16 and prints the verbatim acceptance; `2bc8038` and `f442ac7` are ancestors of HEAD | Yes | r3 `M9_banner_*` |
| M10 cut-3 label | never printed | outcome label `… [one initialization seed per draw at 16,384]`, item 4 "(label: …)", classes section line, `q1_start.json` label = the ADR string; pooled line NOT AVAILABLE at 8K/16K under cut 3 (m10). Not in classes.csv (not required) | Yes | r3 `M10_cut3`; e2e summary `cut_label` |
| m1 ADDRESS STABLE | 11/20 NaN → median 0.9, STABLE | median 0.0, not STABLE, `non_finite` 11 | Yes | before_a6 / r3 |
| m2 G10 naming | "auditor's reading" | "IMPLEMENTER'S second reading"; README step 6 names the auditor's file and sha256 in the freeze record | Yes | `gates.py:435` |
| m3 unhashed G10 code | ran unpinned | freeze plan pins both scripts; G10 refuses to run a script whose hash differs. Not exercised by the e2e (G10's script is not run under tiny sizes) | Yes (unit test only) | `test_g10_executes_only_the_auditor_script_the_plan_pinned` |
| m4 H20-A | literal "not RELIABLE" | the ruling's sentence; 0 disagreements (§4) | Yes | r5 |
| m5 WX AUC | absent | `answer_site_auc`; my brute-force pairwise AUC (own 64-position zero-padded window, own cosine, ties ½, 8 sites vs 55 other positions) equals it exactly (0.7152876… WX-A5-D, 0.654296875 WX-A1; diff 0.0) | Yes | `outputs/r6_auc.json` |
| m6 i | not reported | median over cells of the smaller panel, in analysis and report | Yes | analysis.py, report.py |
| m7 swap accuracy = panel accuracy | not asserted | `check_swap_accuracy` raises on a difference > 1e-9 | Yes | evaluate.py:127 |
| m8 README step 3 / gates exit | G1 None, exit 0 on G1/G2 failure | README generates the rehearsal draw first; exit 0 only if G1 and G2 passed too | Yes | stages.py `work_gates` |
| m9 config name | `p10s0_addressing.toml` | `configs/p10s0_qualification.toml`, old file gone | Yes | |
| m10, m11 | | pooled line withheld under cut 3 at 8K/16K; item 5 prints ADDRESS RECALL, DENSE COMPARISON, sustained success and i | Yes | |
| m12 | | README note on `train.configure()` | Yes | |
| m13 generate.sh guards | flag only | typed cap, missing cap flag, overrides, missing acceptance, missing `DECISION.md`, provisional cap all refused (in `cmd_generate`; not in the worker — N2) | Yes (N2) | r3 `generation_guards` |
| m14 | informational | unchanged | — | |

## 2. The lead's rulings

| Ruling | Implemented exactly? | Note |
|---|---|---|
| Cap raise only before the freeze | Yes in effect: after the freeze the config, `studies/` (where `CAP_HOURS` lives), ADR and tests are compared with the freeze commit, so no raise can pass. Before the freeze the README's procedure ("change `cap_hours` in the config") is refused by `validate_config` ("expected 16.0; got 20.0") | N5 |
| Run decision outside the hashed spec | Yes: `results/p10s0-freeze-<date>/DECISION.md`; registered generation refuses without it; a post-freeze commit there does not stop a stage (test) | |
| Analysis and report reserved, doubled, at both evaluations | Yes as worded (`reserve_seconds` in `pre_q1_decision` and `post_q1_decision`; from `stage_caps.json` `measured.reserve_analysis_report`) | N4: the 60 s floor of their caps is not reserved |
| H20-A as the ADR sentence | Yes; 0 disagreements on 5,000 registries | |
| Config renamed | Yes | |
| Generation cap = 2 × measured, floor 60 s, freeze refuses while provisional | Yes: `set_generation_cap`, `validate_config` (cap must equal max(60, 2 × measured) unless provisional), `freeze-plan` and `verify_plan` refuse a provisional block, registered generation refuses it | N6: `set-generation-cap` accepts any generation manifest (the implementer's own e2e set it from a DRY generation) |
| WX before the probe | Yes, and **through the driver**: in my variant (`probe.sh` before `wx.sh`) the driver refused "WX runs before the 65,536 probe … run wx first" (exit 2); after `wx.sh` the probe stage ran | The check is "`evaluate-wx/manifest.json` exists": a WX block that stops before its evaluation stage (ledger refusal) leaves the probe refused for good; this can only happen when the budget is gone anyway |
| H20-O | Yes: NOT_EVALUATED → "not read", NOT QUALIFIED → "not supported", the 8K/4K class printed descriptively | |
| Printed strings listed in the freeze record template | Partly: README step 10 lists most, but not `NUMBER_LABELS`, `REGIME_TEXT`, `CALIBRATED_TEXT`, the "Cut 3 of section 10.4 applies …" sentences, the i and AUC description lines | N7 |

## 3. `guard_seconds_per_task` — ruling: **acceptable as an engineering correction to a projection**

- **Specified?** No. ADR-0020 §10.3 defines a block's projection as measured seconds per update × planned updates + measured evaluation, in rounds of six. The guard term, like the task start-up of the P9-II audit's B1, is an implementer addition to that formula.
- **What it is.** `measure_guard_seconds` (stages.py) times git status, `frozen_input_check`, four file hashes and 15 `git rev-parse` once, at `projection` time. It adds that time to every item's per-task overhead, so it is paid once per training task and once per evaluation task.
- **Effect on decisions.** It only increases projections. The block caps get slightly larger and the headroom rule slightly more demanding, so cut 3 before Q1 and cuts 1–2 at the Q1 gate become marginally more likely. It never makes the rule easier to satisfy. Size: in the real worktree it measured 0.57–0.75 s per task, so Q1 (230 cells × 2 tasks) gains about 460 × 0.7 / 6 ≈ 54 s on a block projected at 3–4 h (under 0.5 %).
- **Can it be tuned?** It is one wall-clock sample, recorded in the projection record (`guard_seconds_per_task`), whose hash the freeze pins. Re-running `projection` would give a different value, but the same is true of the rates themselves. It is not a free parameter.
- **Accuracy.** It underestimates the real guard. In my frozen clone the real `registered_state` took 0.51–0.87 s, against 0.36–0.47 s for `measure_guard_seconds` on the same tree. The projection recorded 0.26 s, measured earlier under different load. The size is negligible at real scale.
- **Recommendation.** List the term in the freeze record as an implementer addition. Optionally record the median of several samples. No lead ruling is needed unless the lead wants §10.3's formula applied literally (`outputs/r7_post_e2e_checks.json`).

## 4. `evaluate.py` and the arms (task 4)

- The fix commit does **not** move the read swap. It was already inside `p9iieval.eval_chunking` at `d27ba7f` (line 136 there). The change only adds `check_swap_accuracy` and, for WX cells, `answer_site_auc` after the swap.
- **Bit-identity.** `scripts/r4_eval_identity.py` ran once with the `d27ba7f` tree (`git archive` into `old_d27ba7f/`) and once with HEAD. It covered A0, A1, A2, A5-D, A6, A7, WX-A5-D and WX-A1 at 2K/4K, plus A0, A5-D and A6 at 8K/4K, six updates each, with both chunked and unchunked evaluation (22 records). Every key of every old record is bit-identical in the new one (floats compared by `float.hex`). The only new key is `answer_site_auc` on the four WX records (`outputs/r4_compare.txt`).
- **Arms equal `studies.p9ii`'s.** `train.py`, `model.py`, `studies/p9*`, `src/`, `uv.lock` and `pyproject.toml` are unchanged between `d27ba7f` and `3a9a742`. The predecessor's `a5_arms_identity.py`, re-run at HEAD, gives forward pass, parameters after 6 steps and task losses bit-identical for all 12 arm × stage pairs. WX differs only in `addition.wq` and gives W7's query and logits bit-identically. 8K/4K builds A0, A5-D and A6 and refuses A1 and A2. A2's AdamW step counters reset (`outputs/a5_arms_identity_at_3a9a742.json`).
- **Seeds and bounds.** The predecessor's `a10_seeds.py` and `a9_bounds.py` outputs at HEAD are identical to the first audit's.

## 5. Independent rule comparison (task 5)

- **Update.** The predecessor's `a1_rules_from_adr.py` was changed only in H20-A (the ruling's sentence) and H20-O (NOT_EVALUATED → "not read"). Diff: `outputs/a1_ruling_update.diff`.
- **Run.** `a2_compare_random.py` with 1,000 cases each at seeds 1, 2 and 3, plus 2,000 cases (seed 11) with `FORCE_COMMITTED=1`.
- **Result: 0 disagreements in 5,000 registries.** Coverage included outcome rows 2–6; H20-A supported / not supported / not read (2,985 / 966 / 190); H20-O supported / not supported / not read / not tested (591 / 310 / 70 / 3,170); WX PASSES / 4,096 ONLY / DOES NOT PASS; probe 0–3 of 3 and NOT_EVALUATED (`outputs/r5_compare_*.txt`).
- **Deviation (my own).** Running the full S0 suite inside the frozen e2e-variant clone, `test_registered_generation_needs_…` called `cmd_generate` in registered mode against the clone. The clone had a `DECISION.md` and a set generation cap, so every guard passed, and a stage `generate-p10s0-draw-1` started.
  - Its worker failed at reading the P5 corpus, which the clone does not have.
  - No data manifest or draw was written.
  - The clone's ledger received one entry of 1.3 s.
  - The failed records are kept in `outputs/e2e_variant_kept/pytest_registered_generation_attempt/`. This is finding N1.

## 6. The end-to-end exercise (task 6)

**What it covers (implementer's run here: exit 0, 727 s; summary in `e2e_implementer/summary.json`).** Everything runs in a throwaway `git init` copy of the tracked and untracked files.

- **Shim.** A `uv` shim runs the current interpreter, so no environment is built.
- **Before the freeze.** A tiny DRY rehearsal is used as both the alone and the busy rehearsal. A DRY generation sets the generation cap (measured 17.8 s, so the cap is the 60 s floor). Then come DRY gates and a projection whose seconds-per-update are scaled ×89.85 so that cut 3 applies, with the 32K/64K peak raised to 2 GiB.
- **Freeze.** `caps`, then a `DECISION.md` stand-in and a commit. `generate.sh` runs on a TEST_PROFILE run directory (13 test draws and 2 test reserves), then `freeze-plan --test-profile --test-candidate A5-D` and the freeze commit.
- **Registered sequence.** `gates.sh`, `q1.sh` (cut 3, with the label), `q1_gate.sh`, `wx.sh`, `probe.sh` (refused: NOT RUN — MEMORY), `analysis.sh`, `report.sh`, and a second `q1.sh` (refused).
- **The outcome is row 3, INCONCLUSIVE** (random backbone). The candidate A5-D was forced by `--test-candidate`.
- **My variant** (`scripts/r1_e2e_variant.py`, probe allowed) also covers: probe before WX refused by the driver; the probe stage run after WX; a 13-draw registered gates timing; and a probe evaluation stopped at its cap (I2).

**Can the test profile be active in a real registered run?** I tried each route:

- **Marker added after a registered freeze:** refused (`verify_plan`: the plan's profile is not the run directory's).
- **Marker removed after a test freeze:** refused.
- **`--test-profile` without the marker, or the reverse:** `freeze-plan` refuses.
- **`--dry-candidate` in a registered worker outside the test profile:** refused.
- **Under the test profile, can a registered seed be read?** No. `spec_for` and `set_names` resolve to `p10s0-test-*`, which are inside 920001–920999 (G9 asserts it).
- **The only way:** deliberately write `TEST_PROFILE` into the run directory before `generate.sh` and pass `--test-profile` to `freeze-plan`. `plan.json` then records `"profile": "test"`.
- **If that were done in the real repository:**
  - The real S0 ledger in the main checkout would be charged, because registered mode fixes the ledger root.
  - `RESULTS.md`, `results.json` and `classes.csv` would say nothing about a test profile, and `analysis.json` says `"dry": false` (N3).
  - That `plan.json` commit would block every later real freeze (N8).

**What remains unexercised before the freeze.**

- Real sizes and the real backbone and corpus. The template-pool check is skipped under tiny sizes.
- The real `uv run --locked` (the shim stands in for it).
- G10's Part 1 run and the pinned hashes in the registered gates (`run_script` is false under tiny sizes).
- G4's identity check on the rehearsal set at real size.
- Registered seed names and data.
- The busy-process rehearsal (the e2e uses one rehearsal directory for both).
- At the Q1 gate: cuts 1 and 2 by budget (only the memory cut is exercised), item 4's stop, and Q1 NOT RUN — MEMORY.
- A candidate produced by the analysis rather than forced.
- Draw replacement by a reserve after a G1 failure.
- A Q1 or WX stage stopped at its cap.
- The analysis and report times behind the reserve (the e2e uses 1 s stand-ins; the real analyze took 1.8 s and report 4.2 s).
- The real ledger with prior charges from the pipeline check and the rehearsal.

## 7. Remaining findings (file:line, fix)

- **N1 (major) — `tests/test_p10s0_governance.py:110-125` and `:311`.**
  - **What happens.**
    - `:311` asserts that the real config's generation block is provisional. It fails as soon as README step 4 commits the cap, and a fix after the freeze would change `tests/test_p10s0_*` and stop every registered stage (the M4 class).
    - `:123` expects `cmd_generate(--mode registered)` on the real tree to refuse because `DECISION.md` is missing. Once `DECISION.md` exists and the cap is set, it does not refuse: it starts a registered generation of draw 1 from pytest, with the run directory in pytest's tmp and the ledger at the main checkout's `experiments/`. With the real corpus present it would build registered draw 1 outside `generate.sh`. Demonstrated in the frozen clone: 2 failed, 388 passed (`outputs/m4_full_s0_suite_in_frozen_clone.txt`).
  - **Fix.**
    - Make both tests state-independent. Build a throwaway repo (with or without the acceptance, `DECISION.md` and a provisional cap), monkeypatch `stages.repo_of` to it, and monkeypatch `stages.run_stage_tasks` and `new_run_dir` to raise if they are reached.
    - Assert the provisional flag only on the throwaway config.
    - Add a suite-wide guard: no test may reach `pool.run_stage` in registered mode without a monkeypatched pool.
    - Re-run the suite on a clone that has a set cap, a `DECISION.md` and freeze files.
- **N2 (major, narrow) — `studies/p10s0/stages.py:311-322` (`registered_worker_guard`) and `:374-401` (`run_stage_tasks`).**
  - **What happens.** After the freeze, a typed `work train --mode registered --run-dir R --freeze-commit F --labels WX-WX-A1-2K4K-d01-j0` (a cell outside the plan; the candidate was A5-D) exited 0 and wrote `train.json`. The ledger went from 27 entries to 27. No stage cap, `q1_start`/headroom or Q1-gate check applied (`outputs/r7_post_e2e_checks.json`). Before the freeze, `work generate --mode registered` returns from the guard after the override check only, skipping `cmd_generate`'s acceptance, `DECISION.md` and provisional-cap guards and the ledger (by code reading).
  - **Fix.** Give workers a stage token.
    - `run_stage_tasks` writes `run_dir/<stage>/RUNNING.json` with a nonce and the task labels.
    - It passes `P10S0_STAGE_TOKEN=<stage>:<nonce>` through `pool.run_stage(env=…)`; the env dict already exists at :391.
    - A registered worker refuses unless the token matches a running stage of its run directory with no manifest yet, and its labels are among that stage's tasks.
    - Give `cmd_generate` the same token.
    - Test that a typed worker is refused, and that the e2e still passes.
- **N3 (minor) — `studies/p10s0/report.py:36` (`banner_text`), `stages.py:655` (`work_analyze`).**
  - **What happens.** Products of a TEST_PROFILE run are not labelled as such, and `analysis.json` says `"dry": false`.
  - **Fix.** Record `profile` in `analysis.json`, `q1_gate.json` and `results.json`. Print "TEST PROFILE — test seeds, tiny sizes, synthetic backbone; not a result" in the banner. Make `freeze-plan --test-profile` refuse unless an e2e-only environment variable (set by `e2e.clone_env`) is present.
- **N4 (minor; PENDING LEAD REVIEW) — `stages.py:970-975` (`reserve_of`), `:1120`, `:935`; `budget.py:284`.**
  - **What happens.** The reserve is 2 × (A + R) measured, but the analysis and report caps are max(60 s, 2 × measured), and `ledger.require_room` checks the cap. With A = R = 5 s and Q1 run to its cap under a rule that bound exactly, 20 s remain and the analysis is refused ("20 s … remain, less than the stage cap of 60 s") (r3 `M6_floor_case`).
  - **Options for the lead.** (a) Reserve the frozen caps: reserve = (cap_analysis + cap_report) / 2, so that doubling gives the caps. (b) Charge analysis and report without `require_room`. Either departs from the ruling's literal "rehearsed time, doubled" only by the floor.
- **N5 (minor) — `studies/p10s0/freeze/README.md:13`.**
  - **What happens.** A pre-freeze raise also needs `core.CAP_HOURS`, the re-rendered config and `test_p10s0_core`'s `cap_hours == 16.0` to change, since `holds()` and `Ledger` read the constant.
  - **Fix.** Say so in the README.
- **N6 (minor) — `stages.py:943-956` (`cmd_set_generation_cap`).**
  - **What happens.** It accepts any COMPLETE `generate-*` manifest, including a DRY one (which is how the e2e sets it) and the check draw's.
  - **Fix.** Require `mode == "rehearsal"` and the stage `generate-p10s0-rehearsal`; allow DRY only under the e2e's flag.
- **N7 (minor) — README step 10.**
  - **What happens.** The freeze-record list of implementer-worded strings is incomplete (see §2).
  - **Fix.** Generate the list mechanically, for example by printing every string constant of `classes`, `core`, `report` and `analysis` not found in ADR-0019/0020. Alternatively, attach a rendered RESULTS.md per outcome row for the lead's approval.
- **N8 (minor) — `stages.py:262-263`.**
  - **What happens.** `added[-1]` is the *oldest* commit that ever added `plan.json`. If `plan.json` is ever committed, removed and re-added, the real freeze is refused permanently (throwaway repo: `outputs/r8_readded_plan.txt`).
  - **Fix.** Use `added[0]`, the latest addition; the `studies/` tree comparison already binds HEAD's plan to the freeze's.
- **N9 (minor) — `stages.py:404-405` (`stage_cap`).**
  - **What happens.** In registered mode a typed `--stage-cap-seconds` is still returned first. This is unreachable today only because overrides are refused earlier.
  - **Fix.** Ignore it when `mode == REGISTERED` (belt and braces).

**Informational.**

- **I1 — gates per draw.** In the variant, the registered gates' per-draw part was 0.48 s against the rehearsal's 0.30 s (×1.6). The registered gates took 20.6 s against a measured 13.15 s (×1.57); the cap was the 60 s floor. The registered loop hash-verifies each draw against its manifest and builds draw 1 twice. The 2 × cap leaves about 25 % margin.
- **I2 — the probe's evaluation cap is the tightest in the plan.** The probe is one round of six cells, so its cap is 2 × one cell's evaluation. In my variant, under heavy load at tiny size, all six probe evaluations were stopped at 6.6–6.8 s against a cap of 6.5 s (projection 3.26 s), so evaluate-probe was INCOMPLETE. The implementer's e2e never reaches this, because its probe is refused for MEMORY.
- **I3 — records that are not products.** `gates.json` (G10's candidate list ["A5-D", "A1"]), stage manifests and gate/cell records name A5-D only as an arm identifier, without the three strings. I do not read §8.7 as covering them. The lead decides whether G10's candidate list is a "label".
- **I4 — unused generation cap.** `stage_caps.json` keeps an unused `generate` entry beside the config's generation cap, which is the one registered generation actually uses. Drop it, or assert they are equal.
- **I5 — deleted test files.** `check_preconditions` does not detect a `tests/test_p10s0_*` file deleted after the freeze (it predates the fix commit).
- **Item 7 (new changes in the fix commit).** No threshold, registry, run length or seed changed: the config diff is the `[generation]` block only, and seeds, bounds and arms are identical. No test was weakened in a way that hides a defect: the preconditions test now compares every change with the original freeze commit, and the config byte-equality test re-renders the file's own generation block, whose form `validate_config` checks. New registered-mode holes: N1 and N2.

## 8. What the lead must check in the rehearsal and gates records

1. The generation cap comes from the manifest `generate-p10s0-rehearsal/manifest.json` (mode rehearsal, not DRY). The config holds `provisional = false` and `cap_seconds = max(60, 2 × measured_seconds)`.
2. The rehearsal-draw `gates.json` has non-null G1 (the draw was generated first), `timing.per_draw_seconds` > 0, exit 0, G10 `auditor_script_run` true and the script's sha256. `stage_caps.json` gates = 2 × (G + 12 P). Keep the 1.6 × per-draw ratio of I1 in mind.
3. The projection record:
   - `unit_updates` = 8192 and `missing_items` empty.
   - The alone and busy rehearsals are distinct directories, with `busy_processes` 12 recorded.
   - Every item is present: A2 pre/post, WX-A5-D, WX-A1, and 32K/64K for A5-D, A1 and A6.
   - `guard_seconds_per_task` is recorded and small.
4. Memory: every block's rehearsal peak (training, evaluation with the read swap, pool task) is ≤ 1.5 GiB, the probe's at 65,536 slots in particular.
5. Probe evaluation margin (I2): the 32K/64K items' `evaluation_seconds` against their task overhead, and the fixed parts of a registered evaluation task (manifest-verified data build, snapshot load, guard) against the 2 × one-cell cap.
6. Analysis and report wall times measured on synthetic full-registry records, not stand-ins. If 2 × (A + R) < 120 s, N4's floor case applies.
7. Freeze record:
   - `plan.json` `"profile": "registered"`, with no TEST_PROFILE file in the run directory.
   - `plan.json` added exactly once in history (N8).
   - The pinned auditor-script hashes and the generation block.
   - The guard term (§3) and the full string list (N7).
   - The S0 suite green on the frozen tree (N1).
8. The Q1 start record (`q1_start.json`): charged hours, the reserve, and the full / cut 3 decision against the projected numbers.

## Files (all under `/private/tmp/claude-501/-Users-daniellaloush-dandush03-ArborLM--claude-worktrees-arborlm-consolidation-experiment-2b31c1/cfc0efd5-b7ca-4602-959a-07fe6b8d4e7d/scratchpad/p10s0-recheck/`)

Scripts (`scripts/`):

- `r1_e2e_variant.py` — e2e variant with the probe allowed and WX after it.
- `r3_demos.py` — M1, M2, M3, M5, M6, M9, M10, m1 and the generation guards.
- `r4_eval_identity.py` and `r4_compare.py` — evaluate bit-identity before and after.
- `r6_auc.py` — independent AUC.
- `r7_post_e2e_checks.py` — product scan, typed worker, guard timings.
- `cmp/a1_rules_from_adr.py` and `cmp/a2_compare_random.py` — the predecessor's comparator, updated for the rulings.

Outputs (`outputs/`):

- `pytest_p10s0.txt` — HEAD: 390 passed, 1 skipped (the opt-in full e2e test), 272 s.
- `ruff.txt` — all checks passed.
- `m4_full_s0_suite_in_frozen_clone.txt` — 2 failed, 388 passed.
- `r3_demos.json`, `after_a7_at_3a9a742.txt`, `before_a6_at_d27ba7f.json`.
- `r4_eval_old.json`, `r4_eval_new.json`, `r4_compare.txt`.
- `r5_compare_*.txt`, `a1_ruling_update.diff`.
- `r6_auc.json`.
- `r7_post_e2e_checks.json`, `r7b_noncell_scan.txt`.
- `r8_readded_plan.txt`.
- `a5_arms_identity_at_3a9a742.json`, `a10_seeds_at_3a9a742.json`, `a9_bounds_at_3a9a742.json`.
- `e2e_implementer.stdout`, `e2e_variant.stdout`.
- `e2e_variant_kept/` — plan, caps, config, projection, ledger, q1_start, q1_gate, gates, RESULTS.md, the evaluate-probe manifest, and the pytest-started registered generation records.

E2E logs: `e2e_implementer/{e2e.log,summary.json}` and `e2e_variant/{e2e.log,summary.json}`. The clones (283 MB each) and pytest temp directories (3.9 GB each) were deleted. `old_d27ba7f/` (8 MB, a `git archive` of `d27ba7f`) is kept for r4.

Commands:

- `cd <worktree> && UV_NO_SYNC=1 uv run --locked --offline pytest tests/test_p10s0_*.py -q -p no:cacheprovider --basetemp <scratch>/pytest_tmp`
- `PYTHONPATH=<worktree> .venv/bin/python -m studies.p10s0.e2e --out <scratch>/e2e_implementer`
- `PYTHONPATH=<worktree> .venv/bin/python scripts/r1_e2e_variant.py <scratch>/e2e_variant <worktree>`
- `PYTHONPATH=<worktree> .venv/bin/python scripts/cmp/a2_compare_random.py 1000 {1,2,3}` and `FORCE_COMMITTED=1 … 2000 11`
- `.venv/bin/python -I -c "sys.path.insert(0,<tree>); runpy.run_path('scripts/r4_eval_identity.py')"` for each tree, then `r4_compare.py`.

Failed checker attempts, kept (`failed_attempts/`), all my own errors:

- 01 — `test_set(9)` is out of range (rerun with 8).
- 02 — the predecessor's a7 against the `git archive` tree fails because that tree is not a git repository. The predecessor's committed output stands as the "before".
- 03 — a shell variable invoked as a command.
- 04 — `git rm` removed the directory.

The pytest-started registered generation attempt is recorded in §5, not here, because it was a finding.

Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.
