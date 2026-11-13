# WikiText-2 acquisition checkpoint

Human-approved local train/validation acquisition at pinned revision; test split remains unacquired/uninspected. Actual corpus bytes match both registered SHA-256 values. Original data and immutable acquisition manifest remain in `data/wikitext2/`; this folder contains provenance only.

Root independent checks after Luna implementation:

- `uv run --no-sync pytest tests/test_fetch_wikitext.py`: 9 passed (mocked network only).
- `uv run --no-sync ruff check src/arborlm/fetch_wikitext.py tests/test_fetch_wikitext.py`: all checks passed.
- `uv run --no-sync mypy src/arborlm/fetch_wikitext.py`: no issues in 1 source file.

Regression tests cover missing-file/manifest mismatch, SHA/size/cap failures, partial transfers, preserved invalid existing files, immutable acquisition records, failure logging and no test-split request. No model training was done for this checkpoint. The optional PyTorch NumPy warning is unrelated to the stdlib downloader.

License metadata conflict is retained in the provenance sidecar and ADR-0004. No legal precedence or redistribution rights are inferred. Source and hashes remain auditable without committing corpus content or temporary CDN authorization URLs.
