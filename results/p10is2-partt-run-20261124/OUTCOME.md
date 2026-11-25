# P10-I-S2 Part T — outcome record of the registered run (ended 2026-11-24 15:22 local)

Written by the lead (Claude Fable 5.2). `Astra review: NOT_PERFORMED`. Claude review is not Astra review. **This is a registered negative and inconclusive outcome. It is not a success claim.** Every line below carries the study's oracle line: oracle-assisted (word-level addresses supplied by rule); lexical translation of short closed-vocabulary sentences, two capabilities of one kind; frozen English student; teacher-only training material verified by measured-precision filter; not autonomous learned memory.

## Registered labels (as the frozen code wrote them; `records/report.txt`, SHA-256 c649e830154a8ad2c11a9381e69ba15303f1468e8383e1c7ccc9adbfa228a132)

All with 3 replicates, U = 8,000, **NOT CONVERGED AT U**.

| Line | Label |
|---|---|
| MILESTONE (sequential acquisition with retention) | **NOT ESTABLISHED** — a lookup baseline does as well: E-table |
| AGAINST-LOOKUP | LOOKUP SUFFICES (best baseline by frequency: E-table, in all 12 cell/task readings; smallest margin over the rule +0.0297) |
| AGAINST-DENSE (M-append against D-append) | acquisition: DENSE AHEAD; retention: NOT EVALUABLE |
| AGAINST-DENSE (M-seq against D-seq) | acquisition: DENSE AHEAD; retention: MIXED |
| ACQUISITION | ACQUISITION-INCONCLUSIVE |
| RETENTION | RETENTION-INCONCLUSIVE: NOT CHALLENGED — SECOND NOT ACQUIRED |
| GENERAL-QUALITY | PRESERVED (the keyword router stayed silent) |
| MODIFICATION (M-ii, descriptive) | INTERMEDIATE |

## The numbers (reproduced by audit 20 from the per-item records)

| cell | G_first (M1) | ACQ1 | G_second (M-append) | ACQ2 | F | rho | delta G vs D-append | delta G / delta rho, M-seq vs D-seq |
|---|---|---|---|---|---|---|---|---|
| 0AB | 0.513 | True | 0.489 | False | 0.072 | 0.770 | -0.084 | -0.112 / +0.090 |
| 0BA | 0.501 | True | 0.513 | True | 0.063 | 0.800 | -0.127 | -0.105 / -0.060 |
| 1AB | 0.514 | True | 0.501 | True | 0.068 | 0.782 | -0.078 | -0.098 / +0.033 |
| 1BA | 0.504 | True | 0.506 | True | 0.056 | 0.824 | -0.124 | -0.118 / -0.152 |
| 2AB | 0.506 | True | 0.484 | False | 0.072 | 0.766 | -0.098 | -0.067 / -0.477 |
| 2BA | 0.503 | True | 0.499 | False | 0.086 | 0.726 | -0.133 | -0.145 / -0.122 |

The acquisition threshold is G >= 0.50 (non-strict in the ADR and in the code). Descriptive readings that enter no label: M-append scores 0.84 and 0.89 on seen training items and 0.31 and 0.33 on open items (A, B); M1 0.57 and 0.25–0.26; the untouched student 0.16 and 0.15 on open items; the teachers 0.69 and 0.74. General-quality loss increase: 0.000 in every cell and position (the router chose no route on every general window).

## What the labels do not say (audit 20, for the reader)

1. The cell-level acquisition results sit on the 0.50 threshold. The noise in each G is about ±0.012; G_first clears 0.50 by 0.001 to 0.014 and G_second lies between 0.016 below and 0.013 above. The pattern of which cells pass ACQ2 cannot be told from noise. No single edge cell changes ACQUISITION, AGAINST-LOOKUP or MILESTONE.
2. "NOT CHALLENGED" is the correct label by the rule's order, but the retention condition itself fails in all six cells (rho 0.73–0.82, F 0.056–0.086, none in the negative zone below 0.70), with the first-stage rows frozen. Part of each loss is already present at the append point.
3. "Retention MIXED" for M-seq against D-seq compares near-total losses on both sides (D-seq rho 0.01–0.06; M-seq -0.46 to 0.13). Neither retains.
4. Dense is ahead on the first acquisition too (D1 G_first 0.57–0.65 against M1 0.50–0.51) and was still improving at U = 8,000.
5. LOOKUP SUFFICES and GENERAL-QUALITY PRESERVED are not overstated.

## Recomputation (ADR-0025 section 8.6)

