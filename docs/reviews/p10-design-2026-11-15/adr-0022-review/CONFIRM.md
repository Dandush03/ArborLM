# Confirmation review of ADR-0022 revision 3 (P10-S2)

- **Reviewer:** Claude Opus 5.5 (`claude-opus-5-5`), the same specification auditor as `REVIEW.md` (revision 1). I wrote no part of ADR-0022.
- **Date:** 2026-11-15 (UTC).
- **Object:** `S/ADR-0022-p10-s2-two-teacher-transfer.rev3.md` (635 lines, mtime 00:29). I diffed it against `.rev2.md`: 154 changed lines, consistent with the revision history.
- **Status:** independent engineering and mathematical review evidence. **Not Astra validation, not human approval. Astra review: NOT_PERFORMED.**
- **Ran:** read-only web checks.
  - HTML directory indexes of `downloads.tatoeba.org/exports/per_language/{eng,deu,fra,spa}/`.
  - HEAD requests (no body) for the five primary Tatoeba files.
  - The Tatoeba downloads page.
  - PyPI JSON for `sacrebleu` 2.5.1.
  - The text of `sacrebleu/metrics/chrf.py` at tag v2.5.1, read as a text file.
- **Re-checked by hand:** the cell, unit and hour arithmetic of §13.
- **Not done:** no download, no install, no package resolution, no training, no git.

## Verdict: **READY AFTER LISTED TEXT EDITS** (paste-ready below), then READY for the lead's self-approval once the human lead answers the open decisions (§7)

Revision 3 fixes all three blockers in substance. A positive label now needs the teacher (training material exists only as teacher output) and needs an arm where interference can happen (one shared top-8). No new blocker.

Ten findings remain at MAJOR level (C1–C10). Each can be fixed by a text change. Three of them would otherwise drive the run onto a perverse path:

- C1: gate G5 contradicts the append design and would raise ENGINEERING-FAILURE.
- C2: absolute control limits can turn a working memory into NOT_EVALUATED.
- C5: the qualification filter is fitted at its own edge, so it fails its check about half the time.

C3 reports a mistake in my own revision-1 advice (M6).

---

## 1. Blockers and majors of revision 1

