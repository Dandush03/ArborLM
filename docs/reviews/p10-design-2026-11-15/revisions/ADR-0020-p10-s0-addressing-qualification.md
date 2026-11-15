# ADR-0020 — P10-S0: Addressing qualification for the P10 programme

- **Status: DESIGN REVISION 1 — DRAFT FOR THE LEAD, NOT YET REVIEWED. SPEC: PENDING ASTRA REVIEW. Nothing is implemented, rehearsed or run. No approval exists.**
- **Date:** 2026-11-15 (UTC)
- **Study code:** P10S0. Package `studies/p10s0/`. Config `configs/p10s0_qualification.toml`. Tests `tests/test_p10s0_*.py`. Launch scripts `studies/p10s0/launch/`.
- **Origin.** The human lead's P10 direction: "Addressing remains a mandatory prerequisite. Incorporate the most promising P9-II addressing interventions as a qualification gate rather than assuming they have succeeded." and the later update that S0 (robust addressing), S1 (capacity, ADR-0021) and S2 (transfer, ADR-0022) are "three parallel, scientifically independent experiments". This document is S0 only.
- **Evidence it rests on.** P9-I (ADR-0017 Part I): COMPLETE — NO_INTERFACE_SELECTED, accepted by the human lead as a registered negative result (ADR-0017 §15.9); `results/p9i-run-attempt2-2026-11-15/OUTCOME.md`; `docs/reviews/p9i-results-2026-11-15/REVIEW.md`. P9-II (ADR-0019 revision 4): **not yet run**. This text is written before any P9-II observation exists and uses no P9-II result. Diagnostic runs of the two reviews are exploratory and enter no rule.
- **Roles (study-specific).** Lead: Claude Fable 5.2. Specification review, implementation audit and recomputation from raw records: Opus 5.5, in contexts separate from implementation, receiving code and records and not the lead's conclusions. Implementation: Sonnet 5.5. Inventory: Haiku 5.5. The model that actually ran each delegated task is recorded from session metadata. ADR-0012 stays not approved. **Astra review: NOT_PERFORMED.** A Claude review is neither Astra validation nor a human approval.
- **Relation to other work.** P9-II runs and is committed first. S0 imports `studies.p9ii`, `studies.p9i` and `studies.p9` unedited. S1 and S2 do not wait for S0, and S0 uses no result of S1 or S2. P1–P9-II code, configs, records and ADRs are not edited.
- **Marking.** Judgment-call numbers are marked **[lead's choice]**. "As ADR-0019 §x" means the definition of ADR-0019 revision 4 applies unchanged.

## 0. What S0 is, in one paragraph

P9-II asks which training method makes sparse addressing reliable. S0 does not ask that again. S0 takes the arm P9-II's registered outcome selects, by a mapping fixed here before P9-II runs (§3), and asks whether that arm is good enough to be relied on by the P10 programme: on new draws, at the fact and slot counts S1 uses, at matched exposure at 65,536 slots, under two facts per slot, when facts are added later, and when the interface is not told the record length. S0 has no calibrated quantity and tunes nothing. If P9-II selects nothing, S0 does not run and reports that addressing is not qualified.

## 1. What is known, and what is not

Registered (P9-I, one draw, two initialization seeds, 8,192 updates): oracle-query retrieval 0.967–1.000; every learned query interface at chance (0.028–0.044) with 1–6 distinct top-1 slots; the dense window control 0.78–0.80 at 16,384 slots and 0.13 at 65,536; block-0 attention trained with the memory reached 0.54–0.65 at 4,096 slots only, with the next-byte loss up 67–100%.

Exploratory (review diagnostics on other draws; not registered): collapse within 64 updates in every run; an escape that depends on the draw and hardly on the initialization seed (9 of 11 runs at 4,096 slots; none complete at 16,384 within 8,192 updates); a starved query-projection gradient in the collapsed state.

Not known, and the subject of P9-II: whether any training method is reliable across draws at 4,096 and 16,384 slots.

Not known, and not answerable by P9-II as designed (the subject of S0):

1. Whether a P9-II-reliable arm stays reliable in a second, independent study with its own draws.
2. Whether it works at 65,536 slots at matched exposure. P9-II Stage 3 gives 32 exposures per fact and can only be positive or uninformative (ADR-0019 §8.5), and it does not run at all for a scheduled arm.
3. Whether it works when the memory holds two facts per slot (S1's cell 8K/4K).
4. Whether it keeps addressing old facts when training continues on new facts (S2 is sequential).
5. Whether it depends on being told the record length (W7's seven-position window).

## 2. Question and hypotheses

**Is there a learned query–key interface that the P10 programme may rely on: fact-specific, not collapsed, memory-dependent, used without any oracle at inference, and reproduced on new draws and seeds under the conditions the P10 studies use?**

Let C be the candidate arm selected by §3. Each hypothesis can fail.

- **H20-R (replication).** C is RELIABLE (§8.2) on six new draws at 2,048 facts / 4,096 slots and at 8,192 facts / 16,384 slots, at 512 exposures per fact.
- **H20-S (scale at matched exposure).** C succeeds in 3 of 3 new draws at 32,768 facts / 65,536 slots at 512 exposures per fact.
- **H20-O (overload).** With 8,192 facts in 4,096 slots C keeps at least 0.90 of the oracle reference's accuracy and stays un-collapsed.
- **H20-Q (added facts).** After training continues on 4,096 new facts, the 4,096 old facts are still addressed and answered as well as under the oracle reference given the same sequence.
- **H20-L (record length).** The same training recipe applied to a query that sees the whole causal context, and is not told the record length, is RELIABLE at both core sizes.
- **H20-B (against answer-only).** C IMPROVES ON A0 (§8.3) at each core cell type. Not defined when C is A0.

H20-R failing means the P9-II result did not replicate; that is a registered negative and addressing is not qualified.

## 3. The mapping from P9-II's registered outcome to S0's arms (fixed now)

### 3.1 Inputs read from P9-II

Only these, from P9-II's analysis output as recomputed by the auditor and committed: the outcome row of ADR-0019 §8.6; each stage's status; for each learned arm X ∈ {A0, A5-C, A5-D, A4, A2, A1} its class at 4,096 (Stage 1) and at 16,384 (Stage 2, 4U readout); LM CAPABILITY REDUCED flags; NEGATIVE CONTROL FAILED flags; the calibrated values (λ, U_pre, k_0/N, μ). No accuracy, no per-draw table and no Stage 3 label enters the mapping.

### 3.2 Definitions

- **Excluded.** X is excluded if it prints LM CAPABILITY REDUCED at any size, or if X ∈ {A1, A2} and NEGATIVE CONTROL FAILED is printed at any size. A1-S is never a candidate.
- **Status at 16,384.** c16(X) = RELIABLE; or FAILED (UNRELIABLE, UNRELIABLE (LM CAPABILITY REDUCED) or FAILS, with Stage 2 COMPLETE); or UNTESTED (X did not advance, or Stage 2 is not COMPLETE, or X is NOT_EVALUATED there).
- **Full-scope set** E = non-excluded arms RELIABLE at 4,096 with c16 ≠ FAILED. **Small-scope set** E4 = non-excluded arms RELIABLE at 4,096 with c16 = FAILED.
- **Rank in E.** Tier 1 (c16 = RELIABLE) before tier 2 (c16 = UNTESTED); inside a tier, ADR-0019's carry-forward order A0, A5-C, A5-D, A4, A2, A1. Inside E4 the same order.
- **Supervision class.** LABEL-FREE: A0, A4, A5-C, A5-D. ADDRESS-SUPERVISED IN TRAINING: A1, A2.
- **No second chance.** S0 never trains an arm **as a candidate (C or X2)** at 16,384 or 65,536 slots if P9-II classed it FAILED at 16,384. A registered failure is not re-tried on other draws. A0 as the baseline is exempt: it runs at every cell type of the scope whatever its P9-II class, because the paired comparison needs it.
- **A candidate must be RELIABLE at 4,096 in P9-II.** If the arm P9-II carries forward is A0 on the strength of 16,384 alone, it is not in E and S0's candidate is the next arm by rank.

### 3.3 The rule

1. **Candidate C** = the first arm of E by rank, with **scope FULL** (4,096, 16,384 and 65,536 slots). If E is empty, C = the first arm of E4, with **scope SMALL** (4,096 slots only). If both are empty, S0 does not run (§3.4 rows 7–9).
2. **Runner-up X2** = the first arm, by rank, of the set C came from, other than C, whose supervision class differs from C's; if there is none, the first arm of that set other than C; if the set holds only C, there is no X2. X2 has C's scope. *(The other class comes first so that, where P9-II offers both, S0 holds one label-free and one supervised arm.)*
3. **Record-length variant X1 = WX(C)** (§5.2): C's training recipe on the full-context query. Always present when S0 runs.
4. **Answer-only baseline A0**, always (it is the candidate itself when C = A0). **Oracle reference A6** and **dense control A7**, always.
5. Every arm uses P9-II's code and P9-II's calibrated value, unchanged. A1-S is not run in S0: whether supervision works through fact information is P9-II's question and S0 inherits P9-II's reading.
6. **Order of qualification, fixed:** C first; X2 only if C does not meet §8.4. WX never becomes the qualified interface (§8.6). No arm is added, removed or reordered after any S0 record exists.
7. The mapping is evaluated by a committed script from P9-II's committed analysis output; its output (the **arm-selection record**) is part of the freeze and is recomputed by the auditor (gate G10).

### 3.4 What the rule gives for each P9-II outcome

| No. | P9-II outcome (ADR-0019 §8.6) | Arms S0 trains | Scope |
|---|---|---|---|
| 1 | ADDRESSING-RELIABLE, carried arm LABEL-FREE (A5-C, A5-D or A4) | C = the carried arm; X2 = the first supervised arm of E by rank (RELIABLE at 16,384 before UNTESTED there), else the next label-free arm of E, else none; WX(C); A0; A6; A7 | FULL |
| 2 | ADDRESSING-RELIABLE, carried arm supervised only (A2 or A1) | C = A2 if RELIABLE at 16,384, else A1; X2 = a label-free arm of E if one exists (it is then UNTESTED at 16,384), else the other supervised arm if in E, else none; WX(C); A0; A6; A7. The label carries (ADDRESS-SUPERVISED IN TRAINING) | FULL |
| 3 | ANSWER-ONLY RELIABLE, A0 RELIABLE at 16,384 | C = A0 (no separate baseline); X2 = first other arm of E by rank (necessarily not A0; label-free arms are the same class as A0, so a supervised arm of E comes first); WX(A0); A6; A7 | FULL |
| 4 | ANSWER-ONLY RELIABLE, A0 not RELIABLE at 16,384 | If A0 is UNTESTED at 16,384 (Stage 2 not COMPLETE): C = A0 unless a tier-1 arm exists. If A0 FAILED at 16,384: A0 leaves E; C = first arm of E; if E is empty, C = A0 from E4 with scope SMALL. X2, WX, A6, A7 by the rule; A0 runs as the baseline at every cell type of the scope when it is not C | FULL, or SMALL if C comes from E4 |
| 5 | ADDRESSING-RELIABLE AT 4,096 ONLY | If some arm RELIABLE at 4,096 did not advance (UNTESTED at 16,384): it is in E and is C with scope FULL. Otherwise C = first arm of E4, scope SMALL: cell types 2K/4K and 8K/4K only; no 16,384 or 65,536 cell of any arm; no Q2, no Q3 | FULL or SMALL |
| 6 | ADDRESSING-RELIABLE AT 4,096; 16,384 \<status\> | Every arm RELIABLE at 4,096 is UNTESTED at 16,384: C = first of E in carry-forward order; X2 by the rule; WX(C); A0; A6; A7. Qualification at 16,384 would rest on S0 alone and the label says so | FULL |
| 7 | ADDRESSING-UNRELIABLE | none. **S0 is not run.** Outcome **ADDRESSING-NOT-QUALIFIED (BY P9-II; S0 NOT RUN)**; §12 is returned to the human lead | — |
| 8 | ADDRESSING-FAILS | as row 7 | — |
| 9 | INCONCLUSIVE | none. **S0 is not run.** Outcome **INCONCLUSIVE (P9-II INCONCLUSIVE; S0 NOT RUN)**. Not a statement that addressing fails | — |
| 10 | ENGINEERING_FAIL / INCOMPLETE / NOT_INTERPRETED | none. Status **NOT STARTED — P9-II \<status\>**. A second P9-II attempt is the human lead's decision (ADR-0019 §14); S0 waits for a registered P9-II outcome or for the human lead's direction | — |

Rows 1–6 are illustrations of §3.3; where a row and §3.3 could be read differently, §3.3 decides. Any outcome with E and E4 both empty and a P9-II outcome of rows 3–6 (possible only through exclusions) is treated as row 9.

**Architectural alternatives are not arms of S0 in any row.** Testing one is a new study (P10-I) and needs the human lead's review (§12, §18).

## 4. What S0 adds beyond P9-II

| Addition | Why a P10 study needs it | Why P9-II cannot give it |
|---|---|---|
| Replication on S0's own draws and seed namespace (§7) | A lane of S1, or the integrated study, would rest on one study's draws otherwise | P9-II is one study; its Stage 2 has four draws (per-draw bound 0.47) |
| 65,536 slots at 512 exposures per fact (Q2) | S1's largest cells have 65,536 slots | Stage 3 is 32 exposures per fact, positive-or-uninformative, and skipped for A2 and A4 |
| Two facts per slot, cell 8K/4K (Q1) | S1's steps start from overloaded cells; its lane L names 8K/4K | every P9-II cell has 0.5 facts per slot |
| Facts added later (Q3) | S2 is sequential; an integrated study would add facts to a trained memory | P9-II trains every fact from the first update |
| A query not told the record length (WX) | every W7 result carries "told the record length" | W7 only; A5-C removes common-mode content, not the window |
| Fact-level dependence in S1's unit (a_use, §8.1) | S1's rules use usefully retained facts | P9-II scores accuracy and value permutation |

## 5. System, arms and schedules

### 5.1 Common

As ADR-0019 §3 and §4: frozen 27,392-parameter backbone, the P9-I task, flat memory (cosine keys, key width 16, top-8, temperature 0.2) read and added at answer sites only, alphabet-only loss, one AdamW at 0.003, clip 1.0, batch of 16 contexts = 128 answer sites. No backbone parameter is trained. No fact identity is an input of any learned arm at inference (gate G6). Arms A0, A1, A2, A4, A5-C, A5-D, A6, A7 are exactly ADR-0019 §4, from `studies.p9ii`.

### 5.2 WX, the full-context query (new)

For an answer site at position t (0 ≤ t ≤ 63) let h̃_j = h_j for j ≥ 0 and the zero vector for j < 0, h being the frozen block-0 output (width 32). Then

z = W_X · [h̃_{t−63}; …; h̃_t], W_X ∈ R^{16×2,048}, q = z / ‖z‖.

- 64 is the backbone's context length, not a property of the task. WX is not told that a record has eight bytes or where the identifier is. W7 is the special case of WX in which all but the last 224 columns of W_X are zero, so everything W7 can represent WX can.
- W_X is drawn by W7's initializer at fan-in 2,048 **[lead's choice]**; no column is copied from W7. WX has 32,768 query parameters against W7's 3,584; the difference is reported and nothing is parameter-matched to it.
- WX(C) is trained exactly as C: same loss terms, same calibrated value, same schedule, same target slots. For A5-C the running mean m has width 16 as before.
- **What WX still is told.** The memory reads only at positions 8r + 6. That input (the answer position) is not removed in S0: removing it needs reads and a loss at every position, which changes the objective for every arm and reintroduces the interference measured between rungs R0 and R0a of ADR-0017 §5.3. It is out of scope. Consequently **no S0 label says that an interface finds where to read**, and every label carries "the memory is told the answer position".
- Descriptive only, no training and no rule: for the qualified interface, the area under the ROC curve of max_s a_s for separating answer sites from the other 55 positions of Panel A contexts.

### 5.3 Training regime: 512 exposures per fact

Every cell is trained for U(F) = 4·F updates (512 exposures per fact **[lead's choice; the exposure of P9-II's Stage 1 and of its Stage 2 class readout]**): 8,192 updates at 2,048 facts, 32,768 at 8,192, 131,072 at 32,768. Schedules are expressed in exposures per fact as ADR-0019 §5: A2's U_pre and A4's T_A are multiplied by F / 2,048. The class readout is at U(F). A snapshot at 8,192 updates is also scored where U(F) > 8,192; for constant-objective arms it is printed as ALSO AT MATCHED UPDATES when the arm is RELIABLE there, and for A2 and A4 as MID-SCHEDULE; it enters no rule.

### 5.4 Added facts (Q3)

At 16,384 slots. In a Q3 draw the 8,192 facts lie in 512 clusters of 16 (ADR-0017 §4.3). **Set A** = the facts of clusters 1–256, **set B** = the facts of clusters 257–512 (4,096 each). Three streams: the draw's A-only stream and B-only stream (the generator restricted to those clusters, own seeds, §7) and its ordinary stream over A ∪ B.

- **Phase 1:** A-only stream, 16,384 updates (512 exposures per A fact). Snapshot S_A with optimizer state.
- **Phase 2, regime SEQ-N (no replay):** from S_A, B-only stream, 16,384 updates.
- **Phase 2, regime SEQ-R (replay):** from S_A, the ordinary stream over A ∪ B, 32,768 updates (512 further exposures per fact of both sets).
- Nothing is re-initialized between phases. The AdamW moments and counters are reset at the start of phase 2 **[lead's choice; S2 starts every stage with a fresh optimizer]**. The arm's schedule restarts at the start of each phase, in exposures per fact of that phase's trained facts. Target slots s(f) are one injection of A ∪ B into the slots, drawn once.
- Arms: the qualified candidate and A6, each through phase 1 and both regimes.
- **Frozen-memory read (evaluation only, no training).** The keys, values, output projection and gate of S_A combined with the query projection (and, for A5-C, the buffer m) of the phase-2 end state, scored on set A. It asks whether a memory frozen after phase 1 stays addressable while its query encoder goes on training, the situation of S2's mechanism (i).

## 6. Matrix

Cell type "8K/4K" = 8,192 facts in 4,096 slots. Init seeds 2001 and 2002.

### 6.1 Q1 — core (six draws, 1–6)

| Cell type | Load | Updates | Learned arms | Draws × init seeds | References A6, A7 |
|---|---|---|---|---|---|
| 2K/4K | 0.5 | 8,192 | A0, C, WX(C), X2 | 6 × 2 = 12 cells per arm | 6 × 1 each |
| 8K/4K | 2 | 32,768 | A0, C, X2 | 6 × 1 = 6 | 6 × 1 each |
| 8K/16K | 0.5 | 32,768 | A0, C, WX(C), X2 | 6 × 1 = 6 | 6 × 1 each |

- In the one-seed cell types draw d uses init seed 2001 for odd d and 2002 for even d; A6 and A7 use 2001. Both seeds therefore occur at every cell type. Two seeds per draw are spent only where they are cheapest **[lead's choice; the P9-I diagnostics found outcomes clustered by draw, and the unit of every bound is the draw]**.
- Within a draw, 8K/4K and 8K/16K share facts, streams and panels; the 2,048-fact set of a draw is generated independently (§7). Within a draw and seed every arm sees the same data, batch order and initialization of shared parameters.
- Cells: 2K/4K 48 + 12, 8K/4K 18 + 12, 8K/16K 24 + 12 = **126** with X2; **102** without X2; **102 / 78** when C = A0; **90 / 72** with scope SMALL (no 8K/16K cell).

### 6.2 Q2 — 65,536 slots at matched exposure (three new draws, 7–9)

32K/64K, 131,072 updates, init seed 2001: C (the qualified candidate), A0, A6, A7 × 3 draws = **12** cells (9 when the candidate is A0). Runs only for a candidate qualified at 16,384 (§8.5) and only within budget (§10.4). Scored also at 8,192 and 32,768 updates (32 and 128 exposures per fact), descriptively.

### 6.3 Q3 — added facts (four new draws, 10–13)

Qualified candidate and A6 × 4 draws × (phase 1 + SEQ-N + SEQ-R) = **24** training jobs, init seed 2001. Runs only for a candidate qualified at 16,384.

### 6.4 Totals

At most 126 + 12 + 24 = **162** registered training jobs; at least 54 (C = A0, scope SMALL, no X2). Pipeline check: 3 (§9.1). No draw of one stage enters another stage. Two reserve draws (§7).

**Why these numbers.** With the draw as the unit, the one-sided 95% lower bound on the per-draw success probability is 0.61 for 6 of 6, 0.42 for 5 of 6, 0.47 for 4 of 4 and 0.37 for 3 of 3. S0 states these bounds and claims no more. Where S0's protocol at a cell type is identical to P9-II's (2K/4K at 8,192 updates = Stage 1; 8K/16K at 32,768 = Stage 2 at 4U; identity checked by G4), the pooled count of the two studies is printed beside it, descriptively (for example 10 of 10 draws at 16,384 gives 0.74, 14 of 14 at 4,096 gives 0.81), with the note that P9-II's draws were used to select the arm and that the two studies define a draw's success with two cells and with one or two cells respectively.

## 7. Seeds and data identities

- **Registered data seed sets** `p10s0-draw-1` … `p10s0-draw-13`, bases 200001 + 100·(d − 1) (200001 … 201201). **Reserve sets** `p10s0-reserve-1`, `-2`: bases 201301, 201401. Used range 200001–201499.
- Layout in a set (P9-I convention inside each block: fourteen data seeds, three Panel A null seeds, three Panel B null seeds): base + 0…19 the 2,048-fact set (Q1) or the 32,768-fact set (Q2); base + 20…39 the 8,192-fact set (Q1, Q3). Target-slot seed base + 40 + j, j = init seed − 2001. Derangement seeds for the read swap base + 50 (first set) and base + 51 (second set). A-only and B-only stream seeds base + 70 and base + 71.
- **Init seeds** 2001, 2002. **Pipeline check:** data base 209001, init 2091. **Rehearsal:** data base 209101, init 2092. **Unit tests:** 920001–920999.
- **Disjointness (gate G9).** The implementation asserts that these ranges are disjoint from each other and from: P9 (170001–171343, 179001–179933, 1701–1702); P9-I (182001–182020, 180101–181900, 1791–1792, 1801–1802, 900001–900233); the review diagnostics (500001–500004); P9-II (190001–191599, 1891, 1901–1902, tests from 910001); S1 (210001–219999, 2101–2105, 2191–2192, tests from 921001); S2 (220001–229999); the seeds of P1–P8 read from their configs. A search of `studies/`, `configs/`, `src/` and `tests/` on 2026-11-15 found none of 200001–209999, 2001, 2002, 2091, 2092 or 920001–920999 in use; `experiments/` and `results/` were not searched and the audit must do so.
- Within a draw, training contexts, the calibration stream, Panels A and B, H1, H2 and the unseen-fact control are disjoint as ADR-0017 §4. In Q3 the panels are split by set; a panel context holds facts of one cluster and so of one set.
- All thirteen registered draws and both reserves are generated, hashed and G1-checked at the freeze, before any model sees them. No P9-II draw, panel or snapshot is used by S0.

## 8. Measurements, criteria and labels

### 8.1 Recorded

- During training, every 64 updates: as ADR-0019 §8.1, with the same probe set (both calibration-stream occurrences of the first 256 trained facts), the same slot-based definitions of collapse onset, escape, "separated" and the four categories.
- At the readout: as ADR-0019 §8.2, including LM capability and cost. No efficiency claim is made from any cost figure.
- **New: read swap and a_use.** π is a seeded derangement of the cell's facts with answer(π(f)) ≠ answer(f). For fact f on a panel, the swapped prediction is the model's prediction at f's answer site when the memory's read vector there is replaced by the read vector the model computes at π(f)'s answer site in π(f)'s own panel context. **a_use** = share of facts answered correctly whose swapped prediction is not their answer (the usefully retained facts of ADR-0021 §7.1). Reported with i = 5 − h₂(e) − e·log₂31 bits per fact, e = 1 − a_use.
- **New in Q3:** for set A before and after phase 2, accuracy on Panels A and B; the share of A facts whose top-1 slot on Panel A is unchanged; the mean Jaccard overlap of their top-8 sets; the frozen-memory read of §5.4; for set B, accuracy; the probe statistics over the first 256 facts of A ∪ B.

### 8.2 Cell success and arm class

A cell of a learned arm **succeeds** at the readout if conditions 1–5 of ADR-0019 §8.3 hold, with one change and one addition:

- **Condition 1 in cell type 8K/4K:** accuracy ≥ 0.90 × A6's on the same draw, and A6 ≥ 0.50 **[lead's choice]**, else the draw is NOT_EVALUATED for that cell type. (At two facts per slot the oracle reference may be below 0.90; what it reaches is S1's question, and S0 asks only whether learned addressing keeps what the oracle keeps.) Elsewhere the floor stays A6 ≥ 0.90.
- **Condition 6 (fact-specific dependence):** a_use ≥ 0.95 × accuracy on Panels A and B **[lead's choice; the DEP number of ADR-0021 §8.1]**.

So a success means, as numbers: accuracy at least 0.90 of the oracle reference; value permutation and memory-off inside the chance interval; at least 128 distinct top-1 slots on the 512 probe sites and no slot top-1 for more than 10 of them; held-out templates at 0.90 of Panel A; no leakage; at least 0.95 of the correct answers lost when the read is swapped.

**Arm class per cell type** (first match wins):

| Order | Class | 12-cell type (2K/4K) | 6-cell types | Q2 (3 cells) |
|---|---|---|---|---|
| 1 | NOT_EVALUATED | more than one draw NOT_EVALUATED | more than one draw NOT_EVALUATED | any draw NOT_EVALUATED |
| 2 | RELIABLE | at most one failed cell; no LM CAPABILITY REDUCED | no failed cell; no LM CAPABILITY REDUCED | 3 of 3 succeed; no LM CAPABILITY REDUCED |
| 3 | UNRELIABLE | at least 4 successes | at least 2 successes | 2 of 3 |
| 4 | FAILS | otherwise | otherwise | otherwise |

- LM CAPABILITY REDUCED as ADR-0019 §8.4 (b): a cell is flagged if its relative next-byte loss rise exceeds A6's on the same draw and cell type by more than 0.05; an arm flagged in more than one cell of a cell type carries the flag there.
- "No failed cell" in the six-cell types is stricter than ADR-0019's "at most one" **[lead's choice: with one cell per draw, one failure is one failed draw and leaves a bound of 0.42]**.

### 8.3 Arm-level annotations (enter no class unless §8.4 says so)

- **ADDRESS STABLE**, per cell type: the median over cells of the share of facts with the same top-1 slot on Panels A and B ≥ 0.80 (ADR-0019 §8.4's number).
- **ADDRESS RECALL** (A1, A2), **DENSE COMPARISON**, the four training-time categories and **sustained success**: as ADR-0019 §8.4 and §8.7.
- **Paired comparison with A0**, per cell type: d(X) as ADR-0019 §8.4; IMPROVES ON A0 if d ≥ 4 and X has more successes; HARMS if d ≤ −4; otherwise NOT DISTINGUISHED. The number 4 is used with 12 pairs and with 6 pairs. In Q2 (3 pairs) only the counts are printed.
- **OVERLOAD-QUALIFIED:** the qualified arm is RELIABLE at 8K/4K. OVERLOAD NOT QUALIFIED if UNRELIABLE or FAILS; OVERLOAD NOT_EVALUATED otherwise.

### 8.4 Qualification of an arm (C, then X2)

An arm **meets the core criteria at 4,096** if it is RELIABLE at 2K/4K and ADDRESS STABLE there. It **meets them at 16,384** if in addition it is RELIABLE at 8K/16K and ADDRESS STABLE there. The criteria named by the human lead map as follows:

| Criterion | Number |
|---|---|
| Fact-specific retrieval | success conditions 1 and 6; ADDRESS STABLE ≥ 0.80; held-out templates ≥ 0.90 (condition 4) |
| Resistance to query collapse | success condition 3 at the readout in every counted cell (slot-based, ADR-0019 §8.3); the category counts printed |
| Strong memory dependence | success condition 2 (value permutation and memory-off inside the chance interval) and condition 6 |
| No oracle at inference | gate G6: token-only forward; logits bit-identical under permutation of target slots, oracle codes and fact tables |
| Replication across draws and seeds | the class rule of §8.2 on S0's draws, with the per-draw bound printed; P9-II's class as the first study |
| LM capability | G5 for the backbone; the relative criterion against A6 for the system |

### 8.5 Stages and their status

- **Q1 gate.** The qualified candidate is C if C meets the core criteria at 4,096; otherwise X2 if X2 does; otherwise none. Its **scope** is 16,384 if it meets them at 16,384, else 4,096. The choice between C and X2 is made at 4,096 only and is not revisited: if C qualifies at 4,096 only and X2 would qualify at 16,384, the candidate stays C and X2's classes are printed beside it **[lead's choice; open question 2]**.
- Q3 and Q2 run only for a candidate with scope 16,384, in that order, each under its budget rule (§10.4).
- Each of Q2 and Q3 has a status: COMPLETE, NOT RUN — SCOPE, NOT RUN — BUDGET, NOT RUN — NO CANDIDATE, INCOMPLETE, NOT_EVALUATED. Q1's result is decided from Q1 alone and stands whatever happens later.

**Q3 labels**, per regime, over the four draws; all four must be evaluated (A6's set-A accuracy after phase 2 ≥ 0.50 on both panels, else the regime is NOT_EVALUATED):

| Label | Rule (all four draws, Panels A and B) |
|---|---|
| OLD FACTS RETAINED | candidate's set-A accuracy after phase 2 ≥ 0.90 × A6's after the same phase 2 |
| NEW FACTS ACQUIRED | candidate's set-B accuracy ≥ 0.90 × A6's |
| NOT COLLAPSED | success condition 3 on the A ∪ B probe after phase 2 |
| ADDRESSES KEPT (descriptive in SEQ-R) | median over draws of the share of A facts with unchanged top-1 slot ≥ 0.80 |
| **SEQUENTIAL-STABLE (regime)** | the first three hold; in SEQ-N also ADDRESSES KEPT |
| ENCODER KEEPS A FROZEN MEMORY ADDRESSABLE | frozen-memory read of set A ≥ 0.90 × the candidate's own set-A accuracy at S_A, all four draws **[lead's choice]** |

Otherwise the regime prints SEQUENTIAL-UNSTABLE with the failed parts. In SEQ-R a re-mapping of addresses is not a defect if the answers are retained.

### 8.6 Study outcome (first match wins)

| Order | Outcome | Rule |
|---|---|---|
| 1 | **NOT STARTED — P9-II \<status\>** | §3.4 row 10 |
| 2 | **ENGINEERING_FAIL / INCOMPLETE** | a failed gate; a difference between frozen and running code, config, launch scripts, arm-selection record or data identities; a Q1 cell without a record. No scientific label is derived and no denominator is reduced |
| 3 | **INCONCLUSIVE** | §3.4 row 9; or both C and X2 (or C alone when there is no X2) are NOT_EVALUATED at 2K/4K |
| 4 | **ADDRESSING-NOT-QUALIFIED** | §3.4 rows 7–8 (printed with "BY P9-II; S0 NOT RUN"); or S0 ran and no candidate meets the core criteria at 4,096 (printed with "NOT REPLICATED IN S0" and each arm's classes) |
| 5 | **ADDRESSING-QUALIFIED** | the candidate has scope 16,384, Q2 is COMPLETE and the candidate is RELIABLE at 32K/64K |
| 6 | **ADDRESSING-QUALIFIED AT 4,096 AND 16,384 ONLY** | scope 16,384; Q2 is COMPLETE and the candidate is not RELIABLE there (its class and count are printed; at 512 exposures per fact this is a result, not an exposure-limited probe) |
| 7 | **ADDRESSING-QUALIFIED AT 4,096 AND 16,384; 65,536 \<status\>** | scope 16,384; Q2 is not COMPLETE; not read as a failure to scale |
| 8 | **ADDRESSING-QUALIFIED AT 4,096 ONLY** | scope 4,096: by §3.3 scope SMALL, or because the candidate at 8K/16K is UNRELIABLE, FAILS, NOT_EVALUATED or not ADDRESS STABLE. The label says which; NOT_EVALUATED is not read as a failure at 16,384 |

Every outcome of rows 5–8 is printed with, and may not be shortened to omit:

1. the arm and its calibrated value; whether it is C or X2;
2. **(LABEL-FREE)** or **(ADDRESS-SUPERVISED IN TRAINING — needs a target slot per fact)**;
3. **the training regime it is qualified for:** 512 exposures per fact, U(F) = 4·F updates, schedules in exposures per fact, at 0.5 facts per slot;
4. the sizes, each with its evidence: "P9-II and S0" or "S0 only", the draw counts and the per-draw bound;
5. OVERLOAD-QUALIFIED / NOT QUALIFIED / NOT_EVALUATED; the Q3 labels per regime or Q3's status;
6. the paired label against A0 per cell type; DENSE COMPARISON; ADDRESS RECALL where defined;
7. **RECORD-LENGTH-FREE VARIANT:** PASSES (WX(C) RELIABLE and ADDRESS STABLE at 2K/4K and 8K/16K) / PASSES AT 4,096 ONLY / DOES NOT PASS / NOT_EVALUATED / NOT RUN. WX is S0-only evidence on a different parameter count; it is an annotation and never the qualified interface;
8. the fixed sentences: **"W7 is told the record length. The memory is told the answer position. Synthetic fixed-length records; one frozen 27,392-parameter backbone."**

**Hypothesis readings, fixed now.** H20-R: supported if C is the qualified candidate with scope 16,384; not supported otherwise. H20-S: supported under row 5; contradicted if C FAILS at 32K/64K; not supported otherwise. H20-O: supported if OVERLOAD-QUALIFIED. H20-Q: supported if SEQUENTIAL-STABLE in SEQ-N; supported with replay only if in SEQ-R alone. H20-L: supported if the variant PASSES. H20-B: supported if C IMPROVES ON A0 at 2K/4K and at 8K/16K; contradicted if C HARMS at either.

## 9. What the sibling studies may use

### 9.1 Per label

| S0 outcome | S1 learned-addressing lane (ADR-0021 §5.6) | S2 (ADR-0022 §5.4) | Programme |
|---|---|---|---|
| ADDRESSING-QUALIFIED | the qualified arm, exactly as S0 froze it (S0's code hash and value, no tuning), at 0.5 facts per slot on 4,096, 16,384 and 65,536 slots; cell 8K/4K only if OVERLOAD-QUALIFIED; each cell run for 4·F updates; S0's full annotation list printed with every lane result | nothing to run: S2 has no slot-level learned addressing and a different student. With SEQUENTIAL-STABLE the lead may **propose** the supplement S2 §5.4 names | learned addressing may be named as qualified, with the full label |
| … AT 4,096 AND 16,384 ONLY, or 65,536 \<status\> | as above without any 65,536-slot cell (S1's lane cells 2K/4K, 8K/4K, 8K/16K are covered) | as above | no statement about 65,536 beyond the label |
| … AT 4,096 ONLY | no lane: no step between memory sizes can be formed. The lane prints OMITTED — QUALIFIED AT 4,096 ONLY | none | no capacity-scaling statement under learned addressing |
| ADDRESSING-NOT-QUALIFIED | no lane | none; no supplement is proposed | **no capacity-scaling claim under learned addressing is made anywhere in P10.** S1's and S2's outcomes stand as oracle-addressed results with their own annotations. The lead reports an addressing failure and returns §12 to the human lead |
| INCONCLUSIVE, ENGINEERING_FAIL, INCOMPLETE, NOT STARTED | no lane | none | no statement about learned addressing |

- Overloaded cells other than 8K/4K, cells with more than 32,768 facts, and any regime other than 512 exposures per fact are outside every qualification.
- A lane may use a label only after the auditor has recomputed the stage it rests on from raw records. A Q1-based label (row 7 with Q2 pending) may be used on its own once Q1 is recomputed.

### 9.2 Timing

**A qualification that is recorded after a sibling study's freeze changes nothing in that study.** Its lane stays as its freeze record states (omitted, if nothing was qualified then). The qualification then goes to the fourth, integrated study (proposed after all three finish, not run) or to P10-I, which needs the human lead's review. S0 never delays S1 or S2, and neither delays S0.

### 9.3 Inconsistencies in the sibling drafts that this text cannot fix

- ADR-0021 §5.6 names S0 as "ADR-0019" with the outcome "ADDRESSING-RELIABLE" and requires acceptance by the human lead. Under this ADR the gate is S0's own label of §8.6. ADR-0021 needs that reference changed before its review; until then §9.1 states what S0 permits and ADR-0021 states what S1 does.
- ADR-0021 §6.3 lists P9-II's seed range as 190001–190733; revision 4 uses up to 191599. ADR-0019 §7 and ADR-0021 §6.3 give open-ended test ranges ("910001 upward", "921001 upward") that overlap each other and S0's unless bounded.

## 10. Gates, pipeline check, rehearsal, resources

### 10.1 Pipeline check (no calibration exists)

S0 has no tuned quantity. Before the freeze, on the pipeline-check draw only: A6, A7 and C at 2K/4K, one cell each (3 cells), to confirm that the pipeline produces records of the registered shape. Their accuracies are not results and select nothing.

### 10.2 Gates

- **G1** as ADR-0019 §9, per draw and fact set, with the same replacement rule: a registered draw failing G1 is replaced by the next unused reserve in fixed order, taking its place and stage; a failed reserve, or a third replacement, stops everything and returns to the human lead.
- **G2** chance interval per draw and fact count. **G5** and **G6** as ADR-0019 §9, G6 extended to WX.
- **G4** as ADR-0019 §9 for the arms in the arm-selection record, plus:
  - each arm's forward and one training step in S0 are bit-identical to `studies.p9ii`'s on a shared rehearsal seed;
  - WX with W_X zero outside its last 224 columns, and equal to a W7 projection there, gives W7's query bit for bit; the zero padding for t < 63 is as §5.2;
  - schedules at 8K/4K, 8K/16K and 32K/64K equal the exposure-scaled formulas; at 65,536 slots the full-N score path and (if A4 is in the record) the k = N read are checked against a direct computation;
  - the read swap: π has no fixed point and no pair with equal answers; swapping twice restores the logits;
  - Q3: the A-only and B-only streams hold only facts of their sets; phase 2 starts from S_A bit for bit with zeroed AdamW state; the frozen-memory read combines the stated tensors and no others.
- **G9** seed disjointness (§7). **G10** the arm-selection record equals the output of the mapping script on P9-II's committed analysis output, whose hash is recorded.
- The gates stage runs at real size on the rehearsal draw before the freeze and again on registered seeds before training. All gate outputs are written to the run directory and committed. A harness error is reported apart from a gate failure.
- **Fixed launch scripts**, no free arguments, committed before the freeze and covered by its hash: gates, Q1, Q1 gate, Q3, Q2 gate, Q2, analysis, report. No registered stage is launched by a typed command.
- **Analysis and report are exercised before the freeze on synthetic records of the full registry:** every row of §3.4, every class, label and outcome of §8, every stage status, missing cells, failed gates, non-finite values, a replaced draw, and each cut of §10.4.

### 10.3 Rehearsal

On the rehearsal draw, six single-thread workers, through the whitelist validator of P9-I (time, memory, shapes, counts, identity; no loss or accuracy is written or shown): every distinct (arm, cell type, phase) of the frozen matrix for 256 updates and one full evaluation including the read swap; A2 before and after its switch; A4 at k_0, mid-schedule and k = 8; Q3's three segments. Run twice: alone, and with twelve other busy single-thread processes **[lead's choice; S1 and S2 may be training on the same machine]**. The larger measured rate of the two is used. A stage's projection = measured seconds per update × planned updates (A4's annealing at its most expensive measured rate) + measured evaluation, arranged in rounds of six. The projections of every possible configuration are recorded at the freeze.

### 10.4 Resources

Apple M5 Max, 48 GB, CPU only, six single-thread workers. No cloud, no download, no new dependency, no change to `uv.lock` or `pyproject.toml`, no SSD work.

**Projection, not a measurement of this study.** From P9-I's per-update costs with six workers: 0.008–0.012 s at 4,096 slots, 0.013–0.015 at 16,384, 0.035–0.053 at 65,536 (rehearsal), and the slowest registered rates 0.0112 / 0.0195 / 0.0619. Makespan is summed time divided by six, which assumes perfect packing.

| Block | Jobs | Summed CPU-hours (fastest / W7 registered / slowest) | Makespan, hours |
|---|---|---|---|
| Q1, largest (126 cells) | 60 × 8,192 at 4,096; 30 × 32,768 at 4,096; 36 × 32,768 at 16,384 | 7.5 / 8.6 / 11.0 | 1.3 / 1.4 / 1.8 |
| Q1, 102 cells | | 6.2 / 7.1 / 9.0 | 1.0 / 1.2 / 1.5 |
| Q2, 12 cells × 131,072 updates | 1.27 / 1.93 / 2.25 h per cell | 15.3 / 23.2 / 27.0 | two rounds: 2.5 / 3.9 / 4.5 |
| Q2 after cut 1, 6 cells | | 7.6 / 11.6 / 13.5 | one round: 1.3 / 1.9 / 2.3 |
| Q3, 24 jobs | 16 × 16,384 and 8 × 32,768 at 16,384 | 1.9 / 2.0 / 2.8 | 0.3 / 0.3 / 0.5 |
| Pipeline check, rehearsal (twice), gates, generation of 15 draws, evaluation, analysis | | | about 0.7 |

**Projected charged total: about 4.8 to 7.5 hours** for the largest configuration. Not in the table and unmeasured: L_addr's all-key backward, A4's wide read, WX's wider projection, the probes (about 2% in the ADR-0019 review's estimate), the read swap in evaluation.

**Caps [lead's choice; fixed at the freeze on rehearsal evidence].**

- **Budget A — pipeline check, rehearsal, gates, Q1: 6 hours charged.** Q1 starts only if twice its rehearsed projection fits in what remains of Budget A.
- **Budget B — Q3 then Q2: 10 hours charged.** Budget A's unused time does not move to Budget B. Each stage starts only if twice its rehearsed projection fits in what remains of Budget B after the time actually charged.
- 3 GiB per worker; 18 GiB aggregate; the rehearsal must show a peak of at most 1.5 GiB per worker (P9-I's peak was 1.49 GiB, in evaluation at 65,536). Each stage's time cap is twice its rehearsed projection. A running stage that reaches its cap is stopped and is INCOMPLETE.

**Rule if the rehearsal shows the budget does not fit (fixed now, applied in this order, each cut recorded in the freeze):**

1. Q1 does not fit Budget A: drop X2 everywhere (only C can then qualify). Still not: drop WX (the variant prints NOT RUN and H20-L is not tested). Still not: nothing registered is run and the matter returns to the human lead.
2. Q2 does not fit what remains of Budget B: **cut 1** — drop A0 and A7 at 32K/64K (six cells, one round; the paired label and DENSE COMPARISON print NOT RUN at that size). Still not: Q2 is NOT RUN — BUDGET.
3. Q3 does not fit: NOT RUN — BUDGET.
4. No draw, update count, threshold or exposure is changed to make anything fit.

At the slowest rates the full Q2 needs 2 × 4.5 = 9.0 h and Q3 2 × 0.5 = 1.0 h, exactly Budget B; any unmeasured overhead then triggers cut 1. At the W7 registered rate the two need 8.7 h.

No timing-sensitive comparison is made between cells; CPU seconds are descriptive.

## 11. Implementation

New package `studies/p10s0/` importing `studies.p9ii`, `studies.p9i` and `studies.p9` unedited. New code: the mapping script, WX, the 8,192-facts-in-4,096-slots cell, the exposure-scaled schedules at 65,536, the read swap, the Q3 streams, phases and frozen-memory read, the analysis and report. Records carry the study code P10S0. Implementation may start before P9-II finishes, because every arm of the mapping exists in P9-II's code; the freeze cannot happen before P9-II's outcome is recomputed and committed.

## 12. Architectural alternatives to return if nothing qualifies

Reported, not run. Each would be a new study (P10-I) under the human lead's review. Ordered by the lead's present judgment of evidence and cost **[lead's choice]**.

1. **Contrastive query encoder, frozen before memory training.** Train the query projection alone so that two occurrences of a fact in different contexts are close and different facts are far (InfoNCE over queries, no slots, no values); freeze it; then train keys, values and readout on the answer loss. It differs from A2 in having no fixed slot targets and no later movement of the encoder. Evidence: the P9-I review's design-stage probe (a contrastively fitted W7 query with an oracle store, 0.96–1.00). Needs fact-pair supervision or two contexts of a fact per batch.
2. **Keys written from encoder states (nearest-neighbour addressing).** A fact's key is not learned: at its first training occurrence the centred, normalized window state (224 wide, or a fixed random projection of it) is written as the key of a free slot; only values and readout are trained. Addressing is then nearest-neighbour retrieval over fixed states, with no query collapse possible. Evidence: the window carries 19.8–20.0 bits of the identifier (ADR-0017 §I.1); S1's KNN-W baseline will measure the no-learning version. Costs: write-time slot allocation; key width 224 unless projected.
3. **Hashed, content-addressed keys from input bytes.** Slots from seeded hashes of the last k input bytes, for several k at once (k = 1…8), reads summed; values learned. No learned addressing and no collapse; S1's H8 is the oracle-identifier version. It is a lexical index: it generalizes only to exact byte matches, and choosing k is the record-length leak in another form unless all k are used.
4. **Product-key addressing.** Split the query into two halves, each scored against √N half-keys; a slot is a pair. Collapse of one sub-query costs √N of the address space, not all of it, and scoring is 2√N instead of N products. Untested here; the common-mode problem remains inside each half.
5. **Balanced assignment in place of a penalty.** Replace the soft diversity penalty by a hard constraint: each batch's queries are assigned to slots by an equal-partition (Sinkhorn) step and trained toward their assignment. Label-free; stronger than A5-D; the assignment must be made consistent across batches for one fact, which again needs either fact identity or content similarity.
6. **Let the model form the query, with its language modelling protected.** P9-I's arm BB reached 0.54–0.65 at 4,096 slots by training block-0 attention, and destroyed next-byte prediction. A joint loss (next-byte on corpus rows plus the answer loss) or a small added block is the form the handoff names as the eventual path. It leaves the frozen-backbone lineage and is the largest change.

The lead's recommendation when the time comes is made on S0's and P9-II's records, not here.

## 13. Order of work

1. Opus review of this revision; revise until no blocker or major is open.
2. Lead's approval under the delegation (§18), or referral of the items of §17 to the human lead.
3. P9-II's registered outcome recomputed by the auditor and committed. (Steps 4 and 5 may begin before this; step 7 may not.)
4. Implementation with tests and the fixed launch scripts.
5. Pipeline check; rehearsal (twice); gates at real size on the rehearsal draw; analysis on synthetic registries; implementation audit.
6. The mapping script run on P9-II's committed output; arm-selection record; audited (G10). If it selects nothing: the outcome of §3.4 rows 7–10 is recorded and the study ends here.
7. Generation and G1 of all draws; cuts by §10.4; freeze of specification, code, config, launch scripts, seeds, thresholds, arm-selection record, projections, caps, cuts and data identities.
8. The registered run, once, by the launch scripts: gates; Q1; Q1 gate; Q3; Q2 gate; Q2.
9. Independent recomputation from raw records and snapshots by the auditor, stage by stage (Q1 first, so that a Q1-based label can be used); outcome report with deviations, failed attempts and negative results kept.

## 14. Stop rules

- A failed gate, or any difference between the frozen and the running code, config, launch scripts, arm-selection record or data identities, stops the run.
- A stage whose doubled projection does not fit is not started; a stage that reaches its cap is stopped and is INCOMPLETE. Completed stages stand.
- A failed cell is kept and not re-run.
- No re-run with changed settings. A second attempt after an engineering stop needs the human lead's decision, with everything observed in the first attempt listed.
- No registered seed is seen by a model before the freeze.
- If P9-II's outcome is amended after S0's freeze, S0 stops and returns to the human lead.

## 15. What S0 cannot establish

- Anything about capacity, useful-capacity scaling, locality or transfer. A qualified interface is a precondition for asking those questions with learned addressing, not an answer to them.
- That the interface works on natural language, on another backbone or student (S2's student included), at loads other than 0.5 and 2 facts per slot, beyond 65,536 slots or 32,768 facts, or under any regime other than 512 exposures per fact.
- That the interface finds where to read: the memory is told the answer position in every arm, WX included.
- That address labels are available in a real system. A supervised arm's qualification says nothing about learning addresses without labels.
- That a qualified arm beats a tuned baseline: A0 is untuned by design (ADR-0019 §6), and the candidate was selected on P9-II's draws.
- Why an arm works. The negative control A1-S is P9-II's; S0 does not repeat it.
- A success probability above the printed per-draw bounds. Three draws at 65,536 give 0.37 at best.
- That adding facts is safe in general: Q3 is one size, one split, two regimes, four draws, and a flat memory with shared slots.
- Any efficiency, latency or storage claim. Costs are descriptive.
- That WX's result transfers to W7's parameter count, or that a full-context linear query is a practical interface.
- A failure of the ArborLM concept, whatever the outcome.

## 16. Requirements map

| The human lead's requirement | Where |
|---|---|
| P9-II interventions as a gate, not assumed to have succeeded | §3 (mapping fixed before P9-II runs), §3.4 rows 7–10 |
| Compare answer-only with addressing supervision and staged optimization | A0 in every cell type; C and X2 from different supervision classes where P9-II offers both (§3.3 item 2). The full comparison of all methods is P9-II's and is not repeated |
| Multiple independent draws and initialization seeds | §6, §7; bounds in §6.4 |
| Fact-specific retrieval, resistance to collapse, strong memory dependence, no oracle at inference | §8.2, §8.4 |
| If none qualifies: stop capacity-scaling claims, report an addressing failure, return with alternatives | §8.6 row 4, §9.1, §12 |
| Own hypotheses, controls, thresholds, freeze, Opus audit, outcome report; own identity, seeds, partitions, budget | header, §2, §7, §8, §10, §13 |
| S1 and S2 do not wait; learned addressing evaluated separately if qualified | §9 |
| M5 Max 48 GB; caps from a full-size rehearsal with at least 2× headroom; no cloud, no downloads | §10.3, §10.4 |

## 17. Decisions reserved for the human lead

1. Any change of thresholds, arms, mapping or budget after the freeze; any second attempt; any second P9-II attempt on which S0 would depend.
2. Everything that follows an ADDRESSING-NOT-QUALIFIED or INCONCLUSIVE outcome: which alternative of §12, if any, becomes P10-I.
3. The use of S0's outcome in any programme-level claim; the fourth, integrated study; any supplement to S2.
4. Whether the caps of §10.4 (16 charged hours in two budgets) are within the delegation, if the lead does not read them so.
5. Merge, publication, weight release, ADR-0012.

## 18. Approval record

Empty until the specification review is complete.

The human lead's words, verbatim:

> "we can change it to  p10 can be self approve but p10-I need my review"

Recorded with it, verbatim: "p9-II and p10 can run in parallel, but we must first commit p9 and then adjust any implementation as p10-I if needed once p10 is done running".

The lead's conditions for using the delegation, as in ADR-0019 §16: (1) the specification review ends with no open blocker or major; (2) the implementation audit is clean before the freeze; (3) the rehearsal shows 2× headroom; (4) nothing changes after the arm-selection record except the cuts of §10.4; (5) no registered seed has been observed; and (6) P9-II's outcome is recomputed and committed before the freeze.

Lead's approval: PENDING the specification review. The human lead's review is required for any P10-I. Astra review: NOT_PERFORMED.

## Open questions for the lead

1. **Does S0 run at all when P9-II is UNRELIABLE or FAILS?** This draft says no (rows 7–8) and treats every architectural alternative as P10-I under the human lead's review. The other reading of "S0 tests reliable learned addressing" would put one alternative of §12 (the contrastive frozen encoder) into S0 as an arm. That would make S0 a first test of a new method, not a gate.
2. **C before X2, decided at 4,096 only.** If C qualifies at 4,096 only and X2 would qualify at 16,384, the candidate stays C. The alternative, "the arm with the larger scope wins", is also fixed in advance but lets the runner-up overtake.
3. **One init seed per draw at 8K/4K, 8K/16K and 32K/64K, with "no failed cell".** Two seeds per draw there would add 36 to 48 cells at the expensive sizes. Is the alternating-seed design enough for "multiple initialization seeds"?
4. **Three draws at 65,536** give a bound of 0.37. A fourth and fifth draw cost one more round of about 2 to 4.5 hours with headroom doubling it. Accept 0.37, or enlarge Budget B?
5. **WX as the record-length test.** It is a superset of W7 with nine times the query parameters. Is that the right leak-free variant, or should it be a 16-position window, or the attention arm A4 of P9-I (which the auditor's probe predicted to fail on frozen states for representational reasons)? The answer-position leak is left in place in every case.
6. **"No second chance" (§3.2).** An arm that P9-II classed UNRELIABLE at 16,384 is never retrained there by S0, even if it failed by a single cell. Keep it strict?
7. **Programme reading of NOT-QUALIFIED.** This draft lets S1's and S2's oracle-addressed outcomes stand and forbids only capacity-scaling claims under learned addressing. The human lead's original sentence ("stop capacity-scaling claims") predates the three-study update; the lead may want the human lead to confirm the reading.
8. **Budget.** 16 charged hours in two budgets, sized so that the full Q2 fits only at the measured W7 rate. Is that within the delegation, and may S0's stages overlap S1's and S2's training on the machine (the rehearsal assumes they may)?

Astra review: NOT_PERFORMED. A Claude review is not an Astra review, and this document is not a human approval.
