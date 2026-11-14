# ADR-0016 implementation audit before the freeze — 2026-11-14

- Auditor: **Claude Opus 5.5 (`claude-opus-5-5`)**, auditor role, per this session's own metadata. This is independent engineering and mathematical evidence. It is **not Astra validation and not human approval**. Astra review: NOT_PERFORMED.
- Audited: the uncommitted files `supplements/__init__.py`, `supplements/p8s/{__init__,common,null,sim,frozen,stage,analysis,preflight,synthetic}.py`, `tests/test_p8s_{precondition,wrappers,end_to_end,analysis,frozen,stage}.py` and the preflight record `results/p8-supplement-2026-11-14/preflight/preflight-20261114T135842Z.json`. I did not write any of them. HEAD `6808693`.
- I edited no existing file, did not commit, did not run the supplement stage, and did not null or simulate any panel trace of the five cells. For those cells I read traces and counts only, and rebuilt layouts from the calibration traces. Everything I wrote is in this folder.
- Environment: macOS 27.2.1 arm64, uv 0.12.15, Python 3.12.14, torch 2.8.0, pytest 8.4.1, ruff 0.12.12, mypy 1.17.1, worktree `.venv`. Data: `/Users/daniellaloush/dandush03/ArborLM/experiments`.

## Verdict: **NOT READY TO FREEZE**, because of one MAJOR finding (M1) that needs a small fix

The simulation path is correct and faithful to the frozen code. Its evidence:

- the wrappers differ from the frozen `simulate_panel`/`simulate_cell` only as §4 allows;
- all **55/55** registered cells replay field for field through the new wrappers (test inputs include `b102-o302-s601-C04` with 17 slots and `b102-o302-s602-C05`, a tree cell with 16 slots);
- the detector agrees with my own reference predicate on every adversarial input in its domain;
- the precondition holds on all ten real panel traces, so the registered generator is never reached.

I found no blocker. One requirement of §4 is missing from the records, and those records cannot be regenerated after the single run, so I ask for M1 to be fixed before the freeze.

**After M1:**

- Re-run `supplements.p8s.preflight` on the final code. Any code change alters `supplement_source_sha256`.
- Commit the new preflight record and this folder. The stage refuses a dirty tree.
- A further audit needs only the diff and the new preflight record.

The MINOR items are recommended. None of them blocks.

## Findings

### MAJOR

**M1. The registered P7-B reproduction record is not cited by hash anywhere.**

- **What §4 requires.** "P7-B reproduction gate: not re-run. The registered reproduction record is cited by hash."
- **What the code does.** `sim.py:159-177` drops `reproduction_record_sha256` from every supplementary record, which is right: the supplement did not run that gate. But nothing replaces it. `common.frozen_inputs` (`common.py:124-135`), the stage manifest (`stage.py:167-197`) and the analysis wrapper (`analysis.py:561-572`) do not mention it either.
- **The value.** The registered hash is `86608f87de87cd87b0656a35bbe0e178e9a37609e8fcd69375b1990db9d5f9a8`. It is cited in the registered sim manifest `reproduction_gate.sha256`, which is committed at `b8302c2`. I recomputed it from `scratchpad/p7b_repro_frozen.json`.
- **Required change.** Add to `frozen_inputs`, and to the stage manifest, a field such as `"p7b_reproduction_record_cited": {"sha256": "86608f87…", "source": "reproduction_gate of the registered P8S stage manifest (b8302c2)", "note": "cited, not re-run (ADR-0016 §4)"}`.
- **How to source the value.** Read it from the registered `manifest.json` and check it against its blob at `b8302c2`, or hard-code it and check it there.
- **Test.** Add a test that the field is present.

### MINOR

1. **The W9 status line is not verbatim.**
   - `ADR-0016` line 3 reads "revision 2 with wording changes W1–W9 … Auditor re-check: ready to implement once W1–W9 are applied (they are; recorded in §9.1)". RECHECK W9 prescribed "… Auditor re-check: NOT READY pending wording changes W1–W9 (recorded in §9.1)".
   - The new wording describes the state after W1–W8 were applied, which matches the RECHECK verdict. W1–W8, the line-5 change of W9 and the §9.1 entry are verbatim (`outputs/check_w_applied_run2.txt`).
   - Required: none, or a §9.1 note that line 3 was updated after W1–W9 were applied.
