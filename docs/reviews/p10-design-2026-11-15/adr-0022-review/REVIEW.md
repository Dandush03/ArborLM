# Specification review of ADR-0022 (P10-S2, two-teacher sequential transfer), design revision 1

- **Reviewer:** Claude Opus 5.5 (model id `claude-opus-5-5`), acting as specification auditor for this study only. I did not write any part of ADR-0022.
- **Date:** 2026-11-15 (UTC).
- **Object:** `S/ADR-0022-p10-s2-two-teacher-transfer.md` (446 lines, mtime 2026-11-14 23:50). `S` = `/private/tmp/claude-501/-Users-daniellaloush-dandush03-ArborLM--claude-worktrees-arborlm-consolidation-experiment-2b31c1/cfc0efd5-b7ca-4602-959a-07fe6b8d4e7d/scratchpad`.
- **Read for context:** `AGENTS.md`, `CLAUDE.md`, ADR-0017 §5.1–5.6, §8.5 and §18 (I.1–I.4), `studies/p9/model.py` (gate and read formula), `studies/p9/core.py` (seed namespace), `S/EVIDENCE_INVENTORY_P9II_P10.md` (B0, B6, B9, NEEDS REVIEW), and `S/ADR-0019-robust-sparse-address-learning.rev4.md` as a format reference.
- **Status of this document:** independent engineering and mathematical review evidence. **It is not Astra validation and not human approval.** **Astra review: NOT_PERFORMED.**
- **What I ran:** read-only Hugging Face Hub API and PyPI/OSV metadata queries (JSON listings, `config.json`, `README.md`, `tokenizer_config.json`, `generation_config.json`; HEAD requests for two weight files and one dataset file); two idealized synthetic probes on random vectors (no real data, no training); parameter-count arithmetic. Commands are in §K.
- **What I did not do:** download any weight or data file, install any package, run any training or registered benchmark, resolve the package set, or test Marian loading. No git operation and no edit of a tracked file.

## Verdict: **NOT READY** for the lead's self-approval

Three blockers. Two concern what the label would mean: the primary arm cannot fail for any reason connected to doing things in sequence, and the teachers can be replaced by the gold data. The third is that the data cannot be downloaded the way the draft plans. Ten majors. Most can be fixed by text changes, and the design I recommend in §I is smaller than the draft. The frank assessment in §0 of the draft is honest and mostly right. But several weaknesses it names as "stated limitations" in fact decide the label, so stating them is not enough.

---

## Findings at a glance

| # | Class | Finding (one line) | Fix (one line) |
|---|---|---|---|
| B1 | BLOCKER | In the primary oracle lane, M-i is two independent memories behind a keyword switch. Its Stage B is the same computation as the other order's Stage A, so ACQ2 (ratio ≈ 1), RET, GEN and the order control are true or identical by construction. TRANSFER-POSITIVE (i only) means only that each language was learned once, separately. | Delete label row 7. Replace primary M-i with **M-append-frozen**: one store, B's slots appended, A's rows frozen, one top-8 over all slots, no switch between memories. Retention is then empirical (probe: 22–27% of every A read's weight moves to B slots). Keep separate-store M-i only as a free BY-CONSTRUCTION reference. |
| B2 | BLOCKER | The teachers do not matter. Verification by exact match makes T_A a subset of the gold. MA-gold, as defined (gold for the *same* sentences), differs from Stage A only in case, punctuation and which reference was chosen, so it cannot measure what the teacher adds. TEACHER ADDS NOTHING is an annotation that does not move the label. A positive would mean "two parallel corpora learned", not "knowledge from two teachers". | Train only on **teacher outputs for English sources that have no gold reference in that target language**, so the language can only come from the teacher. Verify with an acceptance filter whose precision is measured on gold-bearing Q, fixed before the run (PENDING LEAD REVIEW: does this count as "suitable verification"?). The gold control uses gold-bearing sentences. TRANSFER-POSITIVE requires the teacher-only arm. |
| B3 | BLOCKER | `Helsinki-NLP/tatoeba_mt` is **gated (`gated: "auto"`)**. Unauthenticated `resolve` returns **HTTP 401**, and its LFS SHA-256 values are masked in the public tree. The draft's "without an account token" plan cannot run, and G7 cannot compare data files against pinned hashes. The student model and the dataset are also downloads beyond the human's "two small teachers". | Take to the human lead: approve the student download and the data download, and choose a source (a personal Hub account accepting the gate, or an ungated Tatoeba or Tatoeba-Challenge release). Data hashes become "recorded at first download", not "pinned". |
| M1 | MAJOR | M-ii can pass by inertia. Its own acceptance filter (≤ 0.02 drop on D_con from V2-i) nearly guarantees RET on E_A. Consolidation has no goal except "do no harm". | Add a modification floor: A's value rows must change by ≥ [0.10] relative norm, else RETENTION BY INERTIA (no class 6). State that RET is selected for, and give consolidation an objective or call it "continued training with replay". |
| M2 | MAJOR | With oracle codes and N ≥ W, the read is a fixed linear map of the values. The memory is functionally a per-(task, word) vector table. The baseline that would embarrass it (a plain word-vector table or the R2 dedicated slot) is missing. | Add **E-table**: one trainable 576-vector per (task, word) and one per task marker, added at the same layer and positions. Add the annotation EQUIVALENT TO A WORD TABLE. |
| M3 | MAJOR | Controls are underspecified. The task-marker read is a learned soft prompt that can carry a "write German" signal without any lexicon, and the draft does not say whether code permutation permutes the marker code. "Passes an acquisition threshold" (row 4) is ambiguous between 0.10 and 0.50. | Add **marker-only** and **words-only** ablations, permute word codes only, give CONTROL-FAILED an exact threshold, and make marker-only ≥ [0.25] block ACQ1. |
| M4 | MAJOR | Held-out means held-out English only. Target-side duplicates and English near-duplicates (contractions, name swaps) let evaluation references appear verbatim as training targets. | Partition by connected components over shared normalized English *or* any shared normalized reference, plus contraction expansion. Report and exclude overlap, and add G1 checks. |
| M5 | MAJOR | GEN is vacuous in every oracle-routed arm, and the draft does not say whether LoRA arms are switched off on route ∅. If they are not, the GEN comparison is unfair. If they are, GEN is vacuous for them too. | All arms gated by the same route. GEN printed BY CONSTRUCTION wherever route ∅ is exact. GEN enters the label only through the learned-router condition (or the always-on diagnostic). |
| M6 | MAJOR | H22-D (does sparsity help retention?) is confounded. M-seq reads with task-specific oracle codes, while L-seq gets no task conditioning. Any advantage may come from the oracle address, not from sparsity. | Add M-seq-shared (task-agnostic codes u(w)), or reword SPARSE-RETENTION as "task-coded oracle addressing in a sparse store". |
| M7 | MAJOR | The pilot gate covers capability A only, uses the same D_cal as calibration, and does not decide whether French works. The drafter's main risk (an uninformative negative) remains half unguarded. | Run the pilot on both capabilities with a fixed rule and a declared optimism caveat. |
| M8 | MAJOR | The budget almost certainly breaks the draft's own 2× headroom rule. The charging of parallel evaluation workers is ambiguous. Two of the 21 trained cells per replicate (M-i, L-sep) duplicate other cells. The cut rule calls L-seq-R a required baseline, but the human's list does not require it. | Adopt the smaller design of §I (≈ [8–12] charged h, preregistered third replicate). Define charged hours as the sum over processes. Fix the cut-rule wording. |
| M9 | MAJOR | Governance of dependencies. `transformers` and six other packages would sit in the registered training path outside the lock, but CLAUDE.md allows `--with` for analysis-only tools. The proposed pins cannot be combined with any 5.x release. | Human acceptance needed, or isolate the teachers in a one-time generation step. The student is a plain Llama implemented in torch with a reference-equivalence test. Choose one consistent package set (§G). |
| M10 | MAJOR | The labels lack scope words. TRANSFER-POSITIVE would be printed without "lexical", "same kind", "closed vocabulary" or "gold-verified". "Complementary" narrowed to two translation directions needs the human lead's word, not the lead's. | Make the fixed label line in §I.5 mandatory, and take open question 1 to the human lead (PENDING LEAD REVIEW). |

