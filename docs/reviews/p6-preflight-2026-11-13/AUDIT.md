# P6-E / P6-Q pre-freeze implementation audit

- Date: 2026-11-13. Auditor: Claude Opus 5.5 (`claude-opus-5-5`), auditor role.
- Status: independent engineering and mathematical evidence only. **Not Astra validation and not human approval.** Astra review: NOT_PERFORMED.
- Binding specification: `docs/decisions/ADR-0011-p6-retrieval-optimization-and-routing-fidelity.md` (working-tree SHA-256 `af623dee…c034c`, includes §7 and clarifications 1–14).
- Code audited: untracked files on branch `claude/p5-review-p6-proposal`, HEAD `981ce729261f8a606c635a7d785bdb840d5e4c2a`. SHA-256 at audit time:

| File | SHA-256 |
|---|---|
| src/arborlm/p6_analysis.py | 7b55e1898305409c342c367f07a2f919291547385d616f504863451b35f0606c |
| src/arborlm/p6_common.py | 47ed1edf6d232311fc2776d23844b9018948097cad20fef7e4b198f13168f732 |
| src/arborlm/p6_equivalence.py | af2dac157dca3850c77a90dc7083b54dea24d5aa30554adeeea708f91fb8ffae |
| src/arborlm/p6_fidelity.py | ea1c3b383e24b2a09ba3c063cbc42560ce61043d8c5d7121ad2618cdad63edae |
| src/arborlm/p6_fidelity_analysis.py | c8e576f1df0b1eabecf35dfd9827f50c761171f424472b3b15b3d89b55f58f40 |
| src/arborlm/p6_fidelity_reference.py (auditor-written; only its call sites audited) | a4e713608b8622f646011df88e5931ff92b1d612f0ea9711dab74f1a25156373 |
| src/arborlm/p6_fidelity_study.py | 704d1ba593af5a88dd7f0b3b8ad2e14c5156fddd8674732b4d14c78738ef0955 |
| src/arborlm/p6_retrieval.py | aa70eefd804a0581de2c43905361a272f48a7ce27ca9b3e1f88d917ecd5c3f34 |
| src/arborlm/p6_retrieval_study.py | 55af671fe1db7eddbfd010847728725c601c624d515f5dbf90ba03b3ede67dac |
| src/arborlm/p6_stage.py | 1adc178d3041d52420895aea646582985fef72c44fb437eff546e52ae2a52076 |
| src/arborlm/p6_timing_study.py | c673329a4ca502a50b166ca1ad1e05a0b7afadc07dd42f3232097d2fd1d71027 |
| tests/test_p6_fidelity.py | e06e808cac9b7364794db567407a526dd41d2a55f91111266b0ce85da311510d |
| tests/test_p6_fidelity_reference.py | 5c68383d8a1001c2f28e174127b23189962b7951bdba6416cae2c74035bd6436 |
| tests/test_p6_retrieval.py | fa7aa0eacccec7c613ba1ec16cc3afdacee06fefda02dbe9c6818704d6ba818e |

Any finding below refers to these bytes; later edits need re-audit of the changed lines.

## Environment and commands

macOS-27.2.1-arm64, Python 3.12.14, torch 2.8.0, `uv.lock` unchanged. All commands from the repository root.

```sh
uv run --locked pytest -q tests/test_p6_retrieval.py tests/test_p6_fidelity.py tests/test_p6_fidelity_reference.py -p no:cacheprovider
#   157 passed, 1 warning (NumPy not installed) in 31.03 s
uv run --locked ruff check src/arborlm/p6_*.py tests/test_p6_*.py   # All checks passed
uv run --locked mypy src/arborlm                                     # no issues in 58 files
uv run --locked python docs/reviews/p6-preflight-2026-11-13/checks/check_p6e_variants.py
uv run --locked python docs/reviews/p6-preflight-2026-11-13/checks/check_p6q_numerics.py
uv run --locked python docs/reviews/p6-preflight-2026-11-13/checks/check_p6q_budget.py
uv run --locked python docs/reviews/p6-preflight-2026-11-13/checks/check_p6e_budget.py <scratch> {eq|screen|confirm}
uv run --locked python docs/reviews/p6-preflight-2026-11-13/checks/check_p6q_partial_analysis.py <scratch>
```

