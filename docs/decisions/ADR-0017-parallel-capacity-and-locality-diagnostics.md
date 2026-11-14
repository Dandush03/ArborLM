# ADR-0017 — Parallel useful-capacity, anti-collapse and locality diagnostics (P9)

- **Status: DESIGN REVISION 2 — NOT APPROVED. No implementation, calibration, rehearsal, training or evaluation is authorized by this text.**
- **Date:** 2026-11-14
- **Revision history.**
  - Revision 0: the human lead's draft, unchanged at `docs/reviews/adr-0017-design-2026-11-14/ADR-0017-draft-rev0-human.md`.
  - Revision 1: the Claude lead's design (git history). Reviewed by Opus 5.5: **NOT READY**, 3 blockers, 14 major, 18 minor — `docs/reviews/adr-0017-design-2026-11-14/REVIEW.md`.
  - Revision 2 (this text) answers that review; §16 maps every finding to its change.
- **Origin.** The human lead asked in chat on 2026-11-14 for the design to begin and stated that the request is not permission to launch the study.
- **Roles (proposed, study-specific).** Lead: Claude Fable 5.2. Independent audit: Opus 5.5. Implementation and simulations: Sonnet 5.5. Inventory: Haiku 5.5. Actual models are recorded per delegation. ADR-0012 stays not approved. **Astra review: NOT_PERFORMED.**
- **Companions:** `EXECUTION_PLAN.md`, `RESOURCE_BUDGET.md`, `EVIDENCE_INVENTORY.md`, `REVIEW.md` in `docs/reviews/adr-0017-design-2026-11-14/`.

## 0. Departures from the human draft that need the human lead's explicit acceptance

1. **Family 2 (compositional) is not run.** With one memory read between frozen layers no read can depend on another read's result, so a latent two-hop answer cannot be computed (auditor confirmed). An explicit chained version would test lookup under a changed template, not composition. Running it would spend cells on a result that cannot bear the name. It is described in §4.5 as an option the human lead can restore.
2. **Two approvals instead of one** (§12): approval of this specification for implementation, calibration and rehearsal; later, approval of the frozen final revision for the run.
3. **A testbed calibration before the freeze** (§12 step 4), on rehearsal seeds, limited to controls and the readout rung, able to change only the exposure count from a fixed menu.
4. **Caps are proposed, and fixed only at the second approval** on rehearsal evidence (§11). The projection exceeds the draft's 8 hours and 2 GiB.
5. **MPS is not used.** Equal frequency only; skewed fact frequency is untested.
6. **Cache size follows distinct selected slots on the calibration stream**, and is also reported against useful slots (§8.4).

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
| C — locality | D08, D09 | synthetic part: none. Trained part: the 4K→16K capacity step is supported for the architecture concerned (§8.2), and the cell is UTILIZATION_PRESERVED or UTILIZATION_IMPROVED |
| D — incremental | D10 | G1–G4 on sets A and B; phase-A accuracy ≥ 0.5 |

All lanes run in parallel after the common freeze, as the draft asks. If Lane C's gate fails its trained part is **H17-LOC NOT EVALUATED**, descriptive only. A passing subset is never promoted.

