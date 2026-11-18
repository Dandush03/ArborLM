# Independent specification review of ADR-0024 (P10-I-S1: capacity scaling; frozen-checkpoint routing diagnosis)

**Verdict: NOT READY.** Two blocking findings: the U_P rule and the rate search depend on each other (F1), and Lane R's decision table assigns causes the reads cannot identify (F2). Fifteen findings are REQUIRED and twelve are ADVISORY. Most of the draft is careful and honest. Its disclosures are better than any earlier P10 draft's, and nearly every number it quotes checks out. The problems are in the rules, not the prose.

- Reviewer: the `arbor-auditor` subagent. Model as I know it: Claude Opus 5.5 (`claude-opus-5-5`). I did not write any part of the draft or of P10-S1.
- This is an independent engineering and mathematical review. It is **not** Astra validation and **not** human approval. `Astra review: NOT_PERFORMED`. Claude review is not Astra review.
- Draft reviewed: `docs/decisions/ADR-0024-p10-i-s1-capacity-scaling-and-routing-diagnosis.md`, sha256 `40c6876dd39c55b21416924ae491e04f505e8024a5c9a8f76e49f0b5c9aa5008`, 482 lines, untracked, in worktree HEAD `c525898` (branch `claude/p10-i-specs`).
- Scientific choices are flagged **PENDING LEAD REVIEW**. I choose no hypothesis, threshold or gate.

## 0. Method, environment and commands

- Machine: Darwin 27.2.0 arm64. Interpreter: Python 3.15.1 (`/opt/homebrew/bin/python3`), stdlib only, run with `-I`. My scripts import nothing from `arborlm`, `studies` or the P10-S1 audit library (`auditlib.py`).
- Scripts were written in the session scratchpad (`/private/tmp/claude-501/-Users-daniellaloush-dandush03-ArborLM--claude-worktrees-arborlm-consolidation-experiment-2b31c1/cfc0efd5-b7ca-4602-959a-07fe6b8d4e7d/scratchpad/`). The scratchpad is not durable, so the logic that carries weight is reproduced in the Appendix.
  - `python3 -I r1_retention.py`: the RESTORED rule of §14 in accuracy terms.
  - `python3 -I r2_depc.py > r2_depc.out`: DEP-c of §9.1 on every recorded read of P10-S1 attempt 2.
  - `python3 -I r3_crowding.py`: theoretical code crowding for i.i.d. unit codes of width 16.
  - `python3 -I r4_cost.py`: seconds per update from `results/p10s1-run-2026-11-17/manifests/train.manifest.json` and each cell's `train.json`.
- Run directory, read-only: `/Users/daniellaloush/dandush03/ArborLM/experiments/P10S1-registered-attempt2-20261117`.
  - I read the recorded counts in `eval.json` (correct, useful, n, disabled_correct), the NO-MEMORY counts in `baselines/*.json`, `train.json` metadata, and snapshot listings.
  - **I computed no routing statistic and opened no recorded recall value.** For `tree_recall_of_exhaustive_top8` and `ivf_measured.recall_of_exhaustive_top8` I printed key names and presence counts only (F11).
- Code read: `studies/p10s1/{model,index,evaluate,analysis,core}.py`, `studies/p9/model.py` (`_top_flat`, `_top_tree`, `select`, `delta`), and `studies/p9/core.py` constants.
- **Failed attempt, kept.** One `grep -o` with a long Unicode-class pattern, used to list the seed lines of the sibling drafts, failed with "exceeds complexity limits". I re-ran the search in Python. There was no other effect.

---

## A. U_P against the run length (the human lead's point A)

**Is the reading sound?** Partly.

- A diagnosis of what limits a trained memory is better made late in training. That part of the argument is sound.
- The draft's own reason depends on an untested premise: "where missing training is least likely to be the answer."
  - T-OQ rose from 0.469 to 0.769 at 8K/4K and from 0.401 to 0.697 at 32K/16K between U_P and the run length (audit §6).
  - Nothing in the draft checks that T-OQ (or F-OQ) has plateaued at the run length.
  - If the tree is still rising, the run length is not where missing training has been excluded.

**Can it be bent?** The rule is mechanical:
- run length primary;
- U_P registered beside it;
- CHECKPOINT-DEPENDENT if either label differs;
- intermediate checkpoints descriptive.

No rule lets a checkpoint be picked after the fact. But the primary choice still carries weight downstream:
- R-CONFIRM compares only the run-length pair (§15).
- The "recommended next action" is the run-length one, plus a note (§14).
- Open choice 8 lets a Stage B study be proposed on R-DIAGNOSIS alone, which is the run-length pair.

So the checkpoint chosen knowing the data decides what Stage B is pointed at.

**Was it chosen knowing the data, and does that tilt the result?** Yes, and the draft admits it, but only in §24, the note to reviewers. Its effect on Lane R's labels is not neutral. All Lane R labels compare a read with F0, not tree with index. My recomputation from the audit's mean a_use (`r1_retention.py`):

| Primary cell | T0 gap to F0, U_P → run (bits) | Index (I256@512) gap to F0, U_P → run (bits) | a_use a read needs to be RESTORED, U_P → run |
|---|---|---|---|
| 8K/4K | 3.08 → 1.87 | 2.23 → 2.27 | 0.920 → 0.974 |
| 32K/16K | 3.11 → 2.28 | 2.73 → 3.17 | 0.885 → 0.969 |

Reading the table:
- At the run length the tree's gap shrinks by 0.8–1.2 bits and the index's grows. That makes the tree rows of §14 (PARTLY RESTORES) more reachable.
- It also makes INDEX DOES NOT APPROACH FLAT more likely. F0 sits at the ceiling (0.996 and 0.992), so RESTORED needs a_use of about 0.97.
- The primary choice therefore leans toward "fix the router" over "investigate a separately trained index". I cannot tell which way the drafter would prefer, but the lean is real.

**Required (F8).**
- Make the two checkpoints **co-primary**. R-DIAGNOSIS is the common pair when U_P and the run length agree. Otherwise it is CHECKPOINT-DEPENDENT with both pairs and **no single recommended next action**.
- Register an objective plateau check at the run length: i\*(run) − i\*(run/2) ≤ 0.10 on both panels, for T-OQ and F-OQ at each primary cell, using the existing snapshots. Print TREE STILL LEARNING where it fails.
- Move the §24 disclosure into §14.