| Finding | Status | Note |
|---|---|---|
| B1 | **Fixed** | M-append-frozen is primary; row "i only" removed; nothing BY CONSTRUCTION earns a label; order now decides which rows are frozen. New defect in the gate text: C1. |
| B2 | **Fixed** | Training material comes only from no-gold sources; MA-gold is redefined; every positive row requires teacher-only material. The filter has an edge-selection problem: C5. |
| B3 | **Fixed** | Gated copy dropped. I verified the Tatoeba exports (§6). All downloads wait for the human lead. |
| M1 | Fixed | Floor 0.10; RETENTION BY INERTIA is a class; "selected, then confirmed". |
| M2 | Fixed | E-table in every replicate. |
| M3 | **Partly** | Ablations added and CONTROL-FAILED placed after NO-ACQUISITION. The absolute limits of 0.10 on 300 items are fragile (C2). |
| M4 | Fixed, new risk | Connected components are adopted. A giant component is possible (C6). |
| M5 | **Diverging** | GEN is now a label gate under the keyword router, but it is near-vacuous and looser than revision 1 (C4). |
| M6 | **Fixed as I asked, but my request was partly wrong** | See C3. |
| M7 | Fixed | Pilot covers both capabilities, but only at U = 2,000; see C7 for the U = 1,000 rungs. |
| M8 | Fixed (lead's ruling on replication) | Matrix, charging rule and cut wording fixed. The rung rule is judged in §4. |
| M9 | Fixed | Registered path is locked-only; the new tokenization definition needs tests (C8). |
| M10 | Fixed | Scope line added; "complementary" goes to the human lead. |
| Minors L1–L15 | Fixed | Except the chrF definition, which does not match sacrebleu for short strings (C10). |

## 2. Rulings, and which trivial system passes each gate of the new label table

| Gate / label element | Trivial system that passes | Caught? |
|---|---|---|
| Teacher-only material (positive rows 6–8) | None from gold: the gold path cannot earn a label. The student's target language can come only from the teacher outputs. | **Yes. The teachers now matter causally.** |
| ACQ1 / ACQ2 | E-table, LoRA, Dice lexicon | Annotations only. The label does not claim superiority, which is acceptable. |
| RET on M-append-frozen | A word table with task-partitioned rows, or separate adapters (L-sep), retain **by construction**. The shared store has to survive crosstalk it creates itself. | Retention is now empirical; probe: 22–27% of read weight moves. The label must say a table or separate modules would not lose A at all (minor m1). |
| Sequential interference possible? | Yes: one top-8 over 2N rows. | — |
| GEN under the keyword router | **Any system.** The router is trained on WikiText-2 *train* prefixes as "none" and tested on WikiText-2 *validation* windows, the same domain and format. Prompts all begin "English: …\nGerman:". If the router never fires, the loss ratio is exactly 1.000. The bound is 1.05 × loss, about 0.15 nats at a loss near 3, which is looser than revision 1's *negative zone* (0.10 nats). | **No** (C4). |
| WITHHELD row | Fires only on router false triggers. A wrong trigger reads task codes at every in-vocabulary word of the window. The row's wording correctly blames the route. | Wording sound; gate weak (C4). |
| Ensemble or retrieval | Annotation only | Fine |

**The perverse paths I found:**

- **C1 (G5 contradiction).** G5 says "newly appended rows with gate 0 change nothing". In one shared top-8 that is false. Appended rows with fresh keys enter the top-8 of first-capability queries and take softmax weight: about 22% in the idealized probe. They contribute g₂·V = 0, but they push first-stage rows out and renormalize the rest. A's read therefore changes at the append, and §6.3's "append cost" says exactly this. As written, G5 must fail, giving ENGINEERING-FAILURE (row 1), or an implementer will quietly exclude gate-0 rows from selection, which removes the interference the design needs.
- **C2 (absolute control limits).** Permuting values or word codes keeps the vectors German (or French). The output can then turn German-like with the wrong words and still earn chrF credit for function words and endings. A legitimate memory can show G_perm of 0.1–0.2. On 300 items the paired 95% half-width of a control's G is roughly 0.03–0.05, using the review's assumed sd of 0.2. Under "every replicate × both orders × two permutations", one excursion above 0.10 sends ACQ1 to NOT_EVALUATED and the study to row 12 with no named reason.
- **C5 (filter at its own edge).** The selection picks "the most permissive of 24 settings with precision ≥ 0.90 on Q_fit", so the chosen setting sits at its own edge. Its true precision is about 0.90 or a little below. The check then needs a point estimate ≥ 0.90 on Q_check with as few as 150 items. That passes with probability near ½, so a good teacher has roughly even odds of being disqualified, and the study then falls through to the fallback.

## 3. Segment-level tokenization: risks and the equivalence test needed

SmolLM2 uses GPT-2-style byte-level BPE. Its pre-tokenizer attaches a leading space to the next word. Concatenating separately tokenized segments differs from whole-string tokenization at these points:

1. **Leading space.** `"English:"` + `" {source}"`: the source must be tokenized *with* its leading space (` Tom`, not `Tom`). The same holds for the target after `German:` (` Ich …`).
2. **Whitespace runs.** `"\n"` next to another whitespace character merges in the regex (`\s+(?!\S)`). The `\n` between the target and the next `English:` in C1 and in R-icl must be its own segment exactly as whole-string tokenization would produce it.
3. **BOS.** Say whether `<|endoftext|>` (id 0) is prepended. The equivalence logits and every registered input must use the same convention.
4. **Word-to-subword map for reads.** "Last subword of each in-vocabulary word" must come from tokenizer offsets in the data-generation step and be stored, not recomputed.
5. **Decoding.** Byte-level tokens can split multi-byte UTF-8 characters (ä, é, ç). Decode whole id sequences, never token by token, with the reference's error policy. The newline stop rule must fire on any generated token whose bytes contain `\n`, including merged tokens, and cut the text at the first `\n`.
6. **Normalization order.** Tokenize raw NFC text; normalize only for identity and chrF.

**Equivalence tests to add to §14.2 and G8 (paste-ready, see E8):**

- (a) Segment ids against whole-string ids for every training row, evaluation prompt and R-icl prompt. Mismatch rate reported; 0 required on prompts. Target mismatches are listed, and the training loss uses the segment ids.
- (b) `decode(encode(x)) == x` for every reference and accepted teacher output.
- (c) The decoder against the reference on 1,000 *random* id sequences, including split multi-byte characters, not only on valid text.
- (d) Logits at the injection point: with a fixed vector added at the output of block L, the study's student must match the reference with a forward hook at the same place within 1e-3. This pins the off-by-one between "output of block L" and `hidden_states[L+1]`.
- (e) Greedy decoding with a KV cache against full recomputation, and against the reference `generate`, on 100 prompts: identical tokens.

The 1e-3 logit tolerance is reasonable for a 30-block FP32 model on CPU (expected differences are around 1e-5 to 1e-4). Measuring the reference's own run-to-run difference, as open question 6 proposes, is better.

## 4. The rehearsal rung rule

- **Order 4×2,000 → 3×2,000 → 4×1,000 → 3×1,000.** The order is defensible, and the choice depends on measured throughput, not on outcomes. That is legitimate.
- **Under-powered and mislabelled rungs (C7).** Calibration and the pilot gate run at U = 2,000 (§12.1). If rung 3 or 4 is selected, the setting and the pilot pass belong to a different U. A U = 1,000 negative could then be under-training rather than the absence of a capability. Fix: constant learning rate, so take snapshots of the calibration cells at 1,000 updates, and re-apply the selection rule and the pilot gate at the chosen U. Every label and class line then prints "(n replicates, U = …)", and NO-ACQUISITION reads "within U updates".
- **"Every replicate must pass": what the probability means.** Treat a mechanism's outcome as an independent per-replicate pass with probability p. Then 4 of 4 has probability p⁴: at most 1/16 = 0.0625 when p ≤ 0.5, and 3 of 3 at most 0.125. So a positive at 4 of 4 is evidence that the per-replicate pass rate exceeds ½; it is not a confidence interval on an effect. It is strict in the other direction too: a true per-replicate pass rate of 0.8 yields 4 of 4 only 41% of the time. Expect INTERMEDIATE or NOT REPLICATED often. The orders share each replicate's data draw, so they are not independent evidence. This is defensible, and matches the human's "close any possible misguidance", if §9 states it (E7).

## 5. Precedence, cells, hours

- **Precedence** is sound with one gap. Mechanism class 1 (NOT_EVALUATED: ACQ1 fails in any replicate) captures a marker-only failure, a noisy control (C2) and an undefined gap alike, and the study then lands in row 12 without a reason. Add a printed reason line (E2). WITHHELD before the positives and after CONTROL-FAILED is correct. M-ii failing GEN alone goes to row 8 as stated.
- **Cells (my recount):** S1 2 + M-append-frozen 2 + M-ii 2 + M-seq-shared 2 + M-seq 2 + M-joint 1 + E-table 2 + MA-gold 2 + LoRA-1 2 + L-seq 2 = **19**. Units: 18 store-type (M-ii counted twice; M-joint twice) + 4 LoRA. **76 / 57.** Memory cells for ablations: 13. All correct.
- **Hours (my recount from §13.3's per-unit ranges):** rung 1 14.0–35.2 h, rung 2 10.6–26.6, rung 3 10.0–27.2, rung 4 7.6–20.6. These match the draft. With pre-freeze work P ≈ 3.5–7 h, P + 2R ≤ 36 needs R ≤ about 14.5–16 h, as the draft says. At mid-range throughput only rung 4 fits, and "not started" is a real outcome. The draft says so honestly.
- **Affordable additions (C3, C9):** dropping M-seq-shared (C3) frees 2 store units per replicate; adding L-joint (C9) costs 2 LoRA units. Net about +0.1 to +0.3 h per replicate.

## 6. Downloads against what I verified (2026-11-15, read-only)

| Item | Finding | Confidence |
|---|---|---|
| Rows 1–3, 5 (models) | Unchanged from my revision-1 verification; the table matches (sizes, SHA-256, licences). | High |
| Tatoeba per-language indexes | Readable without an account. Every listed size matches exactly: eng_sentences 24,947,715; deu_sentences 12,144,786; fra_sentences 9,805,546; eng-deu_links 3,557,634; eng-fra_links 2,679,128; spa_sentences 6,376,323; eng-spa_links 1,762,602. Dated 14-Nov-2026 (07:49 and 08:14). | High |
| Files served without an account | **HEAD returned HTTP/2 200 with matching `content-length` and `application/octet-stream`** for the five primary files. That resolves the draft's "TO VERIFY" on account-free access. No body fetched. | High |
| Licence and weekly regeneration | Downloads page contains "CC BY 2.0 FR", "every Saturday", and the link-file columns "Sentence id" / "Translation id". | High (strings present); per-pair file format still to confirm at download |
| Link symmetry | `deu/deu-eng_links` is 3,552,331 B against `eng/eng-deu_links` 3,557,634 B, and `fra/fra-eng_links` 2,678,076 B against 2,679,128 B. They may differ only in order or compression, or in content. Use the `eng/` files and check symmetry at download (minor m4). | Medium |
| Weekly drift and the fallback | The fallback's Spanish files fetched later would come from a different weekly export than the English file. Fetch all files in one session (+8.1 MB), and open the fallback files only if the fallback is invoked (minor m5). | High |
| sacrebleu 2.5.1 | Exists, Apache-2.0, Python ≥ 3.8, no advisories. Brings portalocker, regex, tabulate, colorama, lxml and numpy. Latest is 2.6.0. | High |
| sacrebleu chrF definition | Default (`eps_smoothing=False`): averages precision and recall over **effective orders only** (orders where hypothesis and reference both have n-grams), then F-β; whitespace excluded by default. ADR §10.1 says "averaged over the six orders". The two differ for strings shorter than 6 characters after whitespace removal, so the 0.001 cross-check would fail on short items (C10). | High (source text) |
| Total | 930 MB primary; 1,253 MB with the fallback. Matches my arithmetic: models 876.9 + data 53.1. | High |

## 7. The human's requirements: still missing or diverging

1. **"Ordinary multi-teacher distillation"** exists only in memory form (M-joint). L-joint, an adapter trained on both teachers' mixed outputs and the ordinary form of multi-teacher distillation, was dropped (C9).
2. **Mechanism (i) "with learned routing".** Revision 3 realizes it as learned keys competing in one top-8 under oracle queries, plus a keyword router that only decides whether to read. Defensible, but the ADR should state this reading explicitly (E9). PENDING LEAD REVIEW.
3. **General quality "before and after every stage".** The keyword-router GEN is measured only for stage-2 snapshots. Add the S1 snapshots (E4).
4. **"Learned addressing evaluated separately if qualified".** Revision 1 had a sentence pointing to a separately approved supplement if S0 qualifies an interface; revision 3 only lists it as reserved. Restore the sentence (minor m6).
5. **Cost and active-memory "gates".** Registered rules with descriptive standing. Acceptable, because TRANSFER-POSITIVE is independent, but say they are rules with no label consequence (already implied).
6. **Everything else** on the human's list (teachers, licences, pinned revisions, frozen student plus memory, sequential stages, mechanism ii, sequential LoRA, ensemble, retrieval, capabilities A, B, combined, B→A order, separate data, verification, sequence-level distillation, the five cost measures, no fusion claim, independent label, small teachers, no cloud, 36 h) is met.

**Decisions that stay with the human lead (listed, not resolved):**

- downloads of the student (272.4 MB), the Tatoeba exports (53.1 MB) and the fallback (315.3 MB + 8.1 MB);
- whether package wheels for the data-generation step count as downloads;
- whether two translation directions are "complementary capabilities";
- whether measured-precision filtering is "suitable verification";
- the MPS departure and the packages-outside-the-lock departure (§15).

## 8. Findings (C1–C10 MAJOR, m1–m7 minor) with paste-ready edits

**C1, E1 (§12.3 G5; replace):**
> **G5** (a) On route "none", logits equal the frozen student's bit for bit on the general panel. (b) A new store with gate 0 on an empty base changes nothing. (c) **Gate isolation of appended rows:** after the append and before any update, the read r with the appended rows' values replaced by arbitrary values equals r with them at zero, bit for bit (so g₂ = 0 isolates the values). The appended rows do take top-8 weight from first-stage rows. That change is the **append cost** (§6.3), measured and not gated. Appended keys are initialized from the same distribution as first-stage keys *(lead's choice)*, and the report states that the append cost depends on that initialization.

**C2, E2 (§11.1 ACQ1/ACQ2 control clauses; replace):**
> … G ≥ 0.50; **G − max(G_value-perm, G_code-perm) ≥ 0.30** *(lead's choice)*; G_marker-only ≤ 0.25. Control G values use the teacher and Stage 0 scores of the same 300-item subsample.

Add under §11.3:
> Every TRANSFER-INCONCLUSIVE label prints the reason of each NOT_EVALUATED class: undefined gap, acquisition below 0.50, lexical margin below 0.30, or marker-only above 0.25.

**C3, my own error in revision-1 M6, E3 (§1 H22-E, §6.3, §11.4).**

M-seq-shared gives both tasks *identical* addresses for the same word. The store then has to hold German and French values on the same rows, so forgetting is near-certain whatever sparsity does. It does not isolate sparsity: in this design, sparsity protects A only when addresses differ, and here they differ only through the oracle task code. Replace:

> **H22-E (descriptive, no hypothesis test).** In this design the retention effect of sparsity cannot be separated from oracle task coding: different tasks touch different rows only because their codes differ. M-seq (task-specific codes) is compared with L-seq and printed as "sparse store with oracle task codes against a dense adapter". M-seq-shared is removed. Its two units per replicate pay for L-joint (C9).

Rename the annotation to **TASK-CODED SPARSE RETENTION / NONE**, with the rule M-seq against L-seq.

**C4, E4 (§11.1 GEN and §6.4(a); replace the threshold and add hard negatives):**
> GEN: in condition (a), loss ≤ the unmodified student's + **0.02 nats** *(lead's choice; revision 1's value)* on a panel of 200 windows of which **100 are WikiText-2 validation windows that contain any of the strings "German", "French", "English", "translation" or a line ending in ":"** (selected by rule with the partition seed), and 100 ordinary windows. Printed beside it: the router's false-trigger count per stratum, and the always-on loss increase (b). A pass is described as "the keyword router stayed silent", not as "the memory preserves general language". GEN is measured for every S1 and stage-2 snapshot, so general quality is reported before and after every stage.

**C5, E5 (§5.3 Fixing the filter):**
> … as the most permissive setting whose **95% Wilson lower bound** of precision on Q_fit is ≥ 0.90 … The chosen setting must then show a point precision ≥ 0.90 on Q_check with at least 150 accepted items.

(This answers open question 5. Selecting on the lower bound on fit and checking the point estimate on held items removes the edge effect without making the check itself stricter.)

**C6, E6 (§5.2 identity groups; add):**
> The size distribution of identity groups is reported before assignment. Groups larger than 50 sentence pairs *(lead's choice)* go to the training side by rule. Of the remaining groups, the partition seed assigns groups to the evaluation side until it holds 20% of the remaining pairs (counted in pairs, not groups).

**C7, E7 (§12.1, §12.2, §9):**
> Calibration cells save a snapshot at 1,000 updates. If the rehearsal rule selects U = 1,000, the selection rule and the pilot gate are applied to those snapshots. Every class and label line prints "(n replicates, U = …)", and NO-ACQUISITION reads "within U updates". **Meaning of "every replicate":** if a mechanism's per-replicate pass probability were 0.5 or less, n of n passes would occur with probability at most 0.5ⁿ (0.0625 for four, 0.125 for three). The two orders share each replicate's draw and are not independent evidence. A true per-replicate pass rate of 0.8 gives 4 of 4 with probability 0.41.

**C8, E8 (§14.2 step 4 and G8; add tests (a)–(e) of §3 above, plus):**
> A model input is the concatenation of segment ids. Each segment is tokenized with its leading space where whole-string tokenization would attach one, BOS is [prepended / not prepended] in every input, and newline separators are their own segments. The registered path's stop rule fires on the first generated token whose bytes contain 0x0A. Decoding is over whole sequences.

**C9, E9 (§7 table, new row, and §6.3):**
> | **L-joint** — ordinary multi-teacher distillation (adapter form) | one LoRA of rank 84 on the mixed material of both teachers, 2U | yes | the ordinary multi-teacher student | anything about order |
>
> **Learned routing in mechanism (i)** is realized as learned keys of all rows competing in one top-8 under oracle queries, and a learned keyword router that decides whether the store is read. The human lead's phrase may intend more; this reading is stated, not assumed.

**C10, E10 (§10.1 chrF):**
> … precision and recall averaged over the **effective** orders (orders at which both hypothesis and reference have at least one n-gram), then F with β = 2, as sacrebleu 2.5.1's default (`eps_smoothing=False`); an item with no effective order scores 0 …

**Minors.**

- **m1.** Add to §17: "Retention in the shared store is retention against crosstalk that the shared top-8 itself creates; a word table with task-partitioned rows or separate adapters retain by construction."
- **m2.** Say whether the first-stage gate g₁ is trainable in M-ii (it should be, or say why not).
- **m3.** ACQ2 controls on M-append-frozen: say whether values are permuted across all rows or only the second stage's, and whether the codes permuted are the second task's.
- **m4.** Use the `eng/` link files and check symmetry against the `deu/` and `fra/` files at download.
- **m5.** Fetch all Tatoeba files, fallback included, in one session.
- **m6.** Restore: "If S0 qualifies an interface, evaluating it in S2 needs a separately approved supplement."
- **m7.** The 0.10 modification floor is a Frobenius ratio over all first-stage rows. Rows never selected cannot move, so state that the floor may be hard to reach, and report the share of first-stage rows that changed at all.

## Commands and environment

- Same machine and tools as `REVIEW.md` §K. Date 2026-11-15 UTC.
- `curl -sL -A generic-client -o web/tatoeba/idx_<l>.html https://downloads.tatoeba.org/exports/per_language/<l>/` for eng, deu, fra and spa, followed by a `grep` for file names and sizes.
- `curl -sI` on `…/per_language/{eng/eng_sentences.tsv.bz2, eng/eng-deu_links.tsv.bz2, eng/eng-fra_links.tsv.bz2, deu/deu_sentences.tsv.bz2, fra/fra_sentences.tsv.bz2}` (HEAD only).
- `curl -sL https://tatoeba.org/en/downloads` saved to `web/tatoeba/downloads_page.html`.
- `https://pypi.org/pypi/sacrebleu/2.5.1/json`.
- `https://raw.githubusercontent.com/mjpost/sacrebleu/v2.5.1/sacrebleu/metrics/chrf.py` saved as text (`web/sacrebleu_chrf_v2.5.1.py.txt`), read with `grep`, not executed.
- No new probe. The quantitative statements about appending reuse `scripts/shared_store_interference*.out.txt`. The control-noise half-widths (C2) are back-of-envelope estimates from an assumed per-item sd of 0.2; they are not measured.

Astra review: NOT_PERFORMED. This confirmation is not Astra validation and not human approval.
