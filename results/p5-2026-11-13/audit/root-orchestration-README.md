# P5 reporting and resource audit

From the repository root, with the original P5 local suite and its quality push
journal present:

```sh
python3 results/p5-2026-11-13/audit/root-orchestration-audit.py > /tmp/p5-orchestration.json
cmp /tmp/p5-orchestration.json results/p5-2026-11-13/audit/root-orchestration-result.json
```

The script uses only the standard library and read-only Git commands. Run
before editing the frozen source or tracked documentation: it checks all 95
frozen files against the worktree and launch commit. The 2,763-file historical
preservation check uses the acceptance record's finalized P4 reference and
source, config, test, result, ADR, packaging and lock paths. It checks both the
current Git tip and on-disk bytes. No model call, network request or Git
mutation is needed.

After the final report changes README/research-log text, repeat this historical
working-source check in an isolated checkout of
`1862a2a311b894e5539fa722ce127f98b66a7afd`, before those documentation changes.
Pass `--raw /absolute/path/to/the/original/P5HIER-suite` and
`--journal /absolute/path/to/p5-push-journal.json` to use the retained local
artifacts. The final documentation checkout intentionally differs from the
95-file execution freeze; that difference is not a numerical-source change.

The public [quality ledger](root-orchestration-ledger.json) contains just the
117 checkpoint IDs and their registered order and status. The preserved
[raw ACK files](root-orchestration-acks) contain the quality-stage and 36 timing
reporting acknowledgments. For every recorded checkpoint, the audit verifies
Git ancestry, that the commit changed only the corresponding bundle, and
that all committed bundle files agree with both the compact worktree copies
and local original bytes. The output includes manifest/result hashes for all
154 commits. ACKs attest to successful push as recorded by the operator; Git
ancestry and file bytes do not establish that any chat message was delivered.

The audit independently sums the 37 validated waits, reconstructs active and
combined time, checks worker/stage/suite limits and RSS, recounts the quality
matrix and timing calls, and confirms the suite completed. An initial
[tooling attempt](root-orchestration-attempt-01.stderr.log) failed because
`git diff-tree` required separate `-r` and `-z` switches; the corrected
attempt passed and the final replay added independent quality recounts.
