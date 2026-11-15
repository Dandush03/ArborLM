# ADR-0021 (P10-S1) revision 3: narrow re-check of the K1–K7 rewording

**Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.**

- **Reviewer:** Claude Opus 5.5 (`claude-opus-5-5`), auditor role. This is the same role as the author of `CONFIRM.md` (K1–K7), but a different session. Two of the findings below are defects in that confirmation's own paste-ready text (K3, K4, K6). They are reported as such.
- **Object:** `docs/decisions/ADR-0021-p10-s1-useful-capacity-scaling.md` (719 lines, revision 3), worktree `p10-design`, branch `claude/p10-design`, HEAD `2ef6a4f`, clean. Read in full, together with `CONFIRM.md`, `diff revisions/…rev2.md` against revision 3, ADR-0019 §7, ADR-0020 §7 and §9.3, ADR-0022 §9 and its header, and the P9-II seed namespace in `studies/p9ii/core.py` (lines 389–391 and 461–462).
- **Ran:** stdlib arithmetic only: `python3 -I r3_recheck_arithmetic.py` (Python 3.15.1, macOS, stdlib only), plus `git rev-parse`, `diff` and `rg` for seed literals in `studies tests configs src`. No ArborLM code, no model, no seed, no network, no commit.
- **Where the files are:** a PreToolUse hook refused to let this session write inside the `p10-design` worktree ("belongs to a different worktree"). I did not work around it. This file and the script, with its output, are in this session's scratchpad. The coordinator must copy them to `docs/reviews/p10-design-2026-11-15/adr-0021-review/` (`RECHECK_REV3.md`, `r3_recheck_arithmetic.py`, `outputs/r3_recheck_arithmetic.txt`).

## Verdict: READY SUBJECT TO the listed text edits

K1–K7 are applied faithfully. The wording is verbatim, and §20's deviations are acceptable. The rewording itself introduced no new contradiction or changed number. Re-reading the applied text exposed two majors in the confirmation's own text:
- **R1.** The efficiency verdict table has no row for some censored cases.
- **R2.** Cut 3 depends on a calibration prediction for 8K/16K that the calibration never makes.

R2 needs a lead's choice among the stated options before its text can be fixed. There are also 11 minors. After R1 and R2 are applied verbatim, plus the lead's choice for R2, no further review round is needed. Text worded otherwise needs a re-check.

## 1. K1–K7: application

