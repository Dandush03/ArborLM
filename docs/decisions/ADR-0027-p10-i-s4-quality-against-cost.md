# ADR-0027 — P10-I-S4: quality against computational cost (conditional specification)

**Status: DRAFT — CONDITIONAL — NOT APPROVED. Nothing under this ADR is implemented, calibrated, frozen or run. Entry requires a separate decision by the human lead.**

- Date: 2026-11-17 UTC. Drafted by the lead (Claude Fable 5.2) under `docs/reviews/p10-i-direction-2026-11-17/DIRECTION.md` sections 2 to 5 and 8.
- `Astra review: NOT_PERFORMED`. Claude review is not Astra review. **SPEC: PENDING ASTRA REVIEW.**
- Kind of document: a conditional specification. It fixes the entry criterion, the question, the primary comparison, the verdict labels, the stop rules, the cost ceilings and what is reserved for the human lead. It does not fix every parameter. Section 12 lists what a later revision must fix before a freeze. Approval of the P10-I programme does not authorize this study.
- P1 to P10 code, records, thresholds, seeds and outcomes are immutable. Nothing here revises or reopens them. ArborLM is unproven research; no label below is a success claim for the project.

## 1. Question and outcome meanings

At matched training computation, is the quality of the memory at least that of strong, individually optimised alternatives on the same task, data and frozen backbone?

| Outcome | Meaning |
|---|---|
| MEMORY AHEAD AT MATCHED COMPUTE | On the tested task, backbone and budget, the memory arm's quality exceeds the best alternative's by the registered margin. Nothing about wall time, latency, energy, RAM or storage follows. |
| MEMORY MATCHES AT MATCHED COMPUTE | Neither is ahead by the margin. Not an advantage. |
| ALTERNATIVE AHEAD AT MATCHED COMPUTE | A dense or other alternative is the better use of the same computation on this task. A registered negative result. |
| COST-MEASURE DEPENDENT | The label differs between the two measures of training computation (section 5). Inconclusive. |
| S4 NOT EVALUABLE (reason) | A validity condition failed (section 9). Not negative, not positive. |

Each secondary axis (section 6) has its own line. No line substitutes for another, and no combination of lines is a label.

## 2. Background: registered findings

| Finding | Record |
|---|---|
| P4: at 512 updates and 198,401 trainable parameters the dense adapter beat memory in 27 of 27 comparisons | `results/p4-2026-11-12/`, as summarised in `DIRECTION.md` section 4 |
| P10-S1 capacity CAPACITY-INCONCLUSIVE; efficiency EFFICIENCY-NEGATIVE (DENSE FASTER); F-OQ and H8 DENSE AHEAD; DENSE HOLDS MORE AT SATURATION for F-OQ, F-OQ-IVF and T-OQ; DICT DOMINATES ON THIS TASK; no line positive for the store | `results/p10s1-run-2026-11-17/OUTCOME.md` section 2, `ACCEPTANCE.md` |
| Mean a_use at 32K facts / 16K slots at the run length: T-OQ 0.697, F-OQ 0.992, D-OQ 0.999 | `OUTCOME.md` section 4 |
| At 8K/16K the two cost measures disagree: D-OQ's cost to reach the level is 0.27–0.38 of T-OQ's in measured CPU seconds and 1.32–1.87 of it in analytic multiply-adds; the any-cell combination rule was unregistered | `ACCEPTANCE.md` ruling 2 |
| Audit observation, descriptive: at matched compute F-OQ is ahead of D-OQ at 32K/16K by 0.24–0.33 bits in 5 of 5 replicates, while DENSE AHEAD holds at matched updates and at D-OQ's best snapshot | `OUTCOME.md` section 4, finding 4 |
| Memory arms ran at learning rate 0.003, untuned by design; D-OQ at its calibrated rate | `OUTCOME.md` section 4 |
| Supplementary read-path throughput (descriptive, in RAM, enters no line): T-OQ about 10,100 queries/s at batch 1 from 1,024 to 16,384 slots; F-OQ 19,177 → 7,292; D-OQ 107,879 → 16,768 | `results/p10s1-run-2026-11-17/supplement/throughput_supplement.json` |
| Backbone: frozen, byte-level, 27,392 parameters, context 64 | `docs/decisions/ADR-0021-p10-s1-useful-capacity-scaling.md` section 2 item 10; `ADR-0009` |

