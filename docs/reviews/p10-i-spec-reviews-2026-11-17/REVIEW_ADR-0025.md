# Independent specification review — ADR-0025 (P10-I-S2, sequential teacher transfer)

- **Object:** `docs/decisions/ADR-0025-p10-i-s2-sequential-teacher-transfer.md`, 382 lines, SHA-256 `ec166414a2db9bdb8a34db842e12c3d06b98ed81c852d95d5503a77df828440a`, untracked on branch `claude/p10-i-specs` (worktree HEAD `c525898` at review time). Line numbers below are the draft's.
- **Reviewer:** the `arbor-auditor` subagent, model Claude Opus 5.5 (as I know it). I did not write the draft or any part of P10-S2's code or records. This is independent engineering and mathematical review. It is **not** Astra validation and **not** human approval. `Astra review: NOT_PERFORMED`.
- **Read against:** `DIRECTION.md` §§4, 5, 7, 9; `AGENTS.md`; `CLAUDE.md`; `docs/EXPERIMENT_PROTOCOL.md`; ADR-0022 rev. 5 with its addenda (combined tasks; 44 GEN windows; data-step outcome); `results/p10s2-datagen-2026-11-16/` (README, `prefreeze_record.json`); `studies/p10s2/{data,prefreeze,retrieval}.py`; the P10-S2 bundle and downloads under `.claude/worktrees/agent-a91c79a181109bb9c/data/` (read only); `docs/reviews/p10s2-qualification-2026-11-16/REVIEW.md`; `results/p10s1-run-2026-11-17/OUTCOME.md`; `results/p10s0-run-2026-11-16/OUTCOME.md`; `docs/reviews/p10-design-2026-11-15/{DOWNLOAD_LEDGER.md,adr-0022-review/CONFIRM.md}`; sibling drafts ADR-0023, -0024, -0026, -0027, -0028.
- **No training, generation, network access or long computation.** No file other than this one was written in the repository. No git write.

## Verdict: NOT READY

There are two blocking findings. (B1) The draft removes M-ii, the combined tasks and the cost measures. All three are on the human lead's P10 list, and the reason the draft gives for removing them is wrong for M-ii. (B2) The draft drops general-language preservation from the condition for a positive milestone reading, and §3 does not say so. Eighteen required findings follow. Most are text changes. Three of them affect feasibility or validity: the shared English source pools of A and B (R4), the fairness of D-append (R12) and the retention line's NOT EVALUABLE ordering (R9). Every number I checked against a record matches, apart from small imprecisions (§A).

## A. Numbers quoted from records (task item 1)

Checked by my own script, `scratchpad/rev0025/checks.py` (output `checks.out`). The full path is given at the end. Records were read with `python3 -I` (Python 3.15.1, Darwin arm64).

