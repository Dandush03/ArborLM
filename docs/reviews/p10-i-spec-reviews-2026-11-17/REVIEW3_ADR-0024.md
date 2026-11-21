# Third review of ADR-0024 draft 3 (P10-I-S1, useful capacity scaling), for approval readiness

- **Reviewer:** the `arbor-auditor` subagent. Model as I know it: Claude Opus 5.5 (`claude-opus-5-5`). I wrote no part of ADR-0024 and none of the P10-S1 code or records I read. This review is independent engineering and mathematical evidence. It is **not** Astra validation and **not** a human approval. `Astra review: NOT_PERFORMED`. Claude review is not Astra review. Where a point is a scientific choice it is marked **PENDING LEAD REVIEW** or reserved to the human lead.
- **Draft reviewed:** `docs/decisions/ADR-0024-p10-i-s1-capacity-scaling.md`, 476 lines, SHA-256 `ae5da48ee4189280867c78b52150678b3adb1990519c786907faca870fbd8989`. Worktree `arborlm-consolidation-experiment-2b31c1`, branch `claude/p10-i-r`, HEAD `ef5596b` when I finished (the session began at `fc14159`; the draft file did not change between them as far as I read it).
- **Nothing was written** in the worktree except this file and my scripts in `experiments/_scratch/reviews3/` (git-ignored; `git check-ignore` confirmed). No git write. No training, no generation, no network. No `eval.json`, no checkpoint and no sealed value was opened.

## Verdict

**Block M: READY AFTER THE LISTED EDITS** (section E gives every edit as text). No finding is blocking once those edits are made. **Block X: NOT READY. Defer it to its own decision after block M** (edit E10). Several engineering items are missing, and its funding figure is a large cost that the human lead must set himself. **Lane L** is correctly excluded from this approval. One wording fix and one missing printed state remain (E11).

Do not take two of the draft's open choices under the delegation. Both narrow a negative in the store's favour, and both were written after P10-S1's readings were seen:

- §21 item 4, the dense reading;
- §21 item 6, the symmetric split rule.

E3 and E4 give the stricter text to adopt in their place. Two more items need the human lead himself:

- H_X (§21 item 2), a cost of about 100 charged hours. The human lead was told "capacity about 26".
- The cost bound of block M's design ceilings (F7).

Dropping H8 (§21 item 5) also leans towards the store by leaving a test out. I recommend keeping H8 or asking the human lead (F17).

## A. Method, commands, environment

- Machine: Darwin 27.2.0 arm64. Scripts: `/opt/homebrew/bin/python3` 3.15.1, run as `python3 -I -B`, standard library only. They import nothing from `arborlm`, `studies` or the implementer's analysis code. Scripts and outputs are in `experiments/_scratch/reviews3/`:
  - `r3_0024_spu.py <results/p10s1-run-2026-11-17>`: seconds per update per (arm, facts, slots), computed as each training task's `seconds` divided by `run_updates` from the cell's `train.json` (metadata only), from `manifests/train.manifest.json`.
    - **Attempt 1 (kept, `r3_0024_spu.attempt1.out`):** my label regex did not allow the `_lr<rate>` suffix, so every D-OQ cell was silently dropped. This was my error, not a defect in the records.
    - **Attempt 2 (`r3_0024_spu_v2.py`, `.out`):** the suffix is parsed, and the D-OQ figures appear.
  - `r3_0024_eval.py <results dir>`: evaluation seconds per snapshot per cell type. It reads `manifests/evaluate.manifest.json` and counts snapshot directories by listing only; no `eval.json` is opened.
  - `r3_0024_depc.py results/p10s1-run-2026-11-17/audit/a4_dep_sensitivity.out`: DEP-c of §8.1 on the 32 recorded reads that failed P10-S1's 0.95 condition. It uses an exact binomial in log space, with p⁺ taken from the G2 upper ends 100/2,048, 325/8,192 and 1,159/32,768.
  - `r3_0024_arith.py`: code crowding, the ladder, the ceilings and the cost bounds.
  - `timeout 300 python3 -I -B docs/reviews/p10-i-direction-2026-11-17/seed_registry_check_r3.py > r3_0024_seedcheck.out`. The checker's SHA-256 is `e4623604…c67594`, which matches registry revision 3.
- Code read: `studies/p10s1/core.py` (seed layout, grid, `SEED_RANGE`); `studies/p10s1/evaluate.py` `panel_counts` (useful = correct with the own read and wrong under the swap); `studies/p10s1/timing.py` (`wait_for_quiet`, `concurrency_check`); `studies/p10s1/stages.py` (concurrency guard); `studies/p10s1/classes.py` (MC readouts in both measures); `studies/p10ir/plan.py` lines 268–310 (a dirty-tree refusal).
- Documents read: ADR-0021 §5, §8, §10.1; ADR-0029 §11–§20; REVIEW2; DIRECTION; DELEGATION; SEED_REGISTRY r3; ACCEPTANCE; ADR-0027 Route B; ADR-0028 Q2; ADR-0023 §15.

