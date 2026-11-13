# P7-A pre-freeze re-audit (ADR-0013 §14 items 8–14 applied)

- Date: 2026-11-13. Auditor role: Claude Opus 5.5 (`claude-opus-5-5`). Branch `claude/p7a-storage-locality-proposal`, HEAD `3617fc6`. The P7-A code is still untracked.
- **This is independent engineering and mathematical evidence. It is not Astra validation and not human approval.** Astra review: NOT_PERFORMED.
- Synthetic data only. No model was run on a real checkpoint, and no real trace, registered stage, `loader-smoke` or training was run. The only real-derived input is part E of `check_fm_null.py`, which reads my own earlier output `outputs/fm_distortion.json` (per-cell max count and top-8 share of the 81 published P5 histograms). No new computation was run on P5 records.
- Environment: macOS 27.2 arm64, Apple M5 Max. Project Python 3.12.14 via `uv run --locked` (torch 2.8.0). System `python3` 3.15.1 for `check_item8_wording.py`.

## Audited files (sha256, unchanged from the start to the end of this re-audit)

| File | sha256 |
|---|---|
| src/arborlm/p7a_analysis.py | `f1fd07e93c2e9db2b20284a84ad06120bd624c2a229219c2c2a24b22fe4f4776` |
| src/arborlm/p7a_core.py | `666d7d7781388773536e4e491c320aa6b03a4fed7fcc66a4bbe3f4381901b805` |
| src/arborlm/p7a_sim.py | `42a121a22a9c0fbc1fa5652581068aa9564a5a1f6e2d72fdf71a8576ce865975` |
| src/arborlm/p7a_stage.py | `150a50fea5d1c2091cdb2fc7f1e23629631b8507eaa440aaecdb5c44f8d9865e` |
| src/arborlm/p7a_study.py | `8317b9392ec97c692523d45dccdb02002463df96405089b2c307ee5fe3eba06e` |
| src/arborlm/p7a_trace.py | `396c956e9f2215b37a179209502946b08adfc56bc081e2950e94128a6d35e7e0`, **identical** to the hash in my pre-freeze dry-run manifest |
| tests/test_p7a_analysis.py | `fbd0e9dd7dd6a5091f31662557839e51158b89c482a482d952c9db90777175a6` |
| tests/test_p7a_sim.py | `a0794767152eb1449acb79462e7e58425a66718f590912c10ddb726d28e3427f` |
| tests/test_p7a_study.py | `801d4aa103b5cc9934bf4c8f743112a257a97cf667fae642027d441676c4b76a` |
| tests/test_p7a_trace.py | `a256045a013e65809e36b622ed79d2d89b05d3dbb2a62d67489b76483216aaef`. My first audit did not record a hash for this file. Its mtime (15:07) is earlier than AUDIT.md (15:29), so it is unchanged by mtime only, which is weak evidence. |
| docs/decisions/ADR-0013-p7a-storage-page-locality.md | `ce79969876d8e2c685dc396c3c7b339f3b1b42ff601698b9c75bd550b05274e7`. `git diff` shows 17 inserted lines (§14 items 8–14) and no other change. |
| docs/reviews/…/independent_sim.py (v2, mine) | `fc522698c30568679e687cf6d3a1a2e8d75eb1d4b237d3e8f60374c68a051a08` |
| docs/reviews/…/independent_sim.v1.py (kept) | `61b29d8895e838cd3266bbc9b1a96bbcd5c75c665fe8d1d5f8acb27644817ae2` |
| docs/reviews/…/check_exact_null.py (imported by `tests/test_p7a_sim.py`) | `6fd462d487c7b9d8f082487c242eb5ef77a311e4f87fe4fc2218f0968adfa7ba` |

## Counts

BLOCKER 0 · MAJOR 0 · MINOR 7 (new) · NOTE 4. Every earlier BLOCKER and MAJOR is FIXED.

## Commands run (repo root) and results

