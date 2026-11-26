# Confirmation read of ADR-0024 with the third review's edits applied (block M), commit f875bb1

- Reader: `arbor-auditor` subagent, Claude Opus 5.5 (`claude-opus-5-5`). I wrote REVIEW3_ADR-0024 (the review whose edits were applied). I did not write any of the text added at f875bb1, and I judge the rules nobody has reviewed as new rules. This read is independent engineering and mathematical evidence. It is not Astra validation and not a human approval. `Astra review: NOT_PERFORMED`.
- Read (READ-ONLY): worktree `agent-ab85673ff3c4d1eb2`, branch `claude/p10-i-s1`, commit `f875bb1`. `git diff ef5596b f875bb1 -- docs/decisions/ADR-0024-p10-i-s1-capacity-scaling.md` (only this ADR and REVIEW3 changed: `--stat` shows 2 files), the ADR in full (679 lines), REVIEW3_ADR-0024.md, ADR-0021 §5.4, §8.2–§8.10, DELEGATION_2026-11-18.md, and P10-S1 audit outputs `a3_lines.out` and `a4_dep_sensitivity.out`. No eval.json, checkpoint or sealed value was opened. No git write.
- Environment: Darwin 27.2.0 arm64, `python3` 3.15.1 run as `python3 -I -B`, standard library only. Nothing is imported from `arborlm`, `studies` or any analysis module.
- Scripts and outputs are in this folder:
  - `python3 -I -B r4_0024_cost.py <agent worktree>/results/p10s1-run-2026-11-17 > r4_0024_cost.out` uses the labels and `seconds` of the tasks in `manifests/train.manifest.json`, plus `ledger_after_run.json`.
  - `python3 -I -B r4_0024_cost2.py > r4_0024_cost2.out` covers the ladder, the base plan, the calibration makespan and H8's calibration share.
  - Check of method: charged training time in P10-S1 is the stage's wall time, 49,251 s. The sum of task seconds divided by 6 gives 49,223 s, within 0.06%.

## Verdict

**CONFIRMED WITH THE LISTED CORRECTIONS.** E1–E9, E11 and E12 are applied as §22.3 says. E10 was replaced by a stricter reduction of block X, and E6 by a stricter, explicit-decision rule. Block X and lane L are not approved, and block M depends on neither. The three P10-S1 counterfactual statements check out (section 3).

The added rules hold seven defects that an implementer would have to guess at, or that contradict another rule: C1–C7, all of which affect code. Two of them, C5 and C6, contain a choice I mark **PENDING LEAD REVIEW**. I give a default, and in each case the default is not more lenient to the store. Implementation can start now on everything except the plan/projection code (§17.1), the MC-C reading (§8.2/§9.2) and the quiet-decision path (§16). Those three wait for C1–C7.

## 1. Corrections that affect code (old text → new text)

**C1. MC-C has two definitions that contradict each other (§8.2 against §9.2).**
- In §8.2, the clause after the colon reads "the cell whose advantage would be claimed … is read at U_P, and the other at …". That holds in every case. The sentence after it says that where the measures agree, MC-C is the larger-multiplier one of MC-A and MC-T. ADR-0021 §5.4 says the same.
- §9.2 then says "(the arm at U_P, D-OQ at the later snapshot)". That is wrong in the normal case where D-OQ costs more in both measures, as for F-OQ in P10-S1. There ADR-0021 reads D-OQ at U_P and the arm later.
- Read literally, §9.2 gives D-OQ more compute than the arm. That is harsher than ADR-0021 and not equal compute.
- §8.2: "a third reading **MC-C** that exists only where MC-T is measured: the cell whose advantage would be claimed (…) is read at U_P, and the other at the smallest grid snapshot whose multiplier is at least the largest of r and 1/r over both measures, r being … Where the measures agree on the direction, MC-C is the one of MC-A and MC-T with the larger multiplier. Where they disagree, MC-AMBIGUOUS is printed and MC-C is a snapshot of its own." → "a third reading **MC-C** that exists only where MC-T is measured. (i) Where MC-A and MC-T agree on which cell of the pair costs more per update, MC-C is whichever of the MC-A and MC-T readings has the larger multiplier: the costlier cell at U_P, the cheaper at that reading's matched snapshot. A measure in which the two costs per update are exactly equal counts as agreeing with the other measure. (ii) Where they disagree (MC-AMBIGUOUS, printed), the cell whose advantage would be claimed (the larger cell in §9.1; the memory arm in §9.2) is read at U_P, and the other at the smallest grid snapshot whose multiplier is at least the largest of r and 1/r over both measures, r being the ratio of the two cells' costs per update in a measure (ADR-0021 §5.4)."
- §9.2: "the comparator reading **MC-C** of §8.2 (the arm at U_P, D-OQ at the later snapshot)" → "the comparator reading **MC-C** of §8.2 (as defined there; under MC-AMBIGUOUS the arm at U_P and D-OQ at the later snapshot)".
- The agent's reason for adding MC-C is correct, and I endorse it. E2's "U_MC = U_P in a reading where the larger cell is cheaper" is more lenient than ADR-0021 when the measures disagree. ADR-0021 then reads the smaller cell at max(r_A, 1/r_T). MC-C can only add a condition: in the agree case it equals one of the readings row 4 already requires. It is fixed before observation, computable and reachable. It also never reads the larger (claimed) cell late in the agree-cheaper case, so it cannot favour the store there.