## B. Numbers checked

| Claim (draft) | My result | Verdict |
|---|---|---|
| §2 item 11: crowding 0.111 / 0.377 / 0.849 / 0.999 | P(cos > 0.8) = 5.773e-5 for independent unit vectors in R¹⁶. Shares 0.111 / 0.377 / 0.849 / 0.999 | Matches |
| §2 item 10: "All 32 reads that failed the 0.95 condition pass" DEP-c | 0 of 32 fail; largest excess among them +0.0069 of n (`r3_0024_depc.out`) | Matches. The totals "0 of 4,394" and "+0.0101" need per-read counts that sit only in `eval.json`. **Not recomputed** |
| §7.2 ceilings 1,572,864 and 3,145,728 are ladder points; 4·U₀ is always a ladder point | Ladder 65,536 × {1, 1.5, 2, 3, 4, …}: both are on it, and 4·U is on it for every ladder U | Matches |
| §9.2 "0.0216 against 0.0124 s per update at 32K/16K" | D-OQ 0.02156, F-OQ 0.01244 (six-worker medians) | Matches. **But** T-OQ 0.01288 > D-OQ 0.01036 at 8K/4K and T-OQ 0.01161 > D-OQ 0.00513 at 8K/1K: the reason given holds for F-OQ, not for T-OQ at 4,096 slots (F16) |
| §17 seconds per update | F-OQ 0.00599 / 0.00497 / 0.0091–0.0092 / 0.0124–0.0136; T-OQ 0.0116–0.0147; D-OQ 0.0051 / 0.0088–0.0104 / 0.0177–0.0216 | Matches |
| §12 block X central 128K/16K "about 18", upper "about 71", one D-OQ cell "about 38 h" | 17.7 / 70.9 / 37.7 h | Matches |
| §12 block X totals (26 / 48 / > 120) | The table has no evaluation term. Scaling P10-S1's 26.9 s per snapshot at 32K/16K (F-OQ) to 131,072 facts and 65,536 slots gives about 3–8 additional charged hours. With it, the central P_X is about 102–112, above the suggested H_X of 100 | Under the central assumptions, block X is probably NOT FUNDED at H_X = 100 (F9) |
| §17 block M upper "about 60" | If U₀ sits at the calibration ceiling and every loaded cell runs to 4·U₀: about **124** charged hours for the loaded cells alone; the longest cell (T-OQ, 32K/4K) about **42.7 h** of wall time. Calibration's load search to its ceilings: about 54 worker-hours, longest single run about 10.7 h | The draft's upper case is not the bound its own ceilings allow (F7) |
| §6 G9 "requires RESULT: PASS" with the cited checker | The r3 checker now returns **RESULT: FAIL**, exit 1, 34 problems. All 34 are P10-I-R's own config and test literals (`configs/p10ir_routing.toml`, `tests/`) counted against P10-I-R's own allocation, the self-collision of ADR-0029 §19 ruling 6. ADR-0024's values show 0 actual collisions | G9 as written fails by construction (F3) |
| §9.1 matched compute reads MC-A only | P10-S1's registered `mc_multiplier` at F-OQ C1 and C2 was 1.689 and 1.697 (`analysis.json`), the **larger** of the two measures (ADR-0021 §5.4). MC-A alone can only give the same or an earlier snapshot | A relaxation of the positive that the draft does not disclose (F1) |

## C. Confirmation-review (REVIEW2) findings: status

