# ADR-0027 — P10-I-S4: quality against computational cost (conditional specification)

**Status: DRAFT — CONDITIONAL — NOT APPROVED. Nothing under this ADR is implemented, calibrated, frozen or run. Entry requires a separate decision by the human lead.**

- Date: 2026-11-17 UTC. Revision 3, after the independent review and its confirmation review (section 15), aligned with the sibling drafts as they stood on disk at this revision (ADR-0023, ADR-0024 and ADR-0026 third drafts; ADR-0029). Drafted by the lead (Claude Fable 5.2) under `docs/reviews/p10-i-direction-2026-11-17/DIRECTION.md` sections 2 to 5 and 8.
- `Astra review: NOT_PERFORMED`. Claude review is not Astra review. **SPEC: PENDING ASTRA REVIEW.**
- Kind of document: a conditional specification. It fixes the entry criterion, the question, the primary comparison, the verdict labels, the stop rules, the cost ceilings and what is reserved for the human lead. It does not fix every parameter. Section 12 lists what a later revision must fix before a freeze. Approval of the P10-I programme does not authorize this study.
- P1 to P10 code, records, thresholds, seeds and outcomes are immutable. Nothing here revises or reopens them. ArborLM is unproven research; no label below is a success claim for the project.

## 1. Question and outcome meanings

At matched training computation, is the quality of the memory at least that of strong, individually optimised alternatives on the same task, data and frozen backbone?

| Outcome | Meaning |
|---|---|
| MEMORY AHEAD AT MATCHED COMPUTE | Under **both** cost measures, the memory arm's quality exceeds every trained alternative's by the registered margin, on the tested task, backbone and budget. Nothing about wall time, latency, energy, RAM or storage follows. |
| ALTERNATIVE AHEAD AT MATCHED COMPUTE | Under **either** cost measure, a trained alternative is ahead by the margin. A registered negative result. Every alternative that reaches the count is named, with the measure. |
| NOT SEPARATED AT MARGIN | Under both measures neither side is ahead by the margin. This is not a demonstrated match and is never worded as parity. |
| COST-MEASURE DEPENDENT | The memory is ahead under one measure and not separated under the other. Inconclusive. |
| S4 NOT EVALUABLE (reason) | A validity condition failed (section 9). Not negative, not positive. |

Every label is printed with the scope sentence of section 4 and, where it applies, the qualifier `LOOKUP SUFFICIENT ON THIS TASK` (section 5). Each secondary axis (section 6) has its own line. No line substitutes for another, and no combination of lines is a label.

## 2. Background: registered findings

| Finding | Record |
|---|---|
| P4: at 512 updates and 198,401 trainable parameters the dense adapter beat memory in 27 of 27 comparisons | `results/p4-2026-11-12/README.md` |
| P10-S1 capacity CAPACITY-INCONCLUSIVE; efficiency EFFICIENCY-NEGATIVE (DENSE FASTER); F-OQ and H8 DENSE AHEAD; DENSE HOLDS MORE AT SATURATION for F-OQ, F-OQ-IVF and T-OQ; DICT DOMINATES ON THIS TASK; no line positive for the store | `results/p10s1-run-2026-11-17/OUTCOME.md` section 2, `ACCEPTANCE.md` |
| Mean a_use at 32K facts / 16K slots: at the registered read point U_P, T-OQ 0.401, F-OQ 0.916, D-OQ 0.957; at the run length, 0.697, 0.992, 0.999 | `OUTCOME.md` section 4 |
| At 8K/16K the two cost measures disagree: D-OQ's cost to reach the level is 0.27–0.38 of T-OQ's in measured CPU seconds and 1.32–1.87 of it in analytic multiply-adds | `ACCEPTANCE.md` ruling 2 |
| At 8K/16K (16,384 slots): cumulative analytic multiply-adds to U_P, T-OQ / D-OQ = 5.21e11 / 2.65e12 = 0.197; both arms share U_P there, so 0.197 is also the per-update ratio. Isolated CPU seconds per update, T-OQ / D-OQ = 0.01156 / 0.01204 = 0.960 (rehearsal timing, descriptive) | `RESULTS.md`, cost table and "Isolated timing" |
| Audit observation, descriptive: at matched compute F-OQ is ahead of D-OQ at 32K/16K by 0.24–0.33 bits in 5 of 5 replicates, while DENSE AHEAD holds at matched updates and at D-OQ's best snapshot | `OUTCOME.md` section 4, finding 4 |
| Memory arms ran at learning rate 0.003, untuned by design; D-OQ at its calibrated rate | `OUTCOME.md` section 4 |
| Supplementary read-path throughput (descriptive, in RAM, enters no line): T-OQ 10,106 to 10,211 queries/s at batch 1 from 1,024 to 16,384 slots; F-OQ 19,177 → 7,292; D-OQ 107,879 → 16,768 | `results/p10s1-run-2026-11-17/supplement/throughput_supplement.json` |
| Backbone: frozen, byte-level, 27,392 parameters, context 64 | `docs/decisions/ADR-0021-p10-s1-useful-capacity-scaling.md` section 2 item 10; `ADR-0009` |

