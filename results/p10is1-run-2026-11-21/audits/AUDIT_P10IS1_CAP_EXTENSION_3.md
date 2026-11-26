# P10-I-S1: re-audit of commit e22ae49 (D1) and the lead's ruling on the dense-speed panel reading

Auditor: arbor-auditor subagent, model Opus 5.5 (`claude-opus-5-5`), 2026-11-21. Independent engineering audit. **Not Astra validation and not human approval.** `Astra review: NOT_PERFORMED`.

## Verdict: READY TO RUN THE DRIVER

## 1. Commit e22ae49

**D1: fixed.**
- `extract_tracebacks` now takes the `analysis` and `report` sections by their markers: from `=== <stage> <date>` to `=== <stage> exit=`, the first section of each name. Within a section it keeps only frame, indented, caret and exception lines and drops every line that begins with `{`.
- `produce` refuses unless exactly two blocks are found. It does so **before** the COMPLETE check and before creating any directory.
- **Tested on the real stage-output file** (`P10IS1-registered-20261121-stages.out`). I ran a copy of the driver at e22ae49, extraction function only (`.venv` Python 3.12 with `-I -B`; script and outputs in `experiments/_scratch/p10is1_supplement_check2_20261121/`). It finds **2 blocks**:
  - analysis: 15 lines, 5 frames, ending `ValueError: expected a 'baseline' record, got 'stage_manifest'`;
  - report: 13 lines, 4 frames, ending `FileNotFoundError: … analysis/analysis.json`.
  - Neither block holds a line beginning `{`.
  - The record's `section_headers` would be the two date markers only.
- **A failed attempt of mine, kept:** `extract_check_run1.out` failed because the system Python 3.9 has no `datetime.UTC`.

**The repository refusal.** `--supplement-dir` inside the worktree is refused. The default `<run dir>-analysis-supplement` lies in `experiments/`, outside the worktree, so it passes.

**Addendum corrections: accurate.** §1 now states:
- the registered analysis stage was launched once at 10:45 and crashed inside `build_registry`, before `analyze`, so it produced no value;
- the report stage crashed three seconds later;
- the stage output was cut to each stage's last 1,500 bytes, with no `Traceback` header.

All of this matches the file's structure. §4 describes the new extraction and the repository refusal, and it requires disclosure of any second supplement directory.

**Tests.** I ran only the light tests of `tests/test_p10is1_analysis_supplement.py` (`-k "extract or refuses_a_supplement or only_the_registered_report or addendum"`): **4 passed**. I did not run the synthetic-run tests, because of the memory limits. The worktree stayed clean (`git status` empty): no bytecode or cache was written.

**Unchanged since my re-audit 2 and still sound:**
- the frozen `build_registry`, `analyze` and `render` are called unchanged;
- the path trick filters only `baselines/` (my registry-equality check: every field EQUAL);
- the run directory is never written, and every output is labelled.

**Before running the driver** with the addendum's §7 command, confirm the stage-output file is the one named there and unchanged since this check. It held 12 stage markers (train through report) when I read it. If the analysis or report stage is ever relaunched and appended to it, the driver still takes the **first** section of each name, the 10:45 crashes.

## 2. The lead's ruling on the dense-speed panel reading: I agree

**Ruling as I understand it:** the registered reading is what the frozen code computes. My recomputation prints its own reading beside it. A difference is a disclosure in the outcome record and never changes a label.

**Why I agree:**
- The frozen `labels.dense_speed` counts a replicate towards DENSE FASTER if **either** panel is sure, and gives DENSE NOT FASTER only if **both** panels are clear in all five replicates.
- That is the reading that cannot favour the store, and it matches ADR-0024 §9's general rule: "a favouring condition needs both panels; a blocking condition needs either".
- It was fixed and audited before any observation.
- My `recompute.py` already computes exactly this reading. After the first comparison runs I aligned it, and that is disclosed in `NOTE.md`. I expect no difference from it.

**One limit, so that the ruling is not read too widely:** it should cover differences of **interpretation**, where the ADR's text admits two readings. If my recomputation finds that the frozen code makes a **computational error** (a value the frozen rule itself would not give), that is an engineering finding to be handled as the loader defect was, by an addendum and the human lead. It is not a disclosure beside a label that stands. I recommend the ruling say so in one sentence.

## 3. Change to my own recomputation launcher (scratch only, not the study)

`experiments/_scratch/p10is1_recompute_20261121/run_registered.sh` now:
- accepts the supplement's `REPORT_SUPPLEMENT.md` as the signal that the analysis exists;
- compares with `<run dir>-analysis-supplement/analysis/analysis_supplement.json` when the registered `analysis/analysis.json` does not exist.

Its syntax was checked; it was not run. `compare.py` already reads a `{"result": …}` wrapper. The comparison will be against the frozen analysis function as applied by the driver, and the output will say which file was compared.

`Astra review: NOT_PERFORMED`
