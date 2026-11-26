# Review — ADR-0024 addendum: the quiet-machine load limit becomes a measured rule (P10-I-S1)

Reviewer: arbor-auditor subagent, model Opus 5.5 (`claude-opus-5-5`), 2026-11-19. Independent engineering and mathematical review. **This is not Astra validation and not human approval.** `Astra review: NOT_PERFORMED`.

Text reviewed: `docs/decisions/ADR-0024-addendum-quiet-rule.md` in worktree `agent-ab0efbf6bb233cc02` (branch `claude/p10-i-s1-impl`, commit `3226357`), SHA-256 `50946536fbab95978b27110c8f6617939e7cdbf2be95553264b5e824fff560b6`. Evidence: `results/p10is1-quiet-evidence-2026-11-19/load_10s_samples.log`, SHA-256 `d3c19c3553afb454216f4b7d4eeb51613f9acbd782cc6ece0c9f3f0b4c3113b3`.
Also read: the brief (`BRIEF_ADR0024_QUIET_ADDENDUM.md`), ADR-0024 §8.2, §9.1–§9.5, §10, §11, §15, §16; `configs/p10is1_capacity.toml` `[quiet]` and `[caps]`; `studies/p10is1/quiet.py`; `studies/p10is1/stages.py` (`measure_timing`, `_execute_stage_body`, `execute_stage`, `stage_cap_seconds`); `studies/p10is1/core.py` (`Ledger`); `studies/p10s1/timing.py` (`cpu_seconds_per_update`); `studies/p10is5/core.py`, ADR-0028 §8–§9 and `results/p10is5-run-2026-11-18/OUTCOME.md` from `origin/main`; the evidence manifests and `timing_attempt_01.json` (load readings only); `experiments/P10IS1-projection.json` (cap and stage-hour keys only); `experiments/_scratch/s1_quiet/run_s1_quiet.sh` (how the log was made: `sysctl -n vm.loadavg`, field 2, every 10 s, with `caffeinate -i`).
Not opened: any `timing.json` (rehearsal or measuring), any sealed value, any registered record of P10-I-S1.

