# ADR-0022 — P10-S2: Two-teacher sequential knowledge transfer into expandable learned memory

- **Status: DESIGN REVISION 2 — NOT YET CONFIRMED. SPEC: PENDING ASTRA REVIEW. Nothing is implemented, downloaded, installed or run.**
- **Date:** 2026-11-15 (UTC)
- **Origin.** The human lead's P10 direction, milestone question 2: "Can ArborLM sequentially acquire complementary capabilities from two pretrained teacher models while preserving earlier capabilities?"
- **Decision that stays with the human lead.** This design uses two translation directions (English→German, English→French) as the two capabilities. They are two capabilities of one kind. **Whether that satisfies "complementary capabilities" is the human lead's decision, not the lead's** (§16).
- **Study code** P10S2. **Package** `studies/p10s2/`. **Seed namespace** 220001–229999 (§9).
- **Roles (study-specific).** Lead: Claude Fable 5.2. Specification audit, implementation audit and recomputation: Opus 5.5, in contexts separate from implementation, receiving code and records and not the lead's conclusions. Implementation: Sonnet 5.5. Inventory: Haiku 5.5. The model that actually ran each delegated task is recorded from session metadata. ADR-0012 stays not approved. **Astra review: NOT_PERFORMED.**
- **Relation to other work.** S2 is one of three independent P10 experiments (S0 addressing, S1 capacity, S2 transfer). It does not wait for S0 and uses no result of S0 or S1. Its label is independent of CAPACITY-POSITIVE and SYSTEM-POSITIVE. P1–P9 code, records and ADRs are not edited.
- **Evidence it rests on.** P9-I (ADR-0017 Part I): oracle-addressed memory stores and returns answers; every learned query interface collapsed onto 1–6 slots (`results/p9i-run-attempt2-2026-11-15/OUTCOME.md`). No registered evidence exists on incremental learning or teachers. The specification review of revision 1 (`adr-0022-review/REVIEW.md`, Opus 5.5) and its two synthetic probes are review evidence, not registered results.

