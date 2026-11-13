# RAM pilot preflight — before training

Authorized root reviewer accepted the implementation for the bounded ADR-0005 screen after inspecting model/lookup, data, metrics, checkpoint and orchestration code. Sol implemented; Luna independently audited contracts and arithmetic. Astra review NOT PERFORMED.

Root independently ran locked-extra-pilot Ruff, mypy (18 files), pytest (59 passed), and E0 regression smoke (11 gates passed); exact commands/output are preserved here. Root separately reconstructed the dataset from pinned Parquet rows without importing pilot_data and matched both selected byte arrays and their row/offset/rank metadata. Counts: 4,096 train, 512 validation; 15 cross-split validation candidate occurrences excluded.

Registered trial command: `uv run --locked --extra pilot python -m arborlm pilot --config configs/p1_ram_screen.toml --data-dir data/wikitext2 --output-root experiments`.

Six variants × seeds 42/43/44, 256 steps each, 131,072 training targets per cell. Config/spec/scientific gates are frozen before trial. No real-data model has been trained at this checkpoint. The prior Linux data-acquisition/E0 check also passed (Actions 43352388395); CI for this implementation will run after push.

No data/weight release or scientific success follows. Full binary checkpoints and corpus remain local. Reviewer will report all results, including negative/null and cap failures, then apply the preregistered gates without tuning them.
