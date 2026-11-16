# ADR-0022 addendum — the combined tasks C1 and C2 and the strengthened COMPOSES rule

- **Status: Addendum to ADR-0022 revision 5 — combined tasks C1 and C2 and the strengthened COMPOSES rule; checked by the auditor (READY SUBJECT TO edits, applied here); the strengthened rule and its two tightenings are the human lead's decisions of 2026-11-15; approved by the human lead and adopted by the lead on 2026-11-15 (adoption record at the end). Astra review: NOT_PERFORMED.**
- **Date:** 2026-11-15 (UTC). Drafted by the lead (Claude Fable 5.2). Checked by Opus 5.5 in a separate context (`CHECK_C1_C2.md`: majors M1–M4, minors m1–m11, edits E1–E13). The text after the edits has not been re-read by the auditor. Nothing is implemented or run under it. SPEC: PENDING ASTRA REVIEW.
- **Why.** The implementation stopped at `PendingLeadReview`: the ADR "does not say how C1 pairs two sources or how C2 lays out its prompt", and an adapter applied to a sequence of two tasks was reported NOT_EVALUATED for the same reason. This addendum fixes everything the COMPOSES lines need, before any calibration.
- **What it changes.** It adds definitions to §6.4, one listed seed to §9 and G9, checks to §14.2 test (a) and to the rehearsal, and a cost projection to §13.3. **By the human lead's decision of 2026-11-15, made before any S2 observation, it replaces the COMPOSES rule of §11.4** with a per-answer rule on the gap above the untrained student (§8). It changes no other threshold, and no arm, model, data source, replicate count, rung or cap. The new rule carries one new number, the 0.50 cut of DOES NOT COMPOSE, which the human lead agreed; and two tightenings, B(i) and B(ii) of §8, which the human lead confirmed: two existing thresholds reused as conditions for being defined, and the harder of two floors in the numerator.
- **The human lead's decision, verbatim** (full record: `docs/reviews/p10-design-2026-11-15/HUMAN_DECISIONS_2026-11-15.md`, p10-design worktree):

  > let's strenght the registerd rule, the ost is aceptable

  and, after the lead described the per-answer gain rule:

  > agree with your proposed rule

  and, in answer to the lead's question on the two tightenings B(i) and B(ii) of §8, "Do you confirm the two tightenings? If you'd rather keep the rule exactly as you agreed it, I'll strike them.":

  > I agree with your recommendation

- **Rule for open points** (the ADR's): an existing convention of the ADR where one exists, otherwise the option that is harder for a positive composition line; for a baseline, the strongest fair form (AGENTS.md: "Preserve strong baselines"). Each is marked **[lead's choice]** with the alternative, and listed in §12.
- Oracle qualification, unchanged: every address and every route below is supplied by rule. "S1 and S2 must not claim autonomous learned-memory success from oracle-assisted results." (the human lead; ADR-0022 header, §11.3, §18).

## 1. Every existing mention, and consistency

| # | Where | Text | How this addendum stands to it |
|---|---|---|---|
| 1 | §5.2 panel table | "E_C \| evaluation \| 500 *(lead's choice)* \| held-out sentences with both; basis of the combined tasks" | Both tasks use every E_C sentence and no other sentence (§2). |
| 2 | §5.2 sufficiency | "If E_A or E_B cannot reach 500 items, E_C 250, or an accepted pool 8,000, the study stops" | n = \|E_C\|, between 250 and 500; nothing is added to the sufficiency rule. |
| 3 | §5.4 Routes | "A route says which task codes a segment is read with: none, A, B, or both (combined task C2)." | C1 gives each of its two segments one route. C2 gives its source route "both" (§4, §5). |
| 4 | §6.4 | "**Combined tasks** (never trained on), scored for M-append-frozen, M-ii, M-joint, L-joint, L-seq, M-i-separate, L-sep and the ensemble" | The scored set is exactly this list (§7). No training stream and no router stream contains a two-answer sequence. |
| 5 | §6.4 | "C1, two sources: `English: {s1}\nGerman:` …, then after the model's own answer `\nEnglish: {s2}\nFrench:` …" | §4 is this layout on half the items and its mirror image (French first) on the other half; the model's own answer stays in the context. **A stated extension of the ADR's text** (§2). |
| 6 | §6.4 | "C2, one source, both answers: the source words are read with both tasks' codes and the reads are summed." | §5: two reads per source word, one per task code, summed. |
| 7 | §6.4 | "Score: mean chrF of the two answers; an item passes if both match a reference exactly." | §6; still computed and printed. |
| 8 | §9 | "The partition seed 220901 draws in this order: … E_A, E_B, E_C, E_open." | E_C is built as before; the new seed 220911 is used after it (§3). |
| 9 | §11.3 | "The words … COMPOSES … and every other class, mechanism, router, composition or cost line, are therefore printed only directly under that line" | §9. |
| 10 | §11.4 | "COMPOSES C1 / C2 \| mean over replicates of the combined score ≥ 0.80 × the mean of the arm's two single-task scores" | **Replaced by the human lead's decision** (§8). Revision 5's ratio is still printed beside the new line, labelled as replaced. |
| 11 | §11.4 | "Every annotation, the ROUTER and COMPOSES lines included, is printed under the oracle-assisted line of §11.3, also when it appears in a table of its own." | §9. |
| 12 | §13.3 table | "Combined panels, append point, ablations on 300 items, GEN and router lane, diagnostic, retrieval \| CPU \| — \| 0.9–3.0 h \| 3.6–12.0 h" | §10: the row gives no breakdown; the time of this addendum is projected separately and charged inside R. |
| 13 | §14.2 step 4, test (a) | "segment ids against whole-string ids for every training row, evaluation prompt and R-icl prompt; … 0 required on prompts" | §4.4 extends the check to the combined layouts. |
| 14 | §14.2 step 5 | "generation with beam scores for the training sources, Q, D_cal, D_con and the evaluation panels. **Outputs on evaluation panels are stored and hashed and are not scored before the registered run**" | The ensemble's and the teachers' scores on E_C come from these stored outputs; both teachers generate on E_C (§14). |
| 15 | §20 | "Annotation margins \| … 0.80 for composition"; "Panels E_C, E_open, D_cal, D_con \| 500, 500, 500, 300" | The margin row is reworded (§14); the panel is unchanged. |
| 16 | `CONFIRM.md` §3 item 2 | "The `\n` between the target and the next `English:` in C1 and in R-icl must be its own segment exactly as whole-string tokenization would produce it." | §4.1: that newline is the stored newline segment. |
| 17 | `CONFIRM.md` §7 item 6 | the human lead's list includes "capabilities A, B, combined" | The combined tasks stay in the design. |