Two lessons shape this draft. First, P10-S1 compared a tuned dense control with untuned memory arms; S4 optimises every arm under one rule. Second, P10-S1's efficiency line was decided by an unstated rule over cells and by which cost measure was read; S4 names one primary budget and treats disagreement between cost measures as its own label.

## 3. Entry criterion

Entry is a decision by the human lead. The lead may propose entry only if the following condition, computed from registered and accepted outcomes, is true.

**ENTRY = A or B**, and the route taken fixes the task of S4.

- **Route A (P10-I-S3, ADR-0026).** Both of S3's outcome lines at its primary checkpoint: (A1) the dependence-on-memory line is registered positive; and (A2) the competitiveness line against the dense adapter is registered positive or registered as within S3's own margin. A negative or inconclusive A2 fails Route A. S4 then runs on S3's task and data.
- **Route B (P10-I-S1, ADR-0024).** For one and the same memory arm at one and the same cell: (B1) a positive capacity label; (B2) no label that places the dense control ahead of that arm at matched compute or at matched updates; (B3) the dependence check passed at every snapshot the labels use; and (B4) if the arm is sparse (tree or indexed), the routing-quality lane's registered retention condition is met. S4 then runs on S1's task, and every S4 label carries `STORE ONLY; ORACLE-ADDRESSED` wherever addressing was supplied by an oracle.

The exact label names are those of ADR-0024 and ADR-0026 as approved. The revision of this ADR that precedes the entry decision replaces the descriptions above by those names, without changing their meaning. Descriptive figures, audit observations and intermediate checkpoints never satisfy a clause.

**P10-S1's registered outcome does not meet this criterion.** No line is positive for the store, the capacity line is inconclusive, the efficiency line is negative, and F-OQ and H8 are DENSE AHEAD. The matched-compute observation at 32K/16K is an audit finding, not a registered label, and does not count. P4 does not meet it either. On today's records S4 may not be entered.

## 4. Arms and the question of a meaningful alternative

One memory arm enters: the arm that satisfied the entry route, unchanged in architecture.

| Arm | What it isolates | Standing |
|---|---|---|
| M: the qualifying memory arm | The subject | Required |
| D: dense adapter at equal stored parameters (the family that led in P4 and P10-S1) | Memory structure against an unstructured dense map | Required |
| D+: best dense adapter over a registered width and depth grid | Whether D is a weak representative of dense | Required |
| FT: the backbone unfrozen and trained, no addition | Whether any addition is needed at this scale | Required on the 27,392-parameter backbone |
| KV: dictionary or nearest-neighbour lookup where the task admits one | Value a plain lookup already provides (P10-S1: DICT DOMINATES) | Required where defined; reported beside the label, and a memory label is never read without it |
| LoRA | Low-rank adaptation of a large frozen model | See below |

**LoRA.** LoRA is an alternative to full fine-tuning when the backbone is too large to train in full. Here the backbone has 27,392 parameters; every memory and dense addition in P10-S1's cost table has more trainable parameters than the whole backbone (33,793 to 1,049,601, `RESULTS.md`). Full fine-tuning (arm FT) is cheap and is the honest form of that alternative. A low-rank restriction of weight matrices this small saves nothing that matters and would be a weak baseline dressed as a strong one. LoRA on this backbone is therefore **NOT APPLICABLE**, and the report says so in those words.

A comparison with LoRA is meaningful only on a backbone large enough that full fine-tuning is a real cost. That is a different study configuration: it needs a larger pretrained backbone (possibly a download), a new qualification of the memory on that backbone, and its own approval. This document does not authorize it. Whether a larger backbone is a precondition for S4 is reserved (section 11, item 1). Without it, S4's scope sentence is fixed: "one frozen 27,392-parameter backbone; alternatives are dense additions and full fine-tuning; no statement about adaptation of a large model".

One change per comparison: M against each alternative separately, same data draws, same panels, same budget. Every arm, including M, gets the same optimisation search (learning rates, and for D+ the grid) on calibration draws only, with the same number of search cells per arm.

## 5. Primary comparison and label rule