2. **The top-level key `supplement` is outside the literal W6 pattern `supplement_*`.**
   - The key is written at `sim.py:170`. `preflight.compare_replay` excludes keys with `startswith("supplement")` (`preflight.py:76,83`), which is broader than W6.
   - Required: rename it to `supplement_study`, or exclude `supplement_` plus the exact key `supplement`.
   - My strict checker flagged it in run 1 (see "Failed checker attempts").
3. **The analysis wall time is not enforced.**
   - §7 caps "execution and analysis together" at 30 minutes. The stage alone gets the full 1800 s (`stage.py:93`, `common.py:58`), and the analysis only records `combined_within_limit` (`analysis.py:633-641`).
   - The expected stage time is about 5 × 4 s, so this is moot in practice. Still:
     - give the stage a cap below 1800 s, or
     - state that a breach is reported as a limit violation.
4. **Failures outside `SupplementError` leave no failure record.**
   - Analysis: `analysis.main` catches only `SupplementError` (`analysis.py:667`). A `KeyError` or `ValueError` from a malformed record leaves only a traceback; `compare_csvs` raises `ValueError` if a needed column is missing.
   - Stage: if `stage.execute` raises after `allocate_run` (`stage.py:131`), for example from `run_pool`, it leaves a `P8SUP-*` directory with no manifest. That directory correctly blocks a re-run, but the cause is not recorded.
   - Required: wrap both and write a failure manifest or `STOPPED` file that contains the exception.
5. **JSON and text writing.**
   - `json.dumps` with the default `allow_nan=True` and `write_text` with no explicit encoding are used at `analysis.py:574-580,671` and `preflight.py:321`. The label contains an em dash.
   - Required: use `canonical_json`, or `allow_nan=False` with `encoding="utf-8"`.
   - Supplementary CSVs end lines with `\n`, while the registered ones use `\r\n`, because `csv_text` reads them back through `read_text`. The W5 comparison is unaffected because it parses with `csv`. This matters only if bodies are ever compared byte for byte.
6. **The "runs once" guard covers only the experiments root it is given** (`stage.py:77-83`).
   - A run with a different `--experiments-root` would not be refused.
   - Required: refuse a non-default root, or also check for a marker under `results/p8-supplement-2026-11-14/`.
7. **Analysis provenance is tied to the current ADR-0016 and code, which creates an ordering trap.**
   - `check_supplement_provenance` requires the current `ADR-0016` hash and supplement digest to equal those in the records (`analysis.py:119-122,146-149`).
   - So the analysis must run **before any edit to ADR-0016**, including the §10 outcome record. No change to `supplements/p8s/` is possible after the stage.
   - Required: state this order in the run procedure.
8. **Prediction checks: the readings are right, two checks are weak.**
   - The three readings are correct:
     - P1 as `misses_warm == 0` is the literal "counted (post-warm-up) miss count". It is stronger than m = 0.
     - P6's "distinct pages" as `stats.distinct_stream` is the number of distinct pages the whole stream touches.
     - P8 as `[q["case"] for q in open_questions] == ["C09"]` matches the frozen `open_questions` shape, a list of dicts with `case`.
   - **P2 can be vacuous.** `pred_2` (`analysis.py:303-322`) would pass vacuously on stream groups if a null or order stream had an empty group map. `checked > 0` is still met through the temporal-reuse comparisons.
   - **P6 is nearly tautological.** `pred_6` compares against the simulator's own `distinct_stream`. Under the fast path in `p7b_sim.cache_counts`, `misses_all = first_touch_all = distinct_stream` holds by construction whenever `distinct_stream ≤ C`.
   - Suggested:
     - in P2, assert that the key sets equal `{L-FREQ|R2, L-COAX|R2, L-FREQ|R8, L-COAX|R8}`;
     - in P6, also assert `distinct_stream ≤ 8`.
   - My own recomputation after the run will check P1–P9 independently in any case.
9. **Test gaps.** None of these leaves a §6 bullet uncovered:
   - `pred_8` has no unit test (`test_p8s_analysis.py:109` asserts 1–7 and 9 only).
   - `run_stage` refusing because of an existing `P8SUP` run, or a failed frozen verification, is tested only through the helpers.
   - `check_null_stream` re-implements the registered checks rather than calling them. I compared it line by line with `p7a_core.py:436-442`; it is equivalent.
