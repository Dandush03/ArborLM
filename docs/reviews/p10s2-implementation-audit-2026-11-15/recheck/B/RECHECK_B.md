# P10-S2 re-check, lane B: stages, ledger, budget and the cap rule, freeze, rehearsal, calibration, recomputation, gates, launch scripts, registered mode

Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.

- Object: pinned commit `fc08681` (`.../scratchpad/pin-p10s2-fc08681`), against ADR-0022 revision 5 with every addendum at its end (including "rulings on the points the three fix lanes left open") and `ADR-0022-addendum-combined-tasks.md`, after the fixes to `docs/reviews/p10s2-implementation-audit-2026-11-15/B/AUDIT_B.md`.
- Model that ran this re-check: Opus 5.5 (`claude-opus-5-5`). I did not write any of this code or the predecessor audit.
- Environment: macOS 27.2.1 arm64, 18 cores, MPS available; Python 3.12.14; torch 2.8.0. Interpreter `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a91c79a181109bb9c/.venv/bin/python` (no environment created). Every run used `PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH=<tree>/src` (see failed attempt 2), `TMPDIR` and `--basetemp` inside this folder. Seeds: test range only (229001–229999; my own RNG 229501, 229777). No network, download, real model or data; no calibration, rehearsal or registered seed drawn. The end-to-end exercise was run once.
- `R` below = this folder; `P` = the pinned tree; `E` = `R/e2e/p10s2-e2e-xxf8y7o5` (the kept clone of the one exercise run).

## Verdict: READY AFTER LISTED FIXES

All three blockers (B1–B3) and every major (M1–M12) of the predecessor audit are fixed as specified, and all minors except where noted. My own recomputation of the cap and rung rule matches the code (0 of 10,800 points differ). The recomputation rule behaves as the rulings state on every probe. The end-to-end exercise passes through the real launch scripts.

Three new majors remain:
- **N1.** The rehearsal does not time E_open, so R is too small.
- **N2.** A registered stage accepts a study ledger that does not hold P.
- **N3.** The freeze accepts pre-freeze records that are typed, stand-in or mismatched.

There are also 13 minors.

They are not all due at the same step:

| When | Must be fixed |
|---|---|
| Before calibration | N3 (a) and (b): what the calibration record carries, and the typed `--updates`/`--device` |
| Before the pre-freeze gates stage and the rehearsal | N1, N3 (a) and (b) for their records, m1, m2, m6 |
| Before data generation (or at the latest before the freeze, because the file is frozen) | m3 (a test that fails once the study ledger exists) |
| Before the freeze | N2, N3 (c), m4, m5, m7; then a re-check of these fixes |
| Lead's rulings (PENDING LEAD REVIEW) | m8, m12, and the reading of m2 |

## Commands and outputs (cwd = `P` unless stated; `$PY` = the interpreter above)

