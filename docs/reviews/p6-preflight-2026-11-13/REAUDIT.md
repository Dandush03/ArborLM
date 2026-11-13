# P6-E / P6-Q pre-freeze re-audit (after fixes)

- Date: 2026-11-13. Auditor: Claude Opus 5.5 (`claude-opus-5-5`), auditor role.
- Status: independent engineering and mathematical evidence only. **Not Astra validation and not human approval.** Astra review: NOT_PERFORMED.
- Scope: the fixes for `AUDIT.md` (same folder) as decided in ADR-0011 §7, clarifications 15–27. I read all of clarifications 6–27, and I re-read every changed file in full.
- Binding specification: ADR-0011 working tree, SHA-256 `f292f0e332276af5c2471b4812d3f2c44e7698a14a22a48b7e92776a4d12c66f`. HEAD `981ce729261f8a606c635a7d785bdb840d5e4c2a`; the P6 files are untracked.

## Files audited (SHA-256; identical at the start and at the end of this re-audit)

| File | SHA-256 | vs AUDIT.md |
|---|---|---|
| src/arborlm/p6_analysis.py | b053f41fe0be5d808327d23f8411f8303a3dd3014cf0b6569db2f61cdf4cf546 | changed |
| src/arborlm/p6_common.py | 9919f2e5890e9a7ce32e0e9b2b8ce2df775a7c356db35f0daa0d54a40dc6a5a3 | changed |
| src/arborlm/p6_equivalence.py | 73815909d5a470246bf789084bc722d0bbb92a18c718754176582dddeb3febe6 | changed |
| src/arborlm/p6_fidelity.py | 7e0e4a3b7af9b5e6406912f1e368f7b77fdb91a41ae308202fedcd47287d3f71 | changed |
| src/arborlm/p6_fidelity_analysis.py | b99920a47ccd93f81f474abb297d9e80b208940837ed675a1c7157b908fce401 | changed |
| src/arborlm/p6_fidelity_reference.py (auditor-written; not self-audited) | a4e713608b8622f646011df88e5931ff92b1d612f0ea9711dab74f1a25156373 | **identical** |
| src/arborlm/p6_fidelity_study.py | e210c550a61cc29a23d5ba303c9c0406c3ab7543b19e4c6efade853edf72fd1c | changed |
| src/arborlm/p6_retrieval.py | aa70eefd804a0581de2c43905361a272f48a7ce27ca9b3e1f88d917ecd5c3f34 | **identical** |
| src/arborlm/p6_retrieval_study.py | 280b0669d9737df1e8347289885c7bd6e1600d783b68cb9a565c927b43dfa93f | changed |
| src/arborlm/p6_stage.py | 43bcbb84e7a2b7ee5ccadb259027881b5ee89d0c7b8f4485f2e2ed32cd172d2d | changed |
| src/arborlm/p6_timing_study.py | 3ba8449e73cab3b747cfb77bbf661181d569ea2a4cb2298841fc32f58450b184 | changed |
| tests/test_p6_fidelity.py | d58af9b2d49eb40804c89d581b07bbbade9e3813f6f3c2513f9d65fb8bb77b89 | changed |
| tests/test_p6_fidelity_reference.py (auditor-written) | 5c68383d8a1001c2f28e174127b23189962b7951bdba6416cae2c74035bd6436 | identical |
| tests/test_p6_retrieval.py | f5a91446da3e284cc877ae34e3acc0c172b4c34a195561c758753f152f5b4b86 | changed |

## Environment and commands

macOS-27.2.1-arm64, Python 3.12.14, torch 2.8.0, `uv.lock` unchanged. All commands were run from the repository root.