Two lessons shape this draft. First, P10-S1 compared a tuned dense control with untuned memory arms; S4 searches every arm under one rule. Second, P10-S1's efficiency label was decided by an unregistered any-cell rule, and at 8K/16K its two cost measures disagreed (`ACCEPTANCE.md` ruling 2); S4 names one primary budget and writes down how the two measures combine.

## 3. Entry criterion

Entry is a decision by the human lead. The lead may propose entry only if the condition below is true of registered and accepted outcomes. Descriptive figures, audit observations, intermediate checkpoints and tags never satisfy a clause.

**Reading of the direction.** `DIRECTION.md` section 4 says "P10-I-S3 or P10-S1". This draft reads the second as P10-I-S1 (ADR-0024), the successor that carries P10-S1's corrections. ADR-0026 section 12 reads it literally as P10-S1; the two drafts differ until the human lead rules (section 11, item 2). `PENDING LEAD REVIEW`. P10-S1 fails under either reading (end of this section).

**ENTRY = A or B.** The route fixes the task and the memory arm of S4.

- **Route A (P10-I-S3, ADR-0026).** The qualifying labels are exactly those ADR-0026 section 12 names. Both: (A1) the registered label of line 1 (DEPENDENCE, arm M-TREE), which is its FRESH regime label (ADR-0026 section 6.5), is **DEPENDENT**; (A2) the registered label of line 2, **COMPETITIVENESS[TREE]** (its FRESH label), is **COMPETITIVE** or **MEMORY AHEAD** (ADR-0026 sections 6.3 to 6.5). Never qualifying: any REP or REP-U regime label; M-FLAT's descriptive D1–D3; CAPACITY WITHOUT DEMONSTRATED DEPENDENCE; NO CAPACITY; NOT COMPETITIVE, including K1 alone; INCONCLUSIVE; NOT EVALUABLE; COMPETITIVENESS[FLAT]. **Convergence tags.** Whether a qualifying label still qualifies when D-ADAPT's registered FRESH convergence tag is NOT CONVERGED is ADR-0026's open choice 13. It is the human lead's, ruled at ADR-0026's Decision 1 before any S3 observation. This ADR does not decide it: Route A's condition is A1 and A2 **as qualified by that ruling**, and S4 may not be proposed for entry on Route A until the ruling is recorded. The memory arm is M-TREE; the task and corpus are S3's.
- **Route B (P10-I-S1, ADR-0024).** The registered **C-CAPACITY** outcome is **CAPACITY-POSITIVE** (ADR-0024 section 9.3, row 3), **carried by a trained arm: F-OQ or T-OQ**. ADR-0024 section 9.3 states that only a trained arm may carry a label another study uses for entry. F-OQ-IVF is an evaluation-only read of F-OQ's memory, with no training, rate search or training cost of its own; it qualifies nothing here, and a positive printed "POST-HOC READ ONLY; NO TRAINED ARM QUALIFIES" fails Route B. For the qualifying arm, CAPACITY_SUPPORTED and NOT BEHIND DENSE already require: a CAPACITY STEP in each of block M's two transitions (1,024 → 4,096 and 4,096 → 16,384); no qualified DEP failure at any snapshot of either cell up to its run length (ADR-0024 sections 8.1 and 9.1, row 2); STORE NOT BEHIND (cell) in all four readings (MC-A, MC-T, MU and D-BEST) on both panels in all five replicates, with MC-T measured and neither matched-compute pair MC-SHORT; and DENSE HOLDS MORE at no loaded cell (section 9.2). So a dense comparison that was not run, was split or was not measured cannot satisfy Route B. If both F-OQ and T-OQ qualify, each enters S4 as its own memory arm with its own label; neither is selected as the best. The cell is fixed in advance: the larger cell of the arm's CAPACITY STEP in block M's transition 4,096 → 16,384, which is 32K/16K if step C2 is a CAPACITY STEP for that arm and otherwise 8K/16K (step N2). Block X and X-CAPACITY do not enter Route B. Every S4 label on this route carries the tags ADR-0024 section 1 attaches to a block M positive, copied as registered there, including `STORE ONLY; ORACLE-ADDRESSED`.

Two things the first draft asked of Route B are not used, because no sibling draft provides them. There is no cell-level capacity label (ADR-0024's capacity labels are step and arm classes). There is no "routing retention met" label: R-DIAGNOSIS, now in ADR-0029 (Stage A1 on P10-S1's checkpoints, Stage A2 on fresh checkpoints), is a diagnosis and has no pass label. C-EFFICIENCY, C-SATURATION as a line of its own, X-CAPACITY, R-DIAGNOSIS, R-CONFIRM and ADR-0024's lane L (not specified and not approved in its third draft) are not part of the entry condition.

If an entry-route label is renamed or withdrawn between the entry decision and the freeze, the study stops and returns to the human lead.

**P10-S1's registered outcome does not meet this criterion.** No line is positive for the store, the capacity line is inconclusive, the efficiency line is negative, and F-OQ and H8 are DENSE AHEAD. The matched-compute observation at 32K/16K is an audit finding, not a registered label. P4 does not meet it either. On today's records S4 may not be entered.

## 4. Arms and the question of a meaningful alternative

