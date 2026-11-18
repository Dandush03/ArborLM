# ADR-0025 — P10-I-S2: Sequential teacher transfer, under word-level addresses supplied by rule

**Status: APPROVED FOR IMPLEMENTATION AND REHEARSAL (Decision 1) by the lead under the human lead's delegation of 2026-11-18. Not frozen. No registered run is approved.**

- **Date:** 2026-11-17 (UTC). **Drafted and revised by:** the lead (Claude Fable 5.2). **Independent specification reviews:** the `arbor-auditor` subagent (Opus 5.5), three times (section 18); the third found no blocking finding and was NOT READY only because choices were needed from the lead. This text makes those choices and applies that review's edits; **it has not been reviewed again.** Approval: section 17. Nothing under this ADR is implemented, calibrated, frozen or run.
- **Study code** P10IS2. **Package** `studies/p10is2/` (new files only). **Seeds:** section 6.
- **Predecessor:** P10-S2 (ADR-0022), registered outcome TRANSFER-INCONCLUSIVE: TEACHERS-NOT-QUALIFIED, accepted by the human lead as registered. That outcome is not revised and P10-S2 is not reopened. This is a new study with new seeds.
- **Oracle qualification.** Every address and every registered route is supplied by rule. The human lead's instruction, verbatim as ADR-0022 records it: "S1 and S2 must not claim autonomous learned-memory success from oracle-assisted results." Section 5.4 puts the oracle-assisted line above every printed line.
- ArborLM is unproven research; no line of this study is a success claim. `Astra review: NOT_PERFORMED`. Claude review is not Astra review.
- Figures marked *(lead's choice)* are judgment calls fixed here before any observation. None is taken from a paper.

## 1. Question and outcomes

**Question.** Under word-level addresses supplied by rule, can a frozen pretrained student with an expandable key–value memory acquire a lexical capability from a first pretrained teacher, then a second from a second teacher, and still hold the first — and how does that compare with a dense adapter trained the same way, with lookup baselines, and with no memory?

**Part Q** qualifies the teachers and generates the material. **Part T** measures transfer. Part Q is finished, independently recomputed and accepted as registered before Part T is frozen. Each part has its own candidate plan, rehearsals, caps, freeze and Decision 2 (section 10).

Registered lines. Each is printed separately; none substitutes for another.

| Line | Positive means | Negative means | Inconclusive means |
|---|---|---|---|
| QUALIFICATION (Part Q) | Both teachers meet the quality criteria and the material exists in the required amount | A teacher fails a quality criterion. Says nothing about transfer | The corpus cannot supply the counts |
| ACQUISITION | The store learned each capability from teacher output alone, on held-out sentences, and the gain depends on the stored content | The store did not learn a capability within the registered training length | Mixed across cells, or a control failed |
| RETENTION | The first capability was kept while the second was acquired in the same store, on a task where the unprotected store does forget | The first capability was lost | Mixed, or retention was not challenged |
| GENERAL-QUALITY | With a learned keyword router deciding whether the store is read, ordinary English text is not degraded | It is degraded | — |
| AGAINST-DENSE | Printed as two labels (acquisition, retention), never merged into one. For each: the store is ahead of the dense adapter trained the same way | The dense adapter is ahead | Not distinguished or mixed |
| AGAINST-LOOKUP | The store is ahead of every lookup and retrieval baseline | A lookup baseline does as well: the result shows nothing a lookup cannot provide | Mixed |

**Milestone question 2** (sequential acquisition with retention) is one derived line, built as ADR-0022's study label was:

- SUPPORTED (append-frozen), or SUPPORTED (append-frozen + consolidation): ACQUISITION-POSITIVE and RETENTION-POSITIVE and GENERAL-QUALITY PRESERVED (section 8.4).
- **WITHHELD — GENERAL QUALITY NOT PRESERVED UNDER A LEARNED ROUTE:** ACQUISITION and RETENTION are positive and the GEN check fails in any cell. Neither a positive nor a negative.
- NOT ESTABLISHED: otherwise.

AGAINST-DENSE and AGAINST-LOOKUP are printed directly beneath it. If AGAINST-LOOKUP is LOOKUP SUFFICES, the milestone line itself carries "a lookup baseline does as well: {name}".

Descriptive lines, which enter no line above: MODIFICATION (M-ii), COMPOSES C1 / C2, the annotations of ADR-0022 section 11.4, and the cost lines (section 8.5).

## 2. Background

| Finding | Record |
|---|---|
| P10-S2 stopped before its freeze on counts: accepted Q_check items 78 and 22 against 150; accepted pools 7,804 and 2,341 against 8,000. Own scores 0.7675 and 0.7754 (bar 0.55), margins 0.6214 and 0.6425 (bar 0.30) and a Q_fit filter setting passed. Q_check precision was 0.9231 (72 of 78) and 0.9545 (21 of 22) | `results/p10s2-datagen-2026-11-16/README.md`, `prefreeze_record.json` |
| Acceptance: 104 and 41 of 500 on Q_fit; 13.0% (A) and 3.9% (B) of 60,000 generation sources. Sources: 734,418 (A) and 784,089 (B). Generation: 740 s and 844 s per 60,000 at the default thread count; peak memory 5,677 MiB | same (`filter`, `partition`, `steps.memory_by_phase`) |
| P10-S2's partition holds 181,970 (A) and 132,151 (B) gold keys outside the panels, 67,626 of them with both references. The two source pools therefore share about 669,900 sources | bundle `partition.json` under `.claude/worktrees/agent-a91c79a181109bb9c/data/p10s2-pre-20261115/data/bundle/` (the reviewer's count, `REVIEW2_ADR-0025.md` N1) |
| The gate's per-item inputs were not stored; the filter's word count was not defined in the ADR; teacher outputs differ with the thread count | `docs/reviews/p10s2-qualification-2026-11-16/REVIEW.md`; README |
| P10-S1, oracle addressing: no line positive for the store; DICT DOMINATES ON THIS TASK; DENSE AHEAD at matched updates (at matched compute the flat store led at 32K/16K in 5 of 5 replicates); memory arms at an untuned rate; UNDERTRAINED-AT-U_P | `results/p10s1-run-2026-11-17/OUTCOME.md` |
| P10-S0: learned addressing qualified at 0.5 facts per slot on the byte backbone with the answer position given; overload (2 facts per slot) not qualified | `results/p10s0-run-2026-11-16/OUTCOME.md` |
| The human lead's P10 list includes "mechanism ii", "capabilities A, B, combined" and "the five cost measures"; he strengthened the COMPOSES rule | `adr-0022-review/CONFIRM.md` section 7 item 6; `HUMAN_DECISIONS_2026-11-15.md` |

`DIRECTION.md` section 5 says both teachers "passed the quality criteria". The Q_check precision was read on 78 and 22 items (95% Wilson lower bounds 0.842 and 0.782), below the 150 required, so filter precision is not yet established; Part Q measures it. The teachers and corpus are P10-S2's and their figures have been seen: Part Q is a confirmatory re-measurement on a new partition.

## 3. Every change from ADR-0022 (revision 5 with its addenda)

Anything not in this table is as ADR-0022, whose sections are cited as definitions and not edited. Arm names map: ST1 → M1, M-append-frozen → M-append, LoRA-1 → D1, L-seq → D-seq, L-joint → D-joint, L-sep → D-sep, M-i-separate → M-sep.