```sh
uv run --locked pytest -q tests/test_p6_retrieval.py tests/test_p6_fidelity.py tests/test_p6_fidelity_reference.py -p no:cacheprovider
#   207 passed, 1 warning (NumPy not installed) in 60.68 s
uv run --locked ruff check src/arborlm/p6_*.py tests/test_p6_*.py     # All checks passed!
uv run --locked ruff format --check src/arborlm/p6_*.py tests/test_p6_*.py
#   "Would reformat: tests/test_p6_fidelity_reference.py" (my own file; NOTE 1)
uv run --locked mypy src/arborlm                                       # no issues found in 58 source files
# Earlier checks, re-run (old outputs kept; new outputs have a -recheck suffix):
uv run --locked python docs/reviews/p6-preflight-2026-11-13/checks/check_p6e_variants.py      > checks/check_p6e_variants-recheck.out.txt
uv run --locked python docs/reviews/p6-preflight-2026-11-13/checks/check_p6q_numerics.py      > checks/check_p6q_numerics-recheck.out.txt
uv run --locked python docs/reviews/p6-preflight-2026-11-13/checks/check_p6q_budget.py        > checks/check_p6q_budget-recheck.out.txt
uv run --locked python docs/reviews/p6-preflight-2026-11-13/checks/check_p6q_partial_analysis.py <scratch> > checks/check_p6q_partial_analysis-recheck.out.txt
uv run --locked python docs/reviews/p6-preflight-2026-11-13/checks/check_p6e_budget.py <scratch> {eq|screen|confirm}
#   -> checks/check_p6e_budget-recheck.FAILED-attempt1.out.txt (see below)
uv run --locked python docs/reviews/p6-preflight-2026-11-13/checks/check_p6e_budget_recheck.py <scratch> {screen|confirm}  (+ eq phase of the old script)
#   -> checks/check_p6e_budget_recheck.out.txt
# New re-audit checks:
uv run --locked python docs/reviews/p6-preflight-2026-11-13/checks/check_reaudit_width_and_fixtures.py {1|0}   # 1 thread, then default (6)
uv run --locked python docs/reviews/p6-preflight-2026-11-13/checks/check_reaudit_p6q_analysis.py <scratch>
uv run --locked python -m arborlm.p6_retrieval_study dry-run --output-root <scratch>/out --results-root <scratch>/res --pair-count 2 --rounds 1 --panel-rows 16
#   all four stages completed (scratch only; not evidence)
uv run --locked python docs/reviews/p6-preflight-2026-11-13/checks/check_reaudit_p6e_chain.py <scratch>/res <scratch2>
uv run --locked python docs/reviews/p6-preflight-2026-11-13/checks/check_reaudit_p6e_failed_confirm.py <copy of scratch res> <scratch3>
# Inline check (described in the paragraph below):
#   concentration_report fields per rule -> checks/check_reaudit_concentration_fields.out.txt
```

The inline concentration check builds a `RetrievalCounts` for 64 random queries under each rule, using `tree_candidates` on random keys and router (seed 3), and prints selected fields of `p6_fidelity.concentration_report(tracker, rule=rule)`.

Data used: random synthetic tensors and the synthetic dry-run fixture only. No real checkpoint, real panel or real training row was loaded. No study stage or `loader-smoke` was run against the real roots. Scratch output went to the session scratch folder. Reading P5 compact `result.json` key names (no values used) was the only contact with `results/`. `find experiments results -iname '*p6*'` returns nothing.

**Failed checker attempt (kept):** `checks/check_p6e_budget-recheck.FAILED-attempt1.out.txt`. My old budget script called `timing_worker` without `spec["source"]`, which timing workers now require for the worker-end source check, so screen and confirm failed with `KeyError: 'source'`. This was my script's gap, not a code defect. Attempt 2 is `check_p6e_budget_recheck.py`, which supplies the source expectations and uses a 512-row synthetic panel so that the new per-worker replay cost is included.

## Status of prior findings

