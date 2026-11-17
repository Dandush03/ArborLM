# ADR-0016 — P8 supplement: simulating the five fully collapsed cells

- **Status: HUMAN-APPROVED (§9), EXECUTED ONCE on 2026-11-14, COMPLETE (5/5 cells). Outcome in §10. The registered P8 study remains INCOMPLETE with decision `none`.**
- **Date:** 2026-11-14
- **Revision history.** Revision 1 was reviewed by Opus 5.5 and found NOT READY (1 blocker, 5 major, 9 minor): `docs/reviews/p8-supplement-spec-review-2026-11-14/REVIEW.md`. Revision 2 answers those findings. Revision 2 was re-checked by Opus 5.5: `docs/reviews/p8-supplement-spec-review-2026-11-14/RECHECK.md`.
- **Origin.** On 2026-11-14 the human lead wrote in chat: "start working on the missing simulation". The Claude lead reads that as direction to prepare this work. It is not recorded here as approval of this specification, of the exception in §1.1, or of the workflow.
- **Governance.** A study-specific Claude workflow for this supplement only, **which itself needs the human lead's authorization** (§9). ADR-0012 stays not approved. Astra review: NOT_PERFORMED. The null rule of §3 is **PENDING ASTRA REVIEW**.
- **Relation to ADR-0015.** ADR-0015 and every P8 record are unchanged. The registered P8 study remains **INCOMPLETE (55/60 simulated)** with decision **`none`**, permanently. Nothing this ADR produces is a registered P8 output.

## 1. Why a supplement is needed

Five P8 cells have no simulation record:

`b101-o301-s601-C04`, `b101-o301-s601-C05`, `b101-o301-s602-C04`, `b101-o301-s602-C05`, `b102-o302-s601-C05`.

In each, every one of the 32,768 queries selects the same eight slots, on the calibration trace and on both panels (review outputs `collapsed_trace_sets_run1.json`). The count-preserving null of ADR-0013 §14 item 8 exists for such a trace and is unique as a sequence of sets: it equals the trace. The registered greedy generator cannot construct it and raised an invariant error on Panel A. Panel B was never attempted.

### 1.1 This is an exception to ADR-0015, not something ADR-0015 permits

ADR-0015 §11 says no cell is rerun with a changed rule, and each `sim.failed.json` says "the cell is not re-run with changed parameters". Simulating these cells with a different null rule is exactly that. Labelling it a supplement is honest but does not remove the conflict. **The human approval in §9 must name this exception explicitly.** Without it, this ADR is not approved.

## 2. What is already known — this is not a blind test

Every simulation quantity for the five cells can be derived on paper; only the layout-dependent page counts need the layout code to run. The outcome is stated here so that it cannot be presented later as a finding.

- **Quality guard.** C04 and C05 fail all four guard conditions on both panels from the evaluation records alone. Rule 1 gives QUALITY-FAILED.
- **Simulation.** Eight slots occupy at most eight pages; the cache holds 32 pages at (R=2, C=32) and 8 at (R=8, C=8).
- **Scope of "E undefined".** At case level E is undefined for every regularized case in the registered analysis. Per cell it is defined in 5 of 6 C06 cells and 4 of 6 C07 cells; the claim here is about the five collapsed cells only.
- **Consequence.** No class of C06–C10 can change and no case can become LOCALITY-POSITIVE. The registered decision stays `none`.

**Exact predictions, fixed now, used as the test oracle:**

1. In all five cells, both panels, both settings, both tie rules, every layout: the counted (post-warm-up) miss count is exactly 0 for the actual stream.
2. The three null records and the order-shuffled record equal the actual record in every simulated quantity.
3. Temporal-reuse ratio to null is exactly 1.0.
4. E is undefined (null below 0.05) in all five cells.
5. Supplementary class of C04 and of C05 is QUALITY-FAILED on both panels.
6. For every stream, layout, setting and tie rule: `misses_warm = first_touch_warm = 0` and `misses_all = first_touch_all` = the number of distinct pages.
7. The three null `stream_sha256` values of a panel are identical.
8. `concentration_controls_bind` is false and `open_questions` is `[C09]`, unchanged.
9. The supplementary mechanical decision letter is `c` (not a registered decision).

