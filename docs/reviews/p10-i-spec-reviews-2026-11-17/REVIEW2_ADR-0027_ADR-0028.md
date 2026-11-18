# Confirmation review of the revised ADR-0027 (P10-I-S4) and ADR-0028 (P10-I-S5)

- Date: 2026-11-17 UTC (about 21:40 to 22:10). Reviewer: the `arbor-auditor` subagent, model Claude Opus 5.5 (`claude-opus-5-5`, as the session reports it). The drafter of both revisions was Claude Fable 5.2. The reviewer did not write either draft. The first review (`REVIEW_ADR-0027_ADR-0028.md`) was written by an earlier `arbor-auditor` instance; where its text was copied into a draft and is wrong, that is reported here as well (finding S4-N11).
- Reviewed at branch `claude/p10-i-specs`, HEAD `26ea57b`, clean tree. Drafts: `docs/decisions/ADR-0027-p10-i-s4-quality-against-cost.md` (226 lines), `docs/decisions/ADR-0028-p10-i-s5-physical-ssd-memory.md` (244 lines). Read against the **current** text of ADR-0023, ADR-0024, ADR-0026, ADR-0029, `CLOSURE_LEDGER.md`, `SEED_REGISTRY.md` and `DIRECTION.md`.
- Independent engineering and mathematical review. It is not Astra validation and not human approval. `Astra review: NOT_PERFORMED`. Scientific choices are marked `PENDING LEAD REVIEW`; the reviewer chooses no threshold.

## Verdicts

| Draft | Verdict | New blocking | New required | New advisory |
|---|---|---|---|---|
| ADR-0027 (S4) | **NOT READY** | 1 | 8 | 5 |
| ADR-0028 (S5) | **NOT READY** | 0 | 5 | 5 |

Main reason for both: the two drafts were revised against sibling texts that have since changed. ADR-0027's Route A names labels that ADR-0026 no longer has, so its entry criterion is not computable; Route B cites wrong section numbers, a removed arm (PK-OQ) and an ambiguous cell. ADR-0028's Q1 names ADR-0023 outcome rows by wrong numbers and wrong names, and Q2 states that no learned-address capacity label exists, which ADR-0024's lane L now contradicts. Most of the cross-reference repairs are mechanical (table at the end, with exact replacement text). The remaining required items need rules that are not purely mechanical: Route A's replicate unit, panels and data ceiling; the treatment of F-OQ-IVF; the selection rule for D+; the quiet-load figure; the utilisation measure; and the resident-budget rule.

---

## Part A. ADR-0027 (P10-I-S4)

### A.1 First-review findings

| Finding | Revision says | Judgement | Note |
|---|---|---|---|
| A-B1 analytic matching; disagreement rule | FIXED | **FIXED**, with one premise left unstated (S4-N4) | The combination is now asymmetric. MC-A's omissions are stated in §5 and §14. The ADR-0021 §5.4 precedent is cited |
| A-R1 B\* not computable | FIXED | **FIXED**, two small gaps (S4-N6) | Order of work, max over D, D+ and FT, KV excluded, B\* NOT DETERMINED |
| A-R2 conversion to MC-T | FIXED | **FIXED** | B\*_T = update count × per-update CPU of the arm that defines B\* |
| A-R3 snapshot shortfall | FIXED | **FIXED** | Snapshots per arm at f·B\*; NO SNAPSHOT AT B\* |
| A-R4 KV's role | FIXED | **FIXED** | KV is out of the rule. The qualifier is registered |
| A-R5 quantifier order | FIXED | **FIXED** | Joint reading, written out |
| A-R6 D+ search budget | FIXED | **PARTLY FIXED** | The surplus is now stated. **No rule says how the "best" D+ architecture is chosen** (S4-N7) |
| A-R7 MEMORY MATCHES | FIXED | **FIXED** | NOT SEPARATED AT MARGIN; parity is excluded in §1 and §14 |
| A-R8 δ estimator | FIXED | **FIXED** | Estimator specified; floors fixed with reasons (judged under S4-N10) |
| A-R9 Route B | FIXED with ADR-0024's names | **FIX INTRODUCED NEW PROBLEMS** | Wrong section numbers; "largest funded transition" is ambiguous; F-OQ-IVF is not a trainable arm; DEP wording is out of date (S4-N2, cross-reference table) |
| A-R10 search boundary | FIXED | **FIXED for rates**; D+ architecture edge has no outcome (S4-N7) | |
| A-R11 quiet block | FIXED | **PARTLY FIXED** | PAUSED and three reschedules are in. The load figure is set at the freeze from the rehearsal, with no ceiling fixed now (S4-N5) |
| A-R12 unclassified limits | FIXED | **FIXED** | |
| A-A1 … A-A6 | FIXED | **FIXED** | The A-A3 removal was checked: §8 now quotes 0.998 (record) and "about 3" (reviewer), each attributed |
| A-A7 product-key memory | ANSWERED | **ANSWER NO LONGER VALID** | It rests on "ADR-0024 defines PK-OQ"; ADR-0024 §4 has removed PK-OQ (cross-reference table) |
| A.4 missing NOT EVALUABLE cases; scope sentence | FIXED | **FIXED**, except that a Route A data-exhaustion case is missing (S4-N3) | |

### A.2 New findings

