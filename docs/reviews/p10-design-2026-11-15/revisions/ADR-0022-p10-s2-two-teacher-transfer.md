# ADR-0022 — P10-S2: Two-teacher sequential knowledge transfer into expandable learned memory

- **Status: DESIGN REVISION 1 — NOT YET REVIEWED. SPEC: PENDING ASTRA REVIEW. Nothing is implemented, downloaded, installed or run.**
- **Date:** 2026-11-15 (UTC)
- **Origin.** The human lead's P10 direction, milestone question 2: "Can ArborLM sequentially acquire complementary capabilities from two pretrained teacher models while preserving earlier capabilities?" The binding requirements are quoted where they are used.
- **Study code** P10S2. **Package** `studies/p10s2/`. **Seed namespace** 220001–229999, disjoint from every earlier study (§9).
- **Roles (study-specific).** Lead: Claude Fable 5.2. Specification audit, implementation audit and recomputation: Opus 5.5, in contexts separate from implementation, receiving code and records and not the lead's conclusions. Implementation: Sonnet 5.5. Inventory: Haiku 5.5. The model that actually ran each delegated task is recorded from session metadata. ADR-0012 stays not approved. **Astra review: NOT_PERFORMED.**
- **Relation to other work.** S2 is one of three independent P10 experiments (S0 addressing, S1 capacity, S2 transfer). It does not wait for S0 and uses no result of S0 or S1. Its outcome label is independent of CAPACITY-POSITIVE and SYSTEM-POSITIVE. P1–P9 code, records and ADRs are not edited; S2 imports nothing that it would need to change.
- **Evidence it rests on.** P9-I (ADR-0017 Part I): oracle-addressed memory stores and returns answers (R1 0.967–1.000, R2 1.000); every learned query interface collapsed onto 1–6 slots (`results/p9i-run-attempt2-2026-11-15/OUTCOME.md`). No registered evidence exists on capacity, incremental learning (ADR-0017 Lane D never ran) or teachers. `docs/RESEARCH_HANDOFF.md` Phase 5 names teacher migration as an optional later branch with "verify exact checkpoint and license before choosing".