| Finding | Status | Note |
|---|---|---|
| B-M1 MC snapshots at loaded cells | **FIXED** | §7.2 item 2 |
| B-M2 calibration ceilings | **FIXED** | The calibration "full" rule omits ADR-0021's i\* ≤ 4.0 (guess G7), and the cost bound is not stated (F7) |
| B-M3 order ambiguities | **FIXED** | All three texts present |
| B-M4 D-BEST and the disclosure | **PARTLY FIXED** | D-BEST is restored on the positive side. The new disclosure says "one thing is narrower". Two further narrowings are not disclosed: the any-cell to every-cell combination, and DENSE HOLDS MORE at *every* rather than *any* loaded cell. The capacity Δ_MC also reads MC-A only, a relaxation on the positive side that is not disclosed (F1, F2) |
| B-M5 lane L | **FIXED** | Approval approves nothing of lane L; nothing in M or X depends on it (checked: §0, §1, §9, §11, §12, §15). Two wording points remain (F12) |
| B-M6 block X draws and funding | **FIXED in design** (fresh draws; blind funding rule) | **NEW PROBLEM:** block X cannot be implemented as written (F8) |
| B-M7 X arm classes | **FIXED** | |
| B-M8 quiet wording | **FIXED** | Matches the ledger (202–376 s) and ADR-0021 §25.16 |
| B-M9 arm-level NOT APPLICABLE | **FIXED** | |
| B-M10 report defects named | **FIXED** | |
| B-M11 file name | **FIXED** | |
| B-M12 seed text | **PARTLY FIXED** | §6 still says the registry has not assigned block X's seeds; registry revision 2 confirmed them. G9 cites `seed_registry_check.py`, not `_r3` (F3) |
| B-M13 entry-label arms | **FIXED** | ADR-0027 Route B quotes it correctly |

## D. Findings

**F1. REQUIRED. §9.1, Δ_MC: a relaxation of the positive.**
- ADR-0021 §5.4 read the smaller cell at the larger of the two measures' multipliers.
- Draft 3 reads Δ_MC in MC-A alone. A CAPACITY verdict whose MC-T value is below 0.5 only carries NOT CONFIRMED.
- MC-A's multiplier is never larger than max(MC-A, MC-T), so a CAPACITY step can only become easier. In P10-S1 the multiplier used was 1.69, which reads the smaller cell at 2·U_P.
- §9.2 says "For a positive, nothing is relaxed", and §9.1 says every threshold is ADR-0021's. Neither discloses this.
- Edit **E2**.

**F2. REQUIRED, and not to be taken under the delegation. §9.2 and §9.5: the negative is narrowed in three ways, after P10-S1 was seen.**
- The three narrowings:
  - DENSE AHEAD needs matched compute;
  - an arm is DENSE AHEAD only at every cell;
  - DENSE HOLDS MORE counts only at every loaded cell. ADR-0021 §8.5 row 1 says "at any loaded cell".
- In §9.5, a negative needs every cell in both readings. The draft's own disclosure says this would turn P10-S1's registered EFFICIENCY-NEGATIVE into INCONCLUSIVE.
- Each change moves a result from NEGATIVE towards INCONCLUSIVE. Each was written knowing P10-S1's pattern: MU and D-BEST for D-OQ, MC for F-OQ, and DENSE FASTER at 2K/4K only.
- DELEGATION §3 says "No relaxation", and the brief excludes choices that could favour the memory.
- The reason given ("an update is not a resource; D-OQ costs more per update") holds for F-OQ. It does not hold for T-OQ at 4,096 slots, where D-OQ was the cheaper per update.
- My recommendation: **adopt the stricter text E3 and E4 under the delegation.** They keep ADR-0021's any-reading, any-cell negative and draft 3's stricter all-readings positive, and they print "NOT AT MATCHED COMPUTE" beside a dense lead held only at MU or D-BEST, so the information the narrowing wanted to convey is not lost. The narrower alternatives go to the human lead. **PENDING LEAD REVIEW** for the science; the direction (stricter for the store) is the one the delegation permits.

**F3. REQUIRED. §6, seeds and G9.**
- (a) The block X sentence is stale.
- (b) G9 names the revision-2 checker. The registry (§4.5 item 5, revision 3) requires a new file.
- (c) Any copy of the cited checker fails today on P10-I-R's own files, and will fail on P10-I-S1's own files once they exist.
- Edit **E1**, which adopts ADR-0029's ruling 6 approach.

**F4. REQUIRED. §16, the quiet condition.**
- (a) After 6 hours MC-T becomes NOT MEASURED for good, and that makes CAPACITY-POSITIVE and X-CAPACITY POSITIVE unreachable because the desktop was busy. This conflicts with DIRECTION §5: a study should not end on a limit of convenience. It also conflicts with ADR-0027 §6, which reschedules up to three further sessions and cites ADR-0024 as its model.
- (b) Only the load at the start is checked. P10-S1 also refused if another study's stage process was alive (`studies/p10s1/timing.py` `concurrency_check`). Another study starting mid-stage is not detected.
- (c) The timing preview is listed as needing quiet, but it feeds only item caps, and the draft does not say what a non-quiet preview means.
- (d) The quiet-condition deadline is not classified in §15.
- Edit **E6**.

**F5. REQUIRED. §18, the two-rehearsal procedure is missing.** The caps are set "after the rehearsal" and are also in the plan the rehearsal must use. ADR-0029 needed ruling 5 and §20 (a measuring rehearsal, then a counting rehearsal against the candidate plan whose hash the freeze checks) to resolve the same circularity. Edit **E8a**.

