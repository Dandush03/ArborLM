# P9-II pre-freeze re-check (ADR-0019 revision 4) — 2026-11-15

- **Auditor:** Claude Opus 5.5 (`claude-opus-5-5`), arbor-auditor role. I did not write the code checked here.
- **Scope:** the fixes in `2e47e16`, checked with `git diff 927bdbf 2e47e16 -- studies/p9ii tests`; the lead's `results/p9ii-calibration-2026-11-15/CORRECTION.md`; and rehearsal 2 with its real-size gates in `results/p9ii-rehearsal2-2026-11-15/` (commit `043e107`).
- **Worktree:** branch `claude/adr-0019-p9ii` at HEAD `043e107`.
- **Environment:** as in AUDIT.md. That is macOS-27.2.1-arm64, Python 3.12.14, torch 2.8.0, `uv run --locked` or `.venv/bin/python` with `PYTHONPATH=.`.
- **Seeds:** all generation and training I ran used P9-II test seeds (910001–919999). The calibration snapshots were only scored, never trained.
- **Not done:** no registered stage, no generation of registered or reserve data, no edit of any existing file, no commit.
- **Location:** scripts are in `recheck/` and outputs in `recheck/outputs/`. Failed attempts are kept beside them.
- **Status:** independent engineering and mathematical evidence. It is not Astra validation and not a human approval. **Astra review: NOT_PERFORMED.**

## Verdict

**READY TO FREEZE.** Two caveats come with it. Neither blocks the freeze, and neither is a code defect.

- **(i) PENDING LEAD REVIEW, the A4 budget consequence.**
  - The registered §10 rule charges A4's entire anneal at its k_0 rate. Under that rule every Stage 2 configuration that contains A4 fails 2× Budget B, with doubled projections of 11,561–14,660 s.
  - The rule is the ADR's own text, and the code applies it correctly.
  - A tighter bound is still conservative if the cost per update does not decrease with k: it charges the first half of the anneal at the k_0 rate and the second half at the midpoint rate. Under that bound every A4 configuration fits, doubled at 7,612–10,711 s.
  - So the predicted NOT RUN — BUDGET comes from the projection rule, not from what A4 will actually cost.
  - The lead has accepted this consequence. Changing the rule would be a budget amendment, which falls to the human lead.
- **(ii) The freeze record must contain the items listed in section 5.**

Findings from the pre-freeze audit: B1 fixed. M1–M7 fixed. m1–m15 fixed or answered, as tabled below. New findings: no blocker, no major, three minors (n1–n3). The P9-II tests pass: 162 passed (r9).

---

## 1. The findings, one by one

