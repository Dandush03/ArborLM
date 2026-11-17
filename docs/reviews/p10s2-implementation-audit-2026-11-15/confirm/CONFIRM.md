# P10-S2: narrow confirmation of the fixes to re-checks A, B and C (commit d57bf29)

**Claude (Opus 5.5) review. Astra review: NOT_PERFORMED. Not a human approval.** I wrote none of the audited code.

- Object: `d57bf29` on `claude/p10-s2` in the worktree `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a91c79a181109bb9c`, diffed against its parent `1939575`.
- Spec: ADR-0022 (with the last addendum, "rulings on the three re-checks", 2026-11-15) and `ADR-0022-addendum-combined-tasks.md`.
- Re-checks confirmed against: `docs/reviews/p10s2-implementation-audit-2026-11-15/recheck/{A,B,C}/`.
- Environment: macOS arm64; the worktree's `.venv/bin/python` (Python 3.12.14, torch 2.8.0, no numpy); uv 0.12.15; CPU only; `OMP_NUM_THREADS=1` for my scripts.
- Load: the machine was also running P10-S0's six workers (load average 7.9 to 8.9). pytest-xdist is not installed, so the suite ran in a single process.
- Constraints kept: no network, fetch, datagen, calibration, rehearsal or registered stage, and no real data or model. Nothing under `experiments/P10S0*` was touched.
- Repository state: the worktree was read-only to me. `git status` was clean after every step. The real study ledger `experiments/P10S2/ledger.jsonl` was unchanged (606 B, mtime 14:35) after every step.
- Location: every script and output named here is in this folder, `/private/tmp/claude-501/-Users-daniellaloush-dandush03-ArborLM--claude-worktrees-arborlm-consolidation-experiment-2b31c1/cfc0efd5-b7ca-4602-959a-07fe6b8d4e7d/scratchpad/s2confirm-report/`.

| # | Command (cwd = the worktree unless stated) | Output | Result |
|---|---|---|---|
| T | `UV_NO_SYNC=1 uv run --locked pytest tests/test_p10s2_*.py -q -p no:cacheprovider --basetemp <scratchpad>/s2confirm/bt -rfEs` (no `-n`: xdist absent) | `pytest_p10s2.out.txt` | **524 passed, 1 skipped, 0 failed** in 289.6 s. The skip is the opt-in end-to-end test (`P10S2_E2E=1`). The basetemp was deleted afterwards. |
| R | `PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 .venv/bin/python confirm_rules.py` | `confirm_rules.attempt1.out.txt`, `confirm_rules.attempt2.out.txt` | My own implementation of the composition rule, written from the addendum text, compared with `classes.comp_cell` and `composition_class`. **Attempt 1 (kept, my weak generator):** 30,000 arms, 0 disagreements, but 0 COMPOSES outcomes. **Attempt 2:** 30,000 arms with outcomes COMPOSES 9,735, INCONCLUSIVE 12,582, NOT_EVALUATED 7,678 and DOES NOT COMPOSE 5; **0 disagreements**. Boundaries, GEN, the m9 position, the fixed lines and the guards are covered below. |
| D | `... .venv/bin/python confirm_datagen.py <scratch>` | `confirm_datagen.out.txt` | Attempt machinery on fakes (see F2, F3, F4). |
| L | Shallow clone of `d57bf29` into the scratchpad. Cwd = clone: `PYTHONPATH=<clone>/src <worktree>/.venv/bin/python confirm_launcher.py <clone> <tmp>` with a **fake installer** | `confirm_launcher.out.txt` | The documented `datagen.sh` sequence cannot complete (F1). The clone was deleted afterwards. |

## Verdict

**READY AFTER F1, F2, F3.** All three are small changes. A short re-confirmation of those three is enough; a full re-check is not needed.

**Blocks the later freeze:**
- Nothing in the code as written lets a wrong freeze through: every hole I found fails closed.
- Before the freeze, the following still need a lead ruling or a fix: F5 and F9 (lead rulings), the N3 commit reading (gap 3), and F10. These are listed below.

## 1. Findings of re-checks A, B and C

