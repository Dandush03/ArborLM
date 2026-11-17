# ADR-0025 — P10-I-S2: Sequential teacher transfer, under word-level addresses supplied by rule

**Status: DRAFT — NOT APPROVED. Nothing under this ADR is implemented, calibrated, frozen or run.**

- **Date:** 2026-11-17 (UTC). **Drafted and revised by:** the lead (Claude Fable 5.2). **Independent specification review:** the `arbor-auditor` subagent (Opus 5.5), verdict NOT READY on the first draft; this revision answers it (section 18). Human lead's approval: not given.
- **Study code** P10IS2. **Package** `studies/p10is2/` (new files only). **Data-seed namespace** 250001–259999 (section 6).
- **Predecessor:** P10-S2 (ADR-0022), registered outcome TRANSFER-INCONCLUSIVE: TEACHERS-NOT-QUALIFIED, accepted by the human lead as registered. That outcome is not revised and P10-S2 is not reopened. This is a new study with new seeds.
- **Oracle qualification.** Every address and every registered route is supplied by rule. The human lead's instruction, verbatim as ADR-0022 records it: "S1 and S2 must not claim autonomous learned-memory success from oracle-assisted results." Section 5.4 puts the oracle-assisted line above every printed line.
- ArborLM is unproven research; no line of this study is a success claim. `Astra review: NOT_PERFORMED`. Claude review is not Astra review.
- Figures marked *(lead's choice)* are judgment calls fixed here before any observation. None is taken from a paper.

## 1. Question and outcomes

**Question.** Under word-level addresses supplied by rule, can a frozen pretrained student with an expandable key–value memory acquire a lexical capability from a first pretrained teacher, then a second from a second teacher, and still hold the first — and how does that compare with a dense adapter trained the same way, with lookup baselines, and with no memory?

**Part Q** qualifies the teachers and generates the material. **Part T** measures transfer. Part Q is finished, recomputed and accepted by the human lead before Part T is frozen.

Registered lines. Each is printed separately; none substitutes for another.

| Line | Positive means | Negative means | Inconclusive means |
|---|---|---|---|
| QUALIFICATION (Part Q) | Both teachers meet the quality criteria and the material exists in the required amount | A teacher fails a quality criterion. Says nothing about transfer | The corpus cannot supply the counts |
| ACQUISITION | The store learned each capability from teacher output alone, on held-out sentences, and the gain depends on the stored content | The store did not learn a capability within the registered training length | Mixed across cells, or a control failed |
| RETENTION | The first capability was kept while the second was acquired in the same store, on a task where the unprotected store does forget | The first capability was lost | Mixed, or retention was not challenged |
| GENERAL-QUALITY | With a learned keyword router deciding whether the store is read, ordinary English text is not degraded | It is degraded | — |
| AGAINST-DENSE | The store is ahead of the dense adapter trained the same way | The dense adapter is ahead | Not distinguished or mixed |
| AGAINST-LOOKUP | The store is ahead of every lookup and retrieval baseline | A lookup baseline does as well: the result shows nothing a lookup cannot provide | Mixed |

**Milestone question 2** (the P10 direction: sequential acquisition with retention) is one derived line, built as ADR-0022's study label was:

- SUPPORTED (append-frozen), or SUPPORTED (append-frozen + consolidation): ACQUISITION-POSITIVE and RETENTION-POSITIVE and GENERAL-QUALITY PRESERVED (section 8.4).
- **WITHHELD — GENERAL QUALITY NOT PRESERVED UNDER A LEARNED ROUTE:** ACQUISITION and RETENTION are positive and the GEN check fails in any cell. Neither a positive nor a negative.
- NOT ESTABLISHED: otherwise.

AGAINST-DENSE and AGAINST-LOOKUP are printed directly beneath it. If AGAINST-LOOKUP is LOOKUP SUFFICES, the milestone line itself carries "a lookup baseline does as well: {name}".

Descriptive lines, which enter no line above: MODIFICATION (M-ii), COMPOSES C1 / C2, the annotations of ADR-0022 section 11.4, and the cost lines (section 8.5).

## 2. Background

| Finding | Record |
|---|---|
| P10-S2 stopped before its freeze. Both teachers passed own score (0.7675, 0.7754 against 0.55) and margin (0.6214, 0.6425 against 0.30). A filter setting passed on Q_fit for both. Point precision on Q_check was 0.9231 (72 of 78) and 0.9545 (21 of 22) against 0.90 | `results/p10s2-datagen-2026-11-16/README.md`, `prefreeze_record.json` |
| The gate failed on counts: accepted Q_check items 78 and 22 against 150; accepted pools 7,804 and 2,341 against 8,000 (7,763 and 2,300 available against the 10,000 the sufficiency rule needs) | same |
| Acceptance on Q_fit was 104 of 500 (20.8%) and 41 of 500 (8.2%). Of 60,000 generation sources per capability, 13.0% (A) and 3.9% (B) were accepted. 79 accepted sources were shared between the two pools | same; shares computed from the recorded counts |
| In-vocabulary no-gold sources: 734,418 (A) and 784,089 (B). Gold pairs outside Q, D_cal and D_con: 181,970 and 132,151 | `prefreeze_record.json`, `partition` |
| Generation took 740 s (A) and 844 s (B) per 60,000 sources at the machine's default thread count; the whole step 2,100 s; peak resident memory 5,677 MiB | `steps.memory_by_phase` (differences of recorded elapsed times) |
| The gate's per-item inputs on Q were not stored | `docs/reviews/p10s2-qualification-2026-11-16/REVIEW.md`, finding 1 |
| No student was trained. Nothing about transfer was measured | ADR-0022, addendum of 2026-11-16 |
| P10-S1, oracle addressing: no line positive for the store; DICT DOMINATES ON THIS TASK; DENSE AHEAD at matched updates, while at matched compute the flat store was ahead of the dense arm at 32K/16K in 5 of 5 replicates (finding 4); memory arms ran at an untuned rate; UNDERTRAINED-AT-U_P | `results/p10s1-run-2026-11-17/OUTCOME.md`, sections 2 and 4 |
| P10-S1: the flat store's mean a_use at the run length was 1.000 at 0.5 facts per slot and 0.654 and 0.637 at the loaded cells | same, section 4 table |
| P10-S0: learned addressing (A5-D) qualified at 4,096 and 16,384 slots at 0.5 facts per slot; OVERLOAD NOT QUALIFIED; the memory is told the answer position; nothing there is about natural language or another backbone | `results/p10s0-run-2026-11-16/OUTCOME.md` |
| The human lead's P10 list for this study includes "mechanism ii", "capabilities A, B, combined" and "the five cost measures"; he later strengthened the COMPOSES rule ("let's strenght the registerd rule, the ost is aceptable") | `docs/reviews/p10-design-2026-11-15/adr-0022-review/CONFIRM.md` section 7 item 6; `HUMAN_DECISIONS_2026-11-15.md` |

**One precision on the direction record.** `DIRECTION.md` section 5 says both teachers "passed the quality criteria". The Q_check precision was above 0.90 but was read on 78 and 22 items (95% Wilson lower bounds 0.842 and 0.782), below the 150 the design required. Filter precision at the registered sample size is not yet established; Part Q measures it.

**Provenance.** The teachers and the corpus are P10-S2's, whose quality figures have been seen. Part Q is a confirmatory re-measurement on a new partition, not a blind first test.

## 3. Every change from ADR-0022 (revision 5 with its addenda)

Anything not in this table is as ADR-0022, whose sections are cited as definitions and not edited. Arm names map: ST1 → M1, M-append-frozen → M-append, LoRA-1 → D1, L-seq → D-seq, L-joint → D-joint, L-sep → D-sep, M-i-separate → M-sep.

| # | Item | ADR-0022 | This study | Why |
|---|---|---|---|---|
| 1 | Teacher qualification | A gate inside the pre-freeze step | Part Q, a registered stage with its own outcome | A count shortfall must not end the study |
| 2 | Amount of generation and of Q_check | Fixed: 60,000 sources; 500 items | Generate until met, within a budget (section 4.3) | `DIRECTION.md` section 5, rule 2 |
| 3 | Q_fit; panel of Q1 and Q2 | Q_fit 500; Q1 and Q2 on Q (1,000) | Q_fit 2,000, fixed; Q1, Q2 and Q3 on it | Section 4.2: at 500 items teacher B's filter passes only with zero errors |
| 4 | Thresholds of Q1–Q4, the filter grid, the 0.60 correctness cut, the population (sentences with both references) | — | Same | Scientific thresholds |
| 5 | Per-item Q records | Not stored | Stored and hashed | Audit finding |
| 6 | Shared English sources of A and B | Split in halves after generation | Split before generation by a listed seed, four fifths to B | The pools overlap by about 600,000 sources; B's yield is about a third of A's (section 4.3) |
| 7 | Generation threads | Machine default | Six, fixed | Outputs differ with the thread count |
| 8 | Replicates | Four or three by a rung rule; overlapping draws | Three; disjoint draws if both pools reach 24,000 | The cap is extendable instead; independence of replicates |
| 9 | Training length | 2,000 or 1,000 by budget | Convergence rule to at most 8,000 (section 7.1) | P10-S1's UNDERTRAINED-AT-U_P |
| 10 | Learning rates | Store fixed at 0.003; LoRA two values; ties to the first listed | Three values for each trained module type; ties to the smaller | P10-S1's untuned memory arms |
| 11 | Arms | — | D-append added; R-gloss-icl added; MA-gold and its annotation TEACHER-EQUIVALENT-TO-GOLD removed | Sections 5.2 and 13 |
| 12 | Study label | One label, first match of 12 rows | Separate lines plus the milestone line. NOT REPLICATED, INTERMEDIATE and ORDER-DEPENDENT are printed as INCONCLUSIVE with the passing cells per order | "No line substitutes for another" |
| 13 | General quality | Gate of the positive label; WITHHELD when it fails | Same, on the milestone line; also its own line | Unchanged in effect |
| 14 | Retention | NOT_EVALUATED checked before FORGETS | The negative zone is read first over evaluable cells (section 8.3); RETENTION-POSITIVE also needs forgetting pressure from M-seq | A failure must not be hidden; a retention result on a task the unprotected store does not forget is empty |
| 15 | M-seq | Descriptive only | Also the source of forgetting pressure | Item 14 |
| 16 | M-ii | Class in label rows 7 and 8 | Descriptive MODIFICATION line; decides the "+ consolidation" suffix | Unchanged in effect |
| 17 | Combined tasks C1, C2 | Addendum's rule; ten arm-cells per replicate | Same rule; twelve arm-cells (D-append added) | Item 11 |
| 18 | Cost | Five measures; TRAINING COST COMPARABLE; FEWER VALUE ROWS ACTIVE; stored size | Same measures and lines except TRAINING COST COMPARABLE, removed; counted training multiply-adds added | `DIRECTION.md` section 7: no wall-time comparison on a machine that cannot be isolated for the training stage |
| 19 | A cap stops a stage | INCOMPLETE | PAUSED, resumable | `DIRECTION.md` section 5, rule 1 |
| 20 | Fallback teacher | Replaces one teacher that failed the gate | By the human lead's decision; both teachers are then re-qualified on the rebuilt partition | Section 4.4 |
| 21 | Memory guard of the data step | 8 GiB | 12 GiB | Attempts 6 and 7 stopped at 8.09 and 9.38 GiB |
| 22 | Frozen inputs, seeds, rehearsal | — | Sections 6 and 11 | P10's engineering failures |

## 4. Part Q — teacher qualification and data generation

### 4.1 Order of work and panels

The order is fixed. Each step is complete before the next starts.

1. Hash checks of every input; the applied generation configuration of each teacher is asserted equal to its pinned file and recorded; student conversion and equivalence record (gate G8); tokenizer record.
2. **Fixed-input counts, before any teacher runs.** E_A and E_B at least 500 items each and E_C at least 250 (ADR-0022 section 5.2); the training-side pool of in-vocabulary sentences with both references at least 3,300 (Q_fit, D_cal, D_con and one Q_check block); 44 marker-like and at least 100 ordinary GEN windows. A shortfall gives QUALIFICATION-INCONCLUSIVE: DATA-INSUFFICIENT.
3. Partition with this study's partition seed. Panels, all from sentences with both a German and a French reference, as in P10-S2:

| Panel | Size | Use |
|---|---|---|
| E_A, E_B; E_C; E_open | 1,000 each if the data allow; 500; 500 | Evaluation; combined tasks; descriptive. **Never scored before the registered run of Part T** |
| Q_fit | 2,000 | Q1, Q2, Q3 |
| Q_check reserve | 16 blocks of 500 in a seeded order, or as many whole blocks as the pool holds | Q4 |
| D_cal; D_con | 500; 300 | Part T calibration and pilot; M-ii's acceptance constraint |

4. The source pools are then defined, excluding every identity group of every panel and of the whole Q_check reserve, drawn or not. Shared sources are split (section 4.3, rule 4).
5. Teachers and the untrained student on Q_fit; Q1, Q2; the filter is selected (Q3) and fixed.
6. Q_check (section 4.3, rules 1–3); Q4.
7. Generation (rules 4–6). Steps 7 and 8 run only if both teachers pass Q1–Q4.
8. Teacher outputs on E_A, E_B, E_C, E_open, D_cal and D_con, stored and hashed and **not scored**; the token-id bank and tokenization tests of ADR-0022 section 14.2; the truncation limit; the GEN window list; the C1 pairing.

No teacher runs after Part Q. Every output above is listed with its hash in the Part Q manifest.

### 4.2 Quality criteria (scientific thresholds)

| # | Criterion | Threshold | Reason for the figure |
|---|---|---|---|
| Q1 | Teacher's mean sentence chrF-norm on its own capability, on Q_fit | ≥ 0.55 | Most short sentences substantially right; fixed in ADR-0022 before any teacher was run |
| Q2 | Q1's score minus the larger of the other teacher's and the untrained student's score on that capability | ≥ 0.30 | The capability is the teacher's and absent from the student, so a gap of at least 0.30 exists to close |
| Q3 | On the grid τ ∈ {−0.05, −0.10, …, −0.60} × length ratio ∈ {[0.5, 2.0], [0.6, 1.6]}: the most permissive setting whose 95% Wilson lower bound of precision on Q_fit is ≥ 0.90, where an accepted output is correct if its chrF-norm against the best reference is ≥ 0.60. Ties: larger τ, then the narrower range | a setting exists | At most one accepted item in ten wrong; selecting on the lower bound keeps the setting off its own edge |
| Q4 | Point precision of that setting on Q_check (same 0.60 cut), read on at least 150 accepted items | ≥ 0.90 | The same bar on held items; 150 accepted items give a 95% interval of about 0.84–0.94 at the bar |

**Sampling risk of Q3, and why Q_fit is 2,000.** A Wilson lower bound of 0.90 needs at least 35 accepted items with no error, 53 with one, 69 with two, 84 with three. Teacher B's setting in P10-S2 accepted 41 of 500, all correct: one wrong item would have failed it. That would be a quality failure caused by the size of the panel.

| Q_fit | Expected accepted at P10-S2's shares (A / B) | Errors tolerated (A / B) |
|---|---|---|
| 500 | 104 / 41 | 4 / 0 |
| 2,000 | 416 / 164 | 29 / 8 |

Q_fit is fixed at 2,000 before any observation; it is never extended to make a setting pass. The teachers need under a minute for it. A larger panel can admit a more permissive setting nearer the bar; Q4 on held items is the guard against that.

**Sampling risk of Q4.** At a true precision of 0.92, a reading on 150 to 160 items falls below 0.90 in about one run in six. That is a registered quality failure.

### 4.3 Counts: generate until met, within a budget

None of these counts is a scientific claim. Stopping reads accept counts only.

| Count | Target | Block | Ceiling |
|---|---|---|---|
| Accepted Q_check items, per teacher | 150 | 500 items | the reserve (at most 8,000 items) |
| Accepted sources per capability: minimum | 10,000 | 20,000 sources | the capability's split pool |
| Accepted sources per capability: disjoint target | 24,000 (3 × 8,000) | same | same |

**Q_check: three stopping rules.**

1. The filter setting is fixed from Q_fit before the first Q_check block is drawn.
2. Blocks are taken in the reserve's seeded order, never skipped or reordered, also across a pause. After each block only the filter is applied and accepted items are counted. Drawing stops at the first block boundary with at least 150 accepted items; the stop block index is recorded.
3. No reference is read and no chrF is computed or logged for any Q_check item before the stop is recorded. Precision is then computed once, in one call, over every accepted item of every block drawn. Q_check is not extended after that.

The accept indicator depends only on the teacher's output and the source, so the number accepted carries no information about correctness and the precision reading is unbiased (review, R5).

**Generation.**

4. **Split before generation.** Each identity unit that is a no-gold source for both capabilities is assigned to B with probability 4/5, otherwise to A, by the source-split seed *(lead's choice)*. Each teacher generates only on its own sources. A capability's count is its own accepted outputs after the evaluation-equal drop; it does not depend on the other capability.
5. Sources are taken in a seeded order in blocks. A capability stops when it reaches 24,000 or its pool ends.
6. **Disjoint or overlapping draws.** If both capabilities reach 24,000, each replicate's 8,000 items are drawn without overlap between replicates. Otherwise, if both reach 10,000, replicates draw from the whole pool and the shared share is printed beside every line that says "every cell". If either is below 10,000 when its pool ends: QUALIFICATION-INCONCLUSIVE: DATA-EXHAUSTED.

**Projection (estimates; the pool overlap is the reviewer's bound from recorded counts, not a measurement).** The two pools share at least about 600,000 sources. After the split, A has about 254,000 sources and B about 664,000. At P10-S2's yields (13.0% and 3.9%) that is about 33,000 accepted for A and about 26,000 for B. Acceptance by the two teachers is correlated (79 shared accepted sources where independence predicts about 19), so yields on the split pools may differ. **The disjoint target may be out of reach for B; rule 6 then gives overlapping draws.** Q_check needs about 1,000 items for A and about 3,400 for B at P10-S2's shares.

**Budget and persistence.**

7. Part Q's charged-hours cap is the time charged before its freeze plus twice the whole-pool time projected from its rehearsal (section 10), computed by code. A stop on the cap or the memory guard is PAUSED; the stage resumes at the next block and completed blocks are not regenerated.
8. Every per-item input of the gate is stored and hashed: outputs, beam scores, accept indicators, chrF per item on Q_fit and Q_check, the full grid table, and the score of every rejected generation output.
9. Six threads, fixed and recorded. A fixed 100-sentence output digest per teacher is asserted at every resume.

### 4.4 QUALIFICATION outcome (first match wins; a per-teacher status table is printed under the label)

| Order | Label | Rule |
|---|---|---|
| 1 | QUALIFICATION-ENGINEERING-FAILURE | A hash mismatch, a failed G1, an applied generation configuration that differs from the pinned file, or a digest mismatch at a resume |
| 2 | QUALIFICATION-INCONCLUSIVE: DATA-INSUFFICIENT | Step 2 of section 4.1 |
| 3 | QUALIFICATION-NEGATIVE: QUALITY (teacher and criterion named) | A teacher fails Q1, Q2, Q3 or the precision of Q4 |
| 4 | QUALIFICATION-INCONCLUSIVE: DATA-EXHAUSTED | The reserve ends before 150 accepted items, or rule 6 |
| 5 | TEACHERS-QUALIFIED (DISJOINT DRAWS / OVERLAPPING DRAWS) | Both teachers pass Q1–Q4 and both pools reach at least 10,000 |

PAUSED is a state of the stage, not an outcome; no label is printed while the stage is paused.

**If only one teacher qualifies.** Part T does not run with one teacher: retention needs two. The label of row 3 or 4 is registered. If exactly one teacher failed (on quality or on exhaustion), the human lead may decide, at that time, to invoke the fallback of ADR-0022 section 4.2 (`Helsinki-NLP/opus-mt-en-es`, a different training regime) once. It needs a download (section 12), and the Spanish files would come from a later Tatoeba export, which the report states. A fallback language changes the gold pairs, the identity groups and the partition. So **both** teachers then pass the whole of Part Q again on the rebuilt partition, with the same seeds and rules; the surviving teacher's earlier figures are printed and do not count. If that run does not end TEACHERS-QUALIFIED, or both primary teachers failed, the study ends with the Part Q label and Part T is NOT STARTED.

The outcome is recomputed independently from the stored per-item records. The recomputation also regenerates a seeded subsample of 1,000 sources per teacher at six threads and compares outputs, since stored outputs cannot check generation.

## 5. Part T — design

### 5.1 Stages of training

Capabilities A (English→German) and B (English→French). Both orders run in every replicate. A **cell** is one (replicate, order) pair: six cells per sequential arm. Every stage runs U updates of batch 32 with AdamW, no weight decay, clip 1.0, constant rate, fresh optimizer state. Training material is teacher output on sentences with no reference in that language.

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

Not trained; each uses the replicate's training draw, not the whole pool:

| Baseline | Definition | What it isolates |
|---|---|---|
| R-exact | Table from training source to accepted output | Confirms the panels are held out (zero hits, gate G1) |
| R-gloss | Co-occurrence lexicon (Dice), word by word | A word-level dictionary without learning |
| R-gloss-icl | The top gloss of each source word placed in the frozen student's prompt *(lead's choice, from the review)* | A lexicon used by the student: the untrained analogue of a word-addressed store |
| R-nn | Nearest training source by character-trigram TF-IDF | Sentence retrieval without composition |
| R-icl | The four nearest accepted pairs in the prompt | Retrieval that can generalize |

Controls on every memory cell, on a fixed 300-item subsample of each panel: memory off; values permuted; word codes permuted; marker-only; for a stage-2 store they act on the second stage's rows and codes (ADR-0022 section 7).

**Fairness of the dense comparison, stated.** Parameters, updates, batch, data and the size of the rate search match. The store also has a two-way read-layer search, an extra tuning dimension in its favour. The store receives the task identity by rule inside its address; D-append and D-seq receive it only through the prompt. D-sep is the dense arm given the same task information by rule. Rates are selected at 2,000 updates for every module type alike and used at U.

### 5.3 What transfer is measured on

Every score is on E_A or E_B: evaluation-side sentences, disjoint in identity groups from every training source, built from the closed vocabulary. Gate G1 requires that no evaluation reference equals a training output and that R-exact has zero hits. **A plain lookup of the generated pairs answers no evaluation item.**

What training and evaluation share is the vocabulary: the test is composition of known words into unseen sentences. The frozen student supplies word order and morphology; the store supplies per-word target information. This is lexical knowledge used by the student, not transfer of a skill. A word-level lookup can in principle do it, which is why E-table and the lexicon baselines are in the design. The share of evaluation items with a training source at word-level edit distance 1 (0.0816 in P10-S2's partition) is reported, and every score is also printed without those items; that figure enters no rule.

### 5.4 Addressing

**Oracle addressing, as ADR-0022 section 5.4.** The code of (task, word) is a fixed random unit vector from a seeded hash. The read is a flat scan with top-8; no tree, no index.

- Why not P10-S0's interface: A5-D was qualified on the byte backbone, on synthetic facts, with the answer position given. Using it here would test addressing and transfer at once.
- Load: 2,001 codes per task. M-append: 4,002 codes on 8,192 rows (0.49). M-seq: 4,002 on 4,096 (0.98). No arm is in overload. The loads of P10-S0 and P10-S1 are context, not evidence: another task and backbone.
- **The fixed line.** Every label, class, annotation, composition and cost line, table, caption, machine-readable record and terminal summary carries directly above it: **"oracle-assisted (word-level addresses supplied by rule); lexical translation of short closed-vocabulary sentences, two capabilities of one kind; frozen English student; teacher-only training material verified by measured-precision filter; not autonomous learned memory."** Every line also prints "(3 replicates, U = …)", and NOT CONVERGED AT U where section 7.1 says so. The analysis refuses to write a line without them.
- Learned addressing is not part of this specification; it would be a separately approved supplement after P10-I-S0.

### 5.5 General quality, and the combined tasks

**GEN** is measured as ADR-0022 sections 5.4 and 6.4 with rulings C-M6 and m9 and the addendum of 2026-11-16: a keyword router (A, B, none) trained with route labels; 44 marker-like and 100 ordinary windows of WikiText-2 validation, one half of the weight each; both decision positions; for every M1 and stage-2 memory snapshot, and for D-seq as comparison. The router's route accuracy and false-trigger counts are printed beside it. Under the oracle route general text is bit-identical to the student and counts for nothing.

**C1 and C2** are as `ADR-0022-addendum-combined-tasks.md` sections 2 to 9, never trained on, scored under the oracle route on the stage-2 snapshots of M-append, M-ii, D-seq and D-append (both orders), M-joint, D-joint, M-sep and D-sep (twelve arm-cells per replicate), plus S0 and the ensemble. D-append is scored as D-seq is: its adapters apply at every position.

## 6. Seeds

**Data seeds** (partitions, draws, orders, sampling, hashes) lie in 250001–259999. The review found no overlap with P1 to P10 or with the other P10-I drafts.

| Use | Data seeds |
|---|---|
| Registered replicates: bases 250001, 250101, 250201 | +1 training draw; +2 batch order (a fresh generator also orders M-ii's replay); +4 permutation controls; +10 code hash; +13 router "none" prefixes and batch order |
| Partition side (Part Q) | 250901 partition; 250902 Q_fit; 250903 Q_check reserve order; 250904 source split; 250905 source block order; 250906 control subsample; 250907 GEN ordinary windows; 250908 teacher tokenizer and digest sentences; 250909 tokenization test (c) id sequences; 250910 equivalence injection vector; 250911 C1 pairing; 250912 seen items; 250913 timing-benchmark items; 250914 recomputation's regeneration subsample |
| Analysis | 250915 bootstrap intervals (descriptive) |
| Calibration | 251001 + 100·i, same offsets |
| Rehearsal | 252001 + 100·i, same offsets |

**Initialization seeds and test seeds are not assigned here.** They are assigned in the programme-wide registry the lead will write (`docs/reviews/p10-i-direction-2026-11-17/SEED_REGISTRY.md`), one per role and replicate: stage-1 store; appended rows; M-joint store; D1; second adapter of D-append; D-joint; E-table; router projection and keys; and the unit-test range. The registry is checked against every literal and derived seed of P1 to P10 and of the other P10-I studies before any freeze.

Every generator is seeded directly by a listed seed through one function that records seed and purpose and refuses any other; no seed is derived by hashing or arithmetic beyond the listed offsets. Gate G9 asserts this on planned and on recorded seeds.

## 7. Calibration, pilot and gates (before the Part T freeze; calibration seeds; D_cal only)

### 7.1 Calibration

1. **Rates.** Store and E-table: {0.001, 0.003, 0.01}. LoRA: {0.0001, 0.0003, 0.001} *(lead's choice: three values around ADR-0022's)*. Each is a stage 1 of 2,000 updates on each capability, calibration draw i = 0. The rate with the higher mean chrF on D_cal over the two capabilities is taken; a difference below 0.01 goes to the smaller rate. The store's read layer L ∈ {4, 12} is then chosen the same way.
2. **Training length.** With the chosen settings, M1 and D1 are trained on each capability on calibration draw i = 1 with snapshots at 1,000, 2,000, 4,000 and 8,000 updates. U is the smallest u in {1,000, 2,000, 4,000} such that, for both module types and both capabilities, chrF on D_cal at 2u exceeds chrF at u by less than 0.01. If none qualifies, U = 8,000 and every Part T line carries NOT CONVERGED AT U. One U serves every arm and stage. Convergence of the stage-2 arms is not checked; that is a stated limit.
3. Calibration scores are never reported as results.

### 7.2 Pilot gate

At the calibrated settings, on D_cal: if M1's gap closed is below 0.25 for either capability, Part T is **NOT STARTED: PILOT** and the work returns to the human lead.

### 7.3 Gates

G1 partitions and zero R-exact hits; G2 repeat-scoring identity; G4 determinism on CPU, snapshot round trip, gradient reach (frozen rows, the frozen first adapter and the student receive no gradient), MPS against CPU on 20 updates; G5 route "none" bit-identical to the student, and gate isolation of appended rows; G6 addresses and routes take the prompt only; G7 frozen bytes; G8 student equivalence; G9 seeds. Definitions and tolerances as ADR-0022 section 12.3. A failed gate stops the run with ENGINEERING-FAILURE.

## 8. Rules that turn measurements into labels

Every rule reads the final snapshot of a stage. Intermediate snapshots (U/4, U/2) are descriptive.

### 8.1 Quantities, per cell

- s_c(X): mean chrF-norm of arm X on the full panel E_c (maximum over references per item).
- Gap closed: G_c(X) = (s_c(X) − s_c(S0)) / (s_c(teacher c) − s_c(S0)), on the full panel. Defined only if the denominator is ≥ 0.30.
- Control quantities (value-permuted, code-permuted, marker-only, and the arm's own G set beside them) are computed on the 300-item subsample, with the teacher and S0 scores of the same subsample.
- "First" and "second" are the capabilities in the cell's order. V1(X) is the stage-1 snapshot the arm continues: M1 for memory arms, D1 for dense arms, of the same cell.
- **Forgetting.** F(X) = s_first(V1) − s_first(X after stage 2). Retained share ρ(X) = G_first(X after stage 2) / G_first(V1). **ρ, F and RET are defined for an arm's cell only if G_first(V1(X)) ≥ 0.50;** otherwise that arm's cell is NOT EVALUABLE: FIRST NOT ACQUIRED.

### 8.2 Cell-level conditions

| Condition | Rule | Reason for the figures |
|---|---|---|
| ACQ1 | Full-panel G_first(M1) ≥ 0.50; on the subsample, G(M1) − max(G_value-permuted, G_code-permuted) ≥ 0.30 and G_marker-only ≤ 0.25 | Half the gap is the least that can be called acquisition; most of that half must come from the stored content at its addresses; the marker alone may carry at most half of the minimum |
| ACQ2(X) | G_second(X) ≥ 0.50 and ≥ 0.80 × G of the single-teacher module of the same type on that capability in the same replicate, which is M1 or D1 of the **other** order; for memory arms the same margin and marker-only limits on the second stage's controls | A second capability worth four fifths of what one teacher alone gives |
| RET(X) | F(X) ≤ 0.03 and ρ(X) ≥ 0.90 | 0.03 is about 2.5 times the 95% half-width of a 1,000-item panel mean (0.012 at a standard deviation of 0.2, ADR-0022 section 5.2); losing more than a tenth of what was acquired is not retention |
| Negative zones | Acquisition: G < 0.25. Retention: ρ < 0.70 | Half the acquisition bar; a loss of three tenths or more |
| Forgetting pressure | In at least 4 of the 6 cells: G_second(M-seq) ≥ 0.50 and ρ(M-seq) < 0.90 | A validity condition: the same module type, without protection, loses more than a tenth while learning the second capability, in a majority of cells *(lead's choice)*. D-seq's ρ is printed beside it and does not count |

### 8.3 Lines (first match wins within a line; "every cell" means all six)

A registered record that is missing makes the study INCOMPLETE (section 8.6) and no line is derived.

**ACQUISITION**

| Order | Label | Rule |
|---|---|---|
| 1 | NOT EVALUABLE | A gap is undefined on E_A or E_B |
| 2 | ACQUISITION-INCONCLUSIVE: CONTROL-FAILED | A value or code permutation of M1 or of M-append gives G ≥ 0.50 in any cell. (The same reading for M-seq, M-ii and M-joint is printed on their own lines and does not act here) |
| 3 | ACQUISITION-NEGATIVE (FIRST TEACHER / SECOND TEACHER) | G_first(M1) < 0.25 in every cell / G_second(M-append) < 0.25 in every cell |
| 4 | ACQUISITION-POSITIVE | ACQ1 and ACQ2(M-append) pass in every cell |
| 5 | ACQUISITION-INCONCLUSIVE | Otherwise; passing cells per order are printed |

**RETENTION.** Under every label the per-cell table of G_first(M1), ACQ1, G_second, F and ρ for M-append is printed, with the number of evaluable cells in the negative zone.

| Order | Label | Rule |
|---|---|---|
| 1 | NOT EVALUABLE: GAP UNDEFINED | A gap is undefined |
| 2 | RETENTION-NEGATIVE: FORGETTING | At least four cells are evaluable for M-append, and ρ(M-append) < 0.70 in every evaluable cell |
| 3 | NOT EVALUABLE: FIRST NOT ACQUIRED | ACQ1 fails in any cell |
| 4 | RETENTION-INCONCLUSIVE: NOT CHALLENGED — SECOND NOT ACQUIRED | G_second(M-append) < 0.50 in any cell |
| 5 | RETENTION-INCONCLUSIVE: NOT CHALLENGED — NO FORGETTING PRESSURE | The forgetting-pressure condition does not hold |
| 6 | RETENTION-POSITIVE | RET(M-append) passes in every cell |
| 7 | RETENTION-INCONCLUSIVE | Otherwise |

A NOT EVALUABLE retention line is not read as negative and not as "no forgetting"; the table beneath it says what was seen.

**GENERAL-QUALITY.** PRESERVED if, for M-append's stage-2 snapshot in every cell, under both decision positions, the loss increase over the unmodified student is ≤ 0.02 nats per token. NOT PRESERVED otherwise. A pass is described as "the keyword router stayed silent".

**AGAINST-DENSE.** The primary pair is M-append against D-append, in every cell. ΔG = G_second(M-append) − G_second(D-append); Δρ = ρ(M-append) − ρ(D-append). For each: MEMORY AHEAD if Δ ≥ +0.05 in every cell; DENSE AHEAD if Δ ≤ −0.05 in every cell; NOT DISTINGUISHED if |Δ| < 0.05 in every cell; MIXED otherwise. Δρ is NOT EVALUABLE if either arm's cell is not evaluable in any cell. 0.05 is just above the precision of a gap closure on 1,000 items (about 0.04). The reading is at matched updates. Printed with the line, always: the qualifier **"the memory receives the task identity by rule in its address; the dense arm receives it only through the prompt"**; the same two quantities for M-seq against D-seq; D-sep's and M-sep's scores (retention BY CONSTRUCTION); the annotation NO ADVANTAGE OVER SEPARATE ADAPTERS by ADR-0022's rule; and the counted training multiply-adds per update of both arms.

**AGAINST-LOOKUP.** For each cell and capability, b is the best score among R-gloss, R-gloss-icl, R-nn, R-icl and E-table. LOOKUP SUFFICES if b ≥ s(M-append) − 0.03 on both capabilities in every cell. MEMORY ADDS OVER LOOKUP if s(M-append) − b ≥ 0.05 on both capabilities in every cell. MIXED otherwise. The baseline that gave b is named, with E-table's parameter count (about half the store's).

### 8.4 Milestone line

SUPPORTED (append-frozen) requires ACQUISITION-POSITIVE, RETENTION-POSITIVE and GENERAL-QUALITY PRESERVED. The suffix becomes "(append-frozen + consolidation)" if, in addition, MODIFICATION is RETAINS UNDER MODIFICATION and M-ii's snapshots pass the GEN check in every cell. If ACQUISITION and RETENTION are positive and GENERAL-QUALITY is NOT PRESERVED: WITHHELD — GENERAL QUALITY NOT PRESERVED UNDER A LEARNED ROUTE, printed with the router's false-trigger rate and the loss increase per cell. Otherwise NOT ESTABLISHED. No result printed BY CONSTRUCTION satisfies any rule.

### 8.5 Descriptive lines (they enter no line of 8.3; only MODIFICATION touches the milestone suffix)

- **MODIFICATION (M-ii)**, first match: CONSOLIDATION-REJECTED (count printed) if any cell failed the D_con constraint; FORGETS UNDER MODIFICATION if ρ < 0.70 in every evaluable cell; RETENTION BY INERTIA if ACQ2 and RET pass in every cell and any cell is below the modification floor; RETAINS UNDER MODIFICATION if ACQ2 and RET pass in every cell; INTERMEDIATE otherwise. RET's reference is V1 = M1.
- **COMPOSES C1 / C2**: the strengthened rule of the addendum, section 8, with its two fixed lines and the exact-match pass rate (section 9, and ruling m10).
- **Annotations** of ADR-0022 section 11.4 with the rulings of its addenda (printed if they hold in any replicate or order, with the mean), except TEACHER-EQUIVALENT-TO-GOLD. This includes ROUTER QUALIFIED / NOT QUALIFIED, APPEND COST, EXACT-MATCH WEAK, BELOW JOINT BOUND, BELOW ADAPTER JOINT and TASK-CODED SPARSE RETENTION. Seen-item scores and E_open scores are printed and enter nothing.
- **Cost.** The five measures of ADR-0022 section 10.2 are recorded: teacher inference (per accepted item), student training (seconds, updates, rows, memory, and counted multiply-adds), footprint, active work as counts, and the timing benchmark. Lines: FEWER VALUE ROWS ACTIVE and the stored-size arithmetic, as ADR-0022 section 11.5. **TRAINING COST COMPARABLE is not printed:** it compares training wall seconds, and training runs for many hours on a machine that cannot be isolated for that long. Training seconds are recorded as measured, without a comparison label. No count is reported as measured efficiency.

### 8.6 Study status and recomputation

- ENGINEERING-FAILURE: a failed gate, a hash mismatch, a difference between frozen and running inputs, or a recomputation difference that changes any condition, line or annotation.
- INCOMPLETE: a registered record is missing after the run has ended. No line is derived and no denominator is reduced.
- PAUSED is a state, not an outcome.
- **Recomputation**, as ADR-0022 section 13.3 and rulings B-M9 and C-M3: no result is reported before every registered score is recomputed on CPU from the snapshots. With the frozen scoring code every score must be bit-identical; with the auditor's own code every greedy sequence must be identical and every item score within 1e-6. A cell beyond tolerance is NOT EVALUABLE and the recomputed value is the one reported. Verdicts are compared as verdicts.

## 9. Limits (DIRECTION.md section 5)

| Limit | Kind | Rule |
|---|---|---|
| Part Q charged hours; Part T charged hours: each P + 2R, computed by code from its rehearsal and shown to the human lead at its Decision | Resource cap | PAUSED and resumable. Extended on cost projections only, never on an outcome value; every planned block and cell still runs |
| Memory guard: 12 GiB per worker in Part Q; 8 GiB per worker and 24 GiB aggregate in Part T | Resource cap | PAUSED; raised only on measured memory |
| Generation sources; Q_check items | Design ceiling | Generate until met (section 4.3); the ceilings are the split pools and the reserve |
| Training length U | Design ceiling | Convergence rule; top rung 8,000, then NOT CONVERGED AT U |
| Q_fit 2,000; replicates 3; rows per stage; vocabulary; panel sizes; the 4/5 split | Design, fixed | Not extended and not changed after the Part Q rehearsal |
| Q1–Q4, the 0.60 cut, the 150 minimum | Scientific threshold | Never relaxed. Neither Q_fit nor Q_check is extended after a quality value is read |
| ACQ, RET, negative zones, forgetting pressure, 0.05 and 0.03 margins, GEN 0.02 nats, pilot 0.25, COMPOSES 0.80 and 0.50, M-ii's 0.02 and 0.10 | Scientific threshold | Never relaxed |

No limit is extended because a partial result looks close.

## 10. Stages, machine load, order of work

The machine is also the human lead's working computer. **No registered label reads wall time.** Load is measured at each stage, not assumed: the 1-minute load average is recorded at the start and end of every stage.

| # | Stage | Device | Quiet machine | Human gate before it |
|---|---|---|---|---|
| 1 | Implementation and tests on synthetic stand-ins; implementation audit | CPU | no | approval of this specification |
| 2 | Part Q rehearsal (below) | CPU, six threads | no | — |
| 3 | Part Q freeze; registered Part Q; independent recomputation | CPU | no | Decision 1; then acceptance of the outcome |
| 4 | Calibration, convergence rule, pilot | MPS training, CPU scoring | no | — |
| 5 | Part T rehearsal (section 11); implementation audit | both | no | — |
| 6 | Part T freeze; registered run: gates, training, evaluation, analysis, report | both | no | Decision 2 |
| 7 | Timing benchmark (ADR-0022 section 10.2): CPU, six threads, three repetitions, median | CPU | **yes, about 15 minutes**: load average at most 2.0 at the start and end of each repetition *(lead's choice)* | — |
| 8 | Independent recomputation; outcome record | CPU | no | — |

If the condition of stage 7 is not met, the figures are recorded with the measured load and marked NOT ISOLATED; a repetition whose coefficient of variation exceeds 5% is marked UNSTABLE. The stage is not repeated and enters no line.

**Part Q rehearsal, sealed.** It runs the frozen Part Q plan end to end on a rehearsal partition seed with the real teachers, limited to two generation blocks per capability and one Q_check block, with one forced pause and resume. It reports timings, memory, counts and yields. The values of Q1 to Q4 and every per-item score are written to a sealed file and are not displayed or read by the lead before Part Q's outcome is registered. No Part Q setting, threshold or size changes after the rehearsal. Its time is charged to Part Q and counts in P.

Training on MPS is not bit-reproducible; snapshots are the object and every score is recomputed on CPU.

## 11. Engineering requirements carried from P10

1. **Durable data, first.** The P10-S2 downloads and packages sit git-ignored in an agent worktree (section 12). Before any worktree clean-up, the lead copies them to a durable location named by the human lead and verifies every hash. WikiText-2 is not in this worktree either; its path is checked before any step that reads it (P10-S2 attempt 2).
2. **Frozen inputs, stated exactly, one set per part.** Part Q: `studies/p10is2/partq/**`, `configs/p10is2_partq.toml`, the requirements file, the input hashes, the Part Q plan. Part T: `studies/p10is2/**` outside `partq/`, `configs/p10is2_partt.toml`, `uv.lock`, `pyproject.toml`, the Part Q manifest, the plan file and the freeze record. A change of Part T code cannot invalidate a Part Q resume or recomputation. The approved revision of this ADR is recorded by hash in each freeze record and is **not** an input checked at run time. The check compares hashes of the listed files; it does not require a particular HEAD.
3. **Run-time notes** go to the chat or another branch. Nothing is committed in the run worktree while a registered stage is active.
4. **Resumable stages.** Each completed block or cell is recorded atomically. A PAUSED stage continues and completed work is not recomputed. A training cell checkpoints every 500 updates with optimizer and generator state; a resumed cell is marked.
5. **Rehearsal against the frozen plan itself**, for every registered stage of both parts, before its Decision: every cell type, one cell of each trained type at full U, one combined scoring of each arm kind, one forced pause and resume.
6. **Every reading rule is in section 8**, including how cells combine. A rule the analysis needs and section 8 lacks stops the work before the freeze and returns to the human lead.
7. **Reference arm through every validity check.** In the Part T rehearsal, on calibration data, E-table (whose dependence on its vectors is given by construction) is run through the lexical-margin and marker-only conditions, and the evaluable-cell rule and the forgetting-pressure reading are exercised on M-seq and D-seq. A check the reference fails is not used; the specification returns to the human lead before the freeze.
8. **Analysis on a synthetic registry with known answers,** covering every label of sections 8.3 to 8.5, every status, cells that are not evaluable or not challenged, undefined gaps, rejected consolidations, non-finite values and every descriptive table, each against a hand-computed expectation.
9. **Fail fast.** Every fixed-input count is checked before any teacher runs (attempt 4); the applied generation configuration is asserted (attempt 5).
10. **Platform of record:** this machine (macOS on Apple silicon, torch 2.8.0 from the lock), CPU for all scoring. Bit-exact assertions are made on it only. `ruff`, `mypy` and `pytest` run locally; GitHub CI is not relied on.

## 12. Downloads, packages and services

No paid service, account, login or cloud use is needed.

| Item | Size | State | Needs |
|---|---|---|---|
| Teachers A and B, student, Tatoeba exports | 936,320,520 bytes (29 files) | On disk at `.claude/worktrees/agent-a91c79a181109bb9c/data/p10s2-pre-20261115/downloads/`; hashes in `DOWNLOAD_LEDGER.md` and `studies/p10s2/records/tatoeba_session.json`. Seen present on 2026-11-17; not re-hashed for this draft | The durable copy (section 11, item 1) |
| Data-generation packages outside the lock (transformers 4.57.1 and seven companions, hash-pinned) | 126,182,132 bytes | On disk in the same worktree, `data/datagen-packages/` | **The human lead's approval to use them in Part Q.** The earlier approval was for P10-S2's data step |
| WikiText-2 | — | In the main checkout's `data/wikitext2/` and in the agent worktree | Path check |
| Fallback teacher and Spanish Tatoeba files | 315.3 MB + 8.1 MB | **Not on disk** | **The human lead's decision, only if the fallback is invoked** |

The ledger's running total is 1,188,183,868 bytes of 30 GB. That delegation was given for P10, and the human lead recorded that the P10 delegation does not cover P10-I. The Tatoeba exports carry no revision and are regenerated weekly: a lost copy cannot be fetched again byte for byte.

## 13. Open choices reserved for the human lead

1. **Part Q as a separate registered stage, accepted before Part T is frozen.** Recommended: yes.
2. **One teacher qualifies.** Recommended: Part T does not run; the fallback by your decision at that time. Alternative: a one-teacher ACQUISITION-only lane (M1, D1, E-table and the lookup baselines for the qualified capability, about a fifth of Part T's training), with RETENTION NOT EVALUABLE. P10-S2 never tested acquisition; the lane would be the first such measurement, but it does not answer the milestone question.
3. **Q_fit fixed at 2,000.** Recommended: yes (section 4.2). Alternative: 500 for Q3 and 1,000 for Q1 and Q2, as ADR-0022, with teacher B's filter passing only at zero errors.
4. **Population of the Q panels: sentences with both references**, as P10-S2. Recommended: yes, for comparability. The supply is not in the records; it is counted from the corpus before Decision 1 and reported. Alternative: per-capability gold pools, a larger supply and a changed population.
5. **Split of shared sources 4/5 to B; disjoint target 24,000**, with overlapping draws as the written fallback. Recommended: yes.
6. **Kept from your P10 list as descriptive lines:** M-ii, the combined tasks under the strengthened rule, the five cost measures. **Removed:** only TRAINING COST COMPARABLE (a wall-time comparison) and MA-gold with its annotation (the design is teacher-only; the loss is the gold reference point). Alternative: you may remove M-ii or the combined tasks to save cost (section 14).
7. **Forgetting pressure read on M-seq only.** Recommended: yes. Consequence: if the unprotected store does not forget, RETENTION cannot be positive and the milestone is NOT ESTABLISHED.
8. **Oracle addressing only.** Recommended: yes.
9. **Three replicates, both orders, "every cell" rules.** Recommended: yes. A true per-cell pass rate of 0.8 gives six of six with probability 0.26; INCONCLUSIVE should be expected often.
10. **Who may extend an hour cap.** Recommended: the lead, once, to at most twice its value, on recorded cost projections; beyond that, you.
11. **Use of the out-of-lock data-generation packages in Part Q.**
12. **A durable location for the data; and whether the download delegation covers P10-I.**
13. **The two translation directions as the two capabilities, the 135M student, training on MPS, R-gloss-icl as an added baseline.** Recommended: yes.
14. **Independence from P10-I-S0 and S1.** Recommended: this study uses no result of either.

## 14. Cost projection — an estimate, to be replaced by the rehearsals

**Part Q.** Measured in P10-S2 at the default thread count (18 cores): 12.3 ms per source for teacher A and 14.1 ms for B; 0.095 s and 0.36 s per accepted item; both teachers on the 1,000 items of Q (2,000 translations) in 26 s. At six threads generation may be two to three times slower.

| Scenario | Sources A / B | Generation at P10-S2's rate | At six threads (estimate) |
|---|---|---|---|
| Minimum pools (10,000) | 77,000 / 256,000 | about 1.3 h | 2.5–4 h |
| Disjoint target (24,000), if reachable | 185,000 / 615,000 | about 3.0 h | 6–9 h |
| Both split pools to the end | 254,000 / 664,000 | about 3.5 h | 7–10.5 h |

The Part Q rehearsal measures seconds per source at six threads, yield, the shared share of the pools, peak memory and the time of a pause and resume.

**Part T (no student has been trained on this machine).** The one measured anchor: 2,000 greedy answers of the untrained student (two per Q item) took 178 s in P10-S2's data step, about 0.089 s each. Training rates are ADR-0022 section 13.3's operation-count projections, uncertain by about a factor of three.

| Work | Basis | U = 2,000 | U = 8,000 |
|---|---|---|---|
| Training: 42 store-type and 24 LoRA units of U over three replicates | 5–10 and 8–15 min per unit of 2,000 | 7–13 h | 27–52 h |
| Calibration and ladder: 36 units of 2,000 (22 store-type, 14 LoRA) | same | 4–7 h | 4–7 h |
| Scoring: 54 trained cells on both panels; controls, routers, GEN, retrieval | 1.6–5.2 min per cell for the panels; ADR-0022's 0.9–3.0 h per replicate for the rest | 4–14 h | 4–14 h |
| Combined tasks, registered run, three replicates, twelve arm-cells | the addendum's 2.0–7.8 min per arm-cell | 1.2–4.8 h | 1.2–4.8 h |
| Independent recomputation (one repetition of all scoring) | same | 5–19 h | 5–19 h |
| **Total, order of magnitude** | | **about 20–60 h** | **about 40–100 h** |

The addendum's figure for the combined tasks with recomputation is 2.07–8.19 h for three replicates and ten arm-cells; with D-append's two cells it is about 2.5–9.8 h (the lead's arithmetic, not checked). M-ii costs 12 of the 42 store-type units. The Part T rehearsal measures seconds per update of every cell type on MPS, scoring seconds per item of every kind, peak resident and MPS memory, and the gates, analysis and report times.

## 15. Stop rules and NOT EVALUABLE outcomes

- A failed gate or a difference from the freeze stops the run: ENGINEERING-FAILURE. A second attempt needs the human lead's decision. Failed runs and failed checker attempts are kept.
- A resource cap stops a stage as PAUSED; it resumes after the cap is extended under section 9.
- Part T is NOT STARTED if Part Q does not end TEACHERS-QUALIFIED, or on the pilot gate.
- NOT EVALUABLE lines are those of section 8.3. None is read as negative, and each prints the per-cell values behind it.
- Nothing is re-run with changed settings. No result is reported before the recomputation is complete.

## 16. What this study cannot establish

- Anything about learned addressing, routing or overload. Addresses and routes are supplied by rule; a GEN pass means the keyword router stayed silent.
- That the memory is more than a dictionary, unless AGAINST-LOOKUP says so; and then only for lexical translation of short sentences from a 2,000-word vocabulary. Not transfer of a skill.
- Continual learning in general: two teachers, two stages, two capabilities of one kind, one student.
- That retention is an advantage of sparsity or of the memory. Tasks touch different rows because their oracle codes differ; M-append's first-stage rows are frozen by design; separate modules behind a switch retain by construction.
- Superiority over adapters. The store is given the task by rule and LoRA is not; LoRA changes every position and the store writes at source positions only.
- That each training item was correct: the filter has a measured precision.
- Knowledge fusion or composition of capabilities; COMPOSES is descriptive, under routes given by rule.
- Efficiency, latency, storage, capacity scaling, anything about SSD. Counts are not measured efficiency.
- Behaviour with large teachers or students; a success probability (three replicates, one partition, one corpus).
- A failure of the ArborLM concept, whatever the outcome.

## 17. Approval record

None. This revision awaits the reviewer's re-check and the human lead's review. `Astra review: NOT_PERFORMED`.

## 18. Review record

Review: `docs/reviews/p10-i-spec-reviews-2026-11-17/REVIEW_ADR-0025.md`, by the `arbor-auditor` subagent (Opus 5.5), verdict NOT READY on the first draft. Revision: the lead (Claude Fable 5.2). The review is not Astra validation and not human approval.

| Finding | Severity | Disposition | Where |
|---|---|---|---|
| B1 M-ii, combined tasks, cost removed on a wrong reason | BLOCKING | FIXED: restored as descriptive lines; only the wall-time rule and MA-gold removed, with reasons; C1/C2 costed for three replicates | §2, §3 rows 11 and 16–18, §5.2, §5.5, §8.5, §13 item 6, §14 |
| B2 general quality dropped from the positive condition | BLOCKING | FIXED: WITHHELD restored; one table of all changes | §1, §3, §8.4 |
| R1 Q1 and Q2 called unchanged | REQUIRED | FIXED: listed as a change | §3 row 3, §4.2 |
| R2 population of the Q panels; 0.60 cut | REQUIRED | FIXED: both-reference population kept; cut and grid written out | §4.1, §4.2, §13 item 4 |
| R3 sampling risk of Q3 | REQUIRED | FIXED: Wilson table; Q_fit fixed at 2,000 | §4.2, §13 item 3 |
| R4 overlapping source pools | REQUIRED | FIXED: split before generation; projection redone | §4.3 rule 4, §14 |
| R5 optional stopping rules | REQUIRED | FIXED: three rules | §4.3 rules 1–3 |
| R6 Q_check against the source pool | REQUIRED | FIXED: reserve blocked up front; fixed order | §4.1 steps 3–4 |
| R7 Part Q outputs; missing seeds | REQUIRED | FIXED | §4.1 step 8, §6 |
| R8 fallback | REQUIRED | FIXED: both teachers re-qualified; applies to exhaustion; per-teacher status | §4.4 |
| R9 retention failure hidden by NOT EVALUABLE | REQUIRED | FIXED: negative zone read first over evaluable cells; table always printed | §8.3 |
| R10 ρ unguarded; pressure from D-seq; ACQ1 | REQUIRED | FIXED: guard at 0.50; pressure on M-seq as ρ < 0.90; ACQ1 required | §8.1, §8.2, §8.3 |
| R11 open reading points | REQUIRED | FIXED | §8.1–8.3 |
| R12 fairness of D-append | REQUIRED | FIXED: qualifier, D-sep, compute counts, read-layer note | §5.2, §8.3 |
| R13 oracle wording | REQUIRED | FIXED | header, §1, §5.4 |
| R14 Part Q rehearsal reveals quality | REQUIRED | FIXED: sealed subset rehearsal | §10 |
| R15 out-of-lock packages | REQUIRED | FIXED: needs new approval | §12, §13 item 11 |
| R16 engineering failure in Part Q | REQUIRED | FIXED | §4.4 |
| R17 PAUSED as an outcome | REQUIRED | FIXED | §1, §4.4, §8.6 |
| R18 recomputation tolerance; panel minimums | REQUIRED | FIXED | §4.1 step 2, §8.6 |
| A1 lookup baselines | ADVISORY | FIXED: R-gloss-icl; replicate's draw; milestone carries the lookup result | §1, §5.2, §5.3 |
| A2 one-teacher lane | ADVISORY | ANSWERED: offered as an alternative, not recommended | §13 item 2 |
| A3 calibration seeds; 36 units; stage-2 convergence | ADVISORY | FIXED; stage-2 convergence stated as a limit | §6, §7.1, §14 |
| A4 Part Q cap at six threads | ADVISORY | FIXED: cap from the rehearsal | §4.3 rule 7, §14 |
| A5 P10-S1 matched-compute caveat | ADVISORY | FIXED | §2 |
| A6 dropped annotations | ADVISORY | FIXED: restored by citation | §8.5 |
| A7 engineering additions | ADVISORY | FIXED | §4.4, §11 |
| A8 seed convention | ADVISORY | FIXED: initialization and test seeds go to the programme registry | §6 |
| A9 wall time | ADVISORY | FIXED: the timing benchmark has a measured quiet condition | §10 |
| A10 downloads; WikiText-2 location | ADVISORY | FIXED | §11 item 1, §12 |
| Figures: 26 s phase; 36 units; 178 s | — | FIXED | §14 |

Still unverified by the lead: the pool-overlap figures of section 4.3 (the reviewer's bound), the supply of both-reference sentences, and every Part T rate.