| Draft line | Quoted | Record | Result |
|---|---|---|---|
| 34 | own 0.7675 / 0.7754; margin 0.6214 / 0.6425; Q_check 72/78 = 0.9231, 21/22 = 0.9545 | `prefreeze_record.json` `qualification.detail` | match |
| 35 | Q_check accepted 78 / 22 vs 150; pools 7,804 / 2,341 vs 8,000; available 7,763 / 2,300 vs 10,000 | `qualification`, `sufficiency_after_filter` | match |
| 36 | Q_fit 104/500 = 20.8 %, 41/500 = 8.2 %; pool yields 13.0 % / 3.9 % | `filter`; 7,804/60,000 = 0.1301, 2,341/60,000 = 0.0390 | match. 7,809 and 2,342 passed the filter before the eval-equal drops (5, 1; qualification review) |
| 37 | 734,418 / 784,089 in-vocabulary no-gold sources; gold 181,970 / 132,151 "outside the panels" | `partition.source_pool`, `gold_pool`; `data.py:339-340` confirms in-vocabulary, 3–10 words | match. The record says "outside Q, D_cal, D_con". Evaluation panels are on the other side by construction, so the wording is acceptable |
| 38 | 740 s / 844 s; 2,100 s; 5,677 MiB | `steps.memory_by_phase`: 855.0 − 114.8 = 740.2; 1,699.0 − 855.0 = 844.0; end 2,099.6; peak 5,677 | match |
| 42 | a_use 1.000 (2K/4K, 8K/16K); 0.654, 0.637 (8K/1K, 32K/4K) | P10-S1 `OUTCOME.md` §4 table, F-OQ column | match |
| 43 | A5-D qualified at 4,096 and 16,384, 0.5 facts per slot | P10-S0 `OUTCOME.md` l. 7 | match |
| 45 | Wilson lower bounds 0.842 / 0.782 | recomputed 0.84217 / 0.78202 | match |
| 86 | 150 items at 0.90: interval about 0.84–0.94 | Wilson(135, 150) = 0.8416–0.9385 | match |
| 90 | true precision 0.92 → below 0.90 in "roughly one run in six" | Binomial: 0.146 at K = 150; 0.184 at K = 156 (two A blocks); 0.141 at K = 160 | acceptable ("one in seven to one in five") |
| 98–100 | Q_check need about 1,000 / 3,500 items; sources 77,000 / 261,000; 195,000 / 657,000 | 962 / 3,409; 77,290 / 260,870; 194,770 / 657,391 (computed from the "available" rates) | arithmetic matches. The population basis is not the same (R2, R4) |
| 100, 324 | 657,000 of 784,089, about 84 % | 83.8 % | match |
| 108, 341–343 | 5.6 h whole pools; 1.3 h; 3.2 h | 5.58 h; 1.28 h; 3.24 h at 12.34 / 14.07 ms per source | match |
| 133 | 2,424,833 and 2,419,200 parameters | 4,096·592 + 1; 42·30·(1,152 + 768) | match |
| 172 | loads 0.49 / 0.98 | 4,002/8,192 = 0.489; 4,002/4,096 = 0.977 | match |
| 268 | 8 GiB guard stopped attempts 6 and 7 | README attempts table | match |
| 310–315 | 936,320,520 B; 126,182,132 B; running total 1,188,183,868 B | `fetch_record.json` (29 files, summed); `DOWNLOAD_LEDGER.md` last two rows | match |
| 328 | 0.8⁶ = 0.26 | 0.262 | match |
| 337 | "teachers on 1,000 Q items in 26 s" | the 26.4 s phase is **both** teachers on Q_fit and Q_check (`prefreeze.py:167-169`): 2,000 translations | imprecise. Say "both teachers, 2,000 translations" |
| 347 | 178 s; "whether one or two prompts per item was not verified" | `prefreeze.py:228-232`: the student is scored for **both** capabilities over all 1,000 Q items, so 2,000 greedy answers in 178.1 s (about 0.089 s each, at the default thread count) | resolved: two |
| 351 | 30 store-type and 24 LoRA units | 10 + 8 per replicate | match |
| 352 | calibration and ladder "about 30 units of 2,000" | 18 (rate grids, 3 modules × 3 rates × 2 capabilities) + 2 (second read layer) + 16 (M1 and D1 to 8,000 on two capabilities) = 36 | understated by about 20 % |

## B. Quality criteria: ADR-0022 against the draft, one by one (task item 2)

| Criterion | ADR-0022 | Draft | Same? |
|---|---|---|---|
| Q1 own score ≥ 0.55 | on Q = Q_fit ∪ Q_check, **1,000 items, every item with both a German and a French reference** (`data.py:280,323`; `prefreeze.py:195-196`) | on Q_fit^c, **500 items per capability**, drawn from that capability's gold pool | threshold same; **panel halved and population changed** (R2) |
| Q2 margin ≥ 0.30 | on the same 1,000 both-reference items | implicitly on Q_fit^c | same change (R2) |
| Q3 filter on Q_fit, Wilson lower bound ≥ 0.90, most permissive setting, grid and tie rule of §5.3 | Q_fit = 500 both-reference items | 500 per-capability items. The per-item correctness cut (chrF ≥ 0.60 against the best reference) is not restated | threshold same; population changed; the 0.60 is inherited only by citation (R2) |
| Q4 point precision ≥ 0.90 on ≥ 150 accepted Q_check items | fixed 500 items, both references | seeded blocks of 500 until ≥ 150 accepted, per-capability gold pool | threshold same; sample size now adaptive (no bias, see R5) |
| Pool ≥ 8,000 and sufficiency 10,000 | §4.3(3), §5.2 | 10,000 minimum; 25,200 disjoint target | count; acceptable |
| Panel sufficiency E_A, E_B ≥ 500 | §5.2 | not stated | gap (R18) |
| ACQ1, ACQ2, RET, negative zones, CONTROL-FAILED ≥ 0.50, gap defined ≥ 0.30, pilot 0.25 | §11.1, §11.3, §12.2 | §8.2–8.3, §7.2 | same figures |
| GEN 0.02 nats as a **gate of the positive label** (TRANSFER-POSITIVE WITHHELD) | §11.1, §11.3 rows 6–8 | separate line; **not** a condition of the milestone reading (l. 28) | **weakened, not disclosed** (B2) |
| ACQ1 failing in any replicate → mechanism NOT_EVALUATED | §11.2 row 1 | RETENTION line needs only G_first(M1) ≥ 0.50, not the lexical margin or the marker limit | weakened for the RETENTION line; the milestone still needs ACQUISITION (R10) |
| Recomputation tolerance (bit-identical / 1e-6; NOT_EVALUATED cell; ENGINEERING-FAILURE if a label changes) | §13.3 | "a recomputation difference that changes any condition or line" (l. 260); no tolerance | incomplete (R18) |

