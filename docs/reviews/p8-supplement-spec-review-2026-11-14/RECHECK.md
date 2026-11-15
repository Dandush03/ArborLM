# Re-check of ADR-0016 revision 2 — 2026-11-14

- Reviewer: **Claude Opus 5.5 (`claude-opus-5-5`)**, auditor role, per this session's own metadata. This is **not Astra validation and not human approval**. Astra review: NOT_PERFORMED.
- Text reviewed: `docs/decisions/ADR-0016-p8-supplement-collapsed-cell-simulations.md` (139 lines). This is the working-tree version: committed `356a29d` plus the uncommitted §9 approval edit.
- I edited no existing file, did not implement anything and did not simulate any of the five cells. New files are this one, `recheck_import_probe.sh` and `outputs/recheck_import_probe_run1.txt`.
- Environment: macOS arm64, uv 0.12.15, Python 3.12, worktree `.venv` (ruff 0.12.12, mypy 1.17.1, pytest 8.4.1).

## Verdict: **NOT READY** as written. Every remaining change is wording only.

The mathematics, the exception and the governance framing are now sound. Revision 2 still makes one plan infeasible: under the unchanged repository config, the test files at the chosen location cannot import the chosen package. It also leaves two gates vacuous or unnamed. Once W1–W9 below are applied verbatim, I consider it **READY TO IMPLEMENT** without another re-check. Gate 5, the implementation audit, still applies.

## 1. Status of the original findings

| # | Finding | Status | Reason |
|---|---|---|---|
| B1 (f1) | Frozen identity checks / provenance | **PARTLY** | The code location, the not-called list and the identity fields are fixed. The blob check omits `uv.lock` and `pyproject.toml`, which ADR-0015 §16.7 lists. The ADR-0015 exemption names no reference blob. → W3 |
| M1 (f2) | Copied `simulate_panel`, `method` field | RESOLVED | Copied wrappers, monkeypatching forbidden, `method` kept, replay test. |
| M2 (f3) | Replay gate | **PARTLY** | It runs through the new wrappers and includes the near-collapsed cell. The excluded fields are "a named list" that is never named. No tree cell is required. The check needs local data, so a skipped pytest would pass it vacuously. → W6 |
| M3 (f4) | Reference for originals | **PARTLY** | `sim.json` is verified against `b8302c2`. The 60 `eval.json` inputs are not. → W3 |
| M4 (f5) | Exception and governance | **PARTLY** | The exception is named and accepted in the human's words. The rule is marked PENDING ASTRA REVIEW. Workflow authorization (c) is inferred, not stated (§3 below). Lines 3 and 5 will be stale. → W9 |
| M5 (f6) | COMPLETE / letter envelope | RESOLVED | Nested envelope, CSV/Markdown header, §8 bullets. |
| m (f7) | §2 overstatements | RESOLVED | E scope is per cell versus case. "Registered decision stays `none`". |
| m (f8) | Exact predictions / oracle | **PARTLY** | Missing: identical null hashes, `misses_all = first_touch_all`, controls not binding, `open_questions = [C09]`, supplementary letter `c`. → W7 |
| m (f9) | Precondition redundancy | RESOLVED | Stated, with a redundant direct check. |
| m (f10) | Panel B evidence / dead branch | RESOLVED | "Not expected to be taken". |
| m (f11) | Stream-hash definition / disclosures | **PARTLY** | Disclosures are present. "Registered packing" is not exact. The three hashes are not stated to be identical. → W8 |
| m (f12) | Gate order and missing gates | **PARTLY** | Order is fixed. (ii) is in. (iii) is declined with a reason, which is the lead's choice. (i) is missing: rebuilt layouts versus the five `layouts.int16.bin` files already in the failed cell directories (they exist; checked). (iv) is missing Q ≠ 32,768. The synthetic 60-cell run does not require single-set C04/C05 with m = 0. → W6 |
| m (f13) | Freeze-commit reference | **PARTLY** | `378aeac` plus tree are used. The supplement's own freeze commit has no tree hash, and the single-line pre-push rewrite changes hashes. → W4 |
| m (f14) | Keys allowed to differ | **NOT RESOLVED** | The list is both incomplete and too broad (§2 (iv)). → W5 |
| m (f15) | Six §8 additions | RESOLVED (6/6) | (c) not registered; COMPLETE not registered; classes not registered; means do not supersede; identity null carries no locality information; no replication. |
| — | §2.1 analytic addendum (PENDING LEAD REVIEW) | RESOLVED | Offered. The human chose execution. |