Every auditor check uses random synthetic tensors with the registered shapes. No real checkpoint, real panel or real training row was loaded, and no study CLI was run against the real roots. `experiments/` and `results/` contain no P6 artifact (`find experiments results -iname '*p6*'` returned nothing). Outputs are saved next to each script in `checks/`.

**Failed checker attempt (kept):** `checks/check_p6e_budget.FAILED-attempt1.*`. My first budget script called `configure_cpu()` and then `timing_worker()`, which calls it again; torch refuses a second `set_num_interop_threads`. This was my mistake, not a defect in the audited code (the study runs each worker in a fresh process). Attempt 2 runs each phase in its own process.

## Summary

| Severity | Count |
|---|---:|
| BLOCKER | 1 |
| MAJOR | 2 |
| MINOR | 11 |
| NOTE | 13 |

Overall: the retrieval variants match the frozen reference as specified. The equivalence classifier and gate cannot be passed by a variant that selects differently from the reference. The P6-E criteria arithmetic matches §3.6 clause by clause. The P6-Q rule substitution, measurements, gates and flag arithmetic match §4.3–4.4 and clarifications 6–14. The blocker is in P6-Q run accounting and analysis: in the step-0 shortfall that clarification 6 itself expects, the code cannot produce the registered flags. The two majors concern the P6-Q time margin and P6-E protection against reruns and mismatched stages.

---

## BLOCKER

### B1. P6-Q analysis refuses to compute any registered flag unless all 27 step-0 records completed, and crashes on a cell killed by a cap

- Evidence: `src/arborlm/p6_fidelity_analysis.py:248-250` raises `"P6-Q analysis requires all 54 final and 27 initial records"`. `:233-234` raises on any record whose `outcome != "completed"`. `src/arborlm/p6_fidelity_study.py:642-644` reads `result.json` from every exported cell folder, but `_export` (`:436-441`) exports only the files that exist, and a worker killed by the watchdog writes no `result.json`. `tests/test_p6_fidelity.py:597-598` asserts this refusal as intended behaviour.
- Demonstration (`checks/check_p6q_partial_analysis.out.txt`): with 54 final records and 6 step-0 records, `analyze` raises `ValueError: P6-Q analysis requires all 54 final and 27 initial records`. When a cap-killed cell folder is present, `analyze_study` raises `FileNotFoundError`.
- Why it matters: clarification 6 says the 27 step-0 checkpoints are descriptive and run "in the remaining budget", and that any not reached "is recorded as unexecuted and reported". The run order already reflects this. That clarification projects about 2,300 s against the 1,800 s cap. On my synthetic full-panel model, one checkpoint evaluation took 26.5 s (`checks/check_p6q_budget.out.txt`), so the 54 finals alone use roughly 1,450–1,650 s. Only a handful of step-0 checkpoints will be reached. The registered run will therefore almost certainly end with step-0 records missing, plus one cell killed mid-run by `min(60, remaining)` (`p6_fidelity_study.py:551-561`). As written, the registered FID/COS/LOSS/PRIOR flags cannot be computed without changing frozen code after outcomes are visible. In the same situation the suite also labels itself `stopped`/`failed` (`:552-553`, `:598`, `:622`).
- Fix:
  - (a) Compute flags and paired differences from the 54 finals alone. Report flags as `INCOMPLETE` (not an exception) when any final is missing or not completed.
  - (b) Summarize step-0 over completed records only, listing labels that were unexecuted or failed.
  - (c) In `analyze_study`, list every cell folder that has no `result.json` or a non-completed outcome instead of crashing.
  - (d) Do not start a step-0 item when `remaining < CHECKPOINT_SECONDS`; record it as `unexecuted` so a cap-killed partial cell does not appear as a failure.
  - (e) Give the suite a distinct terminal status, for example `completed_finals_step0_partial`, when all 54 finals completed and the stop came from the budget during step-0.
  - Add a test with 54 finals and k < 27 step-0 records, and a test with a killed folder.

