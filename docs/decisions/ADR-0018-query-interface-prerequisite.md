# ADR-0018 — The query interface: can the model tell its memory what it needs? (P9-I)

- **Status: DESIGN REVISION 3 — NOT APPROVED. SPEC: PENDING ASTRA REVIEW. No implementation, calibration or execution is authorized by this text.**
- **Date:** 2026-11-14
- **Origin.** ADR-0017 revision 3 is CALIBRATION BLOCKED by the human lead's direction of 2026-11-14 (ADR-0017 §15.2): "we may first need to solve a more fundamental problem: How does the language model reliably communicate what information it needs to its memory?", and "correct the scientific design if the findings hold, and only then authorize a new execution."
- **Evidence it rests on.** `results/p9-calibration-2026-11-14/`; the independent audit `docs/reviews/p9-calibration-audit-2026-11-14/AUDIT.md`; and the independent design review of revision 1, `docs/reviews/adr-0018-design-2026-11-14/REVIEW.md` (both Opus 5.5). The review's probes are representation-only, on rehearsal draw 0. They are feasibility evidence, not results of this study.
- **Revision history.** Revision 1 (commit `80155d6`) was reviewed NOT READY: 2 blockers, 6 majors, 14 minors. Revision 2 (commit `649f76f`) applied them; the auditor's confirmation (`docs/reviews/adr-0018-design-2026-11-14/CONFIRM.md`) found no blocker and required four text edits (R1–R4). Revision 3 applies R1–R4 and the minors n1–n8. §16 maps each finding to its change.
- **Roles (proposed, study-specific).** Lead: Claude Fable 5.2. Audit: Opus 5.5. Implementation: Sonnet 5.5. Inventory: Haiku 5.5. ADR-0012 stays not approved. **Astra review: NOT_PERFORMED.**
- **Relation to ADR-0017.** ADR-0017 stays blocked. This study is its prerequisite. It tests none of H17-CAP, H17-UTIL, H17-LOC, H17-INC. Its outcome selects, by a rule fixed here, the interface with which ADR-0017 would be revised, or records that none was selected. ADR-0017 §15.2 recorded the intent as "a new revision" of ADR-0017; a separate ADR departs from that and is the human's choice (§14.1). **Its cost:** ADR-0017 still needs its own revision, audit, calibration and two approvals afterwards.

## 1. What is known

On the frozen 27,392-parameter backbones, with five-symbol checksum identifiers (20 bits), rehearsal seeds:

- The hidden state at the answer site carries 0.4 bits of the identifier by a linear probe and 1.0–1.4 by a small non-linear probe. Each identifier position carries its own symbol and almost nothing else. The record's seven input positions together carry 19.8–20.0 bits.
- Attention from the answer site is near-uniform; no head gathers the identifier.
- Content written by a memory at earlier positions does not reach the answer site through the frozen upper block: a perfect per-fact vector at the six earlier positions gives 2.8–4.7% (chance 3.1%), the same vector at the answer site 96.9%.
- Given the right slot, the readout works (97–100%). It learns by number of optimizer updates of the shared output projection and gate, not by exposures per fact.
- Training on all 256 output bytes while scoring within the 32-symbol alphabet costs one symbol on one backbone and slows learning severalfold (16,384 slots at 2,048 updates: 0.68 against 0.993 with the alphabet loss).

So the memory can store and return an answer, and the backbone cannot say which answer it wants. That is a property of this testbed. It is not evidence about the ArborLM concept.

## 2. Scope, question and hypotheses

**Scope.** W7, E7, A4 and A4E are query encoders that belong to the memory; they read the frozen states (or the embeddings) of the input. A WORKS class for one of them shows that a memory-side encoder can address facts on this task. It does not show that the language model communicates what it needs. Unless BACKBONE CONTRIBUTES holds (§8.2), the outcome is reported as "addressed by a memory-side encoder of the input; the frozen backbone contributes nothing to addressing". Only arm BB (§3.2), which runs if the human lead chooses it (§14.2), lets the model itself form the query.

**Question.** Can a small learned interface deliver a fact's identity to the memory at the position where the answer is produced, what is the least such interface, and does it need the model to change?