| Finding | Status | Evidence |
|---|---|---|
| **B1** per-task overhead | **Fixed.** `Rate.task_overhead_seconds` is taken from the rehearse manifest and added once to each training task and once to each evaluation task. The Stage 1 evaluation cap is 178.5 s (projection 89.2 s). | r8 reproduces every projection with overhead from the raw records. Overhead measures 1.53–1.91 s, and there are 0 mismatches against `projection.json`. |
| **M1** projection at calibrated values | **Fixed.** `rehearse` refuses without `--calibration`. The projection carries `hyper` and `calibration_sha256`. `verify_plan` refuses on any mismatch. | r8: hyper equals the calibration's, and the sha256 equals `ad5d7ee2…`. The rehearsed A4 widths are k_0 = 2,048 and mid = 128 at 16,384 slots; k_0 = 512 and mid = 64 at 4,096. |
| **M2** memory with evaluation peaks | **Fixed.** The peak is the maximum of the training, sampled, evaluation and pool-task peaks, computed per stage. The registered stage and the gate refuse with NOT RUN — BUDGET (MEMORY). Evaluation chunking brings the 65,536-slot peak down to 1.00 GiB. | r8 peaks: Stage 1 0.474 GiB, Stage 2 0.769, Stage 3 0.999. Doubled, these are 0.95, 1.54 and 2.00 GiB, all within 3 GiB; six workers doubled come to 11.98 GiB or less, within 24. Chunked evaluation gives the same numbers (section 2). |
| **M3** caps per configuration | **Fixed.** `caps_table` has one entry per Stage 2 configuration (16) and per Stage 3 arm (4). `stage_caps_for` reads the gate record. A configuration with no entry is refused. | r2 shows that every configuration finds its cap. Stage 3 with A2 or A4 has no entry and is refused, which is correct because it can never be selected. r7 does the lookup from a gate record in the clone. |
| **M4** per-draw gates | **Fixed.** `require_draw_plan` checks that the plan exists, that `ok` is true, and that G1 passed for every seed set it names. It applies to registered train, evaluate, gates and the seeds lookup. The registered gates compute G2 for all 14 draws at their own size, and `assess` returns NOT_INTERPRETED on any per-draw G2 failure. | r7: a plan with `ok` false is refused, and a reserve with failed G1 is refused. r2 R-c: a G2 failure on draw 7 gives NOT_INTERPRETED (G2 failed on draw 7). |
| **M5** reserve substitution | **Fixed.** `generate-*` stages are excluded from the failed tasks. A draw plan that is not `ok` makes the result INCOMPLETE. A replacement prints as REPLACED BY RESERVE k. | r2 R-a (failed generate task plus a replacement) completes as row 4, and RESULTS.md prints REPLACED BY RESERVE 1. R-b: an exhausted plan gives NOT_INTERPRETED (INCOMPLETE). r7: the analysis in the clone prints `{'5': 'REPLACED BY RESERVE 1'}`. |
| **M6** readings without a COMPLETE Stage 2 | **Fixed.** Row 3 without a COMPLETE Stage 2 prints B–G as NOT TESTED AT 16,384. Nothing is carried forward unless Stage 2 is COMPLETE. | r2 R-f: row 3, B–G NOT TESTED AT 16,384, Stage 3 NOT RUN — BUDGET. R-d: INCOMPLETE gives no carry-forward. r6 on 1,000 random registries: every difference from the old code is one of the intended ones. |
| **M7** freeze order | **Fixed** by `studies/p9ii/freeze/README.md` and `launch/generate.sh`. Generation, G1 and the draw plan come before the freeze commit. `verify_plan` checks the run dir, the draw plan, all 16 data manifests, the cap table, the calibration and the projection. | r7: the full procedure in a clone, with fabricated manifests. An ADR edit after the freeze is refused. |
| m1 | Answered by CORRECTION.md. The README is left as written. | — |
| m2 | Fixed by M1. | — |
| m3 | Fixed. `last_query` is set to None after the loss is formed. Numbers are unchanged (section 2). | r1 |
| m4 | Fixed. `g6_after_training` trains every learned arm, then changes the injection and the fact table. It requires identical logits, an identical rebuild from `state_dict`, and no stray tensors. | `gates_rehearsal_set5.json`: g6 trained passed. |
| m5 | Fixed. Stage 3 inherits NOT RUN — BUDGET or INCOMPLETE from Stage 2, and the gate writes INCOMPLETE. | r2 R-e, R-f, R-d |
| m6 | Fixed. A missing manifest now gives INCOMPLETE, not BUDGET. | code |
| m7 | Fixed. `annotation_lines` prints NEGATIVE CONTROL FAILED, SUPERVISION-DEPENDENT, ADDRESS RECALL/STABLE, the categories, MID-SCHEDULE, d(A2 vs A1), r of A6, the dense comparison and SCALE PROBE. The two medians are named apart. | r2 RESULTS.md checks |
| m8 | Fixed. The train record carries `cpu_seconds` and analytical counts labelled as analytical. The projection carries `cost_differences`. | r8 / `projection.json` |
| m9 | Fixed. The denominator is the evaluated cells only. | r6: H19-C follows this change in 4 of 1,000 registries, as intended. |
| m10–m15 | Fixed: docstring; `generate.sh` added; a single cap source (`--caps` must be the frozen file, whose hash is in the plan); probe hardening with an assertion; tie key `first_success_key`; A2 parameter labels. | r7 (the `--caps` refusal), r5 (the tie key) |

## 2. Can any number a cell computes differ? No.