Other mentions, none in conflict (the auditor's list): §0 item 1 and §5.2 use "composition" for words into sentences, a different sense, and a COMPOSES line must not be read as support for §0's phrase; §6.1 ("scored on every panel") is the basis for scoring Stage 0 on the combined tasks; §11.3 rows 1 and 2 (integrity, §8); §17 ("Knowledge fusion"). In the review records "C1" and "C2" also name two confirmation findings; those are unrelated.

## 2. Definitions in one place

- **A, B.** Capability A is English→German, B is English→French (a fallback language takes its place as in the ADR).
- **Items.** n = |E_C|. Each E_C item x has a source, German references R_A(x) and French references R_B(x), pooled as §5.2 says.
- **C1 (two sources, two tasks, one sequence).** n items; item j is an ordered pair (s1, s2) of two different E_C sentences. The model answers s1 in the item's first language and then, with its own answer left in the context, answers s2 in the other language.
- **C1 order alternates** **[lead's choice, same cost]**. For even j the first task T1 is A (German) and the second task T2 is B (French), which is §6.4's text. For odd j, T1 is B and T2 is A: `English: {s1}\nFrench:` …, then `\nEnglish: {s2}\nGerman:` …. The alternation is by the parity of j and is the same in both training orders. The alternative not taken is German always first; under it C1's German answer equals the single-task answer by construction and C1 would never test German in second position.
- **C2 (one source, both tasks, one sequence).** n items; item j is one E_C sentence s. The model answers s in German and then, with its own German answer left in the context, answers the same s in French. The source words carry the reads of both tasks, summed, for the whole item. **Limitation, stated:** C2 keeps German then French on every item, so C2 never tests German in second position.
- **Single-task E_C answers.** For every E_C sentence x and each language a, one single-task answer from the prompt P_a(x) under route a (§6).

## 3. C1 pairing and the new seed

- **Seed 220911 — "C1 pairing"** **[lead's choice]**. A partition-side stream like 220902–220910: a fresh generator seeded directly with 220911 draws one uniform permutation σ of the indices 0…n−1 of E_C in stored order. It is drawn once, in the partition step, after E_C is built, and stored with the data manifest (the pair list, with each item's task order, is hashed). No later stage draws it again.
- **Pairs.** Item j (j = 0…n−1) is s1 = E_C[σ(j)], s2 = E_C[σ((j+1) mod n)]. Every E_C sentence is s1 exactly once and s2 exactly once, and s1 ≠ s2 by index. The data-generation step asserts that no two E_C items share a normalized English string and reports the count. If any do, they stay as they are, and s1 ≠ s2 still holds by index.
- **What the alternation gives.** With n even, the sentences σ(even) are answered in German only (first in their own item, second in the item before) and the sentences σ(odd) in French only. So in C1 each language is tested in second position on n/2 items, and the single-task answer of the same sentence in the same language is the first answer of another C1 item. With n odd, items n−1 and 0 are both German-first; the two second-position sets then have (n−1)/2 and (n+1)/2 items and nothing else changes.
- **G9.** 220911 lies in 220001–228999, outside the replicate offsets, 220901–220910, calibration (221001–221999), rehearsal (222001–222999), tests (229001–229999), and the ranges of S0, S1 and P1–P9-II (checked by the auditor). **G9 lists it** (the edits are in §14).
- The alternative not taken: cyclic neighbours in stored order, with no seed. The stored order of E_C comes out of a stratified draw and may be structured by reference count; and the ADR's convention is a listed seed for every draw.
- **Rehearsal and tests.** The rehearsal exercises and times the two-step scoring, never on E_C or any registered panel (the lead's ruling). Its combined scorings reuse the first items of the rehearsal's own single-task scoring set and add no item set. Item i is paired with item i+1 (mod m) in stored order, with the same alternation by parity and no seed. An answer whose source has no reference in that language is generated and timed and not scored. Rehearsal combined scores are timing records, not results. The permutation code is unit-tested with test seeds (229001–229999).

## 4. C1: exact layout

### 4.1 Segments

Segment-level tokenization as §2 and §14.2 step 4: an input is a concatenation of stored segment ids; nothing is encoded in the registered path. Stored pieces, all of which exist already for the single-task prompts:

| Name | Text | Note |
|---|---|---|
| BOS | — | only if the reference default prepends it (§14.2); at the start of a sequence only |
| E | `English:` | template piece |
| S(x) | ` {x}` | the source of sentence x with its leading space, with the stored positions of the last subword of each word |
| NL | `\n` | its own segment |
| M_A, M_B | `German:`, `French:` | task markers |

Single-task prompts (§5.4): P_A(x) = [BOS] E S(x) NL M_A; P_B(x) = [BOS] E S(x) NL M_B.

C1, item (s1, s2) with tasks (T1, T2) = (A, B) for even j and (B, A) for odd j:

- **Step 1 input:** P_T1(s1) = [BOS] E S(s1) NL M_T1. Greedy decoding gives the generated ids g1.
- **Answer ids a1:** the ids of g1 strictly before the stop token (the first generated token whose bytes contain 0x0A, §14.2). If the new-token limit is reached with no stop token, a1 is all of g1.
- **Step 2 input:** [BOS] E S(s1) NL M_T1 · a1 · NL · E S(s2) NL M_T2. Greedy decoding gives g2 and a2 in the same way.
- As a string, even j: `English: {s1}\nGerman:{answer 1}\nEnglish: {s2}\nFrench:` (§6.4's text); odd j: the same with `French:` first and `German:` second. No BOS is inserted before the second `English:`.
- **Step 2 is the continuation of step 1's sequence.** Its first positions are step 1's positions with the same reads. Decoding with the key–value cache kept from step 1 and full recomputation of the step 2 input must give identical tokens (tested, §11). The registered path is the cache continuation. In the rehearsal check (§11 item 9), any token difference against full recomputation is a G4-class defect and stops the work before the freeze. When a1 reached the limit, its last token is fed through the model before the step-2 input.

**The newline after the answer** **[lead's choice]**: the context holds a1 followed by the stored NL segment, as training targets and R-icl prompts are built ("newline separators are their own segments"). The generated stop token itself is not placed in the context. If the stop token carried bytes before its newline, those bytes belong to the answer text that is scored (the text is cut at the first newline, §14.2) and are absent from the context; the count of such items is reported per cell. The alternative keeps the generated ids verbatim, stop token included.

### 4.2 Reads under the oracle route

| Positions | Route | Read |
|---|---|---|
| each word w of S(s1), at its stored last subword | T1 | q = u(T1, w) |
| last token of M_T1 | T1 | q = u(T1, ⟨task⟩) |
| a1 and the NL after it | none | never read (target positions, §5.4) |
| each word w of S(s2) | T2 | q = u(T2, w), at position = stored position in P_T2(s2) − \|BOS\| + \|[BOS] E S(s1) NL M_T1 a1 NL\| |
| last token of M_T2 | T2 | q = u(T2, ⟨task⟩), at the position given by the same formula |
| a2 | none | never read |

Positions are stored positions plus an offset; nothing is re-derived from text. Every E_C sentence is in-vocabulary, so every source word is read. The combined tasks are scored under the oracle route only; there is no keyword-router lane on them (the lead's ruling).

### 4.3 Length

- The new-token limit of §5.4 (the frozen 99.5th percentile) applies to each answer separately.
- No prompt and no context is ever truncated. A first answer that reaches the limit without a stop token stays in the context whole, followed by NL, and is scored as generated, as in single-task scoring **[lead's choice]** (the alternative, cutting or dropping such items, would remove the hardest items). The count of answers that hit the limit is reported per cell, for each of the two answers.
- **Maximum length:** the student's 8,192 positions. With sentences of 3 to 10 words it cannot be approached. The implementation asserts the step 2 input plus the limit is at most 8,192; an item that fails the assertion makes the cell's combined score NOT_EVALUATED (it is not dropped and no denominator is reduced).

### 4.4 Whole-string check (extension of §14.2 test (a))

For every C1 item, with the first stored reference of s1 in the item's first language (tokenized with its leading space) in place of a1, and for every C2 item likewise (§5.1), the segment ids are compared with the whole-string ids: 0 mismatches required at every segment boundary and inside every template piece and source. Mismatches inside the substituted reference are listed, as test (a) lists target mismatches, and require nothing. A required mismatch has the same consequence as a prompt mismatch in test (a). The check uses references as text only; nothing is scored.

## 5. C2: exact layout

### 5.1 Segments **[lead's choice]**

C2, item s:

- **Step 1 input:** P_A(s) = [BOS] E S(s) NL M_A → g1, a1 as in §4.1.
- **Step 2 input:** [BOS] E S(s) NL M_A · a1 · NL · M_B → g2, a2.
- As a string: `English: {s}\nGerman:{answer 1}\nFrench:`. The source appears once.
- Newline, length and continuation rules are those of §4.1 and §4.3 (L-sep's step 2 is the one exception, §7).

This uses only the ADR's template pieces. The alternative is one marker naming both languages with both answers in one generation; it needs a template piece and a way to split the answers that the ADR does not have.

### 5.2 Reads under the oracle route (route "both")

| Positions | Read |
|---|---|
| each word w of S(s) | **two reads, summed:** r = read(u(A, w)) + read(u(B, w)). Each is a read of §3 on its own (its own top-8 over all rows of the arm's store, its own softmax, its own stage gates); the two results are added and the sum is added once to the output of block L. It is not one read with a summed query. |
| last token of M_A | q = u(A, ⟨task⟩) only |
| a1 and the NL after it | none |
| last token of M_B (in the appended part) | q = u(B, ⟨task⟩) only |
| a2 | none |

- The summed word reads are present from step 1 on: the German answer is generated with the French reads already added at the source words. This is forced by "one source, both answers" in one causal sequence, and it is the harder case.
- **Markers** **[lead's choice]**: each marker is read with its own task's code where it stands, as §5.4 defines the marker read; §6.4 sums "the source words" only. The alternative reads both marker codes at M_A.

## 6. References, scores, items

- **Answer score:** chrF-norm of §10.1 against the references of the answer's own language and sentence, with the maximum over references. Answer text is the decoded generation cut at the first newline (§14.2). An empty answer scores 0.
- **Per-answer means (what the rule of §8 uses).** For task K and language a, s_a(X, K) is the mean of the answer-a scores over the items in which a is tested: in C2, all n items; **in C1, only the items where a is the second answer** (about n/2 items for each language). In C1 the first answer equals the single-task answer by construction, so it tests nothing and is not used by the rule.
- **Item score and combined score (§6.4's, kept):** item score = ½·(score of answer 1 + score of answer 2); the combined score of a cell is the mean over all n items; no item is dropped. **Pass** = both normalized answers equal a normalized reference; the pass rate is descriptive only (§10.1).
- **Single-task E_C answers.** For each sentence x and language a: if x is the first sentence of a C1 item whose first task is a, the single-task answer is that first answer (generated from P_a(x) with the single-task reads; recorded once, not generated twice). Otherwise it is generated from P_a(x) under route a in a separate single-answer scoring. With n even that separate scoring is n answers: German for the sentences σ(odd), French for the sentences σ(even). S_A^C and S_B^C are the means over all n sentences; the rule of §8 uses the means over the sentences each answer is tested on.
- **Also recorded per cell, per task:** the first-answer and second-answer means, by language; the bootstrap interval over items (seed 220906, as every cell); the scores on the single-reference subset — for C1 the items where the reference set used for s1 and the reference set used for s2 each have exactly one reference (with German first: |R_A(s1)| = 1 and |R_B(s2)| = 1), for C2 the items where |R_A(s)| = 1 and |R_B(s)| = 1; both generated id sequences of every item, for the recomputation.

## 7. Arms

**Scored on C1 and C2: exactly §6.4's list**, under the oracle route only.

| Arm | Scored? | C1 | C2 |
|---|---|---|---|
| M-append-frozen, M-ii (after Stage 2; both training orders) | yes | one store of 2N rows, one top-8 over all rows per read; §4.2 | §5.2; each of the two reads runs over all 2N rows |
| M-joint | yes (one cell) | as above | as above |
| M-i-separate (assembled from the two ST1 stores of the replicate; one object per replicate) | yes; printed "assembled, not trained" | each segment reads the ST1 store of its own task with that task's codes | read(u(A, w)) from A's store plus read(u(B, w)) from B's store, summed; each marker from its own store |
| L-joint, L-seq (one adapter; L-seq in both training orders) | yes | the adapter is applied at every position of the sequence | the same; route "both" applies the one adapter once, not twice |
| L-sep (the two LoRA-1 adapters of the replicate) | yes; printed "assembled, not trained" | **position-wise** **[lead's choice]**: the LoRA update used at a position is that of the task owning it. T1 owns [BOS] E S(s1) NL M_T1 and a1. T2 owns the NL after a1, E S(s2) NL M_T2 and a2 (§6.4 writes that newline as the start of the second piece). Step 2 continues step 1 | **a switch per answer** **[lead's choice]**: Each answer is generated with its own adapter over the source. Step 1: A's adapter on [BOS] E S(s) NL M_A and a1. Step 2 is computed in full without the step-1 cache: B's adapter on [BOS] E S(s) NL, A's on M_A and a1 (as generated), and B's on NL, M_B and a2. This is the deployment form of two adapters behind a switch. |
| Ensemble (oracle route) | yes; **BY CONSTRUCTION** | each answer is the stored output of the teacher of its language on its sentence; no context reaches a teacher | Teacher A's and Teacher B's stored outputs on s. Its values are printed without any composition word **[lead's choice]** |
| Stage 0 student | yes, once (§6.1: "scored on every panel") | the layouts of §4 and §5 with no read, and the single-task E_C answers | the floor of §8; printed beside every composition line; no composition word **[lead's choice]** |
| M-seq | not scored (§6.4's list; the lead's ruling) | — | — |
| E-table | not scored (§6.4's list; the lead's ruling) | — | — |
| ST1, LoRA-1, MA-gold | no | single-capability cells; not applicable | — |
| Append point, ablations, always-on diagnostic, keyword-router lane | no | the combined tasks are scored on the stage-2 snapshot only, without ablation, under the oracle route | — |

- **L-sep on C1, why position-wise.** It is the adapter form of §5.4's "a route says which task codes a segment is read with", and it is what the store arms do: their first-segment reads stay in place during step 2. Recomputing the whole sequence under the second adapter would let that adapter re-process the first answer, an option no store arm has. That is the alternative not taken.
- **L-sep on C2, why a switch per answer.** The aim is the strongest fair adapter baseline. The alternative not taken is the draft's: both adapters' updates summed on the source positions. That sum acts in all 30 blocks over the whole prefix, while the store sums two reads at one layer on the source words, so it would not be like for like and would handicap a baseline (the auditor's M3).
- **M-ii.** If a cell is CONSOLIDATION-REJECTED, no M-ii combined score exists for that replicate and order; it is NOT_EVALUATED with that reason **[lead's choice]** (the alternative reports the pinned version's scores, which are M-append-frozen's).
- G6 applies: addresses and routes take the prompt segments only. The model's answer changes offsets, never a code; permuting references changes no address and no route.

## 8. The COMPOSES line (strengthened by the human lead)

**The rule the human lead agreed** (in the lead's description to him): for each of the two answers, the arm's gain over the untrained student inside the combined task as a fraction of its single-task gain on the same E_C sentences; each answer needs at least 0.80; COMPOSES only if every training order and every replicate passes; DOES NOT COMPOSE if some answer keeps less than 0.50 in every replicate of some order; otherwise COMPOSITION INCONCLUSIVE; revision 5's raw-score ratio still printed beside it; descriptive, entering no gate, class or TRANSFER label.

**The text of the rule.** It replaces the COMPOSES row of §11.4. It is the auditor's E1, with the changes listed in `CHANGES_FINAL.md`.

> | COMPOSES C1 / C2 (strengthened by the human lead's decision of 2026-11-15, recorded in `HUMAN_DECISIONS_2026-11-15.md`, before any S2 calibration, rehearsal or registered record; it replaces revision 5's raw-score rule) | On the E_C sentences, for task K ∈ {C1, C2}, arm X, order o, replicate r and answer a ∈ {German, French}: s_a(X, K) is the mean chrF-norm of answer a inside K, over the items in which a is tested (C2: all items; C1: the items where a is the second answer); s_a(X, single) is X's single-task score on the same sentences (§6 of the combined-tasks addendum); Stage 0 and the teacher likewise. **Defined** only if s_a(teacher, single) − s_a(Stage 0, single) ≥ 0.30 (§10.1) and X's single-task gap closed on E_C, G_a^C = (s_a(X, single) − s_a(Stage 0, single)) / (s_a(teacher, single) − s_a(Stage 0, single)), is ≥ 0.50 (§11.1 ACQ); otherwise NOT_EVALUATED with the reason **[B(i), confirmed by the human lead]**. **H_a = (s_a(X, K) − m_a) / (s_a(X, single) − s_a(Stage 0, single))**, with m_a = max(s_a(Stage 0, K), s_a(Stage 0, single)) **[B(ii), confirmed by the human lead]**. A cell (o, r) passes if H_a ≥ 0.80 for both answers. First match wins: **NOT_EVALUATED** if any H of any cell of X is undefined, any combined or single-task E_C score of X is undefined (§8 of the addendum), or X is M-ii with a CONSOLIDATION-REJECTED cell; **COMPOSES K** if every cell of every order passes; **DOES NOT COMPOSE K** if, for some order and some answer a, H_a < 0.50 in every replicate of that order; otherwise **COMPOSITION INCONCLUSIVE**. Every line prints n, every H_a per cell, the single-task G_a^C, Stage 0's per-answer combined and single scores (the floor), and beside them revision 5's ratio C̄ / (0.80 · S̄) labelled "revision 5's raw-score rule, replaced by the human lead". The ensemble's and Stage 0's values are printed without any of these words (BY CONSTRUCTION; floor). Every line carries: "descriptive; enters no gate, class or label". In C1 the first answer equals the single-task answer by construction, so each H_a of C1 is computed on the items where a stands second (about n/2 items); C2 never tests German in second position. |

Notes on the text:

- **"Order"** is the training order (both for M-append-frozen, M-ii and L-seq; the one cell or object per replicate for M-joint, L-joint, M-i-separate and L-sep). The position of an answer inside an item is a different thing and is fixed by §2.
- **0.50 for DOES NOT COMPOSE** is the number the human lead agreed ("less than half its gain"). The alternative not taken is the auditor's: 0.70, by the precedent of RET's negative zone (§11.1), which has the same form (a share of the gap kept). The cut does not affect when COMPOSES prints.
- **B(i) and B(ii) are the two tightenings the human lead confirmed** ("I agree with your recommendation"). They come from the auditor's M1 and go beyond the wording he first agreed. B(i) reuses two existing thresholds, each on its own quantity, so that the denominator is at least 0.15; without it a small single-task gain gives a noisy or meaningless ratio, and an arm that does nothing has no defined H. B(ii) takes the harder of Stage 0's two scores as the floor; with Stage 0's combined score alone, an arm degraded by the context would be credited with Stage 0's own drop, and the ensemble could exceed 1.
- **Reasons printed with NOT_EVALUATED:** "teacher gap on E_C below 0.30"; "single-task gap below 0.50" (so that a forgotten capability is not read as a failure to compose); CONSOLIDATION-REJECTED; a recomputation difference beyond tolerance; the length assertion of §4.3.
- **C1 has half the items per answer.** With n = 500, each H_a of C1 rests on about 250 items and is less precise than C2's.
- **Revision 5's ratio:** C̄ is the mean over the replicates of an order of the combined score of §6; S̄ the mean of ½·(S_A^C + S_B^C). It decides nothing.

**Defined scores and integrity.**

- A cell's combined scores are **defined** when its snapshot was scored on all n items with finite scores, the pair list matches its hash in the data manifest, and the recomputation agrees within the tolerance of §13.3. No replicate is left out and no denominator is reduced.
- The combined scorings are registered scores of their cells. A registered cell whose record lacks them, and a recomputation difference that changes a composition line, fall under §11.3 rows 2 and 1 as the ADR already states for every registered score and annotation **[lead's choice]** (the alternative confines a missing combined record to a NOT_EVALUATED line).

## 9. Standing of the composition lines

- **Descriptive.** A composition score or line enters no cell-level gate (§11.1), no mechanism class (§11.2), no row of the study label by its value (§11.3), no other annotation and no cost line. No value of C1 or C2 can produce, withhold or change TRANSFER-POSITIVE or any other label; a missing combined record or a recomputation difference acts on the label through §11.3 rows 1–2, as for every registered score.
- **Headed by the oracle-assisted line.** Every composition line, table, caption, machine-readable record and terminal or log summary carries, directly above it, §11.3's fixed line: "oracle-assisted (word-level addresses supplied by rule); lexical translation of short closed-vocabulary sentences, two capabilities of one kind; frozen English student; teacher-only training material verified by measured-precision filter; not autonomous learned memory." The analysis refuses to write a composition output without it. The human lead's rule stands: "S1 and S2 must not claim autonomous learned-memory success from oracle-assisted results."
- **Second fixed line, on every composition line and every composition table:** "combined tasks: the routes, the order of the answers and the summing of reads are supplied by rule; neither combined task was trained on; descriptive; enters no gate, class or label."
- **Printed with every composition line:** what §8's text lists, the pass rate, and "(n replicates, U = …)".
- COMPOSES says only that, under routes given by rule, each answer of an arm keeps at least 0.80 of its single-task gain over the untrained student on the same sentences, in every replicate and training order. It does not say the model combines capabilities, chooses a task, or fuses knowledge (§17), and it is not evidence for §0's "used compositionally", which is about words in sentences.

## 10. Cost — a projection, not a measurement

Nothing here is measured. The rate is the ADR's (§13.3: 1.6–5.2 min to score E_A and E_B of one trained cell, read as 2,000 single answers, so 0.8–2.6 min per 1,000 answers); second answers are costed at 1.0 to 1.5 single answers. The figures in the table are the auditor's recomputation (`check/cost.py`). The rehearsal replaces all of it.

| Work | Answers | Time |
|---|---|---|
| One arm-cell: C1 (2n), C2 (2n), separate single-task answers (n), n = 500 | 2,500–3,000 equivalents | 2.0–7.8 min |
| Ten arm-cells per replicate (M-append-frozen 2, M-ii 2, M-joint 1, L-joint 1, L-seq 2, M-i-separate 1, L-sep 1) | | 20–78 min |
| **Added scoring per replicate** | | **0.33–1.30 h** |
| Stage 0 student, once per study | 2,500–3,000 | 0.03–0.13 h |
| Ensemble, teachers | no generation | negligible |
| Registered run, four replicates (three) | | 1.37–5.33 h (1.03–4.03 h) |
| Independent recomputation of the same scorings, four (three) | | 1.37–5.33 h (1.03–4.03 h) |
| **Added to R, four replicates (three)** | | **2.73–10.66 h (2.07–8.06 h)** |

- **Charged inside R.** The combined scorings and their recomputation are S2 processes: they are charged (§13.2), they are inside R(n, U) and inside the cap, and the rehearsal measures one combined scoring of each kind of arm for the rung rule.
- **Relation to the ADR's row.** §13.3 already has a row that names "Combined panels" and gives no breakdown. The whole figure above is treated as additional **[lead's choice]** (the reading that counts more time against the cap).
- **The strengthened rule and the alternating order add no scoring.** The answer counts per arm-cell are unchanged.
- **Consequence on the ADR's own model** (the auditor's text):

  > With the addition, R becomes 23.01–65.40 h (rung 1), 17.46–49.52 h (rung 2), 18.74–57.07 h (rung 3) and 14.26–43.27 h (rung 4). At 36 hours only rung 4 fits: for x ≤ 0.06 at P = 3.5 and x < 0.01 at P = 7.0 (rung 2 no longer fits). At the 72-hour ceiling rung 1 fits for x ≤ 0.26 (0.22), rung 2 for x ≤ 0.52 (0.46), rung 3 for x ≤ 0.40 (0.35) and rung 4 for x ≤ 0.68 (0.62); above that the outcome is NOT STARTED: BUDGET. The rung rule, the rungs and the cap are unchanged; the rule is applied to measured rates. The human lead accepted the cost (HUMAN_DECISIONS, 2026-11-15).

| Rung | R (h) | 36 h, P = 3.5 | 36 h, P = 7.0 | 72 h, P = 3.5 | 72 h, P = 7.0 |
|---|---|---|---|---|---|
| 1 (4 × 2,000) | 23.01–65.40 | no | no | x ≤ 0.26 (was 0.40) | x ≤ 0.22 (was 0.35) |
| 2 (3 × 2,000) | 17.46–49.52 | no (was 0.03) | no | x ≤ 0.52 (was 0.72) | x ≤ 0.46 (was 0.65) |
| 3 (4 × 1,000) | 18.74–57.07 | no (was < 0.01) | no | x ≤ 0.40 (was 0.59) | x ≤ 0.35 (was 0.54) |
| 4 (3 × 1,000) | 14.26–43.27 | x ≤ 0.06 (was 0.17) | x < 0.01 (was 0.10) | x ≤ 0.68 (was 0.95) | x ≤ 0.62 (was 0.88) |

- **Effect of the switch per answer for L-sep on C2 (the lead's arithmetic, not checked by the auditor).** Step 2 of each of L-sep's n C2 items recomputes its prefix. Costed at up to one further single answer per item at the slow end and nothing measurable at the fast end, that is at most 500 answers, or 1.3 min, per replicate. The added scoring per replicate becomes 0.33–1.32 h; the registered run 1.37–5.42 h for four replicates (1.03–4.10 h for three); **added to R: 2.73–10.83 h (2.07–8.19 h)**. R becomes 23.01–65.57 h (rung 1), 17.46–49.65 h (rung 2), 18.74–57.24 h (rung 3) and 14.26–43.40 h (rung 4). Every "fits for x ≤" figure in the table is unchanged to two decimals.
- The human lead's acceptance was recorded against "about 3 to 12 hours … for four replicates, unchecked"; 2.73–10.83 h is inside that.

## 11. Tests and checks the implementation owes (synthetic stand-ins first)

1. The pair list: a permutation; every sentence once as s1 and once as s2; s1 ≠ s2; the task order by parity; identical when redrawn from the same seed; G9 accepts 220911 only in the partition step.
2. Step 2 input equals the concatenation of §4.1 / §5.1 for both task orders; read positions equal the formula of §4.2; the answer positions and the newline after them are never read.
3. Cache continuation against full recomputation of step 2: identical tokens, for a store arm, a one-adapter arm and L-sep on C1 (position-wise). L-sep on C2: step 2 is the full computation of §7 and is checked against its definition on a hand case.
4. C2 word read equals the sum of two separate reads; it differs from one read with a summed query on a hand case.
5. Every first answer of C1 is bit-identical to a single-task scoring of the same sentence in the same language.
6. The whole-string check of §4.4 in the data-generation step; the assertion and count of §3 on normalized strings.
7. Ensemble: each per-answer mean inside C1 and C2 equals its single-task mean on the same sentences.
8. Report: every composition line under both fixed lines; refusal without them; NOT_EVALUATED with its reason for a rejected M-ii cell, a missing replicate, a teacher gap below 0.30 and a single-task gap below 0.50; no composition word for the ensemble or Stage 0; the H values of the ensemble and Stage 0; the reason line for an undefined H; revision 5's ratio labelled as replaced.
9. In the rehearsal: check 3 on 20 items at real size; one combined scoring of each kind of arm, timed, on the first items of the rehearsal's own single-task scoring set.
10. The rule of §8 on synthetic records: a do-nothing arm, a first-answer-only arm and a copy-the-first-answer arm do not print COMPOSES; the ensemble prints H = 1 when Stage 0's combined score does not exceed its single-task score, and never more than 1.

For reference only: the provisional layout in the implementation worktree (`studies/p10s2/evaluate.py`, `score_combined`) matches §4.1–§4.2 for German-first items and §5. It differs in the pairing, the alternating order, the rule, L-sep, the single-task E_C answers and the Stage 0 row.

## 12. The lead's choices in this addendum

| # | Point | Choice | Alternative not taken | § |
|---|---|---|---|---|
| 1 | C1 answer order | alternates by the parity of j: German first for even j, French first for odd j; the same in both training orders | German always first (§6.4's text on every item) | 2 |
| 2 | C2 answer order | German then French on every item; limitation stated | alternating C2, or both orders (more scoring) | 2 |
| 3 | C1 pairing | permutation σ from new listed seed 220911; item j = (σ(j), σ(j+1)) | cyclic neighbours in stored order, no seed | 3 |
| 4 | Newline after answer 1 | generated ids before the stop token, then the stored NL segment | generated ids verbatim with the stop token | 4.1 |
| 5 | Answer at the token limit | kept whole in the context and scored | cut or dropped | 4.3 |
| 6 | C2 layout | `English: {s}\nGerman:` … `\nFrench:` …, own first answer kept | one marker naming both languages | 5.1 |
| 7 | C2 markers | each marker read with its own task code where it stands | both marker codes at the first marker | 5.2 |
| 8 | L-sep on C1 | position-wise adapters, step 2 continues step 1 | recompute the whole sequence under the second adapter | 7 |
| 9 | L-sep on C2 | a switch per answer; step 2 recomputed with the source under the second task's adapter | both adapters' updates summed on the source positions (the draft) | 7 |
| 10 | Ensemble, Stage 0 | scored; values printed; no composition word | a composition line for them | 7 |
| 11 | Rejected M-ii cell | NOT_EVALUATED | the pinned version's scores | 7 |
| 12 | Single-task scores | on the E_C sentences each answer is tested on | E_A and E_B scores | 6, 8 |
| 13 | DOES NOT COMPOSE cut | 0.50, as the human lead agreed | 0.70, RET's negative zone (the auditor) | 8 |
| 14 | Missing combined record | falls under §11.3 row 2 like any registered score | NOT_EVALUATED line only | 8 |
| 15 | Cost | counted wholly in addition to the existing row | netted against that row | 10 |
| B(i) | When H is defined | teacher gap on E_C ≥ 0.30 and single-task gap closed on E_C ≥ 0.50 — **confirmed by the human lead** | no condition beyond a single-task gain greater than 0 | 8 |
| B(ii) | Floor in the numerator | the larger of Stage 0's combined and single-task scores — **confirmed by the human lead** | Stage 0's combined score alone | 8 |

Not choices of the lead: the strengthened rule itself, its 0.80 and 0.50, and B(i) and B(ii) (the human lead); no keyword-router lane, M-seq and E-table not scored, rehearsal never on a registered panel (the lead's rulings on the draft, applied throughout).

## 13. Open points

The draft's five open points are answered: the rule is strengthened (the human lead); M-seq and E-table are not scored and the router lane is struck (the lead's rulings); the cost is accepted (the human lead) and restated (§10); the rehearsal reuses its own single-task items (§3).

Still open:

1. **The lead's adoption** of this addendum is pending. The text after the auditor's edits, with rulings C and D, has not been re-read by the auditor.

## 14. Edits to the ADR text when the addendum is adopted

- **§6.4, combined tasks:** add "as defined in the combined-tasks addendum; C1 alternates the order of the two tasks by item".
- **§9:** change "220902–220910 are drawn once" to "220902–220911 are drawn once". Add to "Further listed seeds": "220911, the C1 pairing (a permutation of E_C, drawn once after E_C is built; the combined-tasks addendum)". §22's historical "Not applied" item 1 is not edited.
- **G9 (§12.3):** change "220901–220910, of which 220902–220910" to "220901–220911, of which 220902–220911".
- **§11.4:** replace the COMPOSES row with the row of §8.
- **§14.2 step 5:** state that both teachers generate on every E_C sentence.
- **§20:** in the seed row, change "220901–220910" to "220901–220911". In the "Annotation margins" row, change "0.80 for composition" to "0.80 of the per-answer gap above Stage 0 for composition (strengthened by the human lead); single-task G on E_C ≥ 0.50 and teacher gap ≥ 0.30 to be defined (confirmed by the human lead); 0.50 for DOES NOT COMPOSE".
- **Header and §18:** one line recording the human lead's decisions with the three quotations above and their source.

## Adoption record — 2026-11-15 (UTC)

- **The human lead approved this addendum,** verbatim: "I've read P10-S2 cobined task done please continue with simulations, consider it as approved" (full record of this and the three earlier quotations: `docs/reviews/p10-design-2026-11-15/HUMAN_DECISIONS_2026-11-15.md`).
- **Adopted by the lead (Claude Fable 5.2).** From this commit the addendum is part of ADR-0022's specification. Where it and ADR-0022 revision 5 differ on the combined tasks C1 and C2, on §6.4's scoring of them or on the COMPOSES rule of §11.4, the addendum governs. ADR-0022's own text is not rewritten; the edits listed in this addendum's §14 are applied by reference.
- **What was and was not independently checked.** Opus 5.5 checked the draft and the strengthened rule (`docs/reviews/p10-design-2026-11-15/adr-0022-review/c1c2-addendum/CHECK_C1_C2.md`: READY SUBJECT TO edits, no leakage found). The final text applies those edits and two later rulings of the lead (C1 alternates the order of the two languages; the adapter baseline on C2 switches adapters per answer); the passages those two rulings changed have not been re-read by a reviewer, and the implementation audit before the freeze reads them.
- No S2 calibration, rehearsal or registered record existed when the rule was strengthened or when this addendum was adopted. Astra review: NOT_PERFORMED.

