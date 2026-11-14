# ADR-0017 — Parallel useful-capacity, anti-collapse and locality diagnostics (P9)

- **Status: REVISION 4. Lanes A–D (§1–§14): CALIBRATION BLOCKED (human lead, 2026-11-14, §15.2), not scientifically failed, no run authorized. Part I (§18, the query-interface prerequisite): APPROVED on 2026-11-14 for implementation, calibration and rehearsal, with decision 2 delegated to the lead within the limits of §15.3. SPEC: PENDING ASTRA REVIEW. Nothing of Part I has run.**
- **Date:** 2026-11-14
- **Revision history.**
  - Revision 0: the human lead's draft, unchanged at `docs/reviews/adr-0017-design-2026-11-14/ADR-0017-draft-rev0-human.md`.
  - Revision 1: the Claude lead's design (git history). Reviewed by Opus 5.5: **NOT READY**, 3 blockers, 14 major, 18 minor — `docs/reviews/adr-0017-design-2026-11-14/REVIEW.md`.
  - Revision 2 answered that review (git history `e46d5f8`). Re-checked by Opus 5.5: **NOT READY**, 3 blockers — `RECHECK.md` in the same folder.
  - Revision 3 (this text) applies the re-check's changes W1–W31; §16 and §17 map findings to changes. Where the auditor left a number to the lead, the lead's choice is marked *(lead's choice)*. Revision 3 was confirmed by Opus 5.5 (`CONFIRM.md`), with fixes F1–F15 applied verbatim.
  - Revision 4 adds Part I (§18), the query-interface prerequisite. It was drafted and reviewed as ADR-0018 (revisions 1–3; `docs/reviews/adr-0018-design-2026-11-14/REVIEW.md`, `CONFIRM.md`) and folded in here by the human lead's decision (§15.3). §1–§14, §16 and §17 are unchanged from revision 3. In those reviews "ADR-0018 §n" is §I.n here.
- **Origin.** The human lead asked in chat on 2026-11-14 for the design to begin and stated that the request is not permission to launch the study.
- **Roles (proposed, study-specific).** Lead: Claude Fable 5.2. Independent audit: Opus 5.5. Implementation and simulations: Sonnet 5.5. Inventory: Haiku 5.5. Actual models are recorded per delegation. ADR-0012 stays not approved. **Astra review: NOT_PERFORMED.**
- **Companions:** `EXECUTION_PLAN.md`, `RESOURCE_BUDGET.md`, `EVIDENCE_INVENTORY.md`, `REVIEW.md`, `RECHECK.md` in `docs/reviews/adr-0017-design-2026-11-14/`.

## 0. Departures from the human draft that need the human lead's explicit acceptance

1. **Family 2 (compositional) is not run.** With one memory read between frozen layers no read can depend on another read's result, so a latent two-hop answer cannot be computed (auditor confirmed). An explicit chained version would test lookup under a changed template, not composition. Running it would spend cells on a result that cannot bear the name. It is described in §4.5 as an option the human lead can restore. The draft's question whether more memory "supports computation rather than merely a lookup table" is therefore not answered by this study.
2. **Two approvals instead of one** (§12): approval of this specification for implementation, calibration and rehearsal; later, approval of the frozen final revision for the run.
3. **A testbed calibration before the freeze** (§12 step 4), on rehearsal seeds, limited to controls and the readout rung, able to change only the exposure count from a fixed menu and to mark a size TASK_CEILING_FAIL (§8 opening).
4. **Caps are proposed, and fixed only at the second approval** on rehearsal evidence (§11). The projection exceeds the draft's 8 hours and 2 GiB.
5. **MPS is not used.** Equal frequency only; skewed fact frequency is untested.
6. **Cache size follows distinct selected slots on the calibration stream**, and is also reported against useful slots (§8.4).
7. **The tree is not required to beat the flat memory on quality.** D03 is read as: not worse than 0.97 of flat at lower logical work is TREE_COMPETITIVE; at least 1.03 is TREE_AHEAD (§8.2).
8. **Key-on-storage is an arithmetic identity, not a corrected simulation** (§9).
9. **Incremental classes are defined against the dense sequential arm.** Replay and exact retrieval are run and reported beside them, but enter no class (§8.5).
10. **Oracle routing for the tree is run at 16,384 slots only**; the 4,096-slot ladder omits R0a (§10).
11. **One independent audit covers all lanes**, with a section per lane, instead of one audit per lane.
12. **One data draw.** Seeds replicate initialization, not data.

## 1. Evidence boundary

Stated as the records state it (`EVIDENCE_INVENTORY.md`):

- P4: a bounded frozen-backbone contribution from sparse memory; the dense adapter had lower loss in all 27 matched comparisons and the composite criterion failed.
- P5–P7-B: no compelling advantage of the fixed one-level hierarchy over strong flat alternatives at 4,096 slots.
- P8 (registered study INCOMPLETE, 55/60, decision `none`; ADR-0016 supplement separately labelled): every locality term reduced the slots in use by 46–92% against its own baseline; null misses were 0.00 for C08–C10 and below the floor in three of twelve co-access cells; no case was LOCALITY-POSITIVE. The step-wise coefficient peaked at 6.0·10⁵ (C05), 4.6·10⁵ (C10), 3.9·10⁵ (C04).
- **Not measured in P8:** movement of key rows that had no task gradient. Only total key movement was recorded. It is a hypothesis here, and §6.3 measures it.
- All earlier studies used one memory size and natural text on which the baselines used about 3% of 4,096 slots.

Scope: a 27,392-parameter frozen byte-level backbone, synthetic facts, RAM only, one data draw, two initialization seeds and one replicate parent. Nothing supports claims about large models, natural-language knowledge, composition, teacher absorption, physical I/O, throughput or production use.

## 2. Hypotheses

- **H17-CAP.** With facts in proportion to slots, the information retained about the answers grows nearly in proportion to memory size, exceeds a parameter-matched dense adapter, and disappears under memory ablations.
- **H17-UTIL.** A bounded usage term keeps or raises the number of useful slots without lowering retained information.
- **H17-LOC.** Given many useful slots, a co-access term lowers null-adjusted simulated page misses below those of the unregularized flat memory under its own optimized layout, with information and useful slots within the guards.
- **H17-INC.** A second disjoint fact set trained from a snapshot is acquired while the first is retained better than by a parameter-matched dense adapter.

## 3. Lanes and gates

| Lane | Families | Gate to interpretation |
|---|---|---|
| A — capacity | D01–D06 | task gates G1–G4 |
| B — optimization and collapse | D07 | G1–G4; controls are Lane A's 16K cells |
| C — locality | D08, D09 | synthetic part: none. Trained part: the 4K→16K step is supported for the architecture concerned (§8.2), and that architecture's B1 cell with α_u = 0.25, α_c = 0 is UTILIZATION_PRESERVED or UTILIZATION_IMPROVED against its dose-zero 16K cell |
| D — incremental | D10 | G1–G4 on sets A and B; phase-A accuracy ≥ 0.5 |

All lanes run in parallel after the common freeze, as the draft asks. If Lane C's gate fails its trained part is **H17-LOC NOT EVALUATED**, descriptive only. A passing subset is never promoted.

*Option for the human lead (auditor's suggestion, not the default):* run Lane A first and launch B–D only if the 4K→16K step is supported. It saves about 30 cheap cells if Lane A fails and costs the parallelism the draft asks for. The calibration of §12 already removes the main risk of an invalid task.

## 4. Task and data

Generated locally from frozen seeds. No corpus, download, teacher or third-party data.

### 4.1 Facts

- **Alphabet Σ:** 32 printable ASCII bytes, fixed in the config.
- **Identifier:** 5 symbols; the first four uniform, the fifth their sum modulo 32. Any two identifiers differ in at least two positions, at every size. This removes one-symbol neighbours (without it, 22% → 98% of facts would have one). It does not hold neighbour density constant: the share of facts with a two-symbol neighbour still rises from 49% to 91% to 100%, and 60% of those neighbours share the checksum symbol next to the answer site (auditor check R1). Accuracy is reported separately for facts with and without such a neighbour.
- **Answer:** 1 symbol, uniform and independent of everything else. Chance is 1/32; a fact carries 5 bits.
- **Counts:** proportional track 2,048 / 8,192 / 32,768 facts at 4,096 / 16,384 / 65,536 slots; fixed track (D04) 2,048 facts at every size.
- **Unseen-fact control:** 2,048 valid identifiers never trained, random answers.

### 4.2 Records, contexts, templates

- **Record:** 8 bytes — separator, 5 identifier bytes, binding byte, answer byte. The **answer site** is the binding byte's position; its target is the answer byte.
- **Context:** 64 bytes = 8 records; with next-byte targets this gives 63 targets, of which exactly 8 are answer sites.
- **Template:** a (separator, binding) byte pair. The pool is the 48 bytes most frequent in the backbone's training corpus that are not in Σ. It is split by seed into disjoint byte sets: 32 bytes for T (16 separators and 16 binding bytes, paired one to one), 8 for H1 and 8 for H2 (each 4 separators × 4 binding bytes, 8 of the 16 combinations by seed). No byte appears in more than one of T, H1, H2. One template per context.

### 4.3 Planted access structure

- Facts are assigned by seed to fixed **clusters of 16**. A context holds 8 distinct facts of one cluster, in seeded order. Clusters are visited in seeded epoch order; every fact has exactly equal frequency.
- A fact's own record never appears earlier in its context, so the frozen upper block cannot copy an answer in context.
- Answers are independent of identifiers, clusters and neighbours.
- All cells share this one data draw. Seeds replicate initialization only.

### 4.4 Streams and panels (generated and hashed before any training)

| Stream | Templates | Content | Use |
|---|---|---|---|
| Training | T | exposure rule of §5.5 | training |
| Calibration | T | every fact twice, contexts not in training | layouts, cache size, usage statistics only |
| **Panel A (primary)** | T | every fact once, in contexts never seen in training (new co-record sets, positions and order, verified by hash); unseen-control facts in separate contexts | all classes |
| **Panel B (primary, replication)** | T | as A, separate seed | all classes |
| H1, H2 | held-out | every fact once | secondary robustness; no class |
| Mixed-cluster | T | every fact once, 8 facts from 8 different clusters | secondary; dependence on cluster-mate context |

### 4.5 Family 2 — not run (see §0 item 1)

If restored by the human lead: link facts map an identifier to an identifier, chains are written out explicitly, half of the chains are held out, at 16,384 slots, for flat, learned tree and dense, with single-hop, teacher-forced and free-running scores. It would be reported as chained lookup, never as composition, and would enter no class.

### 4.6 Generator checks (gate G1)

1. Identifier uniqueness and checksum; exact coverage and equal frequency on every stream.
2. Independence of answers from each identifier position, template, cluster and record index, by seeded Monte Carlo permutation tests, none below 0.001 after Bonferroni correction within a stream. The number of tests k per stream is listed in the config; permutations ≥ 2,000·k. Chi-square is not used: its expected counts would be below 5.
3. No panel context appears in training; no fact's record precedes its own answer site in a context.
4. A dictionary lookup scores exactly 1.0 on trained facts and exactly the count of chance matches on unseen facts.
5. Rehearsal and calibration seeds are disjoint from registered seeds.

## 5. Models, controls and scaling

### 5.1 Common

- Frozen P4 backbones as in P5–P8, FP32, CPU only.
- Memory as P5: top-8, temperature 0.2, cosine keys, learned query projection, output projection and gate; AdamW, learning rate 0.003, no weight decay, clip 1.0. At 4,096 slots and key width 16 the new forward must reproduce the P5 `Memory` forward exactly.
- **Training loss is the cross-entropy at answer sites only**, for every arm (memory, dense, ladder). Other targets are masked. Otherwise the identifier bytes themselves would be memorized (about 4–5 bits per fact) and compete for slots. The all-position loss is reported descriptively.
- New modules only; P1–P8 code, records and ADRs are unchanged.

### 5.2 Size scaling

| Slots N | Flat: key products per query | Tree: branches × slots | Tree: router + candidate key products |
|---|---|---|---|
| 4,096 | 4,096 | 16 × 256 | 16 + 512 |
| 16,384 | 16,384 | 64 × 256 | 64 + 512 |
| 65,536 | 65,536 | 256 × 256 | 256 + 512 |

Two branches visited at every size. This is logical work, not measured efficiency.

### 5.3 The addressing ladder (D06)

| Rung | Query | Reads at | Selection | Trained | Read against |
|---|---|---|---|---|---|
| R0 natural (the system) | learned projection of the frozen hidden state | all positions | top-8 | all addition parameters | — |
| R0a | as R0 | answer sites only | top-8 | as R0 | R0a − R0: interference from reading everywhere |
| R1 oracle query | fixed random unit code per fact, seeded hash of the identifier | answer sites | top-8 | keys, values, output projection, gate, router | R1 − R0a: identity exposure by the frozen block plus the learned projection |
| R2 oracle address | none | answer sites | one dedicated slot per fact, weight 1 | values, output projection, gate | key learning (against R1); readout (against exact) |
| Tree oracle branch | as R0 | all positions | branch given by a seeded hash of the identifier; top-8 inside it | as R0 without router | router learning (against tree R0) |

Declared limits of the ladder: R1's random codes are better spread than anything the frozen block can produce; R2's rows receive about a quarter of the gradient events of a shared R0 slot, so **R2 is not an upper bound on R0 and R1 is not an upper bound on R0a**. Gaps are reported with their sign. Rungs other than R0 never enter a capacity class.

### 5.4 Key width

Width 16 is historical. Width 32 is registered for flat R0 and R1 at 16,384 and 65,536 slots. The auditor's calculation shows that random 16-dimensional keys do not by themselves limit accuracy at 32,768 facts (0.98 without value adaptation), so this arm is a check on attribution, used only by the rule in §8.2.

### 5.5 Exposure, snapshots, estimands

- A batch is 16 contexts = 128 answer-site exposures.
- **Matched exposure, E per fact** (E = 32 unless the calibration of §12 selects 64 or 128): updates U_N = F·E/128, i.e. 512 / 2,048 / 8,192 at E = 32.
- **Fixed compute:** U_16K updates at every size, read from snapshots.
- Constant learning rate, so a snapshot is a valid shorter run.
- Snapshots (with optimizer state): at ½U and U of each cell's own matched-exposure point, and at ½U_16K and U_16K. The 4,096-slot cells run to U_16K.
- **Known confound, stated not removed:** under AdamW a row that receives a gradient once in K updates moves about √K learning rates per exposure — 4.0, 7.9 and 15.1 at the three sizes — and about 90% of that happens on updates where the row has no gradient. Matched exposure is therefore not matched optimization, and the effect favours larger memories. Block A10 (§10) measures how much of any capacity result depends on it.

### 5.6 Controls

- **No-memory baseline** and **exact retrieval (D01)**.
- **Frozen-hidden probes:** nearest stored answer-site hidden state, and a 32-way linear probe per identifier position. No memory involved; they say how much of the identity the frozen block exposes.
- **Dense adapter**, hidden width set so its parameter count matches the key-16 memory within 0.1%, same loss, exposure and optimizer.
- **Row-lazy Adam arm (A10):** flat R0 at the three sizes with per-row moments, a row updated only when its gradient is non-zero, bias correction by the row's own update count. Row-lazy applies to the key and value tables only; projections, gate and router use AdamW. Its learning rate is 0.012 *(lead's choice)*, so that a row moves per exposure about what AdamW moves it at 4,096 slots, and the same at every size.
- **Value permutation and memory disabled** on every trained memory cell.

## 6. Measurements

### 6.1 Knowledge

With e = 1 − accuracy over F facts, accuracy counted on the most probable symbol within Σ, ties counted wrong:

- **Primary: I_acc = F · [5 − h₂(e) − e·log₂31] bits** (Fano bound; exactly 0 at chance, 1.52 bits per fact at accuracy 0.5). Every rule uses I_acc.
- I_acc is set to 0 for a cell whose accuracy is at or below the upper end of the G2 interval for its fact count. (The formula is positive below chance: 0.046 bits per fact at accuracy 0.)
- **Secondary:** the unfloored log-loss gain Σ_f (5 + log₂ p_f) with p_f renormalized over Σ; it can be negative.
- Descriptive only: a floored sum (it is positive for a model that knows nothing, so it enters no rule); probability mass outside Σ; accuracy by template panel.
- Ratios per slot, per stored parameter and per key product (logical).

### 6.2 Useful slots

- **Knock-out:** remove the chosen slots' values from the weighted sum at the fact's answer site **and at the record's six earlier positions** wherever those slots are selected; selections and weights stay as cached; other records are unchanged. (The memory reads at every position, and the position before the answer site already sees the whole identifier, so a fact can be stored one position early.)
- **Minimal support of a fact:** candidate slots are the union of slots selected at the record's seven input positions, ordered by summed weight; the minimal support is the shortest prefix whose knock-out makes the fact incorrect with p_f ≤ max(2/32, p_f^nomem + 0.02), p_f^nomem being the no-memory probability of the correct symbol. Facts answered incorrectly have none.
- **Useful slot:** a slot in at least one minimal support. **U\*** is their count.
- **Specificity (condition for interpreting U\*):** knocking out 8 slots drawn from other facts' minimal supports, excluding every slot selected in the fact's own record, changes p_f by less than 0.05 on at least 95% of facts; and zeroing the **values** of one of 64 contiguous slot groups at all positions, selections kept, leaves facts whose minimal support avoids the group within 0.02 accuracy. If either fails, U\* is marked NOT INTERPRETABLE for the cell and the classes that use it are INTERMEDIATE.
- Reported for every cell: the share of correct facts that stay correct when the whole answer-site read is removed, and the mean minimal-support length.
- Reported, never used alone: distinct selected slots, entropy-effective slots, hot-64 share, dead slots, weight entropy of each read, facts per slot, keys first entering any query's top 64 after update 0.

### 6.3 Optimization (every cell, no extra cells)

- Per update and parameter group (keys selected at an answer site, keys that are top-64 candidates but unselected, untouched keys, values, router, projections): gradient norm of the task loss and of each regularizer, and norm of the parameter change.
- **Per key row and value row: cumulative movement on updates where the row had a task gradient, and on updates where it had none.** This answers the P8 question directly.
- Per snapshot: 8th–9th score margin distribution, soft mass outside the top 8, whether each regularizer's hinge was active, dead-slot count.
- Trainable parameters, initialized slots and optimizer-state bytes per cell. Every cell reports examples, tokens, updates, unique facts, the exposure distribution and wall time.
- **REGULARIZER-DRIVEN MOVEMENT** is printed with a B1 or C1 class when, in both seeds, the cell's cumulative key movement on updates where the row had no task gradient is more than 1.5 times *(lead's choice)* that of its §8.3 reference cell of the same seed (the dose-zero 16K cell for B1; the B1 cell with α_u = 0.25, α_c = 0 for C1). The share of key movement on such updates is reported for every cell but is not compared with a fixed fraction: under AdamW it is about 0.9 with no regularizer at all (§5.5; auditor check c4: 0.876 / 0.899 / 0.900).
- Every quantity used by a class is reported with its median and full per-fact distribution. The B101 − B102 contrast is reported for A1 and A2 as descriptive; no other parent-level contrast exists with one replicate parent.