**What changed.** `model.py` is identical to the calibration commit `3d779e1`. So are `studies/p9`, `studies/p9i`, `src/`, `configs/`, `uv.lock` and `pyproject.toml`.

The training step changed in only two ways. `last_query` is set to None after the auxiliary loss is formed. The train record gains `cpu_seconds`, analytical counts and labels.

Evaluation changed in two ways:

- The selection runs in smaller blocks of queries (`chunk_elements` of 2^20 instead of 2^24) inside `eval_chunking`.
- G5 runs in blocks of 128 corpus rows.

`build_probe` gained a skip for facts at or above the trained count, plus an assertion. Neither can fire on a stream whose probe facts are all trained. That matches the calibration records exactly (r5).

**Evidence (r1, `r1_numbers_unchanged.py`).** The calibration-commit package is extracted with `git archive 3d779e1` and imported beside HEAD's. Both run on test seeds with the real backbone and real-size data.

- **Training, 4,096 and 16,384 slots, all nine arms.** Each cell runs 192 updates. At 4,096 this covers A2's switch at 96, A4's anneal to 128, and A5-C's centre. Every parameter, buffer, per-update record and diagnostics field matches bit for bit, timing and memory excepted. Result: ALL IDENTICAL at both sizes.
- **Evaluation, the whole eval record except identity and environment.** The calibration-commit `evaluate_readout` is compared against HEAD's chunked `evaluate_readout`, and HEAD's chunked against HEAD's unchunked.
  - All nine arms at 4,096: ALL IDENTICAL.
  - All nine arms at 16,384: ALL IDENTICAL.
  - A0, A1, A5-C, A5-D, A6 and A7 at 65,536 (the arms Stage 3 can run): ALL IDENTICAL.
  - The A6 cells (256 distinct top-1 slots at 16,384 and 65,536; 243 at 4,096), A5-D at 65,536 (470 distinct) and the A1, A2 and A5-D cells at 4,096 (156–361 distinct) exercise non-degenerate selections. Most other short-trained cells are collapsed.
- **Calibration under HEAD's code (r5).** The 22 calibration snapshots are scored with HEAD's `calibration_accuracy`, plain and inside `eval_chunking`, and with HEAD's probe. The maximum absolute difference is 0 against the records and against my independent re-scoring (b2).
- **Rule checks.**
  - The 20,000-table enumeration (c2, seed 20261116) against HEAD's `classes.py` gives 0 mismatches on every rule. Rows 2–8 are all hit, row 8 five times.
  - The old-against-HEAD `analyze_study` differential (r6, 1,000 random registries, seed 11) differs only in the intended ways:
    - H19-B–G NOT TESTED AT 16,384 in row 3 without a COMPLETE Stage 2: 265 registries;
    - H19-C following the new SUPERVISION-DEPENDENT denominator: 4;
    - the SUPERVISION-DEPENDENT entry itself: 240;
    - carry-forward withheld when Stage 2 is not COMPLETE: 198;
    - Stage 3 status: 230.
  - Nothing differs in classes, paired labels, draw tables or outcomes. The v1 run of r6 flagged one "unintended" case. My classifier was too coarse: the case was the H19-C/denominator effect. The v1 output is kept.

## 3. The calibration selection under the corrected tie rule

The rule is recomputed from the raw diagnostics with HEAD's `first_success_key` and `select_value`, and separately with my own reading of the corrected rule (r5). Both give the same values:

| Arm | Selected | How |
|---|---|---|
| A1 | λ = **1.0** | key (0, 2,688) against (0, 2,752) |
| A2 | U_pre = **2,048** | primary: 0.124 against 0.037 |
| A4 | k_0 = **N/8** | primary: 0.521 against 0.123. For k_0 = N the key is now (1, 7,680), because draw 4 succeeded at 7,680. That does not matter, since the primary criterion decides. |
| A5-D | μ = **1.0** | key (0, 2,464) against (0, 2,752) |

**The selection is unchanged.**

## 4. Rehearsal 2

Recomputed in r8 with plain json.