**F6. REQUIRED. §14 and §18, code and environment errors.**
- Missing: the equivalent of ADR-0029 ruling 11 (an `item_error` makes the analysis refuse), the PAUSED path for environment errors, and what a non-finite registered cell is.
- §9.3 row 2 does not say whether INCOMPLETE prints any outcome.
- Edit **E8b**.

**F7. REQUIRED. §17 and §15: the cost the design ceilings allow is not stated, and the cap projection's assumption is unstated.**
- Within the draft's own ceilings, the loaded cells alone could cost about 124 charged hours, with single cells of about 43 hours of wall time. The table's "upper about 60" assumes U₀ equal to P10-S1's lengths.
- The human lead was told "capacity about 26" (DELEGATION §4).
- Edit **E5**.

**F8. REQUIRED. §12, block X cannot be implemented as written.** These items are unspecified:

| Missing item | Detail |
|---|---|
| Calibration and rehearsal draws of 131,072 facts | No seeds in the registry. "re-selected on X's calibration" has no data |
| G2 chance interval | Not defined at n = 131,072. DEP-a, DEP-b, DEP-c and p⁺ all use it |
| U_P of the 32,768-fact row on X's draws | Selection cell 32K/64K? |
| MC-T at 65,536 slots | STORE NOT BEHIND at 128K/64K needs it, but §16's timing stage covers 256–16,384 slots only |
| F-OQ-IVF at 65,536 slots | 256 lists |
| Evaluation term of the cost table | Missing |
| Memory | At 131,072 facts, against the 3 GiB guard |

- H_X is a large cost and is not the delegation's to set.
- Edit **E10**: defer block X with its rules fixed now and H_X set by the human lead before block M's Decision 2.

**F9. ADVISORY, cost. At the suggested H_X of 100, block X is probably not funded.**
- The central P_X is about 96 without evaluation, and about 102–112 with it (B).
- P_X also assumes "every loaded cell full at U₀", so it is a low projection. A funded run can then reach H_X and PAUSE, and an extension goes back to the human lead.
- The human lead should see both facts when he sets H_X.

**F10. REQUIRED (mechanical). §18, the frozen-input set omits imported code and the lock file.** Block M reproduces P10-S1's model and evaluation (`studies/p10s1/`, `studies/p9/`, `src/arborlm/`). ADR-0029's implementation audit added the imported P10-S1 code to its freeze comparison. Edit **E7**.

**F11. REQUIRED (mechanical). §16, platform settings for the bit-exact gate G4 are not stated.** ADR-0029 R3-7 set the precedent. Edit **E9**.

**F12. ADVISORY. §13, lane L wording.**
- "Settled now" reads as approved rules, while the same section says nothing of lane L is approved.
- There is no printed value for the case where ADR-0023 licenses a cell before block M freezes.
- Edit **E11**.

**F13. ADVISORY. §8.1 and §9.3: no counterfactual disclosure for capacity.**
- DEP-c fails none of P10-S1's 32 failing reads, and the audit's run without those failures gives F-OQ CAPACITY_SUPPORTED (`audit/a4_dep_sensitivity.out`). Under draft 3's DEP, P10-S1's capacity line would therefore turn on the dense labels.
- With DENSE HOLDS MORE at both loaded cells in 5 of 5, it would be CAPACITY-NEGATIVE (b), under both draft 3 and E3.
- State this beside §9.3, as §9.5 does for efficiency. Text in E12 item 21.

**F14. ADVISORY. §12, N3 is costly and descriptive only.** N3 (32K/16K → 32K/64K, 3 arms at 65,536 slots) enters only X's DEPENDENCE_FAILED row. It costs about a third of the 65,536-slot work. Decide this in block X's revision.

**F15. ADVISORY. §7.2 item 5: the F-OQ-not-full return does not list the human lead's options.** ADR-0021 §10.1 0b listed them: stop, or run with the transition fixed as NOT TESTED. Add them.

**F16. ADVISORY. §9.2 and §10: two wording points.**
- §9.2's cost reason is true for F-OQ only (B).
- §10's row "C-SATURATION / STORE HOLDS MORE" names a dense-at-saturation label, not a C-SATURATION outcome.

**F17. ADVISORY, PENDING LEAD REVIEW. H8 (§21 item 5).**
- Dropping H8 removes the only check that could show learned keys add nothing (KEY-LEARNING-LIMITED). Under the equal rate search, that comparison is untested.
- The cost is about 1.5 charged hours plus three rate units (30 short runs).
- Omitting a check that can only count against the learned-key design leans towards the store. Keep H8 at all seven cells with the equal rate search, or let the human lead rule.

