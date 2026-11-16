# ADR-0020 — P10-S0: Addressing qualification for the P10 programme

- **Status: DESIGN REVISION 2 — NOT YET CONFIRMED. SPEC: PENDING ASTRA REVIEW. Nothing is implemented, rehearsed or run. No approval exists.**
- **Date:** 2026-11-15 (UTC)
- **Revision history.** Revision 1 (2026-11-15): first draft; reviewed by Opus 5.5 (`adr-0020-review/REVIEW.md`), verdict NOT READY (blockers B1–B2, majors M1–M7, minors m1–m20). Revision 2 (this text): applies that review under the lead's rulings. §19 maps every finding to its change; §20 lists the lead's choices. The design changed in substance: S0 now always runs and always contains the answer-only, supervised and staged arms; the runner-up arm, the small scope, the added-facts stage and the 65,536 label are gone; the sample is ten draws by two seeds.
- **Study code:** P10S0. Package `studies/p10s0/`. Config `configs/p10s0_qualification.toml`. Tests `tests/test_p10s0_*.py`. Launch scripts `studies/p10s0/launch/`. This text calls the study "P10-S0" or "S0" and its stages Q1 and Q2; it has no "Stage 0".
- **Origin.** The human lead's P10 direction: "Addressing remains a mandatory prerequisite. Incorporate the most promising P9-II addressing interventions as a qualification gate rather than assuming they have succeeded." and "Phase 1 — Addressing qualification: … Compare the original answer-only method with preregistered addressing supervision and staged optimization. Evaluate across multiple independent data draws and initialization seeds. …"; and the later update that S0, S1 (ADR-0021) and S2 (ADR-0022) are "three parallel, scientifically independent experiments". The direction texts are quoted from the lead's task messages; they are not in the repository.
- **Evidence it rests on.** P9-I (ADR-0017 Part I): COMPLETE — NO_INTERFACE_SELECTED, accepted by the human lead as a registered negative result (ADR-0017 §15.9). P9-II (ADR-0019 revision 4): **not yet run**; this text is written before any P9-II observation and uses no P9-II result. Review diagnostics are exploratory and enter no rule.
- **Roles (study-specific).** Lead: Claude Fable 5.2. Specification review, implementation audit and recomputation: Opus 5.5, in contexts separate from implementation, receiving code and records and not the lead's conclusions. Implementation: Sonnet 5.5. Inventory: Haiku 5.5. The model that actually ran each delegated task is recorded from session metadata. ADR-0012 stays not approved. **Astra review: NOT_PERFORMED.** A Claude review is neither Astra validation nor a human approval.
- **Relation to other work.** P9-II runs and is committed first. S0 imports `studies.p9ii`, `studies.p9i` and `studies.p9` unedited. S1 and S2 do not wait for S0; S0 uses no result of S1 or S2. P1–P9-II code, configs, records and ADRs are not edited.
- **Marking.** Judgment-call numbers are marked **[lead's choice]**. "As ADR-0019 §x" means the definition of ADR-0019 revision 4 applies unchanged.

## 0. What S0 is, in one paragraph

S0 is the registered qualification gate of the P10 programme and an independent replication of P9-II's central comparison. Whatever P9-II shows, S0 trains the answer-only method (A0), addressing supervision (A1) and staged optimization (A2) on ten new draws and two initialization seeds, at 4,096 and at 16,384 slots, with ADR-0019's definitions and P9-II's calibrated values. P9-II's outcome adds at most one further arm, by a mapping fixed here (§3). An interface is qualified from S0's own classes by a fixed preference order (§8.5). P9-II's classes are printed beside S0's as REPLICATES or DOES NOT REPLICATE. S0 tunes nothing.

## 1. What is known, and what is not

Registered (P9-I, one draw, two initialization seeds, 8,192 updates): oracle-query retrieval 0.967–1.000; every learned query interface at chance (0.028–0.044) with 1–6 distinct top-1 slots; the dense window control 0.78–0.80 at 16,384 slots and 0.13 at 65,536.

Exploratory (review diagnostics on other draws; not registered): collapse within 64 updates in every run; an escape that depends on the draw and hardly on the initialization seed; a starved query-projection gradient in the collapsed state.

Not known, the subject of P9-II: which training method, if any, is reliable across draws at 4,096 and 16,384 slots.

Not known, and not answerable by P9-II alone (the subject of S0):

1. Whether P9-II's classes for A0, A1 and A2 are reproduced by a second study with its own draws, and with ten draws where P9-II's Stage 2 has four.
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
- **H20-D (the carried label-free arm; only if a fourth arm exists).** C4 is RELIABLE and IMPROVES ON A0 at both core sizes.
- **H20-R (replication), per arm and size.** The arm's class on S0's draws under P9-II's criteria agrees with its P9-II class (RELIABLE in both, or not RELIABLE in both).
- **H20-Q (qualification).** At least one arm meets S0's criteria at both core sizes (§8.5).
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
4. **The interface carried forward** (ADR-0019 §8.6: the first RELIABLE arm at 16,384, 4U readout, in the order A0, A5-C, A5-D, A4, A2, A1, without LM CAPABILITY REDUCED; A1 and A2 skipped where NEGATIVE CONTROL FAILED is printed). If it is A4, A5-C or A5-D, **C4 is that arm** with its calibrated value. If it is A0, A2 or A1, or no arm is carried, there is no fourth arm, and the reason is printed.

Nothing else is read: no accuracy, no per-draw table, no Stage 3 label. The mapping is evaluated by a committed script; its output, the **arm-selection record**, is part of the freeze. The auditor recomputes it from this text, not from the implementer's script (gate G10).

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
| ADDRESSING-RELIABLE AT 4,096 ONLY | none (nothing is carried) |
| ADDRESSING-RELIABLE AT 4,096; 16,384 \<status\> | none (Stage 2 not COMPLETE) |
| ADDRESSING-UNRELIABLE, ADDRESSING-FAILS, INCONCLUSIVE | none |
| ENGINEERING_FAIL / INCOMPLETE / NOT_INTERPRETED | none; printed as in §3.2 item 2 |

In every row S0 runs its full core matrix. P9-II's outcome changes only whether a fourth learned arm is present. No arm is added, removed or reordered after any S0 record exists.

**Consequence, stated:** a label-free arm that P9-II finds RELIABLE at 4,096 but that is not the carried arm (because A0 precedes it, or because it failed or was not run at 16,384) is not in S0.

## 4. What S0 adds beyond P9-II

| Addition | Why P10 needs it | Why P9-II cannot give it |
|---|---|---|
| The A0 / A1 / A2 comparison on S0's own ten draws × two seeds at both sizes | the gate must not rest on one study; the human lead asked for this comparison in Phase 1 | P9-II is one study; its Stage 2 has four draws (bound 0.47) and only the arms that advanced |
| Classes under P9-II's criteria printed beside P9-II's (REPLICATES / DOES NOT REPLICATE) | says whether P9-II's finding is a property of its draws | — |
| Fact-level dependence in S1's unit (read swap, a_use) and address stability as criteria | S1's rules use usefully retained facts | P9-II scores accuracy and value permutation; stability is an annotation there |
| Two facts per slot, cell 8K/4K, label-free arms | S1's lane step starts from 8K/4K | every P9-II cell has 0.5 facts per slot |
| WX, a query not told the record length | every W7 result carries "told the record length" | W7 only |
| 65,536 at 512 exposures per fact, as a probe | descriptive input for a later study | P9-II's Stage 3 has 32 exposures per fact and is skipped for A2 and A4 |

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

Cell type "8K/4K" = 8,192 facts in 4,096 slots. Init seeds 2001 and 2002. n_L = number of learned core arms = 3 (A0, A1, A2) or 4 (with C4).

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

### 6.2 Q2 — annotations for the qualified candidate (after the Q1 gate)

| Block | Cell type | Updates | Arms | Draws × seeds | Cells |
|---|---|---|---|---|---|
| WX | 2K/4K and 8K/16K | 8,192 and 32,768 | WX(candidate) | draws 1–10 × 1 (alternating seeds as 8K/4K) | 20 |
| 65,536 probe | 32K/64K | 131,072 | candidate, A6 | three new draws 11–13 × seed 2001 | 6 |

- WX reuses the Q1 draws, where A6 and A7 already exist. The candidate was chosen on those draws by the fixed rule of §8.5; WX is an annotation and the reuse is stated with it.
- Q2 runs only if a candidate is qualified at both core sizes. Otherwise both blocks print NOT RUN — NO CANDIDATE.

### 6.3 Totals and bounds

At most 230 + 26 = **256** registered training cells; 180 if there is no fourth arm and no candidate. Pipeline check: 3 cells (§10.1). Two reserve draws (§7).

One-sided 95% Clopper–Pearson lower bounds on the per-draw success probability. **In the two-seed cell types a draw succeeds only when both of its cells succeed; every printed bound uses that count.**

| Draws succeeding | Bound |
|---|---|
| 10 of 10 | 0.741 |
| 9 of 10 (the least that RELIABLE guarantees, §8.3) | 0.606 |
| 9 of 9 (one draw NOT_EVALUATED) | 0.717 |
| 8 of 9 | 0.571 |
| 8 of 10 (not RELIABLE; for reference) | 0.493 |
| 3 of 3 (65,536 probe) | 0.368 |

S0 states these bounds and claims no more. Where S0's protocol at a cell type is identical to P9-II's (2K/4K at U = Stage 1; 8K/16K at 4U = Stage 2; identity checked by G4), the pooled count of the two studies is printed beside the S0 count, always, as a descriptive line (for reference: 18 of 18 gives 0.847, 17 of 18 gives 0.762, 14 of 14 gives 0.807, 13 of 14 gives 0.703). No rule uses the pooled count.

## 7. Seeds and data identities

- **Registered data seed sets** `p10s0-draw-1` … `p10s0-draw-13`, bases 200001 + 100·(d − 1). Draws 1–10: Q1 and WX. Draws 11–13: the 65,536 probe. **Reserve sets** `p10s0-reserve-1`, `-2`: bases 201301, 201401, each holding all three fact sets. Replacement as ADR-0019 §9.
- Layout in a set (P9-I convention inside each block of twenty: fourteen data seeds, three Panel A null seeds, three Panel B null seeds): base + 0…19 the 2,048-fact set; base + 20…39 the 8,192-fact set; base + 60…79 the 32,768-fact set. Target-slot seeds, with j = init seed − 2001: base + 40 + j (2,048 facts), base + 44 + j (8,192 facts, 16,384 slots), base + 48 + j (32,768 facts). WX uses the target slots of its cell. Read-swap derangement seeds base + 50, + 51, + 52 for the three fact sets.
- **Init seeds** 2001, 2002. **Pipeline check:** data base 209001, init 2091. **Rehearsal:** data base 209101, init 2092. **Unit tests:** 920001–920999.
- **Bounded, disjoint namespaces (gate G9).** P9 (170001–171343, 179001–179933, 1701–1702); P9-I (182001–182020, 180101–181900, 1791–1792, 1801–1802, 900001–900233); review diagnostics (500001–500004); P9-II (190001–191599, 1891, 1901–1902, tests 910001–919999); **S0 (200001–209999, init 2001–2002, check and rehearsal init 2091–2092, tests 920001–920999)**; S1 (210001–219999, 2101–2105, 2191–2192, tests 921001–921999); S2 (220001–228999, tests 229001–229999); the seeds of P1–P8 read from their configs. G9 asserts these in code and reads P9-II's actual test seeds from its committed code at S0's freeze, asserting them inside 910001–919999.
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

- All numbers in the table **[lead's choice]**. "No draw with both seeds failed" is implied by "at most one failed cell" and is written out because the bound of §6.3 depends on it.
- LM CAPABILITY REDUCED as ADR-0019 §8.4 (b): a cell is flagged if its relative next-byte loss rise exceeds A6's on the same draw and cell type by more than 0.05; an arm flagged in more than one cell of a cell type carries the flag there and is printed **UNRELIABLE (LM CAPABILITY REDUCED)** when the count of row 2 is met.
- **Two classes are printed for every learned arm and cell type:** the class under S0's criteria and the **class under P9-II's criteria** (conditions 1–5 and the same count rule, on S0's cells). Qualification uses S0's criteria. Replication uses P9-II's.

### 8.4 Comparisons and annotations (enter no class)

- **Paired comparison with A0**, per core cell type, as ADR-0019 §8.4: d(X) = (cells where X succeeds and A0 fails) − (cells where A0 succeeds and X fails) over the 20 pairs; IMPROVES ON A0 if d ≥ 4 and X has more successes; HARMS if d ≤ −4; otherwise NOT DISTINGUISHED. The exact sign-test p-value is printed. d(A2 against A1) is printed, descriptively.
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

**Preference order, fixed [lead's choice]: C4 (if present), then A2, then A1, then A0.**

1. The candidate is the first arm in the order that meets the criteria at 2K/4K **and** at 8K/16K. Its scope is 4,096 and 16,384.
2. If there is none, the first arm in the order that meets them at 2K/4K is printed as qualified at 4,096 only. Q2 is not run.
3. If there is none, no arm is qualified.
4. When A0 is the candidate the label reads **(ANSWER-ONLY SUFFICES)**. When A0 meets the criteria but an earlier arm is the candidate, **ANSWER-ONLY ALSO MEETS THE CRITERIA** is printed.

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
| 4 | **ADDRESSING-QUALIFIED (4,096 AND 16,384)** | §8.5 item 1 |
| 5 | **ADDRESSING-QUALIFIED AT 4,096 ONLY** | §8.5 item 2. The label says why 16,384 is missing: UNRELIABLE, FAILS, NOT_EVALUATED or not ADDRESS STABLE. NOT_EVALUATED is not read as a failure at 16,384 |
| 6 | **ADDRESSING-NOT-QUALIFIED** | §8.5 item 3. Printed as "NOT QUALIFIED IN S0" with, for every arm and size, the S0 class, the class under P9-II's criteria, the replication label and, where an arm is RELIABLE under P9-II's criteria but not under S0's, the added criterion it failed (condition 6 or ADDRESS STABLE) |

Each of Q2's blocks has a status: COMPLETE, NOT RUN — NO CANDIDATE, NOT RUN — BUDGET, NOT RUN — MEMORY, INCOMPLETE, NOT_EVALUATED. Q1's outcome is decided from Q1 alone and stands whatever happens in Q2.

**The outcome of rows 4–5 is printed with, and may not be shortened to omit:**

1. the arm and its calibrated value;
2. **(LABEL-FREE)** for A0, A4, A5-C, A5-D, or **(ADDRESS-SUPERVISED IN TRAINING — needs a target slot per fact)** for A1, A2;
3. the regime: 512 exposures per fact (U at 2,048 facts, 4U at 8,192), schedules in exposures per fact, 0.5 facts per slot;
4. per size: S0's draw count and per-draw bound; P9-II's class; REPLICATES / DOES NOT REPLICATE / NOT COMPARABLE; the pooled count;
5. the annotations of §8.6 and §8.4, including P9-II's negative-control result for a supervised candidate;
6. the classes of the other arms and their paired labels against A0;
7. the fixed sentences: **"W7 is told the record length. The memory is told the answer position. Synthetic fixed-length records; one frozen 27,392-parameter backbone."**

**The text of ADDRESSING-NOT-QUALIFIED says only what S0 found:** that no tested arm met S0's criteria on S0's draws, with item 6 of the table. It makes no statement about S1 or S2 (§17 item 0).

**Hypothesis readings, fixed now.** H20-A: supported if A0 is not RELIABLE (S0's criteria) at 2K/4K or at 8K/16K. H20-B, C, D: supported if the arm is RELIABLE and IMPROVES ON A0 at both core sizes; contradicted if it HARMS at either; not supported otherwise. H20-R, per arm and size: supported if REPLICATES; not supported if DOES NOT REPLICATE; not read if NOT COMPARABLE. Qualification is reported separately from replication. H20-Q: supported under row 4. H20-O, H20-L and H20-S are read on the qualified candidate: H20-O supported if OVERLOAD-QUALIFIED, not tested if NOT RUN; H20-L supported if the variant PASSES, otherwise not supported, never contradicted; H20-S supported as an annotation if 3 of 3, contradicted if 0 of 3 with A6 evaluated, otherwise not supported.

## 9. What the sibling studies may use

### 9.1 Per label

| S0 outcome | S1 learned-address lane (ADR-0021 revision 2, which cites this ADR's labels) | S2 (ADR-0022) |
|---|---|---|
| ADDRESSING-QUALIFIED (4,096 AND 16,384) | the candidate exactly as S0 froze it (S0's code hash; P9-II's calibrated value from the arm-selection record; no tuning), at 2K/4K and 8K/16K, and at 8K/4K **only if OVERLOAD-QUALIFIED**; each cell run for 4·F updates (8,192 at 2K/4K; 32,768 at 8K/4K and 8K/16K). The lane's one step is 8K/4K → 8K/16K, so **without OVERLOAD-QUALIFIED no step can be formed** and the lane prints OMITTED — NOT OVERLOAD-QUALIFIED; for a supervised candidate it prints OMITTED — SUPERVISED ARM HAS NO 8K/4K CELL. The lane's cells record S0's probe set, H1/H2 and the read swap so that S0's cell-success rule can be applied. Whether a human acceptance is also needed is decided by ADR-0021 | nothing to run: S2 has no slot-level learned addressing and a different student |
| ADDRESSING-QUALIFIED AT 4,096 ONLY | no lane | none |
| ADDRESSING-NOT-QUALIFIED | no lane | none |
| INCONCLUSIVE, ENGINEERING_FAIL, INCOMPLETE, NOT STARTED | no lane | none |

No lane uses a 65,536-slot cell, any load other than 0.5 and (with OVERLOAD-QUALIFIED) 2, or any regime other than 512 exposures per fact. A lane may use a label only after the auditor has recomputed Q1 from raw records.

### 9.2 Timing, stated plainly

**A qualification recorded after a sibling study's freeze changes nothing in that study.** S0 can freeze only after P9-II's outcome is recomputed and committed, and S0's Q1 is the longest part of its run. S1 and S2 do not wait. **In the expected timeline S1 freezes before S0's Q1 label is recomputed, so S1's learned-address lane will be omitted.** "Learned addressing evaluated separately if qualified" is then met only by a later study: the integrated study or P10-I. **Both need the human lead's review**; the integrated study is proposed, not executed automatically.

### 9.3 Corrections owed by the sibling drafts (this text cannot make them)

The review's §6 lists them; they are repeated for the lead: ADR-0021 header and §5.6 must cite ADR-0020 and its labels, 4·F updates with F-OQ read at the same update count, S0's cell-success rule at all three lane cells; ADR-0021 §6.3 must list P9-II as 190001–191599 with tests 910001–919999, S0's ranges, and bound its own tests to 921001–921999; ADR-0022 §9 must name S0's and S1's ranges and use 220001–228999 with tests 229001–229999; ADR-0022 §10 must write "s_c(Stage 0)" in place of "s_c(S0)"; ADR-0022 §5.4 must read "a supplement approved by the human lead". ADR-0019 §7's "910001 upward" is read as 910001–919999 and asserted by G9.

## 10. Gates, pipeline check, rehearsal, resources

### 10.1 Pipeline check (no calibration exists)

S0 has no tuned quantity. Before the freeze, on the pipeline-check draw only: A0, A6 and A7 at 2K/4K, one cell each (3 cells), to confirm that the pipeline produces records of the registered shape. Their accuracies are not results and select nothing.

### 10.2 Gates

- **G1** as ADR-0019 §9, per draw and fact set, with its replacement rule. **G2** chance interval per draw and fact count. **G5**, **G6** as ADR-0019 §9, G6 extended to WX.
- **G4** as ADR-0019 §9, for **every arm the mapping can select** (A0, A1, A2, A4, A5-C, A5-D and WX of each), plus:
  - each arm's forward and one training step in S0 are bit-identical to `studies.p9ii`'s on a shared rehearsal seed;
  - WX with W_X zero outside its last 224 columns, and equal to a W7 projection there, gives W7's query bit for bit; the zero padding is as §5.2;
  - schedules at 8K/4K, 8K/16K and 32K/64K equal the exposure-scaled formulas; at 65,536 slots the full-N score path and A4's k = N read are checked against a direct computation;
  - the read swap: π has no fixed point and no pair with equal answers; swapping twice restores the logits; the tie rule of §8.1;
  - no A1 or A2 cell exists at 8K/4K in the registry.
- **G9** seed disjointness (§7). **G10** the arm-selection record equals the auditor's independent evaluation of §3.2 on P9-II's committed records, whose hashes are recorded.
- The gates stage runs at real size on the rehearsal draw before the freeze and again on registered seeds before training. All gate outputs are written to the run directory and committed. A harness error is reported apart from a gate failure.
- **Manifests record the platform** (OS, architecture, Python, torch, thread settings). Bit-identity gates are asserted on the registered platform; tests that depend on it are platform-conditional.
- **Fixed launch scripts**, no free arguments, committed before the freeze and covered by its hash: gates, Q1, Q1 gate, WX, probe gate, probe, analysis, report. No registered stage is launched by a typed command.
- **Analysis and report are exercised before the freeze on synthetic records of the full registry:** every row of §3.3, every class under both criteria, every label, annotation and outcome of §8, every block status, missing cells, failed gates, non-finite values, a replaced draw, and each cut of §10.4.

### 10.3 Rehearsal

On the rehearsal draw, six single-thread workers, through the whitelist validator of P9-I (time, memory, shapes, counts, identity; no loss or accuracy is written or shown): every (arm, cell type, phase) of the frozen Q1 matrix, and WX and the 32K/64K cell for **every arm that can become the candidate** (A0, A1, A2 and C4), for 256 updates and one full evaluation with the read swap; A2 before and after its switch; A4 at k_0, mid-schedule and k = 8. Run twice: alone, and with twelve other busy single-thread processes **[lead's choice; S1 and S2 may be training on the same machine]**; the larger measured rate is used. A block's projection = measured seconds per update × planned updates (the most expensive possible candidate; A4's annealing at its most expensive measured rate) + measured evaluation, arranged in rounds of six.

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

Unmeasured and not in the table: L_addr's all-key backward, A4's wide read, WX's wider projection, the probes during training (about 2% in the ADR-0019 review's estimate), the read swap in evaluation.

**Cap: 16 charged hours for S0, one budget**, covering the pipeline check, rehearsal, gates and every registered block. Twice the largest projection is 9.9 / 11.9 / 14.6 h. At the slowest rates this leaves 1.4 h (about 10%) for everything unmeasured.

**Headroom rule.** After the rehearsal, the registered run starts only if (hours already charged) + 2 × (rehearsed projection of everything still to run, at the most expensive possible candidate) ≤ 16. Each block's own time cap is twice its rehearsed projection; a block that reaches it is stopped and is INCOMPLETE.

**Cut order if the rule does not hold (fixed now, applied in this order, recorded in the freeze):**

1. Drop WX (the variant prints NOT RUN; H20-L is not tested).
2. Drop the 65,536 probe (NOT RUN — BUDGET).
3. Drop the second seed at 8K/16K: every learned arm runs ten cells there, seeds alternating by draw as in 8K/4K; the 10-cell class rule of §8.3 applies at 8K/16K; the label states "one initialization seed per draw at 16,384".
4. Nothing else. If the rule still does not hold, nothing registered is run and the matter returns to the human lead. No draw, update count, threshold or exposure is changed.

**Memory.** 3 GiB per worker, 18 GiB aggregate; the rehearsal must show a peak of at most 1.5 GiB per worker (P9-I's peak was 1.49 GiB, in evaluation at 65,536). **If the rehearsal peak of a block's configuration exceeds 1.5 GiB per worker, that block is NOT RUN — MEMORY; nothing is changed to make it fit.** If that block is Q1, nothing registered is run and the matter returns to the human lead. Known risk: A4 at k = N = 65,536 gathers a value tensor of about 1.0 GiB in the forward pass alone (review, c1).

No timing-sensitive comparison is made between cells; CPU seconds are descriptive.

## 11. Implementation

New package `studies/p10s0/` importing `studies.p9ii`, `studies.p9i` and `studies.p9` unedited. New code: the mapping script, WX, the 8K/4K cell, the exposure-scaled schedules at 65,536, the read swap, the two-criteria classes, the replication labels, analysis and report. Records carry the study code P10S0. Implementation, gates and the pipeline check may start before P9-II's registered run finishes, because A0, A1 and A2 are in every branch and every possible fourth arm exists in P9-II's code; they need P9-II's code committed and its calibration record audited. The freeze cannot happen before P9-II's outcome is recomputed and committed.

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

1. Confirmation review of this revision by the auditor; any passage changed afterwards is re-checked.
2. The human lead's answer on §17 item 0 is recorded if it has arrived; it does not block S0 (the NOT-QUALIFIED text is neutral until then).
3. Lead's approval under the delegation (§18).
4. Implementation with tests and the fixed launch scripts. Pipeline check (§10.1).
5. Gates at real size on the rehearsal draw and the implementation audit, for every arm the mapping can select and WX of each, at every cell type of §6. Analysis and report on synthetic registries.
6. P9-II's registered outcome recomputed and committed. The mapping script on P9-II's committed records; arm-selection record; audited (G10).
7. Rehearsal, twice (§10.3), of the selected arms and of WX and the probe for every possible candidate; projections, caps, memory check, cuts of §10.4.
8. Generation and G1 of all draws; freeze of specification, code, config, launch scripts, seeds, thresholds, arm-selection record, projections, caps, cuts and data identities.
9. The registered run, once, by the launch scripts: gates; Q1; Q1 gate; WX; probe gate; probe.
10. Independent recomputation from raw records and snapshots by the auditor, Q1 first; outcome report with deviations, failed attempts and negative results kept.

## 14. Stop rules

- A failed gate, or any difference between the frozen and the running code, config, launch scripts, arm-selection record or data identities, stops the run.
- A block whose doubled projection does not fit is not started; a block that reaches its cap is stopped and is INCOMPLETE. Completed blocks stand.
- A failed cell is kept and not re-run.
- No re-run with changed settings. A second attempt after an engineering stop needs the human lead's decision, with everything observed in the first attempt listed.
- No registered seed is seen by a model before the freeze.
- If P9-II's outcome or calibration record is amended after S0's freeze, S0 stops and returns to the human lead.

## 15. What S0 cannot establish

- Anything about capacity, useful-capacity scaling, locality, transfer or adding facts later.
- That the interface works on natural language, on another backbone or student (S2's included), at loads other than 0.5 and, for label-free arms, 2 facts per slot, or under any regime other than 512 exposures per fact.
- Anything reliable about 65,536 slots: three draws, one initialization seed, a probe.
- That the interface finds where to read: the memory is told the answer position in every arm, WX included.
- That address labels are available in a real system, or why supervision works: the negative control A1-S is P9-II's and is not repeated.
- That an untuned transfer failing means the arm fails. λ, U_pre, k_0/N and μ were calibrated by P9-II on W7 at 4,096 slots; at two facts per slot, in WX and at 65,536 they are untested transfers. **A failure at a new condition is a failure of the recipe as calibrated at 4,096 on W7, not necessarily of the arm.**
- That a qualified arm beats a tuned baseline: A0 is untuned by design.
- That the record length is required, from a WX failure.
- A success probability above the printed per-draw bounds.
- That a qualification overrides P9-II. If S0 and P9-II disagree on an arm, both classes and the pooled count are printed; S0's label rests on S0's draws, and the disagreement is part of the label.
- Any efficiency, latency or storage claim.
- A failure of the ArborLM concept, whatever the outcome.

## 16. Requirements map

| The human lead's requirement | Where |
|---|---|
| P9-II interventions as a gate, not assumed to have succeeded | A1 and A2 are re-tested on S0's own draws in every branch (§3.1); P9-II adds at most one arm (§3.2) |
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

## 18. Approval record

The human lead's words, verbatim:

> "we can change it to  p10 can be self approve but p10-I need my review"

> "im confortable with does number if it mean it will resolve most dough and close any posible misguidence due to a small set"

The second sentence was his answer on the P10 budgets (S0 16 hours, S1 12 hours, S2 36 hours), as relayed by the lead.

The lead's conditions for using the delegation, as in ADR-0019 §16: (1) the specification review ends with no open blocker or major; (2) the implementation audit is clean before the freeze; (3) the rehearsal shows 2× headroom; (4) nothing changes after the arm-selection record except the cuts of §10.4; (5) no registered seed has been observed; (6) P9-II's outcome is recomputed and committed before the freeze.

Lead's approval: PENDING the confirmation review.

## 19. How revision 2 answers the review

Review: `adr-0020-review/REVIEW.md` (Opus 5.5), verdict NOT READY.

| Finding | Change in revision 2 |
|---|---|
| **B1** readings of the human lead's direction decided inside the ADR | Items 1 and 2: resolved by the lead's ruling to take the direction literally, so no reading is needed. S0 always runs and always contains A0, A1 and A2 on its own draws (§3.1); P9-II adds at most one arm (§3.2). The reviewer's paste-ready item 0 (a) and (b) is therefore **not adopted**; its alternative ("always run a fixed Q1") is, without the fourth "best label-free arm" as a fixed member and **without the pooled class rule the reviewer said it would need**: by the lead's ruling the candidate comes from S0's own classes, and P9-II's class, the replication label and the pooled count are printed with it (§8.4, §8.7, §15). The confirmation review should look at this point. Item 3: kept as a question for the human lead with the reviewer's text (§17 item 0); the NOT-QUALIFIED text is neutral until answered (§8.7) |
| **B2** no target injection at 8K/4K | Option (a). §5.1: A1 and A2 are not run at 8K/4K; NOT RUN — NO TARGET INJECTION; §6.1, §8.6, §9.1, G4 |
| **M1** mapping non-determinism, mislabel, missing rows | Adopted for the reduced mapping: fixed reading order (§3.2), a class of a non-COMPLETE Stage 2 is not read, every outcome enumerated including carried-A0 and excluded-A0 families (§3.3). The exclusion mislabel cannot occur: S0 always runs and never prints "P9-II INCONCLUSIVE". G10 requires an independent evaluation from the text |
| **M2** scope SMALL | Moot. S0 always runs its full core scope; SMALL, E, E4 and "no second chance" no longer exist. ADDRESSING-QUALIFIED AT 4,096 ONLY remains as an outcome of S0's own classes and permits nothing (§9.1) |
| **M3** 65,536 as headline label | Adopted. One label, ADDRESSING-QUALIFIED (4,096 AND 16,384); 65,536 is an annotation probe of the candidate and A6, 3 draws × 1 seed, 6 cells, printed with 0.368 and "probe; not a qualification" (§6.2, §8.6) |
| **M4** NOT REPLICATED mixes replication with added criteria | Adopted. Two classes per arm and cell type (§8.3); replication labels from the class under P9-II's criteria (§8.4); NOT QUALIFIED IN S0 names the added criterion (§8.7); H20-R reads replication only. "No failed cell" is gone, so the added criteria are condition 6 and ADDRESS STABLE |
| **M5** order of work | Adopted and adapted (§13 steps 5–7): gates for every selectable arm before the arm-selection record; rehearsal after it. Because the candidate is known only after Q1, the rehearsal covers WX and the probe for every possible candidate |
| **M6** Q3 | Option (a): dropped. §12.2 lists it for the integrated study or P10-I with the reviewer's corrections |
| **M7** interface with ADR-0021 | Adopted against ADR-0021 revision 2 as described by the lead (§9.1): 8K/4K needed for the lane's only step; no 65,536; 4·F updates; S0's success rule at all three cells; acceptance left to ADR-0021. §9.2 states that in the expected timeline the lane will be omitted |
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

## 20. The lead's choices in this revision (fixed before any rehearsal)

| No. | Choice | Where |
|---|---|---|
| 1 | S0 always runs with A0, A1, A2, A6, A7; at most one fourth arm, P9-II's carried arm if it is A4, A5-C or A5-D; no X2 | §3 |
| 2 | Candidate from S0's own classes; preference order C4, A2, A1, A0 ("answer-only suffices") | §8.5 |
| 3 | Ten registered draws × two init seeds at 2K/4K and 8K/16K; one seed at 8K/4K and for WX; probe three draws × one seed | §6 |
| 4 | RELIABLE at 20 cells: at most one failed cell, no draw with both seeds failed; UNRELIABLE from 5 successes; NOT_EVALUATED above one unevaluated draw | §8.3 |
| 5 | 10-cell types: at most one failed cell; UNRELIABLE from 3 successes (drafter's proposal, to be confirmed by the lead) | §8.3 |
| 6 | Condition 6 at 0.95; oracle floor 0.50 at 8K/4K | §8.2 |
| 7 | A1 and A2 not run at 8K/4K | §5.1 |
| 8 | 65,536 as an annotation probe, never in the label | §8.6 |
| 9 | Q3 dropped | §12.2 |
| 10 | WX initializer at fan-in 2,048; WX on the Q1 draws after the gate (drafter's consequence of choice 2, to be confirmed) | §5.2, §6.2 |
| 11 | One cap of 16 charged hours; cut order WX, probe, second seed at 8K/16K; nothing else | §10.4 |
| 12 | Rehearsal twice, the second under twelve busy processes | §10.3 |
| 13 | Bounded seed namespaces | §7 |
| 14 | NOT-QUALIFIED text neutral about S1 and S2 until the human lead answers | §8.7, §17 |
| 15 | Order of the alternatives | §12.1 |

## Points the drafter could not settle (for the lead and the confirmation review)

1. **Qualification on S0's classes alone when P9-II registered a failure.** If P9-II classes A2 UNRELIABLE at 16,384 and S0 classes it RELIABLE, A2 is qualified with DOES NOT REPLICATE P9-II in its label. The reviewer said an always-run design needs a pooled rule; the ruling does not include one. The text prints the pooled count but uses no pooled rule.
2. **A0 last in the preference order.** If A0 and A1 both meet the criteria and C4 and A2 do not, the qualified interface is A1, which needs address labels, although the label-free A0 also qualifies. The text prints ANSWER-ONLY ALSO MEETS THE CRITERIA. ADR-0019's carry-forward order puts A0 first.
3. **"S0 ALWAYS runs" has one exception:** no audited P9-II calibration record means λ and U_pre are undefined (§3.2 item 1).
4. **The fourth arm exists only if P9-II's Stage 2 is COMPLETE and carries A4, A5-C or A5-D.** A label-free arm RELIABLE at 4,096 only, or behind A0 in P9-II's order, is not tested in S0.
5. **WX and the probe need the candidate, which is known only after Q1.** They therefore run after the Q1 gate, WX on the Q1 draws. If the lead wants WX on fresh draws it costs twenty more reference cells.
6. **The 10-cell class rule and the UNRELIABLE cut at 5 of 20** are the drafter's numbers; the ruling fixed only RELIABLE at 20 cells.
7. **ADR-0021 revision 2 was not available**; §9.1 follows the lead's description of it.
8. **Headroom at the slowest rates is about 10%** before unmeasured costs; cut 1 or 2 is likely if L_addr or A4 is slow at 16,384.

Astra review: NOT_PERFORMED. A Claude review is not an Astra review, and this document is not a human approval.
