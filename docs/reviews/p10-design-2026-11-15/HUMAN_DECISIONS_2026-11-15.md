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

## S2's composition rule is strengthened (2026-11-15 UTC)

The lead reported that ADR-0022's registered COMPOSES rule (§11.4) compares raw scores, so an arm that adds nothing could satisfy it, and that the lead had left the rule unchanged and printed the untrained student's score beside it. The human lead answered, verbatim:

> let's strenght the registerd rule, the ost is aceptable

Recorded by the lead:

- **The COMPOSES rule of ADR-0022 §11.4 is strengthened by the human lead's decision**, before any S2 calibration, rehearsal or registered record exists. The new rule measures each answer's gain over the untrained student inside the combined task against its gain in the single task, on the same sentences, and requires both answers to pass; its exact text is fixed in the combined-tasks addendum after an independent check.
- "The cost is acceptable" is read as covering the added scoring time of the combined tasks (projected by the drafter at about 3 to 12 hours of charged time for four replicates, unchecked), within the hour-cap delegation already recorded.
- The composition lines stay descriptive: they enter no gate, class or TRANSFER label.

### The human lead's agreement with the proposed rule (2026-11-15 UTC)

The lead described the proposed rule to the human lead: for each of the two answers, the arm's gain over the untrained student inside the combined task as a fraction of its gain on the same sentences in the single task; each answer must keep at least 0.80 of its single-task gain; COMPOSES only if every training order and replicate passes; DOES NOT COMPOSE if some answer keeps less than half its gain in every replicate of an order; otherwise inconclusive; the replaced rule still printed beside it. The lead also stated two assumptions: the line stays descriptive and does not feed the transfer label; "the cost is acceptable" covers the added scoring time. The human lead answered, verbatim:

> agree with your proposed rule

Recorded by the lead: the rule as described is approved by the human lead in substance. Its exact text is still subject to the independent check in progress; anything the check changes beyond wording is reported to the human lead before the addendum is adopted. The two stated assumptions were not objected to and stand.

### The human lead's confirmation of the two tightenings (2026-11-15 UTC)

After the independent check (Opus 5.5) of the combined-tasks addendum, the lead put two tightenings of the strengthened rule to the human lead, recommending both: (1) the rule is read only if the teacher's gap on the combined-evaluation sentences is at least 0.30 and the arm's single-task gap closed on them is at least 0.50, otherwise NOT_EVALUATED; (2) the floor subtracted in the numerator is the larger of the untrained student's combined and single-task scores for that answer. The lead asked: "Do you confirm the two tightenings? If you'd rather keep the rule exactly as you agreed it, I'll strike them." The human lead answered, verbatim:

> I agree with your recommendation

Recorded by the lead: both tightenings are confirmed. The thresholds the human lead agreed earlier (0.80 to pass; below 0.50 for DOES NOT COMPOSE) are unchanged. The lead's own design choices reported in the same message (C1 alternates the order of the two languages; the adapter baseline on C2 switches adapters per answer) were not objected to and stand as the lead's choices.

### The human lead's approval of the combined-tasks addendum (2026-11-15 UTC)

Verbatim:

> I've read P10-S2 cobined task done please continue with simulations, consider it as approved

Recorded by the lead: the combined-tasks addendum to ADR-0022 (tasks C1 and C2 and the strengthened COMPOSES rule with its two tightenings) is approved by the human lead. The lead adopts the final text into ADR-0022 once the drafting context has removed the "pending confirmation" marks, without a further question. "Continue with simulations" is read as the direction to proceed with the P10 calibrations, rehearsals and registered runs under the delegations already recorded; it waives no audit, freeze or headroom rule.

## Repository clean-up and reproducibility files, after P10 (2026-11-15 UTC)

The human lead, verbatim:

> great once we finish with p10-II-S0..2 we must clean the repo, i see it have zip folder that are unrelated and handoff that aren't needed to the study also we are missing cursial files here like the requirements libs,files,models needed in other computers to reproduce each of our finding, so we should have a list per and it's missing it's global CITATION.cff

Recorded by the lead as a task for after the three P10 studies (S0, S1, S2) are finished. Nothing is removed or added now.

- **Clean-up.** Candidates seen at the repository root on `main` at the time of this record: `ArborLM-Codex-Research-Starter.zip`, `ArborLM-Research-Handoff.md`, `OVERNIGHT_REPORT.md`, and `docs/ArborLM_Claude_Handoff_P5_to_P6.md`. `docs/RESEARCH_HANDOFF.md` is named by `AGENTS.md`/`CLAUDE.md` as required reading and is not a candidate without the human lead saying so. The lead lists every candidate with what refers to it and gets the human lead's yes on the list before deleting anything; removal is by an ordinary commit (history is not rewritten).
- **Reproduction requirements, one list per study** (P1–P9-II and P10-S0, S1, S2): the Python version and locked packages, extra packages outside the lock with pinned versions and hashes, input files with hashes and where they come from, models with pinned revisions, hashes and licences, hardware and platform of record, the commands, expected run time, and which results are bit-reproducible on which platform.
- **A global `CITATION.cff`** at the repository root. The lead asks the human lead for the author list, title, licence and preferred citation before writing it; no name or affiliation is invented.

