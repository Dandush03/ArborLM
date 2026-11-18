# P10-I-R outcome record (ADR-0029, sections 18–20)

**Status: stage group A1 is recorded as registered, independently recomputed, and accepted by the lead under the human lead's delegation. Stage group A2 is recorded as registered; its independent recomputation is in progress and its acceptance waits for it.** Nothing here is a success claim. This study is a diagnosis; it is neither a positive nor a negative result for ArborLM. `Astra review: NOT_PERFORMED`. Claude review is not Astra review.

Every label carries: ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK. A1's labels also carry REGISTERED RE-ANALYSIS OF OBSERVED CELLS (the accuracies of these checkpoints were known from P10-S1 before the study was designed); A2's carry FRESH CHECKPOINTS.

## 1. The run

| Item | Value |
|---|---|
| Freeze commit | `c712a905b01da3f12e2f884f8eaf44933a1756db`; Decision 2 for A1 at `3f54642`, for A2 at `755594b` (`results/p10ir-freeze-2026-11-18/`), both taken by the lead under the delegation of 2026-11-18 |
| Run directory | `experiments/P10IR-registered-20261118` (not in git) |
| A1 (reads of P10-S1's checkpoints) | gates COMPLETE; 70 tasks, 280 checkpoints, 0 item errors, 4,003.4 s charged (cap 6 h); analysis and report COMPLETE; 2026-11-18 04:35–05:42 UTC |
| A2 (20 fresh cells, then the same reads) | gates COMPLETE (43.3 s); training COMPLETE, 20 tasks, 4,871.5 s; reads COMPLETE, 20 tasks, 2,483.6 s; confirm COMPLETE; 0 item errors; 2.06 h charged (cap 3 h); 08:42–10:46 UTC |
| Charged, registered stages | 11,405.8 s (3.17 h); total cap 10 h. The machine was shared with other studies' work throughout; nothing in this study registers a time |

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

**A2.** Recorded as registered. Its acceptance follows its independent recomputation, which is added to this folder when it returns.

## 8. What this study cannot establish

That a learned memory works without an oracle; anything about a task a dictionary cannot solve; any cause acting during training; that a differently trained tree, router or index would or would not close the gap; anything about speed, storage or cost. The registered TREE_BEHIND of P10-S1 stands unchanged.

## 9. For the human lead

1. Rulings 1 to 11 were made by the lead before any registered read and are put to the human lead for confirmation; none changed a label.
2. Decisions 2 for A1 and A2 were taken by the lead under the delegation.
3. The next-action table of the routing note is not triggered: the study recommends no action. Whether a Stage B training study follows is the human lead's decision after P10-I.