## 2. New checks on revision 2

### (i) `supplements/p8s/` with `tests/test_p8s_*.py` — digest-compatible, but the tests cannot import it as specified

- **Frozen digest: compatible.** `p8_core.source_hashes` hashes `Path(__file__).parent.rglob("*.py")`. That is `src/arborlm/` only (editable install `.pth` → `<worktree>/src`). A top-level `supplements/` is not included.
  - Current digest: `8b5a03a08fc10a4ac29bdf9c6dd2d21945b9bb3aff459766b58304545d570507`. This equals the frozen value.
  - `git diff 378aeac HEAD -- src configs tests pyproject.toml uv.lock .github` is empty.
  - The frozen `simulate_cell` eval-record digest check (`p8_sim.py:320`) would therefore still pass.
  - `spec_sha256()` is now `d4bdd771…cbf4` (ADR-0015 §17). The copied wrapper must not compare it.
- **pytest: incompatible as written.** CI and CLAUDE.md run `uv run --locked pytest`. pytest is started through its console script, so the repository root is not on `sys.path`. `tests/` has no `__init__.py`, so rootdir-prepend inserts only `tests/`. That is why `p8_dry`/`p8_fake` import, but `supplements` does not. Probe (`recheck_import_probe.sh`, output `outputs/recheck_import_probe_run1.txt`):
  1. A plain `from supplements.p8s import X` in `tests/test_p8s_plain.py` fails under `uv run --locked pytest` with `ModuleNotFoundError: No module named 'supplements'`. It passes only under `python -m pytest`, which adds the cwd. That is not the gate command.
  2. Inserting the repository root into `sys.path` at the top of the test file passes under `uv run --locked pytest`.
  3. ruff 0.12.12 accepts that file with no E402.
- **mypy: the gate is vacuous as written.** `uv run --locked mypy src/arborlm` never sees `supplements/`.
  - `mypy supplements/p8s` alone fails with `import-untyped`, because `arborlm` has no `py.typed`.
  - `mypy src/arborlm supplements/p8s` passes (87 files on the probe copy).
  - No config change is needed.
- **ruff, packaging, CI.** `ruff check .` covers `supplements/`. Hatchling builds `src/arborlm` only, and the top-level directory does not affect `uv sync --locked`. `.gitignore` does not ignore `supplements/`. CI needs no change once W1 is applied.
- **Location.** Keep `supplements/p8s/`, but add W1 (sys.path line in each test file, the mypy command, the `-m` runner). No location inside `src/arborlm/` is compatible. Putting production code under `tests/` would import without any change, but I do not recommend it.

### (ii) Frozen functions are callable without the refused gates — YES

Nothing below reads the digest, the spec hash, `require_freeze` or `verify_freeze`:

- `p8_sim`: `load_trace`, `simulate_trace`, `build_p8_layouts`, `layout_hashes`, `temporal_reuse`, `branch_persistence`, `m_fraction`.
- `p8_analysis`: `CellData`, `analyse`, `decision_inputs`, `cells_rows`, `pairs_rows`, `scorecard_rows`.
- The p7a/p7b helpers they use. grep finds `spec_sha256` only as definitions in `p7a_core` and `p7b_core`.

Notes on using them:

- `load_trace` → `read_trace` verifies each `.bin` against the `sha256` in `eval.json`. `check_trace` requires Q = 32,768.
- `scorecard_rows` expects `clean_scorecard_source(result)`. These, `jsonable`, `jsonable_floats` and `write_csv` are pure and should be listed.
- The identity-null record needs `p7a_core.fm_generator_seed` and `p7a_core._pack`.
- Nothing in the "called unchanged" list is gated.

### (iii) Commits — both exist and are pushed

- `378aeac1f6d1…` has tree `b13a9f9c0908…` and is an ancestor of HEAD and on `origin/claude/p8-locality-aware-training`. It equals `80f46ae`, which is on the local backup branch only.
- `b8302c247c30…` is already the **pushed** hash; the original was `8efdcc7a…`; tree `290d15de…`. It is an ancestor of HEAD.
- `b8302c2` contains 60 `eval.json`, 55 `sim.json`, 5 `sim.failed.json` and the three stage manifests. It contains **no** `.bin` trace or layout files; those exist only under the main checkout's `experiments/`.
- ADR-0015's current blob is `add0a37659e2…`, the same at `2d10338`, `d3aded5` and HEAD.

### (iv) §5 key list — incomplete and too broad

Checked against `analyse`, `decision_inputs`, `run_analysis` and the row builders:

- No case other than C04/C05 references C04 or C05. `CASE_BASELINE`, `CASE_FLAT_COUNTERPART` (C05→C04 only) and C10's references (C06, C08) confirm this.
- **Missing from the ADR list:**
  - `cells_with_complete_records` (55 → 60);
  - the run-level keys `dry_run` and `inputs`, which `run_analysis` adds and `analyse` does not;
  - every CSV;
  - in particular `scorecard.csv`'s `study_status` column, which `scorecard_rows` fills from `result["study_status"]` in **every** row, so all ten rows change.
- **Too broad:** "control-binding entries" and "decision inputs derived from them". By prediction, `concentration_controls_bind` stays `false` and `open_questions` stays `[C09]`. The registered C04/C05 class is INCOMPLETE, which is not in `open_questions`; QUALITY-FAILED is not either. Only `section_8_option_indicated` and `section_8_reason` may differ.
- **My own discrepancy:** finding 14 of the original review said only the C04/C05 rows of `scorecard.csv` differ. That was wrong for the same reason.

## 3. Approval text (§9) versus M4

- **Covers (a) and (b).** "let's run the 5 simulation as a supplements and by this im accepting the exception" was given after the human was shown §1.1, which names ADR-0015 §11 and the `sim.failed.json` note.
- **Does not explicitly cover (c).** M4 asked for explicit authorization of the study-specific Claude workflow (lead, implementer and auditor roles, no Astra). The lead infers it from "run … in this session". That is a reasonable reading but not an explicit authorization.
- **Remains for the human:**
  1. A one-line explicit authorization of the Claude workflow for this supplement.
  2. Confirmation that the wording changes W1–W9 below, which are engineering-only and alter no hypothesis, threshold, null rule or cell, may be recorded in §9.1 without re-approval.
- Nothing here is human approval or Astra review.

## 4. Required wording changes (apply verbatim)

**W1 — §4, replace the bullet beginning "No frozen file is edited" with:**

> - **No frozen file is edited and none is added under `src/arborlm/`.** The frozen source digest covers every `*.py` under `src/arborlm/`; a new file there would change it. Supplement code lives in a new top-level package `supplements/p8s/` (with `supplements/__init__.py` and `supplements/p8s/__init__.py`) and is run from the repository root as `uv run --locked python -m supplements.p8s.<module>` (not with `-I`, which removes the repository root from `sys.path`). Tests live in `tests/test_p8s_*.py`; because `uv run --locked pytest` does not put the repository root on `sys.path`, each such file inserts it (`sys.path.insert(0, str(Path(__file__).resolve().parents[1]))`) before importing `supplements.p8s`. `pyproject.toml`, `uv.lock`, `tests/conftest.py` and the CI workflow are not changed. Type checking of the supplement uses `uv run --locked mypy src/arborlm supplements/p8s`.

