# P8 results and review — locality-aware memory training (ten-case pilot)

- Label: `RESULT: FABLE-REVIEWED, OPUS-AUDITED — ASTRA NOT_PERFORMED — PENDING HUMAN REVIEW`. Run under a study-specific Claude workflow for P8 only; ADR-0012 remains pending.
- Specification: [ADR-0015](../../decisions/ADR-0015-p8-locality-aware-memory-training.md), revision 3, frozen at commit `80f46ae`. Matrix, panels, margins and limits were set by the human lead's overnight direction (ADR-0015 §15).
- **Study status: INCOMPLETE.** 60 of 60 cells trained and evaluated; **55 of 60 simulated**. Nothing was rerun, repaired, retuned or selected. P1–P7-B outcomes are unchanged.
- Independent recomputation: Claude Opus 5.5, [`../p8-results-audit-2026-11-14/RESULTS_AUDIT.md`](../p8-results-audit-2026-11-14/RESULTS_AUDIT.md): 1,232 analysis values and 2,032 trace statistics recomputed from raw records with tools fixed before the freeze, zero differences. Who did what: [DELEGATION.md](DELEGATION.md).
- Everything about pages is a **simulation of value-page cache misses on traces, at hypothetical row sizes**. No storage device was used. Nothing here measures I/O, latency or throughput.
- Graphs, tables and data: [`results/p8-2026-11-14/report/`](../../../results/p8-2026-11-14/report/) (`report.html`, nine PNG figures, CSV and JSON).

## 1. What was tested

Whether adding a differentiable locality term to the training loss of a 4,096-slot memory on a frozen backbone produces access patterns that a page layout can exploit **beyond the checkpoint's own slot popularity**, without losing predictive quality or collapsing utilization — and whether a learned tree benefits more than flat memory. Ten cases (three standard baselines, two concentration controls, four locality cases, one combined), three parents, two seeds, 512 updates each; two fresh validation panels (ranks 3072–3583 and 3584–4095), proven unused by two independent reconstructions before the freeze.

## 2. Registered outcome

| Case | Architecture, objective | Panel A | Panel B | Study class |
|---|---|---|---|---|
| C01–C03 | flat / fixed tree / learned tree, standard | baselines | baselines | — |
| C04 | flat + concentration | INCOMPLETE | INCOMPLETE | **INCOMPLETE** (4 of 6 cells simulated) |
| C05 | learned tree + concentration | INCOMPLETE | INCOMPLETE | **INCOMPLETE** (3 of 6 cells simulated) |
| C06 | flat + co-access | COLLAPSED | COLLAPSED | **COLLAPSED** |
| C07 | learned tree + co-access | CONCENTRATION-ONLY | CONCENTRATION-ONLY | **CONCENTRATION-ONLY** |
| C08 | flat + temporal reuse | QUALITY-FAILED | QUALITY-FAILED | **QUALITY-FAILED** |
| C09 | learned tree + temporal reuse | QUALITY-FAILED | COLLAPSED | **NOT REPLICATED ACROSS PANELS** |
| C10 | learned tree + both | QUALITY-FAILED | QUALITY-FAILED | **QUALITY-FAILED** |

- **No case is LOCALITY-POSITIVE on either panel.** None beats the optimized flat baseline; none shows an architecture advantage.
- Registered decision-map output: **"none"**, because the study is incomplete. See §6 for what can and cannot be said about the decision.
- The classes of C06–C10 rest on complete records for those cases, but see defect 1 in §7: the simulation stage kept launching cells after the first failure, which the freeze record's wording said it would not. Whether those classes stand as registered is a decision for the human lead.

## 3. What happened, in numbers

Means over six cells; Panel A / Panel B. NLL in nats per byte. N_eff is the entropy-effective number of slots used on 262,144 selections. m is simulated warm capacity misses per query under the co-access layout, primary setting (2 rows per page, 32-page cache, hypothetical row size).

