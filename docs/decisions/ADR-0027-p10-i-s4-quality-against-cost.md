# ADR-0027 — P10-I-S4: quality against computational cost (conditional specification)

**Status: DRAFT — CONDITIONAL — NOT APPROVED. Nothing under this ADR is implemented, calibrated, frozen or run. Entry requires a separate decision by the human lead.**

- Date: 2026-11-17 UTC. Revision 2, after independent review (section 15). Drafted by the lead (Claude Fable 5.2) under `docs/reviews/p10-i-direction-2026-11-17/DIRECTION.md` sections 2 to 5 and 8.
- `Astra review: NOT_PERFORMED`. Claude review is not Astra review. **SPEC: PENDING ASTRA REVIEW.**
- Kind of document: a conditional specification. It fixes the entry criterion, the question, the primary comparison, the verdict labels, the stop rules, the cost ceilings and what is reserved for the human lead. It does not fix every parameter. Section 12 lists what a later revision must fix before a freeze. Approval of the P10-I programme does not authorize this study.
- P1 to P10 code, records, thresholds, seeds and outcomes are immutable. Nothing here revises or reopens them. ArborLM is unproven research; no label below is a success claim for the project.

## 1. Question and outcome meanings

At matched training computation, is the quality of the memory at least that of strong, individually optimised alternatives on the same task, data and frozen backbone?

| Outcome | Meaning |
|---|---|
| MEMORY AHEAD AT MATCHED COMPUTE | Under **both** cost measures, the memory arm's quality exceeds every trained alternative's by the registered margin, on the tested task, backbone and budget. Nothing about wall time, latency, energy, RAM or storage follows. |
| ALTERNATIVE AHEAD AT MATCHED COMPUTE | Under **either** cost measure, a trained alternative is ahead by the margin. A registered negative result. |
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
| Per update at 16,384 slots (8K/16K): analytic multiply-adds T-OQ / D-OQ = 5.21e11 / 2.65e12 = 0.197; isolated CPU seconds per update T-OQ / D-OQ = 0.01156 / 0.01204 = 0.960 (rehearsal timing, descriptive) | `RESULTS.md`, cost table and "Isolated timing" |
| Audit observation, descriptive: at matched compute F-OQ is ahead of D-OQ at 32K/16K by 0.24–0.33 bits in 5 of 5 replicates, while DENSE AHEAD holds at matched updates and at D-OQ's best snapshot | `OUTCOME.md` section 4, finding 4 |
| Memory arms ran at learning rate 0.003, untuned by design; D-OQ at its calibrated rate | `OUTCOME.md` section 4 |
| Supplementary read-path throughput (descriptive, in RAM, enters no line): T-OQ 10,106 to 10,211 queries/s at batch 1 from 1,024 to 16,384 slots; F-OQ 19,177 → 7,292; D-OQ 107,879 → 16,768 | `results/p10s1-run-2026-11-17/supplement/throughput_supplement.json` |
| Backbone: frozen, byte-level, 27,392 parameters, context 64 | `docs/decisions/ADR-0021-p10-s1-useful-capacity-scaling.md` section 2 item 10; `ADR-0009` |

Two lessons shape this draft. First, P10-S1 compared a tuned dense control with untuned memory arms; S4 searches every arm under one rule. Second, P10-S1's efficiency label was decided by an unregistered any-cell rule, and at 8K/16K its two cost measures disagreed (`ACCEPTANCE.md` ruling 2); S4 names one primary budget and writes down how the two measures combine.

## 3. Entry criterion

Entry is a decision by the human lead. The lead may propose entry only if the condition below is true of registered and accepted outcomes. Descriptive figures, audit observations, intermediate checkpoints and tags never satisfy a clause.

**Reading of the direction.** `DIRECTION.md` section 4 says "P10-I-S3 or P10-S1". This draft reads the second as P10-I-S1 (ADR-0024), the successor that carries P10-S1's corrections. `PENDING LEAD REVIEW`. P10-S1 fails under either reading (end of this section).

**ENTRY = A or B.** The route fixes the task and the memory arm of S4.