**W2 — §4, replace the "Frozen functions called unchanged" bullet with:**

> - **Frozen functions called unchanged** (none reads the source digest, the spec hash or the freeze): `p8_sim.load_trace`, `build_p8_layouts`, `layout_hashes`, `simulate_trace`, `temporal_reuse`, `branch_persistence`, `m_fraction`; `p7b_layout.write_layout_file`, `verify_partitions`, `CalibrationTrace.declared`; `p7a_core.selection_counts`, `query_order`, `fm_generator_seed`, `_pack`, and `frequency_matched_detail` via `p7b_core.null_streams` (precondition-false branch only); `p8_analysis.CellData`, `analyse` (which calls `decision_inputs`), `jsonable`, `jsonable_floats`, `clean_scorecard_source`, `cells_rows`, `pairs_rows`, `scorecard_rows`, `write_csv`. The copied `simulate_cell` keeps the frozen check that each `eval.json`'s `source_sha256` equals the current `src/arborlm` digest, and does not compare the spec hash.

**W3 — §4, replace the "Verification of frozen material instead" bullet with:**

> - **Verification of frozen material instead:** every file under `src/arborlm/`, `configs/p8_locality_training.toml`, `uv.lock`, `pyproject.toml` and the ten P8 test files of the freeze (`tests/conftest.py`, `tests/p8_dry.py`, `tests/p8_fake.py`, `tests/test_p8_analysis.py`, `tests/test_p8_core.py`, `tests/test_p8_eval.py`, `tests/test_p8_objective.py`, `tests/test_p8_panel.py`, `tests/test_p8_sim.py`, `tests/test_p8_train.py`) are compared file by file with the git blobs at pushed commit `378aeac` (tree `b13a9f9c09083a9b486adb9b691089f00409059f`; cited in older records as `80f46ae`), and `p8_core.source_digest()` must equal `8b5a03a08fc10a4ac29bdf9c6dd2d21945b9bb3aff459766b58304545d570507` (no extra `*.py` under `src/arborlm/`). ADR-0015 is not compared with the freeze; it is compared with its blob at `2d10338` (`add0a37659e228ba3f6e9a1cd414ec271d88c7c8`), whose only change from the freeze is the status line and §17, and the record says so. All 60 `eval.json` files of the evaluation run and the 55 registered `sim.json` files are verified against the blobs committed at pushed commit `b8302c2` (tree `290d15dedc5cdaf57ea8bbbe3097575b1d582d14`); trace `.bin` files are verified by `load_trace` against the `sha256` inside each `eval.json`.

**W4 — §4, append to the "Supplementary records carry their own identity" bullet:**

> `supplement_freeze_commit` is recorded together with its tree hash, because the single-line pre-push rewrite can change commit hashes; the tree hash is the identity.

**W5 — §5, replace the third bullet ("For the 55 registered cells …") with:**

> - The comparison is between `jsonable(analyse(...))` and the registered `analysis.json`, excluding `dry_run` and `inputs` (written by `run_analysis`, not by `analyse`). Keys allowed to differ: `study_status`, `cells_with_complete_records`, `missing_cells`, everything under `cases.C04` and `cases.C05`, `decision_inputs.section_8_option_indicated` and `decision_inputs.section_8_reason`. Every other key must be equal, including `concentration_controls_bind`, all other `decision_inputs` keys and the top-level `open_questions`. No other case references C04 or C05. CSVs are compared on their bodies below the supplementary header line: `cells.csv` may differ only by the rows of the five new cells; `pairs.csv` only by rows whose `case` is C04 or C05; `scorecard.csv` only in the C04 and C05 rows and in the `study_status` column of every row (the frozen `scorecard_rows` writes the study status into each row). Any other difference stops the supplement.

**W6 — §6 gate 4, replace the replay bullet and add three bullets:**