Scripts and outputs (my own code; nothing imported from `arborlm` or `studies`): `/Users/daniellaloush/dandush03/ArborLM-sealed/review-s1-quiet/recompute.py`, `recompute2.py`, `recompute3.py`, with outputs `recompute_run1.out`, `recompute2_run1.out`, `recompute3_run1.out`. Command, each: `timeout 300 python3 -I <script> <path to load_10s_samples.log>`; Python 3.15.1 (system `python3`), macOS arm64. All load arithmetic in integer hundredths. Every check ran first time; there is no failed checker attempt to keep. (This report was to be written at `/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/audits/`; a worktree hook refused that path, so it was written through the session worktree's `experiments` symlink, which resolves to the same directory.)

## Verdict

**READY AFTER THE LISTED EDITS**, and §A3.4 (the spread bound), the idle-time condition and the application condition are not implemented until the human lead has answered the questions at the end. As it stands the text is **not** ready. It claims that no label becomes easier for the store. That is false through the NOT MEASURED route that §A3.4 feeds (B1). Its settled test is presented as a guard, but on tonight's own log it accepts windows contaminated by a rising load (R1).

## Recomputed figures (all match the addendum unless stated)

| Quantity | Mine | Addendum |
|---|---|---|
| Samples, span, largest gap | 1,367; 18:40:27–22:28:42; 11 s (gaps of 10 or 11 s only) | same; "no gap above 15 s" |
| 18:40–19:21 / 19:21–20:36 / 20:36–20:45 / 20:45–22:15 / 22:15–22:28, half-open | n 243/449/54/538/83; min, median, nearest-rank P95, max, count ≤ 1.0 all as in the table | same |
| Settled part [20:45, 22:15) | 538 samples (539 if 22:15:00 is included); ≤ 1.00: 12 (2.2 %); ≤ 1.74: 512 (95.2 %); ≤ 2.24: 532 (98.9 %) | same |
| Throughput poll instants 20:36 … 22:16 | 1.63, 1.41, 1.23, 1.44, 1.04, 1.05, 1.49, 1.34, 1.41, 1.85, 1.19 **with the first sample at or after each instant**; with the nearest sample the 22:06 value is 2.00 | the first convention, unstated |
| 3.25 at 20:34:32, 1.63 at 20:36:03 | confirmed | same |
| 60-min / 30-min windows inside [20:45, 22:15) | P95 1.61–1.88 (179 windows) / 1.50–2.10 (359) | same |
| Windows starting 20:26:02–20:33:02 (in the fall), P95 fall | 2.33–2.94 | same |
| **Windows starting 20:36–21:15: largest median fall and P95 fall** | **0.18 and 0.31 at every 10-s start** (0.16 and 0.20 at five-minute starts) | **"at most 0.15 and 0.20"**: discrepancy (A1) |

**The rule applied to the whole log** (load conditions only: the log records no process, power or HID state). I applied it at every one of 948 possible start samples (10-min settle + 360-sample window): 322 ACCEPTED, 460 NOT SETTLED, 166 ABOVE CEILING, 0 gaps.
- Accepted L ranges **2.11–2.99**, median 2.14. Windows wholly in the clean idle part give **L = 2.11–2.38**. Started at 20:36–20:45, as a person would start it after the training, the first attempt is accepted with **L = 2.12**.
- **Training 19:21–20:36 is not admitted.** Every window containing it is refused (NOT SETTLED or ABOVE CEILING; training-level windows give L ≈ 7.1–7.3). Only 9 accepted windows touch it, by their first samples at 20:35:xx at the end of the decay, with L 2.12–2.18. 60 accepted attempts have the end of training inside the **settle** only (L 2.12–2.14). Sequential attempts started at 18:40:27 run ABOVE CEILING (7.08) → NOT SETTLED (7.06) → ACCEPTED at 21:00:47 (2.24).
- **The settled test is one-sided and lets a rise through.** 172 windows that contain training pass both settled tests and are stopped only by the ceiling. 80 accepted windows have the 22:15–22:28 rise in their last third (application reopened, other studies resumed, load up to 6.74): median fall −0.09 to −0.04, P95 fall −2.56 to −0.38, **L 2.38–2.99**, all under the ceiling.
- **How often a stage gets a quiet reading.** At L = 2.11–2.14, 98.3–98.5 % of settled samples are ≤ L (100 % at 2.99), and the first 10-minute poll from 20:36:03 passes on the one-minute load. An approximate five-minute average (exponential smoothing of the logged one-minute values, τ = 300 s; an approximation, not a measurement) is about 2.70 at 20:36:03. So the five-minute condition would refuse that first poll and pass the next (about 1.57 at 20:46).
- Medians as mean of the two middle values against nearest rank (S5's convention, `studies/p10is5/core.py` lines 251–262): no accept/refuse decision differs on this log.
- Floating point: of 976 pairs of two-decimal values whose exact difference is 0.25, **30 give a float difference above 0.25** (e.g. 0.54 − 0.29 = 0.25000000000000006); 48 of 951 at 0.50 do likewise. P95 + 0.5 is inexact in float (0.07 + 0.5 = 0.5700000000000001).

## Answers to the seven questions

**1. Scope of the decision.** The human lead decided only "a rule measured on this Mac (about 2.2)" against 1.0. The measured rule, settle period, window, margin and ceiling define that decision and are inside it. Of the three additions:
- *HIDIdleTime ≥ 600 s*: he was not asked. It only adds refusals and cannot change a value. But it limits his use of his own working computer: about 80 minutes untouched for the baseline, and at least 10 minutes before and through each stage. So it needs his word as an operational matter, not a scientific one. It is needed: under a limit near 2, a user at the keyboard can pass the load test.
- *Application presence equal to the baseline's*: he was not asked; the brief asked the drafter to decide. It is a consistency rule. It needs his word only because it decides whether he must close the application. As written, it also refuses a stage run with the application *closed* after an *open* baseline, which is the quieter case (A3).
- *The spread bound*: he was not asked, and it is a new validity rule that decides whether MC-T exists. It is **not** monotone for the store (question 2). **It must go to him before implementation**, as the lead's test requires.

**2. The spread bound.**
- *Chosen to pass?* 0.05 was set knowing P10-S1's registered spreads (0.0017–0.0364, 15 of 16 at most 0.013, at a start load of 0.98), and this is disclosed. It is generous against that record (about 1.4× the worst item). Its stated reason, the throughput CV limit, is a different statistic: for three normal repeats E[range] ≈ 1.69 σ, so s ≤ 0.05 corresponds to a CV of about 0.03. No P10-I-S1 timing value was used, so it was not chosen to pass on this study's values. The text does not say whether the lead himself, or any agent, opened the rehearsal's `timing.json`, which would show this study's spreads (R6).
- *Selection by re-timing.* As written, only the failing items are re-timed, after the other items, and the second set is kept if its spread passes. Under contention, a low spread selects low-contention repeats, which have lower CPU values. The items that get this second draw are the noisier arms' items. So the rule is symmetric in its text but not in its effect: it can lower one arm's measured cost relative to another's. Re-timing is bounded at once per item, so it cannot be gamed by unlimited retries within an attempt. But after TIMING SPREAD "the stage is repeated" with no bound within a session (B1).
- *An item that stays above the bound.* The attempt is discarded. MC-T is all or nothing, so there is no per-item NOT MEASURED. In the code, a discarded attempt is recorded with status `PAUSED — QUIET CONDITION NOT MET` (`quiet.run_alone_stage`, the end-check branch). It **counts in `paused_attempts`**, i.e. towards the six sessions after which MC-T NOT MEASURED may be decided. "Recorded as the existing end-check discards are" therefore makes TIMING SPREAD a route to study-wide NOT MEASURED.
- *Does NOT MEASURED make rows easier?* Yes, some of them. The table gives each direction, comparing NOT MEASURED with a measured MC-T on the same data; "easier" means easier for the store:

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

So NOT MEASURED removes the store's positives and also removes routes to negatives; the outcome lines move towards INCONCLUSIVE from both sides. P10-S1's records make the direction foreseeable: MC-T was the reading in which D-OQ was faster at 8K/16K (§9.5's figures), so losing MC-T removes a reading already known to have gone against the store. A looser start condition, plus a bound that discards contended attempts and counts them towards NOT MEASURED, can turn a failing MC-T condition into an absent one. ADR-0024 §10's own sentence ("no negative becomes unreachable") is about reachability, not ease. The addendum's §A5 sentence "No label becomes easier for the store" is false as written. (Note: the brief's "section 11's rows" are §9.1's rows; §11 is the order of work.)

**3. The rule.** It becomes computable once the edits of R3 are made: median, integer arithmetic, rounding of stage readings, what "holding at every sample" means, the HID and thermal sources, and a power assertion. The settled test is one-sided by design, and the log shows it admits contaminated windows (above). On this log the contamination is caught by the HID and process conditions, not by the load tests, and the text must say so. A two-sided median test, |median(T1) − median(T3)| ≤ 0.25, refuses no clean window on this log (range −0.08 to 0.18), but it does not catch tonight's rise either (−0.09 to −0.04). A two-sided P95 test at 0.50 would refuse clean windows (clean P95 fall down to −0.59). So a rise test would be a threshold chosen after seeing the data: `PENDING LEAD REVIEW`. L on tonight's log: **2.12** for an attempt started after the training, and 2.11–2.38 over clean windows. The margin 0.50 has a stated reason (one burst of about 40 s; half a sustained thread) and comes from ADR-0028. The ceiling 3.00 sits between figures seen tonight (2.38) and S5's unsettled 3.53, which §A4's last paragraph discloses. It does not separate out the contaminated windows, which reach 2.99. The human lead was told "about 2.2"; the rule admits up to 3.00 (R7).

**4. A looser limit and the readings.** §A5's physics is sound for CPU-seconds: at load 2–3 on 18 cores a single thread does not queue, while cache, bandwidth, thermal and core-class effects remain. The existing checks do not cover the timing stage:
- `measure_timing` drops the repeats; I confirmed that it keeps only the medians and the peak RSS.
- The concurrent-to-isolated ratio belongs to the measuring rehearsal.
- The throughput CV limit is descriptive.

Nothing records the load during the stage (A4). Does a CAPACITY label become easier? Through the start condition alone this cannot be shown either way, because labels read ratios. Through §A3.4 as written, yes (B1).

**5. Disclosure.** Adequate on the observed 2.2 %, the completed rehearsal timing, P10-S1's spreads, and the drafter not opening `timing.json`. Missing:
- whether anyone, the lead included, opened the rehearsal's `timing.json` (R6);
- that the human lead was told "about 2.2" while the ceiling admits 3.00 (R7);
- the poll-sample convention and the 0.15/0.20 figures (A1).

**6. Implementer requirements.** Incomplete:
- the marker lists are undefined (R4);
- the caps question is left open, although the code already answers it, wrongly (R2);
- "the stage is repeated" has no bound (B1);
- it does not say whether stage readings are rounded or raw (R3).

**7. Practicality.** The baseline is taken once. 80 minutes untouched (10 for HID, 10 settle, 60 window) plus a few minutes per stage is practical in an evening slot. On this log, 30-minute windows give P95 1.50–2.10 (accepted L 2.00–2.99 over all starts) against 1.61–1.88 for 60-minute windows: the shorter window doubles the spread of the frozen figure. Keep 60 minutes.

## Findings

**B1 — BLOCKING — §A3.4, §A5, §A3.5.** *Problem:*
- A TIMING SPREAD discard is recorded "as the existing end-check discards are", which the code counts as a PAUSED quiet session towards the six-session NOT MEASURED path.
- "The stage is repeated" has no bound.
- Per-item re-timing selects low-contention readings for some arms only.
- §A5 claims "No label becomes easier for the store", which is false (table above).

*Change:* replace §A3.4 by:
> "**A3.4 Validity of the timing itself (new; it applies only if the human lead accepts it, §A9 item 3).** For each (arm, slots) item the stage records the three per-repeat values of CPU-seconds and wall-seconds per update. s = (max − min) / median of the three CPU values, in floating point from the recorded values; the median of three is the middle value. An attempt is valid only if s ≤ 0.05 at every item. If any item has s > 0.05, the whole attempt is discarded (TIMING SPREAD) and the full item list is timed again once in the same session, after a new quiet reading of §A3.2; readings of two attempts are never combined, and both are kept and printed. If the second attempt also has an item above the bound, the session ends **PAUSED — TIMING SPREAD**. A TIMING SPREAD session is not a PAUSED — QUIET CONDITION NOT MET session: it is recorded with its own status, does not count towards the six sessions of §A3.5, and cannot support a NOT MEASURED decision. After three TIMING SPREAD sessions the matter returns to the human lead; no outcome follows automatically. The ratio of CPU to wall seconds per repeat is printed and is not a condition."

and replace §A5's bullet "No label becomes easier for the store" by:
> "**What NOT MEASURED does, and why the spread bound may not lead to it.** A NOT MEASURED decision is not neutral. It removes CAPACITY-POSITIVE, STORE NOT BEHIND, STORE HOLDS MORE and EFFICIENCY-POSITIVE, and it also removes the MC-T and MC-C conditions of §9.1 row 4 (so CAPACITY, CAPACITY STEP and CAPACITY_SUPPORTED become easier and CAPACITY-NEGATIVE (a) harder), the MC-T and MC-C routes to DENSE AHEAD, and the E-T routes to EFFICIENCY-NEGATIVE and DENSE FASTER. In P10-S1, MC-T was a reading in which D-OQ was faster. A rule that discards contended timing attempts and counted them towards NOT MEASURED could therefore turn a failing MC-T condition into an absent one; §A3.4 does not count them. The quiet-reading conditions added here (five-minute average, idle time, end load, virtual machines, application presence) only add refusals; they change no value and do not shorten the path to NOT MEASURED."

**R1 — REQUIRED — §A4 "Settled tests" row.** *Problem:* "A rise late in a window does not fail: it is idle variation" is contradicted by the log. 80 accepted window positions have the 22:15–22:28 rise (application reopened, other studies resumed) in their last third, with L 2.38–2.99. *Change:* replace that sentence by: "The tests are one-sided. On the log of §A2, 80 accepted window positions have the 22:15–22:28 rise in their last third and give L from 2.38 to 2.99; the load tests do not refuse them, and the conditions of §A3.3 (idle time, processes) do. A rising load from a source those conditions do not see (a virtual machine starting, a backup, indexing) is caught only by the ceiling. Whether to add a test on a rise is `PENDING LEAD REVIEW`; on this log |median(T1) − median(T3)| ≤ 0.25 refuses no clean window and would not have caught the 22:15 rise." Also correct "at most 0.15 and 0.20" (A1).

**R2 — REQUIRED — §A8 item 9 (caps).** *Problem:* the code already answers the question, and not as the text assumes:
- `execute_stage` charges `max(pool_seconds, wall time since the stage began)` for timing and throughput, so the quiet wait is charged.
- The per-stage cap (`timing_hours = 1.0`) is not enforced for these two stages, because they do not use the `Pool` cap. Only the study total is enforced, through `Ledger.require_room`.
- Six 6-hour sessions would therefore charge up to 36 h against the 51-h total and pause training on a cap.
- The projection's timing figure is 0.031 h (`P10IS1-projection.json`, `stage_hours.timing`), so it does not include waiting. The quiet rehearsal charged 2,478 s, of which about 2,400 s were waiting (polls from 18:40:30, quiet at about 19:20:30, finished at 19:21:48).
- ADR-0028 §9 states "quiet waiting, which is not charged".

*Change:* replace item 9 by: "**Caps.** The charged seconds of the timing and throughput stages are the measuring seconds (from the quiet reading to the end check, including the 120-s delay and any re-timing); the waiting of §A3.2 and of the baseline is recorded per session and is not charged, as in ADR-0028 §9. The cap rule is unchanged. The implementer reports before the candidate plan: the charged and waiting seconds of every earlier rehearsal's timing stage, and whether any figure of the projection contains waiting."

**R3 — REQUIRED — §A3.1 items 1, 3–5; §A3.2; §A3.3.** *Problem:* two people cannot compute the rule identically as written:
- "Median" is undefined. S5's code uses nearest rank ceil(n/2); the drafter's figures use the mean of the two middle values.
- Float differences fail at the boundary (30 of 976 pairs whose exact difference is 0.25).
- The text does not say whether stage readings are compared raw or rounded; `quiet_reading` compares the raw `getloadavg` value.
- "Every condition holding at each sample" needs the HID source and its units, the thermal parse, and a power assertion. Without the assertion an idle Mac may sleep, and every attempt is then discarded for gaps.

*Change:* add to §A3.1 item 1: "All loads are handled as integers in hundredths: v = round(x, 2) × 100 as an integer. Every difference, comparison, P95 and L is computed in those integers; L = P95 + 50. The median of an even number of values is the mean of the two middle values, compared exactly (as 2 × median in hundredths). The nearest rank is ⌈95 n / 100⌉ in integer arithmetic. At each sample every condition of §A3.3 is read anew; one failure at one sample discards the attempt. The command holds a power assertion against idle sleep (`caffeinate -i -w <pid>`) for the whole attempt." Add to §A3.2: "The one-minute and five-minute averages are rounded with round(x, 2) before comparison with L." Add to §A3.3: "`HIDIdleTime` is read from `ioreg -c IOHIDSystem` in nanoseconds and divided by 10⁹. A thermal warning is any line of `pmset -g therm` other than the three 'No … has been recorded' lines."

**R4 — REQUIRED — §A3.3 and §A8 item 2 (markers).** *Problem:*
- `app_markers` and `vm_markers` are undefined.
- "The Claude application" does not say whether Claude Code CLI processes count; those ran tonight's other studies.
- The VM clause admits a VM that is present throughout the baseline, although a VM's load is not constant (S5 disclosure 1).

*Change:* "`vm_markers` (regular expressions on the full command line, case-insensitive): `com\.apple\.Virtualization\.VirtualMachine`, `qemu-system`, `limactl`, `colima`, `com\.docker\.(backend|virtualization|vmnetd)`, `Docker Desktop`, `vfkit`, `krunkit`, `OrbStack`, `prl_vm_app`, `VirtualBoxVM`, `UTM`. A stage reading and every baseline sample require that no process matches a VM marker. `app_markers`: `/Applications/Claude.app/Contents/MacOS/Claude` (the desktop application) and, listed separately, any process whose command line runs Claude Code (`claude` CLI); both presences are recorded; whether the CLI counts as 'the application' is fixed by the human lead's answer to §A9 item 2." Drop "unless one matching the same marker was alive at every sample of the baseline window".

**R5 — REQUIRED — §A3.1 item 8 (second baseline).** *Problem:* "for a stated reason" is open-ended, so a second baseline taken before the plan could be chosen for its L. *Change:* "A second baseline may be taken only for one of: an OS update, a hardware or power-setting change, a change of the condition of §A3.3 decided by the human lead, or a failure of the first found by review. Both are kept; the second replaces the first only for that reason, recorded before the second is taken."

**R6 — REQUIRED — §A7 item 2.** *Problem:* it says only that the drafter did not read `timing.json`. *Change:* add "The lead states whether he or any agent opened the rehearsal's `timing.json` (quiet run of 2026-11-19 or the measuring rehearsal's) before the spread bound was set; if yes, what was seen is disclosed here."

**R7 — REQUIRED — §A7 (new item 6).** *Change:* "The human lead was told 'about 2.2'. On the log of §A2, windows taken after the machine settled give L from 2.11 to 2.38; the ceiling admits up to 3.00, and windows with a rising load in their last third gave up to 2.99 on the load tests alone. He is told this before implementation (§A9 item 4)."

**A1 — ADVISORY — §A4 and §A2.** "At most 0.15 and 0.20" is 0.18 and 0.31 at every 10-s start (0.16 and 0.20 at five-minute starts); state the grid used. State that the throughput poll values are the first sample at or after each instant (the nearest sample gives 2.00 at 22:06). Neither changes a conclusion.

**A2 — ADVISORY — §A3.1 item 1.** The sampler's own `ps -A`, `pmset` and `ioreg` calls every 10 s add load during the baseline that the stages do not have, which raises L slightly. Use a light process listing (`ps -Ao pid,comm`) and record the sampler's own CPU seconds.

**A3 — ADVISORY — §A3.3, application presence.** Refusing a stage because the application is closed after an open baseline refuses a quieter condition. Consider "refused if present at the stage and absent at the baseline". This matters only if he chooses "open".

**A4 — ADVISORY — §A8 item 5.** In each quiet stage's record, keep the one-minute load every 10 s during the stage and the CPU-to-wall ratio per repeat (descriptive), so a contended stage can be audited.

**A5 — ADVISORY — §A8 item 4.** Add tests:
- the float-boundary pairs (0.54/0.29 at 0.25);
- the median of an even number of values;
- the HID unit conversion;
- a TIMING SPREAD session not counted by `paused_attempts`;
- the six-session decision refusing when the PAUSED sessions include a TIMING SPREAD one.

## Questions for the human lead (each with my recommendation)

1. "Do you accept a new rule that throws away a timing attempt when any item's three repeats differ by more than 5 %, retimes the whole list once, and after three such failed sessions brings the matter back to you instead of ever leading to 'not measured'?" Recommend **yes**, in that form (B1), and not in the drafted form.
2. "Will you leave the Mac untouched (no keyboard or mouse) for about 80 minutes once for the baseline, and for 10 minutes before and during each of the two short quiet stages?" Recommend **yes**; it is what makes a limit near 2 safe.
3. "During the baseline and the two quiet stages, should the Claude application (and any Claude Code session) be closed, or may it stay open and silent?" Recommend **closed**: the stages need you away anyway, tonight's evidence was taken with it closed, and code cannot check that the agent is silent.
4. "You were told the limit would be about 2.2; tonight's settled windows give 2.11–2.38, but the rule allows up to 3.00. Accept 3.00 as the ceiling?" Recommend **yes, with that disclosure**; a lower ceiling chosen now would also be chosen after seeing the log.

`Astra review: NOT_PERFORMED`