Minor findings are in §L.

---

## A. Credible test, or one that cannot fail or cannot succeed?

### A.1 Trivial systems that pass each gate

| Gate / label | Trivial system that passes | Do the draft's controls catch it? |
|---|---|---|
| ACQ1 (G_first ≥ 0.50 on held-out; permutation controls ≤ 0.10) | (a) A per-(task, word) vector table at the same layer (E-table). (b) LoRA. (c) A word-by-word Dice lexicon (R-gloss) for short Tatoeba sentences with near-monotone order. (d) Possibly the **task-marker read alone** acting as a soft prompt, if chrF credits generic German character n-grams. | (a) **No**: not in the design (M2). (b), (c) only as annotations. (d) **Not cleanly**: the permutation control's handling of the marker code is unspecified (M3). |
| ACQ2 (G_second ≥ 0.50 and ≥ 0.80 × single-teacher) | M-i itself. In the oracle lane, Memory B on French prompts is trained and read exactly as the single-teacher B student. The ratio is ≈ 1 up to the initialization seed. | **No** (B1). |
| RET | Any frozen module behind a keyword switch: M-i, L-sep, or two lookup tables. | Printed BY CONSTRUCTION. Row 7 still awards TRANSFER-POSITIVE (B1). |
| RET under modification (M-ii) | An M-ii whose optimizer barely moves A. Its acceptance filter (≤ 0.02 drop on D_con) is itself a retention test on a sister panel. | **No** (M1). |
| GEN | Every oracle-routed arm and every route-gated adapter: bit-identical on WikiText under route ∅. | Printed BY CONSTRUCTION for M-i only. LoRA gating unspecified (M5). |
| Order control (H22-E) | M-i in both orders computes the same two memories. "Order" is a reseeding. | **No** (B1). |
| "From two teachers" | Gold Tatoeba pairs. Exact-match verification returns gold strings. | **No** (B2): MA-gold uses the same sentences and is near-tautological. |
| Cost and active-memory lines | "STORED SMALLER THAN ENSEMBLE" is decided by arithmetic: 139,364,674 / 148,613,487 = 0.938 > 0.75, so it always fails (`scripts/param_counts.out.txt`). | Descriptive only, but predetermined (minor). |

### A.2 What TRANSFER-POSITIVE would mean as drafted

Row 7, numerically, says: "a 2.4M-parameter oracle-addressed lexical store trained on gold-equal German pairs closes ≥ 50% of the gap, and so does a separate one trained on gold-equal French pairs." That is **two parallel corpora memorized as word vectors and used compositionally by a frozen English LM**. It is a real and possibly interesting result about lexical injection. It is not "sequential acquisition from two teachers while preserving earlier capabilities":

- *sequential* plays no role (B1);
- *teachers* play no role beyond filtering (B2);
- *preserving* is by construction (§0 item 2 of the draft says so).

Row 6 (i + ii) adds M-ii. Under M1, M-ii can pass by doing little. Because it starts from a single store of 2N slots built from M-i, its one real empirical content is whether the one-store merge hurts A.

### A.3 Making the teacher matter, with the smallest change

The cleanest change costs no new download:

1. **Teacher-only sources.** For capability A (German), training prompts are training-side, in-vocabulary English sentences that have **no German reference in any downloaded file**. Tatoeba's English sentences in `eng-fra` and not in `deu-eng` are the natural pool. For B, the reverse. The student's German can then only come from Teacher A. Gold German is used only for Q, D_cal, D_con, the audit and the evaluation panels.
2. **Verification without per-item gold.** Use an acceptance filter computed from the teacher alone: for example, length-normalized beam log-probability ≥ τ, target/source length ratio in [ρ1, ρ2], and output ≠ source after normalization. Fix τ, ρ1, ρ2 on **Q** before the run, so that the filter's measured precision on Q is ≥ [0.90] at "chrF ≥ [0.60] against gold". Report the measured precision with its interval. Precision is a property of the filter, measured on held gold; it is not item-level truth. Whether this satisfies the human's "suitable verification" is **PENDING LEAD REVIEW**, and probably a question for the human lead. The alternative, round-trip verification, needs two reverse models (de→en, fr→en), which are further downloads beyond the approval.
3. **Gold control redefined.** MA-gold trains Stage 1 on the same number of **gold** pairs drawn from gold-bearing training-side sentences. It is a reference point, not a ceiling. The annotation TEACHER-EQUIVALENT-TO-GOLD stays descriptive. The label requires that the teacher-only arm passes the gates.
4. **Contamination statement.** opus-mt-en-de and opus-mt-en-fr are the 2020-02-26 OPUS models (READMEs fetched). OPUS includes Tatoeba, so the teachers may have seen evaluation sentences. That inflates the gap denominator (conservative), but the report must state it.

Capabilities where the teacher's knowledge is not available as a dataset at all (facts the teacher knows, for example) have no gold to verify against. They would need a separate ground-truth source, so the cost is larger. The teacher-only-source design above is the smallest change that makes the teacher causally necessary.

---

## B. Is translation the right capability pair?

- **Acceptable for the smallest demonstration, with explicit scope.** Two directions are complementary in the weak sense: disjoint output languages, and each teacher's own-language margin is gated (§4.3). They are one *kind* of capability. Only the human lead can say whether that satisfies "demonstrably complementary" (M10, PENDING LEAD REVIEW).
- **The drafter's rejection of procedural tasks is partly overstated.** A hand-written address can supply recurring units for arithmetic too, for example (digit pair, carry). But such an address would encode the algorithm's decomposition, so the oracle would carry the skill. The same caveat applies, more mildly, to word-level addresses for translation: the address function *is* the lexical segmentation. State this in §0 item 1 instead of "no such unit".
- **Heterogeneous alternatives that are word-addressable and checkable**, such as translation plus POS or NER tagging from a token-classification teacher with a UD or CoNLL gold, would need a third model family, a different output format, and licence checks I did not perform. Not recommended for the smallest version.
- **Exact match.** As the *verification* rule it is too harsh as a filter (yield biased to easy items) and too lenient as evidence (it reduces the teacher to gold; B2). As an *evaluation* score it is too harsh for a frozen 135M student; keep it descriptive.
- **chrF.** Better as the primary score, but specify it exactly (minor L5): chrF2, character n = 1–6, word n-grams 0, whitespace removed, per-order precision and recall averaged before F (state which convention), 0–1 scale, sentence-level mean over items. Cross-check the study's implementation against `sacrebleu` on 1,000 pairs as an analysis-only check. Lowercasing and punctuation stripping make it "chrF-norm"; call it that.
- **Multiple references.** The maximum over references favours items with more references, and Tatoeba's reference counts vary. Report the reference-count distribution of every panel, and the scores for items with one reference only. Sample E panels stratified by reference count (1 vs ≥ 2), so that replicates and arms see the same mix.

## C. The student and the memory

- **SmolLM2-135M facts verified** (pinned revision `config.json`): `LlamaForCausalLM`, 30 layers, hidden 576, 9 heads, **3 KV heads (GQA)**, intermediate 1,536, vocabulary 49,152, `max_position_embeddings` 8,192, `rope_theta` 100,000, tied embeddings, BF16. Recomputed parameters: 134,515,008, equal to the Hub's safetensors total. The draft's "from memory" numbers are correct. Add the GQA fact: it sets the LoRA v-projection to 576×192.
- **Plausibility.** P9-I (§I.1) found that content written at earlier positions did not reach the answer site through the tiny frozen block. S2 again reads only at source positions and never at target positions. The answer must travel through 30−L frozen layers of attention. In a 30-layer LM that is plausible, but it is the decisive unknown, so the pilot must test it for both languages (M7).
- **Is it still the project's mechanism?** Partly. Kept: cosine keys, top-8, temperature 0.2, residual addition, key width 16, and oracle codes equal to rung R1. Changed: no output projection, no learned query (R1 by design), and a **linear scalar gate initialized at 0** instead of P9's `sigmoid(gate)` with initial value −2.0 (`studies/p9/model.py` line 277 and line 464). These are legitimate choices (the zero gate gives G5 bit-identity), but §3 must list them as departures. The value initialization must be non-zero: with g = 0 and V = 0, both gradients are zero and nothing ever learns.
- **"Well separated" is overstated.** Idealized probe (`scripts/shared_store_interference_2.out.txt`): with 2,001 random 16-dimensional codes and keys equal to the codes, only **0.589** of a read's weight lands on the word's own slots (0.503 with key noise 0.1). Training can compensate through the values (N ≥ W makes the linear system solvable), so this is not fatal. But "with addresses fixed and well separated, any failure is a failure of storing" is false; replace it.
- **Pilot gate.** It is fixed in advance and has a stop outcome, which is good. Defects: capability A only, and it is scored on the same D_cal used for calibration (optimistic) (M7).

## D. Controlled addressing and routing: what is left of "memory"?