**Is a confirmatory read on fresh checkpoints required for any claim?**
- Not for choosing where Stage B looks. For any statement about cause ("the tree's gap is caused by X"), yes.
- The new reads (T1–T3, Tv, I64@c, attention mass) have not been printed. That makes Lane R partly blind, which is better than the draft says.
- But the thresholds and the primary checkpoint were fixed knowing T0 and F0 for the same five draws. And two recall quantities already sit in the raw records (F11).
- R-CONFIRM as drafted has gaps, and both must close (F9):
  - It depends on Lane C being funded.
  - It does not fix block B's U_P and run length to P10-S1's 8,192/49,152 and 16,384/98,304. Under §8, block B would take ADR-0024's own U_P, so its checkpoints are not "the same checkpoints".

## B. The candidate-recall measurements (the human lead's point B)

**What the code does** (`studies/p9/model.py` `_top_tree` and `select`; `studies/p10s1/model.py`; `studies/p10s1/index.py`):

- **Query.** For R1 the query is the fixed oracle unit code of the record (`_query` returns `_oracle_codes`), with no learned query projection. "The query does not depend on the context" is correct.
- **Tree read.**
  - `routes = q·normalize(router)ᵀ / 0.2`. The two best branches are taken with `stable_top` (ties go to the lower id).
  - Candidates are the 2 × 256 keys of those branches, scored `cos/0.2 + log_softmax(routes)[branch]`.
  - The top 64 are kept and `selected = top-8`. Weights are the softmax of the eight scores (`delta`).
  - The prior is a **per-branch constant**. Softmax is invariant to a common shift, so the prior changes weights **only between slots of different branches**, and selection only at the branch boundary.
  - Consequences:
    - Tv with v = 1 gives *identical* selection and weights with priors on and off.
    - Whenever all eight selected slots lie in one branch, the prior's total-variation effect is exactly zero.
    - "Priors distort retrieval weights" can therefore act only through cross-branch reweighting and boundary selection.
  - None of this is stated in §12/§13. It should be, and the v = 1 identity makes a free exactness gate (F21).
- **"All candidates with priors on" (T3) is well defined.** `log_softmax` is over all branches, so every key has a prior. Because the prior is a soft branch restriction, though, T3 removes the hard candidate restriction while keeping a soft one. With a confident router (temperature 0.2, 16 or 64 branches), T3 may differ little from T0. T2 is the only read that is "exact search" in the note's sense.
- **Index.** k-means with N/256 lists by default. Lists are visited in descending centroid cosine until **at least** c keys are collected, so the candidate count is a minimum, not exact. Then the masked top-8 by cos/0.2.
  - For a flat memory with no prior, any element of E8 inside C is in the selected top-8. So SR8 = CR8 and AM_S = AM_C for every index read, and the draft's sentence "a loss of quality is then a loss of recall by construction" is correct.
- **Feasibility.**
  - Tree: N/256 branches; 4 at 1,024 slots, 16 at 4,096, 64 at 16,384.
    - Tv with v = 8 is **infeasible** at 1,024 slots, and v = 4 there equals T3/T2.
    - The draft says only that "a budget of 128 is not defined for a tree" (F21).
  - I64@c at 1,024 slots: 16 lists of about 64 keys, c ∈ {128, 256, 512}. At 4,096 and 16,384 all five budgets are feasible.
  - The loaded cells 8K/1K and 32K/4K are covered.
  - All checkpoints named in §11 exist on disk for the 70 F-OQ/T-OQ cells, including 98,304 and 393,216 at 32K/4K.

**Does the 2 × 2 separate the three explanations?** Not as the label table uses it (F2, blocking).

1. **No partial-priors row.** Row 3 needs T1 fully RESTORED. Row 5 (PARTLY) considers only T2/T3. Suppose T1 closes 80% of the gap and T2/T3 each close less than 50%: the result is row 6, "EXACT SEARCH DOES NOT RESTORE → improve memory training", although the priors explain most of the gap.
2. **Read/train mismatch is labelled "content poorly learned".** In a jointly trained tree, a slot outside the router's branches for fact f never received f's gradient. Its key's cosine to q_f is just whatever it is. Exact search (T2) can therefore pick slots that were never trained for f, so i(T2) < i(T0) is possible.
   - In that case g < 0 and row 6 says "improve memory training and representation". The cause is not identified: the content may be fine for the read it was trained under.
   - CR8, AM_C and AM_S of T0 are printed but enter no rule, so the table cannot tell "the router misses the entries that hold f" from "exact search ranks entries that do not hold f".
3. **"T2 or T3" mixes two different interventions.** Suppose only T2 restores (not T1, not T3). Then removing both priors and the restriction is needed, which is a joint cause, but row 4 maps it to "improve the router and candidate coverage".

**Required change for F2.**
- Define g_P = g(T1), g_C = g(T3) and g_PC = g(T2), with g as in §14.
- Use these labels:
  - PRIORS (T1 restored, or g_P ≥ 0.5 with g_C < 0.5);
  - CANDIDATES (T3 restored, or g_C ≥ 0.5 with g_P < 0.5);
  - JOINT (only T2 restored, or g_PC ≥ 0.5 with g_P, g_C < 0.5);
  - BOTH SEPARATELY;
  - EXACT SEARCH HARMS: i(T2) ≤ i(T0) − 0.25, printed as **NOT SEPARABLE AT READ TIME**, with no next action;
  - CONTENT: g_PC < 0.5 **and** CR8(T0) ≥ a registered floor. Without high recall, "content" is not identified.
- A CR8 floor is a new threshold, **PENDING LEAD REVIEW**.