## MAJOR

### M1. The time margin for the 54 P6-Q finals is thin; a modest slowdown leaves the registered flags incomplete

- Evidence: `checks/check_p6q_budget.out.txt`. On a synthetic model with the full 512×65 panel, `evaluate_checkpoint` took 26.5 s: X16P 9.4 s, X16N 9.3 s, width curve 6.1 s, the rest about 1.6 s. Peak RSS was 0.80 GB. Real cells add `prepare()` work that synthetic runs skip: parent verification, two restores per final, file hashing and process start. That is likely 2–4 s more, giving about 54 × 29–31 s ≈ 1,570–1,670 s of the 1,800 s cap before any step-0 work. Clarification 6 quotes about 26 s plus process start.
- Why it matters: if the real machine is about 10% slower, or real cells take longer to prepare, finals near the end of the order are killed or never run. FID/LOSS/PRIOR/COS then become INCOMPLETE for at least one kind. Under §4.6 the cap cannot be raised.
- Fix (keeps every registered quantity unchanged): compute the width curve from the X16P candidate scores already captured by the spy, not by re-running `tree_candidates` five times (`p6_fidelity.py:574-591`).
  - The captured scores are in route-rank branch order, so the visit-k candidate set is exactly the first 256·k columns.
  - Selecting with `stable_top(captured[:, :256*k], 8, ids[:, :256*k])` is the frozen selection on the same float32 scores that gate (ii) already uses for k = 2.
  - This saves about 6 s per checkpoint, roughly 330 s over the finals.
  - Keep a one-batch cross-check against `tree_candidates(visit=k)` for every k, as an extra integrity check.
- Separately, PENDING LEAD REVIEW: whether to authorize a loader-only smoke test on one real cell before the registered run (restore and hash only; no replay, no rule evaluation) to measure real `prepare()` time.

### M2. P6-E does not prevent a second registered run of a stage, nor check that screen, confirm and analysis consumed the same upstream runs

- Evidence:
  - `src/arborlm/p6_stage.py:94-106`: `open_stage` always allocates a new run and never checks for an earlier completed or failed run of the same stage under `--results-root`.
  - `p6_stage.py:265-272`: an explicit `--equivalence-run` / `--screen-run` is accepted without checking `dry_run`.
  - `p6_retrieval_study.py:120-134`: `analyze_stage` takes the screen selection from `--screen-run` (or the single completed one) and the confirm run as "the one completed confirm". It never checks that the confirm's recorded `evidence.screen_run`, `evidence.selection_sha256` and `evidence.equivalence_run` (written at `p6_timing_study.py:433-456`) match the screen and equivalence runs being analysed.
  - `p6_timing_study.py:426-457`: confirm takes its equivalence run independently of the one the screen used.
  - In contrast, P6-Q refuses a non-empty results root (`p6_fidelity_study.py:492-493`).
- Why it matters (audit question 11): an operator can re-run `screen` or `confirm` and then pick a run with an explicit ID. All runs are preserved, so nothing is silently overwritten, but nothing in the code ties the analysed confirm to the analysed selection. That leaves open a selection-by-rerun path and an inconsistent analysis (the wrong entity names give INCOMPLETE, or in the worst case criteria computed against a selection the confirm did not time). This conflicts with "single registered invocation per study".
- Fix:
  - For non-dry-run stages, refuse to open a stage if `results_root/<stage>/` already has any run (completed or failed) unless an explicit, recorded `--supersede <run-id> --reason ...` is given.
  - In `require_completed`, also require `manifest.dry_run == dry_run` when a run ID is given.
  - In `analyze_stage`, assert that the confirm's `evidence.screen_run == screen_dir.name`, that `evidence.selection_sha256 == sha256(selection.json)`, that the confirm and the screen record the same `equivalence_run`, and that each confirm worker's `plan == confirm_entities(selection)` with `outcome == "completed"` and `dry_run` false.

