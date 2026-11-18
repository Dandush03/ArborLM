# P10-I-S1 block M — from calibration to the registered stages (run sheet)

Status: implementation and calibration only. Nothing is frozen; no Decision 2 exists. Every command is run from the worktree that holds the freeze (`cd <worktree>`), prefixed `uv run --locked python -m studies.p10is1.stages`
(written `S` below). All figures marked *estimate* are analytical or hypothetical (P10-S1 six-worker rates), never measured here. Anything marked **UNSURE** needs your eye.

Folders used below (all outside git or git-ignored; `E=/Users/daniellaloush/dandush03/ArborLM/experiments`):
- `RUN=$E/P10IS1-pre-20261118` — holds `draws/` (the five manifests from `generate`) and the public calibration files. It must also be the REGISTERED run directory: `candidate-plan` reads the manifests from it and the plan stores its path (every registered stage refuses another). **UNSURE**: the name says "pre"; using it avoids copying the manifests (copying them to a new folder also works, but then `generate` is not re-run: copy `draws/` and the public files).
- `SEALED=/Users/daniellaloush/dandush03/ArborLM-sealed/p10is1-cal` — sealed; never opened. Its ledger `P10IS1-calibration-ledger.json` is read by `project` only (6.48 h charged by the calibration: the ledger's own total, the only figure read).
- `CAL=$RUN/calibration_public.json` (public). Public content: U_P = 8,192 at all three rows; U0 = 196,608 (2K/256), 98,304 (8K/1K), 196,608 (32K/4K); 2K/256 runs; no return to the lead; H8 UNDERTRAINED-AT-U_P at 2K/1K, 8K/4K, 32K/16K and NOT CALIBRATED at 8K/1K, 32K/4K; 17 rates carry EDGE BY TIE-WALK (several at 0.1, the top of the grid; T-OQ at 4,096 and 16,384 slots at 0.3 after one extension). **UNSURE**: that many top-of-grid selections is a fact of the record; the ADR rule accepts it (tie-walk edge is taken, not extended).

## 1. `qualify` (started by you)
`S qualify --sealed-dir $SEALED --run-dir $RUN --calibration $CAL`
Trains R2 at the three reference cells (2K/4K, 8K/16K, 32K/32K) to U_P = 8,192 on the rehearsal draw and both calibration draws (9 runs), evaluates every snapshot fraction with DEP-a/b/c. Writes the work into `$SEALED/<view>/` and the PUBLIC `$RUN/qualification.json` (`table`: row -> fraction -> qualified conditions; `failures`; no accuracy). Charges its seconds to `$E/P10IS1-prefreeze-ledger.json`. *Estimate*: 10-30 min on one process.

## 2. Candidate plan (first, provisional)
`S candidate-plan --run-dir $RUN --calibration $CAL --s1-run-dir $E/P10S1-registered-attempt2-20261117`
- `--s1-run-dir`: P10-S1's registered attempt 2 (the run whose checkpoints the adapter identity gate reproduces: `cells/P_F-OQ_f8192_n4096_d1_i2101/snapshots/u0004096` etc. exist there; identified by listing, 2026-11-18). The gate trains F-OQ and T-OQ at 8K/4K draw 1 for 2,048 updates and compares tensors bit for bit.
- `--projection`: omit it now. The plan then lists every loaded cell to 4 x U0 and carries `caps_provisional: true`; it is only for the measuring rehearsal. Writes `studies/p10is1/freeze/plan.json` (refuses to overwrite without `--supersede`). Takes seconds.

## 3. Measuring rehearsal (rates)
`S rehearse --measuring --run-dir $E/P10IS1-measuring-20261118 --plan studies/p10is1/freeze/plan.json --rates-out $E/P10IS1-measuring-20261118-rates.json --workers 6,7`
- `--run-dir` must be new/empty and git-ignored. Rehearsal draw only (249201, init 330192); no registered seed.
- Writes the rates file (`by_workers.{6,7}`: seconds per update per arm and size, evaluation seconds per snapshot under the k-worker load, `contention` = the worst item, `contention_by_item` = every item, peak RSS per worker, fixed stages, `machine.before/after` = load average and other study processes alive) and prints the worst-item and per-item slowdowns. Charges `$E/P10IS1-prefreeze-ledger.json`.
- It does NOT demand a quiet machine (no code refuses), but the contention ratio is only meaningful under the load the run will have: run it with the machine as it will be during the registered run and read `machine` in the file; anything else running is recorded there, not excluded. The isolated timing inside it is not the MC-T source (that is the registered timing stage).
- *Estimate*: 30-90 min (isolated timing of 16 items x 800 updates, k = 6 and 7 concurrent rounds, 16 evaluations, 3 baselines). **UNSURE** about the upper end at 32K facts.

## 4. `project` (the one projection, section 17.1)
`S project --calibration $CAL --rates $E/P10IS1-measuring-20261118-rates.json --charged-hours 0 --ledger $SEALED/P10IS1-calibration-ledger.json --ledger $E/P10IS1-prefreeze-ledger.json --out $E/P10IS1-projection.json`
- H_c = `--charged-hours` (typed; use only for hours that have NO ledger) + every `--ledger`. The two ledgers above are everything: calibration (sealed dir) and generate + qualify + measuring rehearsal (pre-freeze ledger, which is only complete once steps 1 and 3 have finished). Do not pass the ledger again after the counting rehearsal.
- Output: `grants` (G per ladder cell), `levels_considered`, `closed`, `stage_hours`, `caps` (`config_caps`, `total_cap_hours`, `total_above_limit`), `measured_slowdown` (rule figure beside per-item figures), `h_charged_breakdown`, `worker_choice` (6 or 7 workers: lower projected hours).
- Labels: `WITHIN BUDGET` = base plan and the granted levels fit B = (60 + H_c)/2 on the total; `BASE PLAN ABOVE BUDGET` = even U0 for every loaded cell does not fit: exit code 3, the freeze refuses it, no cell/length/threshold changes and only the human lead may raise the 60 h (not the lead); `refused: true` is the same fact. A cell in `closed` is simply granted no further level (NOT FULL WITHIN BUDGET possible there). `total_above_limit: true` = the caps would exceed 60 h: the freeze refuses; the human lead's decision.

## 5. Caps — entered BY HAND in the config
Copy `caps.config_caps` of `$E/P10IS1-projection.json` into `configs/p10is1_capacity.toml` `[caps]`, key by key: `train_hours`, `evaluate_hours`, `timing_hours`, `throughput_hours`, `analysis_hours`, `rehearsal_hours`, `total_hours`; set `provisional = false`. Commit nothing yet. The freeze compares ALL seven with the projection and refuses any difference. (`calibration_hours` and the plan's other fields are not entered by hand.) The config is a frozen file: edit it BEFORE step 6, and not again.

## 6. Candidate plan again, with the projection
`S candidate-plan --run-dir $RUN --calibration $CAL --projection $E/P10IS1-projection.json --s1-run-dir $E/P10S1-registered-attempt2-20261117 --supersede`
Moves the provisional plan to `freeze/superseded/`, writes the plan with `params.granted` = the projection's grants. Any later change to code, config, calibration file or manifests makes `freeze` refuse (re-derivation).

## 7. Counting rehearsal
`S rehearse --counting --run-dir $E/P10IS1-counting-20261118 --plan studies/p10is1/freeze/plan.json --record-out $E/P10IS1-counting-20261118-rehearsal.json --qualification $RUN/qualification.json`
Runs the registered driver's own stage functions on the rehearsal-draw view of that plan file, all stages in order (REAL SIZE: one replicate, every cell to its granted length, ladder rounds included), then the analysis and report on a synthetic registry keyed by the plan's labels. The record names the plan file's SHA-256, `caps_provisional` (must be false: hence step 5 first) and the R2 table. **The timing and throughput stage functions inside it use the real quiet condition: they PAUSE (not fail) if the machine is not quiet (load <= 1.0, no other study's stage alive, mains power); run it with the machine alone.** *Estimate*: about 1.1 h (hypothetical), plus waiting for quiet.

## 8. Freeze
`S freeze --rehearsal $E/P10IS1-counting-20261118-rehearsal.json`
Writes `studies/p10is1/freeze/freeze_record.json`. Refuses: no projection / projection not WITHIN BUDGET / grants or any of the seven caps differing / total over 60 h / provisional caps / rehearsal record missing a stage, on provisional caps, naming another plan file, or without the R2 table for all three rows / G9 (seeds, runs the registry checker copy) failing / plan not equal to a re-derivation. Then COMMIT `freeze/plan.json` + `freeze/freeze_record.json` (and the edited config): that commit is the FREEZE COMMIT `F` (`git rev-parse HEAD`). Nothing else may change afterwards in `studies/p10is1/**`, the config, `uv.lock`, `studies/p10s1`, `studies/p9*`, `src/arborlm`.

## 9. Decision 2
Create and COMMIT (after `F`) `results/p10is1-freeze-<any-suffix>/DECISION_2.md` containing the full 40-character hash of `F` anywhere in the text and, as its own line, exactly `DECISION: RUN` (and no `DECISION: DO NOT RUN` line). Only the committed content counts. The tree must then be clean (no writes in the worktree during the run; run dir and ledgers are outside it).

## 10. Registered stages (one run directory `$RUN`; `F` = freeze commit)
Each: `sh studies/p10is1/launch/<stage>.sh $RUN F` (= `S registered <stage> --run-dir $RUN --freeze-commit F`). Resumable; PAUSED stages are simply started again. Order:
1. `gates` — G9, manifests regenerated and compared, adapter identity gate against P10-S1 attempt 2. Minutes.
2. `timing` — **MACHINE ALONE** (quiet condition: load <= 1.0, no other study stage, mains, not Low Power; retried every 10 min for 6 h per session; PAUSED — QUIET CONDITION NOT MET otherwise; NOT MEASURED only by `$RUN/decisions/timing_not_measured.json` after 6 PAUSED attempts). Training refuses until it is COMPLETE. *Estimate* 5-10 min.
3. `train` — all cells to base length (U0 for ladder cells). *Estimate* 4.9 h (hypothetical, six workers).
4. `ladder` — loaded cells continue round by round to the first ladder point at which every store arm is full in every replicate, or to G. *Estimate* 0.1-3 h (hypothetical: depends on where they stop).
5. `evaluate` — cells that are not ladder cells. *Estimate* 0.4 h.
6. `baselines` — 15 no-memory baselines, minutes.
7. `analysis`, 8. `report` — minutes (refuse while any item error exists).
9. `throughput` — **MACHINE ALONE**, after everything else; PAUSED/rescheduled the same way. *Estimate* about 7 min.

## Base plan and the 60-hour budget (analytical, HYPOTHETICAL)
From the public file: U0 = 196,608 / 98,304 / 196,608 at 2K/256 / 8K/1K / 32K/4K, i.e. 0.5 / 0.25 / 0.25 of P10-S1's registered lengths (393,216 / 393,216 / 786,432). Base-plan updates per replicate (computed with `core.planned_cells`, U_P 8,192 at every row): cells that are not loaded 958,464 (run length 6 x 8,192 = 49,152; R2 8,192) plus loaded cells at U0 1,376,256 (8K/1K 4 arms x 98,304; 32K/4K 4 x 196,608; 2K/256 196,608) = 2,334,720; times five replicates = 11,673,600 updates (P10-S1's comparable figure was about 2x that). With P10-S1's six-worker rates and H_c of 7-12 h (calibration 6.5 h + generate/qualify/measuring rehearsal, estimate) the projection code gives: base remaining about 6.8 h (train 4.9, ladder 0.1, evaluation 0.4, counting rehearsal 1.1, fixed 0.25), every ladder cell granted all four levels (up to 786,432 / 393,216 / 786,432 = P10-S1's lengths), projected total about 25-30 h, caps total about 44-49 h: inside 60 h with room. Longest single item: T-OQ at 32K/4K, about 2.8 h at 786,432. This is a projection from P10-S1 rates, not a measurement; the measuring rehearsal replaces it.
