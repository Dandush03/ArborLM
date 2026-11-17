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

**Outcome (row 4): ADDRESSING-QUALIFIED (4,096 AND 16,384)**

1. **Arm and calibrated value:** A5-D; μ = 1.0 (P9-II's audited calibration record).

**FOURTH ARM: A5-D — ADDED BY THE HUMAN LEAD'S DECISION OF 2026-11-15; THE REGISTERED MAPPING GAVE NONE (P9-II CARRIED A0)**

*A0 is UNRELIABLE at 4,096 (4/16) and at chance at matched updates at 16,384; A5-D is the only label-free arm RELIABLE at both sizes; A5-D was not probed at 65,536 because the rule sent A0 to Stage 3.*

**"A5-D was added after P9-II's outcome was observed, knowing it was RELIABLE there (16/16 at 4,096; 8/8 at 16,384). For A5-D, S0 is a confirmatory replication on new draws, not an unbiased first test. Its CONSISTENT ACROSS STUDIES label and pooled count include the P9-II records it was chosen on and add no independent evidence; no pooled per-draw bound is printed for A5-D."**

2. **Supervision:** (LABEL-FREE)
3. **Regime:** 512 exposures per fact (U = 8,192 updates at 2,048 facts, 4U = 32,768 at 8,192 facts); schedules in exposures per fact; 0.5 facts per slot at 2K/4K and 8K/16K.
4. **Per size:**
   - 4,096 slots (2K/4K): S0 RELIABLE (20/20 cells; 10/10 draws; per-draw bound 0.741); P9-II class RELIABLE; REPLICATES P9-II; pooled: 18 of 18 draws succeeded (P9-II 8 of 8; S0 10 of 10); no pooled per-draw bound is printed for A5-D; **CONSISTENT ACROSS STUDIES**.
   - 16,384 slots (8K/16K): S0 RELIABLE (20/20 cells; 10/10 draws; per-draw bound 0.741); P9-II class RELIABLE; REPLICATES P9-II; pooled: 14 of 14 draws succeeded (P9-II 4 of 4; S0 10 of 10); no pooled per-draw bound is printed for A5-D; **CONSISTENT ACROSS STUDIES**.
5. **Annotations (sections 8.6 and 8.4):**
   - OVERLOAD NOT QUALIFIED
   - RECORD-LENGTH-FREE VARIANT: DOES NOT PASS (not evidence that the record length is required) (block status COMPLETE)
   - AT 65,536 (probe; not a qualification; S0 only; three draws; one initialization seed): 3 of 3 succeed (per-draw bound 0.368)
   - 4,096 slots (2K/4K): ADDRESS STABLE (median 0.916); COLLAPSE-FREE: 20 of 20 counted cells never had a collapse onset
   - 16,384 slots (8K/16K): ADDRESS STABLE (median 0.871); COLLAPSE-FREE: 20 of 20 counted cells never had a collapse onset
   - 4,096 slots (2K/4K): DENSE COMPARISON DENSE AT CEILING
   - 4,096 slots (2K/4K): sustained success: 20 of 20 cells with a first success (descriptive)
   - 4,096 slots (2K/4K): i = 4.984 bits per fact (median over cells, the smaller panel; reported)
   - 16,384 slots (8K/16K): DENSE COMPARISON DENSE AT CEILING
   - 16,384 slots (8K/16K): sustained success: 20 of 20 cells with a first success (descriptive)
   - 16,384 slots (8K/16K): i = 4.979 bits per fact (median over cells, the smaller panel; reported)
6. **The other arms** (class under S0's criteria; paired against A0 under S0's criteria with d under P9-II's criteria beside it):
   - A0 at 4,096 slots (2K/4K): UNRELIABLE
   - A0 at 16,384 slots (8K/16K): RELIABLE
   - A1 at 4,096 slots (2K/4K): RELIABLE; IMPROVES ON A0 (d = 11; P9-II criteria: d = 11)
   - A1 at 16,384 slots (8K/16K): UNRELIABLE; HARMS (d = -4; P9-II criteria: d = -4)
   - A2 at 4,096 slots (2K/4K): FAILS; HARMS (d = -9; P9-II criteria: d = -9)
   - A2 at 16,384 slots (8K/16K): FAILS; HARMS (d = -17; P9-II criteria: d = -17)
7. **Fixed sentences:** W7 is told the record length. The memory is told the answer position. Synthetic fixed-length records; one frozen 27,392-parameter backbone.


## Classes per arm and cell type

| arm | cell type | S0 class (S0's criteria) | class under P9-II's criteria | P9-II class | replication | consistency | pooled (P9-II's criteria) | ADDRESS STABLE | collapse |
|---|---|---|---|---|---|---|---|---|---|
| A0 (LABEL-FREE) | 2K/4K | UNRELIABLE (9/20 cells; 3/10 draws; per-draw bound 0.087) | UNRELIABLE (9/20 cells; 3/10 draws; per-draw bound 0.087) | UNRELIABLE | REPLICATES P9-II | INCONSISTENT ACROSS STUDIES | 5 of 18 draws succeeded (P9-II 2 of 8; S0 3 of 10); pooled per-draw bound 0.116 | ADDRESS STABLE (0.876) | COLLAPSE-FREE: 0 of 20 counted cells never had a collapse onset |
| A0 (LABEL-FREE) | 8K/16K | RELIABLE (19/20 cells; 9/10 draws; per-draw bound 0.606) | RELIABLE (19/20 cells; 9/10 draws; per-draw bound 0.606) | RELIABLE | REPLICATES P9-II | CONSISTENT ACROSS STUDIES | 13 of 14 draws succeeded (P9-II 4 of 4; S0 9 of 10); pooled per-draw bound 0.703 | ADDRESS STABLE (0.896) | COLLAPSE-FREE: 0 of 20 counted cells never had a collapse onset |
| A0 (LABEL-FREE) | 8K/4K | FAILS (0/10 cells; 0/10 draws; per-draw bound 0.000) | FAILS (0/10 cells; 0/10 draws; per-draw bound 0.000) | — | NOT COMPARABLE | — | NOT AVAILABLE (S0's protocol at this cell type is not P9-II's) | ADDRESS STABLE (0.833) | COLLAPSE-FREE: 0 of 10 counted cells never had a collapse onset |
| A1 (ADDRESS-SUPERVISED IN TRAINING) | 2K/4K | RELIABLE (20/20 cells; 10/10 draws; per-draw bound 0.741) | RELIABLE (20/20 cells; 10/10 draws; per-draw bound 0.741) | RELIABLE | REPLICATES P9-II | CONSISTENT ACROSS STUDIES | 18 of 18 draws succeeded (P9-II 8 of 8; S0 10 of 10); pooled per-draw bound 0.847 | ADDRESS STABLE (1.000) | COLLAPSE-FREE: 3 of 20 counted cells never had a collapse onset |
| A1 (ADDRESS-SUPERVISED IN TRAINING) | 8K/16K | UNRELIABLE (15/20 cells; 5/10 draws; per-draw bound 0.222) | UNRELIABLE (15/20 cells; 5/10 draws; per-draw bound 0.222) | UNRELIABLE | REPLICATES P9-II | INCONSISTENT ACROSS STUDIES | 7 of 14 draws succeeded (P9-II 2 of 4; S0 5 of 10); pooled per-draw bound 0.264 | ADDRESS STABLE (0.999) | COLLAPSE-FREE: 0 of 20 counted cells never had a collapse onset |
| A2 (ADDRESS-SUPERVISED IN TRAINING) | 2K/4K | FAILS (0/20 cells; 0/10 draws; per-draw bound 0.000) | FAILS (0/20 cells; 0/10 draws; per-draw bound 0.000) | FAILS | REPLICATES P9-II | INCONSISTENT ACROSS STUDIES | 0 of 18 draws succeeded (P9-II 0 of 8; S0 0 of 10); pooled per-draw bound 0.000 | ADDRESS STABLE (0.809) | COLLAPSE-FREE: 0 of 20 counted cells never had a collapse onset |
| A2 (ADDRESS-SUPERVISED IN TRAINING) | 8K/16K | FAILS (2/20 cells; 0/10 draws; per-draw bound 0.000) | FAILS (2/20 cells; 0/10 draws; per-draw bound 0.000) | — | NOT COMPARABLE | SINGLE-STUDY EVIDENCE | NOT AVAILABLE | ADDRESS STABLE (0.842) | COLLAPSE-FREE: 0 of 20 counted cells never had a collapse onset |
| A5-D (LABEL-FREE) | 2K/4K | RELIABLE (20/20 cells; 10/10 draws; per-draw bound 0.741) | RELIABLE (20/20 cells; 10/10 draws; per-draw bound 0.741) | RELIABLE | REPLICATES P9-II | CONSISTENT ACROSS STUDIES | 18 of 18 draws succeeded (P9-II 8 of 8; S0 10 of 10); no pooled per-draw bound is printed for A5-D | ADDRESS STABLE (0.916) | COLLAPSE-FREE: 20 of 20 counted cells never had a collapse onset |
| A5-D (LABEL-FREE) | 8K/16K | RELIABLE (20/20 cells; 10/10 draws; per-draw bound 0.741) | RELIABLE (20/20 cells; 10/10 draws; per-draw bound 0.741) | RELIABLE | REPLICATES P9-II | CONSISTENT ACROSS STUDIES | 14 of 14 draws succeeded (P9-II 4 of 4; S0 10 of 10); no pooled per-draw bound is printed for A5-D | ADDRESS STABLE (0.871) | COLLAPSE-FREE: 20 of 20 counted cells never had a collapse onset |
| A5-D (LABEL-FREE) | 8K/4K | FAILS (1/10 cells; 1/10 draws; per-draw bound 0.005) | FAILS (1/10 cells; 1/10 draws; per-draw bound 0.005) | — | NOT COMPARABLE | — | NOT AVAILABLE (S0's protocol at this cell type is not P9-II's) | ADDRESS STABLE (0.863) | COLLAPSE-FREE: 10 of 10 counted cells never had a collapse onset |

UNRELIABLE and FAILS enter no rule; qualification, replication and OVERLOAD use RELIABLE against not RELIABLE only. P9-II's classes are those of its registered record (read through the arm-selection record).

- A1: P9-II NEGATIVE CONTROL at 4,096: not failed; at 16,384: not failed (P9-II's printed result, repeated).
- A2: P9-II NEGATIVE CONTROL at 4,096: not failed; at 16,384: not failed (P9-II's printed result, repeated).
- A0 at 2K/4K: i median 3.470 bits per fact (reported); ADDRESS STABLE non-finite cells counted as 0: 0
- A0 at 2K/4K: sustained success: 10 of 10 cells with a first success (descriptive)
- A0 at 8K/16K, readout at U: FAILS — ALSO AT MATCHED UPDATES (enters no rule).
- A0 at 8K/16K: DENSE COMPARISON DENSE AT CEILING
- A0 at 8K/16K: i median 4.934 bits per fact (reported); ADDRESS STABLE non-finite cells counted as 0: 0
- A0 at 8K/16K: sustained success: 20 of 20 cells with a first success (descriptive)
- A0 at 8K/4K, readout at U: FAILS — ALSO AT MATCHED UPDATES (enters no rule).
- A0 at 8K/4K: i median 3.976 bits per fact (reported); ADDRESS STABLE non-finite cells counted as 0: 0
- A0 at 8K/4K: sustained success: 7 of 7 cells with a first success (descriptive)
- A1 at 2K/4K: ADDRESS RECALL median 1.000 ADDRESS RECALL
- A1 at 2K/4K: DENSE COMPARISON DENSE AT CEILING
- A1 at 2K/4K: i median 4.919 bits per fact (reported); ADDRESS STABLE non-finite cells counted as 0: 0
- A1 at 2K/4K: sustained success: 20 of 20 cells with a first success (descriptive)
- A1 at 8K/16K, readout at U: FAILS — ALSO AT MATCHED UPDATES (enters no rule).
- A1 at 8K/16K: ADDRESS RECALL median 1.000 ADDRESS RECALL
- A1 at 8K/16K: i median 4.803 bits per fact (reported); ADDRESS STABLE non-finite cells counted as 0: 0
- A1 at 8K/16K: sustained success: 20 of 20 cells with a first success (descriptive)
- A2 at 2K/4K: ADDRESS RECALL median 0.004 
- A2 at 2K/4K: i median 0.012 bits per fact (reported); ADDRESS STABLE non-finite cells counted as 0: 0
- A2 at 8K/16K, readout at U: FAILS — MID-SCHEDULE (not a matched-update run) (enters no rule).
- A2 at 8K/16K: ADDRESS RECALL median 0.003 
- A2 at 8K/16K: i median 4.142 bits per fact (reported); ADDRESS STABLE non-finite cells counted as 0: 0
- A2 at 8K/16K: sustained success: 10 of 10 cells with a first success (descriptive)
- A5-D at 2K/4K: DENSE COMPARISON DENSE AT CEILING
- A5-D at 2K/4K: i median 4.984 bits per fact (reported); ADDRESS STABLE non-finite cells counted as 0: 0
- A5-D at 2K/4K: sustained success: 20 of 20 cells with a first success (descriptive)
- A5-D at 8K/16K, readout at U: UNRELIABLE — ALSO AT MATCHED UPDATES (enters no rule).
- A5-D at 8K/16K: DENSE COMPARISON DENSE AT CEILING
- A5-D at 8K/16K: i median 4.979 bits per fact (reported); ADDRESS STABLE non-finite cells counted as 0: 0
- A5-D at 8K/16K: sustained success: 20 of 20 cells with a first success (descriptive)
- A5-D at 8K/4K, readout at U: FAILS — ALSO AT MATCHED UPDATES (enters no rule).
- A5-D at 8K/4K: i median 4.448 bits per fact (reported); ADDRESS STABLE non-finite cells counted as 0: 0
- A5-D at 8K/4K: sustained success: 10 of 10 cells with a first success (descriptive)

**FOURTH ARM: A5-D — ADDED BY THE HUMAN LEAD'S DECISION OF 2026-11-15; THE REGISTERED MAPPING GAVE NONE (P9-II CARRIED A0)**

*A0 is UNRELIABLE at 4,096 (4/16) and at chance at matched updates at 16,384; A5-D is the only label-free arm RELIABLE at both sizes; A5-D was not probed at 65,536 because the rule sent A0 to Stage 3.*

**"A5-D was added after P9-II's outcome was observed, knowing it was RELIABLE there (16/16 at 4,096; 8/8 at 16,384). For A5-D, S0 is a confirmatory replication on new draws, not an unbiased first test. Its CONSISTENT ACROSS STUDIES label and pooled count include the P9-II records it was chosen on and add no independent evidence; no pooled per-draw bound is printed for A5-D."**


## Paired comparisons with A0

d(X) over the 20 pairs of cells, success under S0's criteria (the readings H20-B, H20-C and H20-D use), with d under P9-II's criteria printed beside it (it enters no reading).

| arm | cell type | label (S0's criteria) | d | p (sign test) | d under P9-II's criteria | label (P9-II's criteria) |
|---|---|---|---|---|---|---|
| A1 | 2K/4K | IMPROVES ON A0 | 11 | 0.001 | 11 | IMPROVES ON A0 |
| A1 | 8K/16K | HARMS | -4 | 0.219 | -4 | HARMS |
| A2 | 2K/4K | HARMS | -9 | 0.004 | -9 | HARMS |
| A2 | 8K/16K | HARMS | -17 | 0.000 | -17 | HARMS |
| A5-D | 2K/4K | IMPROVES ON A0 | 11 | 0.001 | 11 | IMPROVES ON A0 |
| A5-D | 8K/16K | NOT DISTINGUISHED FROM A0 | 1 | 1.000 | 1 | NOT DISTINGUISHED FROM A0 |

d(A2 against A1) at 2K/4K (descriptive): -20 (p = 0.000).

d(A2 against A1) at 8K/16K (descriptive): -13 (p = 0.000).

H20-D note: A0 fails 1 of its cells at 8K/16K, fewer than four: IMPROVES ON A0 is unreachable and H20-D reads not supported, whatever A5-D does (the registered reading).

**FOURTH ARM: A5-D — ADDED BY THE HUMAN LEAD'S DECISION OF 2026-11-15; THE REGISTERED MAPPING GAVE NONE (P9-II CARRIED A0)**

*A0 is UNRELIABLE at 4,096 (4/16) and at chance at matched updates at 16,384; A5-D is the only label-free arm RELIABLE at both sizes; A5-D was not probed at 65,536 because the rule sent A0 to Stage 3.*

**"A5-D was added after P9-II's outcome was observed, knowing it was RELIABLE there (16/16 at 4,096; 8/8 at 16,384). For A5-D, S0 is a confirmatory replication on new draws, not an unbiased first test. Its CONSISTENT ACROSS STUDIES label and pooled count include the P9-II records it was chosen on and add no independent evidence; no pooled per-draw bound is printed for A5-D."**


## Qualification (section 8.5)

Preference order, fixed: A0, A5-D, A2, A1 (C4 = A5-D; the order was fixed in revision 3, before P9-II ran; the occupant of C4 was chosen after).

- A0: qualifies at 16,384 ONLY
- A1: qualifies at 4,096 ONLY
- A2: qualifies at no size
- A5-D: qualifies at 4,096 AND 16,384
- ALSO QUALIFIES: A1 (4,096 ONLY)

**FOURTH ARM: A5-D — ADDED BY THE HUMAN LEAD'S DECISION OF 2026-11-15; THE REGISTERED MAPPING GAVE NONE (P9-II CARRIED A0)**

*A0 is UNRELIABLE at 4,096 (4/16) and at chance at matched updates at 16,384; A5-D is the only label-free arm RELIABLE at both sizes; A5-D was not probed at 65,536 because the rule sent A0 to Stage 3.*

**"A5-D was added after P9-II's outcome was observed, knowing it was RELIABLE there (16/16 at 4,096; 8/8 at 16,384). For A5-D, S0 is a confirmatory replication on new draws, not an unbiased first test. Its CONSISTENT ACROSS STUDIES label and pooled count include the P9-II records it was chosen on and add no independent evidence; no pooled per-draw bound is printed for A5-D."**


## Annotations on the candidate (section 8.6)

- OVERLOAD: OVERLOAD NOT QUALIFIED
- WX block status: COMPLETE; RECORD-LENGTH-FREE VARIANT: DOES NOT PASS (not evidence that the record length is required)
- 65,536 probe status: COMPLETE; 3 of 3 succeed (per-draw bound 0.368)
- WX at 2K/4K: FAILS (2/10 cells; ADDRESS STABLE ADDRESS STABLE; descriptive AUC of max_s a_s for answer sites against the other 55 positions: median 0.929; i median 3.220 bits per fact)
- WX at 8K/16K: FAILS (0/10 cells; ADDRESS STABLE no; descriptive AUC of max_s a_s for answer sites against the other 55 positions: median 0.843; i median 1.708 bits per fact)
- A failure of WX is not evidence that the record length is required; WX is never the qualified interface.


## Hypothesis readings (section 8.7)

| hypothesis | reading | notes |
|---|---|---|
| H20-A | supported |  |
| H20-B | CONTRADICTED | arm: A1; paired: {'2K/4K': 'IMPROVES ON A0', '8K/16K': 'HARMS'} |
| H20-C | CONTRADICTED | arm: A2; paired: {'2K/4K': 'HARMS', '8K/16K': 'HARMS'} |
| H20-D | not supported | a5d_provenance: {'f1_annotation': 'A0 is UNRELIABLE at 4,096 (4/16) and at chance at matched updates at 16,384; A5-D is the only label-free arm RELIABLE at both sizes; A5-D was not probed at 65,536 because the rule sent A0 to Stage 3.', 'fourth_arm_string': "FOURTH ARM: A5-D — ADDED BY THE HUMAN LEAD'S DECISION OF 2026-11-15; THE REGISTERED MAPPING GAVE NONE (P9-II CARRIED A0)", 'provenance_sentence': "A5-D was added after P9-II's outcome was observed, knowing it was RELIABLE there (16/16 at 4,096; 8/8 at 16,384). For A5-D, S0 is a confirmatory replication on new draws, not an unbiased first test. Its CONSISTENT ACROSS STUDIES label and pooled count include the P9-II records it was chosen on and add no independent evidence; no pooled per-draw bound is printed for A5-D."}; arm: A5-D; paired: {'2K/4K': 'IMPROVES ON A0', '8K/16K': 'NOT DISTINGUISHED FROM A0'}; registered_note: A0 fails 1 of its cells at 8K/16K, fewer than four: IMPROVES ON A0 is unreachable and H20-D reads not supported, whatever A5-D does (the registered reading) |
| H20-L | not supported | label: RECORD-LENGTH-FREE VARIANT: DOES NOT PASS (not evidence that the record length is required); note: a failure of WX is never evidence that the record length is required; H20-L is never contradicted |
| H20-O | not supported | descriptive_a5d_8k_4k_class: FAILS; label: OVERLOAD NOT QUALIFIED |
| H20-Q | supported |  |
| H20-R (A0, 2K/4K) | supported | label: REPLICATES P9-II |
| H20-R (A0, 8K/16K) | supported | label: REPLICATES P9-II |
| H20-R (A1, 2K/4K) | supported | label: REPLICATES P9-II |
| H20-R (A1, 8K/16K) | supported | label: REPLICATES P9-II |
| H20-R (A2, 2K/4K) | supported | label: REPLICATES P9-II |
| H20-R (A2, 8K/16K) | not read | label: NOT COMPARABLE |
| H20-R (A5-D, 2K/4K) | supported | a5d_provenance: {'f1_annotation': 'A0 is UNRELIABLE at 4,096 (4/16) and at chance at matched updates at 16,384; A5-D is the only label-free arm RELIABLE at both sizes; A5-D was not probed at 65,536 because the rule sent A0 to Stage 3.', 'fourth_arm_string': "FOURTH ARM: A5-D — ADDED BY THE HUMAN LEAD'S DECISION OF 2026-11-15; THE REGISTERED MAPPING GAVE NONE (P9-II CARRIED A0)", 'provenance_sentence': "A5-D was added after P9-II's outcome was observed, knowing it was RELIABLE there (16/16 at 4,096; 8/8 at 16,384). For A5-D, S0 is a confirmatory replication on new draws, not an unbiased first test. Its CONSISTENT ACROSS STUDIES label and pooled count include the P9-II records it was chosen on and add no independent evidence; no pooled per-draw bound is printed for A5-D."}; label: REPLICATES P9-II |
| H20-R (A5-D, 8K/16K) | supported | a5d_provenance: {'f1_annotation': 'A0 is UNRELIABLE at 4,096 (4/16) and at chance at matched updates at 16,384; A5-D is the only label-free arm RELIABLE at both sizes; A5-D was not probed at 65,536 because the rule sent A0 to Stage 3.', 'fourth_arm_string': "FOURTH ARM: A5-D — ADDED BY THE HUMAN LEAD'S DECISION OF 2026-11-15; THE REGISTERED MAPPING GAVE NONE (P9-II CARRIED A0)", 'provenance_sentence': "A5-D was added after P9-II's outcome was observed, knowing it was RELIABLE there (16/16 at 4,096; 8/8 at 16,384). For A5-D, S0 is a confirmatory replication on new draws, not an unbiased first test. Its CONSISTENT ACROSS STUDIES label and pooled count include the P9-II records it was chosen on and add no independent evidence; no pooled per-draw bound is printed for A5-D."}; label: REPLICATES P9-II |
| H20-S | supported | label: 3 of 3 succeed (per-draw bound 0.368); note: annotation; never part of the label; permits nothing |

Every reading is about S0's draws. A hypothesis reading is not a success of the science.


## Oracle-query reference A6 per draw

| cell type | draw | A6 accuracy A | A6 accuracy B | evaluated |
|---|---|---|---|---|
| 2K/4K | 1 | 1.000 | 1.000 | True |
| 2K/4K | 10 | 1.000 | 1.000 | True |
| 2K/4K | 2 | 1.000 | 1.000 | True |
| 2K/4K | 3 | 1.000 | 1.000 | True |
| 2K/4K | 4 | 1.000 | 1.000 | True |
| 2K/4K | 5 | 1.000 | 1.000 | True |
| 2K/4K | 6 | 1.000 | 1.000 | True |
| 2K/4K | 7 | 1.000 | 1.000 | True |
| 2K/4K | 8 | 1.000 | 1.000 | True |
| 2K/4K | 9 | 1.000 | 1.000 | True |
| 8K/16K | 1 | 1.000 | 1.000 | True |
| 8K/16K | 10 | 1.000 | 1.000 | True |
| 8K/16K | 2 | 1.000 | 1.000 | True |
| 8K/16K | 3 | 1.000 | 1.000 | True |
| 8K/16K | 4 | 1.000 | 1.000 | True |
| 8K/16K | 5 | 1.000 | 1.000 | True |
| 8K/16K | 6 | 1.000 | 1.000 | True |
| 8K/16K | 7 | 1.000 | 1.000 | True |
| 8K/16K | 8 | 1.000 | 1.000 | True |
| 8K/16K | 9 | 1.000 | 1.000 | True |
| 8K/4K | 1 | 0.995 | 0.995 | True |
| 8K/4K | 10 | 0.994 | 0.995 | True |
| 8K/4K | 2 | 0.995 | 0.994 | True |
| 8K/4K | 3 | 0.994 | 0.995 | True |
| 8K/4K | 4 | 0.995 | 0.995 | True |
| 8K/4K | 5 | 0.995 | 0.995 | True |
| 8K/4K | 6 | 0.997 | 0.996 | True |
| 8K/4K | 7 | 0.994 | 0.993 | True |
| 8K/4K | 8 | 0.995 | 0.995 | True |
| 8K/4K | 9 | 0.996 | 0.995 | True |


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

