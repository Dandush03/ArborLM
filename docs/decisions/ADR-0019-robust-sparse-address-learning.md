# ADR-0019 — Robust Sparse Address Learning: Escaping Query Collapse Across Data Draws (P9-II)

- **Status: REVISION 4 — CONFIRMED BY THE AUDITOR SUBJECT TO R1–R7, WHICH THIS REVISION APPLIES; CALIBRATED, REHEARSED, AUDITED AND FROZEN (§16); THE SINGLE REGISTERED RUN IS APPROVED BY THE LEAD UNDER THE HUMAN LEAD'S DELEGATION (§16). SPEC: PENDING ASTRA REVIEW. The outcome is recorded in `results/` and the research log, not in this text.**
- **Date:** 2026-11-15 (UTC)
- **Revision history.** Revision 1 (2026-11-15): first draft, reviewed by Opus 5.5 with verdict NOT READY (3 blockers, 9 majors, 17 minors). Revision 2: applied that review under the lead's rulings and listed ten open points. Revision 3: applied the lead's rulings on those open points (§18); confirmation review by Opus 5.5 (`docs/reviews/adr-0019-design-2026-11-15/CONFIRM.md`) with verdict READY AFTER the text edits R1–R7 (two majors, five minors, no blocker). Revision 4 (this text): applies R1–R7 with the values the auditor suggested, which the lead took; §17 maps every finding to its change. The auditor stated that with R1–R7 applied verbatim no further review round is needed, and that any changed passage needs a re-check.
- **Origin.** The human lead's mission "ArborLM — Research Consolidation and P9-II Authorization" (2026-11-15) and the later directions recorded in §16.
- **Evidence it rests on.** P9-I (ADR-0017 Part I): registered outcome COMPLETE — NO_INTERFACE_SELECTED, `results/p9i-run-attempt2-2026-11-15/`; independent review `docs/reviews/p9i-results-2026-11-15/REVIEW.md` (Opus 5.5). The diagnostic runs of that review and of the revision-1 specification review are exploratory and are not registered evidence.
- **Roles (study-specific).** Lead: Claude Fable 5.2. Specification review, implementation audit and recomputation: Opus 5.5, in contexts separate from the integration work. Implementation: Sonnet 5.5. Inventory: Haiku 5.5. ADR-0012 stays not approved. **Astra review: NOT_PERFORMED.** The specification review is neither Astra validation nor a human approval.
- **Relation to other work.** ADR-0017 Lanes A–D stay calibration blocked. This study tests none of capacity scaling, locality or incremental learning. Its outcome feeds the addressing qualification of the later P10 design; it does not start P10.

## 1. What is known, and what is only suspected

Registered (P9-I, one data draw, two initialization seeds, U = 8,192 updates):

- Oracle-query retrieval (R1) 0.967–1.000 and oracle address (R2) 1.000: the memory stores and returns answers when addressed.
- The natural query, the seven-position window query (W7), its embedding version and a four-head attention query: 0.028–0.044 at every size (chance about 0.03).
- The dense adapter on the same window (D7): 0.78–0.80 at 16,384 slots (0.44 on the second backbone), 0.13 at 65,536. The window carries the identity.
- Training the block-0 attention: partial at 4,096 slots (0.54–0.65), with next-byte loss up 67–100%.