| K | Applied? | Passage in rev 3 (quoted) | Note |
|---|---|---|---|
| K1 | Yes, verbatim | §8.2: "**Loaded** (a smaller cell): plateaued and i\*(N; U_run) ≤ 4.0 bits per fact (a_use ≤ about 0.896) *(lead's choice)*. This one threshold is used for CAPACITY (row 4), NULL (row 8), FLAT, NOT LOADED (row 9) and the load calibration"; row 4 "**the smaller cell is loaded**"; §10.1 item 0 and its five-row table are word for word | "Saturated below the ceiling" and "L\*" are gone from the text. §0 now reads "loaded (§8.2)". The added §8.2 sentence ("needs the larger cell at 4.70 bits or more (a_use 0.974)") matches `k1_confirm_arithmetic.txt`. The partition of the rule table is complete at both slot counts. Overload-row gaps: minors m1–m4 |
| K2 | Yes | (a) §8.5 table, verbatim: "DENSE AHEAD … Takes precedence over every other label"; "BEATS DENSE … in **all 5** replicates … BEATS DENSE (DENSE AT CHANCE AT cell)". (b) §6.2: "'At least 4 of 5' is used for negatives, ceilings and DENSE AHEAD. Every positive condition, BEATS DENSE included, needs all 5." (c) §8.7 reading: five sub-bullets with the same words (§20 item 3). (d) printed label, verbatim; §12 dense-family line | The (b) sentence now collides with TREE_AHEAD "at least 4" (m7). A wording overstatement inherited from K2(c) is m11 |
| K3 | Yes, verbatim | §10.3: "3. D-OQ at a larger cell (among 8K/64K and 32K/16K) **only if the load calibration predicted that step's smaller cell not loaded** (8K/16K for A2; 32K/4K for B1)…"; §8.5: "(only after cut 3 of §10.3)"; §6.1 and §6.2: "unless cut 2 of §10.3 removes it" | Consistent renumbering throughout. **The K3 text itself is defective (R2)** |
| K4 | Yes, verbatim except "[1.5]" → "1.5 times *(lead's choice)*" | §8.8 Level paragraph, eight-row table, OPTIMIZER-ASSISTED sentence, step class "DEPENDENCE_FAILED (at least 2); … FASTER STEP (FASTER or REACHED ONLY BY THE LARGER in all 5; the number of each is printed)", arm class "DEPENDENCE_FAILED (any step)", closing sentence | **The K4 table is not exhaustive (R1)** |
| K5 | Yes, verbatim | §7.4 rule 4: "**F-OQ-IVF's W is measured, not analytic.** …" | §8.5 still says "SUBLINEAR (analytic)" (m6) |
| K6 | Yes, verbatim | §10.3: "On this projection the draw-1 seed block needs 1.4 + 2 × 5.3 = **12.0 hours: zero slack.** … the draw-1 seed block saves about 0.7 hours under the twofold rule, the permitted D-OQ cut about 0.6. Beyond that the work returns to the human lead…" | 0.6 is the saving with **both** D-OQ cells cut. Under K3 the expected saving is 0.37 or 0 (R2, §2) |
| K7 | Yes | (a) §6.3 "Unit tests: **921001–921999**"; G9 "S2 (220001–228999, tests 229001–229999)". (b) §5.6 items 1, 2, 4 verbatim, item 7 added; §6.1 "F-LA × 3 cells × 5 \| +15". (c) §13 item 5 verbatim, with "'K7(c)' in §8.7 and §8.8 means item 5 above" | ADR-0020 §9.3 asked S1 for a different F-LA sentence. Revision 3 follows K7(b) (note N2) |

§20 items 1–6 checked against `CONFIRM.md`. All are true statements of what changed. Item 5 (UPDATES-ONLY STEP excludes REACHED ONLY BY THE LARGER) is deterministic and not a defect. Whether it is intended is **PENDING LEAD REVIEW**: REACHED ONLY BY THE LARGER is strictly stronger than FASTER IN UPDATES ONLY, yet a mix of the two becomes MIXED.

## 2. Registry and budget, re-derived (`r3_recheck_arithmetic.py`)

- **Configurations:** F-OQ 7, T-OQ 7, H8 7, D-OQ 5, R2 4 = **30** per replicate. × 5 = **150**. Seed block +14 per draw. Lane L +15.
- **Calibration:** 14 + 12 + 6 + 12 = **44** runs, plus 4 for the overload row.
- **Training per replicate:** F 3,544 s, T 7,063, H8 1,543, D 3,000, R2 289. Total 15,439 (revision 3: 15,440). 150 cells = 21.44 CPU-h = **3.57 charged h**.
- **Seed block:** 1.97 CPU-h per draw = 0.33 h.
- **Calibration hours:** load 2.95, U_P + H8 0.49, dense 2.11. Total 5.54 CPU-h = 0.92 h. With the rehearsal, 0.45, that gives **≈1.4 h**.
- **Headroom at 12 h:**

| Seed blocks | Charged + 2 × remaining | Slack |
|---|---|---|
| Draw 1 only | 1.4 + 2 × 5.30 = **12.00 h** | **0.00** |
| Draws 1 and 2 | 12.66 h | −0.66 |
| None | 11.35 h | +0.65 |

- **Sensitivity** (doubled): T-OQ at 2.5× adds 0.82 h; D-OQ +20% adds 0.28 h (revision 3 says "about 0.4" for each item; that holds only for the evaluation hour); evaluation +20% adds 0.40 h.
- **Cuts** (doubled savings): cut 2 (the draw-1 seed block) saves 0.66 h. Cut 3 at 8K/64K (A2) saves 0.37 h; at 32K/16K (B1), 0.22 h; both, 0.59 h.
- **Overload row** (training only, doubled; D-OQ at the larger cell only / at both cells):

