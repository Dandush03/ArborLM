# P10 — specifications, budget and execution plan (2026-11-15 UTC)

Written by the lead (Claude Fable 5.2). Design only: nothing in P10 is implemented, downloaded or run. Astra review: NOT_PERFORMED.

## The three studies

| Study | ADR | Question | Reviewed revision | Independent review (Opus 5.5) | Lead's approval |
|---|---|---|---|---|---|
| S0 addressing qualification | ADR-0020 | Is there a learned addressing method that is reliable across independent draws, without oracle addressing at inference? | 3 | revision 1 NOT READY (2 blockers, 7 majors); revision 2 confirmed subject to E1–E10, applied | PENDING |
| S1 useful-capacity scaling | ADR-0021 | Under controlled addressing, does a larger memory hold more useful information, or only learn faster, against a strong dense control? | 3 | revision 1 NOT READY (4 blockers, 11 majors); revision 2 confirmed subject to K1–K7, applied | PENDING |
| S2 two-teacher transfer | ADR-0022 | Can a memory attached to a frozen student acquire a second teacher's capability after a first, in one shared store, and keep the first? | 4 | revision 1 NOT READY (3 blockers, 10 majors); revision 3 confirmed subject to C1–C10, applied | PENDING the human lead's answers |

Reviews, confirmations, their scripts and every earlier revision are in this folder. Each study has its own hypotheses, controls, thresholds, seeds, data partitions, budget, freeze, audit and report.

## Budgets on the M5 Max (48 GB)

| Study | Charged-hours cap | Projection | Memory caps | Note |
|---|---|---|---|---|
| S0 | 16 | 4.9–7.3 h; doubled 9.9–14.6 | 3 GiB per worker, 18 GiB aggregate | about 9% left at the slowest rates |
| S1 | 12 | about 6.7 h; doubled 12.0 | 3 GiB per worker, 18 GiB aggregate | zero slack; a rise to 16 h has been put to the human lead |
| S2 | 36 | registered run 7.7–35.5 h depending on the rung the rehearsal admits, plus 3.5–7 h before the freeze | set by rehearsal | unmeasured; "not started" is a possible rehearsal outcome |
| **Total** | **64** | | | accepted by the human lead on 2026-11-15 "if it mean it will resolve most dough and close any posible misguidence due to a small set" |

P9-II (ADR-0019) has its own budgets (4 h and 3 h) and runs first.

## Seeds (disjoint by construction and checked by a gate in each study)

| Study | Registered data seeds | Initialization seeds | Test seeds |
|---|---|---|---|
| P9-II | 190001–191599 | 1901, 1902 (calibration 1891) | 910001–919999 |
| S0 | 200001–209999 | 2001, 2002 | 920001–920999 |
| S1 | 210001–219999 | 2101–2105 | 921001–921999 |
| S2 | 220001–228999 | as ADR-0022 | 229001–229999 |

## Order and scheduling

1. P9-II: implementation (in progress), calibration, rehearsal, audits, freeze, the registered run, recomputation. Its calibrated values and registered outcome are inputs to S0's fixed arm rule.
2. S0, S1 and S2 are implemented in parallel, each in its own worktree and package (`studies/p10s0/`, `studies/p10s1/`, `studies/p10s2/`), by separate implementers, each audited by a separate Opus context before its freeze.
3. On one machine, registered stages do not overlap: only one study's registered or rehearsal stage runs at a time, with six single-thread CPU workers; S2's GPU training does not run while a CPU study is being timed; timing-sensitive measurements (S1's throughput stage) run alone. Implementation, unit tests and reviews may overlap with a running stage only outside timed stages.
4. Proposed run order after the freezes: S1 (CPU, about 7 h), then S0 (CPU, 5–7 h; needs P9-II's result), then S2 (GPU, the longest), unless a study is ready earlier; S1 and S2 do not wait for S0's result.
5. Each study: gates at real size on rehearsal seeds before the freeze; fixed launch scripts; manifests record the platform; analysis exercised on synthetic full-registry records; one registered run; independent recomputation from raw records.
6. After all three: the lead proposes a fourth, integrated validation from the independently qualified mechanisms. It is not executed without the human lead. Any change suggested by P9-II or by one study for another goes into a separately specified follow-up, P10-I, which needs the human lead's review.

## Approval status and what is still the human lead's

- The human lead allowed the lead to self-approve P10 studies ("we can change it to  p10 can be self approve but p10-I need my review"). The lead uses that per study only when: the specification review has no open blocker or major; the implementation audit is clean before the freeze; the rehearsal shows 2× headroom; nothing changes after calibration except what the specification names; no registered seed has been observed.
- **Open with the human lead:**
  1. S2: the downloads (student model, Tatoeba exports, fallback teacher and data — 938 MB, or 1,253 MB with the fallback, plus about 6 MB of link files), the package wheels for the one-off data-generation step, whether two translation directions are "complementary capabilities", whether a filter of measured precision ≥ 0.90 is "suitable verification", and training on the GPU with CPU recomputation.
  2. S1: raising the cap from 12 to 16 hours so the seed-variance block and all dense controls survive.
  3. S0/S1/S2: whether "if no interface qualifies, stop capacity-scaling claims" applies to learned addressing only, with oracle-addressed S1 and S2 outcomes standing under their labels.
- Corrections ADR-0022 still needs before its approval (from the S0 confirmation, E8): the "s_c(S0)" symbol and the store names "S1"/"S2" clash with study names; a supplement must name the human lead; its seed check must list S0.

## What P10 cannot establish, whatever the outcomes

Oracle-addressed results are not autonomous learned memory. Nothing here measures SSD or storage latency. S2 is one kind of capability (lexical translation) with small teachers. A positive in one study implies nothing about the others.

## Addendum, 2026-11-15 (UTC): caps, downloads and concurrency after the human lead's later decisions

Recorded verbatim in `HUMAN_DECISIONS_2026-11-15.md` and in each ADR. This addendum supersedes the table and items above where they differ.

- **Caps:** S0 16 h, S1 16 h (raised from 12), S2 36 h with the lead's extension rule up to 72 h at the rehearsal check (the CPU recomputation is charged). The lead may extend hour caps before a study's registered seeds are observed.
- **Downloads:** no per-item permission below a running total of 30 GB; ledger in `DOWNLOAD_LEDGER.md`.
- **S0** runs four learned arms: the diversity penalty A5-D was added by the human lead after P9-II (ADR-0020 revision 4).
- **Order item 3 is replaced:** the studies' compute stages may run at the same time under the five conditions of `HUMAN_DECISIONS_2026-11-15.md` (rehearsal under the same load, 12 CPU workers plus the GPU, a 40 GiB bound on doubled rehearsed peaks, timing stages alone, separate budgets).
- **P9-II** is complete and accepted by the human lead (ADR-0019 §16).

