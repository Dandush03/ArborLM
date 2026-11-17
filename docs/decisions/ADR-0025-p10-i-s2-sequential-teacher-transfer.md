# ADR-0025 — P10-I-S2: Sequential teacher transfer

**Status: DRAFT — NOT APPROVED. Nothing under this ADR is implemented, calibrated, frozen or run.**

- **Date:** 2026-11-17 (UTC). **Drafted by:** the lead (Claude Fable 5.2). Independent specification review (Opus 5.5): not yet performed. Human lead's approval: not given.
- **Study code** P10IS2. **Package** `studies/p10is2/` (new files only). **Seed namespace** 250001–259999 (section 6).
- **Predecessor:** P10-S2 (ADR-0022), registered outcome TRANSFER-INCONCLUSIVE: TEACHERS-NOT-QUALIFIED, accepted by the human lead as registered. That outcome is not revised and P10-S2 is not reopened. This is a new study with new seeds.
- **Standing of every result:** oracle-addressed (section 5.4). ArborLM is unproven research; no line of this study is a success claim. `Astra review: NOT_PERFORMED`. Claude review is not Astra review.
- Figures marked *(lead's choice)* are judgment calls fixed here before any observation. None is taken from a paper.

## 1. Question and outcomes

**Question.** Can a frozen pretrained student with an expandable key–value memory acquire a capability from a first pretrained teacher, then a second capability from a second teacher, and still hold the first — and how does that compare with a dense adapter trained the same way, with lookup baselines, and with no memory?

The study has two parts. **Part Q** qualifies the teachers and generates the training material. **Part T** measures transfer. Part Q is finished, recomputed and accepted by the human lead before Part T is frozen.

Six outcome lines. Each is printed separately; none substitutes for another.

| Line | Positive means | Negative means | Inconclusive means |
|---|---|---|---|
| QUALIFICATION (Part Q) | Both teachers meet the quality criteria and the material exists in the required amount | A teacher fails a quality criterion. Says nothing about transfer | Data exhausted, or the stage is PAUSED on a resource cap |
| ACQUISITION | The store learned each capability from teacher output alone, on held-out sentences, and the gain depends on the stored content | The store did not learn a capability within the registered training length | Mixed across replicates or orders, or a control failed |
| RETENTION | The first capability was kept while the second was acquired in the same store, on a task where an unprotected arm does forget | The first capability was lost | Mixed, or no arm forgot (retention was not challenged) |
| AGAINST-DENSE | The store is ahead of the dense adapter trained the same way | The dense adapter is ahead | Not distinguished or mixed |
| AGAINST-LOOKUP | The store is ahead of every lookup and retrieval baseline | A lookup baseline does as well: the result shows nothing a lookup cannot provide | Mixed |
| GENERAL-QUALITY | With a learned keyword router deciding whether the store is read, ordinary English text is not degraded | It is degraded | Not measured |

Milestone question 2 of the P10 direction (sequential acquisition with retention) is printed as "supported, oracle-addressed" only if ACQUISITION and RETENTION are both positive; otherwise "not established". The AGAINST-DENSE and AGAINST-LOOKUP lines are printed directly beneath it, whatever they say.

## 2. Background

| Finding | Record |
|---|---|
| P10-S2 stopped before its freeze. Both teachers passed own score (0.7675, 0.7754 against 0.55) and margin (0.6214, 0.6425 against 0.30). A filter setting passed on Q_fit for both. Point precision on Q_check was 0.9231 (72 of 78) and 0.9545 (21 of 22) against 0.90 | `results/p10s2-datagen-2026-11-16/README.md`, `prefreeze_record.json` |
| The gate failed on counts: accepted Q_check items 78 and 22 against 150; accepted pools 7,804 and 2,341 against 8,000 (7,763 and 2,300 available against the 10,000 the sufficiency rule needs) | same |
| Acceptance on Q_fit was 104 of 500 (20.8%) and 41 of 500 (8.2%). Of 60,000 generation sources per capability, 13.0% (A) and 3.9% (B) were accepted | same; shares computed here from the recorded counts |
| In-vocabulary no-gold sources available: 734,418 (A) and 784,089 (B). Gold pairs outside the panels: 181,970 and 132,151 | `prefreeze_record.json`, `fixed_input_counts` |
| Generation took 740 s (A) and 844 s (B) per 60,000 sources; the whole step 2,100 s, peak resident memory 5,677 MiB | `prefreeze_record.json`, `steps.memory_by_phase` (differences of the recorded elapsed times) |
| The gate's per-item inputs on Q were not stored, so the per-item gate could not be recomputed | `docs/reviews/p10s2-qualification-2026-11-16/REVIEW.md`, finding 1 |
| No student was trained. Nothing about transfer was measured | ADR-0022, addendum of 2026-11-16 |
| P10-S1, oracle addressing: no line positive for the store; DICT DOMINATES ON THIS TASK; DENSE AHEAD; the memory arms ran at an untuned learning rate while the dense arm was calibrated; UNDERTRAINED-AT-U_P | `results/p10s1-run-2026-11-17/OUTCOME.md`, sections 2 and 4 |
| P10-S1: the flat store's mean a_use at the run length was 1.000 at 0.5 facts per slot (2K/4K, 8K/16K) and 0.654 and 0.637 at the loaded cells (8K/1K, 32K/4K) | same, section 4 table |
| P10-S0: learned addressing (arm A5-D) qualified at 4,096 and 16,384 slots at 0.5 facts per slot; OVERLOAD NOT QUALIFIED; the memory is told the answer position; nothing there is about natural language or another backbone | `results/p10s0-run-2026-11-16/OUTCOME.md` |

**One precision on the direction record.** `DIRECTION.md` section 5 says both teachers "passed the quality criteria". The record supports that for own score, margin and the Q_fit rule. The Q_check precision was above 0.90 but was read on 78 and 22 items (95% Wilson lower bounds 0.842 and 0.782), below the 150 the design required for that reading. So filter precision at the registered sample size is not yet established; Part Q measures it.

**Provenance.** The teachers and the corpus are those of P10-S2, whose quality figures have been seen. For own score and margin, Part Q is a confirmatory re-measurement on a new partition, not a blind first test.

## 3. What changes from ADR-0022, and what does not

| Item | ADR-0022 | This study | Why |
|---|---|---|---|
| Teacher qualification | One gate inside the pre-freeze step | Part Q, a registered stage with its own outcome | A count shortfall must not end the study; quality is reported on its own |
| Amount of generation | Fixed: 60,000 sources, 500 Q_check items | Generate until the count is met, within a budget (section 4.3) | `DIRECTION.md` section 5, rule 2 |
| Quality thresholds | 0.55; 0.30; Wilson lower bound 0.90 on Q_fit; point precision 0.90 on at least 150 accepted Q_check items | Unchanged | Scientific thresholds |
| Per-item Q records | Not stored | Stored and hashed | Audit finding |
| Training length | 2,000 or 1,000 updates, chosen by budget | A convergence rule on calibration draws (section 7.1) | P10-S1's UNDERTRAINED-AT-U_P |
| Learning rates | Store fixed at 0.003; LoRA searched | The same three-value search for every trained module type | P10-S1's untuned memory arms |
| Dense comparison of the primary arm | L-seq (one adapter continued) and L-sep (BY CONSTRUCTION) | D-append added: a second adapter with the first frozen, both applied | "Trained the same way": one change per comparison |
| Retention validity | None | Retention is positive only if an unprotected arm forgets | A retention result on a task nothing forgets is empty |
| Replicates | Four or three by budget; overlapping draws | Three; disjoint draws if the pool allows (section 4.3) | Independence of replicates; the hour cap is extendable instead |
| Removed | M-ii (consolidation with replay), MA-gold, combined tasks C1 and C2, the timing benchmark, the cost lines | Not in this study (section 13, item 6) | None bears on acquisition or retention; no wall-time rule is registered on a shared machine |

Unchanged: the student (`HuggingFaceTB/SmolLM2-135M`, frozen), the two teachers (`Helsinki-NLP/opus-mt-en-de`, `opus-mt-en-fr`, at the revisions pinned in ADR-0022 section 4.1), the Tatoeba exports, the memory mechanism (ADR-0022 section 3), the prompts, the address function, chrF-norm, and the definitions of normalization, identity groups, no-gold sources and the 2,000-word closed vocabulary (ADR-0022 sections 5.2, 5.4, 10.1). Where this text is silent, those sections and the rulings in ADR-0022's addenda govern as definitions. They are cited, not edited.

## 4. Part Q — teacher qualification and data generation

### 4.1 Panels

A new partition is built with this study's partition seed. Evaluation panels (E_A, E_B: 1,000 items each; E_open: 500) are built and hashed in Part Q. **No evaluation panel is scored before the registered run of Part T.**

| Panel | Size | Use |
|---|---|---|
| Q_fit^c, per capability c | 500 gold-bearing training-side items | Own score, margin, filter selection |
| Q_check^c | blocks of 500, drawn in a seeded order (section 4.3) | Filter precision |
| D_cal | 500 | Part T calibration and pilot only |
| T_c | accepted teacher outputs on no-gold sources | Student training material |

### 4.2 Quality criteria (scientific thresholds; unchanged from ADR-0022 sections 4.3 and 5.3)

| # | Criterion | Threshold | Reason for the figure |
|---|---|---|---|
| Q1 | Teacher's mean sentence chrF on its own capability, Q_fit | ≥ 0.55 | Above the level at which most short sentences are substantially right; fixed in ADR-0022 before any teacher was run |
| Q2 | Q1's score minus the larger of the other teacher's and the untrained student's score | ≥ 0.30 | The capability must be the teacher's and absent from the student, so that a gap of at least 0.30 exists to close |
| Q3 | A filter setting exists on the grid of ADR-0022 section 5.3 whose 95% Wilson lower bound of precision on Q_fit is ≥ 0.90; the most permissive such setting is taken, ties as registered there | exists | At most one accepted item in ten may be wrong; selecting on the lower bound keeps the setting off its own edge |
| Q4 | Point precision of the chosen setting on Q_check, read on at least 150 accepted items | ≥ 0.90 | The same bar on held items. 150 accepted items give a 95% interval of about 0.84–0.94 at the bar |

The 150 in Q4 is the minimum evidence behind the precision reading. It is kept. What changes is how it is reached (section 4.3).

**Stated risk.** If the filter's true precision is near 0.92, a reading on about 150 items falls below 0.90 by sampling in roughly one run in six. That is a registered quality failure. Q_check is not extended after its precision has been read.

### 4.3 Counts: generate until met, within a budget

None of these counts is a scientific claim. Each is reached under the rule below. The stopping decisions read accept counts only.

| Count | Target | Block | Ceiling | Projected need from P10-S2's yields |
|---|---|---|---|---|
| Accepted Q_check items, per capability | 150 | 500 items | 8,000 items (16 blocks) *(lead's choice)* | A: about 1,000 items at 15.6%; B: about 3,500 at 4.4% |
| Available accepted sources, per capability: minimum | 10,000 (8,000 × 1.25, ADR-0022 section 5.2) | 20,000 sources | the whole source pool | A: about 77,000 sources; B: about 261,000 |
| Available accepted sources: disjoint target | 25,200 (3 × 8,000 × 1.05) *(lead's choice)* | same | the whole source pool | A: about 195,000 sources; B: about 657,000 of 784,089 |

Rules:

1. **Q_check.** Blocks are drawn in a fixed seeded order from the capability's gold pool. After each block the filter is applied and the accepted items are counted; references are not read. Drawing stops at the first block boundary with at least 150 accepted items. Only then is precision computed, once, over every accepted item of every block drawn.
2. **Generation.** Sources are drawn in a fixed seeded order in blocks. After each block the available accepted count is computed by the sufficiency rule of ADR-0022 section 5.2. Generation of a capability stops when the disjoint target is met or its source pool is exhausted.
3. **Disjoint or overlapping draws.** If both capabilities reach 25,200, each replicate's 8,000 items are drawn without overlap between replicates. Otherwise, if both reach 10,000, replicates draw from the whole pool as in ADR-0022 and the shared share is printed beside every line that says "every cell". The choice follows from the counts by this rule and from nothing else.
4. **Exhaustion.** If a ceiling or a pool ends before 150 accepted Q_check items or 10,000 available sources, the outcome is QUALIFICATION-INCONCLUSIVE: DATA-EXHAUSTED for that teacher. No threshold is touched.
5. **Budget.** Part Q has a resource cap of 10 charged hours *(lead's choice)*: generating both whole pools is projected at 5.6 hours from the measured rates (section 14). A stop on the cap or on the memory guard is PAUSED; the stage resumes from the last completed block and completed blocks are not regenerated.
6. **Persistence.** Every per-item input of the gate is stored and hashed: teacher outputs, beam scores, chrF per item on Q_fit and Q_check, the full grid table, and the score of every rejected generation output.
7. **Threads.** P10-S2 found that teacher outputs differ between 2 and 18 CPU threads. Generation runs with six threads, fixed in the configuration and recorded; the digest of a fixed 100-sentence record per teacher is asserted at every resume.

### 4.4 QUALIFICATION outcome (first match wins)

| Order | Label | Rule |
|---|---|---|
| 1 | QUALIFICATION-PAUSED | A resource cap stopped the stage. Not a final outcome |
| 2 | QUALIFICATION-NEGATIVE: QUALITY (teacher named, criterion named) | A teacher fails Q1, Q2, Q3 or the precision of Q4 |
| 3 | QUALIFICATION-INCONCLUSIVE: DATA-EXHAUSTED | Rule 4 of section 4.3, for either teacher |
| 4 | TEACHERS-QUALIFIED (DISJOINT DRAWS / OVERLAPPING DRAWS) | Both teachers pass Q1–Q4 and both pools reach at least 10,000 |

**If only one teacher qualifies.** Part T does not run with one teacher: retention needs two, and a single-teacher result would stand in for a line it cannot answer. The label of row 2 or 3 is registered. The fallback of ADR-0022 section 4.2 (`Helsinki-NLP/opus-mt-en-es`, a different training regime) may replace the failed teacher once, only by the human lead's decision at that time, and it needs a download (section 12). The fallback teacher then passes the whole of Part Q on the same seeds with Spanish in place of the failed language. If it fails, or both primary teachers fail, the study ends with the Part Q label and Part T is NOT STARTED.

Part Q's outcome is recomputed independently from the stored per-item records and returned to the human lead before Part T is frozen.

## 5. Part T — design

### 5.1 Stages of training

Capabilities A (English→German) and B (English→French). Both orders (A then B, B then A) run in every replicate. A **cell** is one (replicate, order) pair: three replicates give six cells per arm. Every stage runs U updates of batch 32 with AdamW, no weight decay, clip 1.0, constant learning rate, fresh optimizer state. Training material is teacher output on sentences with no reference in that language; gold references never train a student.

### 5.2 Arms

N = 4,096 rows per stage (2,424,833 trainable parameters). LoRA rank 42 on the query and value projections of all 30 blocks (2,419,200 parameters), as ADR-0022 section 7.

| Arm | Stage 1 | Stage 2 | What it isolates |
|---|---|---|---|
| S0 (no memory) | — | — | The frozen student alone: the floor of every gap |
| M1 | N rows on teacher 1 | — | Acquisition from one teacher; the single-teacher reference |
| **M-append** (primary) | = M1 | N rows appended; first-stage rows frozen; one top-8 over all 2N rows; trained on teacher 2 | Acquisition of the second capability and retention of the first, in one store with no switch |
| M-seq | = M1 | Same N rows, all trainable, on teacher 2; no growth, no replay | The unprotected store: whether forgetting occurs. Against M-append: the effect of append-and-freeze |
| D1 | LoRA rank 42 on teacher 1 | — | Dense single-teacher reference |
| **D-append** | = D1 | A second rank-42 adapter added; the first frozen; both applied on every task prompt; trained on teacher 2 | The dense adapter trained the same way as M-append. The pair differs in the module only |
| D-seq | = D1 | The same adapter continued on teacher 2 | The dense adapter trained the same way as M-seq |
| M-joint, D-joint | 2N rows / rank 84 on the mixed material, 2U updates | — | What simultaneous training reaches. Descriptive |
| E-table | One trainable 576-vector per (task, word), same positions as the store's reads, no keys | — | A trained dictionary: perfect addressing, no sharing. Each capability; its retention is BY CONSTRUCTION |
| Teachers | — | — | The ceiling of every gap (stored outputs) |

Not trained, scored on the same panels:

| Baseline | Definition | What it isolates |
|---|---|---|
| R-exact | Table from training source to accepted output | Confirms the panels are held out (zero hits required, gate G1) |
| R-gloss | Co-occurrence lexicon from accepted pairs, word by word | A word-level dictionary without learning |
| R-nn | Nearest training source by character-trigram TF-IDF; its output returned | Sentence retrieval without composition |
| R-icl | The four nearest accepted pairs in the frozen student's prompt | Retrieval that can generalize |

Controls on every memory cell, on a fixed 300-item subsample of each panel: memory off; values permuted across rows; word codes permuted across words; marker-only. For a stage-2 store the permutations act on the second stage's rows and the second task's codes.

Two stores or two adapters behind an oracle switch retain exactly. They are assembled and printed **BY CONSTRUCTION** and enter no line.

### 5.3 What transfer is measured on

Every score is on E_A or E_B: sentences on the evaluation side, disjoint in identity groups from every training source, built from the closed vocabulary. Gate G1 requires that no evaluation reference equals a training output and that R-exact has zero hits. **A plain lookup of the generated pairs therefore answers no evaluation item.**

What training and evaluation share is the vocabulary. The test is composition of known words into unseen sentences. A word-level lookup can in principle do this, which is why R-gloss and E-table are in the design and AGAINST-LOOKUP is its own line. The share of evaluation items with a training source at word-level edit distance 1 (0.0816 in P10-S2's partition) is reported, and every score is also printed with those items removed; that second figure enters no rule.

### 5.4 Addressing

**Oracle addressing, as in ADR-0022 section 5.4.** The code of (task, word) is a fixed random unit vector from a seeded hash; the store is read with it at the last subword of each in-vocabulary source word and at the task marker. The read is a flat scan with top-8; no tree and no index.

- Why not P10-S0's qualified interface: A5-D was qualified on the byte backbone, on synthetic facts, with the answer position given. It has no registered behaviour on a 576-wide student or on natural-language prompts. Using it here would test addressing and transfer at once.
- Load: 2,001 codes per task. M-append holds 4,002 codes on 8,192 rows (0.49 per row), the load at which P10-S0 qualified and at which P10-S1's flat store held under oracle addressing. M-seq holds 4,002 codes on 4,096 rows (0.98). No arm is in overload. Those studies used another task and backbone; the comparison of loads is context, not evidence.
- **What this restricts.** Every label, table and summary line carries: "ORACLE-ADDRESSED (word-level addresses supplied by rule); lexical translation of short closed-vocabulary sentences; two capabilities of one kind; frozen English student; not autonomous learned memory." The analysis refuses to write a line without it. Nothing here bears on learned addressing, routing quality or overload.
- A learned-addressing lane is not part of this specification. It would be a separately approved supplement after P10-I-S0.

### 5.5 General quality under a learned keyword router

As ADR-0022 sections 5.4 and 6.4 with the rulings C-M6, m9 and the addendum of 2026-11-16: a three-key router (A, B, none) trained with route labels decides at token 64 whether the store is read; the panel is the 44 marker-like and 100 ordinary windows of WikiText-2 validation, weighted one half each; the loss is read under both decision positions. Under the oracle route general text is bit-identical to the student and counts for nothing.

## 6. Seeds

| Use | Seeds |
|---|---|
| Registered replicates | bases 250001, 250101, 250201; offsets +0 stage-1 store, +1 training draw, +2 batch order, +3 router, +4 permutation controls, +6 appended rows, +7 M-joint, +8 LoRA (stage 1), +9 E-table, +10 code hash, +11 second adapter of D-append |
| Partition side (Part Q) | 250901 partition; 250902 Q_fit; 250903 Q_check block order; 250904 source block order; 250905 control subsample; 250906 GEN ordinary windows; 250907 bootstrap intervals (analysis only); 250908 teacher tokenizer record |
| Calibration | 251001–251999 |
| Rehearsal (Part Q and Part T) | 252001–252999 |
| Tests | 259001–259999 |

Every generator is seeded directly by a listed seed through one function that records the seed and its purpose and refuses any other. No seed is derived by hashing or arithmetic beyond the listed offsets. Gate G9 asserts, on planned and on recorded seeds, that all lie in 250001–259999 and in the set of their stage. The namespace overlaps none listed for P9 to P10 in ADR-0021 section 6.3 and ADR-0022 section 9 (P10-S0 200001–209999, P10-S1 210001–219999, P10-S2 220001–229999, and the smaller ranges listed there). The lead has not re-derived the P1–P8 lists, and has not compared the namespace with the other P10-I drafts; G9 checks the earlier studies from those sections, and the specification review is asked to confirm both.

## 7. Calibration, pilot and gates (before the Part T freeze; calibration seeds; D_cal only)

### 7.1 Calibration

1. **Rates.** For each of store, LoRA and E-table: learning rate ∈ {0.001, 0.003, 0.01} for the store and E-table, {0.0001, 0.0003, 0.001} for LoRA *(lead's choice; each grid is three values around the ADR-0022 value)*, a stage 1 of 2,000 updates on each capability. The rate with the higher mean chrF on D_cal over the two capabilities is taken; a difference below 0.01 goes to the smaller rate. The store's read layer L ∈ {4, 12} is chosen the same way at the chosen rate.
2. **Training length (design ceiling with a rule).** With the chosen settings, M1 and D1 are trained on each capability with snapshots at 1,000, 2,000, 4,000 and 8,000 updates. U is the smallest rung u in {1,000, 2,000, 4,000} such that, for both module types and both capabilities, chrF on D_cal at 2u exceeds chrF at u by less than 0.01. If no rung qualifies, U = 8,000 and every Part T line carries NOT CONVERGED AT U. One U serves every arm and stage.
3. Calibration scores are never reported as results.

### 7.2 Pilot gate

At the calibrated settings, on D_cal: if M1's gap closed is below 0.25 for either capability, Part T is **NOT STARTED: PILOT** and the work returns to the human lead. No registered seed has then been used.

### 7.3 Gates

G1 partitions and zero R-exact hits; G2 repeat-scoring identity of the student and the stored teacher outputs; G4 determinism on CPU, snapshot round trip, gradient reach (frozen rows, frozen first adapter and the student receive no gradient); G5 route "none" is bit-identical to the student, and appended rows with gate 0 contribute nothing through their values; G6 addresses and routes take the prompt only; G7 frozen bytes; G8 student equivalence; G9 seeds. Definitions as ADR-0022 section 12.3. A failed gate stops the run with ENGINEERING-FAILURE.

## 8. Rules that turn measurements into labels

All rules read the final snapshot of each stage. Intermediate snapshots (U/4, U/2) are descriptive and enter no rule.

### 8.1 Quantities, per cell

- s_c(X): mean chrF-norm of arm X on E_c (maximum over references per item).
- Gap closed: G_c(X) = (s_c(X) − s_c(S0)) / (s_c(teacher c) − s_c(S0)). Defined only if the denominator is ≥ 0.30.
- "First" and "second" are the capabilities in the cell's training order. V1 is the stage-1 snapshot (M1 or D1) of the same cell.
- **Forgetting.** F(X) = s_first(V1) − s_first(X after stage 2). Retained share ρ(X) = G_first(X after stage 2) / G_first(V1).
- **Append cost.** The change of s_first at the append, before any update. Reported; enters no rule.

### 8.2 Cell-level conditions

| Condition | Rule | Reason for the figures |
|---|---|---|
| ACQ1 | G_first(M1) ≥ 0.50; G − max(G_value-permuted, G_code-permuted) ≥ 0.30; G_marker-only ≤ 0.25 | Half the gap is the least that can be called acquisition. The margin of 0.30 requires that most of that half comes from the stored content at its addresses. The marker alone may carry at most half of the minimum gain |
| ACQ2(X) | G_second(X) ≥ 0.50 and ≥ 0.80 × G_second of the single-teacher module of the same type in the same replicate; for memory arms the same margin and marker-only limits | A second capability worth four fifths of what one teacher alone gives |
| RET(X) | F(X) ≤ 0.03 and ρ(X) ≥ 0.90. Read only if G_second(X) ≥ 0.50; otherwise the cell is RETENTION NOT CHALLENGED | 0.03 chrF is about 2.5 times the 95% half-width of a 1,000-item panel mean (0.012 at a standard deviation of 0.2, ADR-0022 section 5.2). Losing more than a tenth of what was acquired is not retention. An arm that learned nothing new retains trivially |
| Negative zones | Acquisition: G < 0.25. Retention: ρ < 0.70 | Half the acquisition bar; a loss of three tenths or more |
| Forgetting pressure | M-seq fails RET in at least 4 of 6 cells, or D-seq fails RET in at least 4 of 6 cells (cells NOT CHALLENGED do not count as failing) | A validity condition, not a claim: a majority of cells showing that the task can be forgotten *(lead's choice)* |

### 8.3 Lines (first match wins within each line; "every cell" means all six)

**ACQUISITION**

| Order | Label | Rule |
|---|---|---|
| 1 | NOT EVALUABLE | A gap is undefined on E_A or E_B, or a registered cell or control record is missing |
| 2 | ACQUISITION-INCONCLUSIVE: CONTROL-FAILED | A value or code permutation gives G ≥ 0.50 in any cell |
| 3 | ACQUISITION-NEGATIVE (FIRST TEACHER / SECOND TEACHER) | G_first(M1) < 0.25 in every cell / G_second(M-append) < 0.25 in every cell |
| 4 | ACQUISITION-POSITIVE | ACQ1 and ACQ2(M-append) pass in every cell |
| 5 | ACQUISITION-INCONCLUSIVE | Otherwise; the count of passing cells per order is printed |

**RETENTION**

| Order | Label | Rule |
|---|---|---|
| 1 | NOT EVALUABLE | G_first(M1) < 0.50 in any cell (nothing to retain), or an undefined gap or missing record |
| 2 | RETENTION-NEGATIVE: FORGETTING | ρ(M-append) < 0.70 in every cell |
| 3 | RETENTION-INCONCLUSIVE: NOT CHALLENGED | M-append is RETENTION NOT CHALLENGED in any cell, or forgetting pressure is absent |
| 4 | RETENTION-POSITIVE | RET(M-append) passes in every cell |
| 5 | RETENTION-INCONCLUSIVE | Otherwise |

**AGAINST-DENSE.** Two paired comparisons, each in every cell: M-append against D-append (primary) and M-seq against D-seq (printed beside it, descriptive). Two quantities: ΔG = G_second(memory) − G_second(dense), and Δρ = ρ(memory) − ρ(dense). For each quantity of the primary pair: MEMORY AHEAD if Δ ≥ +0.05 in every cell; DENSE AHEAD if Δ ≤ −0.05 in every cell; NOT DISTINGUISHED if |Δ| < 0.05 in every cell; MIXED otherwise. The line prints both quantities, for example "acquisition: DENSE AHEAD; retention: NOT DISTINGUISHED". 0.05 is just above the precision of a gap closure on 1,000 items (about 0.04, ADR-0022 section 5.2). A cell where either arm is RETENTION NOT CHALLENGED makes the retention quantity NOT EVALUABLE.

**AGAINST-LOOKUP.** For each cell and capability, b is the best score among R-gloss, R-nn, R-icl and E-table on that panel. LOOKUP SUFFICES if b ≥ s(M-append) − 0.03 on both capabilities in every cell. MEMORY ADDS OVER LOOKUP if s(M-append) − b ≥ 0.05 on both capabilities in every cell. MIXED otherwise. The baseline that gave b is named, and the line says whether it was the trained table or an untrained retrieval.

**GENERAL-QUALITY.** PRESERVED if, for M-append's stage-2 snapshot in every cell and under both decision positions, the loss increase over the unmodified student is ≤ 0.02 nats per token. NOT PRESERVED if it exceeds 0.02 in any cell. NOT MEASURED if a record is missing. A pass is described as "the keyword router stayed silent".

### 8.4 Study status

ENGINEERING-FAILURE: a failed gate, a hash mismatch, a difference between frozen and running inputs, or a recomputation difference that changes any condition or line. INCOMPLETE: a registered cell has no record after the run has ended; no line is derived from a reduced denominator. PAUSED: a resource cap stopped a stage; not an outcome.

## 9. Limits (DIRECTION.md section 5)

| Limit | Kind | Rule |
|---|---|---|
| Part Q charged hours: 10 | Resource cap | PAUSED and resumable. Extended on cost projections only |
| Part T charged hours: P + 2R, computed by the code from the rehearsal record and shown to the human lead at Decision 2 | Resource cap | PAUSED and resumable. Extended on cost projections only, never on an outcome value; every planned cell still runs |
| Memory guard: 12 GiB per worker in Part Q (measured peak 5.7 GiB; P10-S2's guard of 8 GiB stopped attempts 6 and 7), 8 GiB per worker and 24 GiB aggregate in Part T | Resource cap | PAUSED; raised only on measured memory |
| Generation sources; Q_check items | Design ceiling | Generate until met (section 4.3); ceilings are the source pool and 8,000 items |
| Training length U | Design ceiling | Convergence rule (section 7.1); top rung 8,000, then NOT CONVERGED AT U is printed |
| Replicates (3), rows per stage, vocabulary, panel sizes | Design, fixed | Not extended. More replicates would be a new specification |
| Q1–Q4 | Scientific threshold | Never relaxed. Q_check is not extended after its precision is read |
| ACQ, RET, negative zones, forgetting pressure, 0.05 and 0.03 margins, 0.02 nats, pilot 0.25 | Scientific threshold | Never relaxed |

No limit is extended because a partial result looks close.

## 10. Stages, machine load, order of work

The machine is also the human lead's working computer. **No registered rule of this study reads wall time**, so no stage needs a quiet machine for validity. Load affects cost only; the load average is recorded at the start and end of every stage.

| # | Stage | Device | Quiet machine | Human gate before it |
|---|---|---|---|---|
| 1 | Implementation and tests on synthetic stand-ins; implementation audit | CPU | no | approval of this specification |
| 2 | Part Q rehearsal on rehearsal seeds, end to end against the frozen Part Q plan, including one pause and resume | CPU, six threads | no | — |
| 3 | Part Q freeze; registered Part Q; independent recomputation | CPU | no | Decision 1 |
| 4 | Calibration, convergence rule, pilot | MPS training, CPU scoring | no | acceptance of Part Q's outcome |
| 5 | Part T rehearsal (section 11); implementation audit | both | no | — |
| 6 | Part T freeze; registered run: gates, training, evaluation, analysis, report | both | no | Decision 2 |
| 7 | Independent recomputation of every score on CPU from snapshots; outcome record | CPU | no | — |

Training on MPS is not bit-reproducible; snapshots are the object and every score is recomputed on CPU. If MPS memory pressure from other work stops a cell, the stage is PAUSED.

## 11. Engineering requirements carried from P10

1. **Frozen inputs, stated exactly.** `studies/p10is2/**`, `configs/p10is2_*.toml`, `uv.lock`, `pyproject.toml`, the data manifest, the plan file and the freeze record. The approved revision of this ADR is recorded in the freeze record by hash and is **not** a frozen input checked at run time. The freeze check compares the hashes of the listed files; it does not require a particular HEAD or a clean tree outside them.
2. **Run-time notes** go to the chat or to another branch. Nothing is committed in the run worktree while a registered stage is active.
3. **Resumable stages.** Every registered stage records each completed block or cell atomically. A PAUSED stage continues; completed cells are not recomputed. A training cell checkpoints every 500 updates with optimizer and generator state; a cell resumed from a checkpoint is marked as such in its record.
4. **Rehearsal against the frozen plan itself.** Every registered stage of Part Q and Part T is run end to end from the frozen plan file on rehearsal seeds before its Decision, with every cell type, one cell of each trained type at full U, and one forced pause and resume. Tests on a different plan do not stand in for this.
5. **Every reading rule is in section 8**, including how cells combine. A rule the analysis needs and section 8 lacks stops the work before the freeze and returns to the human lead as an amendment.
6. **Reference arm through every validity check.** In the rehearsal, on calibration data, E-table (whose dependence on its word vectors is given by construction) is run through the lexical-margin and marker-only conditions, and M-seq and D-seq through the forgetting-pressure reading. A check the reference fails is not used; the specification returns to the human lead before the freeze.
7. **Analysis on a synthetic registry with known answers,** covering every label of section 8.3, every status of 8.4, missing cells, NOT CHALLENGED cells, undefined gaps and non-finite values, and every descriptive table of the report, each compared with a hand-computed expectation.
8. **Platform of record:** this machine (macOS on Apple silicon, torch 2.8.0 from the lock), CPU for all scoring. Bit-exact assertions are made on it only. Checks (`ruff`, `mypy`, `pytest`) run locally; GitHub CI is not relied on for this study.

## 12. Downloads and services

No paid service, account, login or cloud use is needed.

| Item | Size | State | Approval |
|---|---|---|---|
| Teachers A and B, student, Tatoeba exports (seven files) | 936,320,520 bytes | On disk at `.claude/worktrees/agent-a91c79a181109bb9c/data/p10s2-pre-20261115/downloads/`, verified against the hashes in `DOWNLOAD_LEDGER.md` and `studies/p10s2/records/tatoeba_session.json` at P10-S2's run. The directory was seen present on 2026-11-17; the files were not re-hashed for this draft | None needed while present |
| Data-generation packages (transformers 4.57.1 and companions, hash-pinned) | 126,182,132 bytes | On disk in the same worktree, `data/datagen-packages/` | None needed while present |
| WikiText-2 | — | On disk (`data/wikitext2/`) | None |
| Fallback teacher `opus-mt-en-es` and Spanish Tatoeba files | 315.3 MB + 8.1 MB | **Not on disk** | **The human lead's decision, only if the fallback is invoked** |

The ledger's running total is 1,188,183,868 bytes of the 30 GB the standing delegation allows. That delegation was given for P10; whether it extends to P10-I is item 11 of section 13.

**Risk.** The data sit in a git-ignored directory of an agent worktree that a clean-up could remove. The Tatoeba exports carry no revision and are regenerated weekly: a lost copy cannot be fetched again byte for byte, and a new export would be a new corpus under new hashes. Moving the files to a durable location needs the human lead's word (item 10).

## 13. Open choices reserved for the human lead

1. **Part Q as a separate registered stage, accepted before Part T is frozen.** Recommended: yes.
2. **One teacher qualifies.** Recommended: Part T does not run with one teacher; the fallback may be invoked once by your decision at that time.
3. **Generation budget.** Recommended: ceilings at the whole source pool and 8,000 Q_check items; Part Q cap 10 hours.
4. **Disjoint replicate draws** (target 25,200 per capability, about 84% of B's source pool at P10-S2's yield) with the overlapping design as the written fallback. Recommended: yes. Alternative: overlapping draws from 10,000, as ADR-0022.
5. **Q_fit stays at 500 items.** Recommended: yes, so that only the count rule changes. A larger Q_fit would let the same Wilson bar admit a more permissive filter and raise yield, at the price of a filter closer to the 0.90 edge.
6. **Removed from the predecessor:** M-ii, MA-gold, combined tasks C1 and C2, timing benchmark, cost lines. Recommended: remove. You strengthened the COMPOSES rule in P10-S2; if you want composition measured, it returns as a descriptive lane under the ADR-0022 addendum's text, at an unmeasured scoring cost the addendum projected at 3 to 12 hours for four replicates.
7. **Oracle addressing only.** Recommended: yes; learned addressing as a later supplement.
8. **Three replicates, both orders, "every cell" rules.** Recommended: yes. A true per-cell pass rate of 0.8 gives six of six with probability 0.26; INCONCLUSIVE should be expected often.
9. **Who may extend an hour cap.** Recommended: the lead may raise a cap once, to at most twice its value, on cost projections recorded in the ledger; anything beyond returns to you.
10. **A durable location for the downloaded data.**
11. **Whether the standing download delegation (under 30 GB) covers P10-I.**
12. **The two translation directions as the two capabilities, the 135M student, and training on MPS,** each accepted for P10-S2. Recommended: carry over, with section 16's limits.
13. **Independence from P10-I-S0 and S1.** Recommended: this study uses no result of either and need not wait for them.

## 14. Cost projection — an estimate, to be replaced by the rehearsals

**Part Q (grounded in P10-S2's measurements).** 12.3 ms per source for teacher A and 14.1 ms for teacher B; 0.095 s and 0.36 s per accepted item; teachers on 1,000 Q items in 26 s. P10-S2 ran at the machine's default thread count; six threads may be slower.

| Scenario | Sources A / B | Generation | With partition, checks and tokenization |
|---|---|---|---|
| Minimum pools (10,000) | 77,000 / 261,000 | about 1.3 h | about 2 h |
| Disjoint target (25,200) | 195,000 / 657,000 | about 3.2 h | about 4 h |
| Both whole pools | 734,418 / 784,089 | about 5.6 h | about 6.5 h |

The Part Q rehearsal measures: seconds per source at six threads, yield on the rehearsal partition, peak memory with the larger stored records, and the time of a pause and resume.

**Part T (not measured anywhere).** No student has been trained on this machine. The only measured anchor is 178 s for the untrained student's greedy answers on Q in P10-S2's data step (1,000 items; whether one or two prompts per item was not verified for this draft). The training rates below are ADR-0022 section 13.3's operation-count projections, stated there as uncertain by about a factor of three.

| Work | Basis | U = 2,000 | U = 8,000 |
|---|---|---|---|
| Training: 30 store-type and 24 LoRA units of U over three replicates | 5–10 and 8–15 min per unit of 2,000 | 6–11 h | 23–44 h |
| Calibration and convergence ladder (about 30 units of 2,000) | same | 3–7 h | 3–7 h |
| Scoring: 48 trained cells on both panels, controls, routers and GEN, retrieval baselines | 1.6–5.2 min per cell for the panels | 4–10 h | 4–10 h |
| Independent recomputation (one repetition of scoring) | same | 4–10 h | 4–10 h |
| **Total, order of magnitude** | | **about 20–40 h** | **about 35–70 h** |

The Part T rehearsal measures: seconds per update of every cell type on MPS at full size, scoring seconds per item of every kind, peak resident and MPS memory, and the gates, analysis and report times. R and the cap follow from those figures by code, not by typing.

## 15. Stop rules and NOT EVALUABLE outcomes

- A failed gate or a difference from the freeze stops the run: ENGINEERING-FAILURE. A second attempt needs the human lead's decision. Failed runs and failed checker attempts are kept.
- A resource cap stops a stage as PAUSED. It resumes after the cap is extended under section 9.
- Part T is NOT STARTED if Part Q does not end TEACHERS-QUALIFIED, or on the pilot gate.
- NOT EVALUABLE lines are listed in section 8.3. A line that is NOT EVALUABLE is printed as such and is never read as negative.
- Nothing is re-run with changed settings. No result is reported before the recomputation is complete.

## 16. What this study cannot establish

- Anything about learned addressing, routing or overload. Addresses are supplied by rule.
- That the memory is more than a dictionary, unless AGAINST-LOOKUP says so; and then only for lexical translation of short sentences from a 2,000-word vocabulary.
- Continual learning in general. Two teachers, two stages, two capabilities of one kind, one student.
- That retention is an advantage of sparsity. Tasks touch different rows because their oracle codes differ, and M-append's first-stage rows are frozen by design; what is tested is retention against crosstalk in a shared top-8.
- Superiority over adapters. LoRA changes every position and the store writes at source positions only; the comparison is with "the existing alternative", not a matched mechanism.
- That each training item was correct. The filter has a measured precision; items are not checked one by one.
- Efficiency, latency, storage, capacity scaling or anything about SSD. No cost line is registered, and logical counts are not reported as measured efficiency.
- Behaviour with large teachers or students.
- A success probability: three replicates on one partition of one corpus.
- A failure of the ArborLM concept, whatever the outcome.

## 17. Approval record

None. This draft awaits the independent specification review and the human lead's review. `Astra review: NOT_PERFORMED`.