**Index label (F3).** The draft says N/8 is "the share of keys the tree scores at 4,096 slots (512), the equal-candidate standard of ADR-0021 §8.5". The equal-candidate standard is a **fixed 512** (ADR-0021 F-OQ-IVF, "at least 512 candidates"), not N/8.
- At 32K/16K, N/8 = 2,048: four times the tree's 512 candidates, and the largest budget read.
- So INDEX APPROACHES FLAT ONLY ABOVE N/8 is **unreachable at a primary cell**, and SPARSE INDEX APPROACHES FLAT would be granted at four times the tree's budget.
- Use 512, the tree's candidate count, as the standard, or print both. The labels must use the *measured* mean candidate count beside the nominal c.

**Is the decision table computable, every row reachable, nothing unlabelled?**
- There is a catch-all (MIXED) and NOT EVALUABLE, so nothing is unlabelled.
- NO GAP is defined but practically unreachable at the primary cells: the gaps are 1.9–3.1 bits. That is acceptable.
- Not stated:
  - whether a replicate whose g is undefined (no gap) counts against rows 3–6;
  - the denominator when one replicate is NOT EVALUABLE (F24).
- The index label is fully computable once F3 is fixed. ONLY ABOVE N/8 is unreachable at 16,384 slots as drafted.

**Recall against "exact search of the same checkpoint".** It is defined correctly and is honest about what it is. For the tree it is recall of what the tree's own keys rank first, which is exactly why it cannot carry the CONTENT inference unaided (point 2 above).

## C. Can the lines stay independent? Count, and my judgement (the human lead's point C)

**Count (from the draft).**

| Item | Count |
|---|---|
| Lines of text | 482 |
| Registered outcome lines | 4: C-CAPACITY, C-SATURATION, C-EFFICIENCY, R-DIAGNOSIS. A fifth registered print, R-CONFIRM |
| Trained arms | 5: F-OQ, T-OQ, PK-OQ (new), D-OQ, R2 |
| Evaluation-only arms | 6: F-OQ-IVF, DICT, no-memory, unseen control, KNN-W, KNN-W-IVF |
| Lane R reads per checkpoint | about 27: T0–T3; Tv with 4 visit counts × priors on/off (8, partly duplicate); F0; I256@512; I64@c with 5 budgets × 3 index seeds |
| Lane R checkpoints | 70 cells × 4 (2 labelled, 2 descriptive) = 280 |
| Trained cells | 240: block M 155, block X 65, block B 20 |
| Blocks | M, X, B; plus the calibration searches (U_P ladder, a five-rate grid for five arms over the slot units and each loaded cell, run-until-full load search) and the rehearsal |
| Distinct verdict, class and label values | over 70. Every cost-dependent efficiency and dense verdict is doubled (E-A/E-T, MC-A/MC-T) |
| Open choices for the human lead | 11 |
| Approval points | 7: Lane R approval, Lane C approval, block X funding, Decision 2 per lane, acceptance per lane |

**Judgement.**