- **Quality.** The task's registered quality measure from the entry route (S3's primary measure, or S1's usefully-retained accuracy), on both evaluation panels.
- **Training computation, measure 1 (matching variable).** Analytic multiply-adds of whole training updates, including the frozen backbone's forward and backward pass and the optimiser, by a formula checked against a counted run (as ADR-0021 section 22 M6).
- **Training computation, measure 2 (concordance).** Measured CPU seconds of training, single process, thread counts fixed, on a quiet stage (section 8).
- **Primary budget B\*.** One budget, fixed at the freeze from calibration draws: the computation at which the strongest alternative meets the registered convergence rule. Every arm is read at the last snapshot whose cumulative computation is at most B\*. Other budgets are descriptive.
- **Replicate rule.** Five fresh data draws. A replicate favours M only if both panels show M ahead by margin δ; it favours an alternative if either panel shows the alternative ahead by δ (the asymmetric rule of ADR-0021 section 22 (h)).
- **Label under one measure.** MEMORY AHEAD if at least 4 of 5 replicates favour M against every required alternative. ALTERNATIVE AHEAD if at least 4 of 5 replicates favour any one alternative. Otherwise MEMORY MATCHES.
- **Combination.** The label is computed under measure 1 and again with B\* converted to measure 2. If the two labels are equal, that is the outcome. If they differ, the outcome is COST-MEASURE DEPENDENT and both are printed. If measure 2 is NOT MEASURED (machine not quiet), the outcome is S4 NOT EVALUABLE (COST MEASURE 2 NOT MEASURED).
- **δ** is fixed by the later revision from calibration: at least twice the between-seed standard deviation of the quality measure on calibration draws, with a floor stated before observation. It is not taken from a paper and is never changed after the freeze. The figure 4 of 5 requires more than a bare majority of five draws; it is a proposal for the review.

Matching on analytic computation makes this a statement about quality at an equal budget. It is not a statement that either arm is faster or cheaper. No advantage is inferred from parameter counts, active parameters, rows read or any other logical count.

## 6. Secondary axes, each reported separately

| Axis | How measured | If the condition fails |
|---|---|---|
| Training wall time | Quiet isolated stage, medians over repeats, CV rule | WALL TIME NOT MEASURED |
| Inference latency and throughput | Quiet isolated stage, batch 1 and one larger batch | LATENCY NOT MEASURED |
| Energy | Needs administrator access (`powermetrics`); the lead does not have it | ENERGY NOT MEASURED unless the human lead runs or authorizes it (section 11, item 4) |
| Peak RAM | Process peak resident memory per arm | Always measured |
| Stored bytes | Bytes of the checkpoint on disk, counted | Always measured |

Each axis is printed per arm with its own table. There is no composite score and no sentence that combines axes with the primary label. Storage here means checkpoint size; physical storage I/O belongs to ADR-0028.

## 7. Data, seeds, sizes, checkpoints

