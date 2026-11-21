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

(to be completed)