## MINOR (each: file:line, why, fix)

1. **(c) is not actually gated on the tie rule.** `p6_equivalence.py:54-81`: `classify` ignores `tie_rule_violations_*`. The fixtures are not required to contain ties at run time (`compare_fixtures`, `:461-496`). Agreement with the frozen reference is what gates, and the reference does obey the rule (tested at `tests/test_p6_retrieval.py:241`; my own independent rule `checks/check_p6e_variants.py:my_registered_rule` agreed on 6×4,096 random queries), so I see no false-pass path. But §3.3(c) says "checked against the registered tie rule". Fix: make the variant NOT_EQUIVALENT on (c) when `tie_rule_violations_variant > 0`. Stop the stage when `tie_rule_violations_reference > 0`, or when any non-router fixture case has `queries_with_exact_ties_in_reference_top9 == 0`, or when the router case has no route tie at rank 2/3. My synthetic counts per case were 13, 24, 11 score-tie queries and 10 rank-2/3 route ties (`check_p6e_variants.out.txt`).
2. **`gate` silently skips missing scopes.** `p6_equivalence.py:656-660` filters to `GATE_SCOPES` and takes the worst over whatever is present. A record missing `c_fixtures` would gate on (a)+(b) only. Fix: require all four scopes and treat a missing one as NOT_EQUIVALENT.
3. **No integrity replay in timing workers.** `p6_timing_study.py:265-300`. Each timing worker restores the checkpoints again in a fresh process, checks hashes, and measures without replaying the P5 NLL. The equivalence stage's replay comes earlier in time, so §2 is arguably met. P5's timing worker also did not replay. PENDING LEAD REVIEW: whether "before any P6 measurement on a checkpoint … in the matched environment" means per process. Replaying would cost about 0.5 s per checkpoint per worker (`check_p6q_budget` phase `unmodified_replay`).
4. **The timing worker does not re-check the source archive.** P5 checked it after timing (`hierarchy_ablation.py:796-797`); `p6_timing_study.py:377-385` does not. Fix: compare `record_source` archive SHA-256 with the stage manifest at worker end.
5. **Fingerprint binding misses `.data` writes.** `p6_retrieval.py:166-169`, `:183-184`. In `check_p6e_variants.out.txt`, a `.data` in-place write (also inside `inference_mode`) is not detected by the fingerprint; the full hash detects it. Mitigation already present: full `verify_source()` and `state_digest` before and after each timing schedule (`p6_timing_study.py:324-327`, `:353`, `:377-385`), so a mutation cannot go unreported. Only a mid-schedule stale cache would go unnoticed until the end. Fix: state this limit in the timing record. No O(1) check can see `.data` writes, so keep relying on the full hash before and after the schedule (already present).
6. **Nearest-rank p50 is not reported.** `p6_analysis.py:43-75` and `p6_timing_study.py:193` report `statistics.median` (mean of the 40th and 41st samples) plus nearest-rank p10/p90/p95. §3.4 lists "nearest-rank p10/p50/p90/p95". The ratios correctly use the P5 median. Fix: add `p50_ns` nearest-rank as a reported field only.
7. **Concentration reports for X16P/X16N/T2N carry T2P constants.** `p6_fidelity.py:426-434` reuses `RetrievalCounts.report()`, which hard-codes `full_key_dots_per_query=512`, `logical_key_elements_per_query=8192` and the router element counts (`pilot_metrics.py:74-77`). Under X16 these labels are wrong (`check_p6q_numerics.out.txt`, last line). Fix: drop or relabel the analytical-work fields for non-T2P rules; keep the selection statistics.
8. **Coverage does not record key-only and value-only counts.** `p6_fidelity.py:338-349` records key, value, either and both. Clarification 8 asks for key-only, value-only and both to be counted. They can be derived, but should be explicit fields.
9. **The `_preflight` result is not enforced.** `p6_fidelity_study.py:443-458`, `:544`: `frozen_equals_reference` is logged but a `False` does not stop the run. Fix: stop on `False`.
10. **The suite cell-start rule can kill a final that would have finished.** `p6_fidelity_study.py:561` gives the last item `min(60, remaining)` seconds. For a final this is spec-consistent (cap breach stops the stage), but it should be logged as "started with less than the per-checkpoint cap" so a budget kill is distinguishable from a slow cell. (Related to B1(d).)
11. **An explicit equivalence/screen run ID can consume a dry-run record.** `p6_stage.py:265-272` (see M2). Listed separately because it is a one-line fix even if M2's broader guard is not adopted.