| ID | Status | Evidence |
|---|---|---|
| **B1** | **FIXED** | (a) `p6_fidelity_analysis.py:296-355`: flags are computed only when all 54 finals completed (`finals_complete`, :327); otherwise every flag is `{"status": "INCOMPLETE", ...}` (:342-349) and no exception is raised. (b) `initial_tables` :206-228 covers 0–27 step-0 records, and unexecuted or failed labels are listed with their reasons (:274-293, :318-322). (c) `p6_fidelity_study.py:702-715` lists a folder without `result.json` as `no_result_json`. (d) :586-606: no item starts with less than 60 s remaining; such an item is `unexecuted` with reason `budget` plus a `budget_exhausted_before_start` event. (e) Distinct terminal status `completed_finals_step0_partial` (:72-74, :593, :678-679). Tests: `test_p6_fidelity.py:628,661,804,845,978,1033`. My demonstration: `check_p6q_partial_analysis-recheck.out.txt` now completes both cases. `check_reaudit_p6q_analysis.out.txt` covers 7 cases: every case with a missing, failed or killed final is INCOMPLETE; where flags are computed, my own independent Fraction arithmetic agrees with all 16 flag outcomes. A flag is never PASS/FAIL from fewer than 27 finals of its kind. |
| **M1** | **FIXED as decided** (residual margin: MINOR 5) | `p6_fidelity.py:668-729`: the visit-k selection is `stable_top(scores[:, :256k], 8, ids[:, :256k])` on the captured X16P scores. The first batch is cross-checked against `tree_candidates(visit=k, use_prior=True)` for all 7 widths, and a mismatch raises a `width` GateViolation. :784-789 requires the check to have run and width-2 to equal T2P. Exactness: see Regression (a). Measured saving (`check_p6q_budget-recheck.out.txt`): 26.5 → 23.0 s per synthetic checkpoint. The X16P phase grew 9.4 → 12.1 s because the six selections now run inside it. **Discrepancy with my own AUDIT.md estimate:** I predicted about 6 s saved; the measured saving is about 3.5 s (about 190 s over 54 finals). |
| **M2** | **FIXED** | Rerun guard `p6_stage.py:118-159`, applied at :174 and recorded in the manifest at :197. The explicit-ID dry-run check is at :345-352. Linkage is `p6_retrieval_study.py:198-246`, called at :160-168. Confirm checks screen↔equivalence and selection hash (`p6_timing_study.py:461-471`). `check_reaudit_p6e_chain.out.txt`: the registered order is never blocked; every second run without a valid `--supersede`+reason is refused; a superseding screen paired with the old confirm fails linkage; a dry-run record is refused as registered input. |
| MINOR 1 (tie rule gates c) | FIXED | `p6_equivalence.py:63-64` (variant tie-rule violation on c → NOT_EQUIVALENT); fixture integrity stop :534-550; reference-tie-rule stop in all scopes :553-560; both called at :644-645. Spurious-stop risk: see Regression (c). |
| MINOR 2 (missing scope) | FIXED | `p6_equivalence.py:723-730`; test `test_p6_retrieval.py:858`. |
| MINOR 3 (replay in timing workers) | FIXED (clarification 19) | `p6_timing_study.py:279-288`, recorded at :423. See Regression (d). |
| MINOR 4 (archive recheck at worker end) | FIXED | `p6_stage.py:59-71`; timing worker :394, equivalence worker `p6_equivalence.py:777`. Operational consequence: MINOR 3 below. |
| MINOR 5 (`.data` fingerprint limit) | FIXED (disclosed) | `p6_common.py:32-40` `KNOWN_LIMITS`, copied into every stage manifest (`p6_stage.py:198`) and worker record (`p6_timing_study.py:425`, `p6_equivalence.py:791`); clarification 23. |
| MINOR 6 (nearest-rank p50) | FIXED | `p6_analysis.py:64-71`; indices `ceil(n·p)` give 8, 40, 72, 76 for n = 80, exact in float. Ratios still use `median_ns`. |
| MINOR 7 (X16/T2N concentration labels) | FIXED | `p6_fidelity.py:75-82`, :445-465. `check_reaudit_concentration_fields.out.txt`: T2P keeps the P5 fields byte-for-byte; T2N/X16P/X16N omit all six and say so. |
| MINOR 8 (key-only/value-only) | FIXED | `p6_fidelity.py:361-363`. |
| MINOR 9 (preflight enforced) | FIXED | `p6_fidelity_study.py:567-573`. I ran `_preflight()` myself: `frozen_equals_reference: True` at 1 thread, 6 threads and under `configure_cpu()`. It is deterministic, so it cannot stop the real run spuriously on this build. |
| MINOR 10 (start rule logging) | FIXED | `p6_fidelity_study.py:586-606`; `started_with_remaining_seconds` :639; no item gets `min(60, remaining)` any more. |
| MINOR 11 (explicit ID dry-run) | FIXED | `p6_stage.py:345-352`; `check_reaudit_p6e_chain.out.txt` last line. |

Notes from AUDIT.md that were addressed: NOTE 8 (fallbacks logged per pass, `p6_equivalence.py:186-204`); NOTE 12 (docstring now accurate, `p6_fidelity.py:16-20`); NOTE 13 (`loader-smoke` exists; see Regression (f)).