| Command | Result | Output |
|---|---|---|
| `uv run --locked --extra pilot pytest -q tests/test_p7a_sim.py tests/test_p7a_trace.py tests/test_p7a_analysis.py tests/test_p7a_study.py` | 114 passed (36 s), after my v2 edit. It also passed before the edit. | `reaudit/outputs/pytest_p7a.txt`, `…_before_script_edit.txt` |
| `uv run --locked ruff check …p7a_*.py…`; `ruff format --check`; `uv run --locked mypy src/arborlm` | all clean; mypy: no issues in 64 files | `reaudit/outputs/lint_types.txt` |
| `uv run --locked --extra pilot python -m arborlm.p7a_study budget` | flat 9.47 s, tree 11.15 s; projected 858 s; margin 4.20; peak RSS 0.82 GB | `reaudit/outputs/budget.txt` |
| `uv run --locked --extra pilot python -m arborlm.p7a_study dry-run` | trace, simulate and analyze all exit 0; outcomes INCOMPLETE (expected); experiments/ and results/ unchanged | `reaudit/outputs/dry_run.txt` |
| `uv run --locked --extra pilot python …/reaudit/check_fm_null.py` | see the null section | `reaudit/outputs/fm_null.{txt,json}` |
| `python3 -I …/reaudit/check_item8_wording.py` | MINOR-R3 | `reaudit/outputs/item8_wording.txt` |
| `uv run --locked --extra pilot python …/reaudit/check_conc_logic.py 2000` | 0 mismatches in 4,000 outcome evaluations | `reaudit/outputs/conc_logic.{txt,json}` |
| `uv run --locked --extra pilot python …/reaudit/check_stage_state.py <scratch>` | see Regressions | `reaudit/outputs/stage_state.txt` |
| `uv run --locked --extra pilot python …/reaudit/harness_gate.py <scratch> all` | see the gate section | `reaudit/outputs/harness_gate_all.{txt,json,console.txt}`, `gate_*.stdout.txt`, `gate_p2_full_agree.summary.json` |

**Earlier runs kept.** `reaudit/outputs/run1_*` is a first part-1 harness run with v2 before I added two reporting-only fields (`script_sha256`, `study_result_sha256`). Its results are identical to the final run. The first `check_conc_logic.py` run, with 60 instances, was a smoke test (0 mismatches); the 2,000-instance run overwrote its output file. I made no failed checker attempts in this re-audit.

---

## 1. Status of each earlier finding

