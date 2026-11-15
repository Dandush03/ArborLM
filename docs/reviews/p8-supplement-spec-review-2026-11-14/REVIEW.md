# ADR-0016 (proposed P8 supplement) — independent specification review

- Reviewer: **Claude Opus 5.5 (`claude-opus-5-5`)**, auditor role, per this session's own metadata. **Not Astra validation and not human approval.** Astra review: NOT_PERFORMED.
- Date: 2026-11-14 UTC. Worktree HEAD `d3aded5`; ADR-0016 is untracked (as given to me). Reviewed text: `docs/decisions/ADR-0016-p8-supplement-collapsed-cell-simulations.md` (96 lines).
- I edited no existing file, ran no training, evaluation or simulation of any P8 cell, and built no null for the five cells. I read the five cells' trace files (counts and row contents only). Everything else ran on synthetic data. I wrote files only in this folder.
- Environment: macOS 27.2.1 arm64, Python 3.12.14, torch 2.8.0, uv 0.12.15, `uv run --locked python -I …` from the worktree root. No `arborlm.*_analysis` module is imported by my scripts. `uv run --locked ruff check .` passes from the repo root (no `ruff.toml` was needed here).
- Conflict-of-interest note: I wrote the P8 results audit that ADR-0016 cites. This review checks the lead's new specification, not my audit.

## Verdict: **NOT READY** for human approval

The mathematics is sound. Both requested proofs hold (§A, §B). The predictions in §2 are correct in substance.

The execution and provenance design in §4–§6 cannot be carried out as written. Three things block it:

1. The frozen identity checks cannot pass on today's tree. ADR-0015 itself was edited after the freeze.
2. Placing new files in `src/arborlm/` changes the frozen source digest that the same section says will be verified.
3. The frozen analysis entry points accept a supplementary record only if that record carries source, spec and freeze values it was not produced under.

All of these can be fixed by rewording. None needs a new scientific choice, except the governance point in finding 5.

**Grade counts:** 1 BLOCKER, 5 MAJOR, 9 MINOR.

## A. Proof item 1 — uniqueness of the null under the precondition: **PROVED**

Setup:
- A panel trace has Q queries.
- Every row holds 8 distinct slot IDs. `p7a_core.check_trace` enforces this, and `p8_sim.load_trace` calls it (`src/arborlm/p7a_core.py:239-241`, `src/arborlm/p8_sim.py:303`).
- The trace has counts c. Let S = {i : cᵢ > 0}.
- Assume |S| = 8 and cᵢ = Q for every i ∈ S.

The claim: let N be any Q×8 stream in which every row holds 8 distinct slots and every slot's count equals cᵢ. These are the registered hard-stop conditions at `p7a_core.py:437-445`. Then every row of N equals S as a set.

Proof:
1. For j ∉ S the count is 0, so j occurs in no row of N. Every row is therefore a subset of S.
2. A row has 8 distinct elements and |S| = 8. A subset of S with 8 elements is S itself.

Consequences:
- **Row order.** All rows are equal, so the row order of N is immaterial. ADR-0013's step-4 query permutation therefore changes nothing.
- **What the registered greedy would have produced.** If the greedy had terminated on these traces, its output would have passed the same hard-stop checks. By the lemma it would then equal the identity null up to within-row order. So the identity null is not a substitute distribution. It is the registered null's only possible value, up to an order that §B shows no recorded quantity reads.
- **The registered greedy did succeed on two replicates.** My earlier replay shows it succeeding on replicates 1 and 2 of `b101-o301-s601-C04` Panel A (seeds 91331003 and 91332003): `docs/reviews/p8-results-audit-2026-11-14/outputs/null_failure_analysis_run1.json`. Under ADR-0016 those two replicates are replaced by the identity null. By the lemma and §B, they are equal in every quantity except the stream hash (finding 11).
- **What the proof needs.** It uses only "8 non-zero counts, each equal to Q" plus within-row distinctness. The third clause of the precondition ("every query's slot set equals S") is a consequence of these, not an extra assumption (finding 9).

## B. Proof item 2 — order invariance: **PROVED**

Only the stream hash depends on the order of slots within a row. Read on the frozen code at HEAD; `src/arborlm/` is byte-identical to the freeze tree `b13a9f9`.

In the P8 path, a null tensor is consumed in exactly two places, both inside `simulate_panel` (`p8_sim.py:274-282`).