**S4-N1. BLOCKING. §3 Route A (line 48). The entry criterion names labels that do not exist in ADR-0026.** ADR-0026 revision 2 has no regime-combination labels. "DEPENDENT, BOTH REGIMES", "DEPENDENT, FRESH ONLY", "BOTH REGIMES or FRESH ONLY" and "REPEATED DATA ONLY" are all gone. The registered label of each line is its FRESH regime label (ADR-0026 §6.5). Line 1's labels are DEPENDENT / CAPACITY WITHOUT DEMONSTRATED DEPENDENCE / NO CAPACITY / NOT EVALUABLE (§6.2, §10). In ADR-0026, convergence is a per-arm, per-regime tag (§5.2), not a property of "the FRESH regime". INCONCLUSIVE is a label (§6.4), not a tag. "With the FRESH regime CONVERGED" is therefore not computable. It also settles in advance ADR-0026's open choice 13, whether a label that carries "(DENSE STILL IMPROVING)" or a NOT CONVERGED tag still qualifies, which ADR-0026 §12 leaves to the human lead. Change: replace A1 and A2 with the text in the cross-reference table, row X1.

**S4-N2. REQUIRED. §3 Route B (line 49). F-OQ-IVF can qualify but is not a trainable arm.** ADR-0024 §9.3 row 3 makes F-OQ, T-OQ **or F-OQ-IVF** a qualifying arm. F-OQ-IVF is "evaluation only": F-OQ's keys read through the index, with nothing learned (ADR-0024 §4). ADR-0027 says "every arm that is both … enters S4 as its own memory arm", and that M's learning rate is searched. For F-OQ-IVF, the training run, the rate search and the training computation (MC-A, MC-T) are all undefined. Change: add one sentence, either "F-OQ-IVF enters as F-OQ trained under §4's search and read through ADR-0024's registered index at evaluation; its training computation is F-OQ's plus the index build, which is counted in MC-A and MC-T", or "F-OQ-IVF does not enter S4". Which one is a scientific choice, `PENDING LEAD REVIEW`.

**S4-N3. REQUIRED. Route A is not specified enough to run, and §12 does not list what is missing.** (a) **Replicates:** §5 and §7 speak of "five fresh data draws", "two calibration draws" and "two initialisation seeds". ADR-0026's unit is a cell (parent, initialisation seed) on nine fixed P3 parents, with 27 cells and 22-of-27 rules. "Draw" has no meaning there. (b) **Panels:** §5 requires "both panels". ADR-0026 has one registered panel and one calibration panel (§4), and it requires ADR-0027 to exclude both panels through its panel ledger. ADR-0027 does not mention the ledger. (c) **Data ceiling:** ADR-0026's FRESH pool supports at most 19,064 single-pass updates (§4). B\* is the largest of the alternatives' convergence computations, and ADR-0026 itself expects FRESH arms to be NOT CONVERGED at 16,384. If M's MC-A per update is lower than the defining arm's, M needs more updates than the defining arm does, and the pool can run out before B\*. No NOT EVALUABLE case covers this. (d) Seeds: the registry gives S4 "draw sets", which also does not fit Route A (registry §7 item 6 leaves the count PENDING). Change: in §12 add "Route A: the replicate unit (parent, initialisation seed and FRESH stream), its count and which parents; two registered panels drawn under ADR-0026 §4's panel rule and ledger; the training-data ceiling", and in §9 add **S4 NOT EVALUABLE (TRAINING DATA EXHAUSTED BEFORE B\*)**.

**S4-N4. REQUIRED. §5 combination table, row 2, "including MC-T NOT MEASURED when MC-A gives X-AHEAD". The clause holds only under a premise the draft does not state or check.** The reasoning is that MC-A leans towards the memory, so an alternative that leads even under MC-A would lead under MC-T as well. That follows only if (i) M's measured CPU per counted multiply-add is at least that of each alternative and of the arm that defines B\*, so that M gets no fewer updates at matched MC-A than at matched MC-T, and (ii) quality does not fall between the two update counts. P10-S1 supports (i) for T-OQ against D-OQ (0.197 counted against 0.960 measured). It is not established for D+ or FT, or on Route A. (ii) can fail on repeated data, which Route A does not use, so on Route A it is about FRESH learning curves. The clause is right in direction and wrong to state without its condition. Change: append to the row "provided the rehearsal's per-update figures show that M's CPU seconds per counted multiply-add are at least those of X and of the arm that defines B\*; otherwise S4 NOT EVALUABLE (MC-T NOT MEASURED)". The label is then printed as "ALTERNATIVE AHEAD AT MATCHED COMPUTE (MC-A; MC-T NOT MEASURED)". The rehearsal measures per-update MC-T anyway (§8), so the check costs nothing.

**S4-N5. REQUIRED. §8 quiet condition. The load figure is fixed from the rehearsal with no ceiling, and it gates the positive label.** "Stays at or below a figure fixed at the freeze" means a rehearsal on a loaded machine (the reviewer saw about 3) could set a figure that makes "quiet" meaningless. Yet MC-T decides whether MEMORY AHEAD can be printed. ADR-0024 §16 fixes the same quantity now: one-minute load average ≤ 1.0, retried every 10 minutes for up to 6 hours. Change: fix a ceiling now (for example "the figure is at most 1.0, as ADR-0024 §16"). Alternatively, reserve the figure explicitly for the human lead in §11. The number is `PENDING LEAD REVIEW`. Also state that B\*_T and the snapshot update counts use the **rehearsal's** per-update figures, and that the confirmation block only tests them against the CV rule.