## C. Findings

### B1 — BLOCKING — §3 l. 62, §13 item 6 l. 326, §16 l. 375
**Problem.** The draft removes M-ii, MA-gold, the combined tasks C1 and C2, the timing benchmark and the cost lines. The stated reason is "None bears on acquisition or retention". That is false for M-ii. M-ii is ADR-0022's mechanism (ii), retention **under modification** (H22-D). Three of the removed items are on the human lead's own P10 list: "mechanism ii", "capabilities A, B, combined" and "the five cost measures" (`adr-0022-review/CONFIRM.md` §7 item 6, quoted at ADR-0022 addendum §1 row 17). The human lead then strengthened the COMPOSES rule and accepted its cost ("let's strenght the registerd rule, the ost is aceptable"; `HUMAN_DECISIONS_2026-11-15.md`). Under the authority order of `AGENTS.md`, the human lead's direction ranks above a lead's recommendation. `DIRECTION.md` §4 says each P10-I study "carries its P10 study's corrections". It does not authorise dropping requested content. The removal is visible in §13, so it is not silent. But it is defaulted to "remove" on a false premise. The DIRECTION.md §7 rule against wall-time comparisons also justifies only removing TRAINING COST COMPARABLE and the timing benchmark. The count-based lines (value rows read, stored size) read no wall time.
**Change.** (a) Correct the reason in §3 and §13 item 6. Say that M-ii tests retention under modification and that the combined tasks, mechanism ii and the cost measures were on the human lead's P10 list. Quote the source. (b) Make the default "keep, descriptive" for C1/C2 under the addendum's strengthened rule, for M-ii and for the logical-count cost lines, with removal as the human lead's explicit alternative. Otherwise present the two options without a recommendation. (c) If C1/C2 are kept, restate the arm list (M-ii → per (a); L-seq → D-seq; add D-append) and cost the lane for **three** replicates. The addendum gives 2.07–8.19 h for three. "3 to 12 hours for four" is the figure the human lead accepted, not this study's. (d) Drop only the wall-time rule (TRAINING COST COMPARABLE), citing DIRECTION.md §7.

### B2 — BLOCKING — §1 l. 28, §3 table, §8.3 l. 256
**Problem.** ADR-0022 required GEN for any positive label and printed TRANSFER-POSITIVE WITHHELD when it failed (§11.3 rows 6–8). In the draft, milestone question 2 is printed "supported, oracle-addressed" when ACQUISITION and RETENTION are positive, whatever GENERAL-QUALITY says. The §3 table of changes does not list this. It is a weakening of a positive criterion carried over from the predecessor.
**Change.** Either require GENERAL-QUALITY = PRESERVED for "supported", and print "WITHHELD — GENERAL QUALITY NOT PRESERVED UNDER A LEARNED ROUTE" otherwise, as ADR-0022 did. Or list the change in §3 and as a reserved choice in §13, with the reason, for the human lead to decide.

### R1 — REQUIRED — §3 l. 55, §4.2 l. 79 ("unchanged from ADR-0022")
**Problem.** Q1 and Q2 move from a 1,000-item panel to a 500-item panel (see table B). The draft calls them "Unchanged".
**Change.** Either compute Q1 and Q2 on 1,000 items (Q_fit^c plus the first Q_check block, fixed before any reading), or list the change in §3 with its precision consequence.

