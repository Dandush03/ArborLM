# Re-check of ADR-0020 revision 3 (P10-S0) against E1–E10 and against P9-II's actual records

**Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.**

Intended location: `docs/reviews/p10-design-2026-11-15/adr-0020-review/RECHECK_REV3.md` in worktree `p10-design`. The session's worktree-isolation hook blocked the write there, so this file was written to the session scratchpad and must be copied unmodified.

- **Reviewer:** Claude Opus 5.5 (`claude-opus-5-5`). I wrote no part of ADR-0019–0022, of P9-II's code or records, or of the P9-II results audit. `CONFIRM.md` (E1–E10) was written by an earlier Opus 5.5 context. Some passages checked here are that text, applied verbatim; where it is defective, I say so.
- **Date:** 2026-11-15. Worktree `.claude/worktrees/p10-design`, branch `claude/p10-design`, HEAD `2ef6a4f`.
- **Inputs (sha256, first 8 hex digits):**
  - ADR-0020 rev3 `19d44458`; rev2 `62d16ed3`; `CONFIRM.md` `26c60df4`.
  - ADR-0021 `14236743`; ADR-0022 `a4fc3d02`; ADR-0019 `93913658`.
  - P9-II run records: `OUTCOME.md` `66946b87`, `classes.csv` `90457131`, `results.json` `9b2ca547`, `stage_gate_1.json` `14988c8a`, `stage_gate_3.json` `e60fae1d`.
  - P9-II calibration: `calibration.json` `ad5d7ee2`. P9-II results audit: `REVIEW.md` `e1697af3`.
- **Provenance.** ADR-0020 rev3 has one commit, `c56b23a` (2026-11-15 01:35 −0500). P9-II was frozen at `d2746d3` (03:47) and its run records were committed at `d72b173` (05:28). The rev3 rules and numbers were therefore fixed before any P9-II observation. Every later edit to ADR-0020 is made after observation: it must be editorial, and changes prompted by P9-II's results are for the human lead.
- **Ran:**
  - `git log`, `diff rev2 rev3`, `grep`, `shasum -a 256`.
  - Two read-only `python3 -I -c` one-liners on `results.json`: per-arm classes, `draw_counts` and LM flags.
  - One `python3 -I -c` arithmetic check: Clopper–Pearson bounds, cell counts, budget, seed maxima.
  - Environment: Python 3.15.1, standard library only, Darwin 27.2.0 arm64.
  - No training, no model, no network, no commit, no edit of any existing file.
- **Failed attempts (kept):**
  1. A `grep -o` with a long regex exceeded the ugrep complexity limit and printed nothing. I re-ran it as a plain `grep -n`.
  2. Writing this file into the `p10-design` worktree was refused by the session hook (see above).

## Verdict: READY SUBJECT TO the listed text edits

- R1 and R2 (major) are text edits needed before the lead's approval.
- R3–R10 (minor) should be applied in the same pass.
- None changes a threshold, an arm or the mapping.
- Separately, and **PENDING LEAD REVIEW / for the human lead**: given P9-II's actual outcome, S0 as written cannot qualify any label-free interface and cannot test A5-D (§3). This is a correct consequence of rules fixed before observation, not a text defect.

## 1. E1–E10 in revision 3 (every changed line of `diff rev2 rev3` read)

