# Root independent data and parent audit

Status: PASS. Reviewer: root Codex under the human-authorized scientific-reviewer exception. Astra review: NOT_PERFORMED. No P5 model forwards, evaluations or training occurred.

Command executed from repository root before any P5 data freeze:

```sh
uv run --locked --extra pilot python experiments/review/p5-root-data-audit.py > experiments/review/p5-root-preflight/data-audit.log 2> experiments/review/p5-root-preflight/data-audit-tooling.log
```

`audit.py` is an AST-identical formatted copy of the executed source (original retained in commit `1cf9fa6`); `audit.json`, `stdout.log` and `stderr.log` preserve its outputs. It imports no ArborLM module and independently reconstructs raw Parquet chunks, ranks, deduplication, full-training exclusion, four prior panels and the new 512-row panel. It also compares all nine actual P4 baseline tensors byte-for-byte against their P3 ancestors and verifies original/compact checkpoint records.

The prior-use check scans all locally available `dataset_manifest.json` files under `results` and `experiments`; the complete inventory is retained. This is a pre-freeze audit: running the identical script after creating P5 manifests intentionally fails its strict no-prior-P5-manifest assertion. Reproduction of that temporal check requires the recorded prior artifact inventory, without subsequently generated P5 manifests. It cannot rule out unknown external experiments or near-duplicate text.

New panel ranks: 2048..2559; SHA-256: `d50cbe4c303791148c922bfe9201fe00b192c44deef855077860ffc98cc72b98`. Zero exact overlap with four previous panels or the full training candidate pool. Raw corpus and binary checkpoints remain local.

This is one preflight component, not acceptance of the implementation or authorization to train. Luna's separate reconstruction, engineering tests and the final code/config/data/spec/lock freeze remain required.

The initial archival source triggered nine Ruff line-length errors. Formatting and adjacent string-literal wrapping resolved them; Python AST equality to the executed source was checked, preserving every operation and output. This was an evidence-source formatting defect, not a model experiment.

GitHub CI run [43425530897](https://github.com/Dandush03/ArborLM/actions/runs/43425530897) preserves the original nine line-length failures; the failed-step output is retained alongside this audit. The corrected audit passes `uv run --locked --extra pilot ruff check results/p5-preflight-2026-11-13/root-data-parent/audit.py`.
