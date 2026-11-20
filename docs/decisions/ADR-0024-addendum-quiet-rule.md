# ADR-0024 addendum — P10-I-S1 — the quiet-machine load limit becomes a rule measured on this machine

**Status: ADDENDUM — the decision of the human lead is recorded (2026-11-19); this text is a DRAFT until independently reviewed.** Nothing here is approved for execution. ADR-0024 itself is not edited; where this addendum and ADR-0024 §16 differ on the quiet condition, this addendum applies once reviewed and accepted. Decision 2 is not taken by this text.

`Astra review: NOT_PERFORMED`

Drafted by the arbor-lead subagent (Fable 5.2, model `claude-fable-5-2`, as stated by the session) on the scientific lead's brief of 2026-11-19. Times of day are local (UTC−5) unless marked UTC.

## A1. The decision

ADR-0024 §16 requires, at the start of the isolated timing stage (the source of MC-T) and of the read-path throughput stage, a one-minute load average of at most 1.0, polled every 10 minutes for at most 6 hours per session. The figure 1.0 was written without a measurement of this machine's idle load; the specification review of 2026-11-17 had flagged that no record supported an idle load of 1.0–1.2.

On 2026-11-19 the lead put to the human lead, with the evidence of §A2: "Do you want S1's quiet limit changed to a rule measured on this Mac (about 2.2), or kept at 1.0?" The human lead answered:

> "Yes, measured rule"

Earlier the same day he had agreed to test the fixed limit by a quiet run before deciding:

> "in case it work we use it if it does not work then you can reuse it for upper limit"

The decision is that the limit is a measured rule. The figure "about 2.2" was an illustration (1.74 + 0.5 on the log of §A2). **It is not the registered value**: that comes from the study's own window (§A3).

## A2. The evidence (`results/p10is1-quiet-evidence-2026-11-19/`; figures recomputed by the drafter from `load_10s_samples.log`)

A counting rehearsal of the candidate plan was run from a plain terminal with the Claude application closed, on mains power, with no other study's process alive (`quiet_run_summary.txt`: "S0 0, S2 0, other 0"). The one-minute load was sampled every 10 s: 1,367 samples, 18:40:27 to 22:28:42, no gap above 15 s.

| Part of the log | Samples | Min | Median | 95th pct (nearest rank) | Max | At or below 1.0 | What it is |
|---|---|---|---|---|---|---|---|
| 18:40–19:21 | 243 | 0.99 | 1.45 | 4.46 | 5.81 | 6 | the timing stage waiting, then measuring; **not idle** |
| 19:21–20:36 | 449 | 0.99 | 6.23 | 6.71 | 8.09 | 1 | train, ladder, evaluate, baselines; **not idle** |
| 20:36–20:45 | 54 | 1.15 | 1.355 | 1.63 | 1.81 | 0 | the load falling after training (3.25 at 20:34:32, 1.63 at 20:36:03); **not settled** |
| **20:45–22:15** | **538** | **0.92** | **1.31** | **1.74** | **2.88** | **12 (2.2 %)** | machine left alone; the settled idle part |
| 22:15–22:28 | 83 | 0.82 | 1.34 | 4.86 | 6.74 | 10 | the application reopened at about 22:16, other studies resumed at 22:28; **not idle** |

- The lead's figures for 20:45–22:15 are confirmed (minimum 0.92, median 1.31, 95th percentile 1.74, 2.2 % at or below 1.0) with one difference: the drafter counts **538** samples in [20:45:00, 22:15:00), not 544. No figure changes.
- **Timing stage:** quiet on the fifth poll. Readings 1.72, 3.40, 1.02, 1.39, 0.99 (`timing_attempt_01.json`: 1.7212, 3.3955, 1.0244, 1.3887, 0.9917); status QUIET RUN; end check clean. `timing_manifest.json`: COMPLETE, 2,478 charged seconds over a span of 41 min 18 s, which contains the four failed polls. Train, ladder, evaluate and baselines: COMPLETE.
- **Throughput stage:** waiting from 20:36. The log's samples at the eleven 10-minute instants 20:36 to 22:16 are 1.63, 1.41, 1.23, 1.44, 1.04, 1.05, 1.49, 1.34, 1.41, 1.85, 1.19: all above 1.0, between 1.04 and 1.85. The poll readings themselves are not in the evidence folder. The lead stopped the rehearsal at 22:27 (exit code 143). **The rehearsal is INCOMPLETE and cannot be frozen on.**
- Under 1.0 a poll of a settled idle machine passes about one time in 45. Of the 538 settled samples, 512 (95.2 %) are at or below 1.74 and 532 (98.9 %) at or below 2.24.
- Earlier the same day, with the application open, the lead silent for 25 minutes and nothing else running, three readings of the load averages were 1.21, 1.23, 1.27. **These are in the session record only, not in a file**; they are three readings and say nothing about a 95th percentile.
- P10-I-S5's precedent (`results/p10is5-run-2026-11-18/OUTCOME.md` on main, disclosure 2): its idle window began about two minutes after another job, its loads ran 3.64, 3.40, 3.10 … 1.49, and it gave a ceiling of 3.53; the settled part gave 2.32. Disclosure 1: a Docker virtual machine ran unnoticed through four stages.