## NOTE

1. **Guard band sufficiency (§3.2, audit question 1).** `p6_retrieval.py:356-381`. A query is unflagged when all eight adjacent gaps among the fast top-9 are ≥ δ. Suppose every candidate's fast score differs from its T2-arithmetic score by at most ε. Then for k ≤ 8, t_k − t_{k+1} ≥ δ − 2ε. For any candidate j outside the fast top-9, t_j ≤ f_9 + ε ≤ f_8 − δ + ε < t_8. So the selected IDs and their order equal T2's exactly if and only if ε < δ/2 = 5e-5, and T2's selection equals T0's by STRICT equivalence. Bound: the prior is computed by identical code in both paths. The contraction error of each method is at most γ₁₆‖q‖‖k̂‖/0.2 ≈ 4.8e-6. Adding the prior adds rounding of about ≤ 1e-6. So ε ≤ ~1.1e-5 in the worst case, and the guard is logically sufficient with at least 4× margin. Measured on synthetic data: max |T4 − T2 contraction| = 1.43e-6, T3 bitwise equal to T2, and the fallback fraction was 0.76–1.25% (`check_p6e_variants.out.txt`). Exact ties give a gap of 0 < δ and always fall back, so T5's first-occurrence tie behaviour never reaches the output. `<` versus `≤` at exactly δ is immaterial given the margin.
2. **T3 is arithmetically T2 on this build.** `p6_retrieval.py:384-391` gathers `[2N,256,16]` key blocks and uses `bmm`. Its contraction was bitwise equal to T2's on every synthetic case, and T3 classified STRICT. It differs from T2 only in gather layout, guard and `topk` without the safety argsort. PENDING LEAD REVIEW: whether "contraction expressed on branch blocks" was meant to avoid the per-query key copy. As implemented, T3 measures layout plus guard cost, not a different contraction.
3. **Load-time `slot_offsets` cache.** `p6_retrieval.py:272` caches `arange(256)`, which the reference builds per call. It is not one of the caches listed in §3.2 for T1, but costs about 1 µs; disclose it.
4. **Guard and fingerprint cost biases timing slightly against variants.** Measured at 3.4 µs per call with the fingerprint versus 92.7 µs with the full hash, against a T2 W8 lookup of about 5.3 ms (exploratory, one run): about 0.07% at W8, more at W1, and a few percent at Wtok (descriptive only). The full hash would have been about 1.8% at W8. The fingerprint choice is sound because the full hash is verified before and after every schedule (MINOR 5).
5. **Flat comparator reading.** `p6_analysis.py:311-325` uses the median across 27 workers of each worker's W8 `addition_forward` median. This is a reasonable literal reading of "lowest W8 addition_forward median in T-screen". A paired geometric-mean ratio to F0 would mirror the tree rule more closely. Both are defensible; the choice is made before observation and recorded in `selection.json`.
6. **Comparator fairness, exploratory.** On synthetic tensors, F2's kernel (clone of a 512×4,096 matrix plus 9 passes, `p6_retrieval.py:83-97`, `:252-260`) is slower than `topk`, while the same kernel on 512-wide tree rows is faster than `topk` (`check_p6e_budget.out.txt`). This follows the specified kernel and is not a defect. PENDING LEAD REVIEW only if the lead wants to discuss whether the flat comparator set is a fair "same kinds of optimization" baseline. No threshold or variant should change.
7. **The RNG-unchanged checks are vacuous inside `_isolated_rng`.** `p6_equivalence.py:314`, `p6_fidelity.py:226` and `p6_timing_study.py:132` restore RNG state, so the after-checks cannot see RNG use inside those blocks. No variant uses RNG; record the limitation.
8. **Fallback counts are logged twice in equivalence.** `p6_equivalence.py:325-351` logs once for the lookup and once for the forward per batch. The fraction is unaffected; the counts are doubled. This is descriptive and shown in the record.
9. **A crashing variant halts the whole equivalence stage.** `p6_equivalence.py:704-710` re-raises, so one variant's exception stops all variants: conservative, no false pass, but P6-E would then end with no timing.
10. **Per-token split.** `p6_fidelity.py:437-454`, `:761-764` split positions by whether that position's own selection changed, as §4.3 says. Block 1's causal attention carries changes to later positions, so "unchanged" positions are not counterfactually untouched. This is a caveat for interpretation (PENDING LEAD REVIEW for wording), not a code defect.
11. **Flag thresholds are compared as exact `Fraction(float)`.** `p6_fidelity_analysis.py:87-94`, `:113-121`. `Fraction(0.95)` and `Fraction(-0.005)` differ from the decimal values by about 1e-17 to 1e-19. Recall means are k/262,144, so no ambiguity is possible for FID/COS. For LOSS/PRIOR the window is about 1e-19. Independent recomputation must use the same convention.
12. **The docstring claims the real loader was exercised.** `p6_fidelity.py:16-17` says nothing has been applied to a real checkpoint "beyond the engineering confirmation that the loader works". No P6 artifact exists under `experiments/` or `results/`. Ask the implementer to record exactly what ran (if `prepare()` only, the real panel was read but no P6 quantity was computed).
13. **The real-data loaders are untested.** `load_real_cell` (`p6_common.py:121-172`) and `prepare`/`_restore`/`locate`/`verify_hashes` (`p6_fidelity_study.py:118-322`) have no test, since no real fixture exists. A path or key error would surface only in the registered invocation. See M1's PENDING LEAD REVIEW about a loader-only smoke test.