### Authorship and citations (2026-11-15 UTC)

The human lead, verbatim, on the `CITATION.cff` and what is cited:

> the true is that everything done was done here, I didn't cite anyone nor did I start any expirement based on comments of other studies, but we did reduce the work by reading throught existing studies that you can cite

Recorded by the lead:

- The work in this repository is original to this project: no experiment was started from another study's comments. `CITATION.cff` describes this repository as the work to cite.
- Prior work that was read and that saved effort is to be cited. The lead compiles the list from what the repository itself records as read (`docs/LITERATURE_CHECK.md`, the ADRs and reviews) and from the artefacts the studies use (models, datasets, metrics and libraries, whose licences in some cases require attribution). Every entry is checked against its source before it is written; nothing is cited from memory alone, and nothing is listed as read that the records do not show was read.

### P10-S1: the capacity grid is shifted down (2026-11-15 UTC)

After the independent check of the drafted load-search extension (`docs/reviews/p10s1-load-search-2026-11-15/` on `claude/p10-s1`), the lead offered (A) the extension as drafted or (B) a capacity line at 1,024 → 4,096 → 16,384 slots at eight facts per slot, recommended B, and said B changes registered rows after calibration data was seen (no registered seed observed) and so needs the human lead. The human lead, verbatim:

> im ok with b

Recorded by the lead: option B is approved. ADR-0021 §24 carries the record; revision 5 of ADR-0021 is drafted and independently reviewed before any code change or run. The lead also extends the dense control's learning-rate grid upward in revision 5 under the P10 delegation (no separate question was put to the human lead on it).

### P10-S0: the outcome is accepted as registered (2026-11-16 UTC)

The lead reported the registered run's outcome (row 4, ADDRESSING-QUALIFIED at 4,096 and 16,384 slots, arm A5-D), its caveats and the independent recomputation (1,065 comparisons, 0 disagreements), and asked whether the outcome is accepted as registered. The human lead, verbatim:

> register it as it is, same as the other we commit push and the propose a P10-I to adress each better

Recorded by the lead: the outcome is accepted unchanged, with its caveats (ADR-0020, last addendum, on `claude/p10-s0`). Each shortfall is a candidate item for the P10-I proposal, which is proposed and not run and needs the human lead's review. The lead does not read this message as a decision on any other open question.

### P10-S1: the load search is extended once (2026-11-16 UTC)

The first load search returned both loaded cells (8K/1K, 32K/4K) as NOT LOADED WITHIN ITS CEILING: F-OQ passes at the ceiling and at one earlier candidate in each cell but never at two consecutive candidates (misses of 0.003 to 0.024 bits against the 0.10 limit). The lead offered (1) one more candidate per cell with every rule unchanged, (2) both transitions fixed as CAPACITY NOT TESTED, (3) stopping S1, and recommended (1). The human lead, verbatim:

> Extend search once

Recorded by the lead: ADR-0021 §25.15 on `claude/p10-s1` fixes the two new candidates (393,216 and 786,432), that nothing else changes, and that the extension is made once.

### P10-S2: the outcome is accepted as registered; P10-I is drafted in three parts (2026-11-16 UTC)

The lead reported that P10-S2's data step completed and its teacher qualification gate failed on the accepted counts (78 and 22 accepted on Q_check against 150; pools of 7,804 and 2,341 against 8,000), giving TRANSFER-INCONCLUSIVE: TEACHERS-NOT-QUALIFIED before the freeze, with the independent recomputation agreeing. The human lead, verbatim:

> we should accept it as it is, and start working on P10-I on all of the simulation meaning
>
> P10-I-S0, P10-I-S1, P10-I-S2
>
> because each have their own correction that needed to be done, and now we have more data including the result of P9-II

Recorded by the lead: the P10-S2 outcome is accepted unchanged (ADR-0022, last addendum, on `claude/p10-s2`). P10-I is drafted as three parts, P10-I-S0, P10-I-S1 and P10-I-S2, on the branch `claude/p10-i-design`. The lead reads "start working" as drafting the specifications: nothing under P10-I is implemented or run before the human lead's review and recorded approval. P10-S1 continues under ADR-0021 as approved; its result, when it exists, is an input to P10-I-S1.
