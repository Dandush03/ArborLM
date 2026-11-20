# ADR-0024 addendum — P10-I-S1 — the quiet-machine load limit becomes a rule measured on this machine

**Status: ADDENDUM, DRAFT 3 — the human lead decided to adopt a measured rule and delegated the four remaining choices to the lead; reviewed once (READY AFTER THE LISTED EDITS; edits applied in draft 2 and not re-read); choice 3 is taken against the reviewer's recommendation; APPROVED FOR IMPLEMENTATION by the lead under the delegation; an independent audit of the implementation follows; no registered stage of P10-I-S1 is approved by this text.** ADR-0024 itself is not edited; where this addendum and ADR-0024 §16 differ on the quiet condition, this addendum applies. Decision 2 is not taken by this text.

`Astra review: NOT_PERFORMED`

Drafted by the arbor-lead subagent (Fable 5.2, model `claude-fable-5-2`, as stated by the session) on the scientific lead's briefs of 2026-11-19. Reviewed by the arbor-auditor subagent (Opus 5.5, `claude-opus-5-5`, as its report states). Times of day are local (UTC−5) unless marked UTC.

## A0. The four remaining choices: delegated by the human lead and taken by the lead

The review ended with four questions for the human lead (its report, last section). On 2026-11-19 (about 23:45 Panama time) the lead reported the four questions; the human lead answered:

> "I'll let you drive s1  not sure about the question but we can always change parameters as long as we add it to the changelog and make them reproducible"

The lead (Claude Fable 5.2) therefore takes the four choices under that delegation, records them here and in `docs/PARAMETER_CHANGELOG.md`, and reports them; he can overrule any of them before the registered run.

**The lead's reading of his words, which the lead stated back to him:** a parameter may be changed with a recorded reason BEFORE the quantity it governs is observed in a registered run; nothing is changed after a registered value is seen, and no scientific threshold is changed by this addendum.

The quotation, the time and the delegation are recorded as the lead relayed them to the drafter; the drafter did not see the human lead's message.

| # | The question, in short | Reviewer recommended | The lead's choice |
|---|---|---|---|
| 1 | The timing-spread rule | yes, in the amended form | **Taken in the amended form** (§A3.4): the whole list is re-timed once; a spread failure never counts toward NOT MEASURED; after three sessions ending in a spread failure the matter returns to the human lead |
| 2 | The machine left untouched: about 80 minutes once for the baseline, and 10 minutes plus the stage each time | yes | **Taken as drafted** (§A3.1, §A3.3) |
| 3 | The Claude application and Claude Code closed, or open and silent | **closed** | **OPEN, with the lead silent** (no tool call, no subagent, no other study process, no virtual machine) during the baseline and during every quiet stage. **Taken against the reviewer's recommendation** (§A3.3, §A7 item 1) |
| 4 | A ceiling of 3.00 when he was told "about 2.2" | yes, with that disclosure | **3.00 stays**, with the disclosure of §A7 item 7; a registered limit above 2.50 is reported to him before the candidate plan is frozen (a report, not a gate) |

## A1. The decision

ADR-0024 §16 requires, at the start of the isolated timing stage (the source of MC-T) and of the read-path throughput stage, a one-minute load average of at most 1.0, polled every 10 minutes for at most 6 hours per session. The figure 1.0 was written without a measurement of this machine's idle load; the specification review of 2026-11-17 had flagged that no record supported an idle load of 1.0–1.2.

On 2026-11-19 the lead put to the human lead, with the evidence of §A2: "Do you want S1's quiet limit changed to a rule measured on this Mac (about 2.2), or kept at 1.0?" The human lead answered:

> "Yes, measured rule"

Earlier the same day he had agreed to test the fixed limit by a quiet run before deciding:

> "in case it work we use it if it does not work then you can reuse it for upper limit"

The decision is that the limit is a measured rule. The figure "about 2.2" was an illustration (1.74 + 0.5 on the log of §A2). **It is not the registered value**: that comes from the study's own window (§A3). The settle period, window, margin and ceiling define that decision. The idle-time condition, the application condition and the spread bound go beyond what he was asked (§A0).

## A2. The evidence (`results/p10is1-quiet-evidence-2026-11-19/`; figures recomputed by the drafter and again by the reviewer from `load_10s_samples.log`)

