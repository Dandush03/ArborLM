# Confirmation review of ADR-0020 revision 4 (P10-S0)

**Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.**

- **Reviewer.** Claude Opus 5.5 (`claude-opus-5-5`). I wrote no part of ADR-0019–0022, of revision 4 or its CHANGES.md, or of P9-II's code and records. RECHECK_REV3.md (R1–R10) was written by an earlier Opus 5.5 context. Where its pasted text is defective, I say so (F3).
- **Date.** 2026-11-15.
- **Worktree.** `.claude/worktrees/p10-design`, branch `claude/p10-design`. Review started at `7afac47`. HEAD moved to `3cf3576` during the review. That commit touches only ADR-0022 and its re-check (no seed or S0 line), so ADR-0020 and every other input are unchanged.
- **Intended location.** Writes into the worktree are blocked for subagents, so this file and its scripts are in the session scratchpad.
- **Inputs (sha256, first 8 hex digits):**
  - ADR-0020 rev4 `21db26d3`; rev3 archive `19d44458`; CHANGES.md `aa6ca6de`.
  - RECHECK_REV3 `71e22ca6`.
  - ADR-0019 `93913658`; ADR-0021 rev4 `4d6902bf`; ADR-0022 `e3d89d89` (at HEAD).
  - P9-II records: OUTCOME `66946b87`, classes.csv `90457131`, results.json `9b2ca547`, stage_gate_1 `14988c8a`, stage_gate_3 `e60fae1d`.
  - P9-II calibration `ad5d7ee2`; P9-II results review `e1697af3`.
- **Environment.** Python 3.15.1, standard library only. Darwin arm64. No training, no model, no network, no commit, no edit of any repository file.
- **Commands** (S = this folder; W = the worktree):
  - `git diff --no-index -U0 <rev3> <rev4> > S/rev3_rev4.diff`, plus a word diff `S/rev3_rev4.wdiff`.
  - `git show c56b23a:docs/decisions/ADR-0020-… | diff -q - <rev3 archive>` printed nothing: the archive is identical to `c56b23a`.
  - `python3 -I S/check_changes.py W` → `S/check_changes.out`. My own parser applies CHANGES.md's Old/New and Inserted-after blocks to rev3. It does not use `build.py`.
  - `python3 -I S/numbers_check.py S/rev3_rev4.diff` → `S/numbers_check.out`.
  - `python3 -I S/arithmetic.py W` → `S/arithmetic.out`.
  - Read-only `python3 -I -c` one-liners on `results.json`, `classes.csv`, `calibration.json` and `cells.csv`.
  - `grep` and `sed` on ADR-0019, ADR-0021, ADR-0022, OUTCOME.md, the P9-II REVIEW.md, prior S0 reviews and `studies/p9/model.py`.
- **Failed checker attempts.** None. Every script ran correctly the first time. numbers_check flagged 14 removed numbers. I classified each by hand (task 1): all are expected removals, none an S0 threshold or count.

## Verdict: READY SUBJECT TO the listed text edits

- One finding (F1) needs the lead's choice before implementation. It concerns which cell-success criterion the paired d(X) uses. It is pre-existing (rev2/rev3), but rev4's new H20-D sentence depends on it.
- The other edits are minor and paste-ready.
- No blocker.
- No threshold, count, cap, seed, class rule, preference order or consistency rule was changed by rev4.

---

## 1. Diff accounting (task 1)

- **Complete.** rev3 + C01–C46, applied by my parser, reproduces rev4 byte for byte (`check_changes.out`: "rev3 + CHANGES == rev4 (byte identical)"). No change is unlisted, and no listed change is missing.
- **Archive.** The rev3 archive equals `c56b23a`'s file (open point 12 is closed).
- **Numbers removed (`numbers_check.out`).** All belong to the R1/R9 deletions:
  - the old §9.3 bullets: S0's seed list quoted for ADR-0022, ADR-0021's old test range 921001–929999, "§5.4";
  - the old §9.1 cell: "§8.2";
  - the lane sentence: "512 exposures per fact".
  - None is an S0 threshold or count.
  - The lane constraints removed from ADR-0020 survive in ADR-0021 rev4 §5.6 items 1 and 4: no 65,536 cell, 4·F updates, 2K/4K, 8K/4K and 8K/16K, Q1 recomputed from raw records.