Numbers marked **[lead's choice]** are judgment calls of this draft.

## 0. Frank assessment before the design

1. **The smallest credible demonstration is narrow.** A sparse key–value memory with controlled addresses is a lookup table. It can carry a capability only if the capability decomposes into units that recur between training items and held-out items. Procedural skills (arithmetic, code-output prediction) have no such unit under a controlled address: a hash of the item gives a held-out item an untrained address, so generalization is zero by construction. This draft therefore adopts a **lexical** capability pair (translation into two languages) and says plainly that a positive result would show transfer of *lexical knowledge used compositionally by a frozen student*, not transfer of a skill.
2. **Two of the five required gates are true by construction in the primary lane.** With Memory A frozen and oracle routing, retention of A on single-task items is bit-exact, and with no read on ordinary text the general-language quality is bit-exact. The draft does not count these as empirical findings. Empirical retention comes only from arms that modify A's parameters (§6.3) or let a learned router err (§5.4), and the label says which one passed (§11).
3. **The natural existing alternatives are strong and may well win.** Separate adapters behind a task switch, a co-occurrence lexicon, and retrieval of demonstrations into the prompt can all do this task. S2 measures them and prints the comparison with the label. S2 is not designed to show superiority and cannot.
4. **Where gold data verifies the teacher, the teacher is nearly redundant as a data source.** Verified teacher outputs here are, by the verification rule, gold references that the teacher reproduced. The study tests the pipeline (teacher → verification → sequence-level distillation → sequential memory versions) and retention. A gold-only control (§7) measures how much the teacher contributes.
5. **Risk of an uninformative negative.** The proposed student is an English model. Whether a frozen English model can emit German and French when lexical vectors are injected at one layer is unknown. A pre-freeze pilot gate (§12.2) stops the study before the registered run if it cannot.

## 1. Question and hypotheses

**Can a frozen pretrained student with an expandable sparse memory acquire, one after the other, two capabilities from two pretrained teachers, keeping the first when the second is added, when addresses are controlled?**

- **H22-A (acquisition).** Training Memory A on Teacher A's verified outputs closes at least half of the teacher–student gap on held-out items of capability A, and the gain disappears when the memory's values or unit codes are shuffled.
- **H22-B (additional acquisition).** Adding new capacity and training it on Teacher B's verified outputs, without resetting anything, closes at least half of the gap on capability B and reaches at least 0.80 of what a single-teacher B student reaches.
- **H22-C (retention under modification).** A consolidation step that changes Memory A's parameters, with replay and a retention constraint, keeps capability A within 0.03 chrF.
- **H22-D (sparse locality helps retention).** Sequential training in one sparse memory without replay forgets less than a parameter-matched dense adapter trained the same way.
- **H22-E (order).** H22-A to H22-C hold in both orders, A→B and B→A.
- **H22-F (general quality).** With a learned router, the student's next-token loss on ordinary English text rises by at most 0.02 nats per token.

Each can fail. H22-D failing while H22-A to H22-C hold would mean the result owes nothing to sparsity.

## 2. The student (design problem 1)

**Adopted as primary: option (a), a new small pretrained student, frozen.**

| Item | Value | Source and confidence |
|---|---|---|
| Repository | `HuggingFaceTB/SmolLM2-135M` (base model, not the instruct variant) | Hub API, read 2026-11-14 |
| Revision | `93efa2f097d58c2a74874c7e644dbc9b0cee75a2` (last modified 2025-02-06) | Hub API `sha`; re-check at download |
| License | Apache-2.0 | Hub API `cardData.license` and tags |
| Parameters | 134,515,008 (stored BF16) | Hub API safetensors metadata |
| Weight file | `model.safetensors`, 269,060,552 bytes, LFS oid `80521b40281d6ce74e35c9282c22539e75aa0ac8578892b2a59955ef78d55da1` | Hub tree API |
| Architecture | believed 30 blocks, width 576, 9 heads, BPE vocabulary 49,152 | **from memory, not verified; read from `config.json` at download** |

- Loaded as FP32 (about 0.54 GB). **No student parameter is trained in any memory arm.**
- **Cost of this choice.** A third model to download; `transformers` and six other packages outside the lock (§14); the memory generalized from width 32 to the student's width; a subword tokenizer in place of bytes; training on MPS, a departure from the CPU-only practice of P1–P9 (§15). None of the P9 code is reused except as a numerical reference for the read (§3).
- **Why not option (b)** (the 27,392-parameter byte backbone with teachers reduced to symbol tables). It would keep the audited code and cost minutes, but the "teachers" would be lookup tables with a model's name on them, the student has no general-language quality worth preserving, and the result would repeat P9-I's oracle rungs. It would not answer the milestone question.
- **Why this student and not a larger or multilingual one.** A multilingual student of 0.5B parameters already translates, which shrinks the gap the gates are measured on; a 70M model is weaker at composition. 135M is the smallest model for which a held-out composition test is plausible [lead's choice]. GPT-2 small (MIT, 124M) is the alternative if the pilot gate fails for reasons specific to this model; changing the student needs a revised specification.

## 3. The memory, generalized in width

The mechanism is the project's (ADR-0017 §5.1): cosine keys, top-8 sparse read, read temperature 0.2, values added to the residual stream.

- A memory M has N = 4,096 slots [lead's choice]: keys K ∈ R^{N×16}, values V ∈ R^{N×d} with d the student's width, and a scalar gate g (initial value 0, so a new memory changes nothing until trained). There is no output projection: a value is added directly to the residual [lead's choice; a narrower value with a projection is the alternative]. Trainable parameters per memory: N·(16 + d) + 1 = 2,424,833 at d = 576.
- **Read.** For a query q (unit vector in R^16): a_s = q·k_s/‖k_s‖; the 8 largest a_s are selected; weights softmax(a/0.2) over the selected; r = g · Σ w_s V_s. r is added to the output of block L at the read position. L is fixed by calibration from {4, 12} [lead's choice].
- **Reference test.** On shared inputs the selection and weights must equal those of the P9 flat memory forward (`studies/p9`), imported read-only.
- **Version store.** Every memory state is an immutable snapshot with a manifest and content hash: V0 (empty), V1 (after the first stage), V2-i, V2-ii and so on. A reader pinned to V1 must be unaffected while V2 is prepared; rollback is the pinning of the earlier manifest. This is an engineering property, tested, and not a scientific result.

## 4. Capabilities and teachers (design problem 2)

### 4.1 Primary pair

| | Capability A | Capability B |
|---|---|---|
| Task | English → German, short sentences | English → French, short sentences |
| Teacher | `Helsinki-NLP/opus-mt-en-de` | `Helsinki-NLP/opus-mt-en-fr` |
| Revision | `6183067f769a302e3861815543b9f312c71b0ca4` (2023-08-16) | `dd7f6540a7a48a7f4db59e5c0b9c42c8eea67f18` (2024-02-14) |
| License | **CC-BY-4.0** (Hub API and model card) | Apache-2.0 (Hub API) |
| Weights | `pytorch_model.bin`, 297,928,209 bytes, LFS oid `da068344…206bdd` | `pytorch_model.bin`, 300,827,685 bytes, LFS oid `cc1de10b…0d64de` |
| Parameters | about 74 million, **inferred from file size, not stated by the Hub; count at load** | same |
| Tokenizer | SentencePiece (`source.spm`, `target.spm`) | same |

- **Why this pair.** Each teacher has one capability and cannot produce the other's language, so complementarity is as demonstrable as it can be. Both are small enough for CPU inference. Correctness is checked against held gold references, never against the teacher.
- **Honest limit.** These are two instances of one kind of capability. A reader may say "complementary" should mean different kinds. A heterogeneous pair (for example translation plus code-output prediction from a small code model) was considered and rejected for the primary lane because the second capability has no recurring unit for a controlled address (§0 item 1). It could only run under learned addressing, which S2 does not test.
- **Security note.** Both teacher repositories publish pickle weights only (no safetensors file on `main`). They are loaded with `torch.load(..., weights_only=True)` after the file's SHA-256 is checked against the pinned oid, converted once to safetensors locally, and the pickle is not loaded again.

### 4.2 Fallback, fixed now

If one teacher fails qualification (§4.3), it is replaced by `Helsinki-NLP/opus-mt-en-es` (English → Spanish; revision `5bc4493d463cf000c1f0b50f8d56886a392ed4ab`; Apache-2.0; `pytorch_model.bin` 312,087,523 bytes) and qualification is run once more for the new pair. If that fails, or both primary teachers fail, the study stops with TRANSFER-INCONCLUSIVE: TEACHERS-NOT-QUALIFIED. No third pair is tried. The fallback's data files are downloaded only if it is invoked.

### 4.3 Teacher qualification gate (before any student training; registered)

On the qualification panel Q (§5.2; 1,000 items with German and French references), with score s = mean sentence chrF against the best reference (§10.1):

1. Each teacher on its own capability: s ≥ 0.55 [lead's choice].
2. Margin: own-capability score minus the larger of (the other teacher's score on that capability, the untrained student's score on it) ≥ 0.30 [lead's choice].
3. Verified-output yield on the training side (§5.3) is enough for the smallest permitted training set (8,000 per capability per replicate).

The model card reports chrF 0.664 on an older Tatoeba test for the German teacher; that is the card's claim and is not relied on.

## 5. Data and addressing

### 5.1 Sources

| Data | Use | License | Size | Pin |
|---|---|---|---|---|
| `Helsinki-NLP/tatoeba_mt`, files `data/dev/tatoeba-dev.deu-eng.tsv` (25,137,632 B), `data/dev/tatoeba-dev.eng-fra.tsv` (21,044,993 B), `data/test/tatoeba-test.deu-eng.tsv` (3,135,265 B), `data/test/tatoeba-test.eng-fra.tsv` (2,097,757 B) | prompts and gold references | CC-BY 2.0 (card; the link is the French version of the licence) | 51.4 MB | dataset revision `f337793bd1dbb50077995b8df53e16bc58451f33` as read 2026-11-14; the repository showed a modification that same day, so **re-read the sha at download and record file SHA-256** |
| Fallback only: `tatoeba-dev.eng-spa.tsv` (16,211,945 B), `tatoeba-test.eng-spa.tsv` (2,284,102 B) | as above | as above | 18.5 MB | as above |
| WikiText-2 raw, validation and train parquet, already local (`data/wikitext2/`) | general-language panel; router negatives | CC BY-SA as recorded in ADR-0004; local use approved | 0 new | existing pin |

No procedurally generated alternative exists for translation gold. Row counts of the four files are not known to this draft; §5.2's sufficiency rule handles that.

### 5.2 Partitions (built and hashed before any teacher runs)

- Normalization for identity: Unicode NFC, lower case, punctuation stripped, whitespace collapsed. An English sentence is identified by the SHA-256 of its normalized form.
- **Evaluation side:** every English sentence that occurs in either *test* file, with all its references from all four files. **Training side:** every other English sentence. Any training-side sentence whose hash equals an evaluation-side hash is impossible by construction; gate G1 checks it anyway, over every panel pair.
- **Closed vocabulary:** the 2,000 most frequent word types [lead's choice] of training-side sentences of 3 to 10 words. A sentence is *in-vocabulary* if all its words are.
- Panels, sampled with the partition seed from in-vocabulary sentences of 3–10 words:

| Panel | Side | Size | Content |
|---|---|---|---|
| E_A, E_B | evaluation | 1,000 each | held-out sentences with German / French references |
| E_C | evaluation | 500 | held-out sentences with both; basis of the combined tasks |
| E_open | evaluation | 500 | sentences with at least one out-of-vocabulary word (descriptive only) |
| Q | training side, then removed | 1,000 | qualification, both references |
| D_cal | training side, then removed | 1,000 | calibration and pilot only |
| D_con | training side, then removed | 500 | acceptance constraint of mechanism (ii) only |
| T_A^r, T_B^r | training side | 16,000 each per replicate r | verified teacher outputs; T_A^r and T_B^r are disjoint in English sentences |

- **Evaluation is on held-out sentences only.** No evaluation sentence is a training prompt of any arm. What is shared between training and evaluation is the vocabulary: the test is composition of seen words into unseen sentences. Seen-item (memorization) accuracy is reported on 500 training items per cell and enters no rule.
- **Sufficiency rule, fixed now.** If the pools cannot supply a panel: E_A/E_B fall to 500 and E_C to 250; T falls to 8,000. Below that the study stops with TRANSFER-INCONCLUSIVE: DATA-INSUFFICIENT.

### 5.3 Teacher outputs and verification (design problem 3)

- Each teacher translates every training-side in-vocabulary sentence once: beam 4, maximum 48 new tokens, on CPU. Tokens in and out, seconds and peak memory are recorded.
- **Verification.** An output is accepted only if, after the normalization of §5.2, it equals one of the gold references of that sentence. Everything else is rejected. The rejection rate is reported per teacher, with the chrF distribution of the rejected outputs.
- Consequence, stated: accepted outputs are gold references the teacher reproduced, and the accepted set is biased toward easy sentences.
- **Distillation is sequence-level.** The student is trained by cross-entropy on the accepted output *text*, tokenized by the student's own tokenizer, with the prompt positions masked. No teacher logits or teacher token alignments are used, since the tokenizers differ.

### 5.4 Controlled addressing (design problem 4)

- **Prompts.** Capability A: `English: {source}\nGerman:`; capability B: `English: {source}\nFrench:`. The target is the translation followed by a newline. Greedy decoding, at most 32 new tokens, stop at newline.
- **Address.** For a task t and a vocabulary word w, the unit code is u(t, w) = a fixed random unit vector in R^16 from a seeded hash of the pair (the R1 construction of ADR-0017 §5.3). The memory is read at the last subword of each in-vocabulary source word with q = u(t, w), and once at the last token of the task marker with q = u(t, ⟨task⟩). Out-of-vocabulary words and target positions are never read.
- **What the address is.** A deterministic, hand-written function of the prompt text (word segmentation, a vocabulary table, the task marker, a hash). It uses no reference and no teacher output; gate G6 checks that the address function takes the prompt only and that changing the references changes no address.
- **What it isolates.** With addresses fixed and well separated, any failure is a failure of storing, combining or retaining values, not of finding them. That is the purpose: S2 asks about acquisition and retention with the P9-I collapse taken out of the picture.
- **What cannot be claimed.** That the model decides where to look; that the model knows which task it is doing; anything about learned sparse addressing. Every S2 result is **oracle-assisted** and is reported under that word.
- **Routing.** A route is the set of tasks whose memories are read for a segment: ∅, {A}, {B} or {A, B}.
  - **Primary lane (oracle route):** the route is read from the task marker by rule. Ordinary text has no marker, so its route is ∅.
  - **Learned-router lane (reported separately):** three router keys (A, B, none) with cosine scores and a learned 16×d projection of the student's hidden state at the last prompt token of a memory-free first pass; top-1 at inference. It is trained with route labels (cross-entropy over the three scores at temperature 0.2), with ordinary-text prefixes from WikiText-2 *train* as "none" examples, and retrained at each stage on stored prompts of all tasks so far. An answer-loss-only router is not run: P9-I's registered collapse of answer-trained queries is the reason. Routing between prompts that carry different marker words is easy, and a pass says little about fine-grained addressing; word-level addresses stay symbolic in this lane too.
  - No learned slot-level addressing is run in S2. If S0 qualifies an interface, evaluating it here needs a separately approved supplement.

## 6. Stages (design problem 5)

Every stage runs exactly U = 2,000 updates [lead's choice] of batch 32 with AdamW (no weight decay, clip 1.0, constant learning rate fixed by calibration) and a fresh optimizer state. Order A→B is described; order B→A is the same with the letters exchanged and is run in full.

### 6.1 Stage 0 — baseline

The untrained student and both teachers are scored on every panel. No training.

### 6.2 Stage A

Memory A (N slots) is trained on T_A. Result: version V1. This is also the single-teacher A student.

### 6.3 Stage B, from V1

| Arm | New capacity | Memory A | Replay of A | What it tests |
|---|---|---|---|---|
| **M-i** (mechanism i) | Memory B, N new slots | frozen bit-for-bit | none | B is learned beside an untouched A |
| **M-ii** (mechanism ii) | starts from M-i's result; one store of 2N slots | trainable | 32 replayed A rows added to each batch of 32 B rows | consolidation with a retention constraint |
| M-grow (control) | N new slots in the same store | trainable | none | growth without freezing |
| M-seq (control) | none | trainable | none | does sparsity alone protect A (H22-D) |
| M-seq-R (control) | none | trainable | as M-ii | replay without growth |

- **Retention constraint of M-ii.** Soft: the replayed rows. Hard: the refined version V2-ii is published only if, on D_con, chrF on the first capability is at least V2-i's minus 0.02 and chrF on the second is at least V2-i's minus 0.02 [lead's choice]. Otherwise the cell is CONSOLIDATION-REJECTED, the pinned version stays V2-i, and the cell cannot count as an empirical retention pass.
- Replay uses stored verified outputs of the first teacher; the teacher is not run again. Replay arms see more examples; updates and examples are reported, and replay arms are compared with each other and with the bound.
- M-ii, M-grow, M-seq and M-seq-R read one store with a single top-8.

### 6.4 Evaluation schedule

Before and after every stage, every trained snapshot is scored on E_A, E_B, the combined panels and the general panel (§10). "Before" a stage is the parent snapshot's score.

- **Combined tasks** (both capabilities in one item; never trained on by any arm):
  - C1, two sources: `English: {s1}\nGerman:` … then, after the model's own first answer, `\nEnglish: {s2}\nFrench:` …; the item needs a route change inside one context.
  - C2, one source: `English: {s}\nGerman:` … `\nFrench:` …; the source words are read with both tasks' codes and the two reads are summed.
  - The score is the mean chrF of the two answers; an item passes if both answers match a reference exactly.
- **General-language quality.** Mean next-token negative log-likelihood of the student on 200 windows of 256 tokens [lead's choice] from WikiText-2 validation, with the mean KL divergence to the Stage 0 student and the share of positions whose top-1 token is unchanged. This data is used for nothing else in S2. Conditions: (G-route) the arm's registered operating condition — route ∅ in the oracle lane, the learned router's choice from a 64-token prefix in the router lane; (G-stress) reads forced at every in-vocabulary word with task A's codes, a diagnostic that enters no rule.

## 7. Baselines (design problem 6)

All share partitions, U, batch size and the sequence-level loss. LoRA is a small implementation inside `studies/p10s2/` (no new package), on the query and value projections of every block; rank is set so the trainable parameter count is within 1% of the memory arm it is matched to.

| Baseline | Definition | Matched to | Can show | Cannot show |
|---|---|---|---|---|
| Single-teacher students | Stage A of each order (memory); L-A and L-B (LoRA) | — | what one teacher gives alone | — |
| **M-joint** — ordinary multi-teacher distillation | one store of 2N slots trained from initialization on T_A ∪ T_B mixed, 2U updates | M-i's total slots and examples | the bound sequential arms are measured against | anything about order |
| **L-seq** | one LoRA adapter trained on A then B, no replay | one memory's parameters | forgetting of a dense adapter (the comparator of H22-D) | — |
| **L-seq-R** | as L-seq with replay as in M-ii | same | what replay buys a dense adapter | — |
| **L-sep** | adapter A frozen, adapter B new, selected by the same oracle route | M-i | **the fair existing alternative to mechanism (i)**; if it matches M-i, the memory has shown no advantage | — |
| L-joint | one adapter of twice the size on T_A ∪ T_B, 2U updates | M-joint | dense bound | — |
| **Ensemble** | the two teachers behind the oracle route, and behind the learned router | — | the quality ceiling and its cost | it is not a student |
| **R-exact** | table from training sentence to verified output; exact match | — | zero hits on held-out items by construction: confirms the panels are held out | — |
| **R-nn** | nearest training sentence by character-trigram TF-IDF cosine; return its stored output | — | how far sentence retrieval goes without composition | — |
| **R-icl** | the 4 nearest verified pairs placed in the frozen student's prompt | — | retrieval that can generalize; the strong retrieval competitor | its longer prompt is a cost, reported |
| **R-gloss** | co-occurrence lexicon (Dice) from the verified pairs; word-by-word output in source order | — | the non-learned equivalent of a word-addressed memory | — |
| MA-gold (control) | Stage A trained on gold references of the same sentences instead of the teacher's accepted outputs; order A→B only | Stage A | what the teacher adds beyond gold | — |
| Ablations | memory off; values permuted across slots; unit codes permuted across words | every memory cell | that the gain passes through the stored values and the addresses | — |

A transfer claim needs generalization: every gate of §11 is computed on held-out panels, and the retrieval and lexicon baselines are printed beside it.

## 8. What "more parameters" is controlled by

"Do not claim successful knowledge fusion merely because the combined memory contains more parameters." M-i has 2N slots after Stage B. It is read against M-joint (same 2N, simultaneous), M-seq (N, no growth), M-grow (2N, no freezing) and L-sep (same parameters, dense). The value-permutation ablation shows whether the parameters are used. The word "fusion" is not used for any outcome; C2 is the only test in which the two memories act on the same positions, and it produces an annotation, not a label.

## 9. Replicates, seeds, pairing

- **Three replicates** [lead's choice], r = 1, 2, 3. A replicate is a new training draw (T_A^r, T_B^r) and a new initialization. Evaluation panels, Q, D_cal, D_con and the vocabulary are common to all replicates and are fixed by the partition seed.
- Seeds: replicate base 220001, 220101, 220201 (base + 0 initialization, + 1 training draw, + 2 batch order, + 3 router, + 4 permutation controls); partition seed 220901; calibration 221001–221999; rehearsal 222001–222999; tests 229001–229999. The implementation asserts the ranges are disjoint from each other and from every seed of P1–P9-II, and writes the hash of every panel and stream to a data manifest at the freeze.
- Within a replicate every arm sees the same data, the same batch order where the data are the same, and the same initialization of shared parameters. Both orders are run in every replicate.
- With three replicates nothing statistical is claimed beyond "replicated in 3 of 3". No confidence interval across replicates is printed; a bootstrap interval over items is printed per cell.

## 10. Measurements

### 10.1 Quality

- **chrF**: character n-gram F-score, n = 1…6, β = 2, on the normalized strings, implemented in the study and unit-tested against hand-computed cases; the item score is the maximum over references; the panel score is the mean.
- Exact-match rate (the verification rule) is reported beside it.
- **Gap closed** for capability c: G_c = (s_c(arm) − s_c(S0)) / (s_c(teacher c) − s_c(S0)), all on the same panel. It is defined only if the denominator is at least 0.30; otherwise the cell is NOT_EVALUATED.

### 10.2 Costs (design problem 8)

- Teacher inference: input and output tokens, wall and CPU seconds, peak memory, per teacher.
- Student training: wall seconds per cell with the device named, updates, examples, peak memory.
- Footprint: stored parameters and bytes of the student, each memory version, each adapter, each teacher, each retrieval index.
- Active inference work per item, as counts: memory reads, key products per read (N or 2N — a flat scan, logical work), value rows read, distinct slots touched; adapter parameters applied per token; teacher parameters per token for the ensemble; comparisons and prompt tokens for retrieval.
- **Timing benchmark, separate from training:** after all training, one process, CPU, six threads, 200 items per panel, three repetitions, median reported. Descriptive only. No latency, throughput, storage or efficiency claim is made from any of these numbers.

## 11. Gates, classes and labels (design problem 7)

All thresholds below are [lead's choice] and are fixed at the freeze.

### 11.1 Cell-level gates (per replicate and order; "first" and "second" are the capabilities in training order)

| Gate | Rule |
|---|---|
| ACQ1 | after Stage A, G_first ≥ 0.50; and G_first ≤ 0.10 with values permuted and ≤ 0.10 with unit codes permuted |
| ACQ2 | after Stage B, G_second ≥ 0.50 and G_second ≥ 0.80 × the single-teacher student's G on that capability in the same replicate; permutation controls as ACQ1 |
| RET | s_first after Stage B ≥ s_first after Stage A − 0.03, and G_first after ≥ 0.90 × G_first before |
| GEN | negative log-likelihood on the general panel under G-route rises by ≤ 0.02 nats per token over Stage 0 |
| Negative zones | acquisition: G < 0.25; retention: G_first after < 0.70 × before; general: rise > 0.10 nats |

Memory off equals the Stage 0 student exactly; gate G5 checks it and it is not counted as evidence.

### 11.2 Mechanism class (for M-i, M-ii, M-grow, M-seq, M-seq-R, L-seq, L-seq-R, L-sep; per order; first match wins)

| Order | Class | Rule over the three replicates |
|---|---|---|
| 1 | NOT_EVALUATED | ACQ1 fails in any replicate (nothing to retain), or a gap is undefined |
| 2 | NOT REPLICATED | replicates fall on different sides of a positive or negative threshold |
| 3 | NO-NEW-CAPABILITY | G_second in the negative zone in all replicates |
| 4 | FORGETS | retention in the negative zone in all replicates |
| 5 | DEGRADES-GENERAL | GEN in the negative zone in all replicates |
| 6 | ACQUIRES-AND-RETAINS | ACQ2, RET and GEN pass in all replicates |
| 7 | INTERMEDIATE | otherwise |

M-i's RET and GEN in the oracle lane are satisfied by construction and are printed as **BY CONSTRUCTION**, with gate G5's bit-identity result. M-ii with any CONSOLIDATION-REJECTED cell cannot be class 6.

### 11.3 Study label (first match wins)

| Order | Label | Rule |
|---|---|---|
| 1 | **ENGINEERING-FAILURE** | a defect found by gates G1, G4, G5, G6 or G7; a hash mismatch of a download; a difference between frozen and running code, configuration or data |
| 2 | **INCOMPLETE** | a registered cell has no record, or a cap stopped a stage; no class is derived for a mechanism with a missing cell and no denominator is reduced |
| 3 | **TRANSFER-INCONCLUSIVE: TEACHERS-NOT-QUALIFIED** or **DATA-INSUFFICIENT** | §4.3 or §5.2; the study stops before training |
| 4 | **TRANSFER-INCONCLUSIVE: CONTROL-FAILED** | a permutation control passes an acquisition threshold in any cell, or the ensemble's oracle-routed score differs from the teacher's own |
| 5 | **TRANSFER-NEGATIVE: NO-ACQUISITION** | Stage A's G_first is in the negative zone in all replicates of both orders |
| 6 | **TRANSFER-POSITIVE (i + ii)** | M-i and M-ii are both ACQUIRES-AND-RETAINS in both orders |
| 7 | **TRANSFER-POSITIVE (i only; retention by construction)** | M-i is ACQUIRES-AND-RETAINS in both orders; M-ii is not |
| 8 | **TRANSFER-NEGATIVE: NO-ADDITIONAL-ACQUISITION** | M-i is NO-NEW-CAPABILITY in both orders |
| 9 | **TRANSFER-INCONCLUSIVE: ORDER-DEPENDENT** | M-i is ACQUIRES-AND-RETAINS in exactly one order |
| 10 | **TRANSFER-INCONCLUSIVE** | anything else; the classes are printed |

- TRANSFER-POSITIVE means, numerically: in both orders and all three replicates, at least half of the teacher–student gap closed on held-out sentences for each capability in turn, the second at 0.80 or more of a single-teacher student, the first within 0.03 chrF after the second, the gain removed by both permutation controls, and the general panel within 0.02 nats.
- Every label is printed with the fixed line **"oracle-assisted: word-level addresses and routes are supplied by rule; not autonomous learned memory"**. The label never changes because of the learned-router lane.
- A forgetting outcome of M-ii, M-seq or M-grow is a mechanism class and does not make the study negative while M-i holds; it is reported with equal prominence.

### 11.4 Mandatory annotations (printed with the label; they do not change it)

| Annotation | Rule |
|---|---|
| NO ADVANTAGE OVER SEPARATE ADAPTERS | L-sep is ACQUIRES-AND-RETAINS and its scores on both capabilities are within 0.03 of M-i's or above, in at least one order |
| RETRIEVAL SUFFICES | R-icl's or R-nn's score is within 0.03 of M-i's or above on both capabilities |
| LEXICON-EQUIVALENT | R-gloss's score is within 0.03 of M-i's or above on both capabilities |
| SPARSE-RETENTION / NO SPARSE-RETENTION | M-seq's loss of G_first is smaller than L-seq's by at least 0.10 in all replicates of both orders / otherwise (H22-D) |
| ROUTER-QUALIFIED / ROUTER-NOT-QUALIFIED | learned-router lane: route accuracy ≥ 0.99 on E_A, E_B and the general prefixes, and M-i passes ACQ2, RET and GEN with the learned routes, all replicates |
| COMPOSES C1 / C2 | mean over replicates of the combined score ≥ 0.80 × the mean of the two single-task scores of the same arm |
| EXACT-MATCH WEAK | gap closed on exact-match rate < 0.10 for either capability |
| TEACHER ADDS NOTHING OVER GOLD | MA-gold's G is within 0.03 of Stage A's or above |
| BELOW JOINT BOUND | M-i's G on either capability < 0.90 × M-joint's |
| Cost lines (§11.5) | always printed |

### 11.5 Cost and active-memory comparisons (registered rules, descriptive standing)

Against L-sep, R-icl and the ensemble, for M-i after Stage B, medians over replicates:

- **TRAINING COST COMPARABLE** if student-training wall seconds per stage ≤ 1.5 × L-sep's on the same device and U; otherwise **TRAINING COST HIGHER**, with the ratio.
- **FEWER VALUE ROWS ACTIVE** if (value rows read per item × d) ≤ 0.10 × the adapter parameters applied per item; printed always with the key products per read, which are not reduced by sparsity in a flat scan.
- **STORED SMALLER THAN ENSEMBLE** if student plus memories is ≤ 0.75 × the two teachers' parameters; printed with M-i's G on each capability, which says how far below the ensemble's quality it is.
- Teacher inference cost is printed as tokens and seconds per accepted training item.

None of these is an efficiency result. Logical counts are never reported as measured efficiency.

## 12. Calibration, pilot and gates

### 12.1 Calibration (before the freeze; calibration seeds, D_cal only)

- Memory: L ∈ {4, 12} × learning rate ∈ {0.001, 0.003}. LoRA: learning rate ∈ {0.0001, 0.0003, 0.001, 0.003}. Four settings each; Stage A, capability A, one seed, U updates. Rule: the highest chrF on D_cal; a difference below 0.01 goes to the first value listed. Eight cells. Calibration scores are never reported as results.
- Nothing else may be tuned. The evaluation panels are not read before the registered run.

### 12.2 Pilot gate (before the freeze; registered rule)

With the calibrated setting, on D_cal: if Stage A's gap closed is below 0.25, the registered run does not start. The outcome is recorded as **NOT STARTED: STUDENT CANNOT USE THE MEMORY ON THIS TASK**, with the calibration records, and the lead returns to the human lead with a revised design. This is a stop before the freeze, not a study label.

### 12.3 Gates of the run

- **G1** partitions: every pair of panels and streams is disjoint by sentence hash; vocabulary closure holds; hashes match the manifest.
- **G2** baseline sanity: the Stage 0 student and each teacher are scored twice with identical results, and every gap of §10.1 is defined (≥ 0.30) on E_A and E_B; an undefined gap gives NOT_EVALUATED cells, not a stop.
- **G3** teacher qualification (§4.3), on registered data, before any student training.
- **G4** determinism of evaluation on CPU (two scorings bit-identical); snapshot save and restore bit-identical; gradient reach (in M-i nothing of Memory A or the student receives a gradient; in every memory arm no student parameter does); a 20-update run on CPU repeated bit-identically; the same 20 updates on MPS agree with CPU in loss within 1e-3.
- **G5** with route ∅, logits equal the frozen student's bit for bit on the general panel; a new memory with gate 0 changes nothing.
- **G6** the address function and the router take the prompt only; permuting references changes no address and no route.
- **G7** downloads: revision and SHA-256 of every file equal the pinned values; licenses re-read and recorded.
- The gates stage runs at real size on rehearsal seeds before the freeze and again on registered seeds before training. A failed gate stops the run.

## 13. Matrix and projected resources (design problem 9)

### 13.1 Matrix per replicate

| Group | Cells | Stage-units of U |
|---|---|---|
| Memory, order A→B: Stage A, M-i, M-ii, M-grow, M-seq, M-seq-R | 6 | 6 |
| Memory, order B→A | 6 | 6 |
| M-joint; MA-gold | 2 | 3 |
| LoRA, each order: single, L-seq, L-seq-R | 6 | 6 |
| L-joint | 1 | 2 |
| **Trained cells** | **21** | 15 memory + 8 LoRA |

Three replicates: **63 trained cells**. Evaluation-only: Stage 0, two teachers, the ensemble (two routings), four retrieval baselines, three ablations on each of 14 memory cells per replicate, the learned-router lane on M-i and L-sep, the timing benchmark. Calibration adds 8 cells; the router's training is a linear map on cached states.

### 13.2 Projection — not a measurement

No number below has been measured on this machine. They come from operation counts and are uncertain by a factor of about three either way; the rehearsal replaces them.

| Work | Device | Assumption | Projected |
|---|---|---|---|
| Teacher generation, about 2 × 60,000 short sentences, beam 4 | CPU | 30–60 sentences per second | 0.6–1.2 h |
| Memory stage of U updates (1,536 tokens per update) | MPS, FP32 | 0.15–0.30 s per update | 5–10 min |
| LoRA stage of U updates | MPS, FP32 | 0.25–0.45 s per update | 8–15 min |
| All training, 3 replicates (45 memory units + 24 LoRA units) | MPS, serial | above | 7–13.5 h |
| One full evaluation of a snapshot (about 220,000 token-forwards) | CPU, 6 threads | 4–13 min | — |
| All evaluation (63 full, about 130 partial) | CPU, 3 workers | above | 4–10 h wall |
| Calibration, pilot, rehearsal | both | — | 3–5 h |

- **Runtime.** Training on torch MPS in FP32; teacher generation and all registered evaluation on CPU with deterministic algorithms. The locked environment has torch 2.8.0 with MPS available and none of `transformers`, `tokenizers`, `safetensors`, `sentencepiece`, `numpy` (§14). Training on MPS is not bit-reproducible; what is independently recomputed is every score, from saved snapshots, on CPU. If the rehearsal finds an unsupported MPS operation or a silent CPU fallback, training moves to CPU (projected 4–6 times slower) and the cut rule applies.
- **Caps** [lead's choice]: 8 GiB per worker; 24 GiB aggregate; total download 1.5 GB (primary pair 0.93 GB; with the fallback 1.26 GB); new disk use 6 GB; **36 charged hours for S2 alone**, charged as wall-clock hours of S2 processes, calibration, pilot and rehearsal included.
- **Rehearsal** at full size on rehearsal seeds: every cell type for 200 updates, one memory cell and one LoRA cell for the full U, one full evaluation of each kind, the gates stage, and analysis and report on synthetic records of the whole registry including missing cells, rejected consolidations and non-finite values. It must show at least 2× headroom on time and memory for the registered run.
- **Cut rule, fixed now, applied before the freeze and recorded:** if 2× headroom is not shown, drop in this order until it is: (1) MA-gold; (2) M-seq-R and L-seq-R together — **this removes a required baseline (LoRA with replay) and needs the human lead's acceptance**; (3) evaluation panels to 500; (4) the third replicate, in which case every "all replicates" rule reads 2 of 2 and the report says so. If headroom is still missing, the run is not started.

## 14. Downloads and packages (exact list for the delegation)

Models (only the files named; no other file of a repository is fetched):

| Repository | Revision | License (verified from) | Parameters | Files and size |
|---|---|---|---|---|
| `HuggingFaceTB/SmolLM2-135M` | `93efa2f097d58c2a74874c7e644dbc9b0cee75a2` | Apache-2.0 (Hub API) | 134,515,008 | `model.safetensors` 269,060,552 B; `config.json`, `generation_config.json`, `tokenizer.json`, `tokenizer_config.json`, `vocab.json`, `merges.txt`, `special_tokens_map.json` ≈ 3.4 MB |
| `Helsinki-NLP/opus-mt-en-de` | `6183067f769a302e3861815543b9f312c71b0ca4` | CC-BY-4.0 (Hub API, model card) | ≈ 74 M, count at load | `pytorch_model.bin` 297,928,209 B; `config.json`, `generation_config.json`, `source.spm`, `target.spm`, `vocab.json`, `tokenizer_config.json` ≈ 2.8 MB |
| `Helsinki-NLP/opus-mt-en-fr` | `dd7f6540a7a48a7f4db59e5c0b9c42c8eea67f18` | Apache-2.0 (Hub API) | ≈ 74 M, count at load | `pytorch_model.bin` 300,827,685 B; same small files ≈ 2.9 MB |
| fallback only: `Helsinki-NLP/opus-mt-en-es` | `5bc4493d463cf000c1f0b50f8d56886a392ed4ab` | Apache-2.0 (Hub API) | ≈ 77 M, count at load | `pytorch_model.bin` 312,087,523 B; small files ≈ 3.2 MB |

The requirement speaks of "the two small teachers". The student is a third model; the lead's reading of the delegation should be stated to cover it, or the human lead asked (open question 4).

Datasets: §5.1.

Packages, per command, with `uv.lock` and `pyproject.toml` untouched (`uv run --locked --with …`; `pyarrow` is not needed, the data files are TSV):

| Package | Version | Checked on PyPI 2026-11-14 |
|---|---|---|
| transformers | 4.57.1 | exists, not yanked, needs Python ≥ 3.9, `huggingface-hub ≥ 0.34, < 1.0`, `tokenizers ≥ 0.22.0, ≤ 0.23.0`, `safetensors ≥ 0.4.3`; torch ≥ 2.2 in its extra. **PyPI lists security advisories against this release; the current release is 5.23.0. The lead must read the advisories and choose** |
| tokenizers | 0.22.1 | exists, arm64 abi3 wheel |
| safetensors | 0.6.2 | exists, arm64 abi3 wheel |
| huggingface-hub | 0.35.3 | exists; brings `hf-xet` on arm64 |
| sentencepiece | 0.2.1 | exists, cp312 arm64 wheel |
| numpy | 2.3.3 | exists, cp312 arm64 wheel |
| sacremoses | 0.1.1 | exists (MIT by classifier); used by the Marian tokenizer for punctuation normalization |

Transitive dependencies (`filelock`, `fsspec`, `packaging`, `pyyaml`, `regex`, `requests`, `tqdm`, `typing-extensions`, `hf-xet`, `click`, `joblib` and theirs) are not pinned by the table. Before any use, one resolution is written to `studies/p10s2/requirements-p10s2.txt` with exact versions and hashes; every command uses that file, and it is part of the freeze. That the seven versions resolve together with torch 2.8.0 on Python 3.12 has not been tested.

Downloads run once, without an account token, with telemetry disabled, into a git-ignored directory named by repository and revision; every later command runs offline.

## 15. Departures from project practice that need explicit acceptance

1. A pretrained student and `transformers`, against the handoff's "first tests use a train-from-scratch small model" (Phase 5 foresees a pretrained model later).
2. Training on MPS without bit reproducibility; reproducibility is of scores from snapshots.
3. A 36-hour cap, nine times P9-II's.
4. Pickle weight files for the teachers, loaded once in weights-only mode.
5. A CC-BY-4.0 teacher: attribution is owed in any publication; no weights trained on its outputs are released by this study.

## 16. Order of work, stop rules, reserved decisions

**Order.** (1) Opus review of this revision; revise until clean. (2) Lead's approval under the delegation, with the items of §15 and the open questions either settled or taken to the human lead. (3) Implementation with tests, on synthetic stand-ins, before any download. (4) Downloads and G7. (5) Partitions, teacher generation on calibration and rehearsal material, calibration, pilot gate. (6) Rehearsal; implementation audit; cut rule. (7) Freeze of code, configuration, requirements file, seeds, thresholds, calibration record, data manifest. (8) The registered run, once: gates, G3, Stage 0, Stage A, Stage B, baselines, evaluation, timing benchmark. (9) Independent recomputation of every score from snapshots by the auditor; outcome report.

**Stop rules.** A failed gate or any difference from the freeze stops the run. A stage that would exceed a cap is not started. Nothing is re-run with changed settings. A second attempt after an engineering stop needs the human lead's decision. Failed runs and failed checker attempts are kept.

**Reserved for the human lead.** Any change of thresholds, arms, models, data or budget after the freeze; a second attempt; any model above 2 billion parameters, any cloud spend, any further download; use of the locally present Ollama weights (not used here); learned slot-level addressing inside S2; the use of S2's outcome in any P10 system claim; merge; publication; weight release; ADR-0012.

## 17. What S2 cannot establish

- **Autonomous learned memory.** Word-level addresses and, in the primary lane, routes are supplied by rule. A positive result is oracle-assisted and may not be cited as learned-memory success. The learned-router lane concerns a three-way choice between prompts that carry different marker words.
- **Knowledge fusion.** Two memories side by side with a switch are two memories. More parameters holding more is not fusion. Only C2 touches joint use, and it yields an annotation.
- **Retention as a discovery under mechanism (i).** It is a property of freezing.
- **Skill transfer.** The capability is lexical translation of short sentences from a closed vocabulary of 2,000 words. Nothing follows for procedural skills, open vocabulary, long text or other languages.
- **The value of the teachers.** Accepted outputs are gold references; if MA-gold matches, the teachers added nothing but the selection of items.
- **Large models.** Teachers of about 74 million parameters and a 135-million student say nothing about 25B or 100B teachers.
- **Superiority.** Separate adapters, a lexicon or retrieval may match or beat the memory. The study reports that.
- **Storage, latency, efficiency, capacity scaling, locality.** No such claim; counts are logical work.
- **A success probability.** Three replicates on one partition of one corpus.
- **A failure of the ArborLM concept,** whatever the outcome.

## 18. Approval record

To be filled before any implementation: the Opus review reference; the lead's approval under the delegation, quoting the human lead's delegation verbatim; and the human lead's words on the items of §15 that the delegation does not cover.

## Open questions for the lead

1. Is a lexical pair (two translation directions) acceptable as "complementary capabilities", given that a heterogeneous pair cannot be run under controlled addressing (§0, §4.1)?
2. Should mechanism (i) alone earn TRANSFER-POSITIVE (row 7), when its retention is by construction, or should the label require M-ii (row 6 only)?
3. Exact match to a gold reference as the verification rule makes the teacher a selector of gold. Keep it, or accept chrF ≥ a threshold and admit unverified near-misses?
4. Does the delegation's wording ("the two small teachers") cover the student download and the 51 MB of dataset files, or does that go to the human lead?
5. MPS training with CPU-recomputed scores, or CPU throughout at four to six times the hours?
6. transformers 4.57.1 (known to this draft, advisories listed) or a 5.x release (current, untested here)?
7. Three replicates and 63 cells within 36 hours, or a smaller matrix (for example without M-grow and M-seq-R) from the start?
8. Values at full student width (2.4 M parameters per memory) or narrow values with an output projection (0.4 M), which is closer to P5's form?

## Things the lead must verify before approval

- SmolLM2-135M's architecture (blocks, width, heads, vocabulary, context) from its `config.json`; this draft states them from memory.
- The teachers' parameter counts (inferred from file size) and that the LFS oids quoted are SHA-256 digests.
- All four revision hashes again at download; the dataset repository showed a modification on 2026-11-14.
- The Tatoeba licence wording (CC-BY 2.0 France) and its attribution duty; the CC-BY-4.0 duty for the German teacher; that no licence restricts training a model on a teacher's outputs for local research.
- Row counts of the four data files, the size of the two-reference intersection, and whether the pools meet §5.2 — unknown until the files are read.
- That the seven package versions resolve together with torch 2.8.0 on Python 3.12, and the content of the advisories against transformers 4.57.1.
- That Marian loading in the chosen `transformers` version accepts weights-only loading with torch 2.8.0.
- Every throughput figure of §13.2; none is measured.
- That the German teacher was trained on OPUS data that includes Tatoeba: its score on these panels overstates its general quality. This does not bias the student's gap closure, but the report must say it.
- That seed range 220001–229999 is unused in every earlier study's code and records (asserted here from the inventory, not searched).