- **Whitelist.** No violations in 60 records. The only loss-like key is the boolean `loss_finite`. Every record has seed set rehearsal-5.
- **Binding.** `projection.json` has sha256 `6895b920b3b6869acbf4745cf1e42d249d217d01139cf4b4b058c16c8b162936`, identical in `results/` and the run dir. Its `hyper` equals the calibration's, and its `calibration_sha256` equals `ad5d7ee2…`.
- **Arithmetic.** I reproduced every projection exactly, task overhead included:

| Stage | Projected | Doubled | Budget remaining |
|---|---|---|---|
| Stage 1 | 2,071.7 s | 4,143.3 s | Budget A: 13,866.4 s |
| Stage 2, configurations without A4 | 1,153.8–3,519.1 s | 2,307.7–7,038.2 s | 10,800 s |
| Stage 2, configurations with A4 | 5,780.5–7,330.0 s | 11,561.0–14,660.1 s | 10,800 s, so NOT RUN — BUDGET |
| Stage 3 | 315.6–720.6 s | 631.2–1,441.2 s | what Stage 2 leaves |

- **Memory.** As under M2 above.
- **The gates at real size on set 5 all passed.** That includes G6 after training.
- **The registered gates do more work than the rehearsal-mode measurement.** They compute G2 for all 14 draws.
  - r3 measures it at about 8.2 s on top of the 8.3 s of the rehearsal-mode gates. Doubled, that is about 33 s, within the 60 s floor of the gates cap.
  - At real log size (148 learned cells, 32,768-line update logs at Stage 2), analysis and report take 8.1 s and under 0.1 s (r4). Doubled, they are well within the 60 s floor.

**Is the A4 consequence correctly derived?**

Yes, under the registered rule. Stage 2 then never runs when A4 is one of the advancing arms. The other advancing arm loses its Stage 2 as well, because no reduced Stage 2 exists.

The driver and the analysis handle this without a perverse label:

| Case | What is printed |
|---|---|
| **R-e:** A4 and A5-D RELIABLE, A0 not | The gate record shows `advancing` [A5-D, A4], NOT RUN — BUDGET, projection 6,547.6 s against 10,800 s remaining. Outcome: "ADDRESSING-RELIABLE AT 4,096; 16,384 NOT RUN — BUDGET: A5-D (LABEL-FREE), paired against A0 at 4,096: IMPROVES ON A0 (not read as a failure to scale)". A4 and A5-D print RELIABLE at 4,096. Stage 3 is NOT RUN — BUDGET. Nothing is carried forward. H19-D and H19-G are read at 4,096, as §8.6 prescribes outside row 3. |
| **R-f:** A0 and A4 RELIABLE | Row 3, with B–G NOT TESTED AT 16,384 and Stage 3 NOT RUN — BUDGET. |

The registered rule, though, overstates A4's cost. k(t) exceeds 512 for only 25% of the anneal and exceeds 128 for only 50% of it. The measured rates are 0.137 s/update at k = 2,048, 0.017 at k = 128 and 0.013 at k = 8.

**PENDING LEAD REVIEW / human lead.** r11 recomputes with the tighter bound described in the Verdict: half the anneal at the k_0 rate, half at the midpoint rate, valid if cost does not decrease with k. Under it, A4 alone is 3,806 s (doubled 7,612 s), and A4 with another arm is 4,555–5,356 s (doubled 9,110–10,711 s). All fit.

If the lead keeps the rule, the report should state that a Stage 2 not run because A4 advanced reflects the projection rule. Changing §10 before the freeze is a budget decision for the human lead.

## 5. The freeze record the lead must write in ADR-0019 §16

It goes inside the single freeze commit, together with `plan.json` and `stage_caps.json`. The driver refuses if the ADR changes after that commit, as r7 shows.

1. **Code identity.**
   - The commit the generation ran at, with the statement that `studies/`, `configs/`, `src/`, `tests/test_p9ii_*`, `uv.lock` and `pyproject.toml` are unchanged between it and the freeze commit.
   - `core.code_identity()`: `source_sha256`, `config_sha256`, `frozen_source_sha256`. Leave out `spec_sha256`, because it would hash the record itself.
   - Per-file sha256 of `studies/p9ii/*.py`, `studies/p9ii/launch/*.sh` and the imported `studies/p9` and `studies/p9i` modules.