**C2. The grant levels are not always ladder points (§7.2 items 6 and 7, §17.1 items 3 and 5, rulings 9 and 11).**
- The ladder is 65,536 × {1, 1.5, 2, 3, 4, 6, …}. For U₀ = 1.5·2^k·65,536, the points 1.5·U₀ and 3·U₀ are **not** on it. P10-S1's own lengths 393,216 and 786,432 are of that form.
- From those U₀ the next four ladder points are 1.333, 2, 2.667 and 4 × U₀ (`r4_0024_cost2.out`). A G of 1.5·U₀ would have no "full at two consecutive ladder points" test and no snapshot schedule.
- §7.2 item 6: "G is one of U₀ × {1, 1.5, 2, 3, 4}, at most **4 · U₀**" → "G is U₀ or one of the first four ladder points above U₀ (the fourth is always 4 · U₀)".
- §17.1 item 3: "The steps are the ladder points above U₀: 1.5 · U₀, 2 · U₀, 3 · U₀, 4 · U₀. Steps are considered level by level (all cell types at 1.5 · U₀ first, then 2 · U₀, and so on)." → "Level j (j = 1…4) of a cell type is the j-th ladder point above that cell type's U₀; level 4 is 4 · U₀. Levels are considered in order j = 1, 2, 3, 4, all cell types at level j before any at level j + 1."
- §17.1 item 5: "fewer multiples of U₀" → "a lower level". This keeps "never less": D-OQ's U₀ is the larger of the store arms' U₀, so its j-th ladder point is never below theirs.

**C3. The projection's charged time is undefined for long items (§17.1 item 1, §15).**
- Charged time is stage wall time. In P10-S1 it equalled sum/6 only because the items were balanced.
- With run-until-full items it does not. One T-OQ 32K/4K item at 4·U₀ (U₀ at the ceiling) is 42.7 h. The calibration load search at the ceiling is 9.1 h by sum/6 but 10.7 h by makespan.
- Add to item 1: "The projected charged time of a stage is the makespan of a longest-processing-time-first schedule of its items (each at its rehearsal seconds per update times the contention ratio) on the stage's worker count, and never less than its longest item."

**C4. Timing of the projection (§17.1 item 1 against §18).**
- §18 writes the candidate plan **before** the measuring rehearsal. §17.1 item 1 says the projection is computed "when the candidate plan is written", from the measuring rehearsal's rates.
- §17.1 item 1: "The projection is computed once, by the frozen projection code, when the candidate plan is written" → "The candidate plan is first written with every loaded cell listed to 4 · U₀. The projection is computed once, by the frozen projection code, after the measuring rehearsal, when the caps and the granted lengths are written into the candidate plan; items beyond G are then removed, and the counting rehearsal's hours are included as projected."

**C5. The caps and the 60-hour budget contradict each other (§15 rows 1 and 3, §17.1 item 8, §24). PENDING LEAD REVIEW for the choice.**
- Caps are set as "charged + 2 × projected remaining". With a 1× projection near 60 and about 12 h already charged, the caps come to about 108.
- Truncating them to sum to 60 removes the headroom entirely. Any slowdown, including the machine sharing that §16.1 item 3 expects, then PAUSES the run, and the extension goes to the human lead. The text also does not say how a truncated sum is divided among stages.
- I propose two coherent texts. Choose one.
- **(A) Default: keeps 60 as the most hours ever charged without the human lead.**
  - §17.1 first paragraph: "is at most 60 hours" → "is at most B = (60 + H_c)/2 hours, where H_c is the hours already charged when the projection is made, so that the caps of §15's rule (charged + 2 × projected remaining) sum to at most 60".
  - §17.1 item 8: replace "where the rule gives more, the caps are set to sum to 60 and a stage that reaches its cap is PAUSED" with "by construction of B the rule never gives more".