A counting rehearsal of the candidate plan was run from a plain terminal with the Claude application closed, on mains power, with no other study's process alive (`quiet_run_summary.txt`: "S0 0, S2 0, other 0"). The one-minute load was sampled every 10 s: 1,367 samples, 18:40:27 to 22:28:42, gaps of 10 or 11 s only.

| Part of the log (half-open) | Samples | Min | Median | 95th pct (nearest rank) | Max | At or below 1.0 | What it is |
|---|---|---|---|---|---|---|---|
| 18:40–19:21 | 243 | 0.99 | 1.45 | 4.46 | 5.81 | 6 | the timing stage waiting, then measuring; **not idle** |
| 19:21–20:36 | 449 | 0.99 | 6.23 | 6.71 | 8.09 | 1 | train, ladder, evaluate, baselines; **not idle** |
| 20:36–20:45 | 54 | 1.15 | 1.355 | 1.63 | 1.81 | 0 | the load falling after training (3.25 at 20:34:32, 1.63 at 20:36:03); **not settled** |
| **20:45–22:15** | **538** | **0.92** | **1.31** | **1.74** | **2.88** | **12 (2.2 %)** | machine left alone; the settled idle part |
| 22:15–22:28 | 83 | 0.82 | 1.34 | 4.86 | 6.74 | 10 | the application reopened at about 22:16, other studies resumed at 22:28; **not idle** |

- The lead's figures for 20:45–22:15 are confirmed (minimum 0.92, median 1.31, 95th percentile 1.74, 2.2 % at or below 1.0) with one difference: **538** samples in [20:45:00, 22:15:00), not 544 (539 if 22:15:00 is included). No figure changes.
- **Timing stage:** quiet on the fifth poll. Readings 1.72, 3.40, 1.02, 1.39, 0.99 (`timing_attempt_01.json`: 1.7212, 3.3955, 1.0244, 1.3887, 0.9917); status QUIET RUN; end check clean. `timing_manifest.json`: COMPLETE, 2,478 charged seconds, of which about 2,400 s were waiting for the quiet reading (§A8 item 9). Train, ladder, evaluate and baselines: COMPLETE.
- **Throughput stage:** waiting from 20:36. The first log sample at or after each of the eleven 10-minute instants 20:36 to 22:16 reads 1.63, 1.41, 1.23, 1.44, 1.04, 1.05, 1.49, 1.34, 1.41, 1.85, 1.19: all above 1.0. (With the nearest sample the 22:06 value is 2.00.) The poll readings themselves are not in the evidence folder. The lead stopped the rehearsal at 22:27 (exit code 143). **The rehearsal is INCOMPLETE and cannot be frozen on.**
- Under 1.0 a poll of a settled idle machine passes about one time in 45. Of the 538 settled samples, 512 (95.2 %) are at or below 1.74 and 532 (98.9 %) at or below 2.24.
- Earlier the same day, with the application open, the lead silent for 25 minutes and nothing else running, three readings of the load averages were 1.21, 1.23, 1.27. **These are in the session record only, not in a file.**
- P10-I-S5's precedent (`results/p10is5-run-2026-11-18/OUTCOME.md` on main, disclosure 2): its idle window began about two minutes after another job, its loads ran 3.64, 3.40, 3.10 … 1.49, and it gave a ceiling of 3.53; the settled part gave 2.32. Disclosure 1: a Docker virtual machine ran unnoticed through four stages.

## A3. The amended rule (replacement text for ADR-0024 §16's quiet condition)

**Old text (§16, table row 1, quoted):** "At its start: one-minute load average ≤ 1.0, no process of another ArborLM study's stage alive (P10-S1's `concurrency_check`), mains power, not in Low Power Mode. At its end: no such process alive, and none started during it; otherwise its figures are discarded and the run is repeated. Retried every 10 minutes for up to 6 hours in a session."

**New text, in full.** It applies to the isolated timing stage and to the throughput stage alike.

**A3.1 The quiet baseline.** Before the candidate plan is written, the study's own code takes one idle window on this machine (a new command; it reads no seed, no data and no sealed value).

