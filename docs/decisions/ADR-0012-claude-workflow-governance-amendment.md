# ADR-0012 — Proposed governance amendment: human-requested Claude research workflow

- Date: 2026-11-13 (America/Panama).
- Status: **PROPOSAL — PENDING HUMAN RESEARCH LEAD APPROVAL. Not in force.** Until the approval record in §7 is filled in by the human lead, the authority order in `AGENTS.md` is unchanged and everything produced under this workflow is labelled `PENDING HUMAN REVIEW`.
- Prepared by: Claude Fable 5.2 (`claude-fable-5-2`), at the human research lead's request in `docs/ArborLM_Claude_Handoff_P5_to_P6.md` and the accompanying chat instruction of 2026-11-13.
- **Astra review: NOT_PERFORMED.** This amendment does not constitute, replace or imply Astra validation of anything, past or future.

## 1. Why an amendment is needed

`AGENTS.md` and `docs/RESEARCH_HANDOFF.md` §9 assign scientific reasoning and final validation to Astra. Astra has not reviewed any ArborLM specification or result. P1–P5 ran under a session exception recorded in `docs/RESEARCH_LOG.md` (2026-11-12, "Human authorizes alternate scientific reviewer"), which authorized root Codex as scientific reviewer.

The human lead has now handed orchestration to Claude and named specific Claude models for specific roles. That instruction outranks prior convention under the repository authority order (item 1: the human lead's current explicit direction), but it is a chat/handoff instruction, not yet a recorded governance decision. This ADR turns it into one that can be approved, amended or rejected, without editing `AGENTS.md` or any historical label.

## 2. What does not change

- Every historical record stays as written: `Astra review: NOT_PERFORMED`, the Codex reviewer exception, all P1–P5 approvals, thresholds, outcomes and failed gates.
- `AGENTS.md` is not edited by this ADR. If the human lead approves this amendment, a one-paragraph pointer to it may be added to `AGENTS.md` by the human lead or on their explicit instruction.
- The human research lead alone approves: specifications for execution, budgets, merges, publication, release of weights or data, new training, SSD work and any scaling.
- No model approves its own work. The labels `ASTRA VALIDATED` / `STATUS: ASTRA-VALIDATED` remain reserved for a demonstrable Astra review and are not used under this workflow.

## 3. Proposed role assignment

| Role | Model (ID) | Owns | May not |
|---|---|---|---|
| Scientific lead / orchestrator | Claude Fable 5.2 (`claude-fable-5-2`) | Hypotheses, architecture decisions, preregistration drafts, experiment design, orchestration, final interpretation | Approve its own specifications for execution; merge; publish; start training, SSD or scaling work; relabel history |
| Independent auditor | Claude Opus 5.5 (`claude-opus-5-5`) | Independent mathematical verification, critical code review, scientific implementation audits, recomputation from raw records | Audit work it produced; choose thresholds or gates; run training or registered benchmarks |
| Implementer | Claude Sonnet 5.5 (`claude-sonnet-5-5`) | Code, tests, CI, figures, benchmark harnesses, documentation, under an approved specification | Change scientific assumptions, metrics, seeds or thresholds; modify P1–P5 files |
| Evidence clerk | Claude Haiku 5.5 (`claude-haiku-5-5`) | Read-only inventory, metadata and provenance extraction, log classification, formatting | Interpret results or decide anything scientific |

Role definitions with these limits are checked in under `.claude/agents/` (`arbor-lead`, `arbor-auditor`, `arbor-implementer`, `arbor-clerk`).

## 4. Proposed review labels

To keep the provenance of each review distinguishable from Astra's and from the earlier Codex exception:

- `SPEC: PENDING HUMAN REVIEW (Fable-drafted)` — a specification drafted by the scientific lead, not yet approved.
- `SPEC: HUMAN-APPROVED (Fable-drafted, Opus-audited)` — only with a quoted human approval and a retained audit record.
- `RESULT: FABLE-REVIEWED, OPUS-AUDITED — ASTRA NOT_PERFORMED` — result interpretation under this workflow.
- `STATUS: HUMAN-APPROVED` — unchanged meaning; requires the human lead's recorded words.

## 5. Delegation evidence rule

A delegated task is recorded as performed by a given model only when session metadata shows that model produced the output. For each delegated task the record keeps: role, requested model, model reported by session metadata, the brief, and the output location. If a requested model is unavailable, the substitution is recorded and the task is labelled with the model that actually ran. A subagent's own statement of its identity is recorded as a self-report, not as verification.

Implementer and auditor always run in separate contexts. The auditor is given code and records, not the lead's conclusions.

## 6. Known weaknesses of this arrangement

- All four roles are Claude models from one vendor. Independence between lead, auditor and implementer is separation of context and instructions, not independence of training or failure modes. Correlated blind spots are possible, and this is weaker than review by an unrelated system or a human domain expert.
- The scientific lead both designs studies and interprets them. The mitigations are preregistered thresholds fixed before observation, auditor recomputation from raw records, and the human approval gates above. They reduce, and do not remove, the conflict.
- This workflow has no track record on this project yet. The first evidence of how well it works will be the P5 review itself and its independent audit.

## 7. Decisions requested from the human lead

1. Approve, amend or reject the role assignment in §3 as the project's working scientific-review arrangement in place of the Codex reviewer exception, for work from P6 onward.
2. State whether this is temporary (for example, until Astra is available, or for P6 only) or standing.
3. Approve or amend the labels in §4.
4. Say whether `AGENTS.md` should gain a pointer to this ADR, and who edits it.
5. Say whether an Astra review of P1–P5 and of this workflow should still be sought when Astra is available.

### Approval record

*Empty. To be completed with the human research lead's quoted decision, date and the commit that records it.*
