# Confirmation review of ADR-0020 revision 2 (P10-S0), with the lead's rulings 1–6

- **Reviewer:** Claude Opus 5.5 (`claude-opus-5-5`), the same specification auditor as `REVIEW.md`. I wrote no part of ADR-0019–0022 or any code they rely on.
- **Date:** 2026-11-15. **Astra review: NOT_PERFORMED.** This is independent engineering and mathematical evidence, not Astra validation and not a human approval.
- **Inputs (sha256 prefixes):** ADR-0020 rev2 `62d16ed3`, ADR-0021 rev2 `9fd4b08f`, ADR-0022 rev4 `7516ca6a`, ADR-0019 rev4 `667ef3ef`. The lead's rulings 1–6 are quoted from the coordinator's message; they are not yet in the text.
- **Ran:** `c5_rev2_mapping_and_consistency.py` (output `outputs/c5_rev2.txt`; a failed first attempt is kept, see §6). **Did not run:** any training, any model, git or GitHub, or a download. No tracked file was edited.

## Verdict: READY AFTER the listed text edits

Two edits are required (E1, E2). Without E1, the design has the "two chances to pass" path described below. Every other finding is a minor edit (E3–E10). With E1–E10 applied as written, I see no need for another review round. Any passage the lead words differently needs a re-check.

## 1. Status of the review's findings

| Finding | Status in rev2 | Note |
|---|---|---|
| B1 (a)(b) readings of the direction | **Resolved.** S0 always runs and always contains A0, A1 and A2 on its own 10 × 2 draws. This is the human lead's literal text, so no reading is needed. | It creates the two-chances path; E1 closes it (ruling 1, corrected). |
| B1 (c) "stop capacity-scaling claims" | **Correctly left to the human lead** (§17 item 0). The NOT-QUALIFIED text is neutral. | It no longer concerns S0's design; see E9. |
| B2 target injection at 8K/4K | **Resolved.** Option (a), with G4 asserting it. | — |
| M1 mapping | **Resolved.** Re-enumerated: 2,462,636 P9-II records, 0 disagreements between the §3.2 rule and the §3.3 table. C4 is present only under ADDRESSING-RELIABLE or ANSWER-ONLY RELIABLE with A4, A5-C or A5-D carried. | One wording slip (E7). |
| M2 SMALL scope | Moot (removed). | — |
| M3 65,536 | **Resolved.** Probe only, bound 0.368, never in the label. | — |
| M4 replication vs added criteria | **Resolved.** Two classes per arm; REPLICATES / DOES NOT REPLICATE. | — |
| M5 order of work | **Resolved.** The pipeline check no longer needs the candidate; gates cover every selectable arm before selection; the rehearsal follows the mapping. | — |
| M6 Q3 | Dropped; the corrections are carried in §12.2. | — |
| M7 hand-off to S1 | **Not consistent with ADR-0021 rev2** (the lane omitted vs a two-cell descriptive lane; label names). | E2. |
| Minors m1–m20 | Applied or moot as §19 states. I checked m1, m4, m6, m7, m10, m13, m15–m17 and m20 in the text. | m11, m12, m18 are still open in the sibling drafts (E8). |

## 2. The lead's rulings

### Ruling 1 (consistency across studies): needed, but not well defined as worded → E1

**Why it is needed.** Revision 2 picks the candidate from S0's classes alone (§8.5, §15, "No rule uses the pooled count"). An arm that P9-II registered as FAILS at 16,384 can therefore be qualified by S0. With four learned arms re-tested, the path is real. That is the two-chances path my review warned an always-run design would open. Ruling 1 is the right repair.

**Two defects in the ruling as worded** (enumerated in `outputs/c5_rev2.txt`, Part 2):

1. **It is undefined whenever a draw is NOT_EVALUATED.** Both class tables allow one unevaluated draw (P9-II Stage 1 at 14 cells; S0 at 18 cells), so the pooled denominator can be 16 or 17, not 18. In every such case "16 of 18" has no meaning. Part 2 marks them "lead's rule undefined".
2. **It reads only P9-II's class at 4,096.** Example: P9-II RELIABLE at 4,096 and FAILS at 16,384 (0 of 4 draws), S0 RELIABLE at both sizes. Ruling 1 qualifies the arm at both sizes, although the pooled count at 16,384 is 10 of 14 (bound 0.460). The two-chances path stays open at the larger size.