---

## Point-by-point coverage of the requested checks

1. **Variants (§3.2).** F1/F2/T1/T2 return `selected`, scores, `branch_ids` (rank order), `candidate_ids` (reference rank order) and `route_scores` bitwise equal to F0/T0 on synthetic data. T3 is also bitwise equal; T4/T5 select identically with max score difference ≤ 1.43e-6 (`check_p6e_variants.out.txt`). Division by temperature is used everywhere (`/ TEMP`; tested at `tests/test_p6_retrieval.py:154-158`). The prior is gathered with the ID-sorted branch order that matches the ID-ordered candidates (`p6_retrieval.py:108-113`, `:300-302`, `:359`). The tie rule:
   - routes use frozen `stable_top` (`:285`);
   - T1 and T2 use frozen `stable_top`;
   - F2 uses first-occurrence maxima, a strict-descent check and the stable-argsort fallback, equivalent to `stable_top`;
   - T3–T5 send any tie to T2 through the δ guard.
   The guard is exactly δ = 1e-4 over the 8 adjacent gaps among the top 9, recomputed with T2 arithmetic (`reference_arithmetic_t2`). Logical sufficiency: NOTE 1. No variant caches or reuses query-dependent results across calls (`fallback_log` is bookkeeping only), and nothing query-dependent is precomputed. T3 is arithmetically T2 (NOTE 2).
