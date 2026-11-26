# P10-I-S1: audit of the evaluate-cap extension (commit 2506c99) and of the analysis loader defect

Auditor: arbor-auditor subagent, model Opus 5.5 (`claude-opus-5-5`), 2026-11-21. Independent engineering audit. **Not Astra validation and not human approval.** `Astra review: NOT_PERFORMED`.

## What I read and ran

- **Commit 2506c99** in the implementer worktree, read only: the addendum, `APPROVAL.md`, `apply_extension.py`, `verify_resume_identity.py`, and the new test's text.
- **The frozen code at 46bf55a**, from my existing read-only archive (`experiments/_scratch/p10is1_recompute_20261121/frozen/`): `core.Ledger`, `stages.stage_cap_seconds`, `stages.cmd_registered`, `stages.build_registry`, `report.py`, `rehearsal.py` and `rehearsal_real.py`.
- **The registered run directory: one listing only.** `baselines/` holds `manifest.json` alone. I read no evaluate output, no ladder decision, no outcome value and no sealed file, and I started no stage.
- **One read-only call**, with `PYTHONPATH=<archive>:<archive>/src`, the venv Python and `-B`, under `timeout 120`: `core.read_record(<counting rehearsal>/baselines/manifest.json, "baseline")` raises `ValueError: expected a 'baseline' record, got 'stage_manifest'`.
- **No new scratch directory** was created, and no tests were run, because of the memory limit.

## Q1: the extension mechanism. Verdict: READY AFTER THE REQUIRED CHANGES BELOW

### Is a negative ledger entry honest?

**It is an honest carrier only with disclosure where readers look; without it, it misstates one figure.**

The ledger is defined as "charged wall time of the study" (`core.Ledger`). After the two entries, three figures change meaning:
- `charged("evaluate")` no longer equals evaluate's charged wall time: it is one hour low.
- A stage that never ran, `evaluate-cap-extension-offset`, shows +1 h.
- The total stays exactly true.

The entries are labelled, carry the approval's hash, and keep a pre-image, so they are a transparent adjusting entry, not a hidden one. But any later per-stage sum of the ledger is wrong unless the reader knows about them.

### Does every later reader still give true figures?

| Reader | Effect |
|---|---|
| `stage_cap_seconds` | spent on key `evaluate` = evaluate + baselines − 3,600, so the effective cap on the key is 2.0 h, as approved. True for its purpose |
| `Ledger.remaining` / `require_room` (the total cap of 52 h) | unchanged; the total is still the true total |
| `Ledger.charge` (`max(0, seconds)`) | clamps only new charges. It reads the existing entries and appends, so the negative entry survives every later charge. `apply_extension` writes directly and is not clamped. Nothing validates the sign. **Not defeated** |
| `read_ledger_seconds` (projection's H_c) | sums with the sign; the total is unchanged |
| stage manifests (`charged_seconds`) | true, positive per invocation. Unaffected |
| `report.py` | prints only the **plan's** caps ("Caps (the plan's figures…)"). **It will show evaluate 1.0 h** while up to 2.0 h is spent. It prints no charged hours, so it understates nothing, but the cap it prints is not the effective cap. **This is not disclosed in the report**, which is frozen |
| analysis; my `recompute.py` | read no ledger. Unaffected |
| any later accounting that sums the ledger by stage (OUTCOME, scorecard, a future projection) | **understates evaluate by 1 h and shows a phantom stage** unless told |

### Applied twice, or with another amount?

**No.**
- It refuses if the offset stage exists or the pre-image file exists.
- The amount is fixed at 1.0 h by the machine-read line and the code.
- The default is a dry run.

**Gap:** it does not check that no S1 stage is running. `Ledger.charge` is read-modify-write, so a stage charging during `--apply` can silently drop the two entries, or the extension can drop that charge (R2).

### Is `verify_resume_identity.py` faithful?

**Yes.** It calls the same functions in the same order as `cmd_registered` lines 537–542: `configure_worker`, `check_preconditions`, `load_registered_plan`, `verify_plan` with the freeze commit, `require_decision_2`, `require_ignored_run_dir`.