10. **The preflight record must match the frozen code.** The kept record's `supplement_source_sha256` is `21a103c0…e548`, which equals the current code. Any fix changes it, so regenerate the record (see the verdict).
11. **The implementer's failed first pytest run was not kept.** "10 failures in `tests/test_p7b_study.py`" exists only as a report. Per policy the log should have been kept. See item 6 of the checks.

### Observations judged acceptable (no change required)

- **`source_sha256` kept at top level, `spec_sha256` and `reproduction_record_sha256` omitted.**
  - The kept value is the frozen `src/arborlm` digest the supplement actually ran against. §4 lists "the frozen source digest they ran against" as part of the record's identity. It is neither the P8 freeze commit nor the spec hash.
  - Omitting `spec_sha256` is required, because the P8 spec hash is not the supplement's own. It is also protective: the frozen `check_provenance` (`p8_analysis.py:400-405`) would refuse these records, because `spec_sha256` is missing.
  - `schema: "P8-sim-v1"` has to stay, because W6 requires every field outside its list to equal the registered record.
- **`dry_run: False` is hard-coded** in `build_record`. That is truthful for the real run. Preflight replays are written to scratch only.

## What I checked, with counts

1. **No existing file was modified, and the frozen digest is unchanged.**
   - `git status --short` shows only untracked new paths. `git diff --stat` and `git diff --cached` are empty, and `git diff --stat 378aeac HEAD -- src configs pyproject.toml uv.lock .github tests` is empty.
   - `p8_core.source_digest()` = `8b5a03a08fc10a4ac29bdf9c6dd2d21945b9bb3aff459766b58304545d570507`.
   - Blob comparison by `git hash-object` (my own code, `independent_checks.py`):
     - **98** files: 85 under `src/arborlm` at `378aeac` plus 13 others. 0 differ, and no extra working file.
     - **60** `eval.json` and **55** `sim.json` equal to their blobs at `b8302c2`.
     - ADR-0015 working blob = blob at `2d10338` = `add0a376…c8c8`.
     - The tree hashes match: `b13a9f9c…` and `290d15de…`.
2. **`null.py`.**
   - **Precondition** (`null.py:48-87`) is exactly §3: eight non-zero slots, each equal to Q, then the redundant check that every sorted row equals S. The total check is redundant but harmless.
   - **Identity rows** are S ascending (`null.py:90-94`).
   - **Hash.** `stream_sha256` = `sha256(p7a_core._pack(stream,"h"))`. I recomputed it independently with `struct.pack("<{8Q}h")`; it is equal.
   - **Seeds.** They are recorded through the pure `fm_generator_seed`, with no RNG consumed.
   - **Precondition-false branch.** It calls `b_core.null_streams(counts, seeds, index)` unchanged and only adds `precondition: False`.
   - **Adversarial inputs** (`adversarial_detector.py`, `outputs/adversarial_detector_run2.txt`) agree with my reference predicate on all 12 in-domain cases:
     - duplicates that preserve every count, which only the direct check catches;
     - one count Q−1 with another Q+1; nine slots; seven slots plus a repeat;
     - Q = 1 and Q = 3; slot 0; int16 and int32 input; an empty trace.
   - **Same outcome as the registered generator on the false branch:** both raise `InvariantError` on a nine-slot near-collapse, and the streams are identical on a 32-hot-slot trace.
   - **Out-of-domain input:** a negative slot ID raises a `RuntimeError` from `bincount`. `load_trace`/`check_trace` exclude such IDs first.
3. **The `sim.py` wrappers.**
   - **Mechanical diff** against `p8_sim.py:261-374`, with module-local names qualified: the only differences are the null provider, `NULL_KEYS` adding `method`/`precondition`, the added `supplement_null_preconditions`, and docstrings. The frozen `simulate_cell` never compared the spec hash, and the eval-record source-digest check is kept.
   - **No monkeypatching:** `grep` for setattr, patch, mock, importlib, `sys.modules`, `globals`, exec and eval finds nothing in `supplements/`.
   - **Replay** of all 55 registered cells through `build_record` with the default provider (precondition evaluated: false on all 110 panels). Every field is type-strictly equal to the registered `sim.json` once the W6 list (plus the `supplement` key, MINOR 2) is excluded, and all 55 layout files are equal.
   - **Frozen `simulate_cell` on `b102-o302-s601-C04` and `b102-o302-s602-C05`:** also equal. This confirms that the registered records are reproducible on this machine.