1. *Samples and arithmetic.* Every 10 s the command records the one-minute load average (`os.getloadavg()[0]`) and the five-minute average, and reads every condition of §A3.3 anew. Each sample is appended to the record as it is taken. **All loads are handled as integers in hundredths: v = round(x, 2) × 100 as an integer. Every difference, comparison, P95 and L is computed in those integers.** The median of an even number of values is the mean of the two middle values, compared exactly (as 2 × median in hundredths). P95 is the nearest-rank 95th percentile: the value at 1-indexed rank ⌈95 n / 100⌉ of the ascending values, in integer arithmetic (rank 114 of 120, rank 342 of 360).
2. *Settle period.* 60 consecutive samples (10 minutes) during which every condition of §A3.3 holds. Their loads are recorded and enter no figure.
3. *Window.* The next 360 consecutive samples (60 minutes). One failure of one condition at one settle or window sample discards the attempt; the next attempt begins again at the settle period.
4. *Sleep and gaps.* The command holds a power assertion against idle sleep (`caffeinate -i -w <pid>`) for the whole attempt. A gap of more than 15 s between two consecutive samples, or a boot time that differs between the first and the last sample, discards the attempt.
5. *Settled, two-sided.* Split the 360 window loads in order into thirds T1, T2, T3 of 120. The window is **settled** if and only if |median(T1) − median(T3)| ≤ 25 hundredths (computed as |2·median(T1) − 2·median(T3)| ≤ 50) **and** |P95(T1) − P95(T3)| ≤ 50 hundredths. A rising load is refused as a falling one is. A window that is not settled is discarded and retaken from the settle period.
6. *The limit and the ceiling.* **L = P95(the 360 window loads) + 50 hundredths.** If L > 300 the window is refused: BASELINE ABOVE CEILING. It is retaken; L is never clamped. An accepted L above 250 is reported to the human lead before the candidate plan is frozen; the report is not a gate.
7. *Bounded, with the fallback to the closed condition.* Attempts follow one another within a session of at most 6 hours; no attempt starts that could not finish inside it (70 minutes). A session without an accepted window is **PAUSED — NO QUIET BASELINE**, with every sample kept, and is rescheduled. **If three baseline sessions in the open-and-silent condition end so (every window unsettled, discarded or above the ceiling), the condition of §A3.3 changes to CLOSED for the baseline and for all stages, by this rule and not by a new decision; the change is recorded in the baseline record and in `docs/PARAMETER_CHANGELOG.md`.** After three further such sessions in the closed condition the matter returns to the human lead. No outcome follows automatically, and the candidate plan cannot be written without a baseline.
8. *Fixed before the plan.* P95, L, the condition (open or closed), both application presences and the SHA-256 of the samples record are written into the config's `[quiet]` section before the candidate plan and are frozen with it. One baseline is used for both stages and for the counting rehearsal. **A baseline and a stage are never taken in different conditions.**
9. *A second baseline.* A second baseline may be taken only for one of: an OS update, a hardware or power-setting change, a change of the condition of §A3.3 decided by the human lead, or a failure of the first found by review. Both are kept; the second replaces the first only for that reason, recorded before the second is taken. None is taken after a timing value of the registered run exists.

**A3.2 A quiet reading.** At a stage's start: the one-minute **and** the five-minute load averages, each rounded with round(x, 2) and taken in hundredths, are both at most L, and every condition of §A3.3 holds. If not, the reading is repeated every 10 minutes for at most 6 hours in a session, each stage with its own session and deadline; every reading is written to the run directory as it is taken, with the condition that failed. At the stage's end: the conditions of §A3.3 hold, no study process started during the stage, and the one-minute load read 120 s after the last measured update, rounded the same way, is at most L. A failed end check discards the figures and the attempt is repeated, as before.

**A3.3 The condition of the machine, the same at every baseline sample and at every stage reading.**

