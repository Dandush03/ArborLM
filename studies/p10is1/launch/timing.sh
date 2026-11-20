#!/bin/sh
# Registered stage timing (ADR-0024; the quiet-rule addendum A3.2, A3.4, A8 item 0). Refuses unless frozen and decided. QUIET STAGE: one command, the output goes to a file, the timeout (13 h) lies above the stage's own
# deadlines (a wait of at most 6 h, and a second wait of at most 6 h if a timing spread forces a re-timing, plus the measuring), the keep-awake watcher is started by the stage inside its own process family. The lead
# launches it, makes NO tool call and runs no other Claude session until it exits; its exit code is the report (0 COMPLETE, 3 PAUSED, 2 or 75 refused).
# Usage: <script> <run-dir> <freeze-commit> <output-file>
exec timeout 46800 uv run --locked python -m studies.p10is1.stages registered timing --run-dir "$1" --freeze-commit "$2" >> "$3" 2>&1