- **H18-NAT (expected to fail; baseline).** The natural query — a learned linear projection of the answer-site hidden state — retrieves facts above chance.
- **H18-WIN.** A learned linear query over the hidden states of the last seven positions retrieves facts nearly as well as an oracle query.
- **H18-ATT.** A learned four-head attention layer over the causal prefix forms a query that retrieves facts nearly as well as an oracle query, without being given a window. The auditor's probe predicts this fails over frozen states.
- **H18-BB (does the frozen backbone contribute?).** The window query over block-0 states is better than the same query over raw embeddings. The auditor's probe on rehearsal draw 0 predicts the opposite: E7 ≥ W7.
- **H18-MODEL (only under §14.2 option b).** With the block-0 attention trained together with the memory, the natural query retrieves facts nearly as well as an oracle query.

Each can fail. Every class is a statement "within U updates" (§6), not about what longer training could reach.

## 3. Interfaces under test

All use the flat memory of ADR-0017 §5 (cosine keys, top-8, temperature 0.2, key width 16), read **at the answer site only**, and add the read there. Reading at other positions is not used: §1 shows it cannot reach the answer.

### 3.1 Core arms

| Arm | Query at the answer site t | Trained | Extra parameters |
|---|---|---|---|
| N natural | W·h_t | keys, values, W, output projection, gate | — (historical) |
| W7 window | W·[h_{t−6}; …; h_t] | as N, with the wider W | 16 × 224 − 16 × 32 = 3,072 |
| E7 embedding window | W·[e_{t−6}; …; e_t], e = token + position embedding (no block) | as W7 | 3,072 |
| A4 attention | one attention layer, 4 heads × 8, bias-free q, k, v (32 × 32 each); query from h_t, keys and values over the full causal prefix h_0…h_t; in the form of the backbone's attention (causal, scores scaled by 1/√8, no layer norm, no output projection); its output, then W | as N, plus the layer | 3 × 32 × 32 = 3,072 |
| A4E | A4 with e in place of h | as A4 | 3,072 |
| R1 oracle-query reference | fixed random unit code per fact (ADR-0017 §5.3) | keys, values, output projection, gate | — |
| R2 oracle address | dedicated slot per fact | values, output projection, gate | — |

- h is the frozen block-0 output; the frozen backbone is unchanged in every core arm. The interface is part of the memory addition and is trained with it.
- **W7 is told the record length** (seven positions). That is the task leaking into the design, and is stated with every W7 result.
- **A4 is given no window.** It must learn where to look in the whole prefix. This is the reason it is preferred over W7 when both work. The auditor probed a 16-position window (two records, also task-shaped); the full-prefix form is unprobed.
- **A1 (one head) is withdrawn.** One head with one shared value map is close to a weighted bag of symbols: the probe gave 0.34 / 0.24 / 0.16 at 2,048 / 8,192 / 32,768 facts (B101), and its noise-free idealization 0.81 at 32,768. The numbers are kept in the review.
- **R1 is a reference, not a ceiling:** optimized additive codes match or exceed random codes, so η (§5) may exceed 1.
- **Tree variants are withdrawn.** They entered no rule. Routing with the selected interface belongs to the revision of ADR-0017.

### 3.2 Arm BB — the model forms the query (runs only under §14.2 option b)

- **BB:** the block-0 attention of the backbone (qkv and output projection, 4,224 parameters) is trained together with the memory. Everything else in the backbone stays frozen. The memory reads arm N's natural query W·h_t at the answer site. AdamW, lr 0.003, in the same group as the output projection and gate (ADR-0017 §5.1; the key and value tables keep row-lazy Adam at 0.012); the same gradient clip covers it.
- **BB-D:** D plain (§3.3) with the same trainable attention.
- **BB-0:** no memory; the same trainable attention, trained on the answer loss alone.
- BB needs approval to train a backbone parameter. It leaves the P4–P8 frozen-backbone lineage; `docs/RESEARCH_HANDOFF.md` names joint training of backbone and memory as the eventual path.
- The backbone's next-byte loss on its own corpus rows is reported before and after for BB, BB-D and BB-0 (descriptive; the answer loss does not protect it).
- Feasibility evidence, not a result: the input a retrained block-0 attention sees is the embedding, and four heads over embeddings reach 0.99 / 0.97 / 0.85 in the oracle-store probe (B101; B102 0.98 / 0.94 / 0.81).

### 3.3 Dense controls