| U_P' | Doubled cost |
|---|---|
| 8,192 | 2.09–2.30 h |
| 16,384 | 4.17–4.61 h |
| 32,768 | 8.35–9.22 h |

At 12 h the most every cut can recover is 0.66 + 0.59 = 1.25 h. **The overload branch of K1 therefore always ends in a return to the human lead under the 12-hour cap.**

**What the specification says happens if the rehearsal projection, doubled, exceeds 12 hours.** The test is the headroom rule of §10.3: charged-so-far + 2 × projected remaining ≤ 12 h, and twice the peak memory within the memory caps. If it fails, the cuts apply "in this order, until the headroom rule holds; nothing else may be cut":
1. The draw-2 seed block. In practice this cut does nothing: by §6.2 that block is added only if the same rule holds with it.
2. The draw-1 seed block.
3. D-OQ at 8K/64K and/or 32K/16K, only where calibration predicted that step's smaller cell not loaded. A step that loses its D-OQ cell prints DENSE NOT READ and cannot support CAPACITY_SUPPORTED.
4. Stop and return to the human lead with the measured shortfall and two options: raise the cap, or shorten the run lengths (a new registered design and a re-review). "The lead does not choose between them."

The registered run does not start. Decision 2 (§11 item 8) requires the headroom rule to hold. The calibration and rehearsal hours, about 1.4, are already charged. "The five replicates, U_P, the run lengths and every threshold are never changed to make the study fit."

**Is the rule fixed before observation?** Yes. The list and the order are fixed in the text before calibration. Its inputs (load predictions, rehearsal timing) come from calibration and rehearsal draws only, which §8's opening paragraph allows.

**Is it unambiguous?** No. Three gaps:
- **R2:** cut 3's condition for A2 has no defined input.
- **m5:** the priority of lane L against the seed blocks is not stated.
- **m10:** if both D-OQ cells are eligible and one suffices, the order is not stated.

**Effective margin at 12 h.** After all cuts, the projection may grow by 0.33 h of remaining time (≈6%) with cut 2 only. With the A2 D-OQ cut too, it may grow by 0.51 h (≈10%). Anything beyond that is a return.

**For the human lead's information only; the cap is not changed here.** At **16 h**, with the same ≈1.4 h charged first, the allowed remaining time is 7.3 h rather than 5.3. That would protect:
- Both seed blocks, with 3.34 h of doubled slack.
- An overrun of the remaining time of up to +2.0 h (+38%) with the draw-1 block and no cut. At 12 h the tolerance is 0%.
- All three named risks at once: T-OQ at 2.5×, D-OQ +20% and evaluation +20% total +1.50 h doubled.
- Every D-OQ cell, so no DENSE NOT READ.
- The overload row at U_P' = 8,192: 2.1–2.3 h doubled plus its evaluation, inside the 4.0 h slack. At U_P' = 16,384 it fits only after dropping seed blocks. At 32,768 it does not fit.

A 16-hour cap would not protect the run lengths or the U_P choice, which never change.

## 3. Seeds

The seeds are consistent everywhere in revision 3:
- §6.2: init 2100 + r for r = 1…5, giving 2101–2105. Seed block 2111/2121 (draw 1) and 2112/2122 (draw 2).
- §6.3: bases 210001–210401, using offsets up to +60 (below +100, so the sets do not overlap). Calibration 219001/219101 with init 2191. Rehearsal 219201 with init 2192. Tests 921001–921999.
- §6.1 and G9 agree.

**Disjointness:**
- **ADR-0019 / P9-II:** data 190001–191599, init 1891, 1901, 1902, tests 910001–919999. ADR-0019 itself says "910001 upward"; ADR-0020 and the P9-II code bound it at 919999.
- **ADR-0020:** 200001–209999, 2001–2002, 2091–2092, tests 920001–920999.
- **ADR-0022:** namespace 220001–229999, including calibration 221001–221999, rehearsal 222001–222999 and tests 229001–229999. Its initialization seeds are base + 0, so they lie inside 220xxx.

