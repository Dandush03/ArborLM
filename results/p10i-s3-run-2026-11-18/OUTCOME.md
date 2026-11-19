# P10-I-S3 (ADR-0026, longer training) — outcome record (2026-11-18 UTC)

Written by the lead (Claude Fable 5.2). The registered labels below are as the frozen code wrote them and as the independent recomputation reproduced them. They are accepted as registered by the lead under the human lead's delegation of 2026-11-18 (`DELEGATION_2026-11-18.md`, sections 1 and 7); this is not the human lead's own acceptance and not a success claim. ArborLM is unproven research. `Astra review: NOT_PERFORMED`. Claude review is not Astra review.

## 1. Disclosed first

1. **Fixed duration against reviewer advice.** The study trains every arm for a fixed 16,384 updates. The reviewer advised a larger corpus first; the fixed duration was taken at approval under the delegation. The calibration (rehearsal R1) found every arm × regime NOT CONVERGED at 16,384, and the registered FRESH run confirms it for all three arms (deltas: D-ADAPT +0.0172, M-FLAT +0.0208, M-TREE +0.0181, against ε = 0.001).
2. **M-TREE's FRESH rate at 16,384 updates (0.3) is at the edge of the extended grid.** The tree's line-2 label is INCONCLUSIVE for that reason.
3. **Route A to ADR-0027 is closed** by the open-choice-13 ruling: D-ADAPT is NOT CONVERGED.
4. The Decision 2 for this run was taken by the lead under the delegation. The machine was shared with P10-I-S1's calibration and other work during the run; no load average was recorded by any stage. The study registers no timing reading; results are deterministic and the bitwise identities (disabled = BASE, replay = enabled) hold in every record.

## 2. Registered labels (FRESH regime; ADR-0026 section 6)

| Line | Label |
|---|---|
| 1, DEPENDENCE | **DEPENDENT** (M-TREE NOT CONVERGED) [RATE-AT-EDGE] |
| 2, COMPETITIVENESS[TREE] | **INCONCLUSIVE (MEMORY RATE AT EDGE)**; base label NOT COMPETITIVE (MEMORY STILL IMPROVING) |
| 2, COMPETITIVENESS[FLAT] (separate sub-label) | **MEMORY AHEAD** (DENSE STILL IMPROVING) |

"Registered positive: line 1 True, line 2 False" is the ADR's term (section 6.5). It licenses only that A1's label qualifies before the open-choice-13 ruling, which then closes it. Nothing here qualifies for ADR-0027.