### R2 — REQUIRED — §4.1 l. 74–75, §4.3 l. 98, §4.3 rule 1
**Problem.** P10-S2's Q panels were drawn from sentences that have **both** references (`data.py:280,323`). The draft draws per capability from each gold pool, which is a different population, possibly with different sentence length and difficulty. The projected Q_check yields (15.6 %, 4.4 %) and pool yields come from the old population. The provenance note (l. 47) calls Part Q a re-measurement, but on a changed population. Q3's per-item correctness cut (chrF ≥ 0.60) is not written in §4.2.
**Change.** State the population and choose deliberately. Both-reference sentences keep comparability. Per-capability sentences raise the supply for B. Flag the yield projection as population-shifted. Write the 0.60 cut and the grid into the Q3 row.

### R3 — REQUIRED — §4.2, §13 item 5
**Problem.** The draft states the sampling risk of Q4 but not of Q3, which is the more fragile one for teacher B. A Wilson lower bound ≥ 0.90 needs at least 35 accepted items with 0 errors, 53 with 1 error, 69 with 2 and 84 with 3 (my computation). B's setting accepted 41 of 500 on P10-S2's Q_fit with no error. A single wrong item among B's accepted outputs on the new Q_fit would force a stricter setting, with lower yield and a larger pool need, or fail Q3. That would be a QUALIFICATION-NEGATIVE caused by the size of Q_fit, which is the kind of convenience limit `DIRECTION.md` §5 targets. Extending Q_fit until a setting passes would be optional stopping on a quality outcome and is not acceptable. A larger **fixed** Q_fit, chosen now, is acceptable.
**Change.** State the figures above in §4.2. In §13 item 5, give the human lead a costed option of a fixed larger Q_fit (for example 2,000 per capability; teacher time is negligible, under 1 minute). Correct the stated downside: Q4 on held items is the guard against an edge filter.

### R4 — REQUIRED — §4.3 table l. 98–100, rules 2–3, §14 l. 341–343
**Problem.** The two source pools overlap heavily, and the projection ignores it. Every in-vocabulary training-side English key is in A's source pool, in A's gold pool, or in one of a few thousand blocked or contraction-only keys. So |A ∪ B| ≲ 734,418 + 181,970 + about 2,000, and **|A ∩ B| ≳ 600,000**: at least 82 % of A's pool and 77 % of B's. If both capabilities generate on most of their pools, sources accepted by both form shared identity units. The sufficiency rule (`data.py:445-458`) gives each capability only half of them. In P10-S2, two independent 60,000-source samples (`data.py:368-379`) would overlap in about 3,750 English sentences. Under independent acceptance they would yield about 19 shared accepted units. The record has 79 (`sufficiency_after_filter.shared`). That implies P(A accepts | B accepts) ≈ 0.5, against a marginal 0.13 (my estimate; it depends on the intersection bound). At that correlation, B's available count from the whole pool is about 30,000 − 11,500 + 5,750 ≈ 24,300, **below the 25,200 disjoint target**. The 10,000 minimum would need about 326,000 B sources, not 261,000. Rule 2 also does not say how "available" is computed while the two capabilities are generated in parallel or in sequence. A's count depends on B's progress.
**Change.** (a) Pick one design. Either split the English intersection between A and B by a listed seed **before** generation, so each teacher generates only on its own sources (no wasted generation; availability is simply its own accepted count; disjoint across replicates is then judged against the split pools), or keep the post-hoc split and define the order of generation and the availability computation exactly. (b) Redo the projection with the overlap and state that the disjoint target may be infeasible for B. (c) Have the Part Q rehearsal measure the shared share.

### R5 — REQUIRED (text) — §4.3 rule 1 (optional stopping, task item 2)
**Analysis.** The stopping rule reads only acceptance indicators, which depend only on the teacher output and the source (beam score, length ratio, difference from the source). With a seeded random block order, the accepted items in the first m blocks, conditional on their number K, are a uniformly random K-subset of the accepted subpopulation of the gold pool, and K is ancillary to correctness. The point precision is therefore unbiased conditional on K, and the Wilson interval keeps its coverage. **There is no optional-stopping problem, and a separate fixed-size check sample is not needed.** That holds only if (i) no chrF or reference is computed or logged for any Q_check item before the stop, (ii) blocks are neither skipped nor reordered across a PAUSE, and (iii) the filter setting is fixed from Q_fit before the first Q_check block is drawn.
**Change.** Write (i)–(iii) as rules. Make the implementation compute Q_check chrF only after the stop, in one call, and record the stop block index before that call.