4. **`frozen.py` and `stage.py`.**
   - **W3 coverage.** The verification compares exactly the W3 list:
     - every file under `src/arborlm` (with extras flagged), the config, `uv.lock`, `pyproject.toml` and the ten test files;
     - the digest;
     - ADR-0015 against `2d10338`, with a classifier that requires the change to be only the status line plus §17;
     - 60 + 55 records against `b8302c2`, with the five missing `sim.json` accepted only when no blob exists.
   - **What the stage refuses, in order:**
     - a dirty tree (`--untracked-files=all`);
     - a missing or non-ancestor freeze commit;
     - `supplements/`, `tests/test_p8s_*` or ADR-0016 at HEAD differing from the freeze;
     - an existing `P8SUP-*`;
     - a frozen-verification failure.
   - **Limits.**
     - One worker is enforced.
     - 2 GiB RSS is enforced: the frozen pool kills the worker.
     - The 1800 s wall time is enforced for the stage (pool cap plus worker deadline) and only recorded for the analysis (MINOR 3).
     - Failure records are written by the frozen pool, with "not re-run".
   - **Identity.**
     - Records carry `supplement_spec_sha256`, `supplement_source_sha256`, `supplement_freeze_commit` (commit, tree and `supplements_tree`) and `frozen_inputs`.
     - Records do not state the P8 freeze or spec as their own.
     - The reproduction-record citation is missing (M1).
5. **`analysis.py`.**
   - The frozen `analyse` is called unchanged on 60 `CellData` (`analysis.py:541`). The labels are exactly those of §5.
   - **W5 rule** (`adversarial_w5.py`, `outputs/adversarial_w5_run1.txt`): all 21 cases behave as W5 requires.
     - Correctly stopped:
       - `bool` vs `int`, and a last-bit float change;
       - extra keys or a longer list under C06; C10 referring to C04;
       - any change to `open_questions` or other `decision_inputs`, `concentration_controls_bind`, a new top-level key, or `schema`.
     - Allowed: anything under C04/C05, `section_8_*`, and `int` 3 vs `float` 3.0.
     - CSV rules: a reordering of registered rows and a value change in a non-C04/C05 scorecard row are both caught; a change in the `study_status` column alone is allowed.
   - **Zero handling:** I checked the frozen `ratio`, `retention` and `geometric_mean_ratio` for 0/0 on collapsed C05-vs-C04 pairs. They return `None` with a reason and do not raise.
   - **The preflight's own check:** the 55-cell analysis reproduces the registered `analysis.json` and its CSVs exactly.
6. **Tests and the reported flake.**
   - **Lint and types:**
     - `uv run --locked ruff check .`: all checks passed, including this folder.
     - `uv run --locked mypy src/arborlm supplements/p8s`: no issues in 94 source files.
   - **Full suite.** `uv run --locked pytest -q -p no:cacheprovider` → **859 passed, 3 skipped**, in 264 s.
   - **New files alone:** 61 passed, 0 skipped. Every §6 gate-4 bullet is covered by a test or by the recorded preflight script.
   - **`tests/test_p7b_study.py`, three further runs, all 40/40 passed:**
     - alone;
     - twice in parallel with each other;
     - in parallel with a third pytest process running the p8s tests.
   - **The 10 failures did not reproduce. No log of them exists.**
   - **Why the new files are unlikely to be the cause:**
     - pytest orders `test_p7b_*` before `test_p8s_*`;
     - the new tests write only to `tmp_path`;
     - they create no `*.py` under `src/arborlm`.
   - **A known mechanism that is not the reported one.** `p7b_study.dry_run` returns 1 if the top-level listing of the repository's `results/` or `experiments/` changes during the pipeline fixture (`p7b_study.py:956,1011-1014`). The implementer's preflight created `results/p8-supplement-2026-11-14/` at 08:58:27. If that coincided with a running suite, it would fail `test_dry_run_completes_…` (`test_p7b_study.py:80-81`). That explains **one** failure, not ten.
   - **Conclusion:** the "10 failures" are unexplained and unverifiable. They are not attributable to the new files. **PENDING LEAD REVIEW:** whether to require that no CLI writing under `results/` runs during a test run.
