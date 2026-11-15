# P9-I (ADR-0017 Part I) — audit of the post-freeze gate-harness fix (commit `0e0fbfb`)

- **Auditor:** Claude Opus 5.5 (`claude-opus-5-5`). I wrote `AUDIT.md` and `RECHECK.md` in this folder (verdict READY TO FREEZE), so part of this audit is about my own miss. I did not write the fix (implementer: Sonnet 5.5) or the diagnosis (the lead).
- **Date:** 2026-11-14/15 (UTC). **Worktree:** `.claude/worktrees/arborlm-consolidation-experiment-2b31c1`, branch `claude/adr-0017-design`, HEAD `0e0fbfb`. Diff reviewed: `git diff dd8b205 0e0fbfb` (and `5c2d07f..0e0fbfb`).
- **Status:** independent engineering and mathematical evidence. It is not Astra validation, not human approval, and not a decision on a second attempt. **Astra review: NOT_PERFORMED.**
- **Environment:** Apple M5 Max, macOS 27.2.1 (Darwin 27.2.0 arm64), Python 3.12.14, torch 2.8.0 on CPU in float32, `uv run --locked`, `PYTHONPATH=.` from the worktree root. `$E` = `/Users/daniellaloush/dandush03/ArborLM/experiments`, `$S` = this session's scratchpad.

## What I ran

| # | Command (from the worktree root) | Output (`outputs/`) | Result |
|---|---|---|---|
| 1 | `PYTHONPATH=. uv run --locked python …/g1_diagnosis.py $E` | `g1_diagnosis.txt` | diagnosis reproduced on rehearsal draws 0 and 2 |
| 2 | `git diff --stat dd8b205 0e0fbfb -- studies/p9i/{model,core,classes,train,evaluate,report}.py studies/p9/ configs src pyproject.toml uv.lock` | `g2_unchanged_files_diffstat.txt` | empty |
| 3 | `… a4_arm_forward.py $E`, `… a5_classes_enumeration.py`, `… a3_rehearsal_replay.py $E/P9IH-… $E $S/g2_a3_replay N-n4096-b101-o301-s1801 BB-n4096-b101-o301-s1802 A4E-n16384-b101-o301-s1801` (my unchanged pre-freeze scripts, at HEAD) | `g2_a4_…`, `g2_a5_…`, `g2_a3_…_at_0e0fbfb.txt` | each byte-identical to its `r3_…_at_dd8b205.txt` |
| 4 | `… g3_analyze_report.py $S/g3_run2 results/p9i-run-attempt1-2026-11-14/gates.json` | `g3_analyze_report.txt` | 9 of 10 scenarios pass; S9 crashes the analyze worker (X1) |
| 5 | `… g3b_nonfinite.py $S/g3b_run1 results/p9i-run-attempt1-2026-11-14/gates.json` | `g3b_nonfinite.txt` | X1 isolated; X2 found |
| 6 | `… g3c_handoff.py $S/g3c_run1` | `g3c_handoff.txt` | 0 failed checks |
| 7 | `sh …/g3d_gates_rehearsal_at_dd8b205.sh <worktree> $E $S/g3d2` | `g3d_gates_rehearsal_at_dd8b205.txt` | at `dd8b205` the gates stage cannot run on rehearsal seeds |
| 8 | `uv run --locked pytest -p no:cacheprovider -x -q` (twice; then a third time) | `g4_pytest_run{1,2,3}.txt` | see §4 |
| 9 | `uv run --locked pytest -p no:cacheprovider -q tests/test_p9_pool.py` ×5, during pytest run 2 | `g4_pool_stress_under_load.txt` | 5 × 36 passed |
| 10 | `uv run --locked ruff check .` | — | All checks passed |

Not run: no registered stage, no registered-seed generation, no read of registered-seed data beyond the committed attempt-1 records (`results/p9i-run-attempt1-2026-11-14/`). The only training was (a) the three 64-update rehearsal-draw-2 replays in row 3 (tensor comparison only) and (b) row 6: two cells for 8,192 updates on the **synthetic** backbone with **test** seeds (`p9i-test-0`) in calibration mode. I read no loss or accuracy from either. Every pool stage I ran used a private ledger under `$S`; the project ledger `$E/P9I-ledger.json` still has 6 entries (checked before and after). No existing file edited, nothing committed.