### R6 — REQUIRED — §4.1, §4.3 rule 1 (Q_check against the source pool)
**Problem.** ADR-0022 removes from the source pools every identity group used by Q, D_cal and D_con (`data.py:338-340`, re-check A R1). Q_check is now adaptive, up to 16 blocks, so the source pool's definition depends on how many blocks are drawn. If generation runs alongside, it is circular.
**Change.** Fix the order. Either draw Q_check to its stop before the source pools are defined, or reserve and block the groups of all 16 potential blocks (8,000 items) up front.

### R7 — REQUIRED — §4 (contents of Part Q), §6 seeds
**Problem.** Part Q is described as qualification and pool generation only. The P10-S2 data step also produced teacher outputs on E_A, E_B, D_cal (and E_C, E_open, D_con) (`prefreeze.py:126,170-173`), the student conversion and equivalence record (G8), the token-id bank, the tokenizer record, the truncation limit and the GEN window list. Part T needs all of these: the gap denominators, the pilot and G8. Nobody else may run the teachers after Part Q. The draft says neither where these artefacts are produced nor that teacher outputs on evaluation panels are stored, hashed and not scored. The seed list also lacks equivalents of P10-S2's 220910 (test (c) id sequences) and 220912 (equivalence injection vector, used but not in ADR-0022 §9). D-joint's initialisation has no offset (+8 says "stage 1").
**Change.** List every Part Q output and its hash in the manifest, including teacher outputs on E_A, E_B and D_cal, stored and not scored. Add the missing listed seeds and D-joint's offset.

### R8 — REQUIRED — §4.4 l. 121 (fallback)
**Problem.** A fallback language changes the gold pairs, the identity groups, the no-gold sources and the partition. So the qualified teacher's Part Q result does not carry over, and "passes the whole of Part Q on the same seeds with Spanish" leaves the surviving teacher's status unclear. The rule also does not say whether DATA-EXHAUSTED counts as "failed" for the fallback. With "first match wins", a quality failure of one teacher hides the other teacher's exhaustion.
**Change.** State that both teachers are re-qualified on the rebuilt partition and that the surviving teacher's earlier figures are printed but do not count. State whether the fallback applies to DATA-EXHAUSTED. Print a per-teacher status under the single label. Note that the Spanish Tatoeba files would be a later export, a new corpus (ADR-0022 §4.2, §14.1).

### R9 — REQUIRED — §8.3 RETENTION row 1 l. 246 (a failure can be hidden)
**Problem.** NOT EVALUABLE ("G_first(M1) < 0.50 in any cell") is checked before RETENTION-NEGATIVE. If M-append forgets catastrophically in all six cells and one M1 cell reaches G = 0.49, the line prints NOT EVALUABLE, and §15 says a NOT EVALUABLE line "is never read as negative".
**Change.** Evaluate the negative zone first, over the cells where G_first(M1) ≥ 0.50 and ρ is defined, with at least four such cells required. Or print the per-cell ρ table under every NOT EVALUABLE retention line, with a sentence stating how many evaluable cells are in the negative zone.

### R10 — REQUIRED — §8.1 l. 217, §8.2 RET and forgetting pressure l. 226–228, AGAINST-DENSE l. 252
**Problem.** (a) ρ(X) = G_first(after) / G_first(V1) has no guard for the dense arms: G_first(D1) can be small or ≤ 0, so ρ(D-seq), ρ(D-append) and Δρ become unstable or undefined. The forgetting-pressure count and AGAINST-DENSE both read them. (b) Forgetting pressure is met if **D-seq alone** fails RET in 4 of 6 cells. M-append's only threat is crosstalk inside a store with oracle task codes. A dense adapter that forgets does not show that the store's task can be forgotten through that channel. (c) A RET failure can be F > 0.03 with ρ = 0.95, a weak sign of "forgetting". (d) The RETENTION line does not require ACQ1's lexical margin and marker-only limit (table B).
**Change.** (a) Define ρ and RET for an arm only when G_first(V1) ≥ 0.50; otherwise mark that arm's cell NOT EVALUABLE with the reason. (b) Base forgetting pressure on M-seq (the same module type), with D-seq printed descriptively, or justify the "or" explicitly as a lead's choice for the human lead. (c) Consider pressure as ρ(unprotected) < 0.90. (d) Print ACQ1's status on the RETENTION line, or require ACQ1 for RETENTION-POSITIVE as ADR-0022 did.