2. **What changed since calibration.**
   - The list of files changed since `3d779e1`, with the statement and evidence that no computed number differs: this RECHECK §2 (r1, r5) and `tests/test_p9ii_replay.py`.
   - `model.py` is identical.
   - The training step differs only in `last_query = None` and new record fields. Evaluation differs only in blocking, which is bit-identical at 4,096, 16,384 and 65,536.
3. **Calibration.**
   - Run dir `experiments/P9IIC-20261115T071159540788Z-1a93c3ded92e40628c2abb9bd4235188`.
   - Record sha256 `ad5d7ee29ccd3f0be8b9875afdd957f35901e0d80f4babca6917916d0cf552cf`.
   - Selected values: λ = 1.0, U_pre = 2,048, k_0/N = 1/8, μ = 1.0, confirmed under the corrected tie rule.
   - Pointers to `CORRECTION.md` and to the A2 decision: kept as registered, with the reason.
4. **Rehearsal and projection.**
   - Run dir `experiments/P9IIH-20261115T082413529266Z-cafbe1b47e1d478ba3c2882732830ffa`.
   - `projection.json` sha256 `6895b920b3b6869acbf4745cf1e42d249d217d01139cf4b4b058c16c8b162936`.
   - The Stage 1 decision (2,071.7 s, doubled 4,143.3 s, within the Budget A remainder at freeze time).
   - The Stage 2 table of 16 configurations and the Stage 3 table of 4 arms.
   - Memory per stage.
   - The lead's statement on the A4 consequence and on this re-check's bound.
5. **Cap table.**
   - `stage_caps.json` and its sha256.
   - The `caps` command exactly as run, with the measured gates, analysis and report walls and the 60 s floor.
   - The Stage 1 train and evaluate caps.
6. **Gates on rehearsal seeds.**
   - `experiments/P9IIG-rehearsal-gates2-20261115T082352Z`: G1, G2, G4, G5 and G6 (including G6 after training) passed at real size.
   - The registered gates run first through `gates.sh`, with G2 for all 14 draws.
7. **Data identities.** These are produced by `launch/generate.sh <run-dir> <code-commit>` before the freeze commit.
   - The registered run directory.
   - For each of the 16 seed sets (`p9ii-draw-1`…`14` with bases 190001…191301, and `p9ii-reserve-1` and `-2` with bases 191401 and 191501): the name, the base seed, the sha256 of its `data_manifest.json`, the stream hashes and the G1 result.
   - `draw_plan.json` and its sha256, `ok` true, and every replacement as REPLACED BY RESERVE k.
   - The statement that generation and G1 are not an observation of a registered seed by a model.
8. **`plan.json`.**
   - The contents: calibration {path, sha256}; projection {path, sha256}; `stage_caps_sha256`; `run_dir`; `draw_plan` {sha256}; `data_manifests` for all 16 seed sets.
   - Its own sha256.
9. **Ledgers.** Budget A charged at freeze time, which includes generation; Budget B at 0 s.
10. **Launch commands.** The exact eight commands, in order: `sh studies/p9ii/launch/{gates,stage1,stage1_gate,stage2,stage3_gate,stage3,analysis,report}.sh <run-dir> <freeze-commit>`.
11. **The lead's five conditions**, each with its evidence, as below.
12. **Status lines.** "Astra review: NOT_PERFORMED"; the delegation text; and "not a human approval".

### The five conditions now