7. **Preflight re-run and independent reproduction.**
   - I ran `uv run --locked python -m supplements.p8s.preflight --scratch <scratch>/audit_p8s_preflight/scratch --out-dir docs/reviews/p8-supplement-preflight-2026-11-14/outputs/preflight_rerun`. All five checks pass in 15 s, and the supplement digest is the same as the kept record's.
   - My own code (`independent_checks.py`) agrees:
     - blob counts **98/60/55**;
     - layout files of all **5** cells, rebuilt from calibration only, byte-equal to the failed-directory files;
     - replay equality on **4** cells, then **55**, with only the W6 fields excluded.
   - `five_cell_preconditions.py` reads only the traces: the precondition holds on all **15** traces of the five cells (calibration, A, B). Each has 8 slots, 1 distinct row set, and Q = 32,768.
8. **Ways the single run could fail for an engineering reason.**
   - **Paths:** the default experiments root resolves to the main checkout's `experiments/`. The eval run, the registered P8S run (with the five `layouts.int16.bin`) and the registered analysis directory all exist, and no `P8SUP-*` exists yet.
   - **Worker spawn:** `-m supplements.p8s.sim` with `PYTHONPATH=<repo>` is exercised end to end by `test_execute_runs_one_worker_keeps_failures_and_records_limits`.
   - **Deadline:** generous.
   - **RSS:** registered workers peaked near 260 MB.
   - **Precondition:** it holds on all ten panel traces, so the generator is not reached.
   - **Remaining traps:**
     - the stage refuses until this folder and `results/p8-supplement-2026-11-14/` are committed (clean tree);
     - ADR-0016 must not be edited between the stage and the analysis (MINOR 7);
     - an unexpected exception leaves no reason on record (MINOR 4).

## Failed checker attempts and my own discrepancies (kept)

- **`check_w_applied.py`, run 1** (`outputs/check_w_applied_run1.txt`) reported W6 and W8 as NOT FOUND. My checker compared unindented lines and whole lines; W6 items are nested under gate 4, and W8 is a fragment inside a sentence. Run 2 strips indentation and uses substring matching for fragments. Only W9's line 3 remains different (MINOR 1).
- **`independent_checks.py`, run 1** (`outputs/independent_checks_run1.json`) listed all four replay cells as failures. The sole difference was the top-level `supplement` key, which my literal `supplement_*` rule did not exclude. Run 2 (all 55 cells) excludes it explicitly under the label "NOT literally supplement_*" and recorded 0 failures (MINOR 2).
- **`adversarial_detector.py`, run 1** (`outputs/adversarial_detector_run1.txt`, truncated) crashed in my precondition-false test. The frozen generator itself raises on my nine-slot near-collapse input. Run 2 compares the outcomes of the supplement path and the registered generator, including the exception, and adds a non-failing trace.
- **`adversarial_w5.py`** labels one case "NaN … on both sides". In fact NaN is set on the new side only, so the case tests a NaN-vs-number difference, which correctly stops. A NaN on both sides cannot occur, because the registered file was written with `allow_nan=False`.
- **Formatting.** After the outputs were produced I ran `ruff format` on my five scripts. The changes are formatting only, so the recorded outputs still correspond to the code.

## Commands (repository root)

```
git status --short; git diff --stat; git diff --stat --cached
git diff --stat 378aeac HEAD -- src configs pyproject.toml uv.lock .github tests
uv run --locked python docs/reviews/p8-supplement-preflight-2026-11-14/check_w_applied.py            # runs 1, 2
uv run --locked python -m supplements.p8s.preflight --scratch <scratch>/audit_p8s_preflight/scratch \
  --out-dir docs/reviews/p8-supplement-preflight-2026-11-14/outputs/preflight_rerun
uv run --locked python docs/reviews/p8-supplement-preflight-2026-11-14/independent_checks.py \
  /Users/daniellaloush/dandush03/ArborLM/experiments <scratch>/audit_p8s_preflight/ind1                # run 1 (4 cells)
uv run --locked python docs/reviews/p8-supplement-preflight-2026-11-14/independent_checks.py \
  /Users/daniellaloush/dandush03/ArborLM/experiments <scratch>/audit_p8s_preflight/ind2 all allow-supplement-key   # run 2 (55 cells)
uv run --locked python docs/reviews/p8-supplement-preflight-2026-11-14/adversarial_detector.py       # runs 1, 2
uv run --locked python docs/reviews/p8-supplement-preflight-2026-11-14/adversarial_w5.py
uv run --locked python docs/reviews/p8-supplement-preflight-2026-11-14/five_cell_preconditions.py /Users/daniellaloush/dandush03/ArborLM/experiments
uv run --locked ruff check .
uv run --locked mypy src/arborlm supplements/p8s
uv run --locked pytest -q -p no:cacheprovider
uv run --locked pytest -q -p no:cacheprovider tests/test_p8s_*.py
uv run --locked pytest -q -p no:cacheprovider tests/test_p7b_study.py           # alone, then 2x concurrently + p8s concurrently
```