- **Lane R should be its own ADR.** I agree with the drafter, and there is one more reason he does not give.
  - Each lane's freeze record hashes "this ADR" (§20).
  - If Lane R freezes first (open choice 10), any later change to the Lane C half before Lane C's freeze changes a frozen input of Lane R, or forbids Lane C's pre-freeze amendments.
  - That is the failure mode that cost P10-S1 attempt 1 (a commit to a frozen ADR stopped 171 cells).
  - §20's "amended only by separate record files" softens this but does not remove it. Lane C *must* be amended before its own freeze, at least with calibration outcomes.
  - DIRECTION/LITERATURE note §5.4 (the human lead's direction) places the lane inside ADR-0024. Splitting needs his ruling (open choice 9). Until then, at minimum, each lane's freeze must hash a **per-lane extract** and not the whole file (F12).
- **A split Lane R ADR should carry its own confirmation set:** F-OQ and T-OQ at 8K/4K and 32K/16K, five fresh draws, rate 0.003, P10-S1's U_P and run lengths. At this run's per-update costs that is about 7 charged hours (F9).
- **Smallest coherent Lane C (my engineering view; PENDING LEAD REVIEW):**
  - block M only: the seven cells plus 2K/256;
  - F-OQ, T-OQ, D-OQ, R2, with F-OQ-IVF evaluation-only;
  - five replicates and the equal rate search;
  - DEP-c at every snapshot (F6);
  - the explicit dense and speed rules with all readings printed;
  - run-until-full at the loaded cells.
- That answers what the acceptance carried into P10-I-S1 (early-snapshot DEP, the cell-combination rule, the matched-compute observation, the seed-block defect), with tuned rates. Roughly 20–30 charged hours (F10).
- **PK-OQ** is a new architecture whose only role is a descriptive sparse-arm comparison. The note's §5.2 lists it under Stage B. I would defer it (F13).
- **Block X** costs about twice all of P10-S1. The lead's own registered expectation is CAPACITY-NEGATIVE (b) (§10.3). It is a candidate for a separate, conditional specification after block M, with an entry criterion such as "an arm is CAPACITY_SUPPORTED at block M and not DENSE AHEAD (arm)". Whether to condition it is **PENDING LEAD REVIEW**.
- **A structural point for whoever decides.** Under the draft's every-cell arm rules, adding cells makes **both** decisive outcomes harder. With block X, DENSE AHEAD (arm) needs DENSE HOLDS MORE at *every* loaded cell, now three. Block X therefore raises the chance of INCONCLUSIVE.

---

## Numbered findings

Severity: **BLOCKING** (cannot be approved as written), **REQUIRED** (must change before approval), **ADVISORY**.

### F1. BLOCKING — U_P and the rate search depend on each other; R2's rate unit is undefined
- **Location.** §7 (rate unit table: "Readout at the row's U_P"); §8 (U_P "at the calibrated rates").
- **Problem.**
  - The rate of every non-loaded unit is chosen by a_use at the row's U_P. U_P is defined as the smallest ladder value at which F-OQ and R2 pass, *at the calibrated rates*. Neither can be computed first, and an implementer would have to invent the order.
  - The unit table is by slot count (1,024, 4,096, 16,384, 65,536). R2's cells (2K/4K, 8K/16K, 32K/32K, 128K/128K) are not all in it: 32,768 and 131,072 slots have no unit.
  - D-OQ's 1,024-slot unit names 2K/1K, where D-OQ is not a registered cell.
- **Change.** Register an explicit order. For example:
  1. select the rates at a provisional readout fixed now (P10-S1's 8,192/8,192/16,384, or a stated multiple);
  2. then compute U_P at those rates;
  3. if U_P differs from the provisional readout, re-select once at U_P and stop (no further iteration);
  4. print both.

  Also define R2's selection cells and D-OQ's 1,024-slot unit (or state that D-OQ is calibrated at 2K/1K as a calibration-only cell). PENDING LEAD REVIEW on the order chosen.

### F2. BLOCKING — Lane R's tree label misassigns causes
- **Location.** §14, tree label table, rows 3–6 and the "next action" column.
- **Problem** (detail in section B).
  - There is no partial-priors row.
  - Exact-search harm (read/train mismatch) is labelled "improve memory training".
  - Only-T2 (joint) is labelled "router and candidate coverage".
  - CR8 and AM enter no rule, so "content poorly learned" is never identified.
  - The lane's stated purpose, which is to separate the note's three explanations, is therefore not met.
- **Change.** Replace rows 3–6 with the g_P, g_C, g_PC decomposition and the labels listed in section B, including EXACT SEARCH HARMS → NOT SEPARABLE AT READ TIME. Gate the CONTENT label on CR8(T0) being high, at a registered floor (PENDING LEAD REVIEW). State in §12 that the prior acts only across branches (Tv v = 1: priors on ≡ off).

### F3. REQUIRED — N/8 contradicts its own reason and makes a label unreachable at 32K/16K
- **Location.** §14, index label table.
- **Problem.** See section B. The equal-candidate standard is 512, not N/8. At 16,384 slots N/8 = 2,048 is the top budget, so ONLY ABOVE N/8 cannot occur.
- **Change.** Use 512 (or "the tree's candidates, 512 keys plus N/256 router scores") as the sparse standard, and print c\* against both 512 and N/8. Define c\* on the nominal minimum and print the measured mean and 99th-percentile candidate counts. Optionally require restoration at c\* and every larger budget.

### F4. REQUIRED — Matched compute made primary after seeing it favour F-OQ
- **Location.** §10.2.
- **Problem.**
  - ADR-0021 §8.5 row 1 made DENSE AHEAD fire on *any one* of MU, MC, D-BEST. The draft lets MU and D-BEST decide nothing, and makes STORE NOT BEHIND (needed for CAPACITY-POSITIVE) depend on MC-A and MC-T only.
  - This was chosen after seeing MC favour F-OQ in 5 of 5 replicates while MU (4 of 5) and D-BEST (5 of 5) favoured D-OQ. For a positive, it is a relaxation in the store's favour.
  - The guard "this change alone cannot produce a positive" holds **only on P10-S1's saturation numbers** (D-OQ ahead by 1.76–1.87 bits). It is not a property of the rule. With tuned memory rates on fresh seeds the saturation gap is unknown.
  - The reason itself (an update is not a resource) is sound. MU gives D-OQ 1.74× (CPU) to 2.5× (multiply-adds) the compute, so a store that is not behind at MU is *more* convincing, not less.
- **Change (defensible registration).**
  - A store-favouring dense label (STORE NOT BEHIND) needs d > −0.25 in **MC-A, MC-T and MU**.
  - DENSE AHEAD (the blocking side) needs MC-A, and MC-T where measured, as drafted.
  - D-BEST stays descriptive: it gives D-OQ up to six times the updates against the store at U_P, and the saturation reading already compares each at its full length.
  - This keeps the principled primary reading, removes the post-observation relaxation of the positive, and states the asymmetry openly.
  - The alternative of all three readings for a positive and MC for a negative has the same effect. PENDING LEAD REVIEW (open choice 4).

### F5. REQUIRED — The efficiency rule's effect on P10-S1 is not disclosed
- **Location.** §10.5, last paragraph ("Applied to nothing in P10-S1").
- **Problem.**
  - For a positive, "DENSE NOT FASTER at every cell" is the same as the old any-cell block. The change is entirely on the negative side, and it makes NEGATIVE harder.
  - The rule is symmetric and computable. Checking it: the positive needs NOT FASTER at every FASTER-STEP cell in both readings; the negative needs FASTER at every cell in both readings, or NOT_SUPPORTED for both arms in both readings. The replicate counts (5 of 5 against 4 of 5) follow ruling (h).
  - On P10-S1's records (audit §3):
    - at 2K/4K, D-OQ is faster in both cost readings (CPU ratio 0.083–0.118, multiply-adds 0.32–0.46);
    - at 8K/16K, it is faster in CPU (0.27–0.38) and not faster in multiply-adds (1.32–1.87).
  - Under the draft, P10-S1's registered EFFICIENCY-NEGATIVE would become **EFFICIENCY-INCONCLUSIVE (DENSE SPEED SPLIT; READINGS DISAGREE)**. The measured-CPU reading says dense is faster at both cells.
  - Rows 1–2 (ENGINEERING, PAUSED) of the outcome table are missing; the table starts at row 3.
- **Change.** State this counterfactual in §10.5 beside the rule, with the per-reading split. Add rows 1–2.

### F6. REQUIRED — DEP: the snapshot change weakens ruling 22 (g) without saying so; the read list omits i\*'s snapshot; DEP-c is inert on P10-S1
- **Location.** §9.1 "Where DEP is read"; §10.1 "Snapshots read by DEP".
- **My derivation of DEP-c.**
  - Under the null that a fact the store has not usefully retained is answered right only by the backbone, c − u ~ Binomial(m, p₀) with m = n − u. p₀ is the backbone's rate, b/n.
  - In the records, b (NO-MEMORY) equals `disabled_correct` in every one of 4,394 reads, as G5's identical logits imply.
  - (i) is a one-sided test at 10⁻⁴, but with p⁺ = (upper end of the G2 interval)/n in place of p₀. p⁺ is 0.0488 at n = 2,048, 0.0397 at 8,192 and 0.0354 at 32,768, against b/n of about 0.028–0.031. (ii) is an effect-size floor of 1% of n above m·b/n.
- **Recomputed on every recorded read of P10-S1 attempt 2** (`r2_depc.out`; 3,210 registered and 1,184 seed-block snapshot-panel reads):
  - DEP-c fails **0 of 4,394** reads, with no a_use floor applied.
  - **All 32 reads that failed the 0.95 condition pass**, including the four F-OQ N2 snapshots (8K/16K r2 A/B and 8K/4K r4 A/B at 2,048 updates) and all 12 of R2's.
  - R2 passes at every one of its 150 reads (largest excess +0.0038 of n).
  - The largest excess on any memory read is +0.0101 of n, a T-OQ 2K/1K r5 Panel B read at a_use 0.055, below the DEP floor. It fails (ii) alone, and (i) passes there (z = −2.90).
  - The z-scores of the 32 former failures against p⁺ run from −8.27 to −1.69.
- **How strong a violation DEP-c detects** (fail needs c − u at least): n = 8,192 and a_use 0.5, an excess of 1.2% of n above m·b/n; n = 2,048 and a_use 0.25, 3.0% of n. It is not powerless. A generic answer bias that makes 5% of non-retained facts correct is caught at n = 8,192 and a_use 0.5.
- **Problem.**
  1. "Enters a verdict only at the snapshots that verdict reads" is the reading that ruling 22 (g) explicitly rejected in favour of "every snapshot up to the run length (the stricter reading)". The draft gives one sentence of reason and does not say it reverses 22 (g).
  2. By itself that change would have turned P10-S1's F-OQ into CAPACITY_SUPPORTED and the outcome into CAPACITY-NEGATIVE (b) (audit `a4_dep_sensitivity.out`, mode "read"). Stacked on DEP-c it is redundant, because DEP-c alone already clears every P10-S1 failure.
  3. The §10.1 list (U_P, U_MC, last two ladder points) omits the snapshots that attain i\*(N; U_run) and i\*(N; U_run/2). i\* is a maximum over all snapshots, so those are snapshots "whose values the verdict reads". The audit's "read" mode included them.
  4. The draft says DEP-c was not recomputed on P10-S1. It now has been, and the record should say it is inert there.
- **Change.**
  - Keep ruling 22 (g): DEP-c is read at every snapshot up to the run length. On P10-S1's data this costs nothing, and it avoids a second post-observation weakening.
  - If the lead keeps "only where read", state that it reverses 22 (g) and give the audit's counterfactual, and add the argmax snapshots of i\* to every list.
  - Record the result above in §9.1. Restate the a_use ≥ 0.25 applicability floor of ADR-0021 §8.1 (F26).

### F7. ADVISORY — DEP-c's stated reasons
- **Location.** §9.1 "Reasons for the figures".
- **Problem.**
  - (a) "10⁻⁴ gives fewer than one false failure in 2,289 evaluations" treats 10⁻⁴ as the per-test rate. Under p⁺ the real rate is far lower, and (i) and (ii) use different nulls (p⁺ and b/n).
  - (b) "An unexplained share of 1% moves i by at most about 0.09 bits" is wrong in two ways.
    - c − u does not enter i at all, because i is computed from u.
    - If the 1% were moved into u, di/da = log₂(31·a/(1 − a)), which exceeds 9 bits per unit of a above a_use 0.943. One percent then moves i by 0.09–0.15 bits near the ceiling, which reaches the 0.10 plateau limit.
- **Change.** Use p₀ = b/n (paired, the same panel) in (i). Better still, use a paired count: the non-useful facts correct with memory against the same facts correct with memory disabled, which needs per-fact records. Or keep p⁺ and state that it is deliberately conservative. Rewrite the 0.01 reason.

### F8. REQUIRED — U_P / run length in Lane R
- **Location.** §14 "Two checkpoints, two labels, one primary"; §24 item 1.
- **Problem and change.** See section A: co-primary checkpoints; no single next action when they differ; a registered plateau check (TREE STILL LEARNING); the disclosure moved into §14.

### F9. REQUIRED — R-CONFIRM is not a like-for-like confirmation and depends on Lane C
- **Location.** §5 block B; §15.
- **Problem.**
  - Block B's U_P and run length follow ADR-0024's §8, not P10-S1's.
  - If Lane C is not approved or funded, R-CONFIRM is NOT RUN forever.
  - CONFIRMED compares the run-length pair only.
  - If the calibrated rate happens to be 0.003, block B duplicates registered cells with identical seeds (F20).
- **Change.**
  - Fix block B's lengths at 8,192/49,152 (8K/4K) and 16,384/98,304 (32K/16K), with the same snapshot schedule.
  - CONFIRMED needs both pairs to match, or the same CHECKPOINT-DEPENDENT structure.
  - If Lane R becomes its own ADR, move block B into it. 20 cells cost about 7 charged hours at P10-S1's per-update costs (8K/4K 49,152 × 0.0091 and 0.0129 s; 32K/16K 98,304 × 0.0124 and 0.0147 s; five replicates; divided by six workers).

### F10. REQUIRED — Cost projection omits the largest risks
- **Location.** §18.
- **Problem** (my figures from `r4_cost.py`; the parallelism check is 295,340 cell-seconds against 49,251 s charged, which is 6.0).
  - (a) **Block X at up to 4·U₀ is not projected.** 128K/16K at U₀ ≈ 1.57 million updates is about 22 charged hours for 4 arms × 5 replicates at 0.0124/0.0147/0.0216/~0.013 s per update. At 4·U₀ it is about 90 hours, and one D-OQ cell alone would take about 38 hours of wall time on the critical path.
  - (b) 128K/64K and 32K/64K at 6·U_P (8–12 h) implicitly assume that U_P for the 131,072-fact row is 16,384. The 32,768-fact row needed twice the 8,192 row's U_P. At 32,768 or 65,536 the figure is about 14 or 28 h, using 0.035–0.049 s (F-OQ) and 0.071–0.077 s (D-OQ) at 65,536 slots.
  - (c) "Block M calibration about 6 h" is low. P10-S1's revision-5 calibration (load search and dense rates only) charged 18,683 s (5.2 h). ADR-0024 adds a five-rate, two-draw search for four more arms, 80 loaded runs of 65,536 updates (about 2 h wall), a run-until-full load search, and 2K/256, which was not full at 262,144. I estimate 8–12 h or more.
  - (d) Lane R at 1–3 h is plausible but tight: 280 checkpoints × about 27 reads, each needing the derangement read. I estimate 2–5 h.
  - The headline "60–75 h" for both blocks is then a central case. The plausible upper range, with every loaded cell running to 4·U₀, is over 150 h, beyond the "130–150 h" cap the draft quotes.
- **Change.** Give low, central and upper cases, including the 4·U₀ ceilings for both blocks and the U_P uncertainty at 131,072 facts, before the human lead's block X funding decision.

### F11. REQUIRED — Lane R's "not seen" column misdescribes what the records hold, and those values are not sealed
- **Location.** §11, right-hand column, last row.
- **Problem.** I checked key names and presence only; no value was printed.
  - `tree_recall_of_exhaustive_top8` is stored **for T-OQ only, at U_P only** (`evaluate.py` `deep_measures` → `separability` → `tree_recall`). It is the share of the exhaustive top-8 inside the router's visited branches, which is CR8 of T0 exactly.
  - The index's recall is stored **at every snapshot** of every F-OQ-IVF read (`index.py` `IVFMemory.measured()` → `ivf_measured.recall_of_exhaustive_top8`; 370 of 370 IVF reads carry it). It is SR8 = CR8 of I256@512.
  - The draft says the evaluation stored recall "by the tree and by the index at U_P", which is wrong on both counts.
  - Neither value is in `analysis.json`, `results.json`, `RESULTS.md` or the audit outputs (0 matches), so "not printed" is true.
  - Anyone with the run directory can open them, and nothing in the draft prevents that before Lane R's freeze.
- **Change.**
  - Correct the description.
  - Add a sealing rule: no one opens these keys before Lane R's freeze, and the freeze record states that no one has.
  - Use both as **exact reproduction gates** in §19: T0's CR8 at U_P must equal the recorded tree recall, and I256@512's CR8 must equal the recorded index recall at every checkpoint read. These are stronger checks of the new code than the correct/useful counts alone.
  - Rephrase "not seen by anyone" as "not printed in any committed record; no one in this workflow reports having opened them".

### F12. REQUIRED — One ADR, two freezes
- **Location.** §0, §17, §20, §24 item 4.
- **Problem and change.** See section C. Split Lane R into its own ADR (needs the human lead's ruling on note §5.4), or make each lane's frozen input a per-lane extract file with its own hash, never the combined ADR.

### F13. REQUIRED — PK-OQ: under-specified, and its place conflicts with the direction
- **Location.** §4.1; open choice 5.
- **Problem.**
  - **Comparison with Lample et al. (2019), from my own memory of the paper.** I have not re-read it, and I cite no number from it.
    - Product keys there: a query (from a query network with batch normalisation) is split into two halves. Each half is scored by **inner product** against √N learned sub-keys. The top-k of each half gives k² pairs; the top-k pairs by summed score are exact. The output is the softmax-weighted sum of values, with multiple heads and k around 32.
    - The draft's PK-OQ keeps the product construction and the exactness argument, which is correct for a sum of scores.
    - It differs in cosine scoring of re-normalised halves at temperature 0.2, a single head, k = 8, and a fixed oracle query.
    - These are reasonable adaptations, but the text should call it "a single-head, cosine-scored product-key read after Lample et al.", not imply that it follows the paper.
  - "Initialised as F-OQ's keys" is undefined: F-OQ's keys are [N, 16] and the sub-keys are [n, 8] × 2. Seed, distribution and scale must be specified.
  - **Direction.** The human lead's §5.6 endorses the lead's §4 drafting considerations, including item 4 ("a product-key memory arm ... belong[s] in the comparison"). The human lead's §5.2 lists product-key memory as a Stage B intervention, and §5.4 says a new architecture becomes a separate study.
    - As a Lane C capacity baseline that enters no outcome, PK-OQ is defensible.
    - But §10.6 reads it "against T-OQ and F-OQ-IVF", which is a routing comparison, which is Stage B content.
    - The documents disagree, and AGENTS.md says to stop and ask.
- **Change.** Specify the initialisation. Rename the arm's description. Put the conflict to the human lead as written (open choice 5) and recommend deferral. If PK-OQ is kept, state that its sparse-arm comparison may not be cited to select a Stage B design. PENDING LEAD REVIEW.

### F14. REQUIRED — The quiet-machine rule and its consequences
- **Location.** §17 (load ≤ 1.0, three retries two minutes apart; "idles at a load of about 1.0–1.2").
- **Problem.**
  - "Idles at 1.0–1.2" has no source in the records. The ADR-0027 review removed the same claim as unsourced (`ADR-0027` line 219, A-A3).
  - If true, the ≤ 1.0 rule fails most of the time. P10-S1's supplement passed at 0.998.
  - When MC-T is NOT MEASURED, STORE NOT BEHIND is unavailable, so **CAPACITY-POSITIVE is unreachable**. And because both E-A and E-T are needed, **EFFICIENCY can be neither positive nor negative**.
  - §17 says only that C-EFFICIENCY "cannot be positive". The phrase "favouring dense labels are unavailable" is ambiguous.
- **Change.**
  - Remove or source the idle claim.
  - Give a waiting protocol with a deadline (for example, retries every 10 minutes for up to N hours; or a scheduled window agreed with the human lead).
  - State plainly every outcome that MC-T NOT MEASURED makes unreachable.

### F15. REQUIRED — Disclosure placement
- **Location.** §24 (reviewer notes).
- **Problem.** Several disclosures exist only in §24, which may not survive into the approved text: primary = run length chosen knowing its direction; the symmetric rule and the MU demotion written after observation.
- **Change.** Each disclosure goes beside its rule (§10.2, §10.5, §14).

### F16. REQUIRED — Lane R gates and NOT EVALUABLE cases that are missing
- **Location.** §19.
- **Problem and change.** Add:
  - the recorded-recall reproduction gates (F11);
  - "Tv defined only for v ≤ N/256; at 1,024 slots v ∈ {1, 2, 4}, and v = 4 is T3/T2";
  - the v = 1 priors-on ≡ priors-off identity as an exactness gate;
  - I256@512's `index_sha256` must equal the recorded one;
  - a rule for when F0 itself fails reproduction (the cell is NOT EVALUABLE for both labels).

  Gate G9 (seed disjointness from P10-S1's 210001–219999) must exempt Lane R's intended reuse of P10-S1's draws and P10-S1's index seed (base + 60), or G9 fails by construction.

### F17. REQUIRED — Lane C rule gaps
- **Location.** §8, §10.1.
- **Problem.**
  - The ladder rule and Δ_SAT − 2·[i\*(U_run) − i\*(U_run/2)] need a snapshot at U/2 of every ladder point. U = 1.5 × 65,536 needs 49,152. The snapshot schedule must list them.
  - "Every other arm starts at the larger of the two U₀" must name the arms (D-OQ, PK-OQ).
  - The NOT FULL WITHIN BUDGET status at block X's 128K/16K is not reflected in §18's cost (F10).
- **Change.** List the snapshot schedule per ladder point and name the arms.

### F18. ADVISORY — Crowding at 131,072 facts can be computed now
- **Location.** §5 "A confound that grows with the row"; §18 "unknowns".
- **Finding.**
  - For i.i.d. uniform unit codes of width 16 (`r3_crowding.py`), the share with a neighbour above cosine 0.8 is 0.111, 0.377 and 0.849 at 2,048, 8,192 and 32,768. That matches P10-S1's 0.10, 0.38 and 0.85.
  - At **131,072 it is 0.999**, with median nearest-neighbour cosine 0.858.
  - Block X's within-row steps (C3, N3) keep the fact set fixed and stay interpretable. The saturation pair 4,096 → 16,384 compares rows with crowding 0.85 against 0.999 and is heavily confounded.
  - Peak RAM: P10-S1's `separability` forms 2,048 × F cosine blocks, about 1 GiB at F = 131,072, against the 3 GiB per-worker guard.
- **Change.** Print the theoretical figure in the draft now. Let the human lead decide block X with it. Have the rehearsal confirm it and measure peak memory.

### F19. ADVISORY — Dropping H8
- **Location.** §4.
- **Problem.** H8 is the only fixed-address control: learned keys against hashed slots. KEY-LEARNING-LIMITED was False at P10-S1's untuned rate (RESULTS.md line 32). Under the new rate search, the comparison could change. Dropping it removes the one check of whether key learning adds anything on a task a hash solves.
- **Change.** Keep H8 at the two loaded cells at least, or state this loss under §22. PENDING LEAD REVIEW (open choice 6).

### F20. ADVISORY — Bridge duplication
- **Location.** §5, §7.
- **Problem.** If the selected rate for F-OQ or T-OQ at 8K/4K or 32K/16K is 0.003, block B's cells duplicate the registered cells (same seeds).
- **Change.** State that block B is then not run and the registered cells serve.

### F21. ADVISORY — Measurement definitions
- **Location.** §13.
- **Problem and change.**
  - Define TV distance on the union of the two selected sets, with zero weight outside each.
  - State that ties in E8 and E1 follow `stable_top` (lowest slot id).
  - State that I64@c's c is a minimum and print measured counts.
  - Say that the prior changes weights only across branches (see B).

### F22. ADVISORY — STORE HOLDS MORE drops ADR-0021's cost condition
- **Location.** §10.2, the saturation labels.
- **Problem.** ADR-0021 §8.5 also required D-OQ's cost per update to be at least the arm's in both measures. It is descriptive here, but it should match or the change should be noted.

### F23. ADVISORY — Quotation details
- Every number in §2, §10.2, §14, §17 and §18 that I checked matches its record. The exceptions:
  - §18 "F-OQ 0.0050 ... at 1,024": 2K/1K is 0.0060; 0.0050 is 8K/1K.
  - §18 "1.946 in P10-S1's rehearsal under unrelated load": ADR-0021 line 1265 says "worst D-OQ at 1,024 slots"; "under unrelated load" is the drafter's gloss.
  - §11 recall location (F11).
  - §17 idle load, unsourced (F14).
- Checked and matching:
  - §2 items 1–10 against OUTCOME.md, ACCEPTANCE.md, AUDIT.md §2–§6, ERRATUM and `a4_dep_sensitivity.out`. This includes a_use 0.256–0.414, ratios 0.9262–0.9486 and 0.9425–0.9471, 157 < 173, 12 R2 failures at 512–1,024, 2,289 evaluations, ρ 3.785–3.875 and 2.389–2.922, gains 0.1059 and 0.132, d values, 1.76–1.87, 0.27–0.38 and 1.32–1.87, and analysis.py lines 167–169 and 631.
  - Fact 13's 1.46–1.52 and +0.54–0.62.
  - The 0.10/0.38/0.85 crowding (ADR-0021 §8.10).
  - The seconds per update in §18 (F-OQ 0.0081–0.0092 and 0.0124–0.0136, T-OQ 0.0116–0.0147, D-OQ 0.0051, 0.0088–0.0104 and 0.0177–0.0216; peak 0.390 GiB).
  - 49,251 s, 1,899 s and 25.39 h from the ledger; timing stages 202–376 s.
  - §14's 0.942 → 0.496 bits (draft "0.50"), 0.19 bits, i = 2.5 at a_use 0.678, and a_use 0.9686 at 0.992 (draft "about 0.969").
  - The cell arithmetic of §5 (31; 13; 4; 155 + 65 + 20 = 240).

### F24. ADVISORY — Lane R replicate accounting
- **Location.** §14 replicate rule.
- **Problem and change.** State that the denominator is always 5, that a NOT EVALUABLE or undefined-g replicate counts as not satisfying, and that I64's mean over three index seeds is taken before the panel test.

### F25. ADVISORY — Tags
- **Location.** §1, §14.
- **Problem and change.** Lane R's labels describe oracle-addressed memories on the same lookup task. They should carry `ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK` beside REGISTERED RE-ANALYSIS OF OBSERVED CELLS.
- On point (9): the Lane C cap "necessary condition met / not met / not established" is honest enough. "Necessary condition met" must never be paraphrased as "half the storage claim". ADR-0021 §8.7's "storage half supported" wording should not return.

### F26. ADVISORY — Small items
- Restate DEP's a_use ≥ 0.25 applicability floor (ADR-0021 §8.1); the draft is silent (F6).
- Rows 1–2 are missing from the efficiency table (F5).
- **Retention rule (point 10).** The rule is reasoned, and in accuracy terms (`r1_retention.py`, mean a_use of F0) it requires:

  | Cell, checkpoint | F0 a_use | Required a_use | Share of the improvement above chance (1/32) retained |
  |---|---|---|---|
  | 8K/4K, U_P | 0.948 | 0.920 | 0.969 |
  | 8K/4K, run | 0.996 | 0.974 | 0.977 |
  | 32K/16K, U_P | 0.916 | 0.885 | 0.965 |
  | 32K/16K, run | 0.992 | 0.969 | 0.976 |
  | loaded 8K/1K, U_P / run | — | 0.366 / 0.613 | 0.933 |
  | loaded 32K/4K, U_P / run | — | 0.368 / 0.597 | 0.933 |

  - At every primary cell it is stricter than the note's 95% of accuracy. At the loaded (secondary) cells it is slightly looser than 95% of accuracy (0.613 against 0.621 at 8K/1K run) and than 95% of the improvement.
  - The human lead's requirement is met: i is zero at the chance interval and counts only read-dependent answers, and the floor i(Y) ≥ 0.473 stops a weak reference.
  - The draft's claim "a ratio of i **is** the retained improvement above the no-memory baseline" is true in information units, not in accuracy units. Say "in bits".

### F27. ADVISORY — Seed namespaces
- Checked against the sibling drafts: ADR-0023 (data 300001–309999; inits 3001–3002, 3091–3092; tests 930001–930999), ADR-0025 (250001–259999), ADR-0026 (260001–269999; inits 2601–2603, 2691–2692; tests 926001–926999), ADR-0027 (270001–279999; inits 2701–2799) and ADR-0028 (280001–289999).
- No overlap with ADR-0024's 240001–249999, inits 2401–2405 and 2491–2493, or tests 924001–924999.
- P10-S1's derived-seed convention (init + 1000·k, router at init + 5000) gives 3401–3405, 3491–3493, …, 7401…. None of these collides with the siblings' inits or their derived values.
- No use of 24xxxx or 924xxx was found in `configs/`, `studies/` or `src/`.
- G9 needs the Lane R exemption (F16).

---

## Answers to the other numbered checks

- (1) Numbers: see F23. Mismatches: §11's recall location, §18's 0.0050 at 1,024 slots, the 1.946 gloss, and the unsourced idle load.
- (2) DEP-c: F6 and F7. R2 passes at every snapshot (0 of 150 fail), and the four failing F-OQ snapshots pass, as do all 32. "Only where read" is a weakening relative to 22 (g) and is not openly argued as one.
- (3) Dense-speed rule: symmetric and computable. Its effect on P10-S1 (NEGATIVE → INCONCLUSIVE) is not disclosed (F5).
- (4) Matched compute primary: yes, a post-observation relaxation of the positive. The defensible registration is in F4.
- (5) Equal rate search: right in principle (EXPERIMENT_PROTOCOL §3), but circular with U_P (F1). At loaded cells the selection at 65,536 updates favours fast rates for runs of 0.4–3 million updates; the draft states this limit. Bridge: F9 and F20.
- (6) H8 and PK-OQ: F13 and F19.
- (7) Block X: F10 and F18. Meaningful for the within-row step C3; heavily confounded for the saturation pair; its cost is underestimated at the upper end.
- (8) Run-until-full up to 4·U₀: compliant with DIRECTION §5. It is a design ceiling with a convergence rule written in advance, it is applied by frozen code to the cell's own statistic, and nothing is extended because a result looks close. Its cost must be projected (F10) and its snapshots listed (F17).
- (9) DICT DOMINATES: honest enough (F25).
- (10) Retention: F26.
- (11) What has and has not been seen: F11.
- (12) Limits, quiet machine and cost: F10 and F14. The engineering-lessons table (§20) is good, and its "nothing written in the frozen worktree" rule matches the lesson of P10-S1 attempt 1.
- (13) Seeds: F27.
- (14) Overclaims and loopholes: F2 (causal labels), F3 (N/8), F4 (post-observation primary), F6 (DEP read list), F8 (primary checkpoint drives Stage B), F11 (unsealed values).

## Appendix — logic of the scripts that produced the reported numbers

`r2_depc.py` (core). G2 is the exact central binomial interval of level 1 − 0.001/40 around 1/32. Its output ([34, 100], [192, 325], [894, 1,159]) reproduces ADR-0021 G2.

```python
lo, hi = g2(n); pplus = hi / n; m = n - u
q = smallest k with BinomCDF(k; m, pplus) >= 1 - 1e-4
cond_i  = (c - u) > q
cond_ii = (c - u - m * b / n) / n > 0.01      # b = NO-MEMORY correct, same draw, facts, panel
fail = cond_i and cond_ii
old  = (4 * u >= n) and (20 * u < 19 * c)      # ADR-0021 third condition with the a_use >= 0.25 floor
```

It is run over every `cells/*/eval/u*/eval.json`, reads `main` and `ivf`, panels A and B, and excludes D-OQ.
- Output: reads 4,394 (registered 3,210); b == disabled_correct in all; DEP-c failures 0; former 0.95-condition failures 32 (registered) / 36 (with seed-block cells), all passing DEP-c.

`r1_retention.py`:
- i(a) = 5 − h₂(1 − a) − (1 − a)·log₂31.
- Threshold i\* = max(i(F0) − 0.25, 0.9·i(F0)), inverted by bisection to a_use.
- Mean a_use from AUDIT.md §6.

`r3_crowding.py`:
- P(cos > t) for two i.i.d. points on S¹⁵ by numerical integration of (1 − x²)^{6.5}.
- Share with a neighbour above 0.8 = 1 − (1 − p)^{F−1}.

`r4_cost.py`:
- seconds per update = manifest `seconds` / `train.json` `run_updates`, per (kind, arm, slots, facts), median and range.

`Astra review: NOT_PERFORMED`.