| Case | NLL | ΔNLL vs baseline | Pairs above +0.005 | Gain retention | N_eff | U-ratio | m | M-ratio (range over settings and tie rules) |
|---|---|---|---|---|---|---|---|---|
| C01 flat | 2.3637 / 2.3452 | — | — | — | 127 / 128 | — | 2.29 / 2.30 | — |
| C02 fixed tree | 2.3635 / 2.3452 | — | — | — | 103 / 104 | — | 1.75 / 1.76 | — |
| C03 learned tree | 2.3648 / 2.3465 | — | — | — | 84 / 84 | — | 1.32 / 1.31 | — |
| C04 flat + conc | 2.3797 / 2.3591 | +0.0106 / +0.0100 | 6 / 6 | 0.55 | 8–13 per cell | 0.076 | 0 in the 4 simulated cells | not determinable |
| C05 tree + conc | 2.3812 / 2.3607 | +0.0117 / +0.0106 | 6 / 6 | 0.48–0.51 | 8–13 per cell | 0.105 | 0 in the 3 simulated cells | not determinable |
| C06 flat + co | 2.3670 / 2.3486 | +0.0033 / +0.0034 | 1 / 1 | 0.85 | 50 / 50 | 0.371 | 0.34 / 0.35 | 0.143–0.151 |
| C07 tree + co | 2.3657 / 2.3476 | +0.0009 / +0.0011 | 0 / 0 | 0.95 | 46 / 46 | 0.538 | 0.21 / 0.21 | 0.161–0.189 |
| C08 flat + temp | 2.3679 / 2.3496 | +0.0042 / +0.0044 | 2 / 2 | 0.81–0.82 | 22 / 22 | 0.172 | 0.000 | 0–0.00006 |
| C09 tree + temp | 2.3689 / 2.3503 | +0.0041 / +0.0038 | 2 / 1 | 0.82 | 21 / 21 | 0.251 | 0.000 | ≤ 0.00024 |
| C10 tree + both | 2.3715 / 2.3527 | +0.0067 / +0.0062 | 4 / 5 | 0.70–0.71 | 20 / 20 | 0.238 | 0.000 | 0–0.00001 |

The C04 and C05 rows for ΔNLL, pairs, retention and U-ratio come from the evaluation records, which exist for all six cells; they are the auditor's descriptive reading, not registered classes.

### 3.1 Every locality term acted as a concentration term

Each regularized case ended up using a fraction of the slots its baseline uses: about 40% (C06, C07), 17–25% (C08, C09, C10) and under 11% (C04, C05). The standard flat memory already uses only about 127 effective slots (391 distinct) of 4,096; the regularized memories use 20–50.

With so few slots, the working set fits inside the simulated 64-row cache. Misses fall to a fifth of the baseline's (co-access cases) or to essentially zero (temporal cases). **The count-preserving null falls with them**: the null's own misses are 0.00 in every C08, C09 and C10 cell and below the registered 0.05 floor in three of the twelve co-access cells. So the registered locality measure E — misses relative to what slot popularity alone costs — is **undefined for every regularized case**, and so is its utilization adjustment (no case's utilization range overlaps its baseline's). The study has no evidence of locality beyond concentration, and at these cache settings it could not have produced any once utilization fell this far: the simulated question became degenerate.

Where E is still defined per cell, it does not move. In the co-access cells with a usable null, E under the co-access layout is 0.68 (C06, five cells) and 0.76 (C07, four cells) against 0.70 (C01) and 0.73 (C03) in the primary setting. These are descriptive, on a subset, and enter no class.

### 3.2 Temporal structure did not appear

Slot reuse across the previous eight queries rose from 0.48 (C01) to 0.73–0.75 (co-access) and 0.93–0.96 (temporal), but the same statistic on the count-preserving null rose equally: the actual-to-null ratio is 1.00–1.03 for every regularized case, against 1.03–1.05 for the baselines. Reuse rose because few slots are in use, not because consecutive queries share slots more than chance. Top-branch persistence in trees is *below* its order-shuffled value in every tree case (ratio 0.66–0.94).

### 3.3 The concentration controls collapsed completely, and broke the null generator

C04 and C05 lost about half the memory's gain (ΔNLL +0.010 to +0.012; all six pairs above the guard) and went to 8–13 effective slots. Five of their twelve cells select **the same eight slots on every one of 32,768 queries**. For those cells the only count-preserving null is the trace itself. ADR-0013's unchanged greedy shuffle-and-repair generator cannot construct it and raised an invariant error; those five cells have no simulation record (Panel A failed first; Panel B was never attempted). The auditor confirmed a valid null exists in each case and that the generator, not the data, is what failed.

By the registered rule order C04 and C05 would be QUALITY-FAILED from the evaluation records alone, whatever their simulations showed. That is a descriptive reading; their registered class is INCOMPLETE.

### 3.4 Flat versus tree

