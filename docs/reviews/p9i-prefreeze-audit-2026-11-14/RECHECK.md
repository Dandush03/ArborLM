# P9-I (ADR-0017 Part I) — re-check of the pre-freeze fixes (commit `dd8b205`)

- **Auditor:** Claude Opus 5.5 (`claude-opus-5-5`). I wrote `AUDIT.md` in this folder (calibration CONFIRMED; implementation READY AFTER M1, M2, M3). I did not write the fixes (implementer: Sonnet 5.5, commit `dd8b205`) or any code under `studies/p9i/`.
- **Date:** 2026-11-14. **Worktree:** `.claude/worktrees/arborlm-consolidation-experiment-2b31c1`, branch `claude/adr-0017-design`, HEAD `dd8b20587ace7ff21652b37779f3cc760ed272ef`. Diff reviewed: `git diff 85d6c1b dd8b205 -- studies/p9i tests`.
- **Status:** independent engineering and mathematical evidence. Not Astra validation, not human approval, not decision 2. **Astra review: NOT_PERFORMED.**
- **Environment:** Apple M5 Max, macOS 27.2.1 arm64, Python 3.12.14, torch 2.8.0 CPU float32, `uv run --locked`, `PYTHONPATH=.` from the worktree root. Run directories read from `/Users/daniellaloush/dandush03/ArborLM/experiments/`.

## What I ran

| Command (from the worktree root) | Output | Result |
|---|---|---|
| `uv run --locked ruff check .` | — | All checks passed |
| `uv run --locked mypy src/arborlm supplements/p8s studies/p9 studies/p9i` | — | no issues in 121 source files |
| `uv run --locked pytest -q -p no:cacheprovider` | — | 1731 passed, 4 skipped, 3 warnings (510 s); also `tests/test_p9i_prefreeze.py tests/test_p9i_stages.py tests/test_p9i_classes.py` alone: 47 passed |
| `PYTHONPATH=. uv run --locked python docs/reviews/p9i-prefreeze-audit-2026-11-14/r1_recheck_fixes.py $EXP/P9IC-20261114T225847947431Z-b0cf703a0d7c4f7ab8f308c3de6ddf78` | `outputs/r1_recheck_fixes.txt` | 31 checks, 0 failed |
| `… r2_freeze_plan_preconditions.py <throw-away clone at dd8b205>` | `outputs/r2_freeze_plan_preconditions.txt` | as below |
| `… a4_arm_forward.py $EXP` (unchanged audit script, at HEAD) | `outputs/r3_a4_arm_forward_at_dd8b205.txt` | identical to `a4_arm_forward.txt` except one NumPy-missing warning line on stderr |
| `… a5_classes_enumeration.py` (unchanged, at HEAD) | `outputs/r3_a5_classes_enumeration_at_dd8b205.txt` | byte-identical to `a5_classes_enumeration.txt` (20,000 tables, 0 disagreements) |
| `… a3_rehearsal_replay.py $EXP/P9IH-20261114T231255388625Z-8c6758d15894479b840ff5b5afd93630 $EXP <fresh scratch> N-n4096-b101-o301-s1801 BB-n4096-b101-o301-s1802 A4E-n16384-b101-o301-s1801` | `outputs/r3_a3_replay_at_dd8b205.txt` | 3/3 model.pt and optimizer.pt bit-identical to the rehearsal (trained at `939b4bf`) |

`$EXP` = `/Users/daniellaloush/dandush03/ArborLM/experiments`. Not run: no registered stage, no registered-seed data (182001+), no training or evaluation beyond the 3 × 64-update rehearsal-draw-2 replay (tensor comparison only, no loss or accuracy read). No existing file edited, nothing committed.

**Failed checker attempt (kept, my mistake):** `outputs/r3_a3_replay_at_dd8b205_attempt1_FAILED_auditor_scratch_reuse.txt` — I pointed the replay at a scratch directory that still held my earlier audit's replay output, and `train._publish` correctly refused to overwrite (`FileExistsError`). Re-run in a fresh directory.

## 1. M1 and M2 — FIXED

