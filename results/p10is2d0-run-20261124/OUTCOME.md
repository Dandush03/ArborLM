# P10-I-S2-D0 (ADR-0035): outcome note by the lead

Status: POST-HOC EXPLORATORY DIAGNOSTIC OF AN OBSERVED RUN. No registered label. Not a success claim.
Astra review: NOT_PERFORMED. Written by the lead (arbor-lead, Claude Fable 5.2); not human approval.
Human lead review: PENDING (the specification was approved by the lead under the human lead's delegation of the night of 2026-11-24; see docs/reviews/adr-0035-p10-i-s2-d0-2026-11-24/).

## What ran

- Counterfactual reads over Part T's frozen M-append snapshots, all six cells, both panels, oracle route, CPU, no training.
- 24 reproduction passes and 96 counted passes, computed once by commit e74cbf25. 7.714 worker-hours of the 8.0 cap.
- The driver crashed in report rendering after the last pass. Under LEAD_DECISION_1.md, commit ffd29d74 fixed one formatting loop and added a finalize-only command that wrote report.txt (SHA-256 f1975d386bfe4f2d80026bbcdbab75bb9990f4ea458afc408ed5812f5a4c9c96) from the existing records. The failed attempt is kept.
- Gates: reproduction largest deviation 0.0 on all 24 passes; identity gates pass (largest 3.8e-06); no-write check passes; Part T run directory unchanged (412 files).

## Independent recomputation (arbor-auditor, Claude Opus 5.5, own code)

RECOMPUTATION AGREES (audit/AUDIT_P10IS2D0_1.md, audit/AUDIT_P10IS2D0_2.md): 120,000 greedy sequences, 0 differ; item scores largest difference 4.4e-16; 702 derived readings largest difference 1.6e-15; read statistics largest difference 3.7e-8; both summary words and cut-off counts identical. The auditor's first comparison attempt failed on a defect in its own checker and is kept. In three cells the auditor filled four passes each from its own gate sequences where the input was bit-identical.

## Readings (first capability, final store; s units)

| cell | T (= registered F) | (i) slot displacement | (ii) softmax renormalisation | (iii) stage-2 values | interaction (order) |
|---|---|---|---|---|---|
| r0 AB | +0.07188 | +0.04591 | -0.01815 | +0.04412 | -0.00250 |
| r0 BA | +0.06291 | +0.04133 | -0.03154 | +0.05312 | -0.00174 |
| r1 AB | +0.06803 | +0.04635 | -0.01606 | +0.03774 | -0.00506 |
| r1 BA | +0.05552 | +0.04781 | -0.03995 | +0.04766 | -0.00963 |
| r2 AB | +0.07206 | +0.03823 | -0.01424 | +0.04807 | -0.00939 |
| r2 BA | +0.08640 | +0.04509 | -0.02855 | +0.06986 | +0.01439 |

- Summary wording as printed: MIXED (path order), MIXED (values-first order), final MIXED.
- Competition, (i)+(ii), reaches 2/3 of T in 0 of 6 cells in either order. Stage-2 values reach 2/3 of T in 4 cells (path order) and 3 cells (values-first); 5 were needed. r2 AB sits at 0.66707 against 2/3.
- Renormalisation is negative in all six cells: it offsets part of the slot displacement.
- Counterfactual retention arithmetic (not RET): DOES NOT HOLD in all six cells under per-stage top-8 (c: F_cf 0.19 to 0.37) and under the protected stage-1 read (g(1): F_cf 0.043 to 0.057, rho_cf 0.81 to 0.86). Read c costs the second capability 0.103 to 0.139.
- Second capability: stage 2 read alone scores 0.075 to 0.131 below the registered read; on these stores the second capability leans on stage-1 rows.

## What this does and does not support (lead's reading)

- The hypothesis that cross-stage top-k competition and softmax renormalisation explain most of Part T's retention loss is not supported on these stores. Competition accounts for a minority of the loss (net -3% to 37% of T by cell, values-first order).
- A read-time bank isolation would not have rescued retention on these snapshots: per-stage top-8 is worse, and a protected stage-1 read recovers only part of the loss.
- This is a counterfactual read on stores trained under the global read. It does not show what a store trained under an isolated read would do. P11-S1 (ADR-0034 draft) already uses per-block reads with learned addresses; D0 gives no reason to change that and no evidence for it.
- It does not change any Part T label. It is oracle-addressed, on a frozen small student, two capabilities of one kind.

## Disclosures

See RECORD.md (chmod +x on the launch script; one pkill by pattern on the implementer's own test wrapper; ADR-0035 draft 3 had no third review; no implementation audit before launch; the report-step crash; deterministic algorithms ON; evaluate.py path correction). Further: the lead opened one statistics file to print key names, types and its scalar labelling values while diagnosing the crash (the auditor cannot verify that nothing else was read); ADR section 8.3 does not say whether a resume may run at a different commit (PENDING HUMAN LEAD REVIEW); second-capability shares are null in the implementer's record because T2 is negative; cost.json and run_complete.json differ by 0.36 s.