Any other observation is reported as a discrepancy and investigated. Nothing is adjusted.

The value of the supplement is bookkeeping: a simulation record for 60 of 60 cells, and C04/C05 case means that are not selection-biased.

### 2.1 Alternative with no execution

Because the outcome is determined, the auditor notes that a written analytic addendum (the derivation above plus the all-six-cell evaluation-only means) would deliver most of this value without running anything and without the §1.1 exception. Choosing between that and this supplement is the human lead's decision (§9).

## 3. The single-set null rule

Let a panel trace have Q queries and selection counts c.

**Precondition (checked on the trace, per cell and per panel):** exactly 8 slots have a non-zero count and each of those counts equals Q. (That every query's set is then the same set S follows; the tool also checks it directly as a redundant assertion.)

**If the precondition holds:** each of the three null replicates is the stream of Q rows, every row being S in ascending slot-ID order. The record states `method: "single-set identity null (ADR-0016 §3)"`, the replicate seed and generator seed the registered rule would have used (recorded, not consumed), and `stream_sha256 = sha256(p7a_core._pack(stream, "h"))` (little-endian int16, C order), identical for the three replicates by construction.

**If the precondition does not hold on a panel:** the registered generator is called unchanged with the registered seeds; if it fails, the cell stays without a record and the supplement is reported incomplete. Existing records show all ten panel traces meet the precondition, so this branch is not expected to be taken.

**Proved by the auditor (review §§ proofs 1–2):**

1. Uniqueness: under the precondition every count-preserving stream has every row equal to S as a set.
2. Order invariance: the simulator sorts each row before use (`p7b_sim.py:63`) and temporal reuse tests set membership only; the sole recorded quantity that depends on within-row order is `stream_sha256`, which nothing downstream reads.

**Disclosures.**

- The registered generator emits rows in no canonical order, so supplementary stream hashes are not comparable with registered ones.
- For `b101-o301-s601-C04` Panel A the registered generator succeeded on replicates 1 and 2 and failed on 3. The supplement uses the identity null for all three; by proof 1 the streams are the same sequences of sets.
- The rule is not a general repair of the generator and applies to no other cell.

## 4. Scope and how the code is arranged

- **Cells:** exactly the five labels in §1.
- **Inputs:** evaluation run `P8E-20261114T043753008527Z-ab07648862054617b63d9e4d83e5407f` (eval.json and traces). No training, no evaluation, no new traces.
- **No frozen file is edited and none is added under `src/arborlm/`.** The frozen source digest covers every `*.py` under `src/arborlm/`; a new file there would change it. Supplement code lives in a new top-level package `supplements/p8s/` (with `supplements/__init__.py` and `supplements/p8s/__init__.py`) and is run from the repository root as `uv run --locked python -m supplements.p8s.<module>` (not with `-I`, which removes the repository root from `sys.path`). Tests live in `tests/test_p8s_*.py`; because `uv run --locked pytest` does not put the repository root on `sys.path`, each such file inserts it (`sys.path.insert(0, str(Path(__file__).resolve().parents[1]))`) before importing `supplements.p8s`. `pyproject.toml`, `uv.lock`, `tests/conftest.py` and the CI workflow are not changed. Type checking of the supplement uses `uv run --locked mypy src/arborlm supplements/p8s`.
- **Frozen functions called unchanged** (none reads the source digest, the spec hash or the freeze): `p8_sim.load_trace`, `build_p8_layouts`, `layout_hashes`, `simulate_trace`, `temporal_reuse`, `branch_persistence`, `m_fraction`; `p7b_layout.write_layout_file`, `verify_partitions`, `CalibrationTrace.declared`; `p7a_core.selection_counts`, `query_order`, `fm_generator_seed`, `_pack`, and `frequency_matched_detail` via `p7b_core.null_streams` (precondition-false branch only); `p8_analysis.CellData`, `analyse` (which calls `decision_inputs`), `jsonable`, `jsonable_floats`, `clean_scorecard_source`, `cells_rows`, `pairs_rows`, `scorecard_rows`, `write_csv`. The copied `simulate_cell` keeps the frozen check that each `eval.json`'s `source_sha256` equals the current `src/arborlm` digest, and does not compare the spec hash.
- **Replaced by new supplement code (copied, not patched):** `simulate_panel` and `simulate_cell` wrappers that take a null provider and keep the `method` field; the stage runner; the record loader and provenance check; the output writers. **No monkeypatching of any frozen module.** A test shows the copied wrappers with the registered null provider reproduce registered records (§6).
- **Not called:** `verify_freeze`, `load_cells`, `check_provenance`, `run_analysis`. They cannot pass honestly: ADR-0015 was edited after the freeze to add its outcome record, and supplementary records were not produced under the P8 freeze.
- **Verification of frozen material instead:** every file under `src/arborlm/`, `configs/p8_locality_training.toml`, `uv.lock`, `pyproject.toml` and the ten P8 test files of the freeze (`tests/conftest.py`, `tests/p8_dry.py`, `tests/p8_fake.py`, `tests/test_p8_analysis.py`, `tests/test_p8_core.py`, `tests/test_p8_eval.py`, `tests/test_p8_objective.py`, `tests/test_p8_panel.py`, `tests/test_p8_sim.py`, `tests/test_p8_train.py`) are compared file by file with the git blobs at pushed commit `378aeac` (tree `b13a9f9c09083a9b486adb9b691089f00409059f`; cited in older records as `80f46ae`), and `p8_core.source_digest()` must equal `8b5a03a08fc10a4ac29bdf9c6dd2d21945b9bb3aff459766b58304545d570507` (no extra `*.py` under `src/arborlm/`). ADR-0015 is not compared with the freeze; it is compared with its blob at `2d10338` (`add0a37659e228ba3f6e9a1cd414ec271d88c7c8`), whose only change from the freeze is the status line and §17, and the record says so. All 60 `eval.json` files of the evaluation run and the 55 registered `sim.json` files are verified against the blobs committed at pushed commit `b8302c2` (tree `290d15dedc5cdaf57ea8bbbe3097575b1d582d14`); trace `.bin` files are verified by `load_trace` against the `sha256` inside each `eval.json`.
- **Supplementary records carry their own identity:** `supplement_spec_sha256` (this ADR), `supplement_source_sha256` (files under `supplements/p8s/`), `supplement_freeze_commit`, and the frozen source digest they ran against. They never state the P8 freeze commit or spec hash as their own. `supplement_freeze_commit` is recorded together with its tree hash, because the single-line pre-push rewrite can change commit hashes; the tree hash is the identity.
- **P7-B reproduction gate:** not re-run. The registered reproduction record is cited by hash; the page simulator files are verified identical by the blob comparison.
- **Outputs:** `experiments/P8SUP-<utc>-<id>/` and `results/p8-supplement-2026-11-14/`. The original `sim.failed.json` files and `results/p8-2026-11-14/` are untouched.

## 5. Supplementary analysis

- The frozen `analyse` is called on 60 `CellData` objects: 55 from the registered records and five from the supplement.
- The frozen function will write `study_status: "COMPLETE"` and a decision-map letter. New writer code nests its whole result under `supplementary_analysis` inside a file whose top level states: `label: "SUPPLEMENTARY (ADR-0016) — not the registered P8 output"`, `registered_study_status: "INCOMPLETE"`, `registered_decision: "none"`, and a note that the nested status and decision describe the 60-record supplementary input only. CSV and Markdown outputs carry the same header line.
- The comparison is between `jsonable(analyse(...))` and the registered `analysis.json`, excluding `dry_run` and `inputs` (written by `run_analysis`, not by `analyse`). Keys allowed to differ: `study_status`, `cells_with_complete_records`, `missing_cells`, everything under `cases.C04` and `cases.C05`, `decision_inputs.section_8_option_indicated` and `decision_inputs.section_8_reason`. Every other key must be equal, including `concentration_controls_bind`, all other `decision_inputs` keys and the top-level `open_questions`. No other case references C04 or C05. CSVs are compared on their bodies below the supplementary header line: `cells.csv` may differ only by the rows of the five new cells; `pairs.csv` only by rows whose `case` is C04 or C05; `scorecard.csv` only in the C04 and C05 rows and in the `study_status` column of every row (the frozen `scorecard_rows` writes the study status into each row). Any other difference stops the supplement.
- The nested decision-map output is reported as produced. It authorizes nothing.

## 6. Gates, in order

1. Auditor proofs of §3 — done (revision 1 review).
2. Auditor re-check of revision 2.
3. Human approval recorded in §9, naming the §1.1 exception and authorizing the workflow.
4. Implementation (Sonnet), with tests:
   - precondition detector: single set; one query differing; nine slots; unequal counts; eight slots with one count below Q; wrong total;
   - the identity null passes the registered count and distinctness checks;
   - a synthetic single-set cell simulates end to end and meets predictions 1–3;
   - replay through the new wrappers with the registered null provider (precondition evaluated and false) on at least three registered cells, including the near-collapsed `b102-o302-s601-C04` (17 slots) and at least one tree cell (for example `b102-o302-s602-C05`): every field equals the registered `sim.json` except exactly `seconds`, `worker_seconds`, `peak_rss_bytes_ru_maxrss`, `source_sha256`, `spec_sha256`, `reproduction_record_sha256`, the added `supplement_*`/`frozen_inputs` fields, and the added `method` and `precondition` keys of each `panels.*.null_streams` entry; and the rebuilt `layouts.int16.bin` has the registered `layouts.file_sha256`;
   - for each of the five cells, the rebuilt layout file and hash table equal the `layouts.int16.bin` already in that cell's failed directory under `experiments/P8S-20261114T043952694180Z-088e6814edcd465894aebd125d53ddc3/cells/<label>/`;
   - checks that need local data (replay, layout equality, blob and trace verification) run as a recorded script whose output is kept under `results/p8-supplement-2026-11-14/`; a skipped test does not satisfy them;
   - the synthetic 60-cell run uses single-set C04/C05 cells (m = 0 everywhere) and completes without exception; precondition-detector tests also cover Q ≠ 32,768.
   - a synthetic 60-cell run of the supplementary analysis and writers, checking the labels of §5;
   - frozen-file blob comparison passes; frozen source digest unchanged with the supplement code present; ruff, mypy and the full test suite pass.
5. Auditor review of the implementation. Any blocker stops.
6. Freeze commit of the supplement code.
7. One execution. A failure is kept as a failed record and is not re-run with changed parameters.
8. Supplementary analysis; then independent recomputation by the auditor from raw records, including a check of predictions 1–5.

## 7. Limits

- One worker; at most 2 GiB RSS; at most 30 minutes wall time for execution and analysis together.
- No training, no downloads, no paid services, no SSD work, no change to `uv.lock` or `pyproject.toml`.
- No merge of any pull request and no publication.

## 8. What must not be claimed

- That the registered P8 study is complete, or that its decision is (c). It is INCOMPLETE with decision `none`.
- That `study_status: "COMPLETE"` inside the supplementary output describes the registered study.
- That the supplementary C04/C05 classes are registered classes, or that the supplementary means supersede `analysis.json`. They sit beside it.
- That the supplement tested or independently replicated anything. It reuses the same traces and its outcome was predicted in §2.
- That the identity null carries locality information. With one set, E is undefined by construction.
- That the null generator is repaired in general.
- Any positive result for locality-aware training.

## 9. Approval record

Required: (a) supplement execution or the no-execution addendum of §2.1; (b) if execution, acceptance of the §1.1 exception to ADR-0015 §11; (c) authorization of the Claude workflow for this supplement.

**Human lead, in chat, 2026-11-14 (verbatim), after being shown both options and the exception:**

> got it, now I understand let's run the 5 simulation as a supplements and by this im accepting the exception
>
> ones you done push all the result to the same PR

Reading by the Claude lead: (a) execution; (b) the exception is accepted in the human lead's own words; (c) is not stated separately and is read as given by the instruction to run the supplement in this session. The instruction also authorizes pushing the results to draft PR #5. It does not authorize merging, and it approves revision 2 as shown; changes required by the auditor's re-check are listed in §9.1 and limited to answering findings.

### 9.1 Changes after approval

2026-11-14: the auditor's wording changes W1–W9 (`RECHECK.md` §4) were applied verbatim: W1 code location, test import line, runner and mypy command; W2 the list of frozen functions called unchanged; W3 the file, eval-record and sim-record verification; W4 freeze tree hash; W5 the keys and CSV rows allowed to differ; W6 gate-4 tests; W7 predictions 6–9; W8 the stream-hash definition; W9 status and revision lines. They change no hypothesis, threshold, null rule, cell or prediction outcome.

**Two points the auditor referred to the human lead, not separately confirmed.** (1) Authorization of the Claude workflow for this supplement is inferred from the instruction to run it, not stated in the human lead's words. (2) W1–W9 were applied after the approval without re-approval, on the lead's judgment that they only answer audit findings. The lead proceeded on both; the human lead can object to either, and the objection would be recorded here.

## 10. Outcome record

Added after execution. Adding this section and changing the status line change this file's hash; the run records cite the hash at the freeze, `22d25195…4458` (file as committed at `3018126`). No other line was changed.

- **Freeze:** commit `3018126db5f8bed740813bc6722fe2319e31024c`, tree `671c184a19f183812588c5da491fa6733a1c88a3`; supplement code digest `88b86f48…5377`; frozen P8 source digest `8b5a03a0…0507`, unchanged.
- **Reviews before the run (Opus 5.5):** specification review (NOT READY), re-check (ready once W1–W9 applied), implementation audit (NOT READY: one major, the missing P7-B citation), re-check after fixes (READY TO FREEZE). Implementation by Sonnet 5.5; 874 tests passing.
- **Run, once:** `P8SUP-20261114T144104227089Z-fbfb3d18513749b081f9cdd93f22ad81`; 5 of 5 cells completed; 11.2 s; peak worker RSS 242 MB; one worker. Analysis `P8SUPA-20261114T144120084661Z-f008b8673e97484fa528ccf36beba4e9`, 0.31 s. No failed attempt and no re-run.
- **Precondition:** held on all ten panel traces; the registered generator was not called.
- **Predictions 1–9 of §2:** all hold. Every counted miss is 0; null and order-shuffled simulation records equal the actual; temporal-reuse ratio to null is 1.0; E is undefined in all five cells.
- **Supplementary classes (not registered classes):** C04 QUALITY-FAILED and C05 QUALITY-FAILED on both panels. On all six cells each, both cases fail all four guard conditions (ΔNLL +0.0100 to +0.0117; gain retention 0.48–0.56).
- **Comparison with the registered analysis:** differences only where §5 allows; all values for C01–C03, C06–C10 and the 55 registered cells are equal. Nested supplementary status `COMPLETE` and mechanical letter `c` describe the 60-record input only.
- **All-six-cell means versus the registered partial means:** the partial means understated the collapse, as flagged earlier. Panel A distinct slots: C04 22.75 → 17.83, C05 31.0 → 19.5; memory gain: C04 0.0154 → 0.0131, C05 0.0139 → 0.0108. The registered files are unchanged; the supplementary values sit beside them.
- **Independent recomputation (Opus 5.5):** 5,934 simulation values re-derived from raw traces with separate code, 1,548 analysis values, 128 case means: zero differences. `docs/reviews/p8-supplement-results-audit-2026-11-14/RESULTS_AUDIT.md`.
- **Defects and notes, none blocking:** the tool prints `decision_inputs` as a whole among the differences seen, although only its two allowed keys differ; the 30-minute limit was enforced on the stage and only recorded for the analysis; the run-once guard checks one experiments root; the P7-B reproduction record cited by hash exists as a file only outside the repository (an older P8 preservation question); the implementer's first full test run showed ten failures in `tests/test_p7b_study.py` that did not reproduce and whose log was not kept; the two points in §9.1 remain inferred, not confirmed.
- **What this does not change:** the registered P8 study is INCOMPLETE (55/60) with decision `none`. No case is LOCALITY-POSITIVE. The supplement tested and replicated nothing; its outcome was predicted. The null generator is not repaired in general. Astra review: NOT_PERFORMED. The single-set null rule is PENDING ASTRA REVIEW.
