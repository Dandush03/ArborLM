# ADR-0016 — P8 supplement: simulating the five fully collapsed cells

- **Status: PROPOSED (revision 2) — not approved. No implementation or execution before a recorded human approval of this text.**
- **Date:** 2026-11-14
- **Revision history.** Revision 1 was reviewed by Opus 5.5 and found NOT READY (1 blocker, 5 major, 9 minor): `docs/reviews/p8-supplement-spec-review-2026-11-14/REVIEW.md`. Revision 2 answers those findings. Revision 2 has not been re-reviewed.
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

Any other observation is reported as a discrepancy and investigated. Nothing is adjusted.

The value of the supplement is bookkeeping: a simulation record for 60 of 60 cells, and C04/C05 case means that are not selection-biased.

### 2.1 Alternative with no execution

Because the outcome is determined, the auditor notes that a written analytic addendum (the derivation above plus the all-six-cell evaluation-only means) would deliver most of this value without running anything and without the §1.1 exception. Choosing between that and this supplement is the human lead's decision (§9).

## 3. The single-set null rule

Let a panel trace have Q queries and selection counts c.

**Precondition (checked on the trace, per cell and per panel):** exactly 8 slots have a non-zero count and each of those counts equals Q. (That every query's set is then the same set S follows; the tool also checks it directly as a redundant assertion.)

**If the precondition holds:** each of the three null replicates is the stream of Q rows, every row being S in ascending slot-ID order. The record states `method: "single-set identity null (ADR-0016 §3)"`, the replicate seed and generator seed the registered rule would have used (recorded, not consumed), and `stream_sha256` over that tensor in the registered packing.

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
- **No frozen file is edited and none is added under `src/arborlm/`.** The frozen source digest covers every `*.py` under `src/arborlm/`; a new file there would change it and make the frozen `simulate_cell` refuse. Supplement code therefore lives in a new top-level directory `supplements/p8s/`, with tests in `tests/test_p8s_*.py`.
- **Frozen functions called unchanged:** layout construction and layout file writing, `simulate_trace`, `temporal_reuse`, `branch_persistence`, `load_trace`, trace and count helpers, and the pure analysis functions (`CellData`, `analyse`, `decision_inputs`, the row builders).
- **Replaced by new supplement code (copied, not patched):** `simulate_panel` and `simulate_cell` wrappers that take a null provider and keep the `method` field; the stage runner; the record loader and provenance check; the output writers. **No monkeypatching of any frozen module.** A test shows the copied wrappers with the registered null provider reproduce registered records (§6).
- **Not called:** `verify_freeze`, `load_cells`, `check_provenance`, `run_analysis`. They cannot pass honestly: ADR-0015 was edited after the freeze to add its outcome record, and supplementary records were not produced under the P8 freeze.
- **Verification of frozen material instead:** every file under `src/arborlm/`, `configs/p8_locality_training.toml` and the P8 tests is compared file by file with the git blobs at pushed commit `378aeac` (tree `b13a9f9`; cited in older records as `80f46ae`). ADR-0015 is exempt and its post-freeze change is stated in the record. The 55 registered `sim.json` files are verified against the blobs committed at `b8302c2`.
- **Supplementary records carry their own identity:** `supplement_spec_sha256` (this ADR), `supplement_source_sha256` (files under `supplements/p8s/`), `supplement_freeze_commit`, and the frozen source digest they ran against. They never state the P8 freeze commit or spec hash as their own.
- **P7-B reproduction gate:** not re-run. The registered reproduction record is cited by hash; the page simulator files are verified identical by the blob comparison.
- **Outputs:** `experiments/P8SUP-<utc>-<id>/` and `results/p8-supplement-2026-11-14/`. The original `sim.failed.json` files and `results/p8-2026-11-14/` are untouched.

## 5. Supplementary analysis

- The frozen `analyse` is called on 60 `CellData` objects: 55 from the registered records and five from the supplement.
- The frozen function will write `study_status: "COMPLETE"` and a decision-map letter. New writer code nests its whole result under `supplementary_analysis` inside a file whose top level states: `label: "SUPPLEMENTARY (ADR-0016) — not the registered P8 output"`, `registered_study_status: "INCOMPLETE"`, `registered_decision: "none"`, and a note that the nested status and decision describe the 60-record supplementary input only. CSV and Markdown outputs carry the same header line.
- For the 55 registered cells every per-cell value, and for C01–C03 and C06–C10 every case-level value, must equal the registered analysis exactly. The keys that may differ are limited to: C04 and C05 case entries, the missing-cell list, the study status, the control-binding entries that depend on C04/C05, and the decision inputs derived from them. Any other difference stops the supplement.
- The nested decision-map output is reported as produced. It authorizes nothing.

## 6. Gates, in order

1. Auditor proofs of §3 — done (revision 1 review).
2. Auditor re-check of revision 2.
3. Human approval recorded in §9, naming the §1.1 exception and authorizing the workflow.
4. Implementation (Sonnet), with tests:
   - precondition detector: single set; one query differing; nine slots; unequal counts; eight slots with one count below Q; wrong total;
   - the identity null passes the registered count and distinctness checks;
   - a synthetic single-set cell simulates end to end and meets predictions 1–3;
   - replay through the new wrappers with the registered null provider on at least three registered cells, including the near-collapsed `b102-o302-s601-C04` (17 slots): all fields equal the registered `sim.json` except a named list of timing, memory, timestamp and path fields, and the layout file is byte-identical to the registered `layouts.int16.bin`;
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

None. Pending. An approval must state, in the human lead's words: (a) supplement execution or the no-execution addendum of §2.1; (b) if execution, acceptance of the §1.1 exception to ADR-0015 §11; (c) authorization of the Claude workflow for this supplement.

## 10. Outcome record

None. Not executed.
