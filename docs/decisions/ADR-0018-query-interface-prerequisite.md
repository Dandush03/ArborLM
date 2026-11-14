# ADR-0018 — The query interface: can the model tell its memory what it needs? (P9-I)

- **Status: DESIGN REVISION 1 — NOT APPROVED. No implementation, calibration or execution is authorized by this text.**
- **Date:** 2026-11-14
- **Origin.** ADR-0017 revision 3 is CALIBRATION BLOCKED by the human lead's direction of 2026-11-14 (ADR-0017 §15.2): "we may first need to solve a more fundamental problem: How does the language model reliably communicate what information it needs to its memory?", and "correct the scientific design if the findings hold, and only then authorize a new execution."
- **Evidence it rests on.** `results/p9-calibration-2026-11-14/` and the independent audit `docs/reviews/p9-calibration-audit-2026-11-14/AUDIT.md` (Opus 5.5), which confirmed the findings with separate code.
- **Roles (proposed, study-specific).** Lead: Claude Fable 5.2. Audit: Opus 5.5. Implementation: Sonnet 5.5. Inventory: Haiku 5.5. ADR-0012 stays not approved. **Astra review: NOT_PERFORMED.**
- **Relation to ADR-0017.** ADR-0017 stays blocked. This study is its prerequisite. It tests none of H17-CAP, H17-UTIL, H17-LOC, H17-INC. Its outcome selects, by a rule fixed here, the interface with which ADR-0017 would be revised — or records that no tested interface works on this backbone.

## 1. What is known

On the frozen 27,392-parameter backbones, with five-symbol checksum identifiers (20 bits), rehearsal seeds:

- The hidden state at the answer site carries 0.4 bits of the identifier by a linear probe and 1.0–1.4 by a small non-linear probe. Each identifier position carries its own symbol and almost nothing else. The record's seven input positions together carry 19.8–20.0 bits.
- Attention from the answer site is near-uniform; no head gathers the identifier.
- Content written by a memory at earlier positions does not reach the answer site through the frozen upper block: a perfect per-fact vector at the six earlier positions gives 2.8–4.7% (chance 3.1%), the same vector at the answer site 96.9%.
- Given the right slot, the readout works (97–100%). It learns by number of optimizer updates of the shared output projection and gate, not by exposures per fact.
- Training on all 256 output bytes while scoring within the 32-symbol alphabet costs one symbol on one backbone and slows learning roughly fourfold.

So the memory can store and return an answer, and the backbone cannot say which answer it wants. That is a property of this testbed. It is not evidence about the ArborLM concept.

## 2. Question and hypotheses

**Can a small learned interface deliver a fact's identity to the memory at the position where the answer is produced, and what is the least such interface?**

- **H18-NAT (expected to fail; registered as a baseline).** The natural query — a learned linear projection of the answer-site hidden state — retrieves facts above chance.
- **H18-WIN.** A learned linear query over the hidden states of the last seven positions retrieves facts nearly as well as an oracle query.
- **H18-ATT.** A single learned attention head that reads the preceding positions and forms the query retrieves facts nearly as well as an oracle query, without being told the record length.
- **H18-BB (does the backbone contribute?).** The window query over block-0 hidden states is no worse than the same query over raw token and position embeddings. If embeddings do as well, the backbone adds nothing to addressing here.

Each can fail. A failure of all learned interfaces is a result: this backbone cannot serve as the testbed, and ADR-0017 stays blocked.

## 3. Interfaces under test

All use the flat memory of ADR-0017 §5 unless stated (cosine keys, top-8, temperature 0.2, key width 16), read **at the answer site only**, and add the read there. Reading at other positions is not used: §1 shows it cannot reach the answer.

| Arm | Query at the answer site t | Trained | Extra parameters |
|---|---|---|---|
| N natural | W·h_t | keys, values, W, output projection, gate | — (historical) |
| W7 window | W·[h_{t−6}; …; h_t], h from block 0 | as N, with the wider W | 16 × 224 − 16 × 32 = 3,072 |
| E7 embedding window | W·[e_{t−6}; …; e_t], e = token + position embedding (no block) | as W7 | 3,072 |
| A1 attention head | one head: query from h_t, keys and values from h_{t−15}…h_t, causal, 32 wide, then W | as N, plus the head | 3 × 32 × 32 = 3,072 |
| R1 oracle query | fixed random unit code per fact (ADR-0017 §5.3) | keys, values, output projection, gate | — |
| R2 oracle address | dedicated slot per fact | values, output projection, gate | — |