Regime labels (never a line's label): REP line 1 and line 2[TREE] NOT EVALUABLE, line 2[FLAT] NOT COMPETITIVE; REP-U line 1 and line 2[TREE] NOT EVALUABLE (see 4.2).

## 3. What the measurements say, and what they do not

- **Line 1.** On fresh data the tree memory lowers the loss (mean C +0.1287 over 27 cells, 9 parents) and the gain depends on the stored values: the smallest per-cell ratios are P_used/C = 1.70 and X_mean/C = 0.98 against thresholds of 0.5. The label is robust to cell spread.
- **Line 1 passes D2 largely through harm.** Reassigning values leaves the model WORSE than the frozen backbone in 27 of 27 FRESH cells (mean B − H_used = −0.150, larger in size than the gain); the batch-mean read is worse than the backbone in 19 of 27 (mean B − H_mean = −0.0042). So the control shows that wrong values hurt, which is dependence, but not that the gain is retrieval of the right content in any stronger sense. The registered report omits these figures although section 3.4 requires them (correction 5.2).
- **Line 2, tree against the dense adapter.** Mean Q = −0.0008: level within resolution. The base label NOT COMPETITIVE turns on parents: 7 of 9 against 8 needed; the deciding parent is 0.00068 short with a standard error of about 0.0012 on a 3-cell mean. The label is within cell spread of COMPETITIVE; if it flipped, Route A would still be closed (D-ADAPT's delta is 17 × ε). The registered label stays INCONCLUSIVE and nothing more is claimed.
- **Line 2, flat memory against the dense adapter.** Mean Q +0.0127 against 0.005, 27 of 27 cells, smallest parent mean +0.0044. Robust by its thresholds, but both arms are still improving by more per measurement interval than the flat memory's lead (0.0208 and 0.0172 against 0.0127), so the ordering at convergence is not identified.
- **Routing (descriptive).** On fresh data the tree is behind the flat memory in training from 2,048 updates and the gap grows with duration (G_train +0.0135 at 16,384). The trend label is fragile at its first point: G_train at 512 is +0.004881, 0.00012 below the 0.005 threshold. Consistent with P10-I-R (the tree's deficit is not a read-time effect); not an explanation of it.
- **Not shown:** anything at convergence; anything beyond one corpus, byte-level text, nine correlated parents and one addition size; any efficiency reading. No p-value is computed.

## 4. Independent recomputation (arbor-auditor subagent, Claude Opus 5.5; `audit/RECOMPUTE.md`)

Verdict: **REPRODUCED WITH CORRECTIONS.** 921 quantities recomputed from the 621 training and 1,755 evaluation records with code importing nothing from the study: largest difference 0.0; no label differs. Completeness and identity checks pass (no missing, duplicate or error record; plan `2c02a026…`; rate table as frozen; all 1,755 checkpoint hashes match their training records; manifests COMPLETE, no resume). Charged 24,064 s = 6.68 h of the 10.18 h cap (gates 657 s, train 21,904 s, eval 1,503 s).

### 4.1 The integrity check
The joint-permutation tolerance 1e-06 is the ADR's (sections 3.4, 10). Of 324 joint reads 317 match exactly; seven deviate, all in REP or REP-U; two exceed the tolerance (REP c12 at 16,384, −1.80e-6; REP-U c21 at 512 at rate 0.03, +3.33e-6). All 108 FRESH joint reads deviate by exactly 0, so the registered labels do not rest on a near miss. Likely cause, inferred from the code and NOT confirmed by re-evaluation: an exact float32 score tie among the top candidates, broken by slot index, which the permutation changes. If so the check as specified is not exact under ties: a defect of the specification, not shown to be a defect of the tree read. It is recorded as open; no label is changed because of it.

### 4.2 REP-U
REP is NOT EVALUABLE by the ADR's own rule (the failing read is one the label uses). REP-U's failing read is a descriptive checkpoint of a per-duration run that no label reads; it counts because the implementation read "on any cell" as every checkpoint of every run, and no ruling records that reading. The registered regime label stays NOT EVALUABLE as the frozen code wrote it. Checked only where the labels read, REP-U would be line 1 DEPENDENT and line 2[TREE] NOT COMPETITIVE (MEMORY STILL IMPROVING). Regime labels are never a line's label, so no registered line depends on this.

## 5. Corrections to the registered report (`REPORT.md` is kept as written)

1. Rehearsal convergence tags that differ from the registered ones are not printed (section 5.2 requires both): M-TREE REP rehearsal NOT CONVERGED (δ 0.001234), registered CONVERGED (δ 0.000266); M-FLAT REP rehearsal NOT CONVERGED (δ 0.004522), registered CONVERGED (δ −0.001465).
2. B − H_used and B − H_mean with counts are not printed (section 3.4); the figures are in section 3 above.
3. Step-0 losses are not printed (section 6.2): mean enabled NLL M-TREE 2.3516840399, M-FLAT 2.3516838491, D-ADAPT 2.3516919788; mean B 2.3516840475.
4. The K1–K3 figures and margins behind line 2 are not printed; they are in `audit/RECOMPUTE.md` and summarized in section 3.
5. The REP routing lines and the REP and REP-U six-parent figures use M-TREE values from regimes that are NOT EVALUABLE; read them as descriptive figures of non-evaluable regimes.
6. Decision 2 cites SHA-256 `753a0c66…` for `rehearsal_public.json`. That was the file before the counting rehearsal added its entries; the file frozen on, and named in the freeze record, is `d902be55…` (copied here).

## 6. Run facts

- Freeze commit `2e985787c466c5ac66356635d4c68704d3730c55`; Decision 2 `results/p10i-s3-freeze-2026-11-18/DECISION_2.md` (commit `936c4fc`); run directory `experiments/P10IS3-registered-20261118` (git-ignored; public records copied here: `analysis.json`, `REPORT.md`, `ledger.json`, `manifests/`).
- Stages gates, train, eval, analysis, report: each COMPLETE at first launch, 2026-11-18 13:58–20:39 UTC. No pause, no resume, no item error.
- Rehearsals and the two refused freeze attempts: see Decision 2.
- Open, for the human lead: the lead's rulings taken for this study under the delegation (the fixed duration; open choice 13; the REP-U scope left as coded) await confirmation; none changed a registered label after observation.
- Text edits owed to ADR-0026 by a later amendment, not made here: section 6.1 names ValueError where the code raises RuntimeError; the joint-permutation check needs a tie rule; "on any cell" needs its scope stated. The seed registry needs the joint-permutation seeds added.
