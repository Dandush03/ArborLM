# P10-I-R — registered run, stage group A1 (2026-11-18 UTC)

**Record of the registered run as the frozen code wrote it. Not yet independently recomputed; the outcome record follows the recomputation.** Nothing here is a success claim. `Astra review: NOT_PERFORMED`.

Freeze commit `c712a90`; Decision 2 for A1 at `3f54642` (`results/p10ir-freeze-2026-11-18/`). Run directory `experiments/P10IR-registered-20261118` (not in git). Stages: gates-a1 COMPLETE (3.4 s), a1 COMPLETE (70 tasks, 280 checkpoints, 0 item errors, 4,003.4 s charged, cap 6 h), analysis COMPLETE, report COMPLETE; 04:35 to 05:42 UTC.

| File | What it is |
|---|---|
| `REPORT.md` | The registered report, as written by the frozen report stage |
| `analysis.json` | The registered analysis record |
| `gates-a1.json`, `manifests/` | Gate record and stage manifests |
| `ledger_after_a1.json` | Charged time |

Registered labels (from `REPORT.md`; every label carries REGISTERED RE-ANALYSIS OF OBSERVED CELLS; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK):

- R-DIAGNOSIS: EVALUABLE.
- Tree component: EXACT SEARCH HARMS, at U_P and at the run length, at both primary cells (8K/4K and 32K/16K). Recommended action: none.
- Index component: INDEX APPROACHES FLAT ONLY ABOVE 512, at both checkpoints and both primary cells. Recommended action: none.
- R-CONFIRM-TREE and R-CONFIRM-INDEX: NOT RUN (stage group A2 has its own Decision 2).