**S4-N6. REQUIRED (small). §5 "Order of work" and "δ".** (a) δ uses s "at B\*" from calibration runs. The convergence runs stop when each arm meets its rule, and B\* is the largest of those points, so the runs of the other arms (and of M) need not reach B\* or B\*_T. Add "calibration runs of every arm continue to B\* and B\*_T". (b) "Median over the two calibration draws" is the mean of two values, and each draw has two initialisation seeds. Write "mean over the four calibration runs (two draws × two initialisation seeds)", or name the rule.

**S4-N7. REQUIRED. §4 D+.** "Best dense adapter over a registered width and depth grid" has no selection rule. It is not stated whether the best is chosen by quality at the fixed search length in updates or in compute, on which panel, or with which tie rule. The choice matters for the outcome: B\* includes c(D+), so a larger D+ moves the budget at which everything is read. D+ at an edge of its architecture grid after two extensions has no outcome (only the rate edges do). Change: state the rule, for example "D+ is the (architecture, rate) pair with the lowest calibration quality loss at the search length, ties to the smaller architecture", and add **ALTERNATIVE ARCHITECTURE AT EDGE** with the same reading as ALTERNATIVE RATE AT EDGE. The rule is `PENDING LEAD REVIEW`.

**S4-N8. REQUIRED. §7 seeds against `SEED_REGISTRY.md`.** The draft proposes initialisation seeds 2701–2799 and says "a scan … found no earlier use". The registry (§5) shows 2701 = P9's 1701 + 1000 and 2791/2792 = P9-I's calibration seeds + 1000, which is 20 actual collisions. It replaces them with 330401–330499. The sibling ranges quoted are also out of date: ADR-0023 is now 330001–330099; ADR-0026 is 2601–2699 in its draft, and both are replaced by the registry; ADR-0029 is missing. The test range 936001–936999 is not mentioned. Replacement text is in row X8 of the cross-reference table. The registry also asks for the count of registered initialisation seeds, which depends on the route (S4-N3).

**S4-N9. ADVISORY. §1 and §5.** When two different alternatives each reach 4 of 5, say that every one of them is named. On Route A, quality is NLL, so lower is better: write "ahead by δ means lower NLL by at least δ" (on Route B, higher i is better).

**S4-N10. ADVISORY. §5 δ, judged.** The estimator is computable. The pooled within-group SD has (4 − 1) × 8 = 24 degrees of freedom on Route B (4 trained arms × 2 panels, 4 runs each), so the concern of A-R8 is met. It measures the SD of single-arm quality, not of paired differences. Because the data draw is shared within a replicate, it overstates the SD of the differences, and this widens δ on both sides. That is conservative and needs no change. Floors: 0.005 nats per byte matches ADR-0026 §6.1. 0.25 bits matches ADR-0024 §9.2's "d > −0.25". The 6/32 = 0.1875 figure is correct.

**S4-N11. ADVISORY. §2 line 32.** The row says "Per update at 16,384 slots: analytic multiply-adds T-OQ / D-OQ = 5.21e11 / 2.65e12". In `RESULTS.md` lines 216–252 those figures are in the column "Analytic multiply-adds **to U_P**", which is cumulative, not per update. The ratio 0.197 is still the per-update ratio, because both arms share U_P at 8K/16K (128 exposures per fact, lines 221 and 252). The error comes from the first review (A-B1), which used the same words. Change: "Cumulative analytic multiply-adds to U_P at 8K/16K (equal U_P): T-OQ / D-OQ = 5.21e11 / 2.65e12 = 0.197, also the per-update ratio".

**S4-N12. ADVISORY. §3 "Reading of the direction".** ADR-0026 §12 reads `DIRECTION.md` §4's "P10-S1" literally: "not a revision of P10-S1, which remains the other route the direction names". ADR-0027 reads it as P10-I-S1. The two drafts disagree. The question is already `PENDING LEAD REVIEW` (§11 item 2). Say in §3 that ADR-0026 reads it the other way.

**S4-N13. ADVISORY. §9.** State the precedence explicitly: every S4 NOT EVALUABLE reason is tested before the combination table.

### A.3 New material judged (task list)

- **Asymmetric label rule.** All 12 combinations of (MC-A ∈ {M, X, NS}) × (MC-T ∈ {M, X, NS, NM}) reach exactly one row. M-AHEAD and X-AHEAD cannot both hold under one measure, because a replicate that has M ahead of X by δ on both panels cannot have X ahead by δ on either. The direction follows ADR-0021 §5.4 (checked: `ADR-0021` line 193). The NOT MEASURED clause: see S4-N4.
- **B\*, B\*_T, per-arm snapshots, joint 4 of 5:** computable as written, apart from S4-N6.
- **NOT SEPARATED AT MARGIN:** correctly worded, and parity is excluded.
- **LOOKUP SUFFICIENT ON THIS TASK:** computable on Route B. On Route B it will almost surely print (DICT 32,768 of 32,768 in P10-S1). On Route A it does not apply, since KV is not defined there.
- **Search-edge extension:** correct for rates and asymmetric in the conservative direction. The gap for the D+ architecture is S4-N7.
- **Quiet blocks PAUSED and rescheduled:** see S4-N5.
- Unsourced facts: none found. Load figures are attributed (0.998 from the supplement; "about 3" to the reviewer).

---

## Part B. ADR-0028 (P10-I-S5)

### B.1 First-review findings