## E. Exact edits

**E1 (§6).**

Replace the bullet "**Not yet assigned by the registry (needed by this draft):** … until lane L is specified." with:

> "- **Block X** (registry revision 2, confirmed): draw sets 240501, 240601, 240701, 240801, 240901 (fact tables of 131,072 facts, P10-S1 in-set layout) and initialisation 330121–330125 (draw r → 330120 + r). Block X's calibration and rehearsal draws are requested from the registry in block X's revision (§12). Lane L's values stay PENDING there (247001–247999, 330111–330115) until lane L is specified."

Replace the G9 bullet with:

> "- **Gate G9** runs a new copy of `seed_registry_check_r3.py` (SHA-256 `e462360420321aa284b0e4d47b106806419ab616794a5c632fee70f122c67594`) extended with this study's named values, with R2 and R3 expanded (registry §4.3 item 5, §4.5 item 5). The copy excludes from the inventory the files of every P10-I study's own package, config and tests (as ADR-0029 §19 ruling 6); each study's own values are checked separately against its own allocation rows. The copy's hash and its exclusions are recorded in the gate result. G9 requires RESULT: PASS and an empty MISSING list before each freeze. (On 2026-11-18 the unmodified r3 checker returned FAIL with 34 problems, all of them P10-I-R's own literals against P10-I-R's own allocation.)"

**E2 (§9.1).**

Replace "Δ_MC = i(4N; U_P) − i(N; U_MC), in reading MC-A." with:

> "Δ_MC = i(4N; U_P) − i(N; U_MC), computed separately in MC-A and, where measured, in MC-T. In a reading in which the larger cell costs no more per update than the smaller, U_MC = U_P in that reading."

In row 4, replace "Δ_MC ≥ 0.5;" with:

> "Δ_MC ≥ 0.5 in MC-A and, where MC-T is measured, in MC-T (a pair MC-SHORT in either reading fails this condition);"

Replace the sentence "Where MC-T is measured, Δ_MC is also computed in it and printed; a CAPACITY verdict whose MC-T value is below 0.5 carries NOT CONFIRMED AT MEASURED CPU COST." with:

> "Where MC-T is NOT MEASURED, Δ_MC is read in MC-A alone and every CAPACITY verdict carries MATCHED COMPUTE IN MC-A ONLY. Disclosure: ADR-0021 §5.4 read the smaller cell at the larger of the two measures' multipliers (1.689 at F-OQ's C1 and 1.697 at C2 in P10-S1, `analysis.json`); requiring Δ_MC ≥ 0.5 in each measure is at least as strict wherever MC-T is measured."

**E3 (§9.2, dense: the stricter text).**

Replace the DENSE AHEAD (cell) row with:

> "| DENSE AHEAD (cell) | d ≤ −0.25 on either panel in ≥ 4 replicates in at least one reading: MU, MC-A, MC-T (where measured) or D-BEST (ADR-0021 §8.5). The count in each reading is printed. Where the lead holds only in MU or D-BEST, the label is printed DENSE AHEAD (NOT AT MATCHED COMPUTE). A replicate whose pair is MC-SHORT in a reading does not count towards this label in that reading |"

In "Arm-level combination", replace "DENSE AHEAD (arm) if DENSE AHEAD at every such cell, or DENSE HOLDS MORE at every loaded cell." with:

> "DENSE AHEAD (arm) if DENSE AHEAD at any such cell, or DENSE HOLDS MORE at any loaded cell (ADR-0021 §8.5)."

Replace the bullet "**For a negative, one thing is narrower.** … (§21 item 4)." with:

> "- **For a negative, nothing is narrowed relative to ADR-0021 §8.5:** any one reading at any such cell, or DENSE HOLDS MORE at any loaded cell, gives DENSE AHEAD. Draft 3 proposed a narrower negative (a dense lead at matched compute required, every cell, every loaded cell). It was written after P10-S1's readings were seen and would move P10-S1's pattern at 32K/16K from DENSE AHEAD to SPLIT. It is reserved to the human lead (§21 item 4) and is not adopted under the delegation."

Replace §21 item 4 with:

> "4. **Dense reading (§9.2).** A positive needs all four readings; a negative is ADR-0021's (any one reading, any cell, any loaded cell) (adopted). The narrower negative of draft 3 is reserved to the human lead and is not taken under the delegation."

**E4 (§9.5, efficiency: the stricter text).**

Replace row 4 with:

> "| 4 | EFFICIENCY-NEGATIVE | F-OQ and T-OQ are both EFFICIENCY_NOT_SUPPORTED in E-A, or both in E-T; or at least one is EFFICIENCY_SUPPORTED in both readings and every such arm is DENSE FASTER at one or more FASTER-STEP cells in one or more readings |"