- **(B) Keeps 60 at 1×.**
  - §17.1 item 8 → "Caps follow §15's rule unchanged and may sum to up to 120 − H_c hours; setting them is the human lead's own decision whenever their sum exceeds 60."
  - §24 bullet "a sum of caps above 60 charged hours" stays as written.
- Under (A), with H_c ≈ 12–15 h, B ≈ 36–37. At U₀ = 2× P10-S1's lengths the base plan (about 37) then reaches B (§2 below).

**C6. The grant order can give D-OQ more training than a store arm, and H8 less than F-OQ (§17.1 items 3–5). PENDING LEAD REVIEW.**
- The order cannot leave D-OQ with *less* training than a store arm: item 5, together with D-OQ's U₀ = max. That part is fixed before observation and uses only rehearsal rates and calibration-draw U₀.
- The reverse is possible. Item 4 closes only the cell type that did not fit, so D-OQ (granted first) can keep receiving later levels after T-OQ at the same cell was closed. At 32K/4K, D-OQ costs 0.00875 s per update against T-OQ's 0.01221.
- Dense at saturation reads "each arm at its own full length". A store arm left NOT FULL WITHIN BUDGET against a longer-trained D-OQ can then produce DENSE HOLDS MORE, and with it CAPACITY-NEGATIVE (b). ADR-0021 §8.5 read both at the same U_L.
- H8 is last in the order, so it can end below F-OQ. That makes KEY-LEARNING-LIMITED (the only label against learned keys) harder to reach. It enters no outcome.
- Items 3–5 → "A grant covers a loaded cell, all its arms and all five replicates at once, costed as if every replicate used it. Within a level the cells are taken in the order 2K/256, 8K/1K, 32K/4K. A cell whose next level would exceed the budget is closed. Every arm at a cell therefore has the same level; D-OQ and H8, whose U₀ is the larger of F-OQ's and T-OQ's, never have fewer updates than a store arm."

**C7. The quiet-condition decision for throughput (§16 bullet 4, ruling 25).**
- "written into the run's records before training starts" cannot hold for the throughput stage, which runs after training. The text also does not say whether analysis and report wait while throughput is PAUSED.
- Add: "For the throughput stage the decision is written before the report stage; analysis and report do not wait for it, and print THROUGHPUT PENDING while it is PAUSED."

## 2. Other corrections (wording and figures)

**C8. "undecided, not negative" is not accurate (§17.1 last paragraph, §20 item 4).**
- Under §9.1, a smaller cell that is not full cannot give CAPACITY, NULL or FLAT. It can still give REVERSED or BEHIND WITHIN BUDGET, which need no full cell. Those come before NOT FULL WITHIN BUDGET in the step class order, and they can make an arm CAPACITY_NOT_SUPPORTED, which leads to NEGATIVE (a).
- An arm that is not full also still enters dense at saturation at its own length, which leads to NEGATIVE (b).
- This is the same structure as ADR-0021. Only the sentence is wrong.
- "its step and its saturation pair are then not decided" / "undecided, not negative" → "its saturation pair is NOT FULL and its step cannot be CAPACITY, NULL or FLAT; the step can still be REVERSED or BEHIND WITHIN BUDGET, and the arm still enters dense at saturation at its own length".

**C9. The cost figures, recomputed (`r4_0024_cost.out`, `r4_0024_cost2.out`). They are sums divided by 6 unless stated.**

| Agent's figure | My figure | Agrees? |
|---|---|---|
| Training of 120 cells, "10" | 10.01 h for the 115 cells P10-S1 ran, 10.47 h with an estimate for 2K/256 | Yes |
| Loaded F/T/D, "about 7.7" | 7.38 h (7.83 h with 2K/256) | Yes |
| H8, "1.5 h", "1.1 h" at loaded cells | 1.51 h and 1.12 h | Yes |
| H8 per loaded cell, "1,619 s and 3,204 s" | 1,619 s and 3,204 s | Yes |
| Beyond P10-S1's lengths at the ceiling, "about 116" and "about 17" | 117.5 h and 16.8 h; the F/T/D/2K/256 total at 16× is 125.3 h | Yes |
| Extensions to 4·U₀, "26 / 53 / 79 / 106" | 26.5 / 53.0 / 79.5 / 106.1 h | Yes |
| Totals "21 / 29 / about 170" | Low 9 + 1.5 + 0 + 9 + 2 = 21.5; central 28.5; upper about 172 | Arithmetically consistent with the rows |