Numbers marked *(lead's choice)* are judgment calls.

## Revision history

| Revision | Date | Status | Change |
|---|---|---|---|
| 1 | 2026-11-14 | reviewed: NOT READY (B1–B3, M1–M10, 15 minors) | first draft |
| 2 | 2026-11-15 | not yet confirmed | primary arm is now one appended store with frozen rows; training material is teacher output on sentences without gold; data from the Tatoeba project's own exports; teachers isolated in a pre-freeze data-generation step, registered path on the locked environment only; smaller per-replicate matrix with four replicates; controls, labels and scope words as ruled. §19 maps every finding to its change. |

## 0. Frank assessment before the design

1. **The demonstration is narrow.** A sparse key–value memory with controlled addresses is a lookup table. It carries a capability only through units that recur between training and held-out items. The word-level address used here *is* the lexical segmentation: the hand-written address supplies part of the structure of the task. A hand-written address could supply units for a procedural task too (for example digit pair and carry), but then the address would encode the algorithm. A positive result here would show transfer of *lexical knowledge used compositionally by a frozen student*, not transfer of a skill.
2. **What is by construction is not counted.** With oracle routes, general-language quality on ordinary text is bit-exact, and a separate frozen store behind a switch retains exactly. Neither satisfies any label row (§11). Retention is tested in a store where it can fail (§6.3).
3. **The existing alternatives are strong and may win.** Separate adapters behind a switch, a plain word-vector table, a co-occurrence lexicon and retrieved demonstrations can all do this task. S2 measures them and prints the comparison with the label. S2 cannot show superiority.
4. **The teacher must be the only source of the target language.** Revision 1 trained on teacher outputs that equalled gold references, which made the teachers replaceable by the corpus. Revision 2 trains on teacher outputs for English sentences that have no reference in that language. The price is that correctness of each training item is no longer checked against gold; it is checked by a filter whose precision is measured on gold-bearing sentences (§5.3).
5. **Risk of an uninformative negative.** The student is an English model. Whether it can emit German and French from lexical vectors injected at one layer is unknown. The pilot gate tests both languages before the freeze (§12.2).
6. **The budget may not hold four replicates.** The projection (§13) fits the cap with 2× headroom only at the fast end of an unmeasured throughput estimate. The rehearsal rule decides; it can end in "not started".

## 1. Question and hypotheses

**Can a frozen pretrained student with an expandable sparse memory acquire, one after the other, two lexical capabilities from two pretrained teachers, keeping the first when the second is added to the same store, when addresses are controlled?**

- **H22-A (acquisition).** A memory trained on Teacher 1's filtered outputs closes at least half of the teacher–student gap on held-out items; the gain disappears when values or word codes are permuted and is not carried by the task-marker read alone.
- **H22-B (additional acquisition).** Appending new rows to the same store and training them on Teacher 2's outputs, with the old rows frozen, closes at least half of the gap on the second capability and reaches at least 0.80 of a single-teacher student.
- **H22-C (retention in a shared store).** The first capability stays within 0.03 chrF after the append and the second stage, although its reads can now select the new rows.
- **H22-D (retention under modification).** Continued training of all rows with replay and a retention constraint keeps the first capability while changing its rows by at least 0.10 in relative norm.
- **H22-E (sparsity and retention).** Sequential training in one sparse store with task-agnostic codes forgets less than a parameter-matched dense adapter.
- **H22-F (order).** H22-A to H22-C hold in both orders.

Each can fail. The reviewer's probe makes H22-C a real question: with random 16-dimensional codes and idealized keys, appending N rows moved 22–27% of the weight of every first-capability read onto the new rows, and 89–97% of those reads touched a new row, before any training of the new rows (`adr-0022-review/scripts/shared_store_interference.out.txt`; synthetic vectors, an order-of-magnitude argument).

## 2. The student

**Adopted: a small pretrained student, frozen.**

| Item | Value | Verified |
|---|---|---|
| Repository, revision | `HuggingFaceTB/SmolLM2-135M` @ `93efa2f097d58c2a74874c7e644dbc9b0cee75a2` | Hub API, by drafter and reviewer; not gated |
| License | Apache-2.0 | Hub API |
| Parameters | 134,515,008, stored BF16 | Hub metadata; recomputed from the configuration by the reviewer |
| Weights | `model.safetensors`, 269,060,552 B, SHA-256 `80521b40281d6ce74e35c9282c22539e75aa0ac8578892b2a59955ef78d55da1` | Hub tree API |
| Architecture | `LlamaForCausalLM`: 30 blocks, width 576, 9 heads, 3 key–value heads (grouped-query attention), intermediate width 1,536, vocabulary 49,152, 8,192 positions, rotary base 100,000, tied embeddings | pinned `config.json`, read by the reviewer |

- **The registered path runs on the locked environment only** (torch 2.8.0, no other package). The student is implemented in torch inside `studies/p10s2/` as a plain Llama-style decoder and loaded from a plain torch file produced once by the data-generation step (§14.2). **No student parameter is trained in any memory arm.**
- **Tokenization without a tokenizer package.** The data-generation step tokenizes, with the reference tokenizer, every text segment the study uses: each source sentence, each reference, each teacher output, each general-text window, and the fixed template pieces. A model input is defined as the concatenation of segment token ids. The registered path never encodes text; it decodes generated ids with a small pure-Python byte-level decoder that is checked against the reference decoder in the data-generation step.
- **Cost of this choice.** A third model to download; a student implementation and a decoder that must be proven equivalent to the reference; the memory generalized to width 576; training on MPS (§15).
- **Why not the 27,392-parameter byte backbone with teachers reduced to symbol tables.** It would repeat P9-I's oracle rungs with a model's name attached and has no general-language quality to preserve. It would not answer the milestone question.

## 3. The memory, generalized in width

Kept from the project's mechanism (ADR-0017 §5.1): cosine keys, key width 16, top-8 sparse read, read temperature 0.2, addition to the residual stream, oracle codes as in rung R1.

**Departures, listed:**

- No output projection: a value has the student's width d = 576 and is added directly.
- No learned query: the query is the oracle code (§5.4).
- The gate is a linear scalar with initial value 0, in place of P9's `sigmoid(gate)` with initial value −2.0 (`studies/p9/model.py`). The zero gate makes a new store, and newly appended rows, contribute nothing until trained (gate G5).
- Values are initialized from a normal distribution with standard deviation 0.02 *(lead's choice)*, never at zero: with gate 0 and values 0 both gradients vanish.
- **One gate per stage.** Rows written in stage k share gate g_k. Freezing a stage's rows freezes its keys, values and gate.

Definition. A store has rows s = 1…S with keys k_s ∈ R^16, values V_s ∈ R^d and stage index σ(s). For a unit query q: a_s = q·k_s/‖k_s‖; the 8 largest are selected, ties broken by the lowest row index; weights w = softmax(a/0.2) over the selected; r = Σ w_s · g_σ(s) · V_s, added to the output of block L at the read position. N = 4,096 rows per stage *(lead's choice)*; trainable parameters per stage N·(16 + 576) + 1 = 2,424,833. L is fixed by calibration from {4, 12} *(lead's choice)*.

- **Reference test.** On shared inputs the selection and weights equal those of the P9 flat memory forward, imported read-only.
- **Addresses are fixed, not well separated.** In the reviewer's idealized probe only 0.50–0.59 of a read's weight lands on a word's own rows (`scripts/shared_store_interference_2.out.txt`). Training can compensate through the values because rows outnumber units. A failure is therefore a failure of storing, mixing or retaining values under fixed addresses; it is not excluded that address overlap contributes.
- **Version store.** Every store state is an immutable snapshot with manifest and content hash. A reader pinned to an earlier version is unaffected while a later one is prepared; rollback is the pinning of the earlier manifest. Engineering property, tested; not a result.

## 4. Capabilities and teachers

### 4.1 Primary pair

| | Capability A | Capability B |
|---|---|---|
| Task | English → German, short sentences | English → French, short sentences |
| Teacher, revision | `Helsinki-NLP/opus-mt-en-de` @ `6183067f769a302e3861815543b9f312c71b0ca4` | `Helsinki-NLP/opus-mt-en-fr` @ `dd7f6540a7a48a7f4db59e5c0b9c42c8eea67f18` |
| License | CC-BY-4.0 | Apache-2.0 |
| Weights | `pytorch_model.bin`, 297,928,209 B, SHA-256 `da068344b1b0c20e6d4a8f77f48e06646b90d679029006b18579e68977206bdd` | `pytorch_model.bin`, 300,827,685 B, SHA-256 `cc1de10b49342ad2f33e06bc4474ddd6eaca278474903c4a8636ce15680d64de` |
| Parameters | 73,944,309 (plus 524,288 positional buffers) | 74,669,178 |
| Training regime | OPUS, 2020-02-26 release | same |

Parameter counts are the reviewer's arithmetic from the configurations, not counts from the weights; they are counted at load.

- **Why this pair.** Each teacher has one capability and cannot produce the other's language. Both run on CPU. Held gold references exist for measuring them.
- **Contamination, stated.** Both teachers were trained on OPUS, which includes Tatoeba. They may have seen evaluation sentences. This raises the teacher's score, which enlarges the gap the student must close; it does not help the student. The report states it.
- **Weight format.** `main` has no safetensors file. It has a pickle file, a Flax msgpack and a TensorFlow h5 (and `rust_model.ot` for German); unmerged conversion-bot pull requests carry safetensors. The pickle is used: SHA-256 checked, then `torch.load(weights_only=True)` once, offline, inside the data-generation step (§14.2).
- **Tokenizer gate.** The German teacher's `tokenizer_config.json` lacks `model_max_length` and relies on library internals. The data-generation step records the teacher token ids of 100 fixed sentences per teacher; the record is frozen and any later teacher run must reproduce it.

### 4.2 Fallback, fixed now

If one teacher fails §4.3, it is replaced once by `Helsinki-NLP/opus-mt-en-es` @ `5bc4493d463cf000c1f0b50f8d56886a392ed4ab` (Apache-2.0; `pytorch_model.bin` 312,087,523 B; 77,484,009 parameters). **It is a Tatoeba-Challenge model (opus-2020-08-18), a different training regime from the primary pair; a fallback pair would mix regimes, and the report would say so.** If the fallback pair fails, or both primary teachers fail, the study stops with TRANSFER-INCONCLUSIVE: TEACHERS-NOT-QUALIFIED. The fallback's files are fetched only if it is invoked and approved (§14.1).

### 4.3 Teacher qualification gate (before the freeze and before any registered student training)

On panel Q (1,000 gold-bearing training-side items with German and French references), with s = mean sentence chrF against the best reference (§10.1):

1. Each teacher on its own capability: s ≥ 0.55 *(lead's choice)*.
2. Margin: own-capability score minus the larger of the other teacher's score and the untrained student's score on that capability ≥ 0.30 *(lead's choice)*.
3. The acceptance filter reaches the required precision (§5.3) and the accepted pool is at least 8,000 items per capability.

Q is on the training side, so this gate reads no evaluation panel. Its result is part of the freeze record.

## 5. Data and addressing

### 5.1 Source

The gated copy `Helsinki-NLP/tatoeba_mt` is not used. The data are the Tatoeba project's own weekly exports, listed in §14.1: plain sentence files for English, German and French and the two link files between English and each target language. License CC BY 2.0 FR (the project's downloads page). The exports are regenerated every Saturday and carry no revision identifier, so **SHA-256 values are recorded at first download and frozen from then on; the downloaded bytes are kept and verified at every load.** The plain sentence files are used, not the detailed ones, which add contributor names the study does not need.

General-language text: WikiText-2 raw, validation and train, already local (`data/wikitext2/`; CC BY-SA as recorded in ADR-0004).

### 5.2 Partitions (built and hashed before any teacher output is scored)

- **Normalization.** Unicode NFC, lower case, punctuation stripped, whitespace collapsed.
- **Gold pairs.** An English sentence with a linked German (French) sentence has a German (French) reference. References are pooled over all English sentences with the same normalized string.
- **Identity groups** are the connected components of the graph whose nodes are gold pairs, with an edge when two pairs share a normalized English string, a normalized English string after contraction expansion (fixed list in the code), or any normalized reference string. A group goes whole to one side. The partition seed assigns 20% of groups *(lead's choice)* to the **evaluation side** and the rest to the **training side**.
- **No-gold sources.** A training-side English sentence is a *no-German source* if no sentence with its normalized string, or its contraction-expanded string, has a German reference, and that string does not occur on the evaluation side. *No-French source* likewise.
- **Closed vocabulary.** The 2,000 most frequent word types *(lead's choice)* of training-side English sentences of 3 to 10 words. A sentence is in-vocabulary if all its words are.
- **Panels** (in-vocabulary, 3–10 words; evaluation panels sampled stratified by reference count, 1 against 2 or more):

| Panel | Side | Size | Content |
|---|---|---|---|
| E_A, E_B | evaluation | 1,000 each if the data allow, else the largest available | held-out sentences with German / French references |
| E_C | evaluation | 500 *(lead's choice)* | held-out sentences with both; basis of the combined tasks |
| E_open | evaluation | 500 | at least one out-of-vocabulary word; descriptive only |
| Q = Q_fit ∪ Q_check | training side, gold-bearing | 500 + 500 | qualification; filter fitting and filter check |
| D_cal | training side, gold-bearing | 500 *(lead's choice)* | calibration and pilot only |
| D_con | training side, gold-bearing | 300 *(lead's choice)* | acceptance constraint of mechanism (ii) only |
| T_A^r | no-German sources | 8,000 accepted teacher outputs per replicate *(lead's choice)* | training material for capability A |
| T_B^r | no-French sources | 8,000 per replicate | training material for capability B; disjoint from T_A^r in English |
| Gold_A^r, Gold_B^r | training side, gold-bearing, outside Q, D_cal, D_con | 8,000 pairs each per replicate | MA-gold only |

- **Precision the panel size gives.** With 1,000 items and a sentence-chrF standard deviation near 0.2 (the reviewer's assumption, to be replaced by the measured value), a panel mean has a 95% half-width of about 0.012 and a gap closure of about 0.04. With 500 items: about 0.018 and 0.06. Every cell prints a bootstrap interval over items.
- **Evaluation is on held-out sentences.** What training and evaluation share is the vocabulary: the test is composition of seen words into unseen sentences. The reference-count distribution of every panel is reported, and every score is also given for single-reference items alone.
- **Exclusions, then gate G1.** A teacher output on a training source is dropped if, normalized, it equals a normalized reference of any evaluation panel; the count is reported. G1 then checks: every pair of panels and streams is disjoint in identity groups; no normalized reference or teacher output of any training stream equals a normalized reference of any evaluation panel; vocabulary closure holds. The share of evaluation items with a training neighbour at word-level Levenshtein distance 1 is reported.
- **Sufficiency rule.** The in-vocabulary pools are counted before teacher generation is planned. If E_A or E_B cannot reach 500 items, E_C 250, or an accepted pool 8,000, the study stops with TRANSFER-INCONCLUSIVE: DATA-INSUFFICIENT.

### 5.3 Teacher outputs and verification

- **Teacher-only training sources.** T_A^r is drawn only from in-vocabulary no-German sources; T_B^r only from no-French sources. The student's German can come only from Teacher A, its French only from Teacher B. Gold references of training-side sentences are used for Q, D_cal, D_con and the gold control, never as student training targets in any arm that can earn the label.
- **Generation.** Beam 4, at most 48 new tokens, CPU, in the data-generation step. At most 60,000 sources per capability, a seeded sample *(lead's choice)*. Tokens in and out, seconds and peak memory are recorded.
- **Acceptance filter.** An output is accepted if (a) its length-normalized beam log-probability (sum of the token log-probabilities of the returned hypothesis divided by its token count) is ≥ τ; (b) the ratio of its word count to the source's lies in [ρ1, ρ2]; (c) it differs from the source after normalization.
- **Fixing the filter.** (τ, ρ1, ρ2) is chosen on Q_fit from the grid τ ∈ {−0.05, −0.10, …, −0.60}, [ρ1, ρ2] ∈ {[0.5, 2.0], [0.6, 1.6]} *(lead's choice)* as the most permissive setting (largest accepted share) whose precision — the share of accepted outputs with chrF ≥ 0.60 against the best reference — is ≥ **0.90**. The chosen setting must then show precision ≥ **0.90** on Q_check with at least 150 accepted items *(lead's choice)*; otherwise the teacher is not qualified. The precision and its 95% Wilson interval are reported. The filter is fixed before the freeze.
- **What this verification is.** A measured property of the filter on gold-bearing sentences, applied to sentences without gold. It is not a per-item correctness check, and no-gold sentences may differ from gold-bearing ones. The human lead's rule "do not treat a teacher's generated answer as correct without suitable verification" is met in this sense and no other; the lead has ruled this acceptable, and it is named in the label line (§11.3).
- **Distillation is sequence-level.** Cross-entropy on the accepted output text in the student's token ids, prompt positions masked. No teacher logits or token alignments.

### 5.4 Controlled addressing and routes

- **Prompts.** A: `English: {source}\nGerman:`; B: `English: {source}\nFrench:`. Target: the translation and a newline. Greedy decoding, stop at newline. The limit on new tokens is the 99.5th percentile of the gold references of D_cal in student tokens, measured in the rehearsal and frozen (rule fixed now).
- **Address.** For task t and vocabulary word w, the code u(t, w) is a fixed random unit vector in R^16 from a seeded hash of the pair. The store is read at the last subword of each in-vocabulary source word with q = u(t, w), and at the last token of the task marker with q = u(t, ⟨task⟩). Out-of-vocabulary words and target positions are never read.
- **What the address is.** A hand-written function of the prompt (word segmentation, vocabulary table, task marker, hash). Gate G6 checks it takes the prompt only.
- **What cannot be claimed.** That the model decides where to look or knows its task; anything about learned sparse addressing. Every result is **oracle-assisted**.
- **Routes.** A route says which task codes a segment is read with: none, A, B, or both (combined task C2).
  - **Oracle route (the registered condition of every label row):** read from the task marker by rule; ordinary text has none. **There is no switch between memories in the primary arm**: one store, one top-8 over all rows.
  - **Every memory and every adapter arm is applied only under its route**: no read and no adapter on route "none".
  - **Learned-router lane (annotation only).** Three router keys (A, B, none), cosine scores, a learned 16×576 projection of the student's hidden state at the last prompt token of a memory-free pass, top-1. Trained with route labels, with WikiText-2 *train* prefixes as "none", retrained at each stage on stored prompts. An answer-loss-only router is not run, because of P9-I's registered collapse. **It is a keyword-level classifier**: the prompts differ in a marker word, and a pass says nothing about fine-grained addressing.
  - No learned slot-level addressing is run in S2.

## 6. Stages

Every stage runs U updates of batch 32 with AdamW (no weight decay, clip 1.0, constant learning rate from calibration) and a fresh optimizer state. U = 2,000 or 1,000 by the rehearsal rule (§13.3). "First" and "second" are the capabilities in training order; both orders run in every replicate.

### 6.1 Stage 0

The untrained student and both teachers are scored on every panel.

### 6.2 Stage 1

**S1**: a store of N rows trained on Teacher 1's accepted outputs. Version V1. It is also the single-teacher student of that capability.

### 6.3 Stage 2, from V1

| Arm | New capacity | First-stage rows | Replay | What it tests |
|---|---|---|---|---|
| **M-append-frozen** (mechanism i, primary) | N new rows appended to the same store | frozen bit-for-bit (keys, values, gate) | none | the second capability learned in the same store as an untouched first; one top-8 over all 2N rows; queries u(t, w); no switch. Retention is empirical, because first-capability reads can select the new rows |
| **M-ii** (mechanism ii: continued training with replay and a retention constraint) | starts from M-append-frozen's result | trainable | 32 replayed first-teacher rows added to each batch of 32 | whether the first capability survives when its rows are changed |
| M-seq-shared (control) | none | trainable | none | forgetting in a sparse store with task-agnostic codes (H22-E) |
| M-seq (control) | none | trainable | none | the same with task-specific codes; the difference from M-seq-shared is the effect of oracle task coding |

- **M-i-separate** (two stores behind the oracle route) is not trained. It is assembled from the two S1 stores of the same replicate and reported as **BY CONSTRUCTION**. It enters no label.
- **Append point.** M-append-frozen is also scored immediately after the append, before any update. The drop of the first capability at that point is reported as the *append cost*.
- **Mechanism (ii) has no objective beyond its loss.** It is continued training of all rows on the second teacher's material plus replay. The study does not claim it improves anything; it asks whether the first capability survives modification.
- **Retention constraint of M-ii.** Soft: the replayed rows. Hard: the new version is published only if, on D_con, chrF on each capability is at least the M-append-frozen version's minus 0.02 *(lead's choice)*; otherwise the cell is CONSOLIDATION-REJECTED and the pinned version stays.
- **Modification floor.** M-ii counts as retention under modification only if ‖V_1(after) − V_1(before)‖_F / ‖V_1(before)‖_F ≥ 0.10 over the first stage's value rows. Below that the cell is **RETENTION BY INERTIA** and cannot be class 5 (§11.2). Because the acceptance check selects for retention, RET of a published M-ii is reported as "selected on D_con, then confirmed on E".
- **M-seq-shared.** Continues from V1 on the second teacher's material; every read, for both tasks, uses the first task's codes, including the marker code. The store receives no task information; only the marker words in the prompt tell the student which language is wanted. This is the condition comparable to an adapter, which also gets no task input.
- Replay uses stored accepted outputs; no teacher is run again. Replay cells see twice the rows per update; updates and rows are reported.

### 6.4 Evaluation schedule

Every trained snapshot is scored on E_A and E_B after its stage; "before" is the parent snapshot's score.

- **Combined tasks** (never trained on), scored for M-append-frozen, M-ii, M-joint, L-seq, M-i-separate, L-sep and the ensemble:
  - C1, two sources: `English: {s1}\nGerman:` …, then after the model's own answer `\nEnglish: {s2}\nFrench:` …
  - C2, one source, both answers: the source words are read with both tasks' codes and the reads are summed.
  - Score: mean chrF of the two answers; an item passes if both match a reference exactly.
- **General-language quality.** Mean next-token negative log-likelihood on 200 windows of 256 tokens *(lead's choice)* of WikiText-2 validation, with mean KL to the Stage 0 student and the share of unchanged top-1 tokens. This data is used for nothing else. Under oracle routes every arm is bit-identical to the student on this panel; gate G5 checks it and the result is printed **BY CONSTRUCTION**. It is measured for real only in (a) the learned-router condition and (b) the always-on diagnostic (reads with the first task's codes at every in-vocabulary word; adapters always applied), both for M-append-frozen and L-seq.
- **Seen-item scores** on 300 training items are reported for S1 and M-append-frozen and enter no rule.
- Evaluation batches have a fixed composition, so scores do not depend on the worker.

## 7. Baselines and controls

All share partitions, U, batch size and the sequence-level loss. LoRA is implemented inside `studies/p10s2/`, on the query and value projections of all 30 blocks; with grouped-query attention the value projection is 576×192, so one rank costs 57,600 parameters. Rank 42 gives 2,419,200 (−0.23% against one stage of the store). Placement is fixed, not tuned; calibration tunes only its learning rate.

| Baseline | Definition | Trained? | Can show | Cannot show |
|---|---|---|---|---|
| Single-teacher students | S1 of each order; LoRA-1 of each order | yes | what one teacher gives alone | — |
| **M-joint** — ordinary multi-teacher distillation | one store of 2N rows from initialization on the mixed material of both teachers, 2U updates | yes | the bound for sequential arms | anything about order |
| **L-seq** — sequential adapter | LoRA-1 continued on the second teacher's material, no replay | yes | forgetting of a dense adapter | — |
| **L-sep** | the two LoRA-1 adapters of a replicate behind the oracle route | assembled | the fair existing alternative to separate modules; BY CONSTRUCTION for retention | — |
| **E-table** | one trainable 576-vector per (task, vocabulary word) and per task marker, added at layer L at the same positions as the store's reads; no keys, no top-k | yes, each capability | whether the keyed sparse store adds anything over a word-vector table | — |
| **MA-gold** | S1 trained on Gold^r (8,000 gold pairs from gold-bearing sentences) | yes, each capability | a reference point for the teacher's material; not a bound | what the teacher adds item by item |
| **Ensemble** | the two teachers behind the oracle route, and behind the learned router | no | the quality ceiling and its cost | it is not a student |
| **R-exact** | table from training source to accepted output | no | zero hits on held-out items: confirms the panels are held out | — |
| **R-nn** | nearest training source by character-trigram TF-IDF cosine; return its output | no | sentence retrieval without composition | — |
| **R-icl** | the 4 nearest accepted pairs in the frozen student's prompt | no | retrieval that can generalize | its longer prompt is a cost, reported |
| **R-gloss** | co-occurrence lexicon (Dice) from accepted pairs; word-by-word output | no | the non-learned equivalent of a word-addressed store | — |

**Structural asymmetry, stated.** LoRA changes every position, including the generated ones; the store writes only at source positions. LoRA is the stronger class. That is acceptable for "the existing alternative".

**Dropped from revision 1:** M-grow, M-seq-R, L-seq-R, L-joint. The lead's original brief asked for sequential adapters "with and without replay"; the with-replay adapter is dropped under the ruling on M8 (§19, conflicts).

**Ablations on every memory cell**, scored on a fixed 300-item subsample of E_A and of E_B *(lead's choice; the review's text does not state a size)*: memory off; values permuted across rows; **word codes** permuted across vocabulary words, the marker code kept; **marker-only** (word reads off); **words-only** (marker read off).

## 8. What "more parameters" is controlled by

M-append-frozen has 2N rows after Stage 2. It is read against M-joint (2N, simultaneous), M-seq and M-seq-shared (N, no growth), E-table (no keys) and L-sep (dense, separate). The value permutation shows whether the rows are used. The word "fusion" is used for no outcome.

## 9. Replicates, seeds, pairing

- **Four replicates, run unconditionally, if the rehearsal shows the whole study fits the cap with 2× headroom; otherwise three.** The choice is made by the rule of §13.3 and recorded before the freeze. There is no adaptive scheme: no replicate depends on another's result. **A positive label needs every replicate.**
- A replicate is a new training draw (T_A^r, T_B^r, Gold^r) and a new initialization. Evaluation panels, Q, D_cal, D_con and the vocabulary are common and fixed by the partition seed. E-table, MA-gold, M-seq-shared and M-seq run in every replicate.
- Seeds: replicate bases 220001, 220101, 220201, 220301 (base + 0 initialization, + 1 training draw, + 2 batch order, + 3 router, + 4 permutation controls, + 5 gold draw); partition seed 220901; calibration 221001–221999; rehearsal 222001–222999; tests 229001–229999. The implementation asserts the ranges are disjoint from each other and from every seed of P1–P9-II and S1, and writes the hash of every panel and stream to the data manifest. The reviewer's search of `src`, `studies`, `configs` and `tests` found numbers in this range only as parameter counts.
- Within a replicate every arm shares data, batch order where the data are the same, and the initialization of shared parameters.
- Four replicates give "4 of 4", a replication count. No interval across replicates is printed.

## 10. Measurements

### 10.1 Quality

- **chrF-norm.** chrF2 on normalized strings (§5.2): character n-grams n = 1…6, no word n-grams, whitespace removed before n-gram extraction, precision and recall averaged over the six orders before the F-score with β = 2, scale 0–1; item score is the maximum over references; panel score is the mean over items. Implemented in the study, unit-tested on hand cases, and cross-checked against `sacrebleu` 2.5.1 on 1,000 pairs of Q in the data-generation step (agreement within 0.001 per item *(lead's choice)* with matching settings; analysis-only).
- Exact-match rate is descriptive only.
- **Gap closed:** G_c = (s_c(arm) − s_c(S0)) / (s_c(teacher c) − s_c(S0)), same panel. Defined only if the denominator is ≥ 0.30; otherwise NOT_EVALUATED.

### 10.2 Costs

- Teacher inference: tokens in and out, wall and CPU seconds, peak memory; per accepted item.
- Student training: wall seconds per cell, device, updates, rows, peak memory.
- Footprint: stored parameters and bytes of student, each store version, each adapter, each teacher, each index.
- Active work, as counts: reads per item, key products per read (N or 2N, a flat scan), value rows read; per generated token on both sides: value rows read per item × 576 ÷ generated tokens for the store, adapter parameters applied per generated token for LoRA; teacher parameters per token for the ensemble; comparisons and prompt tokens for retrieval.
- **Timing benchmark, separate from training:** after all training, one process, CPU, six threads, 200 items per panel, three repetitions, median. Descriptive only. No latency, throughput, storage or efficiency claim.

## 11. Gates, classes and labels

Thresholds are *(lead's choice)* unless taken from the review, and are fixed at the freeze.

### 11.1 Cell-level gates (per replicate and order)

| Gate | Rule |
|---|---|
| ACQ1 (S1) | G_first ≥ 0.50; G ≤ 0.10 with values permuted; G ≤ 0.10 with word codes permuted; G ≤ 0.25 marker-only |
| ACQ2 (stage-2 arm) | G_second ≥ 0.50 and ≥ 0.80 × the single-teacher student's G on that capability in the same replicate; the same three control limits |
| RET | s_first after Stage 2 ≥ s_first after Stage 1 − 0.03, and G_first after ≥ 0.90 × G_first before |
| Negative zones | acquisition G < 0.25; retention G_first after < 0.70 × before |

GEN is not a gate of any label row: under oracle routes it is BY CONSTRUCTION. It counts only inside the router annotation (§11.4).

### 11.2 Mechanism class (M-append-frozen, M-ii, M-seq-shared, M-seq, L-seq; per order; first match wins)

| Order | Class | Rule over all replicates |
|---|---|---|
| 1 | NOT_EVALUATED | ACQ1 fails in any replicate, or a gap is undefined |
| 2 | NO-NEW-CAPABILITY | G_second in the negative zone in every replicate |
| 3 | FORGETS | retention in the negative zone in every replicate |
| 4 | RETENTION BY INERTIA (M-ii only) | ACQ2 and RET pass in every replicate, and any cell is below the modification floor |
| 5 | ACQUIRES-AND-RETAINS | ACQ2 and RET pass in every replicate; for M-ii no cell is CONSOLIDATION-REJECTED |
| 6 | NOT REPLICATED | some replicate passes both ACQ2 and RET while another is in the negative zone of acquisition or retention |
| 7 | INTERMEDIATE | otherwise |

M-i-separate and L-sep are printed **BY CONSTRUCTION** and receive no class.

### 11.3 Study label (first match wins)

| Order | Label | Rule |
|---|---|---|
| 1 | **ENGINEERING-FAILURE** | a defect found by gates G1, G4–G8; a hash mismatch; a difference between frozen and running code, configuration or data; the oracle-routed ensemble's score differing from the teacher's own |
| 2 | **INCOMPLETE** | a registered cell has no record, or a cap stopped a stage; no class is derived for a mechanism with a missing cell; no denominator is reduced |
| 3 | **TRANSFER-INCONCLUSIVE: TEACHERS-NOT-QUALIFIED** or **DATA-INSUFFICIENT** | §4.3 or §5.2; the study stops before the freeze |
| 4 | **TRANSFER-NEGATIVE: NO-ACQUISITION** | S1's G is in the negative zone in every replicate, for both capabilities |
| 5 | **TRANSFER-INCONCLUSIVE: CONTROL-FAILED** | a value permutation or a word-code permutation gives G ≥ 0.50 in any cell |
| 6 | **TRANSFER-POSITIVE (append-frozen + consolidation)** | M-append-frozen and M-ii are both ACQUIRES-AND-RETAINS in both orders, with teacher-only training material (§5.3) |
| 7 | **TRANSFER-POSITIVE (append-frozen)** | M-append-frozen is ACQUIRES-AND-RETAINS in both orders, with teacher-only training material; M-ii is not |
| 8 | **TRANSFER-NEGATIVE: FORGETTING** | M-append-frozen is FORGETS in both orders |
| 9 | **TRANSFER-NEGATIVE: NO-ADDITIONAL-ACQUISITION** | M-append-frozen is NO-NEW-CAPABILITY in both orders |
| 10 | **TRANSFER-INCONCLUSIVE: ORDER-DEPENDENT** | M-append-frozen is ACQUIRES-AND-RETAINS in exactly one order |
| 11 | **TRANSFER-INCONCLUSIVE** | anything else; the classes are printed |

- **No result printed BY CONSTRUCTION satisfies any row of this table.**
- TRANSFER-POSITIVE means, numerically: in both orders and every replicate, on held-out sentences, S1 closes at least half the gap with all three controls within their limits; the appended rows close at least half the gap on the second capability and reach 0.80 of a single-teacher student; the first capability stays within 0.03 chrF and 0.90 of its gap closure, in one store read with one top-8; and all student training material came from the teachers on sentences without gold.
- Every label is printed with the fixed line: **"oracle-assisted (word-level addresses supplied by rule); lexical translation of short closed-vocabulary sentences, two capabilities of one kind; frozen English student; teacher-only training material verified by measured-precision filter; not autonomous learned memory."**
- Order now matters in substance: it decides which rows are frozen and which are appended.

### 11.4 Mandatory annotations (printed with the label; they do not change it)

| Annotation | Rule |
|---|---|
| NO ADVANTAGE OVER SEPARATE ADAPTERS | L-sep's scores on both capabilities are within 0.03 of M-append-frozen's or above, in at least one order |
| EQUIVALENT TO A WORD TABLE | E-table's G is within 0.03 of S1's or above, on both capabilities, in every replicate |
| RETRIEVAL SUFFICES | R-icl's or R-nn's score is within 0.03 of M-append-frozen's or above on both capabilities |
| LEXICON-EQUIVALENT | R-gloss's score is within 0.03 of M-append-frozen's or above on both capabilities |
| TEACHER-EQUIVALENT-TO-GOLD | MA-gold's G is within 0.03 of S1's or above |
| BELOW JOINT BOUND | M-append-frozen's G on either capability < 0.90 × M-joint's |
| SPARSE-RETENTION / NO SPARSE-RETENTION | M-seq-shared's loss of G_first is smaller than L-seq's by ≥ 0.10 in every replicate of both orders / otherwise. M-seq is printed beside it; the difference between M-seq and M-seq-shared is attributed to oracle task coding, not sparsity |
| ROUTER (keyword-level) QUALIFIED / NOT QUALIFIED | route accuracy ≥ 0.99 on E_A, E_B and general prefixes; M-append-frozen passes ACQ2 and RET with learned routes; general-panel loss rises ≤ 0.02 nats per token; every replicate |
| APPEND COST | the first capability's change in G at the append point, before training |
| COMPOSES C1 / C2 | mean over replicates of the combined score ≥ 0.80 × the mean of the arm's two single-task scores |
| EXACT-MATCH WEAK | gap closed on exact-match rate < 0.10 for either capability |
| Cost lines | always printed (§11.5) |

### 11.5 Cost and active-memory lines (registered rules, descriptive standing)

For M-append-frozen after Stage 2, medians over replicates:

- **TRAINING COST COMPARABLE** if training wall seconds per stage ≤ 1.5 × LoRA-1's on the same device and U; otherwise TRAINING COST HIGHER, with the ratio.
- **FEWER VALUE ROWS ACTIVE** if the store's value parameters read per generated token ≤ 0.10 × the adapter parameters applied per generated token (both as defined in §10.2); always printed with the key products per read, which a flat scan does not reduce.
- **Stored size against the ensemble is arithmetic, not a comparison:** student plus a 2N-row store is 139,364,674 parameters against 148,613,487 for the two teachers, a ratio of 0.938. It is printed as such, with M-append-frozen's G on each capability.
- Teacher inference cost per accepted training item.

None is an efficiency result. Logical counts are never reported as measured efficiency.

## 12. Calibration, pilot and gates

### 12.1 Calibration (before the freeze; calibration seeds; D_cal only)

- Store: L ∈ {4, 12} at learning rate 0.003, for each capability: 4 cells. LoRA: learning rate ∈ {0.0003, 0.001}, for each capability: 4 cells *(lead's choice, the review's suggestion)*. Each is a Stage 1 of U = 2,000 updates on calibration draws.
- Rule: the setting with the higher mean over the two capabilities of chrF on D_cal; a difference below 0.01 goes to the first value listed. Calibration scores are never reported as results. Nothing else is tuned. Evaluation panels are not scored before the registered run.

### 12.2 Pilot gate (before the freeze)

With the calibrated store setting, on D_cal, Stage 1 for **both** capabilities (these are calibration cells; no extra training). If either has a gap closed below 0.25, the registered run does not start: **NOT STARTED: STUDENT CANNOT USE THE MEMORY ON THIS TASK**, recorded with the calibration records. The pilot's scores are optimistic, because D_cal also selected the setting. They are not results.

### 12.3 Gates

- **G1** partitions (§5.2).
- **G2** the Stage 0 student and the stored teacher outputs score identically twice; every gap is defined on E_A and E_B (an undefined gap gives NOT_EVALUATED cells, not a stop).
- **G3** teacher qualification and filter precision (§4.3, §5.3), before the freeze.
- **G4** determinism of CPU evaluation (two scorings bit-identical; fixed batch composition; lowest-index tie rule); snapshot save and restore bit-identical; gradient reach (in M-append-frozen no first-stage row, gate or student parameter receives a gradient; in every memory arm no student parameter does); 20 updates on CPU repeated bit-identically; the same 20 updates on MPS agree with CPU in loss within 1e-3 and in parameters within a relative norm difference of 1e-4 *(lead's choice)*. `PYTORCH_ENABLE_MPS_FALLBACK` is unset, so any fallback is an error. macOS, torch and MPS versions are in the manifest.
- **G5** on route "none", logits equal the frozen student's bit for bit on the general panel; a new store and newly appended rows with gate 0 change nothing.
- **G6** the address function and the router take the prompt only; permuting references changes no address and no route.
- **G7** frozen bytes: every model file equals its pinned SHA-256 (large files) or git-blob SHA-1 (small files); every Tatoeba file, the converted student file, every teacher-output file and every token-id file equals the SHA-256 recorded at first download or creation. Checked at every load.
- **G8** student equivalence: the result recorded by the data-generation step (§14.2) is present and within tolerance, and the registered path's student reproduces the stored reference logits within the same tolerance.
- The gates stage runs at real size on rehearsal seeds before the freeze and again on registered seeds before training. A failed gate stops the run.

## 13. Matrix and projected resources

### 13.1 Matrix per replicate

| Group | Cells | Units of U |
|---|---|---|
| S1 (two orders) | 2 | 2 |
| M-append-frozen | 2 | 2 |
| M-ii (64-row batches, about twice the cost per update) | 2 | 4 |
| M-seq-shared, M-seq | 4 | 4 |
| M-joint | 1 | 2 |
| E-table (each capability) | 2 | 2 |
| MA-gold (each capability) | 2 | 2 |
| LoRA-1, L-seq | 4 | 4 |
| **Trained cells per replicate** | **19** | 18 store-type + 4 LoRA |

**Four replicates: 76 trained cells. Three: 57.** Assembled without training: M-i-separate, L-sep. Scored without training: Stage 0, teachers, ensemble, four retrieval baselines, five ablations on each of 13 memory cells per replicate, the append point, the router lane, the always-on diagnostic, the timing benchmark. Calibration and pilot: 8 cells.

### 13.2 Charging rule

**Charged hours are the sum of wall-clock hours over all S2 processes: k parallel workers running for t hours charge k·t.** The data-generation step, calibration, pilot, rehearsal and the registered run are all charged. **Cap: 36 charged hours for S2.**

### 13.3 Projection — not a measurement

No figure below is measured on this machine. They come from operation counts and are uncertain by about a factor of three; the rehearsal replaces them.

| Work | Device | Per unit | Per replicate | Four replicates |
|---|---|---|---|---|
| Store-type unit of U = 2,000 | MPS, FP32 | 5–10 min | 18 units: 1.5–3.0 h | 6.0–12.0 h |
| LoRA unit of U = 2,000 | MPS, FP32 | 8–15 min | 4 units: 0.5–1.0 h | 2.1–4.0 h |
| Scoring E_A and E_B of a trained cell | CPU, 6 threads | 1.6–5.2 min | 19 cells: 0.5–1.6 h | 2.0–6.6 h |
| Combined panels, append point, ablations on 300 items, router lane, diagnostic, retrieval | CPU | — | 0.9–3.0 h | 3.6–12.0 h |
| Stage 0, teacher scoring, general panel, timing benchmark | CPU | — | — | 0.3–0.6 h |
| **Registered run** | | | | **14–35 h** |
| Data-generation step (teachers on at most 2 × 60,000 sources plus panels; conversion; token ids) | CPU | — | — | 1.0–1.8 h |
| Calibration and pilot (8 cells with scoring) | both | — | — | 1.0–2.2 h |
| Rehearsal | both | — | — | 1.5–3.0 h |
| **Before the freeze** | | | | **3.5–7.0 h** |

**Rehearsal rule, fixed now.** Let P be the hours already charged at the end of the rehearsal and R(n, U) the registered run projected from the rehearsal's measured rates for n replicates and U updates. The design is the first of the following for which P + 2·R ≤ 36:

1. four replicates, U = 2,000;
2. four replicates, U = 1,000;
3. three replicates, U = 1,000;
4. none: the run is not started and the lead returns to the human lead.

The outcome of the rule is recorded before the freeze. On the projection above, rung 1 holds only if the registered run measures at about 15 hours or less, which is the fast end; rung 3 projects to 8–20 hours. **It is plausible that the rule ends at rung 3 or rung 4.** The lead's ruling fixes "four, otherwise three"; the placement of the U = 1,000 step between them is this draft's ordering (§19, conflicts).

- **Runtime.** Training on torch MPS in FP32, which is not bit-reproducible; what is recomputed independently is every score, from saved snapshots, on CPU with deterministic algorithms. If the rehearsal finds an unsupported MPS operation, training moves to CPU and the rule above is applied to the CPU rates.
- **Other caps** *(lead's choice)*: 8 GiB per worker; 24 GiB aggregate; total download 1.5 GB; new disk use 6 GB.
- **Rehearsal content,** at full size on rehearsal seeds: every cell type for 200 updates; one store cell, one M-ii cell and one LoRA cell for the full U; one scoring of each kind; the truncation percentile of §5.4; the gates stage; analysis and report on synthetic records of the whole registry including missing cells, rejected consolidations, inertia cells and non-finite values.

## 14. Downloads, packages and the data-generation step

### 14.1 Downloads requiring the human lead's approval — none is made before it

The lead has asked the human lead about the student and the data and has no answer yet. The human lead's words cover "two small teachers"; everything else in this table is outside those words.

| # | What | Source | Files | Size | License | Identity |
|---|---|---|---|---|---|---|
| 1 | Teacher A | `Helsinki-NLP/opus-mt-en-de` @ `6183067f…b0ca4` | `pytorch_model.bin`, `config.json`, `generation_config.json`, `source.spm`, `target.spm`, `vocab.json`, `tokenizer_config.json` | 300.8 MB | CC-BY-4.0 | revision and SHA-256 pinned now |
| 2 | Teacher B | `Helsinki-NLP/opus-mt-en-fr` @ `dd7f6540…67f18` | same file names | 303.7 MB | Apache-2.0 | pinned now |
| 3 | Student | `HuggingFaceTB/SmolLM2-135M` @ `93efa2f0…e75a2` | `model.safetensors`, `config.json`, `generation_config.json`, `tokenizer.json`, `tokenizer_config.json`, `vocab.json`, `merges.txt`, `special_tokens_map.json` | 272.4 MB | Apache-2.0 | pinned now |
| 4 | Tatoeba exports | `https://downloads.tatoeba.org/exports/per_language/` | `eng/eng_sentences.tsv.bz2` (24,947,715 B), `deu/deu_sentences.tsv.bz2` (12,144,786 B), `fra/fra_sentences.tsv.bz2` (9,805,546 B), `eng/eng-deu_links.tsv.bz2` (3,557,634 B), `eng/eng-fra_links.tsv.bz2` (2,679,128 B) | 53.1 MB | CC BY 2.0 FR | no revision exists; SHA-256 recorded at first download and frozen |
| 5 | Fallback teacher, only if invoked | `Helsinki-NLP/opus-mt-en-es` @ `5bc4493d…ed4ab` | as rows 1–2 | 315.3 MB | Apache-2.0 | pinned now |
| 6 | Fallback data, only if invoked | same Tatoeba site | `spa/spa_sentences.tsv.bz2` (6,376,323 B), `eng/eng-spa_links.tsv.bz2` (1,762,602 B) | 8.1 MB | CC BY 2.0 FR | recorded at first download |
| | **Total** | | | **930 MB without the fallback; 1,253 MB with it** | | |

- **Tatoeba, what was checked (read-only, 2026-11-15).** The project's downloads page states the files are "released under CC BY 2.0 FR" and that the exports are updated every Saturday. The per-language directory indexes for `eng`, `deu`, `fra` and `spa` were readable without an account and list the files above with the sizes shown (index dated 14-Nov-2026; the unit is taken to be bytes). Sentence files have three tab-separated columns (id, language, text). **TO VERIFY AT DOWNLOAD:** that the files themselves are served without an account (only the indexes were fetched); the column format of the per-pair link files (the downloads page documents "sentence id, translation id" for the full link file); the sizes, which change weekly.
- **How.** Plain HTTPS of the pinned `resolve/<revision>/<file>` addresses for the models and of the addresses above for Tatoeba, each followed by a hash check. No account, no token, no Hub client in the download step. Files go to a git-ignored directory named by source and revision or download date.
- CC BY 2.0 FR and CC-BY-4.0 require attribution in any publication. No data and no weights are redistributed by this study.

### 14.2 The data-generation step (once, before the freeze; the only place where packages outside the lock are used)

Run with `uv run --locked --with-requirements studies/p10s2/requirements-datagen.txt`; `uv.lock` and `pyproject.toml` are untouched. It does, offline after the downloads:

1. hash checks of every downloaded file;
2. conversion of the pinned student weights to a plain FP32 torch file, whose SHA-256 is frozen;
3. **student equivalence test:** the study's torch student against the reference implementation on the pinned weights, on a fixed 256-token text from WikiText-2 train, FP32, CPU: maximum absolute logit difference ≤ 1e-3 and identical top-1 token at every position *(lead's choice)*; the reference logits are stored for gate G8;
4. token ids of every text segment (§2), and the decoder check: the study's decoder reproduces the reference decoder on 1,000 fixed id sequences;
5. teacher loading (SHA-256 check, weights-only load, local configuration files only), the 100-sentence tokenizer record per teacher, and generation with beam scores for the training sources, Q, D_cal, D_con and the evaluation panels. **Outputs on evaluation panels are stored and hashed and are not scored before the registered run**;
6. the chrF cross-check against `sacrebleu`.

Its outputs are data files with frozen hashes. Scoring, filter fitting, qualification, calibration, the pilot and everything registered run on the locked environment.

| Package | Version | Note |
|---|---|---|
| transformers | 4.57.1 | the set below is the one the reviewer verified as mutually compatible by metadata; a 5.x release cannot be combined with these companions |
| tokenizers | 0.22.1 | |
| safetensors | 0.6.2 | |
| huggingface-hub | 0.35.3 | a dependency of `transformers` only; not used to download |
| sentencepiece | 0.2.1 | |
| numpy | 2.3.3 | |
| sacremoses | 0.1.1 | |
| sacrebleu | 2.5.1 | analysis-only cross-check; exists on PyPI, Apache-2.0; not checked by the reviewer |

- Transitive dependencies are fixed by one resolution written to `requirements-datagen.txt` with exact versions and hashes, which is part of the freeze. **That the set resolves with torch 2.8.0 on Python 3.12 has not been run.**
- **The one relevant advisory.** GHSA-29pf-2h5f-8g72 (CVE-2026-4372, fixed in 5.3.0): a malicious `config.json` carrying `_attn_implementation_internal` can make `from_pretrained` execute code. Mitigation: the configuration files are hash-pinned, and the reviewer checked that the pinned ones contain no such key; loading is offline from local paths with no remote code; downloads are plain HTTPS with SHA-256 checks; weights are loaded in weights-only mode (torch 2.8.0 is past the fix for CVE-2025-32434). The other advisories listed against 4.57.1 concern interfaces this step does not call.
- Package wheels are themselves downloads. The lead reads the delegation as covering pinned per-command additions; the reviewer reads CLAUDE.md as not covering them (§19, conflicts).

## 15. Departures from project practice that need explicit acceptance

1. A pretrained student, against the handoff's "first tests use a train-from-scratch small model".
2. Training on MPS without bit reproducibility; snapshots are the object, scores are reproduced on CPU. A re-run would not reproduce the snapshots.
3. A 36-hour cap. The human lead has said this figure is acceptable (§18).
4. Pickle weight files for the teachers, loaded once in weights-only mode.
5. A CC-BY-4.0 teacher and CC BY 2.0 FR data: attribution owed on publication.
6. Packages outside the lock in a pre-freeze data-generation step, whose outputs the registered run consumes as frozen data.
7. Data without a revision identifier: frozen by recorded hash, not by pin.

## 16. Order of work, stop rules, reserved decisions

**Order.** (1) Confirmation review of this revision. (2) The human lead's answer on the downloads of §14.1 and on "complementary". (3) Lead's approval. (4) Implementation with tests on synthetic stand-ins, before any download. (5) Downloads; data-generation step. (6) Partitions; filter fitting; G3; calibration; pilot. (7) Rehearsal; implementation audit; rehearsal rule. (8) Freeze of code, configuration, requirements file, seeds, thresholds, filter, calibration record, rehearsal-rule outcome, data manifest. (9) The registered run, once. (10) Independent recomputation of every score from snapshots; outcome report.

**Stop rules.** A failed gate or any difference from the freeze stops the run. A stage that would exceed a cap is not started. Nothing is re-run with changed settings. A second attempt after an engineering stop needs the human lead's decision. Failed runs and failed checker attempts are kept.

**Reserved for the human lead.** Whether two translation directions count as "complementary capabilities". Every download of §14.1. Any change of thresholds, arms, models, data or budget after the freeze. A second attempt. Any model above 2 billion parameters, any cloud spend, any account or login, any further download. Use of the locally present Ollama weights (not used here). Learned slot-level addressing inside S2. Use of S2's outcome in any P10 system claim. Merge, publication, weight release, ADR-0012.

## 17. What S2 cannot establish

- **Autonomous learned memory.** Addresses and routes are supplied by rule.
- **Anything about routing beyond keyword detection.**
- **That the sparse keyed store beats a word-vector table,** unless E-table loses.
- **That knowledge came from the teachers rather than from gold data,** unless the teacher-only arm passes; and even then each training item was accepted by a filter of measured precision, not checked.
- **Knowledge fusion.** One store holding two lexicons is not fusion; more parameters holding more is not fusion.
- **Skill transfer.** The capability is lexical translation of short sentences from a 2,000-word vocabulary. A frozen English model's success does not transfer to non-lexical or open-vocabulary use.
- **That the two capabilities are complementary in kind.** They are two directions of one task.
- **Large models.** Teachers of 74 million parameters and a 135-million student say nothing about 25B or 100B teachers.
- **Superiority** over adapters, tables, lexicons or retrieval.
- **Storage, latency, efficiency, capacity scaling, locality.**
- **A success probability.** Three or four replicates on one partition of one corpus.
- **That MPS-trained snapshots would be reproduced by re-running.**
- **A failure of the ArborLM concept,** whatever the outcome.

## 18. Approval record

The human lead, verbatim:

> "we can change it to  p10 can be self approve but p10-I need my review"

> "im confortable with does number if it mean it will resolve most dough and close any posible misguidence due to a small set"

Lead's approval: PENDING the confirmation review and the human lead's answer on downloads.

## 19. Map of the review of revision 1 to this revision

| Finding | Change | Where |
|---|---|---|
| B1 | Label row "i only" deleted. Primary arm is M-append-frozen (one store, appended rows, frozen first-stage rows, one top-8, no switch). M-i-separate assembled, BY CONSTRUCTION, no class, no label. The probe's 22–27% cited. "No BY CONSTRUCTION result satisfies any row." | §1, §6.3, §11.2, §11.3 |
| B2 | Training material is teacher output on sentences with no gold in that language. Acceptance filter defined; precision ≥ 0.90 at chrF ≥ 0.60, fitted on Q_fit and required again on Q_check. MA-gold redefined on gold-bearing sentences. Positive rows require teacher-only material. Qualification gate kept. | §0, §4.3, §5.2, §5.3, §7, §11.3 |
| B3 | Gated copy dropped. Tatoeba's own exports, files and sizes listed; hashes recorded at first download. One download table under the required heading; student and data awaiting the human lead. | §5.1, §14.1 |
| M1 | Modification floor 0.10; RETENTION BY INERTIA as a class; "selected, then confirmed"; mechanism (ii) named as continued training with replay, no objective claimed. | §6.3, §11.2 |
| M2 | E-table in every replicate; EQUIVALENT TO A WORD TABLE. | §7, §11.4 |
| M3 | Marker-only and words-only ablations; word codes permuted with the marker code kept; marker-only ≤ 0.25 in ACQ1 and ACQ2; CONTROL-FAILED at G ≥ 0.50, placed after NO-ACQUISITION. | §7, §11.1, §11.3 |
| M4 | Connected-component identity groups with contraction expansion and shared references; extended G1; neighbour share reported. Adapted: with no test files, groups are assigned by the partition seed. | §5.2 |
| M5 | All arms gated by route; GEN printed BY CONSTRUCTION and removed from label gates; counted only in the router annotation; always-on diagnostic. | §5.4, §6.4, §11.1, §11.4 |
| M6 | M-seq-shared added and used for SPARSE-RETENTION; M-seq printed beside it. | §6.3, §11.4 |
| M7 | Pilot on both capabilities, with the optimism caveat. | §12.2 |
| M8 | Reduced matrix (19 cells per replicate); charged hours as the sum over processes; replay-without-growth controls removed outright. Replication follows the lead's ruling, not the review's two-then-three scheme. | §9, §13 |
| M9 | Registered path on the locked environment only; teachers and conversion in a pre-freeze data-generation step; torch student with equivalence test; segment-level token ids and a pure-Python decoder; reviewer's package set; the one relevant advisory and its mitigation. | §2, §12.3 (G8), §14.2 |
| M10 | Scope words in the fixed label line; "complementary" left to the human lead in the header and §16. | header, §11.3, §16 |
| L1 | Weight-format sentence corrected. | §4.1 |
| L2 | 100-sentence teacher token-id record, frozen. | §4.1, §14.2 |
| L3 | Fallback kept (the ruling lists it among the downloads) and its different regime stated. | §4.2 |
| L4 | Departures of the memory listed; non-zero value initialization; "well separated" replaced. | §3 |
| L5 | chrF-norm defined exactly; sacrebleu cross-check. | §10.1, §14.2 |
| L6 | New-token limit from the 99.5th percentile, measured in rehearsal. | §5.4 |
| L7 | Stored-size line printed as arithmetic (0.938); value rows defined per generated token on both sides. | §10.2, §11.5 |
| L8 | NOT REPLICATED restricted to the deciding thresholds and placed after the all-replicate classes. | §11.2 |
| L9 | Lowest-index tie rule; fixed evaluation batch composition. | §3, §6.4, §12.3 |
| L10 | Data hashes "recorded at first download". | §5.1, §12.3 (G7) |
| L11 | Plain HTTPS with hash checks; no Hub client in the download step. | §14.1 |
| L12 | Claim about procedural skills reworded. | §0 |
| L13 | Router named a keyword-level classifier. | §5.4, §11.4 |
| L14 | LoRA placement stated as fixed, not tuned. | §7 |
| L15 | Pools counted before the teacher-generation plan; generation capped at 60,000 sources per capability. | §5.2, §5.3 |
| Review §H (MPS) | Versions in the manifest; fallback variable unset; parameter agreement in G4. | §12.3 |
| Review §J | Ensemble mismatch moved to ENGINEERING-FAILURE; additions to "cannot establish". | §11.3, §17 |

**Rulings that could not be applied as given, and conflicts between fixes (listed, not resolved silently):**

1. **Four replicates against the cap.** On the projection, four replicates at U = 2,000 fit only at the fast end of an unmeasured estimate. The ruling says "four, otherwise three"; the review supplies a U = 2,000 / 1,000 rule. This draft orders them 4×2,000 → 4×1,000 → 3×1,000 → not started. Preferring replicates over updates is this draft's reading of the human lead's words; the lead may prefer 3×2,000 before 4×1,000.
2. **"Ablations on every memory cell" against the budget.** Applied to all 13 memory cells per replicate, but on a 300-item subsample; the review's text gives no size. At 1,000 items the ablations alone would add roughly 3–10 charged hours over four replicates.
3. **M-seq.** The review's reduced design lists only M-seq-shared; its text for M6 prints M-seq beside it. Both are run in every replicate (two extra cells per replicate).
4. **Sequential adapter with replay.** The lead's original brief asked for sequential adapters "with and without replay". Under the M8 ruling the with-replay adapter (L-seq-R) is not in the matrix.
5. **Fallback.** The review recommends dropping the fallback; the ruling lists the fallback teacher among the downloads. Kept, with its different training regime stated.
6. **M4 as written refers to test files.** With the project's own exports there are none; identity groups are assigned to sides by the partition seed (20% to evaluation).
7. **Filter precision is measured where gold exists and applied where it does not.** B2 as ruled cannot remove this; Q_fit / Q_check splitting was added to avoid fitting and measuring on the same items, which halves the items behind each precision figure.
8. **Packages as downloads.** The lead reads the delegation as covering pinned per-command packages; the review says CLAUDE.md does not obviously cover them. They are confined to the data-generation step, but they are still fetched. Not decided here.
9. **Tatoeba public access is confirmed for the directory listings only.** The files were not fetched (no downloads in this task); the link-file format is inferred from the full export's documentation.
10. **Segment-level tokenization** is a consequence of the M9 ruling (no tokenizer in the registered path). Concatenating segment ids can differ from tokenizing the whole string at segment boundaries. It is the same for every arm, but it is a definition the review did not see.

## Open questions for the lead

1. Order of the rehearsal rule: four replicates at U = 1,000 before three at U = 2,000, or the reverse?
2. Is a 300-item subsample enough for the ablations, given limits at 0.10, 0.25 and 0.50?
3. Should FORGETTING of M-append-frozen in both orders be a study-level negative (row 8, as drafted), given that the append cost may be large before any training?
4. Is 20% of identity groups the right evaluation share, or should it be set after the pools are counted (before any scoring)?
5. Should the filter's precision bar apply to the point estimate (as drafted) or to the lower Wilson bound, which is stricter and may reject both teachers?
6. Keep M-seq with task-specific codes (two cells per replicate) or print only M-seq-shared?
7. Does the equivalence tolerance (1e-3 on logits, identical top-1) suit a 30-block FP32 model, or should it be set from a measured run-to-run difference of the reference itself?

## Things the lead must verify before approval

- The human lead's answers: downloads of §14.1 (student, data, fallback, and whether package wheels count) and "complementary".
- That the Tatoeba files are served without an account, the link-file format, and the sizes on the day of download.
- That the package set of §14.2 resolves with torch 2.8.0 on Python 3.12; `sacrebleu` 2.5.1 was not checked by the reviewer.
- That Marian loading in `transformers` 4.57.1 accepts the pinned German repository despite its tokenizer configuration.
- Every throughput figure of §13.3; none is measured.
- That enough in-vocabulary no-gold sources and gold-bearing identity groups exist; unknown until the files are read.
- That the confirmation reviewer accepts the adaptations listed under "conflicts" above.