- Frozen code, registered stage `recompute` (`records/recomputation/attempt_001.json`): ok, tolerance 0, no differences; 11.79 charged hours.
- Auditor's own code (audit 21, arbor-auditor, Claude Opus 5.5; own greedy loop, own chrF, own routing of snapshots to items; the only frozen module imported is `studies.p10s2.model` for the student's forward pass and weight loader): **RECOMPUTATION AGREES**. 101 tasks, 56,976 worker-seconds, CPU. 468 of 468 item records, 592 of 592 registry keys, 38 of 38 combined records and 304 combined means compared; 219,525 greedy sequences identical; 241,350 item scores, largest difference 4.4e-16; 0 differences. Comparison record SHA-256 in `audit/`.
- **Precision ruling (lead, for the human lead's review).** Computed in float64, the auditor's per-window general-quality NLL differs from the stored float32 values by up to 4.5e-5 on all 17,280 NLL values (base and arm for each of 8,640 windows), and the six M-ii modification values by up to 1.1e-5; computed in float32 from the same logits they match bit for bit. The verdict is read in the stored precision. Section 8.6's 1e-6 tolerance is written for item scores and greedy sequences, both of which agree; the float64 differences are rounding over the vocabulary and change no reading (general quality is 0.000 either way; modification 0.60–0.67 against a 0.10 floor).
- Audit 20 (same auditor role, own standard-library script from the per-item records): OUTCOME REPRODUCED, every headline label and every per-cell number.

## Run identity and cost

- Run directory `experiments/P10IS2-T-registered-20261121` (local, git-ignored). `gates` and 50 of 54 training cells ran under the first freeze `c25d4f0b1d0ff5f529072cc7983c835a0267e2fb` (Decision 2 `results/p10is2-partt-freeze-20261122/`); the four remaining M-ii cells and all later stages ran under the second freeze `e7632df05f35fc727d827eb57a750437d4f9ab0a` (Decision 2 `results/p10is2-partt-freeze-20261123/`, ruling 51). The train stage record names only the second freeze.
- Charged hours: gates 0.40; train 99.02 (cap 125.8); evaluate 11.47 (21.77); controls 0.00; combined 4.20 (6.0); recompute 11.79 (22.66); analysis and report 0.00. Run ledger 126.89 h; with the 24.45 h charged before the freeze and the second targeted rehearsal (1.04 h), 152.38 h against the 204.25 h plan total and the 205 h bound. The auditor's own-code recomputation (15.83 worker-hours against a projection of about 12) is outside the ledger, as in Part Q.
- Large records not committed (kept in the run directory): `item_records.json` SHA-256 54589c9fc0782b217d55e9b788a886c90a1c2ce35d2140fb32da8ed5246af938; `combined.json` SHA-256 8292d2156da9d768f0d713d240a30fb1f069cc3d3fc509278d0c81cc1843df9c; the snapshots.

## Disclosures

All eleven disclosures of the first Decision 2 and all ten of the second stand. In addition and in summary:

1. **Two freezes.** Ruling 50 (six other-study freeze records taken off the branch for the run; restored before merging) and ruling 51 (caps amended on cost, bound 95.68 → 151 → 205 h, M-ii one worker at a time, charged-time cap check, memory admission, a targeted rehearsal in place of a repeated counting rehearsal) with its listed departures from ADR-0025 sections 7.1, 9 and 10. A registered stage ran above its cap under the first freeze (95.87 h against 75.68 h).
2. **Mixed training conditions.** 50 cells trained up to three at a time; three M-ii cells trained under heavy memory pressure to updates 1,500, 500 and 3,000, were killed at the cap and resumed alone from their checkpoints; one M-ii cell started alone. MPS training is not bit-reproducible in any case; no registered quantity is a time.
3. **The failed targeted-rehearsal attempt was charged to the plan,** which effectively renewed the 3.0 h targeted allowance.
4. **The lead's driver omitted the frozen descriptive `cost` command.** It was run after the report stage, at 15:35 on 2026-11-24, with the frozen code and the registered preconditions; it wrote `cost.json` and `cost.txt`, which enter no label. `report.txt` therefore lacks the counted multiply-adds that section 8.3 says are always printed with AGAINST-DENSE; they are in `records/cost.txt` (per update: D1 and D-seq 2.329e11, D-append 2.37e11, M1 and M-seq 2.119e11, M-append 2.12e11, M-ii 4.24e11). The timing benchmark was not measured. The router's false-trigger counts are not printed. **The cost record has defects of its own (audit 21), none entering a label:** "peak resident 0.0 bytes" for every arm but M-ii is an artifact (the cost code reads the second invocation's manifest, where 50 skipped cells record 0; M-ii's figure is a median over four measured cells and two zeros); "teacher inference 0.0 s per accepted item" is wrong (generation was reused from Part Q attempt 2, whose ledger entry the code does not read); the M-ii median training time (3,557 s) is a resumed cell that ran 7,500 updates, and every arm's median mixes in the contended first invocation; the backward multiply-adds of the store arms count only the blocks above the read layer (a reading section 8.5 does not state; it makes the memory arms' count about 15% lower); the stored-size line prints "G not evaluated" although G is defined; FEWER VALUE ROWS ACTIVE is not printed. The multiply-adds and footprint figures themselves reproduce by hand.
5. **Order of reporting.** Section 8.6 says no result is reported before both recomputations. The lead gave the registered labels to the human lead in chat at about 15:25 on 2026-11-24, after the frozen-code recomputation and before the auditor's own-code recomputation (which ended at 21:13 and agrees). Nothing was published or merged in between.
6. **Machine.** Colima ran from about 12:25 on 2026-11-22 to 12:40 on 2026-11-23 and again from 20:02 on 2026-11-23 through the end of the run, against the statements in both Decision 2 records that it was stopped; the ArborML Lab session's builds and the human lead's own work ran during the stages after `train`. These affect charged time only.
7. **Seal.** No sealed value was read before the report stage completed; the lead declined a proposal to score the 50 finished cells early. The auditor read the sealed records from 15:25 on 2026-11-24.
8. Audit 20's defects D1 and D2 (the frozen recomputation's record does not prove how many item records and combined means it compared) are closed from the auditor's side by audit 21's own counts; D4 (the train manifest names one freeze) is stated above.

## What this outcome is evidence of

Component evidence only. On a frozen small English student, with addresses supplied by rule, an appended key-value store trained for 8,000 updates behaves like a word table: a plain learned lookup table (E-table) matches or beats it in every reading, a dense LoRA adapter of equal size acquires more at matched updates, and neither capability's acquisition is clear of the threshold. It is not a test of capability parity, of learned addressing, or of a pretrained dense backbone with an expandable memory against a larger dense network; it supports no claim about those.

## Acceptance

See `ACCEPTANCE.md`.