**Failed checker attempt (my mistake, kept):** `outputs/g3_analyze_report_attempt1_FAILED_auditor_bug.txt`. `arborlm.io.write_json` does not create parent directories, and my record builder assumed it did. I added a `mkdir` wrapper (marked in the script) and re-ran it into a fresh directory. The implementer's code was not involved.

**Discrepancy in my own pre-freeze audit:** `AUDIT.md` says "Gradient reach: every trainable tensor of every arm receives a non-zero finite gradient". My `a4` checked only 10 arms. It left out R1 and R2, and it used random tokens. For R1 and R2 I relied on the exact re-scoring of the calibration snapshots (`a2`, 28 of 28 counts) and on `a7`'s restoration. That supports the lead's statement that R2's forward was matched, but my sentence claimed more than `a4` showed.

## 1. The lead's diagnosis — CONFIRMED (mechanism) and completed

I reproduced it on rehearsal draws 0 and 2 with the verified B101 backbone, my own loss (256-way cross-entropy at the 8 answer sites) and my own identifier-to-table hit count (`g1_diagnosis.txt`):

| Draw | First 8 Panel A rows: fact ids | ids < 2,048 | R2 table hits | R2 reach (`values`, `wo`, `gate`) |
|---|---|---|---|---|
| 0 | 4,000 … 28,845 | 0 of 64 | 0 of 64 | False, False, False |
| 2 | 2,224 … 32,349 | 0 of 64 | 0 of 64 | False, False, False |

The implementer's `train.gradient_reach` gives the same booleans. All 11 other arms reach every parameter on the same rows, which matches attempt 1's `gates.json` (only R2 failed, with 3 trainable tensors).

**Why the failure was almost certain at real size.** Panel A rows are octets of one cluster: the median spread of fact ids within a row is 14. So the 2,048 facts of the 4,096-slot cell fill exactly 256 of the 4,352 rows (5.88%). The chance that the first 8 rows hold none of them is about 0.94^8 ≈ 0.61. On both rehearsal draws the first such row is row 15. In the attempt-1 DRY profile (512 trained facts, 128 per cell, 25%), the first 8 rows held 24 of 64 covered facts, so the DRY gates passed.

**What I add to the diagnosis:**

- **Nothing about the model was learnt.** R2 at init with an empty read gets no gradient by construction: the lookup table gives −1, so no slot is selected. The fact ids of 2,482–29,279 that the lead quotes were read from registered data; I cannot check that range without regenerating registered data, which I did not do. The mechanism and the 0-of-64 count are reproduced on two rehearsal draws.
- **The cause was structural, not only "DRY sizes".** At `dd8b205` the gates stage could not run on rehearsal seeds. The restoration jobs were built with `mode=CALIBRATION if args.mode != REGISTERED else REGISTERED`, and `check_seed_set("calibration", "rehearsal-2")` refuses that combination (`g3d…txt`: gates INCOMPLETE, `ValueError: mode 'calibration' cannot use the 'rehearsal-2' seed set`, no `gates.json`). The calibration draw could not be used either, because §I.6 trains only R1 and R2 there. So the registered run was the gates stage's first execution at real size. The fix's `mode=args.mode` removes this. The lead's draw-2 gates run (`$E/P9IG-rehearsal-gates-draw2-20261115T003153Z`: G1, G2 and G4 pass, 12/12 arms reached, restoration bit-identical with 55 and 67 tensors) is the first real-size gates execution.
- **The other gates were sound in attempt 1.** The N-vs-R0a identity, the initial identities and G2 do not depend on which facts the cell covers. Restoration trains on the cell's own stream, which holds only covered facts. I recomputed G2's intervals with my own exact binomial code (log-space pmf, tail 0.001/8/2): [36, 96] for 2,048 facts, [198, 318] for 8,192 and [905, 1147] for 32,768, equal to the implementer's and to the record. All 8 recorded counts (70, 259, 1077, 60, 62, 256, 1005, 66) lie inside (`g3_analyze_report.txt`).

## 2. The fix — correct and minimal; registered computation unchanged