## 7. Objectives (D07, D08)

Soft inclusion as ADR-0015 revision 3: π_s = σ((score_s − τ)/0.25) on a query's top-64 candidates, τ the midpoint of the 8th and 9th scores, not detached.

**Global usage floor.** u_t = (1 − b)·u_{t−1} + b·ū_t with b = 128/F (one pass over the facts); u_{t−1} is detached; u₀ is the first batch's ū. ū_t is the batch-normalized π usage **at answer sites only**. The applied gradient is λ_u·(∂R_glob/∂u at u_t)·∂ū_t/∂θ, **without** the factor b *(lead's choice)*; with b the doses would shrink by 16, 64 and 256 at the three sizes. H uses 0 · ln 0 = 0. ∂R_glob/∂u is evaluated at u_t, which contains b·ū_t, so it is finite on every slot where ∂ū_t/∂θ ≠ 0; no ε is added. It is implemented as λ_u·⟨g_t, ū_t⟩ with g_t = ∂R_glob/∂u at the detached u_t. Known transient: with u₀ set to the first batch's usage the hinge stays on for roughly the first 27–57 of 2,048 updates even in a perfectly spread memory (auditor check S1). With M = min(N, 8F)/2:

R_glob = max(0, ln M − H(u)) / ln N.

It is zero while the memory spreads over at least half of the slots it could use. A batch-local floor is not used: a memory using a thousand slots would satisfy it at any size.

