# Specification review of ADR-0020 (P10-S0, addressing qualification), design revision 1

- **Reviewer:** Claude Opus 5.5 (`claude-opus-5-5`), specification auditor for this study only. I did not write any part of ADR-0019, ADR-0020, ADR-0021 or ADR-0022, or any code they rely on.
- **Date:** 2026-11-15. **Astra review: NOT_PERFORMED.** This review is independent engineering and mathematical evidence. It is neither Astra validation nor a human approval, and it does not approve anything.
- **Inputs (sha256 prefixes; full hashes in `outputs/input_hashes.txt`):** ADR-0020 revision 1 `930f71d7`, ADR-0019 rev4 `667ef3ef`, ADR-0021 `27950dac`, ADR-0022 `e5cb296f`, evidence inventory `a59af8a1`. Worktree at `ecd5b87`; `studies/p9/data.py` read for the generator.
- **What I ran:** arithmetic and enumeration scripts, a seed search, and one structural generator check (§10). **What I did not run:** no training, no model, no registered benchmark, no new real-data experiment, no git or GitHub action, no download. No tracked file was edited.

## Verdict: NOT READY for the lead's self-approval

Two blockers and seven majors are open. Every number the draft prints that I could recompute matches (bounds, cell counts, projections, seed layout). The problems are in what the draft decides, labels and hands to the sibling studies, not in its arithmetic.

| ID | Class | One line |
|---|---|---|
| B1 | BLOCKER | The draft settles two readings of the human lead's explicit direction (S0 has no data when P9-II gives no reliable arm, and the answer-only/supervised/staged comparison belongs to P9-II; "stop capacity-scaling claims" covers learned addressing only). The human lead must confirm them; the lead cannot self-approve them. |
| B2 | BLOCKER | At 8K/4K (8,192 facts, 4,096 slots) the target slot s(f) of A1 and A2 is defined as an injection, which cannot exist. A registered cell is undefined in reachable branches. |
| M1 | MAJOR | The mapping is not deterministic in one reachable case (c16 when Stage 2 is not COMPLETE), mislabels another (all arms excluded is printed as "P9-II INCONCLUSIVE"), and the §3.4 table omits two families. |
| M2 | MAJOR | Scope SMALL spends 72–90 cells on a label that §9.1 lets nobody use, and retrains at 8,192 facts an arm that P9-II failed at 8,192 facts. |
| M3 | MAJOR | The headline label ADDRESSING-QUALIFIED rests at 65,536 on 3 draws and one initialization seed (bound 0.37). No sibling lane uses 65,536. Q2 is about 68% of S0's CPU. |
| M4 | MAJOR | "NOT REPLICATED IN S0" and H20-R mix replication failure with failure of criteria that S0 added (condition 6, ADDRESS STABLE, "no failed cell"). |
| M5 | MAJOR | The order of work runs the pipeline check and rehearsal on C before the arm-selection record exists. |
| M6 | MAJOR | Q3's label OLD FACTS RETAINED can print after half the old facts are lost. Q3 matches S2's shared-memory arm, not mechanism (i), and no sibling can use it. |
| M7 | MAJOR | §9.1 does not match ADR-0021 §5.6: the lane's only step needs 8K/4K; 65,536 is not a lane cell; update counts, acceptance rule and success rule differ. In the expected timeline the lane is omitted, and the human lead should be told. |
| m1–m20 | minor | Listed in §4. |

---

## 1. Blockers

### B1. Readings of the human lead's explicit direction are decided inside a self-approvable ADR

**Finding.** The human lead's S0 requirements include: "Compare the original answer-only method with preregistered addressing supervision and staged optimization. Evaluate across multiple independent data draws and initialization seeds", together with S0 being one of "three parallel, scientifically independent experiments" with its own data. The draft decides three things on its own authority:

1. **No data of its own in rows 7–9 of §3.4.** When P9-II is ADDRESSING-UNRELIABLE, ADDRESSING-FAILS or INCONCLUSIVE, S0 trains nothing. Its outcome is then a relabelling of P9-II, not an experiment. My enumeration (c2) confirms that E and E4 are always empty in those rows, so this follows from the rule and is not a side effect.
2. **The comparison is left to P9-II.** The comparison of answer-only, supervised and staged training is P9-II's. S0 compares C (and X2, if one exists) with A0 only. In row 1 with no supervised arm in E, and in row 3 with none either, S0 contains no supervised or staged arm at all. §16 maps the requirement to "A0 in every cell type; C and X2 from different supervision classes where P9-II offers both", which is accurate only when P9-II offers both.
3. **Scope of "stop capacity-scaling claims"** (§9.1, open question 7). The draft applies it to learned addressing only and lets S1's and S2's oracle-addressed outcomes stand. See §7 (item H).

Each of these readings is defensible, and I recommend reading (1) myself (§5, item A). But they are readings of the human lead's explicit direction. AGENTS.md puts that direction first in the authority order and says: "If documents disagree, stop and request a recorded Astra/human decision rather than silently choosing." The draft is not silent: it lists them as open questions 1 and 7. It addresses them to the lead, though, and the delegation the human gave covers P10 *studies* after a clean review, not reinterpretations of his own requirements. "p10 will determine if the hypothesis stands" makes the stakes explicit. Under reading (1), the likeliest negative branch produces no new evidence.

**Fix (paste-ready).** Add to §17 as item 0, and to §18 as a required record before approval:

> 0. **Readings of the human lead's P10 direction, to be confirmed or replaced by the human lead before the lead approves this ADR:**
> (a) When P9-II's registered outcome has no arm RELIABLE at 4,096 slots (ADDRESSING-UNRELIABLE, ADDRESSING-FAILS or INCONCLUSIVE), S0 trains nothing and has no data of its own. It records ADDRESSING-NOT-QUALIFIED (BY P9-II; S0 NOT RUN) or INCONCLUSIVE (P9-II INCONCLUSIVE; S0 NOT RUN), and the lead returns §12 to the human lead.
> (b) The comparison of the original answer-only method with addressing supervision and staged optimization, across independent draws and initialization seeds, is the one P9-II (ADR-0019) registers. S0 compares only the arm(s) the mapping of §3 selects with A0. S0 includes a supervised or staged arm only if P9-II found one RELIABLE at 4,096.
> (c) "Stop capacity-scaling claims" (if no interface qualifies) is applied as in §9.1, worded as in §9.4 [new; see M7 and item H of the review].
> The human lead's words on (a)–(c) are recorded verbatim in §18. Until then the lead's approval is not given.