- H8's calibration share is not stated in the ADR. My estimate is about 0.35 charged hours.
- **The base-plan column is not right at the top end.** I anchor at the agent's 1× base of 26. Each 1× of U₀ then adds 8.8 h (loaded cells at U₀, with D-OQ, H8 and 2K/256) plus the calibration load search: 2.3 h by sum/6, or 2.7 h by makespan. That gives:
  - 2×: 37.1–37.5 (the agent has 36);
  - 4×: **59.2–60.4** (the agent has **64**).
- So "the base plan does not fit" at the ceiling is not a reliable statement. It sits at the budget's edge, and the rule decides.
- "Three times P10-S1's lengths" cannot occur. U₀ is a ladder point, so the possible multiples are 1, 1.333, 2, 2.667 and 4.
- Table rows: "three times P10-S1's lengths | about 46 | about 79 |" → "2.667 times | about 45 | about 71 |". "the calibration ceiling (four times) | about 64 | about 106 | The base plan does not fit. …" → "| about 59–61 | about 106 | At the budget's edge: by item 2's rule either no extension is granted or the work returns as item 2 states".
- §17 sentence: "60 was the upper figure he was shown" → "60 was draft 3's upper figure". The delegation record (§4) shows only "capacity about 26 with an unbounded conditional block".

**C10. The return of a base plan above budget, as a rule (§17.1 item 2).**
- "**If the base plan alone projects above 60 hours, the work returns to the human lead before the freeze**, with the projection. The lead drops no cell, arm or replicate and shortens no length to make it fit." → "If the base plan alone projects above the budget, the projection code writes BASE PLAN ABOVE BUDGET into the candidate plan, the freeze refuses that plan, and the work returns to the human lead with the projection. His options are exactly two, as for §7.2 item 5: (i) block M is not run, and every C line is recorded NOT RUN — BASE PLAN ABOVE BUDGET; (ii) he raises the budget by a recorded decision on the projection alone. Neither option is taken under the delegation. No cell, arm, replicate, length, ceiling or threshold changes."

**C11. Ruling 26 (memory check) leaves the measure and the deadline open.**
- Name both. Default: "available memory = (free + inactive + purgeable + speculative pages) × page size from `vm_stat`; the wait is retried every 10 minutes for at most 6 hours, then PAUSED — ENVIRONMENT". **PENDING LEAD REVIEW** for the figures.

**C12. Ruling 17, the conservative form.** The direction is sound: a D-OQ dependence failure only blocks store-favouring labels and never deletes a dense lead. It is stricter than ADR-0021 and stricter than my recommendation, and it is computable. Name the snapshots it reads:
- "that D-OQ snapshot" → "each D-OQ snapshot the label's rule reads: U_P and the matched snapshots (MU, MC-A, MC-T, MC-C), D-OQ's best snapshot (D-BEST), the snapshot attaining i\* and U_run/2 (STORE HOLDS MORE), and s_prev and s_hit (DENSE NOT FASTER)".

**C13. H8's units can return the work (§4 last bullet).** A RATE AT EDGE or an all-diverged H8 unit returns the work by §7.1. "H8 gates nothing" → "H8's annotations gate nothing; its rate units follow §7.1 like every arm's".

**C14. H8's four runs to U_P (§4).** Add "after the last selection of §7.1 step 3". H8's 4,096-slot rate can be re-selected when U_P of the 8,192 row moves, and 2K/4K uses that rate.

## 3. The specific questions

- **MC-C.** The reason is correct (C1). Defined as in C1, it restores ADR-0021 §5.4 exactly where MC-T is measured. It is fixed before observation, cannot favour the store and is reachable.
- **Grant order.**
  - Fixed before observation: yes.
  - Rehearsal rates only: yes, plus U₀ from the calibration draws, which are not registered.
  - Can it leave D-OQ with less training than a store arm? No.
  - The reverse? Yes, and H8 can end below F-OQ (C6).
  - "NOT FULL WITHIN BUDGET … undecided, not negative": half right (C8).