| Edit | Faithful? | Passage in rev3 (quoted) | New contradiction / ambiguity |
|---|---|---|---|
| **E1(a)** | Yes. Verbatim except "[two]" → "two **[lead's choice]**", my role's proposed value. | §8.5 (b): "P9-II did not print LM CAPABILITY REDUCED for X at that size, **and** at most two **[lead's choice]** draws failed among the evaluated draws of both studies. … at least 16 of 18 draws at 4,096 and 12 of 14 at 16,384." Order: "A0, then C4 (if present), then A2, then A1." | §8.7 row 5 lacks the new reason (R3). "X advanced" is ambiguous for A0 (R4). |
| E1(b) §6.3 | verbatim | "The pooled count enters exactly one rule, the consistency rule of §8.5, …" | The descriptive pooled line is underdefined (R7). |
| E1(c) H20-Q | verbatim | "At least one arm meets S0's criteria and is CONSISTENT ACROSS STUDIES at both core sizes (§8.5)." | none |
| E1(d) §8.7 row 6 | verbatim | "… (condition 6 or ADDRESS STABLE) and every arm that met S0's criteria but was INCONSISTENT ACROSS STUDIES, with P9-II's class and the pooled count." | Grammar: the clause can be read as falling under the "where …" clause (R10). |
| E1(e) §15 | verbatim ("two") | "That S0 overrides P9-II. An arm qualifies only if it is CONSISTENT ACROSS STUDIES (§8.5). …" | none |
| E1(f) §20 row 2 | verbatim | "Candidate from S0's classes subject to the consistency rule of §8.5 (rulings 1 and 3); preference order A0, C4, A2, A1." | none |
| E1(g) | verbatim plus one sentence | "The points were raised at the end of revision 2." | none |
| **E2** §9.1 row 1 | verbatim | "… cells 2K/4K and 8K/16K, and 8K/4K only if OVERLOAD-QUALIFIED (never for A1 or A2 …); … Without OVERLOAD-QUALIFIED the lane's 8K/16K-against-8K/4K difference is printed NOT AVAILABLE." | **Contradicts ADR-0021 rev3 §5.6** (R1). |
| E3 §3.3 | verbatim | "none (no label-free arm is carried; A0 may be, if RELIABLE at 16,384 only)" | none |
| **E4** §10.4 | re-check paragraph verbatim; cut swap written out | "After the Q1 gate the rule is evaluated once more … Cuts 1 and 2 are applied then, not before Q1. Cut 3 is decided before Q1." "Cut order … (fixed now, applied in this order; cut 3 recorded in the freeze, cuts 1 and 2 recorded at the Q1 gate): 1. Drop the 65,536 probe … 2. Drop WX … 3. Drop the second seed at 8K/16K" | **The pre-Q1 evaluation is not determined** (R2). The defect is in E4's own sentence (my role's earlier text). |
| E5 | verbatim, both places | §8.3 "UNRELIABLE and FAILS enter no rule; …"; §10.4 "With cut 3, a draw at 8K/16K succeeds when its one cell succeeds; …" | none |
| E6 §16 | verbatim | "A label-free arm that P9-II found RELIABLE at 4,096 but did not carry is not re-tested (§3.3, consequence)." | none. This is exactly the A5-D case (§3). |
| E7 | verbatim | "16 of 18 / 12 of 14 (pooled, the consistency threshold) \| 0.690 / 0.615" | recomputed 0.690 / 0.615 ✓ |
| E8 §9.3 | the lead's choice (921001–921999) | "ADR-0021 (revision 3, being written): …"; "ADR-0022 revision 4 — to be applied …" | Stale (R9). ADR-0021 rev3 has item 1 verbatim and 921001–921999 (its line 213), but its item 4 was rewritten by its own K7. ADR-0022 applied all four corrections at `2ef6a4f` (its line 5; S0's seeds at line 246). |
| E9 | verbatim | "The answer is required before any programme-level text, S1 report summary or S2 report summary cites S0's outcome (§17 item 3)." | none |
| **E10** G10 | verbatim | "the auditor's enumeration script `adr-0020-review/c5_rev2_mapping_and_consistency.py` (Part 1) is re-run on P9-II's committed records." | **Cannot be done as worded.** Part 1 enumerates a modelled space (`itertools.product(c2.CLS4, …)`) and opens no file (R5). The defect is in E10's own text. |

**§19's list of reworded passages is incomplete.** It omits:

- the header status and revision history;
- the §9.1 column header;
- the §9.2 parenthetical;
- §13 step 1;
- §18 "Lead's approval: PENDING.";
- §20 rows 5, 10 and 17;
- the closing heading.

I read all of them. None changes a rule or number. The §9.2 parenthetical is true of ADR-0021 rev3 item 2.