It differs only in this:
- it reports every check instead of stopping at the first refusal;
- it does not reach `ledger_of`'s `require_ignored_path` on the ledger, or `require_room`.

Both are minor. The commit touches nothing under the frozen roots, so identity holds.

### Is there a cleaner route that keeps identity?

**No materially cleaner one.**
- The cap arithmetic reads a frozen cap (plan and config) minus the ledger's spent time on the key. Without a code or plan change, only "spent" can move, so any identity-preserving route is a ledger entry.
- Putting the credit on `baselines` instead only moves the distortion.
- The alternative is an amending freeze with new caps: a new plan, a new freeze record, a counting rehearsal of the new plan file (the freeze's rehearsal gate requires it) and a new Decision 2. That is far heavier, for a one-hour resource change.

**The ledger route is acceptable with R1–R4.**

### Required changes

- **R1. Memory before resuming.**
  - The stall was the 18-GiB aggregate memory guard. About 14.5 GiB is available now.
  - The runner adds a worker only when available memory is at least 18 GiB, and it **charges wall time while it waits**. Resumed as is, evaluate would spend the new hour waiting and be PAUSED again on its cap.
  - **Resume only when `vm_stat`** (free + inactive + purgeable + speculative pages) **shows at least 18 GiB plus a margin** (about 20 GiB), with heavy co-tenants stopped.
- **R2. No stage alive during `--apply`.** `apply_extension.py` must refuse while any `studies.p10is1` process is alive, using the same pattern as the study-process check. The lead must apply it with S1 stopped.
- **R3. Disclosure where readers will see it.** Add to the addendum, and to the OUTCOME or acceptance record when it is written:
  - "the ledger's `evaluate` sum is 3,600 s below evaluate's charged wall time; the true per-stage charge is the sum of the stage manifests' `charged_seconds` (or the ledger sum excluding the two extension entries); the effective evaluate-and-baselines cap is 2.0 h; the report prints the frozen 1.0 h".
  - The report itself cannot carry this, because it is frozen.
- **R4. Correct the addendum's §3** to say plainly that after the extension the ledger no longer gives per-stage charged time for `evaluate`, and which figures remain true (R3).

### Advisory

- **A1.** `APPROVAL.md` quotes the answer "as relayed; the implementer did not hear it". Under the standing delegation for P10 hour-cap extensions this suffices. If the human lead confirms in writing, add his line.
- **A2.** The ledger rewrite is not atomic. The pre-image file covers a failed write.

## Q2: the analysis defect

### Does the registered path really crash? **Yes.**

- `stages.build_registry` (frozen, lines 366–369) globs `run_dir/baselines/*.json` and calls `core.read_record(p, "baseline")` on each.
- `execute_stage` writes the baselines **stage manifest** to `run_dir/baselines/manifest.json` (kind `stage_manifest`), whether the stage ends PAUSED or COMPLETE.
- `read_record` raises **`ValueError`** ("expected a 'baseline' record, got 'stage_manifest'"). I confirmed this read-only on the counting rehearsal's own manifest.
- `ValueError` is not a `StageRefused`, so `cmd_registered` does not catch it. The registered analysis stage dies with a traceback. It writes no analysis record and no ENGINEERING STOP status, which is what the ADR requires.
- The registered run's `baselines/` already holds `manifest.json`, from the PAUSED attempt.

### Why did the counting rehearsal pass?

It never called `build_registry` on a real run directory. `run_counting` runs the seven record-producing stages, then `analysis.analyze(synthetic_registry_for(pl))`, a registry built in memory from the plan's labels (`rehearsal_real.py`, about line 228). Its "analysis COMPLETE" therefore says nothing about the registered loader.

### Why no test or audit caught it, mine included

- **The tests.** `run_synthetic` executes baselines through `execute_stage` but, by its docstring, does not run the analysis. The tests that call `do_analysis` or `build_registry` (`test_p10is1_audit_fixes.py`, `test_p10is1_rehearsal.py`) use run directories in which no baselines stage manifest was written. No test combines the two.
- **The audits.** They examined the quiet rule, the freeze and the rehearsal records, not `build_registry`'s inputs.
- **My own miss.** While building the independent recomputation, **my own loader crashed on exactly this file** (`KeyError: 'no_memory'` on `baselines/manifest.json` of the counting rehearsal). I patched my loader to skip records that are not `baseline`, and my comparison harness filtered the same way, but **I did not connect it to the study's `build_registry`**, which globs the same directory. I should have reported it then.

### Options

**(a) One-line fix and an amending freeze.**
- **The fix:** `glob("d*_f*.json")`, or skip records whose kind is not `baseline`. That changes `studies/p10is1/stages.py`, so its hash in the plan's `frozen_files` changes.
- **The procedure:**
  - `candidate-plan` refuses while a freeze record exists, so a new plan needs an amending procedure outside the code;
  - a new freeze record;
  - the freeze's rehearsal gate requires a counting rehearsal record that names the new plan file's SHA-256, so either a new counting rehearsal (about 1.4 charged hours plus the quiet stages with the machine alone) or an explicit ruling;
  - a new Decision 2.
- **Re-verified:** `check_preconditions` and `verify_plan` against the new commit, and the imported files.
- **Completed cells:** records carry no freeze identity (only the launch checks do), so they would be reused mechanically. In substance they stay valid, because no training or evaluation code changes. The record must state "cells under F1, analysis under F2, diff = one loader line".
- **Cost:** heavy. Its advantage is that the registered analysis stage then really runs.

**(b) No code change and no tampering: none exists.**
- Moving or renaming `baselines/manifest.json` before the analysis alters the run directory and the PAUSED and COMPLETE bookkeeping that `build_registry` reads from `*/manifest.json`. That is tampering. Rejected.
- Any configuration route is also a frozen-file change.

**(c) An out-of-tree driver that feeds the frozen `analysis.analyze` the same registry without the manifest.**
- **Precedent:** ADR-0021 §25.21, where P10-S1's defective registered throughput stage was supplemented by a new file.
- The driver is a NEW committed file outside the frozen roots, so identity holds. It:
  - runs `verify_resume_identity.py`'s checks first;
  - builds the `Registry` **exactly** as frozen `build_registry` does, the reads, cpu, ladder stops, qualification, calibration and status (item errors, failed cells, paused manifests, gates) included, **except** that it reads only `d*_f*.json` under `baselines/`;
  - calls frozen `analysis.analyze` and frozen `report.render` unchanged;
  - writes into NEW directories such as `run_dir/analysis_supplement/` and `run_dir/report_supplement/`, never `analysis/analysis.json`.
- **Is it "the registered analysis"?** Not literally: it is not the registered stage through `cmd_registered`. It is **the frozen analysis function on the registered records, through a disclosed corrected loader**, and must be labelled so.
- **How to verify it:**
  1. show that the driver's `Registry` equals what frozen `build_registry` returns when only the glob is patched in memory (same keys and values);
  2. compare with my independent recomputation (`run_registered.sh`, which needs no change; it compares with `analysis/analysis.json` if present, otherwise with the supplement once pointed there).
- The registered `analysis` and `report` stages are recorded as **ENGINEERING STOP — ANALYSIS LOADER DEFECT (not run)**, with this audit and the implementer's reproduction as the evidence.

### Recommendation: (c), decided and committed **before any outcome value is seen**

- It changes no frozen identity and no training or evaluation record. The defect lies only in a loader line that cannot touch any value.
- It follows the P10-S1 precedent.
- Its correctness is checkable twice: by the registry-equality check and by my independent recomputation.

(a) is the stricter record but costs a new rehearsal and Decision 2 for a defect that does not touch the science. Choosing between (a) and (c) is the lead's call, `PENDING LEAD REVIEW`. If (c) is chosen, the addendum should state that the choice was made before the analysis was run.

`Astra review: NOT_PERFORMED`
