# ADR-0020 revision 3 → revision 4: every changed passage

- **Drafted by:** Claude Fable 5.2 (`claude-fable-5-2`), as the lead's drafter, 2026-11-15. Text only: no code of the study, no run, no commit, no network. Nothing was written into the `p10-design` worktree.
- **Base:** `docs/decisions/ADR-0020-p10-s0-addressing-qualification.md` at revision 3, sha256 `19d44458…` (the hash the re-check records), commit `c56b23a`.
- **Read:** `AGENTS.md`, `CLAUDE.md`; ADR-0020 revision 3 in full; `adr-0020-review/RECHECK_REV3.md` in full; ADR-0021 revision 4 header, §5.6, §6 (seed lines), §15, §21; ADR-0019 §4, §5, §8.4–§8.6, §16 (the passages on A5-D, the stages and the carry-forward order); `results/p9ii-run-2026-11-15/OUTCOME.md`, `classes.csv`, `results.json` (`draw_counts`, `carried_forward` only); `results/p9ii-calibration-2026-11-15/calibration.json`; `docs/reviews/p9ii-results-2026-11-15/REVIEW.md` (the passages on A5-D, A0 and the carry-forward). `docs/RESEARCH_HANDOFF.md`, `docs/EXPERIMENT_PROTOCOL.md` and `docs/RESEARCH_LOG.md` were not re-read for this text edit.
- **How the file was made:** revision 3 was copied and 46 exact text edits were applied by `build/build.py` (beside this file), each anchored on a passage that occurs exactly once. Everything not listed below is byte-identical to revision 3.
- **Not a review.** Astra review: NOT_PERFORMED. This draft needs an independent confirmation and the lead's approval; neither exists. The human lead has not accepted the P9-II outcome.

## What did not change

No threshold, criterion, class rule, preference order (A0, C4, A2, A1), consistency rule, seed, draw count, update count, cut or cap. The mapping of §3.2 and §3.3 is kept word for word, apart from the fixed string R6 asked for.

## Arithmetic checked for this revision (Python standard library, from the ADR's own rates)

- Q1 with n_L = 4: 100 + 100 + 30 = **230 cells**; with a candidate 230 + 20 + 6 = **256**, plus 3 pipeline-check cells. Without a candidate 230. The 180-cell case no longer occurs.
- Summed CPU-hours (fastest / W7 / slowest): Q1 15.84 / 17.74 / 23.36; WX 1.37 / 1.51 / 2.03; probe 7.65 / 11.60 / 13.52.
- Six workers: Q1 2.64 / 2.96 / 3.89; WX 0.23 / 0.25 / 0.34; probe (one round) 1.27 / 1.93 / 2.25; other about 0.8. Whole plan **4.94 / 5.94 / 7.28 h**; doubled **9.88 / 11.88 / 14.57 h** against the 16-hour cap.
- These equal revision 3's "largest configuration", which was already computed for four learned arms. The twofold rule holds on the projection; no cut applies on the projection.
- Margins at the slowest rates: uncut plan 1.11×, without the probe 1.70×, Q1 alone 1.85×, Q1 under cut 3 (190 cells, 2.71 h) 2.66×. Revision 3's three-arm configuration (6.44 h, 1.28×) is gone.
- P9-II failed draws per arm (from `results.json`): A0 6 of 8 and 0 of 4; A5-D 0 of 8 and 0 of 4; A1 0 of 8 and 2 of 4; A2 8 of 8 and no Stage 2 class.

## Every changed passage

### C01 — header, status line

- **Answers:** task item 5
- **Reason:** New status for revision 4.

**Old:**

> - **Status: DESIGN REVISION 3 — CONFIRMED BY THE AUDITOR SUBJECT TO E1–E10, WHICH THIS REVISION APPLIES. SPEC: PENDING ASTRA REVIEW. Nothing is implemented or run.**

**New:**

> - **Status: DESIGN REVISION 4 — pending an independent confirmation; lead's approval PENDING; nothing implemented or run. SPEC: PENDING ASTRA REVIEW.**

### C02 — header, revision history

- **Answers:** R10
- **Reason:** "(this text)" was attached to revision 2 and to revision 3; neither is this text any more.

**Old:**

> Revision 2 (this text): applies that review under the lead's rulings.

**New:**

> Revision 2: applies that review under the lead's rulings.

### C03 — header, revision history

- **Answers:** R10; task item 5
- **Reason:** Revision 3 is no longer this text; revision 4 is added to the history.

**Old:**

> Revision 3 (this text): applies E1–E10 with the auditor's text and the lead's choices on the bracketed points. §19 maps every finding of both reviews to its change; §20 lists the lead's choices. The auditor stated that with E1–E10 applied as written no further review round is needed, and that any passage worded differently needs a re-check; the passages not pasted verbatim are listed at the end of §19.

**New:**

> Revision 3 (commit `c56b23a`): applies E1–E10 with the auditor's text and the lead's choices on the bracketed points. §19 maps every finding of both reviews to its change; §20 lists the lead's choices. The auditor stated that with E1–E10 applied as written no further review round is needed, and that any passage worded differently needs a re-check; the passages not pasted verbatim are listed at the end of §19. Re-check of revision 3 by Opus 5.5 against E1–E10 and against P9-II's actual records (`adr-0020-review/RECHECK_REV3.md`): READY SUBJECT TO the text edits R1–R10 (R1 and R2 major, R3–R10 minor). **Revision 4 (this text)** does two things and nothing else: it makes A5-D the fourth arm by the human lead's decision of 2026-11-15, taken after P9-II's outcome was observed and before any S0 record exists (§3.4, §18); and it applies R1–R10 and note N1. §21 maps each change to its source. No threshold, criterion, preference order, consistency rule, seed, draw count or cap is changed. Revision 3 is to be kept unchanged as `docs/reviews/p10-design-2026-11-15/revisions/ADR-0020-rev3.md`.

### C04 — header, evidence line

- **Answers:** R10; human decision
- **Reason:** The revision 3 sentence is kept as the record of when its rules were fixed, with the commits the re-check names. Revision 4 states honestly that it is written after P9-II's outcome, what it takes from it, and that the human lead has not accepted that outcome.

**Old:**

> P9-II (ADR-0019 revision 4): **not yet run**; this text is written before any P9-II observation and uses no P9-II result. Review diagnostics are exploratory and enter no rule.

**New:**