Replace the second row of §16 with:

> | Compare answer-only with addressing supervision and staged optimization | Registered by P9-II (ADR-0019 §4, §8.4) on its fourteen draws. S0 compares the selected arm(s) with A0 only (§3.3). S0 contains a supervised or staged arm only if P9-II found one RELIABLE at 4,096. This reading is §17 item 0(b), confirmed by the human lead on [date] |

If the human lead rejects (a)/(b), the alternative is to *always* run a fixed Q1 at 2K/4K and 8K/16K with A0, A1, A2 and the best label-free arm, whatever P9-II shows. That makes S0 a confirmatory replication of P9-II's core comparison. It conflicts with "no second chance" (an arm with two or more failed cells of sixteen in P9-II cannot become reliable on new draws without a pooled rule), so it would need a pooled class rule over P9-II's and S0's draws. That is a different study and needs its own review.

### B2. The target slot of A1/A2 is undefined at 8K/4K

**Finding.** ADR-0019 §4 defines s(f) as "a fixed injection s(f) from the trained facts into the N slots". ADR-0020 §5.4 uses the same word for Q3. At 8K/4K, F = 8,192 > N = 4,096, so no injection exists. A1 and A2 are candidates in rows 1–6 (and A2/A1 are C in row 2), and WX(C) inherits the target. In those branches the registered cell is undefined, and the implementer would have to make a scientific choice, which the protocol forbids.

The obvious repair (two facts per target slot) is not neutral. L_addr pulls both facts' queries toward the same key. Two facts with the same target then read nearly the same top-8 set, and with different answers about half of them must be wrong. Accuracy would be capped by the target design, not by addressing. A6 uses random codes and top-8 sets, so its accuracy is not capped this way.

**Fix (paste-ready), [lead's choice] between:**

> **(a, recommended)** §5.1, new bullet: "At cell type 8K/4K the arms A1 and A2 (as C, X2 or inside WX(C)) are not run, because a target-slot injection does not exist when facts outnumber slots. For such an arm OVERLOAD prints NOT RUN — NO TARGET INJECTION. If the qualified arm is supervised, S1's learned-address lane cannot form step 8K/4K → 8K/16K, and §9.1 prints OMITTED — SUPERVISED ARM HAS NO 8K/4K CELL."
>
> **(b)** §5.1, new bullet: "At 8K/4K, s(f) is a seeded two-to-one map: a uniformly random permutation p of the 8,192 facts (seed base + 40 + j) and s(f) = p(f) mod 4,096. Two facts that share a target are pulled toward one key. OVERLOAD for a supervised arm therefore tests this target design as well as addressing, and the label says so: OVERLOAD (TWO FACTS PER TARGET SLOT)."

Correct the cell counts of §6.1 and the cut rule of §10.4 for (a).

---

## 2. Majors

### M1. Mapping: one non-deterministic case, one mislabel, two unlisted families (item A, gate G10)

I implemented P9-II's outcome rule (ADR-0019 rev4 §8.4, §8.6) and S0's rule (§3.2–§3.3) independently and enumerated 2,462,636 class combinations (`c2_mapping_enumeration.py`, `outputs/c2_mapping_enumeration.txt`). The enumeration varied six arms × five classes at 4,096, the NC flags, four Stage-2 statuses and six classes at 16,384 for every advanced arm. Results:

- **Complete.** Every combination receives a P9-II row (0 unclassified) and an S0 branch. Wherever the §3.4 table covers a case, the §3.3 rule and the literal table agree (0 disagreements).
- **(a) Not deterministic.** "c16 = RELIABLE; … or UNTESTED (… Stage 2 is not COMPLETE …)" overlaps when Stage 2 is INCOMPLETE (or NOT_EVALUATED) and P9-II's analysis still prints a class for an arm whose cells finished. Row 4's own clause "C = A0 unless a tier-1 arm exists" can only fire in that overlap, so the draft anticipates it. In 9,788 enumerated records the two readings choose a different C or X2. Example: everything RELIABLE at 4,096, Stage 2 INCOMPLETE, A5-C printed RELIABLE at 16,384. Strict reading: C = A0, X2 = A2. Loose reading: C = A5-C, X2 = A2. The LM flag has the same issue at Stage 2's U readout, which ADR-0019 does not say is excluded.
- **(b) Mislabel.** "E and E4 both empty under rows 3–6 … is treated as row 9" prints **INCONCLUSIVE (P9-II INCONCLUSIVE; S0 NOT RUN)**. That case is reachable: 513,696 enumerated records, for example every arm that is RELIABLE at 4,096 carries LM CAPABILITY REDUCED at 16,384, or A1/A2 are excluded by NEGATIVE CONTROL FAILED at 16,384. P9-II was not INCONCLUSIVE in those records, so the printed sentence is false. The programme consequence also differs: NOT-QUALIFIED triggers "report an addressing failure", INCONCLUSIVE does not.
- **(c) Unlisted families.** (i) ANSWER-ONLY RELIABLE with A0 excluded (LM-flagged at 16,384). (ii) ADDRESSING-RELIABLE with A0 as P9-II's carried arm (A0 RELIABLE at 16,384, not at 4,096). In both the rule decides, but the table's rows 1–4 do not mention them.

**Fix (paste-ready).** Replace the c16 bullet of §3.2 with:

> - **Status at 16,384**, read in this order: (1) **UNTESTED** if P9-II's Stage 2 status is not COMPLETE, or X did not advance to Stage 2, or X's class at 16,384 (4U readout) is NOT_EVALUATED; (2) **RELIABLE** if X's class at 16,384 (4U readout) is RELIABLE; (3) **FAILED** otherwise (UNRELIABLE, UNRELIABLE (LM CAPABILITY REDUCED) or FAILS). A class printed for a Stage 2 that is not COMPLETE is not read. LM CAPABILITY REDUCED and NEGATIVE CONTROL FAILED are read at Stage 1 and at Stage 2's 4U readout only.

Replace the sentence after the §3.4 table with:

> If P9-II's outcome is one of rows 3–6 and E and E4 are both empty, every arm RELIABLE at 4,096 was excluded. S0 is not run. If at least one exclusion is LM CAPABILITY REDUCED, the outcome is **ADDRESSING-NOT-QUALIFIED (BY P9-II EXCLUSIONS: <arm — reason — size, for each>; S0 NOT RUN)**. If all exclusions are NEGATIVE CONTROL FAILED, it is **INCONCLUSIVE (P9-II NEGATIVE CONTROL FAILED AT <size>; S0 NOT RUN)** [lead's choice of the split]. Neither is described as "P9-II INCONCLUSIVE" unless P9-II's own outcome is INCONCLUSIVE.