- h is the frozen block-0 output; the frozen backbone is unchanged in every arm. The interface is part of the memory addition and is trained with it.
- **W7 knows the record length** (seven positions); that is a property of the task leaking into the design, stated as a limit. **A1 does not:** it sees sixteen positions, two records, and must learn where to look. A1 is the form that could carry over to text.
- Tree variant: W7 and A1 with the learned tree (64 branches at 16,384 slots), the router fed by the same query. It checks that routing can use the interface; it is not a tree-against-flat comparison.

### Dense controls

- **D plain:** the P4/P5 adapter on h_t, parameter-matched to arm N. Expected at chance.
- **D7 window:** the adapter on [h_{t−6}; …; h_t], hidden width set so its parameter count matches arm W7 **including the interface** within 0.1%. This is the fair comparator: same window, same parameters, same updates.

## 4. Task, data, loss

- Task, identifiers, templates, clusters, streams and panels exactly as ADR-0017 §4 (family 1), with the data generator already implemented and its gate G1.
- **Loss: cross-entropy over the 32 alphabet symbols at answer sites**, for every arm. Scoring is the most probable alphabet symbol, ties wrong. Loss and scoring now use the same output set. The 256-way loss is reported descriptively.
- **Matched updates.** Every cell of a size runs the same number of updates U, and **U is the same at every size** (§6). Exposures per fact therefore differ across sizes and are reported. Matched exposure is not used in any rule.
- Memory reads only at answer sites, so non-answer positions are untouched in every arm.

## 5. Measurements

- Accuracy and I_acc (Fano bound with the chance floor) as ADR-0017 §6.1, on primary panels A and B; H1/H2 and mixed-cluster panels secondary.
- **Interface efficiency** η = accuracy(arm) / accuracy(R1), same size, seed and panel.
- Query diagnostics: mean cosine between queries of different facts; share of facts whose nearest other query is closer than 0.9; for A1, the attention weight on the five identifier positions.
- Memory dependence: value permutation and disabling; minimal supports as ADR-0017 §6.2 restricted to the answer-site read (there is no other read).
- No-memory baseline, exact retrieval, unseen-fact control with the LEAKAGE flag; gate G2 as ADR-0017 §8.1.
- Training diagnostics of ADR-0017 §6.3; parameters and optimizer-state bytes per arm.

## 6. Calibration (fresh rehearsal draw, before the freeze)

Draw 0 informed this design, so calibration uses rehearsal draw 1.

- Allowed: controls; R2 at the three sizes with the alphabet loss, snapshots at 1,024 / 2,048 / 4,096 / 8,192 updates.
- **Rule:** U is the smallest of {2,048, 4,096, 8,192} at which R2 accuracy is ≥ 0.95 at every size, taking the minimum over the registered-parent (B101) runs and both panels; the B102 run is reported. If no U qualifies at some size, that size is `TASK_CEILING_FAIL` and is not run.
- Not allowed: any arm of §3 other than R2.
- After calibration only U and ceiling-failed sizes may change. Anything else is a new revision.

## 7. Matrix and seeds