1. **`simulate_trace` → `p7b_sim.page_sets` → `simulate_group`** (`p8_sim.py:176-179`).
   - `page_sets` maps each slot to its page and **sorts every row** (`.sort(dim=1)`), then drops duplicates (`p7b_sim.py:61-64`).
   - For any permutation σ of a row, the multiset of pages is unchanged, so the sorted, de-duplicated tuple is identical.
   - Everything downstream is a function of that list of tuples alone:
     - `stream_stats` (`p7b_sim.py:68-84`);
     - the `cache_counts` shortcut (`:177-185`);
     - `lru_pass`, including the `pages == previous` skip and the descending rule via `reversed_order` (`:94-164`);
     - `check_group`.
   - So `stats` and every `by_c` count are order-invariant. So is m (`p8_sim.py:196-203`), and with it null_mean, E and every analysis value read through `CellData.m`, `null_mean` and `e` (`p8_analysis.py:327-356`).
2. **`temporal_reuse`** (`p8_sim.py:207-231`).
   - `hits` counts, for each slot of row t, membership in the union of the previous rows. That is a sum over the elements of a set, so it is order-free.
   - `slots_per_query = len(rows[0]) = 8` is order-free.
   - So `value` is order-free, and so are `CellData.reuse` and `ratio_to_null` (`p8_analysis.py:358-367`).

Not consumers of the null:
- `evaluation_counts` (`p8_sim.py:181`) comes from the actual trace.
- `order_shuffled` (`:171`, `:280`) comes from the actual trace.
- `branch_persistence` (`:287-294`) comes from the actual branch trace.
- Layouts come from the calibration trace.
- The null tensor is never written to disk.

The only order-dependent recorded quantity is `stream_sha256`. It is `sha256(_pack(out, "h"))` at `p7a_core.py:455`, copied into the record at `p8_sim.py:283-285`. A repository-wide grep finds no consumer of `stream_sha256` in `p8_analysis.py`, in `results/p8-2026-11-14/report/*.py`, or in the auditor tools under `docs/reviews/p8-preflight-2026-11-14/`.

Empirical companion (synthetic only): `order_invariance_synthetic.py`.
- 18 random streams × layouts, comparing within-row-shuffled against original: simulation records and reuse are identical in 18/18, and the stream hash differs in 18/18.
- A synthetic single-set stream with rows in varying order against its ascending identity null: identical records, m = 0 at both settings and both tie rules, reuse = 1.0, in 5/5 layouts.
- Output: `outputs/order_invariance_synthetic_run2.json`.

**Is the generator's row order canonical? Is "ascending" defensible?**
- The registered rows have **no canonical within-row order**. They are slices of a shuffled occurrence list, modified by in-place swaps (`p7a_core.py:370-399`).
- The actual collapsed traces are not ascending either. In every one of the 15 traces (5 cells × calibration/A/B), 0 of 32,768 rows are ascending. Each trace has 203–748 distinct within-row orders, presumably score order. Output: `outputs/collapsed_trace_sets_run1.json`.
- So "ascending slot-ID order" is a defensible canonical choice. It creates no inconsistency in any simulated or analysed quantity of the 55 records.
- The only inconsistency is that the supplementary `stream_sha256` values are not comparable with the registered ones. That is harmless and must be disclosed (finding 11).

## C. Findings

### BLOCKER

**1. §4 and §5 rest on frozen identity checks that cannot pass. Satisfying them would require supplementary records to misstate their provenance.**

Evidence, from `freeze_feasibility.py` → `outputs/freeze_feasibility_run1.json`:

- **(a) ADR-0015 changed after the freeze, so frozen freeze verification now refuses.**
  - ADR-0015 was edited after the freeze: the status line and §17 were added in `2d10338`.
  - `core.spec_sha256()` now returns `d4bdd771…6cbf4`. Every P8 record carries `979274e9…fa40ba` (`p8_core.py:337-338`).
  - `p8_train.verify_freeze` therefore refuses today against both `378aeac` and `80f46ae`: "ADR-0015 … differs from the freeze commit" (`p8_train.py:88-96`).
  - So `p8_pool.require_freeze` (`p8_pool.py:47-61`) fails. That breaks `run_stage` (`p8_sim.py:431`) and `run_analysis` (`p8_analysis.py:1152`), even before any new file exists.