The memory arm M is the arm fixed by the entry route. Its architecture is fixed; only its learning rate is searched.

| Arm | What it isolates | In the label rule |
|---|---|---|
| M: the qualifying memory arm | The subject | Yes |
| D: dense adapter at equal stored parameters (the family that led in P4 and P10-S1) | Memory structure against an unstructured dense map | Yes |
| D+: the dense adapter selected over a registered width and depth grid that contains D's architecture (selection rule below) | Whether D is a weak representative of dense | Yes |
| FT: the backbone unfrozen and trained, no addition | Whether any addition is needed at this scale | Yes |
| KV: dictionary lookup (ADR-0024's DICT) on Route B; NOT DEFINED on Route A unless the later revision defines one | Value a plain lookup already provides | No: it has no training computation. It gives the qualifier of section 5 |
| PK: product-key memory | A structured sparse memory that is not a tree | Not an arm. No sibling draft defines one: ADR-0024 section 4 removed its product-key arm and places it in Stage B of the routing work, which is not specified (section 11, item 6) |
| LoRA | Low-rank adaptation of a large frozen model | NOT APPLICABLE (below) |

**Search.** One learning-rate grid, the same for every trained arm, fixed in the revision before calibration. Rates are chosen on the calibration runs only, at one fixed search length in updates, by mean calibration-panel quality at its end over the four calibration runs. D+ runs that same rate grid at every architecture of its grid, so it gets more search cells than M; the surplus is on the side of the alternative, which is the conservative direction.

**Selection of D+.** D+ is the (architecture, rate) pair with the best mean calibration-panel quality at the search length. Pairs within a tie tolerance of the best (one tenth of the route's δ floor: 0.0005 nats per byte on Route A, 0.025 bits on Route B) are tied; a tie goes to the fewer parameters, then to the smaller rate. The choice moves B\* (section 5), which is why it is a rule and not a later parameter. `PENDING LEAD REVIEW`.

**Edges.** If a chosen rate lies at an edge of the rate grid, or D+ is the largest architecture of its grid, the grid is extended by one step past that edge and the search repeated, at most twice per edge, within the hour cap. What follows if the edge persists is in section 9 (ALTERNATIVE RATE AT EDGE, ALTERNATIVE ARCHITECTURE AT EDGE, MEMORY RATE AT EDGE).

**LoRA.** On this backbone full fine-tuning (arm FT) contains every solution a low-rank update of the same weights can reach, and costs about the same per update, because both need the backbone's backward pass. LoRA therefore cannot be a stronger alternative than FT here, and adding it would add a weaker baseline, not a stronger one. For scale: the backbone has 27,392 parameters, and the memory and dense arms of P10-S1 have 33,793 to 788,481 trainable parameters (`RESULTS.md` cost table; the reference rung R2, which is neither, has 1,049,601). LoRA on this backbone is **NOT APPLICABLE**, and the report says so in those words. FT with 27,392 parameters is weak by construction on a memorisation task (Route B); a label there is never read as "memory beats fine-tuning".

A comparison with LoRA is meaningful only on a backbone large enough that full fine-tuning is a real cost. That needs a larger pretrained backbone (possibly a download), a new qualification of the memory on it, and its own approval. This document does not authorize it (section 11, item 1). **Scope sentence, printed with every label:** "one frozen 27,392-parameter backbone; alternatives are dense additions and full fine-tuning; no statement about adaptation of a large model".

One change per comparison: M against each alternative separately, same data draws, same panels, same budget.

## 5. Primary comparison and label rule

**Quality.** Route A: mean next-byte NLL in nats per byte (ADR-0026 section 6.1); lower is better, and "ahead by δ" means lower by at least δ. Route B: i, bits per fact usefully retained (ADR-0024); higher is better. Two registered evaluation panels on either route (section 7).

**Two measures of training computation** (the cost readings of ADR-0024 section 8.2):

- **MC-A, analytic.** Multiply-adds of whole training updates, including the backbone's forward and backward pass and the optimiser, by the formula of ADR-0021 section 22 M6, checked against a counted run. It counts matrix products and gather-weighted sums. **It omits top-k selection, sorting, index traversal and memory-bound gathers**, so it undercounts what a sparse memory does per update: at 16,384 slots it gives T-OQ 0.197 of D-OQ's cost per update where measured CPU gives 0.960 (section 2). It is used as the first matching variable because it is deterministic and independent of machine load. It is a counted quantity and is never reported as measured cost or efficiency.
- **MC-T, measured.** Single-thread process CPU seconds per update, per arm at its size, median of repeats, from an isolated timing block on a quiet machine (section 8). Cumulative MC-T of an arm at u updates is u times that arm's per-update figure. **B\*_T and every snapshot update count use the rehearsal's per-update figures.** The isolated timing stage after training only tests those figures against the CV rule; it does not replace them.

**Order of work before the freeze.** (1) Rate search and selection of D+ (section 4). (2) Convergence runs at the chosen rates: four calibration runs per arm (two calibration data sets × two initialisation seeds). (3) B\* and B\*_T. (4) The calibration runs of every arm, M included, continue to B\* and to B\*_T, so that s (below) is measured at the budget.

**Primary budget B\*.** For each of D, D+ and FT, c(arm) is the mean over the four calibration runs of the cumulative MC-A computation at which the run first meets the registered convergence rule. B\* = max of c(D), c(D+), c(FT). KV does not enter. If any calibration run of the three does not meet the rule within the training-length ceiling, the outcome is S4 NOT EVALUABLE (B\* NOT DETERMINED). B\*_T, the budget in MC-T, is the update count of the B\*-defining arm at B\* times that arm's per-update CPU seconds. Other budgets are descriptive.

**Route A's data bound.** Route A trains on unseen single-pass data only, because its entry labels are FRESH labels. ADR-0026's FRESH pool supports at most 19,064 updates (its section 4), so the training-length ceiling on Route A is 19,064 updates for every arm and is not extended. If any arm's update count at B\* or at B\*_T would exceed 19,064, the outcome is S4 NOT EVALUABLE (TRAINING DATA EXHAUSTED BEFORE B\*). Both this and B\* NOT DETERMINED are known from the calibration runs, before the freeze and before any registered cell, and the study then returns to the human lead. ADR-0026 itself expects arms to be NOT CONVERGED at 16,384 updates on this corpus, so on Route A one of these two outcomes is likely under the rule as written. The alternative, a budget fixed by duration and not by convergence, is reserved (section 11, item 8); it is not adopted here.

**Snapshots.** Each arm is saved at update counts set per arm, so that its cumulative computation is the largest not exceeding f · B\* (and f · B\*_T) for f in {1/8, 1/4, 1/2, 3/4, 1}. The reading at f = 1 is therefore within one update of the budget for every arm. If one update of an arm exceeds the budget, S4 NOT EVALUABLE (NO SNAPSHOT AT B\*).

**Replicate unit.**

| | Route B | Route A |
|---|---|---|
| Unit | A data draw: 5 fresh draw sets, one initialisation seed each | A parent: ADR-0026's nine fixed P3 parents, three initialisation seeds each (27 cells per arm). A parent's value on a panel is the mean over its three seeds, as in ADR-0026 section 6.1 |
| Count required | at least 4 of 5 | at least 8 of 9 (ADR-0026's parent rule) |
| One-sided chance of the count under no difference | 6/32 = 0.19 | 10/512 = 0.02 |

**Replicate rule.** A unit **favours M** only if, on both panels, M is ahead of **every one** of D, D+ and FT by δ in that same unit (the joint reading). A unit **favours alternative X** if, on either panel, X is ahead of M by δ. This is the asymmetric rule of ADR-0021 section 22 (h).

**Label under one measure.** M-AHEAD if at least the required count of units favour M. X-AHEAD if at least the required count favour one and the same alternative X; if two alternatives each reach it, both are named. Otherwise NOT-SEPARATED. M-AHEAD and X-AHEAD cannot both hold: a unit that favours M cannot favour any X.

**Combining the two measures (asymmetric).**

| MC-A | MC-T | Outcome |
|---|---|---|
| M-AHEAD | M-AHEAD | MEMORY AHEAD AT MATCHED COMPUTE |
| X-AHEAD | M-AHEAD, X-AHEAD or NOT-SEPARATED | ALTERNATIVE AHEAD AT MATCHED COMPUTE (MC-A) |
| M-AHEAD or NOT-SEPARATED | X-AHEAD | ALTERNATIVE AHEAD AT MATCHED COMPUTE (MC-T) |
| X-AHEAD | NOT MEASURED, and the premise below holds | ALTERNATIVE AHEAD AT MATCHED COMPUTE (MC-A; MC-T NOT MEASURED) |
| X-AHEAD | NOT MEASURED, and the premise below fails | S4 NOT EVALUABLE (COST MEASURE MISSING) |
| M-AHEAD under one, NOT-SEPARATED under the other | | COST-MEASURE DEPENDENT |
| NOT-SEPARATED | NOT-SEPARATED | NOT SEPARATED AT MARGIN |
| M-AHEAD or NOT-SEPARATED | NOT MEASURED | S4 NOT EVALUABLE (COST MEASURE MISSING) |

**Premise for a negative without measured cost.** An alternative that leads under MC-A would also lead under MC-T only if matching on MC-A gives the memory at least as many updates as matching on MC-T does, and more updates do not hurt it. So the row applies only if the **rehearsal's** figures show both: (i) M's CPU seconds per counted multiply-add are at least those of X and of the arm that defines B\*; and (ii) M's mean calibration quality at its MC-A-matched update count is not worse than at its MC-T-matched update count. P10-S1 supports (i) for T-OQ against D-OQ (0.197 counted against 0.960 measured); it is not established for D+, FT or Route A, which is why it is checked and not assumed. The rehearsal measures per-update CPU in any case.

Reason for the asymmetry. A label that favours the memory must hold under both measures, because the analytic one omits selection and lookup work and so leans towards sparse arms; a label against the memory needs only one. This follows the direction of ADR-0021 section 5.4, which read an ambiguous pair in favour of the comparator. It agrees with ADR-0024 section 9.2, where a store-favouring label needs matched compute under both cost measures separately (and matched updates and the dense arm's best snapshot as well). It is stricter against the memory than ADR-0024's negatives: there DENSE AHEAD (cell) needs MC-A and, where measured, MC-T, and an efficiency negative needs both readings at every cell (section 9.5). S4 is stricter because its positive label is the one most open to misuse.

**δ.** δ = max(floor, 2 × s). s is the pooled within-group standard deviation of the quality measure at B\*, over groups (trained arm, panel), from the four calibration runs of each arm. Floors, fixed now: Route A 0.005 nats per byte (the resolution used since ADR-0006 and in ADR-0026 section 6.1); Route B 0.25 bits (the "not behind" margin of ADR-0021 and ADR-0024 section 9.2). The floor carries the weight; s can only widen δ. s is the spread of single-arm quality, not of paired differences, so it overstates the spread of a difference and widens δ for both sides. The factor 2 and the required counts are `PENDING LEAD REVIEW`.

**Lookup qualifier.** Where KV is defined (Route B): if KV's quality is at least M's minus δ on both panels in at least 4 of 5 draws, every S4 label carries `LOOKUP SUFFICIENT ON THIS TASK`, and no label is printed without it. On P10-S1's records the dictionary answered every fact, so on Route B the qualifier is expected. On Route A no KV is defined and the qualifier does not apply.

This is a statement about quality at an equal budget. It is not a statement that either arm is faster or cheaper. No advantage is inferred from parameter counts, active parameters, rows read or MC-A itself.

## 6. Secondary axes, each reported separately

| Axis | How measured | If the condition fails |
|---|---|---|
| Training wall time | Quiet isolated block, medians over repeats, CV rule | WALL TIME NOT MEASURED |
| Inference latency and throughput | Quiet isolated block, batch 1 and one larger batch | LATENCY NOT MEASURED |
| Energy | Needs administrator access (`powermetrics`); the lead does not have it | ENERGY NOT MEASURED unless the human lead runs or authorizes it (section 11, item 4) |
| RAM | Process peak resident memory, and analytic bytes of parameters plus optimiser state. In P10-S1 peak resident memory was 320–376 MB per process, mostly runtime, so the analytic figure is the informative one | Always reported |
| Stored bytes | Checkpoint bytes on disk, with and without optimiser state, printed separately | Always reported |

Each axis is printed per arm in its own table. There is no composite score and no sentence that combines axes with the primary label. Storage here means checkpoint size; storage I/O belongs to ADR-0028.

## 7. Data, seeds, sizes

- **Route B.** Task and sizes are ADR-0024's at the cell of section 3. Five registered draw sets and two calibration draw sets, all fresh; two initialisation seeds on the calibration sets; the two evaluation panels of ADR-0024's layout.
- **Route A.** ADR-0026's corpus, FRESH pool and nine parents (read-only reuse of the P3 backbones, as ADR-0026 section 3.1). Each cell's training stream is a seeded permutation of the FRESH pool, single pass. This is data the backbone and S3's additions have met in other orders; it is unseen by the arms trained here, and "fresh" means that and no more. **Panels and the ledger:** two registered panels and one calibration panel, 512 chunks each, are drawn by ADR-0026 section 4's panel rule, after and excluding every byte span already in the shared panel ledger (ADR-0026's and ADR-0025's panels and every earlier study's), and are written into that ledger at S4's freeze. `arbor-clerk` inventories and `arbor-auditor` reconstructs them independently. If the walk runs out of eligible chunks: S4 NOT EVALUABLE (NO ELIGIBLE PANEL), decided before any training.
- **Seeds** are those of `docs/reviews/p10-i-direction-2026-11-17/SEED_REGISTRY.md` section 4.2: data 270001–279999, with registered sets at 270001 + 100(d − 1), calibration sets 279001 and 279101, rehearsal set 279201, auxiliary 277001–278999; initialisation 330401–330499; tests 936001–936999. The first draft's initialisation range 2701–2799 collided with seeds derived in P9 and P9-I (registry section 5) and is withdrawn. A gate re-runs the registry checker, with derived seeds expanded, before the freeze.

| Role | Route B | Route A |
|---|---|---|
| Registered data | 5 draw sets, d = 1..5; inside a set, the offsets of ADR-0024's generator layout, copied at the freeze | 27 stream-permutation seeds: set d = parent p (1..9), offset s − 1 for initialisation seed s (1..3). The registry lists d = 1..5 and holds 65 further sets; d = 6..9 is a request to the registry, `PENDING LEAD REVIEW` |
| Registered initialisation | 5: 330401–330405, one per draw, shared by all arms | 3: 330401–330403, shared by all parents and arms |
| Calibration | sets 279001, 279101 × initialisation 330491, 330492 = 4 runs per (arm, rate) | 2 calibration parents (fixed in the later revision) with stream seeds 279001, 279101 × initialisation 330491, 330492 = 4 runs per (arm, rate) |
| Rehearsal | set 279201, initialisation 330495 | stream seed 279201, initialisation 330495 |
| Test mode and unit tests | 330498, 330499; 936001–936999 | the same |

## 8. Stages

| Stage | Quiet machine | Notes |
|---|---|---|
| Rehearsal and calibration (calibration draws only) | Only its timing block | Rate search, convergence, s, per-update MC-T; fixes B\*, B\*_T, δ, snapshot update counts |
| Freeze, Decision 2 by the human lead | No | |
| Training, evaluation | No | Resumable per cell; no time comparison is read from this stage |
| Isolated timing (MC-T confirmation, wall time, latency) | Yes, about 1 to 2 hours (estimate) | See below |
| Analysis, report, independent recomputation | No | |

**Quiet condition, measured at the stage.** No record states what this machine's idle load is (recorded checks: 0.998 at the P10-S1 supplement; in ADR-0024 section 16, 0.73 after 1.34 at P10-S1's rehearsal timing and 0.98 at its registered timing stage; the reviewer saw about 3 with other sessions running). **Ceiling, fixed now: a block is quiet only if the one-minute load average is at most 1.0 at its start and at its end.** Reason: it is the figure ADR-0024 section 16 fixes for the same quantity on the same machine, so one rule holds across the programme; MC-T is a single-thread measurement on an 18-core machine, and 1.0 is the level at which P10-S1's timing stages ran. The rehearsal may not raise it. `PENDING LEAD REVIEW`. Within a session the check is retried every 10 minutes for up to 6 hours, as in ADR-0024. Power source, Low Power Mode, thermal state and the thread's quality-of-service class are recorded with every block; a block on battery or in Low Power Mode is not quiet. A session that ends without a quiet block is **PAUSED** and rescheduled with the human lead, in up to three further sessions; only then is the axis NOT MEASURED. This applies to the rehearsal's timing block as well as to the stage after training. A per-update figure from the stage after training that differs from the rehearsal's by more than the registered CV rule is MC-T UNSTABLE and MC-T is treated as NOT MEASURED.

## 9. Limits, stop rules, NOT EVALUABLE

| Limit | Kind | Rule |
|---|---|---|
| Total charged time, proposed 60 hours | Resource cap | Extendable on cost projection only, never on outcome values; a stop is PAUSED and resumable; every planned cell still runs |
| Memory guard per process | Resource cap | As above |
| Rate grid and D+ architecture grid bounds | Design ceiling | Extended one step past an edge, at most twice per edge, within the hour cap |
| Search length; training-length ceiling; convergence-rule parameters | Design ceiling | Fixed before calibration; training length extended only by the convergence rule. On Route A the ceiling is 19,064 updates (the corpus) and is not extended |
| Units (5 draws on Route B; 9 parents × 3 seeds on Route A), snapshot fractions | Design ceiling | Fixed now (units) and at the freeze (fractions) |
| Rescheduled quiet sessions (3) | Design ceiling | Fixed now |
| Load-average ceiling 1.0; retry every 10 minutes for 6 hours; CV rule | Validity threshold | The ceiling is fixed now; the CV rule at the freeze from the rehearsal; neither changed after |
| δ floors, factor 2, tie tolerance, 4 of 5 and 8 of 9, both-panels rule, the combination table and its premise, reference-check tolerance | Scientific threshold | Never relaxed after observation |

Stop rules: the study stops and returns to the human lead if the entry condition does not hold at the freeze; if the rehearsal projects more than the cap; or if a gate fails. No limit is extended because a partial result looks close.

**Precedence.** Every S4 NOT EVALUABLE reason is tested before the combination table of section 5 is read, except COST MEASURE MISSING, which is a row of that table.

S4 NOT EVALUABLE, each printed by name: B\* NOT DETERMINED; TRAINING DATA EXHAUSTED BEFORE B\* (Route A); NO ELIGIBLE PANEL (Route A); NO SNAPSHOT AT B\*; COST MEASURE MISSING (only where section 5's table says so); REFERENCE NOT REPRODUCED (the entry arm does not reproduce its entry-route behaviour on calibration runs within the registered tolerance); ALTERNATIVE RATE AT EDGE (an alternative's rate is still at an edge after two extensions and the label would not be ALTERNATIVE AHEAD); ALTERNATIVE ARCHITECTURE AT EDGE (D+ is still the largest architecture of its grid after two extensions and the label would not be ALTERNATIVE AHEAD); MEMORY RATE AT EDGE (the same for M's rate when the label would be ALTERNATIVE AHEAD); ANALYTIC FORMULA CHECK FAILED; NON-FINITE TRAINING in any arm; PLATFORM CHANGED between stages; FEWER UNITS THAN REGISTERED after resumption.

## 10. Cost projection (estimate; replaced by the rehearsal)

P10-S1 charged 49,251.2 s for 178 training cells and 1,899.0 s for 1,866 snapshot evaluations (`OUTCOME.md` section 1), about 277 s per training cell. **Route B:** 4 trained arms × 5 draws = 20 registered cells per memory arm, plus about 60 to 120 search and convergence cells; at P10-S1's average cost, of the order of 6 to 12 hours. **Route A:** 4 trained arms × 27 cells = 108 registered cells of up to 19,064 updates each, plus four calibration runs per (arm, rate, D+ architecture); the per-update costs are in ADR-0026 section 9 and are not repeated here, and the total is several times Route B's. The 60-hour cap is a placeholder. The rehearsal measures cost per update per arm under both measures, the convergence length and the search size, and replaces all of this. On a larger backbone no estimate can be made from the records.

## 11. Reserved for the human lead

1. **Backbone.** The 27,392-parameter backbone with LoRA NOT APPLICABLE, or a larger backbone as a precondition. Recommendation: the small backbone first, with the scope sentence; a larger backbone is a separate specification, approval and, if needed, download decision.
2. **Route B alone, and the reading of "P10-S1" in the direction** (this draft reads it as P10-I-S1; ADR-0026 section 12 reads it literally). Recommendation: Route B alone should not suffice; a plain lookup dominated P10-S1's task.
3. **Cost measures.** MC-A as first matching variable with MC-T required for any label that favours the memory (this draft), or MC-T alone. Measured CPU seconds thus gate the positive label; that is a measured time quantity inside the primary rule and the human lead should confirm it. Recommendation: as drafted, for the ratios in section 2.
4. **Energy.** Recommendation: not measured in the first run; the line prints ENERGY NOT MEASURED.
5. **The required counts (4 of 5 draws; 8 of 9 parents), the factor 2 in δ, the tie tolerance and the selection rule for D+.**
6. **Product-key memory as a further alternative** (named in `LITERATURE_AND_ROUTING_NOTE.md` section 2). No sibling draft defines a product-key arm any more: ADR-0024 section 4 removed it and places it in Stage B of the routing work, and no Stage B study exists. It could enter S4 only as an arm that such a study had defined and qualified; adding it here would mean designing a new architecture inside S4. Recommendation: not included; revisit only if a Stage B study is approved and completed.
7. **ADR-0026's open choice 13** (does a qualifying label still qualify when D-ADAPT's FRESH convergence tag is NOT CONVERGED). Route A follows the ruling; this ADR makes no recommendation of its own beyond ADR-0026's.
8. **Route A's budget when convergence is not reached within 19,064 updates.** As written the outcome is S4 NOT EVALUABLE. The alternative is a stated bound: B\* is the B\*-defining arm's computation at ADR-0026's U\* = 16,384 updates, and every label carries "AT FIXED DURATION; NOT AT CONVERGENCE". Recommendation: keep NOT EVALUABLE as the registered rule and decide the alternative only at the entry decision, before any S4 calibration run.
9. **The quiet-load ceiling of 1.0** (section 8), and the windows for quiet sessions.
10. **The entry decision**, the hour cap, and the approval of the revised specification.

## 12. What a later revision must fix before a freeze

The rate grid and D+ grid; the search length; the convergence rule and, on Route B, the training-length ceiling; the reference-check tolerance; the CV rule; seeds inside each registered set; the frozen-input set; the hour cap after rehearsal. Route A only: the two calibration parents; the panel identities and their ledger entries; the registry entry for sets d = 6..9. Fixed already and not reopened: the entry labels, the replicate units and counts, the label rule, the combination table and its premise, the δ floors, B\*'s definition, the selection rule for D+, the quiet-load ceiling, Route A's data bound.

## 13. Engineering requirements carried from P10

- The frozen-input set is listed file by file at the freeze. Status and run notes go to a notes file outside that set; nothing is committed in the frozen worktree during a run. Every stage is resumable; PAUSED continues; completed cells are not recomputed.
- Every registered stage, including isolated timing and the report, is rehearsed end to end against the frozen plan itself before Decision 2.
- Every reading rule is in the specification (section 5). The reference arm is run through every validity check in rehearsal; a check it fails is not used. The analysis, including descriptive sections, is tested on a synthetic registry with known answers, one for each row of the combination table.
- No count gate on generated data; "generate until met, within a stated budget".
- Platform of record: the research machine (macOS 27.2.1, arm64, CPython 3.12.14, torch 2.8.0, as in the throughput supplement's environment record). Bit-exact assertions are made on it only. Checks (`ruff`, `mypy`, `pytest`) run locally; GitHub CI is not relied on.
- Delegated work records the model that ran it from session metadata. Implementer and auditor work in separate contexts.

## 14. What S4 cannot establish

- Efficiency, speed, latency or energy advantage of a system; storage I/O behaviour (ADR-0028).
- That MC-A is the true cost of a sparse memory: it omits selection and memory-bound work.
- Anything on another backbone, a trainable large model, or against LoRA; that memory beats fine-tuning in general.
- That memory works without an oracle, where the entry route was oracle-addressed; value beyond a lookup where `LOOKUP SUFFICIENT ON THIS TASK` is printed.
- Parity, from NOT SEPARATED AT MARGIN. That an alternative outside the registered list would not do better.
- Any statement beyond the tested task, sizes and budget; any project-level claim.

## 15. Review record

Independent review by the `arbor-auditor` subagent (Claude Opus 5.5): `docs/reviews/p10-i-spec-reviews-2026-11-17/REVIEW_ADR-0027_ADR-0028.md`, verdict NOT READY (1 blocking, 12 required, 7 advisory). This revision is by the lead (Claude Fable 5.2). It has not been re-reviewed. Neither is Astra review or human approval.

| Finding | Severity | Disposition | Where |
|---|---|---|---|
| A-B1 analytic matching and the disagreement rule | BLOCKING | FIXED | §1, §2, §5 (measures, combination table, reason), §11 item 3, §14 |
| A-R1 B\* not computable | REQUIRED | FIXED | §5 "Order of work", "Primary budget" |
| A-R2 conversion to measure 2 | REQUIRED | FIXED | §5 MC-T, B\*_T |
| A-R3 snapshot shortfall | REQUIRED | FIXED | §5 "Snapshots" |
| A-R4 KV's role | REQUIRED | FIXED (the qualifier; the choice is the lead's, open to the human lead) | §4, §5 "Lookup qualifier" |
| A-R5 quantifier order | REQUIRED | FIXED (joint reading) | §5 "Replicate rule" |
| A-R6 D+ search budget | REQUIRED | FIXED | §4 "Search" |
| A-R7 MEMORY MATCHES | REQUIRED | FIXED (renamed; no equivalence label) | §1, §5, §14 |
| A-R8 δ estimator | REQUIRED | FIXED; 4 of 5 and factor 2 left PENDING LEAD REVIEW | §5 "δ", §11 item 5 |
| A-R9 Route B | REQUIRED | FIXED with ADR-0024's names; the routing clause dropped with the reason | §3 |
| A-R10 search boundary | REQUIRED | FIXED | §4 "Search", §9 |
| A-R11 quiet block | REQUIRED | FIXED | §8, §9 |
| A-R12 unclassified limits | REQUIRED | FIXED | §9 table |
| A-A1 wording of the P10-S1 lesson | ADVISORY | FIXED | §2 |
| A-A2 parameter range; LoRA reason | ADVISORY | FIXED | §4 |
| A-A3 "idles at 1.0–1.2" | ADVISORY | FIXED (removed) | §8 |
| A-A4 reading of "P10-S1" | ADVISORY | FIXED | §3 |
| A-A5 RAM and stored bytes | ADVISORY | FIXED | §6 |
| A-A6 core placement, power | ADVISORY | FIXED | §8 |
| A-A7 product-key memory | ADVISORY | ANSWERED: reserved, with a recommendation | §4, §11 item 6 |
| A.4 missing NOT EVALUABLE cases; scope sentence on labels | — | FIXED | §9, §1, §4 |

**Confirmation review** by the `arbor-auditor` subagent (Claude Opus 5.5): `docs/reviews/p10-i-spec-reviews-2026-11-17/REVIEW2_ADR-0027_ADR-0028.md` (NOT READY: 1 blocking, 8 required, 5 advisory) and the stale references listed in `REVIEW2_ADR-0024_ADR-0029.md` section E. Revision 3 is by the lead (Claude Fable 5.2), against the sibling texts on disk at the time. It has not been re-reviewed. Rows above keep their first-review dispositions; where the confirmation review reopened one, the row below governs.

| Finding | Severity | Disposition | Where |
|---|---|---|---|
| S4-N1 Route A names labels ADR-0026 does not have; pre-decides open choice 13 | BLOCKING | FIXED: ADR-0026 section 12's names; the ruling on choice 13 is followed, not made | §3, §11 item 7 |
| S4-N2 F-OQ-IVF could qualify | REQUIRED | FIXED: only F-OQ or T-OQ, as ADR-0024 section 9.3 now states | §3 |
| S4-N3 Route A not specified: unit, panels, data ceiling, seeds | REQUIRED | FIXED: nine parents × three seeds, 8 of 9; panel ledger rule; 19,064-update bound with NOT EVALUABLE; seed roles | §5, §7, §9, §11 item 8, §12 |
| S4-N4 negative without measured cost rests on an unstated premise | REQUIRED | FIXED: premise checked on rehearsal figures; otherwise COST MEASURE MISSING | §5 |
| S4-N5 quiet-load figure had no ceiling | REQUIRED | FIXED: 1.0, with the reason; rehearsal figures define B\*_T | §5, §8, §9 |
| S4-N6 calibration runs to B\*; "median of two" | REQUIRED | FIXED | §5 |
| S4-N7 D+ selection rule; architecture edge | REQUIRED | FIXED; rule PENDING LEAD REVIEW | §4, §9 |
| S4-N8 seeds against the registry | REQUIRED | FIXED: registry values, roles and counts; 2701–2799 withdrawn | §7 |
| X2–X5, X7 section numbers, four readings, the cell, ADR-0029 | REQUIRED | FIXED, re-checked against the third drafts (STORE NOT BEHIND now needs four readings, not three) | §3, §5 |
| A-A7 / X6 product-key memory | ADVISORY | ANSWERED anew: no sibling defines it; not an arm; reserved | §4, §11 item 6 |
| S4-N9 naming every alternative; direction of "ahead" | ADVISORY | FIXED | §1, §5 |
| S4-N10 δ judged | ADVISORY | FIXED (the overstatement is stated) | §5 |
| S4-N11 "per update" for cumulative figures | ADVISORY | FIXED | §2 |
| S4-N12 / X9 the two readings of "P10-S1" | ADVISORY | FIXED | §3, §11 item 2 |
| S4-N13 precedence of NOT EVALUABLE | ADVISORY | FIXED | §9 |

`Astra review: NOT_PERFORMED`.