*Option for the human lead (auditor's suggestion, not the default):* run Lane A first and launch B–D only if the 4K→16K step is supported. It saves about 30 cheap cells if Lane A fails and costs the parallelism the draft asks for. The calibration of §12 already removes the main risk of an invalid task.

## 4. Task and data

Generated locally from frozen seeds. No corpus, download, teacher or third-party data.

### 4.1 Facts

- **Alphabet Σ:** 32 printable ASCII bytes, fixed in the config.
- **Identifier:** 5 symbols; the first four uniform, the fifth their sum modulo 32. Any two identifiers differ in at least two positions, at every size. Without this, the share of facts with a one-symbol neighbour would rise from 22% to 98% across sizes and facts would get harder for a reason unrelated to memory.
- **Answer:** 1 symbol, uniform and independent of everything else. Chance is 1/32; a fact carries 5 bits.
- **Counts:** proportional track 2,048 / 8,192 / 32,768 facts at 4,096 / 16,384 / 65,536 slots; fixed track (D04) 2,048 facts at every size.
- **Unseen-fact control:** 2,048 valid identifiers never trained, random answers.

### 4.2 Records, contexts, templates

- **Record:** 8 bytes — separator, 5 identifier bytes, binding byte, answer byte. The **answer site** is the binding byte's position; its target is the answer byte.
- **Context:** 64 bytes = 8 records; with next-byte targets this gives 63 targets, of which exactly 8 are answer sites.
- **Template:** a (separator, binding) byte pair. The pool is the 48 bytes most frequent in the backbone's training corpus that are not in Σ; 16 training pairs T, 8 pairs H1, 8 pairs H2, split by seed, so held-out templates are exchangeable with training ones. One template per context.

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
2. Independence of answers from each identifier position, template, cluster and record index, by Monte Carlo permutation tests (10,000 permutations, seeded), none below 0.001 after Bonferroni correction. Chi-square is not used: its expected counts would be below 5.
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
- **Row-lazy Adam arm (A10):** flat R0 at the three sizes with per-row moments, a row updated only when its gradient is non-zero, bias correction by the row's own update count. Each exposure then moves a row about one learning rate at every size.
- **Value permutation and memory disabled** on every trained memory cell.

## 6. Measurements

### 6.1 Knowledge

With e = 1 − accuracy over F facts, accuracy counted on the most probable symbol within Σ, ties counted wrong:

- **Primary: I_acc = F · [5 − h₂(e) − e·log₂31] bits** (Fano bound; exactly 0 at chance, 1.52 bits per fact at accuracy 0.5). Every rule uses I_acc.
- **Secondary:** the unfloored log-loss gain Σ_f (5 + log₂ p_f) with p_f renormalized over Σ; it can be negative.
- Descriptive only: a floored sum (it is positive for a model that knows nothing, so it enters no rule); probability mass outside Σ; accuracy by template panel.
- Ratios per slot, per stored parameter and per key product (logical).

### 6.2 Useful slots

- **Knock-out:** at one fact's answer site, keep selection and weights, remove the chosen slots' values from the weighted sum, leave all other positions unchanged. Selections and weights are cached, so no knock-out needs a table edit.
- **Minimal support of a fact:** the shortest prefix of its selected slots in order of weight whose knock-out makes the fact incorrect with p_f ≤ max(2/32, p_f^nomem + 0.02), p_f^nomem being the no-memory probability of the correct symbol. Facts answered incorrectly have none.
- **Useful slot:** a slot in at least one minimal support. **U\*** is their count.
- **Specificity (condition for interpreting U\*):** knocking out 8 slots drawn from other facts' minimal supports changes p_f by less than 0.05 on at least 95% of facts; and zeroing one of 64 contiguous slot groups leaves facts whose minimal support avoids the group within 0.02 accuracy. If either fails, U\* is marked NOT INTERPRETABLE for the cell and the classes that use it are INTERMEDIATE.
- Reported, never used alone: distinct selected slots, entropy-effective slots, hot-64 share, dead slots, weight entropy of each read, facts per slot, keys first entering any query's top 64 after update 0.

### 6.3 Optimization (every cell, no extra cells)

- Per update and parameter group: gradient norm of the task loss and of each regularizer, and norm of the parameter change.
- **Per key row and value row: cumulative movement on updates where the row had a task gradient, and on updates where it had none.** This answers the P8 question directly.
- Per snapshot: 8th–9th score margin distribution, soft mass outside the top 8, whether each regularizer's hinge was active, dead-slot count.
- Trainable parameters, initialized slots and optimizer-state bytes per cell.

## 7. Objectives (D07, D08)

Soft inclusion as ADR-0015 revision 3: π_s = σ((score_s − τ)/0.25) on a query's top-64 candidates, τ the midpoint of the 8th and 9th scores, not detached.

**Global usage floor.** u is an exponential moving average of the batch-normalized π usage over the last F/128 updates (one pass over the facts); the gradient flows only through the current batch's term. With M = min(N, 8F)/2:

R_glob = max(0, ln M − H(u)) / ln N.

It is zero while the memory spreads over at least half of the slots it could use. A batch-local floor is not used: a memory using a thousand slots would satisfy it at any size.

**Stated limit.** A key that is in no query's top 64 receives no gradient from any term and cannot be revived by gradient. The study measures how many keys enter a top 64 after update 0; it does not claim a cure for dead slots.

**Locality.** R_co of ADR-0015 (expected number of 8-slot identifier groups touched per selected slot), unchanged.

**Coefficients — absolute, no measurement, no cap, no adaptation:**

- λ_u = α_u · ln 32 / (ln M / ln N): a fully collapsed memory costs α_u times the chance-level answer loss.
- λ_c = α_c · ln 32 / (1 − 1/8): the worst co-access value costs α_c times the chance-level answer loss.
- Doses: α_u ∈ {0, 0.25, 1}; α_c ∈ {0, 0.25, 1}, the non-zero α_c only together with α_u = 0.25. No other dose is run; none is selected afterwards.

Revision 1's rule (a coefficient from gradient norms at initialization, capped at 100) is withdrawn: in P8's own records the usage hinge would have been inactive at initialization in every flat cell, giving a zero gradient, and both doses would have hit the cap in the tree cells.

## 8. Gates, thresholds, classes

Thresholds may change only before the freeze, by a recorded revision approved at the second decision.

### 8.1 Task gates

- **G1** generator checks (§4.6).
- **G2** chance: no-memory baseline and unseen-fact accuracy, once per size × track × primary panel (16 tests), each inside the exact binomial central interval of level 1 − 0.001/16 around 1/32. The same corrected interval is "chance" wherever a rule says so.
- **G3** readout ceiling, **decided in the calibration** (§12 step 4): R2 accuracy ≥ 0.95 on rehearsal panels at every size at the selected exposure. If it is not reached at E = 128 at some size, that size is `TASK_CEILING_FAIL` and is not run. In the registered run R2 is a diagnostic.
- **G4** determinism and identity: checkpoint restoration, stream hashes, P5 forward invariance.

### 8.2 Capacity (flat and learned tree separately; R0; matched exposure; Panels A and B separately)

Let I_N be I_acc at size N.

- **Step supported** (N → 4N): I_{4N}/I_N ≥ 3.0 in both B101 seeds and ≥ 2.5 in the B102 replicate, and accuracy at 4N above the G2 interval in every cell.
- **Beats dense:** I ≥ 1.10 × the matched dense adapter's, both seeds, at the larger size.
- **Dependence:** value permutation and disabling give chance accuracy; at least 90% of correctly answered facts have a minimal support.
- **Plateau:** the gain from the ½U snapshot to U is below 5% of I at U.

Classes, **first matching rule wins**:

| Order | Class | Rule |
|---|---|---|
| 1 | NOT REPLICATED | Panels A and B would give different classes |
| 2 | CAPACITY_NOT_SUPPORTED | some step has ratio < 2.0 in both seeds and its larger cell has plateaued |
| 3 | CAPACITY_POSITIVE | both steps supported; beats dense at 16K and 64K; dependence holds; accuracy at 64K ≥ 0.50 |
| 4 | CAPACITY_PARTIAL | the 4K→16K step is supported, with beats-dense and dependence at 16K |
| 5 | UNDERTRAINED | some step is not supported and its larger cell has not plateaued |
| 6 | INTERMEDIATE | otherwise |

Annotations (they do not change the class, and are always printed with it):

- **EMPTY-SLOT-EFFECT** if, at 2,048 fixed facts (D04), I_acc per fact rises by more than 25% from 4K to 64K.
- **OPTIMIZER-DEPENDENT** if a step supported under AdamW is not supported in the row-lazy arm (A10).
- **KEY-WIDTH-LIMITED** if key-32 R0 supports the 16K→64K step and key-16 R0 does not.
- **TREE_COMPETITIVE** (D03) if tree I_acc ≥ 0.97 × flat I_acc at 16K in both seeds and both panels; otherwise TREE_BEHIND; the fixed tree is reported beside it.

**Ladder report**, per size, in Fano bits per fact with sign: exact − R2, R2 − R1, R1 − R0a, R0a − R0, and tree oracle-branch − tree R0; with the frozen-hidden probes beside R0. A gap is called material at ≥ 0.5 bits per fact.

### 8.3 Utilization (per architecture, against its dose-zero 16K cell; both seeds; both panels; first match wins)

| Order | Class | Rule |
|---|---|---|
| 1 | NOT REPLICATED | panels disagree |
| 2 | COLLAPSED | U\* ratio < 0.80 or I ratio < 0.90 |
| 3 | ENTROPY_INFLATION | entropy-effective slots ratio ≥ 1.25, I ratio < 1.03 and U\* ratio < 1.03 |
| 4 | UTILIZATION_IMPROVED | I ratio ≥ 1.05 and U\* ratio ≥ 1.05 |
| 5 | UTILIZATION_PRESERVED | I ratio ≥ 0.97, accuracy drop ≤ 0.02, U\* ratio ≥ 0.97 |
| 6 | NO DIFFERENCE / INTERMEDIATE | otherwise |

### 8.4 Locality (trained part, gated by §3)

- **Simulator:** re-implemented for general N (the P7-B code fixes 4,096 slots, a dense co-access matrix that would need 16 GiB at 65,536, and 16-bit layout files). Required before use: exact equivalence with P7-B on P7-B's recorded traces at 4,096, and a sparse co-access count. ADR-0016's identity null for single-set streams only.
- **Traces:** answer-site reads (primary); all-position reads (secondary).
- **Cache rule, fixed before evaluation:** W = distinct slots selected at answer sites on the calibration stream; R slots per page; cache pages C = max(1, round(ρ·W/R)); primary settings ρ ∈ {1/16, 1/4} × R ∈ {8, 32}. The ratio of cache to U\* is reported for every cell.
- **E** = actual misses / mean of three count-preserving nulls. Null miss rate below 0.05, or a single-set stream, makes the setting DEGENERATE.
- **Comparison:** E of the case and E of the reference, **each under its own optimized co-access layout fitted on its calibration stream**; the same under identity layout is reported beside it.
- **References:** locality reference = the dose-zero flat 16K cell; utilization reference for a locality cell = the cell with α_u = 0.25, α_c = 0 of the same architecture.
- **Oracle layout (bound):** each slot goes to the cluster with most of its calibration accesses, ties to the lowest cluster number; clusters contiguous.
- **Expectation stated in advance:** on this stream the reference's own optimized layout is expected to reach E near 0.77 when slots are shared at random across clusters, and far lower when sharing follows clusters (auditor's calculation). The test is therefore whether training changes how slots are shared, beyond what a layout fitted afterwards achieves.