| Finding | Status | Evidence |
|---|---|---|
| **B1** frequency-matched null | **FIXED** | `p7a_core.py:351-457` implements item 8 (steps 1–4, one `random.Random(s*1000+cell_index)`, hard-stop check `:438-445`). `p7a_sim.py:450-456` uses it per replicate and stores generation records with `stream_sha256`. Tests: exact counts `test_p7a_sim.py:356-386`, hard stop `:416-429`, step 1–3 equality with my script `:432-452`. My own regeneration agrees bit for bit (below). |
| **M1** analysis guard | **FIXED** | `p7a_study.py:505-520` compares current source hashes, spec hash and `git_head` with the simulate manifest. It is called at `:607` before `open_stage`. Test: `test_p7a_study.py:533-564`, which also checks that no analyze directory is created. |
| **M2** independent-check gate | **FIXED**, with the hardening gaps MINOR-R1 and MINOR-R2 | `p7a_study.py:532-598`, `:608-614`, recorded hash `:619`. Tests: `test_p7a_study.py:568-701`. Validated end to end with my script (below). |
| **M3** degenerate concentration control | **FIXED** | `p7a_analysis.py:228-258`: a frequency-matched flat mean below 0.05 makes CONC DEGENERATE, giving `outcome_for` → UNSPECIFIED (`:110-125`). Tests: `test_p7a_analysis.py:332-378`. Independent truth-table check: 0 mismatches (below). |
| **Tie rule** (minor 1) | **FIXED** | Ascending rule documented (`p7a_sim.py:10-16`). `lru_pass(descending=)` at `:151-191`. Sensitivity at the primary setting only (`:485-501`), descriptive table (`p7a_analysis.py:600-654`) with no criterion. Ascending numbers are untouched: the descending pass is a separate call over the same read-only page sets, and `test_p7a_sim.py:620-654` compares every stored ascending count with a plain pass. |
| Minor 2: decomposition per checkpoint | FIXED | `p7a_analysis.py:407-424` |
| Minor 3: descriptive tables | FIXED | `p7a_analysis.py:425-427, 521-597` |
| Minor 4: sim worker environment | FIXED | `p7a_study.py:155-156`; test `test_p7a_study.py:771-802` |
| Minor 5: end-of-stage check | FIXED | `p7a_stage.py:66-105`. NOTE-R1: the docstring is wrong about `results/`. |
| Minor 6: P6 label in trace-worker environment | FIXED | `p7a_study.py:112-113` overwrites it with P7-A's record (tested `:796-802`) |
| Minor 7: budget overhead | PARTLY | Stated in the note (`p7a_study.py:846-849`), not measured. My harness measured study `simulate_checkpoint` at 10.0–16.1 s per full-size checkpoint. With +1–2 s per worker, 81 checkpoints come to about 1,000–1,150 s, a margin of about 3.1–3.6 against 3,600 s. |
| Minor 8: trace-stage timing | NOT FIXED | Still unmeasured. It is an operator step (`loader-smoke` timing) and needs no code change. See §6. |
| Minor 9: tests | FIXED | FM exactness, analysis guard, gate, FM-degenerate CONC, calibration slice (`test_p7a_study.py:705-715`), sim worker with a P5 record (`:718-768`). One test is lucky with its seed: MINOR-R4. |

## 2. The exact count-preserving null (item 8)

**It implements exactly the four registered steps with one generator.** `_deal_and_repair` (`p7a_core.py:356-399`):
- step 1, occurrences in slot order, `generator.shuffle` (`:370-371`);
- step 2, the deal (`:372`);
- step 3, the repair (`:374-398`).

`frequency_matched_detail` then applies step 4 with the **same** `generator` object (`:433-437`). There is one `random.Random(fm_generator_seed(s, index))`, and `index = core.cell_index(pair, kind)` is passed by the sim worker (`p7a_study.py:201`). My v2 records `cell_index` independently from the label order and compares it.

**Bit-for-bit regeneration.** `independent_sim.fm_stream` (v2) was written from the ADR text with a different loop structure. It does not use `check_exact_null.py`, which the implementer had already matched. `check_fm_null.py` part A covered 12 histograms × replicates {91301, 91302, 91303} × cell indices {0, 40, 80} = **108 cases, 108 agree** in rows, `stream_sha256`, swap count and generator seed. The histograms were Zipf 1.0 and 1.2, hottest slot at 0.56 Q, a slot in every query, k = 9 and k = 8 tight, and uniform over 4,096 slots, at Q = 64, 512, 4,096 and 32,768. In 4 of the 108 cases, both implementations stop at the same query (k = 8 tight; see MINOR-R4). Full-size generation takes 0.13 s mean and 0.22 s max in the study, and 0.10 s mean in mine. Through the stage pipeline, my script also regenerates all three replicates of the 18 selected checkpoints. `stream_sha256`, swap counts and every count in the 60 (layout, R, C) configurations per replicate under L-ID and L-FREQ agree, at 512 queries (81-checkpoint dry-run pipeline) and at 32,768 queries (18 full-size checkpoints).