**Arithmetic after the edits:**

- **Cells.** Q1 = 180 (three learned arms) or 230 (four) ✓. Q2 = 26, so at most 256 + 3 ✓.
- **Six-worker hours.** 4.94 / 5.94 / 7.28 ✓. Doubled: 9.88 / 11.88 / 14.57. Left at the slowest rates: 1.43 h (8.9%) ✓.
- **Headroom multiples.** Uncut 1.110×, without the probe 1.701×, Q1 alone 1.849× ✓.
- **Bounds.** 0.741, 0.606, 0.717, 0.571, 0.493, 0.368, 0.847, 0.762, 0.807, 0.703 ✓.
- **Seeds.** Largest data seed 201280, and 201480 with the reserves ✓.
- **Unit-test ranges.** 920001–920999 and 921001–921999 do not overlap ✓.
- **Cost reason for the cut order.** The probe takes about 6.6× WX per round (2.25 h vs 0.34 h) ✓.

Editorial defects: a duplicated heading at line 527 ("## 20. … ## 20. …"), and line 5 still says "Revision 2 (this text)" (R10).

## 2. §3.2 applied mechanically to P9-II's records

| §3.2 step | Record | Result |
|---|---|---|
| 1 calibration | `calibration.json`: `"hyper":{"k0_fraction":0.125,"lambda":1.0,"mu":1.0,"u_pre":2048.0}`. Audited in `docs/reviews/p9ii-prefreeze-audit-2026-11-15/` (cited by the calibration `CORRECTION.md`) | exists → S0 runs |
| 2 outcome row | `results.json` `result.outcome`: `"outcome": "ADDRESSING-RELIABLE", "row": 4`; `assessment`: `"status": "COMPLETE"`, `"interpretable": true` | interpreted |
| 3 Stage 2 | `result.carried_forward.stage2_status: "COMPLETE"` | COMPLETE |
| 4 carried arm | `result.carried_forward: {"arm": "A0", …, "supervision": "(LABEL-FREE)"}`; `stage_gate_3.json "selected":"A0"`; `OUTCOME.md`: "Interface carried forward under the registered order: **A0**" | A0 → **no fourth arm** |

§3.3 row used: "ADDRESSING-RELIABLE, carried arm A0 (RELIABLE at 16,384, not at 4,096) | none (already in S0)". It matches `classes.csv`: `stage1,4096,A0,…,UNRELIABLE,16,4,12` and `stage2,16384,A0,…,RELIABLE,8,8,0`.

**S0's arm set:**

| Arm | Calibrated value | Cell types |
|---|---|---|
| A0 | — | 2K/4K, 8K/16K, 8K/4K |
| A1 | λ = 1.0 | 2K/4K, 8K/16K |
| A2 | U_pre = 2,048 updates at 2,048 facts, i.e. 8,192 at 8K/16K (§5.3) | 2K/4K, 8K/16K |
| A6 | reference | 2K/4K, 8K/16K, 8K/4K |
| A7 | reference | 2K/4K, 8K/16K |

- n_L = 3, so Q1 = 180 cells. The values k_0/N = 0.125 and μ = 1.0 are not used.
- **Fourth-arm label:** not fixed by the text. §3.2 item 4 says only "the reason is printed". The only fixed string, "FOURTH ARM: NONE — P9-II \<status\>" (item 2), is for a non-interpreted P9-II (R6).

**Other places ADR-0020 reads P9-II.** Failed draws = `0/2` + `1/2` in `results.json` `draw_sensitivity.draw_counts`.