- **(b) New modules in `src/arborlm/` change the frozen source digest.**
  - `source_digest` hashes **every** `*.py` under `src/arborlm/` (`p8_core.py:324-334`).
  - On a scratch copy of `src/arborlm`, adding one empty `p8s_placeholder.py` changes the digest from `8b5a03a0…570507` to `e6ccfe12…13fb1`.
  - ADR-0016 line 51 asks for both "frozen source digest verified equal to the freeze value" and new `src/arborlm/p8s_*.py` files. The two are mutually exclusive.
- **(c) With (b) in place, the frozen simulation and analysis paths refuse.**
  - `simulate_cell` raises `StopError` because the eval record's source hash ≠ the current digest (`p8_sim.py:320-321`).
  - `check_reproduction_record` refuses (`p8_sim.py:410`).
  - `run_analysis` refuses (`p8_analysis.py:1160-1161`).
- **(d) `check_provenance` would force a misstatement.**
  - It requires one `source_sha256` and one `spec_sha256` across both manifests and all 120 records, and one freeze commit across both manifests (`p8_analysis.py:400-406`, `415-417`).
  - A supplementary sim record written by `worker_main` stamps whatever the current tree gives (`p8_sim.py:392-393`). Under (a) and (b) that is not the frozen value.
  - The only way to pass is for the supplement to write `8b5a03…`, `979274…` and freeze `80f46ae` into records and a manifest produced by different code, under a different specification and a different freeze. That misstates provenance.
  - `run_analysis` would also write an analysis manifest stamped with ADR-0015's spec hash and freeze (`p8_analysis.py:1183-1191`).

**Required change.** Replace §4's "imports the frozen functions" and §5's "frozen analysis functions called unchanged" with an explicit list. Recommended wording:

- **Frozen functions called unchanged** (none of them reads the source digest or the spec hash):
  - `p8_sim.load_trace`, `build_p8_layouts`, `layout_hashes`, `simulate_trace`, `temporal_reuse`, `branch_persistence`, `m_fraction`;
  - `p7b_layout.write_layout_file`, `verify_partitions`, `CalibrationTrace.declared`;
  - `p7a_core.selection_counts`, `query_order`, `frequency_matched_detail` (non-precondition path only);
  - `p8_analysis.load_cells(eval_run, assembled_sim_dir, dry_run=None)` (provenance skipped by the function's documented contract), `CellData`, `analyse`, `jsonable`, and the CSV row builders.
- **Frozen functions *not* called:**
  - `simulate_cell`, `simulate_panel`, `worker_main`, `run_stage`, `check_reproduction_record`;
  - `check_provenance`, `run_analysis`, `require_freeze`, `verify_freeze`.
  - Each is replaced by a named new function. The spec lists each new function's differences from the frozen one.
- **Frozen-file verification.** Replace "frozen source digest verified equal" with a per-file check: every file in the freeze tree's `src/arborlm` list (85 files; tree `b13a9f9c…`) has its frozen sha256, so the frozen-subset digest equals `8b5a03a0…570507`. The config, `uv.lock` and `pyproject.toml` equal the freeze. ADR-0015 is **not** compared with the freeze, because it changed legitimately in §17. Instead it is compared with a named post-outcome commit, and the change is disclosed. The only additional `src/arborlm` files are the declared `p8s_*.py`.
- **Supplementary identity fields.** Supplementary records and manifests carry their own fields, for example:
  - `supplement_source_sha256` (full current digest);
  - `supplement_spec_sha256` (ADR-0016);
  - `supplement_freeze_commit`;
  - `frozen_inputs: {source_sha256: 8b5a03…, spec_sha256: 979274…, freeze_commit: 378aeac (= 80f46ae)}`, labelled "inputs verified against", never as the producer.
  - `source_sha256` and `spec_sha256` are never written with a value the producing code did not compute.
- **Supplementary provenance check (new code).** It replaces `check_provenance` and verifies:
  - the 55 originals by hash (finding 4);
  - the 60 eval.json files by hash;
  - every supplementary record's `eval_json_sha256`;
  - one consistent supplementary identity across the 5 new records.

### MAJOR

**2. "Replaces only the null provider" (line 51) cannot be done without copying `simulate_panel`, and the `method` field (line 35) cannot be recorded by frozen code.**
- `simulate_panel` calls `b_core.null_streams` through the shared `p7b_core` module (`p8_sim.py:274`). Replacing it unchanged needs a monkeypatch of a module global used by P7-B too.
- The record keeps only three keys of each null's info (`p8_sim.py:283-285`), so `method` would be dropped.

Required change:
- Forbid monkeypatching.
- Specify a new `simulate_panel_s` that differs from `p8_sim.py:261-295` only in (i) the null provider and (ii) the recorded null keys, which add `method` and `precondition`.
- Add a test asserting that `simulate_panel_s` and the frozen `simulate_panel` give equal output on synthetic non-single-set panels.
- Correct §4's "the same … recorded fields" (line 50), because the null entry gains keys.

**3. The replay gate "reproduces a registered `sim.json` byte for byte" (line 70) is unsatisfiable, and as worded it does not test the supplement's own code path.**
- `sim.json` contains wall-clock and environment fields:
  - `seconds` (`p8_sim.py:372`);
  - `worker_seconds`, `peak_rss_bytes_ru_maxrss`, `determinism` (`:392-397`);
  - `source_sha256`, `spec_sha256`, `reproduction_record_sha256`.
- Wall-clock fields can never repeat, and the hash fields will differ (finding 1).

Required change:
- Define the compared subtree: `panels.*` without timing, `layouts` (including `file_sha256` and `hash_table`), `eval_json_sha256`, `calibration_files`, `settings`, `ties`, `cell`, `cell_index`, `variant`, `case`, `label`, `outcome`, `schema`.
- Require the replay to run **through the supplement's new wrappers** with the precondition evaluated and false.
- Require at least one replayed cell to be a near-collapsed concentration cell, for example `b102-o302-s601-C04` (17 distinct slots, max count 26,636) or `b102-o302-s602-C05` (16 slots, a tree). These are the cells closest to the precondition boundary. Also require one tree cell.

**4. "Verified by hash against the original manifest" (line 56) is impossible: the sim manifest holds no per-file hashes.**
- `P8S-…088e6814…/manifest.json` has the keys `cap_hit … workers`. Each `outcomes` entry has only label, status, returncode, seconds, peak_rss and reason.
- The same applies to the eval manifest, for the five `eval.json` files named as inputs in §4 (line 49).

Required change: name the reference.
- The git blobs of the committed copies under `results/p8-2026-11-14/simulate/P8S-…/cells/<label>/sim.json` and `…/evaluate/P8E-…/cells/<label>/eval.json`, at commit `b8302c2`.
- My audit found all 639 committed files byte-identical to the local run (`docs/reviews/p8-results-audit-2026-11-14/RESULTS_AUDIT.md` §5).
- Trace `.bin` files are checked against the `sha256` inside each `eval.json` (`traces.<name>.files.selected.sha256`).
- `load_cells` needs **one** sim directory holding 60 `cells/<label>/sim.json` (`p8_analysis.py:428-459`). The spec must define this assembled directory: copies plus 5 new records, with its own clearly supplementary manifest. It must not be presented as a P8 sim-stage run.

**5. Conflict with ADR-0015 §11 and the failed records; governance is not established.**
- ADR-0015 line 221: "No cell is rerun with a changed seed, dose or rule."
- `sim.failed.json`: "the cell is not re-run with changed parameters".
- In substance, ADR-0016 simulates exactly those cells again under a null rule written after the failure was observed. Calling it a "separate supplement" (line 7) is honest labelling. It does not remove the conflict.
- Per AGENTS.md line 40 ("If documents disagree, stop and request a recorded Astra/human decision"), the approval in §9 must explicitly name and except ADR-0015 §11 / §16.6 and the failed-record note.
- "Study-specific Claude workflow for this supplement only" (line 6) is a governance choice. The P8 workflow was authorized by the overnight direction for P8 only (ADR-0015 §15, line 261). It needs its own explicit human authorization, not inference from "start working on the missing simulation".
- The new single-set rule is a new scientific choice and, per AGENTS.md lines 9 and 14, should be marked `PENDING ASTRA REVIEW` in the status line.
- **PENDING LEAD REVIEW** for the wording. Whether to grant the exception is a human decision.

**6. The frozen `analyse` will write `study_status: "COMPLETE"` and `section_8_option_indicated: "c"`, and §5's header requirement cannot be met by frozen writers.**
- On 60 records, `analyse` sets `study_status = "COMPLETE"` and `missing_cells = []` (`p8_analysis.py:821-827`).
- `decision_option` then returns `"c"` (`:230-251`, `:948`).
- `run_analysis` writes `analysis.json` with no header (`:1176-1181`).

Required change:
- Specify a supplementary output envelope written by new code: for example `{"label": "SUPPLEMENTARY (ADR-0016) — not the registered P8 output", "registered_study_status": "INCOMPLETE", "registered_decision": "none", "supplementary_analyse_output": …}`.
- Do the same for the CSVs: a header row or a sidecar file.
- State in §2 and §8 that the embedded `study_status: "COMPLETE"` and `"c"` describe the assembled 60-record set only.

### MINOR

**7. §2 overstates two things.**
- Line 22, "E … undefined … as in every other regularized case": the **E-ratio** is undefined for every regularized case, but per-checkpoint E is defined for 5 of 6 C06 cells and 4 of 6 C07 cells (`RESULTS_AUDIT.md` §2.3). Say instead "as in every simulated C04/C05 cell (4/4 and 3/3 below the floor)".
- Line 23, "the decision reading '(c)' cannot change": the registered decision is `none`. (c) is a non-registered descriptive reading (`RESULTS_AUDIT.md` §4c, §7). Reword to "the registered decision stays `none`; the supplementary mechanical output is predicted to be (c)".

**8. §2's predictions are correct but should be exact, so they can serve as the test oracle.**

What I verified analytically, and on synthetic data in `outputs/order_invariance_synthetic_run2.json`:
- In all five cells, calibration, Panel A and Panel B share **the same** 8-slot set (`outputs/collapsed_trace_sets_run1.json`).
- Under any layout, the stream touches at most 8 distinct pages, and 8 is at most C at both settings. So `cache_counts` takes its shortcut (`p7b_sim.py:177-185`).
- Every query contains all of S, so `distinct_first_half = distinct_stream`.

Hence, for **every** stream (actual, order-shuffled, null 1–3), every layout, both settings and both tie rules:
- `misses_warm = first_touch_warm = 0`;
- `misses_all = first_touch_all = distinct pages`;
- `ctx_q` all zeros;
- m = 0;
- null records identical to the actual records under L-FREQ and L-COAX;
- order-shuffled records identical to the actual records.

Temporal reuse is exactly 1.0 for the actual, order-shuffled and each null stream: hits = 8 × 32,256. `null_mean = fsum([1.0, 1.0, 1.0]) / 3 = 1.0`, so `ratio_to_null = 1.0` exactly (`p8_analysis.py:358-367`). The prediction "exactly 1" is therefore correct.

Further predictions:
- The three null hashes are identical.
- C04 and C05 study class is QUALITY-FAILED, from evaluation data alone.
- `concentration_controls_bind = false`.
- `open_questions = [C09]`.

Add these as predictions and as the gate-3 end-to-end oracle.

**9. The precondition (line 33) is correct and not contradictory, but it is redundant.**
- Given `check_trace`'s within-row distinctness, clause 3 follows from clauses 1–2. Clause 2 follows from clause 1 together with Σc = 8Q and max c ≤ Q.
- Keeping all three as direct checks is fine. State that they are evaluated on the trace rows after `load_trace` (shape, range, distinctness, counts hash against eval.json), not on eval.json counts.

**10. The evidence that Panel B meets the precondition supports the claim.**
- All five cells: on Panel B, 8 distinct slots, each with count 32,768; 1 distinct query set; 32,768/32,768 rows distinct (`docs/reviews/p8-results-audit-2026-11-14/outputs/null_failure_analysis_run1.json`).
- Re-confirmed from the trace files in `outputs/collapsed_trace_sets_run1.json`.
- The §3 "otherwise call the registered generator" branch is therefore dead for these five cells on both panels. Say so, so that the replay gate (finding 3) is the only exercise of that branch.

**11. Stream-hash definition and disclosure.**
- State the hash exactly as the registered one: sha256 of the little-endian int16, C-order pack, as `p7a_core._pack(out, "h")`.
- State that the three replicate hashes are identical by construction.
- Disclose that the supplementary hashes are not comparable with registered hashes, because registered rows have no canonical order.
- Disclose that for `b101-o301-s601-C04` Panel A replicates 1–2 the registered greedy would have succeeded. The identity null replaces two obtainable streams that are equal in every simulated quantity.

**12. Gate order and missing gates (§6).**
- Gate 1 (human approval) precedes gate 2 (these proofs and this review). Put the review and proofs first, or make the approval explicitly conditional on them.
- Add these gates:
  - (i) For each of the five cells, the rebuilt `layouts.int16.bin` and its hash table equal the file already in the failed cell's directory (`experiments/P8S-…/cells/<label>/layouts.int16.bin`; written before the null failed). This is a free determinism check.
  - (ii) The frozen `analyse` runs on a **synthetic** 60-cell set in which the C04/C05 cells are single-set. The C04-vs-C01, C05-vs-C03, C05-vs-C04 and C04/C05 `controls` paths have never executed on real records, and m = 0 denominators occur there. `ratio` handles zero (`p8_analysis.py:261-269`), but the report generator did not (defect 9 of the results audit).
  - (iii) Whether ADR-0015 §10.7's P7-B reproduction gate is re-run on the supplement's code. I recommend it: it is cheap, and the wrappers change the code path.
  - (iv) Precondition-detector tests also cover Q ≠ 32,768, a set of 8 slots with one row differing, and a 7-slot impossible histogram (rejected by `check_trace`).

**13. Freeze-commit reference.**
- `80f46ae` is reachable only from the local branch `backup/p8-before-single-line-rewrite` and is not an ancestor of HEAD.
- The pushed equivalent is `378aeac`, with the same tree `b13a9f9c…` (`docs/reviews/p8-results-2026-11-14/COMMIT_MAP.md`).
- The spec should verify against the tree hash or `378aeac`, never against `80f46ae` alone.
- The supplement's own freeze commit should be recorded with its tree hash, because the pre-push single-line rewrite changes commit hashes.

**14. §5's "every value must equal the registered analysis" (line 59) needs an explicit list of keys that may differ.**
- Expected to differ: `study_status`, `cells_with_complete_records`, `missing_cells`, `decision_inputs.section_8_*`, everything under `cases.C04` and `cases.C05`, and the C04/C05 rows of `cells.csv`, `pairs.csv` and `scorecard.csv`.
- Must be byte-equal: everything else, including `concentration_controls_bind` (false) and `open_questions` ([C09]).

**15. Additions to §8 ("must not be claimed").**
- That (c) is the registered P8 decision. It stays `none`.
- That the `study_status: "COMPLETE"` inside the supplementary output describes the registered study.
- That the C04/C05 supplementary classes are registered classes.
- That the identity null carries locality information. With one set, E is undefined by construction.
- That the supplementary C04/C05 means supersede `analysis.json`. They sit beside it.
- That the supplement independently replicates anything. It reuses the same traces.

Separately, **PENDING LEAD REVIEW**: everything the supplement produces is analytically determined (finding 8), except layout-dependent page counts and the evaluation-only means, which need no simulation. A written analytic addendum would deliver most of the bookkeeping value with no new execution. Whether that is preferable is the lead's and the human's choice. I do not choose.

## D. Commands and files

All commands were run from the worktree root.

```
uv run --locked python -I docs/reviews/p8-supplement-spec-review-2026-11-14/order_invariance_synthetic.py \
  > docs/reviews/p8-supplement-spec-review-2026-11-14/outputs/order_invariance_synthetic_run2.json
uv run --locked python -I docs/reviews/p8-supplement-spec-review-2026-11-14/freeze_feasibility.py <scratchpad dir> \
  > docs/reviews/p8-supplement-spec-review-2026-11-14/outputs/freeze_feasibility_run1.json
uv run --locked python -I docs/reviews/p8-supplement-spec-review-2026-11-14/collapsed_trace_sets.py \
  /Users/daniellaloush/dandush03/ArborLM/experiments/P8E-20261114T043753008527Z-ab07648862054617b63d9e4d83e5407f \
  > docs/reviews/p8-supplement-spec-review-2026-11-14/outputs/collapsed_trace_sets_run1.json
uv run --locked ruff check .        # All checks passed!
```

Before writing `collapsed_trace_sets.py`, I ran the same trace read as an inline system `python3` command. The results were identical.

| File | sha256 |
|---|---|
| `order_invariance_synthetic.py` | `62ccd9bc…14f` |
| `freeze_feasibility.py` | `bc17dde1…b6d` |
| `collapsed_trace_sets.py` | `17784f01…b33` |
| `outputs/order_invariance_synthetic_run2.json` | `fad24aa0…43` |
| `outputs/freeze_feasibility_run1.json` | `27c017f3…f9` |
| `outputs/collapsed_trace_sets_run1.json` | `3e846b62…c8` |

Failed attempt (kept): `failed_attempts/order_invariance_attempt1_FAILED_auditor_used_numpy_not_installed.stderr`. My first version hashed via `tensor.numpy()`, and numpy is not in the locked environment. I replaced it with `array('h')`, and run 2 is the recorded output. The stderr files contain only torch's "Failed to initialize NumPy" warning.
