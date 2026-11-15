# Delegation record — P8, 2026-11-14

Study-specific Claude workflow for P8 only, by the human lead's overnight direction (ADR-0015 §15); ADR-0012 pending. **Astra review: NOT_PERFORMED.** Model identity is the `model` field in each subagent's local session transcript, counted by the lead; transcripts are not committed.

| Task | Role | Requested | Transcript model (count of `model` fields) |
|---|---|---|---|
| Merges of PR #3 and PR #4, design, ADR-0015 (three revisions), rulings on review and audit findings, execution of the registered commands, results review, overnight report | Lead | `claude-fable-5-2` | `claude-fable-5-2` (this session) |
| Evidence inventory: parents, seeds, panels, P5 setup, defects | Clerk | `claude-haiku-5-5` | `claude-haiku-5-5` (194), `claude-opus-5-5` (1) |
| Spec review of ADR-0015 revision 1 | Auditor | `claude-opus-5-5` | `claude-opus-5-5` (43) |
| Independent panel proof and tool | Auditor | `claude-opus-5-5` | `claude-opus-5-5` (82) |
| Training implementation, tests, rehearsal, audit fixes | Implementer | `claude-sonnet-5-5` | `claude-sonnet-5-5` (177), `claude-opus-5-5` (1) |
| Evaluation, simulation, analysis implementation, tests, dry run, audit fixes | Implementer | `claude-sonnet-5-5` | `claude-sonnet-5-5` (235), `claude-opus-5-5` (1) |
| Report generator | Implementer | `claude-sonnet-5-5` | `claude-sonnet-5-5` (151), `claude-opus-5-5` (1) |
| Pre-freeze audit, training side; independent objective reference | Auditor | `claude-opus-5-5` | `claude-opus-5-5` (97) |
| Pre-freeze audit, evaluation/simulation/analysis; independent recomputation and trace tools | Auditor | `claude-opus-5-5` | `claude-opus-5-5` (157) |
| Narrow re-check before freeze | Auditor | `claude-opus-5-5` | `claude-opus-5-5` (150) |
| Independent recomputation of results and failure analysis | Auditor | `claude-opus-5-5` | `claude-opus-5-5` (147) |

No substitution was requested. Four transcripts of non-Opus roles each contain one `claude-opus-5-5` model field; the lead has not determined what produced it and records it as observed. The clerk declined to write its inventory as a Markdown file (its role definition) and returned it as a message with machine-readable tables in the session scratch area; nothing from it is committed beyond what this review and the ADR quote.

## Human decisions in this study

One: the written overnight direction of 2026-11-13 (America/Panama), quoted in ADR-0015 §15. It authorized merging PRs #3 and #4 subject to CI, and the defined P8 pilot through the registered gates without routine confirmation. No other human input was received during the study.

## What the lead did itself

- Merged PR #3 and PR #4 with merge commits after re-checking CI, and confirmed the merged tree equals the tree CI tested.
- Wrote three revisions of ADR-0015. The first was found NOT READY by the spec review (three false statements about the proxy, two of them gates; an overstated matching claim). The lead's stop-rule wording in the freeze record did not match the simulation stage's behaviour (results review, defect 1).
- Ruled on every audit finding; declined one proposed condition (a utilization floor against flat that no tree could meet) and recorded why.
- Ran every registered stage, once. Made one failed launcher attempt before any stage started (kept).
- Patched the analysis-only report generator after the run for a division by zero (results review, defect 9).
- Did not repair, rerun or substitute the five failed simulation cells.
