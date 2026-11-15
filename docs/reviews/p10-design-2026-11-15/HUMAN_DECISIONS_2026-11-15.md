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

## Downloads — standing permission (2026-11-15 UTC)

The lead asked the human lead to confirm the S2 package wheels "at about 23 to 32 MB for the eight named packages, plus the dependencies the resolver pulls in". The human lead answered, verbatim:

> you don't have to ask for permission to download if the overall is less than 30gb

Recorded by the lead, with the limits the lead puts on its own use of this:

- The lead may download what a specified P10 study needs without asking each time, while the **running total of all downloads made under this permission stays below 30 GB**. The total is kept in a download ledger in the repository (`docs/reviews/p10-design-2026-11-15/DOWNLOAD_LEDGER.md`: date, study, source, pinned revision or hash, licence, bytes, running total), written before a fetch is started and completed after it.
- The S2 package wheels and their resolver dependencies are therefore approved; the pending confirmation is closed.
- Unchanged: every file is named in a specification or its freeze requirements first; revisions are pinned and hashes and licences recorded; `pyproject.toml` and `uv.lock` do not change; no account, login, cloud or paid service; no model above the size limits of the study's ADR; nothing is executed from a download other than pinned packages and weights loaded by the specified loaders. A download that would take the total to 30 GB or more returns to the human lead.
- The permission is about downloading. It approves no training, no run, no design change and no publication.

## Running the P10 studies at the same time (2026-11-15 UTC)

Looking at the task list, the human lead wrote, verbatim:

> can you keep nextime which p is running like the last Opus audit of S0 should say P10-S0 so i can follow them and also i would expect to see more process running in parallel since each P10-S have many divergent to cover on each case, make sure to maximize the time by using the m5 capabilities

Recorded by the lead:

- **Naming.** Every delegated task and background job carries its study code first ("P10-S0: …").
- **Concurrency.** This answers the question ADR-0020 §17 item 4 reserved ("whether S0's blocks may overlap S1's and S2's training on the machine"): they may. It replaces item 3 of the order in `EXECUTION_PLAN.md` ("registered stages do not overlap").
- **The lead's conditions for overlapping compute stages** (the lead's, so that a faster schedule changes no result):
  1. A study's rehearsal is measured under the load it will run under: if its registered stages are to share the machine, the rehearsal runs with the other studies' worker counts busy (ADR-0020 §10.3 already rehearses "under 12 busy processes"), and the twofold headroom rule is applied to those loaded rates.
  2. The machine has 18 cores and 48 GiB. CPU studies keep their registered six single-thread workers each (S0 and S1 side by side use 12 cores); S2 trains on the GPU. The sum over concurrently running studies of twice their rehearsed peak memory must stay within 40 GiB; each study's own per-worker and aggregate limits are unchanged.
  3. Stages whose measurement is the time itself (S1's throughput and cost timing; any timing benchmark) run alone, as their ADRs say.
  4. Charged hours are counted per study as before; running side by side does not merge budgets.
  5. Reviews and audits are split by dimension into parallel reviewer contexts where the parts are independent.