S1's derived seeds (init + 1000·k, k ≤ 5 in `studies/p9/model.py:272–279`) end in 101–105, 111, 112, 121, 122, 191 or 192 modulo 1000. None collides.

In `studies tests configs src`, `rg` found no literal in 210001–219999 or 921001–921999. The only hits are P9-II's deliberate reservations and negative-test probes: `RESERVED_LATER = ((200001, 229999), (920001, 929999))` and `215000` / `925000` in `tests/test_p9ii_core.py:121,123`. None is a seed of a trained model.

Discrepancies:
- **m8:** P9-II's committed namespace declares calibration init `{1891, 1892}` (`studies/p9ii/core.py:462`). G9's P9-II list names only 1891. There is no collision.
- **N1 (ADR-0020, not S1):** ADR-0020 §7 lists S1's init seeds as "2101–2105, 2191–2192" and omits 2111, 2112, 2121, 2122.

## 4. Barring an autonomous learned-memory claim

The bar is enforced in these passages:
- §3 item 4: "**Every positive label of S1 carries STORE ONLY; ORACLE-ADDRESSED and may not be printed without it.**"
- §8.7 printed label: "CAPACITY-POSITIVE [STORE ONLY; ORACLE-ADDRESSED; WITHIN REGISTERED RUN LENGTHS; … S0 status (K7(c)); learned-address lane status]".
- §8.8: "Printed as EFFICIENCY-POSITIVE [STORE ONLY; ORACLE-ADDRESSED; …]".
- §8.7 reading: "It says nothing about addressing by the model, about use of the store by a language model, or about useful capability beyond recall of the trained facts."
- §12: "**No autonomous learned-memory success may be claimed from S1**, whatever lane L shows."
- §5.6 items 5–6: lane L "gives no step verdict" and "changes no S1 class or outcome".
- §8.7: "H8 alone cannot give CAPACITY-POSITIVE".
- §13 item 5: "never summarised as 'ArborLM's capacity scales'".

Two gaps (m9):
- The descriptive positive labels (KNOWLEDGE SCALES WITH MEMORY, TREE_AHEAD, RISES WITH SLOTS) and the intermediate classes (CAPACITY STEP, CAPACITY_SUPPORTED, BEATS DENSE, FASTER STEP, EFFICIENCY_SUPPORTED) are not named as "positive labels" that must carry the tag when printed outside their tables. "KNOWLEDGE SCALES WITH MEMORY" printed alone reads as an autonomous claim.
- §13 item 5's ban on "ArborLM's capacity scales" applies only "if S0 qualifies no interface".

## 5. Findings

### R1 (MAJOR) — §8.8 step-verdict table is not exhaustive (defect in K4's text)

Take A1. The smaller cell reaches i_T at u_T(N) = 20,000. The larger cell is right-censored above U_run(4N) = 32,768. Then:
- Row 4 is false: the smaller cell is not censored.
- Rows 5–6 are false for every allowed value.
- Row 7 is not decided, since U_run(4N) < 2·u_T(N).
- Row 3 needs *all* of rows 4–7 undecidable, which does not hold.
- Row 8 needs both u_T known, which does not hold.

No verdict applies. B2 behaves the same way, as do cases with one cell left-censored ("known" is not defined for left-censored values). Fact 5 of §1 makes this case likely.

Text: replace the §8.8 row 3 rule with

> both cells right-censored; or at least one u_T is censored and no condition of rows 4–7 holds for every value the bounds allow

and the row 8 rule with

> otherwise; both u_T known (neither left- nor right-censored)

### R2 (MAJOR) — Cut 3 for A2 has no defined input (defect in K3's text, carried into K6)

The load calibration at 16,384 slots measures loads 2, 4 and 8 only (§10.1 item 0), and "loadedness is not assumed to carry from one load to another". No calibration predicts 8K/16K (load 0.5). The U_P check reads it at 8,192 updates only, not at U_run. So "only if the load calibration predicted that step's smaller cell not loaded (8K/16K for A2…)" cannot be evaluated.

Under the lead's own expectation (32K/4K loaded), B1's D-OQ cell is never cuttable. Whether the only other D-OQ cut, 0.37 h doubled, exists then depends on this undefined input.