| Arm, size | P9-II class (cells) | P9-II failed draws | §8.5 consistency (pooled ≤ 2) | §8.4 replication | Well defined? |
|---|---|---|---|---|---|
| A0, 4,096 | UNRELIABLE (4/16) | **6 of 8** | **INCONSISTENT whatever S0 observes** | comparable | yes |
| A0, 16,384 | RELIABLE (8/8) | 0 of 4 | S0 ≤ 2 failed of 10; or SINGLE-STUDY EVIDENCE if "advanced" excludes A0 | comparable | **ambiguous (R4)**. No effect on qualification. |
| A1, 4,096 | RELIABLE (16/16) | 0 of 8 | met whenever A1 is S0-RELIABLE | comparable | yes |
| A1, 16,384 | UNRELIABLE (6/8) | **2 of 4** | **S0 must have 0 failed draws** (P9-II criteria) | comparable | yes |
| A2, 4,096 | FAILS (0/16) | 8 of 8 | **INCONSISTENT whatever S0 observes** | comparable | yes |
| A2, 16,384 | none (`stage_gate_1.json "advancing":["A5-D","A1"]`) | — | (a): SINGLE-STUDY EVIDENCE | NOT COMPARABLE | yes. §6.3's descriptive pooled count has no P9-II part (R7). |
| LM flag | `lm_flagged_cells` 0 for every arm and size | — | met | — | yes |
| Negative control | `negative_control_failed: false`, both stages | — | A1/A2 classes read; "not failed" printed | — | yes |

**Consequence (rules fixed before observation):**

- Neither A0 nor A2 can become the candidate at any scope.
- **Only A1 (address-supervised) can be qualified.**
- At both sizes this requires A1 RELIABLE and ADDRESS STABLE under S0's criteria, with **zero** failed draws at 16,384 under P9-II's criteria. That is stricter than S0's RELIABLE.
- P9-II's F4 (an A1 failure by half a fact) is one of the two P9-II failed draws.

## 3. Findings

**Major:**

- **R1 — §9.1 row 1 (E2) contradicts ADR-0021 rev3 §5.6.**
  - ADR-0021 rev3 item 2 says: "**OMITTED — NOT OVERLOAD-QUALIFIED** … **OMITTED — SUPERVISED ARM HAS NO 8K/4K CELL** (candidate A1 or A2)". Its item 4 runs the lane "at 2K/4K, 8K/4K and 8K/16K … 15 cells".
  - ADR-0020 says the lane runs 2K/4K and 8K/16K without OVERLOAD-QUALIFIED and prints NOT AVAILABLE.
  - Two Opus confirmations (E2 here; K7 in `adr-0021-review/CONFIRM.md`) issued contrary paste texts.
  - A1 is the only arm S0 can qualify, so the contradiction falls on the reachable case. AGENTS.md requires a recorded decision.
  - **Edit:** replace the S1 cell with "As ADR-0021 §5.6 (revision 3) defines lane L, items 1, 2 and 4; this ADR states no lane rule of its own", and update §9.3.