| # | Item | ADR-0022 | This study | Why |
|---|---|---|---|---|
| 1 | Teacher qualification | A gate inside the pre-freeze step | Part Q, a registered stage with its own outcome | A count shortfall must not end the study |
| 2 | Amount of generation and of Q_check | Fixed: 60,000 sources; 500 items | Generate until met, within a budget (section 4.3) | `DIRECTION.md` section 5, rule 2 |
| 3 | Q_fit; panel of Q1 and Q2 | Q_fit 500; Q1 and Q2 on Q (1,000) | Q_fit 2,000, fixed; Q1, Q2 and Q3 on it | At 500 items teacher B's filter passes only with zero errors (section 4.2) |
| 4 | Thresholds of Q1–Q4, filter grid, 0.60 cut, population (both references) | — | Same | Scientific thresholds |
| 5 | Per-item Q records; the filter's word count | Not stored; not defined | Stored and hashed; defined (section 4.2) | Audit findings |
| 6 | Shared English sources of A and B | Split in halves after generation | Split before generation, 4/5 to B | The pools share about 669,900 sources. **4/5 is the registered split.** 0.804, the share that equalises the two teachers' expected accepted counts at P10-S2's yields, is its rationale only and is not a parameter |
| 7 | Generation threads | Machine default | Six, fixed | Outputs differ with the thread count |
| 8 | Replicates | Four or three by a rung rule; overlapping draws | Three; disjoint draws if both pools reach 24,000 | The cap is extendable instead; independence of replicates |
| 9 | Training length | 2,000 or 1,000 by budget | Convergence rule to at most 8,000 | P10-S1's UNDERTRAINED-AT-U_P |
| 10 | Learning rates | Store fixed at 0.003; LoRA two values; ties to the first listed | Three values per trained module type; ties to the smaller | P10-S1's untuned memory arms |
| 11 | Arms | — | D-append and R-gloss-icl added; MA-gold and TEACHER-EQUIVALENT-TO-GOLD removed | Section 5.2; the design is teacher-only |
| 12 | Study label | One label, first match of 12 rows | Separate lines plus the milestone line. NOT REPLICATED, INTERMEDIATE and ORDER-DEPENDENT print as INCONCLUSIVE with passing cells per order. NOT STARTED: STUDENT CANNOT USE THE MEMORY is renamed NOT STARTED: PILOT | "No line substitutes for another" |
| 13 | General quality | Gate of the positive label | Same, on the milestone line; also its own line | Unchanged in effect |
| 14 | Retention | NOT_EVALUATED before FORGETS | Negative zone read first over evaluable cells; RETENTION-POSITIVE also needs forgetting pressure from M-seq (so M-seq is no longer only descriptive) | A failure must not be hidden; retention on a task the unprotected store does not forget is empty |
| 15 | ρ and RET | Defined whenever the gap is | Defined for an arm's cell only if its stage-1 module reached G_first ≥ 0.50 | A ratio over a small or negative gain is unstable, notably for dense arms |
| 16 | "At least four evaluable cells" for RETENTION-NEGATIVE | "every replicate" | New figure: four of six | A majority of the six cells, as for forgetting pressure |
| 17 | Margins 0.05 (AGAINST-DENSE; MEMORY ADDS OVER LOOKUP) | Annotations used 0.03 and 0.10 | New lines with a new figure | Just above the precision of a gap closure on 1,000 items (about 0.04, ADR-0022 section 5.2) |
| 18 | M-ii | Class in label rows 7 and 8 | Descriptive MODIFICATION line; decides the "+ consolidation" suffix | Unchanged in effect |
| 19 | Combined tasks | Addendum's rule; ten arm-cells per replicate | Same rule; twelve (D-append added) | Row 11 |
| 20 | Cost lines | TRAINING COST COMPARABLE and others | TRAINING COST COMPARABLE removed; counted training multiply-adds added; the rest kept | No wall-time comparison on a training stage that cannot be isolated (`DIRECTION.md` section 7) |
| 21 | Caps | 36 charged hours, raisable once to 72; a cap stop is INCOMPLETE; 1.5 GB download and 6 GB disk caps | Per part and per stage, charged + 2 × projected remaining, computed by code from its measuring rehearsal (section 10), extendable on cost projections; a cap stop is PAUSED; downloads within the human lead's delegation of 2026-11-17 (under 50 GB in total, no per-item approval), each recorded in the download ledger; none is planned except the fallback's files if the fallback is invoked; new disk 10 GiB *(lead's choice)*, a resource cap | `DIRECTION.md` section 5; per-item records need more disk |
| 22 | Fallback teacher | Replaces one failed teacher | Not part of this study's run. If exactly one teacher fails, Part T does not run and the Part Q label is registered; whether a fallback study follows is the human lead's decision afterwards | Section 4.4: a fallback is chosen after a failure is observed and changes teachers and data |
| 23 | Memory guard of the data step | 8 GiB | 12 GiB | Attempts 6 and 7 stopped at 8.09 and 9.38 GiB |
| 24 | Frozen inputs, seeds, rehearsal | — | Sections 6, 10 and 11: the pattern of ADR-0029 sections 13 and 18–20 | P10's engineering failures |
| 25 | Annotation TASK-CODED SPARSE RETENTION | No guard | NOT EVALUABLE unless both arms have a defined ρ and G_second ≥ 0.50 in every cell (the Δρ guard of section 8.3) | An arm whose second stage learned nothing keeps ρ near 1 trivially; the second review's N2, applied to every reading of Δρ |
| 26 | Order of rows in ACQUISITION | NO-ACQUISITION read before CONTROL-FAILED | **Same.** The third draft read CONTROL-FAILED first; that change was not deliberate and is reverted | The third review's F6 (b) |
| 27 | Denominator of the 300-item control subsample | Only the full-panel denominator could make a gap undefined | A subsample denominator below 0.30 makes the cell's control conditions undefined; the cell counts as a gap undefined and ACQUISITION is NOT EVALUABLE | The control margins are differences of ratios over that denominator; over a small one they are unstable. The change can remove a label and cannot create a positive one |
| 28 | Re-check ruling R16 (the data step may be re-run after a cap stop or an engineering error) | Any stop of the data step on its cap or an engineering error | Kept, narrowed. A cap or guard stop is PAUSED and resumes. A code or environment error in Part Q, before any value of Q1–Q4 has been computed, resumes from the last completed block once the cause is recorded; after that point a second attempt is the human lead's decision. A stop on a registered test of the step returns to the lead, as R16 says (section 8.6) | P10-S2 needed eight attempts; after a quality value exists a re-run could be chosen on it |
| 29 | Size of the Q_check reserve | 500 items, fixed | 16 blocks of 500 | About 2.3 times the 3,409 items B needs at its P10-S2 Q_check share (0.044). **Chosen knowing that share** (section 4.3) |

Reverted to ADR-0022 after the second review, so not changes: the words-only ablation; CONTROL-FAILED on any memory cell; the ensemble integrity check; the sacrebleu cross-check; no intermediate snapshot is scored. Reverted after the third: the order of rows in ACQUISITION (row 26). The evaluation population is also unchanged: E_A, E_B and E_open are not restricted to both-reference sentences (section 4.1, step 3).

## 4. Part Q — teacher qualification and data generation

### 4.1 Order of work and panels

The order is fixed. Each step is complete before the next starts.

1. Hash checks of every input; the applied generation configuration of each teacher is asserted equal to its pinned file and recorded; student conversion and equivalence record (gate G8); tokenizer record.
2. **Fixed-input counts, before any teacher runs.** E_A and E_B at least 500 items each and E_C at least 250 (ADR-0022 section 5.2); at least 3,300 training-side in-vocabulary sentences with both references (Q_fit, D_cal, D_con and one Q_check block; P10-S2's partition held 67,626); 44 marker-like and, after the ledger exclusion below, at least 100 ordinary GEN windows. A shortfall gives QUALIFICATION-INCONCLUSIVE: DATA-INSUFFICIENT.
3. Partition with this study's partition seed. Panels, as in P10-S2: Q_fit, the Q_check reserve, D_cal, D_con and E_C from sentences with both a German and a French reference; E_A, E_B and E_open from evaluation-side sentences with a reference in their language, stratified by reference count (ADR-0022 section 5.2).

| Panel | Size | Use |
|---|---|---|
| E_A, E_B; E_C; E_open | 1,000 each if the data allow; 500; 500 | Evaluation; combined tasks; descriptive. **Never scored before the registered run of Part T** |
| Q_fit | 2,000 | Q1, Q2, Q3 |
| Q_check reserve | 16 blocks of 500 in a seeded order, or as many whole blocks as the pool holds | Q4 |
| D_cal; D_con | 500; 300 | Part T calibration and pilot; M-ii's acceptance constraint |

**Panel populations as measured in P10-S2, and the supply to count.** In P10-S2's partition only 337 of E_A's 1,000 items, 478 of E_B's 1,000 and 131 of E_open's 500 had both references; Q_fit, Q_check, D_cal, D_con and E_C were all both-reference. So:

- E_A and E_B stay at 1,000 each from their own-language populations. Restricting them to both-reference sentences would change the evaluation population (to about a third of E_A's and a half of E_B's, at P10-S2's shares); it is not done.
- The both-reference supply is what limits the other panels. Training side: Q_fit 2,000 + D_cal 500 + D_con 300 = 2,800 fixed, plus the Q_check reserve, of which B is expected to need 7 blocks (3,500) and the whole reserve is 8,000: 6,300 expected, 10,800 at most, against 67,626 in P10-S2's partition. Evaluation side: E_C needs 500 (at least 250) both-reference sentences, drawn as ADR-0022 section 5.2 and the combined-tasks addendum draw it.
- **Counted before Decision 2 of Part Q** (the third draft's "Decision 1", renamed in section 10), in the Part Q measuring rehearsal, with no teacher run: the corpus-level numbers of in-vocabulary identity groups with a German reference, a French reference and both (these do not depend on a partition seed), the same counts on each side of the rehearsal partition, and the ordinary GEN windows left after the ledger exclusion. The Decision 2 record shows them against the requirements above. If the corpus-level supply cannot hold a panel at its minimum, the specification returns to the human lead before the freeze; a shortfall known in advance is not registered as an outcome. Step 2 then counts exactly on the registered partition.

4. The source pools are defined, excluding every identity group of every panel and of the whole Q_check reserve, drawn or not. Shared sources are split (section 4.3, rule 4) and the exact pool sizes are recorded.
5. Teachers and the untrained student on Q_fit; Q1, Q2; the filter is selected (Q3) and fixed.
6. Q_check (section 4.3, rules 1–3); Q4.
7. Generation (rules 4–6). Steps 7 and 8 run only if both teachers pass Q1–Q4.
8. Teacher outputs on E_A, E_B, E_C, E_open, D_cal and D_con, stored and hashed and **not scored**; the token-id bank and tokenization tests of ADR-0022 section 14.2; the chrF cross-check against `sacrebleu` (step 6 there); the truncation limit; the GEN window list; the C1 pairing; token ids of every target-language word type of the accepted pools, each as its own segment with a leading space, for R-gloss-icl, with the separator segments of its template (section 5.2). With these in the bank, Part T encodes no text and needs no tokenizer and no package outside the lock.

No teacher runs after Part Q. Every output is listed with its hash in the Part Q manifest.

**GEN windows and the shared panel ledger.** This study uses all 44 marker-like windows of WikiText-2 validation on the fixed grid, and 100 sampled ordinary windows. All 144 are recorded as (row, byte span) in the shared P10-I panel ledger at the Part Q freeze. ADR-0026 excludes those spans from its own panels; the exclusion runs in that direction, because the marker-like stratum is every such window and cannot give any up. The 100 ordinary windows are sampled only from ordinary windows whose byte spans overlap no span already in the shared ledger at the Part Q freeze (ADR-0026's panels included, if it froze first); step 2 counts the ordinary windows after that exclusion. A window is recorded by its start and end byte offsets in the validation text concatenated as ADR-0022's ruling A-B3 defines, with its first and last row. Two spans overlap if they share at least one byte of that concatenated text; a window that covers several rows has one span, from the first byte of its first token to the last byte of its last token.

### 4.2 Quality criteria (scientific thresholds)

| # | Criterion | Threshold | Reason for the figure |
|---|---|---|---|
| Q1 | Teacher's mean sentence chrF-norm on its own capability, on Q_fit | ≥ 0.55 | Most short sentences substantially right; fixed in ADR-0022 before any teacher was run |
| Q2 | Q1's score minus the larger of the other teacher's and the untrained student's score on that capability | ≥ 0.30 | The capability is the teacher's and absent from the student, so a gap of at least 0.30 exists to close |
| Q3 | On the grid τ ∈ {−0.05, −0.10, …, −0.60} × length ratio ∈ {[0.5, 2.0], [0.6, 1.6]}: the most permissive setting (the largest accepted share on Q_fit, as ADR-0022 section 5.3) whose 95% Wilson lower bound of precision on Q_fit is ≥ 0.90, where an accepted output is correct if its chrF-norm against the best reference is ≥ 0.60. Ties: larger τ, then the narrower range | a setting exists | At most one accepted item in ten wrong; selecting on the lower bound keeps the setting off its own edge |
| Q4 | Point precision of that setting on Q_check (same 0.60 cut), read on at least 150 accepted items | ≥ 0.90 | The same bar on held items; 150 items give a 95% interval of about 0.84–0.94 at the bar |

The filter's length ratio counts whitespace-separated words after normalization, as P10-S2's code computed it (the `accepts` function, `studies/p10s2/filtering.py:56–61`, which also rejects non-finite scores and outputs containing a newline).

**Sampling risk of Q3, and why Q_fit is 2,000.** A Wilson lower bound of 0.90 needs at least 35 accepted items with no error, 53 with one, 69 with two, 84 with three. Teacher B's setting in P10-S2 accepted 41 of 500, all correct: one wrong item would have failed it, a quality failure caused by the size of the panel.

| Q_fit | Expected accepted at P10-S2's shares (A / B) | Errors tolerated (A / B) |
|---|---|---|
| 500 | 104 / 41 | 4 / 0 |
| 2,000 | 416 / 164 | 29 / 8 |

Q_fit is fixed at 2,000 before any observation and is never extended to make a setting pass. A larger panel can admit a more permissive setting nearer the bar; Q4 on held items is the guard.

**Sampling risk of Q4.** At a true precision of 0.92, a reading on 150 to 160 items falls below 0.90 in about one run in six. That is a registered quality failure.

### 4.3 Counts: generate until met, within a budget

None of these counts is a scientific claim. Each is a design ceiling with a rule. Stopping reads accept counts only.

| Count | Target | Block | Ceiling |
|---|---|---|---|
| Accepted Q_check items, per teacher | 150 | 500 items | the reserve (at most 8,000 items). 16 blocks: about 2.3 times the 3,409 items B needs at its P10-S2 Q_check share (0.044); chosen knowing that share |
| Accepted sources per capability: minimum | 10,000 (ADR-0022's 8,000 × 1.25: one draw of 8,000 with a quarter to spare) | 20,000 sources | the capability's split pool |
| Accepted sources per capability: disjoint target | 24,000 (three disjoint draws of 8,000) | same | same |

**Q_check: three stopping rules.**

1. The filter setting is fixed from Q_fit before the first Q_check block is drawn.
2. Blocks are taken in the reserve's seeded order, never skipped or reordered, also across a pause. After each block only the filter is applied and accepted items are counted. Drawing stops at the first block boundary with at least 150 accepted items; the stop block index is recorded.
3. No reference is read and no chrF is computed or logged for any Q_check item before the stop is recorded. Precision is then computed once, in one call, over every accepted item of every block drawn. Q_check is not extended after that.

The accept indicator depends only on the teacher's output and the source, so the number accepted carries no information about correctness (first review, R5).

**Generation.**

4. **Split before generation.** Each identity unit that is a no-gold source for both capabilities is assigned to B with probability 4/5, otherwise to A, by the source-split seed. Each teacher generates only on its own sources. A capability's count is its own accepted outputs after the evaluation-equal drop.
5. Sources are taken in a seeded order in blocks. A capability stops when it reaches 24,000 or its pool ends.
6. **Disjoint or overlapping draws; one joint decision, by rule.** If both capabilities reach 24,000: one seeded permutation per capability orders its accepted pool, and replicate r (0, 1, 2) takes positions 8,000·r to 8,000·r + 7,999. The label is TEACHERS-QUALIFIED (DISJOINT DRAWS). Otherwise, if both reach 10,000: each replicate draws 8,000 with its own training-draw seed from the whole pool, the label is TEACHERS-QUALIFIED (OVERLAPPING DRAWS), and the shared share is printed beside every line that says "every cell". If either is below 10,000 when its pool ends: QUALIFICATION-INCONCLUSIVE: DATA-EXHAUSTED.

**Projection (estimated from P10-S2's partition and yields; the pools are recounted exactly at step 4 before any teacher runs).** A has about 64,500 sources of its own and B about 114,300; about 669,900 are shared. With 4/5 of the shared sources to B, A has about 198,500 sources and B about 650,100. At P10-S2's yields (13.0% and 3.9%) that is about 25,800 accepted for A and about 25,400 for B. The registered split is 4/5; 0.804, the share that equalises the two expected counts, is its rationale only, and both reach 24,000 only for a share between about 0.75 and 0.82. **In expectation A exceeds the disjoint target by about 7.6% and B by about 5.7%. A fall in yield of 7.0% (A) or 5.4% (B) misses it.** The binomial spread of the counts is only about 150, so the outcome depends on the yield the new filter setting gives, not on sampling. Acceptance by the two teachers is correlated and the split changes each pool's mix, so the yields may differ. The 24,000 is a design ceiling, not the claim. If either falls short, OVERLAPPING DRAWS is the registered fallback label; it follows from the accepted counts by rule 6 and is never chosen. The split does not touch qualification, which reads both-reference panels only. It does make the training populations differ: about a third of A's sources have a French reference and about 18% of B's a German one (114,344 of 650,199). Q_check needs about 1,000 items for A and about 3,400 for B.

**Budget and persistence.**

7. Part Q's charged-hours caps are, per stage, the time charged before its freeze plus twice the remaining time projected from its measuring rehearsal with the whole split pools generated (section 10), computed by code. A stop on a cap or guard is PAUSED; the stage resumes at the next block and completed blocks are not regenerated.
8. Every per-item input of the gate is stored and hashed: outputs, beam scores, accept indicators, chrF per item on Q_fit and Q_check, the full grid table, and the score of every rejected generation output.
9. Six threads, fixed and recorded. A fixed output digest per teacher is asserted at every resume. Generation runs in batches of 32 sources in stored block order. The digest and the regeneration subsample are whole stored batches, drawn by seed 250914 and regenerated with the same composition and order.
   - **The layout is frozen.** Batch size 32, the order of sources within a block and the order of blocks are in the Part Q plan. Every teacher run uses it: Q_fit, Q_check, generation and the panel outputs. A batch is stored with its index, its source keys in order, its token sequences and its beam scores.
   - **Digest:** 4 whole batches (128 sources) of the teacher's Q_fit run, the first draw of seed 250914. **Regeneration subsample:** 32 whole generation batches per teacher (1,024 sources), the second draw of seed 250914, taken over all stored generation batches after generation has ended. These replace the earlier "100 sentences" and "1,000 sources", which were not whole batches.
   - **Tolerance and consequence.** On the platform of record, at six threads and with the stored composition and order, every regenerated output token sequence must be identical to the stored one: the tolerance is zero. Beam scores are compared within 1e-4 and a larger difference is printed, not acted on. A different token sequence is a difference in what the study produced: QUALIFICATION-ENGINEERING-FAILURE (section 4.4), with the batch index, the item and both sequences recorded. A subsample regenerated in any other layout proves nothing and is not compared.

### 4.4 QUALIFICATION outcome (first match wins; a per-teacher status table is printed under the label)

| Order | Label | Rule |
|---|---|---|
| 1 | QUALIFICATION-ENGINEERING-FAILURE | A failed gate on study-produced data (as section 11, item 2 distinguishes), a failed G1, an applied generation configuration that differs from the pinned file, a digest mismatch at a resume, or a regeneration difference (below) |
| 2 | QUALIFICATION-INCONCLUSIVE: DATA-INSUFFICIENT | Step 2 of section 4.1 |
| 3 | QUALIFICATION-NEGATIVE: QUALITY (teacher and criterion named) | A teacher fails Q1, Q2, Q3 or the precision of Q4 |
| 4 | QUALIFICATION-INCONCLUSIVE: DATA-EXHAUSTED | The reserve ends before 150 accepted items, or rule 6 |
| 5 | TEACHERS-QUALIFIED (DISJOINT DRAWS / OVERLAPPING DRAWS) | Both teachers pass Q1–Q4 and both pools reach at least 10,000 |

PAUSED is a state of the stage, not an outcome. If the human lead records that a paused stage will not resume, the terminal label is **STOPPED AT A RESOURCE CAP BY DECISION (stage; counts or cells reached)**, in Part Q and in Part T alike. It is not negative; the per-teacher or per-cell table is printed.

**If only one teacher qualifies.** Part T does not run with one teacher: retention needs two. The label of row 3 or 4 is registered. **The rule, fixed now:** if exactly one teacher fails qualification (on quality or on exhaustion), Part T does not run, the Part Q label is registered and Part T is NOT STARTED. The same holds if both fail. **The fallback is not invoked under the delegation and is no part of this study's run.** Whether a fallback study follows is the human lead's decision afterwards, taken on the registered Part Q record.

For that decision, what a fallback would involve: the teacher of ADR-0022 section 4.2 (`Helsinki-NLP/opus-mt-en-es`, a different training regime). Its files (323.4 MB) fall within the download delegation (section 12); the invocation remains the human lead's decision. The Spanish files would come from a later Tatoeba export, which the report would state. A fallback language changes the gold pairs, identity groups and partition, so **both** teachers would pass the whole of Part Q again on a rebuilt partition; the surviving teacher's earlier figures would be printed and would not count. Its seeds and specification would be recorded with that decision, not here.

**Recomputation of Part Q.** Independent, from the stored per-item records. It also regenerates the subsample of section 4.3, rule 9 (32 whole stored batches per teacher) at six threads on the platform of record, in the stored composition and order. The output token sequences must be identical to the stored ones; any difference is QUALIFICATION-ENGINEERING-FAILURE. A difference between a recomputed and a registered value of Q1–Q4 beyond 1e-6, or in any accept indicator, is an engineering stop (section 8.6); no label is then derived.

## 5. Part T — design

### 5.1 Stages of training

Capabilities A (English→German) and B (English→French). Both orders run in every replicate. A **cell** is one (replicate, order) pair: six cells per sequential arm. Every stage runs U updates of batch 32 with AdamW, no weight decay, clip 1.0, constant rate, fresh optimizer state. Training material is teacher output on sentences with no reference in that language. Only the final snapshot of a stage is scored.

### 5.2 Arms

N = 4,096 rows per stage (2,424,833 trainable parameters). LoRA rank 42 on the query and value projections of all 30 blocks (2,419,200), as ADR-0022 section 7.

| Arm | Stage 1 | Stage 2 | What it isolates |
|---|---|---|---|
| S0 (no memory) | — | — | The frozen student: the floor of every gap |
| M1 | N rows on teacher 1 | — | Acquisition from one teacher |
| **M-append** (primary) | = M1 | N rows appended; first-stage rows frozen; one top-8 over 2N rows; teacher 2 | Second acquisition and retention in one store, no switch |
| M-seq | = M1 | Same N rows, all trainable, teacher 2; no growth, no replay | The unprotected store: forgetting pressure. Against M-append: the effect of append-and-freeze |
| M-ii | = M-append's result | All rows trainable; teacher 2 plus 32 replayed first-teacher rows per batch; published only if chrF on D_con stays within 0.02 of M-append's on each capability; modification floor 0.10 (ADR-0022 section 6.3) | Retention under modification (H22-D) |
| D1 | LoRA rank 42 on teacher 1 | — | Dense single-teacher reference |
| **D-append** | = D1 | A second rank-42 adapter; the first frozen; both applied on every task prompt; teacher 2 | The dense adapter trained the same way as M-append; the pair differs in the module |
| D-seq | = D1 | The same adapter continued on teacher 2 | The dense adapter trained the same way as M-seq |
| M-joint, D-joint | 2N rows / rank 84, mixed material, 2U | — | Simultaneous training. Descriptive |
| E-table | One trainable 576-vector per (task, word), at the store's read positions, no keys (1,152,577 parameters per capability) | — | A trained dictionary. Retention BY CONSTRUCTION |
| M-sep, D-sep | assembled from the two M1 / D1 of a replicate behind the oracle route | — | Separate modules with the task given by rule. Retention BY CONSTRUCTION; acquisition empirical |
| Teachers (ensemble) | — | — | The ceiling of every gap (stored outputs) |

Not trained; each uses the replicate's training draw:

| Baseline | Definition | What it isolates |
|---|---|---|
| R-exact | Table from training source to accepted output | Confirms the panels are held out (zero hits, gate G1) |
| R-gloss | Co-occurrence lexicon (Dice), word by word | A word-level dictionary without learning |
| R-gloss-icl | The top gloss of each source word placed in the frozen student's prompt *(lead's choice, from the first review)*. Template below | The untrained analogue of a word-addressed store |
| R-nn | Nearest training source by character-trigram TF-IDF | Sentence retrieval without composition |
| R-icl | The four nearest accepted pairs in the prompt | Retrieval that can generalize |

**R-gloss-icl template *(lead's choice)*.** Before the task prompt that S0 receives, unchanged, one line per in-vocabulary source word that has an entry in the replicate's lexicon, in source order, repeated words included: the source word, the separator ` =`, the top gloss word, a newline. A word with no entry gives no line. The prompt is a concatenation of stored segments only: the source word's segment from the bank, the separator segment, the gloss word's segment stored at Part Q (section 4.1, step 8) and the newline segment. Tokenization test (a) of ADR-0022 section 14.2 is run at Part Q on these prompts for a seeded sample of training sources with a lexicon built from the whole accepted pool; zero mismatches are required. Its longer prompt is a cost and is reported, as for R-icl.

Controls on every memory cell, on a fixed 300-item subsample of each panel, as ADR-0022 section 7: memory off; values permuted; word codes permuted; marker-only; words-only. For M-append they act on the second stage's rows and codes. M-seq and M-ii have no separate second-stage rows: the controls act on all N (M-seq) or 2N (M-ii) rows and the second task's codes. For M-joint they act on all 2N rows and both tasks' codes, each task's controls read on its own panel.

**Fairness of the dense comparison, stated.** Parameters, updates, batch, data and the size of the rate search match. The store also has a two-way read-layer search, an extra tuning dimension in its favour. The store receives the task identity by rule inside its address; D-append and D-seq receive it only through the prompt. D-sep is the dense arm given the same task information by rule. Rates are selected at 2,000 updates for every module type alike and used at U.

### 5.3 What transfer is measured on

Every score is on E_A or E_B: evaluation-side sentences, disjoint in identity groups from every training source, built from the closed vocabulary. Gate G1 requires that no evaluation reference equals a training output and that R-exact has zero hits. **A plain lookup of the generated pairs answers no evaluation item.**

What training and evaluation share is the vocabulary: the test is composition of known words into unseen sentences. The frozen student supplies word order and morphology; the store supplies per-word target information. This is lexical knowledge used by the student, not transfer of a skill. A word-level lookup can in principle do it, which is why E-table and the lexicon baselines are in the design. The share of evaluation items with a training source at word-level edit distance 1 (0.0816 in P10-S2's partition) is reported, and every score is also printed without those items; that figure enters no rule.

### 5.4 Addressing

**Oracle addressing, as ADR-0022 section 5.4.** The code of (task, word) is a fixed random unit vector from a seeded hash. The read is a flat scan with top-8; no tree, no index.

- Why not P10-S0's interface: A5-D was qualified on the byte backbone, on synthetic facts, with the answer position given. Using it here would test addressing and transfer at once.
- Load: 2,001 codes per task. M-append: 4,002 codes on 8,192 rows (0.49). M-seq: 4,002 on 4,096 (0.98). Both are below the two per row at which P10-S0 tested overload. Those loads are context, not evidence: another task and backbone.
- **The fixed line.** Every label, class, annotation, composition and cost line, table, caption, machine-readable record and terminal summary carries directly above it: **"oracle-assisted (word-level addresses supplied by rule); lexical translation of short closed-vocabulary sentences, two capabilities of one kind; frozen English student; teacher-only training material verified by measured-precision filter; not autonomous learned memory."** Every line also prints "(3 replicates, U = …)", and NOT CONVERGED AT U where section 7.1 says so. The analysis refuses to write a line without them.
- Learned addressing is not part of this specification; it would be a separately approved supplement after P10-I-S0.

### 5.5 General quality, and the combined tasks

**GEN** is measured as ADR-0022 sections 5.4 and 6.4 with rulings C-M6 and m9 and the addendum of 2026-11-16: a keyword router (A, B, none) trained with route labels; the 44 marker-like and 100 ordinary windows of section 4.1, one half of the weight each; both decision positions; for every M1 and stage-2 memory snapshot, and for D-seq as comparison. Route accuracy and false-trigger counts are printed beside it. Under the oracle route general text is bit-identical to the student and counts for nothing.

**C1 and C2** are as `ADR-0022-addendum-combined-tasks.md` sections 2 to 9, never trained on, scored under the oracle route on the stage-2 snapshots of M-append, M-ii, D-seq and D-append (both orders), M-joint, D-joint, M-sep and D-sep (twelve arm-cells per replicate), plus S0 and the ensemble. D-append is scored as D-seq is: its adapters apply at every position.

## 6. Seeds

Values are those of `docs/reviews/p10-i-direction-2026-11-17/SEED_REGISTRY.md` section 4.2, checked there against every literal and derived seed of P1 to P10 and the other P10-I drafts (`seed_registry_check_r3.py`, Revision 3). Gate G9 runs a copy of that checker that excludes this study's own files, as ADR-0029 section 19 ruling 6 did, with the copy's SHA-256 in the gate record, and checks this study's named values against the registry's allocation rows, before each freeze. Run unchanged, that checker reports FAIL once any P10-I study is implemented, because it counts a study's own config and tests as collisions with its own allocation (at `fc14159`: 34 problems, all P10-I-R's own seeds, none of this study's). The copy's substitutions are recorded with it.

**Data seeds, 250001–259999.**

| Use | Seeds |
|---|---|
| Registered replicates: bases 250001, 250101, 250201 | +1 training draw (overlapping design only); +2 batch order (a fresh generator also orders M-ii's replay); +4 permutation controls; +10 code hash; +13 router "none" prefixes and batch order |
| Partition side (Part Q) | 250901 partition; 250902 Q_fit; 250903 Q_check reserve order; 250904 source split; 250905 source block order; 250906 control subsample; 250907 GEN ordinary windows; 250908 teacher tokenizer and digest sentences; 250909 tokenization test (c); 250910 equivalence injection vector; 250911 C1 pairing; 250912 seen items; 250913 timing-benchmark items; 250914 regeneration subsample |
| Analysis | 250915 bootstrap intervals (descriptive) |
| Disjoint draws (rule 6) | 250916 permutation of A's pool; 250917 of B's (registry Revision 2, carried in Revision 3) |
| Route accuracy | 250918: the 200 WikiText-2 train pieces on which route accuracy on general text is measured (ADR-0022's lane-C ruling). Inside this study's allocated range 250901–250999; the registry's row names it at its next revision, before the Part Q freeze |
| Calibration | 251001 + 100·i, i = 0, 1, same offsets. A repeated calibration (section 7.1, rule 4): i = 2, 3 (251201, 251301) |
| Part T rehearsal | 252001, same offsets (i = 0 only) |
| Part Q rehearsal, partition side | 252901–252914, mirroring 250901–250914 (registry Revision 2, carried in Revision 3). Both Part Q rehearsals use them |

**Initialization seeds, 330201–330299.** Roles j: 0 stage-1 store; 1 appended rows; 2 M-joint store; 3 D1; 4 second adapter of D-append; 5 D-joint; 6 E-table; 7 router projection and keys. Registered replicate r (0, 1, 2): 330201 + 10r + j. Calibration draw i (0, 1): 330231 + 10i + j. A repeated calibration, draws 2 and 3: 330261 + j and 330271 + j (inside the allocation's spare 330261–330297; named in the registry before use). Rehearsal (both Part T rehearsals): 330251 + j. Test mode: 330298, 330299. **Unit tests:** 934001–934999.

Every generator is seeded directly by a listed seed through this study's own function, which records seed and purpose and refuses any other (P10-S2's function refuses seeds outside 220001–229999, `studies/p10s2/core.py:147–188`, and is not used for seeding); no seed is derived by hashing or arithmetic beyond the listed offsets.

## 7. Calibration, pilot and gates (before the Part T freeze; calibration seeds; D_cal only)

### 7.1 Calibration

1. **Rates.** Store and E-table: {0.001, 0.003, 0.01}. LoRA: {0.0001, 0.0003, 0.001} *(lead's choice: three values around ADR-0022's)*. Each is a stage 1 of 2,000 updates on each capability, calibration draw 0. **The rate grid is run at read layer L = 4** *(lead's choice: the first listed in ADR-0022 section 12.1)*. The rate with the higher mean chrF on D_cal over the two capabilities is taken; a difference below 0.01 goes to the smaller rate. The store's read layer L ∈ {4, 12} is then chosen the same way: the store at L = 12 at its chosen rate, against its L = 4 result; a difference below 0.01 goes to L = 4. E-table uses the store's chosen layer with its own rate. Every arm uses the rate of its module type (store rate: M1, M-append, M-seq, M-ii, M-joint; LoRA rate: D1, D-append, D-seq, D-joint). A rate whose training produces a non-finite loss is recorded DIVERGED and is not eligible; if every rate of a module type diverges, calibration stops and the work returns to the human lead.
2. **Training length.** With the chosen settings, M1 and D1 are trained on each capability on calibration draw 1 with snapshots at 1,000, 2,000, 4,000 and 8,000 updates. U is the smallest u in {1,000, 2,000, 4,000} such that, for both module types and both capabilities, chrF on D_cal at 2u exceeds chrF at u by less than 0.01 (any difference below 0.01, a decrease included, counts as converged; 0.01 is the lead's choice, the figure of the rate tie rule, read as a paired difference on the same 500 items). If none qualifies, U = 8,000 and every Part T line carries NOT CONVERGED AT U. One U serves every arm and stage. Convergence of the stage-2 arms, of E-table and of the joint arms is not checked; that is a stated limit.
3. Calibration scores are never reported as results.
4. **Cap and code identity.** Calibration and the pilot run under a stage cap of twice their time projected from the Part T measuring rehearsal, computed by code (section 10); a stop on it is PAUSED. Every calibration record carries the SHA-256 of each training and scoring file it ran (the Part T import walk of section 11, item 2). **No Part T training or scoring file changes after a calibration output exists.** The Part T freeze refuses calibration records whose hashes differ from the frozen files; stand-in records are refused. If a file must change (an audit finding, a rehearsal defect), the whole of calibration and the pilot are repeated on the spare registry seeds of section 6, and the earlier records are kept, marked SUPERSEDED and used for nothing. The repetition used is the one whose hashes equal the frozen files; it is never chosen on its values. One repetition is provided for; a second needs seeds entered in the registry first and a recorded decision of the lead.

### 7.2 Pilot gate

At the calibrated settings, on D_cal: if M1's gap closed is below 0.25 for either capability (0.25 is the edge of the acquisition negative zone, half the acquisition bar), Part T is **NOT STARTED: PILOT** and the work returns to the human lead. The pilot reads M1 of calibration draw 1 at the chosen U. An undefined D_cal gap gives NOT STARTED: PILOT (GAP UNDEFINED).

### 7.3 Gates

G1 partitions and zero R-exact hits; G2 repeat-scoring identity; G4 determinism on CPU, snapshot round trip, gradient reach (frozen rows, the frozen first adapter and the student receive no gradient), MPS against CPU on 20 updates; G5 route "none" bit-identical to the student, and gate isolation of appended rows; G6 addresses and routes take the prompt only; G7 frozen bytes; G8 student equivalence; G9 seeds. Definitions and tolerances as ADR-0022 section 12.3. A failed gate stops the run with ENGINEERING-FAILURE.

## 8. Rules that turn measurements into labels

### 8.1 Quantities, per cell

- s_c(X): mean chrF-norm of arm X on the full panel E_c (maximum over references per item).
- Gap closed: G_c(X) = (s_c(X) − s_c(S0)) / (s_c(teacher c) − s_c(S0)), on the full panel. Defined only if the denominator is ≥ 0.30.
- Control quantities (value-permuted, code-permuted, marker-only, words-only, and the arm's own G beside them) are computed on the 300-item subsample with the teacher and S0 scores of the same subsample. If the subsample's denominator is below 0.30, the cell's control conditions are undefined and the cell counts as a gap undefined.
- "First" and "second" are the capabilities in the cell's order. V1(X) is the stage-1 snapshot the arm continues: M1 for memory arms, D1 for dense arms, of the same cell.
- **Forgetting.** F(X) = s_first(V1) − s_first(X after stage 2). Retained share ρ(X) = G_first(X after stage 2) / G_first(V1). **ρ, F and RET are defined for an arm's cell only if G_first(V1(X)) ≥ 0.50;** otherwise that arm's cell is NOT EVALUABLE: FIRST NOT ACQUIRED.

### 8.2 Cell-level conditions

| Condition | Rule | Reason for the figures |
|---|---|---|
| ACQ1 | Full-panel G_first(M1) ≥ 0.50; on the subsample, G(M1) − max(G_value-permuted, G_code-permuted) ≥ 0.30 and G_marker-only ≤ 0.25 | Half the gap is the least that can be called acquisition; most of that half must come from the stored content at its addresses; the marker alone may carry at most half of the minimum |
| ACQ2(X) | G_second(X) ≥ 0.50 and ≥ 0.80 × G of the single-teacher module of the same type on that capability in the same replicate, which is M1 or D1 of the **other** order; for memory arms the same margin and marker-only limits on the second stage's controls | A second capability worth four fifths of what one teacher alone gives |
| RET(X) | F(X) ≤ 0.03 and ρ(X) ≥ 0.90 | 0.03 is about 2.5 times the 95% half-width of a 1,000-item panel mean (0.012 at a standard deviation of 0.2, ADR-0022 section 5.2); losing more than a tenth of what was acquired is not retention |
| Negative zones | Acquisition: G < 0.25. Retention: ρ < 0.70 | Half the acquisition bar; a loss of three tenths or more |
| Forgetting pressure | In at least 4 of the 6 cells: G_second(M-seq) ≥ 0.50 and ρ(M-seq) < 0.90 | A validity condition: the same module type, unprotected, loses more than a tenth while learning the second capability, in a majority of cells *(lead's choice)*. D-seq's ρ is printed beside it and does not count |

### 8.3 Lines (first match wins within a line; "every cell" means all six)

**Order of reading.** The study status of section 8.6 is read first. Under ENGINEERING-FAILURE, ENGINEERING STOP or INCOMPLETE no line is derived. The NOT EVALUABLE clauses below that name a missing, non-finite or recomputation-failed value are a second guard: no rule can turn such a value into a pass or into a measured failure.

**ACQUISITION**

| Order | Label | Rule |
|---|---|---|
| 1 | NOT EVALUABLE | A gap is undefined on E_A or E_B, or a cell it reads failed recomputation (section 8.6) |
| 2 | ACQUISITION-NEGATIVE (FIRST TEACHER / SECOND TEACHER) | G_first(M1) < 0.25 in every cell / G_second(M-append) < 0.25 in every cell. If both hold: "(FIRST TEACHER; SECOND TEACHER)" |
| 3 | ACQUISITION-INCONCLUSIVE: CONTROL-FAILED | A value or code permutation gives G ≥ 0.50 in any memory cell (M1, M-append, M-seq, M-ii, M-joint), as ADR-0022 section 11.3 row 5 |
| 4 | ACQUISITION-POSITIVE | ACQ1 and ACQ2(M-append) pass in every cell |
| 5 | ACQUISITION-INCONCLUSIVE | Otherwise; passing cells per order are printed |

**RETENTION.** Under every label the per-cell table of G_first(M1), ACQ1, G_second, F and ρ for M-append is printed, with the number of evaluable cells in the negative zone.

| Order | Label | Rule |
|---|---|---|
| 1 | NOT EVALUABLE: GAP UNDEFINED / RECOMPUTATION | A gap is undefined, or a cell the line reads failed recomputation |
| 2 | RETENTION-NEGATIVE: FORGETTING | At least four cells are evaluable for M-append, and ρ(M-append) < 0.70 in every evaluable cell |
| 3 | NOT EVALUABLE: FIRST NOT ACQUIRED | ACQ1 fails in any cell |
| 4 | RETENTION-INCONCLUSIVE: NOT CHALLENGED — SECOND NOT ACQUIRED | G_second(M-append) < 0.50 in any cell |
| 5 | RETENTION-INCONCLUSIVE: NOT CHALLENGED — NO FORGETTING PRESSURE | The forgetting-pressure condition does not hold |
| 6 | RETENTION-POSITIVE | RET(M-append) passes in every cell |
| 7 | RETENTION-INCONCLUSIVE | Otherwise |

A NOT EVALUABLE retention line is not read as negative and not as "no forgetting"; the table beneath it says what was seen.

**GENERAL-QUALITY.** PRESERVED if, for M-append's stage-2 snapshot in every cell, under both decision positions, the loss increase over the unmodified student is ≤ 0.02 nats per token (ADR-0022's revision-1 value). NOT PRESERVED if every reading is recorded and finite and one exceeds 0.02. NOT EVALUABLE if a reading is missing, non-finite or failed recomputation. The milestone line is then NOT ESTABLISHED (GENERAL QUALITY NOT EVALUABLE). A missing or non-finite GEN value is never NOT PRESERVED; where it comes from an error it is an engineering stop first (section 8.6). A pass is described as "the keyword router stayed silent".

**AGAINST-DENSE.** The primary pair is M-append against D-append, in every cell. Two quantities, each with its own label: ΔG = G_second(M-append) − G_second(D-append), and Δρ = ρ(M-append) − ρ(D-append).

- For each quantity: MEMORY AHEAD if Δ ≥ +0.05 in every cell; DENSE AHEAD if Δ ≤ −0.05 in every cell; NOT DISTINGUISHED if |Δ| < 0.05 in every cell; MIXED otherwise.
- **The value of the line is the pair, printed as "acquisition: {label}; retention: {label}".** The two are never merged into one word.
- **Guard.** Δρ is NOT EVALUABLE if, in any cell, either arm's ρ is undefined (section 8.1) or either arm has G_second < 0.50 (retention not challenged). An arm whose second stage learned nothing keeps ρ near 1 trivially and can never win on retention. The same guard applies to the M-seq against D-seq pair and to the annotation TASK-CODED SPARSE RETENTION.
- The reading is at matched updates. Printed with the line, always: the qualifier **"the memory receives the task identity by rule in its address; the dense arm receives it only through the prompt"**; the same pair of labels for M-seq against D-seq; D-sep's and M-sep's scores (retention BY CONSTRUCTION); the annotation NO ADVANTAGE OVER SEPARATE ADAPTERS by ADR-0022's rule; and the counted training multiply-adds per update of both arms (section 8.5).

**AGAINST-LOOKUP.** For each cell and capability, b is the best score among R-gloss, R-gloss-icl, R-nn, R-icl and E-table. LOOKUP SUFFICES if b ≥ s(M-append) − 0.03 on both capabilities in every cell. MEMORY ADDS OVER LOOKUP if s(M-append) − b ≥ 0.05 on both capabilities in every cell. MIXED otherwise. The baseline that gave b is named, with E-table's parameter count (about half the store's).

### 8.4 Milestone line

SUPPORTED (append-frozen) requires ACQUISITION-POSITIVE, RETENTION-POSITIVE and GENERAL-QUALITY PRESERVED. The suffix becomes "(append-frozen + consolidation)" if, in addition, MODIFICATION is RETAINS UNDER MODIFICATION and M-ii's snapshots pass the GEN check in every cell. If ACQUISITION and RETENTION are positive and GENERAL-QUALITY is NOT PRESERVED: WITHHELD — GENERAL QUALITY NOT PRESERVED UNDER A LEARNED ROUTE, printed with the router's false-trigger rate and the loss increase per cell. If GENERAL-QUALITY is NOT EVALUABLE: NOT ESTABLISHED (GENERAL QUALITY NOT EVALUABLE), never WITHHELD. Otherwise NOT ESTABLISHED. The suffix is not given if any GEN reading of M-ii is not evaluable. No result printed BY CONSTRUCTION satisfies any rule.

### 8.5 Descriptive lines (they enter no line of 8.3; only MODIFICATION touches the milestone suffix)

- **MODIFICATION (M-ii)**, first match: CONSOLIDATION-REJECTED (count printed) if any cell failed the D_con constraint; NOT EVALUABLE if fewer than four cells are evaluable for M-ii (section 8.1), or a cell it reads failed recomputation; FORGETS UNDER MODIFICATION if ρ < 0.70 in every evaluable cell (so it needs at least four evaluable cells, the registered number, and with none it is NOT EVALUABLE); RETENTION BY INERTIA if ACQ2 and RET pass in every cell and any cell is below the modification floor; RETAINS UNDER MODIFICATION if ACQ2 and RET pass in every cell; INTERMEDIATE otherwise. RET's reference is V1 = M1. In a CONSOLIDATION-REJECTED cell, M-ii's snapshot for every other reading is the pinned M-append snapshot, and it is marked as such.
- **COMPOSES C1 / C2**: the strengthened rule of the addendum, section 8, with its two fixed lines and the exact-match pass rate (section 9, and ruling m10).
- **Annotations** of ADR-0022 section 11.4 with the rulings of its addenda (printed if they hold in any replicate or order, with the mean), except TEACHER-EQUIVALENT-TO-GOLD. This includes ROUTER QUALIFIED / NOT QUALIFIED, APPEND COST, EXACT-MATCH WEAK, BELOW JOINT BOUND, BELOW ADAPTER JOINT and TASK-CODED SPARSE RETENTION. Seen-item and E_open scores are printed and enter nothing.
- **Cost.** The five measures of ADR-0022 section 10.2 are recorded: teacher inference per accepted item; student training (seconds, updates, rows, memory); footprint; active work as counts; the timing benchmark. Lines: FEWER VALUE ROWS ACTIVE and the stored-size arithmetic (ADR-0022 section 11.5). TRAINING COST COMPARABLE is not printed (section 3, row 20); training seconds are recorded without a comparison label. **Counted training multiply-adds per update:** at batch 32 and the mean training sequence length, one forward and one backward pass, counting each linear map as inputs × outputs per token and pass (twice in the backward pass where its weights are trainable), the key scan as rows × 16 per read and the value mix as 8 × 576 per read; computed by one function tested on hand cases. No count is reported as measured efficiency.

### 8.6 Study status and recomputation

- **PAUSED — IDENTITY:** a hash difference of a frozen input file found when a task starts (section 11, item 2). A state, not an outcome; the stage resumes once the file is restored bit for bit.
- ENGINEERING-FAILURE: a failed gate on study-produced data (as section 11, item 2 distinguishes); the oracle-routed ensemble's score differing from the teacher's own. No line is derived.
- **ENGINEERING STOP.** A code or environment error inside a block, cell or item stops its stage. While any such error is recorded, the analysis refuses: ENGINEERING STOP — ITEM ERRORS. It is never NOT EVALUABLE or INCOMPLETE. In Part Q, a step stopped by such an error before any value of Q1–Q4 has been computed resumes from its last completed block once the cause is recorded, as ADR-0022's ruling R16 allowed. After that point a second attempt is the human lead's decision. A non-finite value in a registered record (a loss, a score, a GEN reading) is treated the same way: ENGINEERING STOP — NON-FINITE VALUE; it is never a scientific label. An environment error (out of memory, file system) propagates and is never recorded as a failed gate. In Part T a stopped cell resumes from its last checkpoint once the cause is recorded and the fix changes no frozen file; a fix that changes a frozen file ends the attempt, and a second attempt is the human lead's decision.
- INCOMPLETE: a registered record is missing after the run has ended and no error is recorded for it. No line is derived and no denominator is reduced.
- PAUSED is a state; its terminal label, if the stage is not resumed, is that of section 4.4.
- **Recomputation**, as ADR-0022 section 13.3 and rulings B-M9 and C-M3: no result is reported before every registered score is recomputed on CPU from the snapshots. With the frozen scoring code every score must be bit-identical; with the auditor's own code every greedy sequence must be identical and every item score within 1e-6. **A cell beyond tolerance is an engineering stop, not a scientific NOT EVALUABLE: ENGINEERING STOP — RECOMPUTATION.** No line, condition or annotation is derived or reported while it stands; both values and the cell are recorded. This resolves the earlier conflict between "NOT EVALUABLE: RECOMPUTATION" and ENGINEERING-FAILURE in favour of the stop (the third review's F9, reading (i), as ADR-0029 ruling 11). The "failed recomputation" clauses of sections 8.3 and 8.5 stay as the second guard only: such a cell never counts as passing or as in a negative zone. What follows a stop (finding the cause; a further recomputation) is recorded; a re-run of any registered cell is the human lead's decision. Verdicts are compared as verdicts.

## 9. Limits (DIRECTION.md section 5)

| Limit | Kind | Rule |
|---|---|---|
| Part Q and Part T charged hours, per stage: charged + 2 × projected remaining, computed by code from the part's measuring rehearsal and stated in its Decision 2 record. The measuring rehearsals have fixed caps (section 10); calibration has its own (section 7.1) | Resource cap | PAUSED and resumable. Extended on cost projections only, never on an outcome value; every planned block and cell still runs |
| Memory guard: 12 GiB per worker in Part Q; 8 GiB per worker and 24 GiB aggregate in Part T. New disk: 10 GiB | Resource cap | PAUSED; raised only on measured use. Resume checkpoints of a training cell are deleted once its final snapshot is recorded; the durable copy of section 11, item 1 is not counted against the 10 GiB. |
| Generation sources; Q_check items; the 24,000 disjoint target | Design ceiling | Generate until met (section 4.3); ceilings are the split pools and the reserve; OVERLAPPING DRAWS by rule if the target is missed |
| Training length U | Design ceiling | Convergence rule; top rung 8,000, then NOT CONVERGED AT U |
| Q_fit 2,000; replicates 3; rows per stage; vocabulary; panel sizes; the 4/5 split; the batch layout of generation | Design, fixed | Fixed by this text; not extended and not changed by any rehearsal |
| Q1–Q4, the 0.60 cut, the 150 minimum | Scientific threshold | Never relaxed. Neither Q_fit nor Q_check is extended after a quality value is read |
| ACQ, RET, negative zones, forgetting pressure, four evaluable cells, 0.05 and 0.03 margins, GEN 0.02 nats, pilot 0.25, COMPOSES 0.80 and 0.50, M-ii's 0.02 and 0.10 | Scientific threshold | Never relaxed |

No limit is extended because a partial result looks close.

## 10. Stages, machine load, order of work

The machine is also the human lead's working computer. **No registered label reads wall time.** Load is measured at each stage, not assumed: the 1-minute load average is recorded at the start and end of every stage.

| # | Stage | Device | Quiet machine | Human gate before it |
|---|---|---|---|---|
| 1 | Implementation of both parts and tests on synthetic stand-ins; independent implementation audit | CPU | no | Decision 1 (section 17) |
| 2 | Part Q: candidate plan; measuring rehearsal; caps by code; counting rehearsal against that exact plan file (below) | CPU, six threads | no | Decision 1; the durable copy (section 11, item 1) |
| 3 | Part Q freeze; registered Part Q; independent recomputation | CPU | no | **Decision 2 of Part Q**; then acceptance of the outcome as registered |
| 4 | Part T measuring rehearsal; then calibration, convergence rule, pilot, under the calibration cap | MPS training, CPU scoring | no | Decision 1; Part Q accepted as TEACHERS-QUALIFIED |
| 5 | Part T: candidate plan; caps by code; counting rehearsal against that exact plan file; re-audit of any changed code | both | no | — |
| 6 | Part T freeze; registered run: gates, training, evaluation, analysis, report | both | no | **Decision 2 of Part T** |
| 7 | Timing benchmark | CPU, six threads | **alone** (below) | none; the rule below |
| 8 | Independent recomputation; outcome record | CPU | no | — |

"Decision 1" is the approval of this specification for implementation and rehearsal, as in ADR-0029 (the third draft used the name for the decision to run Part Q; that is now Decision 2 of Part Q). Neither Decision 2 is given by this text (section 17).

**The pattern, applied to Part Q and to Part T separately** (ADR-0029 sections 13 and 18–20):

1. **Candidate plan.** `freeze/partq_plan.json` and `freeze/partt_plan.json` list every block, cell, item, label, path and manifest of the part's registered stages. Every stage derives its blocks, cells and items from its plan file only. Part T's candidate plan is written after calibration, because it holds U, the rates and the read layer.
2. **Measuring rehearsal**, under a fixed cap stated here *(lead's choice)*: **3.0 charged hours for Part Q, 3.0 for Part T**. A stop on it is PAUSED and the figure may be raised once, to twice, by the lead on its own partial timings. It measures seconds per unit of every kind, peak memory per worker and disk use, and records the machine's load (the 1-minute load average and the other studies' processes alive) with every figure. It cannot be frozen on.
3. **Caps by code:** for every registered stage, charged + 2 × projected remaining, from the measuring rehearsal's rates and the plan's counts. Part Q's projection assumes both split pools are generated to the end and the whole Q_check reserve is drawn.
4. **Counting rehearsal against that exact file,** under those caps: the candidate plan file itself; its SHA-256 goes into the rehearsal record, and the freeze refuses a plan with any other hash. Tasks, items, labels, paths and manifests are enumerated from it; the analysis and the report run on a synthetic registry keyed by its labels (section 11, item 8); the rehearsal subset below is executed, with one forced pause and resume and one forced PAUSED — IDENTITY and restore.
5. **Freeze,** then the part's Decision 2, taken on the counting rehearsal's record and the independent implementation audit. A code change after the counting rehearsal means the counting rehearsal is repeated; for Part T it also means calibration is repeated (section 7.1, rule 4).

**Part T measuring rehearsal.** It needs real material, so it runs after Part Q's outcome is accepted, on Part Q's registered bank and accepted pools, with the rehearsal seeds of section 6 and D_cal only: 200 updates of every trained cell type on MPS, 20 scoring items of each kind on CPU, the combined scoring of one arm of each kind, the router's training, the gates on rehearsal data, and the timing benchmark's duration. Its scores are sealed and not displayed. Before Part Q exists, Part T runs on synthetic stand-ins only; P10-S2's bundle is not trained on *(the conservative reading of the third review's open point G21: a rehearsal on it would show whether the student learns from teacher output)*.

**Timing benchmark (stage 7).** It is descriptive: no wall-time comparison and no label is registered on it. **It runs alone:** it is opened only when no process of this or any other study is alive on the machine, and that is checked again with the quiet condition before each repetition. As ADR-0022 section 10.2: one process, 200 items per panel, three repetitions, median; timed arms S0, M-append, D-append, D-seq, E-table and R-icl *(lead's choice; ADR-0022 does not list them)*. The quiet condition is read **before** each repetition starts, never at its end, because the benchmark's own six threads raise the load: the 1-minute load average must be at most 2.0 after at least 60 seconds with no study process running. Reason for 2.0: at most two busy cores of the machine's 18 besides the benchmark's six, so each benchmark thread has a core. The 30-minute bound applies to each repetition's start, counted from the opening of the attempt. If a repetition cannot start within it, the attempt ends, its completed repetitions are kept and marked INCOMPLETE ATTEMPT, and the stage is rescheduled. The first attempt with three completed repetitions is the record; no attempt is chosen on its figures. After five attempts without one, the lead records the decision **NOT MEASURED** and the stage is closed. Every wait is bounded. The load measured before and after each repetition is printed with every figure; a set of repetitions whose coefficient of variation exceeds 5% is marked UNSTABLE. Duration: minutes, an estimate measured in the Part T rehearsal.

**Part Q rehearsals, sealed.** Both run on the rehearsal partition seeds with the real teachers. The measuring rehearsal runs steps 1 to 8 with one generation block per capability and one Q_check block, and reports the supply counts of section 4.1. The counting rehearsal runs the candidate plan file itself end to end (its SHA-256 goes into the rehearsal record, and the freeze refuses a plan with any other hash), limited to two generation blocks per capability and one Q_check block, with one forced pause and resume; it may reuse the measuring rehearsal's completed blocks, which the same seeds and layout make identical. They report timings, memory, counts and yields. The values of Q1 to Q4 and every per-item score go to a sealed file and are not displayed or read before Part Q's outcome is registered. The chosen filter setting and the yields are visible and are informative about Q_fit precision; that is harmless because no Part Q setting, threshold or size changes after the rehearsal. The rehearsal partition is a different split of the same corpus, so its sealed per-item teacher and student scores include sentences that are evaluation-side in the registered partition; they are sealed, never displayed and never read by Part T. Their time is charged to Part Q and counts in its caps.

Training on MPS is not bit-reproducible; snapshots are the object and every score is recomputed on CPU.

## 11. Engineering requirements carried from P10

1. **Durable data, first.** The P10-S2 data sit git-ignored in an agent worktree that may be cleaned: `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a91c79a181109bb9c/data/p10s2-pre-20261115/`. Before any worktree clean-up, and before Part Q's implementation reads a byte of it, **the lead copies it to `/Users/daniellaloush/dandush03/ArborLM/data/p10s2-pre-20261115/`** (the main checkout's git-ignored data folder) and verifies every downloaded file's SHA-256 against the download ledger (`docs/reviews/p10-design-2026-11-15/DOWNLOAD_LEDGER.md`) and `studies/p10s2/records/tatoeba_session.json`. The copy and its verification are recorded (date, file count, bytes, the list of hashes). Part Q reads the durable copy only. The installed package directory `data/datagen-packages/` of the same worktree (4,270 files, 126,182,132 bytes) is copied beside it, to `/Users/daniellaloush/dandush03/ArborLM/data/datagen-packages/`, and compared file by file with the source; if it cannot be verified it is not used and the question returns to the human lead, because a fresh installation would be a download of packages outside the lock. The Tatoeba exports cannot be fetched again byte for byte (section 12). WikiText-2 is not in this worktree; its path is checked before any step that reads it (P10-S2 attempt 2).
2. **Frozen inputs, stated exactly, one set per part, completed from an import walk.** Identity is by SHA-256 of each listed file. The text of this ADR is outside both sets: each freeze record stores its hash for provenance only, and a test asserts that every threshold in this ADR equals the config's value. The check compares hashes of the listed files; it does not require a particular HEAD.
   - **Part Q:** `studies/p10is2/partq/**`; `studies/p10is2/common/**`; `configs/p10is2_partq.toml`; `uv.lock` and `pyproject.toml`; the requirements file (section 12) and the manifest of the installed package set (names, versions and the hash of every installed file, as ADR-0022's ruling R2); the launch scripts; the stage caps; the hashes of every input (the downloads, WikiText-2); the shared panel ledger as it stands at the freeze; the candidate plan `freeze/partq_plan.json`.
   - **Part T:** `studies/p10is2/**` outside `partq/` (`common/` included); `configs/p10is2_partt.toml`; `uv.lock` and `pyproject.toml`; the launch scripts; the stage caps; the Part Q manifest; the shared panel ledger (ADR-0026 freezes it by SHA-256); the calibration records (section 7.1, rule 4); the candidate plan `freeze/partt_plan.json`.
   - **The import walk.** At each freeze a script walks the imports of the part's entry points (launch scripts and every stage module) and lists every repository file reached. Every such file outside `studies/p10is2/` joins that part's set by file and hash: any `studies/p10s2/*.py` that is reused and what it imports, and `src/arborlm/*` (P10-S2's modules import `src/arborlm/io.py`). The freeze refuses if the walk reaches a file the set does not list. Imported P10-S2 code is listed by file and hash; seeding goes through this study's own function. Part Q's code imports from the rest of the package only through `common/`, so a change of Part T code outside `common/` cannot invalidate a Part Q resume or recomputation; a change inside `common/` after the Part Q freeze is refused by Part Q's check, and Part T takes a copy under a new name if it needs one.
   - **Identity differences.** A hash difference of a frozen input file found when a task starts stops the task as PAUSED — IDENTITY. Restoring the file bit for bit lets the stage resume; completed blocks and cells are kept. ENGINEERING-FAILURE stays for differences in what the study produced: a teacher digest or regeneration difference, the ensemble check, a failed gate. A refused worker is recorded PAUSED — IDENTITY, never FAILED.
3. **Run-time notes** go to the chat or another branch. Nothing is committed or written in the run worktree's frozen files between a Decision 2 and the end of that stage's report. The study runs in its own worktree, never in another study's (section 20).
4. **Resumable stages.** Each completed block or cell is recorded atomically. A PAUSED stage continues and completed work is not recomputed. A training cell checkpoints every 500 updates with optimizer and generator state; a resumed cell is marked.
5. **Rehearsal against the candidate plan file itself; its SHA-256 goes into the rehearsal record, and the freeze refuses a plan with any other hash.** Each part has a measuring rehearsal, with a fixed cap stated here (section 10), after which its caps are computed by code; then a counting rehearsal under those caps. Every stage derives its blocks, cells and items from its plan file only. The counting rehearsal covers every registered stage of the part before its Decision 2. For Part T: every cell type, one cell of each trained type at full U, one combined scoring of each arm kind, one forced pause and resume.
6. **Every reading rule is in section 8**, including how cells combine. A rule the analysis needs and section 8 lacks stops the work before the freeze and returns to the human lead.
7. **Reference arm through every validity check.** In the Part T rehearsal, on calibration data, E-table (whose dependence on its vectors is given by construction) is run through the lexical-margin and marker-only conditions, and the evaluable-cell rule, the Δρ guard and the forgetting-pressure reading are exercised on M-seq and D-seq. A check the reference fails is not used; the specification returns to the human lead before the freeze.
8. **Analysis on a synthetic registry with known answers,** covering every label of sections 4.4 and 8.3 to 8.5, every status, cells that are not evaluable, not challenged or failed in recomputation, undefined gaps, rejected consolidations, non-finite values, recorded item errors (the analysis must refuse), a recomputation difference (it must refuse) and every descriptive table, each against a hand-computed expectation.
9. **Fail fast.** Every fixed-input count is checked before any teacher runs (attempt 4); the applied generation configuration is asserted (attempt 5).
10. **Platform of record:** this machine (macOS on Apple silicon, torch 2.8.0 from the lock), CPU for all scoring, at six threads with deterministic algorithms on, as `studies/p10s2/stages.py` sets them, recorded with every score. Bit-exact assertions are made on it, under those settings, only. `ruff`, `mypy` and `pytest` run locally; GitHub CI is not relied on.

## 12. Downloads, packages and services

No paid service, account, login or cloud use is needed.

| Item | Size | State | Needs |
|---|---|---|---|
| Teachers A and B, student, Tatoeba exports | 936,320,520 bytes (29 files) | On disk at `.claude/worktrees/agent-a91c79a181109bb9c/data/p10s2-pre-20261115/downloads/`; hashes in `docs/reviews/p10-design-2026-11-15/DOWNLOAD_LEDGER.md` and `studies/p10s2/records/tatoeba_session.json`. Not re-hashed for this text | The durable copy (section 11, item 1), verified before Part Q's implementation reads it |
| Data-generation packages outside the lock (28 hash-pinned packages: 8 named, 20 transitive) | 126,182,132 bytes | On disk in the same worktree, `data/datagen-packages/` | Their use in Part Q only: section 13, item 6. No download. The earlier approval was for P10-S2's data step |
| WikiText-2 | — | In the main checkout's `data/wikitext2/` and in the agent worktree | Path check |
| Fallback teacher and Spanish Tatoeba files | 315.3 MB + 8.1 MB | **Not on disk** | The human lead's decision to invoke the fallback; the download is within the 50 GB delegation |

**One statement on downloads.** Downloads for P10-I need no per-item approval within the human lead's delegation of 2026-11-17 ("proceed with the download as long as it's lower of 50gb you dont have to ask permissions"). **None is expected: everything this study needs is on disk.** The fallback's files (323.4 MB) would fall under the delegation if the fallback were ever invoked; it is not invoked by this study (section 4.4). The ledger's running total is 1,188,183,868 bytes. Downloads for P10-I fall under the human lead's delegation of 2026-11-17 (under 50 GB in total, no per-item approval). It covers no package outside the lock (`DELEGATION_2026-11-18.md` section 3); the packages above are already on disk, so their use, not a download, is the question, and section 13, item 6 answers it. Any download would be recorded in the ledger before it starts. The Tatoeba exports carry no revision and are regenerated weekly: a lost copy cannot be fetched again byte for byte.

## 13. The open choices, and how each stands

The third draft reserved these for the human lead. Under his delegation of 2026-11-18 (section 17) the lead takes each at the option the draft recommended, unless stated otherwise below. Items 2 (the fallback) and 7 stay with the human lead.

1. **Part Q as a separate registered stage,** accepted before Part T is frozen. Taken: yes.
2. **One teacher qualifies.** Taken: Part T does not run and the Part Q label is registered (section 4.4). **The fallback is not invoked under the delegation;** whether a fallback study follows is the human lead's decision afterwards. The one-teacher ACQUISITION-only lane is not taken: it does not answer the milestone question.
3. **Kept from the human lead's P10 list as descriptive lines:** M-ii, the combined tasks, the five cost measures. Removed: TRAINING COST COMPARABLE and MA-gold. Taken as drafted; the human lead may still remove M-ii or the combined tasks to save cost before the Part T freeze (section 14).
4. **Oracle addressing only; three replicates, both orders, "every cell" rules.** Taken. Even at a per-cell pass rate of 0.8, six of six has probability of about 0.26 if cells were independent (the two orders of a replicate are not); INCONCLUSIVE should be expected often.
5. **Who may extend an hour cap.** Taken: the lead, once, to at most twice its value, on recorded cost projections; beyond that, the human lead.
6. **Packages outside the lock, and the durable location.**
   - **What is taken, and only this:** the *use*, with **no download** and **no change to `uv.lock` or `pyproject.toml`**, of the 28 hash-pinned packages already installed (126,182,132 bytes; 8 named, 20 transitive) at `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a91c79a181109bb9c/data/datagen-packages/`, used from the verified durable copy of section 11, item 1. Their requirements file is `studies/p10s2/requirements-datagen.txt`, SHA-256 `d549380e67b220945d183a159a2cc2a85c2c982947367c70fd411038769e8867`: the set the human lead approved for P10-S2's data step.
   - **Mechanism:** the one P10-S2 used (`studies/p10s2/launch/datagen.sh`): the installed directory on the `PYTHONPATH` of the data-generation process only, under `uv run --locked --offline`. `uv run --locked --with-requirements` on that file is allowed only with `--offline`, when it resolves from the local cache. A process that would fetch anything is refused.
   - **Scope:** Part Q's teacher and tokenizer work only: generation, Q_fit and Q_check, the panel outputs with the token bank and the conversion and equivalence records of step 1, the GEN-window tokenization, the two Part Q rehearsals, and the regeneration check of the independent recomputation. **Part T uses the lock alone.** No other package, and nothing in any other study.
   - **Authority, stated as it is.** The third reviewer advised leaving this with the human lead, because `DELEGATION_2026-11-18.md` section 3 keeps "any package outside the lock" with him. The lead takes it under the human lead's widened delegation of 2026-11-18, "and you have my permission to auto approve everything until you complete P10-I" (section 17), and **reports it to the human lead as the first item of this study's record.** No package outside the lock is put on any process's path before that sentence is in the committed delegation record.
   - **Durable location:** named by the lead, section 11, item 1.
   - **Downloads:** section 12; none is expected.
7. **Lane D (P9, H17-INC) and ADR-0020 section 12.2 (sequential addition of facts),** carried to this study as candidates by the closure ledger (its section 10, item 3). **Not taken up in this study, and not decided here: left with the human lead, as the closure ledger reserves them.** RETENTION here is of a lexical capability under oracle task codes, not of a first set of facts under learned addressing, and section 12.2's conditions (ρ against the oracle reference A6, set-A clusters, schedule restarts) do not apply to this design.
8. **The timing benchmark.** Taken: descriptive only; it runs alone, by the rule of section 10; NOT MEASURED by a recorded decision after five rescheduled attempts. No wall-time comparison is registered.
9. **Independence from P10-I-S0 and S1.** Taken: this study uses no result of either.

Design choices made by the lead, open to the human lead's veto before the Part Q freeze (reasons in sections 3 to 5 and 8): Q_fit fixed at 2,000 and the Q_check reserve of 16 blocks, both chosen knowing P10-S2's data and disclosed; Q_fit, Q_check, D_cal, D_con and E_C from both-reference sentences; the registered 4/5 split and the 24,000 target with OVERLAPPING DRAWS as the fallback by rule; forgetting pressure read on M-seq only; R-gloss-icl and its template; the rate grid at L = 4; the caps of the measuring rehearsals.

## 14. Cost projection — an estimate, to be replaced by the rehearsals

**Part Q.** Measured in P10-S2 at the default thread count (18 cores): 12.3 ms per source for teacher A and 14.1 ms for B; both teachers on the 1,000 items of Q (2,000 translations) in 26 s. At six threads generation may be two to three times slower.

| Scenario | Sources A / B | Generation at P10-S2's rate | At six threads (estimate) |
|---|---|---|---|
| Minimum pools (10,000) | 77,000 / 256,000 | about 1.3 h | 2.5–3.8 h |
| Disjoint target (24,000), if reachable | 185,000 / 615,000 | about 3.0 h | 6.1–9.1 h |
| Both split pools to the end | 198,500 / 650,100 | about 3.2 h | 6.4–9.7 h |

The Part Q rehearsal measures seconds per source at six threads, yield, peak memory, disk use and the time of a pause and resume.

**Part T (no student has been trained on this machine).** One measured anchor: 2,000 greedy answers of the untrained student (two per Q item) took 178 s in P10-S2's data step, about 0.089 s each. Training rates are ADR-0022 section 13.3's operation-count projections, uncertain by about a factor of three.

| Work | Basis | At U = 2,000 |
|---|---|---|
| Training: 42 store-type and 24 LoRA units of U over three replicates (M-ii is 12 of the 42) | 5–10 and 8–15 min per unit of 2,000 | 7–13 h |
| Calibration and ladder: 36 units of 2,000 (22 store-type, 14 LoRA) | same | 4–7 h |
| Scoring: 54 trained cells on both panels; controls, routers, GEN, retrieval | 1.6–5.2 min per cell for the panels; ADR-0022's 0.9–3.0 h per replicate for the rest | 4–14 h |
| Combined tasks, three replicates, twelve arm-cells | the addendum's 2.0–7.8 min per arm-cell | 1.2–4.9 h |
| Independent recomputation (one repetition of all scoring) | same | 5–19 h |
| **Total, order of magnitude** | | **about 21–57 h** |

Training scales with U: at U = 8,000 the training row is 27–52 h and the total about 41–96 h. Not included: the Part T rehearsal, the gates stages and router training. The Part T rehearsal measures seconds per update of every cell type on MPS, scoring seconds per item of every kind, peak resident and MPS memory, and the gates, analysis and report times.

## 15. Stop rules and NOT EVALUABLE outcomes

- A failed gate on study-produced data stops the run: ENGINEERING-FAILURE. A second attempt needs the human lead's decision. Failed runs and failed checker attempts are kept.
- A hash difference of a frozen input file is PAUSED — IDENTITY and resumes on restore (section 11, item 2). A code or environment error, a non-finite value or a recomputation difference is an engineering stop and never a scientific label (section 8.6).
- A resource cap stops a stage as PAUSED; it resumes after the cap is extended under section 9, or ends with the terminal label of section 4.4 by the human lead's decision.
- Part T is NOT STARTED if Part Q does not end TEACHERS-QUALIFIED, or on the pilot gate.
- NOT EVALUABLE lines are those of sections 8.3 and 8.5. None is read as negative, and each prints the per-cell values behind it.
- Nothing is re-run with changed settings. No result is reported before the recomputation is complete.

## 16. What this study cannot establish

- Anything about learned addressing, routing or overload; a GEN pass means the keyword router stayed silent.
- That the memory is more than a dictionary, unless AGAINST-LOOKUP says so, and then only for lexical translation of short sentences from a 2,000-word vocabulary. Not transfer of a skill.
- **Retention on a task where the unprotected store does not forget.** If M-seq does not forget, RETENTION cannot be positive: it is INCONCLUSIVE: NOT CHALLENGED, which is neither retention nor its absence, and the milestone is NOT ESTABLISHED.
- That retention is an advantage of sparsity or of the memory: tasks touch different rows because their oracle codes differ, M-append's first-stage rows are frozen by design, and separate modules behind a switch retain by construction.
- Superiority over adapters: the store is given the task by rule and LoRA is not.
- Continual learning in general (two teachers, two stages, two capabilities of one kind, one student); knowledge fusion or composition.
- That each training item was correct: the filter has a measured precision.
- Efficiency, latency, storage, capacity scaling, anything about SSD. Counts are not measured efficiency.
- Large teachers or students; a success probability; a failure of the ArborLM concept, whatever the outcome.

## 17. Approval record — Decision 1 (2026-11-18 UTC)

**Review trail.** Three independent reviews by the `arbor-auditor` subagent (Opus 5.5): the first and the second NOT READY; the third (`REVIEW3_ADR-0025.md`) NOT READY with no blocking finding, solely because several items needed a choice by the lead. Those choices are now made (sections 13 and 19), and that review's edits E1–E15 and findings F1–F16 are applied (section 18). **The text with the edits applied has not been reviewed again.**

**The decision.** Decision 1 is taken by the lead (Claude Fable 5.2) under the human lead's delegation of 2026-11-18. His words, verbatim:

> once its done can you accept the results as they come and continue with the next simulations until you conclude P10-I-*

> and you have my permission to auto approve everything until you complete P10-I

The first sentence and the lead's reading of it are in `docs/reviews/p10-i-direction-2026-11-17/DELEGATION_2026-11-18.md` (sections 1 and 2; item 2 names approval for implementation and rehearsal, at the options the drafts recommend unless an independent review says otherwise, and section 3 requires a draft judged NOT READY to be revised first, which this text does). The second sentence is **not yet in that committed record**; the lead adds it there, with his reading, before any Decision 2 and before the package use of section 13, item 6. Decision 1 itself rests on the first.

**What this approves.** Implementation of Part Q and Part T in new files (`studies/p10is2/`, `configs/p10is2_partq.toml`, `configs/p10is2_partt.toml`, `tests/test_p10is2_*.py`), their independent implementation audit, the measuring and counting rehearsals of both parts, and calibration with the pilot, as sections 7, 10 and 11 define them. **Nothing registered.** The items of section 13 stand as written there, the rulings of section 19 with them.

**What it does not cover.**

- Each freeze and each registered run: Decision 2 of Part Q and Decision 2 of Part T are separate recorded decisions, each taken on its counting rehearsal's record and an independent audit of the code.
- The fallback teacher, and any fallback study.
- Any change of a threshold, label, seed or rule. An amendment is recorded and, after a freeze, is the human lead's.
- Any download beyond the 50 GB delegation of 2026-11-17 (none is expected).
- Any package beyond the 28 named in section 13, item 6, any use of those outside Part Q, and any change to `uv.lock` or `pyproject.toml`.
- Lane D and ADR-0020 section 12.2; merges to `main`, publication, weights, paid services; any change to P10-S2 or another completed study.

The human lead can withdraw or narrow the delegation at any time. `Astra review: NOT_PERFORMED`. Claude review is not Astra review. Nothing here is a result or a success claim.

## 18. Review record

All three reviews are by the `arbor-auditor` subagent (Opus 5.5): `docs/reviews/p10-i-spec-reviews-2026-11-17/REVIEW_ADR-0025.md`, `REVIEW2_ADR-0025.md` and `REVIEW3_ADR-0025.md`, each NOT READY (the third with no blocking finding). All revisions are by the lead (Claude Fable 5.2). The edits of the third review are applied below and the text with them applied has not been reviewed again. The reviews are not Astra validation and not human approval.

**First review** (confirmed by the second, which judged B1, B2, R1–R3, R5–R9, R11–R18 and the advisories FIXED or ANSWERED, and R4, R10 and A9 as needing the changes below).

| Findings | Disposition | Where |
|---|---|---|
| B1 (M-ii, combined tasks, cost), B2 (general quality) | FIXED | §1, §3, §5.2, §5.5, §8.4, §8.5 |
| R1–R3, R5–R8, R16–R18 (Part Q) | FIXED | §4 |
| R9–R13 (reading rules, fairness, oracle wording) | FIXED | §5.2, §5.4, §8 |
| R14, R15 (sealed rehearsal; out-of-lock packages) | FIXED | §10, §12 |
| A1, A3–A8, A10 | FIXED | §2, §4.4, §5.2, §6, §7.1, §8.5, §11, §12 |
| A2 (one-teacher lane) | ANSWERED: offered, not recommended | §13 item 2 |

**Second review.**

| Finding | Severity | Disposition | Where |
|---|---|---|---|
| N1 pool overlap (also R4) | REQUIRED | FIXED: measured overlap of about 669,900; projection corrected; both teachers near the target | §2, §3 row 6, §4.3, §14 |
| N2 guard on Δρ (also R10) | REQUIRED | FIXED | §8.3 |
| N3 value of AGAINST-DENSE | REQUIRED | FIXED | §1, §8.3 |
| N4 seven unlisted changes | REQUIRED | FIXED: rows 15, 16, 17 and 21 added, pilot rename in row 12; words-only, CONTROL-FAILED scope, ensemble check, sacrebleu and unscored intermediate snapshots reverted to ADR-0022 | §3, §4.1, §5.1, §5.2, §8.3, §8.6 |
| N5 timing benchmark (also A9) | REQUIRED | FIXED | §10 |
| N6 recomputation failure in "every cell" rules | REQUIRED | FIXED | §8.3, §8.6 |
| N7 terminal label of a paused stage | REQUIRED | FIXED | §4.4, §15 |
| N8 regeneration tolerance | REQUIRED | FIXED | §4.4 |
| N9 Lane D, ADR-0020 §12.2, word count | REQUIRED | FIXED: the first two declined with a reason and reserved; the word count defined | §4.2, §13 item 7 |
| N10 construction of disjoint draws | REQUIRED | FIXED | §4.3 rule 6, §6 |
| N11–N13 | ADVISORY | FIXED | §5.4, §8.1, §8.5, §10, §12, §13 item 4 |
| Cross-references: seed registry, panel ledger | — | FIXED | §4.1, §6 |
| Section 16: RETENTION and M-seq | — | FIXED | §16 |

**Third review** (`REVIEW3_ADR-0025.md`; object: the third draft, 515 lines, SHA-256 `1ab20f0ca234d10b3051be780c3b6185d6d9b0667a6363e22a6c354cceaae325`).

| Finding | Severity | Disposition | Where |
|---|---|---|---|
| F1 identity failures terminal | REQUIRED | FIXED: PAUSED — IDENTITY, resume on restore (E13) | §4.4, §8.6, §11 item 2, §15 |
| F2 code and environment errors; R16 | REQUIRED | FIXED: engineering stop, the analysis refuses; R16 kept, narrowed (E14); non-finite values added by the lead | §3 row 28, §8.6, §15 |
| F3 rehearsal order, candidate plan, caps | REQUIRED (lead's choice) | FIXED: ADR-0029's pattern for each part; measuring caps 3.0 h each | §9, §10, §11 item 5 |
| F4 calibration cap and code identity; rate-grid layer | REQUIRED (lead's choice) | FIXED: cap by rule; no code change after calibration output, else repetition on spare seeds; L = 4 | §6, §7.1 |
| F5 panel population | REQUIRED | FIXED as "as in P10-S2" (E12); measured populations and the supply to count stated | §4.1 |
| F6 unlisted changes | REQUIRED | FIXED: rows 25–29 (E1); the ACQUISITION row order reverted to ADR-0022 | §3, §4.3, §8.3 |
| F7 GENERAL-QUALITY NOT EVALUABLE | REQUIRED | FIXED (E8) | §8.3, §8.4 |
| F8 MODIFICATION vacuous | REQUIRED | FIXED (E9) | §8.5 |
| F9 recomputation precedence | REQUIRED (lead's choice) | FIXED: reading (i), the engineering stop | §8.3, §8.6 |
| F10 download text | REQUIRED | FIXED: one statement (E2–E4) | §3 row 21, §4.4, §12, §13 item 6 |
| F11 gate G9 and seed text | REQUIRED | FIXED (E6) | §6 |
| F12 batch layout | REQUIRED | FIXED (E10), with whole-batch counts, tolerance and consequence | §4.3 rule 9, §4.4 |
| F13 gloss tokens for Part T | REQUIRED | FIXED (E11); template stated | §4.1 step 8, §5.2 |
| F14 shared panel ledger | REQUIRED | FIXED (E7); overlap and span defined | §4.1 |
| F15 frozen-input sets | REQUIRED | FIXED: lists and the import-walk rule; own seed function | §6, §11 item 2 |
| F16 A1–A9 | ADVISORY | FIXED (E15 for A1, A2). A7: the length is now above 515 lines; no rule was cut | §4.2, §4.3, §7, §8.3, §10 |
| G1–G22 implementer's guesses | — | RULED | §19 |
| §4 packages | — | ANSWERED: the smallest request, taken by the lead under the widened delegation against the reviewer's advice, reported first | §13 item 6, §17 |
| §8 item 2 fallback; item 7; item 8; 0.804 | — | ANSWERED: fallback not invoked; Lane D left with the human lead; benchmark rule given; 4/5 registered | §3 row 6, §4.4, §10, §13 |
| E5 checkpoints and the durable copy | — | FIXED | §9 |

Still unverified by the lead: the pool figures (the reviewer's counts on P10-S2's partition; the new partition will differ), every Part T rate, and the six-thread generation rate.

## 19. Rulings for the implementer

Fixed here so that nothing is guessed. Numbers G1–G22 are the third review's; L1–L12 are the lead's. A question these do not answer stops the work and returns to the lead before the freeze (section 11, item 6).

| # | Question | Ruling |
|---|---|---|
| G1 | Read layer of the rate grid; E-table's layer and rate; which rate each arm uses | Section 7.1, rule 1: grid at L = 4; the store's other layer at its chosen rate; E-table at the store's chosen layer with its own rate; every arm its module type's rate. This is the 36 units of section 14 |
| G2 | The pilot's snapshot; an undefined D_cal gap | M1 of calibration draw 1 at the chosen U; NOT STARTED: PILOT (GAP UNDEFINED) |
| G3 | Convergence at 2u | Any difference below 0.01, negative included, is converged. E-table, the joint arms and the stage-2 arms are not checked |
| G4 | Calibration after a code change; its cap | Section 7.1, rule 4 |
| G5 | Batch composition of generation, digest and regeneration | Section 4.3, rule 9 |
| G6 | Threads and determinism of CPU scoring and recomputation | Six threads, deterministic algorithms on, recorded with every score; bit-exact claims under those settings only |
| G7 | Workers | Part Q: one teacher per worker, at most two workers, six threads and 12 GiB each. Part T: at most three workers (8 GiB each, 24 GiB aggregate); at most two while another study runs (section 20). The count used is in every stage record |
| G8 | R-gloss-icl template and token ids | Sections 4.1 step 8 and 5.2 |
| G9 | Rows and codes the permutation controls act on | Section 5.2 |
| G10 | M-ii in a CONSOLIDATION-REJECTED cell; MODIFICATION with no evaluable cell | Section 8.5 |
| G11 | GEN missing or non-finite | Sections 8.3 and 8.6: never NOT PRESERVED |
| G12 | Recomputation difference | Section 8.6: ENGINEERING STOP — RECOMPUTATION; nothing labelled |
| G13 | Item, code and environment errors; Part Q re-runs | Section 8.6. Each item's record has an `item_error` field; the analysis refuses while any is set |
| G14 | Hash difference of a frozen file | PAUSED — IDENTITY (section 11, item 2) |
| G15 | Q3 fails for one teacher | The other teacher's Q_check still runs; the per-teacher table is complete; the label is row 3. Generation (step 7) does not run |
| G16 | Both ACQUISITION-NEGATIVE criteria hold | "(FIRST TEACHER; SECOND TEACHER)" |
| G17 | Rule 4 mechanics | Identity units in sorted key order (a no-gold source's unit is its contraction-expanded string, ADR-0022's lane-A ruling). One uniform draw each from a generator seeded 250904; B if u < 0.8 |
| G18 | Span format; exclusion of ordinary windows | Section 4.1 |
| G19 | Seed of the 200 WikiText-2 train pieces for route accuracy | 250918 (section 6) |
| G20 | Disk | A cell's resume checkpoints are deleted once its final snapshot is recorded; the durable copy is not counted against the 10 GiB (section 9) |
| G21 | Data of the Part T measuring rehearsal | Part Q's registered outputs, after Part Q is accepted; synthetic stand-ins before that; P10-S2's bundle is not trained on (section 10) |
| G22 | The benchmark's 30-minute bound | Each repetition's start, counted from the attempt's opening (section 10) |
| L1 | Names of the decisions | Decision 1: this approval. Decision 2 of Part Q and of Part T: each freeze-and-run. Records: `results/p10is2-partq-freeze-<date>/DECISION_2_PARTQ.md` and `results/p10is2-partt-freeze-<date>/DECISION_2_PARTT.md`, committed before the stage starts |
| L2 | Charged time | Worker count × wall time of every attempt, rehearsals and paused attempts included, kept in one ledger per part. The independent recomputation is charged |
| L3 | A stop on a registered test of the data step (a tokenization test, the filter-score assertion, the chrF cross-check, G8) | Not an engineering error to be resumed past: the step stops and returns to the lead, as R16 says |
| L4 | Non-finite loss | In calibration: the rate is DIVERGED and not eligible. In a rehearsal: recorded, and the cause is found before the freeze. In a registered stage: ENGINEERING STOP — NON-FINITE VALUE |
| L5 | Sealed rehearsal values | Written through a whitelist extractor to a sealed file; the report prints timings, memory, counts, yields and the chosen filter setting only. No test and no log prints a sealed value |
| L6 | Thresholds | Every threshold and count of this ADR is in the configs; a test asserts each equals the value written here |
| L7 | The checker copy of G9 | A copy of `seed_registry_check_r3.py` (SHA-256 `e462360420321aa284b0e4d47b106806419ab616794a5c632fee70f122c67594`) whose only changes exclude `studies/p10is2/**`, `configs/p10is2_*.toml` and `tests/test_p10is2_*.py`; the substitutions and the copy's hash are in the gate record. Run before each freeze and at the point of training |
| L8 | Analysis output without the fixed line | Refused (section 5.4). Registry keys carry the arm's and the reading's name, so two readings of one cell cannot share a key |
| L9 | Order of the two teachers' work in Part Q | Either order or in parallel (G7). No step of one teacher reads a value of the other except Q2, which is computed after both have run on Q_fit |
| L10 | WikiText-2 | Read from the main checkout's `data/wikitext2/`; its path and hashes are checked in step 1, before anything else |
| L11 | The run directory | Git-ignored; a guard refuses to start a registered stage in a directory git would track, or in a worktree that another study's freeze record names |
| L12 | What Part T may read of Part Q | The Part Q manifest's files only, by hash. Never a sealed rehearsal file, never a Q_fit or Q_check per-item score |

## 20. Sharing the machine, and cost

The machine is the human lead's working computer and other P10-I studies run on it.

- **Only stage 7, the timing benchmark, runs alone.** Its quiet condition excludes the processes of every study (section 10).
- **Everything else may share the machine.** No registered label reads wall or CPU time. Teacher outputs are fixed by thread count and batch layout, not by load; CPU scoring is deterministic at fixed threads; gate G4's MPS-against-CPU check uses tolerances.
- **What sharing costs.** Charged hours grow under contention, so a cap computed from a quiet rehearsal can PAUSE: every rehearsal record states the load it ran under. Memory: Part T's 24 GiB aggregate beside, for example, P10-I-R's 18 GiB comes to 42 of the machine's 48 GiB. **While another study runs, Part T uses at most two workers (16 GiB).**
- **Own worktree.** The study is implemented, rehearsed and run in its own worktree, never in another study's, and nothing is written in a frozen worktree during a run.

**Cost, as the third review recomputed it (estimates until the rehearsals):**

| Part | Charged hours | Not included |
|---|---|---|
| Part Q | about 4–12 (generation 2.5–3.8 h at the 10,000 minimum, 6.1–9.1 h to the 24,000 target, at most 6.4–9.7 h for the whole split pools, on an unmeasured two- to threefold slowdown at six threads; Q_fit and Q_check, minutes; the bank, about 6 minutes in P10-S2; rehearsal, about 1–2 h) | — |
| Part T at U = 2,000 | 21–57 | rehearsals, gates, routers |
| Part T at U = 8,000 | 41–96 | rehearsals, gates, routers |

The whole study is about 25–110 charged hours. No figure here is a measurement of efficiency.

`Astra review: NOT_PERFORMED`. Claude review is not Astra review.
