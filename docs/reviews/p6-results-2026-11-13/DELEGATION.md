# Delegation record — P6, 2026-11-13

Workflow of ADR-0012 (governance questions still open). **Astra review: NOT_PERFORMED.** Model identity is the `model` field on assistant messages in each subagent's local session transcript, counted by the lead; transcripts are not committed, so this is the lead's record of metadata it inspected.

| Task | Role | Requested | Transcript model (assistant messages) |
|---|---|---|---|
| Specification, orchestration, decisions on audit findings, execution of the registered commands, this review | Lead | `claude-fable-5-2` | `claude-fable-5-2` (this session) |
| P6-E implementation, first session (interrupted by a session restart before tests were written) | Implementer | `claude-sonnet-5-5` | `claude-sonnet-5-5` (88) |
| P6-E completion and tests; P6-Q run-order change | Implementer | `claude-sonnet-5-5` | `claude-sonnet-5-5` (116) |
| P6-Q implementation and tests | Implementer | `claude-sonnet-5-5` | `claude-sonnet-5-5` (95) |
| Independent float64 reference for P6-Q | Auditor | `claude-opus-5-5` | `claude-opus-5-5` (19) |
| Pre-freeze audit of all P6 code | Auditor | `claude-opus-5-5` | `claude-opus-5-5` (74) |
| Fixes for audit findings; loader smoke command | Implementer | `claude-sonnet-5-5` | `claude-sonnet-5-5` (108) |
| Re-audit before freeze | Auditor | `claude-opus-5-5` | `claude-opus-5-5` (132) |
| Independent recomputation of results | Auditor | `claude-opus-5-5` | `claude-opus-5-5` (112) |

No substitution was needed. The first three tasks ran as general-purpose subagents with a model override and the role file as instructions; after the session restart the named project agents (`arbor-implementer`, `arbor-auditor`) were used directly. No clerk (Haiku) task was needed for P6.

## What the lead did itself

- Read `p6_retrieval.py` (all variants), `p6_fidelity_reference.py` and the rule-substitution code in `p6_fidelity.py` in full, and both audit reports. The remaining P6 modules (stage machinery, timing harness, analysis) were not read line by line by the lead; they were covered by the auditor's two passes and by tests.
- Ran lint, type check and the full test suite before the freeze (368 passed), the two recorded loader smoke commands, and the six registered stage commands, one at a time, with no other task from this session running during a stage.
- Read the registered verdicts and clause values from the implementation's analysis and compared them with the auditor's recomputation.

## Departures from procedure, stated

- An implementer ran a formatter over `tests/` by mistake during the fix round, altering three tracked tests and the auditor's test file; it restored all four to their original bytes (verified by `git diff` and by the auditor's hash table) before the freeze.
- Implementers and the auditor ran and timed variants on synthetic tensors before the freeze (dry runs, budget checks). ADR-0011 §7 clarification 27 discloses what those showed.
- The freeze was committed locally and not pushed before execution, at the human lead's instruction.
- The auditor wrote the float64 reference it later relied on in gate (iv).
