# P10-S1 re-check of the fixes after the implementation audit (ADR-0021 §22, §22.1) — 2026-11-15

**Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.**

- **Auditor:** Claude Opus 5.5 (model id `claude-opus-5-5`), the arbor-auditor role.
  - I wrote none of the code under review: the implementation `8747af2` and the fixes `82e58dd` are by Sonnet 5.5, per the commit messages.
  - I did not write the first audit (`../AUDIT.md`). I re-ran its scripts unchanged and wrote updated versions in this folder.
- **Worktree:** `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1`, branch `claude/p10-s1`, HEAD `82e58dd`.
  - I edited nothing outside this folder and made no commit.
- **Environment:**
  - macOS-27.2.1-arm64, Python 3.12.14, torch 2.8.0, uv 0.12.15.
  - I used the existing `.venv` only and created no environment.
  - Commands ran from the worktree root as `PYTHONPATH=. uv run --locked python <script>`.
  - Scratch directory: `/private/tmp/claude-501/-Users-daniellaloush-dandush03-ArborLM--claude-worktrees-arborlm-consolidation-experiment-2b31c1/cfc0efd5-b7ca-4602-959a-07fe6b8d4e7d/scratchpad/p10s1-recheck/`. It was deleted at the end. Logs quoted here were copied into `outputs/` first, with the scratch path replaced by `<scratch>`.
- **What I ran:**
  - the unit tests;
  - my own scripts (`r1`–`r8`);
  - the predecessor's scripts, unchanged (`../c1`, `c2`, `c4`, `c4b`, `c6`, `c7`, `c9`, `c10`);
  - the implementer's end-to-end exercise, `python -m studies.p10s1.e2e`. It runs the DRY stage, then a tiny registered sequence on the test seed sets `p10s1-test-0..4` (bases 921001–921401);
  - my clone probes on those same test sets.

  The predecessor's scripts used test sets `p10s1-test-5`/`-6` (921501, 921601) and the frozen backbone B101/O301. **No calibration, rehearsal or registered stage was run, and no calibration, rehearsal or registered data was generated or read.**
- Other processes loaded the machine heavily throughout (1-minute load average 31–230). No wall time below is a measurement.

## Verdict: **READY AFTER LISTED FIXES**

Every first-audit finding I re-checked is fixed:
- M1, M2, M4, M5, M6, M7 and m1–m4 and m6–m16 are fixed. m5 is fixed, but its test now checks less than before (N5 below).
- **M3 is fixed for every typed command and the launch path, but not for the worker entry point (N1).**
- **M8 is done for the sequence it claims**, with the limits listed under M8.
- My independent implementation of §8.2–§8.8 with the §22 rulings agrees with `classes.py` and `analysis.py` on every case: **0 disagreements**.
- Nothing scientific changed: no threshold, registry, run length or seed.
- The P9-I bit-for-bit reproduction still holds.

New findings:
- **2 majors**, both on the integrity of the single registered run (N1, N2). Neither touches calibration or the rehearsal.
- **7 minors** (N3–N9). N9 answers the coordinator's question about the P6 full-suite failure.
- **2 points PENDING LEAD REVIEW** (P1, P2).

**Order.** I recommend making N1 and N2, and the minors the lead accepts, **before calibration**. Reason: every calibration record carries the code identity, and the freeze's `identity_drift` will list any later change. Either way, N1 and N2 must be fixed **before the freeze**.

### New findings

**N1 (major). The worker entry point still runs registered-mode training and gates with no freeze. Same class as M3.**
- **Where:** `studies/p10s1/stages.py:1444` (`verify_worker_plan`); `work_gates`, `work_train`, `work_evaluate`.
- **The check is circular.** The worker accepts any `--freeze-plan` file whose SHA-256 equals `--freeze-plan-sha256`, and the caller types both values on the same command line. Nothing binds the file to `studies/p10s1/freeze/plan.json`, to a freeze commit or to Decision 2.
- **What the workers skip** (r3 inspection):
  - they call no `check_preconditions`;
  - they read no ledger;
  - they do not check Decision 2.
- **Demonstrated in a clone** under the test switch (r4: test seeds only, tiny size):
  1. `generate.sh` produced the five draws.
  2. `work gates --mode registered --freeze-plan <self-made> --freeze-plan-sha256 <its digest>` exited 0 and wrote `gates.json`.
  3. `work train --mode registered … --labels P_F-OQ_f2048_n4096_d1_i2101_u8` exited 0 and trained the cell.
  4. The cell's `train.json` has `"mode": "registered"` and `"status": "completed"`.
  5. There was no freeze commit and no Decision 2.
- **Without the switch:** `seeds_for` gives `core.draw_seeds(k)`, i.e. the registered seeds. So the same three commands would observe registered seeds before any freeze. Generating those draws is allowed before the freeze.
- **The README is wrong here.** It claims "a registered worker needs the frozen plan and the digest the driver verified". The code does not check that the driver verified anything.
- **Fix:** in `verify_worker_plan`, when the mode is registered and the worker is not `generate`:
  1. require `Path(args.freeze_plan).resolve() == (core.repo_root() / FREEZE_PLAN).resolve()`;
  2. pass `--freeze-commit` through `common_args`;
  3. call `check_preconditions(REGISTERED, core.repo_root(), args.freeze_commit)`, `verify_plan(load_plan(repo), repo, Path(args.run_dir))` and `require_decision_2(repo, args.freeze_commit)`.

  These are git and hash calls costing about a second per task.