## A3. The amended rule (replacement text for ADR-0024 §16's quiet condition)

**Old text (§16, table row 1, quoted):** "At its start: one-minute load average ≤ 1.0, no process of another ArborLM study's stage alive (P10-S1's `concurrency_check`), mains power, not in Low Power Mode. At its end: no such process alive, and none started during it; otherwise its figures are discarded and the run is repeated. Retried every 10 minutes for up to 6 hours in a session."

**New text, in full.** It applies to the isolated timing stage and to the throughput stage alike.

**A3.1 The quiet baseline.** Before the candidate plan is written, the study's own code takes one idle window on this machine (a new command; it reads no seed, no data and no sealed value).

1. *Samples.* Every 10 s the command records the one-minute load average (`os.getloadavg()[0]`, rounded with `round(x, 2)`; every later computation uses the recorded value), the five-minute average, the processes of §A3.3 and the power state. Each sample is appended to the record as it is taken.
2. *Settle period.* 60 consecutive samples (10 minutes) during which every condition of §A3.3 holds. Their loads are recorded and enter no figure.
3. *Window.* The next 360 consecutive samples (60 minutes), with every condition of §A3.3 holding at each. A failed condition at any settle or window sample, a gap of more than 15 s between two consecutive samples, or a changed boot time discards the attempt; the next attempt begins again at the settle period.
4. *Settled.* Split the 360 window loads in order into thirds T1, T2, T3 of 120. The window is **settled** if and only if median(T1) − median(T3) ≤ 0.25 **and** P95(T1) − P95(T3) ≤ 0.50. P95 is the nearest-rank 95th percentile: the value at 1-indexed rank ⌈0.95 n⌉ of the ascending values (rank 114 of 120, rank 342 of 360). A window that is not settled is discarded and retaken from the settle period.
5. *The limit.* **L = P95(the 360 window loads) + 0.50**, to two decimals.
6. *Ceiling.* If L > 3.00 (a window P95 above 2.50) the window is refused: BASELINE ABOVE CEILING. It is retaken; L is never clamped to the ceiling.
7. *Bounded.* Attempts follow one another within a session of at most 6 hours; no attempt starts that could not finish inside it (70 minutes). A session without an accepted window is **PAUSED — NO QUIET BASELINE**, with every sample kept, and is rescheduled. After three such sessions the matter returns to the human lead; no outcome follows automatically, and the candidate plan cannot be written without a baseline.
8. *Fixed before the plan.* P95, L, the window's condition (§A3.3) and the SHA-256 of the samples record are written into the config's `[quiet]` section before the candidate plan and are frozen with it. One baseline is used for both stages and for the counting rehearsal. A second baseline may be taken only before the candidate plan is written, for a stated reason recorded beside the first, which is kept; never after a timing value of the registered run exists.

**A3.2 A quiet reading.** At a stage's start: the one-minute **and** the five-minute load averages are both at most L, and every condition of §A3.3 holds. If not, the reading is repeated every 10 minutes for at most 6 hours in a session, each stage with its own session and deadline; every reading is written to the run directory as it is taken. At the stage's end: the conditions of §A3.3 hold, no study process started during the stage, and the one-minute load read 120 s after the last measured update is at most L. A failed end check discards the figures and the attempt is repeated, as before.

**A3.3 The condition of the machine, the same for the window and for the stages.**