| # | What | Command | Output | Result |
|---|---|---|---|---|
| T1 | S2 test suite, pinned tree | `PYTHONPATH=$P/src PYTHONDONTWRITEBYTECODE=1 TMPDIR=$R/tmp $PY -m pytest -q -p no:cacheprovider --basetemp=$R/pytest-tmp tests/test_p10s2_*.py -rfE` | `outputs/pytest_pinned.txt` | **495 passed, 6 failed, 1 skipped** (195 s). The 6 failures are the location-based test guard, because the pinned tree lies under `/private/tmp` (see m3). The run created an empty `experiments/P10S2/` in the pinned tree; I removed it (`rmdir`) |
| T2 | the same, in a throwaway FROZEN clone (real configuration; `plan.json`, `stage_caps.json`, `cap_raise.json`, `records/`, a committed `DECISION.md`, a study ledger with a registered entry) | `sh $R/scripts/r5_frozen_clone.sh $P $R $PY` | `outputs/r5_frozen_clone.txt` | **495 passed, the same 6 failed, 1 skipped**. No failure comes from the freeze files, so the old M11 test is fixed |
| T3 | the frozen clone with the guard behaving as at the real location (a pytest plugin makes only basetemp and `$R/tmp` temporary) | cwd `$R/frozen-clone`: `PYTHONPATH=$CL/src:$CL:$R/scripts RECHECK_TMP=$R/tmp TMPDIR=$R/tmp PYTHONDONTWRITEBYTECODE=1 $PY -m pytest -q -p no:cacheprovider -p recheck_location_plugin --basetemp=$R/pytest-loc-tmp tests/test_p10s2_*.py`, once as frozen and once with `experiments/` moved out | `outputs/r5b_location_simulated.txt` | with the study ledger present: **4 failed, 497 passed, 1 skipped**. Each failure is `not (REAL_ROOT/"experiments"/"P10S2").exists()` (`tests/test_p10s2_integration.py:71`). The same clone without `experiments/`: **501 passed, 1 skipped**. With the guard behaving as at the real location, it refuses as intended (m3) |
| E | the end-to-end exercise, once | `PYTHONPATH=$P/src ... $PY -m studies.p10s2.e2e --workdir $R/e2e --keep` | `outputs/e2e.json`, `outputs/e2e.stderr.txt` | **ok = true, 195 s**. Training ran on MPS. 18 steps behaved as required (cap-stopped calibration, exit 4; failed pilot with the real threshold, exit 3; rehearse refused, exit 2; relaxed pilot; calibrate, prefreeze_gates and rehearse scripts; freeze; freeze commit; decision; three refusals; the 7 registered scripts; a second run refused; a tampered recomputed score listed with its cell NOT_EVALUATED). Mechanics label on stand-ins: TRANSFER-NEGATIVE: NO-ACQUISITION (2 replicates, U = 4). This is not a result |
| R1 | cap rule and rung rule, my own code | `$PY $R/scripts/r1_cap_rule.py $P $R/outputs/r1_cap_rule.json` | `outputs/r1_cap_rule.json` | grid of 4,800 points plus 6,000 random points: **0 mismatches**. Boundary probes: see m4 |
| R2 | snapshot on MPS, memory, device, state leaks | `$PY $R/scripts/r2_device_memory.py $P $R/outputs/r2_device_memory.json` | `outputs/r2_device_memory.json` | see B1, M6, M8, (f) |
| R3 | recomputation rule probes on the kept run | cwd `E/clone`, `PYTHONPATH=E/clone/src $PY $R/scripts/r3_recompute.py $E $R/outputs/r3_recompute.json` | `outputs/r3_recompute.json` | 10 probes, every check passes (see task 5) |
| R4 | watchdog with SIGINT ignored | `$PY $R/scripts/r4_watchdog.py $P $R/outputs/r4_watchdog.json` | `outputs/r4_watchdog.json` | see task 3 |
| R6 | registered-mode guards on the kept clone (restored afterwards) | `sh $R/scripts/r6_registered_guards.sh $E $PY` | `outputs/r6_registered_guards.txt` | P1 is a fresh ledger, **accepted** (N2). P2–P7 are refused as required. Run directory and ledger restored: 0 differences |
| R7 | what the freeze accepts | `$PY $R/scripts/r7_freeze_inputs.py $E $R/r7work $PY` | `outputs/r7_freeze_inputs.txt`, `.json` | 7 cases: control accepted, failed pilot refused, **five bad inputs accepted** (N3) |
| R8 | cost of one registered bootstrap interval | `$PY $R/scripts/r8_bootstrap_cost.py $P` | `outputs/r8_bootstrap_cost.json` | 1.4 ms (12 items), 8.4 ms (500), 15.0 ms (1,000), 10,000 resamples, 6 threads |
| R9 | failed cells keep the replicate's records | `$PY $R/scripts/r9_failed_cells.py $P $R/r9work $R/outputs/r9_failed_cells.json` | `outputs/r9_failed_cells.json` | see M10 |
| R10 | which commit is "the commit that added plan.json" | `sh $R/scripts/r10_freeze_commit_identity.sh $R/r10git` | `outputs/r10_freeze_commit_identity.txt` | the oldest add on the branch (see (e)) |
| R11 | frozen stage caps against 2R | `$PY $R/scripts/r11_caps_vs_R.py $P $E/pre-run/rates.json` | `outputs/r11_caps_vs_R.txt` | sum of caps = 2R + 2 × start-up at every rung (m5) |
| R12 | printing of NOT STARTED lines (old C out-of-lane note) | inline, `outputs/r12_emit_not_started.txt` | | no OracleLineMissing; the oracle line heads each |
| R14 | E_open in the stand-in bundle | inline `read_bundle` of the exercise's bundle | `outputs/r14_standin_e_open.txt` | 0 E_open items (so 0 with an A or B reference) |
| R13 | data generation charged and capped | `$PY $R/scripts/r13_datagen_charge.py $P $R/r13work` | `outputs/r13_datagen_charge.json` | see B3 |

## 1. The predecessor's findings, before → after (with the demonstrations re-run)