- **Addresses.** Each read uses q = u(t, w) at the last subword of every in-vocabulary source word, plus q = u(t, ⟨task⟩) at the marker. The address is a function of the prompt only (G6). That is correct as stated.
- **What remains learned:** the values (a lexical vector per task and word, mixed through top-8), the keys (alignment to fixed codes), and the gate. With oracle routing between separate stores, what remains is **a learned word-vector table plus a keyword switch**. That is why E-table is the decisive comparison (M2).
- **Retention by construction makes RET vacuous for M-i.** The draft prints BY CONSTRUCTION but still lets row 7 award a positive (B1). The human's mechanism (i) reads "freeze Memory A while training Memory B, **with learned routing**". The draft's label never depends on the learned router, and in this task the router is a three-way keyword classifier that a pass says little about. The arm that makes mechanism (i) non-vacuous without leaving controlled addressing is **M-append-frozen**: one store, A's rows frozen, B's N rows appended, one top-8 over 2N, task-coded queries, no switch between memories. The idealized probe shows that appending B with A frozen moves **0.222–0.266 of every A read's weight** onto B's slots (89–97% of A queries touch a B slot), before any B value is trained toward anything (`scripts/shared_store_interference.out.txt`). Retention there is a genuine empirical question, and it is the expandable-memory question the human asked.
- **Labels.** (1) BY CONSTRUCTION results never satisfy a positive. (2) TRANSFER-POSITIVE requires empirical retention in M-append-frozen. (3) The consolidation variant requires M-ii with the modification floor. (4) The learned-router lane stays an annotation, worded as a keyword-level router.

## E. Baselines

- **Present and mostly fair:** single-teacher students, M-joint and L-joint (ordinary multi-teacher distillation), L-seq, L-seq-R, L-sep, the ensemble, R-exact, R-nn, R-icl and R-gloss cover the human's list.
- **Parameter matching is feasible.** LoRA on q and v of 30 blocks gives 57,600 parameters per rank. Rank 42 → 2,419,200 (−0.23% vs 2,424,833). Rank 84 → 4,838,400 vs M-joint (−0.23%). Both are within 1%.
- **Structural asymmetry, to be stated.** LoRA modifies every position, including the generation positions. The memory writes only at source positions. LoRA is the stronger hypothesis class, and that is acceptable for "the existing alternative".
- **Missing:** E-table (M2). M-seq-shared for H22-D (M6). Marker-only and words-only ablations (M3).
- **Redundant cells:** M-i (separate stores, oracle route) = the two Stage-A memories of the two orders. L-sep = the two single-teacher LoRAs. With matched seeds both are free; with independent seeds they are cells that measure nothing new.
- **The comparison that would embarrass the memory:** E-table ≥ memory (the memory machinery adds nothing over a table), and L-sep ≫ M-i. Only the second is in the draft.

## F. Data hygiene

1. Partition by English hash only (§5.2) leaves **target-side leakage**. "I'm tired." and "I am tired." are different normalized English strings with the same German reference. Name-swapped Tatoeba templates ("Tom …"/"Mary …") are near-duplicates (M4).
2. Teacher-side contamination: the OPUS 2020 teachers likely saw Tatoeba (A.3 item 4). The fallback en-es is a *Tatoeba-Challenge* model (opus-2020-08-18; README fetched) with a different training regime, so a fallback pair would mix regimes (minor).
3. T_A and T_B are disjoint in English (good). Under A.3, A and B sources are disjoint by gold availability.
4. General panel: WikiText-2 validation, already local and approved. SmolLM2's pretraining probably included Wikipedia-derived text, so only the *relative* NLL is meaningful (the draft uses it that way). Router negatives come from WikiText-2 train, a disjoint split.
5. Data hashes: Tatoeba's LFS oids are masked by the gate, so they cannot be pinned before download (B3). The small Hub files can be pinned now by git-blob SHA-1 from the tree API; LFS files by SHA-256 (the LFS oid is the SHA-256 of the content).

## G. Facts verified independently (2026-11-15 UTC, Hub/PyPI/OSV APIs)

