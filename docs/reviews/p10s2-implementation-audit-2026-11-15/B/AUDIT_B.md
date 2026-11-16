# P10-S2 implementation audit, part B (engineering): stages, launch scripts, freeze, ledger and caps, registered mode, rehearsal and the rung rule, the recomputation rule

Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.

- Object: pinned commit `8ad26b5` (`claude/p10-s2`), `studies/p10s2/`, `configs/p10s2_transfer.toml`, `tests/test_p10s2_*.py`, against ADR-0022 revision 5 (§9, §12–§13, §16, §18). The combined-tasks addendum is not implemented at this commit and its absence is not reported as a finding.
- Model that ran this audit: Opus 5.5 (claude-opus-5-5). I did not write any of this code.
- Environment: macOS 27.2.1 (26B131), arm64; Python 3.12.14; torch 2.8.0; MPS available. Interpreter `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a91c79a181109bb9c/.venv/bin/python`, working directory the pinned folder, `PYTHONDONTWRITEBYTECODE=1`, pytest with `-p no:cacheprovider`. The pinned tree was still clean (`git status --porcelain` empty) after every run. No network, no download, no real model or data, no calibration, rehearsal or registered seed drawn. My own checks used test seeds only (229501, 229777, and the stand-ins' own test-range seeds).

## Verdict: READY AFTER LISTED FIXES

Three blockers and twelve majors. None is a design problem; each has a concrete fix. **They are not all due at the same step:**

- **Before the data-generation step:** blocker B3. Data generation is not charged and writes no ledger entry. Its wall time cannot be recovered afterwards, and without it the freeze can never pass.
- **Before calibration:** blocker B1 (calibration crashes on MPS) and major M8 (the device is not frozen and `auto` falls back to CPU silently).
- **Before the rehearsal:** blocker B2 (`rehearse.sh` crashes), and majors M5, M6 and M7. The rehearsal produces the rates and memory peaks that the rung rule and every frozen cap are computed from, so they must be measured correctly the first time.
- **Before the freeze:** every other major, then an end-to-end run of the registered sequence (M12) and a re-audit of the fixes.

What I checked numerically is right:

- **Rung rule and cap extension.** Given the implementation's rate model, the logic matches my own code exactly: 0 differences over 7,680 grid points and 4,000 random points.
- **Dry stage.** It completes, writes only inside its run directory and leaves nothing in the temporary directory.
- **Stored-score recomputation.** In the dry run, the recomputation of cell scores agrees bit for bit.
- **Test suite.** 206 tests pass.

## Numbers recomputed (command, output file, result)

| # | What | Command (cwd = pinned folder) | Output | Result |
|---|---|---|---|---|
| T | p10s2 test suite | `PYTHONDONTWRITEBYTECODE=1 $PY -m pytest -q -p no:cacheprovider --basetemp=../p10s2-audit-B/pytest-tmp tests/test_p10s2_*.py` | `outputs/pytest_p10s2.txt` | 206 passed, 3 warnings, 212 s |
| D | dry stage | `PYTHONDONTWRITEBYTECODE=1 TMPDIR=<scratch tmp> $PY -m studies.p10s2.stages dry --run-dir ../p10s2-audit-B/dry1` | `outputs/dry1.txt`, `dry1/` | exit 0, gates ok, 7 min 17 s wall, 4.7 MB; recomputation `complete`, 0 differences; the temporary directory was empty afterwards; pinned tree clean. Label TRANSFER-NEGATIVE: NO-ACQUISITION (2 replicates, U = 4) is a mechanics check on stand-ins, not a result |
| B1 | rung rule and cap extension, grid | `$PY ../p10s2-audit-B/scripts/b1_rung_rule_recompute.py $PWD ../p10s2-audit-B/b1tmp` | `outputs/b1_rung_rule_recompute.json` | 7,680 points (scale × P ∈ {0.5, 3.5, 7, 12} × calibrated L × L12/L4 ratio × E-table ratio × start-up ∈ {0, 30 s}). Implementation's rate model: **0 mismatches**. ADR wording for the recomputation (timing row included): 117 mismatches. ADR wording for E-table (slower layer at U = 1,000): 0 mismatches on this grid. No start-up term (the ADR has none): 1,011 |
| B1b | the same, continuous random sample | `$PY ../p10s2-audit-B/scripts/b1b_random_grid.py $PWD ../p10s2-audit-B/b1tmp` (Python `random`, seed 229501) | `outputs/b1b_random_grid.json` | 4,000 points (implementation's outcomes: rung 1 934, rung 2 308, rung 4 321, NOT STARTED 2,437). Implementation's model: **0 mismatches**. E-table rule: **20 flips** (rung 4 becomes NOT STARTED: BUDGET); R(·, 1,000) up to 5.5% higher. Timing in the recomputation: **377 differences** (cap one hour higher, or a different rung). See M7 |
| B2 | registered driver guards in a throwaway git repo with a real `write_freeze` plan (heavy stage functions replaced by recorders; no world built, no seed drawn) | `$PY ../p10s2-audit-B/scripts/b2_registered_driver_bypass.py $PWD ../p10s2-audit-B/b2tmp` | `outputs/b2_registered_driver_bypass.json` | train runs with no `gates.json`; a typed `--caps` file replaces the frozen cap (90,520 s → 36,000 s); the registered ledger holds 0 h while P = 3.5 h, so a 33 h train cap starts against a 36 h cap; `--repo` checks a tree other than the code that runs; after 3 registered ledger entries, `record_raise` and a second `write_freeze` with the pre-freeze ledger are both **accepted** (cap 36 → 54 h); only the run's own ledger makes the freeze refuse |
| B3 | pre-freeze paths on stand-ins | `$PY ../p10s2-audit-B/scripts/b3_prefreeze_paths.py $PWD ../p10s2-audit-B/b3tmp` | `outputs/b3_prefreeze_paths.json` | `rehearse` with `rehearse.sh`'s exact flags: **TypeError at `int(args.layer)`**. Calibration's mid-training snapshot on MPS: stays on `mps:0`, and scoring it raises **RuntimeError (mat1 on CPU, expected GPU)**. CPU `index_put(accumulate=True)` with duplicate indices, deterministic off vs on: 200 of 200 trials differ bitwise; matmul at 1 vs 6 threads: equal. `select_device("auto")` without MPS returns `cpu` |
| B4 | does the memory measure see MPS memory? | `$PY -I ../p10s2-audit-B/scripts/b4_mps_rss.py` | `outputs/b4_mps_rss.json` | 2.00 GiB allocated on MPS (driver: 4.02 GiB): `ru_maxrss` rose **0.024 GiB** |

## Findings

### Blockers

**B1 — Calibration crashes on MPS at the first 1,000-update snapshot.** At `calibration.py:105-112` the snapshot is `copy.deepcopy(arm)` taken inside `on_update` while the arm is on the training device. `train_arm` moves only the live arm back to CPU (`train.py:156`), so the copy stays on `mps:0`. Scoring it with the CPU context raises `RuntimeError: Tensor for argument #1 'mat1' is on CPU, but expected it to be on GPU` (B3, test seeds). Calibration would stop after training its first cell. The dry stage and the tests never meet this, because they train on CPU.
*Fix:* take the snapshot as a CPU copy of the trainable state, e.g. `copy.deepcopy(arm)` followed by `.to(cpu)`, or a state-dict copy to CPU. Add a test with `device=mps`, skipped when MPS is unavailable.

**B2 — `rehearse.sh` cannot run.** The script passes no `--layer` (`launch/rehearse.sh:17`). The parser's default is `None` (`stages.py:426`), whose help text says the layer is read "from the calibration record in the run directory", but nothing reads it. `stages.py:381` then evaluates `int(args.layer)` and raises TypeError (B3). The script test (`tests/test_p10s2_prefreeze.py:67-84`) only checks that argparse accepts the argv, so it passes. This is the same class of failure as P9-II's GENERATE_ATTEMPT1.
*Fix:* read `selection.read_layer` and `selection.lora_lr` from `<run-dir>/calibration.json` and refuse if the file is missing or the pilot failed. Also use the calibrated LoRA learning rate, not `lora_learning_rates[0]` (`stages.py:381`). Test this by executing the script's argv through `stages.main` on a stand-in bundle, not just through the parser.

**B3 — The data-generation step is neither charged nor capped, and the freeze then deadlocks.**
- `datagen.py:202-214` writes no ledger entry and ignores its required `--stage-cap-seconds`.
- `freeze.prefreeze_caps_from_ledger` (`freeze.py:111-121`) requires a completed `datagen` entry, so `write_freeze` refuses forever ("still provisional").
- The rehearsal's headroom check reads P from `<run-dir>/ledger.jsonl` (`stages.py:379-386`), which leaves out data generation (projected at 1.0–1.8 h) and the fetch step. P is therefore understated by up to 1.8 h. That can choose a higher rung than the rule allows, or set the cap raise too low.

The time cannot be reconstructed once the step has run, so this must be fixed before data generation.
*Fix:* datagen (and fetch) run inside `Ledger(<study ledger>).charge("datagen", ...)` with a deadline, and refuse to start when the cap is exceeded. See M3 for the single study ledger.

### Majors

**M1 — The registered driver accepts overrides (defect class 2).**
- `--caps` is a free path, and `stages.py:308` uses the typed file for the deadline and the ledger check. `verify_plan` hashes only the frozen file (`freeze.py:93`). B2 showed a typed table replacing the frozen train cap.
- `--repo` (`stages.py:302,414`) points every check (clean tree, ancestry, frozen paths, plan) at another checkout, while the code that runs is `core.ROOT`. A modified working tree can therefore run under a clean clone's identity (B2d).

*Fix:* remove `--repo` from the registered parser (tests can monkeypatch `core.ROOT`). Either remove `--caps` or refuse any value other than `studies/p10s2/freeze/stage_caps.json` resolved under `core.ROOT`. Assert `Path(sys.modules["studies.p10s2"].__file__)` lies under the checked repository.

**M2 — Order of registered stages and write-once outputs are not enforced (classes 1 and 8).**
- `cmd_registered` (`stages.py:298-338`) never reads `gates.json`. `train` runs with the second gates stage absent or failed (B2a), against §12.3's "a failed gate stops the run".
- `evaluate` and `recompute` run without a completed train record.
- `analysis` runs before `recompute` and writes an INCOMPLETE `outcome.json`. `output.write_record` (`output.py:64-67`) overwrites, so a later rerun silently replaces a written outcome, and `evaluate/r*.json` can be rewritten by rerunning `evaluate`.
- `analyze` treats a missing `gates.json` as all gates passing (`analysis.py:345-347` iterates over an empty mapping).

*Fix:* each registered stage requires its predecessor's completion record (gates all ok → train → evaluate → timing → recompute → analysis → report) and refuses a second run if its own completion record exists. Outputs are write-once. Analysis refuses, or labels ENGINEERING-FAILURE, if `gates.json` is missing or any G1–G9 is absent.

**M3 — There is no single study ledger: P is outside the registered checks, and the cap-raise and freeze guards read a typed ledger (classes 3 and 6).**
- Registered stages charge `<run-dir>/ledger.jsonl` (`stages.py:311`), a different file from the pre-freeze ledger (README step 6 uses two run directories). `refuse_if_over` therefore starts from 0 h, not P. B2c: a 33 h train cap started against 36 h with P = 3.5 h.
- `write_freeze` and `record_raise` check "registered seed observed" only in the in-process seed record and in the ledger file they are handed (`budget.py:194-218`, `stages.py:395`). B2e: after registered processes had run, the README's freeze command raised the cap to 54 h and re-froze, and both were accepted. This violates §13.3, which allows the cap to be raised only at the rehearsal's headroom check and never after a registered seed is observed.
- `record_raise` does not recompute the proposal from the frozen rates and P. It trusts the caller's `rung1_total_hours` (`budget.py:213`), and `write_freeze` does not cross-check the raise file against `propose_raise(P, rates)`.

*Fix:* one append-only study ledger at a fixed path outside every run directory (for example `experiments/P10S2/ledger.jsonl`), used by fetch, datagen, calibrate, rehearse, freeze and every registered stage. The registered refusal reads P + charged + stage cap. `write_freeze` and `record_raise` refuse if any registered entry exists in that ledger, or if any committed `plan.json` exists in history. The freeze recomputes the proposal and refuses a raise file that differs.

**M4 — Budget enforcement during the registered run is coarse, and analysis and report can be locked out (class 6).**
- The deadline is checked only between replicates (`stages.py:82-90,106-112`), so `train` can overrun its cap by up to a whole replicate (about a quarter of training at n = 4).
- `gates`, `timing`, `analysis` and `report` get no deadline (`stages.py:327,330,332-333`).
- Neither the rung rule nor the caps reserve the analysis and report caps. `analysis` and `report` still pass `refuse_if_over` (`stages.py:313`), so a run that overruns can end with no outcome record. With the extension rule, the slack is under one hour by construction (cap = ceil(P + 2R)).

*Fix:* check the deadline per cell and per scored snapshot, and record the cell it stopped at. Every registered stage gets a deadline. Reserve the frozen analysis and report caps inside the rule (count them in R), or charge analysis and report without the room check. **PENDING LEAD REVIEW** on which, as in the P10-S0 audit's M6.

**M5 — The rehearsal does not measure what the registered stages do; R and the frozen caps are understated (class 6).**
- Timing benchmark: measured on 3 items of one panel, once (`rehearsal.py:92,119`). The registered stage runs 3 snapshots × 2 panels × 200 items × 3 repetitions (`stages.py:160-183`), about 1,200 times the measured work.
- Second gates stage: measured as `g4(world, plan0, 2)` + `g5` (`rehearsal.py:122`). The registered gates run G2, which is two complete Stage 0 scorings with subsamples, the "four scorings of E_A and E_B" of the ADR's own projection. They also run G4 with 20 updates on CPU twice plus 20 on CPU and 20 on MPS, and G6–G9.
- Router training: three routers per replicate, each embedding all its task prompts and 8,000 "none" prefixes, trained inside `evaluate` and again inside `recompute` (`stages.py:114`, `cells.py:170-176`). It is untimed: `build_routers` runs before `extra` is timed (`rehearsal.py:116-117`).
- Per-replicate extras: `extra × 11` (`rehearsal.py:126`) multiplies retrieval, which runs once per replicate, by 11. It omits the append-point scoring, the assembled composites, M-ii's D_con check and the ensemble.
- M-append-frozen and M-ii are timed with N-row stores (`rehearsal.py:49,53,75-76`), while the registered cells read 2N rows.
- §12.3 also requires the gates stage at real size on rehearsal seeds before the freeze. No pre-freeze gates command exists: `gates-rehearsal` is used only by `dry` (`stages.py:252`).

*Fix:* time the registered functions themselves at real size: `stage_timing` with the frozen item count and repetitions on one snapshot set, `gates.run_gates` with frozen arguments, `build_routers` and `router_record`, `assembled_scores` and `_consolidation`. Time each cell type in its registered configuration (MAF and M-ii from an appended 2N store). Add a pre-freeze `gates` command on rehearsal seeds whose measured time becomes `gates2_seconds`.

**M6 — The memory rule cannot see MPS memory, and nothing enforces memory at run time (class 7).**
- Training peaks are `ru_maxrss` (`rehearsal.py:25-27,78,109`). B4: a 2 GiB MPS tensor (4 GiB from the driver) raised `ru_maxrss` by 0.024 GiB. "Twice the measured peak within 8 GiB per worker and 24 GiB aggregate" is therefore unverified for MPS training.
- `recompute_peak_bytes` is copied from the evaluation peak, not measured.
- No registered stage has an RSS or MPS watchdog, and `memory_exceeded` is never passed (`stages.py:221`). The §13.3 rule "if the recomputation cannot be completed within the memory limits, the label is INCOMPLETE" can never fire, and a recomputation above 8 GiB counts as complete.

*Fix:* the training peak = max(RSS, `torch.mps.driver_allocated_memory()`) sampled per update, or the process footprint (`phys_footprint`). Measure recompute in its own process. Give each registered worker a sampled watchdog that stops the stage at the per-worker limit and writes a memory record; analysis reads that record into `memory_exceeded`.

**M7 — Two rate-model readings in the rung rule differ from the ADR text; rule logic is otherwise exact.**
- E-table: §13.1 counts E-table among the 16 store-type units, and §13.3 says "for every store-type cell, the slower of the rates measured at L = 4 and at L = 12" for U = 1,000. `budget.group_rate` (`budget.py:76-77`) gives ETABLE a single rate, measured only at the calibrated layer (`rehearsal.py:55`). B1b: 20 of 4,000 decisions flip from rung 4 to NOT STARTED: BUDGET, and R rises by up to 5.5%.
- Recomputation: the ADR projects it as "one repetition of the three scoring rows (an upper estimate, because the timing benchmark is not repeated)". Its table figures (5.82–18.84 h) include the timing row. `recompute_seconds` subtracts timing (`budget.py:106-108`). B1b: 377 of 4,000 decisions differ, mostly a cap one hour lower.

These are the "counts more time against the cap" choices of the ADR.
*Fix:* measure E-table at both layers and use the slower one at U = 1,000; include the timing row in the recomputation projection. If the implementer's readings are preferred instead: **PENDING LEAD REVIEW**.

**M8 — The device is not frozen, and "auto" falls back to CPU silently (class 11).**
- `RunConfig.registered(..., device="auto")` is used by registered stages (`stages.py:323`, `worldio.py:114`). `select_device("auto")` returns CPU when MPS is unavailable (`train.py:41-42`; B3d).
- G4 then records the MPS comparison as "not applicable", `ok: true` (`gates.py:118-125`). Training would run on CPU against rates rehearsed on MPS, and the projection and caps would be wrong.
- The device is not in the plan.

*Fix:* the rehearsal records the device it trained on; the plan freezes it; registered stages pass it explicitly and refuse if it is unavailable. "auto" is allowed only in `dry` and in tests. The ADR's own rule for unsupported MPS operations is "training moves to CPU and the rule is applied to the CPU rates", which must happen at the rehearsal, before the freeze, not silently at run time.

**M9 — The recomputation compares only cell records (the recomputation rule).**
- `stage_analysis` builds `rec_cells` from `rep["cells"]` only (`stages.py:217-220`), and `compare_cells` compares only `scores` and `extras` (`recompute.py:99-117`).
- The recomputed Stage 0 and teacher scores (every gap's denominator), the retrieval baselines, the assembled M-i-separate and L-sep, the router records (route accuracy, which decides ROUTER QUALIFIED) and the ensemble are recomputed into `recompute/` but never compared. The recomputed study also reuses the registered baseline (`analysis.py:417-419`).

§13.3 says "every registered score has been recomputed … and compared". As implemented, a Stage 0 or teacher difference cannot make a cell NOT_EVALUATED or the study ENGINEERING-FAILURE.
*Fix:* compare `baseline`, `assembled`, `retrieval`, `routers` and `ensemble` under the same tolerance cases. Use the recomputed baseline in the recomputed study. List every difference.

**M10 — Failed cells are kept only for non-finite losses; any other failure loses whole-replicate records (class 8).**
- `train_replicate` writes nothing until the whole replicate returns (`stages.py:89-90`). Any exception other than a non-finite loss (an unsupported MPS operation, a device error, an out-of-memory, a deadline) propagates out of `train_arm` (`train.py:139-157`, with no `finally`).
- The replicate's completed cells then have immutable snapshots but no train record, and `evaluate` scores them as "missing".
- The cells cannot be resumed either, because `save_arm` refuses existing snapshots (`world.py:127-128`).

*Fix:* write each cell's record as it completes. Catch per-cell exceptions as `failed` with the error text, and skip only the cells that depend on it. Move the arm and student back to CPU in a `finally`.

**M11 — The freeze takes typed design values and does not read the calibration or pilot outcome; post-freeze records deadlock (classes 2, 3, 5).**
- `cmd_freeze` / `write_freeze` take `--layer`, `--store-lr` and `--lora-lr` as typed values (`stages.py:392-398,436-438`) and only hash the calibration file (`freeze.py:154-173`).
  - A typed layer or learning rate different from the calibration's selection is frozen without complaint.
  - For U = 1,000 the selection must come from `selection_at_snapshot`, and it does not.
  - A failed pilot (NOT STARTED: STUDENT CANNOT USE THE MEMORY ON THIS TASK, §12.2) does not stop the freeze.
- `tests/test_p10s2_prefreeze.py:333` asserts that `plan.json` and `stage_caps.json` do not exist under `core.ROOT`. That test fails once the freeze commit adds them. Fixing it afterwards changes a `tests/test_p10s2_*` file, which `check_preconditions` (`freeze.py:55-57`) then refuses. This is the defect P9-II fixed in `2bc8038` and P10-S0's M4.
- `core.SPEC` (the ADR) is a frozen path (`freeze.py:29`). Any record written into ADR-0022 after the freeze commit therefore makes every registered stage refuse. That includes the lead's approval of the registered run, which §18 says needs "its own recorded decision". The README does not say where post-freeze records go.

*Fix:*
- Derive layer and learning rates from the calibration record, with the snapshot selection when U = 1,000.
- Refuse the freeze if the pilot failed.
- Change the test to "both or neither".
- Have the README name a post-freeze decision file outside every frozen path. Alternatively, require the approval to be committed with the freeze commit.

**M12 — The registered sequence has never been executed end to end through the launch scripts (class 4).**
- The tests check that each script's argv parses (`tests/test_p10s2_prefreeze.py:55-84`). The dry stage calls stage functions directly, without `cmd_registered`, the plan, the caps or the ledger checks.
- `rehearse.sh` crashes (B2) and calibration crashes on MPS (B1), which shows how far argv parsing is from execution.
- Nothing has run `datagen.sh` → `calibrate.sh` → `rehearse.sh` → `freeze` → commit → `gates.sh` … `report.sh`.

*Fix:* one end-to-end test in a throwaway git clone, with stand-in data and test seed sets substituted for the registered names and a tiny registered rung substituted through configuration. It executes each launch script's argv through `stages.main` (or the scripts themselves with a stub `uv`) in order. It includes one cap stop, one refused stage (no gates, typed caps) and one recomputation difference. Run it once before the freeze, and again after the fixes above.

### Minors

- m1. Pre-freeze `--stage-cap-seconds` is required but ignored by `calibrate` and `rehearse` (`stages.py:347-389`): no deadline and no ledger room check. The values are the provisional upper ends (`configs/p10s2_transfer.toml:182`). *Fix:* enforce them as a deadline, and refuse at start if the study ledger has no room.
- m2. The rehearsal's start-up measure builds the world in **test** mode with `RunConfig.dry()` and `provisional_combined=True` on the real bundle (`rehearsal.py:138-142`). This is class 10: a stand-in path reached from the rehearsal. It also draws test seeds on real data, and the whole-task peak it reports is for a dry-sized world. *Fix:* measure start-up by running the real registered entry (`build_world(bundle, "rehearsal", 1, RunConfig.registered(...))`) in the child process.
- m3. Evaluation runs with deterministic algorithms off; recomputation turns them on (`stages.py:189-194`). On CPU, `index_put(accumulate=True)` with duplicate indices differs bitwise between the two settings (200 of 200 trials, B3c). A read path with two reads at the same position (C2 sums both tasks' reads) would make cells NOT_EVALUATED by construction. Thread count is fixed only for timing. *Fix:* set the same deterministic flag and thread count (6, §10.2) in `evaluate`, `recompute` and the gates stage, and record them.
- m4. `write_freeze` writes `prefreeze_caps.json` (and `prefreeze_stop.json`) into the frozen folder even when it refuses (`freeze.py:144,161`). That leaves an untracked file, so the next pre-freeze stage refuses on an unclean tree. `plan["code"]` (`freeze.py:124-127,177`) is never verified. `studies/__init__.py` is outside `FROZEN_PATHS`. *Fix:* write refusal records outside the frozen folder; verify or drop `code`; add `studies/__init__.py`.
- m5. Any commit whose frozen paths equal HEAD's is accepted as the freeze commit, including a later one (`freeze.py:52-59`). The recorded identity is then not the freeze commit. *Fix:* require that `--freeze-commit` is the commit that added `studies/p10s2/freeze/plan.json` (`git log --diff-filter=A --format=%H -- studies/p10s2/freeze/plan.json`).
- m6. `record_raise` refuses a second raise only while `cap_raise.json` exists (`budget.py:207`), so deleting the file before the commit allows another. Covered by M3's fix (the raise recorded in the study ledger).
- m7. The registered `gates` stage builds G7's manifest from the current files themselves (`stages.py:273-274,327`), which makes the check tautological; `read_bundle` does the real check against `manifest.json`. G9's planned seeds are those of replicate 0 only (`stages.py:327`, `gates.py:278`). In registered train and evaluate processes the seed record is written nowhere. (Lanes A and C may report these too.)
- m8. The rehearsal never runs analysis and report on synthetic records of the whole registry (ADR §13.3 "Rehearsal content"); only the tests do. *Fix:* call the report test's synthetic registry from `rehearse`, or record that the tests stand for it. **PENDING LEAD REVIEW**.

## Item-by-item answers to the brief

1. **Registered mode without the frozen plan, caps and freeze commit.** Every registered stage calls `check_preconditions`, `load_plan` and `verify_plan`. No other command uses `registered-run` seeds, and an ancestor commit without the plan cannot pass, because the frozen tree includes `plan.json`. Holes remain: `--repo` (M1), a later commit accepted as the freeze commit (m5), and no ordering (M2).
2. **Overrides.** `--caps` and `--repo` are accepted (M1). There is no flag for ledger root, memory, synthetic stand-ins, subsets or replicate count. The device is not an argument, but it is not frozen either (M8). U comes from the plan.
3. **Freeze hashing post-freeze files; cap raise after a registered seed.** The plan names the raise file and refuses an unnamed one. The ADR is frozen, so post-freeze records deadlock (M11). The raise and a re-freeze are accepted after registered processes when given the pre-freeze ledger (M3, B2e).
4. **End to end through the launch scripts.** Never run (M12). `rehearse.sh` fails (B2). The registered scripts pass exactly `--run-dir`, `--freeze-commit` and `--caps`; datagen, calibrate and rehearse pass a cap that is then ignored (m1).
5. **Tests that fail once freeze files exist.** `tests/test_p10s2_prefreeze.py:333` (M11).
6. **Projections.**
   - Present: start-up, the second gates stage and the recomputation are in R.
   - Unmeasured or under-measured: timing, gates, routers and extras (M5).
   - Not projected: data generation is not charged (B3); analysis and report are not reserved (M4).
7. **Memory.** Training, evaluation, recomputation and task peaks enter `memory_check` with 2× against 8 GiB and 24 GiB (`budget.py:241-253`). But MPS memory is invisible, the recomputation peak is not measured, and nothing is enforced at run time (M6).
8. **Failed cells.** Non-finite losses are kept as failed, and dependent cells are skipped. Other exceptions lose the replicate's records (M10). Snapshots are immutable.
9. **Provisional pre-freeze caps.** Present, and the freeze refuses while any is provisional. Because data generation writes no ledger entry, it always refuses (B3). The caps are not enforced (m1).
10. **Stand-in paths.**
    - `provisional_combined` is refused outside test mode (`worldio.py:133-134`, `evaluate.py:166-167`).
    - `reference_standin` and `standins` are reached only from `dry`.
    - The rehearsal's start-up child reaches the stand-in path through test mode (m2).
11. **Device and CPU recomputation.**
    - Scores are computed on CPU: `evaluate.CPU`, and every arm is moved to CPU after training.
    - Timing threads are restored, and the recomputation's deterministic flag is restored.
    - Training device falls back silently (M8). Device mixing crashes calibration (B1). The deterministic flag and thread count differ between evaluate and recompute (m3).

Rehearsal now measures full-length store, M-ii and LoRA cells: **yes in code** (`rehearsal.py:62-80`, `--full-updates 2000`), with these limits:
- It cannot currently run (B2).
- M-ii is timed on a fresh N-row store, not on the appended 2N store (M5).
- LoRA uses `lora_learning_rates[0]`, not the calibrated rate (B2's fix).

## Outside lane B (one line each)

- (Known, addendum pending, not a finding) `score_snapshot(..., combined=True)` raises `PendingLeadReview` outside test mode, and `measure_rates` calls it (`rehearsal.py:117`). The rehearsal and the registered `evaluate` cannot run until the combined-tasks addendum lands.
- (Lane C) `analyze` does not turn a failed G2 ("scored identically twice") into ENGINEERING-FAILURE (`analysis.py:345-347` lists G1 and G4–G9 only).

## Scientific questions flagged

- **PENDING LEAD REVIEW:** M4 (reserve analysis and report inside R, or charge them without the room check).
- **PENDING LEAD REVIEW:** M7, only if the implementer's readings (E-table at one layer, recomputation without the timing row) are to be kept instead of the ADR's more conservative ones.
- **PENDING LEAD REVIEW:** m8 (whether the tests stand for the rehearsal's "analysis and report on synthetic records").

## Files kept (all under this folder)

- `scripts/b1_rung_rule_recompute.py`, `scripts/b1b_random_grid.py`, `scripts/b2_registered_driver_bypass.py`, `scripts/b3_prefreeze_paths.py`, `scripts/b4_mps_rss.py`
- `outputs/pytest_p10s2.txt`, `outputs/dry1.txt`, `outputs/b1_rung_rule_recompute.json`, `outputs/b1b_random_grid.json`, `outputs/b2_registered_driver_bypass.json`, `outputs/b3_prefreeze_paths.json`, `outputs/b4_mps_rss.json`
- Run directories: `dry1/` (4.7 MB), `b2tmp/`, `b3tmp/`, `b1tmp/`, `pytest-tmp/` (11 MB). None is over 100 MB, so none was deleted.

### Failed checker attempts (kept)

- `failed_attempts/01_b1_conflated_overhead.py` and its output: **my own error.** The first version's "ADR" variant changed three things at once: no per-process start-up, E-table at the slower layer, and timing in the recomputation. Its 1,074 mismatches mixed the three effects, mostly the start-up term, which the ADR does not define. It was replaced by the one-factor-at-a-time version above. It does not count as evidence of a rule error.
- `scripts/b3_prefreeze_paths.py` carries a guard that would stop the rehearsal check before any rehearsal-seed world was built, if the driver got past the layer argument. The guard was not reached, because the TypeError came first.