| Finding | Revision says | Judgement | Note |
|---|---|---|---|
| B-B1 result and RAM parity | FIXED | **PARTLY FIXED** | Recall floor, common resident budget, common read primitive at queue depth 1, all in. Residual: S-FLAT is exact (recall 1) and the resident budget alone decides whether S-FLAT reads keys from the device (S5-N4) |
| B-R1 quantifiers, margins | FIXED | **FIXED** | First match; NOT SEPARATED added; MEASURES DISAGREE now means disagreement |
| B-R2 Q1 and Q2 met by different systems | FIXED | **FIXED in rule; the stated premise is now false** | One system is required (good). "No sibling draft registers this" is contradicted by ADR-0024 lane L (S5-N2) |
| B-R3 utilisation floor timing | FIXED | **PARTLY FIXED** | The floor is fixed now. The measure is not computable the same way by two people (S5-N3) |
| B-R4 cold state | FIXED | **FIXED** as rehearsal checks with named outcomes; build path, positive control last, `purge` not relied on | |
| B-R5 counters | FIXED | **FIXED** | Per-process primary, driver cross-check, "never NAND", upper bound 1.1 |
| B-R6 write charging | FIXED | **FIXED** | |
| B-R7 backup, snapshots, indexing | FIXED | **FIXED** (advisory caveat, S5-N9) | |
| B-R8 device cache | FIXED | **FIXED** | Disjoint pages, settling, randomised order, invalid repeats |
| B-R9 health counters | FIXED | **FIXED** | |
| B-R10 E0 | FIXED | **FIXED** | |
| B-R11 cannot answer as capped | FIXED | **FIXED; reason to restate** | The conclusion still holds, now because of Q3 and the licence, not because Q2 lacks a source (S5-N2) |
| B-R12 scientific label | FIXED | **FIXED** (structure) | |
| B-R13 read point | FIXED | **FIXED** | §2 and §11 give both read points; checked against `OUTCOME.md` line 88 |
| B-R14 PAUSED; limits | FIXED | **FIXED** | |
| B-A1 … B-A6 | FIXED | **FIXED** | B-A5 is labelled as the reviewer's observation (checked below) |
| B.4 NOT EVALUABLE; no cross-citation | FIXED | **FIXED**, two unnamed outcomes (S5-N6) | |

### B.2 New findings

**S5-N1. REQUIRED. §3.2 Q1 (line 61). Wrong row numbers, wrong labels, and a narrower licence than ADR-0023 gives.** ADR-0023 §7: step **3** is "OVERLOAD-QUALIFIED UP TO **L_Q**" (the draft says "row 4, OVERLOAD-QUALIFIED UP TO ℓ"). Step 6 is "OVERLOAD NOT QUALIFIED **AT ℓ₁**; ADDRESSING QUALIFIED UP TO L_Q". Steps 4 and 5 also carry "ADDRESSING QUALIFIED UP TO L_Q", and ADR-0023 §15 item 2 grants the licence "whatever the status of ℓ₁". Q1 accepts any status of ℓ₁ under step 3 but rejects steps 4 and 5. That asymmetry has no stated reason. "Line Q QUALIFIED AT THIS CELL TYPE" is not a state in ADR-0023: §6.4's states are HOLDS / FAILS / NOT EVALUABLE. Replacement text: row Y1 of the cross-reference table.

**S5-N2. REQUIRED. §3.2 Q2 (line 62) and "What follows" (line 67). The statement that ADR-0024 has no learned-address lane is now false. Re-judged:** ADR-0024 §13 lane L trains F-LA, which is A5-D "exactly as ADR-0023 freezes it", at ADR-0023's licensed cell types with load ≤ L_Q. Its line L-CAPACITY registers **LEARNED-ADDRESS GAIN FROM SLOTS**. So **one and the same system** (A5-D, flat memory) can now meet Q1 and a registered capacity condition. "Q2 has no registered source" no longer holds. Two caveats belong in the draft: (a) L-CAPACITY is a lane-wide step label ("at every licensed step"), not a label at one N. It has no dense comparison and no saturation reading. Whether it is "useful capacity" in Q2's sense is a scientific choice, `PENDING LEAD REVIEW`. (b) Lane L's largest licensed cell is 8K/16K. **The conclusion "as capped, the scientific part cannot answer its own question" still holds, for a different reason:** Q1 and Q2 can now be met only at N ≤ 16,384 slots (about 3.15 MB, by the draft's 192 bytes per slot), and Q3 then needs RAM restricted by construction. Replacement text: rows Y2 and Y3.

**S5-N3. REQUIRED. §3.2 Q2-U. U = N_eff/N is not computable the same way by two people, and its meaning depends on an unfixed quantity.** The draft does not say which selections are counted (top-1, or all k = 8 per query, weighted or not), or over which query set. In P8, N_eff = exp(H of selection counts) over 262,144 selections (`ADR-0015` line 119; `results/p8-2026-11-14/SUMMARY.md` line 30). The ratio depends on λ = selections per slot. For selections spread uniformly at random, the reviewer's computation gives E[N_eff]/N ≈ 0.365, 0.564, 0.752, 0.875, 0.938 at λ = 0.5, 1, 2, 4, 8. At load 0.5 counted on top-1 (λ = 0.5), even a perfect one-fact-per-slot memory has U = 0.5 exactly and random placement gives about 0.37. Counted on top-8 (λ = 4), random placement gives about 0.88. The fixed floor 0.5 therefore means different things depending on a definition the draft has not written. Change: fix the selections (for example "all 8 selections of every Panel A query"), the query set, and print λ and the uniform-random expectation beside U. Whether the floor should be relative to that expectation is `PENDING LEAD REVIEW`. The reason the draft gives for 0.5 is a reason (it is not fitted to P8's 0.03), but it does not take λ into account.