2. **Guards and binding.** Gradient-enabled and training-mode refusal is present and tested. Caches are plain tensors, and the wrapped module is held unregistered. Fingerprint: NOTE 4 and MINOR 5.
3. **Equivalence (§3.3).** STRICT/BOUNDED/NOT_EQUIVALENT match the table. Comparisons are bitwise via int-view for floats (`p6_retrieval.py:53-61`). Tolerances are 1e-5/1e-4/1e-6 with `≤`. Mismatches are counted per query over all queries, and a single mismatch gives NOT_EQUIVALENT. The gate requires every checkpoint (27 or 54) and every gate scope (but see MINOR 2). The reference path is the unmodified `Memory`/`Model`. The variant is compared against the reference, never itself, never after sorting, and never on a subset. No exception is swallowed. Oracle: `topk(9)` with a full stable sort only when an exact tie occurs among the top 9. This is valid: strictly decreasing top-9 values determine the top 8 and their order uniquely, regardless of IDs (`p6_equivalence.py:117-132`); `-0.0 == 0.0` routes to the full sort, consistent with `stable_top`. The oracle is not gating (MINOR 1). The integrity replay is against `results/p5-2026-11-13/<cell>/result.json` `final.nll`, bitwise via `struct.pack("!d")` (`p6_common.py:154-157`, `p6_equivalence.py:502-514`).
4. **Timing (§3.4).**
   - Workloads match P5: W8/W1 from `p5_timing.inputs_from_rows`, plus Wtok as the first token of W1.
   - Scopes use the same callables as P5 (`partial(model)`, `partial(model.addition, h)`, `partial(model.addition.lookup, q)`); the only extra work in variant calls is the guard (NOTE 4) and the `slot_offsets` cache (NOTE 3).
   - Protocol: 8 rounds × (2 warmups + 10 timed); rotation `(pair_index + round) mod n` over all worker entities, with the same index as P5; GC disabled only inside blocks; reliability rule identical to P5 (`summarize_rounds`, tested equal to `p5_timing.summarize`); no outlier removal or rerun.
   - T-screen selection rules: §3.2 and §3.4. T-confirm times only {F0, comparator, T0, selected} per kind, in fresh subprocesses.
   - Caps match §3.5; a breach stops the stage and preserves partial and unexecuted rows.
   - Flat comparator: NOTE 5.
   - Feasibility on synthetic models: equivalence worker about 15 s, screen worker about 27 s, confirm worker about 10 s, before real-loader overhead. That gives about 400–500 s, 750–850 s and 300 s against caps of 1,200/1,200/600 s, and stays within the 90/45 s per-worker caps (`check_p6e_budget.out.txt`; exploratory, one machine).
5. **Analysis (§3.6).**
   - SP: GM ≤ 0.50; ≥ 26/27 pairs < 1; 9/9 parents < 1; reliability on all 27.
   - PAR: addition GM ≤ 1.00 with 22/27 and 8/9 ≤ 1.00; forward ≤ 1.05 with 22/27 and 8/9 ≤ 1.05.
   - PR: addition GM ≤ 0.80 with 22/27 and 8/9 < 1; forward as in PAR.
   - Ratios are computed from raw samples, never from stored summaries. Wrong pair counts give INCOMPLETE, unreliable measurements give INCONCLUSIVE, and ratios against F0 are reported alongside. Criteria are evaluated on T-confirm records only. All match the specification.