- No process of any ArborLM study's stage alive other than the stage's own (the existing check).
- Mains power; not Low Power Mode; no thermal warning. A thermal warning is any line of `pmset -g therm` other than the three "No … has been recorded" lines.
- `HIDIdleTime` at least 600 s: the human lead is not using the machine. It is read from `ioreg -c IOHIDSystem` in nanoseconds and divided by 10⁹. Under 1.0 this needed no rule; under a limit near 2 a user at the keyboard could pass the load test.
- **No virtual machine.** No process matches a `vm_markers` entry (regular expressions on the full command line, case-insensitive): `com\.apple\.Virtualization\.VirtualMachine`, `qemu-system`, `limactl`, `colima`, `com\.docker\.(backend|virtualization|vmnetd)`, `Docker Desktop`, `vfkit`, `krunkit`, `OrbStack`, `prl_vm_app`, `VirtualBoxVM`, `UTM`. A virtual machine that ran through the baseline is not admitted either: its load is not constant.
- **The Claude application and Claude Code may be open, with the lead silent** (choice 3 of §A0). `app_markers`: `/Applications/Claude.app/Contents/MacOS/Claude` (the desktop application) and, listed separately, any process whose command line runs Claude Code (the `claude` CLI). Both presences are recorded at every sample and reading. **A stage reading is refused unless each of the two presences equals the baseline's.**
- *Silent* means: from the launch of a baseline attempt or a quiet stage until it reports, the lead makes no tool call, no subagent runs, and no other Claude session works on this machine. The baseline and each quiet stage are launched by the lead from the session as a single command with its own `timeout` and its output redirected to a file; the command's exit is the report, and the lead does not poll it (the condition P10-I-S5's audit required). **Code cannot verify the silence.** What it records is the top ten processes at start and end, which will show the application, and the load itself.
- *The closed condition* (only by the fallback of §A3.1 item 7): no process matches either application marker at any baseline sample or stage reading, and the baseline and stages are started from a plain terminal by the same launch scripts.
- At every baseline attempt's start and end, and at each stage's start and end, the ten processes with the highest CPU share are recorded (`ps -Aro pid,pcpu,comm`). Recorded, not a condition. The per-sample process check uses a light listing (`ps -Ao pid,command`), and the sampler records its own CPU seconds: its own calls add a little load that the stages do not have.

**A3.4 Validity of the timing itself (new; taken by the lead under the delegation, §A0 choice 1).** For each (arm, slots) item the stage records the three per-repeat values of CPU-seconds and wall-seconds per update. s = (max − min) / median of the three CPU values, in floating point from the recorded values; the median of three is the middle value. An attempt is valid only if s ≤ 0.05 at every item. If any item has s > 0.05, the whole attempt is discarded (TIMING SPREAD) and the full item list is timed again once in the same session, after a new quiet reading of §A3.2; readings of two attempts are never combined, and both are kept and printed. If the second attempt also has an item above the bound, the session ends **PAUSED — TIMING SPREAD**. A TIMING SPREAD session is not a PAUSED — QUIET CONDITION NOT MET session: it is recorded with its own status, does not count towards the six sessions of §A3.5, and cannot support a NOT MEASURED decision. After three TIMING SPREAD sessions the matter returns to the human lead; no outcome follows automatically. The ratio of CPU to wall seconds per repeat is printed and is not a condition.

**A3.5 PAUSED and NOT MEASURED: unchanged.** A session without a quiet run is PAUSED — QUIET CONDITION NOT MET and rescheduled. A timeout never ends a stage NOT MEASURED. NOT MEASURED is recorded only after the first attempt and five rescheduled attempts have ended PAUSED — QUIET CONDITION NOT MET, by the explicit decision of §16 carrying the table of §10. The path is not shortened. Attempts made under the 1.0 limit, in any earlier directory, do not count. PAUSED — NO QUIET BASELINE and PAUSED — TIMING SPREAD sessions do not count.

## A4. Thresholds fixed now, with reasons