**S5-N4. REQUIRED. §5 matching conditions 1 and 2.** (a) S-FLAT is the exact reference, so its recall is 1. S-TREE is read at the smallest budget with recall ≥ 0.90. "S-TREE better than S-FLAT" is therefore never a comparison at matched recall. The positive label requires beating both baselines, so this does not make the positive easier against ANN. It does make "reads less than S-FLAT" partly true by construction, which is P7-A's mechanism again. Because ANN's budget grid is discrete, ANN can also sit well above 0.90 while S-TREE sits at 0.90. (b) If the common resident budget holds all keys, S-FLAT reads only the k value pages, the minimum, and S-TREE cannot read less. If the budget is below the key bytes, S-FLAT must read keys from the device and loses on bytes by construction. The budget, "fixed at the freeze" with no rule, therefore decides the bytes comparison against S-FLAT. Change: state both facts beside the rule. Print each arm's recall at its operating point and the recall gap. Give the rule or reason for the resident budget, fixed before R1 (`PENDING LEAD REVIEW`), or reserve it in §11.

**S5-N5. REQUIRED. §10 seeds against `SEED_REGISTRY.md`.** The registry (§4.2) reserves 280001–286999, 287001–288999, 289001–289199 and 289201–289299, initialisation seeds 330501–330599 if a memory initialiser is used, and tests 937001–937999. It notes "roles and counts not yet stated by the draft" (§7 item 6). The draft's sibling list is out of date: ADR-0026 is shown as "initialisation 2601–2691" (now 330301–330399), ADR-0023's initialisation is missing, and ADR-0029 (290001–299999) is absent. Replacement text: row Y5. The roles and counts still have to be written (workload seeds, store-content seeds, arm-order seeds per block and repeat, R1 seeds).

**S5-N6. ADVISORY. §7 and §9.** Two failure outcomes have no name in §9: positive control failed ("the method is invalid"), and cache ratios of two arms more than 0.05 apart. Name them, for example **POSITIVE CONTROL FAILED** and **CACHE RATIO NOT MATCHED**.

**S5-N7. ADVISORY. §3.1.** The entry clauses are called E1 to E4, and the stages are also called E1 (store build) and E2 (read benchmark). Rename the clauses (for example EC1 to EC4).

**S5-N8. ADVISORY. §5 engineering label.** State that m_b and m_q are relative differences ((baseline − S-TREE)/baseline). State that the denominator stays 5 when a repeat is invalid, so that with four valid repeats the positive needs all four. Note that BASELINE NOT WORSE also covers "within the margin on both measures for one baseline in 4 of 5". That is conservative, and it should be said in the meaning column.

**S5-N9. ADVISORY. §2, §3.1, §6: device facts not attributed in line, and one hygiene caveat.** "48 GiB of RAM" (§2), "`smartctl` is not installed" (§3.1), "675 GiB free on 2026-11-17" and "1.81 TiB by `df`" (§6), and "`tmutil listlocalsnapshots /` needs no administrator access" (§6) are the first reviewer's observations. They are stated as facts, while §15 says the drafter ran nothing. The reviewer re-checked at about 21:58 UTC: `df -k /` gives 708,290,284 KiB available (675.5 GiB) and 1,948,404,040 KiB total (1.81 TiB); `sysctl -n hw.memsize` gives 51,539,607,552 (48 GiB); `smartctl` was not found. Add "(reviewer's observation)" to each. Caveat, to the reviewer's knowledge and not tested: APFS local snapshots cover the whole volume, so excluding a path from backup does not keep a local snapshot from holding the store's blocks. The draft's outcome STORE RETAINED BY SNAPSHOT covers the consequence, and the 500 GB free-space floor should count retained stores until they are released.

**S5-N10. ADVISORY. §11 item 1.** "Hold E1 and E2 until ADR-0024's R-DIAGNOSIS has shown which read path is worth benchmarking." R-DIAGNOSIS is now in ADR-0029. It can come out CHECKPOINT-DEPENDENT, in which case "no single next action is recommended" (ADR-0029 §9 item 3). ADR-0029 says any claim about cause needs Stage A2 (R-CONFIRM). Replacement text: row Y4.

### B.3 New material judged (task list)

- **Comparison only at a recall floor, within one resident-RAM budget, with one read primitive at queue depth 1:** present and computable, except the residuals in S5-N4.
- **Rehearsal checks** (cold state, `purge`, counter visibility, contamination bound, positive control, device cache, continuity): each has a stated test and an outcome. "Drive health" is a stop rule (§9) and an entry clause (E3), not a §7 check. That is acceptable. Two outcomes are unnamed (S5-N6).
- **Write cap:** charges the study's own logical bytes, with the per-process counter as a cross-check. The rehearsal's 2 GB is inside the 64 GB and needs E0. Correct.
- **Store hygiene:** checked in R0, before E1 and before each E2 block. Correct, with the caveat in S5-N9.
- **PAUSED on physical caps:** yes (§9 row 1, §8 quiet rule).
- **Utilisation label (U ≥ 0.5):** the reason given is a real reason but is incomplete. See S5-N3.
- **Device figures quoted from the first review:** "about 1 MB/s of background writes over 20 s", "5.6 MB/s on average since boot" (§6) and "about 3.8 TB written in the 7.9 days since boot" (§6) are each explicitly attributed to "the reviewer". They agree with the first review (1.01 MB/s; 5.64 MB/s; 3,836,560,117,760 B over 680,100 s = 7.87 days). The other device facts are not attributed in line (S5-N9).
- **No hardware purchase, no large write-intensive benchmark:** confirmed. Line 8 forbids both. §11 item 7 proposes no other device and no purchase. E2 is read-only. Update traffic is excluded (§6). Whether 50–64 GB of store builds counts as "large" is reserved for the human lead (§10, §11 item 2). Nothing implies a purchase.
- **The two verdicts are never combined:** confirmed. §1 forbids joint sentences and cross-citation. The two labels have separate rules (§5), separate evidence and separate NOT EVALUABLE lists. No rule reads one line's label in the other. §11 item 1 discusses the tree's quality only as an argument about timing, not as part of a label.

