# P10-I-S2 Part Q — outcome record of registered attempt 3 (2026-11-20 UTC; 2026-11-19 local)

Written by the lead (Claude Fable 5.2). `Astra review: NOT_PERFORMED`. Claude review is not Astra review. **This is a qualification of two teachers and of training material. It is not a transfer result and not a success claim: no student has learned anything from a teacher in this study yet.** Every statement carries the oracle line: oracle-assisted (word-level addresses supplied by rule); lexical translation of short closed-vocabulary sentences, two capabilities of one kind; frozen English student; teacher-only training material verified by measured-precision filter; not autonomous learned memory.

## Registered label (as the frozen code wrote it; `records/qualification.json`)

**TEACHERS-QUALIFIED (DISJOINT DRAWS)** — both teachers pass Q1 to Q4; accepted sources A 24,187 and B 24,796. Part T has not started and may be frozen only after this acceptance and its own Decision 2.

Freeze commit `83595e07da303031a0d3ec840c2c40d6408da756`; Decision 2 `results/p10is2-partq-freeze-20261119-attempt3/DECISION_2_PARTQ.md` (taken by the lead; the human lead approved the third attempt himself: `docs/decisions/ADR-0025-addendum-part-q-attempt-3.md`). Registered stages reuse, regeneration, outputs, analysis: each COMPLETE at first launch, 22:50 to 23:08 local, no pause, no item error, no engineering failure.

**Stages 1 to 6 (inputs, partition, qfit, qcheck, generation, regeneration) were computed under freeze `55017df4616a81795918e21e0792fa742f77bdc4` in registered attempt 2 and reused, not recomputed** (addendum section 4): 25,792 files, each a frozen input by SHA-256, re-hashed at the start and end of every stage; the regeneration identity check was run again in attempt 3 and passed. Same registered seeds; nothing drawn anew. Attempt 2 itself stopped at `outputs` and is recorded as QUALIFICATION-ENGINEERING-FAILURE (`results/p10is2-partq-run-20261119/OUTCOME.md`); attempt 1 was refused at `inputs`.

## The numbers (reproduced by the independent recomputation)

| Gate | Threshold | Teacher A | Teacher B |
|---|---|---|---|
| Q1, teacher's own mean score | ≥ 0.55 | 0.763188 | 0.764105 |
| Q2, margin over the untrained student | ≥ 0.30 | 0.619208 | 0.633634 |
| Q3, filter precision, Wilson lower bound | ≥ 0.90 | 0.9213 (308 of 324; τ −0.20, length ratio 0.5–2.0) | 0.9224 (124 of 128; τ −0.15, length ratio 0.5–2.0) |
| Q4, check reserve: accepted and precision | ≥ 150 accepted; precision ≥ 0.90 | 150 of 156 accepted-correct (0.9615), stopped at block 1 | 142 of 151 (0.9404), stopped at block 4 |
| Accepted pool | ≥ 24,000 | 24,187 | 24,796 |

For comparison, P10-S2 (ADR-0022) ended TEACHERS-NOT-QUALIFIED with 78 and 22 accepted on the check against 150 and pools of 7,804 and 2,341 against 8,000 under its own rules; the two studies' rules differ (ADR-0025 tables every change), so this is context, not a like-for-like improvement figure.

## Independent recomputation

`audit/RECOMPUTE_P10IS2_PARTQ.md` (arbor-auditor subagent, Claude Opus 5.5; own code): **REPRODUCED WITH CORRECTIONS.** 341 quantities compared, largest real difference 0.0; every accept indicator and every per-item score matches; the label is the same. The regeneration identity was redone by the auditor from the durable packages, offline, six threads, on the 32 recorded batches per teacher: 1,024 + 1,024 outputs, 0 differing token sequences (scores within 1.19e-7). Tokenization test (a) with the auditor's own tokenizer over all 46,380 real R-gloss-icl prompts: 0 mismatches. All 25,792 reused files match the plan; the manifest's 259 files match; the only commit after the freeze is Decision 2 and the tree was clean.

## Corrections and disclosures (the registered records are kept as written)

1. **A term of Q2 could not be recomputed.** Only the untrained student's two mean scores are stored, although ADR-0025 section 4.3 rule 8 says every per-item input of the gate is stored. It cannot change the label: Q2 passes for any student mean up to 0.463. Recorded as a departure of the implementation from the specification.
2. **Teacher B's Q4 Wilson lower bound is 0.8906**, below 0.90. Q4 is registered as a point-precision gate (0.9404 ≥ 0.90), so B passes as registered; the interval is printed here because the report does not print it.
3. **Margins on the pool.** Teacher A generated its whole pool and cleared 24,000 by 187. Teacher B had 23,998 after 30 blocks and needed a 31st.
4. Nine outputs per teacher were dropped as equal to an evaluation reference; yields 0.1229 (A) and 0.0400 (B).
5. Decision 2 quotes 2,030 s and 966 s for the two attempt-3 counting rehearsals; those are wall times, and their ledgers show 2,022 s and 963 s. They are outside the total by the ruling recorded in Decision 2; had they counted, the total would be 14.31 h against the 13.83 h cap.
6. The one change of scientific text against the approved ADR is the segment rule of the R-gloss-icl template (addendum section 3), made knowing that attempt 2 failed tokenization test (a) on one prompt. The prompt text is unchanged; no word, item or prompt was dropped.

## Cost

Attempt 3 charged 1,039.6 s; Part Q in total 48,533.6 s (13.48 h) of the 13.83 h cap. Stage charges against caps: reuse 2.35 of 72 s; regeneration 410.7 of 936 s; outputs 623.4 of 1,296 s; analysis 3.1 of 36 s.

## Acceptance

The lead accepts this outcome as registered, unchanged, with the corrections above beside it, under the human lead's delegation of 2026-11-18 ("accept the results as they come and continue with the next simulations until you conclude P10-I-*"). It is an acceptance by the lead under that delegation, not the human lead's own.

## What it licenses, and what Part T still needs

It licenses the use of the two teachers and of the accepted pools as training material for Part T, as ADR-0025 defines. It licenses no statement about transfer, retention, a memory, or a student being better than a teacher. Before any Part T freeze: Part T's own implementation audit, rehearsals and Decision 2; the open advisory that Part T reads Part Q files without checking them against the manifest (reused files are covered by the reuse hashes only); the Q_fit panel left out of the bundle's partition as the auditor notes; and the departure of item 1.