| Finding | Before (AUDIT_B) | After (this re-check) | Status |
|---|---|---|---|
| B1 calibration snapshot on MPS | `copy.deepcopy` stayed on `mps:0`; scoring raised `mat1 is on CPU` | R2: old method still raises the same RuntimeError; `calibration.cpu_snapshot` copy is on `cpu` and scores (0.1085). `run_calibration` end to end on MPS (stand-in, layers patched in-process to [0,1], 4 updates, snapshot 2): ok, `selection_at_snapshot` present. Exercise: `calibrate.sh` on MPS ok | fixed |
| B2 `rehearse.sh` crashed | TypeError at `int(args.layer)` | layer and LoRA learning rate read from `calibration.json`; refuses without it or after a failed pilot (exercise steps 3, 6) | fixed |
| B3 data generation not charged | no ledger entry; freeze deadlocked | R13: start marker and end entry; guard stop after 0.52 s charged as `failed`; refused to start with 0.10 h room under a 1.8 h cap (no entry written); `prefreeze_caps_from_ledger` sees the datagen charge. `fetch.run` is under `measure("fetch")` | fixed |
| M1 `--caps`, `--repo` | typed caps replaced the frozen cap; `--repo` checked another tree | `--caps` has one choice (R6 P6b: even `./studies/...` refused), `--repo` and `--device` do not exist (P6c, exercise); `check_code_location` refuses an `arborlm` imported from elsewhere (my failed attempt 2 shows it firing) | fixed |
| M2 order and write-once | train ran without gates; analysis before recompute | R6 P5: analysis refused without the recompute record; P7: train refused when G4 = false; exercise: train before gates refused, second gates refused; `record()` write-once | fixed |
| M3 one ledger, raise after registered | 33 h train cap against 36 h with P ignored; raise and re-freeze accepted after registered processes | one ledger at `experiments/P10S2/ledger.jsonl`. R6 P2: 35.99 h charged gives a refusal. P4a–d: `raise-cap` and `freeze` refused after the registered run, also with the ledger moved aside (plan in history). P3: a hand-appended raise makes every stage refuse. **But P1: a fresh ledger is accepted (N2)** | fixed except N2 |
| M4 deadlines, reserve | checked between replicates; analysis/report unreserved | every registered stage under `StageGuard(cap)`; per-update STOP hooks; reserve = analysis + report caps in `refuse_if_over` (`stages.py:589-590`); R in the rule contains max(a,30)+max(r,30), doubled = the caps' 60 s floors (ruling) | fixed (m5) |
| M5 rehearsal measures registered work | timing on 3 items; no G2; routers untimed; N-row stores | registered stage functions run on a rehearsal world (task 4) | fixed except **N1** |
| M6 MPS memory invisible | `ru_maxrss` +0.024 GiB for 2 GiB | R2: 1 GiB MPS tensor: `max` rose 0.48 GiB (from 0.59 GB RSS to the 1.11 GB driver figure; RSS +0.0008 GiB); a guard with limit below the sample stopped in 0.12 s with `MemoryLimitExceeded`; `memory/<stage>.json` feeds `memory_exceeded` | fixed (m1) |
| M7 E-table layer, timing in recompute | one E-table rate; timing excluded | `ETABLE@L{4,12}` keys, slower at U = 1,000; `recompute_seconds = scoring_seconds` (timing included). R1 agrees | fixed |
| M8 device | `auto` fell back to CPU silently | R2: `auto` → ValueError; MPS reported unavailable → RuntimeError; `PYTORCH_ENABLE_MPS_FALLBACK=1` → RuntimeError; G4 with `require_mps` on a CPU world fails, `cpu_by_freeze` prints NOT APPLICABLE — TRAINING ON CPU BY THE FREEZE. Device in the plan. **But CPU can be frozen on a typed reason (N3)** | fixed except N3 |
| M9 recomputation compares cells only | Stage 0, teachers, routers etc. not compared | every section compared; verdicts by `analysis.verdicts` (task 5) | fixed |
| M10 failed cell loses replicate | records lost on any non-NaN exception | R9: (a) an operation error inside a cell: 17 completed, 1 failed with the error, `r0.json` written. (b) an exception outside a cell: rebuilt from snapshots, 5 completed, 13 failed with the error. (c) guard cap mid-replicate: 1 completed, 11 failed, 6 skipped_dependency, `stopped.json` written | fixed |
| M11 freeze trusts typed values; test fails once frozen; ADR frozen | typed layer/LR; `test_p10s2_prefreeze.py:333` | layer, LRs and pilot come from `calibration.json` (U = 1,000 from the snapshots); a failed pilot is refused (R7 'pilot'); T2: no test fails because of freeze files; the decision is in `results/p10s2-freeze-*/DECISION.md`. **But other typed or stand-in record content is still accepted (N3)** | fixed except N3 |
| M12 never run end to end | — | exercise E passes (task 6) | fixed |
| m1 pre-freeze caps ignored | — | `StageGuard(cap_seconds=--stage-cap-seconds)` and room check in calibrate, prefreeze-gates, rehearse, datagen | fixed (m6: no stop record in two of them) |
| m2 startup child in test mode | — | `_child_world` uses `RunConfig.registered` on rehearsal seeds, CPU | fixed |
| m3 deterministic/threads differ | — | `scoring_environment()` in evaluate, recompute, gates; R2 shows it restores threads, deterministic flag and warn_only | fixed |
| m4 refusal files in frozen folder; `code` unverified | — | refusals to `experiments/P10S2/refusals/`; `plan["code"]` verified; `studies/__init__.py` frozen | fixed |
| m5 later commit accepted | — | R6 P6a: the decision commit as `--freeze-commit` refused | fixed |
| m6 raise file deleted, re-raise | — | the raise is a ledger entry; R6 P3 | fixed |
| m7 G7 tautological, G9 replicate 0 | — | G7 reads `manifest.json` (empty manifest fails); G9 plans every replicate; `seeds/<stage>.json` per world-building stage (exercise asserts seeds) | fixed |
| m8 rehearsal analysis/report on synthetic registry | — | `synthetic_registry_run` (4 replicates, missing cell, rejected consolidation, inertia cell, non-finite value) runs `stage_analysis` and `stage_report` in the probe child | fixed (m10) |
| A-M3 panels before freeze | rehearsal scored E_A/E_B | `rehearsal_world` swaps in D_cal; I traced every scoring path in `stage_evaluate`/`gates.run_gates`/`calibration` and found none that reads E_A, E_B, E_C or E_open. That also creates N1 | fixed (N1) |
| A-M4 G9 vacuous | — | strict `seed_gate`; empty record fails (lane A re-checks the detail) | fixed in my lane's use |
| C out-of-lane: OracleLineMissing on NOT STARTED | — | R12: no exception | fixed |