**Exact counts and distinct slots.** Each swap keeps every count. It removes one duplicate from q (x leaves once, and y is not in q) and creates none in r (r lacked x), so already-repaired rows stay valid. The final check (`:438-445`) recomputes the counts from the permuted stream and checks distinctness per row. **The hard stop is real.** I replaced `_deal_and_repair` with two corrupting variants (a duplicate inside a query, and a count moved to another slot with distinctness kept). Both raise `InvariantError` (part D). The sim worker maps `InvariantError` to `gate_violation/invariant`, exit 1 (`p7a_study.py:229-233`), which stops the simulate stage.

**Termination.** The repair always terminates. The `while` loop runs at most 7 times per row (one fewer duplicate per pass, or a raise), and the partner scan is bounded by Q.

**Can the repair fail on a feasible histogram?** Yes, but only by stopping loudly. I found no case of a silently wrong arrangement. Part B uses k = 8 slots each with count Q, which is feasible because every query holds all eight. The greedy repair dead-ends in 102/300, 137/300 and 144/300 seeds at Q = 8, 16 and 128. Both implementations raise on exactly the same seeds. With k ≥ 9, there were 0 failures in 900 trials. **For the registered run this cannot happen, whatever the seed.** A dead-end at query q with duplicate x needs every query that lacks x to consist only of the at most 6 other slots in q. At least Q − c_x + 1 queries lack x, so a dead-end requires 8(Q − c_x + 1) ≤ the sum of the 6 largest counts. Part E: 8(Q − c_max + 1) exceeds the top-8 sum (an upper bound on the top-6 sum) for **81/81** published histograms. The tightest is b102-o303-fixed_tree-s502: 114,472 > 110,120.

