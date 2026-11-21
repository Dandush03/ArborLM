# P10-I-S6 outcome record (ADR-0031): does the flat memory's lead over the dense adapter persist at convergence?

Status: registered run executed once, 2026-11-20 05:57 to 19:11 (local), at freeze `cedfbe2842e8eb8bcc99c4303f5191fe0b3861e1`; all five stages (gates, train, eval, analysis, report) exit 0. Labels independently recomputed (below). **Not accepted by the human lead yet. Astra review: NOT_PERFORMED.** Nothing here is a success claim.

Decision 2 (to run) was taken by the lead (Claude) under the human lead's delegation of 2026-11-19 (`docs/reviews/p10-i-s6-spec-reviews-2026-11-19/DELEGATION_DECISION_2.md`), not by him in person. Implementation rulings 1 to 22 (ADR-0031 addenda 1 and 2) still await his confirmation; he may overrule them before accepting this outcome.

## Registered label

**Line P: CONVERGENCE NOT REACHED (BOTH STILL IMPROVING)** (ADR-0031 section 12.3 row 12: "K* does not exist; neither converged at rung 4"). Reading rung R = 4, k_max = 4; dependence-qualified: False.

What ADR-0031 section 19 says this means: "Sixteen times the duration was not enough by the registered criterion. The trend line describes the lead over the trained range … The human lead may weigh that description." What it does not mean: "Nothing about the ordering at convergence, in either direction; no tag is PERSISTS, and none qualifies for anything PERSISTS would. Not a reason to extend this study".

Other registered readouts: D[FLAT] at R: DEPENDENT. R16: REPLICATED AT 16,384. OA: REPLICATED AT 16,384.

## Descriptive figures (never labels)

| rung | updates | rate M-FLAT | rate D-ADAPT | loss M-FLAT | loss D-ADAPT | mean Q (flat lead) | cells / parents with Q > 0 | class |
|---|---|---|---|---|---|---|---|---|
| 0 | 16,384 | 0.03 | 0.01 | 2.2122 | 2.2245 | 0.0124 | 26 of 27 / 9 of 9 | UNDECIDED |
| 1 | 32,768 | 0.1 | 0.01 | 2.1925 | 2.2056 | 0.0131 | 27 / 9 | UNDECIDED |
| 2 | 65,536 | 0.03 | 0.01 | 2.1742 | 2.1879 | 0.0137 | 27 / 9 | UNDECIDED |
| 3 | 131,072 | 0.1 | 0.01 | 2.1576 | 2.1695 | 0.0119 | 27 / 9 | UNDECIDED |
| 4 | 262,144 | 0.003 | 0.01 | 2.1454 | 2.1522 | 0.0068 | 24 / 8 | M-AHEAD |

Trend tag: LEAD SHRINKING (Δ = -0.0056 over 16,384 to 262,144 updates). It is descriptive, says nothing about the ordering at convergence and is not the label PERSISTS. At rung 4 the improvement per doubling is 0.0122 (M-FLAT) and 0.0173 (D-ADAPT), both larger than the lead (0.0068). The class M-AHEAD at rung 4 is not a label.

## Independent recomputation

By the auditor (arbor-auditor, Claude Opus 5.5 per the agent definition), 2026-11-20, own standard-library code written from ADR-0031 and its addenda, importing nothing from the study: `recomputation/`. Result: every label and every figure printed in `report.md` reproduced (121 of 121 checks at printed precision); 146 of 147 fields of `analysis.json` equal at full precision. All 189 training items and 837 evaluations present exactly once, none resumed, none rerun; integrity checks hold bitwise. Rate selection reproduced from the calibration records and used only the calibration pool, parents and panel.

## Disclosures

1. **Thin margins of the descriptive tag.** The lead is positive at rung 4 on exactly 8 of 9 parents, the minimum for the tag; one fewer would read LEAD LOST BY RUNG 4. Δ is 0.000581 beyond the -0.005 line; a Δ above it would read LEAD HELD AT EVERY RUNG. Neither changes the registered label.
2. **Rungs 0 to 3 are UNDECIDED** only through the Q† clause; M-AHEAD at rung 4 arises because the dense arm's best rung is 4.
3. **D[FLAT] = DEPENDENT passes through harm.** Reassigning used slots makes all 27 cells worse than BASE (mean B − H_used −0.2266). Reading the mean value row loses the gain (mean B − H_vmean −0.0030; 17 of 27 cells worse than BASE).
4. **M-FLAT calibration.** Its rate grid used both upward extensions the ADR allows; rungs 0 and 4 were decided by the 0.0005 tie rule in favour of a smaller rate than the minimiser (0.3); the rate path is not monotone (0.03, 0.1, 0.03, 0.1, 0.003), so adjacent rungs come from different runs. D-ADAPT chose 0.01 at every rung.
5. **R16 and OA at rung 0:** both arms NOT CONVERGED.
6. **Defect in `analysis.json` (no label effect):** `harm["0"].used_slots` holds the OA block's values, because the statistics key carries no OA marker and OA M-FLAT shares rate 0.03 with registered rung 0. COLLAPSED is read at R = 4, where no OA run exists. It would have mattered had R been 0.
7. **Report omissions against the ADR:** per-rung counts of cells and parents with Q > 0 (given in the table above from the recomputation), used slots per cell, rung-0 convergence states beside R16 and OA, per-parent δ and δrun, most section 12.5 descriptives. `analysis.json`: `calibration_states` is null while `calibration_vs_registered_states_that_differ` prints `{}` as if computed (the auditor computed it: no state differs); `delta_per_parent` holds the per-parent δrun; no code identity (the stage manifests carry it).
8. **Ledger.** Charged: gates 923.9 s + train 46,537.2 s + eval 175.4 s = 47,636.6 s (13.23 h), 59 % of the cap. The field `total_seconds` (80,428.6) in `ledger.json` is the cap (22.34 h), not a total. No stage paused. Rehearsals charged a separate ledger (31,232.6 s of 57,600 s).
9. **Machine sharing.** P10-I-S0's registered grid ran beside the training from its start; P10-I-S2 Part T's measuring rehearsal ran beside it from about 15:20 and through evaluation. No S6 label depends on wall time. The Part T rehearsal is not a quiet-machine stage (its config allows two workers on a shared machine); its measured rates are pessimistic for that reason.
10. **Rehearsal history.** The 62 `attempts` records all belong to the R1 calibration rehearsal (pauses on 2026-11-19 for P10-I-S1's quiet stage and after a terminal death on 2026-11-20); none names a registered item.
11. **Sealed access.** After all labels had matched, the auditor opened `rehearsal_sealed.json` (sha256 e85caefc…deda2, equal to the public record's) to check the rate selection, and listed the sealed folder's top level. The lead did not open it.
12. Synthetic-scale study on one frozen backbone; nothing about cost, efficiency, the tree memory, SSD or other corpora.

## Files

`report.md`, `analysis.json`, `ledger.json`: copies from the run directory (git-ignored `experiments/P10IS6-run-20261119`). `recomputation/`: the auditor's scripts, outputs and `RECOMPUTATION.md`.