- **Source of each change.** Every change traces to (a) the human lead's decision or (b) R1–R10/N1, with these qualifications:
  - **Changed reading (within R2, the lead's choice).**
    - The pre-Q1 start rule is now less demanding than rev3's literal rule. Rev3 doubled the whole remaining plan at the most expensive possible candidate; rev4 doubles Q1 and earlier stages only.
    - "Most expensive possible candidate" is narrowed from "any arm" to {A5-D, A1}.
    - Both were offered by R2. They are stated, not hidden (C30 note).
  - **Drafter's additions beyond the paste text.** None of these changes a rule:
    - the informational freeze record (§10.4);
    - the third printed provenance element (§3.4);
    - "or accepts it with a changed reading" in §14 (conservative);
    - the H20-D consequence sentence (but see F1);
    - the §3.5 table (I verified it against the records below);
    - G10's two clauses and part (d) (follow from the decision and R2).
  - **R1 (C23/C24).** The "row 1" sentence is ambiguous (F4).
- **Facts rev4 cites, verified against the committed records:**
  - **Hashes.** Every hash rev4 and the re-check cite matches.
  - **F1 annotation.** Verbatim from OUTCOME.md line 32.
  - **"171 comparisons, 0 disagreements".** The P9-II REVIEW.md, line 11.
  - **Calibration.** λ = 1.0, U_pre = 2048, k_0/N = 0.125, μ = 1.0 (`calibration.json` `hyper`; μ chosen from {0.1, 1.0}).
  - **A5-D definition.** Matches ADR-0019 line 75: normalized un-centred queries of the 128 answer sites, L_div = log mean_{i≠j} exp(2 q_i·q_j).
  - **draw_counts** (failed draws = "0/2" + "1/2"):

    | Arm, size | Failed draws |
    |---|---|
    | A0, 4,096 | 6 of 8 |
    | A0, 16,384 | 0 of 4 |
    | A5-D, 4,096 | 0 of 8 |
    | A5-D, 16,384 | 0 of 4 |
    | A1, 4,096 | 0 of 8 |
    | A1, 16,384 | 2 of 4 |
    | A2, 4,096 | 8 of 8 |
    | A2, 16,384 | no Stage 2 class |

  - **Classes.** As in §3.5.
  - **LM flags.** `lm_flagged_cells` = 0 everywhere.
  - **Carried arm.** `carried_forward.arm` = A0, Stage 2 COMPLETE.
  - **§3.5 conclusions** (A0 and A2 cannot qualify; A5-D whenever S0-RELIABLE; A1 at both sizes only with 0 failed S0 draws at 8K/16K) follow from §8.5 (b). A cell that succeeds under S0's criteria also succeeds under P9-II's, so failures under P9-II's criteria are at most S0's.
  - **H20-D premise.** P9-II's paired label for A5-D at 16,384 is NOT DISTINGUISHED (d = 0, A0 8/8), as rev4 says.

## 2. Provenance of the fourth arm (task 2)

**Where it is stated.** It is stated prominently and honestly in:
- header lines 5 and 8;
- §0, §1 item 1 and §2 H20-D;
- §3.3's consequence, §3.4 (eight items, fixed string, F1 annotation, fixed sentence) and §3.5;
- §4, §8.5 (pointer) and §8.7 (print item 1, and the "In every outcome row" paragraph);
- §15, §16, §18, §20 rows 1 and 21, §21, and the closing line.

The status line (line 3) does not mention it. That is optional (F10).

**What S0 can support about A5-D.**
- S0's draws, seeds and panels are disjoint from P9-II's (§7). P9-II's draws were the only data used to choose A5-D.
- Selection on one data set followed by testing on independent data is a valid confirmatory design. So **S0's own class, draw count and per-draw Clopper–Pearson bound for A5-D are not biased by the selection.**
- If A5-D qualifies, S0 supports this, within the fixed scope of §8.7 item 7 and §15: "on ten draws × two seeds not used in its selection, A5-D at μ = 1.0 (P9-II's calibration) met S0's criteria at 4,096 and 16,384; k of 10 draws; per-draw bound b".
- If A5-D fails, DOES NOT REPLICATE is an equally valid and informative result.

**What S0 cannot support about A5-D.**
- That A5-D was a pre-registered prediction or a pre-registered preference.
- Any two-study strength of evidence. P9-II's 16/16 and 8/8 are the data the arm was selected on, the best label-free result among six P9-II arms, and subject to winner's-curse inflation. The pooled count and CONSISTENT ACROSS STUDIES are therefore automatically favourable and add nothing.
- That A5-D is better than A1. No A5-D-versus-A1 comparison is registered. The order is a tie-break by supervision type (CONFIRM.md ruling 3: label-free, then supervision removed, then supervised), not evidence.
- Anything outside S0's scope.

**Is the drafter's wording right?**
- It is honest and conservative.
- One imprecision: "not an unbiased first test" can be read as saying S0's own A5-D numbers are biased. They are not; only the selection, the pooled count and the order are affected (edit F5).

**Labels that could overstate.**
- (i) **CONSISTENT ACROSS STUDIES** printed for A5-D. It is automatic, and the printed provenance does not say so (§15 does, but §15 is not printed).
- (ii) **The pooled count**, and any pooled bound (§6.3 quotes 18/18 → 0.847), for A5-D.
- (iii) **S1's "S0 status" line (ADR-0021 K7(c)) and lane L.** These could cite an A5-D qualification without the fourth-arm string (F8, cross-ADR).
- (i) and (ii) are fixed by F5. (iii) is the lead's.

## 3. Arithmetic, R2 start rule, cut order (task 3)

Output from `arithmetic.out`, using rev4's own P9-I rates.

| Quantity | Recomputed | Rev4 |
|---|---|---|
| Q1 cells (100 + 100 + 30) | 230 | 230 ✓ |
| Q1 under cut 3 (100 + 60 + 30) | 190 | 190 ✓ |
| With Q2 | 256, + 3 check | 256 + 3 ✓ |
| Three-arm Q1 | 180 | 180 ✓ |
| Summed CPU-h Q1 / WX / probe | 15.84/17.74/23.36; 1.37/1.51/2.03; 7.65/11.60/13.52 | ✓ |
| Six workers Q1 / WX / probe / cut-3 Q1 | 2.64/2.96/3.89; 0.23/0.25/0.34; 1.27/1.93/2.25; 1.85/2.10/2.71 | ✓ |
| Whole plan / doubled / left | 4.94/5.94/7.28; 9.88/11.88/14.57; 1.43 h (8.9%) | ✓ |
| Three-arm whole | 4.37/5.29/6.44 | ✓ |
| Rev3-rule multiples | 1.110, 1.702, 1.850, 2.657 (three-arm 1.277) | ✓ |
| Pre-Q1 2·(0.8 + Q1) | 9.39 | 9.39 ✓ |
| Post-Q1 0.8 + Q1 + 2·(WX + probe) | 9.875 | 9.87 (rounding of 4.69 + 5.18; immaterial) |
| Q1 at its cap | 13.77 | 13.77 ✓ |
| Clopper–Pearson bounds (12 values) | 0.741, 0.606, 0.717, 0.571, 0.493, 0.368, 0.690, 0.615, 0.847, 0.762, 0.807, 0.703 | ✓ |

**Reading A, start rule.**
- *Before Q1:* charged + 2 × (Q1 + remaining pre-Q1 stages) ≤ 16. Otherwise cut 3; otherwise item 4.
- *After the Q1 gate:* charged + 2 × (WX + probe) at the actual candidate's rates ≤ 16. Otherwise cut 1, then cut 2.
- *Determinism.* The rule is deterministic: cuts are applied in a fixed order, each only if the rule still fails, and Q2 runs only for a candidate at both sizes.
- *One wording defect.* "the stages before it" does not say whether stages already run (and charged) are also doubled (F3).

**Thresholds under reading A** (rates = m × the slowest P9-I rates; Q1 at its projection):
- Q1 runs uncut up to m = 1.850; cut 3 up to 2.657; above that, item 4.
- After the gate, the probe is kept up to m = 1.675 (0.8 + 3.89m + 2·2.59m ≤ 16). WX is kept whenever Q1 ran uncut.
- **Rev4's bullet "The margin of the uncut plan is 11% … If the rehearsed rates exceed that margin, the registered cuts apply …" is wrong under reading A.**
  - The 1.11× is rev3's whole-plan rule.
  - At m = 1.2 reading A keeps the probe (11.69 h ≤ 16).
  - This is descriptive text, not a rule, but it misinforms the reader (F2).
- "If Q1 had run up to its own cap" is a vacuous case: a block that reaches its cap is INCOMPLETE, so there is no Q2. It is a harmless upper bound.

**Cut order.** Still fully determined.
- Cut 3 is the only cut before Q1.
- Cuts 1 and then 2 come after the gate.
- Item 4 is the terminal case.
- No new cut; the fourth arm is not a cut.

## 4. Findings

### F1 (major: needs a choice before implementation; enters no class or outcome) — the criterion behind d(X)

- **The gap.** §8.4 defines d(X) from "cells where X succeeds and A0 fails". §8.2 defines two kinds of success: under P9-II's criteria and under S0's criteria. §8.3 says "Qualification uses S0's criteria. Replication uses P9-II's." Neither covers the paired label, H20-B/C/D or §8.7 print item 6.
- **Prior reviews.** None settled it (grep of REVIEW.md, CONFIRM.md and RECHECK_REV3.md).
- **Why it matters now.** Rev4's new H20-D sentence ("If A0 does the same in S0…") depends on it. Under S0's criteria, A0 can fail condition 6 (read swap) even where it succeeds under P9-II's. P9-II recorded no read swap, so no observation bears on this choice. But the choice is made after P9-II, and should say so.
- **PENDING LEAD REVIEW.** Paste-ready, option (a); option (b) swaps the two criteria:
  - §8.4, first bullet, append: "Cell success in d(X) is success under S0's criteria (§8.2), the criteria of the class that H20-B, H20-C and H20-D read; d(X) under P9-II's criteria is printed beside it and enters no reading. **[lead's choice, made in revision 4 after P9-II's outcome was observed; P9-II recorded no read swap]**"
  - §2 H20-D: replace "If A0 does the same in S0," with "If A0 fails fewer than four of its 20 cells at 8K/16K in S0 (cell success as in §8.4),".
- **Note.** The same arithmetic applies to H20-B: P9-II's d(A1) at 16,384 was −2.

### F2 (minor) — budget bullets describe rev3's rule, not reading A

- In §10.4, replace the bullet beginning "**On the projection the twofold rule holds with n_L = 4 and no cut applies.**" with:
  > - **On the projection the twofold rule holds with n_L = 4 and no cut applies.** The projection is not a measurement. Under the headroom rule as worded below (reading A), at a common multiple m of the slowest P9-I rates and with Q1 running at its projection: Q1 runs uncut up to m ≈ 1.85; above that cut 3 applies, and Q1 under cut 3 fits up to m ≈ 2.66; above that nothing registered is run and the matter returns to the human lead (item 4). After the Q1 gate the probe is kept up to m ≈ 1.68 (0.8 + 3.89m + 2 × 2.59m ≤ 16) and dropped above that (cut 1); WX then fits whenever Q1 ran uncut. No new cut is defined, the fourth arm is not a cut, and the cap is not raised.
- At the end of the bullet "**What is lost is the smaller configuration.**", append: "These multiples, and the 1.43 hours above, are computed under revision 3's whole-plan rule; under reading A the thresholds are those of the last bullet."

### F3 (minor) — R2's pasted sentence (the re-check's own text) is not fully determined

- In §10.4's headroom rule, replace "Before Q1 the rule is evaluated on Q1 and the stages before it only." with "Before Q1 the rule is evaluated on Q1 and on the stages before Q1 that have not yet run; stages already run count once, as hours already charged."

### F4 (minor) — §9.1 "the outcome of row 1" can be read as §8.7 row 1 (NOT STARTED)

- Replace "S0 has the outcome of row 1 with Q1 recomputed by the auditor" with "S0 has the outcome ADDRESSING-QUALIFIED (4,096 AND 16,384) (§8.7 row 4) with Q1 recomputed by the auditor from raw records".

### F5 (minor) — the printed provenance omits that consistency is automatic for A5-D

- §3.4, the fixed sentence, append: "Its CONSISTENT ACROSS STUDIES label and pooled count include the P9-II records it was chosen on and add no independent evidence; no pooled per-draw bound is printed for A5-D."
- §3.4 item 3, append: "S0's own class, draw count and per-draw bound for A5-D come from draws not used in its selection and are read as stated; the selection affects the pooled count, the consistency label and the preference order."
- G10 compares the override part character for character, so it then checks the extended sentence.

### F6 (minor; a stop risk) — gates and rehearsal still cover arms that S0 never runs (open point 1)

- **The risk.** G4 runs on registered seeds before training and stops S0 if it fails. It still checks A4's k = N read at 65,536 slots, which gathers a value tensor of about 1.0 GiB (§10.4, "Known risk"), and A5-C, neither of which S0 trains. §10.3 also rehearses A4, and WX and 32K/64K for A0 and A2.
- **A second gap, pre-existing.** A6 at 32K/64K, which the probe trains, is not listed for rehearsal, so the probe's memory check has no measurement for it.
- **Paste-ready:**
  - §10.2 G4: "for **every arm the mapping can select** (A0, A1, A2, A4, A5-C, A5-D and WX of each)" → "for **every arm in S0's arm set** (§3.4: A0, A1, A2, A5-D), A6, A7, and WX of each arm that can still be the candidate (§3.5: A5-D, A1)".
  - §10.2 G4: "at 65,536 slots the full-N score path and A4's k = N read are checked against a direct computation" → "at 65,536 slots the full-N score path is checked against a direct computation".
  - §13 step 5: "for every arm the mapping can select and WX of each" → "for every arm in S0's arm set and WX of each arm that can still be the candidate (§3.5)".
  - §10.3: "and WX and the 32K/64K cell for **every arm that can become the candidate** (A0, A1, A2 and C4)" → "and WX and the 32K/64K cell for **every arm that can still be the candidate** (§3.5: A5-D and A1), and A6 at 32K/64K"; delete "A4 at k_0, mid-schedule and k = 8."
  - Keep §10.2's synthetic registries for every row of §3.3, adding "the override of §3.4 and the list of §3.5".

### F7 (minor; print only) — ALSO QUALIFIES is worded only for an A0 candidate

- With an arm chosen after observation ranked ahead of A1, A1's status must stay visible when A5-D is the candidate.
- §8.5 item 5: replace "Every later arm in the order that would also qualify is printed as **ALSO QUALIFIES: \<arms\>**." with "Whatever the candidate, every later arm in the order that would also qualify is printed as **ALSO QUALIFIES: \<arm\> (\<scope\>)**."

### F8 (minor; cross-ADR; the lead's call, no ADR-0020 edit) — ADR-0021

- ADR-0021 §5.6 item 1 cites "(ADR-0020 §9.1)" for the auditor recomputation. Rev4 §9.1 no longer states it and defers back. The rule survives in ADR-0021's own words, so the citation is only circular.
- ADR-0021's "S0 status" line (K7(c)) and lane item 5 ("S0's full annotation list") do not explicitly carry the §3.4 fourth-arm string, which §8.7 print item 1 attaches to an A5-D candidate.
- In the expected timeline the lane is omitted, so the practical impact is low. An editorial note in ADR-0021 would close it. That is outside this file.

### F9 (note) — headroom rounding

- 9.87 against 9.875 h. "Q1 at its own cap" is a vacuous case. No edit needed.

### F10 (optional) — status line

- Status line (line 3), append: "Fourth arm A5-D added by the human lead's decision after P9-II's outcome was observed (§3.4)."

### F11 (note; seeds, task 5)

- **ADR-0020 §7 / G9.** Consistent with ADR-0019 (P9-II init 1901–1902, calibration 1891), ADR-0021 §6.3 (N1's 2111, 2121, 2112, 2122 match) and ADR-0022 §9 (S0's list matches exactly).
- **Harmless differences.**
  - ADR-0021 lists P9-II as "1891–1892". 1892 does not occur in `studies/p9ii` or `configs`.
  - ADR-0021 also lists the review stand-in 941001. ADR-0020 omits it; it lies outside every range.
  - ADR-0021's G9 covers derived seeds (init + 1000…5000, `studies/p9/model.py:236`); ADR-0020's G9 does not.
- **Derived-seed check.** I checked offsets 1000–5000 for every listed init seed: no collision (S0 3001–7092 against S1 3101–7192, P9-II 2891–6902, P9-I 2791–6802, P9 2701–6702). Optional edit, G9: append "and the seeds derived from the initialization seeds (+1000 … +5000, as `studies.p9` uses)".

## 5. Consistency with ADR-0021 rev4 §5.6 and the seeds (task 5)

- **Lane L agrees in substance.**
  - The lane exists only with ADDRESSING-QUALIFIED (4,096 AND 16,384) before S1's freeze, with Q1 recomputed.
  - It is omitted unless the candidate is OVERLOAD-QUALIFIED; candidate A1 or A2 prints SUPERVISED ARM HAS NO 8K/4K CELL.
  - Cells 2K/4K, 8K/4K and 8K/16K at 4·F updates; the calibrated value comes from the arm-selection record (μ = 1.0 for A5-D).
- **Rev4's §9.1 consequence is correct.** With P9-II's records, the lane can exist only if A5-D is the candidate and is OVERLOAD-QUALIFIED. The residual issues are F4 and F8.
- **Seeds.** See F11.

## 6. Implementability (task 6)

- **Major.**
  - F1: the criterion behind d(X).
- **Minor.**
  - F3: the R2 wording.
  - F4: "row 1".
  - F6: gate scope and A6 rehearsal at 32K/64K.
  - F7: ALSO QUALIFIES scope.
- **No blocker.** Everything else is implementable as written, including:
  - A5-D from `studies.p9ii` unedited;
  - L_div on WX's queries;
  - the 8K/4K seed alternation;
  - the arm-selection record parts (a)–(d) and G10.

## 7. Rulings on the drafter's 13 open points

1. **Arms no longer in S0. Needs this exact edit: F6.** Left as is, a gate failure on A4 or A5-C, which are never trained, would stop S0.
2. **R2 reading A less demanding before Q1. Acceptable as drafted.** It was the re-check's offered reading and is the lead's choice. Keep the informational freeze sentence. Apply F2 and F3.
3. **Part (d) and the G10 clause. Acceptable as drafted.** The exclusion test is exactly §8.5 (b) at 4,096, and I recomputed it: {A5-D, A1}.
4. **H20-D reads "not supported" unless A0 fails at least 4 cells at 16,384. Acceptable as drafted; it must not be changed.**
   - It is a registered reading fixed before observation.
   - Changing it now would be a post-observation change; only the human lead could make it.
   - The sentence depends on F1, whose edit also fixes the sentence.
   - H20-B is subject to the same arithmetic.
5. **Preference order ranks a post-observation arm ahead of A1. Acceptable as drafted, plus F7.**
   - The order's pre-observation rationale is supervision type; A5-D is label-free.
   - §3.4 item 5 states the fact.
   - The human lead's words do not address order. Placing A5-D in C4's slot is recorded as the lead's application (§20 row 21).
6. **Scope of the human lead's words. Acceptable as drafted.** It is marked as the lead's application.
7. **"Set up by reference". Needs this exact edit**, so that it is clear what may run before acceptance.
   - §11: replace "Until it is, S0 may be implemented, set up by reference to P9-II's audited calibration record (S0 has no calibration of its own, §10.1) and rehearsed, but not frozen." with "Until it is, §13 steps 4–7 may proceed (implementation and tests, the pipeline check, the gates on the rehearsal draw, the implementation audit, the arm-selection record and its audit, the rehearsal), with P9-II's audited calibration values taken by reference (S0 has no calibration of its own, §10.1); step 8, the generation of the registered draws and the freeze, waits."
   - §18 condition 7: replace "Until then S0 may be implemented, set up by reference to P9-II's audited calibration record and rehearsed, but not frozen." with "Until then §13 steps 4–7 may proceed and step 8 waits (§11)."
8. **If the human lead does not accept P9-II. Acceptable as drafted: S0 returns to him before any freeze. What happens then is a decision for the human lead.**
   - What in S0 rests on P9-II, for the lead's message to him:
     - λ, U_pre and μ;
     - the mapping's result;
     - every input of the consistency rule (P9-II classes, failed draws, LM flags; §3.5);
     - the candidate list;
     - the F1 annotation;
     - the replication labels;
     - the negative-control print.
   - If he accepts with a reading that carries A5-D, the override becomes the mapping's own result, and §3.4 must be rewritten before the freeze.
9. **Fixed provenance sentence. Acceptable; extend it by F5.**
10. **§17 item 0 unanswered. Acceptable.** It does not block S0 (§13 step 2).
11. **Relayed quotations. Acceptable.**
    - §18 discloses that they were relayed.
    - The quoted words match the relay in my own task message. I too have only the relay.
    - The lead should check them against the chat record before approving.
12. **Archive of revision 3. Resolved.** `revisions/ADR-0020-rev3.md` (commit `7afac47`) is byte-identical to `c56b23a`'s ADR-0020.
13. **P9-II's measured rates not used. Acceptable as drafted;** the rehearsal decides.
    - For information only, from the median `wall_seconds` in `cells.csv`, including evaluation:

      | P9-II arm, size | s/update |
      |---|---|
      | A5-D, 4,096 | 0.0093 |
      | A1, 4,096 | 0.0110 |
      | A5-D, 16,384 | 0.0141 |
      | A1, 16,384 | 0.0203 (4% above the slowest P9-I rate) |
      | A0, 65,536 | 0.0398 |

    - Q1 at these rates is about 3.19 h with six workers, using A1 as a stand-in for A2 at 16,384. The probe round is about 1.45 h. Both are inside the projection's bracket.

Astra review: NOT_PERFORMED. This is a Claude (Opus 5.5) review. It is not an Astra review and not a human approval.
