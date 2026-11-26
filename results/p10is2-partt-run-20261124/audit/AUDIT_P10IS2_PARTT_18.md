# Audit 18 (delta): P10-I-S2 Part T, commit 1f776a74

VERDICT: READY FOR SECOND FREEZE AFTER A COMPLETE TARGETED REHEARSAL. No blocking defect; advisories A1–A4 below.

- Auditor: arbor-auditor, run as Claude Opus 5.5 (claude-opus-5-5). Date 2026-11-23.
- Strictly read-only. In worktree agent-acd0bce1f7811562f I ran only `git log`, `git show`, `git diff`, `sed` and
  `grep`. I ran no pytest, ruff or uv there, and read nothing under sealed/ or snapshots/.
- I did not re-run anything for this delta. The D1 finding rests on audit 17's simulation in my own clone.
- This is engineering evidence from a Claude review. It is not Astra review and not human approval.

## 1. D1 and D2
- D1 is fixed at partt_amendment/__init__.py:113: `all(own in c or c in amend["exempt_files"] for c in changed)`.
  This is the fix audit 17 proposed.
- The new test (tests/test_p10is2_partt_amendment_fixes.py:31-43) runs the real `planmod.import_walk` against the
  first freeze's plan. It asserts:
  - the added files are exactly the exempt and own files;
  - the import-walk part of the plan difference is empty;
  - one extra file, `engine_extra.py`, still refuses.
  This matches my audit-17 simulation.
- D2 is fixed at partt_stages.py:110: `--rehearsal-arms` now refuses in a registered launch, and the test covers it.

## 2. The calibration exemption in `chosen_calibration`
- **What is exempted.** partt_stages.py:359 compares the calibration record against
  `checked_files(frozen studies/p10is2 *.py, amend)`. That is every studies/p10is2 .py file except the six
  exempt_files named in AMENDMENT_RECORD.json:
  - common/runner.py
  - partt_tasks.py
  - partt_caps.py
  - partt_stages.py
  - partt_targeted.py
  - partt_amendment/__init__.py
- **Nothing else can be exempted.** `load` refuses any PROTECTED file and any file that is not a studies/p10is2 .py
  file (partt_amendment/__init__.py:49-52). The PROTECTED files are engine, partt_run, scoring, labels, annotations,
  partt_items, partt_real, calibration and quantities. Every other studies/p10is2 .py file (common/core, gates, plan,
  partt_plan, partt_rehearsal and the rest) is still compared.
- **A training or scoring file that differs is still refused.** Its hash differs, so repetition_used finds no
  matching repetition.
- **The selection is unchanged.** Exempting files only widens which repetitions match, and repetition_used picks the
  original (0) when it matches. The first freeze used calibration_0.json, and the new test asserts rep 0.
- **Backstop for edits inside an exempt file.** partt_stages.py is exempted as a whole file, and it holds
  calibration_from_record. Any change it made to U, rates, layer, items, seeds or registry keys would change the
  plan's `.calibration`, `.items`, `.seeds` or `.registry_keys`. None of those is on plan_diff_problems' allowed list,
  so the second freeze would refuse.
- **What I diffed.** `git diff --stat c25d4f0b 1f776a74 -- studies configs` lists only:
  - the config;
  - runner.py, partt_caps.py, partt_stages.py and partt_tasks.py;
  - the new partt_amendment/ and partt_targeted.py files;
  - the six other-study freeze records removed under ruling 50.
  I read all of these diffs; none touches a selection.

## 3. Checkpoint health check
- **Read-only.** `checkpoint_health` (partt_targeted.py:70-90) only reads, with `torch.load(map_location="cpu")`.
  It writes nothing and returns only `loadable`, `update` and `problem`, with no tensor or loss. The test checks the
  mtime and size of every file before and after.
- The preflight now requires every `*M-ii*.ckpt` in the registered checkpoints/ directory to be loadable
  (partt_targeted.py:48-51, 66).
- **A1 (advisory): there is no recovery path for a corrupt checkpoint.**
  - On resume, engine.train_cell (engine.py:323-328) loads with no validation and no fallback. A corrupt file makes
    the cell ERROR, then FAILED, then an item error, and the stage ends FAILED.
  - `retry` releases the cell for one resume, but the same file fails again.
  - No command moves a checkpoint aside to start the cell fresh. A fresh start would be the same computation from the
    same seeds and parent snapshot, but doing it needs a manual run-directory edit, and no ruling covers that.
  - Because the preflight requires loadable checkpoints, a corrupt one makes the targeted rehearsal INCOMPLETE, which
    blocks the second freeze. It is caught early, not silently.
  - The lead should decide beforehand: move the file to checkpoints/kept/ and start that cell fresh, recorded as a
    departure.
