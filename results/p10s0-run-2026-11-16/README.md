# P10-S0 — registered run record (2026-11-15/16 UTC)

ArborLM is unproven research. This is the record of the one registered run of P10-S0 (ADR-0020 revision 4 and addenda), frozen at commit `579d332e4f1cb93815be430a720d3eb6467a782e`. **It is not yet independently recomputed and not accepted by the human lead.** Astra review: NOT_PERFORMED.

- Run directory (local, git-ignored): `experiments/P10S0-registered-20261115`. Copied here unchanged: `RESULTS.md`, `results.json`, `classes.csv`, `analysis.json`, `gates.json`, `q1_start.json`, `q1_gate.json`, `draw_plan.json`, every stage manifest (`manifests/`), and the study ledger after the run.
- Stages, all COMPLETE, in the registered order: gates (all passed), Q1 (230 of 230 cells trained and evaluated, no cut), Q1 gate, WX (20 cells), probe (6 cells), analysis, report. No task failed; no draw was replaced by a reserve.
- Charged time (MEASURED): 21,941 s (6.09 h) of the 22-hour cap, the pre-freeze stages included. Q1 training 13,415 s against a projection of 30,276 s (the projection used the rate measured under twelve other busy processes).
- **Registered outcome as printed by the report (row 4): ADDRESSING-QUALIFIED (4,096 AND 16,384)**, arm A5-D (label-free), with the annotations OVERLOAD NOT QUALIFIED and RECORD-LENGTH-FREE VARIANT: DOES NOT PASS. A5-D was added by the human lead's decision after P9-II's outcome was seen; for A5-D this run is a confirmatory replication on new draws, not an unbiased first test.
- The report's section "What may not be said" applies to every use of these numbers. The memory is told the answer position in every arm; nothing here is about capacity, transfer, efficiency or natural language.