---

## Part C. Cross-reference mismatches (exact replacement text)

| # | File, line | What it says | What it must say |
|---|---|---|---|
| X1 | ADR-0027 L48 (Route A) | "(A1) the registered label of line 1 is **DEPENDENT, BOTH REGIMES** or **DEPENDENT, FRESH ONLY**; (A2) … **COMPETITIVE** or **MEMORY AHEAD**, BOTH REGIMES or FRESH ONLY, with the FRESH regime CONVERGED and no INCONCLUSIVE tag (… 6.3 to 6.5 and 12). REPEATED DATA ONLY, NOT COMPETITIVE, INCONCLUSIVE and NOT EVALUABLE fail Route A." | "(A1) the registered label of line 1 (DEPENDENCE, arm M-TREE), which is its FRESH regime label (ADR-0026 §6.5), is **DEPENDENT**; (A2) the registered label of line 2, **COMPETITIVENESS[TREE]** (its FRESH label), is **COMPETITIVE** or **MEMORY AHEAD** (ADR-0026 §6.3–6.5, §12). Every REP or REP-U regime label, CAPACITY WITHOUT DEMONSTRATED DEPENDENCE, NO CAPACITY, NOT COMPETITIVE, INCONCLUSIVE and NOT EVALUABLE fail Route A. Whether a qualifying label that carries "(DENSE STILL IMPROVING)" or a NOT CONVERGED tag still qualifies is ADR-0026's open choice 13 and is decided by the human lead before entry." |
| X2 | ADR-0027 L49 | "(ADR-0024 section 10.3)" | "(ADR-0024 §9.3, row 3)" |
| X3 | ADR-0027 L49 | "which already requires a capacity step in every funded transition, the dependence conditions at the snapshots the verdicts read, and STORE NOT BEHIND under both cost readings with the measured one present" | "which already requires a CAPACITY STEP in each of block M's two transitions (1,024 → 4,096 and 4,096 → 16,384), no qualified DEP failure at any snapshot of either cell up to its run length (ADR-0024 §8.1, §9.1 row 2), STORE NOT BEHIND (cell) in MC-A, MC-T and MU on both panels in all five replicates with MC-T measured and neither matched-compute pair MC-SHORT, and DENSE HOLDS MORE at no loaded cell (§9.2)" |
| X4 | ADR-0027 L49 | "the larger cell of the arm's CAPACITY STEP in the largest funded transition" | "the larger cell of the arm's CAPACITY STEP in block M's transition 4,096 → 16,384: 32K/16K if step C2 is a CAPACITY STEP for that arm, otherwise 8K/16K (step N2). Block X and X-CAPACITY do not enter Route B" (plus the F-OQ-IVF sentence of S4-N2) |
| X5 | ADR-0027 L51 | "Lane R (R-DIAGNOSIS) is a diagnosis of P10-S1's existing checkpoints and has no pass label." | "R-DIAGNOSIS, now in ADR-0029 (Stage A1 on P10-S1's checkpoints, Stage A2 on fresh checkpoints trained as P10-S1 trained them), is a diagnosis and has no pass label. ADR-0024's L-CAPACITY (lane L) is also not part of the entry condition." |
| X6 | ADR-0027 L68 and L173 (§11 item 6) | "PK: product-key memory (ADR-0024's PK-OQ)"; "include on Route B, where ADR-0024 defines PK-OQ" | "PK: product-key memory. No sibling draft defines one (ADR-0024 §4 removed PK-OQ; the routing note places it in Stage B of the routing work)"; §11 item 6: "Recommendation: not included unless a sibling study defines and qualifies a product-key arm; including it here would mean defining a new architecture in S4." The recommendation itself is the lead's to rewrite |
| X7 | ADR-0027 L83 and L108 | "the cost readings of ADR-0024 section 9.2"; "agrees with ADR-0024 section 10.2 ("a label that favours the store needs both cost readings, measured"). It differs from ADR-0024 section 10.5, which makes negatives need both readings too" | L83: "ADR-0024 §8.2". L108: "agrees with ADR-0024 §9.2 ("a label that favours the store needs matched compute under both cost measures and matched updates as well"). It differs from ADR-0024 §9.2's DENSE AHEAD (cell), which needs MC-A and, where measured, MC-T, and from §9.5, where a negative needs both readings at every cell" |
| X8 | ADR-0027 L131 (§7) | "Proposed seed namespace **270001–279999**, initialisation seeds 2701–2799. A scan … found no earlier use. Sibling drafts …: ADR-0023 300001–309999 and 3001–3091; ADR-0024 240001–249999; ADR-0025 250001–259999; ADR-0026 initialisation 2601–2691; ADR-0028 280001–289999." | "Seeds are those of `SEED_REGISTRY.md` §4.2: registered draw sets 270001 + 100(d−1), d = 1..5; calibration 279001, 279101; rehearsal 279201; auxiliary 277001–278999; initialisation 330401–330405 (registered; count PENDING by route), 330491, 330492 (calibration), 330495 (rehearsal), 330498, 330499 (test mode); tests 936001–936999. The draft's earlier 2701–2799 collided with P9's and P9-I's derived seeds (registry §5) and is withdrawn. The G9 gate re-runs the registry checker with R2 and R3 expanded before the freeze." Route A's mapping onto this layout is added under S4-N3 |
| X9 | ADR-0027 L44 | reads "P10-S1" as P10-I-S1 | add: "ADR-0026 §12 reads it literally as P10-S1; the two drafts differ until the human lead rules" |
| Y1 | ADR-0028 L61 (Q1) | "registers outcome row 4, **OVERLOAD-QUALIFIED UP TO ℓ**, or row 6, **OVERLOAD NOT QUALIFIED; ADDRESSING QUALIFIED UP TO L_Q**, and the system's load is at most L_Q with Line Q **QUALIFIED AT THIS CELL TYPE** at its slot count" | "P10-I-S0 (ADR-0023) registers, by its §7 procedure, step 3 (**OVERLOAD-QUALIFIED UP TO L_Q**) or step 4, 5 or 6 (each ending **ADDRESSING QUALIFIED UP TO L_Q**), recomputed and accepted. The system is A5-D as ADR-0023 freezes it, at one of ADR-0023's tested cell types (§4.1) with load at most L_Q, where Line Q HOLDS (§6.4) (ADR-0023 §15 items 1–2)." If the lead wants to exclude steps 4 and 5, the draft must give the reason and mark it `PENDING LEAD REVIEW` |
| Y2 | ADR-0028 L62 (Q2) | "**No sibling draft registers this.** ADR-0024's C-CAPACITY is oracle-addressed … and has no learned-address lane, so CAPACITY-POSITIVE there does not satisfy Q2 … Q2 needs a registered label from a later approved study of the composed system, or a reference check inside S5 …" | "ADR-0024's C-CAPACITY is oracle-addressed and does not satisfy Q2. ADR-0024's lane L (§13) trains the same A5-D system at ADR-0023's licensed cells; its line L-CAPACITY = **LEARNED-ADDRESS GAIN FROM SLOTS** is a candidate source, with N the larger cell of a licensed step it read. Whether a gain-from-slots label with no dense or saturation reading is "useful capacity" in Q2's sense is `PENDING LEAD REVIEW`. Otherwise Q2 needs a registered label from a later approved study, or a reference check inside S5 whose rule is fixed before any calibration draw is observed." |
| Y3 | ADR-0028 L67 | "At 16,384 slots the store is about 3 MB. So no outcome … can make Q1 and Q3 true together …, and Q2 has no registered source." | "ADR-0023 licenses learned addressing only at its tested cell types with load ≤ L_Q (§15 item 1); the largest is 8K/16K, and ADR-0024's lane L uses only those cells. At 16,384 slots the store is about 3.15 MB. So no outcome of P10-I-S0 to S3, and no lane L outcome, can make Q1, Q2 and Q3 true together without restricting RAM by construction." (The rest of the paragraph stands.) |
| Y4 | ADR-0028 L186 (§11 item 1) | "Hold E1 and E2 until ADR-0024's R-DIAGNOSIS has shown which read path is worth benchmarking." | "Hold E1 and E2 until ADR-0029's R-DIAGNOSIS is recorded and accepted (with R-CONFIRM if Stage A2 is funded). If it is CHECKPOINT-DEPENDENT or NOT EVALUABLE, it names no read path, and the human lead decides." |
| Y5 | ADR-0028 L179 (§10 seeds) | "Seeds: proposed namespace **280001–289999** … Sibling drafts …: ADR-0023 300001–309999; ADR-0024 240001–249999; ADR-0025 250001–259999; ADR-0026 initialisation 2601–2691; ADR-0027 270001–279999." | "Seeds are those of `SEED_REGISTRY.md` §4.2: registered workloads, store contents and arm orders 280001–286999; auxiliary 287001–288999; R1 289001–289199; rehearsal 289201–289299; initialisation 330501–330599 only if a memory initialiser is used; tests 937001–937999. Roles and counts: [to be written: seeds per workload, per store layout, per block's arm order and per repeat; R1's]. The G9 gate re-runs the registry checker before the freeze." |
| Z1 | `CLOSURE_LEDGER.md` L16 (not one of the two drafts; listed for the lead) | "S1 (ADR-0024, capacity scaling, with the frozen-checkpoint routing diagnosis lane)" | "S1 (ADR-0024, capacity scaling); routing diagnosis in ADR-0029 (PENDING HUMAN LEAD RULING on the split)" |