6. **P6-Q rule substitution.** Only `memory.lookup` is shadowed, and route scores use Memory.lookup's exact expression. `tree_candidates` is called with `(visit, use_prior)` = T2P (2, True), T2N (2, False), X16P (16, True), X16N (16, False). The spy returns `original(...)` unchanged (`spy_identical=True` in 6/6 synthetic cases). T2P is gated bitwise against both the unmodified replay and the P5 record.
7. **Measurements.** recall_P/C, histograms, width curve (vs X16P), certificate (`values[:,7] ≥ 5 + max unvisited log-prior`, in float64), coverage (bitwise int32 view; key|value), trained-restricted recall (macro over queries with ≥1 trained reference slot, and pooled), lost candidates (rank from the full 16-branch order; margins against X16P only), weighted recall (reference's own softmax), prior effects, concentration (P5's tail, T2P must reproduce P5) and the per-token split all match §4.3 and clarifications 6–14. Signs: Δ_restrict = X16P − T2P, Δ_prior = T2N − T2P, Δ_both = X16N − T2P; negative means the alternative is better, consistent with LOSS (≤ −0.005, cells/parents < 0) and the PRIOR sign meaning in §4.4/4.5.
8. **Gates and flags.**
   - Gates (i)–(iv) and the clarification-12 integrity stops are implemented. Gate (iv) stops only on differing sets with a float64 boundary gap > 1e-5.
   - Measured float32-versus-float64 score error was ≤ 1.95e-6, so 1e-5 leaves about 2.5× margin for a two-sided flip (`check_p6q_numerics.out.txt`).
   - FID/COS: ≥ 0.95, 22/27, 8/9. LOSS as above. PRIOR: |mean| ≥ 0.005 with sign agreement 22/27 and 8/9; a zero mean fails.
   - Boundary equality passes, and parents are 9 (b, o) groups of 3 seeds.
9. **Run order and records.** 54 finals first (parent/seed ascending, fixed then learned), then 27 step-0. Caps 60 s per checkpoint (whole process) and 1,800 s total. Each cell's compact record is exported as soon as it finishes; arrays stay under `experiments/` with SHA-256; checkpoint hashes are checked before and after; the manifest records source, spec and lock hashes. Defects: B1 and M1.
10. **Tests.** They compare variants with the frozen `Memory`, not with themselves. The classification and criteria tests use hand-calculated numbers, including exact boundary cases. The defect-injection tests (`_WrongOrder`, `_Mutating`, corrupted gates, perturbed references) show the stops fire. Partly self-referential: the fixture tie checks use the implementation's own `full_sort_oracle`/`reference_scores`, which my independent rule cross-checked on random data. Important untested behaviour:
    - partial step-0 analysis (B1; the test asserts the opposite);
    - rerun refusal and stage consistency (M2);
    - fingerprint against `.data` writes (MINOR 5);
    - the timing worker's state-mutation stop path;
    - the real loaders (NOTE 13);
    - a missing gate scope (MINOR 2).
11. **Leakage and rerun.** Nothing in the code or tests computes a P6 quantity on real data. Dry-run refuses `experiments/` and `results/`. P6-Q refuses a non-empty results root and refuses to overwrite `analysis.json`. P6-E: M2 and MINOR 11.

## What I did not check

- Nothing was run on real checkpoints, the real panel or real training rows, so I have no evidence that the real loaders work (`load_real_cell`, P6-Q `prepare`/`_restore`/`locate`/`verify_hashes`). I also have no evidence that T1/T2 are bitwise STRICT on the real weights and build; that is exactly what the registered equivalence stage will measure.
- I did not audit `p6_fidelity_reference.py` itself or its tests (I wrote them), only how it is called.
- I did not audit the frozen dependencies used as black boxes: `watchdog.supervise`, `p5_clock.SuiteRSS`, `records.*`, `p5_checkpoint.restore`, `p5_parent.*`, `p5_data.load_frozen`. In particular I did not verify that `supervise` enforces the RSS and wall-time caps as the stages assume.
- I did not verify that P6 timings are comparable with P5's on the same machine, nor the accuracy of the torch-profiler allocation numbers (`allocation_profile`); they are labelled approximate.
- I did not re-derive ADR-0010 §7 text beyond comparing with `p5_timing.py` and the P5 timing worker in `hierarchy_ablation.py:687-811`.
- Timings and budgets in `checks/` are single exploratory runs on synthetic tensors on this machine. They are not registered evidence and not predictions of P6 outcomes.