- **Test to add:** the r4 sequence, which must then refuse at step B1.

**N2 (major). The freeze accepts DRY records and a plan with U_P = 8.**
- **Where:** `stages.py:1118–1160` (`cmd_freeze`). Neither `cmd_freeze`, `verify_plan` nor `cmd_registered` reads a record's `"dry"` flag or the plan's `unit`; `grep '"dry"'` finds writers only.
- **Shown by the e2e run.** Its freeze ran without `--dry` on the DRY projection (`"dry": true`). That projection has `returns_to_lead` cleared, because `cmd_project` empties it in DRY mode. The DRY calibration bound to it still held two open returns to the lead: the load rule and the U_P check (`e2e_logs/04-dry_prerequisites.log`). The frozen plan had `unit` 8.
- The test switch changes only the manifest names in `cmd_freeze`. So the same freeze **without** the switch would freeze real registered draws against DRY records.
- **Consequence:** registered cells at real size would run for 48 updates. That run would be the single registered run, and it cannot be repeated.
- It needs an operator to pass the wrong files, but the guard is two lines.
- **Fix:** unless `core.test_switch()`:
  - refuse when any bound record (projection, calibration, timing, gates) has `"dry": true`;
  - refuse when `plan.unit != core.U_P`;
  - refuse when the calibration's own `returns_to_lead` is non-empty;
  - in `cmd_registered`, refuse a plan whose `unit != core.U_P`.

**N3 (minor). M5's descriptive texts are computed but not printed beside the label.**

- **The matched-updates text** (`mu_text`):
  - It reaches RESULTS.md only inside the CAPACITY-POSITIVE outcome line.
  - Where an arm carries DENSE NOT ESTABLISHED AT MATCHED COMPUTE and is not positive, the text is in `analysis.json` only. The capacity table prints just the label (`report.py:58`).
  - r6: `slow_large` (CAPACITY_ONE_TRANSITION arms) and the directed-transition scenario show the label without the MU text in RESULTS.md.
  - The ruling says that text "is printed beside it".
- **The DENSE MATCHES sentence:**
  - `analysis.py:328–337` computes `dense_matches_sentence` verbatim.
  - Nothing in `report.py` or `classes.capacity_outcome` prints it (grep).
  - Under the frozen cost measure DENSE MATCHES cannot occur for a supported arm (see M6: every 65,536-slot dense pair is MC-SHORT). It can occur only for a non-supported arm whose CAPACITY STEPs all end at 16,384 slots, and then the §8.5 sentence would be missing.
- **Fix:** in `_capacity_table`, print `dense_detail.mu_text` after a NOT ESTABLISHED label and `dense_matches_sentence` after DENSE MATCHES.

**N4 (minor). The whole-update multiply-add formula omits the gather-weighted sum that §22.1 names.**
- The value read `combined = (weights[..., None] * table[chosen]).sum(-2)` (`studies/p9/model.py:463`) is elementwise. torch's FLOP counter does not see it, so the implementer's test cannot catch the omission.
- Missing per update:
  - F-OQ and T-OQ: 3·Q·8·32 = 98,304;
  - H8: 2·Q·8·32 = 65,536;
  - R2: 2·Q·1·32 = 8,192.
- Effect on totals: 0.01–0.16% (r2). No MC multiplier changes grid point.
- **Fix:** either add the term to `frozen.memory_madds` and `core.MADDS_FORMULA`, or have the lead record that it is excluded. The second option contradicts the §22.1 text as written.

**N5 (minor). The m5 fix narrowed the "no existing file edited" test.**
- **Where:** `tests/test_p10s1_core.py:243–250`.
- **What it no longer catches** (r7):
  - modified or deleted tracked files under `results/`, for example `results/p9i-run-attempt2-…/OUTCOME.md`;
  - `tests/test_p9*`, `tests/test_p5*`;
  - `studies/p10s0/`;
  - `docs/reviews/`;
  - `AGENTS.md`, `CLAUDE.md`, `docs/RESEARCH_LOG.md`;
  - a quoted (non-ASCII) path.
- The old test caught all of these. Exempting `docs/decisions/ADR-0021` is sound in itself: it is this study's own specification, it is amended only by the lead, and `check_preconditions` hashes it into the freeze. It matters only for uncommitted edits.
- **Fix:** fail on every non-`??` status line outside the study's own paths, and on `??` lines under the protected prefixes. That keeps m5 fixed (untracked review folders pass) and restores the old coverage.

**N6 (minor). `set-generation-cap --generation-seconds` writes a typed figure into the config with no record of where it came from.**
- **Where:** `stages.py:1034`.
- The README says the cap is twice the rehearsal's measured G1 time. The e2e run used the typed path with 600 s.
- The config line cannot show which of the two was used.
- **Fix:** write the measured seconds and the rehearsal manifest's SHA-256 next to the cap. Refuse `--generation-seconds` unless the test switch is on, or record it as "typed".

**N7 (minor). The freeze's `identity_drift` (m15) omits two things.**
- **The config's name.** The config changes after calibration by design (`set-generation-cap`), so the calibration, timing and gates records always differ from the frozen identity in `config_sha256`. `files_changed` is then `[]`, because `source_hashes` does not cover the config (e2e `plan.json`).
- **The projection record.** It carries no `identity` (`"NOT RECORDED"`).
- **Fix:** include the config in `files_changed`, and add `identity`/`source_hashes` to the projection record.

