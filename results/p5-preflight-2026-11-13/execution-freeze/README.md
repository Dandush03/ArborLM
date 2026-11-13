# P5 execution freeze

Frozen before every real-data P5 model forward, training update, scientific evaluation and registered timing worker. Source commit: `9028507844c500bc4d296202e7c6c6e4ae552ecc`; clean source archive SHA-256: `6be82b23ae0c453c30c588a2ded4c3df0300ac7c20e0d7ff929bd02fc2a7d56e`.

`freeze.json` records the exact configuration/specification/lock/data identities, all nine parents, execution order, counts and resource ceilings. `source.json` retains the complete archived source-file hash map. The source archive, corpus and binary checkpoints remain local. Results-only commits may change Git HEAD and dirty status during execution; every captured numerical/source identity must remain identical to this freeze.

Engineering preflight was independently accepted after 161 passing full-suite tests, Ruff, mypy47, E0's11 gates, Luna's separate review and root's data/parent/arithmetic audits. Human approval of ADR-0010 and the 2,400-second ceiling is recorded in ADR section13; the authorized reviewer's acceptance is section14. Astra review: **NOT_PERFORMED**. Merging, publication and further scaling still require human approval.

Exact command used from the clean source commit:

```sh
uv run --locked --extra pilot python experiments/review/p5-root-preflight/freeze.py
```

`freeze-script.txt` preserves the exact executed Python source. It intentionally requires the recorded clean source commit and unused output directories. The freeze does not itself execute a model. Only the registered invocation may follow explicit orchestration authorization; no source/config/test/threshold changes or unregistered retries are permitted.