| Finding | Status | Evidence |
|---|---|---|
| A R1 (groups of Q, D_cal and D_con; G1 across panels) | PASS | `data.py`: `blocked_groups` is removed from both `gold_pool` and `source_pool`. `gate_g1` compares stream groups with `all_panel_groups`. Test `test_r1_…` passes. |
| A R2 (hash-required install) | PASS in the module; **launcher broken (F1)** | `install_datagen.check_requirements`: hashes on every pin, option lines refused, the eight pins required. `uv pip install --require-hashes --target data/datagen-packages` (`uv pip install --help` lists both flags). The download-ledger row is written before the install and completed after it. The install is charged under the kind `install`. Installed versions are checked and torch/pyarrow shadowing is refused. `datagen.check_installed_pins` runs at the step start. `data/datagen-packages` is git-ignored (`.gitignore:10`). The current `requirements-datagen.txt` is still unhashed, so the install refuses, as it should. |
| A R3 (every exception leaves a record) | PASS | `run` catches `BaseException` after the start, writes `datagen_attempts/attempt-NNN.json` and `prefreeze_record.json`, and re-raises. Probe D and the test `test_r3_r16_…` confirm it. |
| A R4, R5, R9, R10, R11 | PASS | The offline variables are assigned, not set by default. A teacher folder must hold exactly the verified files. The whole-string check aligns from both ends. `split("\t", 2)` keeps a tab inside a sentence. `load_state_dict` refuses a key mismatch. |
| A R6 | **Gap (partial)**: only the host restriction is done | See gap 1. |
| A R7 | PASS | A Tatoeba manifest is refused once the record exists or the download ledger has a completed Tatoeba row. Both are true now. |
| A R8 | PASS (doc), with F8 | — |
| A R13 | PASS | `cells.teacher_matrix` uses the §4.3 item 2 definition on E_A, E_B, E_C, E_open, D_cal and D_con, inside the Stage 0 record. It is registered-stage only. In the rehearsal world only D_cal outputs exist under those names. |
| A R14 | PASS | `rehearsal.train_windows` cuts its windows from `world.wiki_train_ids` with `cut_windows`. The registered windows are replaced in `rehearsal_world`. |
| A R16 (re-run rule) | **PASS in principle; F2 and F1** | Stop kinds: `RegisteredTestStop` (equivalence, test (a), chrF, G9, `ScoreMismatch`), `WindowsInsufficient` and `PendingLeadReview` are classed `registered-test`; everything else, `KeyboardInterrupt` included, is classed `engineering`. A completed bundle is never re-run. |
| B N1 | PASS | `rehearsal_world` adds `E_open_A` and `E_open_B` stand-ins. `scale_factor` counts every registered panel. The stand-in bundle now has E_open items. |
| B N2 | PASS | The plan records `ledger: {lines, sha256}` after the raise entry. `verify_plan` → `verify_ledger_snapshot` refuses a ledger with a different prefix or a lower total. It runs in every registered stage (`stages.py:593`). |
| B N3 (a) and (b) | PASS for calibration, prefreeze-gates and rehearse; **F3 for the data record** | `_identity` records the manifest SHA-256, commit, configuration SHA-256, seed mode, update counts and device. Typed `--updates`, `--full-updates` and `--device` are refused outside pytest. `--device-reason` is removed. CPU needs `mps_attempt.ok == False` measured by the rehearsal itself. |
| B N3 (c) | PASS except the commit (gap 3) | `freeze.check_identities` checks the manifest (including against the data record), the configuration, the seed modes, the update counts, the device, `synthetic`/`dry`, and the data record's `seed_mode == "registered-data"` unless the configuration uses the test seed namespace. |
| B m1, m2, m3, m4, m5, m6, m7, m9, m10, m13 | PASS | See the diff. m4: `math.ceil(need)`. m7: P is read from `rehearsal.json`, and the freeze refuses if the ledger holds more than that P. m13: `gates_sha256` is checked in `require_order`. |
| B m8 | PASS for the pre-freeze and registered stages; **F4 for datagen and install** | — |
| B m11 | **Gap**: not done | See gap 2. |
| B m12 | PASS for failed stages; F10 | — |
| C N-M1 | PASS | `block(..., composition=True)`. `check_text` requires `COMBINED_LINE` for H lines and the Table 4 caption. Probe R: an all-NOT_EVALUATED block has both lines. |
| C N-M2 | PASS | For C2 adapter arms (L-seq, L-joint, L-sep), `H['A']` prints as "BY CONSTRUCTION (1.0)". A COMPOSES line says "rests on the French answer alone" (probe R prints both lines). |
| C m1, m2, m3, m4, m5, m6, m7, m8, m10 | PASS | The lead's sentence is the first item of "What S2 cannot establish". n items and items per answer are printed. A rejected M-ii gives a NOT_EVALUATED line and does not make the study INCOMPLETE. `valid_combined` is checked. The empty-assembled exemption is dropped. Verdicts are recomputed on `reported_study`. TEACHER-EQUIVALENT-TO-GOLD uses "either". `H_a` and `h_by_answer` are guarded (probe R refuses both). The pass rate and the contamination sentence are on every arm line. |
| C m9 | PASS for the position; **gap 4** | — |