Classes, all four settings, both tie rules, both seeds, both panels, first match wins:

| Order | Class | Rule |
|---|---|---|
| 1 | NOT REPLICATED | panels disagree |
| 2 | DEGENERATE | any primary setting is degenerate |
| 3 | COLLAPSED / QUALITY_FAILED | §8.3 COLLAPSED, or I ratio to the locality reference < 0.97 |
| 4 | LOCALITY_POSITIVE | E ratio ≤ 0.80; cell UTILIZATION_PRESERVED or IMPROVED |
| 5 | CONCENTRATION_ONLY | raw miss ratio ≤ 0.80 and E ratio > 0.90 |
| 6 | WORSE / NO DIFFERENCE / INTERMEDIATE | E ratio ≥ 1.10 / in (0.90, 1.10) / otherwise |

A hierarchy advantage needs the tree case to be LOCALITY_POSITIVE against the **flat case with the same doses**.

### 8.5 Incremental (Lane D; 16,384 slots; A and B are 4,096 disjoint facts each)

- Phase A: E exposures of A. Phase B from snapshot V1: E exposures of B.
- Arms in phase B: flat sequential (all addition parameters train); flat memory-only (keys and values train; projections and gate frozen); learned tree sequential; flat with replay; dense sequential; dense with replay; flat joint on A∪B from initialization (bound); exact retrieval (append).
- **Replay** keeps B's E exposures and adds one replayed A record per B record as extra rows; updates and examples are reported, and replay arms are compared only with each other and the bound.

