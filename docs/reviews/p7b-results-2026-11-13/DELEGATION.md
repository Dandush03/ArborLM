# Delegation record — P7-B, 2026-11-13

Study-specific Claude workflow for P7-B only, by the human lead's direction; ADR-0012 pending. **Astra review: NOT_PERFORMED.** Model identity is the `model` field on assistant messages in each subagent's local session transcript, counted by the lead; transcripts are not committed.

| Task | Role | Requested | Transcript model (assistant messages) |
|---|---|---|---|
| Design, orchestration, decisions on review and audit findings, execution of the registered commands, this review | Lead | `claude-fable-5-2` | `claude-fable-5-2` (this session) |
| Identity manifest of the P7-A traces | Clerk | `claude-haiku-5-5` | `claude-haiku-5-5` (39) |
| Inventory of validation ranks used by every study | Clerk | `claude-haiku-5-5` | `claude-haiku-5-5` (132) |
| Review of revision 1 (calibration traces only) | Auditor | `claude-opus-5-5` | `claude-opus-5-5` (57) |
| Re-review of revision 3 | Auditor | `claude-opus-5-5` | `claude-opus-5-5` (85) |
| Implementation, tests, timed dry run | Implementer | `claude-sonnet-5-5` | `claude-sonnet-5-5` (186) |
| Pre-freeze audit; independent panel, layout and re-simulation tools | Auditor | `claude-opus-5-5` | `claude-opus-5-5` (140) |
| Fixes for audit findings | Implementer | `claude-sonnet-5-5` | `claude-sonnet-5-5` (133) |
| Narrow re-check before freeze | Auditor | `claude-opus-5-5` | `claude-opus-5-5` (106) |
| Independent recomputation of results | Auditor | `claude-opus-5-5` | `claude-opus-5-5` (121) |

No substitution was needed.

## Human decisions in this study

- Direction: existing stream plus a prospective replication on validation ranks 2560–3071; five predetermined partition seeds; study-specific governance; acceptance of the registered choices (review of revision 2).
- "I've read the adr and seems logic to me, please proceed with the validation once you finish the push of pr 4."
- "Confirm, proceed", in answer to the question about the corrected five-partition rule.

All three are quoted in ADR-0014 §15.

## What the lead did itself

- Wrote four revisions of the specification, three of them in response to independent reviews that found blockers in the lead's drafts.
- Confirmed the half-open rank convention in the panel code.
- Ran lint, type check and the full test suite before the freeze (677 passed); ran every registered stage and every auditor tool in the registered order with the clean-tree check before each; committed the layout hashes, the stream-B identity manifest, the raw simulation records and the analysis records in that order.
- Did not open any simulation record or analysis output until both streams were simulated and both independent re-simulations had agreed.
- Did not read the P7-B implementation line by line; it was covered by the auditor's pre-freeze audit and re-check, the tests, and three independent tools.

## Departures and weaknesses, stated

- The lead's drafts contained a blocker in each of two independent reviews (a utilization check that could not fire; a five-partition rule that could not fail). Both were fixed before execution; the second fix was confirmed by the human lead.
- Calibration-side analogues of the main result were visible to the auditor and the lead before approval. The specification says so at its top.
- A layout-stage command exceeded the tool's foreground time limit and continued in the background to completion; it ran once.
- The implementer was allowed to read the auditor's earlier review scripts, so the two layout implementations are not independent in origin; the auditor's registered tool was restructured for that reason.
- One control (L-NCOAX) fell outside its registered band in the confirmation setting; it is reported in the review.