**The four gaps, and whether each may stand.**

1. **R6, partial.** The final URL and Last-Modified are not recorded. **May stand, before the freeze too.** It is moot: the only Tatoeba session is complete and committed, and R7 now refuses any second one.
2. **m11.** No driver token is required for registered-run seeds. **May stand for data generation.** Before the freeze it is optional; re-check B marked it so and no ruling requires it. To close it: `seeded_generator(..., "registered-run")` refuses unless `P10S2_REGISTERED_RUN_ID` equals the run id of an open `registered` start marker in the study ledger.
3. **N3, commit only.** The freeze checks only that a commit is present. **May stand for data generation and calibration**, because each record stores its commit, so the check can be added later. **Before the freeze**, the ruling's "the freeze checks all of them" needs either:
   - the lead's reading, recorded, that presence is enough; or
   - this fix: each record's commit must be an ancestor of the freeze commit, and `git diff --quiet <commit> <freeze-commit> -- studies/p10s2 src/arborlm configs/p10s2_transfer.toml` must hold, or else the differing paths are listed in the plan. Which of the two applies is the lead's choice: **PENDING LEAD REVIEW**.
4. **C m9.** Test `test_m9_…` shows the decision lands on the colon. No test shows that a colon-keyed router then fails the 0.02 threshold. **May stand, before the freeze too.** The threshold and the measurement are unchanged; this only strengthens a demonstration. A nice-to-have: a version of re-check C's `check_gen.py` with a colon-feature router.

## 2. The path that matters next

**F1 (blocker for data generation; fails closed). `launch/datagen.sh` cannot complete, and cannot be re-run.**
- Cause:
  - `install_datagen.run` writes rows to the **tracked** `docs/reviews/p10-design-2026-11-15/DOWNLOAD_LEDGER.md`.
  - The next line of the script starts `datagen.main`, whose `freeze.check_code_commit` refuses a dirty tree.
  - Re-running `datagen.sh` after committing the ledger runs `install_datagen` again. It refuses because `data/datagen-packages` exists (exit 2), and `set -eu` stops the script before the datagen line.
- Consequence: R16's documented re-run path through the launcher is also dead.
- Demonstrated in a clone with a fake installer (`confirm_launcher.out.txt`):
  - `git status` after the install: `M docs/reviews/p10-design-2026-11-15/DOWNLOAD_LEDGER.md`;
  - clean-HEAD check: `REFUSED: the working tree is not clean`;
  - second install: `InstallRefused … exists`.
