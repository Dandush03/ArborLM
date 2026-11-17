#!/bin/sh
# recheck r7: log who reads the real process list during the test suite, then behave as ps
echo "${PYTEST_CURRENT_TEST:-no-test} :: $*" >> /private/tmp/claude-501/-Users-daniellaloush-dandush03-ArborLM--claude-worktrees-arborlm-consolidation-experiment-2b31c1/cfc0efd5-b7ca-4602-959a-07fe6b8d4e7d/scratchpad/s1recheck-report/r7_ps_calls.log
exec /bin/ps "$@"