### R11 — REQUIRED — §8.2–8.3 (can two people compute the same thing? task item 5)
**Problem.** Several reading points are left open. (i) In ACQ1, is "G" the full-panel G or the 300-item subsample G? ADR-0022 §7 computes control G values with the teacher and Stage 0 scores of the same subsample; the draft does not say. (ii) CONTROL-FAILED "in any cell": of which arms (M1, M-append, M-seq, M-joint, E-table)? (iii) ACQ2's "single-teacher module of the same type in the same replicate" is M1 or D1 of the **other** order; say so. (iv) RETENTION row 3 merges "second capability not acquired" with "no arm forgot" under one label.
**Change.** Settle (i)–(iii) in §8. Split (iv) into two labels: NOT CHALLENGED: SECOND NOT ACQUIRED and NOT CHALLENGED: NO FORGETTING PRESSURE.

### R12 — REQUIRED — §5.2 D-append l. 142, AGAINST-DENSE l. 252, §5.2 l. 159 (fairness, task item 6)
**Problem.** Parameters match (2,424,833 against 2,419,200 per stage). Updates, batch, data and the three-point rate grids match. The store also tunes its read layer (an extra two-way choice), which slightly favours the memory. The real asymmetry is **information**. The store is read with **task-specific oracle codes** u(t, w), so the task identity is supplied by rule inside the address. D-append applies both adapters on every task prompt, and gets the task only through the marker word in context. A retention advantage for M-append (Δρ ≥ +0.05, MEMORY AHEAD) could be produced by the oracle task code rather than by the memory. The draft removes ADR-0022's NO ADVANTAGE OVER SEPARATE ADAPTERS annotation. L-sep, the dense arm given the same oracle task information, then appears on no line. Separately, the learning rate is selected at 2,000 updates and then used at U, which may be up to 8,000. The P10-S1 lesson about matched compute (OUTCOME finding 4) is not carried over: AGAINST-DENSE is read at matched updates only.
**Change.** On the AGAINST-DENSE retention quantity, print the fixed qualifier "the memory receives the task identity by rule in its address; the dense arm receives it only through the prompt". Restore L-sep's scores beside the AGAINST-DENSE line (BY CONSTRUCTION for retention, empirical for acquisition), as ADR-0022's annotation did. Record that the read-layer search is an extra tuning dimension for the store. Print the counted training multiply-adds per update for both arms beside the line, since they are counts and read no wall time.

### R13 — REQUIRED — §5.4 l. 173, §1 l. 13, §8.3
**Problem.** The fixed line drops ADR-0022's "teacher-only training material verified by measured-precision filter". The human lead accepted the filter as verification in that sense and no other (ADR-0022 §18 item 4). The draft does not require "(n replicates, U = …)" on each line. The question (l. 13) does not say "under rule-supplied addresses". The human lead's instruction "S1 and S2 must not claim autonomous learned-memory success from oracle-assisted results" is not quoted.
**Change.** Restore the filter clause. Add "(3 replicates, U = …)" and NOT CONVERGED AT U where it applies. Put "under word-level addresses supplied by rule" into the question and the title line. Quote the instruction in the header.

### R14 — REQUIRED — §10 stage 2, §11 item 4 (Part Q rehearsal reveals the quality outcome)
**Problem.** A Part Q rehearsal "end to end" on rehearsal seeds is a full qualification of the same teachers on another partition of the same corpus. It shows Q1–Q4 and the yields before the registered Part Q, which opens the way to redesign after a peek.
**Change.** Either rehearse Part Q on stand-in teachers, or on a small subset (for example two blocks) with the Q1–Q4 values computed but sealed and not shown. State that no Part Q setting, threshold or size changes after the rehearsal. State the rehearsal's own charge and whether it counts against the 10-hour cap.