Exploratory (the two reviews' diagnostics; other draws, not registered):

- In every run the queries collapse within 64 updates (mean cosine between queries of different facts 0.95–0.998; 1–6 distinct top-1 slots); the loss then sits at ln 32, the answer-symbol marginal.
- 91–99% of the trained pre-normalization query is the same vector for every fact (0.50–0.57 at initialization): the separator, binding byte and position components shared by every record.
- In the collapsed state the gradient of the answer loss on the query projection is small (about 2.7e-6 against 1.9e-2 on the output projection in one diagnostic; 0.0067 on the query projection in another), while an address loss gives 55 times more on the query projection and 285 times more on the keys. A random-target address loss gives the same magnitude.
- W7 at 4,096 slots later escaped and reached 0.94–0.98 in 9 of 11 runs on five other draws; on the registered draw it had not. At 16,384 slots it reached only 0.04 by 8,192 updates on two draws. Within a draw the outcome hardly depended on the initialization seed.
- After global centring, 56–74% of the remaining query variance is (template × record position) structure that a global mean cannot remove.

So the leading hypothesis is unstable optimization of sparse addressing, not missing information and not insufficient storage. That hypothesis has not been tested by a registered experiment. This study tests it.

## 2. Question and hypotheses

**Can a learned query–key interface be trained to give distinct, useful addresses through sparse top-8 retrieval, reliably across independently generated data draws and initialization seeds, and at more than one memory size?**

- **H19-A (collapse under the answer-only objective).** With answer-only training, the queries of W7 collapse early in most cells, the addressing gradient is starved in the collapsed state, and the arm is not reliable across draws.
- **H19-B (addressing supervision).** An auxiliary objective that tells each query which key it should match makes the arm reliable where answer-only training on the same draws and seeds is not.
- **H19-C (staged optimization).** Learning addresses first and answers second is reliable where answer-only training is not, and the function survives the removal of the supervision.
- **H19-D (curriculum).** Starting from a wide differentiable read and narrowing it to the hard top-8 makes answer-only training reliable without any fact identity.
- **H19-F (common mode; added by the lead).** Removing the fact-independent component of the query before normalization (arm A5-C) makes answer-only training reliable without any fact identity.
- **H19-G (query diversity; the human lead's "query-diversity constraint").** A diversity penalty on the batch's queries (arm A5-D) makes answer-only training reliable without any fact identity.
- **H19-E (draw robustness).** A reliable arm succeeds in every draw, not only on favourable ones.

Every reading of H19-B, C, D, F and G is **paired against A0 on the same draw and initialization seed** (§8.4, §8.6). Each can fail, and each can be contradicted. If no learned arm is reliable at 4,096 slots, the result is a registered negative on trainable sparse addressing for this interface and backbone, and the recommendation is a different retrieval architecture, not more compute. If A0 itself is reliable on these draws, the result says that the collapse of P9-I's registered draw is not a reliability failure here, and none of the remedies is shown to be needed.

## 3. System common to all arms

- Frozen 27,392-parameter backbone, the P9-I task (ADR-0017 §4), the flat memory of ADR-0017 §5 (cosine keys, key width 16, top-8, read temperature 0.2), read and added **at answer sites only** (the fixed positions 8r + 6 of every 64-byte input), alphabet-only loss, one AdamW (lr 0.003), gradient clip 1.0, batch as P9-I (16 contexts = 128 answer sites).
- **No backbone parameter is trained in any arm.** This is true of the backbone parameters, not of the system's next-byte predictions: the memory reads at its fixed positions on any input, and block 1 attention carries the read to later positions. Two things are therefore registered:
  - **G5 (backbone identity, §9):** the sha256 of every backbone tensor after training equals the frozen backbone's, and with the addition disabled each arm's logits on the backbone's corpus rows equal the frozen backbone's bit for bit. This is the criterion for the pretrained model itself.
  - **LM capability of the system (measured, §8.2 and §8.4):** the next-byte loss on the corpus rows with the addition active, compared with the frozen backbone's, for every learned arm and for the oracle reference A6.
- Query before normalization: z = W·[h_{t−6}; …; h_t] (the W7 form of P9-I), q = z / ‖z‖. Key k_s for slot s, κ_s = k_s / ‖k_s‖. Score a_s = q·κ_s.
- **No fact identity is an input of any learned arm at inference.** The forward of arms A0, A1, A2, A4, A5-C, A5-D and A1-S takes tokens only (gate G6). Fact identities used in training are listed per arm in §4 as auxiliary supervision.
- Every cell runs exactly its stage's number of updates in total (§5), whatever its phases.

## 4. Arms

| Arm | Mechanism | Fact identity used in training | Extra trained parameters |
|---|---|---|---|
| A0 | W7, answer-only (the P9-I arm and recipe, unchanged and untuned) | none | — |
| A1 | A0 + address loss L_addr with constant weight λ for the whole run | target slot of each fact | none |
| A2 | Phase 1: L_addr only, for U_pre updates (query projection and keys train; values, output projection and gate frozen). Phase 2: answer loss only for the remaining updates, everything trainable, **L_addr removed**; the AdamW moments are reset at the switch | target slot, phase 1 only | none |
| A4 | Answer-only. The read is softmax(a/0.2) over the **top-k(t)** slots, with k(t) = max(8, round(k_0 · (8/k_0)^{t/T_A})) for t < T_A and k = 8 from T_A on; T_A = U/2 at Stage 1 | none | none |
| A5-C | Answer-only + centred queries: z′ = z − m, q = z′/‖z′‖, with m an exponential moving average of the batch mean of z (decay 0.99, no gradient through m); m is initialized as the mean of z at initialization over the first 16 training batches *(lead's choice)* and is frozen at evaluation | none | none (m is a buffer) |
| A5-D | Answer-only + μ·L_div on the batch's normalized queries (no centring) | none | none |
| A1-S | Negative control of A1: the target slot is redrawn uniformly at random for every occurrence (not a function of the fact) | a random slot | none |
| A6 | R1, the oracle-query reference (ADR-0017 §5.3) | oracle at inference (reference only) | — |
| A7 | D7, the parameter-matched dense window control | none | — |

Definitions.

- **Target slot.** A fixed injection s(f) from the trained facts into the N slots, drawn once per cell from a seed (§7). It is an arbitrary label, not an oracle code: nothing about s(f) is visible in the tokens.
- **Address loss.** For an answer site of fact f, L_addr = −log( exp(a_{s(f)}/τ_a) / Σ_{s=1..N} exp(a_s/τ_a) ), averaged over the batch's answer sites, τ_a = 0.2. It uses all N scores and has gradients to W and to the keys only. It is a supervised InfoNCE with fixed proxies. Its floor at τ_a = 0.2, with the query equal to its target key, is 4.09 / 5.47 / 6.84 nats at 4,096 / 16,384 / 65,536 slots, so it never saturates and acts as a permanent key-spreading term. **Both values of the λ grid make L_addr dominant** on the query projection and the keys (5.5 to 285 times the answer loss's gradient in the review's diagnostic). Its gradient norm (4–6) exceeds the clip of 1.0, so in A1 the answer-loss gradients are scaled down by about 0.2; the clip factor is recorded at every update.
- **A1-S target stream.** One uniform draw over the N slots per answer-site occurrence, from a random stream with its own seed (§7), independent of the fact, of the data order and of the initialization.
- **A2's switch.** At the update where L_addr is removed, the AdamW first and second moments of **all** parameters are reset to zero and the bias-correction counters restart. Without the reset, the second moments built by L_addr would hold the query projection and the keys nearly still (mean step 0.03–0.72 of a fresh optimizer's in the review's simulation), and "the addresses survived" could mean only that they were not allowed to move. U_pre counts inside the run's updates. No arm gets more updates than another.
- **A4's read.** At t ≥ T_A the read is exactly the standard top-8 read at temperature 0.2, so the curriculum ends at the read it is scored with. k_0 is a fraction of N: the calibrated fraction (1/8 or 1) is used at every size *(lead's choice)*. Reported per record: the soft mass outside the top 8 and the active retrieval work (k(t) value rows per query).
- **Diversity penalty** (A5-D). With q_1…q_128 the normalized, un-centred queries of the 128 answer sites of the update, L_div = log( mean_{i≠j} exp(2·q_i·q_j) ). It uses no fact identity. The review found that every batch holds 128 distinct facts in 128 answer sites, so L_div never repels two occurrences of the same fact; §8.2 still measures same-fact consistency.
- **Hyperparameters fixed by calibration** (§6), one per arm: λ for A1 (A1-S uses A1's λ), U_pre for A2, the fraction k_0/N for A4, μ for A5-D. A5-C has none.
- **Schedules in later stages** are defined in §5.

**What each contrast tests.** A0 against A1: does address supervision make addressing reliable (H19-B). A0 against A2: the same with the supervision removed before the answers are learned (H19-C, mandatory control 3). A0 against A4: does a wide-to-narrow read suffice without labels (H19-D). A0 against A5-C: is the common mode the cause (H19-F). A0 against A5-D: does a diversity penalty suffice (H19-G). A0 against A1-S: does an address-loss gradient of the same magnitude help without fact information (mandatory control 9). A6 and A7: ceilings and the dense alternative on the same draws.

**Arms not in the matrix.**

- **A3 (joint losses with a predefined decay of λ), the human lead's proposed arm, is removed.** The specification auditor recommended it as redundant with A1 and A2: at the measured gradient ratios, λ(t)·L_addr dominates the query projection and the keys until the last 2–20% of the decay, so A3 behaves like A1 and then like A2 with a late switch, and is unlikely to differ in class from either. This is the pre-freeze matrix change the human lead allowed; the matrix stays the smallest credible one.
- **A1-U** (the negative term of L_addr only) is not added (§17, M9).
- **W5**, the identifier-only window, is excluded: it is told the identifier positions. A5-C is the general form of removing the fact-independent window content.
- A label-free query–query contrastive loss is not added: it needs batches with two contexts of the same fact, which changes data access relative to A0.

## 5. Stages, draws and seeds

| Stage | Size (slots / facts) | Arms | Draws × init seeds | Updates | Cells |
|---|---|---|---|---|---|
| 1 | 4,096 / 2,048 | A0, A1, A2, A4, A5-C, A5-D, A1-S | draws 1–8 × 2 | U | 112 |
| 1 | 4,096 / 2,048 | A6, A7 | draws 1–8 × 1 | U | 16 |
| 2 | 16,384 / 8,192 | A0; the arms that pass the Stage 1 gate (at most 2 besides A0, §8.4); A1-S if an address-supervised arm advances | draws 9–12 × 2 | 4U, read at U and 4U | 8 to 32 |
| 2 | 16,384 / 8,192 | A6, A7 | draws 9–12 × 1 | 4U, read at U and 4U | 8 |
| 3 | 65,536 / 32,768 | A0, the single selected arm (if it is not A0), A6, A7; run only if the selected arm has a constant objective (§8.5) | draws 13–14 × 1 | U | 6 or 8 |

Recount: Stage 1 is 7 × 16 + 2 × 8 = **128** cells. Stage 2 is at most (1 + 2 + 1) × 8 + 2 × 4 = **40** cells and at least 16 (A0 alone advances). Stage 3 is at most **8**. Calibration is **22** (§6). At most **198** cells.

- **Draws.** Fourteen new registered data draws and two reserve draws, from sixteen new seed sets (§7). Each draw is a complete, independent data set: facts, clusters, templates, training stream, calibration stream, Panels A and B, held-out template panels, unseen-fact control. **Stage 1 uses draws 1–8, Stage 2 draws 9–12, Stage 3 draws 13–14.** No Stage 1 draw enters Stage 2 or 3, and no panel used for the Stage 1 gate enters a later class. All draws are generated, hashed and checked by G1 at freeze time, before any model sees them (§9). The P9-I registered draw and all rehearsal draws are historical only and enter no rule.
- **Pairing.** Within a draw and seed, every arm sees the same data, the same batch order and the same initialization of the shared parameters.
- **Why 8 × 2.** Sixteen cells per arm let the study separate between-draw from within-draw variation and estimate a failure rate. The P9-I diagnostics found outcomes clustered by draw, so the 16 cells are worth about 8 draws. Counting a draw as a success when both of its cells succeed, 8 of 8 draws gives a one-sided 95% lower bound of 0.69 on the per-draw success probability and 7 of 8 gives 0.53. The figures 0.83 and 0.74 for 16 and 15 of 16 cells would hold only if cells were independent, which the diagnostics contradict. **The study states the per-draw bound and claims no more.** At Stage 2, 4 of 4 draws gives 0.47.
- **Stage 2 runs 4U updates** so that one training gives a readout at U (matched updates with Stage 1) and at 4U (matched exposures per fact with Stage 1: 512). **In Stage 2 every schedule is expressed in exposures per fact:** A2's U_pre and A4's T_A are multiplied by 4, so the 4U readout reproduces Stage 1's protocol in every respect at matched exposure. **The 4U readout decides the Stage 2 class for every arm.** The U readout is a valid matched-update run only for arms with a constant objective (A0, A1, A1-S, A5-C, A5-D, A6, A7); for them it is printed as ALSO AT MATCHED UPDATES when the arm is RELIABLE there too. For A2 and A4 the U readout is printed as **MID-SCHEDULE (not a matched-update run)** and enters no rule; A4 is scored at that readout with its standard top-8 read.
- **Stage 3 runs U updates only** (32 exposures per fact). A matched-exposure run at that size does not fit the budget. Stage 3 is a probe: **it can only be positive or uninformative** (§8.5). **It runs only if the selected arm has a constant objective (A0, A1, A5-C or A5-D).** The schedules of A2 and A4, expressed in exposures per fact, do not fit inside U updates at this size (U_pre alone would be 16,384 to 32,768 updates), and no schedule is ever defined in updates at Stage 3. If the selected arm is A2 or A4, Stage 3 is not run and prints NOT RUN — SCHEDULED ARM.

## 6. Budget of updates and calibration

- **U = 8,192**, the value calibrated and audited in P9-I for the oracle rungs. It is not re-tuned.
- **A0 is untuned by design.** It is the registered P9-I recipe. Every arm-against-A0 contrast therefore compares an arm at its better of two settings with an untuned baseline; this is stated wherever a contrast is reported.
- **Calibration** (before the freeze, designated calibration draws only): at 4,096 slots, two calibration draws (rehearsal seed sets 3 and 4, on which no model has been trained or evaluated; their generator has been exercised by unit tests and by a G1 timing script), one initialization seed, each arm at each value of its grid:

  | Arm | Grid |
  |---|---|
  | A1 | λ ∈ {0.1, 1.0} |
  | A2 | U_pre ∈ {1,024, 2,048} |
  | A4 | k_0 ∈ {N/8, N} (512 or 4,096 slots at this size) *(lead's choice)* |
  | A5-D | μ ∈ {0.1, 1.0} |

  16 cells. A0, A6 and A7 are run on the same two draws as a check of the pipeline (3 × 2 = 6 cells). **22 cells in all.**
- **Rule.** The value with the higher minimum accuracy over the two draws, measured on each draw's calibration stream. A tie, or a difference below 0.02, goes to the secondary criterion: the earlier median, over the two draws, of the time to first success (§8.7; a cell that never succeeds counts as later than any that does). If that is also tied, the first value listed. With near-binary accuracy, ties on the first criterion are expected to be common.
- Nothing else may be changed after calibration. Bracketed and *(lead's choice)* numbers in this text are fixed before calibration and are not revisited after it.
- Calibration accuracies are reported as calibration, never as results.

## 7. Seeds and data identities

- **Registered data seed sets:** `p9ii-draw-1` … `p9ii-draw-14`, base seeds 190001, 190101, …, 191301. **Reserve sets:** `p9ii-reserve-1` and `p9ii-reserve-2`, bases 191401 and 191501 (§9). Layout inside a set, the P9-I registered convention: base + 0…13 are the fourteen data seeds in P9's order, base + 14…16 the Panel A null seeds, base + 17…19 the Panel B null seeds.
- **Initialization seeds** 1901 and 1902. Cells run at one seed (A6, A7, all of Stage 3) use 1901.
- **Target-slot seed** of a cell: base + 40 + j. **A1-S target-stream seed:** base + 60 + j. Here j = initialization seed − 1901 *(lead's choice)*.
- **Calibration:** rehearsal seed sets 3 and 4 of the P9 namespace (179301+, 179401+), initialization seed 1891. **Rehearsal** for time, memory and gates: rehearsal seed set 5 (179501+). **Tests: 910001 upward** (900001 upward is P9-I's test namespace, and the P9-I review trained models on it).
- The implementation asserts that the registered, reserve, calibration, rehearsal and test seed ranges are disjoint from each other and from every seed used by P9 and P9-I, and writes the hash of every stream to a data manifest at freeze time. Seeds 190001 upward, 1891, 1901 and 1902 are unused in the repository and in `experiments/` (review, minor 3).
- Within a draw, training contexts, the calibration stream, Panel A, Panel B and the held-out template panels are disjoint as in ADR-0017 §4. No registered panel is used for calibration, for the probe or for selection.

## 8. Measurements, classes and rules

### 8.1 Recorded during training (every 64 updates, no gradient)

**Probe set.** For the first 256 trained facts in the order of their first appearance in the draw's calibration stream, both of their occurrences in that stream (512 answer sites, 256 probe facts). The calibration stream uses training templates and contexts that are not in training. (The first 512 sites of the stream would hold 475 to 512 distinct facts and almost no repeated fact; the auditor measured it.) Panels A and B stay untouched until the readout. No rule or action during training reads the probe. At the readout the probe set is read once more, for success condition 3 (§8.3).

Recorded at every record:

- probe accuracy (ties counted wrong);
- mean cosine between queries of different facts, effective rank and total variance, all on the **un-centred** normalized query z/‖z‖ for every arm (A5-C also reports its centred version, descriptively);
- number of distinct top-1 slots and the largest top-1 share; share of facts with a private slot (in the top 8 of exactly one probe fact); address stability between the two occurrences of a fact;
- for arms with a target slot, top-1 and top-8 recall of s(f) and the mean score a_{s(f)};
- mean cosine between each query and its top-1 key;
- gradient norms before clipping, the clip factor, and actual parameter movement since the previous record, for the query projection, keys, values and output projection;
- the answer loss and, where present, L_addr and L_div;
- the fact-independent share ‖mean z‖² / E‖z‖² on the probe, and the share of centred query variance explained by (template, record index) groups;
- for A4, k(t) and the soft mass outside the top 8.

Definitions, for every arm, **slot-based** (the mean cosine enters none of them):

- **Collapse onset:** the first record at which the number of distinct top-1 slots on the probe is ≤ 32 *(lead's choice)*.
- **Escape:** the first later record from which, to the end, the slot part of success condition 3 holds (distinct top-1 ≥ 0.50 × probe facts and largest top-1 share ≤ 0.02).
- **Separated** (for cells with no collapse onset): the same condition holds at the readout. (An untrained W7 query has 0.33 × probe facts and largest share 0.039 in the review's measurement, so a lower threshold would call an unlearned query separated.)
- **Reported beside them, in no rule:** the cosine onset (the first record with mean cosine ≥ 0.9 on the un-centred queries) and the cosine escape (the first later record from which, to the end, it is ≤ 0.5).
- Four categories, reported for every cell and never merged: **never collapsed and separated**; **never collapsed, not separated**; **collapsed and recovered**; **collapsed and not recovered**.

### 8.2 Recorded at the readout (U; also 4U in Stage 2)

Accuracy on Panels A and B and on the held-out template panels H1/H2; negative log-likelihood over the alphabet; accuracy with the memory disabled and with values permuted; unseen-fact control with the LEAKAGE flag; gate G2 (chance interval) on the no-memory backbone; address stability (share of facts whose top-1 slot is the same on Panels A and B); same-fact consistency (mean cosine between the Panel A and Panel B queries of the same fact); distinct selected slots; on the probe set, the number of distinct top-1 slots and the largest top-1 share; the mean query cosine on the un-centred queries (recorded and reported for every arm; not a condition).

**LM capability:** for every learned arm, A6 and A7, the next-byte loss on the backbone's 2,048 corpus rows with the addition active, reading at its fixed positions as in training, and the same loss for the frozen backbone.

**Cost (control 4):** CPU seconds, peak memory, and active retrieval work (key scores computed and value rows read per query). Analytical FLOPs and measured CPU seconds per update are reported separately for L_addr (N-way softmax and all-key backward), for A4's top-k(t) read, and for L_div (128² pairs). No efficiency claim is made from any of these.

### 8.3 Cell success

A cell of a learned arm **succeeds** at a readout if all five conditions hold (conditions 1, 2 and 4 on both Panels A and B):

1. accuracy ≥ 0.90 × the accuracy of A6 on the same draw, size and readout (and A6 ≥ 0.90, else the draw is NOT_EVALUATED at that size);
2. accuracy with values permuted and with the memory disabled is inside the G2 interval;
3. at the readout, on the probe set, the number of distinct top-1 slots is ≥ 0.50 × the number of probe facts **and** the largest top-1 share is ≤ 0.02 *(lead's choice; for reference, in P9-I the collapsed arms had 1–6 distinct top-1 slots, and the partial BB arm 1,233 of 2,048 with largest share 0.006)*. With the probe of §8.1 this is at least 128 distinct top-1 slots and no slot top-1 for more than 10 of the 512 sites. The condition is the same for every arm, with no per-arm exception. The mean cosine is not a condition;
4. accuracy on H1 and H2 ≥ 0.90 × the cell's own Panel A accuracy (the address generalizes to held-out contexts). This condition and its number were fixed in revision 1, before the review's measurement was seen. The review then measured, on one exploratory escaped model, H1/A 0.982 and H2/A 0.938: the condition is reachable and the margin is small. For A5-C the frozen m is a training-template mean. The condition is not changed;
5. the cell has no LEAKAGE flag.

A cell that is evaluated and does not succeed has **failed**.

### 8.4 Arm class at a size (learned arms A0, A1, A2, A4, A5-C, A5-D and A1-S; first match wins)

| Order | Class | Rule |
|---|---|---|
| 1 | NOT_EVALUATED | fewer than 14 evaluated cells at Stage 1 (more than one draw NOT_EVALUATED); fewer than 7 evaluated cells at Stage 2 (any draw NOT_EVALUATED) *(lead's choice)* |
| 2 | RELIABLE | at most one failed cell among the evaluated cells, and the arm does not carry LM CAPABILITY REDUCED at that size |
| 3 | UNRELIABLE | at least 4 cells succeed at Stage 1 (at least 2 at Stage 2), not row 2 |
| 4 | FAILS | otherwise |

Revision 1's clause "every evaluated draw has at least one success" is removed: it is implied by row 2.

An arm that meets row 2's count but carries LM CAPABILITY REDUCED is printed as **UNRELIABLE (LM CAPABILITY REDUCED)**.

**LM capability.** Three parts.

- (a) **The pretrained model itself:** G5. The backbone's tensors are hash-identical before and after training.
- (b) **The system with the memory active, relative to the oracle reference.** For each cell, r = (next-byte loss with the addition active − frozen backbone's) / frozen backbone's, on the backbone's 2,048 corpus rows. A cell is flagged if r > r(A6, same draw and size) + 0.05 *(lead's choice)*. An arm flagged in more than one cell at a size prints **LM CAPABILITY REDUCED** there: it is not RELIABLE, does not advance and cannot be carried forward. r is printed for every arm and for A6.
- (c) The absolute rise is printed beside it for every arm. In the review's measurement A6 itself raised the loss by 13.6–14.7%, an escaped W7 by 13.4% and a collapsed W7 by 5.05%. The criterion therefore measures damage beyond what any memory read at the fixed positions causes, which is a property of this testbed, and says nothing about a deployed system (§13).

**Paired comparisons with A0 (fixed now).** For each learned arm X ≠ A0 at a size and readout, let d(X) = (cells where X succeeds and A0 fails) − (cells where A0 succeeds and X fails), over the paired cells (same draw and initialization seed).

| Order | Label | Rule |
|---|---|---|
| 1 | IMPROVES ON A0 | d(X) ≥ 4 *(lead's choice)* and X has more successes than A0 |
| 2 | HARMS | d(X) ≤ −4 |
| 3 | NOT DISTINGUISHED FROM A0 | otherwise |

The exact two-sided sign-test p-value on the discordant pairs is printed beside d(X), descriptively. The same number 4 is used at Stage 1 (16 pairs) and at Stage 2 (8 pairs).

The paired difference d(A2 against A1) on the same draw and seed is printed at each size, descriptively, as the effect of removing the address supervision.

**Negative control.** A1-S is read only through the paired rule. **NEGATIVE CONTROL FAILED** is printed at a size if A1-S IMPROVES ON A0 there, or if A1-S is RELIABLE there. A1-S being UNRELIABLE while NOT DISTINGUISHED FROM A0 is not a failed control. Where NEGATIVE CONTROL FAILED is printed, the classes of A1 and A2 at that size are printed but not interpreted as fact-specific supervision, and A1 and A2 are skipped in the outcome rows and in the carry-forward order at that size; if it is printed at 4,096, they do not advance to Stage 2.

**Stage 1 gate.** Stage 2 is run if at least one arm is eligible to advance (RELIABLE at Stage 1, not A1-S, and not skipped because NEGATIVE CONTROL FAILED). A0 runs at Stage 2 whenever Stage 2 is run. Besides A0, an arm goes to Stage 2 only if it is RELIABLE at Stage 1; if more than two are, the two are taken in this order: A5-C, A5-D, A4 (no fact identity in training), then A2 (supervision removed), then A1. If A1 or A2 advances, A1-S runs at Stage 2 with it. A1-S never advances on its own account.

**Stage 2 class** is decided at 4U for every arm. For constant-objective arms the class at U is also printed (ALSO AT MATCHED UPDATES when RELIABLE there). For A2 and A4 the U readout is MID-SCHEDULE and has no class.

**Annotations per arm and size.**

- The count of cells in each of the four categories of §8.1; the median escape update.
- **SUPERVISION-DEPENDENT** (A2): in more than half of the cells, the probe accuracy at the readout is lower by more than 0.10 than its maximum over the 512 updates before the removal of L_addr *(lead's choice)*, **or** the cell's status after the removal is "collapsed and not recovered". In A2 the answer path is frozen before the removal, so probe accuracy there is at chance and the first clause cannot fire: **for A2 only the collapse clause can fire.**
- **ADDRESSES RE-MAPPED** (A2, descriptive): top-8 recall of s(f) falls by more than 0.10 between the removal and the readout while the cell succeeds. It is not a defect.
- For A2, the movement of the query projection and the keys after the removal, relative to A0's movement over the same updates.
- **ADDRESS RECALL** (A1, A2): the median over cells of top-8 recall of s(f) on Panels A and B ≥ 0.90 *(lead's choice)*. **ADDRESS STABLE** (every learned arm): the median over cells of the share of facts with the same top-1 slot on Panels A and B ≥ 0.80 *(lead's choice; an escaped exploratory W7 had 0.89)*. Both are printed per arm and size, enter no class, and are carried with the interface.
- **DENSE COMPARISON**, for RELIABLE arms, paired by draw, first match wins: **BEATS DENSE** if the median over draws of accuracy(arm)/accuracy(A7) on the same draw is ≥ 1.10; **DENSE AT CEILING** if the median accuracy of A7 is above 0.909, where 1.10 cannot be reached and the comparison is not informative; **DENSE SUFFICES** otherwise. The per-draw differences and the number of draws on which the arm is higher are printed. Every label speaks about this task and this budget only.

### 8.5 Stage 3 (probe)

Runs only if an arm is RELIABLE at 16,384, the selected arm has a constant objective (A0, A1, A5-C or A5-D), and the budget condition of §10 holds. If the selected arm is A2 or A4, Stage 3 is not run and prints NOT RUN — SCHEDULED ARM; no later arm in the order is substituted. The selected arm is the first RELIABLE arm at 16,384 in the carry-forward order of §8.6. Its label is **SCALE PROBE POSITIVE** if both cells succeed and **SCALE PROBE UNINFORMATIVE** otherwise (the counts of successes are printed). With 32 exposures per fact a non-positive result is exposure-limited and is not evidence against scaling: the probe can only be positive or uninformative. A positive is two cells on two draws and supports no reliability statement.

### 8.6 Study outcome

**Stage status.** Stage 1's outcome is decided from Stage 1 alone and stands whatever happens later. Stages 2 and 3 each get their own status: COMPLETE, NOT RUN — BUDGET, NOT RUN — NO ARM PASSED, NOT RUN — SCHEDULED ARM (Stage 3 only), INCOMPLETE or NOT_EVALUATED. The status is part of the printed outcome.

**Outcome (first match wins).**

| Order | Outcome | Rule |
|---|---|---|
| 1 | ENGINEERING_FAIL / INCOMPLETE / NOT_INTERPRETED | at Stage 1, as ADR-0017 §8.6 and §I.9: a G4 defect; a missing or failed-to-run Stage 1 cell; a failed gate |
| 2 | INCONCLUSIVE | Stage 1 is NOT_EVALUATED; or NEGATIVE CONTROL FAILED at 4,096 and no label-free arm (A0, A4, A5-C, A5-D) is RELIABLE at 4,096 |
| 3 | ANSWER-ONLY RELIABLE | A0 is RELIABLE at 4,096. The collapse of P9-I's registered draw is not a reliability failure on these draws. H19-A is not supported. Other arms are reported by their paired comparison with A0 and by median escape update; none is "supported" unless it IMPROVES ON A0 at 16,384 |
| 4 | ADDRESSING-RELIABLE | Stage 2 is COMPLETE and some learned arm other than A0 and A1-S is RELIABLE at 4,096 and at 16,384 (4U). The row does not require IMPROVES ON A0; the paired label is printed inside the outcome label and the hypothesis reading follows the paired rule |
| 5 | ADDRESSING-RELIABLE AT 4,096 ONLY | Stage 2 is COMPLETE, some learned arm other than A0 and A1-S is RELIABLE at 4,096, none at 16,384 |
| 6 | ADDRESSING-RELIABLE AT 4,096; 16,384 \<status\> | some learned arm other than A0 and A1-S is RELIABLE at 4,096 and Stage 2 is not COMPLETE; the status is printed in the label and the outcome is not read as a failure to scale |
| 7 | ADDRESSING-UNRELIABLE | no learned arm is RELIABLE at 4,096, at least one other than A1-S is UNRELIABLE |
| 8 | ADDRESSING-FAILS | every learned arm other than A1-S FAILS at 4,096 |

- **Labels carry the supervision.** Every outcome of rows 3 to 6 names its arm, the arm's paired label against A0, and its supervision class in the label itself: **(LABEL-FREE)** if the arm is A0, A4, A5-C or A5-D; **(ADDRESS-SUPERVISED IN TRAINING)** if it is A1 or A2. Summaries must not shorten it. Row 3 also prints the Stage 2 status and A0's Stage 2 class.
- **Hypothesis readings, fixed now.** Read at 4,096 (Stage 1); in the case of row 3, at 16,384 (4U).
  - H19-A is supported if, at Stage 1, A0 has collapse onset (slot-based, §8.1) within 256 updates in at least 12 of 16 cells, **and** in at least 12 of 16 cells the ratio ‖∇wq‖ / ‖∇wo‖ of the answer loss, averaged over updates 64–1,024, is ≤ 0.01 *(lead's choice)*, **and** A0 is not RELIABLE.
  - H19-B is supported if A1 is RELIABLE, IMPROVES ON A0, and NEGATIVE CONTROL FAILED is not printed.
  - H19-C: A2 is RELIABLE, IMPROVES ON A0, NEGATIVE CONTROL FAILED is not printed, and A2 is not SUPERVISION-DEPENDENT.
  - H19-D: A4 is RELIABLE and IMPROVES ON A0.
  - H19-F: A5-C is RELIABLE and IMPROVES ON A0.
  - H19-G: A5-D is RELIABLE and IMPROVES ON A0.
  - H19-E, per arm X: supported if X is RELIABLE (which leaves no draw with both cells failed); not supported otherwise. For A0 the clustering test of §8.7 is the primary evidence.
  - Each of B, C, D, F, G is **"not supported"** otherwise, and **CONTRADICTED** if its arm HARMS.
- **The interface carried forward** is the first RELIABLE arm at 16,384 (4U) in the order **A0**, then A5-C, A5-D, A4, then A2, then A1, with all its annotations, and only if it does not carry LM CAPABILITY REDUCED. If the outcome is row 7 or 8, the recommendation is to change the retrieval architecture.

### 8.7 Draw-sensitivity estimands (descriptive, fixed now), per arm and size

- the draws × seeds success table;
- the counts of draws with 2/2, 1/2 and 0/2 successes;
- the within-draw discordance rate (draws at 1/2 over evaluated draws);
- an exact permutation test of seed exchangeability within draws (are failures clustered by draw?);
- the failure rate, with its per-draw Clopper–Pearson interval;
- the escape update per cell, with never-escaped cells censored at the readout; its median; the between-draw and within-draw mean squares of log escape update (one-way ANOVA, 2 seeds per draw, uncensored cells only, with the censored count);
- time to first success: the first record with probe accuracy ≥ 0.90 × A6's readout accuracy on the same draw and size;
- **sustained success:** after the first success, no later record falls below that line by more than 0.05 *(lead's choice)*. Its frequency is printed per arm.

## 9. Gates

- **G1** (generator, per draw). All fourteen registered draws and both reserve draws are generated and G1-checked at the freeze, before any model sees them. G1 runs ten independence streams per draw at a Bonferroni-controlled 0.001 each, so a sound generator fails about 1% of draws and about 13% of runs of fourteen draws. Therefore: a registered draw that fails G1 is replaced by the next unused reserve set, `p9ii-reserve-1` then `p9ii-reserve-2`, in that fixed order, taking the failed draw's place and stage. The replacement is recorded in the freeze. No other replacement is allowed. If a reserve draw fails G1, or more than two draws need replacing, nothing is run and the matter returns to the human lead. Generating a draw and checking it with G1 is not an observation of a registered seed by a model.
- **G2** (chance, per draw and size).
- **G4** (determinism, checkpoint restoration, gradient reach for every arm on contexts the cell covers). The address loss reaches the query projection and keys and nothing else. A0's forward and one training step are bit-identical to P9-I's W7. G4 adds:
  - k(t) at updates 0, 1, T_A/2 and T_A equals the formula, and from T_A the read equals the standard top-8 read bit for bit;
  - A2 switches objective and trainable set at U_pre, and all AdamW moments and bias-correction counters are reset there;
  - A5-C's m receives no gradient, is restored from checkpoints and is frozen at evaluation;
  - A1-S's target stream is reproducible from its seed and independent of the fact;
  - L_addr uses all N scores, checked against a direct computation at 65,536; A4's read at k = N uses all N scores, checked against a direct computation at 16,384 (A4 never runs at 65,536).
- **G5 (backbone identity):** the sha256 of every backbone tensor after training equals the frozen backbone's; with the addition disabled, each arm's logits on the backbone's corpus rows equal the frozen backbone's bit for bit.
- **G6:** the forward of the learned arms has no fact-identity input; with token inputs fixed, permuting s, the R1 codes and the fact-index tables leaves every learned arm's logits bit-identical.
- The gates stage runs at real size on rehearsal seeds before the freeze and again on registered seeds before training; a failed gate stops the run.
- **All gate outputs are written to the run directory and committed** (the P9-I review found a comparison output that was not).
- **Fixed launch scripts.** Each registered stage (gates, Stage 1, the Stage 1 gate, Stage 2, the Stage 3 gate, Stage 3, analysis, report) is launched by one script that takes no free arguments, committed before the freeze, covered by the freeze hash, and used for every registered stage. No registered stage is launched by a typed command. The reason is on record: in P9-I the lead mistyped launch commands three times.

## 10. Resources

Rates measured in P9-I's registered run (attempt 2, six single-thread workers; review script c5): W7 0.0098 / 0.0141 / 0.0531 s per update at 4,096 / 16,384 / 65,536 slots; the slowest memory or dense arm of P9-I (its four-head query, not an arm of this study) 0.0112 / 0.0195 / 0.0619. Peak memory 0.63 GiB in training, 1.49 GiB in P9-I's rehearsal evaluation.

**Projection from those rates** (training only; makespan with six workers = rounds × time per cell):

| Block | Cells | Updates | s per cell (W7 / slowest) | Summed hours (W7 / slowest) | Rounds | Makespan hours (W7 / slowest) |
|---|---|---|---|---|---|---|
| Calibration | 22 | 8,192 | 80 / 92 | 0.49 / 0.56 | 4 | 0.09 / 0.10 |
| Stage 1 | 128 | 8,192 | 80 / 92 | 2.85 / 3.26 | 22 | 0.49 / 0.56 |
| Stage 2, largest | 40 | 32,768 | 462 / 639 | 5.13 / 7.10 | 7 | 0.90 / 1.24 |
| Stage 2, smallest | 16 | 32,768 | 462 / 639 | 2.05 / 2.84 | 3 | 0.39 / 0.53 |
| Stage 3 | 8 | 8,192 | 435 / 507 | 0.97 / 1.13 | 2 | 0.24 / 0.28 |

Not in the table, to be measured by the rehearsal: the probes every 64 updates (about 2% in the review's estimate), L_addr's N-way softmax and all-key backward, A4's top-k(t) read, L_div, and evaluation (P9-I: 98 s for 57 cells; by cell count about 0.06 h for Stage 1, 0.04 h for the two readouts of the largest Stage 2, 0.01 h for Stage 3). Data generation and G1 cost about 18 s per draw in P9-I.

Stage 2 makespan by configuration (cells = 8 × learned arms + 8): 16 cells 0.39 / 0.53 h; 24 cells 0.51 / 0.71 h; 32 cells 0.77 / 1.07 h; 40 cells 0.90 / 1.24 h.

**Rehearsal.** Every distinct (arm, size, phase) of the matrix for 256 updates *(lead's choice)* plus one full evaluation, on rehearsal set 5, six workers. A2, A4 and A1-S are not rehearsed at 65,536, where they never run. Phases: A2 before and after its switch; A4 at k_0, at the midpoint of its schedule and at k = 8. A stage's projection = measured s per update × planned updates (A4's annealing phase at its most expensive measured rate) + measured evaluation, arranged in rounds of six. The projection for every possible Stage 2 configuration is recorded at the freeze, so the Stage 1 gate reads a table and computes nothing new.

**Budget A (initial registered phase): calibration + rehearsal + Stage 1 ≤ 4 hours charged.** This is the human lead's "maximum 4 hours charged execution for the initial registered phase". Projection at the slowest P9-I rates: calibration 0.10 h, rehearsal and gates about 0.1 h, generation and G1 of sixteen draws about 0.1 h, Stage 1 0.56 h + 0.06 h evaluation: **about 0.9 h**. Stage 1 starts only if twice its rehearsed projection is within what remains of Budget A after calibration and rehearsal (projected: 2 × 0.62 = 1.24 h against about 3.7 h). If it is not, nothing registered is run and the matter returns to the human lead.

**Budget B (progression): Stage 2 + Stage 3 ≤ 3 hours charged** *(lead's choice)*. This is the human lead's "separately defined progression gate and resource budget". Budget A's unused time does not move to Budget B.

- Stage 2 is run only if twice its rehearsed projection, for the configuration the Stage 1 gate selects, is within Budget B. **There is no reduced Stage 2:** no draw, arm or update is dropped to make it fit. If it does not fit, Stage 2 and Stage 3 are not run, their status is NOT RUN — BUDGET, and the outcome says so (§8.6 row 6).
- Stage 3 is run only if twice its rehearsed projection is within what remains of Budget B after the time Stage 2 actually charged. If not, it is not run: NOT RUN — BUDGET. This dependency on how many arms passed is mechanical and fixed here.
- Projection: the largest Stage 2 (40 cells) is 0.90 h (W7 rates) to 1.24 h (slowest rates) of training plus about 0.04 h of evaluation, so twice the projection is **1.9 to 2.6 h against 3 h**. At the slowest rates this leaves about 17% for everything the table omits. Stage 3 needs 2 × 0.29 = 0.6 h of what remains (projected 1.7 h or more).

**Caps.** 3 GiB per worker; 24 GiB aggregate; each stage's time cap is twice its rehearsed projection; memory must show 2× headroom in the rehearsal. A running stage that reaches its cap is stopped (§14). No timing-sensitive comparison is made between cells; CPU seconds are reported descriptively. Revision 1's cut rule (drop Stage 3, then run Stage 2 on two draws) is removed.

No cloud, no downloads, no new dependency, no SSD work.

## 11. Implementation

- New package `studies/p9ii/`, importing `studies.p9i` and `studies.p9` without editing them; config `configs/p9ii_addressing.toml`; tests `tests/test_p9ii_*.py`; launch scripts under `studies/p9ii/launch/`. Records carry the study code P9II.
- The implementation audit covers every imported path used, including the full-N score path at 65,536, which the chunked top-64 scorer of `studies/p9` does not provide. The gates stage must run at real size on rehearsal seeds before the freeze (the lesson of P9-I attempt 1), and analysis and report must be exercised on synthetic records of the full registry, including missing cells, failed gates, non-finite values, every stage status of §8.6 and a replaced draw.
- **The consolidation of P8 and P9-I into `main` must be complete before implementation starts** (§16).

## 12. Order of work

1. Confirmation review by the auditor (done on revision 3: READY after R1–R7, applied here). Any passage changed after this revision is re-checked by the auditor.
2. Consolidation of P8 and P9-I into `main` complete.
3. Implementation with tests and the fixed launch scripts.
4. Calibration (§6); audited.
5. Rehearsal of every (arm, size, phase) for time, memory and correctness, gates at real size on rehearsal seeds; implementation audit.
6. Freeze of code, configuration, launch scripts, seeds, thresholds, calibration record, stage projections and data identities; generation and G1 of all registered and reserve draws, with any replacement recorded.
7. The registered run, once, by the launch scripts: Stage 1; the Stage 1 gate; Stage 2; the Stage 3 gate; Stage 3.
8. Independent recomputation from raw records by the auditor; report.

## 13. What this study cannot establish

- Anything about memory capacity, useful-capacity scaling, locality or incremental learning. More slots in use is not more capacity.
- That a reliable arm would be reliable on natural language, on another backbone, with another interface than W7, or at 65,536 slots. Stage 3 is a probe at 32 exposures per fact and can only be positive or uninformative.
- That address supervision is available in a real system: a target slot per fact is a training label this task provides. A supervised arm's success says nothing about learning addresses without labels.
- That W7 is a general interface: it is told the record length. The memory is also told where the answer site is (it reads only at positions 8r + 6), a task-structure input of the same kind. A known answer position does not exist in real text. **The memory is told the answer position, and the LM-capability criterion of §8.4 is measured under that condition: it says nothing about a deployed system.**
- That matched exposure at 16,384 is matched optimization: under AdamW a row updated once in K steps moves about √K learning rates per exposure (ADR-0017 §5.5).
- That a tuned arm beats a tuned baseline: A0 is untuned by design.
- A success probability above the per-draw bounds stated in §5.
- Any efficiency claim: work counts and CPU seconds are descriptive.
- A failure of the ArborLM concept, whatever the outcome.

## 14. Stop rules

- A failed gate, or any difference between the frozen and the running code, configuration, launch scripts or data identities, stops the run.
- A stage whose doubled projection does not fit its budget is not started (NOT RUN — BUDGET). A running stage that reaches its cap is stopped and is INCOMPLETE. In both cases the completed stages stand.
- No re-run with changed settings. A second attempt after an engineering stop needs the human lead's decision, as in P9-I.

## 15. Decisions reserved for the human lead

Any change of thresholds, arms or budget after the freeze; a second attempt; Stages 2 and 3 if they are not run for budget; the use of this study's outcome in P10; merge; publication; ADR-0012.

## 16. Approval record

To be completed after the confirmation review.

The human lead's words, verbatim:

(a) "my bad first finish p9-ii autoaprove your adr the proceed with p10 with the details above, in fact you could start preparing everything needed for p10 while you work in p9 since I know you're capable" and "but p10 will determinate if the hipótesis stands"

(b) "p9-II and p10 can run in parallel, but we must first commit p9 and then adjust any implementation as p10-I if needed once p10 is done running"

(c) "we can change it to  p10 can be self approve but p10-I need my review" (this concerns P10 and is recorded here only for completeness of the delegation history)

The lead's conditions for using the delegation:

1. the specification review ends with no open blocker or major;
2. the implementation audit is clean before the freeze;
3. the rehearsal shows 2× headroom;
4. nothing changes after calibration except the calibrated values;
5. no registered seed has been observed.

The consolidation of P8 and P9-I into `main` must be complete before implementation starts. The lead reads Budget B (§10) as covered by the delegation and has told the human lead so.

### Lead's approval for implementation, calibration and rehearsal — 2026-11-15 (UTC)

- The specification review ended NOT READY (3 blockers, 9 majors, 17 minors) on revision 1; revisions 2 and 3 applied it; the confirmation (`docs/reviews/adr-0019-design-2026-11-15/CONFIRM.md`) found no open blocker and required edits R1–R7, which revision 4 applies with the auditor's text and values. Two places were not verbatim in the drafter's revision 4 and are settled here: §13 now says the language-model criterion "says nothing about a deployed system", matching the auditor's §8.4 text; the withdrawn term TESTBED-LIMITED appears only in the history sections. **Condition 1 holds.**
- The consolidation of P8 and P9-I into `main` is complete (`main` at `5877468`, receipt in `docs/reviews/p9i-consolidation-2026-11-15/CONSOLIDATION_RECEIPT.md`); this branch is cut from it.
- **Under the human lead's delegation quoted above, the lead approves ADR-0019 revision 4 for implementation, calibration and rehearsal.** The registered run is approved separately, in a freeze record added to this section, only if conditions 2–5 hold then; otherwise the decision returns to the human lead. A second attempt after an engineering stop is not covered.
- Budget B (3 hours for Stages 2 and 3) is the lead's reading of the human lead's "separately defined progression gate and resource budget"; the human lead was told on 2026-11-15 and has not objected.
- Every run manifest records the operating system, hardware and library versions (the P9-I registered manifests did not, as the consolidation review found).
- This is the lead acting under delegation. It is not Astra validation and not a separate human approval. Astra review: NOT_PERFORMED.

### Freeze record — 2026-11-15 (UTC)

1. **Code.** Registered data were generated at commit `a1685d0`; the freeze commit is the commit that adds this record, `studies/p9ii/freeze/plan.json` and `studies/p9ii/freeze/stage_caps.json`, and changes nothing else under `studies/`, `configs/` or `tests/`. 1,907 tests passing, 4 skipped; ruff and mypy clean.
2. **Changes since the calibration (commit `3d779e1`), and why no computed number differs.** Commit `2e47e16`: budget, driver, analysis, report, diagnostics-recording and evaluation-chunking fixes required by the pre-freeze audit (B1, M1–M7, m3–m15); `model.py` is byte-identical. Commit `a1685d0`: one flag in `studies/p9ii/launch/generate.sh` (below). Evidence (auditor's re-check, `docs/reviews/p9ii-prefreeze-audit-2026-11-15/RECHECK.md`): training is bit-identical between `3d779e1` and `2e47e16` for all nine arms at 4,096 and 16,384 slots; whole evaluation records are bit-identical, chunked or not, at all three sizes; the 22 calibration cells re-score with zero difference; the class rules agree with an independent implementation on 20,000 random tables, the only output differences against the earlier analysis being the intended rule corrections.
3. **Calibration.** `results/p9ii-calibration-2026-11-15/calibration.json`, sha256 `ad5d7ee29ccd3f0be8b9875afdd957f35901e0d80f4babca6917916d0cf552cf`. Selected: λ = 1.0 (A1), U_pre = 2,048 (A2), k_0 = N/8 (A4), μ = 1.0 (A5-D). Confirmed by the auditor from raw records and snapshots. Corrections to the lead's reading: `results/p9ii-calibration-2026-11-15/CORRECTION.md`. **A2 is kept exactly as registered**, although the audit's diagnostics show its moment reset collapses the pretrained addresses; changing an arm after its calibration was seen is not allowed.
4. **Rehearsal 2** (bound to the calibration record): `results/p9ii-rehearsal2-2026-11-15/projection.json`, sha256 `6895b920b3b6869acbf4745cf1e42d249d217d01139cf4b4b058c16c8b162936`. Stage 1 projects to 2,072 s (doubled 4,143 s; Budget A had 13,866 s left). Stage 2 doubled: 2,308–7,038 s without A4, 11,561–14,660 s with A4, against Budget B's 10,800 s. Stage 3 doubled: 631–1,441 s. Peak memory doubled stays within 2.00 GiB per worker.
5. **The lead's statement on A4 and Budget B.** Budget B stays 3 hours. If A4 is among the arms that pass the Stage 1 gate, Stage 2 does not fit with 2× headroom and prints NOT RUN — BUDGET for every arm, as §10 provides; the report will say that the skipped stage comes from the projection rule, which charges A4's whole anneal at its costliest rate and therefore overstates it. The human lead was told on 2026-11-15 that raising Budget B to 4.5 hours would remove this path and had not answered at the freeze; the lead does not raise the cap itself.
6. **Stage caps.** `studies/p9ii/freeze/stage_caps.json`, sha256 `fdc9db79dcf1a3f6a19716828f2e9bfb08591d49cd5003b891e0d4ea286fc88b`, written by `uv run --locked python -m studies.p9ii.stages caps --projection results/p9ii-rehearsal2-2026-11-15/projection.json --gates-wall-seconds 16.5 --analysis-wall-seconds 8.1 --report-wall-seconds 0.1 --out studies/p9ii/freeze/stage_caps.json` (the three times are the auditor's measurements; each of those caps rests on the 60 s floor).
7. **Gates on rehearsal seed set 5 at real size, real backbones:** G1, G2, G4, G5, G6 all passed, no defect (`results/p9ii-rehearsal2-2026-11-15/gates_rehearsal_set5.json`). The registered gates run first in the registered run.
8. **Registered data.** Generated before this commit by `sh studies/p9ii/launch/generate.sh` into `experiments/P9IIP-registered-20261115b`: fourteen registered draws and two reserve draws, **all sixteen passed G1; no reserve substitution**; draw plan sha256 `627263112e5c36c461d1a04e0d16040aebf8a534ce09b9e55bbb8fe1b8eb773d`; the sixteen data-manifest hashes are in `plan.json`. No model has been trained or evaluated on these data.
   - **Generation attempt 1 was refused before generating anything**: the fixed script passed no stage cap and the driver refused all sixteen calls (`results/p9ii-freeze-2026-11-15/GENERATE_ATTEMPT1.md`). The script had never been executed; the fix is one flag. This change was made after the auditor's READY TO FREEZE and is submitted to the auditor's recomputation.
9. **Plan.** `studies/p9ii/freeze/plan.json`, sha256 `b4c057e9739e5f162089eba0f56594461c3b3051f0f7bdd10b9fbaa134fff722`; the driver's own verification accepts it.
10. **Ledgers.** Budget A charged 719 s of 14,400 s at the freeze (gates on rehearsal seeds twice, calibration, rehearsal twice, generation); Budget B 0 s.
11. **Launch, in this order, each as `sh studies/p9ii/launch/<stage>.sh <run-dir> <freeze-commit>`:** `gates`, `stage1`, `stage1_gate`, `stage2`, `stage3_gate`, `stage3`, `analysis`, `report`. `stage1_gate` is launched only after Stage 1 has finished. No registered stage is launched by a typed command, and no stage is re-run with changed settings.

### Decision on the registered run — taken by the lead under delegation, 2026-11-15 (UTC)

The lead's five conditions, checked at the freeze:

1. *The specification review ends with no open blocker or major.* **Holds** (above).
2. *The implementation audit is clean before the freeze.* **Holds:** the audit found one blocker and seven majors in budget, driver and analysis code; all were fixed and re-checked; the re-check's verdict is READY TO FREEZE with three minor notes (n1–n3), which this record answers (launch order stated; measured times listed). One further defect surfaced after that verdict, in a launch script the audit could not execute (item 8); it is fixed and disclosed.
3. *The rehearsal shows 2× headroom.* **Holds** under the registered rule for Stage 1 and for every Stage 2 configuration without A4; a configuration with A4 is not run, by rule (item 5).
4. *Nothing changes after calibration except the calibrated values.* **Holds for every computed number; does not hold literally for the code** (item 2 and the one-flag script fix). No arm, loss, schedule, threshold, seed or rule was changed, and no registered data existed when the fixes were made. As in P9-I, the lead judges the condition met in the sense it was written for (no tuning after observation) and states the literal exception so the human lead can overrule it.
5. *No registered seed has been observed.* **Holds:** the registered data were generated and checked by G1 only; no model has been trained or evaluated on them.

**Decision: the lead approves the single registered run of P9-II as frozen here**, under the human lead's delegation quoted above. It covers no re-run, no second attempt after an engineering stop, no change of budget, and nothing outside this study. The outcome is reported as registered whatever it is. This is not Astra validation and not a separate human approval. Astra review: NOT_PERFORMED.

### Record of the registered run — 2026-11-15 (UTC)

- The single registered run was executed once at freeze commit `d2746d3` (run directory `experiments/P9IIP-registered-20261115b`). Every stage ended COMPLETE; 174 of 174 cells; no cell was re-run.
- Registered outcome as printed and as recomputed by Opus 5.5 from raw records (171 comparisons, 0 disagreements): **ADDRESSING-RELIABLE: A5-D (LABEL-FREE), paired against A0 at 4,096: IMPROVES ON A0; at 16,384: NOT DISTINGUISHED FROM A0**; interface carried forward by the order of §8.6: A0; Stage 3: SCALE PROBE UNINFORMATIVE.
- Records: `results/p9ii-run-2026-11-15/` (`OUTCOME.md` holds the lead's rulings on the audit's findings; no rule, threshold or reading was changed after observation). Review: `docs/reviews/p9ii-results-2026-11-15/REVIEW.md`.
- **The outcome has not been accepted by the human lead.** This entry is a record, not an approval. Astra review: NOT_PERFORMED.

### Human lead's acceptance of the outcome — 2026-11-15 (UTC)

The lead asked: "Do you accept the P9-II outcome as registered? S0 can be implemented and rehearsed without it but cannot be frozen." The human lead answered, verbatim (the sentence also answers two P10 questions, recorded in ADR-0021 and ADR-0022):

> yes I do, yes we can raise to 16 and I approve the package

Recorded by the lead:

- **P9-II is accepted by the human lead as registered: COMPLETE — ADDRESSING-RELIABLE: A5-D (LABEL-FREE), paired against A0 at 4,096: IMPROVES ON A0; at 16,384: NOT DISTINGUISHED FROM A0;** interface carried forward by the registered order: A0; Stage 3: SCALE PROBE UNINFORMATIVE.
- The acceptance is of the outcome as printed and recomputed, with the audit's findings and the lead's rulings in `results/p9ii-run-2026-11-15/OUTCOME.md` attached. It changes no rule, reading or limit of §13, and it is not a claim of a breakthrough.
- Astra review: NOT_PERFORMED. Claude review is not Astra review.

## 17. How revisions 2, 3 and 4 answer the reviews

Review: `docs/reviews/adr-0019-design-2026-11-15/REVIEW.md` (Opus 5.5), verdict NOT READY. Numbers marked *(lead's choice)* in the text are the review's suggested values or the lead's rulings; all are fixed before calibration.

| Finding | Change in revision 2 |
|---|---|
| **B1** absolute readings, A0 path missing | Adopted in full. §8.4: paired rule against A0 on the same draw and seed (IMPROVES ON / HARMS / NOT DISTINGUISHED, threshold 4), NEGATIVE CONTROL FAILED redefined on the paired rule. §8.6: row ANSWER-ONLY RELIABLE; A0 first in the carry-forward order; every hypothesis reading paired; CONTRADICTED added. §2 reworded. |
| **B2** G5 fails by construction; LM criterion missing | Adopted. §3 and §9: G5 checks backbone tensor hashes and memory-disabled logits. §8.2 and §8.4: LM capability measured with the memory active; a cell is flagged when its relative rise exceeds A6's on the same draw and size by more than 0.05 (R1); more than one flagged cell at a size prints LM CAPABILITY REDUCED, and the arm is not RELIABLE and cannot be carried forward; the absolute 5% line and the TESTBED-LIMITED clause of revision 3 are removed (R1). §13: the answer-site position is a task-structure input, and the criterion says nothing about a deployed system. |
| **B3** schedules in U against a 4U stage | Adopted. §5: schedules in exposures per fact at Stage 2; the 4U readout decides the class; the U readout of A2 and A4 is MID-SCHEDULE and enters no rule. Stage 3, which the review's text does not cover, runs only for a constant-objective selected arm (ruling 1). |
| **M1** A5 joins two mechanisms; vacuous diagnostics | Adopted. §4: A5-C (centring only) and A5-D (diversity only); H19-F on A5-C, new H19-G on A5-D. §8.1: cosine on un-centred queries, four categories, (template, record) variance share. Under ruling 2 the categories and success condition 3 are slot-based for every arm and the cosine is reported beside them; the review's "cosine or slots" onset and "cosine and slots" escape are not adopted in that form, because a cosine condition either fails A5-C by construction (un-centred) or is vacuous (centred). |
| **M2** A4 ends at a read that is not top-8 | Adopted in the top-k form. §4: k(t) from k_0 to 8 at temperature 0.2; grid {N/8, N}, a fraction of N used at every size (ruling 6). The temperature-annealing alternative is not adopted, because the lead ruled for the top-k form. |
| **M3** AdamW carry-over; wrong dependence measure; A3 | Adopted. §4: moments reset at the removal of L_addr. §8.4: SUPERVISION-DEPENDENT by probe accuracy or collapse; ADDRESSES RE-MAPPED descriptive; movement relative to A0. **A3 dropped** and the removal recorded in §4. With A3 dropped, only the collapse clause can fire for A2; §8.4 says so (ruling 3). |
| **M4** bounds, estimands, probe accuracy | Adopted. §5: per-draw bounds (0.69, 0.53, 0.47). §8.1: probe accuracy. New §8.7. The clause "every draw has at least one success" is removed. The review's bracketed replacement ("no draw has both of its cells failed") is not added, because it is implied by "at most one failed cell" and would be equally redundant. |
| **M5** later stages reuse the selecting draws | Adopted. §5 and §7: Stage 1 draws 1–8, Stage 2 draws 9–12, Stage 3 draws 13–14, bases 190001 to 191301. |
| **M6** precedence, hidden supervision, denominators, LEAKAGE | Adopted. §8.3 condition 5. §8.4 row 1 and row 2 denominators (14 and 7). §8.6: per-stage status, row 6, labels with (LABEL-FREE) or (ADDRESS-SUPERVISED IN TRAINING). |
| **M7** budget | Adopted with the lead's numbers. §10: Budget A 4 h for calibration, rehearsal and Stage 1; Budget B 3 h for Stages 2 and 3; 2× headroom against what remains; no reduced Stage 2; Stage 3 NOT RUN — BUDGET if it does not fit; the cut rule is removed. The Stage 1 gate advances at most two arms besides A0, so Stage 2 is at most 40 cells (ruling 4). |
| **M8** G1 false failures, G4 coverage, gate outputs, launch | Adopted. §7 and §9: two reserve draws in fixed order; added G4 tests (the λ(t) test is not included, because A3 is dropped); gate outputs committed; fixed launch scripts, with the P9-I reason. |
| **M9** A1-S weak and absent at Stage 2 | Adopted. §5 and §8.4: A1-S runs at Stage 2 whenever a supervised arm advances and is read only against A0. A1-U is not adopted, because the lead ruled against adding it. |
| Minor 1 calibration draws wording | Adopted, §6. |
| Minor 2 test seeds, null-seed layout | Adopted, §7: tests from 910001; the P9-I registered layout stated. |
| Minor 3 seeds 190001+ free | Recorded in §7. No change needed. |
| Minor 4 probe set | Adopted, §8.1: the draw's calibration stream; Panels A and B untouched until the readout. |
| Minor 5 fact-independent share | Adopted, §8.1. |
| Minor 6 L_addr properties | Adopted, §4: floor, dominance at both λ, clip factor recorded. The label-free contrastive variant is not added, as the review recommends. |
| Minor 7 G6 wording | Adopted, §9. |
| Minor 8 calibration ties; untuned A0 | Adopted, §6: secondary criterion earlier median escape update, then the first value listed; A0 untuned by design (§6, §13). |
| Minor 9 dense comparison | Adopted, §8.4: paired by draw, DENSE AT CEILING added, scope statement. The 1.10 threshold is unchanged. |
| Minor 10 Stage 3 | Adopted in the "keep" form, §5, §8.5, §13: a probe that can only be positive or uninformative; the labels NEGATIVE and MIXED are replaced by UNINFORMATIVE. |
| Minor 11 approval record | Adopted as the lead ruled: §16 holds the human lead's words, the lead's five conditions and the placeholder. The statement that the review is neither Astra validation nor human approval is in the header, because the lead fixed the content of §16. |
| Minor 12 H19-A mechanism | Adopted, §8.6: gradient-ratio clause (12 of 16 cells, ratio ≤ 0.01). |
| Minor 13 extra computation | Adopted, §8.2. |
| Minor 14 W5 exclusion | Adopted, §4. |
| Minor 15 H1/H2 condition | Kept as a success condition at 0.90 (lead's ruling); §8.3 records that it was fixed before the review's number and that the measured margin (0.938) is small. Not moved to an annotation. |
| Minor 16 §13 additions | Adopted, §13. |
| Minor 17 bookkeeping | Adopted: A1-S target-stream seed (§7), A5-D batch definition (§4). |

**Confirmation review of revision 3** (`docs/reviews/adr-0019-design-2026-11-15/CONFIRM.md`, Opus 5.5): READY AFTER R1–R7. All seven are applied with the auditor's text and suggested values.

| Finding | Change in revision 4 |
|---|---|
| **R1** (major) the LM criterion is vacuous through TESTBED-LIMITED | Adopted. §8.4 parts (b) and (c) replaced: a cell is flagged when r exceeds A6's r on the same draw and size by more than 0.05. TESTBED-LIMITED is deleted from §8.4, §17 and §18 (§3 never named it). |
| **R2** (major) the escape threshold is below the untrained level | Adopted. §8.1: escape and "separated" use the slot part of success condition 3, held to the end (escape) or at the readout (separated). §6: the calibration tie-break is the time to first success. |
| **R3** (minor) no registered criterion for address recall | Adopted. §8.4 annotations ADDRESS RECALL (0.90) and ADDRESS STABLE (0.80). |
| **R4** (minor) the probe holds few repeated facts | Adopted. §8.1: both occurrences of the first 256 trained facts of the calibration stream. §8.3 states the resulting counts (128 slots; 10 sites). |
| **R5** (minor) the Stage 1 gate when the negative control fails | Adopted. §8.4 Stage 1 gate. |
| **R6** (minor) no direct comparison of A1 and A2 | Adopted. §8.4: d(A2 against A1) printed, descriptive. |
| **R7** (minor) the LM flag is invisible in the class | Adopted. §8.4: UNRELIABLE (LM CAPABILITY REDUCED). |

## 18. The lead's choices on the open points and on the confirmation review (fixed before calibration)

Revision 2 listed ten open points and a set of drafting additions. The lead ruled on each; revision 3 applies the rulings.

| No. | Open point | Ruling *(lead's choice)* | Where |
|---|---|---|---|
| 1 | Schedules in exposures per fact do not fit Stage 3 | Stage 3 runs only if the selected arm has a constant objective (A0, A1, A5-C, A5-D). Otherwise NOT RUN — SCHEDULED ARM. No schedule is ever defined in updates at Stage 3 | §5, §8.5, §8.6 |
| 2 | Success condition 3 and A5-C | Slot-based for every arm, no exception: on the probe set at the readout, distinct top-1 slots ≥ 0.50 × probe facts and largest top-1 share ≤ 0.02. The cosine is recorded and reported, not a condition. Training-time categories are slot-based (onset: ≤ 32 distinct top-1 slots; escape and "separated": condition 3's slot test, as revised by R2); cosine onset and escape are reported beside them | §8.1, §8.2, §8.3 |
| 3 | SUPERVISION-DEPENDENT after dropping A3 | Accepted: for A2 only the collapse clause can fire, and the text says so | §8.4 |
| 4 | Budget B against the largest Stage 2 | Budget B stays 3 hours. The Stage 1 gate advances at most two arms besides A0, so Stage 2 is at most 40 cells | §5, §8.4, §10 |
| 5 | Untested LM-capability threshold | (a) G5 is the criterion for the pretrained model; (b) and (c) as revised by R1: a cell is flagged when its relative next-byte loss rise exceeds A6's rise on the same draw and size by more than 0.05; an arm flagged in more than one cell at a size prints LM CAPABILITY REDUCED and is barred from being carried forward; the absolute rise is printed beside it. The absolute 5% line and TESTBED-LIMITED of revision 3 are withdrawn, because the auditor measured A6 itself at +13.6 to +14.7%. §13 states that the memory is told the answer position | §3, §8.2, §8.4, §13 |
| 6 | k_0 at larger sizes | k_0 is a fraction of N; grid {N/8, N}; the calibrated fraction is used at every size | §4, §6 |
| 7 | Denominators (14 and 7 evaluated cells) | Accepted as drafted. One NOT_EVALUATED draw at Stage 2 makes the arm NOT_EVALUATED there; at Stage 1, 13 of 14 reaches RELIABLE, with a per-draw bound of at most 0.65 | §8.4 |
| 8 | ADDRESSING-RELIABLE without IMPROVES ON A0 | Accepted: the row does not require it; the paired label is printed inside the outcome label and the hypothesis reading follows the paired rule | §8.6 |
| 9 | The review's bracketed replacement for the redundant draw clause | Accepted: not added | §8.4 |
| 10 | Arm-level LM rule (more than one flagged cell) | Accepted; the flag is the relative one of R1 | §8.4 |

Drafting additions accepted by the lead: hypothesis H19-G for A5-D; the seed offsets + 40 and + 60; A1 and A2 skipped in outcome rows, and not advancing, where NEGATIVE CONTROL FAILED is printed; Stage 2 with A0 alone when A0 is the only RELIABLE arm; the label DENSE AT CEILING; SCALE PROBE UNINFORMATIVE for Stage 3; the statement in the header that the review is neither Astra validation nor human approval.

**Values taken on the confirmation review.** The lead takes every bracketed value as the auditor suggests:

- R1: margin 0.05 over A6's rise on the same draw and size; TESTBED-LIMITED deleted.
- R3: 0.90 for ADDRESS RECALL and 0.80 for ADDRESS STABLE.
- R4: the probe is both occurrences of the first 256 facts of each draw's calibration stream.
- R2, R5, R6, R7: as the auditor wrote them.

**The drafter's three readings of the rulings, as they now stand.**

1. *Slot-based categories.* Collapse onset is ≤ 32 distinct top-1 slots on the probe. Escape is condition 3's slot test (≥ 0.50 × probe facts and largest share ≤ 0.02) held from a record to the end; "separated" is the same test at the readout. The revision-3 escape line of 0.25 × probe facts is withdrawn (R2). The cosine onset and escape are reported beside them and enter no rule. H19-A's "collapse onset within 256 updates" and the collapse clause of SUPERVISION-DEPENDENT use these definitions. The calibration tie-break no longer uses the escape update: it is the time to first success.
2. *An LM-flagged arm.* An arm that prints LM CAPABILITY REDUCED at a size is not RELIABLE there, does not advance and is not carried forward; the flag is the relative one of R1, and the class is printed as UNRELIABLE (LM CAPABILITY REDUCED) when the count of row 2 is met (R7).
3. *No substitution at Stage 3.* If the first RELIABLE arm in the carry-forward order is A2 or A4, Stage 3 prints NOT RUN — SCHEDULED ARM and no later arm is substituted.


Astra review: NOT_PERFORMED. A Claude review is not an Astra review, and this document is not a human approval.