## 2. The sibling defect classes in S2

(a) **Registered worker started by hand or outside the plan.** S2 has no registered worker processes: each registered stage is one process driven by `cmd_registered`. The only child processes are the rehearsal's `startup`/`probe`, which are pre-freeze and run in rehearsal mode. No CLI trains a cell outside `registry(n)` of the plan. There is no driver token, however: `core.seeded_generator(seed, purpose, "registered-run")` accepts any in-process caller, and such a draw leaves no ledger entry, so `registered_seed_observed` cannot see it (m11). Not demonstrated; drawing a registered seed is outside my permissions.

(b) **Freeze accepting DRY/stand-in records, a wrong unit, or open returns.** **Reproduced (N3).** R7 shows five cases. A failed pilot is refused, and a failed pre-freeze gates record is refused (code: `freeze.py:241-243`). The study's "open returns to the lead" are NOT STARTED records, and the freeze refuses them (pilot, prefreeze stop, BUDGET).

(c) **Tests that assume a pre-freeze tree, or that can start a registered stage against the real repository.**
- In the frozen clone, no test fails because of freeze files (T2).
- **One test assumes no study ledger exists** (T3, m3). It fails in the real repository from the first fetch or data-generation charge onward.
- The test guard is keyed to location. In a checkout under `/tmp` (an audit pin, the exercise's clone), registered and pre-freeze commands run past it. My T1 run created `experiments/P10S2/` in the pinned tree (removed).

(d) **Test profile, stand-ins or `provisional` paths in a real registered run.**
- I found no flag that reaches them. `RunConfig.registered` is used, `provisional_combined` is refused outside test mode, an empty `timing_items` is refused in registered-run, and `--device`/`--updates`/`--repo` do not exist.
- The one route is data identity: the frozen `--data-dir` is typed and not bound to the bundle that calibration and the rehearsal read, so a stand-in bundle can be frozen (R7 'bundle', N3).
- With the real configuration, a stand-in student (3 layers) would fail at read layer 4 or 12. I could not show a registered run on a stand-in bundle under the real configuration without drawing real calibration seeds, so it is not demonstrated.

(e) **Oldest vs latest `plan.json` commit.** `check_freeze_identity` takes `added[-1]` of `git log --diff-filter=A` (newest first), which is the **oldest** add on the branch (R10). In the re-add case (A added, deleted, B re-added) A is required. A side branch that added `plan.json` and was merged with `-s ours` does not appear. `plan_in_history` uses `--all` and sees it, so the raise is still refused. Together with the frozen-path equality this is the strict reading. No defect.

(f) **In-process leaks.**
- `scoring_environment` and `stage_timing` restore thread count, deterministic flag and warn_only (R2).
- `train_arm` on MPS restores `deterministic=True` but drops `warn_only=True` (R2; m9; no registered caller uses warn_only).
- No `set_default_device`/`set_default_dtype`/global seed anywhere in `studies/p10s2` (grep).
- Global state that persists and is deliberate: `train.MPS_IN_USE`, `train.STOP` (cleared by each guard), and `ctx.seed_plan` (mutated by calibration, gates and scoring).

## 3. The cap rule, the reserve, deadlines, the watchdog

- **Rule (R1).** My own R and rule (cells, layers, start-up, combined rows, timing in the recomputation, analysis/report reserve, cap = 36, else the smallest whole hour ≤ 72 at which rung 1 fits, else 72 with the rung order, else NOT STARTED: BUDGET) agree with `budget.computed_cap` and `budget.rehearsal_rule` on **4,800 grid points and 6,000 random points (0 mismatches)**. Caps from 36 to 72 h are all exercised, and the outcomes are rung 1, 2 and 4 and NOT STARTED: BUDGET.
- **Boundary (m4).** When P + 2R₁ exceeds a whole hour h by less than 1e-12 h, `math.ceil(need - 1e-12)` returns h, rung 1 does not fit at h, and rung 2 is chosen under a cap that was raised for rung 1:

  | P + 2R₁ | code (cap, outcome) | rule (cap, outcome) |
  |---|---|---|
  | 40 + 5e-13 | 40, rung 2 | 41, rung 1 |
  | 36 + 5e-13 | 36, rung 2 | 37, rung 1 |

  The probability is negligible.
- **The freeze records the raise and refuses any other cap.**
  - `write_freeze` computes the cap and, once all else is accepted, calls `record_raise` itself (`freeze.py:259-260`).
  - `verify_raise` refuses a file or ledger cap different from `computed_cap(P, rates)`.
  - `verify_plan` refuses a ledger cap different from the plan's (R6 P3).
- **No raise after any registered seed.** The CLI paths are all refused: `raise-cap` and `freeze` after registered processes, with or without the ledger (R6 P4a–d). A hand-appended ledger raise stops every stage (P3). Editing `cap_raise.json` changes a frozen path. The registered room check uses `plan["cap_hours"]`, never the ledger's cap. The only theoretical path is a registered seed drawn outside `cmd_registered` before the freeze (m11).
- **Reserve.** `reserved_seconds` adds the frozen analysis and report caps (floor 60 s each) to every earlier stage's room check. R contains max(a, 30 s) + max(r, 30 s), so 2R reserves exactly those caps (ruling).
- **Sum of caps (m5).** The frozen caps sum to 2R + 2 × start-up (R11), because the timing cap includes a start-up that R does not.
- **Deadlines.** Every registered stage, calibrate, prefreeze-gates, rehearse and datagen run under `StageGuard(cap)`. Training also checks per update (`_armed`).
- **Watchdog with SIGINT ignored (R4, fresh child per case).**

  | Case | SIGINT ignored | SIGINT default |
  |---|---|---|
  | `StageGuard` around a Python loop | `CapReached` at 1.05 s | the same |
  | The old `_thread.interrupt_main` | **ran the full 6.0 s (no stop)** | 1.02 s |
  | Inside `time.sleep(2)` | stop delivered at 2.01 s, when the C call returned (documented) | the same |
  | Around `train_arm` | the cell ends `failed` with the cap reason and returns normally | the same |

  The fix works.

## 4. The rehearsal: what it measures, and every scaling assumption in R

Measured by the registered functions themselves:
- **Training.** `stage_train` of all 18 cells, 200 updates, at both read layers (E-table included), on the training device. Then full U for ST1, for M-ii (from an appended 2N-row store, as registered) and for LoRA-1. The ruling's larger-of rule is applied to MAF, MSEQ, MAGOLD (ST1 stands in) and LSEQ (LoRA-1 stands in), and recorded in `stand_in_rates`.
- **Scoring, in a fresh CPU child on the rehearsal world.** `stage_evaluate` covers Stage 0, the 18 cells, assembled arms, retrieval, the three routers (router training included), the ensemble and combined scoring. Also `stage_timing` at 200 items × registered repetitions, `stage_recompute`, and `stage_analysis` and `stage_report` on synthetic records of the whole registry.
- **The pre-freeze gates stage on rehearsal seeds, at 4 replicates.** G2 and G4's three panel scorings are scaled.
- **Combined scoring.** `score_combined_cell`, which includes C1, C2 and the separate single-task answers (the extra French pass of the strengthened rule's single-task scores), on a D_cal combined set scaled to |E_C|.
- **No evaluation panel is scored.**

Scaling assumptions that enter R (marked ↓ where they can make R too small):
1. **↓ E_open is not in the rehearsal world or in the scale (N1).** `rehearsal_world` replaces `ctx.panels` with {E_A: D_cal A, E_B: D_cal B} only (`rehearsal.py:140`). `scale_factor` counts E_A + E_B only (`rehearsal.py:59`). But `cells.score_snapshot` scores every `ctx.panels` entry at every snapshot (`cells.py:211`), and the registered world has `E_open_A` and `E_open_B` (`worldio.py:153-156`; up to 500 items each, against 1,000 + 1,000 for E_A + E_B). Stage 0 and G2 score them too. So panel scoring of up to one third of the registered items is never timed, in evaluate and again in the recomputation. On the ADR's own projection of the E_A/E_B scoring row (1.9–6.2 h for four replicates) this is up to about 1.0–3.1 h in each of evaluate and recompute, and so up to about 4–12 h of cap after doubling. This is a projection, not a measurement.
2. Scoring time is proportional to item count, and D_cal items stand for E items in length and generation length (↓ if E sentences are longer).
3. The rehearsal scores 200-update snapshots, and registered scoring is of 2,000-update arms. Generation length can differ either way (↓ possible).
4. The scale s = (|E_A|+|E_B|)/(|D_cal A|+|D_cal B|), 2.0 with the configured sizes, also multiplies the fixed-size per-replicate parts: GEN windows, routers, retrieval and 300-item ablations. That over-counts (conservative).
5. **↓ MJOINT, ETABLE and LJOINT use 200-update rates only (m2).** No full-length factor applies to them, while MAF, MSEQ, MAGOLD and LSEQ take the larger of the two rates. In the exercise the short rates were larger (warm-up), but drift over long MPS runs (allocator growth, thermal throttling) would go the other way.
6. U = 1,000 training is 1,000 × the per-update rate (rate independent of U).
7. Per-process start-up is counted for every training cell, every scored cell (18 per replicate, in evaluate and recompute), the gates stage and timing. Registered stages are single processes, so this over-counts (conservative).
8. Combined scoring is taken at the slowest arm kind on the rehearsal set, scaled by |E_C|/m. The LoRA and L-sep arms timed there are untrained (direction unknown). The per-replicate measured total keeps the combined part at scale s rather than |E_C|/m. That is conservative while s ≥ |E_C|/m (2.0 ≥ 1.0 at the configured sizes).
9. The recomputation is projected as one repetition of scoring (the probe's measured recompute time is recorded but not used). Evaluate and recompute now share one environment.
10. The second gates stage is the measured pre-freeze gates time with G2 and three G4 panel scorings scaled by s. G4's scorings are approximated by a NullArm "none" scoring of the first panel (↓ slightly: a memory arm under the oracle route does more work). G2 lacks E_open (as in 1).
11. Analysis is timed on a synthetic registry with an injected missing cell, so **no bootstrap interval is computed** (`analysis.py:721`). R8 puts one registered interval at 15 ms at 1,000 items, so about 5 s for about 300 intervals. The 60 s floor covers it (m10).
12. **↓ Memory (m1).**
    - The peak is max(RSS, MPS driver, MPS allocated), not their sum. R2 shows MPS memory is not in RSS, so the footprint is understated when both are large.
    - Every rehearsal peak comes from one-replicate worlds, while registered processes build four. The pre-freeze gates stage builds four but its peak is not recorded in the rates.

## 5. The recomputation

- **Every recomputed quantity is compared.** `compare_study` compares:
  - cell `scores` and `extras`;
  - `baseline` (Stage 0, teachers and the combined Stage 0/ensemble);
  - per replicate: `assembled`, `retrieval`, `routers` and `ensemble`.

  A missing section is incomplete. Verdicts are compared through `analysis.verdicts`, which covers gates, ensemble checks, classes, per-cell gates, annotations including ROUTER QUALIFIED, composition, GEN under both decisions and controls. The verdict path holds no number.
- **Tolerance.** The registered analysis passes `"frozen-code"`, so the tolerance is 0.0 (bitwise; NaN equals NaN; sequences equal as tuples).
- **Probes (R3), with my own checks.**
  - *Identical records:* complete, 0 differences, label unchanged.
  - *A 1e-15 change to one cell score:* listed; that cell alone NOT_EVALUATED; no EF.
  - *+0.25 on an E-table cell:* listed; NOT_EVALUATED; label unchanged.
  - *Stage 0 E_A +0.05:* listed under `baseline`; 8+ verdicts change, so **ENGINEERING-FAILURE**.
  - *Teacher E_A −0.6:* **ENGINEERING-FAILURE**.
  - *GEN loss increase 1.0 on every M-append-frozen snapshot:* the GEN verdicts flip under both decisions; **ENGINEERING-FAILURE**.
  - *Permutation-control ablations changed:* **ENGINEERING-FAILURE**.
  - *Router accuracy changed with no verdict change:* listed under `r0/routers`; recomputed value reported; no EF.
  - *A missing recomputed ensemble:* **INCOMPLETE**, no class printed.
  - *Memory exceeded:* **INCOMPLETE**, no class printed.

  In every probe, each edit was listed, the NOT_EVALUATED cells equalled the edited cells, and EF held exactly when my verdict comparison differed.
- **Charged inside R.** The recompute stage is charged as `recompute` under `ledger.measure`, and R carries it.
- **Reading noted, not a defect.** A baseline difference that changes no verdict marks no cell NOT_EVALUATED. The recomputed value is reported. The ADR's NOT_EVALUATED rule is stated per cell.

## 6. The end-to-end exercise

- **Covers.** Every pre-freeze and registered launch script in order, the freeze and its commit, the decision commit, the refusals listed in §1, a cap stop, a failed pilot, and a recomputation difference. Training ran on MPS in my run. It runs in a source-only clone with the current interpreter and a stub `uv`. No virtual environment is created, and it deletes itself unless `--keep` is given.
- **Substitutions.** The full list is in `outputs/e2e.json` → `substitutions`:
  - seed sets moved into 229001–229999;
  - stand-in sizes, read layers [0, 1], tiny rungs and tiny update counts;
  - `timing_items` 3;
  - after the real 0.25 threshold has stopped the sequence once, `gates.pilot_gap_min = -1.0`, committed in the clone.

  All of these are writes to the clone's `configs/p10s2_transfer.toml`.
- **Could a substitution leak into a real run?**
  - The real configuration is a frozen path, and the freeze hashes it into the plan (`config_sha256`).
  - The test `test_the_clone_is_source_only...` asserts that the real file is untouched.
  - The e2e module is part of `studies/p10s2` and is frozen, but nothing in the registered path imports it.
  - I found no route by which the relaxed pilot or the test seeds could reach a real run.
  - One residual risk: the exercise writes its data-generation ledger charge with a direct `Ledger(...)` call. Run without a clone, `Ledger()` would be the real one, but `exercise()` always builds a clone first.
- **Still unexercised:**
  - `datagen.sh` (needs downloads) and `fetch`;
  - real sizes: 1,000-item panels, 2,000 updates, the 135M student; MPS memory at that size;
  - the U = 1,000 path through the freeze (the snapshot selection);
  - a raise recorded by the freeze (the exercise's rates fit 36 h, so `proposal` was null);
  - the CPU-by-freeze path;
  - a stage stopped by its frozen cap inside the registered sequence;
  - the memory watchdog in a registered stage;
  - E_open at any size: the stand-in bundle has no E_open item (R14; N1).

## 7. Findings still open

### Majors

**N1. The rehearsal does not time E_open; R and the evaluate, recompute and gates caps are too small.**
- Where: `rehearsal.py:56-61` (`scale_factor`) and `rehearsal.py:133-147` (`rehearsal_world` keeps only E_A and E_B). The registered `cells.score_snapshot` (`cells.py:211`) scores every panel, E_open_A and E_open_B included, at every snapshot, and so do `stage0_scores` and G2.
- Effect: up to 1,000 of 3,000 panel items per snapshot are untimed in evaluate and in the recomputation (task 4, item 1).
- It is also never exercised. The stand-in bundle has **0 E_open items** (R14, `outputs/r14_standin_e_open.txt`), so the dry stage, the tests and the exercise never score an E_open panel. The exercise's evaluate records hold only `E_A` and `E_B`.
- Fix: in `rehearsal_world`, add D_cal stand-in panels named `E_open_A`/`E_open_B` scored under the oracle route only, or add |E_open_A| + |E_open_B| to the numerator of `scale_factor`. Add a test that the rehearsal world has the same panel names as the registered world.
- When: **before the pre-freeze gates stage and the rehearsal.**

**N2. A registered stage accepts a study ledger that does not hold P.**
- Where: `freeze.verify_plan` (`freeze.py:141-170`) compares only the ledger's cap with the plan's.
- Demonstration: R6 P1. With `experiments/P10S2/ledger.jsonl` moved aside, `report.sh` ran (exit 0) against P = 0. The same happens in any other worktree of the repository, because the ledger is git-ignored and per checkout. When the cap was raised, a fresh ledger is refused (its cap is 36), so the hole is open exactly when the cap is 36 h.
- Fix: at the freeze, record in the plan the ledger's line count and the SHA-256 of those lines. `verify_plan` refuses unless the ledger starts with exactly those lines, and unless `total_hours() >= plan["charged_hours_at_freeze"]`.
- When: **before the freeze** (the plan's content).

**N3. The freeze accepts typed, stand-in or mismatched pre-freeze records (defect class b).**
- Demonstration (R7). Each case was run in a new repository made from the exercise clone's pre-freeze commit, with the pre-freeze ledger. The freeze **accepted**:
  - `--data-dir` naming a different stand-in bundle from the one calibration and the rehearsal read ('bundle');
  - a calibration record that says 6 updates where the configuration says 150 in the exercise and 2,000 registered ('cal_upd'; a typed `--updates`);
  - a rehearsal whose full-length cells ran 1 update ('full_upd'; a typed `--full-updates`);
  - `train_device = "cpu"` with a typed reason and no failed MPS attempt ('device'). The ruling allows CPU only "if the rehearsal itself cannot run on MPS", and the code accepts any non-empty `--device-reason` (`freeze.py:237-240`, `stages.py:734, 776`);
  - a calibration record marked `{"synthetic": true, "mode": "test"}` ('dry_rec').
- Cause: `calibration.json`, `prefreeze_gates.json` and `rates.json`/`rehearsal.json` carry no identity. There is no data-manifest digest, code commit, configuration digest or seed mode, and the update counts are not checked.
- Fix:
  - (a) Calibrate, prefreeze-gates and rehearse write into their records the SHA-256 of the bundle's `manifest.json`, the code commit, the configuration SHA-256, the seed mode, the update counts and the device. On CPU they also write the failed MPS attempt (the exception text of a rehearsal run that failed on MPS).
  - (b) Remove `--updates`, `--full-updates` and `--device` from the pre-freeze parser, or refuse values other than the configuration's. The exercise substitutes through its clone's configuration anyway.
  - (c) `write_freeze` refuses unless every record's manifest digest equals `data_dir/manifest.json`'s and equals the data-generation record's, the counts equal the configuration (`calibration.updates`, `calibration_snapshot_updates`, `rehearsal.short_updates`/`full_updates`), the mode is calibration/rehearsal, and CPU comes with a recorded MPS failure. Whether the records must also share the freeze's code commit is **PENDING LEAD REVIEW**.
- When: (a) and (b) **before calibration**, because a record written without its identity cannot be checked later and re-running calibration is a second attempt. (c) **before the freeze.**

### Minors

| # | Finding | Fix | When |
|---|---|---|---|
| m1 | Memory measure: `max` of RSS and MPS instead of the sum (`train.py:72`). Rehearsal peaks come from one-replicate worlds (`rehearsal.py:178-188, 339`), while registered processes build four. The pre-freeze gates guard's peak (four replicates) is not saved | Use the sum (or `phys_footprint`). Record the pre-freeze gates peak and feed it to `task_peak_bytes`. Build the start-up child at the largest rung's replicate count | before the rehearsal |
| m2 | MJOINT, ETABLE and LJOINT take 200-update rates only. The larger-of rule is applied only where the code chose a stand-in (`rehearsal.py:93-98`) | Apply max(own short rate, the full-length rate of the same family) to them too, or state the reading. **PENDING LEAD REVIEW** if kept | before the rehearsal |
| m3 | (i) `tests/test_p10s2_integration.py:71` asserts `not (REAL_ROOT/"experiments"/"P10S2").exists()`. It fails in the real repository once fetch or data generation has charged the ledger (T3: 4 failures with the ledger, which cannot be fixed after the freeze without changing a frozen file). (ii) The guard (`core.py:62-76`) is keyed to temporary roots. A checkout under `/tmp` gets no protection (T1 created `experiments/P10S2` in the pin) | (i) Compare before and after state (as the ledger test does). (ii) Also refuse any root under `REAL_ROOT` unless it is a pytest basetemp | before data generation (at the latest before the freeze) |
| m4 | `budget.py:214` `ceil(need - 1e-12)` can give a cap at which rung 1 does not fit (R1 boundary) | `math.ceil(need)`, or assert rung 1 fits at the computed cap | before the freeze |
| m5 | The frozen caps sum to 2R + 2 × start-up (R11). The timing cap includes a start-up (`budget.py:323`) that `scoring_seconds` (`budget.py:120-123`) does not | Add the start-up to the timing row of R, or drop it from the cap | before the freeze |
| m6 | `cmd_prefreeze_gates` and `cmd_rehearse` do not catch `CapReached`/`MemoryLimitExceeded`/`RehearsalFailed`. They end in a traceback with no stop record, while calibrate writes `calibration_stopped.json`. Prefreeze-gates also runs after a failed pilot (`stages.py:723-754, 757-798`) | Catch the exceptions, write `*_stopped.json`, exit 4. Refuse prefreeze-gates after a failed pilot | before the rehearsal |
| m7 | The freeze uses P at freeze time (`freeze.py:218`), not the rehearsal-end P that the ADR names and that `rehearsal.json` records. A raise recorded by `raise-cap` at P₁ makes any freeze at P₂ ≠ P₁ refuse permanently (once only) | Use `charged_hours_at_end_of_rehearsal`, and check the ledger has no later charge. Or drop the separate `raise-cap` command | before the freeze |
| m8 | An orphan start marker is charged `now - t_start` without bound (`ledger.py:72`). After a killed registered stage, every later stage is refused as wall time passes | Charge min(elapsed, the stage's frozen cap). **PENDING LEAD REVIEW** (an accounting rule) | before the freeze |
| m9 | `train_arm` restores `deterministic=True` without `warn_only` (`train.py:224-225`) | Restore both | any time |
| m10 | The rehearsal's synthetic registry always injects a missing cell, so the analysis computes no bootstrap interval and `analysis_seconds` excludes them (R8: about 5 s at registered size; the 60 s floor covers it) | Time the intervals on a copy without the missing cell, or record the omission | before the rehearsal (nice to have) |
| m11 | No driver token: `seeded_generator(..., "registered-run")` accepts any in-process caller, and such a draw is not in the study ledger | Require an environment token set by `cmd_registered` (its ledger run id) before a registered-run seed is issued | before the freeze (optional) |
| m12 | A registered stage that ends `failed` (for example evaluate failing outside its per-replicate guard) blocks every later stage, and no outcome or label record is written | An `analysis`-only path that writes ENGINEERING-FAILURE/INCOMPLETE from the stage records. **PENDING LEAD REVIEW** (the ADR says a second attempt needs the human lead) | before the freeze |
| m13 | `gates.json` is not bound by hash to `stages/gates.json`, so an edited gates record is read as written | Store its SHA-256 in the stage record and check it in `require_order` | before the freeze |

## 8. Scientific questions flagged (PENDING LEAD REVIEW)

- N3 (c): must every pre-freeze record share the freeze's code commit?
- m2: does ST1 or LoRA-1's full-length rate stand in for M-joint, E-table and L-joint?
- m8: the bound on the orphan charge.
- m12: the record after a failed mid-sequence stage.
- The reading in §5: a Stage 0 or teacher difference that changes no verdict marks no cell NOT_EVALUATED.

## Files

Everything below is under `R` = `/private/tmp/claude-501/-Users-daniellaloush-dandush03-ArborLM--claude-worktrees-arborlm-consolidation-experiment-2b31c1/cfc0efd5-b7ca-4602-959a-07fe6b8d4e7d/scratchpad/p10s2-recheck-B/`.

- **Scripts** (`scripts/`): `r1_cap_rule.py`, `r2_device_memory.py`, `r3_recompute.py`, `r4_watchdog.py`, `r5_frozen_clone.sh`, `recheck_location_plugin.py`, `r6_registered_guards.sh`, `r7_freeze_inputs.py`, `r8_bootstrap_cost.py`, `r9_failed_cells.py`, `r10_freeze_commit_identity.sh`, `r11_caps_vs_R.py`, `r13_datagen_charge.py`.
- **Outputs**: in `outputs/`, as listed in the table above.
- **Kept work directories** (none over 100 MB, so none deleted):

  | Directory | Size |
  |---|---|
  | `e2e/` (the kept clone) | 29 MB |
  | `frozen-clone/` | 54 MB |
  | `r7work/` | 34 MB |
  | `pytest-tmp/` | 23 MB |
  | `pytest-frozen-tmp/` | 23 MB |
  | `r9work/`, `r10git/`, `r13work/`, `tmp/` | small |
- **Failed checker attempts (kept, `failed_attempts/README.txt`).** All five are my own errors and none is evidence of a defect:
  1. r1's boundary probes used negative P (unphysical). The result was unchanged.
  2. pytest without `PYTHONPATH=<pin>/src`: the virtual environment's `arborlm` comes from another worktree, `check_code_location` refused, and `-x` stopped the run.
  3. r5's clone lacked `docs/reviews/...`, so collection failed.
  4. r7 built a bundle with the clone's test-seed configuration, so it was refused by the seed function.
  5. r10 ran inline in zsh with no word splitting, then hit a missing `mkdir`.
- **Pinned tree state.** `git status --porcelain` is empty. The ignored `__pycache__/` folders, `studies/p9/__pycache__` among them, were written at 14:22–14:25 while another process (PID 59160, not mine) used the same pin. My runs set `PYTHONDONTWRITEBYTECODE=1`. The only file my runs created there was the empty `experiments/P10S2/`, which I removed.