`stages.assess` (new, pure) replaces the inline logic in `work_analyze`. Read, then exercised with my own synthetic tables (`r1`, part a; my table builder from `a5`, not the implementer's test helper):

| Case | status | interpretable | outcome | classes |
|---|---|---|---|---|
| complete, gates pass | COMPLETE | True | BB (step 1) | derived |
| missing BB-0 cell (complete matrix gives MODEL_STORES_FACTS) | INCOMPLETE | False | NOT_INTERPRETED (INCOMPLETE), missing label listed | none |
| one BB seed missing at 65,536 (previously moved selection to A4) | INCOMPLETE | False | NOT_INTERPRETED (INCOMPLETE) | none |
| missing B102 replicate | INCOMPLETE | False | NOT_INTERPRETED (INCOMPLETE) | none |
| G2 failed | COMPLETE | False | NOT_INTERPRETED, "G2 failed" | descriptive |
| G1 failed | COMPLETE (not ENGINEERING_FAIL) | False | NOT_INTERPRETED, "G1 failed" | descriptive |
| G1 not recorded | COMPLETE | False | NOT_INTERPRETED, "G1 not recorded" | descriptive |
| LEAKAGE flag | COMPLETE | False | NOT_INTERPRETED, cell named | descriptive |
| G4 defect | ENGINEERING_FAIL | False | NOT_INTERPRETED | descriptive |
| no gates record | INCOMPLETE | False | NOT_INTERPRETED (INCOMPLETE), "gates record" | none |
| failed task + G2 + LEAKAGE | INCOMPLETE | False | NOT_INTERPRETED (INCOMPLETE), both reasons kept | none |
| R1 < 0.5, gates pass | COMPLETE | True | INCONCLUSIVE (step 0 unchanged) | derived |

This matches the lead's ruling: any failed G1/G2/LEAKAGE/G4 → NOT_INTERPRETED with reasons; G1/G2 failure is not ENGINEERING_FAIL; ENGINEERING_FAIL only from G4 defects; missing cells derive nothing and the denominator is not reduced (the analyze worker always iterates the full registry: `--only`/`--group` are not forwarded by `common_args`, so a worker cannot be given a subset). `report.render_markdown` prints **NOT INTERPRETED** with the reasons / missing labels above the status and selection (r1 part b). `analysis.json` carries `interpretable`, `gate_reasons`, `g4_passed`.

Registered `train` refuses unless `gates.json` exists with `g1_passed`, `g2_passed`, `g4_passed` all `True` (checked in both `cmd_train` and the worker `work_train`). r1 part c: no record, G2 False, G1 None, G4 False → each REFUSED; all True → accepted. This closes my "PENDING LEAD REVIEW" on M2 as the lead ruled (a gate failure before training stops the run).

## 2. Minors — applied

| Minor | Check | Result |
|---|---|---|
| 1 registered needs `--calibration`, refuses `--updates` | `updates_for` (r1 c) | both REFUSED; U from the audited record = 8,192 |
| 1 calibration binding | launch hash passed to every worker (`--calibration-sha256`); `cmd_train` writes `calibration_binding.json`; `check_binding` in evaluate and analyze; binding written into train, eval and analysis records | wrong launch hash REFUSED; evaluate before binding REFUSED; binding with other U REFUSED; a different file (one extra byte) REFUSED; equal → accepted. Binding of `results/p9i-calibration-2026-11-14/calibration.json` = `{sha256 087bf0b5885859a78781e32cb0e0ce8d3b154dfcc471965cf82f06718c509f44, U 8192, failed sizes {}}`; the run-directory copy has the same hash |
| 2 data manifest for evaluation | `work_evaluate` now `require_manifest=not dry and registered` (read) | applied |
| 3 template pool | `study_data` raises in registered mode if `study.pool != p9core.TEMPLATE_POOL` (read; also in `work_generate`'s path) | applied |
| 4 report columns | `_rows_cells`: `eta_{A,B}` (accuracy / same size, parent, seed, panel R1), permuted, disabled, support share / mean length / useful slots, `lm_before_nats`, `lm_after_nats`, `lm_relative_rise`; key names checked against `evaluate.py` | applied (η column `None` when R1 = 0, report only; the class code keeps its +∞/0 rule) |
| 5 rehearsal draw name | `seed_set` in the whitelist, validator string-only, written in rehearsal and train records | applied |
| 6 stale text | `evaluate.py` docstring updated; the ADR status line is for the freeze edit | applied / pending freeze |
| 8 loss | `loss.detach().item()` — the same Python float as `float(loss)` | applied |
| 10 snapshot hash | `evaluate_cell` compares `file_sha256(model.pt)` with `train.json["snapshot_sha256"][str(u)]`, required in `work_evaluate` | applied; the 90 calibration snapshots all match their `train.json` (r1 d), so genuine snapshots pass |

## 3. Nothing the calibration and my checks rested on changed

- `git diff 85d6c1b dd8b205 -- studies/p9i/model.py studies/p9i/core.py studies/p9i/data.py configs` is **empty**.
- `train.py`: a record field (`extra`, `seed_set`), the rehearsal whitelist, and `float(loss)` → `loss.detach().item()`. No change to batches, loss, optimizer, clipping or snapshots. `evaluate.py`: a docstring, the hash check before loading, and extra keys merged after `_finite`. `classes.py`: two outcome constants. No computed number changes.
- Re-run at HEAD: **forward equality** (a4) — every arm's max |logit difference| vs my reference, parameter counts, causality, non-site zero, BB's 4,224 parameters: identical output; **class agreement** (a5) — 20,000 random tables, 0 disagreements, byte-identical output; **determinism** (a3) — N, BB, A4E 64-update replays on rehearsal draw 2 reproduce the rehearsal's `model.pt` and `optimizer.pt` bit for bit (the rehearsal ran at `939b4bf`).
- Code identity: `source_sha256` changed `5bc82bce…` → `7573da72a1d702c57d257d617f5f0f3ec6207bfb8c12b6f381b485a33225a4db` (expected: `studies/p9i` changed); `spec_sha256 7dcbcfc1…` and `config_sha256 7cc20791…` unchanged; `frozen_source_sha256 8b5a03a0…` unchanged.

## 4. M3 — the lead's freeze plan

**Mechanics: satisfies the registered-mode precondition.** `r2` in a throw-away clone at `dd8b205`: a "freeze commit" that changes only ADR-0017 (simulated §15.5 and decision-2 text) → `check_preconditions(--freeze-commit = that commit)` ACCEPTED at HEAD = freeze and after a later results-only commit; `--freeze-commit dd8b205` REFUSED (ADR differs); an ADR edit after the freeze REFUSED. So the decision-2 entry must be in the freeze commit and the ADR must not change until the run ends; the plan does that. No ADR hash is pinned anywhere in code or tests (searched), so editing the ADR breaks nothing else.

**§15.3: satisfied, provided the freeze commit records the following (F1–F4).** "Approve after the freeze" is met in substance: the decision is taken on a code tree that is fixed before the decision (the code commit named in §15.5, whose `studies/`, `configs/p9i_interface.toml` and `tests/test_p9i_*` must equal the freeze commit's) and recorded before any registered stage. The condition-by-condition check the lead will write must include:

- **F1 (condition 3, "nothing changed after calibration except U").** Taken literally it is false: `studies/p9i` changed after the calibration (`source_sha256 5bc82bce… → 7573da72…`). The decision-2 entry must state that the only changes are the audit-required fixes M1, M2 and minors 1–5, 8, 10, list them, and cite this re-check (model, data, core and config unchanged; forward, class and determinism re-checks identical). Whether that reading of condition 3 is acceptable is the lead's call under the delegation — **PENDING LEAD REVIEW** (if the lead doubts it, decision 2 returns to the human).
- **F2 (§12 item 7 "freeze of … data and panel identities"; my minor 2 second half).** The lead's §15.5 list has no data identity. Either generate registered data before the freeze commit (the generate stage is built to run before it: `skip_preconditions=True`, `--i-understand-freeze-time`) and record the generate run directory, the `data_manifest.json` sha256 and G1's pass in §15.5; or state in §15.5 that data are generated after the freeze from frozen code and seeds and that the auditor checks the manifest after the run. The first matches the ADR's wording. In either case the decision-2 entry should say how condition 5 is read: generating registered data and G1 observe no model output on registered seeds. **PENDING LEAD REVIEW** (which order).
- **F3 (calibration hash).** The in-code binding plus the ADR hash is sufficient, because (i) every registered stage refuses without `--calibration`, (ii) every worker and every later stage is bound to the hash the train stage recorded, and (iii) the hash appears in `calibration_binding.json`, every train/eval record and `analysis.json`. What the code cannot do is compare it with the ADR. Close that by procedure: §15.5 names the file (`results/p9i-calibration-2026-11-14/calibration.json`, committed, sha256 `087bf0b5…`) and the exact `--calibration` argument; the independent recomputation after the run must check `calibration_binding.json` equals `087bf0b5…`, 8,192, `{}` before anything is interpreted. A mismatch would waste budget but cannot pass unnoticed.
- **F4 (caps and tree).** Stage caps are operator arguments (`--stage-cap-seconds`, required in registered mode); §15.5 should give the exact command line per stage, and the recomputation should compare each stage manifest's cap with §15.5. Ledger: 930.3 s charged + 6,000 s of caps = 6,930 s ≤ 14,400 s (condition 4; this re-check charged nothing). The working tree must be clean when stages run, so this folder (`RECHECK.md`, `r1`, `r2`, outputs) must be committed before the freeze commit or in it.

Condition 2 ("no open blocker or major"): with this re-check M1 and M2 are closed; M3 closes when the freeze commit is made as above.

Second failed checker attempt (kept in this note, my mistake): my first polling loops for the background pytest matched the word "passed" in ruff's "All checks passed!" and returned before pytest finished; no number was taken from them.

## 5. New problems

None blocking. Notes:

- N1 (minor, not introduced): `cells_for` honours `--only`/`--group` in the analyze coordinator, but the worker re-derives the full registry (`common_args` forwards neither), so the denominator cannot shrink. Fine as is; do not add `--only` forwarding later.
- N2 (cosmetic): when both INCOMPLETE and gate reasons apply, the report lists the reasons and the missing labels under NOT INTERPRETED; fine. The η report column is `None` where R1 = 0 while the class code uses +∞/0; report-only, consistent with the rule that R1 < 0.5 makes the size NOT_EVALUATED first.
- N3: existing tests `test_p9i_classes.py` and `test_p9i_stages.py` were edited (one assertion widened, one assertion added); both pre-freeze P9I files, additive, acceptable.

## Verdict

**READY TO FREEZE**, with the freeze commit carrying F1–F4 in §15.5 / the decision-2 entry (text only, no code change). M1 FIXED, M2 FIXED (as the lead ruled), M3 plan SUFFICIENT subject to F1–F4. Minors 1–6, 8, 10 applied; 7 and 9 remain notes.

Astra review: NOT_PERFORMED. This re-check is not human approval and not decision 2.