| Figure | Value | Reason |
|---|---|---|
| Window | 360 samples, 60 min | On the log of §A2, 30-minute windows of the settled part give P95 from 1.50 to 2.10; 60-minute windows give 1.61 to 1.88. The shorter window doubles the spread of a figure that is frozen |
| Settle | 60 samples, 10 min | The one-minute average forgets a past load with a time constant of one minute: after 10 minutes less than 0.01 % of it remains |
| Settled tests | 25 (medians) and 50 (P95s), both two-sided | See below the table |
| Percentile | 95, nearest rank | ADR-0028 §8 and `studies/p10is5/core.py` |
| Margin | 50 | ADR-0028's. One extra runnable thread lasting about 40 s raises the one-minute average by about 0.5 (1 − e^(−40/60) = 0.49); a sustained extra thread raises it by 1.0 |
| Ceiling on L | 300 | It lies between the figures of clean windows on this machine (2.11 to 2.38 tonight; 2.32 from S5's settled part) and the one known unsettled figure (3.53). It does not by itself separate contaminated windows, which reached 2.99 on the load tests of draft 1 (§A7 item 7) |
| Idle time | 600 s | ADR-0028 §8 |
| End load delay | 120 s | ADR-0028 §8: the stage's own thread has left the average |
| Timing spread | 0.05 | A quarter of the smallest cost margin a rule reads (0.8). It is also the figure of the throughput CV limit, which is a different statistic: for three repeats a range of 0.05 corresponds to a CV of about 0.03. In P10-S1's registered timing (same function, same machine, start load 0.98; `results/p10s1-run-2026-11-17/results.json`) the 16 items have s from 0.0017 to 0.0364, 15 of them at most 0.013. The bound is about 1.4 times the worst of them |

**The settled tests on tonight's log.** Draft 1's tests were one-sided (a fall only). The review showed that they accepted 80 window positions with the 22:15–22:28 rise in their last third (the application reopened, other studies resumed), giving L from 2.38 to 2.99. The lead ruled that the tests are two-sided, at the same two figures. The following counts are the drafter's, computed after the review and **not checked by the reviewer**, with load conditions only (the log records no process, power or idle-time state):

- Of 948 possible attempt starts (settle plus window), 242 are accepted, 695 are not settled and 11 are above the ceiling. Accepted L runs from 2.11 to 2.43. An attempt started at 20:36:03, after the training, is accepted with L = 2.12.
- Of the 179 windows wholly inside 20:45–22:15, **170 are accepted (L 2.11 to 2.24) and 9 are refused** (their L would have been 2.25 to 2.38). They are refused on the P95 test, for the rise at 22:00–22:15 while the machine was left alone (maximum 2.88). A refused clean window costs a retake, not a looser limit. Over those 179 windows the median difference runs from −0.08 to 0.18 and the P95 difference from −0.59 to 0.31.
- **9 accepted windows still end after 22:16**, with L 2.38 to 2.43. The load tests do not refuse them.

**What else guards the end of a window.** The conditions of §A3.3 at every sample: idle time, study processes, virtual machines and the application markers would each have refused the 22:16 reopening. A rising load from a source those conditions do not see (a backup, indexing) and too small for the two-sided tests is caught only by the ceiling. The stage's own readings (§A3.2) do not repair a loose L.

The two-sided form was ruled after seeing that the one-sided form failed on this log; the figures 25 and 50 are draft 1's and were not re-chosen. The settled tests, the window length, the ceiling and the spread bound were all chosen after seeing tonight's load log, S5's window and P10-S1's registered spreads. They are set knowing **no timing value of P10-I-S1** (§A7 item 4).

## A5. What this changes scientifically

MC-T is single-thread process CPU-seconds per update from the isolated timing stage (§8.2). It is read by labels: §9.1's rows apply "where MC-T is measured", MC-C exists only with it (§8.2), C-EFFICIENCY's reading E-T uses it (§9.5), and CAPACITY-POSITIVE is unreachable without it (§10). Throughput is a reported reading and enters no outcome.

- **What a looser load limit cannot do.** CPU-seconds do not count time the thread waits for a core. On 18 cores, a load of 2 to 3 does not make a one-thread process queue, and queueing would lengthen wall time, not CPU time.
- **What it can do.** Other work can raise CPU-seconds per update through shared caches and memory bandwidth, through the clock and thermal state, and through the scheduler placing the thread on a slower class of core. Items are timed one after another, so a burst falls on some items and not others. Labels read **ratios** of costs between cells. An uneven inflation can move a ratio in either direction. Through the start condition alone, it cannot be shown that a label becomes easier or harder for the store.
- **What the stage records today.** `studies/p10s1/timing.py` returns the per-repeat CPU and wall values, but `studies/p10is1/stages.py::measure_timing` keeps only the median CPU value, the median wall value and the peak memory of each item. The concurrent-to-isolated ratio belongs to the measuring rehearsal. The throughput CV limit is descriptive. Nothing records the load during the stage.
- **What NOT MEASURED does, and why the spread bound may not lead to it.** A NOT MEASURED decision is not neutral. It removes CAPACITY-POSITIVE, STORE NOT BEHIND, STORE HOLDS MORE and EFFICIENCY-POSITIVE, and it also removes the MC-T and MC-C conditions of §9.1 row 4 (so CAPACITY, CAPACITY STEP and CAPACITY_SUPPORTED become easier and CAPACITY-NEGATIVE (a) harder), the MC-T and MC-C routes to DENSE AHEAD, and the E-T routes to EFFICIENCY-NEGATIVE and DENSE FASTER. In P10-S1, MC-T was a reading in which D-OQ was faster. A rule that discards contended timing attempts and counted them towards NOT MEASURED could therefore turn a failing MC-T condition into an absent one; §A3.4 does not count them. The quiet-reading conditions added here (five-minute average, idle time, end load, virtual machines, application presence) only add refusals; they change no value and do not shorten the path to NOT MEASURED.

The directions, row by row (the reviewer's table; it compares MC-T NOT MEASURED with a measured MC-T on the same data, and "easier" means easier for the store):

| Row (ADR-0024) | Reads | Under MC-T NOT MEASURED |
|---|---|---|
| §9.1 row 4 CAPACITY (Δ_MC ≥ 0.5 in MC-T and MC-C; MC-SHORT in MC-T fails) | MC-T, MC-C | conditions drop: **easier** (printed MATCHED COMPUTE IN MC-A ONLY) |
| §9.1 step class CAPACITY STEP; arm classes CAPACITY_SUPPORTED, CAPACITY_ONE_TRANSITION | via row 4 | **easier** |
| §9.1 arm class CAPACITY_NOT_SUPPORTED ("no CAPACITY STEP") | via row 4 | harder to reach, i.e. **easier for the store** |
| §9.2 DENSE AHEAD (a lead in MC-T or MC-C counts) | MC-T, MC-C | two routes to a dense lead removed: **easier for the store** |
| §9.2 STORE NOT BEHIND; arm NOT BEHIND DENSE | MC-T required | unreachable: harder |
| §9.2 STORE HOLDS MORE (cost in both measures) | MC-T | unreachable: harder |
| §9.3 CAPACITY-POSITIVE | via STORE NOT BEHIND | unreachable: harder |
| §9.3 CAPACITY-NEGATIVE (a) | via CAPACITY_NOT_SUPPORTED | **harder to reach (easier for the store)** |
| §9.3 CAPACITY-NEGATIVE (b) | CAPACITY_SUPPORTED and DENSE AHEAD | mixed |
| §9.5 EFFICIENCY-POSITIVE | E-T | unreachable: harder |
| §9.5 EFFICIENCY-NEGATIVE ("both in E-T"; DENSE FASTER in a reading) | E-T | E-T routes removed: **easier for the store** |

So NOT MEASURED removes the store's positives and also removes routes to negatives; the outcome lines move towards INCONCLUSIVE from both sides. ADR-0024 §10's sentence "no negative becomes unreachable" is about reachability, not ease, and is not edited. This addendum changes no threshold of §7–§9 and adds no route to NOT MEASURED.

- **What is lost.** P10-S1's timing started at 0.98. A timing started near 2 is not the same measurement condition, and MC-T of the two studies is compared only with that stated.

## A6. What is unchanged

Every scientific threshold, label, rule, seed, cell, arm, grid and run length of ADR-0024; the stages that run alone and the meaning of "alone"; the 10-minute poll and the 6-hour session; the six-session path to NOT MEASURED and its decision file; training not starting while the timing stage is PAUSED; THROUGHPUT PENDING; §16.1; the cap rule and the 60-hour limit; the seed registry. ADR-0024's text and all P1–P10 records are not edited.

## A7. Disclosures

1. **Choice 3 (the application open, the lead silent) is taken against the reviewer's recommendation, which was "closed".** The reviewer's reasons: the stages need the human lead away anyway, the evidence of 2026-11-19 was taken with the application closed, and code cannot check that the agent is silent. The lead's reasons:
   - (a) The limit is measured by the study's own window in the same condition in which the stages run, and the code refuses a stage whose application presence differs from the baseline's. So the rule calibrates itself to the condition, and a noisier condition yields refused or unsettled windows, not a looser reading.
   - (b) The timing-spread bound and the two-sided settled test guard the reading itself.
   - (c) With the application closed every quiet stage needs the human lead at the keyboard, and the lead cannot see or record what happens; this cost four hours of two other studies on 2026-11-19.
   - (d) The evidence is thin in both directions (open and silent: three readings 1.21–1.27 in the session record; closed: median 1.31 over 90 minutes), which the reviewer also says.

   **What remains open under this choice, stated by the drafter.** Reason (a) holds for a load that rises, falls or fails a condition. A steady extra load during the baseline that the conditions do not see is not refused: it raises P95 and so L, up to the ceiling. The silence of the lead is a rule of conduct that no code checks. What bounds the effect is the ceiling, the report above 2.50, the spread bound and the fallback of §A3.1 item 7. This draft's text on choice 3 has not been reviewed.
2. The four choices of §A0 were taken by the lead under a delegation the human lead gave in the words quoted there, having said he was "not sure about the question". He can overrule any of them before the registered run.
3. The change is made **after observing** that the fixed limit is met on this machine only by luck (2.2 % of settled samples), and **knowing that the rehearsal's timing stage completed once under the old limit**.
4. No registered value of P10-I-S1 exists. The calibration's sealed values are unopened. **What was opened of the incomplete rehearsal's run directory:** the lead (Claude Fable 5.2) opened the timing stage's manifest and its quiet-attempt record (the load readings) and the manifests of train, ladder, evaluate and baselines; it did not open `timing/timing.json` or any item record. The drafter read the same files in the evidence folder and no other. The reviewer's statement, copied from its report: "Not opened: any `timing.json` (rehearsal or measuring), any sealed value, any registered record of P10-I-S1."
5. **The rehearsal's completed timing record** may not be used for any registered reading, to set or adjust any threshold, or to accept, discard or repeat any later timing attempt. Once the registered timing record exists and is fixed, the two may be compared in the report as a description, labelled as rehearsal against registered and with both start loads printed, and only if their settings (updates, repeats, items) are equal.
6. The incomplete rehearsal directory and the evidence folder are kept. The script the lead used on 2026-11-19 (`experiments/_scratch/s1_quiet/run_s1_quiet.sh` in the main checkout) is not part of the study.
7. **The ceiling.** The human lead was told "about 2.2". The ceiling admits up to 3.00. On the log of §A2, under the two-sided tests, clean windows give L from 2.11 to 2.24, and accepted windows that run into the 22:16 reopening give up to 2.43 on the load tests alone (the drafter's counts, §A4; under draft 1's one-sided tests the reviewer found 2.11 to 2.38 and up to 2.99). That log was taken with the application closed; no window has been taken in the open condition. A registered limit above 2.50 is reported to him before the candidate plan is frozen; the report is not a gate.
8. Three conditions were added that the human lead was not asked about in the question quoted in §A1: idle time, the application condition and the spread bound. They are now covered by the delegation of §A0.
9. Draft 1 said "No label becomes easier for the store". The review found that false through the NOT MEASURED route (finding B1); the sentence is removed and §A5 states the directions.

## A8. Requirements for the implementer (approved for implementation by the lead under the delegation of §A0; an independent implementation audit follows; no registered stage is approved)

0. **Launch.** The baseline and each quiet stage have a launch script that runs as one command with its own `timeout` above the session's deadline and its output redirected to a file. The keep-awake watcher (`caffeinate -i -w <pid>`) is started inside the stage's own process family, and the own-process set of the study-process check covers the stage's ancestors and descendants, so that the watcher is never counted as another study's process (P10-I-S5's defect, `OUTCOME.md` disclosure 6); a test shows it. The lead records each of the four choices of §A0, and any fallback to the closed condition, in `docs/PARAMETER_CHANGELOG.md` with its reason and the command that reproduces the figure.
1. **The baseline command** (§A3.1), in new code beside `quiet.py`: a samples file written line by line, and a record with the attempts, the discarded windows and their reasons, the thirds' medians and P95s, P95, L, the condition (open or closed), the count of PAUSED sessions in each condition, both application presences, the top processes, the sampler's own CPU seconds, the OS build and boot time. Every wait has a deadline. The accepted record and its samples are copied into `results/` and committed before the candidate plan.
2. **`[quiet]`** gains, loads in hundredths: `baseline_provisional` (true until the figures are written), `load_p95`, `load_limit`, `load_margin = 50`, `load_ceiling = 300`, `percentile = 95`, `baseline_samples = 360`, `baseline_interval_seconds = 10`, `settle_samples = 60`, `settled_median_diff_max = 25`, `settled_p95_diff_max = 50`, `sample_gap_max_seconds = 15`, `hid_idle_min_seconds = 600`, `end_load_delay_seconds = 120`, `timing_spread_max = 0.05`, `timing_spread_sessions_to_human_lead = 3`, `vm_markers` and `app_markers` exactly as in §A3.3, `condition` ("open" or "closed"), `app_present` and `cli_present` (from the baseline), `open_sessions_before_closed = 3`, `load_report_above = 250`, `baseline_record_sha256`. `load_average_max` is removed, not left at 1.0. `core.py`'s list of required keys and the config test follow this addendum.
3. **The candidate plan refuses while `baseline_provisional` is true. The freeze re-derives P95, L, the condition and both presences from the committed samples and refuses on any difference**, on an unsettled window, or on L above the ceiling. It prints a notice when L is above 250.
4. **`quiet.py`:** the reading of §A3.2 and §A3.3 in integer hundredths; the end check with the delayed load; the failed condition recorded with each reading; each reading appended to the run directory as it is taken. Tests: nearest rank at 120 and 360; the median of an even number of values; each settled test at its boundary on both sides, with the float pairs that fail in floating point (0.54 and 0.29 at 0.25); the ceiling at 300 and 301; a discarded window; a gap; each marker; a stage refused when either application presence differs from the baseline's, in each direction; the change to the closed condition after exactly three open sessions and not before; the idle-time unit conversion; the thermal parse; five-minute average above L with the one-minute below; the end load; no path writes NOT MEASURED.
5. **`measure_timing`:** keep `runs` and `wall_runs` per item and the CPU-to-wall ratio per repeat; §A3.4's rule and its own status. In each quiet stage's record keep the one-minute load every 10 s during the stage (descriptive). Tests: s at 0.05 and just above; a second attempt that fails; a TIMING SPREAD session not counted by `paused_attempts`; the six-session decision refusing when the sessions it names include a TIMING SPREAD one.
6. **A separate bounded wait for each quiet stage.** Timing and throughput each have their own session and deadline, and each launch script its own `timeout` above it. In the counting rehearsal a PAUSED quiet stage is retried by itself in the same directory without rerunning completed stages; the rehearsal is COMPLETE only when both have a quiet run.
7. **The counting rehearsal is rerun in full, in a new directory,** against the candidate plan written after the baseline. The incomplete one is kept.
8. **Seed gate: unaffected.** The baseline and the quiet rule read no seed and no data, and no allocation changes.
9. **Caps.** The charged seconds of the timing and throughput stages are the measuring seconds (from the quiet reading to the end check, including the 120-s delay and any re-timing); the waiting of §A3.2 and of the baseline is recorded per session and is not charged, as in ADR-0028 §9. The cap rule is unchanged. The per-stage caps (`timing_hours`, `throughput_hours`) apply to those charged seconds and are enforced for these two stages; the review found that today `execute_stage` charges the wall time since the stage began, waiting included, and enforces only the study total for them. The projection and the cap figures are otherwise unaffected: the projection's timing figure (0.031 h) contains no waiting. The implementer reports before the candidate plan: the charged and waiting seconds of every earlier rehearsal's timing stage, and whether any figure of the projection contains waiting; if one does, the projection of §17.1 is recomputed by its own rule and returns to the lead.
10. Anything this text leaves to a guess is reported to the lead before code is written; where two readings are possible, the stricter one for the store applies.

## A9. Review record

| Round | Reviewer | Text | Verdict | Disposition |
|---|---|---|---|---|
| 1 | arbor-auditor subagent, Opus 5.5 (`claude-opus-5-5`), 2026-11-19; report `experiments/_scratch/audits/REVIEW_ADR-0024-QUIET-ADDENDUM.md` | draft 1, SHA-256 `50946536fbab95978b27110c8f6617939e7cdbf2be95553264b5e824fff560b6` | READY AFTER THE LISTED EDITS (1 blocking, 7 required, 5 advisory); not ready as it stood | B1, R2 to R7 applied with the reviewer's texts. R1: the reviewer left a rise test `PENDING LEAD REVIEW`; the lead ruled it two-sided, on both tests (§A3.1 item 5); the counts under that ruling in §A4 are the drafter's and unreviewed. A1, A2, A4, A5 applied. A3 (refuse only when the application is present at the stage and absent at the baseline) not adopted: the lead requires equal presence in both directions |
| — | — | draft 2 | not re-read | — |
| — | none | draft 3 (this text): the four questions answered by the lead under the human lead's delegation (§A0) | not reviewed | Choices 1, 2 and 4 follow the reviewer's recommendation. **Choice 3 is taken against it** (§A7 item 1). The fallback to the closed condition, the launch rule and the report above 2.50 are new in this draft and unreviewed. An independent audit of the implementation follows |

The review is not Astra validation and not human approval.