Closure ledger, items for these two studies: H4 "CARRIED INTO P10-I-S5" (L34) is taken up (ADR-0028 §1, §14). "A matched-cost quality comparison belongs to P10-I-S4 if entered" (L101) is taken up (ADR-0027 §1, §5). Platform of record (L135) is taken up in both (§13 and §12). Lane C locality (L57) is answered by S5's own entry criteria. No carried item is left unaddressed.

Seed registry: the reviewer re-ran the checker. It gave `RESULT: PASS`, exit 0, checker SHA-256 `6e1e0ea3…f30f`, equal to the hash in `SEED_REGISTRY.md` §6. Neither draft names a value that conflicts with the registry's allocation **except** ADR-0027's 2701–2799 (X8). Both drafts' sibling lists are out of date (X8, Y5).

## Part D. Choices reserved for the human lead, judged

| Draft, item | Choice | Really the human lead's? |
|---|---|---|
| 0027 §11.1 | Backbone; LoRA NOT APPLICABLE | Yes |
| 0027 §11.2 | Route B alone; reading of "P10-S1" | Yes (note the disagreement with ADR-0026, S4-N12) |
| 0027 §11.3 | MC-A plus MC-T for a favourable label | Yes; the draft makes a recommendation |
| 0027 §11.4 | Energy | Yes (administrator access) |
| 0027 §11.5 | 4 of 5, factor 2 | Yes (scientific thresholds, proposed with reasons) |
| 0027 §11.6 | Product-key alternative | Yes, but the recommendation rests on a removed arm (X6) |
| 0027 §11.7 | Entry, cap, approval | Yes |
| 0027 §12 (not reserved) | Rate grid, D+ grid, convergence rule, quiet load figure | **Partly misplaced.** The D+ selection rule (S4-N7) and the ceiling on the quiet load figure (S4-N5) are missing rules, not later parameters. The ADR-0026 open choice 13 that Route A depends on is pre-empted in A2 instead of being deferred to it (S4-N1) |
| 0028 §11.1 | Engineering part before a neural memory is qualified | Yes |
| 0028 §11.2 | Write budget, endurance figure, "large" | Yes |
| 0028 §11.3 | Administrator and tool actions | Yes |
| 0028 §11.4 | Baseline implementations / dependency amendment | Yes |
| 0028 §11.5 | Scientific part as capped | Yes; the reason should be restated (Y2, Y3) |
| 0028 §11.6 | R_min, U, cache ratios, 4 of 5 | Yes, but U's definition is a missing rule, not a choice (S5-N3) |
| 0028 §11.7 | Entry per part | Yes |
| 0028 §13 (not reserved) | Resident budget "fixed at the freeze" | **Missing rule.** It decides the comparison with S-FLAT (S5-N4); it should be ruled before R1 or reserved explicitly |
| 0028 Q2 (new) | Whether L-CAPACITY counts as useful capacity | Yes, `PENDING LEAD REVIEW` (S5-N2) |