Replace the "Disclosure, placed with the rule" paragraph of §9.5 with:

> "**Disclosure, placed with the rule.** The positive is P10-S1's any-cell block, applied in each reading. The negative keeps the any-cell combination that P10-S1's frozen code applied (`studies/p10s1/analysis.py` line 631) and that the human lead accepted in the registered label (`ACCEPTANCE.md` ruling 2); it is now written down and applied per reading, with each cell and reading printed. On P10-S1's records it gives EFFICIENCY-NEGATIVE again (D-OQ faster at 2K/4K in both readings). Draft 3's negative, which needed every cell in both readings, would have turned P10-S1's registered negative into INCONCLUSIVE and was written knowing that; it is reserved to the human lead (§21 item 6)."

In §10, replace the C-EFFICIENCY row with:

> "| C-EFFICIENCY | POSITIVE (needs E-T) | NEGATIVE through E-A; INCONCLUSIVE | the outcome with '(E-A ONLY; MEASURED COST NOT AVAILABLE)' |"

Replace §21 item 6 with:

> "6. **Split rule (§9.2, §9.5).** A positive needs every cell and both readings; a negative needs one cell in one reading (adopted). The symmetric alternative of draft 3 is reserved to the human lead and is not taken under the delegation."

**E5 (§17, after the table; and §15 first row).**

Add to §17:

> "**Bound within the design ceilings.** If every loaded cell's U₀ is at its calibration ceiling and every loaded cell runs to 4·U₀, the loaded cells alone cost about 124 charged hours at P10-S1's six-worker seconds per update, with one T-OQ cell at 32K/4K taking about 43 hours of wall time. The calibration's load search to its ceilings costs about 54 worker-hours, with its longest run about 11 hours. The projection behind each cap states its assumption for loaded cells: U₀ for the projection, with the bound at 4·U₀ printed beside it. A cap or an extension whose bound exceeds 60 charged hours (this table's upper case) goes to the human lead; it is not set under the delegation."

Append to §15's first row:

> "; the projection's assumption for loaded cells is stated (§17)".

**E6 (§16, first two rows; and §15).**

Replace the "How it is met" cell of the timing row with:

> "**Yes, for the isolated timing stage (MC-T).** At its start: one-minute load average ≤ 1.0, no process of another ArborLM study's stage alive (P10-S1's `concurrency_check`), mains power, not in Low Power Mode. At its end: no such process alive, and none started during it; otherwise its figures are discarded and the run is repeated. Retried every 10 minutes for up to 6 hours in a session. A session without a quiet run is **PAUSED** and rescheduled with the human lead, in up to three further sessions (as ADR-0027 §6); only then is MC-T NOT MEASURED, with the consequences of §10. The calibration's timing preview needs no quiet condition: it sets item caps only and enters no rule."

Apply the same text to the throughput row, with THROUGHPUT NOT MEASURED.

Add a row to §15:

> "| Quiet-condition sessions (6 hours each; at most four sessions) | Design ceiling | Fixed; reaching it gives MC-T NOT MEASURED or THROUGHPUT NOT MEASURED (§10) |"

**E7 (§18, row 1).**

After "calibration records and data manifests" insert:

> ", every module imported from outside `studies/p10is1/` (from `studies/p10s1/`, `studies/p9/` and `src/arborlm/`) and `uv.lock`, each by SHA-256".

**E8a (§18, a new row).**

> "| The plan's caps and the rehearsal depend on each other (ADR-0029 §19 ruling 5, §20) | Two rehearsals. A measuring rehearsal on provisional caps measures seconds per update, contention, evaluation seconds per snapshot and peak memory. The caps are set from it by §15's rule and written into the candidate `freeze/plan.json`. A counting rehearsal then runs every registered stage end to end against that file, and its SHA-256 goes into the rehearsal record. The freeze refuses unless the committed plan has that hash. Nothing is frozen on the measuring rehearsal |"

**E8b (§18, a new row; and §9.3 row 2).**

New row:

> "| A code error recorded as a result (ADR-0029 §20 ruling 11) | An exception inside an item that is not a gate failure, a resource cap or an identity stop is never a NOT_EVALUATED, DEPENDENCE_FAILED or failed cell. If any registered stage has one, the analysis refuses and every line prints ENGINEERING STOP — ITEM ERRORS. An environment error (out of memory, file system) stops the task as PAUSED — ENVIRONMENT, and the task resumes once the environment is fixed without a code change. A registered training cell that ends with a non-finite loss is a recorded failed cell: kept, not re-run, the stage INCOMPLETE (§14) |"

