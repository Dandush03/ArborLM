# P4 data and parent preflight

This record covers only the registered data panel and P3 parent artifacts. It contains no P4 model outcomes. Engineering preflight remains pending; no P4 model evaluation or training has occurred. Astra review has not been performed.

Reproduce with the local pinned Parquet files and registered P3 binary parents present:

```sh
uv run --locked --extra pilot python results/p4-preflight-2026-11-12/independent-data-parent-audit.py
```

The command exits 0. Its stdout is byte-identical to `root-data-parent-audit.json`, `independent-data-parent-audit.json`, and the preserved `root-data-parent-audit.log`.
