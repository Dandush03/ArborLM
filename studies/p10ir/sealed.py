# ruff: noqa: E501
"""P10IR whitelist extractor for P10-S1's ``eval.json`` records (ADR-0029 section 4, 'Sealing rule').

**Every access to an ``eval.json`` of P10-S1's run goes through this module.** It returns only the keys a gate or the analysis names:

* counts (``n``, ``correct``, ``useful``) of the recorded ``main`` and ``ivf`` reads on Panels A and B (gate 2 and the plateau series),
* the recorded index hash and list count of the ``ivf`` read (gate 2),
* ``update`` and ``label``.

The two sealed values (``tree_recall_of_exhaustive_top8`` at U_P of a T-OQ cell and ``ivf_measured.recall_of_exhaustive_top8`` of every F-OQ-IVF read) are never returned, printed, logged or put in an
exception message: ``sealed_equal`` answers equal or not equal and nothing else. Before the freeze no one calls it (the seal forbids gate 3 then).
A test scans the sources: no other module under ``studies/p10ir`` names an ``eval.json`` or a sealed key.
"""

import json
from pathlib import Path
from typing import Any

from . import labels

PANELS = ("A", "B")
READS = ("main", "ivf")
COUNT_KEYS = ("n", "correct", "useful")
SEALED_PATHS: dict[str, tuple[str, ...]] = {
    "tree_recall": ("reads", "main", "deep", "separability", "tree_recall_of_exhaustive_top8"),
    "ivf_recall": ("reads", "ivf", "ivf_measured", "recall_of_exhaustive_top8"),
}


class SealedMissing(FileNotFoundError):
    """The record or the key a gate names is not there (the message names the file, never a value)."""


def eval_path(run_dir: Path, label: str, update: int) -> Path:
    return run_dir / "cells" / label / "eval" / f"u{update:07d}" / "eval.json"


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SealedMissing(f"no evaluation record at {path}")
    with path.open("rb") as stream:
        data = json.load(stream)
    if not isinstance(data, dict):
        raise ValueError(f"not an evaluation record: {path}")
    return data


def _walk(data: dict[str, Any], path: tuple[str, ...]) -> Any:
    cur: Any = data
    for part in path:
        if not isinstance(cur, dict) or part not in cur:
            raise SealedMissing(f"the record lacks the key path {'.'.join(path[:-1])}.<key>")
        cur = cur[part]
    return cur


def counts(run_dir: Path, label: str, update: int, read: str) -> dict[str, dict[str, int]]:
    """``{panel: {n, correct, useful}}`` of the recorded ``main`` or ``ivf`` read at a snapshot. Nothing else of the record is returned."""
    if read not in READS:
        raise ValueError(f"unknown recorded read {read!r}")
    data = _load(eval_path(run_dir, label, update))
    out: dict[str, dict[str, int]] = {}
    for p in PANELS:
        panel = _walk(data, ("reads", read, "panels", p))
        out[p] = {k: int(_walk(panel, (k,))) for k in COUNT_KEYS}
    return out


def index_record(run_dir: Path, label: str, update: int) -> dict[str, Any]:
    """The recorded index hash and list count of the F-OQ-IVF read."""
    data = _load(eval_path(run_dir, label, update))
    ivf = _walk(data, ("reads", "ivf", "index_sha256"))
    return {"index_sha256": str(ivf), "index_lists": int(_walk(data, ("reads", "ivf", "index_lists")))}


def information_series(run_dir: Path, label: str, updates: list[int], read: str = "main") -> dict[str, dict[int, float]]:
    """``{panel: {update: i}}`` of the recorded ``main`` read at the given snapshots, i by P10-S1's ``bits_per_fact`` from the recorded counts (the plateau check of section 9)."""
    from studies.p10s1 import core as s1

    out: dict[str, dict[int, float]] = {p: {} for p in PANELS}
    for u in updates:
        c = counts(run_dir, label, u, read)
        for p in PANELS:
            out[p][u] = s1.bits_per_fact(c[p]["useful"], c[p]["n"])
    return out


def available_updates(run_dir: Path, label: str) -> list[int]:
    """The snapshots that have an evaluation record, from the directory names only (nothing is opened)."""
    root = run_dir / "cells" / label / "eval"
    if not root.is_dir():
        return []
    return sorted(int(p.name[1:]) for p in root.iterdir() if p.name.startswith("u") and (p / "eval.json").is_file())


def sealed_equal(run_dir: Path, label: str, update: int, which: str, value: float) -> bool:
    """Whether the recorded sealed quantity ``which`` equals ``value`` exactly. Returns a boolean and nothing else: the recorded value is never returned or printed."""
    if which not in SEALED_PATHS:
        raise ValueError(f"unknown sealed quantity {which!r}")
    data = _load(eval_path(run_dir, label, update))
    recorded = _walk(data, SEALED_PATHS[which])
    equal = isinstance(recorded, int | float) and not isinstance(recorded, bool) and float(recorded) == float(value)
    del recorded, data
    return bool(equal)


def counts_equal(mine: dict[str, dict[str, int]], recorded: dict[str, dict[str, int]]) -> bool:
    """Gate 2's comparison of correct and useful counts (and n) on both panels, exactly."""
    return all(all(int(mine[p][k]) == int(recorded[p][k]) for k in COUNT_KEYS) for p in labels.PANELS)