| # | Condition | My judgment |
|---|---|---|
| 1 | Spec review clean | Done earlier (CONFIRM.md and revision 4). |
| 2 | Implementation audit clean | **Holds.** B1 and M1–M7 are fixed and verified. No new blocker or major. The new minors n1–n3 do not affect any registered number or rule. |
| 3 | 2× headroom shown | **Holds under the registered rule.** Time: Stage 1 at 4,143 s against 13,866 s; every Stage 2 configuration without A4; Stage 3 from what Stage 2 leaves. Configurations with A4 do not fit, and by §10 they print NOT RUN — BUDGET, which the lead has accepted (see the A4 caveat in the Verdict). Memory: 2.00 GiB or less doubled per worker, and 11.98 GiB or less for six workers doubled. |
| 4 | Nothing changed after calibration except the calibrated values | **Holds for every computed number.** The code changed only in budget, driver, analysis, report, diagnostics recording, the probe guard and evaluation blocking. None of these can change a training update, a loss, a selection, an accuracy, a probe value or a rule input: training and evaluation are bit-identical to the calibration code for all nine arms (§2). What did change after calibration are the rules the lead applied from my audit (tie key, SUPERVISION-DEPENDENT denominator, row-3 readings, carry-forward, Stage 3 status). Each is a correction toward the ADR text, verified in r6, and none moves a threshold. |
| 5 | No registered seed observed | **Holds.** `experiments/` has no `p9ii-draw-*` or `p9ii-reserve-*` directory and no P9-II record with a seed in 190001–191599. Every run of mine used test seeds. The clone used fabricated stand-in manifests. |

## 6. New findings

- **n1 (minor).** `assess` and the Stage 3 status mapping cover NOT RUN — BUDGET and INCOMPLETE. They do not cover NOT RUN — BUDGET (MEMORY) at Stage 2. If Stage 2 were ever refused for memory, Stage 3 would print NOT RUN — NO ARM PASSED. The measured peaks make this very unlikely. Fix: add `budget.NOT_RUN_MEMORY` to the tuple in `analysis.analyze_study`.
- **n2 (minor).** If `stage1_gate.sh` is launched before Stage 1 has finished, it writes `stage_gate_1.json` once, as INCOMPLETE. Gates are computed once, so that record could not be replaced. The launch order in the freeze README prevents this. State it in the freeze record.
- **n3 (minor).** The caps of analysis, report and gates rest on the 60 s floor, not on 2× a time measured in registered mode. My measurements fit with margin: 8.1 s, under 0.1 s, and about 16.5 s respectively. Record those measurements in the freeze record as the basis for the floor.

**Correction about my own earlier review.** `CORRECTION.md` rightly notes that the A2 moment reset was added in revision 2 on my own specification-review recommendation (REVIEW.md M3), and that my diagnostic later showed it produces a worse optimizer artifact. I record that the recommendation was mine.

## Commands (all from the worktree; S = session scratchpad, E = `experiments/`)

| Script | Purpose |
|---|---|
| `recheck/r1_numbers_unchanged.py E S/old/oldpkg S {train,eval} {4096,16384,65536} <arms>` | Old against HEAD training and evaluation (the old package is from `git archive 3d779e1 studies/p9ii`). Two failed attempts are kept: zsh word splitting, and the old package's repository root. |
| `recheck/r2_synthetic_registry.py S results/p9ii-rehearsal2-2026-11-15/projection.json` | Synthetic full-registry scenarios. |
| `recheck/r3_registered_gates_time.py E` | Time of the per-draw work in the registered gates. |
| `recheck/r4_analysis_time.py S <calibration A2 cell dir>` | Analysis and report time at real log size. |
| `recheck/r5_calibration_head.py <calibration run> E outputs/b2_rescore_calibration.json` | Calibration under HEAD's code; selection under the corrected tie rule. |
| `recheck/r6_classes_differential.py S/old/oldpkg 1000 11` | Old against HEAD analysis on random registries. The v1 run (400 registries, seed 7, coarse classifier) is kept. |
| `recheck/r7_freeze_clone.sh <worktree> S E <projection> <calibration>` | Freeze procedure and driver paths in a throw-away clone. |
| `recheck/r8_rehearsal2.py <rehearsal2 run> <calibration.json> <ledger_A.json>` | Rehearsal 2 recomputed. |
| `recheck/r11_a4_bound.py <rehearsal2 run> <calibration.json>` | A4 projection under the tighter bound. A failed attempt is kept. |
| `c2_classes_enumeration.py 20000 20261116` | Run against HEAD; output in `recheck/outputs/r10_c2_against_head.txt`. |
| `uv run --locked pytest tests/test_p9ii_*.py -q` | Test suite: 162 passed (`recheck/outputs/r9_pytest_p9ii.txt`). |
