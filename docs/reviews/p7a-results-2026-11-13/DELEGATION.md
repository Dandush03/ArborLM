# Delegation record — P7-A, 2026-11-13

Workflow of ADR-0012 (governance questions still open). **Astra review: NOT_PERFORMED.** Model identity is the `model` field on assistant messages in each subagent's local session transcript, counted by the lead; transcripts are not committed.

| Task | Role | Requested | Transcript model (assistant messages) |
|---|---|---|---|
| Direction review, specification, decisions on audit findings, execution of the registered commands, this review | Lead | `claude-fable-5-2` | `claude-fable-5-2` (this session) |
| Review of the draft's mathematical and measurement assumptions (before human approval) | Auditor | `claude-opus-5-5` | `claude-opus-5-5` (50) |
| Implementation, tests, timed dry run | Implementer | `claude-sonnet-5-5` | `claude-sonnet-5-5` (112) |
| Pre-freeze audit; independent simulator | Auditor | `claude-opus-5-5` | `claude-opus-5-5` (109) |
| Fixes for audit findings; count-preserving null | Implementer | `claude-sonnet-5-5` | `claude-sonnet-5-5` (77) |
| Re-audit before freeze; simulator extended to the null stream | Auditor | `claude-opus-5-5` | `claude-opus-5-5` (128) |
| Independent recomputation of results | Auditor | `claude-opus-5-5` | `claude-opus-5-5` (87) |

No substitution was needed. No clerk (Haiku) task was used.

## What the lead did itself

- Read the cache simulator's page-set, statistics and LRU functions in `p7a_sim.py`, both audit reports, the re-audit and the results audit. The trace, stage, analysis and CLI modules were not read line by line by the lead; they were covered by the auditor's passes and by tests.
- Ran lint, type check and the full test suite before the freeze (482 passed), one recorded loader smoke command, the three registered stage commands and the auditor's independent-simulator command, in order, with nothing committed between the start of `trace` and the end of `analyze`.
- Read the registered criteria from the implementation's analysis and compared them with the auditor's recomputation.

## Human decisions in this study

- Approval of ADR-0013 as drafted in revision 2 ("Approve as drafted").
- Choice of the exact count-preserving null over the approved sampling method, when the audit showed the approved text contradicted itself ("Exact count-preserving (Recommended)").

## Departures and weaknesses, stated

- The lead's first draft had two blockers found by the auditor before approval; revision 2 was what the human approved.
- The lead's own clarification 2 (the sampling procedure) was wrong and was withdrawn before any trace existed.
- The first attempt to launch the trace stage failed in the shell before the command started (a glob error in the wrapper line); nothing ran and no run directory was created. The stage was then run once.
- The freeze was committed locally and not pushed before execution, to limit CI usage as for P6.
- The auditor wrote the independent simulator and the reference null generator that the study's tests compare against, so agreement between them is not fully independent evidence. The auditor's later full recomputation from raw traces used a separately written script.
- One defect in a non-criterion table (tree key reads under random key placement) was found only after the run.