In §9.3 row 2, append:

> " INCOMPLETE: no outcome is printed on any line (ADR-0021 §8.7 row 2)."

**E9 (§16, first paragraph).**

After "CPU only." insert:

> "The settings P10-S1's cells recorded (`environment.threads` of every `train.json`: one torch thread and one interop thread per worker, deterministic algorithms as recorded) are fixed in the config and asserted by each worker. The OS build is recorded with every gate result."

**E10 (§0, §11, §12, §21 item 2: defer block X).**

§0, block X row, last cell:

> "Rules fixed; **not approved with this draft**. Engineering items completed in a revision before its own approval (§12)"

§11: replace "including block X's timing rehearsal → block X's funding computed by rule and recorded" with "→".

§12: add at the end:

> "**Not approved with this draft.** Block X's rules above are fixed now. A revision before block X's approval completes, without changing any rule above: (1) calibration and rehearsal draws of 131,072 facts and their seeds (registry); (2) the G2 chance interval at n = 131,072; (3) U_P of the 32,768-fact row on X's calibration draws (selection cell 32K/64K); (4) the isolated MC-T timing at 65,536 slots under §16's quiet condition; (5) F-OQ-IVF at 65,536 slots; (6) the evaluation term and peak memory at 131,072 facts in P_X. **H_X is set by the human lead himself before block M's Decision 2; it is not set under the delegation.** If no figure is recorded by then, X-CAPACITY is NOT TESTED — NOT FUNDED BY RULE. P_X may be computed after block M's run, since its inputs (block M's calibrated U₀ and the rehearsal's seconds per update and per snapshot) do not depend on block M's registered results."

§21 item 2:

> "2. **Block X (§12).** Its rules are fixed; the block is deferred to a revision and its own approval. H_X is set by the human lead himself (lead's suggestion 100 charged hours; with evaluation, the central P_X is about 102–112). **PENDING HUMAN LEAD RULING; not taken under the delegation.**"

**E11 (§13).**

Replace "**Settled now.**" with:

> "**Constraints the revision must keep** (recorded with this draft; they approve no lane L cell, rule or budget):"

In "Registered values now", append:

> "If ADR-0023 has an accepted outcome that licenses a cell when block M freezes, block M's report prints LANE L LICENSED — NOT YET SPECIFIED; NOT RUN UNDER THIS APPROVAL."

**E12. Add a new subsection "§8.3 Rulings fixed now (from the third review)".** Its numbered items are the rulings in section F below, items 1–21, verbatim. Item 21 is the F13 disclosure.

## F. What an implementer would have to guess, and the ruling I recommend for each

1. **Δ_MC direction in a reading where the larger cell is the cheaper.** U_MC = U_P in that reading (E2).
2. **F-OQ-IVF's cost.** F-OQ-IVF's MC-A and MC-T costs per update, and its cost in STORE HOLDS MORE, are F-OQ's training costs; the index build is not counted. Its matched snapshots are F-OQ's.
3. **DEP qualification beyond U_P.** A snapshot at update u maps to the fraction u/U_P. At fractions above 1, the qualification at fraction 1 applies. A condition stays qualified at a fraction where R2 is under the a_use floor; only an actual R2 failure disqualifies it.
4. **Registered R2 failure.** "Not applied at that snapshot in that replicate" means: at that fraction, for every arm of that row, in that replicate. It is printed per arm.
5. **DENSE AHEAD counts.** Counts are per reading, and a replicate counts if either panel meets the condition (as E3). MC-SHORT replicates do not count in that reading.
6. **MC-SHORT in row 4.** A pair MC-SHORT in either reading fails Δ_MC (E2).
7. **Calibration "full".** It includes ADR-0021's i\* ≤ 4.0. F-OQ full but above 4.0 on a view at its U₀ is treated as "F-OQ not full at the ceiling", which returns the work to the human lead before the freeze.
8. **Order of the loaded-cell work.** The loaded-cell rate units (at 65,536) precede the load search. The load search continues each selected rate's calibration runs from their 65,536 checkpoint (G4 restoration); no new runs are started.
9. **Plan items for run-until-full.** The plan lists every loaded cell with U₀, the maximal length 4·U₀ and every snapshot up to it. A cell stops at the first ladder point at which it is full. Later items are recorded NOT REACHED, not missing. The stop statistic is computed by the frozen code and not displayed (whitelist).
10. **i\* in the stop rule.** i\* is the maximum of i over snapshots ≤ U on each panel. DEP is not consulted; DEP enters the verdicts, not the stopping rule.
11. **U_run of a loaded cell.** U_run is the ladder point at which the cell was found full, or 4·U₀.
12. **MC-T source.** One isolated timing stage after Decision 2 and before training, on the rehearsal draw, covering every arm × size including 256 slots and R2's cells. It is all or nothing.
13. **Timing preview.** No quiet condition; it sets caps only (E6).
14. **Cap projection.** U₀ with the 4·U₀ bound printed beside it (E5).
15. **Item, environment and non-finite errors.** As E8b.
16. **INCOMPLETE.** No outcome on any line (E8b).
17. **DEP for D-OQ.** DEP-a, DEP-b and DEP-c apply to D-OQ wherever a rule reads D-OQ at a_use ≥ 0.25 (efficiency qualification, dense readings), with the same R2 qualification. **PENDING LEAD REVIEW**; ADR-0021's text says "memory cell".
18. **U_P's "row's larger step cell".** It is 2K/4K, 8K/4K and 32K/16K for the three rows, as ADR-0021 §10.1 item 1.
19. **Edge walk.** A best rate within 0.02 of an edge chosen by the walk is taken, recorded as EDGE BY TIE-WALK, and not extended (ADR-0021 §10.1 item 3). A diverged rate is a run that ends `failed` or whose readout is inside the chance interval.
20. **Binomial quantile in DEP-c.** It is the smallest k with P(X ≤ k) ≥ 1 − 10⁻⁴, computed exactly in log space (no package outside the lock). "Exceeds" means strictly greater.
21. **Counterfactual disclosure (F13), to place beside §9.3.** "On P10-S1's records DEP-c fails none of the 32 reads that failed the 0.95 condition (third review), and the audit's run without those failures gives F-OQ CAPACITY_SUPPORTED (`audit/a4_dep_sensitivity.out`). C-CAPACITY would then turn on the dense labels; with DENSE HOLDS MORE at both loaded cells in 5 of 5 replicates it would be CAPACITY-NEGATIVE (b)."