- **H8.** The rate search and calibration are consistent with ADR-0021 §8.4 and §10.1 (UNDERTRAINED-AT-U_P, and NOT CALIBRATED at the loaded cells). 2K/1K is now calibrated because it is a selection cell. Two corrections apply: C13 and C14.
- **Rulings 21–26.**
  - 21, 22, 23 and 24: sound (24 also needs C2–C4 in its planted tests).
  - 25: consistent, since 1 + 5 = six PAUSED attempts, but it needs C7.
  - 26: needs C11.
  - 17: see C12.
- **E6.** Five rescheduled attempts, then the stage stays PAUSED, and NOT MEASURED needs an explicit decision. §10, §15, §16 and ruling 25 agree with each other. It is reachable, and it can only remove store-favouring labels. Only the throughput case is broken (C7).
- **E4 / DENSE SPEED UNDECIDED.** Row 3 needs DENSE NOT FASTER (above 0.8 in all 5) at every cell in both readings. That is stricter than ADR-0021's "not DENSE FASTER". Row 4 is my E4 word for word. The rename is consistent.
- **E3.** Applied as I wrote it, with MC-C added on both sides.
- **E10 / block X; E7; E12.**
  - §12 holds only constraints. No block M rule, budget or seed reads block X or lane L. §22.2 flags its stale pointers to §12 as history.
  - §18's "each by SHA-256", followed by "by comparison with the freeze commit", is refined by "In detail". Not a contradiction.
  - Advisory: state that the imported set is the transitive closure from a static import walk, listed in the freeze record.
  - §23 rulings 1–20 match my section F word for word, with the adopted forms beside them.
- **The statement beside §9.3, checked against the audit's recorded figures (`a3_lines.out`, `a4_dep_sensitivity.out`).**
  - **Registered rules plus the new dense and split rules give EFFICIENCY-NEGATIVE.** F-OQ is EFFICIENCY_NOT_SUPPORTED: N1 and N2 are SAME in all 5, because u ratios of 0.53–0.64 exceed 0.5 in every reading. T-OQ is a FASTER STEP at N1 and N2, with cost ratios at most 0.51 in both measures, so it is supported in E-A and in E-T. D-OQ is faster at 2K/4K in both readings (cpu 0.083–0.118, madds 0.32–0.46, 5/5). Row 4 clause 2 therefore applies.
  - **They also give CAPACITY-INCONCLUSIVE.** F-OQ and F-OQ-IVF are DEPENDENCE_FAILED and T-OQ is INTERMEDIATE. T-OQ's steps are GAIN WITHIN BUDGET or MIXED, which come before NOT FULL WITHIN BUDGET, so it does not become NOT_TESTED_BY_LOAD. No arm is CAPACITY_SUPPORTED.
  - **With DEP-c it would be CAPACITY-NEGATIVE (b): confirmed, conditionally.**
    - All 32 failures are from the 0.95 condition, and DEP-c fails none of them.
    - In "DEP mode none", F-OQ is CAPACITY_SUPPORTED (C1 and C2 are CAPACITY STEPs; a_use at 32K/16K is 0.909). F-OQ-IVF and T-OQ are INTERMEDIATE.
    - F-OQ is DENSE AHEAD at C2 (MU 4/5, D-BEST 5/5) and has DENSE HOLDS MORE at both loaded cells, 5/5.
    - The condition: DEP-c must also fail none of the other reads. That is the first review's "0 of 4,394", which needs eval.json and is not recomputed here.
    - A read that passes the 0.95 condition can in principle fail DEP-c at high accuracy. From the recorded means, raw − a_use ≤ 0.011 in every cell type. That is below the 0.01 + (1 − a_use)·b/n that DEP-c (ii) needs.
- **§24.**
  - Accurate: the quoted second sentence is not in DELEGATION_2026-11-18.md at ef5596b or f875bb1. Section 6 there holds a different, 24-hour grant.
  - §24 should add that §6 exists and that it does not change what Decision 1 covers.
  - The header and §22 sentence "has not been reviewed again" is now superseded by this read. Update it when C1–C14 are applied.
- **Nothing else changed.** `git diff --stat ef5596b f875bb1` lists only the ADR and REVIEW3. Every § reference I followed resolves. Apart from C1, C2, C4, C5 and C7, I found no rule that contradicts another.

`Astra review: NOT_PERFORMED`. Claude review is not Astra review. This read is not a human approval.
