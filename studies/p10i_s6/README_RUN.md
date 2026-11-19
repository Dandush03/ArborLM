# P10-I-S6 run sheet (ADR-0031) — implementation for rehearsal only; the registered run is NOT approved

Self-check material. Not independent review, not Astra validation, not human approval. Durations are estimates from ADR-0031 section 18 (analytical), not measurements. Run everything from the repository root with `uv run --locked python ...`; run the stage that reads downloaded files with `-I` from a directory that is not the data directory.

STATUS OF THIS SHEET: steps marked IMPLEMENTED exist and have unit tests; steps marked NOT WRITTEN do not exist yet (the rehearsal drivers R1, R2, R3 and the D0 data-preparation command). Do not follow this sheet past a NOT WRITTEN step.

| # | Step | Command | Writes | Expected duration | Needs the lead's hand |
|---|---|---|---|---|---|
| 1 | Fetch (network; the only one) | `uv run --locked python -m studies.p10i_s6.fetch --out-dir <data>/wikitext103-train --ledger-dir <data>` | train parquet files (about 0.3 GB), `DOWNLOAD_LEDGER_S6.jsonl` and `.md` (PLANNED rows first, COMPLETE or FAILED after) | minutes | yes: Decision 1 covers it; run it yourself; merge the ledger rows into `DOWNLOAD_LEDGER.md` (its layout could not be read from the implementer's worktree) |
| 2 | D0 data preparation | NOT WRITTEN (`corpus.py` has the functions: `scan_rows`, `select_compact`, `decide_pools`, `write_chunk_table`, `reproduces_select`, `overlap_with_excluded`, `pools_disjoint`; the panel walk uses `studies.p10i_s3.data.walk_panels` and `ledger`) | chunk table, pool counts, manifest with `files`, `table`, `decision.k_max`, `gates`, `panels_file` | about 1 h, RSS up to 8 GiB | yes |
| 3 | P0 parents | NOT WRITTEN as a command (`parents.identity_gate` then `parents.train_new_parents` for `registered` and `calibration`) | twelve backbones `registered00.pt` ... `calibration02.pt`, `*_parents.json` | minutes each | yes: new training; the identity gate must reproduce all nine old digests first, else ENGINEERING STOP |
| 4 | R1 calibration | NOT WRITTEN (`items.calibration_items`, `calibration.extension_decision`, `rate_table`, `calibration_states`, `sealed_bytes`, `write_sealed`, `public_summary` are the parts) | sealed archive outside every git working tree; `rehearsal_public.json` | about 5 to 9 charged hours | yes |
| 5 | `write-rate-table` | `python -m studies.p10i_s6.stages write-rate-table --public <rehearsal_public.json>` | `freeze/rate_table.json` | seconds | no |
| 6 | R2 measuring rehearsal | NOT WRITTEN as a driver (`stages work r2probe` and `cost.unit_costs_from_probes` are the parts; whole processes, overhead separate) | R2 record with `unit_costs` | under 1 h | yes |
| 7 | `candidate-plan --r2 <R2> --data-manifest ... --parent-dir ... --parent-suite ...` | `python -m studies.p10i_s6.stages candidate-plan --run-dir <run> ...` | `freeze/plan.json` (refuses to overwrite without `--supersede`), seed plan | seconds | no |
| 8 | R3 counting rehearsal | NOT WRITTEN | rehearsal record naming the plan file's SHA-256 | up to 16 h cap | yes |
| 9 | `freeze --rehearsal <rehearsal_public.json>` | `python -m studies.p10i_s6.stages freeze ...` | `freeze/freeze_record.json` | seconds | commit, then Decision 2 is the human lead's own |
| 10 | Registered stages (after Decision 2) | `studies/p10i_s6/launch/{gates,train,eval,analysis,report}.sh <run-dir> <freeze-commit>` | records under the run dir | about 16 to 31 charged hours (analytical estimate) | Decision 2 |

Pause for another study's quiet stage: create `<run-dir>/pause-request` (its text is the reason). Workers start no new item while it exists; a training item stops at its next rung snapshot and resumes from it if the resume-identity gate passed (otherwise it restarts from update 0). Remove the file and run the same launch script again.

Seed gate: `uv run --locked python docs/reviews/p10-i-direction-2026-11-17/seed_registry_check_r4.py --own "P10-I-S6 ADR-0031=configs/p10i_s6_*,studies/p10i_s6/*,tests/test_p10i_s6_*"` must print `RESULT: PASS` (it does on the implementer's tree).