| Claim in draft | Finding | Confidence |
|---|---|---|
| SmolLM2-135M revision `93efa2f0…a2` exists, last modified 2025-02-06, Apache-2.0 | Confirmed; equals `main` today; not gated | High |
| `model.safetensors` 269,060,552 B, LFS oid `80521b40…5da1` | Confirmed | High |
| Parameters 134,515,008 BF16 | Confirmed (Hub) and recomputed from config | High |
| Architecture 30 / 576 / 9 heads / 49,152 | Confirmed; also **3 KV heads**, intermediate 1,536, max positions 8,192, tied embeddings | High |
| opus-mt-en-de revision `6183067f…b4`, 2023-08-16, CC-BY-4.0 | Confirmed (API `cardData.license` and README); equals `main` | High |
| opus-mt-en-fr revision `dd7f6540…18`, 2024-02-14, Apache-2.0 | Confirmed; equals `main` | High |
| opus-mt-en-es revision `5bc4493d…ab`, Apache-2.0, 312,087,523 B | Confirmed; it is a Tatoeba-Challenge model (opus-2020-08-18) | High |
| `pytorch_model.bin` sizes and oids (de `da068344…206bdd`, fr `cc1de10b…0d64de`) | Confirmed | High |
| "pickle weights only (no safetensors on `main`)" | **Partly wrong.** No safetensors on `main`, correct. But `main` also has `flax_model.msgpack` and `tf_model.h5`, and en-de also `rust_model.ot`. Unmerged SFconvertbot PRs with `model.safetensors` exist (en-de PR 4, 5; en-fr PR 1, 2, 5, 9) | High |
| ≈ 74M parameters each | en-de 73,944,309 (+524,288 sinusoidal buffers = 74,468,597, matching file size / 4); en-fr 74,669,178; en-es 77,484,009 | High (arithmetic from config; not counted from weights) |
| en-de tokenizer config | `tokenizer_config.json` lacks `model_max_length`; open Hub PR 6 says the repo relies on attribute maps inside `transformers` that were being removed (transformers#29112). Behaviour may differ across `transformers` versions | Medium-high |
| Tatoeba files and sizes at `f337793b…f33` | Sizes confirmed (25,137,632; 21,044,993; 3,135,265; 2,097,757; total 51,415,647) | High |
| Tatoeba licence CC-BY 2.0 (France URL) | Confirmed in the dataset README | High |
| Tatoeba download without a token | **Wrong: dataset `gated: "auto"`; HEAD and ranged GET return 401; LFS oids masked; `lastModified` 2026-11-14T10:58:30Z.** I infer, without verifying, that the gate may be the modification the draft noticed | High (gating), Low (cause) |
| Total download, primary set | 928,370,951 B (student 272.4 MB incl. small files; de 300.8 MB; fr 303.7 MB; data 51.4 MB), i.e. 0.93 GB as drafted; fallback adds 315.3 MB + 18.5 MB | High |
| transformers 4.57.1 | Exists, not yanked. Python ≥ 3.9; hub ≥ 0.34, < 1.0; tokenizers ≥ 0.22.0, ≤ 0.23.0; safetensors ≥ 0.4.3; torch ≥ 2.2 (extra). So torch 2.8.0 is compatible by metadata (resolution not run) | High (metadata) |
| Advisories against 4.57.1 | 7 distinct (12 ids). **Relevant to this path:** GHSA-29pf-2h5f-8g72 (CVE-2026-4372, fixed 5.3.0): a malicious `config.json` with `_attn_implementation_internal` can make `from_pretrained` run attacker code. Mitigation: the pinned `config.json` files contain no such key (checked) and are hash-pinned; load offline from local paths. **Not on this path if the listed APIs are avoided:** X-CLIP conversion (PYSEC-2025-217), GLM4 weights (PYSEC-2025-218), `Trainer._load_rng_state` (GHSA-69w3; torch ≥ 2.6 also mitigates), LightGlue (GHSA-fgcw), `load_custom_generate` (GHSA-x9r9), tokenizer `save_pretrained` path traversal (GHSA-xrqw) | High (listing); Medium (applicability) |
| "current release is 5.23.0" | Confirmed. Requires Python ≥ 3.11, torch ≥ 2.6 (extra), **hub ≥ 1.31, tokenizers ≥ 0.23.1, safetensors ≥ 0.8.0**. The draft's companion pins (hub 0.35.3, tokenizers 0.22.1, safetensors 0.6.2) are incompatible with any 5.x choice; whether 5.x still loads Marian `.bin` and the slow `MarianTokenizer` I did not verify | High (metadata); Unverified (Marian in 5.x) |
| tokenizers 0.22.1, safetensors 0.6.2, huggingface-hub 0.35.3, sentencepiece 0.2.1, numpy 2.3.3, sacremoses 0.1.1 | All exist, none yanked, no advisories listed. arm64 wheels for tokenizers, safetensors, sentencepiece and numpy (cp312). numpy 2.3.3 needs Python ≥ 3.11. hub 0.35.3 pulls `hf-xet` on arm64 | High |

**Pickle security.** torch 2.8.0's `torch.load(weights_only=True)` uses a restricted unpickler; the known bypass (CVE-2025-32434) affected torch < 2.6. A SHA-256 check before loading, plus loading once in an offline process and saving a local safetensors with its hash recorded, is adequate. Two non-pickle paths need no `transformers` for the conversion: the Hub's unmerged SFconvertbot safetensors (pin the PR commit and SHA-256; that trusts the bot's conversion), or the Flax msgpack (needs `msgpack`, another package). The draft's route is fine. Correct the "pickle-only" sentence.

## H. Reproducibility and governance

- **MPS.** Training is not bit-reproducible. Making snapshots the object and recomputing every score on CPU is an acceptable compromise, but it is a departure the human lead should accept explicitly (§15 item 2 already lists it). Add three things: the MPS and macOS versions to the manifest; `PYTORCH_ENABLE_MPS_FALLBACK` unset (any fallback becomes an error); and a G4 check that the 20-update CPU run and the MPS run agree on parameters (relative norm difference ≤ [1e-4]), not only on loss.
- **"Frozen" downloads.** Pin revision and SHA-256 for LFS files and git-blob SHA-1 for small files. Store the converted safetensors' SHA-256 in the freeze. "Frozen" must mean frozen *bytes*, verified at every load, not only at download.
- **Lock rule.** CLAUDE.md allows `--with` for analysis-only tools. A requirements file with hashes is good practice, but `transformers` in the registered training path is not analysis-only. That needs the human lead's acceptance, unless the design follows M9: teachers run once as a quarantined data-generation step; the student is a torch-only Llama with a safetensors header parser (the format is a JSON header plus raw little-endian tensors); tokenization with `tokenizers` only, or a pure-Python byte-level BPE checked against reference token ids.
- **Download approvals.** The human approved "two small teachers" in substance. The **student (SmolLM2-135M, 272 MB)**, the **Tatoeba data (51 MB)**, any **account login to accept the dataset gate**, and the **package downloads** are not covered by those words. Under CLAUDE.md ("No … downloads … without explicit human approval"), these go to the human lead. The lead's delegation to self-approve *studies* does not obviously extend to downloads; flag clearly.

## I. Matrix, seeds, statistics, budget, and a smaller design

### I.1 Statistics

- **Item-level noise is small.** With 1,000 items and a sentence-chrF standard deviation near 0.2, the standard error of a panel mean is about 0.006, and of a gap closure (denominator ≈ 0.4) about 0.02. The 0.03 RET margin is several paired standard errors. The 0.02-nat GEN margin on 51,200 tokens is large compared with item noise. **Replicate (seed and data-draw) variation dominates.** Three replicates give "3 of 3", a replication count, not an interval; the draft says so correctly.
- **NOT REPLICATED is too broad.** "Replicates fall on different sides of a positive or negative threshold", checked before the negative classes, lets a split on any irrelevant threshold hide a 3-of-3 negative. Restrict it to the thresholds that decide the class being assigned (minor L8).
- **Seeds.** 220001+ is disjoint from P9 (170001–179xxx), ADR-0019 (190001–191301) and S1 (210001–210401). My grep of `src`, `studies`, `configs` and `tests` found 22xxxx numbers only as parameter counts (225537, 225793), not as seeds. The implementation's assertion stands.

### I.2 Budget

The projected high end without the 2× headroom is about 30 h (training 13.5, evaluation 10, calibration 5, teachers 1.2). With 2× headroom that is about 60 h against a 36 h cap, so the cut rule will probably trigger before the run, and step 2 needs the human anyway. "Charged as wall-clock hours of S2 processes" with three evaluation workers is ambiguous between counting 1× and 3× (M8).

### I.3 Recommended smallest credible design (target ≤ [10] charged hours; every number marked [ ] is the lead's choice)

1. **Downloads (human-approved list):** the two teachers, SmolLM2-135M and Tatoeba (source and gate decision by the human). No fallback pair is pre-approved. If a teacher fails qualification, stop with TEACHERS-NOT-QUALIFIED.
2. **Data:** as §5.2, plus the A.3 teacher-only sources and the M4 partition. Panels E_A and E_B [500], E_C [250], Q [1,000], D_cal [500], D_con [300]. Training draws T_A^r and T_B^r of [8,000] accepted teacher outputs each, from no-gold sources.
3. **Pilot (before the freeze):** Stage 1 for **both** capabilities, one calibration seed, the memory at L ∈ {4, 12} with one learning rate [0.003], LoRA at two learning rates [3e-4, 1e-3]: 8 cells at U [2,000]. Stop rule: G_cap < 0.25 on D_cal for either capability → NOT STARTED.
4. **Per replicate and order** (first capability → second):
   - **S1**: memory on teacher-1 outputs (U). This is also the single-teacher student.
   - **M-append-frozen** (primary mechanism (i)): append N, freeze old rows, one top-8 over 2N, task-coded queries, no switch (U).
   - **M-ii**: from M-append-frozen; all rows trainable; replay 1:1 of teacher-1 outputs; acceptance on D_con; modification floor [0.10] (U).
   - **LoRA-1** on teacher-1 (U); **L-seq** continues on teacher-2 without replay (U).
   - Free, no training: **M-i-separate** (two S1 memories with an oracle switch; BY CONSTRUCTION reference), **L-sep** (two LoRA-1s with a switch), ensemble, R-icl, R-gloss, R-nn, all ablations (values permuted, word codes permuted, marker-only, words-only, memory off).
   - Per replicate, shared: **M-joint** on mixed teacher outputs (2U). Replicate 1 only: **E-table** per capability (2 × U), **MA-gold** per capability (2 × U), **M-seq-shared** for H22-D (2 × U, optional).
   - Units: replicate 1 = 2 × 5 + 2 + 6 = 18; replicates 2 and 3 = 12 each, for 42 stage-units in total.
5. **Replicates:** preregistered sequential rule. Run replicates 1 and 2. Run replicate 3 only if both show TRANSFER-POSITIVE for at least one mechanism. A positive label needs 3 of 3; a negative or NOT REPLICATED is final at 2. This saves compute without inflating positives. A positive costs ≈ 42 units, anything else ≈ 30.
6. **Hours at the draft's 5–15 min per unit:** 2.5–10.5 h of training (M-ii's 64-row batches cost about 2× per update), plus teachers about 1 h, evaluation about 2–4 h (reduced panels, one worker charged as wall time), plus pilot and rehearsal about 2 h. That is ≈ 8–17 h, so [U = 1,000] may be needed to reach ≤ 10 h. Decide in the rehearsal by a rule written now: U = 2,000 if the projected total with 2× headroom is ≤ [24] h, else U = 1,000.
7. **Label (replaces §11.3 rows 6–9):** TRANSFER-POSITIVE (append-frozen) requires all of the following, in every replicate and both orders, on held-out panels:
   - S1 passes ACQ1 with all controls;
   - M-append-frozen passes ACQ2 and RET empirically;
   - training material is teacher-only;
   - GEN is BY CONSTRUCTION (declared).

   TRANSFER-POSITIVE (append-frozen + consolidation) additionally needs M-ii class 6 above the modification floor. Annotations: NO ADVANTAGE OVER SEPARATE ADAPTERS, EQUIVALENT TO A WORD TABLE, RETRIEVAL SUFFICES, LEXICON-EQUIVALENT, TEACHER-EQUIVALENT-TO-GOLD, BELOW JOINT BOUND, ROUTER (keyword-level).

## J. Label precedence and what S2 cannot establish

- **Row 4 (CONTROL-FAILED)** pre-empts everything, including a clear NO-ACQUISITION. A permutation control at, for example, 0.12 would hide a total failure. Put NO-ACQUISITION before CONTROL-FAILED, and give CONTROL-FAILED an exact threshold (M3). "Ensemble score differs from the teacher's own" is a code check; move it to ENGINEERING-FAILURE.
- **Row 9 (ORDER-DEPENDENT)**, for separate-store M-i, would really mean "German and French differ", since order does nothing there. Under B1's fix it applies to M-append-frozen, where order decides which rows are frozen, and becomes meaningful.
- **Rows 5 and 8** overlap for M-i: Stage B of one order is Stage A of the other.
- **Add to §17 (cannot establish):**
  - that the sparse keyed memory beats a word-vector table (unless E-table loses);
  - that knowledge came from the teachers rather than from gold data (unless the teacher-only arm passes);
  - anything about routing beyond keyword detection;
  - that a frozen *English* LM's success transfers to non-lexical or open-vocabulary use;
  - that MPS-trained snapshots would be reproduced by re-running.

---

## Paste-ready replacement text

**R-B1 (§6.3 table, new first row; §11.3 rows 6–7):**

> | **M-append-frozen** (mechanism i, primary) | N new slots appended to the same store | frozen bit-for-bit | none | B learned in the same store as an untouched A; one top-8 over all 2N slots; queries u(t, w); no switch between memories. Retention is empirical, because A's reads can select B's slots. |
>
> M-i-separate (two stores behind the oracle route) is not trained. It is assembled from the two Stage-1 memories of the same replicate and reported as **BY CONSTRUCTION**. It enters no label.
>
> | 6 | **TRANSFER-POSITIVE (append-frozen + consolidation)** | M-append-frozen and M-ii (above the modification floor, §6.3) are both ACQUIRES-AND-RETAINS in both orders, with teacher-only training material (§5.3) |
> | 7 | **TRANSFER-POSITIVE (append-frozen)** | M-append-frozen is ACQUIRES-AND-RETAINS in both orders, with teacher-only training material; M-ii is not |
>
> No result printed BY CONSTRUCTION satisfies any row of this table.

**R-B2 (§5.3, replacing the verification bullets):**

> - **Teacher-only training sources.** T_A^r is drawn only from training-side, in-vocabulary English sentences that have **no German reference** in any downloaded file. T_B^r is drawn only from those with **no French reference**. Gold references of training-side sentences are used for Q, D_cal, D_con and the verification audit, never as student training targets, except in MA-gold.
> - **Verification.** A teacher output is accepted if its length-normalized beam log-probability ≥ τ, its length ratio to the source lies in [ρ1, ρ2], and it differs from the source after normalization. τ, ρ1 and ρ2 are fixed on Q before the run, as the most permissive setting whose measured precision on Q (share of accepted outputs with chrF ≥ [0.60] against the best reference) is ≥ [0.90]. The precision and its 95% Wilson interval are reported. A per-item correctness claim is not made. *(PENDING LEAD REVIEW: whether measured-precision verification satisfies "suitable verification".)*
> - **MA-gold** trains Stage 1 on [8,000] gold pairs drawn from gold-bearing training-side sentences. It is a reference, not a bound. Annotation TEACHER-EQUIVALENT-TO-GOLD if its G is within 0.03 of Stage 1's or above.

**R-B3 (§14, after the dataset row):**

> `Helsinki-NLP/tatoeba_mt` is gated (`gated: auto`, read 2026-11-15). Unauthenticated downloads return HTTP 401 and the LFS hashes are not public. The human lead decides between accepting the gate with a personal account and an ungated release of the same files. Data SHA-256 values are recorded at first download and frozen from then on. The student model, the data and any account action are downloads outside "the two small teachers" and need the human lead's explicit approval before step (4) of §16.

**R-M1 (§6.3, after the retention constraint):**

> **Modification floor.** M-ii counts as retention under modification only if the relative change of the first memory's value rows, ‖V_A(after) − V_A(before)‖_F / ‖V_A(before)‖_F, is ≥ [0.10]. Below that, the cell is RETENTION BY INERTIA and cannot be class 6. Because the acceptance check on D_con selects for retention, RET for a published M-ii is reported as "selected, then confirmed on E".

**R-M2 (§7 table, new row):**

> | **E-table** | one trainable 576-vector per (task, vocabulary word) and per task marker, added at layer L at the same positions as the memory's reads; no keys, no top-k | Stage 1 of each capability, replicate 1 | whether the keyed sparse memory adds anything over a word-vector table | — |
>
> Annotation **EQUIVALENT TO A WORD TABLE**: E-table's G is within 0.03 of Stage 1's or above, on both capabilities.

**R-M3 (§7 ablations and §11):**

> Ablations on every memory cell: memory off; values permuted across slots; **word codes** permuted across vocabulary words (the marker code is kept); **marker-only** (word reads off); **words-only** (marker read off). ACQ1 and ACQ2 require G ≤ 0.10 under value and word-code permutation and G ≤ [0.25] under marker-only. CONTROL-FAILED (study label) applies when a value or word-code permutation gives G ≥ 0.50 in any cell. It is placed after NO-ACQUISITION.

**R-M4 (§5.2, replacing the identity bullet):**

> Identity groups are the connected components of the graph whose nodes are training and evaluation sentence pairs, with an edge when two pairs share a normalized English string, a normalized English string after contraction expansion (fixed list in the code), or any normalized reference string. A group is assigned whole to the evaluation side if any member is in a test file. G1 checks that no normalized reference or teacher output of any training stream equals a normalized reference of any evaluation panel. The share of evaluation items with a word-swapped training neighbour (Levenshtein distance 1 at word level) is reported.

**R-M5 (§7 preamble and §11.1):**

> Every adapter and memory arm is applied only under its route: no read and no adapter on route ∅. GEN is printed **BY CONSTRUCTION** wherever G5 shows bit-identity. It enters a label only in the learned-router condition. The always-on condition (adapter or reads with the first task's codes on every in-vocabulary word) is a diagnostic.

**R-M6 (§11.4, SPARSE-RETENTION):**

> SPARSE-RETENTION compares M-seq-shared (codes u(w) shared by both tasks) with L-seq. M-seq (task-specific codes) is printed beside it, and the difference between the two is attributed to oracle task coding, not sparsity.

**R-M7 (§12.2):**

> With the calibrated settings, on D_cal, Stage 1 is run for **both** capabilities. If either has a gap closed below 0.25, the registered run does not start (NOT STARTED: STUDENT CANNOT USE THE MEMORY ON THIS TASK). The pilot's scores are optimistic, because D_cal also selected the calibration setting. They are not results.

**R-M8 (§13.2 caps):**

> Charged hours are the sum of wall-clock hours over all S2 processes (k parallel workers for t hours charge k·t). Cut rule step (2) removes optional replay-without-growth controls. It is not a required baseline: the human's list names "sequential LoRA/adapters", which L-seq provides.

**R-M10 (§11.3, fixed line):**

> Every label is printed with: **"oracle-assisted (word-level addresses supplied by rule); lexical translation of short closed-vocabulary sentences, two capabilities of one kind; frozen English student; teacher-only training material verified by measured-precision filter; not autonomous learned memory."**

---

## L. Minor findings

1. §4.1 security note: the repositories are not pickle-only (msgpack, h5, and rust_model.ot for en-de); safetensors exist in unmerged bot PRs. Correct the sentence; the loading plan is fine.
2. en-de `tokenizer_config.json` lacks `model_max_length` (open PR 6); tokenization depends on `transformers` internals. Freeze reference token ids for 100 sentences per teacher as a gate.
3. The fallback en-es is a Tatoeba-Challenge model, a different regime from the 2020-02-26 OPUS pair. Say so, or drop the fallback (my recommendation: stop on failure).
4. §3: list the gate change (linear, initial value 0, versus sigmoid with initial value −2), the absent output projection, and a non-zero value initialization (otherwise zero gradients). Replace "well separated" (probe: 0.50–0.59 own-slot mass).
5. chrF: give the exact definition and a sacrebleu cross-check (B).
6. Student `max_new_tokens = 32`: German and French text in an English BPE may truncate. Measure the truncation rate of gold references in student tokens during the rehearsal and set the limit to the 99.5th percentile.
7. "STORED SMALLER THAN ENSEMBLE" is decided by arithmetic (0.938 > 0.75). Print it as arithmetic, not as a comparison. Define "FEWER VALUE ROWS ACTIVE" per generated token on both sides.
8. NOT REPLICATED: restrict it to the thresholds that decide the class being assigned.
9. Top-k ties: fix a rule (lowest slot index) and keep the evaluation batch composition fixed, for CPU determinism across workers.
10. G7 for the data: "recorded at first download", not "equal to pinned".
11. Download through plain HTTPS of pinned `resolve/<revision>/<file>` URLs with SHA-256 checks. This avoids `huggingface-hub` and `hf-xet` in the download step.
12. §0 item 1: the claim that procedural skills have no recurring unit is overstated (B).
13. The learned router is a keyword classifier. Say so in its annotation (the draft partly does).
14. Calibration tunes the memory's layer and learning rate but LoRA only the learning rate (4 vs 4 settings, which is fair in count). Note that LoRA placement (q, v) is fixed, not tuned.
15. Count the in-vocabulary training-side pool before fixing the teacher-generation projection; "2 × 60,000" is an assumption.

## K. Commands and environment

- Machine: Apple M5 Max (inventory), `arm64`, macOS (Darwin 27.2.0). curl 8.7.1. Date 2026-11-15 05:15 UTC.
- Hub metadata (no weights): `curl -sL -A generic-client https://huggingface.co/api/models/<repo>/revision/<sha>`, `/tree/<sha>`, `/refs?include_prs=1`, `/discussions`, and `https://huggingface.co/<repo>/resolve/<sha>/{config.json,README.md,tokenizer_config.json,generation_config.json}`, for `HuggingFaceTB/SmolLM2-135M` and `Helsinki-NLP/opus-mt-{en-de,en-fr,en-es}`. Dataset: `https://huggingface.co/api/datasets/Helsinki-NLP/tatoeba_mt`, `/tree/f337793b…/data/{dev,test}`, `/commits/main` (returned the gate error), and README. Gate check: `curl -I` of `…/datasets/Helsinki-NLP/tatoeba_mt/resolve/f337793b…/data/test/tatoeba-test.eng-fra.tsv` → 401; also one 1-byte ranged GET → 401, nothing received. `curl -I` of the student safetensors and the en-de `.bin` → 302 (not followed). Saved responses: `adr-0022-review/web/` (58 files).
- PyPI: `https://pypi.org/pypi/<pkg>/<ver>/json` for the seven packages and `transformers` latest. OSV: `https://api.osv.dev/v1/vulns/<id>` for 7 advisory ids. Saved in `web/`.
- Arithmetic: `python3 -I scripts/param_counts.py web` → `scripts/param_counts.out.txt` (system Python, standard library only).
- Probes: from the worktree, `uv run --locked python -I <R>/scripts/shared_store_interference.py` and `…_2.py` (torch 2.8.0, CPU, float64, seeds 1–3) → `scripts/*.out.txt`. Synthetic random vectors, idealized keys; an order-of-magnitude argument, not a prediction of trained behaviour.
- Repository reads: `grep -rnE "\b22[0-9]{4}\b" src studies configs tests` (only parameter counts found); `studies/p9/model.py` lines 230–293 and 455–465; `studies/p9/core.py` lines 130–153.
- Failed attempts, kept as part of the record: (1) a first fetch loop without `-L` saved HTTP 307 redirect bodies instead of the config and README files; refetched with `-L`. (2) My first inspection command contained an unquoted `echo == …`, which zsh rejected (`= not found`) before printing everything; rerun with quoting. (3) The `commits` endpoint returned the gate error. That error is how the gating was discovered, so it is evidence, not a defect.

Astra review: NOT_PERFORMED. This review is not Astra validation and not human approval.
