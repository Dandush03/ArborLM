# ADR-0020 — P10-S0: Addressing qualification for the P10 programme

- **Status: DESIGN REVISION 4 — CONFIRMED BY THE AUDITOR SUBJECT TO F1–F7 AND TWO EDITS, APPLIED (`adr-0020-review/confirm-rev4/CONFIRM_REV4.md`); approved by the lead for implementation, tests, gates on the rehearsal draw and rehearsal only (§18); nothing implemented or run. Fourth arm A5-D added by the human lead's decision after P9-II's outcome was observed (§3.4). SPEC: PENDING ASTRA REVIEW.**
- **Date:** 2026-11-15 (UTC)
- **Revision history.** Revision 1 (2026-11-15): first draft; reviewed by Opus 5.5 (`adr-0020-review/REVIEW.md`), verdict NOT READY (blockers B1–B2, majors M1–M7, minors m1–m20). Revision 2: applies that review under the lead's rulings. The design changed in substance: S0 now always runs and always contains the answer-only, supervised and staged arms; the runner-up arm, the small scope, the added-facts stage and the 65,536 label are gone; the sample is ten draws by two seeds. Confirmation review of revision 2 by Opus 5.5 (`adr-0020-review/CONFIRM.md`): READY AFTER the text edits E1–E10 (E1 and E2 required, E3–E10 minor, no blocker). Revision 3 (commit `c56b23a`): applies E1–E10 with the auditor's text and the lead's choices on the bracketed points. §19 maps every finding of both reviews to its change; §20 lists the lead's choices. The auditor stated that with E1–E10 applied as written no further review round is needed, and that any passage worded differently needs a re-check; the passages not pasted verbatim are listed at the end of §19. Re-check of revision 3 by Opus 5.5 against E1–E10 and against P9-II's actual records (`adr-0020-review/RECHECK_REV3.md`): READY SUBJECT TO the text edits R1–R10 (R1 and R2 major, R3–R10 minor). **Revision 4 (this text)** does two things and nothing else: it makes A5-D the fourth arm by the human lead's decision of 2026-11-15, taken after P9-II's outcome was observed and before any S0 record exists (§3.4, §18); and it applies R1–R10 and note N1. §21 maps each change to its source. No threshold, criterion, preference order, consistency rule, seed, draw count or cap is changed. Revision 3 is to be kept unchanged as `docs/reviews/p10-design-2026-11-15/revisions/ADR-0020-rev3.md`.
- **Study code:** P10S0. Package `studies/p10s0/`. Config `configs/p10s0_qualification.toml`. Tests `tests/test_p10s0_*.py`. Launch scripts `studies/p10s0/launch/`. This text calls the study "P10-S0" or "S0" and its stages Q1 and Q2; it has no "Stage 0".
- **Origin.** The human lead's P10 direction: "Addressing remains a mandatory prerequisite. Incorporate the most promising P9-II addressing interventions as a qualification gate rather than assuming they have succeeded." and "Phase 1 — Addressing qualification: … Compare the original answer-only method with preregistered addressing supervision and staged optimization. Evaluate across multiple independent data draws and initialization seeds. …"; and the later update that S0, S1 (ADR-0021) and S2 (ADR-0022) are "three parallel, scientifically independent experiments". The direction texts are quoted from the lead's task messages; they are not in the repository.
- **Evidence it rests on.** P9-I (ADR-0017 Part I): COMPLETE — NO_INTERFACE_SELECTED, accepted by the human lead as a registered negative result (ADR-0017 §15.9). P9-II (ADR-0019 revision 4): **not yet run**; this text is written before any P9-II observation and uses no P9-II result (written at `c56b23a`, before P9-II's run records `d72b173`; that sentence is true of revisions 1–3 and of every rule and number they fixed). **Revision 4 is written after P9-II's registered outcome was observed.** P9-II is COMPLETE with the registered outcome ADDRESSING-RELIABLE: A5-D (LABEL-FREE); interface carried forward A0; recomputed by Opus 5.5 (171 comparisons, 0 disagreements); **not accepted by the human lead at the time of writing**. Revision 4 takes one thing from that outcome that revision 3's rules did not already take: the fourth arm, by the human lead's decision (§3.4). No S0 code, pipeline check, rehearsal or record exists. Review diagnostics are exploratory and enter no rule.
- **Roles (study-specific).** Lead: Claude Fable 5.2. Specification review, implementation audit and recomputation: Opus 5.5, in contexts separate from implementation, receiving code and records and not the lead's conclusions. Implementation: Sonnet 5.5. Inventory: Haiku 5.5. The model that actually ran each delegated task is recorded from session metadata. ADR-0012 stays not approved. **Astra review: NOT_PERFORMED.** A Claude review is neither Astra validation nor a human approval.
- **Relation to other work.** P9-II runs and is committed first. S0 imports `studies.p9ii`, `studies.p9i` and `studies.p9` unedited. S1 and S2 do not wait for S0; S0 uses no result of S1 or S2. P1–P9-II code, configs, records and ADRs are not edited.
- **Marking.** Judgment-call numbers are marked **[lead's choice]**. "As ADR-0019 §x" means the definition of ADR-0019 revision 4 applies unchanged.

## 0. What S0 is, in one paragraph

S0 is the registered qualification gate of the P10 programme and an independent replication of P9-II's central comparison. Whatever P9-II shows, S0 trains the answer-only method (A0), addressing supervision (A1) and staged optimization (A2) on ten new draws and two initialization seeds, at 4,096 and at 16,384 slots, with ADR-0019's definitions and P9-II's calibrated values. P9-II's outcome adds at most one further arm, by a mapping fixed here (§3). Applied to P9-II's records, that mapping gives no further arm. The human lead then added A5-D, the label-free diversity penalty, as the fourth arm, after P9-II's outcome was observed and knowing that A5-D was RELIABLE there (§3.4). For A5-D, S0 is therefore a confirmatory replication on new draws, not an unbiased first test. An interface is qualified from S0's own classes by a fixed preference order, and only if it is consistent with P9-II's registered classes (§8.5). P9-II's classes are printed beside S0's as REPLICATES or DOES NOT REPLICATE. S0 tunes nothing.

## 1. What is known, and what is not

Registered (P9-I, one draw, two initialization seeds, 8,192 updates): oracle-query retrieval 0.967–1.000; every learned query interface at chance (0.028–0.044) with 1–6 distinct top-1 slots; the dense window control 0.78–0.80 at 16,384 slots and 0.13 at 65,536.

Exploratory (review diagnostics on other draws; not registered): collapse within 64 updates in every run; an escape that depends on the draw and hardly on the initialization seed; a starved query-projection gradient in the collapsed state.

Not known, the subject of P9-II: which training method, if any, is reliable across draws at 4,096 and 16,384 slots.

Not known, and not answerable by P9-II alone (the subject of S0):

1. Whether P9-II's classes for A0, A1 and A2 (and, by the decision of §3.4, A5-D) are reproduced by a second study with its own draws, and with ten draws where P9-II's Stage 2 has four.
2. Whether a reliable arm also meets stricter fact-specificity criteria (read swap; address stability).
3. Whether a label-free arm keeps addressing at two facts per slot (S1's cell 8K/4K).
4. Whether the qualified recipe depends on being told the record length (W7's seven-position window).
5. As a probe only: what the qualified arm does at 65,536 slots at matched exposure.

## 2. Question and hypotheses

**Is there a learned query–key interface that the P10 programme may rely on: fact-specific, not collapsed, memory-dependent, used without any oracle at inference, and reliable on ten new draws and two initialization seeds at 4,096 and 16,384 slots?**

Each hypothesis can fail. "At both core sizes" means cell types 2K/4K and 8K/16K.

- **H20-A (answer-only is unreliable).** A0 is not RELIABLE at one or both core sizes on S0's draws.
- **H20-B (addressing supervision).** A1 is RELIABLE and IMPROVES ON A0 (§8.4) at both core sizes.
- **H20-C (staged optimization).** A2 is RELIABLE and IMPROVES ON A0 at both core sizes.
- **H20-D (the carried label-free arm; only if a fourth arm exists).** C4 is RELIABLE and IMPROVES ON A0 at both core sizes. *Revision 4:* the fourth arm exists and is A5-D, added by the human lead's decision and not carried by the mapping (§3.4). The hypothesis and its reading are unchanged. Stated before S0 runs: IMPROVES ON A0 needs d ≥ 4 (§8.4), that is at least four cells in which A0 fails; in P9-II A0 succeeded in 8 of 8 cells at 16,384 (4U). If A0 fails fewer than four of its 20 cells at 8K/16K in S0 (cell success as in §8.4), H20-D reads "not supported" whatever A5-D does. That is the registered reading, not a defect to be repaired.
- **H20-R (replication), per arm and size.** The arm's class on S0's draws under P9-II's criteria agrees with its P9-II class (RELIABLE in both, or not RELIABLE in both).
- **H20-Q (qualification).** At least one arm meets S0's criteria and is CONSISTENT ACROSS STUDIES at both core sizes (§8.5).
- **H20-O (overload; read on the qualified candidate, label-free candidates only).** At 8,192 facts in 4,096 slots the candidate keeps at least 0.90 of the oracle reference's accuracy and stays un-collapsed.
- **H20-L (record length; read on WX of the qualified candidate).** The candidate's recipe applied to a query that sees the whole causal context is RELIABLE at both core sizes.
- **H20-S (65,536 probe; read on the qualified candidate; annotation).** The candidate succeeds in 3 of 3 draws at 32,768 facts / 65,536 slots at 512 exposures per fact.

If no arm meets the criteria, the result is a registered ADDRESSING-NOT-QUALIFIED with S0's own data behind it.

## 3. Arms and the mapping from P9-II's registered outcome (fixed now)

### 3.1 Arms present in every branch

| Arm | Definition | Value used |
|---|---|---|
| A0 | answer-only W7, ADR-0019 §4, untuned | — |
| A1 | A0 + address loss, ADR-0019 §4 | λ from P9-II's audited calibration record |
| A2 | staged: address loss only, then answer loss only with AdamW reset, ADR-0019 §4 | U_pre from P9-II's audited calibration record |
| A6 | oracle-query reference (R1) | — |
| A7 | parameter-matched dense window control (D7) | — |

These five are the comparison the human lead asked for. They run whatever P9-II's outcome is, including when P9-II classed A1 or A2 UNRELIABLE or FAILS. S0's classes come from S0's draws only. There is no runner-up arm X2. A1-S is not run in S0; P9-II's negative-control result is printed beside S0's classes for A1 and A2.

### 3.2 The fourth arm C4: what is read from P9-II, in this order

Read only from P9-II's records as recomputed by the auditor and committed:

1. **The calibration record** (λ, U_pre, k_0/N, μ). If no audited P9-II calibration record exists, S0 cannot define A1 or A2 and is **NOT STARTED — NO P9-II CALIBRATION RECORD**; the matter returns to the human lead. This is the only branch in which S0 does not run.
2. **The outcome row** of ADR-0019 §8.6. If it is ENGINEERING_FAIL, INCOMPLETE or NOT_INTERPRETED, there is no fourth arm; S0 runs A0, A1, A2, A6, A7 and prints **FOURTH ARM: NONE — P9-II \<status\>**.
3. **Stage 2's status.** If it is not COMPLETE, there is no fourth arm (no arm is carried forward by ADR-0019 §8.6 without a class at 16,384). A class printed for a Stage 2 that is not COMPLETE is not read.
4. **The interface carried forward** (ADR-0019 §8.6: the first RELIABLE arm at 16,384, 4U readout, in the order A0, A5-C, A5-D, A4, A2, A1, without LM CAPABILITY REDUCED; A1 and A2 skipped where NEGATIVE CONTROL FAILED is printed). If it is A4, A5-C or A5-D, **C4 is that arm** with its calibrated value. If it is A0, A2 or A1, there is no fourth arm and the record prints **FOURTH ARM: NONE — P9-II CARRIED \<arm\> (ALREADY IN S0)**. If no arm is carried, there is no fourth arm, and the reason is printed.

Nothing else is read: no accuracy, no per-draw table, no Stage 3 label. The mapping is evaluated by a committed script; its output, the **arm-selection record**, is part of the freeze. The auditor recomputes it from this text, not from the implementer's script (gate G10). From revision 4 the record has a second part, the override of §3.4, which the script copies from this text and does not compute.

### 3.3 What the rule gives for every P9-II outcome

| P9-II outcome (ADR-0019 §8.6) | Fourth arm C4 |
|---|---|
| ADDRESSING-RELIABLE, carried arm A5-C, A5-D or A4 | that arm |
| ADDRESSING-RELIABLE, carried arm A2 or A1 | none (already in S0) |
| ADDRESSING-RELIABLE, carried arm A0 (RELIABLE at 16,384, not at 4,096) | none (already in S0) |
| ANSWER-ONLY RELIABLE, Stage 2 COMPLETE, carried arm A0 | none |
| ANSWER-ONLY RELIABLE, Stage 2 COMPLETE, A0 not RELIABLE or LM-flagged at 16,384, carried arm A5-C, A5-D or A4 | that arm |
| ANSWER-ONLY RELIABLE, Stage 2 COMPLETE, carried arm A2 or A1, or none | none |
| ANSWER-ONLY RELIABLE, Stage 2 not COMPLETE | none |
| ADDRESSING-RELIABLE AT 4,096 ONLY | none (no label-free arm is carried; A0 may be, if RELIABLE at 16,384 only) |
| ADDRESSING-RELIABLE AT 4,096; 16,384 \<status\> | none (Stage 2 not COMPLETE) |
| ADDRESSING-UNRELIABLE, ADDRESSING-FAILS, INCONCLUSIVE | none |
| ENGINEERING_FAIL / INCOMPLETE / NOT_INTERPRETED | none; printed as in §3.2 item 2 |

In every row S0 runs its full core matrix. P9-II's outcome changes only whether a fourth learned arm is present. No arm is added, removed or reordered after any S0 record exists.

**Consequence, stated:** a label-free arm that P9-II finds RELIABLE at 4,096 but that is not the carried arm (because A0 precedes it, or because it failed or was not run at 16,384) is not in S0. *Revision 4: this case occurred, for A5-D, and the human lead overrode it (§3.4).*

### 3.4 Revision 4: what the rule gave on P9-II's records, and the human lead's override

§3.2 and §3.3 are kept as written in revision 3. They are the record of what the rule fixed before any P9-II observation gives.

**What the rule gave.** Evaluated by the auditor on P9-II's committed records (`RECHECK_REV3.md` §2):

| §3.2 step | P9-II record | Result |
|---|---|---|
| 1 calibration | `results/p9ii-calibration-2026-11-15/calibration.json` (sha256 `ad5d7ee2…`): λ = 1.0, U_pre = 2,048, k_0/N = 0.125, μ = 1.0; audited | exists; S0 runs |
| 2 outcome row | ADDRESSING-RELIABLE, row 4; COMPLETE, interpretable | interpreted |
| 3 Stage 2 | COMPLETE | read |
| 4 carried arm | A0 | **no fourth arm** |

The row of §3.3 that applies is "ADDRESSING-RELIABLE, carried arm A0 (RELIABLE at 16,384, not at 4,096) — none (already in S0)". By §3.2 item 4 the mapping's own result prints **FOURTH ARM: NONE — P9-II CARRIED A0 (ALREADY IN S0)**. This is the case named in §3.3's consequence: A5-D was RELIABLE in P9-II at 4,096 (16 of 16 cells) and at 16,384 (8 of 8), and was not carried because A0 precedes it in ADR-0019's order.

**The override.** The lead put this question to the human lead: "Add the diversity penalty to S0? As written, S0 cannot test it and can only qualify the supervised arm. I recommend adding it; the alternative is to run S0 as written and test the penalty in P10-I." The human lead's answer of 2026-11-15, verbatim (§18):

> yes s0 should include the penalty and i approve s2 download

(The second half concerns ADR-0022 and is not S0's.) By that decision **the fourth arm C4 is A5-D**: answer-only training plus μ·L_div on the batch's normalized, un-centred queries, exactly as ADR-0019 §4 defines it and as `studies.p9ii` implements it, with **μ = 1.0** from P9-II's audited calibration record. The decision overrides one result of the mapping, the entry "no fourth arm". It changes no other rule of this ADR.

**Provenance. To be read with every S0 result for A5-D.**

1. **The decision was made after P9-II's outcome was observed** (run records `d72b173`, recomputation `74f15d1`) **and before any S0 record exists.** No S0 code, pipeline check, rehearsal, gate output or generated draw exists.
2. **The arm was chosen with knowledge of its result.** The human lead and the lead knew that A5-D was RELIABLE in P9-II: 16 of 16 cells at 4,096 and 8 of 8 at 16,384. A5-D is in S0 because of that observed result, not because a rule fixed in advance selected it.
3. **For A5-D, S0 is a confirmatory replication on new draws of an arm selected on its observed result. It is not an unbiased first test.** S0's draws, seeds and panels are new and disjoint from P9-II's (§7), and every threshold was fixed in revision 3 before P9-II ran. What is not independent of P9-II is the choice to test this arm. S0's own class, draw count and per-draw bound for A5-D come from draws not used in its selection and are read as stated; the selection affects the pooled count, the consistency label and the preference order.
4. **The pooled count adds no independent evidence for A5-D.** P9-II's A5-D cells are the cells on which the arm was selected, and none failed. CONSISTENT ACROSS STUDIES (§8.5) therefore holds for A5-D whenever it is RELIABLE in S0 (§3.5). For A5-D that label means "S0 did not contradict the records the arm was chosen on", and no more.
5. **The preference order A0, C4, A2, A1 (§8.5) was fixed in revision 3, before P9-II ran. The occupant of C4 was chosen after.** The order therefore places an arm chosen after observation ahead of A1. The order is not changed; this is stated so that it is not read as a pre-registered preference for A5-D.
6. **Scope.** The human lead's words do not list cells. The lead applies them thus: A5-D takes exactly the place revision 3 defines for a label-free C4 (2K/4K, 8K/16K and 8K/4K in Q1; WX and the 65,536 probe if it is the qualified candidate), and nothing more.
7. P9-II's F1 ruling left "whether a later study uses A0, A5-D or both" to "that study's own specification and approval". This decision is that choice for S0: both.
8. **The human lead has not accepted the P9-II outcome at the time of writing.** The decision above is not such an acceptance and is not recorded as one (§18).

**Printed string (fixed).** Wherever the fourth arm is named, and wherever a class, label or annotation of A5-D is printed (§8.7):

**FOURTH ARM: A5-D — ADDED BY THE HUMAN LEAD'S DECISION OF 2026-11-15; THE REGISTERED MAPPING GAVE NONE (P9-II CARRIED A0)**

followed by P9-II's F1 annotation, verbatim from `results/p9ii-run-2026-11-15/OUTCOME.md`: *A0 is UNRELIABLE at 4,096 (4/16) and at chance at matched updates at 16,384; A5-D is the only label-free arm RELIABLE at both sizes; A5-D was not probed at 65,536 because the rule sent A0 to Stage 3.*

and by the fixed sentence: **"A5-D was added after P9-II's outcome was observed, knowing it was RELIABLE there (16/16 at 4,096; 8/8 at 16,384). For A5-D, S0 is a confirmatory replication on new draws, not an unbiased first test. Its CONSISTENT ACROSS STUDIES label and pooled count include the P9-II records it was chosen on and add no independent evidence; no pooled per-draw bound is printed for A5-D."**

**The arm-selection record** (part of the freeze) therefore holds: (a) the mapping's result as the script and the auditor compute it, with the hashes of the P9-II records read; (b) the override: the human lead's words, the date, the printed string, the F1 annotation and the fixed sentence; (c) the calibrated values used, λ = 1.0, U_pre = 2,048 and μ = 1.0 (k_0/N = 0.125 is not used: A4 is not in S0); (d) the arms that can still be the candidate (§3.5).

**S0's arm set in revision 4** (n_L = 4):

| Arm | Calibrated value | Cell types |
|---|---|---|
| A0 | — | 2K/4K, 8K/16K, 8K/4K |
| A1 | λ = 1.0 | 2K/4K, 8K/16K |
| A2 | U_pre = 2,048 updates at 2,048 facts, 8,192 at 8,192 facts (§5.3) | 2K/4K, 8K/16K |
| C4 = A5-D | μ = 1.0 | 2K/4K, 8K/16K, 8K/4K; WX and the 65,536 probe if it is the candidate |
| A6 | reference | 2K/4K, 8K/16K, 8K/4K; the 65,536 probe |
| A7 | reference | 2K/4K, 8K/16K |

μ = 1.0 was calibrated by P9-II on W7 at 4,096 slots and 0.5 facts per slot. At 8K/4K, in WX and at 65,536 it is an untested transfer (§15). In WX(A5-D), L_div is taken on WX's queries (§5.2: the same loss terms).

### 3.5 What the consistency rule does with P9-II's records (a consequence; no rule is changed)

The rule of §8.5 was fixed in revision 3. Applied to P9-II's committed records it gives the following before S0 runs. A P9-II draw is failed when any of its cells fails (§8.5 (b)); the counts are from `results.json` (`draw_sensitivity.draw_counts`), as read by the re-check and re-read for A5-D by the drafter. P9-II printed LM CAPABILITY REDUCED for no arm at either size.

| Arm, size | P9-II class (cells) | P9-II failed draws | What §8.5 then requires of S0 |
|---|---|---|---|
| A0, 4,096 | UNRELIABLE (4/16) | 6 of 8 | nothing can satisfy it: more than two failed draws already. **INCONSISTENT ACROSS STUDIES whatever S0 observes** |
| A0, 16,384 | RELIABLE (8/8) | 0 of 4 | at most two failed draws of S0's ten (P9-II's criteria). No effect on qualification, because A0 fails the rule at 4,096 |
| A5-D, 4,096 | RELIABLE (16/16) | 0 of 8 | at most two failed draws of S0's ten. **Met whenever A5-D is RELIABLE in S0** (RELIABLE allows at most one failed cell, so at most one failed draw) |
| A5-D, 16,384 | RELIABLE (8/8) | 0 of 4 | the same. **Met whenever A5-D is RELIABLE in S0** |
| A2, 4,096 | FAILS (0/16) | 8 of 8 | **INCONSISTENT ACROSS STUDIES whatever S0 observes** |
| A2, 16,384 | none (A2 has no Stage 2 class) | — | case (a): SINGLE-STUDY EVIDENCE. No effect, because A2 fails the rule at 4,096 |
| A1, 4,096 | RELIABLE (16/16) | 0 of 8 | met whenever A1 is RELIABLE in S0 |
| A1, 16,384 | UNRELIABLE (6/8) | 2 of 4 | **no failed draw in S0**: every evaluated 8K/16K cell of A1 succeeds under P9-II's criteria (conditions 1–5). This is stricter than RELIABLE, which allows one failed cell |

**Which arms can still qualify.** Items 1 and 2 of §8.5 both need consistency at 2K/4K. So:

- **A0 cannot be the candidate at any scope.** If it meets S0's criteria it is printed by §8.5 item 4 (RELIABLE IN S0; INCONSISTENT ACROSS STUDIES). "(ANSWER-ONLY SUFFICES)" cannot be printed.
- **A2 cannot be the candidate at any scope.**
- **A5-D can.** It is the candidate at both sizes if it is RELIABLE under S0's criteria and ADDRESS STABLE at 2K/4K and at 8K/16K. It stands first among the arms that can qualify, because the order is A0, C4, A2, A1.
- **A1 can.** It is the candidate only if A5-D is not, and then at both sizes only if, besides meeting S0's criteria, it has no failed draw at 8K/16K under P9-II's criteria. With one such failed draw A1 is at most qualified at 4,096 only (§8.7 row 5).
- Under cut 3 of §10.4 a draw at 8K/16K is its one cell, and the same counts apply.

**The arms that can still be the candidate** are therefore A5-D and A1. This list is computed from §8.5 (b) and P9-II's committed records (an arm is excluded if at 4,096 its P9-II failed draws already exceed two, or P9-II printed LM CAPABILITY REDUCED for it there), is printed in the arm-selection record, and is recomputed by the auditor (G10). §10.3 and §10.4 use it.

**What follows for the annotations (stated; nothing is changed).**

- OVERLOAD (H20-O) can be read only if A5-D is the candidate. If A1 is the candidate it prints NOT RUN — NO TARGET INJECTION, as before.
- WX (H20-L) and the 65,536 probe (H20-S) run for whichever of A5-D and A1 is the candidate at both sizes.
- "(LABEL-FREE)" can appear in outcome rows 4–5 only with A5-D.
- In revision 3, with no fourth arm, only A1 could qualify (`RECHECK_REV3.md` §2). That is the situation the human lead's decision changed.

## 4. What S0 adds beyond P9-II

| Addition | Why P10 needs it | Why P9-II cannot give it |
|---|---|---|
| The A0 / A1 / A2 comparison on S0's own ten draws × two seeds at both sizes | the gate must not rest on one study; the human lead asked for this comparison in Phase 1 | P9-II is one study; its Stage 2 has four draws (bound 0.47) and only the arms that advanced |
| Classes under P9-II's criteria printed beside P9-II's (REPLICATES / DOES NOT REPLICATE) | says whether P9-II's finding is a property of its draws | — |
| Fact-level dependence in S1's unit (read swap, a_use) and address stability as criteria | S1's rules use usefully retained facts | P9-II scores accuracy and value permutation; stability is an annotation there |
| Two facts per slot, cell 8K/4K, label-free arms | S1's lane step starts from 8K/4K | every P9-II cell has 0.5 facts per slot |
| WX, a query not told the record length | every W7 result carries "told the record length" | W7 only |
| 65,536 at 512 exposures per fact, as a probe | descriptive input for a later study | P9-II's Stage 3 has 32 exposures per fact and is skipped for A2 and A4 |
| *Revision 4:* A5-D on ten new draws × two seeds at both sizes, under S0's stricter criteria, at two facts per slot and, if it is the candidate, in WX and at 65,536 | the human lead's decision (§3.4); as written in revision 3, S0 could qualify only the supervised arm | P9-II has 8 and 4 draws for A5-D, no read swap, 0.5 facts per slot only, and its Stage 3 probed A0. **A confirmatory replication: the arm was chosen on its P9-II result** |

## 5. System, WX and the training regime

### 5.1 Common

As ADR-0019 §3 and §4: frozen 27,392-parameter backbone, the P9-I task, flat memory (cosine keys, key width 16, top-8, temperature 0.2) read and added at answer sites only, alphabet-only loss, one AdamW at 0.003, clip 1.0, batch of 16 contexts = 128 answer sites. No backbone parameter is trained. No fact identity is an input of any learned arm at inference (gate G6). All arms are exactly ADR-0019 §4, from `studies.p9ii`.

**No target injection at 8K/4K.** ADR-0019 defines the target slot s(f) as an injection of the trained facts into the slots. With 8,192 facts and 4,096 slots none exists. **A1 and A2 are not run at 8K/4K.** For them OVERLOAD prints **NOT RUN — NO TARGET INJECTION**. Only A0, a label-free C4 and A6 run there.

### 5.2 WX, the full-context query

For an answer site at position t (0 ≤ t ≤ 63) let h̃_j = h_j for j ≥ 0 and the zero vector for j < 0, h being the frozen block-0 output (width 32). Then z = W_X · [h̃_{t−63}; …; h̃_t], W_X ∈ R^{16×2,048}, q = z / ‖z‖.

- 64 is the backbone's context length, not a property of the task. WX is not told that a record has eight bytes. W7 is the special case in which all but the last 224 columns of W_X are zero.
- W_X is drawn by W7's initializer at fan-in 2,048 **[lead's choice]**; no column is copied. WX has 32,768 query parameters against W7's 3,584.
- WX(X) is trained exactly as arm X: same loss terms, calibrated value, schedule and target slots.
- **WX can only inform in one direction.** At initialization the last seven positions carry about 224 / 2,048 ≈ 11% of the query variance, and under AdamW the per-step change of z is about nine times W7's at the same, un-retuned learning rate. A failure of WX is therefore **not evidence that the record length is required**: H20-L can be supported or "not supported", never contradicted.
- **What WX is still told.** The memory reads only at positions 8r + 6. Removing that needs reads and a loss at every position, which changes the objective of every arm (rungs R0 against R0a of ADR-0017 §5.3). It is out of scope. **No S0 label says that an interface finds where to read.**
- Descriptive only, no training, no rule: for the qualified candidate, the area under the ROC curve of max_s a_s for separating answer sites from the other 55 positions of Panel A contexts.

### 5.3 Training regime

With U = 8,192: 2K/4K runs U updates; 8K/4K and 8K/16K run 4U = 32,768 and are read at U and at 4U as ADR-0019 §5 defines (the 4U readout decides the class; the U readout is ALSO AT MATCHED UPDATES for constant-objective arms and MID-SCHEDULE for A2 and A4, and enters no rule); 32K/64K runs 16U = 131,072. Every class readout is therefore at 512 exposures per fact. Schedules are in exposures per fact as ADR-0019 §5: A2's U_pre and A4's T_A are multiplied by F / 2,048.

## 6. Matrix

Cell type "8K/4K" = 8,192 facts in 4,096 slots. Init seeds 2001 and 2002. n_L = number of learned core arms = 3 (A0, A1, A2) or 4 (with C4). **In revision 4 n_L = 4: C4 = A5-D (§3.4).** The three-arm figures below are kept as revision 3's and no longer occur.

### 6.1 Q1 — core (ten registered draws, 1–10)

| Cell type | Load | Updates | Learned arms | Draws × init seeds | References (seed 2001) |
|---|---|---|---|---|---|
| 2K/4K | 0.5 | 8,192 | A0, A1, A2, C4 | 10 × 2 = 20 cells per arm | A6, A7 × 10 |
| 8K/16K | 0.5 | 32,768 | A0, A1, A2, C4 | 10 × 2 = 20 cells per arm | A6, A7 × 10 |
| 8K/4K | 2 | 32,768 | A0, C4 (label-free by construction) | 10 × 1 | A6 × 10 |

- In 8K/4K draw d uses init seed 2001 for odd d and 2002 for even d.
- **References are draw-paired, not seed-paired:** A6 and A7 use seed 2001 on every draw.
- Within a draw, 8K/4K and 8K/16K share facts, streams and panels; the 2,048-fact set is generated independently (§7). Within a draw and seed every arm sees the same data, batch order and initialization of shared parameters.
- Cells: 2K/4K 20·n_L + 20; 8K/16K 20·n_L + 20; 8K/4K 20 or 30. **Q1 = 180 cells with three learned arms, 230 with four.**
- **Revision 4, n_L = 4:** 2K/4K 80 learned + 20 reference = 100 cells; 8K/16K 80 + 20 = 100; 8K/4K 10 (A0) + 10 (A5-D) + 10 (A6) = 30. **Q1 = 230 cells.** Under cut 3 of §10.4, 8K/16K has 40 + 20 = 60 cells and Q1 has 190.

### 6.2 Q2 — annotations for the qualified candidate (after the Q1 gate)

| Block | Cell type | Updates | Arms | Draws × seeds | Cells |
|---|---|---|---|---|---|
| WX | 2K/4K and 8K/16K | 8,192 and 32,768 | WX(candidate) | draws 1–10 × 1 (alternating seeds as 8K/4K) | 20 |
| 65,536 probe | 32K/64K | 131,072 | candidate, A6 | three new draws 11–13 × seed 2001 | 6 |

- WX reuses the Q1 draws, where A6 and A7 already exist. The candidate was chosen on those draws by the fixed rule of §8.5; WX is an annotation and the reuse is stated with it.
- Q2 runs only if a candidate is qualified at both core sizes. Otherwise both blocks print NOT RUN — NO CANDIDATE.

### 6.3 Totals and bounds

At most 230 + 26 = **256** registered training cells; 180 if there is no fourth arm and no candidate. *Revision 4:* with the fourth arm fixed, the count is **256** with a qualified candidate (230 + 20 WX + 6 probe) and **230** without one; the 180-cell case no longer occurs. Pipeline check: 3 cells (§10.1). Two reserve draws (§7).

One-sided 95% Clopper–Pearson lower bounds on the per-draw success probability. **In the two-seed cell types a draw succeeds only when both of its cells succeed; every printed bound uses that count.**

| Draws succeeding | Bound |
|---|---|
| 10 of 10 | 0.741 |
| 9 of 10 (the least that RELIABLE guarantees, §8.3) | 0.606 |
| 9 of 9 (one draw NOT_EVALUATED) | 0.717 |
| 8 of 9 | 0.571 |
| 8 of 10 (not RELIABLE; for reference) | 0.493 |
| 3 of 3 (65,536 probe) | 0.368 |
| 16 of 18 / 12 of 14 (pooled, the consistency threshold) | 0.690 / 0.615 |

S0 states these bounds and claims no more. Where S0's protocol at a cell type is identical to P9-II's (2K/4K at U = Stage 1; 8K/16K at 4U = Stage 2; identity checked by G4), the pooled count of the two studies is printed beside the S0 count, always, as a descriptive line, under P9-II's criteria; NOT AVAILABLE where P9-II has no class for the arm at that size (for reference: 18 of 18 gives 0.847, 17 of 18 gives 0.762, 14 of 14 gives 0.807, 13 of 14 gives 0.703). The pooled count enters exactly one rule, the consistency rule of §8.5, and there it is counted in failed draws over the evaluated draws of both studies.

## 7. Seeds and data identities

- **Registered data seed sets** `p10s0-draw-1` … `p10s0-draw-13`, bases 200001 + 100·(d − 1). Draws 1–10: Q1 and WX. Draws 11–13: the 65,536 probe. **Reserve sets** `p10s0-reserve-1`, `-2`: bases 201301, 201401, each holding all three fact sets. Replacement as ADR-0019 §9.
- Layout in a set (P9-I convention inside each block of twenty: fourteen data seeds, three Panel A null seeds, three Panel B null seeds): base + 0…19 the 2,048-fact set; base + 20…39 the 8,192-fact set; base + 60…79 the 32,768-fact set. Target-slot seeds, with j = init seed − 2001: base + 40 + j (2,048 facts), base + 44 + j (8,192 facts, 16,384 slots), base + 48 + j (32,768 facts). WX uses the target slots of its cell. Read-swap derangement seeds base + 50, + 51, + 52 for the three fact sets.
- **Init seeds** 2001, 2002. **Pipeline check:** data base 209001, init 2091. **Rehearsal:** data base 209101, init 2092. **Unit tests:** 920001–920999.
- **Bounded, disjoint namespaces (gate G9).** P9 (170001–171343, 179001–179933, 1701–1702); P9-I (182001–182020, 180101–181900, 1791–1792, 1801–1802, 900001–900233); review diagnostics (500001–500004); P9-II (190001–191599, 1891, 1901–1902, tests 910001–919999); **S0 (200001–209999, init 2001–2002, check and rehearsal init 2091–2092, tests 920001–920999)**; S1 (210001–219999, 2101–2105, seed-block initialization seeds 2111, 2121, 2112, 2122, 2191–2192, tests 921001–921999); S2 (220001–228999, tests 229001–229999); the seeds of P1–P8 read from their configs. G9 asserts these in code and reads P9-II's actual test seeds from its committed code at S0's freeze, asserting them inside 910001–919999.
- The specification auditor searched `studies/`, `configs/`, `src/`, `tests/`, `results/`, `supplements/`, `docs/`, `templates/`, `prompts/` and `experiments/` (14,155 text files, with a positive control) and found S0's ranges unused (review m19).
- Within a draw, training contexts, the calibration stream, Panels A and B, H1, H2 and the unseen-fact control are disjoint as ADR-0017 §4. All thirteen registered draws and both reserves are generated, hashed and G1-checked at the freeze, before any model sees them. No P9-II draw, panel or snapshot is used by S0.

## 8. Measurements, criteria and labels

### 8.1 Recorded

- During training, every 64 updates: as ADR-0019 §8.1, with the same probe set (both calibration-stream occurrences of the first 256 trained facts) and the same slot-based definitions of collapse onset, escape, "separated" and the four categories.
- At the readout: as ADR-0019 §8.2, including LM capability and cost. No efficiency claim is made from any cost figure.
- **Read swap and a_use.** π is a seeded derangement of the cell's facts with answer(π(f)) ≠ answer(f). The swapped prediction for fact f on a panel is the model's prediction at f's answer site when the memory's read vector there is replaced by the read vector the model computes at π(f)'s answer site in π(f)'s own panel context. The swapped prediction counts as the fact's answer if that answer is among the arg-max symbols (ties on the conservative side). **a_use** = share of facts answered correctly whose swapped prediction is not their answer (ADR-0021 §7.1). Reported with i = 5 − h₂(e) − e·log₂31 bits per fact, e = 1 − a_use.

### 8.2 Cell success

A cell of a learned arm **succeeds under P9-II's criteria** if conditions 1–5 of ADR-0019 §8.3 hold. It **succeeds under S0's criteria** if in addition:

- **Condition 6 (fact-specific dependence):** a_use ≥ 0.95 × accuracy on Panels A and B **[lead's choice; the DEP number of ADR-0021]**.

In cell type 8K/4K, condition 1 reads: accuracy ≥ 0.90 × A6's on the same draw, and A6 ≥ 0.50 **[lead's choice]**, else the draw is NOT_EVALUATED there. Whether A6 reaches 0.50 at two facts per slot is unknown; if it does not on two or more draws, OVERLOAD is NOT_EVALUATED, and nothing is tuned to avoid that.

As numbers, a success under S0's criteria means: accuracy at least 0.90 of the oracle reference; value permutation and memory-off inside the chance interval; at least 128 distinct top-1 slots on the 512 probe sites and no slot top-1 for more than 10 of them; held-out templates at 0.90 of Panel A; no leakage; at least 0.95 of the correct answers lost when the read is swapped.

### 8.3 Arm class per cell type (first match wins)

| Order | Class | 20-cell types (2K/4K, 8K/16K) | 10-cell types (8K/4K, WX) | 65,536 probe (3 cells) |
|---|---|---|---|---|
| 1 | NOT_EVALUATED | more than one draw NOT_EVALUATED | more than one draw NOT_EVALUATED | any draw NOT_EVALUATED |
| 2 | RELIABLE | at most one failed cell of the evaluated cells, no draw with both seeds failed, no LM CAPABILITY REDUCED | at most one failed cell, no LM CAPABILITY REDUCED | no class; counts only |
| 3 | UNRELIABLE | at least 5 successes | at least 3 successes | — |
| 4 | FAILS | otherwise | otherwise | — |

UNRELIABLE and FAILS enter no rule; qualification, replication and OVERLOAD use RELIABLE against not RELIABLE only.

- All numbers in the table **[lead's choice]**; the confirmation review checked them (ruling 6). "No draw with both seeds failed" is implied by "at most one failed cell" and is written out because the bound of §6.3 depends on it.
- LM CAPABILITY REDUCED as ADR-0019 §8.4 (b): a cell is flagged if its relative next-byte loss rise exceeds A6's on the same draw and cell type by more than 0.05; an arm flagged in more than one cell of a cell type carries the flag there and is printed **UNRELIABLE (LM CAPABILITY REDUCED)** when the count of row 2 is met.
- **Two classes are printed for every learned arm and cell type:** the class under S0's criteria and the **class under P9-II's criteria** (conditions 1–5 and the same count rule, on S0's cells). Qualification uses S0's criteria. Replication uses P9-II's.

### 8.4 Comparisons and annotations (enter no class)

- **Paired comparison with A0**, per core cell type, as ADR-0019 §8.4: d(X) = (cells where X succeeds and A0 fails) − (cells where A0 succeeds and X fails) over the 20 pairs; IMPROVES ON A0 if d ≥ 4 and X has more successes; HARMS if d ≤ −4; otherwise NOT DISTINGUISHED. The exact sign-test p-value is printed. d(A2 against A1) is printed, descriptively. Cell success in d(X) is success under S0's criteria (§8.2), the criteria of the class that H20-B, H20-C and H20-D read; d(X) under P9-II's criteria is printed beside it and enters no reading. **[lead's choice, made in revision 4 after P9-II's outcome was observed; P9-II recorded no read swap]**
- **Replication of P9-II**, per arm and size, from the class under P9-II's criteria: **REPLICATES P9-II** if the arm is RELIABLE in both studies or not RELIABLE in both; **DOES NOT REPLICATE P9-II** if RELIABLE in exactly one; **NOT COMPARABLE** if either is NOT_EVALUATED or P9-II has no class for the arm at that size (it did not advance, Stage 2 not COMPLETE, P9-II not interpreted). P9-II's class and S0's are printed side by side.
- **ADDRESS STABLE**, per cell type: the median over cells of the share of facts with the same top-1 slot on Panels A and B ≥ 0.80 (ADR-0019's number). **ADDRESS RECALL** (A1, A2), **DENSE COMPARISON**, **sustained success**: as ADR-0019 §8.4 and §8.7.
- **COLLAPSE-FREE: k of n** counted cells never had a collapse onset. Printed beside the class so that "collapsed and recovered" is not read as "never collapsed".
- **P9-II NEGATIVE CONTROL**: P9-II's printed result at each size, repeated beside A1's and A2's classes.

### 8.5 The Q1 gate: the qualified candidate

An arm **meets the criteria at a core size** if it is RELIABLE there under S0's criteria and ADDRESS STABLE there. The mapping of the human lead's criteria:

| Criterion | Number |
|---|---|
| Fact-specific retrieval | conditions 1 and 6; ADDRESS STABLE ≥ 0.80; held-out templates ≥ 0.90 (condition 4) |
| Resistance to query collapse | condition 3 at the readout in every counted cell; COLLAPSE-FREE printed |
| Strong memory dependence | condition 2 (value permutation and memory-off inside the chance interval) and condition 6 |
| No oracle at inference | gate G6: token-only forward; logits bit-identical under permutation of target slots, oracle codes and fact tables |
| Multiple draws and initialization seeds | the class rule of §8.3 on ten draws × two seeds, with the per-draw bound |
| LM capability | G5 for the backbone; the relative criterion against A6 for the system |

**Consistency with P9-II (fixed now; the lead's ruling 1).** For a learned arm X and a core size, let P be X's class at that size in P9-II's registered record: at 4,096 the Stage 1 class, at 16,384 the Stage 2 class at the 4U readout. P is read only if P9-II's outcome is interpreted and, at 16,384, P9-II's Stage 2 is COMPLETE and X has a Stage 2 class at the 4U readout. X is **CONSISTENT ACROSS STUDIES** at that size if:

(a) P is not available or is NOT_EVALUATED. The label then says **SINGLE-STUDY EVIDENCE** at that size. Or:

(b) P9-II did not print LM CAPABILITY REDUCED for X at that size, **and** at most two **[lead's choice]** draws failed among the evaluated draws of both studies. In both studies a draw counts as failed when any of its evaluated cells fails under P9-II's criteria (conditions 1–5 of ADR-0019 §8.3). With every draw evaluated this is at least 16 of 18 draws at 4,096 and 12 of 14 at 16,384. It always holds when X is RELIABLE in both studies.

Otherwise X is **INCONSISTENT ACROSS STUDIES** at that size. P9-II's classes for A1 and A2 are read as classes even where P9-II printed NEGATIVE CONTROL FAILED; that result is printed in the label (§8.7 item 5).

**Preference order, fixed (the lead's ruling 3): A0, then C4 (if present), then A2, then A1.** (Unchanged in revision 4. C4 is present and is A5-D; what the rule above gives on P9-II's actual records, arm by arm, is in §3.5.)

1. The candidate is the first arm in the order that meets the criteria **and** is CONSISTENT ACROSS STUDIES at 2K/4K and at 8K/16K. Its scope is 4,096 and 16,384.
2. If there is none, the first arm in the order that meets the criteria and is CONSISTENT ACROSS STUDIES at 2K/4K is printed as qualified at 4,096 only. Q2 is not run.
3. If there is none, no arm is qualified.
4. An arm that meets the criteria at a size but is INCONSISTENT ACROSS STUDIES there is printed **RELIABLE IN S0; INCONSISTENT ACROSS STUDIES (P9-II \<class\>; pooled \<failed\> of \<n\> draws failed)**. It is not qualified at that size, and the rule moves to the next arm.
5. When A0 is the candidate the label reads **(ANSWER-ONLY SUFFICES)**. Whatever the candidate, every later arm in the order that would also qualify is printed as **ALSO QUALIFIES: \<arm\> (\<scope\>)**. SINGLE-STUDY EVIDENCE is printed for each size where (a) applied.

No other use of S0 data selects an arm.

### 8.6 Annotations on the qualified candidate

- **OVERLOAD-QUALIFIED** if the candidate is RELIABLE at 8K/4K; **OVERLOAD NOT QUALIFIED** if UNRELIABLE or FAILS; **OVERLOAD NOT_EVALUATED**; **OVERLOAD NOT RUN — NO TARGET INJECTION** if the candidate is A1 or A2.
- **RECORD-LENGTH-FREE VARIANT:** PASSES (WX RELIABLE and ADDRESS STABLE at 2K/4K and 8K/16K) / PASSES AT 4,096 ONLY / DOES NOT PASS (not evidence that the record length is required) / NOT_EVALUATED / NOT RUN. WX is never the qualified interface.
- **AT 65,536 (probe; not a qualification; S0 only; three draws; one initialization seed): k of 3 succeed**, with "per-draw bound 0.368" when k = 3, or the block's status. It is never part of the label and permits nothing in §9.

### 8.7 Study outcome (first match wins)

| Order | Outcome | Rule |
|---|---|---|
| 1 | **NOT STARTED — NO P9-II CALIBRATION RECORD** | §3.2 item 1 |
| 2 | **ENGINEERING_FAIL / INCOMPLETE** | a failed gate; a difference between frozen and running code, config, launch scripts, arm-selection record or data identities; a Q1 cell without a record. No scientific label is derived and no denominator is reduced |
| 3 | **INCONCLUSIVE** | cell type 2K/4K is NOT_EVALUATED (more than one draw where A6 < 0.90) |
| 4 | **ADDRESSING-QUALIFIED (4,096 AND 16,384)** | §8.5 item 1 (criteria met and CONSISTENT ACROSS STUDIES at both core sizes) |
| 5 | **ADDRESSING-QUALIFIED AT 4,096 ONLY** | §8.5 item 2. The label says why 16,384 is missing: UNRELIABLE, FAILS, NOT_EVALUATED, not ADDRESS STABLE, or INCONSISTENT ACROSS STUDIES (P9-II \<class\>; pooled \<failed\> of \<n\>). NOT_EVALUATED is not read as a failure at 16,384 |
| 6 | **ADDRESSING-NOT-QUALIFIED** | §8.5 item 3. Printed as "NOT QUALIFIED IN S0" with, for every arm and size, the S0 class, the class under P9-II's criteria, the replication label and, where an arm is RELIABLE under P9-II's criteria but not under S0's, the added criterion it failed (condition 6 or ADDRESS STABLE); and also every arm that met S0's criteria but was INCONSISTENT ACROSS STUDIES, with P9-II's class and the pooled count. |

Each of Q2's blocks has a status: COMPLETE, NOT RUN — NO CANDIDATE, NOT RUN — BUDGET, NOT RUN — MEMORY, INCOMPLETE, NOT_EVALUATED. Q1's outcome is decided from Q1 alone and stands whatever happens in Q2.

**The outcome of rows 4–5 is printed with, and may not be shortened to omit:**

1. the arm and its calibrated value; for A5-D, the fourth-arm string of §3.4 with P9-II's F1 annotation and the fixed provenance sentence;
2. **(LABEL-FREE)** for A0, A4, A5-C, A5-D, or **(ADDRESS-SUPERVISED IN TRAINING — needs a target slot per fact)** for A1, A2;
3. the regime: 512 exposures per fact (U at 2,048 facts, 4U at 8,192), schedules in exposures per fact, 0.5 facts per slot;
4. per size: S0's draw count and per-draw bound; P9-II's class; REPLICATES / DOES NOT REPLICATE / NOT COMPARABLE; the pooled count; CONSISTENT ACROSS STUDIES or SINGLE-STUDY EVIDENCE;
5. the annotations of §8.6 and §8.4, including P9-II's negative-control result for a supervised candidate;
6. the classes of the other arms and their paired labels against A0;
7. the fixed sentences: **"W7 is told the record length. The memory is told the answer position. Synthetic fixed-length records; one frozen 27,392-parameter backbone."**

**The text of ADDRESSING-NOT-QUALIFIED says only what S0 found:** that no tested arm met S0's criteria on S0's draws, with item 6 of the table. It makes no statement about S1 or S2 (§17 item 0).

**In every outcome row,** wherever a class, label, annotation or hypothesis reading of A5-D is printed, the fourth-arm string of §3.4, P9-II's F1 annotation and the fixed provenance sentence are printed with it, and may not be shortened away. The same string and annotation are printed where the arm-selection record or the carried arm of P9-II is cited.

**Hypothesis readings, fixed now.** H20-A: supported if A0 is not RELIABLE (S0's criteria) at 2K/4K or at 8K/16K. H20-B, C, D: supported if the arm is RELIABLE and IMPROVES ON A0 at both core sizes; contradicted if it HARMS at either; not supported otherwise. H20-R, per arm and size: supported if REPLICATES; not supported if DOES NOT REPLICATE; not read if NOT COMPARABLE. Qualification is reported separately from replication. H20-Q: supported under row 4. H20-O, H20-L and H20-S are read on the qualified candidate: H20-O supported if OVERLOAD-QUALIFIED, not tested if NOT RUN; H20-L supported if the variant PASSES, otherwise not supported, never contradicted; H20-S supported as an annotation if 3 of 3, contradicted if 0 of 3 with A6 evaluated, otherwise not supported.

## 9. What the sibling studies may use

### 9.1 Per label

| S0 outcome | S1 learned-address lane (ADR-0021 §5.6, which cites this ADR's labels) | S2 (ADR-0022) |
|---|---|---|
| ADDRESSING-QUALIFIED (4,096 AND 16,384) | As ADR-0021 §5.6 (revision 4) defines lane L, items 1, 2 and 4; this ADR states no lane rule of its own | nothing to run: S2 has no slot-level learned addressing and a different student |
| ADDRESSING-QUALIFIED AT 4,096 ONLY | no lane | none |
| ADDRESSING-NOT-QUALIFIED | no lane | none |
| INCONCLUSIVE, ENGINEERING_FAIL, INCOMPLETE, NOT STARTED | no lane | none |

Which cells the lane runs, when it is omitted and what it prints are ADR-0021 §5.6's (revision 4), not this ADR's. As a consequence of that text, stated here and not a rule of this ADR: the lane exists only when, before S1's freeze, S0 has the outcome ADDRESSING-QUALIFIED (4,096 AND 16,384) (§8.7 row 4) with Q1 recomputed by the auditor from raw records and the candidate is OVERLOAD-QUALIFIED; for candidate A1 or A2 it prints OMITTED — SUPERVISED ARM HAS NO 8K/4K CELL. With P9-II's actual records (§3.5) the lane can therefore exist only if A5-D is the candidate and is OVERLOAD-QUALIFIED.

### 9.2 Timing, stated plainly

**A qualification recorded after a sibling study's freeze changes nothing in that study.** S0 can freeze only after P9-II's outcome is recomputed and committed, and S0's Q1 is the longest part of its run. S1 and S2 do not wait. **In the expected timeline S1 freezes before S0's Q1 label is recomputed, so S1's learned-address lane will be omitted** (ADR-0021 §5.6 omits it when nothing is qualified at its freeze). "Learned addressing evaluated separately if qualified" is then met only by a later study: the integrated study or P10-I. **Both need the human lead's review**; the integrated study is proposed, not executed automatically.

### 9.3 Corrections owed by the sibling drafts (this text cannot make them)

- **ADR-0021: nothing is owed.** Its revision 4 has §5.6 item 1 as revision 3 of this ADR asked and unit tests 921001–921999. Its §5.6 item 4 was written by its own confirmation (K7: "S0's cell-success rule is applied at all three cells") and differs from the sentence revision 3 of this ADR asked for; this ADR now defers to ADR-0021's text (§9.1, R1), so no edit is owed.
- **ADR-0022: nothing is owed.** The four corrections revision 3 listed (the Stage 0 score symbol, the store renamed ST1, the supplement approved by the human lead, S0's seeds in the disjointness check) were applied at commit `2ef6a4f`.
- Revision 4 of this ADR asks no new edit of either sibling. ADR-0021 §5.6 takes "P9-II's calibrated value from the arm-selection record"; for A5-D that is μ = 1.0 (§3.4).
- ADR-0019 §7's "910001 upward" is read as 910001–919999 and asserted by G9.

## 10. Gates, pipeline check, rehearsal, resources

### 10.1 Pipeline check (no calibration exists)

S0 has no tuned quantity. Before the freeze, on the pipeline-check draw only: A0, A6 and A7 at 2K/4K, one cell each (3 cells), to confirm that the pipeline produces records of the registered shape. Their accuracies are not results and select nothing.

### 10.2 Gates

- **G1** as ADR-0019 §9, per draw and fact set, with its replacement rule. **G2** chance interval per draw and fact count. **G5**, **G6** as ADR-0019 §9, G6 extended to WX.
- **G4** as ADR-0019 §9, for **every arm in S0's arm set** (§3.4: A0, A1, A2, A5-D), A6, A7, and WX of each arm that can still be the candidate (§3.5: A5-D, A1), plus:
  - each arm's forward and one training step in S0 are bit-identical to `studies.p9ii`'s on a shared rehearsal seed;
  - WX with W_X zero outside its last 224 columns, and equal to a W7 projection there, gives W7's query bit for bit; the zero padding is as §5.2;
  - schedules at 8K/4K, 8K/16K and 32K/64K equal the exposure-scaled formulas; at 65,536 slots the full-N score path is checked against a direct computation;
  - the read swap: π has no fixed point and no pair with equal answers; swapping twice restores the logits; the tie rule of §8.1;
  - no A1 or A2 cell exists at 8K/4K in the registry.
- **G9** seed disjointness (§7). **G10** the mapping part of the arm-selection record equals the auditor's independent evaluation of §3.2 on P9-II's committed records, whose hashes are recorded; Part 1 of the auditor's enumeration script `adr-0020-review/c5_rev2_mapping_and_consistency.py` is re-run and the table cell matching P9-II's committed outcome is cited. The override part equals §3.4 character for character (the human lead's words, the printed string, the F1 annotation, the fixed sentence, μ = 1.0). The list of arms that can still be the candidate equals the auditor's independent evaluation of §8.5 (b) on P9-II's committed records (§3.5).
- The gates stage runs at real size on the rehearsal draw before the freeze and again on registered seeds before training. All gate outputs are written to the run directory and committed. A harness error is reported apart from a gate failure.
- **Manifests record the platform** (OS, architecture, Python, torch, thread settings). Bit-identity gates are asserted on the registered platform; tests that depend on it are platform-conditional.
- **Fixed launch scripts**, no free arguments, committed before the freeze and covered by its hash: gates, Q1, Q1 gate (candidate, and the headroom re-check of §10.4), probe, WX, analysis, report. No registered stage is launched by a typed command.
- **Analysis and report are exercised before the freeze on synthetic records of the full registry:** every row of §3.3, every class under both criteria, every label, annotation and outcome of §8, every block status, missing cells, failed gates, non-finite values, a replaced draw, and each cut of §10.4.

### 10.3 Rehearsal

On the rehearsal draw, six single-thread workers, through the whitelist validator of P9-I (time, memory, shapes, counts, identity; no loss or accuracy is written or shown): every (arm, cell type, phase) of the frozen Q1 matrix, and WX and the 32K/64K cell for **every arm that can still be the candidate** (§3.5: A5-D and A1), and A6 at 32K/64K, for 256 updates and one full evaluation with the read swap; A2 before and after its switch; Run twice: alone, and with twelve other busy single-thread processes **[lead's choice; S1 and S2 may be training on the same machine]**; the larger measured rate is used. A block's projection = measured seconds per update × planned updates (the most expensive possible candidate; A4's annealing at its most expensive measured rate) + measured evaluation, arranged in rounds of six. *Revision 4:* "the most expensive possible candidate" is the most expensive among the arms that can still be the candidate as the arm-selection record lists them (§3.5: A5-D and A1). A4 is not in S0, so its clause has no application.

### 10.4 Resources

Apple M5 Max, 48 GB, CPU only, six single-thread workers. No cloud, no download, no new dependency, no change to `uv.lock` or `pyproject.toml`, no SSD work.

**Projection, not a measurement of this study.** From P9-I's per-update costs with six workers: fastest rehearsal rates 0.008 / 0.013 / 0.035 s at 4,096 / 16,384 / 65,536 slots; W7's registered rates 0.0098 / 0.0141 / 0.0531; the slowest registered rates 0.0112 / 0.0195 / 0.0619. "Six workers" is summed time divided by six (perfect packing), except the probe, which is one round of six cells.

| Block | Cells | Summed CPU-hours (fastest / W7 / slowest) | With six workers, hours |
|---|---|---|---|
| Q1, four learned arms | 230 | 15.8 / 17.7 / 23.4 | 2.6 / 3.0 / 3.9 |
| Q1, three learned arms | 180 | 12.4 / 13.8 / 18.3 | 2.1 / 2.3 / 3.1 |
| WX | 20 | 1.4 / 1.5 / 2.0 | 0.2 / 0.3 / 0.3 |
| 65,536 probe | 6 | 7.6 / 11.6 / 13.5 | 1.3 / 1.9 / 2.3 |
| Pipeline check, rehearsal (twice), gates, generation of 15 draws, evaluation, analysis | | | about 0.8 |
| **Largest configuration** | **256 + 3** | **24.9 / 30.9 / 38.9** | **about 4.9 / 5.9 / 7.3** |

Unmeasured and not in the table: L_addr's all-key backward, A5-D's L_div (a 128 × 128 query product per update), A4's wide read (not in S0 after §3.4), WX's wider projection, the probes during training (about 2% in the ADR-0019 review's estimate), the read swap in evaluation.

**Cap: 16 charged hours for S0, one budget**, covering the pipeline check, rehearsal, gates and every registered block. Twice the largest projection is 9.9 / 11.9 / 14.6 h. At the slowest rates this leaves 1.4 h (about 9%) for everything unmeasured. By the confirmation review's arithmetic the uncut plan absorbs rates up to 1.11 times the slowest P9-I rates, the plan without the probe up to 1.70 times, and Q1 alone up to 1.85 times.

**Revision 4: the arithmetic for n_L = 4, from the rates above.** The row "Q1, four learned arms" and the "Largest configuration" row were computed in revision 3 for four learned arms. They are now the only configuration; the three-arm row no longer occurs. Re-derived:

| Block | Cells × updates, at the rate of | Summed CPU-hours (fastest / W7 / slowest) | With six workers, hours |
|---|---|---|---|
| Q1, 2K/4K | 100 × 8,192, 4,096 slots | 1.82 / 2.23 / 2.55 | |
| Q1, 8K/16K | 100 × 32,768, 16,384 slots | 11.83 / 12.83 / 17.75 | |
| Q1, 8K/4K | 30 × 32,768, 4,096 slots | 2.18 / 2.68 / 3.06 | |
| **Q1 (230 cells)** | | **15.84 / 17.74 / 23.36** | **2.64 / 2.96 / 3.89** |
| WX (20 cells) | 10 × 8,192 and 10 × 32,768 | 1.37 / 1.51 / 2.03 | 0.23 / 0.25 / 0.34 |
| 65,536 probe (6 cells, one round) | 6 × 131,072, 65,536 slots | 7.65 / 11.60 / 13.52 | 1.27 / 1.93 / 2.25 |
| Pipeline check, rehearsal, gates, generation, evaluation, analysis | | | about 0.8 |
| **Whole plan (256 + 3 cells)** | | **24.86 / 30.85 / 38.91** | **4.94 / 5.94 / 7.28** |
| Q1 under cut 3 (190 cells) | 8K/16K with 60 cells | 11.10 / 12.61 / 16.26 | 1.85 / 2.10 / 2.71 |

- **Twice the whole plan is 9.88 / 11.88 / 14.57 hours, under the 16-hour cap.** At the slowest rates 1.43 hours (8.9%) remain for everything unmeasured. These are revision 3's figures; adding A5-D by decision does not change them, because revision 3 already budgeted for a fourth arm.
- **What is lost is the smaller configuration.** With three learned arms the whole plan was 4.37 / 5.29 / 6.44 hours, and the uncut plan absorbed rates up to 1.28 times the slowest P9-I rates. With four it absorbs 1.11 times; the plan without the probe 1.70 times; Q1 alone 1.85 times; Q1 under cut 3 alone 2.66 times (each computed as (16 − 2 × 0.8) / (2 × the block's six-worker hours at the slowest rates)). These multiples, and the 1.43 hours above, are computed under revision 3's whole-plan rule; under reading A the thresholds are those of the last bullet.
- **Under the headroom rule as worded below (R2).** Before Q1, counting the whole 0.8 hours as still to run: 2 × (0.8 + 3.89) = 9.39 hours at the slowest rates, which holds. After the Q1 gate, at the projected charge of 0.8 + 3.89 = 4.69 hours: 4.69 + 2 × (0.34 + 2.25) = 9.87 hours, which holds. If Q1 had run up to its own cap (2 × 3.89 = 7.79 hours): 0.8 + 7.79 + 5.18 = 13.77 hours, which still holds.
- **On the projection the twofold rule holds with n_L = 4 and no cut applies.** The projection is not a measurement. Under the headroom rule as worded below (reading A), at a common multiple m of the slowest P9-I rates and with Q1 running at its projection: Q1 runs uncut up to m ≈ 1.85; above that cut 3 applies, and Q1 under cut 3 fits up to m ≈ 2.66; above that nothing registered is run and the matter returns to the human lead (item 4). After the Q1 gate the probe is kept up to m ≈ 1.68 (0.8 + 3.89m + 2 × 2.59m ≤ 16) and dropped above that (cut 1); WX then fits whenever Q1 ran uncut. No new cut is defined, the fourth arm is not a cut, and the cap is not raised.

**Headroom rule.** The rule is: (hours already charged) + 2 × (rehearsed projection of the stages evaluated) ≤ 16. Before Q1 the rule is evaluated on Q1 and on the stages before Q1 that have not yet run; stages already run count once, as hours already charged. If it does not hold, cut 3 is applied; if it still does not hold, item 4 applies. After the Q1 gate the rule is evaluated on WX and the probe with the actual candidate's rehearsed rates and the hours charged, and cuts 1 and then 2 are applied as needed. **[lead's choice: reading A of the re-check's R2]** Each block's own time cap is twice its rehearsed projection; a block that reaches it is stopped and is INCOMPLETE.

The freeze also records, as information and not as a start condition, the rehearsed projection of WX and of the probe at the most expensive candidate among the arms that can still be the candidate (§3.5), and whether the rule would hold after a Q1 that ran at its projection.

**Cuts if the rule does not hold (fixed in revision 3; numbering and content unchanged). Cut 3 is the only cut available before Q1 and is recorded in the freeze. Cuts 1 and then 2 are applied at the Q1 gate and recorded there:**

1. Drop the 65,536 probe (NOT RUN — BUDGET) **[lead's choice of order: the probe costs about six times WX and is the weaker annotation]**.
2. Drop WX (the variant prints NOT RUN — BUDGET; H20-L is not tested).
3. Drop the second seed at 8K/16K: every learned arm runs ten cells there, seeds alternating by draw as in 8K/4K; the 10-cell class rule of §8.3 applies at 8K/16K; the label states "one initialization seed per draw at 16,384". With cut 3, a draw at 8K/16K succeeds when its one cell succeeds; the consistency rule of §8.5 counts it that way.
4. Nothing else. If the rule still does not hold, nothing registered is run and the matter returns to the human lead. No draw, update count, threshold or exposure is changed.

**Memory.** 3 GiB per worker, 18 GiB aggregate; the rehearsal must show a peak of at most 1.5 GiB per worker (P9-I's peak was 1.49 GiB, in evaluation at 65,536). **If the rehearsal peak of a block's configuration exceeds 1.5 GiB per worker, that block is NOT RUN — MEMORY; nothing is changed to make it fit.** If that block is Q1, nothing registered is run and the matter returns to the human lead. Known risk: A4 at k = N = 65,536 gathers a value tensor of about 1.0 GiB in the forward pass alone (review, c1).

No timing-sensitive comparison is made between cells; CPU seconds are descriptive.

## 11. Implementation

New package `studies/p10s0/` importing `studies.p9ii`, `studies.p9i` and `studies.p9` unedited. New code: the mapping script, WX, the 8K/4K cell, the exposure-scaled schedules at 65,536, the read swap, the two-criteria classes, the replication labels, analysis and report. Records carry the study code P10S0. Implementation, gates and the pipeline check may start before P9-II's registered run finishes, because A0, A1 and A2 are in every branch and every possible fourth arm exists in P9-II's code; they need P9-II's code committed and its calibration record audited. (Moot since revision 4: P9-II's run has finished and its records are committed.) A5-D is taken from `studies.p9ii` unedited; S0 writes no arm code for it. The freeze cannot happen before P9-II's outcome is recomputed and committed. **The freeze also requires that the human lead's acceptance of the P9-II outcome is recorded (the lead's ruling on R8). It is not recorded at the time of writing. Until it is, §13 steps 4–7 may proceed (implementation and tests, the pipeline check, the gates on the rehearsal draw, the implementation audit, the arm-selection record and its audit, the rehearsal), with P9-II's audited calibration values taken by reference (S0 has no calibration of its own, §10.1); step 8, the generation of the registered draws and the freeze, waits.**

## 12. If nothing qualifies: architectural alternatives; and what was moved out of S0

### 12.1 Architectural alternatives

Reported, not run. Each would be P10-I, under the human lead's review. Ordered by the lead's present judgment **[lead's choice]**.

1. **Contrastive query encoder, frozen before memory training.** Train the query projection alone so that two occurrences of a fact are close and different facts far (InfoNCE over queries, no slots); freeze it; then train keys, values and readout on the answer loss. Evidence: the P9-I review's design-stage probe (0.96–1.00 with an oracle store). It needs fact-pair supervision or two contexts of a fact per batch; **that changes data access relative to A0 (ADR-0019 §4 excluded it for that reason), so a comparison with A0 would not be matched.**
2. **Keys written from encoder states (nearest-neighbour addressing).** At a fact's first training occurrence the centred, normalized window state (224 wide, or a fixed random projection) is written as the key of a free slot; only values and readout are trained. No query collapse is possible. Evidence: the window carries 19.8–20.0 bits of the identifier; S1's KNN-W baseline measures the no-learning version.
3. **Hashed, content-addressed keys from input bytes.** Slots from seeded hashes of the last k input bytes for several k at once, reads summed; values learned. A lexical index: exact byte matches only; choosing k is the record-length leak in another form unless all k are used.
4. **Product-key addressing.** Two half-queries, each scored against √N half-keys; a slot is a pair. A collapse of one half costs √N of the address space, not all; the common-mode problem remains inside each half.
5. **Balanced assignment in place of a penalty.** Each batch's queries are assigned to slots by an equal-partition (Sinkhorn) step and trained toward the assignment. Label-free and stronger than A5-D; consistency across batches for one fact again needs fact identity or content similarity.
6. **Let the model form the query, with its language modelling protected.** P9-I's arm BB reached 0.54–0.65 at 4,096 slots and destroyed next-byte prediction. A joint loss or a small added block is the path the handoff names. It leaves the frozen-backbone lineage.

### 12.2 Sequential addition of facts — moved to the integrated study or P10-I

Revision 1's stage Q3 (train 4,096 facts, then add 4,096) is not in S0. The reviewer's reasons, accepted: no sibling can use its label; it models a shared-memory sequential setting, not S2's mechanism (i) with a frozen first memory; its retention label could print after half the old facts were lost. If a later study takes it up, the design must: report the retention ratio ρ = set-A accuracy after phase 2 / at the end of phase 1 for the arm and for the oracle reference, and require both ρ(arm) ≥ 0.90 × ρ(A6) and an absolute ρ(arm); define set A as code clusters 0–255 (fact rows 0–4,095), which the generator supports (review, c4); and decide whether schedules restart in phase 2, since restarting A4's wide read or A2's address-only phase writes into the old facts' slots.

## 13. Order of work

1. Confirmation review by the auditor (done on revision 2: READY after E1–E10, applied in revision 3). Re-check of revision 3 (done: READY SUBJECT TO R1–R10, applied in revision 4). **Independent confirmation of revision 4: pending.** It covers every passage listed in §21, and any passage changed after this revision.
2. The human lead's answer on §17 item 0 is recorded if it has arrived; it does not block S0 (the NOT-QUALIFIED text is neutral until then). The answer is required before any programme-level text, S1 report summary or S2 report summary cites S0's outcome (§17 item 3).
3. Lead's approval under the delegation (§18).
4. Implementation with tests and the fixed launch scripts. Pipeline check (§10.1).
5. Gates at real size on the rehearsal draw and the implementation audit, for every arm in S0's arm set and WX of each arm that can still be the candidate (§3.5), at every cell type of §6. Analysis and report on synthetic registries for every row of §3.3, the override of §3.4 and the list of §3.5.
6. P9-II's registered outcome recomputed and committed (done: `d72b173`, `74f15d1`). The mapping script on P9-II's committed records; the override of §3.4 and the list of §3.5 added; arm-selection record; audited (G10).
7. Rehearsal, twice (§10.3), of the selected arms and of WX and the probe for every possible candidate; projections, caps, memory check, cut 3 of §10.4.
8. Generation and G1 of all draws; freeze of specification, code, config, launch scripts, seeds, thresholds, arm-selection record, projections, caps, cuts and data identities. **Not before the human lead's acceptance of the P9-II outcome is recorded (§18 condition 7).**
9. The registered run, once, by the launch scripts: gates; Q1; Q1 gate with the headroom re-check; then WX and the probe as far as the cuts allow.
10. Independent recomputation from raw records and snapshots by the auditor, Q1 first; outcome report with deviations, failed attempts and negative results kept.

## 14. Stop rules

- A failed gate, or any difference between the frozen and the running code, config, launch scripts, arm-selection record or data identities, stops the run.
- A block whose doubled projection does not fit is not started; a block that reaches its cap is stopped and is INCOMPLETE. Completed blocks stand.
- A failed cell is kept and not re-run.
- No re-run with changed settings. A second attempt after an engineering stop needs the human lead's decision, with everything observed in the first attempt listed.
- No registered seed is seen by a model before the freeze.
- If P9-II's outcome or calibration record is amended after S0's freeze, S0 stops and returns to the human lead.
- S0 is not frozen while the human lead's acceptance of the P9-II outcome is not recorded. If the human lead does not accept it, or accepts it with a changed reading, S0 returns to the human lead before any freeze.

## 15. What S0 cannot establish

- Anything about capacity, useful-capacity scaling, locality, transfer or adding facts later.
- **An unbiased first test of A5-D.** A5-D was added by the human lead's decision after P9-II's outcome was observed, knowing it was RELIABLE there. S0's result for it is a confirmatory replication on new draws. For A5-D the pooled count and CONSISTENT ACROSS STUDIES include the records on which it was chosen and add no independent evidence (§3.4).
- That the interface works on natural language, on another backbone or student (S2's included), at loads other than 0.5 and, for label-free arms, 2 facts per slot, or under any regime other than 512 exposures per fact.
- Anything reliable about 65,536 slots: three draws, one initialization seed, a probe.
- That the interface finds where to read: the memory is told the answer position in every arm, WX included.
- That address labels are available in a real system, or why supervision works: the negative control A1-S is P9-II's and is not repeated.
- That an untuned transfer failing means the arm fails. λ, U_pre, k_0/N and μ were calibrated by P9-II on W7 at 4,096 slots; at two facts per slot, in WX and at 65,536 they are untested transfers. **A failure at a new condition is a failure of the recipe as calibrated at 4,096 on W7, not necessarily of the arm.**
- That a qualified arm beats a tuned baseline: A0 is untuned by design.
- That the record length is required, from a WX failure.
- A success probability above the printed per-draw bounds.
- That S0 overrides P9-II. An arm qualifies only if it is CONSISTENT ACROSS STUDIES (§8.5). Where P9-II has a class, at most two draws failed among both studies' evaluated draws. Where it has none, the label says SINGLE-STUDY EVIDENCE.
- Any efficiency, latency or storage claim.
- A failure of the ArborLM concept, whatever the outcome.

## 16. Requirements map

| The human lead's requirement | Where |
|---|---|
| P9-II interventions as a gate, not assumed to have succeeded | A1 and A2 are re-tested on S0's own draws in every branch (§3.1). P9-II adds at most one arm, its carried label-free arm (§3.2). A label-free arm that P9-II found RELIABLE at 4,096 but did not carry is not re-tested (§3.3, consequence). *Revision 4:* that arm is A5-D, and it is re-tested by the human lead's decision of 2026-11-15, as a confirmatory replication (§3.4). |
| Compare answer-only with addressing supervision and staged optimization | A0, A1, A2 at both core sizes, ten draws × two seeds, in every branch (§3.1, §6.1); paired rule (§8.4) |
| Multiple independent draws and initialization seeds | §6, §7; bounds in §6.3 |
| Fact-specific retrieval, resistance to collapse, strong memory dependence, no oracle at inference | §8.2, §8.5 |
| If none qualifies: report an addressing failure and return with alternatives | §8.7 row 6, §12.1 |
| "Stop capacity-scaling claims" | **not decided here**: §17 item 0 |
| Own hypotheses, controls, thresholds, freeze, Opus audit, outcome report; own identity, seeds, partitions, budget | header, §2, §7, §8, §10, §13 |
| S1 and S2 do not wait; learned addressing evaluated separately if qualified | §9 |
| M5 Max 48 GB; caps from a full-size rehearsal with at least 2× headroom; no cloud, no downloads | §10.3, §10.4 |

## 17. Decisions reserved for the human lead

0. **The reading of "If no interface qualifies, stop capacity-scaling claims."** The lead told the human lead its reading on 2026-11-15 and **has no answer yet.** The question, in the reviewer's words:

   > **If S0 qualifies no interface:** (1) No capacity-scaling claim is made for ArborLM as a system, and none under learned addressing. (2) S1's registered outcome is reported only as a property of the memory store given an external address, always printed with "ORACLE-ADDRESSED — NO LEARNED ADDRESSING QUALIFIED (ADR-0020)", and is never summarised as "ArborLM's capacity scales". (3) S2's outcome is reported as oracle-assisted, as ADR-0022 already requires. (4) The lead reports an addressing failure and returns §12. Please confirm this reading, or say that S1's capacity labels are also withheld.

   Until it is answered, S0's NOT-QUALIFIED outcome text says only what S0 found and makes no statement about S1 or S2. The answer is recorded verbatim in §18 when it arrives.
1. Any change of thresholds, arms, mapping or budget after the freeze; any second attempt; the branch NOT STARTED — NO P9-II CALIBRATION RECORD.
2. Everything that follows ADDRESSING-NOT-QUALIFIED or INCONCLUSIVE: which alternative of §12.1, if any, becomes P10-I.
3. The use of S0's outcome in any programme-level claim; the integrated study (proposed, not executed automatically; needs his review); any supplement to S2; any P10-I.
4. Whether S0's blocks may overlap S1's and S2's training on the machine, and the aggregate memory of concurrent P10 studies (S0 18 GiB, S1 18 GiB, S2 its own, on 48 GB).
5. Merge, publication, weight release, ADR-0012.
6. **Acceptance of the P9-II outcome.** Pending. S0's freeze requires it to be recorded (§11, §13 step 8, §18 condition 7).

## 18. Approval record

The human lead's words, verbatim:

> "we can change it to  p10 can be self approve but p10-I need my review"

> "im confortable with does number if it mean it will resolve most dough and close any posible misguidence due to a small set"

The second sentence was his answer on the P10 budgets (S0 16 hours, S1 12 hours, S2 36 hours), as relayed by the lead.

**The human lead's decision on the fourth arm (2026-11-15), verbatim:**

> yes s0 should include the penalty and i approve s2 download

It answered this question, put by the lead: "Add the diversity penalty to S0? As written, S0 cannot test it and can only qualify the supervised arm. I recommend adding it; the alternative is to run S0 as written and test the penalty in P10-I." The second half of the answer concerns ADR-0022 and is not S0's. The decision was made after P9-II's outcome was observed and before any S0 record exists (§3.4). It is a decision about S0's arms. It is not an approval of this specification for execution, and it is **not an acceptance of the P9-II outcome: the human lead has not accepted that outcome at the time of writing.**

The quotations in this section are recorded as relayed to the drafter by the coordinating session, misspellings included. The drafter did not read the chat record itself.

The lead's conditions for using the delegation, as in ADR-0019 §16: (1) the specification review ends with no open blocker or major; (2) the implementation audit is clean before the freeze; (3) the rehearsal shows 2× headroom; (4) nothing changes after the arm-selection record except the cuts of §10.4, applied as that section fixes; (5) no registered seed has been observed; (6) P9-II's outcome is recomputed and committed before the freeze; **(7) the human lead's acceptance of the P9-II outcome is recorded before the freeze (the lead's ruling on R8). Until then §13 steps 4–7 may proceed and step 8 waits (§11).**

**Independent confirmation of revision 4 (Opus 5.5, 2026-11-15):** READY SUBJECT TO listed text edits, no blocker (`docs/reviews/p10-design-2026-11-15/adr-0020-review/confirm-rev4/CONFIRM_REV4.md`). The auditor reproduced revision 4 byte for byte from revision 3 and the change list, and recomputed the cell counts, the budget and the bounds. Its edits F2–F7, F10 and its edits on the drafter's points 1 and 7 are applied verbatim. F1, the one major, was a choice for the lead: cell success in the paired comparison d(X) is success under S0's criteria, with d(X) under P9-II's criteria printed beside it (§8.4). That choice is made after P9-II's outcome was observed and before any S0 record exists; P9-II recorded no read swap, so no observation bears on it. F8 concerns ADR-0021 and is handled there.

### Lead's approval for implementation and rehearsal — 2026-11-15 (UTC)

Taken by the lead (Claude Fable 5.2) under the delegation quoted above. Not a human approval of the study and not an Astra review.

- **Approved:** §13 steps 4–7 of revision 4: implementation in `studies/p10s0/` and its tests, the pipeline check, the gates on the rehearsal draw, the implementation audit, the arm-selection record and its audit, and the rehearsal.
- **Not approved here:** step 8 (generation of the registered draws and the freeze) and the registered run. Step 8 waits for the human lead's recorded acceptance of the P9-II outcome (§11), a clean implementation audit, a rehearsal that meets the twofold rule, and a separate recorded decision.
- **Basis:** revision 1 review, revision 2 confirmation (E1–E10), revision 3 re-check (R1–R10, N1) and revision 4 confirmation (F1–F10) have no open blocker or major. The fourth arm is the human lead's decision, recorded verbatim in §3.4.
- The lead checked the human lead's quotation in §3.4 and this section against the chat record: it is verbatim.

## 19. How revision 2 answers the review

Review: `adr-0020-review/REVIEW.md` (Opus 5.5), verdict NOT READY.

| Finding | Change in revision 2 |
|---|---|
| **B1** readings of the human lead's direction decided inside the ADR | Items 1 and 2: resolved by the lead's ruling to take the direction literally, so no reading is needed. S0 always runs and always contains A0, A1 and A2 on its own draws (§3.1); P9-II adds at most one arm (§3.2). The reviewer's paste-ready item 0 (a) and (b) is therefore **not adopted**; its alternative ("always run a fixed Q1") is, without the fourth "best label-free arm" as a fixed member. Revision 2 had no pooled rule; revision 3 adds the consistency rule (E1), which closes the path by which an arm that failed in P9-II could qualify on S0 alone. Item 3: kept as a question for the human lead with the reviewer's text (§17 item 0); the NOT-QUALIFIED text is neutral until answered (§8.7) |
| **B2** no target injection at 8K/4K | Option (a). §5.1: A1 and A2 are not run at 8K/4K; NOT RUN — NO TARGET INJECTION; §6.1, §8.6, §9.1, G4 |
| **M1** mapping non-determinism, mislabel, missing rows | Adopted for the reduced mapping: fixed reading order (§3.2), a class of a non-COMPLETE Stage 2 is not read, every outcome enumerated including carried-A0 and excluded-A0 families (§3.3). The exclusion mislabel cannot occur: S0 always runs and never prints "P9-II INCONCLUSIVE". G10 requires an independent evaluation from the text |
| **M2** scope SMALL | Moot. S0 always runs its full core scope; SMALL, E, E4 and "no second chance" no longer exist. ADDRESSING-QUALIFIED AT 4,096 ONLY remains as an outcome of S0's own classes and permits nothing (§9.1) |
| **M3** 65,536 as headline label | Adopted. One label, ADDRESSING-QUALIFIED (4,096 AND 16,384); 65,536 is an annotation probe of the candidate and A6, 3 draws × 1 seed, 6 cells, printed with 0.368 and "probe; not a qualification" (§6.2, §8.6) |
| **M4** NOT REPLICATED mixes replication with added criteria | Adopted. Two classes per arm and cell type (§8.3); replication labels from the class under P9-II's criteria (§8.4); NOT QUALIFIED IN S0 names the added criterion (§8.7); H20-R reads replication only. "No failed cell" is gone, so the added criteria are condition 6 and ADDRESS STABLE |
| **M5** order of work | Adopted and adapted (§13 steps 5–7): gates for every selectable arm before the arm-selection record; rehearsal after it. Because the candidate is known only after Q1, the rehearsal covers WX and the probe for every possible candidate |
| **M6** Q3 | Option (a): dropped. §12.2 lists it for the integrated study or P10-I with the reviewer's corrections |
| **M7** interface with ADR-0021 | Adopted. Revision 2 followed the lead's description of ADR-0021 revision 2; the confirmation review read that text and found a mismatch, corrected by E2 (§9.1): a descriptive lane without step verdict, no 65,536, 4·F updates, S0's success rule printed per lane cell, no human acceptance required. §9.2 states that in the expected timeline the lane will be omitted |
| m1 bounds at two seeds | Adopted, §6.3 |
| m2 hypotheses name the arm | Adopted, §2 and §8.7. WX is trained on the candidate, so "NOT TESTED FOR X2" is not needed |
| m3 8.7 h against 8.4 h | Moot; one budget, recomputed (§10.4) |
| m4 memory rule | Adopted, §10.4 |
| m5 untested transfers | Adopted, §15 |
| m6 WX one-directional | Adopted, §5.2, §8.6, §8.7 |
| m7 a_use ties | Adopted, §8.1 |
| m8, m9 Q3 indices and schedules | Q3 dropped; carried into §12.2 |
| m10 bounded seed ranges; G9 | Adopted with the lead's ranges, §7 |
| m11, m12, m18 sibling wording | Listed in §9.3; not this file's to change |
| m13 integrated study governance | Adopted: needs the human lead's review (§9.2, §17 item 3) |
| m14 shared machine | Adopted, §17 item 4 |
| m15 COLLAPSE-FREE | Adopted, §8.4 |
| m16 references draw-paired | Adopted, §6.1 |
| m17 LM print form | Adopted, §8.3 |
| m19 seed search | Recorded, §7 |
| m20 alternative 1 data access | Adopted, §12.1 |
| Review §8 smallest matrix | Not adopted: the lead ruled ten draws × two seeds on the human lead's acceptance of the budget (§18) |

**Confirmation review of revision 2** (`adr-0020-review/CONFIRM.md`, Opus 5.5): READY AFTER E1–E10. All ten are applied.

| Finding | Change in revision 3 |
|---|---|
| **E1** (required) two chances to pass; consistency rule; preference order | Adopted with the auditor's text. §8.5: CONSISTENT / INCONSISTENT ACROSS STUDIES, SINGLE-STUDY EVIDENCE, threshold of two failed draws over both studies' evaluated draws, order A0, C4, A2, A1. §6.3 (b), §2 H20-Q (c), §8.7 row 6 (d), §15 (e), §20 row 2 (f), the closing section (g) |
| **E2** (required) §9.1 against ADR-0021 revision 2 | Adopted. §9.1 row 1 replaced; the two ADR-0021 edits are listed in §9.3 |
| **E3** wording of the 4,096-only row | Adopted, §3.3 |
| **E4** re-check after the Q1 gate; cut order | Adopted, §10.4: the rule is evaluated again after the Q1 gate with the actual candidate; cut order probe, WX, second seed at 8K/16K (the lead's choice) |
| **E5** UNRELIABLE and FAILS enter no rule; a draw under cut 3 | Adopted, §8.3 and §10.4 |
| **E6** requirements map, row 1 | Adopted, §16 |
| **E7** bounds table | Adopted, §6.3 |
| **E8** sibling drafts | Adopted with the lead's choices: S1's tests are 921001–921999; ADR-0022's corrections are listed "to be applied in ADR-0022 before its approval" (§9.3) |
| **E9** when the human lead's answer is needed | Adopted, §13 step 2 |
| **E10** G10 | Adopted, §10.2 |

**Passages not pasted verbatim from CONFIRM.md, for the auditor's re-check.**

1. E1 (a) (b) and (e): the auditor's bracket "[two]" is written "two", with **[lead's choice]** after it in §8.5 (b). The value is the auditor's.
2. E4: the swap is written out as cuts 1 and 2 with their printed statuses, the reason for the order, and a clause saying when each cut is recorded. The re-check paragraph is verbatim.
3. E8: the auditor offered two ways to settle S1's test range; the text states the one the lead chose, and heads the ADR-0022 list "to be applied in ADR-0022 before its approval". A third bullet on ADR-0019's test range is kept from revision 2.
4. E1 (g): the auditor's list is verbatim; one sentence follows it naming where the points were raised.
5. Edits that follow from E1 and E4 and were not in the auditor's list: §0 (one clause on consistency); §8.7 row 4 and print item 4 (the consistency label); §10.2 launch scripts and §13 steps 7 and 9 (the Q1-gate re-check and the new block order); §10.4 (the review's headroom multiples; "about 9%" for "about 10%"); §18 condition 4; the B1 and M7 rows of this section; §20 rows 2, 11 and 16.
6. Added in revision 4 (R10). The re-check found this list incomplete. Revision 3 also reworded, without listing them here: the header status and revision history; the §9.1 column header; the §9.2 parenthetical; §13 step 1; §18 "Lead's approval: PENDING."; §20 rows 5, 10 and 17; the closing heading. The re-check read all of them and found that none changes a rule or a number.

## 20. The lead's choices in this revision (fixed before any rehearsal)

| No. | Choice | Where |
|---|---|---|
| 1 | S0 always runs with A0, A1, A2, A6, A7; at most one fourth arm, P9-II's carried arm if it is A4, A5-C or A5-D; no X2. *Revision 4: that rule gave no fourth arm; the fourth arm is A5-D by the human lead's decision, not by a choice of the lead (§3.4)* | §3 |
| 2 | Candidate from S0's classes subject to the consistency rule of §8.5 (rulings 1 and 3); preference order A0, C4, A2, A1. | §8.5 |
| 3 | Ten registered draws × two init seeds at 2K/4K and 8K/16K; one seed at 8K/4K and for WX; probe three draws × one seed | §6 |
| 4 | RELIABLE at 20 cells: at most one failed cell, no draw with both seeds failed; UNRELIABLE from 5 successes; NOT_EVALUATED above one unevaluated draw | §8.3 |
| 5 | 10-cell types: at most one failed cell; UNRELIABLE from 3 successes (ruling 6; confirmed by the confirmation review) | §8.3 |
| 6 | Condition 6 at 0.95; oracle floor 0.50 at 8K/4K | §8.2 |
| 7 | A1 and A2 not run at 8K/4K | §5.1 |
| 8 | 65,536 as an annotation probe, never in the label | §8.6 |
| 9 | Q3 dropped | §12.2 |
| 10 | WX initializer at fan-in 2,048; WX and the probe after the Q1 gate, WX on the Q1 draws (ruling 5) | §5.2, §6.2 |
| 11 | One cap of 16 charged hours; cut order probe, WX, second seed at 8K/16K; nothing else; cuts 1 and 2 decided after the Q1 gate. *Revision 4 (R2, reading A):* before Q1 the rule is evaluated on Q1 and the stages before it only, with cut 3 the only cut available then | §10.4 |
| 12 | Rehearsal twice, the second under twelve busy processes | §10.3 |
| 13 | Bounded seed namespaces | §7 |
| 14 | NOT-QUALIFIED text neutral about S1 and S2 until the human lead answers | §8.7, §17 |
| 15 | Order of the alternatives | §12.1 |
| 16 | Consistency threshold: at most two failed draws among the evaluated draws of both studies | §8.5 |
| 17 | S1's unit-test seeds 921001–921999 | §7, §9.3 |
| 18 | *Revision 4.* R4: P9-II's class at 16,384 is read for an arm that has a Stage 2 class at the 4U readout | §8.5 |
| 19 | *Revision 4.* R8: S0's freeze requires the recorded acceptance of the P9-II outcome by the human lead | §11, §13, §14, §18 |
| 20 | *Revision 4.* "Most expensive possible candidate" means over the arms that can still be the candidate (§3.5) | §10.3, §10.4 |
| 21 | *Revision 4.* The human lead's decision is applied as: A5-D takes exactly the place revision 3 defines for a label-free C4 | §3.4 item 6 |

## 21. Revision 4: each change and its source

Revision 4 was drafted on 2026-11-15, after P9-II's outcome was observed and before any S0 record exists. It changes the fourth arm, by the human lead's decision, and applies the re-check of revision 3 (`adr-0020-review/RECHECK_REV3.md`). **No threshold, criterion, class rule, preference order, consistency rule, seed, draw count, update count or cap is changed.** Of its changes, only the fourth arm was prompted by P9-II's results; that one is the human lead's. The lead's choices among the re-check's options are R2 (reading A), R4, R5 (the reworded option) and R8.

| Source | What revision 4 does | Where |
|---|---|---|
| **Human lead's decision, 2026-11-15** ("yes s0 should include the penalty …") | C4 = A5-D with μ = 1.0; the mapping's result (none) is kept as the record and the override is written beside it with its provenance; fixed printed string with P9-II's F1 annotation and a fixed provenance sentence; n_L = 4; Q1 = 230 cells; budget arithmetic re-derived; what the unchanged consistency rule gives per arm | header, §0, §1, §2 H20-D, §3.2, §3.4, §3.5, §4, §6, §6.3, §8.5 (pointer), §8.7 print item 1 and the paragraph after the NOT-QUALIFIED text, §10.2 G10, §10.4, §11, §13 step 6, §15, §16 row 1, §18, §20 rows 1 and 21 |
| **R1** (major) §9.1 contradicted ADR-0021 §5.6 | lane L deferred entirely to ADR-0021 §5.6, revision 4; this ADR states no lane rule; the consequence for A1 and A5-D is stated as a consequence | §9.1 |
| **R2** (major) pre-Q1 headroom evaluation not determined | reading A with the auditor's sentence; the cut heading reworded to match; "most expensive possible candidate" defined over the arms that can still be the candidate | §10.3, §10.4, §20 rows 11 and 20 |
| **R3** §8.7 row 5 lacked the reason added by E1 | "or INCONSISTENT ACROSS STUDIES (P9-II \<class\>; pooled \<failed\> of \<n\>)" appended | §8.7 row 5 |
| **R4** "X advanced" ambiguous for A0 | "X has a Stage 2 class at the 4U readout" | §8.5, §20 row 18 |
| **R5** G10's second clause not executable | the reworded option: Part 1 is re-run and the matching table cell is cited | §10.2 |
| **R6** no fixed fourth-arm string; F1 annotation missing | "FOURTH ARM: NONE — P9-II CARRIED \<arm\> (ALREADY IN S0)" for the mapping's own result; the revision 4 string for the override; F1 annotation verbatim wherever the carried arm or A5-D is cited | §3.2 item 4, §3.4, §8.7 |
| **R7** descriptive pooled count underdefined | "under P9-II's criteria; NOT AVAILABLE where P9-II has no class for the arm at that size" | §6.3 |
| **R8** P9-II's human acceptance pending | the lead's ruling: the freeze requires the recorded acceptance; implementation, set-up by reference to P9-II's calibration record and rehearsal may proceed | §11, §13 step 8, §14, §17 item 6, §18 condition 7, §20 row 19 |
| **R9** §9.3 stale | rewritten: nothing is owed by ADR-0021 (revision 4) or ADR-0022 (`2ef6a4f`) | §9.3 |
| **R10** editorial | "(this text)" removed from revisions 2 and 3; the evidence line keeps its sentence with the two commits; §11's moot clause marked; duplicated §20 heading removed; §19's list completed; §8.7 row 6 grammar | header, §8.7 row 6, §11, §19, §20 |
| **N1** S1's seed-block initialization seeds | 2111, 2121, 2112, 2122 listed in S1's namespace | §7 |

**Stated consequences of the re-check that revision 4 does not turn into changes:** the re-check's finding that, as written in revision 3, only A1 could qualify and no label-free qualification was possible is superseded by the human lead's decision and restated for four arms in §3.5.

**Passages of revision 4 that are the drafter's wording and not the auditor's paste text, for the confirmation:** all of §3.4 and §3.5; the revision 4 additions to §0, §2, §4, §6, §6.3, §8.5, §8.7, §15, §16 and §18; G10's two added clauses; §10.3's and §10.4's definition of "most expensive possible candidate"; the informational projection recorded at the freeze (§10.4); the budget table and bullets for n_L = 4; the cut heading; §9.1's consequence sentence; §9.3; §11; §13 steps 1, 6 and 8; §14's new bullet; §17 item 6. Pasted from the re-check without change: the §9.1 cell (R1, with "revision 4" for "revision 3"), the three sentences of R2's edit, R3's clause, R4's clause, R5's reworded clause, R6's first string, R7's clause, R10's row 6 wording.

**Left as revision 3 wrote them although the fourth arm is now fixed** (listed so that the confirmation can check them; none is changed here): G4 and §13 step 5 still cover every arm the mapping could have selected (A4 and A5-C included); §10.3 still rehearses WX and the 32K/64K cell for A0 and A2, which can no longer be the candidate; §10.2's synthetic registries still exercise every row of §3.3; the three-arm rows of §6.1 and §10.4.

## The lead's rulings on the drafter's points

**The lead's rulings on the drafter's points (2026-11-15):**
(1) consistency rule, §8.5;
(2) NOT STARTED without an audited P9-II calibration record, §3.2;
(3) preference order A0, C4, A2, A1, §8.5;
(4) the fourth arm only when P9-II carries a label-free arm, §3.2;
(5) WX and the probe after the Q1 gate, WX on the Q1 draws, §6.2;
(6) class thresholds of §8.3 confirmed by the confirmation review.
ADR-0021 revision 2 was checked by the confirmation review (§9).

The points were raised at the end of revision 2.

Astra review: NOT_PERFORMED. A Claude review is not an Astra review, and this document is not a human approval. The human lead's decision recorded in §18 fixes the fourth arm; it does not approve this specification for execution and does not accept the P9-II outcome.

## Addendum to §18 — the human lead's acceptance of P9-II (2026-11-15 UTC)

The human lead accepted the P9-II outcome as registered (verbatim in ADR-0019 §16: "yes I do, yes we can raise to 16 and I approve the package", in answer to "Do you accept the P9-II outcome as registered? S0 can be implemented and rehearsed without it but cannot be frozen."). The condition of §11 and §18 that S0's freeze waits for that acceptance is met. Step 8 still needs a clean implementation audit, a rehearsal that meets the twofold rule, and the lead's separate recorded decision. Nothing else in this ADR changes.

## Addendum — the human lead's delegation on the hour cap (2026-11-15 UTC)

The human lead, verbatim (the first clause concerns ADR-0022):

> I Aprove the link files with 6.2mb and you can extend the hour cap if needed across all p10

Recorded by the lead, with the limits the lead puts on its own use of this:

- The lead may raise a P10 study's charged-hours cap when the study's own headroom rule would otherwise cut registered cells or stop the study.
- A cap is raised only **before that study's registered seeds are observed** (at the rehearsal's headroom check, or at a stage gate that reads time and memory only). It is never raised in response to a result, and never to add cells, arms, updates or replicates beyond what the specification registers.
- Each raise is recorded in the study's ADR with the measured projection that required it, the old and new cap, and what it protects. Memory caps (3 GiB per worker, 18 GiB aggregate, and S2's own) are not hour caps and are not changed.
- The human lead's words do not extend to downloads, cloud or paid services, models, data, thresholds or designs.

S0's cap is unchanged by this record (16 hours). Programme-level record: `docs/reviews/p10-design-2026-11-15/HUMAN_DECISIONS_2026-11-15.md`.

## Addendum — the lead's rulings on the implementation audit, fixed before the pipeline check and rehearsal (2026-11-15 UTC)

The independent implementation audit (Opus 5.5, `docs/reviews/p10s0-implementation-audit-2026-11-15/AUDIT.md`) found the implementation READY AFTER LISTED FIXES: no blocker, 10 majors, 14 minors. The auditor's own implementation of the class, consistency, qualification and outcome rules agreed with the code on 5,000 random registries except for H20-A; the arms are bit-identical to `studies.p9ii`'s. The rulings below are the lead's (Claude Fable 5.2), made **before any S0 pipeline check, rehearsal, gate output or generated draw exists**. They are part of the specification from here on. Astra review: NOT_PERFORMED.

| Finding | Ruling |
|---|---|
| **M5** records made after the freeze; the hour-cap delegation | The lead's run decision is recorded in a file outside the hashed specification (`results/p10s0-freeze-<date>/DECISION.md`), named in the freeze README, and this ADR is amended with it after the registered run. **A cap raise under the human lead's delegation can only be made before the freeze**, at the rehearsal's headroom check, by changing the cap in the config and recording it in this ADR before the freeze commit. After the freeze the cap is fixed; the checks at the Q1 gate use the frozen cap and apply the registered cuts. No raise is ever made after a registered seed has been observed |
| **M6** analysis and report can be locked out | The headroom rule (reading A) counts, at every evaluation, the rehearsed time of the analysis and report stages (doubled like every other remaining stage) as part of what is still to run. A block is not started if it would leave less than that. This makes the rule slightly more demanding; it changes no cut and no order |
| **M8** the gates cap | The cap of the registered gates stage is computed for 13 draws × 3 fact sets from the rehearsal draw's measured per-draw time, not copied from the one-draw rehearsal gates |
| **m4** H20-A | As the ADR's sentence reads: supported if A0 is UNRELIABLE or FAILS at 2K/4K or at 8K/16K; not supported if A0 is RELIABLE at both; not read otherwise |
| Item 1 | The config is `configs/p10s0_qualification.toml`, as the header says |
| Item 2 | The generation cap is twice the measured generation time of the rehearsal draw, with a floor of 60 seconds per draw; the freeze refuses while the cap is provisional |
| Item 6 | Every printed string this ADR does not fix is listed in the freeze record and approved there by the lead |
| Item 7 | After the Q1 gate, WX runs before the 65,536 probe |
| Item 10, H20-O | "Not read" when OVERLOAD is NOT_EVALUATED; "not supported" when NOT QUALIFIED |
| M1–M4, M7, M9, M10 and the other minors | Implementation defects, fixed as the audit states. M7: the whole registered sequence is exercised end to end on test seeds through the real launch scripts before the freeze. M9: the branch is brought up to the design branch, which records the human lead's acceptance of P9-II |

Items 3, 4, 5, 8 (with P9-II's test-seed constants also asserted directly), 9, 11 and the rest of item 10 were found correct and stand.

