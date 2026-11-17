# P10-S0 — addressing qualification (ADR-0020 design revision 4)

ArborLM is unproven research. Astra review: NOT_PERFORMED. A Claude review is neither Astra validation nor a human approval. The human lead accepted the P9-II outcome as registered (docs/decisions/ADR-0019-robust-sparse-address-learning.md section 16: "yes I do, yes we can raise to 16 and I approve the package").

Number labels: every accuracy, count, class and label in this report is MEASURED on S0's own cells (or, where it says P9-II, copied from P9-II's committed records); per-draw bounds are ANALYTICAL (one-sided 95% Clopper-Pearson); no HYPOTHETICAL number appears; no cost figure is an efficiency claim or a speedup.

## Arm selection (section 3.4)

- The registered mapping's own result (section 3.2, on P9-II's committed records): **FOURTH ARM: NONE — P9-II CARRIED A0 (ALREADY IN S0)** (table row 3 of section 3.3; fourth arm by the mapping: None).
- The human lead's override (section 3.4, 2026-11-15) fixes the fourth arm as A5-D:

  > yes s0 should include the penalty and i approve s2 download

- Calibrated values used (P9-II's audited calibration record; equals the record: True): λ = 1.0, U_pre = 2,048, μ = 1.0 (k_0/N = 0.125 is not used: A4 is not in S0).
- Arms that can still be the candidate (section 3.5): A5-D, A1; excluded: A0 (P9-II failed draws at 4,096 already exceed two (6 of 8)); A2 (P9-II failed draws at 4,096 already exceed two (8 of 8)).

**FOURTH ARM: A5-D — ADDED BY THE HUMAN LEAD'S DECISION OF 2026-11-15; THE REGISTERED MAPPING GAVE NONE (P9-II CARRIED A0)**

*A0 is UNRELIABLE at 4,096 (4/16) and at chance at matched updates at 16,384; A5-D is the only label-free arm RELIABLE at both sizes; A5-D was not probed at 65,536 because the rule sent A0 to Stage 3.*

**"A5-D was added after P9-II's outcome was observed, knowing it was RELIABLE there (16/16 at 4,096; 8/8 at 16,384). For A5-D, S0 is a confirmatory replication on new draws, not an unbiased first test. Its CONSISTENT ACROSS STUDIES label and pooled count include the P9-II records it was chosen on and add no independent evidence; no pooled per-draw bound is printed for A5-D."**


## Outcome (section 8.7)

**Outcome (row 3): INCONCLUSIVE [one initialization seed per draw at 16,384]**
Cut 3 of section 10.4 applies: one initialization seed per draw at 16,384.
Cell type 2K/4K is NOT_EVALUATED: more than one draw has A6 below 0.90. Nothing is qualified or disqualified.


## Classes per arm and cell type

| arm | cell type | S0 class (S0's criteria) | class under P9-II's criteria | P9-II class | replication | consistency | pooled (P9-II's criteria) | ADDRESS STABLE | collapse |
|---|---|---|---|---|---|---|---|---|---|
| A0 (LABEL-FREE) | 2K/4K | NOT_EVALUATED (0/0 cells; 0/0 draws) | NOT_EVALUATED (0/0 cells; 0/0 draws) | UNRELIABLE | NOT COMPARABLE | NOT DEFINED (S0 NOT_EVALUATED) | NOT AVAILABLE (S0 NOT_EVALUATED) | no (nan) | COLLAPSE-FREE: 20 of 20 counted cells never had a collapse onset |
| A0 (LABEL-FREE) | 8K/16K | NOT_EVALUATED (0/0 cells; 0/0 draws) | NOT_EVALUATED (0/0 cells; 0/0 draws) | RELIABLE | NOT COMPARABLE | NOT DEFINED (S0 NOT_EVALUATED) | NOT AVAILABLE (S0 NOT_EVALUATED) | no (nan) | COLLAPSE-FREE: 10 of 10 counted cells never had a collapse onset |
| A0 (LABEL-FREE) | 8K/4K | NOT_EVALUATED (0/0 cells; 0/0 draws) | NOT_EVALUATED (0/0 cells; 0/0 draws) | — | NOT COMPARABLE | — | NOT AVAILABLE (S0's protocol at this cell type is not P9-II's) | no (nan) | COLLAPSE-FREE: 10 of 10 counted cells never had a collapse onset |
| A1 (ADDRESS-SUPERVISED IN TRAINING) | 2K/4K | NOT_EVALUATED (0/0 cells; 0/0 draws) | NOT_EVALUATED (0/0 cells; 0/0 draws) | RELIABLE | NOT COMPARABLE | NOT DEFINED (S0 NOT_EVALUATED) | NOT AVAILABLE (S0 NOT_EVALUATED) | no (nan) | COLLAPSE-FREE: 20 of 20 counted cells never had a collapse onset |
| A1 (ADDRESS-SUPERVISED IN TRAINING) | 8K/16K | NOT_EVALUATED (0/0 cells; 0/0 draws) | NOT_EVALUATED (0/0 cells; 0/0 draws) | UNRELIABLE | NOT COMPARABLE | NOT DEFINED (S0 NOT_EVALUATED) | NOT AVAILABLE (S0 NOT_EVALUATED) | no (nan) | COLLAPSE-FREE: 10 of 10 counted cells never had a collapse onset |
| A2 (ADDRESS-SUPERVISED IN TRAINING) | 2K/4K | NOT_EVALUATED (0/0 cells; 0/0 draws) | NOT_EVALUATED (0/0 cells; 0/0 draws) | FAILS | NOT COMPARABLE | NOT DEFINED (S0 NOT_EVALUATED) | NOT AVAILABLE (S0 NOT_EVALUATED) | no (nan) | COLLAPSE-FREE: 20 of 20 counted cells never had a collapse onset |
| A2 (ADDRESS-SUPERVISED IN TRAINING) | 8K/16K | NOT_EVALUATED (0/0 cells; 0/0 draws) | NOT_EVALUATED (0/0 cells; 0/0 draws) | — | NOT COMPARABLE | NOT DEFINED (S0 NOT_EVALUATED) | NOT AVAILABLE (S0 NOT_EVALUATED) | no (nan) | COLLAPSE-FREE: 7 of 10 counted cells never had a collapse onset |
| A5-D (LABEL-FREE) | 2K/4K | NOT_EVALUATED (0/0 cells; 0/0 draws) | NOT_EVALUATED (0/0 cells; 0/0 draws) | RELIABLE | NOT COMPARABLE | NOT DEFINED (S0 NOT_EVALUATED) | NOT AVAILABLE (S0 NOT_EVALUATED) | no (nan) | COLLAPSE-FREE: 20 of 20 counted cells never had a collapse onset |
| A5-D (LABEL-FREE) | 8K/16K | NOT_EVALUATED (0/0 cells; 0/0 draws) | NOT_EVALUATED (0/0 cells; 0/0 draws) | RELIABLE | NOT COMPARABLE | NOT DEFINED (S0 NOT_EVALUATED) | NOT AVAILABLE (S0 NOT_EVALUATED) | no (nan) | COLLAPSE-FREE: 10 of 10 counted cells never had a collapse onset |
| A5-D (LABEL-FREE) | 8K/4K | NOT_EVALUATED (0/0 cells; 0/0 draws) | NOT_EVALUATED (0/0 cells; 0/0 draws) | — | NOT COMPARABLE | — | NOT AVAILABLE (S0's protocol at this cell type is not P9-II's) | no (nan) | COLLAPSE-FREE: 10 of 10 counted cells never had a collapse onset |

Cut 3 of section 10.4 applies at 16,384: one initialization seed per draw at 16,384; the 10-cell class rule applies there.

UNRELIABLE and FAILS enter no rule; qualification, replication and OVERLOAD use RELIABLE against not RELIABLE only. P9-II's classes are those of its registered record (read through the arm-selection record).

- A1: P9-II NEGATIVE CONTROL at 4,096: not failed; at 16,384: not failed (P9-II's printed result, repeated).
- A2: P9-II NEGATIVE CONTROL at 4,096: not failed; at 16,384: not failed (P9-II's printed result, repeated).
- A0 at 2K/4K: i median 0.000 bits per fact (reported); ADDRESS STABLE non-finite cells counted as 0: 0
- A0 at 2K/4K: sustained success: 13 of 13 cells with a first success (descriptive)
- A0 at 8K/16K, readout at U: NOT_EVALUATED — ALSO AT MATCHED UPDATES (enters no rule).
- A0 at 8K/16K: i median 0.000 bits per fact (reported); ADDRESS STABLE non-finite cells counted as 0: 0
- A0 at 8K/4K, readout at U: NOT_EVALUATED — ALSO AT MATCHED UPDATES (enters no rule).
- A0 at 8K/4K: i median 0.000 bits per fact (reported); ADDRESS STABLE non-finite cells counted as 0: 0
- A1 at 2K/4K: ADDRESS RECALL median 0.621 
- A1 at 2K/4K: i median 0.000 bits per fact (reported); ADDRESS STABLE non-finite cells counted as 0: 0
- A1 at 2K/4K: sustained success: 14 of 14 cells with a first success (descriptive)
- A1 at 8K/16K, readout at U: NOT_EVALUATED — ALSO AT MATCHED UPDATES (enters no rule).
- A1 at 8K/16K: ADDRESS RECALL median 1.000 ADDRESS RECALL
- A1 at 8K/16K: i median 0.000 bits per fact (reported); ADDRESS STABLE non-finite cells counted as 0: 0
- A2 at 2K/4K: ADDRESS RECALL median 0.016 
- A2 at 2K/4K: i median 0.000 bits per fact (reported); ADDRESS STABLE non-finite cells counted as 0: 0
- A2 at 2K/4K: sustained success: 14 of 14 cells with a first success (descriptive)
- A2 at 8K/16K, readout at U: NOT_EVALUATED — MID-SCHEDULE (not a matched-update run) (enters no rule).
- A2 at 8K/16K: ADDRESS RECALL median 0.088 
- A2 at 8K/16K: i median 0.000 bits per fact (reported); ADDRESS STABLE non-finite cells counted as 0: 0
- A5-D at 2K/4K: i median 0.000 bits per fact (reported); ADDRESS STABLE non-finite cells counted as 0: 0
- A5-D at 2K/4K: sustained success: 14 of 14 cells with a first success (descriptive)
- A5-D at 8K/16K, readout at U: NOT_EVALUATED — ALSO AT MATCHED UPDATES (enters no rule).
- A5-D at 8K/16K: i median 0.000 bits per fact (reported); ADDRESS STABLE non-finite cells counted as 0: 0
- A5-D at 8K/4K, readout at U: NOT_EVALUATED — ALSO AT MATCHED UPDATES (enters no rule).
- A5-D at 8K/4K: i median 0.000 bits per fact (reported); ADDRESS STABLE non-finite cells counted as 0: 0

**FOURTH ARM: A5-D — ADDED BY THE HUMAN LEAD'S DECISION OF 2026-11-15; THE REGISTERED MAPPING GAVE NONE (P9-II CARRIED A0)**

*A0 is UNRELIABLE at 4,096 (4/16) and at chance at matched updates at 16,384; A5-D is the only label-free arm RELIABLE at both sizes; A5-D was not probed at 65,536 because the rule sent A0 to Stage 3.*

**"A5-D was added after P9-II's outcome was observed, knowing it was RELIABLE there (16/16 at 4,096; 8/8 at 16,384). For A5-D, S0 is a confirmatory replication on new draws, not an unbiased first test. Its CONSISTENT ACROSS STUDIES label and pooled count include the P9-II records it was chosen on and add no independent evidence; no pooled per-draw bound is printed for A5-D."**


## Paired comparisons with A0

d(X) over the 20 pairs of cells, success under S0's criteria (the readings H20-B, H20-C and H20-D use), with d under P9-II's criteria printed beside it (it enters no reading).

| arm | cell type | label (S0's criteria) | d | p (sign test) | d under P9-II's criteria | label (P9-II's criteria) |
|---|---|---|---|---|---|---|
| A1 | 2K/4K | NOT DISTINGUISHED FROM A0 | 0 | 1.000 | 0 | NOT DISTINGUISHED FROM A0 |
| A1 | 8K/16K | NOT DISTINGUISHED FROM A0 | 0 | 1.000 | 0 | NOT DISTINGUISHED FROM A0 |
| A2 | 2K/4K | NOT DISTINGUISHED FROM A0 | 0 | 1.000 | 0 | NOT DISTINGUISHED FROM A0 |
| A2 | 8K/16K | NOT DISTINGUISHED FROM A0 | 0 | 1.000 | 0 | NOT DISTINGUISHED FROM A0 |
| A5-D | 2K/4K | NOT DISTINGUISHED FROM A0 | 0 | 1.000 | 0 | NOT DISTINGUISHED FROM A0 |
| A5-D | 8K/16K | NOT DISTINGUISHED FROM A0 | 0 | 1.000 | 0 | NOT DISTINGUISHED FROM A0 |

d(A2 against A1) at 2K/4K (descriptive): 0 (p = 1.000).

d(A2 against A1) at 8K/16K (descriptive): 0 (p = 1.000).

H20-D note: A0 fails 0 of its cells at 8K/16K, fewer than four: IMPROVES ON A0 is unreachable and H20-D reads not supported, whatever A5-D does (the registered reading).

**FOURTH ARM: A5-D — ADDED BY THE HUMAN LEAD'S DECISION OF 2026-11-15; THE REGISTERED MAPPING GAVE NONE (P9-II CARRIED A0)**

*A0 is UNRELIABLE at 4,096 (4/16) and at chance at matched updates at 16,384; A5-D is the only label-free arm RELIABLE at both sizes; A5-D was not probed at 65,536 because the rule sent A0 to Stage 3.*

**"A5-D was added after P9-II's outcome was observed, knowing it was RELIABLE there (16/16 at 4,096; 8/8 at 16,384). For A5-D, S0 is a confirmatory replication on new draws, not an unbiased first test. Its CONSISTENT ACROSS STUDIES label and pooled count include the P9-II records it was chosen on and add no independent evidence; no pooled per-draw bound is printed for A5-D."**


## Qualification (section 8.5)

Preference order, fixed: A0, A5-D, A2, A1 (C4 = A5-D; the order was fixed in revision 3, before P9-II ran; the occupant of C4 was chosen after).

- A0: qualifies at no size
- A1: qualifies at no size
- A2: qualifies at no size
- A5-D: qualifies at no size

**FOURTH ARM: A5-D — ADDED BY THE HUMAN LEAD'S DECISION OF 2026-11-15; THE REGISTERED MAPPING GAVE NONE (P9-II CARRIED A0)**

*A0 is UNRELIABLE at 4,096 (4/16) and at chance at matched updates at 16,384; A5-D is the only label-free arm RELIABLE at both sizes; A5-D was not probed at 65,536 because the rule sent A0 to Stage 3.*

**"A5-D was added after P9-II's outcome was observed, knowing it was RELIABLE there (16/16 at 4,096; 8/8 at 16,384). For A5-D, S0 is a confirmatory replication on new draws, not an unbiased first test. Its CONSISTENT ACROSS STUDIES label and pooled count include the P9-II records it was chosen on and add no independent evidence; no pooled per-draw bound is printed for A5-D."**


## Annotations on the candidate (section 8.6)

- OVERLOAD: OVERLOAD NOT RUN — NO CANDIDATE
- WX block status: NOT RUN — NO CANDIDATE; RECORD-LENGTH-FREE VARIANT: NOT RUN — NO CANDIDATE
- 65,536 probe status: NOT RUN — NO CANDIDATE; —
- A failure of WX is not evidence that the record length is required; WX is never the qualified interface.


## Hypothesis readings (section 8.7)

| hypothesis | reading | notes |
|---|---|---|
| H20-A | not read | why: A0 NOT_EVALUATED or missing at a size and not UNRELIABLE or FAILS at the other |
| H20-B | not supported | arm: A1; paired: {'2K/4K': 'NOT DISTINGUISHED FROM A0', '8K/16K': 'NOT DISTINGUISHED FROM A0'} |
| H20-C | not supported | arm: A2; paired: {'2K/4K': 'NOT DISTINGUISHED FROM A0', '8K/16K': 'NOT DISTINGUISHED FROM A0'} |
| H20-D | not supported | a5d_provenance: {'f1_annotation': 'A0 is UNRELIABLE at 4,096 (4/16) and at chance at matched updates at 16,384; A5-D is the only label-free arm RELIABLE at both sizes; A5-D was not probed at 65,536 because the rule sent A0 to Stage 3.', 'fourth_arm_string': "FOURTH ARM: A5-D — ADDED BY THE HUMAN LEAD'S DECISION OF 2026-11-15; THE REGISTERED MAPPING GAVE NONE (P9-II CARRIED A0)", 'provenance_sentence': "A5-D was added after P9-II's outcome was observed, knowing it was RELIABLE there (16/16 at 4,096; 8/8 at 16,384). For A5-D, S0 is a confirmatory replication on new draws, not an unbiased first test. Its CONSISTENT ACROSS STUDIES label and pooled count include the P9-II records it was chosen on and add no independent evidence; no pooled per-draw bound is printed for A5-D."}; arm: A5-D; paired: {'2K/4K': 'NOT DISTINGUISHED FROM A0', '8K/16K': 'NOT DISTINGUISHED FROM A0'}; registered_note: A0 fails 0 of its cells at 8K/16K, fewer than four: IMPROVES ON A0 is unreachable and H20-D reads not supported, whatever A5-D does (the registered reading) |
| H20-L | not tested | label: RECORD-LENGTH-FREE VARIANT: NOT RUN — NO CANDIDATE |
| H20-O | not tested | descriptive_a5d_8k_4k_class: NOT_EVALUATED; label: OVERLOAD NOT RUN — NO CANDIDATE |
| H20-Q | not read |  |
| H20-R (A0, 2K/4K) | not read | label: NOT COMPARABLE |
| H20-R (A0, 8K/16K) | not read | label: NOT COMPARABLE |
| H20-R (A1, 2K/4K) | not read | label: NOT COMPARABLE |
| H20-R (A1, 8K/16K) | not read | label: NOT COMPARABLE |
| H20-R (A2, 2K/4K) | not read | label: NOT COMPARABLE |
| H20-R (A2, 8K/16K) | not read | label: NOT COMPARABLE |
| H20-R (A5-D, 2K/4K) | not read | a5d_provenance: {'f1_annotation': 'A0 is UNRELIABLE at 4,096 (4/16) and at chance at matched updates at 16,384; A5-D is the only label-free arm RELIABLE at both sizes; A5-D was not probed at 65,536 because the rule sent A0 to Stage 3.', 'fourth_arm_string': "FOURTH ARM: A5-D — ADDED BY THE HUMAN LEAD'S DECISION OF 2026-11-15; THE REGISTERED MAPPING GAVE NONE (P9-II CARRIED A0)", 'provenance_sentence': "A5-D was added after P9-II's outcome was observed, knowing it was RELIABLE there (16/16 at 4,096; 8/8 at 16,384). For A5-D, S0 is a confirmatory replication on new draws, not an unbiased first test. Its CONSISTENT ACROSS STUDIES label and pooled count include the P9-II records it was chosen on and add no independent evidence; no pooled per-draw bound is printed for A5-D."}; label: NOT COMPARABLE |
| H20-R (A5-D, 8K/16K) | not read | a5d_provenance: {'f1_annotation': 'A0 is UNRELIABLE at 4,096 (4/16) and at chance at matched updates at 16,384; A5-D is the only label-free arm RELIABLE at both sizes; A5-D was not probed at 65,536 because the rule sent A0 to Stage 3.', 'fourth_arm_string': "FOURTH ARM: A5-D — ADDED BY THE HUMAN LEAD'S DECISION OF 2026-11-15; THE REGISTERED MAPPING GAVE NONE (P9-II CARRIED A0)", 'provenance_sentence': "A5-D was added after P9-II's outcome was observed, knowing it was RELIABLE there (16/16 at 4,096; 8/8 at 16,384). For A5-D, S0 is a confirmatory replication on new draws, not an unbiased first test. Its CONSISTENT ACROSS STUDIES label and pooled count include the P9-II records it was chosen on and add no independent evidence; no pooled per-draw bound is printed for A5-D."}; label: NOT COMPARABLE |
| H20-S | not tested |  |

Every reading is about S0's draws. A hypothesis reading is not a success of the science.


## Oracle-query reference A6 per draw

| cell type | draw | A6 accuracy A | A6 accuracy B | evaluated |
|---|---|---|---|---|
| 2K/4K | 1 | 0.023 | 0.055 | False |
| 2K/4K | 10 | 0.039 | 0.047 | False |
| 2K/4K | 2 | 0.039 | 0.039 | False |
| 2K/4K | 3 | 0.016 | 0.047 | False |
| 2K/4K | 4 | 0.023 | 0.016 | False |
| 2K/4K | 5 | 0.023 | 0.047 | False |
| 2K/4K | 6 | 0.016 | 0.023 | False |
| 2K/4K | 7 | 0.039 | 0.031 | False |
| 2K/4K | 8 | 0.039 | 0.023 | False |
| 2K/4K | 9 | 0.023 | 0.062 | False |
| 8K/16K | 1 | 0.141 | 0.148 | False |
| 8K/16K | 10 | 0.102 | 0.145 | False |
| 8K/16K | 2 | 0.121 | 0.133 | False |
| 8K/16K | 3 | 0.188 | 0.145 | False |
| 8K/16K | 4 | 0.156 | 0.164 | False |
| 8K/16K | 5 | 0.176 | 0.160 | False |
| 8K/16K | 6 | 0.098 | 0.094 | False |
| 8K/16K | 7 | 0.121 | 0.172 | False |
| 8K/16K | 8 | 0.191 | 0.148 | False |
| 8K/16K | 9 | 0.145 | 0.164 | False |
| 8K/4K | 1 | 0.145 | 0.152 | False |
| 8K/4K | 10 | 0.105 | 0.145 | False |
| 8K/4K | 2 | 0.133 | 0.141 | False |
| 8K/4K | 3 | 0.176 | 0.129 | False |
| 8K/4K | 4 | 0.152 | 0.164 | False |
| 8K/4K | 5 | 0.172 | 0.141 | False |
| 8K/4K | 6 | 0.113 | 0.117 | False |
| 8K/4K | 7 | 0.145 | 0.168 | False |
| 8K/4K | 8 | 0.156 | 0.148 | False |
| 8K/4K | 9 | 0.141 | 0.141 | False |


## Assessment

- interpretable: True


## What may not be said

- Nothing about capacity, useful-capacity scaling, locality, transfer or adding facts later.
- Not an unbiased first test of A5-D: it was added after P9-II's outcome was observed, knowing it was RELIABLE there (confirmatory replication on new draws).
- Nothing about natural language, another backbone or student, loads other than 0.5 and (label-free arms) 2 facts per slot, or any regime other than 512 exposures per fact.
- Nothing reliable about 65,536 slots: three draws, one initialization seed, a probe.
- Not that the interface finds where to read: the memory is told the answer position in every arm, WX included.
- Not that a qualified arm beats a tuned baseline (A0 is untuned by design), and no efficiency, latency or storage claim.
- Not a failure of the ArborLM concept, whatever the outcome; not a success of it either.

**FOURTH ARM: A5-D — ADDED BY THE HUMAN LEAD'S DECISION OF 2026-11-15; THE REGISTERED MAPPING GAVE NONE (P9-II CARRIED A0)**

*A0 is UNRELIABLE at 4,096 (4/16) and at chance at matched updates at 16,384; A5-D is the only label-free arm RELIABLE at both sizes; A5-D was not probed at 65,536 because the rule sent A0 to Stage 3.*

**"A5-D was added after P9-II's outcome was observed, knowing it was RELIABLE there (16/16 at 4,096; 8/8 at 16,384). For A5-D, S0 is a confirmatory replication on new draws, not an unbiased first test. Its CONSISTENT ACROSS STUDIES label and pooled count include the P9-II records it was chosen on and add no independent evidence; no pooled per-draw bound is printed for A5-D."**

