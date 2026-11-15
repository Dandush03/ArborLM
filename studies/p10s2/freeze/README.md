# P10-S2 freeze procedure (ADR-0022 revision 5, sections 13, 16)

Status: procedure only. Nothing in this directory is a freeze: `plan.json`, `stage_caps.json`, `cap_raise.json` and `rehearsal_outcome.json` do not exist until the lead writes them, and every registered
stage refuses to run without them. Astra review: NOT_PERFORMED. The implementation was made on synthetic stand-ins only (ADR section 18, "Lead's approval for implementation on synthetic stand-ins").

## Order (each step before the next; the freeze commit is step 8)

1. Downloads (human-approved files only; `studies/p10s2/fetch.py`, which refuses without `--i-have-recorded-human-approval` and a manifest; the wheels only after the human lead's confirmation with sizes).
2. Data-generation step, once: `sh studies/p10s2/launch/datagen.sh <run-dir> <code-commit>` (the only place with packages outside the lock).
3. Calibration and the pilot gate: `sh studies/p10s2/launch/calibrate.sh <run-dir> <code-commit>`. A pilot gap closed below 0.25 on either capability ends in NOT STARTED: STUDENT CANNOT USE THE MEMORY ON THIS TASK.
4. Rehearsal: `sh studies/p10s2/launch/rehearse.sh <run-dir> <code-commit>`. It measures the rates and the memory peaks (training, evaluation, whole task) and writes the headroom check. Every pre-freeze stage writes to
   `<run-dir>/ledger.jsonl`: charged hours are the sum over all S2 processes (k workers for t hours charge k t).
5. The cap. At this headroom check only, before any registered seed is observed, if four replicates at U = 2,000 do not satisfy P + 2R <= 36, the lead may raise the cap once, to the smallest whole number of hours at
   which they do, up to 72 (`budget.propose_raise`, `budget.record_raise`; the mechanism refuses after any registered seed has been observed, a second raise, a cap above 72 or a value that is not the smallest
   whole number). The record goes to `studies/p10s2/freeze/cap_raise.json` and into the freeze commit.
6. The rung rule in its registered order: 4 x 2,000, 3 x 2,000, 4 x 1,000, 3 x 1,000, else NOT STARTED: BUDGET (recorded in `rehearsal_outcome.json`; the work returns to the human lead):
   `uv run --locked python -m studies.p10s2.stages freeze --rates <run-dir>/rates.json --ledger <run-dir>/ledger.jsonl --run-dir <registered-run-dir> --data-dir <data dir> --calibration <calibration.json> --prefreeze <prefreeze_record.json> --layer L --store-lr LR --lora-lr LR`.
   It writes `stage_caps.json` (one entry per design configuration and stage, 2x the projection with task start-up included; a stage whose configuration has no entry refuses) and `plan.json` (the identities
   registered stages check: configuration, cap table, data manifest, calibration, pre-freeze and projection records, cap in force, design, planned seeds, code digests).
7. The lead writes the section 16 freeze record.
8. One freeze commit containing the record, `plan.json`, `stage_caps.json`, `projection.json`, `rehearsal_outcome.json` and, if made, `cap_raise.json`.
9. Launch, in this order, each with `sh studies/p10s2/launch/<stage>.sh <registered-run-dir> <freeze-commit>`: `gates`, `train`, `evaluate`, `timing`, `recompute`, `analysis`, `report`.

## What every registered stage enforces

The working tree is clean; the freeze commit is an ancestor of HEAD; `studies/p10s2`, the config, the ADR, `src/arborlm`, `uv.lock`, `pyproject.toml` and every `tests/test_p10s2_*` equal their content at that
commit; every identity in `plan.json` holds; the design is a registered rung; the stage has a cap for that design and the ledger has room under the cap in force. The only arguments are the run directory and the
freeze commit. The recomputation is charged and no result is reported before it completes (ADR section 13.3).

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