## Regression review (questions 2a–2g)

**(a) Width curve.** Frozen `tree_candidates(visit=k)` builds its candidates from `stable_top(routes, k)`. These equal the first k branches of the full 16-branch stable order: when there is no tie among the top k+1, both paths give the unique top-k order; with a tie, both use the stable argsort. The candidate IDs are therefore exactly the first 256·k captured columns, in the same order. Routes, the log-softmax prior, normalization and `/TEMP` are the same expressions. The only remaining dependency is whether each `bmm` row is bitwise independent of the row count M. `check_reaudit_width_and_fixtures.out.txt` tests this:

- `bmm` mismatches between M = 256k and M = 4,096: 0 for all k at N = 512, 64 and 1, at 1 and 6 threads.
- Over every batch, not just the first, on tensors with constructed route ties at rank k/k+1 (85–128 queries per k) and exact score ties across branch boundaries: the derived width-k selection equals direct `tree_candidates(visit=k)` on 0 mismatching queries for all k.
- My own full lexicographic sort (descending score, then ascending ID) agrees: 0 mismatches.

The spy captures exactly one tensor per batch, because the inner recursive `stable_top` call has `ids=None`. The hook runs after the spy is removed, so the cross-check's own calls are not captured. The width-k rows are concatenated in batch order, which is query order. The first-batch cross-check cannot stop spuriously on this build unless `bmm` row invariance fails on the real run's thread configuration. Gate (ii) has always depended on the same property for k = 2.

**(b) B1 path.** See the B1 row above. INCOMPLETE and unexecuted states are distinguishable in `analysis.json`: suite reasons are `budget` or `stage stopped earlier (<kind>)`, and record outcomes are `gate_violation`, `error` or `no_result_json`. Two reporting issues are MINOR 2 and NOTE 2 below.

**(c) Equivalence stops on real checkpoints.**
- *Reference tie rule in the panel, timing and Wtok scopes* (:553-560). The oracle uses `reference_scores` (:96-109), which repeats `Memory.lookup` / `tree_candidates` operation by operation. A `topk(9)` with strictly decreasing values determines the top 8 uniquely, and every exact tie goes through the full sort that reproduces `stable_top`. No spurious stop is possible while the reference arithmetic is deterministic. Exercised on a 512-row synthetic panel (`check_p6e_budget_recheck.out.txt`, eq phase completed).
- *Fixture integrity* (:534-550). Flat, tree-within-branch and tree-across-branches cases contain a ten-fold duplicate, or identical router rows plus duplicated keys, so exact top-9 ties exist for any weights. The across-branch case also relies on identical router rows giving bitwise-identical route scores in one GEMM, which holds on this build.
- The router case keeps router rows 4–7 at the checkpoint's own values. For the fixed tree those rows are the untrained registered init (a buffer), and per seed the fixture has 10, 8 and 11 rank-2/3 route ties. For the learned tree they are trained. In my simulation (rows 4–7 perturbed at 4 scales, and fully random), 0 of 200 runs per setting lost all ties. To remove them, all four trained rows would have to align with the constructed queries at cosine above about 0.50–0.66 and also break the 4–7 noise-query ties. Residual risk is low but not zero (NOTE 3).

**(d) Timing-worker replay.** It runs at `p6_timing_study.py:288`: after load, before variant construction, before the first-call measurement and before `run_timing`. It is outside every timed region and every GC-disabled block. The state, RNG, mode and GC baselines are captured before the replay (:279-282) and compared at the end (:385-393), so any side effect of the replay would stop the worker. My synthetic screen and confirm workers completed with all three replays bitwise-equal and the end check passing. Side effect on a descriptive quantity: MINOR 4.

**(e) Rerun and linkage guards.** They do not block the legitimate sequence (see M2). One gap: the analysis cannot report INCOMPLETE when a timing stage fails (MINOR 1).