With a_A, a_B accuracy after phase B and a_A⁰ accuracy on A after phase A; classes need a_A⁰ ≥ 0.5, else NOT_EVALUATED. First match wins:

| Order | Class | Rule (both seeds, both panels) |
|---|---|---|
| 1 | NOT REPLICATED | panels disagree |
| 2 | NO_NEW_CAPABILITY | a_B < 0.5 × the joint bound's accuracy on B |
| 3 | FORGETTING | a_A < 0.70 × a_A⁰ |
| 4 | INCREMENTAL_POSITIVE | a_B ≥ 0.9 × the joint bound on B; a_A ≥ 0.90 × a_A⁰; and a_A exceeds the dense sequential arm's a_A by at least 0.10 absolute |
| 5 | INTERMEDIATE | otherwise |

If the dense sequential arm itself retains a_A ≥ a_A⁰ − 0.10, the last condition cannot be met and the result is reported as **NO ADVANTAGE OVER DENSE**, which is a finding.

Reported: slots and bytes changed between V1 and V2, overlap of A and B minimal supports, updates, examples, logical lookup work.

**Version store (engineering test only):** copy-on-write snapshots and atomic manifest publication in a local directory; a reader pinned to V1 while V2 is prepared; no mixed versions, replay equivalence, rollback.

### 8.6 Study status

- `ENGINEERING_FAIL`: identity, determinism, checkpoint or gradient-reach defects only. A regularizer being inactive is a recorded scientific property, not a failure.
- `INCOMPLETE`: any registered cell lacks a record; no class is derived for a lane with a missing mandatory cell; the denominator is never reduced.
- A failed cell stops the launch of cells that depend on it — **in every stage, enforced by the job manager and tested** (the P8 deviation). Other lanes continue. Nothing is re-run with changed settings.

