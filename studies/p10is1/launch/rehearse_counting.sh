#!/bin/sh
# The counting rehearsal (ADR-0024 sections 11, 18; the quiet-rule addendum A8 items 0, 6 and 7). It runs the registered driver's own stage functions, TWO OF THEM QUIET STAGES (timing, throughput) with the measured rule
# of the config. One command: the output goes to a file, the timeout (20 h) lies above the stages' own deadlines (a wait of at most 6 h for timing, a second of at most 6 h if a timing spread forces a re-timing, and one
# of at most 6 h for throughput, plus about 1.1 h of work), the keep-awake watcher is started by the command itself inside its own process family. The lead launches it, makes NO tool call and runs no other Claude session
# until it exits. Exit 0: every stage COMPLETE. Exit 1: not complete (a PAUSED quiet stage): run it again with RESUME=resume (the same directory; completed stages are not run again, the PAUSED one is retried by itself).
# Usage: <script> <run-dir> <plan> <record-out> <qualification> <output-file> [resume]
if [ "$6" = "resume" ]; then
  exec timeout 72000 uv run --locked python -m studies.p10is1.stages rehearse --counting --resume --run-dir "$1" --plan "$2" --record-out "$3" --qualification "$4" >> "$5" 2>&1
fi
exec timeout 72000 uv run --locked python -m studies.p10is1.stages rehearse --counting --run-dir "$1" --plan "$2" --record-out "$3" --qualification "$4" >> "$5" 2>&1