**(f) `loader-smoke`.** P6-E (`p6_retrieval_study.py:266-319`) runs `load_real_cell`, `integrity_replay` per kind and `files_unchanged`. P6-Q (`p6_fidelity_study.py:751-800`) runs `prepare` (which also restores the step-0 checkpoint for coverage but computes nothing from it), the unmodified `evaluate`, and re-hashing. Neither calls a variant, comparison, rule substitution, reference, timing or measurement function. The only writes are `environment.json` into a `tempfile` folder, which is refused if it lies under `experiments/` or `results/`. The `p5_data` writer is the freeze function and is not reached by `load_frozen`. Not run by me. No smoke output is recorded anywhere in the repository (NOTE 4).

**(g) Loader in `p6_common.py`.** `load_real_cell` (:133-187) resolves the quality path and the P4 suite (`output_root / PARENT_SUITE`) to absolute paths, as P5's provenance requires. It checks the compact P5 record, the snapshot hash and the WikiText-2 acquisition manifest, and keeps the three memory kinds. `files_unchanged` (:103-123) uses the same provenance keys as P5's own `check_unchanged` (`p5_parent.py:41-50`). This is consistent with the frozen `_timing_models`, but I could not exercise it. P6-E derives the P4 suite from `--output-root`, so P6-E must be run with `--output-root experiments` (NOTE 5).

## New findings

### BLOCKER
None.

### MAJOR
None.

### MINOR
1. **P6-E analysis cannot report INCOMPLETE when a timing stage fails.** `p6_retrieval_study.py:151-159` uses `require_completed` for screen and confirm. A confirm stopped by a cap breach therefore makes the registered analysis end `failed` with no criteria at all, instead of SP/PAR/PR = INCOMPLETE (`check_reaudit_p6e_failed_confirm.out.txt`). The error text "pass the run ID explicitly" is misleading, because an explicit failed ID is also refused (`p6_stage.py:340-344`). The INCOMPLETE branch in `analyze` (`p6_analysis.py:222-224`) is unreachable for a failed stage. **This was already true of the code I audited earlier, and I missed it in AUDIT.md.** No false pass is possible. Fix: let `analyze_stage` accept the single (or explicitly named) failed confirm run, still pass it through `check_linkage` restricted to the completed workers, and call `analyze` on those workers so the criteria come out INCOMPLETE.
2. **Flags are labelled `COMPUTED` even when the suite stopped on an engineering gate or an integrity error outside the finals.** `p6_fidelity_analysis.py:337`. Case G in `check_reaudit_p6q_analysis.out.txt`: a gate violation on a step-0 checkpoint gives `flags_status: COMPUTED` with suite outcome `stopped`. §4.3 says such a violation "stops the study for engineering review". The suite outcome is in the same file, so this is not a false pass, but a bare flag could be quoted without the stop. Fix: set `flags_status` to a distinct value such as `COMPUTED_SUITE_STOPPED` whenever `suite.outcome` is not in `("completed", "completed_finals_step0_partial")` or the suite record is missing. PENDING LEAD REVIEW for whether such flags may be interpreted at all.
3. **The worker-end source check also covers docs/, so any documentation edit during a P6-E stage stops the stage.** `p6_stage.py:59-71` rebuilds the `records.record_source` archive. Its allowlist is `src, tests, docs, configs, prompts, templates, .github` and root files, with `.md`/`.txt`/`.json` included and tracked and untracked files both counted. During my own re-audit the archive hash changed between two runs only because I appended to a `.txt` file under `docs/reviews/` (`check_p6e_budget_recheck.out.txt`, 9f36… then 28e9…). Clarification 2 forbids agent, test and Git activity during *timing* stages. The equivalence stage (up to 1,200 s) has the same check, and nothing forbids editing the research log, a review or an ADR during it. A stop there costs the registered invocation (a rerun needs `--supersede`). Fix (procedural, no code change): extend clarification 2 so that nothing in the archive allowlist (including docs/) is modified from the opening of each P6-E stage until it ends, equivalence included.
4. **"First call after model load" is now measured after a full-panel replay.** `p6_timing_study.py:288` versus :320-331. The replay runs every unmodified model over 512 rows, so the reference entities' "first call" is no longer the first call after load, and these numbers are not comparable with P5's. The value is descriptive only. Fix: change `first_call_note` (:413-414) to "first W8 model_forward call per entity after load, the 512-row integrity replay and cache construction".
5. **P6-Q time margin: improved but unverified on real cells.** For all 54 finals to start, each final's worker must average ≤ (1,800 − 60)/53 ≈ 32.8 s. On synthetic data I measured 23.6 s per process, but real `prepare()` cost is unmeasured by me and no `loader-smoke` timing is recorded (NOTE 4). If one learned final near the end is skipped for budget, **both** kinds' flags become INCOMPLETE (`p6_fidelity_analysis.py:342-349`), as clarification 15 states literally. §4.4 defines flags per kind, so computing a kind's flags whenever its own 27 finals completed would also be consistent. PENDING LEAD REVIEW; no code change unless the lead amends clarification 15. Recommended before freeze: record one P6-Q `loader-smoke` output (`prepare_seconds`, `replay_seconds`, `peak_rss_bytes_ru_maxrss`) with the freeze, so the margin is evidenced.

