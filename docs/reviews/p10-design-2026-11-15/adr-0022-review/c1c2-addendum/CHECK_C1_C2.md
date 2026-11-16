# Check of the ADR-0022 addendum on the combined tasks C1 and C2

**Claude (Opus 5.5) review. Astra review: NOT_PERFORMED. This is not a human approval.**

- Date: 2026-11-15 (UTC). Model: Opus 5.5 (`claude-opus-5-5`), running as the independent auditor.
- What I read: `ADDENDUM_C1_C2.md` (the draft by the Fable 5.2 drafting context), ADR-0022 revision 5 in `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/p10-design` (all of it), `AGENTS.md`, `CLAUDE.md`, `adr-0022-review/{REVIEW,CONFIRM,RECHECK_REV4}.md`, `confirm-rev5/CONFIRM_REV5.md`, and `HUMAN_DECISIONS_2026-11-15.md` §"S2's composition rule is strengthened".
- What I did: read the files. No code ran apart from two arithmetic scripts in `scratchpad/adr-0022-c1c2/check/` (`cost.py`, `rule.py`), run with `python3 -I <script>` (Python 3.15.1, macOS, no packages). No network access. Nothing was committed. Nothing in the repository was edited.
- Rulings I checked against: the lead's rulings 2–5 as given, and ruling 1 as **replaced** by the coordinator's message. That message says the human lead decided to strengthen the registered rule. The human lead's words, "let's strenght the registerd rule, the ost is aceptable", are recorded in `docs/reviews/p10-design-2026-11-15/HUMAN_DECISIONS_2026-11-15.md` line 56 of the p10-design worktree. I found that record. I did not verify the chat it came from.

## Verdict: READY SUBJECT TO the listed edits (paste-ready text in §7)

No blocker. There are 4 majors. M1 concerns the strengthened rule's floors, M2 the rulings the draft does not yet apply, M3 the L-sep C2 treatment and its fairness to the adapter baseline, and M4 a cost figure that needs restating. There are 11 minors.

Status of the change: **the COMPOSES rule of §11.4 is a registered rule. It is changed here by the human lead's decision, before any S2 calibration, rehearsal or registered record exists.** Because of that, the addendum's sentence "It changes no threshold, arm, model, data source, replicate count, rung or cap" has to be reworded (edit E2).

---

## (a) Consistency with every existing mention, and what changes

I checked each quotation in the addendum's §1 table against the ADR text. All 17 are accurate: rows 1–15 against ADR lines 139, 151, 168, 206–209, 272, 356, 373, 377, 446, 527, 532, 792 and 804; row 16 against CONFIRM.md line 72 (§3 item 2); row 17 against CONFIRM.md line 122 (§7 item 6).

Other mentions the table does not list. None of them conflicts with the addendum:
- §0 item 1, "lexical knowledge used compositionally", and §5.2, "the test is composition of seen words into unseen sentences". These use "composition" in another sense (words into sentences), not the combined tasks. No conflict, but the report should not let a COMPOSES line be read as support for §0's phrase.
- §6.1, "The untrained student and both teachers are scored on every panel". This is the addendum's basis for scoring Stage 0 on C1 and C2, and it is cited in §7.
- §11.3 rows 1 and 2, cited in the addendum's §8 (integrity).
- §17, "Knowledge fusion …", cited in §9.
- RECHECK_REV4 line 55 ("C1/C2 name both the combined tasks … and confirmation findings") and line 200 item 3 ("COMPOSES C1 / C2"). Covered by the addendum's sentence about the review records.
- CONFIRM_REV5 lines 242 and 245 (oracle-line coverage). Covered.

**What the addendum, with the human lead's change, alters.** Everything else is unchanged.

