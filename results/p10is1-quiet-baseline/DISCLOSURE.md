# P10-I-S1 quiet baseline: machine-sharing disclosure

Written by the lead (Claude Fable 5.2) before the launch of the first baseline session on 2026-11-20 (night, local time), and completed after it. The baseline's own record is never edited; this file states what the record cannot show.

## Before the launch

- **Another project shares this Mac.** A second Claude session of the same user (ArborML Lab, a separate private repository) works on this machine. It was asked by message on 2026-11-20 to stop every agent, tool call and background job for the window, and to confirm before the launch. The baseline is launched only after its confirmation. Its commitments are a peer session's word, not an enforced control.
- **What the baseline's code sees of it:** tool calls and `claude` processes of every Claude session of this user; a `claude` process starting or stopping, or a tool call, discards the attempt.
- **What it does not see:** that project's CPU use outside tool calls, and anything it left running in the background that is not a study process. The load condition is the only guard against those.
- **The lead's own sessions:** every background task, subagent and monitor of the ArborLM lead session is finished or stopped before the launch; the lead makes no tool call from the launch until the exit notification.
- **The human lead** is away from the machine (asleep) and has left it on mains power with his applications open (Slack, Safari, Chrome, WhatsApp, tech-admin, Finder, Claude). Condition registered in the addendum: application open, lead silent.
- Docker (Colima) is stopped.

## After the session (completed by the lead)

Session 1 was launched at 23:11 local time on 2026-11-20 (04:11 UTC on 2026-11-21) and exited with code 0 at 00:55 local time (05:55 UTC): **ACCEPTED**, no paused session. Figures re-derived by `baseline verify`: `load_p95` 167, `load_limit` 217 (hundredths; below the 250 that is reported to the human lead and below the ceiling of 300), condition `open`, application present, Claude Code present. Record SHA-256 `62c031ecf29f9634cc3e7e8b170c17e68a7298a7ade1a50a7c8f828f4ba347bd`, samples SHA-256 `73da7c385d36f5ad19a000f3595255598d6a68d1cde7cba11100238c4663e4b5`; both are copied unchanged to `results/p10is1-quiet-baseline-20261121/`.

- **Attempt 1 was discarded** (04:11:00 to 04:45:05 UTC, 202 samples, reason `CLAUDE PROCESS SET CHANGED`): a `claude` process started or stopped 34 minutes into the window. It is kept in the record and in the samples file. The lead made no tool call in that time. The cause was not observed; the likeliest one is the ArborML Lab session ending, because after the baseline that session was no longer reachable by message and no `claude` process younger than 2026-11-17 was alive. This is an inference, not a measurement.
- **Attempt 2 was accepted** (04:45:16 to 05:55:57 UTC, 420 samples). Settling checks (first against last third of the window, hundredths of load): medians 119 and 139.5, difference 20.5 against a two-sided limit of 25 (the record stores twice the median: 238, 279, -41); 95th percentiles 151 and 179, difference 28 against a limit of 50. Both pass. The load rose slightly through the window; it stayed inside the registered tolerance.
- **The ArborML Lab session** confirmed "Lab quiet" at 23:11 local time before the launch. Its end message could not be delivered (the session was gone), so its statement of what it ran during the window, if anything, was **not obtained**. The top-ten process lists at the start and end of each attempt (in the record) show no build or Lab job; they do show Orca (a desktop application of the user's) at 3.0 % CPU at the end of attempt 2 and two long-lived `claude` command-line sessions near idle.
- **The lead** made no tool call and ran no subagent between the launch and the exit notification.
- **The record's code commit** is `260762b`, one documentation-only commit (this file) after the audited commit `8038f44`; no file under `studies/p10is1/` or `configs/` differs between them.
- The human lead was asleep; the machine was on mains power.

`Astra review: NOT_PERFORMED`