- **Route A (P10-I-S3, ADR-0026).** Both: (A1) the registered label of line 1 is **DEPENDENT, BOTH REGIMES** or **DEPENDENT, FRESH ONLY**; (A2) the registered label of **COMPETITIVENESS[TREE]** is **COMPETITIVE** or **MEMORY AHEAD**, BOTH REGIMES or FRESH ONLY, with the FRESH regime CONVERGED and no INCONCLUSIVE tag (ADR-0026 sections 6.3 to 6.5 and 12). REPEATED DATA ONLY, NOT COMPETITIVE, INCONCLUSIVE and NOT EVALUABLE fail Route A. COMPETITIVENESS[FLAT] alone does not satisfy it. The memory arm is M-TREE; the task and data are S3's.
- **Route B (P10-I-S1, ADR-0024).** The registered **C-CAPACITY** outcome is **CAPACITY-POSITIVE** (ADR-0024 section 10.3). By that rule an arm is CAPACITY_SUPPORTED and NOT BEHIND DENSE, which already requires a capacity step in every funded transition, the dependence conditions at the snapshots the verdicts read, and STORE NOT BEHIND under both cost readings with the measured one present. So a dense comparison that was not run, was split or was not measured cannot satisfy Route B. Every arm that is both CAPACITY_SUPPORTED and NOT BEHIND DENSE enters S4 as its own memory arm with its own label; none is selected as the best. The cell is fixed in advance: the larger cell of the arm's CAPACITY STEP in the largest funded transition. Every S4 label on this route carries ADR-0024's tags `STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK`.

