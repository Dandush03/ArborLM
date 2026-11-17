# P10-S1 run record, 2026-11-17 (attempt 2)

Read `OUTCOME.md` first. Nothing here is a success claim. `Astra review: NOT_PERFORMED`.

| File | What it is |
|---|---|
| `OUTCOME.md` | The outcome record: run, registered outcome, throughput, independent recomputation, items waiting for the human lead |
| `RESULTS.md`, `results.json` | The registered report, as the frozen report stage wrote it (its seed-block section is wrong: see `OUTCOME.md` section 4, finding 3) |
| `analysis.json`, `gates.json` | The registered analysis record and the gates record |
| `manifests/` | Stage manifests of attempt 2; the failed throughput stage's record and log |
| `ledger_after_run.json` | Charged time across the calibration, attempt 1 and attempt 2 |
| `supplement/throughput_supplement.json` | The supplementary throughput measurement (ADR-0021 section 25.21); not the registered stage |
| `audit/` | The independent recomputation (Opus 5.5): `AUDIT.md`, its scripts and their outputs. The scripts are the auditor's, unchanged except for a first line `# ruff: noqa` added by the lead so the repository's lint passes |
| `attempt1/train.manifest.json` | Attempt 1's training manifest (S1-INCOMPLETE, 171 of 178 cells refused; ADR-0021 section 25.19) |
| `SHA256.txt` | Digests of the files in this folder |

The cell records, snapshots and data draws stay in `experiments/` (not in git). The freeze records are in `results/p10s1-freeze-2026-11-16/` (attempt 1) and `results/p10s1-freeze-attempt2-2026-11-17/`.
