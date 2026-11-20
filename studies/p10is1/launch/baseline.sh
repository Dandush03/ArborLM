#!/bin/sh
# The quiet baseline (ADR-0024 addendum A3.1, A8 items 0 and 1): ONE SESSION, at most 6 hours. One command: the timeout (6.5 h) lies above the session's own deadline, the output goes to a file, and the keep-awake
# watcher (`caffeinate -i -w <pid>`) is started by the command itself, inside its own process family. The lead launches it, makes NO tool call and runs no other Claude session until it exits; its exit code is the report
# (0 accepted, 3 PAUSED — NO QUIET BASELINE: run the same command again, 2 refused).
# Usage: <script> <out-dir> <output-file>
exec timeout 23400 uv run --locked python -m studies.p10is1.baseline run --out-dir "$1" >> "$2" 2>&1