Add two illustration rows:

> | 1a | ADDRESSING-RELIABLE, carried arm A0 (RELIABLE at 16,384, not at 4,096) | A0 is not in E (§3.2). C = first arm of E by rank; X2 by the rule; A0 runs as the baseline | FULL |
> | 3a | ANSWER-ONLY RELIABLE, A0 excluded (LM CAPABILITY REDUCED at 16,384) | C = first arm of E, else of E4; X2 by the rule; A0 runs as the baseline | FULL or as M2 |

G10 must require that the auditor's mapping is written from the text, not from the implementer's script. My script is an existing instance, and it should be re-run on P9-II's committed output.

### M2. Scope SMALL is a perverse branch

**Finding.** E4 arms are RELIABLE at 4,096 and FAILED at 16,384 in P9-II. Under SMALL scope S0 trains 90 cells (72 without X2) and can only reach ADDRESSING-QUALIFIED AT 4,096 ONLY. §9.1 then gives S1 no lane, S2 nothing and the programme no statement. SMALL scope also includes 8K/4K. That cell holds the same 8,192 facts at which the arm failed with four times more slots, so a near-certain failure is retrained. "No second chance" is written in slot counts (16,384, 65,536) and lets this through. c2 shows SMALL is reachable from ANSWER-ONLY RELIABLE (A0 or others) and from ADDRESSING-RELIABLE AT 4,096 ONLY. The latter is one of the outcomes I consider plausible, since W7 escaped at 4,096 in 9 of 11 exploratory runs and reached 0.04 at 16,384.

**Fix (paste-ready), §3.3 item 1, second sentence:**