The choice is scientific, **PENDING LEAD REVIEW**. The options:
- (a) A2's D-OQ cell at 8K/64K is never cut.
- (b) 8K/16K counts as predicted not loaded whenever load 2 at 16,384 slots is not loaded. This contradicts the no-carry sentence unless that sentence is limited.
- (c) Add 8K/16K to the load calibration: 2 runs, ≈0.52 CPU-h, ≈0.09 h charged before the rule.

Also replace K6's "the permitted D-OQ cut about 0.6" with:

> the D-OQ cut, where cut 3 permits it, about 0.37 hours (8K/64K) and 0.22 hours (32K/16K) under the twofold rule

### Minors

- **m1.** Overload row: no rule if none of U_P' ∈ {8,192, 16,384, 32,768} qualifies. Add: "If none qualifies, the work returns to the human lead before the freeze."
- **m2.** Overload row: "for F-OQ, T-OQ, H8, D-OQ and R2" at both slot counts reads as D-OQ at 65K/16K too. Elsewhere D-OQ runs only at larger and diagonal cells. State which; lead's choice.
- **m3.** Overload row: load 4 at 16,384 slots is judged at 32,768 updates. The row's registered smaller cell runs 4·U_P', up to 131,072. This is a prediction only and the run judges every cell. Say so in the row.
- **m4.** §6.2 fixes a 32,768-fact table per draw. The overload row needs a 65,536-fact registered table, but its nesting and seed layout are not specified. Lead's choice of nesting; the seed layout is the implementer's, inside 210001–219999.
- **m5.** Lane L (§5.6 item 6) and the seed blocks both compete for headroom, but their priority is unstated. Put lane L into the cut order or state that it is decided after cut 2.
- **m6.** §8.5 "SUBLINEAR (analytic)" contradicts §7.4 rule 4. Write "SUBLINEAR (analytic; measured for F-OQ-IVF, §7.4 rule 4)".
- **m7.** §6.2 "Every positive condition … needs all 5" contradicts TREE_AHEAD "at least 4", and TREE_COMPETITIVE's count is unstated. Either limit the sentence to capacity and efficiency verdicts, classes, outcomes and BEATS DENSE, or change TREE_AHEAD. Add "in at least 4 replicates at both cells" to TREE_COMPETITIVE.
- **m8.** G9's P9-II list: add 1892 (declared in P9-II's namespace).
- **m9.** §3 item 4: enumerate the positive labels as in §4 above. Make §13 item 5's "never summarised as 'ArborLM's capacity scales'" unconditional.
- **m10.** Cut 3: if both cells are eligible, cut [8K/64K first, then 32K/16K] (the lead may change this bracket).
- **m11.** §8.7 reading: "at least as well as a dense map" overstates DENSE MATCHES, which allows a dense lead of less than 0.25 bits, or a larger lead in up to 3 replicates. Replace it with "with no dense lead of 0.25 bits per fact or more in 4 of 5 replicates (BEATS DENSE or DENSE MATCHES, printed)".

### Notes outside S1 (no edit to S1 asked)

- **N1.** ADR-0020 §7 omits S1's seed-block init seeds.
- **N2.** ADR-0020 §9.3 asked S1 §5.6 item 4 to add "Each F-LA cell records S0's probe set, H1/H2 and the read swap, and prints whether it succeeds under ADR-0020 §8.2". Revision 3 has K7(b)'s "S0's cell-success rule is applied at all three cells".
- **N3.** ADR-0022's initialization seeds are base + 0 (220001…). If S2 derives generator seeds as init + 1000·k, they fall in its own calibration and rehearsal ranges (221001, 222001). Not checked; S2's concern.
- **N4.** The status line reads "CONFIRMED BY THE AUDITOR SUBJECT TO K1–K7". After this re-check it should also cite R1, R2 and this file.

## 6. Files

All in this session's scratchpad, to be copied into `adr-0021-review/`:
- `r3_recheck_arithmetic.py`
- `r3_recheck_arithmetic.txt` (its output)
- this file