Initialization seeds 1801 and 1802 on parent B101/O301; one replicate (seed 1801, parent B102/O302) where marked. Data seeds 180001 upward (new draw; ADR-0017's registered seeds stay unused). Rehearsal seeds as ADR-0017 (179001 upward).

| Size (slots / facts) | Arms | Cells |
|---|---|---|
| 16,384 / 8,192 | N, W7, E7, A1, R1, R2, D plain, D7, tree W7, tree A1 | 20, + B102 replicate of W7, A1, R1, D7 = 24 |
| 65,536 / 32,768 | N, W7, A1, R1, D7 | 10 |
| 4,096 / 2,048 | W7, A1, R1 | 6 |
| **Total** | | **40** |

Three sizes are included so that the selected interface is known to work across the range ADR-0017 needs, not to measure capacity. No capacity class is derived here.

## 8. Classes and the selection rule

Per learned interface (W7, A1; E7 and N are classified the same way for the record), at a size, both B101 seeds and both panels, first match wins:

| Order | Class | Rule |
|---|---|---|
| 1 | NOT_EVALUATED | R1 accuracy below 0.5 at that size in either seed (the ceiling itself failed) |
| 2 | INTERFACE_WORKS | accuracy ≥ 0.5 and η ≥ 0.90; value permutation and disabling give chance |
| 3 | INTERFACE_PARTIAL | accuracy above the G2 interval and ≥ 0.25, not row 2 |
| 4 | INTERFACE_FAILS | accuracy inside the G2 interval or below 0.25 |
| — | NOT REPLICATED | panels disagree |

Seeds must agree, else INTERMEDIATE. The B102 replicate is reported and must not be INTERFACE_FAILS for a WORKS class to stand at 16,384.

Annotations:

- **BEATS DENSE WINDOW** if the arm's I_acc ≥ 1.10 × D7's at 16,384 and 65,536, both seeds. **DENSE WINDOW SUFFICES** if D7's accuracy ≥ 0.90 × the arm's: then the memory is not needed for this task at this size, and that is reported plainly.
- **BACKBONE ADDS NOTHING** if E7's accuracy ≥ 0.97 × W7's at 16,384, both seeds.
- **TREE ROUTES** if the tree variant's accuracy ≥ 0.90 × its flat arm's at 16,384.

**Selection rule for a revision of ADR-0017** (fixed now):

1. If A1 is INTERFACE_WORKS at all three sizes → A1 is the interface.
2. Else if W7 is INTERFACE_WORKS at all three sizes → W7, with the limit that it knows the record length.
3. Else → no tested interface works; ADR-0017 stays blocked on this backbone. The options then are a backbone trained to carry what it needs, or stopping this testbed. Either needs a new specification.

A1 is preferred over W7 when both work because it does not encode the record length. A size marked TASK_CEILING_FAIL removes itself from the rule and is stated with the outcome.

## 9. Gates and status

- G1 (generator), G2 (chance; 8 tests as ADR-0017 §8.1), G4 (determinism, checkpoint restoration; the interface modules must leave arm N bit-identical to ADR-0017's R0a at every size).
- `ENGINEERING_FAIL`, `INCOMPLETE`, the dependent-cell stop rule and no re-run with changed settings, as ADR-0017 §8.6. No cell here depends on another.

## 10. Resources (projection from the measured P9 timings, not a measurement of this study)

- Memory reads only at answer sites: 128 queries per update instead of 1,008, so key scoring is about eight times cheaper than in the P9 timing (0.128 s per update at 65,536 slots).
- Projection: under 1 hour of charged execution with six single-thread workers; calibration under 15 minutes.
- **Proposed caps:** 3 GiB per worker, 24 GiB aggregate (as decided for ADR-0017), 3 hours for calibration, rehearsal and the run together. The rehearsal measures time and memory only and fixes the stage caps.

## 11. Implementation

- New modules beside `studies/p9/` (for example `studies/p9i/`), importing the audited P9 data, memory, training, evaluation and job-manager code. No existing file changes; ADR-0017's code and records stay as they are.
- The alphabet loss, answer-site-only reads for arm N, and matched updates are options added in the new package, not edits to `studies/p9/`.

## 12. Order of work

1. Auditor review of this revision; revise until ready.
2. **Human decision 1:** approve for implementation, calibration and rehearsal.
3. Implementation with tests (gradient reach for each interface; arm N identical to R0a; D7 parameter match; every class and annotation triggered on synthetic records).
4. Calibration on rehearsal draw 1 (§6); audited.
5. Rehearsal for time and memory; implementation audit; freeze.
6. **Human decision 2:** approve the frozen revision and the run.
7. The run, once; independent recomputation; report.

## 13. What must not be claimed

- Anything about capacity scaling, utilization, locality or incremental learning. None is tested.
- That an interface that works here would work on natural language. The task has fixed-length records and random identifiers.
- That W7 is a general interface: it is told the record length.
- That a failure of all interfaces is a failure of the ArborLM concept: it would be a statement about this backbone.
- That the oracle rungs are systems.

## 14. Decisions reserved for the human lead

1. Whether the prerequisite should be a separate study (this ADR) or folded into a revision of ADR-0017.
2. Whether a learned interface trained with the memory is acceptable as "the model telling its memory what it needs", given that the frozen backbone itself is unchanged. The alternative — training part of the backbone — is not in this design.
3. Decisions 1 and 2 of §12.
4. ADR-0012; merge; publication; any next phase.

## 15. Approval record

None. Pending.