`<scratch>` = `/private/tmp/claude-501/-Users-daniellaloush-dandush03-ArborLM--claude-worktrees-arborlm-consolidation-experiment-2b31c1/cfc0efd5-b7ca-4602-959a-07fe6b8d4e7d/scratchpad`. The supplement code digest at audit time was `21a103c05055a8a7174a52fdaffa16d1445f398f6b6f2d8c7e65394406c7e548`, and the ADR-0016 sha256 was `22d25195851360f6a260062de1f641f9d6a394d92f0121d383fe1371b6a64458`.

## Re-check after fixes — 2026-11-14

- Auditor: **Claude Opus 5.5 (`claude-opus-5-5`)**, same session and role as above. Not Astra validation, not human approval. Astra review: NOT_PERFORMED.
- Scope: the fixes the implementer reports for M1 and MINOR 2, 4, 5, 8 and 9. MINOR 1, 3, 6, 7 and 11 are reported as deliberately unchanged. HEAD is still `6808693`. Supplement code digest is now `88b86f48b1bfe8fce106b243a679335b9d1ca78cf85fa288047120ed07245377`. ADR-0016 sha256 is unchanged at `22d25195…4458`.
- I edited no file other than this one, plus new files in this folder (`recheck_keysets.py`, `outputs/recheck_*`, `outputs/preflight_recheck/`). I did not commit, did not run the stage, and did not simulate or null any panel trace of the five cells.

### Verdict: **READY TO FREEZE**

No required change. M1 is fixed and verified. The simulation path is byte-identical to the audited one. The new failure wrappers and the stricter P2/P6 checks are correct. Lint, types and the full suite pass. The remaining items below are optional or procedural.

### 1. M1: the P7-B reproduction record is now cited by hash

- **Where the constant lives.** `common.py:54` defines `P7B_REPRODUCTION_SHA256 = 86608f87…f9a8`, and `common.p7b_reproduction_record_cited()` is at `common.py:66-72`.
- **Where it is cited:**
  - `frozen_inputs` (`common.py:148`), which goes into every supplementary `sim.json`, because `sim.py:175` calls `common.frozen_inputs`;
  - the stage manifest (`stage.py:218`);
  - the analysis wrapper (`analysis.py:591`).
- **Check and refusal.** `frozen.check_p7b_citation` (`frozen.py:75-93`) compares the constant with `reproduction_gate.sha256` in the blob of the registered P8S `manifest.json` at `b8302c2`. A mismatch, a missing blob or unreadable content becomes a problem, and `verify_frozen_files` (`frozen.py:126-128`) makes that problem refuse both the stage and the analysis.
- **Provenance checks.** `check_supplement_provenance` refuses records or a manifest whose citation differs (`analysis.py:128-131,155-156`).
- **Tests.**
  - `test_p8s_frozen.py:112-140`: presence, equality with the blob, and refusal on mismatch, missing blob and unreadable content;
  - `test_p8s_stage.py:151,158`;
  - `test_p8s_analysis.py:268-296,338`.
- **Independent check of the value.**
  - `git show b8302c2:results/p8-2026-11-14/simulate/P8S-20261114T043952694180Z-088e6814edcd465894aebd125d53ddc3/manifest.json` gives `reproduction_gate.sha256 = 86608f87de87cd87b0656a35bbe0e178e9a37609e8fcd69375b1990db9d5f9a8`.
  - `shasum -a 256` of the file that manifest names (`<scratch>/p7b_repro_frozen.json`) gives the same value.
- **Observation, PENDING LEAD REVIEW.** The cited record exists only at a session-scratchpad path, which the registered manifest's `reproduction_gate.file` names. It is not in the repository. ADR-0016 §4 asks only for a hash citation, so this does not block the supplement. Whether the record itself should be preserved is a pre-existing P8 matter.