- **A2 (minor).** The docstring says `update` is checked "within the calibrated updates' reach"; the code only checks
  `update >= 0`.

## 4. Ruling 51 as committed (ADR-0025-addendum-part-t-rulings-16.md)
It states:
- the 205 h bound's authority, quoted verbatim, with the lead's reading flagged "for his review";
- the AMENDMENT_RECORD.json SHA-256 (10463ef9…), which matches `git show 1f776a74:… | shasum`;
- combined at about 3.7x;
- the departures from §7.1 rule 4, §10 items 3 and 5, and §9;
- the cap overrun;
- the mixed cell history, including that checkpoints were written under memory pressure;
- the machine state;
- the admission limit.

**A3 (advisory, disclosure gaps).** The ruling does not state:
- the corrupt-checkpoint risk and the missing fresh-start path (A1);
- the hashes of partt_amendment/__init__.py and partt_targeted.py, which hold the PROTECTED list and the checks.
  At 1f776a74 they are:
  - __init__.py: 48270810c177da696d7261a9e253402a0ebe2f1d21426950a18b4bc489919c8c
  - partt_targeted.py: 536c3b9b1f64923d891edc6c44e540b03a2bc3782b9b6c74470bb62fd44854e6
  Decision 2 should cite both.
- that the exemption works by whole file, not by change. Its backstop is the plan-difference check (§2).

## 5. Command order (from the code)
1. `git mv` freeze/partt_freeze_record.json into a subdirectory of freeze/, and commit.
   - Until then, candidate-plan --supersede (partt_stages.py:685), the rehearsal entry (partt_stages.py:89) and freeze
     (partt_stages.py:771) all refuse.
   - The subdirectory is outside both the frozen set and the L11 glob.
2. `candidate-plan --supersede`.
   - Pass `--run-dir` as the registered directory.
   - Add `cap_amendment_record` to the manifests.
   - Pass the charged ledgers of measuring 1–3, calibration and the first counting rehearsal. Do NOT pass the
     registered ledger, or its charge is counted twice.
3. Zero the stage caps: the eight stage keys and total_hours, but not calibration_hours.
   - `apply_caps_text` (partt_caps.py:148-161) refuses unless every key it writes is exactly `0.0`.
4. `caps-config --apply`. It writes train 125.8, combined 6.0 and total 204.02, and leaves the other stage caps as
   they were. My audit-17 check gave config_diff_problems = [] for exactly this state.
5. `candidate-plan --supersede` again, so the plan carries the written caps. `verify_plan` compares the config caps
   with the plan's.
6. Commit, and push if required. The freeze calls `require_log_pushed(head)`, which needs the calibration log commit
   in `@{u}`. That commit is already pushed.
7. Run the targeted rehearsal on a clean tree, with its run directory under the git-ignored experiments/.
8. Run the freeze, commit the new record (this is F2), and push.
9. Commit Decision 2 at a NEW path, e.g. `results/p10is2-partt-freeze-20261123/DECISION_2_PARTT.md`.
   - It must have a line that is exactly `DECISION: RUN` and contain the full 40-character F2 hash.
   - It must have no `DECISION: DO NOT RUN` line.
   - `require_decision_2` matches the glob `results/p10is2-partt-freeze-*/DECISION_2_PARTT.md` and reads the
     committed text at HEAD (plan.py:283-293).
   - Do not overwrite the 20261122 file.
10. Run the read-only preflight: check_preconditions, load_registered_plan, verify_plan, require_decision_2 and
    require_ignored_run_dir.
11. Launch: `sh studies/p10is2/launch/partt_registered.sh train /Users/daniellaloush/dandush03/ArborLM/experiments/P10IS2-T-registered-20261121 <full F2>`.

**Failure points in this sequence:**
- Steps 3–5 in the wrong order: caps-config refuses if the caps are not zeroed, and verify_plan refuses if the plan
  predates the caps.
- Any commit to a frozen path after F2: PAUSED — IDENTITY at the launch.
- A merge of main: L11.
- An unloadable checkpoint: A1.

**A4.** Nothing in the sequence writes to the registered run directory before the launch. The preflight only reads.

Astra review: NOT_PERFORMED
