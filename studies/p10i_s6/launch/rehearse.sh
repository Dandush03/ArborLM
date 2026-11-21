#!/bin/sh
# P10IS6 rehearsal phase r1 | r2 | r3 (ADR-0031 section 16, requirement 1): the same stage driver and the same fresh worker processes as the registered stages; the plan is a REHEARSAL plan, never a registered one.
# Usage: rehearse.sh <r1|r2|r3> --run-dir <dir> --sealed-dir <dir outside every git working tree> [--data-manifest F --parent-dir D --parent-suite D ...]
# The keep-awake watcher (caffeinate, waiting on this very process) is part of the stage's own process family; this study registers no timing reading and has no quiet rule.
# No loop, no sleep, no wait: every wait inside has a deadline (the stage cap). Every expansion is quoted.
set -eu
if [ "$#" -lt 1 ]; then
    echo "usage: $0 <r1|r2|r3> --run-dir <dir> --sealed-dir <dir> ..." >&2
    exit 2
fi
cd "$(dirname "$0")/../../.."
if command -v caffeinate >/dev/null 2>&1; then
    caffeinate -i -w "$$" &
fi
exec uv run --locked python -m studies.p10i_s6.stages rehearse "$@"
