# ruff: noqa: E501
"""Synthetic single-set evaluation cells for the ADR-0016 tests (no real data, no training).

``write_single_set_cell`` writes an ``eval.json`` and three traces (calibration, A, B) of 32,768
queries in which every query selects the same eight slots, in a rotating (non-ascending) order.
Trees put the eight slots in one branch. Nothing here is a registered or real record.
"""

import json
from pathlib import Path
from typing import Any

import torch
from torch import Tensor

from arborlm import p7a_core as a_core
from arborlm import p7b_core as b_core
from arborlm import p8_core as core
from arborlm.io import write_json

from .null import TOP


def single_set_slots(tree: bool) -> tuple[int, ...]:
    base = 3 * core.PER_BRANCH if tree else 100  # trees: all eight slots lie in branch 3
    return tuple(base + 11 * i for i in range(TOP))


def single_set_trace(
    slots: tuple[int, ...], tree: bool, shift: int, queries: int = core.EVAL_QUERIES
) -> tuple[Tensor, Tensor | None]:
    base = torch.tensor(slots, dtype=torch.int64)
    index = (torch.arange(TOP)[None, :] + torch.arange(queries)[:, None] + shift) % TOP
    selected = base[index]
    if not tree:
        return selected, None
    other = torch.arange(queries) % (core.BRANCHES - 1)
    other = other + (other >= 3).to(torch.int64)
    branches = torch.stack([torch.full((queries,), 3, dtype=torch.int64), other], dim=1)
    return selected, branches


def write_single_set_cell(root: Path, cell: core.Cell) -> Path:
    """The cell directory (``eval.json`` + traces) of a synthetic single-set cell."""
    cell_dir = root / "cells" / cell.label
    cell_dir.mkdir(parents=True)
    tree = cell.variant != "flat"
    slots = single_set_slots(tree)
    traces: dict[str, Any] = {}
    for shift, (name, prefix) in enumerate(
        (("calibration", "calibration"), ("A", "panelA"), ("B", "panelB"))
    ):
        selected, branches = single_set_trace(slots, tree, shift)
        files = a_core.write_trace(cell_dir, prefix, selected, branches)
        counts = a_core.selection_counts(selected)
        traces[name] = {
            "prefix": prefix,
            "files": files,
            "utilization": {"counts_sha256": b_core.counts_sha256(counts)},
        }
    write_json(
        cell_dir / "eval.json",
        {
            "outcome": "completed",
            "label": cell.label,
            "variant": cell.variant,
            "source_sha256": core.source_digest(),
            "spec_sha256": "0" * 64,
            "synthetic": "ADR-0016 test fixture; not a registered record",
            "traces": traces,
        },
    )
    return cell_dir


def collapsed_group(distinct_pages: int = TOP) -> dict[str, Any]:
    """One simulated group of a fully collapsed stream, as predictions 1, 2 and 6 state it."""
    counts = {
        "misses_all": distinct_pages,
        "first_touch_all": distinct_pages,
        "misses_warm": 0,
        "first_touch_warm": 0,
        "ctx_q": [0] * 7,
    }
    return {
        "stats": {"distinct_stream": distinct_pages, "distinct_first_half": distinct_pages},
        "by_c": {str(cap): {tie: dict(counts) for tie in core.TIES} for cap in (32, 8)},
    }


def collapse_sim_record(sim: dict[str, Any]) -> dict[str, Any]:
    """Rewrite a synthetic (``p8_fake``) simulation record into a fully collapsed one: every group
    equals ``collapsed_group()``, temporal reuse is 1.0 everywhere and the three null hashes agree."""
    out: dict[str, Any] = json.loads(json.dumps(sim))
    for record in out["panels"].values():
        for groups in record["streams"].values():
            for key in groups:
                groups[key] = collapsed_group()
        reuse = {
            "hits": 258048,
            "queries_counted": 32256,
            "slots_per_query": TOP,
            "value": 1.0,
            "window": 8,
        }
        record["temporal_reuse"] = {name: dict(reuse) for name in record["temporal_reuse"]}
        record["null_streams"] = [{"stream_sha256": "ab" * 32} for _ in range(3)]
    return out
