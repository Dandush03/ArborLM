# ADR-0022 addendum — the combined tasks C1 and C2 (draft)

- **Status: DRAFT by the lead (Claude Fable 5.2). Not approved, not audited, nothing implemented or run under it. SPEC: PENDING ASTRA REVIEW. Astra review: NOT_PERFORMED.**
- **Date:** 2026-11-15 (UTC). Applies to ADR-0022 revision 5.
- **Why.** The implementation stopped at `PendingLeadReview`: the ADR "does not say how C1 pairs two sources or how C2 lays out its prompt", and an adapter applied to a sequence of two tasks was reported NOT_EVALUATED for the same reason. This addendum fixes everything the lines COMPOSES C1 / C2 need, before any calibration.
- **What it changes.** It adds definitions to §6.4, one listed seed to §9 and G9, a reading of the denominator of §11.4's COMPOSES rule, checks to §14.2 test (a) and to the rehearsal, and a cost projection to §13.3. **It changes no threshold, arm, model, data source, replicate count, rung or cap.** The 0.80 margin, the 500-item E_C panel and the list of arms scored on the combined tasks are the ADR's.
- **Rule for open points** (the ADR's, header of revision 5): an existing convention of the ADR where one exists, otherwise the option that is harder for a positive composition line. Each is marked **[lead's choice]** with the alternative, and listed in §12. Points that need a scientific decision are in §13 and are not decided here.
- Oracle qualification, unchanged: every address and every route below is supplied by rule. "S1 and S2 must not claim autonomous learned-memory success from oracle-assisted results." (the human lead; ADR-0022 header, §11.3, §18).

## 1. Every existing mention, and consistency

| # | Where | Text | How this addendum is consistent |
|---|---|---|---|
| 1 | §5.2 panel table | "E_C \| evaluation \| 500 *(lead's choice)* \| held-out sentences with both; basis of the combined tasks" | Both tasks use every E_C sentence and no other sentence (§2). |
| 2 | §5.2 sufficiency | "If E_A or E_B cannot reach 500 items, E_C 250, or an accepted pool 8,000, the study stops" | n = \|E_C\|, between 250 and 500; nothing is added to the sufficiency rule. |
| 3 | §5.4 Routes | "A route says which task codes a segment is read with: none, A, B, or both (combined task C2)." | C1 gives each of its two segments one route (A, then B). C2 gives its source route "both" (§4, §5). |
| 4 | §6.4 | "**Combined tasks** (never trained on), scored for M-append-frozen, M-ii, M-joint, L-joint, L-seq, M-i-separate, L-sep and the ensemble" | The scored set is exactly this list (§7). No training stream and no router stream contains a two-answer sequence. |
| 5 | §6.4 | "C1, two sources: `English: {s1}\nGerman:` …, then after the model's own answer `\nEnglish: {s2}\nFrench:` …" | §4 is this layout, segment by segment; the model's own answer stays in the context. |
| 6 | §6.4 | "C2, one source, both answers: the source words are read with both tasks' codes and the reads are summed." | §5: two reads per source word, one per task code, summed. |
| 7 | §6.4 | "Score: mean chrF of the two answers; an item passes if both match a reference exactly." | §6. |
| 8 | §9 | "The partition seed 220901 draws in this order: … E_A, E_B, E_C, E_open." | E_C is built as before; the new seed 220911 is used after it (§3). |
| 9 | §11.3 | "The words … COMPOSES … and every other class, mechanism, router, composition or cost line, are therefore printed only directly under that line" | §9. |
| 10 | §11.4 | "COMPOSES C1 / C2 \| mean over replicates of the combined score ≥ 0.80 × the mean of the arm's two single-task scores" | §8 keeps the rule and the 0.80 and says which single-task scores. |
| 11 | §11.4 | "Every annotation, the ROUTER and COMPOSES lines included, is printed under the oracle-assisted line of §11.3, also when it appears in a table of its own." | §9. |
| 12 | §13.3 table | "Combined panels, append point, ablations on 300 items, GEN and router lane, diagnostic, retrieval \| CPU \| — \| 0.9–3.0 h \| 3.6–12.0 h" | §10: the row gives no breakdown; the time of this addendum is projected separately and charged inside R. |
| 13 | §14.2 step 4, test (a) | "segment ids against whole-string ids for every training row, evaluation prompt and R-icl prompt; … 0 required on prompts" | §4.4 extends the check to the combined layouts. |
| 14 | §14.2 step 5 | "generation with beam scores for the training sources, Q, D_cal, D_con and the evaluation panels. **Outputs on evaluation panels are stored and hashed and are not scored before the registered run**" | The ensemble's combined scores come from these stored outputs on E_C (§7). |
| 15 | §20 | "Annotation margins \| … 0.80 for composition"; "Panels E_C, E_open, D_cal, D_con \| 500, 500, 500, 300" | Unchanged. |
| 16 | `CONFIRM.md` §3 item 2 | "The `\n` between the target and the next `English:` in C1 and in R-icl must be its own segment exactly as whole-string tokenization would produce it." | §4.1: that newline is the stored newline segment. |
| 17 | `CONFIRM.md` §7 item 6 | the human lead's list includes "capabilities A, B, combined" | The combined tasks stay in the design. |

