# ruff: noqa: E501
"""Helpers of the P10IS6 tests and of the synthetic rehearsal (a module of the package so that pytest does not collect it): scratch directories INSIDE the worktree (never /tmp), tiny synthetic backbones, chunk tables and panels.
Seeds are the registry's test range only; no registered seed, no checkpoint of the experiments directory and no sealed value is touched. Self-check only."""

import contextlib
import shutil
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import torch

from . import core


def scratch_root() -> Path:
    """``experiments/_scratch/p10i_s6_tests`` of THIS worktree (git-ignored)."""
    root = core.repo_root() / "experiments" / "_scratch" / "p10i_s6_tests"
    root.mkdir(parents=True, exist_ok=True)
    return root


@contextlib.contextmanager
def scratch(name: str = "t") -> Iterator[Path]:
    d = scratch_root() / f"{name}-{uuid.uuid4().hex[:10]}"
    d.mkdir(parents=True)
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


def synthetic_backbone(k: int = 0) -> Any:
    from arborlm.p4_model import Backbone
    from arborlm.pilot_model import PilotModel

    return Backbone(PilotModel("dense_small", 42 + k))


def random_rows(n: int, seed: int) -> torch.Tensor:
    g = torch.Generator().manual_seed(seed)
    return torch.randint(0, 256, (n, 65), generator=g, dtype=torch.int64)


def write_table(path: Path, rows: torch.Tensor) -> None:
    path.write_bytes(bytes(rows.to(torch.uint8).reshape(-1).tolist()))