- **Scope.** `git diff dd8b205 0e0fbfb` touches `studies/p9i/stages.py` (+49/−5), adds `tests/test_p9i_gates_harness.py` (new, 130 lines) and adds `results/p9i-run-attempt1-2026-11-14/ruff.toml`. `model.py`, `core.py`, `classes.py`, `train.py`, `evaluate.py`, `report.py`, everything under `studies/p9/` (incl. `data.py`), `configs/`, `src/`, `pyproject.toml` and `uv.lock` are unchanged (`g2_unchanged_files_diffstat.txt` is empty).
- **Re-run at HEAD.** Forward equality of 10 arms against my reference (`a4`), 20,000 class tables (`a5`), and bit-identical 64-update replays of N, BB and A4E on rehearsal draw 2 (`a3`): all three outputs are byte-identical to the `dd8b205` outputs.
- **`gate_contexts` / `assert_covered`.** These choose rows of `evaluate.stream_for(study, 2048, "panel_a")` whose 8 facts all lie below 2,048. By `restrict_stream`, the restricted stream holds rows that are entirely below F or entirely unseen, and every covered fact appears once (G1 "coverage"/"layout"; 256 such rows on both draws). So 8 rows always exist. On draws 0 and 2 the chosen ids are 273–1,775 and 371–1,167, the table maps all 64 identifiers to their own fact's slot, and all 12 arms reach every trainable tensor with no stray gradient. A `HarnessError` is raised outside the defect list, so it fails the gates task and writes no `gates.json`, and `require_gates_passed` then refuses training. It can never be recorded as a G4 defect. The gates now feed the N-vs-R0a identity and the initial identities with covered rows instead of rows 0–7. Both are valid inputs for an equality check.
- **`args.mode` in the restoration jobs.** Registered: `REGISTERED` → `REGISTERED`, identical. DRY (`cmd_dry` forces calibration): `CALIBRATION` → `CALIBRATION`, identical. Rehearsal: `CALIBRATION` (which crashed) → `REHEARSAL`, newly runnable, and rehearsal mode writes only whitelisted records.
- **`DRY_SIZES`** (512 → 2,048 trained) is read only when `args.dry`. `main` refuses `--dry` with `--mode registered`, and `seeds_for` refuses synthetic or DRY with registered seeds. Registered data sizes are `DataSizes()` defaults, unchanged. Note: the new DRY proportion alone would **not** have caught this defect on test seed 0, because the old harness still reaches R2 there (8 of 64 covered in rows 0–7). The regression is caught by the new tests: the reordered-rows test and the real-proportion test.
- **Code identity.** `source_sha256` at HEAD is `43a611c48b33…5bc5d6` (equal to the lead's P9IG manifest). `spec 2798a8db…`, `config 7cc20791…` and `frozen_source 8b5a03a0…` are unchanged since the freeze.

## 3. Why my pre-freeze audit missed it, and what else exercised only at DRY size

**Why.** I read `work_gates` and checked its parts separately: gradient reach on random tokens for 10 arms, restoration for 10 arms, the N/R0a identity. I never ran the gates stage on real-proportion data, and I did not notice that it could not be run on rehearsal seeds. A gate harness chooses its own inputs, and that choice was the one thing I did not test at real size.

**The analyze and report stages at real size (57 cells, synthetic records, invented accuracies; `g3_analyze_report.txt`).** I used the real registry, real facts per size (2,048 / 8,192 / 32,768), U = 8,192 from the committed calibration record (sha256 `087bf0b5…`), and the implementer's own `work analyze` and `work report` entry points (rehearsal mode). S10 also went through the pool commands with a private ledger. Expected outcomes were written by hand from §I.8:

| Scenario | Outcome (step) | Status / interpretable | Checks |
|---|---|---|---|
| S1 BB works everywhere | BB (1) | COMPLETE / True | BB INTERFACE_WORKS ×3, BEATS DENSE, LM PRESERVED, 57 cell rows, 14 class rows |
| S2 only W7 (+E7) works | W7 (3) | COMPLETE / True | E7/W7 ADDS NOTHING, encoder + W7 + system scope lines |
| S3 nothing works | NO_INTERFACE_SELECTED (4) | COMPLETE / True | all FAILS |
| S4 R1 = 0.40 at 65,536 | INCONCLUSIVE (0), `{65536: NOT_EVALUATED}` | COMPLETE / True | every arm NOT_EVALUATED at 65,536 |
| S5 one cell missing | NOT_INTERPRETED (INCOMPLETE) | INCOMPLETE / False | 56 read, missing label listed, no classes |
| S6 BB's B102 replicate fails, A4 works | A4 (2) | COMPLETE / True | BB 16,384 INTERMEDIATE |
| S7 BB-0 above chance at 65,536, LM rise 0.08 | NO_INTERFACE_SELECTED (4) | COMPLETE / True | MODEL_STORES_FACTS, NOT COMPARED, LM DEGRADED |
| S8 G2 failed + one LEAKAGE | NOT_INTERPRETED | COMPLETE / False | both reasons, banner printed |
| S9 a zero accuracy in a ratio denominator | **analyze crashes** | — | X1 |
| S10 pool path, S1 inputs | BB (1) | manifests COMPLETE | `failed_tasks` empty |

**X1 (MAJOR, present at `dd8b205`, not introduced by the fix, missed by my pre-freeze audit).** `classes.ratio` returns `+inf` by design when a dense comparison's dense accuracy is 0 or a backbone contrast's state-arm accuracy is 0. `work_analyze` writes the analysis with `arborlm.io.write_json`, which uses `allow_nan=False`, so it raises `ValueError: Out of range float values are not JSON compliant: inf`. `g3b_nonfinite.txt` shows each trigger alone:

- S9a: D7 = 0 at 65,536 while W7 is PARTIAL there.
- S9b: W7 = 0 at 16,384 while E7 is positive.
- S9c: zeros that no ratio reads do not crash.
- S12: through the pool, the analyze stage ends INCOMPLETE with no `analysis.json`, and then the report stage fails too.

It needs an exact 0 of 2,048–32,768 on some seed and panel. Ties count as wrong, so a collapsed arm with tied alphabet logits scores exactly 0. That is unlikely but not excluded. If it happens, the single registered run loses its automatic analysis and report, and §15.5 forbids re-running a stage with changed settings. Engineering fix (it changes no rule or number): serialise non-finite floats in `analysis.json` as strings (`"+inf"`, `"-inf"`, `"nan"`), for example a `_jsonable` mapping applied to `result` before `write_json`. Add a test for S9a and S9b. The report reads only labels from these blocks, so it is unaffected.

**X2 (minor).** If a BB eval record's `language_modelling.relative_rise` is `None` (`evaluate._finite` maps a non-finite rise to `None`), `work_analyze` raises a `TypeError` at `float(None)` (S11). The eval record's own `degraded` flag is `True` for an infinite rise but `False` for NaN. How a non-finite rise should be labelled is a scientific reading: **PENDING LEAD REVIEW**. The minimal engineering fix is not to crash, and to record the reading.

**Train → evaluate hand-off at registered sizes (`g3c_handoff.txt`, 0 failed checks).** This cannot be done on rehearsal draw 2 with the real backbone: rehearsal mode writes no `train.json`, so `evaluate_cell(require_train_record=True)` is unreachable, and the calibration draw may train only R1 and R2. I therefore ran the implementer's `generate → gates → train → evaluate` commands through the pool in calibration mode, with the synthetic backbone, test seeds and real sizes. I used two registered labels, `N-n4096-b101-o301-s1801` and `BB-n4096-b101-o301-s1801`, and U = 8,192 from the committed calibration.

- **Gates** pass at real proportion.
- **`calibration_binding.json`** = {`087bf0b5…`, 8192, {}}, and `updates.json` = 8192.
- **Snapshots:** each cell has exactly `snapshots/u0008192/model.pt`. `train.json` has `facts` 2,048, `matched_updates` = `run_updates` = 8,192, `snapshot_sha256` = {"8192": sha256 of that file}, carries the binding, and lists 2,048 unique facts.
- **Eval records** are at `cells/<label>/eval/u0008192/eval.json`, with update 8,192, 2,048 facts per panel, interval [36, 96], 2,048 unseen controls, the binding, and an LM block for BB only.
- **Refusals:** a calibration file with one extra byte is REFUSED (exit 2). A tampered `data_manifest.json` stream hash makes every evaluate task fail, with no eval written.
- **Charged (private ledger):** train 76.5 s, evaluate 2.3 s.

**Still unexercised at real size before the run:**

1. Interface arms trained for 8,192 updates on the real backbone. The rehearsal ran only 64 updates; the calibration ran 8,192 only for R1 and R2. From the rehearsal records, Σ(s/update × 8,192) = 8,338 s, the LPT makespan on 6 workers is 1,407 s, and the worst list-scheduling bound is 1,390 + 404 = 1,794 s. All are below the 3,600 s train cap.
2. Registered evaluate with all 2,048 next-byte rows; the rehearsal used 256. The rehearsal's 57 evaluations sum to 353 s, makespan about 59 s, cap 900 s.
3. Registered-only branches have unit tests (my `r1`) but no real-size execution: `require_gates_passed` on a real passing record, `verified_data(require_manifest=True)` in train and evaluate, workers deriving U with no `--updates` (my g3c passed `--updates 8192` because calibration mode forwards it), and `check_binding` in registered mode. `check_preconditions` has run only for the attempt-1 gates stage.
4. Analyze and report on real records (synthetic only, above).
5. The fixed gates on registered data. By rule this happens only in attempt 2.

## 4. Test suite

- **Run 1** (`g4_pytest_run1.txt`; 00:32:41–00:41:27 UTC, with my other checks running concurrently): **1737 passed, 4 skipped, 3 warnings in 523.18 s**, exit 0.
- **Run 2** (`g4_pytest_run2.txt`; 00:42:24–00:51:05 UTC, with g3d and the pool stress loop running concurrently): **1737 passed, 4 skipped, 3 warnings in 520.69 s**, exit 0.
- **Run 3** (`g4_pytest_run3.txt`; 00:51:16–00:59:56 UTC, machine otherwise idle): **1737 passed, 4 skipped, 3 warnings in 517.90 s**, exit 0.
- **Load stress:** 5 runs of `tests/test_p9_pool.py`, the timing-sensitive pool tests (sleeps of 0.4–2.5 s, `wall_seconds < 2.0`, overlap == limit), during run 2: 36 passed each time.

**No failure in 3 full runs.** I cannot identify the implementer's single truncated failure. 1,737 = 1,731 at `dd8b205` + the 6 new tests. The most likely class is the pre-existing P9 pool tests, which assert on wall-clock behaviour of subprocesses (`tests/test_p9_pool.py`: `wall_seconds < 2.0`, concurrency overlap with 0.4 s sleeps, an aggregate-RSS kill race with a 2.5 s sleep); they could fail on a loaded machine, but they did not fail here. **Bearing on the run:** none of these tests runs in the registered stages. The pool's real behaviour is recorded in each stage manifest, and a registered stage needs a clean tree, not a passing test run. A recurrence should be captured with full output (`-x -q -rf`) and identified before the freeze record cites a test count, so that the record states a reproducible count (1,737 passed, 4 skipped here).

## 5. Governance — a second attempt with the same seeds and data

**What has been observed on registered seeds** (from the committed records and the run directory listing; I opened no file in `$E/P9IP-…/g4_restore`):

- G1's generator checks.
- G2's no-memory counts on both parents. All are at chance and contain no trained arm.
- Init-time booleans: the N-vs-R0a identity, the BB initial identities and the gradient reach of 12 untrained arms.
- The lead's diagnostic, which regenerated registered data in memory and printed the fact ids of Panel A rows 0–7 (64 ids) and R2's reach booleans.
- **Not listed in the attempt-1 README:** the G4 restoration check trained N and BB at 4,096 (seed 1801, B101) for 32 updates on registered data. Its `train.json` and `updates.jsonl` (per-update losses) are in `$E/P9IP-…/g4_restore/{N,BB}/restore_check/{straight,first,resumed}/`. This is by design of the frozen gate, which runs in registered mode, and those 32 updates are the opening of two registered cells' training. I did not read them.

**None of this is a measurement of a trained arm's accuracy, and none bears on a class or the selection.** Attempt 1 stopped for a reason fixed by the data layout and the harness, not by any arm's performance. So repeating with the same seeds is not optional stopping. Changing the seeds would itself depart from the registration. **Reuse the same registered seeds and data:** in my judgement, nothing observed compromises a second attempt. The decision is the human lead's: §15.6 excludes "a re-run".

**Use a new run directory and regenerate. Do not copy.** The old directory cannot be reused: `gates/manifest.json` exists and a stage is never overwritten, and `work_analyze` counts every `*/manifest.json`, so the failed gates task would make the run INCOMPLETE. Regenerating (`generate --mode registered --i-understand-freeze-time`, about 12 s) is deterministic, because `studies/p9/data.py` and the seeds are unchanged. But the **file** hash of the new `data_manifest.json` will **not** be `8d73e555…`: the manifest embeds `identity` (`source_sha256` was `7573da72…` and is now `43a611c4…`; `spec_sha256` will change with the new freeze edit). The identity to compare is the **`sha256s` block** (14 hashes: facts, lane_d, pool, templates and 10 streams), which must equal the block in `results/p9i-run-attempt1-2026-11-14/data_manifest.json`. This is the comparison `verified_data` makes. `g1.json` has no identity block, so it should be byte-identical: sha256 `ab324b8546a377ac…ce0445143`.

**The new freeze record must contain:**

1. The new freeze commit and the code commit. The diff from `dd8b205` is limited to `studies/p9i/stages.py` (gate inputs, `HarnessError`, restoration mode, DRY sizes), the new `tests/test_p9i_gates_harness.py` (and the X1/X2 fix if made), with the new `source_sha256`. State that model, core, data, classes, train, evaluate, report and the config are unchanged, and cite this audit. The new test file must be in the freeze commit: `check_preconditions` compares every `tests/test_p9i_*` with it. This review folder must be committed first so the tree is clean.
2. The attempt-1 account: run directory `P9IP-20261114T235955649302Z-…` kept and never reused; stopped at gates; cause as above; charged 5.6 s for the gates stage.
3. The full list of what was observed on registered seeds, as above, including the 32-update restoration training and the lead's diagnostic. State that the restoration logs stay unread until the run ends.
4. The human lead's recorded decision authorizing attempt 2 under the changed code. The lead's §15.6 delegation does not cover it.
5. Data: same registered seeds (182001+), a new run directory, generation at freeze time. The expected `sha256s` block equals attempt 1's, and the expected `g1.json` sha256 is `ab324b85…`. State explicitly that the manifest file hash differs from `8d73e555…` because of the embedded code identity.
6. The expected G2 counts: identical to attempt 1 (A: 70, 259, 1077, 60; B: 62, 256, 1005, 66; and the B102 counts in `controls.no_memory_replicate`). The `g4_restore` `model.pt` hashes are expected to equal attempt 1's, because the inputs are unchanged. Snapshot files are byte-identical across processes and code versions: the a3 replays at HEAD reproduce the rehearsal's `model.pt` sha256, `5780d024…` for N and `75ac0640…` for BB. Whether a difference stops the run is **PENDING LEAD REVIEW**; I only report that the computation is deterministic.
7. Calibration binding unchanged: `087bf0b5…`, U = 8,192, no failed size.
8. The exact command line and cap per stage, including the new generate. Ledger: 965.1 s charged now (829.3 calibration + 101.0 rehearsal + 11.3 + 5.6 attempt 1 + 11.7 + 6.1 for the lead's draw-2 gates rehearsal, which was charged to the project ledger), leaving 13,434.9 s against 5,700 s of run caps plus generate.
9. How X1 (and X2) were resolved: fixed with tests, or accepted by the lead as a recorded residual risk with the procedure "if analyze fails, the auditor's recomputation from the raw records is the analysis of record".

## Verdict

**Two items remain before re-freezing.**

- **X1** (MAJOR, low likelihood, high consequence): serialise non-finite ratios in `analysis.json` (strings for ±inf and NaN), with tests for a zero dense accuracy and a zero state-arm accuracy. The lead may instead accept X1 as a recorded residual risk.
- **X2** (minor): do not crash on a `None` relative rise; the label it gets is **PENDING LEAD REVIEW**.

Once they are dealt with, the code is **READY TO RE-FREEZE**, with the freeze record items 1–9 above.

The gate fix itself is **correct and minimal**. The lead's diagnosis is **confirmed** and completed with the structural cause. The registered train, evaluate, analyze and report computations are unchanged from `dd8b205`.

Astra review: NOT_PERFORMED. This audit is not human approval and not a decision on a second attempt.