Two things the first draft asked of Route B are not used, because no sibling draft provides them. There is no cell-level capacity label (ADR-0024's capacity labels are step and arm classes). There is no "routing retention met" label for a Lane C arm: Lane R (R-DIAGNOSIS) is a diagnosis of P10-S1's existing checkpoints and has no pass label. C-EFFICIENCY and R-DIAGNOSIS are not part of the entry condition.

If an entry-route label is renamed or withdrawn between the entry decision and the freeze, the study stops and returns to the human lead.

**P10-S1's registered outcome does not meet this criterion.** No line is positive for the store, the capacity line is inconclusive, the efficiency line is negative, and F-OQ and H8 are DENSE AHEAD. The matched-compute observation at 32K/16K is an audit finding, not a registered label. P4 does not meet it either. On today's records S4 may not be entered.

## 4. Arms and the question of a meaningful alternative

The memory arm M is the arm fixed by the entry route. Its architecture is fixed; only its learning rate is searched.

| Arm | What it isolates | In the label rule |
|---|---|---|
| M: the qualifying memory arm | The subject | Yes |
| D: dense adapter at equal stored parameters (the family that led in P4 and P10-S1) | Memory structure against an unstructured dense map | Yes |
| D+: best dense adapter over a registered width and depth grid | Whether D is a weak representative of dense | Yes |
| FT: the backbone unfrozen and trained, no addition | Whether any addition is needed at this scale | Yes |
| KV: dictionary lookup (ADR-0024's DICT) on Route B; NOT DEFINED on Route A unless the later revision defines one | Value a plain lookup already provides | No: it has no training computation. It gives the qualifier of section 5 |
| PK: product-key memory (ADR-0024's PK-OQ) | A structured sparse memory that is not a tree | Reserved (section 11, item 6) |
| LoRA | Low-rank adaptation of a large frozen model | NOT APPLICABLE (below) |

**Search.** One learning-rate grid, the same for every trained arm, fixed in the revision before calibration. Rates are chosen on calibration draws only, at one fixed search length, by quality at its end. D+ runs that same rate grid at every architecture of its grid, so it gets more search cells than M; the surplus is on the side of the alternative, which is the conservative direction. If a chosen rate lies at an edge of the grid, the grid is extended by one step past that edge, at most twice, within the hour cap.

**LoRA.** On this backbone full fine-tuning (arm FT) contains every solution a low-rank update of the same weights can reach, and costs about the same per update, because both need the backbone's backward pass. LoRA therefore cannot be a stronger alternative than FT here, and adding it would add a weaker baseline, not a stronger one. For scale: the backbone has 27,392 parameters, and the memory and dense arms of P10-S1 have 33,793 to 788,481 trainable parameters (`RESULTS.md` cost table; the reference rung R2, which is neither, has 1,049,601). LoRA on this backbone is **NOT APPLICABLE**, and the report says so in those words. FT with 27,392 parameters is weak by construction on a memorisation task (Route B); a label there is never read as "memory beats fine-tuning".

A comparison with LoRA is meaningful only on a backbone large enough that full fine-tuning is a real cost. That needs a larger pretrained backbone (possibly a download), a new qualification of the memory on it, and its own approval. This document does not authorize it (section 11, item 1). **Scope sentence, printed with every label:** "one frozen 27,392-parameter backbone; alternatives are dense additions and full fine-tuning; no statement about adaptation of a large model".

One change per comparison: M against each alternative separately, same data draws, same panels, same budget.

## 5. Primary comparison and label rule

**Quality.** Route A: mean next-byte NLL in nats per byte (ADR-0026 section 6.1). Route B: i, bits per fact usefully retained (ADR-0024). Both evaluation panels.

**Two measures of training computation** (the cost readings of ADR-0024 section 9.2):

- **MC-A, analytic.** Multiply-adds of whole training updates, including the backbone's forward and backward pass and the optimiser, by the formula of ADR-0021 section 22 M6, checked against a counted run. It counts matrix products and gather-weighted sums. **It omits top-k selection, sorting, index traversal and memory-bound gathers**, so it undercounts what a sparse memory does per update: at 16,384 slots it gives T-OQ 0.197 of D-OQ's cost per update where measured CPU gives 0.960 (section 2). It is used as the first matching variable because it is deterministic and independent of machine load. It is a counted quantity and is never reported as measured cost or efficiency.
- **MC-T, measured.** Single-thread process CPU seconds per update, per arm at its size, median of repeats, from an isolated timing block on a quiet machine (section 8). Cumulative MC-T of an arm at u updates is u times that arm's per-update figure.

**Order of work before the freeze.** (1) Rate search (section 4). (2) Convergence runs at the chosen rates on both calibration draws. (3) B\*.

**Primary budget B\*.** For each of D, D+ and FT, c(arm) is the median over the two calibration draws of the cumulative MC-A computation at which the arm first meets the registered convergence rule. B\* = max of c(D), c(D+), c(FT). KV does not enter. If any of the three does not meet the rule within the training-length ceiling, the outcome is S4 NOT EVALUABLE (B\* NOT DETERMINED). B\*_T, the budget in MC-T, is the update count of the B\*-defining arm at B\* times that arm's per-update CPU seconds. Other budgets are descriptive.

**Snapshots.** Each arm is saved at update counts set per arm, so that its cumulative computation is the largest not exceeding f · B\* (and f · B\*_T) for f in {1/8, 1/4, 1/2, 3/4, 1}. The reading at f = 1 is therefore within one update of the budget for every arm. If one update of an arm exceeds the budget, S4 NOT EVALUABLE (NO SNAPSHOT AT B\*).

**Replicate rule.** Five fresh data draws. A replicate **favours M** only if, on both panels, M is ahead of **every one** of D, D+ and FT by δ in that same replicate (the joint reading). A replicate **favours alternative X** if, on either panel, X is ahead of M by δ. This is the asymmetric rule of ADR-0021 section 22 (h).

**Label under one measure.** M-AHEAD if at least 4 of 5 replicates favour M. X-AHEAD if at least 4 of 5 replicates favour one and the same alternative X. Otherwise NOT-SEPARATED.

**Combining the two measures (asymmetric).**

| MC-A | MC-T | Outcome |
|---|---|---|
| M-AHEAD | M-AHEAD | MEMORY AHEAD AT MATCHED COMPUTE |
| X-AHEAD under either measure, whatever the other, including MC-T NOT MEASURED when MC-A gives X-AHEAD | | ALTERNATIVE AHEAD AT MATCHED COMPUTE (the measure is named) |
| M-AHEAD under one, NOT-SEPARATED under the other | | COST-MEASURE DEPENDENT |
| NOT-SEPARATED | NOT-SEPARATED | NOT SEPARATED AT MARGIN |
| M-AHEAD or NOT-SEPARATED | NOT MEASURED | S4 NOT EVALUABLE (MC-T NOT MEASURED) |

Reason. A label that favours the memory must hold under both measures, because the analytic one omits selection and lookup work and so leans towards sparse arms; a label against the memory needs only one. This follows the direction of ADR-0021 section 5.4, which read an ambiguous pair in favour of the comparator, and agrees with ADR-0024 section 10.2 ("a label that favours the store needs both cost readings, measured"). It differs from ADR-0024 section 10.5, which makes negatives need both readings too; S4 is stricter against the memory because its positive label is the one most open to misuse.

**δ.** δ = max(floor, 2 × s). s is the pooled within-group standard deviation of the quality measure at B\*, over groups (arm, panel), from the two calibration draws × two initialisation seeds. Floors, fixed now: Route A 0.005 nats per byte (the resolution used since ADR-0006 and in ADR-0026); Route B 0.25 bits (the "not behind" margin of ADR-0021 and ADR-0024). The floor carries the weight; s has few degrees of freedom and can only widen δ. The factor 2 and the count 4 of 5 are `PENDING LEAD REVIEW`; under no difference a one-sided 4 of 5 occurs with probability 6/32 = 0.19, which is why the margin and the both-panels rule are also required.

**Lookup qualifier.** Where KV is defined: if KV's quality is at least M's minus δ on both panels in at least 4 of 5 replicates, every S4 label carries `LOOKUP SUFFICIENT ON THIS TASK`, and no label is printed without it. On Route B this adds to the DICT tag already carried.

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

- Task, data and sizes are those of the entry route. Five registered draws and two calibration draws, all fresh; two initialisation seeds on calibration draws.
- Proposed seed namespace **270001–279999**, initialisation seeds 2701–2799. A scan of `configs`, `studies`, `src`, `tests` and `docs/decisions` found no earlier use. Sibling drafts as read on 2026-11-17: ADR-0023 300001–309999 and 3001–3091; ADR-0024 240001–249999; ADR-0025 250001–259999; ADR-0026 initialisation 2601–2691; ADR-0028 280001–289999. A gate at the freeze asserts disjointness from every earlier and sibling study, including derived seeds.

## 8. Stages

| Stage | Quiet machine | Notes |
|---|---|---|
| Rehearsal and calibration (calibration draws only) | Only its timing block | Rate search, convergence, s, per-update MC-T; fixes B\*, B\*_T, δ, snapshot update counts |
| Freeze, Decision 2 by the human lead | No | |
| Training, evaluation | No | Resumable per cell; no time comparison is read from this stage |
| Isolated timing (MC-T confirmation, wall time, latency) | Yes, about 1 to 2 hours (estimate) | See below |
| Analysis, report, independent recomputation | No | |

**Quiet condition, measured at the stage.** No record states what this machine's idle load is (one check exists: 0.998 at the P10-S1 supplement; the reviewer saw about 3 with other sessions running). The rehearsal measures it. A block is quiet if the 1-minute load average, sampled every 10 s over a 60 s window before the block and again at its end, stays at or below a figure fixed at the freeze. Power source, Low Power Mode, thermal state and the thread's quality-of-service class are recorded with every block; a block on battery or in Low Power Mode is not quiet. A block that is not quiet is **PAUSED** and rescheduled with the human lead, in up to three further sessions; only then is the axis NOT MEASURED. A measured per-update figure that differs from the rehearsal's by more than the registered CV rule is MC-T UNSTABLE and is treated as NOT MEASURED.

## 9. Limits, stop rules, NOT EVALUABLE

| Limit | Kind | Rule |
|---|---|---|
| Total charged time, proposed 60 hours | Resource cap | Extendable on cost projection only, never on outcome values; a stop is PAUSED and resumable; every planned cell still runs |
| Memory guard per process | Resource cap | As above |
| Rate grid and D+ architecture grid bounds | Design ceiling | Extended one step past an edge, at most twice, within the hour cap |
| Search length; training-length ceiling; convergence-rule parameters | Design ceiling | Fixed before calibration; training length extended only by the convergence rule |
| Number of draws (5), snapshot fractions | Design ceiling | Fixed at the freeze |
| Rescheduled quiet sessions (3) | Design ceiling | Fixed now |
| Load-average figure; CV rule | Validity threshold | Fixed at the freeze from the rehearsal; not changed after |
| δ floors, factor 2, 4 of 5, both-panels rule, the combination table, reference-check tolerance | Scientific threshold | Never relaxed after observation |

Stop rules: the study stops and returns to the human lead if the entry condition does not hold at the freeze; if the rehearsal projects more than the cap; or if a gate fails. No limit is extended because a partial result looks close.

S4 NOT EVALUABLE, each printed by name: B\* NOT DETERMINED; NO SNAPSHOT AT B\*; MC-T NOT MEASURED (only where section 5's table says so); REFERENCE NOT REPRODUCED (the entry arm does not reproduce its entry-route behaviour on calibration draws within the registered tolerance); ALTERNATIVE RATE AT EDGE (an alternative's rate is still at an edge after two extensions and the label would not be ALTERNATIVE AHEAD); MEMORY RATE AT EDGE (the same for M when the label would be ALTERNATIVE AHEAD); ANALYTIC FORMULA CHECK FAILED; NON-FINITE TRAINING in any arm; PLATFORM CHANGED between stages; FEWER THAN FIVE REPLICATES after resumption.

## 10. Cost projection (estimate; replaced by the rehearsal)

P10-S1 charged 49,251.2 s for 178 training cells and 1,899.0 s for 1,866 snapshot evaluations (`OUTCOME.md` section 1), about 277 s per training cell. S4 on the existing backbone is about 4 arms × 5 draws = 20 registered cells per memory arm, plus about 60 to 120 search and convergence cells. At P10-S1's average cost that is of the order of 6 to 12 hours on Route B. On Route A the runs are S3's lengths and the figure is several times larger; ADR-0026 section 9 holds the per-update costs. The 60-hour cap is a placeholder. The rehearsal measures cost per update per arm under both measures, the convergence length and the search size, and replaces all of this. On a larger backbone no estimate can be made from the records.

## 11. Reserved for the human lead

1. **Backbone.** The 27,392-parameter backbone with LoRA NOT APPLICABLE, or a larger backbone as a precondition. Recommendation: the small backbone first, with the scope sentence; a larger backbone is a separate specification, approval and, if needed, download decision.
2. **Route B alone, and the reading of "P10-S1" in the direction.** Recommendation: Route B alone should not suffice; a plain lookup dominated P10-S1's task.
3. **Cost measures.** MC-A as first matching variable with MC-T required for any label that favours the memory (this draft), or MC-T alone. Measured CPU seconds thus gate the positive label; that is a measured time quantity inside the primary rule and the human lead should confirm it. Recommendation: as drafted, for the ratios in section 2.
4. **Energy.** Recommendation: not measured in the first run; the line prints ENERGY NOT MEASURED.
5. **4 of 5 and the factor 2 in δ.**
6. **Product-key memory as a further alternative** (named in `LITERATURE_AND_ROUTING_NOTE.md` section 2). Recommendation: include on Route B, where ADR-0024 defines PK-OQ; not on Route A, where no sibling defines it.
7. **The entry decision**, the hour cap, and the approval of the revised specification.

## 12. What a later revision must fix before a freeze

The rate grid and D+ grid; the search length; the convergence rule and training-length ceiling; the reference-check tolerance; the load figure and CV rule; KV on Route A, if any; seeds; the frozen-input set; the hour cap after rehearsal. Fixed already and not reopened: the entry labels, the label rule, the combination table, the δ floors, B\*'s definition.

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

`Astra review: NOT_PERFORMED`.