- No process of any ArborLM study's stage alive other than the stage's own (the existing check).
- Mains power; not Low Power Mode; no thermal warning (`pmset -g therm`).
- `HIDIdleTime` at least 600 s: the human lead is not using the machine. Under 1.0 this needed no rule; under a limit near 2 an active user could pass it.
- **The Claude application may be open.** While a window or a quiet stage runs, the lead makes no tool call and no subagent or other study runs; the command is started by a launch script and the lead does not poll it. Code cannot verify the lead's silence; it records whether the application's process is present, and **the stage refuses unless that presence equals the baseline's**.
- Virtual machines: no process matching the config's `vm_markers` (Colima, Lima, Docker, QEMU, the Virtualization framework) is alive at a stage reading unless one matching the same marker was alive at every sample of the baseline window.
- At every baseline attempt, and at each stage's start and end, the ten processes with the highest CPU share (`ps -Aro pid,pcpu,comm`) are recorded. Recorded, not a condition.

*Why one condition and not two windows.* The evidence (open and silent: 1.21 to 1.27, three readings; closed: median 1.31 over 538 samples) does not show that an open, silent application adds load, and it is too thin to show that it adds none. The rule does not depend on the answer: the limit is measured in the condition the stages will run in, and the code refuses a stage whose condition differs. If the human lead prefers the application closed, the baseline is taken closed and the stages run closed.

**A3.4 Validity of the timing itself (new).** For each (arm, slots) item the stage keeps the three per-repeat values of CPU-seconds per update and of wall-seconds per update. Let s = (max − min) / median of the three CPU values. The item is valid if s ≤ 0.05. An item with s > 0.05 is timed once more in full (warm-up and three repeats) after the last item of the same attempt; both sets are kept in the record; the second is used only if its s ≤ 0.05. If any item is still invalid the attempt's figures are discarded (TIMING SPREAD), the attempt is recorded as the existing end-check discards are, and the stage is repeated. MC-T remains all or nothing. The ratio of CPU to wall seconds per repeat is printed and is not a condition: no record gives its usual value.

**A3.5 PAUSED and NOT MEASURED: unchanged.** A session without a quiet run is PAUSED — QUIET CONDITION NOT MET and rescheduled. A timeout never ends a stage NOT MEASURED. NOT MEASURED is recorded only after the first attempt and five rescheduled attempts have ended PAUSED, by the explicit decision of §16 carrying the table of §10. The path is not shortened: with a measured limit a settled machine should pass most readings, so six PAUSED sessions would mean the machine's condition has changed, which is a reason to look, not to decide sooner. Attempts made under the 1.0 limit, in any earlier directory, do not count. PAUSED — NO QUIET BASELINE sessions are not stage attempts.

## A4. Thresholds fixed now, with reasons

| Figure | Value | Reason |
|---|---|---|
| Window | 360 samples, 60 min | On the log of §A2, 30-minute windows of the settled part give P95 from 1.50 to 2.10; 60-minute windows give 1.61 to 1.88. P10-I-S5's 10 minutes is too short for a figure that is frozen |
| Settle | 60 samples, 10 min | The one-minute average forgets a past load with a time constant of one minute: after 10 minutes less than 0.01 % of it remains. The tests of item 4 guard what the settle period cannot see |
| Settled tests | 0.25 (medians), 0.50 (P95s), falling only | They test the failure P10-I-S5 had. On tonight's log the 60-minute windows starting 20:36 to 21:15 give at most 0.15 and 0.20; windows starting 20:26 to 20:33, which include the fall, give 2.33 to 2.94 on the second test; S5's own window gives 0.755 and 1.71. A rise late in a window does not fail: it is idle variation and belongs in the percentile |
| Percentile | 0.95, nearest rank | ADR-0028 §8 and `studies/p10is5/core.py` |
| Margin | 0.50 | ADR-0028's. One extra runnable thread lasting about 40 s raises the one-minute average by about 0.5 (1 − e^(−40/60) = 0.49); a sustained extra thread raises it by 1.0. The margin admits a brief burst above the window's own 95th percentile and not a second sustained job |
| Ceiling on L | 3.00 | Every settled figure seen on this machine is below it (2.11 to 2.38 on tonight's 60-minute windows; 2.32 from S5's settled part) and the one known unsettled figure is above it (3.53). At 3.0 the other runnable threads average half of the machine's six fastest-class cores (`hw.perflevel0.physicalcpu` = 6) |
| Idle time | 600 s | ADR-0028 §8 |
| End load delay | 120 s | ADR-0028 §8: the stage's own thread has left the average |
| Timing spread | 0.05 | The study's registered stability limit for throughput (`throughput_cv_max`); a quarter of the smallest cost margin a rule reads (0.8). In P10-S1's registered timing (same function, same machine, started at load 0.98; `results/p10s1-run-2026-11-17/results.json`) the 16 items have s from 0.0017 to 0.0364, 15 of them at most 0.013, so the bound is reachable on a quiet machine |

