# ADR-0022 — P10-S2: Two-teacher sequential knowledge transfer into expandable learned memory

- **Status: DESIGN REVISION 5 — pending an independent confirmation; lead's approval PENDING; nothing implemented, downloaded or run. SPEC: PENDING ASTRA REVIEW.**
- **Date:** 2026-11-15 (UTC)
- **Editorial corrections after revision 4 (E8 of the ADR-0020 confirmation; no rule, threshold, arm or number changed):** the single-teacher store is named **ST1** (it was "S1", which is also a study name); the Stage 0 score is written s_c(Stage 0) (it was "s_c(S0)"); a supplement for learned addressing names the human lead; the seed check lists S0. The text before these corrections is `docs/reviews/p10-design-2026-11-15/revisions/ADR-0022-rev4-before-E8.md`.
- **Revision 5** applies the re-check of revision 4 (`adr-0022-review/RECHECK_REV4.md`, Opus 5.5: READY SUBJECT TO text edits; majors J1–J8, minors J9–J14 and others) and does nothing else. No threshold, arm, model, data source, replicate count, rung or cap is changed. Points the re-check left open are settled by the P9 / P9-II convention where one exists, otherwise by the option that is harder for a positive label or counts more time against the cap; each is marked **[lead's choice]** and listed in §20 with the alternative not taken. §21 maps each change to its finding. The revision 4 text is kept at `docs/reviews/p10-design-2026-11-15/revisions/ADR-0022-rev4.md`.
- **Origin.** The human lead's P10 direction, milestone question 2: "Can ArborLM sequentially acquire complementary capabilities from two pretrained teacher models while preserving earlier capabilities?"
- **The two capabilities.** This design uses two translation directions (English→German, English→French) as the two capabilities. The human lead has accepted them as the two capabilities of this study (§18, item 3). They remain two capabilities of one kind, and §17 limits what a result can mean.
- **Oracle qualification.** Every address and every registered route in S2 is supplied by rule. "Learned memory" in the title names a store whose keys and values are trained; it does not name learned addressing. The human lead's instruction, verbatim: "S1 and S2 must not claim autonomous learned-memory success from oracle-assisted results." §11.3 puts the oracle-assisted line above every printed class, label, annotation and cost line.
- **Study code** P10S2. **Package** `studies/p10s2/`. **Seed namespace** 220001–229999 (§9).
- **Roles (study-specific).** Lead: Claude Fable 5.2. Specification audit, implementation audit and recomputation: Opus 5.5, in contexts separate from implementation, receiving code and records and not the lead's conclusions. Implementation: Sonnet 5.5. Inventory: Haiku 5.5. The model that actually ran each delegated task is recorded from session metadata. ADR-0012 stays not approved. **Astra review: NOT_PERFORMED.**
- **Relation to other work.** S2 is one of three independent P10 experiments (S0 addressing, S1 capacity, S2 transfer). It does not wait for S0 and uses no result of S0 or S1. Its label is independent of CAPACITY-POSITIVE and SYSTEM-POSITIVE. P1–P9 code, records and ADRs are not edited.
- **Evidence it rests on.** P9-I (ADR-0017 Part I): oracle-addressed memory stores and returns answers; every learned query interface collapsed onto 1–6 slots (`results/p9i-run-attempt2-2026-11-15/OUTCOME.md`). No registered evidence exists on incremental learning or teachers. The specification review of revision 1 (`adr-0022-review/REVIEW.md`) and the confirmation of revision 3 (`adr-0022-review/CONFIRM.md`), both Opus 5.5, with the two synthetic probes, are review evidence, not registered results. The re-check of revision 4 (`adr-0022-review/RECHECK_REV4.md`, Opus 5.5) has the same standing.

Numbers marked *(lead's choice)* are judgment calls.

## Revision history

| Revision | Date | Status | Change |
|---|---|---|---|
| 1 | 2026-11-14 | reviewed: NOT READY (B1–B3, M1–M10, 15 minors) | first draft |
| 2 | 2026-11-15 | superseded by revision 3 after the lead's rulings on its ten listed conflicts | primary arm is now one appended store with frozen rows; training material is teacher output on sentences without gold; data from the Tatoeba project's own exports; teachers isolated in a pre-freeze data-generation step, registered path on the locked environment only; smaller per-replicate matrix with four replicates; controls, labels and scope words as ruled. §19 maps every finding to its change. |
| 3 | 2026-11-15 | confirmed by the auditor: READY AFTER LISTED TEXT EDITS (C1–C10, m1–m7; `adr-0022-review/CONFIRM.md`) | general-language preservation is an empirical gate of the positive label, measured under the keyword router, with the label TRANSFER-POSITIVE WITHHELD when it fails; rehearsal rule reordered (three full-length replicates before four shortened ones); the lead's rulings on revision 2's ten points recorded (§19); list of the lead's choices added (§20). No cell was added or removed. |
| 4 | 2026-11-15 | applied C1–C10 and m1–m7; re-checked by the auditor: READY SUBJECT TO text edits (J1–J8 major, J9–J14 and others minor; `adr-0022-review/RECHECK_REV4.md`) | gate G5 rewritten for the append design; control limits as a lexical margin; M-seq-shared removed and L-joint restored (18 trained cells per replicate); GEN at 0.02 nats on a panel with marker-like windows, for every snapshot; filter selected on the Wilson lower bound; large identity groups to training; calibration and pilot re-applied at the chosen U; tokenization conventions and equivalence tests; chrF over effective orders; "(n, U)" on every label; the meaning of "every replicate" stated. §19 maps every finding. |
| 5 | 2026-11-15 | pending an independent confirmation; lead's approval PENDING | applies the re-check of revision 4: generator seeds listed and seeded directly, with seed gate G9; key initialization stated; the download scope stated once (what is approved, what is open with the human lead); marker strings of the GEN panel within tokens 1–64; router training recipe; disjoint training draws and gold sufficiency; the rung rule's rates and charged scope, and NOT STARTED: BUDGET; RET reference; LoRA and E-table initialization; filter tie-break; window grid; BOS from the reference default; the oracle-assisted line above every printed class and line. No threshold, arm, model, data source, replicate count, rung or cap changed. §21 maps every finding. |

## 0. Frank assessment before the design

1. **The demonstration is narrow.** A sparse key–value memory with controlled addresses is a lookup table. It carries a capability only through units that recur between training and held-out items. The word-level address used here *is* the lexical segmentation: the hand-written address supplies part of the structure of the task. A hand-written address could supply units for a procedural task too (for example digit pair and carry), but then the address would encode the algorithm. A positive result here would show transfer of *lexical knowledge used compositionally by a frozen student*, not transfer of a skill.
2. **What is by construction is not counted.** With oracle routes, general-language quality on ordinary text is bit-exact, and a separate frozen store behind a switch retains exactly. Neither satisfies any label row (§11). Retention is tested in a store where it can fail (§6.3), and general-language preservation is tested under a learned router that can trigger wrongly on ordinary text (§6.4, §11.1).
3. **The existing alternatives are strong and may win.** Separate adapters behind a switch, a plain word-vector table, a co-occurrence lexicon and retrieved demonstrations can all do this task. S2 measures them and prints the comparison with the label. S2 cannot show superiority.
4. **The teacher must be the only source of the target language.** Revision 1 trained on teacher outputs that equalled gold references, which made the teachers replaceable by the corpus. Revision 2 trains on teacher outputs for English sentences that have no reference in that language. The price is that correctness of each training item is no longer checked against gold; it is checked by a filter whose precision is measured on gold-bearing sentences (§5.3).
5. **Risk of an uninformative negative.** The student is an English model. Whether it can emit German and French from lexical vectors injected at one layer is unknown. The pilot gate tests both languages before the freeze (§12.2).
6. **The budget may not hold four replicates.** The projection (§13) fits the cap with 2× headroom only at the fast end of an unmeasured throughput estimate. The rehearsal rule decides (§13.3); it can end at three replicates, at shortened training, or in **NOT STARTED: BUDGET**.

## 1. Question and hypotheses

**Can a frozen pretrained student with an expandable sparse memory acquire, one after the other, two lexical capabilities from two pretrained teachers, keeping the first when the second is added to the same store, when addresses are controlled?**

- **H22-A (acquisition).** A memory trained on Teacher 1's filtered outputs closes at least half of the teacher–student gap on held-out items; the gain disappears when values or word codes are permuted and is not carried by the task-marker read alone.
- **H22-B (additional acquisition).** Appending new rows to the same store and training them on Teacher 2's outputs, with the old rows frozen, closes at least half of the gap on the second capability and reaches at least 0.80 of a single-teacher student.
- **H22-C (retention in a shared store).** The first capability stays within 0.03 chrF after the append and the second stage, although its reads can now select the new rows.
- **H22-D (retention under modification).** Continued training of all rows with replay and a retention constraint keeps the first capability while changing its rows by at least 0.10 in relative norm.
- **H22-E (descriptive, no hypothesis test).** In this design the retention effect of sparsity cannot be separated from oracle task coding: different tasks touch different rows only because their codes differ. M-seq (task-specific codes) is compared with L-seq and printed as "sparse store with oracle task codes against a dense adapter". M-seq-shared is removed. Its two units per replicate pay for L-joint (§7).
- **H22-F (order).** H22-A to H22-C hold in both orders.
- **H22-G (general quality under a learned route).** When a learned keyword router, not a rule, decides whether the store is read, the student's loss on ordinary English text rises by at most 0.02 nats per token over the unmodified student, on a panel half of whose windows contain marker-like strings.

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
- The gate is a linear scalar with initial value 0, in place of P9's `sigmoid(gate)` with initial value −2.0 (`studies/p9/model.py`). The zero gate makes a new store on an empty base change nothing, and keeps the *values* of newly appended rows out of the read until trained. Appended rows do take top-8 weight from first-stage rows from the moment of the append (§6.3, gate G5).
- Values are initialized from a normal distribution with standard deviation 0.02 *(lead's choice)*, never at zero: with gate 0 and values 0 both gradients vanish. Appended keys are initialized from the same distribution as first-stage keys *(lead's choice)*; the report states that the append cost depends on that initialization. Keys are initialized from a normal distribution with standard deviation 0.02 *(lead's choice; as P9's `_matrix`)*. Appended keys and values are drawn from the same distributions with the stage-2 seed (§9), never with the stage-1 seed. **[lead's choice]** The alternative, keys of unit scale, would make the keys move far less per update under the cosine score; the P9 convention is kept.
- **One gate per stage.** Rows written in stage k share gate g_k. Freezing a stage's rows freezes its keys, values and gate.

Definition. A store has rows s = 1…S with keys k_s ∈ R^16, values V_s ∈ R^d and stage index σ(s). For a unit query q: a_s = q·k_s/‖k_s‖; the 8 largest are selected, ties broken by the lowest row index; weights w = softmax(a/0.2) over the selected; r = Σ w_s · g_σ(s) · V_s, added to the output of block L at the read position. N = 4,096 rows per stage *(lead's choice)*; trainable parameters per stage N·(16 + 576) + 1 = 2,424,833. L is fixed by calibration from {4, 12} *(lead's choice)*.

- **Reference test.** On shared inputs the selection and weights equal those of the P9 flat memory forward, imported read-only. The test passes S2's own tensors explicitly to the P9 forward. S2 does not construct P9's `ScalableMemory` from a seed, so P9's `seed + 1000·k` derivation is not exercised (§9, gate G9). If the P9 forward cannot be given the tensors without editing P9, the reference test is dropped and the report says so **[lead's choice]**.
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

If one teacher fails §4.3, it is replaced once by `Helsinki-NLP/opus-mt-en-es` @ `5bc4493d463cf000c1f0b50f8d56886a392ed4ab` (Apache-2.0; `pytorch_model.bin` 312,087,523 B, SHA-256 `befce0f620e8e63f83bbb7f0818eb51d541cba28057a7cc14b00466d85c4994c` from the reviewer's saved Hub tree, `adr-0022-review/web/opus_en-es_tree.json`, to be checked at download; 77,484,009 parameters). **It is a Tatoeba-Challenge model (opus-2020-08-18), a different training regime from the primary pair; a fallback pair would mix regimes, and the report would say so.** If the fallback pair fails, or both primary teachers fail, the study stops with TRANSFER-INCONCLUSIVE: TEACHERS-NOT-QUALIFIED. The fallback teacher's files and the fallback's Tatoeba files (Spanish; rows 5 and 6 of §14.1) are fetched only if the rule above invokes the fallback. The human lead's approval covers them for that case only (§18). If the fallback is invoked, the invocation first returns to the human lead (the fallback is a reserved decision); partitions and panels are then rebuilt by the same rules and seeds with the fallback language in place of the failed one, before any training.

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
- **Identity groups** are the connected components of the graph whose nodes are gold pairs, with an edge when two pairs share a normalized English string, a normalized English string after contraction expansion (fixed list in the code), or any normalized reference string. A group goes whole to one side. The size distribution of identity groups is reported before assignment. Groups larger than 50 sentence pairs *(lead's choice)* go to the training side by rule. Of the remaining groups, the partition seed assigns groups to the **evaluation side** until it holds 20% of the remaining pairs (counted in pairs, not groups); the rest form the **training side**.
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
- **Sufficiency rule.** The in-vocabulary pools are counted before teacher generation is planned. If E_A or E_B cannot reach 500 items, E_C 250, or an accepted pool 8,000, the study stops with TRANSFER-INCONCLUSIVE: DATA-INSUFFICIENT. English sources in both accepted pools are split, by the training-draw seed of each replicate, into two halves assigned to A and B before drawing. Sufficiency requires, for each capability, its exclusive accepted sources plus its half ≥ 8,000 × 1.25 *(lead's choice)*, and 8,000 gold pairs per capability outside Q, D_cal and D_con; otherwise DATA-INSUFFICIENT. **[lead's choice]** The half is the smaller one when the shared count is odd; the gold pairs are in-vocabulary pairs of 3 to 10 words. All replicates draw from one accepted pool per capability, so their training draws overlap. The share of training items common to each pair of replicates is reported, and §9's reading of "every replicate" is given with that share.

### 5.3 Teacher outputs and verification

- **Teacher-only training sources.** T_A^r is drawn only from in-vocabulary no-German sources; T_B^r only from no-French sources. The student's German can come only from Teacher A, its French only from Teacher B. Gold references of training-side sentences are used for Q, D_cal, D_con and the gold control, never as student training targets in any arm that can earn the label.
- **Generation.** Beam 4, at most 48 new tokens, CPU, in the data-generation step. At most 60,000 sources per capability, a seeded sample *(lead's choice)* (seed 220903, §9). Tokens in and out, seconds and peak memory are recorded.
- **Acceptance filter.** An output is accepted if (a) its length-normalized beam log-probability (sum of the token log-probabilities of the returned hypothesis divided by its token count) is ≥ τ; (b) the ratio of its word count to the source's lies in [ρ1, ρ2]; (c) it differs from the source after normalization.
- **Fixing the filter.** (τ, ρ1, ρ2) is chosen on Q_fit from the grid τ ∈ {−0.05, −0.10, …, −0.60}, [ρ1, ρ2] ∈ {[0.5, 2.0], [0.6, 1.6]} *(lead's choice)* as the most permissive setting (largest accepted share) whose **95% Wilson lower bound** of precision on Q_fit — precision being the share of accepted outputs with chrF ≥ 0.60 against the best reference — is ≥ **0.90**. Among settings with the same accepted share, the one with the larger τ is taken, then the narrower length-ratio range **[lead's choice]**. The chosen setting must then show a point precision ≥ **0.90** on Q_check with at least 150 accepted items *(lead's choice)*; otherwise the teacher is not qualified. Selecting on the lower bound and checking the point estimate on held items keeps the chosen setting away from its own edge without making the check stricter. The precision and its 95% Wilson interval are reported. Splitting Q halves the items behind each figure: at the bar, a measured precision of 0.90 has a 95% Wilson interval of about 0.84–0.94 with 150 accepted items and about 0.87–0.92 if all 500 items of Q_check are accepted. The filter is fixed before the freeze.
- **What this verification is.** A measured property of the filter on gold-bearing sentences, applied to sentences without gold. It is not a per-item correctness check, and no-gold sentences may differ from gold-bearing ones. The human lead's rule "do not treat a teacher's generated answer as correct without suitable verification" is met in this sense and no other; the human lead has accepted the filter as the verification of the teachers' outputs (§18, item 4), and it is named in the label line (§11.3).
- **Distillation is sequence-level.** Cross-entropy on the accepted output text in the student's token ids, prompt positions masked. No teacher logits or token alignments.

### 5.4 Controlled addressing and routes

- **Prompts.** A: `English: {source}\nGerman:`; B: `English: {source}\nFrench:`. Target: the translation and a newline. Greedy decoding, stop at newline. The limit on new tokens is the 99.5th percentile of the gold references of D_cal in student tokens, measured in the rehearsal and frozen (rule fixed now).
- **Address.** For task t and vocabulary word w, the code u(t, w) is a fixed random unit vector in R^16 from a seeded hash of the pair (seed +10 of the replicate, §9; the hash takes that listed seed and the pair as inputs, as P9's `unit_code` does, and seeds no generator). The store is read at the last subword of each in-vocabulary source word with q = u(t, w), and at the last token of the task marker with q = u(t, ⟨task⟩). Out-of-vocabulary words and target positions are never read.
- **What the address is.** A hand-written function of the prompt (word segmentation, vocabulary table, task marker, hash). Gate G6 checks it takes the prompt only.
- **What cannot be claimed.** That the model decides where to look or knows its task; anything about learned sparse addressing. Every result is **oracle-assisted**.
- **Routes.** A route says which task codes a segment is read with: none, A, B, or both (combined task C2).
  - **Oracle route (the registered condition of every label row):** read from the task marker by rule; ordinary text has none. **There is no switch between memories in the primary arm**: one store, one top-8 over all rows.
  - **Every memory and every adapter arm is applied only under its route**: no read and no adapter on route "none".
  - **Learned-router lane (decides the GEN gate of §11.1; otherwise annotation).** Three router keys (A, B, none), cosine scores, a learned 16×576 projection of the student's hidden state at the last prompt token of a memory-free pass, top-1. Trained with route labels, with WikiText-2 *train* prefixes as "none", retrained at each stage on stored prompts. An answer-loss-only router is not run, because of P9-I's registered collapse. **It is a keyword-level classifier**: the prompts differ in a marker word, and a pass says nothing about fine-grained addressing. Router training: AdamW, learning rate 0.001, 500 updates of batch 64 *(lead's choice)*, on the stored prompts of the current stage's training streams only (never D_cal, D_con or an evaluation panel) and on WikiText-2 *train* prefixes of exactly 64 tokens in equal number; the projection is initialized from seed +3. The decision position in training matches GEN's (the 64th token of a "none" prefix; the last prompt token of a task prompt). **[lead's choice]** In detail, all **[lead's choice]**: "the current stage's training streams" are the prompts of T^r of every task the router of that snapshot must know — one stream for an ST1 router, T_A^r and T_B^r for a stage-2 or joint router; prompts only, and no teacher is run. Every batch holds the same number of examples of each class (each task, and "none") as nearly as 64 allows, the remainder going to "none". The "none" prefixes are consecutive non-overlapping 64-token pieces of the tokenized WikiText-2 train file, 8,000 of them sampled with seed +3. The hidden state is the output of block L, where the store would be read. The loss is cross-entropy over the cosine scores divided by the read temperature 0.2. The projection and then the router keys are drawn from N(0, 0.02) by one generator seeded +3; every router is trained from that initialization and is not continued from an earlier stage's router. A router depends on the replicate and on the set of tasks, not on the arm.
  - No learned slot-level addressing is run in S2. If S0 qualifies an interface, evaluating it in S2 needs a supplement approved by the human lead.

## 6. Stages

Every stage runs U updates of batch 32 with AdamW (no weight decay, clip 1.0, constant learning rate from calibration) and a fresh optimizer state. U = 2,000 or 1,000 by the rehearsal rule (§13.3). "First" and "second" are the capabilities in training order; both orders run in every replicate.

### 6.1 Stage 0

The untrained student and both teachers are scored on every panel.

### 6.2 Stage 1

**ST1**: a store of N rows trained on Teacher 1's accepted outputs. Version V1. It is also the single-teacher student of that capability.

### 6.3 Stage 2, from V1

| Arm | New capacity | First-stage rows | Replay | What it tests |
|---|---|---|---|---|
| **M-append-frozen** (mechanism i, primary) | N new rows appended to the same store | frozen bit-for-bit (keys, values, gate) | none | the second capability learned in the same store as an untouched first; one top-8 over all 2N rows; queries u(t, w); no switch. Retention is empirical, because first-capability reads can select the new rows |
| **M-ii** (mechanism ii: continued training with replay and a retention constraint) | starts from M-append-frozen's result | trainable | 32 replayed first-teacher rows added to each batch of 32 | whether the first capability survives when its rows are changed |
| M-seq (control) | none | trainable | none | a sparse store with oracle task codes trained in sequence without growth or replay; set beside L-seq, descriptively (H22-E) |

- **M-i-separate** (two stores behind the oracle route) is not trained. It is assembled from the two ST1 stores of the same replicate and reported as **BY CONSTRUCTION**. It enters no label.
- **Learned routing in mechanism (i)** is realized as learned keys of all rows competing in one top-8 under oracle queries, and a learned keyword router that decides whether the store is read. The human lead's phrase may intend more; this reading is stated, not assumed.
- **Append point.** M-append-frozen is also scored immediately after the append, before any update. The drop of the first capability at that point is reported as the *append cost*.
- **Mechanism (ii) has no objective beyond its loss.** It is continued training of all rows on the second teacher's material plus replay. The study does not claim it improves anything; it asks whether the first capability survives modification.
- **Retention constraint of M-ii.** Soft: the replayed rows. Hard: the new version is published only if, on D_con, chrF on each capability is at least the M-append-frozen version's minus 0.02 *(lead's choice)*; otherwise the cell is CONSOLIDATION-REJECTED and the pinned version stays.
- **Modification floor.** M-ii counts as retention under modification only if ‖V_1(after) − V_1(before)‖_F / ‖V_1(before)‖_F ≥ 0.10 over the first stage's value rows. Below that the cell is **RETENTION BY INERTIA** and cannot be class 5 (§11.2). The ratio is taken over all first-stage rows; rows never selected by any read cannot move, so the floor may be hard to reach, and the share of first-stage rows that changed at all is reported. In M-ii the first-stage gate g_1 is trainable, like the rows it scales; its change is reported. Because the acceptance check selects for retention, RET of a published M-ii is reported as "selected on D_con, then confirmed on E".
- Replay uses stored accepted outputs; no teacher is run again. Replay cells see twice the rows per update; updates and rows are reported.

### 6.4 Evaluation schedule

Every trained snapshot is scored on E_A and E_B after its stage; "before" is the parent snapshot's score, except in the RET gate and the retention negative zone, where it is V1 for every stage-2 arm (§11.1).

- **Combined tasks** (never trained on), scored for M-append-frozen, M-ii, M-joint, L-joint, L-seq, M-i-separate, L-sep and the ensemble:
  - C1, two sources: `English: {s1}\nGerman:` …, then after the model's own answer `\nEnglish: {s2}\nFrench:` …
  - C2, one source, both answers: the source words are read with both tasks' codes and the reads are summed.
  - Score: mean chrF of the two answers; an item passes if both match a reference exactly.
- **General-language quality.** Mean next-token negative log-likelihood on 200 windows of 256 tokens of WikiText-2 validation — **100 windows that contain any of the strings "German", "French", "English", "translation" or a line ending in ":", with at least one such string within tokens 1–64 of the window (the part the router sees)** (selected by rule with the GEN-window seed 220905, §9) and 100 ordinary windows *(lead's choice)* — with mean KL to the Stage 0 student and the share of unchanged top-1 tokens. This data is used for nothing else. **Window grid **[lead's choice]**.** The validation file is tokenized once as a whole in the data-generation step and cut from its first token into consecutive, non-overlapping windows of 256 tokens; a trailing remainder is dropped. A window is in the marker-like stratum if one of the strings lies wholly within the text of its tokens 1–64, and in the ordinary stratum if it contains none of the strings anywhere. A window whose only such strings lie after token 64 is in neither stratum and is not used. 100 windows of each stratum are sampled with the GEN-window seed. If either stratum has fewer than 100 windows on this grid, neither the grid nor the rule is changed and the work returns to the lead before the freeze. Under oracle routes every arm is bit-identical to the student on this panel; gate G5 checks it and the result is printed **BY CONSTRUCTION** and counts for nothing. It is measured for real in two conditions:
  - **(a) keyword-router condition — the registered GEN measurement.** For each window, the learned router of that snapshot reads the student's hidden state at token 64 of a memory-free pass. If it returns a task, the store is read with that task's codes at every in-vocabulary word of the whole window; if it returns "none", nothing is read. The loss is the mean next-token negative log-likelihood over tokens 65–256 of all 200 windows, and is compared with the unmodified student's loss on the same positions. Printed beside it: the router's false-trigger count per stratum, and the always-on loss increase (b). A pass is described as "the keyword router stayed silent", not as "the memory preserves general language". **GEN is measured for every ST1 and stage-2 memory snapshot** (the router of an ST1 snapshot knows one task and "none"), so general quality is reported before and after every stage; and for L-seq with the adapter applied when the router returns a task (comparison only).
  - **(b) always-on diagnostic** (reads with the first task's codes at every in-vocabulary word; adapter always applied), for M-append-frozen and L-seq. It enters no rule.
- **Seen-item scores** on 300 training items are reported for ST1 and M-append-frozen and enter no rule.
- Evaluation batches have a fixed composition, so scores do not depend on the worker.

## 7. Baselines and controls

All share partitions, U, batch size and the sequence-level loss. LoRA is implemented inside `studies/p10s2/`, on the query and value projections of all 30 blocks; with grouped-query attention the value projection is 576×192, so one rank costs 57,600 parameters. Rank 42 gives 2,419,200 (−0.23% against one stage of the store); rank 84 gives 4,838,400 (−0.23% against M-joint). Placement is fixed, not tuned; calibration tunes only its learning rate. LoRA form **[lead's choice]**: the update is (α/r)·B·A with α = r, a scale of 1; A is drawn uniform on ±1/√(fan-in), the conventional initialization (as ADR-0021 does for its dense control), from seed +8; B is zero, so an untrained adapter changes nothing; no dropout.

| Baseline | Definition | Trained? | Can show | Cannot show |
|---|---|---|---|---|
| Single-teacher students | ST1 of each order; LoRA-1 of each order | yes | what one teacher gives alone | — |
| **M-joint** — ordinary multi-teacher distillation (memory form) | one store of 2N rows from initialization on the mixed material of both teachers, 2U updates | yes | the bound for sequential arms | anything about order |
| **L-joint** — ordinary multi-teacher distillation (adapter form) | one LoRA of rank 84 on the mixed material of both teachers, 2U | yes | the ordinary multi-teacher student | anything about order |
| **L-seq** — sequential adapter | LoRA-1 continued on the second teacher's material, no replay | yes | forgetting of a dense adapter | — |
| **L-sep** | the two LoRA-1 adapters of a replicate behind the oracle route | assembled | the fair existing alternative to separate modules; BY CONSTRUCTION for retention | — |
| **E-table** | one trainable 576-vector per (task, vocabulary word) and per task marker, added at layer L at the same positions as the store's reads; no keys, no top-k; vectors drawn from N(0, 0.02) with seed +9 and multiplied by one linear scalar gate with initial value 0, as the store's values are **[lead's choice]** | yes, each capability | whether the keyed sparse store adds anything over a word-vector table | — |
| **MA-gold** | ST1 trained on Gold^r (8,000 gold pairs from gold-bearing sentences) | yes, each capability | a reference point for the teacher's material; not a bound | what the teacher adds item by item |
| **Ensemble** | the two teachers behind the oracle route, and behind the learned router | no | the quality ceiling and its cost | it is not a student |
| **R-exact** | table from training source to accepted output | no | zero hits on held-out items: confirms the panels are held out | — |
| **R-nn** | nearest training source by character-trigram TF-IDF cosine; return its output | no | sentence retrieval without composition | — |
| **R-icl** | the 4 nearest accepted pairs in the frozen student's prompt | no | retrieval that can generalize | its longer prompt is a cost, reported |
| **R-gloss** | co-occurrence lexicon (Dice) from accepted pairs; word-by-word output | no | the non-learned equivalent of a word-addressed store | — |

**Structural asymmetry, stated.** LoRA changes every position, including the generated ones; the store writes only at source positions. LoRA is the stronger class. That is acceptable for "the existing alternative".

**Dropped from revision 1:** M-grow, M-seq-R, L-seq-R. L-joint, dropped in revision 2, is restored; M-seq-shared, added in revision 2, is removed. The human lead's list names "sequential LoRA/adapters", which L-seq provides. Replay for adapters was the lead's earlier addition and is withdrawn.

**Ablations on every memory cell**, scored on a 300-item subsample of E_A and of E_B, drawn once with the ablation-subsample seed 220904 (§9) and the same for every cell and replicate *(lead's choice)*: memory off; values permuted across rows; **word codes** permuted across vocabulary words, the marker code kept; **marker-only** (word reads off); **words-only** (marker read off). For a stage-2 store, the ACQ2 controls permute the values of the second stage's rows among themselves and the word codes of the second task; first-stage rows and the first task's codes are left as they are. Control G values use the teacher and Stage 0 scores of the same 300-item subsample.

## 8. What "more parameters" is controlled by

M-append-frozen has 2N rows after Stage 2. It is read against M-joint (2N, simultaneous), M-seq (N, no growth), E-table (no keys) and L-sep (dense, separate). The value permutation shows whether the rows are used. The word "fusion" is used for no outcome.

## 9. Replicates, seeds, pairing

- **Four replicates, run unconditionally, if the rehearsal shows the whole study fits the cap with 2× headroom; otherwise three.** The choice is made by the rule of §13.3 and recorded before the freeze. There is no adaptive scheme: no replicate depends on another's result. **A positive label needs every replicate.**
- A replicate is a new training draw (T_A^r, T_B^r, Gold^r) and a new initialization. Evaluation panels, Q, D_cal, D_con and the vocabulary are common and fixed by the partition seed. E-table, MA-gold, M-seq and L-joint run in every replicate.
- Seeds: replicate bases 220001, 220101, 220201, 220301, each with these offsets:
  - +0 stage-1 store (keys, then values, from one generator in that order);
  - +1 training draw;
  - +2 batch order;
  - +3 router;
  - +4 permutation controls;
  - +5 gold draw;
  - +6 stage-2 appended rows;
  - +7 M-joint store;
  - +8 LoRA initialization;
  - +9 E-table initialization;
  - +10 oracle-code hash **[lead's choice]** (per replicate, as every data draw of P9-II and of S1 carries its own code seed; the alternative is one fixed code seed for all replicates).

  Within a replicate, the M-seq and M-ii arms start from the snapshots they continue. Partition seed 220901. The other partition-side streams each have a listed seed **[lead's choice]**: 220902 the Q split, 220903 the 60,000-source sample, 220904 the ablation subsample, 220905 the GEN window selection. (The re-check's text took these streams by a hash of (220901, stream name); a hashed seed would leave the listed sets.) Calibration draws use 221001 + 100·i and rehearsal draws 222001 + 100·i with the same offsets, i = 0…9; tests use 229001–229999. Every generator is seeded directly by a listed seed: **no "+1000·k" derivation is used**, and no seed is obtained by hashing or by arithmetic on another seed beyond the offsets listed here. One seed serves the uses that §9 pairs, in a fixed order **[lead's choice]**: +0 initializes ST1 of both orders and MA-gold of both capabilities; +6 the appended rows of both orders (keys, then values); +8 LoRA-1 of both orders and, with its own shapes, L-joint; +9 E-table of both capabilities; +1 and +5 draw capability A, then B.

  The implementation asserts that every seed actually passed to a generator lies in the listed sets and is disjoint from:
  - P1–P9-II (as listed in ADR-0021 §6.3);
  - S0 (200001–209999, 2001–2002, 2091–2092, 920001–920999);
  - S1 (210001–219999, 2101–2105, 2111, 2112, 2121, 2122, 2191–2192, 921001–921999).

  Every listed registered seed lies in S2's namespace 220001–228999 and outside S2's calibration (221001–221999), rehearsal (222001–222999) and test (229001–229999) ranges; gate G9 (§12.3) asserts it on the seeds actually used. The implementation writes the hash of every panel and stream to the data manifest. The reviewer's search of `src`, `studies`, `configs` and `tests` found numbers in this range only as parameter counts.
- Within a replicate every arm shares data, batch order where the data are the same, and the initialization of shared parameters.
- **Meaning of "every replicate":** if a mechanism's per-replicate pass probability were 0.5 or less, n of n passes would occur with probability at most 0.5ⁿ (0.0625 for four, 0.125 for three). The two orders share each replicate's draw and are not independent evidence. A true per-replicate pass rate of 0.8 gives 4 of 4 with probability 0.41. A positive at n of n is therefore evidence that the per-replicate pass rate exceeds one half; it is not a confidence interval on an effect, and INTERMEDIATE or NOT REPLICATED should be expected often. No interval across replicates is printed.
- Every class and label line prints "(n replicates, U = …)", under the oracle-assisted line of §11.3.

## 10. Measurements

### 10.1 Quality

- **chrF-norm.** chrF2 on normalized strings (§5.2): character n-grams n = 1…6, no word n-grams, whitespace removed before n-gram extraction, precision and recall averaged over the **effective** orders (orders at which both hypothesis and reference have at least one n-gram), then F with β = 2, as sacrebleu 2.5.1's default (`eps_smoothing=False`); an item with no effective order scores 0; scale 0–1; item score is the maximum over references; panel score is the mean over items. Implemented in the study, unit-tested on hand cases, and cross-checked against `sacrebleu` 2.5.1 on 1,000 pairs of Q in the data-generation step (agreement within 0.001 per item *(lead's choice)* with matching settings; analysis-only).
- Exact-match rate is descriptive only.
- **Gap closed:** G_c = (s_c(arm) − s_c(Stage 0)) / (s_c(teacher c) − s_c(Stage 0)), same panel. Defined only if the denominator is ≥ 0.30; otherwise NOT_EVALUATED.

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
| ACQ1 (ST1) | G_first ≥ 0.50; **G − max(G_value-perm, G_code-perm) ≥ 0.30** *(lead's choice)*; G_marker-only ≤ 0.25. Control G values use the teacher and Stage 0 scores of the same 300-item subsample |
| ACQ2 (stage-2 arm) | G_second ≥ 0.50 and ≥ 0.80 × the single-teacher student's G on that capability in the same replicate; the same lexical margin and marker-only limit (§7 says what is permuted) |
| RET | s_first after Stage 2 ≥ s_first after Stage 1 − 0.03, and G_first after ≥ 0.90 × G_first before. "after Stage 1" and "before" mean V1 (the ST1 snapshot) for every stage-2 arm, including M-ii **[lead's choice]** (the alternative is the parent snapshot, which for M-ii is M-append-frozen's) |
| Negative zones | acquisition G < 0.25; retention G_first after < 0.70 × before |
| GEN (keyword router) | in condition (a) of §6.4, loss ≤ the unmodified student's + **0.02 nats** per token *(lead's choice; revision 1's value)* on the 200-window panel of §6.4, of which 100 windows contain marker-like strings |

GEN is an empirical gate of the positive label and is measured only under the keyword router. Under oracle routes it is printed BY CONSTRUCTION and counts for nothing. GEN is not part of a mechanism class (§11.2); it enters at the label (§11.3).

### 11.2 Mechanism class (M-append-frozen, M-ii, M-seq, L-seq; per order; first match wins)

| Order | Class | Rule over all replicates |
|---|---|---|
| 1 | NOT_EVALUATED | ACQ1 fails in any replicate, or a gap is undefined |
| 2 | NO-NEW-CAPABILITY | G_second in the negative zone in every replicate |
| 3 | FORGETS | retention in the negative zone in every replicate |
| 4 | RETENTION BY INERTIA (M-ii only) | ACQ2 and RET pass in every replicate, and any cell is below the modification floor |
| 5 | ACQUIRES-AND-RETAINS | ACQ2 and RET pass in every replicate; for M-ii no cell is CONSOLIDATION-REJECTED |
| 6 | NOT REPLICATED | some replicate passes both ACQ2 and RET while another is in the negative zone of acquisition or retention |
| 7 | INTERMEDIATE | otherwise |

M-i-separate and L-sep are printed **BY CONSTRUCTION** and receive no class. Every class line is printed under the oracle-assisted line of §11.3.

### 11.3 Study label (first match wins)

| Order | Label | Rule |
|---|---|---|
| 1 | **ENGINEERING-FAILURE** | a defect found by gates G1, G4–G9; a hash mismatch; a difference between frozen and running code, configuration or data; the oracle-routed ensemble's score differing from the teacher's own |
| 2 | **INCOMPLETE** | a registered cell has no record, or a cap stopped a stage; no class is derived for a mechanism with a missing cell; no denominator is reduced |
| 3 | **TRANSFER-INCONCLUSIVE: TEACHERS-NOT-QUALIFIED** or **DATA-INSUFFICIENT** | §4.3 or §5.2; the study stops before the freeze |
| 4 | **TRANSFER-NEGATIVE: NO-ACQUISITION** | ST1's G is in the negative zone in every replicate, for both capabilities, within U updates |
| 5 | **TRANSFER-INCONCLUSIVE: CONTROL-FAILED** | a value permutation or a word-code permutation gives G ≥ 0.50 in any cell |
| 6 | **TRANSFER-POSITIVE WITHHELD — GENERAL QUALITY NOT PRESERVED UNDER A LEARNED ROUTE** | M-append-frozen is ACQUIRES-AND-RETAINS in both orders, with teacher-only training material, and its GEN gate fails in any replicate of either order |
| 7 | **TRANSFER-POSITIVE (append-frozen + consolidation)** | M-append-frozen and M-ii are both ACQUIRES-AND-RETAINS in both orders, with teacher-only training material (§5.3), and GEN holds for both in every replicate of both orders |
| 8 | **TRANSFER-POSITIVE (append-frozen)** | M-append-frozen is ACQUIRES-AND-RETAINS in both orders, with teacher-only training material, and its GEN holds in every replicate of both orders; row 7 does not apply |
| 9 | **TRANSFER-NEGATIVE: FORGETTING** | M-append-frozen is FORGETS in both orders |
| 10 | **TRANSFER-NEGATIVE: NO-ADDITIONAL-ACQUISITION** | M-append-frozen is NO-NEW-CAPABILITY in both orders |
| 11 | **TRANSFER-INCONCLUSIVE: ORDER-DEPENDENT** | M-append-frozen is ACQUIRES-AND-RETAINS in exactly one order |
| 12 | **TRANSFER-INCONCLUSIVE** | anything else; the classes are printed |

- **No result printed BY CONSTRUCTION satisfies any row of this table.**
- **Every label is printed with "(n replicates, U = …)"**, the design the rehearsal rule selected.
- Every TRANSFER-INCONCLUSIVE label prints the reason of each NOT_EVALUATED class: undefined gap, acquisition below 0.50, lexical margin below 0.30, or marker-only above 0.25.
- Row 6 is neither a positive nor a negative: acquisition and retention passed under controlled addresses, and the one gate that depends on a learned decision failed. It is reported with the false-trigger rate of the router on ordinary text and the loss ratio per replicate. When M-ii alone fails GEN, row 8 applies and the report says so.
- TRANSFER-POSITIVE means, numerically: in both orders and every replicate, on held-out sentences, ST1 closes at least half the gap, with a lexical margin of at least 0.30 over the permutation controls and marker-only at most 0.25; the appended rows close at least half the gap on the second capability and reach 0.80 of a single-teacher student; the first capability stays within 0.03 chrF and 0.90 of its gap closure, in one store read with one top-8; all student training material came from the teachers on sentences without gold; and, with a learned keyword router deciding whether the store is read, the loss on a general-language panel with marker-like windows rises by at most 0.02 nats per token in every replicate — that is, the keyword router stayed silent.
- Every label is printed with the fixed line: **"oracle-assisted (word-level addresses supplied by rule); lexical translation of short closed-vocabulary sentences, two capabilities of one kind; frozen English student; teacher-only training material verified by measured-precision filter; not autonomous learned memory."**
- The same line heads every mechanism-class line, every annotation and every table of the outcome report that prints a class or label, and every cost line.
- **No positive wording without it.** The human lead's instruction, verbatim: "S1 and S2 must not claim autonomous learned-memory success from oracle-assisted results." The words ACQUIRES-AND-RETAINS, TRANSFER-POSITIVE, QUALIFIED, COMPOSES, TRAINING COST COMPARABLE and FEWER VALUE ROWS ACTIVE, and every other class, mechanism, router, composition or cost line, are therefore printed only directly under that line: in the outcome report, in every table and figure caption, in the machine-readable outcome record (as a field of the same record), and in any summary a script writes to the terminal or to a log. The analysis refuses to write an output in which such a line lacks it, and the report test on synthetic records (§13.3, rehearsal content) checks every such line.
- Order now matters in substance: it decides which rows are frozen and which are appended.

### 11.4 Mandatory annotations (printed with the label; they do not change it)

| Annotation | Rule |
|---|---|
| NO ADVANTAGE OVER SEPARATE ADAPTERS | L-sep's scores on both capabilities are within 0.03 of M-append-frozen's or above, in at least one order |
| EQUIVALENT TO A WORD TABLE | E-table's G is within 0.03 of ST1's or above, on both capabilities, in every replicate |
| RETRIEVAL SUFFICES | R-icl's or R-nn's score is within 0.03 of M-append-frozen's or above on both capabilities |
| LEXICON-EQUIVALENT | R-gloss's score is within 0.03 of M-append-frozen's or above on both capabilities |
| TEACHER-EQUIVALENT-TO-GOLD | MA-gold's G is within 0.03 of ST1's or above |
| BELOW JOINT BOUND | M-append-frozen's G on either capability < 0.90 × M-joint's |
| TASK-CODED SPARSE RETENTION / NONE | M-seq's loss of G_first is smaller than L-seq's by ≥ 0.10 in every replicate of both orders / otherwise. Descriptive: a sparse store with oracle task codes against a dense adapter; not a test of sparsity |
| BELOW ADAPTER JOINT | M-joint's G on either capability < 0.90 × L-joint's (the two ordinary multi-teacher students, memory form against adapter form) |
| ROUTER (keyword-level) QUALIFIED / NOT QUALIFIED | route accuracy ≥ 0.99 on E_A, E_B and general prefixes, and M-append-frozen passes ACQ2 and RET with learned routes on the task panels, every replicate. (GEN under the router is a label gate, §11.1, and is printed beside this line.) |
| APPEND COST | the first capability's change in G at the append point, before training |
| COMPOSES C1 / C2 | mean over replicates of the combined score ≥ 0.80 × the mean of the arm's two single-task scores |
| EXACT-MATCH WEAK | gap closed on exact-match rate < 0.10 for either capability |
| Cost lines | always printed (§11.5) |

Every annotation, the ROUTER and COMPOSES lines included, is printed under the oracle-assisted line of §11.3, also when it appears in a table of its own.

### 11.5 Cost and active-memory lines (registered rules, descriptive standing)

For M-append-frozen after Stage 2, medians over replicates:

- **TRAINING COST COMPARABLE** if training wall seconds per stage ≤ 1.5 × LoRA-1's on the same device and U; otherwise TRAINING COST HIGHER, with the ratio.
- **FEWER VALUE ROWS ACTIVE** if the store's value parameters read per generated token ≤ 0.10 × the adapter parameters applied per generated token (both as defined in §10.2); always printed with the key products per read, which a flat scan does not reduce.
- **Stored size against the ensemble is arithmetic, not a comparison:** student plus a 2N-row store is 139,364,674 parameters against 148,613,487 for the two teachers, a ratio of 0.938. It is printed as such, with M-append-frozen's G on each capability.
- Teacher inference cost per accepted training item.

None is an efficiency result. Logical counts are never reported as measured efficiency. Each cost line is printed under the oracle-assisted line of §11.3.

## 12. Calibration, pilot and gates

### 12.1 Calibration (before the freeze; calibration seeds; D_cal only)

- Store: L ∈ {4, 12} at learning rate 0.003, for each capability: 4 cells. LoRA: learning rate ∈ {0.0003, 0.001}, for each capability: 4 cells *(lead's choice, the review's suggestion)*. Each is a Stage 1 of U = 2,000 updates on calibration draws.
- Rule: the setting with the higher mean over the two capabilities of chrF on D_cal; a difference below 0.01 goes to the first value listed. Calibration cells save a snapshot at 1,000 updates. If the rehearsal rule selects U = 1,000, the selection rule and the pilot gate are applied to those snapshots. Calibration scores are never reported as results. Nothing else is tuned. Evaluation panels are not scored before the registered run.

### 12.2 Pilot gate (before the freeze)

With the calibrated store setting, on D_cal, Stage 1 for **both** capabilities (these are calibration cells; no extra training). If either has a gap closed below 0.25, the registered run does not start: **NOT STARTED: STUDENT CANNOT USE THE MEMORY ON THIS TASK**, recorded with the calibration records. The pilot's scores are optimistic, because D_cal also selected the setting. They are not results.

### 12.3 Gates

- **G1** partitions (§5.2).
- **G2** the Stage 0 student and the stored teacher outputs score identically twice; every gap is defined on E_A and E_B (an undefined gap gives NOT_EVALUATED cells, not a stop).
- **G3** teacher qualification and filter precision (§4.3, §5.3), before the freeze.
- **G4** determinism of CPU evaluation (two scorings bit-identical; fixed batch composition; lowest-index tie rule); snapshot save and restore bit-identical; gradient reach (in M-append-frozen no first-stage row, gate or student parameter receives a gradient; in every memory arm no student parameter does); 20 updates on CPU repeated bit-identically; the same 20 updates on MPS agree with CPU in loss within 1e-3 and in parameters within a relative norm difference of 1e-4 *(lead's choice)*. `PYTORCH_ENABLE_MPS_FALLBACK` is unset, so any fallback is an error. macOS, torch and MPS versions are in the manifest.
- **G5** (a) On route "none", logits equal the frozen student's bit for bit on the general panel. (b) A new store with gate 0 on an empty base changes nothing. (c) **Gate isolation of appended rows:** after the append and before any update, the read r with the appended rows' values replaced by arbitrary finite values equals r with them at zero, bit for bit (so g₂ = 0 isolates the values). The appended rows do take top-8 weight from first-stage rows. That change is the **append cost** (§6.3), measured and not gated. Appended keys are initialized from the same distribution as first-stage keys *(lead's choice)*, and the report states that the append cost depends on that initialization. The distribution is normal with standard deviation 0.02, drawn with the stage-2 seed (§3, §9).
- **G6** the address function and the router take the prompt only; permuting references changes no address and no route.
- **G7** frozen bytes: every model file equals its pinned SHA-256 (large files) or git-blob SHA-1 (small files); every Tatoeba file, the converted student file, every teacher-output file and every token-id file equals the SHA-256 recorded at first download or creation. Checked at every load.
- **G8** student equivalence: the result recorded by the data-generation step (§14.2) is present and within tolerance, and the registered path's student reproduces the stored reference logits within the same tolerance, including the stored injection-point logits and the stored greedy sequences of §14.2 step 4.
- **G9** seeds (§9). Every generator in `studies/p10s2/` is seeded through one function, which records the seed and its purpose and refuses a seed outside the set allowed for the running stage. The gate asserts, on the seeds planned for the registry and again on the seeds actually recorded: every seed of the registered run is one of the listed registered seeds (a replicate base + 0…10, or 220901–220905), lies in 220001–228999 and lies outside 221001–221999, 222001–222999 and 229001–229999; every calibration seed lies in 221001–221999, every rehearsal seed in 222001–222999 and every test seed in 229001–229999; no recorded seed lies in a range of P1–P9-II, S0 or S1 listed in §9. A source check asserts that no generator is seeded anywhere else and that the global default generator is not used. The recorded seed list is written to the run record. A seed outside its set stops the run.
- The gates stage runs at real size on rehearsal seeds before the freeze and again on registered seeds before training. A failed gate stops the run.

## 13. Matrix and projected resources

### 13.1 Matrix per replicate

| Group | Cells | Units of U |
|---|---|---|
| ST1 (two orders) | 2 | 2 |
| M-append-frozen | 2 | 2 |
| M-ii (64-row batches, about twice the cost per update) | 2 | 4 |
| M-seq | 2 | 2 |
| M-joint | 1 | 2 |
| E-table (each capability) | 2 | 2 |
| MA-gold (each capability) | 2 | 2 |
| LoRA-1, L-seq | 4 | 4 |
| L-joint | 1 | 2 |
| **Trained cells per replicate** | **18** | 16 store-type + 6 LoRA |

**Four replicates: 72 trained cells. Three: 54.** Assembled without training: M-i-separate, L-sep. Scored without training: Stage 0, teachers, ensemble, four retrieval baselines, five ablations on each of 11 memory cells per replicate, the append point, the router lane, the always-on diagnostic, the timing benchmark. Calibration and pilot: 8 cells.

### 13.2 Charging rule

**Charged hours are the sum of wall-clock hours over all S2 processes: k parallel workers running for t hours charge k·t.** The data-generation step, calibration, pilot, rehearsal and the registered run are all charged. So is the second gates stage on registered seeds. The independent recomputation of §16 step 10 is not charged (§13.3). **Cap: 36 charged hours for S2.**

### 13.3 Projection — not a measurement

No figure below is measured on this machine. They come from operation counts and are uncertain by about a factor of three; the rehearsal replaces them.

| Work | Device | Per unit | Per replicate | Four replicates |
|---|---|---|---|---|
| Store-type unit of U = 2,000 | MPS, FP32 | 5–10 min | 16 units: 1.3–2.7 h | 5.3–10.7 h |
| LoRA unit of U = 2,000 | MPS, FP32 | 8–15 min | 6 units: 0.8–1.5 h | 3.2–6.0 h |
| Scoring E_A and E_B of a trained cell | CPU, 6 threads | 1.6–5.2 min | 18 cells: 0.5–1.6 h | 1.9–6.2 h |
| Combined panels, append point, ablations on 300 items, GEN and router lane, diagnostic, retrieval | CPU | — | 0.9–3.0 h | 3.6–12.0 h |
| Stage 0, teacher scoring, general panel, timing benchmark | CPU | — | — | 0.3–0.6 h |
| **Registered run** | | | | **14.4–35.5 h** |
| Second gates stage on registered seeds (inside R; not in the row above): four scorings of E_A and E_B at the rate above, plus at most 0.05 h for the repeated updates, the general panel and the hash checks | both | — | — | 0.1–0.4 h |
| Independent recomputation of every score (§16 step 10): an audit step after the registered run, **not charged** (§13.3); for information, one repetition of the three scoring rows, an upper estimate | CPU | — | — | 5.8–18.8 h |
| Data-generation step (teachers on at most 2 × 60,000 sources plus panels; conversion; token ids) | CPU | — | — | 1.0–1.8 h |
| Calibration and pilot (8 cells with scoring) | both | — | — | 1.0–2.2 h |
| Rehearsal | both | — | — | 1.5–3.0 h |
| **Before the freeze** | | | | **3.5–7.0 h** |

**Rehearsal rule, fixed now.** Let P be the hours already charged at the end of the rehearsal and R(n, U) the registered run projected from the rehearsal's measured rates for n replicates and U updates. The design is the first of the following for which P + 2·R ≤ 36:

1. four replicates, U = 2,000;
2. three replicates, U = 2,000;
3. four replicates, U = 1,000;
4. three replicates, U = 1,000;
5. none: the run is not started and the lead returns to the human lead.

**Rates and scope of the rule (revision 5).** R(n, U) contains, for n replicates: training; every scoring of the registered run; the timing benchmark; and the second gates stage on registered seeds. **The independent recomputation of every score (§16 step 10) is not in R and is not charged to the 36 hours** **[lead's choice]**. It is an audit step performed after the registered run by a separate auditor context, and the project's convention is that such a recomputation is not charged to the study's budget: the Opus recomputations of P9-I and P9-II were not charged to those studies. (The alternative not taken is the recomputation inside R.) For information, it is projected at 5.8–18.8 h for four replicates and 4.4–14.3 h for three, as one repetition of the three scoring rows, an upper estimate. It must respect the per-process memory limits of this section (8 GiB per worker, 24 GiB aggregate), and no result is reported before it completes. For U = 2,000 the training rates are those of the calibrated setting, rehearsed at full length. For U = 1,000 the setting may be re-selected (§12.1), and the read layer may change with it. R(n, 1,000) therefore uses, for every store-type cell, the slower of the rates measured at L = 4 and at L = 12 **[lead's choice]** (the slower rate counts more time against the cap; the re-check's text used the rates of the re-selected setting). The read layer that was not rehearsed at full length is measured on 200 rehearsal updates of each store-type cell type before the rule is applied, and that time is part of P. The second gates stage enters R at the time the rehearsal's gates stage measured. The outcome "none" is recorded as **NOT STARTED: BUDGET** with the rehearsal record. A re-design after it is a new decision of the human lead (§16).

Under-training is not traded for a fourth replicate before three full-length replicates have been tried *(lead's ruling)*.

The outcome of the rule is recorded before the freeze. On the table above, training and scoring come to the figures below (the re-check's recomputation; revision 4 printed 7.7 for 7.64). The second gates stage is projected at 0.11–0.40 h at every rung: it does not depend on n or U. That figure is unmeasured like the others, and the rehearsal's gates stage replaces it.

| Rung | Design | Training and scoring (h) | Second gates stage (h) | R (h) |
|---|---|---|---|---|
| 1 | 4 × 2,000 | 14.35–35.51 | 0.11–0.40 | **14.46–35.90** |
| 2 | 3 × 2,000 | 10.84–26.78 | 0.11–0.40 | **10.95–27.18** |
| 3 | 4 × 1,000 | 10.09–27.17 | 0.11–0.40 | **10.19–27.57** |
| 4 | 3 × 1,000 | 7.64–20.53 | 0.11–0.40 | **7.75–20.93** |

A rung holds only if its R measures at about 15 hours or less (14.5 h at P = 7.0, 16.25 h at P = 3.5), so rung 1 holds only at the fast end. **It is plausible that the rule ends at rung 2 or below, or at NOT STARTED: BUDGET.**

- **Runtime.** Training on torch MPS in FP32, which is not bit-reproducible; what is recomputed independently is every score, from saved snapshots, on CPU with deterministic algorithms. If the rehearsal finds an unsupported MPS operation, training moves to CPU and the rule above is applied to the CPU rates.
- **Other caps** *(lead's choice)*: 8 GiB per worker; 24 GiB aggregate; total download 1.5 GB; new disk use 6 GB.
- **Rehearsal content,** at full size on rehearsal seeds: every cell type for 200 updates; one store cell, one M-ii cell and one LoRA cell for the full U; 200 updates of each store-type cell type at the read layer that calibration did not select (for the rule's rates); one scoring of each kind; the truncation percentile of §5.4; the gates stage; analysis and report on synthetic records of the whole registry including missing cells, rejected consolidations, inertia cells and non-finite values.

## 14. Downloads, packages and the data-generation step

### 14.1 Downloads requiring the human lead's approval — none is made before it

**Approved by the human lead and recorded (§18):** rows 1–4 — the two teachers, the student and the Tatoeba exports; only if the fallback rule of §4.2 is invoked, rows 5 and 6, the fallback teacher and the fallback (Spanish) data; and the package wheels for the one-off data-generation step (§14.2). **Not approved, open with the human lead:** the two symmetry-check link files (6.2 MB, below), about which the lead has asked again; any package outside the lock other than those wheels. Nothing in the open list is fetched before a recorded answer of the human lead, given with the sizes in front of them. Implementation and tests on synthetic stand-ins need none of it. No download has been made.

| # | What | Source | Files | Size | License | Identity |
|---|---|---|---|---|---|---|
| 1 | Teacher A | `Helsinki-NLP/opus-mt-en-de` @ `6183067f…b0ca4` | `pytorch_model.bin`, `config.json`, `generation_config.json`, `source.spm`, `target.spm`, `vocab.json`, `tokenizer_config.json` | 300.8 MB | CC-BY-4.0 | revision and SHA-256 pinned now |
| 2 | Teacher B | `Helsinki-NLP/opus-mt-en-fr` @ `dd7f6540…67f18` | same file names | 303.7 MB | Apache-2.0 | pinned now |
| 3 | Student | `HuggingFaceTB/SmolLM2-135M` @ `93efa2f0…e75a2` | `model.safetensors`, `config.json`, `generation_config.json`, `tokenizer.json`, `tokenizer_config.json`, `vocab.json`, `merges.txt`, `special_tokens_map.json` | 272.4 MB | Apache-2.0 | pinned now |
| 4 | Tatoeba exports | `https://downloads.tatoeba.org/exports/per_language/` | `eng/eng_sentences.tsv.bz2` (24,947,715 B), `deu/deu_sentences.tsv.bz2` (12,144,786 B), `fra/fra_sentences.tsv.bz2` (9,805,546 B), `eng/eng-deu_links.tsv.bz2` (3,557,634 B), `eng/eng-fra_links.tsv.bz2` (2,679,128 B) | 53.1 MB | CC BY 2.0 FR | no revision exists; SHA-256 recorded at first download and frozen |
| 5 | Fallback teacher, only if invoked | `Helsinki-NLP/opus-mt-en-es` @ `5bc4493d…ed4ab` | as rows 1–2 | 315.3 MB | Apache-2.0 | pinned now |
| 6 | Fallback data, only if invoked | same Tatoeba site | `spa/spa_sentences.tsv.bz2` (6,376,323 B), `eng/eng-spa_links.tsv.bz2` (1,762,602 B) | 8.1 MB | CC BY 2.0 FR | recorded at first download |
| | **Total** | | | **930 MB approved and fetched (rows 1–4); 8.1 MB + 315.3 MB more only if the fallback is invoked (1,253 MB in all). Not in these figures: the package wheels (approved, §14.2; about 23 to 32 MB for the eight named packages, their dependencies recorded at fetch time); 6.2 MB of symmetry-check link files (not approved)** | | |

- **Tatoeba, what was checked (read-only, 2026-11-15).** The project's downloads page states the files are "released under CC BY 2.0 FR" and that the exports are updated every Saturday. The per-language directory indexes for `eng`, `deu`, `fra` and `spa` are readable without an account and list the files above with the sizes shown (dated 14-Nov-2026). The auditor's HEAD requests for the five primary files returned HTTP 200 with matching lengths, so the files are served without an account. Sentence files have three tab-separated columns (id, language, text). **TO VERIFY AT DOWNLOAD:** the column format of the per-pair link files (the downloads page documents "Sentence id" / "Translation id"); the sizes, which change weekly. The `eng/` link files are used, and their symmetry is checked at download against `deu/deu-eng_links.tsv.bz2` and `fra/fra-eng_links.tsv.bz2`, whose listed sizes differ slightly (3,552,331 B and 2,678,076 B); those two files add 6.2 MB. **They were in no figure shown to the human lead and are not approved.** The human lead's answer on the package wheels did not name them, and the lead has asked again (§18). The symmetry check against them is made only if the human lead approves them; they are then fetched in the same session as row 4. Without them the check is not made, and the data manifest and the report say that the symmetry of the link files was not checked **[lead's choice]**.
- **One session.** The five files of row 4 (and the two link files, if approved) are fetched in one session, because a later fetch would come from a different weekly export. The fallback's Tatoeba files are not fetched with them. If the fallback is invoked, they come from a later weekly export: link rows whose English sentence id is absent from the frozen English file are dropped and counted, the dates of both sessions are recorded, and the report states the mix **[lead's choice]**.
- **How.** Plain HTTPS of the pinned `resolve/<revision>/<file>` addresses for the models and of the addresses above for Tatoeba, each followed by a hash check. No account, no token, no Hub client in the download step. Files go to a git-ignored directory named by source and revision or download date.
- CC BY 2.0 FR and CC-BY-4.0 require attribution in any publication. No data and no weights are redistributed by this study.

### 14.2 The data-generation step (once, before the freeze; the only place where packages outside the lock are used)

Run with `uv run --locked --with-requirements studies/p10s2/requirements-datagen.txt`; `uv.lock` and `pyproject.toml` are untouched. It does, offline after the downloads:

1. hash checks of every downloaded file;
2. conversion of the pinned student weights to a plain FP32 torch file, whose SHA-256 is frozen;
3. **student equivalence test:** the study's torch student against the reference implementation on the pinned weights, on a fixed 256-token text from WikiText-2 train, FP32, CPU: maximum absolute logit difference ≤ 1e-3 and identical top-1 token at every position *(lead's choice)*; the reference logits are stored for gate G8;
4. token ids of every text segment (§2). **Conventions.** A model input is the concatenation of segment ids. Each segment is tokenized with its leading space where whole-string tokenization would attach one, BOS follows the reference tokenizer's default for this model, read from the pinned `tokenizer.json`/`tokenizer_config.json` and recorded in the data-generation step; the draft expects "not prepended" (the same convention in the equivalence logits and every registered input), and newline separators are their own segments. Raw NFC text is tokenized; normalization is used only for identity and chrF. The position of the last subword of each in-vocabulary word comes from the reference tokenizer's offsets and is stored, not recomputed. The registered path's stop rule fires on the first generated token whose bytes contain 0x0A and cuts the text at the first newline. Decoding is over whole sequences, never token by token, with the reference's error policy. **Tests:**
   - (a) segment ids against whole-string ids for every training row, evaluation prompt and R-icl prompt; mismatch rate reported; 0 required on prompts; target mismatches are listed, and the training loss uses the segment ids;
   - (b) `decode(encode(x)) == x` for every reference and accepted teacher output;
   - (c) the study's decoder against the reference on 1,000 random id sequences, including split multi-byte characters, not only on valid text;
   - (d) logits at the injection point: with a fixed vector added at the output of block L, the study's student matches the reference with a forward hook at the same place within 1e-3 (this pins the off-by-one between "output of block L" and `hidden_states[L+1]`); the logits are stored for G8;
   - (e) greedy decoding with a key–value cache against full recomputation, and against the reference `generate`, on 100 prompts: identical tokens; the sequences are stored for G8;
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
| sacrebleu | 2.5.1 | analysis-only cross-check; exists on PyPI, Apache-2.0, no advisories (`CONFIRM.md` §6); brings portalocker, regex, tabulate, colorama, lxml and numpy |

- Transitive dependencies are fixed by one resolution written to `requirements-datagen.txt` with exact versions and hashes, which is part of the freeze. **That the set resolves with torch 2.8.0 on Python 3.12 has not been run.**
- **The one relevant advisory.** GHSA-29pf-2h5f-8g72 (CVE-2026-4372, fixed in 5.3.0): a malicious `config.json` carrying `_attn_implementation_internal` can make `from_pretrained` execute code. Mitigation: the configuration files are hash-pinned, and the reviewer checked that the pinned ones contain no such key; loading is offline from local paths with no remote code; downloads are plain HTTPS with SHA-256 checks; weights are loaded in weights-only mode (torch 2.8.0 is past the fix for CVE-2025-32434). The other advisories listed against 4.57.1 concern interfaces this step does not call.
- **Package wheels are themselves downloads. The human lead has approved them (§18):** the eight packages named above and the dependencies the resolver requires for them, pinned with exact versions and hashes in the requirements file of the freeze, installed with `uv run --locked --with`; `uv.lock` and `pyproject.toml` do not change. The 938 MB figure did not include them. From the reviewer's saved index records (`adr-0022-review/web/pypi_*.json`), the wheels of the eight named packages for macOS arm64 and Python 3.12 total about 23 MB, or about 32 MB if numpy's larger wheel is the one selected. The transitive dependencies are not in those records; their names, versions, hashes and sizes are recorded at fetch time. Nothing else is installed outside the lock without a further answer. By §16 the wheels are fetched with the downloads, after implementation on synthetic stand-ins.

## 15. Departures from project practice that need explicit acceptance

1. A pretrained student, against the handoff's "first tests use a train-from-scratch small model".
2. Training on MPS without bit reproducibility; snapshots are the object, scores are reproduced on CPU. A re-run would not reproduce the snapshots.
3. A 36-hour cap. The human lead has said this figure is acceptable (§18).
4. Pickle weight files for the teachers, loaded once in weights-only mode.
5. A CC-BY-4.0 teacher and CC BY 2.0 FR data: attribution owed on publication.
6. Packages outside the lock in a pre-freeze data-generation step, whose outputs the registered run consumes as frozen data.
7. Data without a revision identifier: frozen by recorded hash, not by pin.

**Standing of each item at revision 5.** Item 2 rests on the human lead's answer recorded in §18 (training on MPS with every score recomputed on CPU). Item 3 rests on the human lead's sentence "im confortable with does number …" quoted in §18, which answered the lead's message listing S0 16 h, S1 12 h, S2 36 h, total 64 h (§18). Item 6 rests on the human lead's approval of the package wheels (§18) and reaches no other package. Items 1, 4, 5 and 7 are neither reserved for the human lead in §16 nor yet accepted: their acceptance is for the lead's approval record in §18, under the delegation "we can change it to  p10 can be self approve but p10-I need my review". This revision does not record that acceptance.

## 16. Order of work, stop rules, reserved decisions

**Order.** (1) The human lead's answers on the reserved items below: recorded in §18, except the link files. (2) Lead's approval, recorded in §18. (3) Implementation review as the work proceeds. (4) Implementation with tests on synthetic stand-ins, before any download. (5) Downloads of the approved files (§14.1) and of the approved wheels (§14.2); data-generation step. (6) Partitions; filter fitting; G3; calibration; pilot. (7) Rehearsal; implementation audit; rehearsal rule. (8) Freeze of code, configuration, requirements file, seeds, thresholds, filter, calibration record, rehearsal-rule outcome, data manifest. (9) The registered run, once; the router of each ST1 and stage-2 snapshot is trained and its GEN measurement taken inside the run. (10) Independent recomputation of every score from snapshots; outcome report.

**Stop rules.** A failed gate or any difference from the freeze stops the run. A stage that would exceed a cap is not started. Nothing is re-run with changed settings. A second attempt after an engineering stop needs the human lead's decision. Failed runs and failed checker attempts are kept.

**Reserved for the human lead.**

The five items the auditor left for the human lead, with their state at revision 5 (§18 holds the words), and a sixth from the re-check. The lead does not decide them:

1. The downloads of the two teachers (300.8 MB + 303.7 MB), the student (272.4 MB) and the Tatoeba data (53.1 MB), and, only if the fallback rule is invoked, the fallback teacher and data (315.3 MB + 8.1 MB) (§14.1). **Answered: approved.**
2. The package wheels for the data-generation step (§14.2; about 23 to 32 MB for the eight named packages, their dependencies recorded at fetch time). **Answered: approved.**
3. Whether two translation directions are "complementary capabilities". **Answered: yes.**
4. Whether a filter of measured precision counts as "suitable verification" (§5.3). **Answered: yes.**
5. Acceptance of training on MPS and of packages outside the lock (§15 items 2 and 6). **Training on MPS with scores recomputed on CPU: answered, yes. Packages outside the lock: approved for the data-generation wheels of item 2 and for nothing else.**
6. The two symmetry-check link files (6.2 MB, §14.1). **Open: not approved.** The answer on item 2 did not name them; the lead has asked again.

Nothing in an open item is fetched or installed before a recorded answer.

Also reserved: any change of thresholds, arms, models, data or budget after the freeze; a second attempt; any model above 2 billion parameters, any cloud spend, any account or login, any further download; use of the locally present Ollama weights (not used here); learned slot-level addressing inside S2 (a separately approved supplement if S0 qualifies an interface); use of S2's outcome in any P10 system claim; merge, publication, weight release, ADR-0012.

## 17. What S2 cannot establish

- **Autonomous learned memory.** Addresses and routes are supplied by rule.
- **Anything about routing beyond keyword detection.** A pass of the GEN gate means the keyword router stayed silent, including on windows with marker-like words; it does not mean the memory preserves general language; it says nothing about preservation under learned fine-grained addressing.
- **That the sparse keyed store beats a word-vector table,** unless E-table loses.
- **That knowledge came from the teachers rather than from gold data,** unless the teacher-only arm passes; and even then each training item was accepted by a filter of measured precision, not checked.
- **Retention as an advantage.** Retention in the shared store is retention against crosstalk that the shared top-8 itself creates; a word table with task-partitioned rows or separate adapters retain by construction.
- **That sparsity protects earlier knowledge.** Different tasks touch different rows only because their oracle codes differ (H22-E).
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

**Human lead's decision on the downloads — 2026-11-15 (UTC), verbatim:**

> "yes s0 should include the penalty and i approve s2 download"

It answered the lead's question: "Approve the S2 downloads? They total 938 MB, or 1,253 MB with the fallback teacher. S2 cannot start without them." The message before it described them as "the student model, the Tatoeba exports and the package wheels for data generation". (The first half of the sentence concerns ADR-0020.)

Recorded by the lead:

- **Reserved item 1 is answered: approved.** The student (272.4 MB), the Tatoeba data (53.1 MB), and, only if the fallback rule of this ADR calls for them, the fallback teacher and data (315.3 MB + 8.1 MB), at the pinned revisions and with the licence checks of §14.1. Nothing else may be downloaded.
- **Reserved item 2:** the lead reads the approval as covering the package wheels for the one-off data-generation step, because the question named them and the total included them. They are installed outside the lock with `uv run --locked --with`, pinned in the requirements file of the freeze; `uv.lock` and `pyproject.toml` do not change.
- **Reserved items 3, 4 and 5 have no answer** (complementary capabilities; the precision filter as suitable verification; training on MPS). The lead does not decide them.
- No download has been made at the time of this record. By §16 the downloads come after implementation on synthetic stand-ins.

**Human lead's answers on reserved items 3, 4 and 5 — 2026-11-15 (UTC), verbatim:**

> "s2.1 yes s2.2 yes, s2.3 yes"

The three questions as the lead put them, in this order: "1. Do two translation directions (English→German, English→French) count as "complementary capabilities"? Yes, or the study needs a different second capability. 2. Is a filter with measured precision of at least 0.90 "suitable verification" of the teacher's outputs? Yes or no. 3. May S2 train on the Mac's GPU, with scores recomputed on CPU? Yes or no."

Recorded by the lead:

- **Item 3: yes.** Two translation directions are accepted as the two capabilities of this study. They remain two capabilities of one kind, and §17 still limits what a result can mean.
- **Item 4: yes.** The filter of §5.3 with measured precision ≥ 0.90 is accepted as the verification of the teachers' outputs.
- **Item 5: yes, as asked:** training on MPS with every score recomputed on CPU. The question did not name "packages outside the lock"; the lead reads them as covered only for the data-generation wheels already recorded above, and nothing else is installed outside the lock without a further answer.
- All five reserved items now have an answer. No reserved item is decided by the lead.

**Correction by the lead — 2026-11-15 (UTC), after the re-check of revision 4 (`adr-0022-review/RECHECK_REV4.md`, J3 and J4).** The record above of reserved item 2 contains a false statement and is superseded here; the text above is kept as written.

- The 938 MB figure shown to the human lead did **not** include the package wheels. It is 938.2 MB = teachers 604.5 + student 272.4 + Tatoeba 53.1 + Spanish (fallback) data 8.1. The lead's message named the wheels beside that figure but gave them no size, and did not mention the 6.2 MB of symmetry-check link files at all.
- Therefore **reserved item 2 (package wheels) and the link files are not answered.** The lead does not read the approval as covering them. No wheel and no link file is fetched until the human lead says so with their sizes in front of them.
- The same applies to "packages outside the lock" in item 5: unanswered beyond MPS training itself.
- The download scope of §4.2, §14.1 and this section disagree on whether the Spanish data are fetched with the main session or only if the fallback is invoked (J3). Until revision 5 settles the text, the narrowest reading holds: fallback teacher and fallback data only if the fallback rule is invoked.
- Implementation on synthetic stand-ins needs none of these.

**Human lead's answer on the package wheels — 2026-11-15 (UTC), verbatim:**

> "yes I do, yes we can raise to 16 and I approve the package"

The third clause answered the lead's question: "Approve the package wheels and the 6.2 MB of link files for S2? These were not in the 938 MB figure." (The first two clauses answer other questions.)

Recorded by the lead:

- **The package wheels for the one-off data-generation step are approved:** the eight packages named in §14.2 and the dependencies the resolver requires for them, pinned in the requirements file of the freeze, installed with `uv run --locked --with`; `uv.lock` and `pyproject.toml` do not change. The eight named packages come to about 23 to 32 MB; the transitive dependencies are recorded at fetch time.
- **The two symmetry-check link files (6.2 MB) were not named in the answer and stay not approved.** The lead has asked again. Until an answer names them they are not fetched and the symmetry check is not made (§14.1).
- **Context of the second quotation at the head of this section** ("im confortable with does number …"): it answered the lead's message listing S0 16 h, S1 12 h, S2 36 h, total 64 h. The human lead has since raised S1's cap to 16 h; S2's 36 h is unchanged. §15 item 3 rests on it.

**Download scope as revision 5 states it** (one statement for §4.2, §14.1, §14.2 and §16; it adds no approval and removes none):

- Approved by the human lead and recorded above: the two teachers, the student, the Tatoeba data; the fallback teacher and the fallback (Spanish) data only if the fallback rule of §4.2 is invoked; the package wheels for the one-off data-generation step.
- Not approved, open with the human lead: the 6.2 MB of symmetry-check link files; any package outside the lock other than those wheels.
- Nothing in the open list is fetched before a recorded answer. Implementation and tests on synthetic stand-ins need none of it.
- The re-check's paste-ready edits to the earlier records (E-J3 for item 1, E-J4 for item 2 and for the last bullet) are not applied to those records: the lead's correction keeps them as written and supersedes them. E-J3's "fetched in the same session" is not adopted (§14.1).

**§15 departures 1, 4, 5 and 7 (J9).** Their acceptance is for the lead's approval record, under the delegation "we can change it to  p10 can be self approve but p10-I need my review". It is not given in this revision.

Lead's approval: PENDING. Revision 5 answers the re-check (majors J1–J8, minors J9–J14 and others; §21) and awaits an independent confirmation.

## 19. Map of the review of revision 1 to this revision

**Segment-level tokenization (flagged in revision 3; examined in `CONFIRM.md` §3; conventions and tests (a)–(e) now in §14.2 step 4).** Because the registered path has no tokenizer (M9), a model input is the concatenation of token ids of segments tokenized separately in the data-generation step (§2, §14.2). This can differ from tokenizing the whole string at segment boundaries (for example around the newline before a marker). It is the same for every arm and for the reference scores, but it is a definition that the review of revision 1 did not see, and it changes what "the student's prompt" is.

| Finding | Change | Where |
|---|---|---|
| B1 | Label row "i only" deleted. Primary arm is M-append-frozen (one store, appended rows, frozen first-stage rows, one top-8, no switch). M-i-separate assembled, BY CONSTRUCTION, no class, no label. The probe's 22–27% cited. "No BY CONSTRUCTION result satisfies any row." | §1, §6.3, §11.2, §11.3 |
| B2 | Training material is teacher output on sentences with no gold in that language. Acceptance filter defined; precision ≥ 0.90 at chrF ≥ 0.60, fitted on Q_fit and required again on Q_check. MA-gold redefined on gold-bearing sentences. Positive rows require teacher-only material. Qualification gate kept. | §0, §4.3, §5.2, §5.3, §7, §11.3 |
| B3 | Gated copy dropped. Tatoeba's own exports, files and sizes listed; hashes recorded at first download. One download table under the required heading; student and data awaiting the human lead. | §5.1, §14.1 |
| M1 | Modification floor 0.10; RETENTION BY INERTIA as a class; "selected, then confirmed"; mechanism (ii) named as continued training with replay, no objective claimed. | §6.3, §11.2 |
| M2 | E-table in every replicate; EQUIVALENT TO A WORD TABLE. | §7, §11.4 |
| M3 | Marker-only and words-only ablations; word codes permuted with the marker code kept; marker-only ≤ 0.25 in ACQ1 and ACQ2; CONTROL-FAILED at G ≥ 0.50, placed after NO-ACQUISITION. | §7, §11.1, §11.3 |
| M4 | Connected-component identity groups with contraction expansion and shared references; extended G1; neighbour share reported. Adapted: with no test files, groups are assigned by the partition seed. | §5.2 |
| M5 | All arms gated by route; GEN printed BY CONSTRUCTION under oracle routes and counting for nothing there; counted only under the learned keyword router, where revision 3 makes it a gate of the positive label; always-on diagnostic. | §5.4, §6.4, §11.1, §11.3 |
| M6 | Revision 2 added M-seq-shared; the auditor withdrew that advice (C3). Revision 4 removes it: M-seq against L-seq is descriptive, annotation TASK-CODED SPARSE RETENTION. | §1, §6.3, §11.4 |
| M7 | Pilot on both capabilities, with the optimism caveat. | §12.2 |
| M8 | Reduced matrix (19 cells per replicate in revisions 2 and 3; 18 after C3 and C9); charged hours as the sum over processes; replay-without-growth controls removed outright. Replication follows the lead's rulings (four or three by the rehearsal rule, no adaptive scheme), not the review's two-then-three scheme. | §9, §13 |
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

**The lead's rulings on the ten points listed in revision 2** (applied in revision 3; superseded where the confirmation changed them): rehearsal rule order (§13.3); ablations on a 300-item subsample fixed by seed (§7); no sequential adapter with replay — the human lead's list names sequential adapters, and replay for adapters was the lead's earlier addition, withdrawn (§7); fallback teacher kept with its regime stated (§4.2); fit/check split of Q (§5.3); package wheels left to the human lead (§16); segment-level tokenization accepted (§14.2); general-language preservation an empirical gate under the keyword router with TRANSFER-POSITIVE WITHHELD (§11). Superseded: "M-seq and M-seq-shared both run" (C3); "20% of identity groups" (C6: 20% of pairs, large groups to training); "5% relative" (C4: 0.02 nats).

**Map of the confirmation of revision 3 (`CONFIRM.md`) to revision 4:**

| Finding | Change | Where |
|---|---|---|
| C1 | G5 replaced with the auditor's text (route "none"; empty base; gate isolation of appended values); append cost measured, not gated; key initialization stated. | §3, §12.3 |
| C2 | Control limits replaced by the lexical margin G − max(G_value-perm, G_code-perm) ≥ 0.30; marker-only ≤ 0.25 kept; reason line on every TRANSFER-INCONCLUSIVE label. | §11.1, §11.3 |
| C3 | M-seq-shared removed; H22-E descriptive; annotation TASK-CODED SPARSE RETENTION / NONE (M-seq against L-seq); freed units to L-joint. | §1, §6.3, §11.4, §13.1 |
| C4 | GEN at + 0.02 nats; 100 of 200 windows chosen for marker-like strings; false-trigger counts per stratum; wording "the keyword router stayed silent"; measured for every ST1 and stage-2 snapshot. | §6.4, §11.1, §11.3, §17 |
| C5 | Filter selected on the 95% Wilson lower bound on Q_fit; point precision ≥ 0.90 on Q_check. | §5.3 |
| C6 | Group size distribution reported; groups above 50 pairs to training; 20% of remaining pairs to evaluation. | §5.2 |
| C7 | Calibration snapshots at 1,000 updates; selection and pilot re-applied at the chosen U; "(n replicates, U = …)" on every class and label; NO-ACQUISITION "within U updates"; meaning of "every replicate". | §9, §11.3, §12.1 |
| C8 | Tokenization conventions and tests (a)–(e); G8 extended. | §12.3, §14.2 |
| C9 | L-joint restored at rank 84; the reading of "learned routing" stated. | §6.3, §7, §13.1 |
| C10 | chrF over effective orders, as sacrebleu 2.5.1's default. | §10.1 |
| m1 | Added to "cannot establish". | §17 |
| m2 | g_1 trainable in M-ii, change reported. | §6.3 |
| m3 | ACQ2 controls permute second-stage values and the second task's codes. | §7 |
| m4 | `eng/` link files used; symmetry checked at download. | §14.1 |
| m5 | All Tatoeba files in one session. | §14.1 |
| m6 | Supplement sentence restored. | §5.4, §16 |
| m7 | Floor may be hard to reach; share of changed rows reported. | §6.3 |

**Not applied verbatim (listed, not resolved silently):**

1. **C8, BOS.** The auditor's text leaves "[prepended / not prepended]" open. This revision writes "not prepended" as the lead's choice. If the reference tokenizer's default for this model prepends it, the convention must be reconsidered before the freeze, because the student was trained with whichever convention its authors used. *Revision 5: replaced by the re-check's rule; BOS follows the reference tokenizer's default (§14.2).*
2. **C4, which snapshots.** "Every ST1 and stage-2 snapshot" is applied to the memory snapshots that are read under a router (ST1, M-append-frozen, M-ii, M-seq, M-joint) and to L-seq for comparison. E-table and MA-gold snapshots are scored for GEN as well only if the lead wants them; as written they are not, to keep the scoring within the projection.
3. **C9, added annotation.** BELOW ADAPTER JOINT (M-joint against L-joint) is this draft's addition, so that the restored cell is read against something. It changes no label.
4. **m3.** The auditor asked the ADR to "say whether"; the choice made (second-stage rows and second-task codes only) is this draft's.
5. **m4.** Checking symmetry needs the `deu/` and `fra/` link files (6.2 MB more), which the download table did not list before; they are now named under row 4. *Revision 5: these two files are not approved and are open with the human lead (§14.1, §18).*
6. **C7, "(n, U)".** Printed on class and label lines; annotations inherit it from the label they accompany.

## 20. The lead's choices in one list

Rulings (given by the lead on the review and on revision 2):

- Primary arm M-append-frozen; no label from anything BY CONSTRUCTION.
- Teacher-only training material; acceptance filter with measured precision ≥ 0.90.
- Tatoeba's own exports, not the gated copy; hashes recorded at first download.
- Registered path on the locked environment only; teachers in a pre-freeze data-generation step.
- Four replicates if the rehearsal rule allows, otherwise three; every replicate needed for a positive; no adaptive scheme.
- Rehearsal rule order 4 × 2,000 → 3 × 2,000 → 4 × 1,000 → 3 × 1,000 → not started.
- Evaluation panels of 1,000 items per capability where the data allow.
- Cap of 36 charged hours with 2× headroom; charged as the sum over processes.
- E-table, MA-gold, M-seq and L-joint (rank 84) in every replicate; M-seq-shared dropped (C3 accepted); no L-seq-R; fallback teacher kept.
- Ablations on a 300-item subsample fixed by seed.
- Identity groups larger than 50 pairs to training; 20% of the remaining pairs to evaluation; fit/check split of Q, with selection on the Wilson lower bound.
- GEN under the keyword router, at most 0.02 nats per token, on 200 windows of which 100 are chosen for marker-like strings, every replicate; TRANSFER-POSITIVE WITHHELD otherwise.
- Lexical margin of 0.30 over the permutation controls.
- "(n replicates, U = …)" on every label.

Numbers and settings chosen in drafting and standing unless the lead changes them:

| Item | Value | Section |
|---|---|---|
| Rows per stage; key width; top-k; temperature | 4,096; 16; 8; 0.2 | §3 |
| Value width and initialization | 576, no projection; normal, standard deviation 0.02 | §3 |
| Read layer candidates | {4, 12} | §3, §12.1 |
| Closed vocabulary; sentence length | 2,000 word types; 3–10 words | §5.2 |
| Panels E_C, E_open, D_cal, D_con | 500, 500, 500, 300 | §5.2 |
| Training material per capability per replicate | 8,000 accepted outputs; 8,000 gold pairs for MA-gold | §5.2 |
| Teacher generation | beam 4, at most 48 new tokens, at most 60,000 sources per capability | §5.3 |
| Filter grid; precision criterion; minimum accepted on Q_check | τ from −0.05 to −0.60 in steps of 0.05, two length-ratio ranges; chrF ≥ 0.60; 150 | §5.3 |
| Teacher qualification | own score ≥ 0.55; margin ≥ 0.30 | §4.3 |
| Batch; optimizer; calibration learning rates | 32; AdamW, no decay, clip 1.0; store 0.003, LoRA {0.0003, 0.001} | §6, §12.1 |
| Consolidation acceptance; modification floor | drop ≤ 0.02 on D_con; ≥ 0.10 relative change | §6.3 |
| General panel | 200 windows of 256 tokens, 100 with marker-like strings; router decision at token 64; + 0.02 nats | §6.4, §11.1 |
| BOS convention; key initialization | the reference tokenizer's default (expected: not prepended); normal, standard deviation 0.02, appended rows drawn with the stage-2 seed | §14.2, §3 |
| Acquisition; ratio to single teacher; retention | G ≥ 0.50; ≥ 0.80; drop ≤ 0.03 and ≥ 0.90 of G | §11.1 |
| Controls; negative zones | lexical margin ≥ 0.30; marker-only ≤ 0.25; G < 0.25, retention < 0.70 | §11.1 |
| CONTROL-FAILED threshold | G ≥ 0.50 under a permutation | §11.3 |
| Annotation margins | 0.03; 0.90 of the joint bound; 0.10 for task-coded sparse retention; 0.99 route accuracy; 0.80 for composition | §11.4 |
| Cost lines | 1.5× training time; 0.10 active-value ratio | §11.5 |
| Gap defined | denominator ≥ 0.30 | §10.1 |
| Pilot stop | gap closed < 0.25 on either capability | §12.2 |
| Tolerances | MPS against CPU: loss 1e-3, parameters 1e-4; student equivalence: logits 1e-3, identical top-1; chrF cross-check 0.001 | §12.3, §14.2, §10.1 |
| Memory and download caps | 8 GiB per worker; 24 GiB aggregate; 1.5 GB download; 6 GB disk | §13.3 |
| Seeds | replicate bases 220001, 220101, 220201, 220301 with offsets +0…+10; partition-side streams 220901–220905; every generator seeded directly | §9 |

**Choices made in revision 5 where the re-check left a point open** (each marked **[lead's choice]** in the text; rule used: the P9 / P9-II convention where one exists, otherwise the option that is harder for a positive label or counts more time against the cap):

| Point | Choice | Alternative not taken | Section |
|---|---|---|---|
| J1 seed derivation | every generator seeded directly by a listed seed; offsets +0…+10 per replicate | P9's `seed + 1000·k`, which lands in S2's own calibration and rehearsal ranges with the present bases | §9, G9 |
| J1 partition-side streams | listed seeds 220902–220905 | a hash of (220901, stream name), which leaves the listed sets | §9 |
| J1 oracle-code seed | per replicate (+10) | one fixed code seed for all replicates | §5.4, §9 |
| J1 appended rows | own seed +6, keys then values | reuse of the stage-1 seed (duplicates the first-stage keys) | §3, §9 |
| J1 seeds shared between cells | +0 for ST1 of both orders and MA-gold; +8 for LoRA-1 and L-joint; +9 for E-table of both capabilities | a separate seed per cell | §9 |
| J2 key initialization | normal, standard deviation 0.02, as P9's `_matrix` | unit-scale keys | §3 |
| J5 marker placement | at least one marker-like string within tokens 1–64 of every window of that stratum; windows with such strings only later are not used | keep such windows and report their share | §6.4 |
| J6 router recipe | AdamW, 0.001, 500 updates of batch 64; prompts of every task the router must know; balanced classes; 8,000 "none" prefixes of 64 tokens; hidden state at block L; cross-entropy over cosine scores at temperature 0.2; trained from seed +3 for every snapshot | the second stream only at stage 2; the final layer's hidden state; continuing the earlier router | §5.4 |
| J7 disjoint draws | shared accepted sources split in halves by each replicate's training-draw seed; pool ≥ 8,000 × 1.25 per capability; 8,000 gold pairs per capability; overlap between replicates reported | draws disjoint across replicates (pool ≥ n × 8,000), harder to satisfy; one split fixed by the partition seed | §5.2 |
| J8a rates after re-selection | the slower of the rates at L = 4 and L = 12 | the rates of the re-selected setting | §13.3 |
| J8b scope of R | second gates stage inside R and the 36 hours; the independent recomputation not charged (the P9-I / P9-II convention), within the memory limits, and no result reported before it completes | the recomputation inside R | §13.2, §13.3 |
| P9 reference test | tensors passed explicitly to the P9 forward; `ScalableMemory` never constructed from a seed; the test is dropped, and the report says so, if that needs an edit of P9 | constructing the P9 module with a seed | §3 |
| J10 RET reference | V1 for every stage-2 arm | the parent snapshot (M-append-frozen's for M-ii) | §6.4, §11.1 |
| J11 LoRA form | α = r; A uniform on ±1/√(fan-in), B zero; no dropout | α = 2r; A normal with standard deviation 0.02 | §7 |
| J11 E-table | N(0, 0.02) with a linear scalar gate at 0, as the store | zero vectors without a gate | §7 |
| J12 filter tie-break | larger τ, then the narrower length-ratio range | first in grid order | §5.3 |
| J14 window grid | consecutive non-overlapping 256-token windows from the first token; fewer than 100 in a stratum returns to the lead | overlapping windows; filling a short stratum from the other | §6.4 |
| Seed gate | G9, with a failure counted under ENGINEERING-FAILURE like G4–G8 | an assertion outside the gate list | §11.3, §12.3 |
| Link files not approved | the symmetry check is not made and the report says so | not starting the data-generation step without it | §14.1 |
| Fallback data from a later export | link rows to English ids absent from the frozen file dropped and counted | fetching the 8.1 MB with row 4, as revision 4's table said | §14.1 |

## 21. Map of the re-check of revision 4 (`RECHECK_REV4.md`) to revision 5

| Finding | Change | Where |
|---|---|---|
| J1 (major) generator seeds | Offsets +0…+10 per replicate; listed stream seeds 220902–220905; direct seeding, no +1000·k; S1's ranges listed; gate G9 on the seeds actually used; G9 in ENGINEERING-FAILURE | §3, §5.3, §5.4, §7, §9, §11.3, §12.3 |
| J2 (major) key initialization | Normal, standard deviation 0.02; appended rows from the stage-2 seed | §3, §12.3 |
| J3 (major) download scope | One statement: rows 1–4 approved; fallback teacher and data only if invoked; link files and wheels open. E-J3's "same session" for the fallback data not adopted | §4.2, §14.1, §16, §18 |
| J4 (major) wheels not in the figure | The figure's content stated; the human lead's later approval of the wheels recorded; the link files stay open; sizes from the saved index records where they exist | §14.1, §14.2, §16, §18 |
| J5 (major) marker placement | At least one marker-like string within tokens 1–64 | §6.4 |
| J6 (major) router recipe | E-J6, with data, balance, layer, loss and initialization stated | §5.4 |
| J7 (major) disjoint draws, gold | E-J7; overlap between replicates reported | §5.2 |
| J8 (major) rung rule | Slower of the two read layers' rates at U = 1,000; second gates stage inside R and shown in the rung table; recomputation not charged, by the P9-I / P9-II convention; NOT STARTED: BUDGET | §0, §13.2, §13.3 |
| J9 departures 1, 4, 5, 7 | Acceptance placed with the lead's approval record; not given here | §15, §18 |
| J10 RET reference | V1 for every stage-2 arm | §6.4, §11.1 |
| J11 LoRA scaling, E-table | α = r, conventional initialization; E-table as the store | §7 |
| J12 filter tie-break | Larger τ, then the narrower range | §5.3 |
| J13 finite values | "arbitrary finite values" | §12.3 |
| J14 window grid | Consecutive non-overlapping windows; strata defined | §6.4 |
| Re-check §2: stale parenthetical, 7.6, unnamed outcome | Parenthetical deleted; 7.6–20.5 h; NOT STARTED: BUDGET | §0, §13.3 |
| Re-check §3 minor: S1 ranges | Listed | §9 |
| Re-check §4: fallback SHA-256 | Added from the reviewer's saved Hub tree | §4.2 |
| Re-check §4: stale sentences | Header; §14.1 opening; §14.2 wheels and sacrebleu; §5.3; closing lists | header, §5.3, §14.1, §14.2, closing lists |
| Re-check §1 C8: BOS (E-m3) | The reference tokenizer's default, recorded | §14.2, §19, §20 |
| Re-check §5: oracle line (E-5) | The line heads every class, annotation, router, composition and cost line; no positive wording without it | header, §9, §11.2–§11.5 |

**Not applied verbatim (listed, not resolved silently):**

1. **E-J1, named streams.** The re-check took them by a hash of (220901, stream name). Revision 5 gives each a listed seed, because the lead's instruction for this revision is that every seed actually used stays inside 220001–228999 and outside the calibration, rehearsal and test ranges.
2. **E-J3.** The re-check's text fetched the fallback's Tatoeba files in the same session as row 4. Revision 5 follows the lead's correction in §18: fallback teacher and fallback data only if the fallback rule is invoked.
3. **E-J3 and E-J4, edits to the §18 records.** Not made. The earlier records are kept as written; the lead's correction supersedes them and the statement at the end of §18 gives the scope.
4. **E-J8.** The re-check's text used the rates of the re-selected setting; revision 5 uses the slower of the two read layers' rates. The re-check's text also charged the independent recomputation inside R; by the lead's ruling it is not charged, following the P9-I / P9-II convention (§13.3).
5. **E-J9.** The re-check's sentence records the lead's acceptance. Revision 5 does not record it; it is left to the lead's approval record.
6. **Additions beyond the re-check's text**, each marked **[lead's choice]**: the details of the router recipe, the window grid, the LoRA and E-table forms, the filter tie-break, gate G9, the handling of a later fallback export, the rule for the P9 reference test, the rebuilding of partitions for a fallback language, and the projection of the second gates stage.

## Open questions for the lead

1. Should acquisition and retention with learned routes on the task panels also gate the label, or is the general panel alone what the human lead's requirement means? As drafted, only the general panel gates it.
2. In the GEN measurement the router decides once per window, from token 64. Is one decision per window the right unit, or should it decide per line?
3. Should FORGETTING of M-append-frozen in both orders be a study-level negative (row 9, as drafted), given that the append cost may be large before any training and depends on the key initialization?
4. BOS: settled by rule in revision 5 (the reference tokenizer's default, recorded in the data-generation step).
5. Should GEN also be scored for E-table and MA-gold snapshots?
6. Should the equivalence tolerance (1e-3) be replaced by a measured run-to-run difference of the reference, as the auditor prefers?
7. The choices of revision 5 listed at the end of §20, each with its alternative. The heaviest in consequence: training draws that overlap between replicates; the oracle-code seed per replicate; the recomputation outside the charged hours.

## Things the lead must verify before approval

- The human lead's answer still open: the two symmetry-check link files (§16); the lead has asked again.
- The per-pair link-file format, the symmetry of the link files, and the sizes on the day of download (account-free access was confirmed by the auditor's HEAD requests).
- That the package set of §14.2 resolves with torch 2.8.0 on Python 3.12. Not run; it is run when the approved wheels are fetched (§16 step 5).
- That Marian loading in `transformers` 4.57.1 accepts the pinned German repository despite its tokenizer configuration.
- Every throughput figure of §13.3; none is measured.
- That enough in-vocabulary no-gold sources and gold-bearing identity groups exist; unknown until the files are read.
- The six items listed under "Not applied verbatim" in §19.
