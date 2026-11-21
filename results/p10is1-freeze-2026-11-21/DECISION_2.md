# P10-I-S1 — Decision 2 (registered run)

DECISION: RUN

Freeze commit: 46bf55a5cc0eda11b7201c4ab777e69c6970c4cd

Date: 2026-11-21 (about 03:25 Panama time).

## Who decided

The scientific lead (Claude, Fable 5.2), under the human lead's delegation of 2026-11-18 for P10-I (outcomes accepted as registered, run decisions and merges taken by the lead until P10-I is complete; no threshold relaxed, safeguards kept) and his word of 2026-11-19 that the lead drives P10-I-S1. ADR-0024 records Decision 2 as the human lead's own; this record is taken under that delegation and not by him in person. He is away until 2026-11-23, has not seen the figures below, and may overrule this decision.

## What was checked

| Item | Reading | Met |
|---|---|---|
| Quiet baseline | ACCEPTED, session 1 attempt 2; `load_p95` 167, `load_limit` 217 (hundredths), below the 250 that is reported and the 300 ceiling; re-derived independently by the auditor | yes |
| Projection | WITHIN BUDGET. Second projection differs from the first only in the charged hours (6.704 to 7.967 h); grants identical (2K/256: 786,432; 8K/1K: 393,216; 32K/4K: 786,432) | yes |
| Caps | not provisional; total 52.0 h; charged so far 9.32 h; with every registered stage cap spent the total is 44.3 h, under the 60 h limit | yes |
| Counting rehearsal | `P10IS1-counting-20261121`: all nine stages COMPLETE at real size against plan e1479e365300fb92f63522ae69cec79e928c5f458d86fde91e8beeb64f0f1864; both quiet stages with a genuine quiet reading; 600 s waited, not charged; about 1.35 charged hours | yes |
| Freeze | `freeze` exit 0; record sha256 3e325abc80146735c1e3eb3063f6808b8837e5d79395c829cc419d9bbcd3793c; plan re-derived equal; gate G9 passed (seed-registry checker, revision 3) | yes |
| Independent audit | arbor-auditor (Claude Opus 5.5): READY FOR THE FREEZE COMMIT AND DECISION 2 (`AUDIT_PREFREEZE_3.md` in this folder) | yes |

## Conditions of the run

- No threshold, label rule, seed, cell, grant or cap is changed by this decision.
- The timing stage runs first and alone, the throughput stage last and alone; the lead makes no tool call while either runs.
- Sharing the machine with P10-I-S2 Part T during the train and ladder stages is allowed only if at least about 34 GiB of memory is available when Part T starts (the auditor's condition: below that, this study stops adding workers and the waiting is charged). Nothing measured is shared: timing and throughput refuse while another study's process is alive.
- If a stage reaches its cap, an extension is decided on the cost ledger alone, before any registered value is read, and is recorded in `docs/PARAMETER_CHANGELOG.md`.
- An identity failure or a code or environment error is an engineering stop, not a scientific outcome.
- No file in this worktree is written or committed while a registered stage runs.

## Disclosures

1. No rehearsal has run a ladder cell past its base length at real size: in the counting rehearsal all three ladder cells were full at U0 and the ladder stopped at round 0. That is why the rehearsal cost 1.35 h against the 6.47 h the projection lists for it. The registered ladder may be the first real-size run of later rounds.
2. Gate G9 used revision 3 of the seed registry. Revision 4 on main allocates only P10-I-S6 blocks, which the auditor found do not overlap this study's ranges. This branch has not been merged with main since.
3. A system process at full CPU (for example `signpost_reporter`, seen at the start of the rehearsal's throughput stage) is visible to the quiet rule only through the load figures, not through the process conditions.
4. The registered quiet stages need the Claude application and Claude Code present, as at the baseline, and an unchanged set of Claude processes; a session of the user's that starts or ends discards the measurement, which is then retried inside the stage's wait.
5. The quiet baseline's attempt 1 was discarded (three `claude` processes ended together); another project's session (ArborML Lab) shares this Mac and could not be reached after the window, so its statement of what ran was not obtained (`results/p10is1-quiet-baseline/DISCLOSURE.md`).
6. Before the candidate plan was superseded, the old plan file was set aside by hand because an identical copy already held the name the command moves it to; nothing was deleted (changelog row 22; found harmless by the audit).
7. ADR-0024 section 11 says the projection runs once; it was run a second time by the accounting ruling (changelog row 21).
8. The lead's implementation rulings for this study (quiet-rule addendum and rulings F1 to F7, N1 to N4) are pending the human lead's confirmation.
9. Any result of this run is component evidence (predictive loss at fixed small backbones). It does not bear on capability parity with reference models (ADR-0032).

`Astra review: NOT_PERFORMED`