> P9-II (ADR-0019 revision 4): **not yet run**; this text is written before any P9-II observation and uses no P9-II result (written at `c56b23a`, before P9-II's run records `d72b173`; that sentence is true of revisions 1–3 and of every rule and number they fixed). **Revision 4 is written after P9-II's registered outcome was observed.** P9-II is COMPLETE with the registered outcome ADDRESSING-RELIABLE: A5-D (LABEL-FREE); interface carried forward A0; recomputed by Opus 5.5 (171 comparisons, 0 disagreements); **not accepted by the human lead at the time of writing**. Revision 4 takes one thing from that outcome that revision 3's rules did not already take: the fourth arm, by the human lead's decision (§3.4). No S0 code, pipeline check, rehearsal or record exists. Review diagnostics are exploratory and enter no rule.

### C05 — §0

- **Answers:** human decision
- **Reason:** The one-paragraph summary must say what the mapping gave and that the fourth arm was added by decision after observation.

**Old:**

> P9-II's outcome adds at most one further arm, by a mapping fixed here (§3).

**New:**

> P9-II's outcome adds at most one further arm, by a mapping fixed here (§3). Applied to P9-II's records, that mapping gives no further arm. The human lead then added A5-D, the label-free diversity penalty, as the fourth arm, after P9-II's outcome was observed and knowing that A5-D was RELIABLE there (§3.4). For A5-D, S0 is therefore a confirmatory replication on new draws, not an unbiased first test.

### C06 — §1, list item 1

- **Answers:** human decision
- **Reason:** A5-D's classes are now among those S0 can reproduce.

**Old:**

> 1. Whether P9-II's classes for A0, A1 and A2 are reproduced by a second study with its own draws, and with ten draws where P9-II's Stage 2 has four.

**New:**

> 1. Whether P9-II's classes for A0, A1 and A2 (and, by the decision of §3.4, A5-D) are reproduced by a second study with its own draws, and with ten draws where P9-II's Stage 2 has four.

### C07 — §2, H20-D

- **Answers:** human decision
- **Reason:** The fourth arm exists. The hypothesis text and its reading (§8.7) are unchanged. One arithmetic consequence of the unchanged reading is stated because it is known before S0 runs.

**Old:**

> - **H20-D (the carried label-free arm; only if a fourth arm exists).** C4 is RELIABLE and IMPROVES ON A0 at both core sizes.

**New:**

> - **H20-D (the carried label-free arm; only if a fourth arm exists).** C4 is RELIABLE and IMPROVES ON A0 at both core sizes. *Revision 4:* the fourth arm exists and is A5-D, added by the human lead's decision and not carried by the mapping (§3.4). The hypothesis and its reading are unchanged. Stated before S0 runs: IMPROVES ON A0 needs d ≥ 4 (§8.4), that is at least four cells in which A0 fails; in P9-II A0 succeeded in 8 of 8 cells at 16,384 (4U). If A0 does the same in S0, H20-D reads "not supported" whatever A5-D does. That is the registered reading, not a defect to be repaired.

### C08 — §3.2 item 4

- **Answers:** R6
- **Reason:** The re-check found no fixed string for the case in which the carried arm is already in S0.

**Old:**

> If it is A0, A2 or A1, or no arm is carried, there is no fourth arm, and the reason is printed.

**New:**

> If it is A0, A2 or A1, there is no fourth arm and the record prints **FOURTH ARM: NONE — P9-II CARRIED \<arm\> (ALREADY IN S0)**. If no arm is carried, there is no fourth arm, and the reason is printed.

### C09 — §3.2, closing paragraph

- **Answers:** human decision
- **Reason:** The arm-selection record now has a second part. The mapping stays as the record of what the pre-fixed rule gives.

**Old:**

> The mapping is evaluated by a committed script; its output, the **arm-selection record**, is part of the freeze. The auditor recomputes it from this text, not from the implementer's script (gate G10).

**New:**

> The mapping is evaluated by a committed script; its output, the **arm-selection record**, is part of the freeze. The auditor recomputes it from this text, not from the implementer's script (gate G10). From revision 4 the record has a second part, the override of §3.4, which the script copies from this text and does not compute.

### C10 — §3.3, after the consequence sentence: new §3.4 and §3.5

- **Answers:** human decision (task items 1 and 3); R6
- **Reason:** New §3.4 records what the mapping gave, the override, its provenance and the fixed printed string with P9-II's F1 annotation. New §3.5 states what the unchanged consistency rule does with P9-II's actual records for each arm, A5-D included, and which arms can still qualify.

**Inserted after this passage (which is unchanged):**

> **Consequence, stated:** a label-free arm that P9-II finds RELIABLE at 4,096 but that is not the carried arm (because A0 precedes it, or because it failed or was not run at 16,384) is not in S0.

**New text:**

>  *Revision 4: this case occurred, for A5-D, and the human lead overrode it (§3.4).*
>
> ### 3.4 Revision 4: what the rule gave on P9-II's records, and the human lead's override
>
> §3.2 and §3.3 are kept as written in revision 3. They are the record of what the rule fixed before any P9-II observation gives.
>
> **What the rule gave.** Evaluated by the auditor on P9-II's committed records (`RECHECK_REV3.md` §2):
>
> | §3.2 step | P9-II record | Result |
> |---|---|---|
> | 1 calibration | `results/p9ii-calibration-2026-11-15/calibration.json` (sha256 `ad5d7ee2…`): λ = 1.0, U_pre = 2,048, k_0/N = 0.125, μ = 1.0; audited | exists; S0 runs |
> | 2 outcome row | ADDRESSING-RELIABLE, row 4; COMPLETE, interpretable | interpreted |
> | 3 Stage 2 | COMPLETE | read |
> | 4 carried arm | A0 | **no fourth arm** |
>
> The row of §3.3 that applies is "ADDRESSING-RELIABLE, carried arm A0 (RELIABLE at 16,384, not at 4,096) — none (already in S0)". By §3.2 item 4 the mapping's own result prints **FOURTH ARM: NONE — P9-II CARRIED A0 (ALREADY IN S0)**. This is the case named in §3.3's consequence: A5-D was RELIABLE in P9-II at 4,096 (16 of 16 cells) and at 16,384 (8 of 8), and was not carried because A0 precedes it in ADR-0019's order.
>
> **The override.** The lead put this question to the human lead: "Add the diversity penalty to S0? As written, S0 cannot test it and can only qualify the supervised arm. I recommend adding it; the alternative is to run S0 as written and test the penalty in P10-I." The human lead's answer of 2026-11-15, verbatim (§18):
>
> > yes s0 should include the penalty and i approve s2 download
>
> (The second half concerns ADR-0022 and is not S0's.) By that decision **the fourth arm C4 is A5-D**: answer-only training plus μ·L_div on the batch's normalized, un-centred queries, exactly as ADR-0019 §4 defines it and as `studies.p9ii` implements it, with **μ = 1.0** from P9-II's audited calibration record. The decision overrides one result of the mapping, the entry "no fourth arm". It changes no other rule of this ADR.
>
> **Provenance. To be read with every S0 result for A5-D.**
>
> 1. **The decision was made after P9-II's outcome was observed** (run records `d72b173`, recomputation `74f15d1`) **and before any S0 record exists.** No S0 code, pipeline check, rehearsal, gate output or generated draw exists.
> 2. **The arm was chosen with knowledge of its result.** The human lead and the lead knew that A5-D was RELIABLE in P9-II: 16 of 16 cells at 4,096 and 8 of 8 at 16,384. A5-D is in S0 because of that observed result, not because a rule fixed in advance selected it.
> 3. **For A5-D, S0 is a confirmatory replication on new draws of an arm selected on its observed result. It is not an unbiased first test.** S0's draws, seeds and panels are new and disjoint from P9-II's (§7), and every threshold was fixed in revision 3 before P9-II ran. What is not independent of P9-II is the choice to test this arm.
> 4. **The pooled count adds no independent evidence for A5-D.** P9-II's A5-D cells are the cells on which the arm was selected, and none failed. CONSISTENT ACROSS STUDIES (§8.5) therefore holds for A5-D whenever it is RELIABLE in S0 (§3.5). For A5-D that label means "S0 did not contradict the records the arm was chosen on", and no more.
> 5. **The preference order A0, C4, A2, A1 (§8.5) was fixed in revision 3, before P9-II ran. The occupant of C4 was chosen after.** The order therefore places an arm chosen after observation ahead of A1. The order is not changed; this is stated so that it is not read as a pre-registered preference for A5-D.
> 6. **Scope.** The human lead's words do not list cells. The lead applies them thus: A5-D takes exactly the place revision 3 defines for a label-free C4 (2K/4K, 8K/16K and 8K/4K in Q1; WX and the 65,536 probe if it is the qualified candidate), and nothing more.
> 7. P9-II's F1 ruling left "whether a later study uses A0, A5-D or both" to "that study's own specification and approval". This decision is that choice for S0: both.
> 8. **The human lead has not accepted the P9-II outcome at the time of writing.** The decision above is not such an acceptance and is not recorded as one (§18).
>
> **Printed string (fixed).** Wherever the fourth arm is named, and wherever a class, label or annotation of A5-D is printed (§8.7):
>
> **FOURTH ARM: A5-D — ADDED BY THE HUMAN LEAD'S DECISION OF 2026-11-15; THE REGISTERED MAPPING GAVE NONE (P9-II CARRIED A0)**
>
> followed by P9-II's F1 annotation, verbatim from `results/p9ii-run-2026-11-15/OUTCOME.md`: *A0 is UNRELIABLE at 4,096 (4/16) and at chance at matched updates at 16,384; A5-D is the only label-free arm RELIABLE at both sizes; A5-D was not probed at 65,536 because the rule sent A0 to Stage 3.*
>
> and by the fixed sentence: **"A5-D was added after P9-II's outcome was observed, knowing it was RELIABLE there (16/16 at 4,096; 8/8 at 16,384). For A5-D, S0 is a confirmatory replication on new draws, not an unbiased first test."**
>
> **The arm-selection record** (part of the freeze) therefore holds: (a) the mapping's result as the script and the auditor compute it, with the hashes of the P9-II records read; (b) the override: the human lead's words, the date, the printed string, the F1 annotation and the fixed sentence; (c) the calibrated values used, λ = 1.0, U_pre = 2,048 and μ = 1.0 (k_0/N = 0.125 is not used: A4 is not in S0); (d) the arms that can still be the candidate (§3.5).
>
> **S0's arm set in revision 4** (n_L = 4):
>
> | Arm | Calibrated value | Cell types |
> |---|---|---|
> | A0 | — | 2K/4K, 8K/16K, 8K/4K |
> | A1 | λ = 1.0 | 2K/4K, 8K/16K |
> | A2 | U_pre = 2,048 updates at 2,048 facts, 8,192 at 8,192 facts (§5.3) | 2K/4K, 8K/16K |
> | C4 = A5-D | μ = 1.0 | 2K/4K, 8K/16K, 8K/4K; WX and the 65,536 probe if it is the candidate |
> | A6 | reference | 2K/4K, 8K/16K, 8K/4K; the 65,536 probe |
> | A7 | reference | 2K/4K, 8K/16K |
>
> μ = 1.0 was calibrated by P9-II on W7 at 4,096 slots and 0.5 facts per slot. At 8K/4K, in WX and at 65,536 it is an untested transfer (§15). In WX(A5-D), L_div is taken on WX's queries (§5.2: the same loss terms).
>
> ### 3.5 What the consistency rule does with P9-II's records (a consequence; no rule is changed)
>
> The rule of §8.5 was fixed in revision 3. Applied to P9-II's committed records it gives the following before S0 runs. A P9-II draw is failed when any of its cells fails (§8.5 (b)); the counts are from `results.json` (`draw_sensitivity.draw_counts`), as read by the re-check and re-read for A5-D by the drafter. P9-II printed LM CAPABILITY REDUCED for no arm at either size.
>
> | Arm, size | P9-II class (cells) | P9-II failed draws | What §8.5 then requires of S0 |
> |---|---|---|---|
> | A0, 4,096 | UNRELIABLE (4/16) | 6 of 8 | nothing can satisfy it: more than two failed draws already. **INCONSISTENT ACROSS STUDIES whatever S0 observes** |
> | A0, 16,384 | RELIABLE (8/8) | 0 of 4 | at most two failed draws of S0's ten (P9-II's criteria). No effect on qualification, because A0 fails the rule at 4,096 |
> | A5-D, 4,096 | RELIABLE (16/16) | 0 of 8 | at most two failed draws of S0's ten. **Met whenever A5-D is RELIABLE in S0** (RELIABLE allows at most one failed cell, so at most one failed draw) |
> | A5-D, 16,384 | RELIABLE (8/8) | 0 of 4 | the same. **Met whenever A5-D is RELIABLE in S0** |
> | A2, 4,096 | FAILS (0/16) | 8 of 8 | **INCONSISTENT ACROSS STUDIES whatever S0 observes** |
> | A2, 16,384 | none (A2 has no Stage 2 class) | — | case (a): SINGLE-STUDY EVIDENCE. No effect, because A2 fails the rule at 4,096 |
> | A1, 4,096 | RELIABLE (16/16) | 0 of 8 | met whenever A1 is RELIABLE in S0 |
> | A1, 16,384 | UNRELIABLE (6/8) | 2 of 4 | **no failed draw in S0**: every evaluated 8K/16K cell of A1 succeeds under P9-II's criteria (conditions 1–5). This is stricter than RELIABLE, which allows one failed cell |
>
> **Which arms can still qualify.** Items 1 and 2 of §8.5 both need consistency at 2K/4K. So:
>
> - **A0 cannot be the candidate at any scope.** If it meets S0's criteria it is printed by §8.5 item 4 (RELIABLE IN S0; INCONSISTENT ACROSS STUDIES). "(ANSWER-ONLY SUFFICES)" cannot be printed.
> - **A2 cannot be the candidate at any scope.**
> - **A5-D can.** It is the candidate at both sizes if it is RELIABLE under S0's criteria and ADDRESS STABLE at 2K/4K and at 8K/16K. It stands first among the arms that can qualify, because the order is A0, C4, A2, A1.
> - **A1 can.** It is the candidate only if A5-D is not, and then at both sizes only if, besides meeting S0's criteria, it has no failed draw at 8K/16K under P9-II's criteria. With one such failed draw A1 is at most qualified at 4,096 only (§8.7 row 5).
> - Under cut 3 of §10.4 a draw at 8K/16K is its one cell, and the same counts apply.
>
> **The arms that can still be the candidate** are therefore A5-D and A1. This list is computed from §8.5 (b) and P9-II's committed records (an arm is excluded if at 4,096 its P9-II failed draws already exceed two, or P9-II printed LM CAPABILITY REDUCED for it there), is printed in the arm-selection record, and is recomputed by the auditor (G10). §10.3 and §10.4 use it.
>
> **What follows for the annotations (stated; nothing is changed).**
>
> - OVERLOAD (H20-O) can be read only if A5-D is the candidate. If A1 is the candidate it prints NOT RUN — NO TARGET INJECTION, as before.
> - WX (H20-L) and the 65,536 probe (H20-S) run for whichever of A5-D and A1 is the candidate at both sizes.
> - "(LABEL-FREE)" can appear in outcome rows 4–5 only with A5-D.
> - In revision 3, with no fourth arm, only A1 could qualify (`RECHECK_REV3.md` §2). That is the situation the human lead's decision changed.

### C11 — §4 table, new last row

- **Answers:** human decision
- **Reason:** States what S0 now adds for A5-D and what P9-II did not give, with the caveat.

**Inserted after this passage (which is unchanged):**

> | 65,536 at 512 exposures per fact, as a probe | descriptive input for a later study | P9-II's Stage 3 has 32 exposures per fact and is skipped for A2 and A4 |

**New text:**

> | *Revision 4:* A5-D on ten new draws × two seeds at both sizes, under S0's stricter criteria, at two facts per slot and, if it is the candidate, in WX and at 65,536 | the human lead's decision (§3.4); as written in revision 3, S0 could qualify only the supervised arm | P9-II has 8 and 4 draws for A5-D, no read swap, 0.5 facts per slot only, and its Stage 3 probed A0. **A confirmatory replication: the arm was chosen on its P9-II result** |

### C12 — §6, opening line

- **Answers:** human decision (task item 2)
- **Reason:** n_L is now fixed at 4.

**Old:**

> n_L = number of learned core arms = 3 (A0, A1, A2) or 4 (with C4).

**New:**

> n_L = number of learned core arms = 3 (A0, A1, A2) or 4 (with C4). **In revision 4 n_L = 4: C4 = A5-D (§3.4).** The three-arm figures below are kept as revision 3's and no longer occur.

### C13 — §6.1, cell count

- **Answers:** human decision (task item 2)
- **Reason:** Cell counts re-derived for n_L = 4.

**Old:**

> - Cells: 2K/4K 20·n_L + 20; 8K/16K 20·n_L + 20; 8K/4K 20 or 30. **Q1 = 180 cells with three learned arms, 230 with four.**

**New:**

> - Cells: 2K/4K 20·n_L + 20; 8K/16K 20·n_L + 20; 8K/4K 20 or 30. **Q1 = 180 cells with three learned arms, 230 with four.**
> - **Revision 4, n_L = 4:** 2K/4K 80 learned + 20 reference = 100 cells; 8K/16K 80 + 20 = 100; 8K/4K 10 (A0) + 10 (A5-D) + 10 (A6) = 30. **Q1 = 230 cells.** Under cut 3 of §10.4, 8K/16K has 40 + 20 = 60 cells and Q1 has 190.

### C14 — §6.3, totals

- **Answers:** human decision (task item 2)
- **Reason:** Totals for n_L = 4. The 180-cell case cannot occur any more.

**Old:**

> At most 230 + 26 = **256** registered training cells; 180 if there is no fourth arm and no candidate.

**New:**

> At most 230 + 26 = **256** registered training cells; 180 if there is no fourth arm and no candidate. *Revision 4:* with the fourth arm fixed, the count is **256** with a qualified candidate (230 + 20 WX + 6 probe) and **230** without one; the 180-cell case no longer occurs.

### C15 — §6.3, descriptive pooled count

- **Answers:** R7
- **Reason:** The re-check found the descriptive pooled line underdefined: no criteria named, and printed "always" where P9-II has no cells.

**Old:**

> the pooled count of the two studies is printed beside the S0 count, always, as a descriptive line (for reference:

**New:**

> the pooled count of the two studies is printed beside the S0 count, always, as a descriptive line, under P9-II's criteria; NOT AVAILABLE where P9-II has no class for the arm at that size (for reference:

### C16 — §7, namespaces, S1

- **Answers:** N1
- **Reason:** S1's seed-block initialization seeds (ADR-0021 §6) were missing from the list G9 asserts.

**Old:**

> S1 (210001–219999, 2101–2105, 2191–2192, tests 921001–921999)

**New:**

> S1 (210001–219999, 2101–2105, seed-block initialization seeds 2111, 2121, 2112, 2122, 2191–2192, tests 921001–921999)

### C17 — §8.5, consistency rule, when P is read

- **Answers:** R4
- **Reason:** "X advanced" is ambiguous for A0 (ADR-0019 runs A0 at Stage 2 without listing it as advancing). The re-check's wording, confirmed by the lead.

**Old:**

> P is read only if P9-II's outcome is interpreted and, at 16,384, P9-II's Stage 2 is COMPLETE and X advanced.

**New:**

> P is read only if P9-II's outcome is interpreted and, at 16,384, P9-II's Stage 2 is COMPLETE and X has a Stage 2 class at the 4U readout.

### C18 — §8.5, after the preference order

- **Answers:** human decision (task item 3)
- **Reason:** Points to the consequence section. The order itself is untouched.

**Old:**

> **Preference order, fixed (the lead's ruling 3): A0, then C4 (if present), then A2, then A1.**

**New:**

> **Preference order, fixed (the lead's ruling 3): A0, then C4 (if present), then A2, then A1.** (Unchanged in revision 4. C4 is present and is A5-D; what the rule above gives on P9-II's actual records, arm by arm, is in §3.5.)

### C19 — §8.7, row 5

- **Answers:** R3
- **Reason:** E1 added a further reason for which 16,384 can be missing; row 5 did not list it.

**Old:**

> The label says why 16,384 is missing: UNRELIABLE, FAILS, NOT_EVALUATED or not ADDRESS STABLE. NOT_EVALUATED is not read as a failure at 16,384 |

**New:**

> The label says why 16,384 is missing: UNRELIABLE, FAILS, NOT_EVALUATED, not ADDRESS STABLE, or INCONSISTENT ACROSS STUDIES (P9-II \<class\>; pooled \<failed\> of \<n\>). NOT_EVALUATED is not read as a failure at 16,384 |

### C20 — §8.7, row 6

- **Answers:** R10
- **Reason:** Grammar: the last clause could be read as falling under the "where …" clause.

**Old:**

> the added criterion it failed (condition 6 or ADDRESS STABLE) and every arm that met S0's criteria but was INCONSISTENT ACROSS STUDIES, with P9-II's class and the pooled count. |

**New:**

> the added criterion it failed (condition 6 or ADDRESS STABLE); and also every arm that met S0's criteria but was INCONSISTENT ACROSS STUDIES, with P9-II's class and the pooled count. |

### C21 — §8.7, print list, item 1

- **Answers:** human decision (task item 1); R6
- **Reason:** The fixed string, the F1 annotation and the provenance sentence must travel with the arm.

**Old:**

> 1. the arm and its calibrated value;

**New:**

> 1. the arm and its calibrated value; for A5-D, the fourth-arm string of §3.4 with P9-II's F1 annotation and the fixed provenance sentence;

### C22 — §8.7, after the NOT-QUALIFIED paragraph

- **Answers:** human decision (task item 1); R6
- **Reason:** A5-D's classes are printed in every outcome, not only in rows 4–5; the provenance must be printed with them in every case.

**Inserted after this passage (which is unchanged):**

> **The text of ADDRESSING-NOT-QUALIFIED says only what S0 found:** that no tested arm met S0's criteria on S0's draws, with item 6 of the table. It makes no statement about S1 or S2 (§17 item 0).

**New text:**

> **In every outcome row,** wherever a class, label, annotation or hypothesis reading of A5-D is printed, the fourth-arm string of §3.4, P9-II's F1 annotation and the fixed provenance sentence are printed with it, and may not be shortened away. The same string and annotation are printed where the arm-selection record or the carried arm of P9-II is cited.

### C23 — §9.1, table row 1, S1 cell

- **Answers:** R1
- **Reason:** Revision 3's cell (E2) contradicted ADR-0021 §5.6: it let the lane run at 2K/4K and 8K/16K without OVERLOAD-QUALIFIED, where ADR-0021 omits the lane. Lane L is deferred entirely to ADR-0021 §5.6, revision 4.

**Old:**

> | ADDRESSING-QUALIFIED (4,096 AND 16,384) | The candidate exactly as S0 froze it (S0's code hash; P9-II's calibrated value from the arm-selection record; no tuning), as ADR-0021 §5.6 defines the lane: cells 2K/4K and 8K/16K, and 8K/4K only if OVERLOAD-QUALIFIED (never for A1 or A2, which have no 8K/4K cell); each cell run for 4·F updates; no step verdict. Each F-LA cell records S0's probe set, H1/H2 and the read swap, and prints whether it succeeds under S0's cell-success rule (§8.2). Without OVERLOAD-QUALIFIED the lane's 8K/16K-against-8K/4K difference is printed NOT AVAILABLE. A human acceptance is not required by either ADR. | nothing to run: S2 has no slot-level learned addressing and a different student |

**New:**

> | ADDRESSING-QUALIFIED (4,096 AND 16,384) | As ADR-0021 §5.6 (revision 4) defines lane L, items 1, 2 and 4; this ADR states no lane rule of its own | nothing to run: S2 has no slot-level learned addressing and a different student |

### C24 — §9.1, sentence after the table

- **Answers:** R1
- **Reason:** The sentence stated lane rules of this ADR's own. It is replaced by a pointer and by the consequence of ADR-0021's text, marked as a consequence.

**Old:**

> No lane uses a 65,536-slot cell, any load other than 0.5 and (with OVERLOAD-QUALIFIED) 2, or any regime other than 512 exposures per fact. A lane may use a label only after the auditor has recomputed Q1 from raw records.

**New:**

> Which cells the lane runs, when it is omitted and what it prints are ADR-0021 §5.6's (revision 4), not this ADR's. As a consequence of that text, stated here and not a rule of this ADR: the lane exists only when, before S1's freeze, S0 has the outcome of row 1 with Q1 recomputed by the auditor and the candidate is OVERLOAD-QUALIFIED; for candidate A1 or A2 it prints OMITTED — SUPERVISED ARM HAS NO 8K/4K CELL. With P9-II's actual records (§3.5) the lane can therefore exist only if A5-D is the candidate and is OVERLOAD-QUALIFIED.

### C25 — §9.3

- **Answers:** R9
- **Reason:** The section was stale: ADR-0022's corrections were applied at `2ef6a4f`; ADR-0021 is at revision 4, has item 1 and the test range as asked, and wrote its own item 4.

**Old:**

> - **ADR-0021 (revision 3, being written):** §5.6 item 1: "… S0 (ADR-0020) has the outcome **ADDRESSING-QUALIFIED (4,096 AND 16,384)**, with Q1 recomputed by the auditor (ADR-0020 §9.1)." §5.6 item 4, append: "Each F-LA cell records S0's probe set, H1/H2 and the read swap, and prints whether it succeeds under ADR-0020 §8.2." §6.3 unit tests 921001–929999 → **921001–921999** (the lead's choice; this ADR's §7 and G9 already use that range).
> - **ADR-0022 revision 4 — to be applied in ADR-0022 before its approval:** §10 "s_c(S0)" → "s_c(Stage 0)"; the stores named "S1"/"S2" in §6–§11, and "ACQ1 (S1)", renamed (for example "St1"/"St2"), because S0, S1 and S2 are study names; §5.4 "a separately approved supplement" → "a supplement approved by the human lead (ADR-0020 §17 item 3)"; §9 "disjoint … from every seed of P1–P9-II and S1" → "… of P1–P9-II, S0 (200001–209999, 2001–2002, 2091–2092, 920001–920999) and S1".

**New:**

> - **ADR-0021: nothing is owed.** Its revision 4 has §5.6 item 1 as revision 3 of this ADR asked and unit tests 921001–921999. Its §5.6 item 4 was written by its own confirmation (K7: "S0's cell-success rule is applied at all three cells") and differs from the sentence revision 3 of this ADR asked for; this ADR now defers to ADR-0021's text (§9.1, R1), so no edit is owed.
> - **ADR-0022: nothing is owed.** The four corrections revision 3 listed (the Stage 0 score symbol, the store renamed ST1, the supplement approved by the human lead, S0's seeds in the disjointness check) were applied at commit `2ef6a4f`.
> - Revision 4 of this ADR asks no new edit of either sibling. ADR-0021 §5.6 takes "P9-II's calibrated value from the arm-selection record"; for A5-D that is μ = 1.0 (§3.4).

### C26 — §10.2, G10

- **Answers:** R5 (reworded option); human decision
- **Reason:** The second clause could not be done as worded: Part 1 of the script enumerates a modelled space and opens no file. The re-check's reworded option is used. G10 is extended to the two new parts of the arm-selection record.

**Old:**

> **G10** the arm-selection record equals the auditor's independent evaluation of §3.2 on P9-II's committed records, whose hashes are recorded; the auditor's enumeration script `adr-0020-review/c5_rev2_mapping_and_consistency.py` (Part 1) is re-run on P9-II's committed records.

**New:**

> **G10** the mapping part of the arm-selection record equals the auditor's independent evaluation of §3.2 on P9-II's committed records, whose hashes are recorded; Part 1 of the auditor's enumeration script `adr-0020-review/c5_rev2_mapping_and_consistency.py` is re-run and the table cell matching P9-II's committed outcome is cited. The override part equals §3.4 character for character (the human lead's words, the printed string, the F1 annotation, the fixed sentence, μ = 1.0). The list of arms that can still be the candidate equals the auditor's independent evaluation of §8.5 (b) on P9-II's committed records (§3.5).

### C27 — §10.3, the block projection

- **Answers:** R2
- **Reason:** The re-check asked what "most expensive possible candidate" means. Lead's instruction: the maximum over the arms that can still be the candidate.

**Old:**

> A block's projection = measured seconds per update × planned updates (the most expensive possible candidate; A4's annealing at its most expensive measured rate) + measured evaluation, arranged in rounds of six.

**New:**

> A block's projection = measured seconds per update × planned updates (the most expensive possible candidate; A4's annealing at its most expensive measured rate) + measured evaluation, arranged in rounds of six. *Revision 4:* "the most expensive possible candidate" is the most expensive among the arms that can still be the candidate as the arm-selection record lists them (§3.5: A5-D and A1). A4 is not in S0, so its clause has no application.

### C28 — §10.4, unmeasured list

- **Answers:** human decision (task item 2)
- **Reason:** A5-D adds a loss term whose cost the P9-I rates do not contain.

**Old:**

> Unmeasured and not in the table: L_addr's all-key backward, A4's wide read, WX's wider projection,

**New:**

> Unmeasured and not in the table: L_addr's all-key backward, A5-D's L_div (a 128 × 128 query product per update), A4's wide read (not in S0 after §3.4), WX's wider projection,

### C29 — §10.4, after the cap paragraph

- **Answers:** human decision (task item 2)
- **Reason:** Cell counts and the 16-hour arithmetic re-derived for n_L = 4 from the ADR's own rates, with the cut that would apply if the rehearsal exceeds the margin.

**Inserted after this passage (which is unchanged):**

> By the confirmation review's arithmetic the uncut plan absorbs rates up to 1.11 times the slowest P9-I rates, the plan without the probe up to 1.70 times, and Q1 alone up to 1.85 times.

**New text:**

> **Revision 4: the arithmetic for n_L = 4, from the rates above.** The row "Q1, four learned arms" and the "Largest configuration" row were computed in revision 3 for four learned arms. They are now the only configuration; the three-arm row no longer occurs. Re-derived:
>
> | Block | Cells × updates, at the rate of | Summed CPU-hours (fastest / W7 / slowest) | With six workers, hours |
> |---|---|---|---|
> | Q1, 2K/4K | 100 × 8,192, 4,096 slots | 1.82 / 2.23 / 2.55 | |
> | Q1, 8K/16K | 100 × 32,768, 16,384 slots | 11.83 / 12.83 / 17.75 | |
> | Q1, 8K/4K | 30 × 32,768, 4,096 slots | 2.18 / 2.68 / 3.06 | |
> | **Q1 (230 cells)** | | **15.84 / 17.74 / 23.36** | **2.64 / 2.96 / 3.89** |
> | WX (20 cells) | 10 × 8,192 and 10 × 32,768 | 1.37 / 1.51 / 2.03 | 0.23 / 0.25 / 0.34 |
> | 65,536 probe (6 cells, one round) | 6 × 131,072, 65,536 slots | 7.65 / 11.60 / 13.52 | 1.27 / 1.93 / 2.25 |
> | Pipeline check, rehearsal, gates, generation, evaluation, analysis | | | about 0.8 |
> | **Whole plan (256 + 3 cells)** | | **24.86 / 30.85 / 38.91** | **4.94 / 5.94 / 7.28** |
> | Q1 under cut 3 (190 cells) | 8K/16K with 60 cells | 11.10 / 12.61 / 16.26 | 1.85 / 2.10 / 2.71 |
>
> - **Twice the whole plan is 9.88 / 11.88 / 14.57 hours, under the 16-hour cap.** At the slowest rates 1.43 hours (8.9%) remain for everything unmeasured. These are revision 3's figures; adding A5-D by decision does not change them, because revision 3 already budgeted for a fourth arm.
> - **What is lost is the smaller configuration.** With three learned arms the whole plan was 4.37 / 5.29 / 6.44 hours, and the uncut plan absorbed rates up to 1.28 times the slowest P9-I rates. With four it absorbs 1.11 times; the plan without the probe 1.70 times; Q1 alone 1.85 times; Q1 under cut 3 alone 2.66 times (each computed as (16 − 2 × 0.8) / (2 × the block's six-worker hours at the slowest rates)).
> - **Under the headroom rule as worded below (R2).** Before Q1, counting the whole 0.8 hours as still to run: 2 × (0.8 + 3.89) = 9.39 hours at the slowest rates, which holds. After the Q1 gate, at the projected charge of 0.8 + 3.89 = 4.69 hours: 4.69 + 2 × (0.34 + 2.25) = 9.87 hours, which holds. If Q1 had run up to its own cap (2 × 3.89 = 7.79 hours): 0.8 + 7.79 + 5.18 = 13.77 hours, which still holds.
> - **On the projection the twofold rule holds with n_L = 4 and no cut applies.** The projection is not a measurement. The margin of the uncut plan is 11% over the slowest P9-I rates, and the rehearsal is taken under twelve busy processes. If the rehearsed rates exceed that margin, the registered cuts apply as fixed: after the Q1 gate the probe is dropped first (cut 1), then WX (cut 2); before Q1, if Q1 itself does not fit (rates above 1.85 times the slowest), the second seed at 8K/16K is dropped (cut 3); if Q1 under cut 3 does not fit (above 2.66 times), nothing registered is run and the matter returns to the human lead (item 4). No new cut is defined, the fourth arm is not a cut, and the cap is not raised.

### C30 — §10.4, headroom rule

- **Answers:** R2 (reading A, the auditor's sentence)
- **Reason:** The pre-Q1 evaluation was not determined: the start rule counted WX and the probe, whose cuts cannot be applied before Q1. Reading A, with the auditor's sentence. Note for the confirmation: the pre-Q1 check now covers Q1 only, which is less demanding than the literal revision 3 sentence (the whole plan at the most expensive candidate); on the projection both hold.

**Old:**

> **Headroom rule.** After the rehearsal, the registered run starts only if (hours already charged) + 2 × (rehearsed projection of everything still to run, at the most expensive possible candidate) ≤ 16. Each block's own time cap is twice its rehearsed projection; a block that reaches it is stopped and is INCOMPLETE.
>
> After the Q1 gate the rule is evaluated once more, before WX and the probe, with the rehearsed rates of the actual candidate and the hours actually charged. Cuts 1 and 2 are applied then, not before Q1. Cut 3 is decided before Q1.

**New:**

> **Headroom rule.** The rule is: (hours already charged) + 2 × (rehearsed projection of the stages evaluated) ≤ 16. Before Q1 the rule is evaluated on Q1 and the stages before it only. If it does not hold, cut 3 is applied; if it still does not hold, item 4 applies. After the Q1 gate the rule is evaluated on WX and the probe with the actual candidate's rehearsed rates and the hours charged, and cuts 1 and then 2 are applied as needed. **[lead's choice: reading A of the re-check's R2]** Each block's own time cap is twice its rehearsed projection; a block that reaches it is stopped and is INCOMPLETE.
>
> The freeze also records, as information and not as a start condition, the rehearsed projection of WX and of the probe at the most expensive candidate among the arms that can still be the candidate (§3.5), and whether the rule would hold after a Q1 that ran at its projection.

### C31 — §10.4, cut-order heading

- **Answers:** R2
- **Reason:** "Applied in this order" contradicted the timing: cut 3 is the only cut available before Q1. The cuts, their numbering and their content are unchanged.

**Old:**

> **Cut order if the rule does not hold (fixed now, applied in this order; cut 3 recorded in the freeze, cuts 1 and 2 recorded at the Q1 gate):**

**New:**

> **Cuts if the rule does not hold (fixed in revision 3; numbering and content unchanged). Cut 3 is the only cut available before Q1 and is recorded in the freeze. Cuts 1 and then 2 are applied at the Q1 gate and recorded there:**

### C32 — §11

- **Answers:** R10; R8 (lead's ruling); human decision
- **Reason:** The "may start before P9-II's run finishes" clause is moot. The freeze condition gains the lead's ruling on R8. A5-D needs no new arm code.

**Old:**

> Implementation, gates and the pipeline check may start before P9-II's registered run finishes, because A0, A1 and A2 are in every branch and every possible fourth arm exists in P9-II's code; they need P9-II's code committed and its calibration record audited. The freeze cannot happen before P9-II's outcome is recomputed and committed.

**New:**

> Implementation, gates and the pipeline check may start before P9-II's registered run finishes, because A0, A1 and A2 are in every branch and every possible fourth arm exists in P9-II's code; they need P9-II's code committed and its calibration record audited. (Moot since revision 4: P9-II's run has finished and its records are committed.) A5-D is taken from `studies.p9ii` unedited; S0 writes no arm code for it. The freeze cannot happen before P9-II's outcome is recomputed and committed. **The freeze also requires that the human lead's acceptance of the P9-II outcome is recorded (the lead's ruling on R8). It is not recorded at the time of writing. Until it is, S0 may be implemented, set up by reference to P9-II's audited calibration record (S0 has no calibration of its own, §10.1) and rehearsed, but not frozen.**

### C33 — §13 step 1

- **Answers:** task item 5; R10
- **Reason:** Records the re-check and that revision 4's confirmation is pending.

**Old:**

> 1. Confirmation review by the auditor (done on revision 2: READY after E1–E10, applied here). The passages of §19 not pasted verbatim, and any passage changed after this revision, are re-checked by the auditor.

**New:**

> 1. Confirmation review by the auditor (done on revision 2: READY after E1–E10, applied in revision 3). Re-check of revision 3 (done: READY SUBJECT TO R1–R10, applied in revision 4). **Independent confirmation of revision 4: pending.** It covers every passage listed in §21, and any passage changed after this revision.

### C34 — §13 step 6

- **Answers:** human decision
- **Reason:** P9-II's outcome is recomputed and committed; the record now has the override part.

**Old:**

> 6. P9-II's registered outcome recomputed and committed. The mapping script on P9-II's committed records; arm-selection record; audited (G10).

**New:**

> 6. P9-II's registered outcome recomputed and committed (done: `d72b173`, `74f15d1`). The mapping script on P9-II's committed records; the override of §3.4 and the list of §3.5 added; arm-selection record; audited (G10).

### C35 — §13 step 8

- **Answers:** R8 (lead's ruling)
- **Reason:** Freeze condition.

**Old:**

> 8. Generation and G1 of all draws; freeze of specification, code, config, launch scripts, seeds, thresholds, arm-selection record, projections, caps, cuts and data identities.

**New:**

> 8. Generation and G1 of all draws; freeze of specification, code, config, launch scripts, seeds, thresholds, arm-selection record, projections, caps, cuts and data identities. **Not before the human lead's acceptance of the P9-II outcome is recorded (§18 condition 7).**

### C36 — §14, new last bullet

- **Answers:** R8 (lead's ruling)
- **Reason:** Stop rule for the freeze condition.

**Inserted after this passage (which is unchanged):**

> - If P9-II's outcome or calibration record is amended after S0's freeze, S0 stops and returns to the human lead.

**New text:**

> - S0 is not frozen while the human lead's acceptance of the P9-II outcome is not recorded. If the human lead does not accept it, or accepts it with a changed reading, S0 returns to the human lead before any freeze.

### C37 — §15, new bullet after the first

- **Answers:** human decision (task item 1)
- **Reason:** The limit that follows from the provenance of the fourth arm.

**Inserted after this passage (which is unchanged):**

> - Anything about capacity, useful-capacity scaling, locality, transfer or adding facts later.

**New text:**

> - **An unbiased first test of A5-D.** A5-D was added by the human lead's decision after P9-II's outcome was observed, knowing it was RELIABLE there. S0's result for it is a confirmatory replication on new draws. For A5-D the pooled count and CONSISTENT ACROSS STUDIES include the records on which it was chosen and add no independent evidence (§3.4).

### C38 — §16, row 1

- **Answers:** human decision
- **Reason:** The requirements map said the un-carried label-free arm is not re-tested. It now is, by decision.

**Old:**

> A label-free arm that P9-II found RELIABLE at 4,096 but did not carry is not re-tested (§3.3, consequence). |

**New:**

> A label-free arm that P9-II found RELIABLE at 4,096 but did not carry is not re-tested (§3.3, consequence). *Revision 4:* that arm is A5-D, and it is re-tested by the human lead's decision of 2026-11-15, as a confirmatory replication (§3.4). |

### C39 — §17, new item 6

- **Answers:** R8 (lead's ruling)
- **Reason:** The acceptance of the P9-II outcome is the human lead's and now gates S0's freeze.

**Inserted after this passage (which is unchanged):**

> 5. Merge, publication, weight release, ADR-0012.

**New text:**

> 6. **Acceptance of the P9-II outcome.** Pending. S0's freeze requires it to be recorded (§11, §13 step 8, §18 condition 7).

### C40 — §18, approval record

- **Answers:** human decision; R8 (lead's ruling); task item 5
- **Reason:** Records the human lead's decision verbatim with the question it answered, states that the P9-II outcome is not accepted, adds the freeze condition, and keeps the lead's approval PENDING.

**Old:**

> The lead's conditions for using the delegation, as in ADR-0019 §16: (1) the specification review ends with no open blocker or major; (2) the implementation audit is clean before the freeze; (3) the rehearsal shows 2× headroom; (4) nothing changes after the arm-selection record except the cuts of §10.4, applied as that section fixes; (5) no registered seed has been observed; (6) P9-II's outcome is recomputed and committed before the freeze.
>
> Lead's approval: PENDING.

**New:**

> **The human lead's decision on the fourth arm (2026-11-15), verbatim:**
>
> > yes s0 should include the penalty and i approve s2 download
>
> It answered this question, put by the lead: "Add the diversity penalty to S0? As written, S0 cannot test it and can only qualify the supervised arm. I recommend adding it; the alternative is to run S0 as written and test the penalty in P10-I." The second half of the answer concerns ADR-0022 and is not S0's. The decision was made after P9-II's outcome was observed and before any S0 record exists (§3.4). It is a decision about S0's arms. It is not an approval of this specification for execution, and it is **not an acceptance of the P9-II outcome: the human lead has not accepted that outcome at the time of writing.**
>
> The quotations in this section are recorded as relayed to the drafter by the coordinating session, misspellings included. The drafter did not read the chat record itself.
>
> The lead's conditions for using the delegation, as in ADR-0019 §16: (1) the specification review ends with no open blocker or major; (2) the implementation audit is clean before the freeze; (3) the rehearsal shows 2× headroom; (4) nothing changes after the arm-selection record except the cuts of §10.4, applied as that section fixes; (5) no registered seed has been observed; (6) P9-II's outcome is recomputed and committed before the freeze; **(7) the human lead's acceptance of the P9-II outcome is recorded before the freeze (the lead's ruling on R8). Until then S0 may be implemented, set up by reference to P9-II's audited calibration record and rehearsed, but not frozen.**
>
> Independent confirmation of revision 4: PENDING.
>
> Lead's approval: PENDING.

### C41 — §19, list of passages not pasted verbatim, new item 6

- **Answers:** R10
- **Reason:** The re-check found the list incomplete and named the missing passages.

**Inserted after this passage (which is unchanged):**

> §10.4 (the review's headroom multiples; "about 9%" for "about 10%"); §18 condition 4; the B1 and M7 rows of this section; §20 rows 2, 11 and 16.

**New text:**

> 6. Added in revision 4 (R10). The re-check found this list incomplete. Revision 3 also reworded, without listing them here: the header status and revision history; the §9.1 column header; the §9.2 parenthetical; §13 step 1; §18 "Lead's approval: PENDING."; §20 rows 5, 10 and 17; the closing heading. The re-check read all of them and found that none changes a rule or a number.

### C42 — §20 heading

- **Answers:** R10
- **Reason:** Duplicated heading.

**Old:**

> ## 20. The lead's choices in this revision (fixed before any rehearsal)## 20. The lead's choices in this revision (fixed before any rehearsal)

**New:**

> ## 20. The lead's choices in this revision (fixed before any rehearsal)

### C43 — §20 row 1

- **Answers:** human decision
- **Reason:** Row 1 stated the rule for the fourth arm; the arm now comes from the decision.

**Old:**

> | 1 | S0 always runs with A0, A1, A2, A6, A7; at most one fourth arm, P9-II's carried arm if it is A4, A5-C or A5-D; no X2 | §3 |

**New:**

> | 1 | S0 always runs with A0, A1, A2, A6, A7; at most one fourth arm, P9-II's carried arm if it is A4, A5-C or A5-D; no X2. *Revision 4: that rule gave no fourth arm; the fourth arm is A5-D by the human lead's decision, not by a choice of the lead (§3.4)* | §3 |

### C44 — §20 row 11

- **Answers:** R2
- **Reason:** Row 11 described when the cuts are decided.

**Old:**

> | 11 | One cap of 16 charged hours; cut order probe, WX, second seed at 8K/16K; nothing else; cuts 1 and 2 decided after the Q1 gate | §10.4 |

**New:**

> | 11 | One cap of 16 charged hours; cut order probe, WX, second seed at 8K/16K; nothing else; cuts 1 and 2 decided after the Q1 gate. *Revision 4 (R2, reading A):* before Q1 the rule is evaluated on Q1 and the stages before it only, with cut 3 the only cut available then | §10.4 |

### C45 — §20 table, new rows 18–21; new §21

- **Answers:** task item 5
- **Reason:** The lead's choices of this revision are added to §20, and the new §21 maps each change to its source (human decision; R1–R10; N1).

**Inserted after this passage (which is unchanged):**

> | 17 | S1's unit-test seeds 921001–921999 | §7, §9.3 |

**New text:**

> | 18 | *Revision 4.* R4: P9-II's class at 16,384 is read for an arm that has a Stage 2 class at the 4U readout | §8.5 |
> | 19 | *Revision 4.* R8: S0's freeze requires the recorded acceptance of the P9-II outcome by the human lead | §11, §13, §14, §18 |
> | 20 | *Revision 4.* "Most expensive possible candidate" means over the arms that can still be the candidate (§3.5) | §10.3, §10.4 |
> | 21 | *Revision 4.* The human lead's decision is applied as: A5-D takes exactly the place revision 3 defines for a label-free C4 | §3.4 item 6 |
>
> ## 21. Revision 4: each change and its source
>
> Revision 4 was drafted on 2026-11-15, after P9-II's outcome was observed and before any S0 record exists. It changes the fourth arm, by the human lead's decision, and applies the re-check of revision 3 (`adr-0020-review/RECHECK_REV3.md`). **No threshold, criterion, class rule, preference order, consistency rule, seed, draw count, update count or cap is changed.** Of its changes, only the fourth arm was prompted by P9-II's results; that one is the human lead's. The lead's choices among the re-check's options are R2 (reading A), R4, R5 (the reworded option) and R8.
>
> | Source | What revision 4 does | Where |
> |---|---|---|
> | **Human lead's decision, 2026-11-15** ("yes s0 should include the penalty …") | C4 = A5-D with μ = 1.0; the mapping's result (none) is kept as the record and the override is written beside it with its provenance; fixed printed string with P9-II's F1 annotation and a fixed provenance sentence; n_L = 4; Q1 = 230 cells; budget arithmetic re-derived; what the unchanged consistency rule gives per arm | header, §0, §1, §2 H20-D, §3.2, §3.4, §3.5, §4, §6, §6.3, §8.5 (pointer), §8.7 print item 1 and the paragraph after the NOT-QUALIFIED text, §10.2 G10, §10.4, §11, §13 step 6, §15, §16 row 1, §18, §20 rows 1 and 21 |
> | **R1** (major) §9.1 contradicted ADR-0021 §5.6 | lane L deferred entirely to ADR-0021 §5.6, revision 4; this ADR states no lane rule; the consequence for A1 and A5-D is stated as a consequence | §9.1 |
> | **R2** (major) pre-Q1 headroom evaluation not determined | reading A with the auditor's sentence; the cut heading reworded to match; "most expensive possible candidate" defined over the arms that can still be the candidate | §10.3, §10.4, §20 rows 11 and 20 |
> | **R3** §8.7 row 5 lacked the reason added by E1 | "or INCONSISTENT ACROSS STUDIES (P9-II \<class\>; pooled \<failed\> of \<n\>)" appended | §8.7 row 5 |
> | **R4** "X advanced" ambiguous for A0 | "X has a Stage 2 class at the 4U readout" | §8.5, §20 row 18 |
> | **R5** G10's second clause not executable | the reworded option: Part 1 is re-run and the matching table cell is cited | §10.2 |
> | **R6** no fixed fourth-arm string; F1 annotation missing | "FOURTH ARM: NONE — P9-II CARRIED \<arm\> (ALREADY IN S0)" for the mapping's own result; the revision 4 string for the override; F1 annotation verbatim wherever the carried arm or A5-D is cited | §3.2 item 4, §3.4, §8.7 |
> | **R7** descriptive pooled count underdefined | "under P9-II's criteria; NOT AVAILABLE where P9-II has no class for the arm at that size" | §6.3 |
> | **R8** P9-II's human acceptance pending | the lead's ruling: the freeze requires the recorded acceptance; implementation, set-up by reference to P9-II's calibration record and rehearsal may proceed | §11, §13 step 8, §14, §17 item 6, §18 condition 7, §20 row 19 |
> | **R9** §9.3 stale | rewritten: nothing is owed by ADR-0021 (revision 4) or ADR-0022 (`2ef6a4f`) | §9.3 |
> | **R10** editorial | "(this text)" removed from revisions 2 and 3; the evidence line keeps its sentence with the two commits; §11's moot clause marked; duplicated §20 heading removed; §19's list completed; §8.7 row 6 grammar | header, §8.7 row 6, §11, §19, §20 |
> | **N1** S1's seed-block initialization seeds | 2111, 2121, 2112, 2122 listed in S1's namespace | §7 |
>
> **Stated consequences of the re-check that revision 4 does not turn into changes:** the re-check's finding that, as written in revision 3, only A1 could qualify and no label-free qualification was possible is superseded by the human lead's decision and restated for four arms in §3.5.
>
> **Passages of revision 4 that are the drafter's wording and not the auditor's paste text, for the confirmation:** all of §3.4 and §3.5; the revision 4 additions to §0, §2, §4, §6, §6.3, §8.5, §8.7, §15, §16 and §18; G10's two added clauses; §10.3's and §10.4's definition of "most expensive possible candidate"; the informational projection recorded at the freeze (§10.4); the budget table and bullets for n_L = 4; the cut heading; §9.1's consequence sentence; §9.3; §11; §13 steps 1, 6 and 8; §14's new bullet; §17 item 6. Pasted from the re-check without change: the §9.1 cell (R1, with "revision 4" for "revision 3"), the three sentences of R2's edit, R3's clause, R4's clause, R5's reworded clause, R6's first string, R7's clause, R10's row 6 wording.
>
> **Left as revision 3 wrote them although the fourth arm is now fixed** (listed so that the confirmation can check them; none is changed here): G4 and §13 step 5 still cover every arm the mapping could have selected (A4 and A5-C included); §10.3 still rehearses WX and the 32K/64K cell for A0 and A2, which can no longer be the candidate; §10.2's synthetic registries still exercise every row of §3.3; the three-arm rows of §6.1 and §10.4.

### C46 — closing line

- **Answers:** task item 5
- **Reason:** States what the human decision recorded in §18 is and is not; keeps the Astra statement.

**Old:**

> Astra review: NOT_PERFORMED. A Claude review is not an Astra review, and this document is not a human approval.

**New:**

> Astra review: NOT_PERFORMED. A Claude review is not an Astra review, and this document is not a human approval. The human lead's decision recorded in §18 fixes the fourth arm; it does not approve this specification for execution and does not accept the P9-II outcome.

## Open for the lead

Points where the instructions and the ADR did not settle the matter without a choice. Nothing below was chosen by the drafter; where a wording had to be written to make the text complete, it is the most conservative one and is marked.

1. **Gates and rehearsal still cover arms that can no longer be in S0.** G4 and §13 step 5 cover "every arm the mapping can select" (A4 and A5-C and WX of each included). §10.3 rehearses WX and the 32K/64K cell for A0 and A2, which §3.5 shows cannot be the candidate. Left as revision 3 wrote them (more work, no scientific effect). Narrowing them to the arms actually in S0 is a change the instructions did not list.
2. **R2, reading A, is less demanding before Q1 than the literal revision 3 sentence.** Revision 3 required twice the whole remaining plan (WX and probe included, at the most expensive candidate) to fit before the run starts. Reading A requires only Q1 and the stages before it. On the projection both hold (14.57 h against 9.39 h). C30 adds that the freeze records the WX and probe projection "as information and not as a start condition"; that sentence is the drafter's and can be deleted.
3. **The arm-selection record gained a part (d)** and G10 a clause: the list of arms that can still be the candidate, computed from §8.5 (b) on P9-II's records. R2's "over the arms that can still be the candidate" needs some recorded definition of that set; this one is the drafter's wording. The exclusion test used ("P9-II failed draws at 4,096 already exceed two, or LM flag there") is a consequence of §8.5, not a new rule, but it is new text.
4. **H20-D is likely to read "not supported" by construction.** Its reading needs IMPROVES ON A0 at both core sizes, i.e. at least four failed A0 cells at 8K/16K; P9-II had none. The reading is unchanged and the consequence is stated in §2. Whether to leave it so is the lead's.
5. **The preference order now ranks an arm chosen after observation ahead of A1.** The order (A0, C4, A2, A1) is revision 3's and is unchanged, as instructed. §3.4 item 5 states the fact. If the lead or the human lead wants A5-D's qualification to carry a different print than A1's beyond the fixed provenance sentence, that is a new choice.
6. **Scope of the human lead's words.** "s0 should include the penalty" names no cells. §3.4 item 6 and §20 row 21 record the lead's application (2K/4K, 8K/16K, 8K/4K; WX and the probe as candidate), as the task instructed. It is marked as the lead's application, not as the human lead's words.
7. **"Calibrated-by-reference".** S0 has no calibration (§10.1). The text renders the phrase as "set up by reference to P9-II's audited calibration record". If the lead meant something else (for example that the pipeline check may run), §11 and §18 condition 7 need that wording.
8. **What happens to S0 if the human lead does not accept the P9-II outcome, or accepts it with a changed reading.** C36 says S0 returns to the human lead before any freeze. That is the conservative reading of R8's ruling; the ruling itself only says the freeze requires the acceptance.
9. **Fixed provenance sentence.** The task fixed the fourth-arm string and the F1 annotation. The third printed element ("A5-D was added after P9-II's outcome was observed … not an unbiased first test.") is the drafter's wording of the instruction that A5-D's classes "must be read with that stated". The lead may reword or drop it; the string and the annotation stand without it.
10. **§17 item 0 is still unanswered** by the human lead. Unchanged by this revision.
11. **The quotations in §18** are recorded as relayed in the task; the drafter did not read the chat record. §18 says so.
12. **Revision 3 must be archived** as `docs/reviews/p10-design-2026-11-15/revisions/ADR-0020-rev3.md` (from commit `c56b23a`) when revision 4 is copied in; the header says it is "to be kept" there. The drafter could not write into the worktree.
13. **P9-II's measured per-update costs now exist** (its run records) and are closer to S0's arms than the P9-I rates the projection uses. They were not used: the instruction was to re-derive from the ADR's own rates, and the rehearsal decides. Using them in the projection would be a new choice.

Astra review: NOT_PERFORMED. This file and the draft beside it are not a review, not a human approval and not a result.
