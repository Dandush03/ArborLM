# P10-I-R — registered run, stage groups A1 and A2 (2026-11-18 UTC)

**Read `OUTCOME.md` first.** Record of the registered run as the frozen code wrote it, with the independent recomputation of A1. Nothing here is a success claim. `Astra review: NOT_PERFORMED`.

Freeze commit `c712a90`; Decision 2 for A1 at `3f54642` (`results/p10ir-freeze-2026-11-18/`). Run directory `experiments/P10IR-registered-20261118` (not in git). Stages: gates-a1 COMPLETE (3.4 s), a1 COMPLETE (70 tasks, 280 checkpoints, 0 item errors, 4,003.4 s charged, cap 6 h), analysis COMPLETE, report COMPLETE; 04:35 to 05:42 UTC.

| File | What it is |
|---|---|
| `REPORT.md` | The registered report, as written by the frozen report stage |
| `analysis.json` | The registered analysis record |
| `gates-a1.json`, `manifests/` | Gate record and stage manifests |
| `ledger_after_a1.json`, `ledger_after_a2.json` | Charged time |
| `OUTCOME.md` | The outcome record: labels, numbers, the recomputation, what the result does and does not show, acceptance |
| `confirm/` | The confirmatory part's report and record (A2) |
| `audit_a1/` | The independent recomputation of A1 (Opus 5.5): report, scripts (a first line `# ruff: noqa` added by the lead), outputs |

Registered labels (from `REPORT.md`; every label carries REGISTERED RE-ANALYSIS OF OBSERVED CELLS; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK):

- R-DIAGNOSIS: EVALUABLE.
- Tree component: EXACT SEARCH HARMS, at U_P and at the run length, at both primary cells (8K/4K and 32K/16K). Recommended action: none.
- Index component: INDEX APPROACHES FLAT ONLY ABOVE 512, at both checkpoints and both primary cells. Recommended action: none.
- R-CONFIRM-TREE: CONFIRMED and R-CONFIRM-INDEX: CONFIRMED on fresh checkpoints (stage group A2; `confirm/REPORT_CONFIRM.md`; recomputation of A2 pending).