- **Fix I would accept:**
  - Make the install a separate, documented step: `uv run --locked python -m studies.p10s2.install_datagen --code-commit <HEAD>`, after which the operator commits `DOWNLOAD_LEDGER.md`.
  - `datagen.sh` no longer installs. Before `exec`, it runs a locked-environment check (for example `python -m studies.p10s2.install_datagen --verify`) that requires:
    - the directory exists;
    - `check_installed` passes;
    - the committed download ledger has a `completed` "data-generation packages" row whose revision equals `sha256(requirements)[:12]`.
  - Add a test that runs the whole sequence in a git clone (fake installer, commit, then datagen's start reaches `run`), and a test of a second `datagen.sh` after an engineering stop.

**F2 (major; before data generation). `lead_release.json` releases forever.**
- `datagen_rerun_gate` tests only that the file exists. It never reads its content (the test writes `"{}"`).
- After one release, a second registered-test stop is re-run without the lead.
- Probe D: after `ScoreMismatch`, then the release, then a `RegisteredTestStop`, the gate returns `None`.
- **Fix:** the release must be `{"releases_attempt": N, "cause": "...", "released_by": "..."}`. The gate must require `releases_attempt` equal to the last attempt's number, and preferably the file committed. Add a test with two registered-test stops.

**F3 (major; before data generation; the lead's N3 ruling). The data record has no code commit and no configuration hash.**
- `run()` never receives `--code-commit`, and the record holds neither the commit nor `config_sha256` (probe D: `code_commit` absent).
- This is the most important pre-freeze record, and it is written once.
- **Fix:** pass `code_commit` into `run`. Record it with the configuration SHA-256, the requirements SHA-256 and `transformers.__file__` in every attempt record and in the final `prefreeze_record.json`. `check_identities` should refuse a data record without them.

**F4 (minor; before data generation is advisable).**
- `charged_stage` opens `led.measure(stage, ...)` without `cap_seconds`, and `install` has no cap either. A killed datagen (OOM, or a kill while P10-S0 shares the machine) is therefore charged without bound, contrary to m8.
- `write_freeze` refuses permanently on any unfinished start marker, and no command resolves one.
- **Fix:** pass `cap_seconds=stage_cap_seconds` in `charged_stage`, and give the install a cap. How a killed process's marker is closed (a recorded end entry charged at min(elapsed, cap)) is an accounting rule: **PENDING LEAD REVIEW**.

**F5 (minor; PENDING LEAD REVIEW before the freeze). The CPU path through the freeze cannot be reached.**
- Calibration records `device` = the configured "mps".
- If the rehearsal fails over to CPU, `check_identities` refuses, because calibration's device differs from `rates.train_device`.
- This fails closed: the work returns to the lead.
- **Fix:** either state in the README that an MPS failure in the rehearsal returns to the lead, or exempt calibration's device from the equality when `mps_attempt.ok` is False.

**F6 (minor). Datagen checks versions, not provenance.**
- `datagen` started by hand with `uv run --with transformers==4.57.1 …` (unhashed) passes `check_installed_pins`.
- **Fix:** assert each of the eight modules' `__file__` is under `ROOT/data/datagen-packages` (the F1 verify step covers the ledger row).

**F7 (minor). Shadowing is checked for torch and pyarrow only.**
- Dependencies of the resolved set (filelock, typing-extensions, fsspec and others) would shadow the locked copies that torch imports.
- **Fix:** refuse any distribution in the target directory whose name is in `uv.lock` at a different version.

**F8 (minor, documentation).**
- The README says WikiText "has no flag", but `datagen.main` has `--wikitext-dir`. The ADR-0004 pins protect it.
- The `requirements-datagen.txt` header still says `uv run --with-requirements`.
- **Fix:** correct both lines while resolving the hashes.

**F9 (minor; before the freeze). Out of order is caught late.**
- `calibrate` does not require the data step's completed record for its `--data-dir`. A stand-in or wrong bundle is caught only at the freeze, after a write-once calibration has been spent.
- **Fix:** calibrate, prefreeze-gates and rehearse refuse unless `<run-dir>/data/prefreeze_record.json` has no `stopped` and its `bundle_manifest_sha256` equals `<data-dir>/manifest.json`.

**F10 (minor; before the freeze).**
- m12 handles a stage with status `failed` only.
- A failed second gates stage makes `train` refuse at start, so no stage record and no stop record exist. A room-check refusal does the same.
- Either way the analysis stage cannot write the §11 outcome (ENGINEERING-FAILURE / INCOMPLETE).
- **Fix:** on an in-sequence refusal after the freeze (a failed gate, or no room), write `stop_record.json` with the outcome, and let the analysis run.

**F11 (minor).** `_refuse_typed` is bypassed by setting `PYTEST_CURRENT_TEST` by hand. The freeze's identity check is the backstop (it checks update counts and devices). **Fix (optional):** also require `"pytest" in sys.modules`.

**Per stage, the questions asked:**

| Stage | Can it run out of order? | Can it see a registered seed before the freeze? | Can a typed flag change a registered number? | Does a failure leave a kept record and a charge? |
|---|---|---|---|---|
| `install_datagen` | Any time; harmless | No | No | Yes: the download row is completed `failed`, the ledger entry is `failed`, the directory is removed. F4 (no cap) |
| `datagen.sh` / `datagen` | F1 | No: mode `registered-data`, strict G9; registered-run seeds are refused | `--wikitext-dir` is pinned by hash; the cap is replaced at the freeze | Yes, for every exception (R3). A kill leaves an unbounded orphan (F4) |
| calibrate, prefreeze-gates, rehearse | F9 (caught at the freeze) | No | No (N3 b; F11) | Yes: `*_stopped.json` is written, and the stage is charged with its cap |
| freeze | Refuses out of order (provisional caps, missing records, identities, ledger beyond P, orphan markers) | Refuses if one was seen | No: everything comes from the records | Refusals are written to `experiments/P10S2/refusals/`, outside the frozen folder |
| registered stages | `require_order` | — | `--caps` has one choice | Yes (m12, with F10) |

## 3. Combined tasks C1/C2, COMPOSES, GEN

Result: **PASS**.

**The rule** (probe R; `classes.comp_cell` and `composition_class`):
- Definedness: the teacher gap must be ≥ 0.30 (`core.GAP_MIN` 0.3) and G_a^C ≥ 0.50 (`acq_gap_min`).
- H_a = (s_a(X,K) − max(s0_K, s0_single)) / (s_a(X,single) − s0_single).
- A cell passes at H_a ≥ 0.80 for both answers. Exactly 0.80 passes, exactly 0.50 is defined, and a gap of exactly 0.30 is defined.
- First match wins: NOT_EVALUATED, then COMPOSES (every cell), then DOES NOT COMPOSE (some order and answer with H < 0.50 in every replicate), then INCONCLUSIVE.
- My implementation disagrees with the code on 0 of 30,000 arms.

**What is printed:**
- BY CONSTRUCTION, for the ensemble and for the C2 German answer of the adapter arms.
- Both fixed lines, verbatim. `ORACLE_LINE` and `COMBINED_LINE` match the addendum §9 text.
- The contamination sentence, together with the exact-match pass rate.

**GEN:**
- `gen_gate(0.02, 0.02)` = True; `(0.02, 0.0200001)` = False; `(0.03, None)` = False; `(0.01, None)` = None.
- m9, checked with a toy tokenizer of one character per token:
  - with "German:", the decision is at the ':' (index 9);
  - without a colon, it is at the last letter (index 8);
  - with the colon just past the decision span, it stays at index 38, never beyond the span.

## 4. Oracle and teacher wording

Result: **PASS** (minor F12).
- Grep of `studies/p10s2/*.py` for autonom*, success and learned memory: the only output strings are the fixed line ("not autonomous learned memory"), `LEAD_RULE`, and the NOT_ESTABLISHED items "Autonomous learned memory: addresses and routes are supplied by rule." and "A success probability: …".
- The ensemble prints no composition word.
- Every guarded word, H line and composition key is refused without its line(s) (probe R).

**F12 (minor).** `check_text` is structural. A free-text line such as "autonomous learned-memory success on French", with no guarded word in it, is not refused (probe R), though no code path emits one. **Fix (optional):** refuse any line matching `/autonom/i` other than the three fixed strings.

## 5. Tests

- `tests/test_p10s2_*.py`: **524 passed, 1 skipped, 0 failed** (command T).
- `test_p8_sim.py::test_p7b_reproduction_gate`, not run by me: its `skipif` tests only `Path("experiments").is_dir()` (`tests/test_p8_sim.py:182-183`).
  - `experiments/P10S2/ledger.jsonl`, the real ledger from the first fetch, makes `experiments/` exist. The test therefore runs without the P5 checkpoints and fails.
  - **This is harmless.** It is an environment artifact of this worktree, not a P7-B or P8 regression, and P8 code is immutable.
  - Record it in the PR. To check P7-B, run the test from the main checkout, or here with `ARBORLM_EXPERIMENTS_ROOT=<main checkout>/experiments`; with `ARBORLM_EXPERIMENTS_ROOT=/nonexistent` it skips.

## 6. Failed or weak checker attempts (kept)

- `confirm_rules.attempt1.py` and `confirm_rules.attempt1.out.txt`: 0 disagreements, but my generator produced no COMPOSES outcome. It was superseded by attempt 2. This was my mistake, not a code defect.
- My first clone command named the branch `claude/p10s2` and failed ("Remote branch not found"). The branch is `claude/p10-s2`, and the clone was re-run with that name.