- Standard training repeats P5 and P7: quality within 0.0013 nats/byte of flat; trees use fewer slots (N_eff 84–103 against 127) and have fewer misses for that reason, with E the same (0.70 flat, 0.70 fixed, 0.73 learned).
- Under the co-access term the learned tree kept more quality (ΔNLL +0.001, gain retention 0.95) than flat (+0.003, 0.85) and more of its baseline's utilization (0.54 against 0.37), ending at about the same absolute N_eff (46 against 50). Under the temporal term both lost about 0.004. Six pairs from three correlated parents; no architecture claim follows, and the registered architecture-advantage test is false for every case.

### 3.5 What the proxy did during training

All three regularizer values fell. Part of the fall was the margin-widening route declared in advance (ADR-0015 §3): in C04, C05 and C10 the gap between the 8th and 9th scores grew to 4–8.5 and the soft mass outside the top eight went to about zero, after which the step-wise coefficient λ rose to about 6·10⁵ (the regularizer gradient having almost vanished). No λ = 0 event and no gradient clipping occurred. The ADR's sentence that λ is bounded is wrong as an operational statement (defect 5).

### 3.6 Layout controls

- Arbitrary 16×256 partitions cost 1.5–2.4 times the unconstrained co-access layout in the primary setting for every case with nonzero misses, as in P7-B.
- The slot-ID grouping the co-access term trains toward is **not** itself a good layout: m under the identity layout is 0.59 (C06) and 0.41 (C07) against 0.34 and 0.21 under post-hoc co-access clustering. In the confirmation setting the identity layout gives the single-term temporal cases (C08, C09) 4–5 misses per query where clustering gives zero.

## 4. What is established, what failed, what remains unknown

**Measured in this pilot (both panels agree to the third decimal on almost every quantity):**

- At one dose, three differentiable locality terms each reduced the number of slots in use by 46–92% in 512 updates.
- Predictive cost was small relative to the reduction: the tree with the co-access term kept 95% of the memory's gain on about 46 effective slots; the temporal cases kept about 82% on about 21.
- The simulated miss reductions are fully accounted for by that concentration. No registered quantity shows co-access or temporal structure beyond slot popularity.
- The pure concentration term is the worst trade of the five: most collapse, most quality lost.

**Failed:**

- H3 as registered: no case met the locality criteria. Two cases failed the quality guard, one collapsed, one was concentration-only, one did not replicate between panels (a single pair at 0.00551 on Panel A against 0.00486 on Panel B decided it; neither panel could have been positive).
- The study itself did not complete: five simulation records are missing.
- The matched-pressure rule did not deliver a controlled dose (§3.5).

**Unknown:**

- Whether any locality term can add structure beyond popularity when utilization is held up — this design could not tell, because nothing held utilization up and the cache then swallowed the working set.
- Whether a lower dose, a utilization floor, or a load-balance term changes the picture. One dose was registered (ADR-0015 §9).
- Whether the small quality cost of using 20–50 slots survives longer training or a memory that actually uses its capacity. The baselines here use about 3% of the slots; this pilot says little about a memory under capacity pressure.
- Anything about physical storage (H4) or capacity scaling (H5).

## 5. How this result should be weighed

- **It is a negative result for the registered question and an incomplete study.** It does not show that locality-aware training cannot work; it shows that these three terms, at this dose, reduce to concentration.
- **The registered measure went degenerate.** With 20–50 slots in use and 64 cached rows, both misses and null misses are near zero. P7-B's settings were chosen for memories using 80–150 effective slots.
- **One dose, 512 updates, three correlated parents, two seeds, one corpus, hypothetical row sizes.** Panel B is a same-corpus check; it reproduces Panel A almost exactly, which shows stability on this corpus only.
- **All roles are Claude models.** The auditor's pre-freeze audits missed defect 1.

## 6. Decision memo

