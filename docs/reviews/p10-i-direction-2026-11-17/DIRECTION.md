# P10-I — direction of the programme (recorded 2026-11-17 UTC)

**Status: DIRECTION RECORDED. This is not a specification.** No P10-I study is drafted, implemented, calibrated, frozen or run. Drafting starts only after P10-S1's registered outcome has been independently recomputed, analysed with the human lead and merged to `main`. Every P10-I study needs the human lead's approval before anything is implemented or run.

This file is a condensed record of a discussion between the human lead and the lead (Claude Fable 5.2) on 2026-11-16 and 2026-11-17 UTC. The human lead asked for a cleaned record instead of a verbatim one. The discussion included a proposal and a follow-up note that the human lead prepared outside this workflow and brought into it; where this record adopts their content, it is the human lead's direction.

## 1. Approval record

The human lead, verbatim, on the sequence, the per-study constraints, the closure ledger and the policy on limits recorded below:

> "agreed and you can clean this conversation to record it as P10-I but still we need to wait for the last results from P10-S1"

On the policy on limits (section 5), the concern as the human lead stated it:

> "another thing that truble me is that we close expiriment due to self impose caps, i think we should expand does caps if we see that it will resolve the expiriment"

Earlier decisions that remain in force: P10-I waits for P10-S1's analysis; P10-S1 is reviewed and merged first; P10-I is planned from the complete change log and from what went wrong in each P10 study (`docs/reviews/p10-design-2026-11-15/HUMAN_DECISIONS_2026-11-15.md`).

## 2. Scope: six studies

The ADR numbers are proposed. None of these ADRs exists.

| Study | Proposed ADR | Question | Drafted as |
|---|---|---|---|
| P10-I-S0 | ADR-0023 | Robust addressing and generalisation, including overload | Full specification |
| P10-I-S1 | ADR-0024 | Useful capacity scaling | Full specification |
| P10-I-S2 | ADR-0025 | Sequential teacher transfer | Full specification |
| P10-I-S3 | ADR-0026 | Longer training of the frozen-backbone memory and its dependence on memory | Full specification |
| P10-I-S4 | ADR-0027 | Quality against computational cost | Short conditional specification |
| P10-I-S5 | ADR-0028 | Physical SSD-backed memory | Short conditional specification |

The outcomes stay separate. No study's result substitutes for another's.

## 3. Sequence

1. Finish P10-S1; recompute its outcome independently; the human lead accepts it as registered; merge it to `main`.
2. Write the closure ledger (section 6).
3. Draft P10-I-S0 to S3 in full, each with a separate independent specification review (Opus 5.5) and fresh seeds.
4. Draft P10-I-S4 and S5 as conditional specifications with entry criteria, stop rules and cost ceilings. Approval of the programme does not authorise either.
5. Return to the human lead: the reviewed specifications, cost projections, dependencies, the closure ledger and every methodological choice reserved for the human lead. Nothing is implemented or run before that approval.

## 4. Constraints per study

### P10-I-S0 — addressing and overload

Background (ADR-0020, accepted outcome): A5-D qualified at 4,096 and 16,384 slots; OVERLOAD NOT QUALIFIED, with A5-D at 8,192 facts on 4,096 slots passing 1 of 10 cells and failing on held-out templates only. S0 tested overload at one load and one fixed training length.