| Kind | Change |
|---|---|
| Threshold | The 0.80 number is unchanged, but **the rule it sits in changes**: it is now per answer, on the gap above Stage 0, and per replicate and order, where it was a raw-score mean ratio. Two existing thresholds are reused as definition floors (§10.1's 0.30 and ACQ's 0.50; see M1). A negative cut is added (0.50 in the lead's draft; I propose 0.70 on precedent, PENDING LEAD REVIEW). |
| Arm | None added. Stage 0's scoring on C1 and C2 rests on §6.1. M-seq and E-table are not scored (ruling 2). The router lane is struck (ruling 3). |
| Model, data source, replicate count, rung, cap | None. |
| Gate | G9's listed set gains 220911, a textual change to a gate. The §4.4 whole-string check extends §14.2 test (a), whose failure stops the work before the freeze. |
| Class | None. |
| Label | None by value. Two integrity readings apply. A missing combined record becomes a case of §11.3 row 2, INCOMPLETE; that is a reading of "a registered cell has no record". A recomputation difference that changes a COMPOSES line falls under §11.3 row 1, ENGINEERING-FAILURE; the ADR already says this, because COMPOSES is an annotation. So a combined scoring can affect the label through integrity, though not through its value (m8). |

## (b) Can each definition be implemented with no further choice?

| Item | Verdict |
|---|---|
| Items, n = \|E_C\| (250–500) | Yes. |
| Seed 220911 | Lies in 220001–228999. It is outside the replicate offsets (220001–011, 220101–111, 220201–211, 220301–311), outside 221001–221999, 222001–222999 and 229001–229999, and outside S0 (200001–209999) and S1 (210001–219999). The P1–P9-II ranges in ADR-0021 §6.3 are all below 200000 or in 900001–941001, so it is clear of those too. G9 must list it. **The edit is incomplete** (m1): §9's own sentence "220902–220910 are drawn once, in the data-generation and partition steps" needs it, and so does the "Further listed seeds" list. |
| Pairing σ, item j = (σ(j), σ(j+1 mod n)) | Yes. Each sentence is s1 exactly once and s2 exactly once, and s1 ≠ s2 by index. The justification "two E_C sentences never share a normalized English string, because such sentences are one identity group" does not follow (m2): being in one identity group does not make two items one item, and §5.2 does not say a panel holds one item per normalized string. |
| Layouts under segment tokenization | Yes for C1 (§4.1) and C2 (§5.1). They use only stored segments. The read offset is worded as "less BOS"; a formula is given in m5. |
| Reads per position | Yes. Oracle codes as §5.4. In C2, route "both" is two separate top-8 reads (each with its own softmax and gates), summed and added once. The markers are read with their own task's code. Answers and the NL after them are never read. |
| Stop token | Yes. a1 is the ids before the first token that contains 0x0A. Any bytes in the stop token before its newline are scored but are not in the context, and they are counted. A first-token stop gives an empty a1, which scores 0. |
| Answer at the token limit | Yes. The answer is kept whole, followed by NL, and is counted. One implementation note (m4): the last token of an a1 that reached the limit has not been fed through the model, so it must be fed before step 2. |
| Score | Yes: ½[chrF(a1, R_A) + chrF(a2, R_B)], taking the maximum over references, with the per-answer means recorded. Under the strengthened rule, the per-answer means are what is used. |
| Denominator | Yes: the single-task scores on E_C itself. S_A^C is C1's first answers, which are bit-identical to single-task A because σ covers every sentence once as s1. S_B^C is a separate pass. |
| Per-order rule, NOT_EVALUATED, recomputation | Implementable, but §8 has to be rewritten for the strengthened rule (§7, E1). The recomputation rule is the ADR's §13.3, unchanged. |
| Cache continuation against recomputation | The registered path and the consequence of a failure are not stated (m4). |
| Rehearsal | Follows ruling 4 ("never on E_C"). The ruling's "or any registered panel" is missing (E6), and which items the rehearsal uses is still open in the ADR (m10). |

## (c) The 15 entries marked [lead's choice]

| # | Follows a convention? | Harder for a positive line? | Comment |
|---|---|---|---|
| 1 Answer order A first | Yes, §6.4's text (German then French) | Neutral | **Consequence:** C1 always tests French in context, and under the strengthened rule C1's German H is identically 1 (m11). |
| 2 σ from 220911 | Yes (a listed seed for every draw) | Neutral | Fine. |
| 3 NL segment after a1 | Yes (§14.2: "newline separators are their own segments"; CONFIRM §3 item 2) | Slightly easier than the verbatim stop token, because the format is closer to training | Allowed: convention comes before the harder option. |
| 4 Answer at the limit kept | Yes (single-task scoring) | Harder | Fine. |
| 5 C2 layout | Uses only the ADR's template pieces | Neutral | Fine. |
| 6 C2 markers read with their own code | Yes (§6.4 sums "the source words" only) | Neutral | Fine. |
| 7 L-sep C1 position-wise | Yes (§5.4: a route per segment) | Neutral | Fair; see (d). |
| 8 L-sep C2 adapters summed | Analog of §6.4's "summed" | Harder for L-sep | **This handicaps a baseline** (M3). |
| 9 Ensemble and Stage 0 get no COMPOSES word | — | Harder | Fine. Under the new rule, print their H values. |
| 10 Rejected M-ii is NOT_EVALUATED | No convention | Harder | Fine. |
| 11 Router lane | — | — | **Struck by ruling 3.** The text still carries it in five places (M2). |
| 12 Denominator on E_C | Yes ("same panel", §7 and §10.1) | Neutral | Kept by ruling 3. Under the new rule it is the per-answer single-task score on E_C. |
| 13 Every order must pass | — | Harder | Kept. The new rule also requires every replicate. |
| 14 Missing record → §11.3 row 2 | A reading of row 2; row 1 already covers annotations | Harder for the study label | The addendum's §9 sentence "No value … can withhold" is true of values only (m8). |
| 15 Cost counted in full on top of the existing row | Yes ("counts more time against the cap") | — | Fine. |

**Leakage check.**
- No path takes E_C sentences or their references into training, calibration, the filter (Q_fit and Q_check only), the router's training prompts (§5.4 excludes evaluation panels), or the rehearsal (ruling 4).
- §4.4 reads E_C's German references as text in the data-generation step. That is the same exposure as §14.2 test (b), which already reads every reference, and nothing is scored. But a mismatch there could prompt a change of tokenization convention before the freeze that is informed by E_C text. Restricting the zero requirement to template boundaries removes this (m3).
- Teacher outputs on E_C must exist for **both** teachers (m9).

## (d) Is the L-sep treatment fair to the adapter baseline?

- **C1, position-wise: fair.** Step 1, including a1, is exactly LoRA-1(A) on P_A(s1). Step 2 runs B's adapter over a prefix computed under A's adapter. The store arms do the same thing: their A reads stay in the prefix while the B segment is processed. Recomputing the whole sequence under B would let B's adapter re-process the German prefix. No store arm has that option.
- **C2, summed adapters: a handicap that is not like for like.**
  - The store arms add two reads **at one layer (L), at the source-word positions only**.
  - L-sep adds both rank-42 updates to q and v **in all 30 blocks, at every prefix position** (BOS, `English:`, the source, NL), and the effects compound through the frozen stack. Summing independently trained dense adapters is known to interfere ("task arithmetic"). A low C2 score for L-sep would mostly measure that sum, not whether separate adapters can do C2.
  - The strengthened per-answer rule makes this sharper. C2's German answer is now tested on its own, so the summation's damage to the first answer can no longer be averaged away.
  - The choice rule "harder for a positive composition line", applied to a **baseline**, favours the primary arm. That runs against AGENTS.md: "Preserve strong baselines".
- **Fairest implementable alternative (PENDING LEAD REVIEW).** The separate-adapter deployment form, a switch per answer:
  - Step 1 is unchanged: A's adapter on [BOS] E S(s) NL M_A and on a1.
  - Step 2 is computed in full, without the step-1 cache: [BOS] E S(s) NL under B's adapter, M_A and a1 under A's (a1 as generated in step 1), and NL, M_B and a2 under B's.
  - This costs one recomputed prefix per item, which is negligible. It is easier for L-sep than the sum, but it is what "two LoRA-1 adapters behind the oracle route" would do when asked for both answers.
- If the sum is kept, every L-sep C2 line must carry this caveat: "adapters summed in all 30 blocks over the whole prefix; the store sums two reads at one layer on source words; not a like-for-like comparison."
- C2 for L-sep is descriptive and enters no annotation (NO ADVANTAGE OVER SEPARATE ADAPTERS uses single-task scores), so the effect is on how the result is read, not on any label.

## (e) Added cost, recomputed (projection, not measurement)

**Basis.** The ADR's rate is 1.6–5.2 min per 2,000 single answers, so 0.8–2.6 min per 1,000. Second answers are weighted 1.0–1.5 single answers. n = 500. Command: `python3 -I scratchpad/adr-0022-c1c2/check/cost.py`.

- **Per arm-cell:** C1 (2n) + C2 (2n) + S_B^C (n) = 2,500–3,000 answer-equivalents, which takes 2.0–7.8 min. This agrees with the drafter.
- **Per replicate:** 10 arm-cells, router struck: **0.333–1.300 h**. The drafter's 0.36–1.43 h included the router.
- **Stage 0:** once per study, 0.033–0.130 h.
- **Registered run:**
  - 4 replicates: 1.367–5.330 h.
  - 3 replicates: 1.033–4.030 h.
- **Added to R** (run plus an equal recomputation):
  - **4 replicates: 2.73–10.66 h.**
  - **3 replicates: 2.07–8.06 h.**
  - The drafter's figures with the router were 2.97–11.66 h and 2.25–8.81 h; I reproduced them exactly.
- The strengthened rule adds no scoring. Stage 0's single-task and combined scores on E_C, and the teachers' stored outputs on E_C, are already in this figure.

R and what fits. x is the place in the projected range, 0 at the fast end; the condition is P + 2R ≤ cap; values are rounded down. Router struck (the drafter's router-included values in brackets).

| Rung | R (h) | 36 h, P = 3.5 | 36 h, P = 7.0 | 72 h, P = 3.5 | 72 h, P = 7.0 |
|---|---|---|---|---|---|
| 1 (4 × 2,000) | 23.01–65.40 [23.25–66.40] | no (was no) | no (was no) | x ≤ 0.26 [0.25] (was 0.40) | x ≤ 0.22 [0.21] (was 0.35) |
| 2 (3 × 2,000) | 17.46–49.52 [17.64–50.27] | **no** (was 0.03) | no | x ≤ 0.52 [0.50] (was 0.72) | x ≤ 0.46 [0.45] (was 0.65) |
| 3 (4 × 1,000) | 18.74–57.07 [18.98–58.07]; **the drafter omitted this row** | no (was < 0.01) | no | x ≤ 0.40 [0.39] (was 0.59/0.60) | x ≤ 0.35 [0.34] (was 0.54) |
| 4 (3 × 1,000) | 14.26–43.27 [14.44–44.02] | x ≤ 0.06 (was 0.17) | x < 0.01 (was 0.10) | x ≤ 0.68 [0.66] (was 0.95) | x ≤ 0.62 [0.61] (was 0.88) |

What this means:
- **At 36 h** only rung 4 fits, and only at the fast edge (x ≤ 0.06 at P = 3.5; below 0.01 at P = 7.0).
- **At the 72 h ceiling** rung 1 fits for x ≤ 0.26 (P = 3.5). NOT STARTED: BUDGET becomes the outcome for x above about 0.68 (P = 3.5) or 0.62 (P = 7.0); before the addition those points were 0.95 and 0.88.
- The rung 3 "was" value at 72 h and P = 3.5 is 0.60 by my floor; the ADR prints 0.59 (a rounding difference, not a finding).
- `HUMAN_DECISIONS_2026-11-15.md` records the human lead's acceptance against "about 3 to 12 hours … for four replicates, unchecked". The checked figure, with the router struck, is 2.73–10.66 h, which is inside that envelope.

## (f) Check of the strengthened rule (the human lead's decision; the lead's draft)

**Floor to reuse.** §10.1's floor of 0.30 applies to the **teacher** gap (teacher − Stage 0), not to an arm's own gain. Putting 0.30 on the arm's gain would require G ≥ 0.50 on a teacher gap of 0.60 or more, so almost every cell would be NOT_EVALUATED. The right reuse is two existing thresholds, each on its own quantity:
1. the teacher gap on E_C for that answer's language, s_a(teacher, single) − s_a(Stage 0, single) ≥ 0.30 (§10.1); and
2. the arm's single-task gap closed on E_C, G_a^C ≥ 0.50 (ACQ, §11.1).

Together these make the denominator at least 0.15. Using 0.25 (the negative zone) instead would allow denominators near 0.075 and noisy ratios. On n = 500 with an item sd of about 0.2, a paired numerator difference has a 95% half-width of about 0.02–0.03, so H has an uncertainty of about 0.1–0.2 at the floor. The rule is stringent, which is the harder direction for a positive line, and acceptable.

**Mixed baselines (M1).** The draft subtracts Stage 0's **combined** score in the numerator but its **single** score in the denominator.
- If the student does worse in the combined context (s_a(S0, K) < s_a(S0, single)), a context-degraded arm gets credit for Stage 0's own drop. Example: Stage 0 French 0.18 single and 0.10 combined; arm 0.50 single and 0.35 combined. The draft gives H = 0.78. Measured against the single floor, H = 0.53.
- The ensemble then has H > 1.
- **Proposed tightening:** numerator floor m_a = max(s_a(Stage 0, K), s_a(Stage 0, single)), the harder of the two. This gives H ≤ 1 for any arm whose combined score equals its single score, such as the ensemble. The ensemble then reaches H = 1 when the context does not help Stage 0, and stays at or above 0.80 unless the context lifts Stage 0's score by more than 0.2 × the teacher gap (0.06 or more at the floor). That case is correctly read as "the floor rose".

**Negative cut, precedent.** 0.50 mirrors "at least half the gap", which is a *pass* threshold for acquisition; its negative counterpart in the ADR is 0.25. H is a ratio of the gap kept under a condition. That is the form of RET, whose negative zone is G_after < **0.70** × before (§11.1). So 0.70 is the closer precedent, and 0.50 has a weaker one. **PENDING LEAD REVIEW.** The cut does not affect when COMPOSES prints.

**Required tests.** Command: `python3 -I scratchpad/adr-0022-c1c2/check/rule.py`. The numbers are invented for illustration and are not data.

| Case | Old rule (rev 5) | Strengthened rule |
|---|---|---|
| Arm that does nothing (= Stage 0) | **passes** (combined ≈ 0.8 × single holds whenever the context does not cut Stage 0 by more than 20%) | the denominator floor fails (G = 0): NOT_EVALUATED, no COMPOSES |
| Answers only the first segment (a2 empty or Stage-0-like) | passes whenever S_A ≥ 4·S_B (½S_A ≥ 0.4(S_A + S_B)) | H_French ≤ 0, fails |
| Copies the German answer into the French slot (chrF of German against French references ≈ 0.25, Stage 0 ≈ 0.15, arm single 0.50) | fails here, but could pass with a strong German | H_French ≈ 0.31, fails (DOES NOT COMPOSE if it happens in every replicate) |
| Ensemble (BY CONSTRUCTION) | ratio 1 | H_German = 1 in C1; H_French = 1 with the max floor (1.06 with the draft's floor in the example); printed, no word |
| M-i-separate | — | C1: H_German = 1 exactly; the French answer is the real test. C2: both answers are real tests. If any arm can pass, this one can. |

**Are the per-answer denominators defined for every scored arm?**
- Store arms, L-joint and L-seq: defined by the floors.
- L-sep and M-i-separate: they use LoRA-1 or ST1 single-task scores on E_C.
- M-ii rejected: NOT_EVALUATED.
- Stage 0: its denominator is 0 by definition, so it is the floor and has no H.
- Ensemble: its single-task scores are the teachers' stored outputs, so G = 1 and the denominator is the teacher gap. Print it as BY CONSTRUCTION with no word.
- If the teacher gap on E_C for a language is below 0.30, every arm's line is NOT_EVALUATED, with that reason.
- An arm that forgot one capability (L-seq most likely; M-append-frozen if it forgets) is NOT_EVALUATED because its single-task G^C is below 0.50. The reason must be printed as "single-task gap below 0.50", so that it is not read as a failure to compose.

**C1 property.** For every arm, C1's first answer is the single-task A answer, so H_German(C1) = 1 by construction whenever it is defined. C1's COMPOSES therefore tests only the French answer in context. The report should say so.

**Unfair to the adapters relative to the stores?**
1. The L-sep C2 summation (M3) now hits a per-answer test directly.
2. Forgetting moves L-seq into NOT_EVALUATED. The rule is the same for every arm, but the outcome reflects retention, not composition; the reason line handles this.
3. Nothing else is asymmetric. L-joint and L-seq on C2 get one adapter with no summation, which, if anything, favours them.
4. LoRA acts on generated positions too. In position-wise C1 this matches the store's handling of the prefix.

## Findings

**MAJOR**

- **M1. Floors of the strengthened rule.** Reuse §10.1's 0.30 on the teacher gap on E_C together with ACQ's 0.50 on the arm's single-task G^C. Do not apply 0.30 to the arm's own gain. Use the numerator floor max(Stage 0 combined, Stage 0 single). Negative cut: 0.70 (RET precedent) or the lead's 0.50, PENDING LEAD REVIEW. Text: E1.
- **M2. The rulings are not yet applied in the draft.**
  - The router lane is still in §7 (the bullet "Keyword-router lane"), §10 (its row and its total), §11 item 8 ("or the router line"), §12 row 11 and §13 item 3.
  - M-seq and E-table still read "open, §13" (§7 rows; §13 item 2).
  - Ruling 4's "or any registered panel" is missing in §3.
  - §8, §9, §12 rows 12–13 and §13 item 1 describe the replaced raw-score rule.
  - The header's "changes no threshold …" is now false.
  - Text: E2–E7.
- **M3. L-sep on C2.** The sum in all 30 blocks over the whole prefix is not like for like with the store's sum of two reads at one layer, and it handicaps a baseline (AGENTS.md: "Preserve strong baselines"). Adopt the per-answer switch as the fairest implementable form, or keep the sum with the caveat line. PENDING LEAD REVIEW. Text: E8.
- **M4. Cost.** The addendum's §10 total includes the struck router, and its rung paragraph omits rung 3 and wrongly suggests that only rung 4 is affected at 36 h. With the router struck, the added time is 2.73–10.66 h for 4 replicates and 2.07–8.06 h for 3. At 36 h only rung 4 fits, at x ≤ 0.06. Text: E9.

**MINOR**

- **m1.** G9 and §9 also need the §9 sentence "220902–220910 are drawn once" changed to 220902–220911, and a new list bullet "220911, the C1 pairing". Do not edit §22's historical "Not applied" item 1. Text: E10.
- **m2.** Replace the non sequitur about shared normalized strings with an assertion and a reported count. Text: E11.
- **m3.** §4.4 should require 0 mismatches at template and segment boundaries only. Mismatches inside a reference are listed, as test (a) treats targets, so no tokenization decision is driven by E_C text. Text: E12.
- **m4.** Cache continuation is the registered path. A mismatch with full recomputation in the rehearsal check stops work before the freeze as a G4-class defect. The last token of an a1 that reached the limit is fed before step 2. Text: E13.
- **m5.** Give the offset as a formula: position = stored position in P_B(s2) − |BOS| + |[BOS] E S(s1) NL M_A a1 NL|.
- **m6.** The "descriptive; enters no gate, class or label" sentence goes on every COMPOSES line, not only on every table (it is in E1).
- **m7.** Single-reference subset for C1: items where |R_A(s1)| = 1 and |R_B(s2)| = 1.
- **m8.** §9's "No value of C1 or C2 can produce, withhold or change TRANSFER-POSITIVE" should add: "a missing combined record or a recomputation difference acts on the label through §11.3 rows 1–2, as for every registered score."
- **m9.** §14.2 step 5 should say explicitly that both teachers generate on E_C.
- **m10.** Which items the rehearsal uses is still unstated in the ADR. If they are D_cal, its "calibration and pilot only" wording conflicts. PENDING LEAD REVIEW.
- **m11.** Because of the fixed German-first order, C1 never tests German in second position. State this in the report line. Whether to add the reverse order is PENDING LEAD REVIEW (it would add scoring).

## 7. Paste-ready edits

**E1 — ADR §11.4, replace the COMPOSES row, and replace addendum §8 with the same rule.**

> | COMPOSES C1 / C2 (strengthened by the human lead's decision of 2026-11-15, recorded in `HUMAN_DECISIONS_2026-11-15.md`, before any S2 calibration, rehearsal or registered record; it replaces revision 5's raw-score rule) | On the E_C sentences, for task K ∈ {C1, C2}, arm X, order o, replicate r and answer a ∈ {German, French}: s_a(X, K) is the mean chrF-norm of answer a inside K; s_a(X, single) is X's single-task score on the same sentences (§6 of the combined-tasks addendum); Stage 0 and the teacher likewise. **Defined** only if s_a(teacher, single) − s_a(Stage 0, single) ≥ 0.30 (§10.1) and X's single-task gap closed on E_C, G_a^C = (s_a(X, single) − s_a(Stage 0, single)) / (s_a(teacher, single) − s_a(Stage 0, single)), is ≥ 0.50 (§11.1 ACQ); otherwise NOT_EVALUATED with the reason. **H_a = (s_a(X, K) − m_a) / (s_a(X, single) − s_a(Stage 0, single))**, with m_a = max(s_a(Stage 0, K), s_a(Stage 0, single)). A cell (o, r) passes if H_a ≥ 0.80 for both answers. First match wins: **NOT_EVALUATED** if any H of any cell of X is undefined, any combined or single-task E_C score of X is undefined (§8 of the addendum), or X is M-ii with a CONSOLIDATION-REJECTED cell; **COMPOSES K** if every cell of every order passes; **DOES NOT COMPOSE K** if, in some order, every replicate has H_a < 0.50 for some answer *[0.50 is the lead's draft; the auditor notes RET's negative zone, 0.70, as the closer precedent; the lead fixes one before the freeze]*; otherwise **COMPOSITION INCONCLUSIVE**. Every line prints n, every H_a per cell, the single-task G_a^C, Stage 0's per-answer combined and single scores (the floor), and beside them revision 5's ratio C̄ / (0.80 · S̄) labelled "revision 5's raw-score rule, replaced by the human lead". The ensemble's and Stage 0's values are printed without any of these words (BY CONSTRUCTION; floor). Every line carries: "descriptive; enters no gate, class or label". In C1, H_German = 1 by construction, so C1 tests the French answer in context. |

Also in §20's "Annotation margins" row, change "0.80 for composition" to "0.80 of the per-answer gap above Stage 0 for composition (strengthened by the human lead); single-task G on E_C ≥ 0.50 and teacher gap ≥ 0.30 to be defined; [0.50 | 0.70] for DOES NOT COMPOSE". In the ADR header and §18, add one line recording the human lead's decision verbatim, with its source.

**E2 — Addendum header "What it changes".**

> It adds definitions to §6.4, one listed seed to §9 and G9, checks to §14.2 test (a) and to the rehearsal, and a cost projection to §13.3. **By the human lead's decision of 2026-11-15, made before any S2 observation, it replaces the COMPOSES rule of §11.4** with a per-answer rule on the gap above the untrained student (§8). It changes no other threshold, and no arm, model, data source, replicate count, rung or cap.

**E3 — Addendum §7.** Delete the bullet "Keyword-router lane …". In the M-seq and E-table rows, replace "open, §13" and "would …" with "not scored (§6.4's list; the lead's ruling)". Add to the L-sep row: "printed with the caveat of §7 (E8)".

**E4 — Addendum §10.** Delete the row "Keyword-router C1 …". Set "Added scoring per replicate" to **0.33–1.30 h**; registered run, 4 replicates (3): **1.37–5.33 h (1.03–4.03 h)**; recomputation the same; **added to R: 2.73–10.66 h (2.07–8.06 h)**. Replace the "Consequence …" paragraph with:

> With the addition, R becomes 23.01–65.40 h (rung 1), 17.46–49.52 h (rung 2), 18.74–57.07 h (rung 3) and 14.26–43.27 h (rung 4). At 36 hours only rung 4 fits: for x ≤ 0.06 at P = 3.5 and x < 0.01 at P = 7.0 (rung 2 no longer fits). At the 72-hour ceiling rung 1 fits for x ≤ 0.26 (0.22), rung 2 for x ≤ 0.52 (0.46), rung 3 for x ≤ 0.40 (0.35) and rung 4 for x ≤ 0.68 (0.62); above that the outcome is NOT STARTED: BUDGET. The rung rule, the rungs and the cap are unchanged; the rule is applied to measured rates. The human lead accepted the cost (HUMAN_DECISIONS, 2026-11-15).

**E5 — Addendum §11 item 8.** Replace "the router line" with "the H values of the ensemble and Stage 0; the reason line for an undefined H". Add item 10: "The rule of §8 on synthetic records: a do-nothing arm, a first-answer-only arm and a copy-the-first-answer arm do not print COMPOSES; the ensemble prints H = 1."

**E6 — Addendum §3, rehearsal sentence.** Change "never on E_C" to "never on E_C or any registered panel (the lead's ruling)".

**E7 — Addendum §12.** Strike row 11. Rows 12–13: "per-answer H on E_C above max(Stage 0 combined, single), every replicate and order (the human lead's strengthening)". §13: items 1–4 answered by the rulings and the human lead's decision; delete them or mark them answered.

**E8 — Addendum §7, L-sep C2 (lead to choose one).**
- Option (i), the auditor's recommendation as the fairest form: "Each answer is generated with its own adapter over the source. Step 1: A's adapter on [BOS] E S(s) NL M_A and a1. Step 2 is computed in full without the step-1 cache: B's adapter on [BOS] E S(s) NL, A's on M_A and a1 (as generated), and B's on NL, M_B and a2. This is the deployment form of two adapters behind a switch."
- Option (ii), keep the sum and add the printed caveat: "L-sep C2: adapter updates summed in all 30 blocks over the whole prefix; the store sums two reads at one layer on source words; not a like-for-like comparison."

**E9** is in E4.

**E10 — ADR §9.** Change "220902–220910 are drawn once" to "220902–220911 are drawn once". Add to "Further listed seeds": "220911, the C1 pairing (a permutation of E_C, drawn once after E_C is built; the combined-tasks addendum)". In G9, change "220901–220910, of which 220902–220910" to "220901–220911, of which 220902–220911". In §20's seed row, change "220901–220910" to "220901–220911".

**E11 — Addendum §3.** Replace the sentence beginning "Two E_C sentences never share …" with: "The data-generation step asserts that no two E_C items share a normalized English string and reports the count. If any do, they stay as they are, and s1 ≠ s2 still holds by index."

**E12 — Addendum §4.4.** Replace "0 mismatches required" with: "0 mismatches required at every segment boundary and inside every template piece and source. Mismatches inside the substituted reference are listed, as test (a) lists target mismatches, and require nothing."

**E13 — Addendum §4.1, after "tested, §11".** Add: "The registered path is the cache continuation. In the rehearsal check (§11 item 9), any token difference against full recomputation is a G4-class defect and stops the work before the freeze. When a1 reached the limit, its last token is fed through the model before the step-2 input."

## Commands and environment

- `python3 -I /private/tmp/claude-501/-Users-daniellaloush-dandush03-ArborLM--claude-worktrees-arborlm-consolidation-experiment-2b31c1/cfc0efd5-b7ca-4602-959a-07fe6b8d4e7d/scratchpad/adr-0022-c1c2/check/cost.py`: the cost and rung table.
- `python3 -I /private/tmp/claude-501/-Users-daniellaloush-dandush03-ArborLM--claude-worktrees-arborlm-consolidation-experiment-2b31c1/cfc0efd5-b7ca-4602-959a-07fe6b8d4e7d/scratchpad/adr-0022-c1c2/check/rule.py`: the illustrative cases of the rule (invented numbers).
- Environment: Python 3.15.1 on macOS (darwin), standard library only.
- Read-only `grep` and `sed` over `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/p10-design/docs`.
- No failed checker attempts.