### 8.7 Decision map

1. Flat or tree CAPACITY_POSITIVE without OPTIMIZER-DEPENDENT → a separately approved capacity-scaling protocol may be proposed.
2. Capacity positive or partial, locality not positive → redesign placement or routing.
3. Capacity not supported with a material ladder gap → investigate the indicated component (representation at R1 − R0a, interference at R0a − R0, keys at R2 − R1, width if KEY-WIDTH-LIMITED, optimizer if OPTIMIZER-DEPENDENT).
4. `TASK_CEILING_FAIL`, or capacity not supported with no material gap → pause the line or redesign the testbed.

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
| C1 locality dose 0.25 and 1 × flat, learned tree (usage 0.25, 16K) | 4 | 8 |
| D1 phase A: flat, learned tree, dense | 3 | 6 |
| D2 phase B: six trained arms; joint bound | 7 | 14 |
| **Total trained cells** | | **100** |

No training: exact retrieval, no-memory baseline, frozen-hidden probes, at every size and track.

Data seeds: facts 170001, templates 170011, clusters 170031, training order 170041, calibration stream 170051, Panel A 170061, Panel B 170071, H1/H2 170081, mixed-cluster 170082, Lane D sets 170091 and 170092, R1 codes 170101, branch hash 170102, permutation tests 170111. Null seeds 171331–171333 (A) and 171341–171343 (B). Rehearsal and calibration seeds are 179001 upward and appear in no registered cell.

## 11. Resources

- Apple M5 Max, 18 cores, 48 GB; CPU only.
- **Projection (`RESOURCE_BUDGET.md`), not a measurement:** about 4 to 6 hours of charged execution at E = 32 (three or two training workers), and roughly twice that at E = 64.
- **Proposed at the first decision:** a cap of 3 hours and 3 GiB per worker for calibration and rehearsal together.
- **Fixed at the second decision, on rehearsal evidence:** per-worker and aggregate RSS caps, stage caps at twice the measured stage time, and the total. The draft's 8 hours and 2 GiB are not expected to hold twofold headroom; the registered reductions are listed in the budget.
- At most three training workers, four simulation workers. Timing runs alone, with load recorded. No cloud, paid service, download or storage experiment.

## 12. Order of work

1. Auditor re-check of this revision.
2. **Human decision 1:** approve this specification for implementation, calibration and rehearsal; accept or change the departures of §0; approve the delegation.
3. Implementation with tests, including synthetic inputs that trigger every class and the dependent-cell stop rule.
4. **Testbed calibration, rehearsal seeds only, written and audited.** Allowed: the frozen-hidden probes at 2,048 / 8,192 / 32,768 rehearsal facts; the R2 learning curve at each size up to E = 128; no-memory and exact controls; the largest answer probability attainable through the frozen final layers (linear algebra on frozen weights). **Not allowed:** any R0, R0a, R1, tree, dense or regularized arm. **It may change one thing, by this rule:** E is the smallest of {32, 64, 128} at which R2 reaches 0.95 at every size. A size that fails at 128 is `TASK_CEILING_FAIL`. The probes are reported and change nothing.
5. Full-size rehearsal on rehearsal seeds for time and memory. Its record schema is a whitelist (time, RSS, finiteness, shapes); the auditor checks the schema. Loss and accuracy of compared arms are not recorded.
6. Auditor implementation audit: READY TO FREEZE.
7. Registered data and panels generated and hashed; freeze of specification, code, configs, data and panel identities.
8. **Human decision 2:** approve the frozen final revision, the selected E, the caps and the run.
9. The registered run, once.

## 13. What must not be claimed

- That slot entropy, distinct slots or the floored information sum show capacity.
- That R0a, R1, R2 or oracle-branch results are system results, or that the ladder gives upper bounds.
- That logical work is measured efficiency, or that simulation or the key-traffic identity is storage I/O.
- That locality found here would arise without planted structure; equal-frequency planted clusters are a best case.
- That the usage term revives dead slots, unless §6.2's revival count shows it.
- That Lane D shows continual learning in general, or teacher absorption.
- Anything about composition or reasoning.
- Any generalization across data draws, beyond 65,536 slots, or to a trainable backbone.

## 14. Decisions reserved for the human lead

1. Decision 1 (§12 step 2), including each item of §0 and the Lane-A-first option of §3.
2. Decision 2 (§12 step 8).
3. ADR-0012; merge; publication; any next phase.

## 15. Approval record

None. Pending.

## 16. How revision 2 answers the review

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