- Training length is set by a preregistered convergence rule from a rehearsal, so that undertraining is not the limiting factor.
- Overload is tested at several loads, so that a failure still locates where addressing breaks.
- The pass threshold is not lowered (0.90 of the oracle reference's accuracy).
- The question is whether overload works when the design is not the limit. A failure is a registered outcome, not a reason to extend further.
- The design waits for P10-S1's result, which bears on how much training loaded regimes need.

### P10-I-S1 and P10-I-S2

Each carries its P10 study's corrections. Their content is decided after P10-S1's analysis and is not recorded here.

### P10-I-S3 — longer training

Background (P4, `results/p4-2026-11-12/`): at 512 updates and 198,401 trainable parameters, memory improved on the frozen baseline in 27 of 27 comparisons, shuffling its values harmed prediction in 27 of 27, and the dense adapter beat memory in 27 of 27.

- A rehearsal on fresh calibration draws sets a preregistered convergence-based duration and one primary checkpoint. 16,384 updates is the proposed minimum, only if the rehearsal and the budget support it.
- P10-S1's update counts are not carried over; the tasks and training conditions differ.
- Intermediate checkpoints are descriptive. They do not replace the primary endpoint.
- Arms with repeated data and arms with fresh data, so that duration, additional unique data and memory-specific learning can be told apart.
- Memory-disabled, value-permutation and addressing controls. Dense baselines get their own rate search at each duration.
- Two outcomes with separate thresholds: dependence on memory, and competitiveness against the dense adapter.
- The whole comparison matrix is budgeted before approval. P4's and P5's results are not revised; S3's 512-update point is a new measurement.

### P10-I-S4 — quality against cost (conditional)

- Entry requires credible evidence from P10-I-S3 or P10-S1 that memory is competitive enough to justify the comparison.
- One primary comparison: quality at matched training computation, against strong optimised alternatives.
- Wall time, inference latency, energy, RAM and storage are reported separately and are not combined into a success claim.
- LoRA is not forced onto a backbone where it is not a meaningful alternative.
- No advantage is inferred from parameter counts or logical retrieval operations.

### P10-I-S5 — physical SSD (conditional)

- Two verdicts, never combined: ENGINEERING SSD PERFORMANCE and SCIENTIFIC NEURAL-MEMORY ADVANTAGE.
- A synthetic large-store benchmark may test real storage behaviour. It is not evidence of useful neural-memory scaling.
- A neural-memory advantage requires qualified access behaviour, sufficient utilisation, fair storage baselines and measured physical I/O.
- Cache verification, a storage-write budget and NOT EVALUABLE outcomes are part of the design.
- No hardware purchase and no large write-intensive benchmark is authorised.

## 5. Policy on limits

Reason: a study should not end because of a limit that was a matter of convenience, when lifting it under a rule written in advance would have answered the question. Two cases from P10 motivate this. P10-S2 stopped on counts only (accepted check items 78 and 22 against 150; pools 7,804 and 2,341 against 8,000) while both teachers passed the quality criteria; the design fixed the amount of generation and then applied a count gate. P10-S0 tested overload at one load and one training length. (P10-S0 was not stopped by its hour cap: it charged 6.09 of 22 hours and ran every planned cell.)

Every P10-I specification classifies each of its limits and states the rule for it before any registered seed is observed.

| Kind | Examples | Rule |
|---|---|---|
| Resource cap | Hour caps, memory guards | May be extended. The decision uses cost projections only, never outcome values, and every planned cell still runs. |
| Design ceiling | Search ceilings, fixed generation sizes, number of draws, training length | May be extended only under a rule written in the specification, for example "generate until the count is met, within a stated budget" or a convergence rule. |
| Scientific threshold | Pass counts, margins, accuracy ratios | Never relaxed after observation. Unchanged from the standing rules. |

Further rules:

1. A stop on a resource cap is labelled PAUSED, not a final outcome, and the run is resumable from where it stopped.
2. A count gate on generated data becomes "generate until met, within a budget" wherever the count is not itself the scientific claim.
3. A completed study is not reopened. Its registered outcome stands, and the unanswered part is carried into the named P10-I successor.
4. No limit is extended because a partial result looks close.

This policy applies to P10-I specifications. It does not amend `AGENTS.md` or any existing ADR, and it relaxes no threshold of P1 to P10.

## 6. Closure ledger (to be written after P10-S1 is merged)

A separate ledger maps every open issue of P8 and P9 to one of: CLOSED AS RECORDED, SUPERSEDED BY a named study, or CARRIED INTO a named study. The original registered status is preserved in every case.

- P8 remains INCOMPLETE; its supplementary results stay separately recorded.
- P9 lanes A to D remain calibration blocked unless each is explicitly superseded.
- P9-I remains NO_INTERFACE_SELECTED for the tested interfaces; natural-query generalisation stays visible as unresolved.
- ADR-0012 (governance) needs its own explicit ruling by the human lead.
- `docs/RESEARCH_LOG.md` is reconciled through P10 by appending, not by rewriting.

No historical result, threshold, seed or outcome is revised.

## 7. Machine load as a validity condition

The research machine is also the human lead's working computer. Each specification states which stages need a quiet machine, for how long, and what is recorded if the condition is not met. Comparisons that depend on wall time are not registered on stages that cannot be isolated.

## 8. Reserved for the human lead

- The ruling on ADR-0012.
- Whether the engineering part of P10-I-S5 may run before a neural memory is qualified at scale.
- Whether energy is measured (on this machine it needs administrator access, which the lead does not have).
- Entry decisions for P10-I-S4 and S5.
- Approval of each specification.

## 9. Objective

Unchanged: demonstrate useful, continuously trainable neural memory that acquires and retains knowledge from several pretrained teachers, scales externally, and in the end gives a measurable advantage when backed by SSD storage. Nothing in P1 to P10 establishes this yet.

`Astra review: NOT_PERFORMED`.
