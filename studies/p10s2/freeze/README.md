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
6. The cap, at this headroom check only, before any registered seed is observed: if four replicates at U = 2,000 do not satisfy P + 2R <= 36 (R includes the rehearsed analysis and report time), the lead may raise the cap
   once: `uv run --locked python -m studies.p10s2.stages raise-cap --run-dir <run-dir>`. The amount is recomputed by the code from `rates.json` and the study ledger (the smallest whole number of hours at which rung 1
   fits, up to 72), never typed; it is refused after any registered seed has been drawn (study ledger, seed record, or a plan committed in the history) and a second time. It is recorded in the ledger and in
   `studies/p10s2/freeze/cap_raise.json`.
7. The freeze (the rung rule in its registered order: 4 x 2,000, 3 x 2,000, 4 x 1,000, 3 x 1,000, else NOT STARTED: BUDGET):
   `uv run --locked python -m studies.p10s2.stages freeze --pre-run-dir <run-dir> --run-dir <registered-run-dir> --data-dir <data bundle, relative to the repository>`.
   Nothing typed enters the plan: the layer, the learning rates and the pilot result come from `calibration.json` (for U = 1,000 from the 1,000-update snapshots), the design from the rung rule, the cap from the ledger and
   the rehearsal record (a recorded raise is re-derived and must agree), the device from the rehearsal (MPS; PENDING LEAD REVIEW for a CPU rehearsal). It refuses on a failed pilot, a failed pre-freeze gates stage, a
   registered seed, provisional pre-freeze caps, NOT STARTED: BUDGET; refusal records go to `experiments/P10S2/refusals/`, never into this folder. It copies the records into `studies/p10s2/freeze/records/` and writes
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
8. "Registered seed observed" (the cap raise): a replicate seed (base + offset). The partition seeds 220901-220910 are drawn before the rehearsal.
9. The ADR's partition and vocabulary details: evaluation groups are added until 20% of the remaining pairs is reached, stopping at the first group that reaches it; vocabulary frequency per sentence id, ties alphabetical; gold pairs take the first reference in sorted order.

Other rulings of the same date: memory is 8 GiB per worker and 24 GiB aggregate with `workers = 1`, and the rehearsal must show twice the measured peak within them; the pre-freeze stage caps in the configuration are provisional and the freeze refuses until the rehearsal replaces them with twice the measured wall time (`prefreeze_caps.json`); the rehearsal includes the full-length store, M-ii and LoRA cells (`--full-updates`); `rms_norm_eps` is read from the model's own config file at load and checked by gate G8; the fetch manifest requires the blob hashes; the C1/C2 combined-task layouts stay STOPPED (`PendingLeadReview`) until the lead specifies them in the ADR, and the provisional layout is test-only and unreachable in calibration, rehearsal or registered mode.

## Combined tasks (ADR-0022 addendum, human-approved 2026-11-15)

C1 and C2 and the strengthened COMPOSES rule are implemented as the addendum states (`studies/p10s2/combined.py`, `classes.comp_cell`, `analysis.composition`). The listed seed 220911 draws the C1 pairing once, in the partition step, and the pair list is hashed in the data manifest. The rehearsal scores a D_cal set (never E_A, E_B, E_C or E_open), times one combined scoring of each kind of arm, and stops on any difference between cache continuation and full recomputation. Not implemented: the bootstrap intervals over items for the combined cells (the addendum names the seed 220906, which G9 allows only in the data-generation and partition steps); reported to the lead.
