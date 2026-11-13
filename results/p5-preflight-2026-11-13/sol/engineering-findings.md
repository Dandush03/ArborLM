# P5 engineering preflight findings

No P5 experiment, corpus model forward, or registered timing worker was run during
implementation. Synthetic model calls and actual parent restore without a forward
are the only model checks before the separate root authorization.

The in-progress review identified a parent map key mismatch (`-control` versus
`-baseline`), an attempted router read for flat memory, and a duplicate exclusive
cell export. The runner now uses a single consistent parent label, captures router
state only for tree variants, and publishes each cell exactly once. The reviewer
also identified a stage-clock gap in packaging/supervision: quality is charged from
allocation through finalization and timing starts at that same measured transition.
Timing waits exclude only recorded external report/push intervals. The quality
failure path now publishes the combined terminal and leaves timing unexecuted.

Other preflight iterations corrected relative P3 provenance resolution, the stale
P4 config description and result date, float equality where fixed-router byte
identity was required, and operation probes for the actual ATen matmul dispatch.
A matmul/mm trace is accepted only for the expected operand shape, and the raw
operation name is retained. The synthetic schedule confirmed 2112 calls for a
quartet. Initial Ruff/mypy iterations reported typing/formatting errors, resolved
in subsequent isolated checks.

An intermediate combined synthetic check, while Luna's independent fixture file
was still under development, returned 8 failed, 13 passed: uneven-batch NLL and
permutation fixtures, the five per-variant runner fixtures (parent map identity),
and schedule fixture count (registered two workload sizes). The only warning
was the existing PyTorch missing-NumPy warning. Later checks report final status
separately; the intermediate failure is not evidence of a real P5 run.

The ACK operator writes exact JSON with suite_id, worker_id, commit (full
lowercase 40-character SHA) and push_completed=true after reporting and successful
push. The temporary file must be in the suite root outside report-acks; atomic
rename into the emitted ack_path is the publication boundary. In-flight,
out-of-order, and reused ACKs are rejected.

The preserved whole-suite check in regression-attempt-01.log captured the
intermediate independent-test Ruff findings and 147/148 tests passing. The sole
remaining test fixture expected a combined timeout at 2398 seconds; the fixture
was corrected to exercise an actual deadline crossing. The E0 regression
smoke in that attempt passed all 11 gates. The runner also now checks the
deadline after its charged ACK announcement, and checks the complete registered
measurement key/record matrix before accepting a timing worker.

Independent no-forward actual-parent/data check:
../p5-root-preflight/strict-restoration and ../p5-root-preflight/strict-restore.stdout.log.

The last root code review found that flattening parameter membership alone would
accept a split group and allow optimizer option drift. P5 now requires exact
AdamW type, a single group, the complete registered option set and value types,
and exact ordered parameter identity; training, save and restore call this
guard. This adds validation only and does not change the registered optimizer.

Luna identified a final ACK accounting edge case: a wrong worker ACK or invalid
JSON arriving after a delay was rejected, but the polling interval had already
been deducted. Both fake-clock regressions reproduced a 7-second incorrect
deduction. The interval is now eligible for exclusion only after exact ACK
validation; invalid or interrupted waits remain charged. The focused rerun
passed, including the established valid ACK and quality-stage deadline tests.
See delayed-invalid-ack-before.log and delayed-invalid-ack-after.log.
