#!/bin/sh
# Registered stage throughput (ADR-0024; the quiet-rule addendum A3.2, A8 item 0). Refuses unless frozen and decided. QUIET STAGE: one command, the output goes to a file, the timeout (6.5 h) lies above the stage's own
# deadline (one wait of at most 6 h, plus the measuring), the keep-awake watcher is started by the stage inside its own process family. The lead launches it, makes NO tool call and runs no other Claude session until it
# exits; its exit code is the report (0 COMPLETE, 3 PAUSED, 2 or 75 refused).
# Usage: <script> <run-dir> <freeze-commit> <output-file>
exec timeout 23400 uv run --locked python -m studies.p10is1.stages registered throughput --run-dir "$1" --freeze-commit "$2" >> "$3" 2>&1