## Commands and environment

Environment: macOS 27.2.1 (build 26B131), Darwin 27.2.0, arm64. System `python3 -I` for the arithmetic below; `uv run --locked` (Python 3.12.14 from the lock) for the registry checker. No `arborlm.*` module and no implementer summary script was imported. All commands were read-only and run from the worktree root on 2026-11-17 between about 21:40 and 22:10 UTC.

- Reads: the two drafts; `REVIEW_ADR-0027_ADR-0028.md`; ADR-0024 and ADR-0026 in full; ADR-0023 §4.1–4.2, §6.4–6.6, §7, §15 (`sed -n`); ADR-0029 headings, §1, §9–§10 (`grep -n`); `SEED_REGISTRY.md` §4.2–§7; `CLOSURE_LEDGER.md` and `DIRECTION.md` (`grep -n`); `AGENTS.md`.
- `git diff --stat c525898 HEAD -- docs/decisions/ADR-0027* docs/decisions/ADR-0028*` (276 insertions, 142 deletions).
- `grep -n "needs both cost readings" docs/decisions/*.md`: found only in ADR-0027 L108, not in ADR-0024 (X7). `grep -n "5\.4|MC-AMBIGUOUS" ADR-0021`: L184, L193 (the comparator rule).
- Record checks: `grep -n` and `sed -n 205,218p` on `results/p10s1-run-2026-11-17/RESULTS.md` (L216 header "Analytic multiply-adds to U_P"; L221 D-OQ 8K/16K 2.65e+12, CPU 138.2 s; L252 T-OQ 5.21e+11, CPU 115.3 s; L262, L275 CPU per update 0.0120423, 0.0115605, ratio 0.960); `OUTCOME.md` L88 (0.401/0.697, 0.916/0.992, 0.957/0.999); `results/p8-2026-11-14/SUMMARY.md` L30, L49 (N_eff definition, 127 of 4,096); `ADR-0015` L119.
- Seed registry: `timeout 120 uv run --locked python docs/reviews/p10-i-direction-2026-11-17/seed_registry_check.py | tail -5` → `RESULT: PASS`, exit 0; `shasum -a 256` of the checker → `6e1e0ea34fd9fef22f9ef13445460468b4c34e88fef2ed9e27dfe919c8edf30f`.
- Uniform-placement utilisation (S5-N3): `python3 -I -c` computing exp(−E[(c/λ) ln(c/λ)]) for c ~ Poisson(λ), summed to c = 400. Results: λ = 0.5 → 0.365, 1 → 0.564, 2 → 0.752, 4 → 0.875, 8 → 0.938, 16 → 0.969, 64 → 0.992. This is the large-N approximation for uniform random selection.
- Device re-check (S5-N9): `df -k /` (1,948,404,040 KiB total, 708,290,284 available); `sysctl -n hw.memsize` (51,539,607,552); `which smartctl` (not found); `sw_vers`.

Failed or empty checker attempts: none in this review. One discrepancy found that traces to the first review rather than to the drafter: its A-B1 called the 5.21e11 / 2.65e12 figures "per update", and they are cumulative to U_P (S4-N11).

Nothing was run that trains, benchmarks, writes to a store or changes a setting. The sealed recall values in P10-S1's cell records were not opened. This file is the only file created; nothing else was edited, and no git write was made.

`Astra review: NOT_PERFORMED`. Claude review is not Astra review. This review is by the `arbor-auditor` subagent (Claude Opus 5.5) and is not human approval.