The settled tests, the window length, the ceiling and the spread bound were chosen after seeing tonight's load log, S5's window and P10-S1's registered spreads. They are set knowing **no timing value of P10-I-S1**: the rehearsal's timing record was not opened for this text, and no registered value exists.

## A5. What this changes scientifically

MC-T is single-thread process CPU-seconds per update from the isolated timing stage (§8.2). It is read by labels: the CAPACITY rows apply "where MC-T is measured" (§9.1), MC-C exists only with it (§8.2), C-EFFICIENCY's reading E-T uses it (§9.5), and CAPACITY-POSITIVE is unreachable without it (§10). Throughput is a reported reading and enters no outcome. So the quiet condition protects a quantity a label reads.

- **What a looser load limit cannot do.** CPU-seconds do not count time the thread waits for a core. On 18 cores, a load near 2 does not make a one-thread process queue, and queueing would lengthen wall time, not CPU time.
- **What it can do.** Other work can raise CPU-seconds per update through shared caches and memory bandwidth, through the clock and thermal state, and through the scheduler placing the thread on a slower class of core, where a CPU-second does less work. Items are timed one after another, so a burst falls on some items and not others. Labels read **ratios** of costs between cells (the matched snapshot of §8.2, the 0.8 factors of §9.5). An uneven inflation can move a ratio in either direction, so the looser limit cannot be called conservative for the store or against it.
- **What the stage records today.** `studies/p10s1/timing.py` returns the per-repeat CPU and wall values, but `studies/p10is1/stages.py::measure_timing` keeps only the median CPU value, the median wall value and the peak memory of each item: the repeats and their spread are dropped. The concurrent-to-isolated ratio belongs to the measuring rehearsal, is a wall-time figure for the cost projection, and does not watch the timing stage. Throughput has five repeats and a CV limit of 0.05 that labels a reading STABLE or UNSTABLE; it is descriptive.
- **Hence §A3.4.** With the start condition loosened, the registered bound on the spread between repeats is what keeps a contended reading out of MC-T. It applies to every arm and size alike, it can only discard an attempt (the stage is then PAUSED), and it never yields a label. A re-timed item is chosen by its spread, never by its value; both sets are printed.
- **No label becomes easier for the store.** No threshold of §7–§9 changes. MC-T is still all or nothing; a NOT MEASURED decision still removes only store-favouring labels (§10). The added conditions (five-minute average, idle time, end load, spread, virtual machines) are stricter than §16 in every respect except the value of the load limit.
- **What is lost.** P10-S1's timing started at 0.98. A timing started near 2 is not the same measurement condition, and MC-T of the two studies is compared only with that stated.

## A6. What is unchanged

Every scientific threshold, label, rule, seed, cell, arm, grid and run length of ADR-0024; the stages that run alone and the meaning of "alone"; the 10-minute poll and the 6-hour session; the six-session path to NOT MEASURED and its decision file; training not starting while the timing stage is PAUSED; THROUGHPUT PENDING; §16.1; the budget rule and the 60-hour cap; the seed registry. ADR-0024's text and all P1–P10 records are not edited.

## A7. Disclosures