### 2. The simulation path is unchanged

- **Per-file hashes.** I compared each file's current sha256 with the per-file hashes in **my own** preflight rerun record from the audit (`outputs/preflight_rerun/preflight-20261114T140324Z.json`, digest `21a103c0…e548`):
  - `sim.py` (`3680345c…`), `null.py` (`c63e175f…`), `synthetic.py` and `__init__.py` are **byte-identical**;
  - only `analysis.py`, `common.py`, `frozen.py`, `preflight.py` and `stage.py` changed.
- **The digest.** I recomputed it with my own code from every `supplements/p8s/*.py`, using the same recipe as the frozen digest: `88b86f48…5377`. This matches the reported value.
- **Changes that reach records.** `common.py` changed what the worker records only by adding the citation to `frozen_inputs`. That key is in the W6 exclusion list.
- **Re-runs:**
  - Preflight on the current code (`outputs/preflight_recheck/preflight-20261114T143044Z.json`, `outputs/preflight_recheck_run1.log`): all five checks PASS, overall PASS, digest `88b86f48…`.
  - My `independent_checks.py`, run 3, all 55 cells (`outputs/recheck_independent_checks_run3_all55.json`):
    - 98 frozen files compared, 0 differing;
    - 60 `eval.json` and 55 `sim.json` equal to their blobs;
    - the 5 rebuilt layouts equal;
    - **55/55 replayed, 0 failures**.
- **MINOR 2** is fixed by narrowing the exclusion, not by renaming the key. `preflight.is_supplement_key` (`preflight.py:63-65`) now excludes exactly `supplement` and `supplement_*`. This is acceptable: the key `supplement` is listed explicitly in the excluded fields.

### 3. Failure wrappers (MINOR 4) and stricter P2/P6 (MINOR 8)

**Stage (`stage.py:130-157`).**

- The `try` wraps only `_execute_in`. On success, `run` is returned exactly as before.
- `except Exception` writes a `FAILED` manifest with the exception type, message, traceback and identity, then re-raises.
- A successful run therefore cannot be masked or altered. The success manifest is the last statement of `_execute_in`, so nothing after it can raise into the wrapper.
- The failed folder blocks a re-run. Tested at `test_p8s_stage.py:166-200`.

**Analysis (`analysis.py:597-604,716-731`).**

- The wrappers act only on exceptions.
- `failed.json` is written into the output folder if `_write_files` fails, and a `STOPPED-*.json` is written for any other exception. Both re-raise.
- The success path still returns `out`.
- **MINOR 5** is fixed by the switch to `_dump(..., allow_nan=False)` plus UTF-8 writes. That can only turn a NaN or infinity, which the old code would have written silently, into a recorded failure.
- The frozen writers and the registered `analysis.json` already use `allow_nan=False`. I verified earlier that the frozen zero handling returns `None` for 0/0. So I do not expect this to trigger on the real five cells.

**P2 (`analysis.py:311-343`).**

- The stream key sets must now equal `{L-FREQ|R2, L-COAX|R2, L-FREQ|R8, L-COAX|R8}`, be non-empty, and be a subset of `actual`.
- **Evidence:** my `recheck_keysets.py` (`outputs/recheck_keysets_run1.txt`) read all 55 registered `sim.json`:
  - 110 panels across three variants: 44 flat, 12 `fixed_tree` and 54 `learned_tree`;
  - in every panel the `order_shuffled`, `null_1`, `null_2` and `null_3` key sets are exactly those four keys;
  - `temporal_reuse` has all five streams;
  - `actual` is a superset (5 or 6 layouts × R2/R8).
- This is structural. In frozen `p8_sim.simulate_trace` (`p8_sim.py:73-74,159-180`), the order-shuffled and null keys come only from the constants `ORDER_LAYOUTS`/`NULL_LAYOUTS` × `ROWS`. They do not depend on the data.
- From their `eval.json`, the five cells are `C04` flat (2) and `C05` `learned_tree` (3). Both variants are covered above.
- Group records carry no stream label (`p7b_sim.simulate_group` returns only `stats` and `by_c`), so equality with `actual` is a fair test.

**P6 (`analysis.py:395-420`).**

