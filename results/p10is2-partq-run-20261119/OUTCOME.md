# P10-I-S2 Part Q — record of registered attempt 2 (2026-11-19)

Written by the lead (Claude Fable 5.2). **The attempt stopped without a result. Nothing here says anything about the teachers, the memory or transfer.** No line of ADR-0025 is derived. `Astra review: NOT_PERFORMED`. Claude review is not Astra review.

## What happened

Freeze commit `55017df4616a81795918e21e0792fa742f77bdc4`; Decision 2 `results/p10is2-partq-freeze-20261119/DECISION_2_PARTQ.md` (taken by the lead under the human lead's delegation). Run directory `experiments/P10IS2-Q-registered2-20261118` (git-ignored). Local times, 2026-11-19:

| Stage | Ended | Status |
|---|---|---|
| inputs | 07:21 | COMPLETE |
| partition | 07:28 | COMPLETE |
| qfit | 07:41 | COMPLETE |
| qcheck | 07:49 | COMPLETE |
| generation | 14:25 | COMPLETE (23,773 s charged) |
| regeneration | 14:34 | COMPLETE; the regeneration identity check passed |
| outputs | 14:47 | **STOPPED: registered test stop** — "tokenization test (a) on the R-gloss-icl prompts: 1 mismatches (zero required)" |
| analysis | 14:48 | REFUSED by the code: "stage 'analysis' needs 'outputs' to be complete first" |

The failing prompt is E_A/A "ill wait till 230": 3,000 prompts were checked (D_cal/A 500, D_cal/B 500, E_A/A 1,000, E_B/B 1,000), one differs (`records/gloss_test.json`).

## Status

Read strictly, ADR-0025 makes this **QUALIFICATION-ENGINEERING-FAILURE** (a failed gate on study-produced data: sections 4.4 row 1 and 15): no line is derived, Part T does not start, and a further attempt is the human lead's decision. The frozen code recorded the failure (`records/engineering_failures.json`) but wrote no label, because its analysis stage refuses without a completed `outputs` stage; by the specification the row-1 label is derived by rule, so that refusal is a code defect, recorded here.

The independent reading (`audit/STOP_P10IS2_PARTQ_ATTEMPT2.md`, arbor-auditor subagent, Claude Opus 5.5) adds that the human lead may instead rule it a stop on a defect of the specification with no outcome registered. **Which of the two it is recorded as is PENDING THE HUMAN LEAD.** Either way it is not a result about teacher quality.

## The cause (the auditor's finding, reproduced with its own tokenizer code)

The R-gloss-icl template stores each gloss line as separate token segments: a newline, then the next source word with a leading space. The student's tokenizer splits digits out first, so when a source word that begins with a digit is not on the first line, the newline and the space fuse into one token in the real text, while the stored segments give them separately. Words beginning with a letter are unaffected. Over every prompt the study would build, exactly one is affected. It is a defect of the specification's template, written by the lead's drafter and approved under the delegation; it is not a property of the teachers or the data.

## Could it have been caught

Not by the rehearsals as run: they share one set of rehearsal-seed panels, which contain no digit-initial source word; the registered E_A set has one. The code path was the same in rehearsal and in the registered run. A unit test of the newline-then-digit boundary, needing no data, would have caught it before the freeze. No audit and no check of the lead's tested that boundary. That omission is the lead's and the auditor's.

## What is valid, and the seal

- Six stage records are COMPLETE, in registered mode, each within its cap (`records/stages/`).
- Charged: attempt 2, 26,804.0 s (7.45 h); with the 15,832.8 s charged before the freeze the Part Q total is 42,636.8 s (11.84 h) of the 15.15 h cap (`records/charged_ledger.json`).
- **The qualification values were not read.** Sections 8.6 and 15 forbid reporting results under row 1. The lead opened, of this run directory, only: `engineering_failures.json`, `outputs/gloss_test.json`, the stage completion records, `charged_ledger.json` and directory listings. The auditor states what it read in its report and that it did not open the Q_check counts or pool sizes. Nobody is known to have opened `qfit/`, `qcheck/` or `generation/`.
- Registered seeds 250901–250914 were consumed.

## Defects found, for any further attempt

1. The template's segment rule (above): needs an amendment of ADR-0025. The auditor's proposal: store the newline together with the next line's source word, or tokenize each whole line at once. Test (a) stays as registered; dropping digit-initial words or changing the test would alter what was registered.
2. The analysis stage must derive the row-1 label after a recorded engineering failure.
3. The registered cap check ignores the charge before the freeze (it would have allowed 54,540 s where the rule allows 38,707 s; it did not matter in this run).
4. A unit test of the template on a newline-then-digit boundary.

## For the human lead

1. How this attempt is recorded: QUALIFICATION-ENGINEERING-FAILURE as the ADR reads strictly, or a stop on a specification defect with no outcome registered.
2. Whether a third attempt is made, with the amendment of item 1.
3. If so, whether the six completed stages of this attempt are reused under a new freeze (verified by hash, with the regeneration check repeated; the ADR has no rule for carrying records across freezes, so this needs his ruling) or redone with the same seeds (about 7.4 charged hours; new seeds would be a re-draw after an observed stop and are not proposed).

Attempt 1 (refused at `inputs` after 13 s) and every rehearsal are kept, as recorded in the two Decision 2 files.
