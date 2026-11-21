"""Loader for configs/m0_reference_models.toml (every number a proposal; none confirmed)."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(__file__).resolve().parents[2] / "configs" / "m0_reference_models.toml"


def load(path: Path | None = None) -> dict[str, Any]:
    with open(path or CONFIG_PATH, "rb") as fh:
        return tomllib.load(fh)
