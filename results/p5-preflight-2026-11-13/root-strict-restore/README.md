# Root strict restoration preflight

PASS: all nine actual P4 baseline snapshots strictly restored through the new P5 interfaces and their upstream P3 snapshots; frozen parameter counts, gradients and backbone digests match. Zero model forwards, training updates or scientific evaluations.

The implementation froze and reloaded the registered dataset; all first 2,560 selected validation identities match Luna's independent raw-Parquet reconstruction. The derived dataset manifest SHA-256 is `481dba62b283fc7b732bcf3692f38f37c2891b9d2200f9e1fc304c0f5721e848`. No corpus bytes or binary weights are included here.

Executed command:

```sh
uv run --locked --extra pilot python experiments/review/p5-root-preflight/strict-restore.py > experiments/review/p5-root-preflight/strict-restore.stdout.log 2> experiments/review/p5-root-preflight/strict-restore.stderr.log
```

`audit.py` is an AST-equivalent formatted copy of the executed checker. It creates an exclusive scratch directory, so reproduction needs that output path to be unused. The source identity at this provisional check is preserved, but it is explicitly **not the final P5 source freeze**. Complete independent synthetic engineering tests and the final recorded freeze are still required before training. Reviewer: root Codex under human authorization; Astra review: NOT_PERFORMED.
