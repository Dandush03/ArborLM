# ADR-0025 addendum: Part T ruling 40 (ninth addendum): the measuring rehearsal's one cap extension

Status: ruling of the lead coordinator, taken under the human lead's standing delegation that hour-cap extensions need no asking, and reported to the human lead. Recorded by the implementer from the coordinator's message. Existing ADR and ruling files are not edited. `Astra review: NOT_PERFORMED`.

## What happened

The second Part T measuring rehearsal (attempt 2, code at cb3f954, run directory `/Users/daniellaloush/dandush03/ArborLM/experiments/P10IS2-T-measuring2-20261120`; attempt 1 is `.../P10IS2-T-measuring-20261120`, the failed G4-MPS attempt, ruling 39) completed its gates (including the amended G4-MPS), train, controls, evaluate and combined stages. Its recompute stage was PAUSED by its stage guard at the leftover 2,355 s of the 10,800 s cumulative cap (`stages/recompute.paused.json`: "the stage cap of 2355 s is spent"); the ledger holds 10,801 s; `rehearsal_measuring.json` is INCOMPLETE (problem: `recompute: exit 4, expected 0`); analysis and report did not run. The machine was shared with P10-I-S6's registered run and an audit during the attempt.

## Why

Recompute re-scores every registered score and combined record on CPU, by design (ADR-0025 section 8.6), in one process. The completed stages had charged 8,443 s (gates 1,519; train 1,153; controls 3; evaluate 4,536; combined 1,232), leaving 2,355 s of the fixed cap. The diagnosis (read-only, from the run's ledger and per-task timing records) projected recompute at about 5,700 s (the reference 36 s, the replicate-0 scoring about 4,490 s as in the evaluate task, the combined reference 81 s and the combined replicate about 1,143 s), so about 14,200 s in all, about 3.95 h, alone and at the load of those tasks; about 4.8 h with a 20% contention margin. Recompute keeps nothing when paused, so a resume would restart from zero; and a resume is not possible: nothing is left of the cap, and editing the cap in the config changes the config hash that the measuring plan pins (a resume would be PAUSED — IDENTITY). The completed stages' per-task timings are valid observations but the record carries no rates (`derive_rates` runs only when every stage is COMPLETE), so the caps code cannot use them.

## The ruling

1. **The measuring rehearsal's cumulative cap is raised once, from 3.0 h to 6.0 h** (`caps.measuring_rehearsal_hours` in `configs/p10is2_partt.toml`), the most `extension_factor_max = 2.0` allows (ADR-0025 section 10: raisable once, to twice its value). It is the single extension: no further extension of this cap is allowed. **The code does not track whether the extension has been used** (`extension_factor_max` is not read by any code); the one-extension rule is held by this ruling and by the config value being at twice the original.
2. **A third measuring rehearsal runs in a fresh directory** (`experiments/P10IS2-T-measuring3-20261120`); the two earlier attempts are kept as records and nothing in them is edited.
3. **No rate, score or governed value was read to decide.** The decision rests on the ledger's seconds, the per-task wall times of the completed stages and the ADR's rule; no per-item score, registry value or sealed value was opened.
4. **The registered-run caps still come by code** (`caps-proposal` and `caps-config`, rulings 20 and 22) from the COMPLETE measuring record of the third rehearsal; this ruling sets only the rehearsal's own fixed cap, not any registered cap, the counting allowance, the calibration cap or the study budget bound.
5. **Not decided and not done here:** progress records for recompute, and workers for recompute. Recompute is unchanged.

It is the lead coordinator's decision under the standing delegation, reported to the human lead.
