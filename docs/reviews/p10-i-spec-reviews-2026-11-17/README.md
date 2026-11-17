# P10-I draft specifications — status and review trail (2026-11-17 UTC)

**Nothing here is approved. Nothing under P10-I is implemented, calibrated, frozen or run.** Each specification needs the human lead's approval before any implementation or rehearsal, and a second decision before any registered run. `Astra review: NOT_PERFORMED`. Claude review is not Astra review.

Written by the lead (Claude Fable 5.2). Drafts by `arbor-lead` subagents (Fable 5.2); reviews, the seed registry and its checker by the `arbor-auditor` subagent (Opus 5.5), as recorded in session metadata.

## 1. What exists

| Document | Study | Lines | Draft | First review | Confirmation review | State |
|---|---|---|---|---|---|---|
| `docs/decisions/ADR-0023-p10-i-s0-addressing-and-overload.md` | P10-I-S0 | 482 | 3 | NOT READY (2 blocking) | NOT READY (no blocking; 3 required) | Third draft applies them; not re-reviewed |
| `docs/decisions/ADR-0024-p10-i-s1-capacity-scaling.md` | P10-I-S1 (capacity only) | 476 | 3 | NOT READY (2 blocking) | NOT READY (lane L not specified) | Third draft; lane L marked "to be specified, not approved"; not re-reviewed |
| `docs/decisions/ADR-0025-p10-i-s2-sequential-teacher-transfer.md` | P10-I-S2 | 515 | 3 | NOT READY (2 blocking) | NOT READY (no blocking; lead's decisions needed) | Third draft applies them; not re-reviewed |
| `docs/decisions/ADR-0026-p10-i-s3-longer-training.md` | P10-I-S3 | 483 | 3 | NOT READY (1 blocking) | READY AFTER THE LISTED EDITS | Edits applied; not re-reviewed |
| `docs/decisions/ADR-0027-p10-i-s4-quality-against-cost.md` | P10-I-S4 (conditional) | 279 | 3 | NOT READY (1 blocking) | NOT READY (1 blocking, cross-references) | Third draft against the final siblings; not re-reviewed |
| `docs/decisions/ADR-0028-p10-i-s5-physical-ssd-memory.md` | P10-I-S5 (conditional) | 282 | 3 | NOT READY (1 blocking) | NOT READY (no blocking; 5 required) | Third draft against the final siblings; not re-reviewed |
| `docs/decisions/ADR-0029-p10-i-r-routing-diagnosis.md` | P10-I-R (new) | 387 | 2 | (as part of ADR-0024) | NOT READY (1 blocking) | Second draft applies it; not re-reviewed |
| `../p10-i-direction-2026-11-17/CLOSURE_LEDGER.md` | P1–P10 | 176 | 1 + alignment | not reviewed as a document | cross-checked by the ADR reviews | Proposal for approval |
| `../p10-i-direction-2026-11-17/SEED_REGISTRY.md` | all | — | revision 3 | written by the auditor | checker passes | Proposal for approval |

Every review found real defects, and no third draft has been read by a reviewer. The honest state is: **reviewed twice, revised three times, last revision unreviewed.** A third review round is the lead's recommendation only for ADR-0024, ADR-0029 and ADR-0023, where the last changes were rules and not wording; it is cheaper to do it after the rulings below, since several of them change those rules.

Reviews in this folder: `REVIEW_ADR-*.md` (first round), `REVIEW2_ADR-*.md` (confirmation round). Each ADR ends with a review record: finding, disposition, where.

## 2. What the reviews changed, in one line each

- **ADR-0023:** outcome rules made total; new slot counts need new adapter code (the existing cell check accepts three sizes only); the duration ceiling got a written extension rule; the oracle reference is flagged per condition and a flag at load 1 or 2 returns to the human lead before the freeze.
- **ADR-0024:** cut to capacity; product-key memory and H8 removed; dense reading needs four readings (a relaxation the lead had asked for was reversed); block X conditional, on fresh draws, funded by rule; lane L not specified.
- **ADR-0025:** the human lead's P10 items restored as descriptive lines; the general-quality condition restored; every change from ADR-0022 tabled; measured pool overlap (about 669,900) used; a retention failure can no longer become NOT EVALUABLE.
- **ADR-0026:** the "convergence rule" was a fixed duration in disguise and is now stated as fixed with a tag; a third data regime and a context-free control added; calibration statistics sealed.
- **ADR-0027:** asymmetric cost rule (memory ahead needs both measures; the alternative needs either); entry uses the siblings' real labels; an evaluation-only read can never qualify.
- **ADR-0028:** comparison only at equal recall and equal resident RAM; untested machine behaviour became rehearsal checks; the scientific part stated as not evaluable as capped.
- **ADR-0029:** both checkpoints co-primary; labels claim only what the reads identify; the reproduction gate compares like with like.
- **Seeds:** four of the drafts' own initialization seeds collided with seeds that P4, P8, P9, P9-I and P10-S0 derive; one registry now assigns everything.

## 3. Rulings that shape the programme (the human lead's)

The seven drafts list 72 open choices between them (each ADR's section "Open choices reserved for the human lead"). Most are recommendations to confirm. These twelve change what gets built:

| # | Ruling | Where | Lead's recommendation |
|---|---|---|---|
| 1 | Routing diagnosis as its own ADR-0029, or back inside ADR-0024 as first directed | ADR-0029 §16 item 1; ADR-0024 §21 item 8 | **RULED 2026-11-17: "Keep ADR-0029".** ADR-0024's file was renamed to `ADR-0024-p10-i-s1-capacity-scaling.md` |
| 2 | The departures of ADR-0029 from the next-action table of the note's section 5.2 (side by side in the ADR) | ADR-0029 §16 item 8 | Accept; the reads cannot identify some of the causes the table names |
| 3 | Order of studies | ADR-0029 §16 item 7 | P10-I-R first: about 4–8 charged hours in the draft's estimate, almost all of it reads of existing checkpoints, and it informs ADR-0024 and ADR-0026 |
| 4 | Capacity task unchanged although a dictionary solves it, with every label capped at "necessary condition" | ADR-0024 §21 item 1 | Keep, with the cap; a task a lookup cannot solve is a design problem of its own |
| 5 | The 16,384→65,536 block: in, with a funding figure H_X fixed in advance; or out | ADR-0024 §21 item 2 | In as conditional; H_X = 100 charged hours; cost is unbounded before its rehearsal |
| 6 | Lane L (capacity under learned addressing): specified in a later revision, block M not waiting for P10-I-S0 | ADR-0024 §21 item 3 | As drafted |
| 7 | Dense reading: a dense lead at matched updates or best snapshot alone reads INCONCLUSIVE, not NEGATIVE | ADR-0024 §21 item 4 | The lead is not confident here: this is the one remaining narrowing against ADR-0021 and it favours the store. The stricter alternative is in the ADR |
| 8 | Fixed duration of 16,384 updates with a convergence tag, or a larger corpus first | ADR-0026 §13 item 1 | Fixed with the tag; fresh data ends at 19,064 updates |
| 9 | Third data regime (about 7 hours) or accept the confound | ADR-0026 §13 item 5 | Keep the regime |
| 10 | Whether a qualifying label still qualifies for the cost study when the dense arm is tagged NOT CONVERGED | ADR-0026 §13 item 13; ADR-0027 §11 item 7 | No |
| 11 | Teacher study: restored descriptive lines kept or cut for cost; packages outside the lock; a durable home for the P10-S2 data (now git-ignored in an agent worktree) | ADR-0025 §13 items 3, 6 | Keep the lines; approve the packages for Part Q only; copy the data before any clean-up |
| 12 | The closure ledger's proposals: P9 lanes A and B superseded; ADR-0012; Lane D and sequential addition of facts; appending P10 to the research log | `CLOSURE_LEDGER.md`, reserved list | As listed there; ADR-0012 has no proposal |

Also the human lead's, and not urgent: the conditional studies' entry decisions (ADR-0027, ADR-0028), the SSD write budget, anything needing administrator access, and every hour cap.

## 4. Known weak points the lead wants seen

- Several rules were written knowing P10-S1's data: the dense reading, the checkpoint rule of ADR-0029, the dependence test's constants. Each is disclosed beside its rule. ADR-0029 calls itself a re-analysis and requires a confirmatory read on fresh checkpoints before any claim about cause.
- Cost projections are estimates until each rehearsal: ADR-0023 15–55 hours (to about 75 with load 8); ADR-0024 block M about 19 / 26 / 60 (low / central / upper), block X unbounded; ADR-0025 Part T 20–100; ADR-0026 26–48 including its rehearsal; ADR-0029 about 4–8 (reads of existing checkpoints 2–5, the confirmatory part about 1.5, rehearsal under 1).
- ADR-0025 is 515 lines against a target of 450; the reviewer found no rule that could be cut.
- The seed registry's revision 2 edited its checker in place against the registry's own rule; revision 3 uses a new file and records the hashes.
- The lead's briefs stated that the machine idles at a load of 1.0–1.2. No record says so; the drafts now measure the quiet condition at the stage.