`REVIEW.md`, `RECHECK_REV4.md` and `CONFIRM_REV5.md` say nothing else about composition beyond the oracle-line coverage (RECHECK §5 item 3, CONFIRM_REV5 on §11.3–§11.4). In the review records "C1" and "C2" also name two confirmation findings (G5; control limits); those are unrelated.

## 2. Definitions in one place

- **A, B.** Capability A is English→German, B is English→French (the fallback language takes B's or A's place as in the ADR). In both combined tasks the A answer comes first and the B answer second, **in both training orders** **[lead's choice]** (§6.4's C1 text is written German first; C2 follows it). The alternative is the first-trained capability first, which would make the layout depend on the order.
- **Items.** n = |E_C|. Each E_C item x has a source, a set of German references R_A(x) and a set of French references R_B(x), pooled as §5.2 says.
- **C1 (two sources, two tasks, one sequence).** n items; item j is an ordered pair (s1, s2) of two different E_C sentences. The model answers s1 in German, and then, with its own German answer left in the context, answers s2 in French.
- **C2 (one source, both tasks, one sequence).** n items; item j is one E_C sentence s. The model answers s in German and then, with its own German answer left in the context, answers the same s in French. The source words carry the reads of both tasks, summed, for the whole item.
- **Single-task E_C scores** (needed by §8): S_A^C is the arm's score on the single-task A prompt of every E_C sentence; S_B^C likewise for B.

## 3. C1 pairing and the new seed