### NOTE
1. **My own file is not `ruff format`-clean.** `tests/test_p6_fidelity_reference.py:192-216` (auditor-written, unchanged since AUDIT.md). CI runs only `ruff check` (`.github/workflows/e0-cpu.yml:25`), which passes. My earlier audit did not run `ruff format --check`. Cosmetic.
2. **A completed final outside the 27-cell grid crashes the analysis** with `KeyError` in `paired_differences` (case F). This cannot arise from the registered `items()`. A crash here is preferable to a 28-cell flag.
3. **Router-fixture tie on learned checkpoints** depends on trained router rows 4–7; the risk was quantified as low in Regression (c). If it fires, the stage stops (conservative); it does not pass anything.
4. **The real loaders remain exercised only by unrecorded implementer runs.** Clarification 27 says three cells were restored and replayed, but no output is stored. I did not run them, by instruction.
5. P6-E's P4 suite path is `--output-root / PARENT_SUITE` (`p6_common.py:154`), while P6-Q's is `--parent-suite/.. / PARENT_SUITE` or `--p4-suite`. Both are correct only with the documented `--output-root experiments`.
6. `prior_runs` (`p6_stage.py:118-130`) counts a stage folder left by an `open_stage` that crashed before writing its manifest. That forces a `--supersede`, which is conservative.
7. After a supersede, both the old and the new run stay consumable by explicit ID. Linkage keeps the chain consistent, and choosing between them is traceable through the recorded reason, but not prevented. This is accepted by clarification 17 as written.
8. A stopped P6-Q suite performs no suite-level after-hash (`p6_fidelity_study.py:654-658`). Each completed cell still records its own before/after hashes (:368-373).

## Real-data code paths that remain unexercised by any recorded evidence

- P6-E: `load_real_cell` and `CellSource.files_unchanged` on real snapshots; real fixtures built from trained weights (router case on learned trees, NOTE 3); workers writing under `experiments/` and `results/p6-e-2026-11-13/` with the real 27-pair, 8-round counts.
- P6-Q: `verify_hashes` over all 81 items; `prepare` (parent verification, two restores per item, step-0 fixed/learned identity check); gates (i)–(iv) and the width cross-check on trained weights; `_export` to the real results root; real per-checkpoint wall time against the 60 s and 1,800 s caps.
- Both: the subprocess `supervise` wrappers with real-size work (dry runs used tiny fixtures).

## Freeze recommendation: **READY TO FREEZE**

Reasons:
- B1, M1, M2 and MINOR 1–11 are fixed as decided in clarifications 15–27, with tests, and I independently confirmed each.
- No new finding can produce a wrong registered number or a false PASS.
- The new stops (tie-rule, fixture integrity, width cross-check, enforced preflight, timing replay, source recheck) did not fire spuriously on synthetic data. I found no mechanism by which they would fire on real weights, other than the low-probability router-fixture case (NOTE 3) and the procedural docs-edit hazard (MINOR 3).

Conditions I recommend before or at the freeze. They are not code blockers and are lead decisions:
- (i) Adopt the docs-freeze procedure in MINOR 3.
- (ii) Record a `loader-smoke` output for each study with the freeze (MINOR 5, NOTE 4).
- (iii) Decide whether to fix MINORs 1, 2 and 4, which are small and local. Otherwise accept them in writing, so that a failed confirm stage, or flags computed after a suite stop, are handled by the post-run independent recomputation rather than by the frozen analysis.

This is independent engineering evidence only; it is not Astra validation and not approval.