> If E is empty, S0 is not run, and the outcome is **ADDRESSING-NOT-QUALIFIED FOR P10 (BY P9-II: RELIABLE AT 4,096 ONLY — <arms of E4>; S0 NOT RUN)**. A replication at 4,096 alone would yield a label that §9.1 lets no study use [lead's choice; the alternative is to keep SMALL as 2K/4K only, 48–60 cells, and never 8K/4K].

Extend "No second chance" with: "… nor at 8K/4K if P9-II classed it FAILED at 16,384 (the same 8,192 facts in fewer slots)." Remove the SMALL counts from §6.1 and the SMALL rows from §8.6 accordingly.

### M3. ADDRESSING-QUALIFIED at 65,536 should be an annotation, not the headline label

**Finding.** Q2 has 3 draws, all at init seed 2001. A 3-of-3 result gives a per-draw lower bound of 0.368 (recomputed). The human lead's requirement "multiple independent data draws and initialization seeds" is not met at 65,536, because only one seed is used. P9-II treated its own 65,536 probe as "positive or uninformative" and gave it no reliability statement. S0 turns a probe of almost the same size into the top outcome. No sibling consumes it either: ADR-0021 §5.6's lane uses 2K/4K, 8K/4K and 8K/16K only. S0 §9.1 row 1 ("on 4,096, 16,384 and 65,536 slots") offers S1 something S1 never asks for. Q2 costs 23.2 of 33.9 projected CPU-hours at the W7 rate (68%) and fills Budget B to 9.96 of 10 h at the slowest rates.

**Fix (paste-ready).** §8.6 rows 5–7 become one row:

> | 5 | **ADDRESSING-QUALIFIED (4,096 AND 16,384)** | the candidate has scope 16,384. Always printed with the annotation **AT 65,536 (S0 only; three draws; one initialization seed): k of 3 succeed; per-draw bound b**, or Q2's status. The annotation is never a qualification and permits nothing in §9.1 |

H20-S: "supported as an annotation if 3 of 3; contradicted if 0 of 3 with A6 evaluated; otherwise not supported." §9.1 row 1: delete "and 65,536". Q2 [lead's choice]: either drop it (Budget B shrinks to Q3 or to nothing), or reduce it to C and A6 × 3 draws (6 cells, one round, 1.3–2.3 h). A0 and A7 are needed only for the paired and dense labels, which an annotation does not need. If the lead wants a qualification at 65,536, it needs at least 5 draws (5 of 5 → 0.549) and both seeds, and it should be a later study.

### M4. "NOT REPLICATED" mixes a replication failure with stricter criteria

**Finding.** S0's success adds condition 6 (a_use ≥ 0.95 × accuracy). S0's qualification adds ADDRESS STABLE, which P9-II only annotates. The six-cell types use "no failed cell" where ADR-0019 allowed one. An arm can therefore be RELIABLE by P9-II's own criteria on S0's draws and still print **NOT REPLICATED IN S0**, and §2 then calls H20-R "a registered negative … did not replicate". That statement would be false.

**Fix (paste-ready).** §8.4, new paragraph:

> For every learned arm and cell type S0 also prints the **class under P9-II's criteria**: conditions 1–5 of ADR-0019 §8.3 and the count rule of ADR-0019 §8.4 (at most one failed cell), applied to S0's cells. Qualification uses S0's criteria.

§8.6 row 4, replace the parenthesis with:

> … printed "NOT QUALIFIED IN S0", with each arm's S0 class and its class under P9-II's criteria. "NOT REPLICATED" is printed only if C's class under P9-II's criteria is not RELIABLE at 2K/4K (or at 8K/16K for a scope-16,384 reading). Otherwise the text is "REPLICATED UNDER P9-II's CRITERIA; FAILS S0's ADDED CRITERION <condition 6 | ADDRESS STABLE | no failed cell>".

H20-R reading: "supported if C is RELIABLE at 2K/4K and 8K/16K under P9-II's criteria on S0's draws. Qualification is reported separately." Align the H20-R text of §2, which does not mention ADDRESS STABLE although the reading requires it.

### M5. The order of work needs C before C is known

**Finding.** §10.1's pipeline check trains "A6, A7 and C". §10.3 rehearses "every distinct (arm, cell type, phase) of the frozen matrix". §13 puts both at step 5, says steps 4–5 "may begin before" P9-II's outcome exists, and places the arm-selection record at step 6. One of the two must give way. This matters for A4 at 65,536: P9-II never runs A4 there, and a soft read over k = N slots built by gather holds a [128, 65,536, 32] float32 tensor of 1.00 GiB in the forward pass alone (c1). That alone approaches the 1.5 GiB rehearsal limit, and the draft has no rule for a failed memory check (m4).

**Fix (paste-ready), §13 steps 5–7:**

> 5. Gates at real size on the rehearsal draw and the implementation audit, for **every arm the mapping can select** (A0, A1, A2, A4, A5-C, A5-D, and WX of each) at every cell type of §6. Analysis and report on synthetic registries.
> 6. The mapping script on P9-II's committed output; arm-selection record; audited (G10). If it selects nothing, the study ends here (§3.4).
> 6b. Pipeline check (§10.1) and rehearsal, twice (§10.3), of the selected arms only; projections and caps; cuts of §10.4.
> 7. Generation and G1 of all draws; freeze.

### M6. Q3 overclaims retention, does not match S2's mechanism, and has no consumer

**Findings.**

- **Reference.** OLD FACTS RETAINED is "candidate's set-A accuracy after phase 2 ≥ 0.90 × A6's after the same phase 2". With shared slots (8,192 × 8 / 16,384 = 4 top-8 memberships per slot), a shared output projection and gate trained only on B in SEQ-N, the oracle reference may itself forget heavily. If A6 keeps 0.55, the label prints OLD FACTS RETAINED for a candidate at 0.50, having lost about half its facts. The NOT_EVALUATED floor (0.50) does not prevent this. The comparison "forgets no more than oracle addressing" is a sound question, but the label name claims retention. The absolute level at S_A is also not normalised, so a candidate that learned less in phase 1 is judged on a mixture of learning and forgetting.
- **Mapping to S2.** Q3's SEQ-N trains B into the *same* slots. That is S2's shared-memory sequential setting (L-seq/M-seq style), not mechanism (i), where memory A is frozen and B gets new slots. Only the frozen-memory read approximates (i), and even that is an approximation: the phase-2 query projection was trained against moving keys in the same memory, not against a separate memory B.
- **Consumer.** S2 cannot consume any S0 label: different student, no slot-level learned addressing, and a supplement is reserved to the human lead (§17.3). S1 does not use Q3. Q3 exists for a fourth study that is "proposed after all three finish". It is not required by the human lead's S0 criteria.
- **Generator.** The cluster split is sound (`c4_q3_split.py`, using `studies/p9/data.py` unedited with a scratch seed). Cluster of row i is i // 16. Set A is rows 0–4,095, which are code clusters 0–255, not "1–256". A `TrainingStream` over A or B holds only that set's facts, one cluster per context, 32 updates per epoch, and exactly 512 exposures per fact after 16,384 updates. Mixed-cluster octets do not straddle the boundary (256 mod 8 = 0).

**Fix [lead's choice]:** (a, recommended) **drop Q3** and move its design into the proposal of the integrated study, with the corrections below. Or (b) keep it and paste:

> §8.5, Q3 labels: for each arm, its retention ratio ρ = set-A accuracy after phase 2 / set-A accuracy at S_A, per draw and panel, printed with both levels.
> | **RETAINS AS WELL AS ORACLE ADDRESSING** | in all four draws, ρ(candidate) ≥ 0.90 × ρ(A6) |
> | **OLD FACTS RETAINED (ABSOLUTE)** | in all four draws, ρ(candidate) ≥ 0.90 [lead's choice] |
> SEQUENTIAL-STABLE requires both. §5.4: "SEQ-N is the shared-memory sequential setting. It is not S2's mechanism (i); the frozen-memory read is the nearest analogue of (i) available without a second memory." §5.4 set A: "code clusters 0–255 (fact rows 0–4,095 of the draw's 8,192-fact table)". The probe in phase 1 is the first 256 facts of A.

### M7. The interface with ADR-0021 is inconsistent, and the lane will probably be omitted

**Findings.**

- **(a)** ADR-0021 §5.6 runs F-LA on 2K/4K, 8K/4K and 8K/16K, and its only step is A1 = 8K/4K → 8K/16K. Without OVERLOAD-QUALIFIED, S0 §9.1 forbids 8K/4K, so the lane can form no step at all. Yet §9.1 row 2 says "S1's lane cells 2K/4K, 8K/4K, 8K/16K are covered".
- **(b)** §9.1 row 1 offers 65,536 cells that the lane does not have (M3).
- **(c)** Update counts. S0 qualifies at 4·F updates, with 32,768 at both 8K cells, so step A1 is matched within the lane. ADR-0021's classes are read at U_P (8,192 or 16,384) with run lengths of 2–3·U_P, so "the ratio of F-LA's to F-OQ's retained bits per cell" compares different update counts unless F-OQ is read at a matching snapshot.
- **(d)** Acceptance. ADR-0021 requires the outcome to be "accepted by the human lead". S0 requires only the auditor's recomputation.
- **(e)** Success rule. ADR-0021's "S0's own cell-success rule at 2K/4K or 8K/16K" omits 8K/4K. That rule also needs the calibration-stream probe (condition 3), H1/H2 (condition 4) and the read swap (condition 6) to be recorded in S1's F-LA cells.
- **(f)** Timeline. S0 cannot freeze before P9-II's outcome is recomputed. S1 does not wait and freezes after its own calibration, rehearsal and the human lead's decision 2. Unless P9-II and S0's Q1 finish first, lane L is OMITTED, and by §9.2 a later qualification changes nothing in S1. "Learned addressing evaluated separately if qualified" is then met only by a later study (P10-I or the integrated study). The human lead should be told this plainly.

**Fix (paste-ready), §9.1:**

> | ADDRESSING-QUALIFIED (4,096 AND 16,384) | the qualified arm exactly as S0 froze it (S0's code hash and P9-II's calibrated value from the arm-selection record; no tuning), at 2K/4K and 8K/16K, and at 8K/4K only if OVERLOAD-QUALIFIED; each cell run for 4·F updates (8,192 at 2K/4K; 32,768 at 8K/4K and 8K/16K). **Without OVERLOAD-QUALIFIED, no step of the lane can be formed, and the lane prints OMITTED — NOT OVERLOAD-QUALIFIED.** The lane's cells record S0's probe set, H1/H2 and the read swap, so that S0's cell-success rule (including the 8K/4K rule of §8.2) can be applied. S1's own rule (ADR-0021 §5.6) decides whether a human acceptance is also needed | … | … |

New §9.4:

> **Expected timeline, stated for the human lead.** S0 freezes only after P9-II's outcome is recomputed. S1 and S2 do not wait. If S1 freezes before S0's Q1 label is recomputed, S1's lane is omitted, and learned addressing is evaluated with capacity only in a later study that needs the human lead's review (§9.2).

The cross-reference corrections for ADR-0021 and ADR-0022 are listed in §6 (item F).

---

## 3. Minors (paste-ready where short)

- **m1 (§6.4, bounds).** At 2K/4K, RELIABLE allows one failed cell of twelve. Counting a draw as a success only when both its cells succeed, RELIABLE guarantees 5 of 6 draws, a bound of 0.418, not 0.61. Add: "At 2K/4K a draw succeeds when both its cells succeed; the printed bound uses that count."
- **m2 (§8.6 hypothesis readings).** H20-S/O/Q/L must name the arm they are read on. If X2 is the qualified arm, WX was trained on C, not on X2. Add: "H20-S, H20-O and H20-Q are read on the qualified arm (C or X2). H20-L is read on WX(C) and is printed NOT TESTED FOR X2 when X2 is qualified."
- **m3 (§10.4).** "At the W7 registered rate the two need 8.7 h": by the table's own numbers, 2 × (3.9 + 0.3) = 8.4 h (c1: 8.42). Either correct it or state what the 0.3 h difference covers.
- **m4 (§10.4 memory).** There is no rule for a rehearsal peak above 1.5 GiB. Add: "If the rehearsal peak of a stage's configuration exceeds 1.5 GiB per worker, that stage is NOT RUN — MEMORY; nothing is changed to make it fit." Note A4 at k = N = 65,536: a gathered value tensor of 1.00 GiB (c1).
- **m5 (§0, "S0 has no calibrated quantity").** True, but the values λ, U_pre, k_0/N and μ were calibrated on W7 at 4,096. At 65,536, at load 2, in WX and in Q3 phases they are untested transfers. Add to §15: "A failure at a new condition is a failure of the recipe as calibrated at 4,096 on W7, not necessarily of the arm."
- **m6 (WX).** (i) The fan-in-2,048 initializer gives the window columns about 224/2,048 ≈ 11% of the initial query variance, so the initial query is dominated by other records. (ii) Under AdamW the per-step change of z scales with the number of active input columns, about 9× W7's at lr 0.003, and lr is not re-tuned. WX DOES NOT PASS is therefore not evidence that the record length is needed. Add to §8.6 item 7: "A failure of WX is not evidence that the record length is required; H20-L is 'not supported', never 'contradicted'." The remaining answer-position leak is correctly disclosed (§5.2); keep the AUROC descriptive.
- **m7 (a_use ties).** Define: "the swapped prediction counts as the fact's answer if that answer is among the arg-max symbols" (the conservative side, as "ties wrong").
- **m8 (Q3 indices).** "Clusters 1–256" → "code clusters 0–255 (rows 0–4,095)". The phase-1 probe is the first 256 A facts (also in M6).
- **m9 (Q3 schedules).** Restarting A4's schedule in phase 2 restarts a wide soft read over N/8 or N slots, which writes B gradients into A's values. Restarting A2 re-runs L_addr-only training of the query on B. Both choices strongly affect retention. Either keep them and say so in §5.4, or continue at the end-of-phase-1 setting (k = 8; answer-only) [lead's choice].
- **m10 (seeds; G9).** "910001 upward" (P9-II) and "921001 upward" (S1) are open-ended. With P9-I's convention `TEST_SEED_BASE + 100·offset` (`studies/p9i/core.py:351`), P9-II's tests reach 920001 at offset 100. Paste: "G9 reads P9-II's actual test seeds from its committed code at S0's freeze and asserts them disjoint from 920001–920999. S1's tests are taken as 921001–921999 and S2's as 229001–229999."
- **m11 (S2 naming).** ADR-0022 §10 writes "s_c(S0)" for its untrained-student Stage 0. Rename it "s_c(Stage 0)" so that it cannot be read as this study.
- **m12 (S1's G9 list).** ADR-0021 §6.3 must list S0 (200001–209999, 2001–2002, 2091–2092, 920001–920999) and correct P9-II to 190001–191599. ADR-0022 §9 "every seed of P1–P9-II" must add S0 and S1.
- **m13 (governance of the integrated study).** §9.2 says a late qualification goes "to the fourth, integrated study … or to P10-I, which needs the human lead's review". This implies the integrated study might be self-approvable. The human lead said follow-up changes after P10 are P10-I. Paste: "The integrated study is a P10-I item and needs the human lead's review."
- **m14 (shared machine).** S0 18 GiB plus S1 18 GiB plus S2 on a 48 GB machine is not budgeted jointly anywhere. Add to §17 item 4: "and the aggregate memory of concurrent P10 studies".
- **m15 ("resistance to query collapse").** Condition 3 at the readout counts "collapsed and recovered" as resistant. Add the descriptive line "COLLAPSE-FREE: k of n counted cells never had a collapse onset", so the reader can see the difference.
- **m16 (pairing).** On even draws A6 and A7 use seed 2001 while the learned arms use 2002. Say "references are draw-paired, not seed-paired" in §6.1.
- **m17 (LM print form).** Carry over ADR-0019's "UNRELIABLE (LM CAPABILITY REDUCED)" so that the flag is visible in the class (R7 of the ADR-0019 confirmation).
- **m18 (S2 supplement wording).** ADR-0022 §5.4's "separately approved supplement" should read "a supplement approved by the human lead (ADR-0020 §17 item 3)".
- **m19 (seeds verified, positive).** The seed-context search found no use of 200001–209999, 2001, 2002, 2091, 2092 or 920001–920999 (nor of S1's, S2's or P9-II's declared ranges) in `studies/`, `configs/`, `src/`, `tests/`, `results/`, `supplements/`, `docs/`, `templates/`, `prompts/` or `/Users/daniellaloush/dandush03/ArborLM/experiments` (14,155 text files). The only hits, in `results/p5-2026-11-13/audit/independent-arithmetic-attempt-04.stdout`, are count arrays, not seeds. The positive control found P9's and P9-I's known seeds with the same method. P1–P8 compute seeds additively (bases 0, 42–44, 101–303, 401–603, 601–602 plus offsets 1,000–80,000, 9,001, 10,001). None of these sums is 2001, 2002, 2091 or 2092, or lies in 200001–209999. The nearest are 2000 (baseline 0 + 2,000), 2042–2044 and 2401–2503. The audit-time obligation of §7 is met for the namespace. G9 must still assert it in code.
- **m20 (alternatives, §12).** Item 1 ("contrastive query encoder") needs two contexts of a fact per batch, which ADR-0019 §4 excluded for A0 because it changes data access. Say so, so that a later comparison with A0 is not presented as matched.

---

## 4. What I checked and confirmed (no change needed)

- Per-draw one-sided 95% Clopper–Pearson bounds: 6/6 0.6070, 5/6 0.4182, 4/4 0.4729, 3/3 0.3684, 10/10 0.7411, 14/14 0.8074 (and P9-II's 8/8 0.6877, 7/8 0.5293). All as printed.
- Cell counts 126 / 102 / 102 / 78 / 90 / 72 and 54 (c1).
- Q1 summed hours 7.54 / 8.63 / 10.98 and makespan 1.26 / 1.44 / 1.83; Q2 131,072 × 0.035 / 0.0531 / 0.0619 s = 1.274 / 1.933 / 2.254 h per cell, 12 cells 15.3 / 23.2 / 27.0 h, two rounds 2.55 / 3.87 / 4.51 h; Q3 1.89 / 2.05 / 2.84 h; Budget B at the slowest rates 2 × (0.47 + 4.51) = 9.96 h against 10 h. All as printed apart from m3.
- Exposures: 4·F updates × 128 / F = 512 at every size. Q2's snapshots are at 32 and 128 exposures; Q3's phases at 512.
- Seed layout: 15 sets with bases 200001–201401, all offsets used fall in 200001–201472 (< 201499). P9-II rev4's maximum seed is 191562, so ADR-0021's 190001–190733 is wrong (m12).
- The read swap and condition 6 (item C): no degenerate system passes. A collapsed or memory-free system has a_use ≈ 0. For a well-addressed memory at A6 ≈ 0.5, the swapped read gives answer(f) by coincidence with probability about 0.5/31 ≈ 0.016, so a_use/accuracy ≈ 0.98 and 0.95 is reachable. π is a derangement with different answers, and each fact occurs once per panel (a cluster's two panel contexts partition it), so "π(f)'s own panel context" is unique.
- The lowered oracle floor at 8K/4K (A6 ≥ 0.50, ratio 0.90): not a relaxation that lets an arm qualify. It enters only OVERLOAD-QUALIFIED, which gates only S1's 8K/4K cell. Whether A6 reaches 0.50 at load 2 is unknown (P9-I had load 0.5 only). If it does not on two or more draws, OVERLOAD is NOT_EVALUATED, and by M7(a) the lane is omitted. PENDING LEAD REVIEW: the lead should expect that possibility, not tune for it.

---

## 5. Answers by item

**A. Mapping.** Complete over every class combination I enumerated, and the rule agrees with the table wherever the table covers a case. It is not deterministic in the c16 overlap, it mislabels exclusions, and the table omits two families (M1). No branch lets S0 data choose an arm. The arm-selection record precedes generation and the freeze, and §3.1 admits no accuracy or Stage-3 label. The only "retry" is SMALL scope's 8K/4K cell (M2). "S0 does not run when P9-II is UNRELIABLE or FAILS" is consistent with "If no interface qualifies, stop … return with architectural alternatives". It is statistically right: an arm with two or more failed cells of sixteen cannot be made reliable by new draws without a pooled rule. But it makes S0 data-free in those rows and leaves the requested comparison to P9-II. That is the human lead's call (B1). On which scenario is likeliest: from the exploratory evidence (W7 escaped at 4,096 in 9 of 11 runs, 0.04 at 16,384 by 8,192 updates; L_addr gradients 55–285× answer-only) I expect "reliable at 4,096 only" or a supervised arm reliable at both sizes more often than rows 7–8. In the first case the current draft runs a SMALL-scope S0 whose label nobody can use (M2). That expectation is my judgment, not a measurement.

**B. Additions.** Replication on new draws: needed and well defined. 6 draws gives a bound of 0.61 (0.42 at 2K/4K worst case, m1). Matched exposure at 65,536: well defined, underpowered as a label, unused by siblings (M3). S1's grid conditions: 8K/4K is needed and is the only thing S1's lane step needs beyond 2K/4K and 8K/16K, but B2 and M7(a) must be fixed. Q3: well defined in the generator (c4), but the label overclaims and nobody consumes it (M6). WX: well defined, informative only when it passes (m6). Missing: a statement of what happens to S1's lane in the expected timeline (M7f), and a P9-II-criteria class (M4).

**C. Labels.** Precedence tables are first-match and complete. "Qualified at 65,536" should be an annotation (M3). The read-swap condition and the 0.50 floor are sound (§4). No degenerate passer found.

**D. Q3.** It tests the shared-memory sequential setting, not S2's mechanism (i), apart from the frozen-memory read. Retention is measured against the right reference for "no worse than oracle addressing", but without normalisation by S_A and under a label name that claims more (M6). The draft is honest that S2 uses a different student and cannot consume the label (§9.1, §15).

**E. WX.** Fair as a superset test, informative in one direction only. A pass shows the recipe does not need the told window. A fail is confounded by 9× parameters, initial query dominated by non-window content, and an untuned learning rate (m6). It can be annotated as PASSES / PASSES AT 4,096 ONLY / DOES NOT PASS (not evidence of need) / NOT RUN. The answer-position leak remains in every arm and is correctly carried in the fixed sentence.

**F. Sibling use and cross-references.** The late-qualification rule (§9.2) is consistent with ADR-0021 §5.6 item 5 and ADR-0022 §5.4. The per-label table is not (M7). The corrections are in §6 below.

**G. Matrix, projections, budgets, gates, seeds.** Arithmetic confirmed (§4). Q2 at 131,072 updates × 0.035–0.053 s = 1.27–1.93 h per cell (2.25 h at 0.0619). Budget A (6 h) has ample headroom: 2 × 1.83 + about 0.7 h. Budget B (10 h) is exactly full at the slowest rates, and any unmeasured overhead (L_addr's all-key backward, A4's wide read, probes, read swap) triggers cut 1. The cut order is fixed and mechanical. The no-calibration claim is true but hides untested transfers (m5). G10 must be an independent recomputation (M1). Stop rules are adequate apart from memory (m4). The seeds are unused (m19), and the test ranges must be bounded (m10). The cluster split holds in the generator (c4; indices m8).

**H. "Stop capacity-scaling claims".** See §7.

**I. Smaller study.** See §8.

---

## 6. Cross-reference corrections between the three drafts (item F)

| Where | Now | Correction |
|---|---|---|
| ADR-0021 header, line 10 | "S1 does not wait for S0 (ADR-0019)" | "S1 does not wait for S0 (ADR-0020)" |
| ADR-0021 §5.6 item 1 | "S0 (ADR-0019) has a registered outcome ADDRESSING-RELIABLE with an interface carried forward, recomputed by the auditor and accepted by the human lead" | "S0 (ADR-0020) has a registered outcome ADDRESSING-QUALIFIED (4,096 AND 16,384) (ADR-0020 §8.6 as revised) **and OVERLOAD-QUALIFIED**, the Q1 stage recomputed from raw records by the auditor [and accepted by the human lead — lead's choice; must match ADR-0020 §9.1]" |
| ADR-0021 §5.6 item 2 | "S0's calibrated settings … each run to S0's qualified update count for its slot count" | "the P9-II calibrated value recorded in S0's arm-selection record … each run for 4·F updates, F the cell's fact count (8,192 at 2K/4K; 32,768 at 8K/4K and 8K/16K), as ADR-0020 §5.3; F-OQ's comparison snapshot is read at the same update count" |
| ADR-0021 §5.6 item 3 | "fails S0's own cell-success rule at 2K/4K or 8K/16K" | "fails S0's own cell-success rule (ADR-0020 §8.2, with the 8K/4K rule there) at any of its three cells; F-LA cells record S0's probe set, H1/H2 and the read swap" |
| ADR-0021 §6.3 | "ADR-0019's declared ranges (190001–190733, 1891, 1901–1902)" | "ADR-0019's declared ranges (190001–191599, 1891, 1901–1902, tests 910001–919999 as committed); ADR-0020's (200001–209999, 2001–2002, 2091–2092, 920001–920999); ADR-0022's (220001–229999)" |
| ADR-0021 §6.3 | "Unit tests: 921001 upward" | "Unit tests: 921001–921999" |
| ADR-0022 §9 | "disjoint … from every seed of P1–P9-II" | "… of P1–P9-II, ADR-0020 (200001–209999, 2001–2002, 2091–2092, 920001–920999) and ADR-0021 (210001–219999, 2101–2105, 2191–2192, 921001–921999)" |
| ADR-0022 §10 | "s_c(S0)" | "s_c(Stage 0)" (m11) |
| ADR-0022 §5.4 | "a separately approved supplement" | "a supplement approved by the human lead (ADR-0020 §17 item 3)" |
| ADR-0020 §7 G9 | "P9-II (… tests from 910001); S1 (… tests from 921001)" | "P9-II (…, tests as committed in P9-II's code, asserted within 910001–919999); S1 (…, tests 921001–921999); S2 (220001–229999, tests 229001–229999)" |
| ADR-0020 §9.1 rows 1–2 | "4,096, 16,384 and 65,536 slots"; "S1's lane cells 2K/4K, 8K/4K, 8K/16K are covered" | as M7 fix; 65,536 removed; 8K/4K only with OVERLOAD-QUALIFIED, otherwise OMITTED |
| ADR-0020 §9.3 | lists two inconsistencies | add: ADR-0021's lane needs 8K/4K for its only step; update-count mismatch with U_P; human acceptance rule; ADR-0022 "S0" collision |

---

## 7. Item H: the reading of "stop capacity-scaling claims"

Applying the sentence to learned addressing only, and letting S1/S2's oracle-addressed outcomes stand, is a fair reading of the human lead's later update. He made S1 and S2 independent and controlled-addressed, which only makes sense if their outcomes can stand on their own. It is not the only reading. S1's CAPACITY-POSITIVE [ORACLE-ADDRESSED …] is itself a capacity-scaling claim, about the store, and the original sentence did not distinguish store from system. Recommended wording for the human lead (also B1(c)):

> **If S0 qualifies no interface:** (1) No capacity-scaling claim is made for ArborLM as a system, and none under learned addressing. (2) S1's registered outcome is reported only as a property of the memory store given an external address, always printed with "ORACLE-ADDRESSED — NO LEARNED ADDRESSING QUALIFIED (ADR-0020)", and is never summarised as "ArborLM's capacity scales". (3) S2's outcome is reported as oracle-assisted, as ADR-0022 already requires. (4) The lead reports an addressing failure and returns §12. Please confirm this reading, or say that S1's capacity labels are also withheld.

---

## 8. Item I: the smallest version that still serves as the gate, and the recommended matrix

The gate needs three things: replication of C at the two sizes S1's lane uses with draw and seed variation, the 8K/4K cell that S1's lane step needs, and the controls that make the criteria computable (A0 for the paired label, A6 for condition 1, A7 for DENSE COMPARISON).

**MIN (78 cells; 54 when C = A0), six new draws, init seeds 2001/2002:**

| Cell type | Learned arms | Draws × seeds | References |
|---|---|---|---|
| 2K/4K | A0, C | 6 × 2 = 12 each | A6, A7 × 6 |
| 8K/16K | A0, C | 6 × 1 (alternating seeds) | A6, A7 × 6 |
| 8K/4K | A0, C (not for A1/A2 under B2(a)) | 6 × 1 | A6 × 6 (A7 not needed) |

Projected training: 4.8 / 5.5 / 7.0 CPU-h summed at the fastest / W7 / slowest rates. Makespan with six workers 0.80 / 0.91 / 1.17 h (`c3_smaller_matrix.py`).

**Recommended (REC, 90 cells):** MIN plus the second initialization seed at 8K/16K for A0 and C (+12). This answers "multiple initialization seeds" at the size S1's lane needs most, and gives 12 cells per arm at both core sizes. 6.2 / 7.0 / 9.1 CPU-h; makespan 1.04 / 1.17 / 1.52 h. One Budget of [4] charged hours [lead's choice] covers it with 2× headroom.

**Optional blocks, in this cut order [lead's choice]:** X2 (+24 cells, 0.23–0.33 h makespan; keep it if the human lead's answer to B1(b) wants a second supervision class in S0); WX(C) (+18 cells, 0.15–0.23 h; annotation only); a 65,536 annotation probe of C and A6 × 3 draws (6 cells, one round, 1.3–2.3 h; M3).

**Not in the gate:** Q3 (M6), SMALL scope (M2), A0 and A7 at 65,536 (M3).

The draft's largest configuration projects 24.7 / 33.9 / 40.9 CPU-h (makespan 4.1 / 5.6 / 6.8 h). REC with all three optional blocks projects about 9 to 13 CPU-h of training plus the 65,536 probe round.

---

## 9. Items I could not check or chose not to check

- Whether P9-II's analysis will in fact print classes for a non-COMPLETE Stage 2 (M1a). This depends on P9-II's not-yet-written code. The fix makes the question moot.
- A6's accuracy at load 2 and its forgetting under SEQ-N. Measuring either would mean training, which I do not do.
- Real per-update costs of L_addr, A4 and WX at 65,536. The rehearsal must measure them.
- The human lead's direction texts are quoted from the task message. They are not in the repository (the evidence inventory found no P10 text).

## 10. Commands, environment and outputs

Environment: macOS Darwin 27.2.0 arm64. `python3` 3.15.1 for scripts c1–c3 and s1–s3 (standard library only). `uv run --locked python` (Python 3.12.14, torch 2.8.0, the worktree's `.venv`) for c4. Worktree `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1` at `ecd5b87`. Review folder R = `/private/tmp/claude-501/-Users-daniellaloush-dandush03-ArborLM--claude-worktrees-arborlm-consolidation-experiment-2b31c1/cfc0efd5-b7ca-4602-959a-07fe6b8d4e7d/scratchpad/adr-0020-review`.

| Script (in R) | Command | Output (in R/outputs) |
|---|---|---|
| `c1_bounds_projection.py` | `python3 -I c1_bounds_projection.py` | `c1_bounds_projection.txt` |
| `c2_mapping_enumeration.py` | `python3 -I c2_mapping_enumeration.py` | `c2_mapping_enumeration.txt` (attempt 2) |
| `c3_smaller_matrix.py` | `python3 -I c3_smaller_matrix.py` | `c3_smaller_matrix.txt` |
| `c4_q3_split.py` | `cd <worktree> && PYTHONPATH=<worktree> uv run --locked python R/c4_q3_split.py` (scratch seed 777001) | `c4_q3_split.txt` (attempt 2) |
| `s2_seed_context_search.py` | `python3 -I s2_seed_context_search.py <worktree>/{studies,configs,src,tests,results,supplements,docs,templates,prompts}` and `… /Users/daniellaloush/dandush03/ArborLM/experiments` | `s2_seed_context_repo.txt`, `s2_seed_context_experiments.txt` |
| `s3_positive_control.py` | `python3 s3_positive_control.py <worktree>/{studies,tests,results} /Users/daniellaloush/dandush03/ArborLM/experiments` | `s3_positive_control.txt` |

**Failed attempts, kept:**

1. `s1_seed_search.py` → `outputs/s1_seed_search_repo_ATTEMPT1_FAILED_noisy.txt`. A bare-number regex matched digits inside hex hashes and timing values. Not evidence; superseded by s2 (see `outputs/ATTEMPT1_NOTE.txt`).
2. `c2_mapping_enumeration.py` attempt 1 → `outputs/c2_mapping_enumeration_ATTEMPT1_artifact_nc16.txt`. My enumeration let NEGATIVE CONTROL FAILED at 16,384 be printed when Stage 2 never ran (my error, not the draft's). Fixed in place; the conclusions did not change (the exclusion-only count moved from 11,776 to 7,168 records for the 16,384-status row).
3. `c4_q3_split.py` attempt 1 → `outputs/c4_q3_split_ATTEMPT1_FAILED_import.txt`. `ModuleNotFoundError: studies`, because the script's directory, not the working directory, is on `sys.path`. Re-run with `PYTHONPATH`.
4. Editing this file's header: an unquoted shell heredoc expanded the back-ticked hashes and blanked the line; two hash tails I then typed by hand were wrong. Replaced by sha256 prefixes and `outputs/input_hashes.txt` (computed by `shasum -a 256`). No finding depended on it.

Astra review: NOT_PERFORMED. This review is not an Astra review and not a human approval.
