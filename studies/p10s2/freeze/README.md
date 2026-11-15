# P10-S2 freeze procedure (ADR-0022 revision 5, sections 13, 16; the lead's rulings of 2026-11-15)

Status: procedure only. Nothing in this directory is a freeze: `plan.json`, `stage_caps.json`, `cap_raise.json`, `rehearsal_outcome.json`, `projection.json` and `records/` do not exist until the freeze procedure writes
them, and every registered stage refuses to run without them. Astra review: NOT_PERFORMED. The implementation was made on synthetic stand-ins only (ADR section 18, "Lead's approval for implementation on synthetic
stand-ins"); the exercise `python -m studies.p10s2.e2e` runs the whole sequence below through the real launch scripts on test seeds in a throwaway clone (see the end of this file).

## The one study ledger

Charged hours are the sum of wall-clock hours over all S2 processes (k workers for t hours charge k t). There is ONE append-only ledger, `experiments/P10S2/ledger.jsonl` (git-ignored, outside every run
directory), used by the fetch step, the data-generation step, calibration, the pre-freeze gates stage, the rehearsal, the freeze and every registered stage. Every stage writes a start marker before it does anything
and an end entry whether it completes or raises; a start marker with no end (a killed process) is charged the time elapsed since it. P, the hours already charged, is therefore the same number in every stage. Every
stage refuses at start if the ledger has no room for its cap (a registered stage: its cap plus the reserved analysis and report caps). The cap raise is an entry of this ledger.

## Order (each step before the next; the freeze commit is step 8)

1. Downloads (human-approved files only; `studies/p10s2/fetch.py`).
2. Data-generation step, once: `sh studies/p10s2/launch/datagen.sh <run-dir> <code-commit>` (the only place with packages outside the lock). Charged to the study ledger and capped.
3. Calibration and the pilot gate: `sh studies/p10s2/launch/calibrate.sh <run-dir> <code-commit>`. Calibration seeds, D_cal only, training on MPS (the configured device; there is no automatic choice). A pilot gap closed
   below 0.25 on either capability ends in NOT STARTED: STUDENT CANNOT USE THE MEMORY ON THIS TASK. Writes `<run-dir>/calibration.json` (write-once); a stage cap stops it (exit 4, `calibration_stopped.json`).
4. The gates stage at real size on rehearsal seeds: `sh studies/p10s2/launch/prefreeze_gates.sh <run-dir> <code-commit>`. It runs on the rehearsal world: calibration items stand in for every evaluation panel, so no
   evaluation panel is scored and no gap on one is computed before the freeze (the lead's ruling A-M3). Writes `<run-dir>/prefreeze_gates.json`; its time, scaled by the registered item counts, is the second gates stage's
   time in R.
5. Rehearsal: `sh studies/p10s2/launch/rehearse.sh <run-dir> <code-commit>`. It reads the read layer and the calibrated LoRA learning rate from `<run-dir>/calibration.json` (and refuses without it or after a failed pilot),
   and needs `prefreeze_gates.json`. It runs the registered stage functions themselves: training of all 18 cells for 200 updates at each read layer (E-table included), the full-length store, M-ii (from an appended
   2N-row store) and LoRA cells, and in a fresh child process on CPU the evaluate, timing, recompute, analysis and report stages on synthetic records of the whole registry; memory is the larger of the resident set and the
   MPS driver's allocation. Writes `rates.json` and `rehearsal.json` (write-once).
6. The cap is a computed rule, not a discretion (the lead's ruling of 2026-11-15): 36 hours if rung 1 (four replicates, U = 2,000) satisfies P + 2R <= 36 (R includes the rehearsed analysis and report time); otherwise the
   smallest whole number of hours up to 72 at which rung 1 satisfies it; otherwise 72, with the rung order applied against 72; if no rung fits, NOT STARTED: BUDGET. The freeze computes it from `rates.json` and the study
   ledger (`budget.computed_cap`) and records the raise itself, once everything else is accepted; the lead may also record it earlier, at this headroom check only, with
   `uv run --locked python -m studies.p10s2.stages raise-cap --run-dir <run-dir>` (the amount is recomputed, never typed). A raise is refused after any registered seed has been drawn (study ledger, seed record, or a
   plan committed in the history) and a second time; a freeze that finds any recorded cap other than the computed one is refused. The raise is an entry of the ledger and `studies/p10s2/freeze/cap_raise.json`.
7. The freeze (the rung rule in its registered order: 4 x 2,000, 3 x 2,000, 4 x 1,000, 3 x 1,000, else NOT STARTED: BUDGET):
   `uv run --locked python -m studies.p10s2.stages freeze --pre-run-dir <run-dir> --run-dir <registered-run-dir> --data-dir <data bundle, relative to the repository>`.
   Nothing typed enters the plan: the layer, the learning rates and the pilot result come from `calibration.json` (for U = 1,000 from the 1,000-update snapshots), the design from the rung rule, the cap by the rule above (a
   recorded raise is re-derived and must agree), the device from the rehearsal: MPS, or CPU only if the rehearsal itself could not run on MPS (`--device-reason`, recorded; every rate is then rehearsed on CPU, and
   gate G4's MPS comparison prints NOT APPLICABLE — TRAINING ON CPU BY THE FREEZE; in every other registered run G4 must run and pass; no device change after the freeze). It refuses on a failed pilot, a failed
   pre-freeze gates stage, a registered seed, provisional pre-freeze caps, test (a) of the tokenization step absent or with a mismatch, NOT STARTED: BUDGET; refusal records go to `experiments/P10S2/refusals/`, never into this folder. It copies the records into `studies/p10s2/freeze/records/` and writes
   `stage_caps.json` (one entry per design configuration and stage, 2x the projection, task start-up included), `plan.json`, `projection.json` and `rehearsal_outcome.json`. The data bundle must be inside the repository
   (git-ignored `data/`): `plan.json` names it relative to the repository.
8. The lead writes the section 16 freeze record and makes ONE freeze commit containing `plan.json`, `stage_caps.json`, `projection.json`, `rehearsal_outcome.json`, `records/` and, if made, `cap_raise.json`.
   `--freeze-commit` must be the commit that added `plan.json`.
9. The run decision, AFTER the freeze commit and in a LATER commit, outside every frozen path: `results/p10s2-freeze-<date>/DECISION.md`, containing the exact line `DECISION: RUN` and the full 40-character freeze commit
   hash. (The ADR is a frozen path: nothing is written into it after the freeze commit. Every post-freeze record goes under `results/`.) Registered stages refuse without it.
10. Launch, in this order, each with `sh studies/p10s2/launch/<stage>.sh <registered-run-dir> <freeze-commit>`: `gates`, `train`, `evaluate`, `timing`, `recompute`, `analysis`, `report`.

## What every registered stage enforces

The only arguments are the run directory and the freeze commit (and the frozen caps path, which must be exactly `studies/p10s2/freeze/stage_caps.json`): there is no `--repo`, no typed caps file, no device or design
argument. The stage refuses unless: the study package and the library that run lie under the checked repository; the working tree is clean; the freeze commit is the commit that added the plan and an ancestor of
HEAD; `studies/p10s2`, `studies/__init__.py`, the config, the ADR, `src/arborlm`, `uv.lock`, `pyproject.toml` and every `tests/test_p10s2_*` equal their content at that commit; every identity in `plan.json` holds
(including the digest of the code and the copied records); the study ledger's cap equals the plan's; a committed run decision exists; the design is a registered rung; the stage has a cap for that design; the ledger has
room for the stage's cap plus the reserved analysis and report caps; the frozen device (MPS for gates and training, CPU for scoring and recomputation) can be used by this process (no fallback); the predecessor stage has
a completion record (`gates` all passed, then `train`, `evaluate`, `timing`, `recompute`, `analysis`, `report`); and the stage's own record does not exist (a stage is run once). Outputs are write-once. Each stage runs
under a guard: its frozen cap is a deadline (a cell running when it is reached ends `failed` with the reason), the sampled memory (resident set and MPS memory) is held to 8 GiB per worker and recorded in
`<run-dir>/memory/<stage>.json`, and the seeds actually used are recorded in `<run-dir>/seeds/<stage>.json`. Evaluation, recomputation and the gates stage use the same six threads and the same deterministic-algorithms
setting. The recomputation is charged and no result is reported before it completes (ADR section 13.3); it compares every recomputed quantity and every gate and control verdict.

## The end-to-end exercise

`uv run --locked python -m studies.p10s2.e2e` (or `P10S2_E2E=1 uv run --locked pytest tests/test_p10s2_fixB_e2e.py`) runs steps 3 to 10 through the real launch scripts on test seeds in a source-only throwaway clone with
the current interpreter (no new virtual environment), including a calibration stopped by its stage cap, refused stages (no gates record, a typed caps file, `--repo`), a second run of a finished stage, and one recomputation
difference. It deletes itself when done.

## Readings fixed by the lead on 2026-11-15

The implementer chose these where the ADR is silent, and the lead accepted them (an addendum to ADR-0022 will record them). Each is the harder-for-a-positive reading or the only workable one.

1. ACQ for L-seq: G >= 0.50 and the 0.80 ratio for ACQ2 only, printed with "NO PERMUTATION CONTROL (ADAPTER)" (an adapter has no keys or word codes to permute).
2. The lexical margin and the marker-only limit are read on the 300-item subsample (like for like with the controls); the 0.50 thresholds on the full panel.
3. The panel a permutation control is read on (CONTROL-FAILED): the capability the permutation targets (the second capability for a stage-2 arm; both for single-stage cells that train both).
4. The GEN gate holds for an arm only if it holds at every one of its memory snapshots (first stage and stage 2) in every replicate; a missing or non-finite value is not a hold.
5. Annotations the ADR leaves open are read on the mean over replicates (and over both orders where an arm has two); EXACT-MATCH WEAK is read on M-append-frozen after Stage 2.
6. Seen items: one permutation of each accepted pool drawn once with seed 220907 in the partition step; a replicate's seen items are the first 300 of its own training draw in that order.
7. G1: panels are checked against everything; T_A and T_B against each other in English; pools in the data step and streams in the gates stage (a registered replicate seed cannot be observed before the freeze). Two training streams may share an identity group.
8. "Registered seed observed" (the cap raise): a replicate seed (base + offset). The partition-side seeds 220901-220905 and 220907-220912 are drawn before the rehearsal (in the data step); 220906, the bootstrap seed, is drawn in the analysis stage only.
9. The ADR's partition and vocabulary details: evaluation groups are added until 20% of the remaining pairs is reached, stopping at the first group that reaches it; vocabulary frequency per sentence id, ties alphabetical; gold pairs take the first reference in sorted order.

Other rulings of the same date: memory is 8 GiB per worker and 24 GiB aggregate with `workers = 1`, and the rehearsal must show twice the measured peak within them; the pre-freeze stage caps in the configuration are provisional and the freeze refuses until the rehearsal replaces them with twice the measured wall time (`prefreeze_caps.json`); the rehearsal includes the full-length store, M-ii and LoRA cells (`--full-updates`); `rms_norm_eps` is read from the model's own config file at load and checked by gate G8; the fetch manifest requires the blob hashes; the C1/C2 combined-task layouts were then specified by the lead (the section below).

## Combined tasks (ADR-0022 addendum, human-approved 2026-11-15)

C1 and C2 and the strengthened COMPOSES rule are implemented as the addendum states (`studies/p10s2/combined.py`, `classes.comp_cell`, `analysis.composition`). The listed seed 220911 draws the C1 pairing once, in the partition step, and the pair list is hashed in the data manifest. The rehearsal scores a D_cal set (never E_A, E_B, E_C or E_open), times one combined scoring of each kind of arm, and stops on any difference between cache continuation and full recomputation. The bootstrap intervals over items cover the combined cells too; seed 220906 is drawn in the analysis stage only (seed mode `registered-analysis`).

## Integration of the fix lanes (2026-11-15)

Three parallel lanes fixed the three implementation audits and their branches were merged into `claude/p10-s2`; one implementer then made the merged tree one implementation. Their hand-off notes (`HANDOFF_A.md`,
`HANDOFF_B.md`, `HANDOFF_C.md`) are deleted; what each asked for, and what was done, is summarised here. Self-check only: not independent review, not Astra validation, not human approval.

**Lane A (data, seeds, tokenization, fetch, data generation).** (1) `ledger.charge/remaining`: the study ledger has both; `datagen.main` now passes `Ledger()` and the step runs under `Ledger.measure("datagen")` (a start
marker first, an end entry on failure too) and a `stages.StageGuard` (the stage cap as a watchdog); a refusal to start leaves no record, a stop after the start keeps one. `fetch.run` runs under `measure("fetch")`.
(2) Strict G9: `gates.g9` calls `core.seed_gate(..., stage_mode=mode, allow_partial=...)` with `core.planned_seeds` (every replicate, the +10 code seed included); the +10 seed is a recorded use (`SeedPlan.code_seed()`),
so `gates.record_code_seeds` is deleted; the listed partition seeds are 220901-220912 (`core.listed_partition_seeds`); 220906 is drawn in the analysis stage only (`registered-analysis`, `gates.g9_analysis`).
(3) `stage_timing` uses `World.timing_items` (the stored 220908 draw); a registered world without them is refused; the rehearsal world times its first D_cal items. (4) The freeze refuses when
`tokenization_required_ok` is false. (5) G8 runs `equivalence.verify_all` over every layer the data step stored (`gates.equivalence_layers`) and restores the read layer. (6) `launch/datagen.sh` has `--extra pilot`.
(7) `RunConfig.registered` has no default device and `train.select_device` no `auto`: no silent fallback.

**Lane B (stages, ledger, budget, freeze, rehearsal, recomputation, gates, launch scripts).** Requests to A: the ledger/guard (above), the unchanged output layout (`<out>/bundle`, `<out>/prefreeze_record.json`), the +10
seed (above), 220912 in G9 and in `configs/p10s2_transfer.toml` (`partition_streams` now ends 220912). Requests to C: `recompute.outcome_under_recomputation` supersedes `analysis.analyze_with_recomputation`
(deleted); the comparator inside it is C's `analysis.verdicts` / `verdict_changes` (B's `verdict_view` and `outcome_changes` are deleted: one verdict function, no number in it); `analysis.analyze(study, recompute_ne)` and
`strip_classes_if_incomplete` keep their names. The stage code calls the one gates function set; a missing gates record or gate is read by the analysis itself (INCOMPLETE), so `stages.gates_problems` is deleted.

**Lane C (analysis, classes, report, output, routing, evaluate, cells, combined).** `stage_analysis` passes `bootstrap_mode` (seed mode `registered-analysis`; `test` in the dry stage) and the recomputed study to
`outcome_under_recomputation`; the intervals are drawn for the printed outcome only and the compared analyses draw nothing; `analysis.bootstrap_generator` is deleted in favour of `core.bootstrap_generator`;
`worldio.build_world` builds `E_open_A` and `E_open_B` (the E_open items that carry a reference in that language; descriptive, oracle route only, never in a gap, ablation, learned route or the timing benchmark).

**Rulings of the last ADR-0022 addendum applied.** Both teachers generate on every panel section 6.1 names (`prefreeze.TEACHER_PANELS`: E_A, E_B, E_C, E_open, D_cal, D_con) and are stored; each teacher is scored on a panel
against the references of its own capability (E_A, E_B, E_open); the other teacher's score on a single-capability panel is not computed (see the point returned to the lead below). Device rule (above). The cap rule
(step 6). The analysis and report reserve is the sum of their frozen stage caps, each at least 60 s (`budget.stage_caps`, `stages.reserved_seconds`). Stand-in full-length cells: the projection uses the larger of the stand-in
rate and the type's own 200-update rate and the record says so (`rehearsal.full_length_rates`, `stand_in_rates` in the rehearsal record). A missing G2 (or G3) gives INCOMPLETE; a failed gate gives
ENGINEERING-FAILURE. E_open is built and scored.

**What the tests guard.** Registered code, the study ledger and the freeze commands refuse under pytest unless their root is a temporary directory (`core.refuse_under_pytest`); no test can start a registered stage
against the real repository, the real `experiments/` directory or the real ledger.

**Returned to the lead, not chosen.** Section 6.1 says the untrained student and both teachers are scored on every panel. E_A holds German references only and E_B French only, so the score of the other
teacher on them (teacher B's French output against German references, or the reverse) has no reference to be scored against without choosing one; it is not computed. The outputs of both teachers on every panel are generated
and stored, so the choice can be made later without a new data-generation step.