### R15 — REQUIRED — §12 l. 311
**Problem.** "None needed while present" for the data-generation packages. The human lead's approval to run eight packages outside the lock was given for P10-S2's one-off data step (ADR-0022 §18), and `CLAUDE.md` allows `--with` only for analysis-only tools. Files being present on disk is not approval to use them in P10-I-S2's registered Part Q. The human lead also recorded that the P10 delegation does not cover P10-I (ADR-0022 addendum, 2026-11-16).
**Change.** Add to §13: "Use of the hash-pinned data-generation packages outside the lock for Part Q", for the human lead's decision.

### R16 — REQUIRED — §4.4, §8.4 (status for Part Q)
**Problem.** Part Q has no ENGINEERING-FAILURE row. Rule 7 asserts a teacher-output digest at every resume, but a mismatch has no stated consequence. G1, hash and generation-configuration failures have none either. P10-S2 attempt 5 ran without the pinned `renormalize_logits`.
**Change.** Add QUALIFICATION-ENGINEERING-FAILURE (first row) for a digest mismatch at resume, a failed G1, a hash mismatch, or an applied generation configuration that differs from the pinned file. Record the applied configuration, as P10-S2's final attempt did.

### R17 — REQUIRED — §1 l. 21 against §4.4 l. 116
**Problem.** The outcome table lists PAUSED as an "Inconclusive" outcome of QUALIFICATION. §4.4 and `DIRECTION.md` §5 rule 1 say PAUSED is not an outcome.
**Change.** Remove PAUSED from the Inconclusive cell.

### R18 — REQUIRED — §8.4 l. 260, §4.1
**Problem.** The recomputation tolerance and its consequence are not carried over (table B). There is no rule if E_A or E_B has fewer than 1,000 (or 500) items on the new partition.
**Change.** Carry over ADR-0022 §13.3's recomputation rule by citation, with the tolerances. Add ADR-0022 §5.2's minimum panel sizes, with QUALIFICATION-INCONCLUSIVE: DATA-INSUFFICIENT below them.

### A1 — ADVISORY — task item 4 (transfer measure and lookup baselines)
- **Constructible: yes.** Training sources are restricted to English whose normalized and contraction-expanded strings are not on the evaluation side (`data.py:253-258`). Evaluation items are evaluation-side identity groups (`data.py:278`). Training outputs equal to an evaluation reference are dropped (5 and 1 in P10-S2). So R-exact has zero hits by construction, and G1 checks it.
- "Lexical composition only" is honest scoping. In the stricter sense, the frozen student supplies word order and morphology, and the store supplies per-word target information. Keep §0-style wording that it is not transfer of a skill.
- E-table is a strong trained lookup: it has task-specific vectors, positions and gate identical to the store's and its own rate search. Its parameter count is 1,152,577, about half the store's, which makes the baseline weaker. With E-table in b, MEMORY ADDS OVER LOOKUP cannot pass trivially.
- R-gloss, which outputs word by word, is a weak untrained baseline for chrF in German and French. The non-learned analogue of a word-addressed store is a **lexicon in the student's context**: the top gloss of each source word in the prompt. Consider adding it as R-gloss-icl. Also state that R-gloss, R-nn and R-icl use the replicate's training draw (as `retrieval.py` does), not the whole accepted pool.
- If LOOKUP SUFFICES, the milestone line itself should carry "a trained word table does as well", not only the line beneath it.

### A2 — ADVISORY — §4.4 l. 121, §13 item 2 (one teacher)
"Part T does not run with one teacher" is defensible for the milestone. The alternative of a one-teacher ACQUISITION-only lane, with RETENTION NOT EVALUABLE, is not offered. P10-S2 never tested acquisition at all. Offer it to the human lead with its cost.

### A3 — ADVISORY — §7.1 (calibration and convergence)
Convergence is checked on M1 and D1 only, not on the stage-2 arms. Name the calibration seed(s) the ladder uses. Structure 251001–251999 as bases plus offsets (ADR-0022 used 221001 + 100·i). The ladder count is 36 units, not about 30 (§A).

### A4 — ADVISORY — §14 l. 337, §9 (Part Q cap)
The 10-hour cap is set from rates at the default thread count (18 physical cores on this machine; `sysctl hw.physicalcpu`). Part Q runs at 6 threads and may be about 2–3× slower, so 5.6 h could become 11–17 h. The cap is a resource cap, so this only means PAUSED, but say so. Alternatively set Part Q's cap as P + 2R from the Part Q rehearsal, as Part T's is.