- **R2 — the pre-Q1 headroom evaluation is not determined (§10.4).**
  - The start rule counts "everything still to run" (WX and the probe included). Cuts 1–2 cannot be applied before Q1, yet the cuts are "applied in this order".
  - If only the probe makes the pre-Q1 check fail, there are two readings:
    - (A) assume the probe cut and start uncut;
    - (B) only cut 3 is available, which halves the 8K/16K seeds or, under item 4, runs nothing. Reading B violates the stated order.
  - The uncut plan absorbs only 1.11× the slowest P9-I rates, so this case is plausible.
  - **Edit [lead's choice; A is the reading consistent with the order]:** "Before Q1 the rule is evaluated on Q1 and the stages before it only. If it does not hold, cut 3 is applied; if it still does not hold, item 4 applies. After the Q1 gate the rule is evaluated on WX and the probe with the actual candidate's rehearsed rates and the hours charged, and cuts 1 and then 2 are applied as needed."
  - Also say whether "most expensive possible candidate" means {A0, A1, A2} a priori. Conservative; after the mapping only A1 can be the candidate.

**Minor:**

- **R3 — §8.7 row 5 omits the reason added by E1.** Append "or INCONSISTENT ACROSS STUDIES (P9-II \<class\>; pooled \<failed\> of \<n\>)". This is A1's route to "4,096 ONLY" after any failed S0 draw at 8K/16K.
- **R4 — "X advanced" is ambiguous for A0.**
  - ADR-0019 line 98 says "A0 alone advances", but line 212 says "A0 runs at Stage 2 whenever Stage 2 is run. Besides A0, …". The record's `advancing` list excludes A0. §8.4 uses "has no class".
  - **Edit**, if the lead confirms the meaning: "and X has a Stage 2 class at the 4U readout".
- **R5 — G10's second clause is not executable.** Delete it; the first clause suffices, and §2 here is one such evaluation. Or reword: "Part 1 is re-run and the table cell matching P9-II's committed outcome is cited."
- **R6 — no fixed fourth-arm string, and the F1 annotation is missing.**
  - Add the string "FOURTH ARM: NONE — P9-II CARRIED \<arm\> (ALREADY IN S0)".
  - P9-II's F1 ruling (`OUTCOME.md`) requires its annotation "wherever it is cited". The arm-selection record and S0's label cite the carried arm and should carry the annotation verbatim. This attaches a recorded ruling; it is not a rule change.
- **R7 — the descriptive pooled count in §6.3 is underdefined.** It does not say which criteria it uses, and it is "printed … always" where P9-II has no cells (A2 at 16,384). **Edit:** "under P9-II's criteria; NOT AVAILABLE where P9-II has no class".
- **R8 — P9-II's human acceptance is pending.** `OUTCOME.md`: "Not accepted by the human lead". §14 stops S0 if P9-II is amended after S0's freeze. ADR-0020 does not require acceptance before freezing. Timing is **PENDING LEAD REVIEW**.
- **R9 — §9.3 is stale.** ADR-0022 is corrected (`2ef6a4f`). ADR-0021 rev3 exists, and its item 4 differs from E2's sibling edit.
- **R10 — editorial.**
  - Line 5: "Revision 2 (this text)" → "Revision 2".
  - Line 8: keep it, adding "(written at `c56b23a`, before P9-II's run records `d72b173`)".
  - §11's "may start before P9-II's registered run finishes" is moot.
  - Remove the duplicated §20 heading.
  - Complete §19's list.
  - §8.7 row 6: write "; and also every arm that met S0's criteria but …".

**Consequences of the actual outcome.** These are stated only; changes prompted by them belong to the human lead.

- **The 8K/4K block is descriptive only.** A0 × 10 and A6 × 10 at 32,768 updates (20 of 180 Q1 cells) feed only A0's printed class. A0 cannot be the candidate, and A1 has no 8K/4K cell. OVERLOAD therefore prints NOT RUN — NO TARGET INJECTION, and H20-O is "not tested" in every reachable outcome.
- **WX (H20-L) and the 65,536 probe (H20-S)** can run only if A1 qualifies at both sizes.
- **No label-free qualification is possible.** "(LABEL-FREE)" cannot appear in outcome rows 4–5.

**A5-D (the label-free diversity penalty) under S0 as written:**

- **Cannot answer:**
  - whether P9-II's result for A5-D (16/16 at 4,096, 8/8 at 16,384; the only label-free arm RELIABLE at both sizes) replicates on ten new draws;
  - whether it meets S0's stricter criteria (read swap, ADDRESS STABLE);
  - whether it holds at two facts per slot;
  - whether it holds with a query not told the record length;
  - what it does at 65,536 slots at 512 exposures per fact.
- The reason: A5-D is not an S0 arm. The carried arm is A0, so §3.2 admits no fourth arm. The §3.3 consequence and §16 row 1 state this case.
- **Can answer** only:
  - whether answer-only training (A0) is again unreliable at 4,096 and recovers at 16,384;
  - whether address supervision (A1) replicates and meets S0's criteria;
  - whether staged optimization (A2) replicates.
- S0 cannot compare A5-D with anything.
- P9-II's F1 ruling leaves "A0, A5-D or both" to "that study's own specification and approval". ADR-0020 answers it mechanically (A5-D excluded), by a rule fixed before observation. **Changing that requires the human lead.**

Astra review: NOT_PERFORMED. This review is not an Astra review and not a human approval.