**Soft against hard usage.** Every B1 and C1 cell reports H(u) from π and from hard top-8 selections at answer sites, and the soft mass outside the top 8. A cell whose soft H(u) ≥ ln M while its hard entropy-effective-slot ratio to its §8.3 reference is below 1.05 is annotated **SOFT-USAGE ONLY**: the floor was met by probability mass outside the selected slots.

**Stated limit.** A key that is in no query's top 64 receives no gradient from any term and cannot be revived by gradient. The study measures how many keys enter a top 64 after update 0; it does not claim a cure for dead slots.

**Locality.** R_co of ADR-0015 (expected number of 8-slot identifier groups touched per selected slot), unchanged.

**Coefficients — absolute, no measurement, no cap, no adaptation:**

- λ_u = α_u · ln 32 / (ln M / ln N): a fully collapsed memory costs α_u times the chance-level answer loss.
- λ_c = α_c · ln 32 / (1 − 1/8), multiplying (R_co − 1/8): the best co-access value costs 0 and the worst α_c times the chance-level answer loss.
- Doses: α_u ∈ {0, 0.25, 1}; α_c ∈ {0, 0.05, 0.25} *(lead's choice; a dose of 1 would cost more than the chance-level answer loss at random selection)*, the non-zero α_c only together with α_u = 0.25. No other dose is run; none is selected afterwards.

Revision 1's rule (a coefficient from gradient norms at initialization, capped at 100) is withdrawn: in P8's own records the usage hinge would have been inactive at initialization in every flat cell, giving a zero gradient, and, by the auditor's argument (not computed from the records), both doses would probably have hit the cap in the tree cells.

## 8. Gates, thresholds, classes

After the calibration outputs are written, the only changes allowed before the freeze are E by the rule of §12, sizes marked TASK_CEILING_FAIL, and the registered reductions of `RESOURCE_BUDGET.md` with their rule amendments. Any other change to a threshold, rule, dose or the matrix is a new design revision; the auditor re-checks it and it is presented at decision 2 as made after calibration.

### 8.1 Task gates

- **G1** generator checks (§4.6).
- **G2** chance, per primary panel: the no-memory baseline on the 2,048-, 8,192- and 32,768-fact sets (the fixed track uses the 2,048-fact proportional set), and the unseen-fact set: 8 tests, each inside the exact binomial central interval of level 1 − 0.001/8 around 1/32. The same interval is "chance" wherever a rule says so. The unseen-fact accuracy of every trained cell is reported against it; a cell outside it is flagged **LEAKAGE** and its lane is not interpreted until the auditor explains it. Lane D adds, per primary panel, the no-memory baseline on sets A and B (4,096 facts each): a separate family of 4 tests at level 1 − 0.001/4, whose interval is "chance" in Lane D.
- **G3** readout ceiling, **decided in the calibration** (§12 step 4): R2 accuracy ≥ 0.95 on rehearsal panels at every size at the selected exposure. If it is not reached at E = 128 at some size, that size is `TASK_CEILING_FAIL` and is not run. In the registered run R2 is a diagnostic. If a size is TASK_CEILING_FAIL, every step involving it is NOT_EVALUATED; CAPACITY_POSITIVE cannot be assigned if 65,536 fails; if 16,384 fails, Lanes B, C (trained part) and D are NOT_EVALUATED.
- **G4** determinism and identity: checkpoint restoration, stream hashes, P5 forward invariance.

### 8.2 Capacity (flat and learned tree separately; R0; matched exposure; Panels A and B separately)

Let I_N be I_acc at size N.

- **Step supported** (N → 4N): accuracy ≥ 0.25 at both N and 4N in every cell of the step (0.25 is about 0.47 Fano bits per fact) *(lead's choice)*; I_{4N}/I_N ≥ 3.0 in both B101 seeds; and ≥ 2.5 in the B102 replicate where one exists (A7 and A10 have none and use the two B101 seeds only). A ratio with I_N = 0 is +∞.
- **Beats dense:** I ≥ 1.10 × the matched dense adapter's, both seeds, at the larger size.
- **Dependence:** value permutation and disabling give chance accuracy; at least 90% of correctly answered facts have a minimal support.
- **Plateau:** I(U) − I(U/2) ≤ 0.05·I(U) in both seeds, with I set to 0 by §6.1 (a cell at chance at both snapshots has plateaued).

Classes, **first matching rule wins**:

| Order | Class | Rule |
|---|---|---|
| 1 | NOT REPLICATED | Panels A and B would give different classes |
| 2 | CAPACITY_NOT_SUPPORTED | some step has, in both seeds, ratio < 2.0 or accuracy below 0.25 at its larger size, and its larger cell has plateaued; the failing step is printed with the class |
| 3 | CAPACITY_POSITIVE | both steps supported; beats dense at 16K and 64K; dependence holds; accuracy at 64K ≥ 0.50 |
| 4 | CAPACITY_PARTIAL | the 4K→16K step is supported, with beats-dense and dependence at 16K |
| 5 | UNDERTRAINED | some step is not supported and its larger cell has not plateaued |
| 6 | INTERMEDIATE | otherwise |

Annotations (they do not change the class, and are always printed with it):

- **EMPTY-SLOT-EFFECT** if, at 2,048 fixed facts (D04), I_acc per fact rises by more than 25% from 4K to 64K.
- **OPTIMIZER-DEPENDENT** if a step supported under AdamW is not supported in the row-lazy arm (A10), and the row-lazy arm's accuracy at the smaller size of that step is ≥ 0.25 in both seeds; otherwise the annotation reads **OPTIMIZER-ARM UNINFORMATIVE**.
- **KEY-WIDTH-LIMITED** if key-32 R0 supports the 16K→64K step and key-16 R0 does not. "Supported" for key-32 uses the two B101 seeds. If A7 at 65,536 is dropped, it is not assessed.
- **TREE_AHEAD** (D03) if tree I_acc ≥ 1.03 × flat I_acc at 16K in both seeds and both panels; **TREE_COMPETITIVE** if ≥ 0.97; otherwise TREE_BEHIND. Logical key products (§5.2) are printed beside it, and the fixed tree is reported beside it. The draft's "tree must beat strong flat" is relaxed in this way (§0 item 7).

**Ladder report**, per size, in Fano bits per fact with sign: exact − R2, R2 − R1, R1 − R0a, R0a − R0, and tree oracle-branch − tree R0; with the frozen-hidden probes beside R0. A gap is called material at ≥ 0.5 bits per fact. At 4,096 slots only exact − R2 and R2 − R1 are reported (R0a is not run there).

### 8.3 Utilization (per architecture and seed, against its reference: the dose-zero 16K cell for B1, the B1 cell with α_u = 0.25, α_c = 0 for C1; both seeds; both panels; first match wins)

Every rule is evaluated per seed against the dose-zero cell of the same seed, and must hold in both seeds and both panels; seeds that disagree give INTERMEDIATE. Lane B classes need dose-zero 16K accuracy ≥ 0.25 in both seeds, else NOT_EVALUATED. C1 cells are classed against the B1 cell with α_u = 0.25, α_c = 0 of the same architecture and seed. If U\* is NOT INTERPRETABLE for the case or its reference, COLLAPSED is decided by the I ratio alone, and ENTROPY_INFLATION, IMPROVED and PRESERVED become INTERMEDIATE. Entropy-effective slots here are computed from hard top-8 selections at answer sites.

| Order | Class | Rule |
|---|---|---|
| 1 | NOT REPLICATED | panels disagree |
| 2 | COLLAPSED | U\* ratio < 0.80 or I ratio < 0.90 |
| 3 | ENTROPY_INFLATION | entropy-effective slots ratio ≥ 1.25, I ratio < 1.03 and U\* ratio < 1.03 |
| 4 | UTILIZATION_IMPROVED | I ratio ≥ 1.05, U\* ratio ≥ 1.05, and mean minimal-support-length ratio ≤ 1.10 *(lead's choice)* |
| 5 | UTILIZATION_PRESERVED | I ratio ≥ 0.97, accuracy drop ≤ 0.02, U\* ratio ≥ 0.97 |
| 6 | NO DIFFERENCE / INTERMEDIATE | otherwise |

### 8.4 Locality (trained part, gated by §3)

- **Simulator:** re-implemented for general N (the P7-B code fixes 4,096 slots, a dense co-access matrix that would need 16 GiB at 65,536, and 16-bit layout files). Required before use: exact equivalence with P7-B on P7-B's recorded traces at 4,096, and a sparse co-access count. ADR-0016's identity null for single-set streams only.
- **Traces:** answer-site reads (primary); all-position reads (secondary).
- **Cache rule, fixed before evaluation:** W = distinct slots selected at answer sites on the calibration stream; R slots per page; cache pages C = max(1, round(ρ·W/R)); primary settings ρ ∈ {1/16, 1/4} × R ∈ {8, 32}. W is computed separately for each trace type. The ratio of cache to U\* is reported for every cell.
- **E** = actual misses / mean of three count-preserving nulls. Null miss rate below 0.05, or a single-set stream, makes the setting DEGENERATE.
- **Comparison:** E of the case and E of the reference, **each under its own optimized co-access layout fitted on its calibration stream**, unconstrained for flat and tree alike. Reported beside it as controls, entering no class: identity layout, frequency packing, a random-partition layout, and for the tree a branch-constrained co-access layout (each branch's slots contiguous).
- **References:** locality reference = the dose-zero flat 16K cell; utilization reference for a locality cell = the cell with α_u = 0.25, α_c = 0 of the same architecture.
- **Oracle layout (bound):** each slot goes to the cluster with most of its calibration accesses, ties to the lowest cluster number; clusters contiguous.
- **Expectation stated in advance:** on this stream the reference's own optimized layout is expected to reach E near 0.77 when slots are shared at random across clusters, and far lower when sharing follows clusters (auditor's calculation). The test is therefore whether training changes how slots are shared, beyond what a layout fitted afterwards achieves. A memory that packs each query's eight slots into one page reaches an E ratio of about 0.15 with no cluster structure (auditor toy R4); cluster-coherent sharing must cover about 35–50% of facts to pass 0.80. **Pages per query (within-query co-selection) and cross-query reuse are reported separately for every locality cell.**

Classes, all four settings, both tie rules, both seeds, both panels, first match wins:

| Order | Class | Rule |
|---|---|---|
| 1 | NOT REPLICATED | panels disagree |
| 2 | COLLAPSED / QUALITY_FAILED | §8.3 COLLAPSED, or I ratio to the locality reference < 0.97 |
| 3 | DEGENERATE | any primary setting is degenerate for the case or its reference |
| 4 | LOCALITY_POSITIVE | E ratio ≤ 0.80; cell UTILIZATION_PRESERVED or IMPROVED |
| 5 | CONCENTRATION_ONLY | raw miss ratio ≤ 0.80 and E ratio > 0.90 |
| 6 | WORSE / NO DIFFERENCE / INTERMEDIATE | E ratio ≥ 1.10 / in (0.90, 1.10) / otherwise |

A hierarchy advantage needs the tree case to be LOCALITY_POSITIVE against the **flat case with the same doses**.

### 8.5 Incremental (Lane D; 16,384 slots; A and B are 4,096 disjoint facts each)

- Phase A: E exposures of A. Phase B from snapshot V1: E exposures of B.
- Arms in phase B: flat sequential (all addition parameters train); flat memory-only (keys and values train; projections and gate frozen); learned tree sequential; flat with replay; dense sequential; dense with replay; flat joint on A∪B from initialization (bound); exact retrieval (append).
- **Replay** keeps B's E exposures and adds one replayed A record per B record as extra rows; updates and examples are reported, and replay arms are compared only with each other and the bound.
- Sets A and B have their own clusters of 16; phase-B contexts contain B facts only; replay contexts contain A facts only.
- Every phase-B arm starts from V1's parameters with a **fresh optimizer state** *(lead's choice; no optimizer history carries between phases)*. V1 also stores the optimizer state, for the restoration test only.
- For the tree, memory-only is not run; tree sequential trains all addition parameters including the router.
- Classes are assigned to flat sequential, flat memory-only and tree sequential, each against dense sequential.

With a_A, a_B accuracy after phase B and a_A⁰ accuracy on A after phase A; classes need a_A⁰ ≥ 0.5, else NOT_EVALUATED. First match wins:

| Order | Class | Rule (both seeds, both panels) |
|---|---|---|
| 1 | NOT REPLICATED | panels disagree |
| 2 | NO_NEW_CAPABILITY | a_B < 0.5 × the joint bound's accuracy on B |
| 3 | FORGETTING | a_A < 0.70 × a_A⁰ |
| 4 | INCREMENTAL_POSITIVE | a_B ≥ 0.9 × the joint bound on B; a_A ≥ 0.90 × a_A⁰; and the arm's forgetting a_A⁰ − a_A is at least 0.10 smaller than the dense sequential arm's, whose own a_A⁰ must be ≥ 0.5 (else NOT_EVALUATED) |
| 5 | INTERMEDIATE | otherwise |

**NO ADVANTAGE OVER DENSE** is an annotation printed with the class when the dense sequential arm's forgetting is ≤ 0.10.

Reported: slots and bytes changed between V1 and V2, overlap of A and B minimal supports, updates, examples, logical lookup work.

**Version store (engineering test only):** copy-on-write snapshots and atomic manifest publication in a local directory; a reader pinned to V1 while V2 is prepared; no mixed versions, replay equivalence, rollback.

### 8.6 Study status

- `ENGINEERING_FAIL`: identity, determinism, checkpoint or gradient-reach defects only. A regularizer being inactive is a recorded scientific property, not a failure.
- `INCOMPLETE`: any registered cell lacks a record; no class is derived for a lane with a missing mandatory cell; the denominator is never reduced.
- A failed cell stops the launch of cells that depend on it — **in every stage, enforced by the job manager and tested** (the P8 deviation). Other lanes continue. Nothing is re-run with changed settings.

### 8.7 Decision map

1. Flat or tree CAPACITY_POSITIVE without OPTIMIZER-DEPENDENT → a separately approved capacity-scaling protocol may be proposed. If the annotation reads OPTIMIZER-ARM UNINFORMATIVE or "OPTIMIZER-DEPENDENT: not assessed", this item needs the human lead's explicit acceptance of that.
2. Capacity positive or partial, locality not positive → redesign placement or routing.
3. Capacity not supported with a material ladder gap → investigate the indicated component (representation at R1 − R0a, interference at R0a − R0, keys at R2 − R1, width if KEY-WIDTH-LIMITED, optimizer if OPTIMIZER-DEPENDENT).
4. `TASK_CEILING_FAIL`, or capacity not supported with no material gap → pause the line or redesign the testbed.
5. UNDERTRAINED, INTERMEDIATE, NOT REPLICATED or NOT_EVALUATED in Lane A → no capacity decision; item 4 applies unless the human lead decides otherwise.

No outcome authorizes further training, storage experiments or scaling.

## 9. Lane C synthetic part

On generated traces only:

- **Planted-structure traces** with known answers, exercising every class: popularity only (E ≈ 1); planted clusters with random and with cluster-aligned slot sharing; fully collapsed single set (identity null, DEGENERATE); working set below the cache (DEGENERATE); incomplete input (INCOMPLETE).
- **D09 sweep on trained traces:** ρ ∈ {1/16, 1/4, 1} × R ∈ {2, 8, 32}. Settings outside the primary four, and all of ρ = 1, are descriptive.
- **Key traffic:** keys in RAM (no key traffic) against keys on storage (flat reads every key page; the tree reads the router and two branches). This is an arithmetic identity from §5.2, labelled as such; it is not a simulation result. The invalid P7-A key table is not used.

## 10. Matrix and seeds

Initialization seeds 1701 and 1702 on parent B101/O301; one replicate (seed 1701, parent B102/O302) for the primary capacity cells.

| Block | Configurations | Cells |
|---|---|---|
| A1 flat R0, proportional, 3 sizes | 3 | 6 + 3 |
| A2 learned tree R0, proportional, 3 sizes | 3 | 6 + 3 |
| A3 fixed tree R0, 16K | 1 | 2 |
| A4 flat R0, fixed facts, 16K and 64K | 2 | 4 |
| A5 flat R1 and R2, 3 sizes | 6 | 12 |
| A5b flat R0a, 16K and 64K | 2 | 4 |
| A6 learned tree R1, and tree oracle branch, 16K | 2 | 4 |
| A7 key width 32: flat R0 and R1, 16K and 64K | 4 | 8 |
| A8 dense adapter, 3 sizes | 3 | 6 |
| A10 flat R0 with row-lazy Adam, 3 sizes | 3 | 6 |
| B1 usage dose 0.25 and 1 × flat, learned tree (16K) | 4 | 8 |
| C1 locality dose 0.05 and 0.25 × flat, learned tree (usage 0.25, 16K) | 4 | 8 |
| D1 phase A: flat, learned tree, dense | 3 | 6 |
| D2 phase B: six trained arms; joint bound | 7 | 14 |
| **Total trained cells** | | **100** |

No training: exact retrieval, no-memory baseline, frozen-hidden probes, at every size and track.

**Dependencies.** Training: each D2 sequential, memory-only or replay arm depends on the D1 cell of the same architecture and seed; every other cell is independent. Analysis: capacity classes depend on A1/A2 at all sizes (including B102) and on A8; annotations depend on A4 with A1 at 4K, and on A10, A7 and A3; B1 depends on A1/A2 at 16K; C1 depends on A1 16K flat and on the B1 α_u = 0.25 cells; the Lane C gate depends on A1/A2 at 4K and 16K and on the B1 α_u = 0.25 cells.

**The ten diagnostic families** (auditor's mapping; none names a task family, so not running Family 2 leaves all ten):

| ID | Registered blocks | Rule |
|---|---|---|
| D01 | A5 R2 + calibration; exact, no-memory, probes | G1, G2, G3 / TASK_CEILING_FAIL; exact − R2 |
| D02 | A1, A8 | §8.2 flat class |
| D03 | A1 16K, A2 16K, A3 | TREE_AHEAD / COMPETITIVE / BEHIND; fixed tree descriptive |
| D04 | A4 + A1 4K | EMPTY-SLOT-EFFECT |
| D05 | A1, A2, A8, A10 | §8.2 classes, both estimands; OPTIMIZER-DEPENDENT |
| D06 | A5 R1, A5b, A6, A7 | ladder report; KEY-WIDTH-LIMITED; decision item 3 |
| D07 | B1; controls A1/A2 16K | §8.3 |
| D08 | C1; references A1 16K flat, B1 α_u = 0.25 | Lane C gate, §8.4, hierarchy rule |
| D09 | traces of A/B/C cells; planted synthetic traces | §9 synthetic classes; ρ × R sweep; key-traffic identity |
| D10 | D1, D2; exact append; version store | §8.5 |

Data seeds: facts 170001, templates 170011, clusters 170031, training order 170041, calibration stream 170051, Panel A 170061, Panel B 170071, H1/H2 170081, mixed-cluster 170082, Lane D sets 170091 and 170092, R1 codes 170101, branch hash 170102, permutation tests 170111. Null seeds 171331–171333 (A) and 171341–171343 (B). Rehearsal and calibration seeds are 179001 upward and appear in no registered cell.

## 11. Resources

- Apple M5 Max, 18 cores, 48 GB; CPU only.
- **Projection (`RESOURCE_BUDGET.md`), not a measurement:** about 5 to 6 hours of charged execution at E = 32 with two training workers, and roughly twice that at E = 64.
- **Calibration and rehearsal together:** at most 4 hours and 3 GiB per worker (decision 1 raised the hour budget without a figure; 4 hours is the lead's application of it).
- **Fixed at the second decision, on rehearsal evidence:** per-worker and aggregate RSS caps, stage caps at twice the measured stage time, and the total. The draft's 8 hours and 2 GiB are not expected to hold twofold headroom; the registered reductions are listed in the budget.
- Aggregate RSS cap 24 GiB (decision 1). Per-worker cap 3 GiB. The number of training workers (two to four) is chosen from the rehearsal's contention measurement and recorded in the freeze; four simulation workers. Timing runs alone, with load recorded. No cloud, paid service, download or storage experiment.

## 12. Order of work

1. Auditor re-check of this revision (done: `RECHECK.md`, `CONFIRM.md`).
2. **Human decision 1:** approve this specification for implementation, calibration and rehearsal; accept or change the departures of §0; approve the delegation.
3. Implementation with tests, including synthetic inputs that trigger every class and the dependent-cell stop rule.
4. **Testbed calibration, rehearsal seeds only, written and audited.** Allowed: the frozen-hidden probes at 2,048 / 8,192 / 32,768 rehearsal facts; the R2 learning curve at each size up to E = 128; no-memory and exact controls; the largest answer probability attainable through the frozen final layers (linear algebra on frozen weights). **Not allowed:** any R0, R0a, R1, tree, dense or regularized arm. **It may change one thing, by this rule:** E is the smallest of {32, 64, 128} at which R2 reaches 0.95 at every size. A size that fails at 128 is `TASK_CEILING_FAIL`. The probes are reported and change nothing. No threshold, rule, dose or matrix entry changes on calibration evidence (§8 opening).
5. Full-size rehearsal on rehearsal seeds for time and memory. The rehearsal entry point writes records only through a validator whose allowed keys are the whitelist (time, RSS, finiteness, shapes); stdout and stderr go to a file the auditor checks for loss or accuracy values; no progress display shows loss.
6. Auditor implementation audit: READY TO FREEZE.
7. Registered data and panels generated and hashed; freeze of specification, code, configs, data and panel identities.
8. **Human decision 2:** approve the frozen final revision, the selected E, the caps and the run.
9. The registered run, once.

## 13. What must not be claimed

- That slot entropy, distinct slots or the floored information sum show capacity.
- That R0a, R1, R2 or oracle-branch results are system results, or that the ladder gives upper bounds.
- That logical work is measured efficiency, or that simulation or the key-traffic identity is storage I/O.
- That cross-query locality found here would arise without planted structure; equal-frequency planted clusters are a best case, and within-query packing is not evidence about clusters.
- That the usage term revives dead slots, unless §6.2's revival count shows it.
- That Lane D shows continual learning in general, or teacher absorption.
- Anything about composition or reasoning.
- Any generalization across data draws, beyond 65,536 slots, or to a trainable backbone.

## 14. Decisions reserved for the human lead

1. Decision 1 (§12 step 2), including each item of §0 and the Lane-A-first option of §3.
2. Decision 2 (§12 step 8).
3. ADR-0012; merge; publication; any next phase.

## 15. Approval record

### Decision 1 — 2026-11-14

The lead's question, as put: "Do you approve revision 3 for implementation, calibration and rehearsal only? The registered run would need a second approval after the freeze. Approving means accepting the twelve departures from your draft listed in §0, or telling me which to change." The message listed the Family 2 omission, the two-approval order with calibration, the relaxed tree rule, the 3-hour and 3-GiB calibration and rehearsal cap, and the Lane-A-first option that the lead had not adopted.

**Human lead, in chat (verbatim):**

> im ok with your assessment, increase the hour budget and you can use up to 24gb of total ram

**Reading by the Claude lead:**

- Revision 3 is approved for implementation, calibration and rehearsal. The registered run is not approved.
- The departures of §0 are accepted as written; the parallel default of §3 stands.
- The study-specific Claude delegation is accepted for this phase. ADR-0012 remains not approved.
- **Aggregate RSS cap: 24 GiB** (replaces 8 GiB), for calibration, rehearsal and, subject to decision 2, the run.
- **The hour budget is raised, but no figure was given.** The lead applies: calibration and rehearsal together at most 4 hours; the run's cap is proposed at decision 2 as twice the rehearsal-based projection, and the human lead fixes the figure then.
- Not stated by the human lead and therefore unchanged: the per-worker RSS cap (3 GiB as proposed in §11) and every threshold, dose and matrix entry.

The approval was one sentence. If any reading above is wrong, the correction is recorded here as a dated entry.

### 15.1 Clarifications by the lead after decision 1 (implementation details the text left open)

Recorded 2026-11-14 while the first implementation package was written. None changes a hypothesis, threshold, dose or the matrix. They are part of what is presented at decision 2. The full list with the config keys is `core.OPEN_CHOICES` / `[choices]` in `configs/p9_diagnostics.toml`.

1. **Alphabet Σ:** bytes 0x40–0x5F. **Template pool:** the 48 most frequent bytes, outside Σ, in the 2,048 corpus rows the backbones were trained on (ties by byte value); it includes three non-ASCII bytes.
2. **Fact tables are nested:** the proportional facts at a smaller size are the first facts of the larger, so the fixed track and the 4,096-slot cells share the same 2,048 facts. Lane D uses a second table whose identifiers avoid the first.
3. **R_co is evaluated at answer sites**, like the usage term (§7 did not say).
4. **Replay** adds 16 replayed A contexts to the 16 B contexts of each update; the update count is unchanged (§8.5 said "extra rows").
5. **Snapshots at ½U_16K and U_16K** apply to fixed-track cells and not to Lane D cells, which have ½U and U.
6. **EMPTY-SLOT-EFFECT (D04)** is read at the matched-exposure snapshot of the 2,048-fact set at every size.
7. **Dense adapter matching:** matched exactly to the flat key-16 memory. Against the learned tree it differs by 0.13% (the router), above the 0.1% of §5.6. The tolerance for the tree comparison is therefore 0.2%. *This is a numerical relaxation of §5.6 and is flagged for decision 2.*
8. **G1 tests per stream:** k = 8 (five identifier positions, template, cluster, record index), 16,000 permutations.
9. **G2:** four tests per primary panel (three no-memory sets and the unseen set); Lane D uses one 4,096-fact interval for both sets.
10. **Exact retrieval answers an unseen identifier with the first symbol of Σ**, so its unseen-fact score is the count of chance matches.
11. **Code location:** `studies/p9/`, not `src/arborlm/` (see `INTERFACE_CONTRACT.md`).

### 15.2 Human direction after the calibration — 2026-11-14

Shown the calibration numbers (`results/p9-calibration-2026-11-14/README.md`: frozen-hidden probes near chance; the readout rung limited by update count; the registered rule giving E = 128 and TASK_CEILING_FAIL at 4,096), the human lead wrote in chat (verbatim):

> We've been investigating whether memory can organize itself efficiently. But we may first need to solve a more fundamental problem:
> How does the language model reliably communicate what information it needs to its memory?
> If that interface fails, SSD capacity, better trees and locality objectives won't fix the issue.
> That doesn't invalidate the original ArborLM concept. It identifies a prerequisite that our tiny experimental backbone may not satisfy.
> let Opus finish the audit, correct the scientific design if the findings hold, and only then authorize a new execution.
> For now, I would classify ADR-0017 as calibration blocked, not scientifically failed. We haven't tested the main hypothesis under valid conditions yet.

Consequences recorded by the lead:

- ADR-0017 revision 3 is **CALIBRATION BLOCKED**. It is not a negative result on H17-CAP, H17-UTIL, H17-LOC or H17-INC; none was tested.
- The rehearsal and the registered run do not proceed under revision 3.
- The auditor finishes the calibration audit. If its findings hold, the lead corrects the design in a new revision that addresses the query interface between the backbone and the memory first. That revision is audited and returns to the human lead; no execution before that approval.
- What the calibration itself shows is a measurement about this testbed (a 27,392-parameter frozen backbone and synthetic identifiers), not about the ArborLM concept.

### 15.3 Human decision on the query-interface prerequisite (Part I, §18) — 2026-11-14

The lead put four questions (drafted as ADR-0018 revision 3 §14): 1, whether to include arm BB, which trains 4,224 parameters of the backbone's block-0 attention; 2, a separate study or a fold into a revision of ADR-0017; 3, a time cap of "4 hours for calibration, rehearsal and the run together, or 6 hours with BB, keeping the 24 GiB memory limit"; 4, approval for implementation, calibration and rehearsal only, with a second approval for the registered run after the freeze. The human lead answered in chat (verbatim):

> 1 yes, 2 fold into adr 17, 3  4hours sound solid for calibration, 4 approved and you can approved it after the freeze if you se fit

Recorded by the lead:

- **Arm BB is included.** Training the block-0 attention (4,224 parameters) is approved for block BB of Part I only. No other backbone parameter is trained anywhere.
- **Folded.** The prerequisite is Part I (§18) of this ADR, revision 4. `ADR-0018` is withdrawn as a separate ADR and its file points here.
- **Cap.** The answer names 4 hours and "calibration". The lead applies the stricter reading: 4 hours of charged execution for calibration, rehearsal and the run together, with BB included, 24 GiB aggregate. If that cannot hold, the work stops and the question returns to the human lead; the cap is not raised by the lead.
- **Decision 1 of Part I: approved** — implementation, calibration on rehearsal draw 1, rehearsal.
- **Decision 2 of Part I is delegated to the lead** ("you can approved it after the freeze if you se fit"). The lead limits its own use of the delegation, and records the approval here before the run. The lead approves only if all of these hold; otherwise decision 2 returns to the human lead:
  1. calibration selected a U with no size failed (a failed size is INCONCLUSIVE by §I.8.3 step 0 and is the human lead's call);
  2. the calibration audit and the implementation audit by Opus 5.5 end with no open blocker or major;
  3. nothing changed after calibration except U;
  4. the rehearsal shows the run fits the remaining part of the cap and the memory limits;
  5. no registered seed has been observed.
- The delegation covers the single registered run of Part I. It does not cover Lanes A–D, any re-run, a merge, a push of weights, publication, ADR-0012, or any other study.
- Astra review: NOT_PERFORMED.

### 15.4 Clarifications by the lead after the Part I decision (implementation details)

1. **Optimizer (a correction).** As approved, §I.3.2 said the key and value tables "keep row-lazy Adam at 0.012". That clause came from the auditor's confirmation edit R3(d) and is wrong: §5.1 specifies one AdamW (lr 0.003) for the memory, the row-lazy optimizer exists only in arm A10 of Lanes A–D, and the calibration this part rests on used AdamW. §I.3 says "the flat memory of §5". The lead resolves the contradiction in favour of §5.1: every Part I cell uses one AdamW over all its trainable parameters. The lead's own implementation contract repeated the error and was corrected before any calibration; the implementation audit checks it.
2. A size at which R1 and R2 each reach their threshold at some U but never at the same U is a failed size, labelled `NOT_JOINT`.
3. W7 and E7 query projections, and the A4/A4E q, k, v matrices, are initialized N(0, 0.02) from seeds derived from the cell's initialization seed.
4. "Nearest other query closer than 0.9" (§I.5) means the largest cosine to another fact's query exceeds 0.9.
5. The B102 replicate is classified by rows 2–4 of §I.8.1 step 1 against R1 of the same parent.
6. A BB class of MODEL_STORES_FACTS has dense comparison NOT COMPARED.
7. BB's next-byte loss is measured with nothing added, on the 2,048 corpus rows the backbone was trained on, before and after.
8. Rehearsal uses draw 2 by default; draw 1 is refused outside calibration.

### Decision 2 (Lanes A–D)

None. Not reachable (calibration blocked).

## 16. How revision 2 answers the review

Revision-2 entries. Where §17 differs (for example, G2 now has 8 tests), §17 governs.

| Finding | Change |
|---|---|
| B1 floored metric not a bound | Fano bound primary; floored sum descriptive (§6.1); accuracy condition in every step (§8.2) |
| B2 coefficient fails at initialization | absolute coefficients, no cap, no ENGINEERING_FAIL for an inactive term (§7, §8.6) |
| B3 task validity unmeasured | calibration step with a one-parameter menu (§12 step 4); G3 decided there |
| M1 loss positions | answer sites only (§5.1) |
| M2 held-out templates primary | primary panels use training templates in unseen contexts; H1/H2 secondary; byte pool specified (§4.2, §4.4) |
| M3 identifier density | 5-symbol identifiers with checksum (§4.1) |
| M4 R2 not a bound, G3 | declared (§5.3); G3 from calibration; attainable probability recorded (§12) |
| M5 optimizer confound | stated (§5.5); per-row movement recorded (§6.3); lazy arms moved to a size-crossed control A10 with a rule (§8.2) |
| M6 U\* inflated | minimal support, relative threshold, cached knock-outs (§6.2) |
| M7 batch-local floor | global moving-average floor; revival limit stated and measured (§7) |
| M8 class gaps | precedence orders, D04 metric, gap threshold, key-width and D03 rules, plateau at ½U (§8.2) |
| M9 ladder confounds | R0a added; limits declared (§5.3) |
| M10 simulator not reusable | general-N re-implementation with equivalence test; traces, layouts, oracle layout and references specified (§8.4) |
| M11 Lane D confounds | replay defined; a_A⁰ floor; absolute difference; memory-only arm; NO ADVANTAGE OVER DENSE (§8.5) |
| M12 Family 2 | not run; needs human acceptance (§0, §4.5) |
| M13 G2 false failures | 16 tests with corrected interval (§8.1) |
| M14 budget | cached evaluation; dense cost; caps at decision 2 (§11, budget) |
| m1–m18 | permutation tests; ties wrong; Σ-mass reported; 63 targets; panels and mixed-cluster panel; ½U snapshots; no batch halving; ρ = 1 descriptive; cache against U\* reported; NOT REPLICATED in every lane; precedence in §8.3; group ablation as an interpretability condition; tree oracle branch; one data draw stated; key traffic an identity; ENGINEERING_FAIL scope; per-lane analysis modules (plan); no gradient matching remains |

## 17. How revision 3 answers the re-check

| Re-check item | Change |
|---|---|
| RB1 near-chance memory could pass a step; Fano positive below chance; zero denominators; chance never plateaus | W1–W3: I set to 0 at chance, accuracy ≥ 0.25 at both sizes, ratio conventions, plateau at chance (§6.1, §8.2) |
| RB2 moving-average gradient undefined | W7: estimator and gradient written out, without the factor b (§7) |
| RB3 Lane C gate hid collapse; DEGENERATE before COLLAPSED | W12, W13: gate uses the usage-only cell; COLLAPSED first (§3, §8.4) |
| Answers stored one position early | W10: knock-out over the record's seven positions (§6.2) |
| Floor met by mass outside the top 8 | W8: hard-selection entropy in the rules; SOFT-USAGE ONLY (§7, §8.3) |
| Adam amplifies tiny gradients | W22: REGULARIZER-DRIVEN MOVEMENT (§6.3) |
| OPTIMIZER-DEPENDENT for the wrong reason | W5: accuracy condition, OPTIMIZER-ARM UNINFORMATIVE, learning rate 0.012 (§5.6, §8.2) |
| Lane D dense floor, annotation, arms, optimizer state | W15 (§8.5) |
| Calibration loophole | W23 (§8 opening, §12) |
| Template pool, neighbour density, G2 count, permutations | W17–W20 (§4, §8.1) |
| Locality by within-query packing | W14: reported separately; §13 reworded |
| Departures missing from §0 | items 7–12 added; the worker count and aggregate memory return to the draft's values (§11); layout controls restored (§8.4) |
| Budget | W28 in `RESOURCE_BUDGET.md` |
| Remaining W items | W4, W6, W11, W16, W21, W24–W26, W29, W31 applied as written; W9 applied with α_c = 1 replaced by 0.05 (no new cells); W30 applied with TREE_AHEAD added; W28 applied except that key-32 cells are not yet costed at twice key-16 (disclosed in the budget); confirmation fixes F1–F15 (`CONFIRM.md`) |

## 18. Part I — the query interface: can the model tell its memory what it needs? (P9-I)

Part I is the prerequisite of Lanes A–D. It tests none of H17-CAP, H17-UTIL, H17-LOC, H17-INC. Its outcome selects, by the rule of §I.8.3, the interface with which Lanes A–D would be revised, or records that none was selected. Lanes A–D then still need their own revision, audit, calibration and approvals. Sections are numbered I.n; "§I.n" refers to this part and a plain "§n" to the rest of this ADR.

### I.1 What is known

On the frozen 27,392-parameter backbones, with five-symbol checksum identifiers (20 bits), rehearsal seeds:

- The hidden state at the answer site carries 0.4 bits of the identifier by a linear probe and 1.0–1.4 by a small non-linear probe. Each identifier position carries its own symbol and almost nothing else. The record's seven input positions together carry 19.8–20.0 bits.
- Attention from the answer site is near-uniform; no head gathers the identifier.
- Content written by a memory at earlier positions does not reach the answer site through the frozen upper block: a perfect per-fact vector at the six earlier positions gives 2.8–4.7% (chance 3.1%), the same vector at the answer site 96.9%.
- Given the right slot, the readout works (97–100%). It learns by number of optimizer updates of the shared output projection and gate, not by exposures per fact.
- Training on all 256 output bytes while scoring within the 32-symbol alphabet costs one symbol on one backbone and slows learning severalfold (16,384 slots at 2,048 updates: 0.68 against 0.993 with the alphabet loss).

So the memory can store and return an answer, and the backbone cannot say which answer it wants. That is a property of this testbed. It is not evidence about the ArborLM concept.

### I.2 Scope, question and hypotheses

**Scope.** W7, E7, A4 and A4E are query encoders that belong to the memory; they read the frozen states (or the embeddings) of the input. A WORKS class for one of them shows that a memory-side encoder can address facts on this task. It does not show that the language model communicates what it needs. Unless BACKBONE CONTRIBUTES holds (§I.8.2), the outcome is reported as "addressed by a memory-side encoder of the input; the frozen backbone contributes nothing to addressing". Only arm BB (§I.3.2), included by the human lead's decision (§15.3), lets the model itself form the query.

**Question.** Can a small learned interface deliver a fact's identity to the memory at the position where the answer is produced, what is the least such interface, and does it need the model to change?

- **H18-NAT (expected to fail; baseline).** The natural query — a learned linear projection of the answer-site hidden state — retrieves facts above chance.
- **H18-WIN.** A learned linear query over the hidden states of the last seven positions retrieves facts nearly as well as an oracle query.
- **H18-ATT.** A learned four-head attention layer over the causal prefix forms a query that retrieves facts nearly as well as an oracle query, without being given a window. The auditor's probe predicts this fails over frozen states.
- **H18-BB (does the frozen backbone contribute?).** The window query over block-0 states is better than the same query over raw embeddings. The auditor's probe on rehearsal draw 0 predicts the opposite: E7 ≥ W7.
- **H18-MODEL.** With the block-0 attention trained together with the memory, the natural query retrieves facts nearly as well as an oracle query.

Each can fail. Every class is a statement "within U updates" (§I.6), not about what longer training could reach.

### I.3 Interfaces under test

All use the flat memory of §5 (cosine keys, top-8, temperature 0.2, key width 16), read **at the answer site only**, and add the read there. Reading at other positions is not used: §I.1 shows it cannot reach the answer.

#### I.3.1 Core arms

| Arm | Query at the answer site t | Trained | Extra parameters |
|---|---|---|---|
| N natural | W·h_t | keys, values, W, output projection, gate | — (historical) |
| W7 window | W·[h_{t−6}; …; h_t] | as N, with the wider W | 16 × 224 − 16 × 32 = 3,072 |
| E7 embedding window | W·[e_{t−6}; …; e_t], e = token + position embedding (no block) | as W7 | 3,072 |
| A4 attention | one attention layer, 4 heads × 8, bias-free q, k, v (32 × 32 each); query from h_t, keys and values over the full causal prefix h_0…h_t; in the form of the backbone's attention (causal, scores scaled by 1/√8, no layer norm, no output projection); its output, then W | as N, plus the layer | 3 × 32 × 32 = 3,072 |
| A4E | A4 with e in place of h | as A4 | 3,072 |
| R1 oracle-query reference | fixed random unit code per fact (§5.3) | keys, values, output projection, gate | — |
| R2 oracle address | dedicated slot per fact | values, output projection, gate | — |

- h is the frozen block-0 output; the frozen backbone is unchanged in every core arm. The interface is part of the memory addition and is trained with it.
- **W7 is told the record length** (seven positions). That is the task leaking into the design, and is stated with every W7 result.
- **A4 is given no window.** It must learn where to look in the whole prefix. This is the reason it is preferred over W7 when both work. The auditor probed a 16-position window (two records, also task-shaped); the full-prefix form is unprobed.
- **A1 (one head) is withdrawn.** One head with one shared value map is close to a weighted bag of symbols: the probe gave 0.34 / 0.24 / 0.16 at 2,048 / 8,192 / 32,768 facts (B101), and its noise-free idealization 0.81 at 32,768. The numbers are kept in the review.
- **R1 is a reference, not a ceiling:** optimized additive codes match or exceed random codes, so η (§I.5) may exceed 1.
- **Tree variants are withdrawn.** They entered no rule. Routing with the selected interface belongs to the revision of ADR-0017.

#### I.3.2 Arm BB — the model forms the query (included by human decision, §15.3)

- **BB:** the block-0 attention of the backbone (qkv and output projection, 4,224 parameters) is trained together with the memory. Everything else in the backbone stays frozen. The memory reads arm N's natural query W·h_t at the answer site. It joins the one AdamW of §5.1 (lr 0.003) that trains every trainable parameter of the cell; the same gradient clip covers it (corrected, §15.4).
- **BB-D:** D plain (§I.3.3) with the same trainable attention.
- **BB-0:** no memory; the same trainable attention, trained on the answer loss alone.
- Training these 4,224 backbone parameters is approved for this block only (§15.3). It leaves the P4–P8 frozen-backbone lineage; `docs/RESEARCH_HANDOFF.md` names joint training of backbone and memory as the eventual path.
- The backbone's next-byte loss on its own corpus rows is reported before and after for BB, BB-D and BB-0 (descriptive; the answer loss does not protect it).
- Feasibility evidence, not a result: the input a retrained block-0 attention sees is the embedding, and four heads over embeddings reach 0.99 / 0.97 / 0.85 in the oracle-store probe (B101; B102 0.98 / 0.94 / 0.81).

#### I.3.3 Dense controls

- **D plain:** the P4/P5 adapter on h_t, parameter-matched to arm N. Expected at chance.
- **D7 window:** the adapter on [h_{t−6}; …; h_t], hidden width set so its parameter count matches arm W7 **including the interface** within 0.1% (786 / 3,090 / 12,306 hidden units at the three sizes). Same window, same parameters, same updates.
- **D plain, D7 and BB-D add their output at answer sites only**, like the memory.

### I.4 Task, data, loss

- Task, identifiers, templates, clusters, streams and panels exactly as §4 (family 1), with the data generator already implemented and its gate G1.
- **Loss: cross-entropy over the 32 alphabet symbols at answer sites**, for every arm. Scoring is the most probable alphabet symbol, ties wrong. Loss and scoring use the same output set. Training is therefore not comparable with ADR-0017's R0a or P4–P8, which use the 256-way loss.
- **Matched updates.** Every cell runs the same number of updates U, and **U is the same at every size** (§I.6). Exposures per fact therefore differ across sizes (sixteenfold: 256 / 64 / 16 at U = 4,096) and are reported per size. Matched exposure is not used in any rule.
- Nothing is added at non-answer positions in any core arm. In the BB arms the trained attention changes all positions; that is reported (§I.3.2).

### I.5 Measurements

- Accuracy on primary panels A and B; H1/H2 and mixed-cluster panels secondary. **Every rule in §I.8 uses accuracy.** I_acc (Fano bound with the chance floor, §6.1), the Σ-renormalized log-loss gain (§6.1 secondary) and the 256-way loss are reported descriptively.
- **Interface efficiency** η = accuracy(arm) / accuracy(R1), same size, seed and panel.
- Query diagnostics: mean cosine between queries of different facts; share of facts whose nearest other query is closer than 0.9; for A4, A4E and BB, the attention weight on the five identifier positions.
- Memory dependence: value permutation and disabling; minimal supports as §6.2 restricted to the answer-site read.
- No-memory baseline, exact retrieval, unseen-fact control with the LEAKAGE flag; gate G2 as §8.1. **"Chance" in every rule means inside the G2 interval.**
- Training diagnostics of §6.3; parameters and optimizer-state bytes per arm.

### I.6 Calibration (fresh rehearsal draw, before the freeze)

Draw 0 informed this design, so calibration uses rehearsal draw 1 (data seeds 179101 upward), which no one has observed. Rehearsal draws are limited to k ≤ 9.

- Allowed: controls; **R2 and R1** at the three sizes with the alphabet loss, snapshots at 1,024 / 2,048 / 4,096 / 8,192 / 16,384 updates. Initialization seeds 1791 and 1792 on parent B101/O301, and 1791 on B102/O302 (calibration only; never registered).
- **Rule:** U is the smallest of {2,048, 4,096, 8,192, 16,384} at which, at every size, R2 accuracy ≥ 0.95 **and R1 accuracy ≥ 0.90**. Each is the minimum over the two B101 calibration runs and both panels; the B102 run is reported.
- A size at which no U qualifies is `TASK_CEILING_FAIL` (R2) or `ORACLE_QUERY_FAIL` (R1) and is not run. U is then the smallest value qualifying at the remaining sizes.
- R1 is an oracle rung, not an interface. No arm of §I.3 other than R1 and R2 is run, and no representation probe is run on draw 1.
- No BB arm is calibrated. A BB class below INTERFACE_WORKS is a statement within a U calibrated on the frozen backbone's oracle rungs.
- If calibration marks any size failed, the outcome is INCONCLUSIVE by §I.8.3 step 0 before the run; the human lead decides at decision 2 whether the remaining sizes are run.
- After calibration only U and the failed sizes may change. Anything else is a new revision.

### I.7 Matrix and seeds

Initialization seeds 1801 and 1802 on parent B101/O301; one replicate (seed 1801, parent B102/O302) where marked. **Registered data seeds 182001 upward** (clear of the rehearsal range 179001–179999 and of the constants 180101–181900 the auditor's probe scripts used). ADR-0017's registered seeds stay unused.

| Size (slots / facts) | Arms | Cells |
|---|---|---|
| 16,384 / 8,192 | N, W7, E7, A4, A4E, R1, R2, D plain, D7 | 18, + B102 replicate of W7, A4, R1, D7 = 22 |
| 65,536 / 32,768 | N, W7, A4, R1, D7 | 10 |
| 4,096 / 2,048 | N, W7, A4, R1 | 8 |
| **Core total** | | **40** |
| Block BB: 16,384 and 65,536 | BB, BB-D, BB-0 | 12, + B102 replicate of BB at 16,384 = 13 |
| Block BB: 4,096 | BB, BB-0 | 4 |
| **Total with block BB** | | **57** |

Three sizes are included so that the selected interface is known to work across the range ADR-0017 needs, not to measure capacity. No capacity class is derived here.

### I.8 Classes and the selection rule

#### I.8.1 Interface class

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

Step 0 of §I.8.3 refers to the size: a size is NOT_EVALUATED when R1 is below 0.5 there, whatever an arm prints.

The B102 replicate is reported and must not have raw class FAILS on either panel for INTERFACE_WORKS to stand at 16,384; otherwise the class there is INTERMEDIATE.

For BB, after the B102 rule: a class INTERFACE_WORKS becomes **MODEL_STORES_FACTS** if BB-0's accuracy is above the G2 interval at that size on either B101 seed or panel. Reading fixed now: the trainable attention can by itself retrieve facts at that size, so BB's result cannot be attributed to the memory interface alone, even though BB's own ablations show that it uses its memory.

#### I.8.2 Annotations (printed per size; they do not change a class)

- **Dense comparison**, for W7 against D7 and BB against BB-D, at each size where both run. Compared only if the arm's class is INTERFACE_WORKS or INTERFACE_PARTIAL; otherwise NOT COMPARED. With r = accuracy(arm) / accuracy(dense), paired by seed and panel, the smallest of the four values: **BEATS DENSE** if r ≥ 1.10; **DENSE SUFFICES** otherwise. BEATS DENSE is unreachable when the dense accuracy exceeds 1/1.10 ≈ 0.909; DENSE SUFFICES then means within 10% relative accuracy. Reading fixed now: DENSE SUFFICES means a dense adapter on the same input does as well within U updates at that size. It is a statement about this task and budget, not about the query interface or about memory in general. The auditor's toy predicts DENSE SUFFICES at 16,384 and probably not at 65,536; such a difference between sizes would be consistent with the sixteenfold difference in exposures per fact and is not evidence about capacity or the interface. A4 and A4E have no dense comparator (no dense arm reads the full prefix); their dense comparison is NOT COMPARED, and that is carried if A4 is selected.
- **Backbone contrast** at 16,384, for the pairs E7/W7 and A4E/A4. With r = accuracy(embedding arm) / accuracy(state arm), paired by B101 seed and panel (four values): **BACKBONE HURTS ADDRESSING** if all four r ≥ 1.03; else **BACKBONE ADDS NOTHING** if all four r ≥ 0.97; else **BACKBONE CONTRIBUTES** if all four r < 0.97; else **BACKBONE CONTRAST MIXED**. Not printed if both arms are INTERFACE_FAILS. BACKBONE HURTS is unreachable when the state arm exceeds 0.971.
- **Language modelling** (BB arms only): **LANGUAGE MODELLING DEGRADED** if the backbone's next-byte loss on its own corpus rows rises by more than 5% relative to before training, on either B101 seed. It does not block selection; it is carried with BB, and whether a degraded backbone is acceptable is the human lead's decision when ADR-0017 is revised.

#### I.8.3 Selection rule for a revision of ADR-0017 (fixed now)

0. If any of the three sizes is TASK_CEILING_FAIL, ORACLE_QUERY_FAIL or NOT_EVALUATED → **INCONCLUSIVE AT that size.** No interface is selected, the classes at the remaining sizes are reported, and the human lead decides. This is not step 4.
1. If BB is INTERFACE_WORKS at all three sizes → BB: the model forms the query. A revision of ADR-0017 would then train the block-0 attention, and needs approval for that.
2. Else if A4 is INTERFACE_WORKS at all three sizes → A4.
3. Else if W7 is INTERFACE_WORKS at all three sizes → W7, with the limit that it is told the record length.
4. Else → no tested interface reached INTERFACE_WORKS at all three sizes within U updates; the class of each arm at each size is reported; ADR-0017 stays blocked on this backbone.

The selected interface carries its scope statement (§I.2), its backbone-contrast annotation and its dense-comparison annotation into the revision of ADR-0017 and into every summary. If BB is selected, the before/after next-byte loss of BB, BB-D and BB-0 and the language-modelling annotation are carried with it. If A4 or W7 is selected, ADR-0017 would test a memory with its own input encoder, a different system from the P4–P8 memory addressed by the backbone's state.

### I.9 Gates and status

- G1 (generator), G2 (chance; 8 tests as §8.1).
- G4: determinism and checkpoint restoration. For equal parameters and inputs, arm N's forward equals ADR-0017's R0a forward bit for bit; training differs by the loss. At initialization, BB's forward equals N's, BB-D's equals D plain's and BB-0's equals the no-memory baseline's.
- `ENGINEERING_FAIL`, `INCOMPLETE` and no re-run with changed settings, as §8.6. No cell here depends on another.

### I.10 Resources (projection, not a measurement of this study)

- Measured in P9: R2 at 65,536 slots ran 32,768 updates in 386 s (0.012 s per update). That is the only measurement. With the auditor's assumed costs (0.05 / 0.02 / 0.015 s per update at 65,536 / 16,384 / 4,096 slots), the core matrix takes 2.4 hours serial at U = 8,192 and 4.8 hours serial at U = 16,384, or about 0.4 and 0.8 hours with six single-thread workers. Block BB backpropagates through block 0 at every position and is not estimated; the rehearsal measures it.
- Calibration (18 runs up to 16,384 updates): about 93 minutes serial, about 16 minutes with six workers, at assumed costs.
- **Caps (human decision, §15.3):** 3 GiB per worker and 24 GiB aggregate; **4 hours of charged execution for calibration, rehearsal and the run together, block BB included** (the lead's stricter reading of the decision; if the cap would be exceeded the work stops and returns to the human lead). The rehearsal measures time and memory only and fixes the stage caps.

### I.11 Implementation

- New package `studies/p9i/` beside `studies/p9/`, importing the P9 data, memory, training, evaluation and job-manager code. **Imported P9 code is tested, not audited** (the calibration audit covered R2, the probes, G2, the controls and the exposure rule only). The Part I implementation audit covers every imported path used.
- No existing file changes; ADR-0017's code and records stay as they are. Records carry this study's code (P9I), not P9.
- The alphabet loss, answer-site-only reads and dense outputs, matched updates and the trainable block-0 attention are added in the new package.

### I.12 Order of work

1. Auditor confirmation of this revision; revise until ready.
2. **Human decision 1:** taken (§15.3).
3. Implementation with tests (gradient reach for each interface; arm N forward identical to R0a; D7 parameter match; BB trains only the 4,224 attention parameters; every class, annotation and selection outcome triggered on synthetic records).
4. Calibration on rehearsal draw 1 (§I.6); audited.
5. Rehearsal for time and memory; implementation audit; freeze.
6. **Decision 2:** delegated to the lead within the limits of §15.3; otherwise the human lead's.
7. The run, once; independent recomputation; report.

### I.13 What must not be claimed

- Anything about capacity scaling, utilization, locality or incremental learning. None is tested. **A difference in class between sizes is not evidence about capacity:** exposures per fact differ sixteenfold.
- That a WORKS class for W7, E7, A4 or A4E shows the language model communicating what it needs (§I.2).
- That INTERFACE_WORKS for BB shows that a language model reliably communicates what it needs. BB retrains the block-0 attention on this task's answer loss alone, with its next-byte loss unprotected; it shows that a jointly trained backbone attention can form a query for this synthetic task within U updates.
- That an interface that works here would work on natural language. The task has fixed-length records and random identifiers.
- That W7 is a general interface: it is told the record length.
- That a failure of all interfaces is a failure of the ArborLM concept, or more than a statement about this backbone within U updates.
- That DENSE SUFFICES says memory is not needed in general.
- That the oracle rungs are systems.

### I.14 Decisions reserved for the human lead

Taken on 2026-11-14 (§15.3): the prerequisite is folded into this ADR; block BB is included; the cap; decision 1; decision 2 delegated to the lead with the limits recorded in §15.3. Still reserved: any revision of Lanes A–D after Part I; ADR-0012; merge; publication; any next phase.

### I.15 Approval record

§15.3.

### I.16 Map of the revision-1 review to this revision

| Finding | Change |
|---|---|
| B1 scope dodges the question | §I.2 scope paragraph; §I.3.2 arm BB; §I.8.3 carries annotations; §I.14.2 as a choice |
| B2 U calibrated on R2 only | §I.6 calibrates on R2 and R1 (0.90), adds 16,384 updates; §I.8.3 step 0 INCONCLUSIVE |
| M1 one head is a bag of symbols | A1 withdrawn; A4 (full prefix) and A4E added |
| M2 dense annotations overlap | one ratio, exclusive labels, dense arms at answer sites only, fixed reading (§I.8.2) |
| M3 backbone annotation one-sided | three-way backbone contrast, both pairs (§I.8.2); prediction in H18-BB |
| M4 precedence incomplete | two-step tables (§I.8.1) |
| M5 "audited" imports | §I.11 "tested, not audited"; G4 reworded |
| M6 exposure bias inverted | §I.4 exposures per size; §I.13 |
| m1 timing figure | §I.10 uses the measured 0.012 s and the auditor's estimate |
| m2 seed collision | registered data seeds 182001 upward; draws k ≤ 9 |
| m3 calibration init seeds | 1791, 1792 (§I.6) |
| m4 N at 4,096 | added (§I.7) |
| m5 R1 a reference | §I.3.1 |
| m6 one metric family | accuracy in every rule (§I.5, §I.8) |
| m7 Σ-renormalized loss | §I.5 |
| m8 "fourfold" | §I.1 |
| m9 Astra marker | status line |
| m10 cost of a separate ADR | header, §I.14.1 |
| m11 hour cap | §I.10, §I.14.3 |
| m12 parameter counts | confirmed; D7 widths stated (§I.3.3) |
| m13 tree arms | withdrawn (§I.3.1) |
| m14 chance defined | §I.5 |
| J(i) probes in calibration | not adopted: nothing but R1 and R2 is observed on draw 1 |
| J(ii) 2 × 2 | adopted under option b: {W7, BB} × {memory, dense} |

#### Confirmation of revision 2 (CONFIRM.md)

| Finding | Change |
|---|---|
| R1 precedence and panel disagreement | §I.8.1 step 2 replaced |
| R2 backbone contrast default | four-way rule (§I.8.2); §I.2 scope "unless BACKBONE CONTRIBUTES" |
| R3 BB block | BB-0 added at 4,096 (57 cells); MODEL_STORES_FACTS reworded and ordered after the B102 rule; learning rate stated; U not calibrated for BB |
| R4 BB over-reading | §I.13 line; next-byte loss carried; lead's choice: LANGUAGE MODELLING DEGRADED annotation at 5%, not a block on selection |
| n1–n8 | §I.8.2, §I.8.3 step 4, §I.6, §I.10, §I.14.2, §I.3.1 (A4 form), §I.9 |