- **D plain:** the P4/P5 adapter on h_t, parameter-matched to arm N. Expected at chance.
- **D7 window:** the adapter on [h_{t−6}; …; h_t], hidden width set so its parameter count matches arm W7 **including the interface** within 0.1% (786 / 3,090 / 12,306 hidden units at the three sizes). Same window, same parameters, same updates.
- **D plain, D7 and BB-D add their output at answer sites only**, like the memory.

## 4. Task, data, loss

- Task, identifiers, templates, clusters, streams and panels exactly as ADR-0017 §4 (family 1), with the data generator already implemented and its gate G1.
- **Loss: cross-entropy over the 32 alphabet symbols at answer sites**, for every arm. Scoring is the most probable alphabet symbol, ties wrong. Loss and scoring use the same output set. Training is therefore not comparable with ADR-0017's R0a or P4–P8, which use the 256-way loss.
- **Matched updates.** Every cell runs the same number of updates U, and **U is the same at every size** (§6). Exposures per fact therefore differ across sizes (sixteenfold: 256 / 64 / 16 at U = 4,096) and are reported per size. Matched exposure is not used in any rule.
- Nothing is added at non-answer positions in any core arm. In the BB arms the trained attention changes all positions; that is reported (§3.2).

## 5. Measurements

- Accuracy on primary panels A and B; H1/H2 and mixed-cluster panels secondary. **Every rule in §8 uses accuracy.** I_acc (Fano bound with the chance floor, ADR-0017 §6.1), the Σ-renormalized log-loss gain (ADR-0017 §6.1 secondary) and the 256-way loss are reported descriptively.
- **Interface efficiency** η = accuracy(arm) / accuracy(R1), same size, seed and panel.
- Query diagnostics: mean cosine between queries of different facts; share of facts whose nearest other query is closer than 0.9; for A4, A4E and BB, the attention weight on the five identifier positions.
- Memory dependence: value permutation and disabling; minimal supports as ADR-0017 §6.2 restricted to the answer-site read.
- No-memory baseline, exact retrieval, unseen-fact control with the LEAKAGE flag; gate G2 as ADR-0017 §8.1. **"Chance" in every rule means inside the G2 interval.**
- Training diagnostics of ADR-0017 §6.3; parameters and optimizer-state bytes per arm.

## 6. Calibration (fresh rehearsal draw, before the freeze)

Draw 0 informed this design, so calibration uses rehearsal draw 1 (data seeds 179101 upward), which no one has observed. Rehearsal draws are limited to k ≤ 9.

- Allowed: controls; **R2 and R1** at the three sizes with the alphabet loss, snapshots at 1,024 / 2,048 / 4,096 / 8,192 / 16,384 updates. Initialization seeds 1791 and 1792 on parent B101/O301, and 1791 on B102/O302 (calibration only; never registered).
- **Rule:** U is the smallest of {2,048, 4,096, 8,192, 16,384} at which, at every size, R2 accuracy ≥ 0.95 **and R1 accuracy ≥ 0.90**. Each is the minimum over the two B101 calibration runs and both panels; the B102 run is reported.
- A size at which no U qualifies is `TASK_CEILING_FAIL` (R2) or `ORACLE_QUERY_FAIL` (R1) and is not run. U is then the smallest value qualifying at the remaining sizes.
- R1 is an oracle rung, not an interface. No arm of §3 other than R1 and R2 is run, and no representation probe is run on draw 1.
- No BB arm is calibrated. A BB class below INTERFACE_WORKS is a statement within a U calibrated on the frozen backbone's oracle rungs.
- If calibration marks any size failed, the outcome is INCONCLUSIVE by §8.3 step 0 before the run; the human lead decides at decision 2 whether the remaining sizes are run.
- After calibration only U and the failed sizes may change. Anything else is a new revision.

## 7. Matrix and seeds