- It adds `distinct <= 8`.
- On the five cells this holds for every layout and stream. Each trace uses exactly 8 slots (§3 precondition, verified on all 15 traces in the audit). A page holds ≥ 1 slot, so there are at most 8 distinct pages. 8 is ≤ C, which is 32 at R=2 and 8 at R=8.
- So the check cannot falsely fail, and it now catches a self-consistent nine-page group (`test_p8s_analysis.py:423`).

**MINOR 9.** `pred_8` now has a test (`test_p8s_analysis.py:384`). The CLI refusals for an existing run, a failed verification and a dirty tree are tested at `test_p8s_stage.py:203-240`.

### 4. Lint, types, tests and frozen material

- `uv run --locked ruff check .`: All checks passed (`outputs/recheck_ruff_mypy_run1.txt`).
- `uv run --locked mypy src/arborlm supplements/p8s`: no issues in 94 source files.
- `uv run --locked pytest -q -p no:cacheprovider`: **874 passed, 3 skipped**, 3 warnings (torch UserWarnings), 264.28 s (`outputs/recheck_pytest_full_run1.txt`). At audit time the count was 859 passed; the difference is 15 new tests.
- `tests/test_p8s_*.py` alone: **76 passed** (61 at audit time).
- `git status --short` shows only the same untracked paths. `git diff --stat`, `git diff --cached --stat` and `git diff --stat 378aeac HEAD -- src configs pyproject.toml uv.lock .github tests` are empty. No tracked file is modified.
- The frozen digest is unchanged: the preflight `frozen_material` check PASS, and my independent comparison found 98/98 files equal.
- `__pycache__/` is ignored (`.gitignore:2`), so test and preflight runs do not dirty the tree for the stage's clean-tree gate.

### 5. Other engineering risks for the single run

**Nothing blocking.** Optional, non-blocking notes:

- **R1.** `stage.main` catches `SupplementError` and prints "REFUSED". If a `SupplementError` were raised *after* the folder exists, the manifest would correctly say `FAILED` but stderr would say "REFUSED". No code path in `_execute_in` raises it today. Cosmetic.
- **R2.** If the failure-manifest write itself raised, the original exception survives only as `__context__` in the traceback. The analysis can write both a `failed.json` and a `STOPPED-*.json` for one failure. A `BaseException` such as `KeyboardInterrupt` is not recorded. All acceptable.

**Unchanged procedural traps, all still true:**

1. Commit the supplement code, the tests, `results/p8-supplement-2026-11-14/` and this folder (including `outputs/preflight_recheck/`) before the stage. The stage refuses an untracked file.
2. Run the analysis **before any edit to ADR-0016 or `supplements/p8s/`** (MINOR 7).
3. Use the default experiments root (MINOR 6).

**Status of the other minors.** MINOR 1, 3, 6, 7 and 11 are unchanged, as reported. MINOR 10 is resolved in effect: the implementer regenerated the preflight record (`preflight-20261114T142809Z.json`, digest `88b86f48…`) and kept the superseded one with a README.

### Re-check commands (repository root, same environment as above)

```
shasum -a 256 supplements/__init__.py supplements/p8s/*.py tests/test_p8s_*.py
git show b8302c2:results/p8-2026-11-14/simulate/P8S-20261114T043952694180Z-088e6814edcd465894aebd125d53ddc3/manifest.json   # reproduction_gate
shasum -a 256 <scratch>/p7b_repro_frozen.json
uv run --locked ruff check . ; uv run --locked mypy src/arborlm supplements/p8s
uv run --locked python -m supplements.p8s.preflight --scratch <scratch>/recheck/preflight_scratch \
  --out-dir docs/reviews/p8-supplement-preflight-2026-11-14/outputs/preflight_recheck
uv run --locked python docs/reviews/p8-supplement-preflight-2026-11-14/independent_checks.py \
  /Users/daniellaloush/dandush03/ArborLM/experiments <scratch>/recheck/ind3 all allow-supplement-key   # run 3
uv run --locked python docs/reviews/p8-supplement-preflight-2026-11-14/recheck_keysets.py /Users/daniellaloush/dandush03/ArborLM/experiments
uv run --locked pytest -q -p no:cacheprovider
uv run --locked pytest -q -p no:cacheprovider tests/test_p8s_*.py
```

**Failed checker attempts in the re-check:** none. `recheck_keysets.py` declares an unused list `five` and reads the cells' variants from `eval.json` directly instead. This has no effect on the output.
