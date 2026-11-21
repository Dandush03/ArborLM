# P10-I-R outcome record (ADR-0029, sections 18–20)

**Status: COMPLETE. Stage groups A1 and A2 are recorded as registered, independently recomputed, and accepted by the lead under the human lead's delegation.** Nothing here is a success claim. This study is a diagnosis; it is neither a positive nor a negative result for ArborLM. `Astra review: NOT_PERFORMED`. Claude review is not Astra review.

Every label carries: ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK. A1's labels also carry REGISTERED RE-ANALYSIS OF OBSERVED CELLS (the accuracies of these checkpoints were known from P10-S1 before the study was designed); A2's carry FRESH CHECKPOINTS.

## 1. The run

| Item | Value |
|---|---|
| Freeze commit | `c712a905b01da3f12e2f884f8eaf44933a1756db`; Decision 2 for A1 at `3f54642`, for A2 at `755594b` (`results/p10ir-freeze-2026-11-18/`), both taken by the lead under the delegation of 2026-11-18 |
| Run directory | `experiments/P10IR-registered-20261118` (not in git) |
| A1 (reads of P10-S1's checkpoints) | gates COMPLETE; 70 tasks, 280 checkpoints, 0 item errors, 4,003.4 s charged (cap 6 h); analysis and report COMPLETE; 2026-11-18 04:35–05:42 UTC |
| A2 (20 fresh cells, then the same reads) | gates COMPLETE (43.3 s); training COMPLETE, 20 tasks, 4,871.5 s; reads COMPLETE, 20 tasks, 2,483.6 s; confirm COMPLETE; 0 item errors; 2.06 h charged (cap 3 h); 08:42–10:46 UTC |
| Charged | Registered stages 11,405.8 s (3.17 h): A1 1.113 h of its 6.0 h cap, A2 2.055 h of its 3.0 h cap. With the counting rehearsal (0.386 h of 1.0) the study charged 3.55 h of its 10 h total (3.92 h if the measuring rehearsal is counted). Bridge training took 1.35 h against a projection of 0.87 h. The machine was shared with other studies' work throughout; nothing in this study registers a time |

## 2. Registered labels (as the frozen code computed them)

| | A1: P10-S1's checkpoints | A2: fresh checkpoints |
|---|---|---|
| R-DIAGNOSIS | EVALUABLE | EVALUABLE |
| Tree component, at U_P and at the run length, at 8K/4K and 32K/16K | EXACT SEARCH HARMS | EXACT SEARCH HARMS |
| Index component, same | INDEX APPROACHES FLAT ONLY ABOVE 512 | INDEX APPROACHES FLAT ONLY ABOVE 512 |
| Recommended action | none | none |

R-CONFIRM-TREE: CONFIRMED. R-CONFIRM-INDEX: CONFIRMED. (`confirm/REPORT_CONFIRM.md`; A1's analysis record was not rewritten.)

Loaded cells (printed only, A1): 32K/4K at the run length EXACT SEARCH HARMS, at U_P NOT IDENTIFIED; index INDEX APPROACHES FLAT ONLY ABOVE 512. 8K/1K: tree EXACT SEARCH HARMS at the run length, NOT IDENTIFIED at U_P; index INDEX DOES NOT APPROACH FLAT.

## 3. The numbers behind the labels (A1, 32K facts / 16K slots, run length, means over five replicates)

| Read of the trained tree | a_use | information i (bits) |
|---|---|---|
| Flat memory, exhaustive (F0, the reference) | 0.992 | 4.888 |
| Tree as trained: 2 branches, priors on (T0) | 0.697 | 2.615 |
| Priors removed from the weights only (T1w) | 0.633 | 2.235 |
| Priors removed (T1) | 0.529 | 1.671 |
| All candidates, priors on (T3) | 0.408 | 1.092 |
| All candidates, priors off (T2) | 0.033 | 0.000 |

Visit sweep, priors on: v = 1, 2, 4, 8 gives i = 0.837, 2.615, 1.578, 1.182. Candidate recall of T0 against exact search over all keys: CR8 = 0.006.

Index over the flat memory's keys (64 keys per list), by budget of keys scored:

| Budget | a_use | CR8 |
|---|---|---|
| 128 | 0.422 | 0.396 |
| 256 | 0.582 | 0.532 |
| 512 | 0.766 | 0.686 |
| 1,024 | 0.912 | 0.835 |
| 2,048 | 0.976 | 0.944 |

Median c* = 2,048 keys (one eighth of the store) at 32K/16K; at 8K/4K, 2,048 at U_P and 1,024 at the run length.

## 4. Independent recomputation of A1

By the `arbor-auditor` subagent (Opus 5.5), with its own code; report and scripts in `audit_a1/`. The lead (Fable 5.2) designed and ran the study and wrote this record.

- Integrity: all stages COMPLETE and clean; gate 1 confirmed by the auditor's own hashing for 280 of 280 checkpoints and 70 of 70 `train.json` files; every gate passed and none was skipped; no replicate was made NOT EVALUABLE; P10-S1's recorded tree recall at U_P equals the recomputed CR8 of T0 exactly.
- Labels: 15,744 values compared with `analysis.json`, 0 differences.
- Measurements from the checkpoint tensors (32K/16K, two draws, both checkpoints, float64): 624 comparisons, 10 differences, all at float precision, none changing a label.
- Rulings 1 to 11 (ADR-0029 sections 19 and 20) changed no label against the ADR's literal text: none of the cases they cover occurred.
- No defect of the frozen code changed a number or a label.

## 4a. Independent recomputation of A2, and what CONFIRMED means

By the `arbor-auditor` subagent (Opus 5.5); report with its scripts in `audit_a2/AUDIT_P10IR_A2.md`.

- Integrity: all four A2 stages COMPLETE with 0 item errors; plan and config hashes match the freeze; the 20 bridge cells use the registry's seeds (data 290001–296999, initialization 330601–330605) and P10-S1's learning rate, U_P, run lengths and snapshot schedule; 185 snapshot hashes match; the adapter identity snapshots equal P10-S1's; gates 1, 2, 4, 5 and 6 passed, none skipped (gate 3 does not apply to A2); A1's analysis record is unchanged.
- Labels: 4,261 comparisons with `confirm/confirm.json`, 0 differences. Ruling 1 never came into play.
- Measurements from the bridge checkpoint tensors (32K/16K, two draws, both checkpoints): 624 comparisons, 26 differences, all from floating-point near-ties (one count in 32,768 on four reads of one draw); no label affected.
- A1 against A2, mean a_use (A1 / A2):

| Read | 8K/4K at U_P | 8K/4K run length | 32K/16K at U_P | 32K/16K run length |
|---|---|---|---|---|
| F0 | 0.948 / 0.949 | 0.996 / 0.996 | 0.916 / 0.917 | 0.992 / 0.991 |
| T0 | 0.469 / 0.493 | 0.769 / 0.773 | 0.401 / 0.411 | 0.697 / 0.703 |
| T1 | 0.340 / 0.353 | 0.515 / 0.521 | 0.332 / 0.341 | 0.529 / 0.536 |
| T1w | 0.417 / 0.436 | 0.681 / 0.687 | 0.371 / 0.381 | 0.633 / 0.640 |
| T3 | 0.384 / 0.402 | 0.589 / 0.598 | 0.293 / 0.298 | 0.408 / 0.409 |
| T2 | 0.064 / 0.064 | 0.062 / 0.062 | 0.039 / 0.039 | 0.033 / 0.034 |
| CR8 of T0 | 0.072 / 0.073 | 0.063 / 0.062 | 0.016 / 0.016 | 0.0063 / 0.0063 |
| c* (keys) | 2,048 / 2,048 | 1,024 / 1,024 | 2,048 / 2,048 | 2,048 / 2,048 |

  Every difference is within 0.024 and about one standard error; the visit sweep peaks at v = 2 in both; the index curves agree to 0.01. Data draws and initialization seeds both changed, so A2 cannot separate the two sources of variation.

**What CONFIRMED licenses.** The A1 labels reproduce by row name on fresh draws and fresh initialization: exact search over the tree's own keys harms; neither removing the prior nor removing the hard candidate restriction closes most of the gap; the post-hoc index needs more than 512 candidates.

**What it does not license, with three corrections to the registered report** (`confirm/REPORT_CONFIRM.md` and `confirm.json` are kept as the frozen code wrote them):

1. The report prints "A statement that the tree's gap is caused by a named factor at read time … Allowed here: True". **That line does not apply to this outcome.** The code behind it checks only for CONFIRMED. ADR-0029 section 10 makes CONFIRMED necessary for such a statement, not sufficient, and the confirmed row, "EXACT SEARCH HARMS — NOT SEPARABLE AT READ TIME", names no factor and recommends nothing. No statement that the gap is caused by a named read-time factor may be made from this study.
2. Ruling 4 (ADR-0029 section 19) gave as the reason for A2's plateau check being NOT CHECKED that fresh cells have "no recorded snapshot series". That reason is wrong: every bridge cell stores the half-run snapshots; they were not evaluated. The check stays NOT CHECKED for A2 as ruled and as run; the reason is corrected here.
3. A1's run-length labels carry TREE STILL LEARNING in 5 of 5 replicates at both primary cells, and A2's plateau check was not made. The confirmed run-length labels are therefore labels of a tree that had not plateaued. Nothing here says the labels would hold at a plateau.

Also: `a2/` and `A2/` are one directory on this case-insensitive file system.

## 5. What the result does and does not show (the auditor's judgement, adopted)

- **Wider search does not help at read time.** v = 2, the trained setting, is best; v = 1 loses 1.8 bits; v = 4 and 8 lose 1.0 and 1.4 bits with priors on and collapse with priors off. This says nothing about training with more branches visited.
- **The prior carries weight in the trained read.** Removing it loses 0.94 bits, about 0.38 from the weighting and 0.56 from the selection. This does not show that the prior causes the gap to the flat memory.
- **Exact search over the tree's keys selects slots that read near chance** (T2 a_use 0.033). CR8 of 0.006 is below what two random branches would give (0.031); the slots T0 reads have cosine 0.47 to the query against 0.76 for the exact top 8. This does **not** show why the tree is behind or that its content is poor: CR8 does not measure what the router misses.
- **The post-hoc index of the flat keys loses recall.** Its quality tracks the recovered attention mass almost one to one; at 512 candidates it finds 0.69 of the exact top 8 and needs about N/8 candidates at 32K/16K. This says nothing about an index that is trained.
- **Summary: no read-time cause is identified.** No read-time change tested closes the tree's gap, and none of this supports a statement about causes that act during training. That needs a new training study (Stage B), which does not exist and is not authorized.

## 6. Where the registered report reads differently from the records

`REPORT.md` and `confirm/REPORT_CONFIRM.md` are kept as the frozen code wrote them. Found by the recomputation of A1:

1. The R-DIAGNOSIS summary omits a tag that applies: **TREE STILL LEARNING** holds in 5 of 5 replicates at the run length at both primary cells. Part of the tree's gap may be unfinished training; this study cannot say how much.
2. The row's full wording, "EXACT SEARCH HARMS — NOT SEPARABLE AT READ TIME", is defined in the code and never printed.
3. "near 1: not testable" is printed for the candidate-restriction check even where the share is 0.064, that is, where the check was testable.
4. The tree's STILL LEARNING tag is also attached to the index label, although the flat memory plateaued in 5 of 5. This reads less favourably than the records.
5. The report's own reading "study-level NOT EVALUABLE applies per component" does not match ADR section 9 item 1 or the code, which void R-DIAGNOSIS as a whole. It had no effect here.

## 7. Acceptance

**A1.** The lead accepts the A1 outcome as registered, unchanged, with the findings of sections 5 and 6 beside it, under the human lead's delegation of 2026-11-18 (`docs/reviews/p10-i-direction-2026-11-17/DELEGATION_2026-11-18.md`: "once its done can you accept the results as they come and continue with the next simulations until you conclude P10-I-*"; "and you have my permission to auto approve everything until you complete P10-I"). This is an acceptance by the lead under that delegation, not the human lead's own. It is the acceptance of a diagnosis with no recommended action; it is not a success claim.

**A2.** The lead accepts the A2 outcome and R-CONFIRM as registered, unchanged, under the same delegation, with the limits of section 4a beside them.

## 8. What this study cannot establish

That a learned memory works without an oracle; anything about a task a dictionary cannot solve; any cause acting during training; that a differently trained tree, router or index would or would not close the gap; anything about speed, storage or cost. The registered TREE_BEHIND of P10-S1 stands unchanged.

## 9. For the human lead

1. Rulings 1 to 11 were made by the lead before any registered read and are put to the human lead for confirmation; none changed a label.
2. Decisions 2 for A1 and A2 were taken by the lead under the delegation.
3. The next-action table of the routing note is not triggered: the study recommends no action. Whether a Stage B training study follows is the human lead's decision after P10-I.
