# P10-I-R — freeze record, 2026-11-18 UTC

Study: ADR-0029 (frozen-checkpoint routing diagnosis, Stage A). Nothing here is a result. `Astra review: NOT_PERFORMED`.

| Item | Value |
|---|---|
| Candidate plan | `studies/p10ir/freeze/plan.json`, SHA-256 `a52da5fbea0fa2123b091562ed8502d776f2bf09a94bc43c3d9e3c3a118b5e56`; 280 A1 items, 40 A2 items |
| Freeze record | `studies/p10ir/freeze/freeze_record.json`, SHA-256 `01c6b11de3402b04aa1a52bdd2ef7e8427de1185c8794d3fe5332fad7cf054d0` |
| Caps (charged hours, six workers) | rehearsal 1.0, A1 6.0, A2 3.0, total 10.0 (ADR-0029 section 20) |
| Counting rehearsal | `rehearsal_count.json` in this folder; run 2026-11-18 04:10–04:34 UTC at commit `7155f88` against that plan file |
| Run directory | `experiments/P10IR-registered-20261118` (not in git); holds only the bridge draws' manifests so far |

**Counting rehearsal.** Candidate phase COMPLETE with an empty problem list; the synthetic phase and the real-size phase COMPLETE in every stage; gates 1 and 2 passed on 280 of 280 registered checkpoints; the two identity links of ADR-0029 section 4 (each cell's `train.json` against P10-S1's committed training manifest; the draws' manifests against P10-S1's frozen data manifests) passed; the adapter identity gate passed; gate 3 not run; caps not provisional; workers ran with one thread, one interop thread and deterministic algorithms. Peak resident memory per worker: A1 663 MiB, A2 727 MiB, A2 training 347 MiB. The machine was shared with the implementation of other studies during this rehearsal; nothing in P10-I-R registers a time.

**Checks on the code.** Independent implementation audit and two re-audits by the `arbor-auditor` subagent (Opus 5.5): `docs/reviews/p10ir-implementation-audit-2026-11-17/`. The fixes of the second re-audit (commit `ef5596b`) were NOT audited again; the counting rehearsal exercised them. Local checks on `ef5596b` (macOS arm64): `ruff` clean, `mypy src/arborlm` clean, `pytest` 3,417 passed, 2 failed, 7 skipped, the E0 smoke recorded. Both failures are outside this study and pass when run alone: `tests/test_run_records.py::test_watchdog_kills_timed_out_child_and_saves_logs` (timing-sensitive; the machine was loaded) and `tests/test_p8_sim.py::test_p7b_reproduction_gate` (it skips when the working tree has no `experiments` folder and the lead had created one for scratch files; with the folder pointing at the main checkout's data it runs and passes). The full suite was not run again after that. The study's own 224 tests passed on `ef5596b`.

**The seal.** No sealed recall value of P10-S1's records has been displayed to the lead, the implementer or the auditors. Disclosures: the third specification reviewer loaded two `eval.json` files in a script that printed key paths only (ADR-0029 section 17.3, R3-A10); the rehearsals' gates 1 and 2 opened the registered checkpoints and the non-sealed counts of their `eval.json` records, and recomputed nothing sealed. The freeze command recorded the attestation `lead,implementer,auditor` from flags; code cannot verify it.

**Frozen inputs.** As ADR-0029 section 13 lists them; the ADR text is not among them. Nothing is written or committed in this working tree between a Decision 2 and the end of that stage group's report.