### A5 — ADVISORY — §2 l. 41
P10-S1's DENSE AHEAD is quoted without OUTCOME finding 4: at matched compute, F-OQ was ahead of D-OQ at 32K/16K in 5 of 5 replicates. Add the caveat.

### A6 — ADVISORY — §5.2, §8 (dropped annotations)
ROUTER (keyword-level) QUALIFIED (route accuracy ≥ 0.99), APPEND COST, EXACT-MATCH WEAK and the seen-item scores are dropped or reduced without being listed in §3. GEN depends on the router, so print route accuracy beside GENERAL-QUALITY. E_open is built but used nowhere: use it descriptively or drop it. MA-gold's removal is defensible, since the design is teacher-only, but list its loss: TEACHER-EQUIVALENT-TO-GOLD.

### A7 — ADVISORY — §11 (engineering lessons)
The list is good: the frozen-worktree incident, per-item persistence, resumability, rehearsal on the frozen plan, final-snapshot reading, a reference arm through every validity check. Add from P10-S2: assert that the applied generation configuration equals the pinned file (attempt 5), and check every fixed-input count before generation (attempt 4). Use separate frozen-input sets for Part Q and Part T, so that Part T code changes cannot invalidate a Part Q resume or recomputation. Have the independent Part Q recomputation also regenerate a random subsample (for example 1,000 sources) at 6 threads and compare digests. A recomputation from stored outputs cannot check generation.

### A8 — ADVISORY — task item 10 (seeds)
Namespace 250001–259999 is disjoint from P10-S0 (200001–209999, 2001–2002, 2091–2092, 920001–920999), P10-S1 (210001–219999, 2101–2193, 921001–921999), P10-S2 (220001–229999, including 220912), and P1–P9-II as listed in ADR-0021 §6.3 and ADR-0026 l. 95. It is also disjoint from the siblings: ADR-0023 (300001–309999, 3001–3002, 3091–3092, 930001–930999), ADR-0024 (240001–249999, 2401–2405, 2491–2493, 924001–924999), ADR-0026 (260001–269999, 2601–2603, 2691–2692, 926001–926999), ADR-0027 (270001–279999, 2701–2799) and ADR-0028 (280001–289999). A scan of `src`, `studies`, `configs` and `tests` found 25xxxx only inside hexadecimal digests (`studies/p10s0/freeze/plan.json`, `studies/p10s2/requirements-datagen.txt`, `studies/p10s2/records/tatoeba_session.json`). Unlike the siblings, ADR-0025 places its test seeds inside its own namespace (259001–259999), as ADR-0022 did. That is consistent, but the six drafts should agree on one convention.

### A9 — ADVISORY — §10, §7 (machine load; task item 9)
"No registered rule reads wall time" is true of the draft as written, and recording the load average meets `DIRECTION.md` §7. If B1 restores logical cost counts, they read no wall time either. If any wall-time line returns, it needs a quiet-machine stage.

### A10 — ADVISORY — §13 item 11, §12 (downloads; task item 11)
Correctly reserved: whether the under-30 GB delegation covers P10-I (the human lead recorded that the P10 delegation does not cover P10-I); the fallback teacher and Spanish files (323.4 MB); the durable location of the data. The note that the Tatoeba exports cannot be fetched again byte for byte is correct and important. Also note that WikiText-2 is in the main checkout's `data/wikitext2/` and in the P10-S2 agent worktree. It is not in this worktree; P10-S2 attempt 2 failed on exactly this.

## D. Commands and environment

```
python3 -I /private/tmp/claude-501/-Users-daniellaloush-dandush03-ArborLM--claude-worktrees-arborlm-consolidation-experiment-2b31c1/cfc0efd5-b7ca-4602-959a-07fe6b8d4e7d/scratchpad/rev0025/checks.py
python3 -I -c '<read-only json dumps of results/p10s2-datagen-2026-11-16/prefreeze_record.json and of the bundle under agent-a91c79a181109bb9c/data/p10s2-pre-20261115/>'
grep / sed over the files listed in the header; sysctl -n hw.physicalcpu (18)
```

Python 3.15.1, Darwin arm64, standard library only. No package from the repository was imported. The intersection bound and the conditional-acceptance estimate in R4 are my own estimates from recorded counts, not measurements. The exact sample overlap would need the partition to be rebuilt, which I did not do. No failed checker attempt occurred.

`Astra review: NOT_PERFORMED`. This review is not human approval.
