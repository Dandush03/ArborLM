# ruff: noqa: E501
"""Shared builders for the P10S2 tests (no tests here): the synthetic world is built once per process, and a trained one-replicate run is cached. All seeds are test seeds (229001-229999).
Self-check only: not independent review, not Astra validation, not human approval."""

import atexit
import shutil
import sys
import tempfile
from functools import cache
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from studies.p10s2 import cells, standins  # noqa: E402
from studies.p10s2.world import World  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


@cache
def dry_world() -> tuple[World, dict[str, Any]]:
    return standins.build_synthetic_world(replicates=1)


@cache
def trained() -> tuple[World, dict[str, Any], Path, dict[str, Any], dict[str, Any]]:
    """World, pre-freeze record, snapshot directory, training records and scored records of replicate 0 (4 updates per unit: mechanics only)."""
    world, rec = dry_world()
    d = Path(tempfile.mkdtemp(prefix="p10s2-test-"))
    atexit.register(shutil.rmtree, d, ignore_errors=True)  # the snapshots of the cached run are removed when the test process ends
    tr = cells.train_replicate(world, 0, d)
    sc = cells.score_replicate(world, 0, d, tr)
    return world, rec, d, tr, sc
