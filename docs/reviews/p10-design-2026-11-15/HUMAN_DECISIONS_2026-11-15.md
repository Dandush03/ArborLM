# Human lead's decisions on P10, 2026-11-15 (UTC) — programme-level record

Written by the lead (Claude Fable 5.2). Verbatim quotations from the chat record, misspellings included. Astra review: NOT_PERFORMED.

## Link files for S2 and the hour caps of P10

The lead asked: "Do you also approve the 6.2 MB of Tatoeba link files for S2's symmetry check? If not, the check is skipped and the report says so." The human lead answered:

> I Aprove the link files with 6.2mb and you can extend the hour cap if needed across all p10

**Link files (ADR-0022).** Approved: the 6.2 MB of Tatoeba link files for the symmetry check. ADR-0022 revision 5 was under independent confirmation when this was said and still reads "not approved"; the lead folds this record into ADR-0022 §18 when the confirmation's edits are applied. Nothing has been downloaded at the time of this record.

**Hour caps (ADR-0020, ADR-0021, ADR-0022).** Caps at the time of the decision: S0 16 h, S1 16 h, S2 36 h.

Recorded by the lead, with the limits the lead puts on its own use of this:

- The lead may raise a P10 study's charged-hours cap when the study's own headroom rule would otherwise cut registered cells or stop the study.
- A cap is raised only **before that study's registered seeds are observed** (at the rehearsal's headroom check, or at a stage gate that reads time and memory only). It is never raised in response to a result, and never to add cells, arms, updates or replicates beyond what the specification registers.
- Each raise is recorded in the study's ADR with the measured projection that required it, the old and new cap, and what it protects. Memory caps (3 GiB per worker, 18 GiB aggregate, and S2's own) are not hour caps and are not changed.
- The human lead's words do not extend to downloads, cloud or paid services, models, data, thresholds or designs.