- **Seed 220911 — "C1 pairing"** **[lead's choice]**. A partition-side stream like 220902–220910: a fresh generator seeded directly with 220911 draws one uniform permutation σ of the indices 0…n−1 of E_C in stored order. It is drawn once, in the partition step, after E_C is built, and stored with the data manifest (the pair list is hashed). No later stage draws it again.
- **Pairs.** Item j (j = 0…n−1) is s1 = E_C[σ(j)], s2 = E_C[σ((j+1) mod n)]. So every E_C sentence is s1 exactly once and s2 exactly once, s1 ≠ s2 in every item (n ≥ 250), and C1 covers the same German and the same French references as C2 and as the single-task E_C scores. Two E_C sentences never share a normalized English string, because such sentences are one identity group with pooled references (§5.2).
- **G9.** 220911 lies in 220001–228999, outside the replicate offsets (bases + 0…10), 220901–220910, calibration (221001–221999), rehearsal (222001–222999) and tests (229001–229999). **G9 lists it:** in §9 and G9, "220901–220910" becomes "220901–220911" and "220902–220910 are used in the data-generation and partition steps only" becomes "220902–220911". §20's seed row gains it.
- The alternative not taken: cyclic neighbours in stored order (item i with item i+1), which needs no seed. The stored order of E_C comes out of a stratified draw and may be structured by reference count, so neighbours would not be an arbitrary pairing; and the ADR's convention is a listed seed for every draw.
- **Rehearsal and tests.** E_C is not scored before the registered run (§12.1). The rehearsal exercises and times the two-step scoring on the items its single-task scorings use, never on E_C, pairing item i with item i+1 (mod m) in stored order, with no seed; an answer whose source has no reference in that language is generated and timed and not scored. Rehearsal combined scores are timing records, not results. The permutation code is unit-tested with test seeds (229001–229999).

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

C1, item (s1, s2):

- **Step 1 input:** P_A(s1) = [BOS] E S(s1) NL M_A. Greedy decoding gives the generated ids g1.
- **Answer ids a1:** the ids of g1 strictly before the stop token (the first generated token whose bytes contain 0x0A, §14.2). If the new-token limit is reached with no stop token, a1 is all of g1.
- **Step 2 input:** [BOS] E S(s1) NL M_A · a1 · NL · E S(s2) NL M_B. Greedy decoding gives g2 and a2 in the same way.
- As a string: `English: {s1}\nGerman:{answer 1}\nEnglish: {s2}\nFrench:` — §6.4's text. No BOS is inserted before the second `English:`.
- **Step 2 is the continuation of step 1's sequence.** Its first positions are step 1's positions with the same reads. Decoding with the key–value cache kept from step 1 and full recomputation of the step 2 input must give identical tokens (tested, §11).

**The newline after the answer** **[lead's choice]**: the context holds a1 followed by the stored NL segment, as training targets and R-icl prompts are built ("newline separators are their own segments"). The generated stop token itself is not placed in the context. If the stop token carried bytes before its newline, those bytes belong to the answer text that is scored (the text is cut at the first newline, §14.2) and are absent from the context; the count of such items is reported per cell. The alternative keeps the generated ids verbatim, stop token included, which would put merged newline tokens the student never saw at that place in training into the context.

### 4.2 Reads under the oracle route

| Positions | Route | Read |
|---|---|---|
| each word w of S(s1), at its stored last subword | A | q = u(A, w) |
| last token of M_A | A | q = u(A, ⟨task⟩) |
| a1 and the NL after it | none | never read (target positions, §5.4) |
| each word w of S(s2), at its stored position shifted by the length of what precedes the second E, less BOS | B | q = u(B, w) |
| last token of M_B | B | q = u(B, ⟨task⟩) |
| a2 | none | never read |

Positions are stored positions plus an offset; nothing is re-derived from text. Every E_C sentence is in-vocabulary, so every source word is read.

### 4.3 Length

- The new-token limit of §5.4 (the frozen 99.5th percentile) applies to each answer separately.
- No prompt and no context is ever truncated. A first answer that reaches the limit without a stop token stays in the context whole, followed by NL, and is scored as generated, as in single-task scoring **[lead's choice]** (the alternative, cutting or dropping such items, would remove the hardest items). The count of answers that hit the limit is reported per cell, for each of the two answers.
- **Maximum length:** the student's 8,192 positions. With sentences of 3 to 10 words it cannot be approached. The implementation asserts the step 2 input plus the limit is at most 8,192; an item that fails the assertion makes the cell's combined score NOT_EVALUATED (it is not dropped and no denominator is reduced).

### 4.4 Whole-string check (extension of §14.2 test (a))

For every C1 item, with the first stored German reference of s1 (tokenized with its leading space) in place of a1, and for every C2 item likewise (§5.1), the segment ids must equal the whole-string ids: 0 mismatches required, with the same consequence as a prompt mismatch in test (a). The check uses references as text only; nothing is scored.

## 5. C2: exact layout

### 5.1 Segments **[lead's choice]**

C2, item s:

- **Step 1 input:** P_A(s) = [BOS] E S(s) NL M_A → g1, a1 as in §4.1.
- **Step 2 input:** [BOS] E S(s) NL M_A · a1 · NL · M_B → g2, a2.
- As a string: `English: {s}\nGerman:{answer 1}\nFrench:`. The source appears once.
- Newline, length and continuation rules are those of §4.1 and §4.3.

This uses only the ADR's template pieces and C1's answer order. The alternative is one marker naming both languages (for example `German and French:`) with both answers in one generation; it needs a template piece and a way to split the answers that the ADR does not have.

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

## 6. References, score, items

- **Item score** = ½·[chrF(answer 1, R_A) + chrF(answer 2, R_B)], chrF-norm of §10.1 with the maximum over references. In C1, R_A is R_A(s1) and R_B is R_B(s2); in C2 both are of s. Answer text is the decoded generation cut at the first newline (§14.2).
- **Combined score of a cell** = the mean over all n items. Every item yields a score: an empty answer scores 0 (§10.1), and no item is dropped.
- **Pass** = both normalized answers equal a normalized reference. The pass rate is descriptive only, like every exact-match figure (§10.1).
- **Also recorded per cell, per task:** the mean of the first answers and the mean of the second answers separately; the bootstrap interval over items (seed 220906, as every cell); the score on items whose German and French reference sets both have exactly one reference (§5.2's rule for every score); both generated id sequences of every item, for the recomputation.
- **Single-task E_C scores.** S_A^C: the first answer of C1 is generated from P_A(s1) with the single-task reads, so the set of C1 first answers is the single-task A scoring of E_C; it is recorded once and not generated twice. S_B^C: P_B(x) under route B for every E_C sentence, a separate single-answer scoring.

## 7. Arms

**Scored on C1 and C2: exactly §6.4's list.** One rule per kind of arm; the rule exists for every kind so that nothing is undefined.

| Arm | Scored? | C1 | C2 |
|---|---|---|---|
| M-append-frozen, M-ii (after Stage 2; both orders) | yes | one store of 2N rows, one top-8 over all rows per read; §4.2 | §5.2; each of the two reads runs over all 2N rows |
| M-joint | yes (one cell) | as above | as above |
| M-i-separate (assembled from the two ST1 stores of the replicate; one object per replicate) | yes; printed "assembled, not trained" | segment 1 reads capability A's ST1 store with A codes; segment 2 reads capability B's ST1 store with B codes | read(u(A, w)) from A's store plus read(u(B, w)) from B's store, summed; each marker from its own store |
| L-joint, L-seq (one adapter; L-seq in both orders) | yes | the adapter is applied at every position of the sequence | the same; route "both" applies the one adapter once, not twice |
| L-sep (the two LoRA-1 adapters of the replicate) | yes; printed "assembled, not trained" | **position-wise** **[lead's choice]**: the LoRA update used at a position is that of the task owning the position. Task A owns [BOS] E S(s1) NL M_A and a1. Task B owns the NL after a1, E S(s2) NL M_B and a2 (§6.4 writes that newline as the start of the second piece). Positions already computed are not recomputed: step 2 continues step 1 | **[lead's choice]**: [BOS] E S(s) NL carry the sum of both adapters' updates (the adapter form of "read with both tasks' codes and … summed"); M_A and a1 carry A's; the NL after a1, M_B and a2 carry B's |
| Ensemble (oracle route) | yes; **BY CONSTRUCTION** | answer 1 is Teacher A's stored output on s1, answer 2 is Teacher B's stored output on s2; no context reaches a teacher | Teacher A's and Teacher B's stored outputs on s. C1, C2 and the single-task E_C mean are equal by construction; the ratio is printed as "BY CONSTRUCTION" and the word COMPOSES is not printed for it **[lead's choice]** |
| Stage 0 student | yes, once (§6.1: "scored on every panel") | the layouts of §4 and §5 with no read | printed beside every composition line as the floor; receives no COMPOSES word **[lead's choice]** |
| M-seq | no (§6.4 does not list it) | would follow the one-store rule | open, §13 |
| E-table (one table per capability) | no (§6.4 does not list it) | would add e(A, w) on segment 1 and e(B, w) on segment 2, each times its gate | would add both, summed; open, §13 |
| ST1, LoRA-1, MA-gold | no | single-capability cells; not applicable | — |
| Append point, ablations, always-on diagnostic | no | the combined tasks are scored on the stage-2 snapshot only, without ablation | — |

- **L-sep, the alternative not taken:** switch adapters for the whole sequence at step 2 (recompute every position under B's adapter). The position-wise rule is the adapter form of §5.4's "a route says which task codes a segment is read with", and it is what the store arms do: their segment-1 reads stay in place during step 2. For L-sep on C2 the alternatives are A's adapter alone on the source, or NOT_EVALUATED.
- **M-ii.** If a cell is CONSOLIDATION-REJECTED, no M-ii combined score exists for that replicate and order; it is NOT_EVALUATED with that reason **[lead's choice]** (the alternative reports the pinned version's scores, which are M-append-frozen's).
- **Keyword-router lane** **[lead's choice]**. The registered composition lines use the oracle route. In addition, for M-append-frozen only (the arm of the ROUTER annotation), C1 is scored with the stage-2 router of the replicate deciding each segment: decision 1 at the last token of M_A from a memory-free pass over the step 1 input; decision 2 at the last token of M_B from a memory-free pass over the step 2 input (which holds the answer generated under decision 1). A segment routed to task t has its words and its marker read with t's codes; routed to "none", it is not read. Scores are against the German references for answer 1 and the French for answer 2. The line is printed as "C1 under the keyword router (descriptive)", with the two decision accuracies, never with the word COMPOSES. **C2 under the keyword router is NOT_EVALUATED by definition:** the router returns one of A, B, none and has no route "both"; the report says so. The alternative is no router lane for the combined tasks at all (§13, item 3).
- G6 applies: addresses and routes take the prompt segments only. The model's answer changes offsets, never a code; permuting references changes no address and no route.

## 8. The COMPOSES line

For task K ∈ {C1, C2}, arm X and each order o of X (both orders for M-append-frozen, M-ii and L-seq; the single cell or object for M-joint, L-joint, M-i-separate, L-sep), over the replicates r of the design:

- C̄ = mean over r of the combined score of K;
- S̄ = mean over r of ½·[S_A^C + S_B^C] of the same cell;
- the rule of §11.4, unchanged: C̄ ≥ 0.80 × S̄. The ratio C̄/S̄ is printed.

**Which single-task scores** **[lead's choice]**: the arm's single-task scores on the E_C sentences themselves, so that both sides of the rule use the same sentences and references. That is the ADR's convention for comparisons ("Control G values use the teacher and Stage 0 scores of the same 300-item subsample", §7; "same panel", §10.1). The alternative is the arm's E_A and E_B scores, which costs no extra scoring and mixes composition with any difference in difficulty between panels.

**Per order** **[lead's choice]**: the arm's line reads COMPOSES K only if the rule holds in every order of the arm; DOES NOT COMPOSE K if it is evaluated in every order and fails in one; otherwise NOT_EVALUATED. The alternative pools the orders into one mean.

**Defined result against NOT_EVALUATED.**

- A cell's combined score is **defined** when its snapshot was scored on all n items with finite item scores, the pair list matches its hash in the data manifest, and the recomputation agrees within the tolerance of §13.3.
- A composition line is **NOT_EVALUATED**, with its reason printed, when for any replicate of the order a combined score or a single-task E_C score is not defined (CONSOLIDATION-REJECTED for M-ii; a recomputation difference beyond tolerance; the length assertion of §4.3), or when S̄ = 0. No replicate is left out of a mean and no denominator is reduced.
- The combined scorings are registered scores of their cells. A registered cell whose record lacks them, and a recomputation difference that changes a composition line, fall under §11.3 rows 2 and 1 as the ADR already states for every registered score and annotation **[lead's choice]** (the alternative confines a missing combined record to a NOT_EVALUATED line). This is the integrity rule, not the composition result, acting on the label.

## 9. Standing of the composition lines

- **Descriptive.** A composition score or line enters no cell-level gate (§11.1), no mechanism class (§11.2), no row of the study label by its value (§11.3), no other annotation and no cost line. No value of C1 or C2 can produce, withhold or change TRANSFER-POSITIVE or any other label.
- **Headed by the oracle-assisted line.** Every composition line, table, caption, machine-readable record and terminal or log summary carries, directly above it, §11.3's fixed line: "oracle-assisted (word-level addresses supplied by rule); lexical translation of short closed-vocabulary sentences, two capabilities of one kind; frozen English student; teacher-only training material verified by measured-precision filter; not autonomous learned memory." The analysis refuses to write a composition output without it, as for every other class and annotation. The human lead's rule stands: "S1 and S2 must not claim autonomous learned-memory success from oracle-assisted results."
- **Second fixed line, under the first, on every composition table:** "combined tasks: the routes, the order of the answers and the summing of reads are supplied by rule; neither combined task was trained on; descriptive; enters no gate, class or label."
- **Printed with every composition line:** n; C̄; the first-answer and second-answer means; S̄_A and S̄_B on E_C; the ratio; the pass rate; the Stage 0 student's values; "(n replicates, U = …)".
- COMPOSES says only that an arm's two-answer score is at least 0.80 of its single-task score on the same sentences under routes given by rule. It does not say the model combines capabilities, chooses a task, or fuses knowledge (§17).

## 10. Cost — a projection, not a measurement

Nothing here is measured. The rate is the ADR's (§13.3: 1.6–5.2 min to score E_A and E_B of one trained cell, read as 2,000 single answers, so 0.8–2.6 min per 1,000 answers); second answers are costed at 1.0 to 1.5 single answers because of the longer context. The arithmetic is the drafter's and has not been checked by the auditor. The rehearsal replaces all of it.

| Work | Answers | Time |
|---|---|---|
| One arm-cell, oracle route: C1 (2n), C2 (2n), S_B^C (n), n = 500 | 2,500–3,000 equivalents | 2.0–7.8 min |
| Ten arm-cells per replicate (M-append-frozen 2, M-ii 2, M-joint 1, L-joint 1, L-seq 2, M-i-separate 1, L-sep 1) | | 20–78 min |
| Keyword-router C1, two M-append-frozen cells | 1,100–1,450 each | 1.8–7.5 min |
| **Added scoring per replicate** | | **0.36–1.43 h** |
| Stage 0 student, once per study | 2,500–3,000 | 0.03–0.13 h |
| Ensemble | no generation | negligible |
| Registered run, four replicates (three) | | 1.49–5.83 h (1.12–4.41 h) |
| Independent recomputation of the same scorings, four (three) | | 1.49–5.83 h (1.12–4.41 h) |
| **Added to R, four replicates (three)** | | **2.97–11.66 h (2.25–8.81 h)** |

- **Charged inside R.** The combined scorings and their recomputation are S2 processes: they are charged (§13.2), they are inside R(n, U) and inside the cap, and the rehearsal measures one combined scoring of each kind of arm for the rung rule.
- **Relation to the ADR's row.** §13.3 already has a row that names "Combined panels" (0.9–3.0 h per replicate, with five other items) and gives no breakdown. This addendum does not assume any part of that row was the combined panels: the whole figure above is treated as additional **[lead's choice]** (the reading that counts more time against the cap).
- **Consequence on the ADR's own model, stated plainly.** With the upper treatment, rung 1's R becomes 23.25–66.40 h (from 20.28–54.74), and at a 72-hour cap it fits for x ≤ 0.25 at P = 3.5 and x ≤ 0.21 at P = 7.0 (from 0.40 and 0.35). Rung 2 becomes 17.64–50.27 h and fits at 72 hours for x ≤ 0.50 (0.45); rung 4 becomes 14.44–44.02 h and fits at 72 hours for x ≤ 0.66 (0.61), and at 36 hours only for x ≤ 0.06 at P = 3.5. The rung rule, the rungs and the cap are unchanged; the rule is applied to measured rates.

## 11. Tests and checks the implementation owes (synthetic stand-ins first)

1. The pair list: a permutation; every sentence once as s1 and once as s2; s1 ≠ s2; identical when redrawn from the same seed; G9 accepts 220911 only in the partition step.
2. Step 2 input equals the concatenation of §4.1 / §5.1; read positions equal stored positions plus the offset; the answer positions and the newline after them are never read.
3. Cache continuation against full recomputation of step 2: identical tokens, for a store arm, a one-adapter arm and L-sep (position-wise).
4. C2 word read equals the sum of two separate reads; it differs from one read with a summed query on a hand case.
5. The first answers of C1 are bit-identical to a single-task A scoring of the same sentences.
6. The whole-string check of §4.4 in the data-generation step.
7. Ensemble: C1 mean = C2 mean = single-task E_C mean.
8. Report: every composition line under both fixed lines; refusal without them; NOT_EVALUATED with a reason for a rejected M-ii cell, a missing replicate and S̄ = 0; no COMPOSES word for the ensemble, Stage 0 or the router line.
9. In the rehearsal: check 3 on 20 items at real size; one combined scoring of each kind of arm, timed.

For reference only: the provisional layout in the implementation worktree (`studies/p10s2/evaluate.py`, `score_combined`) already matches §4.1, §4.2, §5.1 and §5.2. It differs in the pairing (cyclic neighbours), the denominator (E_A and E_B), pooling over orders, L-sep (NOT_EVALUATED) and the absence of S_B^C, the Stage 0 row and the router line.

## 12. The lead's choices in this addendum

| # | Point | Choice | Alternative not taken | § |
|---|---|---|---|---|
| 1 | Answer order | A (German) first in both training orders, in C1 and C2 | first-trained capability first | 2 |
| 2 | C1 pairing | permutation σ from new listed seed 220911; item j = (σ(j), σ(j+1)) | cyclic neighbours in stored order, no seed | 3 |
| 3 | Newline after answer 1 | generated ids before the stop token, then the stored NL segment | generated ids verbatim with the stop token | 4.1 |
| 4 | Answer at the token limit | kept whole in the context and scored | cut or dropped | 4.3 |
| 5 | C2 layout | `English: {s}\nGerman:` … `\nFrench:` …, own first answer kept | one marker naming both languages | 5.1 |
| 6 | C2 markers | each marker read with its own task code where it stands | both marker codes at the first marker | 5.2 |
| 7 | L-sep on C1 | position-wise adapters, step 2 continues step 1 | recompute the whole sequence under the second adapter | 7 |
| 8 | L-sep on C2 | both adapters' updates summed on the source positions | first adapter alone there, or NOT_EVALUATED | 7 |
| 9 | Ensemble, Stage 0 | scored; no COMPOSES word (BY CONSTRUCTION; floor) | a COMPOSES line for them | 7 |
| 10 | Rejected M-ii cell | NOT_EVALUATED | the pinned version's scores | 7 |
| 11 | Keyword-router lane | C1 for M-append-frozen only, descriptive; C2 NOT_EVALUATED by definition | no router lane on the combined tasks | 7 |
| 12 | Denominator of COMPOSES | single-task scores on the E_C sentences | E_A and E_B scores | 8 |
| 13 | Orders | rule per order; COMPOSES only if every order passes | orders pooled in one mean | 8 |
| 14 | Missing combined record | falls under §11.3 row 2 like any registered score | NOT_EVALUATED line only | 8 |
| 15 | Cost | counted wholly in addition to the existing row | netted against that row | 10 |

## 13. Open for the lead (not decided here)

1. **The rule is weak at both ends, and this addendum may not change it.** (a) It compares raw chrF, so an arm that does nothing can satisfy it; the Stage 0 row is printed as the floor, but the word could still print for a weak arm. (b) In C1 the first answer is the single-task answer by construction, so with equal single-task scores the 0.80 rule asks only that the second answer keep about 0.60 of its single-task score (second-answer mean ≥ 0.8·S_B^C − 0.2·S_A^C). Whether to accept the line as descriptive on these terms, or to amend §11.4 (a stricter rule, or a rule on the second answer), is a decision on a registered rule.
2. **M-seq and E-table.** §6.4 does not list them; the request for this addendum names them. §7 defines how they would be scored. Adding them adds three arm-objects per replicate (about 6–23 min per replicate, twice with the recomputation) and changes the scored set of §6.4. E-table's combined score would bear on how EQUIVALENT TO A WORD TABLE is read.
3. **Cost against the cap.** On the projection the addition is material (§10). Two parts are this draft's and can be struck without touching the layouts: the S_B^C pass (about 4–13 min per replicate; the denominator then falls back to E_A and E_B) and the keyword-router C1 line (about 2–8 min per replicate). Whether to keep them, and whether the upper treatment of the existing row stands, is for the lead.
4. **Rehearsal items.** The ADR does not say which items the rehearsal's "one scoring of each kind" uses, for any scoring. §3 follows whatever the single-task rehearsal scorings use; if that is D_cal, its "calibration and pilot only" wording in §5.2 needs the lead's reading.
5. **Approval path.** This addendum adds a listed seed, a scoring pass and a reading of §11.4. It needs the lead's recorded approval, and the lead should say whether the auditor reads it before the implementer codes it; the human lead's review is needed only if the cost of §10 is judged a budget matter.
