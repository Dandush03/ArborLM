# P2 implementation and independent preflight

ADR-0007 was preregistered before implementation and any P2 model outcomes. Sol implemented the isolated P2 modules; Luna added five independent contract tests and reviewed the mechanical contract. Root read all new numerical/data/checkpoint/analysis/runner code and independently ran locked Ruff, mypy (25 source files), all 79 tests, and E0 smoke. All passed. Exact logs are retained here, including the optional NumPy warning.

Root independently reconstructed the ranked panel directly from the pinned Parquet bytes, without calling the implementation's selector. The P2 panel hash is `8cd4ab927f9ff17f12bba56b011cf11a94d66e1b77f5f4eba97dd100fb455cd2`, matching Sol's frozen data. Original train/P1 panel/tokenizer hashes match; zero exact overlap with full train candidates or the P1 panel. This does not exclude shared articles or near-duplicates.

Control tests verify dense-equivalent forward/update behavior, frozen and optimizer-excluded memory, separate initialization/order RNGs, checkpoint resume and integrity, fresh intervention restores and a hand-computed factorial analysis. P1 numerical files remain unchanged. No real-data P2 training was performed during preflight.

Root authorizes the exact bounded ADR-0007 suite after code freeze. Command: `uv run --locked --extra pilot python -m arborlm.optimization_followup --data-dir data/wikitext2 --output-root experiments`. Sol will execute it; root will report/export checkpoints and inspect results independently. This is the human-authorized Codex review, not Astra validation. Human merge/publication approval remains pending.
