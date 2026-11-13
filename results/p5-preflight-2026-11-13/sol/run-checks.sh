#!/bin/sh
set -ex
uv run --locked --extra pilot ruff check .
uv run --locked --extra pilot mypy src/arborlm
uv run --locked --extra pilot pytest
uv run --locked --extra pilot python -m arborlm smoke --config configs/e0_cpu_smoke.toml --output-root experiments