- Task, data and sizes are those of the entry route. Five registered draws plus two calibration draws, all fresh.
- Proposed seed namespace **270001–279999** (data and derived seeds), initialisation seeds 2701–2799. A scan of `configs`, `studies`, `src` and `docs/decisions` in the p10-i-design worktree found no seed in 270000–289999. A gate at the freeze asserts disjointness from every earlier study (the list of ADR-0021 gate G9, plus P10-S0 200001–209999, P10-S1's seeds as ADR-0021 section 6 lists them, P10-S2 220001–229999) and from ADR-0023 to ADR-0026 and ADR-0028, whose namespaces this drafter could not read.
- Snapshots on a fixed grid for every arm; only the snapshot at B\* enters a label.

## 8. Stages

| Stage | Quiet machine | Notes |
|---|---|---|
| Rehearsal and calibration (calibration draws only) | No, except its timing block | Measures cost per update per arm, convergence, between-seed SD; fixes B\*, δ, rates |
| Freeze, Decision 2 by the human lead | No | |
| Training, evaluation | No | Resumable per cell; no wall-time comparison is read from this stage |
| Isolated timing (measure 2, wall time, latency) | Yes: about 1 to 2 hours, estimate | 1-minute load average at most a figure fixed at the freeze (the machine idles at 1.0–1.2), checked before and after each block; a block that fails is repeated at most twice, then recorded NOT MEASURED |
| Analysis, report, independent recomputation | No | |

The machine is the human lead's working computer. The quiet stage is scheduled with the human lead.

## 9. Limits, stop rules, NOT EVALUABLE

| Limit | Kind | Rule |
|---|---|---|
| Total charged time, proposed 60 hours | Resource cap | Extendable on cost projection only, never on outcome values; a stop is PAUSED and resumable; every planned cell still runs |
| Memory guard per process | Resource cap | As above |
| Search cells per arm, snapshot grid, number of draws (5) | Design ceiling | Fixed at the freeze; equal across arms |
| Training length | Design ceiling | Set by the registered convergence rule; extended only by that rule, within the hour cap |
| δ, 4 of 5, both-panels rule, concordance rule | Scientific threshold | Never relaxed after observation |

Stop rules: the study stops and returns to the human lead if the entry condition is found not to hold at the freeze; if the rehearsal projects more than the cap; or if any gate fails. S4 NOT EVALUABLE is recorded when: the reference check fails (the arm that satisfied entry does not reproduce its entry-route behaviour on calibration draws within the registered tolerance); an alternative's search ends at a boundary of its grid (the alternative is not shown to be optimised); measure 2 is not measured; or fewer than five replicates complete after resumption. No limit is extended because a partial result looks close.

## 10. Cost projection (estimate; replaced by the rehearsal)

P10-S1 charged 49,251.2 s for 178 training cells and 1,899.0 s for 1,866 snapshot evaluations (`OUTCOME.md` section 1), about 277 s per training cell on average. S4 on the existing backbone is about 5 arms × 5 draws = 25 registered cells plus about 40 to 80 search cells. At P10-S1's average cost per cell this is of the order of 5 to 10 hours, and several times that if the route is S3 with long runs; the proposed 60-hour cap leaves room for that and is itself to be replaced. The rehearsal measures cost per update per arm, the convergence length and the search size, and replaces this figure. On a larger backbone no estimate can be made from the records.

## 11. Reserved for the human lead

1. **Backbone.** Run S4 on the 27,392-parameter backbone with LoRA NOT APPLICABLE, or make a larger backbone a precondition. Recommendation: the small backbone first, with the fixed scope sentence; a larger backbone is a separate specification, approval and, if needed, download decision.
2. **Route B alone.** Whether a positive P10-I-S1 result under oracle addressing justifies S4 without Route A. Recommendation: no; wait for Route A, because a plain lookup dominated P10-S1's task.
3. **Matching variable.** Analytic multiply-adds with measured CPU seconds as concordance (this draft), or the reverse. Recommendation: as drafted; analytic counts are reproducible, and the concordance rule prevents a label that only one measure supports.
4. **Energy.** Not measured, or measured by the human lead with administrator access. Recommendation: not measured in the first run; the line prints ENERGY NOT MEASURED.
5. **The entry decision itself**, the hour cap, and the approval of the revised specification.

## 12. What a later revision must fix before a freeze

The label names of the entry routes; the task and quality measure; the list and grids of alternatives; the convergence rule and B\*; δ and its floor; the reference-check tolerance; the quiet-machine load figure and CV rule; the snapshot grid; seeds; the frozen-input set; the hour cap after rehearsal.

## 13. Engineering requirements carried from P10

- The frozen-input set is listed file by file at the freeze. This ADR's status and run notes are written to a separate notes file outside that set; nothing is committed in the frozen worktree during a run. Every stage is resumable; PAUSED continues; completed cells are not recomputed.
- Every registered stage, including isolated timing and the report, is rehearsed end to end against the frozen plan itself before Decision 2.
- Every reading rule is in the specification, including how panels, replicates, alternatives and the two cost measures combine (section 5). The reference arm is run through every validity check in rehearsal; a check it fails is not used. The analysis, including descriptive sections, is tested on a synthetic registry with known answers.
- No count gate on generated data; where data are generated, "generate until met, within a stated budget".
- Platform of record: the research machine (macOS 27.2.1, arm64, CPython 3.12.14, torch 2.8.0, as in the throughput supplement's environment record). Bit-exact assertions are made on it only. Checks (`ruff`, `mypy`, `pytest`) run locally; GitHub CI is not relied on.
- Delegated work records the model that ran it from session metadata. Implementer and auditor work in separate contexts.

## 14. What S4 cannot establish

- Efficiency, speed, latency or energy advantage of a system; storage I/O behaviour (ADR-0028).
- Anything on another backbone, a trainable large model, or against LoRA where LoRA was NOT APPLICABLE.
- That memory works without an oracle, where the entry route was oracle-addressed.
- That an alternative outside the registered list would not do better.
- Any statement beyond the tested task, sizes and budget; any project-level claim. Milestone questions stay as registered.

`Astra review: NOT_PERFORMED`.
