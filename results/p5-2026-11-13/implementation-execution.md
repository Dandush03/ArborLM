# P5 execution record

Sol executed the registered command once on **2026-11-13** (America/Panama),
after the human-authorized reviewer accepted preflight and approved execution.
The quality worker was created at 12:52:06 UTC and finished at 13:13:27 UTC;
the full suite exited successfully shortly after 13:30 UTC. There were no
failed, interrupted, or unexecuted cells or timing workers and no rerun.
Astra review was not performed. This record documents execution; scientific
interpretation and independent artifact audits are separate.

```sh
uv run --locked --extra pilot python -m arborlm.hierarchy_ablation --data-dir data/wikitext2 --output-root experiments --results-root results/p5-2026-11-13
```

The launch verified a clean HEAD at
`6b3e25726d709ab0efe05777ab8205bea5b59464`, all 95 frozen source-file hashes,
the resolved configuration, ADR, and dependency lock. The deterministic
source archive matched SHA-256
`6be82b23ae0c453c30c588a2ded4c3df0300ac7c20e0d7ff929bd02fc2a7d56e`.
See the [execution freeze](../p5-preflight-2026-11-13/execution-freeze/freeze.json).
No source, tests, config, spec, or lock changes were made during execution.
Result-only Git commits tracked each completed quality cell and timing worker.

- **Quality:** 117/117 completed, including 108 trained additions and nine
  frozen baselines; 55,296 updates; 28,311,552 training targets; 333 snapshots;
  612 scientific evaluations and nine old-panel integrity evaluations.
  See the [quality result](quality-suite/result.json).
- **Timing:** 36/36 completed, including 27 quartets and nine baseline workers;
  58,752 scope calls including warmups. See the [suite result](suite/result.json).
  There was no model training or scientific evaluation in timing workers.

| Resource | Observed | Registered ceiling |
| --- | ---: | ---: |
| Quality stage wall time | 1,281.554948875 s | 1,800 s |
| Timing stage active time | 214.904311167 s | 600 s |
| Combined active time | 1,496.459260042 s | 2,400 s |
| Peak sampled suite process-tree RSS | 858,423,296 bytes | 2 GiB |

The timing stage took 1,037.595215416 seconds elapsed. The runner deducted
822.690904249 seconds of recorded external reporting and push waits across
37 validated acknowledgments: one before timing and one after each worker.
No timing worker was live during an acknowledgment wait. The quality
supervised worker took 1,281.550607083 seconds and reached 679,329,792 bytes
peak sampled process-tree RSS. The largest timing worker peak was 349,224,960
bytes. The [suite terminal](suite/terminal.json) records completed status and
no RSS breach.

The local run is
`experiments/P5HIER-20261113T125206040109Z-8a40c493791641028f8eb8dfa26f71be`.
Unfiltered launcher output is retained locally in
`experiments/review/p5-execution.stdout.log` and
`experiments/review/p5-execution.stderr.log`; stderr records the known
optional NumPy initialization warning. Original checkpoint binaries and
optimizer states, source archives, corpus and frozen dataset bytes remain
local. The compact results contain evidence and checkpoint indexes.