**Step 4 removes the adjacency the repair creates (part C, full size, the study's own steps 1–3 then step 4).** The table gives mean slots shared by consecutive queries.

| Histogram | Before step 4 | After step 4 | Far pairs | Independence Σ(c_i/Q)² |
|---|---:|---:|---:|---:|
| Zipf 1.0, 700 slots | 1.4031 | 1.1444 | 1.1393 | 1.1402 |
| Zipf 1.2, 300 slots | 2.1037 | 1.8225 | 1.8257 | 1.8246 |
| Zipf 0.8, 1,500 slots | 0.6439 | 0.4920 | 0.4888 | 0.4930 |

Page reuse with the previous query at R = 2 (L-ID) falls from 0.1765, 0.2638 and 0.0832 before step 4 to 0.1442, 0.2287 and 0.0640 after. Without step 4 the repair would inflate consecutive-query sharing by 23–31%. With it, sharing matches independence to within sampling noise.

## 3. Regressions and new risks

**CONC non-degeneracy and UNSPECIFIED, branch by branch (`p7a_analysis.py:201-259, 110-125, 281-348`):**
- Actual stream degenerate: LRU and CONC are DEGENERATE → UNRESOLVED.
- Actual non-degenerate and LRU fails → NO ADVANTAGE, whatever CONC is.
- LRU holds and frequency-matched flat mean < 0.05 → CONC DEGENERATE → **UNSPECIFIED**. This is now reachable, and the earlier false-positive path (both nulls zero) now gives UNSPECIFIED (test `:351-353`).
- Flat ≥ 0.05 and tree < 0.01 → evaluated as written (item 9).
- `robust` counts only settings with R ≤ 8, NON-DEGENERATE, LRU HOLDS and CONC FAILS. A CONC DEGENERATE setting does not count.
- Any missing or incomplete record → every criterion INCOMPLETE.

`check_conc_logic.py` compares `p7a_analysis.criteria` with my own implementation of §7 plus item 9, which imports nothing from arborlm, on 2,000 random fabricated 81-cell studies drawn near the floors, the ratio and the counts. Result: **0 mismatches** in LRU, CONC and outcome over 4,000 evaluations. Every outcome occurred: NO ADVANTAGE 1,549, UNRESOLVED 1,272, UNSPECIFIED 606, CONCENTRATION-ONLY 269, STRUCTURAL robust 245, STRUCTURAL not robust 59. **No degenerate or incomplete case can yield STRUCTURAL ADVANTAGE or CONCENTRATION-ONLY.** Both require LRU HOLDS, which requires a non-degenerate actual stream. Both also require CONC HOLDS or FAILS, which requires the frequency-matched flat mean ≥ 0.05. Both require `study.complete`.

**Analysis guard and gate against the legitimate sequence.** trace → simulate → independent check → analyze passes. I ran it on the study's own pipeline with all 27 pairs (81 synthetic checkpoints, dry-run flag): `run_analyze` completed, with the gate defaulting to the registered 18 and the file's sha256 recorded in the linkage. The guard blocks only if HEAD, the P7-A sources or the spec change between simulate and analyze. **So nothing may be committed between simulate and analyze, including the independent-check output.** Commit afterwards. A stale or mismatched file is refused when it names another simulate or trace run (negative control "wrong run" with a real second simulate run), another selection, a DIFFER verdict or the `desc` tie rule. It is **not** refused in the two cases MINOR-R1 and MINOR-R2 describe.

**Relaxed end-of-stage check** (`check_stage_state.py`, on a scratch clone, before and after a simulated freeze commit):
- Detected: edits of tracked files (a P5 record, README.md), of `src/arborlm/p7a_core.py` (untracked and tracked), of `tests/test_p7a_sim.py`, of the ADR, and a new `src/arborlm/p7a_extra.py`.
- Not detected, by design: a new file in `docs/reviews/p7a-results-audit/`, a log file at the repository root, and new files under `results/p7a-2026-11-13/` (which stages write).
- My `independent_sim.py` is protected only once committed: an edit is detected after the freeze commit but not before it.

So writing the independent-check output or a log between or during stages breaks nothing, as long as it goes to an untracked path outside `src/`, `tests/`, `configs/` and `docs/decisions/`.

**Descending-order sensitivity.** It leaves the registered ascending numbers untouched (see the tie-rule row in §1). It is computed only for actual / L-FREQ / R = 2 / C = 32 and enters no criterion. `test_p7a_analysis.py:444-450` checks that outcomes are the same with and without it.

## 4. Independent simulator v2 and gate validation

`independent_sim.py` v2 (v1 kept as `independent_sim.v1.py`) adds:
- the frequency-matched regeneration (always on; it cannot be switched off);
- `cell_index`, `script_sha256` and per-label `study_result_sha256`.

It still emits the fields the gate reads: `argv` (with `--registered-selection`, `--sim-workers`, `--trace-root`), `selection`, `tie_rule`, `checkpoints.<label>.differences` and `integrity_problems`, and `verdict`. `registered_selection()` is unchanged, as `tests/test_p7a_sim.py:496-510` requires.

| Run (harness_gate.py, `python -I`, Python 3.12.14) | Script result | Gate |
|---|---|---|
| 81-checkpoint dry-run pipeline, `--registered-selection --allow-small` | AGREE, exit 0, 4.0 s | ACCEPTED; `run_analyze` completed and recorded the file hash |
| Perturbed frequency-matched count (+1, freq_matched_2 L-FREQ R2 C32, one fixed tree) | DIFFER, exit 1, exactly that count flagged | REFUSED |
| Perturbed `stream_sha256` (freq_matched_3) | DIFFER, exit 1 | REFUSED |
| `--tie desc` | DIFFER, exit 1 | REFUSED (verdict, tie rule) |
| Wrong selection (`--labels`, 18 other checkpoints) | AGREE on what it checked | REFUSED (selection, no `--registered-selection`, coverage) |
| Wrong run (a real second simulate run analysed with the first file) | n/a | REFUSED ("did not read this simulate run") |
| v1 script (actual stream only, no FM) | AGREE | **ACCEPTED** (MINOR-R1) |
| Study record edited after an AGREE check | n/a | **ACCEPTED** (MINOR-R2) |
| **18 registered checkpoints, full size (32,768 queries), no `--allow-small`** | **AGREE, exit 0, 249 s** (13.0–14.6 s each; 240 or 270 cache configurations each) | ACCEPTED with `allow_small=False`; REFUSED with a wrong simulate or trace run ID |

Run time for 18 checkpoints of full-size synthetic work is **249 s against the 1,800 s cap** (margin 7.2). Real traces are more concentrated than these synthetic traces, which mostly lowers the cost of my heap-based LRU. The gate's expectations are reasonable. I bent nothing in my script to satisfy them.

## 5. New findings

### MINOR

- **R1. The gate does not require frequency-matched coverage.** A v1 run (actual stream only) passes `check_independent_comparison`, but item 13 says the independent simulator covers the FM stream. *Fix (optional, implementer):* also require `data["version"] >= 2`, or each checkpoint's `cache_configurations_compared` to contain `freq_matched_1..3`. *Procedural alternative:* the runbook names v2 by its sha256 `fc522698…` (my output records `script_sha256`).
- **R2. The gate is not bound to the content of the records it vouches for.** It matches run IDs by path suffix only (`p7a_study.py:572-577`). A study record edited after the check is not detected, and neither is a copy of the workers folder elsewhere with the same last three path parts (my negative-control copies used this). v2 now records `study_result_sha256` per label. *Fix (optional):* the gate compares those hashes with `results/…/simulate/<id>/workers/<label>.result.json`. This needs deliberate tampering, so it is not a safety-of-results issue in an honest run.
- **R3. The item 8 step 3 wording does not pin a unique stream.** It says "take the later position of x", but it does not say which x when a query holds two different duplicated slots, or which later position when x appears three or more times. After the deal, 1,367 and 1,340 of 32,768 queries are such cases on a heavy synthetic histogram. An equally literal reading (the last occurrence of the smallest duplicated slot) gives a different `stream_sha256` (`item8_wording.txt`). The implementation pins the reading in code (`p7a_core.py:365-366`: the later position of the first repeated entry met reading left to right), and so do my script and `check_exact_null.py`. Statistically the readings are equivalent. *Fix:* the run record cites that docstring as the operative definition (wording only, PENDING LEAD REVIEW).
- **R4. The repair can dead-end on feasible histograms, and one test passes by seed luck.** The docstring `p7a_core.py:417-418` implies only infeasible histograms fail. `test_p7a_sim.py:375-386` says the repair "must still finish" on the k = 8 tight histogram, but at Q = 128 it fails for 144/300 seeds; it passes only because 91301/index 0 happens to succeed. This has no effect on the registered run (the §2 bound holds for 81/81). *Fix:* correct the docstring and the test comment, or accept as is.
- **R5. Tests import files from the review folder.** `tests/test_p7a_sim.py:321-324, 432-452, 496-510` load `docs/reviews/p7a-preflight-2026-11-13/check_exact_null.py` and `independent_sim.py`. The freeze commit must include this review folder, or the tests fail in CI. After the freeze, those two files are frozen too.
- **R6. Trace-stage timing is still unprojected (earlier minor 8).** A breach of the 900 s cap stops the trace stage and needs `--supersede` with a recorded reason.
- **R7. Budget overhead is stated but not measured (earlier minor 7).** My estimate is a margin of about 3.1–3.6, not the reported 4.2.

### NOTE

- **R1.** `p7a_stage.py:82-83` says `results/` is git-ignored. It is tracked (5,702 tracked files; only `/experiments/` and `/data/` are ignored). The behaviour is still correct, because new untracked files under `results/` are deliberately not hashed.
- **R2.** The step 4 direction (`stream[p] = rows[order[p]]`) is the natural reading. My script uses it independently.
- **R3.** The budget is now faster (projected 858 s) than in my first audit (1,204 s). The torch multinomial was replaced by about 0.13 s of standard-library generation, and the earlier measurement may have run under load. This is not an issue.
- **R4.** The dry-run stand-in independent-check file (`p7a_study.py:769-791`) is accepted only with `allow_small`, which is set only for dry runs (`:613`), so it cannot satisfy a registered analyze.

## 6. Real-data paths that remain unexercised, and what a failure would do

| Path | If it fails during the registered run |
|---|---|
| `common.load_real_cell` in a trace worker (locate, hash verification, strict restore) | worker `error` → trace stage `failed`; partial records kept; rerun needs `--supersede --reason` |
| Bitwise NLL replay of 81 real checkpoints | `GateViolation` → trace stage stops (registered stop) |
| `calibration_slice` on the real 4,096-chunk pool | `ValueError` → worker error → stage failed |
| P5 histogram and unique-count reproduction (trace worker and sim worker) | `TraceIntegrityError` → registered stop |
| Real trace-stage time against 900 s, real RSS against 2 GiB | cap or RSS breach → stage failed; unexecuted rows kept |
| FM generation on the 81 real histograms (registered seeds) | cannot dead-end (proof above); any count or distinctness violation → `InvariantError` → simulate stage stops |
| My v2 on real traces (format, `trace_dir == label`, P5 comparison) | missing input → exit 2; any difference or integrity problem → exit 1 and DIFFER → the gate refuses analyze (registered stop) |
| Analysis on 81 real records | only fabricated records have been analysed; a schema mismatch would raise → analyze `failed` |
| Real repository state at the freeze (`git_dirty`, HEAD) and the analysis guard | a commit between simulate and analyze → analyze refused (rerun after restoring HEAD) |

## What I did not check

- Anything on real checkpoints, real traces or real P5-derived streams: replay, real timings, real RSS, `loader-smoke`.
- L-RAND, the order- and context-shuffled streams, tree key reads, branch locality and the bootstrap were not recomputed independently. They were reviewed by reading in the first audit, and the related code did not change here.
- The full test suite outside `tests/test_p7a_*.py`.
- The descriptive tables of the analysis were not recomputed independently. Only the criteria and outcomes were.
- Whether earlier test files changed between my two audits: only by hash for the source files I had recorded, and by mtime for `tests/test_p7a_trace.py`.

## Recommendation

**READY TO FREEZE.** Conditions, all procedural and needing no code change:
1. The freeze commit includes `docs/reviews/p7a-preflight-2026-11-13/` (independent_sim.py v2 `fc522698…` and check_exact_null.py), because the tests import them.
2. Nothing is committed between the simulate and analyze stages.
3. The independent check runs after simulate completes and before analyze, and writes outside `src/`, `tests/`, `configs/`, `docs/decisions/` and `results/`.

MINOR-R1 and R2 (gate hardening) and R4 (docstring and test comment) are optional. If the implementer changes any P7-A file for them, I should re-check that diff before the freeze. R3 needs only a sentence in the run record.

**Post-simulate independent check (run from the repository root, after `simulate` has completed and before `analyze`; nothing else running in the repository):**

```sh
uv run --locked --extra pilot python -I docs/reviews/p7a-preflight-2026-11-13/independent_sim.py \
  --trace-root experiments/<P7AT-trace-run-id>/traces \
  --trace-records results/p7a-2026-11-13/trace/<P7AT-trace-run-id>/checkpoints \
  --sim-workers results/p7a-2026-11-13/simulate/<P7AS-simulate-run-id>/workers \
  --p5-results results/p5-2026-11-13 \
  --registered-selection \
  --out docs/reviews/p7a-results-audit-<YYYY-MM-DD>/independent_sim_registered.json
```

Exit 0 and `VERDICT AGREE` are required. Any other exit is the clarification-7 stop. Then run:

```sh
uv run --locked --extra pilot python -m arborlm.p7a_study analyze \
  --independent-check docs/reviews/p7a-results-audit-<YYYY-MM-DD>/independent_sim_registered.json
```

Commit the output folder only after analyze has finished.