The registered map (ADR-0015 §8) outputs "none" for an incomplete study. Read descriptively: no completion of the five missing simulations could make any case LOCALITY-POSITIVE (C04 and C05 fail the quality guard on evaluation records alone; the other cases' records are complete), so the conditions for **(a) proceed toward learned topology** and **(b) keep locality-aware training on flat memory** are not met, and the map's remaining option is **(c) stop or redesign this line at this scale**. That reading is the lead's, not a registered output.

The lead's recommendation, for the human lead to accept or reject:

1. **Do not proceed toward learned topology on this evidence.** Nothing here supports a locality benefit specific to the tree.
2. **Do not read the miss reductions as progress toward the storage goal.** A memory that uses 20 of 4,096 slots has a small working set because it has a small memory in use.
3. **If the line continues, the next question is utilization, not locality.** The baselines use about 3% of their slots after 512 updates. A locality objective can only be tested meaningfully on a memory that is using its capacity, with an explicit term or constraint that keeps it so, and at cache settings scaled to the working set. That would be a new specification.
4. **One observation worth a deliberate follow-up, not a claim:** most of the memory's predictive gain survived on about 46 slots (C07). Whether that means the task needs little memory, or that 512 updates fill little memory, is not known.

## 7. Defects and deviations

None changes a registered number. Numbers 1 and 9 need the human lead's attention.

1. **Stop rule not enforced in simulation (deviation from the freeze record's wording).** ADR-0015 §16 item 6 says a failed cell stops the launch of further cells. The training stage implements that; the simulation pool does not, and continued after the first failure about 2.5 s in. Most of the 55 simulation records, and with them the C06–C10 classes, exist because of that. §11 says only that a failed cell is kept and the study is then INCOMPLETE. The lead wrote §16 item 6 with training in mind and did not check the simulation pool against it; the pre-freeze audits did not catch it. The records are kept as they are; whether the C06–C10 classes are accepted as registered is the human lead's decision.
2. **The registered null generator fails on fully collapsed selections** although a valid null exists. Five cells have no simulation record for this reason.
3. **Case means for C04 and C05 in `analysis.json`, `scorecard.csv` and the figures average only the simulated cells**, which omits the most collapsed ones (for example C05 Panel A distinct slots reads 31.0 where all six cells average 19.5). The scorecard has no cell-count column. This review's table uses all-cell evaluation values for those rows.
4. Where E is undefined, the records write pair and parent counts as 0, not null.
5. ADR-0015 §4 says λ is bounded; it reached about 6·10⁵.
6. Two RSS measurements differ slightly between records (cosmetic).
7. The simulation manifest points at a scratch copy of the P7-B reproduction record; the committed copy (`results/p8-2026-11-14/logs/p7b_reproduction_frozen_source.json`) matches by hash.
8. The determinable C04/C05 guard results are not in the implementation's output; they are in the auditor's report and §3 here.
9. **The report generator was edited after the run.** `results/p8-2026-11-14/report/make_report.py` raised a ZeroDivisionError on its first real render (a ratio with zero misses in the denominator) and received a one-line guard that draws such ratios as undefined. It is an analysis-only plotting tool outside the frozen source tree; no registered number passes through it. The edit is in its own commit.
10. The logged reason for a λ = 0 event can be mislabelled (known before the freeze; no such event occurred).
11. The lead's first launcher line for the restore gate, evaluation and reproduction check failed on shell quoting before any stage started (`results/p8-2026-11-14/logs/launcher_failed_attempt.md`).
12. All commits were local until one push, as in earlier studies; ordering rests on local history and author timestamps. Before the push the commit messages were reduced to single signed lines to satisfy the owner's pre-push hook, which changed the commit hashes but no file content: the freeze commit cited as `80f46ae` in every manifest is pushed as `378aeac`. See [COMMIT_MAP.md](COMMIT_MAP.md).

## 8. Resources

| Stage | Wall time | Cap | Peak worker RSS |
|---|---:|---:|---:|
| Training, 60 cells, 4 workers | 393 s | 5,400 s | 0.47 GiB |
| Restore gate, 10 cells | passed 10/10 | — | — |
| Evaluation and traces | 106 s | 1,800 s | 0.39 GiB |
| Simulation | 74 s | 5,400 s | — |
| Analysis | 1 s | 600 s | — |

Peak aggregate RSS 1.93 GB against 8 GiB. No cloud, paid service, download, SSD work or capacity change. Checkpoints and traces stay local and are not published. Overnight active wall time from the first merge check to this review: about 1 h 45 min of the 8 h limit.

## 9. Questions for the human research lead

1. **Accept the C06–C10 classes as registered, despite defect 1?** They rest on complete records; the stop rule's wording was not followed in the simulation stage.
2. **Complete the five missing simulations?** It would need a repaired null construction for fully collapsed cells (for which the null is the trace itself). It cannot change any class.
3. **Direction:** stop this line at this scale, or authorize a new specification that tests locality on a memory held at high utilization (§6 item 3).
4. **Governance:** ADR-0012 is still pending; P8 ran under a study-specific direction.
5. **Merging** the P8 draft pull request.