**N8 (minor). `work generate --mode registered` skips the provisional-cap and no-override refusals that `generate` now applies.**
- **Where:** `stages.py:1446` returns early for `generate`.
- Generation before the freeze is allowed, so this matters for the cap and the record only.
- **Fix:** apply the same checks in `work_generate` when the mode is registered.

**N9 (minor; the coordinator's P6 question). An S1 test leaks process-global torch and RNG state into the pytest process. The P6 failure does not reproduce from S1.**
- **Where the state changes:** `studies/p10s1/stages.py:1469`. `main()` calls `configure()` (`train.py:524–532`, i.e. `arborlm.engine.configure_cpu`) for every `work` command **before** the worker runs or refuses. `configure_cpu` sets, and never restores:
  - the intra-op threads to 1;
  - the inter-op threads to 1;
  - `use_deterministic_algorithms(True)`;
  - the default device to cpu;
  - `torch.manual_seed(42)` and `random.seed(42)`.
- **Which test triggers it:** `tests/test_p10s1_stages.py:56` (`test_calibrate_worker_refuses_other_cells_before_building_anything`) calls `stages.main(["work", "calibrate-cell", …])` in process four times.
  - r9 (`outputs/p6_leak/r9_process_state.json`) measures the state before and after one refused call: threads 6 → 1, inter-op 18 → 1, deterministic False → True, and the torch and Python RNG states change.
  - The other in-process `work` calls (`tests/test_p10s1_audit_fixes.py:305`, registered mode) are refused by `verify_worker_plan` before `configure()` runs, so they leak nothing.
  - `model.build_model(seed_rng=True)` (`model.py:337–341`) also reseeds the global generators. Tests call it with `seed_rng=False` (r2 check), and the e2e runs in subprocesses.
- **Does it explain the P6 failure? It did not reproduce.** I ran `tests/test_p6_retrieval.py::test_dry_run_end_to_end_on_a_synthetic_fixture` in the same pytest process after each S1 test file, after the leaking test alone, and after all eight files together. It **passed every time** (`outputs/p6_leak/`):

  | Run | Result |
  |---|---|
  | alone | 1 passed |
  | after analysis | 24 passed |
  | after audit_fixes | 65 passed |
  | after budget | 17 passed |
  | after classes | 29 passed |
  | after core | 18 passed |
  | after e2e | 3 passed, 1 skipped |
  | after model | 43 passed |
  | after stages | 25 passed |
  | after the leaking test alone | 2 passed |
  | after all eight files | 217 passed, 1 skipped |

  - **Why the leak does not break this test:** P6's in-process CLI skips its own `configure_cpu` when intra-op = 1, inter-op = 1 and deterministic are already set (`src/arborlm/p6_retrieval_study.py:331–337`). Those are exactly the values S1 leaves behind. P6's workers are subprocesses and configure themselves.
  - **I did not have the failure message.** The coordinator's note gives none, and I did not re-run the 35-minute full suite. So the cause of the full-suite failure is **not determined** by me.
  - Candidates other than S1 state:
    - load-dependent timing inside the P6 dry run (its stage and worker caps, `src/arborlm/p6_stage.py:249–250`);
    - its end-of-worker source and archive re-checks (`p6_sources_unchanged`, `archive_unchanged`);
    - its `_real_results_listing()` before/after equality (`tests/test_p6_retrieval.py:1657`).

    Each of these can fail when other agents write into the shared repository during a 35-minute run. Test files that sort between `test_p10s1_*` and `test_p6_*` were not tested here.
- **Fix (S1):** make `stages.main` call `configure()` only after the worker's argument checks, and run it in a subprocess-only path. Or have `configure()` save `torch.get_num_threads()`, `torch.are_deterministic_algorithms_enabled()`, the default dtype and device, and the torch and Python RNG states, and restore them in a `finally` when called in process. Note that inter-op threads cannot be reset once set, so the cleaner fix is not to call it in the test process at all: make the test call the guard (`stages.calibration_guard`) directly, or run `main` in a subprocess. Add a test that snapshots that state before and after `stages.main(["work", …refused…])` and asserts it is unchanged. Getting the failure message from the full-suite log is the first step to settle the P6 failure itself.

### PENDING LEAD REVIEW

**P1. Lane L under ruling (b).**
- The ruling says: "If S0 qualifies an interface before S1's freeze, the question returns to the lead; nothing is printed OMITTED by default".
- The freeze returns to the lead only when the lane **would run**:
  - S0 is ADDRESSING-QUALIFIED (4,096 AND 16,384);
  - the candidate is not A1 or A2;
  - S0 is overload-qualified.
- For three S0 outcomes it prints OMITTED without returning (`frozen.py:216–240`):
  - "QUALIFIED AT 4,096 ONLY";
  - qualified with candidate A1 or A2;
  - qualified but not overload-qualified.
- These are §5.6 items 2–3, so the implementation follows §5.6. Whether ruling (b) meant "any qualification" or "qualified so that the lane runs" is the lead's call.
- Conservative choice: return to the lead on any S0 qualification.

**P2. Decision 2 is checked only by text.**
- `require_decision_2` (`stages.py:1267–1276`) checks only that a committed `results/p10s1-freeze-*/DECISION_2.md` contains the full 40-character freeze hash.
- A file that records a **refusal** of the run passes (r4 C10).
- A 12-character hash is refused (C9).
- The code cannot judge approval. The lead should know the guard is a presence check, and either accept that or require a fixed approval line.

---

## 1. First-audit findings: before and after

"Before" figures are the predecessor's outputs in `../outputs/`. "After" figures are my re-runs at `82e58dd`, in `outputs/`.

| # | Fixed? | Evidence |
|---|---|---|
| **M1** | **Yes** | Before: `c1` study B, a_use 0.99 at every diagonal cell → implementation NOT ESTABLISHED. After: `analysis.py:418/422` passes I_use = facts × i. The same case gives **KNOWLEDGE SCALES WITH MEMORY** (r1). My own §8.6 rule against `study_b_label` agrees on 40,000 random cases with 0 mismatches; 3,050 of them are SCALES. (The unchanged `c1` script now passes per-fact i where I_use is expected, so its old "NOT ESTABLISHED" no longer tests anything: `r_c1_unchanged_script.json`.) |
| **M2** | **Yes** | Before: `c6`, `BEATS DENSE (DENSE AT CHANCE AT A2)` refused by `emit` and `printable`. After: accepted with the tag (`r_c6_tag_rule.json`). A second parenthesis is still refused (r8), so the widening is exactly one group. |
| **M3** | **Partly** | See below and N1. |
| **M4** | **Yes** | Decision 2 is a committed `results/p10s1-freeze-*/DECISION_2.md`. `results/` is not compared with the freeze commit. Shown: e2e probe "gates.sh before Decision 2" → exit 2; r4 C4–C9 (uncommitted, wrong commit, abbreviated hash → refused). README step 13 says so. See P2. |
| **M5** | **Yes, with N3** | Before (`c5` capacity scenario): every supported arm DENSE MATCHES with D-OQ at a_use 0.2. After (r6, same scenario): every arm DENSE NOT ESTABLISHED AT MATCHED COMPUTE (MC-SHORT), the outcome ends `… DENSE COMPARISON NOT ESTABLISHED AT MATCHED COMPUTE]`, and the reading is "Storage-half reading not available …". See the M5 detail in §2. |
| **M6** | **Yes, with N4** | §2 M6 table: the implementation's matrix-product count equals my hand count and torch's counter, exactly, for every arm and slot count. |
| **M7** | **Yes** | §2 M7: 50,000 random tie walks against my own walk (11,758 three-way ties), 0 mismatches. `finalize` passes the doubling-snapshot a_use trajectories (r5). |
| **M8** | **Done for what it claims** | §3. |
| m1 | Yes | `analysis.py:326` keeps DENSE AHEAD. My r6 wiring applies the same rule independently; 0 differences in 29 scenarios. |
| m2 | Yes | `c4`: overload + seed block on draw 1 is 204 cells (was 208); `only_impl` is now empty. |
| m3 | Yes (as ruled) | DENSE SPEED UNDECIDED: r1 compares it with my rule on 40,000 cases, 0 mismatches. EFFICIENCY-POSITIVE carries it in its bracket in every case (0 misses). |
| m4 | Yes, with N6 | `generate.sh` takes no cap. The cap comes from `[generation]`; a provisional cap is refused (r3). The projection charges 5× the rehearsal G1 time (`budget.Fixed.generate`). |
| m5 | Yes, with N5 | 207 p10s1 tests pass with this untracked folder present (t0). |
| m6 | Yes | Plurals and the per-replicate FASTER / REACHED ONLY BY THE LARGER are refused untagged (c6). Stdout, DRY_SUMMARY and the e2e summary print `classes.printable`. `results.json` has `store_only_tag` and `tag_note`. |
| m7 | Yes | The pause is 120 s × 3 retries (`timing.py:34`). |
| m8 | Yes | `_valid_work` uses `_clean_name`. |
| m9, m10 | Yes | The README states the pinned worktree and the cap of 16. `default_experiments_root` resolves to the main checkout's `experiments/` from a worktree (`studies/p9/core.py:1108`). |
| m11 | Yes | `study_b` adds `me_readout` (a_use and I_use at the ME update). |
| m12 | Yes | `--s0-record` → `fz.s0_status_and_lane`; the record is hashed into `plan.json`. See P1. |
| m13 | Yes | r6 directed-transition scenario gives CAPACITY NOT TESTED naming 16K→64K, with 0 differences from my wiring. r1: every directed case is named (0 unnamed). |
| m14 | Yes | `section_10_2_scenarios` plus `NEVER_NEGATIVE`. The unit test `test_section_10_2_scenarios_never_give_a_negative` passes. |
| m15 | Yes, with N7 | `identity_drift` is in `plan.json` (e2e). |
| m16 | Yes | `seed_check` adds the scope note. `c4b` is unchanged (no overlap). |

### M3 in detail
- **Predecessor's `c10`, unchanged:** argparse still parses the override flags, and `stage_cap()` still prefers a typed value (`r_c10_driver_arguments.json`, same as before). This is now harmless, because the refusal happens in `cmd_registered`/`main`.
- **r3, in process, refused before any git or data access:**
  - **Overrides:** all 20 override flags on `registered train` give exit 2: `--stage-cap-seconds`, `--ledger-root`, `--experiments-root`, `--rss-*`, `--only`, `--repo`, `--workers`, `--freeze-plan[-sha256]`, `--seed-block`, `--overload-u-p`, `--labels`, `--updates`, `--draw`, `--synthetic-backbone`, `--timing`, `--calibration`, `--results-dir`, `--restore-split`.
  - **`--dry`:** exit 2.
  - **Other commands in registered mode:** all 13 other commands with `--mode registered` give exit 2. The six that default to registered (train, evaluate, gates, simulate, analyze, report) also give exit 2 with no `--mode`.
  - **`generate --mode registered`:**
    - with a typed cap, ledger root or repo → exit 2;
    - with no override → exit 2, because this worktree's cap is provisional.
- **Without the frozen plan:** e2e probe "gates.sh before the freeze" and r4 A both give exit 2 ("no freeze plan").
- **With a non-freeze commit** (r4, clone):
  - freeze commit = an ancestor before a config change → refused ("configs/p10s1_capacity.toml at HEAD differs");
  - an ancestor before the freeze files → refused ("studies at HEAD differs");
  - the Decision-2 commit → passes `check_preconditions` (studies are equal) but is refused by `require_decision_2`. C8 and C7 show this.
- **What remains open:** the worker entry point (N1).

## 2. The rulings of §22 and §22.1

| Ruling | Implemented exactly? | Evidence |
|---|---|---|
| M5: label, sentence, MU text, bracket, storage half | Yes, except the printing gaps in N3 | Details below |
| M6: whole update incl. backbone; formula in config; FLOP test | Yes, except N4 | Table below. `[cost].madds_formula` equals `core.MADDS_FORMULA`, and that string matches the code term by term. |
| M7: faster learner, walk, smaller rate; ≥3 rates (§22.1); doubling snapshots | Yes | r1 `tie_walk`: 0 / 50,000. r5: through `finalize`, 0.003 is chosen "at 2048" (= U_P/4) when U_P/2 is equal. D-OQ calibration cells get `snapshot_updates(U_P, run)`. Note: the walk compares a_use (min over two draws, Panel A); the U_P selection itself still uses raw Panel A accuracy, as item 3 says. |
| (b) lane L | See P1 | — |
| (c) page-miss setting | Yes (text only; enters no rule) | `READINGS["simulation_setting"]` |
| (g) DEP at every snapshot ≤ run | Yes | r1 capacity panel: 0 / 60,000. In 20,866 of those cases the ruling changed the verdict compared with the old reads. The unchanged `c1`, on its own seed, now shows 20,790 mismatches for the same reason. |
| (h) blocking labels: either panel; store-favouring labels: both panels | Yes | DENSE AHEAD uses `any` over panels (r1 dense: 0 / 60,000). The unchanged `c1` now differs from the implementation in exactly its 15,419 "either vs both" cases, i.e. it matches the ruled reading. DENSE FASTER: per panel, either (r1). TREE_AHEAD / TREE_COMPETITIVE / BEATS DENSE: both panels (`classes.py:463`, r1 favourable pass with 119 BEATS DENSE). |
| (i) MC-AMBIGUOUS not established | Yes | It is treated like MC-SHORT in the dense label (r1). |
| (j) items 1 and 2 use a_use; §22.1 overload U_P uses a_use | Yes | r5, my test of the overload row (the implementer says theirs is missing). Raw accuracy 0.97 / a_use 0.93 for R2 makes the U_P check fail (12 failures). H8 at 0.95 / 0.85 is UNDERTRAINED. Overload F-OQ at 0.95 / 0.85 gives RETURN_TO_LEAD. Scenario 2 gives overload U_P = 16,384, where raw accuracy would have given 8,192. |
| (k), m3 | Yes | DENSE NOT READ and DENSE SPEED UNDECIDED never block and appear in the bracket (r1: 0 misses). |
| (m), (n) | Yes | Robustness is per panel (`analysis.robustness`, `evaluate.py:311` both panels). The seed block is unchanged (U_P and U_run, Panel A), which the ruling accepts. |
| m2 | Yes | `c4` gives 204. |
| m13 | Yes | r6, r1 |
| M4 | Yes | See §1 and P2. |

### M5 detail
These are my attempts to produce DENSE MATCHES, BEATS DENSE or the storage-half reading with a dense pair that is not established.

- **r1 `dense_label`:**
  - 60,000 random cell sets (two passes), in which up to two cells are MC-SHORT or MC-AMBIGUOUS. The not-established cells carry deliberately absurd MC numbers (d = −9, r = 0.01), which the rule must ignore.
  - Result: 0 mismatches with my rule, and **0 cases of DENSE MATCHES or BEATS DENSE when any pair was not established**.
  - DENSE AHEAD still takes precedence when MU or D-BEST shows it.
- **r1 `outcome`:** 296,352 combinations of arm class × dense label (six labels, including both NOT ESTABLISHED forms) × engineering / incomplete / directed. For each CAPACITY-POSITIVE, all four T-OQ/F-OQ-IVF work-label pairs were also tried.
  - 0 outcome mismatches.
  - 0 positives without the bracket where one was needed, and 0 with it where it was not.
  - **0 storage-half readings without an established, sublinear, positive T-OQ or F-OQ-IVF.**
  - 0 eligible cases missing the reading.
- **Registry level (r6):** the predecessor's `capacity` and `dense_ahead` scenarios now give CAPACITY-POSITIVE with the bracket and "Storage-half reading not available". The latter is still positive, because only T-OQ is DENSE AHEAD.
- **The sentence `C.DENSE_MATCHES_SENTENCE`** matches ADR §8.5 row 3 exactly. It is never printed (N3).

### M6: multiply-adds of one training update
Source: `outputs/r2_madds.json`. "Matmul" means the matrix products only; "whole" means matmul + gather-weighted sum + 4 × trainable.

| Arm, slots | k read | torch counter / 2 | impl. matmul | my matmul | my gather sum | trainable (built = impl. = mine) | my whole | impl. whole | impl. − mine |
|---|---|---|---|---|---|---|---|---|---|
| F-OQ 4K | 8 | 74,715,136 | 74,715,136 | 74,715,136 | 98,304 | 197,633 | 75,603,972 | 75,505,668 | −0.13% |
| F-OQ 16K | 8 | 125,046,784 | = | = | 98,304 | 787,457 | 128,294,916 | 128,196,612 | −0.08% |
| F-OQ 64K | 8 | 326,373,376 | = | = | 98,304 | 3,146,753 | 339,058,692 | 338,960,388 | −0.03% |
| T-OQ 4K / 16K / 64K | 8 | 60,100,608 / 60,297,216 / 61,083,648 | = | = | 98,304 | 197,889 / 788,481 / 3,150,849 | — | — | −0.16 / −0.16 / −0.13% |
| H8 4K / 16K / 64K | 8 | 57,937,920 | = | = | 65,536 | 132,097 / 525,313 / 2,098,177 | — | — | −0.11 / −0.11 / −0.10% |
| R2 (all) | 1 | 57,937,920 | = | = | 8,192 | as H8 | — | — | −0.01% |
| D-OQ 4K / 16K / 64K | — | 123,621,376 / 320,851,968 / 1,109,708,800 | = | = | 0 | 197,618 / 787,480 / 3,146,732 | equal | equal | 0 |

- **Backbone, forward and backward:** 32,901,120 + 24,643,584 = 57,544,704 by my hand count. The implementation gives the same, and so does the predecessor's `c3` counter (115,089,408 FLOPs).
- **MC multipliers under the multiply-add measure alone.** The CPU measure can only raise a multiplier, because the larger of the two is used.

| Pair | Multiplier | Status |
|---|---|---|
| F-OQ capacity 4K→16K | 1.70 | OK |
| F-OQ capacity 16K→64K | 2.64 | OK, read at 24,576 ≤ 32,768 |
| F-OQ dense 16K | 2.53 | OK |
| **F-OQ dense 64K** | 3.31 | **MC-SHORT** |
| T-OQ capacity steps | 1.04 / 1.16 | OK |
| **T-OQ dense** | 5.11 / 15.2 | **MC-SHORT** |
| H8 capacity steps | 1.03 / 1.10 | OK |
| **H8 dense** | 5.40 / 16.9 | **MC-SHORT** |

  My own totals give the same grid point in every pair.
- **What this means:**
  - **Every CAPACITY-POSITIVE will carry DENSE COMPARISON NOT ESTABLISHED AT MATCHED COMPUTE**, as §22 states.
  - For T-OQ and H8, the capacity-pair multiplier is now set by the **CPU** measure: the multiply-add ratios are 1.03–1.16.
  - F-OQ's 16K→64K readout is 24,576, not 32,768. The ruling says this makes MC readouts easier to establish.

## 3. M8: the end-to-end exercise
There was no log or summary in the repository; the opt-in test is skipped by default. **I ran it:** `uv run --locked python -m studies.p10s1.e2e --workdir <scratch>/e2e`.
- Exit code 0 after 15 min 6 s on a loaded machine.
- `"ok": true`. All 25 steps ended as expected, and the 3 refusal probes exited 2.
- The analysis was COMPLETE, with CAPACITY-INCONCLUSIVE and EFFICIENCY-INCONCLUSIVE, and the report was 39,245 bytes.
- Outputs: `outputs/e2e_E2E_SUMMARY.json`, `outputs/e2e_stdout.txt`, `outputs/e2e_logs/*.log`.

**What it covers.** In a source-only clone of the working tree, through the real launch scripts, in order:
- the probe before the freeze (no plan → exit 2);
- the DRY prerequisites:
  - calibration, which exits 1 with two returns to the lead, as DRY data does;
  - rehearsal, timing, synthetic records and projection;
- `set-generation-cap`;
- `generate.sh` for the five **test** draws (tiny, G1 passed);
- `freeze`, then the freeze commit;
- the probe before Decision 2 → exit 2;
- the Decision-2 commit;
- the typed-cap probe → exit 2;
- `gates.sh`, `train.sh`, `evaluate.sh`, `timing.sh`, `simulate.sh`, `analysis.sh`, `report.sh`, all exit 0.

It also exercises:
- `check_preconditions` passing on a real freeze commit;
- `verify_plan` against `plan.json` and `stage_caps.json`;
- `require_decision_2`;
- the ledger (12 entries);
- the clean-tree rule.

**What it does not cover:**
1. **Real seeds and the switch-off path.** The switch replaces `draw_names()`, the seeds, the sizes and the backbone. The `p10s1-draw-*` manifest names, the real G1/G2 over five registered draws, and the real backbone and corpus loading in registered mode are never exercised. This is correct by design, but it means the "switch off" branch of `seeds_for`, `verify_plan` and `cmd_freeze` is covered only by unit tests.
2. **Real size.**
   - U_P is 8 (DRY unit) and the DRY fact counts are used.
   - The six-worker memory peaks, 64K k-means and the 16-h ledger margin are not exercised.
   - `timing.wait_for_quiet` is replaced by `dry_quiet`, so the 120-s waits (m7) are not exercised.
3. **The overload row.** No `--with-overload` and no overload plan: the 38-configuration registry and the overload U_P path are not run end to end. They are covered by unit tests and my r5.
4. **The real projection.** The freeze took a DRY projection whose returns to the lead are cleared (N2). The path where the freeze refuses a non-DRY projection with open returns is not exercised.
5. **The measured generation cap.** The cap was typed (600 s), not measured from the rehearsal manifest (N6).
6. **The pinned-worktree procedure (m9).** A clone was used instead. In a clone `default_experiments_root` is the clone itself; in a worktree it is the main checkout.
7. **Other cases not run:**
   - `--s0-record`;
   - `--no-loaded-transitions`;
   - a cut-3 plan;
   - a seed block on two draws;
   - a failed cell or failed G1 draw (exit 1, record kept);
   - a re-run refusal of a completed registered stage;
   - the worker-entry bypass (N1).

## 4. Independent rule comparison (task 3)
**r1** (`r1_rules_updated.py`) is my code. It re-implements the parts of §8.2–§8.8 that §22 changed and imports the predecessor's own helpers for the rest. It never imports the implementer's computation.

| Rule | Cases | Mismatches |
|---|---|---|
| Capacity verdict, one panel (g) | 60,000 random | **0** (coverage: all 10 verdicts) |
| Dense label (M5, h), normal and favourable passes | 30,000 + 30,000 random | **0** (DENSE AHEAD, DENSE NOT ESTABLISHED, DENSE MATCHES, BEATS DENSE all covered) |
| Capacity outcome, bracket, storage-half reading, directed transition | 296,352 exhaustive | **0** |
| Dense faster + efficiency outcome (h, k, m3) | 40,000 random + 576 exhaustive | **0** |
| Study B with I_use (M1), normal and favourable passes | 20,000 + 20,000 | **0** (KNOWLEDGE SCALES 3,050, KNOWLEDGE DOES NOT SCALE 4,005, NOT ESTABLISHED) |
| Dense-rate tie walk (M7, §22.1) | 50,000, including 11,758 three-way ties | **0** |
| Unchanged rules (predecessor's code): step class, arm class, u_T, efficiency verdict/classes/outcome | as in `../AUDIT.md` | **0** |

**r6** (`r6_synthetic_registry_updated.py`): the predecessor's own run-directory writer and 28 scenarios, plus one directed-transition scenario, with my updated wiring. Compared with `analysis.analyze_study`, there were **0 differences** in every replicate verdict, step class, arm class, dense label (capacity and efficiency) and both outcomes. Every report rendered.

**Disagreements: none.**

**My own process, disclosed:**
- r1's favourable passes were edited **three times** after runs that lacked coverage. The earlier outputs are kept: `outputs/r1_rules_updated_run1.json`, `_run2.json` and `_run3.json`.
  1. The first run had no BEATS DENSE or SCALES cases.
  2. The second run had no SCALES cases, because per-value dips made "all 40 values ≥ 0.85" too rare.
  3. The third run was the same. I had put 0.66 in the choice list, and I_use ratios below 3 occur near a_use 0.86.

  Each edit is marked in the script. None was a disagreement with the implementation.
- Neither earlier run disagreed with the implementation.

## 5. What the fixes changed beyond the findings (task 4)
- **Thresholds, registry, run lengths, seeds:** no change.
  - The `git diff 8747af2 82e58dd` on `studies/p10s1/{core,classes,budget,calibrate,gates,train,model}.py` and `configs/` changes no constant other than the new label strings, `TEST_SWITCH_ENV`, `MADDS_FORMULA` and `GENERATION_DEFAULT`.
  - The config adds `[cost]` and `[generation]` only.
  - `c4` matches the predecessor's output except the m2 fix. `c4b` is identical.
  - `src/`, `studies/p9*`, `uv.lock` and `pyproject.toml` are untouched.
- **P9-I bit-for-bit reproduction:** no regression. `c2` re-run at `82e58dd` is identical to the predecessor's output: F-OQ and R2 equal P9-I's R1 and R2 under three trainers. `c7` (counters, swap, panel independence) is identical as well.
- **Tag check:**
  - No hole on the paths the code uses. It still refuses a second parenthesis, `F-OQ FASTER` and `CAPACITY STEPS` (r8).
  - The new lookbehinds `(?<!DENSE )(?<!NOT )` (`classes.py:70`) also let through `NOT CAPACITY-POSITIVE`, `IS NOT CAPACITY_SUPPORTED`, `DENSE CAPACITY STEP` and `DENSE BEATS DENSE`. The code produces none of these today.
  - Informative: narrowing the lookbehind to exactly `DENSE FASTER` / `DENSE NOT FASTER` would close it.
- **The test switch** (`P10S1_TEST_SEEDS=1`):
  - With it, registered mode accepts only `p10s1-test-0..4`. Without it, registered mode accepts only `p10s1-draw-1..5` (`core.py:817`, unit test, e2e).
  - It reaches worker processes through `os.environ` (`studies/p9/pool.py:329`).
  - It is not recorded in `plan.json` except through the test manifest names and `dry: true`. A real freeze bound to registered draws refuses under the switch, because the manifest names differ.
  - Informative: record the switch state in every record and refuse `freeze` with the switch on outside a clone.
- **Tests changed by the fix commit:**
  - `test_dense_faster…`: a right-censored D-OQ now uses lo = 8,193 instead of 1.0. This is legitimate, because `u_t` sets lo = U_run for a right-censored series.
  - `test_registered_mode_refuses…` now moves `repo_root` instead of passing `--repo`, since `--repo` is now refused.
  - Expectations changed per ruling: madds, calibration snapshots, the default scenario's reading.
  - `generate.sh` must now **not** contain `--stage-cap-seconds`, which is stronger than before.
  - Weakened: the m5 test only (N5). Adding `docs/decisions/ADR-0021` to the paths the test treats as the study's own is sound on its own terms; the narrowing is what weakens it.
- **Calibration cost:** the D-OQ calibration cells are now evaluated at about 8 snapshots instead of 2. This adds evaluation time, not training, and is charged to the ledger.

## 6. What the lead must watch in the calibration and rehearsal records
1. **`calibration.json`:**
   - **`dense_rates.<slots>.decided_by` and `walk`.** A tie is now resolved by code. Check that each walk value is an a_use from the doubling snapshots (U_P/2 … U_P/16 = 4,096 … 512), and whether "smaller learning rate (no snapshot separates …)" was used.
   - **The U_P check and the H8 report on a_use.** With raw accuracy above a_use, a failure here is not a typo.
   - **`identity`/`source_hashes`** must equal the code at the freeze, except for the config change `set-generation-cap` makes (N7).
2. **The cost table.** For T-OQ and H8, the capacity MC multiplier will come from **CPU**. Under the multiply-add measure the ratios are 1.03–1.16. Check whether the timing gives multipliers above 1.25 or 1.5, which move the readout.
   - F-OQ's 16K→64K readout lands at 24,576 when CPU ≤ 3 × the multiply-add multiplier, and above that if CPU disagrees in direction (MC-AMBIGUOUS).
   - Every dense pair at 65,536, and every T-OQ or H8 dense pair, is MC-SHORT, so every CAPACITY-POSITIVE will be bracketed.
3. **The rehearsal's `generate` manifest wall time.** It sets the generation cap. Record whether `set-generation-cap` was given `--run-dir` (measured) or `--generation-seconds` (typed) (N6).
4. **The rehearsal synthetic record:** `never_negative_violations` must be `[]`. The H8 DEPENDENCE_FAILED scenario may be NEGATIVE, as §22.1 rules.
5. **The projection:** `generation.five_draws_seconds` is included in `fixed.generate`. The headroom rule must hold under the 16-h cap with the larger D-OQ calibration evaluation already charged.
6. **The timing stage:** whether `wait_for_quiet` needed retries (120-s pauses). NOT MEASURED stops the projection.
7. **Before the freeze:**
   - N1 and N2 are fixed.
   - The e2e is re-run on the fixed code.
   - The freeze is given non-DRY records only.
   - `plan.json` shows `frozen.plan.unit == 8192`, `generation.provisional == false`, and a `table_facts` that matches the load decision.

## Scripts and outputs (this folder; outputs in `outputs/`)

| Script | What it checks | Output |
|---|---|---|
| `t0`: `uv run --locked pytest -p no:cacheprovider --basetemp <scratch>/pt tests/test_p10s1_*.py -k "not test_dry_" -q` | p10s1 unit tests except the 9 DRY-fixture tests. The DRY stage ran inside the e2e instead. | `t0_pytest_p10s1_no_dry.txt`: 207 passed, 1 skipped (the opt-in e2e), 9 deselected |
| `../c1`, `c2`, `c4`, `c4b`, `c6`, `c7`, `c9`, `c10` (unchanged) | Before/after re-runs | `r_c1_unchanged_script.json`, `r_c2…`, `r_c4…`, `r_c4b…`, `r_c6…`, `r_c7…`, `r_c9…`, `r_c10…` |
| `r1_rules_updated.py` | §8.2–§8.8 with the §22 rulings against `classes.py`/`calibrate.py` | `r1_rules_updated.json` (and `_run1`–`_run3`) |
| `r2_madds.py` | M6 whole-update multiply-adds three ways; MC multipliers | `r2_madds.json` |
| `r3_driver_refusals.py <scratch>` | M3 refusals in process; `verify_worker_plan` on a self-made plan | `r3_driver_refusals.json` |
| `r4_clone_probes.py <scratch>` | Clone under the test switch: worker bypass (N1); commit and Decision-2 checks | `r4_clone_probes.json`, `r4_logs/` |
| `r5_calibration_a_use.py` | (j), §22.1 overload a_use; M7 through `finalize` | `r5_calibration_a_use.json` |
| `r6_synthetic_registry_updated.py` (with `TMPDIR=<scratch>`) | End-to-end analysis vs my wiring, 29 scenarios; report contents | `r6_synthetic_registry_updated.json` |
| `r6b_dense_matches_sentence.py` | Attempt to reach DENSE MATCHES with a 16K-only dense pair. The predecessor's scenarios have 64K CAPACITY STEPs, so it stayed NOT ESTABLISHED; N3 rests on reading the code. | `r6b_dense_matches_sentence.json` |
| `r7_m5_test_predicate.py` | What the rewritten m5 test lets through | `r7_m5_test_predicate.json` |
| `r8_tag_lookbehind.py` | Tag-regex lookbehind cases | `r8_tag_lookbehind.json` |
| `r9_process_state.py <scratch>`; `pytest tests/test_p10s1_<file>.py tests/test_p6_retrieval.py::test_dry_run_end_to_end_on_a_synthetic_fixture` per file, the leaking test alone, all eight files together, and P6 alone (`--basetemp <scratch>/pt-*`) | N9: process-state leak and P6 reproduction | `p6_leak/` |
| `python -m studies.p10s1.e2e --workdir <scratch>/e2e` | M8 | `e2e_E2E_SUMMARY.json`, `e2e_stdout.txt`, `e2e_logs/` |

- `ruff.toml` here extends `../ruff.toml`. `uv run --locked ruff check docs/reviews/p10s1-implementation-audit-2026-11-15/recheck` passes.
- I did not run the full suite, `mypy` or `ruff check .`. Another process was running the full suite in this worktree.

**Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.**