> - replay through the new wrappers with the registered null provider (precondition evaluated and false) on at least three registered cells, including the near-collapsed `b102-o302-s601-C04` (17 slots) and at least one tree cell (for example `b102-o302-s602-C05`): every field equals the registered `sim.json` except exactly `seconds`, `worker_seconds`, `peak_rss_bytes_ru_maxrss`, `source_sha256`, `spec_sha256`, `reproduction_record_sha256`, the added `supplement_*`/`frozen_inputs` fields, and the added `method` and `precondition` keys of each `panels.*.null_streams` entry; and the rebuilt `layouts.int16.bin` has the registered `layouts.file_sha256`;
> - for each of the five cells, the rebuilt layout file and hash table equal the `layouts.int16.bin` already in that cell's failed directory under `experiments/P8S-20261114T043952694180Z-088e6814edcd465894aebd125d53ddc3/cells/<label>/`;
> - checks that need local data (replay, layout equality, blob and trace verification) run as a recorded script whose output is kept under `results/p8-supplement-2026-11-14/`; a skipped test does not satisfy them;
> - the synthetic 60-cell run uses single-set C04/C05 cells (m = 0 everywhere) and completes without exception; precondition-detector tests also cover Q ≠ 32,768.

**W7 — §2, append to the numbered predictions:**

> 6. For every stream, layout, setting and tie rule: `misses_warm = first_touch_warm = 0` and `misses_all = first_touch_all` = the number of distinct pages.
> 7. The three null `stream_sha256` values of a panel are identical.
> 8. `concentration_controls_bind` is false and `open_questions` is `[C09]`, unchanged.
> 9. The supplementary mechanical decision letter is `c` (not a registered decision).

**W8 — §3, replace "and `stream_sha256` over that tensor in the registered packing." with:**

> and `stream_sha256 = sha256(p7a_core._pack(stream, "h"))` (little-endian int16, C order), identical for the three replicates by construction.

**W9 — header and §9.1:**

> - Line 3 → `- **Status: revision 2 — HUMAN-APPROVED for execution on 2026-11-14 (§9), including the §1.1 exception. Not yet executed. Auditor re-check: NOT READY pending wording changes W1–W9 (recorded in §9.1).**`
> - Line 5, replace "Revision 2 has not been re-reviewed." with "Revision 2 was re-checked by Opus 5.5: `docs/reviews/p8-supplement-spec-review-2026-11-14/RECHECK.md`."
> - §9.1: list W1–W9 with the date and state that they change no hypothesis, threshold, null rule, cell or prediction outcome.

## 5. Commands

All commands were run from the worktree root unless noted.

```
git diff --stat 378aeac HEAD -- src configs tests pyproject.toml uv.lock .github   # empty
git log -1 --format='%H %T' 378aeac; git log -1 --format='%H %T' b8302c2; git merge-base --is-ancestor <c> HEAD
git ls-tree -r --name-only b8302c2 -- results/p8-2026-11-14
uv run --locked python -I -c "from arborlm import p8_core; print(p8_core.source_digest()); print(p8_core.spec_sha256())"
sh docs/reviews/p8-supplement-spec-review-2026-11-14/recheck_import_probe.sh <worktree> <empty scratch dir> \
  > docs/reviews/p8-supplement-spec-review-2026-11-14/outputs/recheck_import_probe_run1.txt
uv run --locked ruff check .
```

The probe used the scratch directory `/private/tmp/claude-501/…/scratchpad/probe_run1`.

| File | sha256 |
|---|---|
| `recheck_import_probe.sh` | `57be1c8d…c44a` |
| `outputs/recheck_import_probe_run1.txt` | `d9f25a44…e21f` |

**Discrepancy in my own earlier probe, kept for the record.** An earlier ad hoc probe ran a full `ruff check` on the scratch mini-repo. It reported an import-order (I001) error in the copied `tests/conftest.py`. That is an artefact of the scratch location: ruff's first-party detection differs there. It is not a property of the repository. The recorded probe therefore checks E402 only.