Initialization seeds 1801 and 1802 on parent B101/O301; one replicate (seed 1801, parent B102/O302) where marked. **Registered data seeds 182001 upward** (clear of the rehearsal range 179001–179999 and of the constants 180101–181900 the auditor's probe scripts used). ADR-0017's registered seeds stay unused.

| Size (slots / facts) | Arms | Cells |
|---|---|---|
| 16,384 / 8,192 | N, W7, E7, A4, A4E, R1, R2, D plain, D7 | 18, + B102 replicate of W7, A4, R1, D7 = 22 |
| 65,536 / 32,768 | N, W7, A4, R1, D7 | 10 |
| 4,096 / 2,048 | N, W7, A4, R1 | 8 |
| **Core total** | | **40** |
| Block BB (option b only): 16,384 and 65,536 | BB, BB-D, BB-0 | 12, + B102 replicate of BB at 16,384 = 13 |
| Block BB: 4,096 | BB, BB-0 | 4 |
| **Total with block BB** | | **57** |

Three sizes are included so that the selected interface is known to work across the range ADR-0017 needs, not to measure capacity. No capacity class is derived here.

## 8. Classes and the selection rule

### 8.1 Interface class

For W7, A4 and BB (E7, A4E and N are classified the same way for the record), at a size:

**Step 1 — raw class per B101 seed and panel, first match wins.**

| Order | Raw class | Rule |
|---|---|---|
| 1 | NOT_EVALUATED | R1 accuracy below 0.5 at that size, in any B101 seed or panel (then every seed and panel of that size is NOT_EVALUATED) |
| 2 | WORKS | accuracy ≥ 0.5 and η ≥ 0.90; value permutation and disabling give chance |
| 3 | PARTIAL | accuracy above the G2 interval and ≥ 0.25, not row 2 |
| 4 | FAILS | otherwise |

**Step 2 — class at the size, first match wins.**

| Order | Class | Rule |
|---|---|---|
| 1 | NOT_EVALUATED | raw class NOT_EVALUATED (R1 below 0.5 at that size) |
| 2 | NOT REPLICATED | for at least one B101 seed, the raw classes on Panels A and B differ |
| 3 | INTERMEDIATE | not row 2, and the two B101 seeds give different raw classes |
| 4 | INTERFACE_WORKS / INTERFACE_PARTIAL / INTERFACE_FAILS | the common raw class of all four seed–panel pairs |

Step 0 of §8.3 refers to the size: a size is NOT_EVALUATED when R1 is below 0.5 there, whatever an arm prints.

The B102 replicate is reported and must not have raw class FAILS on either panel for INTERFACE_WORKS to stand at 16,384; otherwise the class there is INTERMEDIATE.

For BB, after the B102 rule: a class INTERFACE_WORKS becomes **MODEL_STORES_FACTS** if BB-0's accuracy is above the G2 interval at that size on either B101 seed or panel. Reading fixed now: the trainable attention can by itself retrieve facts at that size, so BB's result cannot be attributed to the memory interface alone, even though BB's own ablations show that it uses its memory.

### 8.2 Annotations (printed per size; they do not change a class)

- **Dense comparison**, for W7 against D7 and BB against BB-D, at each size where both run. Compared only if the arm's class is INTERFACE_WORKS or INTERFACE_PARTIAL; otherwise NOT COMPARED. With r = accuracy(arm) / accuracy(dense), paired by seed and panel, the smallest of the four values: **BEATS DENSE** if r ≥ 1.10; **DENSE SUFFICES** otherwise. BEATS DENSE is unreachable when the dense accuracy exceeds 1/1.10 ≈ 0.909; DENSE SUFFICES then means within 10% relative accuracy. Reading fixed now: DENSE SUFFICES means a dense adapter on the same input does as well within U updates at that size. It is a statement about this task and budget, not about the query interface or about memory in general. The auditor's toy predicts DENSE SUFFICES at 16,384 and probably not at 65,536; such a difference between sizes would be consistent with the sixteenfold difference in exposures per fact and is not evidence about capacity or the interface. A4 and A4E have no dense comparator (no dense arm reads the full prefix); their dense comparison is NOT COMPARED, and that is carried if A4 is selected.
- **Backbone contrast** at 16,384, for the pairs E7/W7 and A4E/A4. With r = accuracy(embedding arm) / accuracy(state arm), paired by B101 seed and panel (four values): **BACKBONE HURTS ADDRESSING** if all four r ≥ 1.03; else **BACKBONE ADDS NOTHING** if all four r ≥ 0.97; else **BACKBONE CONTRIBUTES** if all four r < 0.97; else **BACKBONE CONTRAST MIXED**. Not printed if both arms are INTERFACE_FAILS. BACKBONE HURTS is unreachable when the state arm exceeds 0.971.
- **Language modelling** (BB arms only): **LANGUAGE MODELLING DEGRADED** if the backbone's next-byte loss on its own corpus rows rises by more than 5% relative to before training, on either B101 seed. It does not block selection; it is carried with BB, and whether a degraded backbone is acceptable is the human lead's decision when ADR-0017 is revised.

### 8.3 Selection rule for a revision of ADR-0017 (fixed now)

0. If any of the three sizes is TASK_CEILING_FAIL, ORACLE_QUERY_FAIL or NOT_EVALUATED → **INCONCLUSIVE AT that size.** No interface is selected, the classes at the remaining sizes are reported, and the human lead decides. This is not step 4.
1. (Option b only.) If BB is INTERFACE_WORKS at all three sizes → BB: the model forms the query. A revision of ADR-0017 would then train the block-0 attention, and needs approval for that.
2. Else if A4 is INTERFACE_WORKS at all three sizes → A4.
3. Else if W7 is INTERFACE_WORKS at all three sizes → W7, with the limit that it is told the record length.
4. Else → no tested interface reached INTERFACE_WORKS at all three sizes within U updates; the class of each arm at each size is reported; ADR-0017 stays blocked on this backbone.

The selected interface carries its scope statement (§2), its backbone-contrast annotation and its dense-comparison annotation into the revision of ADR-0017 and into every summary. If BB is selected, the before/after next-byte loss of BB, BB-D and BB-0 and the language-modelling annotation are carried with it. If A4 or W7 is selected, ADR-0017 would test a memory with its own input encoder, a different system from the P4–P8 memory addressed by the backbone's state.

## 9. Gates and status

- G1 (generator), G2 (chance; 8 tests as ADR-0017 §8.1).
- G4: determinism and checkpoint restoration. For equal parameters and inputs, arm N's forward equals ADR-0017's R0a forward bit for bit; training differs by the loss. At initialization, BB's forward equals N's, BB-D's equals D plain's and BB-0's equals the no-memory baseline's.
- `ENGINEERING_FAIL`, `INCOMPLETE` and no re-run with changed settings, as ADR-0017 §8.6. No cell here depends on another.

## 10. Resources (projection, not a measurement of this study)

- Measured in P9: R2 at 65,536 slots ran 32,768 updates in 386 s (0.012 s per update). That is the only measurement. With the auditor's assumed costs (0.05 / 0.02 / 0.015 s per update at 65,536 / 16,384 / 4,096 slots), the core matrix takes 2.4 hours serial at U = 8,192 and 4.8 hours serial at U = 16,384, or about 0.4 and 0.8 hours with six single-thread workers. Block BB backpropagates through block 0 at every position and is not estimated; the rehearsal measures it.
- Calibration (18 runs up to 16,384 updates): about 93 minutes serial, about 16 minutes with six workers, at assumed costs.
- **Proposed caps, for the human lead's explicit decision (§14.3):** 3 GiB per worker and 24 GiB aggregate (as decided for ADR-0017); 4 hours for calibration, rehearsal and the run together for the core matrix, 6 hours with block BB. The rehearsal measures time and memory only and fixes the stage caps.

## 11. Implementation

- New package `studies/p9i/` beside `studies/p9/`, importing the P9 data, memory, training, evaluation and job-manager code. **Imported P9 code is tested, not audited** (the calibration audit covered R2, the probes, G2, the controls and the exposure rule only). The ADR-0018 implementation audit covers every imported path used.
- No existing file changes; ADR-0017's code and records stay as they are. Records carry this study's code (P9I), not P9.
- The alphabet loss, answer-site-only reads and dense outputs, matched updates and the trainable block-0 attention are added in the new package.

## 12. Order of work

1. Auditor confirmation of this revision; revise until ready.
2. **Human decision 1:** the choices of §14, and approval for implementation, calibration and rehearsal.
3. Implementation with tests (gradient reach for each interface; arm N forward identical to R0a; D7 parameter match; BB trains only the 4,224 attention parameters; every class, annotation and selection outcome triggered on synthetic records).
4. Calibration on rehearsal draw 1 (§6); audited.
5. Rehearsal for time and memory; implementation audit; freeze.
6. **Human decision 2:** approve the frozen revision and the run.
7. The run, once; independent recomputation; report.

## 13. What must not be claimed

- Anything about capacity scaling, utilization, locality or incremental learning. None is tested. **A difference in class between sizes is not evidence about capacity:** exposures per fact differ sixteenfold.
- That a WORKS class for W7, E7, A4 or A4E shows the language model communicating what it needs (§2).
- That INTERFACE_WORKS for BB shows that a language model reliably communicates what it needs. BB retrains the block-0 attention on this task's answer loss alone, with its next-byte loss unprotected; it shows that a jointly trained backbone attention can form a query for this synthetic task within U updates.
- That an interface that works here would work on natural language. The task has fixed-length records and random identifiers.
- That W7 is a general interface: it is told the record length.
- That a failure of all interfaces is a failure of the ArborLM concept, or more than a statement about this backbone within U updates.
- That DENSE SUFFICES says memory is not needed in general.
- That the oracle rungs are systems.

## 14. Decisions reserved for the human lead

1. **Separate study or revision.** Whether the prerequisite is this separate ADR or is folded into a revision of ADR-0017 (cost of the separate ADR stated in the header).
2. **The question asked.** (a) Accept that the study tests memory-side encoders only, so that "how does the language model communicate what it needs" stays open; or (b) add block BB (§3.2, 17 cells), which trains 4,224 parameters of the backbone's block-0 attention and needs approval to train a backbone parameter. The lead recommends (b): without it no arm answers the question as asked, and the probes already predict that the frozen states add nothing. Costs of (b): it leaves the P4–P8 frozen-backbone lineage; 17 more cells whose time is not estimated (cap +2 hours); BB is first in the selection rule, so a revision of ADR-0017 would then train a backbone parameter; U is not calibrated for BB; the answer loss does not protect the backbone's language modelling. Option (a) is cheaper and keeps the lineage, but leaves the question as asked open.
3. **Budget.** The caps of §10.
4. Decisions 1 and 2 of §12.
5. ADR-0012; merge; publication; any next phase.

## 15. Approval record

None. Pending.

## 16. Map of the revision-1 review to this revision

| Finding | Change |
|---|---|
| B1 scope dodges the question | §2 scope paragraph; §3.2 arm BB; §8.3 carries annotations; §14.2 as a choice |
| B2 U calibrated on R2 only | §6 calibrates on R2 and R1 (0.90), adds 16,384 updates; §8.3 step 0 INCONCLUSIVE |
| M1 one head is a bag of symbols | A1 withdrawn; A4 (full prefix) and A4E added |
| M2 dense annotations overlap | one ratio, exclusive labels, dense arms at answer sites only, fixed reading (§8.2) |
| M3 backbone annotation one-sided | three-way backbone contrast, both pairs (§8.2); prediction in H18-BB |
| M4 precedence incomplete | two-step tables (§8.1) |
| M5 "audited" imports | §11 "tested, not audited"; G4 reworded |
| M6 exposure bias inverted | §4 exposures per size; §13 |
| m1 timing figure | §10 uses the measured 0.012 s and the auditor's estimate |
| m2 seed collision | registered data seeds 182001 upward; draws k ≤ 9 |
| m3 calibration init seeds | 1791, 1792 (§6) |
| m4 N at 4,096 | added (§7) |
| m5 R1 a reference | §3.1 |
| m6 one metric family | accuracy in every rule (§5, §8) |
| m7 Σ-renormalized loss | §5 |
| m8 "fourfold" | §1 |
| m9 Astra marker | status line |
| m10 cost of a separate ADR | header, §14.1 |
| m11 hour cap | §10, §14.3 |
| m12 parameter counts | confirmed; D7 widths stated (§3.3) |
| m13 tree arms | withdrawn (§3.1) |
| m14 chance defined | §5 |
| J(i) probes in calibration | not adopted: nothing but R1 and R2 is observed on draw 1 |
| J(ii) 2 × 2 | adopted under option b: {W7, BB} × {memory, dense} |

### Confirmation of revision 2 (CONFIRM.md)

| Finding | Change |
|---|---|
| R1 precedence and panel disagreement | §8.1 step 2 replaced |
| R2 backbone contrast default | four-way rule (§8.2); §2 scope "unless BACKBONE CONTRIBUTES" |
| R3 BB block | BB-0 added at 4,096 (57 cells); MODEL_STORES_FACTS reworded and ordered after the B102 rule; learning rate stated; U not calibrated for BB |
| R4 BB over-reading | §13 line; next-byte loss carried; lead's choice: LANGUAGE MODELLING DEGRADED annotation at 5%, not a block on selection |
| n1–n8 | §8.2, §8.3 step 4, §6, §10, §14.2, §3.1 (A4 form), §9 |
