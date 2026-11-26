# P10-I-S1: re-audit of the cap extension (d5720ea) and the analysis supplement driver (4c6754e)

Auditor: arbor-auditor subagent, model Opus 5.5 (`claude-opus-5-5`), 2026-11-21. Independent engineering audit. **Not Astra validation and not human approval.** `Astra review: NOT_PERFORMED`.

## What I read and ran

- **Read only:** the diffs `2506c99..d5720ea` and `d5720ea..4c6754e`; the driver; both addenda; `OWED_DISCLOSURES.md`; the new test's text; the frozen code at 46bf55a from my read-only archive.
- **Not done:** I did not run the driver on the registered run, start any stage, read any evaluate output, ladder decision or outcome value, or open any sealed file. Nothing was written in the worktree or the run directory.
- **From the registered stage-output file** (`experiments/P10IS1-registered-20261121-stages.out`), I looked only at its structural lines: stage markers, traceback frames and exception lines. I did not look at any line holding a stage result.
- **Scratch:** a new directory `experiments/_scratch/p10is1_supplement_check_20261121/` (row in `CLEANUP_LOG.md`).

## Verdicts

- **READY TO RESUME EVALUATE+BASELINES**, on two conditions:
  - `vm_stat` must show about 20 GiB available, measured as the study measures it (free + inactive + purgeable + speculative pages);
  - `apply_extension.py --apply` must be run with S1 stopped. It now refuses otherwise.
- **NOT READY TO RUN THE DRIVER AFTER THROUGHPUT.** One required fix (D1). Everything else about the driver is sound.

## 1. R2–R4: met

- **R2.** `apply_extension.py` now refuses `--apply`, writing nothing, while any process whose command line contains `studies.p10is1` is alive outside its own family. The dry run prints the live processes. Its own launch line names no such module, so it does not refuse itself. The remaining risk is a time-of-check gap (a stage started between the check and the write); the lead controls the launches, so it is advisory only.
- **R3 and R4.** The addendum §3 and `OWED_DISCLOSURES.md` now state:
  - the ledger's `evaluate` sum is 3,600 s below evaluate's true charged time;
  - the offset stage never ran;
  - the true figure is the sum of the stage manifests' `charged_seconds`, or the ledger without the two `EXTENSION` entries;
  - which figures stay true;
  - the report prints 1.0 h against an effective 2.0 h.

  I checked each statement against the frozen `Ledger`, `stage_cap_seconds` and `report.py`; all are correct. Baselines shares the cap key `evaluate`, and its own ledger sum stays true.

## 2. The driver

- **What it calls, unchanged:**
  - the registered pre-checks, in the same order as `cmd_registered`;
  - frozen `stages.build_registry`, `analysis.analyze` and `report.render`;
  - `rehearsal_record_of`, `quiet.throughput_label` and `stages.item_errors`.
- **The path object** `RunDir(PosixPath)` filters `glob` only when the directory's own name is `baselines`. It keeps only `d<draw>_f<facts>.json`.
  - In Python 3.12, derived paths keep the subclass, so `(run_dir / "baselines").glob("*.json")` is filtered.
  - Every other glob the frozen loader makes is unfiltered: `run_dir.glob("*/manifest.json")` (paused list), `run_dir.glob("*/item_errors/*.json")`, `run_dir.glob("train/cells/*/cell_failed.json")`, and the attempt globs under `<stage>/attempts`. None of them runs on a directory named `baselines`.
  - The evaluation reads go through `ctx.eval_path`, which is built from the plain run directory.
  - The rehearsal record is read from the freeze record's path, not the run directory.
  - **So the trick alters no other read.** The paused list still sees `baselines/manifest.json`. That is correct, and harmless, because the driver requires baselines COMPLETE.
- **Refusals and writing:**
  - It refuses unless the evaluate and baselines manifests are both COMPLETE.
  - It refuses an output directory inside the run directory, or one that already exists.
  - It writes only under `<run dir>-analysis-supplement` (or `--supplement-dir`).
  - Every JSON output carries `label`, and the report starts with the label.
- **Traceback copying (D1, required).** The driver copies only blocks that begin `Traceback (most recent call last):`.
  - **The real stage-output file has no such line.** `grep -c Traceback` returns 0. The captured output is truncated: the analysis section starts with a caret line, and the report section starts in the middle of a line.
  - So on the real file the driver extracts **zero** blocks. The ENGINEERING STOP record would carry `tracebacks: []` and `traceback_count: 0`, contrary to the driver's docstring and the addendum ("with the text of the two tracebacks").
  - Nothing worse happens: no value would leak. But the evidence the record promises would be silently missing.
  - The test passes only because it uses a synthetic file with full headers.
- **Advisory:**
  - `--supplement-dir` is not refused inside the repository or worktree. A supplement written there would dirty the tree and break later identity checks; refuse it.
  - A second supplement can be written under another name. The analysis is deterministic, so this carries no selection risk, but it should be disclosed if done.
  - Test line 84 compares a listing with itself.

## 3. The registry-equality evidence: sound, and reproduced independently

- **The implementer's test** compares the driver's `Registry` with the frozen `build_registry` source compiled in memory with only the glob line changed. It uses dataclass equality, so all fields are compared, on a synthetic run and on the counting rehearsal.
- **My own check** (`registry_equality.py` → `registry_equality_run1.out`) takes another route:
  - the frozen `build_registry`, **unmodified, on a plain `Path`**, over a symlink view of the counting rehearsal directory whose `baselines/` holds only `d*_f*.json`;
  - against the driver's loader on the real directory.
- **Result:** every field is EQUAL (cells, 469 reads, 3 baselines, ladder stops, cpu, qualification, calibration, status apart from `run`, cfg). The unpatched frozen loader on the real directory raises `ValueError: expected a 'baseline' record, got 'stage_manifest'`.
- The check covers the rehearsal draw only. No registered value was read.

## 4. Throughput, and the order of work: correct

- Only `stages.py` touches `analysis/analysis.json`: `do_analysis` writes it (lines 397 and 400) and `do_report` reads it (line 405).
- The throughput branch calls neither, and nothing in the pre-checks reads it.
- **Throughput can therefore run as registered**: alone, on a quiet machine, with the tree clean.
- Running the driver afterwards lets the supplement's report print the throughput state, and its manifest the measured state.
- **The order** throughput, then driver (once D1 is fixed), is the right one. Commit the D1 fix before throughput, or leave the tree untouched until after it, so throughput's identity check sees a clean committed tree.

## 5. Do the addenda say anything false?

- **Cap extension addendum:** no.
- **Loader defect addendum:** one false statement, in §4 ("Records the registered analysis and report stages … with the text of the two tracebacks"). The driver as written records none (D1). Everything else checks:
  - the defect and its mechanism;
  - that both crashes occurred at 10:45 on 2026-11-21, while baselines was PAUSED;
  - why it was missed, including my own miss;
  - only `do_report` reads `analysis.json`;
  - the ruling made before any value was read.
- **Add to the addendum:** the registered analysis stage was launched once, at 10:45, and crashed inside `build_registry`, before `analyze`. It produced no value, and its seconds were charged to the `analysis` key.

## D1. The required fix

In `extract_tracebacks`:
- take the lines between `=== analysis …` and `=== analysis exit=`, and between `=== report …` and `=== report exit=`;
- keep only the frame lines (`  File …`), the indented source and caret lines, and the final exception line;
- drop any line that begins with `{`.

The driver should **refuse** unless exactly two blocks are found, each ending in the expected exception. Add a test on a copy of the real file's structure, header-less and truncated.

`Astra review: NOT_PERFORMED`
