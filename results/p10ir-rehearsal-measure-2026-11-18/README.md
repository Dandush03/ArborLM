# P10-I-R — measuring rehearsal, 2026-11-18 UTC

**Not a registered result. Nothing here can be frozen on: the hour caps were provisional.** No sealed value was read (gate 3 was not run). `Astra review: NOT_PERFORMED`.

Run by the lead (Claude Fable 5.2) at commit `dd273b3` of branch `claude/p10-i-r`, on the platform of record (macOS arm64, torch 2.8.0), after the implementation audit and re-audit (`docs/reviews/p10ir-implementation-audit-2026-11-17/`). Command: `python -m studies.p10ir.stages rehearse --phases synthetic,real,gates12`. Wall time 03:00:57 to 03:24:31 UTC (23.6 minutes). Run directory `experiments/P10IR-rehearsal-measure-20261118` (not in git); `rehearsal.json` and the three ledgers are copied here.

| Check | Result |
|---|---|
| Synthetic phase: all eight stages end to end | COMPLETE |
| Real-size phase (one T-OQ and one F-OQ cell, 32,768 facts, 16,384 slots, rehearsal seeds 299201 / 330692, 64 updates): gates, A1, A2 training, A2 | COMPLETE; item errors 0; no task paused |
| Gate 1 (checkpoint and data identity) on the 280 registered checkpoints | passed, 280 of 280 |
| Gate 2 (the baseline reads reproduce P10-S1's recorded counts) on the same | passed |
| Adapter identity gate (bridge code against P10-S1's own training, tensors compared) | passed |
| Gate 3 (sealed recall values) | not run, by design |
| Peak resident memory per worker | A1 643 MiB, A2 711 MiB, A2 training 344 MiB (guard 3 GiB) |
| Charged seconds | synthetic 67.6; real 959.6; registered-checkpoint gates 294.3 |

Seconds per read at the largest cell (32,768 facts, 16,384 slots), one worker:

| Read | Seconds |
|---|---|
| T0 | 6.3 |
| T1, T1w | 4.2 each |
| T2, T3 (all candidates) | 58.3–58.8 each |
| Tv1 / Tv4 / Tv8, priors on or off | 3.3 / 6.3 / 10.4 each |
| F0 | 5.7 |
| I256@512 | 9.5–9.7 (23.5–24.0 in the A2 phase) |
| I64 at 128 to 2,048 keys, three seeds each | 9.7–11.8 each |

One tree checkpoint costs about 172 worker-seconds and one flat checkpoint about 173 at this size. As an upper bound, taking every one of the 280 checkpoints at the largest cell's cost and adding the measured per-task overhead, stage A1 is about 57,400 worker-seconds, or about 2.7 hours on six workers. This is a projection, not a measurement of A1.

Notes for the freeze: the top-level `platform` block of `rehearsal.json` describes the driver process (six threads, determinism off); the workers set one thread and deterministic algorithms, and the bit-exact gates passed. The record should carry the workers' settings. The candidate-plan phase was not part of this run.