## G. Machine load and running beside another study (18 cores, 48 GiB)

- **Must run alone:**
  - The isolated timing stage (MC-T). Every store-favouring capacity label needs it.
  - The read-path throughput stage (descriptive).
  - Block X's MC-T timing at 65,536 slots, if block X is ever approved.
  - "Alone" means no other study's stage process alive at the start or the end (E6), not only a load average.
- **Can share the machine:** calibration, both rehearsals, generate, gates, train, evaluate, analyze and report. No rule reads their wall time, and gate G4's bit-exactness does not depend on load. Conditions:
  1. Block M's work must not be done in the worktree of a running registered study. P10-I-R's tasks refuse when the git tree is dirty (`studies/p10ir/plan.py:268`), and block M's freeze, calibration records or code would dirty it. Use a separate worktree, with run directories git-ignored.
  2. The memory guard is per study (18 GiB). Two studies at their guards would hold 36 of 48 GiB on the human lead's working computer. Add a machine-level check: a stage does not start unless free memory covers its aggregate guard. P10-S1's measured peaks were 0.39 GiB per worker in training and 1.415 GiB in evaluation, about 8.5 GiB at six workers.
  3. Sharing inflates charged hours, so caps are reached sooner (PAUSED, resumable). The measuring rehearsal's contention ratio should be measured under the conditions the run will have.

## H. Open choices (§21) under the delegation

| Item | Recommended option sound? | Take by delegation? |
|---|---|---|
| 1 Task kept, labels capped | Yes | Yes |
| 2 Block X, H_X = 100 | Rules sound; engineering incomplete (F8) | **No**: a large cost, and the human lead was told "about 26 plus an unbounded block". Defer (E10) |
| 3 Lane L later, separate freeze | Yes | Yes |
| 4 Dense reading | Positive side sound; negative side narrowed after observation | **No**: adopt E3; the narrower version goes to the human lead |
| 5 H8 not run | Removes the only test that can count against learned keys | **Better not**: keep H8 at seven cells, or ask the human lead (F17) |
| 6 Symmetric split | Narrows both capacity and efficiency negatives after observation; it would flip P10-S1's registered negative | **No**: adopt E4 |
| 7 DEP-c floor 0.01 | Yes. Written before the audit and disclosed; it decides none of P10-S1's 32 failing reads | Yes |
| 8 Split into ADR-0029 | Ruled | — |
| 9 Calibration ceilings | Yes as rules | Yes, but the cost bound goes to the human lead (E5) |
| 10 F-OQ-IVF enters C-CAPACITY, no entry elsewhere | Yes (as ADR-0021; not a relaxation) | Yes |

`Astra review: NOT_PERFORMED`. Claude review is not Astra review. This review is not a human approval.
