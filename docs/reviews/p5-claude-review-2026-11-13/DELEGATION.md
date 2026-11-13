# Delegation record — P5 review, 2026-11-13

Workflow proposed in ADR-0012 (pending human approval). **Astra review: NOT_PERFORMED.**

Model identity is taken from the per-message `model` field in each subagent's session transcript, not from the subagent's own statement. Both are shown.

| Task | Role | Requested | Transcript `model` on assistant messages | Self-report | Output |
|---|---|---|---|---|---|
| Orchestration, review, ADR drafts | Lead | `claude-fable-5-2` | `claude-fable-5-2` (this session) | — | `README.md`, `P6_STRATEGY.md`, ADR-0011, ADR-0012 |
| Evidence inventory | Clerk | `claude-haiku-5-5` | `claude-haiku-5-5` (31 records) | "Haiku 5.5 (claude-haiku-5-5)" | `inventory/` |
| Figure package | Implementer | `claude-sonnet-5-5` | `claude-sonnet-5-5` (60 records) | "claude-sonnet-5-5" | `figures/` |
| Operator inspection | Implementer | `claude-sonnet-5-5` | `claude-sonnet-5-5` (33 records) | "claude-sonnet-5-5" | `operators/` |
| Independent audit | Auditor | `claude-opus-5-5` | `claude-opus-5-5` (92 records) | "claude-opus-5-5 (Opus 5.5)" | `audit/` |

No substitution was needed; every requested model was available.

Caveats:

- The haiku and sonnet transcripts each contain one non-message bookkeeping record (`type: api-request-shape`) that names `claude-opus-5-5`. Every assistant message in those transcripts carries the requested model. The meaning of that bookkeeping record is not known to the lead and is recorded here rather than explained away.
- The project subagent definitions in `.claude/agents/` were created during this session. The session could not load newly created agent types, so each task ran as a general-purpose subagent with an explicit model override and was instructed to read and follow the matching role file. Future sessions can invoke the named agents directly.
- Transcripts are local session files and are not committed. This table is therefore a record made by the lead from metadata it inspected, not an independently verifiable artifact.
- Implementer and auditor ran in separate contexts. The auditor's brief contained the code and record locations and the questions, not the lead's conclusions.
- All four roles are Claude models. See ADR-0012 §6 for what that does and does not provide.

## What the lead checked itself

- Read in full: `AGENTS.md`, both handoff documents, the canonical handoff, experiment protocol, research log, ADR-0010, P5 README and authorized review, `pilot_model.py`, `p5_timing.py`. ADR-0001–0009 and the P1–P4 reviews were read through the research log's account and the README summary, not line by line; that is a limit of this review.
- Viewed figures 2 and 4.
- Recomputed R by backbone and the baseline/flat dispersion directly from the per-cell records.
- Ran `lead-checks/router_gradient_support.py` (synthetic).
- Did not rerun the P5 test suite, did not load any checkpoint, did not run any model on real data.