**Threshold.** "16 of 18" is exactly the worst case of "RELIABLE in both studies". Each RELIABLE class allows at most one failed cell, hence at most one failed draw, so two studies allow at most two failed draws. The general form is **at most two failed draws among the evaluated draws of both studies**. That is 16/18 at 4,096 (bound 0.690) and 12/14 at 16,384 (bound 0.615) when every draw is evaluated. It is always met when the arm is RELIABLE in both studies: every P9-II-RELIABLE row in Part 2 qualifies under both versions. Where both versions are defined at 4,096, they agree in every enumerated case. I recommend this form, with the number marked as the lead's choice. Two further points:

- An arm that P9-II printed with LM CAPABILITY REDUCED at a size should not be made consistent by the pooled count; that flag is not a draw count.
- A1/A2 classes printed under P9-II's NEGATIVE CONTROL FAILED are still classes and should be read as such, with the negative-control result in the label (already §8.7 item 5).

Under the rule the fourth arm C4 is always consistent, because a carried arm is RELIABLE at both sizes in P9-II.

**E1 (required, paste-ready).**

(a) Replace §8.5 from "**Preference order, fixed …**" through item 4 with:

> **Consistency with P9-II (fixed now; the lead's ruling 1).** For a learned arm X and a core size, let P be X's class at that size in P9-II's registered record: at 4,096 the Stage 1 class, at 16,384 the Stage 2 class at the 4U readout. P is read only if P9-II's outcome is interpreted and, at 16,384, P9-II's Stage 2 is COMPLETE and X advanced. X is **CONSISTENT ACROSS STUDIES** at that size if:
> (a) P is not available or is NOT_EVALUATED. The label then says **SINGLE-STUDY EVIDENCE** at that size. Or:
> (b) P9-II did not print LM CAPABILITY REDUCED for X at that size, **and** at most [two] draws failed among the evaluated draws of both studies. In both studies a draw counts as failed when any of its evaluated cells fails under P9-II's criteria (conditions 1–5 of ADR-0019 §8.3). With every draw evaluated this is at least 16 of 18 draws at 4,096 and 12 of 14 at 16,384. It always holds when X is RELIABLE in both studies.
> Otherwise X is **INCONSISTENT ACROSS STUDIES** at that size. P9-II's classes for A1 and A2 are read as classes even where P9-II printed NEGATIVE CONTROL FAILED; that result is printed in the label (§8.7 item 5).
>
> **Preference order, fixed (the lead's ruling 3): A0, then C4 (if present), then A2, then A1.**
>
> 1. The candidate is the first arm in the order that meets the criteria **and** is CONSISTENT ACROSS STUDIES at 2K/4K and at 8K/16K. Its scope is 4,096 and 16,384.
> 2. If there is none, the first arm in the order that meets the criteria and is CONSISTENT ACROSS STUDIES at 2K/4K is printed as qualified at 4,096 only. Q2 is not run.
> 3. If there is none, no arm is qualified.
> 4. An arm that meets the criteria at a size but is INCONSISTENT ACROSS STUDIES there is printed **RELIABLE IN S0; INCONSISTENT ACROSS STUDIES (P9-II \<class\>; pooled \<failed\> of \<n\> draws failed)**. It is not qualified at that size, and the rule moves to the next arm.
> 5. When A0 is the candidate the label reads **(ANSWER-ONLY SUFFICES)**. Every later arm in the order that would also qualify is printed as **ALSO QUALIFIES: \<arms\>**. SINGLE-STUDY EVIDENCE is printed for each size where (a) applied.

(b) §6.3, last paragraph: replace "No rule uses the pooled count." with:

> The pooled count enters exactly one rule, the consistency rule of §8.5, and there it is counted in failed draws over the evaluated draws of both studies.

(c) §2, H20-Q:

> At least one arm meets S0's criteria and is CONSISTENT ACROSS STUDIES at both core sizes (§8.5).

(d) §8.7 row 6, append:

> and every arm that met S0's criteria but was INCONSISTENT ACROSS STUDIES, with P9-II's class and the pooled count.

(e) §15, replace the bullet "That a qualification overrides P9-II …" with:

> That S0 overrides P9-II. An arm qualifies only if it is CONSISTENT ACROSS STUDIES (§8.5). Where P9-II has a class, at most [two] draws failed among both studies' evaluated draws. Where it has none, the label says SINGLE-STUDY EVIDENCE.

(f) §20, row 2:

> Candidate from S0's classes subject to the consistency rule of §8.5 (rulings 1 and 3); preference order A0, C4, A2, A1.

(g) Replace the section "Points the drafter could not settle" with:

> **The lead's rulings on the drafter's points (2026-11-15):**
> (1) consistency rule, §8.5;
> (2) NOT STARTED without an audited P9-II calibration record, §3.2;
> (3) preference order A0, C4, A2, A1, §8.5;
> (4) the fourth arm only when P9-II carries a label-free arm, §3.2;
> (5) WX and the probe after the Q1 gate, WX on the Q1 draws, §6.2;
> (6) class thresholds of §8.3 confirmed by the confirmation review.
> ADR-0021 revision 2 was checked by the confirmation review (§9).

**Two-chances path after E1.** Closed. An arm with a registered P9-II failure at a size can qualify there only if the two studies together show no more failed draws than two RELIABLE studies could. Four arms are re-tested, so some family-wise inflation remains. It is bounded by each arm having to be RELIABLE at both sizes in S0 (at least 9 of 10 draws each) and consistent with P9-II. I would not add a correction.

### Ruling 2 (no audited calibration record → NOT STARTED): agreed

It is the only branch in which A1 and A2 are undefined. §3.2 item 1, §8.7 row 1, §14 and §17 item 1 are consistent with it.

### Ruling 3 (A0 first): agreed

The preference order matches ADR-0019's carry-forward order and the principle that the answer-only method needs no labels and no extra mechanism. C4 (label-free) before A2 (supervision removed) before A1 is the right sequel. Applied in E1(a).

### Rulings 4 and 5 (accepted as drafted): agreed, with one honest-wording edit (E6)

- **Ruling 4.** C4 exists only if P9-II carries a label-free arm. If P9-II's outcome is ADDRESSING-RELIABLE AT 4,096 ONLY with, say, A5-C as the only reliable arm, the most promising label-free intervention is not in S0. Under the consistency rule it could rarely qualify anyway (P9-II has failed draws at 16,384), but the requirements map should say so (E6).
- **Ruling 5.** WX on the Q1 draws after the gate is selection-biased in WX's favour (the candidate passed on those draws). That is acceptable for an annotation, and §6.2 states it.

### Ruling 6 (class thresholds): confirmed, with one sentence added (E5)

- 20-cell types: RELIABLE at no more than one failed cell gives 9 of 10 draws at worst, bound 0.606 (8 of 9 → 0.571 with one draw not evaluated). UNRELIABLE from 5 of 20 matches ADR-0019's proportion (4 of 16, 2 of 8 = 25%).
- 10-cell types: RELIABLE at no more than one failed cell, same bound 0.606. UNRELIABLE from 3 of 10 (25% rounds up to 3).
- NOT_EVALUATED at more than one draw is consistent across both tables.
- First-match precedence is correct: NOT_EVALUATED before RELIABLE before UNRELIABLE before FAILS; "UNRELIABLE (LM CAPABILITY REDUCED)" is printed when the count of row 2 is met.
- UNRELIABLE vs FAILS enters no rule; only RELIABLE vs not matters, which E5 states.

## 3. Arithmetic and resources (`outputs/c5_rev2.txt`, Part 3)

**Cell counts.**

| Item | Cells |
|---|---|
| Q1 with three learned arms: 80 + 80 + 20 | 180 ✓ |
| Q1 with four learned arms: 100 + 100 + 30 | 230 ✓ |
| WX | 20 ✓ |
| 65,536 probe | 6 ✓ |
| Pipeline check | 3 ✓ |
| Total | 259 |

**Projections.**

| Rates | Q1 (four arms), CPU-h | WX, CPU-h | Probe, CPU-h | Six-worker time | Doubled | Left of 16 h |
|---|---|---|---|---|---|---|
| fastest | 15.84 | 1.37 | 7.65 | 4.94 h | 9.88 h | 6.12 h |
| W7 | 17.74 | 1.51 | 11.60 | 5.94 h | 11.88 h | 4.12 h |
| slowest | 23.36 | 2.03 | 13.52 | 7.28 h | 14.57 h | 1.43 h (9%) |

All match the draft's figures.

**Is the cut order adequate?** It is adequate to make the run fit:

- The uncut plan absorbs rates up to 1.11× the slowest P9-I rates.
- After cut 2 (probe) it absorbs up to 1.70×.
- Q1 alone absorbs up to 1.85×.
- After cuts 1–3, Q1 needs 7.0 h doubled at the slowest rates.

Two improvements (E4):

1. **Order.** WX is cut before the probe although the probe costs about six times more (2.25 h vs 0.34 h per round at the slowest rates) and is the weaker annotation (bound 0.368). A small overrun therefore removes the cheaper block and keeps the dearer one only if the overrun is under 0.7 h doubled.
2. **Timing.** Both are decided before Q1 "at the most expensive possible candidate", so the probe can be cut because A1/A2/A4 *might* be the candidate when A0 is. Re-evaluating after the Q1 gate with the actual candidate's rehearsed rate is deterministic and fixed in advance.

## 4. Hand-off to S1 and S2 (§9)

- **ADR-0021 rev2 §5.6 vs ADR-0020 rev2 §9.1. They do not match:**
  - **Labels.** S1 item 1 names "ADDRESSING-QUALIFIED, ADDRESSING-QUALIFIED AT 4,096 AND 16,384 ONLY, or … ; 65,536 \<status\>". Revision 2 of S0 has only ADDRESSING-QUALIFIED (4,096 AND 16,384) and AT 4,096 ONLY.
  - **Lane without OVERLOAD-QUALIFIED.** S1 runs a descriptive lane on 2K/4K and 8K/16K without 8K/4K (item 4; no step verdict, item 5). S0 §9.1 says the lane is OMITTED in that case.
  - **Recording.** S1 does not require the F-LA cells to record S0's probe, H1/H2 and read swap.
  - S1's design (descriptive, no step verdict) is the more recent and is internally coherent, so S0 should defer to it. **E2.**
- **ADR-0022 rev4.** No slot-level learned addressing; a supplement needs approval. That is consistent with §9.1. Still open from the review: "s_c(S0)" (§10) and the store named "S1" (§6.2, §7, line "ACQ1 (S1)") collide with the study names; "a separately approved supplement" (§5.4); its seed assertion lists "P1–P9-II and S1" but not S0. **E8.**
- **Seeds across the four studies.**

| Study | Range | Tests | Status |
|---|---|---|---|
| P9-II | 190001–191599 | 910001–919999 | consistent in S0 and S1 |
| S0 | 200001–209999 | 920001–920999 | unused in the repository and `experiments/` (review m19) |
| S1 | 210001–219999 | ADR-0021 rev2 §6.3 says **921001–929999**; ADR-0020 rev2 §7 and the coordinator say 921001–921999 | **conflict: one must change (E8)** |
| S2 | 220001–228999 | 229001–229999 | the 229xxx test block is inside S2's declared 220001–229999, so no conflict |

  S0's internal layout (offsets 0–19, 20–39, 40–41, 44–45, 48–49, 50–52, 60–79) has no overlaps, and the largest seed is 201480 (reserve 2).

## 5. Requirement check (the human lead's addressing-qualification text)

| Requirement | Met? |
|---|---|
| Addressing a mandatory prerequisite; P9-II interventions as a gate, not assumed to have succeeded | Yes. A1/A2 are re-tested in every branch, and the carried label-free arm is added. Caveat: a label-free arm reliable at 4,096 only is not re-tested (E6). |
| Compare answer-only with supervision and staged optimization | Yes. A0, A1, A2 at both sizes, 10 draws × 2 seeds, paired rule. |
| Multiple independent draws and initialization seeds | Yes (cut 3 would reduce 16,384 to one seed per draw; the label says so). |
| Fact-specific retrieval; resistance to collapse; strong memory dependence; no oracle at inference | Yes: conditions 1–6, ADDRESS STABLE, COLLAPSE-FREE printed, G6. |
| Reliability not overstated relative to P9-II | Only after E1. |
| If none qualifies: report an addressing failure and return with alternatives | Yes (§8.7 row 6, §12.1). "Stop capacity-scaling claims" awaits the human lead (§17 item 0). |
| Independent of S1/S2, own seeds/budget; S1/S2 do not wait; learned addressing evaluated separately if qualified | Yes. The expected lane omission is stated plainly (§9.2). |

## 6. Text edits

**E1 (required).** The consistency rule and preference order. Paste-ready text in §2 above.

**E2 (required).** Align §9.1 with ADR-0021 rev2. Replace the S1 cell of row 1 of the §9.1 table with:

> The candidate exactly as S0 froze it (S0's code hash; P9-II's calibrated value from the arm-selection record; no tuning), as ADR-0021 §5.6 defines the lane: cells 2K/4K and 8K/16K, and 8K/4K only if OVERLOAD-QUALIFIED (never for A1 or A2, which have no 8K/4K cell); each cell run for 4·F updates; no step verdict. Each F-LA cell records S0's probe set, H1/H2 and the read swap, and prints whether it succeeds under S0's cell-success rule (§8.2). Without OVERLOAD-QUALIFIED the lane's 8K/16K-against-8K/4K difference is printed NOT AVAILABLE. A human acceptance is not required by either ADR.

And in ADR-0021 rev2 §5.6 (the lead's sibling edit):

> - Item 1: "… S0 (ADR-0020) has the outcome **ADDRESSING-QUALIFIED (4,096 AND 16,384)**, with Q1 recomputed by the auditor (ADR-0020 §9.1)."
> - Item 4, append: "Each F-LA cell records S0's probe set, H1/H2 and the read swap, and prints whether it succeeds under ADR-0020 §8.2."

**E3 (minor).** §3.3, row "ADDRESSING-RELIABLE AT 4,096 ONLY": "none (nothing is carried)" becomes:

> none (no label-free arm is carried; A0 may be, if RELIABLE at 16,384 only)

My enumeration found A0 carried in 237,544 records of that row; the result (no C4) is unchanged.

**E4 (minor; the lead's choice of order).** §10.4, after the headroom rule:

> After the Q1 gate the rule is evaluated once more, before WX and the probe, with the rehearsed rates of the actual candidate and the hours actually charged. Cuts 1 and 2 are applied then, not before Q1. Cut 3 is decided before Q1.

And swap cuts 1 and 2 [lead's choice]:

> 1. Drop the 65,536 probe. 2. Drop WX.

**E5 (minor).** §8.3, after the table:

> UNRELIABLE and FAILS enter no rule; qualification, replication and OVERLOAD use RELIABLE against not RELIABLE only.

And after cut 3 in §10.4:

> With cut 3, a draw at 8K/16K succeeds when its one cell succeeds; the consistency rule of §8.5 counts it that way.

**E6 (minor).** §16, row 1:

> A1 and A2 are re-tested on S0's own draws in every branch (§3.1). P9-II adds at most one arm, its carried label-free arm (§3.2). A label-free arm that P9-II found RELIABLE at 4,096 but did not carry is not re-tested (§3.3, consequence).

**E7 (minor).** §6.3, first table: add the row "16 of 18 / 12 of 14 (pooled, the consistency threshold): 0.690 / 0.615".

**E8 (minor; sibling drafts).** Replace §9.3 with the current state:

> - ADR-0021 rev2: §5.6 items 1 and 4 as E2; §6.3 unit tests 921001–929999 → 921001–921999 (or this ADR's §7 and G9 → 921001–929999; one of the two, consistently).
> - ADR-0022 rev4: §10 "s_c(S0)" → "s_c(Stage 0)"; the stores named "S1"/"S2" in §6–§11, and "ACQ1 (S1)", renamed (for example "St1"/"St2"), because S0, S1 and S2 are study names; §5.4 "a separately approved supplement" → "a supplement approved by the human lead (ADR-0020 §17 item 3)"; §9 "disjoint … from every seed of P1–P9-II and S1" → "… of P1–P9-II, S0 (200001–209999, 2001–2002, 2091–2092, 920001–920999) and S1".

**E9 (minor).** §13 step 2, append:

> The answer is required before any programme-level text, S1 report summary or S2 report summary cites S0's outcome (§17 item 3).

**E10 (minor).** G10 has an independent recomputation already on record. Add to §10.2 G10:

> the auditor's enumeration script `adr-0020-review/c5_rev2_mapping_and_consistency.py` (Part 1) is re-run on P9-II's committed records.

## 7. Commands, environment, failed attempts

Environment: macOS Darwin 27.2.0 arm64, `python3` 3.15.1 (standard library only). Review folder R = `/private/tmp/claude-501/-Users-daniellaloush-dandush03-ArborLM--claude-worktrees-arborlm-consolidation-experiment-2b31c1/cfc0efd5-b7ca-4602-959a-07fe6b8d4e7d/scratchpad/adr-0020-review`.

- `cd R && python3 -I c5_rev2_mapping_and_consistency.py` → `outputs/c5_rev2.txt`. It imports the auditor's own `c2_mapping_enumeration.py` (P9-II model), not project code.
- **Failed attempt, kept:** `outputs/c5_rev2_ATTEMPT1_probe_round_bug.txt`. Part 3 added the probe's summed CPU-hours (7.65–13.52) instead of its one-round time (summed / 6). This gave a false "cap exceeded" result. My bug, not the draft's; corrected in place and re-run. Parts 1 and 2 were unaffected.

Astra review: NOT_PERFORMED. This review is not an Astra review and not a human approval.