1. The change is made **after observing** that the fixed limit is met on this machine only by luck (2.2 % of settled samples), and **knowing that the rehearsal's timing stage completed once under the old limit**.
2. No registered value of P10-I-S1 exists. The calibration's sealed values are unopened. The drafter read the rehearsal's manifests and `timing_attempt_01.json` (load readings only) and did not read its `timing.json`.
3. **The rehearsal's completed timing record** may not be used for any registered reading, to set or adjust any threshold, or to accept, discard or repeat any later timing attempt. Once the registered timing record exists and is fixed, the two may be compared in the report as a description, labelled as rehearsal against registered and with both start loads printed, and only if their settings (updates, repeats, items) are equal; otherwise the comparison is not made.
4. The incomplete rehearsal directory and the evidence folder are kept. The script the lead used on 2026-11-19 (`experiments/_scratch/s1_quiet/run_s1_quiet.sh` in the main checkout) is not part of the study and its log is evidence for this addendum only.
5. Three conditions are added that the human lead was not asked about in the quoted question: idle time, the spread bound, and the virtual-machine rule (§A9).

## A8. Requirements for the implementer

1. **The baseline command** (§A3.1), in new code beside `quiet.py`: a samples file written line by line, and a record with the attempts, the discarded windows and their reasons, the thirds' medians and P95s, P95, L, the application's presence, the VM markers present at every sample, the top processes, the OS build and boot time. Every wait has a deadline. The accepted record and its samples are copied into `results/` and committed before the candidate plan.
2. **`[quiet]`** gains: `baseline_provisional` (true until the figures are written), `load_p95`, `load_limit`, `load_margin = 0.5`, `load_ceiling = 3.0`, `percentile = 0.95`, `baseline_samples = 360`, `baseline_interval_seconds = 10`, `settle_samples = 60`, `settled_median_fall_max = 0.25`, `settled_p95_fall_max = 0.5`, `sample_gap_max_seconds = 15`, `hid_idle_min_seconds = 600`, `end_load_delay_seconds = 120`, `timing_spread_max = 0.05`, `app_markers`, `app_present`, `vm_markers`, `vm_present`, `baseline_record_sha256`. `load_average_max` is removed, not left at 1.0. `core.py`'s list of required keys and the config test that ties each value to its section follow this addendum.
3. **The candidate plan refuses while `baseline_provisional` is true. The freeze re-derives P95, L and the presence fields from the committed samples and refuses on any difference**, on an unsettled window, or on L above the ceiling.
4. **`quiet.py`:** the reading of §A3.2 and §A3.3; the end check with the delayed load; the reason for each failed reading recorded (which condition); each reading appended to the run directory as it is taken, not only when the session ends. Tests: nearest rank at 120 and 360; each settled test at its boundary; the ceiling at 3.00 and 3.01; a discarded window; application presence differing; a VM marker absent from the baseline; five-minute average above L with the one-minute below; the end load; no path writes NOT MEASURED.
5. **`measure_timing`:** keep `runs` and `wall_runs` per item; §A3.4's rule, its re-timing and its record; tests at s = 0.05 and just above, and of a second set that fails.
6. **A separate bounded wait for each quiet stage.** Timing and throughput each have their own session and deadline, and each launch script its own `timeout` above it. In the counting rehearsal a PAUSED quiet stage is retried by itself in the same directory without rerunning completed stages; the rehearsal is COMPLETE only when both have a quiet run.
7. **The counting rehearsal is rerun in full, in a new directory,** against the candidate plan written after the baseline. The incomplete one is kept.
8. **Seed gate: unaffected.** The baseline and the quiet rule read no seed and no data, and no allocation changes.
9. **Caps: the rule is unchanged** (charged hours + 2 × projected remaining). To be checked and reported to the lead before the candidate plan: the rehearsal's timing manifest charged 2,478 s over a span that included 40 minutes of waiting, so a quiet wait appears to be charged against `timing_hours` (1.0) while a session may wait 6 hours. Whether waiting is charged, and the effect of the 120 s end delay and of re-timing, are settled there; this addendum sets no cap figure.
10. Anything this text leaves to a guess is reported to the lead before code is written; where two readings are possible, the stricter one for the store applies.

## A9. Open choices for the human lead

1. **Idle time of 600 s at the window and at each stage start** (§A3.3). Recommended: keep. It means the stages run when he is away from the machine; the application may stay open.
2. **The Claude application open or closed.** Recommended: open and silent, as §A3.3. The baseline is taken in whichever he chooses and the stages must match it.
3. **The spread bound 0.05 with one re-timing per item** (§A3.4). Recommended: keep. The alternative, no bound, leaves MC-T protected by the start reading alone.

## A10. Review record

*(empty: no independent review has been performed on this text)*
